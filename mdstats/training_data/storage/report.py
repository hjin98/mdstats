"""Owner-driven storage reporting: bounded normal report, explicit deep audit.

Two reports with two different jobs, and the difference is a scaling property,
not a formatting preference.

*Normal report* answers ownership questions. Its cost is bounded independently
of how much bulk a campaign holds: owner semantics come from compact pointers,
manifests, and state the owners already maintain, and physical size comes from a
single ``stat`` on each owner root. It never walks a subtree, so it never
promises exact recursive totals - it labels what it knows as known, what it
sampled as an estimate, and what it did not measure as unknown.

*Deep audit* answers physical questions. It walks the workspace exactly once,
inode-deduplicated, under an explicit entry bound. If the bound is reached it
says so rather than presenting a truncated walk as a complete accounting.

Both are read-only and neither grants mutation authority. A family label in a
report is advisory: the executor consults owner views and the ownership
boundary, never a report.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..storage_accounting import ProtectedInputPath, configured_protected_inputs  # noqa: F401
from .inventory import (
    StorageInventorySnapshot,
    archive_candidates,
    cache_candidates,
    safe_candidates,
)
from .policy import StoragePolicy
from .trust import walk_contained

STORAGE_OWNER_REPORT_SCHEMA = "mdstats.mlff-storage-owner-report.v2"
STORAGE_DEEP_AUDIT_SCHEMA = "mdstats.mlff-storage-deep-audit.v2"

#: What a reported size actually means.
SIZE_KNOWN = "known"
SIZE_UNKNOWN = "unknown_without_deep_audit"


@dataclass(frozen=True, slots=True)
class OwnerFamilyTotals:
    owner: str
    artifact_class: str
    artifact_count: int
    measured_bytes: int
    measured_artifact_count: int
    unmeasured_artifact_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "artifact_class": self.artifact_class,
            "artifact_count": int(self.artifact_count),
            "measured_bytes": int(self.measured_bytes),
            "measured_artifact_count": int(self.measured_artifact_count),
            "unmeasured_artifact_count": int(self.unmeasured_artifact_count),
            "bytes_are_exact_totals": False,
        }


def _bounded_metadata(path: Path) -> dict[str, Any]:
    """One ``stat`` on an owner root: never a subtree walk.

    A file reports its exact size. A directory reports that its size is unknown
    without a deep audit, because finding out would cost a recursive traversal
    and that is precisely what normal reporting must not do.
    """

    try:
        stats = path.lstat()
    except OSError:
        return {"exists": False, "kind": "absent", "size_scope": SIZE_UNKNOWN, "bytes": None}
    import stat as stat_module

    if stat_module.S_ISDIR(stats.st_mode):
        return {
            "exists": True,
            "kind": "directory",
            "size_scope": SIZE_UNKNOWN,
            "bytes": None,
        }
    kind = "symlink" if stat_module.S_ISLNK(stats.st_mode) else "file"
    return {
        "exists": True,
        "kind": kind,
        "size_scope": SIZE_KNOWN,
        "bytes": int(stats.st_size),
    }


def build_owner_storage_report(
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
    *,
    top: int = 20,
) -> dict[str, Any]:
    """The normal read-only report: owner semantics plus bounded metadata."""

    # One path can legitimately carry several semantic views - the campaign
    # state database is simultaneously CampaignStore authority, the P2
    # statistical authorities, and the P4 selected authority. Those are
    # different *meanings* of the same bytes, not three separate consumptions of
    # storage, so each row says explicitly whether its bytes are attributed to it
    # alone. Family subtotals must not be added together into a global figure,
    # and this report deliberately publishes none.
    claims: dict[str, list[str]] = {}
    for view in snapshot.views:
        claims.setdefault(str(view.path), []).append(view.artifact_id)

    totals: dict[tuple[str, str], list[int]] = {}
    rows: list[dict[str, Any]] = []
    for view in snapshot.views:
        metadata = _bounded_metadata(view.path)
        measured = metadata["bytes"] is not None
        key = (view.owner, view.artifact_class.value)
        bucket = totals.setdefault(key, [0, 0, 0, 0])
        bucket[0] += 1
        bucket[1] += int(metadata["bytes"] or 0)
        bucket[2] += 1 if measured else 0
        bucket[3] += 0 if measured else 1
        protected, why = snapshot.path_protection(view.path)
        sharing = [
            item for item in claims[str(view.path)] if item != view.artifact_id
        ]
        rows.append(
            {
                **view.to_dict(),
                "physical": metadata,
                "protected": protected,
                "protection_reason": why,
                "logical_attribution": (
                    "shared_with_other_owner_views" if sharing else "exclusive"
                ),
                "shares_path_with": sorted(sharing),
            }
        )
    rows.sort(
        key=lambda item: (
            -(item["physical"]["bytes"] or 0),
            str(item["artifact_id"]),
        )
    )
    families = tuple(
        OwnerFamilyTotals(owner, artifact_class, *value)
        for (owner, artifact_class), value in sorted(
            totals.items(), key=lambda item: (-item[1][1], item[0])
        )
    )
    return {
        "schema": STORAGE_OWNER_REPORT_SCHEMA,
        "read_only_gate": "advisory_read_only",
        "destructive_actions_performed": False,
        "grants_mutation_authority": False,
        "accounting_mode": "bounded_owner_metadata",
        "exact_physical_totals_available": False,
        "exact_physical_totals_hint": "run `storage report --deep` for exact accounting",
        "family_totals_are_additive": False,
        "family_totals_note": (
            "owner family subtotals are per-view logical attributions and overlap "
            "wherever one path carries several semantic views; adding them would "
            "double-count the same inode. `storage report --deep` is the "
            "inode-deduplicated physical accounting."
        ),
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
        "owner_graph_integrity_failures": list(snapshot.integrity_failures),
        "consequential_planning_available": not snapshot.integrity_failures,
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
    entry_limit: int = 200_000,
) -> dict[str, Any]:
    """Exact recursive physical accounting, explicitly requested and bounded.

    The traversal refuses to cross a nested mount, deduplicates inodes so shared
    bytes are not double counted, and stops at ``entry_limit``. A truncated walk
    is reported as incomplete; it is never labeled exact.
    """

    from ..storage_accounting import CampaignOwnershipBoundary

    workspace = Path(os.path.abspath(os.fspath(workspace)))
    boundary = CampaignOwnershipBoundary(workspace, protected_inputs=protected_inputs)
    seen: set[tuple[int, int]] = set()
    refused: list[dict[str, str]] = []
    families: dict[str, dict[str, int]] = {}
    largest: list[tuple[int, str, str]] = []
    logical = allocated = unique = 0
    files = directories = symlinks = 0
    visited = 0
    complete = True

    if workspace.is_dir():
        for path in walk_contained(
            workspace,
            on_refused=lambda item, why: refused.append({"path": str(item), "reason": why}),
        ):
            visited += 1
            if visited > int(entry_limit):
                complete = False
                break
            try:
                stats = path.lstat()
            except OSError:
                continue
            import stat as stat_module

            family = _family_of(path, workspace)
            bucket = families.setdefault(
                family, {"logical_bytes": 0, "unique_inode_bytes": 0, "entries": 0}
            )
            bucket["entries"] += 1
            if stat_module.S_ISDIR(stats.st_mode):
                directories += 1
                continue
            if stat_module.S_ISLNK(stats.st_mode):
                symlinks += 1
                continue
            files += 1
            size = int(stats.st_size)
            logical += size
            bucket["logical_bytes"] += size
            key = (int(stats.st_dev), int(stats.st_ino))
            if key in seen:
                continue
            seen.add(key)
            unique += size
            bucket["unique_inode_bytes"] += size
            blocks = getattr(stats, "st_blocks", None)
            allocated += size if blocks is None else int(blocks) * 512
            largest.append((size, str(path), family))

    largest.sort(key=lambda item: (-item[0], item[1]))
    return {
        "schema": STORAGE_DEEP_AUDIT_SCHEMA,
        "read_only_gate": "advisory_read_only",
        "destructive_actions_performed": False,
        "grants_mutation_authority": False,
        "accounting_mode": "exact_recursive_physical" if complete else "bounded_incomplete",
        "complete": complete,
        "entry_limit": int(entry_limit),
        "entries_visited": visited,
        "workspace": str(workspace),
        "workspace_real_path": str(boundary.workspace_real),
        "totals": {
            "logical_bytes": logical,
            "allocated_physical_bytes": allocated,
            "unique_inode_bytes": unique,
            "file_count": files,
            "directory_count": directories,
            "symlink_count": symlinks,
        },
        "families": [
            {"family": name, **values}
            for name, values in sorted(
                families.items(), key=lambda item: -item[1]["logical_bytes"]
            )
        ],
        "largest_artifacts": [
            {"logical_bytes": size, "path": path, "family": family}
            for size, path, family in largest[: max(0, int(top))]
        ],
        "refused_paths": refused,
        "protected_inputs": [item.to_dict() for item in protected_inputs],
    }


def _family_of(path: Path, workspace: Path) -> str:
    """Advisory physical family label. It grants nothing."""

    try:
        relative = path.relative_to(workspace)
    except ValueError:
        return "outside_workspace"
    parts = relative.parts
    if not parts:
        return "workspace_root"
    if parts[0] != ".mdstats":
        return parts[0]
    return ".mdstats/" + (parts[1] if len(parts) > 1 else "")


def _reclaimable(decisions: Sequence[Any]) -> dict[str, Any]:
    eligible = [item for item in decisions if item.eligible]
    measured = 0
    unknown = 0
    for item in eligible:
        metadata = _bounded_metadata(item.path)
        if metadata["bytes"] is None:
            unknown += 1
        else:
            measured += int(metadata["bytes"])
    return {
        "eligible_count": len(eligible),
        "measured_eligible_bytes": measured,
        "unmeasured_eligible_count": unknown,
        "refused_count": len(decisions) - len(eligible),
        "bytes_are_exact_totals": False,
    }


__all__ = [
    "SIZE_KNOWN",
    "SIZE_UNKNOWN",
    "STORAGE_DEEP_AUDIT_SCHEMA",
    "STORAGE_OWNER_REPORT_SCHEMA",
    "OwnerFamilyTotals",
    "build_deep_storage_audit",
    "build_owner_storage_report",
]
