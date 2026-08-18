"""PAR-DENS2 scene-level CPU/RAM scheduler for density work.

The scheduler owns *execution resources only*.  It does not participate in
scientific density identity, grid selection, cache keys, field normalization,
or provenance hashes.  Tasks declare conservative retained/transient memory and
minimum/preferred worker counts.  Admission is against one affinity/cgroup/
scheduler-aware :class:`RuntimeResourceBudget` resolved by LD10.

PAR-DENS3 and later gates may use the cooperative worker lease to resize chunked
work after sibling tasks complete.  PAR-DENS2 itself introduces the resource
contract and deterministic execution controller without changing density
numerics.
"""

from __future__ import annotations

import multiprocessing as mp
import threading
import time
from contextvars import ContextVar
from concurrent.futures import Future, ProcessPoolExecutor, ThreadPoolExecutor, wait
from contextlib import contextmanager
from contextvars import copy_context
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, Iterable, Iterator, Mapping, Sequence, TypeVar

import numpy as np

from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port
from .density_gpu import density_gpu_major_job_scope
from .runtime_resources import RuntimeResourceBudget, density_resource_budget_scope

DENSITY_TASK_RESOURCES_SCHEMA = "mdstats.density-task-resources.v1"
DENSITY_TASK_REPORT_SCHEMA = "mdstats.density-task-report.v2"
DENSITY_SCHEDULER_REPORT_SCHEMA = "mdstats.density-scheduler-report.v2"
DENSITY_SCHEDULER_POLICY_SCHEMA = "mdstats.density-scheduler-policy.v1"
DENSITY_SCHEDULER_HEARTBEAT_SECONDS = 5.0

_T = TypeVar("_T")
_U = TypeVar("_U")


_CURRENT_DENSITY_WORKER_LEASE: ContextVar["DensityWorkerLease | None"] = ContextVar(
    "mdstats_current_density_worker_lease", default=None
)


def current_density_worker_lease() -> "DensityWorkerLease | None":
    """Return the active PAR-DENS task lease for this execution context.

    Low-level PAR-DENS3 kernels use the live lease only for execution choices
    (chunk concurrency and FFT worker counts).  Scientific planning, field
    identity, and cache keys must remain independent of this value.
    """

    return _CURRENT_DENSITY_WORKER_LEASE.get()


def current_density_worker_count(*, default: int = 1) -> int:
    """Return the live task worker allocation, or ``default`` outside a task."""

    lease = current_density_worker_lease()
    return max(1, int(default if lease is None else lease.workers))


@contextmanager
def density_worker_lease_scope(lease: "DensityWorkerLease") -> Iterator["DensityWorkerLease"]:
    """Bind one live worker lease to the current task context."""

    if not isinstance(lease, DensityWorkerLease):
        raise TypeError("lease must be DensityWorkerLease.")
    token = _CURRENT_DENSITY_WORKER_LEASE.set(lease)
    try:
        yield lease
    finally:
        _CURRENT_DENSITY_WORKER_LEASE.reset(token)


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a nonnegative integer.")
    result = int(value)
    if result < 0:
        raise GraphStyleError(f"{name} must be nonnegative.")
    return result


class DensityTaskExecutionMode(str, Enum):
    """Resource class for one schedulable density task."""

    NATIVE_THREADS = "native_threads"
    PYTHON_THREADS = "python_threads"
    PYTHON_PROCESSES = "python_processes"


