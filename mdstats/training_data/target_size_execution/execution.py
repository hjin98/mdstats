"""P3-C paired TRAIN2 execution and exact completed-epoch boundary state.

One candidate trajectory runs inside one frozen full-``n3`` TRAIN2 budget.
The rungs ``n1/n2/n3`` are realized exclusively through
``Train2RuntimePlan.execution_epoch_limit`` pauses; continuation always
resumes the exact authenticated predecessor boundary state and never
restarts from the foundation or epoch zero.

Ordinary successful evidence at an active boundary ``n_i`` is admissible only
when the real TRAIN2 runtime summary proves the frozen completed-epoch
boundary semantics:

    completed_epochs      == n_i
    execution_epoch_limit == n_i
    raw_checkpoint_epoch  == n_i - 1

Scientific numerical failures are translated only from positively
authenticated real TRAIN2 numerical-failure records.  Everything else —
corrupt/missing/mismatched restart state, ordinary MACE/config/schema/
lineage error, OOM/resource error, filesystem/process/programming error, or
cancellation — remains an execution error that produces no P2 scientific
failure and never advances the reducer.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..target_size_experiment import (
    NumericalFailureKind,
    TargetSizeExperimentDefinition,
    TargetSizeNumericalFailure,
)
from ..train2_runtime import (
    Train2NumericalFailureRecord,
    Train2RuntimePlan,
    Train2RuntimeSummary,
    load_train2_runtime_summary,
    validate_train2_runtime_continuation_artifacts,
)
from .candidate import TargetSizeCandidateTrajectory
from .schedule import TargetSizeScreenSchedule

TARGET_SIZE_BOUNDARY_STATE_SCHEMA = "mdstats.target-size.boundary-state.v1"
TARGET_SIZE_CONTINUATION_SCHEMA = "mdstats.target-size.continuation-request.v1"

EVALUATION_MODEL_STATE_LIVE = "live"
EVALUATION_MODEL_STATE_EMA = "ema"

# Authenticated TRAIN2 failure-code translation.  ``train_nonfinite_ema_state``
# is model-state science, not optimizer-state science: the original TRAIN2
# code is preserved in the classification evidence.
_TRAINED_FAILURE_KINDS = {
    "train_nonfinite_model_state": NumericalFailureKind.TRAIN_NONFINITE_MODEL_STATE,
    "train_nonfinite_ema_state": NumericalFailureKind.TRAIN_NONFINITE_MODEL_STATE,
    "train_nonfinite_optimizer_state": (
        NumericalFailureKind.TRAIN_NONFINITE_OPTIMIZER_STATE
    ),
}


def target_size_evaluation_model_state(optimizer_policy: Any) -> str:
    """Freeze the evaluated model-state representation from the policy.

    All candidates must use the same convention: EMA shadow parameters when
    the frozen policy enables EMA, live parameters otherwise.
    """

    return EVALUATION_MODEL_STATE_EMA if bool(optimizer_policy.ema) else EVALUATION_MODEL_STATE_LIVE


def target_size_boundary_index(
    schedule: TargetSizeScreenSchedule, boundary_epoch: int
) -> int:
    """Index of a rung inside the frozen fidelity ladder."""

    epoch = schedule.validate_boundary_epoch(boundary_epoch)
    return schedule.fidelity_epochs.index(epoch)


def target_size_evaluation_size_for_boundary(
    definition: TargetSizeExperimentDefinition,
    schedule: TargetSizeScreenSchedule,
    boundary_epoch: int,
) -> int:
    """The exact paired P2 evaluation size ``M_i`` of an active boundary."""

    index = target_size_boundary_index(schedule, boundary_epoch)
    return definition.policy.evaluation_sizes[index]


def target_size_evaluation_membership_digest_for_boundary(
    definition: TargetSizeExperimentDefinition,
    schedule: TargetSizeScreenSchedule,
    boundary_epoch: int,
) -> str:
    """Exact P2 evaluation-membership digest paired with the boundary."""

    index = target_size_boundary_index(schedule, boundary_epoch)
    return definition.evaluation_order.membership_digest(
        definition.policy.evaluation_sizes[index]
    )


def target_size_rung_plan(
    trajectory: TargetSizeCandidateTrajectory,
    schedule: TargetSizeScreenSchedule,
    *,
    boundary_epoch: int,
) -> Train2RuntimePlan:
    """Derive one rung TRAIN2 runtime plan inside the full-n3 budget.

    The only rung-varying input is the pause limit.  The plan binds the
    trajectory's training-protocol identity and the seed-neutral
    training-policy identity; every schedule-defining authority stays
    byte-identical across rungs.
    """

    return schedule.runtime_plan(
        training_protocol_digest=trajectory.candidate_training_protocol_digest,
        optimizer_policy_digest=trajectory.seed_neutral_training_policy_digest,
        structures_per_epoch=trajectory.realization.structures_per_epoch,
        execution_epoch_limit=schedule.validate_boundary_epoch(boundary_epoch),
    )


@dataclass(frozen=True, slots=True)
class TargetSizeContinuationRequest:
    """A rung continuation bound to its exact predecessor boundary.

    Every later-rung request binds the exact predecessor trajectory and
    boundary; a checkpoint from another N, seed, context, protocol, or
    boundary is foreign even if tensor shapes match.
    """

    trajectory_digest: str
    predecessor_boundary_epoch: int | None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "trajectory_digest",
            validate_digest(self.trajectory_digest, name="trajectory_digest"),
        )
        if self.predecessor_boundary_epoch is not None:
            epoch = int(self.predecessor_boundary_epoch)
            if epoch <= 0:
                raise TrainingDataInputError(
                    "Continuation predecessor boundary must be a positive completed epoch."
                )
            object.__setattr__(self, "predecessor_boundary_epoch", epoch)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_CONTINUATION_SCHEMA,
            "trajectory_digest": self.trajectory_digest,
            "predecessor_boundary_epoch": self.predecessor_boundary_epoch,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeContinuationRequest:
        if payload.get("schema") != TARGET_SIZE_CONTINUATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported continuation-request schema."
            )
        result = cls(
            trajectory_digest=str(payload["trajectory_digest"]),
            predecessor_boundary_epoch=(
                None
                if payload.get("predecessor_boundary_epoch") is None
                else int(payload["predecessor_boundary_epoch"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Continuation-request digest mismatch."
            )
        return result


def initial_target_size_continuation_request(
    trajectory: TargetSizeCandidateTrajectory,
) -> TargetSizeContinuationRequest:
    """Initialization request: run from epoch zero to the first rung."""

    return TargetSizeContinuationRequest(
        trajectory_digest=trajectory.content_digest,
        predecessor_boundary_epoch=None,
    )


def continuation_request_from_boundary(
    boundary_state: "TargetSizeBoundaryState",
) -> TargetSizeContinuationRequest:
    """Continuation request descending from one exact boundary state."""

    return TargetSizeContinuationRequest(
        trajectory_digest=boundary_state.trajectory_digest,
        predecessor_boundary_epoch=boundary_state.boundary_epoch,
    )


def validate_target_size_continuation_request(
    request: TargetSizeContinuationRequest,
    trajectory: TargetSizeCandidateTrajectory,
    schedule: TargetSizeScreenSchedule,
    *,
    checkpoint_directory: str | Path,
) -> Train2RuntimeSummary:
    """Authenticate the exact predecessor boundary before any resume.

    Resumes only the exact predecessor boundary state of this trajectory:
    never the foundation, never epoch zero, and never a foreign
    N/seed/context/protocol/boundary checkpoint.  The predecessor's own rung
    plan carried ``execution_epoch_limit == n_{i-1}`` (its pause), while every
    schedule-defining authority matches the full-n3 budget.
    """

    if request.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Continuation request binds a different trajectory."
        )
    predecessor = request.predecessor_boundary_epoch
    if predecessor is None:
        raise TrainingDataInputError(
            "An initialized trajectory has no predecessor state to resume."
        )
    schedule.validate_boundary_epoch(predecessor)
    epochs = schedule.fidelity_epochs
    if predecessor == epochs[-1]:
        raise TrainingDataInputError(
            "The terminal boundary has no later rung to continue."
        )
    summary = validate_train2_runtime_continuation_artifacts(
        checkpoint_directory,
        training_protocol_digest=trajectory.candidate_training_protocol_digest,
        optimizer_policy_digest=trajectory.seed_neutral_training_policy_digest,
        budget_policy=schedule.budget_policy,
        learning_rate_policy=schedule.learning_rate_policy,
        structures_per_epoch=trajectory.realization.structures_per_epoch,
    )
    if summary.completed_epochs != predecessor:
        raise TrainingDataInputError(
            "Continuation request does not match the checkpointed boundary."
        )
    if summary.execution_epoch_limit != predecessor:
        raise TrainingDataInputError(
            "Predecessor boundary state was not produced under its own rung pause limit."
        )
    _validate_summary_realization(trajectory, summary)
    return summary


def _validate_summary_realization(
    trajectory: TargetSizeCandidateTrajectory,
    summary: Train2RuntimeSummary,
) -> None:
    realization = trajectory.realization
    if (
        summary.training_protocol_digest != trajectory.candidate_training_protocol_digest
        or summary.optimizer_policy_digest
        != trajectory.seed_neutral_training_policy_digest
    ):
        raise TrainingDataInputError(
            "TRAIN2 state binds a different trajectory protocol or policy."
        )
    if (
        summary.structures_per_epoch != realization.structures_per_epoch
        or summary.updates_per_epoch != realization.updates_per_epoch
        or summary.planned_updates != realization.planned_updates
        or summary.planned_structures_presented
        != realization.planned_structures_presented
    ):
        raise TrainingDataInputError(
            "TRAIN2 state does not carry the trajectory's exact loader/update geometry."
        )


@dataclass(frozen=True, slots=True)
class TargetSizeBoundaryState:
    """The sole authenticated model state eligible for P3 evaluation.

    Binds the exact trajectory, the active boundary completed epoch, the
    rung plan that produced the boundary, the frozen evaluation model-state
    representation, and the real TRAIN2 runtime summary proving the
    completed-epoch boundary semantics.
    """

    trajectory_digest: str
    boundary_epoch: int
    evaluation_model_state: str
    rung_plan_digest: str
    rung_runtime_summary: Train2RuntimeSummary

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "trajectory_digest",
            validate_digest(self.trajectory_digest, name="trajectory_digest"),
        )
        object.__setattr__(
            self, "boundary_epoch", int(self.boundary_epoch)
        )
        if self.evaluation_model_state not in (EVALUATION_MODEL_STATE_LIVE, EVALUATION_MODEL_STATE_EMA):
            raise TrainingDataInputError(
                "Boundary state must freeze its evaluation model-state representation."
            )
        object.__setattr__(
            self,
            "rung_plan_digest",
            validate_digest(self.rung_plan_digest, name="rung_plan_digest"),
        )
        if self.evaluation_model_state == EVALUATION_MODEL_STATE_EMA and (
            self.rung_runtime_summary.ema_state_digest is None
        ):
            raise TrainingDataInputError(
                "EMA-evaluated boundary state requires authenticated EMA state."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_BOUNDARY_STATE_SCHEMA,
            "trajectory_digest": self.trajectory_digest,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_model_state": self.evaluation_model_state,
            "rung_plan_digest": self.rung_plan_digest,
            "rung_runtime_summary": self.rung_runtime_summary.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeBoundaryState:
        if payload.get("schema") != TARGET_SIZE_BOUNDARY_STATE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported boundary-state schema."
            )
        result = cls(
            trajectory_digest=str(payload["trajectory_digest"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_model_state=str(payload["evaluation_model_state"]),
            rung_plan_digest=str(payload["rung_plan_digest"]),
            rung_runtime_summary=Train2RuntimeSummary.from_dict(
                payload["rung_runtime_summary"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Boundary-state digest mismatch."
            )
        return result


def bind_target_size_boundary_state(
    trajectory: TargetSizeCandidateTrajectory,
    schedule: TargetSizeScreenSchedule,
    summary: Train2RuntimeSummary,
    *,
    checkpoint_directory: str | Path,
) -> TargetSizeBoundaryState:
    """Authenticate ordinary successful evidence at one active boundary.

    Enforces the frozen completed-epoch boundary semantics, including the
    off-by-one case ``n1 = 1 -> raw_checkpoint_epoch = 0``, and authenticates
    the full durable TRAIN2 state (live parameters, optimizer-state
    reference, EMA state when enabled, RNG state, completed updates, and
    LR/schedule progress) through the real continuation owner.
    """

    boundary = schedule.validate_boundary_epoch(summary.completed_epochs)
    if summary.execution_epoch_limit != boundary:
        raise TrainingDataInputError(
            "Boundary evidence requires the active rung execution_epoch_limit."
        )
    expected_raw_epoch = boundary - 1
    if summary.raw_checkpoint_epoch != expected_raw_epoch:
        raise TrainingDataInputError(
            "Boundary evidence requires the raw checkpoint of exactly the completed boundary."
        )
    _validate_summary_realization(trajectory, summary)
    authenticated = validate_train2_runtime_continuation_artifacts(
        checkpoint_directory,
        training_protocol_digest=trajectory.candidate_training_protocol_digest,
        optimizer_policy_digest=trajectory.seed_neutral_training_policy_digest,
        budget_policy=schedule.budget_policy,
        learning_rate_policy=schedule.learning_rate_policy,
        structures_per_epoch=trajectory.realization.structures_per_epoch,
    )
    if authenticated.content_digest != summary.content_digest:
        raise TrainingDataInputError(
            "Boundary summary does not authenticate against the durable TRAIN2 state."
        )
    rung_plan = target_size_rung_plan(
        trajectory, schedule, boundary_epoch=boundary
    )
    if rung_plan.content_digest != summary.plan_digest:
        raise TrainingDataInputError(
            "Boundary evidence was not produced under its rung TRAIN2 plan."
        )
    if trajectory.evaluation_model_state == EVALUATION_MODEL_STATE_EMA and (
        summary.ema_state_digest is None
    ):
        raise TrainingDataInputError(
            "EMA-evaluated trajectory requires authenticated EMA boundary state."
        )
    return TargetSizeBoundaryState(
        trajectory_digest=trajectory.content_digest,
        boundary_epoch=boundary,
        evaluation_model_state=trajectory.evaluation_model_state,
        rung_plan_digest=rung_plan.content_digest,
        rung_runtime_summary=summary,
    )


def load_target_size_boundary_state(
    trajectory: TargetSizeCandidateTrajectory,
    schedule: TargetSizeScreenSchedule,
    *,
    boundary_epoch: int,
    checkpoint_directory: str | Path,
) -> TargetSizeBoundaryState:
    """Load and authenticate the exact boundary state from durable state."""

    boundary = schedule.validate_boundary_epoch(boundary_epoch)
    summary = load_train2_runtime_summary(checkpoint_directory)
    if summary.completed_epochs != boundary:
        raise TrainingDataInputError(
            "Durable TRAIN2 state is not at the requested boundary."
        )
    return bind_target_size_boundary_state(
        trajectory, schedule, summary, checkpoint_directory=checkpoint_directory
    )


def translate_target_size_train2_failure(
    record: Train2NumericalFailureRecord,
    *,
    trajectory: TargetSizeCandidateTrajectory,
    definition: TargetSizeExperimentDefinition,
    schedule: TargetSizeScreenSchedule,
    scheduled_boundary_epoch: int,
) -> TargetSizeNumericalFailure:
    """Translate one authenticated TRAIN2 numerical failure to P2 evidence.

    The failure binds the **scheduled active boundary** ``n_i`` so a complete
    boundary matrix can eventually exist, while the classification evidence
    retains the real failure location (original code, failed epoch, completed
    updates, raw checkpoint) and the exact trajectory identity.  The reducer
    is never told the candidate successfully reached ``n_i``.

    Anything that is not a positively authenticated TRAIN2 numerical-failure
    record remains an ordinary execution error and must not call this
    adapter.
    """

    boundary = schedule.validate_boundary_epoch(scheduled_boundary_epoch)
    if trajectory.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Failure translation requires the trajectory's own definition."
        )
    rung_plan = target_size_rung_plan(
        trajectory, schedule, boundary_epoch=boundary
    )
    if (
        record.plan_digest != rung_plan.content_digest
        or record.training_protocol_digest
        != trajectory.candidate_training_protocol_digest
        or record.optimizer_policy_digest
        != trajectory.seed_neutral_training_policy_digest
        or record.budget_policy_digest != schedule.budget_policy.policy_digest
        or record.lr_policy_digest != schedule.learning_rate_policy.policy_digest
        or record.execution_epoch_limit != boundary
        or record.planned_updates != trajectory.realization.planned_updates
    ):
        raise TrainingDataInputError(
            "Numerical-failure record does not bind this trajectory's rung plan."
        )
    kind = _TRAINED_FAILURE_KINDS.get(record.failure_code)
    if kind is None:
        raise TrainingDataInputError(
            "Only authenticated TRAIN2 numerical-failure records are scientific "
            "evidence; unclassified failures remain execution errors."
        )
    evidence = digest(
        {
            "schema": "mdstats.target-size.train2-failure-evidence.v1",
            "trajectory_digest": trajectory.content_digest,
            "scheduled_boundary_epoch": boundary,
            "failure_record": record.to_dict(),
        }
    )
    return TargetSizeNumericalFailure(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=trajectory.execution_context_digest,
        target_size=trajectory.target_size,
        optimizer_seed=trajectory.optimizer_seed,
        boundary_epoch=boundary,
        evaluation_membership_digest=(
            target_size_evaluation_membership_digest_for_boundary(
                definition, schedule, boundary
            )
        ),
        kind=kind,
        classification_evidence_digest=evidence,
    )


__all__ = [
    "EVALUATION_MODEL_STATE_EMA",
    "EVALUATION_MODEL_STATE_LIVE",
    "TARGET_SIZE_BOUNDARY_STATE_SCHEMA",
    "TARGET_SIZE_CONTINUATION_SCHEMA",
    "TargetSizeBoundaryState",
    "TargetSizeContinuationRequest",
    "bind_target_size_boundary_state",
    "continuation_request_from_boundary",
    "initial_target_size_continuation_request",
    "load_target_size_boundary_state",
    "target_size_boundary_index",
    "target_size_evaluation_membership_digest_for_boundary",
    "target_size_evaluation_model_state",
    "target_size_evaluation_size_for_boundary",
    "target_size_rung_plan",
    "translate_target_size_train2_failure",
    "validate_target_size_continuation_request",
]
