"""Exact automatic symmetry discovery for stable three-periodic net views.

The backend computes the rational barycentric (equilibrium) placement of one
connected three-periodic quotient graph and enumerates affine maps determined by
one spanning vertex-star frame.  Every accepted candidate is converted to an
exact :class:`ValidatedPeriodicAutomorphism` and passed to the existing finite
group assembler.

The method follows the exact periodic-net symmetry framework of
Delgado-Friedrichs and O'Keeffe (2003) and the barycentric placement method of
Delgado-Friedrichs (2004).  The local frame enumeration, explicit multiedge
matching, deterministic generator reduction, resource contracts, and source-
bound serialization are mdstats adaptations.

This first discovery backend is complete only for views satisfying all declared
preconditions: one connected rank-three, index-one periodic lift; collision-free
barycentric placement; and at least one quotient vertex whose incident
barycentric edge vectors contain a three-dimensional frame.  Unsupported views
fail transactionally rather than returning a partial symmetry claim.

References
----------
O. Delgado-Friedrichs and M. O'Keeffe, Acta Cryst. A 59, 351-360 (2003),
doi:10.1107/S0108767303012017.
O. Delgado-Friedrichs, in Graph Drawing, LNCS 2912, 178-189 (2004),
doi:10.1007/978-3-540-24595-7_17.
"""

from __future__ import annotations

import hashlib
import itertools
import json
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Iterable, Mapping, Sequence, TypeAlias

from ._periodic_graph import IntMatrix3, LatticeShift, determinant3
from .framework_topology import FrameworkEdgeKey
from .net_symmetry import (
    PeriodicNetSymmetry,
    build_periodic_net_symmetry,
    compose_periodic_automorphisms,
    identity_periodic_automorphism,
    invert_periodic_automorphism,
)
from .periodic_barycentric import (
    PeriodicBarycentricPlacement,
    PeriodicBarycentricResources,
    RationalVector3,
    build_periodic_barycentric_placement,
)
from .periodic_net_view import NetSignature, PeriodicNetView
from .periodic_ring_action import (
    PeriodicEdgeImage,
    ValidatedPeriodicAutomorphism,
    build_validated_periodic_automorphism,
)
from .primitive_ring import LiftedVertexRef
from .primitive_ring_index import PrimitiveRingIndex
from .primitive_ring_symmetry import (
    PrimitiveRingSymmetryIndex,
    build_primitive_ring_symmetry_index,
)

CANONICAL_NET_SYMMETRY_DISCOVERY_SCHEMA = "mdstats.net-symmetry-discovery.v2"
NET_SYMMETRY_DISCOVERY_DIGEST_ALGORITHM = "sha256"
BARYCENTRIC_STAR_DISCOVERY_METHOD = "exact_barycentric_star_frame"

RationalMatrix3: TypeAlias = tuple[RationalVector3, RationalVector3, RationalVector3]


class NetSymmetryDiscoveryError(ValueError):
    """Base exception for automatic periodic-net symmetry discovery."""


class NetSymmetryDiscoveryInputError(NetSymmetryDiscoveryError):
    """Raised when the view, options, or source records are invalid."""


class NetSymmetryDiscoveryUnsupportedError(NetSymmetryDiscoveryError):
    """Raised when the exact first backend cannot certify completeness."""


class NetSymmetryDiscoveryResourceError(NetSymmetryDiscoveryError):
    """Raised when a declared discovery resource bound is exhausted."""


class NetSymmetryDiscoverySerializationError(NetSymmetryDiscoveryError):
    """Raised when serialized discovery data fail source validation."""


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise NetSymmetryDiscoveryInputError(f"{name} must be a positive integer.")
    try:
        result = int(value)
    except (TypeError, ValueError) as exc:
        raise NetSymmetryDiscoveryInputError(
            f"{name} must be a positive integer."
        ) from exc
    if result <= 0:
        raise NetSymmetryDiscoveryInputError(f"{name} must be a positive integer.")
    return result


def _add(left: RationalVector3, right: RationalVector3) -> RationalVector3:
    return tuple(left[i] + right[i] for i in range(3))  # type: ignore[return-value]


def _subtract(left: RationalVector3, right: RationalVector3) -> RationalVector3:
    return tuple(left[i] - right[i] for i in range(3))  # type: ignore[return-value]


def _negate(value: RationalVector3) -> RationalVector3:
    return tuple(-item for item in value)  # type: ignore[return-value]


