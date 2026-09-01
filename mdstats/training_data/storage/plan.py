"""The immutable owner-bound storage plan.

A plan binds three things at inspection time: the exact owner identities the
decision depends on, the exact filesystem identities of the paths it will
touch, and the one resolved operational policy identity it was resolved under.
If any of them changes before apply, apply refuses and demands a re-plan; it
never silently substitutes a new candidate set.

A plan grants no scientific authority.  It is a record of what storage intends
to do to bytes it has already proven it may touch.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..storage_reclamation import filesystem_identity
from .admission import AdmissionObservation
from .durability import canonical_digest
from .inventory import StorageInventorySnapshot
from .policy import StoragePolicy

STORAGE_PLAN_SCHEMA = "mdstats.mlff-storage-plan.v1"

ACTION_REMOVE = "remove"
ACTION_EVICT_CACHE = "evict_cache"
ACTION_ARCHIVE_MEMBER = "archive_member"
ACTION_DEDUP_LINK = "dedup_link"
ACTION_RESTORE_MEMBER = "restore_member"


class StoragePlanStaleError(RuntimeError):
    """The world moved between planning and apply; the plan is refused."""


@dataclass(frozen=True, slots=True)
class PlannedAction:
    """One intended mutation, bound to the identity it was planned against."""

    action: str
    path: Path
    artifact_id: str
    reason: str
    size_bytes: int
    capability_cost: str
    filesystem_identity: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "path": str(self.path),
            "artifact_id": self.artifact_id,
            "reason": self.reason,
            "size_bytes": int(self.size_bytes),
            "capability_cost": self.capability_cost,
            "filesystem_identity": dict(self.filesystem_identity),
        }


@dataclass(frozen=True, slots=True)
class StoragePlan:
    """An immutable, owner-bound, policy-bound intention."""

    workspace: Path
    policy: StoragePolicy
    actions: tuple[PlannedAction, ...]
    refusals: tuple[Mapping[str, Any], ...]
    owner_binding: Mapping[str, Any]
    admission: AdmissionObservation | None
    created_utc: str

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_PLAN_SCHEMA,
            "workspace": str(self.workspace),
            "policy_identity": self.policy.policy_identity,
            "owner_binding": dict(self.owner_binding),
            "actions": [item.to_dict() for item in self.actions],
        }

    @property
    def plan_identity(self) -> str:
        """Content identity of the intention, excluding presentation detail.

        Refusal text, timing, and admission observations are deliberately
        outside the identity: re-running a plan on an unchanged campaign with a
        different amount of free disk produces the same intention.
        """

        return canonical_digest(self._payload())

    @property
    def planned_bytes(self) -> int:
        return sum(int(item.size_bytes) for item in self.actions)

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "plan_identity": self.plan_identity,
            "created_utc": self.created_utc,
            "policy": self.policy.to_dict(),
            "policy_summary": self.policy.describe(),
            "admission": None if self.admission is None else self.admission.to_dict(),
            "refusals": [dict(item) for item in self.refusals],
            "action_count": len(self.actions),
            "planned_bytes": self.planned_bytes,
            "grants_scientific_authority": False,
        }


def owner_binding_for(snapshot: StorageInventorySnapshot) -> dict[str, Any]:
    """The exact owner state a plan is bound to.

    Owner advancement - a newer generation, a new publication, a changed P3
    head closure, a new qualification pointer, a newly active attempt - changes
    this binding and therefore invalidates an unapplied plan.
    """

    return {
        "current_generation": snapshot.current_generation,
        "owner_identity_digest": canonical_digest(
            {
                "views": sorted(
                    {
                        view.artifact_id: [
                            view.artifact_class.value,
                            bool(view.current),
                            bool(view.restart_required),
                            bool(view.hot_path_required),
                            bool(view.safe_reclaimable),
                            bool(view.container_only),
                            bool(view.cache_reconstructible),
                            bool(view.cache_evictable),
                            bool(view.archive_eligible),
                            sorted(view.requires),
                        ]
                        for view in snapshot.views
                    }.items()
                ),
                "unresolved": sorted(snapshot.owner_views.unresolved),
            }
        ),
        "protection_closure_digest": canonical_digest(
            {"protected": sorted(snapshot.protected_ids)}
        ),
    }


def build_storage_plan(
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
    actions: Sequence[PlannedAction],
    *,
    refusals: Sequence[Mapping[str, Any]] = (),
    admission: AdmissionObservation | None = None,
    created_utc: str | None = None,
) -> StoragePlan:
    from datetime import datetime, timezone

    return StoragePlan(
        workspace=snapshot.workspace,
        policy=policy,
        actions=tuple(actions),
        refusals=tuple(dict(item) for item in refusals),
        owner_binding=owner_binding_for(snapshot),
        admission=admission,
        created_utc=created_utc
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def planned_action(
    *,
    action: str,
    path: str | os.PathLike[str],
    artifact_id: str,
    reason: str,
    capability_cost: str = "none",
) -> PlannedAction:
    """Bind one intended mutation to the filesystem identity it was planned on."""

    candidate = Path(os.path.abspath(os.fspath(path)))
    identity = filesystem_identity(candidate)
    size = int(identity.get("size_bytes", 0))
    if identity.get("kind") == "directory":
        size = _tree_bytes(candidate)
    return PlannedAction(
        action=action,
        path=candidate,
        artifact_id=artifact_id,
        reason=reason,
        size_bytes=size,
        capability_cost=capability_cost,
        filesystem_identity=identity,
    )


def revalidate_plan(
    plan: StoragePlan,
    snapshot: StorageInventorySnapshot,
    policy: StoragePolicy,
) -> None:
    """Refuse the plan unless owners, policy, and filesystem identity all hold.

    This is the *snapshot* half of mutation authorization.  It is necessary but
    never sufficient: the executor additionally holds the owning publication
    barrier across revalidation and mutation, because a naked check-then-unlink
    can still race a publication that starts immediately afterwards.
    """

    if policy.policy_identity != plan.policy.policy_identity:
        raise StoragePlanStaleError(
            "The resolved storage policy changed between planning and apply "
            f"({plan.policy.policy_identity[:12]}... -> "
            f"{policy.policy_identity[:12]}...); re-plan before applying. No "
            "scientific identity is affected by a storage policy change."
        )
    current = owner_binding_for(snapshot)
    if current["owner_identity_digest"] != plan.owner_binding.get("owner_identity_digest"):
        raise StoragePlanStaleError(
            "A semantic owner advanced between planning and apply; the plan is "
            "refused rather than silently retargeted at a new candidate set."
        )
    if current["protection_closure_digest"] != plan.owner_binding.get(
        "protection_closure_digest"
    ):
        raise StoragePlanStaleError(
            "The cross-owner protection closure changed between planning and apply; "
            "re-plan before applying."
        )
    for action in plan.actions:
        protected, why = snapshot.path_protection(action.path)
        if protected:
            raise StoragePlanStaleError(
                f"{action.path} became protected after planning: {why}"
            )
        if not action.path.exists() and not action.path.is_symlink():
            # A path that vanished is not an error for a removal, but it is for
            # anything that must operate on exact bytes.
            if action.action in (ACTION_REMOVE, ACTION_EVICT_CACHE):
                continue
            raise StoragePlanStaleError(
                f"{action.path} disappeared between planning and apply."
            )
        observed = filesystem_identity(action.path)
        for key in ("kind", "device", "inode", "size_bytes", "mtime_ns"):
            if observed.get(key) != action.filesystem_identity.get(key):
                raise StoragePlanStaleError(
                    f"{action.path} changed on disk after planning ({key} differs); "
                    "re-plan before applying."
                )


def _tree_bytes(root: Path) -> int:
    total = 0
    seen: set[tuple[int, int]] = set()
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = list(os.scandir(current))
        except OSError:
            continue
        for entry in entries:
            try:
                stats = entry.stat(follow_symlinks=False)
            except OSError:
                continue
            key = (int(stats.st_dev), int(stats.st_ino))
            if entry.is_dir(follow_symlinks=False):
                stack.append(Path(entry.path))
                continue
            if key in seen:
                continue
            seen.add(key)
            total += int(stats.st_size)
    return total


__all__ = [
    "ACTION_ARCHIVE_MEMBER",
    "ACTION_DEDUP_LINK",
    "ACTION_EVICT_CACHE",
    "ACTION_REMOVE",
    "ACTION_RESTORE_MEMBER",
    "STORAGE_PLAN_SCHEMA",
    "PlannedAction",
    "StoragePlan",
    "StoragePlanStaleError",
    "build_storage_plan",
    "owner_binding_for",
    "planned_action",
    "revalidate_plan",
]
