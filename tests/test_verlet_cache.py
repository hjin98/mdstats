"""Stage S2-S3 fixed- and variable-cell Verlet-cache correctness tests."""

from __future__ import annotations

import numpy as np
import pytest

from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis._neighbor_compare import assert_neighbor_results_equal
from mdstats.analysis._neighbors import (
    InvalidCellGeometryError,
    NeighborSearchBackend,
    PairCounting,
    UnsafeNeighborCutoffError,
    build_neighbor_list,
)
from mdstats.analysis._verlet_cache import (
    NeighborSearchSession,
    VerletCacheOptions,
)


def make_trajectory(
    positions: np.ndarray,
    *,
    cell: np.ndarray | None = None,
    cells: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    positions = np.asarray(positions, dtype=float)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames, n_atoms, _ = positions.shape
    if cells is None:
        matrix = np.eye(3) * 10.0 if cell is None else np.asarray(cell, dtype=float)
        cells = np.repeat(matrix[None, ...], n_frames, axis=0)
    else:
        cells = np.asarray(cells, dtype=float)
    fractional = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells))
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.TRAJECTORY,
        frame_ids=np.arange(n_frames, dtype=np.int64),
        atomic_numbers=(
            np.ones(n_atoms, dtype=np.int32)
            if atomic_numbers is None
            else np.asarray(atomic_numbers, dtype=np.int32)
        ),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool) if pbc is None else np.asarray(pbc, dtype=bool),
        steps=np.arange(n_frames, dtype=np.int64),
        times=np.arange(n_frames, dtype=float),
        cells=cells,
        origins=np.zeros((n_frames, 3)),
        fractional_positions=fractional,
        velocities=np.zeros((n_frames, n_atoms, 3)),
        provenance=FrameCollectionProvenance(
            source_format="synthetic",
            source_files=("synthetic",),
            velocity_source="native",
            coordinate_normalization="minimum_image_inferred",
            stress_source=None,
            units_source="synthetic",
        ),
    )


def assert_session_matches_fresh(
    session: NeighborSearchSession,
    collection: AtomisticFrameCollection,
    frame: int,
    *,
    centers: list[int] | np.ndarray,
    candidates: list[int] | np.ndarray,
    cutoff: float,
    pair_counting: PairCounting = PairCounting.DIRECTED,
) -> None:
    cached = session.build_neighbor_list(
        frame_index=frame,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=cutoff,
        pair_counting=pair_counting,
    )
    dense = build_neighbor_list(
        collection,
        frame_index=frame,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=cutoff,
        pair_counting=pair_counting,
        backend=NeighborSearchBackend.DENSE,
    )
    cell_list = build_neighbor_list(
        collection,
        frame_index=frame,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=cutoff,
        pair_counting=pair_counting,
        backend=NeighborSearchBackend.CELL_LIST,
    )
    assert cached.backend is NeighborSearchBackend.VERLET_CACHE
    assert_neighbor_results_equal(cached, dense)
    assert_neighbor_results_equal(cached, cell_list)


def positions_from_fractional(
    fractional: np.ndarray,
    cells: np.ndarray,
) -> np.ndarray:
    """Return Cartesian row-vector coordinates for a variable-cell path."""
    return np.einsum("tni,tij->tnj", fractional, cells)


def test_fixed_cell_reuse_matches_fresh_backends() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.2, 0.0, 0.0], [4.0, 0.0, 0.0]],
            [[0.05, 0.0, 0.0], [1.15, 0.0, 0.0], [4.02, 0.0, 0.0]],
            [[0.10, 0.0, 0.0], [1.10, 0.0, 0.0], [4.04, 0.0, 0.0]],
        ]
    )
    collection = make_trajectory(positions)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.6))
    for frame in range(collection.n_frames):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1, 2],
            candidates=[0, 1, 2],
            cutoff=1.3,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    stats = session.statistics()
    assert stats.evaluations == 3
    assert stats.rebuilds == 1
    assert stats.reuse_evaluations == 2
    assert dict(stats.rebuild_reasons) == {"initial_build": 1}


