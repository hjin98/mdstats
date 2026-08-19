"""Transient exact placement index for canonical primitive-ring catalogs.

Periodic framework edges are represented as quotient-graph edge orbits carrying
integer lattice translations. This follows the vector/quotient-graph viewpoint
of Chung, Hahn, and Klee (1984) and Klee (2004). mdstats adapts that representation
here to source-bound physical edge instances and exact translated primitive-ring
placements without creating a second scientific ring catalog.

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
W. E. Klee, Cryst. Res. Technol. 39, 959-968 (2004),
doi:10.1002/crat.200410281.
"""

from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass, field
from typing import Literal

from ._periodic_graph import (
    add_shift,
    coerce_lattice_shift,
    coerce_nonnegative_int,
    physical_edge_anchor,
    subtract_shift,
)
from .framework_topology import FrameworkEdgeKey
from .periodic_cycle import RingPlacement
from .primitive_ring import (
    LatticeShift,
    PrimitiveRing,
    PrimitiveRingCatalog,
    PrimitiveRingKey,
)


class PrimitiveRingIndexError(ValueError):
    """Base exception for primitive-ring index and placement operations."""


class PrimitiveRingIndexInputError(PrimitiveRingIndexError):
    """Raised when a source catalog, key, edge instance, or index is invalid."""


def _nonnegative(value: object, *, name: str) -> int:
    try:
        return coerce_nonnegative_int(value, name=name)
    except ValueError as exc:
        raise PrimitiveRingIndexInputError(str(exc)) from exc


def _shift(value: object, *, name: str) -> LatticeShift:
    try:
        return coerce_lattice_shift(value, name=name)
    except ValueError as exc:
        raise PrimitiveRingIndexInputError(str(exc)) from exc


def _digest(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PrimitiveRingIndexInputError(f"{name} must be a nonempty string.")
    return value


@dataclass(frozen=True, order=True, slots=True)
class LiftedEdgeInstanceRef:
    """One exact translated instance of one source framework-edge orbit.

    ``edge_key`` is the stable decorated quotient-edge identity. ``anchor_shift``
    is the lattice image of its canonical ``vertex_i`` endpoint. The topology
    digest prevents a structurally similar key from being silently interpreted
    against another source graph.
    """

    topology_graph_digest: str
    edge_key: FrameworkEdgeKey
    anchor_shift: LatticeShift

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "topology_graph_digest",
            _digest(self.topology_graph_digest, name="topology_graph_digest"),
        )
        if not isinstance(self.edge_key, FrameworkEdgeKey):
            raise PrimitiveRingIndexInputError("edge_key must be a FrameworkEdgeKey.")
        object.__setattr__(
            self,
            "anchor_shift",
            _shift(self.anchor_shift, name="anchor_shift"),
        )


@dataclass(frozen=True, order=True, slots=True)
class _PrimitiveRingEdgeOccurrence:
    """Internal source-catalog occurrence of one quotient edge in one ring."""

    ring_key: PrimitiveRingKey
    step_index: int
    edge_index: int
    orientation: Literal[-1, 1]
    canonical_anchor_shift: LatticeShift

    def __post_init__(self) -> None:
        if not isinstance(self.ring_key, PrimitiveRingKey):
            raise PrimitiveRingIndexInputError("ring_key must be a PrimitiveRingKey.")
        object.__setattr__(self, "step_index", _nonnegative(self.step_index, name="step_index"))
        object.__setattr__(self, "edge_index", _nonnegative(self.edge_index, name="edge_index"))
        if self.orientation not in (-1, 1):
            raise PrimitiveRingIndexInputError("orientation must be +1 or -1.")
        object.__setattr__(
            self,
            "canonical_anchor_shift",
            _shift(self.canonical_anchor_shift, name="canonical_anchor_shift"),
        )


@dataclass(frozen=True, order=True, slots=True)
class RingEdgePlacement:
    """A translated ring placement aligned to one requested physical edge instance."""

    placement: RingPlacement
    step_index: int
    orientation: Literal[-1, 1]

    def __post_init__(self) -> None:
        if not isinstance(self.placement, RingPlacement):
            raise PrimitiveRingIndexInputError("placement must be a RingPlacement.")
        object.__setattr__(self, "step_index", _nonnegative(self.step_index, name="step_index"))
        if self.orientation not in (-1, 1):
            raise PrimitiveRingIndexInputError("orientation must be +1 or -1.")


