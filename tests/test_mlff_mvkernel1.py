from __future__ import annotations

import numpy as np

from mdstats.training_data import target_multi_view_selector as mvsel
from mdstats.training_data import target_multi_view_qualification as mvqual
from mdstats.training_data._sparse_vector_kernels import csr_gather_rows, iter_csr_gather_batches
from tests.test_mlff_target_data2c_mvqual1 import _authorities
from tests.test_mlff_target_data2c_mvsel1 import _selector


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
