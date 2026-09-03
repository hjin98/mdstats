"""Filesystem trust boundaries: mounts are ownership boundaries.

Lexical containment and ``realpath`` containment both say a path is *inside*
the campaign workspace.  Neither says the bytes at that path belong to the
campaign.  A bind mount, an NFS/overlay mount, or any other filesystem mounted
at a campaign-contained pathname exposes externally owned bytes through a
campaign-looking path, and a recursive delete, archive collection, or dedup
enumeration that walks into it would operate on someone else's data.

This module answers one question - *does traversing from an authorized root to
this descendant cross into a different mounted filesystem?* - and answers it
conservatively.  A different ``st_dev`` proves a crossing, but the converse
does not hold: a same-device bind mount shares the device number.  So the
mount table is consulted where the platform supplies one, and any ambiguity
(unreadable table, unsupported platform, unstattable path) retains rather than
traverses.

The resolver is injectable so acceptance tests can model a nested mount without
requiring privileged mount creation.  The authorization and traversal code that
consumes it stays production code.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

#: Where Linux publishes the live mount table.  Absence is not an error; it
#: makes mount discovery unavailable, which fails toward retention.
_MOUNTINFO = Path("/proc/self/mountinfo")


class MountBoundaryError(RuntimeError):
    """A traversal would cross a mount boundary, or the boundary is unknown."""


def _read_mount_points() -> tuple[frozenset[str], bool]:
    """Every mount point this platform reports, and whether discovery worked."""

    try:
        text = _MOUNTINFO.read_text(encoding="utf-8")
    except OSError:
        return frozenset(), False
    points: set[str] = set()
    for line in text.splitlines():
        fields = line.split(" ")
        # mountinfo: id parent major:minor root mount-point ...
        if len(fields) >= 5:
            points.add(os.path.abspath(fields[4].replace("\\040", " ")))
    return frozenset(points), True


@dataclass(frozen=True, slots=True)
class MountIdentityResolver:
    """Whether one path is itself a mount point, and its device identity.

    ``available`` reports whether the platform actually supplied a mount table.
    When it did not, every containment question below fails toward retention
    instead of trusting the device number alone.
    """

    mount_points: frozenset[str]
    available: bool

    @classmethod
    def from_platform(cls) -> "MountIdentityResolver":
        points, available = _read_mount_points()
        return cls(mount_points=points, available=available)

    def is_mount_point(self, path: Path) -> bool:
        return os.path.abspath(os.fspath(path)) in self.mount_points

    def device_of(self, path: Path) -> int | None:
        try:
            return int(Path(path).lstat().st_dev)
        except OSError:
            return None


#: The process-wide resolver.  Tests substitute a deterministic one *below* the
#: real boundary/traversal owner; the code that consumes it is unchanged.
_RESOLVER: MountIdentityResolver | None = None


def mount_resolver() -> MountIdentityResolver:
    global _RESOLVER
    if _RESOLVER is None:
        _RESOLVER = MountIdentityResolver.from_platform()
    return _RESOLVER


def set_mount_resolver(resolver: MountIdentityResolver | None) -> None:
    """Install (or clear) the mount-identity resolver."""

    global _RESOLVER
    _RESOLVER = resolver


class NamespaceAmbiguity(RuntimeError):
    """A directory entry could not be authenticated as the thing it claims to be.

    Distinct from "not there": absence is an answer, but a name that is present
    and cannot be opened as a plain directory - substituted, wrong kind,
    unreadable - is unresolved authority, and every owner that descends a tree
    has to fail closed on it rather than guess.
    """


#: The descriptor-relative primitives every no-follow recursion is built from.
#: ``shutil.rmtree(..., dir_fd=...)`` does not exist on the supported Python
#: floor (>=3.10), so the recursions are written from these directly.
_DIR_FD_PRIMITIVES = ("O_NOFOLLOW", "O_DIRECTORY")


def dir_fd_mutation_supported() -> bool:
    """Whether this platform can mutate relative to a directory descriptor.

    Without these, an authenticated directory cannot be carried through to the
    destructive syscall, and the accepted answer is to refuse rather than fall
    back to absolute-path traversal. This is what a recursive owner must check -
    not ``shutil.rmtree.avoids_symlink_attacks``, which describes `rmtree`'s own
    implementation and says nothing about a separate walker.
    """

    return (
        all(hasattr(os, name) for name in _DIR_FD_PRIMITIVES)
        and os.unlink in os.supports_dir_fd
        and os.rmdir in os.supports_dir_fd
        and os.open in os.supports_dir_fd
        and os.scandir in getattr(os, "supports_fd", frozenset())
    )


def open_directory_nofollow(name: str, *, dir_fd: int | None = None) -> int:
    """Open one directory as itself, never through a substituted entry.

    ``O_DIRECTORY|O_NOFOLLOW`` refuses a symlink or non-directory in the same
    syscall that opens the name, and opening relative to an already
    authenticated parent descriptor is what makes a descent *continuous*: a
    check followed by a fresh path lookup is two different namespace
    resolutions, and an entry swapped between them would be followed.

    This is the repository's single no-follow directory acquisition. Every
    recursive owner - the P7 released-attempt descent and the storage
    executor's generic and certified recursions - uses it, because two copies
    of a trust primitive is exactly how one of them ends up weaker than the
    other.
    """

    flags = (
        os.O_RDONLY
        | os.O_DIRECTORY
        | os.O_NOFOLLOW
        # A no-follow open still *opens* the name, and opening a FIFO for
        # reading blocks until someone opens the write end - forever, for a
        # planted node nobody writes to. An owner that can be made to hang by
        # planting a special node has not failed closed, so every authority-
        # bearing open is non-blocking and the kind is decided by ``fstat``.
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        handle = os.open(name, flags, dir_fd=dir_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise NamespaceAmbiguity(
            f"{name!r} could not be opened as a plain directory ({exc.strerror})"
        ) from exc
    try:
        if not stat.S_ISDIR(os.fstat(handle).st_mode):
            os.close(handle)
            raise NamespaceAmbiguity(f"{name!r} is not a directory")
    except OSError as exc:
        os.close(handle)
        raise NamespaceAmbiguity(
            f"{name!r} could not be identified after opening ({exc.strerror})"
        ) from exc
    return handle


def crosses_mount_boundary_at(
    parent_fd: int, name: str, display: Path
) -> tuple[bool, str]:
    """Whether entering ``name`` from ``parent_fd`` leaves the parent's filesystem.

    The descriptor-relative counterpart of :func:`crosses_mount_boundary`. The
    ancestry above ``parent_fd`` was already authenticated by the descent that
    produced it, so the only open question is this one hop - answered by
    comparing the child's device to the parent's and by asking the mount table
    about the child itself.

    A descriptor-safe descent does not make a nested mount ours: the ownership
    boundary is exactly the one R13 froze, and an unreadable or unavailable
    mount identity retains rather than traverses.
    """

    try:
        parent_device = int(os.fstat(parent_fd).st_dev)
        child = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except OSError as exc:
        return True, f"the filesystem identity of {display} is unreadable ({exc})"
    if int(child.st_dev) != parent_device:
        return True, f"{display} is on a different filesystem than its parent"
    resolver = mount_resolver()
    if resolver.is_mount_point(display):
        return True, f"{display} is a mount point beneath its authorized root"
    if not resolver.available:
        # Same device and no mount table: a same-device bind mount cannot be
        # ruled out, so retain rather than traverse.
        return True, (
            "mount discovery is unavailable on this platform, so a same-device "
            f"nested mount at {display} cannot be ruled out"
        )
    return False, ""


def crosses_mount_boundary(root: Path, candidate: Path) -> tuple[bool, str]:
    """Whether reaching ``candidate`` from ``root`` leaves ``root``'s filesystem.

    The root itself may live on a mounted filesystem; that is ordinary and
    supported.  What is refused is descending *through* a nested mount below the
    authorized root, because those bytes have a different owner.
    """

    root_absolute = Path(os.path.abspath(os.fspath(root)))
    target = Path(os.path.abspath(os.fspath(candidate)))
    if target == root_absolute:
        return False, ""
    try:
        target.relative_to(root_absolute)
    except ValueError:
        return True, f"{target} is not beneath {root_absolute}"

    resolver = mount_resolver()
    root_device = resolver.device_of(root_absolute)
    if root_device is None:
        return True, f"the filesystem identity of {root_absolute} is unreadable"

    probe = target
    while probe != root_absolute:
        if not probe.exists() and not probe.is_symlink():
            # A path that does not exist cannot be a mount point. This is the
            # ordinary case for a restore destination whose bytes are still in
            # the archive; the question is answered by its existing ancestors.
            probe = probe.parent
            continue
        device = resolver.device_of(probe)
        if device is None:
            return True, f"the filesystem identity of {probe} is unreadable"
        if device != root_device:
            return True, f"{probe} is on a different filesystem than {root_absolute}"
        if resolver.is_mount_point(probe):
            return True, f"{probe} is a mount point beneath {root_absolute}"
        if not resolver.available:
            # Same device and no mount table: a same-device bind mount cannot be
            # ruled out, so retain rather than traverse.
            return True, (
                "mount discovery is unavailable on this platform, so a same-device "
                f"nested mount beneath {root_absolute} cannot be ruled out"
            )
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    return False, ""


def iter_contained_entries(root: Path) -> Iterable[Path]:
    """Immediate children of ``root`` that do not cross a mount boundary.

    Symlinks are yielded (the caller decides whether unlinking the link object
    is authorized) but are never descended into; that rule is owned separately
    by :class:`~..storage_accounting.CampaignOwnershipBoundary`.
    """

    try:
        entries = sorted(os.scandir(root), key=lambda item: item.name)
    except OSError:
        return
    for entry in entries:
        child = Path(entry.path)
        crossed, _detail = crosses_mount_boundary(root, child)
        if crossed:
            continue
        yield child


def walk_contained(root: Path, *, on_refused: Callable[[Path, str], None] | None = None):
    """Depth-first walk of ``root`` that never crosses a nested mount boundary.

    This is the single traversal primitive every recursive storage action uses,
    so a nested mount is refused once rather than in each caller.  Refusals are
    reported through ``on_refused`` so a plan can record them truthfully instead
    of silently narrowing.
    """

    root_absolute = Path(os.path.abspath(os.fspath(root)))
    stack = [root_absolute]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError as exc:
            if on_refused is not None:
                on_refused(current, f"could not be enumerated: {exc}")
            continue
        for entry in entries:
            child = Path(entry.path)
            crossed, detail = crosses_mount_boundary(root_absolute, child)
            if crossed:
                if on_refused is not None:
                    on_refused(child, detail)
                continue
            yield child
            if entry.is_dir(follow_symlinks=False):
                stack.append(child)


__all__ = [
    "MountBoundaryError",
    "MountIdentityResolver",
    "crosses_mount_boundary",
    "iter_contained_entries",
    "mount_resolver",
    "set_mount_resolver",
    "walk_contained",
]
