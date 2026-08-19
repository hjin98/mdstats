"""Exact rational barycentric placements of periodic-net quotient graphs.

This module extracts the topology-derived equilibrium placement used by exact
periodic-net symmetry discovery into a reusable, source-bound record.  The
barycentric placement method follows Delgado-Friedrichs (2004).  mdstats adds
explicit translation-gauge ownership, collision diagnostics, exact rational
serialization, and resource guards on system size and rational coefficient
growth.

References
----------
O. Delgado-Friedrichs, in Graph Drawing, LNCS 2912, 178-189 (2004),
doi:10.1007/978-3-540-24595-7_17.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
from numbers import Integral
from typing import Any, Mapping, Sequence, TypeAlias

from .periodic_net_view import PeriodicNetView

CANONICAL_PERIODIC_BARYCENTRIC_PLACEMENT_SCHEMA = (
    "mdstats.periodic-barycentric-placement.v1"
)
PERIODIC_BARYCENTRIC_DIGEST_ALGORITHM = "sha256-canonical-json-v1"

RationalVector3: TypeAlias = tuple[Fraction, Fraction, Fraction]


class PeriodicBarycentricError(ValueError):
    """Base exception for exact periodic barycentric placements."""


class PeriodicBarycentricInputError(PeriodicBarycentricError):
    """Raised when a view, anchor, or resource policy is malformed."""


class PeriodicBarycentricUnsupportedError(PeriodicBarycentricError):
    """Raised when the quotient Laplacian cannot define the requested placement."""


class PeriodicBarycentricResourceError(PeriodicBarycentricError):
    """Raised when exact rational construction exceeds a declared resource bound."""


class PeriodicBarycentricSerializationError(PeriodicBarycentricError):
    """Raised when serialized placement data fail source validation."""


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise PeriodicBarycentricInputError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise PeriodicBarycentricInputError(f"{name} must be a positive integer.")
    return result


def _fraction_payload(value: Fraction) -> list[int]:
    return [value.numerator, value.denominator]


def _fraction_from_payload(payload: Sequence[Any]) -> Fraction:
    if len(payload) != 2:
        raise PeriodicBarycentricSerializationError(
            "Serialized rational values require [numerator, denominator]."
        )
    return Fraction(int(payload[0]), int(payload[1]))


def _fractional_part(vector: RationalVector3) -> RationalVector3:
    return tuple(
        value - (value.numerator // value.denominator) for value in vector
    )  # type: ignore[return-value]


def _fraction_bits(value: Fraction) -> int:
    return max(abs(value.numerator).bit_length(), value.denominator.bit_length())


def _check_augmented_bits(
    augmented: list[list[Fraction]], *, max_fraction_bits: int
) -> int:
    maximum = 1
    for row in augmented:
        for value in row:
            maximum = max(maximum, _fraction_bits(value))
            if maximum > max_fraction_bits:
                raise PeriodicBarycentricResourceError(
                    "Exact barycentric elimination exceeded max_fraction_bits."
                )
    return maximum


def _solve_exact_linear_system(
    matrix: list[list[int]],
    right_hand_sides: list[list[int]],
    *,
    max_fraction_bits: int,
) -> tuple[tuple[RationalVector3, ...], int]:
    """Solve one nonsingular integer system against three right-hand sides."""

    size = len(matrix)
    if size == 0:
        return (), 1
    augmented = [
        [Fraction(value) for value in matrix[row]]
        + [Fraction(value) for value in right_hand_sides[row]]
        for row in range(size)
    ]
    width = size + 3
    maximum_bits = _check_augmented_bits(
        augmented, max_fraction_bits=max_fraction_bits
    )
    for column in range(size):
        pivot = next(
            (row for row in range(column, size) if augmented[row][column] != 0),
            None,
        )
        if pivot is None:
            raise PeriodicBarycentricUnsupportedError(
                "The quotient Laplacian is singular after fixing one translation gauge."
            )
        if pivot != column:
            augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0:
                continue
            augmented[row] = [
                augmented[row][entry] - factor * augmented[column][entry]
                for entry in range(width)
            ]
        maximum_bits = max(
            maximum_bits,
            _check_augmented_bits(
                augmented, max_fraction_bits=max_fraction_bits
            ),
        )
    solved = tuple(
        tuple(augmented[row][size + axis] for axis in range(3))
        for row in range(size)
    )
    return solved, maximum_bits


@dataclass(frozen=True, slots=True)
class PeriodicBarycentricResources:
    """Execution limits for exact barycentric placement construction."""

    max_vertices: int = 4096
    max_fraction_bits: int = 4096

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "max_vertices", _positive_int(self.max_vertices, name="max_vertices")
        )
        object.__setattr__(
            self,
            "max_fraction_bits",
            _positive_int(self.max_fraction_bits, name="max_fraction_bits"),
        )

    def to_dict(self) -> dict[str, int]:
        return {
            "max_vertices": self.max_vertices,
            "max_fraction_bits": self.max_fraction_bits,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PeriodicBarycentricResources":
        return cls(
            max_vertices=int(payload["max_vertices"]),
            max_fraction_bits=int(payload["max_fraction_bits"]),
        )


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicBarycentricPlacement:
    """Exact topology-derived placement bound to one :class:`PeriodicNetView`.

    Coordinates are stored in the quotient lattice basis with the selected
    anchor vertex fixed at the origin.  ``collision_atom_pairs`` records pairs
    whose coordinates coincide modulo integer lattice translation; discovery
    backends that require a stable placement must reject nonempty collision data.
    """

    periodic_net_view_digest: str
    topology_graph_digest: str
    anchor_atom_index: int
    vertex_atom_indices: tuple[int, ...]
    coordinates: tuple[RationalVector3, ...]
    collision_atom_pairs: tuple[tuple[int, int], ...]
    max_fraction_bits_observed: int
    canonical_schema_version: str = CANONICAL_PERIODIC_BARYCENTRIC_PLACEMENT_SCHEMA
    digest_algorithm: str = PERIODIC_BARYCENTRIC_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.periodic_net_view_digest) != 64 or len(self.topology_graph_digest) != 64:
            raise PeriodicBarycentricInputError(
                "Placement source digests must be SHA-256 values."
            )
        if isinstance(self.anchor_atom_index, bool) or int(self.anchor_atom_index) < 0:
            raise PeriodicBarycentricInputError("anchor_atom_index must be nonnegative.")
        vertices = tuple(int(value) for value in self.vertex_atom_indices)
        if vertices != tuple(sorted(set(vertices))) or not vertices:
            raise PeriodicBarycentricInputError(
                "vertex_atom_indices must be nonempty, sorted, and unique."
            )
        if int(self.anchor_atom_index) not in vertices:
            raise PeriodicBarycentricInputError(
                "anchor_atom_index must belong to vertex_atom_indices."
            )
        coordinates = tuple(
            tuple(Fraction(value) for value in coordinate)
            for coordinate in self.coordinates
        )
        if len(coordinates) != len(vertices) or any(len(item) != 3 for item in coordinates):
            raise PeriodicBarycentricInputError(
                "coordinates must align with vertex_atom_indices and have length three."
            )
        anchor_position = vertices.index(int(self.anchor_atom_index))
        if coordinates[anchor_position] != (Fraction(0), Fraction(0), Fraction(0)):
            raise PeriodicBarycentricInputError(
                "The selected anchor coordinate must be exactly zero."
            )
        collisions = tuple(tuple(int(value) for value in pair) for pair in self.collision_atom_pairs)
        if any(len(pair) != 2 or pair[0] >= pair[1] for pair in collisions):
            raise PeriodicBarycentricInputError(
                "collision_atom_pairs must contain ordered distinct atom-index pairs."
            )
        if collisions != tuple(sorted(set(collisions))):
            raise PeriodicBarycentricInputError(
                "collision_atom_pairs must be sorted and unique."
            )
        if any(value not in vertices for pair in collisions for value in pair):
            raise PeriodicBarycentricInputError(
                "collision_atom_pairs must reference placement vertices."
            )
        observed = _positive_int(
            self.max_fraction_bits_observed, name="max_fraction_bits_observed"
        )
        actual_observed = max(
            1,
            *(_fraction_bits(value) for coordinate in coordinates for value in coordinate),
        )
        if observed < actual_observed:
            raise PeriodicBarycentricInputError(
                "max_fraction_bits_observed understates the stored coordinates."
            )
        if self.canonical_schema_version != CANONICAL_PERIODIC_BARYCENTRIC_PLACEMENT_SCHEMA:
            raise PeriodicBarycentricInputError(
                "Unsupported periodic barycentric placement schema."
            )
        if self.digest_algorithm != PERIODIC_BARYCENTRIC_DIGEST_ALGORITHM:
            raise PeriodicBarycentricInputError(
                "Unsupported periodic barycentric digest algorithm."
            )
        object.__setattr__(self, "anchor_atom_index", int(self.anchor_atom_index))
        object.__setattr__(self, "vertex_atom_indices", vertices)
        object.__setattr__(self, "coordinates", coordinates)
        object.__setattr__(self, "collision_atom_pairs", collisions)
        object.__setattr__(self, "max_fraction_bits_observed", observed)
        expected = _digest(self._payload(include_digest=False))
        digest = self.digest or expected
        if digest != expected:
            raise PeriodicBarycentricInputError(
                "Stored periodic barycentric placement digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PeriodicBarycentricPlacement):
            return NotImplemented
        return (
            self.digest == other.digest
            and self.periodic_net_view_digest == other.periodic_net_view_digest
        )

    @property
    def collision_free(self) -> bool:
        return not self.collision_atom_pairs

    def coordinate(self, atom_index: int) -> RationalVector3:
        try:
            position = self.vertex_atom_indices.index(int(atom_index))
        except ValueError as exc:
            raise PeriodicBarycentricInputError(
                f"atom_index={atom_index} is absent from this placement."
            ) from exc
        return self.coordinates[position]

    def _payload(self, *, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "anchor_atom_index": self.anchor_atom_index,
            "vertex_atom_indices": list(self.vertex_atom_indices),
            "coordinates": [
                [_fraction_payload(value) for value in coordinate]
                for coordinate in self.coordinates
            ],
            "collision_atom_pairs": [list(pair) for pair in self.collision_atom_pairs],
            "max_fraction_bits_observed": self.max_fraction_bits_observed,
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
        resources: PeriodicBarycentricResources | None = None,
    ) -> "PeriodicBarycentricPlacement":
        if not isinstance(view, PeriodicNetView):
            raise PeriodicBarycentricSerializationError(
                "view must be a PeriodicNetView for source validation."
            )
        try:
            restored = cls(
                periodic_net_view_digest=str(payload["periodic_net_view_digest"]),
                topology_graph_digest=str(payload["topology_graph_digest"]),
                anchor_atom_index=int(payload["anchor_atom_index"]),
                vertex_atom_indices=tuple(int(value) for value in payload["vertex_atom_indices"]),
                coordinates=tuple(
                    tuple(_fraction_from_payload(value) for value in coordinate)
                    for coordinate in payload["coordinates"]
                ),
                collision_atom_pairs=tuple(
                    tuple(int(value) for value in pair)
                    for pair in payload["collision_atom_pairs"]
                ),
                max_fraction_bits_observed=int(payload["max_fraction_bits_observed"]),
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
            if (
                restored.periodic_net_view_digest != view.digest
                or restored.topology_graph_digest != view.source_graph_digest
                or restored.vertex_atom_indices != view.vertex_atom_indices
            ):
                raise PeriodicBarycentricSerializationError(
                    "Serialized placement source identities do not match the supplied view."
                )
            rebuilt = build_periodic_barycentric_placement(
                view,
                anchor_atom_index=restored.anchor_atom_index,
                resources=resources,
            )
            if rebuilt.to_dict() != dict(payload):
                raise PeriodicBarycentricSerializationError(
                    "Serialized periodic barycentric placement is not canonical."
                )
            return restored
        except PeriodicBarycentricError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PeriodicBarycentricSerializationError(
                "Invalid serialized PeriodicBarycentricPlacement payload."
            ) from exc


def build_periodic_barycentric_placement(
    view: PeriodicNetView,
    *,
    anchor_atom_index: int | None = None,
    resources: PeriodicBarycentricResources | None = None,
) -> PeriodicBarycentricPlacement:
    """Construct the exact rational equilibrium placement of one quotient graph."""

    if not isinstance(view, PeriodicNetView):
        raise PeriodicBarycentricInputError("view must be a PeriodicNetView.")
    policy = resources or PeriodicBarycentricResources()
    if not isinstance(policy, PeriodicBarycentricResources):
        raise PeriodicBarycentricInputError(
            "resources must be a PeriodicBarycentricResources record."
        )
    if view.n_vertices > policy.max_vertices:
        raise PeriodicBarycentricResourceError(
            "Barycentric placement exceeds max_vertices."
        )
    if view.n_components != 1:
        raise PeriodicBarycentricUnsupportedError(
            "Exact barycentric placement requires one connected quotient component."
        )
    if anchor_atom_index is None:
        anchor = min(view.vertex_atom_indices)
    else:
        if isinstance(anchor_atom_index, bool) or not isinstance(anchor_atom_index, Integral):
            raise PeriodicBarycentricInputError(
                "anchor_atom_index must be a nonnegative integer or None."
            )
        anchor = int(anchor_atom_index)
        if anchor < 0:
            raise PeriodicBarycentricInputError(
                "anchor_atom_index must be a nonnegative integer or None."
            )
        view.vertex_position(anchor)
    anchor_position = view.vertex_position(anchor)

    n_vertices = view.n_vertices
    laplacian = [[0 for _ in range(n_vertices)] for _ in range(n_vertices)]
    right = [[0, 0, 0] for _ in range(n_vertices)]
    for key in view.edge_keys:
        source = view.vertex_position(key.vertex_i)
        target = view.vertex_position(key.vertex_j)
        if source == target:
            continue
        laplacian[source][source] += 1
        laplacian[target][target] += 1
        laplacian[source][target] -= 1
        laplacian[target][source] -= 1
        for axis in range(3):
            right[source][axis] += key.image_shift[axis]
            right[target][axis] -= key.image_shift[axis]
    retained = [position for position in range(n_vertices) if position != anchor_position]
    reduced_matrix = [
        [laplacian[row][column] for column in retained] for row in retained
    ]
    reduced_right = [right[row] for row in retained]
    solved, observed_bits = _solve_exact_linear_system(
        reduced_matrix,
        reduced_right,
        max_fraction_bits=policy.max_fraction_bits,
    )
    coordinates: list[RationalVector3] = []
    solved_position = 0
    for position in range(n_vertices):
        if position == anchor_position:
            coordinates.append((Fraction(0), Fraction(0), Fraction(0)))
        else:
            coordinates.append(solved[solved_position])
            solved_position += 1
    coordinate_tuple = tuple(coordinates)
    occupied: dict[RationalVector3, int] = {}
    collisions: list[tuple[int, int]] = []
    for position, coordinate in enumerate(coordinate_tuple):
        reduced = _fractional_part(coordinate)
        previous = occupied.get(reduced)
        if previous is not None:
            left = view.vertex_atom_indices[previous]
            right_atom = view.vertex_atom_indices[position]
            collisions.append(tuple(sorted((left, right_atom))))
        else:
            occupied[reduced] = position
    observed_bits = max(
        observed_bits,
        *(_fraction_bits(value) for coordinate in coordinate_tuple for value in coordinate),
    )
    return PeriodicBarycentricPlacement(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        anchor_atom_index=anchor,
        vertex_atom_indices=view.vertex_atom_indices,
        coordinates=coordinate_tuple,
        collision_atom_pairs=tuple(sorted(set(collisions))),
        max_fraction_bits_observed=observed_bits,
    )


__all__ = [
    "CANONICAL_PERIODIC_BARYCENTRIC_PLACEMENT_SCHEMA",
    "PERIODIC_BARYCENTRIC_DIGEST_ALGORITHM",
    "PeriodicBarycentricError",
    "PeriodicBarycentricInputError",
    "PeriodicBarycentricPlacement",
    "PeriodicBarycentricResourceError",
    "PeriodicBarycentricResources",
    "PeriodicBarycentricSerializationError",
    "PeriodicBarycentricUnsupportedError",
    "RationalVector3",
    "build_periodic_barycentric_placement",
]
