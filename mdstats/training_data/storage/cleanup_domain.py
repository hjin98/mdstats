"""The one canonical cleanup semantic classification.

Cleanup is not one destructive operation; it is several, each spending a
different kind of owner authority.  Removing a released P7 attempt member spends
a live attempt session's proof/release/root binding.  Emptying an owner-scoped
container spends typed member certification, retained members, and the owner's
root/path identity.  Unlinking an orphan record file spends nothing beyond the
plan's own target identity.

Before this module the routing decision existed twice - once in production
``_cleanup_engine`` and once, much weaker, in the executor's default engine -
and both were shaped as *negative* fallthrough: whatever no earlier branch
matched became a generic recursive removal.  That shape is the mechanism by
which owner authority silently disappears, because a view the classifier has
never heard of looks exactly like a view that needs no authority.

So the decision lives here once, and it is a **positive allow-domain**.  Every
cleanup action resolves to exactly one semantic class or to
:data:`CLASS_INVALID`.  A new owner field, coverage mode, or exact authorizer
does not become generic by default; it becomes invalid, and invalid never
mutates.

The classification is derived from the **fresh post-``revalidate_plan``
snapshot**, while the storage-operation lease and every touched owner's
activity/publication barrier are still held.  Classifying from the planning
snapshot would re-introduce exactly the check-then-act gap the executor exists
to close.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .owners import (
    NODE_ABSENT,
    NODE_DIRECTORY,
    NODE_FILE,
    NODE_SYMLINK,
    ArtifactClass,
    OwnerArtifactView,
    P7_RELEASED_ATTEMPT_AUTHORIZER,
    SubtreeCoverage,
    observed_node_kind,
)
from .plan import (
    ACTION_EVICT_CACHE,
    ACTION_REMOVE,
    MAINTENANCE_ACTIONS,
    PlannedAction,
    StoragePlan,
)
from .policy import TIER_CACHE, StoragePolicy

#: A released-attempt or other owner-specific exact authorizer decides this
#: action.  Only the named owner implementation may mutate it.
CLASS_EXACT_AUTHORIZER = "exact_authorizer"
#: A directory/container whose removal spends typed member, retained-member, and
#: owner root/path authority.  Never default-engine work.
CLASS_OWNER_SUBTREE = "owner_subtree"
#: A non-directory leaf whose mutation needs nothing beyond the plan-bound
#: target identity and the synchronization already held.  The only destructive
#: class the default engine may execute.
CLASS_GENERIC_LEAF = "generic_leaf"
#: Campaign-state maintenance; realized by its own owner engine.
CLASS_MAINTENANCE = "maintenance"
#: Nothing above could be positively established.  Fails closed before mutation.
CLASS_INVALID = "invalid"

#: The exact authorizers a specialized owner implementation exists for.  An
#: authorizer absent from this set is unsupported, never generic.
IMPLEMENTED_EXACT_AUTHORIZERS = (P7_RELEASED_ATTEMPT_AUTHORIZER,)

#: Node kinds a generic leaf may be.  ``other`` (fifo, socket, device) is
#: deliberately excluded: no owner in this product certifies one, so a special
#: node at an owned name is a contradiction rather than a small file.
GENERIC_LEAF_KINDS = (NODE_FILE, NODE_SYMLINK)


class StorageEngineDomainError(RuntimeError):
    """The selected engine cannot execute every action in this plan.

    Raised only after :meth:`StorageExecutor.run` has materialized and published
    the refused, non-mutating truth of the execution.  It is an engine/domain
    construction failure, not an owner's refusal of a particular target, and it
    never fabricates per-action mutation truth.
    """


@dataclass(frozen=True, slots=True)
class CleanupClassification:
    """One cleanup action's single semantic class, and why."""

    action: PlannedAction
    semantic_class: str
    view: OwnerArtifactView | None
    detail: str
    exact_authorizer: str = ""

    @property
    def valid(self) -> bool:
        return self.semantic_class != CLASS_INVALID