def _matvec(matrix: RationalMatrix3, vector: RationalVector3) -> RationalVector3:
    return tuple(
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _matmul(left: RationalMatrix3, right: RationalMatrix3) -> RationalMatrix3:
    return tuple(
        tuple(
            sum(left[row][inner] * right[inner][column] for inner in range(3))
            for column in range(3)
        )
        for row in range(3)
    )  # type: ignore[return-value]


def _matrix_from_columns(vectors: Sequence[RationalVector3]) -> RationalMatrix3:
    if len(vectors) != 3:
        raise NetSymmetryDiscoveryInputError("A barycentric frame requires three vectors.")
    return tuple(
        tuple(vectors[column][row] for column in range(3))
        for row in range(3)
    )  # type: ignore[return-value]


def _determinant_fraction(matrix: RationalMatrix3) -> Fraction:
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def _inverse_fraction_matrix(matrix: RationalMatrix3) -> RationalMatrix3:
    determinant = _determinant_fraction(matrix)
    if determinant == 0:
        raise NetSymmetryDiscoveryInputError("Barycentric frame matrix is singular.")
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


def _fractional_part(vector: RationalVector3) -> RationalVector3:
    return tuple(
        item - (item.numerator // item.denominator) for item in vector
    )  # type: ignore[return-value]


def _integer_vector(vector: RationalVector3) -> LatticeShift | None:
    if any(item.denominator != 1 for item in vector):
        return None
    return tuple(int(item) for item in vector)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class NetSymmetryDiscoveryOptions:
    """Immutable resource and anchor policy for exact discovery."""

    anchor_atom_index: int | None = None
    max_frame_trials: int = 250_000
    max_candidate_operations: int = 20_000
    max_group_operations: int = 4096
    max_ring_composition_checks: int = 5_000_000
    max_barycentric_vertices: int = 4096
    max_barycentric_fraction_bits: int = 4096

    def __post_init__(self) -> None:
        anchor = self.anchor_atom_index
        if anchor is not None:
            if isinstance(anchor, bool):
                raise NetSymmetryDiscoveryInputError(
                    "anchor_atom_index must be a nonnegative integer or None."
                )
            try:
                anchor = int(anchor)
            except (TypeError, ValueError) as exc:
                raise NetSymmetryDiscoveryInputError(
                    "anchor_atom_index must be a nonnegative integer or None."
                ) from exc
            if anchor < 0:
                raise NetSymmetryDiscoveryInputError(
                    "anchor_atom_index must be a nonnegative integer or None."
                )
        object.__setattr__(self, "anchor_atom_index", anchor)
        object.__setattr__(
            self, "max_frame_trials", _positive_int(self.max_frame_trials, name="max_frame_trials")
        )
        object.__setattr__(
            self,
            "max_candidate_operations",
            _positive_int(self.max_candidate_operations, name="max_candidate_operations"),
        )
        object.__setattr__(
            self,
            "max_group_operations",
            _positive_int(self.max_group_operations, name="max_group_operations"),
        )
        object.__setattr__(
            self,
            "max_ring_composition_checks",
            _positive_int(
                self.max_ring_composition_checks,
                name="max_ring_composition_checks",
            ),
        )
        object.__setattr__(
            self,
            "max_barycentric_vertices",
            _positive_int(
                self.max_barycentric_vertices,
                name="max_barycentric_vertices",
            ),
        )
        object.__setattr__(
            self,
            "max_barycentric_fraction_bits",
            _positive_int(
                self.max_barycentric_fraction_bits,
                name="max_barycentric_fraction_bits",
            ),
        )


@dataclass(frozen=True, slots=True)
class BarycentricFrameIncidence:
    """One oriented quotient-edge incidence in the source discovery frame."""

    edge_position: int
    orientation: int

    def __post_init__(self) -> None:
        if isinstance(self.edge_position, bool) or int(self.edge_position) < 0:
            raise NetSymmetryDiscoveryInputError("edge_position must be nonnegative.")
        if self.orientation not in (-1, 1):
            raise NetSymmetryDiscoveryInputError("orientation must be +1 or -1.")
        object.__setattr__(self, "edge_position", int(self.edge_position))


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicNetSymmetryDiscovery:
    """Certified full symmetry discovery for the exact first backend domain."""

    periodic_net_view_digest: str
    topology_graph_digest: str
    method: str
    anchor_atom_index: int
    source_frame: tuple[BarycentricFrameIncidence, ...]
    barycentric_placement: PeriodicBarycentricPlacement
    frame_trial_count: int
    candidate_operation_count: int
    generator_operation_indices: tuple[int, ...]
    symmetry: PeriodicNetSymmetry
    ring_symmetry: PrimitiveRingSymmetryIndex | None = None
    canonical_schema_version: str = CANONICAL_NET_SYMMETRY_DISCOVERY_SCHEMA
    digest_algorithm: str = NET_SYMMETRY_DISCOVERY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if len(self.periodic_net_view_digest) != 64 or len(self.topology_graph_digest) != 64:
            raise NetSymmetryDiscoveryInputError("Discovery source digests must be SHA-256 values.")
        if self.method != BARYCENTRIC_STAR_DISCOVERY_METHOD:
            raise NetSymmetryDiscoveryInputError("Unsupported symmetry-discovery method.")
        if isinstance(self.anchor_atom_index, bool) or int(self.anchor_atom_index) < 0:
            raise NetSymmetryDiscoveryInputError("anchor_atom_index must be nonnegative.")
        frame = tuple(self.source_frame)
        if len(frame) != 3 or any(not isinstance(item, BarycentricFrameIncidence) for item in frame):
            raise NetSymmetryDiscoveryInputError("source_frame must contain three incidences.")
        if not isinstance(self.barycentric_placement, PeriodicBarycentricPlacement):
            raise NetSymmetryDiscoveryInputError(
                "barycentric_placement must be a PeriodicBarycentricPlacement."
            )
        if (
            self.barycentric_placement.periodic_net_view_digest
            != self.periodic_net_view_digest
            or self.barycentric_placement.topology_graph_digest
            != self.topology_graph_digest
            or self.barycentric_placement.anchor_atom_index
            != int(self.anchor_atom_index)
        ):
            raise NetSymmetryDiscoveryInputError(
                "Discovery and barycentric placement source identities must agree."
            )
        trials = _positive_int(self.frame_trial_count, name="frame_trial_count")
        candidates = _positive_int(
            self.candidate_operation_count, name="candidate_operation_count"
        )
        generators = tuple(int(value) for value in self.generator_operation_indices)
        if generators != tuple(sorted(set(generators))):
            raise NetSymmetryDiscoveryInputError(
                "generator_operation_indices must be sorted and unique."
            )
        if not isinstance(self.symmetry, PeriodicNetSymmetry):
            raise NetSymmetryDiscoveryInputError("symmetry must be a PeriodicNetSymmetry.")
        if (
            self.symmetry.periodic_net_view_digest != self.periodic_net_view_digest
            or self.symmetry.topology_graph_digest != self.topology_graph_digest
            or self.symmetry.anchor_atom_index != int(self.anchor_atom_index)
        ):
            raise NetSymmetryDiscoveryInputError(
                "Discovery and symmetry source identities must agree."
            )
        if self.ring_symmetry is not None:
            if not isinstance(self.ring_symmetry, PrimitiveRingSymmetryIndex):
                raise NetSymmetryDiscoveryInputError(
                    "ring_symmetry must be a PrimitiveRingSymmetryIndex or None."
                )
            if (
                self.ring_symmetry.periodic_net_symmetry_digest != self.symmetry.digest
                or self.ring_symmetry.periodic_net_view_digest
                != self.periodic_net_view_digest
            ):
                raise NetSymmetryDiscoveryInputError(
                    "Discovery ring symmetry must belong to the stored group and view."
                )
        if any(index <= self.symmetry.identity_operation_index or index >= self.symmetry.order for index in generators):
            raise NetSymmetryDiscoveryInputError(
                "Generator indices must identify nonidentity operations in the stored group."
            )
        if self.canonical_schema_version != CANONICAL_NET_SYMMETRY_DISCOVERY_SCHEMA:
            raise NetSymmetryDiscoveryInputError("Unsupported discovery schema version.")
        if self.digest_algorithm != NET_SYMMETRY_DISCOVERY_DIGEST_ALGORITHM:
            raise NetSymmetryDiscoveryInputError("Unsupported discovery digest algorithm.")
        object.__setattr__(self, "anchor_atom_index", int(self.anchor_atom_index))
        object.__setattr__(self, "source_frame", frame)
        object.__setattr__(self, "barycentric_placement", self.barycentric_placement)
        object.__setattr__(self, "frame_trial_count", trials)
        object.__setattr__(self, "candidate_operation_count", candidates)
        object.__setattr__(self, "generator_operation_indices", generators)
        expected = _digest(self._payload(include_digest=False))
        digest = self.digest or expected
        if digest != expected:
            raise NetSymmetryDiscoveryInputError("Stored discovery digest is inconsistent.")
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PeriodicNetSymmetryDiscovery):
            return NotImplemented
        return self.digest == other.digest and self.periodic_net_view_digest == other.periodic_net_view_digest

    @property
    def generators(self) -> tuple[ValidatedPeriodicAutomorphism, ...]:
        return tuple(self.symmetry.operations[index] for index in self.generator_operation_indices)

    def _payload(self, *, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "method": self.method,
            "anchor_atom_index": self.anchor_atom_index,
            "source_frame": [
                {
                    "edge_position": item.edge_position,
                    "orientation": item.orientation,
                }
                for item in self.source_frame
            ],
            "barycentric_placement": self.barycentric_placement.to_dict(),
            "frame_trial_count": self.frame_trial_count,
            "candidate_operation_count": self.candidate_operation_count,
            "generator_operation_indices": list(self.generator_operation_indices),
            "symmetry": self.symmetry.to_dict(),
            "ring_symmetry": (
                None if self.ring_symmetry is None else self.ring_symmetry.to_dict()
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
        ring_index: PrimitiveRingIndex | None = None,
        options: NetSymmetryDiscoveryOptions | None = None,
    ) -> "PeriodicNetSymmetryDiscovery":
        try:
            if payload["periodic_net_view_digest"] != view.digest or payload[
                "topology_graph_digest"
            ] != view.source_graph_digest:
                raise NetSymmetryDiscoverySerializationError(
                    "Serialized discovery source digests do not match the supplied view."
                )
            active_options = options or NetSymmetryDiscoveryOptions()
            barycentric_placement = PeriodicBarycentricPlacement.from_dict(
                payload["barycentric_placement"],
                view=view,
                resources=PeriodicBarycentricResources(
                    max_vertices=active_options.max_barycentric_vertices,
                    max_fraction_bits=active_options.max_barycentric_fraction_bits,
                ),
            )
            symmetry = PeriodicNetSymmetry.from_dict(payload["symmetry"], view=view)
            ring_payload = payload.get("ring_symmetry")
            if ring_payload is not None and ring_index is None:
                raise NetSymmetryDiscoverySerializationError(
                    "ring_index is required to restore serialized ring symmetry."
                )
            ring_symmetry = (
                None
                if ring_payload is None
                else PrimitiveRingSymmetryIndex.from_dict(
                    ring_payload,
                    view=view,
                    symmetry=symmetry,
                    ring_index=ring_index,  # type: ignore[arg-type]
                    max_composition_checks=active_options.max_ring_composition_checks,
                )
            )
            restored = cls(
                periodic_net_view_digest=str(payload["periodic_net_view_digest"]),
                topology_graph_digest=str(payload["topology_graph_digest"]),
                method=str(payload["method"]),
                anchor_atom_index=int(payload["anchor_atom_index"]),
                source_frame=tuple(
                    BarycentricFrameIncidence(
                        edge_position=int(item["edge_position"]),
                        orientation=int(item["orientation"]),
                    )
                    for item in payload["source_frame"]
                ),
                barycentric_placement=barycentric_placement,
                frame_trial_count=int(payload["frame_trial_count"]),
                candidate_operation_count=int(payload["candidate_operation_count"]),
                generator_operation_indices=tuple(
                    int(value) for value in payload["generator_operation_indices"]
                ),
                symmetry=symmetry,
                ring_symmetry=ring_symmetry,
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
            if restored.to_dict() != dict(payload):
                raise NetSymmetryDiscoverySerializationError(
                    "Serialized discovery payload is not canonical."
                )
            return restored
        except NetSymmetryDiscoveryError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise NetSymmetryDiscoverySerializationError(
                "Invalid serialized PeriodicNetSymmetryDiscovery payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class _Incidence:
    edge_position: int
    orientation: int
    signature: NetSignature
    vector: RationalVector3



def _incidences(
    view: PeriodicNetView, coordinates: tuple[RationalVector3, ...]
) -> tuple[tuple[_Incidence, ...], ...]:
    atom_to_position = {
        atom: position for position, atom in enumerate(view.vertex_atom_indices)
    }
    values: list[list[_Incidence]] = [[] for _ in range(view.n_vertices)]
    for edge_position, (key, signature) in enumerate(
        zip(view.edge_keys, view.edge_signatures, strict=True)
    ):
        source = atom_to_position[key.vertex_i]
        target = atom_to_position[key.vertex_j]
        shift = tuple(Fraction(value) for value in key.image_shift)
        forward = _subtract(_add(coordinates[target], shift), coordinates[source])
        reverse = _negate(forward)
        values[source].append(_Incidence(edge_position, 1, signature, forward))
        values[target].append(_Incidence(edge_position, -1, signature, reverse))
    return tuple(
        tuple(
            sorted(
                row,
                key=lambda item: (
                    item.signature,
                    item.edge_position,
                    item.orientation,
                    item.vector,
                ),
            )
        )
        for row in values
    )


def _choose_anchor_and_frame(
    view: PeriodicNetView,
    coordinates: tuple[RationalVector3, ...],
    options: NetSymmetryDiscoveryOptions,
) -> tuple[int, tuple[_Incidence, _Incidence, _Incidence]]:
    incidences = _incidences(view, coordinates)
    signature_counts: dict[NetSignature, int] = {}
    for signature in view.vertex_signatures:
        signature_counts[signature] = signature_counts.get(signature, 0) + 1

    candidate_positions: Iterable[int]
    if options.anchor_atom_index is not None:
        try:
            candidate_positions = (view.vertex_position(options.anchor_atom_index),)
        except Exception as exc:
            raise NetSymmetryDiscoveryInputError(
                "anchor_atom_index is absent from the supplied net view."
            ) from exc
    else:
        candidate_positions = sorted(
            range(view.n_vertices),
            key=lambda position: (
                signature_counts[view.vertex_signatures[position]],
                len(incidences[position]),
                view.vertex_atom_indices[position],
            ),
        )

    for position in candidate_positions:
        for triple in itertools.permutations(incidences[position], 3):
            matrix = _matrix_from_columns([item.vector for item in triple])
            if _determinant_fraction(matrix) != 0:
                return position, triple
    raise NetSymmetryDiscoveryUnsupportedError(
        "No quotient vertex has three linearly independent incident barycentric edge vectors."
    )


def _target_edge_candidates(
    view: PeriodicNetView,
    *,
    signature: NetSignature,
    source_atom: int,
    target_atom: int,
    image_shift: LatticeShift,
) -> tuple[tuple[int, int], ...]:
    reverse_shift = tuple(-value for value in image_shift)
    matches: list[tuple[int, int]] = []
    for position, (key, target_signature) in enumerate(
        zip(view.edge_keys, view.edge_signatures, strict=True)
    ):
        if target_signature != signature:
            continue
        if (
            key.vertex_i == source_atom
            and key.vertex_j == target_atom
            and key.image_shift == image_shift
        ):
            matches.append((position, 1))
        if (
            key.vertex_i == target_atom
            and key.vertex_j == source_atom
            and key.image_shift == reverse_shift
        ):
            matches.append((position, -1))
    return tuple(sorted(set(matches)))


def _edge_action_for_affine_map(
    view: PeriodicNetView,
    matrix: IntMatrix3,
    vertex_images: Mapping[int, LiftedVertexRef],
) -> tuple[PeriodicEdgeImage, ...] | None:
    source_groups: dict[tuple[tuple[int, int], ...], list[int]] = {}
    for source_position, (key, signature) in enumerate(
        zip(view.edge_keys, view.edge_signatures, strict=True)
    ):
        source_image = vertex_images[key.vertex_i]
        target_image = vertex_images[key.vertex_j]
        transformed_shift = tuple(
            sum(matrix[axis][column] * key.image_shift[column] for column in range(3))
            + target_image.image_shift[axis]
            - source_image.image_shift[axis]
            for axis in range(3)
        )
        candidates = _target_edge_candidates(
            view,
            signature=signature,
            source_atom=source_image.atom_index,
            target_atom=target_image.atom_index,
            image_shift=transformed_shift,  # type: ignore[arg-type]
        )
        if not candidates:
            return None
        source_groups.setdefault(candidates, []).append(source_position)

    images: list[PeriodicEdgeImage | None] = [None] * view.n_edges
    used_targets: set[int] = set()
    for candidates, source_positions in source_groups.items():
        target_positions = sorted({position for position, _orientation in candidates})
        if len(target_positions) != len(source_positions):
            return None
        orientation_by_target = {position: orientation for position, orientation in candidates}
        for source_position, target_position in zip(
            sorted(source_positions), target_positions, strict=True
        ):
            images[source_position] = PeriodicEdgeImage(
                target_position, orientation_by_target[target_position]
            )
            used_targets.add(target_position)
    if len(used_targets) != view.n_edges or any(image is None for image in images):
        return None
    return tuple(image for image in images if image is not None)


def _candidate_from_frame(
    view: PeriodicNetView,
    coordinates: tuple[RationalVector3, ...],
    source_position: int,
    source_frame: tuple[_Incidence, _Incidence, _Incidence],
    target_position: int,
    target_frame: tuple[_Incidence, _Incidence, _Incidence],
) -> ValidatedPeriodicAutomorphism | None:
    source_matrix = _matrix_from_columns([item.vector for item in source_frame])
    target_matrix = _matrix_from_columns([item.vector for item in target_frame])
    affine = _matmul(target_matrix, _inverse_fraction_matrix(source_matrix))
    if any(value.denominator != 1 for row in affine for value in row):
        return None
    lattice_matrix: IntMatrix3 = tuple(
        tuple(int(value) for value in row) for row in affine
    )  # type: ignore[assignment]
    if abs(determinant3(lattice_matrix)) != 1:
        return None
    translation = _subtract(
        coordinates[target_position], _matvec(affine, coordinates[source_position])
    )
    coordinate_lookup = {
        _fractional_part(coordinate): position
        for position, coordinate in enumerate(coordinates)
    }
    vertex_images: dict[int, LiftedVertexRef] = {}
    for position, (atom_index, signature, coordinate) in enumerate(
        zip(
            view.vertex_atom_indices,
            view.vertex_signatures,
            coordinates,
            strict=True,
        )
    ):
        transformed = _add(_matvec(affine, coordinate), translation)
        mapped_position = coordinate_lookup.get(_fractional_part(transformed))
        if mapped_position is None or view.vertex_signatures[mapped_position] != signature:
            return None
        shift = _integer_vector(_subtract(transformed, coordinates[mapped_position]))
        if shift is None:
            return None
        vertex_images[atom_index] = LiftedVertexRef(
            view.vertex_atom_indices[mapped_position], shift
        )
    edge_images = _edge_action_for_affine_map(
        view, lattice_matrix, vertex_images
    )
    if edge_images is None:
        return None
    try:
        return build_validated_periodic_automorphism(
            view,
            lattice_matrix=lattice_matrix,
            vertex_images=vertex_images,
            edge_images=edge_images,
        )
    except ValueError:
        return None


def _identity_edge_swap_generators(
    view: PeriodicNetView,
) -> tuple[ValidatedPeriodicAutomorphism, ...]:
    groups: dict[
        tuple[NetSignature, int, int, LatticeShift], list[int]
    ] = {}
    for position, (key, signature) in enumerate(
        zip(view.edge_keys, view.edge_signatures, strict=True)
    ):
        groups.setdefault(
            (signature, key.vertex_i, key.vertex_j, key.image_shift), []
        ).append(position)
    identity_vertices = {
        atom: LiftedVertexRef(atom, (0, 0, 0)) for atom in view.vertex_atom_indices
    }
    generators: list[ValidatedPeriodicAutomorphism] = []
    for positions in groups.values():
        ordered = sorted(positions)
        for left, right in zip(ordered, ordered[1:]):
            images = [PeriodicEdgeImage(position, 1) for position in range(view.n_edges)]
            images[left] = PeriodicEdgeImage(right, 1)
            images[right] = PeriodicEdgeImage(left, 1)
            generators.append(
                build_validated_periodic_automorphism(
                    view,
                    lattice_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                    vertex_images=identity_vertices,
                    edge_images=tuple(images),
                )
            )
    return tuple(generators)


def _operation_key(automorphism: ValidatedPeriodicAutomorphism) -> tuple[Any, ...]:
    return (
        automorphism.lattice_matrix,
        automorphism.vertex_images,
        automorphism.edge_images,
    )


def _close_generators(
    view: PeriodicNetView,
    generators: Sequence[ValidatedPeriodicAutomorphism],
    *,
    anchor_atom_index: int,
    max_operations: int,
) -> dict[tuple[Any, ...], ValidatedPeriodicAutomorphism]:
    from collections import deque

    identity = identity_periodic_automorphism(
        view, anchor_atom_index=anchor_atom_index
    )
    steps: dict[tuple[Any, ...], ValidatedPeriodicAutomorphism] = {}
    for generator in generators:
        steps[_operation_key(generator)] = generator
        inverse = invert_periodic_automorphism(
            view, generator, anchor_atom_index=anchor_atom_index
        )
        steps[_operation_key(inverse)] = inverse
    discovered = {_operation_key(identity): identity}
    queue = deque([identity])
    ordered_steps = tuple(steps[key] for key in sorted(steps))
    while queue:
        current = queue.popleft()
        for step in ordered_steps:
            candidate = compose_periodic_automorphisms(
                view, current, step, anchor_atom_index=anchor_atom_index
            )
            key = _operation_key(candidate)
            if key in discovered:
                continue
            if len(discovered) >= max_operations:
                raise NetSymmetryDiscoveryResourceError(
                    "Candidate generator closure exceeded max_group_operations."
                )
            discovered[key] = candidate
            queue.append(candidate)
    return discovered


def _reduce_discovered_operations(
    view: PeriodicNetView,
    candidates: Sequence[ValidatedPeriodicAutomorphism],
    *,
    anchor_atom_index: int,
    max_operations: int,
) -> tuple[ValidatedPeriodicAutomorphism, ...]:
    ordered = tuple(sorted(candidates, key=_operation_key))
    selected: list[ValidatedPeriodicAutomorphism] = []
    closure = _close_generators(
        view, (), anchor_atom_index=anchor_atom_index, max_operations=max_operations
    )
    for candidate in ordered:
        if _operation_key(candidate) in closure:
            continue
        selected.append(candidate)
        closure = _close_generators(
            view,
            selected,
            anchor_atom_index=anchor_atom_index,
            max_operations=max_operations,
        )
    missing = {_operation_key(candidate) for candidate in ordered} - set(closure)
    if missing:  # pragma: no cover - closure invariant
        raise NetSymmetryDiscoveryError(
            "Reduced generator set does not recover every discovered operation."
        )
    return tuple(selected)


def _generator_indices(symmetry: PeriodicNetSymmetry) -> tuple[int, ...]:
    identity = symmetry.identity_operation_index
    subgroup: set[int] = {identity}
    generators: list[int] = []
    for candidate in range(symmetry.order):
        if candidate == identity or candidate in subgroup:
            continue
        generators.append(candidate)
        changed = True
        subgroup.add(candidate)
        while changed:
            changed = False
            current = tuple(sorted(subgroup))
            for outer in current:
                for inner in current:
                    product = symmetry.compose_indices(outer, inner)
                    if product not in subgroup:
                        subgroup.add(product)
                        changed = True
        if len(subgroup) == symmetry.order:
            break
    if len(subgroup) != symmetry.order:  # pragma: no cover - finite-group invariant
        raise NetSymmetryDiscoveryError("Failed to derive a complete generator subset.")
    return tuple(generators)


def discover_periodic_net_symmetry(
    view: PeriodicNetView,
    *,
    ring_index: PrimitiveRingIndex | None = None,
    options: NetSymmetryDiscoveryOptions | None = None,
) -> PeriodicNetSymmetryDiscovery:
    """Discover and certify the complete automorphism group for a stable view.

    The implementation is exact over :class:`fractions.Fraction`.  Completeness
    follows because every automorphism of a collision-free barycentric placement
    acts affinely and maps the fixed spanning source star frame to one of the
    enumerated signature-compatible target frames.  Every candidate is then
    validated against the original decorated periodic quotient multigraph.
    """

    if not isinstance(view, PeriodicNetView):
        raise NetSymmetryDiscoveryInputError("view must be a PeriodicNetView.")
    active_options = options or NetSymmetryDiscoveryOptions()
    if not isinstance(active_options, NetSymmetryDiscoveryOptions):
        raise NetSymmetryDiscoveryInputError(
            "options must be a NetSymmetryDiscoveryOptions record."
        )
    if (
        view.pbc != (True, True, True)
        or view.n_components != 1
        or view.translation_rank != 3
        or view.translation_index != 1
    ):
        raise NetSymmetryDiscoveryUnsupportedError(
            "The exact first discovery backend requires one connected, rank-three, "
            "index-one three-periodic net view."
        )

    barycentric_resources = PeriodicBarycentricResources(
        max_vertices=active_options.max_barycentric_vertices,
        max_fraction_bits=active_options.max_barycentric_fraction_bits,
    )
    provisional_anchor_atom = (
        active_options.anchor_atom_index
        if active_options.anchor_atom_index is not None
        else view.vertex_atom_indices[0]
    )
    barycentric_placement = build_periodic_barycentric_placement(
        view,
        anchor_atom_index=provisional_anchor_atom,
        resources=barycentric_resources,
    )
    if not barycentric_placement.collision_free:
        raise NetSymmetryDiscoveryUnsupportedError(
            "Barycentric placement contains lifted-vertex collisions: "
            f"{barycentric_placement.collision_atom_pairs}."
        )
    coordinates = barycentric_placement.coordinates
    anchor_position, source_frame = _choose_anchor_and_frame(
        view, coordinates, active_options
    )
    chosen_anchor_atom = view.vertex_atom_indices[anchor_position]
    if chosen_anchor_atom != barycentric_placement.anchor_atom_index:
        barycentric_placement = build_periodic_barycentric_placement(
            view,
            anchor_atom_index=chosen_anchor_atom,
            resources=barycentric_resources,
        )
        if not barycentric_placement.collision_free:
            raise NetSymmetryDiscoveryUnsupportedError(
                "Barycentric placement contains lifted-vertex collisions: "
                f"{barycentric_placement.collision_atom_pairs}."
            )
        coordinates = barycentric_placement.coordinates
        anchor_position, source_frame = _choose_anchor_and_frame(
            view,
            coordinates,
            NetSymmetryDiscoveryOptions(
                anchor_atom_index=chosen_anchor_atom,
                max_frame_trials=active_options.max_frame_trials,
                max_candidate_operations=active_options.max_candidate_operations,
                max_group_operations=active_options.max_group_operations,
                max_ring_composition_checks=active_options.max_ring_composition_checks,
                max_barycentric_vertices=active_options.max_barycentric_vertices,
                max_barycentric_fraction_bits=active_options.max_barycentric_fraction_bits,
            ),
        )

    all_incidences = _incidences(view, coordinates)
    source_signatures = tuple(item.signature for item in source_frame)
    candidates: dict[
        tuple[Any, ...], ValidatedPeriodicAutomorphism
    ] = {}
    frame_trials = 0
    for target_position, target_signature in enumerate(view.vertex_signatures):
        if target_signature != view.vertex_signatures[anchor_position]:
            continue
        for target_frame in itertools.permutations(all_incidences[target_position], 3):
            if tuple(item.signature for item in target_frame) != source_signatures:
                continue
            frame_trials += 1
            if frame_trials > active_options.max_frame_trials:
                raise NetSymmetryDiscoveryResourceError(
                    "Target-frame enumeration exceeded max_frame_trials; no partial "
                    "symmetry result is returned."
                )
            candidate = _candidate_from_frame(
                view,
                coordinates,
                anchor_position,
                source_frame,
                target_position,
                target_frame,
            )
            if candidate is None:
                continue
            key = (
                candidate.lattice_matrix,
                candidate.vertex_images,
                candidate.edge_images,
            )
            candidates[key] = candidate
            if len(candidates) > active_options.max_candidate_operations:
                raise NetSymmetryDiscoveryResourceError(
                    "Validated candidate count exceeded max_candidate_operations; "
                    "no partial symmetry result is returned."
                )

    for generator in _identity_edge_swap_generators(view):
        key = (generator.lattice_matrix, generator.vertex_images, generator.edge_images)
        candidates[key] = generator
    if len(candidates) > active_options.max_candidate_operations:
        raise NetSymmetryDiscoveryResourceError(
            "Validated candidate count exceeded max_candidate_operations after "
            "including indistinguishable-edge permutation generators."
        )
    if not candidates:
        raise NetSymmetryDiscoveryError(
            "Exact frame enumeration failed to recover even the identity operation."
        )

    reduced_generators = _reduce_discovered_operations(
        view,
        tuple(candidates.values()),
        anchor_atom_index=view.vertex_atom_indices[anchor_position],
        max_operations=active_options.max_group_operations,
    )
    symmetry = build_periodic_net_symmetry(
        view,
        reduced_generators,
        anchor_atom_index=view.vertex_atom_indices[anchor_position],
        max_operations=active_options.max_group_operations,
    )
    ring_symmetry = (
        None
        if ring_index is None
        else build_primitive_ring_symmetry_index(
            view,
            symmetry,
            ring_index,
            max_composition_checks=active_options.max_ring_composition_checks,
        )
    )
    generators = _generator_indices(symmetry)
    return PeriodicNetSymmetryDiscovery(
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        method=BARYCENTRIC_STAR_DISCOVERY_METHOD,
        anchor_atom_index=view.vertex_atom_indices[anchor_position],
        source_frame=tuple(
            BarycentricFrameIncidence(item.edge_position, item.orientation)
            for item in source_frame
        ),
        barycentric_placement=barycentric_placement,
        frame_trial_count=frame_trials,
        candidate_operation_count=len(candidates),
        generator_operation_indices=generators,
        symmetry=symmetry,
        ring_symmetry=ring_symmetry,
    )
