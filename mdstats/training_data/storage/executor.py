"""The one consequential storage mutation path.

Every destructive or representation-changing storage action converges here, so
there is exactly one place where authorization, race safety, admission, and
terminality are decided.

Authorization has three independent layers and all three must pass:

1. the cross-owner protection closure (semantic eligibility);
2. :class:`~..storage_accounting.CampaignOwnershipBoundary` (physical
   containment, external inputs, symlink and retention-fence reduction) as a
   final mandatory mutation guard;
3. the owning publication barrier, held across revalidation *and* mutation, so
   a publication that begins immediately after a snapshot check cannot lose its
   object.

Terminality is explicit.  A ``complete`` audit record is published only after
every action in the execution reached a verified terminal disposition; a crash
after a strict subset of individually safe removals is allowed, and retry
re-inventories and re-plans rather than assuming the old remaining set.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .admission import revalidate_admission
from .control_plane import StorageControlPlane
from .durability import durable_unlink
from .inventory import StorageInventorySnapshot
from .lease import owner_mutation_barrier, storage_operation_lease
from .plan import (
    ACTION_EVICT_CACHE,
    ACTION_REMOVE,
    StoragePlan,
    StoragePlanStaleError,
    revalidate_plan,
)
from .policy import StoragePolicy

STORAGE_EXECUTION_SCHEMA = "mdstats.mlff-storage-execution.v1"

STATUS_PLANNED = "planned"
STATUS_COMPLETE = "complete"
STATUS_PARTIAL = "partial"
STATUS_REFUSED = "refused"


class StorageExecutionError(RuntimeError):
    """A storage execution could not complete and said so truthfully."""


@dataclass
class StorageExecutionResult:
    """A truthful account of what one storage execution actually did."""

    operation_identity: str
    plan_identity: str
    policy_identity: str
    status: str
    completed: list[dict[str, Any]] = field(default_factory=list)
    refused: list[dict[str, Any]] = field(default_factory=list)
    reclaimed_bytes: int = 0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_EXECUTION_SCHEMA,
            "operation_identity": self.operation_identity,
            "plan_identity": self.plan_identity,
            "policy_identity": self.policy_identity,
            "status": self.status,
            "completed_actions": list(self.completed),
            "refused_actions": list(self.refused),
            "reclaimed_bytes": int(self.reclaimed_bytes),
            "detail": self.detail,
            "grants_scientific_authority": False,
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def operation_identity(plan: StoragePlan) -> str:
    """A stable 32-hex operation identity for control-plane locators."""

    return plan.plan_identity[:32]


class StorageExecutor:
    """Apply one immutable plan under owner-local race barriers."""

    def __init__(
        self,
        *,
        paths: Any,
        policy: StoragePolicy,
        control_plane: StorageControlPlane,
        boundary: Any,
        resnapshot: Callable[[], StorageInventorySnapshot],
    ) -> None:
        self.paths = paths
        self.policy = policy
        self.control_plane = control_plane
        self.boundary = boundary
        self.resnapshot = resnapshot

    # -- authorization ----------------------------------------------------

    def _authorize(self, path: Path, snapshot: StorageInventorySnapshot) -> tuple[bool, str]:
        """Semantic closure plus the physical ownership boundary, in that order."""

        protected, why = snapshot.path_protection(path)
        if protected:
            return False, why
        authorized, detail = self.boundary.destructive_authorization(path)
        if not authorized:
            return False, detail
        return True, "authorized by the cross-owner closure and the ownership boundary"

    # -- execution --------------------------------------------------------

    def apply(self, plan: StoragePlan, *, trigger: str) -> StorageExecutionResult:
        """Execute one plan, or refuse it, and record the truth either way."""

        identity = operation_identity(plan)
        result = StorageExecutionResult(
            operation_identity=identity,
            plan_identity=plan.plan_identity,
            policy_identity=plan.policy.policy_identity,
            status=STATUS_REFUSED,
        )
        if not plan.policy.apply:
            result.status = STATUS_PLANNED
            result.detail = "dry-run: no mutation was attempted"
            return result

        generations = _generations_touched(plan)
        try:
            with storage_operation_lease(
                self.control_plane,
                timeout_seconds=self.policy.operation_lease_timeout_seconds,
            ):
                with owner_mutation_barrier(self.paths, generations):
                    snapshot = self.resnapshot()
                    revalidate_plan(plan, snapshot, self.policy)
                    if plan.admission is not None:
                        revalidate_admission(plan.admission, self.policy)
                    try:
                        self._execute_actions(plan, snapshot, result)
                    except BaseException as exc:
                        # An interruption part-way through is recorded truthfully
                        # as partial.  Each completed removal was individually
                        # authorized and safe, so nothing is rolled back; the
                        # next run re-inventories and re-plans from live state.
                        result.status = STATUS_PARTIAL
                        result.detail = (
                            "execution was interrupted after a strict subset of "
                            f"actions: {exc}"
                        )
                        self._audit(result, trigger=trigger)
                        raise
        except StoragePlanStaleError as exc:
            result.status = STATUS_REFUSED
            result.detail = str(exc)
            self._audit(result, trigger=trigger)
            return result

        result.status = (
            STATUS_COMPLETE if not result.refused else STATUS_PARTIAL
        )
        result.detail = (
            "every planned action reached a verified terminal disposition"
            if result.status == STATUS_COMPLETE
            else "some actions were refused at mutation time; the execution is not complete"
        )
        self._audit(result, trigger=trigger)
        self.control_plane.prune_audit(keep=self.policy.audit_retention_records)
        return result

    def _execute_actions(
        self,
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        for action in plan.actions:
            authorized, detail = self._authorize(action.path, snapshot)
            if not authorized:
                result.refused.append({**action.to_dict(), "refusal": detail})
                continue
            if action.action not in (ACTION_REMOVE, ACTION_EVICT_CACHE):
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            f"action {action.action!r} is not executed by the cleanup "
                            "executor; it belongs to the archive or dedup owner"
                        ),
                    }
                )
                continue
            removed = _remove_durably(action.path)
            result.completed.append({**action.to_dict(), "removed": removed})
            result.reclaimed_bytes += int(action.size_bytes)

    def _audit(self, result: StorageExecutionResult, *, trigger: str) -> None:
        self.control_plane.append_audit(
            {
                "created_utc": _utc_now(),
                "trigger": trigger,
                "action": self.policy.action,
                "tier": self.policy.tier,
                **result.to_dict(),
            }
        )


def _remove_durably(path: Path) -> bool:
    """Remove one authorized path and persist the directory-entry change."""

    if path.is_symlink() or path.is_file():
        durable_unlink(path)
        return True
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
        from ..target_size_execution.persistence import fsync_parent_directory

        fsync_parent_directory(path)
        return True
    return False


def _generations_touched(plan: StoragePlan) -> tuple[int, ...]:
    """Every campaign generation whose owners could race this plan.

    The current generation is always included: a plan that touches only
    historical bytes still runs while the current owners may be publishing, and
    the barrier is what makes the object-before-pointer window safe.
    """

    generations: set[int] = set()
    current = plan.owner_binding.get("current_generation")
    if current is not None:
        generations.add(int(current))
    for action in plan.actions:
        for part in Path(action.path).parts:
            if part.startswith("g") and part[1:].isdigit():
                generations.add(int(part[1:]))
    return tuple(sorted(generations))


__all__ = [
    "STATUS_COMPLETE",
    "STATUS_PARTIAL",
    "STATUS_PLANNED",
    "STATUS_REFUSED",
    "STORAGE_EXECUTION_SCHEMA",
    "StorageExecutionError",
    "StorageExecutionResult",
    "StorageExecutor",
    "operation_identity",
]