def _canonical_edge_instance_for_step(
    catalog: PrimitiveRingCatalog,
    ring: PrimitiveRing,
    step_index: int,
) -> LiftedEdgeInstanceRef:
    if step_index < 0 or step_index >= ring.size:
        raise PrimitiveRingIndexInputError(
            f"step_index={step_index} is outside ring size {ring.size}."
        )
    step = ring.steps[step_index]
    source = ring.vertex_walk[step_index]
    try:
        edge_key = catalog.edge_searches[step.edge_index].edge_key
    except IndexError as exc:
        raise PrimitiveRingIndexInputError(
            "Ring step references an edge outside the source catalog."
        ) from exc

    # Chung-Hahn-Klee vector-method convention: edge orbit (i,j,Delta)
    # translated by anchor a is physical edge (i,a)->(j,a+Delta). Reverse
    # traversal starts at (j,a+Delta), so its canonical anchor is source-Delta.
    anchor = physical_edge_anchor(
        source.image_shift,
        edge_key.image_shift,
        step.orientation,
    )
    return LiftedEdgeInstanceRef(catalog.topology_graph_digest, edge_key, anchor)


def _build_edge_occurrences(
    catalog: PrimitiveRingCatalog,
) -> tuple[tuple[_PrimitiveRingEdgeOccurrence, ...], ...]:
    buckets: list[list[_PrimitiveRingEdgeOccurrence]] = [
        [] for _ in catalog.edge_searches
    ]
    for ring in catalog.rings:
        for step_index, step in enumerate(ring.steps):
            edge_instance = _canonical_edge_instance_for_step(catalog, ring, step_index)
            buckets[step.edge_index].append(
                _PrimitiveRingEdgeOccurrence(
                    ring_key=ring.key,
                    step_index=step_index,
                    edge_index=step.edge_index,
                    orientation=step.orientation,
                    canonical_anchor_shift=edge_instance.anchor_shift,
                )
            )
    return tuple(tuple(sorted(bucket)) for bucket in buckets)


@dataclass(frozen=True, slots=True)
class PrimitiveRingIndex:
    """Immutable transient occurrence index bound to one primitive-ring catalog.

    The source catalog remains the sole scientific ring result. This index adds
    stable-key lookup, exact canonical physical-edge support, and occurrence-level
    inverse incidence needed by translated placement, automorphism, and GF(2)
    consumers.
    """

    catalog: PrimitiveRingCatalog = field(repr=False, compare=False)
    ring_keys: tuple[PrimitiveRingKey, ...]
    _edge_keys: tuple[FrameworkEdgeKey, ...]
    _edge_to_occurrences: tuple[tuple[_PrimitiveRingEdgeOccurrence, ...], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.catalog, PrimitiveRingCatalog):
            raise PrimitiveRingIndexInputError("catalog must be a PrimitiveRingCatalog.")
        keys = tuple(self.ring_keys)
        expected_keys = tuple(ring.key for ring in self.catalog.rings)
        if keys != expected_keys:
            raise PrimitiveRingIndexInputError(
                "ring_keys must align exactly with the source catalog ring order."
            )
        if keys != tuple(sorted(keys)) or len(set(keys)) != len(keys):
            raise PrimitiveRingIndexInputError("ring_keys must be sorted and unique.")

        edge_keys = tuple(self._edge_keys)
        expected_edge_keys = tuple(search.edge_key for search in self.catalog.edge_searches)
        if edge_keys != expected_edge_keys:
            raise PrimitiveRingIndexInputError(
                "edge_keys must align exactly with the source catalog edge order."
            )
        if edge_keys != tuple(sorted(edge_keys)) or len(set(edge_keys)) != len(edge_keys):
            raise PrimitiveRingIndexInputError("edge_keys must be sorted and unique.")

        occurrences = tuple(tuple(bucket) for bucket in self._edge_to_occurrences)
        expected_occurrences = _build_edge_occurrences(self.catalog)
        if occurrences != expected_occurrences:
            raise PrimitiveRingIndexInputError(
                "edge_to_occurrences is inconsistent with the source catalog."
            )
        object.__setattr__(self, "ring_keys", keys)
        object.__setattr__(self, "_edge_keys", edge_keys)
        object.__setattr__(self, "_edge_to_occurrences", occurrences)

    @property
    def catalog_digest(self) -> str:
        return self.catalog.digest

    @property
    def topology_graph_digest(self) -> str:
        return self.catalog.topology_graph_digest

    @property
    def source_complete_for_ring_sizes_up_to(self) -> int:
        return self.catalog.complete_for_ring_sizes_up_to

    @property
    def source_search_completed_without_resource_truncation(self) -> bool:
        return self.catalog.search_completed_without_resource_truncation

    @property
    def edge_count(self) -> int:
        """Number of source framework edge orbits indexed."""
        return len(self._edge_keys)

    @property
    def occurrence_count(self) -> int:
        """Total canonical ring-step occurrences represented by the index."""
        return sum(len(bucket) for bucket in self._edge_to_occurrences)

    def _validate_placement_source(self, placement: RingPlacement) -> None:
        if not isinstance(placement, RingPlacement):
            raise PrimitiveRingIndexInputError("placement must be a RingPlacement.")
        if placement.topology_graph_digest != self.topology_graph_digest:
            raise PrimitiveRingIndexInputError(
                "RingPlacement belongs to a different topology graph digest."
            )

    def ring_id_for_key(self, key: PrimitiveRingKey) -> int:
        if not isinstance(key, PrimitiveRingKey):
            raise PrimitiveRingIndexInputError("key must be a PrimitiveRingKey.")
        position = bisect_left(self.ring_keys, key)
        if position >= len(self.ring_keys) or self.ring_keys[position] != key:
            raise PrimitiveRingIndexInputError(
                "PrimitiveRingKey is absent from the source catalog."
            )
        return position

    def ring_for_key(self, key: PrimitiveRingKey) -> PrimitiveRing:
        return self.catalog.rings[self.ring_id_for_key(key)]

    def edge_index_for_key(self, key: FrameworkEdgeKey) -> int:
        if not isinstance(key, FrameworkEdgeKey):
            raise PrimitiveRingIndexInputError("key must be a FrameworkEdgeKey.")
        position = bisect_left(self._edge_keys, key)
        if position >= len(self._edge_keys) or self._edge_keys[position] != key:
            raise PrimitiveRingIndexInputError(
                "FrameworkEdgeKey is absent from the source catalog."
            )
        return position

    def edge_key_for_index(self, edge_index: int) -> FrameworkEdgeKey:
        index = _nonnegative(edge_index, name="edge_index")
        if index >= len(self._edge_keys):
            raise PrimitiveRingIndexInputError(
                f"edge_index={index} is outside the source catalog."
            )
        return self._edge_keys[index]

    def canonical_edge_instance(
        self,
        key: PrimitiveRingKey,
        step_index: int,
    ) -> LiftedEdgeInstanceRef:
        ring = self.ring_for_key(key)
        return _canonical_edge_instance_for_step(
            self.catalog,
            ring,
            _nonnegative(step_index, name="step_index"),
        )

    def canonical_edge_instances(
        self,
        key: PrimitiveRingKey,
    ) -> tuple[LiftedEdgeInstanceRef, ...]:
        """Return ordered exact physical-edge support of the canonical representative."""
        ring = self.ring_for_key(key)
        return tuple(
            _canonical_edge_instance_for_step(self.catalog, ring, step_index)
            for step_index in range(ring.size)
        )

    def translated_edge_instances(
        self,
        placement: RingPlacement,
    ) -> tuple[LiftedEdgeInstanceRef, ...]:
        """Return ordered exact physical-edge support of one source-bound placement."""
        self._validate_placement_source(placement)
        return tuple(
            LiftedEdgeInstanceRef(
                self.topology_graph_digest,
                edge.edge_key,
                add_shift(edge.anchor_shift, placement.image_shift),
            )
            for edge in self.canonical_edge_instances(placement.ring_key)
        )


