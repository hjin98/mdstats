from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting.density_block_direct import (
    DensityDirectRealizationLimits,
    DensityDirectRealizationPlan,
    plan_target_owned_direct_realization,
    realize_density_target_owned_direct,
)
from mdstats.plotting.density_block_routing import build_periodic_kernel_block_routing
from mdstats.plotting.density_contracts import DensitySourceProvenance
from mdstats.plotting.density_kernel import PeriodicGaussianStencilSupport
from mdstats.plotting.density_sparse_reference import (
    SparseCICNodeMasses3D,
    scatter_periodic_stencil_sparse,
)
from mdstats.plotting.density_support_atlas import (
    build_density_support_atlas,
    pack_periodic_cic_source,
)
from mdstats.plotting.graph_errors import GraphAdapterError, GraphComplexityError


def _stencil(
    shape: tuple[int, int, int],
    offsets: list[tuple[int, int, int]],
    weights: list[float] | None = None,
) -> PeriodicGaussianStencilSupport:
    canonical = np.asarray(offsets, dtype=np.int64) % np.asarray(shape, dtype=np.int64)
    flat_raw = np.ravel_multi_index(
        (canonical[:, 0], canonical[:, 1], canonical[:, 2]), shape, order="C"
    )
    raw_weights = (
        np.arange(1, len(offsets) + 1, dtype=np.float64)
        if weights is None
        else np.asarray(weights, dtype=np.float64)
    )
    unique = np.unique(flat_raw).astype(np.int64)
    inverse = np.searchsorted(unique, flat_raw)
    reduced = np.zeros(unique.size, dtype=np.float64)
    np.add.at(reduced, inverse, raw_weights)
    reduced /= np.sum(reduced)
    return PeriodicGaussianStencilSupport(
        grid_shape=shape,
        display_cell=np.diag(np.asarray(shape, dtype=np.float64)),
        gaussian_bandwidth=1.0,
        kernel_tail_tolerance=1.0e-8,
        cutoff_radius=4.0,
        active_flat_indices=unique,
        active_weights=reduced,
        pre_normalization_sum=1.0,
        normalization_factor=1.0,
        periodic_image_contribution_count=int(len(offsets)),
        covariance=np.eye(3, dtype=np.float64),
        metadata={"fixture": True},
    )


def _cic(
    shape: tuple[int, int, int],
    coordinates: list[tuple[int, int, int]],
) -> SparseCICNodeMasses3D:
    unique = np.unique(np.asarray(coordinates, dtype=np.int64), axis=0)
    flat = np.ravel_multi_index(
        (unique[:, 0], unique[:, 1], unique[:, 2]), shape, order="C"
    )
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


def _case(
    shape: tuple[int, int, int],
    block: tuple[int, int, int],
    coordinates: list[tuple[int, int, int]],
    offsets: list[tuple[int, int, int]],
):
    cic = _cic(shape, coordinates)
    stencil = _stencil(shape, offsets)
    source = pack_periodic_cic_source(cic, storage_block_shape=block)
    routing = build_periodic_kernel_block_routing(
        stencil, storage_block_shape=block
    )
    atlas = build_density_support_atlas(source, routing)
    return cic, stencil, source, routing, atlas


