"""The one canonical consequential cleanup destructive implementation.

Ordinary cleanup and released-P7 cleanup remove bytes through this module and
through nothing else.  Before it there were three recursions - a generic one, a
certified-subtree one, and a P7-owned one - each independently owning no-follow
descent, mount decisions, target identity, durability, descriptor lifetime,
partial-mutation transport, and byte accounting.  Keeping three copies of that
agreement is the mechanism by which one of them drifts.

What differs between the callers is *authority*, not mechanics:

``P7``
    a live released-attempt session has already authenticated the parent
    directory, so the destructive unit is entered through the descriptor it
    holds;
``ordinary cleanup``
    no owner-specific parent exists, so the unit's parent is authenticated by
    componentwise no-follow descent from the campaign anchor the plan is bound
    to.

Both then spend the same capability the same way: compare the plan-bound target
identity through the authenticated parent, refuse anything the owner did not
certify, and mutate relative to descriptors only.

Two facts are kept apart throughout, because they genuinely come apart: whether
this execution destroyed anything, and how many bytes that accounted for.
Unlinking a zero-byte file, removing an emptied directory, or dropping one more
hard link to an already-counted inode all change the namespace while crediting
nothing.
"""

from __future__ import annotations

import logging
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .outcome import (
    MutationLedger,
    MutationOutcome,
    already_absent,
    refused_no_change,
    removed,
)
#: The one node-kind vocabulary in the package, shared with the owner views so
#: an owner's certified kind and an observed kind are literally comparable.
from .owners import (
    NODE_ABSENT,
    NODE_DIRECTORY,
    NODE_FILE,
    NODE_OTHER,
    NODE_SYMLINK,
)
from .trust import dir_fd_mutation_supported

#: Secondary failure evidence - a descriptor close that failed while a primary
#: product failure was already propagating - is logged rather than raised, so it
#: is visible without displacing the failure that carries the mutation truth.
_LOGGER = logging.getLogger(__name__)

#: The bounded identity dimensions ordinary plan revalidation binds a target on.
#: The consequential mutation boundary observes exactly these, no fewer: if plan
#: revalidation later strengthens its identity, this must not silently become
#: the weaker of the two checks. ``action.size_bytes`` is separate aggregate
#: accounting and never substitutes for the identity field.
TARGET_IDENTITY_DIMENSIONS = ("kind", "device", "inode", "size_bytes", "mtime_ns")


class RemovalError(RuntimeError):
    """A consequential removal could not be attempted at all."""


class _UnanchoredTarget(RuntimeError):
    """A consequential target is not beneath the anchor it must descend from."""


# ---------------------------------------------------------------------------
# owner authority over a destructive unit
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Certification:
    """The whole-unit authority an owner grants over one destructive unit.

    A recursive delete is authority over everything that vanishes with it, so
    every node the walk encounters is checked against this *while mutating*,
    not only when the plan was built.  A node that appeared after certification,
    or changed kind since, contradicts the authority rather than inheriting it.

    ``nodes`` is the owner's typed node set, keyed by path relative to the
    authority the owner certified against; ``prefix`` is what those keys carry
    ahead of the unit's own contents, so an owner that certified an attempt root
    can authorize one member of it without re-keying its proof.  ``root_kind``
    is the kind the owner recorded for the unit itself, when the owner records
    it at all.

    ``exclusive`` replaces the node set for an area whose only writer is the
    owner: enumerating a member set there would be circular, and exclusivity is
    itself the ownership statement.  It still refuses anything that owner cannot
    have written - a symlink or a special node is never made owned by having a
    familiar name.
    """

    nodes: Mapping[str, str] | None = None
    prefix: str = ""
    root_kind: str | None = None
    exclusive: bool = False
    #: The filesystem identity the owner certified for the unit itself.
    root_identity: Mapping[str, int] | None = None
    #: The filesystem identity the owner certified for the authority root above
    #: the unit.  Independent of the plan's own target binding: each may only
    #: narrow authority and neither ever stands in for the other.
    authority_identity: Mapping[str, int] | None = None

    def certifies(self, relative: str, kind: str) -> str:
        """``""`` when this owner certifies ``relative`` as ``kind``, else why not."""

        if kind in (NODE_SYMLINK, NODE_OTHER):
            return f"a {kind} is never a node this owner certified"
        if self.exclusive:
            if kind in (NODE_FILE, NODE_DIRECTORY):
                return ""
            return f"a {kind} is never collected as an owned member"
        recorded = (self.nodes or {}).get(f"{self.prefix}{relative}")
        if recorded is None:
            return f"a {kind} this owner did not record"
        if recorded != kind:
            return (
                f"the owner recorded a {recorded} here but this is a {kind}; a "
                "same-name substitution is not the node it certified"
            )
        return ""


