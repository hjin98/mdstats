"""TARGET-DATA2D hard-coverage + 3/10/30 successive-fidelity size authority.

Coverage is an admissibility gate only.  Every coverage-qualified target-size
rung enters a coarse three-epoch learning screen.  The exact uninterrupted
TRAIN2 trajectory is then reduced 7 -> <=4 at epoch 3, <=4 -> 2 at epoch 10,
and 2 -> 1 at epoch 30.  Replay has zero ranking credit throughout and becomes
a hard admissibility guard only at the final 30-epoch stage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .target_ladder import TARGET_DATA_LADDER_VERSION, TARGET_DATA_LADDER_MV_VERSION, TargetDataLadderPlan

TARGET_SIZE_CONVERGENCE_POLICY_SCHEMA = "mdstats.target-size-convergence-policy.v2"
TARGET_SIZE_CONVERGENCE_POLICY_V1_SCHEMA = "mdstats.target-size-convergence-policy.v1"
TARGET_SIZE_STAGE_A_RUNG_SCHEMA = "mdstats.target-size-stage-a-rung.v1"
TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA = "mdstats.target-size-training-evidence.v3"
TARGET_SIZE_CONVERGENCE_PLAN_SCHEMA = "mdstats.target-size-convergence-plan.v2"
TARGET_SIZE_CONVERGENCE_MV_POLICY_SCHEMA = "mdstats.target-size-convergence-policy.v3"
TARGET_SIZE_CONVERGENCE_MV_PLAN_SCHEMA = "mdstats.target-size-convergence-plan.v3"
TARGET_SIZE_CONVERGENCE_VERSION = "mdstats.target-data2d.size-convergence.2026-08.v2"
TARGET_SIZE_CONVERGENCE_MV_VERSION = "mdstats.target-data2d.size-convergence.2026-08.v3"

_WAIT_COARSE = "awaiting_stage_b0_coarse_training"
_WAIT_SHORT = "awaiting_stage_b1_short_training"
_WAIT_FINAL = "awaiting_stage_c_full_training"
_SELECTED = "selected"
_NONCONVERGED = "nonconverged_at_ladder_boundary"
_FAILED = "failed"


class TargetDataCoverageError(TrainingDataInputError):
    """TARGET-DATA2D hard-coverage/data-adequacy failure."""


@dataclass(frozen=True, slots=True)
class TargetSizeConvergencePolicy:
    """Frozen 3/10/30 target-size successive-fidelity policy."""

    min_coverage_qualifiers: int = 3
    coarse_training_epochs: int = 3
    max_coarse_training_candidates: int = 4
    coarse_target_monitor_configurations: int = 256
    short_training_epochs: int = 10
    max_short_training_candidates: int = 2
    final_training_epochs: int = 30
    practical_equivalence_mev_per_a: float = 1.0
    coarse_practical_equivalence_mev_per_a: float | None = None
    screening_optimizer_seed: int = 1
    policy_version: str = TARGET_SIZE_CONVERGENCE_VERSION

    def __post_init__(self) -> None:
        minimum = int(self.min_coverage_qualifiers)
        coarse_epochs = int(self.coarse_training_epochs)
        coarse_max = int(self.max_coarse_training_candidates)
        coarse_monitor = int(self.coarse_target_monitor_configurations)
        short_epochs = int(self.short_training_epochs)
        short_max = int(self.max_short_training_candidates)
        final_epochs = int(self.final_training_epochs)
        epsilon = float(self.practical_equivalence_mev_per_a)
        coarse_epsilon = epsilon if self.coarse_practical_equivalence_mev_per_a is None else float(self.coarse_practical_equivalence_mev_per_a)
        seed = int(self.screening_optimizer_seed)
        if minimum < 3:
            raise TrainingDataInputError("TARGET-DATA2D min_coverage_qualifiers must be at least three.")
        if not (0 < coarse_epochs < short_epochs < final_epochs):
            raise TrainingDataInputError("TARGET-DATA2D requires 0 < coarse_training_epochs < short_training_epochs < final_training_epochs.")
        if coarse_max < 2 or coarse_max < short_max:
            raise TrainingDataInputError("TARGET-DATA2D max_coarse_training_candidates must be >= max_short_training_candidates and >= 2.")
        if coarse_monitor <= 0:
            raise TrainingDataInputError("TARGET-DATA2D coarse_target_monitor_configurations must be positive.")
        if short_max != 2:
            raise TrainingDataInputError("TARGET-DATA2D currently requires exactly two 10-epoch finalists.")
        if not math.isfinite(epsilon) or epsilon <= 0.0 or not math.isfinite(coarse_epsilon) or coarse_epsilon <= 0.0:
            raise TrainingDataInputError("TARGET-DATA2D practical-equivalence widths must be positive and finite.")
        if seed < 0:
            raise TrainingDataInputError("TARGET-DATA2D screening_optimizer_seed must be nonnegative.")
        if self.policy_version not in {TARGET_SIZE_CONVERGENCE_VERSION, TARGET_SIZE_CONVERGENCE_MV_VERSION}:
            raise TrainingDataInputError("Unsupported TARGET-DATA2D policy version.")
        if self.policy_version == TARGET_SIZE_CONVERGENCE_MV_VERSION and minimum != 4:
            raise TrainingDataInputError("Migrated TARGET-DATA2D v3 freezes min_coverage_qualifiers at four.")
        object.__setattr__(self, "min_coverage_qualifiers", minimum)
        object.__setattr__(self, "coarse_training_epochs", coarse_epochs)
        object.__setattr__(self, "max_coarse_training_candidates", coarse_max)
        object.__setattr__(self, "coarse_target_monitor_configurations", coarse_monitor)
        object.__setattr__(self, "short_training_epochs", short_epochs)
        object.__setattr__(self, "max_short_training_candidates", short_max)
        object.__setattr__(self, "final_training_epochs", final_epochs)
        object.__setattr__(self, "practical_equivalence_mev_per_a", epsilon)
        object.__setattr__(self, "coarse_practical_equivalence_mev_per_a", coarse_epsilon)
        object.__setattr__(self, "screening_optimizer_seed", seed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (TARGET_SIZE_CONVERGENCE_MV_POLICY_SCHEMA if self.policy_version == TARGET_SIZE_CONVERGENCE_MV_VERSION else TARGET_SIZE_CONVERGENCE_POLICY_SCHEMA),
            "policy_version": self.policy_version,
            "min_coverage_qualifiers": self.min_coverage_qualifiers,
            "coarse_training_epochs": self.coarse_training_epochs,
            "max_coarse_training_candidates": self.max_coarse_training_candidates,
            "coarse_target_monitor_configurations": self.coarse_target_monitor_configurations,
            "short_training_epochs": self.short_training_epochs,
            "max_short_training_candidates": self.max_short_training_candidates,
            "final_training_epochs": self.final_training_epochs,
            "practical_equivalence_mev_per_a": self.practical_equivalence_mev_per_a,
            "coarse_practical_equivalence_mev_per_a": self.coarse_practical_equivalence_mev_per_a,
            "screening_optimizer_seed": self.screening_optimizer_seed,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeConvergencePolicy":
        schema = payload.get("schema")
        if schema not in {TARGET_SIZE_CONVERGENCE_POLICY_SCHEMA, TARGET_SIZE_CONVERGENCE_MV_POLICY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2D policy schema.")
        expected_version = TARGET_SIZE_CONVERGENCE_MV_VERSION if schema == TARGET_SIZE_CONVERGENCE_MV_POLICY_SCHEMA else TARGET_SIZE_CONVERGENCE_VERSION
        if str(payload.get("policy_version")) != expected_version:
            raise TrainingDataSerializationError("TARGET-DATA2D policy schema/version generation mismatch.")
        result = cls(
            min_coverage_qualifiers=int(payload["min_coverage_qualifiers"]),
            coarse_training_epochs=int(payload["coarse_training_epochs"]),
            max_coarse_training_candidates=int(payload["max_coarse_training_candidates"]),
            coarse_target_monitor_configurations=int(payload["coarse_target_monitor_configurations"]),
            short_training_epochs=int(payload["short_training_epochs"]),
            max_short_training_candidates=int(payload["max_short_training_candidates"]),
            final_training_epochs=int(payload["final_training_epochs"]),
            practical_equivalence_mev_per_a=float(payload["practical_equivalence_mev_per_a"]),
            coarse_practical_equivalence_mev_per_a=float(payload["coarse_practical_equivalence_mev_per_a"]),
            screening_optimizer_seed=int(payload.get("screening_optimizer_seed", 1)),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("TARGET-DATA2D policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeStageARung:
    """Global hard-coverage qualification for one common target size."""

    target_size: int
    materializable: bool
    qualified: bool
    domain_coverage_passed: tuple[tuple[str, bool], ...]
    domain_mandatory_passed: tuple[tuple[str, bool], ...]
    coverage_report_digests: tuple[tuple[str, str], ...]
    failure_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size <= 0:
            raise TrainingDataInputError("TARGET-DATA2D target_size must be positive.")
        coverage = tuple(sorted((str(k), bool(v)) for k, v in self.domain_coverage_passed))
        mandatory = tuple(sorted((str(k), bool(v)) for k, v in self.domain_mandatory_passed))
        reports = tuple(sorted((str(k), validate_digest(v, name="coverage_report_digest")) for k, v in self.coverage_report_digests))
        domains = tuple(k for k, _ in coverage)
        if not domains or domains != tuple(k for k, _ in mandatory) or domains != tuple(k for k, _ in reports):
            raise TrainingDataInputError("TARGET-DATA2D hard-coverage evidence is incomplete or misaligned.")
        expected = bool(self.materializable and all(v for _, v in coverage) and all(v for _, v in mandatory))
        if bool(self.qualified) != expected:
            raise TrainingDataInputError("TARGET-DATA2D qualified flag contradicts hard-coverage evidence.")
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "domain_coverage_passed", coverage)
        object.__setattr__(self, "domain_mandatory_passed", mandatory)
        object.__setattr__(self, "coverage_report_digests", reports)
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(str(v) for v in self.failure_reasons))))

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": TARGET_SIZE_STAGE_A_RUNG_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "qualified": self.qualified,
            "domain_coverage_passed": [list(v) for v in self.domain_coverage_passed],
            "domain_mandatory_passed": [list(v) for v in self.domain_mandatory_passed],
            "coverage_report_digests": [list(v) for v in self.coverage_report_digests],
            "failure_reasons": list(self.failure_reasons),
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeStageARung":
        if payload.get("schema") != TARGET_SIZE_STAGE_A_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2D Stage-A rung schema.")
        result = cls(
            target_size=int(payload["target_size"]), materializable=bool(payload["materializable"]), qualified=bool(payload["qualified"]),
            domain_coverage_passed=tuple((str(v[0]), bool(v[1])) for v in payload["domain_coverage_passed"]),
            domain_mandatory_passed=tuple((str(v[0]), bool(v[1])) for v in payload["domain_mandatory_passed"]),
            coverage_report_digests=tuple((str(v[0]), str(v[1])) for v in payload["coverage_report_digests"]),
            failure_reasons=tuple(str(v) for v in payload.get("failure_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("TARGET-DATA2D Stage-A rung digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeTrainingEvidence:
    """Authenticated exact endpoint evidence for the 3/10/30 size funnel."""

    stage: str  # coarse | short | final
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
    target_hard_gates_passed: bool
    foundation_identity_digest: str
    evaluation_role_digest: str
    training_policy_digest: str
    training_run_digest: str
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
            raise TrainingDataInputError("TARGET-DATA2D training evidence stage must be coarse, short, or final.")
        size, seed = int(self.target_size), int(self.optimizer_seed)
        completed, planned = int(self.completed_epochs), int(self.planned_epochs)
        updates, structures = int(self.optimizer_update_count), int(self.structures_presented)
        progress, lr, wall, score = map(float, (self.normalized_schedule_progress, self.instantaneous_learning_rate, self.wall_time_seconds, self.target_force_score_mev_per_a))
        if size <= 0 or seed < 0 or completed <= 0 or planned < completed or updates <= 0 or structures <= 0:
            raise TrainingDataInputError("TARGET-DATA2D training-evidence counts are invalid.")
        if not math.isfinite(progress) or not 0.0 <= progress <= 1.0 or not math.isfinite(lr) or lr <= 0.0 or not math.isfinite(wall) or wall < 0.0:
            raise TrainingDataInputError("TARGET-DATA2D schedule/wall evidence is invalid.")
        if not math.isfinite(score) or score < 0.0:
            raise TrainingDataInputError("TARGET-DATA2D target force score must be finite and nonnegative.")
        for name in ("foundation_identity_digest", "evaluation_role_digest", "training_policy_digest", "training_run_digest", "checkpoint_digest", "schedule_digest", "optimizer_state_digest", "rng_state_digest", "target_evaluation_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("replay_evaluation_digest", "physical_qualification_digest", "parent_checkpoint_digest", "parent_optimizer_state_digest", "parent_rng_state_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.replay_diagnostic_force_rmse_mev_per_a is not None:
            replay = float(self.replay_diagnostic_force_rmse_mev_per_a)
            if not math.isfinite(replay) or replay < 0.0:
                raise TrainingDataInputError("TARGET-DATA2D replay diagnostic must be finite and nonnegative.")
            object.__setattr__(self, "replay_diagnostic_force_rmse_mev_per_a", replay)
        parents = (self.parent_checkpoint_digest, self.parent_optimizer_state_digest, self.parent_rng_state_digest)
        if stage == "coarse":
            if any(v is not None for v in parents):
                raise TrainingDataInputError("TARGET-DATA2D coarse evidence cannot claim a continuation parent.")
            if self.replay_diagnostic_force_rmse_mev_per_a is not None or self.replay_evaluation_digest is not None or self.replay_admissible is not None or self.physical_qualification_passed is not None or self.physical_qualification_digest is not None:
                raise TrainingDataInputError("TARGET-DATA2D coarse evidence is target-only and cannot carry replay/physical authority.")
            if not (0.0 < progress < 1.0):
                raise TrainingDataInputError("TARGET-DATA2D coarse schedule progress must be inside the full horizon.")
        elif stage == "short":
            if any(v is None for v in parents):
                raise TrainingDataInputError("TARGET-DATA2D short evidence requires exact epoch-3 checkpoint/optimizer/RNG ancestry.")
            if self.replay_admissible is not None or self.physical_qualification_passed is not None or self.physical_qualification_digest is not None:
                raise TrainingDataInputError("TARGET-DATA2D short evidence cannot carry final replay/physical pass authority.")
            if (self.replay_diagnostic_force_rmse_mev_per_a is None) != (self.replay_evaluation_digest is None):
                raise TrainingDataInputError("TARGET-DATA2D short replay diagnostics require both value and evaluation digest.")
            if not (0.0 < progress < 1.0):
                raise TrainingDataInputError("TARGET-DATA2D short schedule progress must be inside the full horizon.")
        else:
            if any(v is None for v in parents):
                raise TrainingDataInputError("TARGET-DATA2D final evidence requires exact epoch-10 checkpoint/optimizer/RNG ancestry.")
            if abs(progress - 1.0) > 1.0e-12:
                raise TrainingDataInputError("TARGET-DATA2D final schedule progress must be exactly complete.")
            if self.replay_admissible is None or self.replay_evaluation_digest is None or self.physical_qualification_passed is None or self.physical_qualification_digest is None:
                raise TrainingDataInputError("TARGET-DATA2D final evidence requires replay and physical qualification authority.")
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
        object.__setattr__(self, "failure_reasons", tuple(sorted(set(str(v) for v in self.failure_reasons))))

    @property
    def admissible_for_screening(self) -> bool:
        return bool(self.numerical_valid)

    @property
    def admissible_for_stage_c(self) -> bool:
        return bool(self.numerical_valid and self.target_hard_gates_passed and self.replay_admissible and self.physical_qualification_passed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA, "stage": self.stage, "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed, "completed_epochs": self.completed_epochs, "planned_epochs": self.planned_epochs,
            "optimizer_update_count": self.optimizer_update_count, "structures_presented": self.structures_presented,
            "normalized_schedule_progress": self.normalized_schedule_progress, "instantaneous_learning_rate": self.instantaneous_learning_rate,
            "wall_time_seconds": self.wall_time_seconds, "target_force_score_mev_per_a": self.target_force_score_mev_per_a,
            "numerical_valid": self.numerical_valid, "target_hard_gates_passed": self.target_hard_gates_passed,
            "foundation_identity_digest": self.foundation_identity_digest, "evaluation_role_digest": self.evaluation_role_digest,
            "training_policy_digest": self.training_policy_digest, "training_run_digest": self.training_run_digest,
            "checkpoint_digest": self.checkpoint_digest, "schedule_digest": self.schedule_digest,
            "optimizer_state_digest": self.optimizer_state_digest, "rng_state_digest": self.rng_state_digest,
            "target_evaluation_digest": self.target_evaluation_digest,
            "replay_diagnostic_force_rmse_mev_per_a": self.replay_diagnostic_force_rmse_mev_per_a,
            "replay_evaluation_digest": self.replay_evaluation_digest, "replay_admissible": self.replay_admissible,
            "physical_qualification_passed": self.physical_qualification_passed, "physical_qualification_digest": self.physical_qualification_digest,
            "parent_checkpoint_digest": self.parent_checkpoint_digest, "parent_optimizer_state_digest": self.parent_optimizer_state_digest,
            "parent_rng_state_digest": self.parent_rng_state_digest, "failure_reasons": list(self.failure_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeTrainingEvidence":
        if payload.get("schema") != TARGET_SIZE_TRAINING_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Historical TARGET-DATA2D training evidence is stale under the 3/10/30 correction.")
        kwargs = dict(payload)
        kwargs.pop("schema", None); kwargs.pop("content_digest", None)
        if "failure_reasons" in kwargs:
            kwargs["failure_reasons"] = tuple(str(v) for v in kwargs["failure_reasons"])
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2D training-evidence digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeConvergencePlan:
    dataset_id: str
    target_data_ladder_digest: str
    policy: TargetSizeConvergencePolicy
    stage_a_rungs: tuple[TargetSizeStageARung, ...]
    stage_a_survivor_sizes: tuple[int, ...]  # all hard-coverage-qualified rungs
    coarse_training_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    stage_b_survivor_sizes: tuple[int, ...] = ()  # <=4 after epoch 3
    short_training_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    stage_b_finalist_sizes: tuple[int, ...] = ()  # exactly 2 after epoch 10
    final_training_evidence: tuple[TargetSizeTrainingEvidence, ...] = ()
    selected_target_size: int | None = None
    outcome: str = _WAIT_COARSE
    decision_reason: str = "hard coverage qualified; awaiting exact 3-epoch TRAIN2 evidence"
    authority_version: str = TARGET_SIZE_CONVERGENCE_VERSION
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not str(self.dataset_id).strip():
            raise TrainingDataInputError("TARGET-DATA2D dataset_id must be non-empty.")
        object.__setattr__(self, "target_data_ladder_digest", validate_digest(self.target_data_ladder_digest, name="target_data_ladder_digest"))
        if self.authority_version not in {TARGET_SIZE_CONVERGENCE_VERSION, TARGET_SIZE_CONVERGENCE_MV_VERSION}:
            raise TrainingDataInputError("Unsupported TARGET-DATA2D authority version.")
        if self.authority_version == TARGET_SIZE_CONVERGENCE_MV_VERSION:
            if self.policy.policy_version != TARGET_SIZE_CONVERGENCE_MV_VERSION:
                raise TrainingDataInputError("Migrated TARGET-DATA2D v3 requires the v3 fixed-eight policy.")
        elif self.policy.policy_version != TARGET_SIZE_CONVERGENCE_VERSION:
            raise TrainingDataInputError("Historical TARGET-DATA2D v2 requires the v2 policy.")
        rungs = tuple(sorted(self.stage_a_rungs, key=lambda x: x.target_size))
        qualified = tuple(item.target_size for item in rungs if item.qualified)
        survivors = tuple(int(v) for v in self.stage_a_survivor_sizes)
        if survivors != qualified:
            raise TrainingDataInputError("TARGET-DATA2D Stage A must retain every hard-coverage-qualified rung.")
        if len(survivors) < self.policy.min_coverage_qualifiers:
            raise TrainingDataInputError("TARGET-DATA2D Stage-A qualifier count violates frozen policy.")
        coarse = tuple(sorted(self.coarse_training_evidence, key=lambda x: x.target_size))
        stage_b = tuple(int(v) for v in self.stage_b_survivor_sizes)
        short = tuple(sorted(self.short_training_evidence, key=lambda x: x.target_size))
        finalists = tuple(int(v) for v in self.stage_b_finalist_sizes)
        finals = tuple(sorted(self.final_training_evidence, key=lambda x: x.target_size))
        if any(x.stage != "coarse" for x in coarse) or any(x.stage != "short" for x in short) or any(x.stage != "final" for x in finals):
            raise TrainingDataInputError("TARGET-DATA2D evidence is stored under the wrong stage.")
        if any(x.target_size not in survivors for x in coarse):
            raise TrainingDataInputError("TARGET-DATA2D coarse evidence exists outside hard-coverage qualifiers.")
        if stage_b and (len(stage_b) > self.policy.max_coarse_training_candidates or len(stage_b) < 2 or any(v not in survivors for v in stage_b)):
            raise TrainingDataInputError("TARGET-DATA2D 3-epoch survivor set is invalid.")
        if any(x.target_size not in stage_b for x in short):
            raise TrainingDataInputError("TARGET-DATA2D 10-epoch evidence exists outside 3-epoch survivors.")
        if finalists and (len(finalists) != self.policy.max_short_training_candidates or any(v not in stage_b for v in finalists)):
            raise TrainingDataInputError("TARGET-DATA2D 10-epoch finalists are invalid.")
        if any(x.target_size not in finalists for x in finals):
            raise TrainingDataInputError("TARGET-DATA2D final evidence exists outside 10-epoch finalists.")
        selected = None if self.selected_target_size is None else int(self.selected_target_size)
        if selected is not None and selected not in finalists:
            raise TrainingDataInputError("TARGET-DATA2D selected size is not a 30-epoch finalist.")
        allowed = {_WAIT_COARSE, _WAIT_SHORT, _WAIT_FINAL, _SELECTED, _NONCONVERGED, _FAILED}
        if self.outcome not in allowed:
            raise TrainingDataInputError("Unsupported TARGET-DATA2D outcome.")
        if self.outcome == _WAIT_COARSE and (coarse or stage_b or short or finalists or finals or selected is not None):
            raise TrainingDataInputError("TARGET-DATA2D coarse-wait state contains later-stage evidence.")
        if self.outcome == _WAIT_SHORT and (not stage_b or short or finalists or finals or selected is not None):
            raise TrainingDataInputError("TARGET-DATA2D short-wait state is inconsistent.")
        if self.outcome == _WAIT_FINAL and (not finalists or finals or selected is not None):
            raise TrainingDataInputError("TARGET-DATA2D final-wait state is inconsistent.")
        if self.outcome == _SELECTED and selected is None:
            raise TrainingDataInputError("TARGET-DATA2D selected outcome requires selected_target_size.")
        object.__setattr__(self, "stage_a_rungs", rungs); object.__setattr__(self, "stage_a_survivor_sizes", survivors)
        object.__setattr__(self, "coarse_training_evidence", coarse); object.__setattr__(self, "stage_b_survivor_sizes", stage_b)
        object.__setattr__(self, "short_training_evidence", short); object.__setattr__(self, "stage_b_finalist_sizes", finalists)
        object.__setattr__(self, "final_training_evidence", finals); object.__setattr__(self, "selected_target_size", selected)

    @property
    def complete(self) -> bool:
        return self.outcome in {_SELECTED, _NONCONVERGED, _FAILED}

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (TARGET_SIZE_CONVERGENCE_MV_PLAN_SCHEMA if self.authority_version == TARGET_SIZE_CONVERGENCE_MV_VERSION else TARGET_SIZE_CONVERGENCE_PLAN_SCHEMA), "authority_version": self.authority_version,
            "dataset_id": self.dataset_id, "target_data_ladder_digest": self.target_data_ladder_digest,
            "policy": self.policy.to_dict(), "stage_a_rungs": [v.to_dict() for v in self.stage_a_rungs],
            "stage_a_survivor_sizes": list(self.stage_a_survivor_sizes),
            "coarse_training_evidence": [v.to_dict() for v in self.coarse_training_evidence],
            "stage_b_survivor_sizes": list(self.stage_b_survivor_sizes),
            "short_training_evidence": [v.to_dict() for v in self.short_training_evidence],
            "stage_b_finalist_sizes": list(self.stage_b_finalist_sizes),
            "final_training_evidence": [v.to_dict() for v in self.final_training_evidence],
            "selected_target_size": self.selected_target_size, "outcome": self.outcome, "decision_reason": self.decision_reason,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload()); object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetSizeConvergencePlan":
        schema = payload.get("schema")
        if schema not in {TARGET_SIZE_CONVERGENCE_PLAN_SCHEMA, TARGET_SIZE_CONVERGENCE_MV_PLAN_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported TARGET-DATA2D convergence authority schema.")
        expected_version = TARGET_SIZE_CONVERGENCE_MV_VERSION if schema == TARGET_SIZE_CONVERGENCE_MV_PLAN_SCHEMA else TARGET_SIZE_CONVERGENCE_VERSION
        if str(payload.get("authority_version")) != expected_version:
            raise TrainingDataSerializationError("TARGET-DATA2D plan schema/version generation mismatch.")
        result = cls(
            dataset_id=str(payload["dataset_id"]), target_data_ladder_digest=str(payload["target_data_ladder_digest"]),
            policy=TargetSizeConvergencePolicy.from_dict(payload["policy"]),
            stage_a_rungs=tuple(TargetSizeStageARung.from_dict(v) for v in payload["stage_a_rungs"]),
            stage_a_survivor_sizes=tuple(int(v) for v in payload["stage_a_survivor_sizes"]),
            coarse_training_evidence=tuple(TargetSizeTrainingEvidence.from_dict(v) for v in payload.get("coarse_training_evidence", ())),
            stage_b_survivor_sizes=tuple(int(v) for v in payload.get("stage_b_survivor_sizes", ())),
            short_training_evidence=tuple(TargetSizeTrainingEvidence.from_dict(v) for v in payload.get("short_training_evidence", ())),
            stage_b_finalist_sizes=tuple(int(v) for v in payload.get("stage_b_finalist_sizes", ())),
            final_training_evidence=tuple(TargetSizeTrainingEvidence.from_dict(v) for v in payload.get("final_training_evidence", ())),
            selected_target_size=None if payload.get("selected_target_size") is None else int(payload["selected_target_size"]),
            outcome=str(payload["outcome"]), decision_reason=str(payload.get("decision_reason", "")), authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("TARGET-DATA2D plan digest mismatch.")
        return result


def _stage_a_rungs(ladder: TargetDataLadderPlan) -> tuple[TargetSizeStageARung, ...]:
    if ladder.authority_version not in {TARGET_DATA_LADDER_VERSION, TARGET_DATA_LADDER_MV_VERSION}:
        raise TrainingDataInputError("TARGET-DATA2D requires a supported TARGET-DATA2C v4/v5 full-ladder authority.")
    q = {item.target_size: item for item in ladder.rung_qualifications}
    results = []
    for size in ladder.configured_candidate_sizes:
        if size in q:
            item = q[size]
            results.append(TargetSizeStageARung(
                target_size=size, materializable=True, qualified=item.qualified,
                domain_coverage_passed=item.domain_coverage_passed, domain_mandatory_passed=item.domain_mandatory_passed,
                coverage_report_digests=item.coverage_report_digests, failure_reasons=item.failure_reasons,
            ))
        else:
            # unavailable rungs are represented from domain records so the full
            # configured sequence remains visible but cannot qualify.
            reports = []
            coverage = []
            mandatory = []
            for domain in ladder.domains:
                coverage.append((domain.label_domain_id, False)); mandatory.append((domain.label_domain_id, False))
                reports.append((domain.label_domain_id, digest({"schema": "mdstats.target-data2d.unavailable-rung.v1", "domain": domain.label_domain_id, "target_size": size})))
            results.append(TargetSizeStageARung(size, False, False, tuple(coverage), tuple(mandatory), tuple(reports), ("unavailable",)))
    return tuple(results)


def build_target_size_convergence_plan(ladder: TargetDataLadderPlan, *, policy: TargetSizeConvergencePolicy | None = None) -> TargetSizeConvergencePlan:
    """Freeze hard coverage and retain every qualifying rung for epoch 3."""
    expected_version = TARGET_SIZE_CONVERGENCE_MV_VERSION if ladder.authority_version == TARGET_DATA_LADDER_MV_VERSION else TARGET_SIZE_CONVERGENCE_VERSION
    policy = policy or TargetSizeConvergencePolicy(
        min_coverage_qualifiers=4 if expected_version == TARGET_SIZE_CONVERGENCE_MV_VERSION else 3,
        policy_version=expected_version,
    )
    if policy.policy_version != expected_version:
        raise TrainingDataInputError("TARGET-DATA2D policy version does not match the supplied TARGET-DATA2C authority generation.")
    stage_a = _stage_a_rungs(ladder)
    qualified = tuple(item.target_size for item in stage_a if item.qualified)
    if len(qualified) < policy.min_coverage_qualifiers:
        summary = ", ".join(f"n{x.target_size}:{'PASS' if x.qualified else 'FAIL'}" for x in stage_a)
        rescue = (
            f"coverage_rescue={'active' if ladder.coverage_rescue_activated else 'inactive'}"
            f"; rescue_candidates={list(ladder.coverage_rescue_candidate_sizes)}"
        )
        details: list[str] = []
        if ladder.materialized_target_sizes:
            largest_size = ladder.materialized_target_sizes[-1]
            for domain in ladder.domains:
                try:
                    rung = next(item for item in domain.materialized_rungs if item.target_size == largest_size)
                except StopIteration:
                    continue
                report = rung.coverage_report
                if report is not None:
                    failed_families = []
                    for family in report.family_reports:
                        if family.required and (not family.coverage_passed or not family.extent_passed):
                            extent = ",".join(family.extent_failures) if family.extent_failures else "ok"
                            failed_families.append(
                                f"{family.family_id}[mass={family.covered_reference_mass:.4f}/{family.threshold:.4f},extent={extent}]"
                            )
                    failed_strata = [
                        f"{item.stratum_id}[{item.selected_frame_count}/{item.minimum_selected_frames}]"
                        for item in report.stratum_reports if item.required and not item.passed
                    ]
                    if failed_families:
                        details.append(f"{domain.label_domain_id}:families=" + ",".join(failed_families))
                    if failed_strata:
                        details.append(f"{domain.label_domain_id}:strata=" + ",".join(failed_strata))
                if not rung.mandatory_obligations_passed:
                    details.append(
                        f"{domain.label_domain_id}:mandatory=" + ",".join(rung.unsatisfied_obligation_ids)
                    )
        detail_suffix = f"; largest_rung_failures={' | '.join(details)}" if details else ""
        raise TargetDataCoverageError(
            f"TARGET-DATA2D hard coverage found fewer than {policy.min_coverage_qualifiers} qualified rungs; "
            f"{summary}; {rescue}{detail_suffix}."
        )
    return TargetSizeConvergencePlan(
        dataset_id=ladder.dataset_id, target_data_ladder_digest=ladder.content_digest, policy=policy,
        stage_a_rungs=stage_a, stage_a_survivor_sizes=qualified, outcome=_WAIT_COARSE,
        decision_reason=f"hard coverage admitted all {len(qualified)} qualifying rungs; awaiting exact epoch-{policy.coarse_training_epochs} target-only screen",
        authority_version=expected_version,
    )


def _evidence_map(evidence: Sequence[TargetSizeTrainingEvidence]) -> dict[int, TargetSizeTrainingEvidence]:
    out = {}
    for item in evidence:
        if item.target_size in out:
            raise TrainingDataInputError(f"Duplicate TARGET-DATA2D evidence for n{item.target_size}.")
        out[item.target_size] = item
    return out


def _equivalence_aware_target_order(
    evidence: Sequence[TargetSizeTrainingEvidence],
    *,
    epsilon: float,
    boundary_preserve_size: int | None = None,
) -> tuple[int, ...]:
    """Order by target score with deterministic practical-equivalence bands.

    Final selection prefers the smaller size inside an equivalence band.  The
    epoch-3/10 promotion screens may instead preserve the largest tested
    boundary *inside its own equivalence band*.  This does not rescue a
    materially worse boundary rung; it only prevents a finite-budget tie from
    erasing the upper-bound convergence sentinel before epoch 30.
    """

    remaining = sorted(evidence, key=lambda x: (x.target_force_score_mev_per_a, x.target_size))
    ordered: list[int] = []
    boundary = None if boundary_preserve_size is None else int(boundary_preserve_size)
    while remaining:
        anchor = remaining[0].target_force_score_mev_per_a
        band = [x for x in remaining if x.target_force_score_mev_per_a <= anchor + epsilon + 1.0e-12]
        band.sort(key=lambda x: (0 if boundary is not None and x.target_size == boundary else 1, x.target_size))
        ordered.extend(x.target_size for x in band)
        ids = {x.target_size for x in band}
        remaining = [x for x in remaining if x.target_size not in ids]
    return tuple(ordered)


def _common_screening_identity(evidence: Mapping[int, TargetSizeTrainingEvidence]) -> None:
    if len({x.foundation_identity_digest for x in evidence.values()}) != 1 or len({x.evaluation_role_digest for x in evidence.values()}) != 1 or len({x.training_policy_digest for x in evidence.values()}) != 1 or len({x.schedule_digest for x in evidence.values()}) != 1:
        raise TrainingDataInputError("TARGET-DATA2D candidates must share foundation, evaluation role, TRAIN2 policy, and schedule identity.")


def with_stage_b0_evidence(plan: TargetSizeConvergencePlan, evidence: Sequence[TargetSizeTrainingEvidence]) -> TargetSizeConvergencePlan:
    """Apply the exact epoch-3 target-only screen and retain at most four."""
    if plan.outcome != _WAIT_COARSE:
        raise TrainingDataInputError("TARGET-DATA2D epoch-3 evidence can only be attached while awaiting coarse training.")
    by_size = _evidence_map(evidence); expected = set(plan.stage_a_survivor_sizes)
    if set(by_size) != expected:
        raise TrainingDataInputError(f"TARGET-DATA2D epoch-3 evidence must cover every coverage-qualified rung; missing={sorted(expected-set(by_size))}, extra={sorted(set(by_size)-expected)}.")
    for item in by_size.values():
        if item.stage != "coarse" or item.completed_epochs != plan.policy.coarse_training_epochs or item.planned_epochs != plan.policy.final_training_epochs or item.optimizer_seed != plan.policy.screening_optimizer_seed:
            raise TrainingDataInputError("TARGET-DATA2D coarse evidence is not the exact 3-of-30 screening boundary.")
    _common_screening_identity(by_size)
    admissible = tuple(x for x in by_size.values() if x.admissible_for_screening)
    if len(admissible) < 2:
        return TargetSizeConvergencePlan(plan.dataset_id, plan.target_data_ladder_digest, plan.policy, plan.stage_a_rungs, plan.stage_a_survivor_sizes, coarse_training_evidence=tuple(by_size.values()), outcome=_FAILED, decision_reason="epoch-3 screen left fewer than two numerically valid candidates", authority_version=plan.authority_version)
    ranking = _equivalence_aware_target_order(
        admissible,
        epsilon=float(plan.policy.coarse_practical_equivalence_mev_per_a),
        boundary_preserve_size=max(plan.stage_a_survivor_sizes),
    )
    survivors = tuple(ranking[:min(plan.policy.max_coarse_training_candidates, len(ranking))])
    return TargetSizeConvergencePlan(
        plan.dataset_id, plan.target_data_ladder_digest, plan.policy, plan.stage_a_rungs, plan.stage_a_survivor_sizes,
        coarse_training_evidence=tuple(by_size.values()), stage_b_survivor_sizes=survivors, outcome=_WAIT_SHORT,
        decision_reason="epoch-3 target-only equivalence-aware screen retained " + ", ".join(f"n{v}" for v in survivors),
        authority_version=plan.authority_version,
    )


def with_stage_b_evidence(plan: TargetSizeConvergencePlan, evidence: Sequence[TargetSizeTrainingEvidence]) -> TargetSizeConvergencePlan:
    """Apply the exact epoch-10 screen to the epoch-3 survivors and retain two."""
    if plan.outcome != _WAIT_SHORT:
        raise TrainingDataInputError("TARGET-DATA2D epoch-10 evidence can only be attached while awaiting short training.")
    by_size = _evidence_map(evidence); expected = set(plan.stage_b_survivor_sizes)
    if set(by_size) != expected:
        raise TrainingDataInputError(f"TARGET-DATA2D epoch-10 evidence must cover every epoch-3 survivor; missing={sorted(expected-set(by_size))}, extra={sorted(set(by_size)-expected)}.")
    coarse = {x.target_size: x for x in plan.coarse_training_evidence}
    for size, item in by_size.items():
        if item.stage != "short" or item.completed_epochs != plan.policy.short_training_epochs or item.planned_epochs != plan.policy.final_training_epochs or item.optimizer_seed != plan.policy.screening_optimizer_seed:
            raise TrainingDataInputError("TARGET-DATA2D short evidence is not the exact 10-of-30 screening boundary.")
        parent = coarse.get(size)
        if parent is None or (item.parent_checkpoint_digest, item.parent_optimizer_state_digest, item.parent_rng_state_digest) != (parent.checkpoint_digest, parent.optimizer_state_digest, parent.rng_state_digest):
            raise TrainingDataInputError(f"TARGET-DATA2D epoch-10 continuation ancestry differs from epoch 3 for n{size}.")
    _common_screening_identity(by_size)
    admissible = tuple(x for x in by_size.values() if x.admissible_for_screening)
    if len(admissible) < 2:
        return TargetSizeConvergencePlan(plan.dataset_id, plan.target_data_ladder_digest, plan.policy, plan.stage_a_rungs, plan.stage_a_survivor_sizes, plan.coarse_training_evidence, plan.stage_b_survivor_sizes, tuple(by_size.values()), outcome=_FAILED, decision_reason="epoch-10 screen left fewer than two numerically valid candidates", authority_version=plan.authority_version)
    ranking = _equivalence_aware_target_order(
        admissible,
        epsilon=plan.policy.practical_equivalence_mev_per_a,
        boundary_preserve_size=max(plan.stage_a_survivor_sizes),
    )
    finalists = tuple(ranking[:2])
    return TargetSizeConvergencePlan(
        plan.dataset_id, plan.target_data_ladder_digest, plan.policy, plan.stage_a_rungs, plan.stage_a_survivor_sizes,
        plan.coarse_training_evidence, plan.stage_b_survivor_sizes, tuple(by_size.values()), finalists,
        outcome=_WAIT_FINAL, decision_reason="epoch-10 target-only equivalence-aware screen retained " + ", ".join(f"n{v}" for v in finalists),
        authority_version=plan.authority_version,
    )


def with_stage_c_evidence(plan: TargetSizeConvergencePlan, evidence: Sequence[TargetSizeTrainingEvidence], *, largest_materialized_size: int | None = None) -> TargetSizeConvergencePlan:
    """Freeze 30-epoch evidence and select one size or report boundary non-convergence."""
    if plan.outcome != _WAIT_FINAL:
        raise TrainingDataInputError("TARGET-DATA2D final evidence can only be attached while awaiting full training.")
    by_size = _evidence_map(evidence); expected = set(plan.stage_b_finalist_sizes)
    if set(by_size) != expected:
        raise TrainingDataInputError(f"TARGET-DATA2D final evidence must cover both finalists; missing={sorted(expected-set(by_size))}, extra={sorted(set(by_size)-expected)}.")
    short = {x.target_size: x for x in plan.short_training_evidence}
    for size, item in by_size.items():
        if item.stage != "final" or item.completed_epochs != plan.policy.final_training_epochs or item.planned_epochs != plan.policy.final_training_epochs or item.optimizer_seed != plan.policy.screening_optimizer_seed:
            raise TrainingDataInputError("TARGET-DATA2D final evidence is not the exact 30-of-30 boundary.")
        parent = short.get(size)
        if parent is None or (item.parent_checkpoint_digest, item.parent_optimizer_state_digest, item.parent_rng_state_digest) != (parent.checkpoint_digest, parent.optimizer_state_digest, parent.rng_state_digest):
            raise TrainingDataInputError(f"TARGET-DATA2D epoch-30 continuation ancestry differs from epoch 10 for n{size}.")
        for attr, text in (("foundation_identity_digest", "foundation identity"), ("evaluation_role_digest", "evaluation role"), ("training_policy_digest", "TRAIN2 policy"), ("schedule_digest", "schedule")):
            if getattr(item, attr) != getattr(parent, attr):
                raise TrainingDataInputError(f"TARGET-DATA2D {text} changed after epoch 10 for n{size}.")
    admissible = tuple(x for x in by_size.values() if x.admissible_for_stage_c)
    common = dict(
        dataset_id=plan.dataset_id, target_data_ladder_digest=plan.target_data_ladder_digest, policy=plan.policy,
        stage_a_rungs=plan.stage_a_rungs, stage_a_survivor_sizes=plan.stage_a_survivor_sizes,
        coarse_training_evidence=plan.coarse_training_evidence, stage_b_survivor_sizes=plan.stage_b_survivor_sizes,
        short_training_evidence=plan.short_training_evidence, stage_b_finalist_sizes=plan.stage_b_finalist_sizes,
        final_training_evidence=tuple(by_size.values()),
        authority_version=plan.authority_version,
    )
    if not admissible:
        return TargetSizeConvergencePlan(**common, outcome=_FAILED, decision_reason="both 30-epoch finalists failed target/replay/physical admissibility")
    ranking = _equivalence_aware_target_order(admissible, epsilon=plan.policy.practical_equivalence_mev_per_a)
    winner = ranking[0]
    boundary = max(plan.stage_a_survivor_sizes) if largest_materialized_size is None else int(largest_materialized_size)
    if winner == boundary:
        smaller = [x for x in admissible if x.target_size < winner]
        if not smaller:
            return TargetSizeConvergencePlan(**common, outcome=_NONCONVERGED, decision_reason=f"largest qualified rung n{winner} is the only 30-epoch admissible finalist")
        best_smaller = min(smaller, key=lambda x: (x.target_force_score_mev_per_a, x.target_size))
        improvement = best_smaller.target_force_score_mev_per_a - by_size[winner].target_force_score_mev_per_a
        if improvement > plan.policy.practical_equivalence_mev_per_a + 1.0e-12:
            return TargetSizeConvergencePlan(**common, outcome=_NONCONVERGED, decision_reason=f"largest qualified rung n{winner} improves target force score by {improvement:.6g} meV/A beyond practical equivalence")
    return TargetSizeConvergencePlan(**common, selected_target_size=winner, outcome=_SELECTED, decision_reason=f"epoch-30 selected n{winner} after target/replay/physical qualification")


def validate_target_size_convergence_authority(plan: TargetSizeConvergencePlan, *, ladder: TargetDataLadderPlan) -> None:
    if ladder.authority_version not in {TARGET_DATA_LADDER_VERSION, TARGET_DATA_LADDER_MV_VERSION}:
        raise TrainingDataInputError("TARGET-DATA2D requires a supported TARGET-DATA2C v4/v5 authority.")
    expected_version = TARGET_SIZE_CONVERGENCE_MV_VERSION if ladder.authority_version == TARGET_DATA_LADDER_MV_VERSION else TARGET_SIZE_CONVERGENCE_VERSION
    if plan.authority_version != expected_version or plan.policy.policy_version != expected_version:
        raise TrainingDataInputError("TARGET-DATA2D authority generation does not match TARGET-DATA2C.")
    if plan.dataset_id != ladder.dataset_id or plan.target_data_ladder_digest != ladder.content_digest:
        raise TrainingDataInputError("TARGET-DATA2D authority no longer matches TARGET-DATA2C.")
    expected = _stage_a_rungs(ladder)
    if tuple(x.to_dict()["content_digest"] for x in plan.stage_a_rungs) != tuple(x.to_dict()["content_digest"] for x in expected):
        raise TrainingDataInputError("TARGET-DATA2D hard-coverage evidence no longer matches TARGET-DATA2C.")
    qualified = tuple(x.target_size for x in expected if x.qualified)
    if len(qualified) < plan.policy.min_coverage_qualifiers:
        raise TargetDataCoverageError("TARGET-DATA2D live hard-coverage evidence no longer has enough qualifiers.")
    if plan.stage_a_survivor_sizes != qualified:
        raise TrainingDataInputError("TARGET-DATA2D must retain every hard-coverage-qualified rung.")