def build_primitive_ring_index(catalog: PrimitiveRingCatalog) -> PrimitiveRingIndex:
    """Build a deterministic transient occurrence index for one ring catalog."""
    if not isinstance(catalog, PrimitiveRingCatalog):
        raise PrimitiveRingIndexInputError("catalog must be a PrimitiveRingCatalog.")
    return PrimitiveRingIndex(
        catalog=catalog,
        ring_keys=tuple(ring.key for ring in catalog.rings),
        _edge_keys=tuple(search.edge_key for search in catalog.edge_searches),
        _edge_to_occurrences=_build_edge_occurrences(catalog),
    )


def ring_placements_covering_edge(
    index: PrimitiveRingIndex,
    edge_instance: LiftedEdgeInstanceRef,
) -> tuple[RingEdgePlacement, ...]:
    """Return every represented translated ring occurrence covering an exact edge."""
    if not isinstance(index, PrimitiveRingIndex):
        raise PrimitiveRingIndexInputError("index must be a PrimitiveRingIndex.")
    if not isinstance(edge_instance, LiftedEdgeInstanceRef):
        raise PrimitiveRingIndexInputError(
            "edge_instance must be a LiftedEdgeInstanceRef."
        )
    if edge_instance.topology_graph_digest != index.topology_graph_digest:
        raise PrimitiveRingIndexInputError(
            "LiftedEdgeInstanceRef belongs to a different topology graph digest."
        )
    edge_index = index.edge_index_for_key(edge_instance.edge_key)

    placements = tuple(
        RingEdgePlacement(
            placement=RingPlacement(
                topology_graph_digest=index.topology_graph_digest,
                ring_key=occurrence.ring_key,
                image_shift=subtract_shift(
                    edge_instance.anchor_shift,
                    occurrence.canonical_anchor_shift,
                ),
            ),
            step_index=occurrence.step_index,
            orientation=occurrence.orientation,
        )
        for occurrence in index._edge_to_occurrences[edge_index]
    )
    if len(set(placements)) != len(placements):
        raise PrimitiveRingIndexError(
            "Source catalog produced duplicate exact ring-edge placements."
        )
    return tuple(sorted(placements))


__all__ = [
    "LiftedEdgeInstanceRef",
    "PrimitiveRingIndex",
    "PrimitiveRingIndexError",
    "PrimitiveRingIndexInputError",
    "RingEdgePlacement",
    "build_primitive_ring_index",
    "ring_placements_covering_edge",
]
