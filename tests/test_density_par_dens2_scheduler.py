from __future__ import annotations

import time
from dataclasses import replace

import pytest

from mdstats.plotting.density_scheduler import (
    DENSITY_SCHEDULER_REPORT_SCHEMA,
    DENSITY_TASK_RESOURCES_SCHEMA,
    DensityScheduledTask,
    DensitySchedulerPolicy,
    DensitySchedulerTaskError,
    DensitySceneScheduler,
    DensityTaskExecutionMode,
    DensityTaskResources,
)
from mdstats.plotting.graph_errors import GraphAdapterError, GraphComplexityError
from mdstats.plotting.runtime_resources import (
    DensityTimeModel,
    RuntimeResourceBudget,
    RuntimeResourceSnapshot,
    density_time_model_scope,
    resolve_density_resource_limits,
    resolve_runtime_resource_budget,
)


def _budget(*, threads: int = 4, memory: int = 1_000_000) -> RuntimeResourceBudget:
    snapshot = RuntimeResourceSnapshot(
        logical_cpu_count=threads,
        affinity_cpu_count=threads,
        cgroup_cpu_quota=None,
        scheduler_cpu_count=None,
        available_cpu_count=threads,
        host_memory_available_bytes=memory,
        cgroup_memory_limit_bytes=None,
        cgroup_memory_current_bytes=None,
        scheduler_memory_limit_bytes=None,
        rlimit_as_bytes=None,
        process_rss_bytes=1,
        process_virtual_memory_bytes=1,
        available_memory_bytes=memory,
    )
    return RuntimeResourceBudget(
        max_memory_bytes=memory,
        max_threads=threads,
        max_wall_time_seconds=1200.0,
        memory_fraction=0.80,
        thread_fraction=0.90,
        snapshot=snapshot,
        memory_override_source="test",
        thread_override_source="test",
        wall_time_override_source="test",
    )


def _task(
    task_id: str,
    *,
    order: int,
    retained: int = 10,
    transient: int = 20,
    minimum: int = 1,
    preferred: int = 4,
    mode: DensityTaskExecutionMode = DensityTaskExecutionMode.NATIVE_THREADS,
    parent: str | None = None,
) -> DensityTaskResources:
    return DensityTaskResources(
        task_id=task_id,
        retained_bytes=retained,
        transient_bytes=transient,
        minimum_workers=minimum,
        preferred_workers=preferred,
        execution_mode=mode,
        backend="test",
        parent_task_id=parent,
        construction_order=order,
    )


def _square(value: int) -> int:
    return value * value


def test_task_resources_round_trip_and_peak() -> None:
    original = _task("a", order=0, retained=11, transient=7, minimum=1, preferred=3)
    payload = original.to_json_dict()
    assert payload["schema_version"] == DENSITY_TASK_RESOURCES_SCHEMA
    assert payload["peak_bytes"] == 18
    restored = DensityTaskResources.from_json_dict(payload)
    assert restored == original



def test_scheduler_emits_admission_and_completion_progress() -> None:
    events = []
    scheduler = DensitySceneScheduler(
        _budget(threads=2, memory=1_000), progress=events.append
    )

    values = scheduler.run(
        (
            DensityScheduledTask(_task("a", order=0, preferred=2), lambda _lease: "ok"),
        )
    )

    assert values == ("ok",)
    stages = [event.stage for event in events]
    assert stages[0] == "density_scheduler"
    assert "density_scheduler_task" in stages
    assert stages[-1] == "density_scheduler"
    task_events = [event for event in events if event.stage == "density_scheduler_task"]
    assert task_events[0].status == "started"
    assert task_events[-1].status == "completed"
    assert task_events[-1].current == task_events[-1].total == 1


