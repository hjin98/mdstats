"""Deterministic interleaving of one real owner transaction with one answer.

A concurrency test that races a mutation against a loop of observations proves
whatever the scheduler happened to do.  It can pass because the interesting
interval was never sampled, and it can fail later for the same reason.  Worse,
an oracle written as "the answer is one of my two snapshots" silently asserts
that a multi-transaction mutation is atomic, which is a claim about the *test*,
not about the owner.

These helpers replace that with synchronization around the **real** publication
transaction:

* :func:`observe_during_open_publication` starts one status answer, pauses it
  inside its own open read transaction, and then runs one real owner
  publication with a short busy timeout.  The publication provably attempts to
  commit while the answer is in flight, and SQLite's rollback-journal semantics
  decide the outcome rather than the scheduler.

The observer is paused at :func:`campaign_lifecycle._binding_for`, which the
coherent owner snapshot calls *inside* its read transaction, after the
target-size head read and before any pointer row is read.  That is exactly the
window a hybrid answer would need: an implementation that read each pointer in
its own transaction would hold no lock there, and the concurrent commit would
succeed instead of being excluded.

No production sleep, poll, or synchronization primitive is added for any of
this: the pause is a test-only wrapper around one module-level function, and the
mutation runs the real owner's real transaction.
"""

from __future__ import annotations

import contextlib
import sqlite3
import threading
from typing import Any, Callable

from mdstats.training_data import campaign_lifecycle as lifecycle_module

#: How long a barrier waits before declaring the interleaving did not happen.
_BARRIER_TIMEOUT = 120.0

#: The writer's busy timeout while it races one open read transaction.  It is
#: deliberately short: the outcome under test is *whether* the commit is
#: excluded, and waiting 30 s to find out would only slow the answer down.
_WRITER_BUSY_TIMEOUT_MS = 250


@contextlib.contextmanager
def _paused_inside_the_read_transaction():
    """Hold the first owner snapshot open, inside its read transaction."""

    reached = threading.Event()
    release = threading.Event()
    original = lifecycle_module._binding_for

    def hooked(revision: Any) -> Any:
        result = original(revision)
        if not reached.is_set():
            reached.set()
            release.wait(timeout=_BARRIER_TIMEOUT)
        return result

    lifecycle_module._binding_for = hooked
    try:
        yield reached, release
    finally:
        lifecycle_module._binding_for = original


def observe_during_open_publication(
    observe: Callable[[], Any], publish: Callable[[Any], None], store: Any
) -> tuple[Any, str]:
    """One answer, taken while one real publication tries to commit.

    ``observe`` is the public status answer under test; ``publish`` performs one
    real owner publication on ``store``.  Returns the answer and either
    ``"excluded"`` -- the commit could not land inside the in-flight answer, so
    no pointer this answer read could have moved underneath it -- or
    ``"committed"``.

    ``"committed"`` is not a test failure by itself; it is reported so the
    caller can assert the property its owner really guarantees.
    """

    # A short busy timeout on the writer's own thread-local connection.  The
    # store's 30 s default is right for a real operator and useless here.
    store._connect().execute(f"PRAGMA busy_timeout={_WRITER_BUSY_TIMEOUT_MS}")

    answer: list[Any] = []
    failure: list[BaseException] = []

    def run_observer() -> None:
        try:
            answer.append(observe())
        except BaseException as exc:  # noqa: BLE001 - re-raised on the main thread
            failure.append(exc)

    with _paused_inside_the_read_transaction() as (reached, release):
        watcher = threading.Thread(target=run_observer, name="status-answer")
        watcher.start()
        try:
            assert reached.wait(timeout=_BARRIER_TIMEOUT), (
                "the observer never opened its coherent read transaction"
            )
            try:
                publish(store)
                outcome = "committed"
            except sqlite3.OperationalError as exc:
                if "locked" not in str(exc) and "busy" not in str(exc):
                    raise
                store._connect().rollback()
                outcome = "excluded"
        finally:
            release.set()
            watcher.join(timeout=_BARRIER_TIMEOUT)
    if failure:
        raise failure[0]
    assert answer, "the observer produced no answer"
    return answer[0], outcome


__all__ = ["observe_during_open_publication"]
