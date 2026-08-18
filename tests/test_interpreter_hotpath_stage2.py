"""Stage-2 regression tests for interpreter-overhead removals."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from mdstats.analysis._cell_list import (
    _minimum_metric_norm_squared_in_box,
    _minimum_metric_norm_squared_in_boxes,
)
from mdstats.analysis.bond_angle import (
    _batched_center_angles,
    _center_angles,
)
from mdstats.plotting.density_block_direct import (
    _relevant_stencil_mask,
    _relevant_stencil_matrix,
)


def _mock_neighbor_list(degrees: np.ndarray, seed: int) -> SimpleNamespace:
    rng = np.random.default_rng(seed)
    offsets = np.empty(degrees.size + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(degrees, out=offsets[1:])
    vectors = rng.normal(size=(int(offsets[-1]), 3))
    vectors /= np.linalg.norm(vectors, axis=1)[:, None]
    return SimpleNamespace(
        offsets=offsets,
        vectors=vectors,
        row_slice=lambda row: slice(int(offsets[row]), int(offsets[row + 1])),
    )


def test_batched_symmetric_angles_match_center_reference() -> None:
    degrees = np.asarray([0, 1, 4, 7, 3, 5], dtype=np.int64)
    neighbors = _mock_neighbor_list(degrees, 14)
    accepted = np.asarray([True, True, True, False, True, True])
    actual, centers = _batched_center_angles(
        neighbors, neighbors, accepted, symmetric=True, max_pair_rows=12
    )
    expected_angles: list[np.ndarray] = []
    expected_centers: list[np.ndarray] = []
    for center in np.flatnonzero(accepted):
        values = _center_angles(neighbors, neighbors, int(center), symmetric=True)
        if values.size:
            expected_angles.append(values)
            expected_centers.append(
                np.full(values.size, center, dtype=np.int64)
            )
    np.testing.assert_allclose(actual, np.concatenate(expected_angles))
    np.testing.assert_array_equal(centers, np.concatenate(expected_centers))


def test_batched_asymmetric_angles_match_center_reference() -> None:
    degrees_a = np.asarray([2, 0, 5, 3, 8], dtype=np.int64)
    degrees_c = np.asarray([4, 2, 1, 6, 3], dtype=np.int64)
    list_a = _mock_neighbor_list(degrees_a, 22)
    list_c = _mock_neighbor_list(degrees_c, 23)
    accepted = np.asarray([True, False, True, True, True])
    actual, centers = _batched_center_angles(
        list_a, list_c, accepted, symmetric=False, max_pair_rows=10
    )
    expected_angles: list[np.ndarray] = []
    expected_centers: list[np.ndarray] = []
    for center in np.flatnonzero(accepted):
        values = _center_angles(list_a, list_c, int(center), symmetric=False)
        if values.size:
            expected_angles.append(values)
            expected_centers.append(
                np.full(values.size, center, dtype=np.int64)
            )
    np.testing.assert_allclose(actual, np.concatenate(expected_angles))
    np.testing.assert_array_equal(centers, np.concatenate(expected_centers))


def test_relevant_stencil_matrix_matches_scalar_rows() -> None:
    rng = np.random.default_rng(41)
    offsets = rng.integers(-20, 21, size=(700, 3), dtype=np.int64)
    minima = rng.integers(0, 50, size=(37, 3), dtype=np.int64)
    maxima = minima + rng.integers(0, 14, size=(37, 3), dtype=np.int64)
    target_start = np.asarray((20, 24, 18), dtype=np.int64)
    target_stop = np.asarray((36, 40, 34), dtype=np.int64)
    logical = (64, 65, 66)
    actual = _relevant_stencil_matrix(
        offsets, minima, maxima, target_start, target_stop, logical
    )
    expected = np.vstack(
        [
            _relevant_stencil_mask(
                offsets,
                minima[row],
                maxima[row],
                target_start,
                target_stop,
                logical,
            )
            for row in range(minima.shape[0])
        ]
    )
    np.testing.assert_array_equal(actual, expected)


def test_batched_metric_box_minimizer_matches_scalar_reference() -> None:
    rng = np.random.default_rng(91)
    basis = rng.normal(size=(3, 3))
    metric = basis @ basis.T + np.eye(3)
    centers = rng.normal(size=(250, 3))
    half_widths = rng.uniform(0.01, 0.8, size=(250, 3))
    lower = centers - half_widths
    upper = centers + half_widths
    actual = _minimum_metric_norm_squared_in_boxes(
        metric, lower, upper, tolerance=1.0e-12
    )
    expected = np.asarray(
        [
            _minimum_metric_norm_squared_in_box(
                metric, lower[row], upper[row], tolerance=1.0e-12
            )
            for row in range(lower.shape[0])
        ]
    )
    np.testing.assert_allclose(actual, expected, rtol=2.0e-13, atol=2.0e-13)
