"""Collision-proof execution identity for the three training roles.

Target-size screening, a cross-validation fold, and a final-production job can
legitimately share the same selected size and even the same numeric optimizer
seed.  They are still different experiments, and they must never be able to
resume, overwrite, or be mistaken for one another.

Role therefore belongs to *execution* identity - the run digest, the checkpoint
root, the restart owner, the runtime summary, the export identity - and only
there.  It deliberately does not enter selected target membership or the
reusable scientific preparation identity, which stay role-neutral so identical
data preparation can still be shared.
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

#: The superseded full-plan-derived run identity.  It still names historical
#: run roots, so the one-time recovery derivation can recompute it from an
#: authenticated historical plan; it is never a current root identity.
POST_SELECTION_RUN_IDENTITY_SCHEMA = "mdstats.post-selection-run-identity.v1"
TRAINING_TRAJECTORY_IDENTITY_SCHEMA = "mdstats.post-selection-training-trajectory.v1"


class PostSelectionRunRole(str, Enum):
    """The execution roles whose namespaces must never collide."""

    TARGET_SIZE_SCREEN = "target_size_screen"
    POST_SELECTION_CV = "post_selection_cv"
    FINAL_PRODUCTION = "final_production"


@dataclass(frozen=True, slots=True)
class TrainingTrajectoryIdentity:
    """The one pre-fit training position of a P5 run: its root and restart owner.

    Every field is an already-available input capable of changing exact
    TRAIN2/materialization/restart behavior.  The training-only method digest
    carries the objective/exposure/optimizer/LR/precision/backend/architecture/
    cadence/preparation-policy/foundation coordinates; the remaining fields are
    the role position: exact gradient membership, seed and horizon, replay
    training lineage, the common target monitor the trainer validates on, and
    the label-blind composition identity of the governed transfer consumers.

    Deliberately absent: every descendant product (fitted preparation, E0
    result, composition-transfer result, materialization, runtime, checkpoint)
    and every assessment coordinate (hard/warning thresholds, role target
    ceilings, CV outer acceptance, representative ordering, publication).  A
    policy-only edit therefore reproduces this identity; a realized-state
    mismatch under it is detected separately by continuation authentication.
    """

    run_role: str
    selected_binding_digest: str
    method_identity_digest: str
    training_membership_digest: str
    optimizer_seed: int
    planned_epochs: int
    replay_lineage_digest: str | None
    common_monitor_record_digest: str
    transfer_consumer_composition_digest: str | None

    def __post_init__(self) -> None:
        role = PostSelectionRunRole(self.run_role)
        if role is PostSelectionRunRole.TARGET_SIZE_SCREEN:
            raise TrainingDataInputError(
                "Target-size screening does not own a P5 training trajectory."
            )
        object.__setattr__(self, "run_role", role.value)
        for name in (
            "selected_binding_digest",
            "method_identity_digest",
            "training_membership_digest",
            "common_monitor_record_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in ("replay_lineage_digest", "transfer_consumer_composition_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        for name in ("optimizer_seed", "planned_epochs"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise TrainingDataInputError(f"{name} must be an integer.")
        if self.optimizer_seed < 0 or self.planned_epochs <= 0:
            raise TrainingDataInputError(
                "A training trajectory needs a nonnegative seed and a positive horizon."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_TRAJECTORY_IDENTITY_SCHEMA,
            "run_role": self.run_role,
            "selected_binding_digest": self.selected_binding_digest,
            "method_identity_digest": self.method_identity_digest,
            "training_membership_digest": self.training_membership_digest,
            "optimizer_seed": self.optimizer_seed,
            "planned_epochs": self.planned_epochs,
            "replay_lineage_digest": self.replay_lineage_digest,
            "common_monitor_record_digest": self.common_monitor_record_digest,
            "transfer_consumer_composition_digest": (
                self.transfer_consumer_composition_digest
            ),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingTrajectoryIdentity":
        if payload.get("schema") != TRAINING_TRAJECTORY_IDENTITY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection training-trajectory schema."
            )
        result = cls(
            run_role=str(payload["run_role"]),
            selected_binding_digest=str(payload["selected_binding_digest"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            training_membership_digest=str(payload["training_membership_digest"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            planned_epochs=int(payload["planned_epochs"]),
            replay_lineage_digest=(
                None
                if payload.get("replay_lineage_digest") is None
                else str(payload["replay_lineage_digest"])
            ),
            common_monitor_record_digest=str(payload["common_monitor_record_digest"]),
            transfer_consumer_composition_digest=(
                None
                if payload.get("transfer_consumer_composition_digest") is None
                else str(payload["transfer_consumer_composition_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection training-trajectory digest mismatch."
            )
        return result


def post_selection_run_identity(
    *,
    role: PostSelectionRunRole | str,
    plan_digest: str,
    optimizer_seed: int,
    fold_index: int | None = None,
) -> str:
    """Return the *historical* full-plan-derived run identity of one position.

    Current P5 roots are keyed by :class:`TrainingTrajectoryIdentity`.  This
    derivation survives only so the one-time recovery owner can locate a legacy
    root from an authenticated historical plan without scanning ``runs/``.
    """

    resolved = PostSelectionRunRole(role)
    if isinstance(optimizer_seed, bool) or not isinstance(optimizer_seed, int):
        raise TrainingDataInputError("optimizer_seed must be an integer.")
    if fold_index is not None:
        if isinstance(fold_index, bool) or not isinstance(fold_index, int):
            raise TrainingDataInputError("fold_index must be an integer.")
        if fold_index < 0:
            raise TrainingDataInputError("fold_index must be nonnegative.")
    if resolved is PostSelectionRunRole.POST_SELECTION_CV and fold_index is None:
        raise TrainingDataInputError(
            "A cross-validation run identity requires its fold index."
        )
    if resolved is PostSelectionRunRole.FINAL_PRODUCTION and fold_index is not None:
        raise TrainingDataInputError(
            "A final-production run identity has no fold index; final production is "
            "not a fold."
        )
    return digest(
        {
            "schema": POST_SELECTION_RUN_IDENTITY_SCHEMA,
            "run_role": resolved.value,
            "plan_digest": validate_digest(str(plan_digest), name="plan_digest"),
            "optimizer_seed": int(optimizer_seed),
            "fold_index": fold_index,
        }
    )


def reject_foreign_run_continuation(
    *, role: PostSelectionRunRole | str, offered_run_identity: str, run_identity: str
) -> None:
    """Fail closed when a run is offered another run's state to continue.

    Freshness is not a property that can be asserted after the fact, so the only
    admissible parent for a post-selection run's optimizer/RNG/checkpoint state
    is that exact run's own prior attempt.
    """

    if str(offered_run_identity) != str(run_identity):
        raise TrainingDataInputError(
            f"A {PostSelectionRunRole(role).value} run may only continue its own "
            f"execution state. Offered run {str(offered_run_identity)[:12]}... is not "
            f"run {str(run_identity)[:12]}...; screening and cross-validation "
            "trajectories are never admissible parents of another run."
        )


__all__ = [
    "POST_SELECTION_RUN_IDENTITY_SCHEMA",
    "TRAINING_TRAJECTORY_IDENTITY_SCHEMA",
    "TrainingTrajectoryIdentity",
    "PostSelectionRunRole",
    "post_selection_run_identity",
    "reject_foreign_run_continuation",
]
