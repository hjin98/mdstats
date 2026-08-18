from __future__ import annotations

import numpy as np
import pytest

from mdstats.analysis._cell_list import (
    build_cell_list_neighbor_list_with_diagnostics,
)
from mdstats.analysis._neighbor_compare import assert_neighbor_results_equal
from mdstats.analysis._neighbors import (
    CellListComplexityError,
    CellListOptions,
    NeighborSearchBackend,
    PairCounting,
    build_neighbor_list,
    compute_safe_cutoff,
)
from tests.support.neighbor_cases import (
    generate_random_neighbor_case,
    make_collection_from_fractional,
)


@pytest.mark.parametrize(
    ("geometry", "selection", "seed"),
    [
        ("orthogonal", "directed_disjoint", 1101),
        ("orthogonal", "unordered_identical", 1102),
        ("triclinic", "directed_disjoint", 1201),
        ("triclinic", "unordered_identical", 1202),
        ("mixed_pbc", "directed_disjoint", 1301),
        ("mixed_pbc", "unordered_identical", 1302),
        ("boundary", "directed_disjoint", 1401),
        ("boundary", "unordered_identical", 1402),
    ],
)
def test_cell_list_matches_dense_random_matrix(
    geometry: str,
    selection: str,
    seed: int,
) -> None:
    case = generate_random_neighbor_case(
        seed=seed,
        geometry=geometry,
        selection=selection,
        n_atoms=36,
    )
    dense = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
        backend=NeighborSearchBackend.DENSE,
        block_size=5,
    )
    cell_list = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
        backend=NeighborSearchBackend.CELL_LIST,
    )
    assert cell_list.backend is NeighborSearchBackend.CELL_LIST
    assert_neighbor_results_equal(cell_list, dense)


def test_highly_skewed_cell_matches_dense_with_and_without_reduction() -> None:
    cell = np.array(
        [
            [12.0, 0.0, 0.0],
            [11.0, 3.0, 0.0],
            [2.0, 1.0, 10.0],
        ]
    )
    rng = np.random.default_rng(22341)
    collection = make_collection_from_fractional(
        rng.random((96, 3)), cell=cell, pbc=np.ones(3, dtype=bool)
    )
    cutoff = 0.95 * compute_safe_cutoff(collection, frame_indices=[0])
    indices = rng.permutation(collection.n_atoms).astype(np.int64)
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=cutoff,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
        backend="dense",
    )
    for reduction in (False, True):
        actual, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
            collection,
            frame_index=0,
            center_indices=indices,
            candidate_neighbor_indices=indices.copy(),
            cutoff=cutoff,
            pair_counting=PairCounting.UNORDERED_IDENTICAL,
            options=CellListOptions(use_lattice_reduction=reduction),
        )
        assert_neighbor_results_equal(actual, dense)
        assert diagnostics.stencil_size > 0
        assert diagnostics.exact_pair_evaluations <= collection.n_atoms**2
    assert diagnostics.reduction_applied


def test_nonperiodic_cell_list_matches_dense() -> None:
    cell = np.array(
        [
            [10.0, 0.0, 0.0],
            [3.0, 9.0, 0.0],
            [1.5, 2.0, 8.0],
        ]
    )
    rng = np.random.default_rng(9001)
    fractional = rng.normal(loc=0.5, scale=0.8, size=(72, 3))
    collection = make_collection_from_fractional(
        fractional,
        cell=cell,
        pbc=np.zeros(3, dtype=bool),
    )
    centers = np.arange(0, 36, dtype=np.int64)
    candidates = np.arange(36, 72, dtype=np.int64)
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=2.2,
        backend="dense",
    )
    actual = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=2.2,
        backend="cell_list",
    )
    assert_neighbor_results_equal(actual, dense)
    np.testing.assert_array_equal(actual.image_shifts, 0)


def test_cell_list_handles_zero_and_one_accepted_pair() -> None:
    cell = np.diag([10.0, 10.0, 10.0])
    fractional = np.array(
        [
            [0.10, 0.10, 0.10],
            [0.15, 0.10, 0.10],
            [0.80, 0.80, 0.80],
        ]
    )
    collection = make_collection_from_fractional(
        fractional, cell=cell, pbc=np.ones(3, dtype=bool)
    )
    zero = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[2],
        cutoff=1.0,
        backend="cell_list",
    )
    assert zero.n_pairs == 0
    one = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=1.0,
        backend="cell_list",
    )
    assert one.n_pairs == 1
    assert one.neighbor_indices.tolist() == [1]


def test_dense_cluster_and_candidate_order_match_dense() -> None:
    rng = np.random.default_rng(42)
    fractional = 0.48 + 0.02 * rng.normal(size=(40, 3))
    collection = make_collection_from_fractional(
        fractional,
        cell=np.diag([12.0, 12.0, 12.0]),
        pbc=np.ones(3, dtype=bool),
    )
    order = rng.permutation(40).astype(np.int64)
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=order,
        candidate_neighbor_indices=order.copy(),
        cutoff=1.4,
        pair_counting="unordered_identical",
        backend="dense",
    )
    actual = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=order,
        candidate_neighbor_indices=order.copy(),
        cutoff=1.4,
        pair_counting="unordered_identical",
        backend="cell_list",
    )
    assert_neighbor_results_equal(actual, dense)
    assert actual.n_pairs == dense.n_pairs


