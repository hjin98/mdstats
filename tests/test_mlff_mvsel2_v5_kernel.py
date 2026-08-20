from __future__ import annotations

import inspect

import numpy as np

from mdstats.training_data.mvsel2_phase_a_kernel import (
    choose_target_multi_view_phase_a_candidate_v2_kernel,
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
            workers=8,  # execution compatibility only; PAR1 threads are retired
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


def test_mvsel2_v5_kernel_worker_setting_is_semantically_inert() -> None:
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
