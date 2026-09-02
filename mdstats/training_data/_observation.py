"""Invocation-scoped observational execution capability.

A read-only storage command must not change managed campaign state, and that is
a property of the **invocation**, not of one call site. Owner loaders reach
campaign state through several independent helpers, some of which open their own
``CampaignStore`` in order to read one record, and some of which fan byte hashing
out across worker threads. Any one of those opens could otherwise bootstrap a
schema row or write an acceleration receipt, so merely *describing* a campaign
would rewrite two managed databases.

Three properties matter and are why this is a :mod:`contextvars` capability
rather than a flag:

*It propagates downward.* Every nested helper below an observational command
sees it without being told, so a helper cannot escape observation by calling an
ordinary default-creating constructor.

*It propagates into workers.* A ``threading.local`` flag is invisible to a
thread the invocation spawns, which is exactly where the hashing fan-out lives.
:class:`ObservationalThreadPoolExecutor` and :func:`bound_to_current_context`
carry the caller's context into each worker, so a spawned worker is inside the
same capability as the code that spawned it.

*It does not race sideways.* Nothing here mutates process-global state. A
concurrent consequential command in another thread keeps its own writable
behavior while an observational command is running, because the capability lives
in the observational call's own context and nowhere else.

This module deliberately imports nothing from the package: everything that
touches managed state can depend on it without an import cycle.
"""

from __future__ import annotations

import contextvars
import functools
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from typing import Any, Callable, Iterator, TypeVar

#: True while the current execution context may not create or write managed
#: campaign state. Being a context variable rather than a thread-local is the
#: whole point: it is inherited by nested calls and can be carried into workers.
_OBSERVATIONAL: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "mdstats_observational_campaign_state", default=False
)

_T = TypeVar("_T")


def observational() -> bool:
    """Whether the current context forbids creating or writing managed state."""

    return bool(_OBSERVATIONAL.get())


@contextmanager
def observing() -> Iterator[None]:
    """Enter the observational capability for the duration of the block."""

    token = _OBSERVATIONAL.set(True)
    try:
        yield
    finally:
        _OBSERVATIONAL.reset(token)


def bound_to_current_context(function: Callable[..., _T]) -> Callable[..., _T]:
    """Wrap ``function`` so it runs inside the *calling* context.

    Used where work crosses a thread boundary. ``contextvars`` are not inherited
    by :class:`threading.Thread`, so without this a worker started by an
    observational invocation would run with the default writable capability.
    """

    context = contextvars.copy_context()

    @functools.wraps(function)
    def _run(*args: Any, **kwargs: Any) -> _T:
        return context.run(function, *args, **kwargs)

    return _run


class ObservationalThreadPoolExecutor(ThreadPoolExecutor):
    """A pool whose workers inherit the submitting context.

    Every storage fan-out uses this instead of the bare executor, so a worker
    hashing bytes for an observational report is itself observational and cannot
    write an acceleration receipt.
    """

    def submit(self, fn, /, *args, **kwargs):  # type: ignore[override]
        return super().submit(bound_to_current_context(fn), *args, **kwargs)


__all__ = [
    "ObservationalThreadPoolExecutor",
    "bound_to_current_context",
    "observational",
    "observing",
]
