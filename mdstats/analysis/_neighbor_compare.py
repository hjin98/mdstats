"""Canonical comparison utilities for neighbor-backend verification.

The optimized neighbor backends introduced after stage S0 are allowed to discover
candidate pairs in a different internal order.  This module converts any valid
:class:`NeighborListResult` to a canonical CSR ordering and compares scientific
content with explicit diagnostics.

The helpers are private implementation/testing infrastructure.  Scientific
analysis modules should consume :class:`NeighborListResult` directly and should
not depend on this module.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._neighbors import NeighborListResult


@dataclass(frozen=True, slots=True)
class NeighborComparisonOptions:
    """Numerical and metadata policy for neighbor-result comparison."""

    vector_rtol: float = 1.0e-12
    vector_atol: float = 1.0e-12
    distance_rtol: float = 1.0e-12
    distance_atol: float = 1.0e-12
    cutoff_rtol: float = 0.0
    cutoff_atol: float = 1.0e-14
    compare_frame_index: bool = True
    compare_backend: bool = False
    canonicalize: bool = True

    def __post_init__(self) -> None:
        for name in (
            "vector_rtol",
            "vector_atol",
            "distance_rtol",
            "distance_atol",
            "cutoff_rtol",
            "cutoff_atol",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise ValueError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True)
class NeighborComparisonReport:
    """Structured outcome of comparing two neighbor results."""

    equal: bool
    messages: tuple[str, ...]
    max_vector_abs_error: float | None
    max_distance_abs_error: float | None

    def require_equal(self) -> None:
        """Raise ``AssertionError`` with the complete mismatch report."""
        if self.equal:
            return
        details = "\n".join(f"- {message}" for message in self.messages)
        raise AssertionError(f"Neighbor results differ:\n{details}")


def canonicalize_neighbor_result(result: NeighborListResult) -> NeighborListResult:
    """Return a canonically row-sorted copy of ``result``.

    Centers are ordered by canonical atom index.  Entries inside each center row
    are ordered lexicographically by neighbor atom index and periodic image
    shift.  Vectors and distances move with their pair records.  This operation
    changes only representation order, never scientific content.
    """
    if np.unique(result.center_indices).size != result.center_indices.size:
        raise ValueError("center_indices must be unique for canonicalization.")

    center_order = np.argsort(result.center_indices, kind="stable")
    canonical_centers = result.center_indices[center_order]
    row_neighbors: list[np.ndarray] = []
    row_vectors: list[np.ndarray] = []
    row_distances: list[np.ndarray] = []
    row_shifts: list[np.ndarray] = []
    row_counts = np.zeros(result.n_centers, dtype=np.int64)

    for canonical_row, source_row in enumerate(center_order):
        source_slice = result.row_slice(int(source_row))
        neighbors = result.neighbor_indices[source_slice]
        vectors = result.vectors[source_slice]
        distances = result.distances[source_slice]
        shifts = result.image_shifts[source_slice]
        if neighbors.size:
            order = np.lexsort(
                (
                    shifts[:, 2],
                    shifts[:, 1],
                    shifts[:, 0],
                    neighbors,
                )
            )
            neighbors = neighbors[order]
            vectors = vectors[order]
            distances = distances[order]
            shifts = shifts[order]
        row_counts[canonical_row] = neighbors.size
        if neighbors.size:
            row_neighbors.append(neighbors)
            row_vectors.append(vectors)
            row_distances.append(distances)
            row_shifts.append(shifts)

    offsets = np.empty(result.n_centers + 1, dtype=np.int64)
    offsets[0] = 0
    np.cumsum(row_counts, out=offsets[1:])
    neighbors = (
        np.concatenate(row_neighbors) if row_neighbors else np.empty(0, dtype=np.int64)
    )
    vectors = (
        np.concatenate(row_vectors, axis=0)
        if row_vectors
        else np.empty((0, 3), dtype=float)
    )
    distances = (
        np.concatenate(row_distances) if row_distances else np.empty(0, dtype=float)
    )
    shifts = (
        np.concatenate(row_shifts, axis=0)
        if row_shifts
        else np.empty((0, 3), dtype=np.int64)
    )
    return NeighborListResult(
        frame_index=result.frame_index,
        center_indices=canonical_centers,
        neighbor_indices=neighbors,
        offsets=offsets,
        vectors=vectors,
        distances=distances,
        image_shifts=shifts,
        cutoff=result.cutoff,
        pair_counting=result.pair_counting,
        backend=result.backend,
    )


def compare_neighbor_results(
    actual: NeighborListResult,
    expected: NeighborListResult,
    *,
    options: NeighborComparisonOptions | None = None,
) -> NeighborComparisonReport:
    """Compare two neighbor results after optional canonical ordering."""
    policy = NeighborComparisonOptions() if options is None else options
    left = canonicalize_neighbor_result(actual) if policy.canonicalize else actual
    right = canonicalize_neighbor_result(expected) if policy.canonicalize else expected
    messages: list[str] = []

    if policy.compare_frame_index and left.frame_index != right.frame_index:
        messages.append(
            f"frame_index differs: actual={left.frame_index}, "
            f"expected={right.frame_index}."
        )
    if left.pair_counting is not right.pair_counting:
        messages.append(
            "pair_counting differs: "
            f"actual={left.pair_counting.value}, expected={right.pair_counting.value}."
        )
    if policy.compare_backend and left.backend is not right.backend:
        messages.append(
            f"backend differs: actual={left.backend.value}, "
            f"expected={right.backend.value}."
        )
    if not np.isclose(
        left.cutoff,
        right.cutoff,
        rtol=policy.cutoff_rtol,
        atol=policy.cutoff_atol,
    ):
        messages.append(
            f"cutoff differs: actual={left.cutoff:.17g}, expected={right.cutoff:.17g}."
        )

    _compare_exact_array(
        "center_indices", left.center_indices, right.center_indices, messages
    )
    _compare_exact_array("offsets", left.offsets, right.offsets, messages)
    _compare_exact_array(
        "neighbor_indices", left.neighbor_indices, right.neighbor_indices, messages
    )
    _compare_exact_array(
        "image_shifts", left.image_shifts, right.image_shifts, messages
    )

    max_vector_error = _compare_float_array(
        "vectors",
        left.vectors,
        right.vectors,
        rtol=policy.vector_rtol,
        atol=policy.vector_atol,
        messages=messages,
    )
    max_distance_error = _compare_float_array(
        "distances",
        left.distances,
        right.distances,
        rtol=policy.distance_rtol,
        atol=policy.distance_atol,
        messages=messages,
    )
    return NeighborComparisonReport(
        equal=not messages,
        messages=tuple(messages),
        max_vector_abs_error=max_vector_error,
        max_distance_abs_error=max_distance_error,
    )


def assert_neighbor_results_equal(
    actual: NeighborListResult,
    expected: NeighborListResult,
    *,
    options: NeighborComparisonOptions | None = None,
) -> None:
    """Assert exact pair identity and tolerance-bounded geometry equality."""
    compare_neighbor_results(actual, expected, options=options).require_equal()


def _compare_exact_array(
    name: str,
    actual: np.ndarray,
    expected: np.ndarray,
    messages: list[str],
) -> None:
    if actual.shape != expected.shape:
        messages.append(
            f"{name} shape differs: actual={actual.shape}, expected={expected.shape}."
        )
        return
    if np.array_equal(actual, expected):
        return
    mismatch = np.argwhere(actual != expected)
    first = tuple(int(value) for value in mismatch[0])
    messages.append(
        f"{name} differs at index {first}: actual={actual[first]!r}, "
        f"expected={expected[first]!r}."
    )


def _compare_float_array(
    name: str,
    actual: np.ndarray,
    expected: np.ndarray,
    *,
    rtol: float,
    atol: float,
    messages: list[str],
) -> float | None:
    if actual.shape != expected.shape:
        messages.append(
            f"{name} shape differs: actual={actual.shape}, expected={expected.shape}."
        )
        return None
    if actual.size == 0:
        return 0.0
    absolute_error = np.abs(actual - expected)
    max_error = float(np.max(absolute_error))
    close = np.isclose(actual, expected, rtol=rtol, atol=atol)
    if np.all(close):
        return max_error
    first = tuple(int(value) for value in np.argwhere(~close)[0])
    messages.append(
        f"{name} differs at index {first}: actual={actual[first]:.17g}, "
        f"expected={expected[first]:.17g}, absolute_error={absolute_error[first]:.3g}."
    )
    return max_error