def _realize(case):
    cic, stencil, source, routing, atlas = case
    plan = plan_target_owned_direct_realization(source, stencil, routing, atlas)
    field = realize_density_target_owned_direct(
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
    return cic, stencil, source, routing, atlas, plan, field


def _field_flat_values(field) -> tuple[np.ndarray, np.ndarray]:
    parts = list(field.iter_stored_nodes())
    coordinates = np.concatenate([part[0] for part in parts])
    values = np.concatenate([part[1] for part in parts])
    flat = np.ravel_multi_index(
        (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]),
        field.logical_grid_shape,
        order="C",
    )
    order = np.argsort(flat)
    return flat[order], values[order]


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
            [
                (x, y, z)
                for x in (-1, 0, 1)
                for y in (-1, 0, 1)
                for z in (-1, 0, 1)
            ],
        ),
    ],
)
def test_target_owned_direct_matches_ld1a_on_periodic_terminal_cases(
    shape, block, coordinates, offsets
) -> None:
    cic, stencil, source, routing, atlas, plan, field = _realize(
        _case(shape, block, coordinates, offsets)
    )
    reference = scatter_periodic_stencil_sparse(
        cic,
        stencil,
        field_key="fixture",
        label="Fixture",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        max_kernel_pairs=10_000_000,
        max_workspace_bytes=1_000_000_000,
    )
    flat, values = _field_flat_values(field)
    assert np.array_equal(flat, reference.active_flat_indices)
    relative_l1 = float(
        np.sum(np.abs(values - reference.active_values), dtype=np.float64)
        / np.sum(np.abs(reference.active_values), dtype=np.float64)
    )
    assert relative_l1 < 5.0e-12
    assert field.integral == pytest.approx(1.0, rel=0.0, abs=5.0e-13)
    assert plan.exact_contribution_count == (
        source.occupied_node_count * stencil.stencil_offset_count
    )
    assert field.metadata["accepted_contribution_count"] == plan.exact_contribution_count
    assert field.metadata["complete_fine_pair_array_allocated"] is False
    assert field.metadata["global_target_coordinate_array_allocated"] is False
    assert field.metadata["completed_dense_target_blocks_retained"] is False
    assert field.nonzero_node_count == atlas.target_support_node_count


def test_direct_output_is_byte_deterministic_and_plan_round_trips() -> None:
    case = _case(
        (11, 12, 13),
        (4, 4, 4),
        [(0, 0, 0), (10, 11, 12), (5, 6, 7), (2, 9, 1)],
        [(0, 0, 0), (1, 2, 3), (-3, 1, 0), (4, -2, 2), (-1, -1, -1)],
    )
    first = _realize(case)
    second = _realize(case)
    plan = first[-2]
    restored = DensityDirectRealizationPlan.from_json_dict(plan.to_json_dict())
    assert restored.content_identity == plan.content_identity
    assert first[-1].content_identity == second[-1].content_identity
    assert np.array_equal(first[-1].packed_values, second[-1].packed_values)
    assert np.array_equal(first[-1].occupancy_bitsets, second[-1].occupancy_bitsets)


def test_periodic_integer_translation_covariance() -> None:
    shape = (9, 10, 11)
    block = (4, 4, 4)
    coordinates = [(8, 9, 10)]
    offsets = [(0, 0, 0), (1, 2, 0), (-2, 1, -1), (3, -3, 2)]
    shift = np.asarray((2, 3, 4), dtype=np.int64)
    base = _realize(_case(shape, block, coordinates, offsets))[-1]
    shifted_coordinates = [
        tuple(((np.asarray(item) + shift) % np.asarray(shape)).tolist())
        for item in coordinates
    ]
    shifted = _realize(_case(shape, block, shifted_coordinates, offsets))[-1]
    base_dense = np.zeros(shape, dtype=np.float64)
    shifted_dense = np.zeros(shape, dtype=np.float64)
    for coords, values in base.iter_stored_nodes():
        base_dense[coords[:, 0], coords[:, 1], coords[:, 2]] = values
    for coords, values in shifted.iter_stored_nodes():
        shifted_dense[coords[:, 0], coords[:, 1], coords[:, 2]] = values
    expected = np.roll(base_dense, tuple(int(v) for v in shift), axis=(0, 1, 2))
    assert np.allclose(shifted_dense, expected, rtol=0.0, atol=2.0e-15)


def test_planning_limits_fail_before_realization() -> None:
    _, stencil, source, routing, atlas = _case(
        (12, 12, 12),
        (4, 4, 4),
        [(0, 0, 0), (6, 6, 6), (11, 11, 11)],
        [
            (x, y, z)
            for x in (-2, -1, 0, 1, 2)
            for y in (-2, -1, 0, 1, 2)
            for z in (-2, -1, 0, 1, 2)
        ],
    )
    with pytest.raises(GraphComplexityError, match="max_exact_contributions"):
        plan_target_owned_direct_realization(
            source,
            stencil,
            routing,
            atlas,
            limits=DensityDirectRealizationLimits(max_exact_contributions=10),
        )
    with pytest.raises(GraphComplexityError, match="max_target_blocks"):
        plan_target_owned_direct_realization(
            source,
            stencil,
            routing,
            atlas,
            limits=DensityDirectRealizationLimits(max_target_blocks=1),
        )


