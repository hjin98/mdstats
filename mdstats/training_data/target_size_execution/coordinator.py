"""P3-E complete-boundary coordinator, exactly-once commit, and restart.

The P2 reducer remains the sole ranking/survivor authority.  This module
carries only orchestration plumbing:

- deriving the active boundary/matrix from the real reducer state;
- recording reconstructible per-candidate execution progress (which is never
  reducer evidence);
- building one immutable complete boundary batch once the exact active
  matrix exists;
- applying the pure P2 reducer transition exactly once from that batch and
  publishing the crash-consistent execution head;
- reconciling crashed/restarted state against P2 authority with fail-closed
  semantics.

Parallel workers may submit authenticated per-trajectory outcomes; they can
never invoke the reducer.  Only :func:`commit_target_size_boundary_batch`
touches reducer state.

Durable layout under one screen root:

    screen.json              immutable screen identity window
    progress/outcomes.json   partial boundary progress (execution-only)
    batches/<digest>.json    immutable complete boundary batches
    heads/<digest>.json      immutable atomic execution heads
    current_head.json        pointer alias with validated lineage

Every file is written through the same atomic-commit protocol; reopening a
screen root reconciles deterministically to a state the P2 owners can
fully re-derive.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
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
            raise TrainingDataSerializationError("Unsupported screen-window schema.")
        result = cls(
            aggregate_digest=str(payload["aggregate_digest"]),
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            execution_context_digest=str(payload["execution_context_digest"]),
            common_preparation_digest=str(payload["common_preparation_digest"]),
            initial_reducer_digest=str(payload["initial_reducer_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Screen-window digest mismatch.")
        return result


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
    outcome: BoundaryOutcome

    def __post_init__(self) -> None:
        for name in ("window_digest", "trajectory_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        epoch = int(self.boundary_epoch)
        if epoch <= 0:
            raise TrainingDataInputError("Progress boundary epoch must be positive.")
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
            "outcome": self.outcome.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCandidateOutcome:
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
        result = cls(
            window_digest=str(payload["window_digest"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            trajectory_digest=str(payload["trajectory_digest"]),
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
            raise TrainingDataInputError("Batch boundary epoch must be positive.")
        object.__setattr__(self, "boundary_epoch", epoch)
        sizes = tuple(int(v) for v in self.active_candidate_sizes)
        seeds = tuple(int(v) for v in self.optimizer_seeds)
        outcomes = tuple(self.outcomes)
        expected = tuple(
            (size, seed) for size in sizes for seed in seeds
        )
        observed = tuple(
            (item.target_size, item.optimizer_seed) for item in outcomes
        )
        if observed != expected:
            raise TrainingDataInputError(
                "Complete boundary batch must follow the exact P2 "
                "size-major/seed-minor ordered matrix."
            )
        if len({(item.target_size, item.optimizer_seed) for item in outcomes}) != len(outcomes):
            raise TrainingDataInputError("Complete boundary batch contains duplicates.")
        for outcome in outcomes:
            if (
                outcome.experiment_definition_digest
                != self.experiment_definition_digest
                or outcome.execution_context_digest != self.execution_context_digest
                or outcome.boundary_epoch != epoch
                or outcome.evaluation_membership_digest
                != self.evaluation_membership_digest
            ):
                raise TrainingDataInputError(
                    "Complete boundary batch carries out-of-batch lineage."
                )
        object.__setattr__(self, "active_candidate_sizes", sizes)
        object.__setattr__(self, "optimizer_seeds", seeds)
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
            "outcomes": [item.to_dict() for item in self.outcomes],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCompleteBoundaryBatch:
        if payload.get("schema") != BOUNDARY_BATCH_SCHEMA:
            raise TrainingDataSerializationError("Unsupported batch schema.")
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
    result = TargetSizeCompleteBoundaryBatch(
        pre_state_digest=str(payload["pre_state_digest"]),
        experiment_definition_digest=str(payload["experiment_definition_digest"]),
        execution_context_digest=str(payload["execution_context_digest"]),
        boundary_epoch=int(payload["boundary_epoch"]),
        evaluation_membership_digest=str(payload["evaluation_membership_digest"]),
        active_candidate_sizes=tuple(int(v) for v in payload["active_candidate_sizes"]),
        optimizer_seeds=tuple(int(v) for v in payload["optimizer_seeds"]),
        outcomes=outcomes,
    )
    if validate_content_digest and payload.get("content_digest") not in (
        None,
        result.content_digest,
    ):
        raise TrainingDataSerializationError("Boundary batch digest mismatch.")
    return result


def load_target_size_boundary_batch(payload: Mapping[str, Any]) -> TargetSizeCompleteBoundaryBatch:
    return TargetSizeCompleteBoundaryBatch.from_dict(payload)


@dataclass(frozen=True, slots=True)
class TargetSizeExecutionHead:
    """Atomic execution head committing one complete boundary batch."""

    batch_digest: str
    pre_state_digest: str
    post_state_digest: str
    pre_state: TargetSizeReducerState
    post_state: TargetSizeReducerState

    def __post_init__(self) -> None:
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
            raise TrainingDataSerializationError("Unsupported execution-head schema.")
        result = cls(
            batch_digest=str(payload["batch_digest"]),
            pre_state_digest=str(payload["pre_state_digest"]),
            post_state_digest=str(payload["post_state_digest"]),
            pre_state=TargetSizeReducerState.from_dict(payload["pre_state"]),
            post_state=TargetSizeReducerState.from_dict(payload["post_state"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Execution-head digest mismatch.")
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
    outcomes: Sequence[BoundaryOutcome],
) -> TargetSizeCompleteBoundaryBatch:
    """Create the immutable batch only when the exact active matrix exists.

    Anything short of exactly the active matrix (partial, reordered,
    duplicate, foreign-seed) is rejected: the reducer is never consulted
    on a partial matrix.
    """

    requirements = derive_active_boundary_requirements(definition, state)
    if requirements is None:
        raise TrainingDataInputError(
            "Reducer is terminal; no boundary batch may be created."
        )
    boundary_epoch, evaluation_size, keys = requirements
    membership_digest = definition.evaluation_order.membership_digest(evaluation_size)
    observed = tuple((o.target_size, o.optimizer_seed) for o in outcomes)
    if observed != keys:
        raise TrainingDataInputError(
            "Boundary outcomes do not form the exact active matrix."
        )
    return TargetSizeCompleteBoundaryBatch(
        pre_state_digest=state.content_digest,
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=state.execution_context_digest
        if state.execution_context_digest is not None
        else "0" * 64,
        boundary_epoch=boundary_epoch,
        evaluation_membership_digest=membership_digest,
        active_candidate_sizes=state.active_candidate_sizes,
        optimizer_seeds=definition.policy.optimizer_seeds,
        outcomes=tuple(outcomes),
    )


def _candidate_outcome_path(
    root: Path, window_digest: str, boundary_epoch: int, record: TargetSizeCandidateOutcome
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
    outcome: BoundaryOutcome,
) -> None:
    """Publish one content-addressed per-candidate outcome (worker-safe).

    Distinct candidates write distinct paths, so concurrent workers never
    overwrite each other; identical re-submissions are idempotent while a
    diverging outcome for the same (N, seed, boundary) is rejected.  None of
    these records is reducer evidence until the complete batch exists.
    """

    record = TargetSizeCandidateOutcome(
        window_digest=window.content_digest,
        boundary_epoch=outcome.boundary_epoch,
        trajectory_digest=trajectory.content_digest,
        outcome=outcome,
    )
    path = _candidate_outcome_path(
        Path(root), window.content_digest, record.boundary_epoch, record
    )
    if path.is_file():
        existing = TargetSizeCandidateOutcome.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        if existing.content_digest != record.content_digest:
            raise TrainingDataInputError(
                "Conflicting outcome for the same candidate/boundary position."
            )
        return
    _atomic_json_write(path, record.to_dict())


def collect_boundary_candidate_outcomes(
    root: str | Path,
    window: TargetSizeScreenWindow,
    *,
    boundary_epoch: int,
) -> tuple[BoundaryOutcome, ...]:
    """Collect the partial matrix in P2 size-major/seed-minor order."""

    directory = Path(root) / "progress" / str(boundary_epoch)
    if not directory.is_dir():
        return ()
    records: list[TargetSizeCandidateOutcome] = []
    for path in sorted(directory.glob("*.json")):
        record = TargetSizeCandidateOutcome.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        if record.window_digest != window.content_digest:
            raise TrainingDataInputError(
                "Progress record belongs to a different screen window."
            )
        if record.boundary_epoch != int(boundary_epoch):
            raise TrainingDataInputError(
                "Progress record belongs to a different boundary."
            )
        records.append(record)
    records.sort(key=lambda item: (item.outcome.target_size, item.outcome.optimizer_seed))
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
            raise TrainingDataInputError("Conflicting batch persisted at same path.")
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
        batch.execution_context_digest != (state.execution_context_digest or "0" * 64)
        or tuple(batch.active_candidate_sizes) != tuple(state.active_candidate_sizes)
        or tuple(batch.optimizer_seeds) != tuple(definition.policy.optimizer_seeds)
    ):
        raise TrainingDataInputError("Boundary batch lineage diverges from P2 state.")
    post_state = advance_target_size_reducer(definition, state, batch.outcomes)
    return post_state


def commit_target_size_boundary_batch(
    root: str | Path,
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    batch: TargetSizeCompleteBoundaryBatch,
) -> TargetSizeExecutionHead:
    """Persist batch first, apply deterministically, publish head atomically.

    Crash order is exactly: batch persistent file first, then the head file.
    Reopening a root where the batch exists but no current head exists will
    deterministically repair/publish the head from the same batch, never
    producing a second reducer transition from the same evidence.
    """

    root_path = Path(root)
    current_path = root_path / CURRENT_HEAD_FILENAME
    if current_path.is_file():
        current = TargetSizeExecutionHead.from_dict(
            json.loads(current_path.read_text(encoding="utf-8"))
        )
        if current.post_state_digest != batch.pre_state_digest:
            raise TrainingDataInputError(
                "Current head does not provide this batch's exact pre-state."
            )
    # Persistence order: immutable batch, then immutable head, then the
    # current-head pointer alias.  A crash at any point leaves reconcile
    # deterministically convergent and never applies a transition twice.
    persist_complete_boundary_batch(root_path, batch)
    post_state = apply_complete_boundary_batch(definition, state, batch)
    head = TargetSizeExecutionHead(
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
            raise TrainingDataInputError("Existing head conflicts with computed head.")
    else:
        _atomic_json_write(head_path, head.to_dict())
    _atomic_json_write(current_path, head.to_dict())
    return head


def load_current_execution_head(root: str | Path) -> TargetSizeExecutionHead | None:
    path = Path(root) / CURRENT_HEAD_FILENAME
    if not path.is_file():
        return None
    return TargetSizeExecutionHead.from_dict(json.loads(path.read_text(encoding="utf-8")))


def reconcile_target_size_screen_root(
    root: str | Path,
    aggregate: Any,
    context: TargetSizeExecutionContext,
    common: TargetSizeCommonPreparation,
) -> TargetSizeExecutionHead | None:
    """Crash-safe restart reconciliation through real P2 owners.

    Cases handled fail-closed:

    - window identity mismatch: reject (stale/changed P1/P2 authority);
    - head + batch both present and valid: committed post-state returned;
    - batch persisted but no head: apply exactly once and publish the head
      (repair), never duplicating the transition;
    - head without its batch ancestry: fail closed;
    - progress only: no head is published (partial state remains).
    """

    root_path = Path(root)
    window_path = root_path / SCREEN_WINDOW_FILENAME
    if not window_path.is_file():
        return None
    window = TargetSizeScreenWindow.from_dict(
        json.loads(window_path.read_text(encoding="utf-8"))
    )
    if (
        window.aggregate_digest != aggregate.content_digest
        or window.experiment_definition_digest != aggregate.definition.content_digest
        or window.execution_context_digest != context.content_digest
        or window.common_preparation_digest != common.content_digest
    ):
        raise TrainingDataInputError(
            "Screen window does not bind the current P1/P2 authority identity."
        )
    head = load_current_execution_head(root_path)
    definition = aggregate.definition
    if head is not None:
        batch_path = _batch_path(root_path, head.batch_digest)
        if not batch_path.is_file():
            raise TrainingDataInputError(
                "Execution head is missing its complete batch ancestry."
            )
        # The committed post-state must authenticate as deterministic
        # history replay through the real P2 owner; it is never reapplied.
        validate_target_size_reducer_state(definition, head.post_state)
        current_state = head.post_state
    else:
        current_state = aggregate.reducer_state
    # Complete valid batches whose pre-state is the current committed state
    # are applied exactly once, in chain order, repairing any crash gap.
    # Two batches claiming one pre-state are conflicting scientific evidence.
    batches_dir = root_path / "batches"
    if batches_dir.is_dir():
        all_batches = []
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
                batch
                for batch in all_batches
                if batch.pre_state_digest == current_state.content_digest
            ]
            if len(candidates) > 1:
                raise TrainingDataInputError(
                    "Two complete batches claim the same pre-state: "
                    "conflicting scientific evidence."
                )
            if not candidates:
                break
            head = commit_target_size_boundary_batch(
                root_path, definition, current_state, candidates[0]
            )
            current_state = head.post_state
        return head
    return head


__all__ = [
    "BOUNDARY_BATCH_SCHEMA",
    "BOUNDARY_PROGRESS_FILENAME",
    "CURRENT_HEAD_FILENAME",
    "EXECUTION_HEAD_SCHEMA",
    "SCREEN_PROGRESS_SCHEMA",
    "SCREEN_WINDOW_FILENAME",
    "SCREEN_WINDOW_SCHEMA",
    "TargetSizeCandidateOutcome",
    "TargetSizeCompleteBoundaryBatch",
    "TargetSizeExecutionHead",
    "TargetSizeScreenWindow",
    "apply_complete_boundary_batch",
    "build_complete_boundary_batch",
    "collect_boundary_candidate_outcomes",
    "commit_target_size_boundary_batch",
    "derive_active_boundary_requirements",
    "initialize_target_size_screen",
    "load_current_execution_head",
    "load_target_size_boundary_batch",
    "persist_complete_boundary_batch",
    "reconcile_target_size_screen_root",
    "record_candidate_boundary_outcome",
]
