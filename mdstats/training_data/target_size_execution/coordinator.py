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

import fcntl
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..mace_export import MaceExtxyzPolicy
from ..protocol import MaceOptimizerPolicy
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
from .persistence import (
    publish_immutable_bytes_create_or_verify,
    publish_immutable_json_create_or_verify,
    publish_mutable_json_atomic,
)
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


def _publish_create_or_verify(
    path: Path,
    payload: Mapping[str, Any],
    deserializer: Callable[[Mapping[str, Any]], Any] | None = None,
) -> Any:
    """Crash-safe publication using shared persistence primitive."""
    return publish_immutable_json_create_or_verify(
        path, payload, deserializer=deserializer
    )


def _atomic_json_write(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomic mutable JSON write using shared persistence primitive."""
    publish_mutable_json_atomic(path, payload)


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
class TargetSizeExecutionResolver:
    """Execution resolver locating content-addressed and per-cell artifacts."""

    root_directory: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root_directory", Path(self.root_directory).resolve())

    def _cas_path(self, subdirectory: str, content_digest: str) -> Path:
        verified = validate_digest(content_digest, name="content_digest")
        return self.root_directory / subdirectory / f"{verified}.json"

    def trajectory_path(self, trajectory_digest: str) -> Path:
        return self._cas_path("trajectories", trajectory_digest)

    def materialization_path(self, materialization_digest: str) -> Path:
        return self._cas_path("materializations", materialization_digest)

    def evaluation_artifact_path(self, eval_data_digest: str) -> Path:
        return self._cas_path("evaluation_artifacts", eval_data_digest)

    def role_path(self, role_digest: str) -> Path:
        return self._cas_path("roles", role_digest)

    def prediction_evidence_path(self, prediction_digest: str) -> Path:
        return self._cas_path("predictions", prediction_digest)

    def eval2_metric_path(self, metric_digest: str) -> Path:
        return self._cas_path("metrics", metric_digest)

    def snapshot_path(self, snapshot_digest: str) -> Path:
        return self._cas_path("snapshots", snapshot_digest)

    def continuation_path(self, continuation_digest: str) -> Path:
        return self._cas_path("continuations", continuation_digest)

    def planned_rung_path(self, planned_rung_digest: str) -> Path:
        return self._cas_path("planned_rungs", planned_rung_digest)

    def failure_record_path(self, failure_digest: str) -> Path:
        return self._cas_path("failures", failure_digest)

    def failure_bulk_directory(self, failure_digest: str) -> Path:
        """Durable raw TRAIN2/EVAL2 evidence directory for one failure record."""

        return self.root_directory / "failures" / validate_digest(
            failure_digest, name="failure_digest"
        )

    def completion_path(
        self, boundary_epoch: int, completion_digest: str
    ) -> Path:
        epoch = int(boundary_epoch)
        if epoch <= 0:
            raise TrainingDataInputError("completion boundary epoch must be positive.")
        return (
            self.root_directory
            / "completions"
            / str(epoch)
            / f"{validate_digest(completion_digest, name='completion_digest')}.json"
        )

    def progress_path(
        self, window_digest: str, boundary_epoch: int, target_size: int, optimizer_seed: int
    ) -> Path:
        key = digest(
            {
                "schema": "mdstats.target-size.candidate-outcome-key.v1",
                "window_digest": window_digest,
                "boundary_epoch": boundary_epoch,
                "target_size": target_size,
                "optimizer_seed": optimizer_seed,
            }
        )
        epoch = int(boundary_epoch)
        if epoch <= 0:
            raise TrainingDataInputError("progress boundary epoch must be positive.")
        return (
            self.root_directory
            / "progress"
            / str(epoch)
            / f"{key}.json"
        )

    def batch_path(self, batch_digest: str) -> Path:
        return self._cas_path("batches", batch_digest)

    def head_path(self, head_digest: str) -> Path:
        return self._cas_path("heads", head_digest)

    def cell_outcome_path(
        self, window_digest: str, boundary_epoch: int, target_size: int, optimizer_seed: int
    ) -> Path:
        return self.progress_path(
            window_digest, boundary_epoch, target_size, optimizer_seed
        )

    def _load_typed_json(
        self,
        path: Path,
        deserializer: Callable[[Mapping[str, Any]], Any],
    ) -> Any:
        """Load one typed JSON object through the resolver root."""

        path = Path(path)
        try:
            path.resolve().relative_to(self.root_directory)
        except ValueError as exc:
            raise TrainingDataInputError(
                f"Typed artifact path {path} resolves outside the resolver root."
            ) from exc
        if not path.is_file():
            raise TrainingDataInputError(f"Required artifact file missing at {path}")
        try:
            raw_dict = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise TrainingDataSerializationError(
                f"Failed to parse JSON at {path}: {exc}"
            ) from exc
        if not isinstance(raw_dict, Mapping):
            raise TrainingDataSerializationError(
                f"Typed artifact at {path} must contain a JSON object."
            )
        try:
            obj = deserializer(raw_dict)
        except (TrainingDataInputError, TrainingDataSerializationError):
            raise
        except Exception as exc:
            raise TrainingDataSerializationError(
                f"Failed to deserialize typed artifact at {path}: {exc}"
            ) from exc
        if not isinstance(getattr(obj, "content_digest", None), str):
            raise TrainingDataSerializationError(
                f"Typed artifact at {path} does not expose a content digest."
            )
        return obj

    def load_typed_content_addressed(
        self,
        path: Path,
        expected_digest: str,
        deserializer: Callable[[Mapping[str, Any]], Any],
        *,
        validator: Callable[[Any], None] | None = None,
        bulk_validator: Callable[[Any], None] | None = None,
    ) -> Any:
        """Centralized typed content-addressed loader."""
        path = Path(path)
        expected = validate_digest(expected_digest, name="expected_digest")
        if path.stem != expected:
            raise TrainingDataInputError(
                f"Filename stem {path.stem} does not match expected digest {expected_digest}"
            )
        obj = self._load_typed_json(path, deserializer)
        actual_digest = getattr(obj, "content_digest", None)
        if not isinstance(actual_digest, str):
            raise TrainingDataSerializationError(
                f"Typed artifact at {path} does not expose a content digest."
            )
        if actual_digest != expected:
            raise TrainingDataInputError(
                f"Object content digest {actual_digest} does not match expected {expected_digest} at {path}"
            )
        if validator is not None and bulk_validator is not None:
            raise TrainingDataInputError(
                "Provide at most one typed-artifact validator."
            )
        active_validator = bulk_validator if bulk_validator is not None else validator
        if active_validator is not None:
            active_validator(obj)
        return obj

    def load_typed_logical(
        self,
        path: Path,
        deserializer: Callable[[Mapping[str, Any]], Any],
        *,
        validator: Callable[[Any], None] | None = None,
    ) -> Any:
        """Load one typed non-content-addressed logical record.

        Logical records still use the same schema/type/content-digest
        constructor path as content-addressed artifacts; their deterministic
        filename key is checked by :meth:`load_progress`.
        """

        obj = self._load_typed_json(path, deserializer)
        if validator is not None:
            validator(obj)
        return obj

    def load_progress(self, path: Path) -> Any:
        """Load and verify a logical progress pointer and its deterministic key."""

        obj = self.load_typed_logical(path, TargetSizeCandidateOutcome.from_dict)
        expected_path = self.progress_path(
            obj.window_digest,
            obj.boundary_epoch,
            obj.outcome.target_size,
            obj.outcome.optimizer_seed,
        )
        if Path(path).resolve() != expected_path.resolve():
            raise TrainingDataInputError(
                f"Progress file name {Path(path).name} does not match its deterministic cell key."
            )
        return obj

    def load_raw_failure(
        self,
        failure_digest: str,
        *,
        validator: Callable[[Any], None] | None = None,
    ) -> Any:
        """Load one raw TRAIN2/EVAL2 failure through its typed CAS owner."""

        from ..eval2 import Eval2NumericalEvaluationError
        from ..train2_runtime import Train2NumericalFailureRecord

        def deserialize(payload: Mapping[str, Any]) -> Any:
            schema = payload.get("schema")
            if schema == "mdstats.train2-numerical-failure.v1":
                return Train2NumericalFailureRecord.from_dict(payload)
            if schema == "mdstats.eval2-numerical-failure.v1":
                return Eval2NumericalEvaluationError.from_dict(payload)
            raise TrainingDataSerializationError(
                "Unsupported raw target-size failure schema."
            )

        return self.load_typed_content_addressed(
            self.failure_record_path(failure_digest),
            failure_digest,
            deserialize,
            validator=validator,
        )


@dataclass(frozen=True, slots=True)
class TargetSizeRestartAuthority:
    """Mandatory typed authority bundle for crash-safe restart reconciliation and replay."""

    aggregate: Any
    context: TargetSizeExecutionContext
    common: TargetSizeCommonPreparation
    schedule: TargetSizeScreenSchedule
    seed_neutral_optimizer_policy: MaceOptimizerPolicy
    canonical_frame_authority: Any
    frame_catalog: Any
    frame_data_by_run: Mapping[str, Any]
    frame_array_index: Mapping[str, Any]
    correlation_blocks: Mapping[str, str]
    extxyz_policy: MaceExtxyzPolicy
    eval2_policy: Any
    resolver: TargetSizeExecutionResolver
    bulk_roots: Mapping[str, str | Path]
    allow_forward_override: bool = False

    def __post_init__(self) -> None:
        if self.aggregate is None:
            raise TrainingDataInputError("TargetSizeRestartAuthority requires aggregate.")
        if self.context is None:
            raise TrainingDataInputError("TargetSizeRestartAuthority requires context.")
        if self.common is None:
            raise TrainingDataInputError("TargetSizeRestartAuthority requires common.")
        if self.schedule is None:
            raise TrainingDataInputError("TargetSizeRestartAuthority requires schedule.")
        if not isinstance(self.seed_neutral_optimizer_policy, MaceOptimizerPolicy):
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority requires the seed-neutral optimizer template."
            )
        if self.seed_neutral_optimizer_policy.seed < 0:
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority optimizer template seed is invalid."
            )
        if self.canonical_frame_authority is None:
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority requires canonical P1 frame authority."
            )
        for name in (
            "frame_catalog",
            "frame_data_by_run",
            "frame_array_index",
            "correlation_blocks",
        ):
            if getattr(self, name) is None:
                raise TrainingDataInputError(
                    f"TargetSizeRestartAuthority requires {name}."
                )
        try:
            object.__setattr__(
                self,
                "correlation_blocks",
                {
                    str(uid): validate_digest(value, name="correlation block identity")
                    for uid, value in dict(self.correlation_blocks).items()
                },
            )
        except (TypeError, ValueError) as exc:
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority correlation blocks are invalid."
            ) from exc
        expected_uids = set(self.aggregate.population.frame_uids)
        observed_blocks = dict(self.correlation_blocks)
        if set(observed_blocks) != expected_uids:
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority correlation blocks do not cover the accepted P2 population."
            )
        allowed_blocks = set(self.aggregate.split.constraint_component_digests)
        if set(observed_blocks.values()) - allowed_blocks:
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority correlation blocks contain foreign P2 components."
            )
        if not isinstance(self.extxyz_policy, MaceExtxyzPolicy):
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority requires the accepted MaceExtxyzPolicy."
            )
        eval2_digest = getattr(self.eval2_policy, "policy_digest", self.eval2_policy)
        eval2_digest = validate_digest(str(eval2_digest), name="eval2_policy_digest")
        if eval2_digest != self.context.eval2_metric_policy_digest:
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority EVAL2 policy differs from the execution context."
            )
        if not isinstance(self.resolver, TargetSizeExecutionResolver):
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority requires one typed execution resolver."
            )
        if not isinstance(self.allow_forward_override, bool):
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority allow_forward_override must be bool."
            )
        roots = dict(self.bulk_roots)
        required_roots = {"materialization", "snapshot", "evaluation", "train2"}
        if not required_roots.issubset(roots):
            missing = sorted(required_roots.difference(roots))
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority is missing bulk roots: "
                + ", ".join(missing)
            )
        normalized = {
            str(name): Path(value).resolve() for name, value in roots.items()
        }
        object.__setattr__(self, "bulk_roots", normalized)
        self.context.validate_bindings(
            self.aggregate.definition, self.common, self.schedule
        )
        if self.aggregate.reducer_state.execution_context_digest not in (
            None,
            self.context.content_digest,
        ):
            raise TrainingDataInputError(
                "TargetSizeRestartAuthority aggregate state binds a different execution context."
            )

    @property
    def eval2_policy_digest(self) -> str:
        return validate_digest(
            str(getattr(self.eval2_policy, "policy_digest", self.eval2_policy)),
            name="eval2_policy_digest",
        )

    def optimizer_policy_for_seed(self, optimizer_seed: int) -> MaceOptimizerPolicy:
        """Derive the only accepted per-seed optimizer policy."""

        from dataclasses import replace

        seed = int(optimizer_seed)
        if seed not in tuple(self.aggregate.definition.policy.optimizer_seeds):
            raise TrainingDataInputError(
                "Requested optimizer seed is not in the accepted P2 seed population."
            )
        return replace(self.seed_neutral_optimizer_policy, seed=seed)

    def bulk_root(self, name: str) -> Path:
        try:
            return self.bulk_roots[str(name)]
        except KeyError as exc:
            raise TrainingDataInputError(
                f"No declared bulk root exists for {name!r}."
            ) from exc


@dataclass(frozen=True, slots=True)
class TargetSizeResolvedCandidateExecution:
    """Durable resume inputs resolved from one authenticated screen cell.

    This is the production boundary between screen reconciliation and a TRAIN2
    worker.  Callers receive the already-authenticated trajectory,
    materialization, predecessor snapshot, and a mutable continuation
    workspace populated from that snapshot; they do not reconstruct any
    persistence path or predecessor identity themselves.
    """

    trajectory: Any
    optimizer_policy: MaceOptimizerPolicy
    materialization: Any
    predecessor_snapshot: Any
    checkpoint_directory: Path
    boundary_epoch: int
    start_epoch: int

    def __post_init__(self) -> None:
        if not isinstance(self.optimizer_policy, MaceOptimizerPolicy):
            raise TrainingDataInputError(
                "Resolved target-size execution requires an authenticated optimizer policy."
            )
        checkpoint_directory = Path(self.checkpoint_directory).resolve()
        object.__setattr__(self, "checkpoint_directory", checkpoint_directory)
        boundary_epoch = int(self.boundary_epoch)
        start_epoch = int(self.start_epoch)
        if boundary_epoch <= 0 or start_epoch <= 0 or start_epoch >= boundary_epoch:
            raise TrainingDataInputError(
                "Resolved target-size execution has an invalid boundary/start epoch pair."
            )
        object.__setattr__(self, "boundary_epoch", boundary_epoch)
        object.__setattr__(self, "start_epoch", start_epoch)


@dataclass(frozen=True, slots=True)
class TargetSizeCellCompletionRecord:
    """Immutable per-cell completion record binding complete cross-boundary provenance."""

    kind: str
    window_digest: str
    experiment_definition_digest: str
    execution_context_digest: str
    common_preparation_digest: str
    trajectory_digest: str
    target_size: int
    optimizer_seed: int
    materialization_digest: str
    boundary_epoch: int
    outcome_digest: str
    outcome: BoundaryOutcome
    boundary_snapshot_digest: str | None = None
    eval2_role_digest: str | None = None
    evaluation_data_digest: str | None = None
    prediction_evidence_digest: str | None = None
    eval2_metric_record_digest: str | None = None
    failure_record_digest: str | None = None
    planned_rung_digest: str | None = None
    predecessor_continuation_digest: str | None = None
    failure_evidence_digest: str | None = None
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if self.kind not in ("success", "train2_failure", "eval2_failure"):
            raise TrainingDataInputError(
                f"Unsupported cell completion record kind: {self.kind!r}"
            )
        for name in (
            "window_digest",
            "experiment_definition_digest",
            "execution_context_digest",
            "common_preparation_digest",
            "trajectory_digest",
            "materialization_digest",
            "outcome_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for opt_name in (
            "boundary_snapshot_digest",
            "eval2_role_digest",
            "evaluation_data_digest",
            "prediction_evidence_digest",
            "eval2_metric_record_digest",
            "failure_record_digest",
            "planned_rung_digest",
            "predecessor_continuation_digest",
            "failure_evidence_digest",
        ):
            val = getattr(self, opt_name)
            if val is not None:
                object.__setattr__(
                    self, opt_name, validate_digest(val, name=opt_name)
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

        if self.kind == "success":
            if (
                self.boundary_snapshot_digest is None
                or self.eval2_role_digest is None
                or self.evaluation_data_digest is None
                or self.prediction_evidence_digest is None
                or self.eval2_metric_record_digest is None
            ):
                raise TrainingDataInputError(
                    "Success completion record requires snapshot, role, evaluation data, prediction evidence, and metric record digests."
                )
            if isinstance(self.outcome, TargetSizeNumericalFailure):
                raise TrainingDataInputError(
                    "Success completion record cannot have numerical failure outcome."
                )
            if any(
                value is not None
                for value in (
                    self.failure_record_digest,
                    self.failure_evidence_digest,
                )
            ):
                raise TrainingDataInputError(
                    "Success completion record contains failure-only provenance."
                )
            if self.planned_rung_digest is None:
                raise TrainingDataInputError(
                    "Success completion record requires planned_rung_digest."
                )
        elif self.kind == "train2_failure":
            if self.failure_record_digest is None:
                raise TrainingDataInputError(
                    "TRAIN2 failure completion record requires failure_record_digest."
                )
            if self.planned_rung_digest is None:
                raise TrainingDataInputError(
                    "TRAIN2 failure completion record requires planned_rung_digest."
                )
            if (
                self.boundary_snapshot_digest is not None
                or self.eval2_role_digest is not None
                or self.evaluation_data_digest is not None
                or self.prediction_evidence_digest is not None
                or self.eval2_metric_record_digest is not None
            ):
                raise TrainingDataInputError(
                    "TRAIN2 failure completion record must not bind completed boundary snapshot or EVAL2 objects."
                )
            if not isinstance(self.outcome, TargetSizeNumericalFailure):
                raise TrainingDataInputError(
                    "TRAIN2 failure completion record requires TargetSizeNumericalFailure outcome."
                )
        elif self.kind == "eval2_failure":
            if (
                self.boundary_snapshot_digest is None
                or self.eval2_role_digest is None
                or self.evaluation_data_digest is None
                or self.failure_record_digest is None
            ):
                raise TrainingDataInputError(
                    "EVAL2 failure completion record requires snapshot, role, evaluation data, and failure record digests."
                )
            if self.prediction_evidence_digest is None:
                raise TrainingDataInputError(
                    "EVAL2 failure completion record requires prediction_evidence_digest."
                )
            if self.eval2_metric_record_digest is not None:
                raise TrainingDataInputError(
                    "EVAL2 failure completion record must not bind a successful metric record."
                )
            if not isinstance(self.outcome, TargetSizeNumericalFailure):
                raise TrainingDataInputError(
                    "EVAL2 failure completion record requires TargetSizeNumericalFailure outcome."
                )

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
            "kind": self.kind,
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
            "failure_record_digest": self.failure_record_digest,
            "planned_rung_digest": self.planned_rung_digest,
            "predecessor_continuation_digest": self.predecessor_continuation_digest,
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
        kind = str(payload.get("kind", "success"))
        result = cls(
            kind=kind,
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
            boundary_snapshot_digest=(
                None
                if payload.get("boundary_snapshot_digest") is None
                else str(payload["boundary_snapshot_digest"])
            ),
            eval2_role_digest=(
                None
                if payload.get("eval2_role_digest") is None
                else str(payload["eval2_role_digest"])
            ),
            evaluation_data_digest=(
                None
                if payload.get("evaluation_data_digest") is None
                else str(payload["evaluation_data_digest"])
            ),
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
            failure_record_digest=(
                None
                if payload.get("failure_record_digest") is None
                else str(payload["failure_record_digest"])
            ),
            planned_rung_digest=(
                None
                if payload.get("planned_rung_digest") is None
                else str(payload["planned_rung_digest"])
            ),
            predecessor_continuation_digest=(
                None
                if payload.get("predecessor_continuation_digest") is None
                else str(payload["predecessor_continuation_digest"])
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


def _validate_target_size_rung_ancestry(
    *,
    trajectory: Any,
    boundary_epoch: int,
    planned_rung: Any,
    schedule: TargetSizeScreenSchedule,
    predecessor_continuation: Any | None,
) -> tuple[str, str | None]:
    """Validate the exact TRAIN2 rung and its immutable predecessor identity."""

    from mdstats.training_data.train2_runtime import Train2RuntimePlan
    from .execution import (
        TargetSizeBoundarySnapshot,
        TargetSizeContinuationRequest,
        target_size_rung_plan,
    )

    boundary = schedule.validate_boundary_epoch(int(boundary_epoch))
    if not isinstance(planned_rung, Train2RuntimePlan):
        raise TrainingDataInputError(
            "Completion record requires the exact Train2RuntimePlan rung object."
        )
    if int(planned_rung.execution_epoch_limit) != boundary:
        raise TrainingDataInputError(
            "Completion record planned rung limit does not match the boundary."
        )
    expected_plan = target_size_rung_plan(
        trajectory, schedule, boundary_epoch=boundary
    )
    if planned_rung.content_digest != expected_plan.content_digest:
        raise TrainingDataInputError(
            "Completion record planned rung differs from the exact trajectory/schedule rung plan."
        )

    predecessor_digest: str | None = None
    if boundary == schedule.n1:
        if predecessor_continuation is not None:
            from .execution import TargetSizeContinuationRequest

            if not isinstance(predecessor_continuation, TargetSizeContinuationRequest):
                raise TrainingDataInputError(
                    "Initial n1 ancestry must be an authenticated initial continuation request."
                )
            if (
                predecessor_continuation.trajectory_digest != trajectory.content_digest
                or predecessor_continuation.predecessor_boundary_epoch is not None
            ):
                raise TrainingDataInputError(
                    "Initial n1 continuation request must bind this trajectory and have no predecessor boundary."
                )
            predecessor_digest = predecessor_continuation.content_digest
    else:
        if predecessor_continuation is None:
            raise TrainingDataInputError(
                "Continuation n2/n3 rung requires the exact predecessor continuation."
            )
        previous = schedule.fidelity_epochs[
            schedule.fidelity_epochs.index(boundary) - 1
        ]
        if isinstance(predecessor_continuation, TargetSizeBoundarySnapshot):
            if (
                predecessor_continuation.trajectory_digest != trajectory.content_digest
                or predecessor_continuation.boundary_epoch != previous
                or predecessor_continuation.rung_plan_digest
                != target_size_rung_plan(
                    trajectory, schedule, boundary_epoch=previous
                ).content_digest
            ):
                raise TrainingDataInputError(
                    "Predecessor boundary snapshot is not the exact previous rung."
                )
        elif isinstance(predecessor_continuation, TargetSizeContinuationRequest):
            if (
                predecessor_continuation.trajectory_digest != trajectory.content_digest
                or predecessor_continuation.predecessor_boundary_epoch != previous
            ):
                raise TrainingDataInputError(
                    "Predecessor continuation request is not the exact previous rung."
                )
        else:
            raise TrainingDataInputError(
                "Predecessor continuation must be an authenticated boundary snapshot or continuation request."
            )
        predecessor_digest = predecessor_continuation.content_digest
    return planned_rung.content_digest, predecessor_digest


def build_target_size_success_cell_completion_record(
    *,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    materialization: Any,
    boundary_snapshot: Any,
    eval2_role: Any,
    evaluation_data: Any,
    prediction_evidence: Any,
    eval2_metric_record: Any,
    planned_rung: Any,
    schedule: TargetSizeScreenSchedule,
    predecessor_continuation: Any | None = None,
    outcome: BoundaryOutcome | None = None,
) -> TargetSizeCellCompletionRecord:
    """Build and validate one immutable success cell completion record."""
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
    if eval2_role.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role belongs to a different trajectory."
        )
    if eval2_role.boundary_epoch != boundary_snapshot.boundary_epoch:
        raise TrainingDataInputError(
            "EVAL2 role epoch does not match boundary snapshot."
        )
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
    if eval2_role.boundary_state_digest != boundary_snapshot.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role does not bind this boundary snapshot."
        )
    if eval2_role.evaluation_data_digest != evaluation_data.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role does not bind this evaluation data artifact."
        )
    if prediction_evidence.role_digest != eval2_role.content_digest:
        raise TrainingDataInputError(
            "Prediction evidence does not bind this EVAL2 role."
        )
    if (
        prediction_evidence.boundary_state_digest
        != boundary_snapshot.content_digest
    ):
        raise TrainingDataInputError(
            "Prediction evidence does not bind this boundary snapshot."
        )
    if (
        prediction_evidence.evaluation_data_digest
        != evaluation_data.content_digest
    ):
        raise TrainingDataInputError(
            "Prediction evidence does not bind this evaluation data artifact."
        )
    if eval2_metric_record.target_role_digest != eval2_role.content_digest:
        raise TrainingDataInputError(
            "EVAL2 metric record does not bind this EVAL2 role."
        )
    if (
        eval2_metric_record.prediction_digest
        != prediction_evidence.prediction_payload_digest
    ):
        raise TrainingDataInputError(
            "EVAL2 metric record does not bind this prediction payload."
        )

    planned_rung_digest, predecessor_digest = _validate_target_size_rung_ancestry(
        trajectory=trajectory,
        boundary_epoch=boundary_snapshot.boundary_epoch,
        planned_rung=planned_rung,
        schedule=schedule,
        predecessor_continuation=predecessor_continuation,
    )

    from .evaluation import target_size_boundary_metric_from_eval2_record

    derived_outcome = target_size_boundary_metric_from_eval2_record(
        eval2_role, eval2_metric_record
    )
    if (
        outcome is not None
        and outcome.content_digest != derived_outcome.content_digest
    ):
        raise TrainingDataInputError(
            "Supplied outcome does not match outcome derived from EVAL2 metric record."
        )

    boundary_epoch = boundary_snapshot.boundary_epoch
    return TargetSizeCellCompletionRecord(
        kind="success",
        window_digest=window.content_digest,
        experiment_definition_digest=window.experiment_definition_digest,
        execution_context_digest=window.execution_context_digest,
        common_preparation_digest=window.common_preparation_digest,
        trajectory_digest=trajectory.content_digest,
        target_size=trajectory.target_size,
        optimizer_seed=trajectory.optimizer_seed,
        materialization_digest=materialization.content_digest,
        boundary_epoch=boundary_epoch,
        boundary_snapshot_digest=boundary_snapshot.content_digest,
        eval2_role_digest=eval2_role.content_digest,
        evaluation_data_digest=evaluation_data.content_digest,
        prediction_evidence_digest=prediction_evidence.content_digest,
        eval2_metric_record_digest=eval2_metric_record.content_digest,
        planned_rung_digest=planned_rung_digest,
        predecessor_continuation_digest=predecessor_digest,
        outcome_digest=derived_outcome.content_digest,
        outcome=derived_outcome,
        failure_evidence_digest=None,
    )


def build_target_size_train2_failure_cell_completion_record(
    *,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    materialization: Any,
    failure_record: Any,
    planned_rung: Any,
    schedule: TargetSizeScreenSchedule,
    definition: TargetSizeExperimentDefinition | None = None,
    predecessor_continuation: Any | None = None,
    checkpoint_directory: str | Path | None = None,
    outcome: BoundaryOutcome | None = None,
) -> TargetSizeCellCompletionRecord:
    """Build and validate one immutable TRAIN2 failure cell completion record from raw evidence."""
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

    from mdstats.training_data.train2_runtime import (
        Train2NumericalFailureRecord,
        Train2RuntimePlan,
    )
    from .execution import target_size_rung_plan

    if not isinstance(failure_record, Train2NumericalFailureRecord):
        raise TrainingDataInputError(
            "TRAIN2 failure completion record requires a real Train2NumericalFailureRecord."
        )
    if failure_record.raw_checkpoint_sha256 is not None:
        validate_digest(
            failure_record.raw_checkpoint_sha256,
            name="raw_checkpoint_sha256",
        )

    if not isinstance(planned_rung, Train2RuntimePlan):
        raise TrainingDataInputError(
            "TRAIN2 failure completion record requires the exact Train2RuntimePlan rung object."
        )
    rung_epoch = int(planned_rung.execution_epoch_limit)
    try:
        schedule.validate_boundary_epoch(rung_epoch)
    except TrainingDataInputError:
        raise
    expected_plan = target_size_rung_plan(
        trajectory, schedule, boundary_epoch=rung_epoch
    )
    if planned_rung.content_digest != expected_plan.content_digest:
        raise TrainingDataInputError(
            "TRAIN2 failure completion record planned rung differs from the exact trajectory/schedule rung plan."
        )
    if failure_record.plan_digest != planned_rung.content_digest:
        raise TrainingDataInputError(
            "TRAIN2 failure record does not bind the exact planned rung."
        )
    if checkpoint_directory is None:
        raise TrainingDataInputError(
            "TRAIN2 failure completion record requires the durable raw checkpoint directory."
        )
    checkpoint_path = Path(checkpoint_directory) / failure_record.raw_checkpoint_name
    if not checkpoint_path.is_file():
        raise TrainingDataInputError(
            "TRAIN2 failure completion record raw checkpoint bytes are missing."
        )
    checkpoint_sha = __import__("hashlib").sha256(
        checkpoint_path.read_bytes()
    ).hexdigest()
    if checkpoint_sha != failure_record.raw_checkpoint_sha256:
        raise TrainingDataInputError(
            "TRAIN2 failure completion record raw checkpoint SHA-256 mismatch."
        )

    if definition is None:
        raise TrainingDataInputError(
            "TRAIN2 failure completion record requires the accepted experiment definition for raw translation."
        )

    _, predecessor_digest = _validate_target_size_rung_ancestry(
        trajectory=trajectory,
        boundary_epoch=rung_epoch,
        planned_rung=planned_rung,
        schedule=schedule,
        predecessor_continuation=predecessor_continuation,
    )

    from .execution import translate_target_size_train2_failure

    if definition.content_digest != window.experiment_definition_digest:
        raise TrainingDataInputError(
            "Definition content digest does not match window."
        )
    derived_outcome = translate_target_size_train2_failure(
        failure_record,
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=rung_epoch,
    )
    if (
        outcome is not None
        and outcome.content_digest != derived_outcome.content_digest
    ):
        raise TrainingDataInputError(
            "Supplied outcome does not match derived TRAIN2 failure outcome."
        )

    return TargetSizeCellCompletionRecord(
        kind="train2_failure",
        window_digest=window.content_digest,
        experiment_definition_digest=window.experiment_definition_digest,
        execution_context_digest=window.execution_context_digest,
        common_preparation_digest=window.common_preparation_digest,
        trajectory_digest=trajectory.content_digest,
        target_size=trajectory.target_size,
        optimizer_seed=trajectory.optimizer_seed,
        materialization_digest=materialization.content_digest,
        boundary_epoch=derived_outcome.boundary_epoch,
        failure_record_digest=failure_record.content_digest,
        planned_rung_digest=planned_rung.content_digest,
        predecessor_continuation_digest=predecessor_digest,
        outcome_digest=derived_outcome.content_digest,
        outcome=derived_outcome,
        failure_evidence_digest=derived_outcome.classification_evidence_digest,
    )


def build_target_size_eval2_failure_cell_completion_record(
    *,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    materialization: Any,
    boundary_snapshot: Any,
    eval2_role: Any,
    evaluation_data: Any,
    prediction_evidence: Any,
    failure_record: Any,
    planned_rung: Any,
    schedule: TargetSizeScreenSchedule,
    predecessor_continuation: Any | None = None,
    outcome: BoundaryOutcome | None = None,
) -> TargetSizeCellCompletionRecord:
    """Build and validate one immutable EVAL2 failure cell completion record."""
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

    from mdstats.training_data.eval2 import Eval2NumericalEvaluationError
    if not isinstance(failure_record, Eval2NumericalEvaluationError):
        raise TrainingDataInputError(
            "EVAL2 failure completion record requires a real Eval2NumericalEvaluationError."
        )

    if failure_record.target_role_digest != eval2_role.content_digest:
        raise TrainingDataInputError(
            "EVAL2 failure error does not bind this EVAL2 role."
        )
    if (
        failure_record.prediction_digest
        != prediction_evidence.prediction_payload_digest
    ):
        raise TrainingDataInputError(
            "EVAL2 failure error does not bind this prediction payload."
        )
    if eval2_role.boundary_state_digest != boundary_snapshot.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role does not bind this boundary snapshot."
        )
    if eval2_role.evaluation_data_digest != evaluation_data.content_digest:
        raise TrainingDataInputError(
            "EVAL2 role does not bind this evaluation data artifact."
        )
    if prediction_evidence.role_digest != eval2_role.content_digest:
        raise TrainingDataInputError(
            "Prediction evidence does not bind this EVAL2 role."
        )
    if (
        prediction_evidence.boundary_state_digest
        != boundary_snapshot.content_digest
    ):
        raise TrainingDataInputError(
            "Prediction evidence does not bind this boundary snapshot."
        )
    if (
        prediction_evidence.evaluation_data_digest
        != evaluation_data.content_digest
    ):
        raise TrainingDataInputError(
            "Prediction evidence does not bind this evaluation data artifact."
        )

    planned_rung_digest, predecessor_digest = _validate_target_size_rung_ancestry(
        trajectory=trajectory,
        boundary_epoch=boundary_snapshot.boundary_epoch,
        planned_rung=planned_rung,
        schedule=schedule,
        predecessor_continuation=predecessor_continuation,
    )

    from .evaluation import translate_target_size_eval2_failure

    derived_outcome = translate_target_size_eval2_failure(
        eval2_role, failure_record
    )
    if (
        outcome is not None
        and outcome.content_digest != derived_outcome.content_digest
    ):
        raise TrainingDataInputError(
            "Supplied outcome does not match outcome derived from EVAL2 failure record."
        )

    return TargetSizeCellCompletionRecord(
        kind="eval2_failure",
        window_digest=window.content_digest,
        experiment_definition_digest=window.experiment_definition_digest,
        execution_context_digest=window.execution_context_digest,
        common_preparation_digest=window.common_preparation_digest,
        trajectory_digest=trajectory.content_digest,
        target_size=trajectory.target_size,
        optimizer_seed=trajectory.optimizer_seed,
        materialization_digest=materialization.content_digest,
        boundary_epoch=boundary_snapshot.boundary_epoch,
        boundary_snapshot_digest=boundary_snapshot.content_digest,
        eval2_role_digest=eval2_role.content_digest,
        evaluation_data_digest=evaluation_data.content_digest,
        prediction_evidence_digest=prediction_evidence.content_digest,
        failure_record_digest=failure_record.content_digest,
        planned_rung_digest=planned_rung_digest,
        predecessor_continuation_digest=predecessor_digest,
        outcome_digest=derived_outcome.content_digest,
        outcome=derived_outcome,
        failure_evidence_digest=derived_outcome.classification_evidence_digest,
    )


def build_target_size_cell_completion_record(
    *,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    materialization: Any,
    boundary_snapshot: Any | None = None,
    eval2_role: Any | None = None,
    evaluation_data: Any | None = None,
    outcome: BoundaryOutcome | None = None,
    prediction_evidence: Any | None = None,
    eval2_metric_record: Any | None = None,
    failure_record: Any | None = None,
    failure_evidence_digest: str | None = None,
    planned_rung_digest: str | None = None,
    predecessor_continuation_digest: str | None = None,
    kind: str = "success",
    planned_rung: Any | None = None,
    schedule: TargetSizeScreenSchedule | None = None,
    predecessor_continuation: Any | None = None,
    definition: TargetSizeExperimentDefinition | None = None,
    checkpoint_directory: str | Path | None = None,
) -> TargetSizeCellCompletionRecord:
    """Build and validate one immutable per-cell completion record (dispatcher)."""
    if kind == "success":
        if (
            boundary_snapshot is None
            or eval2_role is None
            or evaluation_data is None
            or prediction_evidence is None
            or eval2_metric_record is None
            or planned_rung is None
            or schedule is None
        ):
            raise TrainingDataInputError(
                "Success completion record requires snapshot, role, evaluation data, "
                "prediction evidence, EVAL2 metric record, exact planned rung, and schedule."
            )
        return build_target_size_success_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            boundary_snapshot=boundary_snapshot,
            eval2_role=eval2_role,
            evaluation_data=evaluation_data,
            prediction_evidence=prediction_evidence,
            eval2_metric_record=eval2_metric_record,
            planned_rung=planned_rung,
            schedule=schedule,
            predecessor_continuation=predecessor_continuation,
            outcome=outcome,
        )
    elif kind == "train2_failure":
        if (
            failure_record is None
            or planned_rung is None
            or schedule is None
            or definition is None
            or checkpoint_directory is None
        ):
            raise TrainingDataInputError(
                "TRAIN2 failure completion record requires raw failure_record, exact planned_rung, schedule, definition, and raw checkpoint directory."
            )
        return build_target_size_train2_failure_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            failure_record=failure_record,
            planned_rung=planned_rung,
            schedule=schedule,
            definition=definition,
            predecessor_continuation=predecessor_continuation,
            checkpoint_directory=checkpoint_directory,
            outcome=outcome,
        )
    elif kind == "eval2_failure":
        if (
            boundary_snapshot is None
            or eval2_role is None
            or evaluation_data is None
            or prediction_evidence is None
            or failure_record is None
            or planned_rung is None
            or schedule is None
        ):
            raise TrainingDataInputError(
                "EVAL2 failure completion record requires snapshot, role, evaluation data, "
                "prediction evidence, failure record, exact planned rung, and schedule."
            )
        return build_target_size_eval2_failure_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            boundary_snapshot=boundary_snapshot,
            eval2_role=eval2_role,
            evaluation_data=evaluation_data,
            prediction_evidence=prediction_evidence,
            failure_record=failure_record,
            planned_rung=planned_rung,
            schedule=schedule,
            predecessor_continuation=predecessor_continuation,
            outcome=outcome,
        )
    else:
        raise TrainingDataInputError(f"Unknown cell completion kind: {kind!r}")


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
    res = _publish_create_or_verify(
        path, window.to_dict(), deserializer=TargetSizeScreenWindow.from_dict
    )
    return res


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

    membership_digest = definition.evaluation_order.membership_digest(
        evaluation_size
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


def _resolve_publication_parent(
    resolver: TargetSizeExecutionResolver,
    expected_digest: str | None,
    supplied: Any | None,
    *,
    name: str,
    loader: Callable[[str], Any],
) -> Any | None:
    """Resolve one supplied-or-omitted parent through the typed CAS owner."""

    if expected_digest is None:
        if supplied is not None:
            raise TrainingDataInputError(
                f"Completion does not bind a {name} parent, but one was supplied."
            )
        return None
    expected = validate_digest(expected_digest, name=f"{name}_digest")
    if supplied is None:
        supplied = loader(expected)
    observed = getattr(supplied, "content_digest", None)
    if observed != expected:
        raise TrainingDataInputError(
            f"Supplied/resolved {name} parent does not match its completion digest."
        )
    return supplied


def _resolve_publication_parent_graph(
    root: str | Path,
    authority: TargetSizeRestartAuthority,
    trajectory: Any,
    completion_record: TargetSizeCellCompletionRecord,
    *,
    materialization: Any | None,
    boundary_snapshot: Any | None,
    eval2_role: Any | None,
    evaluation_data: Any | None,
    prediction_evidence: Any | None,
    eval2_metric_record: Any | None,
    failure_record: Any | None,
    planned_rung: Any | None,
    predecessor_continuation: Any | None,
    failure_checkpoint_directory: str | Path | None,
) -> dict[str, Any | None]:
    """Resolve and type-check the complete variant-specific publication graph.

    This phase intentionally performs no completion/progress writes.  Omitted
    arguments are only conveniences for an idempotent retry: every omitted
    digest-bound parent is loaded from the same typed resolver used by replay.
    """

    if not isinstance(authority, TargetSizeRestartAuthority):
        raise TrainingDataInputError(
            "Completion publication requires one complete TargetSizeRestartAuthority."
        )
    root_path = Path(root).resolve()
    if authority.resolver.root_directory != root_path:
        raise TrainingDataInputError(
            "Completion publication root does not match the restart resolver root."
        )

    from ..eval2 import Eval2NumericalEvaluationError, Eval2TargetMetricRecord
    from ..train2_runtime import Train2NumericalFailureRecord, Train2RuntimePlan
    from .candidate import (
        TargetSizeCandidateMaterialization,
        TargetSizeCandidateTrajectory,
    )
    from .evaluation import TargetSizeEval2Role, TargetSizePredictionEvidence
    from .execution import TargetSizeBoundarySnapshot
    from .export import TargetSizeEvaluationArtifact

    if not isinstance(trajectory, TargetSizeCandidateTrajectory):
        raise TrainingDataInputError(
            "Completion publication requires a typed candidate trajectory."
        )
    if (
        completion_record.trajectory_digest != trajectory.content_digest
        or completion_record.experiment_definition_digest
        != authority.aggregate.definition.content_digest
        or completion_record.execution_context_digest
        != authority.context.content_digest
        or completion_record.common_preparation_digest
        != authority.common.content_digest
        or trajectory.target_size != completion_record.target_size
        or trajectory.optimizer_seed != completion_record.optimizer_seed
    ):
        raise TrainingDataInputError(
            "Completion record does not bind the accepted trajectory/P1/P2 cell identity."
        )

    resolved_materialization = _resolve_publication_parent(
        authority.resolver,
        completion_record.materialization_digest,
        materialization,
        name="candidate materialization",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.materialization_path(value),
            value,
            TargetSizeCandidateMaterialization.from_dict,
        ),
    )
    if not isinstance(resolved_materialization, TargetSizeCandidateMaterialization):
        raise TrainingDataInputError(
            "Completion publication candidate materialization has the wrong type."
        )

    resolved_planned_rung = _resolve_publication_parent(
        authority.resolver,
        completion_record.planned_rung_digest,
        planned_rung,
        name="planned rung",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.planned_rung_path(value),
            value,
            Train2RuntimePlan.from_dict,
        ),
    )
    if not isinstance(resolved_planned_rung, Train2RuntimePlan):
        raise TrainingDataInputError(
            "Completion publication planned rung has the wrong type."
        )

    resolved_predecessor = _resolve_publication_parent(
        authority.resolver,
        completion_record.predecessor_continuation_digest,
        predecessor_continuation,
        name="predecessor continuation",
        loader=lambda value: _load_predecessor_continuation(authority.resolver, value),
    )

    resolved_snapshot = _resolve_publication_parent(
        authority.resolver,
        completion_record.boundary_snapshot_digest,
        boundary_snapshot,
        name="boundary snapshot",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.snapshot_path(value),
            value,
            TargetSizeBoundarySnapshot.from_dict,
        ),
    )
    if resolved_snapshot is not None and not isinstance(
        resolved_snapshot, TargetSizeBoundarySnapshot
    ):
        raise TrainingDataInputError(
            "Completion publication boundary snapshot has the wrong type."
        )

    resolved_role = _resolve_publication_parent(
        authority.resolver,
        completion_record.eval2_role_digest,
        eval2_role,
        name="EVAL2 role",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.role_path(value),
            value,
            TargetSizeEval2Role.from_dict,
        ),
    )
    if resolved_role is not None and not isinstance(resolved_role, TargetSizeEval2Role):
        raise TrainingDataInputError("Completion publication EVAL2 role has the wrong type.")

    resolved_evaluation_data = _resolve_publication_parent(
        authority.resolver,
        completion_record.evaluation_data_digest,
        evaluation_data,
        name="evaluation artifact",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.evaluation_artifact_path(value),
            value,
            TargetSizeEvaluationArtifact.from_dict,
        ),
    )
    if resolved_evaluation_data is not None and not isinstance(
        resolved_evaluation_data, TargetSizeEvaluationArtifact
    ):
        raise TrainingDataInputError(
            "Completion publication evaluation artifact has the wrong type."
        )

    resolved_prediction = _resolve_publication_parent(
        authority.resolver,
        completion_record.prediction_evidence_digest,
        prediction_evidence,
        name="prediction evidence",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.prediction_evidence_path(value),
            value,
            TargetSizePredictionEvidence.from_dict,
        ),
    )
    if resolved_prediction is not None and not isinstance(
        resolved_prediction, TargetSizePredictionEvidence
    ):
        raise TrainingDataInputError(
            "Completion publication prediction evidence has the wrong type."
        )

    resolved_metric = _resolve_publication_parent(
        authority.resolver,
        completion_record.eval2_metric_record_digest,
        eval2_metric_record,
        name="EVAL2 metric",
        loader=lambda value: authority.resolver.load_typed_content_addressed(
            authority.resolver.eval2_metric_path(value),
            value,
            Eval2TargetMetricRecord.from_dict,
        ),
    )
    if resolved_metric is not None and not isinstance(
        resolved_metric, Eval2TargetMetricRecord
    ):
        raise TrainingDataInputError("Completion publication EVAL2 metric has the wrong type.")

    resolved_failure = _resolve_publication_parent(
        authority.resolver,
        completion_record.failure_record_digest,
        failure_record,
        name="raw numerical failure",
        loader=lambda value: authority.resolver.load_raw_failure(value),
    )
    if completion_record.kind == "train2_failure":
        if not isinstance(resolved_failure, Train2NumericalFailureRecord):
            raise TrainingDataInputError(
                "TRAIN2 completion publication requires a raw Train2NumericalFailureRecord."
            )
        if any(
            value is not None
            for value in (
                resolved_snapshot,
                resolved_role,
                resolved_evaluation_data,
                resolved_prediction,
                resolved_metric,
            )
        ):
            raise TrainingDataInputError(
                "TRAIN2 failure publication received EVAL2-only parents."
            )
        raw_name = str(getattr(resolved_failure, "raw_checkpoint_name", ""))
        raw_sha = getattr(resolved_failure, "raw_checkpoint_sha256", None)
        if not raw_name or Path(raw_name).name != raw_name or raw_sha is None:
            raise TrainingDataInputError(
                "TRAIN2 failure publication requires a safe raw checkpoint identity."
            )
        raw_sha = validate_digest(raw_sha, name="raw_checkpoint_sha256")
        if failure_checkpoint_directory is None:
            source_raw = authority.resolver.failure_bulk_directory(
                resolved_failure.content_digest
            ) / raw_name
        else:
            source_raw = Path(failure_checkpoint_directory).resolve() / raw_name
        if not source_raw.is_file():
            raise TrainingDataInputError(
                "TRAIN2 failure publication requires durable raw checkpoint bytes."
            )
        import hashlib

        if hashlib.sha256(source_raw.read_bytes()).hexdigest() != raw_sha:
            raise TrainingDataInputError(
                "TRAIN2 failure publication raw checkpoint SHA-256 mismatch."
            )
    elif completion_record.kind == "eval2_failure":
        if not isinstance(resolved_failure, Eval2NumericalEvaluationError):
            raise TrainingDataInputError(
                "EVAL2 completion publication requires a raw Eval2NumericalEvaluationError."
            )
        if any(
            value is None
            for value in (
                resolved_snapshot,
                resolved_role,
                resolved_evaluation_data,
                resolved_prediction,
            )
        ):
            raise TrainingDataInputError(
                "EVAL2 failure publication is missing a mandatory scientific parent."
            )
        if resolved_failure.prediction_digest != resolved_prediction.prediction_payload_digest:
            raise TrainingDataInputError(
                "EVAL2 failure error does not bind the exact prediction payload."
            )
    elif completion_record.kind == "success":
        if any(
            value is None
            for value in (
                resolved_snapshot,
                resolved_role,
                resolved_evaluation_data,
                resolved_prediction,
                resolved_metric,
            )
        ):
            raise TrainingDataInputError(
                "Success completion publication is missing a mandatory scientific parent."
            )
        if resolved_failure is not None:
            raise TrainingDataInputError(
                "Success completion publication received a failure parent."
            )
    else:  # pragma: no cover - completion record constructor already guards this
        raise TrainingDataInputError(
            f"Unsupported completion publication kind: {completion_record.kind!r}"
        )

    return {
        "materialization": resolved_materialization,
        "planned_rung": resolved_planned_rung,
        "predecessor_continuation": resolved_predecessor,
        "boundary_snapshot": resolved_snapshot,
        "eval2_role": resolved_role,
        "evaluation_data": resolved_evaluation_data,
        "prediction_evidence": resolved_prediction,
        "eval2_metric_record": resolved_metric,
        "failure_record": resolved_failure,
    }


def _reverify_published_parent_graph(
    authority: TargetSizeRestartAuthority,
    completion_record: TargetSizeCellCompletionRecord,
) -> None:
    """Run the same replay/scientific authorities before completion publication."""

    trajectory, optimizer_policy, _projection, materialization = (
        _validate_replayed_candidate_lineage(authority, completion_record)
    )
    planned_rung, _predecessor = _load_and_validate_replayed_rung_ancestry(
        authority, completion_record, trajectory
    )
    if completion_record.kind == "success":
        from .evaluation import target_size_boundary_metric_from_eval2_record

        snapshot, _eval_data, role, _prediction, _view, metric = (
            _validate_replayed_eval2_parents(
                authority,
                completion_record,
                trajectory,
                optimizer_policy,
                materialization,
            )
        )
        if snapshot.rung_plan_digest != planned_rung.content_digest:
            raise TrainingDataInputError(
                "Published success snapshot does not bind the exact planned rung."
            )
        if metric is None:
            raise TrainingDataInputError(
                "Success completion replay did not resolve its EVAL2 metric parent."
            )
        derived = target_size_boundary_metric_from_eval2_record(role, metric)
        if derived.content_digest != completion_record.outcome.content_digest:
            raise TrainingDataInputError(
                "Published success outcome differs from its authenticated replay metric."
            )
    elif completion_record.kind == "eval2_failure":
        from .evaluation import translate_target_size_eval2_failure
        from ..eval2 import Eval2NumericalEvaluationError

        snapshot, _eval_data, role, prediction, _view, metric = (
            _validate_replayed_eval2_parents(
                authority,
                completion_record,
                trajectory,
                optimizer_policy,
                materialization,
            )
        )
        if snapshot.rung_plan_digest != planned_rung.content_digest:
            raise TrainingDataInputError(
                "Published EVAL2 failure snapshot does not bind the exact planned rung."
            )
        if metric is not None:
            raise TrainingDataInputError(
                "EVAL2 failure completion replay unexpectedly resolved a metric parent."
            )
        failure = authority.resolver.load_raw_failure(
            completion_record.failure_record_digest or ""
        )
        if not isinstance(failure, Eval2NumericalEvaluationError):
            raise TrainingDataInputError(
                "EVAL2 failure replay did not resolve its raw error parent."
            )
        if failure.prediction_digest != prediction.prediction_payload_digest:
            raise TrainingDataInputError(
                "EVAL2 failure replay error/prediction linkage is foreign."
            )
        derived = translate_target_size_eval2_failure(role, failure)
        if derived.content_digest != completion_record.outcome.content_digest:
            raise TrainingDataInputError(
                "Published EVAL2 failure outcome differs from its raw replay evidence."
            )
    else:
        from .execution import translate_target_size_train2_failure
        from ..train2_runtime import Train2NumericalFailureRecord

        failure = authority.resolver.load_raw_failure(
            completion_record.failure_record_digest or ""
        )
        if not isinstance(failure, Train2NumericalFailureRecord):
            raise TrainingDataInputError(
                "TRAIN2 failure replay did not resolve its raw failure parent."
            )
        raw_name = str(failure.raw_checkpoint_name)
        raw_path = authority.resolver.failure_bulk_directory(
            failure.content_digest
        ) / raw_name
        if not raw_path.is_file():
            raise TrainingDataInputError(
                "TRAIN2 failure replay is missing its raw checkpoint bulk parent."
            )
        import hashlib

        if failure.raw_checkpoint_sha256 is None or hashlib.sha256(
            raw_path.read_bytes()
        ).hexdigest() != failure.raw_checkpoint_sha256:
            raise TrainingDataInputError(
                "TRAIN2 failure replay raw checkpoint bytes do not match the raw failure record."
            )
        derived = translate_target_size_train2_failure(
            failure,
            trajectory=trajectory,
            definition=authority.aggregate.definition,
            schedule=authority.schedule,
            scheduled_boundary_epoch=completion_record.boundary_epoch,
        )
        if derived.content_digest != completion_record.outcome.content_digest:
            raise TrainingDataInputError(
                "Published TRAIN2 failure outcome differs from its raw replay evidence."
            )


def record_candidate_boundary_outcome(
    root: str | Path,
    window: TargetSizeScreenWindow,
    trajectory: Any,
    completion_record: TargetSizeCellCompletionRecord,
    *,
    materialization: Any | None = None,
    boundary_snapshot: Any | None = None,
    eval2_role: Any | None = None,
    evaluation_data: Any | None = None,
    prediction_evidence: Any | None = None,
    eval2_metric_record: Any | None = None,
    failure_record: Any | None = None,
    planned_rung: Any | None = None,
    predecessor_continuation: Any | None = None,
    failure_checkpoint_directory: str | Path | None = None,
    restart_authority: TargetSizeRestartAuthority | None = None,
) -> TargetSizeCandidateOutcome:
    """Publish one completion only after its complete durable parent graph passes replay."""

    if completion_record.window_digest != window.content_digest:
        raise TrainingDataInputError(
            "Completion record belongs to a different screen window."
        )
    if completion_record.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Completion record belongs to a different trajectory."
        )
    resolver = TargetSizeExecutionResolver(Path(root))
    if restart_authority is None:
        raise TrainingDataInputError(
            "Completion publication requires the complete restart authority so omitted parents cannot bypass replay."
        )
    durable_window = restart_authority.resolver.load_typed_logical(
        restart_authority.resolver.root_directory / SCREEN_WINDOW_FILENAME,
        TargetSizeScreenWindow.from_dict,
    )
    if (
        durable_window.content_digest != window.content_digest
        or durable_window.aggregate_digest
        != restart_authority.aggregate.content_digest
        or durable_window.experiment_definition_digest
        != restart_authority.aggregate.definition.content_digest
        or durable_window.execution_context_digest
        != restart_authority.context.content_digest
        or durable_window.common_preparation_digest
        != restart_authority.common.content_digest
    ):
        raise TrainingDataInputError(
            "Completion publication window does not bind the durable restart authority."
        )
    resolved_graph = _resolve_publication_parent_graph(
        root,
        restart_authority,
        trajectory,
        completion_record,
        materialization=materialization,
        boundary_snapshot=boundary_snapshot,
        eval2_role=eval2_role,
        evaluation_data=evaluation_data,
        prediction_evidence=prediction_evidence,
        eval2_metric_record=eval2_metric_record,
        failure_record=failure_record,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor_continuation,
        failure_checkpoint_directory=failure_checkpoint_directory,
    )
    materialization = resolved_graph["materialization"]
    boundary_snapshot = resolved_graph["boundary_snapshot"]
    eval2_role = resolved_graph["eval2_role"]
    evaluation_data = resolved_graph["evaluation_data"]
    prediction_evidence = resolved_graph["prediction_evidence"]
    eval2_metric_record = resolved_graph["eval2_metric_record"]
    failure_record = resolved_graph["failure_record"]
    planned_rung = resolved_graph["planned_rung"]
    predecessor_continuation = resolved_graph["predecessor_continuation"]
    if planned_rung is not None and hasattr(planned_rung, "to_dict"):
        rung_path = resolver.planned_rung_path(planned_rung.content_digest)
        _publish_create_or_verify(
            rung_path,
            planned_rung.to_dict(),
            deserializer=__import__(
                "mdstats.training_data.train2_runtime",
                fromlist=["Train2RuntimePlan"],
            ).Train2RuntimePlan.from_dict,
        )
    if predecessor_continuation is not None and hasattr(
        predecessor_continuation, "to_dict"
    ):
        from .execution import TargetSizeBoundarySnapshot, TargetSizeContinuationRequest

        if isinstance(predecessor_continuation, TargetSizeBoundarySnapshot):
            predecessor_path = resolver.snapshot_path(
                predecessor_continuation.content_digest
            )
            predecessor_deserializer = TargetSizeBoundarySnapshot.from_dict
        elif isinstance(predecessor_continuation, TargetSizeContinuationRequest):
            predecessor_path = resolver.continuation_path(
                predecessor_continuation.content_digest
            )
            predecessor_deserializer = TargetSizeContinuationRequest.from_dict
        else:
            raise TrainingDataInputError(
                "Published predecessor must be an authenticated snapshot or continuation request."
            )
        _publish_create_or_verify(
            predecessor_path,
            predecessor_continuation.to_dict(),
            deserializer=predecessor_deserializer,
        )
    if boundary_snapshot is not None and hasattr(boundary_snapshot, "to_dict"):
        snap_path = resolver.snapshot_path(boundary_snapshot.content_digest)
        from .execution import TargetSizeBoundarySnapshot

        _publish_create_or_verify(
            snap_path,
            boundary_snapshot.to_dict(),
            deserializer=TargetSizeBoundarySnapshot.from_dict,
        )
    if hasattr(trajectory, "to_dict"):
        traj_path = resolver.trajectory_path(trajectory.content_digest)
        from .candidate import TargetSizeCandidateTrajectory

        _publish_create_or_verify(
            traj_path,
            trajectory.to_dict(),
            deserializer=TargetSizeCandidateTrajectory.from_dict,
        )
    if materialization is not None and hasattr(materialization, "to_dict"):
        mat_path = resolver.materialization_path(materialization.content_digest)
        from .candidate import TargetSizeCandidateMaterialization

        _publish_create_or_verify(
            mat_path,
            materialization.to_dict(),
            deserializer=TargetSizeCandidateMaterialization.from_dict,
        )
    if eval2_role is not None and hasattr(eval2_role, "to_dict"):
        role_path = resolver.role_path(eval2_role.content_digest)
        from .evaluation import TargetSizeEval2Role

        _publish_create_or_verify(
            role_path,
            eval2_role.to_dict(),
            deserializer=TargetSizeEval2Role.from_dict,
        )
    if evaluation_data is not None and hasattr(evaluation_data, "to_dict"):
        eval_path = resolver.evaluation_artifact_path(
            evaluation_data.content_digest
        )
        from .export import TargetSizeEvaluationArtifact

        _publish_create_or_verify(
            eval_path,
            evaluation_data.to_dict(),
            deserializer=TargetSizeEvaluationArtifact.from_dict,
        )
    if prediction_evidence is not None and hasattr(
        prediction_evidence, "to_dict"
    ):
        pred_path = resolver.prediction_evidence_path(
            prediction_evidence.content_digest
        )
        from .evaluation import TargetSizePredictionEvidence

        _publish_create_or_verify(
            pred_path,
            prediction_evidence.to_dict(),
            deserializer=TargetSizePredictionEvidence.from_dict,
        )
    if eval2_metric_record is not None and hasattr(
        eval2_metric_record, "to_dict"
    ):
        metric_path = resolver.eval2_metric_path(
            eval2_metric_record.content_digest
        )
        from ..eval2 import Eval2TargetMetricRecord

        _publish_create_or_verify(
            metric_path,
            eval2_metric_record.to_dict(),
            deserializer=Eval2TargetMetricRecord.from_dict,
        )
    if failure_record is not None and hasattr(failure_record, "to_dict"):
        fail_path = resolver.failure_record_path(failure_record.content_digest)
        if failure_record.__class__.__name__ == "Train2NumericalFailureRecord":
            from ..train2_runtime import Train2NumericalFailureRecord

            failure_deserializer = Train2NumericalFailureRecord.from_dict
        else:
            from ..eval2 import Eval2NumericalEvaluationError

            failure_deserializer = Eval2NumericalEvaluationError.from_dict
        _publish_create_or_verify(
            fail_path,
            failure_record.to_dict(),
            deserializer=failure_deserializer,
        )
        if failure_checkpoint_directory is not None:
            failure_bulk = resolver.failure_bulk_directory(
                failure_record.content_digest
            )
            raw_name = str(getattr(failure_record, "raw_checkpoint_name", ""))
            raw_sha = getattr(failure_record, "raw_checkpoint_sha256", None)
            if not raw_name or raw_sha is None:
                raise TrainingDataInputError(
                    "TRAIN2 failure publication requires raw checkpoint identity."
                )
            source_raw = Path(failure_checkpoint_directory) / raw_name
            if not source_raw.is_file():
                raise TrainingDataInputError(
                    "TRAIN2 failure publication raw checkpoint is missing."
                )
            raw_bytes = source_raw.read_bytes()
            publish_immutable_bytes_create_or_verify(
                failure_bulk / raw_name,
                raw_bytes,
                expected_sha256=validate_digest(raw_sha, name="raw_checkpoint_sha256"),
            )

    # Every parent is now present at its canonical path.  Re-run the exact
    # candidate-lineage, rung-ancestry, EVAL2/provider, bulk, and raw-failure
    # validators used during restart before exposing either authoritative
    # completion or logical progress.
    _reverify_published_parent_graph(restart_authority, completion_record)

    progress = TargetSizeCandidateOutcome(
        window_digest=window.content_digest,
        boundary_epoch=completion_record.boundary_epoch,
        trajectory_digest=trajectory.content_digest,
        completion_record_digest=completion_record.content_digest,
        outcome=completion_record.outcome,
    )
    progress_path = _candidate_outcome_path(
        resolver.root_directory,
        window.content_digest,
        progress.boundary_epoch,
        progress,
    )
    # Serialize the final completion/progress pair per logical screen root.
    # This closes the race in which two different completion records pass the
    # preflight concurrently and the losing record would otherwise become an
    # orphan after the progress-slot conflict.
    import fcntl

    publication_lock_path = resolver.root_directory / ".screen_publication.lock"
    with publication_lock_path.open("a+") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            # Preflight the logical cell slot before publishing a new
            # completion.  A conflicting progress pointer must not leave a
            # newly written orphan completion behind.
            if progress_path.exists():
                if not progress_path.is_file():
                    raise TrainingDataInputError(
                        f"Progress path exists but is not a file: {progress_path}"
                    )
                existing_progress = resolver.load_progress(progress_path)
                if existing_progress.content_digest != progress.content_digest:
                    raise TrainingDataInputError(
                        "Conflicting immutable progress record already exists for this logical cell."
                    )

            comp_path = resolver.completion_path(
                completion_record.boundary_epoch, completion_record.content_digest
            )
            _publish_create_or_verify(
                comp_path,
                completion_record.to_dict(),
                deserializer=TargetSizeCellCompletionRecord.from_dict,
            )

            res = _publish_create_or_verify(
                progress_path,
                progress.to_dict(),
                deserializer=TargetSizeCandidateOutcome.from_dict,
            )
            return res
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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
        c_path = (
            root_path
            / "completions"
            / str(boundary_epoch)
            / f"{prog.completion_record_digest}.json"
        )
        if not c_path.is_file():
            raise TrainingDataInputError(
                f"Missing cell completion record for progress: {c_path}"
            )
        rec = TargetSizeCellCompletionRecord.from_dict(
            json.loads(c_path.read_text(encoding="utf-8"))
        )
        if rec.content_digest != prog.completion_record_digest:
            raise TrainingDataInputError(
                "Completion record digest does not match progress reference."
            )
        completions.append(rec)
    completions.sort(key=lambda item: (item.target_size, item.optimizer_seed))
    return tuple(completions)


def collect_boundary_candidate_outcomes(
    root: str | Path,
    window: TargetSizeScreenWindow,
    *,
    boundary_epoch: int,
) -> tuple[TargetSizeCandidateOutcome, ...]:
    """Read all per-candidate progress outcomes for one boundary epoch."""

    root_path = Path(root)
    progress_dir = root_path / "progress" / str(boundary_epoch)
    if not progress_dir.is_dir():
        return ()
    results: list[TargetSizeCandidateOutcome] = []
    for path in sorted(progress_dir.glob("*.json")):
        record = TargetSizeCandidateOutcome.from_dict(
            json.loads(path.read_text(encoding="utf-8"))
        )
        if record.window_digest != window.content_digest:
            raise TrainingDataInputError(
                "Progress outcome belongs to a different screen window."
            )
        if record.boundary_epoch != int(boundary_epoch):
            raise TrainingDataInputError(
                "Progress outcome belongs to a different boundary epoch."
            )
        results.append(record)
    return tuple(results)


def load_target_size_boundary_batch(
    root: str | Path, batch_digest: str
) -> TargetSizeCompleteBoundaryBatch:
    """Load one persisted complete boundary batch by digest."""

    path = _batch_path(Path(root), batch_digest)
    if not path.is_file():
        raise TrainingDataInputError(
            f"Target size boundary batch missing: {path}"
        )
    return TargetSizeCompleteBoundaryBatch.from_dict(
        json.loads(path.read_text(encoding="utf-8"))
    )


def _batch_path(root: Path, content_digest: str) -> Path:
    return root / "batches" / f"{content_digest}.json"


def _head_path(root: Path, content_digest: str) -> Path:
    return root / "heads" / f"{content_digest}.json"


def persist_complete_boundary_batch(
    root: str | Path,
    batch: TargetSizeCompleteBoundaryBatch,
) -> Path:
    """Persist the complete boundary batch in content-addressed batches/<digest>.json."""

    path = _batch_path(Path(root), batch.content_digest)
    _publish_create_or_verify(
        path,
        batch.to_dict(),
        deserializer=TargetSizeCompleteBoundaryBatch.from_dict,
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


def _commit_target_size_boundary_batch_locked(
    root_path: Path,
    current_path: Path,
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    batch: TargetSizeCompleteBoundaryBatch,
) -> TargetSizeExecutionHead:
    parent_head_digest = None
    if current_path.is_file():
        current = TargetSizeExecutionHead.from_dict(
            json.loads(current_path.read_text(encoding="utf-8"))
        )
        immutable_current_path = _head_path(
            root_path, current.content_digest
        )
        if not immutable_current_path.is_file():
            raise TrainingDataInputError(
                "Current execution head pointer has no immutable head record."
            )
        immutable_current = TargetSizeExecutionHead.from_dict(
            json.loads(immutable_current_path.read_text(encoding="utf-8"))
        )
        if immutable_current.content_digest != current.content_digest:
            raise TrainingDataInputError(
                "Current execution head pointer differs from its immutable head record."
            )
        # Case 1: Exact retry already committed
        if current.batch_digest == batch.content_digest:
            if (
                current.pre_state_digest == state.content_digest
                and current.pre_state.content_digest == state.content_digest
            ):
                persisted_batch_path = _batch_path(
                    root_path, batch.content_digest
                )
                if not persisted_batch_path.is_file():
                    raise TrainingDataInputError(
                        "Exact batch retry is missing its immutable batch record."
                    )
                persisted_batch = TargetSizeCompleteBoundaryBatch.from_dict(
                    json.loads(
                        persisted_batch_path.read_text(encoding="utf-8")
                    )
                )
                if persisted_batch.content_digest != batch.content_digest:
                    raise TrainingDataInputError(
                        "Exact batch retry immutable record differs from the requested batch."
                    )
                expected_post = apply_complete_boundary_batch(
                    definition, state, persisted_batch
                )
                if (
                    current.post_state_digest != expected_post.content_digest
                    or current.post_state.content_digest
                    != expected_post.content_digest
                ):
                    raise TrainingDataInputError(
                        "Exact batch retry post-state is not the deterministic reducer result."
                    )
                return current
            raise TrainingDataInputError(
                "Conflicting batch commit: same batch digest but different pre-state."
            )

        # Case 2: Normal successor
        if current.post_state_digest != batch.pre_state_digest:
            raise TrainingDataInputError(
                "Current head does not provide this batch's exact pre-state."
            )
        parent_head_digest = current.content_digest
    else:
        # Initial batch commit
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
    _publish_create_or_verify(
        head_path,
        head.to_dict(),
        deserializer=TargetSizeExecutionHead.from_dict,
    )
    _atomic_json_write(current_path, head.to_dict())

    # Verification: ensure current pointer represents the exact immutable head
    verified = TargetSizeExecutionHead.from_dict(
        json.loads(current_path.read_text(encoding="utf-8"))
    )
    if verified.content_digest != head.content_digest:
        raise TrainingDataInputError(
            "Current head pointer verification failed after commit."
        )
    return head


def commit_target_size_boundary_batch(
    root: str | Path,
    definition: TargetSizeExperimentDefinition,
    state: TargetSizeReducerState,
    batch: TargetSizeCompleteBoundaryBatch,
) -> TargetSizeExecutionHead:
    """Persist batch first, apply deterministically, publish head atomically under CAS lock."""

    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)
    current_path = root_path / CURRENT_HEAD_FILENAME
    lock_path = root_path / ".screen_commit.lock"

    import fcntl
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _commit_target_size_boundary_batch_locked(
                root_path=root_path,
                current_path=current_path,
                definition=definition,
                state=state,
                batch=batch,
            )
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def load_current_execution_head(
    root: str | Path,
) -> TargetSizeExecutionHead | None:
    path = Path(root) / CURRENT_HEAD_FILENAME
    if not path.is_file():
        return None
    return TargetSizeExecutionHead.from_dict(
        json.loads(path.read_text(encoding="utf-8"))
    )


def _path_within_declared_root(path: str | Path, root: str | Path, *, name: str) -> Path:
    """Resolve a bulk locator and require it to remain under its authority root."""

    resolved_root = Path(root).resolve()
    resolved = Path(path).resolve()
    try:
        resolved.relative_to(resolved_root)
    except ValueError as exc:
        raise TrainingDataInputError(
            f"{name} resolves outside its declared bulk root."
        ) from exc
    return resolved


def _evaluation_bulk_root_for_artifact(
    authority: TargetSizeRestartAuthority,
    artifact: Any,
) -> Path:
    """Find the one declared evaluation bulk directory containing exact bytes."""

    from .export import _resolve_artifact_path

    declared = authority.bulk_root("evaluation")
    direct = _resolve_artifact_path(
        declared, artifact.relative_path, name="evaluation artifact path"
    )
    if direct.is_file():
        import hashlib

        if hashlib.sha256(direct.read_bytes()).hexdigest() == artifact.sha256:
            return declared

    relative = Path(str(artifact.relative_path))
    if relative.is_absolute() or ".." in relative.parts:
        raise TrainingDataInputError(
            "Evaluation artifact relative path is not an in-root locator."
        )
    matches: list[Path] = []
    for candidate in declared.rglob(relative.name):
        if not candidate.is_file() or candidate.name != relative.name:
            continue
        import hashlib

        if hashlib.sha256(candidate.read_bytes()).hexdigest() == artifact.sha256:
            matches.append(candidate.parent)
    unique = tuple(dict.fromkeys(matches))
    if len(unique) != 1:
        raise TrainingDataInputError(
            "Evaluation artifact bulk bytes are missing or have conflicting locations."
        )
    return unique[0]


def _load_predecessor_continuation(
    resolver: TargetSizeExecutionResolver,
    content_digest: str,
) -> Any:
    """Load either the typed continuation request or predecessor snapshot."""

    from .execution import TargetSizeBoundarySnapshot, TargetSizeContinuationRequest

    continuation_path = resolver.continuation_path(content_digest)
    snapshot_path = resolver.snapshot_path(content_digest)
    present = [path for path in (continuation_path, snapshot_path) if path.is_file()]
    if len(present) > 1:
        raise TrainingDataInputError(
            "Predecessor continuation digest has conflicting typed parents."
        )
    if not present:
        raise TrainingDataInputError(
            "Predecessor continuation/snapshot parent is missing."
        )
    if present[0] == continuation_path:
        return resolver.load_typed_content_addressed(
            continuation_path,
            content_digest,
            TargetSizeContinuationRequest.from_dict,
        )
    return resolver.load_typed_content_addressed(
        snapshot_path,
        content_digest,
        TargetSizeBoundarySnapshot.from_dict,
    )


def _validate_replayed_candidate_lineage(
    authority: TargetSizeRestartAuthority,
    record: TargetSizeCellCompletionRecord,
) -> tuple[Any, Any, Any, Any]:
    """Load and scientifically validate trajectory/materialization parents."""

    from .candidate import (
        TargetSizeCandidateMaterialization,
        TargetSizeCandidateTrajectory,
        validate_target_size_candidate_trajectory,
        validate_target_size_materialization,
    )

    resolver = authority.resolver
    trajectory = resolver.load_typed_content_addressed(
        resolver.trajectory_path(record.trajectory_digest),
        record.trajectory_digest,
        TargetSizeCandidateTrajectory.from_dict,
    )
    optimizer_policy = authority.optimizer_policy_for_seed(trajectory.optimizer_seed)
    projection = validate_target_size_candidate_trajectory(
        trajectory,
        authority.aggregate.definition,
        authority.context,
        authority.common,
        authority.schedule,
        optimizer_policy=optimizer_policy,
    )
    materialization = resolver.load_typed_content_addressed(
        resolver.materialization_path(record.materialization_digest),
        record.materialization_digest,
        TargetSizeCandidateMaterialization.from_dict,
    )
    if materialization.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Materialization parent does not bind the replayed trajectory."
        )
    materialization_root = materialization.output_directory
    if not materialization_root:
        raise TrainingDataInputError(
            "Materialization does not declare its durable bulk directory."
        )
    materialization_root = _path_within_declared_root(
        materialization_root,
        authority.bulk_root("materialization"),
        name="materialization bulk directory",
    )
    validate_target_size_materialization(
        materialization,
        trajectory,
        canonical_frame_authority=authority.canonical_frame_authority,
        materialization_directory=materialization_root,
        projection=projection,
        definition=authority.aggregate.definition,
        common=authority.common,
        optimizer_policy=optimizer_policy,
        extxyz_policy=authority.extxyz_policy,
        frame_catalog=authority.frame_catalog,
        frame_data_by_run=authority.frame_data_by_run,
        frame_array_index=authority.frame_array_index,
    )
    return trajectory, optimizer_policy, projection, materialization


def prepare_target_size_evaluation_artifact(
    authority: TargetSizeRestartAuthority,
    *,
    evaluation_size: int,
    output_directory: str | Path | None = None,
) -> tuple[Any, Path]:
    """Resolve/create one exact-M artifact under the declared evaluation root.

    The helper is intentionally owned by the target-size execution package so
    workers and restart clients use the same durable evaluation-root and policy
    contract instead of rebuilding ``eval_data_<epoch>`` path conventions.
    """

    if not isinstance(authority, TargetSizeRestartAuthority):
        raise TrainingDataInputError(
            "Evaluation artifact preparation requires one complete TargetSizeRestartAuthority."
        )
    declared_root = authority.bulk_root("evaluation")
    evaluation_root = (
        declared_root / "target_size_evaluation"
        if output_directory is None
        else _path_within_declared_root(
            output_directory,
            declared_root,
            name="evaluation artifact output directory",
        )
    )
    evaluation_root.mkdir(parents=True, exist_ok=True)

    from .export import (
        TargetSizeEvaluationArtifact,
        validate_target_size_evaluation_artifact,
        write_target_size_evaluation_artifact,
    )

    artifact = write_target_size_evaluation_artifact(
        evaluation_root,
        definition=authority.aggregate.definition,
        evaluation_size=int(evaluation_size),
        canonical_frame_authority=authority.canonical_frame_authority,
        frame_catalog=authority.frame_catalog,
        frame_data_by_run=authority.frame_data_by_run,
        policy=authority.extxyz_policy,
        frame_array_index=authority.frame_array_index,
    )
    if not isinstance(artifact, TargetSizeEvaluationArtifact):
        raise TrainingDataInputError(
            "Evaluation artifact owner returned an unexpected artifact type."
        )
    validate_target_size_evaluation_artifact(
        artifact,
        root_directory=evaluation_root,
        definition=authority.aggregate.definition,
        canonical_frame_authority=authority.canonical_frame_authority,
        policy=authority.extxyz_policy,
        frame_catalog=authority.frame_catalog,
        frame_data_by_run=authority.frame_data_by_run,
        frame_array_index=authority.frame_array_index,
    )
    return artifact, evaluation_root


def resolve_target_size_candidate_for_resume(
    root: str | Path,
    authority: TargetSizeRestartAuthority,
    *,
    boundary_epoch: int,
    target_size: int,
    optimizer_seed: int,
    state: TargetSizeReducerState | None = None,
    workspace_root: str | Path | None = None,
) -> TargetSizeResolvedCandidateExecution:
    """Resolve a surviving candidate's exact durable predecessor for TRAIN2.

    The caller may provide the post-reconciliation reducer state.  When it is
    omitted, this owner performs full root reconciliation first.  In either
    case the active cell, prior progress pointer, completion record, trajectory,
    materialization, predecessor snapshot, and continuation bytes are checked
    before a mutable worker workspace is created.
    """

    if not isinstance(authority, TargetSizeRestartAuthority):
        raise TrainingDataInputError(
            "Candidate resume requires one complete TargetSizeRestartAuthority."
        )
    root_path = Path(root).resolve()
    if authority.resolver.root_directory != root_path:
        raise TrainingDataInputError(
            "Candidate resume root does not match the restart resolver root."
        )

    active_state = state
    if active_state is None:
        head = reconcile_target_size_screen_root(root_path, authority)
        if head is None:
            raise TrainingDataInputError(
                "Candidate resume requires an initialized, reconciled screen root."
            )
        active_state = head.post_state
    if not isinstance(active_state, TargetSizeReducerState):
        raise TrainingDataInputError(
            "Candidate resume requires the authenticated reducer state after reconciliation."
        )

    definition = authority.aggregate.definition
    requirements = derive_active_boundary_requirements(definition, active_state)
    if requirements is None:
        raise TrainingDataInputError(
            "Cannot resolve a candidate resume after the reducer became terminal."
        )
    active_boundary, _evaluation_size, active_keys = requirements
    requested_boundary = authority.schedule.validate_boundary_epoch(
        int(boundary_epoch)
    )
    requested_key = (int(target_size), int(optimizer_seed))
    if requested_boundary != active_boundary or requested_key not in active_keys:
        raise TrainingDataInputError(
            "Requested candidate resume is not an exact surviving cell of the active boundary."
        )
    boundary_index = authority.schedule.fidelity_epochs.index(requested_boundary)
    if boundary_index <= 0:
        raise TrainingDataInputError(
            "The first screen rung has no predecessor continuation to resume."
        )
    previous_boundary = authority.schedule.fidelity_epochs[boundary_index - 1]

    window = authority.resolver.load_typed_logical(
        root_path / SCREEN_WINDOW_FILENAME,
        TargetSizeScreenWindow.from_dict,
    )
    if (
        window.aggregate_digest != authority.aggregate.content_digest
        or window.execution_context_digest != authority.context.content_digest
        or window.common_preparation_digest != authority.common.content_digest
    ):
        raise TrainingDataInputError(
            "Candidate resume screen window does not bind the accepted authority."
        )
    progress = authority.resolver.load_progress(
        authority.resolver.progress_path(
            window.content_digest,
            previous_boundary,
            requested_key[0],
            requested_key[1],
        )
    )
    if progress.outcome.target_size != requested_key[0] or progress.outcome.optimizer_seed != requested_key[1]:
        raise TrainingDataInputError(
            "Candidate resume progress pointer does not match the requested cell."
        )
    completion = authority.resolver.load_typed_content_addressed(
        authority.resolver.completion_path(
            previous_boundary, progress.completion_record_digest
        ),
        progress.completion_record_digest,
        TargetSizeCellCompletionRecord.from_dict,
    )
    if (
        completion.window_digest != window.content_digest
        or completion.boundary_epoch != previous_boundary
        or completion.target_size != requested_key[0]
        or completion.optimizer_seed != requested_key[1]
        or completion.outcome_digest != progress.outcome.content_digest
        or completion.kind != "success"
        or completion.boundary_snapshot_digest is None
    ):
        raise TrainingDataInputError(
            "Candidate resume predecessor completion is not an authenticated successful boundary cell."
        )

    trajectory, optimizer_policy, _projection, materialization = (
        _validate_replayed_candidate_lineage(authority, completion)
    )
    if (
        trajectory.target_size != requested_key[0]
        or trajectory.optimizer_seed != requested_key[1]
        or trajectory.content_digest != completion.trajectory_digest
    ):
        raise TrainingDataInputError(
            "Candidate resume trajectory does not match the durable cell identity."
        )
    planned_rung, _predecessor = _load_and_validate_replayed_rung_ancestry(
        authority, completion, trajectory
    )
    from .execution import TargetSizeBoundarySnapshot, validate_target_size_boundary_snapshot

    predecessor = authority.resolver.load_typed_content_addressed(
        authority.resolver.snapshot_path(completion.boundary_snapshot_digest),
        completion.boundary_snapshot_digest,
        TargetSizeBoundarySnapshot.from_dict,
    )

    if not isinstance(predecessor, TargetSizeBoundarySnapshot):
        raise TrainingDataInputError(
            "Candidate resume predecessor is not a boundary snapshot."
        )
    if (
        predecessor.boundary_epoch != previous_boundary
        or predecessor.rung_plan_digest != planned_rung.content_digest
    ):
        raise TrainingDataInputError(
            "Candidate resume predecessor snapshot is not the exact previous rung."
        )
    validate_target_size_boundary_snapshot(
        predecessor,
        snapshot_root=authority.bulk_root("snapshot"),
        trajectory=trajectory,
        schedule=authority.schedule,
    )

    declared_train2_root = authority.bulk_root("train2")
    base_workspace = (
        declared_train2_root / "continuation_workspaces"
        if workspace_root is None
        else _path_within_declared_root(
            workspace_root,
            declared_train2_root,
            name="TRAIN2 continuation workspace root",
        )
    )
    workspace = (
        base_workspace
        / trajectory.content_digest
        / f"from_boundary_{previous_boundary}"
    ).resolve()
    workspace.relative_to(declared_train2_root)
    workspace.mkdir(parents=True, exist_ok=True)
    snapshot_directory = _path_within_declared_root(
        authority.bulk_root("snapshot") / predecessor.snapshot_relative_dir,
        authority.bulk_root("snapshot"),
        name="predecessor snapshot directory",
    )
    raw_source = snapshot_directory / predecessor.raw_checkpoint_name
    companion_source = snapshot_directory / "train2_runtime.pt"
    summary_source = snapshot_directory / "train2_runtime.json"
    if not raw_source.is_file() or not companion_source.is_file() or not summary_source.is_file():
        raise TrainingDataInputError(
            "Authenticated predecessor snapshot is missing continuation files."
        )
    publish_immutable_bytes_create_or_verify(
        workspace / predecessor.raw_checkpoint_name,
        raw_source.read_bytes(),
        expected_sha256=predecessor.raw_checkpoint_sha256,
    )
    publish_immutable_bytes_create_or_verify(
        workspace / "train2_runtime.pt",
        companion_source.read_bytes(),
        expected_sha256=predecessor.companion_sha256,
    )
    from ..train2_runtime import Train2RuntimeSummary

    summary = Train2RuntimeSummary.from_dict(
        json.loads(summary_source.read_text(encoding="utf-8"))
    )
    if summary.content_digest != predecessor.runtime_summary_digest:
        raise TrainingDataInputError(
            "Predecessor snapshot runtime summary digest changed during resume resolution."
        )
    publish_immutable_json_create_or_verify(
        workspace / "train2_runtime.json",
        summary.to_dict(),
        deserializer=Train2RuntimeSummary.from_dict,
    )
    return TargetSizeResolvedCandidateExecution(
        trajectory=trajectory,
        optimizer_policy=optimizer_policy,
        materialization=materialization,
        predecessor_snapshot=predecessor,
        checkpoint_directory=workspace,
        boundary_epoch=requested_boundary,
        start_epoch=previous_boundary,
    )


def _load_and_validate_replayed_rung_ancestry(
    authority: TargetSizeRestartAuthority,
    record: TargetSizeCellCompletionRecord,
    trajectory: Any,
) -> tuple[Any, Any | None]:
    """Resolve the exact rung and predecessor before any outcome translation."""

    from .execution import target_size_rung_plan
    from ..train2_runtime import Train2RuntimePlan

    if record.planned_rung_digest is None:
        raise TrainingDataInputError(
            "Replay completion is missing its exact planned rung parent."
        )
    planned_rung = authority.resolver.load_typed_content_addressed(
        authority.resolver.planned_rung_path(record.planned_rung_digest),
        record.planned_rung_digest,
        Train2RuntimePlan.from_dict,
    )
    expected_plan = target_size_rung_plan(
        trajectory, authority.schedule, boundary_epoch=record.boundary_epoch
    )
    if planned_rung.content_digest != expected_plan.content_digest:
        raise TrainingDataInputError(
            "Replay planned rung differs from the trajectory/schedule authority."
        )
    predecessor = None
    if record.boundary_epoch != authority.schedule.n1:
        if record.predecessor_continuation_digest is None:
            raise TrainingDataInputError(
                "Replay later-rung completion is missing predecessor continuation."
            )
        predecessor = _load_predecessor_continuation(
            authority.resolver, record.predecessor_continuation_digest
        )
        _validate_target_size_rung_ancestry(
            trajectory=trajectory,
            boundary_epoch=record.boundary_epoch,
            planned_rung=planned_rung,
            schedule=authority.schedule,
            predecessor_continuation=predecessor,
        )
    elif record.predecessor_continuation_digest is not None:
        predecessor = _load_predecessor_continuation(
            authority.resolver, record.predecessor_continuation_digest
        )
        _validate_target_size_rung_ancestry(
            trajectory=trajectory,
            boundary_epoch=record.boundary_epoch,
            planned_rung=planned_rung,
            schedule=authority.schedule,
            predecessor_continuation=predecessor,
        )
    elif record.kind == "train2_failure":
        raise TrainingDataInputError(
            "Replay initial-rung TRAIN2 failure is missing its authenticated initial continuation request."
        )
    return planned_rung, predecessor


def _validate_replayed_eval2_parents(
    authority: TargetSizeRestartAuthority,
    record: TargetSizeCellCompletionRecord,
    trajectory: Any,
    optimizer_policy: Any,
    materialization: Any,
) -> tuple[Any, Any, Any, Any, Any, Any]:
    """Replay the complete EVAL2 ancestry and return role/view/pred/metric data."""

    from .evaluation import (
        TargetSizeEval2Role,
        TargetSizePredictionEvidence,
        _authenticate_target_size_provider,
        run_target_size_eval2_reduction,
        target_size_boundary_metric_from_eval2_record,
    )
    from .execution import TargetSizeBoundarySnapshot, validate_target_size_boundary_snapshot
    from .export import TargetSizeEvaluationArtifact, _resolve_artifact_path
    from ..eval2 import Eval2TargetMetricRecord
    import hashlib

    if (
        record.boundary_snapshot_digest is None
        or record.eval2_role_digest is None
        or record.evaluation_data_digest is None
        or record.prediction_evidence_digest is None
    ):
        raise TrainingDataInputError(
            "Replay EVAL2 completion is missing mandatory scientific parents."
        )
    snapshot = authority.resolver.load_typed_content_addressed(
        authority.resolver.snapshot_path(record.boundary_snapshot_digest),
        record.boundary_snapshot_digest,
        TargetSizeBoundarySnapshot.from_dict,
    )
    if snapshot.boundary_epoch != record.boundary_epoch:
        raise TrainingDataInputError(
            "Replay snapshot epoch does not match the completion boundary."
        )
    snapshot_root = authority.bulk_root("snapshot")
    snapshot_dir = _path_within_declared_root(
        snapshot_root / snapshot.snapshot_relative_dir,
        snapshot_root,
        name="snapshot bulk directory",
    )
    validate_target_size_boundary_snapshot(
        snapshot,
        snapshot_root=snapshot_root,
        trajectory=trajectory,
        schedule=authority.schedule,
    )
    eval_data = authority.resolver.load_typed_content_addressed(
        authority.resolver.evaluation_artifact_path(record.evaluation_data_digest),
        record.evaluation_data_digest,
        TargetSizeEvaluationArtifact.from_dict,
    )
    eval_root = _evaluation_bulk_root_for_artifact(authority, eval_data)
    from .export import validate_target_size_evaluation_artifact

    validate_target_size_evaluation_artifact(
        eval_data,
        root_directory=eval_root,
        definition=authority.aggregate.definition,
        canonical_frame_authority=authority.canonical_frame_authority,
        policy=authority.extxyz_policy,
        frame_catalog=authority.frame_catalog,
        frame_data_by_run=authority.frame_data_by_run,
        frame_array_index=authority.frame_array_index,
    )
    role = authority.resolver.load_typed_content_addressed(
        authority.resolver.role_path(record.eval2_role_digest),
        record.eval2_role_digest,
        TargetSizeEval2Role.from_dict,
    )
    from .evaluation import build_target_size_eval2_role

    expected_role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=authority.aggregate.definition,
        schedule=authority.schedule,
        correlation_blocks=authority.correlation_blocks,
        evaluation_data=eval_data,
    )
    if role.content_digest != expected_role.content_digest:
        raise TrainingDataInputError(
            "Replay EVAL2 role differs from the accepted P1/P2 role authority."
        )
    prediction = authority.resolver.load_typed_content_addressed(
        authority.resolver.prediction_evidence_path(record.prediction_evidence_digest),
        record.prediction_evidence_digest,
        TargetSizePredictionEvidence.from_dict,
    )
    if (
        prediction.role_digest != role.content_digest
        or prediction.boundary_state_digest != snapshot.content_digest
        or prediction.boundary_epoch != record.boundary_epoch
        or prediction.evaluation_model_state != trajectory.evaluation_model_state
        or prediction.evaluation_data_digest != eval_data.content_digest
        or prediction.trajectory_digest != trajectory.content_digest
        or prediction.evaluation_model_state != trajectory.evaluation_model_state
        or prediction.evaluation_membership_digest
        != eval_data.evaluation_membership_digest
        or prediction.evaluation_size != eval_data.evaluation_size
    ):
        raise TrainingDataInputError(
            "Replay prediction evidence does not bind the exact EVAL2 ancestry."
        )

    config_path = _resolve_artifact_path(
        _path_within_declared_root(
            materialization.output_directory,
            authority.bulk_root("materialization"),
            name="materialization bulk directory",
        ),
        materialization.mace_config_relative_path,
        name="candidate MACE configuration path",
    )
    config_bytes = config_path.read_bytes()
    config_payload = json.loads(config_bytes.decode("utf-8"))
    if hashlib.sha256(config_bytes).hexdigest() != materialization.mace_config_sha256:
        raise TrainingDataInputError("Replay candidate MACE configuration SHA changed.")
    if digest(config_payload) != materialization.mace_config_digest:
        raise TrainingDataInputError("Replay candidate MACE configuration digest changed.")
    if str(config_payload.get("device", "")) != str(optimizer_policy.device):
        raise TrainingDataInputError("Replay prediction device differs from optimizer policy.")
    if str(config_payload.get("default_dtype", "")) != str(trajectory.realization.default_dtype):
        raise TrainingDataInputError("Replay prediction dtype differs from trajectory realization.")
    provider, evaluated_digest, _companion = _authenticate_target_size_provider(
        raw_checkpoint_path=snapshot_dir / snapshot.raw_checkpoint_name,
        raw_checkpoint_sha256=snapshot.raw_checkpoint_sha256,
        companion_path=snapshot_dir / "train2_runtime.pt",
        companion_sha256=snapshot.companion_sha256,
        summary=snapshot.rung_runtime_summary,
        trajectory=trajectory,
        config_payload=config_payload,
        allow_forward_override=authority.allow_forward_override,
    )
    if prediction.evaluated_model_state_digest != evaluated_digest:
        raise TrainingDataInputError(
            "Replay prediction evidence model-state digest differs from provider state."
        )
    if (
        prediction.device != provider.device
        or prediction.default_dtype != provider.default_dtype
        or prediction.execution_architecture != provider.runtime_architecture_digest
        or prediction.backend_policy != provider.backend_policy
        or prediction.batch_size != eval_data.evaluation_size
    ):
        raise TrainingDataInputError(
            "Replay prediction execution provenance differs from the authenticated provider."
        )
    view = eval_data.build_authenticated_evaluation_view(
        eval_root,
        definition=authority.aggregate.definition,
        canonical_frame_authority=authority.canonical_frame_authority,
        policy=authority.extxyz_policy,
        frame_catalog=authority.frame_catalog,
        frame_data_by_run=authority.frame_data_by_run,
        frame_array_index=authority.frame_array_index,
    )
    if record.eval2_metric_record_digest is None:
        metric = None
    else:
        metric = authority.resolver.load_typed_content_addressed(
            authority.resolver.eval2_metric_path(record.eval2_metric_record_digest),
            record.eval2_metric_record_digest,
            Eval2TargetMetricRecord.from_dict,
        )
        if (
            metric.target_role_digest != role.content_digest
            or metric.prediction_digest != prediction.prediction_payload_digest
        ):
            raise TrainingDataInputError(
                "Replay EVAL2 metric does not bind the exact role and prediction payload."
            )
    return snapshot, eval_data, role, prediction, view, metric


def _reconcile_target_size_screen_root_locked(
    root_path: Path,
    auth: TargetSizeRestartAuthority,
    window: TargetSizeScreenWindow,
) -> TargetSizeExecutionHead | None:
    active_resolver = auth.resolver
    definition = auth.aggregate.definition
    replayed_state = auth.aggregate.reducer_state
    current_path = root_path / CURRENT_HEAD_FILENAME
    current_head = (
        active_resolver.load_typed_logical(
            current_path, TargetSizeExecutionHead.from_dict
        )
        if current_path.is_file()
        else None
    )

    # 1. Whole-root scan: Validate all heads, check stems, detect loops and forks
    heads_dir = root_path / "heads"
    all_heads: list[TargetSizeExecutionHead] = []
    heads_by_digest: dict[str, TargetSizeExecutionHead] = {}
    if heads_dir.is_dir():
        for h_path in sorted(heads_dir.glob("*.json")):
            h_obj = active_resolver.load_typed_content_addressed(
                h_path,
                h_path.stem,
                TargetSizeExecutionHead.from_dict,
            )
            all_heads.append(h_obj)
            heads_by_digest[h_obj.content_digest] = h_obj

    # Check for forks (multiple heads claiming the same parent)
    parent_to_heads: dict[str | None, list[str]] = {}
    for h in all_heads:
        parent_to_heads.setdefault(h.parent_head_digest, []).append(
            h.content_digest
        )
    for p_digest, h_digests in parent_to_heads.items():
        if len(h_digests) > 1:
            raise TrainingDataInputError(
                f"Fork detected: multiple heads {h_digests} claim parent head {p_digest}."
            )

    from .candidate import (
        TargetSizeCandidateMaterialization,
        TargetSizeCandidateTrajectory,
        validate_target_size_candidate_trajectory,
        validate_target_size_materialization,
    )
    from .evaluation import (
        TargetSizeEval2Role,
        TargetSizePredictionEvidence,
        target_size_boundary_metric_from_eval2_record,
        translate_target_size_eval2_failure,
    )
    from .execution import (
        TargetSizeBoundarySnapshot,
        TargetSizeContinuationRequest,
        translate_target_size_train2_failure,
        validate_target_size_boundary_snapshot,
    )
    from .export import (
        TargetSizeEvaluationArtifact,
        validate_target_size_evaluation_artifact,
    )
    from ..eval2 import Eval2NumericalEvaluationError, Eval2TargetMetricRecord
    from ..train2_runtime import Train2NumericalFailureRecord, Train2RuntimePlan

    # 2. Check for content-addressed stems across artifact directories
    scan_configs = (
        ("batches", TargetSizeCompleteBoundaryBatch.from_dict, "Batch"),
        ("snapshots", TargetSizeBoundarySnapshot.from_dict, "Snapshot"),
        ("roles", TargetSizeEval2Role.from_dict, "Role"),
        ("evaluation_artifacts", TargetSizeEvaluationArtifact.from_dict, "Evaluation artifact"),
        ("predictions", TargetSizePredictionEvidence.from_dict, "Prediction evidence"),
        ("metrics", Eval2TargetMetricRecord.from_dict, "Metric record"),
        ("trajectories", TargetSizeCandidateTrajectory.from_dict, "Trajectory"),
        ("materializations", TargetSizeCandidateMaterialization.from_dict, "Materialization"),
        ("continuations", TargetSizeContinuationRequest.from_dict, "Continuation"),
        ("planned_rungs", Train2RuntimePlan.from_dict, "Planned rung"),
    )
    scanned_batches: list[TargetSizeCompleteBoundaryBatch] = []
    for subdir, deserializer, name in scan_configs:
        d_dir = root_path / subdir
        if d_dir.is_dir():
            for obj_file in sorted(d_dir.glob("*.json")):
                loaded = active_resolver.load_typed_content_addressed(
                    obj_file, obj_file.stem, deserializer
                )
                if subdir == "batches":
                    scanned_batches.append(loaded)

    # Evaluation records have one typed owner path.  A retired ``evaluations``
    # directory is evidence of a split persistence topology, even if empty.
    retired_evaluations = root_path / "evaluations"
    if retired_evaluations.exists():
        raise TrainingDataInputError(
            "Retired evaluations/ directory is not an accepted evaluation artifact root."
        )

    # Failure records are deliberately discriminated at load time: a raw
    # TRAIN2 or raw EVAL2 object is accepted, while a serialized P2 failure is
    # never treated as raw evidence.
    failures_dir = root_path / "failures"
    if failures_dir.is_dir():
        for failure_path in sorted(failures_dir.glob("*.json")):
            active_resolver.load_raw_failure(failure_path.stem)

    # Validate completions
    completions_dir = root_path / "completions"
    scanned_completion_digests: set[str] = set()
    if completions_dir.is_dir():
        cells_seen: dict[tuple[int, int, int], str] = {}
        for epoch_dir in sorted(completions_dir.iterdir()):
            if epoch_dir.is_dir():
                for comp_file in sorted(epoch_dir.glob("*.json")):
                    c_rec = active_resolver.load_typed_content_addressed(
                        comp_file,
                        comp_file.stem,
                        TargetSizeCellCompletionRecord.from_dict,
                    )
                    if str(c_rec.boundary_epoch) != epoch_dir.name:
                        raise TrainingDataInputError(
                            f"Completion boundary {c_rec.boundary_epoch} does not match directory {epoch_dir.name}."
                        )
                    cell_key = (
                        c_rec.boundary_epoch,
                        c_rec.target_size,
                        c_rec.optimizer_seed,
                    )
                    if (
                        cell_key in cells_seen
                        and cells_seen[cell_key] != c_rec.content_digest
                    ):
                        raise TrainingDataInputError(
                            f"Conflicting completion records found for cell {cell_key}."
                        )
                    cells_seen[cell_key] = c_rec.content_digest
                    scanned_completion_digests.add(c_rec.content_digest)

    # Validate progress pointers
    progress_dir = root_path / "progress"
    progress_completion_digests: set[str] = set()
    if progress_dir.is_dir():
        for epoch_dir in sorted(progress_dir.iterdir()):
            if epoch_dir.is_dir():
                for prog_file in sorted(epoch_dir.glob("*.json")):
                    prog_obj = active_resolver.load_progress(prog_file)
                    if prog_obj.window_digest != window.content_digest:
                        raise TrainingDataInputError(
                            "Progress record belongs to a different screen window."
                        )
                    if str(prog_obj.boundary_epoch) != epoch_dir.name:
                        raise TrainingDataInputError(
                            f"Progress record epoch {prog_obj.boundary_epoch} does not match directory {epoch_dir.name}."
                        )
                    completion_path = active_resolver.completion_path(
                        prog_obj.boundary_epoch,
                        prog_obj.completion_record_digest,
                    )
                    completion = active_resolver.load_typed_content_addressed(
                        completion_path,
                        prog_obj.completion_record_digest,
                        TargetSizeCellCompletionRecord.from_dict,
                    )
                    if (
                        completion.window_digest != window.content_digest
                        or completion.boundary_epoch != prog_obj.boundary_epoch
                        or completion.target_size != prog_obj.outcome.target_size
                        or completion.optimizer_seed != prog_obj.outcome.optimizer_seed
                        or completion.trajectory_digest != prog_obj.trajectory_digest
                        or completion.outcome_digest != prog_obj.outcome.content_digest
                    ):
                        raise TrainingDataInputError(
                            "Progress pointer does not describe the referenced exact completion cell."
                        )
                    progress_completion_digests.add(prog_obj.completion_record_digest)

    referenced_completion_digests = progress_completion_digests.union(
        digest
        for batch in scanned_batches
        for digest in batch.completion_record_digests
    )
    orphan_completion_digests = scanned_completion_digests.difference(
        referenced_completion_digests
    )
    if orphan_completion_digests:
        raise TrainingDataInputError(
            "Orphan completion record exists without a progress pointer or complete boundary batch: "
            + ", ".join(sorted(orphan_completion_digests))
        )

    # 3. Determine the head chain (ancestry and unique linear successor chain)
    chain: list[TargetSizeExecutionHead] = []
    if current_head is not None:
        immutable_head_path = _head_path(root_path, current_head.content_digest)
        if not immutable_head_path.is_file():
            raise TrainingDataInputError(
                "Current execution head is missing its immutable head file in heads/."
            )
        immutable_head = active_resolver.load_typed_content_addressed(
            immutable_head_path,
            current_head.content_digest,
            TargetSizeExecutionHead.from_dict,
        )
        if immutable_head.content_digest != current_head.content_digest:
            raise TrainingDataInputError(
                "Current head copy differs from immutable head."
            )

        # 1. Backwards walk from current_head to root
        curr = current_head
        visited = {curr.content_digest}
        ancestor_chain: list[TargetSizeExecutionHead] = [curr]
        while curr.parent_head_digest is not None:
            parent_file = _head_path(root_path, curr.parent_head_digest)
            if not parent_file.is_file():
                raise TrainingDataInputError(
                    "Execution head is missing its parent head ancestry."
                )
            parent = active_resolver.load_typed_content_addressed(
                parent_file,
                curr.parent_head_digest,
                TargetSizeExecutionHead.from_dict,
            )
            if parent.content_digest != curr.parent_head_digest:
                raise TrainingDataInputError(
                    "Parent head content digest does not match referenced digest."
                )
            if parent.content_digest in visited:
                raise TrainingDataInputError(
                    "Ancestry loop detected in execution heads."
                )
            visited.add(parent.content_digest)
            ancestor_chain.append(parent)
            curr = parent
        ancestor_chain.reverse()

        # 2. Forwards walk from current_head to unique linear tip
        curr = current_head
        successor_chain: list[TargetSizeExecutionHead] = []
        while True:
            children = parent_to_heads.get(curr.content_digest, [])
            if len(children) > 1:
                raise TrainingDataInputError(
                    f"Fork detected: multiple children {children} claim parent head {curr.content_digest}."
                )
            if not children:
                break
            child_digest = children[0]
            child_head_path = _head_path(root_path, child_digest)
            if not child_head_path.is_file():
                raise TrainingDataInputError(
                    f"Child execution head {child_digest} is missing its immutable head file in heads/."
                )
            child_head = active_resolver.load_typed_content_addressed(
                child_head_path,
                child_digest,
                TargetSizeExecutionHead.from_dict,
            )
            if child_head.parent_head_digest != curr.content_digest:
                raise TrainingDataInputError(
                    "Child head parent digest does not match current head."
                )
            if child_head.content_digest in visited:
                raise TrainingDataInputError(
                    "Ancestry loop detected in execution heads."
                )
            visited.add(child_head.content_digest)
            successor_chain.append(child_head)
            curr = child_head

        chain = ancestor_chain + successor_chain

        chain_digests = {h.content_digest for h in chain}
        for h in all_heads:
            if h.content_digest not in chain_digests:
                raise TrainingDataInputError(
                    f"Orphan head detected: {h.content_digest} is not in current head ancestry/successor chain."
                )
    elif all_heads:
        # Missing current head pointer repair: find the tip head
        child_parents = {
            h.parent_head_digest for h in all_heads if h.parent_head_digest is not None
        }
        tips = [h for h in all_heads if h.content_digest not in child_parents]
        if len(tips) != 1:
            raise TrainingDataInputError(
                f"Cannot resolve head ancestry: found {len(tips)} candidate tips."
            )
        curr = tips[0]
        visited = {curr.content_digest}
        chain = [curr]
        while curr.parent_head_digest is not None:
            parent_file = _head_path(root_path, curr.parent_head_digest)
            if not parent_file.is_file():
                raise TrainingDataInputError(
                    "Execution head is missing its parent head ancestry."
                )
            parent = active_resolver.load_typed_content_addressed(
                parent_file,
                curr.parent_head_digest,
                TargetSizeExecutionHead.from_dict,
            )
            if parent.content_digest != curr.parent_head_digest:
                raise TrainingDataInputError(
                    "Parent head content digest does not match referenced digest."
                )
            if parent.content_digest in visited:
                raise TrainingDataInputError(
                    "Ancestry loop detected in execution heads."
                )
            visited.add(parent.content_digest)
            chain.append(parent)
            curr = parent
        chain.reverse()

        chain_digests = {h.content_digest for h in chain}
        for h in all_heads:
            if h.content_digest not in chain_digests:
                raise TrainingDataInputError(
                    f"Orphan head detected: {h.content_digest} is not in head ancestry chain."
                )

    # 4. Deterministic scientific replay of every committed or candidate batch.
    # The replay function is shared by the current head chain and by a batch
    # left durable after a crash, so an uncommitted batch cannot bypass the
    # exact parent/provenance checks merely because it has no head yet.
    from .evaluation import run_target_size_eval2_reduction
    import hashlib

    def _replay_batch(
        batch: TargetSizeCompleteBoundaryBatch,
        state: TargetSizeReducerState,
    ) -> TargetSizeReducerState:
        requirements = derive_active_boundary_requirements(definition, state)
        if requirements is None:
            raise TrainingDataInputError(
                "A complete boundary batch exists after the reducer became terminal."
            )
        expected_boundary, expected_eval_size, expected_keys = requirements
        expected_membership = definition.evaluation_order.membership_digest(
            expected_eval_size
        )
        if (
            batch.pre_state_digest != state.content_digest
            or batch.experiment_definition_digest != definition.content_digest
            or batch.execution_context_digest != auth.context.content_digest
            or batch.boundary_epoch != expected_boundary
            or batch.evaluation_membership_digest != expected_membership
            or tuple(batch.active_candidate_sizes) != tuple(state.active_candidate_sizes)
            or tuple(batch.optimizer_seeds) != tuple(definition.policy.optimizer_seeds)
            or len(batch.completion_record_digests) != len(expected_keys)
        ):
            raise TrainingDataInputError(
                "Complete boundary batch does not bind the exact active P2 matrix."
            )

        recomputed_outcomes: list[BoundaryOutcome] = []
        observed_keys: list[tuple[int, int]] = []
        for comp_digest in batch.completion_record_digests:
            comp_file = active_resolver.completion_path(batch.boundary_epoch, comp_digest)
            record = active_resolver.load_typed_content_addressed(
                comp_file, comp_digest, TargetSizeCellCompletionRecord.from_dict
            )
            observed_key = (record.target_size, record.optimizer_seed)
            observed_keys.append(observed_key)
            if (
                record.window_digest != window.content_digest
                or record.experiment_definition_digest != definition.content_digest
                or record.execution_context_digest != auth.context.content_digest
                or record.common_preparation_digest != auth.common.content_digest
                or record.boundary_epoch != expected_boundary
                or record.outcome.boundary_epoch != expected_boundary
                or record.outcome.evaluation_membership_digest != expected_membership
            ):
                raise TrainingDataInputError(
                    "Completion record carries foreign screen, P1/P2, or boundary identity."
                )

            trajectory, optimizer_policy, _projection, materialization = (
                _validate_replayed_candidate_lineage(auth, record)
            )
            if (
                trajectory.target_size != record.target_size
                or trajectory.optimizer_seed != record.optimizer_seed
                or trajectory.content_digest != record.trajectory_digest
            ):
                raise TrainingDataInputError(
                    "Completion record cell key does not match its authenticated trajectory."
                )
            if materialization.content_digest != record.materialization_digest:
                raise TrainingDataInputError(
                    "Completion record materialization digest changed during replay."
                )
            planned_rung, _predecessor = _load_and_validate_replayed_rung_ancestry(
                auth, record, trajectory
            )

            if record.kind == "success":
                (
                    snapshot,
                    eval_data,
                    role,
                    prediction,
                    view,
                    metric,
                ) = _validate_replayed_eval2_parents(
                    auth, record, trajectory, optimizer_policy, materialization
                )
                if snapshot.rung_plan_digest != planned_rung.content_digest:
                    raise TrainingDataInputError(
                        "Replay snapshot does not bind the exact planned rung."
                    )
                if metric is None:
                    raise TrainingDataInputError(
                        "Success completion record has no authenticated EVAL2 metric parent."
                    )
                eval_root = _evaluation_bulk_root_for_artifact(auth, eval_data)
                recomputed_metric = run_target_size_eval2_reduction(
                    role,
                    eval_data,
                    prediction,
                    view=view,
                    root_directory=eval_root,
                )
                if recomputed_metric.content_digest != metric.content_digest:
                    raise TrainingDataInputError(
                        "Replayed EVAL2 metric differs from the persisted metric record."
                    )
                derived_outcome = target_size_boundary_metric_from_eval2_record(
                    role, metric
                )
                if record.failure_evidence_digest is not None:
                    raise TrainingDataInputError(
                        "Success completion record carries failure evidence."
                    )

            elif record.kind == "train2_failure":
                if record.failure_record_digest is None:
                    raise TrainingDataInputError(
                        "TRAIN2 failure completion record is missing its raw failure parent."
                    )
                raw_fail = active_resolver.load_raw_failure(
                    record.failure_record_digest
                )
                if not isinstance(raw_fail, Train2NumericalFailureRecord):
                    raise TrainingDataInputError(
                        "TRAIN2 failure completion references a non-TRAIN2 raw failure."
                    )
                failure_root = _path_within_declared_root(
                    active_resolver.failure_bulk_directory(raw_fail.content_digest),
                    auth.bulk_root("train2"),
                    name="TRAIN2 failure bulk directory",
                )
                raw_checkpoint = failure_root / raw_fail.raw_checkpoint_name
                if (
                    not raw_checkpoint.is_file()
                    or hashlib.sha256(raw_checkpoint.read_bytes()).hexdigest()
                    != raw_fail.raw_checkpoint_sha256
                ):
                    raise TrainingDataInputError(
                        "Authenticated TRAIN2 raw checkpoint bytes are missing or changed."
                    )
                derived_outcome = translate_target_size_train2_failure(
                    raw_fail,
                    trajectory=trajectory,
                    definition=definition,
                    schedule=auth.schedule,
                    scheduled_boundary_epoch=batch.boundary_epoch,
                )
                if (
                    record.failure_evidence_digest
                    != derived_outcome.classification_evidence_digest
                ):
                    raise TrainingDataInputError(
                        "TRAIN2 failure evidence digest differs from raw failure translation."
                    )

            elif record.kind == "eval2_failure":
                (
                    snapshot,
                    _eval_data,
                    role,
                    prediction,
                    _view,
                    metric,
                ) = _validate_replayed_eval2_parents(
                    auth, record, trajectory, optimizer_policy, materialization
                )
                if snapshot.rung_plan_digest != planned_rung.content_digest:
                    raise TrainingDataInputError(
                        "Replay snapshot does not bind the exact planned rung."
                    )
                if metric is not None:
                    raise TrainingDataInputError(
                        "EVAL2 failure completion record carries a successful metric parent."
                    )
                if record.failure_record_digest is None:
                    raise TrainingDataInputError(
                        "EVAL2 failure completion record is missing its raw failure parent."
                    )
                raw_error = active_resolver.load_raw_failure(
                    record.failure_record_digest
                )
                if not isinstance(raw_error, Eval2NumericalEvaluationError):
                    raise TrainingDataInputError(
                        "EVAL2 failure completion references a non-EVAL2 raw failure."
                    )
                if (
                    raw_error.target_role_digest != role.content_digest
                    or raw_error.prediction_digest != prediction.prediction_payload_digest
                ):
                    raise TrainingDataInputError(
                        "EVAL2 raw numerical error does not bind the replayed role/prediction."
                    )
                derived_outcome = translate_target_size_eval2_failure(
                    role, raw_error
                )
                if (
                    record.failure_evidence_digest
                    != derived_outcome.classification_evidence_digest
                ):
                    raise TrainingDataInputError(
                        "EVAL2 failure evidence digest differs from raw failure translation."
                    )
            else:  # pragma: no cover - TargetSizeCellCompletionRecord rejects this
                raise TrainingDataInputError(
                    f"Unknown cell completion kind {record.kind!r}."
                )

            if derived_outcome.content_digest != record.outcome_digest:
                raise TrainingDataInputError(
                    "Reconstructed scientific outcome does not match completion outcome digest."
                )
            recomputed_outcomes.append(derived_outcome)

        if tuple(observed_keys) != tuple(expected_keys):
            raise TrainingDataInputError(
                "Completion records do not follow the exact P2 size-major/seed-minor matrix."
            )
        rebuilt_batch = TargetSizeCompleteBoundaryBatch(
            pre_state_digest=batch.pre_state_digest,
            experiment_definition_digest=batch.experiment_definition_digest,
            execution_context_digest=batch.execution_context_digest,
            boundary_epoch=batch.boundary_epoch,
            evaluation_membership_digest=batch.evaluation_membership_digest,
            active_candidate_sizes=batch.active_candidate_sizes,
            optimizer_seeds=batch.optimizer_seeds,
            completion_record_digests=batch.completion_record_digests,
            outcomes=tuple(recomputed_outcomes),
        )
        if rebuilt_batch.content_digest != batch.content_digest:
            raise TrainingDataInputError(
                "Reconstructed scientific batch content digest does not match stored batch."
            )
        return apply_complete_boundary_batch(definition, state, rebuilt_batch)

    chain_batch_digests: set[str] = set()
    for index, head in enumerate(chain):
        if head.pre_state_digest != replayed_state.content_digest:
            raise TrainingDataInputError(
                "Execution head pre-state digest does not match replayed reducer state."
            )
        if head.pre_state.content_digest != replayed_state.content_digest:
            raise TrainingDataInputError(
                "Execution head pre-state does not match replayed reducer state."
            )
        batch = active_resolver.load_typed_content_addressed(
            active_resolver.batch_path(head.batch_digest),
            head.batch_digest,
            TargetSizeCompleteBoundaryBatch.from_dict,
        )
        chain_batch_digests.add(batch.content_digest)
        post_state = _replay_batch(batch, replayed_state)
        if post_state.content_digest != head.post_state_digest:
            raise TrainingDataInputError(
                "Replayed reducer post-state does not match committed execution head."
            )
        if head.post_state.content_digest != post_state.content_digest:
            raise TrainingDataInputError(
                "Execution head post-state does not match replayed reducer post-state."
            )
        if index + 1 < len(chain) and chain[index + 1].pre_state_digest != post_state.content_digest:
            raise TrainingDataInputError(
                "Execution head ancestry has a reducer-state discontinuity."
            )
        replayed_state = post_state

    if chain:
        tip_head = chain[-1]
        if replayed_state.content_digest != tip_head.post_state.content_digest:
            raise TrainingDataInputError(
                "Full replay diverged from tip execution head post-state."
            )
        if (
            current_head is None
            or current_head.content_digest != tip_head.content_digest
            or not current_path.is_file()
        ):
            _atomic_json_write(current_path, tip_head.to_dict())
            verified = TargetSizeExecutionHead.from_dict(
                json.loads(current_path.read_text(encoding="utf-8"))
            )
            if verified.content_digest != tip_head.content_digest:
                raise TrainingDataInputError(
                    "Current head pointer verification failed after reconciliation write."
                )
        head_result = tip_head
    else:
        head_result = None

    # A batch not referenced by the current head chain is either a crash-left
    # candidate for the exact current state or an orphan/fork.  Validate the
    # former by full scientific replay before committing it; reject the latter.
    unreferenced_batches = [
        batch
        for batch in scanned_batches
        if batch.content_digest not in chain_batch_digests
    ]
    while True:
        candidates = [
            batch
            for batch in unreferenced_batches
            if batch.pre_state_digest == replayed_state.content_digest
        ]
        if len(candidates) > 1:
            raise TrainingDataInputError(
                "Two uncommitted complete batches claim the same pre-state: conflicting scientific evidence."
            )
        if not candidates:
            break
        candidate = candidates[0]
        post_state = _replay_batch(candidate, replayed_state)
        head_result = _commit_target_size_boundary_batch_locked(
            root_path=root_path,
            current_path=current_path,
            definition=definition,
            state=replayed_state,
            batch=candidate,
        )
        if head_result.post_state_digest != post_state.content_digest:
            raise TrainingDataInputError(
                "Crash-repaired batch commit differs from its scientifically replayed post-state."
            )
        replayed_state = post_state
        chain_batch_digests.add(candidate.content_digest)
        unreferenced_batches.remove(candidate)

    if unreferenced_batches:
        raise TrainingDataInputError(
            "Orphan complete batch exists without a current-head ancestry or exact current-state parent."
        )

    return head_result


def reconcile_target_size_screen_root(
    root: str | Path,
    authority: TargetSizeRestartAuthority,
) -> TargetSizeExecutionHead | None:
    """Crash-safe restart reconciliation through pure deterministic replay from initial state."""

    if not isinstance(authority, TargetSizeRestartAuthority):
        raise TrainingDataInputError(
            "Screen reconciliation requires one complete TargetSizeRestartAuthority; "
            "legacy aggregate/context/common arguments are not accepted."
        )
    auth = authority

    root_path = Path(root)
    active_resolver = auth.resolver
    if active_resolver.root_directory.resolve() != root_path.resolve():
        raise TrainingDataInputError(
            "Restart resolver root does not match the requested screen root."
        )
    window_path = root_path / SCREEN_WINDOW_FILENAME
    if not window_path.is_file():
        return None
    window = TargetSizeScreenWindow.from_dict(
        json.loads(window_path.read_text(encoding="utf-8"))
    )
    if (
        window.aggregate_digest != auth.aggregate.content_digest
        or window.experiment_definition_digest
        != auth.aggregate.definition.content_digest
        or window.execution_context_digest != auth.context.content_digest
        or window.common_preparation_digest != auth.common.content_digest
        or window.initial_reducer_digest
        != auth.aggregate.reducer_state.content_digest
    ):
        raise TrainingDataInputError(
            "Screen window does not bind the current P1/P2 authority identity."
        )

    lock_path = root_path / ".screen_commit.lock"
    with open(lock_path, "w") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _reconcile_target_size_screen_root_locked(
                root_path=root_path,
                auth=auth,
                window=window,
            )
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


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
    "TargetSizeExecutionResolver",
    "TargetSizeResolvedCandidateExecution",
    "TargetSizeRestartAuthority",
    "TargetSizeScreenWindow",
    "apply_complete_boundary_batch",
    "build_complete_boundary_batch",
    "build_target_size_cell_completion_record",
    "build_target_size_eval2_failure_cell_completion_record",
    "build_target_size_success_cell_completion_record",
    "build_target_size_train2_failure_cell_completion_record",
    "collect_boundary_candidate_outcomes",
    "collect_boundary_cell_completion_records",
    "commit_target_size_boundary_batch",
    "derive_active_boundary_requirements",
    "initialize_target_size_screen",
    "load_current_execution_head",
    "load_target_size_boundary_batch",
    "persist_complete_boundary_batch",
    "prepare_target_size_evaluation_artifact",
    "reconcile_target_size_screen_root",
    "record_candidate_boundary_outcome",
    "resolve_target_size_candidate_for_resume",
]