@dataclass(frozen=True, slots=True)
class DensityTaskResources:
    """Conservative execution-resource declaration for one density task.

    ``retained_bytes`` are bytes that remain live after the task completes and
    therefore continue consuming the scene budget.  ``transient_bytes`` are the
    additional peak bytes needed only while this task runs.  Shared parent data
    must be charged to the parent only; child tasks declare only their exclusive
    retained/transient bytes and name the owning parent through ``parent_task_id``.
    """

    task_id: str
    retained_bytes: int
    transient_bytes: int
    minimum_workers: int = 1
    preferred_workers: int = 1
    execution_mode: DensityTaskExecutionMode | str = DensityTaskExecutionMode.NATIVE_THREADS
    backend: str = "unspecified"
    parent_task_id: str | None = None
    construction_order: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DENSITY_TASK_RESOURCES_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_TASK_RESOURCES_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-task resource schema {self.schema_version!r}."
            )
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise GraphStyleError("task_id must be a nonempty string.")
        if not isinstance(self.backend, str) or not self.backend.strip():
            raise GraphStyleError("backend must be a nonempty string.")
        if self.parent_task_id is not None and (
            not isinstance(self.parent_task_id, str) or not self.parent_task_id.strip()
        ):
            raise GraphStyleError("parent_task_id must be None or a nonempty string.")
        mode = (
            self.execution_mode
            if isinstance(self.execution_mode, DensityTaskExecutionMode)
            else DensityTaskExecutionMode(str(self.execution_mode))
        )
        retained = _nonnegative_int(self.retained_bytes, name="retained_bytes")
        transient = _nonnegative_int(self.transient_bytes, name="transient_bytes")
        minimum = _positive_int(self.minimum_workers, name="minimum_workers")
        preferred = _positive_int(self.preferred_workers, name="preferred_workers")
        if preferred < minimum:
            raise GraphStyleError("preferred_workers cannot be below minimum_workers.")
        order = _nonnegative_int(self.construction_order, name="construction_order")
        object.__setattr__(self, "retained_bytes", retained)
        object.__setattr__(self, "transient_bytes", transient)
        object.__setattr__(self, "minimum_workers", minimum)
        object.__setattr__(self, "preferred_workers", preferred)
        object.__setattr__(self, "construction_order", order)
        object.__setattr__(self, "execution_mode", mode)
        object.__setattr__(self, "metadata", dict(self.metadata))

    @property
    def peak_bytes(self) -> int:
        return self.retained_bytes + self.transient_bytes

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_id": self.task_id,
            "retained_bytes": self.retained_bytes,
            "transient_bytes": self.transient_bytes,
            "peak_bytes": self.peak_bytes,
            "minimum_workers": self.minimum_workers,
            "preferred_workers": self.preferred_workers,
            "execution_mode": self.execution_mode.value,
            "backend": self.backend,
            "parent_task_id": self.parent_task_id,
            "construction_order": self.construction_order,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityTaskResources":
        data = dict(value)
        data.pop("peak_bytes", None)
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DensitySchedulerPolicy:
    """Execution-only scheduler policy resolved inside the scene budget."""

    max_parallel_tasks: int | None = None
    schema_version: str = DENSITY_SCHEDULER_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SCHEDULER_POLICY_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-scheduler policy schema {self.schema_version!r}."
            )
        if self.max_parallel_tasks is not None:
            object.__setattr__(
                self,
                "max_parallel_tasks",
                _positive_int(self.max_parallel_tasks, name="max_parallel_tasks"),
            )


