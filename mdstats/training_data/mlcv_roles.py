"""MLCV-ROLE1 statistical role authority and immutable lineage.

This module does not choose checkpoints or materialize new monitors.  It freezes
which DATA5/replay domains are allowed to participate in each machine-learning
operation so later MLCV gates cannot accidentally reuse an outer CV fold or the
locked test as checkpoint-selection evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .partition import OuterRole
from .replay import ReplayFileArtifact, ReplayLabelMode, ReplayPreparationPlan, ReplayMode

MLCV_ROLE_CATALOG_SCHEMA = "mdstats.mlcv-role-catalog.v1"
MLCV_FOLD_ROLE_RECORD_SCHEMA = "mdstats.mlcv-fold-role-record.v1"
MLCV_REPLAY_ROLE_LINEAGE_SCHEMA = "mdstats.mlcv-replay-role-lineage.v1"
MLCV_ROLE_AUTHORITY_VERSION = "mdstats.mlcv-role-authority.2026-08.v1"


class MlcvDataRole(str, Enum):
    """Statistical roles with selection authority that must never be conflated."""

    TARGET_GRADIENT_TRAINING = "target_gradient_training"
    TARGET_CHECKPOINT_SELECTION = "target_checkpoint_selection"
    TARGET_OUTER_CV_EVALUATION = "target_outer_cv_evaluation"
    TARGET_FINAL_VALIDATION = "target_final_validation"
    TARGET_LOCKED_TEST = "target_locked_test"
    REPLAY_GRADIENT_TRAINING = "replay_gradient_training"
    REPLAY_TRUE_VALIDATION = "replay_true_validation"


class MlcvEvidenceOperation(str, Enum):
    """Operations that can consume statistical evidence."""

    GRADIENT_UPDATE = "gradient_update"
    TRAINING_DIAGNOSTIC = "training_diagnostic"
    CHECKPOINT_STOP = "checkpoint_stop"
    CHECKPOINT_RANK = "checkpoint_rank"
    CHECKPOINT_TOPK_SELECTION = "checkpoint_topk_selection"
    OUTER_CV_EVALUATION = "outer_cv_evaluation"
    FINAL_SEED_SELECTION = "final_seed_selection"
    PHYSICAL_VERIFICATION_FALLBACK = "physical_verification_fallback"
    LOCKED_TEST_EVALUATION = "locked_test_evaluation"


_ALLOWED_OPERATIONS: dict[MlcvDataRole, frozenset[MlcvEvidenceOperation]] = {
    MlcvDataRole.TARGET_GRADIENT_TRAINING: frozenset(
        {MlcvEvidenceOperation.GRADIENT_UPDATE, MlcvEvidenceOperation.TRAINING_DIAGNOSTIC}
    ),
    MlcvDataRole.TARGET_CHECKPOINT_SELECTION: frozenset(
        {
            MlcvEvidenceOperation.CHECKPOINT_STOP,
            MlcvEvidenceOperation.CHECKPOINT_RANK,
            MlcvEvidenceOperation.CHECKPOINT_TOPK_SELECTION,
        }
    ),
    MlcvDataRole.TARGET_OUTER_CV_EVALUATION: frozenset(
        {MlcvEvidenceOperation.OUTER_CV_EVALUATION}
    ),
    MlcvDataRole.TARGET_FINAL_VALIDATION: frozenset(
        {
            MlcvEvidenceOperation.CHECKPOINT_STOP,
            MlcvEvidenceOperation.CHECKPOINT_RANK,
            MlcvEvidenceOperation.CHECKPOINT_TOPK_SELECTION,
            MlcvEvidenceOperation.FINAL_SEED_SELECTION,
        }
    ),
    MlcvDataRole.TARGET_LOCKED_TEST: frozenset(
        {MlcvEvidenceOperation.LOCKED_TEST_EVALUATION}
    ),
    MlcvDataRole.REPLAY_GRADIENT_TRAINING: frozenset(
        {MlcvEvidenceOperation.GRADIENT_UPDATE}
    ),
    MlcvDataRole.REPLAY_TRUE_VALIDATION: frozenset(
        {
            MlcvEvidenceOperation.CHECKPOINT_STOP,
            MlcvEvidenceOperation.CHECKPOINT_RANK,
            MlcvEvidenceOperation.CHECKPOINT_TOPK_SELECTION,
            MlcvEvidenceOperation.FINAL_SEED_SELECTION,
        }
    ),
}


def mlcv_role_allows(
    role: MlcvDataRole | str,
    operation: MlcvEvidenceOperation | str,
) -> bool:
    """Return whether *role* is authorized for *operation*."""

    resolved_role = MlcvDataRole(role)
    resolved_operation = MlcvEvidenceOperation(operation)
    return resolved_operation in _ALLOWED_OPERATIONS[resolved_role]


def require_mlcv_role(
    role: MlcvDataRole | str,
    operation: MlcvEvidenceOperation | str,
    *,
    context: str = "MLCV evidence",
) -> None:
    """Fail closed when a statistical role is used for an unauthorized operation."""

    resolved_role = MlcvDataRole(role)
    resolved_operation = MlcvEvidenceOperation(operation)
    if not mlcv_role_allows(resolved_role, resolved_operation):
        raise TrainingDataInputError(
            f"{context}: role {resolved_role.value!r} is not authorized for "
            f"operation {resolved_operation.value!r}."
        )


def require_mlcv_checkpoint_stopping_role(role: MlcvDataRole | str) -> None:
    require_mlcv_role(role, MlcvEvidenceOperation.CHECKPOINT_STOP, context="MLCV checkpoint stopping")


def require_mlcv_checkpoint_ranking_role(role: MlcvDataRole | str) -> None:
    require_mlcv_role(role, MlcvEvidenceOperation.CHECKPOINT_RANK, context="MLCV checkpoint ranking")


def require_mlcv_topk_selection_role(role: MlcvDataRole | str) -> None:
    require_mlcv_role(
        role,
        MlcvEvidenceOperation.CHECKPOINT_TOPK_SELECTION,
        context="MLCV top-K checkpoint selection",
    )


def require_mlcv_outer_cv_evaluation_role(role: MlcvDataRole | str) -> None:
    require_mlcv_role(
        role,
        MlcvEvidenceOperation.OUTER_CV_EVALUATION,
        context="MLCV outer CV evaluation",
    )


@dataclass(frozen=True, slots=True)
class MlcvFoldRoleRecord:
    """Run-local DATA5 role assignment for one cross-validation fold."""

    fold_index: int
    gradient_training_unit_ids: tuple[str, ...]
    checkpoint_selection_unit_ids: tuple[str, ...]
    outer_evaluation_unit_ids: tuple[str, ...]
    purged_unit_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if int(self.fold_index) < 0:
            raise TrainingDataInputError("MLCV fold index must be nonnegative.")
        groups: list[set[str]] = []
        for name in (
            "gradient_training_unit_ids",
            "checkpoint_selection_unit_ids",
            "outer_evaluation_unit_ids",
            "purged_unit_ids",
        ):
            values = tuple(validate_digest(str(v), name="unit_id") for v in getattr(self, name))
            if len(set(values)) != len(values):
                raise TrainingDataInputError(f"MLCV {name} contains duplicate units.")
            object.__setattr__(self, name, values)
            groups.append(set(values))
        if not self.gradient_training_unit_ids:
            raise TrainingDataInputError("MLCV fold requires gradient-training units.")
        if not self.checkpoint_selection_unit_ids:
            raise TrainingDataInputError("MLCV fold requires nested checkpoint-selection units.")
        if not self.outer_evaluation_unit_ids:
            raise TrainingDataInputError("MLCV fold requires outer CV evaluation units.")
        if any(groups[i] & groups[j] for i in range(len(groups)) for j in range(i + 1, len(groups))):
            raise TrainingDataInputError("MLCV fold statistical roles must be disjoint.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_FOLD_ROLE_RECORD_SCHEMA,
            "fold_index": int(self.fold_index),
            "gradient_training_unit_ids": list(self.gradient_training_unit_ids),
            "checkpoint_selection_unit_ids": list(self.checkpoint_selection_unit_ids),
            "outer_evaluation_unit_ids": list(self.outer_evaluation_unit_ids),
            "purged_unit_ids": list(self.purged_unit_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFoldRoleRecord":
        if payload.get("schema") != MLCV_FOLD_ROLE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV fold-role schema.")
        result = cls(
            fold_index=int(payload["fold_index"]),
            gradient_training_unit_ids=tuple(str(v) for v in payload["gradient_training_unit_ids"]),
            checkpoint_selection_unit_ids=tuple(str(v) for v in payload["checkpoint_selection_unit_ids"]),
            outer_evaluation_unit_ids=tuple(str(v) for v in payload["outer_evaluation_unit_ids"]),
            purged_unit_ids=tuple(str(v) for v in payload.get("purged_unit_ids", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV fold-role digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvReplayRoleLineage:
    """Typed separation of replay gradient labels and authoritative TRUE_DFT validation."""

    replay_mode: ReplayMode
    training_artifact_digest: str | None
    training_label_mode: ReplayLabelMode | None
    validation_artifact_digest: str | None
    validation_label_mode: ReplayLabelMode | None
    training_validation_geometry_overlap_count: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "replay_mode", ReplayMode(self.replay_mode))
        for name in ("training_artifact_digest", "validation_artifact_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.training_label_mode is not None:
            object.__setattr__(self, "training_label_mode", ReplayLabelMode(self.training_label_mode))
        if self.validation_label_mode is not None:
            object.__setattr__(self, "validation_label_mode", ReplayLabelMode(self.validation_label_mode))
        overlap = int(self.training_validation_geometry_overlap_count)
        if overlap < 0:
            raise TrainingDataInputError("Replay training/validation overlap count must be nonnegative.")
        object.__setattr__(self, "training_validation_geometry_overlap_count", overlap)

        if self.replay_mode is ReplayMode.NONE:
            if self.training_artifact_digest is not None or self.training_label_mode is not None:
                raise TrainingDataInputError("Replay NONE cannot carry gradient-training replay lineage.")
            if self.validation_artifact_digest is None:
                if self.validation_label_mode is not None:
                    raise TrainingDataInputError("Replay NONE validation label mode requires an artifact.")
            else:
                if self.validation_label_mode is not ReplayLabelMode.TRUE_DFT:
                    raise TrainingDataInputError("Any MLCV replay validation evidence must carry TRUE_DFT labels.")
            if overlap:
                raise TrainingDataInputError("Replay NONE cannot carry training/validation geometry overlap.")
            return

        if self.training_artifact_digest is None or self.training_label_mode is None:
            raise TrainingDataInputError("MLCV replay training requires explicit artifact and label lineage.")
        if self.validation_artifact_digest is None:
            if self.validation_label_mode is not None:
                raise TrainingDataInputError("MLCV replay validation label mode requires an artifact.")
            if overlap:
                raise TrainingDataInputError("Replay overlap cannot exist without validation evidence.")
        else:
            if self.validation_label_mode is not ReplayLabelMode.TRUE_DFT:
                raise TrainingDataInputError("MLCV replay validation must carry independent TRUE_DFT labels.")
            if overlap:
                raise TrainingDataInputError(
                    "MLCV replay gradient-training and TRUE_DFT validation geometries must be disjoint."
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_REPLAY_ROLE_LINEAGE_SCHEMA,
            "replay_mode": self.replay_mode.value,
            "training_artifact_digest": self.training_artifact_digest,
            "training_label_mode": None if self.training_label_mode is None else self.training_label_mode.value,
            "validation_artifact_digest": self.validation_artifact_digest,
            "validation_label_mode": None if self.validation_label_mode is None else self.validation_label_mode.value,
            "training_validation_geometry_overlap_count": self.training_validation_geometry_overlap_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvReplayRoleLineage":
        if payload.get("schema") != MLCV_REPLAY_ROLE_LINEAGE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV replay-role lineage schema.")
        result = cls(
            replay_mode=ReplayMode(payload["replay_mode"]),
            training_artifact_digest=(
                None if payload.get("training_artifact_digest") is None else str(payload["training_artifact_digest"])
            ),
            training_label_mode=(
                None if payload.get("training_label_mode") is None else ReplayLabelMode(payload["training_label_mode"])
            ),
            validation_artifact_digest=(
                None if payload.get("validation_artifact_digest") is None else str(payload["validation_artifact_digest"])
            ),
            validation_label_mode=(
                None if payload.get("validation_label_mode") is None else ReplayLabelMode(payload["validation_label_mode"])
            ),
            training_validation_geometry_overlap_count=int(
                payload.get("training_validation_geometry_overlap_count", 0)
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV replay-role lineage digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvRoleCatalog:
    """Immutable MLCV-ROLE1 authority derived from DATA5 and replay lineage."""

    label_domain_id: str
    data5_bundle_digest: str
    partition_policy_digest: str
    partition_unit_catalog_digest: str
    outer_partition_digest: str
    cross_validation_plan_digest: str
    final_gradient_training_unit_ids: tuple[str, ...]
    final_validation_unit_ids: tuple[str, ...]
    locked_test_unit_ids: tuple[str, ...]
    folds: tuple[MlcvFoldRoleRecord, ...]
    replay: MlcvReplayRoleLineage
    split_authority: str = "data5_correlation_aware_partition_units"
    authority_version: str = MLCV_ROLE_AUTHORITY_VERSION

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("MLCV label_domain_id must be non-empty.")
        for name in (
            "data5_bundle_digest",
            "partition_policy_digest",
            "partition_unit_catalog_digest",
            "outer_partition_digest",
            "cross_validation_plan_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "final_gradient_training_unit_ids",
            "final_validation_unit_ids",
            "locked_test_unit_ids",
        ):
            values = tuple(validate_digest(str(v), name="unit_id") for v in getattr(self, name))
            if len(set(values)) != len(values):
                raise TrainingDataInputError(f"MLCV {name} contains duplicate units.")
            object.__setattr__(self, name, values)
        if not self.final_gradient_training_unit_ids:
            raise TrainingDataInputError("MLCV final training domain cannot be empty.")
        if not self.final_validation_unit_ids:
            raise TrainingDataInputError("MLCV final validation D cannot be empty.")
        if not self.locked_test_unit_ids:
            raise TrainingDataInputError("MLCV locked test E cannot be empty.")
        outer_sets = (
            set(self.final_gradient_training_unit_ids),
            set(self.final_validation_unit_ids),
            set(self.locked_test_unit_ids),
        )
        if any(outer_sets[i] & outer_sets[j] for i in range(3) for j in range(i + 1, 3)):
            raise TrainingDataInputError("MLCV development, final validation D, and locked test E must be disjoint.")

        folds = tuple(sorted(self.folds, key=lambda item: item.fold_index))
        if not folds or tuple(item.fold_index for item in folds) != tuple(range(len(folds))):
            raise TrainingDataInputError("MLCV fold-role indices must be contiguous from zero.")
        development = set(self.final_gradient_training_unit_ids)
        held_out: list[str] = []
        for fold in folds:
            classified = (
                set(fold.gradient_training_unit_ids)
                | set(fold.checkpoint_selection_unit_ids)
                | set(fold.outer_evaluation_unit_ids)
                | set(fold.purged_unit_ids)
            )
            if classified != development:
                raise TrainingDataInputError(
                    "MLCV fold roles must classify the complete DATA5 development domain."
                )
            held_out.extend(fold.outer_evaluation_unit_ids)
        if len(held_out) != len(set(held_out)) or set(held_out) != development:
            raise TrainingDataInputError(
                "MLCV outer CV folds must hold out every development unit exactly once."
            )
        object.__setattr__(self, "folds", folds)
        if self.split_authority != "data5_correlation_aware_partition_units":
            raise TrainingDataInputError("MLCV production splitting must remain under DATA5 partition-unit authority.")
        if self.authority_version != MLCV_ROLE_AUTHORITY_VERSION:
            raise TrainingDataInputError("Unsupported MLCV role-authority version.")

    def fold(self, fold_index: int) -> MlcvFoldRoleRecord:
        try:
            return self.folds[int(fold_index)]
        except (IndexError, ValueError):
            raise KeyError(fold_index) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_ROLE_CATALOG_SCHEMA,
            "authority_version": self.authority_version,
            "label_domain_id": self.label_domain_id,
            "data5_bundle_digest": self.data5_bundle_digest,
            "partition_policy_digest": self.partition_policy_digest,
            "partition_unit_catalog_digest": self.partition_unit_catalog_digest,
            "outer_partition_digest": self.outer_partition_digest,
            "cross_validation_plan_digest": self.cross_validation_plan_digest,
            "final_gradient_training_unit_ids": list(self.final_gradient_training_unit_ids),
            "final_validation_unit_ids": list(self.final_validation_unit_ids),
            "locked_test_unit_ids": list(self.locked_test_unit_ids),
            "folds": [item.to_dict() for item in self.folds],
            "replay": self.replay.to_dict(),
            "split_authority": self.split_authority,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvRoleCatalog":
        if payload.get("schema") != MLCV_ROLE_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV role-catalog schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            partition_policy_digest=str(payload["partition_policy_digest"]),
            partition_unit_catalog_digest=str(payload["partition_unit_catalog_digest"]),
            outer_partition_digest=str(payload["outer_partition_digest"]),
            cross_validation_plan_digest=str(payload["cross_validation_plan_digest"]),
            final_gradient_training_unit_ids=tuple(str(v) for v in payload["final_gradient_training_unit_ids"]),
            final_validation_unit_ids=tuple(str(v) for v in payload["final_validation_unit_ids"]),
            locked_test_unit_ids=tuple(str(v) for v in payload["locked_test_unit_ids"]),
            folds=tuple(MlcvFoldRoleRecord.from_dict(item) for item in payload["folds"]),
            replay=MlcvReplayRoleLineage.from_dict(payload["replay"]),
            split_authority=str(payload.get("split_authority", "")),
            authority_version=str(payload.get("authority_version", "")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV role-catalog digest mismatch.")
        return result


def build_mlcv_replay_role_lineage(
    replay_plan: ReplayPreparationPlan,
    true_replay_validation_artifact: ReplayFileArtifact | None,
) -> MlcvReplayRoleLineage:
    """Build the replay side of ROLE1 with explicit TRUE_DFT authority."""

    if replay_plan.mode is ReplayMode.NONE:
        return MlcvReplayRoleLineage(
            replay_mode=ReplayMode.NONE,
            training_artifact_digest=None,
            training_label_mode=None,
            validation_artifact_digest=(
                None if true_replay_validation_artifact is None else true_replay_validation_artifact.content_digest
            ),
            validation_label_mode=(
                None if true_replay_validation_artifact is None else true_replay_validation_artifact.label_mode
            ),
        )
    if replay_plan.train_artifact is None:
        raise TrainingDataInputError("MLCV-ROLE1 requires a materialized replay training artifact.")
    overlap = 0
    if true_replay_validation_artifact is not None:
        overlap = len(
            set(replay_plan.train_artifact.geometry_identities)
            & set(true_replay_validation_artifact.geometry_identities)
        )
    return MlcvReplayRoleLineage(
        replay_mode=replay_plan.mode,
        training_artifact_digest=replay_plan.train_artifact.content_digest,
        training_label_mode=replay_plan.train_artifact.label_mode,
        validation_artifact_digest=(
            None if true_replay_validation_artifact is None else true_replay_validation_artifact.content_digest
        ),
        validation_label_mode=(
            None if true_replay_validation_artifact is None else true_replay_validation_artifact.label_mode
        ),
        training_validation_geometry_overlap_count=overlap,
    )


def build_mlcv_role_catalog(
    data5_bundle: Any,
    label_domain_id: str,
    *,
    replay_plan: ReplayPreparationPlan,
    true_replay_validation_artifact: ReplayFileArtifact | None,
    cross_validation_plan: Any | None = None,
) -> MlcvRoleCatalog:
    """Freeze conventional-CV role authority without changing monitor materialization."""

    outer = data5_bundle.outer_partition_for_domain(label_domain_id)
    cv = (
        data5_bundle.cross_validation_for_domain(label_domain_id)
        if cross_validation_plan is None
        else cross_validation_plan
    )
    if cv.label_domain_id != label_domain_id:
        raise TrainingDataInputError("MLCV CV plan belongs to a different label domain.")
    development = tuple(outer.units_for(OuterRole.DEVELOPMENT))
    final_validation = tuple(outer.units_for(OuterRole.OUTER_MONITOR))
    locked_test = tuple(outer.units_for(OuterRole.LOCKED_INTERPOLATION_TEST))
    if not data5_bundle.leakage_audit.passed:
        raise TrainingDataInputError("MLCV role authority requires a passing DATA5 leakage audit.")
    if cv.outer_partition_digest != outer.content_digest:
        raise TrainingDataInputError("MLCV CV/outer-partition lineage mismatch.")
    if cv.policy_digest != data5_bundle.partition_policy.policy_digest:
        raise TrainingDataInputError("MLCV CV/partition-policy lineage mismatch.")
    folds = tuple(
        MlcvFoldRoleRecord(
            fold_index=fold.fold_index,
            gradient_training_unit_ids=fold.training_unit_ids,
            checkpoint_selection_unit_ids=fold.checkpoint_monitor_unit_ids,
            outer_evaluation_unit_ids=fold.evaluation_unit_ids,
            purged_unit_ids=fold.purged_unit_ids,
        )
        for fold in cv.folds
    )
    replay = build_mlcv_replay_role_lineage(replay_plan, true_replay_validation_artifact)
    return MlcvRoleCatalog(
        label_domain_id=label_domain_id,
        data5_bundle_digest=data5_bundle.content_digest,
        partition_policy_digest=data5_bundle.partition_policy.policy_digest,
        partition_unit_catalog_digest=data5_bundle.unit_catalog.content_digest,
        outer_partition_digest=outer.content_digest,
        cross_validation_plan_digest=cv.content_digest,
        final_gradient_training_unit_ids=tuple(development),
        final_validation_unit_ids=tuple(final_validation),
        locked_test_unit_ids=tuple(locked_test),
        folds=folds,
        replay=replay,
    )
