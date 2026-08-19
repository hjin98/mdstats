"""Deterministic, bounded CPU work queue for MLFF campaign stages.

PARCORE1 centralizes the execution mechanics that were first qualified in the
TARGET-DATA2B-FEAS1 PERF3 scheduler.  The queue is execution-only: task
completion order, timing, worker count, memory admission, and locality metadata
must never enter scientific digests.  Callers that require floating-point
order authority use :class:`DeterministicOrderedReducer` to commit completed
results in a canonical sequence.
"""
from __future__ import annotations

from collections import deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from threading import Lock
import time
from typing import Any, Callable, Hashable, Mapping, Sequence

from .resources import StageResourceScope, stage_resource_scope


class DeterministicWorkQueueError(RuntimeError):
    """Base error for the shared deterministic work queue."""


class DeterministicWorkQueueTaskError(DeterministicWorkQueueError):
    """A worker failed; the exception message carries the deterministic task ID."""

    def __init__(self, *, task_id: str, task_kind: str, cause: BaseException) -> None:
        self.task_id = str(task_id)
        self.task_kind = str(task_kind)
        self.cause = cause
        super().__init__(
            f"PARCORE1 task {self.task_id!r} ({self.task_kind}) failed: "
            f"{type(cause).__name__}: {cause}"
        )


class DeterministicWorkQueueMemoryError(DeterministicWorkQueueError):
    """A task or persistent reservation cannot fit the declared RAM budget."""


@dataclass(frozen=True, slots=True)
class DeterministicWorkItem:
    """One execution-only task admitted to :class:`DeterministicWorkQueue`."""

    task_id: str
    canonical_order: tuple[int, ...]
    function: Callable[..., Any] = field(repr=False, compare=False)
    args: tuple[Any, ...] = field(default_factory=tuple, repr=False, compare=False)
    kwargs: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)
    task_kind: str = "work"
    estimated_memory_bytes: int = 0
    locality_key: str | None = None

    def __post_init__(self) -> None:
        if not str(self.task_id).strip():
            raise ValueError("task_id must be non-empty")
        if not callable(self.function):
            raise TypeError("function must be callable")
        order = tuple(int(value) for value in self.canonical_order)
        if any(value < 0 for value in order):
            raise ValueError("canonical_order entries must be non-negative")
        memory = int(self.estimated_memory_bytes)
        if memory < 0:
            raise ValueError("estimated_memory_bytes must be non-negative")
        object.__setattr__(self, "task_id", str(self.task_id))
        object.__setattr__(self, "canonical_order", order)
        object.__setattr__(self, "task_kind", str(self.task_kind))
        object.__setattr__(self, "estimated_memory_bytes", memory)
        if self.locality_key is not None:
            object.__setattr__(self, "locality_key", str(self.locality_key))


