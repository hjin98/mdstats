"""Shared scene context and in-memory scientific dependency cache."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeVar

from .contracts import GraphicsDependencyKey
from .errors import Graphics3DDependencyError

T = TypeVar("T")


@dataclass(slots=True)
class GraphicsSceneContext:
    """Execution context shared by every layer in one universal scene.

    The cache is keyed only by :class:`GraphicsDependencyKey` scientific
    identity. Cache hit/miss state, resolver timing, storage location, and
    waiting on another resolver are execution evidence and are intentionally
    absent from those identities.

    GFX3D-4 adds *single-flight* resolution: concurrent requests for one
    scientific key execute its resolver exactly once. Other callers wait for
    the owning resolution and then consume the same cached object.
    """

    source: Any = None
    source_identity: str | None = None
    display_gauge: Mapping[str, Any] = field(default_factory=dict)
    resources: Any = None
    progress: Any = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    _cache: dict[str, Any] = field(default_factory=dict, init=False, repr=False)
    _lock: threading.RLock = field(default_factory=threading.RLock, init=False, repr=False)
    _inflight: dict[str, threading.Event] = field(default_factory=dict, init=False, repr=False)
    _failures: dict[str, BaseException] = field(default_factory=dict, init=False, repr=False)
    _records: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)
    _hits: int = field(default=0, init=False, repr=False)
    _misses: int = field(default=0, init=False, repr=False)
    _waits: int = field(default=0, init=False, repr=False)

    def __post_init__(self) -> None:
        self.display_gauge = MappingProxyType(dict(self.display_gauge))
        self.metadata = MappingProxyType(dict(self.metadata))

    def _record_hit_locked(self, key: GraphicsDependencyKey, *, waited: bool = False) -> None:
        self._hits += 1
        if waited:
            self._waits += 1
        record = self._records.setdefault(
            key.identity,
            {
                "provider_type": key.provider_type,
                "resolver_executions": 0,
                "cache_hits": 0,
                "wait_hits": 0,
                "resolver_wall_seconds": 0.0,
            },
        )
        record["cache_hits"] = int(record["cache_hits"]) + 1
        if waited:
            record["wait_hits"] = int(record["wait_hits"]) + 1

    def resolve_dependency(self, key: GraphicsDependencyKey, resolver: Callable[[], T]) -> T:
        if not isinstance(key, GraphicsDependencyKey):
            raise Graphics3DDependencyError("key must be GraphicsDependencyKey.")
        identity = key.identity
        owner = False
        event: threading.Event
        with self._lock:
            if identity in self._cache:
                self._record_hit_locked(key)
                return self._cache[identity]
            if identity in self._failures:
                error = self._failures[identity]
                raise Graphics3DDependencyError(
                    f"Previous resolution of GFX3D dependency {key.provider_type!r} failed."
                ) from error
            event = self._inflight.get(identity)  # type: ignore[assignment]
            if event is None:
                event = threading.Event()
                self._inflight[identity] = event
                owner = True

        if not owner:
            event.wait()
            with self._lock:
                if identity in self._cache:
                    self._record_hit_locked(key, waited=True)
                    return self._cache[identity]
                error = self._failures.get(identity)
            raise Graphics3DDependencyError(
                f"Concurrent resolution of GFX3D dependency {key.provider_type!r} failed."
            ) from error

        started = time.perf_counter()
        try:
            value = resolver()
        except Graphics3DDependencyError as error:
            with self._lock:
                self._failures[identity] = error
                self._records[identity] = {
                    "provider_type": key.provider_type,
                    "resolver_executions": 1,
                    "cache_hits": 0,
                    "wait_hits": 0,
                    "resolver_wall_seconds": float(time.perf_counter() - started),
                    "failed": True,
                }
                self._inflight.pop(identity, None)
                event.set()
            raise
        except Exception as error:
            wrapped = Graphics3DDependencyError(
                f"Failed to resolve GFX3D dependency {key.provider_type!r}."
            )
            with self._lock:
                self._failures[identity] = error
                self._records[identity] = {
                    "provider_type": key.provider_type,
                    "resolver_executions": 1,
                    "cache_hits": 0,
                    "wait_hits": 0,
                    "resolver_wall_seconds": float(time.perf_counter() - started),
                    "failed": True,
                }
                self._inflight.pop(identity, None)
                event.set()
            raise wrapped from error

        wall = time.perf_counter() - started
        with self._lock:
            self._cache[identity] = value
            self._misses += 1
            self._records[identity] = {
                "provider_type": key.provider_type,
                "resolver_executions": 1,
                "cache_hits": 0,
                "wait_hits": 0,
                "resolver_wall_seconds": float(wall),
                "failed": False,
            }
            self._inflight.pop(identity, None)
            event.set()
        return value

    def put_dependency(self, key: GraphicsDependencyKey, value: Any) -> None:
        with self._lock:
            self._cache[key.identity] = value
            self._failures.pop(key.identity, None)
            self._records.setdefault(
                key.identity,
                {
                    "provider_type": key.provider_type,
                    "resolver_executions": 0,
                    "cache_hits": 0,
                    "wait_hits": 0,
                    "resolver_wall_seconds": 0.0,
                    "failed": False,
                    "preseeded": True,
                },
            )

    def cache_report(self) -> Mapping[str, int]:
        with self._lock:
            # Preserve the GFX3D-1 public summary shape.  GFX3D-4 wait/failure
            # detail is available through dependency_report() rather than
            # changing historical callers that compare this mapping exactly.
            return MappingProxyType(
                {"entries": len(self._cache), "hits": self._hits, "misses": self._misses}
            )

    def dependency_report(self) -> Mapping[str, Mapping[str, Any]]:
        """Return execution-only dependency timing/cache evidence by key identity."""
        with self._lock:
            return MappingProxyType(
                {
                    identity: MappingProxyType(dict(record))
                    for identity, record in sorted(self._records.items())
                }
            )
