from __future__ import annotations

import numpy as np
import pytest
from ase.data import atomic_masses

import mdstats


def _collection(
    positions: np.ndarray,
    *,
    numbers: tuple[int, ...],
    cell: np.ndarray | None = None,
    pbc: tuple[bool, bool, bool] = (False, False, False),
    origins: np.ndarray | None = None,
) -> mdstats.AtomisticFrameCollection:
    cell_array = np.asarray(np.eye(3) * 12.0 if cell is None else cell, dtype=float)
    cart = np.asarray(positions, dtype=float)
    frac = cart @ np.linalg.inv(cell_array)
    return mdstats.AtomisticFrameCollection(
        frame_semantics="ensemble",
        frame_ids=np.asarray([0], dtype=np.int64),
        atomic_numbers=np.asarray(numbers, dtype=np.int32),
        masses=np.asarray(atomic_masses[np.asarray(numbers, dtype=int)], dtype=float),
        pbc=np.asarray(pbc, dtype=bool),
        steps=None,
        times=None,
        cells=cell_array[None, :, :],
        origins=np.zeros((1, 3), dtype=float) if origins is None else np.asarray(origins, dtype=float)[None, :],
        fractional_positions=frac[None, :, :],
        provenance=mdstats.FrameCollectionProvenance(
            source_format="synthetic-test",
            source_files=("memory://local-structure",),
            coordinate_normalization="none",
            velocity_source="unavailable",
            stress_source=None,
            units_source="test",
        ),
    )


