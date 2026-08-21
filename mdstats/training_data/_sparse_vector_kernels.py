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


def iter_csr_edge_batches(
    offsets: np.ndarray,
    indices: np.ndarray,
    rows: np.ndarray,
    *,
    max_edges: int,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """Yield strictly edge-bounded CSR chunks in canonical selected-row order.

    Each result is ``(gathered_indices, owner_positions)``.  ``owner_positions``
    contains positions into the supplied ``rows`` array, not CSR row numbers.
    This makes ownership exact even when callers intentionally repeat a row.

    Unlike :func:`iter_csr_gather_batches`, this primitive may split inside a
    CSR row.  Every nonempty emitted chunk therefore satisfies
    ``len(gathered_indices) <= max_edges`` even for a single pathological row.
    Only one chunk-sized position/owner scratch pair is live at a time; no
    full-selected-edge owner array is constructed.
    """
    off = np.asarray(offsets)
    idx = np.asarray(indices)
    r = np.asarray(rows, dtype=np.int64)
    if off.ndim != 1 or off.size < 1:
        raise ValueError("CSR offsets must be a nonempty one-dimensional array.")
    if idx.ndim != 1:
        raise ValueError("CSR indices must be one-dimensional.")
    if r.ndim != 1:
        raise ValueError("CSR gather rows must be one-dimensional.")
    edge_limit = int(max_edges)
    if edge_limit < 1:
        raise ValueError("CSR strict edge limit must be positive.")
    row_count = off.size - 1
    if r.size and (np.any(r < 0) or np.any(r >= row_count)):
        raise ValueError("CSR gather row is outside the offsets domain.")
    if np.any(off[1:] < off[:-1]):
        raise ValueError("CSR offsets must be nondecreasing.")
    if int(off[-1]) > idx.size:
        raise ValueError("CSR offsets exceed the indices array.")
    if r.size == 0:
        return

    positions = np.empty(edge_limit, dtype=np.int64)
    owners = np.empty(edge_limit, dtype=np.int64)
    filled = 0

    for owner_position, row in enumerate(r):
        edge_cursor = int(off[int(row)])
        edge_stop = int(off[int(row) + 1])
        while edge_cursor < edge_stop:
            room = edge_limit - filled
            take = min(room, edge_stop - edge_cursor)
            segment = slice(filled, filled + take)
            positions[segment] = np.arange(edge_cursor, edge_cursor + take, dtype=np.int64)
            owners[segment] = owner_position
            filled += take
            edge_cursor += take
            if filled == edge_limit:
                yield idx[positions], owners.copy()
                filled = 0

    if filled:
        yield idx[positions[:filled]], owners[:filled].copy()
