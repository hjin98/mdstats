"""Finite boundary-vertex disk triangulations for Stage 8C.

The first face backend searches the complete family of combinatorial
triangulations of one cyclic polygon using only its boundary vertices.  This is a
finite certificate family, not a complete unknot or Steiner-surface algorithm.
Hass, Snoeyink, and Thurston (2003) show why unrestricted PL spanning disks may
require far more triangles than the boundary size suggests; bounded exhaustion
therefore yields ``UNRESOLVED`` rather than a knot theorem.

Reference
---------
J. Hass, J. Snoeyink, and W. P. Thurston, Discrete Comput. Geom. 29, 1-17
(2003), doi:10.1007/s00454-002-2707-6.
"""

from __future__ import annotations

from functools import lru_cache
from math import comb
from numbers import Integral
from typing import TypeAlias

TriangleIndex: TypeAlias = tuple[int, int, int]
BoundaryTriangulation: TypeAlias = tuple[TriangleIndex, ...]


class SurfaceMeshError(ValueError):
    """Base exception for finite PL surface-mesh construction."""


class SurfaceMeshInputError(SurfaceMeshError):
    """Raised when a polygon or triangulation declaration is malformed."""


class SurfaceMeshResourceError(SurfaceMeshError):
    """Raised before a declared triangulation-family limit is exceeded."""


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise SurfaceMeshInputError(f"{name} must be a positive integer.")
    return int(value)


def polygon_triangulation_count(boundary_size: int) -> int:
    """Return the Catalan count for a labelled convex n-gon."""

    n = _positive_int(boundary_size, name="boundary_size")
    if n < 3:
        raise SurfaceMeshInputError("A disk boundary requires at least three vertices.")
    order = n - 2
    return comb(2 * order, order) // (order + 1)


def _canonical_oriented_triangle(triangle: TriangleIndex) -> TriangleIndex:
    rotations = (
        triangle,
        (triangle[1], triangle[2], triangle[0]),
        (triangle[2], triangle[0], triangle[1]),
    )
    return min(rotations)


def _canonical_triangulation(
    triangles: tuple[TriangleIndex, ...],
) -> BoundaryTriangulation:
    return tuple(sorted(_canonical_oriented_triangle(triangle) for triangle in triangles))


def enumerate_boundary_triangulations(
    boundary_size: int,
    *,
    max_triangulations: int = 100_000,
) -> tuple[BoundaryTriangulation, ...]:
    """Enumerate every oriented boundary-vertex triangulation deterministically."""

    n = _positive_int(boundary_size, name="boundary_size")
    limit = _positive_int(max_triangulations, name="max_triangulations")
    expected = polygon_triangulation_count(n)
    if expected > limit:
        raise SurfaceMeshResourceError(
            f"Boundary size {n} has {expected} triangulations, exceeding "
            f"max_triangulations={limit}."
        )

    @lru_cache(maxsize=None)
    def triangulate(start: int, end: int) -> tuple[BoundaryTriangulation, ...]:
        if end - start < 2:
            return ((),)
        values: list[BoundaryTriangulation] = []
        for split in range(start + 1, end):
            for left in triangulate(start, split):
                for right in triangulate(split, end):
                    values.append(
                        _canonical_triangulation(
                            left + right + ((start, split, end),)
                        )
                    )
        return tuple(sorted(set(values)))

    result = triangulate(0, n - 1)
    if len(result) != expected:
        raise SurfaceMeshError(
            "Triangulation enumeration disagrees with the exact Catalan count."
        )
    for triangulation in result:
        validate_oriented_disk_triangulation(n, triangulation)
    return result


def validate_oriented_disk_triangulation(
    boundary_size: int,
    triangles: BoundaryTriangulation,
) -> None:
    """Validate one oriented simplicial disk on a fixed cyclic boundary."""

    n = _positive_int(boundary_size, name="boundary_size")
    values = tuple(tuple(int(vertex) for vertex in triangle) for triangle in triangles)
    if len(values) != n - 2:
        raise SurfaceMeshInputError(
            "A boundary-vertex n-gon disk must contain exactly n-2 triangles."
        )
    if any(
        len(triangle) != 3
        or len(set(triangle)) != 3
        or any(vertex < 0 or vertex >= n for vertex in triangle)
        for triangle in values
    ):
        raise SurfaceMeshInputError("Triangulation contains an invalid triangle index.")
    if len(set(_canonical_oriented_triangle(value) for value in values)) != len(values):
        raise SurfaceMeshInputError("Triangulation contains duplicate oriented triangles.")

    oriented: dict[tuple[int, int], list[tuple[int, int]]] = {}
    for triangle in values:
        for start, end in (
            (triangle[0], triangle[1]),
            (triangle[1], triangle[2]),
            (triangle[2], triangle[0]),
        ):
            key = (min(start, end), max(start, end))
            oriented.setdefault(key, []).append((start, end))

    boundary_edges = {
        (min(index, (index + 1) % n), max(index, (index + 1) % n)):
        (index, (index + 1) % n)
        for index in range(n)
    }
    for edge, expected_orientation in boundary_edges.items():
        occurrences = oriented.pop(edge, None)
        if occurrences != [expected_orientation]:
            raise SurfaceMeshInputError(
                "Triangulation does not induce the declared oriented polygon boundary."
            )
    for occurrences in oriented.values():
        if len(occurrences) != 2 or occurrences[0] != occurrences[1][::-1]:
            raise SurfaceMeshInputError(
                "Every internal triangulation edge must occur exactly twice with opposite orientation."
            )


__all__ = [
    "BoundaryTriangulation",
    "SurfaceMeshError",
    "SurfaceMeshInputError",
    "SurfaceMeshResourceError",
    "TriangleIndex",
    "enumerate_boundary_triangulations",
    "polygon_triangulation_count",
    "validate_oriented_disk_triangulation",
]