class DensityWorkerLease:
    """Cooperative worker allocation for one active task.

    Worker counts may be rebalanced while a task is active.  Chunked PAR-DENS3+
    kernels should query :attr:`workers` between chunks.  A single monolithic
    native call observes the worker count it was launched with; scientific output
    must never depend on whether later generations grant additional workers.
    """

    __slots__ = (
        "_resources",
        "_scene_budget",
        "_workers",
        "_maximum_workers_seen",
        "_worker_history",
        "_generation",
        "_lock",
    )

    def __init__(
        self,
        resources: DensityTaskResources,
        scene_budget: RuntimeResourceBudget,
        workers: int,
    ) -> None:
        self._resources = resources
        self._scene_budget = scene_budget
        self._workers = int(workers)
        self._maximum_workers_seen = int(workers)
        self._worker_history = [int(workers)]
        self._generation = 0
        self._lock = threading.RLock()

    @property
    def resources(self) -> DensityTaskResources:
        return self._resources

    @property
    def workers(self) -> int:
        with self._lock:
            return self._workers

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    @property
    def maximum_workers_seen(self) -> int:
        with self._lock:
            return self._maximum_workers_seen

    @property
    def worker_history(self) -> tuple[int, ...]:
        with self._lock:
            return tuple(self._worker_history)

    def _resize(self, workers: int) -> None:
        workers = int(workers)
        if workers < self.resources.minimum_workers:
            raise GraphAdapterError("Scheduler attempted to violate a task minimum worker count.")
        with self._lock:
            if workers == self._workers:
                return
            if workers != self._workers:
                self._workers = workers
                self._maximum_workers_seen = max(self._maximum_workers_seen, workers)
                self._worker_history.append(workers)
                self._generation += 1

    def task_budget(self) -> RuntimeResourceBudget:
        """Return the nested budget authoritative for this task's low-level calls."""

        workers = min(self.workers, self._scene_budget.max_threads)
        # Keep the scene memory ceiling visible to nested scientific planners.
        # PAR-DENS2 enforces aggregate task peaks at admission time; replacing
        # the nested planning ceiling with a task estimate would re-derive
        # smaller scientific/execution limits and could change an otherwise
        # approved plan.
        memory = self._scene_budget.max_memory_bytes
        return RuntimeResourceBudget(
            max_memory_bytes=memory,
            max_threads=workers,
            max_wall_time_seconds=self._scene_budget.max_wall_time_seconds,
            memory_fraction=self._scene_budget.memory_fraction,
            thread_fraction=self._scene_budget.thread_fraction,
            snapshot=self._scene_budget.snapshot,
            memory_override_source="par_dens2_task_allocation",
            thread_override_source="par_dens2_task_allocation",
            wall_time_override_source="active_scene_budget",
        )

    @contextmanager
    def budget_scope(self) -> Iterator[RuntimeResourceBudget]:
        """Expose this allocation through the existing LD10 context interface."""

        budget = self.task_budget()
        with density_resource_budget_scope(budget):
            yield budget

    def thread_map(self, function: Callable[[_T], _U], values: Iterable[_T]) -> list[_U]:
        """Run GIL-releasing/Python thread work under the current worker lease."""

        items = list(values)
        if not items:
            return []
        workers = min(self.workers, len(items))
        if workers <= 1:
            return [function(item) for item in items]
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="mdstats-density") as pool:
            return list(pool.map(function, items))

    def process_map(
        self, function: Callable[[_T], _U], values: Iterable[_T]
    ) -> list[_U]:
        """Run genuinely Python-heavy work in a bounded process pool.

        The callable and values must satisfy the normal ``multiprocessing``
        pickling contract.  The process count is never larger than the scheduler
        lease, so child-process parallelism consumes the same global CPU tokens.
        """

        items = list(values)
        if not items:
            return []
        workers = min(self.workers, len(items))
        with ProcessPoolExecutor(
            max_workers=max(1, workers), mp_context=mp.get_context("spawn")
        ) as pool:
            return list(pool.map(function, items))


@dataclass(frozen=True, slots=True)
class DensityScheduledTask(Generic[_T]):
    resources: DensityTaskResources
    function: Callable[[DensityWorkerLease], _T] = field(repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.resources, DensityTaskResources):
            raise TypeError("resources must be DensityTaskResources.")
        if not callable(self.function):
            raise TypeError("function must be callable.")


@dataclass(frozen=True, slots=True)
class DensityTaskReport:
    task_id: str
    construction_order: int
    initial_workers: int
    maximum_workers: int
    worker_allocation_history: tuple[int, ...]
    wall_seconds: float
    retained_bytes: int
    transient_bytes: int
    execution_mode: str
    backend: str
    schema_version: str = DENSITY_TASK_REPORT_SCHEMA

    def to_json_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True)
