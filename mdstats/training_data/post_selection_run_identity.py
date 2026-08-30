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

from enum import Enum
from typing import Any

from ._common import TrainingDataInputError, digest, validate_digest

POST_SELECTION_RUN_IDENTITY_SCHEMA = "mdstats.post-selection-run-identity.v1"


class PostSelectionRunRole(str, Enum):
    """The execution roles whose namespaces must never collide."""

    TARGET_SIZE_SCREEN = "target_size_screen"
    POST_SELECTION_CV = "post_selection_cv"
    FINAL_PRODUCTION = "final_production"


def post_selection_run_identity(
    *,
    role: PostSelectionRunRole | str,
    plan_digest: str,
    optimizer_seed: int,
    fold_index: int | None = None,
) -> str:
    """Return the run identity for one exact (role, plan, seed, fold) position.

    The role is part of the hashed payload rather than a formatting prefix, so
    two roles cannot converge on one identity by accident and cannot be made to
    converge by renaming a directory.
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
    "PostSelectionRunRole",
    "post_selection_run_identity",
    "reject_foreign_run_continuation",
]
