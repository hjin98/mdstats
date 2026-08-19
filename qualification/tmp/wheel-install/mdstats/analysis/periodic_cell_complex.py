"""Translation-labelled periodic cell complexes and exact partition certificates.

The scientific complex is a finite quotient CW complex over the translation
lattice.  Boundary terms therefore retain both the target cell orbit and the
integer image shift.  The auxiliary partition certificate is intentionally
separate: it uses an explicit periodic tetrahedral mesh to prove face conformity,
disjoint interiors, and complete coverage without making tetrahedralization
choices part of scientific tiling identity.

The quotient-edge shift convention follows Chung, Hahn, and Klee (1984) and
Klee (2004).  Exact orientation signs follow the robust-predicate principle of
Shewchuk (1997).  Tetrahedron overlap rejection uses the separating-axis family
for convex tetrahedra, following the overlap formulation of Ganovelli, Ponchio,
and Rocchini (2002), but all projections here use exact ``Fraction`` arithmetic.

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
W. E. Klee, Cryst. Res. Technol. 39, 959-968 (2004),
doi:10.1002/crat.200410281.
J. R. Shewchuk, Discrete Comput. Geom. 18, 305-363 (1997),
doi:10.1007/PL00009321.
F. Ganovelli, F. Ponchio, and C. Rocchini, J. Graphics Tools 7(2), 17-26
(2002), doi:10.1080/10867651.2002.10487557.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
import json
from math import floor
from numbers import Integral
from typing import Any, Iterable, Mapping, Sequence, TypeAlias

from ._periodic_graph import LatticeShift, add_shift, coerce_lattice_shift, physical_edge_anchor
from ._periodic_spatial import (
    PeriodicAabbSupport,
    PeriodicSpatialMethod,
    PeriodicSpatialResources,
    build_periodic_overlap_candidates,
)
from ._robust_geometry import RationalVector3, cross, dot, orient3d, subtract, translate
from .face_candidates import (
    FaceCompatibilityConstraintSystem,
    FaceConstraintKind,
    FaceEmbeddingWitness,
    FacePlacement,
    FacePlacementCertificate,
    FacePlacementStatus,
    FaceWitnessAssignment,
)
from .periodic_cycle import CycleParameterization
from .periodic_net_embedding import PeriodicNetEmbedding, ProjectedEdgeCurveModel
from .periodic_net_view import PeriodicNetView
from .primitive_ring_index import PrimitiveRingIndex

CANONICAL_PERIODIC_CELL_COMPLEX_SCHEMA = "mdstats.periodic-cell-complex.v1"
CANONICAL_PERIODIC_PARTITION_CERTIFICATE_SCHEMA = "mdstats.periodic-partition-certificate.v1"
PERIODIC_CELL_COMPLEX_DIGEST_ALGORITHM = "sha256-canonical-json-v1"

ZERO_SHIFT: LatticeShift = (0, 0, 0)
RationalTetrahedron: TypeAlias = tuple[
    RationalVector3, RationalVector3, RationalVector3, RationalVector3
]


class PeriodicCellComplexError(ValueError):
    """Base exception for Stage-9 cell-complex construction."""


class PeriodicCellComplexInputError(PeriodicCellComplexError):
    """Raised when source identities or explicit records are malformed."""


class PeriodicCellComplexInvariantError(PeriodicCellComplexError):
    """Raised when chain, shell, or partition invariants fail."""


class PeriodicCellComplexResourceError(PeriodicCellComplexError):
    """Raised transactionally before a declared resource limit is exceeded."""


class PeriodicCellComplexSerializationError(PeriodicCellComplexError):
    """Raised when serialized scientific or certificate data are inconsistent."""


class PartitionFacetKind(str, Enum):
    """Role of one periodically paired auxiliary triangle facet."""

    AUXILIARY_INTERNAL = "auxiliary-internal"
    SCIENTIFIC_INTERFACE = "scientific-interface"


class TetrahedronPairRelation(str, Enum):
    """Exact interior relation of two explicit periodic tetrahedron images."""

    DISJOINT = "disjoint"
    BOUNDARY_CONTACT = "boundary-contact"
    IMPROPER_INTERIOR_OVERLAP = "improper-interior-overlap"
    CONTAINMENT_OVERLAP = "containment-overlap"
    COINCIDENT_INTERIOR = "coincident-interior"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _sha(value: str, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise PeriodicCellComplexInputError(f"{name} must be a SHA-256 digest.")
    return value


def _int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise PeriodicCellComplexInputError(f"{name} must be an integer.")
    return int(value)


def _nonnegative(value: object, *, name: str) -> int:
    result = _int(value, name=name)
    if result < 0:
        raise PeriodicCellComplexInputError(f"{name} must be nonnegative.")
    return result


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise PeriodicCellComplexInputError(f"{name} must be positive.")
    return result


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _point_payload(point: RationalVector3) -> list[list[int]]:
    return [_fraction_payload(value) for value in point]


def _coerce_point(value: Sequence[object], *, name: str) -> RationalVector3:
    point = tuple(Fraction(component) for component in value)
    if len(point) != 3:
        raise PeriodicCellComplexInputError(f"{name} must contain three components.")
    return point  # type: ignore[return-value]


def _fraction_from_payload(value: object, *, name: str) -> Fraction:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise PeriodicCellComplexSerializationError(f"{name} must be a [numerator, denominator] pair.")
    numerator = _int(value[0], name=f"{name}[0]")
    denominator = _positive(value[1], name=f"{name}[1]")
    return Fraction(numerator, denominator)


def _point_from_payload(value: object, *, name: str) -> RationalVector3:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise PeriodicCellComplexSerializationError(f"{name} must contain three rational components.")
    return tuple(
        _fraction_from_payload(component, name=f"{name}[{index}]")
        for index, component in enumerate(value)
    )  # type: ignore[return-value]


def _term_from_payload(value: object, *, name: str) -> "TranslatedCellTerm":
    if not isinstance(value, Mapping):
        raise PeriodicCellComplexSerializationError(f"{name} must be a mapping.")
    return TranslatedCellTerm(
        value["cell_index"],
        value["image_shift"],
        value["coefficient"],
    )


def _combine_terms(terms: Iterable["TranslatedCellTerm"]) -> tuple["TranslatedCellTerm", ...]:
    coefficients: dict[tuple[int, LatticeShift], int] = defaultdict(int)
    for term in terms:
        if not isinstance(term, TranslatedCellTerm):
            raise PeriodicCellComplexInputError("Boundary terms must be TranslatedCellTerm records.")
        coefficients[(term.cell_index, term.image_shift)] += term.coefficient
    return tuple(
        TranslatedCellTerm(cell_index, shift, coefficient)
        for (cell_index, shift), coefficient in sorted(coefficients.items())
        if coefficient
    )


@dataclass(frozen=True, order=True, slots=True)
class TranslatedCellTerm:
    """One integer chain term for a translated target-cell orbit."""

    cell_index: int
    image_shift: LatticeShift
    coefficient: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "cell_index", _nonnegative(self.cell_index, name="cell_index"))
        try:
            shift = coerce_lattice_shift(self.image_shift, name="image_shift")
        except ValueError as exc:
            raise PeriodicCellComplexInputError(str(exc)) from exc
        coefficient = _int(self.coefficient, name="coefficient")
        if coefficient == 0:
            raise PeriodicCellComplexInputError("A stored chain term cannot have zero coefficient.")
        object.__setattr__(self, "image_shift", shift)
        object.__setattr__(self, "coefficient", coefficient)

    def translated(self, shift: LatticeShift, coefficient: int = 1) -> "TranslatedCellTerm":
        return TranslatedCellTerm(
            self.cell_index,
            add_shift(self.image_shift, shift),
            self.coefficient * coefficient,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "cell_index": self.cell_index,
            "image_shift": list(self.image_shift),
            "coefficient": self.coefficient,
        }


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicBoundaryOperator:
    """Finite translation-labelled integer boundary operator."""

    source_dimension: int
    source_cell_count: int
    target_cell_count: int
    columns: tuple[tuple[TranslatedCellTerm, ...], ...]
    digest: str = ""

    def __post_init__(self) -> None:
        dimension = _int(self.source_dimension, name="source_dimension")
        if dimension not in (1, 2, 3):
            raise PeriodicCellComplexInputError("source_dimension must be 1, 2, or 3.")
        source_count = _nonnegative(self.source_cell_count, name="source_cell_count")
        target_count = _nonnegative(self.target_cell_count, name="target_cell_count")
        columns = tuple(_combine_terms(column) for column in self.columns)
        if len(columns) != source_count:
            raise PeriodicCellComplexInputError("Boundary column count disagrees with source_cell_count.")
        if any(term.cell_index >= target_count for column in columns for term in column):
            raise PeriodicCellComplexInputError("Boundary term references an invalid target-cell orbit.")
        object.__setattr__(self, "source_dimension", dimension)
        object.__setattr__(self, "source_cell_count", source_count)
        object.__setattr__(self, "target_cell_count", target_count)
        object.__setattr__(self, "columns", columns)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise PeriodicCellComplexInputError("Stored boundary-operator digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeriodicBoundaryOperator) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "source_dimension": self.source_dimension,
            "source_cell_count": self.source_cell_count,
            "target_cell_count": self.target_cell_count,
            "columns": [[term.to_dict() for term in column] for column in self.columns],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)


@dataclass(frozen=True, slots=True)
class PeriodicTileShell:
    """One oriented 3-cell orbit boundary expressed in scientific face orbits."""

    tile_index: int
    face_incidences: tuple[TranslatedCellTerm, ...]
    label: str = ""

    def __post_init__(self) -> None:
        index = _nonnegative(self.tile_index, name="tile_index")
        incidences = _combine_terms(self.face_incidences)
        if not incidences:
            raise PeriodicCellComplexInputError("A tile shell requires at least one face incidence.")
        if any(abs(term.coefficient) != 1 for term in incidences):
            raise PeriodicCellComplexInputError("Tile-shell face incidences must have coefficient +/-1.")
        if not isinstance(self.label, str):
            raise PeriodicCellComplexInputError("Tile label must be a string.")
        object.__setattr__(self, "tile_index", index)
        object.__setattr__(self, "face_incidences", incidences)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "face_incidences": [term.to_dict() for term in self.face_incidences],
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class TileShellInvariant:
    """Finite lifted-boundary invariants for one tile orbit representative."""

    tile_index: int
    vertex_instance_count: int
    edge_instance_count: int
    face_instance_count: int
    euler_characteristic: int
    connected: bool
    nonbranching: bool
    orientable: bool

    def __post_init__(self) -> None:
        for name in ("tile_index", "vertex_instance_count", "edge_instance_count", "face_instance_count"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        object.__setattr__(self, "euler_characteristic", _int(self.euler_characteristic, name="euler_characteristic"))
        object.__setattr__(self, "connected", bool(self.connected))
        object.__setattr__(self, "nonbranching", bool(self.nonbranching))
        object.__setattr__(self, "orientable", bool(self.orientable))

    @property
    def genus_zero(self) -> bool:
        return self.connected and self.nonbranching and self.orientable and self.euler_characteristic == 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "vertex_instance_count": self.vertex_instance_count,
            "edge_instance_count": self.edge_instance_count,
            "face_instance_count": self.face_instance_count,
            "euler_characteristic": self.euler_characteristic,
            "connected": self.connected,
            "nonbranching": self.nonbranching,
            "orientable": self.orientable,
            "genus_zero": self.genus_zero,
        }


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicCellComplex:
    """Scientific periodic 0/1/2/3-cell quotient with formal chain algebra."""

    periodic_net_view_digest: str
    topology_graph_digest: str
    periodic_net_embedding_digest: str
    primitive_ring_catalog_digest: str
    face_placements: tuple[FacePlacement, ...]
    tile_shells: tuple[PeriodicTileShell, ...]
    boundary_1: PeriodicBoundaryOperator
    boundary_2: PeriodicBoundaryOperator
    boundary_3: PeriodicBoundaryOperator
    tile_shell_invariants: tuple[TileShellInvariant, ...]
    construction_witness_digests: tuple[str, ...] = field(default=(), compare=False)
    canonical_schema_version: str = CANONICAL_PERIODIC_CELL_COMPLEX_SCHEMA
    digest_algorithm: str = PERIODIC_CELL_COMPLEX_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "periodic_net_view_digest",
            "topology_graph_digest",
            "periodic_net_embedding_digest",
            "primitive_ring_catalog_digest",
        ):
            _sha(getattr(self, name), name=name)
        faces = tuple(self.face_placements)
        shells = tuple(self.tile_shells)
        invariants = tuple(self.tile_shell_invariants)
        if any(not isinstance(value, FacePlacement) for value in faces):
            raise PeriodicCellComplexInputError("face_placements contain an invalid record.")
        if len({face.digest for face in faces}) != len(faces):
            raise PeriodicCellComplexInputError("Scientific face placements must be unique.")
        if tuple(shell.tile_index for shell in shells) != tuple(range(len(shells))):
            raise PeriodicCellComplexInputError("Tile IDs must be dense and ordered.")
        if tuple(value.tile_index for value in invariants) != tuple(range(len(shells))):
            raise PeriodicCellComplexInputError("Tile-shell invariants must align with tile IDs.")
        witnesses = tuple(self.construction_witness_digests)
        if len(witnesses) != len(faces):
            raise PeriodicCellComplexInputError("One construction witness digest is required per face.")
        for value in witnesses:
            _sha(value, name="construction_witness_digest")
        if self.boundary_1.source_dimension != 1 or self.boundary_2.source_dimension != 2 or self.boundary_3.source_dimension != 3:
            raise PeriodicCellComplexInputError("Boundary operators have inconsistent dimensions.")
        if self.boundary_2.target_cell_count != self.boundary_1.source_cell_count:
            raise PeriodicCellComplexInputError("boundary_2 target count must equal edge-orbit count.")
        if self.boundary_3.target_cell_count != len(faces) or self.boundary_3.source_cell_count != len(shells):
            raise PeriodicCellComplexInputError("boundary_3 counts disagree with faces or tiles.")
        if self.boundary_2.source_cell_count != len(faces):
            raise PeriodicCellComplexInputError("boundary_2 source count disagrees with faces.")
        if any(_compose_boundaries(self.boundary_1, self.boundary_2)):
            raise PeriodicCellComplexInvariantError("The scientific complex violates boundary_1 * boundary_2 = 0.")
        if any(_compose_boundaries(self.boundary_2, self.boundary_3)):
            raise PeriodicCellComplexInvariantError("The scientific complex violates boundary_2 * boundary_3 = 0.")
        counts = (
            self.boundary_1.target_cell_count,
            self.boundary_1.source_cell_count,
            len(faces),
            len(shells),
        )
        if counts[0] - counts[1] + counts[2] - counts[3] != 0:
            raise PeriodicCellComplexInvariantError("Periodic quotient Euler characteristic must equal zero.")
        incidence_counts = Counter(term.cell_index for column in self.boundary_3.columns for term in column)
        if any(incidence_counts[index] != 2 for index in range(len(faces))):
            raise PeriodicCellComplexInvariantError("Every face orbit must have exactly two translated tile-side incidences.")
        if any(not value.genus_zero for value in invariants):
            raise PeriodicCellComplexInvariantError("Every tile boundary must be connected, orientable, nonbranching, and genus zero.")
        if self.canonical_schema_version != CANONICAL_PERIODIC_CELL_COMPLEX_SCHEMA:
            raise PeriodicCellComplexInputError("Unsupported periodic-cell-complex schema.")
        if self.digest_algorithm != PERIODIC_CELL_COMPLEX_DIGEST_ALGORITHM:
            raise PeriodicCellComplexInputError("Unsupported periodic-cell-complex digest algorithm.")
        object.__setattr__(self, "face_placements", faces)
        object.__setattr__(self, "tile_shells", shells)
        object.__setattr__(self, "tile_shell_invariants", invariants)
        object.__setattr__(self, "construction_witness_digests", witnesses)
        expected = _digest(self._scientific_payload(False))
        if self.digest and self.digest != expected:
            raise PeriodicCellComplexInputError("Stored scientific complex digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeriodicCellComplex) and self.digest == other.digest

    @property
    def cell_counts(self) -> tuple[int, int, int, int]:
        return (
            self.boundary_1.target_cell_count,
            self.boundary_1.source_cell_count,
            self.boundary_2.source_cell_count,
            self.boundary_3.source_cell_count,
        )

    def _scientific_payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "face_placements": [face.to_dict() for face in self.face_placements],
            "tile_shells": [shell.to_dict() for shell in self.tile_shells],
            "boundary_1": self.boundary_1.to_dict(),
            "boundary_2": self.boundary_2.to_dict(),
            "boundary_3": self.boundary_3.to_dict(),
            "tile_shell_invariants": [value.to_dict() for value in self.tile_shell_invariants],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        payload = self._scientific_payload(True)
        payload["construction_witness_digests"] = list(self.construction_witness_digests)
        return payload

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        view: PeriodicNetView,
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        face_certificates: Sequence[FacePlacementCertificate],
        selected_witnesses: Sequence[FaceEmbeddingWitness],
        compatibility: FaceCompatibilityConstraintSystem | None = None,
    ) -> "PeriodicCellComplex":
        """Replay construction and reject any noncanonical or tampered payload."""

        try:
            shell_payloads = payload["tile_shells"]
            if not isinstance(shell_payloads, Sequence) or isinstance(shell_payloads, (str, bytes)):
                raise PeriodicCellComplexSerializationError("tile_shells must be a sequence.")
            shells = tuple(
                PeriodicTileShell(
                    shell_payload["tile_index"],
                    tuple(
                        _term_from_payload(term, name=f"tile_shells[{shell_index}].face_incidences")
                        for term in shell_payload["face_incidences"]
                    ),
                    shell_payload.get("label", ""),
                )
                for shell_index, shell_payload in enumerate(shell_payloads)
            )
            rebuilt = build_periodic_cell_complex(
                view,
                embedding,
                ring_index,
                face_certificates,
                selected_witnesses,
                shells,
                compatibility=compatibility,
            )
            if rebuilt.to_dict() != dict(payload):
                raise PeriodicCellComplexSerializationError(
                    "Serialized periodic cell complex is not canonical for the supplied sources."
                )
            return rebuilt
        except PeriodicCellComplexError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PeriodicCellComplexSerializationError(
                "Invalid PeriodicCellComplex payload."
            ) from exc


@dataclass(frozen=True, order=True, slots=True)
class TilePlacementRef:
    """One translated placement of a scientific tile orbit."""

    tile_index: int
    image_shift: LatticeShift = ZERO_SHIFT

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_index", _nonnegative(self.tile_index, name="tile_index"))
        try:
            object.__setattr__(self, "image_shift", coerce_lattice_shift(self.image_shift, name="image_shift"))
        except ValueError as exc:
            raise PeriodicCellComplexInputError(str(exc)) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"tile_index": self.tile_index, "image_shift": list(self.image_shift)}


@dataclass(frozen=True, order=True, slots=True)
class AuxiliaryVertexRef:
    """One explicit image of an auxiliary periodic partition vertex orbit."""

    vertex_index: int
    image_shift: LatticeShift = ZERO_SHIFT

    def __post_init__(self) -> None:
        object.__setattr__(self, "vertex_index", _nonnegative(self.vertex_index, name="vertex_index"))
        try:
            object.__setattr__(self, "image_shift", coerce_lattice_shift(self.image_shift, name="image_shift"))
        except ValueError as exc:
            raise PeriodicCellComplexInputError(str(exc)) from exc

    def to_dict(self) -> dict[str, Any]:
        return {"vertex_index": self.vertex_index, "image_shift": list(self.image_shift)}


@dataclass(frozen=True, slots=True)
class AuxiliaryVertexOrbit:
    """One auxiliary vertex orbit in canonical fractional coordinates."""

    vertex_index: int
    fractional_coordinate: RationalVector3

    def __post_init__(self) -> None:
        index = _nonnegative(self.vertex_index, name="vertex_index")
        point = _coerce_point(self.fractional_coordinate, name="fractional_coordinate")
        if any(value < 0 or value >= 1 for value in point):
            raise PeriodicCellComplexInputError("Auxiliary orbit coordinates must lie in [0, 1).")
        object.__setattr__(self, "vertex_index", index)
        object.__setattr__(self, "fractional_coordinate", point)

    def to_dict(self) -> dict[str, Any]:
        return {"vertex_index": self.vertex_index, "fractional_coordinate": _point_payload(self.fractional_coordinate)}


@dataclass(frozen=True, slots=True)
class PeriodicTetrahedron:
    """One oriented auxiliary tetrahedron assigned to a scientific tile placement."""

    tetrahedron_index: int
    vertices: tuple[AuxiliaryVertexRef, AuxiliaryVertexRef, AuxiliaryVertexRef, AuxiliaryVertexRef]
    tile_placement: TilePlacementRef

    def __post_init__(self) -> None:
        index = _nonnegative(self.tetrahedron_index, name="tetrahedron_index")
        vertices = tuple(self.vertices)
        if len(vertices) != 4 or any(not isinstance(value, AuxiliaryVertexRef) for value in vertices):
            raise PeriodicCellComplexInputError("A tetrahedron requires four AuxiliaryVertexRef records.")
        if len(set(vertices)) != 4:
            raise PeriodicCellComplexInputError("A tetrahedron's lifted vertices must be distinct.")
        if not isinstance(self.tile_placement, TilePlacementRef):
            raise PeriodicCellComplexInputError("tile_placement must be a TilePlacementRef.")
        object.__setattr__(self, "tetrahedron_index", index)
        object.__setattr__(self, "vertices", vertices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tetrahedron_index": self.tetrahedron_index,
            "vertices": [value.to_dict() for value in self.vertices],
            "tile_placement": self.tile_placement.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class PeriodicPartitionResources:
    """Transactional resource limits for exact partition certification."""

    max_auxiliary_vertices: int = 100_000
    max_tetrahedra: int = 500_000
    max_exact_tetrahedron_tests: int = 5_000_000
    max_facet_occurrences: int = 2_000_000

    def __post_init__(self) -> None:
        for name in (
            "max_auxiliary_vertices",
            "max_tetrahedra",
            "max_exact_tetrahedron_tests",
            "max_facet_occurrences",
        ):
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, slots=True)
class PeriodicFacetPair:
    """One exact pair of auxiliary tetrahedron facets modulo translation."""

    tetrahedron_i: int
    local_facet_i: int
    tetrahedron_j: int
    local_facet_j: int
    kind: PartitionFacetKind
    face_index: int | None = None
    face_image_shift: LatticeShift | None = None

    def __post_init__(self) -> None:
        for name in ("tetrahedron_i", "local_facet_i", "tetrahedron_j", "local_facet_j"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        kind = PartitionFacetKind(self.kind)
        object.__setattr__(self, "kind", kind)
        if kind is PartitionFacetKind.AUXILIARY_INTERNAL:
            if self.face_index is not None or self.face_image_shift is not None:
                raise PeriodicCellComplexInputError("Internal facets cannot carry scientific face identity.")
        else:
            if self.face_index is None or self.face_image_shift is None:
                raise PeriodicCellComplexInputError("Scientific interfaces require face index and image shift.")
            object.__setattr__(self, "face_index", _nonnegative(self.face_index, name="face_index"))
            try:
                object.__setattr__(self, "face_image_shift", coerce_lattice_shift(self.face_image_shift, name="face_image_shift"))
            except ValueError as exc:
                raise PeriodicCellComplexInputError(str(exc)) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "tetrahedron_i": self.tetrahedron_i,
            "local_facet_i": self.local_facet_i,
            "tetrahedron_j": self.tetrahedron_j,
            "local_facet_j": self.local_facet_j,
            "kind": self.kind.value,
            "face_index": self.face_index,
            "face_image_shift": None if self.face_image_shift is None else list(self.face_image_shift),
        }


@dataclass(frozen=True, slots=True)
class FaceTriangleCoverage:
    """Auxiliary facet orbit conforming to one triangle of a scientific face witness."""

    face_index: int
    triangle_index: int
    face_image_shift: LatticeShift
    facet_pair_index: int

    def __post_init__(self) -> None:
        for name in ("face_index", "triangle_index", "facet_pair_index"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        try:
            object.__setattr__(self, "face_image_shift", coerce_lattice_shift(self.face_image_shift, name="face_image_shift"))
        except ValueError as exc:
            raise PeriodicCellComplexInputError(str(exc)) from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "face_index": self.face_index,
            "triangle_index": self.triangle_index,
            "face_image_shift": list(self.face_image_shift),
            "facet_pair_index": self.facet_pair_index,
        }


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicPartitionCertificate:
    """Exact auxiliary proof that one scientific complex partitions the 3-torus."""

    periodic_cell_complex_digest: str
    periodic_net_embedding_digest: str
    auxiliary_vertices: tuple[AuxiliaryVertexOrbit, ...]
    tetrahedra: tuple[PeriodicTetrahedron, ...]
    facet_pairs: tuple[PeriodicFacetPair, ...]
    face_triangle_coverage: tuple[FaceTriangleCoverage, ...]
    overlap_candidate_set_digest: str
    exact_tetrahedron_test_count: int
    tile_fractional_volumes: tuple[Fraction, ...]
    total_fractional_volume: Fraction
    canonical_schema_version: str = CANONICAL_PERIODIC_PARTITION_CERTIFICATE_SCHEMA
    digest_algorithm: str = PERIODIC_CELL_COMPLEX_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _sha(self.periodic_cell_complex_digest, name="periodic_cell_complex_digest")
        _sha(self.periodic_net_embedding_digest, name="periodic_net_embedding_digest")
        _sha(self.overlap_candidate_set_digest, name="overlap_candidate_set_digest")
        vertices = tuple(self.auxiliary_vertices)
        tetrahedra = tuple(self.tetrahedra)
        facets = tuple(self.facet_pairs)
        coverage = tuple(self.face_triangle_coverage)
        if tuple(value.vertex_index for value in vertices) != tuple(range(len(vertices))):
            raise PeriodicCellComplexInputError("Auxiliary vertex IDs must be dense and ordered.")
        if tuple(value.tetrahedron_index for value in tetrahedra) != tuple(range(len(tetrahedra))):
            raise PeriodicCellComplexInputError("Tetrahedron IDs must be dense and ordered.")
        tests = _nonnegative(self.exact_tetrahedron_test_count, name="exact_tetrahedron_test_count")
        volumes = tuple(Fraction(value) for value in self.tile_fractional_volumes)
        total = Fraction(self.total_fractional_volume)
        if any(value <= 0 for value in volumes) or total != sum(volumes, Fraction(0)):
            raise PeriodicCellComplexInputError("Stored tile volumes are nonpositive or inconsistent.")
        if total != 1:
            raise PeriodicCellComplexInvariantError("A certified periodic partition must have exact fractional volume one.")
        if self.canonical_schema_version != CANONICAL_PERIODIC_PARTITION_CERTIFICATE_SCHEMA:
            raise PeriodicCellComplexInputError("Unsupported periodic-partition-certificate schema.")
        if self.digest_algorithm != PERIODIC_CELL_COMPLEX_DIGEST_ALGORITHM:
            raise PeriodicCellComplexInputError("Unsupported partition digest algorithm.")
        object.__setattr__(self, "auxiliary_vertices", vertices)
        object.__setattr__(self, "tetrahedra", tetrahedra)
        object.__setattr__(self, "facet_pairs", facets)
        object.__setattr__(self, "face_triangle_coverage", coverage)
        object.__setattr__(self, "exact_tetrahedron_test_count", tests)
        object.__setattr__(self, "tile_fractional_volumes", volumes)
        object.__setattr__(self, "total_fractional_volume", total)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise PeriodicCellComplexInputError("Stored partition-certificate digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, PeriodicPartitionCertificate) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "auxiliary_vertices": [value.to_dict() for value in self.auxiliary_vertices],
            "tetrahedra": [value.to_dict() for value in self.tetrahedra],
            "facet_pairs": [value.to_dict() for value in self.facet_pairs],
            "face_triangle_coverage": [value.to_dict() for value in self.face_triangle_coverage],
            "overlap_candidate_set_digest": self.overlap_candidate_set_digest,
            "exact_tetrahedron_test_count": self.exact_tetrahedron_test_count,
            "tile_fractional_volumes": [_fraction_payload(value) for value in self.tile_fractional_volumes],
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
        selected_witnesses: Sequence[FaceEmbeddingWitness],
        method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
        spatial_resources: PeriodicSpatialResources | None = None,
        resources: PeriodicPartitionResources | None = None,
    ) -> "PeriodicPartitionCertificate":
        """Replay exact partition certification and reject altered evidence."""

        try:
            vertex_payloads = payload["auxiliary_vertices"]
            tetrahedron_payloads = payload["tetrahedra"]
            if not isinstance(vertex_payloads, Sequence) or isinstance(vertex_payloads, (str, bytes)):
                raise PeriodicCellComplexSerializationError("auxiliary_vertices must be a sequence.")
            if not isinstance(tetrahedron_payloads, Sequence) or isinstance(tetrahedron_payloads, (str, bytes)):
                raise PeriodicCellComplexSerializationError("tetrahedra must be a sequence.")
            vertices = tuple(
                AuxiliaryVertexOrbit(
                    record["vertex_index"],
                    _point_from_payload(record["fractional_coordinate"], name=f"auxiliary_vertices[{index}].fractional_coordinate"),
                )
                for index, record in enumerate(vertex_payloads)
            )
            tetrahedra = []
            for index, record in enumerate(tetrahedron_payloads):
                refs = tuple(
                    AuxiliaryVertexRef(ref["vertex_index"], ref["image_shift"])
                    for ref in record["vertices"]
                )
                tile = record["tile_placement"]
                tetrahedra.append(
                    PeriodicTetrahedron(
                        record["tetrahedron_index"],
                        refs,  # type: ignore[arg-type]
                        TilePlacementRef(tile["tile_index"], tile["image_shift"]),
                    )
                )
            rebuilt = certify_periodic_tetrahedral_partition(
                complex_,
                embedding,
                ring_index,
                selected_witnesses,
                vertices,
                tuple(tetrahedra),
                method=method,
                spatial_resources=spatial_resources,
                resources=resources,
            )
            if rebuilt.to_dict() != dict(payload):
                raise PeriodicCellComplexSerializationError(
                    "Serialized partition certificate is not canonical for the supplied sources."
                )
            return rebuilt
        except PeriodicCellComplexError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PeriodicCellComplexSerializationError(
                "Invalid PeriodicPartitionCertificate payload."
            ) from exc


def _compose_boundaries(
    lower: PeriodicBoundaryOperator,
    upper: PeriodicBoundaryOperator,
) -> tuple[tuple[TranslatedCellTerm, ...], ...]:
    if lower.source_cell_count != upper.target_cell_count:
        raise PeriodicCellComplexInputError("Boundary operators cannot be composed.")
    result = []
    for column in upper.columns:
        expanded = []
        for upper_term in column:
            for lower_term in lower.columns[upper_term.cell_index]:
                expanded.append(lower_term.translated(upper_term.image_shift, upper_term.coefficient))
        result.append(_combine_terms(expanded))
    return tuple(result)


def _validate_sources(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
) -> None:
    if not isinstance(view, PeriodicNetView) or not isinstance(embedding, PeriodicNetEmbedding) or not isinstance(ring_index, PrimitiveRingIndex):
        raise PeriodicCellComplexInputError("view, embedding, and ring_index have invalid types.")
    if not view.natural_tiling_eligible:
        raise PeriodicCellComplexInputError(
            "The first Stage-9 backend requires one connected three-periodic net with translation rank three and subgroup index one."
        )
    if embedding.edge_curve_model is not ProjectedEdgeCurveModel.STRAIGHT_SEGMENT:
        raise PeriodicCellComplexInputError("The first Stage-9 backend requires straight projected edges.")
    if (
        embedding.periodic_net_view_digest != view.digest
        or embedding.topology_graph_digest != view.source_graph_digest
        or ring_index.topology_graph_digest != view.source_graph_digest
        or tuple(embedding.edge_keys) != tuple(view.edge_keys)
        or tuple(ring_index.catalog.edge_searches[index].edge_key for index in range(ring_index.edge_count)) != tuple(view.edge_keys)
    ):
        raise PeriodicCellComplexInputError("Cell-complex sources do not share exact graph/view/embedding identity.")


def _validate_face_selection(
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    certificates: Sequence[FacePlacementCertificate],
    witnesses: Sequence[FaceEmbeddingWitness],
    compatibility: FaceCompatibilityConstraintSystem | None,
) -> tuple[tuple[FacePlacementCertificate, ...], tuple[FaceEmbeddingWitness, ...]]:
    certs = tuple(certificates)
    selected = tuple(witnesses)
    if not certs or len(certs) != len(selected):
        raise PeriodicCellComplexInputError("Face certificates and selected witnesses must be nonempty and aligned.")
    if len({cert.face_placement.digest for cert in certs}) != len(certs):
        raise PeriodicCellComplexInputError("Selected scientific faces must be unique.")
    for certificate, witness in zip(certs, selected, strict=True):
        if certificate.status is not FacePlacementStatus.CERTIFIED_ADMISSIBLE:
            raise PeriodicCellComplexInputError("Every selected face requires a certified admissible witness.")
        if certificate.face_placement.periodic_net_embedding_digest != embedding.digest:
            raise PeriodicCellComplexInputError("A selected face belongs to another embedding.")
        if certificate.face_placement.primitive_ring_catalog_digest != ring_index.catalog_digest:
            raise PeriodicCellComplexInputError("A selected face belongs to another primitive-ring catalog.")
        if witness not in certificate.admissible_witnesses:
            raise PeriodicCellComplexInputError("The selected witness is not admissible under its face certificate.")
    if compatibility is not None:
        if not isinstance(compatibility, FaceCompatibilityConstraintSystem):
            raise PeriodicCellComplexInputError("compatibility must be a FaceCompatibilityConstraintSystem.")
        expected_certificates = tuple(sorted(cert.digest for cert in certs))
        if compatibility.face_certificate_digests != expected_certificates:
            raise PeriodicCellComplexInputError("Compatibility system does not cover exactly the selected face certificates.")
        assignments = frozenset(
            FaceWitnessAssignment(face.face_placement.digest, witness.witness_id, witness.digest)
            for face, witness in zip(certs, selected, strict=True)
        )
        if not assignments.issubset(frozenset(compatibility.assignments)):
            raise PeriodicCellComplexInputError("Selected witnesses are absent from the compatibility domain.")
        for constraint in compatibility.constraints:
            if set(constraint.assignments).issubset(assignments):
                if constraint.kind is FaceConstraintKind.UNRESOLVED:
                    raise PeriodicCellComplexInvariantError("The selected face realization retains an unresolved compatibility constraint.")
                raise PeriodicCellComplexInvariantError("The selected face realization violates a finite compatibility constraint.")
    return certs, selected


def _edge_boundary_columns(view: PeriodicNetView) -> tuple[tuple[TranslatedCellTerm, ...], ...]:
    vertex_position = {atom: index for index, atom in enumerate(view.vertex_atom_indices)}
    columns = []
    for edge in view.edge_keys:
        columns.append(
            _combine_terms(
                (
                    TranslatedCellTerm(vertex_position[edge.vertex_i], ZERO_SHIFT, -1),
                    TranslatedCellTerm(vertex_position[edge.vertex_j], edge.image_shift, 1),
                )
            )
        )
    return tuple(columns)


def _face_boundary_column(face: FacePlacement, ring_index: PrimitiveRingIndex) -> tuple[TranslatedCellTerm, ...]:
    ring = ring_index.ring_for_key(face.ring_placement.ring_key)
    terms = []
    for step, source in zip(ring.steps, ring.vertex_walk, strict=True):
        edge_key = ring_index.catalog.edge_searches[step.edge_index].edge_key
        physical_source_shift = add_shift(source.image_shift, face.ring_placement.image_shift)
        anchor = physical_edge_anchor(physical_source_shift, edge_key.image_shift, step.orientation)
        terms.append(
            TranslatedCellTerm(
                step.edge_index,
                anchor,
                step.orientation * face.orientation,
            )
        )
    return _combine_terms(terms)


def _tile_shell_invariant(
    shell: PeriodicTileShell,
    face_boundaries: PeriodicBoundaryOperator,
    edge_boundaries: PeriodicBoundaryOperator,
) -> TileShellInvariant:
    face_occurrences = list(shell.face_incidences)
    raw_edge_occurrences: dict[tuple[int, LatticeShift], list[tuple[int, int]]] = defaultdict(list)
    edge_signed = Counter()
    for face_position, face_term in enumerate(face_occurrences):
        for edge_term in face_boundaries.columns[face_term.cell_index]:
            key = (edge_term.cell_index, add_shift(face_term.image_shift, edge_term.image_shift))
            sign = face_term.coefficient * edge_term.coefficient
            raw_edge_occurrences[key].append((face_position, sign))
            edge_signed[key] += sign
    nonbranching = bool(raw_edge_occurrences) and all(len(values) == 2 for values in raw_edge_occurrences.values())
    orientable = nonbranching and all(value == 0 for value in edge_signed.values())
    adjacency: dict[int, set[int]] = {index: set() for index in range(len(face_occurrences))}
    for values in raw_edge_occurrences.values():
        for left, right in itertools.combinations((item[0] for item in values), 2):
            adjacency[left].add(right)
            adjacency[right].add(left)
    visited: set[int] = set()
    if adjacency:
        queue = deque((0,))
        while queue:
            value = queue.popleft()
            if value in visited:
                continue
            visited.add(value)
            queue.extend(adjacency[value] - visited)
    connected = len(visited) == len(face_occurrences)
    vertex_instances: set[tuple[int, LatticeShift]] = set()
    for edge_index, shift in raw_edge_occurrences:
        for vertex_term in edge_boundaries.columns[edge_index]:
            vertex_instances.add((vertex_term.cell_index, add_shift(shift, vertex_term.image_shift)))
    euler = len(vertex_instances) - len(raw_edge_occurrences) + len(face_occurrences)
    return TileShellInvariant(
        shell.tile_index,
        len(vertex_instances),
        len(raw_edge_occurrences),
        len(face_occurrences),
        euler,
        connected,
        nonbranching,
        orientable,
    )


def build_periodic_cell_complex(
    view: PeriodicNetView,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    face_certificates: Sequence[FacePlacementCertificate],
    selected_witnesses: Sequence[FaceEmbeddingWitness],
    tile_shells: Sequence[PeriodicTileShell],
    *,
    compatibility: FaceCompatibilityConstraintSystem | None = None,
) -> PeriodicCellComplex:
    """Build and validate one scientific translation-labelled cell complex."""

    _validate_sources(view, embedding, ring_index)
    certificates, witnesses = _validate_face_selection(
        embedding, ring_index, face_certificates, selected_witnesses, compatibility
    )
    shells = tuple(tile_shells)
    if not shells or tuple(shell.tile_index for shell in shells) != tuple(range(len(shells))):
        raise PeriodicCellComplexInputError("tile_shells must be nonempty with dense ordered IDs.")
    if any(term.cell_index >= len(certificates) for shell in shells for term in shell.face_incidences):
        raise PeriodicCellComplexInputError("A tile shell references an invalid face orbit.")
    boundary_1 = PeriodicBoundaryOperator(1, len(view.edge_keys), len(view.vertex_atom_indices), _edge_boundary_columns(view))
    boundary_2 = PeriodicBoundaryOperator(
        2,
        len(certificates),
        len(view.edge_keys),
        tuple(_face_boundary_column(cert.face_placement, ring_index) for cert in certificates),
    )
    boundary_3 = PeriodicBoundaryOperator(
        3,
        len(shells),
        len(certificates),
        tuple(shell.face_incidences for shell in shells),
    )
    invariants = tuple(_tile_shell_invariant(shell, boundary_2, boundary_1) for shell in shells)
    return PeriodicCellComplex(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        periodic_net_embedding_digest=embedding.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        face_placements=tuple(cert.face_placement for cert in certificates),
        tile_shells=shells,
        boundary_1=boundary_1,
        boundary_2=boundary_2,
        boundary_3=boundary_3,
        tile_shell_invariants=invariants,
        construction_witness_digests=tuple(witness.digest for witness in witnesses),
    )


def _auxiliary_coordinates(
    vertices: Sequence[AuxiliaryVertexOrbit],
    ref: AuxiliaryVertexRef,
) -> RationalVector3:
    try:
        point = vertices[ref.vertex_index].fractional_coordinate
    except IndexError as exc:
        raise PeriodicCellComplexInputError("Tetrahedron references an invalid auxiliary vertex orbit.") from exc
    return translate(point, ref.image_shift)


def _tetrahedron_coordinates(
    vertices: Sequence[AuxiliaryVertexOrbit], tetrahedron: PeriodicTetrahedron
) -> RationalTetrahedron:
    return tuple(_auxiliary_coordinates(vertices, ref) for ref in tetrahedron.vertices)  # type: ignore[return-value]


def _tetrahedron_volume6(tetrahedron: RationalTetrahedron) -> Fraction:
    return orient3d(*tetrahedron)


def _tetrahedron_edges(tetrahedron: RationalTetrahedron) -> tuple[RationalVector3, ...]:
    return tuple(subtract(tetrahedron[j], tetrahedron[i]) for i, j in itertools.combinations(range(4), 2))


def _tetrahedron_face_normals(tetrahedron: RationalTetrahedron) -> tuple[RationalVector3, ...]:
    result = []
    for omitted in range(4):
        face = tuple(tetrahedron[index] for index in range(4) if index != omitted)
        result.append(cross(subtract(face[1], face[0]), subtract(face[2], face[0])))
    return tuple(result)


def _projection_interval(tetrahedron: RationalTetrahedron, axis: RationalVector3) -> tuple[Fraction, Fraction]:
    values = tuple(dot(point, axis) for point in tetrahedron)
    return min(values), max(values)


def _point_tetrahedron_barycentric_signs(
    point: RationalVector3, tetrahedron: RationalTetrahedron
) -> tuple[Fraction, tuple[Fraction, Fraction, Fraction, Fraction]]:
    total = orient3d(*tetrahedron)
    if total == 0:
        raise PeriodicCellComplexInvariantError("Point classification received a degenerate tetrahedron.")
    signs = (
        orient3d(point, tetrahedron[1], tetrahedron[2], tetrahedron[3]),
        orient3d(tetrahedron[0], point, tetrahedron[2], tetrahedron[3]),
        orient3d(tetrahedron[0], tetrahedron[1], point, tetrahedron[3]),
        orient3d(tetrahedron[0], tetrahedron[1], tetrahedron[2], point),
    )
    return total, signs


def _strict_point_in_tetrahedron(point: RationalVector3, tetrahedron: RationalTetrahedron) -> bool:
    total, signs = _point_tetrahedron_barycentric_signs(point, tetrahedron)
    return all(value > 0 for value in signs) if total > 0 else all(value < 0 for value in signs)


def _closed_point_in_tetrahedron(point: RationalVector3, tetrahedron: RationalTetrahedron) -> bool:
    total, signs = _point_tetrahedron_barycentric_signs(point, tetrahedron)
    return all(value >= 0 for value in signs) if total > 0 else all(value <= 0 for value in signs)


def classify_tetrahedron_pair(
    left: RationalTetrahedron,
    right: RationalTetrahedron,
) -> TetrahedronPairRelation:
    """Classify exact interior overlap of two nondegenerate convex tetrahedra."""

    if _tetrahedron_volume6(left) == 0 or _tetrahedron_volume6(right) == 0:
        raise PeriodicCellComplexInputError("Tetrahedron pair classification requires nondegenerate tetrahedra.")
    axes = list(_tetrahedron_face_normals(left)) + list(_tetrahedron_face_normals(right))
    axes.extend(
        cross(left_edge, right_edge)
        for left_edge in _tetrahedron_edges(left)
        for right_edge in _tetrahedron_edges(right)
    )
    boundary_separator = False
    for axis in axes:
        if axis == ZERO_SHIFT:
            continue
        left_interval = _projection_interval(left, axis)
        right_interval = _projection_interval(right, axis)
        if left_interval[1] < right_interval[0] or right_interval[1] < left_interval[0]:
            return TetrahedronPairRelation.DISJOINT
        if left_interval[1] == right_interval[0] or right_interval[1] == left_interval[0]:
            boundary_separator = True
    if boundary_separator:
        return TetrahedronPairRelation.BOUNDARY_CONTACT
    if frozenset(left) == frozenset(right):
        return TetrahedronPairRelation.COINCIDENT_INTERIOR
    left_in_right = tuple(_closed_point_in_tetrahedron(point, right) for point in left)
    right_in_left = tuple(_closed_point_in_tetrahedron(point, left) for point in right)
    if all(left_in_right) or all(right_in_left):
        return TetrahedronPairRelation.CONTAINMENT_OVERLAP
    return TetrahedronPairRelation.IMPROPER_INTERIOR_OVERLAP


def _facet_vertices(tetrahedron: PeriodicTetrahedron, omitted: int) -> tuple[AuxiliaryVertexRef, AuxiliaryVertexRef, AuxiliaryVertexRef]:
    # Boundary orientation of [v0,v1,v2,v3] is sum_i (-1)^i [v0,...,hat(vi),...,v3].
    values = tuple(tetrahedron.vertices[index] for index in range(4) if index != omitted)
    if omitted % 2:
        values = (values[1], values[0], values[2])
    return values  # type: ignore[return-value]


def _canonical_ref_facet(
    refs: Sequence[AuxiliaryVertexRef],
) -> tuple[tuple[tuple[int, LatticeShift], ...], LatticeShift]:
    ordered = tuple(sorted((ref.vertex_index, ref.image_shift) for ref in refs))
    anchor = ordered[0][1]
    normalized = tuple(
        sorted(
            (
                vertex,
                (shift[0] - anchor[0], shift[1] - anchor[1], shift[2] - anchor[2]),
            )
            for vertex, shift in ordered
        )
    )
    return normalized, anchor


def _floor_fraction(value: Fraction) -> int:
    return value.numerator // value.denominator


def _canonical_triangle_geometry(
    points: Sequence[RationalVector3],
) -> tuple[tuple[RationalVector3, ...], LatticeShift]:
    if len(points) != 3:
        raise PeriodicCellComplexInputError("Triangle geometry requires three points.")
    base = tuple(_floor_fraction(min(point[axis] for point in points)) for axis in range(3))
    normalized = tuple(
        sorted(
            tuple(point[axis] - base[axis] for axis in range(3))  # type: ignore[misc]
            for point in points
        )
    )
    return normalized, base  # type: ignore[return-value]


def _triangle_orientation_sign(
    source: Sequence[RationalVector3],
    target: Sequence[RationalVector3],
) -> int:
    if set(source) != set(target):
        raise PeriodicCellComplexInvariantError("Triangle orientation comparison requires identical vertex sets.")
    permutation = tuple(target.index(value) for value in source)
    inversions = sum(permutation[i] > permutation[j] for i in range(3) for j in range(i + 1, 3))
    return -1 if inversions % 2 else 1


def _witness_triangle_records(
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    witnesses: Sequence[FaceEmbeddingWitness],
) -> dict[tuple[RationalVector3, ...], list[tuple[int, int, LatticeShift, tuple[RationalVector3, ...]]]]:
    result: dict[tuple[RationalVector3, ...], list[tuple[int, int, LatticeShift, tuple[RationalVector3, ...]]]] = defaultdict(list)
    for face_index, (face, witness) in enumerate(zip(complex_.face_placements, witnesses, strict=True)):
        if witness.digest != complex_.construction_witness_digests[face_index]:
            raise PeriodicCellComplexInputError("Partition witness selection disagrees with the scientific complex construction provenance.")
        ring = ring_index.ring_for_key(face.ring_placement.ring_key)
        canonical_refs = tuple(
            (ref.atom_index, add_shift(ref.image_shift, face.ring_placement.image_shift))
            for ref in ring.vertex_walk
        )
        permutation = CycleParameterization(0, face.orientation).vertex_permutation(ring.size)
        refs = tuple(canonical_refs[index] for index in permutation)
        points = tuple(embedding.fractional_coordinate(atom, shift) for atom, shift in refs)
        for triangle_index, triangle in enumerate(witness.triangles):
            oriented = tuple(points[index] for index in triangle)
            key, base = _canonical_triangle_geometry(oriented)
            result[key].append((face_index, triangle_index, base, oriented))
    return result


def certify_periodic_tetrahedral_partition(
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    selected_witnesses: Sequence[FaceEmbeddingWitness],
    auxiliary_vertices: Sequence[AuxiliaryVertexOrbit],
    tetrahedra: Sequence[PeriodicTetrahedron],
    *,
    method: PeriodicSpatialMethod = PeriodicSpatialMethod.AUTO,
    spatial_resources: PeriodicSpatialResources | None = None,
    resources: PeriodicPartitionResources | None = None,
) -> PeriodicPartitionCertificate:
    """Certify an explicit conforming periodic tetrahedral partition."""

    if not isinstance(complex_, PeriodicCellComplex):
        raise PeriodicCellComplexInputError("complex_ must be a PeriodicCellComplex.")
    if complex_.periodic_net_embedding_digest != embedding.digest or complex_.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise PeriodicCellComplexInputError("Partition sources disagree with the scientific complex.")
    witnesses = tuple(selected_witnesses)
    if len(witnesses) != len(complex_.face_placements):
        raise PeriodicCellComplexInputError("One selected witness is required for each scientific face orbit.")
    active = resources or PeriodicPartitionResources()
    vertices = tuple(auxiliary_vertices)
    tets = tuple(tetrahedra)
    if len(vertices) > active.max_auxiliary_vertices or len(tets) > active.max_tetrahedra:
        raise PeriodicCellComplexResourceError("Auxiliary partition size exceeds declared resources.")
    if tuple(value.vertex_index for value in vertices) != tuple(range(len(vertices))):
        raise PeriodicCellComplexInputError("Auxiliary vertex IDs must be dense and ordered.")
    if not tets or tuple(value.tetrahedron_index for value in tets) != tuple(range(len(tets))):
        raise PeriodicCellComplexInputError("Tetrahedron IDs must be nonempty, dense, and ordered.")
    if 4 * len(tets) > active.max_facet_occurrences:
        raise PeriodicCellComplexResourceError("Auxiliary facet count exceeds max_facet_occurrences.")
    if any(tet.tile_placement.tile_index >= complex_.boundary_3.source_cell_count for tet in tets):
        raise PeriodicCellComplexInputError("A tetrahedron references an invalid scientific tile orbit.")
    coordinates = tuple(_tetrahedron_coordinates(vertices, tet) for tet in tets)
    oriented_coordinates = []
    normalized_tets = []
    for tet, points in zip(tets, coordinates, strict=True):
        volume6 = _tetrahedron_volume6(points)
        if volume6 == 0:
            raise PeriodicCellComplexInvariantError("Auxiliary partition contains a degenerate tetrahedron.")
        if volume6 < 0:
            refs = (tet.vertices[1], tet.vertices[0], tet.vertices[2], tet.vertices[3])
            tet = PeriodicTetrahedron(tet.tetrahedron_index, refs, tet.tile_placement)
            points = _tetrahedron_coordinates(vertices, tet)
        normalized_tets.append(tet)
        oriented_coordinates.append(points)
    tets = tuple(normalized_tets)
    coordinates = tuple(oriented_coordinates)

    supports = tuple(PeriodicAabbSupport.from_points(index, points) for index, points in enumerate(coordinates))
    candidate_set = build_periodic_overlap_candidates(
        supports,
        source_digest=complex_.digest,
        method=method,
        resources=spatial_resources,
    )
    exact_tests = 0
    for candidate in candidate_set.candidates:
        exact_tests += 1
        if exact_tests > active.max_exact_tetrahedron_tests:
            raise PeriodicCellComplexResourceError("Exact tetrahedron-test count exceeded max_exact_tetrahedron_tests.")
        left = coordinates[candidate.object_i]
        right = tuple(translate(point, candidate.image_shift) for point in coordinates[candidate.object_j])
        relation = classify_tetrahedron_pair(left, right)  # type: ignore[arg-type]
        if relation not in (TetrahedronPairRelation.DISJOINT, TetrahedronPairRelation.BOUNDARY_CONTACT):
            raise PeriodicCellComplexInvariantError(
                f"Auxiliary tetrahedra have invalid periodic interior relation: {relation.value}."
            )

    facet_occurrences: dict[tuple[tuple[int, LatticeShift], ...], list[tuple[int, int, tuple[AuxiliaryVertexRef, ...], LatticeShift]]] = defaultdict(list)
    for tet in tets:
        for local_facet in range(4):
            refs = _facet_vertices(tet, local_facet)
            key, anchor = _canonical_ref_facet(refs)
            facet_occurrences[key].append((tet.tetrahedron_index, local_facet, refs, anchor))
    if any(len(values) != 2 for values in facet_occurrences.values()):
        raise PeriodicCellComplexInvariantError("Every periodic auxiliary triangle facet must have exactly two tetrahedral incidences.")

    witness_records = _witness_triangle_records(complex_, embedding, ring_index, witnesses)
    facet_pairs: list[PeriodicFacetPair] = []
    coverage: list[FaceTriangleCoverage] = []
    # Accumulate auxiliary triangles by complete scientific face side.  A
    # scientific face may contain several witness triangles, but its boundary
    # coefficient in ∂3 is exactly one signed translated face term.
    derived_face_sides: dict[tuple[int, int, LatticeShift], list[tuple[int, int]]] = defaultdict(list)
    covered_face_triangles: Counter[tuple[int, int]] = Counter()
    for values in sorted(facet_occurrences.values(), key=lambda items: (items[0][0], items[0][1])):
        left, right = values
        left_tet = tets[left[0]]
        right_tet = tets[right[0]]
        left_points = tuple(_auxiliary_coordinates(vertices, ref) for ref in left[2])
        right_points = tuple(_auxiliary_coordinates(vertices, ref) for ref in right[2])
        translation = tuple(left[3][axis] - right[3][axis] for axis in range(3))
        right_translated = tuple(translate(point, translation) for point in right_points)
        if set(left_points) != set(right_translated):
            raise PeriodicCellComplexInvariantError("Periodically paired auxiliary facets do not coincide exactly.")
        if _triangle_orientation_sign(left_points, right_translated) != -1:
            raise PeriodicCellComplexInvariantError("Paired auxiliary facets do not carry opposite induced orientations.")
        left_tile_placement = left_tet.tile_placement
        right_tile_placement = TilePlacementRef(
            right_tet.tile_placement.tile_index,
            add_shift(right_tet.tile_placement.image_shift, translation),
        )
        same_tile = left_tile_placement == right_tile_placement
        if same_tile:
            facet_pairs.append(PeriodicFacetPair(left[0], left[1], right[0], right[1], PartitionFacetKind.AUXILIARY_INTERNAL))
            continue
        geometry_key, geometry_base = _canonical_triangle_geometry(left_points)
        matches = witness_records.get(geometry_key, ())
        if len(matches) != 1:
            raise PeriodicCellComplexInvariantError("A scientific interface facet must match exactly one selected face-witness triangle orbit.")
        face_index, triangle_index, witness_base, witness_points = matches[0]
        face_shift = tuple(geometry_base[axis] - witness_base[axis] for axis in range(3))
        shifted_witness = tuple(translate(point, face_shift) for point in witness_points)
        left_sign = _triangle_orientation_sign(left_points, shifted_witness)
        right_sign = -left_sign
        pair_index = len(facet_pairs)
        facet_pairs.append(
            PeriodicFacetPair(
                left[0], left[1], right[0], right[1],
                PartitionFacetKind.SCIENTIFIC_INTERFACE,
                face_index,
                face_shift,
            )
        )
        coverage.append(FaceTriangleCoverage(face_index, triangle_index, face_shift, pair_index))
        covered_face_triangles[(face_index, triangle_index)] += 1
        for tile_placement, sign in ((left_tile_placement, left_sign), (right_tile_placement, right_sign)):
            relative_shift = tuple(face_shift[axis] - tile_placement.image_shift[axis] for axis in range(3))
            derived_face_sides[(tile_placement.tile_index, face_index, relative_shift)].append(
                (triangle_index, sign)
            )

    expected_triangles = {
        (face_index, triangle_index)
        for face_index, witness in enumerate(witnesses)
        for triangle_index in range(len(witness.triangles))
    }
    if set(covered_face_triangles) != expected_triangles or any(value != 1 for value in covered_face_triangles.values()):
        raise PeriodicCellComplexInvariantError("Scientific face witnesses are not covered exactly once by auxiliary interface-facet orbits.")
    derived_shell_terms: dict[int, list[TranslatedCellTerm]] = defaultdict(list)
    expected_triangle_indices = {
        face_index: set(range(len(witness.triangles)))
        for face_index, witness in enumerate(witnesses)
    }
    for (tile_index, face_index, relative_shift), records in derived_face_sides.items():
        triangle_indices = {triangle_index for triangle_index, _ in records}
        signs = {sign for _, sign in records}
        if triangle_indices != expected_triangle_indices[face_index] or len(records) != len(triangle_indices):
            raise PeriodicCellComplexInvariantError(
                "An auxiliary tile side does not cover every triangle of its selected scientific face witness exactly once."
            )
        if len(signs) != 1:
            raise PeriodicCellComplexInvariantError(
                "Auxiliary triangles assigned to one scientific face side do not carry a common orientation."
            )
        derived_shell_terms[tile_index].append(
            TranslatedCellTerm(face_index, relative_shift, next(iter(signs)))
        )
    for tile_index, expected_column in enumerate(complex_.boundary_3.columns):
        derived = _combine_terms(derived_shell_terms[tile_index])
        if derived != expected_column:
            raise PeriodicCellComplexInvariantError("Auxiliary partition induces a tile shell different from the scientific cell complex.")

    tile_volume6 = [Fraction(0) for _ in range(complex_.boundary_3.source_cell_count)]
    for tet, points in zip(tets, coordinates, strict=True):
        tile_volume6[tet.tile_placement.tile_index] += _tetrahedron_volume6(points)
    tile_volumes = tuple(value / 6 for value in tile_volume6)
    total = sum(tile_volumes, Fraction(0))
    if any(value <= 0 for value in tile_volumes):
        raise PeriodicCellComplexInvariantError("Every scientific tile orbit must receive positive auxiliary volume.")
    if total != 1:
        raise PeriodicCellComplexInvariantError("Exact tetrahedral volume closure failed for the periodic reference domain.")

    return PeriodicPartitionCertificate(
        periodic_cell_complex_digest=complex_.digest,
        periodic_net_embedding_digest=embedding.digest,
        auxiliary_vertices=vertices,
        tetrahedra=tets,
        facet_pairs=tuple(facet_pairs),
        face_triangle_coverage=tuple(sorted(coverage, key=lambda value: (value.face_index, value.triangle_index, value.face_image_shift))),
        overlap_candidate_set_digest=candidate_set.digest,
        exact_tetrahedron_test_count=exact_tests,
        tile_fractional_volumes=tile_volumes,
        total_fractional_volume=total,
    )


__all__ = [
    "AuxiliaryVertexOrbit",
    "AuxiliaryVertexRef",
    "CANONICAL_PERIODIC_CELL_COMPLEX_SCHEMA",
    "CANONICAL_PERIODIC_PARTITION_CERTIFICATE_SCHEMA",
    "FaceTriangleCoverage",
    "PERIODIC_CELL_COMPLEX_DIGEST_ALGORITHM",
    "PartitionFacetKind",
    "PeriodicBoundaryOperator",
    "PeriodicCellComplex",
    "PeriodicCellComplexError",
    "PeriodicCellComplexInputError",
    "PeriodicCellComplexInvariantError",
    "PeriodicCellComplexResourceError",
    "PeriodicCellComplexSerializationError",
    "PeriodicFacetPair",
    "PeriodicPartitionCertificate",
    "PeriodicPartitionResources",
    "PeriodicTetrahedron",
    "PeriodicTileShell",
    "TetrahedronPairRelation",
    "TilePlacementRef",
    "TileShellInvariant",
    "TranslatedCellTerm",
    "build_periodic_cell_complex",
    "certify_periodic_tetrahedral_partition",
    "classify_tetrahedron_pair",
]
