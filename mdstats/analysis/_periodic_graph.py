"""Private exact arithmetic for periodic quotient-graph infrastructure.

The integer image-shift convention follows the vector/quotient-graph
representation of Chung, Hahn, and Klee (1984) and Klee (2004).  This module
contains only representation-neutral arithmetic shared by multiple Stage-5
consumers; it intentionally contains no ring canonicalization or graph search.

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
W. E. Klee, Cryst. Res. Technol. 39, 959-968 (2004),
doi:10.1002/crat.200410281.
"""

from __future__ import annotations

from numbers import Integral
from typing import Any, TypeAlias

LatticeShift: TypeAlias = tuple[int, int, int]
IntMatrix3: TypeAlias = tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]


def coerce_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise ValueError(f"{name} must be an integer.")
    return int(value)


def coerce_nonnegative_int(value: Any, *, name: str) -> int:
    result = coerce_int(value, name=name)
    if result < 0:
        raise ValueError(f"{name} must be nonnegative.")
    return result


def coerce_lattice_shift(value: Any, *, name: str = "image_shift") -> LatticeShift:
    try:
        items = tuple(value)
    except TypeError as exc:
        raise ValueError(f"{name} must contain exactly three integers.") from exc
    if len(items) != 3:
        raise ValueError(f"{name} must contain exactly three integers.")
    return tuple(coerce_int(x, name=name) for x in items)  # type: ignore[return-value]


def coerce_int_matrix3(value: Any, *, name: str = "lattice_matrix") -> IntMatrix3:
    try:
        rows = tuple(tuple(row) for row in value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a 3x3 integer matrix.") from exc
    if len(rows) != 3 or any(len(row) != 3 for row in rows):
        raise ValueError(f"{name} must be a 3x3 integer matrix.")
    return tuple(
        tuple(coerce_int(x, name=name) for x in row) for row in rows
    )  # type: ignore[return-value]


def add_shift(left: LatticeShift, right: LatticeShift) -> LatticeShift:
    return tuple(a + b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def subtract_shift(left: LatticeShift, right: LatticeShift) -> LatticeShift:
    return tuple(a - b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def negate_shift(value: LatticeShift) -> LatticeShift:
    return tuple(-x for x in value)  # type: ignore[return-value]


def determinant3(matrix: IntMatrix3) -> int:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def matvec_shift(matrix: IntMatrix3, shift: LatticeShift) -> LatticeShift:
    return tuple(
        sum(row[column] * shift[column] for column in range(3))
        for row in matrix
    )  # type: ignore[return-value]


def multiply_int_matrices3(left: IntMatrix3, right: IntMatrix3) -> IntMatrix3:
    """Return the exact integer product ``left @ right``."""

    return tuple(
        tuple(
            sum(left[row][inner] * right[inner][column] for inner in range(3))
            for column in range(3)
        )
        for row in range(3)
    )  # type: ignore[return-value]


def invert_unimodular_matrix3(matrix: IntMatrix3) -> IntMatrix3:
    """Return the exact integer inverse of a 3x3 unimodular matrix."""

    determinant = determinant3(matrix)
    if determinant not in (-1, 1):
        raise ValueError(
            "matrix must be unimodular with determinant +1 or -1."
        )
    a = matrix
    cofactors = (
        (
            a[1][1] * a[2][2] - a[1][2] * a[2][1],
            -(a[1][0] * a[2][2] - a[1][2] * a[2][0]),
            a[1][0] * a[2][1] - a[1][1] * a[2][0],
        ),
        (
            -(a[0][1] * a[2][2] - a[0][2] * a[2][1]),
            a[0][0] * a[2][2] - a[0][2] * a[2][0],
            -(a[0][0] * a[2][1] - a[0][1] * a[2][0]),
        ),
        (
            a[0][1] * a[1][2] - a[0][2] * a[1][1],
            -(a[0][0] * a[1][2] - a[0][2] * a[1][0]),
            a[0][0] * a[1][1] - a[0][1] * a[1][0],
        ),
    )
    # inverse = adjugate / det = transpose(cofactor) / det
    return tuple(
        tuple(cofactors[column][row] // determinant for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def physical_edge_anchor(
    source_image_shift: LatticeShift,
    edge_image_shift: LatticeShift,
    orientation: int,
) -> LatticeShift:
    """Return canonical-endpoint anchor of one traversed periodic edge instance.

    For edge orbit ``(i,j,Delta)`` translated by ``a``, the physical edge is
    ``(i,a)->(j,a+Delta)``.  A reverse traversal starts at ``(j,a+Delta)``, so
    its canonical-endpoint anchor is ``source_image_shift-Delta``.
    """
    if orientation == 1:
        return source_image_shift
    if orientation == -1:
        return subtract_shift(source_image_shift, edge_image_shift)
    raise ValueError("orientation must be +1 or -1.")
