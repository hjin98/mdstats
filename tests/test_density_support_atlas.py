from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting.density_block_routing import build_periodic_kernel_block_routing
from mdstats.plotting.density_contracts import DensitySourceProvenance
from mdstats.plotting.density_kernel import PeriodicGaussianStencilSupport
from mdstats.plotting.density_scene_planning import DensitySupportPlanningLimits
from mdstats.plotting.density_sparse_reference import SparseCICNodeMasses3D
from mdstats.plotting.density_support_atlas import (
    DensitySupportAtlas,
    PeriodicPackedCICSourceField3D,
    build_density_support_atlas,
    pack_periodic_cic_source,
    verify_density_support_atlas,
)
from mdstats.plotting.graph_errors import GraphComplexityError


def _stencil(shape: tuple[int, int, int], offsets: list[tuple[int, int, int]]) -> PeriodicGaussianStencilSupport:
    canonical = np.asarray(offsets, dtype=np.int64) % np.asarray(shape, dtype=np.int64)
    flat = np.ravel_multi_index(
        (canonical[:, 0], canonical[:, 1], canonical[:, 2]), shape, order="C"
    )
    flat = np.unique(flat).astype(np.int64)
    weights = np.full(flat.size, 1.0 / flat.size, dtype=np.float64)
    return PeriodicGaussianStencilSupport(
        grid_shape=shape,
        display_cell=np.diag(np.asarray(shape, dtype=np.float64)),
        gaussian_bandwidth=1.0,
        kernel_tail_tolerance=1.0e-8,
        cutoff_radius=3.0,
        active_flat_indices=flat,
        active_weights=weights,
        pre_normalization_sum=1.0,
        normalization_factor=1.0,
        periodic_image_contribution_count=int(flat.size),
        covariance=np.eye(3, dtype=np.float64),
        metadata={"fixture": True},
    )


def _cic(shape: tuple[int, int, int], coordinates: list[tuple[int, int, int]]) -> SparseCICNodeMasses3D:
    array = np.asarray(coordinates, dtype=np.int64)
    flat = np.ravel_multi_index((array[:, 0], array[:, 1], array[:, 2]), shape, order="C")
    order = np.argsort(flat)
    flat = flat[order]
    masses = np.arange(1, flat.size + 1, dtype=np.float64)
    masses /= np.sum(masses)
    return SparseCICNodeMasses3D(
        grid_shape=shape,
        flat_indices=flat,
        node_masses=masses,
        total_measure=1.0,
        source_provenance=DensitySourceProvenance(source_kind="test"),
        metadata={"fixture": True},
    )


@pytest.mark.parametrize(
    ("shape", "block", "coordinates", "offsets"),
    [
        (
            (9, 10, 11),
            (4, 4, 4),
            [(0, 0, 0), (8, 9, 10), (4, 5, 6)],
            [(0, 0, 0), (1, 0, 0), (-1, 0, 0), (2, -3, 1), (-4, 2, -2)],
        ),
        (
            (5, 6, 7),
            (4, 4, 4),
            [(4, 5, 6), (0, 5, 0), (3, 0, 6)],
            [(0, 0, 0), (2, 2, 2), (-2, -2, -2), (4, -3, 1)],
        ),
        (
            (8, 8, 8),
            (4, 4, 4),
            [(0, 0, 0), (7, 7, 7), (3, 4, 5)],
            [(x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1)],
        ),
    ],
)
def test_bitset_atlas_exactly_matches_modular_minkowski_sum(
    shape: tuple[int, int, int],
    block: tuple[int, int, int],
    coordinates: list[tuple[int, int, int]],
    offsets: list[tuple[int, int, int]],
) -> None:
    stencil = _stencil(shape, offsets)
    source = pack_periodic_cic_source(_cic(shape, coordinates), storage_block_shape=block)
    routing = build_periodic_kernel_block_routing(stencil, storage_block_shape=block)
    atlas = build_density_support_atlas(
        source, routing, compute_connected_components=True
    )
    report = verify_density_support_atlas(source, stencil, atlas)
    assert report.exact_match
    assert report.missing_node_count == 0
    assert report.extra_node_count == 0
    assert atlas.target_support_node_count == report.expected_support_node_count
    assert atlas.component_count is not None
    assert atlas.metadata["complete_fine_pair_array_allocated"] is False
    assert atlas.metadata["source_specific_global_cache_used"] is False
    assert atlas.retained_array_bytes <= atlas.planning.atlas_retained_bytes_upper


def test_support_atlas_reports_field_scoped_progress() -> None:
    shape = (9, 10, 11)
    stencil = _stencil(
        shape,
        [(0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)],
    )
    source = pack_periodic_cic_source(
        _cic(shape, [(0, 0, 0), (8, 9, 10), (4, 5, 6)]),
        storage_block_shape=(4, 4, 4),
    )
    routing = build_periodic_kernel_block_routing(
        stencil, storage_block_shape=(4, 4, 4)
    )
    events = []
    atlas = build_density_support_atlas(
        source,
        routing,
        progress=events.append,
        field_key="atomic-density-7",
    )
    assert atlas.target_support_node_count > 0
    atlas_events = [event for event in events if event.stage == "density_support_atlas"]
    assert atlas_events[0].status == "started"
    assert atlas_events[0].current == 0
    assert atlas_events[0].total == source.source_block_count
    assert atlas_events[-1].status == "completed"
    assert atlas_events[-1].current == atlas_events[-1].total == source.source_block_count
    assert "atomic-density-7" in atlas_events[-1].message
    assert any(event.stage == "density_support_atlas_finalize" for event in events)


