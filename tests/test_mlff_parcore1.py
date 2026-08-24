from __future__ import annotations

from threading import Barrier
import time

import pytest

import mdstats


def _scope(*, workers: int = 3, ram: int | None = 1 << 20) -> mdstats.StageResourceScope:
    return mdstats.StageResourceScope(
        stage_name="PARCORE1-test",
        cpu_threads_available=max(4, workers),
        cpu_threads_budget=max(4, workers),
        python_workers=workers,
        tree_workers=1,
        blas_threads=1,
        ram_budget_bytes=ram,
    )


def test_ordered_reducer_commits_only_in_canonical_order() -> None:
    committed: list[tuple[int, str]] = []
    reducer = mdstats.DeterministicOrderedReducer(
        (0, 10, 20), commit=lambda key, value: committed.append((int(key), str(value)))
    )
    assert reducer.push(20, "c") == 0
    assert reducer.push(10, "b") == 0
    assert committed == []
    assert reducer.buffered_count == 2
    assert reducer.push(0, "a") == 3
    assert committed == [(0, "a"), (10, "b"), (20, "c")]
    assert reducer.complete


def test_shared_queue_is_work_conserving_bounded_and_deterministic() -> None:
    barrier = Barrier(3, timeout=2.0)

    def work(value: int) -> int:
        barrier.wait()
        time.sleep(0.005)
        return value * value

    with mdstats.DeterministicWorkQueue(
        _scope(workers=3), max_ready_tasks=6, max_completed_tasks=6,
        heartbeat_interval_seconds=0.05,
    ) as queue:
        for value in range(3):
            queue.submit(
                task_id=f"task-{value}",
                canonical_order=(value,),
                function=work,
                args=(value,),
                estimated_memory_bytes=1024,
                locality_key="node-0",
            )
        completed_items = []
        while len(completed_items) < 3:
            assert queue.wait_for_completion(timeout=2.0)
            completed_items.extend(queue.drain_completed())
        completed = tuple(sorted(completed_items, key=lambda item: item.canonical_order))
        assert [item.task_id for item in completed] == ["task-0", "task-1", "task-2"]
        assert [item.value for item in completed] == [0, 1, 4]
        snapshot = queue.snapshot()
        assert snapshot.max_busy_workers == 3
        assert snapshot.outstanding_tasks == 0
        assert snapshot.peak_accounted_memory_bytes <= (1 << 20)


def test_memory_reservation_applies_backpressure_then_releases() -> None:
    scope = _scope(workers=1, ram=100)
    with mdstats.DeterministicWorkQueue(scope, max_ready_tasks=2) as queue:
        queue.reserve_memory("persistent", 60)
        queue.submit(
            task_id="memory-bound",
            canonical_order=(0,),
            function=lambda: 7,
            estimated_memory_bytes=50,
        )
        blocked = queue.snapshot()
        assert blocked.ready_tasks == 1
        assert blocked.inflight_tasks == 0
        assert blocked.memory_backpressure_events >= 1
        queue.release_memory("persistent")
        assert queue.wait_for_completion(timeout=1.0)
        result = queue.drain_completed()
        assert len(result) == 1 and result[0].value == 7


def test_worker_exception_carries_deterministic_task_identity() -> None:
    def fail() -> None:
        raise RuntimeError("synthetic failure")

    with mdstats.DeterministicWorkQueue(_scope(workers=1)) as queue:
        queue.submit(
            task_id="domain-2/family-4/block-8",
            canonical_order=(2, 4, 8),
            function=fail,
            task_kind="witness-block",
        )
        with pytest.raises(mdstats.DeterministicWorkQueueTaskError) as captured:
            queue.wait_for_completion(timeout=1.0)
        assert captured.value.task_id == "domain-2/family-4/block-8"
        assert captured.value.task_kind == "witness-block"
        assert "synthetic failure" in str(captured.value)


def test_stage_resource_scope_propagates_ram_budget() -> None:
    resources = mdstats.training_data.resources.SystemResourceSnapshot(
        cpu_threads_available=8,
        cpu_fraction=0.5,
        cpu_threads_budget=4,
        ram_available_bytes=1000,
        ram_fraction=0.8,
        ram_budget_bytes=800,
        gpu_memory_fraction=0.9,
        gpu=mdstats.training_data.resources.GpuResourceSnapshot(
            False, 0, None, None, None, None, None, "test"
        ),
    )
    scope = mdstats.build_stage_resource_scope(
        resources, stage_name="test", python_workers=2, blas_threads=1
    )
    assert scope.ram_budget_bytes == 800
    assert scope.estimated_nested_cpu_threads == 2


