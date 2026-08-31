"""The supported deployment/simulation runtime owner for P7 qualification.

Deployment-parity and dynamics claims are claims about a *runtime*, so the
runtime's identity is established by executing it, never by assuming it.  When
the supported runtime is genuinely absent the owner says so with
:class:`~.errors.QualificationUnavailableError`; it never converts absence into
either a pass or a scientific rejection.
"""

from __future__ import annotations

from dataclasses import dataclass
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
from .errors import QualificationError, QualificationUnavailableError
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
        """Can this runtime execute the exact published MACE product?"""

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
            mace_supported = _mace_mliap_interface_supported()
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
        request_path.write_text(json.dumps(dict(request)), encoding="utf-8")
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
        )
        try:
            _stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            _terminate_group(process)
            raise QualificationError(
                f"The supported LAMMPS runtime exceeded its {timeout_seconds:g}s "
                "qualification timeout and its process group was terminated."
            ) from None
        except BaseException:
            _terminate_group(process)
            raise
        if not response_path.is_file():
            raise QualificationError(
                "The LAMMPS qualification worker produced no response "
                f"(exit {process.returncode}): {stderr.strip()[:2000]}"
            )
        payload = json.loads(response_path.read_text(encoding="utf-8"))
    if not payload.get("ok"):
        raise QualificationError(
            f"The supported LAMMPS runtime ({probe.version}) failed: {payload.get('error')}"
        )
    return dict(payload["result"])


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

    energy, forces, _stress = deployed_static_observation(
        atoms,
        artifact_path=artifact_path,
        element_types=element_types,
        working_directory=working_directory,
        timeout_seconds=timeout_seconds,
        include_stress=False,
    )
    return energy, forces


def deployed_static_observation(
    atoms: Any,
    *,
    artifact_path: str | os.PathLike[str],
    element_types: Sequence[str],
    working_directory: str | os.PathLike[str],
    timeout_seconds: float = 900.0,
    include_stress: bool = False,
) -> tuple[float, np.ndarray, np.ndarray | None]:
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
    stress = None
    if result.get("stress_ev_per_angstrom3") is not None:
        stress = canonical_stress_tensor(result["stress_ev_per_angstrom3"])
    return float(result["potential_energy_ev"]), forces, stress


__all__ = [
    "LAMMPS_RUNTIME_PROBE_SCHEMA",
    "LammpsRuntimeProbe",
    "deployed_static_evaluation",
    "deployed_static_observation",
    "execute_lammps_request",
    "probe_lammps_runtime",
    "write_lammps_data",
]
