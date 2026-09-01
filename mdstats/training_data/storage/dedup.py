"""Owner-certified immutable deduplication.

Deduplication is representation optimization only.  Exact byte equality is
necessary but never sufficient: hardlinked names share one inode's type, mode,
ownership, and extended metadata, and any later in-place mutation through one
alias is visible through all of them.  Eligibility is therefore

``owner-certified immutability + exact content identity + owner-certified
metadata compatibility + filesystem realization support + race-safe
replacement``

and anything ambiguous keeps its duplicate bytes.  A cross-device or otherwise
unsupported filesystem falls back to retaining duplicates without a correctness
failure.

Dedup changes inode and ctime, which invalidates stat-keyed acceleration
receipts.  That is a cache miss and a revalidation, never a scientific state
change.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .control_plane import StorageControlPlane
from .durability import parallel_digests, sha256_file
from .inventory import StorageInventorySnapshot
from .lease import owner_mutation_barrier, storage_operation_lease
from .policy import DEDUP_DISABLED, StoragePolicy

DEDUPLICATION_REPORT_SCHEMA = "mdstats.mlff-storage-deduplication.v2"

class StorageDedupError(RuntimeError):
    """A deduplication candidate failed an eligibility or safety contract."""


@dataclass(frozen=True, slots=True)
class DedupCandidate:
    path: Path
    artifact_id: str
    size_bytes: int
    sha256: str
    metadata: tuple[Any, ...]
    device: int
    inode: int


@dataclass
class DedupResult:
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


def collect_dedup_candidates(
    snapshot: StorageInventorySnapshot, policy: StoragePolicy
) -> tuple[tuple[DedupCandidate, ...], list[str]]:
    """Every file whose owner certified immutability *and* a metadata contract.

    Only owner views that positively declare ``dedup_eligible`` contribute.
    Mutable SQLite state, active attempt scratch, and any owner-ambiguous file
    never reach this list, because no owner declares them eligible.
    """

    excluded: list[str] = []
    candidates: list[DedupCandidate] = []
    for view in snapshot.views:
        if not view.dedup_eligible:
            continue
        if not view.immutable:
            excluded.append(
                f"{view.artifact_id}: owner did not certify immutability"
            )
            continue
        if view.metadata_contract not in ("mode_only", "mode_and_ownership"):
            excluded.append(
                f"{view.artifact_id}: owner requires filesystem metadata this "
                f"realization cannot guarantee ({view.metadata_contract})"
            )
            continue
        for path in _iter_files(view.path):
            protected, why = snapshot.path_protection(path)
            if protected:
                excluded.append(f"{path}: {why}")
                continue
            stats = path.lstat()
            if not stat.S_ISREG(stats.st_mode):
                continue
            if int(stats.st_size) < int(policy.dedup_minimum_file_bytes):
                continue
            candidates.append(
                DedupCandidate(
                    path=path,
                    artifact_id=view.artifact_id,
                    size_bytes=int(stats.st_size),
                    sha256="",
                    metadata=_metadata_signature(path),
                    device=int(stats.st_dev),
                    inode=int(stats.st_ino),
                )
            )
    return tuple(candidates), excluded


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_symlink():
        return ()
    if root.is_file():
        return (root,)
    if not root.is_dir():
        return ()
    return (path for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink())


def plan_dedup_groups(
    candidates: Sequence[DedupCandidate], excluded: list[str], *, io_workers: int = 1
) -> list[dict[str, Any]]:
    """Group by size, then metadata, then exact content.

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
        metadata_variants = {item.metadata for item in group}
        if len(metadata_variants) > 1:
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
        # Grouping uses the receipt-accelerated hash for these owner-declared
        # immutable files.  The pre-link re-authentication below is always a
        # fresh byte hash, so a stale receipt can only cost work, never link
        # two files that are not byte-identical.
        digests = parallel_digests(
            [item.path for item in group], workers=io_workers, accelerated=True
        )
        by_hash: dict[str, list[DedupCandidate]] = {}
        for item in group:
            by_hash.setdefault(digests[os.fspath(item.path)], []).append(item)
        for digest, members in sorted(by_hash.items()):
            inodes = {(item.device, item.inode) for item in members}
            if len(members) < 2 or len(inodes) < 2:
                continue
            groups.append(
                {
                    "sha256": digest,
                    "size_bytes": int(size),
                    "metadata_signature": list(metadata),
                    "paths": sorted(str(item.path) for item in members),
                    "unique_inode_count_before": len(inodes),
                    "reclaimable_bytes": int(size) * (len(inodes) - 1),
                }
            )
    groups.sort(key=lambda item: (-int(item["reclaimable_bytes"]), item["sha256"]))
    return groups


