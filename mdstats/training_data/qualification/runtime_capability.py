"""The supported deployment/simulation runtime owner for P7 qualification.

Deployment-parity and dynamics claims are claims about a *runtime*, so the
runtime's identity is established by executing it, never by assuming it.  When
the supported runtime is genuinely absent the owner says so with
:class:`~.errors.QualificationUnavailableError`; it never converts absence into
either a pass or a scientific rejection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import os
import subprocess
import sys
import tempfile

import numpy as np

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
)
from .errors import (
    QualificationError,
    QualificationLineageError,
    QualificationUnavailableError,
)
from .stress import canonical_stress_tensor

LAMMPS_RUNTIME_PROBE_SCHEMA = "mdstats.qualification-lammps-runtime-probe.v1"

_PROBE_CACHE: "LammpsRuntimeProbe | None" = None


@dataclass(frozen=True, slots=True)
class LammpsRuntimeProbe:
    """What the installed simulation runtime actually is, as observed."""

    available: bool
    version: str | None
    mliap_available: bool
    mliappy_available: bool
    python_module_path: str | None
    #: Whether this runtime's ML-IAP python data object exposes the
    #: message-passing exchange interface a MACE ML-IAP model requires.  A
    #: runtime can support ML-IAP in general and still be unable to execute a
    #: MACE product, which is a materially different claim.
    mace_mliap_supported: bool = False
    detail: str = ""

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LAMMPS_RUNTIME_PROBE_SCHEMA,
            "available": bool(self.available),
            "version": self.version,
            "mliap_available": bool(self.mliap_available),
            "mliappy_available": bool(self.mliappy_available),
            "mace_mliap_supported": bool(self.mace_mliap_supported),
            "python_module_path": self.python_module_path,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def supports_deployed_execution(self) -> bool:
        """Can this runtime execute *an* ML-IAP unified model at all?"""

        return bool(self.available and self.mliap_available and self.mliappy_available)

    @property
    def supports_mace_product_execution(self) -> bool:
        """Diagnostic only: static interface observations for MACE.

        This property is retained for operator diagnostics and historical
        callers.  It is deliberately not used to skip or pass product
        qualification; the isolated worker's actual callback execution owns
        that claim.
        """

        return bool(self.supports_deployed_execution and self.mace_mliap_supported)

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest, "detail": self.detail}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LammpsRuntimeProbe":
        if payload.get("schema") != LAMMPS_RUNTIME_PROBE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LAMMPS runtime-probe schema.")
        result = cls(
            available=bool(payload["available"]),
            version=(None if payload.get("version") is None else str(payload["version"])),
            mliap_available=bool(payload["mliap_available"]),
            mliappy_available=bool(payload["mliappy_available"]),
            mace_mliap_supported=bool(payload.get("mace_mliap_supported", False)),
            python_module_path=(
                None
                if payload.get("python_module_path") is None
                else str(payload["python_module_path"])
            ),
            detail=str(payload.get("detail", "")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("LAMMPS runtime-probe digest mismatch.")
        return result


def probe_lammps_runtime(*, refresh: bool = False) -> LammpsRuntimeProbe:
    """Start the real runtime once and record what it supports."""

    global _PROBE_CACHE
    if _PROBE_CACHE is not None and not refresh:
        return _PROBE_CACHE
    try:
        import lammps
    except Exception as exc:  # noqa: BLE001 - absence is a legitimate observation
        _PROBE_CACHE = LammpsRuntimeProbe(
            available=False,
            version=None,
            mliap_available=False,
            mliappy_available=False,
            python_module_path=None,
            detail=f"LAMMPS python module unavailable: {exc}",
        )
        return _PROBE_CACHE
    instance = None
    try:
        instance = lammps.lammps(cmdargs=["-log", "none", "-screen", "none", "-nocite"])
        version = str(instance.version())
        mliap = bool(instance.has_style("pair", "mliap"))
        mace_supported = False
        try:
            from lammps import mliap as mliap_module

            mliap_module.activate_mliappy(instance)
            mliappy = True
            # This is deliberately a separate, diagnostic-only observation.  A
            # failed import/introspection probe must not be able to demote the
            # live mliappy runtime or suppress the semantic product worker;
            # only actual callback execution owns MACE availability.
            try:
                mace_supported = _mace_mliap_interface_supported()
            except Exception as exc:  # noqa: BLE001 - diagnostic failure is non-authoritative
                mace_supported = False
                detail = (
                    "ML-IAP python coupling activated; static MACE interface "
                    f"diagnostic failed: {exc}"
                )
            else:
                detail = (
                    "supported runtime with ML-IAP python coupling"
                    if mace_supported
                    else (
                        "ML-IAP python coupling present, but its data interface does not "
                        "expose the message-passing exchange a MACE ML-IAP model requires"
                    )
                )
        except Exception as exc:  # noqa: BLE001
            mliappy = False
            detail = f"ML-IAP python coupling unavailable: {exc}"
        _PROBE_CACHE = LammpsRuntimeProbe(
            available=True,
            version=version,
            mliap_available=mliap,
            mliappy_available=mliappy,
            mace_mliap_supported=mace_supported,
            python_module_path=str(Path(lammps.__file__).resolve()),
            detail=detail,
        )
    except Exception as exc:  # noqa: BLE001
        _PROBE_CACHE = LammpsRuntimeProbe(
            available=False,
            version=None,
            mliap_available=False,
            mliappy_available=False,
            python_module_path=str(Path(lammps.__file__).resolve()),
            detail=f"LAMMPS runtime could not be started: {exc}",
        )
    finally:
        if instance is not None:
            try:
                instance.close()
            except Exception:
                pass
    return _PROBE_CACHE


@dataclass(frozen=True, slots=True)
class DeployedStaticObservation:
    """Raw static result plus the post-build geometry observed by the worker."""

    energy: float
    forces: np.ndarray
    stress: np.ndarray | None
    cell_angstrom: np.ndarray
    pbc: tuple[bool, bool, bool]
    runtime_evidence: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.runtime_evidence, Mapping):
            raise QualificationLineageError(
                "The deployed runtime returned invalid structured runtime evidence."
            )
        object.__setattr__(self, "runtime_evidence", dict(self.runtime_evidence))

    def __iter__(self):
        # Compatibility with the pre-R13 three-value owner API.  New callers
        # use the named geometry fields and therefore cannot mistake a request
        # copy for an executed-box observation.
        yield self.energy
        yield self.forces
        yield self.stress


def _mace_mliap_interface_supported() -> bool:
    """Does the activated ML-IAP data object satisfy MACE's model contract?

    MACE's ML-IAP model performs an explicit halo exchange of node features
    between LAMMPS domains. A LAMMPS build whose python ML-IAP data object does
    not expose that call can load a MACE artifact and still fail inside the
    first force evaluation, so the capability is probed here rather than
    discovered halfway through an expensive qualification.
    """

    try:
        import mliap_unified_couple  # type: ignore[import-not-found]
    except Exception:
        return False
    data_class = getattr(mliap_unified_couple, "MLIAPDataPy", None)
    if data_class is None:
        return False
    if not hasattr(data_class, "forward_exchange"):
        return False
    try:
        from mace.calculators.lammps_mliap_mace import LAMMPS_MLIAP_MACE  # noqa: F401
    except Exception:
        return False
    return True


def write_lammps_data(atoms: Any, path: str | os.PathLike[str], *, specorder: Sequence[str]) -> str:
    """Write one deterministic LAMMPS data file and return its SHA-256."""

    from ase.io import write as ase_write
    import hashlib

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    ase_write(
        str(target),
        atoms,
        format="lammps-data",
        specorder=list(specorder),
        masses=True,
        atom_style="atomic",
    )
    return hashlib.sha256(target.read_bytes()).hexdigest()


def _require_supported_runtime() -> LammpsRuntimeProbe:
    probe = probe_lammps_runtime()
    if not probe.supports_deployed_execution:
        raise QualificationUnavailableError(
            "The supported LAMMPS/ML-IAP deployment runtime is unavailable "
            f"({probe.detail or 'no detail'}). Deployment-runtime evidence is "
            "reported as unavailable rather than passed or rejected."
        )
    return probe


def execute_lammps_request(
    request: Mapping[str, Any],
    *,
    working_directory: str | os.PathLike[str],
    timeout_seconds: float = 900.0,
) -> dict[str, Any]:
    """Run one bounded request through the real runtime in its own process group.

    The child is started in a new process group and is terminated as a group on
    timeout or interruption, so a wedged MD run never outlives the qualification
    attempt that owns it.
    """

    probe = _require_supported_runtime()
    root = Path(working_directory)
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=str(root), prefix="lammps-call-") as scratch:
        scratch_root = Path(scratch)
        request_path = scratch_root / "request.json"
        response_path = scratch_root / "response.json"
        launch_args = _effective_lammps_cmdargs(request)
        request_payload = dict(request)
        request_payload["lammps_cmdargs"] = launch_args
        request_path.write_text(json.dumps(request_payload), encoding="utf-8")
        environment = dict(os.environ)
        selected_device = request.get("selected_cuda_device")
        if selected_device is not None:
            device_text = str(selected_device)
            if device_text.startswith("cuda:"):
                device_text = device_text.split(":", 1)[1]
            if device_text not in {"", "cpu"}:
                try:
                    int(device_text)
                except ValueError as exc:
                    raise QualificationLineageError(
                        f"Invalid selected CUDA device {selected_device!r}."
                    ) from exc
                # The worker is process-owned.  Restricting visibility makes
                # the selected physical device unambiguous to KOKKOS without
                # assuming device zero.
                environment["CUDA_VISIBLE_DEVICES"] = device_text
        argv = [
            sys.executable,
            "-m",
            "mdstats.training_data.qualification._lammps_worker",
            str(request_path),
            str(response_path),
        ]
        process = subprocess.Popen(  # noqa: S603 - fixed argv, no shell
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
            env=environment,
        )
        try:
            _stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_group(process)
            raise QualificationUnavailableError(
                f"The supported LAMMPS runtime exceeded its {timeout_seconds:g}s "
                "qualification timeout and its process group was terminated."
            ) from None
        except BaseException:
            _terminate_group(process)
            raise
        if not response_path.is_file():
            raise QualificationUnavailableError(
                "The LAMMPS qualification worker produced no response "
                f"(exit {process.returncode}): {stderr.strip()[:2000]}"
            )
        try:
            payload = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise QualificationUnavailableError(
                "The LAMMPS qualification worker returned corrupt structured output; "
                "the real product path is unavailable/blocking."
            ) from exc
    if not isinstance(payload, Mapping):
        raise QualificationUnavailableError(
            "The LAMMPS qualification worker returned a non-object structured result."
        )
    if process.returncode != 0:
        raise QualificationUnavailableError(
            "The LAMMPS qualification worker exited abnormally; no successful "
            f"product evidence is publishable (exit {process.returncode}): "
            f"{payload.get('error', stderr.strip()[:2000])}"
        )
    if not bool(payload.get("ok")):
        raise QualificationUnavailableError(
            f"The supported LAMMPS runtime ({probe.version}) failed: {payload.get('error')}"
        )
    result = payload.get("result")
    if not isinstance(result, Mapping):
        raise QualificationUnavailableError(
            "The LAMMPS qualification worker returned no structured product result."
        )
    result = dict(result)
    evidence = result.get("runtime_evidence")
    if not isinstance(evidence, Mapping):
        raise QualificationUnavailableError(
            "The real LAMMPS worker returned no runtime-owner evidence; product "
            "execution is unavailable/blocking."
        )
    if not bool(evidence.get("mliappy_activated")) or not bool(
        evidence.get("product_callback_executed")
    ):
        raise QualificationUnavailableError(
            "The real LAMMPS worker did not prove mliappy activation and actual "
            "MACE callback execution; product evidence is unavailable/blocking."
        )
    result["runtime_evidence"] = {
        **dict(evidence),
        "worker_exit_status": int(process.returncode),
        "runtime_probe_digest": probe.content_digest,
        "effective_lammps_cmdargs": list(launch_args),
    }
    return result


def _effective_lammps_cmdargs(request: Mapping[str, Any]) -> list[str]:
    """Resolve the worker's exact KOKKOS startup arguments once."""

    requested_args = request.get("lammps_cmdargs")
    if requested_args is not None:
        return [str(value) for value in requested_args]
    gpu_count = int(request.get("kokkos_gpu_count", 0) or 0)
    if gpu_count < 0:
        raise QualificationError("KOKKOS GPU count must be nonnegative.")
    return ["-k", "on", "g", str(gpu_count), "-sf", "kk"] if gpu_count else []