def test_identity_mismatch_is_rejected_before_allocation() -> None:
    shape = (9, 9, 9)
    block = (4, 4, 4)
    stencil = _stencil(shape, [(0, 0, 0), (1, 0, 0), (-1, 0, 0)])
    routing = build_periodic_kernel_block_routing(stencil, storage_block_shape=block)
    source_a = pack_periodic_cic_source(
        _cic(shape, [(0, 0, 0)]), storage_block_shape=block
    )
    source_b = pack_periodic_cic_source(
        _cic(shape, [(1, 0, 0)]), storage_block_shape=block
    )
    atlas_a = build_density_support_atlas(source_a, routing)
    with pytest.raises(GraphAdapterError, match="source identity"):
        plan_target_owned_direct_realization(source_b, stencil, routing, atlas_a)


def test_localized_packed_output_is_smaller_than_fixed_active_blocks() -> None:
    field = _realize(
        _case(
            (32, 32, 32),
            (8, 8, 8),
            [(1, 1, 1), (17, 17, 17)],
            [(0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, 0, 1)],
        )
    )[-1]
    fixed_value_bytes = field.active_block_count * int(np.prod(field.storage_block_shape)) * 8
    assert field.retained_array_bytes < fixed_value_bytes


def test_randomized_direct_equivalence_across_partial_terminal_grids() -> None:
    rng = np.random.default_rng(20260721)
    for case_index in range(16):
        shape = tuple(int(v) for v in rng.integers(5, 13, size=3))
        block = tuple(int(v) for v in rng.integers(2, 6, size=3))
        source_coordinates = sorted(
            {
                tuple(int(v) for v in rng.integers(0, shape, size=3))
                for _ in range(int(rng.integers(1, 8)))
            }
        )
        stencil_offsets = [(0, 0, 0)] + [
            tuple(int(v) for v in rng.integers(-5, 6, size=3))
            for _ in range(int(rng.integers(3, 18)))
        ]
        cic, stencil, _, _, _, _, field = _realize(
            _case(shape, block, source_coordinates, stencil_offsets)
        )
        reference = scatter_periodic_stencil_sparse(
            cic,
            stencil,
            field_key="fixture",
            label="Fixture",
            physical_units="count / angstrom^3",
            broadening_metric="effective_cic_stencil_rms_v1",
            max_kernel_pairs=5_000_000,
            max_workspace_bytes=500_000_000,
        )
        flat, values = _field_flat_values(field)
        assert np.array_equal(flat, reference.active_flat_indices), case_index
        assert np.allclose(
            values,
            reference.active_values,
            rtol=5.0e-12,
            atol=2.0e-15,
        ), case_index


def test_pair_chunk_limit_smaller_than_source_block_is_honored() -> None:
    shape = (12, 12, 12)
    block = (6, 6, 6)
    coordinates = [
        (x, y, z)
        for x in range(4)
        for y in range(3)
        for z in range(2)
    ]
    offsets = [(0, 0, 0), (1, 0, 0), (-1, 0, 0), (0, 1, 0)]
    cic, stencil, source, routing, atlas = _case(
        shape, block, coordinates, offsets
    )
    limits = DensityDirectRealizationLimits(max_pair_chunk_size=5)
    plan = plan_target_owned_direct_realization(
        source, stencil, routing, atlas, limits=limits
    )
    field = realize_density_target_owned_direct(
        source,
        stencil,
        routing,
        atlas,
        field_key="chunked",
        label="Chunked",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        approved_plan=plan,
    )
    reference = scatter_periodic_stencil_sparse(
        cic,
        stencil,
        field_key="chunked",
        label="Chunked",
        physical_units="count / angstrom^3",
        broadening_metric="effective_cic_stencil_rms_v1",
        max_kernel_pairs=1_000_000,
        max_workspace_bytes=100_000_000,
    )
    flat, values = _field_flat_values(field)
    assert np.array_equal(flat, reference.active_flat_indices)
    assert np.allclose(values, reference.active_values, rtol=5.0e-12, atol=2.0e-15)
    assert field.metadata["peak_chunk_pair_count"] <= 5
