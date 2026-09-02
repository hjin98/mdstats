"""Cross-owner inventory: one protection closure, then eligibility.

Per-owner classification is not sufficient.  The current P7 publication is a
read-only descendant of the accepted P5 publication and re-authenticates the
exact P5 checkpoint bytes at their canonical hot paths; P4's current terminal
authority re-reads P3 evidence; a truthful ``waiting_for_reference`` keeps the
whole predecessor lineage resumable.  Asking each artifact's nominal owner in
isolation would preserve every local owner and still break a downstream one.

So the inventory composes the owner-supplied dependency edges into a single
transitive protection closure over every current/restartable owner, and only
then decides what a safe/cache/archive action may touch.  Protection is
monotone: if any reachable current or restartable owner requires an artifact,
no other owner's cache or history classification can override that.

The closure is derived from current owner records on every invocation.  There
is deliberately no second persistent dependency database: a stale one would be
exactly the wrong kind of authority.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..storage_accounting import ProtectedInputPath
from .control_plane import StorageControlPlane, open_storage_control_plane_readonly
from .owners import (
    NODE_ABSENT,
    NODE_DIRECTORY,
    NODE_FILE,
    observed_node_kind,
    ArtifactClass,
    OwnerArtifactView,
    OwnerGraphError,
    OwnerViewSet,
    SubtreeCoverage,
    build_owner_views,
)
from .trust import crosses_mount_boundary, walk_contained

STORAGE_INVENTORY_SCHEMA = "mdstats.mlff-storage-inventory.v1"


@dataclass(frozen=True, slots=True)
class ProtectionReason:
    """Why one artifact is protected, and by which reachable dependent."""

    artifact_id: str
    required_by: str
    detail: str


@dataclass(frozen=True, slots=True)
class StorageInventorySnapshot:
    """The cross-owner snapshot every storage plan is derived from."""

    workspace: Path
    owner_views: OwnerViewSet
    protected_ids: frozenset[str]
    protection_reasons: tuple[ProtectionReason, ...]
    protected_inputs: tuple[ProtectedInputPath, ...]
    control_plane: StorageControlPlane
    #: Paths a retained cold representation still needs; never reclaimable.
    retained_control_paths: frozenset[str]
    #: ``(root, reason, container_only)`` for every protected artifact, resolved
    #: once.  Protection is asked per candidate file during dedup and cleanup, so
    #: this stays a flat scan over a small tuple rather than a per-call lookup
    #: through the whole view list.
    protection_index: tuple[tuple[Path, str, bool], ...] = ()

    # -- queries ---------------------------------------------------------

    @property
    def views(self) -> tuple[OwnerArtifactView, ...]:
        return self.owner_views.views

    @property
    def current_generation(self) -> int | None:
        return self.owner_views.current_generation

    def view(self, artifact_id: str) -> OwnerArtifactView | None:
        for item in self.views:
            if item.artifact_id == artifact_id:
                return item
        return None

    def is_protected(self, artifact_id: str) -> bool:
        return artifact_id in self.protected_ids

    def protecting_paths(self) -> tuple[Path, ...]:
        """Every canonical path the closure protects, deduplicated."""

        return tuple(
            sorted(
                {view.path for view in self.views if view.artifact_id in self.protected_ids}
            )
        )

    def hot_required_paths(self) -> tuple[Path, ...]:
        """Canonical paths a current public resolver dereferences directly."""

        return tuple(sorted({view.path for view in self.views if view.hot_path_required}))

    def path_protection(self, path: str | os.PathLike[str]) -> tuple[bool, str]:
        """Whether the closure protects one filesystem path, and why.

        A path is protected if it *is*, is inside, or contains a protected
        artifact root.  Containment in both directions matters: removing a
        parent removes the protected artifact, and removing a child breaks the
        protected artifact.
        """

        candidate = _absolute(path)
        if str(candidate) in self.retained_control_paths:
            return True, (
                "path is storage control-plane state a retained cold representation "
                "still needs to locate, authenticate, resume, or restore"
            )
        for root, detail, container_only in self.protection_index:
            if candidate == root or _within(candidate, root):
                # ``candidate`` is, or contains, the protected artifact root.
                return True, detail
            if not container_only and _within(root, candidate):
                # ``candidate`` is inside a protected artifact whose owner
                # protects its whole subtree.
                return True, detail
        for item in self.protected_inputs:
            for root in (Path(item.path), Path(item.real_path)):
                if candidate == root or _within(root, candidate) or _within(candidate, root):
                    return True, (
                        f"path overlaps the configured external input {item.key!r}, which "
                        "is never destructible regardless of how it is referenced"
                    )
        for owner, detail in self.owner_views.unresolved:
            root = self._owner_family_root(owner)
            if candidate == root or _within(root, candidate) or _within(candidate, root):
                return True, (
                    f"the {owner} owner could not be authenticated ({detail}); storage "
                    "fails toward retention for its artifacts while ownership is unresolved"
                )
        return False, ""

    def _owner_family_root(self, owner: str) -> Path:
        """The subtree an unresolved owner's failure must retain.

        Retention on owner failure is scoped to that owner's family root rather
        than to the whole workspace: an unreadable P7 record must not silently
        disable unrelated storage-native scratch reclamation, but it must
        absolutely retain every P7 artifact.
        """

        internal = self.workspace / ".mdstats"
        roots = {
            "p1": internal,
            "p2": internal,
            "p3": internal / "target-size",
            "p4": internal,
            "p5": internal / "post-selection",
            "p7": internal / "qualification",
            "campaign_store": internal,
            "storage_control_plane": self.control_plane.root,
        }
        return roots.get(owner, self.workspace)

    # -- consequential-planning gate --------------------------------------

    @property
    def integrity_failures(self) -> tuple[str, ...]:
        return self.owner_views.integrity_failures

    def require_planable(self) -> None:
        """Refuse consequential planning unless the owner graph is sound.

        An incomplete or ambiguous dependency graph cannot establish deletion,
        archive, or dedup authority, so nothing consequential is planned from
        it.  Read-only reporting stays available and shows the exact problem.
        """

        if self.integrity_failures:
            raise OwnerGraphError(
                "The owner graph is not a valid basis for consequential storage "
                "planning; storage refuses to mutate until it is repaired:\n  - "
                + "\n  - ".join(self.integrity_failures)
            )

    # -- recursive authorization ------------------------------------------

    def authorized_members(
        self, view: OwnerArtifactView
    ) -> tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]:
        """The files this owner actually certifies, and what was refused.

        Lexical containment beneath an owner root is not semantic ownership. A
        ``CLOSED`` subtree may be walked, because its owner certified that every
        descendant belongs to the artifact. A ``CONTAINER`` may not: only its
        individually certified children participate, and everything else is
        refused and left alone.

        The comparison is **typed and no-follow** throughout. A recorded regular
        file replaced by a directory at the same relative name - or the reverse -
        is an ownership contradiction, not a match, and a symlink or special node
        is never made owned by having a familiar name. Discarding the kind before
        comparing, or resolving a link to classify it, would authorize a mutation
        on something the owner never wrote.

        Mount boundaries and the physical ownership boundary reduce this further;
        they are applied by the caller, which knows whether it is deleting,
        archiving, or relinking.
        """

        refused: list[tuple[Path, str]] = []
        root = view.path
        root_kind = observed_node_kind(root)
        if root_kind == NODE_FILE:
            return (root,), ()
        if root_kind != NODE_DIRECTORY:
            return (), ()

        if view.coverage is SubtreeCoverage.CLOSED:
            if view.owner_exclusive and not view.certified_nodes:
                # A private scratch area whose only writer is the owner itself.
                # Enumerating a member set here would be circular; exclusivity
                # is the ownership statement, and it still refuses anything that
                # is not a plain file or directory.
                members = []
                for child in walk_contained(
                    root, on_refused=lambda path, why: refused.append((path, why))
                ):
                    kind = observed_node_kind(child)
                    if kind == NODE_DIRECTORY:
                        continue
                    if kind != NODE_FILE:
                        refused.append(
                            (child, f"a {kind} is never collected as an owned member")
                        )
                        continue
                    members.append(child)
                return tuple(sorted(members)), tuple(refused)
            if not view.certified_nodes:
                return (), (
                    (
                        root,
                        "the owner declares a closed subtree but recorded no typed "
                        "node set, so no descendant is individually authorized",
                    ),
                )
            certified = {root / item.path: item.kind for item in view.certified_nodes}
            retained = {root / name for name in view.retained_members}
            members: list[Path] = []
            # Walk the real tree as well: the certification says these nodes are
            # exactly what the owner produced, so anything else present is a
            # contradiction that must reduce authority rather than be ignored.
            #
            # Directories are checked too, not skipped. A recursive delete makes
            # directory nodes disappear as well, so an unexpected *empty*
            # directory that no recorded node mentions would otherwise be swept
            # away by an action nobody authorized to remove it.
            for child in walk_contained(
                root, on_refused=lambda path, why: refused.append((path, why))
            ):
                if child in retained:
                    # The owner's own certification records and locks: known,
                    # never released, and never a contradiction.
                    continue
                kind = observed_node_kind(child)
                recorded = certified.get(child)
                if recorded is None:
                    refused.append((child, f"a {kind} this owner did not record"))
                    continue
                if kind != recorded:
                    refused.append(
                        (
                            child,
                            f"the owner recorded a {recorded} here but this is a "
                            f"{kind}; a same-name substitution is not the node it "
                            "certified",
                        )
                    )
                    continue
                if kind == NODE_DIRECTORY:
                    # Covered by the certification, so it may disappear with the
                    # subtree; it is not an individually reclaimable member.
                    continue
                members.append(child)
            # A recorded node that is absent has legitimately left the tree
            # (reclaimed into an archive, for instance); it bounds what may be
            # acted on, and its absence is not a contradiction.
            return tuple(sorted(members)), tuple(refused)

        if view.coverage is SubtreeCoverage.CONTAINER and view.certified_nodes:
            members = []
            for item in view.certified_nodes:
                child = root / item.path
                crossed, why = crosses_mount_boundary(root, child)
                if crossed:
                    refused.append((child, why))
                    continue
                kind = observed_node_kind(child)
                if kind == NODE_ABSENT:
                    continue
                if kind != item.kind:
                    refused.append(
                        (
                            child,
                            f"the owner certified a {item.kind} here but this is a "
                            f"{kind}",
                        )
                    )
                    continue
                members.append(child)
            return tuple(sorted(members)), tuple(refused)

        return (), ((root, "the owner certifies no descendant of this container"),)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_INVENTORY_SCHEMA,
            "workspace": str(self.workspace),
            "current_generation": self.current_generation,
            "owner_views": [view.to_dict() for view in self.views],
            "unresolved_owners": [
                {"owner": owner, "detail": detail}
                for owner, detail in self.owner_views.unresolved
            ],
            "owner_graph_integrity_failures": list(self.integrity_failures),
            "consequential_planning_available": not self.integrity_failures,
            "protection_closure": [
                {
                    "artifact_id": reason.artifact_id,
                    "required_by": reason.required_by,
                    "detail": reason.detail,
                }
                for reason in self.protection_reasons
            ],
            "protected_inputs": [item.to_dict() for item in self.protected_inputs],
        }


def build_storage_inventory(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    protected_inputs: Sequence[ProtectedInputPath] = (),
    control_plane: StorageControlPlane | None = None,
    journal_retention_records: int = 64,
    certify: bool = False,
) -> StorageInventorySnapshot:
    """Interrogate the owners and compose the transitive protection closure.

    Read-only: the control plane is located rather than created, and the owner
    adapters use non-creating readers.

    ``certify`` decides how hard the owners are asked.  Reporting uses the cheap
    answer, so its cost stays bounded independently of how much bulk a campaign
    holds.  Consequential planning uses the exact one, because that is where a
    wrong answer would mutate bytes.
    """

    plane = control_plane or open_storage_control_plane_readonly(paths)
    owner_views = build_owner_views(
        cfg,
        paths,
        store,
        control_plane=plane,
        journal_retention_records=journal_retention_records,
        certify=certify,
    )
    protected_ids, reasons = compute_protection_closure(owner_views)
    by_id = owner_views.by_id()
    index: list[tuple[Path, str, bool]] = []
    for reason in reasons:
        view = by_id.get(reason.artifact_id)
        if view is None:
            continue
        index.append((view.path, reason.detail, bool(view.container_only)))
    return StorageInventorySnapshot(
        workspace=_absolute(paths.workspace),
        owner_views=owner_views,
        protected_ids=protected_ids,
        protection_reasons=reasons,
        protected_inputs=tuple(protected_inputs),
        control_plane=plane,
        retained_control_paths=plane.retained_archive_paths(),
        protection_index=tuple(index),
    )


def compute_protection_closure(
    owner_views: OwnerViewSet,
) -> tuple[frozenset[str], tuple[ProtectionReason, ...]]:
    """Transitively close protection over every current/restartable owner.

    Seeds are the artifacts an owner itself declares current or restart
    required.  From each seed, every ``requires`` edge is followed, so an
    artifact whose own producing stage is terminal stays protected while any
    reachable current or restartable descendant needs it.
    """

    by_id = owner_views.by_id()
    reasons: dict[str, ProtectionReason] = {}
    pending: list[tuple[str, str]] = []

    for view in owner_views.views:
        if view.current or view.restart_required:
            pending.append((view.artifact_id, view.artifact_id))

    while pending:
        artifact_id, required_by = pending.pop()
        if artifact_id in reasons:
            continue
        view = by_id.get(artifact_id)
        if view is None:
            # An edge naming an artifact no owner reported is not a licence to
            # ignore it; it is recorded so a planner can still refuse.
            reasons[artifact_id] = ProtectionReason(
                artifact_id=artifact_id,
                required_by=required_by,
                detail=(
                    f"artifact {artifact_id} is required by {required_by} but was not "
                    "reported by any owner view"
                ),
            )
            continue
        if artifact_id == required_by:
            detail = (
                f"{view.owner} declares this artifact "
                f"{'current' if view.current else 'restart-required'}: {view.detail}"
            )
        else:
            detail = (
                f"required by {required_by} through the cross-owner dependency closure: "
                f"{view.detail}"
            )
        reasons[artifact_id] = ProtectionReason(
            artifact_id=artifact_id, required_by=required_by, detail=detail
        )
        for dependency in view.requires:
            if dependency not in reasons:
                pending.append((dependency, artifact_id))

    ordered = tuple(sorted(reasons.values(), key=lambda item: item.artifact_id))
    return frozenset(reasons), ordered


@dataclass(frozen=True, slots=True)
class EligibilityDecision:
    """One artifact's eligibility for one requested storage action."""

    artifact_id: str
    path: Path
    eligible: bool
    reason: str
    capability_cost: str = "none"