def test_cutoff_near_unique_image_limit_matches_dense() -> None:
    rng = np.random.default_rng(519)
    cell = np.array(
        [
            [10.0, 0.0, 0.0],
            [2.4, 9.0, 0.0],
            [1.1, 1.6, 8.5],
        ]
    )
    collection = make_collection_from_fractional(
        rng.random((64, 3)), cell=cell, pbc=np.ones(3, dtype=bool)
    )
    cutoff = 0.999 * compute_safe_cutoff(collection, frame_indices=[0])
    indices = np.arange(collection.n_atoms, dtype=np.int64)
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=cutoff,
        pair_counting="unordered_identical",
        backend="dense",
    )
    actual = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=cutoff,
        pair_counting="unordered_identical",
        backend="cell_list",
    )
    assert_neighbor_results_equal(actual, dense)


def test_cell_list_preserves_original_basis_image_shifts_after_reduction() -> None:
    cell = np.array(
        [
            [10.0, 0.0, 0.0],
            [9.5, 1.0, 0.0],
            [0.0, 0.0, 12.0],
        ]
    )
    fractional = np.array(
        [
            [0.98, 0.02, 0.50],
            [0.02, 0.98, 0.50],
            [0.50, 0.50, 0.50],
        ]
    )
    collection = make_collection_from_fractional(
        fractional, cell=cell, pbc=np.ones(3, dtype=bool)
    )
    cutoff = 0.9 * compute_safe_cutoff(collection, frame_indices=[0])
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1, 2],
        cutoff=cutoff,
        backend="dense",
    )
    actual, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1, 2],
        cutoff=cutoff,
        options=CellListOptions(use_lattice_reduction=True),
    )
    assert diagnostics.reduction_applied
    assert_neighbor_results_equal(actual, dense)


def test_multiple_species_pair_cutoffs_match_dense() -> None:
    rng = np.random.default_rng(2026)
    numbers = np.tile(np.array([8, 13, 14], dtype=np.int32), 24)
    collection = make_collection_from_fractional(
        rng.random((72, 3)),
        cell=np.array([[14.0, 0.0, 0.0], [3.0, 13.0, 0.0], [2.0, 1.5, 12.0]]),
        pbc=np.ones(3, dtype=bool),
        atomic_numbers=numbers,
    )
    for center_z, candidate_z, cutoff in ((14, 8, 2.1), (13, 8, 2.4), (8, 8, 2.8)):
        centers = np.flatnonzero(numbers == center_z).astype(np.int64)
        candidates = np.flatnonzero(numbers == candidate_z).astype(np.int64)
        counting = (
            PairCounting.UNORDERED_IDENTICAL
            if center_z == candidate_z
            else PairCounting.DIRECTED
        )
        dense = build_neighbor_list(
            collection,
            frame_index=0,
            center_indices=centers,
            candidate_neighbor_indices=candidates,
            cutoff=cutoff,
            pair_counting=counting,
            backend="dense",
        )
        actual = build_neighbor_list(
            collection,
            frame_index=0,
            center_indices=centers,
            candidate_neighbor_indices=candidates,
            cutoff=cutoff,
            pair_counting=counting,
            backend="cell_list",
        )
        assert_neighbor_results_equal(actual, dense)


def test_cell_list_is_deterministic_and_reduces_pair_evaluations() -> None:
    rng = np.random.default_rng(789)
    n_atoms = 320
    collection = make_collection_from_fractional(
        rng.random((n_atoms, 3)),
        cell=np.diag([36.0, 36.0, 36.0]),
        pbc=np.ones(3, dtype=bool),
    )
    indices = np.arange(n_atoms, dtype=np.int64)
    first, first_diag = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=2.4,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
    )
    second, second_diag = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=2.4,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
    )
    assert_neighbor_results_equal(first, second)
    assert first_diag == second_diag
    dense_unordered_pairs = n_atoms * (n_atoms - 1) // 2
    assert first_diag.exact_pair_evaluations < dense_unordered_pairs // 4


def test_cell_list_options_and_hard_limits_are_validated() -> None:
    with pytest.raises(ValueError, match="positive"):
        CellListOptions(max_stencil_offsets=0)
    with pytest.raises(TypeError, match="integer"):
        CellListOptions(max_stencil_candidates=True)

    collection = make_collection_from_fractional(
        np.random.default_rng(4).random((12, 3)),
        cell=np.diag([10.0, 10.0, 10.0]),
        pbc=np.ones(3, dtype=bool),
    )
    with pytest.raises(CellListComplexityError, match="max_stencil_candidates"):
        build_neighbor_list(
            collection,
            frame_index=0,
            center_indices=np.arange(12),
            candidate_neighbor_indices=np.arange(12),
            cutoff=2.0,
            pair_counting="unordered_identical",
            backend="cell_list",
            cell_list_options=CellListOptions(max_stencil_candidates=1),
        )


