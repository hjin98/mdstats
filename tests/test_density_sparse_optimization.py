"""LD5 exact sparse-density optimization and cache tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting import (
    AtomicDensityOptions,
    DensityKernelOptions,
    DensityOptimizationOptions,
    DensityStorageOptions,
    DensitySourceProvenance,
    PeriodicWeightedSamples3D,
    aggregate_periodic_cic_sparse,
    aggregate_periodic_cic_sparse_optimized,
    clear_density_optimization_caches,
    density_optimization_cache_info,
    get_periodic_gaussian_stencil_support,
    prepare_sparse_canonical_density_optimized,
    prepare_sparse_canonical_density_reference,
    plan_group_batched_sparse_targets_optimized,
    plan_sparse_target_nodes,
    plan_sparse_target_nodes_optimized,
)
from mdstats.plotting.atomic_density import _select_atomic_auto_backend
from mdstats.plotting.density_contracts import DISCRETE_PERIODIZED_OPERATOR
from mdstats.plotting.graph_errors import GraphComplexityError
from mdstats.plotting.density_sparse_optimization import (
    _apply_total_mass_correction,
)


def lta_cell(scale: float = 1.0) -> np.ndarray:
    return scale * np.asarray(
        [
            [3.0, 0.0, 0.0],
            [1.5, 2.598076211353316, 0.0],
            [1.5, 0.8660254037844386, 2.449489742783178],
        ],
        dtype=np.float64,
    )


def sample_batch(
    positions: np.ndarray,
    weights: np.ndarray | None = None,
) -> PeriodicWeightedSamples3D:
    positions = np.asarray(positions, dtype=np.float64)
    if weights is None:
        weights = np.full(positions.shape[0], 1.0 / positions.shape[0])
    weights = np.asarray(weights, dtype=np.float64)
    return PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy"
        ),
        total_measure=float(np.sum(weights, dtype=np.float64)),
        measure_kind="occupancy",
        measure_units="count",
    )


def reference_and_optimized(
    batch: PeriodicWeightedSamples3D,
    *,
    shape: tuple[int, int, int],
    cell: np.ndarray,
    sigma: float,
):
    kwargs = dict(
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="density",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        max_workspace_bytes=1_000_000_000,
    )
    reference = prepare_sparse_canonical_density_reference(batch, **kwargs)
    optimized = prepare_sparse_canonical_density_optimized(
        batch,
        pair_chunk_size=257,
        cache_stencil_supports=False,
        **kwargs,
    )
    return reference, optimized


@pytest.mark.parametrize(
    ("shape", "cell"),
    [
        ((11, 10, 9), np.diag([5.5, 5.0, 4.5])),
        ((12, 11, 10), lta_cell(1.8)),
    ],
)
def test_optimized_cic_matches_reference(
    shape: tuple[int, int, int], cell: np.ndarray
) -> None:
    del cell
    rng = np.random.default_rng(8102)
    batch = sample_batch(rng.random((73, 3)), rng.random(73))
    reference = aggregate_periodic_cic_sparse(batch, shape)
    optimized = aggregate_periodic_cic_sparse_optimized(batch, shape)
    np.testing.assert_array_equal(optimized.flat_indices, reference.flat_indices)
    np.testing.assert_allclose(
        optimized.node_masses, reference.node_masses, rtol=2.0e-15, atol=2.0e-16
    )
    assert optimized.deposited_measure == pytest.approx(batch.total_measure, abs=5e-13)


@pytest.mark.parametrize(
    ("shape", "cell", "positions", "sigma"),
    [
        (
            (16, 15, 14),
            np.diag([8.0, 7.5, 7.0]),
            np.array([[0.999, 0.3, 0.4], [0.001, 0.3, 0.4], [0.42, 0.53, 0.64]]),
            0.42,
        ),
        (
            (17, 16, 15),
            lta_cell(2.4),
            np.array([[0.999, 0.999, 0.999], [0.001, 0.001, 0.001], [0.3, 0.4, 0.5]]),
            0.38,
        ),
        (
            (13, 12, 11),
            lta_cell(2.0),
            np.array([[0.17, 0.29, 0.43], [0.71, 0.62, 0.54]]),
            0.0,
        ),
    ],
)
def test_optimized_field_matches_ld1_a_reference(
    shape: tuple[int, int, int],
    cell: np.ndarray,
    positions: np.ndarray,
    sigma: float,
) -> None:
    reference, optimized = reference_and_optimized(
        sample_batch(positions), shape=shape, cell=cell, sigma=sigma
    )
    np.testing.assert_array_equal(
        optimized.active_flat_indices, reference.active_flat_indices
    )
    denominator = max(1.0e-300, float(np.sum(np.abs(reference.active_values))))
    l1 = float(np.sum(np.abs(optimized.active_values - reference.active_values))) / denominator
    linf = float(np.max(np.abs(optimized.active_values - reference.active_values))) / max(
        1.0e-300, float(np.max(np.abs(reference.active_values)))
    )
    assert l1 <= 2.0e-12
    assert linf <= 5.0e-12
    assert abs(optimized.integral - reference.integral) <= 5.0e-13
    for fraction in (0.5, 0.8, 0.95):
        left = reference.hdr_details(fraction)
        right = optimized.hdr_details(fraction)
        assert abs(left.threshold - right.threshold) <= 5.0e-12 * max(
            1.0, float(np.max(reference.active_values))
        )
        assert abs(left.achieved_mass_fraction - right.achieved_mass_fraction) <= 5.0e-13


def test_optimized_output_is_deterministic_across_chunk_sizes() -> None:
    rng = np.random.default_rng(98)
    batch = sample_batch(rng.random((120, 3)), rng.random(120))
    kwargs = dict(
        grid_shape=(22, 21, 20),
        display_cell=lta_cell(3.1),
        gaussian_bandwidth=0.44,
        field_key="density",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        cache_stencil_supports=False,
    )
    first = prepare_sparse_canonical_density_optimized(
        batch, pair_chunk_size=197, **kwargs
    )
    second = prepare_sparse_canonical_density_optimized(
        batch, pair_chunk_size=4096, **kwargs
    )
    np.testing.assert_array_equal(first.active_flat_indices, second.active_flat_indices)
    np.testing.assert_array_equal(first.active_values, second.active_values)


def test_stencil_cache_hit_clear_and_json_info() -> None:
    clear_density_optimization_caches()
    kwargs = dict(
        grid_shape=(32, 31, 30),
        display_cell=lta_cell(4.0),
        gaussian_bandwidth=0.37,
        kernel_tail_tolerance=1.0e-8,
    )
    first, first_hit = get_periodic_gaussian_stencil_support(**kwargs)
    second, second_hit = get_periodic_gaussian_stencil_support(**kwargs)
    assert not first_hit
    assert second_hit
    assert first is second
    info = density_optimization_cache_info()
    assert info.hits == 1
    assert info.misses == 1
    assert info.insertions == 1
    assert info.current_entries == 1
    assert info.retained_array_bytes > 0
    assert info.to_json_dict()["current_entries"] == 1
    clear_density_optimization_caches()
    cleared = density_optimization_cache_info()
    assert cleared.current_entries == 0
    assert cleared.hits == 0
    assert cleared.misses == 0


def test_cached_support_revalidates_stricter_limits() -> None:
    clear_density_optimization_caches()
    kwargs = dict(
        grid_shape=(40, 40, 40),
        display_cell=np.eye(3) * 10.0,
        gaussian_bandwidth=0.45,
        kernel_tail_tolerance=1.0e-8,
    )
    support, _ = get_periodic_gaussian_stencil_support(**kwargs)
    candidate_count = int(support.metadata["candidate_contribution_count"])
    with pytest.raises(GraphComplexityError, match="candidate image contributions"):
        get_periodic_gaussian_stencil_support(
            **kwargs, max_candidate_contributions=candidate_count - 1
        )


def test_cache_disabled_does_not_retain_support() -> None:
    clear_density_optimization_caches()
    _, hit = get_periodic_gaussian_stencil_support(
        (24, 24, 24),
        np.eye(3) * 6.0,
        0.35,
        use_cache=False,
    )
    assert not hit
    info = density_optimization_cache_info()
    assert info.current_entries == 0
    assert info.hits == 0
    assert info.misses == 0


def test_cache_eviction_is_bounded_and_deterministic() -> None:
    clear_density_optimization_caches()
    for index in range(18):
        get_periodic_gaussian_stencil_support(
            (12 + index, 13, 14),
            np.eye(3) * (5.0 + 0.01 * index),
            0.25,
        )
    info = density_optimization_cache_info()
    assert info.current_entries == info.max_entries
    assert info.evictions == 18 - info.max_entries
    assert info.retained_array_bytes <= info.max_array_bytes


def test_planning_style_warmup_is_reused_by_realization() -> None:
    clear_density_optimization_caches()
    shape = (30, 29, 28)
    cell = lta_cell(3.8)
    sigma = 0.36
    get_periodic_gaussian_stencil_support(shape, cell, sigma)
    batch = sample_batch(np.array([[0.21, 0.32, 0.43], [0.61, 0.72, 0.83]]))
    field = prepare_sparse_canonical_density_optimized(
        batch,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="density",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
    )
    assert field.metadata["stencil_cache_hit_for_realization"] is True
    assert density_optimization_cache_info().hits >= 1



def test_optimized_target_planning_matches_reference() -> None:
    rng = np.random.default_rng(441)
    batch = sample_batch(rng.random((96, 3)), rng.random(96))
    shape = (28, 27, 26)
    cic = aggregate_periodic_cic_sparse_optimized(batch, shape)
    support, _ = get_periodic_gaussian_stencil_support(
        shape, lta_cell(3.6), 0.38, use_cache=False
    )
    reference = plan_sparse_target_nodes(
        cic, support, max_kernel_pairs=50_000_000, max_planning_bytes=1_000_000_000
    )
    optimized = plan_sparse_target_nodes_optimized(
        cic,
        support,
        pair_chunk_size=131,
        max_kernel_pairs=50_000_000,
        max_planning_bytes=1_000_000_000,
    )
    np.testing.assert_array_equal(optimized, reference)

def test_optimization_options_round_trip() -> None:
    options = DensityOptimizationOptions(
        sparse_evaluation_mode="reference",
        cache_stencil_supports=False,
        sparse_pair_chunk_size=12345,
        sparse_group_batch_size=7,
        metadata={"purpose": "test"},
    )
    restored = DensityOptimizationOptions.from_json_dict(options.to_json_dict())
    assert restored == options

def test_ld4_auto_selection_is_identical_in_reference_and_optimized_modes() -> None:
    rng = np.random.default_rng(712)
    batch = sample_batch(rng.random((48, 3)), rng.random(48))
    common = dict(
        grid_shape=(36, 35, 34),
        gaussian_bandwidth=0.34,
        adaptive_smearing=False,
        kernel_options=DensityKernelOptions(
            smoothing_operator=DISCRETE_PERIODIZED_OPERATOR
        ),
        storage_options=DensityStorageOptions(
            grid_backend="auto",
            local_block_shape=(8, 8, 8),
            sparse_activation_fraction=0.20,
        ),
    )
    reference_options = AtomicDensityOptions(
        optimization_options=DensityOptimizationOptions(
            sparse_evaluation_mode="reference",
            cache_stencil_supports=False,
        ),
        **common,
    )
    optimized_options = AtomicDensityOptions(
        optimization_options=DensityOptimizationOptions(
            sparse_evaluation_mode="optimized",
            cache_stencil_supports=False,
            sparse_pair_chunk_size=113,
        ),
        **common,
    )
    kwargs = dict(
        samples=batch,
        field_key="atomic:test",
        grid_shape=(36, 35, 34),
        display_cell=lta_cell(4.2),
        gaussian_bandwidth=0.34,
        max_total_voxels=2_000_000,
        max_nonzero_nodes=2_000_000,
        max_stored_block_values=2_000_000,
        max_blocks=100_000,
        max_kernel_pairs=100_000_000,
        max_planning_bytes=1_000_000_000,
        max_workspace_bytes=2_000_000_000,
        max_cic_contributions=10_000_000,
    )
    reference = _select_atomic_auto_backend(
        options=reference_options, **kwargs
    )
    optimized = _select_atomic_auto_backend(
        options=optimized_options, **kwargs
    )
    assert optimized.selected_backend == reference.selected_backend
    assert optimized.reason == reference.reason
    assert optimized.dense == reference.dense
    assert optimized.local_sparse.logical_node_count == reference.local_sparse.logical_node_count
    assert optimized.local_sparse.active_node_count == reference.local_sparse.active_node_count
    assert optimized.local_sparse.stored_value_count == reference.local_sparse.stored_value_count
    assert optimized.local_sparse.stored_block_count == reference.local_sparse.stored_block_count
    assert optimized.local_sparse.kernel_pair_count == reference.local_sparse.kernel_pair_count
    assert optimized.local_sparse.estimated_peak_bytes < reference.local_sparse.estimated_peak_bytes


def test_streaming_scatter_workspace_scales_with_chunk_not_all_pairs() -> None:
    rng = np.random.default_rng(883)
    batch = sample_batch(rng.random((420, 3)), rng.random(420))
    kwargs = dict(
        grid_shape=(42, 41, 40),
        display_cell=lta_cell(5.0),
        gaussian_bandwidth=0.46,
        field_key="density",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        pair_chunk_size=4096,
        block_shape=(8, 8, 8),
        cache_stencil_supports=False,
        max_workspace_bytes=64 * 1024 * 1024,
    )
    field = prepare_sparse_canonical_density_optimized(batch, **kwargs)
    metadata = field.metadata
    assert metadata["scatter_implementation"] == "two_pass_block_lookup_streaming_v1"
    assert metadata["peak_chunk_pair_count"] <= 4096
    assert metadata["kernel_pair_count"] > metadata["peak_chunk_pair_count"]
    assert metadata["scatter_workspace_upper_bound_bytes"] <= 64 * 1024 * 1024



def test_group_batched_sparse_field_matches_monolithic_field() -> None:
    rng = np.random.default_rng(7701)
    n_groups = 12
    frames = 35
    centers = rng.random((n_groups, 3))
    positions = np.mod(
        centers[None, :, :] + rng.normal(scale=0.008, size=(frames, n_groups, 3)),
        1.0,
    ).reshape((-1, 3))
    groups = np.tile(np.arange(n_groups, dtype=np.int64), frames)
    weights = np.full(positions.shape[0], 1.0 / frames)
    batch = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        sample_group_ids=groups,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=tuple(range(n_groups))
        ),
        total_measure=float(n_groups),
        measure_kind="occupancy",
        measure_units="count",
    )
    kwargs = dict(
        grid_shape=(58, 57, 56),
        display_cell=lta_cell(6.5),
        gaussian_bandwidth=0.22,
        field_key="density",
        label="density",
        physical_units="angstrom^-3",
        broadening_metric="gaussian_sigma_v1",
        pair_chunk_size=8192,
        block_shape=(8, 8, 8),
        cache_stencil_supports=False,
        max_workspace_bytes=256 * 1024 * 1024,
    )
    monolithic = prepare_sparse_canonical_density_optimized(
        batch, group_batch_size=64, **kwargs
    )
    batched = prepare_sparse_canonical_density_optimized(
        batch, group_batch_size=4, **kwargs
    )
    np.testing.assert_array_equal(
        batched.active_flat_indices, monolithic.active_flat_indices
    )
    np.testing.assert_allclose(
        batched.active_values, monolithic.active_values, rtol=3.0e-15, atol=3.0e-16
    )
    assert batched.integral == pytest.approx(monolithic.integral, abs=5.0e-13)
    assert batched.metadata["group_batch_count"] == 3
    assert batched.metadata["source_group_count"] == 12
    assert batched.metadata["scatter_implementation"] == (
        "group_batched_two_pass_block_lookup_v1"
    )


def test_group_batched_target_plan_matches_monolithic_union() -> None:
    rng = np.random.default_rng(8221)
    n_groups = 10
    frames = 18
    positions = rng.random((frames, n_groups, 3)).reshape((-1, 3))
    groups = np.tile(np.arange(n_groups, dtype=np.int64), frames)
    weights = np.full(positions.shape[0], 1.0 / frames)
    samples = PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        sample_group_ids=groups,
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=tuple(range(n_groups))
        ),
        total_measure=float(n_groups),
        measure_kind="occupancy",
        measure_units="count",
    )
    shape = (34, 33, 32)
    cell = lta_cell(4.8)
    cic = aggregate_periodic_cic_sparse_optimized(
        samples, shape, max_workspace_bytes=256 * 1024 * 1024
    )
    support, _ = get_periodic_gaussian_stencil_support(
        shape, cell, 0.31, use_cache=False
    )
    monolithic = plan_sparse_target_nodes_optimized(
        cic,
        support,
        pair_chunk_size=4096,
        block_shape=(8, 8, 8),
        max_kernel_pairs=100_000_000,
        max_planning_bytes=256 * 1024 * 1024,
    )
    batched, pair_count, metadata = plan_group_batched_sparse_targets_optimized(
        samples,
        cic,
        support,
        pair_chunk_size=4096,
        block_shape=(8, 8, 8),
        group_batch_size=3,
        max_kernel_pairs=100_000_000,
        max_planning_bytes=256 * 1024 * 1024,
    )
    np.testing.assert_array_equal(batched, monolithic)
    assert pair_count >= cic.occupied_node_count * support.stencil_offset_count
    assert metadata["group_batch_count"] == 4
    assert metadata["peak_batch_kernel_pair_count"] < pair_count
    assert metadata["planning_mode"] == "group_batched_streaming_union_v1"



def test_total_mass_correction_preserves_tiny_first_node() -> None:
    """A negative roundoff residual must not be applied to a tiny first node."""

    masses = np.array([1.0e-20, 0.5, 0.5], dtype=np.float64)
    target = float(np.nextafter(1.0, 0.0))
    correction_index = _apply_total_mass_correction(
        masses, total_measure=target
    )
    assert correction_index == 1
    assert masses[0] == 1.0e-20
    assert np.all(masses > 0.0)
    assert float(np.sum(masses, dtype=np.float64)) == target