def safe_candidates(snapshot: StorageInventorySnapshot) -> tuple[EligibilityDecision, ...]:
    """Zero-capability-loss candidates the owners positively released.

    Safe never performs acceleration-cache eviction: the SHA receipt store and
    the frame cache are retained by this tier even when their owners could
    certify reconstruction.
    """

    decisions: list[EligibilityDecision] = []
    for view in snapshot.views:
        if not view.safe_reclaimable or not _present(view.path):
            continue
        protected, why = snapshot.path_protection(view.path)
        if protected:
            decisions.append(
                EligibilityDecision(view.artifact_id, view.path, False, why)
            )
            continue
        decisions.append(
            EligibilityDecision(
                view.artifact_id,
                view.path,
                True,
                f"{view.owner} released this artifact: {view.detail}",
            )
        )
    return tuple(decisions)


def cache_candidates(snapshot: StorageInventorySnapshot) -> tuple[EligibilityDecision, ...]:
    """Owner-certified exactly reconstructible cache/index eviction.

    An artifact reaches this list only when its owner can still prove the exact
    reconstruction *now*, not merely because it sits in a directory whose name
    contains "cache".  Everything else is retained, and a `cache` action over a
    campaign with no certified family is legitimately a no-op.
    """

    decisions: list[EligibilityDecision] = []
    for view in snapshot.views:
        if view.artifact_class is not ArtifactClass.REUSABLE_CACHE_INDEX:
            continue
        if not _present(view.path):
            continue
        if not (view.cache_reconstructible and view.cache_evictable):
            decisions.append(
                EligibilityDecision(
                    view.artifact_id,
                    view.path,
                    False,
                    (
                        f"no owner-certified exact reconstruction: {view.detail}"
                        if not view.cache_reconstructible
                        else f"owner retains this cache in the cache tier: {view.detail}"
                    ),
                )
            )
            continue
        protected, why = snapshot.path_protection(view.path)
        if protected:
            decisions.append(EligibilityDecision(view.artifact_id, view.path, False, why))
            continue
        decisions.append(
            EligibilityDecision(
                view.artifact_id,
                view.path,
                True,
                f"owner-certified reconstructible: {view.reconstruction}",
                capability_cost="recomputation_only",
            )
        )
    return tuple(decisions)


