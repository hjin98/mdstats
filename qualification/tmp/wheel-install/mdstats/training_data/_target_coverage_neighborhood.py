"""Execution-only exact neighborhood row compression for TARGET-DATA2B/C.

The scientific coverage relation is witness-row -> unique candidate frame.  A
cKDTree query returns geometric neighbor *rows*, and several rows can belong to
the same candidate frame.  This helper converts one bounded query block into a
canonical row-major unique candidate representation without a Python loop over
witnesses.
"""

from __future__ import annotations

from typing import Any, Sequence

import numpy as np

from ._common import TrainingDataInputError


def compress_unique_candidate_block(
    raw_neighbors: Sequence[Any],
    *,
    frame_indices: np.ndarray,
    row_start: int,
    candidate_count: int,
    context: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return canonical local-row/candidate pairs and per-row unique counts.

    Pairs are sorted first by local witness row and then by candidate frame.
    This is exactly the order produced by the historical per-row ``np.unique``
    reduction, so downstream FP64 ``np.add.at`` accumulation preserves the
    historical row/candidate arithmetic order while eliminating the Python
    witness loop.
    """

    block_rows = len(raw_neighbors)
    if block_rows == 0:
        empty = np.empty(0, dtype=np.int64)
        return empty, empty, empty
    if candidate_count <= 0:
        raise TrainingDataInputError(f"{context} candidate_count must be positive.")

    raw_counts = np.fromiter(
        (len(neighbors) for neighbors in raw_neighbors),
        dtype=np.int64,
        count=block_rows,
    )
    total_raw = int(np.sum(raw_counts, dtype=np.int64))
    if total_raw <= 0:
        raise TrainingDataInputError(f"{context} neighborhood block contains an unsupported witness.")

    flat_neighbor_rows = np.concatenate(raw_neighbors).astype(np.int64, copy=False)
    if flat_neighbor_rows.size != total_raw:
        raise TrainingDataInputError(f"{context} neighborhood block cardinality is inconsistent.")
    if np.any(flat_neighbor_rows < 0) or np.any(flat_neighbor_rows >= len(frame_indices)):
        raise TrainingDataInputError(f"{context} neighborhood query returned an out-of-domain row.")

    local_rows = np.repeat(np.arange(block_rows, dtype=np.int64), raw_counts)
    candidate_frames = frame_indices[flat_neighbor_rows]

    # Packing (local_row, candidate_frame) into one int64 key makes NumPy's
    # compiled unique reduction both deduplicate frame ownership and establish
    # the required row-major/candidate-major canonical order.
    max_key = (block_rows - 1) * int(candidate_count) + (int(candidate_count) - 1)
    if max_key > int(np.iinfo(np.int64).max):
        raise TrainingDataInputError(f"{context} neighborhood key range exceeds int64 capacity.")
    keys = local_rows * np.int64(candidate_count) + candidate_frames
    unique_keys = np.unique(keys)
    unique_rows = unique_keys // np.int64(candidate_count)
    unique_candidates = unique_keys % np.int64(candidate_count)
    unique_counts = np.bincount(unique_rows, minlength=block_rows).astype(np.int64, copy=False)

    own_frames = frame_indices[row_start : row_start + block_rows]
    own_keys = np.arange(block_rows, dtype=np.int64) * np.int64(candidate_count) + own_frames
    positions = np.searchsorted(unique_keys, own_keys)
    valid_positions = positions < unique_keys.size
    if not np.all(valid_positions):
        bad = int(np.flatnonzero(~valid_positions)[0])
        raise TrainingDataInputError(f"{context} self-consistency failed for witness {row_start + bad}.")
    if not np.all(unique_keys[positions] == own_keys):
        bad = int(np.flatnonzero(unique_keys[positions] != own_keys)[0])
        raise TrainingDataInputError(f"{context} self-consistency failed for witness {row_start + bad}.")

    return unique_rows, unique_candidates, unique_counts
