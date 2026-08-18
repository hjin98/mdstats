"""LD2-A backend-neutral HDR and logical-node cloud tests."""

from __future__ import annotations

import json

import numpy as np
import pytest

from mdstats import (
    DensityNodeCloud3D,
    DensitySourceProvenance,
    GAUSSIAN_SIGMA_BROADENING,
    PeriodicScalarField3D,
    PeriodicWeightedSamples3D,
    pack_sparse_reference_blocks,
    prepare_density_node_cloud,
    prepare_sparse_canonical_density_reference,
)
from mdstats.plotting.graph_errors import GraphComplexityError


def _reference(*, shape=(13, 11, 9), sigma=0.31):
    cell = np.asarray(
        [[5.2, 0.0, 0.0], [1.3, 4.6, 0.0], [0.8, 0.5, 3.9]],
        dtype=np.float64,
    )
    samples = PeriodicWeightedSamples3D(
        fractional_positions=np.asarray(
            [
                [0.013, 0.987, 0.501],
                [0.913, 0.087, 0.019],
                [0.443, 0.517, 0.731],
            ],
            dtype=np.float64,
        ),
        weights=np.asarray([0.25, 0.35, 0.40], dtype=np.float64),
        source_provenance=DensitySourceProvenance(
            source_kind="atomic_occupancy", atom_indices=(2,)
        ),
        total_measure=1.0,
        measure_kind="occupancy",
        measure_units="count",
    )
    return prepare_sparse_canonical_density_reference(
        samples,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="atomic-density-0",
        label="Na density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )


def _dense_from_reference(reference):
    return PeriodicScalarField3D(
        field_key=reference.field_key,
        label=reference.label,
        values=reference.to_dense_values(max_nodes=10_000_000),
        display_cell=reference.display_cell,
        total_measure=reference.total_measure,
        selected_atom_indices=(2,),
        gaussian_bandwidth=reference.gaussian_bandwidth,
        metadata={
            "physical_units": reference.physical_units,
            "smoothing_operator": reference.smoothing_operator,
            "broadening_metric": reference.broadening_metric,
        },
        source_provenance=reference.source_provenance,
    )


@pytest.mark.parametrize("fraction", [0.50, 0.80, 0.95])
def test_dense_and_block_sparse_clouds_are_byte_identical(fraction: float) -> None:
    reference = _reference()
    dense = _dense_from_reference(reference)
    sparse = pack_sparse_reference_blocks(reference, block_shape=(4, 5, 3))
    dense_cloud = prepare_density_node_cloud(dense, fraction, max_points=10_000)
    sparse_cloud = prepare_density_node_cloud(sparse, fraction, max_points=10_000)
    assert dense_cloud.logical_indices.tobytes() == sparse_cloud.logical_indices.tobytes()
    assert (
        dense_cloud.relative_intensities.tobytes()
        == sparse_cloud.relative_intensities.tobytes()
    )
    np.testing.assert_array_equal(
        dense_cloud.cartesian_positions, sparse_cloud.cartesian_positions
    )
    assert dense_cloud.hdr_details.to_json_dict() == sparse_cloud.hdr_details.to_json_dict()


def test_cloud_coordinates_and_bounds_follow_exact_logical_nodes() -> None:
    reference = _reference(shape=(17, 13, 11))
    field = pack_sparse_reference_blocks(reference, block_shape=(5, 4, 3))
    cloud = prepare_density_node_cloud(field, 0.95, max_points=10_000)
    expected = (
        cloud.logical_indices.astype(np.float64)
        / np.asarray(field.grid_shape, dtype=np.float64)[None, :]
    ) @ field.display_cell
    scale = max(1.0, float(np.max(np.linalg.norm(field.display_cell, axis=1))))
    np.testing.assert_allclose(
        cloud.cartesian_positions,
        expected,
        rtol=0.0,
        atol=1.0e-12 * scale,
    )
    np.testing.assert_array_equal(
        cloud.bounds.minimum, np.min(cloud.cartesian_positions, axis=0)
    )
    np.testing.assert_array_equal(
        cloud.bounds.maximum, np.max(cloud.cartesian_positions, axis=0)
    )


def test_truncated_selection_is_deterministic_and_block_shape_independent() -> None:
    reference = _reference(shape=(19, 17, 15), sigma=0.45)
    first = prepare_density_node_cloud(
        pack_sparse_reference_blocks(reference, block_shape=(4, 4, 4)),
        0.95,
        max_points=37,
    )
    second = prepare_density_node_cloud(
        pack_sparse_reference_blocks(reference, block_shape=(7, 5, 3)),
        0.95,
        max_points=37,
    )
    assert first.resources.truncated is True
    assert first.resources.selected_point_count == 37
    assert first.logical_indices.tobytes() == second.logical_indices.tobytes()
    assert first.cartesian_positions.tobytes() == second.cartesian_positions.tobytes()
    assert first.relative_intensities.tobytes() == second.relative_intensities.tobytes()


def test_sparse_cloud_does_not_use_dense_conversion(monkeypatch) -> None:
    reference = _reference()
    field = pack_sparse_reference_blocks(reference, block_shape=(4, 4, 4))

    def forbidden(*args, **kwargs):
        raise AssertionError("dense conversion was called")

    monkeypatch.setattr(type(field), "to_dense_values", forbidden)
    cloud = prepare_density_node_cloud(field, 0.95, max_points=1000)
    assert cloud.resources.selected_point_count > 0
    assert cloud.metadata["dense_materialization_used"] is False


def test_cloud_json_round_trip_is_exact() -> None:
    reference = _reference()
    cloud = prepare_density_node_cloud(
        pack_sparse_reference_blocks(reference, block_shape=(4, 4, 4)),
        0.80,
        max_points=29,
        display_replication="match_graph",
    )
    encoded = json.dumps(cloud.to_json_dict(), sort_keys=True, separators=(",", ":"))
    restored = DensityNodeCloud3D.from_json_dict(json.loads(encoded))
    assert restored.to_json_dict() == cloud.to_json_dict()
    np.testing.assert_array_equal(restored.logical_indices, cloud.logical_indices)
    np.testing.assert_array_equal(
        restored.cartesian_positions, cloud.cartesian_positions
    )


def test_cloud_workspace_limit_fails_before_output_allocation() -> None:
    reference = _reference(shape=(31, 29, 23), sigma=0.55)
    field = pack_sparse_reference_blocks(reference, block_shape=(8, 8, 8))
    with pytest.raises(GraphComplexityError, match="max_workspace_bytes"):
        prepare_density_node_cloud(
            field,
            0.95,
            max_points=10_000,
            max_workspace_bytes=1,
        )


def test_resource_bytes_equal_realized_arrays() -> None:
    cloud = prepare_density_node_cloud(
        pack_sparse_reference_blocks(_reference(), block_shape=(4, 4, 4)),
        0.95,
        max_points=41,
    )
    resources = cloud.resources
    assert resources.index_bytes == cloud.logical_indices.nbytes
    assert resources.cartesian_bytes == cloud.cartesian_positions.nbytes
    assert resources.intensity_bytes == cloud.relative_intensities.nbytes
    assert resources.value_bytes == resources.selected_point_count * 8
    assert resources.estimated_peak_bytes >= (
        resources.index_bytes
        + resources.value_bytes
        + resources.cartesian_bytes
        + resources.intensity_bytes
    )


def test_dense_cloud_preserves_historical_selection_and_intensity_policy() -> None:
    reference = _reference(shape=(17, 15, 13), sigma=0.42)
    dense = _dense_from_reference(reference)
    fraction = 0.95
    max_points = 43
    cloud = prepare_density_node_cloud(dense, fraction, max_points=max_points)
    threshold = dense.threshold_for_mass_fraction(fraction)
    eligible = np.flatnonzero(dense.values.ravel() >= threshold)
    positions = np.linspace(0, eligible.size - 1, max_points, dtype=np.int64)
    selected = eligible[positions]
    expected_indices = np.column_stack(
        np.unravel_index(selected, dense.grid_shape)
    ).astype(np.int64)
    expected_values = dense.values.ravel()[selected]
    expected_intensities = expected_values / np.max(expected_values)
    expected_cartesian = (
        expected_indices.astype(np.float64)
        / np.asarray(dense.grid_shape, dtype=np.float64)[None, :]
    ) @ dense.display_cell
    assert cloud.logical_indices.tobytes() == expected_indices.tobytes()
    assert cloud.relative_intensities.tobytes() == expected_intensities.tobytes()
    assert cloud.cartesian_positions.tobytes() == expected_cartesian.tobytes()
