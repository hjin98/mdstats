"""Flexible-fidelity target-size study authority.

The study consumes only REPAIR2 prefix order and MVQUAL hard eligibility. It
owns a configurable three-boundary TRAIN2 successive-fidelity funnel and freezes the
selected target size before any held-out validation. Ladder, migration,
rescue, and downstream validation state are intentionally absent.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
import math
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

TARGET_SIZE_STUDY_VERSION = "mdstats.target-size-study.exact-boundary-screen.2026-08.v1"
TARGET_SIZE_STUDY_POLICY_SCHEMA = "mdstats.target-size-study-policy.v9"
_LEGACY_TARGET_SIZE_STUDY_VERSION = "mdstats.target-size-study.fixed-eight.2026-08.v5.3"
_LEGACY_TARGET_SIZE_STUDY_POLICY_SCHEMA = "mdstats.target-size-study-policy.v6"
TARGET_SIZE_STUDY_CANDIDATE_SCHEMA = "mdstats.target-size-study-candidate.v5"
TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA = "mdstats.target-size-training-evidence.v10"
TARGET_SIZE_TRAJECTORY_FAILURE_EVIDENCE_SCHEMA = (
    "mdstats.target-size-trajectory-failure-evidence.v2"
)
TARGET_SIZE_STAGE_OUTCOME_SCHEMA = "mdstats.target-size-stage-outcome.v3"
TARGET_SIZE_STUDY_PLAN_SCHEMA = "mdstats.target-size-study-plan.v11"
TARGET_SIZE_PREFIX_SCHEMA = "mdstats.target-size-study-repair2-prefix.v1"
TARGET_SIZE_CANDIDATE_DATA_SCHEMA = "mdstats.target-size-study-candidate-data.v1"
# Candidate authority is persisted in DATA7/DATA8 materialization plans.  The
# fixed-fidelity generation used the same unversioned schema label for a
# policy-bound formula; flexible fidelity deliberately does not.  Keep those
# derivations explicitly distinct so restart compatibility never has to infer
# meaning from a bare digest.
TARGET_SIZE_CANDIDATE_AUTHORITY_SCHEMA = "mdstats.target-size-study-candidate-authority.v2"
TARGET_SIZE_CANDIDATE_AUTHORITY_GENERATION = "flexible-fidelity-candidate-prefix.v1"
LEGACY_FIXED_CANDIDATE_AUTHORITY_SCHEMA = "mdstats.target-size-study-candidate-authority.v1"
LEGACY_FIXED_CANDIDATE_AUTHORITY_GENERATION = "fixed-fidelity-policy-bound.v1"
HISTORICAL_FIXED_CANDIDATE_AUTHORITY_RECEIPT_SCHEMA = (
    "mdstats.target-size-study-historical-candidate-authority.v1"
)

FIXED_TARGET_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
FIXED_TARGET_SIZE_CEILING = FIXED_TARGET_SIZES[-1]

OUTCOME_INSUFFICIENT_QUALIFIED_SIZES = "insufficient_qualified_sizes"
OUTCOME_AWAITING_COARSE_SCREEN = "awaiting_coarse_screen"
OUTCOME_AWAITING_SHORT_SCREEN = "awaiting_short_screen"
OUTCOME_AWAITING_FINAL_SCREEN = "awaiting_final_screen"
OUTCOME_SELECTED = "selected"
OUTCOME_NONCONVERGED_AT_FIXED_CEILING = "nonconverged_at_fixed_ceiling"
OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES = "insufficient_comparable_candidates"

_TERMINAL_OUTCOMES = {
    OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
    OUTCOME_SELECTED,
    OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
}
STAGE_COARSE = "coarse"
STAGE_SHORT = "short"
STAGE_FINAL_SCREEN = "final_screen"
_SCREEN_STAGES = (STAGE_COARSE, STAGE_SHORT, STAGE_FINAL_SCREEN)
_OUTCOME_FOR_STAGE = {
    STAGE_COARSE: OUTCOME_AWAITING_COARSE_SCREEN,
    STAGE_SHORT: OUTCOME_AWAITING_SHORT_SCREEN,
    STAGE_FINAL_SCREEN: OUTCOME_AWAITING_FINAL_SCREEN,
}

FAILURE_PHASE_TRAIN = "train"
FAILURE_PHASE_TARGET_EVALUATION = "target_evaluation"
TRAIN2_NUMERICAL_FAILURE_CODES = frozenset({
    "train_nonfinite_model_state",
    "train_nonfinite_ema_state",
})
EVAL2_NUMERICAL_FAILURE_CODES = frozenset({
    "eval_nonfinite_energy_prediction",
    "eval_nonfinite_force_prediction",
    "eval_nonfinite_stress_prediction",
    "eval_nonfinite_target_metric",
})
TARGET_SIZE_SCIENTIFIC_FAILURE_CODES = TRAIN2_NUMERICAL_FAILURE_CODES | EVAL2_NUMERICAL_FAILURE_CODES


@dataclass(frozen=True, slots=True)
class TargetSizeStudyPolicy:
    """Fixed-universe policy with configurable screening boundaries.

    ``fidelity_epochs`` owns only the three screening boundaries.  The
    separately configured production horizon is deliberately supplied by
    ``TrainingBudgetPolicy`` at production assembly/execution time; putting it
    here would create a second target-size authority.
    """

    candidate_sizes: tuple[int, ...] = FIXED_TARGET_SIZES
    minimum_qualified_sizes: int = 3
    coarse_survivor_limit: int = 4
    short_finalist_count: int = 2
    fidelity_epochs: tuple[int, int, int] = (1, 3, 10)
    practical_equivalence_mev_per_a: float = 1.0
    coarse_practical_equivalence_mev_per_a: float = 1.0
    screening_optimizer_seeds: tuple[int, ...] = (1, 2)
    paired_seed_aggregation: str = "arithmetic_mean"
    authority_version: str = TARGET_SIZE_STUDY_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(int(v) for v in self.candidate_sizes)
        raw_epochs = tuple(self.fidelity_epochs)
        if len(raw_epochs) != 3 or any(isinstance(v, bool) or not isinstance(v, int) for v in raw_epochs):
            raise TrainingDataInputError("fidelity_epochs must contain exactly three integer boundaries.")
        epochs = tuple(int(v) for v in raw_epochs)
        if sizes != FIXED_TARGET_SIZES:
            raise TrainingDataInputError(
                "Target-size v5 freezes the candidate universe at 128..16384 powers of two."
            )
        if int(self.minimum_qualified_sizes) != 3:
            raise TrainingDataInputError(
                "Target-size v5 freezes the qualification threshold at three."
            )
        if int(self.coarse_survivor_limit) != 4 or int(self.short_finalist_count) != 2:
            raise TrainingDataInputError(
                "Target-size screening freezes the funnel at q->min(q,4)->2->1."
            )
        if any(value <= 0 for value in epochs) or not (epochs[0] < epochs[1] < epochs[2]):
            raise TrainingDataInputError(
                "fidelity_epochs must be three strictly increasing positive boundaries."
            )
        for name in (
            "practical_equivalence_mev_per_a",
            "coarse_practical_equivalence_mev_per_a",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"{name} must be positive and finite.")
            object.__setattr__(self, name, value)
        seeds = tuple(int(v) for v in self.screening_optimizer_seeds)
        if not seeds or any(v < 0 for v in seeds) or len(set(seeds)) != len(seeds):
            raise TrainingDataInputError(
                "screening_optimizer_seeds must be a non-empty ordered set of unique nonnegative seeds."
            )
        if str(self.paired_seed_aggregation) != "arithmetic_mean":
            raise TrainingDataInputError(
                "Target-size v5 currently supports paired_seed_aggregation='arithmetic_mean' only."
            )
        if self.authority_version != TARGET_SIZE_STUDY_VERSION:
            raise TrainingDataInputError("Unsupported target-size study policy version.")
        object.__setattr__(self, "candidate_sizes", sizes)
        object.__setattr__(self, "minimum_qualified_sizes", 3)
        object.__setattr__(self, "coarse_survivor_limit", 4)
        object.__setattr__(self, "short_finalist_count", 2)
        object.__setattr__(self, "fidelity_epochs", epochs)
        object.__setattr__(self, "screening_optimizer_seeds", seeds)
        object.__setattr__(self, "paired_seed_aggregation", "arithmetic_mean")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_STUDY_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "candidate_sizes": list(self.candidate_sizes),
            "minimum_qualified_sizes": self.minimum_qualified_sizes,
            "coarse_survivor_limit": self.coarse_survivor_limit,
            "short_finalist_count": self.short_finalist_count,
            "fidelity_epochs": list(self.fidelity_epochs),
            "practical_equivalence_mev_per_a": self.practical_equivalence_mev_per_a,
            "coarse_practical_equivalence_mev_per_a": self.coarse_practical_equivalence_mev_per_a,
            "screening_optimizer_seeds": list(self.screening_optimizer_seeds),
            "paired_seed_aggregation": self.paired_seed_aggregation,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeStudyPolicy":
        if payload.get("schema") != TARGET_SIZE_STUDY_POLICY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size policy schema; validate and migrate the fixed-generation record first."
            )
        if "screening_optimizer_seeds" not in payload:
            raise TrainingDataSerializationError(
                "Target-size policy is missing the authenticated ordered screening seed set."
            )
        result = cls(
            candidate_sizes=tuple(int(v) for v in payload["candidate_sizes"]),
            minimum_qualified_sizes=int(payload["minimum_qualified_sizes"]),
            coarse_survivor_limit=int(payload["coarse_survivor_limit"]),
            short_finalist_count=int(payload["short_finalist_count"]),
            fidelity_epochs=tuple(int(v) for v in payload["fidelity_epochs"]),
            practical_equivalence_mev_per_a=float(
                payload["practical_equivalence_mev_per_a"]
            ),
            coarse_practical_equivalence_mev_per_a=float(
                payload["coarse_practical_equivalence_mev_per_a"]
            ),
            screening_optimizer_seeds=tuple(
                int(v) for v in payload["screening_optimizer_seeds"]
            ),
            paired_seed_aggregation=str(payload.get("paired_seed_aggregation", "")),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError(
                "Target-size study policy digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeStudyCandidate:
    """One fixed target size authenticated against REPAIR2 prefixes and MVQUAL."""

    target_size: int
    materializable: bool
    mvqual_hard_pass: bool
    domain_prefix_digests: tuple[tuple[str, str], ...]
    candidate_data_digest: str

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size not in FIXED_TARGET_SIZES:
            raise TrainingDataInputError(
                "Target-size study candidate lies outside the fixed universe."
            )
        prefixes = tuple(
            sorted(
                (
                    str(k),
                    validate_digest(v, name="domain_prefix_digest"),
                )
                for k, v in self.domain_prefix_digests
            )
        )
        if not prefixes or len({k for k, _ in prefixes}) != len(prefixes):
            raise TrainingDataInputError(
                "Target-size study candidate requires one prefix digest per domain."
            )
        if self.mvqual_hard_pass and not self.materializable:
            raise TrainingDataInputError(
                "MVQUAL cannot qualify a target size that REPAIR2 cannot materialize."
            )
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "domain_prefix_digests", prefixes)
        object.__setattr__(
            self,
            "candidate_data_digest",
            validate_digest(self.candidate_data_digest, name="candidate_data_digest"),
        )

    @property
    def qualified(self) -> bool:
        return bool(self.materializable and self.mvqual_hard_pass)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_STUDY_CANDIDATE_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "mvqual_hard_pass": self.mvqual_hard_pass,
            "domain_prefix_digests": [list(v) for v in self.domain_prefix_digests],
            "candidate_data_digest": self.candidate_data_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeStudyCandidate":
        if payload.get("schema") != TARGET_SIZE_STUDY_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size study candidate schema."
            )
        result = cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            mvqual_hard_pass=bool(payload["mvqual_hard_pass"]),
            domain_prefix_digests=tuple(
                (str(v[0]), str(v[1])) for v in payload["domain_prefix_digests"]
            ),
            candidate_data_digest=str(payload["candidate_data_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size study candidate digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeTrainingEvidence:
    """Authenticated successful TRAIN2/EVAL2 endpoint evidence.

    Failed trajectories are represented only by
    :class:`TargetSizeTrajectoryFailureEvidence`; this record always denotes a
    real, complete, finite configured screen endpoint.
    """

    stage: str
    target_size: int
    optimizer_seed: int
    completed_epochs: int
    optimizer_update_count: int
    structures_presented: int
    instantaneous_learning_rate: float
    wall_time_seconds: float
    target_force_score_mev_per_a: float
    foundation_identity_digest: str
    evaluation_role_digest: str
    training_policy_digest: str
    target_size_study_policy_digest: str
    training_run_digest: str
    candidate_data_digest: str
    checkpoint_digest: str
    schedule_digest: str
    optimizer_state_digest: str
    rng_state_digest: str
    target_evaluation_digest: str
    replay_diagnostic_force_rmse_mev_per_a: float | None = None
    replay_evaluation_digest: str | None = None
    replay_admissible: bool | None = None
    physical_qualification_passed: bool | None = None
    physical_qualification_digest: str | None = None
    parent_checkpoint_digest: str | None = None
    parent_optimizer_state_digest: str | None = None
    parent_rng_state_digest: str | None = None

    def __post_init__(self) -> None:
        stage = str(self.stage).strip().lower()
        if stage not in _SCREEN_STAGES:
            raise TrainingDataInputError(
                "Target-size training stage must be coarse, short, or final_screen."
            )
        size = int(self.target_size)
        seed = int(self.optimizer_seed)
        completed = int(self.completed_epochs)
        updates = int(self.optimizer_update_count)
        structures = int(self.structures_presented)
        lr = float(self.instantaneous_learning_rate)
        wall = float(self.wall_time_seconds)
        score = float(self.target_force_score_mev_per_a)
        if size not in FIXED_TARGET_SIZES or seed < 0 or updates <= 0 or structures <= 0:
            raise TrainingDataInputError("Target-size successful endpoint counts are invalid.")
        if completed <= 0:
            raise TrainingDataInputError(
                "Target-size successful evidence must be a positive exact-boundary endpoint."
            )
        if not math.isfinite(lr) or lr <= 0.0 or not math.isfinite(wall) or wall < 0.0:
            raise TrainingDataInputError("Target-size learning-rate/wall evidence is invalid.")
        if not math.isfinite(score) or score < 0.0:
            raise TrainingDataInputError("Target-size force score must be finite and nonnegative.")
        for name in (
            "foundation_identity_digest", "evaluation_role_digest", "training_policy_digest",
            "target_size_study_policy_digest", "training_run_digest", "candidate_data_digest",
            "checkpoint_digest", "schedule_digest", "optimizer_state_digest", "rng_state_digest",
            "target_evaluation_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "replay_evaluation_digest", "physical_qualification_digest",
            "parent_checkpoint_digest", "parent_optimizer_state_digest", "parent_rng_state_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.replay_diagnostic_force_rmse_mev_per_a is not None:
            replay = float(self.replay_diagnostic_force_rmse_mev_per_a)
            if not math.isfinite(replay) or replay < 0.0:
                raise TrainingDataInputError("Replay diagnostic must be finite and nonnegative.")
            object.__setattr__(self, "replay_diagnostic_force_rmse_mev_per_a", replay)
        parents = (
            self.parent_checkpoint_digest,
            self.parent_optimizer_state_digest,
            self.parent_rng_state_digest,
        )
        if stage == STAGE_COARSE:
            if any(v is not None for v in parents):
                raise TrainingDataInputError("Coarse-screen evidence cannot claim a continuation parent.")
            if any(v is not None for v in (
                self.replay_diagnostic_force_rmse_mev_per_a, self.replay_evaluation_digest,
                self.replay_admissible, self.physical_qualification_passed, self.physical_qualification_digest,
            )):
                raise TrainingDataInputError("Coarse-screen evidence is target-only.")
        elif stage == STAGE_SHORT:
            if any(v is None for v in parents):
                raise TrainingDataInputError(
                    "Short-screen evidence requires exact coarse-screen checkpoint/optimizer/RNG ancestry."
                )
            if self.replay_admissible is not None or self.physical_qualification_passed is not None or self.physical_qualification_digest is not None:
                raise TrainingDataInputError("Short-screen evidence cannot carry final replay/physical pass authority.")
            if (self.replay_diagnostic_force_rmse_mev_per_a is None) != (self.replay_evaluation_digest is None):
                raise TrainingDataInputError("Short-screen replay diagnostics require both value and digest.")
        else:
            if any(v is None for v in parents):
                raise TrainingDataInputError(
                    "Final-screen evidence requires exact short-screen checkpoint/optimizer/RNG ancestry."
                )
            if (self.replay_diagnostic_force_rmse_mev_per_a is None) != (self.replay_evaluation_digest is None):
                raise TrainingDataInputError("Final-screen replay diagnostics require both value and digest when present.")
            if self.replay_admissible is not None or self.physical_qualification_passed is not None or self.physical_qualification_digest is not None:
                raise TrainingDataInputError(
                    "Target-size selection forbids replay/physical hard-pass authority in final-screen evidence; downstream gates run after size freeze."
                )
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "optimizer_seed", seed)
        object.__setattr__(self, "completed_epochs", completed)
        object.__setattr__(self, "optimizer_update_count", updates)
        object.__setattr__(self, "structures_presented", structures)
        object.__setattr__(self, "instantaneous_learning_rate", lr)
        object.__setattr__(self, "wall_time_seconds", wall)
        object.__setattr__(self, "target_force_score_mev_per_a", score)

    @property
    def key(self) -> tuple[int, int]:
        return (self.target_size, self.optimizer_seed)

    @property
    def admissible_for_screening(self) -> bool:
        return True

    @property
    def admissible_for_final_selection(self) -> bool:
        return True

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA,
            "stage": self.stage, "target_size": self.target_size, "optimizer_seed": self.optimizer_seed,
            "completed_epochs": self.completed_epochs,
            "optimizer_update_count": self.optimizer_update_count, "structures_presented": self.structures_presented,
            "instantaneous_learning_rate": self.instantaneous_learning_rate,
            "wall_time_seconds": self.wall_time_seconds,
            "target_force_score_mev_per_a": self.target_force_score_mev_per_a,
            "foundation_identity_digest": self.foundation_identity_digest,
            "evaluation_role_digest": self.evaluation_role_digest,
            "training_policy_digest": self.training_policy_digest,
            "target_size_study_policy_digest": self.target_size_study_policy_digest,
            "training_run_digest": self.training_run_digest,
            "candidate_data_digest": self.candidate_data_digest,
            "checkpoint_digest": self.checkpoint_digest,
            "schedule_digest": self.schedule_digest,
            "optimizer_state_digest": self.optimizer_state_digest,
            "rng_state_digest": self.rng_state_digest,
            "target_evaluation_digest": self.target_evaluation_digest,
            "replay_diagnostic_force_rmse_mev_per_a": self.replay_diagnostic_force_rmse_mev_per_a,
            "replay_evaluation_digest": self.replay_evaluation_digest,
            "replay_admissible": self.replay_admissible,
            "physical_qualification_passed": self.physical_qualification_passed,
            "physical_qualification_digest": self.physical_qualification_digest,
            "parent_checkpoint_digest": self.parent_checkpoint_digest,
            "parent_optimizer_state_digest": self.parent_optimizer_state_digest,
            "parent_rng_state_digest": self.parent_rng_state_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeTrainingEvidence":
        if payload.get("schema") != TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Historical invalid-capable target-size endpoint evidence is not restart-compatible with v5 closeout."
            )
        kwargs = dict(payload)
        kwargs.pop("schema", None)
        kwargs.pop("content_digest", None)
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-size training evidence digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeTrajectoryFailureEvidence:
    """Authenticated candidate-specific numerical/scientific trajectory failure."""

    stage: str
    target_size: int
    optimizer_seed: int
    failure_phase: str
    failure_code: str
    failure_reasons: tuple[str, ...]
    target_size_study_policy_digest: str
    training_run_digest: str
    candidate_data_digest: str
    training_policy_digest: str
    schedule_digest: str
    execution_record_digest: str | None = None
    execution_attempt_digest: str | None = None
    checkpoint_digest: str | None = None
    evaluation_role_digest: str | None = None
    target_evaluation_digest: str | None = None
    completed_epochs: int | None = None
    optimizer_update_count: int | None = None

    def __post_init__(self) -> None:
        stage = str(self.stage).strip().lower()
        if stage not in _SCREEN_STAGES:
            raise TrainingDataInputError("Target-size failure evidence has an invalid fidelity stage.")
        size = int(self.target_size)
        seed = int(self.optimizer_seed)
        if size not in FIXED_TARGET_SIZES or seed < 0:
            raise TrainingDataInputError("Target-size failure evidence candidate identity is invalid.")
        phase = str(self.failure_phase).strip()
        code = str(self.failure_code).strip()
        if phase == FAILURE_PHASE_TRAIN:
            if code not in TRAIN2_NUMERICAL_FAILURE_CODES:
                raise TrainingDataInputError("Only explicit TRAIN2 numerical codes may become train-phase target-size failure evidence.")
            if self.execution_record_digest is None or self.execution_attempt_digest is None:
                raise TrainingDataInputError("TRAIN2 failure evidence requires execution-record and attempt provenance.")
            if self.checkpoint_digest is not None or self.evaluation_role_digest is not None or self.target_evaluation_digest is not None:
                raise TrainingDataInputError("Train-phase target-size failure cannot fabricate endpoint/evaluation provenance.")
        elif phase == FAILURE_PHASE_TARGET_EVALUATION:
            if code not in EVAL2_NUMERICAL_FAILURE_CODES:
                raise TrainingDataInputError("Only explicit EVAL2 numerical codes may become evaluation-phase target-size failure evidence.")
            if any(v is None for v in (
                self.execution_record_digest, self.execution_attempt_digest, self.checkpoint_digest,
                self.evaluation_role_digest, self.target_evaluation_digest,
            )):
                raise TrainingDataInputError(
                    "EVAL2 numerical failure requires successful execution, attempt, checkpoint, role, and failed-evaluation provenance."
                )
        else:
            raise TrainingDataInputError("Unsupported target-size failure phase.")
        reasons = tuple(str(v).strip() for v in self.failure_reasons if str(v).strip())
        if not reasons or len(set(reasons)) != len(reasons):
            raise TrainingDataInputError("Target-size failure reasons must be non-empty, unique, and deterministic.")
        for name in (
            "target_size_study_policy_digest", "training_run_digest", "candidate_data_digest",
            "training_policy_digest", "schedule_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "execution_record_digest", "execution_attempt_digest", "checkpoint_digest",
            "evaluation_role_digest", "target_evaluation_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.completed_epochs is not None:
            completed = int(self.completed_epochs)
            if completed < 0:
                raise TrainingDataInputError("Target-size failure completed_epochs cannot be negative.")
            object.__setattr__(self, "completed_epochs", completed)
        if self.optimizer_update_count is not None:
            updates = int(self.optimizer_update_count)
            if updates < 0:
                raise TrainingDataInputError("Target-size failure optimizer_update_count cannot be negative.")
            object.__setattr__(self, "optimizer_update_count", updates)
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "optimizer_seed", seed)
        object.__setattr__(self, "failure_phase", phase)
        object.__setattr__(self, "failure_code", code)
        object.__setattr__(self, "failure_reasons", reasons)

    @property
    def key(self) -> tuple[int, int]:
        return (self.target_size, self.optimizer_seed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_TRAJECTORY_FAILURE_EVIDENCE_SCHEMA,
            "stage": self.stage, "target_size": self.target_size, "optimizer_seed": self.optimizer_seed,
            "failure_phase": self.failure_phase, "failure_code": self.failure_code,
            "failure_reasons": list(self.failure_reasons),
            "target_size_study_policy_digest": self.target_size_study_policy_digest,
            "training_run_digest": self.training_run_digest,
            "candidate_data_digest": self.candidate_data_digest,
            "training_policy_digest": self.training_policy_digest,
            "schedule_digest": self.schedule_digest,
            "execution_record_digest": self.execution_record_digest,
            "execution_attempt_digest": self.execution_attempt_digest,
            "checkpoint_digest": self.checkpoint_digest,
            "evaluation_role_digest": self.evaluation_role_digest,
            "target_evaluation_digest": self.target_evaluation_digest,
            "completed_epochs": self.completed_epochs,
            "optimizer_update_count": self.optimizer_update_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeTrajectoryFailureEvidence":
        if payload.get("schema") != TARGET_SIZE_TRAJECTORY_FAILURE_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-size trajectory-failure schema.")
        kwargs = dict(payload)
        kwargs.pop("schema", None)
        kwargs.pop("content_digest", None)
        kwargs["failure_reasons"] = tuple(str(v) for v in kwargs.get("failure_reasons", ()))
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-size trajectory-failure digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeStageOutcome:
    """Exactly one success or failure for an expected ``(size, seed)`` key."""

    success: TargetSizeTrainingEvidence | None = None
    failure: TargetSizeTrajectoryFailureEvidence | None = None

    def __post_init__(self) -> None:
        if (self.success is None) == (self.failure is None):
            raise TrainingDataInputError("Target-size stage outcome must contain exactly one success or failure.")

    @property
    def key(self) -> tuple[int, int]:
        item = self.success if self.success is not None else self.failure
        assert item is not None
        return item.key

    @property
    def stage(self) -> str:
        item = self.success if self.success is not None else self.failure
        assert item is not None
        return item.stage

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_STAGE_OUTCOME_SCHEMA,
            "success": None if self.success is None else self.success.to_dict(),
            "failure": None if self.failure is None else self.failure.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeStageOutcome":
        if payload.get("schema") != TARGET_SIZE_STAGE_OUTCOME_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-size stage-outcome schema.")
        result = cls(
            success=None if payload.get("success") is None else TargetSizeTrainingEvidence.from_dict(payload["success"]),
            failure=None if payload.get("failure") is None else TargetSizeTrajectoryFailureEvidence.from_dict(payload["failure"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-size stage-outcome digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeStudyPlan:
    dataset_id: str
    repair2_authority_digest: str
    mvqual_authority_digest: str
    policy: TargetSizeStudyPolicy
    candidates: tuple[TargetSizeStudyCandidate, ...]
    qualified_sizes: tuple[int, ...]
    coarse_outcomes: tuple[TargetSizeStageOutcome, ...] = ()
    coarse_survivor_sizes: tuple[int, ...] = ()
    short_outcomes: tuple[TargetSizeStageOutcome, ...] = ()
    short_finalist_sizes: tuple[int, ...] = ()
    final_screen_outcomes: tuple[TargetSizeStageOutcome, ...] = ()
    selected_target_size: int | None = None
    outcome: str = OUTCOME_AWAITING_COARSE_SCREEN
    decision_reason: str = "qualified fixed target-size set frozen; awaiting coarse-screen TRAIN2 outcomes"
    comparison_failure_stage: str | None = None
    comparison_failures: tuple[tuple[int, int, tuple[str, ...]], ...] = ()
    authority_version: str = TARGET_SIZE_STUDY_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)
    _candidate_authority_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("Target-size study dataset_id cannot be empty.")
        object.__setattr__(self, "repair2_authority_digest", validate_digest(self.repair2_authority_digest, name="repair2_authority_digest"))
        object.__setattr__(self, "mvqual_authority_digest", validate_digest(self.mvqual_authority_digest, name="mvqual_authority_digest"))
        if self.authority_version != TARGET_SIZE_STUDY_VERSION:
            raise TrainingDataInputError("Unsupported target-size study authority version.")
        candidates = tuple(sorted(self.candidates, key=lambda v: v.target_size))
        if tuple(v.target_size for v in candidates) != FIXED_TARGET_SIZES:
            raise TrainingDataInputError("Target-size study must record exactly the fixed eight candidates.")
        qualified = tuple(v.target_size for v in candidates if v.qualified)
        if tuple(int(v) for v in self.qualified_sizes) != qualified:
            raise TrainingDataInputError("Target-size study qualified set must equal MVQUAL-qualified materializable candidates.")
        # Derived candidate identity is recomputed here so a forged in-memory
        # candidate cannot survive semantic validation merely because its digest
        # has valid syntax.
        for candidate in candidates:
            expected = _candidate_data_digest(
                self.dataset_id,
                self.repair2_authority_digest,
                candidate.target_size,
                candidate.domain_prefix_digests,
            )
            if candidate.candidate_data_digest != expected:
                raise TrainingDataInputError("Target-size candidate_data_digest failed semantic recomputation.")
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "qualified_sizes", qualified)
        object.__setattr__(self, "coarse_outcomes", tuple(self.coarse_outcomes))
        object.__setattr__(self, "coarse_survivor_sizes", tuple(int(v) for v in self.coarse_survivor_sizes))
        object.__setattr__(self, "short_outcomes", tuple(self.short_outcomes))
        object.__setattr__(self, "short_finalist_sizes", tuple(int(v) for v in self.short_finalist_sizes))
        object.__setattr__(self, "final_screen_outcomes", tuple(self.final_screen_outcomes))
        object.__setattr__(self, "selected_target_size", None if self.selected_target_size is None else int(self.selected_target_size))
        object.__setattr__(self, "comparison_failure_stage", None if self.comparison_failure_stage is None else str(self.comparison_failure_stage))
        object.__setattr__(self, "comparison_failures", tuple(
            (int(size), int(seed), tuple(str(v) for v in reasons))
            for size, seed, reasons in self.comparison_failures
        ))
        _validate_target_size_study_semantics(self)

    @property
    def coarse_evidence(self) -> tuple[TargetSizeTrainingEvidence, ...]:
        return tuple(v.success for v in self.coarse_outcomes if v.success is not None)

    @property
    def coarse_failures(self) -> tuple[TargetSizeTrajectoryFailureEvidence, ...]:
        return tuple(v.failure for v in self.coarse_outcomes if v.failure is not None)

    @property
    def short_evidence(self) -> tuple[TargetSizeTrainingEvidence, ...]:
        return tuple(v.success for v in self.short_outcomes if v.success is not None)

    @property
    def short_failures(self) -> tuple[TargetSizeTrajectoryFailureEvidence, ...]:
        return tuple(v.failure for v in self.short_outcomes if v.failure is not None)

    @property
    def final_screen_evidence(self) -> tuple[TargetSizeTrainingEvidence, ...]:
        return tuple(v.success for v in self.final_screen_outcomes if v.success is not None)

    @property
    def final_screen_failures(self) -> tuple[TargetSizeTrajectoryFailureEvidence, ...]:
        return tuple(v.failure for v in self.final_screen_outcomes if v.failure is not None)

    @property
    def candidate_authority_digest(self) -> str:
        cached = self._candidate_authority_digest_cache
        if not cached:
            cached = digest({
                "schema": TARGET_SIZE_CANDIDATE_AUTHORITY_SCHEMA,
                "generation": TARGET_SIZE_CANDIDATE_AUTHORITY_GENERATION,
                "dataset_id": self.dataset_id,
                "repair2_authority_digest": self.repair2_authority_digest,
                "mvqual_authority_digest": self.mvqual_authority_digest,
                # DATA7/DATA8 candidate-prefix materialization depends on the
                # admitted fixed prefixes, not on later screen geometry.  Keep
                # fidelity policy identity on screening evidence/plans, while
                # allowing an in-place fidelity upgrade to reuse byte-identical
                # candidate materializations after REPAIR2/MVQUAL validation.
                "candidate_digests": [item.content_digest for item in self.candidates],
                "qualified_sizes": list(self.qualified_sizes),
            })
            object.__setattr__(self, "_candidate_authority_digest_cache", cached)
        return cached

    @property
    def candidate_authority_inputs(self) -> dict[str, Any]:
        """Return the complete policy-independent DATA7/DATA8 authority.

        This deliberately exposes the authenticated inputs used by the
        immediate-predecessor bridge.  It is not a second authority: callers
        use it only to prove that a legacy policy-bound digest represents the
        exact same candidate-prefix materialization.
        """

        return {
            "dataset_id": self.dataset_id,
            "repair2_authority_digest": self.repair2_authority_digest,
            "mvqual_authority_digest": self.mvqual_authority_digest,
            "candidate_digests": tuple(item.content_digest for item in self.candidates),
            "qualified_sizes": self.qualified_sizes,
        }

    @property
    def complete(self) -> bool:
        return self.outcome in _TERMINAL_OUTCOMES

    @property
    def next_training_sizes(self) -> tuple[int, ...]:
        if self.outcome == OUTCOME_AWAITING_COARSE_SCREEN:
            return self.qualified_sizes
        if self.outcome == OUTCOME_AWAITING_SHORT_SCREEN:
            return self.coarse_survivor_sizes
        if self.outcome == OUTCOME_AWAITING_FINAL_SCREEN:
            return self.short_finalist_sizes
        return ()

    @property
    def next_training_epoch(self) -> int | None:
        return {
            OUTCOME_AWAITING_COARSE_SCREEN: self.policy.fidelity_epochs[0],
            OUTCOME_AWAITING_SHORT_SCREEN: self.policy.fidelity_epochs[1],
            OUTCOME_AWAITING_FINAL_SCREEN: self.policy.fidelity_epochs[2],
        }.get(self.outcome)

    @property
    def next_training_stage(self) -> str | None:
        return {
            OUTCOME_AWAITING_COARSE_SCREEN: STAGE_COARSE,
            OUTCOME_AWAITING_SHORT_SCREEN: STAGE_SHORT,
            OUTCOME_AWAITING_FINAL_SCREEN: STAGE_FINAL_SCREEN,
        }.get(self.outcome)

    def candidate(self, target_size: int) -> TargetSizeStudyCandidate:
        size = int(target_size)
        for item in self.candidates:
            if item.target_size == size:
                return item
        raise TrainingDataInputError(f"Target size n{size} is outside the fixed universe.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_STUDY_PLAN_SCHEMA,
            "authority_version": self.authority_version,
            "dataset_id": self.dataset_id,
            "repair2_authority_digest": self.repair2_authority_digest,
            "mvqual_authority_digest": self.mvqual_authority_digest,
            "policy": self.policy.to_dict(),
            "candidates": [v.to_dict() for v in self.candidates],
            "qualified_sizes": list(self.qualified_sizes),
            "coarse_outcomes": [v.to_dict() for v in self.coarse_outcomes],
            "coarse_survivor_sizes": list(self.coarse_survivor_sizes),
            "short_outcomes": [v.to_dict() for v in self.short_outcomes],
            "short_finalist_sizes": list(self.short_finalist_sizes),
            "final_screen_outcomes": [v.to_dict() for v in self.final_screen_outcomes],
            "selected_target_size": self.selected_target_size,
            "outcome": self.outcome,
            "decision_reason": self.decision_reason,
            "comparison_failure_stage": self.comparison_failure_stage,
            "comparison_failures": [[size, seed, list(reasons)] for size, seed, reasons in self.comparison_failures],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeStudyPlan":
        if payload.get("schema") != TARGET_SIZE_STUDY_PLAN_SCHEMA or payload.get("authority_version") != TARGET_SIZE_STUDY_VERSION:
            raise TrainingDataSerializationError(
                "Historical target-size screen state is not restart-compatible with the decoupled-screen generation; preserve authenticated candidate materialization and rebuild screening from REPAIR2 + MVQUAL2."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            repair2_authority_digest=str(payload["repair2_authority_digest"]),
            mvqual_authority_digest=str(payload["mvqual_authority_digest"]),
            policy=TargetSizeStudyPolicy.from_dict(payload["policy"]),
            candidates=tuple(TargetSizeStudyCandidate.from_dict(v) for v in payload["candidates"]),
            qualified_sizes=tuple(int(v) for v in payload["qualified_sizes"]),
            coarse_outcomes=tuple(TargetSizeStageOutcome.from_dict(v) for v in payload.get("coarse_outcomes", ())),
            coarse_survivor_sizes=tuple(int(v) for v in payload.get("coarse_survivor_sizes", ())),
            short_outcomes=tuple(TargetSizeStageOutcome.from_dict(v) for v in payload.get("short_outcomes", ())),
            short_finalist_sizes=tuple(int(v) for v in payload.get("short_finalist_sizes", ())),
            final_screen_outcomes=tuple(TargetSizeStageOutcome.from_dict(v) for v in payload.get("final_screen_outcomes", ())),
            selected_target_size=None if payload.get("selected_target_size") is None else int(payload["selected_target_size"]),
            outcome=str(payload["outcome"]),
            decision_reason=str(payload.get("decision_reason", "")),
            comparison_failure_stage=None if payload.get("comparison_failure_stage") is None else str(payload["comparison_failure_stage"]),
            comparison_failures=tuple((int(v[0]), int(v[1]), tuple(str(r) for r in v[2])) for v in payload.get("comparison_failures", ())),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-size study plan digest mismatch.")
        return result


def authenticated_fixed_predecessor_candidate_authority(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Extract the authentic fixed-generation candidate binding from raw state.

    This is deliberately a raw-v8/v6 boundary.  Once a legacy study is
    normalized into the flexible plan, the v6 policy serialization (and thus
    the only authentic legacy policy digest) is no longer available.  The
    returned receipt is compatibility evidence, not a second scientific
    target-size authority.
    """

    raw = dict(payload)
    observed_digest = raw.pop("content_digest", None)
    if observed_digest is not None and observed_digest != digest(raw):
        raise TrainingDataSerializationError(
            "Historical fixed target-size study digest mismatch."
        )
    if (
        raw.get("schema") != "mdstats.target-size-study-plan.v8"
        or raw.get("authority_version") != _LEGACY_TARGET_SIZE_STUDY_VERSION
    ):
        raise TrainingDataSerializationError(
            "Historical target-size study is not the supported fixed v8 generation."
        )
    policy = raw.get("policy")
    if not isinstance(policy, Mapping):
        raise TrainingDataSerializationError(
            "Historical fixed target-size study lacks a v6 policy payload."
        )
    policy_raw = dict(policy)
    policy_digest = policy_raw.pop("policy_digest", None)
    if (
        policy_raw.get("schema") != _LEGACY_TARGET_SIZE_STUDY_POLICY_SCHEMA
        or policy_raw.get("authority_version") != _LEGACY_TARGET_SIZE_STUDY_VERSION
    ):
        raise TrainingDataSerializationError(
            "Historical target-size policy is not the supported fixed v6 generation."
        )
    if not isinstance(policy_digest, str) or policy_digest != digest(policy_raw):
        raise TrainingDataSerializationError(
            "Historical fixed target-size policy digest mismatch."
        )
    if tuple(policy_raw.get("fidelity_epochs", ())) != (3, 10, 30):
        raise TrainingDataSerializationError(
            "Historical fixed target-size policy has an ambiguous fidelity tuple."
        )
    candidates_raw = raw.get("candidates")
    if not isinstance(candidates_raw, list) or not candidates_raw:
        raise TrainingDataSerializationError(
            "Historical fixed target-size study has no candidate population."
        )
    candidates = tuple(TargetSizeStudyCandidate.from_dict(item) for item in candidates_raw)
    qualified_sizes = tuple(int(value) for value in raw.get("qualified_sizes", ()))
    if not qualified_sizes or tuple(sorted(set(qualified_sizes))) != qualified_sizes:
        raise TrainingDataSerializationError(
            "Historical fixed target-size study has an invalid qualified-size set."
        )
    candidate_sizes = {candidate.target_size for candidate in candidates}
    if not set(qualified_sizes).issubset(candidate_sizes):
        raise TrainingDataSerializationError(
            "Historical fixed target-size qualified sizes are outside its candidate population."
        )
    candidate_digests = tuple(candidate.content_digest for candidate in candidates)
    authority_digest = digest({
        "schema": LEGACY_FIXED_CANDIDATE_AUTHORITY_SCHEMA,
        "dataset_id": str(raw["dataset_id"]),
        "repair2_authority_digest": str(raw["repair2_authority_digest"]),
        "mvqual_authority_digest": str(raw["mvqual_authority_digest"]),
        "policy_digest": policy_digest,
        "candidate_digests": list(candidate_digests),
        "qualified_sizes": list(qualified_sizes),
    })
    receipt = {
        "schema": HISTORICAL_FIXED_CANDIDATE_AUTHORITY_RECEIPT_SCHEMA,
        "generation": LEGACY_FIXED_CANDIDATE_AUTHORITY_GENERATION,
        "historical_study_digest": observed_digest or digest(raw),
        "historical_policy_digest": policy_digest,
        "candidate_authority_digest": authority_digest,
        "dataset_id": str(raw["dataset_id"]),
        "repair2_authority_digest": str(raw["repair2_authority_digest"]),
        "mvqual_authority_digest": str(raw["mvqual_authority_digest"]),
        "candidate_digests": list(candidate_digests),
        "qualified_sizes": list(qualified_sizes),
    }
    return {**receipt, "content_digest": digest(receipt)}


