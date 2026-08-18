"""LD1-A deterministic sparse CIC and canonical-convolution reference tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats.plotting import (
    GAUSSIAN_SIGMA_BROADENING,
    DensitySourceProvenance,
    PeriodicWeightedSamples3D,
    aggregate_periodic_cic_sparse,
    build_periodic_gaussian_stencil,
    build_periodic_gaussian_stencil_support,
    convolve_periodic_stencil_direct,
    prepare_sparse_canonical_density_reference,
    scatter_periodic_stencil_sparse,
)
from mdstats.plotting.atomic_density import _deposit_cic
from mdstats.plotting.graph_errors import GraphComplexityError


def lta_cell(scale: float = 1.0) -> np.ndarray:
    return scale * np.asarray(
        [
            [3.0, 0.0, 0.0],
            [1.5, 2.598076211353316, 0.0],
            [1.5, 0.8660254037844386, 2.449489742783178],
        ],
        dtype=np.float64,
    )


def samples(
    positions: np.ndarray,
    weights: np.ndarray | None = None,
    *,
    source_kind: str = "atomic_occupancy",
) -> PeriodicWeightedSamples3D:
    positions = np.asarray(positions, dtype=np.float64)
    if weights is None:
        weights = np.ones(positions.shape[0], dtype=np.float64)
    weights = np.asarray(weights, dtype=np.float64)
    return PeriodicWeightedSamples3D(
        fractional_positions=positions,
        weights=weights,
        source_provenance=DensitySourceProvenance(source_kind=source_kind),
        total_measure=float(np.sum(weights, dtype=np.float64)),
        measure_kind="occupancy",
        measure_units="count",
        metadata={"test_fixture": source_kind},
    )


def dense_direct_reference(
    sample_batch: PeriodicWeightedSamples3D,
    shape: tuple[int, int, int],
    cell: np.ndarray,
    sigma: float,
) -> np.ndarray:
    cic = aggregate_periodic_cic_sparse(sample_batch, shape)
    dense_mass = cic.to_dense_mass_grid(max_nodes=10_000_000)
    stencil = build_periodic_gaussian_stencil(shape, cell, sigma)
    smoothed = convolve_periodic_stencil_direct(dense_mass, stencil)
    voxel_volume = abs(float(np.linalg.det(cell))) / float(np.prod(shape))
    density = smoothed / voxel_volume
    density *= sample_batch.total_measure / (
        float(np.sum(density, dtype=np.float64)) * voxel_volume
    )
    return density


def relative_errors(reference: np.ndarray, candidate: np.ndarray) -> tuple[float, float]:
    delta = np.abs(candidate - reference)
    l1 = float(np.sum(delta, dtype=np.float64)) / max(
        1.0e-300, float(np.sum(np.abs(reference), dtype=np.float64))
    )
    linf = float(np.max(delta)) / max(1.0e-300, float(np.max(np.abs(reference))))
    return l1, linf


def assert_sparse_matches_dense(
    sample_batch: PeriodicWeightedSamples3D,
    shape: tuple[int, int, int],
    cell: np.ndarray,
    sigma: float,
) -> None:
    field = prepare_sparse_canonical_density_reference(
        sample_batch,
        grid_shape=shape,
        display_cell=cell,
        gaussian_bandwidth=sigma,
        field_key="reference",
        label="reference density",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
        max_workspace_bytes=500_000_000,
    )
    sparse_dense = field.to_dense_values(max_nodes=10_000_000)
    reference = dense_direct_reference(sample_batch, shape, cell, sigma)
    l1, linf = relative_errors(reference, sparse_dense)
    assert l1 <= 2.0e-11
    assert linf <= 5.0e-11
    tolerance = 5.0e-13 * max(1.0, sample_batch.total_measure)
    assert abs(field.integral - sample_batch.total_measure) <= tolerance

    maximum = float(np.max(reference))
    voxel_volume = field.voxel_volume
    for fraction in (0.5, 0.8, 0.95):
        details = field.hdr_details(fraction)
        flat = np.sort(reference.ravel())[::-1]
        cumulative = np.cumsum(flat, dtype=np.float64) * voxel_volume
        index = min(
            int(
                np.searchsorted(
                    cumulative,
                    fraction * sample_batch.total_measure,
                    side="left",
                )
            ),
            flat.size - 1,
        )
        reference_threshold = float(flat[index])
        selected = reference >= reference_threshold
        reference_achieved = (
            float(np.sum(reference[selected], dtype=np.float64))
            * voxel_volume
            / sample_batch.total_measure
        )
        assert abs(details.threshold - reference_threshold) <= 5.0e-12 * max(
            1.0, maximum
        )
        assert abs(details.achieved_mass_fraction - reference_achieved) <= 5.0e-13


@pytest.mark.parametrize(
    ("shape", "cell", "positions", "weights", "sigma"),
    [
        (
            (9, 8, 7),
            np.diag([4.5, 4.0, 3.5]),
            np.array([[0.137, 0.283, 0.619], [0.713, 0.431, 0.207]]),
            np.array([0.4, 0.6]),
            0.42,
        ),
        (
            (9, 9, 9),
            lta_cell(1.5),
            np.array([[0.173, 0.327, 0.541], [0.827, 0.673, 0.459]]),
            np.array([0.25, 0.75]),
            0.46,
        ),
        # Face crossing.
        (
            (8, 8, 8),
            np.eye(3) * 4.0,
            np.array([[0.999, 0.36, 0.42], [0.001, 0.36, 0.42]]),
            np.array([0.5, 0.5]),
            0.5,
        ),
        # Edge crossing.
        (
            (8, 8, 8),
            np.eye(3) * 4.0,
            np.array([[0.999, 0.999, 0.42], [0.001, 0.001, 0.42]]),
            np.array([0.5, 0.5]),
            0.5,
        ),
        # Corner crossing.
        (
            (8, 8, 8),
            lta_cell(1.3),
            np.array([[0.999, 0.999, 0.999], [0.001, 0.001, 0.001]]),
            np.array([0.5, 0.5]),
            0.45,
        ),
        # Overlapping sources.
        (
            (8, 9, 10),
            np.diag([4.0, 4.5, 5.0]),
            np.array([[0.31, 0.47, 0.53], [0.31, 0.47, 0.53]]),
            np.array([0.2, 0.8]),
            0.5,
        ),
        # Bimodal hopping trajectory.
        (
            (10, 9, 8),
            lta_cell(1.7),
            np.array(
                [
                    [0.18, 0.22, 0.27],
                    [0.19, 0.21, 0.28],
                    [0.71, 0.76, 0.68],
                    [0.72, 0.75, 0.69],
                ]
            ),
            np.array([0.15, 0.35, 0.2, 0.3]),
            0.48,
        ),
        # Independent ensemble weights.
        (
            (9, 8, 8),
            np.diag([4.5, 4.0, 4.0]),
            np.array(
                [
                    [0.11, 0.24, 0.37],
                    [0.42, 0.55, 0.68],
                    [0.79, 0.16, 0.83],
                ]
            ),
            np.array([0.2, 0.5, 0.3]),
            0.44,
        ),
        # Exact identity path.
        (
            (8, 7, 9),
            lta_cell(1.4),
            np.array([[0.123, 0.456, 0.789], [0.987, 0.654, 0.321]]),
            np.array([0.45, 0.55]),
            0.0,
        ),
    ],
)
def test_sparse_reference_matches_dense_direct_required_cases(
    shape: tuple[int, int, int],
    cell: np.ndarray,
    positions: np.ndarray,
    weights: np.ndarray,
    sigma: float,
) -> None:
    assert_sparse_matches_dense(samples(positions, weights), shape, cell, sigma)


def test_multiple_periodic_images_are_aggregated_without_dense_stencil() -> None:
    shape = (8, 8, 8)
    cell = np.eye(3) * 3.0
    support = build_periodic_gaussian_stencil_support(shape, cell, 1.0)
    dense = build_periodic_gaussian_stencil(shape, cell, 1.0)
    assert support.periodic_image_contribution_count > support.stencil_offset_count
    np.testing.assert_array_equal(
        support.active_flat_indices, dense.active_flat_indices
    )
    np.testing.assert_allclose(
        support.active_weights,
        dense.active_weights,
        rtol=0.0,
        atol=5.0e-18,
    )
    np.testing.assert_allclose(support.covariance, dense.covariance, atol=0.0)
    np.testing.assert_allclose(
        support.to_dense_values(max_nodes=1000), dense.values, rtol=0.0, atol=5.0e-18
    )
    assert support.metadata_dict()["dense_stencil_allocated"] is False


def test_sparse_cic_matches_dense_deposition_and_planning_identity() -> None:
    shape = (11, 10, 9)
    batch = samples(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [0.999, 0.001, 0.5],
                [0.137, 0.283, 0.619],
                [0.137, 0.283, 0.619],
            ]
        ),
        np.array([0.1, 0.2, 0.3, 0.4]),
    )
    sparse = aggregate_periodic_cic_sparse(batch, shape)
    dense = _deposit_cic(batch.fractional_positions, batch.weights, shape)
    np.testing.assert_allclose(
        sparse.to_dense_mass_grid(max_nodes=2000), dense, rtol=0.0, atol=2.0e-16
    )
    np.testing.assert_array_equal(sparse.flat_indices, np.flatnonzero(dense > 0.0))
    assert sparse.deposited_measure == pytest.approx(batch.total_measure, abs=5.0e-13)


def test_repeated_preparation_is_byte_deterministic() -> None:
    batch = samples(
        np.array(
            [
                [0.123, 0.234, 0.345],
                [0.456, 0.567, 0.678],
                [0.789, 0.891, 0.912],
            ]
        ),
        np.array([0.2, 0.3, 0.5]),
    )
    kwargs = dict(
        grid_shape=(9, 9, 9),
        display_cell=lta_cell(1.5),
        gaussian_bandwidth=0.45,
        field_key="deterministic",
        label="deterministic",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
    )
    first = prepare_sparse_canonical_density_reference(batch, **kwargs)
    second = prepare_sparse_canonical_density_reference(batch, **kwargs)
    np.testing.assert_array_equal(first.active_flat_indices, second.active_flat_indices)
    np.testing.assert_array_equal(first.active_values, second.active_values)
    assert first.metadata.canonical_json() == second.metadata.canonical_json()
    assert first.hdr_details(0.8).to_json_dict() == second.hdr_details(0.8).to_json_dict()


def test_periodic_translation_invariance() -> None:
    positions = np.array([[0.137, 0.283, 0.619], [0.713, 0.431, 0.207]])
    shifted = positions + np.array([2.0, -3.0, 4.0])
    original = samples(positions, np.array([0.4, 0.6]))
    translated = samples(shifted - np.floor(shifted), np.array([0.4, 0.6]))
    kwargs = dict(
        grid_shape=(9, 8, 7),
        display_cell=lta_cell(1.5),
        gaussian_bandwidth=0.44,
        field_key="translation",
        label="translation",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
    )
    first = prepare_sparse_canonical_density_reference(original, **kwargs)
    second = prepare_sparse_canonical_density_reference(translated, **kwargs)
    np.testing.assert_array_equal(first.active_flat_indices, second.active_flat_indices)
    np.testing.assert_allclose(first.active_values, second.active_values, rtol=2.0e-12, atol=2.0e-15)


def test_public_node_access_absent_nodes_and_read_only_arrays() -> None:
    field = prepare_sparse_canonical_density_reference(
        samples(np.array([[0.25, 0.25, 0.25]])),
        grid_shape=(8, 8, 8),
        display_cell=np.eye(3) * 4.0,
        gaussian_bandwidth=0.0,
        field_key="access",
        label="access",
        physical_units="angstrom^-3",
        broadening_metric=GAUSSIAN_SIGMA_BROADENING,
    )
    assert not field.active_flat_indices.flags.writeable
    assert not field.active_values.flags.writeable
    gathered = field.gather_node_values(
        np.array([[2, 2, 2], [1, 1, 1], [10, -6, 2]], dtype=np.int64)
    )
    assert gathered[0] > 0.0
    assert gathered[1] == 0.0
    assert gathered[2] == gathered[0]
    assert not gathered.flags.writeable
    batches = list(field.iter_stored_nodes(batch_size=3))
    assert all(not indices.flags.writeable and not values.flags.writeable for indices, values in batches)


def test_resource_limits_fail_before_large_reference_allocations() -> None:
    batch = samples(np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]))
    with pytest.raises(GraphComplexityError, match="max_cic_contributions"):
        aggregate_periodic_cic_sparse(batch, (8, 8, 8), max_cic_contributions=15)
    with pytest.raises(GraphComplexityError, match="max_workspace_bytes"):
        aggregate_periodic_cic_sparse(batch, (8, 8, 8), max_workspace_bytes=100)

    cic = aggregate_periodic_cic_sparse(batch, (8, 8, 8))
    support = build_periodic_gaussian_stencil_support(
        (8, 8, 8), np.eye(3) * 4.0, 0.5
    )
    with pytest.raises(GraphComplexityError, match="max_kernel_pairs"):
        scatter_periodic_stencil_sparse(
            cic,
            support,
            field_key="limit",
            label="limit",
            physical_units="angstrom^-3",
            broadening_metric=GAUSSIAN_SIGMA_BROADENING,
            max_kernel_pairs=1,
        )
    with pytest.raises(GraphComplexityError, match="max_workspace_bytes"):
        scatter_periodic_stencil_sparse(
            cic,
            support,
            field_key="limit",
            label="limit",
            physical_units="angstrom^-3",
            broadening_metric=GAUSSIAN_SIGMA_BROADENING,
            max_workspace_bytes=100,
        )
    with pytest.raises(GraphComplexityError, match="max_nodes"):
        support.to_dense_values(max_nodes=10)