def test_pair_can_enter_physical_cutoff_before_rebuild() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.4, 0.0, 0.0]],
            [[0.21, 0.0, 0.0], [1.19, 0.0, 0.0]],
        ]
    )
    collection = make_trajectory(positions)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    first = session.build_neighbor_list(
        frame_index=0,
        center_indices=[0, 1],
        candidate_neighbor_indices=[0, 1],
        cutoff=1.0,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
    )
    assert first.n_pairs == 0
    second = session.build_neighbor_list(
        frame_index=1,
        center_indices=[0, 1],
        candidate_neighbor_indices=[0, 1],
        cutoff=1.0,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
    )
    assert second.n_pairs == 1
    assert second.distances[0] == pytest.approx(0.98)
    stats = session.statistics()
    assert stats.rebuilds == 1
    assert stats.reuse_evaluations == 1


def test_omitted_pair_cannot_enter_cutoff_inside_skin_bound() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.6, 0.0, 0.0]],
            [[0.2, 0.0, 0.0], [1.4, 0.0, 0.0]],
        ]
    )
    collection = make_trajectory(positions)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    for frame in (0, 1):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1],
            candidates=[0, 1],
            cutoff=1.0,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    assert session.statistics().rebuilds == 1


def test_exact_displacement_threshold_forces_rebuild() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
            [[0.2, 0.0, 0.0], [2.0, 0.0, 0.0]],
        ]
    )
    collection = make_trajectory(positions)
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.4, safety_tolerance=1.0e-14),
    )
    for frame in (0, 1):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0],
            candidates=[1],
            cutoff=1.5,
        )
    stats = session.statistics()
    assert stats.rebuilds == 2
    assert dict(stats.rebuild_reasons) == {
        "displacement_limit": 1,
        "initial_build": 1,
    }


def test_periodic_boundary_crossing_uses_reference_relative_mic() -> None:
    positions = np.array(
        [
            [[9.9, 0.0, 0.0], [0.8, 0.0, 0.0]],
            [[10.1, 0.0, 0.0], [0.8, 0.0, 0.0]],
            [[10.2, 0.0, 0.0], [0.8, 0.0, 0.0]],
        ]
    )
    collection = make_trajectory(positions)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.8))
    for frame in range(3):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0],
            candidates=[1],
            cutoff=1.2,
        )
    assert session.statistics().rebuilds == 1


def test_noncontiguous_frame_evaluation_uses_rebuild_reference() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.3, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.1, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.15, 0.0, 0.0], [1.0, 0.0, 0.0]],
        ]
    )
    collection = make_trajectory(positions)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    for frame in (0, 2, 3):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0],
            candidates=[1],
            cutoff=1.2,
        )
    assert session.statistics().rebuilds == 1


def test_cell_change_forces_conservative_s2_rebuild() -> None:
    positions = np.array(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        ]
    )
    cells = np.array([np.eye(3) * 10.0, np.diag([10.01, 10.0, 10.0])])
    collection = make_trajectory(positions, cells=cells)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    for frame in (0, 1):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0],
            candidates=[1],
            cutoff=1.5,
        )
    stats = session.statistics()
    assert stats.rebuilds == 2
    assert dict(stats.rebuild_reasons) == {"cell_changed": 1, "initial_build": 1}


def test_request_changes_create_independent_caches() -> None:
    collection = make_trajectory(
        np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]])
    )
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    session.build_neighbor_list(
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1, 2],
        cutoff=1.2,
    )
    session.build_neighbor_list(
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1, 2],
        cutoff=1.4,
    )
    session.build_neighbor_list(
        frame_index=0,
        center_indices=[1],
        candidate_neighbor_indices=[0, 2],
        cutoff=1.2,
    )
    assert session.n_caches == 3
    stats = session.statistics()
    assert stats.rebuilds == 3
    assert stats.evaluations == 3


def test_list_radius_must_satisfy_unique_image_limit() -> None:
    collection = make_trajectory(np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]]))
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    with pytest.raises(UnsafeNeighborCutoffError):
        session.build_neighbor_list(
            frame_index=0,
            center_indices=[0],
            candidate_neighbor_indices=[1],
            cutoff=4.8,
        )


def test_randomized_triclinic_trajectory_matches_fresh_searches() -> None:
    rng = np.random.default_rng(20260713)
    cell = np.array([[8.0, 0.0, 0.0], [2.2, 7.4, 0.0], [1.0, 1.3, 7.8]])
    base_fractional = rng.random((24, 3))
    displacements = np.cumsum(rng.normal(scale=0.008, size=(8, 24, 3)), axis=0)
    fractional = base_fractional[None, :, :] + displacements
    positions = np.einsum("tni,ij->tnj", fractional, cell)
    collection = make_trajectory(positions, cell=cell)
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.8))
    for frame in range(collection.n_frames):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=np.arange(24),
            candidates=np.arange(24),
            cutoff=2.1,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    stats = session.statistics()
    assert stats.rebuilds >= 1
    assert stats.rebuilds < stats.evaluations
    assert stats.candidate_pair_evaluations >= stats.accepted_pairs


