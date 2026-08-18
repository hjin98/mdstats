"""Analytical tests for bond-angle distributions and coordination filters."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import (
    AtomisticFrameCollection,
    CoordinationCondition,
    FrameCollectionProvenance,
    FrameSemantics,
    PairCutoffRegistry,
    compute_bond_angle_distribution,
)
from mdstats.analysis import NoBondAnglesError


def make_collection(
    positions: np.ndarray,
    atomic_numbers: np.ndarray,
    *,
    cell: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    positions = np.asarray(positions, dtype=float)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames = positions.shape[0]
    cell = np.eye(3) * 30.0 if cell is None else np.asarray(cell, dtype=float)
    cells = np.repeat(cell[None, ...], n_frames, axis=0)
    scaled = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells))
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.arange(n_frames),
        atomic_numbers=np.asarray(atomic_numbers, dtype=np.int32),
        masses=np.ones(len(atomic_numbers)),
        pbc=np.ones(3, dtype=bool),
        steps=None,
        times=None,
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=scaled,
        velocities=None,
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="unavailable",
            coordinate_normalization="independent_frame_wrapping",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def test_right_angle_and_raw_angle_output() -> None:
    collection = make_collection(
        np.array([[5, 5, 5], [6, 5, 5], [5, 6, 5]], dtype=float),
        np.array([14, 8, 8]),
    )
    result = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs={("Si", "O"): 1.5},
        bins=np.array([0.0, 89.0, 91.0, 180.0]),
        return_angles=True,
        per_frame=True,
    )
    assert result.n_angles == 1
    np.testing.assert_allclose(result.raw_angles, [90.0])
    np.testing.assert_array_equal(result.counts, [0, 1, 0])
    assert result.per_frame_valid.tolist() == [True]
    assert np.sum(result.distribution * np.diff(result.bin_edges)) == pytest.approx(1.0)


def test_ideal_tetrahedron_has_six_equal_angles() -> None:
    vectors = np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float)
    positions = np.vstack([np.zeros(3), vectors]) + np.array([10.0, 10.0, 10.0])
    collection = make_collection(positions, np.array([14, 8, 8, 8, 8]))
    result = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs={("Si", "O"): 2.0},
        coordination_filters=[CoordinationCondition.exact("O", 4)],
        bins=1800,
        return_angles=True,
    )
    assert result.n_angles == 6
    np.testing.assert_allclose(
        result.raw_angles,
        np.full(6, np.degrees(np.arccos(-1.0 / 3.0))),
        atol=1e-12,
    )


def test_periodic_boundary_vectors_preserve_angle() -> None:
    positions = np.array(
        [[0.2, 0.2, 0.2], [9.2, 0.2, 0.2], [0.2, 1.2, 0.2]], dtype=float
    )
    collection = make_collection(
        positions,
        np.array([14, 8, 8]),
        cell=np.eye(3) * 10.0,
    )
    result = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs={("Si", "O"): 1.5},
        return_angles=True,
    )
    np.testing.assert_allclose(result.raw_angles, [90.0], atol=1e-12)


def test_asymmetric_triplet_and_combined_species_filter() -> None:
    positions = np.array(
        [
            [5, 5, 5],
            [15, 5, 5],
            [6, 5, 5],
            [16, 5, 5],
            [15, 6, 5],
            [5, 6, 5],
            [15, 5, 6],
        ],
        dtype=float,
    )
    # O centers 0,1; Si 2,3,4; Al 5,6.
    collection = make_collection(positions, np.array([8, 8, 14, 14, 14, 13, 13]))
    result = compute_bond_angle_distribution(
        collection,
        triplet=("Si", "O", "Al"),
        cutoffs={("O", "Si"): 1.5, ("O", "Al"): 1.5},
        coordination_filters=[CoordinationCondition.exact(("Si", "Al"), 2)],
        return_angles=True,
    )
    # Center 0 has one Si and one Al; center 1 has three total and is rejected.
    assert result.n_accepted_centers == 1
    assert result.n_angles == 1
    np.testing.assert_allclose(result.raw_angles, [90.0])


def test_center_weighting_differs_from_angle_weighting() -> None:
    positions = np.array(
        [
            [5, 5, 5],
            [15, 5, 5],
            [6, 5, 5],
            [5, 6, 5],
            [16, 5, 5],
            [15, 6, 5],
            [14, 5, 5],
        ],
        dtype=float,
    )
    collection = make_collection(positions, np.array([14, 14, 8, 8, 8, 8, 8]))
    result = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs={("Si", "O"): 1.5},
        bins=np.array([0.0, 120.0, 180.0]),
    )
    # First center contributes one 90-degree angle. Second contributes two 90
    # and one 180-degree angle. Angle and center weighting must differ.
    assert result.n_angles == 4
    assert not np.allclose(
        result.angle_weighted_density, result.center_weighted_density
    )
    widths = np.diff(result.bin_edges)
    assert np.sum(result.center_weighted_density * widths) == pytest.approx(1.0)


def test_no_angles_raises() -> None:
    collection = make_collection(
        np.array([[5, 5, 5], [6, 5, 5]], dtype=float), np.array([14, 8])
    )
    with pytest.raises(NoBondAnglesError):
        compute_bond_angle_distribution(
            collection,
            triplet=("O", "Si", "O"),
            cutoffs=PairCutoffRegistry.from_mapping({("Si", "O"): 1.5}),
        )


def test_asymmetric_endpoint_count_is_cartesian_product() -> None:
    positions = np.array(
        [
            [10, 10, 10],  # central O
            [11, 10, 10],
            [10, 11, 10],  # two Si
            [9, 10, 10],
            [10, 9, 10],
            [10, 10, 11],  # three Al
        ],
        dtype=float,
    )
    collection = make_collection(positions, np.array([8, 14, 14, 13, 13, 13]))
    result = compute_bond_angle_distribution(
        collection,
        triplet=("Si", "O", "Al"),
        cutoffs={("O", "Si"): 1.5, ("O", "Al"): 1.5},
    )
    assert result.n_angles == 2 * 3


def test_triclinic_periodic_angle() -> None:
    cell = np.array([[6.0, 0.0, 0.0], [1.0, 6.0, 0.0], [0.5, 0.5, 6.0]])
    center_fractional = np.array([0.05, 0.05, 0.05])
    endpoint_a_fractional = np.array([0.95, 0.05, 0.05])
    endpoint_c_fractional = np.array([0.05, 0.15, 0.05])
    positions = (
        np.vstack([center_fractional, endpoint_a_fractional, endpoint_c_fractional])
        @ cell
    )
    collection = make_collection(positions, np.array([14, 8, 8]), cell=cell)
    result = compute_bond_angle_distribution(
        collection,
        triplet=("O", "Si", "O"),
        cutoffs={("Si", "O"): 1.0},
        return_angles=True,
    )
    vector_a = np.array([-0.1, 0.0, 0.0]) @ cell
    vector_c = np.array([0.0, 0.1, 0.0]) @ cell
    expected = np.degrees(
        np.arccos(
            np.dot(vector_a, vector_c)
            / (np.linalg.norm(vector_a) * np.linalg.norm(vector_c))
        )
    )
    np.testing.assert_allclose(result.raw_angles, [expected], atol=1e-12)