# ---------------------------------------------------------------------------
# identity
# ---------------------------------------------------------------------------


def observed_identity(stats: os.stat_result) -> dict[str, Any]:
    """The plan's identity dimensions, from one no-follow observation."""

    mode = stats.st_mode
    if stat.S_ISLNK(mode):
        kind = NODE_SYMLINK
    elif stat.S_ISREG(mode):
        kind = NODE_FILE
    elif stat.S_ISDIR(mode):
        kind = NODE_DIRECTORY
    else:
        kind = NODE_OTHER
    return {
        "kind": kind,
        "device": int(stats.st_dev),
        "inode": int(stats.st_ino),
        "size_bytes": int(stats.st_size),
        "mtime_ns": int(stats.st_mtime_ns),
    }


def identity_contradiction(
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


def owner_identity_contradiction(
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


# ---------------------------------------------------------------------------
# descriptors
# ---------------------------------------------------------------------------


def close_descriptor(
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


def release_descriptor_behind(handle: int, display: Path, decided: str) -> None:
    """Close one descriptor once, behind an already-decided refusal.

    Raising here would replace the classification the caller records and, on a
    mutating path, the mutation truth that travels with it.
    """

    try:
        os.close(handle)
    except OSError as exc:
        _LOGGER.warning(
            "storage: releasing the descriptor for %s failed while a refusal "
            "(%s) was already decided; the refusal is preserved",
            display,
            decided,
            exc_info=exc,
        )


class DescriptorScope:
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

    def close_all(self, primary: BaseException | None) -> BaseException | None:
        while self._open:
            handle, display = self._open.pop()
            primary = close_descriptor(handle, display, self._ledger, primary)
        return primary

    def release_all_behind(self, decided: str) -> None:
        """Release everything behind an outcome this action has already earned.

        A close that fails once a refusal is decided is secondary evidence: the
        outcome carries why the action stopped and how much of it is already
        gone, and replacing it with an ``OSError`` about a descriptor would lose
        exactly that.
        """

        while self._open:
            handle, display = self._open.pop()
            release_descriptor_behind(handle, display, decided)


def descend_to_parent(
    anchor: Path, target: Path, scope: DescriptorScope
) -> tuple[int, str]:
    """Open ``target``'s parent by componentwise no-follow descent from ``anchor``.

    The root of this chain is justified rather than merely convenient. The
    anchor is the campaign workspace root the plan itself is bound to, and
    :meth:`StorageExecutor.run` holds the storage-operation lease and every
    touched owner's activity/publication barrier across revalidation and
    mutation - so it is retained under the frozen owner+synchronization
    contract, which is exactly what an authenticated root of trust means here.
    It is also the same discipline the P7 acquisition already uses.

    Every component below it is opened ``O_DIRECTORY|O_NOFOLLOW`` relative to
    the descriptor of the parent that was already authenticated, and each hop is
    put through the same opened-descriptor mount decision the walk uses. That is
    what makes the chain continuous. Re-opening ``path.parent`` - or
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


# ---------------------------------------------------------------------------
# the destructive transitions
# ---------------------------------------------------------------------------


def unlink_certified_entry(
    parent_fd: int,
    name: str,
    display: Path,
    stats: os.stat_result,
    ledger: MutationLedger,
) -> None:
    """The one destructive transition for a certified non-directory entry.

    Every cleanup unlink in the product happens here, relative to the descriptor
    that authenticated the entry's parent, and the ledger is updated from this
    call's own syscall the moment it succeeds. Asking the filesystem afterwards
    whether the name is gone cannot answer the question that matters: a name
    this execution failed to unlink can be absent because another actor removed
    it, and a name it did unlink can be present again because another actor
    recreated it. Either reading transfers someone else's transition into this
    action's audit.

    The size is read before the unlink - afterwards there is nothing left to
    read - but credited only once the entry has actually gone, so a failed
    unlink cannot inflate the figure.
    """

    try:
        os.unlink(name, dir_fd=parent_fd)
    except OSError as exc:
        raise ledger.failure(exc, f"{display} could not be removed: {exc}") from exc
    if stat.S_ISLNK(stats.st_mode):
        # The link entry itself is removed; its target never is, and no byte of
        # the target may be credited to this action.
        ledger.note_mutation()
        return
    ledger.credit(int(stats.st_size), (int(stats.st_dev), int(stats.st_ino)))


def persist_entry_removal(
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


def _finalize_directory_removal(
    parent_fd: int, name: str, handle: int, display: Path, ledger: MutationLedger
) -> str:
    """Spend the authenticated capability on the entry it actually describes.

    ``rmdir`` names an entry, so the descriptor that authenticated this
    directory is compared against that entry one last time, immediately before
    the syscall and relative to the parent this descent authenticated. A
    substituted name is refused instead of removed; nothing is re-resolved by
    absolute path.

    Returns ``""`` when the directory is gone, or the contradiction that stopped
    it.  Stopping is a real outcome rather than a failure to report: by then the
    directory's certified children may already be unlinked.
    """

    from .trust import verify_final_directory_identity

    same, why = verify_final_directory_identity(parent_fd, name, handle, display)
    if not same:
        return why
    try:
        os.rmdir(name, dir_fd=parent_fd)
    except OSError as exc:
        return f"{display} could not be removed: {exc}"
    # An emptied directory that is now gone is a destructive transition even
    # though a directory entry credits no bytes under the planner's metric.
    ledger.note_mutation()
    return ""


def _empty_certified_directory(
    handle: int,
    display: Path,
    certification: Certification,
    prefix: str,
    ledger: MutationLedger,
) -> str:
    """Empty one already-authenticated certified directory, descriptor-relative.

    Depth-first and bottom-up, entering each child through a no-follow open on
    the descriptor of the parent that was just authenticated: an entry replaced
    by a symlink between the classification and the open is refused here rather
    than followed out of the authorized tree.

    Anything the owner did not certify with this exact kind - and anything on
    the far side of a mount boundary - stops the removal instead of widening it,
    and the partially emptied container is retained rather than forced.
    Returns ``""`` on success or the contradiction that stopped it; a genuine
    I/O or durability failure raises through the ledger instead, because those
    carry bytes that are already gone.
    """

    from .trust import (
        NamespaceAmbiguity,
        open_directory_nofollow,
        verify_opened_directory_trust,
    )

    try:
        entries = sorted(os.scandir(handle), key=lambda item: item.name)
    except OSError as exc:
        raise ledger.failure(exc, f"{display} could not be enumerated: {exc}") from exc

    for entry in entries:
        relative = f"{prefix}{entry.name}"
        child = display / entry.name
        try:
            child_stat = entry.stat(follow_symlinks=False)
        except OSError as exc:
            # An unmeasurable node is *retained*. Deleting it and crediting zero
            # would put bytes beyond recovery that this action can never account
            # for, and if nothing else had gone yet the outcome would even read
            # as "nothing changed".
            return f"{child} could not be measured: {exc}; the container is retained"
        kind = observed_identity(child_stat)["kind"]
        why = certification.certifies(relative, kind)
        if why:
            return f"{child}: {why}; the container is retained"

        if kind != NODE_DIRECTORY:
            unlink_certified_entry(handle, entry.name, child, child_stat, ledger)
            continue

        try:
            child_handle = open_directory_nofollow(entry.name, dir_fd=handle)
        except FileNotFoundError:
            continue
        except NamespaceAmbiguity as exc:
            return f"{child} is no longer the plain directory it was observed as: {exc}"
        primary: BaseException | None = None
        stopped = ""
        try:
            crossed, detail = verify_opened_directory_trust(handle, child_handle, child)
            if crossed:
                stopped = f"{child} is not campaign-owned: {detail}"
            else:
                stopped = _empty_certified_directory(
                    child_handle, child, certification, f"{relative}/", ledger
                )
                if not stopped:
                    stopped = _finalize_directory_removal(
                        handle, entry.name, child_handle, child, ledger
                    )
        except BaseException as exc:  # noqa: BLE001 - re-raised after the close
            primary = exc
        if primary is None and stopped:
            # The structured refusal is decided *before* the descriptor is
            # released, so this action's already-mutated prefix travels with it.
            # A close failure here is secondary evidence; letting it escape
            # would drop the bytes this action had already taken.
            release_descriptor_behind(child_handle, child, stopped)
            return stopped
        primary = close_descriptor(child_handle, child, ledger, primary)
        if primary is not None:
            raise primary

    try:
        os.fsync(handle)
    except OSError as exc:
        raise ledger.failure(
            exc,
            f"{display} was emptied but the removal could not be made durable: {exc}",
        ) from exc
    return ""


def _spend_certified_unit(
    parent_fd: int,
    name: str,
    display: Path,
    planned_identity: Mapping[str, Any],
    certification: Certification | None,
    ledger: MutationLedger,
    scope: DescriptorScope,
) -> MutationOutcome:
    """Compare, then mutate, then persist - all through the same parent."""

    from .trust import (
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

    observed = observed_identity(stats)
    differing = identity_contradiction(observed, planned_identity)
    if differing:
        return refused_no_change(
            f"{display} is no longer the object this action was planned against "
            f"({differing} differ); the replacement is retained"
        )
    kind = observed["kind"]
    if certification is not None and certification.root_kind is not None:
        if certification.root_kind != kind:
            return refused_no_change(
                f"this owner records {certification.root_kind!r} at that name, not "
                f"the {kind!r} now present; nothing was removed"
            )

    if kind != NODE_DIRECTORY:
        if kind == NODE_OTHER:
            return refused_no_change(
                f"{display} is a special node; no owner certifies one, so it is "
                "retained"
            )
        unlink_certified_entry(parent_fd, name, display, stats, ledger)
        persist_entry_removal(parent_fd, display, ledger)
        return removed("removed", removed_bytes=ledger.removed_bytes)

    if certification is None:
        # Lexical containment is not ownership. Without whole-unit authority a
        # directory is retained; a selectively reclaimable child is planned as
        # its own owner-authorized destructive unit instead.
        return refused_no_change(
            f"{display} is a directory no owner granted whole-unit authority over; "
            "it is retained rather than recursively removed"
        )
    if not dir_fd_mutation_supported():
        raise RemovalError(
            "this platform does not provide the no-follow directory-descriptor "
            f"primitives recursive removal is built on, so {display} is retained "
            "rather than removed by pathname"
        )

    try:
        handle = scope.adopt(open_directory_nofollow(name, dir_fd=parent_fd), display)
    except FileNotFoundError:
        return already_absent("the planned target was already gone")
    except NamespaceAmbiguity as exc:
        return refused_no_change(
            f"{display} could not be opened as the plain directory the plan bound: {exc}"
        )
    except OSError as exc:
        return refused_no_change(f"{display} could not be opened: {exc}")

    # The comparison above was of a directory *entry*. This one is of the
    # descriptor the walk will actually enumerate and remove through, which is
    # the capability the rest of this action spends.
    opened = os.fstat(handle)
    differing = identity_contradiction(observed_identity(opened), planned_identity)
    if differing:
        return refused_no_change(
            f"{display} is no longer the directory this action was planned against "
            f"({differing} differ); the replacement is retained"
        )
    crossed, detail = verify_opened_directory_trust(parent_fd, handle, display)
    if crossed:
        return refused_no_change(f"{display} is not campaign-owned: {detail}")
    differing = owner_identity_contradiction(opened, certification.root_identity)
    if differing:
        return refused_no_change(
            "the certified container is no longer the filesystem object this action "
            f"was authorized against ({differing} differ); nothing was removed"
        )

    stopped = _empty_certified_directory(handle, display, certification, "", ledger)
    if not stopped:
        stopped = _finalize_directory_removal(parent_fd, name, handle, display, ledger)
    if stopped:
        # A contradiction part-way through is a real outcome, and whatever this
        # action already unlinked is already gone from the live namespace: the
        # entry removals owe the same durability step a clean removal does.
        if ledger.mutated:
            persist_entry_removal(parent_fd, display, ledger)
        return ledger.stop(stopped)
    persist_entry_removal(parent_fd, display, ledger)
    return removed("removed", removed_bytes=ledger.removed_bytes)


# ---------------------------------------------------------------------------
# the two entry points
# ---------------------------------------------------------------------------


def remove_certified_unit(
    parent_fd: int,
    name: str,
    display: Path,
    *,
    planned_identity: Mapping[str, Any],
    certification: Certification | None,
) -> MutationOutcome:
    """Remove one destructive unit through an already-authenticated parent.

    The owner that authenticated ``parent_fd`` keeps ownership of it; only the
    descriptors this removal opens itself are closed here.
    """

    ledger = MutationLedger()
    scope = DescriptorScope(ledger)
    primary: BaseException | None = None
    outcome: MutationOutcome | None = None
    try:
        outcome = _spend_certified_unit(
            parent_fd, name, display, planned_identity, certification, ledger, scope
        )
    except BaseException as exc:  # noqa: BLE001 - re-raised after closing
        primary = exc
    if primary is None and outcome is not None and outcome.refused:
        # The refusal is this action's product answer and carries whatever it
        # had already taken. A close that fails behind it is secondary evidence;
        # replacing the refusal with an `OSError` about a descriptor would lose
        # both the reason and the bytes. A close failure after a *successful*
        # removal is not behind anything, and still surfaces as the failure it
        # is.
        scope.release_all_behind(outcome.detail)
        return outcome
    primary = scope.close_all(primary)
    if primary is not None:
        raise primary
    assert outcome is not None
    return outcome


def remove_planned_target(
    action: Any,
    *,
    anchor: Path,
    certification: Certification | None = None,
) -> MutationOutcome:
    """The consequential removal, spent only on the object the plan bound.

    Ordinary plan revalidation happened earlier and by pathname. A same-name
    object substituted afterwards would otherwise inherit that action's
    permission, so the unit's parent is authenticated by continuous no-follow
    descent from the campaign anchor, the live target is compared against
    ``PlannedAction.filesystem_identity`` immediately before the destructive
    syscall, and the syscall is issued relative to that same descriptor - which
    then carries the directory-entry durability step.

    No new identity schema is introduced: the binding the plan already owns is
    the one spent here.
    """

    from .trust import MountBoundaryError, NamespaceAmbiguity

    path = Path(action.path)
    expected = dict(getattr(action, "filesystem_identity", None) or {})
    if not expected:
        raise RemovalError(
            f"{path} reached the consequential removal boundary without the plan's "
            "target identity; a consequential action is never removed unbound"
        )
    if str(expected.get("kind", "")) == NODE_ABSENT:
        return already_absent("the plan bound this target as already absent")

    ledger = MutationLedger()
    scope = DescriptorScope(ledger)
    primary: BaseException | None = None
    outcome: MutationOutcome | None = None
    try:
        try:
            parent_fd, name = descend_to_parent(anchor, path, scope)
        except FileNotFoundError:
            outcome = already_absent(
                "the planned target's authenticated ancestry is gone"
            )
        except (
            NamespaceAmbiguity,
            MountBoundaryError,
            _UnanchoredTarget,
            OSError,
        ) as exc:
            outcome = refused_no_change(
                f"{path} could not be reached through an authenticated descent "
                f"from the campaign anchor: {exc}"
            )
        else:
            differing = (
                owner_identity_contradiction(
                    os.fstat(parent_fd), certification.authority_identity
                )
                if certification is not None
                and certification.authority_identity is not None
                else ""
            )
            outcome = (
                refused_no_change(
                    "the certified authority root is no longer the filesystem "
                    f"object this action was authorized against ({differing} "
                    "differ); nothing was removed"
                )
                if differing
                else _spend_certified_unit(
                    parent_fd, name, path, expected, certification, ledger, scope
                )
            )
    except BaseException as exc:  # noqa: BLE001 - re-raised after closing
        primary = exc
    if primary is None and outcome is not None and outcome.refused:
        # The refusal is this action's product answer and carries whatever it
        # had already taken. A close that fails behind it is secondary evidence;
        # replacing the refusal with an `OSError` about a descriptor would lose
        # both the reason and the bytes. A close failure after a *successful*
        # removal is not behind anything, and still surfaces as the failure it
        # is.
        scope.release_all_behind(outcome.detail)
        return outcome
    primary = scope.close_all(primary)
    if primary is not None:
        raise primary
    assert outcome is not None
    return outcome


__all__ = [
    "TARGET_IDENTITY_DIMENSIONS",
    "Certification",
    "DescriptorScope",
    "RemovalError",
    "close_descriptor",
    "descend_to_parent",
    "identity_contradiction",
    "observed_identity",
    "owner_identity_contradiction",
    "persist_entry_removal",
    "release_descriptor_behind",
    "remove_certified_unit",
    "remove_planned_target",
    "unlink_certified_entry",
]
