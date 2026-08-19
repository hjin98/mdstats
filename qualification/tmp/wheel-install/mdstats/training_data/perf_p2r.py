"""PERF-P2R CPU/control-plane authority for the corrected size funnel.

This module contains no accelerator assumptions.  It encodes the parameterized
3/10/30-style successive-fidelity execution geometry required while
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

PERF_P2R_PARAMETER_GRID_SCHEMA = "mdstats.perf-p2r-parameter-grid.v1"
PERF_P2R_STAGE_PLAN_SCHEMA = "mdstats.perf-p2r-stage-plan.v1"
PERF_P2R_EXPOSURE_SCHEMA = "mdstats.perf-p2r-exposure.v1"


@dataclass(frozen=True, slots=True)
class PerfP2RParameterGrid:
    """Implementation-compatibility grid pending SIZE-FIDELITY1 calibration.

    These values are *not* calibrated production defaults.  They define the
    complete scientific parameter surface that PERF-P2R must execute without
    branching into a different implementation.
    """

    coarse_epoch_candidates: tuple[int, ...] = (3, 4, 5)
    coarse_monitor_size_candidates: tuple[int, ...] = (128, 256, 512, 1024)
    coarse_equivalence_mev_per_a_candidates: tuple[float, ...] = (1.0, 2.0, 4.0)
    minimum_coverage_qualified_sizes: int = 3
    maximum_coverage_qualified_sizes: int = 7
    coarse_survivor_limit: int = 4
    short_survivor_limit: int = 2
    short_training_epochs: int = 10
    final_training_epochs: int = 30
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
        short_epochs = int(self.short_training_epochs)
        final_epochs = int(self.final_training_epochs)
        if minimum < 2 or maximum < minimum:
            raise TrainingDataInputError("PERF-P2R coverage-qualified size bounds are invalid.")
        if short_limit != 2 or coarse_limit < short_limit or coarse_limit > maximum:
            raise TrainingDataInputError("PERF-P2R survivor limits are invalid.")
        if any(v >= short_epochs for v in coarse) or short_epochs >= final_epochs:
            raise TrainingDataInputError(
                "PERF-P2R requires coarse < short < final training boundaries."
            )
        object.__setattr__(self, "coarse_epoch_candidates", coarse)
        object.__setattr__(self, "coarse_monitor_size_candidates", monitors)
        object.__setattr__(self, "coarse_equivalence_mev_per_a_candidates", equivalence)
        object.__setattr__(self, "minimum_coverage_qualified_sizes", minimum)
        object.__setattr__(self, "maximum_coverage_qualified_sizes", maximum)
        object.__setattr__(self, "coarse_survivor_limit", coarse_limit)
        object.__setattr__(self, "short_survivor_limit", short_limit)
        object.__setattr__(self, "short_training_epochs", short_epochs)
        object.__setattr__(self, "final_training_epochs", final_epochs)

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
            "short_training_epochs": self.short_training_epochs,
            "final_training_epochs": self.final_training_epochs,
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
            short_training_epochs=int(payload["short_training_epochs"]),
            final_training_epochs=int(payload["final_training_epochs"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-P2R parameter-grid digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PerfP2RStagePlan:
    """One work-authorizing stage of the successive-fidelity funnel."""

    convergence_digest: str
    stage: str
    candidate_sizes: tuple[int, ...]
    start_epoch: int
    target_epoch: int
    planned_final_epoch: int
    screening_optimizer_seed: int | None
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
            "convergence_digest",
            validate_digest(self.convergence_digest, name="convergence_digest"),
        )
        stage = str(self.stage)
        if stage not in {"coarse", "short", "final", "production"}:
            raise TrainingDataInputError("Unsupported PERF-P2R execution stage.")
        sizes = tuple(sorted(set(int(v) for v in self.candidate_sizes)))
        if not sizes or any(v <= 0 for v in sizes):
            raise TrainingDataInputError("PERF-P2R stage requires positive candidate sizes.")
        start = int(self.start_epoch)
        target = int(self.target_epoch)
        final = int(self.planned_final_epoch)
        if start < 0 or target <= start or final < target:
            raise TrainingDataInputError("PERF-P2R stage epoch geometry is invalid.")
        if bool(self.continuation_required) != (start > 0):
            raise TrainingDataInputError(
                "PERF-P2R continuation flag must exactly match a nonzero start boundary."
            )
        if stage == "coarse":
            if not self.target_only_evaluation or self.replay_diagnostic_authorized or self.physical_qualification_authorized:
                raise TrainingDataInputError("PERF-P2R coarse stage must be target-only.")
        elif stage == "short":
            if self.target_only_evaluation or not self.replay_diagnostic_authorized or self.physical_qualification_authorized:
                raise TrainingDataInputError(
                    "PERF-P2R short stage permits replay diagnostics but not physical qualification."
                )
        elif stage == "final":
            if self.target_only_evaluation or not self.replay_diagnostic_authorized or not self.physical_qualification_authorized:
                raise TrainingDataInputError("PERF-P2R final stage requires full qualification evidence.")
        object.__setattr__(self, "stage", stage)
        object.__setattr__(self, "candidate_sizes", sizes)
        object.__setattr__(self, "start_epoch", start)
        object.__setattr__(self, "target_epoch", target)
        object.__setattr__(self, "planned_final_epoch", final)
        if self.screening_optimizer_seed is not None:
            object.__setattr__(self, "screening_optimizer_seed", int(self.screening_optimizer_seed))

    @property
    def incremental_epochs(self) -> int:
        return self.target_epoch - self.start_epoch

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "convergence_digest": self.convergence_digest,
            "stage": self.stage,
            "candidate_sizes": list(self.candidate_sizes),
            "start_epoch": self.start_epoch,
            "target_epoch": self.target_epoch,
            "planned_final_epoch": self.planned_final_epoch,
            "screening_optimizer_seed": self.screening_optimizer_seed,
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
            convergence_digest=str(payload["convergence_digest"]),
            stage=str(payload["stage"]),
            candidate_sizes=tuple(int(v) for v in payload["candidate_sizes"]),
            start_epoch=int(payload["start_epoch"]),
            target_epoch=int(payload["target_epoch"]),
            planned_final_epoch=int(payload["planned_final_epoch"]),
            screening_optimizer_seed=(
                None
                if payload.get("screening_optimizer_seed") is None
                else int(payload["screening_optimizer_seed"])
            ),
            continuation_required=bool(payload["continuation_required"]),
            target_only_evaluation=bool(payload["target_only_evaluation"]),
            replay_diagnostic_authorized=bool(payload["replay_diagnostic_authorized"]),
            physical_qualification_authorized=bool(payload["physical_qualification_authorized"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("PERF-P2R stage-plan digest mismatch.")
        return result


def build_perf_p2r_stage_plan(convergence: Any) -> PerfP2RStagePlan:
    """Translate current TARGET-DATA2D state into one exact work boundary."""

    outcome = str(convergence.outcome)
    policy = convergence.policy
    common = dict(
        convergence_digest=str(convergence.content_digest),
        planned_final_epoch=int(policy.final_training_epochs),
    )
    if outcome == "awaiting_stage_b0_coarse_training":
        return PerfP2RStagePlan(
            **common,
            stage="coarse",
            candidate_sizes=tuple(convergence.stage_a_survivor_sizes),
            start_epoch=0,
            target_epoch=int(policy.coarse_training_epochs),
            screening_optimizer_seed=int(policy.screening_optimizer_seed),
            continuation_required=False,
            target_only_evaluation=True,
            replay_diagnostic_authorized=False,
            physical_qualification_authorized=False,
        )
    if outcome == "awaiting_stage_b1_short_training":
        return PerfP2RStagePlan(
            **common,
            stage="short",
            candidate_sizes=tuple(convergence.stage_b_survivor_sizes),
            start_epoch=int(policy.coarse_training_epochs),
            target_epoch=int(policy.short_training_epochs),
            screening_optimizer_seed=int(policy.screening_optimizer_seed),
            continuation_required=True,
            target_only_evaluation=False,
            replay_diagnostic_authorized=True,
            physical_qualification_authorized=False,
        )
    if outcome == "awaiting_stage_c_full_training":
        return PerfP2RStagePlan(
            **common,
            stage="final",
            candidate_sizes=tuple(convergence.stage_b_finalist_sizes),
            start_epoch=int(policy.short_training_epochs),
            target_epoch=int(policy.final_training_epochs),
            screening_optimizer_seed=int(policy.screening_optimizer_seed),
            continuation_required=True,
            target_only_evaluation=False,
            replay_diagnostic_authorized=True,
            physical_qualification_authorized=True,
        )
    if outcome == "selected":
        if convergence.selected_target_size is None:
            raise TrainingDataInputError("Selected TARGET-DATA2D authority lacks a target size.")
        return PerfP2RStagePlan(
            **common,
            stage="production",
            candidate_sizes=(int(convergence.selected_target_size),),
            start_epoch=0,
            target_epoch=int(policy.final_training_epochs),
            screening_optimizer_seed=None,
            continuation_required=False,
            target_only_evaluation=False,
            replay_diagnostic_authorized=True,
            physical_qualification_authorized=True,
        )
    raise TrainingDataInputError(
        f"TARGET-DATA2D outcome {outcome!r} does not authorize PERF-P2R training work."
    )


@dataclass(frozen=True, slots=True)
class PerfP2RExposure:
    admissible_sizes: tuple[int, ...]
    coarse_survivor_sizes: tuple[int, ...]
    short_finalist_sizes: tuple[int, ...]
    coarse_training_epochs: int
    short_training_epochs: int
    final_training_epochs: int
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
            "coarse_training_epochs": self.coarse_training_epochs,
            "short_training_epochs": self.short_training_epochs,
            "final_training_epochs": self.final_training_epochs,
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
            coarse_training_epochs=int(payload["coarse_training_epochs"]),
            short_training_epochs=int(payload["short_training_epochs"]),
            final_training_epochs=int(payload["final_training_epochs"]),
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
    coarse_training_epochs: int,
    short_training_epochs: int = 10,
    final_training_epochs: int = 30,
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
    e0 = int(coarse_training_epochs)
    e1 = int(short_training_epochs)
    e2 = int(final_training_epochs)
    if e0 <= 0 or not e0 < e1 < e2:
        raise TrainingDataInputError("PERF-P2R exposure requires coarse < short < final epochs.")
    coarse_work = e0 * sum(admissible)
    short_work = (e1 - e0) * sum(coarse)
    final_work = (e2 - e1) * sum(finalists)
    total = coarse_work + short_work + final_work
    exhaustive = e2 * sum(admissible)
    saved = exhaustive - total
    if saved < 0:
        raise TrainingDataInputError("PERF-P2R exposure cannot exceed exhaustive training.")
    return PerfP2RExposure(
        admissible_sizes=admissible,
        coarse_survivor_sizes=coarse,
        short_finalist_sizes=finalists,
        coarse_training_epochs=e0,
        short_training_epochs=e1,
        final_training_epochs=e2,
        coarse_structure_epochs=coarse_work,
        short_increment_structure_epochs=short_work,
        final_increment_structure_epochs=final_work,
        total_structure_epochs=total,
        exhaustive_structure_epochs=exhaustive,
        saved_structure_epochs=saved,
        saved_fraction=(0.0 if exhaustive == 0 else saved / exhaustive),
    )
