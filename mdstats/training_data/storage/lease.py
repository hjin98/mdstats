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

import contextvars
import errno
import fcntl
import os
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

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


#: True while this execution context holds the storage-operation lease.
#:
#: Reauthenticating a retained archive immediately before consuming it is only
#: race-closed if every *supported* writer of that retained state is serialized
#: with the reader. This variable is how the control plane enforces that rather
#: than trusting each call site to be reachable only from an executor: a
#: mutation of retained catalog/archive state outside the lease is refused.
#:
#: It is not a security boundary. A process that deliberately ignores package
#: ownership and rewrites campaign files is treated as corruption, detected at
#: the next protected authentication point.
_OPERATION_LEASE_HELD: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "mdstats_storage_operation_lease_held", default=False
)


def storage_operation_lease_is_held() -> bool:
    return bool(_OPERATION_LEASE_HELD.get())


@contextmanager
def storage_operation_lease(control_plane: Any, *, timeout_seconds: float = 30.0):
    """Serialize consequential storage mutations with each other."""

    lease = _NonBlockingLease(
        Path(control_plane.lock_root) / STORAGE_OPERATION_LOCK_NAME,
        timeout_seconds=timeout_seconds,
    )
    with lease:
        token = _OPERATION_LEASE_HELD.set(True)
        try:
            yield lease
        finally:
            _OPERATION_LEASE_HELD.reset(token)


@dataclass(frozen=True, slots=True)
class OwnerSynchronization:
    """Exactly which owner seams one plan's mutations must hold.

    Derived from the *planned artifacts*, never from "whatever generation is
    current": an action that rewrites a historical ``g1`` run tree needs g1's
    seams, and taking only the current generation's barriers would fence the
    wrong owner entirely.
    """

    #: Generations whose publication barriers must be held, ascending.
    generations: tuple[int, ...] = ()
    #: P5 run roots whose activity leases must be held exclusively, sorted.
    run_roots: tuple[Path, ...] = ()
    #: P7 attempt roots whose per-attempt state locks must be held, sorted.
    #:
    #: The generation publication barrier is not the same boundary: attempt
    #: state is mutated under its own per-attempt lock, and an *aborted* attempt
    #: - which storage treats as released - may legally reopen as active. Without
    #: this seam storage could delete scratch while the attempt is reopening.
    attempt_roots: tuple[Path, ...] = ()

    @classmethod
    def of(
        cls,
        generations: Iterable[int] = (),
        run_roots: Iterable[Path] = (),
        attempt_roots: Iterable[Path] = (),
    ) -> "OwnerSynchronization":
        return cls(
            generations=tuple(sorted({int(value) for value in generations})),
            run_roots=tuple(sorted({Path(value) for value in run_roots})),
            attempt_roots=tuple(sorted({Path(value) for value in attempt_roots})),
        )

    def merged_with(self, other: "OwnerSynchronization") -> "OwnerSynchronization":
        return OwnerSynchronization.of(
            (*self.generations, *other.generations),
            (*self.run_roots, *other.run_roots),
            (*self.attempt_roots, *other.attempt_roots),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "generations": list(self.generations),
            "run_roots": [str(item) for item in self.run_roots],
        }


@contextmanager
def owner_mutation_barrier(
    paths: Any, synchronization: OwnerSynchronization
) -> Iterator[None]:
    """Hold every owner seam a storage mutation could race against.

    One order, everywhere, so storage and the owners can never deadlock against
    each other:

    ``storage-operation lease -> owner run-activity leases (path order) ->
    P5 publication barriers (generation order) -> P7 publication barriers
    (generation order) -> P7 attempt-state locks (path order) ->
    fresh revalidation -> narrow mutation``

    P5's own execution path takes the same run-activity lease before it ever
    reaches its publication barrier, so the two acquire the shared locks in the
    same direction and no cycle exists. The attempt-state lock comes last for the
    same reason: P7 acquires the generation barrier before it touches attempt
    state, never the reverse.
    """

    from ..campaign_post_selection_runtime import post_selection_run_activity_lease
    from ..qualification.store import attempt_state_lock_at

    if (
        not synchronization.generations
        and not synchronization.run_roots
        and not synchronization.attempt_roots
    ):
        yield
        return

    with ExitStack() as stack:
        for run_root in synchronization.run_roots:
            stack.enter_context(post_selection_run_activity_lease(run_root))
        for generation in synchronization.generations:
            stack.enter_context(post_selection_publication_barrier(paths, generation))
        for generation in synchronization.generations:
            stack.enter_context(qualification_publication_barrier(paths, generation))
        for attempt_root in synchronization.attempt_roots:
            stack.enter_context(attempt_state_lock_at(attempt_root))
        yield


__all__ = [
    "STORAGE_OPERATION_LOCK_NAME",
    "OwnerSynchronization",
    "StorageLeaseUnavailableError",
    "owner_mutation_barrier",
    "post_selection_publication_barrier",
    "qualification_publication_barrier",
    "storage_operation_lease",
]
