"""Stage-11A reference geometry for certified periodic natural tilings.

This module realizes the scientific 3-cells and 2-cell interfaces of a
:class:`~mdstats.analysis.periodic_cell_complex.PeriodicCellComplex` in the
source-bound exact periodic-net embedding.  It does not alter tile identity,
face incidence, or properness.  Auxiliary triangulations remain construction
evidence and are not part of the geometric identity.

The exact volume and centroid formulas are direct affine polyhedral identities.
Translation-labelled adjacency follows the periodic quotient convention already
used by :mod:`mdstats.analysis.periodic_cell_complex`.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import itertools
import json
import math
from numbers import Integral
from typing import Any, Mapping, Sequence

import numpy as np

from ._periodic_graph import LatticeShift, add_shift, coerce_lattice_shift, subtract_shift
from .face_candidates import FacePlacement
from .periodic_cell_complex import PeriodicCellComplex, TranslatedCellTerm
from .periodic_net_embedding import PeriodicNetEmbedding
from .primitive_ring_index import PrimitiveRingIndex

CANONICAL_TILING_GEOMETRY_SCHEMA = "mdstats.tiling-geometry.v1"
TILING_GEOMETRY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)
RationalPoint = tuple[Fraction, Fraction, Fraction]


class TilingGeometryError(ValueError):
    """Base exception for Stage-11A tile geometry."""


class TilingGeometryInputError(TilingGeometryError):
    """Raised when sources or options violate the Stage-11A contract."""


class TilingGeometryInvariantError(TilingGeometryError):
    """Raised when a supplied scientific tile cannot be realized convexly."""


class TilingGeometryResourceError(TilingGeometryError):
    """Raised transactionally before declared finite work limits are exceeded."""


class TilingGeometrySerializationError(TilingGeometryError):
    """Raised when deterministic source replay disagrees with stored data."""


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise TilingGeometryInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise TilingGeometryInputError(f"{name} must be a positive integer.")
    return int(value)


def _finite(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise TilingGeometryInputError(f"{name} must be finite.")
    return result


def _point(value: Sequence[object], *, name: str) -> RationalPoint:
    result = tuple(Fraction(component) for component in value)
    if len(result) != 3:
        raise TilingGeometryInputError(f"{name} must contain three components.")
    return result  # type: ignore[return-value]


def _point_payload(point: RationalPoint) -> list[list[int]]:
    return [[value.numerator, value.denominator] for value in point]


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _add(left: RationalPoint, right: RationalPoint) -> RationalPoint:
    return tuple(left[i] + right[i] for i in range(3))  # type: ignore[return-value]


def _sub(left: RationalPoint, right: RationalPoint) -> RationalPoint:
    return tuple(left[i] - right[i] for i in range(3))  # type: ignore[return-value]


def _scale(value: RationalPoint, factor: Fraction) -> RationalPoint:
    return tuple(component * factor for component in value)  # type: ignore[return-value]


def _average(points: Sequence[RationalPoint]) -> RationalPoint:
    if not points:
        raise TilingGeometryInvariantError("Cannot average an empty point set.")
    return tuple(
        sum((point[axis] for point in points), Fraction(0)) / len(points)
        for axis in range(3)
    )  # type: ignore[return-value]


def _cross(left: RationalPoint, right: RationalPoint) -> RationalPoint:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _dot(left: RationalPoint, right: RationalPoint) -> Fraction:
    return sum((left[i] * right[i] for i in range(3)), Fraction(0))


def _det(left: RationalPoint, middle: RationalPoint, right: RationalPoint) -> Fraction:
    return _dot(left, _cross(middle, right))


def _cartesian(point: RationalPoint, cell: np.ndarray) -> np.ndarray:
    return np.asarray([float(value) for value in point], dtype=np.float64) @ cell


def _polygon_normal(points: Sequence[RationalPoint]) -> RationalPoint:
    if len(points) < 3:
        raise TilingGeometryInvariantError("A scientific face requires at least three vertices.")
    origin = points[0]
    for i in range(1, len(points) - 1):
        normal = _cross(_sub(points[i], origin), _sub(points[i + 1], origin))
        if normal != ZERO_SHIFT:
            if any(_dot(normal, _sub(point, origin)) != 0 for point in points):
                raise TilingGeometryInvariantError("Scientific face vertices are not exactly planar.")
            return normal
    raise TilingGeometryInvariantError("Scientific face polygon is degenerate.")


def _strictly_convex_polygon(points: Sequence[RationalPoint], normal: RationalPoint) -> bool:
    signs: list[int] = []
    for i in range(len(points)):
        first = _sub(points[(i + 1) % len(points)], points[i])
        second = _sub(points[(i + 2) % len(points)], points[(i + 1) % len(points)])
        turn = _dot(normal, _cross(first, second))
        if turn == 0:
            return False
        signs.append(1 if turn > 0 else -1)
    return len(set(signs)) == 1


def _point_segment_distance(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    direction = end - start
    denominator = float(np.dot(direction, direction))
    if denominator == 0.0:
        return float(np.linalg.norm(point - start))
    parameter = float(np.dot(point - start, direction) / denominator)
    parameter = min(1.0, max(0.0, parameter))
    return float(np.linalg.norm(point - (start + parameter * direction)))


def _ring_vertices(
    face: FacePlacement,
    ring_index: PrimitiveRingIndex,
    embedding: PeriodicNetEmbedding,
    extra_shift: LatticeShift = ZERO_SHIFT,
) -> tuple[RationalPoint, ...]:
    ring = ring_index.ring_for_key(face.ring_placement.ring_key)
    base_shift = add_shift(face.ring_placement.image_shift, extra_shift)
    points = tuple(
        embedding.fractional_coordinate(
            ref.atom_index,
            add_shift(ref.image_shift, base_shift),
        )
        for ref in ring.vertex_walk
    )
    if face.orientation == -1:
        points = tuple(reversed(points))
    return points


@dataclass(frozen=True, slots=True)
class TilingGeometryResources:
    max_tiles: int = 4096
    max_faces: int = 16384
    max_vertices_per_face: int = 128
    max_pair_distance_tests: int = 5_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, order=True, slots=True)
class TileSideRef:
    tile_index: int
    face_index: int
    face_image_shift: LatticeShift
    incidence_orientation: int

    def __post_init__(self) -> None:
        if isinstance(self.tile_index, bool) or int(self.tile_index) < 0:
            raise TilingGeometryInputError("tile_index must be nonnegative.")
        if isinstance(self.face_index, bool) or int(self.face_index) < 0:
            raise TilingGeometryInputError("face_index must be nonnegative.")
        try:
            shift = coerce_lattice_shift(self.face_image_shift, name="face_image_shift")
        except ValueError as exc:
            raise TilingGeometryInputError(str(exc)) from exc
        if self.incidence_orientation not in (-1, 1):
            raise TilingGeometryInputError("incidence_orientation must be +/-1.")
        object.__setattr__(self, "tile_index", int(self.tile_index))
        object.__setattr__(self, "face_index", int(self.face_index))
        object.__setattr__(self, "face_image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "face_index": self.face_index,
            "face_image_shift": list(self.face_image_shift),
            "incidence_orientation": self.incidence_orientation,
        }


@dataclass(frozen=True, slots=True)
class TileFaceGeometry:
    side_index: int
    side: TileSideRef
    ring_size: int
    fractional_vertices: tuple[RationalPoint, ...]
    fractional_center: RationalPoint
    cartesian_center: tuple[float, float, float]
    outward_unit_normal: tuple[float, float, float]
    area: float
    perimeter: float
    aperture_witness_radius: float

    def __post_init__(self) -> None:
        if isinstance(self.side_index, bool) or int(self.side_index) < 0:
            raise TilingGeometryInputError("side_index must be nonnegative.")
        if not isinstance(self.side, TileSideRef):
            raise TilingGeometryInputError("side must be a TileSideRef.")
        object.__setattr__(self, "side_index", int(self.side_index))
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        vertices = tuple(_point(value, name="fractional_vertex") for value in self.fractional_vertices)
        if len(vertices) != self.ring_size:
            raise TilingGeometryInputError("fractional_vertices must match ring_size.")
        object.__setattr__(self, "fractional_vertices", vertices)
        object.__setattr__(self, "fractional_center", _point(self.fractional_center, name="fractional_center"))
        for name in ("area", "perimeter", "aperture_witness_radius"):
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise TilingGeometryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        for name in ("cartesian_center", "outward_unit_normal"):
            values = tuple(_finite(value, name=name) for value in getattr(self, name))
            if len(values) != 3:
                raise TilingGeometryInputError(f"{name} must contain three values.")
            object.__setattr__(self, name, values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "side_index": self.side_index,
            "side": self.side.to_dict(),
            "ring_size": self.ring_size,
            "fractional_vertices": [_point_payload(value) for value in self.fractional_vertices],
            "fractional_center": _point_payload(self.fractional_center),
            "cartesian_center": list(self.cartesian_center),
            "outward_unit_normal": list(self.outward_unit_normal),
            "area": self.area,
            "perimeter": self.perimeter,
            "aperture_witness_radius": self.aperture_witness_radius,
        }


@dataclass(frozen=True, slots=True)
class NaturalTileGeometry:
    tile_index: int
    label: str
    vertex_count: int
    edge_count: int
    face_count: int
    side_indices: tuple[int, ...]
    fractional_center: RationalPoint
    cartesian_center: tuple[float, float, float]
    fractional_volume: Fraction
    cartesian_volume: float
    surface_area: float
    equivalent_sphere_radius: float
    sphericity: float
    diameter: float
    convex_certified: bool

    def __post_init__(self) -> None:
        if isinstance(self.tile_index, bool) or int(self.tile_index) < 0:
            raise TilingGeometryInputError("tile_index must be nonnegative.")
        if not isinstance(self.label, str):
            raise TilingGeometryInputError("label must be a string.")
        object.__setattr__(self, "tile_index", int(self.tile_index))
        for name in ("vertex_count", "edge_count", "face_count"):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))
        sides = tuple(int(value) for value in self.side_indices)
        if len(sides) != self.face_count or sides != tuple(sorted(set(sides))):
            raise TilingGeometryInputError("side_indices must be sorted, unique, and match face_count.")
        object.__setattr__(self, "side_indices", sides)
        object.__setattr__(self, "fractional_center", _point(self.fractional_center, name="fractional_center"))
        volume = Fraction(self.fractional_volume)
        if volume <= 0:
            raise TilingGeometryInputError("fractional_volume must be positive.")
        object.__setattr__(self, "fractional_volume", volume)
        for name in ("cartesian_volume", "surface_area", "equivalent_sphere_radius", "sphericity", "diameter"):
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise TilingGeometryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        center = tuple(_finite(value, name="cartesian_center") for value in self.cartesian_center)
        if len(center) != 3:
            raise TilingGeometryInputError("cartesian_center must contain three values.")
        object.__setattr__(self, "cartesian_center", center)
        object.__setattr__(self, "convex_certified", bool(self.convex_certified))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "label": self.label,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "face_count": self.face_count,
            "side_indices": list(self.side_indices),
            "fractional_center": _point_payload(self.fractional_center),
            "cartesian_center": list(self.cartesian_center),
            "fractional_volume": _fraction_payload(self.fractional_volume),
            "cartesian_volume": self.cartesian_volume,
            "surface_area": self.surface_area,
            "equivalent_sphere_radius": self.equivalent_sphere_radius,
            "sphericity": self.sphericity,
            "diameter": self.diameter,
            "convex_certified": self.convex_certified,
        }


@dataclass(frozen=True, slots=True)
class TopologicalWindow:
    window_index: int
    face_index: int
    face_digest: str
    ring_size: int
    side_a: TileSideRef
    side_b: TileSideRef
    relative_tile_translation: LatticeShift
    self_adjacent: bool
    area: float
    aperture_witness_radius: float
    fractional_center: RationalPoint
    cartesian_center: tuple[float, float, float]

    def __post_init__(self) -> None:
        for name in ("window_index", "face_index"):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) < 0:
                raise TilingGeometryInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, int(value))
        _sha(self.face_digest, name="face_digest")
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        if not isinstance(self.side_a, TileSideRef) or not isinstance(self.side_b, TileSideRef):
            raise TilingGeometryInputError("Window sides must be TileSideRef records.")
        try:
            shift = coerce_lattice_shift(self.relative_tile_translation, name="relative_tile_translation")
        except ValueError as exc:
            raise TilingGeometryInputError(str(exc)) from exc
        object.__setattr__(self, "relative_tile_translation", shift)
        object.__setattr__(self, "self_adjacent", bool(self.self_adjacent))
        for name in ("area", "aperture_witness_radius"):
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise TilingGeometryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "fractional_center", _point(self.fractional_center, name="fractional_center"))
        center = tuple(_finite(value, name="cartesian_center") for value in self.cartesian_center)
        if len(center) != 3:
            raise TilingGeometryInputError("cartesian_center must contain three values.")
        object.__setattr__(self, "cartesian_center", center)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "face_index": self.face_index,
            "face_digest": self.face_digest,
            "ring_size": self.ring_size,
            "side_a": self.side_a.to_dict(),
            "side_b": self.side_b.to_dict(),
            "relative_tile_translation": list(self.relative_tile_translation),
            "self_adjacent": self.self_adjacent,
            "area": self.area,
            "aperture_witness_radius": self.aperture_witness_radius,
            "fractional_center": _point_payload(self.fractional_center),
            "cartesian_center": list(self.cartesian_center),
        }


@dataclass(frozen=True, order=True, slots=True)
class TileAdjacencyArc:
    arc_index: int
    window_index: int
    source_tile_index: int
    target_tile_index: int
    target_image_shift: LatticeShift

    def __post_init__(self) -> None:
        for name in ("arc_index", "window_index", "source_tile_index", "target_tile_index"):
            value = getattr(self, name)
            if isinstance(value, bool) or int(value) < 0:
                raise TilingGeometryInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, int(value))
        try:
            shift = coerce_lattice_shift(self.target_image_shift, name="target_image_shift")
        except ValueError as exc:
            raise TilingGeometryInputError(str(exc)) from exc
        object.__setattr__(self, "target_image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {
            "arc_index": self.arc_index,
            "window_index": self.window_index,
            "source_tile_index": self.source_tile_index,
            "target_tile_index": self.target_tile_index,
            "target_image_shift": list(self.target_image_shift),
        }


@dataclass(frozen=True, slots=True, eq=False)
class TilingGeometryCatalog:
    periodic_cell_complex_digest: str
    periodic_net_embedding_digest: str
    primitive_ring_catalog_digest: str
    tiles: tuple[NaturalTileGeometry, ...]
    tile_faces: tuple[TileFaceGeometry, ...]
    windows: tuple[TopologicalWindow, ...]
    adjacency_arcs: tuple[TileAdjacencyArc, ...]
    total_fractional_volume: Fraction
    canonical_schema_version: str = CANONICAL_TILING_GEOMETRY_SCHEMA
    digest_algorithm: str = TILING_GEOMETRY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in ("periodic_cell_complex_digest", "periodic_net_embedding_digest", "primitive_ring_catalog_digest"):
            _sha(getattr(self, name), name=name)
        tiles = tuple(self.tiles)
        faces = tuple(self.tile_faces)
        windows = tuple(self.windows)
        arcs = tuple(self.adjacency_arcs)
        if tuple(tile.tile_index for tile in tiles) != tuple(range(len(tiles))):
            raise TilingGeometryInputError("Tile geometry IDs must be dense and ordered.")
        if tuple(face.side_index for face in faces) != tuple(range(len(faces))):
            raise TilingGeometryInputError("Tile-face geometry IDs must be dense and ordered.")
        if tuple(window.window_index for window in windows) != tuple(range(len(windows))):
            raise TilingGeometryInputError("Window IDs must be dense and ordered.")
        if tuple(arc.arc_index for arc in arcs) != tuple(range(len(arcs))):
            raise TilingGeometryInputError("Adjacency arc IDs must be dense and ordered.")
        if len(arcs) != 2 * len(windows):
            raise TilingGeometryInputError("Exactly two directed adjacency arcs are required per window.")
        total = Fraction(self.total_fractional_volume)
        if total <= 0 or total != sum((tile.fractional_volume for tile in tiles), Fraction(0)):
            raise TilingGeometryInputError("total_fractional_volume is inconsistent with tiles.")
        if self.canonical_schema_version != CANONICAL_TILING_GEOMETRY_SCHEMA:
            raise TilingGeometryInputError("Unsupported tiling-geometry schema.")
        if self.digest_algorithm != TILING_GEOMETRY_DIGEST_ALGORITHM:
            raise TilingGeometryInputError("Unsupported tiling-geometry digest algorithm.")
        object.__setattr__(self, "tiles", tiles)
        object.__setattr__(self, "tile_faces", faces)
        object.__setattr__(self, "windows", windows)
        object.__setattr__(self, "adjacency_arcs", arcs)
        object.__setattr__(self, "total_fractional_volume", total)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise TilingGeometryInputError("Stored tiling-geometry digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, TilingGeometryCatalog) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "tiles": [tile.to_dict() for tile in self.tiles],
            "tile_faces": [face.to_dict() for face in self.tile_faces],
            "windows": [window.to_dict() for window in self.windows],
            "adjacency_arcs": [arc.to_dict() for arc in self.adjacency_arcs],
            "total_fractional_volume": _fraction_payload(self.total_fractional_volume),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        complex_: PeriodicCellComplex,
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        resources: TilingGeometryResources | None = None,
    ) -> "TilingGeometryCatalog":
        rebuilt = build_tiling_geometry_catalog(complex_, embedding, ring_index, resources=resources)
        if rebuilt.to_dict() != dict(payload):
            raise TilingGeometrySerializationError(
                "Serialized tiling geometry is not canonical for the supplied sources."
            )
        return rebuilt


def _build_tile_geometry(
    tile_index: int,
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    cell: np.ndarray,
    start_side_index: int,
    resources: TilingGeometryResources,
) -> tuple[NaturalTileGeometry, tuple[TileFaceGeometry, ...]]:
    shell = complex_.tile_shells[tile_index]
    raw_sides: list[tuple[TileSideRef, tuple[RationalPoint, ...], RationalPoint]] = []
    unique_vertices: set[RationalPoint] = set()
    exact_edges: set[tuple[RationalPoint, RationalPoint]] = set()
    for term in shell.face_incidences:
        face = complex_.face_placements[term.cell_index]
        points = _ring_vertices(face, ring_index, embedding, term.image_shift)
        if len(points) > resources.max_vertices_per_face:
            raise TilingGeometryResourceError("A face exceeds max_vertices_per_face.")
        normal = _polygon_normal(points)
        if not _strictly_convex_polygon(points, normal):
            raise TilingGeometryInvariantError("The first Stage-11 backend requires strictly convex faces.")
        side = TileSideRef(tile_index, term.cell_index, term.image_shift, term.coefficient)
        raw_sides.append((side, points, normal))
        unique_vertices.update(points)
        for first, second in zip(points, points[1:] + points[:1], strict=True):
            exact_edges.add(tuple(sorted((first, second))))
    if not unique_vertices:
        raise TilingGeometryInvariantError("Tile shell contains no vertices.")
    provisional_center = _average(tuple(sorted(unique_vertices)))

    side_geometries: list[TileFaceGeometry] = []
    oriented_polygons: list[tuple[RationalPoint, ...]] = []
    surface_area = 0.0
    for local_index, (side, original_points, original_normal) in enumerate(raw_sides):
        points = original_points
        normal = original_normal
        face_center = _average(points)
        center_sign = _dot(normal, _sub(provisional_center, face_center))
        if center_sign == 0:
            raise TilingGeometryInvariantError("Provisional tile center lies on a face plane.")
        if center_sign > 0:
            points = tuple(reversed(points))
            normal = _scale(normal, Fraction(-1))
        if any(_dot(normal, _sub(vertex, face_center)) > 0 for vertex in unique_vertices):
            raise TilingGeometryInvariantError(
                "The first Stage-11 backend requires a convex tile supported by every face plane."
            )
        if _dot(normal, _sub(provisional_center, face_center)) >= 0:
            raise TilingGeometryInvariantError("Tile witness is not strictly inside every face plane.")
        oriented_polygons.append(points)

        cart_points = tuple(_cartesian(point, cell) for point in points)
        cart_center = np.mean(np.vstack(cart_points), axis=0)
        area = 0.0
        for i in range(1, len(cart_points) - 1):
            area += 0.5 * float(np.linalg.norm(np.cross(cart_points[i] - cart_points[0], cart_points[i + 1] - cart_points[0])))
        perimeter = sum(
            float(np.linalg.norm(cart_points[(i + 1) % len(cart_points)] - cart_points[i]))
            for i in range(len(cart_points))
        )
        aperture = min(
            _point_segment_distance(cart_center, cart_points[i], cart_points[(i + 1) % len(cart_points)])
            for i in range(len(cart_points))
        )
        raw_cart_normal = np.cross(cart_points[1] - cart_points[0], cart_points[2] - cart_points[0])
        norm = float(np.linalg.norm(raw_cart_normal))
        if norm == 0.0:
            raise TilingGeometryInvariantError("Cartesian face normal is degenerate.")
        unit_normal = raw_cart_normal / norm
        if float(np.dot(unit_normal, _cartesian(provisional_center, cell) - cart_center)) > 0:
            unit_normal = -unit_normal
        surface_area += area
        side_geometries.append(
            TileFaceGeometry(
                start_side_index + local_index,
                side,
                len(points),
                points,
                face_center,
                tuple(float(value) for value in cart_center),
                tuple(float(value) for value in unit_normal),
                area,
                perimeter,
                aperture,
            )
        )

    volume = Fraction(0)
    centroid_numerator: RationalPoint = (Fraction(0), Fraction(0), Fraction(0))
    for points in oriented_polygons:
        for i in range(1, len(points) - 1):
            v0, v1, v2 = points[0], points[i], points[i + 1]
            tetra_volume = abs(
                _det(
                    _sub(v0, provisional_center),
                    _sub(v1, provisional_center),
                    _sub(v2, provisional_center),
                )
            ) / 6
            if tetra_volume == 0:
                raise TilingGeometryInvariantError("A face fan contains a degenerate triangle.")
            tetra_centroid = _scale(
                _add(_add(provisional_center, v0), _add(v1, v2)), Fraction(1, 4)
            )
            centroid_numerator = _add(centroid_numerator, _scale(tetra_centroid, tetra_volume))
            volume += tetra_volume
    if volume <= 0:
        raise TilingGeometryInvariantError("Tile volume is not positive.")
    solid_center = _scale(centroid_numerator, Fraction(1, 1) / volume)
    cart_center = _cartesian(solid_center, cell)
    cart_vertices = tuple(_cartesian(point, cell) for point in sorted(unique_vertices))
    pair_tests = len(cart_vertices) * (len(cart_vertices) - 1) // 2
    if pair_tests > resources.max_pair_distance_tests:
        raise TilingGeometryResourceError("Tile diameter work exceeds max_pair_distance_tests.")
    diameter = max(
        float(np.linalg.norm(left - right))
        for left, right in itertools.combinations(cart_vertices, 2)
    )
    cart_volume = float(volume)  # embedding cell volume is normalized to one
    equivalent_radius = (3.0 * cart_volume / (4.0 * math.pi)) ** (1.0 / 3.0)
    sphericity = math.pi ** (1.0 / 3.0) * (6.0 * cart_volume) ** (2.0 / 3.0) / surface_area
    tile = NaturalTileGeometry(
        tile_index,
        shell.label,
        len(unique_vertices),
        len(exact_edges),
        len(side_geometries),
        tuple(face.side_index for face in side_geometries),
        solid_center,
        tuple(float(value) for value in cart_center),
        volume,
        cart_volume,
        surface_area,
        equivalent_radius,
        sphericity,
        diameter,
        True,
    )
    return tile, tuple(side_geometries)


def build_tiling_geometry_catalog(
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    *,
    resources: TilingGeometryResources | None = None,
) -> TilingGeometryCatalog:
    """Realize exact reference tile geometry and translation-labelled windows.

    The first backend requires strictly convex planar scientific faces and convex
    tile shells.  Failure of that finite backend is explicit; no nonconvex volume
    or aperture interpretation is guessed.
    """

    if not isinstance(complex_, PeriodicCellComplex):
        raise TilingGeometryInputError("complex_ must be a PeriodicCellComplex.")
    if not isinstance(embedding, PeriodicNetEmbedding):
        raise TilingGeometryInputError("embedding must be a PeriodicNetEmbedding.")
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise TilingGeometryInputError("ring_index must be a PrimitiveRingIndex.")
    if complex_.periodic_net_embedding_digest != embedding.digest:
        raise TilingGeometryInputError("Cell complex and embedding digests disagree.")
    if complex_.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise TilingGeometryInputError("Cell complex and primitive-ring index digests disagree.")
    if complex_.topology_graph_digest != ring_index.topology_graph_digest:
        raise TilingGeometryInputError("Cell complex and primitive-ring topology digests disagree.")
    active = resources or TilingGeometryResources()
    if not isinstance(active, TilingGeometryResources):
        raise TilingGeometryInputError("resources must be TilingGeometryResources.")
    if len(complex_.tile_shells) > active.max_tiles:
        raise TilingGeometryResourceError("Tile count exceeds max_tiles.")
    if len(complex_.face_placements) > active.max_faces:
        raise TilingGeometryResourceError("Face count exceeds max_faces.")

    cell = embedding.cell_matrix()
    tiles: list[NaturalTileGeometry] = []
    tile_faces: list[TileFaceGeometry] = []
    for tile_index in range(len(complex_.tile_shells)):
        tile, faces = _build_tile_geometry(
            tile_index,
            complex_,
            embedding,
            ring_index,
            cell,
            len(tile_faces),
            active,
        )
        tiles.append(tile)
        tile_faces.extend(faces)

    sides_by_face: dict[int, list[TileFaceGeometry]] = defaultdict(list)
    for face in tile_faces:
        sides_by_face[face.side.face_index].append(face)
    windows: list[TopologicalWindow] = []
    arcs: list[TileAdjacencyArc] = []
    for face_index, scientific_face in enumerate(complex_.face_placements):
        sides = sorted(
            sides_by_face[face_index],
            key=lambda value: (
                value.side.tile_index,
                value.side.face_image_shift,
                value.side.incidence_orientation,
            ),
        )
        if len(sides) != 2:
            raise TilingGeometryInvariantError("Each scientific face must have exactly two tile sides.")
        first, second = sides
        if first.side.incidence_orientation != -second.side.incidence_orientation:
            raise TilingGeometryInvariantError("Window sides must have opposite incidence orientations.")
        if not math.isclose(first.area, second.area, rel_tol=1e-12, abs_tol=1e-12):
            raise TilingGeometryInvariantError("Translated window sides have inconsistent areas.")
        if not math.isclose(
            first.aperture_witness_radius,
            second.aperture_witness_radius,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise TilingGeometryInvariantError("Translated window sides have inconsistent aperture witnesses.")
        translation = subtract_shift(first.side.face_image_shift, second.side.face_image_shift)
        window = TopologicalWindow(
            face_index,
            face_index,
            scientific_face.digest,
            first.ring_size,
            first.side,
            second.side,
            translation,
            first.side.tile_index == second.side.tile_index,
            first.area,
            first.aperture_witness_radius,
            first.fractional_center,
            first.cartesian_center,
        )
        windows.append(window)
        arcs.append(
            TileAdjacencyArc(
                len(arcs),
                face_index,
                first.side.tile_index,
                second.side.tile_index,
                translation,
            )
        )
        arcs.append(
            TileAdjacencyArc(
                len(arcs),
                face_index,
                second.side.tile_index,
                first.side.tile_index,
                tuple(-value for value in translation),  # type: ignore[arg-type]
            )
        )

    return TilingGeometryCatalog(
        complex_.digest,
        embedding.digest,
        ring_index.catalog_digest,
        tuple(tiles),
        tuple(tile_faces),
        tuple(windows),
        tuple(arcs),
        sum((tile.fractional_volume for tile in tiles), Fraction(0)),
    )


__all__ = [
    "CANONICAL_TILING_GEOMETRY_SCHEMA",
    "TILING_GEOMETRY_DIGEST_ALGORITHM",
    "NaturalTileGeometry",
    "TileAdjacencyArc",
    "TileFaceGeometry",
    "TileSideRef",
    "TilingGeometryCatalog",
    "TilingGeometryError",
    "TilingGeometryInputError",
    "TilingGeometryInvariantError",
    "TilingGeometryResourceError",
    "TilingGeometryResources",
    "TilingGeometrySerializationError",
    "TopologicalWindow",
    "build_tiling_geometry_catalog",
]