class DensitySchedulerReport:
    max_threads: int
    max_memory_bytes: int
    peak_reserved_bytes: int
    maximum_concurrent_tasks: int
    wall_seconds: float
    tasks: tuple[DensityTaskReport, ...]
    execution_policy: str = "par_dens2_global_resource_scheduler_v1"
    cpu_budget_obeyed: bool = True
    memory_budget_obeyed: bool = True
    schema_version: str = DENSITY_SCHEDULER_REPORT_SCHEMA

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_threads": self.max_threads,
            "max_memory_bytes": self.max_memory_bytes,
            "peak_reserved_bytes": self.peak_reserved_bytes,
            "maximum_concurrent_tasks": self.maximum_concurrent_tasks,
            "wall_seconds": self.wall_seconds,
            "execution_policy": self.execution_policy,
            "cpu_budget_obeyed": self.cpu_budget_obeyed,
            "memory_budget_obeyed": self.memory_budget_obeyed,
            "tasks": [task.to_json_dict() for task in self.tasks],
        }


class DensitySchedulerTaskError(RuntimeError):
    """One scheduled task failed after deterministic completion collation."""

    def __init__(self, task_id: str, original: BaseException) -> None:
        super().__init__(f"Density task {task_id!r} failed: {original}")
        self.task_id = task_id
        self.original = original