def test_feas1_implicit_scope_is_not_bound_to_transient_host_free_ram(monkeypatch, tmp_path):
    """Direct FEAS1 API remains deterministic when shared-host free RAM fluctuates.

    Campaign callers provide an explicit StageResourceScope and retain strict
    RAM admission.  The implicit direct-API scope must not manufacture a hard
    limit from a transient cgroup snapshot.
    """
    import mdstats
    import mdstats.training_data.resources as resources_module
    from tests.test_mlff_target_data2b_coverage import _build_coverage_inputs

    _, _, _, data4, data5, data6, freeze, audit = _build_coverage_inputs(tmp_path)
    reference = mdstats.build_target_coverage_reference(data4, data5, data6, freeze, audit)
    monkeypatch.setattr(resources_module, "available_memory_bytes", lambda: 1)
    report = mdstats.build_target_coverage_feasibility_report(
        reference, freeze, query_block_size=8
    )
    assert report.domains


def test_neighbor1_implicit_scope_is_not_bound_to_transient_host_free_ram(monkeypatch):
    """Direct NEIGHBOR1 reconstruction is independent of transient free RAM."""
    import mdstats
    import mdstats.training_data.resources as resources_module
    from tests.test_mlff_target_data2b_feas1 import _reference_and_role

    reference, _ = _reference_and_role(split_units=True)
    monkeypatch.setattr(resources_module, "available_memory_bytes", lambda: 1)
    store = mdstats.build_target_coverage_exact_neighborhood_store(
        reference,
        global_workers=1,
        query_workers=1,
        query_block_size=3,
    )
    assert store.domains


def test_mvidx_implicit_scope_is_not_bound_to_transient_host_free_ram(monkeypatch):
    """Direct parallel MVIDX inversion is independent of transient free RAM."""
    import mdstats
    import mdstats.training_data.resources as resources_module
    from tests.test_mlff_target_data2b_feas1 import _reference_and_role

    reference, role = _reference_and_role(split_units=True)
    feasibility = mdstats.build_target_coverage_feasibility_report(reference, role)
    neighborhoods = mdstats.build_target_coverage_exact_neighborhood_store(
        reference, global_workers=1, query_workers=1, query_block_size=3
    )
    monkeypatch.setattr(resources_module, "available_memory_bytes", lambda: 1)
    index = mdstats.build_target_coverage_sparse_index(
        reference,
        role,
        feasibility,
        exact_neighborhood_store=neighborhoods,
        query_workers=1,
        global_workers=2,
        query_block_size=3,
    )
    assert index.domains


def test_try_reserve_memory_backpressures_transient_contention_but_rejects_intrinsic_oversize() -> None:
    scope = _scope(workers=1, ram=100)
    with mdstats.DeterministicWorkQueue(scope, max_ready_tasks=1) as queue:
        queue.reserve_memory("primary", 80)
        assert not queue.try_reserve_memory("secondary", 30)
        blocked = queue.snapshot()
        assert blocked.reserved_memory_bytes == 80
        assert blocked.memory_backpressure_events >= 1
        queue.release_memory("primary")
        assert queue.try_reserve_memory("secondary", 30)
        queue.release_memory("secondary")
        with pytest.raises(mdstats.DeterministicWorkQueueMemoryError, match="intrinsically requires 101 bytes"):
            queue.try_reserve_memory("impossible", 101)


def test_reservation_failure_reports_live_memory_breakdown() -> None:
    scope = _scope(workers=1, ram=100)
    with mdstats.DeterministicWorkQueue(scope, max_ready_tasks=1) as queue:
        queue.reserve_memory("primary", 80)
        with pytest.raises(mdstats.DeterministicWorkQueueMemoryError) as captured:
            queue.reserve_memory("secondary", 30)
        message = str(captured.value)
        assert "available=20" in message
        assert "reserved=80" in message
        assert "stage-budget=100" in message
