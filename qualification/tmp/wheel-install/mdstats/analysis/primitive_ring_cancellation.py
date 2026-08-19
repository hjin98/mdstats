"""Exact finite GF(2) cancellation of translated primitive-ring edge support.

This module implements the Stage-5 P3 consumer prototype. It does not classify
rings as globally strong or weak and does not enumerate a strength-search domain.
Instead it answers one exact finite question: whether the physical lifted-edge
support of a target ``RingPlacement`` lies in the GF(2) span of an explicitly
supplied finite set of strictly smaller translated primitive-ring placements.

The strong-ring concept -- a ring that cannot be written as a sum/symmetric
-difference of smaller rings -- follows Goetzke & Klein (1991) and is discussed
in detail by Yuan & Cormack (2002). mdstats adapts that concept to periodic
framework graphs by using complete source-bound ``LiftedEdgeInstanceRef`` records
as basis elements, so translated instances of one quotient-edge orbit never
cancel unless they are the same physical edge.

References
----------
K. Goetzke and H.-J. Klein, J. Non-Cryst. Solids 127, 215-220 (1991),
doi:10.1016/0022-3093(91)90145-V.
X. Yuan and A. N. Cormack, Comput. Mater. Sci. 24, 343-360 (2002),
doi:10.1016/S0927-0256(01)00256-7.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from numbers import Integral
from typing import Any, Iterable

from .periodic_cycle import RingPlacement
from .primitive_ring import PrimitiveRingKey
from .primitive_ring_index import (
    LiftedEdgeInstanceRef,
    PrimitiveRingIndex,
    PrimitiveRingIndexInputError,
)


class PrimitiveRingCancellationError(ValueError):
    """Base exception for finite primitive-ring support cancellation."""


class PrimitiveRingCancellationInputError(PrimitiveRingCancellationError):
    """Raised when target/candidate placement input is invalid."""


class PrimitiveRingCancellationInvariantError(PrimitiveRingCancellationError):
    """Raised when an internal/source support invariant is violated."""


class PrimitiveRingCancellationResourceError(PrimitiveRingCancellationError):
    """Raised when the finite GF(2) solve exceeds an explicit memory bound."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class FiniteRingCancellationStatus(str, Enum):
    """Exact outcome for one explicitly supplied finite candidate span."""

    DECOMPOSITION_FOUND = "decomposition_found"
    NOT_IN_SUPPLIED_SPAN = "not_in_supplied_span"





def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise PrimitiveRingCancellationInputError(
            f"{name} must be a positive integer."
        )
    return int(value)


@dataclass(frozen=True, slots=True)
class FiniteRingCancellationResources:
    """Conservative bit-capacity limits for the temporary GF(2) workspace."""

    max_matrix_bits: int = 536_870_912
    max_provenance_bits: int = 268_435_456

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_matrix_bits",
            _positive_int(self.max_matrix_bits, name="max_matrix_bits"),
        )
        object.__setattr__(
            self,
            "max_provenance_bits",
            _positive_int(self.max_provenance_bits, name="max_provenance_bits"),
        )


@dataclass(frozen=True, order=True, slots=True)
class RingPlacementSupport:
    """Exact physical lifted-edge support of one translated primitive ring."""

    placement: RingPlacement
    edge_instances: tuple[LiftedEdgeInstanceRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.placement, RingPlacement):
            raise PrimitiveRingCancellationInputError(
                "placement must be a RingPlacement."
            )
        edges = tuple(self.edge_instances)
        if any(not isinstance(edge, LiftedEdgeInstanceRef) for edge in edges):
            raise PrimitiveRingCancellationInputError(
                "edge_instances must contain LiftedEdgeInstanceRef records."
            )
        if edges != tuple(sorted(edges)):
            raise PrimitiveRingCancellationInputError(
                "edge_instances must be sorted deterministically."
            )
        if len(set(edges)) != len(edges):
            raise PrimitiveRingCancellationInvariantError(
                "A lifted-simple ring support cannot contain one physical edge instance twice."
            )
        object.__setattr__(self, "edge_instances", edges)