def test_scheduler_emits_heartbeat_while_long_task_is_running(monkeypatch) -> None:
    import mdstats.plotting.density_scheduler as scheduler_module

    monkeypatch.setattr(scheduler_module, "DENSITY_SCHEDULER_HEARTBEAT_SECONDS", 0.01)
    events = []
    scheduler = DensitySceneScheduler(
        _budget(threads=2, memory=1_000), progress=events.append
    )

    def slow(_lease):
        time.sleep(0.035)
        return "ok"

    assert scheduler.run(
        (DensityScheduledTask(_task("slow", order=0, preferred=2), slow),)
    ) == ("ok",)
    heartbeats = [
        event
        for event in events
        if event.stage == "density_scheduler"
        and event.status == "running"
        and "still running" in event.message
    ]
    assert heartbeats
    assert heartbeats[0].current == 0
    assert heartbeats[0].total == 1
    assert "slow:2w" in heartbeats[0].message




def test_scheduler_workers_inherit_scene_time_model_without_recalibration(monkeypatch) -> None:
    import mdstats.plotting.runtime_resources as runtime_resources

    budget = _budget(threads=4, memory=1_000_000)
    model = DensityTimeModel(
        calibration_threads=4,
        calibration_source="scheduler-inherited-test",
    )
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("scheduled production task recalibrated the density model")

    monkeypatch.setattr(runtime_resources, "calibrate_density_time_model", forbidden)
    scheduler = DensitySceneScheduler(budget)

    def nested_resolve(_lease):
        _nested_budget, inherited, _limits = resolve_density_resource_limits()
        return inherited.calibration_source

    with density_time_model_scope(model):
        result = scheduler.run(
            (
                DensityScheduledTask(
                    _task("nested", order=0, preferred=3), nested_resolve
                ),
            )
        )

    assert result == (model.calibration_source,)
    assert calls == []


def test_scheduler_rejects_impossible_cpu_memory_and_parent_contracts() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=4, memory=100))
    with pytest.raises(GraphComplexityError):
        scheduler.validate_resources((_task("cpu", order=0, minimum=5, preferred=5),))
    with pytest.raises(GraphComplexityError):
        scheduler.validate_resources((_task("memory", order=0, retained=40, transient=70),))
    with pytest.raises(GraphAdapterError):
        scheduler.validate_resources((_task("child", order=0, parent="missing"),))


def test_scheduler_collates_results_by_construction_order_not_completion_order() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=2, memory=1_000))

    def slow(_lease):
        time.sleep(0.05)
        return "first"

    def fast(_lease):
        time.sleep(0.005)
        return "second"

    values = scheduler.run(
        (
            DensityScheduledTask(_task("first", order=0, preferred=1), slow),
            DensityScheduledTask(_task("second", order=1, preferred=1), fast),
        )
    )
    assert values == ("first", "second")
    assert scheduler.last_report is not None
    assert scheduler.last_report.schema_version == DENSITY_SCHEDULER_REPORT_SCHEMA
    assert scheduler.last_report.maximum_concurrent_tasks == 2
    assert scheduler.last_report.peak_reserved_bytes <= scheduler.budget.max_memory_bytes


def test_completed_short_task_returns_cpus_to_remaining_heavy_task() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=4, memory=2_000))

    def short(lease):
        seen = [lease.workers]
        time.sleep(0.04)
        seen.append(lease.workers)
        return max(seen)

    def long(lease):
        seen = [lease.workers]
        deadline = time.monotonic() + 0.4
        while time.monotonic() < deadline:
            seen.append(lease.workers)
            if max(seen) == 4:
                break
            time.sleep(0.01)
        return max(seen)

    values = scheduler.run(
        (
            DensityScheduledTask(_task("short", order=0, preferred=4), short),
            DensityScheduledTask(_task("long", order=1, preferred=4), long),
        )
    )
    assert values[1] == 4
    report = scheduler.last_report
    assert report is not None
    long_report = next(item for item in report.tasks if item.task_id == "long")
    assert long_report.maximum_workers == 4


def test_memory_admission_serializes_tasks_when_parallel_peaks_do_not_fit() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=4, memory=100))
    values = scheduler.run(
        (
            DensityScheduledTask(
                _task("a", order=0, retained=10, transient=60), lambda _lease: "a"
            ),
            DensityScheduledTask(
                _task("b", order=1, retained=10, transient=60), lambda _lease: "b"
            ),
        )
    )
    assert values == ("a", "b")
    assert scheduler.last_report is not None
    assert scheduler.last_report.maximum_concurrent_tasks == 1
    assert scheduler.last_report.peak_reserved_bytes <= 100