def archive_candidates(snapshot: StorageInventorySnapshot) -> tuple[EligibilityDecision, ...]:
    """Owner-declared cold-replaceable reproducibility bulk.

    Hot removal additionally requires that no current public resolver
    dereferences the canonical hot path.  Archive is not a transparent virtual
    filesystem: this package never gives a P1-P7 loader an implicit
    "if missing, read the storage archive" fallback, so an artifact a current
    resolver needs hot simply is not archive-removable.
    """

    hot_required = set(snapshot.hot_required_paths())
    decisions: list[EligibilityDecision] = []
    for view in snapshot.views:
        if not view.archive_eligible or not _present(view.path):
            continue
        protected, why = snapshot.path_protection(view.path)
        if protected:
            decisions.append(EligibilityDecision(view.artifact_id, view.path, False, why))
            continue
        conflict = next(
            (
                required
                for required in hot_required
                if required == view.path
                or _within(view.path, required)
                or _within(required, view.path)
            ),
            None,
        )
        if conflict is not None:
            decisions.append(
                EligibilityDecision(
                    view.artifact_id,
                    view.path,
                    False,
                    (
                        "a current public owner resolver dereferences this canonical hot "
                        f"path directly ({conflict}); archive never inserts a cold-read "
                        "dependency underneath a scientific or currentness owner"
                    ),
                )
            )
            continue
        decisions.append(
            EligibilityDecision(
                view.artifact_id,
                view.path,
                True,
                f"{view.owner} declares this historical reproducibility bulk: {view.detail}",
                capability_cost="explicit_restore_required",
            )
        )
    return tuple(decisions)


def _present(path: Path) -> bool:
    """An artifact that is not on disk is not a reclamation candidate."""

    return path.exists() or path.is_symlink()


def _absolute(path: Any) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


__all__ = [
    "STORAGE_INVENTORY_SCHEMA",
    "OwnerGraphError",
    "EligibilityDecision",
    "ProtectionReason",
    "StorageInventorySnapshot",
    "archive_candidates",
    "build_storage_inventory",
    "cache_candidates",
    "compute_protection_closure",
    "safe_candidates",
]