@dataclass(frozen=True, slots=True)
class RingCancellationWitness:
    """One exact finite decomposition witness for a target placement."""

    target_placement: RingPlacement
    component_placements: tuple[RingPlacement, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.target_placement, RingPlacement):
            raise PrimitiveRingCancellationInputError(
                "target_placement must be a RingPlacement."
            )
        components = tuple(self.component_placements)
        if not components:
            raise PrimitiveRingCancellationInputError(
                "component_placements must contain at least one placement."
            )
        if any(not isinstance(item, RingPlacement) for item in components):
            raise PrimitiveRingCancellationInputError(
                "component_placements must contain RingPlacement records."
            )
        if components != tuple(sorted(components)) or len(set(components)) != len(
            components
        ):
            raise PrimitiveRingCancellationInputError(
                "component_placements must be sorted and unique."
            )
        if any(
            item.topology_graph_digest != self.target_placement.topology_graph_digest
            for item in components
        ):
            raise PrimitiveRingCancellationInputError(
                "component_placements must share the target topology graph digest."
            )
        object.__setattr__(self, "component_placements", components)


@dataclass(frozen=True, slots=True)
class FiniteRingCancellationResult:
    """Exact result relative to one supplied finite set of smaller placements."""

    topology_graph_digest: str
    target_placement: RingPlacement
    candidate_placements: tuple[RingPlacement, ...]
    status: FiniteRingCancellationStatus
    witness: RingCancellationWitness | None

    def __post_init__(self) -> None:
        if not isinstance(self.topology_graph_digest, str) or not self.topology_graph_digest:
            raise PrimitiveRingCancellationInputError(
                "topology_graph_digest must be a nonempty string."
            )
        if not isinstance(self.target_placement, RingPlacement):
            raise PrimitiveRingCancellationInputError(
                "target_placement must be a RingPlacement."
            )
        if self.target_placement.topology_graph_digest != self.topology_graph_digest:
            raise PrimitiveRingCancellationInputError(
                "target_placement topology digest does not match result source."
            )
        candidates = tuple(self.candidate_placements)
        if any(not isinstance(item, RingPlacement) for item in candidates):
            raise PrimitiveRingCancellationInputError(
                "candidate_placements must contain RingPlacement records."
            )
        if candidates != tuple(sorted(candidates)) or len(set(candidates)) != len(
            candidates
        ):
            raise PrimitiveRingCancellationInputError(
                "candidate_placements must be sorted and unique."
            )
        if any(
            item.topology_graph_digest != self.topology_graph_digest
            for item in candidates
        ):
            raise PrimitiveRingCancellationInputError(
                "candidate_placements must share the result topology graph digest."
            )
        if not isinstance(self.status, FiniteRingCancellationStatus):
            raise PrimitiveRingCancellationInputError(
                "status must be a FiniteRingCancellationStatus."
            )
        if self.status is FiniteRingCancellationStatus.DECOMPOSITION_FOUND:
            if not isinstance(self.witness, RingCancellationWitness):
                raise PrimitiveRingCancellationInputError(
                    "DECOMPOSITION_FOUND requires a RingCancellationWitness."
                )
            if self.witness.target_placement != self.target_placement:
                raise PrimitiveRingCancellationInputError(
                    "Witness target does not match result target."
                )
            if not set(self.witness.component_placements).issubset(candidates):
                raise PrimitiveRingCancellationInputError(
                    "Witness components must be drawn from candidate_placements."
                )
        elif self.witness is not None:
            raise PrimitiveRingCancellationInputError(
                "NOT_IN_SUPPLIED_SPAN requires witness=None."
            )
        object.__setattr__(self, "candidate_placements", candidates)


def _resolve_ring_size(index: PrimitiveRingIndex, key: PrimitiveRingKey) -> int:
    try:
        return index.ring_for_key(key).size
    except PrimitiveRingIndexInputError as exc:
        raise PrimitiveRingCancellationInputError(str(exc)) from exc