def classify_cleanup_action(
    action: PlannedAction,
    snapshot,
    policy: StoragePolicy,
) -> CleanupClassification:
    """Resolve one cleanup action to exactly one semantic class.

    ``snapshot`` is the fresh, already-revalidated inventory; ``policy`` is the
    resolved policy the plan was authorized under.  Neither is re-derived here:
    this function decides *who* may act, never *whether* the closure allows it.
    """

    def _invalid(detail: str, view: OwnerArtifactView | None = None):
        return CleanupClassification(action, CLASS_INVALID, view, detail)

    if action.action in MAINTENANCE_ACTIONS:
        return CleanupClassification(
            action,
            CLASS_MAINTENANCE,
            None,
            "campaign-state maintenance is realized by its own owner engine",
        )
    if action.action not in (ACTION_REMOVE, ACTION_EVICT_CACHE):
        return _invalid(
            f"action {action.action!r} is not a cleanup action; it belongs to the "
            "archive, dedup, or restore engine and is not executable here"
        )

    view = snapshot.view(action.artifact_id)
    if view is None:
        return _invalid(
            f"no current owner view reports artifact {action.artifact_id!r}, so no "
            "owner authorizes this action"
        )
    if view.path != action.path:
        # An `artifact_id` is a name, not authority. Without this the plan could
        # name a legitimately reclaimable artifact and point the mutation at an
        # entirely different campaign-owned path that happens to pass the
        # physical boundary.
        return _invalid(
            f"the owner view for {action.artifact_id!r} is at {view.path}, but this "
            f"action targets {action.path}; a cleanup action may not name one owner "
            "artifact and mutate another",
            view,
        )

    eligible, why = _action_kind_eligibility(action, view, policy)
    if not eligible:
        return _invalid(why, view)

    if view.exact_authorizer:
        if view.exact_authorizer in IMPLEMENTED_EXACT_AUTHORIZERS:
            return CleanupClassification(
                action,
                CLASS_EXACT_AUTHORIZER,
                view,
                (
                    f"the {view.exact_authorizer} owner decides this artifact's "
                    "members and mutates them under its own live capability"
                ),
                exact_authorizer=view.exact_authorizer,
            )
        return _invalid(
            f"the owner names the exact authorizer {view.exact_authorizer!r}, for "
            "which no owner implementation exists here; an unrecognized authorizer "
            "is never treated as generic removal",
            view,
        )

    kind = observed_node_kind(action.path)
    if kind == NODE_ABSENT:
        # Already-absent is the outcome the action wanted, and `revalidate_plan`
        # deliberately permits it. Classify from the identity the plan bound so
        # a disappeared directory is still not routed as a leaf.
        kind = str(action.filesystem_identity.get("kind", "")) or NODE_ABSENT

    if kind == NODE_DIRECTORY:
        return CleanupClassification(
            action,
            CLASS_OWNER_SUBTREE,
            view,
            (
                "a directory artifact is removed only through the owner-scoped "
                "certified-subtree implementation, which spends typed member, "
                "retained-member, and owner root/path authority"
            ),
        )
    if kind not in GENERIC_LEAF_KINDS:
        return _invalid(
            f"{action.path} is a {kind}; no owner certifies a node of that kind, so "
            "no cleanup implementation may act on it",
            view,
        )

    unsupported = _leaf_authority_requirements(view)
    if unsupported:
        return _invalid(
            f"the owner view for {action.artifact_id!r} requires "
            + ", ".join(unsupported)
            + "; that authority is spent by an owner-scoped implementation and is "
            "not generic leaf work",
            view,
        )
    return CleanupClassification(
        action,
        CLASS_GENERIC_LEAF,
        view,
        (
            f"a {kind} the owner released whose mutation needs nothing beyond the "
            "plan-bound target identity and the synchronization already held"
        ),
    )