def _repair_domains(repair: Any) -> tuple[Any, ...]:
    domains = tuple(
        sorted(tuple(repair.domains), key=lambda v: str(v.label_domain_id))
    )
    if not domains or len({str(v.label_domain_id) for v in domains}) != len(domains):
        raise TrainingDataInputError(
            "REPAIR2 authority must contain unique non-empty domains."
        )
    return domains


def _prefix_digest(
    dataset_id: str, domain: Any, target_size: int
) -> tuple[str, str]:
    size = int(target_size)
    uids = tuple(str(v) for v in tuple(domain.repaired_master_order)[:size])
    payload = {
        "schema": TARGET_SIZE_PREFIX_SCHEMA,
        "dataset_id": str(dataset_id),
        "label_domain_id": str(domain.label_domain_id),
        "target_size": size,
        "frame_uids": list(uids),
    }
    return str(domain.label_domain_id), digest(payload)


def _candidate_data_digest(
    dataset_id: str,
    repair_digest: str,
    target_size: int,
    prefix_digests: Sequence[tuple[str, str]],
) -> str:
    return digest(
        {
            "schema": TARGET_SIZE_CANDIDATE_DATA_SCHEMA,
            "dataset_id": str(dataset_id),
            "repair2_authority_digest": str(repair_digest),
            "target_size": int(target_size),
            "domain_prefix_digests": [list(v) for v in prefix_digests],
        }
    )