def ring_placement_support(
    index: PrimitiveRingIndex,
    placement: RingPlacement,
) -> RingPlacementSupport:
    """Return exact physical lifted-edge support for one translated ring.

    The support basis uses complete ``LiftedEdgeInstanceRef`` records. This is
    the periodic adaptation required by the strong-ring sum/symmetric-difference
    concept of Goetzke & Klein (1991) / Yuan & Cormack (2002): quotient-equivalent
    edge orbits at different lattice anchors are different physical basis elements.
    """
    if not isinstance(index, PrimitiveRingIndex):
        raise PrimitiveRingCancellationInputError(
            "index must be a PrimitiveRingIndex."
        )
    if not isinstance(placement, RingPlacement):
        raise PrimitiveRingCancellationInputError(
            "placement must be a RingPlacement."
        )

    if placement.topology_graph_digest != index.topology_graph_digest:
        raise PrimitiveRingCancellationInputError(
            "RingPlacement belongs to a different topology graph digest."
        )
    try:
        ring = index.ring_for_key(placement.ring_key)
        edges = tuple(sorted(index.translated_edge_instances(placement)))
    except PrimitiveRingIndexInputError as exc:
        raise PrimitiveRingCancellationInputError(str(exc)) from exc
    if len(edges) != ring.size:
        raise PrimitiveRingCancellationInvariantError(
            "Ring support cardinality disagrees with source ring size."
        )
    if len(set(edges)) != len(edges):
        raise PrimitiveRingCancellationInvariantError(
            "Source ring reuses one exact physical edge instance; lifted-simple support expected."
        )
    return RingPlacementSupport(placement=placement, edge_instances=edges)


def _support_bits(
    support: RingPlacementSupport,
    positions: dict[LiftedEdgeInstanceRef, int],
) -> int:
    bits = 0
    for edge in support.edge_instances:
        bits |= 1 << positions[edge]
    return bits


def _reduce_with_basis(
    vector: int,
    combination: int,
    basis: dict[int, tuple[int, int]],
) -> tuple[int, int]:
    while vector:
        pivot = vector.bit_length() - 1
        row = basis.get(pivot)
        if row is None:
            break
        vector ^= row[0]
        combination ^= row[1]
    return vector, combination


def _verify_witness(
    target: RingPlacementSupport,
    components: tuple[RingPlacementSupport, ...],
) -> None:
    parity: set[LiftedEdgeInstanceRef] = set(target.edge_instances)
    for component in components:
        for edge in component.edge_instances:
            if edge in parity:
                parity.remove(edge)
            else:
                parity.add(edge)
    if parity:
        raise PrimitiveRingCancellationInvariantError(
            "Internal GF(2) witness failed exact physical-edge cancellation verification."
        )


