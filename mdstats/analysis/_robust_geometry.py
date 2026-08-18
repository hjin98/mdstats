"""Exact rational predicates for Stage-8C piecewise-linear surfaces.

The implementation follows the robust-predicate principle of Shewchuk (1997):
all topological decisions are made from exact signs.  Because the authoritative
periodic-net embedding stores rational fractional coordinates, ``Fraction``
arithmetic supplies exact orientation, plane-side, clipping, and intersection
signs directly; no floating-point epsilon enters certification.

The triangle/triangle organization is inspired by the plane-section reduction
used in classical triangle-intersection work, including Moller (1997), but the
code below is an mdstats exact-rational implementation rather than a translation
of Moller's floating-point optimized kernel.

References
----------
J. R. Shewchuk, Discrete Comput. Geom. 18, 305-363 (1997),
doi:10.1007/PL00009321.
T. Moller, J. Graphics Tools 2(2), 25-30 (1997),
doi:10.1080/10867651.1997.10487472.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from fractions import Fraction
from typing import Iterable, Sequence, TypeAlias

RationalVector2: TypeAlias = tuple[Fraction, Fraction]
RationalVector3: TypeAlias = tuple[Fraction, Fraction, Fraction]
Triangle3: TypeAlias = tuple[RationalVector3, RationalVector3, RationalVector3]


class RobustGeometryError(ValueError):
    """Raised when an exact geometric primitive is malformed or degenerate."""


class IntersectionDimension(IntEnum):
    """Topological dimension of an exact compact intersection."""

    EMPTY = -1
    POINT = 0
    SEGMENT = 1
    AREA = 2


def _v3(value: Sequence[object], *, name: str) -> RationalVector3:
    result = tuple(Fraction(item) for item in value)
    if len(result) != 3:
        raise RobustGeometryError(f"{name} must contain three components.")
    return result  # type: ignore[return-value]


def add(left: RationalVector3, right: RationalVector3) -> RationalVector3:
    return tuple(left[i] + right[i] for i in range(3))  # type: ignore[return-value]


def subtract(left: RationalVector3, right: RationalVector3) -> RationalVector3:
    return tuple(left[i] - right[i] for i in range(3))  # type: ignore[return-value]


def scale(value: RationalVector3, factor: Fraction) -> RationalVector3:
    return tuple(component * factor for component in value)  # type: ignore[return-value]


def translate(value: RationalVector3, shift: Sequence[object]) -> RationalVector3:
    delta = _v3(shift, name="shift")
    return add(value, delta)


def dot(left: RationalVector3, right: RationalVector3) -> Fraction:
    return sum((left[i] * right[i] for i in range(3)), Fraction(0))


def cross(left: RationalVector3, right: RationalVector3) -> RationalVector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def sign(value: Fraction) -> int:
    return 1 if value > 0 else (-1 if value < 0 else 0)


def triangle_normal(triangle: Triangle3) -> RationalVector3:
    a, b, c = triangle
    normal = cross(subtract(b, a), subtract(c, a))
    if normal == (0, 0, 0):
        raise RobustGeometryError("Triangle vertices are collinear.")
    return normal


def orient3d(a: RationalVector3, b: RationalVector3, c: RationalVector3, d: RationalVector3) -> Fraction:
    """Return the exact signed tetrahedral determinant."""

    return dot(cross(subtract(b, a), subtract(c, a)), subtract(d, a))


def point_on_segment(
    point: RationalVector3,
    start: RationalVector3,
    end: RationalVector3,
) -> bool:
    direction = subtract(end, start)
    offset = subtract(point, start)
    if direction == (0, 0, 0):
        return point == start
    if cross(direction, offset) != (0, 0, 0):
        return False
    denominator = dot(direction, direction)
    parameter = dot(offset, direction) / denominator
    return Fraction(0) <= parameter <= Fraction(1)


def _projection_axis(normal: RationalVector3) -> int:
    nonzero = [axis for axis, value in enumerate(normal) if value != 0]
    if not nonzero:
        raise RobustGeometryError("A projection requires a nonzero normal.")
    return max(nonzero, key=lambda axis: abs(normal[axis]))


def _project(point: RationalVector3, drop_axis: int) -> RationalVector2:
    return tuple(point[axis] for axis in range(3) if axis != drop_axis)  # type: ignore[return-value]


def _orient2(a: RationalVector2, b: RationalVector2, c: RationalVector2) -> Fraction:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _deduplicate(points: Iterable[RationalVector3]) -> tuple[RationalVector3, ...]:
    result: list[RationalVector3] = []
    for point in points:
        if point not in result:
            result.append(point)
    return tuple(result)


def _normalize_polygon(points: Iterable[RationalVector3]) -> list[RationalVector3]:
    result: list[RationalVector3] = []
    for point in points:
        if not result or point != result[-1]:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return result


def _polygon_area2(points: Sequence[RationalVector3], drop_axis: int) -> Fraction:
    projected = [_project(point, drop_axis) for point in points]
    return sum(
        (
            projected[index][0] * projected[(index + 1) % len(projected)][1]
            - projected[index][1] * projected[(index + 1) % len(projected)][0]
            for index in range(len(projected))
        ),
        Fraction(0),
    )


def _clip_coplanar_triangle(subject: Triangle3, clip: Triangle3) -> tuple[RationalVector3, ...]:
    normal = triangle_normal(clip)
    drop_axis = _projection_axis(normal)
    clip_projected = tuple(_project(point, drop_axis) for point in clip)
    clip_orientation = sign(_orient2(*clip_projected))
    if clip_orientation == 0:  # pragma: no cover - triangle_normal guards this
        raise RobustGeometryError("Projected clip triangle is degenerate.")

    polygon = list(subject)
    for edge_index in range(3):
        clip_start = clip_projected[edge_index]
        clip_end = clip_projected[(edge_index + 1) % 3]
        if not polygon:
            break
        output: list[RationalVector3] = []
        previous = polygon[-1]
        previous_value = clip_orientation * _orient2(
            clip_start, clip_end, _project(previous, drop_axis)
        )
        previous_inside = previous_value >= 0
        for current in polygon:
            current_value = clip_orientation * _orient2(
                clip_start, clip_end, _project(current, drop_axis)
            )
            current_inside = current_value >= 0
            if current_inside != previous_inside:
                denominator = previous_value - current_value
                if denominator == 0:  # pragma: no cover - opposite side flags exclude it
                    raise RobustGeometryError("Invalid exact polygon clipping denominator.")
                parameter = previous_value / denominator
                output.append(add(previous, scale(subtract(current, previous), parameter)))
            if current_inside:
                output.append(current)
            previous = current
            previous_value = current_value
            previous_inside = current_inside
        polygon = _normalize_polygon(output)
    return tuple(_normalize_polygon(polygon))


def _triangle_plane_section(
    triangle: Triangle3,
    plane_point: RationalVector3,
    plane_normal: RationalVector3,
) -> tuple[RationalVector3, ...]:
    values = tuple(dot(plane_normal, subtract(vertex, plane_point)) for vertex in triangle)
    signs = tuple(sign(value) for value in values)
    if all(value > 0 for value in signs) or all(value < 0 for value in signs):
        return ()
    points: list[RationalVector3] = []
    for index, vertex in enumerate(triangle):
        if values[index] == 0:
            points.append(vertex)
        next_index = (index + 1) % 3
        left = values[index]
        right = values[next_index]
        if left * right < 0:
            parameter = left / (left - right)
            points.append(
                add(vertex, scale(subtract(triangle[next_index], vertex), parameter))
            )
    unique = _deduplicate(points)
    if len(unique) > 2:
        # Three points would mean the triangle is coplanar with the plane, which
        # callers exclude before using this section routine.
        raise RobustGeometryError("Triangle-plane section unexpectedly has dimension two.")
    return unique


def _point_at_axis_value(
    section: Sequence[RationalVector3], axis: int, value: Fraction
) -> RationalVector3:
    if len(section) == 1:
        if section[0][axis] != value:
            raise RobustGeometryError("Point section does not contain requested coordinate.")
        return section[0]
    first, second = section
    denominator = second[axis] - first[axis]
    if denominator == 0:
        raise RobustGeometryError("Selected section axis is constant.")
    parameter = (value - first[axis]) / denominator
    return add(first, scale(subtract(second, first), parameter))


@dataclass(frozen=True, slots=True)
class ExactTriangleIntersection:
    """Exact intersection of two nondegenerate closed triangles."""

    dimension: IntersectionDimension
    points: tuple[RationalVector3, ...] = ()
    coplanar: bool = False

    @property
    def empty(self) -> bool:
        return self.dimension is IntersectionDimension.EMPTY


def triangle_triangle_intersection(
    left: Sequence[Sequence[object]],
    right: Sequence[Sequence[object]],
) -> ExactTriangleIntersection:
    left_triangle = tuple(_v3(point, name="left triangle vertex") for point in left)
    right_triangle = tuple(_v3(point, name="right triangle vertex") for point in right)
    if len(left_triangle) != 3 or len(right_triangle) != 3:
        raise RobustGeometryError("Triangle predicates require exactly three vertices.")
    left_value: Triangle3 = left_triangle  # type: ignore[assignment]
    right_value: Triangle3 = right_triangle  # type: ignore[assignment]
    left_normal = triangle_normal(left_value)
    right_normal = triangle_normal(right_value)
    line_direction = cross(left_normal, right_normal)

    if line_direction != (0, 0, 0):
        left_section = _triangle_plane_section(left_value, right_value[0], right_normal)
        right_section = _triangle_plane_section(right_value, left_value[0], left_normal)
        if not left_section or not right_section:
            return ExactTriangleIntersection(IntersectionDimension.EMPTY)
        axis = _projection_axis(line_direction)
        left_interval = sorted(point[axis] for point in left_section)
        right_interval = sorted(point[axis] for point in right_section)
        lower = max(left_interval[0], right_interval[0])
        upper = min(left_interval[-1], right_interval[-1])
        if lower > upper:
            return ExactTriangleIntersection(IntersectionDimension.EMPTY)
        lower_point = _point_at_axis_value(
            left_section if len(left_section) == 2 else right_section, axis, lower
        )
        if lower == upper:
            return ExactTriangleIntersection(
                IntersectionDimension.POINT, (lower_point,), False
            )
        upper_point = _point_at_axis_value(
            left_section if len(left_section) == 2 else right_section, axis, upper
        )
        return ExactTriangleIntersection(
            IntersectionDimension.SEGMENT, (lower_point, upper_point), False
        )

    # Parallel planes are either disjoint or exactly coplanar.
    if dot(left_normal, subtract(right_value[0], left_value[0])) != 0:
        return ExactTriangleIntersection(IntersectionDimension.EMPTY)
    clipped = _clip_coplanar_triangle(left_value, right_value)
    if not clipped:
        return ExactTriangleIntersection(IntersectionDimension.EMPTY, (), True)
    drop_axis = _projection_axis(left_normal)
    if len(clipped) >= 3 and _polygon_area2(clipped, drop_axis) != 0:
        return ExactTriangleIntersection(IntersectionDimension.AREA, clipped, True)
    unique = _deduplicate(clipped)
    if len(unique) == 1:
        return ExactTriangleIntersection(IntersectionDimension.POINT, unique, True)
    axis = next(
        (
            candidate
            for candidate in range(3)
            if max(point[candidate] for point in unique)
            != min(point[candidate] for point in unique)
        ),
        None,
    )
    if axis is None:
        return ExactTriangleIntersection(IntersectionDimension.POINT, (unique[0],), True)
    endpoints = (
        min(unique, key=lambda point: point[axis]),
        max(unique, key=lambda point: point[axis]),
    )
    return ExactTriangleIntersection(IntersectionDimension.SEGMENT, endpoints, True)


def _point_in_triangle_coplanar(
    point: RationalVector3,
    triangle: Triangle3,
) -> tuple[bool, bool]:
    normal = triangle_normal(triangle)
    if dot(normal, subtract(point, triangle[0])) != 0:
        return False, False
    drop_axis = _projection_axis(normal)
    projected = tuple(_project(vertex, drop_axis) for vertex in triangle)
    point2 = _project(point, drop_axis)
    orientation = sign(_orient2(*projected))
    sides = tuple(
        orientation
        * _orient2(projected[index], projected[(index + 1) % 3], point2)
        for index in range(3)
    )
    inside = all(value >= 0 for value in sides)
    strict = inside and all(value > 0 for value in sides)
    return inside, strict


def _clip_coplanar_segment_to_triangle(
    start: RationalVector3,
    end: RationalVector3,
    triangle: Triangle3,
) -> tuple[Fraction, Fraction] | None:
    normal = triangle_normal(triangle)
    drop_axis = _projection_axis(normal)
    projected_triangle = tuple(_project(vertex, drop_axis) for vertex in triangle)
    orientation = sign(_orient2(*projected_triangle))
    start2 = _project(start, drop_axis)
    end2 = _project(end, drop_axis)
    lower = Fraction(0)
    upper = Fraction(1)
    for index in range(3):
        edge_start = projected_triangle[index]
        edge_end = projected_triangle[(index + 1) % 3]
        f0 = orientation * _orient2(edge_start, edge_end, start2)
        f1 = orientation * _orient2(edge_start, edge_end, end2)
        delta = f1 - f0
        if delta == 0:
            if f0 < 0:
                return None
            continue
        crossing = -f0 / delta
        if delta > 0:
            lower = max(lower, crossing)
        else:
            upper = min(upper, crossing)
        if lower > upper:
            return None
    lower = max(lower, Fraction(0))
    upper = min(upper, Fraction(1))
    return None if lower > upper else (lower, upper)


@dataclass(frozen=True, slots=True)
class ExactSegmentTriangleIntersection:
    """Exact segment/triangle intersection, including degeneracies."""

    dimension: IntersectionDimension
    segment_interval: tuple[Fraction, Fraction] | None = None
    points: tuple[RationalVector3, ...] = ()
    triangle_interior: bool = False
    transverse_sign: int = 0
    coplanar: bool = False

    @property
    def empty(self) -> bool:
        return self.dimension is IntersectionDimension.EMPTY


def segment_triangle_intersection(
    start: Sequence[object],
    end: Sequence[object],
    triangle: Sequence[Sequence[object]],
) -> ExactSegmentTriangleIntersection:
    p = _v3(start, name="segment start")
    q = _v3(end, name="segment end")
    if p == q:
        raise RobustGeometryError("Segment endpoints must be distinct.")
    triangle_values = tuple(_v3(point, name="triangle vertex") for point in triangle)
    if len(triangle_values) != 3:
        raise RobustGeometryError("Segment-triangle predicates require three vertices.")
    tri: Triangle3 = triangle_values  # type: ignore[assignment]
    normal = triangle_normal(tri)
    d0 = dot(normal, subtract(p, tri[0]))
    d1 = dot(normal, subtract(q, tri[0]))

    if d0 == 0 and d1 == 0:
        interval = _clip_coplanar_segment_to_triangle(p, q, tri)
        if interval is None:
            return ExactSegmentTriangleIntersection(IntersectionDimension.EMPTY)
        lower, upper = interval
        first = add(p, scale(subtract(q, p), lower))
        if lower == upper:
            _, strict = _point_in_triangle_coplanar(first, tri)
            return ExactSegmentTriangleIntersection(
                IntersectionDimension.POINT,
                (lower, upper),
                (first,),
                strict,
                0,
                True,
            )
        second = add(p, scale(subtract(q, p), upper))
        return ExactSegmentTriangleIntersection(
            IntersectionDimension.SEGMENT,
            (lower, upper),
            (first, second),
            False,
            0,
            True,
        )

    if d0 * d1 > 0:
        return ExactSegmentTriangleIntersection(IntersectionDimension.EMPTY)
    denominator = d0 - d1
    if denominator == 0:
        return ExactSegmentTriangleIntersection(IntersectionDimension.EMPTY)
    parameter = d0 / denominator
    if parameter < 0 or parameter > 1:
        return ExactSegmentTriangleIntersection(IntersectionDimension.EMPTY)
    point = add(p, scale(subtract(q, p), parameter))
    inside, strict = _point_in_triangle_coplanar(point, tri)
    if not inside:
        return ExactSegmentTriangleIntersection(IntersectionDimension.EMPTY)
    direction_sign = sign(dot(subtract(q, p), normal))
    transverse = direction_sign if strict and 0 < parameter < 1 and d0 * d1 < 0 else 0
    return ExactSegmentTriangleIntersection(
        IntersectionDimension.POINT,
        (parameter, parameter),
        (point,),
        strict,
        transverse,
        False,
    )


__all__ = [
    "ExactSegmentTriangleIntersection",
    "ExactTriangleIntersection",
    "IntersectionDimension",
    "RationalVector3",
    "RobustGeometryError",
    "Triangle3",
    "add",
    "cross",
    "dot",
    "orient3d",
    "point_on_segment",
    "scale",
    "segment_triangle_intersection",
    "sign",
    "subtract",
    "translate",
    "triangle_normal",
    "triangle_triangle_intersection",
]