def build_target_size_study(
    repair2: Any,
    mvqual: Any,
    *,
    policy: TargetSizeStudyPolicy | None = None,
) -> TargetSizeStudyPlan:
    """Build the sole v5 target-size authority directly from REPAIR2 + MVQUAL."""

    policy = policy or TargetSizeStudyPolicy()
    dataset_id = str(repair2.dataset_id)
    if dataset_id != str(mvqual.dataset_id):
        raise TrainingDataInputError("REPAIR2 and MVQUAL dataset identities differ.")
    repair_digest = validate_digest(
        repair2.content_digest, name="repair2.content_digest"
    )
    mvqual_digest = validate_digest(
        mvqual.content_digest, name="mvqual.content_digest"
    )
    if (
        validate_digest(
            mvqual.target_multi_view_repair_digest,
            name="mvqual.target_multi_view_repair_digest",
        )
        != repair_digest
    ):
        raise TrainingDataInputError(
            "MVQUAL no longer authenticates the supplied REPAIR2 authority."
        )
    qualified_from_mvqual = tuple(
        sorted(set(int(v) for v in mvqual.mv_qualified_sizes))
    )
    unknown = tuple(
        v for v in qualified_from_mvqual if v not in FIXED_TARGET_SIZES
    )
    if unknown:
        raise TrainingDataInputError(
            f"MVQUAL qualified target sizes outside the v5 fixed universe: {list(unknown)}."
        )
    domains = _repair_domains(repair2)
    candidates: list[TargetSizeStudyCandidate] = []
    for size in policy.candidate_sizes:
        materializable = all(
            len(tuple(domain.repaired_master_order)) >= size for domain in domains
        )
        prefix_digests = tuple(
            _prefix_digest(dataset_id, domain, size) for domain in domains
        )
        candidate_data = _candidate_data_digest(
            dataset_id, repair_digest, size, prefix_digests
        )
        hard_pass = size in qualified_from_mvqual
        if hard_pass and not materializable:
            raise TrainingDataInputError(
                f"MVQUAL qualifies n{size}, but at least one REPAIR2 domain cannot materialize that prefix."
            )
        candidates.append(
            TargetSizeStudyCandidate(
                size,
                materializable,
                hard_pass,
                prefix_digests,
                candidate_data,
            )
        )
    qualified = tuple(v.target_size for v in candidates if v.qualified)
    if len(qualified) < policy.minimum_qualified_sizes:
        return TargetSizeStudyPlan(
            dataset_id=dataset_id,
            repair2_authority_digest=repair_digest,
            mvqual_authority_digest=mvqual_digest,
            policy=policy,
            candidates=tuple(candidates),
            qualified_sizes=qualified,
            outcome=OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
            decision_reason=(
                f"MVQUAL admitted {len(qualified)} fixed candidates; at least three are required"
            ),
        )
    return TargetSizeStudyPlan(
        dataset_id=dataset_id,
        repair2_authority_digest=repair_digest,
        mvqual_authority_digest=mvqual_digest,
        policy=policy,
        candidates=tuple(candidates),
        qualified_sizes=qualified,
        outcome=OUTCOME_AWAITING_COARSE_SCREEN,
        decision_reason=(
            f"MVQUAL admitted {len(qualified)} fixed candidates; awaiting exact coarse-screen target-only evidence"
        ),
    )


