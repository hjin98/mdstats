from __future__ import annotations

import numpy as np

from mdstats.plotting.density_contracts import (
    DensitySourceProvenance,
    is_periodic_node_field_access,
    is_scalar_field3d,
)
from mdstats.plotting.density_packed_field import (
    PeriodicPackedBlockScalarField3D,
    pack_sparse_reference_field,
)
from mdstats.plotting.density_sparse_reference import SparseCanonicalDensityReference3D


def _reference() -> SparseCanonicalDensityReference3D:
    shape = (7, 8, 9)
    coordinates = np.asarray(
        [(0, 0, 0), (6, 7, 8), (3, 4, 5), (1, 1, 1), (1, 1, 2)],
        dtype=np.int64,
    )
    flat = np.ravel_multi_index(
        (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]), shape, order="C"
    )
    order = np.argsort(flat)
    values = np.asarray([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)[order]
    flat = flat[order]
    # Cell volume equals logical-node count, so voxel_volume == 1.
    cell = np.diag(np.asarray(shape, dtype=np.float64))
    return SparseCanonicalDensityReference3D(
        field_key="fixture",
        label="Fixture density",
        physical_units="count / angstrom^3",
        logical_grid_shape=shape,
        active_flat_indices=flat,
        active_values=values,
        display_cell=cell,
        total_measure=float(np.sum(values)),
        gaussian_bandwidth=0.2,
        broadening_metric="effective_cic_stencil_rms_v1",
        source_provenance=DensitySourceProvenance(source_kind="test"),
        metadata={"fixture": True},
    )


def test_packed_field_preserves_protocol_values_and_integral() -> None:
    reference = _reference()
    packed = pack_sparse_reference_field(reference, storage_block_shape=(4, 4, 4))
    assert is_scalar_field3d(packed)
    assert is_periodic_node_field_access(packed)
    assert packed.integral == reference.integral
    assert packed.nonzero_node_count == reference.active_flat_indices.size
    coordinates = np.asarray(
        [(0, 0, 0), (6, 7, 8), (2, 2, 2), (1, 1, 2), (7, 8, 9), (-1, -1, -1)],
        dtype=np.int64,
    )
    assert np.array_equal(
        packed.gather_node_values(coordinates),
        reference.gather_node_values(coordinates),
    )
    packed_nodes = list(packed.iter_stored_nodes())
    packed_coordinates = np.concatenate([item[0] for item in packed_nodes])
    packed_values = np.concatenate([item[1] for item in packed_nodes])
    assert np.array_equal(
        packed_values,
        reference.gather_node_values(packed_coordinates),
    )
    assert packed.storage_summary().stored_value_count == reference.active_flat_indices.size
    assert packed.metadata["fixed_block_value_bytes"] > packed.retained_array_bytes


def test_packed_field_json_round_trip_and_hdr() -> None:
    packed = pack_sparse_reference_field(_reference(), storage_block_shape=(4, 4, 4))
    restored = PeriodicPackedBlockScalarField3D.from_json_dict(packed.to_json_dict())
    assert restored.content_identity == packed.content_identity
    assert restored.integral == packed.integral
    assert np.array_equal(restored.packed_values, packed.packed_values)
    assert restored.hdr_details(0.8).threshold == packed.hdr_details(0.8).threshold


def test_packed_gather_decodes_each_touched_block_once(monkeypatch) -> None:
    import mdstats.plotting.density_packed_field as packed_module

    reference = _reference()
    packed = pack_sparse_reference_field(reference, storage_block_shape=(4, 4, 4))
    grid = np.indices(reference.logical_grid_shape, dtype=np.int64).reshape(3, -1).T
    # Include wrapped duplicates to exercise periodic canonicalization without
    # changing the number of touched active storage blocks.
    query = np.concatenate(
        (
            grid,
            grid[:32] + np.asarray(reference.logical_grid_shape, dtype=np.int64),
            grid[-32:] - np.asarray(reference.logical_grid_shape, dtype=np.int64),
        ),
        axis=0,
    )
    calls: list[tuple[int, ...]] = []
    original = packed_module.unpack_local_bitset

    def counted(words, storage_block_shape):
        calls.append(tuple(int(value) for value in np.asarray(words, dtype=np.uint64)))
        return original(words, storage_block_shape)

    monkeypatch.setattr(packed_module, "unpack_local_bitset", counted)
    actual = packed.gather_node_values(query)
    expected = reference.gather_node_values(query)
    assert np.array_equal(actual, expected)

    active_flat = np.ravel_multi_index(
        (
            packed.active_block_indices[:, 0],
            packed.active_block_indices[:, 1],
            packed.active_block_indices[:, 2],
        ),
        packed.block_grid_shape,
        order="C",
    )
    block_shape = np.asarray(packed.storage_block_shape, dtype=np.int64)
    canonical = np.mod(
        query, np.asarray(packed.logical_grid_shape, dtype=np.int64)[None, :]
    )
    queried_blocks = canonical // block_shape[None, :]
    queried_flat = np.ravel_multi_index(
        (queried_blocks[:, 0], queried_blocks[:, 1], queried_blocks[:, 2]),
        packed.block_grid_shape,
        order="C",
    )
    expected_decodes = np.intersect1d(np.unique(queried_flat), active_flat).size
    assert len(calls) == int(expected_decodes)
