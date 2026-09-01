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

import hashlib
import json
from dataclasses import dataclass, field
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
from .persistence import (
    publish_immutable_bytes_create_or_verify,
    publish_immutable_json_create_or_verify,
)
from .schedule import TargetSizeScreenSchedule

TARGET_SIZE_BOUNDARY_STATE_SCHEMA = "mdstats.target-size.boundary-state.v1"
TARGET_SIZE_BOUNDARY_SNAPSHOT_SCHEMA = "mdstats.target-size.boundary-snapshot.v1"
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


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _checkpoint_for_epoch(directory: Path, epoch: int) -> Path:
    matches = []
    for item in directory.glob("*.pt"):
        name = item.name
        if f"epoch-{int(epoch)}" in name or f"epoch_{int(epoch)}" in name:
            matches.append(item)
    if len(matches) != 1:
        raise TrainingDataInputError(
            f"TRAIN2 expected exactly one raw checkpoint for durable epoch {epoch}; found {len(matches)}."
        )
    return matches[0]


@dataclass(frozen=True, slots=True)
class TargetSizeBoundarySnapshot:
    """Immutable preserved TRAIN2 boundary snapshot for historical proof."""

    trajectory_digest: str
    boundary_epoch: int
    evaluation_model_state: str
    rung_plan_digest: str
    raw_checkpoint_name: str
    raw_checkpoint_sha256: str
    runtime_summary_digest: str
    companion_sha256: str
    optimizer_state_digest: str
    live_parameter_digest: str
    ema_state_digest: str | None
    rng_state_digest: str
    completed_updates: int
    planned_updates: int
    snapshot_relative_dir: str
    rung_runtime_summary: Train2RuntimeSummary
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "trajectory_digest",
            "rung_plan_digest",
            "raw_checkpoint_sha256",
            "runtime_summary_digest",
            "companion_sha256",
            "optimizer_state_digest",
            "live_parameter_digest",
            "rng_state_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.ema_state_digest is not None:
            object.__setattr__(
                self,
                "ema_state_digest",
                validate_digest(self.ema_state_digest, name="ema_state_digest"),
            )
        for name in ("boundary_epoch", "completed_updates", "planned_updates"):
            val = int(getattr(self, name))
            if val <= 0:
                raise TrainingDataInputError(f"{name} must be a positive integer.")
            object.__setattr__(self, name, val)
        if self.evaluation_model_state not in (
            EVALUATION_MODEL_STATE_LIVE,
            EVALUATION_MODEL_STATE_EMA,
        ):
            raise TrainingDataInputError(
                "Boundary snapshot evaluation model state must be 'live' or 'ema'."
            )
        if (
            self.evaluation_model_state == EVALUATION_MODEL_STATE_EMA
            and self.ema_state_digest is None
        ):
            raise TrainingDataInputError(
                "EMA boundary snapshot requires authenticated ema_state_digest."
            )
        for name in ("raw_checkpoint_name", "snapshot_relative_dir"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} cannot be empty.")
        if Path(self.raw_checkpoint_name).name != self.raw_checkpoint_name:
            raise TrainingDataInputError(
                "raw_checkpoint_name must be a single relative filename."
            )
        relative_snapshot = Path(self.snapshot_relative_dir)
        if relative_snapshot.is_absolute() or ".." in relative_snapshot.parts:
            raise TrainingDataInputError(
                "snapshot_relative_dir must remain within the snapshot root."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_BOUNDARY_SNAPSHOT_SCHEMA,
            "trajectory_digest": self.trajectory_digest,
            "boundary_epoch": self.boundary_epoch,
            "evaluation_model_state": self.evaluation_model_state,
            "rung_plan_digest": self.rung_plan_digest,
            "raw_checkpoint_name": self.raw_checkpoint_name,
            "raw_checkpoint_sha256": self.raw_checkpoint_sha256,
            "runtime_summary_digest": self.runtime_summary_digest,
            "companion_sha256": self.companion_sha256,
            "optimizer_state_digest": self.optimizer_state_digest,
            "live_parameter_digest": self.live_parameter_digest,
            "ema_state_digest": self.ema_state_digest,
            "rng_state_digest": self.rng_state_digest,
            "completed_updates": self.completed_updates,
            "planned_updates": self.planned_updates,
            "snapshot_relative_dir": self.snapshot_relative_dir,
            "rung_runtime_summary": self.rung_runtime_summary.to_dict(),
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
    ) -> TargetSizeBoundarySnapshot:
        if payload.get("schema") != TARGET_SIZE_BOUNDARY_SNAPSHOT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size boundary snapshot schema."
            )
        result = cls(
            trajectory_digest=str(payload["trajectory_digest"]),
            boundary_epoch=int(payload["boundary_epoch"]),
            evaluation_model_state=str(payload["evaluation_model_state"]),
            rung_plan_digest=str(payload["rung_plan_digest"]),
            raw_checkpoint_name=str(payload["raw_checkpoint_name"]),
            raw_checkpoint_sha256=str(payload["raw_checkpoint_sha256"]),
            runtime_summary_digest=str(payload["runtime_summary_digest"]),
            companion_sha256=str(payload["companion_sha256"]),
            optimizer_state_digest=str(payload["optimizer_state_digest"]),
            live_parameter_digest=str(payload["live_parameter_digest"]),
            ema_state_digest=(
                None
                if payload.get("ema_state_digest") is None
                else str(payload["ema_state_digest"])
            ),
            rng_state_digest=str(payload["rng_state_digest"]),
            completed_updates=int(payload["completed_updates"]),
            planned_updates=int(payload["planned_updates"]),
            snapshot_relative_dir=str(payload["snapshot_relative_dir"]),
            rung_runtime_summary=Train2RuntimeSummary.from_dict(
                payload["rung_runtime_summary"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Boundary snapshot digest mismatch."
            )
        return result


def promote_target_size_boundary_snapshot(
    trajectory: TargetSizeCandidateTrajectory,
    boundary_state: TargetSizeBoundaryState,
    *,
    checkpoint_directory: str | Path,
    snapshot_root: str | Path,
) -> TargetSizeBoundarySnapshot:
    """Promote one immutable boundary snapshot before active files can advance."""
    if boundary_state.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Boundary state belongs to a different candidate trajectory."
        )
    checkpoint_dir = Path(checkpoint_directory)
    summary = boundary_state.rung_runtime_summary
    boundary_epoch = boundary_state.boundary_epoch
    raw_checkpoint = _checkpoint_for_epoch(
        checkpoint_dir, summary.raw_checkpoint_epoch
    )
    summary_path = checkpoint_dir / "train2_runtime.json"
    companion_path = checkpoint_dir / "train2_runtime.pt"
    if not raw_checkpoint.is_file():
        raise TrainingDataInputError(
            f"Raw checkpoint file is missing: {raw_checkpoint}"
        )
    if not summary_path.is_file():
        raise TrainingDataInputError(
            f"TRAIN2 runtime summary file is missing: {summary_path}"
        )
    if not companion_path.is_file():
        raise TrainingDataInputError(
            f"TRAIN2 continuation companion file is missing: {companion_path}"
        )
    ckpt_sha = _sha256_file(raw_checkpoint)
    if ckpt_sha != summary.raw_checkpoint_sha256:
        raise TrainingDataInputError(
            "Raw checkpoint sha256 does not match runtime summary."
        )
    rel_dir = (
        f"snapshots/{trajectory.content_digest[:16]}/boundary_{boundary_epoch}"
    )
    dest_dir = Path(snapshot_root) / rel_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_raw = dest_dir / raw_checkpoint.name
    dest_summary = dest_dir / "train2_runtime.json"
    dest_companion = dest_dir / "train2_runtime.pt"

    for src, dst in (
        (raw_checkpoint, dest_raw),
        (companion_path, dest_companion),
    ):
        raw_bytes = src.read_bytes()
        publish_immutable_bytes_create_or_verify(
            dst,
            raw_bytes,
            expected_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        )
    publish_immutable_json_create_or_verify(
        dest_summary,
        summary.to_dict(),
        deserializer=Train2RuntimeSummary.from_dict,
    )

    companion_sha = _sha256_file(dest_companion)
    summary_digest = summary.content_digest

    snapshot = TargetSizeBoundarySnapshot(
        trajectory_digest=trajectory.content_digest,
        boundary_epoch=boundary_epoch,
        evaluation_model_state=boundary_state.evaluation_model_state,
        rung_plan_digest=boundary_state.rung_plan_digest,
        raw_checkpoint_name=raw_checkpoint.name,
        raw_checkpoint_sha256=ckpt_sha,
        runtime_summary_digest=summary_digest,
        companion_sha256=companion_sha,
        optimizer_state_digest=summary.optimizer_state_digest,
        live_parameter_digest=summary.live_parameter_digest,
        ema_state_digest=summary.ema_state_digest,
        rng_state_digest=summary.rng_state_digest,
        completed_updates=summary.completed_updates,
        planned_updates=summary.planned_updates,
        snapshot_relative_dir=rel_dir,
        rung_runtime_summary=summary,
    )
    meta_path = dest_dir / "snapshot.json"
    publish_immutable_json_create_or_verify(
        meta_path,
        snapshot.to_dict(),
        deserializer=TargetSizeBoundarySnapshot.from_dict,
    )
    return snapshot


def load_target_size_boundary_snapshot(
    snapshot_root: str | Path,
    snapshot_record: TargetSizeBoundarySnapshot | Mapping[str, Any],
) -> TargetSizeBoundarySnapshot:
    """Load and instantiate a boundary snapshot record."""
    if isinstance(snapshot_record, TargetSizeBoundarySnapshot):
        return snapshot_record
    return TargetSizeBoundarySnapshot.from_dict(snapshot_record)


def validate_target_size_boundary_snapshot(
    snapshot: TargetSizeBoundarySnapshot,
    *,
    snapshot_root: str | Path,
    trajectory: TargetSizeCandidateTrajectory,
    schedule: TargetSizeScreenSchedule | None = None,
) -> Train2RuntimeSummary:
    """Validate that a preserved boundary snapshot remains authentic on restart."""
    if snapshot.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Boundary snapshot binds a different trajectory."
        )
    if snapshot.evaluation_model_state != trajectory.evaluation_model_state:
        raise TrainingDataInputError(
            "Boundary snapshot evaluation model-state mismatch."
        )
    snapshot_root_path = Path(snapshot_root).resolve()
    dest_dir = (snapshot_root_path / snapshot.snapshot_relative_dir).resolve()
    try:
        dest_dir.relative_to(snapshot_root_path)
    except ValueError as exc:
        raise TrainingDataInputError(
            "Preserved boundary snapshot directory resolves outside snapshot root."
        ) from exc
    dest_raw = dest_dir / snapshot.raw_checkpoint_name
    dest_summary = dest_dir / "train2_runtime.json"
    dest_companion = dest_dir / "train2_runtime.pt"
    if (
        not dest_raw.is_file()
        or not dest_summary.is_file()
        or not dest_companion.is_file()
    ):
        raise TrainingDataInputError(
            "Preserved boundary snapshot files are missing."
        )
    if _sha256_file(dest_raw) != snapshot.raw_checkpoint_sha256:
        raise TrainingDataInputError(
            "Preserved boundary raw checkpoint bytes changed."
        )
    if _sha256_file(dest_companion) != snapshot.companion_sha256:
        raise TrainingDataInputError(
            "Preserved boundary companion bytes changed."
        )
    loaded_summary = load_train2_runtime_summary(dest_dir)
    if loaded_summary.content_digest != snapshot.runtime_summary_digest:
        raise TrainingDataInputError(
            "Preserved boundary runtime summary digest changed."
        )
    if (
        snapshot.raw_checkpoint_sha256 != loaded_summary.raw_checkpoint_sha256
        or snapshot.optimizer_state_digest != loaded_summary.optimizer_state_digest
        or snapshot.live_parameter_digest != loaded_summary.live_parameter_digest
        or snapshot.ema_state_digest != loaded_summary.ema_state_digest
        or snapshot.rng_state_digest != loaded_summary.rng_state_digest
        or snapshot.completed_updates != loaded_summary.completed_updates
        or snapshot.planned_updates != loaded_summary.planned_updates
    ):
        raise TrainingDataInputError(
            "Preserved boundary snapshot metadata disagrees with its runtime summary."
        )
    if schedule is not None:
        authenticated = validate_train2_runtime_continuation_artifacts(
            dest_dir,
            training_protocol_digest=(
                trajectory.candidate_training_protocol_digest
            ),
            optimizer_policy_digest=(
                trajectory.seed_neutral_training_policy_digest
            ),
            budget_policy=schedule.budget_policy,
            learning_rate_policy=schedule.learning_rate_policy,
            structures_per_epoch=trajectory.realization.structures_per_epoch,
        )
        if authenticated.content_digest != loaded_summary.content_digest:
            raise TrainingDataInputError(
                "Preserved boundary continuation artifacts failed authentication."
            )
    return loaded_summary


__all__ = [
    "EVALUATION_MODEL_STATE_EMA",
    "EVALUATION_MODEL_STATE_LIVE",
    "TARGET_SIZE_BOUNDARY_SNAPSHOT_SCHEMA",
    "TARGET_SIZE_BOUNDARY_STATE_SCHEMA",
    "TARGET_SIZE_CONTINUATION_SCHEMA",
    "TargetSizeBoundarySnapshot",
    "TargetSizeBoundaryState",
    "TargetSizeContinuationRequest",
    "bind_target_size_boundary_state",
    "continuation_request_from_boundary",
    "initial_target_size_continuation_request",
    "load_target_size_boundary_snapshot",
    "load_target_size_boundary_state",
    "promote_target_size_boundary_snapshot",
    "target_size_boundary_index",
    "target_size_evaluation_membership_digest_for_boundary",
    "target_size_evaluation_model_state",
    "target_size_evaluation_size_for_boundary",
    "target_size_rung_plan",
    "translate_target_size_train2_failure",
    "validate_target_size_boundary_snapshot",
    "validate_target_size_continuation_request",
]