def validate_target_size_study_authority(
    plan: TargetSizeStudyPlan,
    *,
    repair2: Any,
    mvqual: Any,
) -> None:
    rebuilt = build_target_size_study(repair2, mvqual, policy=plan.policy)
    if (
        plan.dataset_id != rebuilt.dataset_id
        or plan.repair2_authority_digest != rebuilt.repair2_authority_digest
        or plan.mvqual_authority_digest != rebuilt.mvqual_authority_digest
    ):
        raise TrainingDataInputError(
            "Target-size study upstream authority has changed."
        )
    if tuple(v.content_digest for v in plan.candidates) != tuple(
        v.content_digest for v in rebuilt.candidates
    ):
        raise TrainingDataInputError(
            "Target-size study candidate prefixes/qualification no longer match REPAIR2 + MVQUAL."
        )
    if plan.qualified_sizes != rebuilt.qualified_sizes:
        raise TrainingDataInputError(
            "Target-size study qualified set no longer matches MVQUAL."
        )


def materialize_candidate_prefix(
    plan: TargetSizeStudyPlan,
    *,
    repair2: Any,
    label_domain_id: str,
    target_size: int,
) -> tuple[str, ...]:
    """Return one exact authenticated REPAIR2 prefix for study or production use."""

    if (
        validate_digest(repair2.content_digest, name="repair2.content_digest")
        != plan.repair2_authority_digest
    ):
        raise TrainingDataInputError(
            "REPAIR2 authority does not match target-size study."
        )
    candidate = plan.candidate(target_size)
    try:
        domain = repair2.domain(str(label_domain_id))
    except (KeyError, AttributeError) as exc:
        raise TrainingDataInputError(
            f"Unknown REPAIR2 label domain {label_domain_id!r}."
        ) from exc
    uids = tuple(
        str(v)
        for v in tuple(domain.repaired_master_order)[: candidate.target_size]
    )
    if len(uids) != candidate.target_size:
        raise TrainingDataInputError(
            f"REPAIR2 cannot materialize n{candidate.target_size} for {label_domain_id}."
        )
    prefix = _prefix_digest(plan.dataset_id, domain, candidate.target_size)
    expected = dict(candidate.domain_prefix_digests).get(str(label_domain_id))
    if expected is None or prefix[1] != expected:
        raise TrainingDataInputError(
            "REPAIR2 prefix changed after target-size study authentication."
        )
    return uids


