from __future__ import annotations

import time

import mdstats

from tests.test_mlff_target_data2c_mvsel1 import _selector
from tests.test_mlff_target_data2c_repair1 import _redundant_selection


def test_mvperf1_optimized_selector_is_byte_equivalent_to_reference() -> None:
    reference, _, _, index, policy, _ = _selector()
    reference_plan = mdstats.build_target_multi_view_selection_plan(
        reference, index, policy=policy, execution_mode="reference"
    )
    optimized_plan = mdstats.build_target_multi_view_selection_plan(
        reference, index, policy=policy, execution_mode="optimized"
    )
    assert optimized_plan.to_dict() == reference_plan.to_dict()
    assert optimized_plan.content_digest == reference_plan.content_digest


def test_mvperf1_optimized_repair_is_byte_equivalent_to_reference() -> None:
    reference, index, selection = _redundant_selection()
    reference_plan = mdstats.build_target_multi_view_repair_plan(
        reference, index, selection, execution_mode="reference"
    )
    optimized_plan = mdstats.build_target_multi_view_repair_plan(
        reference, index, selection, execution_mode="optimized"
    )
    assert optimized_plan.to_dict() == reference_plan.to_dict()
    assert optimized_plan.content_digest == reference_plan.content_digest


def test_mvperf1_execution_mode_is_not_scientific_policy() -> None:
    policy = mdstats.TargetMultiViewSelectorPolicy(target_sizes=(2, 4, 8, 16))
    before = policy.policy_digest
    reference, _, _, index, _, _ = _selector()
    mdstats.build_target_multi_view_selection_plan(reference, index, policy=policy, execution_mode="reference")
    mdstats.build_target_multi_view_selection_plan(reference, index, policy=policy, execution_mode="optimized")
    assert policy.policy_digest == before


def test_mvperf1_batched_state_matches_reference_after_each_selection() -> None:
    from mdstats.training_data import target_multi_view_selector as mvsel

    reference, _, _, index, policy, _ = _selector()
    ref_domain = reference.domain("target")
    sparse_domain = index.domain("target")
    optimized = mvsel._build_domain_state(ref_domain, sparse_domain)
    scalar = mvsel._build_domain_state(ref_domain, sparse_domain)
    for _ in range(12):
        chosen_opt, *_ = mvsel._choose_candidate(ref_domain, sparse_domain, optimized, policy)
        chosen_ref, *_ = mvsel._choose_candidate(ref_domain, sparse_domain, scalar, policy)
        assert chosen_opt == chosen_ref
        mvsel._select_and_update(chosen_opt, sparse_domain, optimized)
        mvsel._select_and_update_reference(chosen_ref, sparse_domain, scalar)
        assert mvsel._states_exactly_equal(optimized, scalar)


def test_mvperf1_scatter_batches_are_bounded_and_order_preserving() -> None:
    import numpy as np
    from mdstats.training_data import target_multi_view_selector as mvsel

    # Four witness rows of 3 edges each. A 5-edge budget must preserve complete
    # rows, so every batch has one row and edge order remains canonical.
    offsets = np.asarray([0, 3, 6, 9, 12], dtype=np.uint64)
    indices = np.asarray([0, 2, 4, 1, 3, 5, 0, 1, 5, 2, 3, 4], dtype=np.uint32)
    witnesses = np.asarray([0, 1, 2, 3], dtype=np.int64)
    amounts = np.asarray([1.0, 2.0, 3.0, 4.0], dtype=np.float64)
    batches = list(mvsel._iter_inverse_scatter_batches(
        offsets, indices, witnesses, amounts, max_edges=5
    ))
    assert [rows.tolist() for rows, _ in batches] == [
        [0, 2, 4], [1, 3, 5], [0, 1, 5], [2, 3, 4]
    ]
    assert [values.tolist() for _, values in batches] == [
        [1.0, 1.0, 1.0], [2.0, 2.0, 2.0],
        [3.0, 3.0, 3.0], [4.0, 4.0, 4.0],
    ]
