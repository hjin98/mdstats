from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting.density_block_direct import realize_density_target_owned_direct
from mdstats.plotting.density_block_routing import build_periodic_kernel_block_routing
from mdstats.plotting.density_contracts import DensitySourceProvenance
from mdstats.plotting.density_kernel import PeriodicGaussianStencilSupport
from mdstats.plotting.density_sparse_reference import SparseCICNodeMasses3D
from mdstats.plotting.density_support_atlas import build_density_support_atlas, pack_periodic_cic_source
from mdstats.plotting.density_tiled_fft import (
    DensityHybridExecutorOptions,
    DensityHybridRealizationLimits,
    DensityHybridRealizationPlan,
    plan_hybrid_tiled_realization,
    realize_density_hybrid_tiled,
)
from mdstats.plotting.graph_errors import GraphAdapterError, GraphComplexityError
from mdstats.plotting.density_scheduler import (
    DensityScheduledTask,
    DensitySceneScheduler,
    DensityTaskResources,
)
from mdstats.plotting.runtime_resources import RuntimeResourceBudget, RuntimeResourceSnapshot


def _stencil(shape: tuple[int, int, int], radius: int = 2) -> PeriodicGaussianStencilSupport:
    signed = np.asarray(
        [
            (x, y, z)
            for x in range(-radius, radius + 1)
            for y in range(-radius, radius + 1)
            for z in range(-radius, radius + 1)
            if x * x + y * y + z * z <= radius * radius
        ],
        dtype=np.int64,
    )
    canonical = signed % np.asarray(shape, dtype=np.int64)
    flat = np.ravel_multi_index(canonical.T, shape, order="C")
    order = np.argsort(flat)
    flat = flat[order]
    signed = signed[order]
    raw = np.exp(-0.5 * np.sum(signed * signed, axis=1, dtype=np.float64))
    weights = raw / np.sum(raw)
    return PeriodicGaussianStencilSupport(
        grid_shape=shape,
        display_cell=np.diag(np.asarray(shape, dtype=np.float64)),
        gaussian_bandwidth=1.0,
        kernel_tail_tolerance=1.0e-8,
        cutoff_radius=float(radius),
        active_flat_indices=flat,
        active_weights=weights,
        pre_normalization_sum=float(np.sum(raw)),
        normalization_factor=float(1.0 / np.sum(raw)),
        periodic_image_contribution_count=int(flat.size),
        covariance=np.eye(3, dtype=np.float64),
        metadata={"fixture": True},
    )


def _case(
    shape: tuple[int, int, int],
    coordinates: np.ndarray,
    *,
    block: tuple[int, int, int] = (4, 4, 4),
    radius: int = 2,
):
    coordinates = np.asarray(coordinates, dtype=np.int64) % np.asarray(shape)
    flat = np.ravel_multi_index(coordinates.T, shape, order="C")
    order = np.argsort(flat)
    flat = flat[order]
    masses = np.arange(1, flat.size + 1, dtype=np.float64)
    masses /= np.sum(masses)
    cic = SparseCICNodeMasses3D(
        grid_shape=shape,
        flat_indices=flat,
        node_masses=masses,
        total_measure=1.0,
        source_provenance=DensitySourceProvenance(source_kind="test"),
        metadata={"fixture": True},
    )
    stencil = _stencil(shape, radius=radius)
    source = pack_periodic_cic_source(cic, storage_block_shape=block)
    routing = build_periodic_kernel_block_routing(stencil, storage_block_shape=block)
    atlas = build_density_support_atlas(source, routing)
    return stencil, source, routing, atlas


def _realize(case, mode: str, *, tile=(8, 8, 8), min_fft=2, pair_chunk=4096):
    stencil, source, routing, atlas = case
    options = DensityHybridExecutorOptions(
        executor_mode=mode,
        compute_tile_shape=tile,
        min_fft_source_nodes=min_fft,
        pair_chunk_size=pair_chunk,
    )
    plan = plan_hybrid_tiled_realization(source, stencil, routing, atlas, options=options)
    field = realize_density_hybrid_tiled(
        source,
        stencil,
        routing,
        atlas,
        field_key="fixture",
        label="Fixture",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        approved_plan=plan,
    )
    return plan, field


def _canonical(case):
    stencil, source, routing, atlas = case
    return realize_density_target_owned_direct(
        source,
        stencil,
        routing,
        atlas,
        field_key="fixture",
        label="Fixture",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
    )


def _relative_l1(first, second) -> float:
    assert np.array_equal(first.active_block_indices, second.active_block_indices)
    assert np.array_equal(first.occupancy_bitsets, second.occupancy_bitsets)
    return float(
        np.sum(np.abs(first.packed_values - second.packed_values), dtype=np.float64)
        / np.sum(np.abs(second.packed_values), dtype=np.float64)
    )