def materialize_candidate_prefix_matrix(
    plan: TargetSizeStudyPlan,
    *,
    repair2: Any,
    label_domain_ids: Sequence[str],
    target_sizes: Sequence[int],
) -> dict[tuple[str, int], tuple[str, ...]]:
    """Materialize unique authenticated REPAIR2 prefixes in one authority pass.

    The scalar helper remains the public single-prefix convenience API.  This
    bulk path exists for screening/materialization planning so REPAIR2 identity
    and domain lookup are not repeated once per optimizer variant or frame UID.
    """

    if (
        validate_digest(repair2.content_digest, name="repair2.content_digest")
        != plan.repair2_authority_digest
    ):
        raise TrainingDataInputError(
            "REPAIR2 authority does not match target-size study."
        )
    labels = tuple(dict.fromkeys(str(value) for value in label_domain_ids))
    sizes = tuple(dict.fromkeys(int(value) for value in target_sizes))
    candidates = {size: plan.candidate(size) for size in sizes}
    expected_prefix_by_size = {
        size: dict(candidate.domain_prefix_digests)
        for size, candidate in candidates.items()
    }
    domains: dict[str, Any] = {}
    for label in labels:
        try:
            domains[label] = repair2.domain(label)
        except (KeyError, AttributeError) as exc:
            raise TrainingDataInputError(
                f"Unknown REPAIR2 label domain {label!r}."
            ) from exc

    result: dict[tuple[str, int], tuple[str, ...]] = {}
    for label in labels:
        domain = domains[label]
        repaired_order = tuple(str(value) for value in domain.repaired_master_order)
        for size in sizes:
            candidate = candidates[size]
            uids = repaired_order[: candidate.target_size]
            if len(uids) != candidate.target_size:
                raise TrainingDataInputError(
                    f"REPAIR2 cannot materialize n{candidate.target_size} for {label}."
                )
            prefix = _prefix_digest(plan.dataset_id, domain, candidate.target_size)
            expected = expected_prefix_by_size[size].get(label)
            if expected is None or prefix[1] != expected:
                raise TrainingDataInputError(
                    "REPAIR2 prefix changed after target-size study authentication."
                )
            result[(label, size)] = uids
    return result