class DensitySceneScheduler:
    """Global work-conserving scheduler under one LD10 host budget."""

    def __init__(
        self,
        budget: RuntimeResourceBudget,
        *,
        policy: DensitySchedulerPolicy | None = None,
        progress: ProgressPortLike | None = None,
    ) -> None:
        if not isinstance(budget, RuntimeResourceBudget):
            raise TypeError("budget must be RuntimeResourceBudget.")
        self.budget = budget
        self.policy = DensitySchedulerPolicy() if policy is None else policy
        if not isinstance(self.policy, DensitySchedulerPolicy):
            raise TypeError("policy must be DensitySchedulerPolicy or None.")
        self._last_report: DensitySchedulerReport | None = None
        self._reporter = ProgressEmitter(
            resolve_progress_port(progress), source="plotting.density_scheduler"
        )

    @property
    def last_report(self) -> DensitySchedulerReport | None:
        return self._last_report

    def validate_resources(self, tasks: Sequence[DensityTaskResources]) -> None:
        """Fail transactionally when declared tasks cannot fit the scene budget."""

        seen: dict[str, int] = {}
        total_retained = 0
        for index, resources in enumerate(tasks):
            if not isinstance(resources, DensityTaskResources):
                raise TypeError("tasks must contain DensityTaskResources.")
            if resources.task_id in seen:
                raise GraphAdapterError(f"Duplicate density task_id {resources.task_id!r}.")
            seen[resources.task_id] = index
            if resources.parent_task_id is not None:
                parent_index = seen.get(resources.parent_task_id)
                if parent_index is None or parent_index >= index:
                    raise GraphAdapterError(
                        f"Task {resources.task_id!r} must name an earlier parent task."
                    )
            if resources.minimum_workers > self.budget.max_threads:
                raise GraphComplexityError(
                    f"Density task {resources.task_id!r} requires at least "
                    f"{resources.minimum_workers} workers but the scene budget allows "
                    f"{self.budget.max_threads}."
                )
            if resources.peak_bytes > self.budget.max_memory_bytes:
                raise GraphComplexityError(
                    f"Density task {resources.task_id!r} predicts a {resources.peak_bytes}-byte "
                    f"peak above the {self.budget.max_memory_bytes}-byte scene budget."
                )
            total_retained += resources.retained_bytes
        if total_retained > self.budget.max_memory_bytes:
            raise GraphComplexityError(
                "Density task outputs predict "
                f"{total_retained} retained bytes, exceeding the scene memory budget "
                f"{self.budget.max_memory_bytes}."
            )

    def _parallel_task_limit(self, task_count: int) -> int:
        limit = min(task_count, self.budget.max_threads)
        if self.policy.max_parallel_tasks is not None:
            limit = min(limit, self.policy.max_parallel_tasks)
        return max(1, limit)

    @staticmethod
    def _rebalance_leases(
        active: Mapping[int, DensityWorkerLease], max_threads: int
    ) -> None:
        if not active:
            return
        ordered = sorted(active)
        # First return every task to its declared minimum.  This makes CPU tokens
        # reusable for newly admitted siblings instead of pinning a stale static
        # split for the lifetime of the scene.
        for index in ordered:
            lease = active[index]
            lease._resize(lease.resources.minimum_workers)
        remaining = max_threads - sum(active[i].workers for i in ordered)
        # Deterministic round-robin water filling prevents a construction-order
        # task from monopolizing every free CPU while siblings remain active.
        while remaining > 0:
            changed = False
            for index in ordered:
                lease = active[index]
                target = min(lease.resources.preferred_workers, max_threads)
                if lease.workers < target:
                    lease._resize(lease.workers + 1)
                    remaining -= 1
                    changed = True
                    if remaining == 0:
                        break
            if not changed:
                break

    def run(self, tasks: Sequence[DensityScheduledTask[_T]]) -> tuple[_T, ...]:
        """Execute tasks with deterministic result collation and bounded resources."""

        scheduled = tuple(tasks)
        if not scheduled:
            self._last_report = DensitySchedulerReport(
                max_threads=self.budget.max_threads,
                max_memory_bytes=self.budget.max_memory_bytes,
                peak_reserved_bytes=0,
                maximum_concurrent_tasks=0,
                tasks=(),
            )
            return ()
        resources = tuple(task.resources for task in scheduled)
        self.validate_resources(resources)
        scheduler_started = time.perf_counter()
        self._reporter.started(
            "density_scheduler",
            f"scheduling {len(scheduled)} density field task(s) under "
            f"{self.budget.max_threads} CPU worker token(s)",
            current=0,
            total=len(scheduled),
            unit="fields",
            metadata={
                "max_threads": int(self.budget.max_threads),
                "max_memory_bytes": int(self.budget.max_memory_bytes),
            },
        )

        results: list[Any] = [None] * len(scheduled)
        failures: dict[int, BaseException] = {}
        maximum_workers_seen: dict[int, int] = {}
        worker_histories: dict[int, tuple[int, ...]] = {}
        task_wall_seconds: dict[int, float] = {}
        # PAR-DENS6 memory-safe deterministic admission: run the largest-peak
        # independent task as early as possible.  Retained outputs accumulate
        # as tasks finish; construction-order admission can therefore strand a
        # late high-workspace task even when a feasible ordering exists.  Peak-
        # descending order is execution-only; results are still collated by
        # construction order and parent dependencies remain authoritative.
        pending = sorted(
            range(len(scheduled)),
            key=lambda index: (-resources[index].peak_bytes, resources[index].construction_order),
        )
        active: dict[int, DensityWorkerLease] = {}
        futures: dict[Future[Any], int] = {}
        committed_retained = 0
        peak_reserved = 0
        maximum_concurrent = 0
        initial_workers: dict[int, int] = {}
        completed_count = 0
        last_heartbeat = scheduler_started
        heartbeat_seconds = float(DENSITY_SCHEDULER_HEARTBEAT_SECONDS)

        parallel_limit = self._parallel_task_limit(len(scheduled))
        def active_peak_bytes() -> int:
            return sum(resources[index].peak_bytes for index in active)

        def can_admit(index: int) -> bool:
            candidate = resources[index]
            if len(active) >= parallel_limit:
                return False
            minimum_cpu = sum(
                resources[i].minimum_workers for i in active
            ) + candidate.minimum_workers
            if minimum_cpu > self.budget.max_threads:
                return False
            memory = committed_retained + active_peak_bytes() + candidate.peak_bytes
            if memory > self.budget.max_memory_bytes:
                return False
            if candidate.parent_task_id is not None:
                parent_index = next(
                    i for i, item in enumerate(resources) if item.task_id == candidate.parent_task_id
                )
                if parent_index in pending or parent_index in active:
                    return False
                if parent_index in failures:
                    return False
            return True

        def task_runner(index: int, lease: DensityWorkerLease) -> Any:
            # Nested low-level resource resolution sees this exact task allocation.
            # The live lease is also context-bound so chunked PAR-DENS3 kernels
            # can observe CPU tokens returned by completed sibling fields.
            started = time.perf_counter()
            try:
                with density_worker_lease_scope(lease):
                    with lease.budget_scope():
                        with density_gpu_major_job_scope(resources[index].task_id):
                            return scheduled[index].function(lease)
            finally:
                task_wall_seconds[index] = time.perf_counter() - started

        with ThreadPoolExecutor(
            max_workers=parallel_limit,
            thread_name_prefix="mdstats-density-scene",
        ) as executor:
            while pending or futures:
                admitted_any = False
                # Reclaim stale extra CPU before admitting new siblings.
                self._rebalance_leases(active, self.budget.max_threads)
                cursor = 0
                newly_admitted: list[int] = []
                while cursor < len(pending):
                    index = pending[cursor]
                    if not can_admit(index):
                        cursor += 1
                        continue
                    contract = resources[index]
                    lease = DensityWorkerLease(
                        contract, self.budget, contract.minimum_workers
                    )
                    active[index] = lease
                    pending.pop(cursor)
                    newly_admitted.append(index)
                    admitted_any = True
                    maximum_concurrent = max(maximum_concurrent, len(active))
                    peak_reserved = max(
                        peak_reserved,
                        committed_retained + active_peak_bytes(),
                    )
                self._rebalance_leases(active, self.budget.max_threads)
                for index in newly_admitted:
                    lease = active[index]
                    initial_workers[index] = lease.workers
                    # ThreadPoolExecutor does not propagate contextvars.  Copy the
                    # caller context per field so PAR-DENS5 GPU journals and any
                    # other execution-only scene context remain visible inside the
                    # scheduled worker without sharing a Context object concurrently.
                    context = copy_context()
                    self._reporter.started(
                        "density_scheduler_task",
                        f"started {resources[index].task_id}; backend={resources[index].backend}; "
                        f"workers={lease.workers}; peak={resources[index].peak_bytes / (1024.0 ** 2):.1f} MiB",
                        current=completed_count,
                        total=len(scheduled),
                        unit="fields",
                        metadata={
                            "task_id": resources[index].task_id,
                            "workers": int(lease.workers),
                            "peak_bytes": int(resources[index].peak_bytes),
                            "backend": resources[index].backend,
                        },
                    )
                    future = executor.submit(context.run, task_runner, index, lease)
                    futures[future] = index
                if not futures:
                    if pending:
                        # A failed parent makes its descendants intentionally
                        # ineligible.  Preserve the authoritative lowest-order
                        # task failure instead of replacing it with a secondary
                        # admission error once all independent work has drained.
                        blocked_by_failed_parent = all(
                            resources[index].parent_task_id is not None
                            and any(
                                failed_index in failures
                                and resources[failed_index].task_id
                                == resources[index].parent_task_id
                                for failed_index in failures
                            )
                            for index in pending
                        )
                        if failures and blocked_by_failed_parent:
                            break
                        index = pending[0]
                        contract = resources[index]
                        raise GraphComplexityError(
                            "No density task can be admitted under the current retained-memory/CPU "
                            f"state; next task={contract.task_id!r}, retained={committed_retained}, "
                            f"task_peak={contract.peak_bytes}, memory_budget={self.budget.max_memory_bytes}."
                        )
                    break

                if admitted_any:
                    # If every possible task has already been admitted, waiting now
                    # avoids a spin while preserving deterministic admission order.
                    pass
                done, _not_done = wait(
                    tuple(futures),
                    timeout=heartbeat_seconds,
                    return_when="FIRST_COMPLETED",
                )
                if not done:
                    now = time.perf_counter()
                    if now - last_heartbeat >= heartbeat_seconds:
                        last_heartbeat = now
                        active_summary = ", ".join(
                            f"{resources[index].task_id}:{active[index].workers}w"
                            for index in sorted(active)
                        )
                        self._reporter.update(
                            "density_scheduler",
                            "density tasks still running; "
                            f"active={len(active)}; pending={len(pending)}; "
                            f"allocations=[{active_summary}]",
                            current=completed_count,
                            total=len(scheduled),
                            unit="fields",
                            metadata={
                                "active_tasks": int(len(active)),
                                "pending_tasks": int(len(pending)),
                                "committed_retained_bytes": int(committed_retained),
                                "active_peak_bytes": int(active_peak_bytes()),
                            },
                        )
                    continue
                # Completion order is intentionally not authoritative.  Process all
                # simultaneously completed futures by construction order.
                for future in sorted(done, key=lambda item: futures[item]):
                    index = futures.pop(future)
                    lease = active.pop(index)
                    try:
                        results[index] = future.result()
                    except BaseException as error:  # preserve lowest-order failure below
                        failures[index] = error
                    maximum_workers_seen[index] = lease.maximum_workers_seen
                    worker_histories[index] = lease.worker_history
                    committed_retained += resources[index].retained_bytes
                    completed_count += 1
                    if index in failures:
                        self._reporter.warning(
                            "density_scheduler_task",
                            f"failed {resources[index].task_id}: {failures[index]}",
                            current=completed_count,
                            total=len(scheduled),
                            unit="fields",
                            metadata={"task_id": resources[index].task_id},
                        )
                    else:
                        self._reporter.completed(
                            "density_scheduler_task",
                            f"completed {resources[index].task_id} in "
                            f"{task_wall_seconds.get(index, 0.0):.1f} s; "
                            f"max_workers={lease.maximum_workers_seen}",
                            current=completed_count,
                            total=len(scheduled),
                            unit="fields",
                            metadata={
                                "task_id": resources[index].task_id,
                                "maximum_workers": int(lease.maximum_workers_seen),
                            },
                        )
                    peak_reserved = max(peak_reserved, committed_retained + active_peak_bytes())
                    self._rebalance_leases(active, self.budget.max_threads)

        reports = tuple(
            DensityTaskReport(
                task_id=resources[index].task_id,
                construction_order=resources[index].construction_order,
                initial_workers=initial_workers.get(index, resources[index].minimum_workers),
                maximum_workers=maximum_workers_seen.get(
                    index, initial_workers.get(index, resources[index].minimum_workers)
                ),
                worker_allocation_history=(
                    active[index].worker_history if index in active else worker_histories.get(
                        index, (initial_workers.get(index, resources[index].minimum_workers),)
                    )
                ),
                wall_seconds=float(task_wall_seconds.get(index, 0.0)),
                retained_bytes=resources[index].retained_bytes,
                transient_bytes=resources[index].transient_bytes,
                execution_mode=resources[index].execution_mode.value,
                backend=resources[index].backend,
            )
            for index in range(len(resources))
        )
        # Allocation history is execution evidence only; task output and cache
        # identity never depend on worker counts.
        self._last_report = DensitySchedulerReport(
            max_threads=self.budget.max_threads,
            max_memory_bytes=self.budget.max_memory_bytes,
            peak_reserved_bytes=peak_reserved,
            maximum_concurrent_tasks=maximum_concurrent,
            wall_seconds=time.perf_counter() - scheduler_started,
            tasks=reports,
        )
        if failures:
            first = min(failures)
            raise DensitySchedulerTaskError(resources[first].task_id, failures[first]) from failures[first]
        self._reporter.completed(
            "density_scheduler",
            f"completed {len(scheduled)} density field task(s) in "
            f"{self._last_report.wall_seconds:.1f} s",
            current=len(scheduled),
            total=len(scheduled),
            unit="fields",
            metadata={
                "maximum_concurrent_tasks": int(maximum_concurrent),
                "peak_reserved_bytes": int(peak_reserved),
            },
        )
        return tuple(results)

    @contextmanager
    def task_scope(self, resources: DensityTaskResources) -> Iterator[DensityWorkerLease]:
        """Synchronously admit one task without changing the caller's execution order.

        This is the PAR-DENS2 integration surface used before PAR-DENS3 enables
        concurrent field realization.  A single task receives all available CPUs
        up to its preference while still being checked against the global memory
        budget, and nested density calls inherit that task allocation.
        """

        self.validate_resources((resources,))
        workers = min(resources.preferred_workers, self.budget.max_threads)
        workers = max(resources.minimum_workers, workers)
        lease = DensityWorkerLease(resources, self.budget, workers)
        task_started = time.perf_counter()
        with density_worker_lease_scope(lease):
            with lease.budget_scope():
                with density_gpu_major_job_scope(resources.task_id):
                    yield lease
        task_wall_seconds = time.perf_counter() - task_started
        self._last_report = DensitySchedulerReport(
            max_threads=self.budget.max_threads,
            max_memory_bytes=self.budget.max_memory_bytes,
            peak_reserved_bytes=resources.peak_bytes,
            maximum_concurrent_tasks=1,
            wall_seconds=task_wall_seconds,
            tasks=(
                DensityTaskReport(
                    task_id=resources.task_id,
                    construction_order=resources.construction_order,
                    initial_workers=workers,
                    maximum_workers=lease.maximum_workers_seen,
                    worker_allocation_history=lease.worker_history,
                    wall_seconds=task_wall_seconds,
                    retained_bytes=resources.retained_bytes,
                    transient_bytes=resources.transient_bytes,
                    execution_mode=resources.execution_mode.value,
                    backend=resources.backend,
                ),
            ),
        )


