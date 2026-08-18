"""Stage-S0 hardening tests for the dense neighbor reference backend."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest

from mdstats.analysis._neighbor_compare import (
    NeighborComparisonOptions,
    assert_neighbor_results_equal,
    canonicalize_neighbor_result,
    compare_neighbor_results,
)
from mdstats.analysis._neighbors import (
    NeighborListResult,
    NeighborSearchBackend,
    PairCounting,
    build_neighbor_list,
)
from tests.support.neighbor_cases import (
    build_scalar_reference_neighbor_list,
    generate_random_neighbor_case,
    make_collection_from_fractional,
)


@pytest.mark.parametrize(
    ("geometry", "selection", "seed"),
    [
        ("orthogonal", "unordered_identical", 1729),
        ("orthogonal", "directed_disjoint", 2718),
        ("triclinic", "unordered_identical", 31415),
        ("triclinic", "directed_disjoint", 16180),
        ("mixed_pbc", "unordered_identical", 57721),
        ("mixed_pbc", "directed_disjoint", 14142),
        ("boundary", "unordered_identical", 17320),
        ("boundary", "directed_disjoint", 22360),
    ],
)
def test_dense_backend_matches_scalar_reference_across_random_cases(
    geometry: str,
    selection: str,
    seed: int,
) -> None:
    case = generate_random_neighbor_case(
        seed=seed,
        geometry=geometry,  # type: ignore[arg-type]
        selection=selection,  # type: ignore[arg-type]
    )
    expected = build_scalar_reference_neighbor_list(case)
    for block_size in (1, 3, 7, 256):
        actual = build_neighbor_list(
            case.collection,
            frame_index=0,
            center_indices=case.center_indices,
            candidate_neighbor_indices=case.candidate_indices,
            cutoff=case.cutoff,
            pair_counting=case.pair_counting,
            backend=NeighborSearchBackend.DENSE,
            block_size=block_size,
        )
        assert_neighbor_results_equal(actual, expected)


def test_dense_backend_is_explicit_and_default_is_identical() -> None:
    case = generate_random_neighbor_case(
        seed=1234,
        geometry="triclinic",
        selection="unordered_identical",
    )
    implicit = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
    )
    explicit = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
        backend="dense",
    )
    assert implicit.backend is NeighborSearchBackend.DENSE
    assert_neighbor_results_equal(
        implicit,
        explicit,
        options=NeighborComparisonOptions(compare_backend=True),
    )


def test_dense_backend_is_deterministic_under_repeated_runs() -> None:
    case = generate_random_neighbor_case(
        seed=8675309,
        geometry="mixed_pbc",
        selection="directed_disjoint",
    )
    results = [
        build_neighbor_list(
            case.collection,
            frame_index=0,
            center_indices=case.center_indices,
            candidate_neighbor_indices=case.candidate_indices,
            cutoff=case.cutoff,
            pair_counting=case.pair_counting,
            block_size=5,
        )
        for _ in range(4)
    ]
    for result in results[1:]:
        assert_neighbor_results_equal(
            result,
            results[0],
            options=NeighborComparisonOptions(canonicalize=False, compare_backend=True),
        )


def test_canonical_comparison_normalizes_selection_order() -> None:
    case = generate_random_neighbor_case(
        seed=42,
        geometry="orthogonal",
        selection="unordered_identical",
    )
    forward = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
    )
    reversed_indices = case.center_indices[::-1]
    reverse = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=reversed_indices,
        candidate_neighbor_indices=reversed_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
    )
    assert_neighbor_results_equal(forward, reverse)
    strict = compare_neighbor_results(
        forward,
        reverse,
        options=NeighborComparisonOptions(canonicalize=False),
    )
    assert not strict.equal
    np.testing.assert_array_equal(
        canonicalize_neighbor_result(forward).center_indices,
        np.sort(case.center_indices),
    )


def test_comparison_reports_periodic_identity_mismatch() -> None:
    case = generate_random_neighbor_case(
        seed=99,
        geometry="boundary",
        selection="unordered_identical",
    )
    result = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
    )
    assert result.n_pairs > 0
    shifts = np.asarray(result.image_shifts).copy()
    shifts[0, 0] += 1
    altered = NeighborListResult(
        frame_index=result.frame_index,
        center_indices=result.center_indices,
        neighbor_indices=result.neighbor_indices,
        offsets=result.offsets,
        vectors=result.vectors,
        distances=result.distances,
        image_shifts=shifts,
        cutoff=result.cutoff,
        pair_counting=result.pair_counting,
        backend=result.backend,
    )
    report = compare_neighbor_results(result, altered)
    assert not report.equal
    assert any("image_shifts" in message for message in report.messages)
    with pytest.raises(AssertionError, match="image_shifts"):
        report.require_equal()


def test_neighbor_result_arrays_are_immutable() -> None:
    case = generate_random_neighbor_case(
        seed=101,
        geometry="orthogonal",
        selection="directed_disjoint",
    )
    result = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
    )
    for array in (
        result.center_indices,
        result.neighbor_indices,
        result.offsets,
        result.vectors,
        result.distances,
        result.image_shifts,
    ):
        assert not array.flags.writeable
    with pytest.raises(ValueError):
        result.center_indices[0] = 99


def test_strict_cutoff_excludes_pair_exactly_on_boundary() -> None:
    collection = make_collection_from_fractional(
        np.array([[0.1, 0.2, 0.3], [0.3, 0.2, 0.3]]),
        cell=np.diag([10.0, 10.0, 10.0]),
        pbc=np.ones(3, dtype=bool),
    )
    result = build_neighbor_list(
        collection,
        frame_index=0,
        center_indices=[0],
        candidate_neighbor_indices=[1],
        cutoff=2.0,
        pair_counting=PairCounting.DIRECTED,
    )
    assert result.n_pairs == 0


def test_comparison_options_reject_negative_tolerance() -> None:
    with pytest.raises(ValueError, match="vector_atol"):
        NeighborComparisonOptions(vector_atol=-1.0)


def test_backend_metadata_can_be_ignored_for_cross_backend_oracle_checks() -> None:
    case = generate_random_neighbor_case(
        seed=701,
        geometry="orthogonal",
        selection="directed_disjoint",
    )
    result = build_neighbor_list(
        case.collection,
        frame_index=0,
        center_indices=case.center_indices,
        candidate_neighbor_indices=case.candidate_indices,
        cutoff=case.cutoff,
        pair_counting=case.pair_counting,
    )
    # ``replace`` documents the intended future use: optimized results may carry
    # different backend metadata while remaining scientifically identical.
    equivalent = replace(result, backend=NeighborSearchBackend.DENSE)
    assert_neighbor_results_equal(result, equivalent)


def test_iterator_propagates_explicit_dense_backend() -> None:
    from mdstats.analysis._neighbors import iter_neighbor_lists

    case = generate_random_neighbor_case(
        seed=404,
        geometry="orthogonal",
        selection="directed_disjoint",
    )
    results = list(
        iter_neighbor_lists(
            case.collection,
            frame_indices=[0],
            center_indices=case.center_indices,
            candidate_neighbor_indices=case.candidate_indices,
            cutoff=case.cutoff,
            pair_counting=case.pair_counting,
            backend="dense",
            block_size=4,
        )
    )
    assert len(results) == 1
    assert results[0].backend is NeighborSearchBackend.DENSE


def test_unknown_backend_name_is_rejected() -> None:
    case = generate_random_neighbor_case(
        seed=405,
        geometry="orthogonal",
        selection="directed_disjoint",
    )
    with pytest.raises(ValueError, match="unknown_backend"):
        build_neighbor_list(
            case.collection,
            frame_index=0,
            center_indices=case.center_indices,
            candidate_neighbor_indices=case.candidate_indices,
            cutoff=case.cutoff,
            pair_counting=case.pair_counting,
            backend="unknown_backend",  # type: ignore[arg-type]
        )