def solve_finite_ring_cancellation(
    index: PrimitiveRingIndex,
    target_placement: RingPlacement,
    candidate_placements: Iterable[RingPlacement],
    *,
    resources: FiniteRingCancellationResources | None = None,
) -> FiniteRingCancellationResult:
    """Solve exact finite smaller-ring cancellation over GF(2).

    This function is exhaustive only over the explicitly supplied finite candidate
    set. ``NOT_IN_SUPPLIED_SPAN`` is therefore *not* a strong-ring classification.
    A later strength stage must separately prove candidate-domain completeness.

    The strong-ring sum concept follows Goetzke & Klein (1991) and Yuan & Cormack
    (2002). The finite membership calculation itself is standard Gaussian
    elimination over GF(2), implemented with temporary Python integer bitsets.
    """
    if not isinstance(index, PrimitiveRingIndex):
        raise PrimitiveRingCancellationInputError(
            "index must be a PrimitiveRingIndex."
        )
    if not isinstance(target_placement, RingPlacement):
        raise PrimitiveRingCancellationInputError(
            "target_placement must be a RingPlacement."
        )
    if target_placement.topology_graph_digest != index.topology_graph_digest:
        raise PrimitiveRingCancellationInputError(
            "target_placement belongs to a different topology graph digest."
        )
    policy = resources or FiniteRingCancellationResources()
    if not isinstance(policy, FiniteRingCancellationResources):
        raise PrimitiveRingCancellationInputError(
            "resources must be a FiniteRingCancellationResources record."
        )

    try:
        raw_candidates = tuple(candidate_placements)
    except TypeError as exc:
        raise PrimitiveRingCancellationInputError(
            "candidate_placements must be an iterable of RingPlacement records."
        ) from exc
    if any(not isinstance(item, RingPlacement) for item in raw_candidates):
        raise PrimitiveRingCancellationInputError(
            "candidate_placements must contain RingPlacement records."
        )
    if len(set(raw_candidates)) != len(raw_candidates):
        raise PrimitiveRingCancellationInputError(
            "candidate_placements must not contain duplicate exact placements."
        )
    if any(
        item.topology_graph_digest != index.topology_graph_digest
        for item in raw_candidates
    ):
        raise PrimitiveRingCancellationInputError(
            "candidate_placements belong to a different topology graph digest."
        )
    candidates = tuple(sorted(raw_candidates))

    target_size = _resolve_ring_size(index, target_placement.ring_key)
    for candidate in candidates:
        candidate_size = _resolve_ring_size(index, candidate.ring_key)
        if candidate_size >= target_size:
            raise PrimitiveRingCancellationInputError(
                "Every candidate ring must be strictly smaller than the target ring."
            )

    target_support = ring_placement_support(index, target_placement)
    candidate_supports = tuple(
        ring_placement_support(index, placement) for placement in candidates
    )

    edge_universe = tuple(
        sorted(
            {
                edge
                for support in (target_support, *candidate_supports)
                for edge in support.edge_instances
            }
        )
    )
    edge_count = len(edge_universe)
    candidate_count = len(candidate_supports)
    matrix_bits = candidate_count * max(1, edge_count)
    provenance_bits = min(candidate_count, edge_count) * candidate_count
    if matrix_bits > policy.max_matrix_bits:
        raise PrimitiveRingCancellationResourceError(
            "max_matrix_bits exceeded during GF(2) elimination"
        )
    if provenance_bits > policy.max_provenance_bits:
        raise PrimitiveRingCancellationResourceError(
            "max_provenance_bits exceeded during GF(2) elimination"
        )

    positions = {edge: position for position, edge in enumerate(edge_universe)}
    target_bits = _support_bits(target_support, positions)
    candidate_bits = tuple(
        _support_bits(support, positions) for support in candidate_supports
    )

    basis: dict[int, tuple[int, int]] = {}
    for candidate_index, vector in enumerate(candidate_bits):
        reduced, combination = _reduce_with_basis(
            vector,
            1 << candidate_index,
            basis,
        )
        if reduced:
            pivot = reduced.bit_length() - 1
            basis[pivot] = (reduced, combination)

    remainder, witness_mask = _reduce_with_basis(target_bits, 0, basis)
    if remainder:
        return FiniteRingCancellationResult(
            topology_graph_digest=index.topology_graph_digest,
            target_placement=target_placement,
            candidate_placements=candidates,
            status=FiniteRingCancellationStatus.NOT_IN_SUPPLIED_SPAN,
            witness=None,
        )

    component_supports = tuple(
        support
        for candidate_index, support in enumerate(candidate_supports)
        if witness_mask & (1 << candidate_index)
    )
    if not component_supports:
        raise PrimitiveRingCancellationInvariantError(
            "Nonempty primitive-ring target reduced to the empty candidate combination."
        )
    _verify_witness(target_support, component_supports)
    component_placements = tuple(sorted(item.placement for item in component_supports))
    witness = RingCancellationWitness(
        target_placement=target_placement,
        component_placements=component_placements,
    )
    return FiniteRingCancellationResult(
        topology_graph_digest=index.topology_graph_digest,
        target_placement=target_placement,
        candidate_placements=candidates,
        status=FiniteRingCancellationStatus.DECOMPOSITION_FOUND,
        witness=witness,
    )


__all__ = [
    "FiniteRingCancellationResources",
    "FiniteRingCancellationResult",
    "FiniteRingCancellationStatus",
    "PrimitiveRingCancellationError",
    "PrimitiveRingCancellationInputError",
    "PrimitiveRingCancellationInvariantError",
    "PrimitiveRingCancellationResourceError",
    "RingCancellationWitness",
    "RingPlacementSupport",
    "ring_placement_support",
    "solve_finite_ring_cancellation",
]
