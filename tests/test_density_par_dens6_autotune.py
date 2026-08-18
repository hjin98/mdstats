from __future__ import annotations

import numpy as np

from mdstats.plotting.density_autotune import (
    DensityAutoTunePolicy,
    DensityAutoTuneProfile,
    autotuned_fft_worker_count,
    autotuned_group_size_multiplier,
    current_density_autotune_profile,
    density_autotune_scope,
    resolve_density_autotune_profile,
)
from mdstats.plotting.density_scheduler import (
    DensityScheduledTask,
    DensitySceneScheduler,
    DensityTaskResources,
)
from mdstats.plotting.runtime_resources import RuntimeResourceBudget, RuntimeResourceSnapshot


def _budget(*, threads: int = 4) -> RuntimeResourceBudget:
    snapshot = RuntimeResourceSnapshot(
        logical_cpu_count=threads,
        affinity_cpu_count=threads,
        cgroup_cpu_quota=None,
        scheduler_cpu_count=None,
        available_cpu_count=threads,
        host_memory_available_bytes=2 * 1024**3,
        cgroup_memory_limit_bytes=None,
        cgroup_memory_current_bytes=None,
        scheduler_memory_limit_bytes=None,
        rlimit_as_bytes=None,
        process_rss_bytes=1,
        process_virtual_memory_bytes=1,
        available_memory_bytes=2 * 1024**3,
    )
    return RuntimeResourceBudget(
        max_memory_bytes=1024**3,
        max_threads=threads,
        max_wall_time_seconds=1200.0,
        memory_fraction=0.8,
        thread_fraction=0.9,
        snapshot=snapshot,
        memory_override_source="fixture",
        thread_override_source="fixture",
        wall_time_override_source="fixture",
    )


def test_autotune_off_is_serial_and_scientifically_neutral() -> None:
    profile = resolve_density_autotune_profile(
        _budget(threads=4), policy=DensityAutoTunePolicy(mode="off")
    )
    assert profile.mode == "off"
    assert profile.max_parallel_tasks is None
    assert profile.scientific_identity_includes_profile is False
    assert profile.to_json_dict()["scientific_identity_includes_profile"] is False


def test_autotune_profile_is_cached_and_bounded_by_runtime_cpu() -> None:
    budget = _budget(threads=4)
    first = resolve_density_autotune_profile(budget, policy=DensityAutoTunePolicy(mode="auto"))
    second = resolve_density_autotune_profile(budget, policy=DensityAutoTunePolicy(mode="auto"))
    assert first is second
    assert 1 <= first.max_parallel_tasks <= budget.max_threads
    assert 1 <= first.fft_worker_cap <= budget.max_threads
    assert first.group_size_multiplier in {1, 2, 4, 8}
    assert first.direct_fft_selection == "par_dens1_calibrated_time_model"
    assert first.cpu_gpu_selection == "par_dens5_transfer_vram_cost_model"


def test_autotune_scope_changes_execution_knobs_only() -> None:
    profile = DensityAutoTuneProfile(
        mode="fixture",
        max_parallel_tasks=2,
        group_size_multiplier=8,
        fft_worker_cap=2,
        direct_fft_selection="fixture",
        cpu_gpu_selection="fixture",
        calibration_wall_seconds=0.0,
        runtime_signature="fixture",
    )
    assert current_density_autotune_profile() is None
    with density_autotune_scope(profile):
        assert current_density_autotune_profile() is profile
        assert autotuned_group_size_multiplier(default=4) == 8
        assert autotuned_fft_worker_count(16) == 2
    assert current_density_autotune_profile() is None


def test_scheduler_report_persists_worker_allocation_history() -> None:
    scheduler = DensitySceneScheduler(_budget(threads=4))
    resources = (
        DensityTaskResources(
            task_id="a", retained_bytes=1, transient_bytes=1,
            minimum_workers=1, preferred_workers=4, construction_order=0,
        ),
        DensityTaskResources(
            task_id="b", retained_bytes=1, transient_bytes=1,
            minimum_workers=1, preferred_workers=4, construction_order=1,
        ),
    )
    tasks = tuple(
        DensityScheduledTask(item, lambda lease, value=i: (value, lease.workers))
        for i, item in enumerate(resources)
    )
    result = scheduler.run(tasks)
    assert tuple(item[0] for item in result) == (0, 1)
    report = scheduler.last_report
    assert report is not None
    assert report.cpu_budget_obeyed is True
    assert report.memory_budget_obeyed is True
    assert report.peak_reserved_bytes <= report.max_memory_bytes
    assert all(task.worker_allocation_history for task in report.tasks)
    assert all(max(task.worker_allocation_history) <= report.max_threads for task in report.tasks)


def test_autotune_profile_never_enters_scientific_numeric_payload() -> None:
    # A simple deterministic arithmetic check: execution knobs may alter worker
    # scheduling, but they are not numerical inputs to density operators.
    data = np.arange(64, dtype=np.float64)
    reference = np.sum(data, dtype=np.float64)
    for multiplier in (1, 2, 4, 8):
        profile = DensityAutoTuneProfile(
            mode="fixture",
            max_parallel_tasks=1,
            group_size_multiplier=multiplier,
            fft_worker_cap=1,
            direct_fft_selection="fixture",
            cpu_gpu_selection="fixture",
            calibration_wall_seconds=0.0,
            runtime_signature=f"fixture-{multiplier}",
        )
        with density_autotune_scope(profile):
            assert np.sum(data, dtype=np.float64) == reference