def materialize_selected_prefix(
    plan: TargetSizeStudyPlan,
    *,
    repair2: Any,
    label_domain_id: str,
) -> tuple[str, ...]:
    if plan.outcome != OUTCOME_SELECTED or plan.selected_target_size is None:
        raise TrainingDataInputError(
            "Production target corpus cannot be materialized before target-size selection."
        )
    return materialize_candidate_prefix(
        plan,
        repair2=repair2,
        label_domain_id=label_domain_id,
        target_size=plan.selected_target_size,
    )


def _outcomes_from_evidence(
    outcomes: Sequence[TargetSizeTrainingEvidence | TargetSizeTrajectoryFailureEvidence | TargetSizeStageOutcome],
) -> tuple[TargetSizeStageOutcome, ...]:
    result: list[TargetSizeStageOutcome] = []
    for item in outcomes:
        if isinstance(item, TargetSizeStageOutcome):
            result.append(item)
        elif isinstance(item, TargetSizeTrainingEvidence):
            result.append(TargetSizeStageOutcome(success=item))
        elif isinstance(item, TargetSizeTrajectoryFailureEvidence):
            result.append(TargetSizeStageOutcome(failure=item))
        else:
            raise TrainingDataInputError(f"Unsupported target-size stage outcome type {type(item).__name__}.")
    return tuple(result)


def _expected_keys(plan: TargetSizeStudyPlan, sizes: Sequence[int]) -> tuple[tuple[int, int], ...]:
    return tuple((int(size), int(seed)) for size in sizes for seed in plan.policy.screening_optimizer_seeds)


def _comparison_failures(
    outcomes: Sequence[TargetSizeStageOutcome], sizes: Sequence[int]
) -> tuple[tuple[int, int, tuple[str, ...]], ...]:
    allowed = set(int(v) for v in sizes)
    result = []
    for outcome in outcomes:
        failure = outcome.failure
        if failure is not None and failure.target_size in allowed:
            result.append((failure.target_size, failure.optimizer_seed, (failure.failure_code, *failure.failure_reasons)))
    return tuple(result)


def _validate_outcome_batch(
    plan: TargetSizeStudyPlan,
    outcomes: Sequence[TargetSizeStageOutcome],
    sizes: Sequence[int],
    stage: str,
) -> dict[tuple[int, int], TargetSizeStageOutcome]:
    expected_endpoint = {
        STAGE_COARSE: plan.policy.fidelity_epochs[0],
        STAGE_SHORT: plan.policy.fidelity_epochs[1],
        STAGE_FINAL_SCREEN: plan.policy.fidelity_epochs[2],
    }[stage]
    expected = _expected_keys(plan, sizes)
    actual = tuple(item.key for item in outcomes)
    if actual != expected:
        raise TrainingDataInputError(
            f"Target-size {stage} outcome population must exactly equal policy-ordered (size, seed) population; expected={list(expected)}, observed={list(actual)}."
        )
    by_key = {item.key: item for item in outcomes}
    if len(by_key) != len(outcomes):
        raise TrainingDataInputError("Target-size stage outcome population contains duplicate keys.")
    training_policy_digests: set[str] = set()
    schedule_digests: set[str] = set()
    success_foundation_digests: set[str] = set()
    success_role_digests: set[str] = set()
    for outcome in outcomes:
        if outcome.stage != stage:
            raise TrainingDataInputError("Target-size stage outcome carries the wrong fidelity stage.")
        item = outcome.success if outcome.success is not None else outcome.failure
        assert item is not None
        candidate = plan.candidate(item.target_size)
        if item.candidate_data_digest != candidate.candidate_data_digest:
            raise TrainingDataInputError("Target-size stage outcome candidate_data_digest mismatch.")
        if item.target_size_study_policy_digest != plan.policy.policy_digest:
            raise TrainingDataInputError("Target-size stage outcome policy digest mismatch.")
        if outcome.success is not None:
            if item.completed_epochs != expected_endpoint:
                raise TrainingDataInputError("Target-size evidence is not at the configured semantic-stage boundary.")
        training_policy_digests.add(item.training_policy_digest)
        schedule_digests.add(item.schedule_digest)
        if outcome.success is not None:
            success_foundation_digests.add(outcome.success.foundation_identity_digest)
            success_role_digests.add(outcome.success.evaluation_role_digest)
    if len(training_policy_digests) != 1 or len(schedule_digests) != 1:
        raise TrainingDataInputError("Target-size stage outcomes do not share one frozen training-policy/schedule identity.")
    if len(success_foundation_digests) > 1 or len(success_role_digests) > 1:
        raise TrainingDataInputError("Successful target-size candidates do not share one foundation/evaluation-role identity.")
    return by_key


