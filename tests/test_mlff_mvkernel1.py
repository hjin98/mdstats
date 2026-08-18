from __future__ import annotations

import numpy as np

from mdstats.training_data import target_multi_view_selector as mvsel
from mdstats.training_data import target_multi_view_qualification as mvqual
from mdstats.training_data._sparse_vector_kernels import csr_gather_rows, iter_csr_gather_batches
from tests.test_mlff_target_data2c_mvqual1 import _authorities
from tests.test_mlff_target_data2c_mvsel1 import _selector


def test_mvkernel1_row_weight_sums_avoid_cross_row_prefix_cancellation() -> None:
    leading_edge_count = 1_000_000
    target_edge_count = 959
    weights = np.asarray([1.68e-4, 1.0351966873706005e-5], dtype=np.float64)
    indices = np.concatenate((
        np.zeros(leading_edge_count, dtype=np.uint32),
        np.ones(target_edge_count, dtype=np.uint32),
    ))
    offsets = np.asarray([
        0,
        leading_edge_count,
        leading_edge_count,
        leading_edge_count + target_edge_count,
        leading_edge_count + target_edge_count,
    ], dtype=np.uint64)

    row_sums = mvsel._row_weight_sums(offsets, indices, weights)

    # This fixture crosses the production guard under the historical global
    # prefix-subtraction implementation, while row-local FP64 accumulation
    # remains reversible to numerical zero under MVSEL's ordered decrements.
    edge_weights = weights[np.asarray(indices, dtype=np.int64)]
    prefix = np.empty(edge_weights.size + 1, dtype=np.float64)
    prefix[0] = 0.0
    np.cumsum(edge_weights, dtype=np.float64, out=prefix[1:])
    historical_target_sum = prefix[-1] - prefix[leading_edge_count]
    historical_residual = float(historical_target_sum)
    corrected_residual = float(row_sums[2])
    for _ in range(target_edge_count):
        historical_residual -= float(weights[1])
        corrected_residual -= float(weights[1])

    assert historical_residual < -5.0e-12
    assert abs(corrected_residual) <= 5.0e-13
    assert row_sums[1] == 0.0
    assert row_sums[3] == 0.0


def test_mvkernel1_ragged_gather_matches_canonical_python_concatenation() -> None:
    offsets = np.asarray([0, 2, 2, 5, 9, 10], dtype=np.uint64)
    indices = np.asarray([7, 8, 1, 4, 9, 2, 3, 5, 8, 6], dtype=np.uint32)
    rows = np.asarray([3, 0, 1, 4, 2], dtype=np.int64)
    gathered, lengths = csr_gather_rows(offsets, indices, rows)
    expected_parts = [indices[int(offsets[r]):int(offsets[r + 1])] for r in rows]
    expected = np.concatenate(expected_parts)
    assert np.array_equal(gathered, expected)
    assert np.array_equal(lengths, np.asarray([4, 2, 0, 1, 3], dtype=np.int64))


def test_mvkernel1_bounded_ragged_batches_preserve_complete_row_order() -> None:
    offsets = np.asarray([0, 3, 6, 9, 12], dtype=np.uint64)
    indices = np.arange(12, dtype=np.uint32)
    rows = np.asarray([0, 1, 2, 3], dtype=np.int64)
    batches = list(iter_csr_gather_batches(offsets, indices, rows, max_edges=5))
    assert [a.tolist() for a, _, _ in batches] == [
        [0, 1, 2], [3, 4, 5], [6, 7, 8], [9, 10, 11]
    ]


def test_mvkernel1_selector_state_matches_reference_after_every_rank() -> None:
    reference, _, _, index, policy, _ = _selector()
    ref_domain = reference.domain("target")
    sparse_domain = index.domain("target")
    optimized = mvsel._build_domain_state(ref_domain, sparse_domain)
    scalar = mvsel._build_domain_state(ref_domain, sparse_domain)
    for _ in range(min(24, sparse_domain.candidate_count)):
        chosen_opt, *_ = mvsel._choose_candidate(ref_domain, sparse_domain, optimized, policy)
        chosen_ref, *_ = mvsel._choose_candidate(ref_domain, sparse_domain, scalar, policy)
        assert chosen_opt == chosen_ref
        mvsel._select_and_update(chosen_opt, sparse_domain, optimized)
        mvsel._select_and_update_reference(chosen_ref, sparse_domain, scalar)
        assert mvsel._states_exactly_equal(optimized, scalar)


def test_mvkernel1_mvqual_telemetry_is_byte_equivalent_to_scalar_reference() -> None:
    reference, role, _, sparse, _, repair, _, _ = _authorities()
    ref_domain = reference.domain("target")
    sparse_domain = sparse.domain("target")
    selected_uids = repair.domain("target").rungs[-1].frame_uids
    optimized = mvqual._selector_telemetry(ref_domain, sparse_domain, role.domain("target"), selected_uids)
    scalar = mvqual._selector_telemetry_reference(ref_domain, sparse_domain, role.domain("target"), selected_uids)
    assert optimized.to_dict() == scalar.to_dict()


def test_mvkernel1_full_mvqual_plan_digest_is_repeatable() -> None:
    reference, role, feasibility, sparse, _, repair, legacy, policy = _authorities()
    first = __import__("mdstats").build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    second = __import__("mdstats").build_target_multi_view_qualification_plan(
        reference, sparse, feasibility, role, legacy, repair, policy=policy
    )
    assert first.to_dict() == second.to_dict()