def test_local_structure_is_rigid_motion_and_permutation_invariant() -> None:
    positions = np.asarray(
        [[1.0, 1.0, 1.0], [2.7, 1.2, 1.1], [1.3, 2.5, 1.4], [1.2, 1.4, 2.8]],
        dtype=float,
    )
    numbers = (14, 8, 8, 14)
    base = mdstats.compute_local_structure_features(
        _collection(positions, numbers=numbers), frame_index=0
    )

    theta = np.deg2rad(37.0)
    rotation = np.asarray(
        [[np.cos(theta), -np.sin(theta), 0.0], [np.sin(theta), np.cos(theta), 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )
    transformed = positions @ rotation.T + np.asarray([2.1, -1.4, 0.8])
    permutation = np.asarray([2, 0, 3, 1], dtype=int)
    moved = mdstats.compute_local_structure_features(
        _collection(transformed[permutation], numbers=tuple(np.asarray(numbers)[permutation])),
        frame_index=0,
    )
    inverse = np.argsort(permutation)
    assert moved.feature_names == base.feature_names
    assert np.allclose(moved.values[inverse], base.values, atol=2.0e-12, rtol=2.0e-12)
    assert np.array_equal(moved.missing_mask[inverse], base.missing_mask)


def test_local_structure_uses_periodic_minimum_image() -> None:
    collection = _collection(
        np.asarray([[0.2, 5.0, 5.0], [9.8, 5.0, 5.0]]),
        numbers=(14, 14),
        cell=np.eye(3) * 10.0,
        pbc=(True, True, True),
    )
    result = mdstats.compute_local_structure_features(collection, frame_index=0)
    assert result.feature("nearest_neighbor_distance_angstrom") == pytest.approx([0.4, 0.4])


def test_smooth_coordination_decreases_continuously_with_distance() -> None:
    near = mdstats.compute_local_structure_features(
        _collection(np.asarray([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]]), numbers=(14, 14)),
        frame_index=0,
    )
    far = mdstats.compute_local_structure_features(
        _collection(np.asarray([[0.0, 0.0, 0.0], [3.5, 0.0, 0.0]]), numbers=(14, 14)),
        frame_index=0,
    )
    assert near.feature("smooth_coordination")[0] == pytest.approx(1.0)
    assert 0.0 < far.feature("smooth_coordination")[0] < 1.0
    assert far.feature("smooth_coordination")[0] < near.feature("smooth_coordination")[0]


def test_missing_angular_features_are_explicitly_masked() -> None:
    result = mdstats.compute_local_structure_features(
        _collection(np.asarray([[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]]), numbers=(14, 14)),
        frame_index=0,
    )
    for name in ("angular_legendre_l1", "angular_legendre_l2", "angular_legendre_l3", "angular_legendre_l4"):
        index = result.feature_index(name)
        assert np.all(result.values[:, index] == 0.0)
        assert np.all(result.missing_mask[:, index])
    assert np.all(np.isfinite(result.feature("bond_orientational_q6")))


def test_dense_pair_budget_fails_closed() -> None:
    collection = _collection(
        np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        numbers=(14, 14, 14, 14),
    )
    with pytest.raises(mdstats.LocalStructureComplexityError, match="pair work"):
        mdstats.compute_local_structure_features(
            collection,
            frame_index=0,
            policy=mdstats.LocalStructureFeaturePolicy(maximum_dense_pair_work=15),
        )


def test_triclinic_minimum_image_and_selected_centers() -> None:
    cell = np.asarray([[10.0, 0.0, 0.0], [2.0, 9.0, 0.0], [1.0, 1.5, 8.0]])
    fractional = np.asarray([[0.02, 0.25, 0.4], [0.98, 0.25, 0.4], [0.5, 0.5, 0.5]])
    collection = _collection(
        fractional @ cell,
        numbers=(14, 14, 8),
        cell=cell,
        pbc=(True, True, True),
    )
    result = mdstats.compute_local_structure_features(
        collection,
        frame_index=0,
        atom_indices=(0,),
    )
    assert result.atom_indices.tolist() == [0]
    assert result.feature("nearest_neighbor_distance_angstrom")[0] == pytest.approx(0.4)


def test_policy_round_trip_feature_order_and_warning_evidence() -> None:
    policy = mdstats.LocalStructureFeaturePolicy(
        radial_centers_angstrom=(1.0, 2.0, 3.0),
        angular_legendre_orders=(2, 4),
        orientational_orders=(4,),
    )
    assert mdstats.LocalStructureFeaturePolicy.from_dict(policy.to_dict()) == policy
    result = mdstats.compute_local_structure_features(
        _collection(np.asarray([[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]), numbers=(14, 14)),
        frame_index=0,
        policy=policy,
    )
    assert result.feature_names == policy.feature_names
    assert "near_coincident_distinct_atoms" in result.warning_codes
    assert np.all(np.isfinite(result.values))


def test_batched_angular_invariants_match_scalar_reference() -> None:
    from mdstats.analysis.local_structure import (
        _angular_and_orientational_moments,
        _batched_angular_and_orientational_moments,
    )

    rng = np.random.default_rng(20260805)
    vectors = rng.normal(size=(12, 17, 3))
    weights = rng.random((12, 17))
    valid = rng.random((12, 17)) > 0.45
    valid[0] = False
    valid[1, 0] = True
    angular_orders = (1, 2, 3, 4)
    orientational_orders = (4, 6)
    angular, angular_missing, orientational, orientational_missing = (
        _batched_angular_and_orientational_moments(
            vectors,
            weights,
            valid,
            angular_orders,
            orientational_orders,
        )
    )
    for row in range(vectors.shape[0]):
        scalar_angular, scalar_orientational = (
            _angular_and_orientational_moments(
                vectors[row, valid[row]],
                weights[row, valid[row]],
                angular_orders,
                orientational_orders,
            )
        )
        for column, expected in enumerate(scalar_angular):
            assert bool(angular_missing[row, column]) == (expected is None)
            if expected is not None:
                assert angular[row, column] == pytest.approx(expected, abs=2e-14)
        for column, expected in enumerate(scalar_orientational):
            assert bool(orientational_missing[row, column]) == (expected is None)
            if expected is not None:
                assert orientational[row, column] == pytest.approx(expected, abs=2e-14)


def test_all_atom_upper_triangle_path_matches_selected_center_path() -> None:
    rng = np.random.default_rng(20260805)
    cell = np.asarray(
        [[10.0, 0.0, 0.0], [3.2, 9.0, 0.0], [1.7, 2.1, 8.0]],
        dtype=float,
    )
    fractional = rng.random((18, 3))
    numbers = tuple(np.resize(np.asarray([8, 13, 14], dtype=int), 18))
    collection = _collection(
        fractional @ cell,
        numbers=numbers,
        cell=cell,
        pbc=(True, True, True),
    )
    full = mdstats.compute_local_structure_features(collection, frame_index=0)
    for atom_index in range(collection.n_atoms):
        selected = mdstats.compute_local_structure_features(
            collection, frame_index=0, atom_indices=(atom_index,)
        )
        np.testing.assert_allclose(
            full.values[atom_index],
            selected.values[0],
            rtol=2.0e-13,
            atol=2.0e-13,
        )
        assert np.array_equal(
            full.missing_mask[atom_index], selected.missing_mask[0]
        )


def test_data6_local_structure_accepts_lta_pair_on_reduced_lattice_plane() -> None:
    """Regression for DATA6 finalize MIC bookkeeping failure."""

    cell = np.asarray(
        [
            [17.3630, 0.0, 0.0],
            [8.6815, 15.0368, 0.0],
            [8.6815, 5.0123, 14.1768],
        ],
        dtype=np.float64,
    )
    displacement = np.asarray(
        [29.171533411850227, 12.525124164525154, 11.211695531556682],
        dtype=np.float64,
    )
    collection = _collection(
        np.asarray([[0.0, 0.0, 0.0], displacement], dtype=np.float64),
        numbers=(14, 14),
        cell=cell,
        pbc=(True, True, True),
    )

    result = mdstats.compute_local_structure_features(collection, frame_index=0)
    from ase.geometry import find_mic

    _vector, expected_distance = find_mic(
        displacement, cell, pbc=np.ones(3, dtype=bool)
    )
    np.testing.assert_allclose(
        result.feature("nearest_neighbor_distance_angstrom"),
        [float(expected_distance), float(expected_distance)],
        rtol=1.0e-12,
        atol=1.0e-12,
    )