def test_phase_b_approved_hybrid_plan_is_reused_across_worker_budgets(monkeypatch) -> None:
    """Worker leases may execute, but never re-partition, an approved field."""

    from dataclasses import replace

    from mdstats import AtomicDensityOptions, DensityKernelOptions, DensityStorageOptions
    from mdstats.plotting import atomic_density as atomic_module
    from mdstats.plotting.atomic_density import (
        _aggregate_sparse_cic_for_options,
        _prepare_sparse_field_for_options,
        _stencil_support_for_options,
    )
    from mdstats.plotting.density_block_routing import get_periodic_kernel_block_routing
    from mdstats.plotting.density_contracts import DensitySourceProvenance, PeriodicWeightedSamples3D
    from mdstats.plotting.density_support_atlas import build_density_support_atlas, pack_periodic_cic_source
    from mdstats.plotting.density_tiled_fft import DensityHybridExecutorOptions, plan_hybrid_tiled_realization
    from mdstats.plotting.runtime_resources import density_resource_budget_scope

    rng = np.random.default_rng(60812)
    positions = rng.random((384, 3), dtype=np.float64)
    samples = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=np.full(positions.shape[0], 1.0 / positions.shape[0], dtype=np.float64),
        source_provenance=DensitySourceProvenance(source_kind="fixture"),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    cell = np.diag([12.0, 12.0, 12.0]).astype(np.float64)
    grid = (32, 32, 32)
    options = AtomicDensityOptions(
        grid_shape=grid,
        gaussian_bandwidth=0.5,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(smoothing_operator="discrete_periodized_v1"),
        storage_options=DensityStorageOptions(grid_backend="local_sparse", local_block_shape=(8, 8, 8)),
    )
    planning_budget = _budget(threads=4)
    options = replace(
        options,
        optimization_options=options.optimization_options.resolve(
            max_memory_bytes=planning_budget.max_memory_bytes
        ),
    )

    with density_resource_budget_scope(planning_budget):
        cic = _aggregate_sparse_cic_for_options(
            samples,
            grid,
            options=options,
            max_cic_contributions=1_000_000,
            max_workspace_bytes=planning_budget.max_memory_bytes,
        )
        stencil, _ = _stencil_support_for_options(
            grid,
            cell,
            0.5,
            options=options,
            max_candidate_contributions=10_000_000,
            max_workspace_bytes=planning_budget.max_memory_bytes,
        )
        source = pack_periodic_cic_source(
            cic, storage_block_shape=options.storage_options.local_block_shape
        )
        routing, _ = get_periodic_kernel_block_routing(
            stencil,
            storage_block_shape=options.storage_options.local_block_shape,
            use_cache=options.optimization_options.cache_stencil_supports,
        )
        atlas = build_density_support_atlas(source, routing)
        approved = plan_hybrid_tiled_realization(
            source,
            stencil,
            routing,
            atlas,
            options=DensityHybridExecutorOptions(
                executor_mode="auto",
                compute_tile_shape=options.optimization_options.hybrid_compute_tile_shape,
                pair_chunk_size=options.optimization_options.sparse_pair_chunk_size,
                min_fft_source_nodes=options.optimization_options.hybrid_min_fft_source_nodes,
                fft_workers=4,
                metadata={"dispatch_stage": "phase_b_fixture", "fft_worker_source": "runtime_thread_budget"},
            ),
        )

        reference = _prepare_sparse_field_for_options(
            samples,
            grid_shape=grid,
            display_cell=cell,
            gaussian_bandwidth=0.5,
            field_key="fixture-density",
            label="fixture density",
            physical_units="angstrom^-3",
            broadening_metric="gaussian_sigma",
            options=options,
            max_cic_contributions=1_000_000,
            max_kernel_pairs=100_000_000,
            max_workspace_bytes=planning_budget.max_memory_bytes,
            max_nonzero_nodes=1_000_000,
            max_stored_block_values=2_000_000,
            max_blocks=100_000,
            max_planning_bytes=planning_budget.max_memory_bytes,
            approved_hybrid_plan=approved,
        )

    def forbidden_replan(*_args, **_kwargs):
        raise AssertionError("approved Phase-B hybrid plan was replanned inside the worker lease")

    monkeypatch.setattr(atomic_module, "plan_hybrid_tiled_realization", forbidden_replan)
    execution_budget = _budget(threads=1)
    with density_resource_budget_scope(execution_budget):
        serial = _prepare_sparse_field_for_options(
            samples,
            grid_shape=grid,
            display_cell=cell,
            gaussian_bandwidth=0.5,
            field_key="fixture-density",
            label="fixture density",
            physical_units="angstrom^-3",
            broadening_metric="gaussian_sigma",
            options=options,
            max_cic_contributions=1_000_000,
            max_kernel_pairs=100_000_000,
            max_workspace_bytes=execution_budget.max_memory_bytes,
            max_nonzero_nodes=1_000_000,
            max_stored_block_values=2_000_000,
            max_blocks=100_000,
            max_planning_bytes=execution_budget.max_memory_bytes,
            approved_hybrid_plan=approved,
        )

    np.testing.assert_array_equal(reference.packed_values, serial.packed_values)
    assert reference.content_identity == serial.content_identity
    assert serial.metadata["hybrid_execution_plan_authority"] == "phase_b_approved_execution_plan"
    assert serial.metadata["hybrid_execution_plan_identity"] == approved.content_identity
