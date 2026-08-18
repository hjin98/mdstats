"""Focused tests for the shared CSR neighbor kernel."""

from __future__ import annotations

import numpy as np
import pytest

import mdstats.analysis._neighbors as neighbors_module
from mdstats import AtomisticFrameCollection, FrameCollectionProvenance, FrameSemantics
from mdstats.analysis._neighbors import (
    PairCounting,
    UnsafeNeighborCutoffError,
    build_neighbor_list,
    compute_safe_cutoff,
    minimum_image_vectors,
)


def make_collection(
    positions: np.ndarray,
    *,
    cell: np.ndarray | None = None,
    atomic_numbers: np.ndarray | None = None,
    pbc: np.ndarray | None = None,
) -> AtomisticFrameCollection:
    positions = np.asarray(positions, dtype=float)
    if positions.ndim == 2:
        positions = positions[None, ...]
    n_frames, n_atoms, _ = positions.shape
    if cell is None:
        cells = np.repeat((np.eye(3) * 10.0)[None, ...], n_frames, axis=0)
    else:
        cell = np.asarray(cell, dtype=float)
        cells = np.repeat(cell[None, ...], n_frames, axis=0)
    scaled = np.einsum("tni,tij->tnj", positions, np.linalg.inv(cells))
    return AtomisticFrameCollection(
        frame_semantics=FrameSemantics.ENSEMBLE,
        frame_ids=np.arange(n_frames),
        atomic_numbers=(
            np.ones(n_atoms, dtype=np.int32)
            if atomic_numbers is None
            else np.asarray(atomic_numbers, dtype=np.int32)
        ),
        masses=np.ones(n_atoms),
        pbc=np.ones(3, dtype=bool) if pbc is None else np.asarray(pbc, dtype=bool),
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


def test_csr_rows_vectors_and_counts() -> None:
    collection = make_collection(
        np.array(
            [
                [0.0, 0.0, 0.0],
                [5.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [5.0, 1.0, 0.0],
            ]
        )
    )
    result = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0, 1],
        candidate_neighbor_indices=[2, 3],
        cutoff=1.5,
    )
    np.testing.assert_array_equal(result.offsets, [0, 1, 2])
    np.testing.assert_array_equal(result.neighbor_indices, [2, 3])
    np.testing.assert_array_equal(result.coordination_counts, [1, 1])
    np.testing.assert_allclose(result.distances, [1.0, 1.0])
    np.testing.assert_allclose(result.vectors, [[1, 0, 0], [0, 1, 0]])


def test_unordered_identical_retains_one_physical_pair() -> None:
    collection = make_collection(np.array([[0, 0, 0], [1, 0, 0], [3, 0, 0]]))
    result = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0, 1, 2],
        candidate_neighbor_indices=[0, 1, 2],
        cutoff=2.5,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
    )
    np.testing.assert_array_equal(result.neighbor_indices, [1, 2])
    np.testing.assert_array_equal(result.offsets, [0, 1, 2, 2])


def test_minimum_image_vectors_support_triclinic_cell() -> None:
    cell = np.array([[4.0, 0.0, 0.0], [1.0, 4.0, 0.0], [0.5, 0.5, 4.0]])
    displacement = np.array([0.8, 0.8, 0.8]) @ cell
    vectors, distances = minimum_image_vectors(
        displacement,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
    )
    expected = np.array([-0.2, -0.2, -0.2]) @ cell
    np.testing.assert_allclose(vectors, expected)
    assert distances == pytest.approx(np.linalg.norm(expected))


def test_safe_cutoff_uses_shortest_periodic_translation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cell = np.array([[4.0, 0.0, 0.0], [3.5, 1.0, 0.0], [0.0, 0.0, 8.0]])
    operation = np.array([[-1, 1, 0], [-1, 2, 0], [0, 0, 1]], dtype=int)
    reduced = operation @ cell
    monkeypatch.setattr(
        neighbors_module,
        "minkowski_reduce",
        lambda input_cell, pbc: (reduced, operation),
    )
    monkeypatch.setattr(
        neighbors_module,
        "is_minkowski_reduced",
        lambda input_cell, pbc: True,
    )

    collection = make_collection(np.array([[0.0, 0.0, 0.0]]), cell=cell)
    safe = compute_safe_cutoff(collection, frame_indices=[0])
    shortest = np.linalg.norm(cell[1] - cell[0])
    assert safe == pytest.approx(0.5 * shortest)

    face_height_bound = 0.5 * min(
        abs(np.linalg.det(cell))
        / np.linalg.norm(np.cross(cell[j], cell[k]))
        for j, k in ((1, 2), (0, 2), (0, 1))
    )
    assert safe > face_height_bound

    with pytest.raises(UnsafeNeighborCutoffError, match="shortest nonzero"):
        build_neighbor_list(
            collection,
            frame_index=0,
            center_indices=[0],
            candidate_neighbor_indices=[0],
            cutoff=safe * 1.1,
        )


