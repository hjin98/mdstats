"""CUEQ-PHASE2 selected-head CuEq source-execution qualification authority.

CUEQ-PHASE2 is optional.  It does not redefine the scientific source model:
the original six-head MACE-MH-1 checkpoint with the exact ``omat_pbe`` head
remains authoritative.  The EXTRACT1-derived single-head checkpoint plus a
qualified pure-cuEquivariance runtime is treated only as an executable
realization for inference-heavy preparation (DATA6, source evaluation, and,
when separately evidenced, pseudolabel/E0 generation).

This module is evidence/control-plane code.  Positive accelerator evidence is
intentionally deferred to FINAL-GPU1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .acceleration import MaceAccelerationParityRecord
from .accelerator_runtime_freeze import CueqDep1RuntimeRecord

CUEQ_PHASE2_POLICY_SCHEMA = "mdstats.cueq-phase2-policy.v1"
CUEQ_PHASE2_CORPUS_SCHEMA = "mdstats.cueq-phase2-development-corpus.v1"
CUEQ_PHASE2_DATA6_PARITY_SCHEMA = "mdstats.cueq-phase2-data6-parity.v1"
CUEQ_PHASE2_ASSESSMENT_SCHEMA = "mdstats.cueq-phase2-path-assessment.v1"
CUEQ_PHASE2_QUALIFICATION_SCHEMA = "mdstats.cueq-phase2-qualification.v1"
CUEQ_PHASE2_VERSION = "mdstats.cueq-phase2.selected-head-source.2026-08.v1"

CUEQ_PHASE2_MH1_SHA256 = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
CUEQ_PHASE2_SOURCE_POTENTIAL_DIGEST = "06bf87891d6addebd3ea300fa23fd6401f0b74897f5676394e99507d03c8fc59"
CUEQ_PHASE2_SELECTED_HEAD_SHA256 = "7b6f3cce6d2086164082f1cb5739098de2db990d6a49f0d60e66a3a0f1ae545e"
CUEQ_PHASE2_SELECTED_HEAD_QUALIFICATION_DIGEST = "0f49db0ff9da291fbb4d70430c71189552a531d0239d92c06d0ca4024b05e365"

CUEQ_PHASE2_STRATA = (
    "composition_species",
    "temperature_strain",
    "high_force_difficulty",
    "unusual_local_mobile_ion",
    "large_high_edge_count",
    "ordinary",
)


def _nonnegative_finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and >= 0.")
    return result


def _tuple_unique(values: Sequence[str], *, name: str) -> tuple[str, ...]:
    result = tuple(str(v).strip() for v in values)
    if any(not v for v in result):
        raise TrainingDataInputError(f"{name} entries must be non-empty.")
    if len(set(result)) != len(result):
        raise TrainingDataInputError(f"{name} entries must be unique.")
    return result


@dataclass(frozen=True, slots=True)
class CueqPhase2Policy:
    """Frozen optional selected-head source-execution policy."""

    source_head: str = "omat_pbe"
    reference_source_kernel_mode: str = "e3nn"
    candidate_source_kernel_mode: str = "cueq_pure"
    source_checkpoint_sha256: str = CUEQ_PHASE2_MH1_SHA256
    source_potential_digest: str = CUEQ_PHASE2_SOURCE_POTENTIAL_DIGEST
    selected_head_checkpoint_sha256: str = CUEQ_PHASE2_SELECTED_HEAD_SHA256
    selected_head_qualification_digest: str = CUEQ_PHASE2_SELECTED_HEAD_QUALIFICATION_DIGEST
    minimum_development_assessments: int = 1
    require_existing_acceleration_parity: bool = True
    require_difficulty_parity: bool = True
    require_frozen_transform_pca_fps_parity: bool = True
    require_data6_selection_identity: bool = True
    require_data7_selection_identity: bool = True
    require_pseudolabel_lineage_if_requested: bool = True
    authority_version: str = CUEQ_PHASE2_VERSION

    def __post_init__(self) -> None:
        if self.source_head != "omat_pbe":
            raise TrainingDataInputError("CUEQ-PHASE2 scientific source head must remain omat_pbe.")
        if self.reference_source_kernel_mode != "e3nn":
            raise TrainingDataInputError("CUEQ-PHASE2 reference source execution must remain e3nn.")
        if self.candidate_source_kernel_mode != "cueq_pure":
            raise TrainingDataInputError("CUEQ-PHASE2 candidate source execution must use cueq_pure.")
        for name in (
            "source_checkpoint_sha256", "source_potential_digest",
            "selected_head_checkpoint_sha256", "selected_head_qualification_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        minimum = int(self.minimum_development_assessments)
        if minimum < 1:
            raise TrainingDataInputError("CUEQ-PHASE2 requires at least one development-corpus assessment.")
        if self.authority_version != CUEQ_PHASE2_VERSION:
            raise TrainingDataInputError("Unsupported CUEQ-PHASE2 authority version.")
        object.__setattr__(self, "minimum_development_assessments", minimum)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE2_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "source_head": self.source_head,
            "reference_source_kernel_mode": self.reference_source_kernel_mode,
            "candidate_source_kernel_mode": self.candidate_source_kernel_mode,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "source_potential_digest": self.source_potential_digest,
            "selected_head_checkpoint_sha256": self.selected_head_checkpoint_sha256,
            "selected_head_qualification_digest": self.selected_head_qualification_digest,
            "minimum_development_assessments": self.minimum_development_assessments,
            "require_existing_acceleration_parity": self.require_existing_acceleration_parity,
            "require_difficulty_parity": self.require_difficulty_parity,
            "require_frozen_transform_pca_fps_parity": self.require_frozen_transform_pca_fps_parity,
            "require_data6_selection_identity": self.require_data6_selection_identity,
            "require_data7_selection_identity": self.require_data7_selection_identity,
            "require_pseudolabel_lineage_if_requested": self.require_pseudolabel_lineage_if_requested,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase2Policy":
        if payload.get("schema") != CUEQ_PHASE2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE2 policy schema.")
        result = cls(**{name: payload[name] for name in (
            "source_head", "reference_source_kernel_mode", "candidate_source_kernel_mode",
            "source_checkpoint_sha256", "source_potential_digest", "selected_head_checkpoint_sha256",
            "selected_head_qualification_digest", "minimum_development_assessments",
            "require_existing_acceleration_parity", "require_difficulty_parity",
            "require_frozen_transform_pca_fps_parity", "require_data6_selection_identity",
            "require_data7_selection_identity", "require_pseudolabel_lineage_if_requested",
            "authority_version",
        )})
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqPhase2DevelopmentCorpus:
    """Deterministic stratified development corpus; locked tests cannot tune it."""

    corpus_digest: str
    deterministic_order_digest: str
    structure_count: int
    atom_count: int
    available_strata: tuple[str, ...] = CUEQ_PHASE2_STRATA
    covered_strata: tuple[str, ...] = CUEQ_PHASE2_STRATA
    deterministic: bool = True
    locked_test_used_for_tuning: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "corpus_digest", validate_digest(self.corpus_digest, name="corpus_digest"))
        object.__setattr__(self, "deterministic_order_digest", validate_digest(self.deterministic_order_digest, name="deterministic_order_digest"))
        if int(self.structure_count) <= 0 or int(self.atom_count) <= 0:
            raise TrainingDataInputError("CUEQ-PHASE2 development corpus must contain structures and atoms.")
        available = _tuple_unique(self.available_strata, name="available_strata")
        covered = _tuple_unique(self.covered_strata, name="covered_strata")
        allowed = set(CUEQ_PHASE2_STRATA)
        if set(available) - allowed or set(covered) - allowed:
            raise TrainingDataInputError("CUEQ-PHASE2 corpus contains an unknown stratification category.")
        object.__setattr__(self, "structure_count", int(self.structure_count))
        object.__setattr__(self, "atom_count", int(self.atom_count))
        object.__setattr__(self, "available_strata", available)
        object.__setattr__(self, "covered_strata", covered)

    @property
    def passed(self) -> bool:
        return bool(self.deterministic and not self.locked_test_used_for_tuning and set(self.available_strata) <= set(self.covered_strata))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE2_CORPUS_SCHEMA,
            "corpus_digest": self.corpus_digest,
            "deterministic_order_digest": self.deterministic_order_digest,
            "structure_count": self.structure_count,
            "atom_count": self.atom_count,
            "available_strata": list(self.available_strata),
            "covered_strata": list(self.covered_strata),
            "deterministic": bool(self.deterministic),
            "locked_test_used_for_tuning": bool(self.locked_test_used_for_tuning),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase2DevelopmentCorpus":
        if payload.get("schema") != CUEQ_PHASE2_CORPUS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE2 development-corpus schema.")
        result = cls(
            corpus_digest=str(payload["corpus_digest"]), deterministic_order_digest=str(payload["deterministic_order_digest"]),
            structure_count=int(payload["structure_count"]), atom_count=int(payload["atom_count"]),
            available_strata=tuple(str(v) for v in payload.get("available_strata", ())),
            covered_strata=tuple(str(v) for v in payload.get("covered_strata", ())),
            deterministic=bool(payload["deterministic"]), locked_test_used_for_tuning=bool(payload["locked_test_used_for_tuning"]),
        )
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("CUEQ-PHASE2 corpus pass state mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE2 corpus digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqPhase2Data6ParityRecord:
    """DATA6/DATA7 downstream parity and lineage evidence.

    Numerical booleans are produced under the already-qualified numerical
    parity authority; this gate does not introduce or relax a tolerance.
    Selection fingerprints remain exact hard-decision evidence.
    """

    scientific_source_digest: str
    candidate_execution_realization_digest: str
    data6_protocol_digest: str
    frozen_reference_transform_digest: str
    difficulty_max_abs: float
    difficulty_rmse: float
    difficulty_parity_passed: bool
    pca_input_max_abs: float
    pca_input_rmse: float
    pca_input_parity_passed: bool
    fps_input_max_abs: float
    fps_input_rmse: float
    fps_input_parity_passed: bool
    reference_data6_selection: tuple[str, ...]
    candidate_data6_selection: tuple[str, ...]
    reference_data7_selection: tuple[str, ...]
    candidate_data7_selection: tuple[str, ...]
    full_refit_selection_verified: bool | None = None
    pseudolabel_requested: bool = False
    pseudolabel_values_parity_passed: bool | None = None
    atomic_e0_parity_passed: bool | None = None
    pseudolabel_scientific_source_digest: str | None = None
    pseudolabel_execution_realization_digest: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "scientific_source_digest", "candidate_execution_realization_digest", "data6_protocol_digest",
            "frozen_reference_transform_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "difficulty_max_abs", "difficulty_rmse", "pca_input_max_abs", "pca_input_rmse",
            "fps_input_max_abs", "fps_input_rmse",
        ):
            object.__setattr__(self, name, _nonnegative_finite(getattr(self, name), name=name))
        for name in ("reference_data6_selection", "candidate_data6_selection", "reference_data7_selection", "candidate_data7_selection"):
            value = _tuple_unique(getattr(self, name), name=name)
            if not value:
                raise TrainingDataInputError(f"{name} must be non-empty.")
            object.__setattr__(self, name, value)
        if self.pseudolabel_scientific_source_digest is not None:
            object.__setattr__(self, "pseudolabel_scientific_source_digest", validate_digest(self.pseudolabel_scientific_source_digest, name="pseudolabel_scientific_source_digest"))
        if self.pseudolabel_execution_realization_digest is not None:
            object.__setattr__(self, "pseudolabel_execution_realization_digest", validate_digest(self.pseudolabel_execution_realization_digest, name="pseudolabel_execution_realization_digest"))
        if self.pseudolabel_requested:
            if self.pseudolabel_values_parity_passed is None or self.atomic_e0_parity_passed is None:
                raise TrainingDataInputError("Requested CUEQ-PHASE2 pseudolabel evidence requires value and E0 parity states.")
            if self.pseudolabel_scientific_source_digest is None or self.pseudolabel_execution_realization_digest is None:
                raise TrainingDataInputError("Requested CUEQ-PHASE2 pseudolabel evidence requires explicit scientific/execution lineage.")

    @property
    def data6_selection_identical(self) -> bool:
        return self.reference_data6_selection == self.candidate_data6_selection

    @property
    def data7_selection_identical(self) -> bool:
        return self.reference_data7_selection == self.candidate_data7_selection

    @property
    def pseudolabel_parity_passed(self) -> bool:
        if not self.pseudolabel_requested:
            return True
        return bool(
            self.pseudolabel_values_parity_passed
            and self.atomic_e0_parity_passed
            and self.pseudolabel_scientific_source_digest == self.scientific_source_digest
            and self.pseudolabel_execution_realization_digest == self.candidate_execution_realization_digest
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE2_DATA6_PARITY_SCHEMA,
            "scientific_source_digest": self.scientific_source_digest,
            "candidate_execution_realization_digest": self.candidate_execution_realization_digest,
            "data6_protocol_digest": self.data6_protocol_digest,
            "frozen_reference_transform_digest": self.frozen_reference_transform_digest,
            "difficulty_max_abs": self.difficulty_max_abs, "difficulty_rmse": self.difficulty_rmse,
            "difficulty_parity_passed": bool(self.difficulty_parity_passed),
            "pca_input_max_abs": self.pca_input_max_abs, "pca_input_rmse": self.pca_input_rmse,
            "pca_input_parity_passed": bool(self.pca_input_parity_passed),
            "fps_input_max_abs": self.fps_input_max_abs, "fps_input_rmse": self.fps_input_rmse,
            "fps_input_parity_passed": bool(self.fps_input_parity_passed),
            "reference_data6_selection": list(self.reference_data6_selection),
            "candidate_data6_selection": list(self.candidate_data6_selection),
            "reference_data7_selection": list(self.reference_data7_selection),
            "candidate_data7_selection": list(self.candidate_data7_selection),
            "data6_selection_identical": self.data6_selection_identical,
            "data7_selection_identical": self.data7_selection_identical,
            "full_refit_selection_verified": self.full_refit_selection_verified,
            "pseudolabel_requested": bool(self.pseudolabel_requested),
            "pseudolabel_values_parity_passed": self.pseudolabel_values_parity_passed,
            "atomic_e0_parity_passed": self.atomic_e0_parity_passed,
            "pseudolabel_scientific_source_digest": self.pseudolabel_scientific_source_digest,
            "pseudolabel_execution_realization_digest": self.pseudolabel_execution_realization_digest,
            "pseudolabel_parity_passed": self.pseudolabel_parity_passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase2Data6ParityRecord":
        if payload.get("schema") != CUEQ_PHASE2_DATA6_PARITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE2 DATA6 parity schema.")
        result = cls(
            scientific_source_digest=str(payload["scientific_source_digest"]),
            candidate_execution_realization_digest=str(payload["candidate_execution_realization_digest"]),
            data6_protocol_digest=str(payload["data6_protocol_digest"]),
            frozen_reference_transform_digest=str(payload["frozen_reference_transform_digest"]),
            difficulty_max_abs=float(payload["difficulty_max_abs"]), difficulty_rmse=float(payload["difficulty_rmse"]),
            difficulty_parity_passed=bool(payload["difficulty_parity_passed"]),
            pca_input_max_abs=float(payload["pca_input_max_abs"]), pca_input_rmse=float(payload["pca_input_rmse"]),
            pca_input_parity_passed=bool(payload["pca_input_parity_passed"]),
            fps_input_max_abs=float(payload["fps_input_max_abs"]), fps_input_rmse=float(payload["fps_input_rmse"]),
            fps_input_parity_passed=bool(payload["fps_input_parity_passed"]),
            reference_data6_selection=tuple(str(v) for v in payload["reference_data6_selection"]),
            candidate_data6_selection=tuple(str(v) for v in payload["candidate_data6_selection"]),
            reference_data7_selection=tuple(str(v) for v in payload["reference_data7_selection"]),
            candidate_data7_selection=tuple(str(v) for v in payload["candidate_data7_selection"]),
            full_refit_selection_verified=payload.get("full_refit_selection_verified"),
            pseudolabel_requested=bool(payload.get("pseudolabel_requested", False)),
            pseudolabel_values_parity_passed=payload.get("pseudolabel_values_parity_passed"),
            atomic_e0_parity_passed=payload.get("atomic_e0_parity_passed"),
            pseudolabel_scientific_source_digest=payload.get("pseudolabel_scientific_source_digest"),
            pseudolabel_execution_realization_digest=payload.get("pseudolabel_execution_realization_digest"),
        )
        for name, expected in (
            ("data6_selection_identical", result.data6_selection_identical),
            ("data7_selection_identical", result.data7_selection_identical),
            ("pseudolabel_parity_passed", result.pseudolabel_parity_passed),
        ):
            if payload.get(name) not in (None, expected):
                raise TrainingDataSerializationError(f"CUEQ-PHASE2 DATA6 {name} mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE2 DATA6 parity digest mismatch.")
        return result


def cueq_phase2_execution_realization_digest(
    *, policy: CueqPhase2Policy, runtime_record_digest: str, dtype: str
) -> str:
    """Content-address the derived selected-head/CuEq executable realization."""

    runtime_digest = validate_digest(runtime_record_digest, name="runtime_record_digest")
    if dtype not in {"float32", "float64"}:
        raise TrainingDataInputError("CUEQ-PHASE2 dtype must be float32 or float64.")
    return digest({
        "schema": "mdstats.cueq-phase2-execution-realization.v1",
        "runtime_record_digest": runtime_digest,
        "scientific_source_checkpoint_sha256": policy.source_checkpoint_sha256,
        "scientific_source_head": policy.source_head,
        "selected_head_checkpoint_sha256": policy.selected_head_checkpoint_sha256,
        "selected_head_qualification_digest": policy.selected_head_qualification_digest,
        "candidate_source_kernel_mode": policy.candidate_source_kernel_mode,
        "dtype": dtype,
    })


@dataclass(frozen=True, slots=True)
class CueqPhase2PathAssessment:
    """Complete original/e3nn -> selected-head/CuEq observable-path assessment."""

    policy: CueqPhase2Policy
    corpus: CueqPhase2DevelopmentCorpus
    runtime_record_digest: str
    reference_source_kernel_mode: str
    candidate_source_kernel_mode: str
    dtype: str
    acceleration_parity: MaceAccelerationParityRecord
    data6_parity: CueqPhase2Data6ParityRecord
    reference_wall_time_seconds: float = 0.0
    candidate_wall_time_seconds: float = 0.0
    candidate_peak_vram_bytes: int = 0
    candidate_reserved_vram_bytes: int = 0
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "runtime_record_digest", validate_digest(self.runtime_record_digest, name="runtime_record_digest"))
        if self.reference_source_kernel_mode != self.policy.reference_source_kernel_mode:
            raise TrainingDataInputError("CUEQ-PHASE2 reference kernel disagrees with policy.")
        if self.candidate_source_kernel_mode != self.policy.candidate_source_kernel_mode:
            raise TrainingDataInputError("CUEQ-PHASE2 candidate kernel disagrees with policy.")
        if self.dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("CUEQ-PHASE2 dtype must be float32 or float64.")
        for name in ("reference_wall_time_seconds", "candidate_wall_time_seconds"):
            object.__setattr__(self, name, _nonnegative_finite(getattr(self, name), name=name))
        if min(int(self.candidate_peak_vram_bytes), int(self.candidate_reserved_vram_bytes)) < 0:
            raise TrainingDataInputError("CUEQ-PHASE2 VRAM telemetry must be >= 0.")
        object.__setattr__(self, "candidate_peak_vram_bytes", int(self.candidate_peak_vram_bytes))
        object.__setattr__(self, "candidate_reserved_vram_bytes", int(self.candidate_reserved_vram_bytes))

        reasons: list[str] = []
        if not self.corpus.passed:
            reasons.append("development_corpus_contract")
        if self.acceleration_parity.reference_mode != self.policy.reference_source_kernel_mode:
            reasons.append("acceleration_parity_reference_mode")
        if self.acceleration_parity.candidate_mode != self.policy.candidate_source_kernel_mode:
            reasons.append("acceleration_parity_candidate_mode")
        if self.acceleration_parity.dtype != self.dtype:
            reasons.append("acceleration_parity_dtype")
        if self.policy.require_existing_acceleration_parity and not self.acceleration_parity.passed:
            reasons.append("existing_numerical_parity_authority")
        if self.data6_parity.scientific_source_digest != self.policy.source_potential_digest:
            reasons.append("scientific_source_lineage")
        if self.data6_parity.candidate_execution_realization_digest != self.execution_realization_digest:
            reasons.append("execution_realization_lineage")
        if self.policy.require_difficulty_parity and not self.data6_parity.difficulty_parity_passed:
            reasons.append("foundation_difficulty_parity")
        if self.policy.require_frozen_transform_pca_fps_parity:
            if not self.data6_parity.pca_input_parity_passed:
                reasons.append("frozen_transform_pca_input_parity")
            if not self.data6_parity.fps_input_parity_passed:
                reasons.append("frozen_transform_fps_input_parity")
        if self.policy.require_data6_selection_identity and not self.data6_parity.data6_selection_identical:
            reasons.append("data6_selection_identity")
        if self.policy.require_data7_selection_identity and not self.data6_parity.data7_selection_identical:
            reasons.append("data7_selection_identity")
        if self.policy.require_pseudolabel_lineage_if_requested and not self.data6_parity.pseudolabel_parity_passed:
            reasons.append("pseudolabel_e0_lineage_parity")
        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def execution_realization_digest(self) -> str:
        return cueq_phase2_execution_realization_digest(
            policy=self.policy, runtime_record_digest=self.runtime_record_digest, dtype=self.dtype
        )

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    @property
    def speedup(self) -> float | None:
        if self.reference_wall_time_seconds <= 0.0 or self.candidate_wall_time_seconds <= 0.0:
            return None
        return float(self.reference_wall_time_seconds / self.candidate_wall_time_seconds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE2_ASSESSMENT_SCHEMA,
            "policy": self.policy.to_dict(), "corpus": self.corpus.to_dict(),
            "runtime_record_digest": self.runtime_record_digest,
            "reference_source_kernel_mode": self.reference_source_kernel_mode,
            "candidate_source_kernel_mode": self.candidate_source_kernel_mode,
            "dtype": self.dtype,
            "execution_realization_digest": self.execution_realization_digest,
            "acceleration_parity": self.acceleration_parity.to_dict(),
            "data6_parity": self.data6_parity.to_dict(),
            "reference_wall_time_seconds": self.reference_wall_time_seconds,
            "candidate_wall_time_seconds": self.candidate_wall_time_seconds,
            "candidate_peak_vram_bytes": self.candidate_peak_vram_bytes,
            "candidate_reserved_vram_bytes": self.candidate_reserved_vram_bytes,
            "speedup": self.speedup,
            "blocking_reasons": list(self.blocking_reasons), "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase2PathAssessment":
        if payload.get("schema") != CUEQ_PHASE2_ASSESSMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE2 path-assessment schema.")
        result = cls(
            policy=CueqPhase2Policy.from_dict(payload["policy"]),
            corpus=CueqPhase2DevelopmentCorpus.from_dict(payload["corpus"]),
            runtime_record_digest=str(payload["runtime_record_digest"]),
            reference_source_kernel_mode=str(payload["reference_source_kernel_mode"]),
            candidate_source_kernel_mode=str(payload["candidate_source_kernel_mode"]),
            dtype=str(payload["dtype"]),
            acceleration_parity=MaceAccelerationParityRecord.from_dict(payload["acceleration_parity"]),
            data6_parity=CueqPhase2Data6ParityRecord.from_dict(payload["data6_parity"]),
            reference_wall_time_seconds=float(payload.get("reference_wall_time_seconds", 0.0)),
            candidate_wall_time_seconds=float(payload.get("candidate_wall_time_seconds", 0.0)),
            candidate_peak_vram_bytes=int(payload.get("candidate_peak_vram_bytes", 0)),
            candidate_reserved_vram_bytes=int(payload.get("candidate_reserved_vram_bytes", 0)),
        )
        if payload.get("execution_realization_digest") not in (None, result.execution_realization_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE2 execution-realization digest mismatch.")
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("CUEQ-PHASE2 path-assessment blockers mismatch.")
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("CUEQ-PHASE2 path-assessment pass state mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE2 path-assessment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqPhase2QualificationRecord:
    """Gate-level authorization for the derived selected-head CuEq source path."""

    policy: CueqPhase2Policy
    cueq_dep1_runtime_digest: str
    cueq_dep1_passed: bool
    assessments: tuple[CueqPhase2PathAssessment, ...] = ()
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cueq_dep1_runtime_digest", validate_digest(self.cueq_dep1_runtime_digest, name="cueq_dep1_runtime_digest"))
        assessments = tuple(self.assessments)
        reasons: list[str] = []
        if not self.cueq_dep1_passed:
            reasons.append("CUEQ_DEP1_RUNTIME_FREEZE")
        if len(assessments) < self.policy.minimum_development_assessments:
            reasons.append("development_path_assessment_missing")
        if any(item.policy.content_digest != self.policy.content_digest for item in assessments):
            reasons.append("assessment_policy_identity")
        if any(item.runtime_record_digest != self.cueq_dep1_runtime_digest for item in assessments):
            reasons.append("assessment_runtime_identity")
        if any(not item.passed for item in assessments):
            reasons.append("development_path_assessment_failed")
        object.__setattr__(self, "assessments", assessments)
        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    @property
    def selected_head_source_cueq_execution_authorized(self) -> bool:
        return self.passed

    @property
    def data6_cueq_execution_authorized(self) -> bool:
        return self.passed

    @property
    def source_evaluation_cueq_execution_authorized(self) -> bool:
        return self.passed

    @property
    def pseudolabel_cueq_execution_authorized(self) -> bool:
        return bool(self.passed and self.assessments and all(item.data6_parity.pseudolabel_requested for item in self.assessments))

    @property
    def original_six_head_cueq_execution_authorized(self) -> bool:
        return False

    @property
    def generated_default_change_authorized(self) -> bool:
        return False

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE2_QUALIFICATION_SCHEMA,
            "authority_version": CUEQ_PHASE2_VERSION,
            "policy": self.policy.to_dict(),
            "cueq_dep1_runtime_digest": self.cueq_dep1_runtime_digest,
            "cueq_dep1_passed": self.cueq_dep1_passed,
            "assessments": [item.to_dict() for item in self.assessments],
            "blocking_reasons": list(self.blocking_reasons), "passed": self.passed,
            "authorization": {
                "selected_head_source_cueq_execution_authorized": self.selected_head_source_cueq_execution_authorized,
                "data6_cueq_execution_authorized": self.data6_cueq_execution_authorized,
                "source_evaluation_cueq_execution_authorized": self.source_evaluation_cueq_execution_authorized,
                "pseudolabel_cueq_execution_authorized": self.pseudolabel_cueq_execution_authorized,
                "original_six_head_cueq_execution_authorized": self.original_six_head_cueq_execution_authorized,
                "generated_default_change_authorized": self.generated_default_change_authorized,
            },
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase2QualificationRecord":
        if payload.get("schema") != CUEQ_PHASE2_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE2 qualification schema.")
        if payload.get("authority_version") != CUEQ_PHASE2_VERSION:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE2 qualification authority version.")
        result = cls(
            policy=CueqPhase2Policy.from_dict(payload["policy"]),
            cueq_dep1_runtime_digest=str(payload["cueq_dep1_runtime_digest"]),
            cueq_dep1_passed=bool(payload["cueq_dep1_passed"]),
            assessments=tuple(CueqPhase2PathAssessment.from_dict(v) for v in payload.get("assessments", ())),
        )
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("CUEQ-PHASE2 qualification blockers mismatch.")
        auth = payload.get("authorization", {})
        expected = result._payload()["authorization"]
        if auth not in ({}, expected):
            raise TrainingDataSerializationError("CUEQ-PHASE2 qualification authorization mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE2 qualification digest mismatch.")
        return result


def build_cueq_phase2_qualification(
    *,
    runtime: CueqDep1RuntimeRecord,
    assessments: Sequence[CueqPhase2PathAssessment] = (),
    policy: CueqPhase2Policy | None = None,
) -> CueqPhase2QualificationRecord:
    """Build CUEQ-PHASE2 without allowing a negative runtime to fall back."""

    active = policy or CueqPhase2Policy()
    return CueqPhase2QualificationRecord(
        policy=active,
        cueq_dep1_runtime_digest=runtime.content_digest,
        cueq_dep1_passed=runtime.passed,
        assessments=tuple(assessments),
    )
