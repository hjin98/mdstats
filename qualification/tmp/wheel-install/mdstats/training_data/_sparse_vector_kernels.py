"""Execution-only exact sparse vector kernels for MLFF training-data stages.

The helpers in this module preserve canonical CSR row order.  They are not
scientific policy and must not enter content digests.
"""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np


def csr_row_lengths(offsets: np.ndarray, rows: np.ndarray) -> np.ndarray:
    """Return CSR row lengths for ``rows`` without materializing row slices."""
    off = np.asarray(offsets)
    r = np.asarray(rows, dtype=np.int64)
    return np.asarray(off[r + 1] - off[r], dtype=np.int64)


def csr_gather_rows(
    offsets: np.ndarray,
    indices: np.ndarray,
    rows: np.ndarray,
    *,
    lengths: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Gather complete CSR rows in the supplied row order.

    Returns ``(gathered_indices, row_lengths)``.  The gathered array is exactly
    equivalent to ``concatenate(indices[offsets[r]:offsets[r+1]] for r in rows)``
    but constructs edge positions with vectorized prefix arithmetic rather than
    one Python/NumPy slice per row.
    """
    off = np.asarray(offsets)
    idx = np.asarray(indices)
    r = np.asarray(rows, dtype=np.int64)
    if r.ndim != 1:
        raise ValueError("CSR gather rows must be one-dimensional.")
    if r.size == 0:
        return np.empty(0, dtype=idx.dtype), np.empty(0, dtype=np.int64)
    lens = csr_row_lengths(off, r) if lengths is None else np.asarray(lengths, dtype=np.int64)
    if lens.shape != r.shape or np.any(lens < 0):
        raise ValueError("CSR gather row lengths are invalid.")
    total = int(np.sum(lens, dtype=np.int64))
    if total == 0:
        return np.empty(0, dtype=idx.dtype), lens
    edge_prefix = np.empty(r.size + 1, dtype=np.int64)
    edge_prefix[0] = 0
    np.cumsum(lens, dtype=np.int64, out=edge_prefix[1:])
    starts = np.asarray(off[r], dtype=np.int64)
    bases = np.repeat(starts - edge_prefix[:-1], lens)
    positions = bases + np.arange(total, dtype=np.int64)
    return idx[positions], lens


def iter_csr_gather_batches(
    offsets: np.ndarray,
    indices: np.ndarray,
    rows: np.ndarray,
    *,
    max_edges: int,
) -> Iterator[tuple[np.ndarray, np.ndarray, slice]]:
    """Yield bounded complete-row CSR gathers in canonical row order.

    The common path emits one vectorized gather.  Oversized inputs use a small
    greedy row-boundary loop only to choose batch boundaries; edge gathering
    inside each batch remains vectorized.  A single row may exceed ``max_edges``
    and is emitted whole, matching MVPERF1 semantics.
    """
    r = np.asarray(rows, dtype=np.int64)
    if r.ndim != 1:
        raise ValueError("CSR gather rows must be one-dimensional.")
    if r.size == 0:
        return
    edge_limit = max(1, int(max_edges))
    lengths = csr_row_lengths(offsets, r)
    total = int(np.sum(lengths, dtype=np.int64))
    if total <= edge_limit:
        gathered, lens = csr_gather_rows(offsets, indices, r, lengths=lengths)
        yield gathered, lens, slice(0, r.size)
        return

    cursor = 0
    while cursor < r.size:
        stop = cursor
        edge_count = 0
        while stop < r.size:
            row_edges = int(lengths[stop])
            if stop > cursor and edge_count + row_edges > edge_limit:
                break
            edge_count += row_edges
            stop += 1
            if edge_count >= edge_limit:
                break
        gathered, lens = csr_gather_rows(
            offsets, indices, r[cursor:stop], lengths=lengths[cursor:stop]
        )
        yield gathered, lens, slice(cursor, stop)
        cursor = stop
