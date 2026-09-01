"""The one consequential storage authorization contract.

Cleanup, deduplication, archive creation, hot reclamation, restore, and
CampaignStore maintenance are realized by different engines, because writing a
tar is not the same operation as relinking an inode.  They are *authorized* the
same way, and that shared contract lives here:

```text
explicit invocation authorization
 -> owner-bound immutable plan
 -> storage-operation lease
 -> every touched owner's activity + publication seam, in one fixed order
 -> fresh owner inventory
 -> plan/closure/eligibility/filesystem/state-identity revalidation
 -> admission revalidation
 -> narrow mutation
 -> truthful durable audit
```

Nothing consequential mutates outside :meth:`StorageExecutor.run`.  A
specialized engine receives an already-revalidated snapshot and the plan it was
authorized against; it may not re-derive its own authority from an old
snapshot, an old catalog, or a physical boundary check alone.

Terminality is explicit.  A ``complete`` audit appears only when every action in
the execution reached a verified terminal disposition; an interruption after a
strict subset is recorded truthfully as partial before the exception propagates.
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
from .lease import OwnerSynchronization, owner_mutation_barrier, storage_operation_lease
from .plan import (
    ACTION_EVICT_CACHE,
    ACTION_MAINTAIN_STATE,
    ACTION_REMOVE,
    EXECUTOR_ACTIONS,
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


class StorageAuthorizationError(RuntimeError):
    """A consequential path was reached without explicit invocation authority."""


@dataclass
class StorageExecutionResult:
    """A truthful account of what one storage execution actually did."""

    operation_identity: str
    plan_identity: str
    policy_identity: str
    action: str
    status: str
    completed: list[dict[str, Any]] = field(default_factory=list)
    refused: list[dict[str, Any]] = field(default_factory=list)
    reclaimed_bytes: int = 0
    created_bytes: int = 0
    restored_bytes: int = 0
    detail: str = ""
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": STORAGE_EXECUTION_SCHEMA,
            "operation_identity": self.operation_identity,
            "plan_identity": self.plan_identity,
            "policy_identity": self.policy_identity,
            "action": self.action,
            "status": self.status,
            "completed_actions": list(self.completed),
            "refused_actions": list(self.refused),
            "reclaimed_bytes": int(self.reclaimed_bytes),
            "created_bytes": int(self.created_bytes),
            "restored_bytes": int(self.restored_bytes),
            "detail": self.detail,
            "grants_scientific_authority": False,
            **({"result": self.payload} if self.payload else {}),
        }


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def operation_identity(plan: StoragePlan) -> str:
    """A stable 32-hex operation identity for control-plane locators."""

    return plan.plan_identity[:32]


#: An engine receives the authorized plan, a *fresh* revalidated snapshot, and
#: the result it must fill in truthfully.  It never re-derives authority.
Engine = Callable[[StoragePlan, StorageInventorySnapshot, StorageExecutionResult], None]


class StorageExecutor:
    """Authorize and run one consequential storage operation."""

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

    def authorize_path(
        self, path: Path, snapshot: StorageInventorySnapshot
    ) -> tuple[bool, str]:
        """Semantic closure plus the physical ownership boundary, in that order."""

        protected, why = snapshot.path_protection(path)
        if protected:
            return False, why
        authorized, detail = self.boundary.destructive_authorization(path)
        if not authorized:
            return False, detail
        return True, "authorized by the cross-owner closure and the ownership boundary"

    # -- execution --------------------------------------------------------

    def run(
        self,
        plan: StoragePlan,
        *,
        trigger: str,
        synchronization: OwnerSynchronization,
        engine: Engine | None = None,
    ) -> StorageExecutionResult:
        """Authorize, revalidate, and execute one plan, or refuse it truthfully."""

        identity = operation_identity(plan)
        result = StorageExecutionResult(
            operation_identity=identity,
            plan_identity=plan.plan_identity,
            policy_identity=plan.policy.policy_identity,
            action=plan.policy.action,
            status=STATUS_REFUSED,
        )
        if not plan.policy.apply:
            result.status = STATUS_PLANNED
            result.detail = "dry-run: no mutation was attempted"
            return result

        try:
            with storage_operation_lease(
                self.control_plane,
                timeout_seconds=self.policy.operation_lease_timeout_seconds,
            ):
                with owner_mutation_barrier(self.paths, synchronization):
                    snapshot = self.resnapshot()
                    revalidate_plan(plan, snapshot, self.policy)
                    if plan.admission is not None:
                        revalidate_admission(plan.admission, self.policy)
                    try:
                        if engine is None:
                            self._execute_actions(plan, snapshot, result)
                        else:
                            engine(plan, snapshot, result)
                    except BaseException as exc:
                        # An interruption part-way through is recorded truthfully
                        # as partial. Each completed mutation was individually
                        # authorized, so nothing is rolled back; the next run
                        # re-inventories and re-plans from live state.
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

        result.status = STATUS_COMPLETE if not result.refused else STATUS_PARTIAL
        result.detail = result.detail or (
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
            if action.action == ACTION_MAINTAIN_STATE:
                # Owner maintenance is realized by its own engine; a plan that
                # reaches the default executor with one is a construction error.
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": "campaign-state maintenance needs its owner engine",
                    }
                )
                continue
            authorized, detail = self.authorize_path(action.path, snapshot)
            if not authorized:
                result.refused.append({**action.to_dict(), "refusal": detail})
                continue
            if action.action not in (ACTION_REMOVE, ACTION_EVICT_CACHE):
                result.refused.append(
                    {
                        **action.to_dict(),
                        "refusal": (
                            f"action {action.action!r} is not executed by the cleanup "
                            "engine; it belongs to the archive, dedup, or restore engine"
                        ),
                    }
                )
                continue
            removed = remove_durably(action.path)
            result.completed.append({**action.to_dict(), "removed": removed})
            result.reclaimed_bytes += int(action.size_bytes)

    def _audit(self, result: StorageExecutionResult, *, trigger: str) -> None:
        """Append this operation to the one durable storage audit stream.

        An audit write failure is an evidence failure, not a scientific one: it
        can never roll back a mutation that already happened and must never be
        allowed to fabricate a ``complete`` record, so it is surfaced on the
        result and the operation's real outcome stands.
        """

        try:
            self.control_plane.ensure()
            self.control_plane.append_audit(
                {
                    "created_utc": _utc_now(),
                    "trigger": trigger,
                    "tier": self.policy.tier,
                    **result.to_dict(),
                }
            )
        except Exception as exc:  # pragma: no cover - surfaced, never swallowed
            result.detail = (
                f"{result.detail} (durable audit write failed: {exc})".strip()
            )


def remove_durably(path: Path) -> bool:
    """Remove one authorized path and persist the directory-entry change."""

    from ..target_size_execution.persistence import fsync_parent_directory

    if path.is_symlink() or path.is_file():
        durable_unlink(path)
        return True
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=False)
        fsync_parent_directory(path)
        return True
    return False


def remove_certified_subtree(
    path: Path,
    *,
    members: Sequence[Path],
    refusals: Sequence[tuple[Path, str]],
) -> tuple[bool, str]:
    """Remove a directory only when every disappearing descendant is certified.

    A recursive delete is authority over everything that vanishes with it.  If
    the owner could not certify some descendant - an unexpected file, a nested
    mount, a symlink - the container stays and only the individually authorized
    members are removed.
    """

    if refusals:
        removed = 0
        for member in members:
            if member.is_file() or member.is_symlink():
                durable_unlink(member)
                removed += 1
        return False, (
            f"retained the container and removed {removed} individually authorized "
            f"member(s); {len(refusals)} descendant(s) were not owner-certified"
        )
    remove_durably(path)
    return True, "every descendant was covered by the owner's closed-subtree certification"


def synchronization_for(
    plan: StoragePlan, snapshot: StorageInventorySnapshot
) -> OwnerSynchronization:
    """Derive the owner seams this plan's own actions require.

    Every generation the plan actually touches contributes its publication
    barriers, and every P5 run root it touches contributes that run's activity
    lease.  The current generation is added as well, because the plan's semantic
    identity depends on current-owner advancement even when no current byte is
    touched.
    """

    generations: set[int] = set()
    run_roots: set[Path] = set()
    if snapshot.current_generation is not None:
        generations.add(int(snapshot.current_generation))

    by_path = {view.path: view for view in snapshot.views}
    for action in plan.actions:
        view = snapshot.view(action.artifact_id)
        if view is not None and view.generation is not None:
            generations.add(int(view.generation))
        for part in action.path.parts:
            if part.startswith("g") and part[1:].isdigit():
                generations.add(int(part[1:]))
        run_root = _post_selection_run_root(action.path)
        if run_root is not None:
            run_roots.add(run_root)
        if view is not None:
            candidate = _post_selection_run_root(view.path)
            if candidate is not None:
                run_roots.add(candidate)
    del by_path
    return OwnerSynchronization.of(generations, run_roots)


def _post_selection_run_root(path: Path) -> Path | None:
    """The P5 run root a path belongs to, if any.

    Run roots are ``.../post-selection/g<N>/runs/<run identity>/...``; the run
    identity component is exactly what P5's activity lease is keyed on.
    """

    parts = path.parts
    for index in range(len(parts) - 1):
        if parts[index] == "post-selection" and index + 3 < len(parts):
            if parts[index + 2] == "runs":
                return Path(*parts[: index + 4])
    return None


__all__ = [
    "STATUS_COMPLETE",
    "STATUS_PARTIAL",
    "STATUS_PLANNED",
    "STATUS_REFUSED",
    "STORAGE_EXECUTION_SCHEMA",
    "Engine",
    "StorageAuthorizationError",
    "StorageExecutionError",
    "StorageExecutionResult",
    "StorageExecutor",
    "operation_identity",
    "remove_certified_subtree",
    "remove_durably",
    "synchronization_for",
]
