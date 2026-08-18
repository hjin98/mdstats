"""Microbenchmarks for the 2026-08-05 MLFF scaling audit.

Run with::

    python benchmarks/benchmark_mlff_scaling_audit_v2.py

The benchmark uses deterministic synthetic identifiers/vectors and measures
bookkeeping kernels only; it is not a MACE inference benchmark.
"""
from __future__ import annotations

import json
from collections import deque
from time import perf_counter

import numpy as np

from mdstats.training_data.selection import (
    _extend_selected_neighbor_matrix,
    _selected_neighbor_distances,
    _smallest_lexicographic_distance_indices,
)


def best_of(function, repeats: int = 3) -> float:
    result = float("inf")
    for _ in range(repeats):
        started = perf_counter()
        function()
        result = min(result, perf_counter() - started)
    return result


def pending_old(requested: tuple[str, ...], completed: tuple[str, ...]) -> tuple[str, ...]:
    # Exact omitted implementation: the set was reconstructed once per UID.
    return tuple(uid for uid in requested if uid not in set(completed))


def pending_new(requested: tuple[str, ...], completed: tuple[str, ...]) -> tuple[str, ...]:
    completed_set = set(completed)
    return tuple(uid for uid in requested if uid not in completed_set)



def queue_old(count: int) -> int:
    pending = list(range(count))
    checksum = 0
    while pending:
        checksum += pending.pop(0)
    return checksum


def queue_new(count: int) -> int:
    pending = deque(range(count))
    checksum = 0
    while pending:
        checksum += pending.popleft()
    return checksum


def full_lexicographic_prefix(distances: np.ndarray, uids: tuple[str, ...], take: int) -> np.ndarray:
    return np.lexsort((np.asarray(uids, dtype=object), distances))[:take]


def repeated_selected_neighbors(values: np.ndarray, levels: tuple[int, ...]) -> tuple[np.ndarray, ...]:
    return tuple(_selected_neighbor_distances(values[:level]) for level in levels)


def incremental_selected_neighbors(values: np.ndarray, levels: tuple[int, ...]) -> tuple[np.ndarray, ...]:
    squared = np.full((len(values), len(values)), np.inf, dtype=np.float64)
    result: list[np.ndarray] = []
    previous = 0
    for current in levels:
        _extend_selected_neighbor_matrix(values, squared, previous, current)
        result.append(
            np.empty((0,), dtype=np.float64)
            if current <= 1
            else np.sqrt(np.min(squared[:current, :current], axis=1))
        )
        previous = current
    return tuple(result)


def main() -> None:
    rows: list[dict[str, float | int | str]] = []
    for count in (500, 1_000, 2_000, 4_000, 8_000, 16_000):
        requested = tuple(f"{index:064x}" for index in range(count))
        completed = requested[: count // 2]
        old = best_of(lambda: pending_old(requested, completed), repeats=2)
        new = best_of(lambda: pending_new(requested, completed), repeats=5)
        assert pending_old(requested, completed) == pending_new(requested, completed)
        rows.append({
            "kernel": "pending_frame_uids",
            "size": count,
            "old_seconds": old,
            "new_seconds": new,
            "speedup": old / new,
        })

    for count in (1_000, 4_000, 16_000):
        old = best_of(lambda: queue_old(count), repeats=2)
        new = best_of(lambda: queue_new(count), repeats=5)
        assert queue_old(count) == queue_new(count)
        rows.append({
            "kernel": "pending_job_queue",
            "size": count,
            "old_seconds": old,
            "new_seconds": new,
            "speedup": old / new,
        })

    rng = np.random.default_rng(20260805)
    candidate_count = 36_759
    take = 512
    tied_distances = np.round(rng.random(candidate_count), 4)
    uids = tuple(f"{index:064x}" for index in rng.permutation(candidate_count))
    old_order = full_lexicographic_prefix(tied_distances, uids, take)
    new_order = _smallest_lexicographic_distance_indices(tied_distances, uids, take)
    np.testing.assert_array_equal(old_order, new_order)
    old = best_of(lambda: full_lexicographic_prefix(tied_distances, uids, take), repeats=5)
    new = best_of(lambda: _smallest_lexicographic_distance_indices(tied_distances, uids, take), repeats=5)
    rows.append({
        "kernel": "centroid_prefix_selection",
        "size": candidate_count,
        "old_seconds": old,
        "new_seconds": new,
        "speedup": old / new,
    })

    levels = (64, 128, 256, 512)
    values = rng.normal(size=(levels[-1], 24))
    old_values = repeated_selected_neighbors(values, levels)
    new_values = incremental_selected_neighbors(values, levels)
    for old_value, new_value in zip(old_values, new_values, strict=True):
        np.testing.assert_allclose(old_value, new_value, rtol=1.0e-12, atol=1.0e-12)
    old = best_of(lambda: repeated_selected_neighbors(values, levels), repeats=3)
    new = best_of(lambda: incremental_selected_neighbors(values, levels), repeats=3)
    rows.append({
        "kernel": "selection_coverage_neighbors",
        "size": levels[-1],
        "old_seconds": old,
        "new_seconds": new,
        "speedup": old / new,
    })

    print(json.dumps(rows, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