@pytest.mark.parametrize(
    ("shape", "coordinates"),
    [
        ((17, 18, 19), np.asarray([(0, 0, 0), (16, 17, 18), (8, 9, 10), (2, 14, 1)])),
        ((9, 10, 11), np.asarray([(8, 9, 10), (0, 9, 0), (4, 0, 10), (3, 5, 6)])),
    ],
)
def test_forced_direct_and_fft_match_canonical_on_periodic_terminal_grids(shape, coordinates) -> None:
    case = _case(shape, coordinates)
    reference = _canonical(case)
    direct_plan, direct = _realize(case, "direct", tile=(8, 8, 8), pair_chunk=31)
    fft_plan, fft = _realize(case, "fft", tile=(8, 8, 8))
    assert direct_plan.fft_tile_count == 0
    assert fft_plan.direct_tile_count == 0
    assert _relative_l1(direct, reference) < 5.0e-12
    assert _relative_l1(fft, reference) < 5.0e-11
    assert direct.integral == pytest.approx(1.0, abs=5.0e-13)
    assert fft.integral == pytest.approx(1.0, abs=5.0e-13)
    assert fft.metadata["global_dense_logical_grid_allocated"] is False


def test_auto_selector_uses_mixed_executors_and_caches_kernel_spectrum() -> None:
    shape = (32, 16, 16)
    sparse = np.asarray([(1, 1, 1)], dtype=np.int64)
    dense = np.column_stack(
        np.unravel_index(np.arange(80, dtype=np.int64), (8, 8, 8), order="C")
    ) + np.asarray((16, 0, 0), dtype=np.int64)
    case = _case(shape, np.concatenate((sparse, dense), axis=0), block=(4, 4, 4))
    options = DensityHybridExecutorOptions(
        executor_mode="auto",
        compute_tile_shape=(16, 16, 16),
        min_fft_source_nodes=16,
        direct_pair_seconds=2.0e-4,
        fft_work_seconds=1.0e-10,
        fft_fixed_seconds=1.0e-5,
    )
    stencil, source, routing, atlas = case
    plan = plan_hybrid_tiled_realization(source, stencil, routing, atlas, options=options)
    assert plan.direct_tile_count == 1
    assert plan.fft_tile_count == 1
    field = realize_density_hybrid_tiled(
        source,
        stencil,
        routing,
        atlas,
        field_key="mixed",
        label="Mixed",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        approved_plan=plan,
    )
    reference = _canonical(case)
    assert _relative_l1(field, reference) < 5.0e-11
    assert field.metadata["direct_tile_count"] == 1
    assert field.metadata["fft_tile_count"] == 1


def test_fft_kernel_spectrum_is_reused_for_equal_tile_shapes() -> None:
    shape = (32, 16, 16)
    first = np.column_stack(np.unravel_index(np.arange(40), (8, 8, 8), order="C"))
    second = first + np.asarray((16, 0, 0))
    case = _case(shape, np.concatenate((first, second)), block=(4, 4, 4))
    plan, field = _realize(case, "fft", tile=(16, 16, 16))
    assert plan.fft_tile_count == 2
    assert plan.kernel_spectrum_cache_bytes > 0
    assert field.metadata["fft_kernel_transform_count"] == 1
    assert field.metadata["cached_fft_kernel_shape_count"] == 1


def test_plan_round_trip_and_repeated_fft_are_numerically_reproducible() -> None:
    case = _case((20, 21, 22), np.asarray([(0, 0, 0), (19, 20, 21), (5, 6, 7), (15, 3, 18)]))
    stencil, source, routing, atlas = case
    options = DensityHybridExecutorOptions(executor_mode="fft", compute_tile_shape=(8, 8, 8))
    plan = plan_hybrid_tiled_realization(source, stencil, routing, atlas, options=options)
    restored = DensityHybridRealizationPlan.from_json_dict(plan.to_json_dict())
    assert restored.content_identity == plan.content_identity
    first = realize_density_hybrid_tiled(
        source, stencil, routing, atlas,
        field_key="fixture", label="Fixture", physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1", approved_plan=restored,
    )
    second = realize_density_hybrid_tiled(
        source, stencil, routing, atlas,
        field_key="fixture", label="Fixture", physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1", approved_plan=restored,
    )
    assert np.array_equal(first.packed_values, second.packed_values)
    assert first.content_identity == second.content_identity