def test_one_dimensional_periodic_axis_matches_dense() -> None:
    rng = np.random.default_rng(1776)
    fractional = rng.normal(loc=0.5, scale=0.7, size=(60, 3))
    fractional[:, 0] -= np.floor(fractional[:, 0])
    collection = make_collection_from_fractional(
        fractional,
        cell=np.array([[15.0, 0.0, 0.0], [2.0, 9.0, 0.0], [1.0, 1.5, 8.0]]),
        pbc=np.array([True, False, False]),
    )
    centers = np.arange(30, dtype=np.int64)
    candidates = np.arange(30, 60, dtype=np.int64)
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=2.3,
        backend="dense",
    )
    actual = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=centers,
        candidate_neighbor_indices=candidates,
        cutoff=2.3,
        backend="cell_list",
    )
    assert_neighbor_results_equal(actual, dense)
    np.testing.assert_array_equal(actual.image_shifts[:, 1:], 0)


def test_two_dimensional_periodic_reduction_matches_dense() -> None:
    rng = np.random.default_rng(31415)
    cell = np.array(
        [
            [10.0, 0.0, 0.0],
            [9.5, 1.0, 0.0],
            [0.5, 0.3, 15.0],
        ]
    )
    fractional = rng.random((80, 3))
    fractional[:, 2] = rng.normal(0.5, 0.15, size=80)
    collection = make_collection_from_fractional(
        fractional, cell=cell, pbc=np.array([True, True, False])
    )
    cutoff = 0.9 * compute_safe_cutoff(collection, frame_indices=[0])
    indices = np.arange(80, dtype=np.int64)
    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=cutoff,
        pair_counting="unordered_identical",
        backend="dense",
    )
    actual, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices.copy(),
        cutoff=cutoff,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
        options=CellListOptions(use_lattice_reduction=True),
    )
    assert diagnostics.reduction_applied
    assert_neighbor_results_equal(actual, dense)
    np.testing.assert_array_equal(actual.image_shifts[:, 2], 0)


def test_iter_neighbor_lists_accepts_explicit_cell_list_backend() -> None:
    case = generate_random_neighbor_case(
        seed=8181,
        geometry="triclinic",
        selection="directed_disjoint",
        n_atoms=30,
    )
    from mdstats.analysis._neighbors import iter_neighbor_lists

    results = list(
        iter_neighbor_lists(
            case.collection,
            frame_indices=[0],
            center_indices=case.center_indices,
            candidate_neighbor_indices=case.candidate_indices,
            cutoff=case.cutoff,
            pair_counting=case.pair_counting,
            backend="cell_list",
        )
    )
    assert len(results) == 1
    assert results[0].backend is NeighborSearchBackend.CELL_LIST




def test_lta_eight_angstrom_cutoff_matches_dense_beyond_face_height() -> None:
    a = 17.3630
    cell = np.array(
        [
            [a, 0.0, 0.0],
            [0.5 * a, np.sqrt(3.0) * 0.5 * a, 0.0],
            [0.5 * a, a / (2.0 * np.sqrt(3.0)), a * np.sqrt(2.0 / 3.0)],
        ]
    )
    rng = np.random.default_rng(1973)
    collection = make_collection_from_fractional(
        rng.random((120, 3)), cell=cell, pbc=np.ones(3, dtype=bool)
    )
    indices = np.arange(collection.n_atoms, dtype=np.int64)
    cutoff = 8.0

    assert 0.5 * a * np.sqrt(2.0 / 3.0) < cutoff
    assert cutoff < compute_safe_cutoff(collection, frame_indices=[0])

    dense = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices,
        cutoff=cutoff,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
        backend="dense",
    )
    actual, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
        collection,
        frame_index=0,
        center_indices=indices,
        candidate_neighbor_indices=indices,
        cutoff=cutoff,
        pair_counting=PairCounting.UNORDERED_IDENTICAL,
    )

    assert_neighbor_results_equal(actual, dense)
    assert diagnostics.accepted_pairs == dense.n_pairs


def test_relaxed_na_lta_framework_pairs_match_dense() -> None:
    from pathlib import Path

    from mdstats import read_structure

    structure = Path(__file__).parent / "data" / "Na_LTA_relaxed.POSCAR"
    collection = read_structure(structure)
    numbers = collection.atomic_numbers
    oxygen = np.flatnonzero(numbers == 8).astype(np.int64)
    for center_number in (13, 14):
        centers = np.flatnonzero(numbers == center_number).astype(np.int64)
        dense = build_neighbor_list(
            collection,
            frame_index=0,
            center_indices=centers,
            candidate_neighbor_indices=oxygen,
            cutoff=2.0,
            backend="dense",
        )
        actual, diagnostics = build_cell_list_neighbor_list_with_diagnostics(
            collection,
            frame_index=0,
            center_indices=centers,
            candidate_neighbor_indices=oxygen,
            cutoff=2.0,
        )
        assert_neighbor_results_equal(actual, dense)
        assert actual.n_pairs == centers.size * 4
        assert diagnostics.exact_pair_evaluations < centers.size * oxygen.size