def _validate_continuation(parent: TargetSizeStageOutcome, child: TargetSizeStageOutcome) -> None:
    if parent.success is None:
        raise TrainingDataInputError("Target-size continuation cannot descend from a failed parent trajectory.")
    parent_item = parent.success
    child_item = child.success if child.success is not None else child.failure
    assert child_item is not None
    for attr in ("target_size", "optimizer_seed", "training_run_digest", "training_policy_digest", "schedule_digest", "candidate_data_digest"):
        if getattr(child_item, attr) != getattr(parent_item, attr):
            raise TrainingDataInputError(f"Target-size continuation changed {attr}.")
    if child.success is not None:
        if child.success.parent_checkpoint_digest != parent_item.checkpoint_digest:
            raise TrainingDataInputError("Target-size continuation checkpoint ancestry changed.")
        if child.success.parent_optimizer_state_digest != parent_item.optimizer_state_digest:
            raise TrainingDataInputError("Target-size continuation optimizer ancestry changed.")
        if child.success.parent_rng_state_digest != parent_item.rng_state_digest:
            raise TrainingDataInputError("Target-size continuation RNG ancestry changed.")
        if child.success.optimizer_update_count <= parent_item.optimizer_update_count:
            raise TrainingDataInputError("Target-size continuation optimizer progress did not increase.")
        if child.success.structures_presented <= parent_item.structures_presented:
            raise TrainingDataInputError("Target-size continuation exposure did not increase.")


def _paired_candidate_scores(
    plan: TargetSizeStudyPlan,
    by_key: Mapping[tuple[int, int], TargetSizeStageOutcome],
    sizes: Sequence[int],
) -> dict[int, float]:
    result: dict[int, float] = {}
    for size in sizes:
        values: list[float] = []
        for seed in plan.policy.screening_optimizer_seeds:
            outcome = by_key[(int(size), int(seed))]
            if outcome.failure is not None:
                break
            assert outcome.success is not None
            values.append(outcome.success.target_force_score_mev_per_a)
        else:
            result[int(size)] = sum(values) / float(len(values))
    return result


def _equivalence_aware_score_order(scores: Mapping[int, float], *, epsilon: float) -> tuple[int, ...]:
    remaining = sorted(scores, key=lambda size: (scores[size], size))
    ordered: list[int] = []
    while remaining:
        anchor = scores[remaining[0]]
        band = [size for size in remaining if scores[size] <= anchor + float(epsilon) + 1.0e-12]
        band.sort()
        ordered.extend(band)
        band_set = set(band)
        remaining = [size for size in remaining if size not in band_set]
    return tuple(ordered)


def _equivalence_aware_target_order(evidence: Sequence[TargetSizeTrainingEvidence], *, epsilon: float) -> tuple[int, ...]:
    scores: dict[int, float] = {}
    for item in evidence:
        if item.target_size in scores:
            raise TrainingDataInputError("Direct equivalence ordering accepts one score per target size.")
        scores[item.target_size] = item.target_force_score_mev_per_a
    return _equivalence_aware_score_order(scores, epsilon=epsilon)


def _validate_target_size_study_semantics(plan: TargetSizeStudyPlan) -> None:
    qualified = plan.qualified_sizes
    q = len(qualified)
    allowed = {
        OUTCOME_INSUFFICIENT_QUALIFIED_SIZES, OUTCOME_AWAITING_COARSE_SCREEN,
        OUTCOME_AWAITING_SHORT_SCREEN, OUTCOME_AWAITING_FINAL_SCREEN,
        OUTCOME_SELECTED, OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
        OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
    }
    if plan.outcome not in allowed:
        raise TrainingDataInputError("Unsupported target-size study outcome.")
    if q < plan.policy.minimum_qualified_sizes:
        if (plan.outcome != OUTCOME_INSUFFICIENT_QUALIFIED_SIZES or plan.coarse_outcomes or
            plan.coarse_survivor_sizes or plan.short_outcomes or plan.short_finalist_sizes or
            plan.final_screen_outcomes or plan.selected_target_size is not None or
            plan.comparison_failure_stage is not None or plan.comparison_failures):
            raise TrainingDataInputError("Sub-threshold qualified set must terminate as insufficient_qualified_sizes.")
        return
    if plan.outcome == OUTCOME_INSUFFICIENT_QUALIFIED_SIZES:
        raise TrainingDataInputError("Qualified set meets the minimum; insufficient_qualified_sizes is inconsistent.")
    if not plan.coarse_outcomes:
        if (plan.outcome != OUTCOME_AWAITING_COARSE_SCREEN or plan.coarse_survivor_sizes or plan.short_outcomes or
            plan.short_finalist_sizes or plan.final_screen_outcomes or plan.selected_target_size is not None or
            plan.comparison_failure_stage is not None or plan.comparison_failures):
            raise TrainingDataInputError("Coarse-screen wait state is inconsistent.")
        return
    e3 = _validate_outcome_batch(plan, plan.coarse_outcomes, qualified, STAGE_COARSE)
    scores3 = _paired_candidate_scores(plan, e3, qualified)
    required3 = min(q, plan.policy.coarse_survivor_limit)
    if len(scores3) < required3:
        expected_failures = _comparison_failures(plan.coarse_outcomes, qualified)
        if (plan.outcome != OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES or
            plan.comparison_failure_stage != STAGE_COARSE or plan.comparison_failures != expected_failures or
            plan.coarse_survivor_sizes or plan.short_outcomes or plan.short_finalist_sizes or plan.final_screen_outcomes or
            plan.selected_target_size is not None):
            raise TrainingDataInputError("Coarse-screen insufficient-comparable terminal state is inconsistent.")
        return
    expected_s3 = _equivalence_aware_score_order(scores3, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a)[:required3]
    if plan.coarse_survivor_sizes != expected_s3:
        raise TrainingDataInputError("Coarse-screen survivor decision does not match paired aggregate/equivalence policy.")
    if not plan.short_outcomes:
        if (plan.outcome != OUTCOME_AWAITING_SHORT_SCREEN or plan.short_finalist_sizes or plan.final_screen_outcomes or
            plan.selected_target_size is not None or plan.comparison_failure_stage is not None or plan.comparison_failures):
            raise TrainingDataInputError("Short-screen wait state is inconsistent.")
        return
    e10 = _validate_outcome_batch(plan, plan.short_outcomes, plan.coarse_survivor_sizes, STAGE_SHORT)
    for key, child in e10.items():
        _validate_continuation(e3[key], child)
    scores10 = _paired_candidate_scores(plan, e10, plan.coarse_survivor_sizes)
    if len(scores10) < plan.policy.short_finalist_count:
        expected_failures = _comparison_failures(plan.short_outcomes, plan.coarse_survivor_sizes)
        if (plan.outcome != OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES or
            plan.comparison_failure_stage != STAGE_SHORT or plan.comparison_failures != expected_failures or
            plan.short_finalist_sizes or plan.final_screen_outcomes or plan.selected_target_size is not None):
            raise TrainingDataInputError("Short-screen insufficient-comparable terminal state is inconsistent.")
        return
    expected_s10 = _equivalence_aware_score_order(scores10, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a)[: plan.policy.short_finalist_count]
    if plan.short_finalist_sizes != expected_s10:
        raise TrainingDataInputError("Short-screen finalist decision does not match paired aggregate/equivalence policy.")
    if not plan.final_screen_outcomes:
        if (plan.outcome != OUTCOME_AWAITING_FINAL_SCREEN or plan.selected_target_size is not None or
            plan.comparison_failure_stage is not None or plan.comparison_failures):
            raise TrainingDataInputError("Final-screen wait state is inconsistent.")
        return
    e30 = _validate_outcome_batch(plan, plan.final_screen_outcomes, plan.short_finalist_sizes, STAGE_FINAL_SCREEN)
    for key, child in e30.items():
        _validate_continuation(e10[key], child)
    scores30 = _paired_candidate_scores(plan, e30, plan.short_finalist_sizes)
    if len(scores30) < plan.policy.short_finalist_count:
        expected_failures = _comparison_failures(plan.final_screen_outcomes, plan.short_finalist_sizes)
        if (plan.outcome != OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES or
            plan.comparison_failure_stage != STAGE_FINAL_SCREEN or plan.comparison_failures != expected_failures or
            plan.selected_target_size is not None):
            raise TrainingDataInputError("Final-screen insufficient-comparable terminal state is inconsistent.")
        return
    ranking = _equivalence_aware_score_order(scores30, epsilon=plan.policy.practical_equivalence_mev_per_a)
    winner = ranking[0]
    if winner == FIXED_TARGET_SIZE_CEILING:
        smaller = [size for size in scores30 if size < winner]
        if smaller and all(scores30[size] - scores30[winner] > plan.policy.practical_equivalence_mev_per_a + 1.0e-12 for size in smaller):
            if plan.outcome != OUTCOME_NONCONVERGED_AT_FIXED_CEILING or plan.selected_target_size is not None or plan.comparison_failure_stage is not None or plan.comparison_failures:
                raise TrainingDataInputError("Fixed-ceiling terminal state does not match final paired comparison.")
            return
    if plan.outcome != OUTCOME_SELECTED or plan.selected_target_size != winner or plan.comparison_failure_stage is not None or plan.comparison_failures:
        raise TrainingDataInputError("Selected target size does not match final paired aggregate/equivalence policy.")