def _terminate_group(process: "subprocess.Popen[str]") -> None:
    import signal

    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=15.0)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            process.wait(timeout=15.0)
        except subprocess.TimeoutExpired:
            pass


def deployed_static_evaluation(
    atoms: Any,
    *,
    artifact_path: str | os.PathLike[str],
    element_types: Sequence[str],
    working_directory: str | os.PathLike[str],
    timeout_seconds: float = 900.0,
) -> tuple[float, np.ndarray]:
    """Energy/forces for one configuration through the real deployed artifact."""

    observation = deployed_static_observation(
        atoms,
        artifact_path=artifact_path,
        element_types=element_types,
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        include_stress=False,
    )
    return observation.energy, observation.forces


def deployed_static_observation(
    atoms: Any,
    *,
    artifact_path: str | os.PathLike[str],
    element_types: Sequence[str],
    working_directory: str | os.PathLike[str],
    timeout_seconds: float = 900.0,
    include_stress: bool = False,
    kokkos_gpu_count: int = 0,
    selected_cuda_device: int | str | None = None,
) -> DeployedStaticObservation:
    """Energy, forces, and optional canonical stress through the real runtime."""

    root = Path(working_directory)
    root.mkdir(parents=True, exist_ok=True)
    data_path = root / "probe.data"
    write_lammps_data(atoms, data_path, specorder=element_types)
    result = execute_lammps_request(
        {
            "mode": "static",
            "data_path": str(data_path),
            "artifact_path": str(Path(artifact_path).resolve()),
            "element_types": list(element_types),
            "pbc": [bool(value) for value in np.asarray(atoms.get_pbc(), dtype=bool)],
            # Whether to read stress is a caller decision; how to interpret it
            # is not.  LAMMPS thermo pressure is bar and positive in
            # compression, and only the worker's LAMMPS adapter knows that, so
            # no units, ordering, or sign travels in this request.
            "include_stress": bool(include_stress),
            "kokkos_gpu_count": int(kokkos_gpu_count),
            "selected_cuda_device": selected_cuda_device,
        },
        working_directory=root,
        timeout_seconds=timeout_seconds,
    )
    forces = np.asarray(result["forces_ev_per_angstrom"], dtype=np.float64)
    if forces.shape != (len(atoms), 3):
        raise QualificationError(
            "The deployed runtime returned a force array whose shape does not "
            "match the probed configuration."
        )
    observed_pbc_value = result.get("pbc", ())
    if (
        not isinstance(observed_pbc_value, (list, tuple))
        or len(observed_pbc_value) != 3
        or any(type(value) is not bool for value in observed_pbc_value)
    ):
        raise QualificationLineageError(
            "The deployed worker returned no exact three-axis boolean PBC observation."
        )
    observed_pbc = tuple(observed_pbc_value)
    requested_pbc = tuple(bool(value) for value in np.asarray(atoms.get_pbc(), dtype=bool))
    if observed_pbc != requested_pbc:
        raise QualificationLineageError(
            "The deployed worker returned a different per-axis PBC than the request."
        )
    cell = np.asarray(result.get("cell_angstrom"), dtype=np.float64)
    if cell.shape != (3, 3) or not np.all(np.isfinite(cell)):
        raise QualificationLineageError(
            "The deployed worker returned no valid post-build cell observation."
        )
    requested_cell = np.asarray(atoms.get_cell(), dtype=np.float64)
    if not np.allclose(cell, requested_cell, rtol=0.0, atol=1.0e-8):
        raise QualificationLineageError(
            "The deployed worker executed a different post-build cell than requested."
        )
    stress = None
    if result.get("stress_ev_per_angstrom3") is not None:
        stress = canonical_stress_tensor(result["stress_ev_per_angstrom3"])
    return DeployedStaticObservation(
        energy=float(result["potential_energy_ev"]),
        forces=forces,
        stress=stress,
        cell_angstrom=cell,
        pbc=requested_pbc,
        runtime_evidence=dict(result["runtime_evidence"]),
    )


__all__ = [
    "LAMMPS_RUNTIME_PROBE_SCHEMA",
    "DeployedStaticObservation",
    "LammpsRuntimeProbe",
    "deployed_static_evaluation",
    "deployed_static_observation",
    "execute_lammps_request",
    "probe_lammps_runtime",
    "write_lammps_data",
]