@dataclass(frozen=True, slots=True)
class DeterministicWorkCompletion:
    """Completed task result before caller-side scientific reduction."""

    task_id: str
    canonical_order: tuple[int, ...]
    task_kind: str
    locality_key: str | None
    estimated_memory_bytes: int
    wall_seconds: float
    value: Any = field(repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class DeterministicWorkQueueSnapshot:
    """Execution telemetry snapshot; never scientific authority."""

    allocated_workers: int
    busy_workers: int
    max_busy_workers: int
    ready_tasks: int
    inflight_tasks: int
    completed_tasks: int
    submitted_tasks: int
    finished_tasks: int
    committed_tasks: int
    ready_memory_bytes: int
    inflight_memory_bytes: int
    completed_memory_bytes: int
    reserved_memory_bytes: int
    memory_budget_bytes: int | None
    peak_accounted_memory_bytes: int
    memory_backpressure_events: int
    queue_backpressure_events: int
    heartbeat_count: int

    @property
    def outstanding_tasks(self) -> int:
        return int(self.ready_tasks + self.inflight_tasks + self.completed_tasks)

    @property
    def accounted_memory_bytes(self) -> int:
        return int(
            self.inflight_memory_bytes
            + self.completed_memory_bytes
            + self.reserved_memory_bytes
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "allocated_workers": self.allocated_workers,
            "busy_workers": self.busy_workers,
            "max_busy_workers": self.max_busy_workers,
            "ready_tasks": self.ready_tasks,
            "inflight_tasks": self.inflight_tasks,
            "completed_tasks": self.completed_tasks,
            "submitted_tasks": self.submitted_tasks,
            "finished_tasks": self.finished_tasks,
            "committed_tasks": self.committed_tasks,
            "ready_memory_bytes": self.ready_memory_bytes,
            "inflight_memory_bytes": self.inflight_memory_bytes,
            "completed_memory_bytes": self.completed_memory_bytes,
            "reserved_memory_bytes": self.reserved_memory_bytes,
            "memory_budget_bytes": self.memory_budget_bytes,
            "peak_accounted_memory_bytes": self.peak_accounted_memory_bytes,
            "memory_backpressure_events": self.memory_backpressure_events,
            "queue_backpressure_events": self.queue_backpressure_events,
            "heartbeat_count": self.heartbeat_count,
        }


class DeterministicOrderedReducer:
    """Buffer arbitrary task completions and commit one canonical key sequence.

    The reducer intentionally knows nothing about threads.  It is a small
    scientific-order guard used by stage-specific coordinators after results
    leave the execution queue.
    """

    __slots__ = ("_buffer", "_commit", "_expected", "_index", "_known", "_position")

    def __init__(
        self,
        expected_keys: Sequence[Hashable],
        *,
        commit: Callable[[Hashable, Any], None],
    ) -> None:
        expected = tuple(expected_keys)
        if len(expected) != len(set(expected)):
            raise ValueError("ordered reducer keys must be unique")
        if not callable(commit):
            raise TypeError("commit must be callable")
        self._expected = expected
        self._known = frozenset(expected)
        self._position = {key: index for index, key in enumerate(expected)}
        self._commit = commit
        self._buffer: dict[Hashable, Any] = {}
        self._index = 0

    @property
    def buffered_count(self) -> int:
        return len(self._buffer)

    @property
    def committed_count(self) -> int:
        return int(self._index)

    @property
    def complete(self) -> bool:
        return self._index == len(self._expected) and not self._buffer

    @property
    def next_key(self) -> Hashable | None:
        if self._index >= len(self._expected):
            return None
        return self._expected[self._index]

    def push(self, key: Hashable, value: Any) -> int:
        if key not in self._known:
            raise KeyError(f"ordered reducer received unknown key {key!r}")
        if key in self._buffer:
            raise ValueError(f"ordered reducer received duplicate buffered key {key!r}")
        if self._position[key] < self._index:
            raise ValueError(f"ordered reducer received already committed key {key!r}")
        self._buffer[key] = value
        return self.commit_ready()

    def commit_ready(self) -> int:
        count = 0
        while self._index < len(self._expected):
            key = self._expected[self._index]
            if key not in self._buffer:
                break
            value = self._buffer.pop(key)
            self._commit(key, value)
            self._index += 1
            count += 1
        return count


class DeterministicWorkQueue(AbstractContextManager["DeterministicWorkQueue"]):
    """Bounded, work-conserving thread queue under one ``StageResourceScope``.

    The coordinator thread is the only thread that mutates queue structure.
    Worker threads only update the synchronized busy counter while executing a
    task.  This lets ``threadpoolctl`` remain a stage-level control rather than
    being manipulated from arbitrary workers.
    """

    def __init__(
        self,
        scope: StageResourceScope,
        *,
        max_ready_tasks: int | None = None,
        max_inflight_tasks: int | None = None,
        max_completed_tasks: int | None = None,
        heartbeat_interval_seconds: float = 30.0,
        telemetry_callback: Callable[[DeterministicWorkQueueSnapshot], None] | None = None,
        thread_name_prefix: str = "mdstats-parcore1",
        manage_resource_scope: bool = True,
    ) -> None:
        if not isinstance(scope, StageResourceScope):
            raise TypeError("scope must be a StageResourceScope")
        workers = int(scope.python_workers)
        self.scope = scope
        self.max_ready_tasks = max(1, int(max_ready_tasks if max_ready_tasks is not None else 2 * workers))
        self.max_inflight_tasks = max(1, int(max_inflight_tasks if max_inflight_tasks is not None else 2 * workers))
        self.max_completed_tasks = max(1, int(max_completed_tasks if max_completed_tasks is not None else 2 * workers))
        self.heartbeat_interval_seconds = max(0.05, float(heartbeat_interval_seconds))
        self.telemetry_callback = telemetry_callback
        self.thread_name_prefix = str(thread_name_prefix)
        self.manage_resource_scope = bool(manage_resource_scope)

        self._ready: deque[DeterministicWorkItem] = deque()
        self._inflight: dict[Future[Any], tuple[DeterministicWorkItem, float]] = {}
        self._completed: deque[DeterministicWorkCompletion] = deque()
        self._seen_task_ids: set[str] = set()
        self._reservations: dict[str, int] = {}
        self._ready_memory_bytes = 0
        self._inflight_memory_bytes = 0
        self._completed_memory_bytes = 0
        self._reserved_memory_bytes = 0
        self._executor: ThreadPoolExecutor | None = None
        self._resource_cm: Any | None = None
        self._entered = False
        self._busy = 0
        self._max_busy = 0
        self._busy_lock = Lock()
        self._submitted = 0
        self._finished = 0
        self._committed = 0
        self._memory_backpressure = 0
        self._queue_backpressure = 0
        self._heartbeat_count = 0
        self._peak_accounted_memory = 0
        self._last_telemetry = time.monotonic()

    @property
    def allocated_workers(self) -> int:
        return int(self.scope.python_workers)

    @property
    def outstanding_tasks(self) -> int:
        return len(self._ready) + len(self._inflight) + len(self._completed)

    @property
    def ready_capacity_remaining(self) -> int:
        return max(0, self.max_ready_tasks - len(self._ready))

    @property
    def has_outstanding_work(self) -> bool:
        return bool(self._ready or self._inflight or self._completed)

    def __enter__(self) -> "DeterministicWorkQueue":
        if self._entered:
            raise RuntimeError("DeterministicWorkQueue cannot be entered twice")
        if self.manage_resource_scope:
            self._resource_cm = stage_resource_scope(self.scope)
            self._resource_cm.__enter__()
        try:
            self._executor = ThreadPoolExecutor(
                max_workers=self.allocated_workers,
                thread_name_prefix=self.thread_name_prefix,
            )
        except BaseException:
            if self._resource_cm is not None:
                self._resource_cm.__exit__(*__import__("sys").exc_info())
            self._resource_cm = None
            raise
        self._entered = True
        self._update_peak_memory()
        return self

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        executor = self._executor
        resource_cm = self._resource_cm
        self._executor = None
        self._resource_cm = None
        try:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=True)
        finally:
            self._entered = False
            if resource_cm is not None:
                return resource_cm.__exit__(exc_type, exc, tb)
        return None

    def _require_entered(self) -> ThreadPoolExecutor:
        if not self._entered or self._executor is None:
            raise RuntimeError("DeterministicWorkQueue must be used as a context manager")
        return self._executor

    def _run_item(self, item: DeterministicWorkItem) -> Any:
        with self._busy_lock:
            self._busy += 1
            self._max_busy = max(self._max_busy, self._busy)
        try:
            return item.function(*item.args, **dict(item.kwargs))
        finally:
            with self._busy_lock:
                self._busy -= 1

    def _memory_budget(self) -> int | None:
        value = self.scope.ram_budget_bytes
        return None if value is None else int(value)

    def _memory_totals(self) -> tuple[int, int, int, int]:
        return (
            int(self._ready_memory_bytes),
            int(self._inflight_memory_bytes),
            int(self._completed_memory_bytes),
            int(self._reserved_memory_bytes),
        )

    def _update_peak_memory(self) -> None:
        ready, inflight, completed, reserved = self._memory_totals()
        self._peak_accounted_memory = max(
            self._peak_accounted_memory,
            inflight + completed + reserved,
        )

    def reserve_memory(self, reservation_id: str, bytes_count: int) -> None:
        reservation_id = str(reservation_id)
        amount = int(bytes_count)
        if not reservation_id:
            raise ValueError("reservation_id must be non-empty")
        if amount < 0:
            raise ValueError("bytes_count must be non-negative")
        if reservation_id in self._reservations:
            raise ValueError(f"duplicate memory reservation {reservation_id!r}")
        budget = self._memory_budget()
        if budget is not None:
            _, inflight, completed, reserved = self._memory_totals()
            if amount + inflight + completed + reserved > budget:
                raise DeterministicWorkQueueMemoryError(
                    f"PARCORE1 reservation {reservation_id!r} requires {amount} bytes but "
                    f"the stage RAM budget is {budget} bytes."
                )
        self._reservations[reservation_id] = amount
        self._reserved_memory_bytes += amount
        self._update_peak_memory()

    def release_memory(self, reservation_id: str) -> int:
        amount = self._reservations.pop(str(reservation_id), None)
        if amount is None:
            raise KeyError(f"unknown memory reservation {reservation_id!r}")
        self._reserved_memory_bytes -= int(amount)
        self._dispatch()
        return int(amount)

    def can_submit(self) -> bool:
        return len(self._ready) < self.max_ready_tasks

    def submit(
        self,
        *,
        task_id: str,
        canonical_order: Sequence[int],
        function: Callable[..., Any],
        args: Sequence[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
        task_kind: str = "work",
        estimated_memory_bytes: int = 0,
        locality_key: str | None = None,
    ) -> None:
        self._require_entered()
        item = DeterministicWorkItem(
            task_id=str(task_id),
            canonical_order=tuple(int(value) for value in canonical_order),
            function=function,
            args=tuple(args),
            kwargs={} if kwargs is None else dict(kwargs),
            task_kind=str(task_kind),
            estimated_memory_bytes=int(estimated_memory_bytes),
            locality_key=locality_key,
        )
        if item.task_id in self._seen_task_ids:
            raise ValueError(f"duplicate PARCORE1 task ID {item.task_id!r}")
        if len(self._ready) >= self.max_ready_tasks:
            self._queue_backpressure += 1
            raise DeterministicWorkQueueError(
                f"PARCORE1 ready queue is full ({self.max_ready_tasks} tasks)."
            )
        budget = self._memory_budget()
        if budget is not None and item.estimated_memory_bytes > budget:
            raise DeterministicWorkQueueMemoryError(
                f"PARCORE1 task {item.task_id!r} estimates {item.estimated_memory_bytes} bytes, "
                f"above the stage RAM budget {budget} bytes."
            )
        self._seen_task_ids.add(item.task_id)
        self._ready.append(item)
        self._ready_memory_bytes += item.estimated_memory_bytes
        self._submitted += 1
        self._update_peak_memory()
        self._dispatch()

    def _admissible_ready_index(self) -> int | None:
        if not self._ready:
            return None
        budget = self._memory_budget()
        if budget is None:
            return 0
        _, inflight, completed, reserved = self._memory_totals()
        available = budget - inflight - completed - reserved
        for index, item in enumerate(self._ready):
            if item.estimated_memory_bytes <= available:
                return index
        return None

    def _pop_ready_index(self, index: int) -> DeterministicWorkItem:
        if index == 0:
            item = self._ready.popleft()
        else:
            self._ready.rotate(-index)
            try:
                item = self._ready.popleft()
            finally:
                self._ready.rotate(index)
        self._ready_memory_bytes -= item.estimated_memory_bytes
        return item

    def _dispatch(self) -> None:
        if not self._entered or self._executor is None:
            return
        while self._ready and len(self._inflight) < self.max_inflight_tasks:
            if len(self._completed) >= self.max_completed_tasks:
                self._queue_backpressure += 1
                break
            index = self._admissible_ready_index()
            if index is None:
                self._memory_backpressure += 1
                break
            item = self._pop_ready_index(index)
            future = self._executor.submit(self._run_item, item)
            self._inflight[future] = (item, time.monotonic())
            self._inflight_memory_bytes += item.estimated_memory_bytes
            self._update_peak_memory()

    def _emit_telemetry(self, *, heartbeat: bool) -> None:
        now = time.monotonic()
        if heartbeat:
            self._heartbeat_count += 1
        self._last_telemetry = now
        if self.telemetry_callback is not None:
            self.telemetry_callback(self.snapshot())

    def wait_for_completion(self, *, timeout: float | None = None) -> bool:
        """Wait for at least one worker completion.

        Returns ``True`` when one or more completed futures were transferred to
        the bounded completed queue and ``False`` on a heartbeat timeout.
        """

        self._require_entered()
        self._dispatch()
        if self._completed:
            return True
        if not self._inflight:
            if self._ready:
                # Ready work with no running task means RAM reservations have
                # blocked every task.  The coordinator must release memory
                # rather than spin forever.
                raise DeterministicWorkQueueMemoryError(
                    "PARCORE1 memory admission blocked every ready task with no in-flight work."
                )
            return False
        wait_timeout = self.heartbeat_interval_seconds if timeout is None else max(0.0, float(timeout))
        done, _ = wait(tuple(self._inflight), timeout=wait_timeout, return_when=FIRST_COMPLETED)
        if not done:
            self._emit_telemetry(heartbeat=True)
            return False

        slots = self.max_completed_tasks - len(self._completed)
        # ``wait`` returns a set.  Sorting by canonical metadata keeps
        # coordinator-visible completion batches deterministic without
        # constraining actual worker execution order.
        ordered_done = sorted(
            done,
            key=lambda future: (
                self._inflight[future][0].canonical_order,
                self._inflight[future][0].task_id,
            ),
        )
        moved = 0
        for future in ordered_done[: max(0, slots)]:
            item, started = self._inflight.pop(future)
            self._inflight_memory_bytes -= item.estimated_memory_bytes
            try:
                value = future.result()
            except BaseException as cause:
                for pending in self._inflight:
                    pending.cancel()
                self._ready.clear()
                self._ready_memory_bytes = 0
                raise DeterministicWorkQueueTaskError(
                    task_id=item.task_id,
                    task_kind=item.task_kind,
                    cause=cause,
                ) from cause
            self._completed.append(
                DeterministicWorkCompletion(
                    task_id=item.task_id,
                    canonical_order=item.canonical_order,
                    task_kind=item.task_kind,
                    locality_key=item.locality_key,
                    estimated_memory_bytes=item.estimated_memory_bytes,
                    wall_seconds=max(0.0, time.monotonic() - started),
                    value=value,
                )
            )
            self._completed_memory_bytes += item.estimated_memory_bytes
            self._finished += 1
            moved += 1
        if moved:
            self._update_peak_memory()
            self._emit_telemetry(heartbeat=False)
        self._dispatch()
        return moved > 0

    def dispatch_ready(self) -> None:
        """Attempt to dispatch currently ready tasks after caller-side state changes."""

        self._require_entered()
        self._dispatch()

    def drain_completed(self, *, dispatch: bool = True) -> tuple[DeterministicWorkCompletion, ...]:
        self._require_entered()
        if not self._completed:
            return ()
        items = tuple(sorted(self._completed, key=lambda item: (item.canonical_order, item.task_id)))
        self._completed.clear()
        self._completed_memory_bytes = 0
        self._committed += len(items)
        if dispatch:
            self._dispatch()
        return items

    def snapshot(self) -> DeterministicWorkQueueSnapshot:
        with self._busy_lock:
            busy = int(self._busy)
            max_busy = int(self._max_busy)
        ready, inflight, completed, reserved = self._memory_totals()
        return DeterministicWorkQueueSnapshot(
            allocated_workers=self.allocated_workers,
            busy_workers=busy,
            max_busy_workers=max_busy,
            ready_tasks=len(self._ready),
            inflight_tasks=len(self._inflight),
            completed_tasks=len(self._completed),
            submitted_tasks=int(self._submitted),
            finished_tasks=int(self._finished),
            committed_tasks=int(self._committed),
            ready_memory_bytes=int(ready),
            inflight_memory_bytes=int(inflight),
            completed_memory_bytes=int(completed),
            reserved_memory_bytes=int(reserved),
            memory_budget_bytes=self._memory_budget(),
            peak_accounted_memory_bytes=int(self._peak_accounted_memory),
            memory_backpressure_events=int(self._memory_backpressure),
            queue_backpressure_events=int(self._queue_backpressure),
            heartbeat_count=int(self._heartbeat_count),
        )


__all__ = [
    "DeterministicWorkQueueError",
    "DeterministicWorkQueueTaskError",
    "DeterministicWorkQueueMemoryError",
    "DeterministicWorkItem",
    "DeterministicWorkCompletion",
    "DeterministicWorkQueueSnapshot",
    "DeterministicOrderedReducer",
    "DeterministicWorkQueue",
]
