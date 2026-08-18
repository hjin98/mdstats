"""Stage-10D exact LTA natural-tiling end-to-end gate.

The first Stage-10D backend is intentionally LTA-specific.  It rebuilds the
unlabeled periodic net at primitive-ring bounds 8, 10, and 12, selects exactly
those bounded-strong primitive rings whose authoritative rational polygons are
strictly convex and planar, reconstructs tile sides from the exact cyclic order
of incident faces around every lifted framework edge, and certifies the resulting
periodic convex partition.

The translation-labelled net model follows Chung, Hahn, and Klee (1984), and the
natural-tiling/properness target follows Blatov, Delgado-Friedrichs, O'Keeffe, and
Proserpio (2007).  Exact face-sector propagation, the periodic convex-polytope
partition certificate, and the cross-bound LTA gate are mdstats-specific.

References
----------
S. J. Chung, T. Hahn, and W. E. Klee, Acta Cryst. A40, 42-50 (1984),
doi:10.1107/S010876738400010X.
V. A. Blatov, O. Delgado-Friedrichs, M. O'Keeffe, and D. M. Proserpio,
Acta Cryst. A63, 418-425 (2007), doi:10.1107/S0108767307038287.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from functools import cmp_to_key
import hashlib
import itertools
import json
from math import ceil, floor, gcd
from numbers import Integral
from typing import Any, Mapping, Sequence, TypeAlias

from ._periodic_graph import LatticeShift, add_shift, subtract_shift
from ._robust_geometry import RationalVector3, cross, dot, segment_triangle_intersection, subtract, translate, triangle_normal, triangle_triangle_intersection
from ._surface_mesh import validate_oriented_disk_triangulation
from .face_candidates import (
    FaceEmbeddingWitness,
    FacePlacementCertificate,
    FacePlacementStatus,
    FaceWitnessMethod,
    _boundary_geometry,
    _allowed_framework_contact,
    _edge_endpoints,
    _intersection_allowed,
    _triangle_coordinates,
    _triangle_refs,
    make_face_placement,
)
from .framework_topology import FrameworkTopology
from .natural_tiling import (
    OrientedCellImage,
    _map_shell,
    _match_tile_shell,
)
from .net_symmetry_discovery import PeriodicNetSymmetryDiscovery, discover_periodic_net_symmetry
from .periodic_cycle import RingPlacement
from .periodic_edge_intersection import certify_periodic_straight_edge_embedding
from .periodic_net_embedding import PeriodicNetEmbedding, build_periodic_net_embedding
from .periodic_net_view import PeriodicNetView, build_periodic_net_view
from .periodic_ring_action import map_ring_placement
from .periodic_cell_complex import PeriodicCellComplex, PeriodicTileShell, TranslatedCellTerm, build_periodic_cell_complex
from .primitive_ring import PrimitiveRingKey, PrimitiveRingOptions, enumerate_primitive_rings
from .primitive_ring_index import LiftedEdgeInstanceRef, PrimitiveRingIndex, build_primitive_ring_index, ring_placements_covering_edge
from .ring_strength import (
    EdgeIncidencePlacementDomain,
    RingStrengthDomain,
    RingStrengthStatus,
    build_ring_strength_catalog,
)

CANONICAL_LTA_GATE_SCHEMA = "mdstats.lta-natural-tiling-gate.v1"
CANONICAL_LTA_PARTITION_SCHEMA = "mdstats.lta-convex-partition.v1"
LTA_GATE_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)
Vector3 = RationalVector3
AxisKey: TypeAlias = tuple[int, int, int]


class LtaNaturalTilingError(ValueError):
    """Base exception for the Stage-10D LTA gate."""


class LtaNaturalTilingInputError(LtaNaturalTilingError):
    """Raised when inputs do not satisfy the declared Stage-10D contract."""


class LtaNaturalTilingInvariantError(LtaNaturalTilingError):
    """Raised when an exact LTA construction violates a required invariant."""


class LtaNaturalTilingResourceError(LtaNaturalTilingError):
    """Raised transactionally before a declared finite limit is exceeded."""


class LtaNaturalTilingSerializationError(LtaNaturalTilingError):
    """Raised when a persistent gate record fails deterministic replay."""


class LtaNaturalTilingGateStatus(str, Enum):
    CERTIFIED = "certified"
    REJECTED = "rejected"
    UNRESOLVED = "unresolved"


class LtaRingGeometryStatus(str, Enum):
    STRICTLY_CONVEX_PLANAR = "strictly-convex-planar"
    NONPLANAR = "nonplanar"
    PLANAR_NONCONVEX_OR_DEGENERATE = "planar-nonconvex-or-degenerate"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _positive(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise LtaNaturalTilingInputError(f"{name} must be a positive integer.")
    return int(value)


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _fraction_from_payload(value: Sequence[Any]) -> Fraction:
    if len(value) != 2:
        raise LtaNaturalTilingSerializationError("A fraction payload must contain two integers.")
    return Fraction(int(value[0]), int(value[1]))


def _ring_key_payload(key: PrimitiveRingKey) -> dict[str, Any]:
    return key.to_dict()


def _add(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[i] + right[i] for i in range(3))  # type: ignore[return-value]


def _scale(value: Vector3, factor: Fraction) -> Vector3:
    return tuple(component * factor for component in value)  # type: ignore[return-value]


def _average(points: Sequence[Vector3]) -> Vector3:
    if not points:
        raise LtaNaturalTilingInvariantError("Cannot average an empty point set.")
    return tuple(sum((point[axis] for point in points), Fraction(0)) / len(points) for axis in range(3))  # type: ignore[return-value]


def _det(left: Vector3, middle: Vector3, right: Vector3) -> Fraction:
    return dot(left, cross(middle, right))


def _negate_shift(value: LatticeShift) -> LatticeShift:
    return tuple(-component for component in value)  # type: ignore[return-value]


def _strict_convex_planar_status(points: Sequence[Vector3]) -> LtaRingGeometryStatus:
    """Classify one cyclic exact polygon without floating-point tolerances."""

    if len(points) < 3:
        return LtaRingGeometryStatus.PLANAR_NONCONVEX_OR_DEGENERATE
    origin = points[0]
    first: Vector3 | None = None
    second: Vector3 | None = None
    for point in points[1:]:
        candidate = subtract(point, origin)
        if candidate != (0, 0, 0):
            first = candidate
            break
    if first is None:
        return LtaRingGeometryStatus.PLANAR_NONCONVEX_OR_DEGENERATE
    for point in points[1:]:
        candidate = subtract(point, origin)
        if cross(first, candidate) != (0, 0, 0):
            second = candidate
            break
    if second is None:
        return LtaRingGeometryStatus.PLANAR_NONCONVEX_OR_DEGENERATE
    if any(_det(first, second, subtract(point, origin)) != 0 for point in points):
        return LtaRingGeometryStatus.NONPLANAR

    for axis_a, axis_b in ((0, 1), (0, 2), (1, 2)):
        if first[axis_a] * second[axis_b] - first[axis_b] * second[axis_a] == 0:
            continue
        signs: list[int] = []
        for index in range(len(points)):
            p0 = points[index]
            p1 = points[(index + 1) % len(points)]
            p2 = points[(index + 2) % len(points)]
            turn = (
                (p1[axis_a] - p0[axis_a]) * (p2[axis_b] - p1[axis_b])
                - (p1[axis_b] - p0[axis_b]) * (p2[axis_a] - p1[axis_a])
            )
            if turn == 0:
                return LtaRingGeometryStatus.PLANAR_NONCONVEX_OR_DEGENERATE
            signs.append(1 if turn > 0 else -1)
        if len(set(signs)) == 1:
            return LtaRingGeometryStatus.STRICTLY_CONVEX_PLANAR
        return LtaRingGeometryStatus.PLANAR_NONCONVEX_OR_DEGENERATE
    return LtaRingGeometryStatus.PLANAR_NONCONVEX_OR_DEGENERATE


@dataclass(frozen=True, order=True, slots=True)
class LtaTileSignature:
    """Face-size exponent signature of one finite lifted tile shell."""

    face_counts: tuple[tuple[int, int], ...]

    def __post_init__(self) -> None:
        values = tuple((int(size), int(count)) for size, count in self.face_counts)
        if not values or values != tuple(sorted(values)) or len({size for size, _ in values}) != len(values):
            raise LtaNaturalTilingInputError("face_counts must be nonempty, sorted, and unique by face size.")
        if any(size <= 0 or count <= 0 for size, count in values):
            raise LtaNaturalTilingInputError("Tile signature sizes and counts must be positive.")
        object.__setattr__(self, "face_counts", values)

    @property
    def symbol(self) -> str:
        return ".".join(f"{size}^{count}" for size, count in self.face_counts)

    def to_dict(self) -> dict[str, Any]:
        return {"face_counts": [[size, count] for size, count in self.face_counts], "symbol": self.symbol}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaTileSignature":
        result = cls(tuple((int(a), int(b)) for a, b in payload["face_counts"]))
        if str(payload.get("symbol")) != result.symbol:
            raise LtaNaturalTilingSerializationError("Tile-signature symbol is inconsistent.")
        return result


@dataclass(frozen=True, order=True, slots=True)
class LtaTileMultiplicity:
    signature: LtaTileSignature
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.signature, LtaTileSignature):
            raise LtaNaturalTilingInputError("signature must be an LtaTileSignature.")
        object.__setattr__(self, "count", _positive(self.count, name="count"))

    def to_dict(self) -> dict[str, Any]:
        return {"signature": self.signature.to_dict(), "count": self.count}


@dataclass(frozen=True, slots=True)
class LtaNaturalTilingResources:
    max_bounds: int = 3
    max_rings_per_bound: int = 512
    max_selected_faces: int = 256
    max_face_triangle_tests: int = 2_000_000
    max_framework_contact_tests: int = 2_000_000
    max_edge_sector_occurrences: int = 4096
    max_periodic_tile_pairs: int = 100_000
    max_sat_axes: int = 10_000_000
    max_symmetry_face_images: int = 100_000
    max_symmetry_tile_images: int = 100_000
    max_symmetry_composition_checks: int = 2_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, slots=True)
class LtaConvexTileCertificate:
    tile_index: int
    signature: LtaTileSignature
    vertex_count: int
    edge_count: int
    face_count: int
    fractional_volume: Fraction
    strict_interior_point: Vector3
    supporting_plane_count: int

    def __post_init__(self) -> None:
        if self.tile_index < 0:
            raise LtaNaturalTilingInputError("tile_index must be nonnegative.")
        for name in ("vertex_count", "edge_count", "face_count", "supporting_plane_count"):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))
        volume = Fraction(self.fractional_volume)
        if volume <= 0:
            raise LtaNaturalTilingInputError("fractional_volume must be positive.")
        point = tuple(Fraction(value) for value in self.strict_interior_point)
        if len(point) != 3:
            raise LtaNaturalTilingInputError("strict_interior_point must contain three fractions.")
        object.__setattr__(self, "fractional_volume", volume)
        object.__setattr__(self, "strict_interior_point", point)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "signature": self.signature.to_dict(),
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "face_count": self.face_count,
            "fractional_volume": _fraction_payload(self.fractional_volume),
            "strict_interior_point": [_fraction_payload(value) for value in self.strict_interior_point],
            "supporting_plane_count": self.supporting_plane_count,
        }


@dataclass(frozen=True, slots=True, eq=False)
class LtaConvexPartitionCertificate:
    periodic_cell_complex_digest: str
    tiles: tuple[LtaConvexTileCertificate, ...]
    periodic_pair_candidate_count: int
    exact_axis_test_count: int
    total_fractional_volume: Fraction
    certified_pairwise_interior_disjoint: bool
    certified_no_void: bool
    canonical_schema_version: str = CANONICAL_LTA_PARTITION_SCHEMA
    digest_algorithm: str = LTA_GATE_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.periodic_cell_complex_digest, str) or len(self.periodic_cell_complex_digest) != 64:
            raise LtaNaturalTilingInputError("periodic_cell_complex_digest must be SHA-256.")
        tiles = tuple(self.tiles)
        if tuple(tile.tile_index for tile in tiles) != tuple(range(len(tiles))):
            raise LtaNaturalTilingInputError("Partition tiles must have dense ordered IDs.")
        for name in ("periodic_pair_candidate_count", "exact_axis_test_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
                raise LtaNaturalTilingInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, int(value))
        total = Fraction(self.total_fractional_volume)
        object.__setattr__(self, "tiles", tiles)
        object.__setattr__(self, "total_fractional_volume", total)
        if self.canonical_schema_version != CANONICAL_LTA_PARTITION_SCHEMA or self.digest_algorithm != LTA_GATE_DIGEST_ALGORITHM:
            raise LtaNaturalTilingInputError("Unsupported LTA partition schema.")
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise LtaNaturalTilingInputError("Stored LTA partition digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    @property
    def certified(self) -> bool:
        return (
            self.certified_pairwise_interior_disjoint
            and self.certified_no_void
            and self.total_fractional_volume == 1
        )

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "tiles": [tile.to_dict() for tile in self.tiles],
            "periodic_pair_candidate_count": self.periodic_pair_candidate_count,
            "exact_axis_test_count": self.exact_axis_test_count,
            "total_fractional_volume": _fraction_payload(self.total_fractional_volume),
            "certified_pairwise_interior_disjoint": self.certified_pairwise_interior_disjoint,
            "certified_no_void": self.certified_no_void,
            "certified": self.certified,
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


@dataclass(frozen=True, slots=True)
class LtaBoundObservation:
    primitive_ring_bound: int
    ring_counts: tuple[tuple[int, int], ...]
    strength_counts: tuple[tuple[int, str, int], ...]
    geometry_counts: tuple[tuple[int, str, int], ...]
    selected_face_counts: tuple[tuple[int, int], ...]
    selected_ring_key_digests: tuple[str, ...]
    excluded_strong_nonplanar_key_digests: tuple[str, ...]
    cell_counts: tuple[int, int, int, int]
    tile_multiplicities: tuple[LtaTileMultiplicity, ...]
    reduced_multiplicity_ratio: tuple[int, ...]
    complex_scientific_key: str
    partition_certificate_digest: str
    partition_total_fractional_volume: Fraction
    partition_pair_candidate_count: int
    partition_axis_test_count: int
    tile_fractional_volumes: tuple[Fraction, ...]
    symmetry_order: int
    symmetry_preserved: bool
    symmetry_composition_check_count: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "primitive_ring_bound", _positive(self.primitive_ring_bound, name="primitive_ring_bound"))
        if len(self.cell_counts) != 4 or any(value <= 0 for value in self.cell_counts):
            raise LtaNaturalTilingInputError("cell_counts must contain four positive integers.")
        if not isinstance(self.complex_scientific_key, str) or len(self.complex_scientific_key) != 64:
            raise LtaNaturalTilingInputError("complex_scientific_key must be SHA-256.")
        if not isinstance(self.partition_certificate_digest, str) or len(self.partition_certificate_digest) != 64:
            raise LtaNaturalTilingInputError("partition_certificate_digest must be SHA-256.")
        object.__setattr__(self, "partition_total_fractional_volume", Fraction(self.partition_total_fractional_volume))
        object.__setattr__(self, "tile_fractional_volumes", tuple(Fraction(value) for value in self.tile_fractional_volumes))
        for name in ("partition_pair_candidate_count", "partition_axis_test_count"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
                raise LtaNaturalTilingInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, int(value))

    def to_dict(self) -> dict[str, Any]:
        return {
            "primitive_ring_bound": self.primitive_ring_bound,
            "ring_counts": [list(value) for value in self.ring_counts],
            "strength_counts": [list(value) for value in self.strength_counts],
            "geometry_counts": [list(value) for value in self.geometry_counts],
            "selected_face_counts": [list(value) for value in self.selected_face_counts],
            "selected_ring_key_digests": list(self.selected_ring_key_digests),
            "excluded_strong_nonplanar_key_digests": list(self.excluded_strong_nonplanar_key_digests),
            "cell_counts": list(self.cell_counts),
            "tile_multiplicities": [value.to_dict() for value in self.tile_multiplicities],
            "reduced_multiplicity_ratio": list(self.reduced_multiplicity_ratio),
            "complex_scientific_key": self.complex_scientific_key,
            "partition_certificate_digest": self.partition_certificate_digest,
            "partition_total_fractional_volume": _fraction_payload(self.partition_total_fractional_volume),
            "partition_pair_candidate_count": self.partition_pair_candidate_count,
            "partition_axis_test_count": self.partition_axis_test_count,
            "tile_fractional_volumes": [_fraction_payload(value) for value in self.tile_fractional_volumes],
            "symmetry_order": self.symmetry_order,
            "symmetry_preserved": self.symmetry_preserved,
            "symmetry_composition_check_count": self.symmetry_composition_check_count,
        }


@dataclass(frozen=True, slots=True, eq=False)
class LtaNaturalTilingGate:
    topology_graph_digest: str
    periodic_net_view_digest: str
    periodic_net_symmetry_digest: str
    periodic_net_embedding_digest: str
    bounds: tuple[int, ...]
    observations: tuple[LtaBoundObservation, ...]
    expected_tile_multiplicities: tuple[LtaTileMultiplicity, ...]
    selected_faces_stable: bool
    tiling_stable: bool
    expected_lta_match: bool
    status: LtaNaturalTilingGateStatus
    unresolved_assumptions: tuple[str, ...] = ()
    canonical_schema_version: str = CANONICAL_LTA_GATE_SCHEMA
    digest_algorithm: str = LTA_GATE_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in ("topology_graph_digest", "periodic_net_view_digest", "periodic_net_symmetry_digest", "periodic_net_embedding_digest"):
            if not isinstance(getattr(self, name), str) or len(getattr(self, name)) != 64:
                raise LtaNaturalTilingInputError(f"{name} must be SHA-256.")
        bounds = tuple(int(value) for value in self.bounds)
        if bounds != tuple(sorted(set(bounds))) or not bounds:
            raise LtaNaturalTilingInputError("bounds must be nonempty, strictly increasing, and unique.")
        observations = tuple(self.observations)
        if tuple(value.primitive_ring_bound for value in observations) != bounds:
            raise LtaNaturalTilingInputError("observations must align with bounds.")
        object.__setattr__(self, "bounds", bounds)
        object.__setattr__(self, "observations", observations)
        object.__setattr__(self, "status", LtaNaturalTilingGateStatus(self.status))
        object.__setattr__(self, "unresolved_assumptions", tuple(str(value) for value in self.unresolved_assumptions))
        if self.canonical_schema_version != CANONICAL_LTA_GATE_SCHEMA or self.digest_algorithm != LTA_GATE_DIGEST_ALGORITHM:
            raise LtaNaturalTilingInputError("Unsupported LTA gate schema.")
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise LtaNaturalTilingInputError("Stored LTA gate digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    @property
    def certified(self) -> bool:
        return self.status is LtaNaturalTilingGateStatus.CERTIFIED

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "topology_graph_digest": self.topology_graph_digest,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "periodic_net_symmetry_digest": self.periodic_net_symmetry_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "bounds": list(self.bounds),
            "observations": [value.to_dict() for value in self.observations],
            "expected_tile_multiplicities": [value.to_dict() for value in self.expected_tile_multiplicities],
            "selected_faces_stable": self.selected_faces_stable,
            "tiling_stable": self.tiling_stable,
            "expected_lta_match": self.expected_lta_match,
            "status": self.status.value,
            "unresolved_assumptions": list(self.unresolved_assumptions),
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
        topology: FrameworkTopology,
        resources: "LtaNaturalTilingResources | None" = None,
    ) -> "LtaNaturalTilingGate":
        rebuilt = certify_lta_natural_tiling(
            topology,
            bounds=tuple(int(value) for value in payload["bounds"]),
            resources=resources,
        )
        if rebuilt.to_dict() != dict(payload):
            raise LtaNaturalTilingSerializationError(
                "Serialized LTA gate is not canonical for the supplied topology."
            )
        return rebuilt


@dataclass(frozen=True, slots=True)
class _TileGeometry:
    tile_index: int
    signature: LtaTileSignature
    vertices: tuple[Vector3, ...]
    edges: tuple[tuple[Vector3, Vector3], ...]
    outward_planes: tuple[tuple[Vector3, Vector3], ...]
    volume: Fraction
    interior: Vector3


@dataclass(frozen=True, slots=True)
class _BoundBuild:
    observation: LtaBoundObservation
    complex_: PeriodicCellComplex
    partition: LtaConvexPartitionCertificate
    ring_index: PrimitiveRingIndex


@dataclass(frozen=True, slots=True)
class LtaNaturalTilingReference:
    """Transient exact LTA sources for downstream Stage-11 geometry."""

    view: PeriodicNetView
    discovery: PeriodicNetSymmetryDiscovery
    embedding: PeriodicNetEmbedding
    ring_index: PrimitiveRingIndex
    complex: PeriodicCellComplex
    partition: LtaConvexPartitionCertificate

    def __post_init__(self) -> None:
        if self.complex.periodic_net_view_digest != self.view.digest:
            raise LtaNaturalTilingInputError("LTA reference view and complex disagree.")
        if self.complex.periodic_net_embedding_digest != self.embedding.digest:
            raise LtaNaturalTilingInputError("LTA reference embedding and complex disagree.")
        if self.complex.primitive_ring_catalog_digest != self.ring_index.catalog_digest:
            raise LtaNaturalTilingInputError("LTA reference ring index and complex disagree.")
        if self.partition.periodic_cell_complex_digest != self.complex.digest:
            raise LtaNaturalTilingInputError("LTA reference partition and complex disagree.")


def _ring_coordinates(index: PrimitiveRingIndex, embedding: PeriodicNetEmbedding, key: PrimitiveRingKey, shift: LatticeShift = ZERO_SHIFT) -> tuple[Vector3, ...]:
    ring = index.ring_for_key(key)
    return tuple(
        embedding.fractional_coordinate(ref.atom_index, add_shift(ref.image_shift, shift))
        for ref in ring.vertex_walk
    )


def _overlap_translation_shifts(
    fixed_points: Sequence[Vector3],
    moving_points: Sequence[Vector3],
) -> tuple[LatticeShift, ...]:
    ranges = []
    for axis in range(3):
        fixed_values = [point[axis] for point in fixed_points]
        moving_values = [point[axis] for point in moving_points]
        low = ceil(min(fixed_values) - max(moving_values))
        high = floor(max(fixed_values) - min(moving_values))
        if low > high:
            return ()
        ranges.append(range(low, high + 1))
    return tuple(tuple(value) for value in itertools.product(*ranges))  # type: ignore[return-value]


def _build_face_certificates(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    index: PrimitiveRingIndex,
    edge_certificate_digest: str,
    keys: Sequence[PrimitiveRingKey],
    resources: LtaNaturalTilingResources,
) -> tuple[tuple[FacePlacementCertificate, ...], tuple[FaceEmbeddingWitness, ...]]:
    """Build strict-convex fan witnesses with direct exact periodic tests.

    LTA contains only 96 quotient framework edges and 172 selected face
    triangles.  Enumerating the finite AABB-derived translation ranges directly
    is substantially cheaper than rebuilding a generic linked-cell broad phase
    for every disk, while retaining the same exact predicates and contact rules.
    """

    prepared = []
    triangle_tests = 0
    framework_tests = 0
    edge_records = tuple(
        (edge_key, _edge_endpoints(embedding, edge_key, ZERO_SHIFT))
        for edge_key in embedding.edge_keys
    )

    for key in keys:
        face = make_face_placement(
            embedding,
            index,
            RingPlacement(index.topology_graph_digest, key, ZERO_SHIFT),
        )
        boundary = _boundary_geometry(face, embedding, index)
        triangles = tuple(
            (0, position, position + 1)
            for position in range(1, len(boundary.refs) - 1)
        )
        validate_oriented_disk_triangulation(len(boundary.refs), triangles)
        coordinates = _triangle_coordinates(boundary, triangles)
        refs = _triangle_refs(boundary, triangles)
        for triangle in coordinates:
            triangle_normal(triangle)

        # Exact periodic self-intersection test for this fan.
        for left_index, left_triangle in enumerate(coordinates):
            for right_index in range(left_index, len(coordinates)):
                right_base = coordinates[right_index]
                for shift in _overlap_translation_shifts(left_triangle, right_base):
                    if left_index == right_index and shift == ZERO_SHIFT:
                        continue
                    if left_index == right_index and shift < ZERO_SHIFT:
                        continue
                    triangle_tests += 1
                    if triangle_tests > resources.max_face_triangle_tests:
                        raise LtaNaturalTilingResourceError(
                            "Exact face triangle-test count exceeds max_face_triangle_tests."
                        )
                    right_triangle = tuple(translate(point, shift) for point in right_base)
                    exact = triangle_triangle_intersection(left_triangle, right_triangle)
                    if exact.empty:
                        continue
                    allowed_vertices = []
                    allowed_edges = []
                    if shift == ZERO_SHIFT:
                        common = set(triangles[left_index]).intersection(triangles[right_index])
                        allowed_vertices = [
                            left_triangle[triangles[left_index].index(value)] for value in common
                        ]
                        if len(common) == 2:
                            first, second = sorted(common)
                            allowed_edges.append(
                                (
                                    left_triangle[triangles[left_index].index(first)],
                                    left_triangle[triangles[left_index].index(second)],
                                )
                            )
                    if not _intersection_allowed(exact, allowed_vertices, allowed_edges):
                        raise LtaNaturalTilingInvariantError(
                            "A strict-convex LTA fan self-intersects in the periodic lift."
                        )

        # Exact framework penetration test.  Translate the quotient edge, not the
        # triangle, so LiftedEdgeInstanceRef remains physically transparent.
        boundary_edges = frozenset(boundary.edges)
        for triangle, triangle_refs in zip(coordinates, refs, strict=True):
            for edge_key, edge_base in edge_records:
                for anchor in _overlap_translation_shifts(triangle, edge_base):
                    framework_tests += 1
                    if framework_tests > resources.max_framework_contact_tests:
                        raise LtaNaturalTilingResourceError(
                            "Framework contact-test count exceeds max_framework_contact_tests."
                        )
                    edge_instance = LiftedEdgeInstanceRef(
                        embedding.topology_graph_digest, edge_key, anchor
                    )
                    start, end = (translate(point, anchor) for point in edge_base)
                    exact = segment_triangle_intersection(start, end, triangle)
                    if exact.empty:
                        continue
                    if not _allowed_framework_contact(
                        exact,
                        edge_instance,
                        triangle_refs,
                        triangle,
                        boundary_edges,
                    ):
                        raise LtaNaturalTilingInvariantError(
                            "A selected LTA natural face is penetrated by the framework."
                        )
        prepared.append((face, triangles))

    query_digest = _digest(
        {
            "embedding": embedding.digest,
            "ring_catalog": index.catalog_digest,
            "face_keys": [_ring_key_payload(key) for key in keys],
            "triangle_tests": triangle_tests,
            "framework_tests": framework_tests,
            "query": "lta-direct-exact-face-and-framework",
        }
    )
    certificates = []
    witnesses = []
    for face, triangles in prepared:
        witness = FaceEmbeddingWitness(
            face,
            0,
            FaceWitnessMethod.BOUNDARY_VERTEX_TRIANGULATION,
            triangles,
            query_digest,
            query_digest,
            (),
        )
        certificates.append(
            FacePlacementCertificate(
                view.digest,
                view.source_graph_digest,
                embedding.digest,
                index.catalog_digest,
                edge_certificate_digest,
                face,
                1,
                (witness,),
                (),
                FacePlacementStatus.CERTIFIED_ADMISSIBLE,
            )
        )
        witnesses.append(witness)
    return tuple(certificates), tuple(witnesses)

def _quotient_coordinates(direction: Vector3, ray: Vector3) -> tuple[Fraction, Fraction]:
    pivot = next((axis for axis, value in enumerate(direction) if value != 0), None)
    if pivot is None:
        raise LtaNaturalTilingInvariantError("A framework edge has zero direction.")
    remaining = [axis for axis in range(3) if axis != pivot]
    result = (
        direction[pivot] * ray[remaining[0]] - direction[remaining[0]] * ray[pivot],
        direction[pivot] * ray[remaining[1]] - direction[remaining[1]] * ray[pivot],
    )
    basis_a = tuple(Fraction(1) if axis == remaining[0] else Fraction(0) for axis in range(3))
    basis_b = tuple(Fraction(1) if axis == remaining[1] else Fraction(0) for axis in range(3))
    if _det(direction, basis_a, basis_b) * direction[pivot] * direction[pivot] < 0:
        result = (result[0], -result[1])
    return result


def _angle_compare(left: tuple[Fraction, Fraction], right: tuple[Fraction, Fraction]) -> int:
    left_half = 0 if left[1] > 0 or (left[1] == 0 and left[0] >= 0) else 1
    right_half = 0 if right[1] > 0 or (right[1] == 0 and right[0] >= 0) else 1
    if left_half != right_half:
        return -1 if left_half < right_half else 1
    determinant = left[0] * right[1] - left[1] * right[0]
    return -1 if determinant > 0 else (1 if determinant < 0 else 0)


def _build_tile_shells(
    index: PrimitiveRingIndex,
    embedding: PeriodicNetEmbedding,
    face_keys: Sequence[PrimitiveRingKey],
    resources: LtaNaturalTilingResources,
) -> tuple[PeriodicTileShell, ...]:
    face_position = {key: position for position, key in enumerate(face_keys)}
    adjacency: dict[tuple[int, int], set[tuple[tuple[int, int], LatticeShift]]] = defaultdict(set)
    occurrence_count = 0

    for face_key in face_keys:
        for edge_instance in index.canonical_edge_instances(face_key):
            edge = edge_instance.edge_key
            anchor = edge_instance.anchor_shift
            start = embedding.fractional_coordinate(edge.vertex_i, anchor)
            end = embedding.fractional_coordinate(edge.vertex_j, add_shift(anchor, edge.image_shift))
            direction = subtract(end, start)
            midpoint = _scale(_add(start, end), Fraction(1, 2))
            incidents = []
            for occurrence in ring_placements_covering_edge(index, edge_instance):
                if occurrence.placement.ring_key not in face_position:
                    continue
                coordinates = _ring_coordinates(index, embedding, occurrence.placement.ring_key, occurrence.placement.image_shift)
                ray = subtract(_average(coordinates), midpoint)
                quotient = _quotient_coordinates(direction, ray)
                if quotient == (0, 0):
                    raise LtaNaturalTilingInvariantError("An incident face has no exact side ray around an edge.")
                incidents.append((quotient, occurrence))
            occurrence_count += len(incidents)
            if occurrence_count > resources.max_edge_sector_occurrences:
                raise LtaNaturalTilingResourceError("Edge-sector occurrence count exceeds max_edge_sector_occurrences.")
            incidents.sort(key=cmp_to_key(lambda a, b: _angle_compare(a[0], b[0])))
            if len(incidents) != 3:
                raise LtaNaturalTilingInvariantError(
                    "The LTA natural-face set must contain exactly three faces around every framework edge."
                )
            if any(_angle_compare(incidents[i][0], incidents[(i + 1) % 3][0]) == 0 for i in range(3)):
                raise LtaNaturalTilingInvariantError("Two incident face-side rays are collinear.")
            for left, right in zip(incidents, incidents[1:] + incidents[:1], strict=True):
                occurrence_left = left[1]
                occurrence_right = right[1]
                node_left = (face_position[occurrence_left.placement.ring_key], occurrence_left.orientation)
                node_right = (face_position[occurrence_right.placement.ring_key], -occurrence_right.orientation)
                gain = subtract_shift(occurrence_right.placement.image_shift, occurrence_left.placement.image_shift)
                adjacency[node_left].add((node_right, gain))
                adjacency[node_right].add((node_left, _negate_shift(gain)))

    components: list[dict[tuple[int, int], LatticeShift]] = []
    seen: set[tuple[int, int]] = set()
    for root in sorted(adjacency):
        if root in seen:
            continue
        offsets = {root: ZERO_SHIFT}
        queue = deque((root,))
        while queue:
            node = queue.popleft()
            seen.add(node)
            for target, gain in sorted(adjacency[node]):
                expected = add_shift(offsets[node], gain)
                if target in offsets and offsets[target] != expected:
                    raise LtaNaturalTilingInvariantError(
                        "A face-side component carries a nonzero periodic translation cycle."
                    )
                if target not in offsets:
                    offsets[target] = expected
                    queue.append(target)
        components.append(offsets)

    shells: list[PeriodicTileShell] = []
    for tile_index, offsets in enumerate(components):
        counts = Counter(index.ring_for_key(face_keys[face_index]).size for face_index, _ in offsets)
        signature = LtaTileSignature(tuple(sorted(counts.items())))
        terms = tuple(
            TranslatedCellTerm(face_index, offsets[(face_index, side)], -side)
            for face_index, side in sorted(offsets)
        )
        shells.append(PeriodicTileShell(tile_index, terms, signature.symbol))
    return tuple(shells)


def _complex_scientific_key(complex_: PeriodicCellComplex, face_keys: Sequence[PrimitiveRingKey]) -> str:
    shells = []
    for shell in complex_.tile_shells:
        shells.append(
            {
                "label": shell.label,
                "faces": sorted(
                    [
                        (
                            _ring_key_payload(face_keys[term.cell_index]),
                            list(term.image_shift),
                            term.coefficient,
                        )
                        for term in shell.face_incidences
                    ],
                    key=_canonical_json,
                ),
            }
        )
    return _digest(
        {
            "view": complex_.periodic_net_view_digest,
            "embedding": complex_.periodic_net_embedding_digest,
            "cell_counts": list(complex_.cell_counts),
            "faces": [_ring_key_payload(key) for key in face_keys],
            "tile_shells": sorted(shells, key=_canonical_json),
        }
    )


def _direct_symmetry_certificate(
    complex_: PeriodicCellComplex,
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    index: PrimitiveRingIndex,
    resources: LtaNaturalTilingResources,
) -> tuple[bool, int]:
    """Prove invariance from a certified generating set of the full group.

    The discovery record already proves that ``generator_operation_indices``
    generates every one of the 96 exact automorphisms.  Therefore it is both
    sufficient and much cheaper to prove that every generator preserves the
    scientific face and tile sets; closure then proves preservation by every
    group element.  Auxiliary fan and convex-partition evidence is deliberately
    absent from this action.
    """

    symmetry = discovery.symmetry
    generators = discovery.generator_operation_indices
    if len(generators) * len(complex_.face_placements) > resources.max_symmetry_face_images:
        raise LtaNaturalTilingResourceError("Generator face images exceed max_symmetry_face_images.")
    if len(generators) * len(complex_.tile_shells) > resources.max_symmetry_tile_images:
        raise LtaNaturalTilingResourceError("Generator tile images exceed max_symmetry_tile_images.")

    # Independently replay finite closure from the stored multiplication table.
    subgroup = {symmetry.identity_operation_index}
    closure_checks = 0
    changed = True
    while changed:
        changed = False
        current = tuple(sorted(subgroup))
        for outer in current:
            for generator in generators:
                for product in (
                    symmetry.multiplication_table[outer][generator],
                    symmetry.multiplication_table[generator][outer],
                ):
                    closure_checks += 1
                    if closure_checks > resources.max_symmetry_composition_checks:
                        raise LtaNaturalTilingResourceError(
                            "Generator closure exceeds max_symmetry_composition_checks."
                        )
                    if product not in subgroup:
                        subgroup.add(product)
                        changed = True
    if len(subgroup) != symmetry.order:
        raise LtaNaturalTilingInvariantError(
            "Stored LTA symmetry generators do not recover the complete group."
        )

    target_by_key = {
        face.ring_placement.ring_key: position
        for position, face in enumerate(complex_.face_placements)
    }
    image_checks = 0
    for operation_index in generators:
        operation = symmetry.operations[operation_index]
        face_images: list[OrientedCellImage] = []
        for face in complex_.face_placements:
            mapped = map_ring_placement(index, view, operation, face.ring_placement)
            target_index = target_by_key.get(mapped.target_placement.ring_key)
            if target_index is None:
                return False, closure_checks + image_checks
            target = complex_.face_placements[target_index]
            face_images.append(
                OrientedCellImage(
                    target_index,
                    subtract_shift(
                        mapped.target_placement.image_shift,
                        target.ring_placement.image_shift,
                    ),
                    mapped.orientation * target.orientation,
                )
            )
            image_checks += 1
        for shell in complex_.tile_shells:
            mapped_shell = _map_shell(shell, face_images, operation.lattice_matrix)
            if _match_tile_shell(mapped_shell, complex_.tile_shells) is None:
                return False, closure_checks + image_checks
            image_checks += 1
    return True, closure_checks + image_checks

def _axis_key(axis: Vector3) -> AxisKey | None:
    if axis == (0, 0, 0):
        return None
    denominator_lcm = 1
    for value in axis:
        denominator_lcm = denominator_lcm * value.denominator // gcd(denominator_lcm, value.denominator)
    integers = [int(value * denominator_lcm) for value in axis]
    divisor = 0
    for value in integers:
        divisor = gcd(divisor, abs(value))
    integers = [value // divisor for value in integers]
    for value in integers:
        if value:
            if value < 0:
                integers = [-item for item in integers]
            break
    return tuple(integers)  # type: ignore[return-value]


def _axis_from_key(key: AxisKey) -> Vector3:
    return tuple(Fraction(value) for value in key)  # type: ignore[return-value]


def _tile_geometry(
    shell: PeriodicTileShell,
    index: PrimitiveRingIndex,
    embedding: PeriodicNetEmbedding,
    face_keys: Sequence[PrimitiveRingKey],
) -> _TileGeometry:
    all_vertices: list[Vector3] = []
    edge_pairs: set[tuple[Vector3, Vector3]] = set()
    planes: list[tuple[Vector3, Vector3]] = []
    volume = Fraction(0)
    signature_counts: Counter[int] = Counter()
    for term in shell.face_incidences:
        ring = index.ring_for_key(face_keys[term.cell_index])
        points = tuple(
            embedding.fractional_coordinate(ref.atom_index, add_shift(ref.image_shift, term.image_shift))
            for ref in ring.vertex_walk
        )
        signature_counts[ring.size] += 1
        all_vertices.extend(points)
        for position in range(len(points)):
            pair = tuple(sorted((points[position], points[(position + 1) % len(points)])))
            edge_pairs.add(pair)  # type: ignore[arg-type]
        normal = triangle_normal((points[0], points[1], points[2]))
        outward = _scale(normal, Fraction(term.coefficient))
        planes.append((outward, points[0]))
        for position in range(1, len(points) - 1):
            triangle = (points[0], points[position], points[position + 1])
            if term.coefficient == -1:
                triangle = (triangle[0], triangle[2], triangle[1])
            volume += dot(triangle[0], cross(triangle[1], triangle[2])) / 6
    vertices = tuple(sorted(set(all_vertices)))
    center = _average(vertices)
    for normal, point in planes:
        sides = tuple(dot(normal, subtract(vertex, point)) for vertex in vertices)
        if any(value > 0 for value in sides):
            raise LtaNaturalTilingInvariantError("A reconstructed LTA tile is not convex in its face halfspaces.")
        if dot(normal, subtract(center, point)) >= 0:
            raise LtaNaturalTilingInvariantError("The exact vertex-average point is not strictly inside an LTA tile.")
    if volume <= 0:
        raise LtaNaturalTilingInvariantError("An oriented LTA tile has nonpositive exact volume.")
    return _TileGeometry(
        shell.tile_index,
        LtaTileSignature(tuple(sorted(signature_counts.items()))),
        vertices,
        tuple(sorted(edge_pairs)),
        tuple(planes),
        volume,
        center,
    )


def _ceil_fraction(value: Fraction) -> int:
    return ceil(value)


def _floor_fraction(value: Fraction) -> int:
    return floor(value)


def _translation_candidates(left: _TileGeometry, right: _TileGeometry) -> tuple[LatticeShift, ...]:
    result_ranges = []
    for axis in range(3):
        left_values = [point[axis] for point in left.vertices]
        right_values = [point[axis] for point in right.vertices]
        low = _ceil_fraction(min(left_values) - max(right_values))
        high = _floor_fraction(max(left_values) - min(right_values))
        if low > high:
            return ()
        result_ranges.append(range(low, high + 1))
    return tuple(tuple(value) for value in itertools.product(*result_ranges))  # type: ignore[return-value]


def _interiors_separated(
    left: _TileGeometry,
    right: _TileGeometry,
    shift: LatticeShift,
    resources: LtaNaturalTilingResources,
    axis_counter: list[int],
) -> bool:
    translated_right = tuple(translate(point, shift) for point in right.vertices)
    axes: set[AxisKey] = set()
    for normal, _ in left.outward_planes + right.outward_planes:
        key = _axis_key(normal)
        if key is not None:
            axes.add(key)
    left_directions = tuple(subtract(end, start) for start, end in left.edges)
    right_directions = tuple(subtract(end, start) for start, end in right.edges)
    for direction_left in left_directions:
        for direction_right in right_directions:
            key = _axis_key(cross(direction_left, direction_right))
            if key is not None:
                axes.add(key)
    for key in sorted(axes):
        axis_counter[0] += 1
        if axis_counter[0] > resources.max_sat_axes:
            raise LtaNaturalTilingResourceError("Exact SAT axis count exceeds max_sat_axes.")
        axis = _axis_from_key(key)
        left_values = tuple(dot(point, axis) for point in left.vertices)
        right_values = tuple(dot(point, axis) for point in translated_right)
        if max(left_values) <= min(right_values) or max(right_values) <= min(left_values):
            return True
    return False


def _certify_convex_partition(
    complex_: PeriodicCellComplex,
    index: PrimitiveRingIndex,
    embedding: PeriodicNetEmbedding,
    face_keys: Sequence[PrimitiveRingKey],
    resources: LtaNaturalTilingResources,
) -> LtaConvexPartitionCertificate:
    geometries = tuple(_tile_geometry(shell, index, embedding, face_keys) for shell in complex_.tile_shells)
    pair_count = 0
    axis_counter = [0]
    for left_index, left in enumerate(geometries):
        for right_index in range(left_index, len(geometries)):
            right = geometries[right_index]
            for shift in _translation_candidates(left, right):
                if left_index == right_index and shift == ZERO_SHIFT:
                    continue
                if left_index == right_index and shift < ZERO_SHIFT:
                    continue
                pair_count += 1
                if pair_count > resources.max_periodic_tile_pairs:
                    raise LtaNaturalTilingResourceError("Periodic tile-pair count exceeds max_periodic_tile_pairs.")
                if not _interiors_separated(left, right, shift, resources, axis_counter):
                    raise LtaNaturalTilingInvariantError(
                        f"LTA tiles {left_index} and {right_index}+{shift} have overlapping interiors."
                    )
    total = sum((geometry.volume for geometry in geometries), Fraction(0))
    if total != 1:
        raise LtaNaturalTilingInvariantError("Exact LTA tile volumes do not close the primitive cell.")
    tile_certificates = tuple(
        LtaConvexTileCertificate(
            geometry.tile_index,
            geometry.signature,
            len(geometry.vertices),
            len(geometry.edges),
            len(complex_.tile_shells[geometry.tile_index].face_incidences),
            geometry.volume,
            geometry.interior,
            len(geometry.outward_planes),
        )
        for geometry in geometries
    )
    # Pairwise periodic interior-disjointness plus exact total volume one excludes
    # an open positive-measure void inside the unit three-torus.
    return LtaConvexPartitionCertificate(
        complex_.digest,
        tile_certificates,
        pair_count,
        axis_counter[0],
        total,
        True,
        True,
    )


def _multiplicities(shells: Sequence[PeriodicTileShell]) -> tuple[LtaTileMultiplicity, ...]:
    counts: Counter[LtaTileSignature] = Counter()
    for shell in shells:
        parsed = []
        for item in shell.label.split("."):
            size, count = item.split("^")
            parsed.append((int(size), int(count)))
        counts[LtaTileSignature(tuple(parsed))] += 1
    return tuple(LtaTileMultiplicity(signature, count) for signature, count in sorted(counts.items()))


def _reduced_ratio(multiplicities: Sequence[LtaTileMultiplicity]) -> tuple[int, ...]:
    values = [item.count for item in multiplicities]
    divisor = 0
    for value in values:
        divisor = gcd(divisor, value)
    return tuple(value // divisor for value in values)


def _build_bound(
    topology: FrameworkTopology,
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    embedding: PeriodicNetEmbedding,
    edge_certificate_digest: str,
    bound: int,
    resources: LtaNaturalTilingResources,
    reference: _BoundBuild | None = None,
) -> _BoundBuild:
    catalog = enumerate_primitive_rings(topology, options=PrimitiveRingOptions(max_ring_size=bound))
    if len(catalog.rings) > resources.max_rings_per_bound:
        raise LtaNaturalTilingResourceError("Primitive-ring count exceeds max_rings_per_bound.")
    index = build_primitive_ring_index(catalog)
    domains = tuple(
        RingStrengthDomain(
            ring.key,
            max_component_size=ring.size - 1,
            placement_domain=EdgeIncidencePlacementDomain(1),
        )
        for ring in catalog.rings
    )
    strength = build_ring_strength_catalog(index, domains)
    status_by_key = {result.target_placement.ring_key: result.status for result in strength.results}
    geometry_by_key = {
        ring.key: _strict_convex_planar_status(_ring_coordinates(index, embedding, ring.key))
        for ring in catalog.rings
    }
    selected_keys = tuple(
        ring.key
        for ring in catalog.rings
        if status_by_key[ring.key] is RingStrengthStatus.STRONG_IN_DOMAIN
        and geometry_by_key[ring.key] is LtaRingGeometryStatus.STRICTLY_CONVEX_PLANAR
    )
    if len(selected_keys) > resources.max_selected_faces:
        raise LtaNaturalTilingResourceError("Selected face count exceeds max_selected_faces.")
    excluded_strong_nonplanar = tuple(
        ring.key
        for ring in catalog.rings
        if status_by_key[ring.key] is RingStrengthStatus.STRONG_IN_DOMAIN
        and geometry_by_key[ring.key] is LtaRingGeometryStatus.NONPLANAR
    )
    ring_counts = tuple(sorted(Counter(ring.size for ring in catalog.rings).items()))
    strength_counts_counter = Counter((ring.size, status_by_key[ring.key].value) for ring in catalog.rings)
    geometry_counts_counter = Counter((ring.size, geometry_by_key[ring.key].value) for ring in catalog.rings)
    selected_counts = tuple(sorted(Counter(index.ring_for_key(key).size for key in selected_keys).items()))
    selected_digests = tuple(_digest(_ring_key_payload(key)) for key in selected_keys)
    excluded_digests = tuple(_digest(_ring_key_payload(key)) for key in excluded_strong_nonplanar)

    # Proof-preserving reuse: once a lower-bound build has certified the exact
    # scientific face keys, every downstream construction is a deterministic
    # function of those keys, the fixed net embedding, and the complete group.
    # Higher bounds still rebuild rings, strength, and exact geometry; reuse is
    # admitted only after byte-for-byte stable-key equality is proven.
    if reference is not None and selected_digests == reference.observation.selected_ring_key_digests:
        base = reference.observation
        observation = LtaBoundObservation(
            bound,
            ring_counts,
            tuple((size, status, count) for (size, status), count in sorted(strength_counts_counter.items())),
            tuple((size, status, count) for (size, status), count in sorted(geometry_counts_counter.items())),
            selected_counts,
            selected_digests,
            excluded_digests,
            base.cell_counts,
            base.tile_multiplicities,
            base.reduced_multiplicity_ratio,
            base.complex_scientific_key,
            base.partition_certificate_digest,
            base.partition_total_fractional_volume,
            base.partition_pair_candidate_count,
            base.partition_axis_test_count,
            base.tile_fractional_volumes,
            base.symmetry_order,
            base.symmetry_preserved,
            base.symmetry_composition_check_count,
        )
        return _BoundBuild(observation, reference.complex_, reference.partition, index)

    certificates, witnesses = _build_face_certificates(
        view, embedding, index, edge_certificate_digest, selected_keys, resources
    )
    shells = _build_tile_shells(index, embedding, selected_keys, resources)
    complex_ = build_periodic_cell_complex(view, embedding, index, certificates, witnesses, shells)
    symmetry_preserved, composition_checks = _direct_symmetry_certificate(
        complex_, view, discovery, index, resources
    )
    partition = _certify_convex_partition(complex_, index, embedding, selected_keys, resources)
    multiplicities = _multiplicities(shells)
    observation = LtaBoundObservation(
        bound,
        ring_counts,
        tuple((size, status, count) for (size, status), count in sorted(strength_counts_counter.items())),
        tuple((size, status, count) for (size, status), count in sorted(geometry_counts_counter.items())),
        selected_counts,
        selected_digests,
        excluded_digests,
        complex_.cell_counts,
        multiplicities,
        _reduced_ratio(multiplicities),
        _complex_scientific_key(complex_, selected_keys),
        partition.digest,
        partition.total_fractional_volume,
        partition.periodic_pair_candidate_count,
        partition.exact_axis_test_count,
        tuple(tile.fractional_volume for tile in partition.tiles),
        discovery.symmetry.order,
        symmetry_preserved,
        composition_checks,
    )
    return _BoundBuild(observation, complex_, partition, index)


def _expected_multiplicities() -> tuple[LtaTileMultiplicity, ...]:
    return (
        LtaTileMultiplicity(LtaTileSignature(((4, 6),)), 6),
        LtaTileMultiplicity(LtaTileSignature(((4, 6), (6, 8))), 2),
        LtaTileMultiplicity(LtaTileSignature(((4, 12), (6, 8), (8, 6))), 2),
    )



def build_lta_natural_tiling_reference(
    topology: FrameworkTopology,
    *,
    resources: LtaNaturalTilingResources | None = None,
) -> LtaNaturalTilingReference:
    """Build the exact ``K=8`` LTA tiling sources for downstream geometry.

    This is a transient construction helper, not a second persistent natural-
    tiling result.  The same exact LTA fingerprint, order-96 symmetry, edge-
    embedding, face, shell, and convex-partition gates used by Stage 10D are
    rerun before the sources are returned.
    """

    if not isinstance(topology, FrameworkTopology):
        raise LtaNaturalTilingInputError("topology must be a FrameworkTopology.")
    active = resources or LtaNaturalTilingResources()
    if not isinstance(active, LtaNaturalTilingResources):
        raise LtaNaturalTilingInputError("resources must be LtaNaturalTilingResources.")
    view = build_periodic_net_view(topology)
    if view.n_vertices != 48 or view.n_edges != 96 or any(int(value) != 4 for value in topology.degree):
        raise LtaNaturalTilingInputError("Topology does not match the unlabeled LTA quotient fingerprint.")
    if view.n_components != 1 or view.translation_rank != 3 or view.translation_index != 1:
        raise LtaNaturalTilingInputError("LTA reference requires one connected rank-three index-one net.")
    discovery = discover_periodic_net_symmetry(view)
    if discovery.symmetry.order != 96:
        raise LtaNaturalTilingInvariantError("The complete unlabeled LTA automorphism group must have order 96.")
    embedding = build_periodic_net_embedding(view, discovery)
    edge_certificate = certify_periodic_straight_edge_embedding(view, embedding)
    if not edge_certificate.certified:
        raise LtaNaturalTilingInvariantError("Authoritative LTA straight-edge embedding is not certified.")
    build = _build_bound(
        topology,
        view,
        discovery,
        embedding,
        edge_certificate.digest,
        8,
        active,
    )
    return LtaNaturalTilingReference(
        view, discovery, embedding, build.ring_index, build.complex_, build.partition
    )


def certify_lta_natural_tiling(
    topology: FrameworkTopology,
    *,
    bounds: Sequence[int] = (8, 10, 12),
    resources: LtaNaturalTilingResources | None = None,
) -> LtaNaturalTilingGate:
    """Rebuild and certify the unlabeled LTA natural tiling at finite bounds.

    The first backend intentionally recognizes the exact LTA quotient fingerprint
    ``V=48, E=96, degree=4`` and requires the complete exact automorphism group to
    have order 96.  It is not a generic natural-tiling constructor.
    """

    if not isinstance(topology, FrameworkTopology):
        raise LtaNaturalTilingInputError("topology must be a FrameworkTopology.")
    active = resources or LtaNaturalTilingResources()
    if not isinstance(active, LtaNaturalTilingResources):
        raise LtaNaturalTilingInputError("resources must be LtaNaturalTilingResources.")
    normalized_bounds = tuple(int(value) for value in bounds)
    if normalized_bounds != tuple(sorted(set(normalized_bounds))) or not normalized_bounds:
        raise LtaNaturalTilingInputError("bounds must be nonempty, strictly increasing, and unique.")
    if normalized_bounds != (8, 10, 12):
        raise LtaNaturalTilingInputError("The Stage-10D ground gate requires bounds exactly (8, 10, 12).")
    if len(normalized_bounds) > active.max_bounds:
        raise LtaNaturalTilingResourceError("Requested bounds exceed max_bounds.")

    view = build_periodic_net_view(topology)
    if view.n_vertices != 48 or view.n_edges != 96 or any(int(value) != 4 for value in topology.degree):
        raise LtaNaturalTilingInputError("Topology does not match the unlabeled LTA quotient fingerprint.")
    if view.n_components != 1 or view.translation_rank != 3 or view.translation_index != 1:
        raise LtaNaturalTilingInputError("LTA ground gate requires one connected rank-three index-one net.")
    discovery = discover_periodic_net_symmetry(view)
    if discovery.symmetry.order != 96:
        raise LtaNaturalTilingInvariantError("The complete unlabeled LTA automorphism group must have order 96.")
    embedding = build_periodic_net_embedding(view, discovery)
    edge_certificate = certify_periodic_straight_edge_embedding(view, embedding)
    if not edge_certificate.certified:
        raise LtaNaturalTilingInvariantError("Authoritative LTA straight-edge embedding is not certified.")

    build_list = []
    for bound in normalized_bounds:
        build_list.append(
            _build_bound(
                topology,
                view,
                discovery,
                embedding,
                edge_certificate.digest,
                bound,
                active,
                reference=build_list[0] if build_list else None,
            )
        )
    builds = tuple(build_list)
    observations = tuple(build.observation for build in builds)
    selected_faces_stable = len({item.selected_ring_key_digests for item in observations}) == 1
    tiling_stable = len({item.complex_scientific_key for item in observations}) == 1
    expected = _expected_multiplicities()
    expected_match = all(
        observation.tile_multiplicities == expected
        and observation.reduced_multiplicity_ratio == (3, 1, 1)
        and observation.cell_counts == (48, 96, 58, 10)
        and observation.symmetry_preserved
        and builds[position].partition.certified
        for position, observation in enumerate(observations)
    )
    status = (
        LtaNaturalTilingGateStatus.CERTIFIED
        if selected_faces_stable and tiling_stable and expected_match
        else LtaNaturalTilingGateStatus.REJECTED
    )
    return LtaNaturalTilingGate(
        topology.graph_digest,
        view.digest,
        discovery.symmetry.digest,
        embedding.digest,
        normalized_bounds,
        observations,
        expected,
        selected_faces_stable,
        tiling_stable,
        expected_match,
        status,
    )


__all__ = [
    "CANONICAL_LTA_GATE_SCHEMA",
    "CANONICAL_LTA_PARTITION_SCHEMA",
    "LTA_GATE_DIGEST_ALGORITHM",
    "LtaBoundObservation",
    "LtaConvexPartitionCertificate",
    "LtaConvexTileCertificate",
    "LtaNaturalTilingError",
    "LtaNaturalTilingGate",
    "LtaNaturalTilingGateStatus",
    "LtaNaturalTilingInputError",
    "LtaNaturalTilingInvariantError",
    "LtaNaturalTilingResourceError",
    "LtaNaturalTilingResources",
    "LtaNaturalTilingReference",
    "LtaNaturalTilingSerializationError",
    "LtaRingGeometryStatus",
    "LtaTileMultiplicity",
    "LtaTileSignature",
    "build_lta_natural_tiling_reference",
    "certify_lta_natural_tiling",
]
