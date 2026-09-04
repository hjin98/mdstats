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
from .cleanup_domain import (
    CLASS_GENERIC_LEAF,
    StorageEngineDomainError,
    classify_cleanup_plan,
    require_supported_domain,
)
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

#: The default engine's complete destructive domain, declared once.  It is both
#: the set :func:`require_supported_domain` preflights and the set the dispatch
#: loop below branches on; a focused invariant test proves the two agree, so a
#: future class cannot be admitted to the domain without a handler.
DEFAULT_CLEANUP_DOMAIN = (CLASS_GENERIC_LEAF,)


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
                    except StorageEngineDomainError as exc:
                        # The plan asked an engine for authority it does not
                        # have. That is a construction failure of the execution
                        # itself, discovered before the first transition, so the
                        # truth is a refused, non-mutating, zero-byte operation -
                        # not a stale plan, and not an owner refusing a target.
                        # It is materialized and durably published here, and only
                        # then does the typed failure continue to the caller.
                        if result.mutated:
                            # A domain failure raised by a fail-closed residual
                            # branch *after* an earlier action already completed
                            # is unreachable while every declared class has a
                            # handler, but the audit still reports what actually
                            # happened rather than a sentence that erases a
                            # persistent change.
                            result.status = STATUS_PARTIAL
                            result.detail = (
                                "the execution stopped at an action the selected "
                                f"engine cannot execute: {exc}"
                            )
                        else:
                            result.status = STATUS_REFUSED
                            result.detail = (
                                "the plan was refused before any action was attempted "
                                f"because the selected engine cannot execute it: {exc}"
                            )
                        self._finalize(result, trigger=trigger)
                        raise
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
        """The default engine: positively classified generic leaves, only.

        Its destructive domain is one *positive* class, established from the
        fresh post-revalidation snapshot while the lease and every touched
        owner's barrier are still held. Everything else - an exact authorizer,
        an owner-scoped directory, maintenance, a special node, or a malformed
        action/owner binding - is outside this engine's authority, and the whole
        plan is refused before the first transition rather than after a
        convenient prefix of it has already been spent.
        """

        classifications = classify_cleanup_plan(
            plan, snapshot, self.policy, engine="default cleanup engine"
        )
        require_supported_domain(
            classifications,
            engine="default cleanup engine",
            supported=DEFAULT_CLEANUP_DOMAIN,
        )
        for item in classifications:
            action = item.action
            if item.semantic_class == CLASS_GENERIC_LEAF:
                authorized, detail = self.authorize_path(action.path, snapshot)
                if not authorized:
                    result.refused.append({**action.to_dict(), "refusal": detail})
                    continue
                record_or_reraise(
                    result,
                    action,
                    lambda action=action: remove_planned_outcome(
                        action, anchor=plan.workspace
                    ),
                )
                continue
            # Unreachable while the preflight above and this branch declare the
            # same one class. It is written as a positive branch plus a
            # fail-closed residual anyway, so that widening the declared domain
            # without adding a handler raises here instead of silently turning
            # the loop body into a generic fallback.
            raise StorageEngineDomainError(
                f"the default cleanup engine has no handler for the "
                f"{item.semantic_class!r} class of {action.action} {action.path}; "
                "no action was attempted"
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


#: The bounded identity dimensions ordinary plan revalidation binds a target on.
#: The consequential mutation boundary observes exactly these, no fewer: if plan
#: revalidation later strengthens its identity, this must not silently become
#: the weaker of the two checks. ``action.size_bytes`` is separate aggregate
#: accounting and never substitutes for the identity field.
TARGET_IDENTITY_DIMENSIONS = ("kind", "device", "inode", "size_bytes", "mtime_ns")


class _UnanchoredTarget(RuntimeError):
    """A consequential target is not beneath the anchor it must descend from."""


def _observed_identity(stats: os.stat_result) -> dict[str, Any]:
    """The plan's identity dimensions, from one no-follow observation."""

    mode = stats.st_mode
    if stat.S_ISLNK(mode):
        kind = "symlink"
    elif stat.S_ISREG(mode):
        kind = "file"
    elif stat.S_ISDIR(mode):
        kind = "directory"
    else:
        kind = "other"
    return {
        "kind": kind,
        "device": int(stats.st_dev),
        "inode": int(stats.st_ino),
        "size_bytes": int(stats.st_size),
        "mtime_ns": int(stats.st_mtime_ns),
    }


def _identity_contradiction(
    observed: Mapping[str, Any], expected: Mapping[str, Any] | None
) -> str:
    """Which plan-bound dimensions the live object fails to reproduce."""

    if not expected:
        return ""
    differing = [
        key
        for key in TARGET_IDENTITY_DIMENSIONS
        if key in expected and observed.get(key) != expected.get(key)
    ]
    return ", ".join(differing)


def _owner_identity_contradiction(
    stats: os.stat_result, expected: Mapping[str, int] | None
) -> str:
    """Whether an opened directory is the owner-certified filesystem object.

    The owner's ``root_identity``/``authority_identity`` and the plan's own
    target identity are independent constraints; each may only narrow authority
    and neither ever stands in for the other.
    """

    if expected is None:
        return ""
    if not stat.S_ISDIR(stats.st_mode):
        return "kind"
    differing = []
    if int(stats.st_dev) != int(expected["device"]):
        differing.append("device")
    if int(stats.st_ino) != int(expected["inode"]):
        differing.append("inode")
    return ", ".join(differing)


def _descend_to_parent(
    anchor: Path, target: Path, scope: "_DescriptorScope"
) -> tuple[int, str]:
    """Open ``target``'s parent by componentwise no-follow descent from ``anchor``.

    The root of this chain is justified rather than merely convenient. The
    anchor is the campaign workspace root the plan itself is bound to, and
    :meth:`StorageExecutor.run` holds the storage-operation lease and every
    touched owner's activity/publication barrier across revalidation and
    mutation - so it is retained under the frozen owner+synchronization
    contract, which is exactly what an authenticated root of trust means here.
    It is also the same discipline the accepted P7 acquisition already uses.

    Every component below it is opened ``O_DIRECTORY|O_NOFOLLOW`` relative to
    the descriptor of the parent that was already authenticated, and each hop is
    put through the same opened-descriptor mount decision the recursions use.
    That is what makes the chain continuous. Re-opening ``path.parent`` - or
    ``path.parent.parent`` - by pathname would be a fresh multi-component
    namespace resolution wearing a no-follow final component: it proves
    something about the object it opened and nothing about the object the plan
    authorized.
    """

    from .trust import (
        MountBoundaryError,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    anchor_absolute = Path(os.path.abspath(os.fspath(anchor)))
    absolute = Path(os.path.abspath(os.fspath(target)))
    try:
        relative = absolute.relative_to(anchor_absolute)
    except ValueError as exc:
        raise _UnanchoredTarget(
            f"{absolute} is not beneath the campaign anchor {anchor_absolute}"
        ) from exc
    if not relative.parts:
        raise _UnanchoredTarget(f"{absolute} is the campaign anchor itself")

    parent_fd = scope.adopt(
        open_directory_nofollow(str(anchor_absolute)), anchor_absolute
    )
    display = anchor_absolute
    for part in relative.parts[:-1]:
        display = display / part
        child_fd = scope.adopt(open_directory_nofollow(part, dir_fd=parent_fd), display)
        crossed, detail = verify_opened_directory_trust(parent_fd, child_fd, display)
        if crossed:
            raise MountBoundaryError(f"{display}: {detail}")
        parent_fd = child_fd
    return parent_fd, relative.parts[-1]


def remove_planned_outcome(action: Any, *, anchor: Path) -> MutationOutcome:
    """The consequential removal, spent only on the object the plan bound.

    Ordinary plan revalidation happened earlier and by pathname. A same-name
    object substituted afterwards would otherwise inherit that action's
    permission, so the live target is observed no-follow through an
    authenticated parent descriptor and compared against
    ``PlannedAction.filesystem_identity`` immediately before the destructive
    syscall - and the syscall is issued relative to that same descriptor, which
    then carries the directory-entry durability step.

    No new identity schema is introduced: the binding the plan already owns is
    the one spent here.
    """

    from .trust import MountBoundaryError, NamespaceAmbiguity

    path = Path(action.path)
    expected = dict(getattr(action, "filesystem_identity", None) or {})
    if not expected:
        raise StorageExecutionError(
            f"{path} reached the consequential removal boundary without the plan's "
            "target identity; a consequential action is never removed unbound"
        )
    if str(expected.get("kind", "")) == "absent":
        return already_absent("the plan bound this target as already absent")

    ledger = MutationLedger()
    scope = _DescriptorScope(ledger)
    primary: BaseException | None = None
    outcome: MutationOutcome | None = None
    try:
        try:
            parent_fd, name = _descend_to_parent(anchor, path, scope)
        except FileNotFoundError:
            raise _ScopeExit(
                already_absent("the planned target's authenticated ancestry is gone")
            )
        except (
            NamespaceAmbiguity,
            MountBoundaryError,
            _UnanchoredTarget,
            OSError,
        ) as exc:
            raise _ScopeExit(
                refused_no_change(
                    f"{path} could not be reached through an authenticated descent "
                    f"from the campaign anchor: {exc}"
                )
            )
        outcome = _spend_planned_capability(
            parent_fd, name, path, expected, ledger, scope
        )
    except _ScopeExit as exit_:
        outcome = exit_.outcome
    except BaseException as exc:  # noqa: BLE001 - re-raised after closing
        primary = exc
    primary = scope.close_all(primary)
    if primary is not None:
        raise primary
    assert outcome is not None
    return outcome


def _spend_planned_capability(
    parent_fd: int,
    name: str,
    display: Path,
    expected: Mapping[str, Any],
    ledger: MutationLedger,
    scope: "_DescriptorScope",
) -> MutationOutcome:
    """Compare, then mutate, then persist - all through the same parent."""

    from .trust import (
        MountBoundaryError,
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    try:
        stats = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return already_absent("the planned target was already gone")
    except OSError as exc:
        return refused_no_change(f"the planned target could not be observed: {exc}")
    differing = _identity_contradiction(_observed_identity(stats), expected)
    if differing:
        return refused_no_change(
            f"{display} is no longer the object this action was planned against "
            f"({differing} differ); the replacement is retained"
        )

    if not stat.S_ISDIR(stats.st_mode):
        _unlink_measured_file(display, stats, ledger, dir_fd=parent_fd)
        return removed("removed", removed_bytes=ledger.removed_bytes)

    if not dir_fd_mutation_supported():
        raise StorageExecutionError(
            "this platform does not provide the no-follow directory-descriptor "
            f"primitives recursive removal is built on, so {display} is retained "
            "rather than removed by pathname"
        )
    try:
        handle = scope.adopt(
            open_directory_nofollow(name, dir_fd=parent_fd), display
        )
    except FileNotFoundError:
        return already_absent("the planned target was already gone")
    except NamespaceAmbiguity as exc:
        return refused_no_change(
            f"{display} could not be opened as the plain directory the plan bound: {exc}"
        )
    # The comparison above was of a directory *entry*. This one is of the
    # descriptor the recursion will actually enumerate and remove through, which
    # is the capability the rest of this action spends.
    differing = _identity_contradiction(_observed_identity(os.fstat(handle)), expected)
    if differing:
        return refused_no_change(
            f"{display} is no longer the directory this action was planned against "
            f"({differing} differ); the replacement is retained"
        )
    crossed, detail = verify_opened_directory_trust(parent_fd, handle, display)
    if crossed:
        # Surfaced as a failure rather than a quiet refusal, exactly as the
        # generic recursion has always surfaced a mounted root: an authorized
        # target that turns out to belong to someone else stops the execution
        # instead of being filed as one unremarkable skipped action.
        raise ledger.failure(
            MountBoundaryError(f"{display}: {detail}"),
            f"{display} is not campaign-owned: {detail}",
        )
    _remove_tree_contents(handle, display, ledger)
    _finalize_directory_removal(parent_fd, name, handle, display, ledger)
    _persist_entry_removal(parent_fd, display, ledger)
    return removed("removed", removed_bytes=ledger.removed_bytes)


def _persist_entry_removal(
    parent_fd: int, display: Path, ledger: MutationLedger
) -> None:
    """Persist a directory-entry removal through the fd that performed it.

    Closing the authenticated parent and reopening ``path.parent`` by pathname
    for the authoritative fsync would persist whichever directory now answers to
    that name - possibly a replacement this execution never removed anything
    from. A failure here is a structured partial mutation carrying this action's
    exact bytes; it is never a no-change refusal, because the entry is already
    gone from the live namespace.
    """

    try:
        os.fsync(parent_fd)
    except OSError as exc:
        raise ledger.failure(
            exc,
            f"{display} was removed but the removal could not be made durable: {exc}",
        ) from exc


def _unlink_measured_file(
    path: Path,
    stats: os.stat_result,
    ledger: MutationLedger,
    *,
    dir_fd: int | None = None,
) -> None:
    """Unlink one already-measured non-directory, crediting only a real removal.

    The primitive reports whether *this* call's unlink syscall succeeded, and
    that is the only evidence used. Asking the filesystem afterwards whether the
    name is gone cannot answer the question that matters: a name this execution
    failed to unlink can be absent because another actor removed it, and a name
    it did unlink can be present again because another actor recreated it.
    Either reading transfers someone else's transition into this action's audit.

    ``dir_fd`` carries the authenticated parent capability through both the
    unlink and the directory-entry fsync that follows it, so a consequential
    removal never widens back to a pathname resolution once that capability
    exists.
    """

    size = int(stats.st_size)
    identity = (int(stats.st_dev), int(stats.st_ino))
    unlinked = False

    def _mark_unlinked() -> None:
        nonlocal unlinked
        unlinked = True
        ledger.credit(size, identity)

    try:
        durable_unlink(
            path, dir_fd=dir_fd, missing_ok=False, on_unlinked=_mark_unlinked
        )
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
    # The parent stays open all the way through the final `rmdir` *and* the
    # directory-entry fsync that persists it. Closing it once the child was
    # acquired would mean both had to name the root by pathname again - a second
    # namespace resolution, and exactly the lookup the descent was built to
    # avoid.
    primary: BaseException | None = None
    try:
        _remove_tree_from_parent(parent_fd, root.name, root, ledger)
    except BaseException as exc:  # noqa: BLE001 - re-raised below
        primary = exc
    close_outcome = _close_descriptor(parent_fd, root.parent, ledger, primary)
    if close_outcome is not None:
        raise close_outcome


def _remove_tree_from_parent(
    parent_fd: int, name: str, root: Path, ledger: MutationLedger
) -> None:
    """Remove one directory tree through an already-authenticated parent.

    The single mechanism both the plan-bound consequential path and the thin
    compatibility remover use, so a directory entry is always removed and
    persisted through the same descriptor that authenticated it.
    """

    from .trust import (
        MountBoundaryError,
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    primary: BaseException | None = None
    try:
        handle = open_directory_nofollow(name, dir_fd=parent_fd)
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
        _finalize_directory_removal(parent_fd, name, handle, root, ledger)
        _persist_entry_removal(parent_fd, root, ledger)
    except BaseException as exc:  # noqa: BLE001 - re-raised below
        primary = exc
    primary = _close_descriptor(handle, root, ledger, primary)
    if primary is not None:
        raise primary


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
                # The structured refusal is constructed *before* the descriptor
                # is released, so this action's already-mutated prefix travels
                # with it. A raw close here would let a close failure escape as
                # a bare `OSError`, outside the `MutationLedger` transport, and
                # the audit would lose the bytes this action had already taken.
                child_primary = ledger.failure(
                    MountBoundaryError(f"{child}: {detail}"),
                    f"{child} is not campaign-owned: {detail}",
                )
                child_primary = _close_descriptor(
                    child_handle, child, ledger, child_primary
                )
                raise child_primary
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
    anchor: Path,
    planned_identity: Mapping[str, Any],
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

    The authority root and the container are *opened* through the authenticated
    descent from the campaign anchor and compared as descriptors, not re-observed
    by pathname and then reopened. A pathname ``lstat`` proves a fact about
    whatever answered that name a moment ago; the descriptor this action then
    enumerates and unlinks through is the only thing worth checking.

    ``planned_identity`` (the plan's own binding) and ``root_identity`` /
    ``authority_identity`` (the owner's) are independent constraints. Each may
    only narrow authority and neither substitutes for the other.
    """

    from .trust import (
        MountBoundaryError,
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    ledger = MutationLedger()
    scope = _DescriptorScope(ledger)
    primary: BaseException | None = None
    outcome: MutationOutcome | None = None
    try:
        try:
            authority_fd, name = _descend_to_parent(anchor, path, scope)
        except FileNotFoundError:
            raise _ScopeExit(
                already_absent("the certified container was already gone")
            )
        except (
            NamespaceAmbiguity,
            MountBoundaryError,
            _UnanchoredTarget,
            OSError,
        ) as exc:
            raise _ScopeExit(
                refused_no_change(
                    "the authority root above the certified container could not be "
                    f"reached through an authenticated descent: {exc}"
                )
            )
        differing = _owner_identity_contradiction(
            os.fstat(authority_fd), authority_identity
        )
        if differing:
            raise _ScopeExit(
                refused_no_change(
                    "the certified authority root is no longer the filesystem object "
                    f"this action was authorized against ({differing} differ); "
                    "nothing was removed"
                )
            )

        try:
            stats = os.stat(name, dir_fd=authority_fd, follow_symlinks=False)
        except FileNotFoundError:
            raise _ScopeExit(
                already_absent("the certified container was already gone")
            )
        except OSError as exc:
            raise _ScopeExit(
                refused_no_change(
                    f"the certified container could not be observed: {exc}"
                )
            )
        differing = _identity_contradiction(
            _observed_identity(stats), planned_identity
        )
        if differing:
            raise _ScopeExit(
                refused_no_change(
                    f"{path} is no longer the object this action was planned against "
                    f"({differing} differ); the replacement is retained"
                )
            )
        if not stat.S_ISDIR(stats.st_mode):
            # A certified non-directory target still spends the same plan-bound
            # capability; only the destructive primitive differs.
            _unlink_measured_file(path, stats, ledger, dir_fd=authority_fd)
            raise _ScopeExit(
                removed(
                    "every descendant was covered by the owner's closed-subtree "
                    "certification",
                    removed_bytes=ledger.removed_bytes,
                )
            )
        if not dir_fd_mutation_supported():
            raise StorageExecutionError(
                "this platform does not provide the no-follow directory-descriptor "
                f"primitives recursive removal is built on, so {path} is retained "
                "rather than removed by pathname"
            )
        try:
            container_fd = scope.adopt(
                open_directory_nofollow(name, dir_fd=authority_fd), path
            )
        except FileNotFoundError:
            raise _ScopeExit(
                already_absent("the certified container was already gone")
            )
        except (NamespaceAmbiguity, OSError) as exc:
            raise _ScopeExit(
                refused_no_change(f"the certified container could not be opened: {exc}")
            )
        crossed, detail = verify_opened_directory_trust(authority_fd, container_fd, path)
        if crossed:
            if refusals:
                # The individually-authorized descent reports a container it may
                # not enter as a plain no-change refusal; the rest of the
                # execution is unaffected by one retained container.
                raise _ScopeExit(
                    refused_no_change(f"{path} is not campaign-owned: {detail}")
                )
            # The fully-certified recursion surfaces a mounted root as a failure,
            # like the generic one: a whole authorized subtree that turns out to
            # belong to someone else is not an unremarkable skipped action.
            raise ledger.failure(
                MountBoundaryError(f"{path}: {detail}"),
                f"{path} is not campaign-owned: {detail}",
            )
        opened = os.fstat(container_fd)
        differing = _owner_identity_contradiction(opened, root_identity)
        if differing:
            raise _ScopeExit(
                refused_no_change(
                    "the certified container is no longer the filesystem object this "
                    f"action was authorized against ({differing} differ); nothing "
                    "was removed"
                )
            )
        differing = _identity_contradiction(_observed_identity(opened), planned_identity)
        if differing:
            raise _ScopeExit(
                refused_no_change(
                    f"{path} is no longer the directory this action was planned "
                    f"against ({differing} differ); the replacement is retained"
                )
            )

        if refusals:
            outcome = _remove_authorized_members(
                container_fd, path, members, refusals, member_authorities, ledger, scope
            )
        else:
            _remove_tree_contents(container_fd, path, ledger)
            _finalize_directory_removal(authority_fd, name, container_fd, path, ledger)
            _persist_entry_removal(authority_fd, path, ledger)
            outcome = removed(
                "every descendant was covered by the owner's closed-subtree "
                "certification",
                removed_bytes=ledger.removed_bytes,
            )
    except _ScopeExit as exit_:
        outcome = exit_.outcome
    except BaseException as exc:  # noqa: BLE001 - re-raised after closing
        primary = exc
    primary = scope.close_all(primary)
    if primary is not None:
        raise primary
    assert outcome is not None
    return outcome


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
    container_fd: int,
    path: Path,
    members: Sequence[Path],
    refusals: Sequence[tuple[Path, str]],
    member_authorities: Mapping[Path, str] | None,
    ledger: MutationLedger,
    scope: "_DescriptorScope",
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

    count = 0
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
            raise _ScopeExit(
                ledger.stop(
                    f"{member} carries no owner-certified kind, so nothing "
                    "authorizes deleting it; the container is retained"
                )
            )
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
                raise _ScopeExit(
                    ledger.stop(f"{display} is no longer a plain directory: {exc}")
                )
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
                raise _ScopeExit(
                    ledger.stop(f"{display} is not campaign-owned: {detail}")
                )
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
    detail = (
        f"retained the container and removed {count} individually authorized "
        f"member(s); {len(refusals)} descendant(s) were not owner-certified"
    )
    return ledger.stop(detail)


class _ScopeExit(Exception):
    """Leave a descriptor scope with an outcome already decided.

    The outcome travels with the exception so a nested step can decide it
    without a shared mutable slot, and so the descriptor scope stays the single
    place that ranks close failures on the way out.
    """

    def __init__(self, outcome: MutationOutcome) -> None:
        super().__init__(outcome.detail)
        self.outcome = outcome


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
    "DEFAULT_CLEANUP_DOMAIN",
    "remove_planned_outcome",
    "synchronization_for",
]
