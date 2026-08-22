from __future__ import annotations

import numpy as np
import pytest

from mdstats.training_data.mvsel2_native_backend import (
    qualify_mvsel2_native_backend_v2,
    score_family_candidate_batch_v2,
)
from mdstats.training_data.mvsel2_phase_b_kernel import (
    build_target_multi_view_lazy_frontier_v2_kernel,
    choose_target_multi_view_phase_b_candidate_v2_kernel,
)
from mdstats.training_data import target_multi_view_selector_v2 as selector_v2
from tests.test_mlff_mvsel2_forward import _forward_fixture


def _require_native(*, parallel: bool = False):
    status = qualify_mvsel2_native_backend_v2()
    if not status.available:
        pytest.skip(status.reason or "MVSEL2 native extension is not built")
    assert status.qualified, status.reason
    if parallel and (not status.openmp or status.max_threads < 2):
        pytest.skip("MVSEL2 native extension has no usable OpenMP backend")
    return status


def _row_fixture() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    lengths = (1, 7, 8, 9, 127, 128, 129, 255, 256, 257, 511, 512, 513, 1582)
    offsets = np.empty(len(lengths) + 1, dtype=np.uint64)
    offsets[0] = 0
    rows: list[np.ndarray] = []
    cursor = 0
    term_count = max(lengths) + 31
    index = np.arange(term_count, dtype=np.float64)
    terms = (
        (index + 1.0) / (term_count + 11.0)
        + np.ldexp((index % 23.0) + 1.0, -46)
    ).astype(np.float64, copy=False)
    for position, length in enumerate(lengths):
        row = np.arange(length, dtype=np.uint32)
        if position % 2:
            row = row + np.uint32(position)
        rows.append(row.astype(np.uint32, copy=False))
        cursor += length
        offsets[position + 1] = cursor
    witnesses = np.concatenate(rows).astype(np.uint32, copy=False)
    candidates = np.arange(len(lengths), dtype=np.uint32)
    return offsets, witnesses, terms, candidates


def _numpy_scores(
    offsets: np.ndarray,
    witnesses: np.ndarray,
    terms: np.ndarray,
    candidates: np.ndarray,
) -> np.ndarray:
    output = np.empty(len(candidates), dtype=np.float64)
    for position, value in enumerate(candidates):
        candidate = int(value)
        start = int(offsets[candidate])
        stop = int(offsets[candidate + 1])
        output[position] = np.sum(
            terms[witnesses[start:stop]],
            dtype=np.float64,
        )
    return output


def test_mvsel2_native_serial_row_scorer_is_bitwise_numpy_exact() -> None:
    _require_native()
    offsets, witnesses, terms, candidates = _row_fixture()
    expected = _numpy_scores(offsets, witnesses, terms, candidates)
    actual, edges = score_family_candidate_batch_v2(
        offsets,
        witnesses,
        terms,
        candidates,
        workers=1,
    )
    assert edges == int(offsets[-1])
    np.testing.assert_array_equal(actual.view(np.uint64), expected.view(np.uint64))


def test_mvsel2_native_openmp_worker_counts_are_bitwise_identical() -> None:
    status = _require_native(parallel=True)
    offsets, witnesses, terms, candidates = _row_fixture()
    expected = _numpy_scores(offsets, witnesses, terms, candidates)
    worker_counts: list[int] = []
    value = 2
    while value < status.max_threads:
        worker_counts.append(value)
        value *= 2
    if status.max_threads >= 2:
        worker_counts.append(int(status.max_threads))
    worker_counts = list(dict.fromkeys(worker_counts))
    for workers in worker_counts:
        actual, edges = score_family_candidate_batch_v2(
            offsets,
            witnesses,
            terms,
            candidates,
            workers=workers,
        )
        assert edges == int(offsets[-1])
        np.testing.assert_array_equal(actual.view(np.uint64), expected.view(np.uint64))


def test_mvsel2_native_parallel_phase_b_matches_scalar_oracle() -> None:
    _require_native(parallel=True)
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    scalar_state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )
    parallel_state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )

    for candidate in range(3):
        expected_score = selector_v2.score_target_multi_view_candidate_v2(
            candidate, forward_domain, scalar_state
        )
        actual_score = selector_v2.score_target_multi_view_candidate_v2(
            candidate, forward_domain, parallel_state
        )
        assert actual_score == expected_score
        selector_v2.select_target_multi_view_candidate_v2(
            candidate, forward_domain, scalar_state, score=expected_score
        )
        selector_v2.select_target_multi_view_candidate_v2(
            candidate, forward_domain, parallel_state, score=actual_score
        )

    scalar_frontier = build_target_multi_view_lazy_frontier_v2_kernel(
        forward_domain,
        scalar_state,
        workers=1,
    )
    parallel_frontier = build_target_multi_view_lazy_frontier_v2_kernel(
        forward_domain,
        parallel_state,
        workers=2,
    )
    np.testing.assert_array_equal(
        parallel_frontier.exact_scores.view(np.uint64),
        scalar_frontier.exact_scores.view(np.uint64),
    )
    np.testing.assert_array_equal(
        parallel_frontier.exact_generations,
        scalar_frontier.exact_generations,
    )

    for _ in range(5):
        expected = choose_target_multi_view_phase_b_candidate_v2_kernel(
            reference_domain,
            forward_domain,
            scalar_state,
            scalar_frontier,
            workers=1,
        )
        actual = choose_target_multi_view_phase_b_candidate_v2_kernel(
            reference_domain,
            forward_domain,
            parallel_state,
            parallel_frontier,
            workers=2,
            batch_size=4,
        )
        assert actual.candidate_index == expected.candidate_index
        assert actual.score == expected.score
        selector_v2.select_target_multi_view_candidate_v2(
            expected.candidate_index,
            forward_domain,
            scalar_state,
            score=expected.score,
        )
        selector_v2.select_target_multi_view_candidate_v2(
            actual.candidate_index,
            forward_domain,
            parallel_state,
            score=actual.score,
        )

    assert parallel_state.selected_order == scalar_state.selected_order
    np.testing.assert_array_equal(parallel_state.available, scalar_state.available)
    np.testing.assert_array_equal(
        parallel_state.obligation_counts,
        scalar_state.obligation_counts,
    )
    np.testing.assert_array_equal(
        parallel_state.correlation_unit_counts,
        scalar_state.correlation_unit_counts,
    )
    for actual_family, expected_family in zip(
        parallel_state.family_states,
        scalar_state.family_states,
        strict=True,
    ):
        np.testing.assert_array_equal(
            actual_family.multiplicity,
            expected_family.multiplicity,
        )
        assert actual_family.coverage_mass == expected_family.coverage_mass
    assert parallel_state.representative_utility == scalar_state.representative_utility
