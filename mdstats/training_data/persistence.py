"""Training-data-wide filesystem publication primitives.

This module is the repository's single owner of the ``fcntl.flock`` advisory
lock and of durable directory-entry fsync.  It carries no stage semantics:
P2 target-order preparation, P3 target-size execution, storage, qualification,
replay, and post-selection publication all import these primitives directly
from here rather than from one another.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
from typing import Any


def _lock_file_path(path: Path) -> Path:
    """Deterministic advisory lock file path adjacent to target."""
    return path.parent / f".{path.name}.lock"


def fsync_parent_directory(path: Path) -> None:
    """Persist a completed rename in the destination directory entry.

    This is the repository's single durable directory-entry publication
    primitive.  Storage archive/restore publication reuses it rather than
    reimplementing a divergent durability discipline.
    """

    try:
        fd = os.open(str(path.parent), os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    except OSError:
        # Some supported filesystems do not permit directory fsync.  The file
        # itself has still been flushed and the rename remains atomic.
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class _FileLock:
    """Context manager for advisory flock on a lock file."""

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._fd: int | None = None

    def __enter__(self) -> _FileLock:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(
            str(self.lock_path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644
        )
        fcntl.flock(self._fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._fd is not None:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None


def artifact_publication_lock(destination: str | Path) -> "_FileLock":
    """Advisory exclusive lock guarding one destination path's publication.

    Content-addressed records publish through create-or-verify byte equality
    and need no external lock.  An artifact produced by a *non-deterministic*
    serializer - a full PyTorch model pickle, for instance - cannot be compared
    byte-for-byte across two independent builds, so concurrent builders of the
    same logical artifact must be serialized instead.  The lock is released by
    the operating system when its holder dies, so a crashed holder never
    strands a waiter.
    """

    return _FileLock(_lock_file_path(Path(destination)))


__all__ = [
    "artifact_publication_lock",
    "fsync_parent_directory",
]
