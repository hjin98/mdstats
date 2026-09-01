"""Storage-operation serialization, and the owner-local race barriers.

Two different synchronization problems are deliberately kept apart.

*Storage against storage.*  :func:`storage_operation_lease` prevents two
concurrent cleanup/dedup/archive/restore mutations from interleaving.  It is an
advisory ``flock`` on one campaign-owned lock file, so a crashed holder's lock
is released by the kernel and no PID, hostname, or pathname inference is ever
needed to recover it.  Ambiguity here reduces authority: a lease that cannot be
acquired refuses the mutation rather than proceeding.

*Storage against the semantic owners.*  The lease above does **not** serialize
storage against P1-P7 writers.  A publisher that writes an immutable object and
then publishes its current pointer has a legitimate window in between, and a
naked ``is_current(); unlink()`` can lose that race.  The owner-local barriers
here are acquired by *both* the owning publisher and the storage mutation, so a
storage action either observes the complete published state or waits for it.
The barriers are narrow by construction: storage does its hashing, scanning,
and planning outside them and holds one only across revalidation and mutation.
"""

from __future__ import annotations

import errno
import fcntl
import os
from contextlib import ExitStack, contextmanager
from pathlib import Path
from typing import Any, Iterator

# The owner-local barriers live with their owners, which is where the publishers
# acquire them.  Storage re-exports them so there is exactly one implementation
# of each and no chance of two divergent lock files.
from ..post_selection_store import post_selection_publication_barrier
from ..qualification.store import qualification_publication_barrier

STORAGE_OPERATION_LOCK_NAME = "storage-operation.lock"


class StorageLeaseUnavailableError(RuntimeError):
    """Another storage operation currently owns the mutation lease."""


class _NonBlockingLease:
    """Advisory exclusive lease with a bounded acquisition timeout."""

    def __init__(self, lock_path: Path, *, timeout_seconds: float) -> None:
        self.lock_path = lock_path
        self.timeout_seconds = max(0.0, float(timeout_seconds))
        self._fd: int | None = None

    def __enter__(self) -> "_NonBlockingLease":
        import time

        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._fd = os.open(str(self.lock_path), os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644)
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                fcntl.flock(self._fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    os.close(self._fd)
                    self._fd = None
                    raise
                if time.monotonic() >= deadline:
                    os.close(self._fd)
                    self._fd = None
                    raise StorageLeaseUnavailableError(
                        "Another storage operation holds the campaign storage mutation "
                        f"lease at {self.lock_path}; overlapping storage mutations are "
                        "never interleaved. Retry once it completes."
                    ) from exc
                time.sleep(0.05)
        # The payload is diagnostic only.  Recovery never depends on reading it:
        # a crashed holder's advisory lock is released by the kernel.
        try:
            os.ftruncate(self._fd, 0)
            os.write(
                self._fd,
                f"pid={os.getpid()} ppid={os.getppid()}\n".encode("utf-8"),
            )
        except OSError:
            pass
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
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


def storage_operation_lease(control_plane: Any, *, timeout_seconds: float = 30.0):
    """Serialize consequential storage mutations with each other."""

    return _NonBlockingLease(
        Path(control_plane.lock_root) / STORAGE_OPERATION_LOCK_NAME,
        timeout_seconds=timeout_seconds,
    )


@contextmanager
def owner_mutation_barrier(paths: Any, generations: tuple[int, ...]) -> Iterator[None]:
    """Hold every owner barrier a storage mutation could race against.

    Generations are entered in a deterministic order so two storage operations
    can never deadlock against each other, and the P5 barrier is always taken
    before the P7 one for the same reason.
    """

    ordered = tuple(sorted({int(value) for value in generations}))
    if not ordered:
        yield
        return

    with ExitStack() as stack:
        for generation in ordered:
            stack.enter_context(post_selection_publication_barrier(paths, generation))
        for generation in ordered:
            stack.enter_context(qualification_publication_barrier(paths, generation))
        yield


__all__ = [
    "STORAGE_OPERATION_LOCK_NAME",
    "StorageLeaseUnavailableError",
    "owner_mutation_barrier",
    "post_selection_publication_barrier",
    "qualification_publication_barrier",
    "storage_operation_lease",
]