def test_hybrid_limits_and_identity_mismatch_fail_transactionally() -> None:
    case = _case((16, 16, 16), np.asarray([(0, 0, 0), (8, 8, 8)]))
    stencil, source, routing, atlas = case
    with pytest.raises(GraphComplexityError, match="max_target_nodes"):
        plan_hybrid_tiled_realization(
            source, stencil, routing, atlas,
            limits=DensityHybridRealizationLimits(max_target_nodes=1),
        )
    plan = plan_hybrid_tiled_realization(source, stencil, routing, atlas)
    other = _case((16, 16, 16), np.asarray([(1, 0, 0), (8, 8, 8)]))
    with pytest.raises(GraphAdapterError, match="identities"):
        realize_density_hybrid_tiled(
            other[1], other[0], other[2], other[3],
            field_key="fixture", label="Fixture", physical_units="count / angstrom^3",
            broadening_metric="effective_cic_stencil_rms_v1", approved_plan=plan,
        )


def test_direct_tile_transient_is_bounded_by_actual_pairs_not_full_chunk() -> None:
    case = _case((16, 16, 16), np.asarray([(1, 1, 1)], dtype=np.int64))
    stencil, source, routing, atlas = case
    options = DensityHybridExecutorOptions(
        executor_mode="direct",
        compute_tile_shape=(16, 16, 16),
        pair_chunk_size=262_144,
    )
    plan = plan_hybrid_tiled_realization(
        source, stencil, routing, atlas, options=options
    )
    assert plan.direct_tile_count == 1
    tile = plan.tile_plans[0]
    assert tile.direct_pair_count < options.pair_chunk_size
    assert tile.transient_bytes_estimate == 112 * tile.direct_pair_count



def _scheduler_budget(*, threads: int = 4, memory: int = 256 * 1024**2) -> RuntimeResourceBudget:
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


def test_parallel_direct_chunk_preserves_exact_serial_reduction_order() -> None:
    shape = (64, 64, 64)
    coordinates = np.column_stack(
        np.unravel_index(np.arange(512, dtype=np.int64), (16, 16, 16), order="C")
    ) + np.asarray((8, 8, 8), dtype=np.int64)
    case = _case(shape, coordinates, block=(8, 8, 8), radius=2)
    stencil, source, routing, atlas = case
    options = DensityHybridExecutorOptions(
        executor_mode="direct",
        compute_tile_shape=(32, 32, 32),
        pair_chunk_size=8192,
    )
    plan = plan_hybrid_tiled_realization(
        source, stencil, routing, atlas, options=options
    )
    serial = realize_density_hybrid_tiled(
        source, stencil, routing, atlas,
        field_key="fixture", label="Fixture", physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1", approved_plan=plan,
    )

    resources = DensityTaskResources(
        task_id="parallel-direct",
        retained_bytes=0,
        transient_bytes=64 * 1024**2,
        minimum_workers=1,
        preferred_workers=4,
        backend="test",
        construction_order=0,
    )
    scheduler = DensitySceneScheduler(_scheduler_budget(threads=4))

    progress_events = []

    def realize(_lease):
        return realize_density_hybrid_tiled(
            source, stencil, routing, atlas,
            field_key="fixture", label="Fixture", physical_units="count / angstrom^3",
            broadening_metric="effective_cic_stencil_rms_v1", approved_plan=plan,
            progress=progress_events.append,
        )

    parallel = scheduler.run((DensityScheduledTask(resources, realize),))[0]
    assert np.array_equal(parallel.active_block_indices, serial.active_block_indices)
    assert np.array_equal(parallel.occupancy_bitsets, serial.occupancy_bitsets)
    assert np.array_equal(parallel.packed_values, serial.packed_values)
    assert parallel.metadata["parallel_direct_chunk_count"] > 0
    assert parallel.metadata["maximum_direct_workers_used"] == 4
    assert parallel.metadata["direct_parallelism_preserves_canonical_reduction_order"] is True
    stages = [event.stage for event in progress_events]
    assert "hybrid_sparse_realization" in stages
    assert "hybrid_direct_realization" in stages
    final_direct = [event for event in progress_events if event.stage == "hybrid_direct_realization"][-1]
    assert final_direct.current == final_direct.total == plan.direct_pair_count

def test_hybrid_wall_time_target_is_advisory_only() -> None:
    case = _case((16, 16, 16), np.asarray([(1, 1, 1), (8, 8, 8)], dtype=np.int64))
    stencil, source, routing, atlas = case
    options = DensityHybridExecutorOptions(
        executor_mode="direct",
        compute_tile_shape=(16, 16, 16),
        direct_pair_seconds=1.0,
    )
    plan = plan_hybrid_tiled_realization(
        source,
        stencil,
        routing,
        atlas,
        options=options,
        limits=DensityHybridRealizationLimits(max_wall_time_seconds=1.0e-6),
    )
    assert plan.metadata["estimated_wall_seconds"] > plan.metadata["max_wall_time_seconds"]
    assert plan.metadata["wall_time_admission_enforced"] is False
    assert plan.metadata["wall_time_budget_exceeded"] is True