def task_resources_from_phase_b_plan(
    plan: Any,
    *,
    preferred_workers: int,
    minimum_workers: int = 1,
    parent_task_id: str | None = None,
) -> DensityTaskResources:
    """Translate a Phase-B field plan into the PAR-DENS2 execution contract."""

    required = (
        "field_key",
        "construction_order",
        "retained_bytes",
        "transient_bytes_upper",
        "metadata",
    )
    for name in required:
        if not hasattr(plan, name):
            raise TypeError(f"plan is missing required attribute {name!r}.")
    metadata = dict(plan.metadata)
    backend = str(metadata.get("backend", "unspecified"))
    execution_mode = DensityTaskExecutionMode.NATIVE_THREADS
    return DensityTaskResources(
        task_id=str(plan.field_key),
        retained_bytes=int(plan.retained_bytes),
        transient_bytes=int(plan.transient_bytes_upper),
        minimum_workers=minimum_workers,
        preferred_workers=preferred_workers,
        execution_mode=execution_mode,
        backend=backend,
        parent_task_id=parent_task_id,
        construction_order=int(plan.construction_order),
        metadata={
            "source_kind": str(getattr(plan, "source_kind", "unknown")),
            "planner_schema": str(getattr(plan, "schema_version", "unknown")),
            "scientific_identity_includes_worker_count": False,
        },
    )


__all__ = [
    "DENSITY_SCHEDULER_POLICY_SCHEMA",
    "DENSITY_SCHEDULER_REPORT_SCHEMA",
    "DENSITY_TASK_REPORT_SCHEMA",
    "DENSITY_TASK_RESOURCES_SCHEMA",
    "DensityScheduledTask",
    "DensitySchedulerPolicy",
    "DensitySchedulerReport",
    "DensitySchedulerTaskError",
    "DensitySceneScheduler",
    "DensityTaskExecutionMode",
    "DensityTaskReport",
    "DensityTaskResources",
    "DensityWorkerLease",
    "current_density_worker_count",
    "current_density_worker_lease",
    "density_worker_lease_scope",
    "task_resources_from_phase_b_plan",
]
