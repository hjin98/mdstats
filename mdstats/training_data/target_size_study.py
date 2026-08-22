"""V5 fixed-universe target-size study authority.

The study consumes only REPAIR2 prefix order and MVQUAL hard eligibility. It
owns the complete 3/10/30 TRAIN2 successive-fidelity funnel and freezes the
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

TARGET_SIZE_STUDY_VERSION = "mdstats.target-size-study.fixed-eight.2026-08.v5.2"
TARGET_SIZE_STUDY_POLICY_SCHEMA = "mdstats.target-size-study-policy.v6"
TARGET_SIZE_STUDY_CANDIDATE_SCHEMA = "mdstats.target-size-study-candidate.v5"
TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA = "mdstats.target-size-training-evidence.v6"
TARGET_SIZE_STUDY_PLAN_SCHEMA = "mdstats.target-size-study-plan.v7"
TARGET_SIZE_PREFIX_SCHEMA = "mdstats.target-size-study-repair2-prefix.v1"
TARGET_SIZE_CANDIDATE_DATA_SCHEMA = "mdstats.target-size-study-candidate-data.v1"
TARGET_SIZE_CANDIDATE_AUTHORITY_SCHEMA = "mdstats.target-size-study-candidate-authority.v1"

FIXED_TARGET_SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)
FIXED_TARGET_SIZE_CEILING = FIXED_TARGET_SIZES[-1]

OUTCOME_INSUFFICIENT_QUALIFIED_SIZES = "insufficient_qualified_sizes"
OUTCOME_AWAITING_EPOCH_3 = "awaiting_epoch_3"
OUTCOME_AWAITING_EPOCH_10 = "awaiting_epoch_10"
OUTCOME_AWAITING_EPOCH_30 = "awaiting_epoch_30"
OUTCOME_SELECTED = "selected"
OUTCOME_NONCONVERGED_AT_FIXED_CEILING = "nonconverged_at_fixed_ceiling"
OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES = "insufficient_comparable_candidates"

_TERMINAL_OUTCOMES = {
    OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
    OUTCOME_SELECTED,
    OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
    OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
}
_STAGE_FOR_EPOCH = {3: "coarse", 10: "short", 30: "final"}


@dataclass(frozen=True, slots=True)
class TargetSizeStudyPolicy:
    """Frozen fixed-universe policy with authenticated paired training seeds."""

    candidate_sizes: tuple[int, ...] = FIXED_TARGET_SIZES
    minimum_qualified_sizes: int = 3
    epoch3_survivor_limit: int = 4
    epoch10_finalist_count: int = 2
    fidelity_epochs: tuple[int, int, int] = (3, 10, 30)
    practical_equivalence_mev_per_a: float = 1.0
    coarse_practical_equivalence_mev_per_a: float = 1.0
    screening_optimizer_seeds: tuple[int, ...] = (1, 2)
    paired_seed_aggregation: str = "arithmetic_mean"
    authority_version: str = TARGET_SIZE_STUDY_VERSION

    def __post_init__(self) -> None:
        sizes = tuple(int(v) for v in self.candidate_sizes)
        epochs = tuple(int(v) for v in self.fidelity_epochs)
        if sizes != FIXED_TARGET_SIZES:
            raise TrainingDataInputError(
                "Target-size v5 freezes the candidate universe at 128..16384 powers of two."
            )
        if int(self.minimum_qualified_sizes) != 3:
            raise TrainingDataInputError(
                "Target-size v5 freezes the qualification threshold at three."
            )
        if int(self.epoch3_survivor_limit) != 4 or int(self.epoch10_finalist_count) != 2:
            raise TrainingDataInputError(
                "Target-size v5 freezes the 3/10/30 funnel at q->min(q,4)->2->1."
            )
        if epochs != (3, 10, 30):
            raise TrainingDataInputError(
                "Target-size v5 freezes TRAIN2 fidelity boundaries at 3/10/30 epochs."
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
        object.__setattr__(self, "epoch3_survivor_limit", 4)
        object.__setattr__(self, "epoch10_finalist_count", 2)
        object.__setattr__(self, "fidelity_epochs", epochs)
        object.__setattr__(self, "screening_optimizer_seeds", seeds)
        object.__setattr__(self, "paired_seed_aggregation", "arithmetic_mean")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_STUDY_POLICY_SCHEMA,
            "authority_version": self.authority_version,
            "candidate_sizes": list(self.candidate_sizes),
            "minimum_qualified_sizes": self.minimum_qualified_sizes,
            "epoch3_survivor_limit": self.epoch3_survivor_limit,
            "epoch10_finalist_count": self.epoch10_finalist_count,
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
                "Historical scalar-seed target-size policy is not restart-compatible with the paired-seed authority."
            )
        if "screening_optimizer_seeds" not in payload:
            raise TrainingDataSerializationError(
                "Target-size policy is missing the authenticated ordered screening seed set."
            )
        result = cls(
            candidate_sizes=tuple(int(v) for v in payload["candidate_sizes"]),
            minimum_qualified_sizes=int(payload["minimum_qualified_sizes"]),
            epoch3_survivor_limit=int(payload["epoch3_survivor_limit"]),
            epoch10_finalist_count=int(payload["epoch10_finalist_count"]),
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
    """Authenticated TRAIN2 endpoint evidence for a v5 candidate trajectory."""

    stage: str
    target_size: int
    optimizer_seed: int
    completed_epochs: int
    planned_epochs: int
    optimizer_update_count: int
    structures_presented: int
    normalized_schedule_progress: float
    instantaneous_learning_rate: float
    wall_time_seconds: float
    target_force_score_mev_per_a: float
    numerical_valid: bool
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
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        stage = str(self.stage).strip().lower()
        if stage not in {"coarse", "short", "final"}:
            raise TrainingDataInputError(
                "Target-size training stage must be coarse, short, or final."
            )
        size = int(self.target_size)
        seed = int(self.optimizer_seed)
        completed = int(self.completed_epochs)
        planned = int(self.planned_epochs)
        updates = int(self.optimizer_update_count)
        structures = int(self.structures_presented)
        progress = float(self.normalized_schedule_progress)
        lr = float(self.instantaneous_learning_rate)
        wall = float(self.wall_time_seconds)
        score = float(self.target_force_score_mev_per_a)
        if (
            size not in FIXED_TARGET_SIZES
            or seed < 0
            or completed <= 0
            or planned < completed
            or updates <= 0
            or structures <= 0
        ):
            raise TrainingDataInputError("Target-size training evidence counts are invalid.")
        if not math.isfinite(progress) or not 0.0 <= progress <= 1.0:
            raise TrainingDataInputError("Target-size schedule progress is invalid.")
        if (
            not math.isfinite(lr)
            or lr <= 0.0
            or not math.isfinite(wall)
            or wall < 0.0
        ):
            raise TrainingDataInputError(
                "Target-size learning-rate/wall evidence is invalid."
            )
        if not math.isfinite(score) or score < 0.0:
            raise TrainingDataInputError(
                "Target-size force score must be finite and nonnegative."
            )
        for name in (
            "foundation_identity_digest",
            "evaluation_role_digest",
            "training_policy_digest",
            "target_size_study_policy_digest",
            "training_run_digest",
            "candidate_data_digest",
            "checkpoint_digest",
            "schedule_digest",
            "optimizer_state_digest",
            "rng_state_digest",
            "target_evaluation_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in (
            "replay_evaluation_digest",
            "physical_qualification_digest",
            "parent_checkpoint_digest",
            "parent_optimizer_state_digest",
            "parent_rng_state_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.replay_diagnostic_force_rmse_mev_per_a is not None:
            replay = float(self.replay_diagnostic_force_rmse_mev_per_a)
            if not math.isfinite(replay) or replay < 0.0:
                raise TrainingDataInputError(
                    "Replay diagnostic must be finite and nonnegative."
                )
            object.__setattr__(
                self, "replay_diagnostic_force_rmse_mev_per_a", replay
            )
        parents = (
            self.parent_checkpoint_digest,
            self.parent_optimizer_state_digest,
            self.parent_rng_state_digest,
        )
        if stage == "coarse":
            if any(v is not None for v in parents):
                raise TrainingDataInputError(
                    "Epoch-3 evidence cannot claim a continuation parent."
                )
            if any(
                v is not None
                for v in (
                    self.replay_diagnostic_force_rmse_mev_per_a,
                    self.replay_evaluation_digest,
                    self.replay_admissible,
                    self.physical_qualification_passed,
                    self.physical_qualification_digest,
                )
            ):
                raise TrainingDataInputError("Epoch-3 evidence is target-only.")
            if not (0.0 < progress < 1.0):
                raise TrainingDataInputError(
                    "Epoch-3 schedule progress must be inside the 30-epoch horizon."
                )
        elif stage == "short":
            if any(v is None for v in parents):
                raise TrainingDataInputError(
                    "Epoch-10 evidence requires exact epoch-3 checkpoint/optimizer/RNG ancestry."
                )
            if (
                self.replay_admissible is not None
                or self.physical_qualification_passed is not None
                or self.physical_qualification_digest is not None
            ):
                raise TrainingDataInputError(
                    "Epoch-10 evidence cannot carry final replay/physical pass authority."
                )
            if (self.replay_diagnostic_force_rmse_mev_per_a is None) != (
                self.replay_evaluation_digest is None
            ):
                raise TrainingDataInputError(
                    "Epoch-10 replay diagnostics require both value and digest."
                )
            if not (0.0 < progress < 1.0):
                raise TrainingDataInputError(
                    "Epoch-10 schedule progress must be inside the 30-epoch horizon."
                )
        else:
            if any(v is None for v in parents):
                raise TrainingDataInputError(
                    "Epoch-30 evidence requires exact epoch-10 checkpoint/optimizer/RNG ancestry."
                )
            if abs(progress - 1.0) > 1.0e-12:
                raise TrainingDataInputError(
                    "Epoch-30 schedule progress must be exactly complete."
                )
            if (self.replay_diagnostic_force_rmse_mev_per_a is None) != (
                self.replay_evaluation_digest is None
            ):
                raise TrainingDataInputError(
                    "Epoch-30 replay diagnostics require both value and digest when present."
                )
            if self.replay_admissible is not None or self.physical_qualification_passed is not None or self.physical_qualification_digest is not None:
                raise TrainingDataInputError(
                    "Target-size v5 forbids replay/physical hard-pass authority in epoch-30 size evidence; "
                    "those model/protocol gates run only after selected_target_size is frozen."
                )
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "optimizer_seed", seed)
        object.__setattr__(self, "completed_epochs", completed)
        object.__setattr__(self, "planned_epochs", planned)
        object.__setattr__(self, "optimizer_update_count", updates)
        object.__setattr__(self, "structures_presented", structures)
        object.__setattr__(self, "normalized_schedule_progress", progress)
        object.__setattr__(self, "instantaneous_learning_rate", lr)
        object.__setattr__(self, "wall_time_seconds", wall)
        object.__setattr__(self, "target_force_score_mev_per_a", score)
        object.__setattr__(
            self,
            "failure_reasons",
            tuple(sorted(set(str(v) for v in self.failure_reasons))),
        )

    @property
    def admissible_for_screening(self) -> bool:
        return bool(self.numerical_valid)

    @property
    def admissible_for_final_selection(self) -> bool:
        # MVQUAL is the sole hard target-size eligibility gate.  Epoch-30 model
        # acceptance (target thresholds, replay degradation, PES/relax/dynamics)
        # is deliberately downstream of the immutable size choice.  Only a
        # numerically invalid trajectory can be excluded from the ranking here.
        return bool(self.numerical_valid)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA,
            "stage": self.stage,
            "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed,
            "completed_epochs": self.completed_epochs,
            "planned_epochs": self.planned_epochs,
            "optimizer_update_count": self.optimizer_update_count,
            "structures_presented": self.structures_presented,
            "normalized_schedule_progress": self.normalized_schedule_progress,
            "instantaneous_learning_rate": self.instantaneous_learning_rate,
            "wall_time_seconds": self.wall_time_seconds,
            "target_force_score_mev_per_a": self.target_force_score_mev_per_a,
            "numerical_valid": self.numerical_valid,
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
            "failure_reasons": list(self.failure_reasons),
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
                "Historical target-size training evidence is stale under v5."
            )
        kwargs = dict(payload)
        kwargs.pop("schema", None)
        kwargs.pop("content_digest", None)
        kwargs["failure_reasons"] = tuple(
            str(v) for v in kwargs.get("failure_reasons", ())
        )
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size training evidence digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeStudyPlan:
    dataset_id: str
    repair2_authority_digest: str
    mvqual_authority_digest: str
    policy: TargetSizeStudyPolicy
    candidates: tuple[TargetSizeStudyCandidate, ...]
    qualified_sizes: tuple[int, ...]
    epoch3_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    epoch3_survivor_sizes: tuple[int, ...] = ()
    epoch10_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    epoch10_finalist_sizes: tuple[int, ...] = ()
    epoch30_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    selected_target_size: int | None = None
    outcome: str = OUTCOME_AWAITING_EPOCH_3
    decision_reason: str = (
        "qualified fixed target-size set frozen; awaiting epoch-3 TRAIN2 evidence"
    )
    comparison_failure_stage: str | None = None
    comparison_failures: tuple[tuple[int, int, tuple[str, ...]], ...] = ()
    authority_version: str = TARGET_SIZE_STUDY_VERSION
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError(
                "Target-size study dataset_id cannot be empty."
            )
        object.__setattr__(
            self,
            "repair2_authority_digest",
            validate_digest(
                self.repair2_authority_digest, name="repair2_authority_digest"
            ),
        )
        object.__setattr__(
            self,
            "mvqual_authority_digest",
            validate_digest(
                self.mvqual_authority_digest, name="mvqual_authority_digest"
            ),
        )
        if self.authority_version != TARGET_SIZE_STUDY_VERSION:
            raise TrainingDataInputError(
                "Unsupported target-size study authority version."
            )
        candidates = tuple(sorted(self.candidates, key=lambda v: v.target_size))
        qualified = tuple(v.target_size for v in candidates if v.qualified)
        e3 = tuple(self.epoch3_evidence)
        s3 = tuple(int(v) for v in self.epoch3_survivor_sizes)
        e10 = tuple(self.epoch10_evidence)
        s10 = tuple(int(v) for v in self.epoch10_finalist_sizes)
        e30 = tuple(self.epoch30_evidence)
        selected = None if self.selected_target_size is None else int(self.selected_target_size)
        failures = tuple(
            sorted(
                (
                    int(size),
                    int(seed),
                    tuple(sorted(set(str(reason) for reason in reasons))),
                )
                for size, seed, reasons in self.comparison_failures
            )
        )
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "qualified_sizes", tuple(int(v) for v in self.qualified_sizes))
        object.__setattr__(self, "epoch3_evidence", e3)
        object.__setattr__(self, "epoch3_survivor_sizes", s3)
        object.__setattr__(self, "epoch10_evidence", e10)
        object.__setattr__(self, "epoch10_finalist_sizes", s10)
        object.__setattr__(self, "epoch30_evidence", e30)
        object.__setattr__(self, "selected_target_size", selected)
        object.__setattr__(
            self,
            "comparison_failure_stage",
            None if self.comparison_failure_stage is None else str(self.comparison_failure_stage),
        )
        object.__setattr__(self, "comparison_failures", failures)
        if tuple(v.target_size for v in candidates) != FIXED_TARGET_SIZES:
            raise TrainingDataInputError(
                "Target-size study must record exactly the fixed eight candidates."
            )
        if tuple(int(v) for v in self.qualified_sizes) != qualified:
            raise TrainingDataInputError(
                "Target-size study qualified set must equal MVQUAL-qualified materializable candidates."
            )
        _validate_target_size_study_semantics(self)

    @property
    def candidate_authority_digest(self) -> str:
        """Stable identity of Q and its exact REPAIR2 prefix population."""
        return digest({
            "schema": TARGET_SIZE_CANDIDATE_AUTHORITY_SCHEMA,
            "dataset_id": self.dataset_id,
            "repair2_authority_digest": self.repair2_authority_digest,
            "mvqual_authority_digest": self.mvqual_authority_digest,
            "policy_digest": self.policy.policy_digest,
            "candidate_digests": [item.content_digest for item in self.candidates],
            "qualified_sizes": list(self.qualified_sizes),
        })

    @property
    def complete(self) -> bool:
        return self.outcome in _TERMINAL_OUTCOMES

    @property
    def next_training_sizes(self) -> tuple[int, ...]:
        if self.outcome == OUTCOME_AWAITING_EPOCH_3:
            return self.qualified_sizes
        if self.outcome == OUTCOME_AWAITING_EPOCH_10:
            return self.epoch3_survivor_sizes
        if self.outcome == OUTCOME_AWAITING_EPOCH_30:
            return self.epoch10_finalist_sizes
        return ()

    @property
    def next_training_epoch(self) -> int | None:
        return {
            OUTCOME_AWAITING_EPOCH_3: 3,
            OUTCOME_AWAITING_EPOCH_10: 10,
            OUTCOME_AWAITING_EPOCH_30: 30,
        }.get(self.outcome)

    def candidate(self, target_size: int) -> TargetSizeStudyCandidate:
        size = int(target_size)
        for item in self.candidates:
            if item.target_size == size:
                return item
        raise TrainingDataInputError(
            f"Target size n{size} is outside the fixed universe."
        )

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
            "epoch3_evidence": [v.to_dict() for v in self.epoch3_evidence],
            "epoch3_survivor_sizes": list(self.epoch3_survivor_sizes),
            "epoch10_evidence": [v.to_dict() for v in self.epoch10_evidence],
            "epoch10_finalist_sizes": list(self.epoch10_finalist_sizes),
            "epoch30_evidence": [v.to_dict() for v in self.epoch30_evidence],
            "selected_target_size": self.selected_target_size,
            "outcome": self.outcome,
            "decision_reason": self.decision_reason,
            "comparison_failure_stage": self.comparison_failure_stage,
            "comparison_failures": [
                [size, seed, list(reasons)]
                for size, seed, reasons in self.comparison_failures
            ],
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
        if payload.get("schema") != TARGET_SIZE_STUDY_PLAN_SCHEMA:
            raise TrainingDataSerializationError(
                "Historical target-size/ladder/migration/scalar-seed state is not restart-compatible with current target-size study v5."
            )
        if payload.get("authority_version") != TARGET_SIZE_STUDY_VERSION:
            raise TrainingDataSerializationError(
                "Target-size study schema/version generation mismatch."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            repair2_authority_digest=str(payload["repair2_authority_digest"]),
            mvqual_authority_digest=str(payload["mvqual_authority_digest"]),
            policy=TargetSizeStudyPolicy.from_dict(payload["policy"]),
            candidates=tuple(
                TargetSizeStudyCandidate.from_dict(v) for v in payload["candidates"]
            ),
            qualified_sizes=tuple(int(v) for v in payload["qualified_sizes"]),
            epoch3_evidence=tuple(
                TargetSizeTrainingEvidence.from_dict(v)
                for v in payload.get("epoch3_evidence", ())
            ),
            epoch3_survivor_sizes=tuple(
                int(v) for v in payload.get("epoch3_survivor_sizes", ())
            ),
            epoch10_evidence=tuple(
                TargetSizeTrainingEvidence.from_dict(v)
                for v in payload.get("epoch10_evidence", ())
            ),
            epoch10_finalist_sizes=tuple(
                int(v) for v in payload.get("epoch10_finalist_sizes", ())
            ),
            epoch30_evidence=tuple(
                TargetSizeTrainingEvidence.from_dict(v)
                for v in payload.get("epoch30_evidence", ())
            ),
            selected_target_size=(
                None
                if payload.get("selected_target_size") is None
                else int(payload["selected_target_size"])
            ),
            outcome=str(payload["outcome"]),
            decision_reason=str(payload.get("decision_reason", "")),
            comparison_failure_stage=(
                None
                if payload.get("comparison_failure_stage") is None
                else str(payload["comparison_failure_stage"])
            ),
            comparison_failures=tuple(
                (int(item[0]), int(item[1]), tuple(str(v) for v in item[2]))
                for item in payload.get("comparison_failures", ())
            ),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size study plan digest mismatch."
            )
        return result


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
        outcome=OUTCOME_AWAITING_EPOCH_3,
        decision_reason=(
            f"MVQUAL admitted {len(qualified)} fixed candidates; awaiting exact epoch-3 target-only evidence"
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


def _expected_evidence_keys(
    sizes: Sequence[int], seeds: Sequence[int]
) -> tuple[tuple[int, int], ...]:
    return tuple((int(size), int(seed)) for size in sizes for seed in seeds)


def _evidence_map(
    evidence: Sequence[TargetSizeTrainingEvidence],
) -> dict[tuple[int, int], TargetSizeTrainingEvidence]:
    result: dict[tuple[int, int], TargetSizeTrainingEvidence] = {}
    for item in evidence:
        key = (item.target_size, item.optimizer_seed)
        if key in result:
            raise TrainingDataInputError(
                f"Duplicate target-size evidence for n{item.target_size}, seed={item.optimizer_seed}."
            )
        result[key] = item
    return result


def _validate_batch_identity(
    plan: TargetSizeStudyPlan,
    evidence: Sequence[TargetSizeTrainingEvidence],
    expected_sizes: Sequence[int],
    epoch: int,
) -> dict[tuple[int, int], TargetSizeTrainingEvidence]:
    expected_keys = _expected_evidence_keys(
        expected_sizes, plan.policy.screening_optimizer_seeds
    )
    observed_keys = tuple(
        (item.target_size, item.optimizer_seed) for item in evidence
    )
    if observed_keys != expected_keys:
        raise TrainingDataInputError(
            f"Epoch-{epoch} evidence must preserve the exact ordered (size, seed) population; "
            f"expected={list(expected_keys)}, observed={list(observed_keys)}."
        )
    by_key = _evidence_map(evidence)
    stage = _STAGE_FOR_EPOCH[epoch]
    for size, seed in expected_keys:
        item = by_key[(size, seed)]
        if (
            item.stage != stage
            or item.completed_epochs != epoch
            or item.planned_epochs != 30
        ):
            raise TrainingDataInputError(
                f"n{size}, seed={seed} evidence is not the exact {epoch}-of-30 TRAIN2 endpoint."
            )
        if item.candidate_data_digest != plan.candidate(size).candidate_data_digest:
            raise TrainingDataInputError(
                f"n{size}, seed={seed} TRAIN2 evidence does not use the authenticated REPAIR2 prefix."
            )
        if item.target_size_study_policy_digest != plan.policy.policy_digest:
            raise TrainingDataInputError(
                f"n{size}, seed={seed} TRAIN2 evidence belongs to a different target-size study policy."
            )
    for attr in (
        "foundation_identity_digest",
        "evaluation_role_digest",
        "training_policy_digest",
        "schedule_digest",
    ):
        if len({getattr(v, attr) for v in by_key.values()}) != 1:
            raise TrainingDataInputError(
                f"Target-size candidates do not share {attr}."
            )
    return by_key


def _validate_continuation(
    parent: TargetSizeTrainingEvidence,
    child: TargetSizeTrainingEvidence,
) -> None:
    if child.target_size != parent.target_size or child.optimizer_seed != parent.optimizer_seed:
        raise TrainingDataInputError(
            "Target-size continuation changed candidate or optimizer-seed identity."
        )
    if child.parent_checkpoint_digest != parent.checkpoint_digest:
        raise TrainingDataInputError(
            f"n{child.target_size}, seed={child.optimizer_seed} continuation checkpoint ancestry changed."
        )
    if child.parent_optimizer_state_digest != parent.optimizer_state_digest:
        raise TrainingDataInputError(
            f"n{child.target_size}, seed={child.optimizer_seed} continuation optimizer ancestry changed."
        )
    if child.parent_rng_state_digest != parent.rng_state_digest:
        raise TrainingDataInputError(
            f"n{child.target_size}, seed={child.optimizer_seed} continuation RNG ancestry changed."
        )
    for attr in (
        "foundation_identity_digest",
        "evaluation_role_digest",
        "training_policy_digest",
        "target_size_study_policy_digest",
        "training_run_digest",
        "schedule_digest",
        "candidate_data_digest",
    ):
        if getattr(child, attr) != getattr(parent, attr):
            raise TrainingDataInputError(
                f"n{child.target_size}, seed={child.optimizer_seed} continuation changed {attr}."
            )


def _paired_candidate_scores(
    plan: TargetSizeStudyPlan,
    by_key: Mapping[tuple[int, int], TargetSizeTrainingEvidence],
    sizes: Sequence[int],
    *,
    final: bool = False,
) -> dict[int, float]:
    """Return comparable arithmetic means over the exact common ordered seed set."""

    result: dict[int, float] = {}
    for size in sizes:
        items = [
            by_key[(int(size), seed)]
            for seed in plan.policy.screening_optimizer_seeds
        ]
        admissible = (
            all(item.admissible_for_final_selection for item in items)
            if final
            else all(item.admissible_for_screening for item in items)
        )
        if not admissible:
            continue
        result[int(size)] = sum(
            item.target_force_score_mev_per_a for item in items
        ) / float(len(items))
    return result


def _comparison_failures(
    plan: TargetSizeStudyPlan,
    by_key: Mapping[tuple[int, int], TargetSizeTrainingEvidence],
    sizes: Sequence[int],
) -> tuple[tuple[int, int, tuple[str, ...]], ...]:
    failures: list[tuple[int, int, tuple[str, ...]]] = []
    for size, seed in _expected_evidence_keys(
        sizes, plan.policy.screening_optimizer_seeds
    ):
        item = by_key[(size, seed)]
        if item.numerical_valid:
            continue
        reasons = item.failure_reasons or ("numerical_invalid",)
        failures.append((size, seed, tuple(sorted(set(reasons)))))
    return tuple(failures)


def _equivalence_aware_score_order(
    scores: Mapping[int, float], *, epsilon: float
) -> tuple[int, ...]:
    remaining = sorted(scores, key=lambda size: (scores[size], size))
    ordered: list[int] = []
    while remaining:
        anchor = scores[remaining[0]]
        band = [
            size
            for size in remaining
            if scores[size] <= anchor + float(epsilon) + 1.0e-12
        ]
        band.sort()
        ordered.extend(band)
        band_set = set(band)
        remaining = [size for size in remaining if size not in band_set]
    return tuple(ordered)


def _equivalence_aware_target_order(
    evidence: Sequence[TargetSizeTrainingEvidence],
    *,
    epsilon: float,
) -> tuple[int, ...]:
    """Compatibility helper for single-evidence synthetic/performance callers."""

    scores: dict[int, float] = {}
    for item in evidence:
        if item.target_size in scores:
            raise TrainingDataInputError(
                "Direct equivalence ordering accepts one score per target size."
            )
        scores[item.target_size] = item.target_force_score_mev_per_a
    return _equivalence_aware_score_order(scores, epsilon=epsilon)


def _validate_target_size_study_semantics(plan: TargetSizeStudyPlan) -> None:
    """Canonical semantic validator for construction, transition, and restart."""

    qualified = plan.qualified_sizes
    q = len(qualified)
    allowed = {
        OUTCOME_INSUFFICIENT_QUALIFIED_SIZES,
        OUTCOME_AWAITING_EPOCH_3,
        OUTCOME_AWAITING_EPOCH_10,
        OUTCOME_AWAITING_EPOCH_30,
        OUTCOME_SELECTED,
        OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
        OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
    }
    if plan.outcome not in allowed:
        raise TrainingDataInputError("Unsupported target-size study outcome.")
    if q < plan.policy.minimum_qualified_sizes:
        if (
            plan.outcome != OUTCOME_INSUFFICIENT_QUALIFIED_SIZES
            or plan.epoch3_evidence
            or plan.epoch3_survivor_sizes
            or plan.epoch10_evidence
            or plan.epoch10_finalist_sizes
            or plan.epoch30_evidence
            or plan.selected_target_size is not None
            or plan.comparison_failure_stage is not None
            or plan.comparison_failures
        ):
            raise TrainingDataInputError(
                "Sub-threshold qualified set must terminate as insufficient_qualified_sizes."
            )
        return
    if plan.outcome == OUTCOME_INSUFFICIENT_QUALIFIED_SIZES:
        raise TrainingDataInputError(
            "Qualified set meets the minimum; insufficient_qualified_sizes is inconsistent."
        )

    if not plan.epoch3_evidence:
        if (
            plan.outcome != OUTCOME_AWAITING_EPOCH_3
            or plan.epoch3_survivor_sizes
            or plan.epoch10_evidence
            or plan.epoch10_finalist_sizes
            or plan.epoch30_evidence
            or plan.selected_target_size is not None
            or plan.comparison_failure_stage is not None
            or plan.comparison_failures
        ):
            raise TrainingDataInputError("Epoch-3 wait state is inconsistent.")
        return

    e3 = _validate_batch_identity(plan, plan.epoch3_evidence, qualified, 3)
    scores3 = _paired_candidate_scores(plan, e3, qualified)
    required3 = min(q, plan.policy.epoch3_survivor_limit)
    if len(scores3) < required3:
        expected_failures = _comparison_failures(plan, e3, qualified)
        if (
            plan.outcome != OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES
            or plan.comparison_failure_stage != "coarse"
            or plan.comparison_failures != expected_failures
            or plan.epoch3_survivor_sizes
            or plan.epoch10_evidence
            or plan.epoch10_finalist_sizes
            or plan.epoch30_evidence
            or plan.selected_target_size is not None
        ):
            raise TrainingDataInputError(
                "Epoch-3 insufficient-comparable terminal state is inconsistent."
            )
        return
    expected_s3 = _equivalence_aware_score_order(
        scores3, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a
    )[:required3]
    if plan.epoch3_survivor_sizes != expected_s3:
        raise TrainingDataInputError(
            "Epoch-3 survivor decision does not match paired aggregate/equivalence policy."
        )
    if not plan.epoch10_evidence:
        if (
            plan.outcome != OUTCOME_AWAITING_EPOCH_10
            or plan.epoch10_finalist_sizes
            or plan.epoch30_evidence
            or plan.selected_target_size is not None
            or plan.comparison_failure_stage is not None
            or plan.comparison_failures
        ):
            raise TrainingDataInputError("Epoch-10 wait state is inconsistent.")
        return

    e10 = _validate_batch_identity(
        plan, plan.epoch10_evidence, plan.epoch3_survivor_sizes, 10
    )
    for key, child in e10.items():
        _validate_continuation(e3[key], child)
    scores10 = _paired_candidate_scores(plan, e10, plan.epoch3_survivor_sizes)
    if len(scores10) < plan.policy.epoch10_finalist_count:
        expected_failures = _comparison_failures(
            plan, e10, plan.epoch3_survivor_sizes
        )
        if (
            plan.outcome != OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES
            or plan.comparison_failure_stage != "short"
            or plan.comparison_failures != expected_failures
            or plan.epoch10_finalist_sizes
            or plan.epoch30_evidence
            or plan.selected_target_size is not None
        ):
            raise TrainingDataInputError(
                "Epoch-10 insufficient-comparable terminal state is inconsistent."
            )
        return
    expected_s10 = _equivalence_aware_score_order(
        scores10, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a
    )[: plan.policy.epoch10_finalist_count]
    if plan.epoch10_finalist_sizes != expected_s10:
        raise TrainingDataInputError(
            "Epoch-10 finalist decision does not match paired aggregate/equivalence policy."
        )
    if not plan.epoch30_evidence:
        if (
            plan.outcome != OUTCOME_AWAITING_EPOCH_30
            or plan.selected_target_size is not None
            or plan.comparison_failure_stage is not None
            or plan.comparison_failures
        ):
            raise TrainingDataInputError("Epoch-30 wait state is inconsistent.")
        return

    e30 = _validate_batch_identity(
        plan, plan.epoch30_evidence, plan.epoch10_finalist_sizes, 30
    )
    for key, child in e30.items():
        _validate_continuation(e10[key], child)
    scores30 = _paired_candidate_scores(
        plan, e30, plan.epoch10_finalist_sizes, final=True
    )
    if len(scores30) < plan.policy.epoch10_finalist_count:
        expected_failures = _comparison_failures(
            plan, e30, plan.epoch10_finalist_sizes
        )
        if (
            plan.outcome != OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES
            or plan.comparison_failure_stage != "final"
            or plan.comparison_failures != expected_failures
            or plan.selected_target_size is not None
        ):
            raise TrainingDataInputError(
                "Epoch-30 insufficient-comparable terminal state is inconsistent."
            )
        return

    ranking = _equivalence_aware_score_order(
        scores30, epsilon=plan.policy.practical_equivalence_mev_per_a
    )
    winner = ranking[0]
    if winner == FIXED_TARGET_SIZE_CEILING:
        smaller = [size for size in scores30 if size < winner]
        ceiling_superior = bool(smaller) and all(
            scores30[size] - scores30[winner]
            > plan.policy.practical_equivalence_mev_per_a + 1.0e-12
            for size in smaller
        )
        if ceiling_superior:
            if (
                plan.outcome != OUTCOME_NONCONVERGED_AT_FIXED_CEILING
                or plan.selected_target_size is not None
                or plan.comparison_failure_stage is not None
                or plan.comparison_failures
            ):
                raise TrainingDataInputError(
                    "Fixed-ceiling terminal state does not match final paired comparison."
                )
            return
    if (
        plan.outcome != OUTCOME_SELECTED
        or plan.selected_target_size != winner
        or plan.comparison_failure_stage is not None
        or plan.comparison_failures
    ):
        raise TrainingDataInputError(
            "Selected target size does not match final paired aggregate/equivalence policy."
        )


def _insufficient_comparable_result(
    plan: TargetSizeStudyPlan,
    *,
    stage: str,
    evidence_field: str,
    evidence: Sequence[TargetSizeTrainingEvidence],
    by_key: Mapping[tuple[int, int], TargetSizeTrainingEvidence],
    sizes: Sequence[int],
) -> TargetSizeStudyPlan:
    return replace(
        plan,
        **{evidence_field: tuple(evidence)},
        selected_target_size=None,
        outcome=OUTCOME_INSUFFICIENT_COMPARABLE_CANDIDATES,
        comparison_failure_stage=stage,
        comparison_failures=_comparison_failures(plan, by_key, sizes),
        decision_reason=(
            f"{stage} target-size comparison has too few numerically valid paired candidates"
        ),
    )


def attach_epoch_3_evidence(
    plan: TargetSizeStudyPlan,
    evidence: Sequence[TargetSizeTrainingEvidence],
) -> TargetSizeStudyPlan:
    if plan.outcome != OUTCOME_AWAITING_EPOCH_3:
        raise TrainingDataInputError(
            "Epoch-3 evidence can only be attached while awaiting epoch 3."
        )
    evidence = tuple(evidence)
    by_key = _validate_batch_identity(plan, evidence, plan.qualified_sizes, 3)
    scores = _paired_candidate_scores(plan, by_key, plan.qualified_sizes)
    required = min(len(plan.qualified_sizes), plan.policy.epoch3_survivor_limit)
    if len(scores) < required:
        return _insufficient_comparable_result(
            plan,
            stage="coarse",
            evidence_field="epoch3_evidence",
            evidence=evidence,
            by_key=by_key,
            sizes=plan.qualified_sizes,
        )
    survivors = _equivalence_aware_score_order(
        scores, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a
    )[:required]
    return replace(
        plan,
        epoch3_evidence=evidence,
        epoch3_survivor_sizes=survivors,
        outcome=OUTCOME_AWAITING_EPOCH_10,
        decision_reason=(
            "epoch-3 paired target-only screen retained "
            + ", ".join(f"n{v}" for v in survivors)
        ),
    )


def attach_epoch_10_evidence(
    plan: TargetSizeStudyPlan,
    evidence: Sequence[TargetSizeTrainingEvidence],
) -> TargetSizeStudyPlan:
    if plan.outcome != OUTCOME_AWAITING_EPOCH_10:
        raise TrainingDataInputError(
            "Epoch-10 evidence can only be attached while awaiting epoch 10."
        )
    evidence = tuple(evidence)
    by_key = _validate_batch_identity(
        plan, evidence, plan.epoch3_survivor_sizes, 10
    )
    parents = _evidence_map(plan.epoch3_evidence)
    for key, item in by_key.items():
        _validate_continuation(parents[key], item)
    scores = _paired_candidate_scores(plan, by_key, plan.epoch3_survivor_sizes)
    if len(scores) < plan.policy.epoch10_finalist_count:
        return _insufficient_comparable_result(
            plan,
            stage="short",
            evidence_field="epoch10_evidence",
            evidence=evidence,
            by_key=by_key,
            sizes=plan.epoch3_survivor_sizes,
        )
    finalists = _equivalence_aware_score_order(
        scores, epsilon=plan.policy.coarse_practical_equivalence_mev_per_a
    )[: plan.policy.epoch10_finalist_count]
    return replace(
        plan,
        epoch10_evidence=evidence,
        epoch10_finalist_sizes=finalists,
        outcome=OUTCOME_AWAITING_EPOCH_30,
        decision_reason=(
            "epoch-10 paired target-only screen retained "
            + ", ".join(f"n{v}" for v in finalists)
        ),
    )


def attach_epoch_30_evidence(
    plan: TargetSizeStudyPlan,
    evidence: Sequence[TargetSizeTrainingEvidence],
) -> TargetSizeStudyPlan:
    if plan.outcome != OUTCOME_AWAITING_EPOCH_30:
        raise TrainingDataInputError(
            "Epoch-30 evidence can only be attached while awaiting epoch 30."
        )
    evidence = tuple(evidence)
    by_key = _validate_batch_identity(
        plan, evidence, plan.epoch10_finalist_sizes, 30
    )
    parents = _evidence_map(plan.epoch10_evidence)
    for key, item in by_key.items():
        _validate_continuation(parents[key], item)
    scores = _paired_candidate_scores(
        plan, by_key, plan.epoch10_finalist_sizes, final=True
    )
    if len(scores) < plan.policy.epoch10_finalist_count:
        return _insufficient_comparable_result(
            plan,
            stage="final",
            evidence_field="epoch30_evidence",
            evidence=evidence,
            by_key=by_key,
            sizes=plan.epoch10_finalist_sizes,
        )
    ranking = _equivalence_aware_score_order(
        scores, epsilon=plan.policy.practical_equivalence_mev_per_a
    )
    winner = ranking[0]
    if winner == FIXED_TARGET_SIZE_CEILING:
        smaller = [size for size in scores if size < winner]
        if smaller and all(
            scores[size] - scores[winner]
            > plan.policy.practical_equivalence_mev_per_a + 1.0e-12
            for size in smaller
        ):
            improvement = min(scores[size] - scores[winner] for size in smaller)
            return replace(
                plan,
                epoch30_evidence=evidence,
                selected_target_size=None,
                outcome=OUTCOME_NONCONVERGED_AT_FIXED_CEILING,
                decision_reason=(
                    f"n16384 improves paired target force score by at least {improvement:.6g} meV/A beyond practical equivalence; "
                    "the fixed ceiling is exhausted and rescue above 16384 is forbidden"
                ),
            )
    return replace(
        plan,
        epoch30_evidence=evidence,
        selected_target_size=winner,
        outcome=OUTCOME_SELECTED,
        decision_reason=(
            f"epoch-30 paired comparison selected n{winner}; target size is immutable before held-out validation"
        ),
    )