def test_stateless_facade_rejects_verlet_backend_selection() -> None:
    collection = make_trajectory(np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]]))
    with pytest.raises(ValueError, match="NeighborSearchSession"):
        build_neighbor_list(
            collection,
            frame_index=0,
            center_indices=[0],
            candidate_neighbor_indices=[1],
            cutoff=1.5,
            backend=NeighborSearchBackend.VERLET_CACHE,
        )


def test_cache_arrays_are_read_only_and_summary_is_stable() -> None:
    collection = make_trajectory(np.array([[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]]))
    session = NeighborSearchSession(collection, VerletCacheOptions(skin=0.5))
    session.build_neighbor_list(
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=1.2,
    )
    digest = session.request_digests[0]
    cache = session.cache_for_request(digest)
    assert cache.summary()["n_candidate_pairs"] == 1
    assert not cache.candidate_neighbor_indices.flags.writeable
    assert not cache.reference_wrapped_positions.flags.writeable
    with pytest.raises(ValueError):
        cache.candidate_neighbor_indices[0] = 0


def test_deformation_aware_options_are_explicit_and_validated() -> None:
    options = VerletCacheOptions(deformation_aware=True)
    assert options.deformation_aware is True
    assert options.to_dict()["max_cell_condition_number"] == pytest.approx(1.0e12)
    with pytest.raises(TypeError, match="deformation_aware"):
        VerletCacheOptions(deformation_aware=1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="condition"):
        VerletCacheOptions(max_cell_condition_number=1.0)


def test_isotropic_expansion_reuses_deformation_aware_cache() -> None:
    scales = np.array([1.0, 1.03, 1.08])
    cells = scales[:, None, None] * np.repeat((np.eye(3) * 10.0)[None], 3, axis=0)
    fractional = np.repeat(
        np.array([[[0.10, 0.10, 0.10], [0.22, 0.10, 0.10], [0.70, 0.70, 0.70]]]),
        3,
        axis=0,
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.5, deformation_aware=True),
    )
    for frame in range(collection.n_frames):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1, 2],
            candidates=[0, 1, 2],
            cutoff=1.3,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    stats = session.statistics()
    assert stats.rebuilds == 1
    assert stats.reuse_evaluations == 2


def test_isotropic_compression_reuses_until_affine_margin_crosses() -> None:
    scales = np.array([1.0, 0.90, 0.74])
    cells = scales[:, None, None] * np.repeat((np.eye(3) * 10.0)[None], 3, axis=0)
    fractional = np.repeat(
        np.array([[[0.10, 0.10, 0.10], [0.25, 0.10, 0.10]]]),
        3,
        axis=0,
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.5, deformation_aware=True),
    )
    for frame in range(3):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1],
            candidates=[0, 1],
            cutoff=1.5,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    stats = session.statistics()
    assert stats.rebuilds == 2
    assert stats.reuse_evaluations == 1
    assert dict(stats.rebuild_reasons) == {
        "cell_deformation_limit": 1,
        "initial_build": 1,
    }


def test_orthorhombic_strain_and_volume_preserving_shear_reuse() -> None:
    h0 = np.array([[10.0, 0.0, 0.0], [0.0, 10.0, 0.0], [0.0, 0.0, 10.0]])
    orthorhombic = h0 @ np.diag([1.04, 0.98, 1.01])
    shear = h0 @ np.array([[1.0, 0.08, 0.0], [0.0, 1.0, 0.05], [0.0, 0.0, 1.0]])
    cells = np.stack([h0, orthorhombic, shear])
    fractional = np.repeat(
        np.array([[[0.10, 0.10, 0.10], [0.22, 0.10, 0.10], [0.35, 0.24, 0.10]]]),
        3,
        axis=0,
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.8, deformation_aware=True),
    )
    for frame in range(3):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1, 2],
            candidates=[0, 1, 2],
            cutoff=1.8,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    assert session.statistics().rebuilds == 1


