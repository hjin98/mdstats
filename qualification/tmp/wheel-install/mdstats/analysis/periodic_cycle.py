"""Source-bound placement and parametrization records for periodic cycles.

This module separates physical placement from boundary parametrization.  A
``RingPlacement`` identifies one translated copy of a canonical primitive-ring
representative.  ``CycleParameterization`` only describes where and in which
orientation that same boundary is traversed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ._periodic_graph import coerce_lattice_shift, coerce_nonnegative_int
from .primitive_ring import LatticeShift, PrimitiveRingKey


class PeriodicCycleInputError(ValueError):
    """Raised when a periodic-cycle identity or parametrization is malformed."""


def _digest(value: str, *, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise PeriodicCycleInputError(f"{name} must be a nonempty string.")
    return value


@dataclass(frozen=True, order=True, slots=True)
class RingPlacement:
    """One exact lattice translation of one canonical primitive-ring representative.

    ``topology_graph_digest`` source-binds the otherwise source-local
    ``PrimitiveRingKey`` and prevents accidental interpretation against another
    framework topology.
    """

    topology_graph_digest: str
    ring_key: PrimitiveRingKey
    image_shift: LatticeShift

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "topology_graph_digest",
            _digest(self.topology_graph_digest, name="topology_graph_digest"),
        )
        if not isinstance(self.ring_key, PrimitiveRingKey):
            raise PeriodicCycleInputError("ring_key must be a PrimitiveRingKey.")
        try:
            shift = coerce_lattice_shift(self.image_shift, name="image_shift")
        except ValueError as exc:
            raise PeriodicCycleInputError(str(exc)) from exc
        object.__setattr__(self, "image_shift", shift)


@dataclass(frozen=True, order=True, slots=True)
class CycleParameterization:
    """Traversal convention on one n-cycle, independent of physical placement.

    For cycle length ``n`` and source position ``k``:

    ``p_V(k) = c + epsilon*k (mod n)``

    while edge-step positions are ``c+k`` for ``epsilon=+1`` and
    ``c-k-1`` for ``epsilon=-1``.
    """

    start_vertex_index: int = 0
    orientation: Literal[-1, 1] = 1

    def __post_init__(self) -> None:
        try:
            start = coerce_nonnegative_int(
                self.start_vertex_index, name="start_vertex_index"
            )
        except ValueError as exc:
            raise PeriodicCycleInputError(str(exc)) from exc
        if self.orientation not in (-1, 1):
            raise PeriodicCycleInputError("orientation must be +1 or -1.")
        object.__setattr__(self, "start_vertex_index", start)

    def vertex_permutation(self, size: int) -> tuple[int, ...]:
        try:
            n = coerce_nonnegative_int(size, name="size")
        except ValueError as exc:
            raise PeriodicCycleInputError(str(exc)) from exc
        if n == 0 or self.start_vertex_index >= n:
            raise PeriodicCycleInputError(
                "size must be positive and start_vertex_index must lie inside the cycle."
            )
        return tuple(
            (self.start_vertex_index + self.orientation * k) % n for k in range(n)
        )

    def step_permutation(self, size: int) -> tuple[int, ...]:
        try:
            n = coerce_nonnegative_int(size, name="size")
        except ValueError as exc:
            raise PeriodicCycleInputError(str(exc)) from exc
        if n == 0 or self.start_vertex_index >= n:
            raise PeriodicCycleInputError(
                "size must be positive and start_vertex_index must lie inside the cycle."
            )
        c = self.start_vertex_index
        if self.orientation == 1:
            return tuple((c + k) % n for k in range(n))
        return tuple((c - k - 1) % n for k in range(n))


__all__ = [
    "CycleParameterization",
    "PeriodicCycleInputError",
    "RingPlacement",
]
