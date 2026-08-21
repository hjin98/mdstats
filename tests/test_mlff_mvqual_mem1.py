from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data._sparse_vector_kernels import (
    csr_gather_rows,
    csr_row_lengths,
    iter_csr_edge_batches,
)
from mdstats.training_data.target_multi_view_qualification import (
    _qualification_provenance_codes,
    _selector_telemetry_indices,
    _selector_telemetry_reference,
)


@dataclass(frozen=True)
class _SparseFamily:
    family_id: str
    rows: tuple[tuple[int, ...], ...]

    def __post_init__(self) -> None:
        offsets = np.zeros(len(self.rows) + 1, dtype=np.uint64)
        for index, row in enumerate(self.rows, start=1):
            offsets[index] = offsets[index - 1] + len(row)
        witnesses = np.asarray(
            [witness for row in self.rows for witness in row], dtype=np.uint32
        )
        object.__setattr__(self, "candidate_offsets", offsets)
        object.__setattr__(self, "candidate_witnesses", witnesses)

    @property
    def witness_count(self) -> int:
        return 6

    def candidate_witness_indices(self, candidate_index: int) -> np.ndarray:
        return np.asarray(self.rows[candidate_index], dtype=np.uint32)


def _fixture() -> tuple[SimpleNamespace, SimpleNamespace, SimpleNamespace]:
    frame_uids = ("f0", "f1", "f2", "f3", "f4")
    family_a = _SparseFamily(
        "family-a",
        (
            (0, 1, 2),
            (1, 2, 3),
            (2, 4),
            (3, 4, 5),
            (0, 5),
        ),
    )
    family_b = _SparseFamily(
        "family-b",
        (
            (0, 3),
            (1, 4),
            (2, 3, 5),
            (0, 2, 4),
            (1, 5),
        ),
    )
    weights = {
        "family-a": np.asarray((0.07, 0.11, 0.19, 0.23, 0.17, 0.23), dtype=np.float64),
        "family-b": np.asarray((0.13, 0.17, 0.20, 0.09, 0.18, 0.23), dtype=np.float64),
    }
    reference = SimpleNamespace(
        frame_uids=frame_uids,
        family=lambda family_id: SimpleNamespace(weights=weights[family_id]),
    )
    sparse = SimpleNamespace(
        families=(family_a, family_b),
        candidate_correlation_unit_codes=np.asarray((0, 0, 1, 2, 2), dtype=np.int32),
        correlation_unit_ids=("u0", "u1", "u2"),
    )
    role = SimpleNamespace(
        development_intervals=(
            SimpleNamespace(
                frame_uids=("f0", "f1"), run_id="run-a", condition_id="cond-x", unit_id="a"
            ),
            SimpleNamespace(
                frame_uids=("f2",), run_id="run-b", condition_id="cond-x", unit_id="b"
            ),
            SimpleNamespace(
                frame_uids=("f3", "f4"), run_id="run-c", condition_id="cond-y", unit_id="c"
            ),
        )
    )
    return reference, sparse, role


def test_mvqual_mem1_current_vectorized_telemetry_matches_frozen_reference() -> None:
    reference, sparse, role = _fixture()
    selected_uids = ("f0", "f2", "f3")
    expected = _selector_telemetry_reference(reference, sparse, role, selected_uids)
    uid_to_index, run_codes, condition_codes = _qualification_provenance_codes(
        reference, role
    )
    selected = np.asarray([uid_to_index[uid] for uid in selected_uids], dtype=np.int64)

    actual = _selector_telemetry_indices(
        reference,
        sparse,
        selected,
        run_codes,
        condition_codes,
    )

    assert actual == expected


def test_mvqual_mem1_reference_locks_unique_owner_and_provenance_semantics() -> None:
    reference, sparse, role = _fixture()
    telemetry = _selector_telemetry_reference(
        reference, sparse, role, ("f0", "f2", "f3")
    )

    assert telemetry.uncovered_witness_count == 0
    assert telemetry.uncovered_reference_mass == 0.0
    assert telemetry.zero_unique_candidate_fraction == 0.0
    assert telemetry.correlation_unit_count == 3
    assert telemetry.maximum_correlation_unit_fraction == 1.0 / 3.0
    assert telemetry.run_count == 3
    assert telemetry.condition_count == 2


def test_strict_csr_edge_stream_reconstructs_canonical_gather_and_owners() -> None:
    offsets = np.asarray((0, 0, 5, 7, 17, 18), dtype=np.uint64)
    indices = np.arange(100, 118, dtype=np.uint32)
    rows = np.asarray((0, 3, 1, 4), dtype=np.int64)
    expected_indices, expected_lengths = csr_gather_rows(offsets, indices, rows)
    expected_owners = np.repeat(
        np.arange(rows.size, dtype=np.int64), expected_lengths
    )

    for edge_limit in (1, 2, 3, 4, 32):
        chunks = list(
            iter_csr_edge_batches(offsets, indices, rows, max_edges=edge_limit)
        )
        assert chunks
        assert all(0 < chunk_indices.size <= edge_limit for chunk_indices, _ in chunks)
        actual_indices = np.concatenate([chunk_indices for chunk_indices, _ in chunks])
        actual_owners = np.concatenate([owners for _, owners in chunks])
        np.testing.assert_array_equal(actual_indices, expected_indices)
        np.testing.assert_array_equal(actual_owners, expected_owners)


def test_strict_csr_edge_stream_splits_one_oversized_row_and_preserves_repeats() -> None:
    offsets = np.asarray((0, 2, 11, 11, 14), dtype=np.uint64)
    indices = np.arange(14, dtype=np.uint32)
    rows = np.asarray((1, 2, 1, 3), dtype=np.int64)
    expected_indices, expected_lengths = csr_gather_rows(offsets, indices, rows)
    expected_owners = np.repeat(
        np.arange(rows.size, dtype=np.int64), expected_lengths
    )

    chunks = list(iter_csr_edge_batches(offsets, indices, rows, max_edges=3))

    assert max(chunk_indices.size for chunk_indices, _ in chunks) == 3
    np.testing.assert_array_equal(
        np.concatenate([chunk_indices for chunk_indices, _ in chunks]), expected_indices
    )
    np.testing.assert_array_equal(
        np.concatenate([owners for _, owners in chunks]), expected_owners
    )


def test_strict_csr_edge_stream_validates_obvious_contract_errors() -> None:
    offsets = np.asarray((0, 1, 2), dtype=np.uint64)
    indices = np.asarray((3, 4), dtype=np.uint32)

    with pytest.raises(ValueError, match="positive"):
        list(iter_csr_edge_batches(offsets, indices, np.asarray((0,)), max_edges=0))
    with pytest.raises(ValueError, match="outside"):
        list(iter_csr_edge_batches(offsets, indices, np.asarray((2,)), max_edges=1))
    with pytest.raises(ValueError, match="one-dimensional"):
        list(
            iter_csr_edge_batches(
                offsets, indices, np.asarray(((0,),)), max_edges=1
            )
        )
