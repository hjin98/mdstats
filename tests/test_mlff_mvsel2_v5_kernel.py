from __future__ import annotations

import inspect

import numpy as np

from mdstats.training_data.mvsel2_phase_a_kernel import (
    choose_target_multi_view_phase_a_candidate_v2_kernel,
)
from mdstats.training_data.mvsel2_phase_b_kernel import (
    build_target_multi_view_lazy_frontier_v2_kernel,
    choose_target_multi_view_phase_b_candidate_v2_kernel,
)
from mdstats.training_data import target_multi_view_selector_v2 as selector_v2
from tests.test_mlff_mvsel2_forward import _forward_fixture


def test_mvsel2_v5_phase_a_kernel_matches_serial_reference_across_ranks() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    reference_state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )
    kernel_state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )

    for _ in range(8):
        expected = selector_v2.choose_target_multi_view_phase_a_candidate_v2(
            reference_domain,
            forward_domain,
            reference_state,
            workers=1,
        )
        actual = choose_target_multi_view_phase_a_candidate_v2_kernel(
            reference_domain,
            forward_domain,
            kernel_state,
            workers=8,  # qualified native/OpenMP row scoring; Python PAR1 is retired
        )
        assert actual == expected

        selector_v2.select_target_multi_view_candidate_v2(
            expected.candidate_index,
            forward_domain,
            reference_state,
            score=expected.score,
        )
        selector_v2.select_target_multi_view_candidate_v2(
            actual.candidate_index,
            forward_domain,
            kernel_state,
            score=actual.score,
        )


def test_mvsel2_v5_kernel_worker_setting_preserves_scientific_choice() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )

    one = choose_target_multi_view_phase_a_candidate_v2_kernel(
        reference_domain, forward_domain, state, workers=1
    )
    many = choose_target_multi_view_phase_a_candidate_v2_kernel(
        reference_domain, forward_domain, state, workers=32
    )
    assert many == one


def test_mvsel2_v5_phase_b_cached_kernel_matches_scalar_oracle_after_mutations() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    reference_state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )
    kernel_state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )

    # Seed identical non-zero witness multiplicities before constructing the
    # Phase-B queues so the cache is tested away from the trivial all-zero state.
    for candidate in range(3):
        expected_score = selector_v2.score_target_multi_view_candidate_v2(
            candidate, forward_domain, reference_state
        )
        actual_score = selector_v2.score_target_multi_view_candidate_v2(
            candidate, forward_domain, kernel_state
        )
        assert actual_score == expected_score
        selector_v2.select_target_multi_view_candidate_v2(
            candidate, forward_domain, reference_state, score=expected_score
        )
        selector_v2.select_target_multi_view_candidate_v2(
            candidate, forward_domain, kernel_state, score=actual_score
        )

    reference_frontier = selector_v2.build_target_multi_view_lazy_frontier_v2(
        forward_domain, reference_state
    )
    kernel_frontier = build_target_multi_view_lazy_frontier_v2_kernel(
        forward_domain, kernel_state
    )
    np.testing.assert_array_equal(
        kernel_frontier.exact_generations,
        reference_frontier.exact_generations,
    )
    np.testing.assert_array_equal(
        kernel_frontier.exact_scores,
        reference_frontier.exact_scores,
    )

    for _ in range(5):
        expected = selector_v2.choose_target_multi_view_phase_b_candidate_v2(
            reference_domain,
            forward_domain,
            reference_state,
            reference_frontier,
        )
        actual = choose_target_multi_view_phase_b_candidate_v2_kernel(
            reference_domain,
            forward_domain,
            kernel_state,
            kernel_frontier,
        )
        # Batched execution may refresh additional stale bounds, so execution
        # telemetry can differ. Scientific choice and exact score may not.
        assert actual.candidate_index == expected.candidate_index
        assert actual.score == expected.score

        selector_v2.select_target_multi_view_candidate_v2(
            expected.candidate_index,
            forward_domain,
            reference_state,
            score=expected.score,
        )
        selector_v2.select_target_multi_view_candidate_v2(
            actual.candidate_index,
            forward_domain,
            kernel_state,
            score=actual.score,
        )

    assert kernel_state.selected_order == reference_state.selected_order
    np.testing.assert_array_equal(kernel_state.available, reference_state.available)
    np.testing.assert_array_equal(
        kernel_state.obligation_counts, reference_state.obligation_counts
    )
    np.testing.assert_array_equal(
        kernel_state.correlation_unit_counts,
        reference_state.correlation_unit_counts,
    )
    for actual_family, expected_family in zip(
        kernel_state.family_states,
        reference_state.family_states,
        strict=True,
    ):
        np.testing.assert_array_equal(
            actual_family.multiplicity,
            expected_family.multiplicity,
        )
        assert actual_family.coverage_mass == expected_family.coverage_mass
    assert kernel_state.representative_utility == reference_state.representative_utility


def test_mvsel2_v5_scalar_reference_worker_setting_is_semantically_inert() -> None:
    reference, _, forward = _forward_fixture()
    reference_domain = reference.domain("target")
    forward_domain = forward.domain("target")
    state = selector_v2.build_target_multi_view_forward_state_v2(
        reference_domain, forward_domain
    )

    one = selector_v2.choose_target_multi_view_phase_a_candidate_v2(
        reference_domain, forward_domain, state, workers=1, batch_size=1
    )
    many = selector_v2.choose_target_multi_view_phase_a_candidate_v2(
        reference_domain, forward_domain, state, workers=32, batch_size=4096
    )
    assert many == one


def test_mvsel2_v5_native_row_preserves_authenticated_integer_storage() -> None:
    persisted = np.asarray([1, 3, 7], dtype=np.uint32)
    row = selector_v2._native_row_v2(persisted)

    assert row is persisted
    assert row.dtype == np.dtype(np.uint32)
    assert np.shares_memory(row, persisted)


def test_mvsel2_v5_scalar_reference_contains_no_candidate_thread_executor() -> None:
    source = inspect.getsource(selector_v2)
    assert "ThreadPoolExecutor" not in source
    assert "executor.map" not in source
    assert "mdstats-mvsel2" not in source
