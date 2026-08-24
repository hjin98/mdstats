from __future__ import annotations

from pathlib import Path

import mdstats
import numpy as np

from mdstats.training_data import target_multi_view_selector as mvsel
from mdstats.training_data._sparse_vector_kernels import csr_gather_rows, iter_csr_gather_batches
from tests._mlff_multiview_legacy_fixtures import _selector


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


def test_mvkernel1_row_weight_sums_are_exact_across_bounded_chunks(monkeypatch) -> None:
    offsets = np.asarray([0, 3, 3, 8, 10, 14], dtype=np.uint64)
    indices = np.asarray([0, 1, 2, 2, 1, 0, 3, 2, 3, 0, 1, 2, 3, 0], dtype=np.uint32)
    weights = np.asarray([1.0e12, 1.0e-9, 3.25, 7.5e-7], dtype=np.float64)
    edge_weights = weights[np.asarray(indices, dtype=np.int64)]
    expected = np.zeros(5, dtype=np.float64)
    for row in range(5):
        expected[row] = np.add.reduce(
            edge_weights[int(offsets[row]):int(offsets[row + 1])], dtype=np.float64
        )

    monkeypatch.setattr(mvsel, "_MVSEL1_MAX_INITIAL_WEIGHT_BYTES", 4 * 8)
    actual = mvsel._row_weight_sums(offsets, indices, weights)

    assert np.array_equal(actual, expected)


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


def test_mvkernel1_dense_run_pair_update_is_bit_exact_to_scatter() -> None:
    rng = np.random.default_rng(20260818)
    candidate_count = 257
    rows: list[np.ndarray] = []
    for _ in range(19):
        keep = rng.random(candidate_count) < 0.985
        rows.append(np.flatnonzero(keep).astype(np.uint32))
    offsets = np.zeros(len(rows) + 1, dtype=np.uint64)
    offsets[1:] = np.cumsum([row.size for row in rows], dtype=np.uint64)
    indices = np.concatenate(rows)
    witnesses = np.arange(len(rows), dtype=np.int64)
    amounts = rng.uniform(1.0e-9, 1.0e-3, size=len(rows)).astype(np.float64)
    left_scatter = rng.uniform(1.0, 2.0, size=candidate_count).astype(np.float64)
    right_scatter = left_scatter.copy()
    left_dense = left_scatter.copy()
    right_dense = right_scatter.copy()

    mvsel._scatter_decrement_pair_exact(
        left_scatter, right_scatter, offsets, indices, witnesses, amounts
    )
    mvsel._scatter_decrement_pair_dense_runs_exact(
        left_dense, right_dense, offsets, indices, witnesses, amounts
    )

    assert np.array_equal(left_dense, left_scatter)
    assert np.array_equal(right_dense, right_scatter)


def test_mvkernel1_selector_reports_initialization_and_first_rank() -> None:
    reference, _, _, index, policy, _ = _selector()
    messages: list[str] = []

    mvsel.build_target_multi_view_selection_plan(
        reference,
        index,
        policy=policy,
        progress_callback=messages.append,
        progress_interval_seconds=3600.0,
    )

    assert messages[0].startswith("status=initializing;")
    assert any("families=1/1 (100.0%)" in message for message in messages)
    assert any(message.startswith("status=selecting;") and "selected=0/" in message for message in messages)
    assert any(message.startswith("status=selecting;") and "selected=1/" in message for message in messages)


def test_mvkernel1_production_density_release_contract() -> None:
    assert mdstats.__version__ == "0.20.242a0"
    source = (
        Path(__file__).resolve().parents[1]
        / "docs/specs/training_data/mlff_mvkernel1_sparse_vector_kernels_spec.md"
    ).read_text(encoding="utf-8")
    for token in ("512 MiB", "98%", "touched flag", "1.11x/1.08x"):
        assert token in source


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
