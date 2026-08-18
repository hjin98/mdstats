"""Authoritative Euclidean embeddings of exact periodic-net views.

The first backend combines the exact rational barycentric placement of
Delgado-Friedrichs (2004) with the complete exact periodic-net automorphism group
of Delgado-Friedrichs and O'Keeffe (2003).  The Euclidean lattice metric is an
mdstats construction derived from the inverse second moment of all projected
quotient-edge vectors.  This metric is exact, invariant under every discovered
automorphism, and covariant under unimodular lattice-basis changes.

The module deliberately stops before global periodic edge-intersection
certification.  It validates distinct lifted vertices, nonzero edge lengths,
noncoincident straight projected edges, and exact symmetry equivariance.  The
periodic spatial broad phase and exact crossing predicates belong to later
stages.

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
O. Delgado-Friedrichs and M. O'Keeffe, Acta Cryst. A 59, 351-360 (2003),
doi:10.1107/S0108767303012017.
O. Delgado-Friedrichs, in Graph Drawing, LNCS 2912, 178-189 (2004),
doi:10.1007/978-3-540-24595-7_17.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
from math import gcd, lcm
import hashlib
import json
from numbers import Integral
from types import MappingProxyType
from typing import Any, Mapping, Sequence, TypeAlias

import numpy as np

from ._periodic_graph import (
    IntMatrix3,
    LatticeShift,
    coerce_int_matrix3,
    coerce_lattice_shift,
)
from .framework_topology import FrameworkEdgeKey
from .net_symmetry_discovery import (
    BARYCENTRIC_STAR_DISCOVERY_METHOD,
    PeriodicNetSymmetryDiscovery,
)
from .periodic_barycentric import RationalVector3
from .periodic_net_view import PeriodicNetView

CANONICAL_PERIODIC_NET_EMBEDDING_SCHEMA = "mdstats.periodic-net-embedding.v1"
PERIODIC_NET_EMBEDDING_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
PERIODIC_NET_EMBEDDING_DISCOVERY_CERTIFICATE_SCHEMA = (
    "mdstats.periodic-net-embedding-discovery-certificate.v1"
)

RationalMatrix3: TypeAlias = tuple[
    tuple[Fraction, Fraction, Fraction],
    tuple[Fraction, Fraction, Fraction],
    tuple[Fraction, Fraction, Fraction],
]
FloatVector3: TypeAlias = tuple[float, float, float]


class PeriodicNetEmbeddingError(ValueError):
    """Base exception for authoritative periodic-net embeddings."""


class PeriodicNetEmbeddingInputError(PeriodicNetEmbeddingError):
    """Raised when embedding inputs or records are malformed."""


class PeriodicNetEmbeddingUnsupportedError(PeriodicNetEmbeddingError):
    """Raised when the first exact embedding backend does not support a view."""


class PeriodicNetEmbeddingInvariantError(PeriodicNetEmbeddingError):
    """Raised when exact metric or symmetry identities fail."""


class PeriodicNetEmbeddingResourceError(PeriodicNetEmbeddingError):
    """Raised when exact construction exceeds a declared resource bound."""


class PeriodicNetEmbeddingSerializationError(PeriodicNetEmbeddingError):
    """Raised when serialized embedding data fail source validation."""


class PeriodicNetEmbeddingMethod(str, Enum):
    """Supported authoritative reference-embedding constructions."""

    BARYCENTRIC_EDGE_COVARIANCE = "barycentric-edge-covariance-v1"


class ProjectedEdgeCurveModel(str, Enum):
    """Geometric model used for one projected net edge."""

    STRAIGHT_SEGMENT = "straight-segment-v1"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise PeriodicNetEmbeddingInputError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise PeriodicNetEmbeddingInputError(f"{name} must be a positive integer.")
    return result


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _fraction_from_payload(payload: Sequence[Any]) -> Fraction:
    if len(payload) != 2:
        raise PeriodicNetEmbeddingSerializationError(
            "Serialized rational values require [numerator, denominator]."
        )
    return Fraction(int(payload[0]), int(payload[1]))


def _fraction_bits(value: Fraction) -> int:
    return max(abs(value.numerator).bit_length(), value.denominator.bit_length())


def _check_fraction_bits(
    values: Sequence[Fraction], *, max_fraction_bits: int, context: str
) -> None:
    if any(_fraction_bits(value) > max_fraction_bits for value in values):
        raise PeriodicNetEmbeddingResourceError(
            f"Exact {context} exceeded max_metric_fraction_bits."
        )


def _add_rational_vectors(
    left: RationalVector3, right: RationalVector3
) -> RationalVector3:
    return tuple(a + b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def _subtract_rational_vectors(
    left: RationalVector3, right: RationalVector3
) -> RationalVector3:
    return tuple(a - b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def _negate_rational_vector(value: RationalVector3) -> RationalVector3:
    return tuple(-component for component in value)  # type: ignore[return-value]


def _shift_as_rational(shift: LatticeShift) -> RationalVector3:
    return tuple(Fraction(component) for component in shift)  # type: ignore[return-value]


def _matvec_fraction(
    matrix: IntMatrix3, vector: RationalVector3
) -> RationalVector3:
    return tuple(
        sum(Fraction(matrix[row][column]) * vector[column] for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _transpose_int(matrix: IntMatrix3) -> IntMatrix3:
    return tuple(
        tuple(matrix[column][row] for column in range(3)) for row in range(3)
    )  # type: ignore[return-value]


def _multiply_int_matrices(left: IntMatrix3, right: IntMatrix3) -> IntMatrix3:
    return tuple(
        tuple(
            sum(left[row][inner] * right[inner][column] for inner in range(3))
            for column in range(3)
        )
        for row in range(3)
    )  # type: ignore[return-value]


def _determinant_int(matrix: IntMatrix3) -> int:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _determinant_fraction(matrix: RationalMatrix3) -> Fraction:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _inverse_fraction_matrix3(matrix: RationalMatrix3) -> RationalMatrix3:
    determinant = _determinant_fraction(matrix)
    if determinant == 0:
        raise PeriodicNetEmbeddingUnsupportedError(
            "Projected edge vectors do not span a three-dimensional metric space."
        )
    a = matrix
    cofactors: RationalMatrix3 = (
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
    return tuple(
        tuple(cofactors[column][row] / determinant for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _primitive_integral_matrix(matrix: RationalMatrix3) -> IntMatrix3:
    denominator_lcm = 1
    for row in matrix:
        for value in row:
            denominator_lcm = lcm(denominator_lcm, value.denominator)
    integer_rows = tuple(
        tuple(int(value * denominator_lcm) for value in row) for row in matrix
    )
    divisor = 0
    for row in integer_rows:
        for value in row:
            divisor = gcd(divisor, abs(value))
    if divisor == 0:
        raise PeriodicNetEmbeddingInvariantError(
            "The exact lattice metric collapsed to the zero matrix."
        )
    primitive = tuple(
        tuple(value // divisor for value in row) for row in integer_rows
    )
    return coerce_int_matrix3(primitive, name="primitive_gram_matrix")


def _quadratic_form(matrix: IntMatrix3, vector: RationalVector3) -> Fraction:
    transformed = _matvec_fraction(matrix, vector)
    return sum(
        vector[axis] * transformed[axis] for axis in range(3)
    )


def _fractional_part(value: Fraction) -> Fraction:
    return value - (value.numerator // value.denominator)


def _wrap_vector(vector: RationalVector3) -> RationalVector3:
    return tuple(_fractional_part(value) for value in vector)  # type: ignore[return-value]


def _difference_is_integer(
    left: RationalVector3, right: RationalVector3
) -> bool:
    return all((a - b).denominator == 1 for a, b in zip(left, right, strict=True))


def _edge_displacement(
    coordinates_by_atom: Mapping[int, RationalVector3], edge_key: FrameworkEdgeKey
) -> RationalVector3:
    return _subtract_rational_vectors(
        _add_rational_vectors(
            coordinates_by_atom[edge_key.vertex_j],
            _shift_as_rational(edge_key.image_shift),
        ),
        coordinates_by_atom[edge_key.vertex_i],
    )


def _edge_covariance(
    coordinates_by_atom: Mapping[int, RationalVector3],
    edge_keys: Sequence[FrameworkEdgeKey],
) -> RationalMatrix3:
    values = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for edge_key in edge_keys:
        displacement = _edge_displacement(coordinates_by_atom, edge_key)
        for row in range(3):
            for column in range(3):
                values[row][column] += displacement[row] * displacement[column]
    return tuple(tuple(row) for row in values)  # type: ignore[return-value]


def _coincident_straight_edge_pairs(
    coordinates_by_atom: Mapping[int, RationalVector3],
    edge_keys: Sequence[FrameworkEdgeKey],
) -> tuple[tuple[FrameworkEdgeKey, FrameworkEdgeKey], ...]:
    endpoints: list[tuple[RationalVector3, RationalVector3, RationalVector3]] = []
    for edge_key in edge_keys:
        start = coordinates_by_atom[edge_key.vertex_i]
        end = _add_rational_vectors(
            coordinates_by_atom[edge_key.vertex_j],
            _shift_as_rational(edge_key.image_shift),
        )
        endpoints.append((start, end, _subtract_rational_vectors(end, start)))
    pairs: list[tuple[FrameworkEdgeKey, FrameworkEdgeKey]] = []
    for left_position, left_key in enumerate(edge_keys):
        left_start, left_end, left_displacement = endpoints[left_position]
        for right_position in range(left_position + 1, len(edge_keys)):
            right_key = edge_keys[right_position]
            right_start, right_end, right_displacement = endpoints[right_position]
            same = (
                left_displacement == right_displacement
                and _difference_is_integer(left_start, right_start)
            )
            reversed_same = (
                left_displacement == _negate_rational_vector(right_displacement)
                and _difference_is_integer(left_start, right_end)
            )
            if same or reversed_same:
                pairs.append((left_key, right_key))
    return tuple(pairs)


def _discovery_certificate_payload(
    discovery: PeriodicNetSymmetryDiscovery,
) -> dict[str, Any]:
    return {
        "canonical_schema_version": PERIODIC_NET_EMBEDDING_DISCOVERY_CERTIFICATE_SCHEMA,
        "periodic_net_view_digest": discovery.periodic_net_view_digest,
        "topology_graph_digest": discovery.topology_graph_digest,
        "method": discovery.method,
        "anchor_atom_index": discovery.anchor_atom_index,
        "source_frame": [
            {
                "edge_position": item.edge_position,
                "orientation": item.orientation,
            }
            for item in discovery.source_frame
        ],
        "barycentric_placement_digest": discovery.barycentric_placement.digest,
        "frame_trial_count": discovery.frame_trial_count,
        "candidate_operation_count": discovery.candidate_operation_count,
        "generator_operation_indices": list(discovery.generator_operation_indices),
        "periodic_net_symmetry_digest": discovery.symmetry.digest,
    }


def periodic_net_symmetry_discovery_certificate_digest(
    discovery: PeriodicNetSymmetryDiscovery,
) -> str:
    """Return the ring-independent completeness-certificate digest."""

    if not isinstance(discovery, PeriodicNetSymmetryDiscovery):
        raise PeriodicNetEmbeddingInputError(
            "discovery must be a PeriodicNetSymmetryDiscovery."
        )
    return _digest(_discovery_certificate_payload(discovery))


@dataclass(frozen=True, slots=True)
class PeriodicNetEmbeddingResources:
    """Execution limits for exact embedding construction."""

    max_vertices: int = 4096
    max_edges: int = 16384
    max_symmetry_operations: int = 2048
    max_metric_fraction_bits: int = 4096

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "max_vertices", _positive_int(self.max_vertices, name="max_vertices")
        )
        object.__setattr__(
            self, "max_edges", _positive_int(self.max_edges, name="max_edges")
        )
        object.__setattr__(
            self,
            "max_symmetry_operations",
            _positive_int(
                self.max_symmetry_operations, name="max_symmetry_operations"
            ),
        )
        object.__setattr__(
            self,
            "max_metric_fraction_bits",
            _positive_int(
                self.max_metric_fraction_bits, name="max_metric_fraction_bits"
            ),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_vertices": self.max_vertices,
            "max_edges": self.max_edges,
            "max_symmetry_operations": self.max_symmetry_operations,
            "max_metric_fraction_bits": self.max_metric_fraction_bits,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicNetEmbeddingResources":
        return cls(
            max_vertices=int(payload["max_vertices"]),
            max_edges=int(payload["max_edges"]),
            max_symmetry_operations=int(payload["max_symmetry_operations"]),
            max_metric_fraction_bits=int(payload["max_metric_fraction_bits"]),
        )


@dataclass(frozen=True, slots=True)
class EmbeddedStraightEdgeSegment:
    """One transient lifted straight segment from an authoritative embedding."""

    periodic_net_embedding_digest: str
    topology_graph_digest: str
    edge_key: FrameworkEdgeKey
    anchor_shift: LatticeShift
    start_fractional: RationalVector3
    end_fractional: RationalVector3
    start_cartesian: FloatVector3
    end_cartesian: FloatVector3
    primitive_squared_length: Fraction

    def __post_init__(self) -> None:
        if len(self.periodic_net_embedding_digest) != 64 or len(self.topology_graph_digest) != 64:
            raise PeriodicNetEmbeddingInputError(
                "Embedded segment source digests must be SHA-256 values."
            )
        if not isinstance(self.edge_key, FrameworkEdgeKey):
            raise PeriodicNetEmbeddingInputError(
                "edge_key must be a FrameworkEdgeKey."
            )
        try:
            anchor = coerce_lattice_shift(self.anchor_shift, name="anchor_shift")
        except ValueError as exc:
            raise PeriodicNetEmbeddingInputError(str(exc)) from exc
        start_fractional = tuple(Fraction(value) for value in self.start_fractional)
        end_fractional = tuple(Fraction(value) for value in self.end_fractional)
        if len(start_fractional) != 3 or len(end_fractional) != 3:
            raise PeriodicNetEmbeddingInputError(
                "Embedded segment fractional endpoints must have length three."
            )
        start_cartesian = tuple(float(value) for value in self.start_cartesian)
        end_cartesian = tuple(float(value) for value in self.end_cartesian)
        if len(start_cartesian) != 3 or len(end_cartesian) != 3:
            raise PeriodicNetEmbeddingInputError(
                "Embedded segment Cartesian endpoints must have length three."
            )
        squared = Fraction(self.primitive_squared_length)
        if squared <= 0:
            raise PeriodicNetEmbeddingInputError(
                "Embedded straight segments require positive squared length."
            )
        object.__setattr__(self, "anchor_shift", anchor)
        object.__setattr__(self, "start_fractional", start_fractional)
        object.__setattr__(self, "end_fractional", end_fractional)
        object.__setattr__(self, "start_cartesian", start_cartesian)
        object.__setattr__(self, "end_cartesian", end_cartesian)
        object.__setattr__(self, "primitive_squared_length", squared)


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicNetEmbedding:
    """Exact source-bound Euclidean reference realization of one periodic net."""

    periodic_net_view_digest: str
    topology_graph_digest: str
    periodic_net_symmetry_digest: str
    barycentric_placement_digest: str
    symmetry_discovery_certificate_digest: str
    method: PeriodicNetEmbeddingMethod
    edge_curve_model: ProjectedEdgeCurveModel
    anchor_atom_index: int
    vertex_atom_indices: tuple[int, ...]
    edge_keys: tuple[FrameworkEdgeKey, ...]
    fractional_coordinates: tuple[RationalVector3, ...]
    primitive_gram_matrix: IntMatrix3
    metric_determinant: int
    minimum_edge_length_squared: Fraction
    maximum_edge_length_squared: Fraction
    canonical_schema_version: str = CANONICAL_PERIODIC_NET_EMBEDDING_SCHEMA
    digest_algorithm: str = PERIODIC_NET_EMBEDDING_DIGEST_ALGORITHM
    digest: str = ""
    _vertex_position_by_atom: Mapping[int, int] = field(
        init=False, repr=False, compare=False, hash=False
    )
    _edge_position_by_key: Mapping[FrameworkEdgeKey, int] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        for name, value in (
            ("periodic_net_view_digest", self.periodic_net_view_digest),
            ("topology_graph_digest", self.topology_graph_digest),
            ("periodic_net_symmetry_digest", self.periodic_net_symmetry_digest),
            ("barycentric_placement_digest", self.barycentric_placement_digest),
            (
                "symmetry_discovery_certificate_digest",
                self.symmetry_discovery_certificate_digest,
            ),
        ):
            if not isinstance(value, str) or len(value) != 64:
                raise PeriodicNetEmbeddingInputError(
                    f"{name} must be a SHA-256 digest."
                )
        try:
            method = PeriodicNetEmbeddingMethod(self.method)
            edge_model = ProjectedEdgeCurveModel(self.edge_curve_model)
        except ValueError as exc:
            raise PeriodicNetEmbeddingInputError(
                "Unsupported embedding method or projected-edge model."
            ) from exc
        if isinstance(self.anchor_atom_index, bool) or int(self.anchor_atom_index) < 0:
            raise PeriodicNetEmbeddingInputError(
                "anchor_atom_index must be nonnegative."
            )
        vertices = tuple(int(value) for value in self.vertex_atom_indices)
        if not vertices or vertices != tuple(sorted(set(vertices))):
            raise PeriodicNetEmbeddingInputError(
                "vertex_atom_indices must be nonempty, sorted, and unique."
            )
        anchor = int(self.anchor_atom_index)
        if anchor not in vertices:
            raise PeriodicNetEmbeddingInputError(
                "anchor_atom_index must belong to vertex_atom_indices."
            )
        edge_keys = tuple(self.edge_keys)
        if not edge_keys or any(not isinstance(key, FrameworkEdgeKey) for key in edge_keys):
            raise PeriodicNetEmbeddingInputError(
                "edge_keys must contain at least one FrameworkEdgeKey."
            )
        if edge_keys != tuple(sorted(set(edge_keys))):
            raise PeriodicNetEmbeddingInputError(
                "edge_keys must be sorted and unique."
            )
        coordinates = tuple(
            tuple(Fraction(value) for value in coordinate)
            for coordinate in self.fractional_coordinates
        )
        if len(coordinates) != len(vertices) or any(len(item) != 3 for item in coordinates):
            raise PeriodicNetEmbeddingInputError(
                "fractional_coordinates must align with vertices and have length three."
            )
        if coordinates[vertices.index(anchor)] != (
            Fraction(0),
            Fraction(0),
            Fraction(0),
        ):
            raise PeriodicNetEmbeddingInputError(
                "The selected anchor fractional coordinate must be exactly zero."
            )
        try:
            gram = coerce_int_matrix3(
                self.primitive_gram_matrix, name="primitive_gram_matrix"
            )
        except ValueError as exc:
            raise PeriodicNetEmbeddingInputError(str(exc)) from exc
        if gram != _transpose_int(gram):
            raise PeriodicNetEmbeddingInputError(
                "primitive_gram_matrix must be symmetric."
            )
        determinant = int(self.metric_determinant)
        if determinant != _determinant_int(gram) or determinant <= 0:
            raise PeriodicNetEmbeddingInputError(
                "metric_determinant must equal the positive Gram determinant."
            )
        if gram[0][0] <= 0 or gram[0][0] * gram[1][1] - gram[0][1] ** 2 <= 0:
            raise PeriodicNetEmbeddingInputError(
                "primitive_gram_matrix must be positive definite."
            )
        entry_gcd = 0
        for row in gram:
            for value in row:
                entry_gcd = gcd(entry_gcd, abs(value))
        if entry_gcd != 1:
            raise PeriodicNetEmbeddingInputError(
                "primitive_gram_matrix must have primitive integer normalization."
            )
        minimum = Fraction(self.minimum_edge_length_squared)
        maximum = Fraction(self.maximum_edge_length_squared)
        if minimum <= 0 or maximum < minimum:
            raise PeriodicNetEmbeddingInputError(
                "Stored edge-length bounds must be positive and ordered."
            )
        if self.canonical_schema_version != CANONICAL_PERIODIC_NET_EMBEDDING_SCHEMA:
            raise PeriodicNetEmbeddingInputError(
                "Unsupported periodic-net embedding schema."
            )
        if self.digest_algorithm != PERIODIC_NET_EMBEDDING_DIGEST_ALGORITHM:
            raise PeriodicNetEmbeddingInputError(
                "Unsupported periodic-net embedding digest algorithm."
            )
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "edge_curve_model", edge_model)
        object.__setattr__(self, "anchor_atom_index", anchor)
        object.__setattr__(self, "vertex_atom_indices", vertices)
        object.__setattr__(self, "edge_keys", edge_keys)
        object.__setattr__(self, "fractional_coordinates", coordinates)
        object.__setattr__(self, "primitive_gram_matrix", gram)
        object.__setattr__(self, "metric_determinant", determinant)
        object.__setattr__(self, "minimum_edge_length_squared", minimum)
        object.__setattr__(self, "maximum_edge_length_squared", maximum)
        object.__setattr__(
            self,
            "_vertex_position_by_atom",
            MappingProxyType({atom: position for position, atom in enumerate(vertices)}),
        )
        object.__setattr__(
            self,
            "_edge_position_by_key",
            MappingProxyType({key: position for position, key in enumerate(edge_keys)}),
        )
        expected = _digest(self._payload(include_digest=False))
        digest = self.digest or expected
        if digest != expected:
            raise PeriodicNetEmbeddingInputError(
                "Stored periodic-net embedding digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PeriodicNetEmbedding):
            return NotImplemented
        return (
            self.digest == other.digest
            and self.periodic_net_view_digest == other.periodic_net_view_digest
        )

    @property
    def n_vertices(self) -> int:
        return len(self.vertex_atom_indices)

    @property
    def n_edges(self) -> int:
        return len(self.edge_keys)

    def vertex_position(self, atom_index: int) -> int:
        if isinstance(atom_index, bool) or not isinstance(atom_index, Integral):
            raise PeriodicNetEmbeddingInputError(
                "atom_index must be a nonnegative integer."
            )
        atom = int(atom_index)
        if atom < 0:
            raise PeriodicNetEmbeddingInputError(
                "atom_index must be a nonnegative integer."
            )
        try:
            return self._vertex_position_by_atom[atom]
        except KeyError as exc:
            raise PeriodicNetEmbeddingInputError(
                f"atom_index={atom} is absent from this embedding."
            ) from exc

    def edge_position(self, edge_key: FrameworkEdgeKey) -> int:
        if not isinstance(edge_key, FrameworkEdgeKey):
            raise PeriodicNetEmbeddingInputError(
                "edge_key must be a FrameworkEdgeKey."
            )
        try:
            return self._edge_position_by_key[edge_key]
        except KeyError as exc:
            raise PeriodicNetEmbeddingInputError(
                "edge_key is absent from this embedding."
            ) from exc

    def fractional_coordinate(
        self,
        atom_index: int,
        image_shift: LatticeShift = (0, 0, 0),
        *,
        wrap: bool = False,
    ) -> RationalVector3:
        try:
            shift = coerce_lattice_shift(image_shift, name="image_shift")
        except ValueError as exc:
            raise PeriodicNetEmbeddingInputError(str(exc)) from exc
        coordinate = _add_rational_vectors(
            self.fractional_coordinates[self.vertex_position(atom_index)],
            _shift_as_rational(shift),
        )
        return _wrap_vector(coordinate) if wrap else coordinate

    def primitive_squared_length(self, vector: RationalVector3) -> Fraction:
        values = tuple(Fraction(value) for value in vector)
        if len(values) != 3:
            raise PeriodicNetEmbeddingInputError(
                "vector must contain exactly three rational components."
            )
        return _quadratic_form(self.primitive_gram_matrix, values)

    def unit_volume_gram_matrix(self) -> np.ndarray:
        determinant_scale = float(self.metric_determinant) ** (1.0 / 3.0)
        matrix = np.asarray(self.primitive_gram_matrix, dtype=np.float64)
        result = matrix / determinant_scale
        result.setflags(write=False)
        return result

    def cell_matrix(self) -> np.ndarray:
        """Return row lattice vectors with unit positive Cartesian cell volume."""

        try:
            result = np.linalg.cholesky(self.unit_volume_gram_matrix())
        except np.linalg.LinAlgError as exc:  # pragma: no cover - exact checks guard this
            raise PeriodicNetEmbeddingInvariantError(
                "Numerical Cholesky factorization failed for the exact positive-definite metric."
            ) from exc
        result.setflags(write=False)
        return result

    def cartesian_coordinate(
        self,
        atom_index: int,
        image_shift: LatticeShift = (0, 0, 0),
        *,
        wrap: bool = False,
    ) -> np.ndarray:
        fractional = np.asarray(
            [float(value) for value in self.fractional_coordinate(atom_index, image_shift, wrap=wrap)],
            dtype=np.float64,
        )
        result = fractional @ self.cell_matrix()
        result.setflags(write=False)
        return result

    def edge_segment(
        self,
        edge_key: FrameworkEdgeKey,
        anchor_shift: LatticeShift = (0, 0, 0),
    ) -> EmbeddedStraightEdgeSegment:
        if self.edge_curve_model is not ProjectedEdgeCurveModel.STRAIGHT_SEGMENT:
            raise PeriodicNetEmbeddingUnsupportedError(
                "The active projected-edge model is not a straight segment."
            )
        self.edge_position(edge_key)
        try:
            anchor = coerce_lattice_shift(anchor_shift, name="anchor_shift")
        except ValueError as exc:
            raise PeriodicNetEmbeddingInputError(str(exc)) from exc
        start = self.fractional_coordinate(edge_key.vertex_i, anchor)
        end_shift = tuple(
            anchor[axis] + edge_key.image_shift[axis] for axis in range(3)
        )
        end = self.fractional_coordinate(edge_key.vertex_j, end_shift)
        displacement = _subtract_rational_vectors(end, start)
        squared = self.primitive_squared_length(displacement)
        start_cart = np.asarray([float(value) for value in start]) @ self.cell_matrix()
        end_cart = np.asarray([float(value) for value in end]) @ self.cell_matrix()
        return EmbeddedStraightEdgeSegment(
            periodic_net_embedding_digest=self.digest,
            topology_graph_digest=self.topology_graph_digest,
            edge_key=edge_key,
            anchor_shift=anchor,
            start_fractional=start,
            end_fractional=end,
            start_cartesian=tuple(float(value) for value in start_cart),
            end_cartesian=tuple(float(value) for value in end_cart),
            primitive_squared_length=squared,
        )

    def _payload(self, *, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "periodic_net_symmetry_digest": self.periodic_net_symmetry_digest,
            "barycentric_placement_digest": self.barycentric_placement_digest,
            "symmetry_discovery_certificate_digest": self.symmetry_discovery_certificate_digest,
            "method": self.method.value,
            "edge_curve_model": self.edge_curve_model.value,
            "anchor_atom_index": self.anchor_atom_index,
            "vertex_atom_indices": list(self.vertex_atom_indices),
            "edge_keys": [key.to_dict() for key in self.edge_keys],
            "fractional_coordinates": [
                [_fraction_payload(value) for value in coordinate]
                for coordinate in self.fractional_coordinates
            ],
            "primitive_gram_matrix": [list(row) for row in self.primitive_gram_matrix],
            "metric_determinant": self.metric_determinant,
            "minimum_edge_length_squared": _fraction_payload(
                self.minimum_edge_length_squared
            ),
            "maximum_edge_length_squared": _fraction_payload(
                self.maximum_edge_length_squared
            ),
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(include_digest=True)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        view: PeriodicNetView,
        discovery: PeriodicNetSymmetryDiscovery,
        resources: PeriodicNetEmbeddingResources | None = None,
    ) -> "PeriodicNetEmbedding":
        if not isinstance(view, PeriodicNetView):
            raise PeriodicNetEmbeddingSerializationError(
                "view must be a PeriodicNetView for source validation."
            )
        if not isinstance(discovery, PeriodicNetSymmetryDiscovery):
            raise PeriodicNetEmbeddingSerializationError(
                "discovery must be a PeriodicNetSymmetryDiscovery for source validation."
            )
        try:
            restored = cls(
                periodic_net_view_digest=str(payload["periodic_net_view_digest"]),
                topology_graph_digest=str(payload["topology_graph_digest"]),
                periodic_net_symmetry_digest=str(
                    payload["periodic_net_symmetry_digest"]
                ),
                barycentric_placement_digest=str(
                    payload["barycentric_placement_digest"]
                ),
                symmetry_discovery_certificate_digest=str(
                    payload["symmetry_discovery_certificate_digest"]
                ),
                method=PeriodicNetEmbeddingMethod(str(payload["method"])),
                edge_curve_model=ProjectedEdgeCurveModel(
                    str(payload["edge_curve_model"])
                ),
                anchor_atom_index=int(payload["anchor_atom_index"]),
                vertex_atom_indices=tuple(
                    int(value) for value in payload["vertex_atom_indices"]
                ),
                edge_keys=tuple(
                    FrameworkEdgeKey.from_dict(item) for item in payload["edge_keys"]
                ),
                fractional_coordinates=tuple(
                    tuple(_fraction_from_payload(value) for value in coordinate)
                    for coordinate in payload["fractional_coordinates"]
                ),
                primitive_gram_matrix=tuple(
                    tuple(int(value) for value in row)
                    for row in payload["primitive_gram_matrix"]
                ),
                metric_determinant=int(payload["metric_determinant"]),
                minimum_edge_length_squared=_fraction_from_payload(
                    payload["minimum_edge_length_squared"]
                ),
                maximum_edge_length_squared=_fraction_from_payload(
                    payload["maximum_edge_length_squared"]
                ),
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
            rebuilt = build_periodic_net_embedding(
                view,
                discovery,
                resources=resources,
            )
            if rebuilt.to_dict() != dict(payload):
                raise PeriodicNetEmbeddingSerializationError(
                    "Serialized PeriodicNetEmbedding is not canonical for the supplied sources."
                )
            return restored
        except PeriodicNetEmbeddingError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PeriodicNetEmbeddingSerializationError(
                "Invalid serialized PeriodicNetEmbedding payload."
            ) from exc


def _validate_sources(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
) -> None:
    if not isinstance(view, PeriodicNetView):
        raise PeriodicNetEmbeddingInputError("view must be a PeriodicNetView.")
    if not isinstance(discovery, PeriodicNetSymmetryDiscovery):
        raise PeriodicNetEmbeddingInputError(
            "discovery must be a PeriodicNetSymmetryDiscovery."
        )
    if discovery.method != BARYCENTRIC_STAR_DISCOVERY_METHOD:
        raise PeriodicNetEmbeddingUnsupportedError(
            "The first embedding backend requires barycentric star symmetry discovery."
        )
    if (
        discovery.periodic_net_view_digest != view.digest
        or discovery.topology_graph_digest != view.source_graph_digest
        or discovery.symmetry.periodic_net_view_digest != view.digest
        or discovery.symmetry.topology_graph_digest != view.source_graph_digest
        or discovery.barycentric_placement.periodic_net_view_digest != view.digest
        or discovery.barycentric_placement.topology_graph_digest
        != view.source_graph_digest
    ):
        raise PeriodicNetEmbeddingInputError(
            "View, discovery, symmetry, and barycentric placement source identities differ."
        )
    if discovery.barycentric_placement.anchor_atom_index != discovery.symmetry.anchor_atom_index:
        raise PeriodicNetEmbeddingInputError(
            "Barycentric placement and symmetry must share the same translation gauge anchor."
        )


def _verify_exact_symmetry(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    coordinates_by_atom: Mapping[int, RationalVector3],
    gram: IntMatrix3,
) -> None:
    anchor = discovery.symmetry.anchor_atom_index
    for operation in discovery.symmetry.operations:
        transformed_metric = _multiply_int_matrices(
            _multiply_int_matrices(_transpose_int(operation.lattice_matrix), gram),
            operation.lattice_matrix,
        )
        if transformed_metric != gram:
            raise PeriodicNetEmbeddingInvariantError(
                "Exact lattice metric is not invariant under the complete net symmetry."
            )
        anchor_image = operation.vertex_image(anchor)
        if anchor_image.image_shift != (0, 0, 0):
            raise PeriodicNetEmbeddingInvariantError(
                "Stored symmetry operation is not normalized to the embedding anchor."
            )
        affine_translation = coordinates_by_atom[anchor_image.atom_index]
        for atom_index in view.vertex_atom_indices:
            image = operation.vertex_image(atom_index)
            left = _add_rational_vectors(
                _matvec_fraction(
                    operation.lattice_matrix, coordinates_by_atom[atom_index]
                ),
                affine_translation,
            )
            right = _add_rational_vectors(
                coordinates_by_atom[image.atom_index],
                _shift_as_rational(image.image_shift),
            )
            if left != right:
                raise PeriodicNetEmbeddingInvariantError(
                    "Barycentric coordinates are not exactly equivariant under the complete symmetry."
                )
        for edge_position, edge_key in enumerate(view.edge_keys):
            source_displacement = _edge_displacement(coordinates_by_atom, edge_key)
            image = operation.edge_images[edge_position]
            target_key = view.edge_keys[image.target_edge_index]
            target_displacement = _edge_displacement(coordinates_by_atom, target_key)
            if image.orientation == -1:
                target_displacement = _negate_rational_vector(target_displacement)
            if _matvec_fraction(
                operation.lattice_matrix, source_displacement
            ) != target_displacement:
                raise PeriodicNetEmbeddingInvariantError(
                    "Projected straight-edge vectors are not exactly equivariant under symmetry."
                )


def build_periodic_net_embedding(
    view: PeriodicNetView,
    discovery: PeriodicNetSymmetryDiscovery,
    *,
    resources: PeriodicNetEmbeddingResources | None = None,
) -> PeriodicNetEmbedding:
    """Construct the authoritative exact first-backend Euclidean embedding."""

    _validate_sources(view, discovery)
    active_resources = resources or PeriodicNetEmbeddingResources()
    if not isinstance(active_resources, PeriodicNetEmbeddingResources):
        raise PeriodicNetEmbeddingInputError(
            "resources must be a PeriodicNetEmbeddingResources record."
        )
    if (
        view.pbc != (True, True, True)
        or view.n_components != 1
        or view.translation_rank != 3
        or view.translation_index != 1
    ):
        raise PeriodicNetEmbeddingUnsupportedError(
            "The first embedding backend requires one connected, rank-three, "
            "index-one three-periodic net view."
        )
    if view.n_vertices > active_resources.max_vertices:
        raise PeriodicNetEmbeddingResourceError(
            "PeriodicNetView exceeds max_vertices."
        )
    if view.n_edges > active_resources.max_edges:
        raise PeriodicNetEmbeddingResourceError("PeriodicNetView exceeds max_edges.")
    if discovery.symmetry.order > active_resources.max_symmetry_operations:
        raise PeriodicNetEmbeddingResourceError(
            "PeriodicNetSymmetry exceeds max_symmetry_operations."
        )
    placement = discovery.barycentric_placement
    if not placement.collision_free:
        raise PeriodicNetEmbeddingUnsupportedError(
            "Barycentric placement contains lifted-vertex collisions: "
            f"{placement.collision_atom_pairs}."
        )
    if placement.vertex_atom_indices != view.vertex_atom_indices:
        raise PeriodicNetEmbeddingInputError(
            "Barycentric placement vertex order differs from the net view."
        )
    coordinates_by_atom = MappingProxyType(
        {
            atom: placement.coordinates[position]
            for position, atom in enumerate(placement.vertex_atom_indices)
        }
    )
    displacements = tuple(
        _edge_displacement(coordinates_by_atom, edge_key) for edge_key in view.edge_keys
    )
    zero_edges = tuple(
        edge_key
        for edge_key, displacement in zip(view.edge_keys, displacements, strict=True)
        if displacement == (Fraction(0), Fraction(0), Fraction(0))
    )
    if zero_edges:
        raise PeriodicNetEmbeddingUnsupportedError(
            "Straight projected-edge model contains zero-length edges."
        )
    coincidences = _coincident_straight_edge_pairs(
        coordinates_by_atom, view.edge_keys
    )
    if coincidences:
        raise PeriodicNetEmbeddingUnsupportedError(
            "Distinct quotient edges coincide as straight projected segments; "
            "a distinct-curve edge backend is required."
        )
    covariance = _edge_covariance(coordinates_by_atom, view.edge_keys)
    _check_fraction_bits(
        tuple(value for row in covariance for value in row),
        max_fraction_bits=active_resources.max_metric_fraction_bits,
        context="edge covariance",
    )
    covariance_determinant = _determinant_fraction(covariance)
    if covariance_determinant <= 0:
        raise PeriodicNetEmbeddingUnsupportedError(
            "Projected edge covariance must be positive definite."
        )
    rational_metric = _inverse_fraction_matrix3(covariance)
    _check_fraction_bits(
        tuple(value for row in rational_metric for value in row),
        max_fraction_bits=active_resources.max_metric_fraction_bits,
        context="lattice metric",
    )
    gram = _primitive_integral_matrix(rational_metric)
    if any(
        abs(value).bit_length() > active_resources.max_metric_fraction_bits
        for row in gram
        for value in row
    ):
        raise PeriodicNetEmbeddingResourceError(
            "Primitive lattice metric exceeded max_metric_fraction_bits."
        )
    determinant = _determinant_int(gram)
    if determinant <= 0:
        raise PeriodicNetEmbeddingInvariantError(
            "Primitive lattice Gram matrix is not positive definite."
        )
    squared_lengths = tuple(
        _quadratic_form(gram, displacement) for displacement in displacements
    )
    if any(value <= 0 for value in squared_lengths):
        raise PeriodicNetEmbeddingInvariantError(
            "Positive-definite metric produced a nonpositive edge length."
        )
    _verify_exact_symmetry(view, discovery, coordinates_by_atom, gram)
    return PeriodicNetEmbedding(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        periodic_net_symmetry_digest=discovery.symmetry.digest,
        barycentric_placement_digest=placement.digest,
        symmetry_discovery_certificate_digest=(
            periodic_net_symmetry_discovery_certificate_digest(discovery)
        ),
        method=PeriodicNetEmbeddingMethod.BARYCENTRIC_EDGE_COVARIANCE,
        edge_curve_model=ProjectedEdgeCurveModel.STRAIGHT_SEGMENT,
        anchor_atom_index=placement.anchor_atom_index,
        vertex_atom_indices=view.vertex_atom_indices,
        edge_keys=view.edge_keys,
        fractional_coordinates=placement.coordinates,
        primitive_gram_matrix=gram,
        metric_determinant=determinant,
        minimum_edge_length_squared=min(squared_lengths),
        maximum_edge_length_squared=max(squared_lengths),
    )


__all__ = [
    "CANONICAL_PERIODIC_NET_EMBEDDING_SCHEMA",
    "PERIODIC_NET_EMBEDDING_DIGEST_ALGORITHM",
    "PERIODIC_NET_EMBEDDING_DISCOVERY_CERTIFICATE_SCHEMA",
    "EmbeddedStraightEdgeSegment",
    "PeriodicNetEmbedding",
    "PeriodicNetEmbeddingError",
    "PeriodicNetEmbeddingInputError",
    "PeriodicNetEmbeddingInvariantError",
    "PeriodicNetEmbeddingMethod",
    "PeriodicNetEmbeddingResourceError",
    "PeriodicNetEmbeddingResources",
    "PeriodicNetEmbeddingSerializationError",
    "PeriodicNetEmbeddingUnsupportedError",
    "ProjectedEdgeCurveModel",
    "RationalMatrix3",
    "build_periodic_net_embedding",
    "periodic_net_symmetry_discovery_certificate_digest",
]
