"""Stage-11B conservative cage, portal, and accessibility semantics.

A natural tile is topological.  This module promotes it to an accessible cage
only through an explicit probe witness.  Likewise, a topological window becomes
an accessible portal only when its stored in-plane aperture witness and its
periodic obstacle clearance both admit the probe.  Failure of a witness is not a
proof of global inaccessibility and remains explicitly unresolved.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
import json
import math
from numbers import Integral
from typing import Any, Mapping, Sequence

import numpy as np

from ._periodic_graph import LatticeShift, add_shift, coerce_lattice_shift, subtract_shift
from .periodic_net_embedding import PeriodicNetEmbedding
from .tiling_geometry import TilingGeometryCatalog

CANONICAL_CAGE_ACCESSIBILITY_SCHEMA = "mdstats.cage-accessibility.v1"
CAGE_ACCESSIBILITY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"


class CageAnalysisError(ValueError):
    """Base exception for Stage-11B cage analysis."""


class CageAnalysisInputError(CageAnalysisError):
    """Raised when probe or source records are invalid."""


class CageAnalysisResourceError(CageAnalysisError):
    """Raised transactionally before a declared finite limit is exceeded."""


class CageAnalysisSerializationError(CageAnalysisError):
    """Raised when deterministic source replay rejects stored data."""


class WitnessAccessibilityStatus(str, Enum):
    CERTIFIED_ACCESSIBLE_AT_WITNESS = "certified-accessible-at-witness"
    WITNESS_BLOCKED_UNRESOLVED = "witness-blocked-unresolved"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise CageAnalysisInputError(f"{name} must be a SHA-256 digest.")
    return value


def _finite_nonnegative(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise CageAnalysisInputError(f"{name} must be finite and nonnegative.")
    return result


def _positive(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise CageAnalysisInputError(f"{name} must be a positive integer.")
    return int(value)


def _fractional_point(value: Sequence[object], *, name: str) -> tuple[Fraction, Fraction, Fraction]:
    result = tuple(Fraction(component) for component in value)
    if len(result) != 3:
        raise CageAnalysisInputError(f"{name} must contain three components.")
    return result  # type: ignore[return-value]


def _point_payload(point: Sequence[Fraction]) -> list[list[int]]:
    return [[value.numerator, value.denominator] for value in point]


@dataclass(frozen=True, slots=True)
class CageAccessibilityResources:
    max_obstacles: int = 100_000
    max_periodic_image_tests: int = 5_000_000
    max_network_arcs: int = 1_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))


@dataclass(frozen=True, order=True, slots=True)
class PeriodicObstacleSphere:
    obstacle_id: int
    fractional_coordinate: tuple[Fraction, Fraction, Fraction]
    radius: float
    label: str = ""

    def __post_init__(self) -> None:
        if isinstance(self.obstacle_id, bool) or int(self.obstacle_id) < 0:
            raise CageAnalysisInputError("obstacle_id must be nonnegative.")
        object.__setattr__(self, "obstacle_id", int(self.obstacle_id))
        object.__setattr__(
            self,
            "fractional_coordinate",
            _fractional_point(self.fractional_coordinate, name="fractional_coordinate"),
        )
        object.__setattr__(self, "radius", _finite_nonnegative(self.radius, name="radius"))
        if not isinstance(self.label, str):
            raise CageAnalysisInputError("label must be a string.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "obstacle_id": self.obstacle_id,
            "fractional_coordinate": _point_payload(self.fractional_coordinate),
            "radius": self.radius,
            "label": self.label,
        }


@dataclass(frozen=True, slots=True)
class AccessibilityProbe:
    radius: float
    label: str = "probe"

    def __post_init__(self) -> None:
        object.__setattr__(self, "radius", _finite_nonnegative(self.radius, name="radius"))
        if not isinstance(self.label, str) or not self.label:
            raise CageAnalysisInputError("Probe label must be a nonempty string.")

    def to_dict(self) -> dict[str, Any]:
        return {"radius": self.radius, "label": self.label}


@dataclass(frozen=True, slots=True)
class CageWitnessAssessment:
    tile_index: int
    status: WitnessAccessibilityStatus
    witness_fractional: tuple[Fraction, Fraction, Fraction]
    obstacle_clearance: float | None
    limiting_obstacle_id: int | None

    def __post_init__(self) -> None:
        if isinstance(self.tile_index, bool) or int(self.tile_index) < 0:
            raise CageAnalysisInputError("tile_index must be nonnegative.")
        object.__setattr__(self, "tile_index", int(self.tile_index))
        object.__setattr__(self, "status", WitnessAccessibilityStatus(self.status))
        object.__setattr__(
            self,
            "witness_fractional",
            _fractional_point(self.witness_fractional, name="witness_fractional"),
        )
        if self.obstacle_clearance is not None:
            value = float(self.obstacle_clearance)
            if not math.isfinite(value):
                raise CageAnalysisInputError("obstacle_clearance must be finite or None.")
            object.__setattr__(self, "obstacle_clearance", value)
        if self.limiting_obstacle_id is not None and int(self.limiting_obstacle_id) < 0:
            raise CageAnalysisInputError("limiting_obstacle_id must be nonnegative or None.")

    @property
    def accessible(self) -> bool:
        return self.status is WitnessAccessibilityStatus.CERTIFIED_ACCESSIBLE_AT_WITNESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "status": self.status.value,
            "witness_fractional": _point_payload(self.witness_fractional),
            "obstacle_clearance": self.obstacle_clearance,
            "limiting_obstacle_id": self.limiting_obstacle_id,
            "accessible": self.accessible,
        }


@dataclass(frozen=True, slots=True)
class PortalWitnessAssessment:
    window_index: int
    status: WitnessAccessibilityStatus
    witness_fractional: tuple[Fraction, Fraction, Fraction]
    topological_aperture_radius: float
    obstacle_clearance: float | None
    limiting_obstacle_id: int | None

    def __post_init__(self) -> None:
        if isinstance(self.window_index, bool) or int(self.window_index) < 0:
            raise CageAnalysisInputError("window_index must be nonnegative.")
        object.__setattr__(self, "window_index", int(self.window_index))
        object.__setattr__(self, "status", WitnessAccessibilityStatus(self.status))
        object.__setattr__(
            self,
            "witness_fractional",
            _fractional_point(self.witness_fractional, name="witness_fractional"),
        )
        aperture = _finite_nonnegative(self.topological_aperture_radius, name="topological_aperture_radius")
        object.__setattr__(self, "topological_aperture_radius", aperture)
        if self.obstacle_clearance is not None:
            value = float(self.obstacle_clearance)
            if not math.isfinite(value):
                raise CageAnalysisInputError("obstacle_clearance must be finite or None.")
            object.__setattr__(self, "obstacle_clearance", value)
        if self.limiting_obstacle_id is not None and int(self.limiting_obstacle_id) < 0:
            raise CageAnalysisInputError("limiting_obstacle_id must be nonnegative or None.")

    @property
    def accessible(self) -> bool:
        return self.status is WitnessAccessibilityStatus.CERTIFIED_ACCESSIBLE_AT_WITNESS

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "status": self.status.value,
            "witness_fractional": _point_payload(self.witness_fractional),
            "topological_aperture_radius": self.topological_aperture_radius,
            "obstacle_clearance": self.obstacle_clearance,
            "limiting_obstacle_id": self.limiting_obstacle_id,
            "accessible": self.accessible,
        }


@dataclass(frozen=True, slots=True)
class AccessibleNetworkComponent:
    component_index: int
    tile_indices: tuple[int, ...]
    translation_rank: int
    translation_generators: tuple[LatticeShift, ...]

    def __post_init__(self) -> None:
        if isinstance(self.component_index, bool) or int(self.component_index) < 0:
            raise CageAnalysisInputError("component_index must be nonnegative.")
        tiles = tuple(int(value) for value in self.tile_indices)
        if not tiles or tiles != tuple(sorted(set(tiles))):
            raise CageAnalysisInputError("tile_indices must be nonempty, sorted, and unique.")
        rank = int(self.translation_rank)
        if rank < 0 or rank > 3:
            raise CageAnalysisInputError("translation_rank must lie in [0, 3].")
        generators = tuple(coerce_lattice_shift(value, name="translation_generator") for value in self.translation_generators)
        object.__setattr__(self, "component_index", int(self.component_index))
        object.__setattr__(self, "tile_indices", tiles)
        object.__setattr__(self, "translation_rank", rank)
        object.__setattr__(self, "translation_generators", generators)

    @property
    def dimensionality(self) -> str:
        return ("isolated-cage", "one-dimensional-channel", "two-dimensional-layer", "three-dimensional-network")[self.translation_rank]

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_index": self.component_index,
            "tile_indices": list(self.tile_indices),
            "translation_rank": self.translation_rank,
            "translation_generators": [list(value) for value in self.translation_generators],
            "dimensionality": self.dimensionality,
        }


@dataclass(frozen=True, slots=True, eq=False)
class CageAccessibilityCatalog:
    tiling_geometry_digest: str
    periodic_net_embedding_digest: str
    probe: AccessibilityProbe
    obstacles: tuple[PeriodicObstacleSphere, ...]
    cages: tuple[CageWitnessAssessment, ...]
    portals: tuple[PortalWitnessAssessment, ...]
    accessible_arc_indices: tuple[int, ...]
    network_components: tuple[AccessibleNetworkComponent, ...]
    periodic_image_test_count: int
    canonical_schema_version: str = CANONICAL_CAGE_ACCESSIBILITY_SCHEMA
    digest_algorithm: str = CAGE_ACCESSIBILITY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _sha(self.tiling_geometry_digest, name="tiling_geometry_digest")
        _sha(self.periodic_net_embedding_digest, name="periodic_net_embedding_digest")
        if not isinstance(self.probe, AccessibilityProbe):
            raise CageAnalysisInputError("probe must be an AccessibilityProbe.")
        obstacles = tuple(self.obstacles)
        if tuple(value.obstacle_id for value in obstacles) != tuple(range(len(obstacles))):
            raise CageAnalysisInputError("Obstacle IDs must be dense and ordered.")
        cages = tuple(self.cages)
        portals = tuple(self.portals)
        if tuple(value.tile_index for value in cages) != tuple(range(len(cages))):
            raise CageAnalysisInputError("Cage assessments must align with tile IDs.")
        if tuple(value.window_index for value in portals) != tuple(range(len(portals))):
            raise CageAnalysisInputError("Portal assessments must align with window IDs.")
        arcs = tuple(int(value) for value in self.accessible_arc_indices)
        if arcs != tuple(sorted(set(arcs))) or any(value < 0 for value in arcs):
            raise CageAnalysisInputError("accessible_arc_indices must be sorted, unique, and nonnegative.")
        components = tuple(self.network_components)
        if tuple(value.component_index for value in components) != tuple(range(len(components))):
            raise CageAnalysisInputError("Network component IDs must be dense and ordered.")
        tests = int(self.periodic_image_test_count)
        if tests < 0:
            raise CageAnalysisInputError("periodic_image_test_count must be nonnegative.")
        if self.canonical_schema_version != CANONICAL_CAGE_ACCESSIBILITY_SCHEMA:
            raise CageAnalysisInputError("Unsupported cage-accessibility schema.")
        if self.digest_algorithm != CAGE_ACCESSIBILITY_DIGEST_ALGORITHM:
            raise CageAnalysisInputError("Unsupported cage-accessibility digest algorithm.")
        object.__setattr__(self, "obstacles", obstacles)
        object.__setattr__(self, "cages", cages)
        object.__setattr__(self, "portals", portals)
        object.__setattr__(self, "accessible_arc_indices", arcs)
        object.__setattr__(self, "network_components", components)
        object.__setattr__(self, "periodic_image_test_count", tests)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise CageAnalysisInputError("Stored cage-accessibility digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, CageAccessibilityCatalog) and self.digest == other.digest

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "tiling_geometry_digest": self.tiling_geometry_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "probe": self.probe.to_dict(),
            "obstacles": [value.to_dict() for value in self.obstacles],
            "cages": [value.to_dict() for value in self.cages],
            "portals": [value.to_dict() for value in self.portals],
            "accessible_arc_indices": list(self.accessible_arc_indices),
            "network_components": [value.to_dict() for value in self.network_components],
            "periodic_image_test_count": self.periodic_image_test_count,
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
        geometry: TilingGeometryCatalog,
        embedding: PeriodicNetEmbedding,
        resources: CageAccessibilityResources | None = None,
    ) -> "CageAccessibilityCatalog":
        probe_payload = payload["probe"]
        obstacles_payload = payload["obstacles"]
        probe = AccessibilityProbe(float(probe_payload["radius"]), str(probe_payload["label"]))
        obstacles = tuple(
            PeriodicObstacleSphere(
                int(value["obstacle_id"]),
                tuple(Fraction(int(item[0]), int(item[1])) for item in value["fractional_coordinate"]),
                float(value["radius"]),
                str(value.get("label", "")),
            )
            for value in obstacles_payload
        )
        rebuilt = assess_cage_accessibility(
            geometry,
            embedding,
            probe,
            obstacles,
            resources=resources,
        )
        if rebuilt.to_dict() != dict(payload):
            raise CageAnalysisSerializationError(
                "Serialized cage accessibility is not canonical for the supplied sources."
            )
        return rebuilt


def _nearest_periodic_clearance(
    point_fractional: Sequence[Fraction],
    obstacles: Sequence[PeriodicObstacleSphere],
    cell: np.ndarray,
    inverse_cell: np.ndarray,
    counter: list[int],
    resources: CageAccessibilityResources,
) -> tuple[float | None, int | None]:
    if not obstacles:
        return None, None
    point = np.asarray([float(value) for value in point_fractional], dtype=np.float64)
    best = math.inf
    best_id: int | None = None
    reciprocal_norms = tuple(float(np.linalg.norm(inverse_cell[:, axis])) for axis in range(3))
    for obstacle in obstacles:
        origin = np.asarray([float(value) for value in obstacle.fractional_coordinate], dtype=np.float64)
        displacement = point - origin
        seed = np.asarray([int(round(-value)) for value in displacement], dtype=np.int64)
        upper = float(np.linalg.norm((displacement + seed) @ cell))
        ranges = []
        for axis in range(3):
            radius = upper * reciprocal_norms[axis] + 1e-12
            low = math.ceil(-displacement[axis] - radius)
            high = math.floor(-displacement[axis] + radius)
            if low > high:
                low = high = int(seed[axis])
            ranges.append(range(low, high + 1))
        for shift in itertools.product(*ranges):
            counter[0] += 1
            if counter[0] > resources.max_periodic_image_tests:
                raise CageAnalysisResourceError("Periodic obstacle work exceeds max_periodic_image_tests.")
            distance = float(np.linalg.norm((displacement + np.asarray(shift, dtype=np.float64)) @ cell)) - obstacle.radius
            if distance < best:
                best = distance
                best_id = obstacle.obstacle_id
    return best, best_id


def _matrix_rank(vectors: Sequence[LatticeShift]) -> int:
    if not vectors:
        return 0
    matrix = [[Fraction(value) for value in vector] for vector in vectors if vector != (0, 0, 0)]
    if not matrix:
        return 0
    row = 0
    column = 0
    while row < len(matrix) and column < 3:
        pivot = next((index for index in range(row, len(matrix)) if matrix[index][column] != 0), None)
        if pivot is None:
            column += 1
            continue
        matrix[row], matrix[pivot] = matrix[pivot], matrix[row]
        divisor = matrix[row][column]
        matrix[row] = [value / divisor for value in matrix[row]]
        for index in range(len(matrix)):
            if index == row:
                continue
            factor = matrix[index][column]
            if factor != 0:
                matrix[index] = [matrix[index][axis] - factor * matrix[row][axis] for axis in range(3)]
        row += 1
        column += 1
    return row


def _network_components(
    geometry: TilingGeometryCatalog,
    accessible_arc_indices: Sequence[int],
    accessible_tile_indices: Sequence[int],
) -> tuple[AccessibleNetworkComponent, ...]:
    adjacency: dict[int, list[tuple[int, LatticeShift]]] = defaultdict(list)
    for arc_index in accessible_arc_indices:
        arc = geometry.adjacency_arcs[arc_index]
        adjacency[arc.source_tile_index].append((arc.target_tile_index, arc.target_image_shift))
    components: list[AccessibleNetworkComponent] = []
    seen: set[int] = set()
    admitted_tiles = tuple(sorted(set(int(value) for value in accessible_tile_indices)))
    for seed in admitted_tiles:
        if seed in seen:
            continue
        queue = deque([seed])
        potentials: dict[int, LatticeShift] = {seed: (0, 0, 0)}
        vertices: set[int] = {seed}
        cycle_vectors: list[LatticeShift] = []
        while queue:
            source = queue.popleft()
            seen.add(source)
            for target, shift in adjacency.get(source, ()):
                proposed = add_shift(potentials[source], shift)
                if target not in potentials:
                    potentials[target] = proposed
                    vertices.add(target)
                    queue.append(target)
                else:
                    cycle = subtract_shift(proposed, potentials[target])
                    if cycle != (0, 0, 0):
                        cycle_vectors.append(cycle)
        unique_generators = tuple(sorted(set(cycle_vectors)))
        components.append(
            AccessibleNetworkComponent(
                len(components),
                tuple(sorted(vertices)),
                _matrix_rank(unique_generators),
                unique_generators,
            )
        )
    return tuple(components)


def assess_cage_accessibility(
    geometry: TilingGeometryCatalog,
    embedding: PeriodicNetEmbedding,
    probe: AccessibilityProbe,
    obstacles: Sequence[PeriodicObstacleSphere] = (),
    *,
    resources: CageAccessibilityResources | None = None,
) -> CageAccessibilityCatalog:
    """Assess explicit cage and portal witnesses under periodic sphere obstacles.

    ``CERTIFIED_ACCESSIBLE_AT_WITNESS`` is a sufficient certificate.  A blocked
    witness is stored as ``WITNESS_BLOCKED_UNRESOLVED`` because another point or
    non-spherical path may still be accessible.
    """

    if not isinstance(geometry, TilingGeometryCatalog):
        raise CageAnalysisInputError("geometry must be a TilingGeometryCatalog.")
    if not isinstance(embedding, PeriodicNetEmbedding):
        raise CageAnalysisInputError("embedding must be a PeriodicNetEmbedding.")
    if geometry.periodic_net_embedding_digest != embedding.digest:
        raise CageAnalysisInputError("Geometry and embedding digests disagree.")
    if not isinstance(probe, AccessibilityProbe):
        raise CageAnalysisInputError("probe must be an AccessibilityProbe.")
    active = resources or CageAccessibilityResources()
    if not isinstance(active, CageAccessibilityResources):
        raise CageAnalysisInputError("resources must be CageAccessibilityResources.")
    ordered_obstacles = tuple(obstacles)
    if len(ordered_obstacles) > active.max_obstacles:
        raise CageAnalysisResourceError("Obstacle count exceeds max_obstacles.")
    if tuple(value.obstacle_id for value in ordered_obstacles) != tuple(range(len(ordered_obstacles))):
        raise CageAnalysisInputError("Obstacle IDs must be dense and ordered.")
    if len(geometry.adjacency_arcs) > active.max_network_arcs:
        raise CageAnalysisResourceError("Adjacency arc count exceeds max_network_arcs.")

    cell = embedding.cell_matrix()
    inverse = np.linalg.inv(cell)
    counter = [0]
    cages: list[CageWitnessAssessment] = []
    for tile in geometry.tiles:
        clearance, obstacle_id = _nearest_periodic_clearance(
            tile.fractional_center,
            ordered_obstacles,
            cell,
            inverse,
            counter,
            active,
        )
        accessible = clearance is None or clearance >= probe.radius
        cages.append(
            CageWitnessAssessment(
                tile.tile_index,
                WitnessAccessibilityStatus.CERTIFIED_ACCESSIBLE_AT_WITNESS
                if accessible
                else WitnessAccessibilityStatus.WITNESS_BLOCKED_UNRESOLVED,
                tile.fractional_center,
                clearance,
                obstacle_id,
            )
        )

    portals: list[PortalWitnessAssessment] = []
    for window in geometry.windows:
        clearance, obstacle_id = _nearest_periodic_clearance(
            window.fractional_center,
            ordered_obstacles,
            cell,
            inverse,
            counter,
            active,
        )
        accessible = (
            window.aperture_witness_radius >= probe.radius
            and (clearance is None or clearance >= probe.radius)
            and cages[window.side_a.tile_index].accessible
            and cages[window.side_b.tile_index].accessible
        )
        portals.append(
            PortalWitnessAssessment(
                window.window_index,
                WitnessAccessibilityStatus.CERTIFIED_ACCESSIBLE_AT_WITNESS
                if accessible
                else WitnessAccessibilityStatus.WITNESS_BLOCKED_UNRESOLVED,
                window.fractional_center,
                window.aperture_witness_radius,
                clearance,
                obstacle_id,
            )
        )

    accessible_arcs = tuple(
        arc.arc_index
        for arc in geometry.adjacency_arcs
        if portals[arc.window_index].accessible
        and cages[arc.source_tile_index].accessible
        and cages[arc.target_tile_index].accessible
    )
    components = _network_components(
        geometry,
        accessible_arcs,
        tuple(cage.tile_index for cage in cages if cage.accessible),
    )
    return CageAccessibilityCatalog(
        geometry.digest,
        embedding.digest,
        probe,
        ordered_obstacles,
        tuple(cages),
        tuple(portals),
        accessible_arcs,
        components,
        counter[0],
    )


__all__ = [
    "AccessibilityProbe",
    "AccessibleNetworkComponent",
    "CAGE_ACCESSIBILITY_DIGEST_ALGORITHM",
    "CANONICAL_CAGE_ACCESSIBILITY_SCHEMA",
    "CageAccessibilityCatalog",
    "CageAccessibilityResources",
    "CageAnalysisError",
    "CageAnalysisInputError",
    "CageAnalysisResourceError",
    "CageAnalysisSerializationError",
    "CageWitnessAssessment",
    "PeriodicObstacleSphere",
    "PortalWitnessAssessment",
    "WitnessAccessibilityStatus",
    "assess_cage_accessibility",
]
