"""PERF-CERT1 end-to-end scientific/performance certification authority.

PERF-CERT1 is the release-level policy recommendation gate that sits above the
independent CUEQ-PHASE1 (training-only) and optional CUEQ-PHASE2
(selected-head source/DATA6) authorities.  It does not create a new scientific
tolerance and it cannot change generated defaults.  Instead, it compares
complete execution profiles against the optimized authoritative MH-1/e3nn
baseline, rejects any profile that changes hard scientific decisions, and may
recommend a scientifically admissible accelerated profile only when it shows a
measured end-to-end operational benefit.

Positive CUDA/CuEq evidence is intentionally deferred to FINAL-GPU1.  This
module is therefore primarily an immutable evidence/control-plane authority.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .cueq_phase1 import CueqPhase1QualificationRecord
from .cueq_phase2 import CueqPhase2QualificationRecord

PERF_CERT1_POLICY_SCHEMA = "mdstats.perf-cert1-policy.v1"
PERF_CERT1_TELEMETRY_SCHEMA = "mdstats.perf-cert1-telemetry.v1"
PERF_CERT1_PROFILE_SCHEMA = "mdstats.perf-cert1-profile.v1"
PERF_CERT1_UPSTREAM_SCHEMA = "mdstats.perf-cert1-upstream-authority.v1"
PERF_CERT1_ASSESSMENT_SCHEMA = "mdstats.perf-cert1-profile-assessment.v1"
PERF_CERT1_QUALIFICATION_SCHEMA = "mdstats.perf-cert1-qualification.v1"
PERF_CERT1_VERSION = "mdstats.perf-cert1.end-to-end.2026-08.v1"

PERF_CERT1_MH1_SHA256 = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
PERF_CERT1_MPA0_SHA256 = "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"

PROFILE_BASELINE = "authoritative_e3nn_baseline"
PROFILE_PHASE1 = "e3nn_source_cueq_training"
PROFILE_PHASE2 = "selected_head_cueq_source_cueq_training"
PROFILE_FALLBACK = "compatibility_fallback"
PERF_CERT1_PROFILE_KINDS = (PROFILE_BASELINE, PROFILE_PHASE1, PROFILE_PHASE2, PROFILE_FALLBACK)

_ALLOWED_KERNEL_MODES = {"e3nn", "cueq_pure"}
_ALLOWED_VERIFICATION_STATES = {"pass", "fail", "not_available"}


def _nonempty(value: str, *, name: str) -> str:
    result = str(value).strip()
    if not result:
        raise TrainingDataInputError(f"{name} must be non-empty.")
    return result


def _finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise TrainingDataInputError(f"{name} must be finite.")
    return result


def _nonnegative_finite(value: float, *, name: str) -> float:
    result = _finite(value, name=name)
    if result < 0.0:
        raise TrainingDataInputError(f"{name} must be >= 0.")
    return result


def _nonnegative_int(value: int, *, name: str) -> int:
    result = int(value)
    if result < 0:
        raise TrainingDataInputError(f"{name} must be >= 0.")
    return result


def _verification(value: str, *, name: str) -> str:
    result = str(value).strip().lower()
    if result not in _ALLOWED_VERIFICATION_STATES:
        raise TrainingDataInputError(f"{name} must be pass, fail, or not_available.")
    return result


@dataclass(frozen=True, slots=True)
class PerfCert1Policy:
    """Frozen PERF-CERT1 comparison and recommendation policy."""

    baseline_profile_kind: str = PROFILE_BASELINE
    minimum_total_speedup: float = 1.0
    require_positive_total_speedup: bool = True
    require_exact_hard_decision_identity: bool = True
    require_exact_data6_selection_identity: bool = True
    require_exact_data7_selection_identity: bool = True
    require_exact_target_selection_identity: bool = True
    require_replay_retention: bool = True
    require_eval2_pass: bool = True
    require_available_deployment_pass: bool = True
    require_available_physical_pass: bool = True
    require_locked_test_not_used_for_tuning: bool = True
    generated_default_change_authorized: bool = False
    authority_version: str = PERF_CERT1_VERSION

    def __post_init__(self) -> None:
        if self.baseline_profile_kind != PROFILE_BASELINE:
            raise TrainingDataInputError("PERF-CERT1 baseline must remain the authoritative e3nn profile.")
        minimum = _nonnegative_finite(self.minimum_total_speedup, name="minimum_total_speedup")
        if minimum < 1.0:
            raise TrainingDataInputError("PERF-CERT1 minimum_total_speedup cannot be below 1.0.")
        if self.generated_default_change_authorized:
            raise TrainingDataInputError("PERF-CERT1 cannot directly authorize a generated-default change.")
        if self.authority_version != PERF_CERT1_VERSION:
            raise TrainingDataInputError("Unsupported PERF-CERT1 authority version.")
        object.__setattr__(self, "minimum_total_speedup", minimum)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_CERT1_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "baseline_profile_kind": self.baseline_profile_kind,
            "minimum_total_speedup": self.minimum_total_speedup,
            "require_positive_total_speedup": bool(self.require_positive_total_speedup),
            "require_exact_hard_decision_identity": bool(self.require_exact_hard_decision_identity),
            "require_exact_data6_selection_identity": bool(self.require_exact_data6_selection_identity),
            "require_exact_data7_selection_identity": bool(self.require_exact_data7_selection_identity),
            "require_exact_target_selection_identity": bool(self.require_exact_target_selection_identity),
            "require_replay_retention": bool(self.require_replay_retention),
            "require_eval2_pass": bool(self.require_eval2_pass),
            "require_available_deployment_pass": bool(self.require_available_deployment_pass),
            "require_available_physical_pass": bool(self.require_available_physical_pass),
            "require_locked_test_not_used_for_tuning": bool(self.require_locked_test_not_used_for_tuning),
            "generated_default_change_authorized": bool(self.generated_default_change_authorized),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfCert1Policy":
        if payload.get("schema") != PERF_CERT1_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 policy schema.")
        result = cls(
            baseline_profile_kind=str(payload["baseline_profile_kind"]),
            minimum_total_speedup=float(payload["minimum_total_speedup"]),
            require_positive_total_speedup=bool(payload["require_positive_total_speedup"]),
            require_exact_hard_decision_identity=bool(payload["require_exact_hard_decision_identity"]),
            require_exact_data6_selection_identity=bool(payload["require_exact_data6_selection_identity"]),
            require_exact_data7_selection_identity=bool(payload["require_exact_data7_selection_identity"]),
            require_exact_target_selection_identity=bool(payload["require_exact_target_selection_identity"]),
            require_replay_retention=bool(payload["require_replay_retention"]),
            require_eval2_pass=bool(payload["require_eval2_pass"]),
            require_available_deployment_pass=bool(payload["require_available_deployment_pass"]),
            require_available_physical_pass=bool(payload["require_available_physical_pass"]),
            require_locked_test_not_used_for_tuning=bool(payload["require_locked_test_not_used_for_tuning"]),
            generated_default_change_authorized=bool(payload["generated_default_change_authorized"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-CERT1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfCert1Telemetry:
    """End-to-end timing, throughput, memory, and recovery telemetry."""

    workload_digest: str
    preparation_wall_time_seconds: float
    target_data2b_wall_time_seconds: float
    target_data2b_families_per_second: float
    target_data2c_selection_scoring_seconds: float
    data6_wall_time_seconds: float
    data6_frames_per_second: float
    data6_peak_vram_bytes: int
    data6_reserved_vram_bytes: int
    data6_headroom_bytes: int
    training_wall_time_seconds: float
    training_updates_per_second: float
    evaluation_wall_time_seconds: float
    total_wall_time_seconds: float
    cuda_oom_count: int = 0
    cuda_backoff_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "workload_digest", validate_digest(self.workload_digest, name="workload_digest"))
        for name in (
            "preparation_wall_time_seconds", "target_data2b_wall_time_seconds",
            "target_data2b_families_per_second", "target_data2c_selection_scoring_seconds",
            "data6_wall_time_seconds", "data6_frames_per_second", "training_wall_time_seconds",
            "training_updates_per_second", "evaluation_wall_time_seconds", "total_wall_time_seconds",
        ):
            object.__setattr__(self, name, _nonnegative_finite(getattr(self, name), name=name))
        for name in (
            "data6_peak_vram_bytes", "data6_reserved_vram_bytes", "data6_headroom_bytes",
            "cuda_oom_count", "cuda_backoff_count",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if self.data6_reserved_vram_bytes and self.data6_peak_vram_bytes > self.data6_reserved_vram_bytes:
            raise TrainingDataInputError("PERF-CERT1 DATA6 peak VRAM cannot exceed reserved VRAM.")
        if self.total_wall_time_seconds <= 0.0:
            raise TrainingDataInputError("PERF-CERT1 total_wall_time_seconds must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_CERT1_TELEMETRY_SCHEMA,
            "workload_digest": self.workload_digest,
            "preparation_wall_time_seconds": self.preparation_wall_time_seconds,
            "target_data2b_wall_time_seconds": self.target_data2b_wall_time_seconds,
            "target_data2b_families_per_second": self.target_data2b_families_per_second,
            "target_data2c_selection_scoring_seconds": self.target_data2c_selection_scoring_seconds,
            "data6_wall_time_seconds": self.data6_wall_time_seconds,
            "data6_frames_per_second": self.data6_frames_per_second,
            "data6_peak_vram_bytes": self.data6_peak_vram_bytes,
            "data6_reserved_vram_bytes": self.data6_reserved_vram_bytes,
            "data6_headroom_bytes": self.data6_headroom_bytes,
            "training_wall_time_seconds": self.training_wall_time_seconds,
            "training_updates_per_second": self.training_updates_per_second,
            "evaluation_wall_time_seconds": self.evaluation_wall_time_seconds,
            "total_wall_time_seconds": self.total_wall_time_seconds,
            "cuda_oom_count": self.cuda_oom_count,
            "cuda_backoff_count": self.cuda_backoff_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfCert1Telemetry":
        if payload.get("schema") != PERF_CERT1_TELEMETRY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 telemetry schema.")
        result = cls(
            workload_digest=str(payload["workload_digest"]),
            preparation_wall_time_seconds=float(payload["preparation_wall_time_seconds"]),
            target_data2b_wall_time_seconds=float(payload["target_data2b_wall_time_seconds"]),
            target_data2b_families_per_second=float(payload["target_data2b_families_per_second"]),
            target_data2c_selection_scoring_seconds=float(payload["target_data2c_selection_scoring_seconds"]),
            data6_wall_time_seconds=float(payload["data6_wall_time_seconds"]),
            data6_frames_per_second=float(payload["data6_frames_per_second"]),
            data6_peak_vram_bytes=int(payload["data6_peak_vram_bytes"]),
            data6_reserved_vram_bytes=int(payload["data6_reserved_vram_bytes"]),
            data6_headroom_bytes=int(payload["data6_headroom_bytes"]),
            training_wall_time_seconds=float(payload["training_wall_time_seconds"]),
            training_updates_per_second=float(payload["training_updates_per_second"]),
            evaluation_wall_time_seconds=float(payload["evaluation_wall_time_seconds"]),
            total_wall_time_seconds=float(payload["total_wall_time_seconds"]),
            cuda_oom_count=int(payload.get("cuda_oom_count", 0)),
            cuda_backoff_count=int(payload.get("cuda_backoff_count", 0)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-CERT1 telemetry digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfCert1ProfileRecord:
    """One complete baseline, accelerated, or compatibility execution profile."""

    profile_id: str
    profile_kind: str
    source_kernel_mode: str
    training_kernel_mode: str
    scientific_source_digest: str
    source_execution_realization_digest: str
    training_execution_realization_digest: str
    dependency_lock_digest: str
    runtime_record_digest: str
    scientific_protocol_digest: str
    mace_mh1_sha256: str
    mace_mpa0_sha256: str
    target_head: str
    target_data2b_family_order_digest: str
    target_data2c_selection_digest: str
    data6_selection_digest: str
    data7_selection_digest: str
    descriptor_parity_passed: bool
    difficulty_parity_passed: bool
    pca_fps_parity_passed: bool
    replay_retention_passed: bool
    checkpoint_admissible: bool
    target_head_extraction_passed: bool
    selected_checkpoint_sha256: str
    target_head_sha256: str
    selected_target_size: int
    selected_seed: int
    target_validation_metric_name: str
    target_validation_metric: float
    replay_validation_metric_name: str
    replay_validation_metric: float
    eval2_passed: bool
    eval2_decision_digest: str
    deployment_verification_state: str
    deployment_verification_digest: str | None
    physical_verification_state: str
    physical_verification_digest: str | None
    telemetry: PerfCert1Telemetry
    locked_test_used_for_tuning: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "profile_id", _nonempty(self.profile_id, name="profile_id"))
        kind = str(self.profile_kind).strip()
        if kind not in PERF_CERT1_PROFILE_KINDS:
            raise TrainingDataInputError("PERF-CERT1 profile_kind is invalid.")
        object.__setattr__(self, "profile_kind", kind)
        source_mode = str(self.source_kernel_mode).strip()
        training_mode = str(self.training_kernel_mode).strip()
        if source_mode not in _ALLOWED_KERNEL_MODES or training_mode not in _ALLOWED_KERNEL_MODES:
            raise TrainingDataInputError("PERF-CERT1 kernel modes must be e3nn or cueq_pure.")
        expected_modes = {
            PROFILE_BASELINE: ("e3nn", "e3nn"),
            PROFILE_PHASE1: ("e3nn", "cueq_pure"),
            PROFILE_PHASE2: ("cueq_pure", "cueq_pure"),
        }
        if kind in expected_modes and (source_mode, training_mode) != expected_modes[kind]:
            raise TrainingDataInputError(f"PERF-CERT1 {kind} kernel modes violate the frozen profile definition.")
        object.__setattr__(self, "source_kernel_mode", source_mode)
        object.__setattr__(self, "training_kernel_mode", training_mode)
        for name in (
            "scientific_source_digest", "source_execution_realization_digest",
            "training_execution_realization_digest", "dependency_lock_digest", "runtime_record_digest",
            "scientific_protocol_digest", "mace_mh1_sha256", "mace_mpa0_sha256",
            "target_data2b_family_order_digest", "target_data2c_selection_digest",
            "data6_selection_digest", "data7_selection_digest", "selected_checkpoint_sha256",
            "target_head_sha256", "eval2_decision_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.mace_mh1_sha256 != PERF_CERT1_MH1_SHA256:
            raise TrainingDataInputError("PERF-CERT1 MACE-MH-1 identity is not the locked foundation model.")
        if self.mace_mpa0_sha256 != PERF_CERT1_MPA0_SHA256:
            raise TrainingDataInputError("PERF-CERT1 MACE-MPA-0 identity is not the locked foundation model.")
        if str(self.target_head).strip() != "omat_pbe":
            raise TrainingDataInputError("PERF-CERT1 target_head must remain omat_pbe.")
        object.__setattr__(self, "target_head", "omat_pbe")
        target_size = int(self.selected_target_size)
        if target_size <= 0:
            raise TrainingDataInputError("PERF-CERT1 selected_target_size must be positive.")
        object.__setattr__(self, "selected_target_size", target_size)
        object.__setattr__(self, "selected_seed", int(self.selected_seed))
        object.__setattr__(self, "target_validation_metric_name", _nonempty(self.target_validation_metric_name, name="target_validation_metric_name"))
        object.__setattr__(self, "replay_validation_metric_name", _nonempty(self.replay_validation_metric_name, name="replay_validation_metric_name"))
        object.__setattr__(self, "target_validation_metric", _finite(self.target_validation_metric, name="target_validation_metric"))
        object.__setattr__(self, "replay_validation_metric", _finite(self.replay_validation_metric, name="replay_validation_metric"))
        deployment = _verification(self.deployment_verification_state, name="deployment_verification_state")
        physical = _verification(self.physical_verification_state, name="physical_verification_state")
        object.__setattr__(self, "deployment_verification_state", deployment)
        object.__setattr__(self, "physical_verification_state", physical)
        for state_name, digest_name in (
            ("deployment_verification_state", "deployment_verification_digest"),
            ("physical_verification_state", "physical_verification_digest"),
        ):
            state = getattr(self, state_name)
            value = getattr(self, digest_name)
            if state == "not_available":
                if value is not None:
                    raise TrainingDataInputError(f"{digest_name} must be absent when verification is unavailable.")
            else:
                if value is None:
                    raise TrainingDataInputError(f"{digest_name} is required for an available verification decision.")
                object.__setattr__(self, digest_name, validate_digest(value, name=digest_name))

    @property
    def hard_decision_digest(self) -> str:
        return digest({
            "schema": "mdstats.perf-cert1-hard-decisions.v1",
            "target_data2b_family_order_digest": self.target_data2b_family_order_digest,
            "target_data2c_selection_digest": self.target_data2c_selection_digest,
            "data6_selection_digest": self.data6_selection_digest,
            "data7_selection_digest": self.data7_selection_digest,
            "selected_target_size": self.selected_target_size,
            "selected_seed": self.selected_seed,
            "replay_retention_passed": bool(self.replay_retention_passed),
            "checkpoint_admissible": bool(self.checkpoint_admissible),
            "target_head_extraction_passed": bool(self.target_head_extraction_passed),
            "eval2_passed": bool(self.eval2_passed),
            "deployment_verification_state": self.deployment_verification_state,
            "physical_verification_state": self.physical_verification_state,
        })

    @property
    def hard_science_passed(self) -> bool:
        return bool(
            self.descriptor_parity_passed
            and self.difficulty_parity_passed
            and self.pca_fps_parity_passed
            and self.replay_retention_passed
            and self.checkpoint_admissible
            and self.target_head_extraction_passed
            and self.eval2_passed
            and self.deployment_verification_state != "fail"
            and self.physical_verification_state != "fail"
            and not self.locked_test_used_for_tuning
        )

    @property
    def execution_profile_digest(self) -> str:
        return digest({
            "schema": "mdstats.perf-cert1-execution-profile.v1",
            "profile_id": self.profile_id,
            "profile_kind": self.profile_kind,
            "source_kernel_mode": self.source_kernel_mode,
            "training_kernel_mode": self.training_kernel_mode,
            "source_execution_realization_digest": self.source_execution_realization_digest,
            "training_execution_realization_digest": self.training_execution_realization_digest,
            "dependency_lock_digest": self.dependency_lock_digest,
            "runtime_record_digest": self.runtime_record_digest,
            "telemetry_workload_digest": self.telemetry.workload_digest,
        })

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_CERT1_PROFILE_SCHEMA,
            "profile_id": self.profile_id,
            "profile_kind": self.profile_kind,
            "source_kernel_mode": self.source_kernel_mode,
            "training_kernel_mode": self.training_kernel_mode,
            "scientific_source_digest": self.scientific_source_digest,
            "source_execution_realization_digest": self.source_execution_realization_digest,
            "training_execution_realization_digest": self.training_execution_realization_digest,
            "dependency_lock_digest": self.dependency_lock_digest,
            "runtime_record_digest": self.runtime_record_digest,
            "scientific_protocol_digest": self.scientific_protocol_digest,
            "mace_mh1_sha256": self.mace_mh1_sha256,
            "mace_mpa0_sha256": self.mace_mpa0_sha256,
            "target_head": self.target_head,
            "target_data2b_family_order_digest": self.target_data2b_family_order_digest,
            "target_data2c_selection_digest": self.target_data2c_selection_digest,
            "data6_selection_digest": self.data6_selection_digest,
            "data7_selection_digest": self.data7_selection_digest,
            "descriptor_parity_passed": bool(self.descriptor_parity_passed),
            "difficulty_parity_passed": bool(self.difficulty_parity_passed),
            "pca_fps_parity_passed": bool(self.pca_fps_parity_passed),
            "replay_retention_passed": bool(self.replay_retention_passed),
            "checkpoint_admissible": bool(self.checkpoint_admissible),
            "target_head_extraction_passed": bool(self.target_head_extraction_passed),
            "selected_checkpoint_sha256": self.selected_checkpoint_sha256,
            "target_head_sha256": self.target_head_sha256,
            "selected_target_size": self.selected_target_size,
            "selected_seed": self.selected_seed,
            "target_validation_metric_name": self.target_validation_metric_name,
            "target_validation_metric": self.target_validation_metric,
            "replay_validation_metric_name": self.replay_validation_metric_name,
            "replay_validation_metric": self.replay_validation_metric,
            "eval2_passed": bool(self.eval2_passed),
            "eval2_decision_digest": self.eval2_decision_digest,
            "deployment_verification_state": self.deployment_verification_state,
            "deployment_verification_digest": self.deployment_verification_digest,
            "physical_verification_state": self.physical_verification_state,
            "physical_verification_digest": self.physical_verification_digest,
            "locked_test_used_for_tuning": bool(self.locked_test_used_for_tuning),
            "hard_decision_digest": self.hard_decision_digest,
            "hard_science_passed": self.hard_science_passed,
            "execution_profile_digest": self.execution_profile_digest,
            "telemetry": self.telemetry.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfCert1ProfileRecord":
        if payload.get("schema") != PERF_CERT1_PROFILE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 profile schema.")
        result = cls(
            profile_id=str(payload["profile_id"]), profile_kind=str(payload["profile_kind"]),
            source_kernel_mode=str(payload["source_kernel_mode"]), training_kernel_mode=str(payload["training_kernel_mode"]),
            scientific_source_digest=str(payload["scientific_source_digest"]),
            source_execution_realization_digest=str(payload["source_execution_realization_digest"]),
            training_execution_realization_digest=str(payload["training_execution_realization_digest"]),
            dependency_lock_digest=str(payload["dependency_lock_digest"]), runtime_record_digest=str(payload["runtime_record_digest"]),
            scientific_protocol_digest=str(payload["scientific_protocol_digest"]), mace_mh1_sha256=str(payload["mace_mh1_sha256"]),
            mace_mpa0_sha256=str(payload["mace_mpa0_sha256"]), target_head=str(payload["target_head"]),
            target_data2b_family_order_digest=str(payload["target_data2b_family_order_digest"]),
            target_data2c_selection_digest=str(payload["target_data2c_selection_digest"]),
            data6_selection_digest=str(payload["data6_selection_digest"]), data7_selection_digest=str(payload["data7_selection_digest"]),
            descriptor_parity_passed=bool(payload["descriptor_parity_passed"]), difficulty_parity_passed=bool(payload["difficulty_parity_passed"]),
            pca_fps_parity_passed=bool(payload["pca_fps_parity_passed"]), replay_retention_passed=bool(payload["replay_retention_passed"]),
            checkpoint_admissible=bool(payload["checkpoint_admissible"]), target_head_extraction_passed=bool(payload["target_head_extraction_passed"]),
            selected_checkpoint_sha256=str(payload["selected_checkpoint_sha256"]), target_head_sha256=str(payload["target_head_sha256"]),
            selected_target_size=int(payload["selected_target_size"]), selected_seed=int(payload["selected_seed"]),
            target_validation_metric_name=str(payload["target_validation_metric_name"]), target_validation_metric=float(payload["target_validation_metric"]),
            replay_validation_metric_name=str(payload["replay_validation_metric_name"]), replay_validation_metric=float(payload["replay_validation_metric"]),
            eval2_passed=bool(payload["eval2_passed"]), eval2_decision_digest=str(payload["eval2_decision_digest"]),
            deployment_verification_state=str(payload["deployment_verification_state"]),
            deployment_verification_digest=payload.get("deployment_verification_digest"),
            physical_verification_state=str(payload["physical_verification_state"]),
            physical_verification_digest=payload.get("physical_verification_digest"),
            telemetry=PerfCert1Telemetry.from_dict(payload["telemetry"]),
            locked_test_used_for_tuning=bool(payload.get("locked_test_used_for_tuning", False)),
        )
        for name, expected in (
            ("hard_decision_digest", result.hard_decision_digest),
            ("hard_science_passed", result.hard_science_passed),
            ("execution_profile_digest", result.execution_profile_digest),
        ):
            if payload.get(name) not in (None, expected):
                raise TrainingDataSerializationError(f"PERF-CERT1 profile {name} mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-CERT1 profile digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfCert1UpstreamAuthority:
    """Content-addressed handoff from CUEQ-PHASE1 and optional CUEQ-PHASE2."""

    cueq_dep1_runtime_digest: str
    cueq_phase1_qualification_digest: str
    cueq_phase1_passed: bool
    phase1_training_authorized: bool
    cueq_phase2_qualification_digest: str
    cueq_phase2_passed: bool
    phase2_source_authorized: bool
    phase2_data6_authorized: bool
    phase2_source_evaluation_authorized: bool
    phase2_pseudolabel_authorized: bool

    def __post_init__(self) -> None:
        for name in ("cueq_dep1_runtime_digest", "cueq_phase1_qualification_digest", "cueq_phase2_qualification_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.cueq_phase1_passed != self.phase1_training_authorized:
            raise TrainingDataInputError("PERF-CERT1 PHASE1 pass and training authorization must agree.")
        if self.cueq_phase2_passed and not (
            self.phase2_source_authorized and self.phase2_data6_authorized and self.phase2_source_evaluation_authorized
        ):
            raise TrainingDataInputError("Passing PERF-CERT1 PHASE2 authority must authorize its required source/DATA6 paths.")
        if not self.cueq_phase2_passed and any((self.phase2_source_authorized, self.phase2_data6_authorized, self.phase2_source_evaluation_authorized, self.phase2_pseudolabel_authorized)):
            raise TrainingDataInputError("Failed PERF-CERT1 PHASE2 authority cannot authorize execution.")

    @classmethod
    def from_qualifications(
        cls,
        phase1: CueqPhase1QualificationRecord,
        phase2: CueqPhase2QualificationRecord,
    ) -> "PerfCert1UpstreamAuthority":
        if phase1.cueq_dep1_runtime_digest != phase2.cueq_dep1_runtime_digest:
            raise TrainingDataInputError("PERF-CERT1 PHASE1 and PHASE2 must bind to the same CUEQ-DEP1 runtime.")
        return cls(
            cueq_dep1_runtime_digest=phase1.cueq_dep1_runtime_digest,
            cueq_phase1_qualification_digest=phase1.content_digest,
            cueq_phase1_passed=phase1.passed,
            phase1_training_authorized=phase1.phase_separated_training_authorized,
            cueq_phase2_qualification_digest=phase2.content_digest,
            cueq_phase2_passed=phase2.passed,
            phase2_source_authorized=phase2.selected_head_source_cueq_execution_authorized,
            phase2_data6_authorized=phase2.data6_cueq_execution_authorized,
            phase2_source_evaluation_authorized=phase2.source_evaluation_cueq_execution_authorized,
            phase2_pseudolabel_authorized=phase2.pseudolabel_cueq_execution_authorized,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_CERT1_UPSTREAM_SCHEMA,
            "cueq_dep1_runtime_digest": self.cueq_dep1_runtime_digest,
            "cueq_phase1_qualification_digest": self.cueq_phase1_qualification_digest,
            "cueq_phase1_passed": bool(self.cueq_phase1_passed),
            "phase1_training_authorized": bool(self.phase1_training_authorized),
            "cueq_phase2_qualification_digest": self.cueq_phase2_qualification_digest,
            "cueq_phase2_passed": bool(self.cueq_phase2_passed),
            "phase2_source_authorized": bool(self.phase2_source_authorized),
            "phase2_data6_authorized": bool(self.phase2_data6_authorized),
            "phase2_source_evaluation_authorized": bool(self.phase2_source_evaluation_authorized),
            "phase2_pseudolabel_authorized": bool(self.phase2_pseudolabel_authorized),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfCert1UpstreamAuthority":
        if payload.get("schema") != PERF_CERT1_UPSTREAM_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 upstream-authority schema.")
        result = cls(
            cueq_dep1_runtime_digest=str(payload["cueq_dep1_runtime_digest"]),
            cueq_phase1_qualification_digest=str(payload["cueq_phase1_qualification_digest"]),
            cueq_phase1_passed=bool(payload["cueq_phase1_passed"]),
            phase1_training_authorized=bool(payload["phase1_training_authorized"]),
            cueq_phase2_qualification_digest=str(payload["cueq_phase2_qualification_digest"]),
            cueq_phase2_passed=bool(payload["cueq_phase2_passed"]),
            phase2_source_authorized=bool(payload["phase2_source_authorized"]),
            phase2_data6_authorized=bool(payload["phase2_data6_authorized"]),
            phase2_source_evaluation_authorized=bool(payload["phase2_source_evaluation_authorized"]),
            phase2_pseudolabel_authorized=bool(payload["phase2_pseudolabel_authorized"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-CERT1 upstream-authority digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfCert1ProfileAssessment:
    """Baseline-relative scientific/performance assessment for one profile."""

    policy: PerfCert1Policy
    upstream: PerfCert1UpstreamAuthority
    baseline: PerfCert1ProfileRecord
    candidate: PerfCert1ProfileRecord
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        reasons: list[str] = []
        if self.baseline.profile_kind != self.policy.baseline_profile_kind:
            reasons.append("authoritative_baseline_profile_kind")
        if not self.baseline.hard_science_passed:
            reasons.append("authoritative_baseline_science")
        if self.candidate.profile_kind == PROFILE_BASELINE:
            reasons.append("candidate_cannot_be_authoritative_baseline")
        if self.baseline.profile_id == self.candidate.profile_id:
            reasons.append("candidate_profile_id_must_differ")
        if self.baseline.scientific_source_digest != self.candidate.scientific_source_digest:
            reasons.append("scientific_source_semantics")
        if self.baseline.scientific_protocol_digest != self.candidate.scientific_protocol_digest:
            reasons.append("scientific_protocol_identity")
        if self.baseline.telemetry.workload_digest != self.candidate.telemetry.workload_digest:
            reasons.append("performance_workload_identity")
        if self.baseline.mace_mh1_sha256 != self.candidate.mace_mh1_sha256 or self.baseline.mace_mpa0_sha256 != self.candidate.mace_mpa0_sha256:
            reasons.append("foundation_model_identity")
        if self.baseline.target_head != self.candidate.target_head:
            reasons.append("target_head_identity")
        if self.policy.require_locked_test_not_used_for_tuning and self.candidate.locked_test_used_for_tuning:
            reasons.append("locked_test_used_for_tuning")
        if not self.candidate.hard_science_passed:
            reasons.append("candidate_hard_science")
        if self.policy.require_exact_hard_decision_identity and self.baseline.hard_decision_digest != self.candidate.hard_decision_digest:
            reasons.append("hard_scientific_decision_identity")
        if self.policy.require_exact_target_selection_identity:
            if self.baseline.target_data2b_family_order_digest != self.candidate.target_data2b_family_order_digest:
                reasons.append("target_data2b_family_order_identity")
            if self.baseline.target_data2c_selection_digest != self.candidate.target_data2c_selection_digest:
                reasons.append("target_data2c_selection_identity")
        if self.policy.require_exact_data6_selection_identity and self.baseline.data6_selection_digest != self.candidate.data6_selection_digest:
            reasons.append("data6_selection_identity")
        if self.policy.require_exact_data7_selection_identity and self.baseline.data7_selection_digest != self.candidate.data7_selection_digest:
            reasons.append("data7_selection_identity")
        if self.policy.require_replay_retention and not self.candidate.replay_retention_passed:
            reasons.append("replay_retention_pass")
        if self.policy.require_eval2_pass and not self.candidate.eval2_passed:
            reasons.append("eval2_pass")
        if self.policy.require_available_deployment_pass:
            if self.candidate.deployment_verification_state == "fail":
                reasons.append("deployment_verification_pass")
            if self.baseline.deployment_verification_state != "not_available" and self.candidate.deployment_verification_state == "not_available":
                reasons.append("candidate_missing_available_deployment_verification")
        if self.policy.require_available_physical_pass:
            if self.candidate.physical_verification_state == "fail":
                reasons.append("physical_verification_pass")
            if self.baseline.physical_verification_state != "not_available" and self.candidate.physical_verification_state == "not_available":
                reasons.append("candidate_missing_available_physical_verification")

        if self.candidate.training_kernel_mode == "cueq_pure":
            if not self.upstream.cueq_phase1_passed or not self.upstream.phase1_training_authorized:
                reasons.append("CUEQ_PHASE1_TRAINING_QUALIFICATION")
            if self.candidate.runtime_record_digest != self.upstream.cueq_dep1_runtime_digest:
                reasons.append("cueq_training_runtime_identity")
        if self.candidate.source_kernel_mode == "cueq_pure":
            if not self.upstream.cueq_phase2_passed or not (
                self.upstream.phase2_source_authorized and self.upstream.phase2_data6_authorized and self.upstream.phase2_source_evaluation_authorized
            ):
                reasons.append("CUEQ_PHASE2_SOURCE_DATA6_QUALIFICATION")
            if self.candidate.runtime_record_digest != self.upstream.cueq_dep1_runtime_digest:
                reasons.append("cueq_source_runtime_identity")

        if self.candidate.profile_kind in (PROFILE_PHASE1, PROFILE_PHASE2):
            if self.policy.require_positive_total_speedup and not self.performance_benefit_passed:
                reasons.append("measured_end_to_end_operational_benefit")
        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def total_speedup(self) -> float:
        return float(self.baseline.telemetry.total_wall_time_seconds / self.candidate.telemetry.total_wall_time_seconds)

    @property
    def performance_benefit_passed(self) -> bool:
        speedup = self.total_speedup
        if self.policy.require_positive_total_speedup:
            return bool(speedup > self.policy.minimum_total_speedup)
        return bool(speedup >= self.policy.minimum_total_speedup)

    @property
    def recommendation_eligible(self) -> bool:
        return self.candidate.profile_kind in (PROFILE_PHASE1, PROFILE_PHASE2)

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_CERT1_ASSESSMENT_SCHEMA,
            "policy": self.policy.to_dict(),
            "upstream": self.upstream.to_dict(),
            "baseline": self.baseline.to_dict(),
            "candidate": self.candidate.to_dict(),
            "total_speedup": self.total_speedup,
            "performance_benefit_passed": self.performance_benefit_passed,
            "recommendation_eligible": self.recommendation_eligible,
            "blocking_reasons": list(self.blocking_reasons),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfCert1ProfileAssessment":
        if payload.get("schema") != PERF_CERT1_ASSESSMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 assessment schema.")
        result = cls(
            policy=PerfCert1Policy.from_dict(payload["policy"]),
            upstream=PerfCert1UpstreamAuthority.from_dict(payload["upstream"]),
            baseline=PerfCert1ProfileRecord.from_dict(payload["baseline"]),
            candidate=PerfCert1ProfileRecord.from_dict(payload["candidate"]),
        )
        for name, expected in (
            ("total_speedup", result.total_speedup),
            ("performance_benefit_passed", result.performance_benefit_passed),
            ("recommendation_eligible", result.recommendation_eligible),
            ("passed", result.passed),
        ):
            if payload.get(name) not in (None, expected):
                raise TrainingDataSerializationError(f"PERF-CERT1 assessment {name} mismatch.")
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("PERF-CERT1 assessment blockers mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-CERT1 assessment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfCert1QualificationRecord:
    """Gate-level end-to-end certification and recommendation record."""

    policy: PerfCert1Policy
    upstream: PerfCert1UpstreamAuthority
    baseline: PerfCert1ProfileRecord | None = None
    candidates: tuple[PerfCert1ProfileRecord, ...] = ()
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        candidates = tuple(self.candidates)
        ids = [item.profile_id for item in candidates]
        if len(ids) != len(set(ids)):
            raise TrainingDataInputError("PERF-CERT1 candidate profile IDs must be unique.")
        if self.baseline is not None and self.baseline.profile_id in set(ids):
            raise TrainingDataInputError("PERF-CERT1 baseline and candidate profile IDs must be distinct.")
        reasons: list[str] = []
        if self.baseline is None:
            reasons.append("authoritative_e3nn_baseline_missing")
        elif self.baseline.profile_kind != self.policy.baseline_profile_kind or not self.baseline.hard_science_passed:
            reasons.append("authoritative_e3nn_baseline_failed")
        accelerated = [item for item in candidates if item.profile_kind in (PROFILE_PHASE1, PROFILE_PHASE2)]
        if not accelerated:
            reasons.append("accelerated_profile_evidence_missing")
        if not self.upstream.cueq_phase1_passed:
            reasons.append("CUEQ_PHASE1_TRAINING_QUALIFICATION")
        if self.baseline is not None and accelerated:
            if not any(item.passed and item.recommendation_eligible for item in self.assessments):
                reasons.append("no_accelerated_profile_certified")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def assessments(self) -> tuple[PerfCert1ProfileAssessment, ...]:
        if self.baseline is None:
            return ()
        return tuple(
            PerfCert1ProfileAssessment(policy=self.policy, upstream=self.upstream, baseline=self.baseline, candidate=item)
            for item in self.candidates
        )

    @property
    def passing_accelerated_assessments(self) -> tuple[PerfCert1ProfileAssessment, ...]:
        return tuple(item for item in self.assessments if item.passed and item.recommendation_eligible)

    @property
    def recommended_profile_id(self) -> str | None:
        passing = self.passing_accelerated_assessments
        if not passing:
            return None
        return min(
            passing,
            key=lambda item: (item.candidate.telemetry.total_wall_time_seconds, item.candidate.profile_id),
        ).candidate.profile_id

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    @property
    def phase_separated_acceleration_profile_recommended(self) -> bool:
        return bool(self.passed and self.recommended_profile_id is not None)

    @property
    def generated_default_change_authorized(self) -> bool:
        return False

    @property
    def generated_default_policy_revision_required(self) -> bool:
        return bool(self.phase_separated_acceleration_profile_recommended)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PERF_CERT1_QUALIFICATION_SCHEMA,
            "authority_version": PERF_CERT1_VERSION,
            "policy": self.policy.to_dict(),
            "upstream": self.upstream.to_dict(),
            "baseline": None if self.baseline is None else self.baseline.to_dict(),
            "candidates": [item.to_dict() for item in self.candidates],
            "assessments": [item.to_dict() for item in self.assessments],
            "recommended_profile_id": self.recommended_profile_id,
            "blocking_reasons": list(self.blocking_reasons),
            "passed": self.passed,
            "authorization": {
                "phase_separated_acceleration_profile_recommended": self.phase_separated_acceleration_profile_recommended,
                "generated_default_change_authorized": self.generated_default_change_authorized,
                "generated_default_policy_revision_required": self.generated_default_policy_revision_required,
            },
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfCert1QualificationRecord":
        if payload.get("schema") != PERF_CERT1_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 qualification schema.")
        if payload.get("authority_version") != PERF_CERT1_VERSION:
            raise TrainingDataSerializationError("Unsupported PERF-CERT1 authority version.")
        result = cls(
            policy=PerfCert1Policy.from_dict(payload["policy"]),
            upstream=PerfCert1UpstreamAuthority.from_dict(payload["upstream"]),
            baseline=None if payload.get("baseline") is None else PerfCert1ProfileRecord.from_dict(payload["baseline"]),
            candidates=tuple(PerfCert1ProfileRecord.from_dict(item) for item in payload.get("candidates", ())),
        )
        serialized_assessments = payload.get("assessments", [])
        expected_assessments = [item.to_dict() for item in result.assessments]
        if serialized_assessments not in ([], expected_assessments):
            raise TrainingDataSerializationError("PERF-CERT1 derived assessments mismatch.")
        if payload.get("recommended_profile_id") not in (None, result.recommended_profile_id):
            raise TrainingDataSerializationError("PERF-CERT1 recommendation mismatch.")
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("PERF-CERT1 qualification blockers mismatch.")
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("PERF-CERT1 qualification pass state mismatch.")
        auth = payload.get("authorization", {})
        expected_auth = result._payload()["authorization"]
        if auth not in ({}, expected_auth):
            raise TrainingDataSerializationError("PERF-CERT1 authorization mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-CERT1 qualification digest mismatch.")
        return result


def build_perf_cert1_qualification(
    *,
    phase1: CueqPhase1QualificationRecord,
    phase2: CueqPhase2QualificationRecord,
    baseline: PerfCert1ProfileRecord | None = None,
    candidates: Sequence[PerfCert1ProfileRecord] = (),
    policy: PerfCert1Policy | None = None,
) -> PerfCert1QualificationRecord:
    """Build PERF-CERT1 from the independent upstream accelerator authorities."""

    active = policy or PerfCert1Policy()
    upstream = PerfCert1UpstreamAuthority.from_qualifications(phase1, phase2)
    return PerfCert1QualificationRecord(
        policy=active,
        upstream=upstream,
        baseline=baseline,
        candidates=tuple(candidates),
    )
