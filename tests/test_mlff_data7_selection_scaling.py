from __future__ import annotations

from pathlib import Path

import numpy as np

from mdstats.training_data.selection import _fps_order


def _legacy_fps_prefix(
    frame_uids: tuple[str, ...],
    vector_by_uid: dict[str, np.ndarray],
    initial: tuple[str, ...],
    tolerance: float,
    limit: int,
) -> list[str]:
    """Exact prefix of the former repeated all-selected-distance algorithm."""

    remaining = set(frame_uids) - set(initial)
    selected = list(initial)
    result: list[str] = []
    if not selected and remaining and len(result) < limit:
        centroid = np.mean([vector_by_uid[uid] for uid in remaining], axis=0)
        scores = {
            uid: float(np.linalg.norm(vector_by_uid[uid] - centroid))
            for uid in remaining
        }
        best_score = max(scores.values())
        first = min(
            uid for uid, score in scores.items()
            if abs(score - best_score) <= tolerance
        )
        selected.append(first)
        remaining.remove(first)
        result.append(first)
    while remaining and len(result) < limit:
        scores = {
            uid: min(
                float(np.linalg.norm(vector_by_uid[uid] - vector_by_uid[other]))
                for other in selected
            )
            for uid in remaining
        }
        best_score = max(scores.values())
        best = min(
            uid for uid, score in scores.items()
            if abs(score - best_score) <= tolerance
        )
        result.append(best)
        selected.append(best)
        remaining.remove(best)
    return result


def test_incremental_bounded_fps_matches_legacy_exact_prefix() -> None:
    rng = np.random.default_rng(20260805)
    uids = tuple(f"{index:064x}" for index in range(48))
    vectors = {uid: rng.normal(size=9) for uid in uids}
    initial = (uids[2], uids[17], uids[31])
    expected = _legacy_fps_prefix(uids, vectors, initial, 1.0e-12, 18)
    observed = _fps_order(uids, vectors, initial, 1.0e-12, limit=18)
    assert observed == expected


def test_incremental_fps_never_builds_more_than_requested_ladder() -> None:
    rng = np.random.default_rng(7)
    uids = tuple(f"{index:064x}" for index in range(200))
    vectors = {uid: rng.normal(size=12) for uid in uids}
    observed = _fps_order(uids, vectors, (), 1.0e-12, limit=23)
    assert len(observed) == 23
    assert len(set(observed)) == 23


def test_mace_summary_cache_reads_each_descriptor_once_per_species_signature(monkeypatch) -> None:
    from types import SimpleNamespace

    from mdstats.training_data import feature_metric

    calls: list[str] = []
    descriptor = np.asarray(
        [[1.0, 2.0], [3.0, 6.0], [5.0, 10.0]], dtype=np.float64
    )

    def fake_read(_manifest, _root, frame_uid):
        calls.append(frame_uid)
        return descriptor

    monkeypatch.setattr(feature_metric, "read_mace_descriptor_array", fake_read)
    uid = "a" * 64
    frame_data = SimpleNamespace(atomic_numbers=np.asarray([8, 14, 8], dtype=np.int32))
    frame_index = {uid: (None, frame_data, 0)}
    data6 = SimpleNamespace(mace_descriptor_manifest=object())
    cache: dict[tuple[str, tuple[int, ...]], tuple[np.ndarray, np.ndarray]] = {}

    first = feature_metric._mace_summary(
        uid,
        data6_bundle=data6,
        descriptor_root=Path("unused"),
        frame_index=frame_index,
        species_atomic_numbers=(8, 14),
        summary_cache=cache,
    )
    second = feature_metric._mace_summary(
        uid,
        data6_bundle=data6,
        descriptor_root=Path("unused"),
        frame_index=frame_index,
        species_atomic_numbers=(8, 14),
        summary_cache=cache,
    )

    assert calls == [uid]
    assert first[0] == second[0]
    np.testing.assert_array_equal(first[1], second[1])
    np.testing.assert_array_equal(first[2], second[2])


def test_incremental_selected_neighbor_matrix_matches_dense_rebuilds() -> None:
    from mdstats.training_data.selection import (
        _extend_selected_neighbor_matrix,
        _selected_neighbor_distances,
    )

    rng = np.random.default_rng(2026080502)
    values = rng.normal(size=(37, 11))
    squared = np.full((len(values), len(values)), np.inf, dtype=np.float64)
    previous = 0
    for current in (1, 4, 9, 18, 37):
        _extend_selected_neighbor_matrix(values, squared, previous, current)
        observed = (
            np.empty((0,), dtype=np.float64)
            if current <= 1
            else np.sqrt(np.min(squared[:current, :current], axis=1))
        )
        expected = _selected_neighbor_distances(values[:current])
        np.testing.assert_allclose(observed, expected, rtol=1.0e-12, atol=1.0e-12)
        previous = current


def test_partial_centroid_order_matches_full_lexsort_with_boundary_ties() -> None:
    from mdstats.training_data.selection import _smallest_lexicographic_distance_indices

    rng = np.random.default_rng(2026080503)
    squared = rng.integers(0, 17, size=10_000).astype(np.float64)
    uids = tuple(f"{index:064x}" for index in range(len(squared) - 1, -1, -1))
    for take in (1, 7, 64, 511, 4_096, len(squared)):
        expected = np.lexsort((np.asarray(uids, dtype=str), squared))[:take]
        observed = _smallest_lexicographic_distance_indices(squared, uids, take)
        np.testing.assert_array_equal(observed, expected)
