"""Deterministic primitive-ring enumeration on periodic framework topologies.

The default algorithm constructs bounded primitive/no-shortcut cycles from
pairs of tied shortest half-paths. Even candidates join two internally disjoint
shortest paths between exact lifted antipodes; odd candidates join two shortest
root paths to adjacent lifted endpoints. A bounded lifted shortest-path index
then verifies the remaining maximal half-cycle pairs.

This construction follows the shortest-path candidate ideas of Horton (1987)
and Vismara (1997), combined with the primitive/no-shortcut ring definition used
by Goetzke and Klein (1991) and the efficient primitive-ring treatment of Yuan
and Cormack (2002). The periodic lifted-state model, decorated multigraph edge
identity, transactional resource limits, and deterministic serialization are
mdstats-specific adaptations.

The earlier removed-edge shortest-closure algorithm remains available as an
explicit secondary method. Its output is an edge-shortest subset and must not be
interpreted as a complete primitive-ring catalog.

References
----------
J. D. Horton, SIAM J. Comput. 16, 358-366 (1987), doi:10.1137/0216026.
P. Vismara, Electron. J. Combin. 4, R9 (1997), doi:10.37236/1294.
K. Goetzke and H.-J. Klein, J. Non-Cryst. Solids 127, 215-220 (1991).
X. Yuan and A. N. Cormack, Comput. Mater. Sci. 24, 343-360 (2002).
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal, TypeAlias

from .framework_topology import FrameworkEdgeKey, FrameworkTopology

LatticeShift: TypeAlias = tuple[int, int, int]

CANONICAL_PRIMITIVE_RING_SCHEMA = "mdstats.primitive-ring.v2"
LEGACY_PRIMITIVE_RING_SCHEMA = "mdstats.primitive-ring.v1"
PRIMITIVE_RING_ALGORITHM_VERSION = "shortest-path-pairs-v1"
PRIMITIVE_RING_DIGEST_ALGORITHM = "sha256"

_ZERO_SHIFT: LatticeShift = (0, 0, 0)


class PrimitiveRingSearchMethod(str, Enum):
    """Algorithm used to generate the cataloged ring family."""

    SHORTEST_PATH_PAIRS = "shortest_path_pairs"
    REMOVED_EDGE_SHORTEST = "removed_edge_shortest"


class PrimitiveRingFamily(str, Enum):
    """Mathematical family represented by a primitive-ring catalog."""

    PRIMITIVE_NO_SHORTCUT = "primitive_no_shortcut"
    EDGE_SHORTEST_SUBSET = "edge_shortest_subset"


class PrimitiveRingError(ValueError):
    """Base exception for primitive-ring operations."""


class PrimitiveRingInputError(PrimitiveRingError):
    """Raised when topology, options, or public records are invalid."""


class PrimitiveRingSearchError(PrimitiveRingError):
    """Raised when a lifted-graph search invariant is violated."""


class PrimitiveRingComplexityError(PrimitiveRingSearchError):
    """Raised when strict resource limits terminate enumeration."""


class PrimitiveRingSerializationError(PrimitiveRingError):
    """Raised when serialized primitive-ring state is malformed."""


def _coerce_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        try:
            import numpy as np

            if not isinstance(value, np.integer):
                raise TypeError
        except (ImportError, TypeError) as exc:
            raise PrimitiveRingInputError(f"{name} must be an integer.") from exc
    return int(value)


def _nonnegative_int(value: Any, *, name: str) -> int:
    result = _coerce_int(value, name=name)
    if result < 0:
        raise PrimitiveRingInputError(f"{name} must be nonnegative.")
    return result


def _positive_int(value: Any, *, name: str) -> int:
    result = _coerce_int(value, name=name)
    if result <= 0:
        raise PrimitiveRingInputError(f"{name} must be positive.")
    return result


def _shift(value: Sequence[int], *, name: str = "lattice shift") -> LatticeShift:
    if len(value) != 3:
        raise PrimitiveRingInputError(f"{name} must contain exactly three integers.")
    return tuple(_coerce_int(x, name=name) for x in value)  # type: ignore[return-value]


def _add_shift(left: LatticeShift, right: LatticeShift) -> LatticeShift:
    return tuple(a + b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def _sub_shift(left: LatticeShift, right: LatticeShift) -> LatticeShift:
    return tuple(a - b for a, b in zip(left, right, strict=True))  # type: ignore[return-value]


def _neg_shift(value: LatticeShift) -> LatticeShift:
    return tuple(-x for x in value)  # type: ignore[return-value]


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def primitive_ring_catalog_digest(payload: Mapping[str, object]) -> str:
    """Return the canonical SHA-256 digest of a primitive-ring payload."""
    clean = dict(payload)
    clean.pop("digest", None)
    return hashlib.sha256(_canonical_json(clean).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class PrimitiveRingOptions:
    """Bounded search and complexity policy for primitive-ring enumeration.

    The ``*_per_edge`` and ``strict_resource_limits`` fields are deprecated v1
    constructor aliases retained for source compatibility. New code should use
    the source/target terminology and ``strict``.
    """

    method: PrimitiveRingSearchMethod = PrimitiveRingSearchMethod.SHORTEST_PATH_PAIRS
    min_ring_size: int = 2
    max_ring_size: int = 12
    max_lifted_states_per_source: int = 250_000
    max_shortest_paths_per_target: int = 100_000
    max_path_pair_combinations_per_anchor: int = 1_000_000
    max_total_candidates: int = 1_000_000
    max_total_rings: int = 250_000
    generate_shortcut_witnesses: bool = False
    allow_one_member_rings: bool = False
    strict: bool = False

    # Deprecated v1 aliases. They are normalized into the fields above.
    max_lifted_states_per_edge: int | None = None
    max_shortest_paths_per_edge: int | None = None
    strict_resource_limits: bool | None = None

    def __post_init__(self) -> None:
        try:
            method = PrimitiveRingSearchMethod(self.method)
        except ValueError as exc:
            raise PrimitiveRingInputError(
                "Invalid primitive-ring search method."
            ) from exc
        minimum = _positive_int(self.min_ring_size, name="min_ring_size")
        maximum = _positive_int(self.max_ring_size, name="max_ring_size")
        if minimum == 1:
            raise PrimitiveRingInputError(
                "One-member rings are reserved but not implemented in primitive-ring v2; "
                "min_ring_size must be at least 2."
            )
        if minimum < 1:
            raise PrimitiveRingInputError("min_ring_size must be positive.")
        if self.allow_one_member_rings:
            raise PrimitiveRingInputError(
                "allow_one_member_rings is a reserved compatibility field and must be False."
            )
        if maximum < minimum:
            raise PrimitiveRingInputError(
                "max_ring_size must be greater than or equal to min_ring_size."
            )
        source_limit = (
            self.max_lifted_states_per_source
            if self.max_lifted_states_per_edge is None
            else self.max_lifted_states_per_edge
        )
        path_limit = (
            self.max_shortest_paths_per_target
            if self.max_shortest_paths_per_edge is None
            else self.max_shortest_paths_per_edge
        )
        strict = (
            self.strict
            if self.strict_resource_limits is None
            else self.strict_resource_limits
        )
        object.__setattr__(self, "method", method)
        object.__setattr__(self, "min_ring_size", minimum)
        object.__setattr__(self, "max_ring_size", maximum)
        object.__setattr__(
            self,
            "max_lifted_states_per_source",
            _positive_int(source_limit, name="max_lifted_states_per_source"),
        )
        object.__setattr__(
            self,
            "max_shortest_paths_per_target",
            _positive_int(path_limit, name="max_shortest_paths_per_target"),
        )
        for name in (
            "max_path_pair_combinations_per_anchor",
            "max_total_candidates",
            "max_total_rings",
        ):
            object.__setattr__(
                self, name, _positive_int(getattr(self, name), name=name)
            )
        object.__setattr__(
            self, "generate_shortcut_witnesses", bool(self.generate_shortcut_witnesses)
        )
        object.__setattr__(
            self, "allow_one_member_rings", bool(self.allow_one_member_rings)
        )
        object.__setattr__(self, "strict", bool(strict))
        object.__setattr__(self, "max_lifted_states_per_edge", None)
        object.__setattr__(self, "max_shortest_paths_per_edge", None)
        object.__setattr__(self, "strict_resource_limits", None)

    @property
    def legacy_max_lifted_states_per_edge(self) -> int:
        return self.max_lifted_states_per_source

    @property
    def legacy_max_shortest_paths_per_edge(self) -> int:
        return self.max_shortest_paths_per_target

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method.value,
            "min_ring_size": self.min_ring_size,
            "max_ring_size": self.max_ring_size,
            "max_lifted_states_per_source": self.max_lifted_states_per_source,
            "max_shortest_paths_per_target": self.max_shortest_paths_per_target,
            "max_path_pair_combinations_per_anchor": self.max_path_pair_combinations_per_anchor,
            "max_total_candidates": self.max_total_candidates,
            "max_total_rings": self.max_total_rings,
            "generate_shortcut_witnesses": self.generate_shortcut_witnesses,
            "allow_one_member_rings": self.allow_one_member_rings,
            "strict": self.strict,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingOptions":
        # v1 payloads used edge-rooted limit names and had no method field.
        return cls(
            method=PrimitiveRingSearchMethod(
                str(
                    payload.get(
                        "method", PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST.value
                    )
                )
            ),
            min_ring_size=int(payload.get("min_ring_size", 2)),
            max_ring_size=int(payload.get("max_ring_size", 32)),
            max_lifted_states_per_source=int(
                payload.get(
                    "max_lifted_states_per_source",
                    payload.get("max_lifted_states_per_edge", 250_000),
                )
            ),
            max_shortest_paths_per_target=int(
                payload.get(
                    "max_shortest_paths_per_target",
                    payload.get("max_shortest_paths_per_edge", 100_000),
                )
            ),
            max_path_pair_combinations_per_anchor=int(
                payload.get("max_path_pair_combinations_per_anchor", 1_000_000)
            ),
            max_total_candidates=int(payload.get("max_total_candidates", 1_000_000)),
            max_total_rings=int(payload.get("max_total_rings", 250_000)),
            generate_shortcut_witnesses=bool(
                payload.get("generate_shortcut_witnesses", False)
            ),
            allow_one_member_rings=bool(payload.get("allow_one_member_rings", False)),
            strict=bool(
                payload.get("strict", payload.get("strict_resource_limits", False))
            ),
        )


@dataclass(frozen=True, order=True, slots=True)
class LiftedVertexRef:
    """One framework atom in one explicit periodic image."""

    atom_index: int
    image_shift: LatticeShift

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "atom_index", _nonnegative_int(self.atom_index, name="atom_index")
        )
        object.__setattr__(self, "image_shift", _shift(self.image_shift))

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "image_shift": list(self.image_shift),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiftedVertexRef":
        return cls(
            atom_index=int(payload["atom_index"]),
            image_shift=tuple(int(x) for x in payload["image_shift"]),
        )


@dataclass(frozen=True, order=True, slots=True)
class LiftedVertexPair:
    """Canonical unordered pair of exact lifted framework vertices."""

    first: LiftedVertexRef
    second: LiftedVertexRef

    def __post_init__(self) -> None:
        if not isinstance(self.first, LiftedVertexRef) or not isinstance(
            self.second, LiftedVertexRef
        ):
            raise PrimitiveRingInputError(
                "LiftedVertexPair endpoints must be LiftedVertexRef records."
            )
        if self.first == self.second:
            raise PrimitiveRingInputError(
                "LiftedVertexPair endpoints must be distinct."
            )
        if self.second < self.first:
            first, second = self.second, self.first
            object.__setattr__(self, "first", first)
            object.__setattr__(self, "second", second)

    def to_dict(self) -> dict[str, Any]:
        return {"first": self.first.to_dict(), "second": self.second.to_dict()}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiftedVertexPair":
        return cls(
            first=LiftedVertexRef.from_dict(payload["first"]),
            second=LiftedVertexRef.from_dict(payload["second"]),
        )


@dataclass(frozen=True, slots=True)
class PrimitiveShortcutWitness:
    """Optional explicit external shortcut proving nonprimitiveness."""

    endpoint_pair: LiftedVertexPair
    first_cycle_arc_length: int
    second_cycle_arc_length: int
    shortcut_steps: tuple["PrimitiveRingStep", ...]
    shortcut_vertices: tuple[LiftedVertexRef, ...]
    shortcut_length: int

    def __post_init__(self) -> None:
        if not isinstance(self.endpoint_pair, LiftedVertexPair):
            raise PrimitiveRingInputError("endpoint_pair must be a LiftedVertexPair.")
        first = _positive_int(
            self.first_cycle_arc_length, name="first_cycle_arc_length"
        )
        second = _positive_int(
            self.second_cycle_arc_length, name="second_cycle_arc_length"
        )
        length = _positive_int(self.shortcut_length, name="shortcut_length")
        steps = tuple(self.shortcut_steps)
        vertices = tuple(self.shortcut_vertices)
        if len(steps) != length or len(vertices) != length + 1:
            raise PrimitiveRingInputError("Shortcut witness lengths are inconsistent.")
        if (
            vertices[0] != self.endpoint_pair.first
            or vertices[-1] != self.endpoint_pair.second
        ):
            raise PrimitiveRingInputError(
                "Shortcut witness endpoints disagree with endpoint_pair."
            )
        if length >= min(first, second):
            raise PrimitiveRingInputError(
                "Shortcut witness must be shorter than both cycle arcs."
            )
        object.__setattr__(self, "first_cycle_arc_length", first)
        object.__setattr__(self, "second_cycle_arc_length", second)
        object.__setattr__(self, "shortcut_length", length)
        object.__setattr__(self, "shortcut_steps", steps)
        object.__setattr__(self, "shortcut_vertices", vertices)

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint_pair": self.endpoint_pair.to_dict(),
            "first_cycle_arc_length": self.first_cycle_arc_length,
            "second_cycle_arc_length": self.second_cycle_arc_length,
            "shortcut_steps": [step.to_dict() for step in self.shortcut_steps],
            "shortcut_vertices": [
                vertex.to_dict() for vertex in self.shortcut_vertices
            ],
            "shortcut_length": self.shortcut_length,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveShortcutWitness":
        return cls(
            endpoint_pair=LiftedVertexPair.from_dict(payload["endpoint_pair"]),
            first_cycle_arc_length=int(payload["first_cycle_arc_length"]),
            second_cycle_arc_length=int(payload["second_cycle_arc_length"]),
            shortcut_steps=tuple(
                PrimitiveRingStep.from_dict(item) for item in payload["shortcut_steps"]
            ),
            shortcut_vertices=tuple(
                LiftedVertexRef.from_dict(item) for item in payload["shortcut_vertices"]
            ),
            shortcut_length=int(payload["shortcut_length"]),
        )


@dataclass(frozen=True, order=True, slots=True)
class PrimitiveRingStep:
    """One oriented traversal of a topology edge."""

    edge_index: int
    orientation: Literal[-1, 1]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "edge_index", _nonnegative_int(self.edge_index, name="edge_index")
        )
        if self.orientation not in (-1, 1):
            raise PrimitiveRingInputError("orientation must be +1 or -1.")

    def reversed(self) -> "PrimitiveRingStep":
        return PrimitiveRingStep(self.edge_index, -self.orientation)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        return {"edge_index": self.edge_index, "orientation": self.orientation}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingStep":
        return cls(
            edge_index=int(payload["edge_index"]),
            orientation=int(payload["orientation"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, order=True, slots=True)
class PrimitiveRingEdgeToken:
    """Structural decorated-edge token used by canonical ring identity."""

    edge_key: FrameworkEdgeKey
    orientation: Literal[-1, 1]

    def __post_init__(self) -> None:
        if not isinstance(self.edge_key, FrameworkEdgeKey):
            raise PrimitiveRingInputError("edge_key must be a FrameworkEdgeKey.")
        if self.orientation not in (-1, 1):
            raise PrimitiveRingInputError("orientation must be +1 or -1.")

    def reversed(self) -> "PrimitiveRingEdgeToken":
        return PrimitiveRingEdgeToken(self.edge_key, -self.orientation)  # type: ignore[arg-type]

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_key": self.edge_key.to_dict(),
            "orientation": self.orientation,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingEdgeToken":
        return cls(
            edge_key=FrameworkEdgeKey.from_dict(payload["edge_key"]),
            orientation=int(payload["orientation"]),  # type: ignore[arg-type]
        )


@dataclass(frozen=True, order=True, slots=True)
class PrimitiveRingKey:
    """Canonical cyclic sequence of complete decorated edge tokens."""

    edge_tokens: tuple[PrimitiveRingEdgeToken, ...]

    def __post_init__(self) -> None:
        tokens = tuple(self.edge_tokens)
        if len(tokens) < 2 or any(
            not isinstance(token, PrimitiveRingEdgeToken) for token in tokens
        ):
            raise PrimitiveRingInputError(
                "PrimitiveRingKey requires at least two edge tokens."
            )
        if tokens != canonicalize_primitive_ring_tokens(tokens):
            raise PrimitiveRingInputError(
                "PrimitiveRingKey edge_tokens are not canonically rotated/reversed."
            )
        object.__setattr__(self, "edge_tokens", tokens)

    def to_dict(self) -> dict[str, Any]:
        return {"edge_tokens": [token.to_dict() for token in self.edge_tokens]}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingKey":
        return cls(
            edge_tokens=tuple(
                PrimitiveRingEdgeToken.from_dict(x) for x in payload["edge_tokens"]
            )
        )


@dataclass(frozen=True, slots=True)
class PrimitiveRing:
    """One canonical zero-winding primitive ring."""

    ring_id: int
    size: int
    steps: tuple[PrimitiveRingStep, ...]
    vertex_walk: tuple[LiftedVertexRef, ...]
    winding: LatticeShift
    key: PrimitiveRingKey
    generator_edge_indices: tuple[int, ...] = ()
    generator_kinds: tuple[str, ...] = ()
    generator_anchor_count: int = 0
    digest_algorithm: str = PRIMITIVE_RING_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        ring_id = _nonnegative_int(self.ring_id, name="ring_id")
        size = _positive_int(self.size, name="size")
        steps = tuple(self.steps)
        vertices = tuple(self.vertex_walk)
        winding = _shift(self.winding, name="winding")
        generators = tuple(
            sorted(
                {
                    _nonnegative_int(x, name="generator edge index")
                    for x in self.generator_edge_indices
                }
            )
        )
        generator_kinds = tuple(sorted({str(x) for x in self.generator_kinds}))
        generator_anchor_count = _nonnegative_int(
            self.generator_anchor_count, name="generator_anchor_count"
        )
        if size < 2 or size != len(steps) or size != len(vertices):
            raise PrimitiveRingInputError(
                "Ring size must equal step and open vertex-walk lengths and be >= 2."
            )
        if any(not isinstance(step, PrimitiveRingStep) for step in steps):
            raise PrimitiveRingInputError("steps contain an invalid record.")
        if any(not isinstance(vertex, LiftedVertexRef) for vertex in vertices):
            raise PrimitiveRingInputError("vertex_walk contains an invalid record.")
        if len(set(vertices)) != size:
            raise PrimitiveRingInputError("Ring vertex_walk must be lifted-simple.")
        if vertices[0].image_shift != _ZERO_SHIFT:
            raise PrimitiveRingInputError(
                "The first canonical lifted vertex must use image (0, 0, 0)."
            )
        if winding != _ZERO_SHIFT:
            raise PrimitiveRingInputError("Primitive rings must have zero winding.")
        if len(self.key.edge_tokens) != size:
            raise PrimitiveRingInputError("Ring key length disagrees with ring size.")
        if not generators and not generator_kinds:
            raise PrimitiveRingInputError(
                "A ring must retain at least one generator provenance record."
            )
        if generator_anchor_count == 0:
            generator_anchor_count = len(generators) or len(generator_kinds)
        if self.digest_algorithm != PRIMITIVE_RING_DIGEST_ALGORITHM:
            raise PrimitiveRingInputError(
                "Unsupported primitive-ring digest algorithm."
            )
        expected = primitive_ring_catalog_digest(
            {
                "ring_id": ring_id,
                "size": size,
                "steps": [step.to_dict() for step in steps],
                "vertex_walk": [vertex.to_dict() for vertex in vertices],
                "winding": list(winding),
                "key": self.key.to_dict(),
                "generator_edge_indices": list(generators),
                "generator_kinds": list(generator_kinds),
                "generator_anchor_count": generator_anchor_count,
                "digest_algorithm": self.digest_algorithm,
            }
        )
        digest = self.digest or expected
        if digest != expected:
            raise PrimitiveRingSerializationError(
                "Stored primitive-ring digest is inconsistent."
            )
        object.__setattr__(self, "ring_id", ring_id)
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "vertex_walk", vertices)
        object.__setattr__(self, "winding", winding)
        object.__setattr__(self, "generator_edge_indices", generators)
        object.__setattr__(self, "generator_kinds", generator_kinds)
        object.__setattr__(self, "generator_anchor_count", generator_anchor_count)
        object.__setattr__(self, "digest", digest)

    @property
    def edge_steps(self) -> tuple[PrimitiveRingStep, ...]:
        """v2 name for the oriented projected-edge traversal."""
        return self.steps

    @property
    def vertex_ids(self) -> tuple[int, ...]:
        return tuple(vertex.atom_index for vertex in self.vertex_walk)

    @property
    def vertex_images(self) -> tuple[LatticeShift, ...]:
        return tuple(vertex.image_shift for vertex in self.vertex_walk)

    @property
    def canonical_key(self) -> PrimitiveRingKey:
        return self.key

    def to_dict(self) -> dict[str, Any]:
        return {
            "ring_id": self.ring_id,
            "size": self.size,
            "steps": [step.to_dict() for step in self.steps],
            "vertex_walk": [vertex.to_dict() for vertex in self.vertex_walk],
            "winding": list(self.winding),
            "key": self.key.to_dict(),
            "generator_edge_indices": list(self.generator_edge_indices),
            "generator_kinds": list(self.generator_kinds),
            "generator_anchor_count": self.generator_anchor_count,
            "digest_algorithm": self.digest_algorithm,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRing":
        return cls(
            ring_id=int(payload["ring_id"]),
            size=int(payload["size"]),
            steps=tuple(PrimitiveRingStep.from_dict(x) for x in payload["steps"]),
            vertex_walk=tuple(
                LiftedVertexRef.from_dict(x) for x in payload["vertex_walk"]
            ),
            winding=tuple(int(x) for x in payload["winding"]),
            key=PrimitiveRingKey.from_dict(payload["key"]),
            generator_edge_indices=tuple(
                int(x) for x in payload.get("generator_edge_indices", ())
            ),
            generator_kinds=tuple(str(x) for x in payload.get("generator_kinds", ())),
            generator_anchor_count=int(payload.get("generator_anchor_count", 0)),
            digest_algorithm=str(
                payload.get("digest_algorithm", PRIMITIVE_RING_DIGEST_ALGORITHM)
            ),
            digest=(
                str(payload.get("digest", "")) if "generator_kinds" in payload else ""
            ),
        )


class PrimitiveRingSearchStatus(str, Enum):
    """Completion state of one removed-edge search."""

    COMPLETE_FOUND = "complete_found"
    COMPLETE_NONE = "complete_none"
    STATE_LIMIT_EXCEEDED = "state_limit_exceeded"
    PATH_LIMIT_EXCEEDED = "path_limit_exceeded"
    CANDIDATE_LIMIT_EXCEEDED = "candidate_limit_exceeded"
    NOT_SEARCHED_GLOBAL_LIMIT = "not_searched_global_limit"
    INVALID_EDGE = "invalid_edge"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True, slots=True)
class PrimitiveRingEdgeSearch:
    """Deterministic diagnostics for one topology-edge search."""

    edge_index: int
    edge_key: FrameworkEdgeKey
    status: PrimitiveRingSearchStatus
    shortest_path_length: int | None
    shortest_path_count: int | None
    shortest_path_count_is_exact: bool
    enumerated_path_count: int
    visited_lifted_state_count: int
    maximum_depth_reached: int
    candidate_count: int
    unique_ring_count: int
    complete_through_ring_size: int
    message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "edge_index", _nonnegative_int(self.edge_index, name="edge_index")
        )
        if not isinstance(self.edge_key, FrameworkEdgeKey):
            raise PrimitiveRingInputError("edge_key must be a FrameworkEdgeKey.")
        try:
            status = PrimitiveRingSearchStatus(self.status)
        except ValueError as exc:
            raise PrimitiveRingInputError("Invalid ring search status.") from exc
        object.__setattr__(self, "status", status)
        for name in (
            "enumerated_path_count",
            "visited_lifted_state_count",
            "maximum_depth_reached",
            "candidate_count",
            "unique_ring_count",
            "complete_through_ring_size",
        ):
            object.__setattr__(
                self, name, _nonnegative_int(getattr(self, name), name=name)
            )
        for name in ("shortest_path_length", "shortest_path_count"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _nonnegative_int(value, name=name))
        object.__setattr__(
            self,
            "shortest_path_count_is_exact",
            bool(self.shortest_path_count_is_exact),
        )
        if self.message is not None and not isinstance(self.message, str):
            raise PrimitiveRingInputError("message must be a string or None.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_index": self.edge_index,
            "edge_key": self.edge_key.to_dict(),
            "status": self.status.value,
            "shortest_path_length": self.shortest_path_length,
            "shortest_path_count": self.shortest_path_count,
            "shortest_path_count_is_exact": self.shortest_path_count_is_exact,
            "enumerated_path_count": self.enumerated_path_count,
            "visited_lifted_state_count": self.visited_lifted_state_count,
            "maximum_depth_reached": self.maximum_depth_reached,
            "candidate_count": self.candidate_count,
            "unique_ring_count": self.unique_ring_count,
            "complete_through_ring_size": self.complete_through_ring_size,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingEdgeSearch":
        return cls(
            edge_index=int(payload["edge_index"]),
            edge_key=FrameworkEdgeKey.from_dict(payload["edge_key"]),
            status=PrimitiveRingSearchStatus(str(payload["status"])),
            shortest_path_length=(
                None
                if payload.get("shortest_path_length") is None
                else int(payload["shortest_path_length"])
            ),
            shortest_path_count=(
                None
                if payload.get("shortest_path_count") is None
                else int(payload["shortest_path_count"])
            ),
            shortest_path_count_is_exact=bool(
                payload.get("shortest_path_count_is_exact", False)
            ),
            enumerated_path_count=int(payload["enumerated_path_count"]),
            visited_lifted_state_count=int(payload["visited_lifted_state_count"]),
            maximum_depth_reached=int(payload["maximum_depth_reached"]),
            candidate_count=int(payload["candidate_count"]),
            unique_ring_count=int(payload["unique_ring_count"]),
            complete_through_ring_size=int(payload["complete_through_ring_size"]),
            message=(
                None if payload.get("message") is None else str(payload["message"])
            ),
        )


@dataclass(frozen=True, slots=True)
class PrimitiveRingSourceSearch:
    """Diagnostics for one quotient-root lifted shortest-path search."""

    source_atom_index: int
    maximum_depth: int
    complete_through_depth: int
    visited_lifted_state_count: int
    target_state_count: int
    predecessor_record_count: int
    truncated: bool
    message: str | None = None

    def __post_init__(self) -> None:
        for name in (
            "source_atom_index",
            "maximum_depth",
            "complete_through_depth",
            "visited_lifted_state_count",
            "target_state_count",
            "predecessor_record_count",
        ):
            object.__setattr__(
                self, name, _nonnegative_int(getattr(self, name), name=name)
            )
        if self.complete_through_depth > self.maximum_depth:
            raise PrimitiveRingInputError(
                "complete_through_depth cannot exceed maximum_depth."
            )
        object.__setattr__(self, "truncated", bool(self.truncated))
        if self.message is not None and not isinstance(self.message, str):
            raise PrimitiveRingInputError("message must be a string or None.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_atom_index": self.source_atom_index,
            "maximum_depth": self.maximum_depth,
            "complete_through_depth": self.complete_through_depth,
            "visited_lifted_state_count": self.visited_lifted_state_count,
            "target_state_count": self.target_state_count,
            "predecessor_record_count": self.predecessor_record_count,
            "truncated": self.truncated,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingSourceSearch":
        return cls(
            source_atom_index=int(payload["source_atom_index"]),
            maximum_depth=int(payload["maximum_depth"]),
            complete_through_depth=int(
                payload.get("complete_through_depth", payload["maximum_depth"])
            ),
            visited_lifted_state_count=int(payload["visited_lifted_state_count"]),
            target_state_count=int(payload["target_state_count"]),
            predecessor_record_count=int(payload["predecessor_record_count"]),
            truncated=bool(payload["truncated"]),
            message=(
                None if payload.get("message") is None else str(payload["message"])
            ),
        )


@dataclass(frozen=True, slots=True)
class PrimitiveRingSearchDiagnostics:
    """Aggregate deterministic diagnostics for one catalog construction."""

    index_depth: int
    source_searches: tuple[PrimitiveRingSourceSearch, ...] = ()
    even_anchors_considered: int = 0
    odd_anchors_considered: int = 0
    shortest_paths_enumerated: int = 0
    path_pair_combinations_considered: int = 0
    structural_candidates: int = 0
    canonical_candidates: int = 0
    rejected_nonprimitive: int = 0
    duplicate_candidates: int = 0
    removed_edge_searches: tuple[PrimitiveRingEdgeSearch, ...] = ()
    shortcut_witnesses: tuple[PrimitiveShortcutWitness, ...] = ()
    shortcut_witness_count: int = 0
    truncated: bool = False
    messages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "index_depth", _nonnegative_int(self.index_depth, name="index_depth")
        )
        searches = tuple(self.source_searches)
        removed = tuple(self.removed_edge_searches)
        witnesses = tuple(self.shortcut_witnesses)
        messages = tuple(str(message) for message in self.messages)
        if any(not isinstance(item, PrimitiveRingSourceSearch) for item in searches):
            raise PrimitiveRingInputError("source_searches contain an invalid record.")
        if any(not isinstance(item, PrimitiveRingEdgeSearch) for item in removed):
            raise PrimitiveRingInputError(
                "removed_edge_searches contain an invalid record."
            )
        if any(not isinstance(item, PrimitiveShortcutWitness) for item in witnesses):
            raise PrimitiveRingInputError(
                "shortcut_witnesses contain an invalid record."
            )
        for name in (
            "even_anchors_considered",
            "odd_anchors_considered",
            "shortest_paths_enumerated",
            "path_pair_combinations_considered",
            "structural_candidates",
            "canonical_candidates",
            "rejected_nonprimitive",
            "duplicate_candidates",
            "shortcut_witness_count",
        ):
            object.__setattr__(
                self, name, _nonnegative_int(getattr(self, name), name=name)
            )
        object.__setattr__(self, "source_searches", searches)
        object.__setattr__(self, "removed_edge_searches", removed)
        object.__setattr__(self, "shortcut_witnesses", witnesses)
        object.__setattr__(self, "shortcut_witness_count", len(witnesses))
        object.__setattr__(self, "messages", messages)
        object.__setattr__(self, "truncated", bool(self.truncated))

    def to_dict(self) -> dict[str, Any]:
        return {
            "index_depth": self.index_depth,
            "source_searches": [item.to_dict() for item in self.source_searches],
            "even_anchors_considered": self.even_anchors_considered,
            "odd_anchors_considered": self.odd_anchors_considered,
            "shortest_paths_enumerated": self.shortest_paths_enumerated,
            "path_pair_combinations_considered": self.path_pair_combinations_considered,
            "structural_candidates": self.structural_candidates,
            "canonical_candidates": self.canonical_candidates,
            "rejected_nonprimitive": self.rejected_nonprimitive,
            "duplicate_candidates": self.duplicate_candidates,
            "removed_edge_searches": [
                item.to_dict() for item in self.removed_edge_searches
            ],
            "shortcut_witnesses": [item.to_dict() for item in self.shortcut_witnesses],
            "shortcut_witness_count": self.shortcut_witness_count,
            "truncated": self.truncated,
            "messages": list(self.messages),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingSearchDiagnostics":
        return cls(
            index_depth=int(payload.get("index_depth", 0)),
            source_searches=tuple(
                PrimitiveRingSourceSearch.from_dict(item)
                for item in payload.get("source_searches", ())
            ),
            even_anchors_considered=int(payload.get("even_anchors_considered", 0)),
            odd_anchors_considered=int(payload.get("odd_anchors_considered", 0)),
            shortest_paths_enumerated=int(payload.get("shortest_paths_enumerated", 0)),
            path_pair_combinations_considered=int(
                payload.get("path_pair_combinations_considered", 0)
            ),
            structural_candidates=int(payload.get("structural_candidates", 0)),
            canonical_candidates=int(payload.get("canonical_candidates", 0)),
            rejected_nonprimitive=int(payload.get("rejected_nonprimitive", 0)),
            duplicate_candidates=int(payload.get("duplicate_candidates", 0)),
            removed_edge_searches=tuple(
                PrimitiveRingEdgeSearch.from_dict(item)
                for item in payload.get("removed_edge_searches", ())
            ),
            shortcut_witnesses=tuple(
                PrimitiveShortcutWitness.from_dict(item)
                for item in payload.get("shortcut_witnesses", ())
            ),
            shortcut_witness_count=int(payload.get("shortcut_witness_count", 0)),
            truncated=bool(payload.get("truncated", False)),
            messages=tuple(str(item) for item in payload.get("messages", ())),
        )


@dataclass(frozen=True, order=True, slots=True)
class PrimitiveRingSizeCount:
    """One exact ring-size frequency."""

    ring_size: int
    ring_count: int

    def __post_init__(self) -> None:
        size = _positive_int(self.ring_size, name="ring_size")
        if size < 2:
            raise PrimitiveRingInputError("ring_size must be at least 2.")
        object.__setattr__(self, "ring_size", size)
        object.__setattr__(
            self, "ring_count", _nonnegative_int(self.ring_count, name="ring_count")
        )

    def to_dict(self) -> dict[str, Any]:
        return {"ring_size": self.ring_size, "ring_count": self.ring_count}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingSizeCount":
        return cls(
            ring_size=int(payload["ring_size"]), ring_count=int(payload["ring_count"])
        )


@dataclass(frozen=True, slots=True)
class LiftedAtomRef:
    """One atom or linker in one explicit periodic image."""

    atom_index: int
    image_shift: LatticeShift

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "atom_index", _nonnegative_int(self.atom_index, name="atom_index")
        )
        object.__setattr__(self, "image_shift", _shift(self.image_shift))

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_index": self.atom_index,
            "image_shift": list(self.image_shift),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LiftedAtomRef":
        return cls(
            atom_index=int(payload["atom_index"]),
            image_shift=tuple(int(x) for x in payload["image_shift"]),
        )


@dataclass(frozen=True, slots=True)
class PrimitiveRingCatalog:
    """Immutable deterministic catalog of rings for one framework topology."""

    topology_digest: str
    topology_graph_digest: str
    options: PrimitiveRingOptions
    search_method: PrimitiveRingSearchMethod
    ring_family: PrimitiveRingFamily
    rings: tuple[PrimitiveRing, ...]
    edge_searches: tuple[PrimitiveRingEdgeSearch, ...]
    ring_size_counts: tuple[PrimitiveRingSizeCount, ...]
    vertex_atom_indices: tuple[int, ...]
    vertex_to_ring_ids: tuple[tuple[int, ...], ...]
    edge_to_ring_ids: tuple[tuple[int, ...], ...]
    diagnostics: PrimitiveRingSearchDiagnostics
    search_completed_without_resource_truncation: bool
    complete_for_ring_sizes_up_to: int
    canonical_schema_version: str = CANONICAL_PRIMITIVE_RING_SCHEMA
    digest_algorithm: str = PRIMITIVE_RING_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in ("topology_digest", "topology_graph_digest"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise PrimitiveRingInputError(f"{name} must be a SHA-256 digest.")
        if not isinstance(self.options, PrimitiveRingOptions):
            raise PrimitiveRingInputError("options must be PrimitiveRingOptions.")
        try:
            search_method = PrimitiveRingSearchMethod(self.search_method)
            ring_family = PrimitiveRingFamily(self.ring_family)
        except ValueError as exc:
            raise PrimitiveRingInputError(
                "Invalid primitive-ring method or family."
            ) from exc
        expected_family = (
            PrimitiveRingFamily.PRIMITIVE_NO_SHORTCUT
            if search_method is PrimitiveRingSearchMethod.SHORTEST_PATH_PAIRS
            else PrimitiveRingFamily.EDGE_SHORTEST_SUBSET
        )
        if ring_family is not expected_family:
            raise PrimitiveRingInputError(
                "search_method and ring_family are inconsistent."
            )
        if self.options.method is not search_method:
            raise PrimitiveRingInputError(
                "Catalog search_method disagrees with options.method."
            )
        if not isinstance(self.diagnostics, PrimitiveRingSearchDiagnostics):
            raise PrimitiveRingInputError(
                "diagnostics must be PrimitiveRingSearchDiagnostics."
            )
        rings = tuple(self.rings)
        searches = tuple(self.edge_searches)
        counts = tuple(self.ring_size_counts)
        vertices = tuple(
            _nonnegative_int(x, name="vertex atom index")
            for x in self.vertex_atom_indices
        )
        vertex_incidence = tuple(
            tuple(sorted({_nonnegative_int(x, name="ring ID") for x in ids}))
            for ids in self.vertex_to_ring_ids
        )
        edge_incidence = tuple(
            tuple(sorted({_nonnegative_int(x, name="ring ID") for x in ids}))
            for ids in self.edge_to_ring_ids
        )
        if any(not isinstance(ring, PrimitiveRing) for ring in rings):
            raise PrimitiveRingInputError("rings contain an invalid record.")
        if any(not isinstance(search, PrimitiveRingEdgeSearch) for search in searches):
            raise PrimitiveRingInputError("edge_searches contain an invalid record.")
        if any(not isinstance(count, PrimitiveRingSizeCount) for count in counts):
            raise PrimitiveRingInputError("ring_size_counts contain an invalid record.")
        if tuple(ring.ring_id for ring in rings) != tuple(range(len(rings))):
            raise PrimitiveRingInputError("Ring IDs must be dense and sorted.")
        if tuple(ring.key for ring in rings) != tuple(
            sorted(ring.key for ring in rings)
        ):
            raise PrimitiveRingInputError("Rings must be sorted by canonical key.")
        if len({ring.key for ring in rings}) != len(rings):
            raise PrimitiveRingInputError("Primitive ring keys must be unique.")
        if tuple(search.edge_index for search in searches) != tuple(
            range(len(searches))
        ):
            raise PrimitiveRingInputError(
                "edge_searches must align with dense topology edge indices."
            )
        if not vertices or tuple(sorted(set(vertices))) != vertices:
            raise PrimitiveRingInputError(
                "vertex_atom_indices must be nonempty, sorted, and unique."
            )
        if len(vertex_incidence) != len(vertices):
            raise PrimitiveRingInputError("vertex_to_ring_ids is misaligned.")
        if len(edge_incidence) != len(searches):
            raise PrimitiveRingInputError("edge_to_ring_ids is misaligned.")
        valid_ids = set(range(len(rings)))
        if any(set(ids) - valid_ids for ids in (*vertex_incidence, *edge_incidence)):
            raise PrimitiveRingInputError("Incidence contains an invalid ring ID.")
        expected_counts = tuple(
            PrimitiveRingSizeCount(size, count)
            for size, count in sorted(Counter(ring.size for ring in rings).items())
        )
        if counts != expected_counts:
            raise PrimitiveRingInputError("ring_size_counts disagree with rings.")
        edge_key_by_index = tuple(search.edge_key for search in searches)
        vertex_position = {atom: position for position, atom in enumerate(vertices)}
        expected_vertex_incidence: list[list[int]] = [[] for _ in vertices]
        expected_edge_incidence: list[list[int]] = [[] for _ in searches]
        for ring in rings:
            if any(step.edge_index >= len(searches) for step in ring.steps):
                raise PrimitiveRingInputError("Ring references an invalid edge index.")
            expected_tokens = tuple(
                PrimitiveRingEdgeToken(
                    edge_key_by_index[step.edge_index], step.orientation
                )
                for step in ring.steps
            )
            if expected_tokens != ring.key.edge_tokens:
                raise PrimitiveRingInputError(
                    "Ring steps disagree with the structural ring key."
                )
            for vertex in ring.vertex_walk:
                if vertex.atom_index not in vertex_position:
                    raise PrimitiveRingInputError(
                        "Ring vertex is absent from vertex_atom_indices."
                    )
                expected_vertex_incidence[vertex_position[vertex.atom_index]].append(
                    ring.ring_id
                )
            # S5-P0 hardening: the stored canonical lifted walk must be a
            # continuous realization of the stored oriented quotient-edge steps.
            # The edge translation convention follows the vector method of
            # Chung, Hahn & Klee (1984), doi:10.1107/S0108767384000088, and
            # Klee (2004), doi:10.1002/crat.200410281.
            for step_index, (step, source) in enumerate(
                zip(ring.steps, ring.vertex_walk, strict=True)
            ):
                target = ring.vertex_walk[(step_index + 1) % ring.size]
                edge_key = edge_key_by_index[step.edge_index]
                if step.orientation == 1:
                    expected_source_atom = edge_key.vertex_i
                    expected_target_atom = edge_key.vertex_j
                    expected_target_image = _add_shift(
                        source.image_shift, edge_key.image_shift
                    )
                else:
                    expected_source_atom = edge_key.vertex_j
                    expected_target_atom = edge_key.vertex_i
                    expected_target_image = _sub_shift(
                        source.image_shift, edge_key.image_shift
                    )
                if source.atom_index != expected_source_atom:
                    raise PrimitiveRingInputError(
                        "Ring vertex_walk source is inconsistent with ring step orientation."
                    )
                if (
                    target.atom_index != expected_target_atom
                    or target.image_shift != expected_target_image
                ):
                    raise PrimitiveRingInputError(
                        "Ring vertex_walk is discontinuous with the stored ring steps."
                    )
            for edge_index in sorted({step.edge_index for step in ring.steps}):
                expected_edge_incidence[edge_index].append(ring.ring_id)
        if vertex_incidence != tuple(
            tuple(sorted(set(ids))) for ids in expected_vertex_incidence
        ):
            raise PrimitiveRingInputError("vertex_to_ring_ids disagrees with rings.")
        if edge_incidence != tuple(
            tuple(sorted(set(ids))) for ids in expected_edge_incidence
        ):
            raise PrimitiveRingInputError("edge_to_ring_ids disagrees with rings.")
        completed = not self.diagnostics.truncated
        if bool(self.search_completed_without_resource_truncation) != completed:
            raise PrimitiveRingInputError(
                "search_completed_without_resource_truncation is inconsistent."
            )
        complete = _nonnegative_int(
            self.complete_for_ring_sizes_up_to,
            name="complete_for_ring_sizes_up_to",
        )
        if complete > self.options.max_ring_size:
            raise PrimitiveRingInputError(
                "complete_for_ring_sizes_up_to exceeds the configured maximum."
            )
        if completed and complete != self.options.max_ring_size:
            raise PrimitiveRingInputError(
                "An untruncated search must be complete through max_ring_size."
            )
        if self.canonical_schema_version != CANONICAL_PRIMITIVE_RING_SCHEMA:
            raise PrimitiveRingSerializationError(
                "Unsupported primitive-ring schema version."
            )
        if self.digest_algorithm != PRIMITIVE_RING_DIGEST_ALGORITHM:
            raise PrimitiveRingSerializationError(
                "Unsupported primitive-ring digest algorithm."
            )
        object.__setattr__(self, "search_method", search_method)
        object.__setattr__(self, "ring_family", ring_family)
        object.__setattr__(self, "rings", rings)
        object.__setattr__(self, "edge_searches", searches)
        object.__setattr__(self, "ring_size_counts", counts)
        object.__setattr__(self, "vertex_atom_indices", vertices)
        object.__setattr__(self, "vertex_to_ring_ids", vertex_incidence)
        object.__setattr__(self, "edge_to_ring_ids", edge_incidence)
        object.__setattr__(
            self,
            "search_completed_without_resource_truncation",
            completed,
        )
        object.__setattr__(self, "complete_for_ring_sizes_up_to", complete)
        expected_digest = primitive_ring_catalog_digest(self._payload_without_digest())
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise PrimitiveRingSerializationError(
                "Stored primitive-ring catalog digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    @property
    def size_counts(self) -> tuple[PrimitiveRingSizeCount, ...]:
        return self.ring_size_counts

    def _payload_without_digest(self) -> dict[str, Any]:
        return {
            "topology_digest": self.topology_digest,
            "topology_graph_digest": self.topology_graph_digest,
            "options": self.options.to_dict(),
            "search_method": self.search_method.value,
            "ring_family": self.ring_family.value,
            "rings": [ring.to_dict() for ring in self.rings],
            "edge_searches": [search.to_dict() for search in self.edge_searches],
            "ring_size_counts": [count.to_dict() for count in self.ring_size_counts],
            "vertex_atom_indices": list(self.vertex_atom_indices),
            "vertex_to_ring_ids": [list(ids) for ids in self.vertex_to_ring_ids],
            "edge_to_ring_ids": [list(ids) for ids in self.edge_to_ring_ids],
            "diagnostics": self.diagnostics.to_dict(),
            "search_completed_without_resource_truncation": (
                self.search_completed_without_resource_truncation
            ),
            "complete_for_ring_sizes_up_to": self.complete_for_ring_sizes_up_to,
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
        }

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload_without_digest()
        payload["digest"] = self.digest
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PrimitiveRingCatalog":
        try:
            return cls(
                topology_digest=str(payload["topology_digest"]),
                topology_graph_digest=str(payload["topology_graph_digest"]),
                options=PrimitiveRingOptions.from_dict(payload["options"]),
                search_method=PrimitiveRingSearchMethod(
                    str(
                        payload.get(
                            "search_method",
                            PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST.value,
                        )
                    )
                ),
                ring_family=PrimitiveRingFamily(
                    str(
                        payload.get(
                            "ring_family",
                            PrimitiveRingFamily.EDGE_SHORTEST_SUBSET.value,
                        )
                    )
                ),
                rings=tuple(PrimitiveRing.from_dict(x) for x in payload["rings"]),
                edge_searches=tuple(
                    PrimitiveRingEdgeSearch.from_dict(x)
                    for x in payload["edge_searches"]
                ),
                ring_size_counts=tuple(
                    PrimitiveRingSizeCount.from_dict(x)
                    for x in payload["ring_size_counts"]
                ),
                vertex_atom_indices=tuple(
                    int(x) for x in payload["vertex_atom_indices"]
                ),
                vertex_to_ring_ids=tuple(
                    tuple(int(x) for x in ids) for ids in payload["vertex_to_ring_ids"]
                ),
                edge_to_ring_ids=tuple(
                    tuple(int(x) for x in ids) for ids in payload["edge_to_ring_ids"]
                ),
                diagnostics=(
                    PrimitiveRingSearchDiagnostics.from_dict(payload["diagnostics"])
                    if "diagnostics" in payload
                    else PrimitiveRingSearchDiagnostics(
                        index_depth=0,
                        removed_edge_searches=tuple(
                            PrimitiveRingEdgeSearch.from_dict(x)
                            for x in payload.get("edge_searches", ())
                        ),
                        truncated=not bool(
                            payload.get(
                                "search_completed_without_resource_truncation", False
                            )
                        ),
                        messages=(
                            "Migrated from v1 removed-edge catalog; primitive completeness is not claimed.",
                        ),
                    )
                ),
                search_completed_without_resource_truncation=bool(
                    payload["search_completed_without_resource_truncation"]
                ),
                complete_for_ring_sizes_up_to=int(
                    payload["complete_for_ring_sizes_up_to"]
                ),
                canonical_schema_version=CANONICAL_PRIMITIVE_RING_SCHEMA,
                digest_algorithm=str(
                    payload.get("digest_algorithm", PRIMITIVE_RING_DIGEST_ALGORITHM)
                ),
                digest=(
                    str(payload.get("digest", ""))
                    if payload.get("canonical_schema_version")
                    == CANONICAL_PRIMITIVE_RING_SCHEMA
                    else ""
                ),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, PrimitiveRingError):
                raise
            raise PrimitiveRingSerializationError(
                "Malformed primitive-ring catalog payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class _HalfEdge:
    edge_index: int
    orientation: Literal[-1, 1]
    source_atom_index: int
    target_atom_index: int
    image_delta: LatticeShift


@dataclass(frozen=True, order=True, slots=True)
class _Predecessor:
    previous_state: LiftedVertexRef
    edge_index: int
    orientation: Literal[-1, 1]


@dataclass(frozen=True, slots=True)
class _BFSResult:
    distance: Mapping[LiftedVertexRef, int]
    predecessors: Mapping[LiftedVertexRef, tuple[_Predecessor, ...]]
    target_distance: int | None
    visited_state_count: int
    maximum_depth_reached: int
    state_limit_exceeded: bool


@dataclass(slots=True)
class _CandidateAccumulator:
    key: PrimitiveRingKey
    steps: tuple[PrimitiveRingStep, ...]
    vertex_walk: tuple[LiftedVertexRef, ...]
    generator_edges: set[int]
    generator_kinds: set[str]
    generator_anchor_count: int = 0


@dataclass(slots=True)
class _SearchAccumulator:
    edge_index: int
    edge_key: FrameworkEdgeKey
    status: PrimitiveRingSearchStatus
    shortest_path_length: int | None
    shortest_path_count: int | None
    shortest_path_count_is_exact: bool
    enumerated_path_count: int
    visited_lifted_state_count: int
    maximum_depth_reached: int
    candidate_count: int
    complete_through_ring_size: int
    message: str | None = None


def canonicalize_primitive_ring_tokens(
    tokens: tuple[PrimitiveRingEdgeToken, ...],
) -> tuple[PrimitiveRingEdgeToken, ...]:
    forward = tuple(tokens)
    reverse = tuple(token.reversed() for token in reversed(tokens))
    variants = [
        sequence[offset:] + sequence[:offset]
        for sequence in (forward, reverse)
        for offset in range(len(sequence))
    ]
    return min(variants)


def _step_tokens(
    topology: FrameworkTopology, steps: Sequence[PrimitiveRingStep]
) -> tuple[PrimitiveRingEdgeToken, ...]:
    return tuple(
        PrimitiveRingEdgeToken(topology.edges[step.edge_index].key, step.orientation)
        for step in steps
    )


def _canonicalize_steps(
    topology: FrameworkTopology,
    steps: tuple[PrimitiveRingStep, ...],
) -> tuple[PrimitiveRingKey, tuple[PrimitiveRingStep, ...]]:
    forward_steps = tuple(steps)
    reverse_steps = tuple(step.reversed() for step in reversed(steps))
    variants: list[
        tuple[tuple[PrimitiveRingEdgeToken, ...], tuple[PrimitiveRingStep, ...]]
    ] = []
    for sequence in (forward_steps, reverse_steps):
        for offset in range(len(sequence)):
            rotated = sequence[offset:] + sequence[:offset]
            variants.append((_step_tokens(topology, rotated), rotated))
    tokens, canonical_steps = min(variants, key=lambda item: (item[0], item[1]))
    return PrimitiveRingKey(tokens), canonical_steps


def _build_half_edge_adjacency(
    topology: FrameworkTopology,
) -> dict[int, tuple[_HalfEdge, ...]]:
    adjacency: dict[int, list[_HalfEdge]] = {
        int(atom): [] for atom in topology.vertex_atom_indices
    }
    for edge_index, edge in enumerate(topology.edges):
        key = edge.key
        adjacency[key.vertex_i].append(
            _HalfEdge(
                edge_index=edge_index,
                orientation=1,
                source_atom_index=key.vertex_i,
                target_atom_index=key.vertex_j,
                image_delta=key.image_shift,
            )
        )
        adjacency[key.vertex_j].append(
            _HalfEdge(
                edge_index=edge_index,
                orientation=-1,
                source_atom_index=key.vertex_j,
                target_atom_index=key.vertex_i,
                image_delta=_neg_shift(key.image_shift),
            )
        )
    for atom, half_edges in adjacency.items():
        half_edges.sort(
            key=lambda item: (
                topology.edges[item.edge_index].key,
                item.orientation,
                item.target_atom_index,
                item.image_delta,
            )
        )
        adjacency[atom] = tuple(half_edges)  # type: ignore[assignment]
    return {atom: tuple(edges) for atom, edges in adjacency.items()}


def _edge_instance_anchor(
    topology: FrameworkTopology,
    state: LiftedVertexRef,
    half_edge: _HalfEdge,
) -> LatticeShift:
    if half_edge.orientation == 1:
        return state.image_shift
    return _sub_shift(
        state.image_shift, topology.edges[half_edge.edge_index].key.image_shift
    )


def _step_destination(
    topology: FrameworkTopology,
    source: LiftedVertexRef,
    step: PrimitiveRingStep,
) -> LiftedVertexRef:
    edge = topology.edges[step.edge_index].key
    if step.orientation == 1:
        if source.atom_index != edge.vertex_i:
            raise PrimitiveRingSearchError(
                "Forward ring step source does not match edge vertex_i."
            )
        return LiftedVertexRef(
            edge.vertex_j, _add_shift(source.image_shift, edge.image_shift)
        )
    if source.atom_index != edge.vertex_j:
        raise PrimitiveRingSearchError(
            "Reverse ring step source does not match edge vertex_j."
        )
    return LiftedVertexRef(
        edge.vertex_i, _sub_shift(source.image_shift, edge.image_shift)
    )


def _physical_instance_key(
    topology: FrameworkTopology,
    source: LiftedVertexRef,
    step: PrimitiveRingStep,
) -> tuple[int, LatticeShift]:
    edge = topology.edges[step.edge_index].key
    anchor = (
        source.image_shift
        if step.orientation == 1
        else _sub_shift(source.image_shift, edge.image_shift)
    )
    return (step.edge_index, anchor)


def _search_removed_edge(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    removed_edge_index: int,
    options: PrimitiveRingOptions,
) -> _BFSResult:
    edge = topology.edges[removed_edge_index].key
    start = LiftedVertexRef(edge.vertex_i, _ZERO_SHIFT)
    target = LiftedVertexRef(edge.vertex_j, edge.image_shift)
    max_depth = options.max_ring_size - 1
    distance: dict[LiftedVertexRef, int] = {start: 0}
    predecessors: dict[LiftedVertexRef, list[_Predecessor]] = defaultdict(list)
    queue: deque[LiftedVertexRef] = deque([start])
    target_distance: int | None = None
    state_limit_exceeded = False

    while queue:
        current = queue.popleft()
        depth = distance[current]
        if target_distance is not None and depth >= target_distance:
            continue
        if depth >= max_depth:
            continue
        for half_edge in adjacency[current.atom_index]:
            if (
                half_edge.edge_index == removed_edge_index
                and _edge_instance_anchor(topology, current, half_edge) == _ZERO_SHIFT
            ):
                continue
            neighbor = LiftedVertexRef(
                half_edge.target_atom_index,
                _add_shift(current.image_shift, half_edge.image_delta),
            )
            next_depth = depth + 1
            known = distance.get(neighbor)
            predecessor = _Predecessor(
                previous_state=current,
                edge_index=half_edge.edge_index,
                orientation=half_edge.orientation,
            )
            if known is None:
                if len(distance) >= options.max_lifted_states_per_source:
                    state_limit_exceeded = True
                    queue.clear()
                    break
                distance[neighbor] = next_depth
                predecessors[neighbor].append(predecessor)
                queue.append(neighbor)
                if neighbor == target and target_distance is None:
                    target_distance = next_depth
            elif known == next_depth:
                predecessors[neighbor].append(predecessor)
        if state_limit_exceeded:
            break

    frozen_predecessors = {
        state: tuple(sorted(records)) for state, records in predecessors.items()
    }
    return _BFSResult(
        distance=distance,
        predecessors=frozen_predecessors,
        target_distance=target_distance,
        visited_state_count=len(distance),
        maximum_depth_reached=max(distance.values()),
        state_limit_exceeded=state_limit_exceeded,
    )


def _count_predecessor_paths(
    start: LiftedVertexRef,
    target: LiftedVertexRef,
    result: _BFSResult,
    limit: int,
) -> tuple[int, bool]:
    counts: dict[LiftedVertexRef, int] = {start: 1}
    states = sorted(result.distance, key=lambda state: (result.distance[state], state))
    saturation = limit + 1
    for state in states:
        if state == start:
            continue
        total = 0
        for predecessor in result.predecessors.get(state, ()):
            total += counts.get(predecessor.previous_state, 0)
            if total >= saturation:
                total = saturation
                break
        counts[state] = total
    value = counts.get(target, 0)
    return value, value <= limit


def _backtrack_shortest_paths(
    start: LiftedVertexRef,
    target: LiftedVertexRef,
    predecessors: Mapping[LiftedVertexRef, tuple[_Predecessor, ...]],
) -> tuple[tuple[PrimitiveRingStep, ...], ...]:
    paths: list[tuple[PrimitiveRingStep, ...]] = []
    reversed_steps: list[PrimitiveRingStep] = []

    def visit(state: LiftedVertexRef) -> None:
        if state == start:
            paths.append(tuple(reversed(reversed_steps)))
            return
        for predecessor in predecessors.get(state, ()):
            reversed_steps.append(
                PrimitiveRingStep(predecessor.edge_index, predecessor.orientation)
            )
            visit(predecessor.previous_state)
            reversed_steps.pop()

    visit(target)
    return tuple(paths)


def _rebuild_vertex_walk(
    topology: FrameworkTopology,
    steps: tuple[PrimitiveRingStep, ...],
) -> tuple[LiftedVertexRef, ...]:
    first_edge = topology.edges[steps[0].edge_index].key
    first_atom = (
        first_edge.vertex_i if steps[0].orientation == 1 else first_edge.vertex_j
    )
    current = LiftedVertexRef(first_atom, _ZERO_SHIFT)
    vertices: list[LiftedVertexRef] = []
    for step in steps:
        vertices.append(current)
        current = _step_destination(topology, current, step)
    if current != vertices[0]:
        raise PrimitiveRingSearchError("Canonical step sequence does not close.")
    return tuple(vertices)


def _validate_candidate_cycle(
    topology: FrameworkTopology,
    steps: tuple[PrimitiveRingStep, ...],
    options: PrimitiveRingOptions,
) -> tuple[LiftedVertexRef, ...]:
    size = len(steps)
    if size < options.min_ring_size or size > options.max_ring_size:
        raise PrimitiveRingSearchError("Candidate ring size lies outside options.")
    first_edge = topology.edges[steps[0].edge_index].key
    first_atom = (
        first_edge.vertex_i if steps[0].orientation == 1 else first_edge.vertex_j
    )
    current = LiftedVertexRef(first_atom, _ZERO_SHIFT)
    vertices: list[LiftedVertexRef] = []
    instances: set[tuple[int, LatticeShift]] = set()
    winding = _ZERO_SHIFT
    for step in steps:
        vertices.append(current)
        instance = _physical_instance_key(topology, current, step)
        if instance in instances:
            raise PrimitiveRingSearchError(
                "Candidate repeats a physical lifted edge instance."
            )
        instances.add(instance)
        destination = _step_destination(topology, current, step)
        winding = _add_shift(
            winding, _sub_shift(destination.image_shift, current.image_shift)
        )
        current = destination
    if current != vertices[0]:
        raise PrimitiveRingSearchError("Candidate ring does not close exactly.")
    if winding != _ZERO_SHIFT:
        raise PrimitiveRingSearchError("Candidate ring has nonzero periodic winding.")
    if len(set(vertices)) != len(vertices):
        raise PrimitiveRingSearchError("Candidate ring is not lifted-simple.")
    return tuple(vertices)


def _candidate_from_path(
    topology: FrameworkTopology,
    removed_edge_index: int,
    path_steps: tuple[PrimitiveRingStep, ...],
    options: PrimitiveRingOptions,
) -> _CandidateAccumulator | None:
    steps = path_steps + (PrimitiveRingStep(removed_edge_index, -1),)
    if not (options.min_ring_size <= len(steps) <= options.max_ring_size):
        return None
    _validate_candidate_cycle(topology, steps, options)
    key, canonical_steps = _canonicalize_steps(topology, steps)
    vertex_walk = _rebuild_vertex_walk(topology, canonical_steps)
    _validate_candidate_cycle(topology, canonical_steps, options)
    return _CandidateAccumulator(
        key=key,
        steps=canonical_steps,
        vertex_walk=vertex_walk,
        generator_edges={removed_edge_index},
        generator_kinds={PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST.value},
        generator_anchor_count=1,
    )


def _strict_limit_error(
    options: PrimitiveRingOptions,
    *,
    edge_index: int,
    status: PrimitiveRingSearchStatus,
    message: str,
) -> None:
    if options.strict:
        raise PrimitiveRingComplexityError(
            f"Primitive-ring edge {edge_index} terminated with {status.value}: {message}"
        )


def _search_status_record(
    accumulator: _SearchAccumulator,
    *,
    unique_ring_count: int,
) -> PrimitiveRingEdgeSearch:
    return PrimitiveRingEdgeSearch(
        edge_index=accumulator.edge_index,
        edge_key=accumulator.edge_key,
        status=accumulator.status,
        shortest_path_length=accumulator.shortest_path_length,
        shortest_path_count=accumulator.shortest_path_count,
        shortest_path_count_is_exact=accumulator.shortest_path_count_is_exact,
        enumerated_path_count=accumulator.enumerated_path_count,
        visited_lifted_state_count=accumulator.visited_lifted_state_count,
        maximum_depth_reached=accumulator.maximum_depth_reached,
        candidate_count=accumulator.candidate_count,
        unique_ring_count=unique_ring_count,
        complete_through_ring_size=accumulator.complete_through_ring_size,
        message=accumulator.message,
    )


def _enumerate_removed_edge_shortest(
    topology: FrameworkTopology,
    *,
    options: PrimitiveRingOptions | None = None,
) -> PrimitiveRingCatalog:
    """Enumerate deterministic local removed-edge shortest-path rings."""
    if not isinstance(topology, FrameworkTopology):
        raise PrimitiveRingInputError("topology must be a FrameworkTopology.")
    opts = PrimitiveRingOptions() if options is None else options
    if not isinstance(opts, PrimitiveRingOptions):
        raise PrimitiveRingInputError("options must be PrimitiveRingOptions or None.")
    adjacency = _build_half_edge_adjacency(topology)
    candidate_map: dict[PrimitiveRingKey, _CandidateAccumulator] = {}
    search_accumulators: list[_SearchAccumulator] = []
    total_candidate_count = 0
    global_limit_reached = False

    for removed_edge_index, edge_path in enumerate(topology.edges):
        edge_key = edge_path.key
        if global_limit_reached:
            search_accumulators.append(
                _SearchAccumulator(
                    edge_index=removed_edge_index,
                    edge_key=edge_key,
                    status=PrimitiveRingSearchStatus.NOT_SEARCHED_GLOBAL_LIMIT,
                    shortest_path_length=None,
                    shortest_path_count=None,
                    shortest_path_count_is_exact=False,
                    enumerated_path_count=0,
                    visited_lifted_state_count=0,
                    maximum_depth_reached=0,
                    candidate_count=0,
                    complete_through_ring_size=max(1, opts.min_ring_size - 1),
                    message="Search skipped after the global candidate limit was reached.",
                )
            )
            continue

        bfs = _search_removed_edge(topology, adjacency, removed_edge_index, opts)
        if bfs.state_limit_exceeded:
            message = "Lifted-state limit exceeded before the bounded search completed."
            _strict_limit_error(
                opts,
                edge_index=removed_edge_index,
                status=PrimitiveRingSearchStatus.STATE_LIMIT_EXCEEDED,
                message=message,
            )
            search_accumulators.append(
                _SearchAccumulator(
                    edge_index=removed_edge_index,
                    edge_key=edge_key,
                    status=PrimitiveRingSearchStatus.STATE_LIMIT_EXCEEDED,
                    shortest_path_length=bfs.target_distance,
                    shortest_path_count=None,
                    shortest_path_count_is_exact=False,
                    enumerated_path_count=0,
                    visited_lifted_state_count=bfs.visited_state_count,
                    maximum_depth_reached=bfs.maximum_depth_reached,
                    candidate_count=0,
                    complete_through_ring_size=max(1, opts.min_ring_size - 1),
                    message=message,
                )
            )
            continue

        if bfs.target_distance is None:
            search_accumulators.append(
                _SearchAccumulator(
                    edge_index=removed_edge_index,
                    edge_key=edge_key,
                    status=PrimitiveRingSearchStatus.COMPLETE_NONE,
                    shortest_path_length=None,
                    shortest_path_count=0,
                    shortest_path_count_is_exact=True,
                    enumerated_path_count=0,
                    visited_lifted_state_count=bfs.visited_state_count,
                    maximum_depth_reached=bfs.maximum_depth_reached,
                    candidate_count=0,
                    complete_through_ring_size=opts.max_ring_size,
                    message=None,
                )
            )
            continue

        start = LiftedVertexRef(edge_key.vertex_i, _ZERO_SHIFT)
        target = LiftedVertexRef(edge_key.vertex_j, edge_key.image_shift)
        path_count, exact = _count_predecessor_paths(
            start,
            target,
            bfs,
            opts.max_shortest_paths_per_target,
        )
        if not exact:
            message = "Tied shortest-path count exceeded the per-edge path limit."
            _strict_limit_error(
                opts,
                edge_index=removed_edge_index,
                status=PrimitiveRingSearchStatus.PATH_LIMIT_EXCEEDED,
                message=message,
            )
            search_accumulators.append(
                _SearchAccumulator(
                    edge_index=removed_edge_index,
                    edge_key=edge_key,
                    status=PrimitiveRingSearchStatus.PATH_LIMIT_EXCEEDED,
                    shortest_path_length=bfs.target_distance,
                    shortest_path_count=path_count,
                    shortest_path_count_is_exact=False,
                    enumerated_path_count=0,
                    visited_lifted_state_count=bfs.visited_state_count,
                    maximum_depth_reached=bfs.maximum_depth_reached,
                    candidate_count=0,
                    complete_through_ring_size=max(1, bfs.target_distance),
                    message=message,
                )
            )
            continue

        paths = _backtrack_shortest_paths(start, target, bfs.predecessors)
        if len(paths) != path_count:
            raise PrimitiveRingSearchError(
                "Predecessor path count disagrees with deterministic backtracking."
            )
        transaction: dict[PrimitiveRingKey, _CandidateAccumulator] = {}
        candidate_count = 0
        limit_hit = False
        for path in paths:
            candidate = _candidate_from_path(topology, removed_edge_index, path, opts)
            if candidate is None:
                continue
            candidate_count += 1
            if total_candidate_count + candidate_count > opts.max_total_candidates:
                limit_hit = True
                break
            existing = transaction.get(candidate.key)
            if existing is None:
                transaction[candidate.key] = candidate
            else:
                existing.generator_edges.add(removed_edge_index)

        if limit_hit:
            message = (
                "Global valid-candidate limit exceeded; edge transaction discarded."
            )
            _strict_limit_error(
                opts,
                edge_index=removed_edge_index,
                status=PrimitiveRingSearchStatus.CANDIDATE_LIMIT_EXCEEDED,
                message=message,
            )
            global_limit_reached = True
            search_accumulators.append(
                _SearchAccumulator(
                    edge_index=removed_edge_index,
                    edge_key=edge_key,
                    status=PrimitiveRingSearchStatus.CANDIDATE_LIMIT_EXCEEDED,
                    shortest_path_length=bfs.target_distance,
                    shortest_path_count=path_count,
                    shortest_path_count_is_exact=True,
                    enumerated_path_count=len(paths),
                    visited_lifted_state_count=bfs.visited_state_count,
                    maximum_depth_reached=bfs.maximum_depth_reached,
                    candidate_count=candidate_count,
                    complete_through_ring_size=max(1, bfs.target_distance),
                    message=message,
                )
            )
            continue

        total_candidate_count += candidate_count
        for key, candidate in transaction.items():
            existing = candidate_map.get(key)
            if existing is None:
                candidate_map[key] = candidate
            else:
                existing.generator_edges.update(candidate.generator_edges)
                existing.generator_kinds.update(candidate.generator_kinds)
                existing.generator_anchor_count += candidate.generator_anchor_count
        status = (
            PrimitiveRingSearchStatus.COMPLETE_FOUND
            if transaction
            else PrimitiveRingSearchStatus.COMPLETE_NONE
        )
        search_accumulators.append(
            _SearchAccumulator(
                edge_index=removed_edge_index,
                edge_key=edge_key,
                status=status,
                shortest_path_length=bfs.target_distance,
                shortest_path_count=path_count,
                shortest_path_count_is_exact=True,
                enumerated_path_count=len(paths),
                visited_lifted_state_count=bfs.visited_state_count,
                maximum_depth_reached=bfs.maximum_depth_reached,
                candidate_count=candidate_count,
                complete_through_ring_size=opts.max_ring_size,
                message=None,
            )
        )

    sorted_candidates = [candidate_map[key] for key in sorted(candidate_map)]
    rings: list[PrimitiveRing] = []
    for ring_id, candidate in enumerate(sorted_candidates):
        rings.append(
            PrimitiveRing(
                ring_id=ring_id,
                size=len(candidate.steps),
                steps=candidate.steps,
                vertex_walk=candidate.vertex_walk,
                winding=_ZERO_SHIFT,
                key=candidate.key,
                generator_edge_indices=tuple(sorted(candidate.generator_edges)),
                generator_kinds=tuple(sorted(candidate.generator_kinds)),
                generator_anchor_count=candidate.generator_anchor_count,
            )
        )
    ring_tuple = tuple(rings)
    generated_by_edge: dict[int, int] = Counter(
        edge_index for ring in ring_tuple for edge_index in ring.generator_edge_indices
    )
    searches = tuple(
        _search_status_record(
            accumulator,
            unique_ring_count=generated_by_edge.get(accumulator.edge_index, 0),
        )
        for accumulator in search_accumulators
    )
    vertex_positions = {
        int(atom): position
        for position, atom in enumerate(topology.vertex_atom_indices)
    }
    vertex_incidence: list[list[int]] = [
        [] for _ in range(topology.vertex_atom_indices.size)
    ]
    edge_incidence: list[list[int]] = [[] for _ in topology.edges]
    for ring in ring_tuple:
        for atom in sorted({vertex.atom_index for vertex in ring.vertex_walk}):
            vertex_incidence[vertex_positions[atom]].append(ring.ring_id)
        for edge_index in sorted({step.edge_index for step in ring.steps}):
            edge_incidence[edge_index].append(ring.ring_id)
    size_counts = tuple(
        PrimitiveRingSizeCount(size, count)
        for size, count in sorted(Counter(ring.size for ring in ring_tuple).items())
    )
    completed = all(
        search.status
        in {
            PrimitiveRingSearchStatus.COMPLETE_FOUND,
            PrimitiveRingSearchStatus.COMPLETE_NONE,
        }
        for search in searches
    )
    complete_up_to = (
        opts.max_ring_size
        if not searches
        else min(search.complete_through_ring_size for search in searches)
    )
    diagnostics = PrimitiveRingSearchDiagnostics(
        index_depth=0,
        removed_edge_searches=searches,
        structural_candidates=total_candidate_count,
        canonical_candidates=len(ring_tuple),
        duplicate_candidates=max(0, total_candidate_count - len(ring_tuple)),
        truncated=not completed,
        messages=(
            "Removed-edge shortest search returns the edge-shortest subset only.",
        ),
    )
    return PrimitiveRingCatalog(
        topology_digest=topology.digest,
        topology_graph_digest=topology.graph_digest,
        options=opts,
        search_method=PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST,
        ring_family=PrimitiveRingFamily.EDGE_SHORTEST_SUBSET,
        rings=ring_tuple,
        edge_searches=searches,
        ring_size_counts=size_counts,
        vertex_atom_indices=tuple(int(x) for x in topology.vertex_atom_indices),
        vertex_to_ring_ids=tuple(tuple(ids) for ids in vertex_incidence),
        edge_to_ring_ids=tuple(tuple(ids) for ids in edge_incidence),
        diagnostics=diagnostics,
        search_completed_without_resource_truncation=completed,
        complete_for_ring_sizes_up_to=complete_up_to,
    )


@dataclass(frozen=True, slots=True)
class _SourceShortestPathIndex:
    source_atom_index: int
    maximum_depth: int
    complete_through_depth: int
    distance: Mapping[LiftedVertexRef, int]
    predecessors: Mapping[LiftedVertexRef, tuple[_Predecessor, ...]]
    truncated: bool
    message: str | None


@dataclass(frozen=True, slots=True)
class _LiftedShortestPathIndex:
    maximum_depth: int
    sources: Mapping[int, _SourceShortestPathIndex]


@dataclass(frozen=True, slots=True)
class _PrimitiveCycleCandidate:
    steps: tuple[PrimitiveRingStep, ...]
    vertex_walk: tuple[LiftedVertexRef, ...]
    certified_shortest_pairs: tuple[LiftedVertexPair, ...]
    generator_kind: str
    generator_anchor: tuple[Any, ...]


@dataclass(slots=True)
class _DefaultSearchStats:
    even_anchors_considered: int = 0
    odd_anchors_considered: int = 0
    shortest_paths_enumerated: int = 0
    path_pair_combinations_considered: int = 0
    structural_candidates: int = 0
    rejected_nonprimitive: int = 0
    duplicate_candidates: int = 0
    first_incomplete_ring_size: int | None = None
    messages: list[str] | None = None
    shortcut_witnesses: list[PrimitiveShortcutWitness] | None = None
    stopped: bool = False

    def __post_init__(self) -> None:
        if self.messages is None:
            self.messages = []
        if self.shortcut_witnesses is None:
            self.shortcut_witnesses = []

    def truncate(self, ring_size: int, message: str) -> None:
        if self.first_incomplete_ring_size is None:
            self.first_incomplete_ring_size = ring_size
        else:
            self.first_incomplete_ring_size = min(
                self.first_incomplete_ring_size, ring_size
            )
        assert self.messages is not None
        if message not in self.messages:
            self.messages.append(message)


def _build_source_shortest_path_index(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    source_atom_index: int,
    maximum_depth: int,
    state_limit: int,
) -> _SourceShortestPathIndex:
    """Build one deterministic transactional lifted BFS index.

    Each depth layer is committed atomically. If the next layer would exceed the
    configured state limit, it is discarded; distances through the current layer
    remain complete and safe for no-shortcut queries.
    """
    start = LiftedVertexRef(source_atom_index, _ZERO_SHIFT)
    distance: dict[LiftedVertexRef, int] = {start: 0}
    predecessors: dict[LiftedVertexRef, tuple[_Predecessor, ...]] = {start: ()}
    frontier: tuple[LiftedVertexRef, ...] = (start,)
    complete_depth = 0
    truncated = False
    message: str | None = None

    for depth in range(maximum_depth):
        next_predecessors: dict[LiftedVertexRef, list[_Predecessor]] = {}
        for state in frontier:
            for half_edge in adjacency[state.atom_index]:
                target = LiftedVertexRef(
                    half_edge.target_atom_index,
                    _add_shift(state.image_shift, half_edge.image_delta),
                )
                previous_distance = distance.get(target)
                if previous_distance is not None:
                    continue
                predecessor = _Predecessor(
                    previous_state=state,
                    edge_index=half_edge.edge_index,
                    orientation=half_edge.orientation,
                )
                next_predecessors.setdefault(target, []).append(predecessor)
        if not next_predecessors:
            complete_depth = maximum_depth
            frontier = ()
            break
        if len(distance) + len(next_predecessors) > state_limit:
            truncated = True
            message = (
                f"Source {source_atom_index} exceeded the lifted-state limit "
                f"before committing depth {depth + 1}."
            )
            complete_depth = depth
            break
        next_states = tuple(sorted(next_predecessors))
        for target in next_states:
            distance[target] = depth + 1
            predecessors[target] = tuple(sorted(next_predecessors[target]))
        frontier = next_states
        complete_depth = depth + 1
    else:
        complete_depth = maximum_depth

    return _SourceShortestPathIndex(
        source_atom_index=source_atom_index,
        maximum_depth=maximum_depth,
        complete_through_depth=complete_depth,
        distance=distance,
        predecessors=predecessors,
        truncated=truncated,
        message=message,
    )


def _build_lifted_shortest_path_index(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    options: PrimitiveRingOptions,
) -> _LiftedShortestPathIndex:
    maximum_depth = options.max_ring_size // 2
    sources: dict[int, _SourceShortestPathIndex] = {}
    for source_atom_index in (int(x) for x in topology.vertex_atom_indices):
        source = _build_source_shortest_path_index(
            topology,
            adjacency,
            source_atom_index,
            maximum_depth,
            options.max_lifted_states_per_source,
        )
        sources[source_atom_index] = source
        if source.truncated and options.strict:
            raise PrimitiveRingComplexityError(
                source.message or "Lifted search truncated."
            )
    return _LiftedShortestPathIndex(maximum_depth=maximum_depth, sources=sources)


def _relative_target(
    source: LiftedVertexRef, target: LiftedVertexRef
) -> LiftedVertexRef:
    return LiftedVertexRef(
        target.atom_index,
        _sub_shift(target.image_shift, source.image_shift),
    )


def _indexed_distance(
    index: _LiftedShortestPathIndex,
    source: LiftedVertexRef,
    target: LiftedVertexRef,
) -> int | None:
    source_index = index.sources[source.atom_index]
    return source_index.distance.get(_relative_target(source, target))


def _indexed_query_complete_through(
    index: _LiftedShortestPathIndex,
    source: LiftedVertexRef,
    depth: int,
) -> bool:
    return index.sources[source.atom_index].complete_through_depth >= depth


def _path_vertices_from_start(
    topology: FrameworkTopology,
    start: LiftedVertexRef,
    steps: Sequence[PrimitiveRingStep],
) -> tuple[LiftedVertexRef, ...]:
    vertices = [start]
    current = start
    for step in steps:
        current = _step_destination(topology, current, step)
        vertices.append(current)
    return tuple(vertices)


def _path_instance_keys(
    topology: FrameworkTopology,
    start: LiftedVertexRef,
    steps: Sequence[PrimitiveRingStep],
) -> frozenset[tuple[int, LatticeShift]]:
    current = start
    keys: set[tuple[int, LatticeShift]] = set()
    for step in steps:
        key = _physical_instance_key(topology, current, step)
        if key in keys:
            return frozenset()
        keys.add(key)
        current = _step_destination(topology, current, step)
    return frozenset(keys)


def _reverse_steps(
    steps: Sequence[PrimitiveRingStep],
) -> tuple[PrimitiveRingStep, ...]:
    return tuple(step.reversed() for step in reversed(steps))


def _count_index_paths(
    source: _SourceShortestPathIndex,
    target: LiftedVertexRef,
    limit: int,
) -> tuple[int, bool]:
    start = LiftedVertexRef(source.source_atom_index, _ZERO_SHIFT)
    result = _BFSResult(
        distance=source.distance,
        predecessors=source.predecessors,
        target_distance=source.distance.get(target),
        visited_state_count=len(source.distance),
        maximum_depth_reached=source.complete_through_depth,
        state_limit_exceeded=source.truncated,
    )
    return _count_predecessor_paths(start, target, result, limit)


def _enumerate_index_paths(
    source: _SourceShortestPathIndex,
    target: LiftedVertexRef,
    options: PrimitiveRingOptions,
    cache: dict[
        tuple[int, LiftedVertexRef], tuple[tuple[PrimitiveRingStep, ...], ...] | None
    ],
    stats: _DefaultSearchStats,
    ring_size: int,
) -> tuple[tuple[PrimitiveRingStep, ...], ...] | None:
    key = (source.source_atom_index, target)
    if key in cache:
        return cache[key]
    count, exact = _count_index_paths(
        source, target, options.max_shortest_paths_per_target
    )
    if not exact:
        message = (
            f"Shortest-path multiplicity exceeded the per-target limit for "
            f"source {source.source_atom_index}, target {target}."
        )
        stats.truncate(ring_size, message)
        if options.strict:
            raise PrimitiveRingComplexityError(message)
        cache[key] = None
        return None
    start = LiftedVertexRef(source.source_atom_index, _ZERO_SHIFT)
    paths = _backtrack_shortest_paths(start, target, source.predecessors)
    if len(paths) != count:
        raise PrimitiveRingSearchError(
            "Shortest-path predecessor count disagrees with enumeration."
        )
    stats.shortest_paths_enumerated += len(paths)
    cache[key] = paths
    return paths


def _maximal_half_cycle_pairs(
    vertices: tuple[LiftedVertexRef, ...],
) -> tuple[tuple[LiftedVertexPair, int, int], ...]:
    size = len(vertices)
    radius = size // 2
    records: list[tuple[LiftedVertexPair, int, int]] = []
    count = radius if size % 2 == 0 else size
    for index in range(count):
        other = (index + radius) % size
        pair = LiftedVertexPair(vertices[index], vertices[other])
        records.append((pair, radius, size - radius))
    return tuple(records)


def _find_external_shortcut_witness(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    vertices: tuple[LiftedVertexRef, ...],
    steps: tuple[PrimitiveRingStep, ...],
    maximum_shortcut_length: int,
    state_limit: int,
) -> PrimitiveShortcutWitness | None:
    """Find one external shortcut witness, if requested.

    Cycle edge instances are removed and cycle vertices may only be reached as
    terminal states. This realizes the external-detour reduction discussed in
    the primitive-ring literature; it is diagnostic and not on the default
    classification path.
    """
    cycle_vertices = set(vertices)
    cycle_instances: set[tuple[int, LatticeShift]] = set()
    current = vertices[0]
    for step in steps:
        cycle_instances.add(_physical_instance_key(topology, current, step))
        current = _step_destination(topology, current, step)

    size = len(vertices)
    positions = {vertex: index for index, vertex in enumerate(vertices)}
    for start in vertices:
        queue: deque[LiftedVertexRef] = deque([start])
        distance = {start: 0}
        parent: dict[LiftedVertexRef, tuple[LiftedVertexRef, PrimitiveRingStep]] = {}
        while queue:
            state = queue.popleft()
            depth = distance[state]
            if depth >= maximum_shortcut_length:
                continue
            for half_edge in adjacency[state.atom_index]:
                step = PrimitiveRingStep(half_edge.edge_index, half_edge.orientation)
                if _physical_instance_key(topology, state, step) in cycle_instances:
                    continue
                target = LiftedVertexRef(
                    half_edge.target_atom_index,
                    _add_shift(state.image_shift, half_edge.image_delta),
                )
                new_depth = depth + 1
                if target in cycle_vertices and target != start:
                    i = positions[start]
                    j = positions[target]
                    forward = (j - i) % size
                    backward = size - forward
                    if new_depth < min(forward, backward):
                        chain_steps = [step]
                        chain_vertices = [target]
                        cursor = state
                        while cursor != start:
                            previous, previous_step = parent[cursor]
                            chain_steps.append(previous_step)
                            chain_vertices.append(cursor)
                            cursor = previous
                        chain_vertices.append(start)
                        chain_steps.reverse()
                        chain_vertices.reverse()
                        pair = LiftedVertexPair(start, target)
                        if pair.first != start:
                            chain_steps = [
                                item.reversed() for item in reversed(chain_steps)
                            ]
                            chain_vertices = list(reversed(chain_vertices))
                        return PrimitiveShortcutWitness(
                            endpoint_pair=pair,
                            first_cycle_arc_length=forward,
                            second_cycle_arc_length=backward,
                            shortcut_steps=tuple(chain_steps),
                            shortcut_vertices=tuple(chain_vertices),
                            shortcut_length=new_depth,
                        )
                    continue
                if target in cycle_vertices or target in distance:
                    continue
                if len(distance) >= state_limit:
                    return None
                distance[target] = new_depth
                parent[target] = (state, step)
                queue.append(target)
    return None


def _primitive_candidate_passes(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    index: _LiftedShortestPathIndex,
    candidate: _PrimitiveCycleCandidate,
    options: PrimitiveRingOptions,
    stats: _DefaultSearchStats,
) -> bool | None:
    """Apply the primitive/no-shortcut criterion to one candidate.

    The maximal-half-arc reduction implements the irreducibility criterion used
    by Goetzke and Klein (1991) and Yuan and Cormack (2002). The exact lifted
    distance lookup is the mdstats periodic adaptation.
    """
    radius = len(candidate.vertex_walk) // 2
    certified = set(candidate.certified_shortest_pairs)
    for pair, first_arc, second_arc in _maximal_half_cycle_pairs(candidate.vertex_walk):
        if pair in certified:
            continue
        if not _indexed_query_complete_through(index, pair.first, radius - 1):
            message = (
                "A primitive no-shortcut query required an incomplete lifted "
                f"distance layer for pair {pair}."
            )
            stats.truncate(len(candidate.vertex_walk), message)
            if options.strict:
                raise PrimitiveRingComplexityError(message)
            return None
        distance = _indexed_distance(index, pair.first, pair.second)
        if distance is not None and distance < radius:
            stats.rejected_nonprimitive += 1
            if options.generate_shortcut_witnesses:
                witness = _find_external_shortcut_witness(
                    topology,
                    adjacency,
                    candidate.vertex_walk,
                    candidate.steps,
                    radius - 1,
                    options.max_lifted_states_per_source,
                )
                if witness is not None:
                    assert stats.shortcut_witnesses is not None
                    stats.shortcut_witnesses.append(witness)
            return False
    return True


def _canonical_candidate_accumulator(
    topology: FrameworkTopology,
    candidate: _PrimitiveCycleCandidate,
    options: PrimitiveRingOptions,
) -> _CandidateAccumulator:
    _validate_candidate_cycle(topology, candidate.steps, options)
    key, canonical_steps = _canonicalize_steps(topology, candidate.steps)
    vertex_walk = _rebuild_vertex_walk(topology, canonical_steps)
    _validate_candidate_cycle(topology, canonical_steps, options)
    return _CandidateAccumulator(
        key=key,
        steps=canonical_steps,
        vertex_walk=vertex_walk,
        generator_edges=set(),
        generator_kinds={candidate.generator_kind},
        generator_anchor_count=1,
    )


def _accept_default_candidate(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    index: _LiftedShortestPathIndex,
    candidate: _PrimitiveCycleCandidate,
    options: PrimitiveRingOptions,
    stats: _DefaultSearchStats,
    candidate_map: dict[PrimitiveRingKey, _CandidateAccumulator],
) -> None:
    if stats.stopped:
        return
    stats.structural_candidates += 1
    if stats.structural_candidates > options.max_total_candidates:
        message = "The global structural-candidate limit was exceeded."
        stats.truncate(len(candidate.steps), message)
        stats.stopped = True
        if options.strict:
            raise PrimitiveRingComplexityError(message)
        return
    primitive = _primitive_candidate_passes(
        topology, adjacency, index, candidate, options, stats
    )
    if primitive is not True:
        return
    accumulator = _canonical_candidate_accumulator(topology, candidate, options)
    existing = candidate_map.get(accumulator.key)
    if existing is None:
        if len(candidate_map) >= options.max_total_rings:
            message = "The global primitive-ring limit was exceeded."
            stats.truncate(len(candidate.steps), message)
            stats.stopped = True
            if options.strict:
                raise PrimitiveRingComplexityError(message)
            return
        candidate_map[accumulator.key] = accumulator
    else:
        stats.duplicate_candidates += 1
        existing.generator_kinds.update(accumulator.generator_kinds)
        existing.generator_anchor_count += 1


def _generate_even_candidates(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    index: _LiftedShortestPathIndex,
    ring_size: int,
    options: PrimitiveRingOptions,
    stats: _DefaultSearchStats,
    path_cache: dict[
        tuple[int, LiftedVertexRef], tuple[tuple[PrimitiveRingStep, ...], ...] | None
    ],
    candidate_map: dict[PrimitiveRingKey, _CandidateAccumulator],
) -> None:
    """Generate even candidates from paired tied shortest antipodal paths.

    This follows the shortest-path candidate structure developed by Horton
    (1987) and refined for relevant cycles by Vismara (1997), extended here to
    exact lifted periodic vertices and decorated multigraph edges.
    """
    radius = ring_size // 2
    for source_atom_index in sorted(index.sources):
        if stats.stopped:
            return
        source_index = index.sources[source_atom_index]
        if source_index.complete_through_depth < radius:
            continue
        start = LiftedVertexRef(source_atom_index, _ZERO_SHIFT)
        targets = sorted(
            state
            for state, distance in source_index.distance.items()
            if distance == radius
        )
        for target in targets:
            if stats.stopped:
                return
            paths = _enumerate_index_paths(
                source_index, target, options, path_cache, stats, ring_size
            )
            if paths is None or len(paths) < 2:
                continue
            stats.even_anchors_considered += 1
            pair_count = len(paths) * (len(paths) - 1) // 2
            if pair_count > options.max_path_pair_combinations_per_anchor:
                message = f"Even anchor {start}->{target} exceeded the path-pair limit."
                stats.truncate(ring_size, message)
                if options.strict:
                    raise PrimitiveRingComplexityError(message)
                continue
            for left_index in range(len(paths)):
                left = paths[left_index]
                left_vertices = _path_vertices_from_start(topology, start, left)
                left_instances = _path_instance_keys(topology, start, left)
                if not left_instances:
                    continue
                for right in paths[left_index + 1 :]:
                    stats.path_pair_combinations_considered += 1
                    right_vertices = _path_vertices_from_start(topology, start, right)
                    if set(left_vertices[1:-1]) & set(right_vertices[1:-1]):
                        continue
                    right_instances = _path_instance_keys(topology, start, right)
                    if not right_instances or left_instances & right_instances:
                        continue
                    steps = tuple(left) + _reverse_steps(right)
                    try:
                        vertices = _validate_candidate_cycle(topology, steps, options)
                    except PrimitiveRingSearchError:
                        continue
                    candidate = _PrimitiveCycleCandidate(
                        steps=steps,
                        vertex_walk=vertices,
                        certified_shortest_pairs=(LiftedVertexPair(start, target),),
                        generator_kind="even_shortest_path_pair",
                        generator_anchor=(
                            source_atom_index,
                            target.atom_index,
                            target.image_shift,
                        ),
                    )
                    _accept_default_candidate(
                        topology,
                        adjacency,
                        index,
                        candidate,
                        options,
                        stats,
                        candidate_map,
                    )


def _generate_odd_candidates(
    topology: FrameworkTopology,
    adjacency: Mapping[int, tuple[_HalfEdge, ...]],
    index: _LiftedShortestPathIndex,
    ring_size: int,
    options: PrimitiveRingOptions,
    stats: _DefaultSearchStats,
    path_cache: dict[
        tuple[int, LiftedVertexRef], tuple[tuple[PrimitiveRingStep, ...], ...] | None
    ],
    candidate_map: dict[PrimitiveRingKey, _CandidateAccumulator],
) -> None:
    """Generate odd candidates from two shortest root paths plus one edge.

    The parity-specific construction follows Vismara's relevant-cycle
    shortest-path families; lifted edge instances and periodic winding are
    mdstats-specific extensions.
    """
    radius = ring_size // 2
    for source_atom_index in sorted(index.sources):
        if stats.stopped:
            return
        source_index = index.sources[source_atom_index]
        if source_index.complete_through_depth < radius:
            continue
        start = LiftedVertexRef(source_atom_index, _ZERO_SHIFT)
        layer_states = tuple(
            sorted(
                state
                for state, distance in source_index.distance.items()
                if distance == radius
            )
        )
        layer_set = set(layer_states)
        for left_target in layer_states:
            if stats.stopped:
                return
            for half_edge in adjacency[left_target.atom_index]:
                right_target = LiftedVertexRef(
                    half_edge.target_atom_index,
                    _add_shift(left_target.image_shift, half_edge.image_delta),
                )
                if right_target not in layer_set or not left_target < right_target:
                    continue
                stats.odd_anchors_considered += 1
                left_paths = _enumerate_index_paths(
                    source_index,
                    left_target,
                    options,
                    path_cache,
                    stats,
                    ring_size,
                )
                right_paths = _enumerate_index_paths(
                    source_index,
                    right_target,
                    options,
                    path_cache,
                    stats,
                    ring_size,
                )
                if left_paths is None or right_paths is None:
                    continue
                pair_count = len(left_paths) * len(right_paths)
                if pair_count > options.max_path_pair_combinations_per_anchor:
                    message = (
                        f"Odd anchor {start}; {left_target}-{right_target} "
                        "exceeded the path-pair limit."
                    )
                    stats.truncate(ring_size, message)
                    if options.strict:
                        raise PrimitiveRingComplexityError(message)
                    continue
                closing = PrimitiveRingStep(half_edge.edge_index, half_edge.orientation)
                for left in left_paths:
                    left_vertices = _path_vertices_from_start(topology, start, left)
                    left_instances = _path_instance_keys(topology, start, left)
                    if not left_instances:
                        continue
                    for right in right_paths:
                        stats.path_pair_combinations_considered += 1
                        right_vertices = _path_vertices_from_start(
                            topology, start, right
                        )
                        if set(left_vertices[1:]) & set(right_vertices[1:]):
                            continue
                        right_instances = _path_instance_keys(topology, start, right)
                        if not right_instances or left_instances & right_instances:
                            continue
                        closing_key = _physical_instance_key(
                            topology, left_target, closing
                        )
                        if (
                            closing_key in left_instances
                            or closing_key in right_instances
                        ):
                            continue
                        steps = tuple(left) + (closing,) + _reverse_steps(right)
                        try:
                            vertices = _validate_candidate_cycle(
                                topology, steps, options
                            )
                        except PrimitiveRingSearchError:
                            continue
                        certified = {
                            LiftedVertexPair(start, left_target),
                            LiftedVertexPair(start, right_target),
                        }
                        if ring_size == 3:
                            certified.add(LiftedVertexPair(left_target, right_target))
                        candidate = _PrimitiveCycleCandidate(
                            steps=steps,
                            vertex_walk=vertices,
                            certified_shortest_pairs=tuple(sorted(certified)),
                            generator_kind="odd_shortest_root_paths",
                            generator_anchor=(
                                source_atom_index,
                                closing.edge_index,
                                closing_key[1],
                            ),
                        )
                        _accept_default_candidate(
                            topology,
                            adjacency,
                            index,
                            candidate,
                            options,
                            stats,
                            candidate_map,
                        )


def _placeholder_edge_searches(
    topology: FrameworkTopology,
    complete_through: int,
) -> tuple[PrimitiveRingEdgeSearch, ...]:
    return tuple(
        PrimitiveRingEdgeSearch(
            edge_index=edge_index,
            edge_key=edge.key,
            status=PrimitiveRingSearchStatus.NOT_APPLICABLE,
            shortest_path_length=None,
            shortest_path_count=None,
            shortest_path_count_is_exact=False,
            enumerated_path_count=0,
            visited_lifted_state_count=0,
            maximum_depth_reached=0,
            candidate_count=0,
            unique_ring_count=0,
            complete_through_ring_size=complete_through,
            message="Edge-rooted search is not used by shortest_path_pairs.",
        )
        for edge_index, edge in enumerate(topology.edges)
    )


def _catalog_from_candidates(
    topology: FrameworkTopology,
    options: PrimitiveRingOptions,
    candidate_map: Mapping[PrimitiveRingKey, _CandidateAccumulator],
    diagnostics: PrimitiveRingSearchDiagnostics,
    complete_through: int,
) -> PrimitiveRingCatalog:
    sorted_candidates = [candidate_map[key] for key in sorted(candidate_map)]
    rings = tuple(
        PrimitiveRing(
            ring_id=ring_id,
            size=len(candidate.steps),
            steps=candidate.steps,
            vertex_walk=candidate.vertex_walk,
            winding=_ZERO_SHIFT,
            key=candidate.key,
            generator_edge_indices=tuple(sorted(candidate.generator_edges)),
            generator_kinds=tuple(sorted(candidate.generator_kinds)),
            generator_anchor_count=candidate.generator_anchor_count,
        )
        for ring_id, candidate in enumerate(sorted_candidates)
    )
    vertex_positions = {
        int(atom): position
        for position, atom in enumerate(topology.vertex_atom_indices)
    }
    vertex_incidence: list[list[int]] = [
        [] for _ in range(topology.vertex_atom_indices.size)
    ]
    edge_incidence: list[list[int]] = [[] for _ in topology.edges]
    for ring in rings:
        for atom in sorted({vertex.atom_index for vertex in ring.vertex_walk}):
            vertex_incidence[vertex_positions[atom]].append(ring.ring_id)
        for edge_index in sorted({step.edge_index for step in ring.steps}):
            edge_incidence[edge_index].append(ring.ring_id)
    size_counts = tuple(
        PrimitiveRingSizeCount(size, count)
        for size, count in sorted(Counter(ring.size for ring in rings).items())
    )
    edge_searches = _placeholder_edge_searches(topology, complete_through)
    completed = not diagnostics.truncated
    return PrimitiveRingCatalog(
        topology_digest=topology.digest,
        topology_graph_digest=topology.graph_digest,
        options=options,
        search_method=PrimitiveRingSearchMethod.SHORTEST_PATH_PAIRS,
        ring_family=PrimitiveRingFamily.PRIMITIVE_NO_SHORTCUT,
        rings=rings,
        edge_searches=edge_searches,
        ring_size_counts=size_counts,
        vertex_atom_indices=tuple(int(x) for x in topology.vertex_atom_indices),
        vertex_to_ring_ids=tuple(tuple(sorted(set(ids))) for ids in vertex_incidence),
        edge_to_ring_ids=tuple(tuple(sorted(set(ids))) for ids in edge_incidence),
        diagnostics=diagnostics,
        search_completed_without_resource_truncation=completed,
        complete_for_ring_sizes_up_to=complete_through,
    )


def _enumerate_shortest_path_pair_primitives(
    topology: FrameworkTopology,
    *,
    options: PrimitiveRingOptions,
) -> PrimitiveRingCatalog:
    if not isinstance(topology, FrameworkTopology):
        raise PrimitiveRingInputError("topology must be a FrameworkTopology.")
    adjacency = _build_half_edge_adjacency(topology)
    index = _build_lifted_shortest_path_index(topology, adjacency, options)
    stats = _DefaultSearchStats()
    path_cache: dict[
        tuple[int, LiftedVertexRef],
        tuple[tuple[PrimitiveRingStep, ...], ...] | None,
    ] = {}
    candidate_map: dict[PrimitiveRingKey, _CandidateAccumulator] = {}

    minimum_complete_depth = min(
        source.complete_through_depth for source in index.sources.values()
    )
    complete_through = min(
        options.max_ring_size,
        2 * minimum_complete_depth + 1,
    )
    if minimum_complete_depth < index.maximum_depth:
        stats.truncate(
            complete_through + 1,
            "At least one lifted source index was truncated before the requested depth.",
        )

    for ring_size in range(options.min_ring_size, options.max_ring_size + 1):
        if stats.stopped:
            break
        if ring_size == 1:
            # One-member zero-shift self-loops are intentionally deferred; the
            # framework topology normally rejects them before this stage.
            continue
        if ring_size % 2 == 0:
            _generate_even_candidates(
                topology,
                adjacency,
                index,
                ring_size,
                options,
                stats,
                path_cache,
                candidate_map,
            )
        else:
            _generate_odd_candidates(
                topology,
                adjacency,
                index,
                ring_size,
                options,
                stats,
                path_cache,
                candidate_map,
            )

    if stats.first_incomplete_ring_size is not None:
        complete_through = min(
            complete_through, max(0, stats.first_incomplete_ring_size - 1)
        )
    source_searches = tuple(
        PrimitiveRingSourceSearch(
            source_atom_index=source.source_atom_index,
            maximum_depth=source.maximum_depth,
            complete_through_depth=source.complete_through_depth,
            visited_lifted_state_count=len(source.distance),
            target_state_count=max(0, len(source.distance) - 1),
            predecessor_record_count=sum(
                len(items) for items in source.predecessors.values()
            ),
            truncated=source.truncated,
            message=source.message,
        )
        for source in (index.sources[key] for key in sorted(index.sources))
    )
    truncated = (
        any(source.truncated for source in source_searches)
        or stats.first_incomplete_ring_size is not None
        or stats.stopped
    )
    diagnostics = PrimitiveRingSearchDiagnostics(
        index_depth=index.maximum_depth,
        source_searches=source_searches,
        even_anchors_considered=stats.even_anchors_considered,
        odd_anchors_considered=stats.odd_anchors_considered,
        shortest_paths_enumerated=stats.shortest_paths_enumerated,
        path_pair_combinations_considered=stats.path_pair_combinations_considered,
        structural_candidates=stats.structural_candidates,
        canonical_candidates=len(candidate_map),
        rejected_nonprimitive=stats.rejected_nonprimitive,
        duplicate_candidates=stats.duplicate_candidates,
        shortcut_witnesses=tuple(stats.shortcut_witnesses or ()),
        truncated=truncated,
        messages=tuple(stats.messages or ()),
    )
    if not truncated:
        complete_through = options.max_ring_size
    return _catalog_from_candidates(
        topology, options, candidate_map, diagnostics, complete_through
    )


def enumerate_primitive_rings(
    topology: FrameworkTopology,
    *,
    options: PrimitiveRingOptions | None = None,
) -> PrimitiveRingCatalog:
    """Enumerate a bounded deterministic ring catalog for one topology.

    ``SHORTEST_PATH_PAIRS`` is the default and returns the primitive
    no-shortcut family. ``REMOVED_EDGE_SHORTEST`` preserves the earlier fast
    edge-shortest subset method and must be selected explicitly.
    """
    opts = options or PrimitiveRingOptions()
    if opts.method is PrimitiveRingSearchMethod.REMOVED_EDGE_SHORTEST:
        return _enumerate_removed_edge_shortest(topology, options=opts)
    return _enumerate_shortest_path_pair_primitives(topology, options=opts)


def _framework_vertex_raw_gauge(
    topology: FrameworkTopology,
) -> dict[int, LatticeShift]:
    """Reconstruct the deterministic framework-to-raw vertex gauge.

    Framework edge keys store projected endpoint shifts, while
    ``raw_image_shift`` and atomic step shifts retain the induced atomic-graph
    gauge. The upstream normalization relation is

    ``projected = raw + gauge[source] - gauge[target]``.

    This helper recovers the per-vertex gauge (rooted at zero in each component)
    so a projected ring walk can be expanded into one continuous raw atomic walk.
    """
    adjacency: dict[int, list[tuple[int, LatticeShift]]] = {
        int(atom): [] for atom in topology.vertex_atom_indices
    }
    for edge in topology.edges:
        key = edge.key
        delta = _sub_shift(edge.raw_image_shift, key.image_shift)
        if key.vertex_i == key.vertex_j:
            if delta != _ZERO_SHIFT:
                raise PrimitiveRingInputError(
                    "Self-image edge raw and projected shifts use inconsistent gauges."
                )
            continue
        adjacency[key.vertex_i].append((key.vertex_j, delta))
        adjacency[key.vertex_j].append((key.vertex_i, _neg_shift(delta)))
    for atom in adjacency:
        adjacency[atom].sort()
    gauge: dict[int, LatticeShift] = {}
    for root in sorted(adjacency):
        if root in gauge:
            continue
        gauge[root] = _ZERO_SHIFT
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, delta in adjacency[current]:
                expected = _add_shift(gauge[current], delta)
                previous = gauge.get(neighbor)
                if previous is None:
                    gauge[neighbor] = expected
                    queue.append(neighbor)
                elif previous != expected:
                    raise PrimitiveRingInputError(
                        "Framework raw/projected edge gauges are cycle-inconsistent."
                    )
    return gauge


def expand_primitive_ring_atomic_walk(
    topology: FrameworkTopology,
    ring: PrimitiveRing,
    *,
    close: bool = False,
) -> tuple[LiftedAtomRef, ...]:
    """Expand one projected ring into its orientation-aware lifted atomic walk."""
    if not isinstance(topology, FrameworkTopology):
        raise PrimitiveRingInputError("topology must be a FrameworkTopology.")
    if not isinstance(ring, PrimitiveRing):
        raise PrimitiveRingInputError("ring must be a PrimitiveRing.")
    if any(step.edge_index >= topology.n_edges for step in ring.steps):
        raise PrimitiveRingInputError("Ring references an edge absent from topology.")
    tokens = _step_tokens(topology, ring.steps)
    if tokens != ring.key.edge_tokens:
        raise PrimitiveRingInputError(
            "Ring structural key is incompatible with the supplied topology."
        )
    vertex_raw_gauge = _framework_vertex_raw_gauge(topology)
    atomic_walk: list[LiftedAtomRef] = []
    for step_index, (step, source_vertex) in enumerate(
        zip(ring.steps, ring.vertex_walk, strict=True)
    ):
        oriented = topology.edges[step.edge_index].oriented(step.orientation)
        if oriented.source_vertex != source_vertex.atom_index:
            raise PrimitiveRingInputError(
                "Ring vertex walk is incompatible with the supplied topology."
            )
        source_image = _add_shift(
            source_vertex.image_shift, vertex_raw_gauge[source_vertex.atom_index]
        )
        segment = [LiftedAtomRef(oriented.atomic_path_indices[0], source_image)]
        image = source_image
        for atom_index, image_delta in zip(
            oriented.atomic_path_indices[1:],
            oriented.atomic_edge_image_shifts,
            strict=True,
        ):
            image = _add_shift(image, image_delta)
            segment.append(LiftedAtomRef(atom_index, image))
        expected_target = ring.vertex_walk[(step_index + 1) % ring.size]
        expected_target_raw = LiftedVertexRef(
            expected_target.atom_index,
            _add_shift(
                expected_target.image_shift,
                vertex_raw_gauge[expected_target.atom_index],
            ),
        )
        if (
            LiftedVertexRef(segment[-1].atom_index, segment[-1].image_shift)
            != expected_target_raw
        ):
            raise PrimitiveRingInputError(
                "Expanded atomic path does not meet the next lifted framework vertex."
            )
        if not atomic_walk:
            atomic_walk.extend(segment)
        else:
            if atomic_walk[-1] != segment[0]:
                raise PrimitiveRingInputError(
                    "Consecutive expanded framework paths are discontinuous."
                )
            atomic_walk.extend(segment[1:])
    if atomic_walk[-1] != atomic_walk[0]:
        raise PrimitiveRingInputError("Expanded atomic ring walk does not close.")
    return tuple(atomic_walk if close else atomic_walk[:-1])


__all__ = [
    "CANONICAL_PRIMITIVE_RING_SCHEMA",
    "LEGACY_PRIMITIVE_RING_SCHEMA",
    "PRIMITIVE_RING_ALGORITHM_VERSION",
    "PRIMITIVE_RING_DIGEST_ALGORITHM",
    "PrimitiveRingSearchMethod",
    "PrimitiveRingFamily",
    "LatticeShift",
    "PrimitiveRingError",
    "PrimitiveRingInputError",
    "PrimitiveRingSearchError",
    "PrimitiveRingComplexityError",
    "PrimitiveRingSerializationError",
    "PrimitiveRingOptions",
    "LiftedVertexRef",
    "LiftedVertexPair",
    "PrimitiveShortcutWitness",
    "PrimitiveRingStep",
    "PrimitiveRingEdgeToken",
    "PrimitiveRingKey",
    "PrimitiveRing",
    "PrimitiveRingSearchStatus",
    "PrimitiveRingEdgeSearch",
    "PrimitiveRingSourceSearch",
    "PrimitiveRingSearchDiagnostics",
    "PrimitiveRingSizeCount",
    "PrimitiveRingCatalog",
    "LiftedAtomRef",
    "enumerate_primitive_rings",
    "expand_primitive_ring_atomic_walk",
    "primitive_ring_catalog_digest",
]
