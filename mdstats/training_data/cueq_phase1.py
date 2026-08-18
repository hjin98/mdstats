"""CUEQ-PHASE1 training-only paired qualification authority.

This gate deliberately separates source-foundation execution from the training
realization.  Source inference, DATA6, pseudolabel generation, source-baseline
evaluation, and their cache identities remain e3nn.  Only training from the
EXTRACT1-qualified selected-head checkpoint may use pure cuEquivariance.

The module is a control-plane/scientific-evidence authority.  It does not claim
GPU qualification on the development host.  Positive CUEQ-DEP1 runtime evidence
and paired short/full training trajectories are required before a phase-separated
CuEq training policy becomes authorized.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .accelerator_runtime_freeze import CueqDep1RuntimeRecord

CUEQ_PHASE1_POLICY_SCHEMA = "mdstats.cueq-phase1-policy.v1"
CUEQ_PHASE1_TRAJECTORY_SCHEMA = "mdstats.cueq-phase1-trajectory.v1"
CUEQ_PHASE1_PAIR_SCHEMA = "mdstats.cueq-phase1-paired-assessment.v1"
CUEQ_PHASE1_QUALIFICATION_SCHEMA = "mdstats.cueq-phase1-qualification.v1"
CUEQ_PHASE1_VERSION = "mdstats.cueq-phase1.training-only.2026-08.v1"

_SHORT_ROLE = "short"
_FULL_ROLE = "full"
_ALLOWED_ROLES = {_SHORT_ROLE, _FULL_ROLE}
_ALLOWED_PHYSICAL_STATES = {"pass", "fail", "not_available"}


def _nonnegative_finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and >= 0.")
    return result


def _finite(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise TrainingDataInputError(f"{name} must be finite.")
    return result


@dataclass(frozen=True, slots=True)
class CueqPhase1Policy:
    """Frozen CUEQ-PHASE1 scientific and execution-separation policy."""

    short_epoch_budget: int = 8
    minimum_full_pairs: int = 1
    source_inference_kernel_mode: str = "e3nn"
    reference_training_kernel_mode: str = "e3nn"
    candidate_training_kernel_mode: str = "cueq_pure"
    require_identical_protocol: bool = True
    require_hard_decision_agreement: bool = True
    require_finite_training: bool = True
    require_target_head_extraction: bool = True
    require_eval2_pass: bool = True
    require_available_physical_pass: bool = True
    authority_version: str = CUEQ_PHASE1_VERSION

    def __post_init__(self) -> None:
        short = int(self.short_epoch_budget)
        if not 5 <= short <= 10:
            raise TrainingDataInputError("CUEQ-PHASE1 short_epoch_budget must lie in [5, 10].")
        minimum_full = int(self.minimum_full_pairs)
        if minimum_full < 1:
            raise TrainingDataInputError("CUEQ-PHASE1 requires at least one representative full pair.")
        if self.source_inference_kernel_mode != "e3nn":
            raise TrainingDataInputError("CUEQ-PHASE1 source inference must remain e3nn.")
        if self.reference_training_kernel_mode != "e3nn":
            raise TrainingDataInputError("CUEQ-PHASE1 reference training must use e3nn.")
        if self.candidate_training_kernel_mode != "cueq_pure":
            raise TrainingDataInputError("CUEQ-PHASE1 candidate training must use cueq_pure.")
        if self.authority_version != CUEQ_PHASE1_VERSION:
            raise TrainingDataInputError("Unsupported CUEQ-PHASE1 authority version.")
        object.__setattr__(self, "short_epoch_budget", short)
        object.__setattr__(self, "minimum_full_pairs", minimum_full)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE1_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "short_epoch_budget": self.short_epoch_budget,
            "minimum_full_pairs": self.minimum_full_pairs,
            "source_inference_kernel_mode": self.source_inference_kernel_mode,
            "reference_training_kernel_mode": self.reference_training_kernel_mode,
            "candidate_training_kernel_mode": self.candidate_training_kernel_mode,
            "require_identical_protocol": self.require_identical_protocol,
            "require_hard_decision_agreement": self.require_hard_decision_agreement,
            "require_finite_training": self.require_finite_training,
            "require_target_head_extraction": self.require_target_head_extraction,
            "require_eval2_pass": self.require_eval2_pass,
            "require_available_physical_pass": self.require_available_physical_pass,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase1Policy":
        if payload.get("schema") != CUEQ_PHASE1_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE1 policy schema.")
        result = cls(
            short_epoch_budget=int(payload["short_epoch_budget"]),
            minimum_full_pairs=int(payload["minimum_full_pairs"]),
            source_inference_kernel_mode=str(payload["source_inference_kernel_mode"]),
            reference_training_kernel_mode=str(payload["reference_training_kernel_mode"]),
            candidate_training_kernel_mode=str(payload["candidate_training_kernel_mode"]),
            require_identical_protocol=bool(payload["require_identical_protocol"]),
            require_hard_decision_agreement=bool(payload["require_hard_decision_agreement"]),
            require_finite_training=bool(payload["require_finite_training"]),
            require_target_head_extraction=bool(payload["require_target_head_extraction"]),
            require_eval2_pass=bool(payload["require_eval2_pass"]),
            require_available_physical_pass=bool(payload["require_available_physical_pass"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqPhase1TrajectoryRecord:
    """One side of a paired e3nn/CuEq training trajectory.

    The protocol identity intentionally enumerates the inputs that must be held
    identical across the pair.  Final checkpoint bytes are *not* compared:
    different accelerator kernels may produce different valid optimization
    trajectories.  Acceptance is based on the existing scientific decisions.
    """

    role: str
    training_kernel_mode: str
    runtime_record_digest: str
    source_foundation_digest: str
    starting_checkpoint_sha256: str
    selected_head_qualification_digest: str
    data8_bundle_digest: str
    optimizer_semantics_digest: str
    split_identity_digest: str
    order_identity_digest: str
    objective_policy_digest: str
    lr_schedule_digest: str
    stopping_policy_digest: str
    replay_policy_digest: str
    validation_protocol_digest: str
    evaluation_protocol_digest: str
    seed: int
    dtype: str
    epoch_budget: int
    update_budget: int
    completed_epochs: int
    gradient_updates: int
    target_validation_metric_name: str
    target_validation_metric: float
    replay_validation_metric_name: str
    replay_validation_metric: float
    replay_retention_passed: bool
    losses_finite: bool
    gradients_finite: bool
    parameters_finite: bool
    checkpoint_admissible: bool
    checkpoint_ranking_digest: str
    target_head_extraction_passed: bool
    target_head_sha256: str | None
    eval2_passed: bool
    eval2_decision_digest: str
    physical_verification_state: str = "not_available"
    physical_verification_digest: str | None = None
    wall_time_seconds: float = 0.0
    updates_per_second: float = 0.0
    peak_vram_bytes: int = 0
    reserved_vram_bytes: int = 0
    representative_full_trajectory: bool = False

    def __post_init__(self) -> None:
        role = str(self.role).strip().lower()
        if role not in _ALLOWED_ROLES:
            raise TrainingDataInputError("CUEQ-PHASE1 trajectory role must be 'short' or 'full'.")
        mode = str(self.training_kernel_mode).strip()
        if mode not in {"e3nn", "cueq_pure"}:
            raise TrainingDataInputError("CUEQ-PHASE1 training kernel must be e3nn or cueq_pure.")
        for name in (
            "runtime_record_digest", "source_foundation_digest", "starting_checkpoint_sha256",
            "selected_head_qualification_digest", "data8_bundle_digest", "optimizer_semantics_digest",
            "split_identity_digest", "order_identity_digest", "objective_policy_digest",
            "lr_schedule_digest", "stopping_policy_digest", "replay_policy_digest",
            "validation_protocol_digest", "evaluation_protocol_digest", "checkpoint_ranking_digest",
            "eval2_decision_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.target_head_sha256 is not None:
            object.__setattr__(self, "target_head_sha256", validate_digest(self.target_head_sha256, name="target_head_sha256"))
        if self.physical_verification_digest is not None:
            object.__setattr__(self, "physical_verification_digest", validate_digest(self.physical_verification_digest, name="physical_verification_digest"))
        dtype = str(self.dtype).strip()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("CUEQ-PHASE1 dtype must be float32 or float64.")
        epoch_budget = int(self.epoch_budget)
        update_budget = int(self.update_budget)
        completed = int(self.completed_epochs)
        updates = int(self.gradient_updates)
        if min(epoch_budget, update_budget, completed, updates) < 0 or epoch_budget < 1 or update_budget < 1:
            raise TrainingDataInputError("CUEQ-PHASE1 trajectory budgets/counts are invalid.")
        if completed > epoch_budget or updates > update_budget:
            raise TrainingDataInputError("CUEQ-PHASE1 completed work cannot exceed the frozen budget.")
        physical = str(self.physical_verification_state).strip().lower()
        if physical not in _ALLOWED_PHYSICAL_STATES:
            raise TrainingDataInputError("CUEQ-PHASE1 physical verification state is invalid.")
        if physical == "not_available" and self.physical_verification_digest is not None:
            raise TrainingDataInputError("Unavailable physical verification cannot carry a decision digest.")
        if physical != "not_available" and self.physical_verification_digest is None:
            raise TrainingDataInputError("Available physical verification requires a decision digest.")
        if self.target_head_extraction_passed and self.target_head_sha256 is None:
            raise TrainingDataInputError("Passing target-head extraction requires target_head_sha256.")
        if role == _SHORT_ROLE and self.representative_full_trajectory:
            raise TrainingDataInputError("A short trajectory cannot be marked representative_full_trajectory.")
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "training_kernel_mode", mode)
        object.__setattr__(self, "dtype", dtype)
        object.__setattr__(self, "seed", int(self.seed))
        object.__setattr__(self, "epoch_budget", epoch_budget)
        object.__setattr__(self, "update_budget", update_budget)
        object.__setattr__(self, "completed_epochs", completed)
        object.__setattr__(self, "gradient_updates", updates)
        object.__setattr__(self, "target_validation_metric", _finite(self.target_validation_metric, name="target_validation_metric"))
        object.__setattr__(self, "replay_validation_metric", _finite(self.replay_validation_metric, name="replay_validation_metric"))
        object.__setattr__(self, "wall_time_seconds", _nonnegative_finite(self.wall_time_seconds, name="wall_time_seconds"))
        object.__setattr__(self, "updates_per_second", _nonnegative_finite(self.updates_per_second, name="updates_per_second"))
        object.__setattr__(self, "peak_vram_bytes", int(self.peak_vram_bytes))
        object.__setattr__(self, "reserved_vram_bytes", int(self.reserved_vram_bytes))
        object.__setattr__(self, "physical_verification_state", physical)
        if self.peak_vram_bytes < 0 or self.reserved_vram_bytes < 0:
            raise TrainingDataInputError("CUEQ-PHASE1 VRAM telemetry cannot be negative.")
        if self.reserved_vram_bytes and self.peak_vram_bytes > self.reserved_vram_bytes:
            raise TrainingDataInputError("CUEQ-PHASE1 peak allocated VRAM cannot exceed reserved VRAM telemetry.")

    @property
    def common_protocol_payload(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "runtime_record_digest": self.runtime_record_digest,
            "source_foundation_digest": self.source_foundation_digest,
            "starting_checkpoint_sha256": self.starting_checkpoint_sha256,
            "selected_head_qualification_digest": self.selected_head_qualification_digest,
            "data8_bundle_digest": self.data8_bundle_digest,
            "optimizer_semantics_digest": self.optimizer_semantics_digest,
            "split_identity_digest": self.split_identity_digest,
            "order_identity_digest": self.order_identity_digest,
            "objective_policy_digest": self.objective_policy_digest,
            "lr_schedule_digest": self.lr_schedule_digest,
            "stopping_policy_digest": self.stopping_policy_digest,
            "replay_policy_digest": self.replay_policy_digest,
            "validation_protocol_digest": self.validation_protocol_digest,
            "evaluation_protocol_digest": self.evaluation_protocol_digest,
            "seed": self.seed,
            "dtype": self.dtype,
            "epoch_budget": self.epoch_budget,
            "update_budget": self.update_budget,
        }

    @property
    def common_protocol_digest(self) -> str:
        return digest(self.common_protocol_payload)

    @property
    def finite_training(self) -> bool:
        return bool(self.losses_finite and self.gradients_finite and self.parameters_finite)

    @property
    def completed_budget(self) -> bool:
        return bool(self.completed_epochs == self.epoch_budget and self.gradient_updates == self.update_budget)

    @property
    def hard_science_passed(self) -> bool:
        return bool(
            self.completed_budget
            and self.replay_retention_passed
            and self.finite_training
            and self.checkpoint_admissible
            and self.target_head_extraction_passed
            and self.eval2_passed
            and self.physical_verification_state != "fail"
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE1_TRAJECTORY_SCHEMA,
            "role": self.role,
            "training_kernel_mode": self.training_kernel_mode,
            **self.common_protocol_payload,
            "common_protocol_digest": self.common_protocol_digest,
            "completed_epochs": self.completed_epochs,
            "gradient_updates": self.gradient_updates,
            "target_validation_metric_name": self.target_validation_metric_name,
            "target_validation_metric": self.target_validation_metric,
            "replay_validation_metric_name": self.replay_validation_metric_name,
            "replay_validation_metric": self.replay_validation_metric,
            "replay_retention_passed": self.replay_retention_passed,
            "losses_finite": self.losses_finite,
            "gradients_finite": self.gradients_finite,
            "parameters_finite": self.parameters_finite,
            "finite_training": self.finite_training,
            "checkpoint_admissible": self.checkpoint_admissible,
            "checkpoint_ranking_digest": self.checkpoint_ranking_digest,
            "target_head_extraction_passed": self.target_head_extraction_passed,
            "target_head_sha256": self.target_head_sha256,
            "eval2_passed": self.eval2_passed,
            "eval2_decision_digest": self.eval2_decision_digest,
            "physical_verification_state": self.physical_verification_state,
            "physical_verification_digest": self.physical_verification_digest,
            "wall_time_seconds": self.wall_time_seconds,
            "updates_per_second": self.updates_per_second,
            "peak_vram_bytes": self.peak_vram_bytes,
            "reserved_vram_bytes": self.reserved_vram_bytes,
            "representative_full_trajectory": self.representative_full_trajectory,
            "hard_science_passed": self.hard_science_passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase1TrajectoryRecord":
        if payload.get("schema") != CUEQ_PHASE1_TRAJECTORY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE1 trajectory schema.")
        result = cls(
            role=str(payload["role"]),
            training_kernel_mode=str(payload["training_kernel_mode"]),
            runtime_record_digest=str(payload["runtime_record_digest"]),
            source_foundation_digest=str(payload["source_foundation_digest"]),
            starting_checkpoint_sha256=str(payload["starting_checkpoint_sha256"]),
            selected_head_qualification_digest=str(payload["selected_head_qualification_digest"]),
            data8_bundle_digest=str(payload["data8_bundle_digest"]),
            optimizer_semantics_digest=str(payload["optimizer_semantics_digest"]),
            split_identity_digest=str(payload["split_identity_digest"]),
            order_identity_digest=str(payload["order_identity_digest"]),
            objective_policy_digest=str(payload["objective_policy_digest"]),
            lr_schedule_digest=str(payload["lr_schedule_digest"]),
            stopping_policy_digest=str(payload["stopping_policy_digest"]),
            replay_policy_digest=str(payload["replay_policy_digest"]),
            validation_protocol_digest=str(payload["validation_protocol_digest"]),
            evaluation_protocol_digest=str(payload["evaluation_protocol_digest"]),
            seed=int(payload["seed"]), dtype=str(payload["dtype"]),
            epoch_budget=int(payload["epoch_budget"]), update_budget=int(payload["update_budget"]),
            completed_epochs=int(payload["completed_epochs"]), gradient_updates=int(payload["gradient_updates"]),
            target_validation_metric_name=str(payload["target_validation_metric_name"]),
            target_validation_metric=float(payload["target_validation_metric"]),
            replay_validation_metric_name=str(payload["replay_validation_metric_name"]),
            replay_validation_metric=float(payload["replay_validation_metric"]),
            replay_retention_passed=bool(payload["replay_retention_passed"]),
            losses_finite=bool(payload["losses_finite"]), gradients_finite=bool(payload["gradients_finite"]),
            parameters_finite=bool(payload["parameters_finite"]), checkpoint_admissible=bool(payload["checkpoint_admissible"]),
            checkpoint_ranking_digest=str(payload["checkpoint_ranking_digest"]),
            target_head_extraction_passed=bool(payload["target_head_extraction_passed"]),
            target_head_sha256=None if payload.get("target_head_sha256") is None else str(payload["target_head_sha256"]),
            eval2_passed=bool(payload["eval2_passed"]), eval2_decision_digest=str(payload["eval2_decision_digest"]),
            physical_verification_state=str(payload.get("physical_verification_state", "not_available")),
            physical_verification_digest=None if payload.get("physical_verification_digest") is None else str(payload["physical_verification_digest"]),
            wall_time_seconds=float(payload.get("wall_time_seconds", 0.0)),
            updates_per_second=float(payload.get("updates_per_second", 0.0)),
            peak_vram_bytes=int(payload.get("peak_vram_bytes", 0)), reserved_vram_bytes=int(payload.get("reserved_vram_bytes", 0)),
            representative_full_trajectory=bool(payload.get("representative_full_trajectory", False)),
        )
        if payload.get("common_protocol_digest") not in (None, result.common_protocol_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE1 common protocol digest mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE1 trajectory digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqPhase1PairedAssessment:
    """Decision-level comparison of one e3nn reference and one pure-CuEq run."""

    policy: CueqPhase1Policy
    reference: CueqPhase1TrajectoryRecord
    candidate: CueqPhase1TrajectoryRecord
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        reasons: list[str] = []
        if self.reference.training_kernel_mode != self.policy.reference_training_kernel_mode:
            reasons.append("reference_training_kernel_mode")
        if self.candidate.training_kernel_mode != self.policy.candidate_training_kernel_mode:
            reasons.append("candidate_training_kernel_mode")
        if self.reference.role != self.candidate.role:
            reasons.append("trajectory_role")
        if self.policy.require_identical_protocol and self.reference.common_protocol_digest != self.candidate.common_protocol_digest:
            reasons.append("common_protocol_identity")
        if self.reference.target_validation_metric_name != self.candidate.target_validation_metric_name:
            reasons.append("target_validation_metric_name")
        if self.reference.replay_validation_metric_name != self.candidate.replay_validation_metric_name:
            reasons.append("replay_validation_metric_name")
        if self.reference.role == _SHORT_ROLE and self.reference.epoch_budget != self.policy.short_epoch_budget:
            reasons.append("short_epoch_budget")
        if self.reference.role == _FULL_ROLE:
            if not self.reference.representative_full_trajectory or not self.candidate.representative_full_trajectory:
                reasons.append("representative_full_trajectory")
        if self.policy.require_finite_training and not (self.reference.finite_training and self.candidate.finite_training):
            reasons.append("finite_training")
        if self.policy.require_hard_decision_agreement:
            decisions = (
                ("replay_retention", self.reference.replay_retention_passed, self.candidate.replay_retention_passed),
                ("checkpoint_admissibility", self.reference.checkpoint_admissible, self.candidate.checkpoint_admissible),
                ("target_head_extraction", self.reference.target_head_extraction_passed, self.candidate.target_head_extraction_passed),
                ("eval2", self.reference.eval2_passed, self.candidate.eval2_passed),
            )
            for name, left, right in decisions:
                if left != right:
                    reasons.append(f"hard_decision_disagreement:{name}")
        if not self.reference.replay_retention_passed or not self.candidate.replay_retention_passed:
            reasons.append("replay_retention_pass")
        if not self.reference.checkpoint_admissible or not self.candidate.checkpoint_admissible:
            reasons.append("checkpoint_admissibility_pass")
        if self.policy.require_target_head_extraction and not (
            self.reference.target_head_extraction_passed and self.candidate.target_head_extraction_passed
        ):
            reasons.append("target_head_extraction_pass")
        if self.policy.require_eval2_pass and not (self.reference.eval2_passed and self.candidate.eval2_passed):
            reasons.append("eval2_pass")
        if self.policy.require_available_physical_pass:
            for label, run in (("reference", self.reference), ("candidate", self.candidate)):
                if run.physical_verification_state == "fail":
                    reasons.append(f"physical_verification_pass:{label}")
            if (
                self.reference.physical_verification_state != "not_available"
                and self.candidate.physical_verification_state == "not_available"
            ):
                reasons.append("candidate_missing_available_physical_verification")
        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    @property
    def target_metric_delta(self) -> float:
        return float(self.candidate.target_validation_metric - self.reference.target_validation_metric)

    @property
    def replay_metric_delta(self) -> float:
        return float(self.candidate.replay_validation_metric - self.reference.replay_validation_metric)

    @property
    def speedup(self) -> float | None:
        if self.candidate.wall_time_seconds <= 0.0 or self.reference.wall_time_seconds <= 0.0:
            return None
        return float(self.reference.wall_time_seconds / self.candidate.wall_time_seconds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE1_PAIR_SCHEMA,
            "policy": self.policy.to_dict(),
            "reference": self.reference.to_dict(),
            "candidate": self.candidate.to_dict(),
            "target_metric_delta": self.target_metric_delta,
            "replay_metric_delta": self.replay_metric_delta,
            "speedup": self.speedup,
            "blocking_reasons": list(self.blocking_reasons),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase1PairedAssessment":
        if payload.get("schema") != CUEQ_PHASE1_PAIR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE1 paired-assessment schema.")
        result = cls(
            policy=CueqPhase1Policy.from_dict(payload["policy"]),
            reference=CueqPhase1TrajectoryRecord.from_dict(payload["reference"]),
            candidate=CueqPhase1TrajectoryRecord.from_dict(payload["candidate"]),
        )
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("CUEQ-PHASE1 paired-assessment blocking reasons mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE1 paired-assessment digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqPhase1QualificationRecord:
    """Gate-level authorization record for training-only pure-CuEq execution."""

    policy: CueqPhase1Policy
    cueq_dep1_runtime_digest: str
    cueq_dep1_passed: bool
    short_pairs: tuple[CueqPhase1PairedAssessment, ...] = ()
    full_pairs: tuple[CueqPhase1PairedAssessment, ...] = ()
    blocking_reasons: tuple[str, ...] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cueq_dep1_runtime_digest", validate_digest(self.cueq_dep1_runtime_digest, name="cueq_dep1_runtime_digest"))
        short = tuple(self.short_pairs)
        full = tuple(self.full_pairs)
        reasons: list[str] = []
        if not self.cueq_dep1_passed:
            reasons.append("CUEQ_DEP1_RUNTIME_FREEZE")
        if not short:
            reasons.append("short_paired_adaptation_missing")
        if any(item.policy.content_digest != self.policy.content_digest for item in short + full):
            reasons.append("pair_policy_identity")
        if any(item.reference.role != _SHORT_ROLE for item in short):
            reasons.append("short_pair_role")
        if any(item.reference.role != _FULL_ROLE for item in full):
            reasons.append("full_pair_role")
        if any(not item.passed for item in short):
            reasons.append("short_paired_adaptation_failed")
        if len(full) < self.policy.minimum_full_pairs:
            reasons.append("representative_full_pair_missing")
        if any(not item.passed for item in full):
            reasons.append("representative_full_pair_failed")
        # Final release qualification must bind every pair to the same positive
        # CUEQ-DEP1 runtime record; cross-runtime comparisons are not admissible.
        for item in short + full:
            if item.reference.runtime_record_digest != self.cueq_dep1_runtime_digest:
                reasons.append("reference_runtime_identity")
            if item.candidate.runtime_record_digest != self.cueq_dep1_runtime_digest:
                reasons.append("candidate_runtime_identity")
        object.__setattr__(self, "short_pairs", short)
        object.__setattr__(self, "full_pairs", full)
        object.__setattr__(self, "blocking_reasons", tuple(dict.fromkeys(reasons)))

    @property
    def passed(self) -> bool:
        return not self.blocking_reasons

    @property
    def phase_separated_training_authorized(self) -> bool:
        return self.passed

    @property
    def source_cueq_execution_authorized(self) -> bool:
        return False

    @property
    def generated_default_change_authorized(self) -> bool:
        return False

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_PHASE1_QUALIFICATION_SCHEMA,
            "authority_version": CUEQ_PHASE1_VERSION,
            "policy": self.policy.to_dict(),
            "cueq_dep1_runtime_digest": self.cueq_dep1_runtime_digest,
            "cueq_dep1_passed": self.cueq_dep1_passed,
            "short_pairs": [item.to_dict() for item in self.short_pairs],
            "full_pairs": [item.to_dict() for item in self.full_pairs],
            "blocking_reasons": list(self.blocking_reasons),
            "passed": self.passed,
            "phase_separated_execution_policy": {
                "source_inference_kernel_mode": self.policy.source_inference_kernel_mode,
                "training_kernel_mode": self.policy.candidate_training_kernel_mode,
                "training_authorized": self.phase_separated_training_authorized,
                "source_cueq_execution_authorized": self.source_cueq_execution_authorized,
                "generated_default_change_authorized": self.generated_default_change_authorized,
            },
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqPhase1QualificationRecord":
        if payload.get("schema") != CUEQ_PHASE1_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE1 qualification schema.")
        if payload.get("authority_version") != CUEQ_PHASE1_VERSION:
            raise TrainingDataSerializationError("Unsupported CUEQ-PHASE1 qualification authority version.")
        result = cls(
            policy=CueqPhase1Policy.from_dict(payload["policy"]),
            cueq_dep1_runtime_digest=str(payload["cueq_dep1_runtime_digest"]),
            cueq_dep1_passed=bool(payload["cueq_dep1_passed"]),
            short_pairs=tuple(CueqPhase1PairedAssessment.from_dict(v) for v in payload.get("short_pairs", ())),
            full_pairs=tuple(CueqPhase1PairedAssessment.from_dict(v) for v in payload.get("full_pairs", ())),
        )
        if tuple(payload.get("blocking_reasons", ())) not in ((), result.blocking_reasons):
            raise TrainingDataSerializationError("CUEQ-PHASE1 qualification blocking reasons mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-PHASE1 qualification digest mismatch.")
        return result


def build_cueq_phase1_qualification(
    *,
    runtime: CueqDep1RuntimeRecord,
    short_pairs: Sequence[CueqPhase1PairedAssessment] = (),
    full_pairs: Sequence[CueqPhase1PairedAssessment] = (),
    policy: CueqPhase1Policy | None = None,
) -> CueqPhase1QualificationRecord:
    """Build the final gate record without weakening a negative runtime state."""

    active = policy or CueqPhase1Policy()
    if runtime.policy.source_inference_kernel_mode != active.source_inference_kernel_mode:
        raise TrainingDataInputError("CUEQ-PHASE1 policy disagrees with the CUEQ-DEP1 source-inference mode.")
    if runtime.policy.training_kernel_mode != active.candidate_training_kernel_mode:
        raise TrainingDataInputError("CUEQ-PHASE1 policy disagrees with the CUEQ-DEP1 training mode.")
    return CueqPhase1QualificationRecord(
        policy=active,
        cueq_dep1_runtime_digest=runtime.content_digest,
        cueq_dep1_passed=runtime.passed,
        short_pairs=tuple(short_pairs),
        full_pairs=tuple(full_pairs),
    )
