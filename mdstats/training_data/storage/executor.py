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

import logging
import os
import shutil
import stat
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .admission import revalidate_admission
from .control_plane import StorageControlPlane
from .durability import durable_unlink
from .inventory import StorageInventorySnapshot
from .trust import dir_fd_mutation_supported
from .lease import OwnerSynchronization, owner_mutation_barrier, storage_operation_lease
from .outcome import (
    MutationLedger,
    MutationOutcome,
    PartialMutationError,
    already_absent,
    partial_change_refused,
    refused_no_change,
    removed,
)
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

#: Secondary failure evidence - a descriptor close that failed while a primary
#: product failure was already propagating - is logged rather than raised, so it
#: is visible without displacing the failure that carries the mutation truth.
_LOGGER = logging.getLogger(__name__)

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
    #: Whether any action mutated the filesystem.  A refusal that happened
    #: part-way through still changed bytes, and an execution that changed bytes
    #: is never "refused; nothing happened".
    mutated: bool = False
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
            "mutated": bool(self.mutated),
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
                        # An interruption is reported from what the action
                        # recorder actually captured, not from the fact that
                        # control left this way. An execution that failed before
                        # changing anything is not "partial after a strict
                        # subset of actions" - that sentence claims a mutation
                        # that never happened, and it is the sentence an
                        # operator reads after an incident. `_settle` already
                        # refuses to call a nothing-happened execution partial;
                        # the two paths agree now.
                        #
                        # Whatever did complete was individually authorized, so
                        # nothing is rolled back and the audit is still
                        # published before the failure continues; the next run
                        # re-inventories and re-plans from live state.
                        if result.mutated:
                            result.status = STATUS_PARTIAL
                            result.detail = (
                                "execution was interrupted after a strict subset of "
                                f"actions: {exc}"
                            )
                        else:
                            result.status = STATUS_REFUSED
                            result.detail = (
                                "execution was interrupted before any action changed "
                                f"anything; nothing was modified: {exc}"
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
        elif not result.mutated:
            # Nothing was mutated. Reporting that as "partial" would imply a
            # persistent change this operation never made.
            result.status = STATUS_REFUSED
            default_detail = (
                "every planned action was refused or unchanged at mutation time; nothing was modified"
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
            record_or_reraise(
                result, action, lambda action=action: remove_durably_outcome(action.path)
            )

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
    """Remove one path and persist the directory-entry change.

    Thin wrapper over :func:`remove_durably_outcome` to preserve compatibility
    without maintaining a separate recursive algorithm. Partial mutations
    propagate rather than being converted to False.
    """

    try:
        outcome = remove_durably_outcome(path)
    except PartialMutationError:
        raise
    if outcome.outcome == "removed":
        return True
    if outcome.mutated:
        raise PartialMutationError(outcome, OSError(outcome.detail))
    return False


def _unlink_measured_file(path: Path, stats: os.stat_result, ledger: MutationLedger) -> None:
    """Unlink one already-measured non-directory, crediting only a real removal.

    The primitive reports whether *this* call's unlink syscall succeeded, and
    that is the only evidence used. Asking the filesystem afterwards whether the
    name is gone cannot answer the question that matters: a name this execution
    failed to unlink can be absent because another actor removed it, and a name
    it did unlink can be present again because another actor recreated it.
    Either reading transfers someone else's transition into this action's audit.
    """

    size = int(stats.st_size)
    identity = (int(stats.st_dev), int(stats.st_ino))
    unlinked = False

    def _mark_unlinked() -> None:
        nonlocal unlinked
        unlinked = True
        ledger.credit(size, identity)

    try:
        durable_unlink(path, missing_ok=False, on_unlinked=_mark_unlinked)
    except OSError as exc:
        if unlinked:
            raise ledger.failure(
                exc,
                f"{path} was removed but the removal could not be made durable: {exc}",
            ) from exc
        raise ledger.failure(exc, f"{path} could not be removed: {exc}") from exc


def remove_durably_outcome(path: Path) -> MutationOutcome:
    """The generic removal, reported as a terminal disposition.

    ``remove_durably`` answers "did I remove something", which conflates the
    target being gone already with this execution having reclaimed it, and it
    cannot say what a *partial* recursive delete already took. Both matter to
    the audit, so this owns the walk: every entry is measured before its unlink
    and credited after it, and a failure part-way through carries the exact
    amount already gone rather than a bare ``OSError``.
    """

    ledger = MutationLedger()
    try:
        stats = path.lstat()
    except FileNotFoundError:
        return already_absent("the planned target was already gone")
    except OSError as exc:
        return refused_no_change(f"the planned target could not be observed: {exc}")

    if not stat.S_ISDIR(stats.st_mode):
        _unlink_measured_file(path, stats, ledger)
        return removed("removed", removed_bytes=ledger.removed_bytes)

    if not dir_fd_mutation_supported():
        # The recursion below descends through directory descriptors, so this is
        # the capability that actually protects it. `shutil.rmtree`'s own
        # symlink-attack promise describes `rmtree`'s implementation and would
        # be no protection at all for a separate walker.
        raise StorageExecutionError(
            "this platform does not provide the no-follow directory-descriptor "
            f"primitives recursive removal is built on, so {path} is retained "
            "rather than removed by pathname"
        )
    _remove_tree_tracked(path, ledger)
    _fsync_parent_tracked(path, ledger)
    return removed("removed", removed_bytes=ledger.removed_bytes)


def _remove_tree_tracked(root: Path, ledger: MutationLedger) -> None:
    """Delete one directory tree, accounting for every entry as it goes.

    Descriptor-relative and no-follow throughout. `shutil.rmtree` earns its
    symlink-attack resistance by descending through directory descriptors; a
    pathname walk that merely *checks* that flag inherits none of it, because
    between classifying a child as a directory and reopening its path, that
    entry can become a symlink and the recursion follows it out of the
    authorized tree. So this opens each child through the one no-follow
    acquisition the repository owns and operates relative to that descriptor.

    Depth-first and bottom-up so a directory is only removed once it is empty.
    A failure at any point raises with the running account attached, because by
    then the tree on disk is neither what it was nor gone - and an emptied
    directory that is now removed counts as a mutation even though a directory
    entry credits no bytes.
    """

    from .trust import (
        MountBoundaryError,
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    try:
        parent_fd = open_directory_nofollow(str(root.parent))
    except FileNotFoundError:
        return
    except NamespaceAmbiguity as exc:
        raise ledger.failure(
            OSError(f"{root.parent} could not be opened as a plain directory: {exc}"),
            f"{root.parent} is not a plain directory: {exc}",
        ) from exc
    # The parent stays open all the way through the final `rmdir`. Closing it
    # once the child was acquired would mean the removal had to name the root
    # by absolute path again - a second namespace resolution, and exactly the
    # lookup the descent was built to avoid.
    primary: BaseException | None = None
    try:
        try:
            handle = open_directory_nofollow(root.name, dir_fd=parent_fd)
        except FileNotFoundError:
            return
        except NamespaceAmbiguity as exc:
            raise ledger.failure(
                OSError(f"{root} is not a plain directory: {exc}"),
                f"{root} could not be opened as a plain directory: {exc}",
            ) from exc
        crossed, detail = verify_opened_directory_trust(parent_fd, handle, root)
        if crossed:
            primary = ledger.failure(
                MountBoundaryError(f"{root}: {detail}"),
                f"{root} is not campaign-owned: {detail}",
            )
            primary = _close_descriptor(handle, root, ledger, primary)
            raise primary
        try:
            _remove_tree_contents(handle, root, ledger)
            _finalize_directory_removal(parent_fd, root.name, handle, root, ledger)
        except BaseException as exc:  # noqa: BLE001 - re-raised below
            primary = exc
        primary = _close_descriptor(handle, root, ledger, primary)
        if primary is not None:
            raise primary
    finally:
        # A close failure here cannot be allowed to displace a primary failure
        # that already carries this action's mutation truth.
        close_outcome = _close_descriptor(parent_fd, root.parent, ledger, primary)
        if close_outcome is not None and close_outcome is not primary:
            raise close_outcome


def _finalize_directory_removal(
    parent_fd: int, name: str, handle: int, display: Path, ledger: MutationLedger
) -> None:
    """Spend the authenticated capability on the entry it actually describes.

    ``rmdir`` names an entry, so the descriptor that authenticated this
    directory is compared against that entry one last time, immediately before
    the syscall and relative to the parent this descent authenticated. A
    substituted name is refused instead of removed; nothing is re-resolved by
    absolute path.
    """

    from .trust import verify_final_directory_identity

    same, why = verify_final_directory_identity(parent_fd, name, handle, display)
    if not same:
        raise ledger.failure(OSError(why), why)
    try:
        os.rmdir(name, dir_fd=parent_fd)
    except OSError as exc:
        raise ledger.failure(exc, f"{display} could not be removed: {exc}") from exc
    ledger.note_mutation()


def _close_descriptor(
    handle: int,
    display: Path,
    ledger: MutationLedger,
    primary: BaseException | None,
) -> BaseException | None:
    """Close one descriptor exactly once and rank its failure honestly.

    A descriptor is closed on every path, including the failing ones, or a
    bounded retry loop leaks one per contradiction. But a close that fails while
    a primary product failure is already in flight is secondary evidence: the
    primary carries what this action removed, and replacing it would lose that.
    So the failure is logged and the primary is preserved; only when close is
    the *sole* failure does it become the outcome - as a partial when the action
    had already mutated, and as a plain failure when it had not.
    """

    try:
        os.close(handle)
    except OSError as exc:
        if primary is not None:
            _LOGGER.warning(
                "storage: closing the descriptor for %s failed after a primary "
                "failure (%s); the primary failure is preserved",
                display,
                exc,
            )
            return primary
        return ledger.failure(exc, f"{display} descriptor close failed: {exc}")
    return primary


def _remove_tree_contents(handle: int, display: Path, ledger: MutationLedger) -> None:
    """Empty one already-authenticated directory, relative to its descriptor."""

    from .trust import (
        MountBoundaryError,
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    try:
        entries = sorted(os.scandir(handle), key=lambda item: item.name)
    except OSError as exc:
        raise ledger.failure(exc, f"{display} could not be enumerated: {exc}") from exc
    for entry in entries:
        child = display / entry.name
        try:
            is_dir = entry.is_dir(follow_symlinks=False)
        except OSError as exc:
            raise ledger.failure(exc, f"{child} could not be observed: {exc}") from exc
        if is_dir:
            # Opened no-follow from this descriptor: an entry replaced by a
            # symlink between the classification above and this open is refused
            # here rather than followed to whatever it points at.
            try:
                child_handle = open_directory_nofollow(entry.name, dir_fd=handle)
            except FileNotFoundError:
                continue
            except NamespaceAmbiguity as exc:
                raise ledger.failure(
                    OSError(f"{child} is no longer a plain directory: {exc}"),
                    f"{child} is no longer the plain directory it was observed as: {exc}",
                ) from exc
            crossed, detail = verify_opened_directory_trust(handle, child_handle, child)
            if crossed:
                os.close(child_handle)
                raise ledger.failure(
                    MountBoundaryError(f"{child}: {detail}"),
                    f"{child} is not campaign-owned: {detail}",
                )
            child_primary: BaseException | None = None
            try:
                _remove_tree_contents(child_handle, child, ledger)
                _finalize_directory_removal(
                    handle, entry.name, child_handle, child, ledger
                )
            except BaseException as exc:  # noqa: BLE001 - re-raised below
                child_primary = exc
            child_primary = _close_descriptor(
                child_handle, child, ledger, child_primary
            )
            if child_primary is not None:
                raise child_primary
            continue
        try:
            child_stat = entry.stat(follow_symlinks=False)
        except OSError as exc:
            raise ledger.failure(exc, f"{child} could not be measured: {exc}") from exc
        try:
            os.unlink(entry.name, dir_fd=handle)
        except OSError as exc:
            raise ledger.failure(exc, f"{child} could not be removed: {exc}") from exc
        if stat.S_ISLNK(child_stat.st_mode):
            # The link entry itself is removed; its target never is.
            ledger.note_mutation()
            continue
        ledger.credit(
            int(child_stat.st_size), (int(child_stat.st_dev), int(child_stat.st_ino))
        )
    try:
        os.fsync(handle)
    except OSError as exc:
        raise ledger.failure(
            exc, f"{display} was emptied but the removal could not be made durable: {exc}"
        ) from exc


def _fsync_parent_tracked(path: Path, ledger: MutationLedger) -> None:
    """Persist the directory-entry removal, keeping the account if it fails."""

    from ..target_size_execution.persistence import fsync_parent_directory

    try:
        fsync_parent_directory(path)
    except OSError as exc:
        raise ledger.failure(
            exc, f"{path} was removed but the removal could not be made durable: {exc}"
        ) from exc




def record_or_reraise(result: "StorageExecutionResult", action: Any, run) -> MutationOutcome:
    """Record what one action did, even when it ends by raising.

    A helper that unlinked and then failed on durability knows something the
    executor's outer interruption handling never will: which action mutated and
    how many bytes are already gone. That evidence is recorded here, at the
    action boundary, before the failure is allowed to continue upward - so the
    partial audit describes the tree that now exists rather than reporting only
    that something went wrong.

    Every ``StorageExecutor`` removal path calls this, including the default
    engine, so the two cannot drift into different truths again.
    """

    try:
        outcome = run()
    except PartialMutationError as exc:
        record_removal(result, action, exc.outcome)
        raise (exc.cause or exc) from exc
    record_removal(result, action, outcome)
    return outcome


def record_removal(
    result: "StorageExecutionResult",
    action: Any,
    outcome: MutationOutcome,
) -> None:
    """File one removal into the collection its outcome actually earns.

    A refused mutation recorded as a completed action is how an execution ends
    up reporting ``complete`` while every byte it planned to reclaim is still on
    disk. The collection, the byte credit, and the mutation flag all come from
    the outcome; none of them is inferred from a reason string.
    """

    planned = int(action.size_bytes)
    entry = {**action.to_dict(), **outcome.to_dict(planned)}
    if outcome.mutated:
        result.mutated = True
    if outcome.succeeded:
        result.completed.append(entry)
    else:
        result.refused.append({**entry, "refusal": outcome.detail})
    # The aggregate is exactly the sum of what the actions each recorded.
    result.reclaimed_bytes += int(entry["reclaimed_bytes"])


def remove_certified_subtree(
    path: Path,
    *,
    members: Sequence[Path],
    refusals: Sequence[tuple[Path, str]],
    root_identity: Mapping[str, int] | None = None,
    authority_identity: Mapping[str, int] | None = None,
    member_authorities: Mapping[Path, str] | None = None,
) -> MutationOutcome:
    """Remove a directory only when every disappearing descendant is certified.

    A recursive delete is authority over everything that vanishes with it.  If
    the owner could not certify some descendant - an unexpected file, a nested
    mount, a symlink - the container stays and only the individually authorized
    members are removed.  That case is a *partial* mutation, not a refusal: the
    authorized members really are gone, and reporting "nothing changed" would
    leave the audit describing a tree that no longer exists.
    """

    # ``rmtree`` avoiding symlink attacks says nothing about the names *above*
    # what it recurses into.  A container replaced between certification and this
    # call - or an authority root above it swapped for a symlink that happens to
    # lead back to the same bytes - would otherwise be entered as if it were the
    # certified one.  Both are re-observed here, at the last moment before entry,
    # with ``lstat`` so a substituted final component is seen as the symlink it
    # is rather than as its target.
    for label, target, expected in (
        ("authority root", path.parent, authority_identity),
        ("container", path, root_identity),
    ):
        if expected is None:
            continue
        try:
            stats = os.lstat(target)
        except OSError as exc:
            return refused_no_change(
                f"the certified {label} could not be re-observed: {exc}"
            )
        if (
            not stat.S_ISDIR(stats.st_mode)
            or int(stats.st_dev) != int(expected["device"])
            or int(stats.st_ino) != int(expected["inode"])
        ):
            return refused_no_change(
                f"the certified {label} is no longer the filesystem object this "
                "action was authorized against; nothing was removed"
            )
    ledger = MutationLedger()
    if refusals:
        return _remove_authorized_members(
            path, members, refusals, member_authorities, ledger
        )
    if not path.exists() and not path.is_symlink():
        return already_absent("the certified container was already gone")
    _remove_tree_or_file_tracked(path, ledger)
    return removed(
        "every descendant was covered by the owner's closed-subtree certification",
        removed_bytes=ledger.removed_bytes,
    )


class _DescriptorScope:
    """Every descriptor one descent opens, closed exactly once at the end.

    Closing inside each branch is how a bounded contradiction loop ends up
    leaking a descriptor per iteration: one path forgets, or an exception skips
    the close it was supposed to reach. The scope owns them instead, and ranks
    close failures against whatever product failure is already in flight rather
    than swallowing them.
    """

    def __init__(self, ledger: MutationLedger) -> None:
        self._open: list[tuple[int, Path]] = []
        self._ledger = ledger

    def adopt(self, handle: int, display: Path) -> int:
        self._open.append((handle, display))
        return handle

    def mark(self) -> int:
        """The current depth, so one member's descent can be unwound alone."""

        return len(self._open)

    def close_to(self, depth: int, primary: BaseException | None) -> BaseException | None:
        """Release everything opened past ``depth``, innermost first.

        A descent to one nested member releases its own intermediates before the
        next member starts. Holding them for the whole action would make the
        descriptor count grow with the certified member set, which is exactly
        the size that is unbounded here.
        """

        while len(self._open) > depth:
            handle, display = self._open.pop()
            primary = _close_descriptor(handle, display, self._ledger, primary)
        return primary

    def close_all(self, primary: BaseException | None) -> BaseException | None:
        return self.close_to(0, primary)


def _remove_authorized_members(
    path: Path,
    members: Sequence[Path],
    refusals: Sequence[tuple[Path, str]],
    member_authorities: Mapping[Path, str] | None,
    ledger: MutationLedger,
) -> MutationOutcome:
    """Remove only the members this owner individually certified.

    The container itself is retained - something inside it was not certified -
    so this is a descent to authorized leaves rather than a recursive delete.
    That does not make the descent less consequential: every directory it passes
    through is an opportunity for a substituted entry or a nested mount to
    redirect a deletion, so each one is opened no-follow from the descriptor
    above it and put through the same opened-descriptor mount decision the
    recursive owners use.

    A member with no owner-certified kind is not deleted. Treating an untyped
    path as a regular file would let the *absence* of authority stand in for
    permission, which is the one substitution no later check can catch.
    """

    from .trust import (
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    scope = _DescriptorScope(ledger)
    primary: BaseException | None = None
    outcome: MutationOutcome | None = None
    count = 0
    try:
        try:
            anchor_fd = scope.adopt(
                open_directory_nofollow(str(path.parent)), path.parent
            )
        except FileNotFoundError:
            outcome = already_absent("the certified container was already gone")
            raise _ScopeExit
        except (NamespaceAmbiguity, OSError) as exc:
            outcome = refused_no_change(
                f"the authority root above the certified container could not be "
                f"opened as a plain directory: {exc}"
            )
            raise _ScopeExit
        try:
            container_fd = scope.adopt(
                open_directory_nofollow(path.name, dir_fd=anchor_fd), path
            )
        except FileNotFoundError:
            outcome = already_absent("the certified container was already gone")
            raise _ScopeExit
        except (NamespaceAmbiguity, OSError) as exc:
            outcome = refused_no_change(
                f"the certified container could not be opened: {exc}"
            )
            raise _ScopeExit
        crossed, detail = verify_opened_directory_trust(anchor_fd, container_fd, path)
        if crossed:
            outcome = refused_no_change(f"{path} is not campaign-owned: {detail}")
            raise _ScopeExit

        container_depth = scope.mark()
        for member in members:
            # Each member's descent is unwound before the next one begins, so
            # the descriptor count does not grow with the certified member set.
            released = scope.close_to(container_depth, None)
            if released is not None:
                raise released
            expected_kind = getattr(member, "authorized_kind", None) or (
                member_authorities or {}
            ).get(member)
            if not expected_kind:
                outcome = ledger.stop(
                    f"{member} carries no owner-certified kind, so nothing "
                    "authorizes deleting it; the container is retained"
                )
                raise _ScopeExit
            try:
                rel = member.relative_to(path)
            except ValueError:
                continue

            parent_handle = container_fd
            descended: list[int] = []
            for part in rel.parts[:-1]:
                display = path.joinpath(*rel.parts[: len(descended) + 1])
                try:
                    parent_handle = scope.adopt(
                        open_directory_nofollow(part, dir_fd=parent_handle), display
                    )
                except FileNotFoundError:
                    parent_handle = -1
                    break
                except (NamespaceAmbiguity, OSError) as exc:
                    outcome = ledger.stop(
                        f"{display} is no longer a plain directory: {exc}"
                    )
                    raise _ScopeExit
                descended.append(parent_handle)
                # An intermediate directory is a traversal decision like any
                # other: a nested mount here would carry the descent onto bytes
                # this campaign does not own.
                crossed, detail = verify_opened_directory_trust(
                    descended[-2] if len(descended) > 1 else container_fd,
                    parent_handle,
                    display,
                )
                if crossed:
                    outcome = ledger.stop(f"{display} is not campaign-owned: {detail}")
                    raise _ScopeExit
            if parent_handle == -1:
                continue
            member_name = rel.parts[-1]

            try:
                stats = os.stat(member_name, dir_fd=parent_handle, follow_symlinks=False)
            except FileNotFoundError:
                continue
            except OSError as exc:
                raise ledger.failure(exc, f"{member} could not be measured: {exc}")

            is_symlink = stat.S_ISLNK(stats.st_mode)
            is_regular = stat.S_ISREG(stats.st_mode)
            if is_symlink:
                if expected_kind != "symlink":
                    continue
            elif is_regular:
                if expected_kind != "file":
                    continue
            else:
                continue

            unlinked = False

            def _on_unlinked(
                stats: os.stat_result = stats, is_symlink: bool = is_symlink
            ) -> None:
                nonlocal unlinked
                unlinked = True
                if is_symlink:
                    ledger.note_mutation()
                else:
                    ledger.credit(
                        int(stats.st_size), (int(stats.st_dev), int(stats.st_ino))
                    )

            try:
                durable_unlink(
                    member,
                    dir_fd=parent_handle,
                    missing_ok=False,
                    on_unlinked=_on_unlinked,
                )
            except OSError as exc:
                if unlinked:
                    raise ledger.failure(
                        exc,
                        f"{member} was removed but the removal could not be made "
                        f"durable: {exc}",
                    ) from exc
                raise ledger.failure(
                    exc, f"{member} could not be removed: {exc}"
                ) from exc
            count += 1
    except _ScopeExit:
        pass
    except BaseException as exc:  # noqa: BLE001 - re-raised after closing
        primary = exc
    primary = scope.close_all(primary)
    if primary is not None:
        raise primary
    if outcome is not None:
        return outcome
    detail = (
        f"retained the container and removed {count} individually authorized "
        f"member(s); {len(refusals)} descendant(s) were not owner-certified"
    )
    return ledger.stop(detail)


class _ScopeExit(Exception):
    """Leave a descriptor scope with an outcome already decided."""


def _remove_tree_or_file_tracked(path: Path, ledger: MutationLedger) -> None:
    """Remove one authorized path, keeping this action's running account."""

    try:
        stats = path.lstat()
    except OSError as exc:
        raise ledger.failure(exc, f"{path} could not be observed: {exc}") from exc
    if not stat.S_ISDIR(stats.st_mode):
        _unlink_measured_file(path, stats, ledger)
        return
    if not dir_fd_mutation_supported():
        # The recursion below descends through directory descriptors, so this is
        # the capability that actually protects it. `shutil.rmtree`'s own
        # symlink-attack promise describes `rmtree`'s implementation and would
        # be no protection at all for a separate walker.
        raise StorageExecutionError(
            "this platform does not provide the no-follow directory-descriptor "
            f"primitives recursive removal is built on, so {path} is retained "
            "rather than removed by pathname"
        )
    _remove_tree_tracked(path, ledger)
    _fsync_parent_tracked(path, ledger)


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
    attempt_roots: set[Path] = set()
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
            attempt_root = _qualification_attempt_root(path)
            if attempt_root is not None:
                attempt_roots.add(attempt_root)
    return OwnerSynchronization.of(generations, run_roots, attempt_roots)


def _qualification_attempt_root(path: Path) -> Path | None:
    """The P7 attempt root a path belongs to, if any.

    Attempt roots are ``.../qualification/g<N>/attempts/<attempt identity>/...``,
    and the attempt identity component is exactly what P7's state lock is keyed
    on. Only attempts a plan actually touches are fenced; taking every attempt's
    lock would serialize unrelated qualification work for no reason.
    """

    parts = path.parts
    for index in range(len(parts) - 1):
        if (
            parts[index] == "qualification"
            and index + 3 < len(parts)
            and parts[index + 2] == "attempts"
        ):
            return Path(*parts[: index + 4])
    return None


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