def test_combined_shear_and_thermal_nonaffine_motion_reuses() -> None:
    h0 = np.eye(3) * 10.0
    cells = np.stack(
        [
            h0,
            h0 @ np.array([[1.0, 0.04, 0.0], [0.0, 1.0, 0.03], [0.0, 0.0, 1.0]]),
            h0 @ np.array([[1.0, 0.07, 0.0], [0.0, 1.0, 0.04], [0.0, 0.0, 1.0]]),
        ]
    )
    base = np.array([[0.10, 0.10, 0.10], [0.24, 0.10, 0.10], [0.50, 0.50, 0.50]])
    fractional = np.stack(
        [
            base,
            base + np.array([[0.002, 0.0, 0.0], [-0.002, 0.001, 0.0], [0.0, 0.0, 0.0]]),
            base
            + np.array([[0.004, 0.0, 0.0], [-0.003, 0.002, 0.0], [0.001, 0.0, 0.0]]),
        ]
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.8, deformation_aware=True),
    )
    for frame in range(3):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1, 2],
            candidates=[0, 1, 2],
            cutoff=1.6,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    assert session.statistics().rebuilds == 1


def test_rigid_cell_rotation_does_not_force_rebuild() -> None:
    theta = np.deg2rad(37.0)
    rotation = np.array(
        [
            [np.cos(theta), -np.sin(theta), 0.0],
            [np.sin(theta), np.cos(theta), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    h0 = np.array([[9.0, 0.0, 0.0], [1.2, 8.5, 0.0], [0.5, 0.8, 9.2]])
    cells = np.stack([h0, h0 @ rotation])
    fractional = np.repeat(
        np.array([[[0.10, 0.20, 0.30], [0.20, 0.20, 0.30], [0.72, 0.61, 0.52]]]),
        2,
        axis=0,
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.5, deformation_aware=True),
    )
    for frame in range(2):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1, 2],
            candidates=[0, 1, 2],
            cutoff=1.2,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    stats = session.statistics()
    assert stats.rebuilds == 1
    assert dict(stats.rebuild_reasons) == {"initial_build": 1}


def test_nonaffine_margin_crossing_has_distinct_rebuild_reason() -> None:
    cells = np.repeat((np.eye(3) * 10.0)[None], 2, axis=0)
    fractional = np.array(
        [
            [[0.10, 0.10, 0.10], [0.30, 0.10, 0.10]],
            [[0.14, 0.10, 0.10], [0.30, 0.10, 0.10]],
        ]
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(
            skin=0.4,
            safety_tolerance=1.0e-14,
            deformation_aware=True,
        ),
    )
    for frame in range(2):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1],
            candidates=[0, 1],
            cutoff=1.5,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    assert dict(session.statistics().rebuild_reasons) == {
        "initial_build": 1,
        "nonaffine_displacement_limit": 1,
    }


def test_species_aware_bound_does_not_double_mobile_singleton_motion() -> None:
    cells = np.repeat((np.eye(3) * 12.0)[None], 2, axis=0)
    atomic_numbers = np.array([14, 14, 11], dtype=np.int32)
    fractional = np.array(
        [
            [[0.10, 0.10, 0.10], [0.20, 0.10, 0.10], [0.50, 0.50, 0.50]],
            [[0.101, 0.10, 0.10], [0.199, 0.10, 0.10], [0.55, 0.50, 0.50]],
        ]
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells),
        cells=cells,
        atomic_numbers=atomic_numbers,
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.8, deformation_aware=True),
    )
    for frame in range(2):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1, 2],
            candidates=[0, 1, 2],
            cutoff=1.5,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    cache = session.cache_for_request(session.request_digests[0])
    assert cache.active_pair_atomic_numbers.tolist() == [[11, 14], [14, 14]]
    assert session.statistics().rebuilds == 1


def test_periodic_crossing_during_deformation_uses_unwrapped_fractional_motion() -> (
    None
):
    h0 = np.eye(3) * 10.0
    h1 = h0 @ np.array([[1.02, 0.04, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    cells = np.stack([h0, h1])
    fractional = np.array(
        [
            [[0.98, 0.20, 0.20], [0.08, 0.20, 0.20]],
            [[1.02, 0.20, 0.20], [0.08, 0.20, 0.20]],
        ]
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=1.0, deformation_aware=True),
    )
    for frame in range(2):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0],
            candidates=[1],
            cutoff=1.3,
        )
    assert session.statistics().rebuilds == 1


