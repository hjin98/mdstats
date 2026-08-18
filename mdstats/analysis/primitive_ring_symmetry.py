"""Derived primitive-ring actions of one exact periodic-net symmetry group.

The finite net automorphism group is a scientific result independent of any
particular primitive-ring search bound.  This module therefore stores the
induced action as a separate, compact index bound simultaneously to one
:class:`PeriodicNetSymmetry` and one :class:`PrimitiveRingCatalog`.

Canonical ring keys are stored once.  Every operation/ring image then uses a
compact target-ring position, an exact lifted image shift, and a cycle
parameterization.  This removes repeated full key payloads while preserving the
exact nonsymmorphic translation cocycle needed for composition on absolute ring
placements.

The periodic quotient/vector representation follows Chung, Hahn, and Klee
(1984); exact periodic-net automorphisms follow Delgado-Friedrichs and O'Keeffe
(2003).

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
O. Delgado-Friedrichs and M. O'Keeffe, Acta Cryst. A 59, 351-360 (2003),
doi:10.1107/S0108767303012017.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
import hashlib
import json
from numbers import Integral
from typing import Any, Mapping, Sequence

from ._periodic_graph import add_shift, matvec_shift, subtract_shift
from .net_symmetry import PeriodicNetSymmetry
from .periodic_cycle import CycleParameterization, RingPlacement
from .periodic_net_view import PeriodicNetView
from .periodic_ring_action import map_ring_placement
from .primitive_ring import LatticeShift, PrimitiveRingKey
from .primitive_ring_index import PrimitiveRingIndex

CANONICAL_PRIMITIVE_RING_SYMMETRY_SCHEMA = "mdstats.primitive-ring-symmetry.v1"
PRIMITIVE_RING_SYMMETRY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class PrimitiveRingSymmetryError(ValueError):
    """Base exception for derived primitive-ring symmetry indexing."""


class PrimitiveRingSymmetryInputError(PrimitiveRingSymmetryError):
    """Raised when source objects or derived action records are incompatible."""


class PrimitiveRingSymmetryResourceError(PrimitiveRingSymmetryError):
    """Raised when exact action validation exceeds a declared limit."""


class PrimitiveRingSymmetryValidationError(PrimitiveRingSymmetryError):
    """Raised when the induced ring action violates exact group composition."""


class PrimitiveRingSymmetrySerializationError(PrimitiveRingSymmetryError):
    """Raised when serialized ring-action data fail source validation."""


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise PrimitiveRingSymmetryInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive_int(value: Any, *, name: str) -> int:
    result = _nonnegative_int(value, name=name)
    if result == 0:
        raise PrimitiveRingSymmetryInputError(f"{name} must be positive.")
    return result


def _orbit_partition(
    element_positions: Sequence[int], image_sets: Mapping[int, set[int]]
) -> tuple[tuple[int, ...], ...]:
    remaining = set(element_positions)
    result: list[tuple[int, ...]] = []
    while remaining:
        seed = min(remaining)
        orbit = tuple(sorted(image_sets[seed]))
        if not set(orbit).issubset(remaining):
            raise PrimitiveRingSymmetryValidationError(
                "Ring orbit sets do not form a partition."
            )
        remaining.difference_update(orbit)
        result.append(orbit)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class RingSymmetryImage:
    """Compact image of one canonical zero-shift primitive-ring placement."""

    target_ring_position: int
    target_image_shift: LatticeShift
    parameterization: CycleParameterization

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_ring_position",
            _nonnegative_int(self.target_ring_position, name="target_ring_position"),
        )
        try:
            shift = tuple(int(value) for value in self.target_image_shift)
        except (TypeError, ValueError) as exc:
            raise PrimitiveRingSymmetryInputError(
                "target_image_shift must contain exactly three integers."
            ) from exc
        if len(shift) != 3:
            raise PrimitiveRingSymmetryInputError(
                "target_image_shift must contain exactly three integers."
            )
        if not isinstance(self.parameterization, CycleParameterization):
            raise PrimitiveRingSymmetryInputError(
                "parameterization must be a CycleParameterization."
            )
        object.__setattr__(self, "target_image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_ring_position": self.target_ring_position,
            "target_image_shift": list(self.target_image_shift),
            "parameterization": {
                "start_vertex_index": self.parameterization.start_vertex_index,
                "orientation": self.parameterization.orientation,
            },
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RingSymmetryImage":
        try:
            parameterization = payload["parameterization"]
            return cls(
                target_ring_position=int(payload["target_ring_position"]),
                target_image_shift=tuple(
                    int(value) for value in payload["target_image_shift"]
                ),
                parameterization=CycleParameterization(
                    start_vertex_index=int(parameterization["start_vertex_index"]),
                    orientation=int(parameterization["orientation"]),  # type: ignore[arg-type]
                ),
            )
        except PrimitiveRingSymmetryError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PrimitiveRingSymmetrySerializationError(
                "Invalid serialized RingSymmetryImage payload."
            ) from exc


@dataclass(frozen=True, slots=True, eq=False)
class PrimitiveRingSymmetryIndex:
    """Compact induced ring action bound to one symmetry and ring catalog."""

    periodic_net_symmetry_digest: str
    periodic_net_view_digest: str
    topology_graph_digest: str
    primitive_ring_catalog_digest: str
    complete_for_ring_sizes_up_to: int
    source_search_completed_without_resource_truncation: bool
    ring_keys: tuple[PrimitiveRingKey, ...]
    action_table: tuple[tuple[RingSymmetryImage, ...], ...]
    ring_orbits: tuple[tuple[int, ...], ...]
    ring_stabilizers: tuple[tuple[int, ...], ...]
    canonical_schema_version: str = CANONICAL_PRIMITIVE_RING_SYMMETRY_SCHEMA
    digest_algorithm: str = PRIMITIVE_RING_SYMMETRY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "periodic_net_symmetry_digest",
            "periodic_net_view_digest",
            "topology_graph_digest",
            "primitive_ring_catalog_digest",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise PrimitiveRingSymmetryInputError(f"{name} must be a SHA-256 digest.")
        complete = _nonnegative_int(
            self.complete_for_ring_sizes_up_to,
            name="complete_for_ring_sizes_up_to",
        )
        ring_keys = tuple(self.ring_keys)
        if ring_keys != tuple(sorted(set(ring_keys))):
            raise PrimitiveRingSymmetryInputError(
                "ring_keys must be sorted and unique."
            )
        actions = tuple(tuple(row) for row in self.action_table)
        if not actions:
            raise PrimitiveRingSymmetryInputError("action_table must be nonempty.")
        if any(len(row) != len(ring_keys) for row in actions):
            raise PrimitiveRingSymmetryInputError(
                "action_table rows must align with ring_keys."
            )
        if any(
            not isinstance(image, RingSymmetryImage)
            or image.target_ring_position >= len(ring_keys)
            for row in actions
            for image in row
        ):
            raise PrimitiveRingSymmetryInputError(
                "action_table contains an invalid ring image."
            )
        orbits = tuple(tuple(int(value) for value in orbit) for orbit in self.ring_orbits)
        if any(
            not orbit
            or orbit != tuple(sorted(set(orbit)))
            or any(value < 0 or value >= len(ring_keys) for value in orbit)
            for orbit in orbits
        ):
            raise PrimitiveRingSymmetryInputError(
                "ring_orbits must be nonempty sorted position sets."
            )
        covered = sorted(value for orbit in orbits for value in orbit)
        if covered != list(range(len(ring_keys))):
            raise PrimitiveRingSymmetryInputError(
                "ring_orbits must partition every ring position."
            )
        stabilizers = tuple(
            tuple(int(value) for value in row) for row in self.ring_stabilizers
        )
        if len(stabilizers) != len(ring_keys) or any(
            value < 0 or value >= len(actions)
            for row in stabilizers
            for value in row
        ):
            raise PrimitiveRingSymmetryInputError(
                "ring_stabilizers must align with ring_keys and operation indices."
            )
        if self.canonical_schema_version != CANONICAL_PRIMITIVE_RING_SYMMETRY_SCHEMA:
            raise PrimitiveRingSymmetryInputError(
                "Unsupported primitive-ring symmetry schema."
            )
        if self.digest_algorithm != PRIMITIVE_RING_SYMMETRY_DIGEST_ALGORITHM:
            raise PrimitiveRingSymmetryInputError(
                "Unsupported primitive-ring symmetry digest algorithm."
            )
        object.__setattr__(self, "complete_for_ring_sizes_up_to", complete)
        object.__setattr__(
            self,
            "source_search_completed_without_resource_truncation",
            bool(self.source_search_completed_without_resource_truncation),
        )
        object.__setattr__(self, "ring_keys", ring_keys)
        object.__setattr__(self, "action_table", actions)
        object.__setattr__(self, "ring_orbits", orbits)
        object.__setattr__(self, "ring_stabilizers", stabilizers)
        expected = _digest(self._payload(include_digest=False))
        digest = self.digest or expected
        if digest != expected:
            raise PrimitiveRingSymmetryInputError(
                "Stored primitive-ring symmetry digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PrimitiveRingSymmetryIndex):
            return NotImplemented
        return (
            self.digest == other.digest
            and self.periodic_net_symmetry_digest
            == other.periodic_net_symmetry_digest
            and self.primitive_ring_catalog_digest
            == other.primitive_ring_catalog_digest
        )

    @property
    def order(self) -> int:
        return len(self.action_table)

    def ring_position(self, ring_key: PrimitiveRingKey) -> int:
        position = bisect_left(self.ring_keys, ring_key)
        if position >= len(self.ring_keys) or self.ring_keys[position] != ring_key:
            raise PrimitiveRingSymmetryInputError(
                "ring_key is absent from this ring-symmetry index."
            )
        return position

    def ring_key(self, position: int) -> PrimitiveRingKey:
        value = _nonnegative_int(position, name="position")
        if value >= len(self.ring_keys):
            raise PrimitiveRingSymmetryInputError(
                "ring position is outside this ring-symmetry index."
            )
        return self.ring_keys[value]

    def ring_image(
        self, operation_index: int, ring_key: PrimitiveRingKey
    ) -> RingSymmetryImage:
        operation = _nonnegative_int(operation_index, name="operation_index")
        if operation >= self.order:
            raise PrimitiveRingSymmetryInputError(
                "operation_index is outside this ring-symmetry index."
            )
        return self.action_table[operation][self.ring_position(ring_key)]

    def target_ring_key(self, image: RingSymmetryImage) -> PrimitiveRingKey:
        if not isinstance(image, RingSymmetryImage):
            raise PrimitiveRingSymmetryInputError(
                "image must be a RingSymmetryImage."
            )
        return self.ring_key(image.target_ring_position)

    @property
    def ring_key_orbits(self) -> tuple[tuple[PrimitiveRingKey, ...], ...]:
        return tuple(
            tuple(self.ring_keys[position] for position in orbit)
            for orbit in self.ring_orbits
        )

    def map_placement(
        self,
        symmetry: PeriodicNetSymmetry,
        operation_index: int,
        placement: RingPlacement,
    ) -> RingPlacement:
        if symmetry.digest != self.periodic_net_symmetry_digest:
            raise PrimitiveRingSymmetryInputError(
                "symmetry does not own this ring-symmetry index."
            )
        if placement.topology_graph_digest != self.topology_graph_digest:
            raise PrimitiveRingSymmetryInputError(
                "placement belongs to a different topology graph."
            )
        operation = _nonnegative_int(operation_index, name="operation_index")
        if operation >= symmetry.order:
            raise PrimitiveRingSymmetryInputError(
                "operation_index is outside the symmetry group."
            )
        image = self.ring_image(operation, placement.ring_key)
        target_shift = add_shift(
            matvec_shift(
                symmetry.operations[operation].lattice_matrix,
                placement.image_shift,
            ),
            image.target_image_shift,
        )
        return RingPlacement(
            self.topology_graph_digest,
            self.ring_key(image.target_ring_position),
            target_shift,
        )

    def _payload(self, *, include_digest: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "periodic_net_symmetry_digest": self.periodic_net_symmetry_digest,
            "periodic_net_view_digest": self.periodic_net_view_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "complete_for_ring_sizes_up_to": self.complete_for_ring_sizes_up_to,
            "source_search_completed_without_resource_truncation": (
                self.source_search_completed_without_resource_truncation
            ),
            "ring_keys": [key.to_dict() for key in self.ring_keys],
            "action_table": [
                [image.to_dict() for image in row] for row in self.action_table
            ],
            "ring_orbits": [list(orbit) for orbit in self.ring_orbits],
            "ring_stabilizers": [list(row) for row in self.ring_stabilizers],
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
        symmetry: PeriodicNetSymmetry,
        ring_index: PrimitiveRingIndex,
        max_composition_checks: int = 5_000_000,
    ) -> "PrimitiveRingSymmetryIndex":
        try:
            if payload["periodic_net_symmetry_digest"] != symmetry.digest:
                raise PrimitiveRingSymmetrySerializationError(
                    "Serialized ring action belongs to another symmetry result."
                )
            if payload["primitive_ring_catalog_digest"] != ring_index.catalog_digest:
                raise PrimitiveRingSymmetrySerializationError(
                    "Serialized ring action belongs to another primitive-ring catalog."
                )
            rebuilt = build_primitive_ring_symmetry_index(
                view,
                symmetry,
                ring_index,
                max_composition_checks=max_composition_checks,
            )
            if rebuilt.to_dict() != dict(payload):
                raise PrimitiveRingSymmetrySerializationError(
                    "Serialized primitive-ring symmetry payload is not canonical."
                )
            return rebuilt
        except PrimitiveRingSymmetryError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PrimitiveRingSymmetrySerializationError(
                "Invalid serialized PrimitiveRingSymmetryIndex payload."
            ) from exc


def build_primitive_ring_symmetry_index(
    view: PeriodicNetView,
    symmetry: PeriodicNetSymmetry,
    ring_index: PrimitiveRingIndex,
    *,
    max_composition_checks: int = 5_000_000,
) -> PrimitiveRingSymmetryIndex:
    """Build and exactly validate the induced action on one ring catalog."""

    if not isinstance(view, PeriodicNetView):
        raise PrimitiveRingSymmetryInputError("view must be a PeriodicNetView.")
    if not isinstance(symmetry, PeriodicNetSymmetry):
        raise PrimitiveRingSymmetryInputError(
            "symmetry must be a PeriodicNetSymmetry."
        )
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise PrimitiveRingSymmetryInputError(
            "ring_index must be a PrimitiveRingIndex."
        )
    if (
        symmetry.periodic_net_view_digest != view.digest
        or symmetry.topology_graph_digest != view.source_graph_digest
    ):
        raise PrimitiveRingSymmetryInputError(
            "PeriodicNetSymmetry and PeriodicNetView have different sources."
        )
    if ring_index.topology_graph_digest != view.source_graph_digest:
        raise PrimitiveRingSymmetryInputError(
            "PrimitiveRingIndex and PeriodicNetView have different topology sources."
        )
    index_edge_keys = tuple(
        search.edge_key for search in ring_index.catalog.edge_searches
    )
    if set(index_edge_keys) != set(view.edge_keys):
        raise PrimitiveRingSymmetryInputError(
            "PrimitiveRingIndex and PeriodicNetView expose different edge-orbit sets."
        )
    check_limit = _positive_int(
        max_composition_checks, name="max_composition_checks"
    )
    ring_keys = tuple(sorted(ring.key for ring in ring_index.catalog.rings))
    ring_positions = {key: position for position, key in enumerate(ring_keys)}
    rows: list[tuple[RingSymmetryImage, ...]] = []
    for operation in symmetry.operations:
        images: list[RingSymmetryImage] = []
        for ring_key in ring_keys:
            occurrence = map_ring_placement(
                ring_index,
                view,
                operation,
                RingPlacement(view.source_graph_digest, ring_key, (0, 0, 0)),
            )
            images.append(
                RingSymmetryImage(
                    target_ring_position=ring_positions[
                        occurrence.target_placement.ring_key
                    ],
                    target_image_shift=occurrence.target_placement.image_shift,
                    parameterization=occurrence.parameterization,
                )
            )
        rows.append(tuple(images))
    action_table = tuple(rows)

    required_checks = symmetry.order * symmetry.order * len(ring_keys)
    if required_checks > check_limit:
        raise PrimitiveRingSymmetryResourceError(
            "Exact ring-action composition validation exceeds max_composition_checks."
        )
    for outer_index, outer in enumerate(symmetry.operations):
        for inner_index in range(symmetry.order):
            composed_index = symmetry.multiplication_table[outer_index][inner_index]
            for source_position, source_key in enumerate(ring_keys):
                direct = action_table[composed_index][source_position]
                inner_image = action_table[inner_index][source_position]
                outer_image = action_table[outer_index][
                    inner_image.target_ring_position
                ]
                expected_shift = subtract_shift(
                    add_shift(
                        matvec_shift(
                            outer.lattice_matrix,
                            inner_image.target_image_shift,
                        ),
                        outer_image.target_image_shift,
                    ),
                    symmetry.composition_translation_table[outer_index][inner_index],
                )
                if (
                    direct.target_ring_position
                    != outer_image.target_ring_position
                    or direct.target_image_shift != expected_shift
                ):
                    raise PrimitiveRingSymmetryValidationError(
                        "Induced primitive-ring placement action violates group composition."
                    )
                source_size = len(source_key.edge_tokens)
                expected_orientation = (
                    outer_image.parameterization.orientation
                    * inner_image.parameterization.orientation
                )
                expected_start = (
                    outer_image.parameterization.start_vertex_index
                    + outer_image.parameterization.orientation
                    * inner_image.parameterization.start_vertex_index
                ) % source_size
                if (
                    direct.parameterization.orientation != expected_orientation
                    or direct.parameterization.start_vertex_index != expected_start
                ):
                    raise PrimitiveRingSymmetryValidationError(
                        "Induced primitive-ring occurrence action violates group composition."
                    )

    image_sets = {
        position: {
            action_table[operation_index][position].target_ring_position
            for operation_index in range(symmetry.order)
        }
        for position in range(len(ring_keys))
    }
    orbits = _orbit_partition(tuple(range(len(ring_keys))), image_sets)
    stabilizers = tuple(
        tuple(
            operation_index
            for operation_index in range(symmetry.order)
            if action_table[operation_index][position].target_ring_position == position
        )
        for position in range(len(ring_keys))
    )
    return PrimitiveRingSymmetryIndex(
        periodic_net_symmetry_digest=symmetry.digest,
        periodic_net_view_digest=view.digest,
        topology_graph_digest=view.source_graph_digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        complete_for_ring_sizes_up_to=(
            ring_index.source_complete_for_ring_sizes_up_to
        ),
        source_search_completed_without_resource_truncation=(
            ring_index.source_search_completed_without_resource_truncation
        ),
        ring_keys=ring_keys,
        action_table=action_table,
        ring_orbits=orbits,
        ring_stabilizers=stabilizers,
    )


__all__ = [
    "CANONICAL_PRIMITIVE_RING_SYMMETRY_SCHEMA",
    "PRIMITIVE_RING_SYMMETRY_DIGEST_ALGORITHM",
    "PrimitiveRingSymmetryError",
    "PrimitiveRingSymmetryIndex",
    "PrimitiveRingSymmetryInputError",
    "PrimitiveRingSymmetryResourceError",
    "PrimitiveRingSymmetrySerializationError",
    "PrimitiveRingSymmetryValidationError",
    "RingSymmetryImage",
    "build_primitive_ring_symmetry_index",
]
