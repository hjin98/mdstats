"""Source-bound embedded face placements and finite compatibility certificates.

Stage 8C separates scientific face identity from auxiliary PL disk witnesses.
The first backend exhausts all triangulations that use only the cyclic boundary
vertices, certifies each disk with exact rational predicates, records framework
penetration separately from disk embeddedness, computes algebraic ring--surface
intersection, and assembles finite witness constraints.

Algorithmic provenance
----------------------
Exact-sign decisions follow the robust-predicate principle of Shewchuk (1997).
The bounded spanning-disk semantics are motivated by Hass, Snoeyink, and Thurston
(2003): failure of a finite triangulation family is ``UNRESOLVED``, never a knot
theorem.  The linking certificate uses the standard equality between linking
number and oriented intersection with a spanning surface; the simplicial
intersection-theoretic viewpoint is described by Hsieh, Kauffman, and Tsau
(2017).  The finite boundary-vertex family, source binding, periodic broad-phase
composition, and constraint ownership are mdstats-specific.

References
----------
J. R. Shewchuk, Discrete Comput. Geom. 18, 305-363 (1997),
doi:10.1007/PL00009321.
J. Hass, J. Snoeyink, and W. P. Thurston, Discrete Comput. Geom. 29, 1-17
(2003), doi:10.1007/s00454-002-2707-6.
C.-C. Hsieh, L. H. Kauffman, and C.-M. Tsau, Asian J. Math. 21, 265-286
(2017), doi:10.4310/AJM.2017.v21.n2.a3.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import json
from numbers import Integral
from typing import Any, Iterable, Literal, Mapping, Sequence, TypeAlias

from ._periodic_graph import add_shift, coerce_lattice_shift
from ._periodic_spatial import (
    PeriodicAabbSupport,
    PeriodicImageCandidate,
    PeriodicSpatialCandidateSet,
    PeriodicSpatialMethod,
    PeriodicSpatialResources,
    build_periodic_overlap_candidates,
)
from ._robust_geometry import (
    ExactSegmentTriangleIntersection,
    ExactTriangleIntersection,
    IntersectionDimension,
    RationalVector3,
    RobustGeometryError,
    point_on_segment,
    segment_triangle_intersection,
    translate,
    triangle_normal,
    triangle_triangle_intersection,
)
from ._surface_mesh import (
    BoundaryTriangulation,
    SurfaceMeshError,
    enumerate_boundary_triangulations,
    validate_oriented_disk_triangulation,
)
from .framework_topology import FrameworkEdgeKey
from .net_symmetry import PeriodicNetSymmetry
from .periodic_cycle import CycleParameterization, RingPlacement
from .periodic_edge_intersection import PeriodicEdgeIntersectionCertificate
from .periodic_net_embedding import PeriodicNetEmbedding, ProjectedEdgeCurveModel
from .periodic_net_view import PeriodicNetView
from .primitive_ring import LatticeShift, LiftedVertexRef
from .primitive_ring_index import LiftedEdgeInstanceRef, PrimitiveRingIndex
from .primitive_ring_symmetry import PrimitiveRingSymmetryIndex

CANONICAL_FACE_PLACEMENT_SCHEMA = "mdstats.face-placement.v1"
CANONICAL_FACE_WITNESS_SCHEMA = "mdstats.face-embedding-witness.v1"
CANONICAL_FACE_CERTIFICATE_SCHEMA = "mdstats.face-placement-certificate.v1"
CANONICAL_FACE_PAIR_CERTIFICATE_SCHEMA = "mdstats.face-witness-pair-certificate.v1"
CANONICAL_FACE_CONSTRAINT_SYSTEM_SCHEMA = "mdstats.face-compatibility-constraints.v1"
FACE_CANDIDATE_DIGEST_ALGORITHM = "sha256-canonical-json-v1"

TriangleIndex: TypeAlias = tuple[int, int, int]


class FaceCandidateError(ValueError):
    """Base exception for embedded face construction and compatibility."""


class FaceCandidateInputError(FaceCandidateError):
    """Raised when source identities or face declarations are incompatible."""


class FaceCandidateResourceError(FaceCandidateError):
    """Raised transactionally before a declared finite resource limit is exceeded."""


class FaceCandidateSerializationError(FaceCandidateError):
    """Raised when a serialized certificate fails source replay."""


class FaceWitnessMethod(str, Enum):
    """Finite spanning-surface families supported by the first backend."""

    BOUNDARY_VERTEX_TRIANGULATION = "boundary-vertex-triangulation"


class FaceFrameworkContactKind(str, Enum):
    """Forbidden framework contact with one embedded disk witness."""

    TRANSVERSE_INTERIOR = "transverse-interior"
    ENDPOINT_ON_INTERIOR = "endpoint-on-interior"
    NONBOUNDARY_CONTACT = "nonboundary-contact"
    COPLANAR_OVERLAP = "coplanar-overlap"


class FaceWitnessRejectionKind(str, Enum):
    """Reason one finite triangulation failed to define an embedded periodic disk."""

    DEGENERATE_TRIANGLE = "degenerate-triangle"
    SURFACE_SELF_INTERSECTION = "surface-self-intersection"
    PERIODIC_SELF_INTERSECTION = "periodic-self-intersection"


class FacePlacementStatus(str, Enum):
    """Scientific status of one face placement under the finite witness family."""

    CERTIFIED_ADMISSIBLE = "certified-admissible"
    UNRESOLVED_NO_ADMISSIBLE_WITNESS = "unresolved-no-admissible-witness"
    UNRESOLVED_NO_EMBEDDED_WITNESS = "unresolved-no-embedded-witness"
    INVALID_REFERENCE_EMBEDDING = "invalid-reference-embedding"


class FaceWitnessPairStatus(str, Enum):
    """Semantics of one pair of particular disk witnesses."""

    PROVEN_LINKED_NONZERO_INTERSECTION = "proven-linked-nonzero-intersection"
    WITNESS_PAIR_INCOMPATIBLE = "witness-pair-incompatible"
    DISJOINT_DISK_WITNESS = "disjoint-disk-witness"
    COMPATIBLE_SHARED_BOUNDARY = "compatible-shared-boundary"
    UNRESOLVED_LINKING = "unresolved-linking"


class FaceConstraintKind(str, Enum):
    """Finite compatibility-system constraint semantics."""

    UNARY_FORBIDDEN = "unary-forbidden"
    PAIR_FORBIDDEN = "pair-forbidden"
    HIGHER_ORDER_FORBIDDEN = "higher-order-forbidden"
    UNRESOLVED = "unresolved"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _sha(value: str, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise FaceCandidateInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise FaceCandidateInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise FaceCandidateInputError(f"{name} must be positive.")
    return result


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _fraction_from_payload(value: Sequence[Any]) -> Fraction:
    if len(value) != 2:
        raise FaceCandidateSerializationError("Fraction payload must contain two integers.")
    return Fraction(int(value[0]), int(value[1]))


def _point_payload(point: RationalVector3) -> list[list[int]]:
    return [_fraction_payload(value) for value in point]


def _point_from_payload(payload: Sequence[Sequence[Any]]) -> RationalVector3:
    values = tuple(_fraction_from_payload(value) for value in payload)
    if len(values) != 3:
        raise FaceCandidateSerializationError("Point payload must contain three fractions.")
    return values  # type: ignore[return-value]


def _shift_payload(shift: LatticeShift) -> list[int]:
    return list(shift)


def _ring_placement_payload(placement: RingPlacement) -> dict[str, Any]:
    return {
        "topology_graph_digest": placement.topology_graph_digest,
        "ring_key": placement.ring_key.to_dict(),
        "image_shift": list(placement.image_shift),
    }


def _ring_placement_from_payload(payload: Mapping[str, Any]) -> RingPlacement:
    from .primitive_ring import PrimitiveRingKey

    return RingPlacement(
        str(payload["topology_graph_digest"]),
        PrimitiveRingKey.from_dict(payload["ring_key"]),
        tuple(int(value) for value in payload["image_shift"]),
    )


@dataclass(frozen=True, slots=True, eq=False)
class FacePlacement:
    """One oriented scientific 2-cell candidate independent of its mesh witness."""

    periodic_net_embedding_digest: str
    primitive_ring_catalog_digest: str
    ring_placement: RingPlacement
    orientation: Literal[-1, 1] = 1
    canonical_schema_version: str = field(
        default=CANONICAL_FACE_PLACEMENT_SCHEMA, compare=False
    )
    digest_algorithm: str = field(default=FACE_CANDIDATE_DIGEST_ALGORITHM, compare=False)
    digest: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        _sha(self.periodic_net_embedding_digest, name="periodic_net_embedding_digest")
        _sha(self.primitive_ring_catalog_digest, name="primitive_ring_catalog_digest")
        if not isinstance(self.ring_placement, RingPlacement):
            raise FaceCandidateInputError("ring_placement must be a RingPlacement.")
        if self.orientation not in (-1, 1):
            raise FaceCandidateInputError("orientation must be +1 or -1.")
        if self.canonical_schema_version != CANONICAL_FACE_PLACEMENT_SCHEMA:
            raise FaceCandidateInputError("Unsupported FacePlacement schema.")
        if self.digest_algorithm != FACE_CANDIDATE_DIGEST_ALGORITHM:
            raise FaceCandidateInputError("Unsupported FacePlacement digest algorithm.")
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FaceCandidateInputError("Stored FacePlacement digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FacePlacement) and self.digest == other.digest

    def __hash__(self) -> int:
        return hash(self.digest)

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "ring_placement": _ring_placement_payload(self.ring_placement),
            "orientation": self.orientation,
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FacePlacement":
        try:
            return cls(
                periodic_net_embedding_digest=str(payload["periodic_net_embedding_digest"]),
                primitive_ring_catalog_digest=str(payload["primitive_ring_catalog_digest"]),
                ring_placement=_ring_placement_from_payload(payload["ring_placement"]),
                orientation=int(payload["orientation"]),  # type: ignore[arg-type]
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except FaceCandidateError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FaceCandidateSerializationError("Invalid FacePlacement payload.") from exc


@dataclass(frozen=True, slots=True)
class FaceEmbeddingResources:
    """Transactional bounds for one face and finite compatibility construction."""

    max_boundary_vertices: int = 32
    max_triangulations: int = 100_000
    max_exact_triangle_tests: int = 5_000_000
    max_framework_contact_tests: int = 5_000_000
    max_pair_witness_combinations: int = 100_000

    def __post_init__(self) -> None:
        for name in (
            "max_boundary_vertices",
            "max_triangulations",
            "max_exact_triangle_tests",
            "max_framework_contact_tests",
            "max_pair_witness_combinations",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, slots=True)
class FaceFrameworkContact:
    """One forbidden exact framework contact with a disk witness."""

    edge_instance: LiftedEdgeInstanceRef
    triangle_index: int
    relative_image_shift: LatticeShift
    contact_kind: FaceFrameworkContactKind
    intersection_dimension: IntersectionDimension
    segment_interval: tuple[Fraction, Fraction] | None
    points_fractional: tuple[RationalVector3, ...]
    transverse_sign: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.edge_instance, LiftedEdgeInstanceRef):
            raise FaceCandidateInputError("edge_instance must be a LiftedEdgeInstanceRef.")
        object.__setattr__(self, "triangle_index", _nonnegative(self.triangle_index, name="triangle_index"))
        try:
            shift = coerce_lattice_shift(self.relative_image_shift, name="relative_image_shift")
        except ValueError as exc:
            raise FaceCandidateInputError(str(exc)) from exc
        dimension = IntersectionDimension(self.intersection_dimension)
        kind = FaceFrameworkContactKind(self.contact_kind)
        interval = self.segment_interval
        if interval is not None:
            interval = (Fraction(interval[0]), Fraction(interval[1]))
            if interval[0] > interval[1]:
                raise FaceCandidateInputError("segment_interval must be ordered.")
        points = tuple(tuple(Fraction(value) for value in point) for point in self.points_fractional)
        if any(len(point) != 3 for point in points):
            raise FaceCandidateInputError("Framework contact points must be 3-vectors.")
        if self.transverse_sign not in (-1, 0, 1):
            raise FaceCandidateInputError("transverse_sign must be -1, 0, or +1.")
        object.__setattr__(self, "relative_image_shift", shift)
        object.__setattr__(self, "contact_kind", kind)
        object.__setattr__(self, "intersection_dimension", dimension)
        object.__setattr__(self, "segment_interval", interval)
        object.__setattr__(self, "points_fractional", points)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_instance": {
                "topology_graph_digest": self.edge_instance.topology_graph_digest,
                "edge_key": self.edge_instance.edge_key.to_dict(),
                "anchor_shift": list(self.edge_instance.anchor_shift),
            },
            "triangle_index": self.triangle_index,
            "relative_image_shift": list(self.relative_image_shift),
            "contact_kind": self.contact_kind.value,
            "intersection_dimension": int(self.intersection_dimension),
            "segment_interval": None
            if self.segment_interval is None
            else [_fraction_payload(value) for value in self.segment_interval],
            "points_fractional": [_point_payload(point) for point in self.points_fractional],
            "transverse_sign": self.transverse_sign,
        }


@dataclass(frozen=True, slots=True)
class FaceWitnessRejection:
    """Deterministic rejection of one triangulation candidate."""

    candidate_id: int
    triangles: BoundaryTriangulation
    rejection_kind: FaceWitnessRejectionKind
    relative_image_shift: LatticeShift = (0, 0, 0)
    left_triangle_index: int | None = None
    right_triangle_index: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _nonnegative(self.candidate_id, name="candidate_id"))
        triangles = tuple(tuple(int(value) for value in triangle) for triangle in self.triangles)
        if any(len(triangle) != 3 for triangle in triangles):
            raise FaceCandidateInputError("Rejection triangles must be index triples.")
        try:
            shift = coerce_lattice_shift(self.relative_image_shift, name="relative_image_shift")
        except ValueError as exc:
            raise FaceCandidateInputError(str(exc)) from exc
        for name in ("left_triangle_index", "right_triangle_index"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonnegative(value, name=name))
        object.__setattr__(self, "triangles", triangles)
        object.__setattr__(self, "rejection_kind", FaceWitnessRejectionKind(self.rejection_kind))
        object.__setattr__(self, "relative_image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "triangles": [list(triangle) for triangle in self.triangles],
            "rejection_kind": self.rejection_kind.value,
            "relative_image_shift": list(self.relative_image_shift),
            "left_triangle_index": self.left_triangle_index,
            "right_triangle_index": self.right_triangle_index,
        }


@dataclass(frozen=True, slots=True, eq=False)
class FaceEmbeddingWitness:
    """One exact embedded periodic PL disk for a scientific face placement.

    Framework contacts do not invalidate disk embeddedness.  They make this
    particular witness inadmissible as a face in the current framework, while the
    same disk remains usable for rigorous ring--surface linking certificates.
    """

    face_placement: FacePlacement
    witness_id: int
    method: FaceWitnessMethod
    triangles: BoundaryTriangulation
    periodic_self_candidate_set_digest: str
    framework_candidate_set_digest: str
    framework_contacts: tuple[FaceFrameworkContact, ...]
    canonical_schema_version: str = CANONICAL_FACE_WITNESS_SCHEMA
    digest_algorithm: str = FACE_CANDIDATE_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.face_placement, FacePlacement):
            raise FaceCandidateInputError("face_placement must be a FacePlacement.")
        witness_id = _nonnegative(self.witness_id, name="witness_id")
        method = FaceWitnessMethod(self.method)
        triangles = tuple(tuple(int(value) for value in triangle) for triangle in self.triangles)
        _sha(self.periodic_self_candidate_set_digest, name="periodic_self_candidate_set_digest")
        _sha(self.framework_candidate_set_digest, name="framework_candidate_set_digest")
        contacts = tuple(self.framework_contacts)
        if any(not isinstance(value, FaceFrameworkContact) for value in contacts):
            raise FaceCandidateInputError("framework_contacts contain an invalid record.")
        if self.canonical_schema_version != CANONICAL_FACE_WITNESS_SCHEMA:
            raise FaceCandidateInputError("Unsupported FaceEmbeddingWitness schema.")
        if self.digest_algorithm != FACE_CANDIDATE_DIGEST_ALGORITHM:
            raise FaceCandidateInputError("Unsupported FaceEmbeddingWitness digest algorithm.")
        object.__setattr__(self, "witness_id", witness_id)
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "triangles", triangles)
        object.__setattr__(self, "framework_contacts", contacts)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FaceCandidateInputError("Stored FaceEmbeddingWitness digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FaceEmbeddingWitness) and self.digest == other.digest

    def __hash__(self) -> int:
        return hash(self.digest)

    @property
    def admissible(self) -> bool:
        return not self.framework_contacts

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "face_placement": self.face_placement.to_dict(),
            "witness_id": self.witness_id,
            "method": self.method.value,
            "triangles": [list(triangle) for triangle in self.triangles],
            "periodic_self_candidate_set_digest": self.periodic_self_candidate_set_digest,
            "framework_candidate_set_digest": self.framework_candidate_set_digest,
            "framework_contacts": [contact.to_dict() for contact in self.framework_contacts],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


@dataclass(frozen=True, slots=True, eq=False)
class FacePlacementCertificate:
    """Finite exact witness-family result for one scientific face placement."""

    periodic_net_view_digest: str
    topology_graph_digest: str
    periodic_net_embedding_digest: str
    primitive_ring_catalog_digest: str
    periodic_edge_intersection_certificate_digest: str
    face_placement: FacePlacement
    triangulation_candidate_count: int
    witnesses: tuple[FaceEmbeddingWitness, ...]
    rejections: tuple[FaceWitnessRejection, ...]
    status: FacePlacementStatus
    canonical_schema_version: str = CANONICAL_FACE_CERTIFICATE_SCHEMA
    digest_algorithm: str = FACE_CANDIDATE_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "periodic_net_view_digest",
            "topology_graph_digest",
            "periodic_net_embedding_digest",
            "primitive_ring_catalog_digest",
            "periodic_edge_intersection_certificate_digest",
        ):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.face_placement, FacePlacement):
            raise FaceCandidateInputError("face_placement must be a FacePlacement.")
        count = _nonnegative(self.triangulation_candidate_count, name="triangulation_candidate_count")
        witnesses = tuple(self.witnesses)
        rejections = tuple(self.rejections)
        if any(not isinstance(value, FaceEmbeddingWitness) for value in witnesses):
            raise FaceCandidateInputError("witnesses contain an invalid record.")
        if any(value.face_placement != self.face_placement for value in witnesses):
            raise FaceCandidateInputError("Every witness must belong to face_placement.")
        if any(not isinstance(value, FaceWitnessRejection) for value in rejections):
            raise FaceCandidateInputError("rejections contain an invalid record.")
        if len(witnesses) + len(rejections) != count and FacePlacementStatus(self.status) is not FacePlacementStatus.INVALID_REFERENCE_EMBEDDING:
            raise FaceCandidateInputError("Witness and rejection counts must exhaust the finite triangulation family.")
        status = FacePlacementStatus(self.status)
        if status is FacePlacementStatus.CERTIFIED_ADMISSIBLE and not any(value.admissible for value in witnesses):
            raise FaceCandidateInputError("Certified face requires an admissible witness.")
        if status is FacePlacementStatus.UNRESOLVED_NO_ADMISSIBLE_WITNESS and (not witnesses or any(value.admissible for value in witnesses)):
            raise FaceCandidateInputError("No-admissible status requires embedded but penetrated witnesses only.")
        if status is FacePlacementStatus.UNRESOLVED_NO_EMBEDDED_WITNESS and witnesses:
            raise FaceCandidateInputError("No-embedded status cannot contain witnesses.")
        if self.canonical_schema_version != CANONICAL_FACE_CERTIFICATE_SCHEMA:
            raise FaceCandidateInputError("Unsupported FacePlacementCertificate schema.")
        if self.digest_algorithm != FACE_CANDIDATE_DIGEST_ALGORITHM:
            raise FaceCandidateInputError("Unsupported face-certificate digest algorithm.")
        object.__setattr__(self, "triangulation_candidate_count", count)
        object.__setattr__(self, "witnesses", witnesses)
        object.__setattr__(self, "rejections", rejections)
        object.__setattr__(self, "status", status)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FaceCandidateInputError("Stored FacePlacementCertificate digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FacePlacementCertificate) and self.digest == other.digest

    @property
    def admissible_witnesses(self) -> tuple[FaceEmbeddingWitness, ...]:
        return tuple(value for value in self.witnesses if value.admissible)

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "periodic_edge_intersection_certificate_digest": self.periodic_edge_intersection_certificate_digest,
            "face_placement": self.face_placement.to_dict(),
            "triangulation_candidate_count": self.triangulation_candidate_count,
            "witnesses": [value.to_dict() for value in self.witnesses],
            "rejections": [value.to_dict() for value in self.rejections],
            "status": self.status.value,
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
        view: PeriodicNetView,
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        edge_certificate: PeriodicEdgeIntersectionCertificate,
        method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
        spatial_resources: PeriodicSpatialResources | None = None,
        resources: FaceEmbeddingResources | None = None,
    ) -> "FacePlacementCertificate":
        """Replay and verify one serialized finite face certificate."""

        try:
            face = FacePlacement.from_dict(payload["face_placement"])
            rebuilt = build_face_placement_certificate(
                view,
                embedding,
                ring_index,
                edge_certificate,
                face,
                method=method,
                spatial_resources=spatial_resources,
                resources=resources,
            )
            if rebuilt.to_dict() != dict(payload):
                raise FaceCandidateSerializationError(
                    "Serialized face certificate is not canonical for the supplied sources."
                )
            return rebuilt
        except FaceCandidateError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FaceCandidateSerializationError(
                "Invalid FacePlacementCertificate payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class FaceAlgebraicIntersection:
    """Algebraic ring--surface intersection for one relative periodic image."""

    relative_image_shift: LatticeShift
    intersection_number: int
    transverse_crossing_count: int
    unresolved_contact_count: int

    def __post_init__(self) -> None:
        try:
            shift = coerce_lattice_shift(self.relative_image_shift, name="relative_image_shift")
        except ValueError as exc:
            raise FaceCandidateInputError(str(exc)) from exc
        object.__setattr__(self, "relative_image_shift", shift)
        object.__setattr__(self, "intersection_number", int(self.intersection_number))
        object.__setattr__(self, "transverse_crossing_count", _nonnegative(self.transverse_crossing_count, name="transverse_crossing_count"))
        object.__setattr__(self, "unresolved_contact_count", _nonnegative(self.unresolved_contact_count, name="unresolved_contact_count"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_image_shift": list(self.relative_image_shift),
            "intersection_number": self.intersection_number,
            "transverse_crossing_count": self.transverse_crossing_count,
            "unresolved_contact_count": self.unresolved_contact_count,
        }


@dataclass(frozen=True, slots=True, eq=False)
class FaceWitnessPairCertificate:
    """Exact periodic relation between two particular embedded disk witnesses."""

    left_witness_digest: str
    right_witness_digest: str
    ring_surface_candidate_set_digest: str
    surface_surface_candidate_set_digest: str
    algebraic_intersections: tuple[FaceAlgebraicIntersection, ...]
    incompatible_surface_contact_count: int
    allowed_shared_boundary_contact_count: int
    status: FaceWitnessPairStatus
    canonical_schema_version: str = CANONICAL_FACE_PAIR_CERTIFICATE_SCHEMA
    digest_algorithm: str = FACE_CANDIDATE_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "left_witness_digest",
            "right_witness_digest",
            "ring_surface_candidate_set_digest",
            "surface_surface_candidate_set_digest",
        ):
            _sha(getattr(self, name), name=name)
        values = tuple(self.algebraic_intersections)
        if any(not isinstance(value, FaceAlgebraicIntersection) for value in values):
            raise FaceCandidateInputError("algebraic_intersections contain an invalid record.")
        incompatible = _nonnegative(self.incompatible_surface_contact_count, name="incompatible_surface_contact_count")
        allowed = _nonnegative(self.allowed_shared_boundary_contact_count, name="allowed_shared_boundary_contact_count")
        status = FaceWitnessPairStatus(self.status)
        if status is FaceWitnessPairStatus.PROVEN_LINKED_NONZERO_INTERSECTION and not any(value.intersection_number != 0 for value in values):
            raise FaceCandidateInputError("Linked status requires a nonzero algebraic intersection.")
        if status is FaceWitnessPairStatus.WITNESS_PAIR_INCOMPATIBLE and incompatible == 0:
            raise FaceCandidateInputError("Incompatible status requires a forbidden surface contact.")
        if self.canonical_schema_version != CANONICAL_FACE_PAIR_CERTIFICATE_SCHEMA:
            raise FaceCandidateInputError("Unsupported pair-certificate schema.")
        object.__setattr__(self, "algebraic_intersections", values)
        object.__setattr__(self, "incompatible_surface_contact_count", incompatible)
        object.__setattr__(self, "allowed_shared_boundary_contact_count", allowed)
        object.__setattr__(self, "status", status)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FaceCandidateInputError("Stored pair-certificate digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FaceWitnessPairCertificate) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "left_witness_digest": self.left_witness_digest,
            "right_witness_digest": self.right_witness_digest,
            "ring_surface_candidate_set_digest": self.ring_surface_candidate_set_digest,
            "surface_surface_candidate_set_digest": self.surface_surface_candidate_set_digest,
            "algebraic_intersections": [value.to_dict() for value in self.algebraic_intersections],
            "incompatible_surface_contact_count": self.incompatible_surface_contact_count,
            "allowed_shared_boundary_contact_count": self.allowed_shared_boundary_contact_count,
            "status": self.status.value,
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
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        left_witness: FaceEmbeddingWitness,
        right_witness: FaceEmbeddingWitness,
        method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
        spatial_resources: PeriodicSpatialResources | None = None,
        resources: FaceEmbeddingResources | None = None,
    ) -> "FaceWitnessPairCertificate":
        """Replay and verify one serialized witness-pair certificate."""

        try:
            rebuilt = certify_face_witness_pair(
                embedding,
                ring_index,
                left_witness,
                right_witness,
                method=method,
                spatial_resources=spatial_resources,
                resources=resources,
            )
            if rebuilt.to_dict() != dict(payload):
                raise FaceCandidateSerializationError(
                    "Serialized witness-pair certificate is not canonical for the supplied sources."
                )
            return rebuilt
        except FaceCandidateError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FaceCandidateSerializationError(
                "Invalid FaceWitnessPairCertificate payload."
            ) from exc


@dataclass(frozen=True, order=True, slots=True)
class FaceWitnessAssignment:
    """One finite-domain value: a particular witness assigned to one face."""

    face_placement_digest: str
    witness_id: int
    witness_digest: str

    def __post_init__(self) -> None:
        _sha(self.face_placement_digest, name="face_placement_digest")
        object.__setattr__(self, "witness_id", _nonnegative(self.witness_id, name="witness_id"))
        _sha(self.witness_digest, name="witness_digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_placement_digest": self.face_placement_digest,
            "witness_id": self.witness_id,
            "witness_digest": self.witness_digest,
        }


@dataclass(frozen=True, slots=True)
class FaceCompatibilityConstraint:
    """Unary, pairwise, or higher-order restriction on witness assignments."""

    kind: FaceConstraintKind
    assignments: tuple[FaceWitnessAssignment, ...]
    reason: str
    certificate_digest: str | None = None

    def __post_init__(self) -> None:
        kind = FaceConstraintKind(self.kind)
        assignments = tuple(sorted(self.assignments))
        if not assignments or len({value.face_placement_digest for value in assignments}) != len(assignments):
            raise FaceCandidateInputError("A constraint requires one assignment per distinct face.")
        expected_size = {
            FaceConstraintKind.UNARY_FORBIDDEN: 1,
            FaceConstraintKind.PAIR_FORBIDDEN: 2,
        }.get(kind)
        if expected_size is not None and len(assignments) != expected_size:
            raise FaceCandidateInputError(f"{kind.value} requires {expected_size} assignments.")
        if kind is FaceConstraintKind.HIGHER_ORDER_FORBIDDEN and len(assignments) < 3:
            raise FaceCandidateInputError("Higher-order constraints require at least three assignments.")
        if not isinstance(self.reason, str) or not self.reason:
            raise FaceCandidateInputError("Constraint reason must be nonempty.")
        if self.certificate_digest is not None:
            _sha(self.certificate_digest, name="certificate_digest")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "assignments", assignments)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "assignments": [value.to_dict() for value in self.assignments],
            "reason": self.reason,
            "certificate_digest": self.certificate_digest,
        }


@dataclass(frozen=True, order=True, slots=True)
class FaceSymmetryRelation:
    """Scientific face image under one exact periodic-net operation."""

    operation_index: int
    source_face_digest: str
    target_face_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_index", _nonnegative(self.operation_index, name="operation_index"))
        _sha(self.source_face_digest, name="source_face_digest")
        _sha(self.target_face_digest, name="target_face_digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_index": self.operation_index,
            "source_face_digest": self.source_face_digest,
            "target_face_digest": self.target_face_digest,
        }


@dataclass(frozen=True, order=True, slots=True)
class FaceWitnessSymmetryRelation:
    """Exact boundary-triangulation image between equivalent witnesses."""

    operation_index: int
    source_witness_digest: str
    target_witness_digest: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "operation_index", _nonnegative(self.operation_index, name="operation_index"))
        _sha(self.source_witness_digest, name="source_witness_digest")
        _sha(self.target_witness_digest, name="target_witness_digest")

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_index": self.operation_index,
            "source_witness_digest": self.source_witness_digest,
            "target_witness_digest": self.target_witness_digest,
        }


@dataclass(frozen=True, slots=True, eq=False)
class FaceCompatibilityConstraintSystem:
    """Finite face/witness domain with hard, unresolved, and symmetry relations."""

    face_certificate_digests: tuple[str, ...]
    assignments: tuple[FaceWitnessAssignment, ...]
    pair_certificates: tuple[FaceWitnessPairCertificate, ...]
    constraints: tuple[FaceCompatibilityConstraint, ...]
    face_symmetry_relations: tuple[FaceSymmetryRelation, ...] = ()
    witness_symmetry_relations: tuple[FaceWitnessSymmetryRelation, ...] = ()
    canonical_schema_version: str = CANONICAL_FACE_CONSTRAINT_SYSTEM_SCHEMA
    digest_algorithm: str = FACE_CANDIDATE_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        faces = tuple(sorted(self.face_certificate_digests))
        if len(set(faces)) != len(faces):
            raise FaceCandidateInputError("face_certificate_digests must be unique.")
        for value in faces:
            _sha(value, name="face_certificate_digest")
        assignments = tuple(sorted(self.assignments))
        if len(set(assignments)) != len(assignments):
            raise FaceCandidateInputError("assignments must be unique.")
        pairs = tuple(sorted(self.pair_certificates, key=lambda value: value.digest))
        constraints = tuple(sorted(self.constraints, key=lambda value: _canonical_json(value.to_dict())))
        face_relations = tuple(sorted(set(self.face_symmetry_relations)))
        witness_relations = tuple(sorted(set(self.witness_symmetry_relations)))
        if self.canonical_schema_version != CANONICAL_FACE_CONSTRAINT_SYSTEM_SCHEMA:
            raise FaceCandidateInputError("Unsupported compatibility-system schema.")
        object.__setattr__(self, "face_certificate_digests", faces)
        object.__setattr__(self, "assignments", assignments)
        object.__setattr__(self, "pair_certificates", pairs)
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "face_symmetry_relations", face_relations)
        object.__setattr__(self, "witness_symmetry_relations", witness_relations)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FaceCandidateInputError("Stored compatibility-system digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FaceCompatibilityConstraintSystem) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "face_certificate_digests": list(self.face_certificate_digests),
            "assignments": [value.to_dict() for value in self.assignments],
            "pair_certificates": [value.to_dict() for value in self.pair_certificates],
            "constraints": [value.to_dict() for value in self.constraints],
            "face_symmetry_relations": [value.to_dict() for value in self.face_symmetry_relations],
            "witness_symmetry_relations": [value.to_dict() for value in self.witness_symmetry_relations],
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
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        certificates: Sequence[FacePlacementCertificate],
        method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
        spatial_resources: PeriodicSpatialResources | None = None,
        resources: FaceEmbeddingResources | None = None,
        symmetry: PeriodicNetSymmetry | None = None,
        ring_symmetry: PrimitiveRingSymmetryIndex | None = None,
    ) -> "FaceCompatibilityConstraintSystem":
        """Replay and verify a serialized finite compatibility system."""

        try:
            higher_order = tuple(
                tuple(
                    FaceWitnessAssignment(
                        str(item["face_placement_digest"]),
                        int(item["witness_id"]),
                        str(item["witness_digest"]),
                    )
                    for item in constraint["assignments"]
                )
                for constraint in payload["constraints"]
                if FaceConstraintKind(str(constraint["kind"]))
                is FaceConstraintKind.HIGHER_ORDER_FORBIDDEN
            )
            rebuilt = build_face_compatibility_constraint_system(
                embedding,
                ring_index,
                certificates,
                method=method,
                spatial_resources=spatial_resources,
                resources=resources,
                higher_order_forbidden=higher_order,
                symmetry=symmetry,
                ring_symmetry=ring_symmetry,
            )
            if rebuilt.to_dict() != dict(payload):
                raise FaceCandidateSerializationError(
                    "Serialized compatibility system is not canonical for the supplied sources."
                )
            return rebuilt
        except FaceCandidateError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FaceCandidateSerializationError(
                "Invalid FaceCompatibilityConstraintSystem payload."
            ) from exc


@dataclass(slots=True)
class _FaceWorkspace:
    resources: FaceEmbeddingResources
    exact_triangle_tests: int = 0
    framework_contact_tests: int = 0

    def triangle_test(self) -> None:
        self.exact_triangle_tests += 1
        if self.exact_triangle_tests > self.resources.max_exact_triangle_tests:
            raise FaceCandidateResourceError("Exact triangle-test count exceeded max_exact_triangle_tests.")

    def framework_test(self) -> None:
        self.framework_contact_tests += 1
        if self.framework_contact_tests > self.resources.max_framework_contact_tests:
            raise FaceCandidateResourceError("Framework contact-test count exceeded max_framework_contact_tests.")


@dataclass(frozen=True, slots=True)
class _BoundaryGeometry:
    refs: tuple[LiftedVertexRef, ...]
    coordinates: tuple[RationalVector3, ...]
    edges: tuple[LiftedEdgeInstanceRef, ...]
    edge_ref_pairs: frozenset[frozenset[LiftedVertexRef]]


def _validate_sources(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    edge_certificate: PeriodicEdgeIntersectionCertificate,
) -> None:
    if not isinstance(view, PeriodicNetView):
        raise FaceCandidateInputError("view must be a PeriodicNetView.")
    if not isinstance(embedding, PeriodicNetEmbedding):
        raise FaceCandidateInputError("embedding must be a PeriodicNetEmbedding.")
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise FaceCandidateInputError("ring_index must be a PrimitiveRingIndex.")
    if not isinstance(edge_certificate, PeriodicEdgeIntersectionCertificate):
        raise FaceCandidateInputError("edge_certificate must be a PeriodicEdgeIntersectionCertificate.")
    if embedding.edge_curve_model is not ProjectedEdgeCurveModel.STRAIGHT_SEGMENT:
        raise FaceCandidateInputError("Stage 8C first backend requires straight projected edges.")
    if (
        embedding.periodic_net_view_digest != view.digest
        or embedding.topology_graph_digest != view.source_graph_digest
        or ring_index.topology_graph_digest != view.source_graph_digest
        or edge_certificate.periodic_net_view_digest != view.digest
        or edge_certificate.periodic_net_embedding_digest != embedding.digest
        or edge_certificate.topology_graph_digest != view.source_graph_digest
    ):
        raise FaceCandidateInputError("Face sources do not share exact view/topology/embedding identity.")


def make_face_placement(
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    ring_placement: RingPlacement,
    *,
    orientation: Literal[-1, 1] = 1,
) -> FacePlacement:
    """Construct one source-bound scientific face identity."""

    if ring_placement.topology_graph_digest != ring_index.topology_graph_digest:
        raise FaceCandidateInputError("ring_placement belongs to a different topology graph.")
    ring_index.ring_for_key(ring_placement.ring_key)
    return FacePlacement(
        periodic_net_embedding_digest=embedding.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        ring_placement=ring_placement,
        orientation=orientation,
    )


def _boundary_geometry(
    face: FacePlacement,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
) -> _BoundaryGeometry:
    if face.periodic_net_embedding_digest != embedding.digest or face.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise FaceCandidateInputError("FacePlacement belongs to different embedding or ring sources.")
    ring = ring_index.ring_for_key(face.ring_placement.ring_key)
    canonical_refs = tuple(
        LiftedVertexRef(
            ref.atom_index,
            add_shift(ref.image_shift, face.ring_placement.image_shift),
        )
        for ref in ring.vertex_walk
    )
    permutation = CycleParameterization(0, face.orientation).vertex_permutation(ring.size)
    refs = tuple(canonical_refs[position] for position in permutation)
    coordinates = tuple(
        embedding.fractional_coordinate(ref.atom_index, ref.image_shift) for ref in refs
    )
    edges = ring_index.translated_edge_instances(face.ring_placement)
    edge_ref_pairs = frozenset(
        frozenset((refs[index], refs[(index + 1) % len(refs)]))
        for index in range(len(refs))
    )
    return _BoundaryGeometry(refs, coordinates, edges, edge_ref_pairs)


def _triangle_coordinates(
    boundary: _BoundaryGeometry,
    triangles: BoundaryTriangulation,
) -> tuple[tuple[RationalVector3, RationalVector3, RationalVector3], ...]:
    return tuple(
        tuple(boundary.coordinates[index] for index in triangle)  # type: ignore[misc]
        for triangle in triangles
    )


def _triangle_refs(
    boundary: _BoundaryGeometry,
    triangles: BoundaryTriangulation,
) -> tuple[tuple[LiftedVertexRef, LiftedVertexRef, LiftedVertexRef], ...]:
    return tuple(
        tuple(boundary.refs[index] for index in triangle)  # type: ignore[misc]
        for triangle in triangles
    )


def _triangle_supports(
    triangles: Sequence[Sequence[RationalVector3]],
    *,
    object_offset: int = 0,
) -> tuple[PeriodicAabbSupport, ...]:
    return tuple(
        PeriodicAabbSupport.from_points(object_offset + index, triangle)
        for index, triangle in enumerate(triangles)
    )


def _edge_endpoints(
    embedding: PeriodicNetEmbedding,
    edge_key: FrameworkEdgeKey,
    anchor_shift: LatticeShift,
) -> tuple[RationalVector3, RationalVector3]:
    start = embedding.fractional_coordinate(edge_key.vertex_i, anchor_shift)
    end_shift = add_shift(anchor_shift, edge_key.image_shift)
    end = embedding.fractional_coordinate(edge_key.vertex_j, end_shift)
    return start, end


def _edge_refs(edge: LiftedEdgeInstanceRef) -> tuple[LiftedVertexRef, LiftedVertexRef]:
    return (
        LiftedVertexRef(edge.edge_key.vertex_i, edge.anchor_shift),
        LiftedVertexRef(edge.edge_key.vertex_j, add_shift(edge.anchor_shift, edge.edge_key.image_shift)),
    )


def _intersection_allowed(
    intersection: ExactTriangleIntersection,
    allowed_vertices: Iterable[RationalVector3],
    allowed_edges: Iterable[tuple[RationalVector3, RationalVector3]],
) -> bool:
    if intersection.empty:
        return True
    vertices = tuple(allowed_vertices)
    edges = tuple(allowed_edges)
    if intersection.dimension is IntersectionDimension.POINT:
        return bool(intersection.points) and intersection.points[0] in vertices
    if intersection.dimension is IntersectionDimension.SEGMENT:
        return any(
            all(point_on_segment(point, edge[0], edge[1]) for point in intersection.points)
            for edge in edges
        )
    return False


def _self_intersection_rejection(
    candidate_id: int,
    triangles: BoundaryTriangulation,
    triangle_coordinates: Sequence[Sequence[RationalVector3]],
    candidate_set: PeriodicSpatialCandidateSet,
    workspace: _FaceWorkspace,
) -> FaceWitnessRejection | None:
    for candidate in candidate_set.candidates:
        left_index = candidate.object_i
        right_index = candidate.object_j
        left = triangle_coordinates[left_index]
        right = tuple(translate(point, candidate.image_shift) for point in triangle_coordinates[right_index])
        workspace.triangle_test()
        try:
            intersection = triangle_triangle_intersection(left, right)
        except RobustGeometryError:
            return FaceWitnessRejection(
                candidate_id,
                triangles,
                FaceWitnessRejectionKind.DEGENERATE_TRIANGLE,
                candidate.image_shift,
                left_index,
                right_index,
            )
        if intersection.empty:
            continue
        allowed_vertices: list[RationalVector3] = []
        allowed_edges: list[tuple[RationalVector3, RationalVector3]] = []
        if candidate.image_shift == (0, 0, 0):
            common = set(triangles[left_index]).intersection(triangles[right_index])
            allowed_vertices = [triangle_coordinates[left_index][triangles[left_index].index(value)] for value in common]
            if len(common) == 2:
                first, second = sorted(common)
                allowed_edges.append((
                    triangle_coordinates[left_index][triangles[left_index].index(first)],
                    triangle_coordinates[left_index][triangles[left_index].index(second)],
                ))
        if not _intersection_allowed(intersection, allowed_vertices, allowed_edges):
            return FaceWitnessRejection(
                candidate_id,
                triangles,
                FaceWitnessRejectionKind.PERIODIC_SELF_INTERSECTION
                if candidate.image_shift != (0, 0, 0)
                else FaceWitnessRejectionKind.SURFACE_SELF_INTERSECTION,
                candidate.image_shift,
                left_index,
                right_index,
            )
    return None


def _framework_contact_kind(exact: ExactSegmentTriangleIntersection) -> FaceFrameworkContactKind:
    if exact.dimension is IntersectionDimension.SEGMENT:
        return FaceFrameworkContactKind.COPLANAR_OVERLAP
    if exact.transverse_sign:
        return FaceFrameworkContactKind.TRANSVERSE_INTERIOR
    if exact.triangle_interior and exact.segment_interval is not None and exact.segment_interval[0] in (0, 1):
        return FaceFrameworkContactKind.ENDPOINT_ON_INTERIOR
    return FaceFrameworkContactKind.NONBOUNDARY_CONTACT


def _allowed_framework_contact(
    exact: ExactSegmentTriangleIntersection,
    edge: LiftedEdgeInstanceRef,
    triangle_refs: Sequence[LiftedVertexRef],
    triangle_coordinates: Sequence[RationalVector3],
    boundary_edges: frozenset[LiftedEdgeInstanceRef],
) -> bool:
    endpoints = _edge_refs(edge)
    common = [ref for ref in endpoints if ref in triangle_refs]
    if edge in boundary_edges and len(common) == 2:
        edge_coordinates = tuple(
            triangle_coordinates[triangle_refs.index(ref)] for ref in endpoints
        )
        return all(point_on_segment(point, edge_coordinates[0], edge_coordinates[1]) for point in exact.points)
    if exact.dimension is IntersectionDimension.POINT and len(common) == 1:
        coordinate = triangle_coordinates[triangle_refs.index(common[0])]
        return exact.points == (coordinate,)
    return False


def _framework_contacts(
    embedding: PeriodicNetEmbedding,
    boundary: _BoundaryGeometry,
    triangles: BoundaryTriangulation,
    triangle_coordinates: Sequence[Sequence[RationalVector3]],
    triangle_refs: Sequence[Sequence[LiftedVertexRef]],
    *,
    source_digest: str,
    method: PeriodicSpatialMethod,
    spatial_resources: PeriodicSpatialResources | None,
    workspace: _FaceWorkspace,
) -> tuple[PeriodicSpatialCandidateSet, tuple[FaceFrameworkContact, ...]]:
    edge_supports = tuple(
        PeriodicAabbSupport.from_points(position, _edge_endpoints(embedding, edge_key, (0, 0, 0)))
        for position, edge_key in enumerate(embedding.edge_keys)
    )
    offset = len(edge_supports)
    supports = edge_supports + _triangle_supports(triangle_coordinates, object_offset=offset)
    candidate_set = build_periodic_overlap_candidates(
        supports,
        source_digest=source_digest,
        method=method,
        resources=spatial_resources,
    )
    contacts: list[FaceFrameworkContact] = []
    boundary_edges = frozenset(boundary.edges)
    for candidate in candidate_set.candidates:
        if candidate.object_i >= offset or candidate.object_j < offset:
            continue
        edge_position = candidate.object_i
        triangle_index = candidate.object_j - offset
        edge_key = embedding.edge_keys[edge_position]
        anchor = tuple(-value for value in candidate.image_shift)
        edge_instance = LiftedEdgeInstanceRef(embedding.topology_graph_digest, edge_key, anchor)
        start, end = _edge_endpoints(embedding, edge_key, anchor)
        workspace.framework_test()
        exact = segment_triangle_intersection(start, end, triangle_coordinates[triangle_index])
        if exact.empty:
            continue
        if _allowed_framework_contact(
            exact,
            edge_instance,
            triangle_refs[triangle_index],
            triangle_coordinates[triangle_index],
            boundary_edges,
        ):
            continue
        contacts.append(
            FaceFrameworkContact(
                edge_instance=edge_instance,
                triangle_index=triangle_index,
                relative_image_shift=candidate.image_shift,
                contact_kind=_framework_contact_kind(exact),
                intersection_dimension=exact.dimension,
                segment_interval=exact.segment_interval,
                points_fractional=exact.points,
                transverse_sign=exact.transverse_sign,
            )
        )
    contacts.sort(
        key=lambda value: (
            embedding.edge_position(value.edge_instance.edge_key),
            value.edge_instance.anchor_shift,
            value.triangle_index,
            value.contact_kind.value,
            value.relative_image_shift,
        )
    )
    return candidate_set, tuple(contacts)


def build_face_placement_certificate(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    edge_certificate: PeriodicEdgeIntersectionCertificate,
    face_placement: FacePlacement,
    *,
    method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
    spatial_resources: PeriodicSpatialResources | None = None,
    resources: FaceEmbeddingResources | None = None,
) -> FacePlacementCertificate:
    """Exhaust the finite boundary-vertex disk family for one face placement."""

    _validate_sources(view, embedding, ring_index, edge_certificate)
    if not isinstance(face_placement, FacePlacement):
        raise FaceCandidateInputError("face_placement must be a FacePlacement.")
    if (
        face_placement.periodic_net_embedding_digest != embedding.digest
        or face_placement.primitive_ring_catalog_digest != ring_index.catalog_digest
        or face_placement.ring_placement.topology_graph_digest != view.source_graph_digest
    ):
        raise FaceCandidateInputError("FacePlacement does not belong to the supplied sources.")
    active = resources or FaceEmbeddingResources()
    if not isinstance(active, FaceEmbeddingResources):
        raise FaceCandidateInputError("resources must be FaceEmbeddingResources.")
    boundary = _boundary_geometry(face_placement, embedding, ring_index)
    if len(boundary.refs) > active.max_boundary_vertices:
        raise FaceCandidateResourceError("Face boundary exceeds max_boundary_vertices.")
    if not edge_certificate.certified:
        return FacePlacementCertificate(
            periodic_net_view_digest=view.digest,
            topology_graph_digest=view.source_graph_digest,
            periodic_net_embedding_digest=embedding.digest,
            primitive_ring_catalog_digest=ring_index.catalog_digest,
            periodic_edge_intersection_certificate_digest=edge_certificate.digest,
            face_placement=face_placement,
            triangulation_candidate_count=0,
            witnesses=(),
            rejections=(),
            status=FacePlacementStatus.INVALID_REFERENCE_EMBEDDING,
        )
    try:
        triangulations = enumerate_boundary_triangulations(
            len(boundary.refs), max_triangulations=active.max_triangulations
        )
    except SurfaceMeshError as exc:
        if "exceeding" in str(exc):
            raise FaceCandidateResourceError(str(exc)) from exc
        raise FaceCandidateInputError(str(exc)) from exc

    workspace = _FaceWorkspace(active)
    witnesses: list[FaceEmbeddingWitness] = []
    rejections: list[FaceWitnessRejection] = []
    for candidate_id, triangles in enumerate(triangulations):
        validate_oriented_disk_triangulation(len(boundary.refs), triangles)
        triangle_coordinates = _triangle_coordinates(boundary, triangles)
        triangle_refs = _triangle_refs(boundary, triangles)
        try:
            for triangle in triangle_coordinates:
                triangle_normal(triangle)
        except RobustGeometryError:
            rejections.append(
                FaceWitnessRejection(
                    candidate_id,
                    triangles,
                    FaceWitnessRejectionKind.DEGENERATE_TRIANGLE,
                )
            )
            continue
        self_candidates = build_periodic_overlap_candidates(
            _triangle_supports(triangle_coordinates),
            source_digest=_digest({"face": face_placement.digest, "candidate_id": candidate_id, "query": "self"}),
            method=method,
            resources=spatial_resources,
        )
        rejection = _self_intersection_rejection(
            candidate_id, triangles, triangle_coordinates, self_candidates, workspace
        )
        if rejection is not None:
            rejections.append(rejection)
            continue
        framework_candidates, contacts = _framework_contacts(
            embedding,
            boundary,
            triangles,
            triangle_coordinates,
            triangle_refs,
            source_digest=_digest({"face": face_placement.digest, "candidate_id": candidate_id, "query": "framework"}),
            method=method,
            spatial_resources=spatial_resources,
            workspace=workspace,
        )
        witnesses.append(
            FaceEmbeddingWitness(
                face_placement=face_placement,
                witness_id=candidate_id,
                method=FaceWitnessMethod.BOUNDARY_VERTEX_TRIANGULATION,
                triangles=triangles,
                periodic_self_candidate_set_digest=self_candidates.digest,
                framework_candidate_set_digest=framework_candidates.digest,
                framework_contacts=contacts,
            )
        )

    if any(value.admissible for value in witnesses):
        status = FacePlacementStatus.CERTIFIED_ADMISSIBLE
    elif witnesses:
        status = FacePlacementStatus.UNRESOLVED_NO_ADMISSIBLE_WITNESS
    else:
        status = FacePlacementStatus.UNRESOLVED_NO_EMBEDDED_WITNESS
    return FacePlacementCertificate(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        periodic_net_embedding_digest=embedding.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        periodic_edge_intersection_certificate_digest=edge_certificate.digest,
        face_placement=face_placement,
        triangulation_candidate_count=len(triangulations),
        witnesses=tuple(witnesses),
        rejections=tuple(rejections),
        status=status,
    )


def _shift_ref(ref: LiftedVertexRef, shift: LatticeShift) -> LiftedVertexRef:
    return LiftedVertexRef(ref.atom_index, add_shift(ref.image_shift, shift))


def _shift_edge(edge: LiftedEdgeInstanceRef, shift: LatticeShift) -> LiftedEdgeInstanceRef:
    return LiftedEdgeInstanceRef(edge.topology_graph_digest, edge.edge_key, add_shift(edge.anchor_shift, shift))


def _ring_segment_supports(boundary: _BoundaryGeometry) -> tuple[PeriodicAabbSupport, ...]:
    return tuple(
        PeriodicAabbSupport.from_points(
            index,
            (boundary.coordinates[index], boundary.coordinates[(index + 1) % len(boundary.coordinates)]),
        )
        for index in range(len(boundary.coordinates))
    )


def _shared_boundary_features(
    left: _BoundaryGeometry,
    right: _BoundaryGeometry,
    shift: LatticeShift,
) -> tuple[set[LiftedVertexRef], set[frozenset[LiftedVertexRef]]]:
    right_refs = {_shift_ref(ref, shift) for ref in right.refs}
    vertices = set(left.refs).intersection(right_refs)
    right_edges = {
        frozenset((_shift_ref(right.refs[index], shift), _shift_ref(right.refs[(index + 1) % len(right.refs)], shift)))
        for index in range(len(right.refs))
    }
    edges = set(left.edge_ref_pairs).intersection(right_edges)
    return vertices, edges


def _segment_surface_intersection_allowed_on_shared_boundary(
    exact: ExactSegmentTriangleIntersection,
    boundary: _BoundaryGeometry,
    shared_vertices: set[LiftedVertexRef],
    shared_edges: set[frozenset[LiftedVertexRef]],
) -> bool:
    """Return whether one ring--surface contact is wholly shared boundary."""

    ref_to_point = dict(zip(boundary.refs, boundary.coordinates, strict=True))
    allowed_vertices = {
        ref_to_point[ref] for ref in shared_vertices if ref in ref_to_point
    }
    allowed_edges = tuple(
        (ref_to_point[refs[0]], ref_to_point[refs[1]])
        for edge in shared_edges
        for refs in (tuple(edge),)
        if len(refs) == 2 and all(ref in ref_to_point for ref in refs)
    )
    if exact.dimension is IntersectionDimension.POINT:
        if not exact.points:
            return False
        point = exact.points[0]
        return point in allowed_vertices or any(
            point_on_segment(point, edge[0], edge[1]) for edge in allowed_edges
        )
    if exact.dimension is IntersectionDimension.SEGMENT:
        return any(
            all(point_on_segment(point, edge[0], edge[1]) for point in exact.points)
            for edge in allowed_edges
        )
    return False


def _ring_surface_intersections(
    left_boundary: _BoundaryGeometry,
    right_boundary: _BoundaryGeometry,
    right_triangles: Sequence[Sequence[RationalVector3]],
    *,
    source_digest: str,
    method: PeriodicSpatialMethod,
    spatial_resources: PeriodicSpatialResources | None,
    workspace: _FaceWorkspace,
) -> tuple[PeriodicSpatialCandidateSet, tuple[FaceAlgebraicIntersection, ...]]:
    segment_supports = _ring_segment_supports(left_boundary)
    offset = len(segment_supports)
    supports = segment_supports + _triangle_supports(right_triangles, object_offset=offset)
    candidate_set = build_periodic_overlap_candidates(
        supports,
        source_digest=source_digest,
        method=method,
        resources=spatial_resources,
    )
    accum: dict[LatticeShift, list[int]] = {}
    for candidate in candidate_set.candidates:
        if candidate.object_i >= offset or candidate.object_j < offset:
            continue
        segment_index = candidate.object_i
        triangle_index = candidate.object_j - offset
        start = left_boundary.coordinates[segment_index]
        end = left_boundary.coordinates[(segment_index + 1) % len(left_boundary.coordinates)]
        triangle = tuple(translate(point, candidate.image_shift) for point in right_triangles[triangle_index])
        workspace.framework_test()
        exact = segment_triangle_intersection(start, end, triangle)
        if exact.empty:
            continue
        shared_vertices, shared_edges = _shared_boundary_features(
            left_boundary, right_boundary, candidate.image_shift
        )
        if _segment_surface_intersection_allowed_on_shared_boundary(
            exact, left_boundary, shared_vertices, shared_edges
        ):
            continue
        record = accum.setdefault(candidate.image_shift, [0, 0, 0])
        if exact.transverse_sign:
            record[0] += exact.transverse_sign
            record[1] += 1
        else:
            record[2] += 1
    values = tuple(
        FaceAlgebraicIntersection(shift, data[0], data[1], data[2])
        for shift, data in sorted(accum.items())
    )
    return candidate_set, values


def _surface_surface_relation(
    left_boundary: _BoundaryGeometry,
    right_boundary: _BoundaryGeometry,
    left_triangles: Sequence[Sequence[RationalVector3]],
    right_triangles: Sequence[Sequence[RationalVector3]],
    left_triangle_refs: Sequence[Sequence[LiftedVertexRef]],
    right_triangle_refs: Sequence[Sequence[LiftedVertexRef]],
    *,
    source_digest: str,
    method: PeriodicSpatialMethod,
    spatial_resources: PeriodicSpatialResources | None,
    workspace: _FaceWorkspace,
) -> tuple[PeriodicSpatialCandidateSet, int, int]:
    left_supports = _triangle_supports(left_triangles)
    offset = len(left_supports)
    supports = left_supports + _triangle_supports(right_triangles, object_offset=offset)
    candidate_set = build_periodic_overlap_candidates(
        supports,
        source_digest=source_digest,
        method=method,
        resources=spatial_resources,
    )
    incompatible = 0
    allowed = 0
    for candidate in candidate_set.candidates:
        if candidate.object_i >= offset or candidate.object_j < offset:
            continue
        left_index = candidate.object_i
        right_index = candidate.object_j - offset
        right = tuple(translate(point, candidate.image_shift) for point in right_triangles[right_index])
        workspace.triangle_test()
        intersection = triangle_triangle_intersection(left_triangles[left_index], right)
        if intersection.empty:
            continue
        shared_vertices, shared_edges = _shared_boundary_features(
            left_boundary, right_boundary, candidate.image_shift
        )
        left_ref_to_point = {
            ref: point for ref, point in zip(left_triangle_refs[left_index], left_triangles[left_index], strict=True)
        }
        shifted_right_ref_to_point = {
            _shift_ref(ref, candidate.image_shift): point
            for ref, point in zip(right_triangle_refs[right_index], right, strict=True)
        }
        common_triangle_refs = set(left_ref_to_point).intersection(shifted_right_ref_to_point)
        allowed_vertices = [left_ref_to_point[ref] for ref in common_triangle_refs if ref in shared_vertices]
        allowed_edges: list[tuple[RationalVector3, RationalVector3]] = []
        for edge in shared_edges:
            refs = tuple(edge)
            if len(refs) == 2 and all(ref in common_triangle_refs for ref in refs):
                allowed_edges.append((left_ref_to_point[refs[0]], left_ref_to_point[refs[1]]))
        if _intersection_allowed(intersection, allowed_vertices, allowed_edges):
            allowed += 1
        else:
            incompatible += 1
    return candidate_set, incompatible, allowed


def certify_face_witness_pair(
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    left_witness: FaceEmbeddingWitness,
    right_witness: FaceEmbeddingWitness,
    *,
    method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
    spatial_resources: PeriodicSpatialResources | None = None,
    resources: FaceEmbeddingResources | None = None,
) -> FaceWitnessPairCertificate:
    """Classify linking and geometric compatibility of two particular witnesses."""

    if not isinstance(left_witness, FaceEmbeddingWitness) or not isinstance(right_witness, FaceEmbeddingWitness):
        raise FaceCandidateInputError("left_witness and right_witness must be FaceEmbeddingWitness records.")
    if left_witness.face_placement == right_witness.face_placement:
        raise FaceCandidateInputError("Witness-pair certification requires distinct scientific faces.")
    for witness in (left_witness, right_witness):
        if witness.face_placement.periodic_net_embedding_digest != embedding.digest or witness.face_placement.primitive_ring_catalog_digest != ring_index.catalog_digest:
            raise FaceCandidateInputError("Witness belongs to different embedding or ring sources.")
    active = resources or FaceEmbeddingResources()
    workspace = _FaceWorkspace(active)
    left_boundary = _boundary_geometry(left_witness.face_placement, embedding, ring_index)
    right_boundary = _boundary_geometry(right_witness.face_placement, embedding, ring_index)
    left_triangles = _triangle_coordinates(left_boundary, left_witness.triangles)
    right_triangles = _triangle_coordinates(right_boundary, right_witness.triangles)
    left_refs = _triangle_refs(left_boundary, left_witness.triangles)
    right_refs = _triangle_refs(right_boundary, right_witness.triangles)
    source = _digest({"left": left_witness.digest, "right": right_witness.digest})
    ring_surface, algebraic = _ring_surface_intersections(
        left_boundary,
        right_boundary,
        right_triangles,
        source_digest=_digest({"source": source, "query": "ring-surface"}),
        method=method,
        spatial_resources=spatial_resources,
        workspace=workspace,
    )
    surfaces, incompatible, allowed = _surface_surface_relation(
        left_boundary,
        right_boundary,
        left_triangles,
        right_triangles,
        left_refs,
        right_refs,
        source_digest=_digest({"source": source, "query": "surface-surface"}),
        method=method,
        spatial_resources=spatial_resources,
        workspace=workspace,
    )
    if any(value.intersection_number != 0 for value in algebraic):
        status = FaceWitnessPairStatus.PROVEN_LINKED_NONZERO_INTERSECTION
    elif incompatible:
        status = FaceWitnessPairStatus.WITNESS_PAIR_INCOMPATIBLE
    elif any(value.unresolved_contact_count for value in algebraic):
        status = FaceWitnessPairStatus.UNRESOLVED_LINKING
    elif allowed:
        status = FaceWitnessPairStatus.COMPATIBLE_SHARED_BOUNDARY
    else:
        status = FaceWitnessPairStatus.DISJOINT_DISK_WITNESS
    return FaceWitnessPairCertificate(
        left_witness_digest=left_witness.digest,
        right_witness_digest=right_witness.digest,
        ring_surface_candidate_set_digest=ring_surface.digest,
        surface_surface_candidate_set_digest=surfaces.digest,
        algebraic_intersections=algebraic,
        incompatible_surface_contact_count=incompatible,
        allowed_shared_boundary_contact_count=allowed,
        status=status,
    )


def map_face_placement(
    face: FacePlacement,
    symmetry: PeriodicNetSymmetry,
    ring_symmetry: PrimitiveRingSymmetryIndex,
    operation_index: int,
) -> FacePlacement:
    """Map scientific face identity without referring to an auxiliary triangulation."""

    if face.primitive_ring_catalog_digest != ring_symmetry.primitive_ring_catalog_digest:
        raise FaceCandidateInputError("Face and ring-symmetry index use different ring catalogs.")
    image = ring_symmetry.ring_image(operation_index, face.ring_placement.ring_key)
    placement = ring_symmetry.map_placement(symmetry, operation_index, face.ring_placement)
    orientation = face.orientation * image.parameterization.orientation
    return FacePlacement(
        periodic_net_embedding_digest=face.periodic_net_embedding_digest,
        primitive_ring_catalog_digest=face.primitive_ring_catalog_digest,
        ring_placement=placement,
        orientation=orientation,  # type: ignore[arg-type]
    )


def _canonical_oriented_triangle(triangle: TriangleIndex) -> TriangleIndex:
    return min(
        triangle,
        (triangle[1], triangle[2], triangle[0]),
        (triangle[2], triangle[0], triangle[1]),
    )


def _mapped_witness_triangles(
    source_face: FacePlacement,
    target_face: FacePlacement,
    source_triangles: BoundaryTriangulation,
    image_parameterization: CycleParameterization,
    ring_size: int,
) -> BoundaryTriangulation:
    source_boundary_to_canonical = CycleParameterization(0, source_face.orientation).vertex_permutation(ring_size)
    target_boundary_to_canonical = CycleParameterization(0, target_face.orientation).vertex_permutation(ring_size)
    canonical_to_target_boundary = {value: index for index, value in enumerate(target_boundary_to_canonical)}
    source_to_target_canonical = image_parameterization.vertex_permutation(ring_size)
    position_map = {
        source_boundary_index: canonical_to_target_boundary[source_to_target_canonical[source_canonical]]
        for source_boundary_index, source_canonical in enumerate(source_boundary_to_canonical)
    }
    return tuple(
        sorted(
            _canonical_oriented_triangle(tuple(position_map[value] for value in triangle))
            for triangle in source_triangles
        )
    )


def build_face_compatibility_constraint_system(
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    certificates: Sequence[FacePlacementCertificate],
    *,
    method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
    spatial_resources: PeriodicSpatialResources | None = None,
    resources: FaceEmbeddingResources | None = None,
    higher_order_forbidden: Sequence[Sequence[FaceWitnessAssignment]] = (),
    symmetry: PeriodicNetSymmetry | None = None,
    ring_symmetry: PrimitiveRingSymmetryIndex | None = None,
) -> FaceCompatibilityConstraintSystem:
    """Build a finite constraint system over scientific faces and disk witnesses."""

    values = tuple(certificates)
    if not values or any(not isinstance(value, FacePlacementCertificate) for value in values):
        raise FaceCandidateInputError("certificates must contain FacePlacementCertificate records.")
    if len({value.face_placement.digest for value in values}) != len(values):
        raise FaceCandidateInputError("certificates must contain distinct scientific faces.")
    for value in values:
        if value.periodic_net_embedding_digest != embedding.digest or value.primitive_ring_catalog_digest != ring_index.catalog_digest:
            raise FaceCandidateInputError("Face certificate belongs to different embedding or ring sources.")
    active = resources or FaceEmbeddingResources()
    witnesses = tuple(witness for certificate in values for witness in certificate.witnesses)
    assignments = tuple(
        FaceWitnessAssignment(witness.face_placement.digest, witness.witness_id, witness.digest)
        for witness in witnesses
    )
    assignment_by_digest = {value.witness_digest: value for value in assignments}
    constraints: list[FaceCompatibilityConstraint] = []
    for witness in witnesses:
        if not witness.admissible:
            constraints.append(
                FaceCompatibilityConstraint(
                    FaceConstraintKind.UNARY_FORBIDDEN,
                    (assignment_by_digest[witness.digest],),
                    "framework-penetrated witness",
                    witness.digest,
                )
            )

    combinations = sum(
        len(values[left].witnesses) * len(values[right].witnesses)
        for left in range(len(values))
        for right in range(left + 1, len(values))
    )
    if combinations > active.max_pair_witness_combinations:
        raise FaceCandidateResourceError("Witness-pair domain exceeds max_pair_witness_combinations.")
    pair_certificates: list[FaceWitnessPairCertificate] = []
    for left_index in range(len(values)):
        for right_index in range(left_index + 1, len(values)):
            for left_witness in values[left_index].witnesses:
                for right_witness in values[right_index].witnesses:
                    pair = certify_face_witness_pair(
                        embedding,
                        ring_index,
                        left_witness,
                        right_witness,
                        method=method,
                        spatial_resources=spatial_resources,
                        resources=active,
                    )
                    pair_certificates.append(pair)
                    pair_assignments = (
                        assignment_by_digest[left_witness.digest],
                        assignment_by_digest[right_witness.digest],
                    )
                    if pair.status in (
                        FaceWitnessPairStatus.PROVEN_LINKED_NONZERO_INTERSECTION,
                        FaceWitnessPairStatus.WITNESS_PAIR_INCOMPATIBLE,
                    ):
                        constraints.append(
                            FaceCompatibilityConstraint(
                                FaceConstraintKind.PAIR_FORBIDDEN,
                                pair_assignments,
                                pair.status.value,
                                pair.digest,
                            )
                        )
                    elif pair.status is FaceWitnessPairStatus.UNRESOLVED_LINKING:
                        constraints.append(
                            FaceCompatibilityConstraint(
                                FaceConstraintKind.UNRESOLVED,
                                pair_assignments,
                                pair.status.value,
                                pair.digest,
                            )
                        )
    valid_assignments = set(assignments)
    for raw in higher_order_forbidden:
        assignment_tuple = tuple(raw)
        if any(value not in valid_assignments for value in assignment_tuple):
            raise FaceCandidateInputError("Higher-order constraint references an unknown assignment.")
        constraints.append(
            FaceCompatibilityConstraint(
                FaceConstraintKind.HIGHER_ORDER_FORBIDDEN,
                assignment_tuple,
                "caller-declared higher-order incompatibility",
            )
        )

    face_relations: list[FaceSymmetryRelation] = []
    witness_relations: list[FaceWitnessSymmetryRelation] = []
    if (symmetry is None) != (ring_symmetry is None):
        raise FaceCandidateInputError("symmetry and ring_symmetry must be supplied together.")
    if symmetry is not None and ring_symmetry is not None:
        face_by_digest = {value.face_placement.digest: value for value in values}
        face_by_identity = {value.face_placement: value for value in values}
        for certificate in values:
            source_face = certificate.face_placement
            ring_size = ring_index.ring_for_key(source_face.ring_placement.ring_key).size
            for operation_index in range(symmetry.order):
                target_face = map_face_placement(source_face, symmetry, ring_symmetry, operation_index)
                target_certificate = face_by_identity.get(target_face)
                if target_certificate is None:
                    continue
                face_relations.append(
                    FaceSymmetryRelation(operation_index, source_face.digest, target_face.digest)
                )
                image = ring_symmetry.ring_image(operation_index, source_face.ring_placement.ring_key)
                target_by_triangles = {witness.triangles: witness for witness in target_certificate.witnesses}
                for source_witness in certificate.witnesses:
                    mapped = _mapped_witness_triangles(
                        source_face,
                        target_face,
                        source_witness.triangles,
                        image.parameterization,
                        ring_size,
                    )
                    target_witness = target_by_triangles.get(mapped)
                    if target_witness is not None:
                        witness_relations.append(
                            FaceWitnessSymmetryRelation(
                                operation_index,
                                source_witness.digest,
                                target_witness.digest,
                            )
                        )

    return FaceCompatibilityConstraintSystem(
        face_certificate_digests=tuple(value.digest for value in values),
        assignments=assignments,
        pair_certificates=tuple(pair_certificates),
        constraints=tuple(constraints),
        face_symmetry_relations=tuple(face_relations),
        witness_symmetry_relations=tuple(witness_relations),
    )


__all__ = [
    "CANONICAL_FACE_CERTIFICATE_SCHEMA",
    "CANONICAL_FACE_CONSTRAINT_SYSTEM_SCHEMA",
    "CANONICAL_FACE_PAIR_CERTIFICATE_SCHEMA",
    "CANONICAL_FACE_PLACEMENT_SCHEMA",
    "CANONICAL_FACE_WITNESS_SCHEMA",
    "FACE_CANDIDATE_DIGEST_ALGORITHM",
    "FaceAlgebraicIntersection",
    "FaceCandidateError",
    "FaceCandidateInputError",
    "FaceCandidateResourceError",
    "FaceCandidateSerializationError",
    "FaceCompatibilityConstraint",
    "FaceCompatibilityConstraintSystem",
    "FaceConstraintKind",
    "FaceEmbeddingResources",
    "FaceEmbeddingWitness",
    "FaceFrameworkContact",
    "FaceFrameworkContactKind",
    "FacePlacement",
    "FacePlacementCertificate",
    "FacePlacementStatus",
    "FaceSymmetryRelation",
    "FaceWitnessAssignment",
    "FaceWitnessMethod",
    "FaceWitnessPairCertificate",
    "FaceWitnessPairStatus",
    "FaceWitnessRejection",
    "FaceWitnessRejectionKind",
    "FaceWitnessSymmetryRelation",
    "build_face_compatibility_constraint_system",
    "build_face_placement_certificate",
    "certify_face_witness_pair",
    "make_face_placement",
    "map_face_placement",
]
