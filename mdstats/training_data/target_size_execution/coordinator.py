"""P3-E complete-boundary coordinator, exactly-once commit, and restart.

The P2 reducer remains the sole ranking/survivor authority.  This module
carries only orchestration plumbing:

- deriving the active boundary/matrix from the real reducer state;
- recording immutable per-cell completion records (:class:`TargetSizeCellCompletionRecord`)
  binding the complete cross-boundary provenance;
- recording reconstructible per-candidate execution progress;
- building one immutable complete boundary batch (:class:`TargetSizeCompleteBoundaryBatch`)
  binding ordered cell completion record digests once the exact active matrix exists;
- applying the pure P2 reducer transition exactly once from that batch and
  publishing the crash-consistent execution head with replayable hash-chain ancestry;
- reconciling crashed/restarted state against P2 authority through full deterministic
  replay from the initial reducer state with fail-closed semantics.

Durable layout under one screen root:

    screen.json              immutable screen identity window
    completions/<epoch>/<digest>.json  immutable cell completion records
    progress/<epoch>/<key>.json        partial boundary progress (pointer)
    batches/<digest>.json    immutable complete boundary batches
    heads/<digest>.json      immutable atomic execution heads
    current_head.json        pointer alias with validated lineage
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..target_size_experiment import (
    BoundaryOutcome,
    ReducerStatus,
    TargetSizeExperimentDefinition,
    TargetSizeNumericalFailure,
    TargetSizeReducerState,
    advance_target_size_reducer,
    target_size_active_boundary_index,
    validate_target_size_reducer_state,
)
from .common import TargetSizeCommonPreparation
from .context import TargetSizeExecutionContext
from .schedule import TargetSizeScreenSchedule

TARGET_SIZE_CELL_COMPLETION_RECORD_SCHEMA = (
    "mdstats.target-size.cell-completion.v1"
)
SCREEN_WINDOW_SCHEMA = "mdstats.target-size.screen-window.v1"
SCREEN_PROGRESS_SCHEMA = "mdstats.target-size.candidate-outcome.v1"
BOUNDARY_BATCH_SCHEMA = "mdstats.target-size.boundary-batch.v1"
EXECUTION_HEAD_SCHEMA = "mdstats.target-size.execution-head.v1"

SCREEN_WINDOW_FILENAME = "screen.json"
CURRENT_HEAD_FILENAME = "current_head.json"


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=str(path.parent), suffix=".tmp"
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except OSError:
            pass
        raise


@dataclass(frozen=True, slots=True)
class TargetSizeScreenWindow:
    """Immutable identity window of one assembled screen.

    Only references/bindings to P1/P2 authority live here; P2 scientific
    state (policy, orders, reducer history) is replayed from the accepted
    owners, never duplicated.
    """

    aggregate_digest: str
    experiment_definition_digest: str
    execution_context_digest: str
    common_preparation_digest: str
    initial_reducer_digest: str

    def __post_init__(self) -> None:
        for name in (
            "aggregate_digest",
            "experiment_definition_digest",
            "execution_context_digest",
            "common_preparation_digest",
            "initial_reducer_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SCREEN_WINDOW_SCHEMA,
            "aggregate_digest": self.aggregate_digest,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "common_preparation_digest": self.common_preparation_digest,
            "initial_reducer_digest": self.initial_reducer_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeScreenWindow:
        if payload.get("schema") != SCREEN_WINDOW_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported screen-window schema."
            )
        result = cls(
            aggregate_digest=str(payload["aggregate_digest"]),
            experiment_definition_digest=str(
                payload["experiment_definition_digest"]
            ),
            execution_context_digest=str(payload["execution_context_digest"]),
            common_preparation_digest=str(payload["common_preparation_digest"]),
            initial_reducer_digest=str(payload["initial_reducer_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Screen-window digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeCellCompletionRecord:
    """Immutable per-cell completion record binding complete cross-boundary provenance."""

    window_digest: str
    experiment_definition_digest: str
    execution_context_digest: str
    common_preparation_digest: str
    trajectory_digest: str
    target_size: int
    optimizer_seed: int
    materialization_digest: str
    boundary_epoch: int
    boundary_snapshot_digest: str
    eval2_role_digest: str
    evaluation_data_digest: str
    prediction_evidence_digest: str | None
    eval2_metric_record_digest: str | None
    outcome_digest: str
    outcome: BoundaryOutcome
    failure_evidence_digest: str | None = None
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "window_digest",
            "experiment_definition_digest",
            "execution_context_digest",
            "common_preparation_digest",
            "trajectory_digest",
            "materialization_digest",
            "boundary_snapshot_digest",
            "eval2_role_digest",
            "evaluation_data_digest",
            "outcome_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.prediction_evidence_digest is not None:
            object.__setattr__(
                self,
                "prediction_evidence_digest",
                validate_digest(
                    self.prediction_evidence_digest,
                    name="prediction_evidence_digest",
                ),
            )
        if self.eval2_metric_record_digest is not None:
            object.__setattr__(
                self,
                "eval2_metric_record_digest",
                validate_digest(
                    self.eval2_metric_record_digest,
                    name="eval2_metric_record_digest",
                ),
            )
        if self.failure_evidence_digest is not None:
            object.__setattr__(
                self,
                "failure_evidence_digest",
                validate_digest(
                    self.failure_evidence_digest,
                    name="failure_evidence_digest",
                ),
            )
        for name in ("target_size", "boundary_epoch"):
            val = int(getattr(self, name))
            if val <= 0:
                raise TrainingDataInputError(
                    f"{name} must be a positive integer."
                )
            object.__setattr__(self, name, val)
        if (
            isinstance(self.optimizer_seed, bool)
            or not isinstance(self.optimizer_seed, int)
            or self.optimizer_seed < 0
        ):
            raise TrainingDataInputError(
                "optimizer_seed must be a nonnegative integer."
            )
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        if self.outcome.boundary_epoch != self.boundary_epoch:
            raise TrainingDataInputError(
                "Cell completion record outcome epoch does not match boundary."
            )
        if self.outcome.target_size != self.target_size:
            raise TrainingDataInputError(
                "Cell completion record outcome target_size mismatch."
            )
        if self.outcome.optimizer_seed != self.optimizer_seed:
            raise TrainingDataInputError(
                "Cell completion record outcome optimizer_seed mismatch."
            )
        if self.outcome.content_digest != self.outcome_digest:
            raise TrainingDataInputError(
                "Cell completion record outcome digest mismatch."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_CELL_COMPLETION_RECORD_SCHEMA,
            "window_digest": self.window_digest,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "common_preparation_digest": self.common_preparation_digest,
            "trajectory_digest": self.trajectory_digest,
            "target_size": self.target_size,
            "optimizer_seed": self.optimizer_seed,
            "materialization_digest": self.materialization_digest,
            "boundary_epoch": self.boundary_epoch,
            "boundary_snapshot_digest": self.boundary_snapshot_digest,
            "eval2_role_digest": self.eval2_role_digest,
            "evaluation_data_digest": self.evaluation_data_digest,
            "prediction_evidence_digest": self.prediction_evidence_digest,
            "eval2_metric_record_digest": self.eval2_metric_record_digest,
            "outcome_digest": self.outcome_digest,
            "outcome": self.outcome.to_dict(),
            "failure_evidence_digest": self.failure_evidence_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizeCellCompletionRecord:
        if payload.get("schema") != TARGET_SIZE_CELL_COMPLETION_RECORD_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported cell completion record schema."
            )
        outcome_payload = payload["outcome"]
        if "kind" in outcome_payload:
            outcome: BoundaryOutcome = TargetSizeNumericalFailure.from_dict(
                outcome_payload
            )
        else:
            from ..target_size_experiment import TargetSizeBoundaryMetric

            outcome = TargetSizeBoundaryMetric.from_dict(outcome_payload)
        result = cls(
            window_digest=str(payload["window_digest"]),
            experiment_definition_digest=str(
                payload["experiment_definition_digest"]
            ),
            execution_context_digest=str(payload["execution_context_digest"]),
            common_preparation_digest=str(payload["common_preparation_digest"]),
            trajectory_digest=str(payload["trajectory_digest"]),
            target_size=int(payload["target_size"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            materialization_digest=str(payload["materialization_digest"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            boundary_snapshot_digest=str(payload["boundary_snapshot_digest"]),
            eval2_role_digest=str(payload["eval2_role_digest"]),
            evaluation_data_digest=str(payload["evaluation_data_digest"]),
            prediction_evidence_digest=(
                None
                if payload.get("prediction_evidence_digest") is None
                else str(payload["prediction_evidence_digest"])
            ),
            eval2_metric_record_digest=(
                None
                if payload.get("eval2_metric_record_digest") is None
                else str(payload["eval2_metric_record_digest"])
            ),
            outcome_digest=str(payload["outcome_digest"]),
            outcome=outcome,
            failure_evidence_digest=(
                None
                if payload.get("failure_evidence_digest") is None
                else str(payload["failure_evidence_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Cell completion record digest mismatch."
            )
        return result


def build_target_size_cell_completion_record(
    *,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    materialization: Any,
    boundary_snapshot: Any,
    eval2_role: Any,
    evaluation_data: Any,
    outcome: BoundaryOutcome,
    prediction_evidence: Any | None = None,
    eval2_metric_record: Any | None = None,
    failure_evidence_digest: str | None = None,
) -> TargetSizeCellCompletionRecord:
    """Build and validate one immutable per-cell completion record."""
    if (
        trajectory.experiment_definition_digest
        != window.experiment_definition_digest
    ):
        raise TrainingDataInputError(
            "Trajectory binds a different experiment definition."
        )
    if trajectory.execution_context_digest != window.execution_context_digest:
        raise TrainingDataInputError(
            "Trajectory binds a different execution context."
        )
    if materialization.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Materialization belongs to a different trajectory."
        )
    if (
        materialization.target_train_artifact.common_preparation_digest
        != window.common_preparation_digest
    ):
        raise TrainingDataInputError(
            "Materialization binds a different common preparation."
        )
    if boundary_snapshot.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Boundary snapshot belongs to a different trajectory."
        )
    if boundary_snapshot.boundary_epoch != outcome.boundary_epoch:
        raise TrainingDataInputError(
            "Boundary snapshot epoch does not match outcome."
        )
    if eval2_role.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role belongs to a different trajectory."
        )
    if eval2_role.boundary_epoch != outcome.boundary_epoch:
        raise TrainingDataInputError("EVAL2 role epoch does not match outcome.")
    if eval2_role.target_size != trajectory.target_size:
        raise TrainingDataInputError(
            "EVAL2 role target_size does not match trajectory."
        )
    if eval2_role.optimizer_seed != trajectory.optimizer_seed:
        raise TrainingDataInputError(
            "EVAL2 role optimizer_seed does not match trajectory."
        )
    if (
        evaluation_data.experiment_definition_digest
        != window.experiment_definition_digest
    ):
        raise TrainingDataInputError(
            "Evaluation data binds a different experiment definition."
        )
    if evaluation_data.evaluation_size != eval2_role.evaluation_size:
        raise TrainingDataInputError(
            "Evaluation data size does not match EVAL2 role."
        )
    if (
        evaluation_data.evaluation_membership_digest
        != eval2_role.evaluation_membership_digest
    ):
        raise TrainingDataInputError(
            "Evaluation data membership digest does not match EVAL2 role."
        )
    pred_digest = None
    if prediction_evidence is not None:
        if prediction_evidence.role_digest != eval2_role.content_digest:
            raise TrainingDataInputError(
                "Prediction evidence does not bind this EVAL2 role."
            )
        if (
            prediction_evidence.evaluation_data_digest
            != evaluation_data.content_digest
        ):
            raise TrainingDataInputError(
                "Prediction evidence binds a different evaluation data authority."
            )
        pred_digest = prediction_evidence.content_digest
    metric_digest = None
    if eval2_metric_record is not None:
        if eval2_metric_record.target_role_digest != eval2_role.content_digest:
            raise TrainingDataInputError(
                "EVAL2 metric record does not bind this EVAL2 role."
            )
        metric_digest = eval2_metric_record.content_digest
    fail_digest = failure_evidence_digest
    if fail_digest is None and isinstance(outcome, TargetSizeNumericalFailure):
        fail_digest = outcome.classification_evidence_digest

    return TargetSizeCellCompletionRecord(
        window_digest=window.content_digest,
        experiment_definition_digest=window.experiment_definition_digest,
        execution_context_digest=window.execution_context_digest,
        common_preparation_digest=window.common_preparation_digest,
        trajectory_digest=trajectory.content_digest,
        target_size=trajectory.target_size,
        optimizer_seed=trajectory.optimizer_seed,
        materialization_digest=materialization.content_digest,
        boundary_epoch=outcome.boundary_epoch,
        boundary_snapshot_digest=boundary_snapshot.content_digest,
        eval2_role_digest=eval2_role.content_digest,
        evaluation_data_digest=evaluation_data.content_digest,
        prediction_evidence_digest=pred_digest,
        eval2_metric_record_digest=metric_digest,
        outcome_digest=outcome.content_digest,
        outcome=outcome,
        failure_evidence_digest=fail_digest,
    )


@dataclass(frozen=True, slots=True)
class TargetSizeCandidateOutcome:
    """One authenticated per-candidate boundary outcome.

    Work-unit/trajectory evidence — a worker may publish such a record, but a
    worker can never invoke or mutate P2 reducer state; only the boundary
    batch/commit path consumes these records.
    """

    window_digest: str
    boundary_epoch: int
    trajectory_digest: str
    completion_record_digest: str
    outcome: BoundaryOutcome

    def __post_init__(self) -> None:
        for name in (
            "window_digest",
            "trajectory_digest",
            "completion_record_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        epoch = int(self.boundary_epoch)
        if epoch <= 0:
            raise TrainingDataInputError(
                "Progress boundary epoch must be positive."
            )
        object.__setattr__(self, "boundary_epoch", epoch)
        if self.outcome.boundary_epoch != epoch:
            raise TrainingDataInputError(
                "Candidate outcome epoch does not match the progress boundary."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SCREEN_PROGRESS_SCHEMA,
            "window_digest": self.window_digest,
            "boundary_epoch": self.boundary_epoch,
            "trajectory_digest": self.trajectory_digest,
            "completion_record_digest": self.completion_record_digest,
            "outcome": self.outcome.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizeCandidateOutcome:
        if payload.get("schema") != SCREEN_PROGRESS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported progress schema.")
        outcome_payload = payload["outcome"]
        if "kind" in outcome_payload:
            outcome: BoundaryOutcome = TargetSizeNumericalFailure.from_dict(
                outcome_payload
            )
        else:
            from ..target_size_experiment import TargetSizeBoundaryMetric

            outcome = TargetSizeBoundaryMetric.from_dict(outcome_payload)
        completion_digest = payload.get("completion_record_digest")
        if completion_digest is None:
            raise TrainingDataSerializationError(
                "Progress record is missing completion_record_digest."
            )
        result = cls(
            window_digest=str(payload["window_digest"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            trajectory_digest=str(payload["trajectory_digest"]),
            completion_record_digest=str(completion_digest),
            outcome=outcome,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Progress digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeCompleteBoundaryBatch:
    """One immutable complete ordered boundary matrix.

    Created only after the exact active matrix exists; the batch binds the
    pre-transition reducer identity so a later conflicting batch against the
    same pre-state is rejected as conflicting scientific evidence.
    """

    pre_state_digest: str
    experiment_definition_digest: str
    execution_context_digest: str
    boundary_epoch: int
    evaluation_membership_digest: str
    active_candidate_sizes: tuple[int, ...]
    optimizer_seeds: tuple[int, ...]
    completion_record_digests: tuple[str, ...]
    outcomes: tuple[BoundaryOutcome, ...]

    def __post_init__(self) -> None:
        for name in (
            "pre_state_digest",
            "experiment_definition_digest",
            "execution_context_digest",
            "evaluation_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        epoch = int(self.boundary_epoch)
        if epoch <= 0:
            raise TrainingDataInputError(
                "Batch boundary epoch must be positive."
            )
        object.__setattr__(self, "boundary_epoch", epoch)
        sizes = tuple(int(v) for v in self.active_candidate_sizes)
        seeds = tuple(int(v) for v in self.optimizer_seeds)
        records = tuple(
            validate_digest(v, name="completion record digest")
            for v in self.completion_record_digests
        )
        outcomes = tuple(self.outcomes)
        expected_len = len(sizes) * len(seeds)
        if len(records) != expected_len or len(outcomes) != expected_len:
            raise TrainingDataInputError(
                "Complete boundary batch completion records and outcomes count "
                f"must equal active matrix count ({expected_len})."
            )
        expected = tuple((size, seed) for size in sizes for seed in seeds)
        observed = tuple(
            (item.target_size, item.optimizer_seed) for item in outcomes
        )
        if observed != expected:
            raise TrainingDataInputError(
                "Complete boundary batch must follow the exact P2 "
                "size-major/seed-minor ordered matrix."
            )
        if len(
            {(item.target_size, item.optimizer_seed) for item in outcomes}
        ) != len(outcomes):
            raise TrainingDataInputError(
                "Complete boundary batch contains duplicates."
            )
        for outcome in outcomes:
            if (
                outcome.experiment_definition_digest
                != self.experiment_definition_digest
                or outcome.execution_context_digest
                != self.execution_context_digest
                or outcome.boundary_epoch != epoch
                or outcome.evaluation_membership_digest
                != self.evaluation_membership_digest
            ):
                raise TrainingDataInputError(
                    "Complete boundary batch carries out-of-batch lineage."
                )
        object.__setattr__(self, "active_candidate_sizes", sizes)
        object.__setattr__(self, "optimizer_seeds", seeds)
        object.__setattr__(self, "completion_record_digests", records)
        object.__setattr__(self, "outcomes", outcomes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BOUNDARY_BATCH_SCHEMA,
            "pre_state_digest": self.pre_state_digest,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_membership_digest": self.evaluation_membership_digest,
            "active_candidate_sizes": list(self.active_candidate_sizes),
            "optimizer_seeds": list(self.optimizer_seeds),
            "completion_record_digests": list(self.completion_record_digests),
            "outcomes": [item.to_dict() for item in self.outcomes],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizeCompleteBoundaryBatch:
        if payload.get("schema") != BOUNDARY_BATCH_SCHEMA:
            raise TrainingDataSerializationError("Unsupported batch schema.")
        if "completion_record_digests" not in payload:
            raise TrainingDataSerializationError(
                "Batch payload missing completion_record_digests."
            )
        return _rehydrate_batch(payload)


def _rehydrate_modules() -> Any:
    from ..target_size_experiment import TargetSizeBoundaryMetric

    return TargetSizeBoundaryMetric


def _rehydrate_batch(
    payload: Mapping[str, Any], *, validate_content_digest: bool = True
) -> TargetSizeCompleteBoundaryBatch:
    metric_kind = _rehydrate_modules()
    outcomes = tuple(
        TargetSizeNumericalFailure.from_dict(item)
        if "kind" in item
        else metric_kind.from_dict(item)
        for item in payload["outcomes"]
    )
    records = tuple(str(v) for v in payload["completion_record_digests"])
    result = TargetSizeCompleteBoundaryBatch(
        pre_state_digest=str(payload["pre_state_digest"]),
        experiment_definition_digest=str(
            payload["experiment_definition_digest"]
        ),
        execution_context_digest=str(payload["execution_context_digest"]),
        boundary_epoch=int(payload["boundary_epoch"]),
        evaluation_membership_digest=str(
            payload["evaluation_membership_digest"]
        ),
        active_candidate_sizes=tuple(
            int(v) for v in payload["active_candidate_sizes"]
        ),
        optimizer_seeds=tuple(int(v) for v in payload["optimizer_seeds"]),
        completion_record_digests=records,
        outcomes=outcomes,
    )
    if validate_content_digest and payload.get("content_digest") not in (
        None,
        result.content_digest,
    ):
        raise TrainingDataSerializationError("Boundary batch digest mismatch.")
    return result


def load_target_size_boundary_batch(
    payload: Mapping[str, Any],
) -> TargetSizeCompleteBoundaryBatch:
    return TargetSizeCompleteBoundaryBatch.from_dict(payload)


@dataclass(frozen=True, slots=True)
class TargetSizeExecutionHead:
    """Atomic execution head committing one complete boundary batch."""

    parent_head_digest: str | None
    batch_digest: str
    pre_state_digest: str
    post_state_digest: str
    pre_state: TargetSizeReducerState
    post_state: TargetSizeReducerState

    def __post_init__(self) -> None:
        if self.parent_head_digest is not None:
            object.__setattr__(
                self,
                "parent_head_digest",
                validate_digest(
                    self.parent_head_digest, name="parent_head_digest"
                ),
            )
        for name in ("batch_digest", "pre_state_digest", "post_state_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.pre_state.content_digest != self.pre_state_digest:
            raise TrainingDataInputError("Head pre-state digest mismatch.")
        if self.post_state.content_digest != self.post_state_digest:
            raise TrainingDataInputError("Head post-state digest mismatch.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EXECUTION_HEAD_SCHEMA,
            "parent_head_digest": self.parent_head_digest,
            "batch_digest": self.batch_digest,
            "pre_state_digest": self.pre_state_digest,
            "post_state_digest": self.post_state_digest,
            "pre_state": self.pre_state.to_dict(),
            "post_state": self.post_state.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeExecutionHead:
        if payload.get("schema") != EXECUTION_HEAD_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported execution-head schema."
            )
        parent_digest = (
            None
            if payload.get("parent_head_digest") is None
            else str(payload["parent_head_digest"])
        )
        result = cls(
            parent_head_digest=parent_digest,
            batch_digest=str(payload["batch_digest"]),
            pre_state_digest=str(payload["pre_state_digest"]),
            post_state_digest=str(payload["post_state_digest"]),
            pre_state=TargetSizeReducerState.from_dict(payload["pre_state"]),
            post_state=TargetSizeReducerState.from_dict(payload["post_state"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Execution-head digest mismatch."
            )
        return result


def initialize_target_size_screen(
    root: str | Path,
    aggregate: Any,
    context: TargetSizeExecutionContext,
    common: TargetSizeCommonPreparation,
) -> TargetSizeScreenWindow:
    """Create the immutable screen window; fails if a differing window exists."""

    window = TargetSizeScreenWindow(
        aggregate_digest=aggregate.content_digest,
        experiment_definition_digest=aggregate.definition.content_digest,
        execution_context_digest=context.content_digest,
        common_preparation_digest=common.content_digest,
        initial_reducer_digest=aggregate.reducer_state.content_digest,
    )
    path = Path(root) / SCREEN_WINDOW_FILENAME
    if path.is_file():
        existing = TargetSizeScreenWindow.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        if existing.content_digest != window.content_digest:
            raise TrainingDataInputError(
                "Screen root already binds different P1/P2 authority identity."
            )
        return existing
    _atomic_json_write(path, window.to_dict())
    return window


def derive_active_boundary_requirements(
    definition: TargetSizeExperimentDefinition, state: TargetSizeReducerState
) -> tuple[int, int, tuple[tuple[int, int], ...]] | None:
    """Active (boundary epoch, M size, ordered matrix keys) or None if terminal."""

    if state.is_terminal:
        return None
    index = target_size_active_boundary_index(state.status)
    boundary_epoch = definition.policy.fidelity_epochs[index]
    evaluation_size = definition.policy.evaluation_sizes[index]
    keys = tuple(
        (size, seed)
        for size in state.active_candidate_sizes
        for seed in definition.policy.optimizer_seeds
    )
    return boundary_epoch, evaluation_size, keys


def build_complete_boundary_batch(
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    completion_records: Sequence[TargetSizeCellCompletionRecord],
) -> TargetSizeCompleteBoundaryBatch:
    """Create the immutable batch only when the exact active matrix exists."""

    requirements = derive_active_boundary_requirements(definition, state)
    if requirements is None:
        raise TrainingDataInputError(
            "Reducer is terminal; no boundary batch may be created."
        )
    boundary_epoch, evaluation_size, keys = requirements
    membership_digest = definition.evaluation_order.membership_digest(
        evaluation_size
    )
    records = tuple(completion_records)
    observed = tuple((r.target_size, r.optimizer_seed) for r in records)
    if observed != keys:
        raise TrainingDataInputError(
            "Cell completion records do not form the exact active matrix."
        )
    for r in records:
        if r.boundary_epoch != boundary_epoch:
            raise TrainingDataInputError(
                "Cell completion record belongs to a different boundary epoch."
            )
        if r.experiment_definition_digest != definition.content_digest:
            raise TrainingDataInputError(
                "Cell completion record binds a different experiment definition."
            )
        if r.outcome.boundary_epoch != boundary_epoch:
            raise TrainingDataInputError(
                "Cell completion record outcome belongs to a different boundary epoch."
            )
    return TargetSizeCompleteBoundaryBatch(
        pre_state_digest=state.content_digest,
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=(
            state.execution_context_digest
            if state.execution_context_digest is not None
            else "0" * 64
        ),
        boundary_epoch=boundary_epoch,
        evaluation_membership_digest=membership_digest,
        active_candidate_sizes=state.active_candidate_sizes,
        optimizer_seeds=definition.policy.optimizer_seeds,
        completion_record_digests=tuple(r.content_digest for r in records),
        outcomes=tuple(r.outcome for r in records),
    )


def _candidate_outcome_path(
    root: Path,
    window_digest: str,
    boundary_epoch: int,
    record: TargetSizeCandidateOutcome,
) -> Path:
    key = digest(
        {
            "schema": "mdstats.target-size.candidate-outcome-key.v1",
            "window_digest": window_digest,
            "boundary_epoch": boundary_epoch,
            "target_size": record.outcome.target_size,
            "optimizer_seed": record.outcome.optimizer_seed,
        }
    )
    return root / "progress" / str(boundary_epoch) / f"{key}.json"


def record_candidate_boundary_outcome(
    root: str | Path,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    completion_record: TargetSizeCellCompletionRecord,
) -> TargetSizeCandidateOutcome:
    """Publish one content-addressed completion record and progress outcome."""

    if completion_record.window_digest != window.content_digest:
        raise TrainingDataInputError(
            "Completion record belongs to a different screen window."
        )
    if completion_record.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Completion record belongs to a different trajectory."
        )
    root_path = Path(root)
    comp_dir = root_path / "completions" / str(completion_record.boundary_epoch)
    comp_path = comp_dir / f"{completion_record.content_digest}.json"
    if not comp_path.is_file():
        _atomic_json_write(comp_path, completion_record.to_dict())
    else:
        existing_comp = TargetSizeCellCompletionRecord.from_dict(
            json.loads(comp_path.read_text(encoding="utf-8"))
        )
        if existing_comp.content_digest != completion_record.content_digest:
            raise TrainingDataInputError(
                "Conflicting completion record at same path."
            )

    progress = TargetSizeCandidateOutcome(
        window_digest=window.content_digest,
        boundary_epoch=completion_record.boundary_epoch,
        trajectory_digest=trajectory.content_digest,
        completion_record_digest=completion_record.content_digest,
        outcome=completion_record.outcome,
    )
    progress_path = _candidate_outcome_path(
        root_path, window.content_digest, progress.boundary_epoch, progress
    )
    if progress_path.is_file():
        existing = TargetSizeCandidateOutcome.from_dict(
            json.loads(progress_path.read_text(encoding="utf-8"))
        )
        if existing.content_digest != progress.content_digest:
            raise TrainingDataInputError(
                "Conflicting outcome for the same candidate/boundary position."
            )
        return existing
    _atomic_json_write(progress_path, progress.to_dict())
    return progress


def collect_boundary_cell_completion_records(
    root: str | Path,
    window: TargetSizeScreenWindow,
    *,
    boundary_epoch: int,
) -> tuple[TargetSizeCellCompletionRecord, ...]:
    """Collect all cell completion records for the active boundary in size-major/seed-minor order."""

    root_path = Path(root)
    progress_dir = root_path / "progress" / str(boundary_epoch)
    if not progress_dir.is_dir():
        return ()
    completions: list[TargetSizeCellCompletionRecord] = []
    for p_path in sorted(progress_dir.glob("*.json")):
        prog = TargetSizeCandidateOutcome.from_dict(
            json.loads(p_path.read_text(encoding="utf-8"))
        )
        if prog.window_digest != window.content_digest:
            raise TrainingDataInputError(
                "Progress record belongs to a different screen window."
            )
        if prog.boundary_epoch != int(boundary_epoch):
            raise TrainingDataInputError(
                "Progress record belongs to a different boundary epoch."
            )
        comp_file = (
            root_path
            / "completions"
            / str(boundary_epoch)
            / f"{prog.completion_record_digest}.json"
        )
        if not comp_file.is_file():
            raise TrainingDataInputError(
                f"Referenced cell completion record is missing: {comp_file}"
            )
        comp = TargetSizeCellCompletionRecord.from_dict(
            json.loads(comp_file.read_text(encoding="utf-8"))
        )
        if comp.content_digest != prog.completion_record_digest:
            raise TrainingDataInputError(
                "Cell completion record digest mismatch."
            )
        completions.append(comp)
    completions.sort(key=lambda item: (item.target_size, item.optimizer_seed))
    return tuple(completions)


def collect_boundary_candidate_outcomes(
    root: str | Path,
    window: TargetSizeScreenWindow,
    *,
    boundary_epoch: int,
) -> tuple[BoundaryOutcome, ...]:
    """Collect the partial matrix in P2 size-major/seed-minor order."""

    records = collect_boundary_cell_completion_records(
        root, window, boundary_epoch=boundary_epoch
    )
    return tuple(record.outcome for record in records)


def _batch_path(root: Path, content_digest: str) -> Path:
    return root / "batches" / f"{content_digest}.json"


def _head_path(root: Path, content_digest: str) -> Path:
    return root / "heads" / f"{content_digest}.json"


def persist_complete_boundary_batch(
    root: str | Path, batch: TargetSizeCompleteBoundaryBatch
) -> Path:
    path = _batch_path(Path(root), batch.content_digest)
    if not path.is_file():
        _atomic_json_write(path, batch.to_dict())
    else:
        existing = TargetSizeCompleteBoundaryBatch.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        if existing.content_digest != batch.content_digest:
            raise TrainingDataInputError(
                "Conflicting batch persisted at same path."
            )
    return path


def apply_complete_boundary_batch(
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    batch: TargetSizeCompleteBoundaryBatch,
) -> TargetSizeReducerState:
    """Apply the pure reducer transition exactly once through the real owner."""

    if batch.pre_state_digest != state.content_digest:
        raise TrainingDataInputError(
            "Boundary batch does not bind the current reducer pre-state."
        )
    if batch.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Boundary batch binds a different experiment definition."
        )
    if (
        batch.execution_context_digest
        != (state.execution_context_digest or "0" * 64)
        or tuple(batch.active_candidate_sizes)
        != tuple(state.active_candidate_sizes)
        or tuple(batch.optimizer_seeds)
        != tuple(definition.policy.optimizer_seeds)
    ):
        raise TrainingDataInputError(
            "Boundary batch lineage diverges from P2 state."
        )
    post_state = advance_target_size_reducer(definition, state, batch.outcomes)
    return post_state


def commit_target_size_boundary_batch(
    root: str | Path,
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    batch: TargetSizeCompleteBoundaryBatch,
) -> TargetSizeExecutionHead:
    """Persist batch first, apply deterministically, publish head atomically."""

    root_path = Path(root)
    current_path = root_path / CURRENT_HEAD_FILENAME
    parent_head_digest = None
    if current_path.is_file():
        current = TargetSizeExecutionHead.from_dict(
            json.loads(current_path.read_text(encoding="utf-8"))
        )
        if current.post_state_digest != batch.pre_state_digest:
            raise TrainingDataInputError(
                "Current head does not provide this batch's exact pre-state."
            )
        parent_head_digest = current.content_digest
    else:
        if batch.pre_state_digest != state.content_digest:
            raise TrainingDataInputError(
                "Initial batch does not bind the current pre-state."
            )

    persist_complete_boundary_batch(root_path, batch)
    post_state = apply_complete_boundary_batch(definition, state, batch)
    head = TargetSizeExecutionHead(
        parent_head_digest=parent_head_digest,
        batch_digest=batch.content_digest,
        pre_state_digest=state.content_digest,
        post_state_digest=post_state.content_digest,
        pre_state=state,
        post_state=post_state,
    )
    head_path = _head_path(root_path, head.content_digest)
    if head_path.is_file():
        existing = TargetSizeExecutionHead.from_dict(
            json.loads(head_path.read_text(encoding="utf-8"))
        )
        if existing.content_digest != head.content_digest:
            raise TrainingDataInputError(
                "Existing head conflicts with computed head."
            )
    else:
        _atomic_json_write(head_path, head.to_dict())
    _atomic_json_write(current_path, head.to_dict())
    return head


def load_current_execution_head(
    root: str | Path,
) -> TargetSizeExecutionHead | None:
    path = Path(root) / CURRENT_HEAD_FILENAME
    if not path.is_file():
        return None
    return TargetSizeExecutionHead.from_dict(
        json.loads(path.read_text(encoding="utf-8"))
    )


def reconcile_target_size_screen_root(
    root: str | Path,
    aggregate: Any,
    context: TargetSizeExecutionContext,
    common: TargetSizeCommonPreparation,
) -> TargetSizeExecutionHead | None:
    """Crash-safe restart reconciliation through pure deterministic replay from initial state."""

    root_path = Path(root)
    window_path = root_path / SCREEN_WINDOW_FILENAME
    if not window_path.is_file():
        return None
    window = TargetSizeScreenWindow.from_dict(
        json.loads(window_path.read_text(encoding="utf-8"))
    )
    if (
        window.aggregate_digest != aggregate.content_digest
        or window.experiment_definition_digest
        != aggregate.definition.content_digest
        or window.execution_context_digest != context.content_digest
        or window.common_preparation_digest != common.content_digest
        or window.initial_reducer_digest
        != aggregate.reducer_state.content_digest
    ):
        raise TrainingDataInputError(
            "Screen window does not bind the current P1/P2 authority identity."
        )

    definition = aggregate.definition
    replayed_state = aggregate.reducer_state
    current_head = load_current_execution_head(root_path)

    if current_head is not None:
        chain: list[TargetSizeExecutionHead] = [current_head]
        curr = current_head
        visited = {curr.content_digest}
        while curr.parent_head_digest is not None:
            parent_file = _head_path(root_path, curr.parent_head_digest)
            if not parent_file.is_file():
                raise TrainingDataInputError(
                    "Execution head is missing its parent head ancestry."
                )
            parent = TargetSizeExecutionHead.from_dict(
                json.loads(parent_file.read_text(encoding="utf-8"))
            )
            if parent.content_digest in visited:
                raise TrainingDataInputError(
                    "Ancestry loop detected in execution heads."
                )
            visited.add(parent.content_digest)
            chain.append(parent)
            curr = parent
        chain.reverse()

        for head in chain:
            if head.pre_state_digest != replayed_state.content_digest:
                raise TrainingDataInputError(
                    "Execution head pre-state digest does not match replayed reducer state."
                )
            batch_path = _batch_path(root_path, head.batch_digest)
            if not batch_path.is_file():
                raise TrainingDataInputError(
                    "Execution head is missing its complete batch ancestry."
                )
            batch = TargetSizeCompleteBoundaryBatch.from_dict(
                json.loads(batch_path.read_text(encoding="utf-8"))
            )
            if batch.pre_state_digest != replayed_state.content_digest:
                raise TrainingDataInputError(
                    "Complete batch pre-state digest does not match replayed reducer state."
                )
            for comp_digest in batch.completion_record_digests:
                comp_file = (
                    root_path
                    / "completions"
                    / str(batch.boundary_epoch)
                    / f"{comp_digest}.json"
                )
                if not comp_file.is_file():
                    raise TrainingDataInputError(
                        f"Batch completion record is missing: {comp_file}"
                    )
                record = TargetSizeCellCompletionRecord.from_dict(
                    json.loads(comp_file.read_text(encoding="utf-8"))
                )
                if record.window_digest != window.content_digest:
                    raise TrainingDataInputError(
                        "Completion record belongs to a different screen window."
                    )
            post_state = apply_complete_boundary_batch(
                definition, replayed_state, batch
            )
            if post_state.content_digest != head.post_state_digest:
                raise TrainingDataInputError(
                    "Replayed reducer post-state does not match committed execution head."
                )
            replayed_state = post_state

        if (
            replayed_state.content_digest
            != current_head.post_state.content_digest
        ):
            raise TrainingDataInputError(
                "Full replay diverged from current execution head post-state."
            )
        head_result = current_head
    else:
        head_result = None

    batches_dir = root_path / "batches"
    if batches_dir.is_dir():
        all_batches: list[TargetSizeCompleteBoundaryBatch] = []
        for path in sorted(batches_dir.glob("*.json")):
            all_batches.append(
                TargetSizeCompleteBoundaryBatch.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            )
        batch_by_pre: dict[str, set[str]] = {}
        for batch in all_batches:
            batch_by_pre.setdefault(batch.pre_state_digest, set()).add(
                batch.content_digest
            )
        if any(len(digests) > 1 for digests in batch_by_pre.values()):
            raise TrainingDataInputError(
                "Conflicting complete batches claim one pre-state: "
                "conflicting scientific evidence."
            )
        while True:
            candidates = [
                b
                for b in all_batches
                if b.pre_state_digest == replayed_state.content_digest
            ]
            if len(candidates) > 1:
                raise TrainingDataInputError(
                    "Two complete batches claim the same pre-state: "
                    "conflicting scientific evidence."
                )
            if not candidates:
                break
            head_result = commit_target_size_boundary_batch(
                root_path, definition, replayed_state, candidates[0]
            )
            replayed_state = head_result.post_state

    return head_result


__all__ = [
    "BOUNDARY_BATCH_SCHEMA",
    "CURRENT_HEAD_FILENAME",
    "EXECUTION_HEAD_SCHEMA",
    "SCREEN_PROGRESS_SCHEMA",
    "SCREEN_WINDOW_FILENAME",
    "SCREEN_WINDOW_SCHEMA",
    "TARGET_SIZE_CELL_COMPLETION_RECORD_SCHEMA",
    "TargetSizeCandidateOutcome",
    "TargetSizeCellCompletionRecord",
    "TargetSizeCompleteBoundaryBatch",
    "TargetSizeExecutionHead",
    "TargetSizeScreenWindow",
    "apply_complete_boundary_batch",
    "build_complete_boundary_batch",
    "build_target_size_cell_completion_record",
    "collect_boundary_candidate_outcomes",
    "collect_boundary_cell_completion_records",
    "commit_target_size_boundary_batch",
    "derive_active_boundary_requirements",
    "initialize_target_size_screen",
    "load_current_execution_head",
    "load_target_size_boundary_batch",
    "persist_complete_boundary_batch",
    "reconcile_target_size_screen_root",
    "record_candidate_boundary_outcome",
]