def _action_kind_eligibility(
    action: PlannedAction, view: OwnerArtifactView, policy: StoragePolicy
) -> tuple[bool, str]:
    """Whether the *current* owner view still grants this exact action kind.

    Path authorization answers "may storage touch these bytes at all".  This
    answers "does the owner still release this artifact for *this* action", which
    is a different question and is the one a malformed or drifted plan gets
    wrong.
    """

    if action.action == ACTION_REMOVE:
        if not view.safe_reclaimable:
            return False, (
                f"the current {view.owner} view does not release "
                f"{action.artifact_id!r} for safe reclamation: {view.detail}"
            )
        return True, ""

    # ACTION_EVICT_CACHE
    if policy.tier != TIER_CACHE:
        return False, (
            f"cache eviction is not authorized under the {policy.tier!r} tier this "
            "plan was resolved for"
        )
    if view.artifact_class is not ArtifactClass.REUSABLE_CACHE_INDEX:
        return False, (
            f"{action.artifact_id!r} is classified {view.artifact_class.value}, not a "
            "reusable cache/index, so it is not an eviction target"
        )
    if not view.cache_reconstructible:
        return False, (
            f"the current {view.owner} view no longer certifies an exact "
            f"reconstruction of {action.artifact_id!r}: {view.detail}"
        )
    if not view.cache_evictable:
        return False, (
            f"the current {view.owner} view retains {action.artifact_id!r} in the "
            f"cache tier: {view.detail}"
        )
    return True, ""


def _leaf_authority_requirements(view: OwnerArtifactView) -> tuple[str, ...]:
    """Owner authority a generic leaf removal would have to spend but cannot."""

    required: list[str] = []
    if view.coverage is not SubtreeCoverage.NOT_APPLICABLE:
        required.append(f"{view.coverage.value} subtree coverage")
    if view.certified_nodes or view.certified_members:
        required.append("typed member certification")
    if view.retained_members:
        required.append("retained-member authority")
    if view.container_only:
        required.append("container-only member authority")
    if view.owner_exclusive:
        required.append("exclusive-writer subtree authority")
    if view.root_identity is not None:
        required.append("an independent owner authority-root identity")
    if view.path_identity is not None:
        required.append("an independent owner path identity")
    return tuple(required)


def classify_cleanup_plan(
    plan: StoragePlan, snapshot, policy: StoragePolicy | None = None
) -> tuple[CleanupClassification, ...]:
    """Classify every action in one plan, in plan order."""

    resolved = policy if policy is not None else plan.policy
    return tuple(
        classify_cleanup_action(action, snapshot, resolved) for action in plan.actions
    )


def require_supported_domain(
    classifications: Sequence[CleanupClassification],
    *,
    engine: str,
    supported: Sequence[str],
) -> None:
    """Refuse the whole plan unless every action is in this engine's domain.

    Plan-wide and order-independent on purpose.  Discovering an unsupported
    action only when the loop reaches it would mean a convenient prefix of the
    plan had already been spent - a partial cleanup nobody authorized, produced
    by a routing bug rather than by an owner's decision.
    """

    allowed = set(supported)
    problems = [
        f"{item.action.action} {item.action.path} [{item.semantic_class}]: {item.detail}"
        for item in classifications
        if item.semantic_class not in allowed
    ]
    if not problems:
        return
    raise StorageEngineDomainError(
        f"the {engine} cannot execute this plan; no action was attempted:\n  - "
        + "\n  - ".join(problems)
    )


__all__ = [
    "CLASS_EXACT_AUTHORIZER",
    "CLASS_GENERIC_LEAF",
    "CLASS_INVALID",
    "CLASS_MAINTENANCE",
    "CLASS_OWNER_SUBTREE",
    "GENERIC_LEAF_KINDS",
    "IMPLEMENTED_EXACT_AUTHORIZERS",
    "CleanupClassification",
    "StorageEngineDomainError",
    "classify_cleanup_action",
    "classify_cleanup_plan",
    "require_supported_domain",
]
