"""Frozen MACE acceleration-backend policy, realization, and qualification.

Campaign configuration records the requested user-facing backend (``e3nn`` or
``cueq``).  Doctor then freezes the exact inference/training implementation so later
stages cannot silently change accelerator kernels or fall back to another backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import importlib
import importlib.metadata
import inspect
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np

from .mace_compatibility import mace_runtime_warning_handled

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
    sha256_file_cached,
)

MACE_ACCELERATION_POLICY_SCHEMA = "mdstats.mace-acceleration-policy.v1"
MACE_ACCELERATION_PROBE_SCHEMA = "mdstats.mace-acceleration-probe.v2"
MACE_ACCELERATION_PROBE_LEGACY_SCHEMA = "mdstats.mace-acceleration-probe.v1"
MACE_ACCELERATION_PARITY_POLICY_SCHEMA = "mdstats.mace-acceleration-parity-policy.v1"
MACE_ACCELERATION_PARITY_RECORD_SCHEMA = "mdstats.mace-acceleration-parity-record.v1"
ACCELERATION_REALIZATION_SCHEMA = "mdstats.acceleration-realization-record.v1"
TRAINING_ACCELERATION_REALIZATION_SCHEMA = "mdstats.training-acceleration-realization-record.v1"
TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_SCHEMA = "mdstats.training-acceleration-repeatability-diagnostic.v2"
TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_LEGACY_SCHEMA = "mdstats.training-acceleration-repeatability-diagnostic.v1"
TRAINING_ACCELERATION_DETERMINISTIC_CONTROL_DIAGNOSTIC_SCHEMA = "mdstats.training-acceleration-deterministic-control-diagnostic.v1"
TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_POLICY_SCHEMA = "mdstats.training-acceleration-noise-normalized-parity-policy.v1"
TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_RECORD_SCHEMA = "mdstats.training-acceleration-noise-normalized-parity-record.v1"


class MaceAccelerationBackend(str, Enum):
    E3NN = "e3nn"
    CUEQ = "cueq"


class MaceAccelerationKernelMode(str, Enum):
    """Resolved implementation behind the user-facing backend choice."""

    E3NN = "e3nn"
    CUEQ_UNRESOLVED = "cueq_unresolved"
    CUEQ_PURE = "cueq_pure"
    CUEQ_OEQ_HYBRID = "cueq_oeq_hybrid"

    @property
    def backend(self) -> MaceAccelerationBackend:
        return (
            MaceAccelerationBackend.E3NN
            if self is MaceAccelerationKernelMode.E3NN
            else MaceAccelerationBackend.CUEQ
        )

    def calculator_kwargs(self) -> dict[str, Any]:
        if self is MaceAccelerationKernelMode.E3NN:
            return {"enable_cueq": False, "enable_oeq": False}
        if self is MaceAccelerationKernelMode.CUEQ_UNRESOLVED:
            raise TrainingDataInputError("Unresolved CuEq mode cannot construct a calculator.")
        if self is MaceAccelerationKernelMode.CUEQ_PURE:
            return {"enable_cueq": True, "enable_oeq": False}
        return {"enable_cueq": True, "enable_oeq": True}


@dataclass(frozen=True, slots=True)
class MaceAccelerationPolicy:
    """Immutable backend choice used by preparation, training, and evaluation."""

    backend: MaceAccelerationBackend = MaceAccelerationBackend.E3NN
    only_cueq: bool = False
    require_available: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "backend", MaceAccelerationBackend(self.backend))
        if self.only_cueq and self.backend is not MaceAccelerationBackend.CUEQ:
            raise TrainingDataInputError("only_cueq requires backend='cueq'.")

    @property
    def enable_cueq(self) -> bool:
        return self.backend is MaceAccelerationBackend.CUEQ

    def calculator_kwargs(self) -> dict[str, Any]:
        return {"enable_cueq": self.enable_cueq}

    def training_config(self) -> dict[str, Any]:
        return {
            "enable_cueq": self.enable_cueq,
            "only_cueq": bool(self.only_cueq),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_ACCELERATION_POLICY_SCHEMA,
            "backend": self.backend.value,
            "enable_cueq": self.enable_cueq,
            "only_cueq": bool(self.only_cueq),
            "require_available": bool(self.require_available),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceAccelerationPolicy":
        if payload.get("schema") != MACE_ACCELERATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE acceleration-policy schema.")
        result = cls(
            backend=MaceAccelerationBackend(str(payload["backend"])),
            only_cueq=bool(payload.get("only_cueq", False)),
            require_available=bool(payload.get("require_available", True)),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE acceleration-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceAccelerationProbe:
    """Runtime evidence that the requested MACE backend is actually usable."""

    device: str
    torch_version: str | None
    torch_cuda_version: str | None
    cuda_available: bool
    mace_version: str | None
    calculator_enable_cueq_supported: bool
    cueq_versions: tuple[tuple[str, str | None], ...]
    cueq_imports_passed: bool
    model_smoke_attempted: bool
    model_smoke_passed: bool | None
    finite_energy: bool | None
    finite_forces: bool | None
    finite_stress: bool | None
    error_type: str | None
    error_message: str | None
    calculator_enable_oeq_supported: bool = False
    oeq_version: str | None = None
    oeq_import_passed: bool = False
    serialization_schema: str = field(
        default=MACE_ACCELERATION_PROBE_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.device not in {"cpu", "cuda"}:
            raise TrainingDataInputError("Acceleration probe device must be cpu or cuda.")
        if self.serialization_schema not in {
            MACE_ACCELERATION_PROBE_SCHEMA, MACE_ACCELERATION_PROBE_LEGACY_SCHEMA
        }:
            raise TrainingDataInputError("Unsupported internal acceleration-probe serialization schema.")
        object.__setattr__(
            self,
            "cueq_versions",
            tuple((str(name), None if value is None else str(value)) for name, value in self.cueq_versions),
        )

    @property
    def cueq_available(self) -> bool:
        device_ready = self.device != "cuda" or self.cuda_available
        return bool(
            device_ready
            and self.cueq_imports_passed
            and self.calculator_enable_cueq_supported
        )

    def passed_for(self, policy: MaceAccelerationPolicy) -> bool:
        if policy.backend is MaceAccelerationBackend.E3NN:
            return self.device != "cuda" or self.cuda_available
        if not self.cueq_available:
            return False
        if self.model_smoke_attempted:
            return bool(
                self.model_smoke_passed
                and self.finite_energy
                and self.finite_forces
                and self.finite_stress
            )
        return True

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "device": self.device,
            "torch_version": self.torch_version,
            "torch_cuda_version": self.torch_cuda_version,
            "cuda_available": self.cuda_available,
            "mace_version": self.mace_version,
            "calculator_enable_cueq_supported": self.calculator_enable_cueq_supported,
            "cueq_versions": [list(item) for item in self.cueq_versions],
            "cueq_imports_passed": self.cueq_imports_passed,
            "cueq_available": self.cueq_available,
            "model_smoke_attempted": self.model_smoke_attempted,
            "model_smoke_passed": self.model_smoke_passed,
            "finite_energy": self.finite_energy,
            "finite_forces": self.finite_forces,
            "finite_stress": self.finite_stress,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }
        if self.serialization_schema == MACE_ACCELERATION_PROBE_SCHEMA:
            payload.update({
                "calculator_enable_oeq_supported": self.calculator_enable_oeq_supported,
                "oeq_version": self.oeq_version,
                "oeq_import_passed": self.oeq_import_passed,
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceAccelerationProbe":
        schema = payload.get("schema")
        if schema not in {MACE_ACCELERATION_PROBE_SCHEMA, MACE_ACCELERATION_PROBE_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MACE acceleration-probe schema.")
        result = cls(
            device=str(payload["device"]),
            torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
            torch_cuda_version=None if payload.get("torch_cuda_version") is None else str(payload["torch_cuda_version"]),
            cuda_available=bool(payload["cuda_available"]),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            calculator_enable_cueq_supported=bool(payload["calculator_enable_cueq_supported"]),
            cueq_versions=tuple((str(v[0]), None if v[1] is None else str(v[1])) for v in payload.get("cueq_versions", ())),
            cueq_imports_passed=bool(payload["cueq_imports_passed"]),
            model_smoke_attempted=bool(payload["model_smoke_attempted"]),
            model_smoke_passed=None if payload.get("model_smoke_passed") is None else bool(payload["model_smoke_passed"]),
            finite_energy=None if payload.get("finite_energy") is None else bool(payload["finite_energy"]),
            finite_forces=None if payload.get("finite_forces") is None else bool(payload["finite_forces"]),
            finite_stress=None if payload.get("finite_stress") is None else bool(payload["finite_stress"]),
            error_type=None if payload.get("error_type") is None else str(payload["error_type"]),
            error_message=None if payload.get("error_message") is None else str(payload["error_message"]),
            calculator_enable_oeq_supported=bool(payload.get("calculator_enable_oeq_supported", False)),
            oeq_version=None if payload.get("oeq_version") is None else str(payload["oeq_version"]),
            oeq_import_passed=bool(payload.get("oeq_import_passed", False)),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE acceleration-probe digest mismatch.")
        return result


def _distribution_version(distribution: str, module: Any | None = None) -> str | None:
    version = None if module is None else getattr(module, "__version__", None)
    if version is not None:
        return str(version)
    try:
        return str(importlib.metadata.version(distribution))
    except importlib.metadata.PackageNotFoundError:
        return None


@mace_runtime_warning_handled("MACE acceleration probe")
def probe_mace_acceleration(
    *,
    device: str = "cuda",
    model_path: str | Path | None = None,
    sample_atoms: Any | None = None,
    default_dtype: str = "float32",
    head: str | None = None,
    run_model_smoke: bool = False,
    install_critical_fp64: bool = True,
) -> MaceAccelerationProbe:
    """Probe package-level CuEq support and optionally execute one real model call."""

    if device not in {"cpu", "cuda"}:
        raise TrainingDataInputError("Acceleration probe device must be cpu or cuda.")
    if default_dtype not in {"float32", "float64"}:
        raise TrainingDataInputError("Acceleration probe dtype must be float32 or float64.")

    torch_version: str | None = None
    torch_cuda_version: str | None = None
    cuda_available = False
    mace_version: str | None = None
    calculator_supported = False
    calculator_oeq_supported = False
    cueq_versions: list[tuple[str, str | None]] = []
    cueq_imports_passed = True
    oeq_version: str | None = None
    oeq_import_passed = False
    error_type: str | None = None
    error_message: str | None = None
    model_smoke_passed: bool | None = None
    finite_energy: bool | None = None
    finite_forces: bool | None = None
    finite_stress: bool | None = None

    try:
        import torch

        torch_version = str(torch.__version__)
        torch_cuda_version = None if torch.version.cuda is None else str(torch.version.cuda)
        cuda_available = bool(torch.cuda.is_available())
    except Exception as exc:  # pragma: no cover - a broken torch import is environment-specific
        error_type = type(exc).__name__
        error_message = str(exc)

    try:
        import mace
        from mace.calculators import MACECalculator

        mace_version = _distribution_version("mace-torch", mace)
        signature = inspect.signature(MACECalculator.__init__)
        calculator_supported = "enable_cueq" in signature.parameters
        calculator_oeq_supported = "enable_oeq" in signature.parameters
    except Exception as exc:
        if error_type is None:
            error_type = type(exc).__name__
            error_message = str(exc)
        MACECalculator = None  # type: ignore[assignment]

    modules = (
        (("cuequivariance",), "cuequivariance"),
        (("cuequivariance-torch",), "cuequivariance_torch"),
        (
            (
                "cuequivariance-ops-torch-cu13",
                "cuequivariance-ops-torch-cu12",
                "cuequivariance-ops-torch-cu11",
                "cuequivariance-ops-torch",
            ),
            "cuequivariance_ops_torch",
        ),
    )
    for distributions, import_name in modules:
        display_name = distributions[0]
        try:
            module = importlib.import_module(import_name)
            installed_name = display_name
            installed_version = None
            for distribution in distributions:
                candidate = _distribution_version(distribution, None)
                if candidate is not None:
                    installed_name = distribution
                    installed_version = candidate
                    break
            if installed_version is None:
                installed_version = getattr(module, "__version__", None)
            cueq_versions.append(
                (installed_name, None if installed_version is None else str(installed_version))
            )
        except Exception as exc:
            cueq_imports_passed = False
            cueq_versions.append((display_name, None))
            if error_type is None:
                error_type = type(exc).__name__
                error_message = f"{import_name}: {exc}"

    try:
        oeq_module = importlib.import_module("openequivariance")
        oeq_import_passed = True
        oeq_version = _distribution_version("openequivariance", oeq_module)
        if oeq_version is None:
            oeq_version = _distribution_version("OpenEquivariance", oeq_module)
    except Exception:
        oeq_import_passed = False
        oeq_version = None

    model_smoke_attempted = bool(run_model_smoke)
    package_ready = bool(
        cueq_imports_passed
        and calculator_supported
        and (device != "cuda" or cuda_available)
    )
    if run_model_smoke:
        if model_path is None or sample_atoms is None:
            raise TrainingDataInputError("A CuEq model smoke requires model_path and sample_atoms.")
        if not package_ready or MACECalculator is None:
            model_smoke_passed = False
        else:
            try:
                if install_critical_fp64:
                    from .critical_precision import install_mace_critical_fp64_patch

                    install_mace_critical_fp64_patch()
                calculator_kwargs: dict[str, Any] = {"enable_cueq": True}
                if head is not None:
                    calculator_kwargs["head"] = str(head)
                calculator = MACECalculator(
                    model_paths=str(Path(model_path).resolve()),
                    device=device,
                    default_dtype=default_dtype,
                    **calculator_kwargs,
                )
                candidate = sample_atoms.copy()
                candidate.calc = calculator
                energy = float(candidate.get_potential_energy())
                forces = np.asarray(candidate.get_forces(), dtype=np.float64)
                stress = np.asarray(candidate.get_stress(voigt=True), dtype=np.float64)
                finite_energy = bool(np.isfinite(energy))
                finite_forces = bool(np.all(np.isfinite(forces)))
                finite_stress = bool(np.all(np.isfinite(stress)))
                model_smoke_passed = bool(finite_energy and finite_forces and finite_stress)
            except Exception as exc:
                model_smoke_passed = False
                finite_energy = False
                finite_forces = False
                finite_stress = False
                error_type = type(exc).__name__
                error_message = str(exc)

    return MaceAccelerationProbe(
        device=device,
        torch_version=torch_version,
        torch_cuda_version=torch_cuda_version,
        cuda_available=cuda_available,
        mace_version=mace_version,
        calculator_enable_cueq_supported=calculator_supported,
        calculator_enable_oeq_supported=calculator_oeq_supported,
        cueq_versions=tuple(cueq_versions),
        cueq_imports_passed=cueq_imports_passed,
        model_smoke_attempted=model_smoke_attempted,
        model_smoke_passed=model_smoke_passed,
        finite_energy=finite_energy,
        finite_forces=finite_forces,
        finite_stress=finite_stress,
        error_type=error_type,
        error_message=error_message,
        oeq_version=oeq_version,
        oeq_import_passed=oeq_import_passed,
    )



@dataclass(frozen=True, slots=True)
class MaceAccelerationParityPolicy:
    """Numerical equivalence policy for accelerated foundation inference."""

    float32_rtol: float = 1.0e-5
    float32_atol: float = 1.0e-6
    float64_rtol: float = 1.0e-10
    float64_atol: float = 1.0e-12
    selection_fraction: float = 0.5
    fps_tie_tolerance: float = 1.0e-12

    def __post_init__(self) -> None:
        for name in ("float32_rtol", "float32_atol", "float64_rtol", "float64_atol", "fps_tie_tolerance"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"Acceleration parity {name} must be positive and finite.")
        if not np.isfinite(self.selection_fraction) or not 0.0 < self.selection_fraction <= 1.0:
            raise TrainingDataInputError("Acceleration parity selection_fraction must be in (0, 1].")

    def tolerance(self, dtype: str) -> tuple[float, float]:
        if dtype == "float32":
            return self.float32_rtol, self.float32_atol
        if dtype == "float64":
            return self.float64_rtol, self.float64_atol
        raise TrainingDataInputError("Acceleration parity dtype must be float32 or float64.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_ACCELERATION_PARITY_POLICY_SCHEMA,
            "float32_rtol": self.float32_rtol,
            "float32_atol": self.float32_atol,
            "float64_rtol": self.float64_rtol,
            "float64_atol": self.float64_atol,
            "selection_fraction": self.selection_fraction,
            "fps_tie_tolerance": self.fps_tie_tolerance,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceAccelerationParityPolicy":
        if payload.get("schema") != MACE_ACCELERATION_PARITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE acceleration-parity policy schema.")
        result = cls(
            float32_rtol=float(payload["float32_rtol"]),
            float32_atol=float(payload["float32_atol"]),
            float64_rtol=float(payload["float64_rtol"]),
            float64_atol=float(payload["float64_atol"]),
            selection_fraction=float(payload["selection_fraction"]),
            fps_tie_tolerance=float(payload["fps_tie_tolerance"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE acceleration-parity policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceAccelerationParityRecord:
    reference_mode: str
    candidate_mode: str
    dtype: str
    structure_count: int
    atom_count: int
    energy_max_abs: float
    energy_rmse: float
    force_max_abs: float
    force_rmse: float
    stress_max_abs: float
    stress_rmse: float
    descriptor_max_abs: float
    descriptor_rmse: float
    reference_selection: tuple[str, ...]
    candidate_selection: tuple[str, ...]
    policy_digest: str
    passed: bool

    def __post_init__(self) -> None:
        reference_mode = MaceAccelerationKernelMode(self.reference_mode)
        candidate_mode = MaceAccelerationKernelMode(self.candidate_mode)
        if reference_mode is not MaceAccelerationKernelMode.E3NN:
            raise TrainingDataInputError("Acceleration parity reference mode must be e3nn.")
        if candidate_mode not in {
            MaceAccelerationKernelMode.CUEQ_PURE,
            MaceAccelerationKernelMode.CUEQ_OEQ_HYBRID,
        }:
            raise TrainingDataInputError("Acceleration parity candidate must be a resolved CuEq implementation.")
        if self.dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Acceleration parity dtype must be float32 or float64.")
        if self.structure_count <= 0 or self.atom_count <= 0:
            raise TrainingDataInputError("Acceleration parity requires non-empty structures/atoms.")
        for name in (
            "energy_max_abs", "energy_rmse", "force_max_abs", "force_rmse",
            "stress_max_abs", "stress_rmse", "descriptor_max_abs", "descriptor_rmse",
        ):
            if not np.isfinite(float(getattr(self, name))) or float(getattr(self, name)) < 0.0:
                raise TrainingDataInputError(f"Acceleration parity {name} must be finite and non-negative.")
        object.__setattr__(self, "reference_selection", tuple(str(v) for v in self.reference_selection))
        object.__setattr__(self, "candidate_selection", tuple(str(v) for v in self.candidate_selection))
        if not self.reference_selection or not self.candidate_selection:
            raise TrainingDataInputError("Acceleration parity selection fingerprints must be non-empty.")
        if self.passed and self.reference_selection != self.candidate_selection:
            raise TrainingDataInputError("Passing acceleration parity requires identical selection fingerprints.")
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))

    @property
    def selection_identical(self) -> bool:
        return self.reference_selection == self.candidate_selection

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_ACCELERATION_PARITY_RECORD_SCHEMA,
            "reference_mode": self.reference_mode,
            "candidate_mode": self.candidate_mode,
            "dtype": self.dtype,
            "structure_count": self.structure_count,
            "atom_count": self.atom_count,
            "energy_max_abs": self.energy_max_abs,
            "energy_rmse": self.energy_rmse,
            "force_max_abs": self.force_max_abs,
            "force_rmse": self.force_rmse,
            "stress_max_abs": self.stress_max_abs,
            "stress_rmse": self.stress_rmse,
            "descriptor_max_abs": self.descriptor_max_abs,
            "descriptor_rmse": self.descriptor_rmse,
            "reference_selection": list(self.reference_selection),
            "candidate_selection": list(self.candidate_selection),
            "selection_identical": self.selection_identical,
            "policy_digest": self.policy_digest,
            "passed": bool(self.passed),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceAccelerationParityRecord":
        if payload.get("schema") != MACE_ACCELERATION_PARITY_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE acceleration-parity record schema.")
        result = cls(
            reference_mode=str(payload["reference_mode"]), candidate_mode=str(payload["candidate_mode"]),
            dtype=str(payload["dtype"]), structure_count=int(payload["structure_count"]), atom_count=int(payload["atom_count"]),
            energy_max_abs=float(payload["energy_max_abs"]), energy_rmse=float(payload["energy_rmse"]),
            force_max_abs=float(payload["force_max_abs"]), force_rmse=float(payload["force_rmse"]),
            stress_max_abs=float(payload["stress_max_abs"]), stress_rmse=float(payload["stress_rmse"]),
            descriptor_max_abs=float(payload["descriptor_max_abs"]), descriptor_rmse=float(payload["descriptor_rmse"]),
            reference_selection=tuple(str(v) for v in payload.get("reference_selection", ())),
            candidate_selection=tuple(str(v) for v in payload.get("candidate_selection", ())),
            policy_digest=str(payload["policy_digest"]), passed=bool(payload["passed"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE acceleration-parity record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingAccelerationRepeatabilityDiagnostic:
    """Non-authorizing repeated TRAIN2 backend numerical diagnostic.

    Version 2 discards explicit warm-up evaluations and computes all-pairs
    statistics over the post-warm-up samples.  Historical v1 baseline-vs-run
    records remain readable.  The diagnostic never widens or otherwise alters
    the active parity policy.
    """

    repeat_count: int
    dtype: str
    structure_count: int
    atom_count: int
    force_threshold: float
    e3nn_self_force_max_abs: tuple[float, ...]
    e3nn_self_force_rmse: tuple[float, ...]
    cueq_self_force_max_abs: tuple[float, ...]
    cueq_self_force_rmse: tuple[float, ...]
    cross_energy_max_abs: tuple[float, ...]
    cross_energy_rmse: tuple[float, ...]
    cross_force_max_abs: tuple[float, ...]
    cross_force_rmse: tuple[float, ...]
    cross_force_p99_abs: tuple[float, ...]
    cross_force_p999_abs: tuple[float, ...]
    cross_force_above_threshold_count: tuple[int, ...]
    cross_force_component_count: int
    cross_stress_max_abs: tuple[float, ...]
    cross_stress_rmse: tuple[float, ...]
    cross_descriptor_max_abs: tuple[float, ...]
    cross_descriptor_rmse: tuple[float, ...]
    cross_selection_identical: tuple[bool, ...]
    policy_digest: str
    torch_deterministic_algorithms: bool | None = None
    torch_deterministic_debug_mode: int | None = None
    cudnn_deterministic: bool | None = None
    cublas_workspace_config: str | None = None
    e3nn_self_force_p99_abs: tuple[float, ...] = ()
    e3nn_self_force_p999_abs: tuple[float, ...] = ()
    e3nn_self_force_above_threshold_count: tuple[int, ...] = ()
    cueq_self_force_p99_abs: tuple[float, ...] = ()
    cueq_self_force_p999_abs: tuple[float, ...] = ()
    cueq_self_force_above_threshold_count: tuple[int, ...] = ()
    comparison_mode: str = "baseline"
    warmup_count: int = 0
    e3nn_self_energy_max_abs: tuple[float, ...] = ()
    e3nn_self_stress_max_abs: tuple[float, ...] = ()
    e3nn_self_descriptor_max_abs: tuple[float, ...] = ()
    cueq_self_energy_max_abs: tuple[float, ...] = ()
    cueq_self_stress_max_abs: tuple[float, ...] = ()
    cueq_self_descriptor_max_abs: tuple[float, ...] = ()
    e3nn_self_selection_identical: tuple[bool, ...] = ()
    cueq_self_selection_identical: tuple[bool, ...] = ()

    @property
    def self_pair_count(self) -> int:
        if self.comparison_mode == "all_pairs":
            return self.repeat_count * (self.repeat_count - 1) // 2
        return self.repeat_count - 1

    @property
    def cross_pair_count(self) -> int:
        if self.comparison_mode == "all_pairs":
            return self.repeat_count * self.repeat_count
        return self.repeat_count

    def __post_init__(self) -> None:
        if self.repeat_count < 2:
            raise TrainingDataInputError("TRAIN2 repeatability diagnostic requires at least two repeats.")
        if self.dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("TRAIN2 repeatability diagnostic dtype must be float32 or float64.")
        if self.structure_count <= 0 or self.atom_count <= 0:
            raise TrainingDataInputError("TRAIN2 repeatability diagnostic requires non-empty structures/atoms.")
        if not np.isfinite(float(self.force_threshold)) or float(self.force_threshold) <= 0.0:
            raise TrainingDataInputError("TRAIN2 repeatability force threshold must be positive and finite.")
        if self.comparison_mode not in {"baseline", "all_pairs"}:
            raise TrainingDataInputError("TRAIN2 repeatability comparison_mode must be baseline or all_pairs.")
        if int(self.warmup_count) < 0:
            raise TrainingDataInputError("TRAIN2 repeatability warmup_count cannot be negative.")
        object.__setattr__(self, "warmup_count", int(self.warmup_count))

        self_names = (
            "e3nn_self_force_max_abs", "e3nn_self_force_rmse",
            "cueq_self_force_max_abs", "cueq_self_force_rmse",
        )
        detail_names = (
            "e3nn_self_force_p99_abs", "e3nn_self_force_p999_abs",
            "cueq_self_force_p99_abs", "cueq_self_force_p999_abs",
            "e3nn_self_energy_max_abs", "e3nn_self_stress_max_abs", "e3nn_self_descriptor_max_abs",
            "cueq_self_energy_max_abs", "cueq_self_stress_max_abs", "cueq_self_descriptor_max_abs",
        )
        cross_names = (
            "cross_energy_max_abs", "cross_energy_rmse",
            "cross_force_max_abs", "cross_force_rmse",
            "cross_force_p99_abs", "cross_force_p999_abs",
            "cross_stress_max_abs", "cross_stress_rmse",
            "cross_descriptor_max_abs", "cross_descriptor_rmse",
        )
        for name in self_names:
            values = tuple(float(v) for v in getattr(self, name))
            if len(values) != self.self_pair_count:
                raise TrainingDataInputError(f"{name} must contain self_pair_count values.")
            if any((not np.isfinite(v) or v < 0.0) for v in values):
                raise TrainingDataInputError(f"{name} must contain finite non-negative values.")
            object.__setattr__(self, name, values)
        for name in detail_names:
            values = tuple(float(v) for v in getattr(self, name))
            if values and len(values) != self.self_pair_count:
                raise TrainingDataInputError(f"{name} must contain self_pair_count values when present.")
            if any((not np.isfinite(v) or v < 0.0) for v in values):
                raise TrainingDataInputError(f"{name} must contain finite non-negative values.")
            object.__setattr__(self, name, values)
        for name in cross_names:
            values = tuple(float(v) for v in getattr(self, name))
            if len(values) != self.cross_pair_count:
                raise TrainingDataInputError(f"{name} must contain cross_pair_count values.")
            if any((not np.isfinite(v) or v < 0.0) for v in values):
                raise TrainingDataInputError(f"{name} must contain finite non-negative values.")
            object.__setattr__(self, name, values)
        counts = tuple(int(v) for v in self.cross_force_above_threshold_count)
        if len(counts) != self.cross_pair_count or any(v < 0 or v > self.cross_force_component_count for v in counts):
            raise TrainingDataInputError("Invalid TRAIN2 repeatability cross force-threshold counts.")
        object.__setattr__(self, "cross_force_above_threshold_count", counts)
        for name in ("e3nn_self_force_above_threshold_count", "cueq_self_force_above_threshold_count"):
            values = tuple(int(v) for v in getattr(self, name))
            if values and len(values) != self.self_pair_count:
                raise TrainingDataInputError(f"{name} must contain self_pair_count values when present.")
            if any(v < 0 or v > self.cross_force_component_count for v in values):
                raise TrainingDataInputError(f"Invalid {name} values.")
            object.__setattr__(self, name, values)
        selections = tuple(bool(v) for v in self.cross_selection_identical)
        if len(selections) != self.cross_pair_count:
            raise TrainingDataInputError("cross_selection_identical must contain cross_pair_count values.")
        object.__setattr__(self, "cross_selection_identical", selections)
        for name in ("e3nn_self_selection_identical", "cueq_self_selection_identical"):
            values = tuple(bool(v) for v in getattr(self, name))
            if values and len(values) != self.self_pair_count:
                raise TrainingDataInputError(f"{name} must contain self_pair_count values when present.")
            object.__setattr__(self, name, values)
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        if self.cublas_workspace_config is not None:
            object.__setattr__(self, "cublas_workspace_config", str(self.cublas_workspace_config))

    @staticmethod
    def _summary(values: Sequence[float]) -> dict[str, float]:
        array = np.asarray(tuple(values), dtype=np.float64)
        return {
            "min": float(np.min(array)),
            "median": float(np.median(array)),
            "p90": float(np.percentile(array, 90.0)),
            "p99": float(np.percentile(array, 99.0)),
            "max": float(np.max(array)),
        }

    @property
    def self_detail_available(self) -> bool:
        return bool(self.e3nn_self_force_p99_abs and self.cueq_self_force_p99_abs)

    @property
    def self_channel_detail_available(self) -> bool:
        return bool(self.e3nn_self_energy_max_abs and self.cueq_self_energy_max_abs)

    @property
    def summaries(self) -> dict[str, dict[str, float]]:
        fields = (
            "e3nn_self_force_max_abs", "e3nn_self_force_rmse",
            "cueq_self_force_max_abs", "cueq_self_force_rmse",
            "cross_energy_max_abs", "cross_force_max_abs", "cross_force_rmse",
            "cross_force_p99_abs", "cross_force_p999_abs",
            "cross_stress_max_abs", "cross_descriptor_max_abs",
        )
        result = {name: self._summary(getattr(self, name)) for name in fields}
        for name in (
            "e3nn_self_force_p99_abs", "e3nn_self_force_p999_abs",
            "cueq_self_force_p99_abs", "cueq_self_force_p999_abs",
            "e3nn_self_energy_max_abs", "e3nn_self_stress_max_abs", "e3nn_self_descriptor_max_abs",
            "cueq_self_energy_max_abs", "cueq_self_stress_max_abs", "cueq_self_descriptor_max_abs",
        ):
            if getattr(self, name):
                result[name] = self._summary(getattr(self, name))
        return result

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_SCHEMA,
            "repeat_count": self.repeat_count,
            "comparison_mode": self.comparison_mode,
            "warmup_count": self.warmup_count,
            "self_pair_count": self.self_pair_count,
            "cross_pair_count": self.cross_pair_count,
            "dtype": self.dtype, "structure_count": self.structure_count, "atom_count": self.atom_count,
            "force_threshold": self.force_threshold,
            "e3nn_self_force_max_abs": list(self.e3nn_self_force_max_abs),
            "e3nn_self_force_rmse": list(self.e3nn_self_force_rmse),
            "e3nn_self_force_p99_abs": list(self.e3nn_self_force_p99_abs),
            "e3nn_self_force_p999_abs": list(self.e3nn_self_force_p999_abs),
            "e3nn_self_force_above_threshold_count": list(self.e3nn_self_force_above_threshold_count),
            "e3nn_self_energy_max_abs": list(self.e3nn_self_energy_max_abs),
            "e3nn_self_stress_max_abs": list(self.e3nn_self_stress_max_abs),
            "e3nn_self_descriptor_max_abs": list(self.e3nn_self_descriptor_max_abs),
            "e3nn_self_selection_identical": list(self.e3nn_self_selection_identical),
            "cueq_self_force_max_abs": list(self.cueq_self_force_max_abs),
            "cueq_self_force_rmse": list(self.cueq_self_force_rmse),
            "cueq_self_force_p99_abs": list(self.cueq_self_force_p99_abs),
            "cueq_self_force_p999_abs": list(self.cueq_self_force_p999_abs),
            "cueq_self_force_above_threshold_count": list(self.cueq_self_force_above_threshold_count),
            "cueq_self_energy_max_abs": list(self.cueq_self_energy_max_abs),
            "cueq_self_stress_max_abs": list(self.cueq_self_stress_max_abs),
            "cueq_self_descriptor_max_abs": list(self.cueq_self_descriptor_max_abs),
            "cueq_self_selection_identical": list(self.cueq_self_selection_identical),
            "cross_energy_max_abs": list(self.cross_energy_max_abs),
            "cross_energy_rmse": list(self.cross_energy_rmse),
            "cross_force_max_abs": list(self.cross_force_max_abs),
            "cross_force_rmse": list(self.cross_force_rmse),
            "cross_force_p99_abs": list(self.cross_force_p99_abs),
            "cross_force_p999_abs": list(self.cross_force_p999_abs),
            "cross_force_above_threshold_count": list(self.cross_force_above_threshold_count),
            "cross_force_component_count": self.cross_force_component_count,
            "cross_stress_max_abs": list(self.cross_stress_max_abs),
            "cross_stress_rmse": list(self.cross_stress_rmse),
            "cross_descriptor_max_abs": list(self.cross_descriptor_max_abs),
            "cross_descriptor_rmse": list(self.cross_descriptor_rmse),
            "cross_selection_identical": list(self.cross_selection_identical),
            "selection_identical_count": sum(self.cross_selection_identical),
            "policy_digest": self.policy_digest,
            "torch_deterministic_algorithms": self.torch_deterministic_algorithms,
            "torch_deterministic_debug_mode": self.torch_deterministic_debug_mode,
            "cudnn_deterministic": self.cudnn_deterministic,
            "cublas_workspace_config": self.cublas_workspace_config,
            "self_detail_available": self.self_detail_available,
            "self_channel_detail_available": self.self_channel_detail_available,
            "summaries": self.summaries,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingAccelerationRepeatabilityDiagnostic":
        schema = payload.get("schema")
        if schema not in {TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_SCHEMA, TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported TRAIN2 repeatability-diagnostic schema.")
        is_legacy = schema == TRAINING_ACCELERATION_REPEATABILITY_DIAGNOSTIC_LEGACY_SCHEMA
        if is_legacy and payload.get("content_digest") is not None:
            raw = {key: value for key, value in payload.items() if key != "content_digest"}
            if payload["content_digest"] != digest(raw):
                raise TrainingDataSerializationError("TRAIN2 repeatability-diagnostic digest mismatch.")
        result = cls(
            repeat_count=int(payload["repeat_count"]), dtype=str(payload["dtype"]),
            structure_count=int(payload["structure_count"]), atom_count=int(payload["atom_count"]),
            force_threshold=float(payload["force_threshold"]),
            e3nn_self_force_max_abs=tuple(payload["e3nn_self_force_max_abs"]),
            e3nn_self_force_rmse=tuple(payload["e3nn_self_force_rmse"]),
            cueq_self_force_max_abs=tuple(payload["cueq_self_force_max_abs"]),
            cueq_self_force_rmse=tuple(payload["cueq_self_force_rmse"]),
            cross_energy_max_abs=tuple(payload["cross_energy_max_abs"]),
            cross_energy_rmse=tuple(payload["cross_energy_rmse"]),
            cross_force_max_abs=tuple(payload["cross_force_max_abs"]),
            cross_force_rmse=tuple(payload["cross_force_rmse"]),
            cross_force_p99_abs=tuple(payload["cross_force_p99_abs"]),
            cross_force_p999_abs=tuple(payload["cross_force_p999_abs"]),
            cross_force_above_threshold_count=tuple(payload["cross_force_above_threshold_count"]),
            cross_force_component_count=int(payload["cross_force_component_count"]),
            cross_stress_max_abs=tuple(payload["cross_stress_max_abs"]),
            cross_stress_rmse=tuple(payload["cross_stress_rmse"]),
            cross_descriptor_max_abs=tuple(payload["cross_descriptor_max_abs"]),
            cross_descriptor_rmse=tuple(payload["cross_descriptor_rmse"]),
            cross_selection_identical=tuple(payload["cross_selection_identical"]),
            policy_digest=str(payload["policy_digest"]),
            torch_deterministic_algorithms=payload.get("torch_deterministic_algorithms"),
            torch_deterministic_debug_mode=payload.get("torch_deterministic_debug_mode"),
            cudnn_deterministic=payload.get("cudnn_deterministic"),
            cublas_workspace_config=payload.get("cublas_workspace_config"),
            e3nn_self_force_p99_abs=tuple(payload.get("e3nn_self_force_p99_abs", ())),
            e3nn_self_force_p999_abs=tuple(payload.get("e3nn_self_force_p999_abs", ())),
            e3nn_self_force_above_threshold_count=tuple(payload.get("e3nn_self_force_above_threshold_count", ())),
            cueq_self_force_p99_abs=tuple(payload.get("cueq_self_force_p99_abs", ())),
            cueq_self_force_p999_abs=tuple(payload.get("cueq_self_force_p999_abs", ())),
            cueq_self_force_above_threshold_count=tuple(payload.get("cueq_self_force_above_threshold_count", ())),
            comparison_mode=("baseline" if is_legacy else str(payload.get("comparison_mode", "all_pairs"))),
            warmup_count=(0 if is_legacy else int(payload.get("warmup_count", 1))),
            e3nn_self_energy_max_abs=tuple(payload.get("e3nn_self_energy_max_abs", ())),
            e3nn_self_stress_max_abs=tuple(payload.get("e3nn_self_stress_max_abs", ())),
            e3nn_self_descriptor_max_abs=tuple(payload.get("e3nn_self_descriptor_max_abs", ())),
            cueq_self_energy_max_abs=tuple(payload.get("cueq_self_energy_max_abs", ())),
            cueq_self_stress_max_abs=tuple(payload.get("cueq_self_stress_max_abs", ())),
            cueq_self_descriptor_max_abs=tuple(payload.get("cueq_self_descriptor_max_abs", ())),
            e3nn_self_selection_identical=tuple(payload.get("e3nn_self_selection_identical", ())),
            cueq_self_selection_identical=tuple(payload.get("cueq_self_selection_identical", ())),
        )
        if not is_legacy and payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 repeatability-diagnostic digest mismatch.")
        return result



@dataclass(frozen=True, slots=True)
class TrainingAccelerationNoiseNormalizedParityPolicy:
    """Permanent TRAIN2 FP32 force parity policy normalized by measured self-noise."""

    repeat_count: int = 10
    warmup_count: int = 1
    stable_channel_abs_ceiling: float = 1.0e-6
    force_distribution_quantile: float = 99.0
    force_distribution_ratio_ceiling: float = 1.25
    force_max_self_factor: float = 1.5
    force_max_absolute_ceiling: float = 1.0e-4
    force_threshold: float = 1.0e-5

    def __post_init__(self) -> None:
        if self.repeat_count < 2:
            raise TrainingDataInputError("TRAIN2 noise-normalized parity repeat_count must be at least two.")
        if self.warmup_count < 1:
            raise TrainingDataInputError("TRAIN2 noise-normalized parity requires at least one discarded warm-up.")
        for name in (
            "stable_channel_abs_ceiling", "force_distribution_ratio_ceiling",
            "force_max_self_factor", "force_max_absolute_ceiling", "force_threshold",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"TRAIN2 noise-normalized parity {name} must be positive and finite.")
        if not 0.0 < float(self.force_distribution_quantile) < 100.0:
            raise TrainingDataInputError("TRAIN2 force_distribution_quantile must lie in (0,100).")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_POLICY_SCHEMA,
            "repeat_count": self.repeat_count,
            "warmup_count": self.warmup_count,
            "stable_channel_abs_ceiling": self.stable_channel_abs_ceiling,
            "force_distribution_quantile": self.force_distribution_quantile,
            "force_distribution_ratio_ceiling": self.force_distribution_ratio_ceiling,
            "force_max_self_factor": self.force_max_self_factor,
            "force_max_absolute_ceiling": self.force_max_absolute_ceiling,
            "force_threshold": self.force_threshold,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingAccelerationNoiseNormalizedParityPolicy":
        if payload.get("schema") != TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 noise-normalized parity policy schema.")
        result = cls(
            repeat_count=int(payload["repeat_count"]), warmup_count=int(payload["warmup_count"]),
            stable_channel_abs_ceiling=float(payload["stable_channel_abs_ceiling"]),
            force_distribution_quantile=float(payload["force_distribution_quantile"]),
            force_distribution_ratio_ceiling=float(payload["force_distribution_ratio_ceiling"]),
            force_max_self_factor=float(payload["force_max_self_factor"]),
            force_max_absolute_ceiling=float(payload["force_max_absolute_ceiling"]),
            force_threshold=float(payload["force_threshold"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TRAIN2 noise-normalized parity policy digest mismatch.")
        return result


def _ratio_or_none(numerator: float, denominator: float) -> float | None:
    if denominator > 0.0:
        return float(numerator / denominator)
    return 0.0 if numerator == 0.0 else None


@dataclass(frozen=True, slots=True)
class TrainingAccelerationNoiseNormalizedParityRecord:
    """Authorizing TRAIN2 FP32 parity record built from warm-up/all-pairs repeatability."""

    dtype: str
    policy_digest: str
    repeatability: TrainingAccelerationRepeatabilityDiagnostic
    stable_energy_max_abs: float
    stable_stress_max_abs: float
    stable_descriptor_max_abs: float
    force_rmse_self_envelope: float
    force_rmse_cross_stat: float
    force_rmse_ratio: float | None
    force_p99_self_envelope: float
    force_p99_cross_stat: float
    force_p99_ratio: float | None
    force_p999_self_envelope: float
    force_p999_cross_stat: float
    force_p999_ratio: float | None
    force_max_self_envelope: float
    force_max_cross: float
    force_max_limit: float
    selection_identical: bool
    passed: bool
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.dtype != "float32":
            raise TrainingDataInputError("Noise-normalized TRAIN2 parity is defined only for FP32.")
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(self, "failure_reasons", tuple(str(v) for v in self.failure_reasons))
        for name in (
            "stable_energy_max_abs", "stable_stress_max_abs", "stable_descriptor_max_abs",
            "force_rmse_self_envelope", "force_rmse_cross_stat",
            "force_p99_self_envelope", "force_p99_cross_stat",
            "force_p999_self_envelope", "force_p999_cross_stat",
            "force_max_self_envelope", "force_max_cross", "force_max_limit",
        ):
            value=float(getattr(self,name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"TRAIN2 noise-normalized parity {name} must be finite and non-negative.")
        for name in ("force_rmse_ratio", "force_p99_ratio", "force_p999_ratio"):
            value=getattr(self,name)
            if value is not None and (not np.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"TRAIN2 noise-normalized parity {name} must be non-negative when present.")
        if self.passed and self.failure_reasons:
            raise TrainingDataInputError("Passing TRAIN2 noise-normalized parity cannot carry failure reasons.")
        if self.passed and not self.selection_identical:
            raise TrainingDataInputError("Passing TRAIN2 noise-normalized parity requires identical selection.")

    @property
    def structure_count(self) -> int:
        return self.repeatability.structure_count

    @property
    def atom_count(self) -> int:
        return self.repeatability.atom_count

    @property
    def selection_identical_count(self) -> int:
        return int(sum(self.repeatability.cross_selection_identical))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_RECORD_SCHEMA,
            "dtype": self.dtype, "policy_digest": self.policy_digest,
            "repeatability": self.repeatability.to_dict(),
            "stable_energy_max_abs": self.stable_energy_max_abs,
            "stable_stress_max_abs": self.stable_stress_max_abs,
            "stable_descriptor_max_abs": self.stable_descriptor_max_abs,
            "force_rmse_self_envelope": self.force_rmse_self_envelope,
            "force_rmse_cross_stat": self.force_rmse_cross_stat, "force_rmse_ratio": self.force_rmse_ratio,
            "force_p99_self_envelope": self.force_p99_self_envelope,
            "force_p99_cross_stat": self.force_p99_cross_stat, "force_p99_ratio": self.force_p99_ratio,
            "force_p999_self_envelope": self.force_p999_self_envelope,
            "force_p999_cross_stat": self.force_p999_cross_stat, "force_p999_ratio": self.force_p999_ratio,
            "force_max_self_envelope": self.force_max_self_envelope,
            "force_max_cross": self.force_max_cross, "force_max_limit": self.force_max_limit,
            "selection_identical": self.selection_identical,
            "selection_identical_count": self.selection_identical_count,
            "passed": bool(self.passed), "failure_reasons": list(self.failure_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingAccelerationNoiseNormalizedParityRecord":
        if payload.get("schema") != TRAINING_ACCELERATION_NOISE_NORMALIZED_PARITY_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 noise-normalized parity record schema.")
        result=cls(
            dtype=str(payload["dtype"]), policy_digest=str(payload["policy_digest"]),
            repeatability=TrainingAccelerationRepeatabilityDiagnostic.from_dict(payload["repeatability"]),
            stable_energy_max_abs=float(payload["stable_energy_max_abs"]), stable_stress_max_abs=float(payload["stable_stress_max_abs"]),
            stable_descriptor_max_abs=float(payload["stable_descriptor_max_abs"]),
            force_rmse_self_envelope=float(payload["force_rmse_self_envelope"]), force_rmse_cross_stat=float(payload["force_rmse_cross_stat"]),
            force_rmse_ratio=None if payload.get("force_rmse_ratio") is None else float(payload["force_rmse_ratio"]),
            force_p99_self_envelope=float(payload["force_p99_self_envelope"]), force_p99_cross_stat=float(payload["force_p99_cross_stat"]),
            force_p99_ratio=None if payload.get("force_p99_ratio") is None else float(payload["force_p99_ratio"]),
            force_p999_self_envelope=float(payload["force_p999_self_envelope"]), force_p999_cross_stat=float(payload["force_p999_cross_stat"]),
            force_p999_ratio=None if payload.get("force_p999_ratio") is None else float(payload["force_p999_ratio"]),
            force_max_self_envelope=float(payload["force_max_self_envelope"]), force_max_cross=float(payload["force_max_cross"]),
            force_max_limit=float(payload["force_max_limit"]), selection_identical=bool(payload["selection_identical"]),
            passed=bool(payload["passed"]), failure_reasons=tuple(payload.get("failure_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 noise-normalized parity record digest mismatch.")
        return result


def build_training_noise_normalized_parity_record(
    repeatability: TrainingAccelerationRepeatabilityDiagnostic,
    *, policy: TrainingAccelerationNoiseNormalizedParityPolicy | None = None,
) -> TrainingAccelerationNoiseNormalizedParityRecord:
    """Reduce DIAG3 all-pairs evidence into the permanent FP32 TRAIN2 authority."""
    active = TrainingAccelerationNoiseNormalizedParityPolicy() if policy is None else policy
    if repeatability.dtype != "float32" or repeatability.comparison_mode != "all_pairs":
        raise TrainingDataInputError("Permanent TRAIN2 noise-normalized parity requires FP32 all-pairs evidence.")
    if repeatability.repeat_count != active.repeat_count or repeatability.warmup_count != active.warmup_count:
        raise TrainingDataInputError("TRAIN2 repeatability evidence does not match the frozen repeat/warm-up contract.")
    if not repeatability.self_detail_available or not repeatability.self_channel_detail_available:
        raise TrainingDataInputError("TRAIN2 noise-normalized parity requires complete DIAG3 self-tail/channel evidence.")
    q=float(active.force_distribution_quantile)
    def qv(values: Sequence[float]) -> float:
        return float(np.percentile(np.asarray(tuple(values), dtype=np.float64), q))
    def env(a: Sequence[float], b: Sequence[float]) -> float:
        return max(qv(a), qv(b))
    frmse_self=env(repeatability.e3nn_self_force_rmse, repeatability.cueq_self_force_rmse)
    frmse_cross=qv(repeatability.cross_force_rmse)
    fp99_self=env(repeatability.e3nn_self_force_p99_abs, repeatability.cueq_self_force_p99_abs)
    fp99_cross=qv(repeatability.cross_force_p99_abs)
    fp999_self=env(repeatability.e3nn_self_force_p999_abs, repeatability.cueq_self_force_p999_abs)
    fp999_cross=qv(repeatability.cross_force_p999_abs)
    fmax_self=max(max(repeatability.e3nn_self_force_max_abs), max(repeatability.cueq_self_force_max_abs))
    fmax_cross=max(repeatability.cross_force_max_abs)
    fmax_limit=min(active.force_max_absolute_ceiling, active.force_max_self_factor*fmax_self)
    ratios=(
        _ratio_or_none(frmse_cross, frmse_self),
        _ratio_or_none(fp99_cross, fp99_self),
        _ratio_or_none(fp999_cross, fp999_self),
    )
    stable=(max(repeatability.cross_energy_max_abs), max(repeatability.cross_stress_max_abs), max(repeatability.cross_descriptor_max_abs))
    selection=bool(all(repeatability.cross_selection_identical) and all(repeatability.e3nn_self_selection_identical) and all(repeatability.cueq_self_selection_identical))
    failures=[]
    for label,value in zip(("energy","stress","descriptor"), stable, strict=True):
        if value > active.stable_channel_abs_ceiling:
            failures.append(f"{label}_max_abs={value:.3e}>{active.stable_channel_abs_ceiling:.3e}")
    for label,ratio in zip(("Frmse","Fp99","Fp99.9"), ratios, strict=True):
        if ratio is None or ratio > active.force_distribution_ratio_ceiling:
            failures.append(f"{label}_p{q:g}_ratio={'inf' if ratio is None else f'{ratio:.3f}'}>{active.force_distribution_ratio_ceiling:.3f}")
    if fmax_cross > fmax_limit:
        failures.append(f"Fmax={fmax_cross:.3e}>{fmax_limit:.3e}")
    if not selection:
        failures.append("selection_not_identical")
    return TrainingAccelerationNoiseNormalizedParityRecord(
        dtype="float32", policy_digest=active.policy_digest, repeatability=repeatability,
        stable_energy_max_abs=stable[0], stable_stress_max_abs=stable[1], stable_descriptor_max_abs=stable[2],
        force_rmse_self_envelope=frmse_self, force_rmse_cross_stat=frmse_cross, force_rmse_ratio=ratios[0],
        force_p99_self_envelope=fp99_self, force_p99_cross_stat=fp99_cross, force_p99_ratio=ratios[1],
        force_p999_self_envelope=fp999_self, force_p999_cross_stat=fp999_cross, force_p999_ratio=ratios[2],
        force_max_self_envelope=fmax_self, force_max_cross=fmax_cross, force_max_limit=fmax_limit,
        selection_identical=selection, passed=not failures, failure_reasons=tuple(failures),
    )

@dataclass(frozen=True, slots=True)
class TrainingAccelerationDeterministicControlDiagnostic:
    """Non-authorizing isolated deterministic-control probe result."""

    status: str
    repeat_count: int
    dtype: str
    cublas_workspace_config: str
    repeatability: TrainingAccelerationRepeatabilityDiagnostic | None = None
    error_type: str | None = None
    error_message: str | None = None
    worker_stderr_tail: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"completed", "unsupported_or_failed"}:
            raise TrainingDataInputError("Invalid deterministic-control diagnostic status.")
        if self.repeat_count < 2:
            raise TrainingDataInputError("Deterministic-control repeat_count must be at least two.")
        if self.dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Deterministic-control dtype must be float32 or float64.")
        if self.status == "completed" and self.repeatability is None:
            raise TrainingDataInputError("Completed deterministic-control diagnostic requires repeatability evidence.")
        if self.status == "unsupported_or_failed" and self.repeatability is not None:
            raise TrainingDataInputError("Failed deterministic-control diagnostic cannot carry repeatability evidence.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_ACCELERATION_DETERMINISTIC_CONTROL_DIAGNOSTIC_SCHEMA,
            "status": self.status,
            "repeat_count": self.repeat_count,
            "dtype": self.dtype,
            "cublas_workspace_config": self.cublas_workspace_config,
            "repeatability": None if self.repeatability is None else self.repeatability.to_dict(),
            "error_type": self.error_type,
            "error_message": self.error_message,
            "worker_stderr_tail": self.worker_stderr_tail,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingAccelerationDeterministicControlDiagnostic":
        if payload.get("schema") != TRAINING_ACCELERATION_DETERMINISTIC_CONTROL_DIAGNOSTIC_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 deterministic-control diagnostic schema.")
        nested = payload.get("repeatability")
        result = cls(
            status=str(payload["status"]), repeat_count=int(payload["repeat_count"]), dtype=str(payload["dtype"]),
            cublas_workspace_config=str(payload["cublas_workspace_config"]),
            repeatability=(None if nested is None else TrainingAccelerationRepeatabilityDiagnostic.from_dict(nested)),
            error_type=None if payload.get("error_type") is None else str(payload["error_type"]),
            error_message=None if payload.get("error_message") is None else str(payload["error_message"]),
            worker_stderr_tail=None if payload.get("worker_stderr_tail") is None else str(payload["worker_stderr_tail"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 deterministic-control diagnostic digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AccelerationRealizationRecord:
    """Frozen accelerator implementation for inference and training.

    MACE 0.3.16 supports CuEq+OpenEquivariance hybrid conversion in
    ``MACECalculator`` but its trainer explicitly disables OEQ when CuEq is
    enabled.  The two execution phases are therefore recorded separately.
    """

    requested_backend: str
    resolved_kernel_mode: str
    training_kernel_mode: str
    device: str
    dtype: str
    foundation_inference_identity_digest: str
    mace_version: str | None
    cueq_versions: tuple[tuple[str, str | None], ...] = ()
    oeq_version: str | None = None
    inference_parity_record_digest: str | None = None
    training_parity_record_digest: str | None = None
    qualified: bool = False
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        backend = MaceAccelerationBackend(self.requested_backend)
        inference_mode = MaceAccelerationKernelMode(self.resolved_kernel_mode)
        training_mode = MaceAccelerationKernelMode(self.training_kernel_mode)
        if inference_mode.backend is not backend or training_mode.backend is not backend:
            raise TrainingDataInputError("Acceleration kernel mode does not match requested backend.")
        if backend is MaceAccelerationBackend.E3NN:
            if inference_mode is not MaceAccelerationKernelMode.E3NN or training_mode is not MaceAccelerationKernelMode.E3NN:
                raise TrainingDataInputError("e3nn realization must use e3nn for inference and training.")
        elif self.qualified:
            if training_mode is not MaceAccelerationKernelMode.CUEQ_PURE:
                raise TrainingDataInputError(
                    "MACE 0.3.16 CuEq production training must bind the pure-CuEq training kernel."
                )
            if self.inference_parity_record_digest is None or self.training_parity_record_digest is None:
                raise TrainingDataInputError(
                    "Qualified CuEq realization requires both inference and pure-training parity evidence."
                )
        if self.device not in {"cpu", "cuda"} or self.dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Acceleration realization device/dtype is unsupported.")
        object.__setattr__(self, "foundation_inference_identity_digest", validate_digest(self.foundation_inference_identity_digest, name="foundation_inference_identity_digest"))
        object.__setattr__(self, "cueq_versions", tuple((str(a), None if b is None else str(b)) for a, b in self.cueq_versions))
        for name in ("inference_parity_record_digest", "training_parity_record_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.qualified and self.failure_reason:
            raise TrainingDataInputError("Qualified acceleration realization cannot carry a failure reason.")

    @property
    def mode(self) -> MaceAccelerationKernelMode:
        return MaceAccelerationKernelMode(self.resolved_kernel_mode)

    @property
    def training_mode(self) -> MaceAccelerationKernelMode:
        return MaceAccelerationKernelMode(self.training_kernel_mode)

    def calculator_kwargs(self) -> dict[str, Any]:
        if not self.qualified:
            raise TrainingDataInputError("Unqualified acceleration realization cannot construct a calculator.")
        return self.mode.calculator_kwargs()

    def training_config(self, *, only_cueq: bool = False) -> dict[str, Any]:
        if not self.qualified:
            raise TrainingDataInputError("Unqualified acceleration realization cannot authorize training.")
        mode = self.training_mode
        return {
            "enable_cueq": mode is MaceAccelerationKernelMode.CUEQ_PURE,
            "enable_oeq": False,
            "only_cueq": bool(only_cueq),
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ACCELERATION_REALIZATION_SCHEMA,
            "requested_backend": self.requested_backend,
            "resolved_kernel_mode": self.resolved_kernel_mode,
            "training_kernel_mode": self.training_kernel_mode,
            "device": self.device,
            "dtype": self.dtype,
            "foundation_inference_identity_digest": self.foundation_inference_identity_digest,
            "mace_version": self.mace_version,
            "cueq_versions": [list(v) for v in self.cueq_versions],
            "oeq_version": self.oeq_version,
            "inference_parity_record_digest": self.inference_parity_record_digest,
            "training_parity_record_digest": self.training_parity_record_digest,
            "qualified": bool(self.qualified),
            "failure_reason": self.failure_reason,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AccelerationRealizationRecord":
        if payload.get("schema") != ACCELERATION_REALIZATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported acceleration-realization schema.")
        required = (
            "requested_backend", "resolved_kernel_mode", "training_kernel_mode",
            "device", "dtype", "foundation_inference_identity_digest",
        )
        missing = tuple(name for name in required if name not in payload)
        if missing:
            raise TrainingDataSerializationError(
                f"Acceleration-realization payload is incomplete: missing {missing}."
            )
        result = cls(
            requested_backend=str(payload["requested_backend"]),
            resolved_kernel_mode=str(payload["resolved_kernel_mode"]),
            training_kernel_mode=str(payload["training_kernel_mode"]),
            device=str(payload["device"]), dtype=str(payload["dtype"]),
            foundation_inference_identity_digest=str(payload["foundation_inference_identity_digest"]),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            cueq_versions=tuple((str(v[0]), None if v[1] is None else str(v[1])) for v in payload.get("cueq_versions", ())),
            oeq_version=None if payload.get("oeq_version") is None else str(payload["oeq_version"]),
            inference_parity_record_digest=(
                None if payload.get("inference_parity_record_digest") is None
                else str(payload["inference_parity_record_digest"])
            ),
            training_parity_record_digest=(
                None if payload.get("training_parity_record_digest") is None
                else str(payload["training_parity_record_digest"])
            ),
            qualified=bool(payload.get("qualified", False)),
            failure_reason=None if payload.get("failure_reason") is None else str(payload["failure_reason"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Acceleration-realization digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingAccelerationRealizationRecord:
    """Frozen TRAIN2-only accelerator realization.

    This record deliberately carries no source-foundation inference authority.
    It binds only the selected training checkpoint and the pure training kernel,
    so a qualified CuEq TRAIN2 path cannot implicitly authorize CuEq for DATA6,
    pseudolabel generation, checkpoint evaluation, or physical verification.
    """

    requested_backend: str
    training_kernel_mode: str
    device: str
    dtype: str
    training_checkpoint_reference: str
    training_checkpoint_sha256: str
    selected_head_qualification_digest: str | None
    mace_version: str | None
    cueq_versions: tuple[tuple[str, str | None], ...] = ()
    training_parity_record_digest: str | None = None
    qualified: bool = False
    failure_reason: str | None = None

    def __post_init__(self) -> None:
        backend = MaceAccelerationBackend(self.requested_backend)
        mode = MaceAccelerationKernelMode(self.training_kernel_mode)
        if mode.backend is not backend:
            raise TrainingDataInputError("TRAIN2 acceleration kernel mode does not match requested backend.")
        if backend is MaceAccelerationBackend.E3NN and mode is not MaceAccelerationKernelMode.E3NN:
            raise TrainingDataInputError("e3nn TRAIN2 realization must use the e3nn training kernel.")
        if backend is MaceAccelerationBackend.CUEQ and self.qualified:
            if mode is not MaceAccelerationKernelMode.CUEQ_PURE:
                raise TrainingDataInputError("Qualified CuEq TRAIN2 realization must use pure CuEq.")
            if self.training_parity_record_digest is None:
                raise TrainingDataInputError("Qualified CuEq TRAIN2 realization requires parity evidence.")
        if self.device not in {"cpu", "cuda"} or self.dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("TRAIN2 acceleration realization device/dtype is unsupported.")
        object.__setattr__(
            self, "training_checkpoint_sha256",
            validate_digest(self.training_checkpoint_sha256, name="training_checkpoint_sha256"),
        )
        if self.selected_head_qualification_digest is not None:
            object.__setattr__(
                self, "selected_head_qualification_digest",
                validate_digest(self.selected_head_qualification_digest, name="selected_head_qualification_digest"),
            )
        if self.training_parity_record_digest is not None:
            object.__setattr__(
                self, "training_parity_record_digest",
                validate_digest(self.training_parity_record_digest, name="training_parity_record_digest"),
            )
        object.__setattr__(
            self, "cueq_versions",
            tuple((str(a), None if b is None else str(b)) for a, b in self.cueq_versions),
        )
        if self.qualified and self.failure_reason:
            raise TrainingDataInputError("Qualified TRAIN2 acceleration realization cannot carry a failure reason.")

    @property
    def training_mode(self) -> MaceAccelerationKernelMode:
        return MaceAccelerationKernelMode(self.training_kernel_mode)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_ACCELERATION_REALIZATION_SCHEMA,
            "requested_backend": self.requested_backend,
            "training_kernel_mode": self.training_kernel_mode,
            "device": self.device,
            "dtype": self.dtype,
            "training_checkpoint_reference": self.training_checkpoint_reference,
            "training_checkpoint_sha256": self.training_checkpoint_sha256,
            "selected_head_qualification_digest": self.selected_head_qualification_digest,
            "mace_version": self.mace_version,
            "cueq_versions": [list(v) for v in self.cueq_versions],
            "training_parity_record_digest": self.training_parity_record_digest,
            "qualified": bool(self.qualified),
            "failure_reason": self.failure_reason,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingAccelerationRealizationRecord":
        if payload.get("schema") != TRAINING_ACCELERATION_REALIZATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TRAIN2 acceleration-realization schema.")
        result = cls(
            requested_backend=str(payload["requested_backend"]),
            training_kernel_mode=str(payload["training_kernel_mode"]),
            device=str(payload["device"]),
            dtype=str(payload["dtype"]),
            training_checkpoint_reference=str(payload["training_checkpoint_reference"]),
            training_checkpoint_sha256=str(payload["training_checkpoint_sha256"]),
            selected_head_qualification_digest=(
                None if payload.get("selected_head_qualification_digest") is None
                else str(payload["selected_head_qualification_digest"])
            ),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            cueq_versions=tuple(
                (str(v[0]), None if v[1] is None else str(v[1]))
                for v in payload.get("cueq_versions", ())
            ),
            training_parity_record_digest=(
                None if payload.get("training_parity_record_digest") is None
                else str(payload["training_parity_record_digest"])
            ),
            qualified=bool(payload.get("qualified", False)),
            failure_reason=None if payload.get("failure_reason") is None else str(payload["failure_reason"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TRAIN2 acceleration-realization digest mismatch.")
        return result


def _rmse_difference(reference: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    a = np.asarray(reference, dtype=np.float64)
    b = np.asarray(candidate, dtype=np.float64)
    if a.shape != b.shape or a.size == 0:
        raise TrainingDataInputError("Acceleration parity arrays must have the same non-empty shape.")
    delta = b - a
    return float(np.max(np.abs(delta))), float(np.sqrt(np.mean(delta * delta)))


def _selection_fingerprint(matrix: np.ndarray, *, fraction: float, tolerance: float) -> tuple[str, ...]:
    from .selection import _fps_order_matrix

    X = np.asarray(matrix, dtype=np.float64)
    uids = tuple(f"q{index:04d}" for index in range(X.shape[0]))
    limit = max(1, min(len(uids), int(np.ceil(len(uids) * fraction))))
    return tuple(_fps_order_matrix(uids, X, (), tolerance, limit=limit))


def _evaluate_acceleration_calculator(calculator: Any, structures: Sequence[Any]) -> dict[str, Any]:
    energies: list[float] = []
    forces: list[np.ndarray] = []
    stresses: list[np.ndarray] = []
    descriptors: list[np.ndarray] = []
    atom_count = 0
    for source in structures:
        atoms = source.copy()
        atoms.calc = calculator
        if len(atoms) <= 0:
            raise TrainingDataInputError("Acceleration qualification does not support empty structures.")
        energies.append(float(atoms.get_potential_energy()) / float(len(atoms)))
        forces.append(np.asarray(atoms.get_forces(), dtype=np.float64).reshape(-1))
        stresses.append(np.asarray(atoms.get_stress(voigt=True), dtype=np.float64).reshape(-1))
        raw = np.asarray(calculator.get_descriptors(atoms, invariants_only=True), dtype=np.float64)
        if raw.ndim != 2 or raw.shape[0] != len(atoms) or not np.all(np.isfinite(raw)):
            raise TrainingDataInputError("Acceleration qualification received invalid MACE descriptors.")
        descriptors.append(np.mean(raw, axis=0))
        atom_count += len(atoms)
    return {
        "energy": np.asarray(energies, dtype=np.float64),
        "forces": np.concatenate(forces),
        "stress": np.concatenate(stresses),
        "descriptors": np.vstack(descriptors),
        "atom_count": atom_count,
    }


def compare_mace_acceleration_calculators(
    reference_calculator: Any,
    candidate_calculator: Any,
    structures: Sequence[Any],
    *,
    candidate_mode: MaceAccelerationKernelMode | str,
    dtype: str,
    policy: MaceAccelerationParityPolicy | None = None,
) -> MaceAccelerationParityRecord:
    """Compare one accelerated calculator against the canonical e3nn reference."""

    if not structures:
        raise TrainingDataInputError("Acceleration qualification requires at least one structure.")
    active = MaceAccelerationParityPolicy() if policy is None else policy
    mode = MaceAccelerationKernelMode(candidate_mode)
    if mode is MaceAccelerationKernelMode.E3NN:
        raise TrainingDataInputError("Acceleration parity candidate must be a CuEq realization.")
    ref = _evaluate_acceleration_calculator(reference_calculator, structures)
    cand = _evaluate_acceleration_calculator(candidate_calculator, structures)
    emax, ermse = _rmse_difference(ref["energy"], cand["energy"])
    fmax, frmse = _rmse_difference(ref["forces"], cand["forces"])
    smax, srmse = _rmse_difference(ref["stress"], cand["stress"])
    dmax, drmse = _rmse_difference(ref["descriptors"], cand["descriptors"])
    rtol, atol = active.tolerance(dtype)
    numerical = all(
        np.allclose(cand[key], ref[key], rtol=rtol, atol=atol)
        for key in ("energy", "forces", "stress", "descriptors")
    )
    ref_selection = _selection_fingerprint(
        ref["descriptors"], fraction=active.selection_fraction, tolerance=active.fps_tie_tolerance
    )
    cand_selection = _selection_fingerprint(
        cand["descriptors"], fraction=active.selection_fraction, tolerance=active.fps_tie_tolerance
    )
    return MaceAccelerationParityRecord(
        reference_mode=MaceAccelerationKernelMode.E3NN.value,
        candidate_mode=mode.value,
        dtype=dtype,
        structure_count=len(structures), atom_count=int(ref["atom_count"]),
        energy_max_abs=emax, energy_rmse=ermse,
        force_max_abs=fmax, force_rmse=frmse,
        stress_max_abs=smax, stress_rmse=srmse,
        descriptor_max_abs=dmax, descriptor_rmse=drmse,
        reference_selection=ref_selection, candidate_selection=cand_selection,
        policy_digest=active.policy_digest,
        passed=bool(numerical and ref_selection == cand_selection),
    )


def _repeatability_pair_metrics(reference: Mapping[str, Any], candidate: Mapping[str, Any], *, force_threshold: float) -> dict[str, Any]:
    emax, ermse = _rmse_difference(reference["energy"], candidate["energy"])
    fmax, frmse = _rmse_difference(reference["forces"], candidate["forces"])
    smax, srmse = _rmse_difference(reference["stress"], candidate["stress"])
    dmax, drmse = _rmse_difference(reference["descriptors"], candidate["descriptors"])
    force_delta = np.abs(np.asarray(candidate["forces"], dtype=np.float64) - np.asarray(reference["forces"], dtype=np.float64))
    return {
        "energy_max_abs": emax, "energy_rmse": ermse,
        "force_max_abs": fmax, "force_rmse": frmse,
        "force_p99_abs": float(np.percentile(force_delta, 99.0)),
        "force_p999_abs": float(np.percentile(force_delta, 99.9)),
        "force_above_threshold_count": int(np.count_nonzero(force_delta > force_threshold)),
        "force_component_count": int(force_delta.size),
        "stress_max_abs": smax, "stress_rmse": srmse,
        "descriptor_max_abs": dmax, "descriptor_rmse": drmse,
    }


def diagnose_mace_acceleration_repeatability(
    reference_calculator: Any,
    candidate_calculator: Any,
    structures: Sequence[Any],
    *,
    dtype: str,
    policy: MaceAccelerationParityPolicy | None = None,
    repeat_count: int = 10,
    force_threshold: float = 1.0e-5,
    warmup_count: int = 1,
) -> TrainingAccelerationRepeatabilityDiagnostic:
    """Measure post-warm-up all-pairs same/cross-backend variability.

    Each backend is explicitly warmed up and the warm-up output is discarded.
    ``repeat_count`` post-warm-up outputs are then retained.  Same-backend
    statistics use all N(N-1)/2 pairs and cross-backend statistics use all N^2
    pairs, eliminating dependence on an arbitrary baseline evaluation.
    """

    if not structures:
        raise TrainingDataInputError("TRAIN2 repeatability diagnostic requires at least one structure.")
    if repeat_count < 2:
        raise TrainingDataInputError("TRAIN2 repeatability diagnostic repeat_count must be at least two.")
    if warmup_count < 1:
        raise TrainingDataInputError("TRAIN2 all-pairs diagnostic requires at least one discarded warm-up.")
    if not np.isfinite(force_threshold) or force_threshold <= 0.0:
        raise TrainingDataInputError("TRAIN2 repeatability diagnostic force_threshold must be positive and finite.")
    active = MaceAccelerationParityPolicy() if policy is None else policy

    # Explicitly discard warm-up evaluations for each backend.  This removes
    # first-call graph/kernel initialization effects from the measured corpus.
    for _ in range(int(warmup_count)):
        warm_ref = _evaluate_acceleration_calculator(reference_calculator, structures)
        warm_cand = _evaluate_acceleration_calculator(candidate_calculator, structures)
        if int(warm_ref["atom_count"]) != int(warm_cand["atom_count"]):
            raise TrainingDataInputError("TRAIN2 repeatability diagnostic backend atom counts differ during warm-up.")

    refs: list[dict[str, Any]] = []
    cands: list[dict[str, Any]] = []
    atom_count = 0
    for _run in range(repeat_count):
        ref = _evaluate_acceleration_calculator(reference_calculator, structures)
        cand = _evaluate_acceleration_calculator(candidate_calculator, structures)
        atom_count = int(ref["atom_count"])
        if int(cand["atom_count"]) != atom_count:
            raise TrainingDataInputError("TRAIN2 repeatability diagnostic backend atom counts differ.")
        refs.append(ref)
        cands.append(cand)

    def selection(record: Mapping[str, Any]) -> tuple[str, ...]:
        return _selection_fingerprint(
            record["descriptors"], fraction=active.selection_fraction, tolerance=active.fps_tie_tolerance
        )

    ref_selections = [selection(item) for item in refs]
    cand_selections = [selection(item) for item in cands]
    e3nn_self: list[dict[str, Any]] = []
    cueq_self: list[dict[str, Any]] = []
    e3nn_self_selection: list[bool] = []
    cueq_self_selection: list[bool] = []
    for i, j in itertools.combinations(range(repeat_count), 2):
        e3nn_self.append(_repeatability_pair_metrics(refs[i], refs[j], force_threshold=force_threshold))
        cueq_self.append(_repeatability_pair_metrics(cands[i], cands[j], force_threshold=force_threshold))
        e3nn_self_selection.append(ref_selections[i] == ref_selections[j])
        cueq_self_selection.append(cand_selections[i] == cand_selections[j])

    cross: list[dict[str, Any]] = []
    cross_selection: list[bool] = []
    for i in range(repeat_count):
        for j in range(repeat_count):
            cross.append(_repeatability_pair_metrics(refs[i], cands[j], force_threshold=force_threshold))
            cross_selection.append(ref_selections[i] == cand_selections[j])

    torch_deterministic_algorithms: bool | None = None
    torch_deterministic_debug_mode: int | None = None
    cudnn_deterministic: bool | None = None
    try:
        import torch
        torch_deterministic_algorithms = bool(torch.are_deterministic_algorithms_enabled())
        torch_deterministic_debug_mode = int(torch.get_deterministic_debug_mode())
        cudnn_deterministic = bool(torch.backends.cudnn.deterministic)
    except Exception:
        pass

    def values(items: Sequence[Mapping[str, Any]], key: str) -> tuple[Any, ...]:
        return tuple(item[key] for item in items)

    return TrainingAccelerationRepeatabilityDiagnostic(
        repeat_count=repeat_count, dtype=dtype, structure_count=len(structures), atom_count=atom_count,
        force_threshold=float(force_threshold), comparison_mode="all_pairs", warmup_count=int(warmup_count),
        e3nn_self_force_max_abs=values(e3nn_self, "force_max_abs"),
        e3nn_self_force_rmse=values(e3nn_self, "force_rmse"),
        cueq_self_force_max_abs=values(cueq_self, "force_max_abs"),
        cueq_self_force_rmse=values(cueq_self, "force_rmse"),
        cross_energy_max_abs=values(cross, "energy_max_abs"), cross_energy_rmse=values(cross, "energy_rmse"),
        cross_force_max_abs=values(cross, "force_max_abs"), cross_force_rmse=values(cross, "force_rmse"),
        cross_force_p99_abs=values(cross, "force_p99_abs"), cross_force_p999_abs=values(cross, "force_p999_abs"),
        cross_force_above_threshold_count=values(cross, "force_above_threshold_count"),
        cross_force_component_count=int(cross[0]["force_component_count"]),
        cross_stress_max_abs=values(cross, "stress_max_abs"), cross_stress_rmse=values(cross, "stress_rmse"),
        cross_descriptor_max_abs=values(cross, "descriptor_max_abs"), cross_descriptor_rmse=values(cross, "descriptor_rmse"),
        cross_selection_identical=tuple(cross_selection), policy_digest=active.policy_digest,
        torch_deterministic_algorithms=torch_deterministic_algorithms,
        torch_deterministic_debug_mode=torch_deterministic_debug_mode,
        cudnn_deterministic=cudnn_deterministic, cublas_workspace_config=os.environ.get("CUBLAS_WORKSPACE_CONFIG"),
        e3nn_self_force_p99_abs=values(e3nn_self, "force_p99_abs"),
        e3nn_self_force_p999_abs=values(e3nn_self, "force_p999_abs"),
        e3nn_self_force_above_threshold_count=values(e3nn_self, "force_above_threshold_count"),
        cueq_self_force_p99_abs=values(cueq_self, "force_p99_abs"),
        cueq_self_force_p999_abs=values(cueq_self, "force_p999_abs"),
        cueq_self_force_above_threshold_count=values(cueq_self, "force_above_threshold_count"),
        e3nn_self_energy_max_abs=values(e3nn_self, "energy_max_abs"),
        e3nn_self_stress_max_abs=values(e3nn_self, "stress_max_abs"),
        e3nn_self_descriptor_max_abs=values(e3nn_self, "descriptor_max_abs"),
        cueq_self_energy_max_abs=values(cueq_self, "energy_max_abs"),
        cueq_self_stress_max_abs=values(cueq_self, "stress_max_abs"),
        cueq_self_descriptor_max_abs=values(cueq_self, "descriptor_max_abs"),
        e3nn_self_selection_identical=tuple(e3nn_self_selection),
        cueq_self_selection_identical=tuple(cueq_self_selection),
    )


@mace_runtime_warning_handled("MACE TRAIN2 acceleration repeatability diagnostic")
def diagnose_training_acceleration_repeatability(
    *,
    training_model_path: str | Path,
    training_head: str,
    structures: Sequence[Any],
    device: str,
    dtype: str,
    parity_policy: MaceAccelerationParityPolicy | None = None,
    repeat_count: int = 10,
    force_threshold: float = 1.0e-5,
) -> TrainingAccelerationRepeatabilityDiagnostic:
    """Construct e3nn/pure-CuEq calculators and measure repeated TRAIN2 numerical variability."""

    from mace.calculators import MACECalculator

    path = Path(training_model_path).expanduser().resolve()
    if not path.is_file():
        raise TrainingDataInputError(f"TRAIN2 diagnostic model does not exist: {path}")
    reference = MACECalculator(
        model_paths=str(path), head=training_head, device=device,
        default_dtype=dtype, enable_cueq=False, enable_oeq=False,
    )
    candidate = MACECalculator(
        model_paths=str(path), head=training_head, device=device,
        default_dtype=dtype, **MaceAccelerationKernelMode.CUEQ_PURE.calculator_kwargs(),
    )
    return diagnose_mace_acceleration_repeatability(
        reference, candidate, structures, dtype=dtype, policy=parity_policy,
        repeat_count=repeat_count, force_threshold=force_threshold, warmup_count=1,
    )


def diagnose_training_acceleration_deterministic_control(
    *,
    training_model_path: str | Path,
    training_head: str,
    structures: Sequence[Any],
    device: str,
    dtype: str,
    parity_policy: MaceAccelerationParityPolicy | None = None,
    repeat_count: int = 10,
    force_threshold: float = 1.0e-5,
    timeout_seconds: float = 900.0,
    cublas_workspace_config: str = ":4096:8",
) -> TrainingAccelerationDeterministicControlDiagnostic:
    """Run the repeatability probe in a fresh process with deterministic controls enabled."""

    if not structures:
        raise TrainingDataInputError("TRAIN2 deterministic-control diagnostic requires at least one structure.")
    active = MaceAccelerationParityPolicy() if parity_policy is None else parity_policy
    model_path = Path(training_model_path).expanduser().resolve()
    if not model_path.is_file():
        raise TrainingDataInputError(f"TRAIN2 diagnostic model does not exist: {model_path}")
    worker = Path(__file__).with_name("_repeatability_deterministic_worker.py")
    if not worker.is_file():
        raise TrainingDataInputError(f"TRAIN2 deterministic-control worker is missing: {worker}")

    try:
        from ase import Atoms
        from ase.io import write as ase_write
    except Exception as exc:
        return TrainingAccelerationDeterministicControlDiagnostic(
            status="unsupported_or_failed", repeat_count=repeat_count, dtype=dtype,
            cublas_workspace_config=cublas_workspace_config,
            error_type=type(exc).__name__, error_message=f"ASE unavailable: {exc}",
        )

    with tempfile.TemporaryDirectory(prefix="mdstats-train2-deterministic-") as tmpdir_text:
        tmpdir = Path(tmpdir_text)
        structures_path = tmpdir / "probe.extxyz"
        policy_path = tmpdir / "policy.json"
        output_path = tmpdir / "result.json"
        minimal = [
            Atoms(
                numbers=np.asarray(source.numbers, dtype=int),
                positions=np.asarray(source.positions, dtype=float),
                cell=np.asarray(source.cell.array, dtype=float),
                pbc=np.asarray(source.pbc, dtype=bool),
            )
            for source in structures
        ]
        ase_write(structures_path, minimal, format="extxyz")
        policy_path.write_text(json.dumps(active.to_dict(), sort_keys=True), encoding="utf-8")
        env = os.environ.copy()
        env["CUBLAS_WORKSPACE_CONFIG"] = cublas_workspace_config
        package_root = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = package_root + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        command = [
            sys.executable, str(worker),
            "--model", str(model_path), "--head", str(training_head),
            "--structures", str(structures_path), "--policy", str(policy_path),
            "--output", str(output_path), "--device", str(device), "--dtype", str(dtype),
            "--repeat-count", str(int(repeat_count)), "--force-threshold", repr(float(force_threshold)),
        ]
        try:
            completed = subprocess.run(
                command, env=env, capture_output=True, text=True,
                timeout=float(timeout_seconds), check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TrainingAccelerationDeterministicControlDiagnostic(
                status="unsupported_or_failed", repeat_count=repeat_count, dtype=dtype,
                cublas_workspace_config=cublas_workspace_config,
                error_type="TimeoutExpired", error_message=f"deterministic-control worker exceeded {timeout_seconds:g} s",
                worker_stderr_tail=(exc.stderr[-2000:] if isinstance(exc.stderr, str) else None),
            )
        payload: dict[str, Any] = {}
        if output_path.is_file():
            try:
                payload = json.loads(output_path.read_text(encoding="utf-8"))
            except Exception:
                payload = {}
        if completed.returncode == 0 and payload.get("status") == "completed":
            nested = TrainingAccelerationRepeatabilityDiagnostic.from_dict(payload["repeatability"])
            return TrainingAccelerationDeterministicControlDiagnostic(
                status="completed", repeat_count=repeat_count, dtype=dtype,
                cublas_workspace_config=cublas_workspace_config, repeatability=nested,
                worker_stderr_tail=(completed.stderr[-2000:] or None),
            )
        return TrainingAccelerationDeterministicControlDiagnostic(
            status="unsupported_or_failed", repeat_count=repeat_count, dtype=dtype,
            cublas_workspace_config=cublas_workspace_config,
            error_type=str(payload.get("error_type") or f"worker_exit_{completed.returncode}"),
            error_message=str(payload.get("error_message") or "deterministic-control worker did not complete"),
            worker_stderr_tail=(completed.stderr[-2000:] or None),
        )


def acceleration_realization_from_e3nn(
    *,
    foundation_inference_identity: Any,
    device: str,
    dtype: str,
    mace_version: str | None,
) -> AccelerationRealizationRecord:
    """Create the deterministic reference realization; no accelerator discovery is involved."""

    return AccelerationRealizationRecord(
        requested_backend=MaceAccelerationBackend.E3NN.value,
        resolved_kernel_mode=MaceAccelerationKernelMode.E3NN.value,
        training_kernel_mode=MaceAccelerationKernelMode.E3NN.value,
        device=device,
        dtype=dtype,
        foundation_inference_identity_digest=foundation_inference_identity.content_digest,
        mace_version=mace_version,
        qualified=True,
    )



@mace_runtime_warning_handled("MACE e3nn acceleration qualification")
def qualify_e3nn_realization(
    *,
    model_path: str | Path,
    head: str,
    structures: Sequence[Any],
    device: str,
    dtype: str,
    foundation_potential_digest: str,
    adapter_version: str,
) -> tuple[AccelerationRealizationRecord, Any]:
    """Qualify the explicit e3nn reference path with real E/F/stress/descriptors."""

    from importlib import metadata as importlib_metadata
    from .foundation import FoundationInferenceIdentity
    from mace.calculators import MACECalculator

    if not structures:
        raise TrainingDataInputError("e3nn qualification requires a deterministic non-empty structure corpus.")
    try:
        mace_version = str(importlib_metadata.version("mace-torch"))
    except Exception:
        try:
            import mace
            mace_version = str(getattr(mace, "__version__", "unknown"))
        except Exception:
            mace_version = "unknown"
    inference = FoundationInferenceIdentity(
        foundation_potential_digest=foundation_potential_digest,
        default_dtype=dtype,
        backend=MaceAccelerationBackend.E3NN.value,
        resolved_kernel_mode=MaceAccelerationKernelMode.E3NN.value,
        mace_version=mace_version,
        adapter_version=adapter_version,
    )
    try:
        calculator = MACECalculator(
            model_paths=str(Path(model_path).resolve()), head=head, device=device,
            default_dtype=dtype, enable_cueq=False, enable_oeq=False,
        )
        _evaluate_acceleration_calculator(calculator, structures)
    except Exception as exc:
        return (
            AccelerationRealizationRecord(
                requested_backend=MaceAccelerationBackend.E3NN.value,
                resolved_kernel_mode=MaceAccelerationKernelMode.E3NN.value,
                training_kernel_mode=MaceAccelerationKernelMode.E3NN.value,
                device=device, dtype=dtype,
                foundation_inference_identity_digest=inference.content_digest,
                mace_version=mace_version, qualified=False,
                failure_reason=f"e3nn qualification failed: {type(exc).__name__}: {exc}",
            ),
            inference,
        )
    return acceleration_realization_from_e3nn(
        foundation_inference_identity=inference, device=device, dtype=dtype,
        mace_version=mace_version,
    ), inference

def _parity_failure_summary(record: MaceAccelerationParityRecord) -> str:
    """Compact numerical reason for one failed accelerator parity record."""

    return (
        f"Emax={record.energy_max_abs:.3e}, Fmax={record.force_max_abs:.3e}, "
        f"Smax={record.stress_max_abs:.3e}, Dmax={record.descriptor_max_abs:.3e}, "
        f"selection_identical={record.selection_identical}"
    )


@mace_runtime_warning_handled("MACE CuEq/e3nn acceleration qualification")
def qualify_cueq_realization(
    *,
    model_path: str | Path,
    head: str,
    structures: Sequence[Any],
    device: str,
    dtype: str,
    foundation_potential_digest: str,
    adapter_version: str,
    probe: MaceAccelerationProbe | None = None,
    parity_policy: MaceAccelerationParityPolicy | None = None,
    prefer_hybrid: bool = False,
    training_model_path: str | Path | None = None,
    training_head: str | None = None,
) -> tuple[
    AccelerationRealizationRecord,
    Any,
    MaceAccelerationParityRecord | None,
    MaceAccelerationParityRecord | None,
]:
    """Resolve source-foundation inference and training-foundation CuEq parity.

    The source-foundation inference model and the executable fine-tuning model
    are not necessarily the same artifact.  In particular, MH-1 training under
    the MACE 0.3.16 compatibility path uses the EXTRACT1-qualified selected-head
    checkpoint, while DATA6/foundation inference still refers to the original
    multi-head checkpoint.  CuEq parity is therefore measured independently for
    those two phases.

    Under MACE 0.3.16 calculator inference may use CuEq+OpenEquivariance hybrid
    conversion, but ``run_train`` disables OEQ whenever CuEq is enabled.  The
    training foundation must therefore pass an independent pure-CuEq parity
    check even when source inference resolves to hybrid mode.
    """

    from importlib import metadata as importlib_metadata
    from .foundation import FoundationInferenceIdentity

    if not structures:
        raise TrainingDataInputError("CuEq qualification requires a deterministic non-empty structure corpus.")
    active_probe = probe or probe_mace_acceleration(device=device, run_model_smoke=False)
    try:
        mace_version = str(importlib_metadata.version("mace-torch"))
    except Exception:
        mace_version = active_probe.mace_version or "unknown"
    failure_reasons: list[str] = []
    if not active_probe.cueq_available:
        failure_reasons.append("CuEq package/device capability is unavailable")

    try:
        from mace.calculators import MACECalculator
    except Exception as exc:
        failure_reasons.append(f"MACE calculator import failed: {exc}")
        MACECalculator = None  # type: ignore[assignment]

    reference = None
    if MACECalculator is not None:
        try:
            reference = MACECalculator(
                model_paths=str(Path(model_path).resolve()), head=head, device=device,
                default_dtype=dtype, enable_cueq=False, enable_oeq=False,
            )
            _evaluate_acceleration_calculator(reference, structures)
        except Exception as exc:
            failure_reasons.append(f"e3nn reference failed: {type(exc).__name__}: {exc}")
            reference = None

    source_pure_parity: MaceAccelerationParityRecord | None = None
    training_parity: MaceAccelerationParityRecord | None = None
    hybrid_parity: MaceAccelerationParityRecord | None = None
    if reference is not None and MACECalculator is not None and active_probe.cueq_available:
        try:
            pure = MACECalculator(
                model_paths=str(Path(model_path).resolve()), head=head, device=device,
                default_dtype=dtype,
                **MaceAccelerationKernelMode.CUEQ_PURE.calculator_kwargs(),
            )
            source_pure_parity = compare_mace_acceleration_calculators(
                reference, pure, structures,
                candidate_mode=MaceAccelerationKernelMode.CUEQ_PURE,
                dtype=dtype, policy=parity_policy,
            )
            if not source_pure_parity.passed:
                failure_reasons.append(
                    "cueq_pure source-foundation inference parity failed ("
                    + _parity_failure_summary(source_pure_parity)
                    + ")"
                )
        except Exception as exc:
            failure_reasons.append(f"cueq_pure failed: {type(exc).__name__}: {exc}")

        if active_probe.oeq_import_passed and active_probe.calculator_enable_oeq_supported:
            try:
                hybrid = MACECalculator(
                    model_paths=str(Path(model_path).resolve()), head=head, device=device,
                    default_dtype=dtype,
                    **MaceAccelerationKernelMode.CUEQ_OEQ_HYBRID.calculator_kwargs(),
                )
                hybrid_parity = compare_mace_acceleration_calculators(
                    reference, hybrid, structures,
                    candidate_mode=MaceAccelerationKernelMode.CUEQ_OEQ_HYBRID,
                    dtype=dtype, policy=parity_policy,
                )
                if not hybrid_parity.passed:
                    failure_reasons.append(
                        "cueq_oeq_hybrid inference parity failed ("
                        + _parity_failure_summary(hybrid_parity)
                        + ")"
                    )
            except Exception as exc:
                failure_reasons.append(f"cueq_oeq_hybrid failed: {type(exc).__name__}: {exc}")

    inference_parity: MaceAccelerationParityRecord | None = None
    selected_mode = MaceAccelerationKernelMode.CUEQ_UNRESOLVED
    if prefer_hybrid and hybrid_parity is not None and hybrid_parity.passed:
        selected_mode = MaceAccelerationKernelMode.CUEQ_OEQ_HYBRID
        inference_parity = hybrid_parity
    elif source_pure_parity is not None and source_pure_parity.passed:
        selected_mode = MaceAccelerationKernelMode.CUEQ_PURE
        inference_parity = source_pure_parity
    elif hybrid_parity is not None and hybrid_parity.passed:
        # Useful diagnostic evidence, but still non-authorizing because the
        # 0.3.16 trainer can only use pure CuEq.
        selected_mode = MaceAccelerationKernelMode.CUEQ_OEQ_HYBRID
        inference_parity = hybrid_parity

    # Training is qualified against the artifact MACE will actually fine-tune.
    # For legacy/single-head callers this defaults to the source model and
    # preserves the historical behaviour.  MH-1 callers pass the EXTRACT1
    # selected-head artifact explicitly.
    effective_training_path = Path(
        training_model_path if training_model_path is not None else model_path
    ).resolve()
    effective_training_head = str(training_head or head)
    source_path = Path(model_path).resolve()
    if (
        source_pure_parity is not None
        and effective_training_path == source_path
        and effective_training_head == str(head)
    ):
        training_parity = source_pure_parity
    elif MACECalculator is not None and active_probe.cueq_available:
        try:
            training_reference = MACECalculator(
                model_paths=str(effective_training_path), head=effective_training_head,
                device=device, default_dtype=dtype, enable_cueq=False, enable_oeq=False,
            )
            _evaluate_acceleration_calculator(training_reference, structures)
            training_pure = MACECalculator(
                model_paths=str(effective_training_path), head=effective_training_head,
                device=device, default_dtype=dtype,
                **MaceAccelerationKernelMode.CUEQ_PURE.calculator_kwargs(),
            )
            training_parity = compare_mace_acceleration_calculators(
                training_reference, training_pure, structures,
                candidate_mode=MaceAccelerationKernelMode.CUEQ_PURE,
                dtype=dtype, policy=parity_policy,
            )
        except Exception as exc:
            failure_reasons.append(
                f"cueq_pure training-foundation qualification failed: {type(exc).__name__}: {exc}"
            )

    if training_parity is not None and not training_parity.passed:
        failure_reasons.append(
            "cueq_pure training-foundation parity failed; "
            "MACE 0.3.16 training cannot be authorized ("
            + _parity_failure_summary(training_parity)
            + ")"
        )

    qualified = bool(
        training_parity is not None
        and training_parity.passed
        and inference_parity is not None
        and inference_parity.passed
    )
    inference = FoundationInferenceIdentity(
        foundation_potential_digest=foundation_potential_digest,
        default_dtype=dtype,
        backend=MaceAccelerationBackend.CUEQ.value,
        resolved_kernel_mode=selected_mode.value,
        mace_version=mace_version,
        adapter_version=adapter_version,
    )
    realization = AccelerationRealizationRecord(
        requested_backend=MaceAccelerationBackend.CUEQ.value,
        resolved_kernel_mode=selected_mode.value,
        training_kernel_mode=(
            MaceAccelerationKernelMode.CUEQ_PURE.value
            if active_probe.cueq_available
            else MaceAccelerationKernelMode.CUEQ_UNRESOLVED.value
        ),
        device=device, dtype=dtype,
        foundation_inference_identity_digest=inference.content_digest,
        mace_version=mace_version, cueq_versions=active_probe.cueq_versions,
        oeq_version=active_probe.oeq_version,
        inference_parity_record_digest=(
            None if inference_parity is None else inference_parity.content_digest
        ),
        training_parity_record_digest=(
            None if training_parity is None else training_parity.content_digest
        ),
        qualified=qualified,
        failure_reason=None if qualified else (
            "; ".join(failure_reasons) or "No production-qualified CuEq realization exists"
        ),
    )
    return realization, inference, inference_parity, training_parity


def qualify_training_acceleration_realization(
    *,
    backend: MaceAccelerationBackend | str,
    training_model_path: str | Path,
    training_head: str,
    structures: Any,
    device: str,
    dtype: str,
    selected_head_qualification_digest: str | None = None,
    probe: MaceAccelerationProbe | None = None,
    parity_policy: MaceAccelerationParityPolicy | None = None,
    noise_normalized_policy: TrainingAccelerationNoiseNormalizedParityPolicy | None = None,
) -> tuple[TrainingAccelerationRealizationRecord, MaceAccelerationParityRecord | TrainingAccelerationNoiseNormalizedParityRecord | None]:
    """Qualify the TRAIN2 backend without granting source-inference authority.

    FP32 CuEq uses the permanent warm-up/all-pairs noise-normalized force gate.
    FP64 retains the conventional one-shot allclose parity authority.
    """

    from importlib import metadata as importlib_metadata

    requested = MaceAccelerationBackend(backend)
    path = Path(training_model_path).expanduser().resolve()
    if not path.is_file():
        raise TrainingDataInputError(f"TRAIN2 qualification model does not exist: {path}")
    if not structures:
        raise TrainingDataInputError("TRAIN2 qualification requires a deterministic non-empty structure corpus.")
    try:
        mace_version = str(importlib_metadata.version("mace-torch"))
    except Exception:
        mace_version = None
    checkpoint_sha = sha256_file_cached(path)
    if requested is MaceAccelerationBackend.E3NN:
        failure_reason = None
        try:
            from mace.calculators import MACECalculator
            reference = MACECalculator(
                model_paths=str(path), head=training_head, device=device,
                default_dtype=dtype, enable_cueq=False, enable_oeq=False,
            )
            _evaluate_acceleration_calculator(reference, structures)
        except Exception as exc:
            failure_reason = f"e3nn TRAIN2 qualification failed: {type(exc).__name__}: {exc}"
        return TrainingAccelerationRealizationRecord(
            requested_backend=requested.value,
            training_kernel_mode=MaceAccelerationKernelMode.E3NN.value,
            device=device,
            dtype=dtype,
            training_checkpoint_reference=str(path),
            training_checkpoint_sha256=checkpoint_sha,
            selected_head_qualification_digest=selected_head_qualification_digest,
            mace_version=mace_version,
            qualified=failure_reason is None,
            failure_reason=failure_reason,
        ), None

    active_probe = probe or probe_mace_acceleration(device=device, run_model_smoke=False)
    failures: list[str] = []
    if not active_probe.cueq_available:
        failures.append("CuEq package/device capability is unavailable")
    parity: MaceAccelerationParityRecord | None = None
    if active_probe.cueq_available:
        try:
            from mace.calculators import MACECalculator
            reference = MACECalculator(
                model_paths=str(path), head=training_head, device=device,
                default_dtype=dtype, enable_cueq=False, enable_oeq=False,
            )
            candidate = MACECalculator(
                model_paths=str(path), head=training_head, device=device,
                default_dtype=dtype,
                **MaceAccelerationKernelMode.CUEQ_PURE.calculator_kwargs(),
            )
            if dtype == "float32":
                active_noise = (
                    TrainingAccelerationNoiseNormalizedParityPolicy()
                    if noise_normalized_policy is None else noise_normalized_policy
                )
                repeatability = diagnose_mace_acceleration_repeatability(
                    reference, candidate, structures, dtype=dtype, policy=parity_policy,
                    repeat_count=active_noise.repeat_count,
                    force_threshold=active_noise.force_threshold,
                    warmup_count=active_noise.warmup_count,
                )
                parity = build_training_noise_normalized_parity_record(
                    repeatability, policy=active_noise,
                )
                if not parity.passed:
                    failures.append(
                        "pure-CuEq TRAIN2 noise-normalized parity failed ("
                        + "; ".join(parity.failure_reasons) + ")"
                    )
            else:
                parity = compare_mace_acceleration_calculators(
                    reference, candidate, structures,
                    candidate_mode=MaceAccelerationKernelMode.CUEQ_PURE,
                    dtype=dtype, policy=parity_policy,
                )
                if not parity.passed:
                    failures.append(
                        "pure-CuEq TRAIN2 parity failed (" + _parity_failure_summary(parity) + ")"
                    )
        except Exception as exc:
            failures.append(f"pure-CuEq TRAIN2 qualification failed: {type(exc).__name__}: {exc}")
    qualified = bool(parity is not None and parity.passed and active_probe.cueq_available)
    record = TrainingAccelerationRealizationRecord(
        requested_backend=requested.value,
        training_kernel_mode=(
            MaceAccelerationKernelMode.CUEQ_PURE.value
            if active_probe.cueq_available
            else MaceAccelerationKernelMode.CUEQ_UNRESOLVED.value
        ),
        device=device,
        dtype=dtype,
        training_checkpoint_reference=str(path),
        training_checkpoint_sha256=checkpoint_sha,
        selected_head_qualification_digest=selected_head_qualification_digest,
        mace_version=mace_version or active_probe.mace_version,
        cueq_versions=active_probe.cueq_versions,
        training_parity_record_digest=None if parity is None else parity.content_digest,
        qualified=qualified,
        failure_reason=None if qualified else ("; ".join(failures) or "CuEq TRAIN2 qualification failed"),
    )
    return record, parity

def detect_default_acceleration_backend(*, device: str = "cuda") -> MaceAccelerationBackend:
    """Resolve the initialization default without silently changing later runs."""

    probe = probe_mace_acceleration(device=device, run_model_smoke=False)
    return MaceAccelerationBackend.CUEQ if probe.cueq_available else MaceAccelerationBackend.E3NN