def test_omitted_pair_stays_complete_near_positive_affine_margin() -> None:
    physical = 1.0
    skin = 0.5
    reference_distance = 1.5001
    scales = np.array([1.0, 0.6668, 2.0 / 3.0])
    cells = scales[:, None, None] * np.repeat((np.eye(3) * 10.0)[None], 3, axis=0)
    fractional = np.repeat(
        np.array(
            [[[0.10, 0.10, 0.10], [0.10 + reference_distance / 10.0, 0.10, 0.10]]]
        ),
        3,
        axis=0,
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells), cells=cells
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(
            skin=skin,
            safety_tolerance=1.0e-12,
            deformation_aware=True,
        ),
    )
    first = session.build_neighbor_list(
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=physical,
    )
    second = session.build_neighbor_list(
        frame_index=1,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=physical,
    )
    third = session.build_neighbor_list(
        frame_index=2,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=physical,
    )
    assert first.n_pairs == second.n_pairs == third.n_pairs == 0
    stats = session.statistics()
    assert stats.rebuilds == 2
    assert stats.reuse_evaluations == 1
    assert dict(stats.rebuild_reasons) == {
        "cell_deformation_limit": 1,
        "initial_build": 1,
    }


def test_randomized_variable_cell_path_matches_fresh_backends() -> None:
    rng = np.random.default_rng(20260714)
    h0 = np.array([[8.5, 0.0, 0.0], [1.7, 8.0, 0.0], [0.8, 1.1, 8.8]])
    n_frames = 9
    n_atoms = 28
    cells = []
    fractional = []
    base = rng.random((n_atoms, 3))
    for frame in range(n_frames):
        shear = 0.015 * frame / (n_frames - 1)
        stretch = np.diag(
            [1.0 + 0.01 * frame, 1.0 - 0.004 * frame, 1.0 + 0.003 * frame]
        )
        deformation = stretch @ np.array(
            [[1.0, shear, 0.0], [0.0, 1.0, 0.5 * shear], [0.0, 0.0, 1.0]]
        )
        cells.append(h0 @ deformation)
        fractional.append(base + rng.normal(scale=0.0015, size=(n_atoms, 3)))
    cells_array = np.asarray(cells)
    fractional_array = np.asarray(fractional)
    collection = make_trajectory(
        positions_from_fractional(fractional_array, cells_array),
        cells=cells_array,
        atomic_numbers=np.resize(np.array([8, 11, 14], dtype=np.int32), n_atoms),
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.9, deformation_aware=True),
    )
    for frame in range(n_frames):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=np.arange(n_atoms),
            candidates=np.arange(n_atoms),
            cutoff=2.0,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    stats = session.statistics()
    assert stats.rebuilds >= 1
    assert stats.rebuilds < stats.evaluations


def test_changed_cell_ensemble_rebuilds_without_fractional_unwrap() -> None:
    h0 = np.eye(3) * 10.0
    h1 = h0 @ np.array([[1.02, 0.03, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    cells = np.stack([h0, h1])
    fractional = np.array(
        [
            [[0.10, 0.10, 0.10], [0.22, 0.10, 0.10]],
            [[0.11, 0.10, 0.10], [0.22, 0.10, 0.10]],
        ]
    )
    trajectory = make_trajectory(
        positions_from_fractional(fractional, cells),
        cells=cells,
    )
    collection = trajectory.as_ensemble()
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(skin=0.8, deformation_aware=True),
    )
    for frame in range(2):
        assert_session_matches_fresh(
            session,
            collection,
            frame,
            centers=[0, 1],
            candidates=[0, 1],
            cutoff=1.5,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
        )
    assert dict(session.statistics().rebuild_reasons) == {
        "fractional_unwrapping_unavailable": 1,
        "initial_build": 1,
    }


def test_deformation_aware_rejects_ill_conditioned_cell() -> None:
    cells = np.stack([np.eye(3) * 10.0, np.diag([10.0, 10.0, 1.0e-7])])
    fractional = np.repeat(
        np.array([[[0.10, 0.10, 0.10], [0.20, 0.10, 0.10]]]),
        2,
        axis=0,
    )
    collection = make_trajectory(
        positions_from_fractional(fractional, cells),
        cells=cells,
        pbc=np.zeros(3, dtype=bool),
    )
    session = NeighborSearchSession(
        collection,
        VerletCacheOptions(
            skin=0.5,
            deformation_aware=True,
            max_cell_condition_number=1.0e6,
        ),
    )
    session.build_neighbor_list(
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=1.5,
    )
    with pytest.raises(InvalidCellGeometryError, match="ill-conditioned"):
        session.build_neighbor_list(
            frame_index=1,
            center_indices=[0],
            candidate_neighbor_indices=[1],
            cutoff=1.5,
        )
