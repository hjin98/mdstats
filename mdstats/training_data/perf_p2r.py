"""PERF-P2R CPU/control-plane authority for the corrected size funnel.

This module contains no accelerator assumptions.  It encodes the parameterized
configurable successive-fidelity execution geometry required while
SIZE-FIDELITY1 is awaiting final-release GPU calibration.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

PERF_P2R_PARAMETER_GRID_SCHEMA = "mdstats.perf-p2r-parameter-grid.flexible-fidelity.v3"
PERF_P2R_STAGE_PLAN_SCHEMA = "mdstats.perf-p2r-stage-plan.flexible-fidelity.v4"
PERF_P2R_EXPOSURE_SCHEMA = "mdstats.perf-p2r-exposure.v2"


@dataclass(frozen=True, slots=True)
class PerfP2RParameterGrid:
    """Implementation-compatibility grid pending SIZE-FIDELITY1 calibration.

    These values are *not* calibrated production defaults.  They define the
    complete scientific parameter surface that PERF-P2R must execute without
    branching into a different implementation.
    """

    coarse_epoch_candidates: tuple[int, ...] = (1,)
    coarse_monitor_size_candidates: tuple[int, ...] = (128, 256, 512, 1024)
    coarse_equivalence_mev_per_a_candidates: tuple[float, ...] = (1.0,)
    minimum_coverage_qualified_sizes: int = 3
    maximum_coverage_qualified_sizes: int = 8
    coarse_survivor_limit: int = 4
    short_survivor_limit: int = 2
    serialization_schema: str = field(
        default=PERF_P2R_PARAMETER_GRID_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != PERF_P2R_PARAMETER_GRID_SCHEMA:
            raise TrainingDataInputError("Unsupported PERF-P2R parameter-grid schema.")
        coarse = tuple(sorted(set(int(v) for v in self.coarse_epoch_candidates)))
        monitors = tuple(sorted(set(int(v) for v in self.coarse_monitor_size_candidates)))
        equivalence = tuple(
            sorted(set(float(v) for v in self.coarse_equivalence_mev_per_a_candidates))
        )
        if not coarse or any(v <= 0 for v in coarse):
            raise TrainingDataInputError("PERF-P2R coarse epoch candidates must be positive.")
        if not monitors or any(v <= 0 for v in monitors):
            raise TrainingDataInputError("PERF-P2R monitor-size candidates must be positive.")
        if not equivalence or any(v <= 0.0 for v in equivalence):
            raise TrainingDataInputError("PERF-P2R equivalence candidates must be positive.")
        minimum = int(self.minimum_coverage_qualified_sizes)
        maximum = int(self.maximum_coverage_qualified_sizes)
        coarse_limit = int(self.coarse_survivor_limit)
        short_limit = int(self.short_survivor_limit)
        if minimum < 2 or maximum < minimum:
            raise TrainingDataInputError("PERF-P2R coverage-qualified size bounds are invalid.")
        if short_limit != 2 or coarse_limit < short_limit or coarse_limit > maximum:
            raise TrainingDataInputError("PERF-P2R survivor limits are invalid.")
        object.__setattr__(self, "coarse_epoch_candidates", coarse)
        object.__setattr__(self, "coarse_monitor_size_candidates", monitors)
        object.__setattr__(self, "coarse_equivalence_mev_per_a_candidates", equivalence)
        object.__setattr__(self, "minimum_coverage_qualified_sizes", minimum)
        object.__setattr__(self, "maximum_coverage_qualified_sizes", maximum)
        object.__setattr__(self, "coarse_survivor_limit", coarse_limit)
        object.__setattr__(self, "short_survivor_limit", short_limit)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "coarse_epoch_candidates": list(self.coarse_epoch_candidates),
            "coarse_monitor_size_candidates": list(self.coarse_monitor_size_candidates),
            "coarse_equivalence_mev_per_a_candidates": list(
                self.coarse_equivalence_mev_per_a_candidates
            ),
            "minimum_coverage_qualified_sizes": self.minimum_coverage_qualified_sizes,
            "maximum_coverage_qualified_sizes": self.maximum_coverage_qualified_sizes,
            "coarse_survivor_limit": self.coarse_survivor_limit,
            "short_survivor_limit": self.short_survivor_limit,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfP2RParameterGrid":
        if payload.get("schema") != PERF_P2R_PARAMETER_GRID_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-P2R parameter-grid schema.")
        result = cls(
            coarse_epoch_candidates=tuple(int(v) for v in payload["coarse_epoch_candidates"]),
            coarse_monitor_size_candidates=tuple(
                int(v) for v in payload["coarse_monitor_size_candidates"]
            ),
            coarse_equivalence_mev_per_a_candidates=tuple(
                float(v) for v in payload["coarse_equivalence_mev_per_a_candidates"]
            ),
            minimum_coverage_qualified_sizes=int(payload["minimum_coverage_qualified_sizes"]),
            maximum_coverage_qualified_sizes=int(payload["maximum_coverage_qualified_sizes"]),
            coarse_survivor_limit=int(payload["coarse_survivor_limit"]),
            short_survivor_limit=int(payload["short_survivor_limit"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-P2R parameter-grid digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfP2RStagePlan:
    """One work-authorizing stage of the successive-fidelity funnel."""

    target_size_study_digest: str
    stage: str
    candidate_sizes: tuple[int, ...]
    start_epoch: int
    target_epoch: int
    schedule_horizon_epoch: int
    screening_optimizer_seeds: tuple[int, ...]
    continuation_required: bool
    target_only_evaluation: bool
    replay_diagnostic_authorized: bool
    physical_qualification_authorized: bool
    serialization_schema: str = field(
        default=PERF_P2R_STAGE_PLAN_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != PERF_P2R_STAGE_PLAN_SCHEMA:
            raise TrainingDataInputError("Unsupported PERF-P2R stage-plan schema.")
        object.__setattr__(
            self,
            "target_size_study_digest",
            validate_digest(self.target_size_study_digest, name="target_size_study_digest"),
        )
        stage = str(self.stage)
        if stage not in {"coarse", "short", "final_screen", "production"}:
            raise TrainingDataInputError("Unsupported PERF-P2R execution stage.")
        sizes = tuple(sorted(set(int(v) for v in self.candidate_sizes)))
        if not sizes or any(v <= 0 for v in sizes):
            raise TrainingDataInputError("PERF-P2R stage requires positive candidate sizes.")
        start = int(self.start_epoch)
        target = int(self.target_epoch)
        horizon = int(self.schedule_horizon_epoch)
        if start < 0 or target <= start or horizon < target:
            raise TrainingDataInputError("PERF-P2R stage epoch geometry is invalid.")
        if bool(self.continuation_required) != (start > 0):
            raise TrainingDataInputError(
                "PERF-P2R continuation flag must exactly match a nonzero start boundary."
            )
        if stage == "coarse":
            if not self.target_only_evaluation or self.replay_diagnostic_authorized or self.physical_qualification_authorized:
                raise TrainingDataInputError("PERF-P2R coarse stage must be target-only.")
        elif stage in {"short", "final_screen"}:
            if not self.target_only_evaluation or self.replay_diagnostic_authorized or self.physical_qualification_authorized:
                raise TrainingDataInputError(
                    "PERF-P2R target-size-v5 selection stages must remain target-only."
                )
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "candidate_sizes", sizes)
        object.__setattr__(self, "start_epoch", start)
        object.__setattr__(self, "target_epoch", target)
        object.__setattr__(self, "schedule_horizon_epoch", horizon)
        seeds = tuple(int(v) for v in self.screening_optimizer_seeds)
        if stage == "production":
            if seeds:
                raise TrainingDataInputError(
                    "PERF-P2R production stage does not own target-size screening seeds."
                )
        elif not seeds or len(set(seeds)) != len(seeds) or any(v < 0 for v in seeds):
            raise TrainingDataInputError(
                "PERF-P2R screening stages require the authenticated ordered unique seed set."
            )
        object.__setattr__(self, "screening_optimizer_seeds", seeds)

    @property
    def incremental_epochs(self) -> int:
        return self.target_epoch - self.start_epoch

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "target_size_study_digest": self.target_size_study_digest,
            "stage": self.stage,
            "candidate_sizes": list(self.candidate_sizes),
            "start_epoch": self.start_epoch,
            "target_epoch": self.target_epoch,
            "schedule_horizon_epoch": self.schedule_horizon_epoch,
            "screening_optimizer_seeds": list(self.screening_optimizer_seeds),
            "continuation_required": self.continuation_required,
            "target_only_evaluation": self.target_only_evaluation,
            "replay_diagnostic_authorized": self.replay_diagnostic_authorized,
            "physical_qualification_authorized": self.physical_qualification_authorized,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfP2RStagePlan":
        if payload.get("schema") != PERF_P2R_STAGE_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-P2R stage-plan schema.")
        result = cls(
            target_size_study_digest=str(payload["target_size_study_digest"]),
            stage=str(payload["stage"]),
            candidate_sizes=tuple(int(v) for v in payload["candidate_sizes"]),
            start_epoch=int(payload["start_epoch"]),
            target_epoch=int(payload["target_epoch"]),
            schedule_horizon_epoch=int(payload["schedule_horizon_epoch"]),
            screening_optimizer_seeds=tuple(
                int(v) for v in payload.get("screening_optimizer_seeds", ())
            ),
            continuation_required=bool(payload["continuation_required"]),
            target_only_evaluation=bool(payload["target_only_evaluation"]),
            replay_diagnostic_authorized=bool(payload["replay_diagnostic_authorized"]),
            physical_qualification_authorized=bool(payload["physical_qualification_authorized"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-P2R stage-plan digest mismatch.")
        return result


def build_perf_p2r_stage_plan(study: Any) -> PerfP2RStagePlan:
    """Translate one current target-size-v5 authority into an exact work boundary."""

    outcome = str(study.outcome)
    policy = study.policy
    coarse_epoch, short_epoch, final_screen_epoch = (int(v) for v in policy.fidelity_epochs)
    common = dict(
        target_size_study_digest=str(study.content_digest),
        schedule_horizon_epoch=int(study.training_horizon_epochs),
    )
    if outcome == "awaiting_coarse_screen":
        return PerfP2RStagePlan(
            **common, stage="coarse", candidate_sizes=tuple(study.qualified_sizes),
            start_epoch=0, target_epoch=coarse_epoch,
            screening_optimizer_seeds=tuple(policy.screening_optimizer_seeds),
            continuation_required=False, target_only_evaluation=True,
            replay_diagnostic_authorized=False, physical_qualification_authorized=False,
        )
    if outcome == "awaiting_short_screen":
        return PerfP2RStagePlan(
            **common, stage="short", candidate_sizes=tuple(study.coarse_survivor_sizes),
            start_epoch=coarse_epoch, target_epoch=short_epoch,
            screening_optimizer_seeds=tuple(policy.screening_optimizer_seeds),
            continuation_required=True, target_only_evaluation=True,
            replay_diagnostic_authorized=False, physical_qualification_authorized=False,
        )
    if outcome == "awaiting_final_screen":
        return PerfP2RStagePlan(
            **common, stage="final_screen", candidate_sizes=tuple(study.short_finalist_sizes),
            start_epoch=short_epoch, target_epoch=final_screen_epoch,
            screening_optimizer_seeds=tuple(policy.screening_optimizer_seeds),
            continuation_required=True, target_only_evaluation=True,
            replay_diagnostic_authorized=False, physical_qualification_authorized=False,
        )
    if outcome == "selected":
        if study.selected_target_size is None:
            raise TrainingDataInputError("Selected target-size-v5 authority lacks a target size.")
        return PerfP2RStagePlan(
            **common, stage="production", candidate_sizes=(int(study.selected_target_size),),
            start_epoch=0, target_epoch=int(study.training_horizon_epochs), screening_optimizer_seeds=(),
            continuation_required=False, target_only_evaluation=False,
            replay_diagnostic_authorized=True, physical_qualification_authorized=True,
        )
    raise TrainingDataInputError(
        f"Target-size-v5 outcome {outcome!r} does not authorize PERF-P2R training work."
    )


@dataclass(frozen=True, slots=True)
class PerfP2RExposure:
    admissible_sizes: tuple[int, ...]
    coarse_survivor_sizes: tuple[int, ...]
    short_finalist_sizes: tuple[int, ...]
    coarse_screen_epoch: int
    short_screen_epoch: int
    final_screen_epoch: int
    reference_training_epoch: int
    coarse_structure_epochs: int
    short_increment_structure_epochs: int
    final_increment_structure_epochs: int
    total_structure_epochs: int
    exhaustive_structure_epochs: int
    saved_structure_epochs: int
    saved_fraction: float
    serialization_schema: str = field(
        default=PERF_P2R_EXPOSURE_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.serialization_schema != PERF_P2R_EXPOSURE_SCHEMA:
            raise TrainingDataInputError("Unsupported PERF-P2R exposure schema.")
        for name in (
            "coarse_structure_epochs",
            "short_increment_structure_epochs",
            "final_increment_structure_epochs",
            "total_structure_epochs",
            "exhaustive_structure_epochs",
            "saved_structure_epochs",
        ):
            if int(getattr(self, name)) < 0:
                raise TrainingDataInputError("PERF-P2R exposure counts must be nonnegative.")
        fraction = float(self.saved_fraction)
        if not 0.0 <= fraction <= 1.0:
            raise TrainingDataInputError("PERF-P2R saved fraction must lie in [0, 1].")
        object.__setattr__(self, "saved_fraction", fraction)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "admissible_sizes": list(self.admissible_sizes),
            "coarse_survivor_sizes": list(self.coarse_survivor_sizes),
            "short_finalist_sizes": list(self.short_finalist_sizes),
            "coarse_screen_epoch": self.coarse_screen_epoch,
            "short_screen_epoch": self.short_screen_epoch,
            "final_screen_epoch": self.final_screen_epoch,
            "reference_training_epoch": self.reference_training_epoch,
            "coarse_structure_epochs": self.coarse_structure_epochs,
            "short_increment_structure_epochs": self.short_increment_structure_epochs,
            "final_increment_structure_epochs": self.final_increment_structure_epochs,
            "total_structure_epochs": self.total_structure_epochs,
            "exhaustive_structure_epochs": self.exhaustive_structure_epochs,
            "saved_structure_epochs": self.saved_structure_epochs,
            "saved_fraction": self.saved_fraction,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PerfP2RExposure":
        if payload.get("schema") != PERF_P2R_EXPOSURE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported PERF-P2R exposure schema.")
        result = cls(
            admissible_sizes=tuple(int(v) for v in payload["admissible_sizes"]),
            coarse_survivor_sizes=tuple(int(v) for v in payload["coarse_survivor_sizes"]),
            short_finalist_sizes=tuple(int(v) for v in payload["short_finalist_sizes"]),
            coarse_screen_epoch=int(payload["coarse_screen_epoch"]),
            short_screen_epoch=int(payload["short_screen_epoch"]),
            final_screen_epoch=int(payload["final_screen_epoch"]),
            reference_training_epoch=int(payload["reference_training_epoch"]),
            coarse_structure_epochs=int(payload["coarse_structure_epochs"]),
            short_increment_structure_epochs=int(payload["short_increment_structure_epochs"]),
            final_increment_structure_epochs=int(payload["final_increment_structure_epochs"]),
            total_structure_epochs=int(payload["total_structure_epochs"]),
            exhaustive_structure_epochs=int(payload["exhaustive_structure_epochs"]),
            saved_structure_epochs=int(payload["saved_structure_epochs"]),
            saved_fraction=float(payload["saved_fraction"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-P2R exposure digest mismatch.")
        return result


def build_perf_p2r_exposure(
    admissible_sizes: Sequence[int],
    coarse_survivor_sizes: Sequence[int],
    short_finalist_sizes: Sequence[int],
    *,
    coarse_screen_epoch: int,
    short_screen_epoch: int,
    final_screen_epoch: int,
    reference_training_epoch: int,
) -> PerfP2RExposure:
    """Compute exact incremental work exposure with no repaid training prefix."""

    admissible = tuple(sorted(set(int(v) for v in admissible_sizes)))
    coarse = tuple(sorted(set(int(v) for v in coarse_survivor_sizes)))
    finalists = tuple(sorted(set(int(v) for v in short_finalist_sizes)))
    if not admissible or any(v <= 0 for v in admissible):
        raise TrainingDataInputError("PERF-P2R exposure requires positive admissible sizes.")
    if not set(finalists).issubset(coarse) or not set(coarse).issubset(admissible):
        raise TrainingDataInputError("PERF-P2R survivor memberships must be nested.")
    if not finalists:
        raise TrainingDataInputError("PERF-P2R exposure requires at least one final candidate.")
    e0 = int(coarse_screen_epoch)
    e1 = int(short_screen_epoch)
    e2 = int(final_screen_epoch)
    reference = int(reference_training_epoch)
    if e0 <= 0 or not e0 < e1 < e2 <= reference:
        raise TrainingDataInputError("PERF-P2R exposure requires coarse < short < final epochs.")
    coarse_work = e0 * sum(admissible)
    short_work = (e1 - e0) * sum(coarse)
    final_work = (e2 - e1) * sum(finalists)
    total = coarse_work + short_work + final_work
    exhaustive = reference * sum(admissible)
    saved = exhaustive - total
    if saved < 0:
        raise TrainingDataInputError("PERF-P2R exposure cannot exceed exhaustive training.")
    return PerfP2RExposure(
        admissible_sizes=admissible,
        coarse_survivor_sizes=coarse,
        short_finalist_sizes=finalists,
        coarse_screen_epoch=e0,
        short_screen_epoch=e1,
        final_screen_epoch=e2,
        reference_training_epoch=reference,
        coarse_structure_epochs=coarse_work,
        short_increment_structure_epochs=short_work,
        final_increment_structure_epochs=final_work,
        total_structure_epochs=total,
        exhaustive_structure_epochs=exhaustive,
        saved_structure_epochs=saved,
        saved_fraction=(0.0 if exhaustive == 0 else saved / exhaustive),
    )