def deduplicate(
    *,
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
    control_plane: StorageControlPlane,
    boundary: Any,
    paths: Any,
    generations: Sequence[int] = (),
) -> DedupResult:
    """Plan, and when authorized apply, owner-certified hardlink dedup.

    Replacement is race-safe (it runs under the owning publication barriers and
    the storage lease) and idempotent: an interruption can never leave a
    temporary path accepted as canonical, because the replacement is a single
    ``rename`` of a fully linked temporary onto the member name.
    """

    if policy.dedup_realization == DEDUP_DISABLED:
        return DedupResult(applied=False, realization=DEDUP_DISABLED)
    candidates, excluded = collect_dedup_candidates(snapshot, policy)
    groups = plan_dedup_groups(candidates, excluded, io_workers=policy.io_worker_limit)
    result = DedupResult(
        applied=bool(policy.apply),
        groups=groups,
        excluded=excluded,
        realization=policy.dedup_realization,
    )
    if not policy.apply or not groups:
        return result

    content_store = control_plane.root / "content-store"
    authorized, detail = boundary.destructive_authorization(content_store)
    if not authorized:
        raise StorageDedupError(f"content store is not campaign-owned: {detail}")

    with storage_operation_lease(
        control_plane, timeout_seconds=policy.operation_lease_timeout_seconds
    ):
        with owner_mutation_barrier(paths, tuple(generations)):
            for group in groups:
                _apply_group(group, content_store, snapshot, boundary, result)
    return result


def _apply_group(
    group: Mapping[str, Any],
    content_store: Path,
    snapshot: StorageInventorySnapshot,
    boundary: Any,
    result: DedupResult,
) -> None:
    digest = str(group["sha256"])
    size = int(group["size_bytes"])
    members = [Path(value) for value in group["paths"]]
    object_path = content_store / "sha256" / digest[:2] / digest
    object_path.parent.mkdir(parents=True, exist_ok=True)

    if object_path.exists():
        if (
            not object_path.is_file()
            or int(object_path.stat().st_size) != size
            or sha256_file(object_path, limit_bytes=size) != digest
        ):
            raise StorageDedupError(
                f"content-addressed object collision or corruption at {object_path}"
            )
    else:
        source = members[0]
        if not same_filesystem(source, object_path.parent):
            result.excluded.append(
                f"cross-device content object not deduplicated: {source}"
            )
            return
        temporary = object_path.parent / f".{digest}.tmp-{os.getpid()}"
        temporary.unlink(missing_ok=True)
        os.link(source, temporary)
        os.replace(temporary, object_path)

    object_stat = object_path.stat()
    object_metadata = _metadata_signature(object_path)
    for member in members:
        # Re-authorize and re-authenticate immediately before the replacement:
        # the plan is not the authorization, the fresh check under the barrier is.
        protected, why = snapshot.path_protection(member)
        if protected:
            result.excluded.append(f"{member}: {why}")
            continue
        authorized, detail = boundary.destructive_authorization(member)
        if not authorized:
            result.excluded.append(f"{member}: {detail}")
            continue
        stats = member.stat()
        if (int(stats.st_dev), int(stats.st_ino)) == (
            int(object_stat.st_dev),
            int(object_stat.st_ino),
        ):
            continue
        if not same_filesystem(member, object_path):
            result.excluded.append(f"cross-device duplicate not deduplicated: {member}")
            continue
        if _metadata_signature(member) != object_metadata:
            result.excluded.append(
                f"{member}: filesystem metadata diverged from the content object; "
                "a shared inode would change owner-required metadata"
            )
            continue
        if int(stats.st_size) != size or sha256_file(member, limit_bytes=size) != digest:
            raise StorageDedupError(
                f"deduplication source changed during the operation: {member}"
            )
        temporary = member.parent / f".{member.name}.dedup-{os.getpid()}"
        temporary.unlink(missing_ok=True)
        os.link(object_path, temporary)
        os.replace(temporary, member)
        result.links_replaced += 1
        result.reclaimed_bytes += size


def prune_orphan_content_objects(
    control_plane: StorageControlPlane, *, boundary: Any
) -> dict[str, int]:
    """Remove content objects whose only remaining link is the object itself."""

    content_store = control_plane.root / "content-store"
    if not content_store.exists():
        return {"objects_removed": 0, "bytes_released": 0}
    authorized, detail = boundary.traversal_authorization(content_store)
    if not authorized:
        raise StorageDedupError(f"content-store traversal is not campaign-owned: {detail}")
    removed = 0
    released = 0
    for path in sorted(content_store.rglob("*"), reverse=True):
        if path.is_symlink():
            continue
        if path.is_file():
            granted, _ = boundary.destructive_authorization(path)
            if not granted:
                continue
            stats = path.stat()
            if int(stats.st_nlink) <= 1:
                released += int(stats.st_size)
                path.unlink()
                removed += 1
        elif path.is_dir():
            try:
                path.rmdir()
            except OSError:
                pass
    return {"objects_removed": removed, "bytes_released": released}


__all__ = [
    "DEDUPLICATION_REPORT_SCHEMA",
    "DedupCandidate",
    "DedupResult",
    "StorageDedupError",
    "collect_dedup_candidates",
    "deduplicate",
    "plan_dedup_groups",
    "prune_orphan_content_objects",
    "same_filesystem",
]
