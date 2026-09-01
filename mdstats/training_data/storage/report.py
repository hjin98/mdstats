"""Owner-driven storage reporting: fast semantics, explicit deep physical audit.

Normal report consumes owner views for meaning and bounded physical metadata
for size, so it never has to restat a whole campaign to say something true
about ownership.  The explicit deep audit performs exact recursive physical
accounting, symlink and ownership inspection, and debugging detail.

Both are read-only and neither grants mutation authority.  A family label in a
report is advisory: the executor consults owner views and the ownership
boundary, never a report.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..storage_accounting import (
    CampaignStorageReport,
    ProtectedInputPath,
    build_campaign_storage_report,
)
from .inventory import (
    StorageInventorySnapshot,
    archive_candidates,
    cache_candidates,
    safe_candidates,
)
from .policy import StoragePolicy

STORAGE_OWNER_REPORT_SCHEMA = "mdstats.mlff-storage-owner-report.v1"
STORAGE_DEEP_AUDIT_SCHEMA = "mdstats.mlff-storage-deep-audit.v1"


@dataclass(frozen=True, slots=True)
class OwnerFamilyTotals:
    owner: str
    artifact_class: str
    logical_bytes: int
    allocated_physical_bytes: int
    unique_inode_bytes: int
    file_count: int
    directory_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "artifact_class": self.artifact_class,
            "logical_bytes": int(self.logical_bytes),
            "allocated_physical_bytes": int(self.allocated_physical_bytes),
            "unique_inode_bytes": int(self.unique_inode_bytes),
            "file_count": int(self.file_count),
            "directory_count": int(self.directory_count),
        }


def build_owner_storage_report(
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
    *,
    top: int = 20,
) -> dict[str, Any]:
    """The normal read-only report: owner semantics plus bounded physical size."""

    totals: dict[tuple[str, str], list[int]] = {}
    rows: list[dict[str, Any]] = []
    for view in snapshot.views:
        measured = _bounded_size(view.path)
        key = (view.owner, view.artifact_class.value)
        bucket = totals.setdefault(key, [0, 0, 0, 0, 0])
        for index, value in enumerate(measured):
            bucket[index] += value
        protected, why = snapshot.path_protection(view.path)
        rows.append(
            {
                **view.to_dict(),
                "logical_bytes": measured[0],
                "allocated_physical_bytes": measured[1],
                "unique_inode_bytes": measured[2],
                "file_count": measured[3],
                "directory_count": measured[4],
                "protected": protected,
                "protection_reason": why,
            }
        )
    rows.sort(key=lambda item: (-int(item["logical_bytes"]), str(item["artifact_id"])))
    families = tuple(
        OwnerFamilyTotals(owner, artifact_class, *value)
        for (owner, artifact_class), value in sorted(
            totals.items(), key=lambda item: -item[1][0]
        )
    )
    return {
        "schema": STORAGE_OWNER_REPORT_SCHEMA,
        "read_only_gate": "advisory_read_only",
        "destructive_actions_performed": False,
        "grants_mutation_authority": False,
        "workspace": str(snapshot.workspace),
        "current_generation": snapshot.current_generation,
        "policy": policy.to_dict(),
        "resolved_policy_summary": policy.describe(),
        "owner_families": [item.to_dict() for item in families],
        "artifacts": rows[: max(0, int(top))],
        "unresolved_owners": [
            {"owner": owner, "detail": detail}
            for owner, detail in snapshot.owner_views.unresolved
        ],
        "protected_inputs": [item.to_dict() for item in snapshot.protected_inputs],
        "potential_reclaim_by_action": {
            "safe": _reclaimable(safe_candidates(snapshot)),
            "cache": _reclaimable(cache_candidates(snapshot)),
            "archive": _reclaimable(archive_candidates(snapshot)),
        },
        "receipt_cache_is_separate_from_campaign_state": True,
    }


def build_deep_storage_audit(
    workspace: Path,
    *,
    protected_inputs: Sequence[ProtectedInputPath] = (),
    top: int = 25,
) -> dict[str, Any]:
    """Exact recursive physical accounting, explicitly requested.

    This reuses the accepted physical accounting owner rather than duplicating
    a second traversal implementation.  It is a debugging and capacity tool: it
    still grants no deletion authority.
    """

    report: CampaignStorageReport = build_campaign_storage_report(
        workspace, protected_inputs=protected_inputs, largest_limit=int(top)
    )
    payload = report.to_dict()
    payload["schema"] = STORAGE_DEEP_AUDIT_SCHEMA
    payload["grants_mutation_authority"] = False
    payload["accounting_mode"] = "exact_recursive_physical"
    return payload


def _reclaimable(decisions: Sequence[Any]) -> dict[str, Any]:
    eligible = [item for item in decisions if item.eligible]
    return {
        "eligible_count": len(eligible),
        "eligible_bytes": sum(_bounded_size(item.path)[0] for item in eligible),
        "refused_count": len(decisions) - len(eligible),
    }


def _bounded_size(path: Path) -> tuple[int, int, int, int, int]:
    """``(logical, allocated, unique_inode, files, directories)`` for one artifact.

    Symlinks are never followed.  A single ``stat`` answers for a file; a
    directory is walked once with ``scandir`` and inode-deduplicated, bounded by
    the subtree the owner actually claims rather than by the whole workspace.
    """

    if not path.exists() and not path.is_symlink():
        return 0, 0, 0, 0, 0
    if path.is_symlink() or path.is_file():
        try:
            stats = path.lstat()
        except OSError:
            return 0, 0, 0, 0, 0
        return int(stats.st_size), _allocated(stats), int(stats.st_size), 1, 0
    logical = 0
    allocated = 0
    unique = 0
    files = 0
    directories = 0
    seen: set[tuple[int, int]] = set()
    stack = [path]
    while stack:
        current = stack.pop()
        directories += 1
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                stats = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            if entry.is_dir(follow_symlinks=False):
                stack.append(Path(entry.path))
                continue
            key = (int(stats.st_dev), int(stats.st_ino))
            files += 1
            logical += int(stats.st_size)
            if key in seen:
                continue
            seen.add(key)
            unique += int(stats.st_size)
            allocated += _allocated(stats)
    return logical, allocated, unique, files, max(0, directories - 1)


def _allocated(stats: os.stat_result) -> int:
    blocks = getattr(stats, "st_blocks", None)
    return int(stats.st_size) if blocks is None else int(blocks) * 512


__all__ = [
    "STORAGE_DEEP_AUDIT_SCHEMA",
    "STORAGE_OWNER_REPORT_SCHEMA",
    "OwnerFamilyTotals",
    "build_deep_storage_audit",
    "build_owner_storage_report",
]
