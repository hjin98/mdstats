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
    MAINTENANCE_ACTIONS,
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

#: Suffix marking an outcome whose durable operational evidence could not be
#: published.
#:
#: The audit is diagnostic evidence, not scientific authority, so a failed audit
#: append never rolls back a mutation that already happened and never fails the
#: science.  But it must not be reported as an ordinary fully audited success
#: either: a caller that checks for ``complete`` would otherwise be told a
#: durable record exists when none does.  The status itself carries the
#: difference so no caller has to parse a detail string to find it.
UNAUDITED_SUFFIX = "_unaudited"


def unaudited_status(status: str) -> str:
    return status if status.endswith(UNAUDITED_SUFFIX) else f"{status}{UNAUDITED_SUFFIX}"


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
    #: Whether this operation's durable audit record was actually published.
    audit_published: bool = False
    #: Why publication failed, when it did.
    audit_failure: str = ""
    #: Why bounded audit retention failed, when it did. Retention is
    #: housekeeping on diagnostic evidence: its failure never unpublishes a
    #: record that was written and never touches the primary mutation.
    retention_failure: str = ""

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
            "audit_published": bool(self.audit_published),
            "audit_failure": self.audit_failure,
            "retention_failure": self.retention_failure,
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
                        self._finalize(result, trigger=trigger)
                        raise
                    self._settle(result)
                    self._finalize(result, trigger=trigger)
                    return result
        except StoragePlanStaleError as exc:
            result.status = STATUS_REFUSED
            result.detail = str(exc)
            with storage_operation_lease(
                self.control_plane,
                timeout_seconds=self.policy.operation_lease_timeout_seconds,
            ):
                self._finalize(result, trigger=trigger)
            return result

        # Unreachable: every path above returns inside the lease.
        raise StorageExecutionError("storage execution reached no terminal disposition")

    def _settle(self, result: StorageExecutionResult) -> None:
        """Decide the terminal status this execution actually earned."""

        if not result.refused:
            result.status = STATUS_COMPLETE
            default_detail = "every planned action reached a verified terminal disposition"
        elif not result.completed:
            # Nothing happened at all. Reporting that as "partial" would imply a
            # mutation this operation never made.
            result.status = STATUS_REFUSED
            default_detail = (
                "every planned action was refused at mutation time; nothing was changed"
            )
        else:
            result.status = STATUS_PARTIAL
            default_detail = (
                "some actions were refused at mutation time; the execution is not complete"
            )
        result.detail = result.detail or default_detail

    def _finalize(self, result: StorageExecutionResult, *, trigger: str) -> None:
        """Publish this operation's audit record and apply bounded retention.

        Both happen while the storage-operation lease is still held, and that is
        deliberate. Retention reads the whole stream and replaces it; if another
        operation could append between the read and the replace, the record it
        just published - and returned as audited - would be silently rewritten
        away. One serialization owns both halves of the stream's lifecycle.
        """

        self._audit(result, trigger=trigger)
        if not result.audit_published:
            return
        try:
            self.control_plane.prune_audit(keep=self.policy.audit_retention_records)
        except Exception as exc:
            # Housekeeping on diagnostic evidence. The mutation stands, the
            # published record stands, and a later operation retries retention.
            result.retention_failure = str(exc)
            result.detail = (
                f"{result.detail} (bounded audit retention failed and will be "
                f"retried by a later operation: {exc})"
            ).strip()

    def _execute_actions(
        self,
        plan: StoragePlan,
        snapshot: StorageInventorySnapshot,
        result: StorageExecutionResult,
    ) -> None:
        for action in plan.actions:
            if action.action in MAINTENANCE_ACTIONS:
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

        # The record states the truth that holds *if* this append succeeds, so
        # the durable evidence of a successful operation does not contradict
        # itself by saying it was never published.
        result.audit_published = True
        result.audit_failure = ""
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
        except Exception as exc:
            # Never rolled back, never fabricated, and never reported as an
            # ordinary success: the status itself becomes an explicitly degraded
            # one so a caller cannot mistake this for a fully audited operation.
            # Pessimistic on purpose. After an arbitrary write/fsync failure a
            # complete record may or may not have reached the file, and this
            # package will not promise a proof of absence it cannot have. What
            # it does promise is that the caller is never told an operation was
            # audited when publication reported failure.
            result.audit_published = False
            result.audit_failure = str(exc)
            result.status = unaudited_status(result.status)
            result.detail = (
                f"{result.detail} (the mutation stands, but its durable audit "
                f"record could not be published: {exc})"
            ).strip()


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

    for action in plan.actions:
        # An action's own target, plus every other object it makes authoritative:
        # a dedup link's canonical source lives in some other owner's run and is
        # never written by the action, yet its inode becomes the bytes behind a
        # second name, so that owner has to be fenced too.
        artifact_ids = (action.artifact_id, *action.synchronization_artifact_ids)
        paths = (action.path, *(Path(item) for item in action.synchronization_paths))
        for artifact_id in artifact_ids:
            view = snapshot.view(artifact_id) if artifact_id else None
            if view is None:
                continue
            if view.generation is not None:
                generations.add(int(view.generation))
            candidate = _post_selection_run_root(view.path)
            if candidate is not None:
                run_roots.add(candidate)
        for path in paths:
            for part in path.parts:
                if part.startswith("g") and part[1:].isdigit():
                    generations.add(int(part[1:]))
            run_root = _post_selection_run_root(path)
            if run_root is not None:
                run_roots.add(run_root)
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
