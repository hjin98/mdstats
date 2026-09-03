"""Owner-certified immutable deduplication by direct hardlink aliasing.

Deduplication is representation optimization only.  Two campaign files with
identical bytes become two names for one inode; nothing about what the campaign
means changes, and no durable dedup registry is created.  There is deliberately
no content-addressed object store: a persistent CAS would add its own lifetime,
garbage collection, recovery, and reporting problems in exchange for nothing
the filesystem does not already do.  When the last campaign alias of a shared
inode is removed or replaced, the filesystem releases the bytes on its own.

Eligibility is a conjunction, and every term is necessary:

``owner-certified immutability + closed link ownership + exact content identity
+ owner-certified metadata compatibility + filesystem realization support +
freshly revalidated owner authorization``

*Closed link ownership* is the term that is easy to miss.  Hardlinked names
share one inode, so an unknown pre-existing link is an unknown writer: anyone
holding it could later mutate every campaign path newly aliased to it.  The
canonical source therefore has to have exactly one link, or every existing link
must be a known member of this very group.

Exact byte equality is also not sufficient by itself.  Mode, ownership, and
other owner-required metadata are shared through the inode too, so they are
part of the grouping key rather than a post-hoc filter.

Dedup changes inode and ctime, which invalidates stat-keyed acceleration
receipts.  That is a cache miss and a revalidation, never a scientific state
change.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .durability import parallel_digests, sha256_file
from .executor import StorageExecutionResult
from .inventory import StorageInventorySnapshot
from .plan import ACTION_DEDUP_LINK, PlannedAction, StoragePlan, planned_action
from .policy import DEDUP_DISABLED, StoragePolicy

DEDUPLICATION_REPORT_SCHEMA = "mdstats.mlff-storage-deduplication.v3"


class StorageDedupError(RuntimeError):
    """A deduplication candidate failed an eligibility or safety contract."""


@dataclass(frozen=True, slots=True)
class DedupCandidate:
    path: Path
    artifact_id: str
    owner_state_identity: str
    size_bytes: int
    metadata: tuple[Any, ...]
    device: int
    inode: int
    link_count: int


@dataclass
class DedupResult:
    """What one dedup plan intends, and what an applied one actually did."""

    applied: bool
    groups: list[dict[str, Any]] = field(default_factory=list)
    links_replaced: int = 0
    reclaimed_bytes: int = 0
    excluded: list[str] = field(default_factory=list)
    realization: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": DEDUPLICATION_REPORT_SCHEMA,
            "applied": bool(self.applied),
            "realization": self.realization,
            "persistent_content_store": False,
            "group_count": len(self.groups),
            "groups": list(self.groups),
            "links_replaced": int(self.links_replaced),
            "reclaimed_bytes": int(self.reclaimed_bytes),
            "excluded": list(self.excluded),
            "receipt_invalidation": (
                "stat-keyed SHA-256 receipts for relinked paths become cache misses; "
                "revalidation rehashes and no scientific state changes"
            ),
            "grants_scientific_authority": False,
        }


def _metadata_signature(path: Path) -> tuple[Any, ...]:
    """File type, mode, uid, and gid: what two names would have to share.

    Owner-required metadata beyond this set must be declared by the owner view;
    a family requiring anything this comparison cannot establish is excluded.
    """

    stats = path.lstat()
    return (
        stat.S_IFMT(stats.st_mode),
        stat.S_IMODE(stats.st_mode),
        int(stats.st_uid),
        int(stats.st_gid),
    )


def same_filesystem(first: Path, second: Path) -> bool:
    """Whether a hardlink between these two paths is realizable at all.

    Hardlinks cannot cross a filesystem boundary. This is the single place that
    decision is made, so an unsupported layout degrades to retaining duplicate
    bytes rather than failing.
    """

    try:
        return int(first.stat().st_dev) == int(second.stat().st_dev)
    except OSError:
        return False


def collect_dedup_candidates(
    snapshot: StorageInventorySnapshot, policy: StoragePolicy
) -> tuple[tuple[DedupCandidate, ...], list[str]]:
    """Every file whose owner certified immutability *and* a metadata contract.

    Enumeration goes through the inventory's recursive-authorization rule, so a
    directory contributes members only where its owner certified the subtree as
    closed, and an unexpected descendant, a symlink, or a nested mount is
    refused rather than absorbed.
    """

    excluded: list[str] = []
    candidates: list[DedupCandidate] = []
    for view in snapshot.views:
        if not view.dedup_eligible:
            continue
        if not view.immutable:
            excluded.append(f"{view.artifact_id}: owner did not certify immutability")
            continue
        if view.metadata_contract not in ("mode_only", "mode_and_ownership"):
            excluded.append(
                f"{view.artifact_id}: owner requires filesystem metadata this "
                f"realization cannot guarantee ({view.metadata_contract})"
            )
            continue
        members, refusals = snapshot.authorized_members(view)
        for path, why in refusals:
            excluded.append(f"{path}: {why}")
        for path in members:
            protected, why = snapshot.path_protection(path)
            if protected:
                excluded.append(f"{path}: {why}")
                continue
            try:
                stats = path.lstat()
            except OSError as exc:
                excluded.append(f"{path}: could not be inspected ({exc})")
                continue
            if not stat.S_ISREG(stats.st_mode):
                continue
            if int(stats.st_size) < int(policy.dedup_minimum_file_bytes):
                continue
            candidates.append(
                DedupCandidate(
                    path=path,
                    artifact_id=view.artifact_id,
                    owner_state_identity=view.state_identity,
                    size_bytes=int(stats.st_size),
                    metadata=_metadata_signature(path),
                    device=int(stats.st_dev),
                    inode=int(stats.st_ino),
                    link_count=int(stats.st_nlink),
                )
            )
    return tuple(candidates), excluded


def plan_dedup_groups(
    candidates: Sequence[DedupCandidate],
    excluded: list[str],
    *,
    io_workers: int = 1,
    accelerated: bool = False,
) -> list[dict[str, Any]]:
    """Group by size, then metadata, then exact content, then link ownership.

    Metadata is part of the grouping key, not a post-hoc filter: two files with
    equal bytes and materially different modes or ownership are not
    interchangeable hardlink aliases and must never end up in one group.
    """

    by_key: dict[tuple[int, tuple[Any, ...]], list[DedupCandidate]] = {}
    by_size: dict[int, list[DedupCandidate]] = {}
    for item in candidates:
        by_size.setdefault(item.size_bytes, []).append(item)
    for size, group in by_size.items():
        if len(group) < 2:
            continue
        if len({item.metadata for item in group}) > 1:
            excluded.append(
                f"{size}-byte candidates differ in owner-required filesystem metadata; "
                "equal bytes alone never authorize a shared inode"
            )
        for item in group:
            by_key.setdefault((size, item.metadata), []).append(item)

    groups: list[dict[str, Any]] = []
    for (size, metadata), group in sorted(by_key.items(), key=lambda kv: -kv[0][0]):
        if len(group) < 2:
            continue
        # An applied run may reuse the campaign's receipt cache for these
        # owner-declared immutable files; a dry-run may not, because writing a
        # receipt would make an observational command change managed state. The
        # pre-link re-authentication below is always a fresh byte hash either
        # way, so a stale receipt can only cost work, never link two files that
        # are not byte-identical.
        digests = parallel_digests(
            [item.path for item in group], workers=io_workers, accelerated=accelerated
        )
        by_hash: dict[str, list[DedupCandidate]] = {}
        for item in group:
            by_hash.setdefault(digests[os.fspath(item.path)], []).append(item)
        for digest, members in sorted(by_hash.items()):
            inodes = {(item.device, item.inode) for item in members}
            if len(members) < 2 or len(inodes) < 2:
                continue
            canonical, why = _choose_canonical(members)
            if canonical is None:
                excluded.append(f"{digest[:12]}...: {why}")
                continue
            groups.append(
                {
                    "sha256": digest,
                    "size_bytes": int(size),
                    "metadata_signature": list(metadata),
                    "canonical": str(canonical.path),
                    "canonical_artifact_id": canonical.artifact_id,
                    "canonical_owner_state_identity": canonical.owner_state_identity,
                    "paths": sorted(str(item.path) for item in members),
                    "replacements": sorted(
                        str(item.path)
                        for item in members
                        if (item.device, item.inode) != (canonical.device, canonical.inode)
                    ),
                    "member_bindings": {
                        str(item.path): {
                            "artifact_id": item.artifact_id,
                            "owner_state_identity": item.owner_state_identity,
                        }
                        for item in members
                    },
                    "unique_inode_count_before": len(inodes),
                    "reclaimable_bytes": int(size) * (len(inodes) - 1),
                }
            )
    groups.sort(key=lambda item: (-int(item["reclaimable_bytes"]), item["sha256"]))
    return groups


def _choose_canonical(
    members: Sequence[DedupCandidate],
) -> tuple[DedupCandidate | None, str]:
    """Pick the shared inode, or refuse the group.

    The canonical inode must have *closed link ownership*: either exactly one
    link, or links that are all accounted for by members of this very group. An
    inode with unknown pre-existing links is never chosen, because whoever holds
    an unknown link could later mutate every path newly aliased to it.
    """

    by_inode: dict[tuple[int, int], list[DedupCandidate]] = {}
    for item in members:
        by_inode.setdefault((item.device, item.inode), []).append(item)
    for item in sorted(members, key=lambda value: str(value.path)):
        known = len(by_inode[(item.device, item.inode)])
        if item.link_count <= known:
            return item, ""
    return None, (
        "no candidate has closed link ownership: every inode carries pre-existing "
        "links this group does not account for, so an external writer could reach "
        "the shared bytes"
    )


#: Failpoint identity for the directory-entry durability boundary, so an
#: acceptance test can prove that an interruption there is never audited as a
#: completed action.
BOUNDARY_BEFORE_DIRECTORY_DURABILITY = "dedup.before_directory_durability"


def build_dedup_plan(
    snapshot: StorageInventorySnapshot, policy: StoragePolicy
) -> tuple[list[PlannedAction], list[dict[str, Any]], list[str]]:
    """The exact immutable dedup intention: one action per replaced alias."""

    if policy.dedup_realization == DEDUP_DISABLED:
        return [], [], ["dedup realization is disabled by policy"]
    candidates, excluded = collect_dedup_candidates(snapshot, policy)
    groups = plan_dedup_groups(
        candidates,
        excluded,
        io_workers=policy.io_worker_limit,
        accelerated=bool(policy.apply),
    )
    actions: list[PlannedAction] = []
    for group in groups:
        canonical = Path(str(group["canonical"]))
        for replacement in group["replacements"]:
            member = Path(replacement)
            bindings = group["member_bindings"][replacement]
            actions.append(
                planned_action(
                    action=ACTION_DEDUP_LINK,
                    path=member,
                    artifact_id=str(bindings["artifact_id"]),
                    reason=(
                        f"exact duplicate of {canonical}; becomes a hardlink alias of "
                        "the same owner-certified immutable inode"
                    ),
                    capability_cost="representation_only",
                    owner_state_identity=str(bindings["owner_state_identity"]),
                    binding={
                        "canonical": str(canonical),
                        "sha256": str(group["sha256"]),
                        "size_bytes": int(group["size_bytes"]),
                        "metadata_signature": list(group["metadata_signature"]),
                        "canonical_artifact_id": str(group["canonical_artifact_id"]),
                        "canonical_owner_state_identity": str(
                            group["canonical_owner_state_identity"]
                        ),
                    },
                    # The canonical source is never written, but its inode
                    # becomes the bytes behind this name. A dedup group can span
                    # two historical P5 runs, and generation supersession is not
                    # a no-writer proof, so the source's owner is fenced by the
                    # same seams as the destination.
                    synchronization_paths=(canonical,),
                    synchronization_artifact_ids=(
                        str(group["canonical_artifact_id"]),
                    ),
                )
            )
    return actions, groups, excluded


def dedup_engine(
    *,
    boundary: Any,
    control_plane: Any,
    groups: Sequence[Mapping[str, Any]],
    excluded: Sequence[str],
    failpoint: Callable[[str], None] = lambda _name: None,
):
    """Build the engine that applies an already-authorized dedup plan.

    Every replacement is re-authorized and re-authenticated *inside* the
    executor's synchronization, against the fresh snapshot the executor just
    revalidated - never against the snapshot that produced the plan.
    """

    def _engine(
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        from .executor import operation_identity

        notes = list(excluded)
        # The pre-rename hardlink lives in storage's own staging area, keyed by
        # this operation's identity, and never inside the P5 run. A hard crash
        # between `link` and `replace` therefore leaves *storage-owned* residue
        # that the existing abandoned-staging lifecycle can retire, instead of an
        # unrecorded descendant that would permanently make the run uncertifiable
        # and block the very reclamation that has to finish.
        staging = control_plane.staging_root_for(operation_identity(plan)) / "dedup"
        staging.mkdir(parents=True, exist_ok=True)
        for action in plan.actions:
            member = action.path
            canonical = Path(str(action.binding["canonical"]))
            digest = str(action.binding["sha256"])
            size = int(action.binding["size_bytes"])
            expected_metadata = tuple(action.binding["metadata_signature"])

            protected, why = snapshot.path_protection(member)
            if protected:
                result.refused.append({**action.to_dict(), "refusal": why})
                continue
            authorized, detail = boundary.destructive_authorization(member)
            if not authorized:
                result.refused.append({**action.to_dict(), "refusal": detail})
                continue
            canonical_artifact_id = str(
                action.binding.get("canonical_artifact_id", "")
            )
            canonical_view = (
                snapshot.view(canonical_artifact_id) if canonical_artifact_id else None
            )
            if canonical_artifact_id and canonical_view is None:
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            f"the canonical source owner {canonical_artifact_id} no "
                            "longer reports this artifact; duplicates are retained"
                        ),
                    }
                )
                continue
            if canonical_view is not None and canonical_view.state_identity != str(
                action.binding.get("canonical_owner_state_identity", "")
            ):
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            "the canonical source owner advanced between planning and "
                            "apply; duplicates are retained rather than relinked"
                        ),
                    }
                )
                continue
            if canonical_view is not None and not canonical_view.dedup_eligible:
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            "the canonical source owner no longer certifies this "
                            "artifact as immutable and dedup-eligible"
                        ),
                    }
                )
                continue
            canonical_protected, canonical_why = snapshot.path_protection(canonical)
            if canonical_protected:
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": f"canonical source is protected: {canonical_why}",
                    }
                )
                continue
            if not canonical.is_file() or canonical.is_symlink():
                result.refused.append(
                    {**action.to_dict(), "refusal": "canonical source is not a plain file"}
                )
                continue

            canonical_stats = canonical.stat()
            member_stats = member.stat()
            if (int(member_stats.st_dev), int(member_stats.st_ino)) == (
                int(canonical_stats.st_dev),
                int(canonical_stats.st_ino),
            ):
                # Already the same inode: dedup is idempotent.
                result.completed.append({**action.to_dict(), "already_aliased": True})
                continue
            if not same_filesystem(member, canonical):
                notes.append(f"cross-device duplicate not deduplicated: {member}")
                result.refused.append(
                    {**action.to_dict(), "refusal": "cross-device hardlink is unsupported"}
                )
                continue
            known_links = 1 + sum(
                1
                for other in plan.actions
                if str(other.binding.get("canonical")) == str(canonical)
                and Path(other.path).exists()
                and Path(other.path).stat().st_ino == int(canonical_stats.st_ino)
            )
            if int(canonical_stats.st_nlink) > known_links:
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            "canonical inode gained pre-existing links this group does "
                            "not account for; an external writer could reach the bytes"
                        ),
                    }
                )
                continue
            if (
                _metadata_signature(member) != expected_metadata
                or _metadata_signature(canonical) != expected_metadata
            ):
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            "filesystem metadata diverged from the plan; a shared inode "
                            "would change owner-required metadata"
                        ),
                    }
                )
                continue
            if (
                int(member_stats.st_size) != size
                or sha256_file(member, limit_bytes=size) != digest
                or int(canonical_stats.st_size) != size
                or sha256_file(canonical, limit_bytes=size) != digest
            ):
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": "content changed between planning and apply",
                    }
                )
                continue

            # The action is complete only once the *directory entry* is durable.
            # An audit that claimed completion before the rename reached the
            # filesystem publication boundary could survive a power loss that
            # the rename did not, leaving durable evidence disagreeing with the
            # recovered tree.
            from ..target_size_execution.persistence import fsync_parent_directory

            if not same_filesystem(staging, member):
                # An atomic hardlink replacement needs one filesystem. Falling
                # back to a copy, or to an unowned temporary inside the run,
                # would trade a refusal for a recovery hole.
                notes.append(
                    f"dedup staging is on a different filesystem than {member}"
                )
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            "storage staging and this member are on different "
                            "filesystems, so an atomic hardlink replacement is "
                            "unavailable; the duplicate is retained"
                        ),
                    }
                )
                continue
            temporary = staging / f"{len(result.completed)}-{member.name}"
            temporary.unlink(missing_ok=True)
            os.link(canonical, temporary)
            try:
                os.replace(temporary, member)
                # The alias is already replaced. Whatever happens next, this
                # execution has changed the namespace, and the executor settles
                # an interruption from what was recorded - so it is recorded
                # here rather than inferred later from a completed-action list
                # this member has not reached yet.
                result.mutated = True
                failpoint(BOUNDARY_BEFORE_DIRECTORY_DURABILITY)
                fsync_parent_directory(member)
            except BaseException:
                # Deterministic cleanup of this operation's own staged link
                # only; the canonical and every other alias are untouched. A
                # crash that skips this leaves the same name as storage-owned
                # abandoned staging rather than an unknown P5 descendant.
                temporary.unlink(missing_ok=True)
                raise
            result.completed.append({**action.to_dict(), "aliased_to": str(canonical)})
            result.reclaimed_bytes += size

        control_plane.clear_staging(operation_identity(plan))
        result.payload = DedupResult(
            applied=True,
            groups=list(groups),
            links_replaced=len(
                [item for item in result.completed if item.get("aliased_to")]
            ),
            reclaimed_bytes=result.reclaimed_bytes,
            excluded=notes,
            realization="direct-owner-certified-hardlink-alias",
        ).to_dict()

    return _engine


__all__ = [
    "DEDUPLICATION_REPORT_SCHEMA",
    "DedupCandidate",
    "DedupResult",
    "StorageDedupError",
    "build_dedup_plan",
    "collect_dedup_candidates",
    "dedup_engine",
    "plan_dedup_groups",
    "same_filesystem",
]
