"""The post-selection cross-validation plan.

Cross-validation happens strictly after ``T_selected`` is frozen, and its
universe is exactly ``T_selected`` - never more, never less.  Leakage safety is
inherited whole from the canonical P1 split-exclusion relation authority, not
rediscovered here: this module projects that authority onto the selected frames,
reduces it to deterministic transitive components, and allocates fold roles at
component granularity so a chain through correlation units, geometry
duplicates, protected events, and replica/structural lineages stays indivisible.

The plan is a *derived* record.  It descends from the current selected binding,
the shared method identity, the CV policy identity, and the current P1 relation
authority; none of those may be recomputed from the plan.  Changing the P1
relation authority or the selected data changes or rejects the plan while
leaving the CV *policy* digest untouched, which is exactly the separation the
parent invalidation DAG requires.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionBinding,
    PostSelectionError,
)
from .neutral_substrate.split_exclusion import (
    project_split_exclusion_constraint_components,
    split_exclusion_component_digest,
)
from .post_selection_identity import (
    CvValidationPolicyIdentity,
    PostSelectionMethodIdentity,
)
from .post_selection_run_identity import (
    PostSelectionRunRole,
    post_selection_run_identity,
)

SELECTED_RELATION_PROJECTION_SCHEMA = "mdstats.post-selection-relation-projection.v1"
POST_SELECTION_CV_FOLD_SCHEMA = "mdstats.post-selection-cv-fold.v1"
POST_SELECTION_CV_PLAN_SCHEMA = "mdstats.post-selection-cv-plan.v1"
POST_SELECTION_CV_FOLD_RUN_PLAN_SCHEMA = "mdstats.post-selection-cv-fold-run-plan.v1"


class PostSelectionCvInfeasibleError(PostSelectionError):
    """The configured CV cannot be built on the selected data without leakage."""


@dataclass(frozen=True, slots=True)
class SelectedRelationProjection:
    """The complete P1 split-exclusion authority projected onto ``T_selected``.

    Only endpoints already inside ``T_selected`` take part.  A related but
    unselected sibling constrains nothing here because it is not in the CV
    universe at all - it can never be pulled in to keep a relation whole.
    """

    relation_authority_digest: str
    frame_authority_digest: str
    neutral_unit_catalog_digest: str
    selected_membership_digest: str
    components: tuple[tuple[str, ...], ...]

    def __post_init__(self) -> None:
        for name in (
            "relation_authority_digest",
            "frame_authority_digest",
            "neutral_unit_catalog_digest",
            "selected_membership_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        components = tuple(
            tuple(str(uid) for uid in component) for component in self.components
        )
        if not components:
            raise TrainingDataInputError(
                "A selected relation projection requires at least one component."
            )
        seen: set[str] = set()
        for component in components:
            if not component or len(set(component)) != len(component):
                raise TrainingDataInputError(
                    "Split-exclusion components must be unique and non-empty."
                )
            if seen & set(component):
                raise TrainingDataInputError(
                    "Split-exclusion components must be disjoint."
                )
            seen.update(component)
        object.__setattr__(self, "components", components)

    @property
    def component_identities(self) -> tuple[str, ...]:
        return tuple(
            split_exclusion_component_digest(component) for component in self.components
        )

    def component_of(self, frame_uid: str) -> str:
        for component in self.components:
            if str(frame_uid) in component:
                return split_exclusion_component_digest(component)
        raise TrainingDataInputError(
            "Frame is outside the selected split-exclusion projection."
        )

    def frames_by_component(self) -> dict[str, tuple[str, ...]]:
        return {
            split_exclusion_component_digest(component): component
            for component in self.components
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SELECTED_RELATION_PROJECTION_SCHEMA,
            "relation_authority_digest": self.relation_authority_digest,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_unit_catalog_digest": self.neutral_unit_catalog_digest,
            "selected_membership_digest": self.selected_membership_digest,
            "components": [list(component) for component in self.components],
            "component_identities": list(self.component_identities),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SelectedRelationProjection":
        if payload.get("schema") != SELECTED_RELATION_PROJECTION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported selected relation-projection schema."
            )
        result = cls(
            relation_authority_digest=str(payload["relation_authority_digest"]),
            frame_authority_digest=str(payload["frame_authority_digest"]),
            neutral_unit_catalog_digest=str(payload["neutral_unit_catalog_digest"]),
            selected_membership_digest=str(payload["selected_membership_digest"]),
            components=tuple(
                tuple(str(uid) for uid in component)
                for component in payload["components"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Selected relation-projection digest mismatch."
            )
        return result


def build_selected_relation_projection(
    context: CurrentSelectedTrainingContext,
) -> SelectedRelationProjection:
    """Project the current P1 relation authority onto the exact selected data.

    The relation semantics belong to P1 and are consumed, never re-derived: this
    function passes the accepted evidence object straight to the canonical
    closure owner that P2 already uses, so correlation units, geometry
    duplicates, protected events, and condition-scoped replica/structural
    lineages all participate with no P5-local taxonomy.
    """

    authorities = context.authorities
    split_exclusion = authorities.split_exclusion
    frame_authority_digest = authorities.frame_authority.content_digest
    unit_catalog_digest = authorities.neutral_base.unit_catalog.content_digest
    if split_exclusion.content_digest != context.binding.split_exclusion_digest:
        raise PostSelectionError(
            "The reconstructed P1 split-exclusion authority does not match the "
            "authenticated current selected binding."
        )
    components = project_split_exclusion_constraint_components(
        context.selected_membership,
        split_exclusion,
        frame_authority_digest=frame_authority_digest,
        neutral_unit_catalog_digest=unit_catalog_digest,
    )
    return SelectedRelationProjection(
        relation_authority_digest=split_exclusion.content_digest,
        frame_authority_digest=frame_authority_digest,
        neutral_unit_catalog_digest=unit_catalog_digest,
        selected_membership_digest=context.selected_membership_digest,
        components=components,
    )


@dataclass(frozen=True, slots=True)
class PostSelectionCvFold:
    """Exact selected-only role membership for one fold.

    Accounting is complete by construction and re-checked here: training,
    checkpoint monitor, outer evaluation, and purge partition the selected
    universe exactly.  A frame that simply disappeared would be a silent
    reduction of the cross-validated population, so it is rejected.
    """

    fold_index: int
    training_frame_uids: tuple[str, ...]
    checkpoint_monitor_frame_uids: tuple[str, ...]
    outer_evaluation_frame_uids: tuple[str, ...]
    purged_frame_uids: tuple[str, ...]
    training_component_ids: tuple[str, ...]
    checkpoint_monitor_component_ids: tuple[str, ...]
    outer_evaluation_component_ids: tuple[str, ...]
    purged_component_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        index = int(self.fold_index)
        if index < 0:
            raise TrainingDataInputError("fold_index must be nonnegative.")
        object.__setattr__(self, "fold_index", index)
        for name in (
            "training_frame_uids",
            "checkpoint_monitor_frame_uids",
            "outer_evaluation_frame_uids",
            "purged_frame_uids",
            "training_component_ids",
            "checkpoint_monitor_component_ids",
            "outer_evaluation_component_ids",
            "purged_component_ids",
        ):
            values = tuple(sorted(str(v) for v in getattr(self, name)))
            if len(set(values)) != len(values):
                raise TrainingDataInputError(f"{name} must be unique.")
            object.__setattr__(self, name, values)
        if not self.training_frame_uids:
            raise TrainingDataInputError("A CV fold requires gradient-training frames.")
        if not self.checkpoint_monitor_frame_uids:
            raise TrainingDataInputError(
                "A CV fold requires its own selected-only checkpoint monitor."
            )
        if not self.outer_evaluation_frame_uids:
            raise TrainingDataInputError(
                "A CV fold requires a held-out outer evaluation membership."
            )
        groups = (
            set(self.training_frame_uids),
            set(self.checkpoint_monitor_frame_uids),
            set(self.outer_evaluation_frame_uids),
            set(self.purged_frame_uids),
        )
        for position, left in enumerate(groups):
            for right in groups[position + 1 :]:
                if left & right:
                    raise TrainingDataInputError(
                        "Cross-validation fold roles must be disjoint."
                    )

    @property
    def all_frame_uids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                set(self.training_frame_uids)
                | set(self.checkpoint_monitor_frame_uids)
                | set(self.outer_evaluation_frame_uids)
                | set(self.purged_frame_uids)
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_CV_FOLD_SCHEMA,
            "fold_index": self.fold_index,
            "training_frame_uids": list(self.training_frame_uids),
            "checkpoint_monitor_frame_uids": list(self.checkpoint_monitor_frame_uids),
            "outer_evaluation_frame_uids": list(self.outer_evaluation_frame_uids),
            "purged_frame_uids": list(self.purged_frame_uids),
            "training_component_ids": list(self.training_component_ids),
            "checkpoint_monitor_component_ids": list(
                self.checkpoint_monitor_component_ids
            ),
            "outer_evaluation_component_ids": list(self.outer_evaluation_component_ids),
            "purged_component_ids": list(self.purged_component_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionCvFold":
        if payload.get("schema") != POST_SELECTION_CV_FOLD_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection CV fold schema."
            )
        result = cls(
            fold_index=int(payload["fold_index"]),
            training_frame_uids=tuple(str(v) for v in payload["training_frame_uids"]),
            checkpoint_monitor_frame_uids=tuple(
                str(v) for v in payload["checkpoint_monitor_frame_uids"]
            ),
            outer_evaluation_frame_uids=tuple(
                str(v) for v in payload["outer_evaluation_frame_uids"]
            ),
            purged_frame_uids=tuple(str(v) for v in payload["purged_frame_uids"]),
            training_component_ids=tuple(
                str(v) for v in payload["training_component_ids"]
            ),
            checkpoint_monitor_component_ids=tuple(
                str(v) for v in payload["checkpoint_monitor_component_ids"]
            ),
            outer_evaluation_component_ids=tuple(
                str(v) for v in payload["outer_evaluation_component_ids"]
            ),
            purged_component_ids=tuple(str(v) for v in payload["purged_component_ids"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection CV fold digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class PostSelectionCvPlan:
    """One immutable current cross-validation plan.

    This is the CV *plan* identity: current selected lineage, the shared method,
    the CV policy, the current P1 relation authority, the exact selected-only
    projection, exact fold memberships, and the exact required run matrix.  It
    depends on the policy; the policy never depends on it.
    """

    binding: PostSelectionBinding
    method_identity_digest: str
    cv_policy_identity_digest: str
    relation_authority_digest: str
    projection_digest: str
    fold_count: int
    folds: tuple[PostSelectionCvFold, ...]
    required_cv_seeds: tuple[int, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "A CV plan requires the authenticated selected binding."
            )
        for name in (
            "method_identity_digest",
            "cv_policy_identity_digest",
            "relation_authority_digest",
            "projection_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        folds = tuple(sorted(self.folds, key=lambda item: item.fold_index))
        count = int(self.fold_count)
        if count < 2 or len(folds) != count:
            raise PostSelectionError(
                "The current CV plan requires K >= 2 folds and exactly K fold records."
            )
        if tuple(item.fold_index for item in folds) != tuple(range(count)):
            raise TrainingDataInputError("CV fold indices must be contiguous from zero.")
        held_out: list[str] = []
        for fold in folds:
            held_out.extend(fold.outer_evaluation_component_ids)
        if len(set(held_out)) != len(held_out):
            raise PostSelectionError(
                "A selected split-exclusion component may be held out in exactly one "
                "outer fold; duplicated outer coverage is not cross-validation."
            )
        object.__setattr__(self, "folds", folds)
        object.__setattr__(self, "fold_count", count)
        seeds = tuple(sorted(int(v) for v in self.required_cv_seeds))
        if not seeds or len(set(seeds)) != len(seeds):
            raise TrainingDataInputError(
                "A CV plan requires a non-empty unique required-seed matrix."
            )
        object.__setattr__(self, "required_cv_seeds", seeds)

    @property
    def held_out_component_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                component
                for fold in self.folds
                for component in fold.outer_evaluation_component_ids
            )
        )

    @property
    def required_run_matrix(self) -> tuple[tuple[int, int], ...]:
        return tuple(
            (seed, fold.fold_index)
            for seed in self.required_cv_seeds
            for fold in self.folds
        )

    def fold(self, fold_index: int) -> PostSelectionCvFold:
        for item in self.folds:
            if item.fold_index == int(fold_index):
                return item
        raise TrainingDataInputError(f"Unknown CV fold index {fold_index}.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_CV_PLAN_SCHEMA,
            "binding": self.binding.to_dict(),
            "method_identity_digest": self.method_identity_digest,
            "cv_policy_identity_digest": self.cv_policy_identity_digest,
            "relation_authority_digest": self.relation_authority_digest,
            "projection_digest": self.projection_digest,
            "fold_count": self.fold_count,
            "folds": [item.to_dict() for item in self.folds],
            "required_cv_seeds": list(self.required_cv_seeds),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionCvPlan":
        if payload.get("schema") != POST_SELECTION_CV_PLAN_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection CV plan schema."
            )
        result = cls(
            binding=PostSelectionBinding.from_dict(payload["binding"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            cv_policy_identity_digest=str(payload["cv_policy_identity_digest"]),
            relation_authority_digest=str(payload["relation_authority_digest"]),
            projection_digest=str(payload["projection_digest"]),
            fold_count=int(payload["fold_count"]),
            folds=tuple(
                PostSelectionCvFold.from_dict(item) for item in payload["folds"]
            ),
            required_cv_seeds=tuple(int(v) for v in payload["required_cv_seeds"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection CV plan digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class PostSelectionCvFoldRunPlan:
    """One exact ``(CV plan, seed, fold)`` execution position.

    The run identity carries the CV role, so a screening or final-production job
    with the same numeric seed cannot share this run's checkpoint root, restart
    ownership, or publication identity.
    """

    cv_plan_digest: str
    method_identity_digest: str
    cv_policy_identity_digest: str
    selected_binding_digest: str
    fold_index: int
    optimizer_seed: int
    planned_epochs: int
    run_identity: str
    run_role: str = PostSelectionRunRole.POST_SELECTION_CV.value

    def __post_init__(self) -> None:
        for name in (
            "cv_plan_digest",
            "method_identity_digest",
            "cv_policy_identity_digest",
            "selected_binding_digest",
            "run_identity",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if PostSelectionRunRole(self.run_role) is not PostSelectionRunRole.POST_SELECTION_CV:
            raise TrainingDataInputError(
                "A CV fold run plan must carry the cross-validation run role."
            )
        object.__setattr__(self, "fold_index", int(self.fold_index))
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        planned = int(self.planned_epochs)
        if planned <= 0:
            raise TrainingDataInputError("planned_epochs must be positive.")
        object.__setattr__(self, "planned_epochs", planned)
        expected = post_selection_run_identity(
            role=PostSelectionRunRole.POST_SELECTION_CV,
            plan_digest=self.cv_plan_digest,
            optimizer_seed=self.optimizer_seed,
            fold_index=self.fold_index,
        )
        if expected != self.run_identity:
            raise TrainingDataInputError(
                "CV fold run identity does not match its (plan, seed, fold) position."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_CV_FOLD_RUN_PLAN_SCHEMA,
            "cv_plan_digest": self.cv_plan_digest,
            "method_identity_digest": self.method_identity_digest,
            "cv_policy_identity_digest": self.cv_policy_identity_digest,
            "selected_binding_digest": self.selected_binding_digest,
            "fold_index": self.fold_index,
            "optimizer_seed": self.optimizer_seed,
            "planned_epochs": self.planned_epochs,
            "run_role": PostSelectionRunRole(self.run_role).value,
            "run_identity": self.run_identity,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionCvFoldRunPlan":
        if payload.get("schema") != POST_SELECTION_CV_FOLD_RUN_PLAN_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection CV fold run-plan schema."
            )
        result = cls(
            cv_plan_digest=str(payload["cv_plan_digest"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            cv_policy_identity_digest=str(payload["cv_policy_identity_digest"]),
            selected_binding_digest=str(payload["selected_binding_digest"]),
            fold_index=int(payload["fold_index"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            planned_epochs=int(payload["planned_epochs"]),
            run_role=str(payload["run_role"]),
            run_identity=str(payload["run_identity"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection CV fold run-plan digest mismatch."
            )
        return result


# ---------------------------------------------------------------------------
# Deterministic fold construction
# ---------------------------------------------------------------------------


def _seeded_component_order(
    component_ids: Sequence[str], *, seed: int, salt: str
) -> tuple[str, ...]:
    """Deterministic seeded order over canonical component identities.

    Ordering by a keyed hash rather than by a PRNG stream keeps the result
    identical across Python versions and independent of how the components were
    discovered, so the same policy and the same selected data always reproduce
    the same folds byte for byte.
    """

    def key(component_id: str) -> tuple[str, str]:
        marker = hashlib.sha256(
            f"{salt}|{int(seed)}|{component_id}".encode("utf-8")
        ).hexdigest()
        return (marker, component_id)

    return tuple(sorted((str(v) for v in component_ids), key=key))


def _spaced_selection(ordered: Sequence[str], count: int) -> tuple[str, ...]:
    """Pick ``count`` evenly spaced entries from a deterministic order."""

    total = len(ordered)
    if count <= 0 or total < count:
        return ()
    if count == 1:
        return (ordered[total // 2],)
    step = (total - 1) / (count - 1)
    indices = sorted({int(round(position * step)) for position in range(count)})
    while len(indices) < count:
        for candidate in range(total):
            if candidate not in indices:
                indices.append(candidate)
                break
        indices = sorted(set(indices))
    return tuple(ordered[index] for index in indices[:count])


def build_post_selection_cv_plan(
    context: CurrentSelectedTrainingContext,
    method: PostSelectionMethodIdentity,
    policy: CvValidationPolicyIdentity,
    *,
    projection: SelectedRelationProjection | None = None,
) -> PostSelectionCvPlan:
    """Build the complete selected-only K-fold plan, or fail before training.

    Every CV-eligible selected component is held out as outer evaluation exactly
    once, so the plan covers the selected population rather than a convenient
    subset.  When the configured ``K`` cannot be satisfied under the inherited
    split-exclusion constraints, this raises with a deterministic diagnostic
    instead of quietly shrinking to fewer folds or synthesizing evidence -
    reducing the fold count would be a scientific policy change, and this
    implementation has no authority to make one.
    """

    resolved_projection = (
        build_selected_relation_projection(context) if projection is None else projection
    )
    if resolved_projection.selected_membership_digest != context.selected_membership_digest:
        raise PostSelectionError(
            "The selected relation projection binds a different selected membership."
        )
    frames_by_component = resolved_projection.frames_by_component()
    component_ids = tuple(sorted(frames_by_component))
    fold_count = policy.fold_count
    if len(component_ids) < fold_count:
        raise PostSelectionCvInfeasibleError(
            f"The selected data yields {len(component_ids)} independent "
            f"split-exclusion components, which cannot support K={fold_count} "
            "outer folds. Cross-validation fails here, before any DATA7/DATA8 or "
            "TRAIN2 work: the fold count is not silently reduced and the selected "
            "population is never enlarged to make K feasible."
        )

    ordered = _seeded_component_order(
        component_ids,
        seed=policy.partition_seed,
        salt=f"{policy.fold_construction_algorithm}|{context.selected_membership_digest}",
    )
    outer_by_fold: list[list[str]] = [[] for _ in range(fold_count)]
    for position, component_id in enumerate(ordered):
        outer_by_fold[position % fold_count].append(component_id)

    folds: list[PostSelectionCvFold] = []
    all_components = set(component_ids)
    for fold_index in range(fold_count):
        outer = set(outer_by_fold[fold_index])
        if not outer:
            raise PostSelectionCvInfeasibleError(
                f"CV fold {fold_index} has no held-out outer component."
            )
        remaining = sorted(all_components - outer)
        purge = set(
            _spaced_selection(
                tuple(remaining), min(policy.purge_components_between_roles, max(0, len(remaining) - 2))
            )
        )
        candidates = tuple(sorted(set(remaining) - purge))
        monitor = set(
            _spaced_selection(
                candidates, policy.checkpoint_monitor_components_per_fold
            )
        )
        if len(monitor) != policy.checkpoint_monitor_components_per_fold:
            raise PostSelectionCvInfeasibleError(
                f"CV fold {fold_index} cannot reserve "
                f"{policy.checkpoint_monitor_components_per_fold} checkpoint-monitor "
                f"component(s) from {len(candidates)} available component(s) under "
                "the inherited split-exclusion constraints."
            )
        training = set(candidates) - monitor
        if not training:
            raise PostSelectionCvInfeasibleError(
                f"CV fold {fold_index} has no gradient-training component left after "
                "reserving its checkpoint monitor and purge components."
            )
        assigned = outer | monitor | training | purge
        if assigned != all_components:
            raise PostSelectionError(
                f"CV fold {fold_index} accounting is incomplete: "
                f"{len(all_components - assigned)} selected component(s) would be "
                "silently omitted."
            )

        def frames(group: set[str]) -> tuple[str, ...]:
            return tuple(
                sorted(uid for item in group for uid in frames_by_component[item])
            )

        folds.append(
            PostSelectionCvFold(
                fold_index=fold_index,
                training_frame_uids=frames(training),
                checkpoint_monitor_frame_uids=frames(monitor),
                outer_evaluation_frame_uids=frames(outer),
                purged_frame_uids=frames(purge),
                training_component_ids=tuple(sorted(training)),
                checkpoint_monitor_component_ids=tuple(sorted(monitor)),
                outer_evaluation_component_ids=tuple(sorted(outer)),
                purged_component_ids=tuple(sorted(purge)),
            )
        )

    plan = PostSelectionCvPlan(
        binding=context.binding,
        method_identity_digest=method.content_digest,
        cv_policy_identity_digest=policy.content_digest,
        relation_authority_digest=resolved_projection.relation_authority_digest,
        projection_digest=resolved_projection.content_digest,
        fold_count=fold_count,
        folds=tuple(folds),
        required_cv_seeds=policy.required_cv_seeds,
    )
    validate_post_selection_cv_plan(plan, context, projection=resolved_projection)
    return plan


def validate_post_selection_cv_plan(
    plan: PostSelectionCvPlan,
    context: CurrentSelectedTrainingContext,
    *,
    projection: SelectedRelationProjection | None = None,
) -> None:
    """Re-check a CV plan against the freshly resolved current authorities.

    Restart takes this path rather than trusting the stored plan digest: the
    plan is authenticated against the current selected binding and the current
    P1 relation authority, so a rebuilt or changed relation authority rejects a
    stale plan instead of silently authorizing work under retired lineage.
    """

    context.require_binding(plan.binding)
    resolved = (
        build_selected_relation_projection(context) if projection is None else projection
    )
    if plan.relation_authority_digest != resolved.relation_authority_digest:
        raise PostSelectionError(
            "The CV plan binds a retired P1 split-exclusion relation authority; the "
            "current authority is different and the plan must be rebuilt."
        )
    if plan.projection_digest != resolved.content_digest:
        raise PostSelectionError(
            "The CV plan binds a different selected-only relation projection than the "
            "current authenticated selected data produces."
        )
    selected = set(context.selected_membership)
    universe: set[str] = set()
    for fold in plan.folds:
        members = set(fold.all_frame_uids)
        outside = members - selected
        if outside:
            raise PostSelectionError(
                f"CV fold {fold.fold_index} uses {len(outside)} frame(s) outside "
                "T_selected. The CV universe is exactly the selected data; a related "
                "but unselected sibling never enters it."
            )
        if members != selected:
            missing = len(selected - members)
            raise PostSelectionError(
                f"CV fold {fold.fold_index} accounts for {len(members)} of "
                f"{len(selected)} selected frames; {missing} would be silently "
                "omitted from cross-validation."
            )
        universe |= members
    if universe != selected:
        raise PostSelectionError(
            "The CV plan does not cover the exact selected population."
        )
    eligible = set(resolved.component_identities)
    held_out = list(plan.held_out_component_ids)
    if len(set(held_out)) != len(held_out):
        raise PostSelectionError(
            "A selected component is held out in more than one outer fold."
        )
    if set(held_out) != eligible:
        missing = sorted(eligible - set(held_out))
        raise PostSelectionError(
            f"{len(missing)} CV-eligible selected component(s) are never held out as "
            "outer evaluation; every eligible component must be evaluated exactly "
            "once across the K folds."
        )


def build_cv_fold_run_plan(
    plan: PostSelectionCvPlan,
    *,
    fold_index: int,
    optimizer_seed: int,
    planned_epochs: int,
) -> PostSelectionCvFoldRunPlan:
    """Bind one exact CV execution position below its plan."""

    if int(optimizer_seed) not in plan.required_cv_seeds:
        raise PostSelectionError(
            f"CV seed {int(optimizer_seed)} is not in the required CV run matrix "
            f"{list(plan.required_cv_seeds)}."
        )
    fold = plan.fold(fold_index)
    plan_digest = plan.content_digest
    return PostSelectionCvFoldRunPlan(
        cv_plan_digest=plan_digest,
        method_identity_digest=plan.method_identity_digest,
        cv_policy_identity_digest=plan.cv_policy_identity_digest,
        selected_binding_digest=plan.binding.content_digest,
        fold_index=fold.fold_index,
        optimizer_seed=int(optimizer_seed),
        planned_epochs=int(planned_epochs),
        run_identity=post_selection_run_identity(
            role=PostSelectionRunRole.POST_SELECTION_CV,
            plan_digest=plan_digest,
            optimizer_seed=int(optimizer_seed),
            fold_index=fold.fold_index,
        ),
    )


__all__ = [
    "POST_SELECTION_CV_FOLD_RUN_PLAN_SCHEMA",
    "POST_SELECTION_CV_FOLD_SCHEMA",
    "POST_SELECTION_CV_PLAN_SCHEMA",
    "SELECTED_RELATION_PROJECTION_SCHEMA",
    "PostSelectionCvFold",
    "PostSelectionCvFoldRunPlan",
    "PostSelectionCvInfeasibleError",
    "PostSelectionCvPlan",
    "SelectedRelationProjection",
    "build_cv_fold_run_plan",
    "build_post_selection_cv_plan",
    "build_selected_relation_projection",
    "validate_post_selection_cv_plan",
]