def test_safe_cutoff_accepts_eight_angstrom_for_lta_primitive_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    a = 17.3630
    cell = np.array(
        [
            [a, 0.0, 0.0],
            [0.5 * a, np.sqrt(3.0) * 0.5 * a, 0.0],
            [0.5 * a, a / (2.0 * np.sqrt(3.0)), a * np.sqrt(2.0 / 3.0)],
        ]
    )
    monkeypatch.setattr(
        neighbors_module,
        "minkowski_reduce",
        lambda input_cell, pbc: (np.asarray(input_cell), np.eye(3, dtype=int)),
    )
    monkeypatch.setattr(
        neighbors_module,
        "is_minkowski_reduced",
        lambda input_cell, pbc: True,
    )

    collection = make_collection(np.array([[0.0, 0.0, 0.0]]), cell=cell)
    safe = compute_safe_cutoff(collection, frame_indices=[0])
    assert safe == pytest.approx(0.5 * a)
    assert safe > 8.0

    # The historical face-height check would reject this same cutoff.
    face_height_bound = 0.5 * a * np.sqrt(2.0 / 3.0)
    assert face_height_bound < 8.0




def test_safe_cutoff_reuses_exactly_repeated_cells(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    positions = np.zeros((3, 1, 3), dtype=float)
    collection = make_collection(positions, cell=np.diag([10.0, 12.0, 14.0]))
    calls = 0

    def fake_shortest(cell: np.ndarray, pbc: np.ndarray) -> float:
        nonlocal calls
        calls += 1
        return 10.0

    monkeypatch.setattr(
        neighbors_module,
        "_shortest_periodic_translation_length",
        fake_shortest,
    )

    safe = compute_safe_cutoff(collection, frame_indices=[0, 1, 2])

    assert safe == pytest.approx(5.0)
    assert calls == 1


def test_partial_periodic_reduction_preserves_periodic_sublattice(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cell = np.array([[4.0, 0.0, 0.0], [3.5, 1.0, 0.0], [0.0, 0.0, 9.0]])
    pbc = np.array([True, True, False])
    operation = np.array([[-1, 1, 0], [-1, 2, 0], [0, 0, 1]], dtype=int)
    reduced = operation @ cell
    monkeypatch.setattr(
        neighbors_module,
        "minkowski_reduce",
        lambda input_cell, pbc: (reduced, operation),
    )
    monkeypatch.setattr(
        neighbors_module,
        "is_minkowski_reduced",
        lambda input_cell, pbc: True,
    )

    collection = make_collection(
        np.array([[0.0, 0.0, 0.0]]),
        cell=cell,
        pbc=pbc,
    )
    safe = compute_safe_cutoff(collection, frame_indices=[0])

    assert safe == pytest.approx(0.5 * np.linalg.norm(cell[1] - cell[0]))


def test_neighbor_image_shifts_reconstruct_periodic_vector() -> None:
    collection = make_collection(np.array([[9.5, 0.0, 0.0], [0.5, 0.0, 0.0]]))
    result = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=1.5,
    )
    np.testing.assert_array_equal(result.image_shifts, [[1, 0, 0]])
    raw = np.array([0.5, 0.0, 0.0]) - np.array([9.5, 0.0, 0.0])
    reconstructed = raw + result.image_shifts[0] @ collection.cells[0]
    np.testing.assert_allclose(reconstructed, result.vectors[0])


def test_triclinic_neighbor_image_shifts_reconstruct_vector() -> None:
    cell = np.array([[4.0, 0.0, 0.0], [1.0, 4.0, 0.0], [0.5, 0.5, 4.0]])
    fractional = np.array([[0.8, 0.8, 0.8], [0.0, 0.0, 0.0]])
    positions = fractional @ cell
    collection = make_collection(positions, cell=cell)
    result = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=1.9,
    )
    np.testing.assert_array_equal(result.image_shifts, [[1, 1, 1]])
    raw = positions[1] - positions[0]
    reconstructed = raw + result.image_shifts[0] @ cell
    np.testing.assert_allclose(reconstructed, result.vectors[0])


def test_minimum_image_vectors_ignores_irrelevant_image_label_bookkeeping() -> None:
    """DATA6-style vector geometry must not depend on integer image labels.

    This LTA-like displacement lies within floating-point noise of an integer
    reduced-lattice plane.  The historical vectors-only path reconstructed an
    unused image label through an explicit inverse and could spuriously reject
    the otherwise valid MIC by a whole lattice vector.
    """

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

    vectors, distances = minimum_image_vectors(
        displacement,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
    )
    ase_vectors, ase_distances = neighbors_module.find_mic(
        displacement, cell, pbc=np.ones(3, dtype=bool)
    )
    np.testing.assert_allclose(vectors, ase_vectors, rtol=1.0e-12, atol=1.0e-12)
    assert distances == pytest.approx(float(ase_distances), rel=1.0e-12, abs=1.0e-12)


def test_minimum_image_geometry_uses_wrap_equivalent_fractional_solve() -> None:
    """Image-bearing MIC uses the same solve convention as wrap_positions."""

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

    vectors, distances, shifts = neighbors_module.minimum_image_geometry(
        displacement,
        cell=cell,
        pbc=np.ones(3, dtype=bool),
    )
    ase_vectors, ase_distances = neighbors_module.find_mic(
        displacement, cell, pbc=np.ones(3, dtype=bool)
    )
    np.testing.assert_allclose(vectors, ase_vectors, rtol=1.0e-12, atol=1.0e-12)
    assert distances == pytest.approx(float(ase_distances), rel=1.0e-12, abs=1.0e-12)
    np.testing.assert_allclose(
        displacement + shifts @ cell,
        vectors,
        rtol=2.0e-12,
        atol=2.0e-11,
    )