def _insufficient_comparable_result(
    plan: TargetSizeStudyPlan,
    *, stage: str, outcome_field: str, outcomes: tuple[TargetSizeStageOutcome, ...], sizes: Sequence[int],
) -> TargetSizeStudyPlan:
    return replace(
        plan,
        **{outcome_field: outcomes},
        selected_target_size=None,
        outcome=OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
        comparison_failure_stage=stage,
        comparison_failures=_comparison_failures(outcomes, sizes),
        decision_reason=f"{stage} target-size comparison has too few complete paired successful candidates",
    )


def attach_coarse_outcomes(
    plan: TargetSizeStudyPlan,
    outcomes: Sequence[TargetSizeTrainingEvidence | TargetSizeTrajectoryFailureEvidence | TargetSizeStageOutcome],
) -> TargetSizeStudyPlan:
    if plan.outcome != OUTCOME_AWAITING_COARSE_SCREEN:
        raise TrainingDataInputError("Coarse outcomes can only be attached while awaiting the coarse screen.")
    batch = _outcomes_from_evidence(outcomes)
    by_key = _validate_outcome_batch(plan, batch, plan.qualified_sizes, STAGE_COARSE)
    scores = _paired_candidate_scores(plan, by_key, plan.qualified_sizes)
    required = min(len(plan.qualified_sizes), plan.policy.coarse_survivor_limit)
    if len(scores) < required:
        return _insufficient_comparable_result(plan, stage=STAGE_COARSE, outcome_field="coarse_outcomes", outcomes=batch, sizes=plan.qualified_sizes)
    survivors = _equivalence_aware_score_order(scores, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a)[:required]
    return replace(plan, coarse_outcomes=batch, coarse_survivor_sizes=survivors, outcome=OUTCOME_AWAITING_SHORT_SCREEN,
                   decision_reason="coarse paired target-only screen complete; awaiting short-screen continuation")


def attach_short_outcomes(
    plan: TargetSizeStudyPlan,
    outcomes: Sequence[TargetSizeTrainingEvidence | TargetSizeTrajectoryFailureEvidence | TargetSizeStageOutcome],
) -> TargetSizeStudyPlan:
    if plan.outcome != OUTCOME_AWAITING_SHORT_SCREEN:
        raise TrainingDataInputError("Short outcomes can only be attached while awaiting the short screen.")
    batch = _outcomes_from_evidence(outcomes)
    by_key = _validate_outcome_batch(plan, batch, plan.coarse_survivor_sizes, STAGE_SHORT)
    parents = {item.key: item for item in plan.coarse_outcomes}
    for key, child in by_key.items():
        _validate_continuation(parents[key], child)
    scores = _paired_candidate_scores(plan, by_key, plan.coarse_survivor_sizes)
    if len(scores) < plan.policy.short_finalist_count:
        return _insufficient_comparable_result(plan, stage=STAGE_SHORT, outcome_field="short_outcomes", outcomes=batch, sizes=plan.coarse_survivor_sizes)
    finalists = _equivalence_aware_score_order(scores, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a)[: plan.policy.short_finalist_count]
    return replace(plan, short_outcomes=batch, short_finalist_sizes=finalists, outcome=OUTCOME_AWAITING_FINAL_SCREEN,
                   decision_reason="short paired target-only screen complete; awaiting final-screen continuation")


def attach_final_screen_outcomes(
    plan: TargetSizeStudyPlan,
    outcomes: Sequence[TargetSizeTrainingEvidence | TargetSizeTrajectoryFailureEvidence | TargetSizeStageOutcome],
) -> TargetSizeStudyPlan:
    if plan.outcome != OUTCOME_AWAITING_FINAL_SCREEN:
        raise TrainingDataInputError("Final-screen outcomes can only be attached while awaiting the final screen.")
    batch = _outcomes_from_evidence(outcomes)
    by_key = _validate_outcome_batch(plan, batch, plan.short_finalist_sizes, STAGE_FINAL_SCREEN)
    parents = {item.key: item for item in plan.short_outcomes}
    for key, child in by_key.items():
        _validate_continuation(parents[key], child)
    scores = _paired_candidate_scores(plan, by_key, plan.short_finalist_sizes)
    if len(scores) < plan.policy.short_finalist_count:
        return _insufficient_comparable_result(plan, stage=STAGE_FINAL_SCREEN, outcome_field="final_screen_outcomes", outcomes=batch, sizes=plan.short_finalist_sizes)
    ranking = _equivalence_aware_score_order(scores, epsilon=plan.policy.practical_equivalence_mev_per_a)
    winner = ranking[0]
    if winner == FIXED_TARGET_SIZE_CEILING:
        smaller = [size for size in scores if size < winner]
        if smaller and all(scores[size] - scores[winner] > plan.policy.practical_equivalence_mev_per_a + 1.0e-12 for size in smaller):
            improvement = min(scores[size] - scores[winner] for size in smaller)
            return replace(plan, final_screen_outcomes=batch, selected_target_size=None, outcome=OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
                           decision_reason=f"n16384 improves paired target force score by at least {improvement:.6g} meV/A beyond practical equivalence; the fixed ceiling is exhausted and rescue above 16384 is forbidden")
    return replace(plan, final_screen_outcomes=batch, selected_target_size=winner, outcome=OUTCOME_SELECTED,
                   decision_reason=f"final-screen paired comparison selected n{winner}; target size is immutable before held-out validation")


def attach_coarse_evidence(plan: TargetSizeStudyPlan, evidence: Sequence[TargetSizeTrainingEvidence]) -> TargetSizeStudyPlan:
    return attach_coarse_outcomes(plan, evidence)


def attach_short_evidence(plan: TargetSizeStudyPlan, evidence: Sequence[TargetSizeTrainingEvidence]) -> TargetSizeStudyPlan:
    return attach_short_outcomes(plan, evidence)


def attach_final_screen_evidence(plan: TargetSizeStudyPlan, evidence: Sequence[TargetSizeTrainingEvidence]) -> TargetSizeStudyPlan:
    return attach_final_screen_outcomes(plan, evidence)


__all__ = [
    "FIXED_TARGET_SIZES", "FIXED_TARGET_SIZE_CEILING",
    "TARGET_SIZE_STUDY_VERSION", "TARGET_SIZE_STUDY_POLICY_SCHEMA", "TARGET_SIZE_STUDY_CANDIDATE_SCHEMA",
    "TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA", "TARGET_SIZE_TRAJECTORY_FAILURE_EVIDENCE_SCHEMA",
    "TARGET_SIZE_STAGE_OUTCOME_SCHEMA", "TARGET_SIZE_STUDY_PLAN_SCHEMA",
    "TARGET_SIZE_PREFIX_SCHEMA", "TARGET_SIZE_CANDIDATE_DATA_SCHEMA", "TARGET_SIZE_CANDIDATE_AUTHORITY_SCHEMA",
    "TARGET_SIZE_CANDIDATE_AUTHORITY_GENERATION", "LEGACY_FIXED_CANDIDATE_AUTHORITY_SCHEMA",
    "LEGACY_FIXED_CANDIDATE_AUTHORITY_GENERATION",
    "HISTORICAL_FIXED_CANDIDATE_AUTHORITY_RECEIPT_SCHEMA",
    "OUTCOME_INSUFFICIENT_QUALIFIED_SIZES", "OUTCOME_AWAITING_COARSE_SCREEN", "OUTCOME_AWAITING_SHORT_SCREEN",
    "OUTCOME_AWAITING_FINAL_SCREEN", "OUTCOME_SELECTED", "OUTCOME_NONCONVERGED_AT_FIXED_CEILING",
    "OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES",
    "STAGE_COARSE", "STAGE_SHORT", "STAGE_FINAL_SCREEN",
    "FAILURE_PHASE_TRAIN", "FAILURE_PHASE_TARGET_EVALUATION",
    "TRAIN2_NUMERICAL_FAILURE_CODES", "EVAL2_NUMERICAL_FAILURE_CODES", "TARGET_SIZE_SCIENTIFIC_FAILURE_CODES",
    "TargetSizeStudyPolicy", "TargetSizeStudyCandidate", "TargetSizeTrainingEvidence",
    "TargetSizeTrajectoryFailureEvidence", "TargetSizeStageOutcome", "TargetSizeStudyPlan",
    "build_target_size_study", "validate_target_size_study_authority",
    "authenticated_fixed_predecessor_candidate_authority",
    "materialize_candidate_prefix", "materialize_candidate_prefix_matrix", "materialize_selected_prefix",
    "attach_coarse_outcomes", "attach_short_outcomes", "attach_final_screen_outcomes",
    "attach_coarse_evidence", "attach_short_evidence", "attach_final_screen_evidence",
    "_equivalence_aware_target_order",
]