def test_packed_cic_source_round_trip_and_identity_is_content_specific() -> None:
    shape = (7, 8, 9)
    first = pack_periodic_cic_source(
        _cic(shape, [(0, 0, 0), (6, 7, 8)]), storage_block_shape=(4, 4, 4)
    )
    restored = PeriodicPackedCICSourceField3D.from_json_dict(first.to_json_dict())
    assert restored.content_identity == first.content_identity
    assert np.array_equal(restored.source_block_indices, first.source_block_indices)
    sparse = restored.to_sparse_cic_node_masses()
    expected = first.to_sparse_cic_node_masses()
    assert np.array_equal(sparse.flat_indices, expected.flat_indices)
    assert np.array_equal(sparse.node_masses, expected.node_masses)

    second = pack_periodic_cic_source(
        _cic(shape, [(1, 0, 0), (6, 7, 8)]), storage_block_shape=(4, 4, 4)
    )
    assert second.content_identity != first.content_identity


def test_atlas_round_trip_and_source_specific_identity() -> None:
    shape = (9, 10, 11)
    stencil = _stencil(shape, [(0, 0, 0), (1, 2, 3), (-2, 0, 1)])
    routing = build_periodic_kernel_block_routing(stencil, storage_block_shape=(4, 4, 4))
    source = pack_periodic_cic_source(
        _cic(shape, [(0, 0, 0), (8, 9, 10)]), storage_block_shape=(4, 4, 4)
    )
    atlas = build_density_support_atlas(source, routing)
    restored = DensitySupportAtlas.from_json_dict(atlas.to_json_dict())
    assert restored.content_identity == atlas.content_identity
    assert np.array_equal(restored.support_flat_indices(), atlas.support_flat_indices())
    assert restored.source_field_identity == source.content_identity


def test_transactional_support_planning_rejects_before_target_allocation() -> None:
    shape = (12, 12, 12)
    stencil = _stencil(
        shape,
        [(x, y, z) for x in (-2, -1, 0, 1, 2) for y in (-2, -1, 0, 1, 2) for z in (-2, -1, 0, 1, 2)],
    )
    source = pack_periodic_cic_source(
        _cic(shape, [(0, 0, 0), (6, 6, 6), (11, 11, 11)]),
        storage_block_shape=(4, 4, 4),
    )
    routing = build_periodic_kernel_block_routing(stencil, storage_block_shape=(4, 4, 4))
    limits = DensitySupportPlanningLimits(max_target_blocks=1)
    with pytest.raises(GraphComplexityError, match="target_block_count_upper"):
        build_density_support_atlas(source, routing, planning_limits=limits)


def test_randomized_terminal_and_periodic_support_equivalence() -> None:
    rng = np.random.default_rng(20260721)
    for case in range(12):
        shape = tuple(int(value) for value in rng.integers(5, 12, size=3))
        block = tuple(int(value) for value in rng.integers(2, 5, size=3))
        source_count = int(rng.integers(1, 7))
        source_coordinates = [
            tuple(int(value) for value in rng.integers(0, shape, size=3))
            for _ in range(source_count)
        ]
        source_coordinates = sorted(set(source_coordinates))
        offsets = [(0, 0, 0)]
        for _ in range(int(rng.integers(3, 12))):
            offsets.append(tuple(int(value) for value in rng.integers(-4, 5, size=3)))
        stencil = _stencil(shape, offsets)
        source = pack_periodic_cic_source(
            _cic(shape, source_coordinates), storage_block_shape=block
        )
        routing = build_periodic_kernel_block_routing(
            stencil, storage_block_shape=block
        )
        atlas = build_density_support_atlas(source, routing)
        report = verify_density_support_atlas(source, stencil, atlas)
        assert report.exact_match, (case, shape, block, report.to_json_dict())


def test_fft_support_dilation_matches_bitset_oracle_on_terminal_periodic_grid() -> None:
    shape = (17, 18, 19)
    block = (8, 8, 8)
    coordinates = [(0, 0, 0), (16, 17, 18), (7, 8, 9), (12, 3, 15)]
    offsets = [
        (x, y, z)
        for x in range(-5, 6)
        for y in range(-4, 5)
        for z in range(-3, 4)
        if x * x + y * y + z * z <= 25
    ]
    stencil = _stencil(shape, offsets)
    source = pack_periodic_cic_source(
        _cic(shape, coordinates), storage_block_shape=block
    )
    routing = build_periodic_kernel_block_routing(
        stencil, storage_block_shape=block
    )
    bitset = build_density_support_atlas(
        source, routing, dilation_backend="bitset"
    )
    fft = build_density_support_atlas(
        source, routing, dilation_backend="fft", fft_workers=1
    )
    assert bitset.content_identity == fft.content_identity
    assert np.array_equal(
        bitset.support_flat_indices(), fft.support_flat_indices()
    )
    assert fft.metadata["dilation_backend"] == "fft"
    assert fft.metadata["fft_kernel_transform_count"] == source.source_block_count
    assert verify_density_support_atlas(source, stencil, fft).exact_match