def test_task_budget_scope_clamps_nested_native_worker_budget() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=8, memory=10_000))
    resources = _task("bounded", order=0, retained=100, transient=100, preferred=3)

    def inspect(lease):
        nested = resolve_runtime_resource_budget()
        return lease.workers, nested.max_threads, nested.max_memory_bytes

    ((workers, nested_threads, nested_memory),) = scheduler.run(
        (DensityScheduledTask(resources, inspect),)
    )
    assert workers == 3
    assert nested_threads == 3
    assert nested_memory == scheduler.budget.max_memory_bytes


def test_thread_and_process_worker_modes_are_bounded_by_same_lease() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=2, memory=10_000))

    def thread_work(lease):
        return lease.thread_map(_square, [1, 2, 3, 4])

    def process_work(lease):
        return lease.process_map(_square, [1, 2, 3, 4])

    values = scheduler.run(
        (
            DensityScheduledTask(
                _task(
                    "threads",
                    order=0,
                    preferred=2,
                    mode=DensityTaskExecutionMode.PYTHON_THREADS,
                ),
                thread_work,
            ),
            DensityScheduledTask(
                _task(
                    "processes",
                    order=1,
                    preferred=2,
                    mode=DensityTaskExecutionMode.PYTHON_PROCESSES,
                ),
                process_work,
            ),
        )
    )
    assert values[0] == [1, 4, 9, 16]
    assert values[1] == [1, 4, 9, 16]
    assert scheduler.last_report is not None
    assert all(item.maximum_workers <= 2 for item in scheduler.last_report.tasks)


def test_sync_task_scope_preserves_calling_thread_and_records_allocation() -> None:
    scheduler = DensitySceneScheduler(
        _budget(threads=4, memory=1000),
        policy=DensitySchedulerPolicy(max_parallel_tasks=1),
    )
    resources = _task("scene", order=0, retained=100, transient=300, preferred=4)
    with scheduler.task_scope(resources) as lease:
        assert lease.workers == 4
        assert resolve_runtime_resource_budget().max_threads == 4
    assert scheduler.last_report is not None
    assert scheduler.last_report.peak_reserved_bytes == 400


def test_failed_parent_preserves_primary_failure_and_blocks_child() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=2, memory=1_000))
    child_started = False

    def fail_parent(_lease):
        raise ValueError("parent boom")

    def child(_lease):
        nonlocal child_started
        child_started = True
        return "child"

    with pytest.raises(DensitySchedulerTaskError, match="parent boom") as excinfo:
        scheduler.run(
            (
                DensityScheduledTask(_task("parent", order=0, preferred=1), fail_parent),
                DensityScheduledTask(
                    _task("child", order=1, preferred=1, parent="parent"), child
                ),
            )
        )
    assert excinfo.value.task_id == "parent"
    assert child_started is False


def test_scheduler_prioritizes_high_peak_task_to_avoid_retained_memory_stranding() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=3, memory=100))
    starts: list[str] = []

    def run(name: str):
        def inner(_lease):
            starts.append(name)
            return name
        return inner

    values = scheduler.run(
        (
            DensityScheduledTask(_task("small-a", order=0, retained=10, transient=20), run("small-a")),
            DensityScheduledTask(_task("small-b", order=1, retained=10, transient=20), run("small-b")),
            DensityScheduledTask(_task("large", order=2, retained=10, transient=80), run("large")),
        )
    )
    # If the two small outputs were committed first, the 90-byte large task
    # could no longer fit under the 100-byte scene budget.  Memory-heavy-first
    # admission finds the feasible execution schedule while preserving the
    # caller-visible construction order.
    assert starts[0] == "large"
    assert values == ("small-a", "small-b", "large")
    assert scheduler.last_report is not None
    assert scheduler.last_report.peak_reserved_bytes <= 100
