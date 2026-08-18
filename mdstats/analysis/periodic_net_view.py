"""Signature-only views of immutable periodic framework topologies.

The first :class:`PeriodicNetView` backend preserves the exact vertex and edge
orbit sets of :class:`~mdstats.analysis.FrameworkTopology`.  It changes only the
deterministic signatures that a later automorphism calculation must preserve.
Ignoring a decoration therefore permits permutation; it never removes, merges,
or contracts graph records.

The periodic quotient-edge representation and closed-walk gain construction
follow the vector/quotient-graph framework of Chung, Hahn, and Klee (1984) and
Klee (2004).  The policy-bound automorphism viewpoint is consistent with the
exact periodic-net treatment of Delgado-Friedrichs and O'Keeffe (2003).

References
----------
S. J. Chung, Th. Hahn, and W. E. Klee, Acta Cryst. A 40, 42-50 (1984),
doi:10.1107/S0108767384000088.
W. E. Klee, Cryst. Res. Technol. 39, 959-968 (2004),
doi:10.1002/crat.200410281.
O. Delgado-Friedrichs and M. O'Keeffe, Acta Cryst. A 59, 351-360 (2003),
doi:10.1107/S0108767303012017.
M. Newman, Integral Matrices, Academic Press (1972).
"""

from __future__ import annotations

import hashlib
import itertools
import json
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from math import gcd
from types import MappingProxyType
from typing import Any, Mapping, TypeAlias

from ._periodic_graph import LatticeShift, add_shift, negate_shift, subtract_shift
from .framework_topology import FrameworkEdgeKey, FrameworkTopology

CANONICAL_NET_VIEW_POLICY_SCHEMA = "mdstats.net-view-policy.v1"
CANONICAL_PERIODIC_NET_VIEW_SCHEMA = "mdstats.periodic-net-view.v1"
PERIODIC_NET_VIEW_DIGEST_ALGORITHM = "sha256"

SignatureAtom: TypeAlias = str | int | bool
NetSignature: TypeAlias = tuple[SignatureAtom, ...]


class PeriodicNetViewError(ValueError):
    """Base exception for periodic-net view construction and validation."""


class PeriodicNetViewInputError(PeriodicNetViewError):
    """Raised when a topology, policy, or source mapping is invalid."""


class PeriodicNetViewSerializationError(PeriodicNetViewError):
    """Raised when a serialized view is incompatible with its source topology."""


class VertexSignatureField(str, Enum):
    """Supported source attributes for first-backend vertex signatures."""

    ATOMIC_NUMBER = "atomic_number"


class EdgeSignatureField(str, Enum):
    """Supported source attributes for first-backend edge signatures."""

    EDGE_KIND = "edge_kind"
    RULE_ID = "rule_id"
    LINKER_ATOMIC_NUMBERS = "linker_atomic_numbers"
    LINKER_COUNT = "linker_count"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _enum_tuple(values: Any, enum_type: type[Enum], *, name: str) -> tuple[Any, ...]:
    try:
        raw = tuple(values)
    except TypeError as exc:
        raise PeriodicNetViewInputError(f"{name} must be an iterable.") from exc
    normalized: list[Enum] = []
    for value in raw:
        try:
            item = value if isinstance(value, enum_type) else enum_type(str(value))
        except (TypeError, ValueError) as exc:
            raise PeriodicNetViewInputError(f"Unsupported {name} entry {value!r}.") from exc
        normalized.append(item)
    if len(set(normalized)) != len(normalized):
        raise PeriodicNetViewInputError(f"{name} must not contain duplicates.")
    return tuple(sorted(normalized, key=lambda item: str(item.value)))


@dataclass(frozen=True, slots=True)
class NetViewPolicy:
    """Deterministic signature policy over one unchanged framework graph.

    ``label`` is descriptive provenance only and is intentionally excluded from
    ``digest``.  Two policies with the same retained fields define the same
    symmetry problem even if users give them different labels.
    """

    vertex_fields: tuple[VertexSignatureField, ...] = ()
    edge_fields: tuple[EdgeSignatureField, ...] = ()
    label: str = field(default="unlabeled framework net", compare=False)
    canonical_schema_version: str = CANONICAL_NET_VIEW_POLICY_SCHEMA
    digest_algorithm: str = PERIODIC_NET_VIEW_DIGEST_ALGORITHM
    digest: str = field(default="", compare=True)

    def __post_init__(self) -> None:
        vertices = _enum_tuple(
            self.vertex_fields, VertexSignatureField, name="vertex_fields"
        )
        edges = _enum_tuple(self.edge_fields, EdgeSignatureField, name="edge_fields")
        if not isinstance(self.label, str) or not self.label.strip():
            raise PeriodicNetViewInputError("label must be a nonempty string.")
        if self.canonical_schema_version != CANONICAL_NET_VIEW_POLICY_SCHEMA:
            raise PeriodicNetViewInputError("Unsupported net-view policy schema version.")
        if self.digest_algorithm != PERIODIC_NET_VIEW_DIGEST_ALGORITHM:
            raise PeriodicNetViewInputError("Unsupported net-view digest algorithm.")
        expected = _digest(
            {
                "canonical_schema_version": self.canonical_schema_version,
                "vertex_fields": [item.value for item in vertices],
                "edge_fields": [item.value for item in edges],
            }
        )
        digest = self.digest or expected
        if digest != expected:
            raise PeriodicNetViewInputError("Stored net-view policy digest is inconsistent.")
        object.__setattr__(self, "vertex_fields", vertices)
        object.__setattr__(self, "edge_fields", edges)
        object.__setattr__(self, "label", self.label.strip())
        object.__setattr__(self, "digest", digest)

    @classmethod
    def unlabeled_framework_net(cls, *, label: str = "unlabeled framework net") -> "NetViewPolicy":
        """Return a policy under which all framework vertices/edges share signatures."""
        return cls(label=label)

    @classmethod
    def chemically_decorated(
        cls, *, label: str = "chemically decorated framework net"
    ) -> "NetViewPolicy":
        """Return the built-in chemistry-preserving first-backend policy."""
        return cls(
            vertex_fields=(VertexSignatureField.ATOMIC_NUMBER,),
            edge_fields=(
                EdgeSignatureField.EDGE_KIND,
                EdgeSignatureField.RULE_ID,
                EdgeSignatureField.LINKER_ATOMIC_NUMBERS,
            ),
            label=label,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "label": self.label,
            "vertex_fields": [item.value for item in self.vertex_fields],
            "edge_fields": [item.value for item in self.edge_fields],
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NetViewPolicy":
        try:
            return cls(
                vertex_fields=tuple(payload.get("vertex_fields", ())),
                edge_fields=tuple(payload.get("edge_fields", ())),
                label=str(payload.get("label", "unlabeled framework net")),
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, PeriodicNetViewError):
                raise
            raise PeriodicNetViewSerializationError(
                "Invalid serialized NetViewPolicy payload."
            ) from exc


def _vertex_signature(
    topology: FrameworkTopology, position: int, policy: NetViewPolicy
) -> NetSignature:
    signature: list[SignatureAtom] = ["framework_vertex"]
    for field_name in policy.vertex_fields:
        if field_name is VertexSignatureField.ATOMIC_NUMBER:
            signature.extend((field_name.value, int(topology.vertex_atomic_numbers[position])))
        else:  # pragma: no cover - exhaustive enum guard
            raise PeriodicNetViewInputError(f"Unhandled vertex signature field {field_name!r}.")
    return tuple(signature)


def _edge_signature(
    topology: FrameworkTopology, position: int, policy: NetViewPolicy
) -> NetSignature:
    edge = topology.edges[position]
    signature: list[SignatureAtom] = ["framework_edge"]
    for field_name in policy.edge_fields:
        if field_name is EdgeSignatureField.EDGE_KIND:
            signature.extend((field_name.value, edge.edge_kind))
        elif field_name is EdgeSignatureField.RULE_ID:
            signature.extend((field_name.value, edge.key.rule_id))
        elif field_name is EdgeSignatureField.LINKER_ATOMIC_NUMBERS:
            signature.append(field_name.value)
            signature.extend(int(x) for x in edge.internal_linker_atomic_numbers)
        elif field_name is EdgeSignatureField.LINKER_COUNT:
            signature.extend((field_name.value, len(edge.key.internal_linker_indices)))
        else:  # pragma: no cover - exhaustive enum guard
            raise PeriodicNetViewInputError(f"Unhandled edge signature field {field_name!r}.")
    return tuple(signature)


def _canonical_gain(gain: LatticeShift) -> LatticeShift:
    for value in gain:
        if value < 0:
            return negate_shift(gain)
        if value > 0:
            return gain
    return gain


def _translation_rank(generators: tuple[LatticeShift, ...], active_axes: tuple[int, ...]) -> int:
    projected = [tuple(vector[axis] for axis in active_axes) for vector in generators]
    projected = [vector for vector in projected if any(vector)]
    if not projected:
        return 0
    if len(active_axes) == 1:
        return 1
    if len(active_axes) == 2:
        for left, right in itertools.combinations(projected, 2):
            if left[0] * right[1] - left[1] * right[0] != 0:
                return 2
        return 1
    for left, right, third in itertools.combinations(projected, 3):
        determinant = (
            left[0] * (right[1] * third[2] - right[2] * third[1])
            - left[1] * (right[0] * third[2] - right[2] * third[0])
            + left[2] * (right[0] * third[1] - right[1] * third[0])
        )
        if determinant != 0:
            return 3
    if len(active_axes) == 3:
        for left, right in itertools.combinations(projected, 2):
            cross = (
                left[1] * right[2] - left[2] * right[1],
                left[2] * right[0] - left[0] * right[2],
                left[0] * right[1] - left[1] * right[0],
            )
            if any(cross):
                return 2
    return 1


# The gcd of maximal generator minors is the determinant divisor and finite
# lattice-subgroup index from Smith normal form; see Newman (1972).
def _translation_index(
    generators: tuple[LatticeShift, ...], active_axes: tuple[int, ...], rank: int
) -> int | None:
    dimension = len(active_axes)
    if rank != dimension:
        return None
    if dimension == 0:
        return 1
    projected = [tuple(vector[axis] for axis in active_axes) for vector in generators]
    projected = [vector for vector in projected if any(vector)]
    minors: list[int] = []
    if dimension == 1:
        minors = [abs(vector[0]) for vector in projected]
    elif dimension == 2:
        minors = [
            abs(left[0] * right[1] - left[1] * right[0])
            for left, right in itertools.combinations(projected, 2)
        ]
    else:
        for left, right, third in itertools.combinations(projected, 3):
            minors.append(
                abs(
                    left[0] * (right[1] * third[2] - right[2] * third[1])
                    - left[1] * (right[0] * third[2] - right[2] * third[0])
                    + left[2] * (right[0] * third[1] - right[1] * third[0])
                )
            )
    result = 0
    for minor in minors:
        result = gcd(result, minor)
    return result if result > 0 else None


@dataclass(frozen=True, slots=True)
class PeriodicNetComponent:
    """One quotient component and its closed-walk translation subgroup."""

    component_id: int
    vertex_positions: tuple[int, ...]
    edge_positions: tuple[int, ...]
    cycle_gain_generators: tuple[LatticeShift, ...]
    translation_rank: int
    translation_index: int | None

    def __post_init__(self) -> None:
        if self.component_id < 0:
            raise PeriodicNetViewInputError("component_id must be nonnegative.")
        vertices = tuple(int(x) for x in self.vertex_positions)
        edges = tuple(int(x) for x in self.edge_positions)
        gains = tuple(tuple(int(x) for x in gain) for gain in self.cycle_gain_generators)
        if not vertices or vertices != tuple(sorted(set(vertices))):
            raise PeriodicNetViewInputError(
                "component vertex_positions must be nonempty, sorted, and unique."
            )
        if edges != tuple(sorted(set(edges))):
            raise PeriodicNetViewInputError(
                "component edge_positions must be sorted and unique."
            )
        if gains != tuple(sorted(set(gains))) or any(gain == (0, 0, 0) for gain in gains):
            raise PeriodicNetViewInputError(
                "cycle_gain_generators must be sorted, unique, and nonzero."
            )
        if self.translation_rank not in (0, 1, 2, 3):
            raise PeriodicNetViewInputError("translation_rank must lie in [0,3].")
        if self.translation_index is not None and self.translation_index <= 0:
            raise PeriodicNetViewInputError("translation_index must be positive when finite.")
        object.__setattr__(self, "vertex_positions", vertices)
        object.__setattr__(self, "edge_positions", edges)
        object.__setattr__(self, "cycle_gain_generators", gains)

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "vertex_positions": list(self.vertex_positions),
            "edge_positions": list(self.edge_positions),
            "cycle_gain_generators": [list(gain) for gain in self.cycle_gain_generators],
            "translation_rank": self.translation_rank,
            "translation_index": self.translation_index,
        }


def _component_analysis(topology: FrameworkTopology) -> tuple[PeriodicNetComponent, ...]:
    atom_to_position = {
        int(atom): position for position, atom in enumerate(topology.vertex_atom_indices)
    }
    active_axes = tuple(axis for axis, periodic in enumerate(topology.pbc) if bool(periodic))
    components: list[PeriodicNetComponent] = []
    for component_id in range(int(topology.n_components)):
        vertex_positions = tuple(
            position
            for position, label in enumerate(topology.component_labels)
            if int(label) == component_id
        )
        vertex_atoms = {int(topology.vertex_atom_indices[position]) for position in vertex_positions}
        edge_positions = tuple(
            position
            for position, edge in enumerate(topology.edges)
            if edge.key.vertex_i in vertex_atoms and edge.key.vertex_j in vertex_atoms
        )

        adjacency: dict[int, list[tuple[int, int, LatticeShift]]] = {
            atom: [] for atom in vertex_atoms
        }
        for edge_position in edge_positions:
            key = topology.edges[edge_position].key
            adjacency[key.vertex_i].append((key.vertex_j, edge_position, key.image_shift))
            adjacency[key.vertex_j].append(
                (key.vertex_i, edge_position, negate_shift(key.image_shift))
            )
        for values in adjacency.values():
            values.sort(key=lambda item: (item[0], item[1], item[2]))

        root = min(vertex_atoms)
        potential: dict[int, LatticeShift] = {root: (0, 0, 0)}
        queue: deque[int] = deque([root])
        while queue:
            source = queue.popleft()
            for target, _edge_position, shift in adjacency[source]:
                if target in potential:
                    continue
                potential[target] = add_shift(potential[source], shift)
                queue.append(target)
        if set(potential) != vertex_atoms:
            raise PeriodicNetViewInputError(
                "FrameworkTopology component labels disagree with quotient adjacency."
            )

        gains: set[LatticeShift] = set()
        for edge_position in edge_positions:
            key = topology.edges[edge_position].key
            gain = subtract_shift(
                add_shift(potential[key.vertex_i], key.image_shift),
                potential[key.vertex_j],
            )
            if gain != (0, 0, 0):
                gains.add(_canonical_gain(gain))
        ordered_gains = tuple(sorted(gains))
        rank = _translation_rank(ordered_gains, active_axes)
        index = _translation_index(ordered_gains, active_axes, rank)
        components.append(
            PeriodicNetComponent(
                component_id=component_id,
                vertex_positions=vertex_positions,
                edge_positions=edge_positions,
                cycle_gain_generators=ordered_gains,
                translation_rank=rank,
                translation_index=index,
            )
        )
    return tuple(components)


@dataclass(frozen=True, slots=True, eq=False)
class PeriodicNetView:
    """Immutable signature projection of one exact framework topology."""

    source_graph_digest: str
    source_topology_digest: str
    pbc: tuple[bool, bool, bool]
    policy: NetViewPolicy
    vertex_atom_indices: tuple[int, ...]
    edge_keys: tuple[FrameworkEdgeKey, ...]
    vertex_signatures: tuple[NetSignature, ...]
    edge_signatures: tuple[NetSignature, ...]
    components: tuple[PeriodicNetComponent, ...]
    canonical_schema_version: str = CANONICAL_PERIODIC_NET_VIEW_SCHEMA
    digest_algorithm: str = PERIODIC_NET_VIEW_DIGEST_ALGORITHM
    digest: str = ""
    _vertex_position_by_atom: Mapping[int, int] = field(init=False, repr=False, compare=False)
    _edge_position_by_key: Mapping[FrameworkEdgeKey, int] = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.source_graph_digest, str) or len(self.source_graph_digest) != 64:
            raise PeriodicNetViewInputError("source_graph_digest must be a SHA-256 digest.")
        if not isinstance(self.source_topology_digest, str) or len(self.source_topology_digest) != 64:
            raise PeriodicNetViewInputError("source_topology_digest must be a SHA-256 digest.")
        if not isinstance(self.policy, NetViewPolicy):
            raise PeriodicNetViewInputError("policy must be a NetViewPolicy.")
        pbc = tuple(bool(x) for x in self.pbc)
        if len(pbc) != 3:
            raise PeriodicNetViewInputError("pbc must contain exactly three booleans.")
        vertices = tuple(int(x) for x in self.vertex_atom_indices)
        edges = tuple(self.edge_keys)
        vertex_signatures = tuple(tuple(item for item in sig) for sig in self.vertex_signatures)
        edge_signatures = tuple(tuple(item for item in sig) for sig in self.edge_signatures)
        components = tuple(self.components)
        if not vertices or vertices != tuple(sorted(set(vertices))):
            raise PeriodicNetViewInputError("vertex_atom_indices must be nonempty, sorted, and unique.")
        if any(not isinstance(key, FrameworkEdgeKey) for key in edges):
            raise PeriodicNetViewInputError("edge_keys must contain FrameworkEdgeKey objects.")
        if edges != tuple(sorted(edges)) or len(set(edges)) != len(edges):
            raise PeriodicNetViewInputError("edge_keys must be sorted and unique.")
        if len(vertex_signatures) != len(vertices):
            raise PeriodicNetViewInputError("vertex_signatures must align with vertices.")
        if len(edge_signatures) != len(edges):
            raise PeriodicNetViewInputError("edge_signatures must align with edges.")
        if not components or tuple(component.component_id for component in components) != tuple(range(len(components))):
            raise PeriodicNetViewInputError("components must be nonempty and consecutively indexed.")
        covered_vertices = sorted(
            position for component in components for position in component.vertex_positions
        )
        covered_edges = sorted(position for component in components for position in component.edge_positions)
        if covered_vertices != list(range(len(vertices))):
            raise PeriodicNetViewInputError("components must partition all view vertices.")
        if covered_edges != list(range(len(edges))):
            raise PeriodicNetViewInputError("components must partition all view edges.")
        if self.canonical_schema_version != CANONICAL_PERIODIC_NET_VIEW_SCHEMA:
            raise PeriodicNetViewInputError("Unsupported periodic-net view schema version.")
        if self.digest_algorithm != PERIODIC_NET_VIEW_DIGEST_ALGORITHM:
            raise PeriodicNetViewInputError("Unsupported periodic-net view digest algorithm.")
        expected = _digest(
            {
                "canonical_schema_version": self.canonical_schema_version,
                "source_graph_digest": self.source_graph_digest,
                "source_topology_digest": self.source_topology_digest,
                "policy_digest": self.policy.digest,
                "vertex_signatures": [list(sig) for sig in vertex_signatures],
                "edge_signatures": [list(sig) for sig in edge_signatures],
            }
        )
        digest = self.digest or expected
        if digest != expected:
            raise PeriodicNetViewInputError("Stored periodic-net view digest is inconsistent.")
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "vertex_atom_indices", vertices)
        object.__setattr__(self, "edge_keys", edges)
        object.__setattr__(self, "vertex_signatures", vertex_signatures)
        object.__setattr__(self, "edge_signatures", edge_signatures)
        object.__setattr__(self, "components", components)
        object.__setattr__(
            self,
            "_vertex_position_by_atom",
            MappingProxyType({atom: position for position, atom in enumerate(vertices)}),
        )
        object.__setattr__(
            self,
            "_edge_position_by_key",
            MappingProxyType({key: position for position, key in enumerate(edges)}),
        )
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PeriodicNetView):
            return NotImplemented
        return (
            self.digest == other.digest
            and self.source_graph_digest == other.source_graph_digest
            and self.source_topology_digest == other.source_topology_digest
            and self.policy.digest == other.policy.digest
        )

    @property
    def n_vertices(self) -> int:
        return len(self.vertex_atom_indices)

    @property
    def n_edges(self) -> int:
        return len(self.edge_keys)

    @property
    def n_components(self) -> int:
        return len(self.components)

    @property
    def ambient_periodic_rank(self) -> int:
        return sum(self.pbc)

    @property
    def translation_rank(self) -> int | None:
        return self.components[0].translation_rank if self.n_components == 1 else None

    @property
    def translation_index(self) -> int | None:
        return self.components[0].translation_index if self.n_components == 1 else None

    @property
    def lifted_component_count(self) -> int | None:
        if any(component.translation_index is None for component in self.components):
            return None
        return sum(int(component.translation_index) for component in self.components)

    @property
    def is_lift_connected(self) -> bool:
        return self.n_components == 1 and self.translation_index == 1

    @property
    def natural_tiling_eligible(self) -> bool:
        return (
            self.pbc == (True, True, True)
            and self.n_components == 1
            and self.translation_rank == 3
            and self.translation_index == 1
        )

    def vertex_position(self, atom_index: int) -> int:
        try:
            return self._vertex_position_by_atom[int(atom_index)]
        except (KeyError, TypeError, ValueError) as exc:
            raise PeriodicNetViewInputError(
                f"atom_index={atom_index} is absent from this net view."
            ) from exc

    def edge_position(self, edge_key: FrameworkEdgeKey) -> int:
        try:
            return self._edge_position_by_key[edge_key]
        except (KeyError, TypeError) as exc:
            raise PeriodicNetViewInputError("edge_key is absent from this net view.") from exc

    def vertex_signature(self, atom_index: int) -> NetSignature:
        """Return the policy signature of one source framework vertex."""
        return self.vertex_signatures[self.vertex_position(atom_index)]

    def edge_signature(self, edge_key: FrameworkEdgeKey) -> NetSignature:
        """Return the policy signature of one source framework edge orbit."""
        return self.edge_signatures[self.edge_position(edge_key)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "source_graph_digest": self.source_graph_digest,
            "source_topology_digest": self.source_topology_digest,
            "pbc": list(self.pbc),
            "policy": self.policy.to_dict(),
            "vertex_atom_indices": list(self.vertex_atom_indices),
            "edge_keys": [key.to_dict() for key in self.edge_keys],
            "vertex_signatures": [list(sig) for sig in self.vertex_signatures],
            "edge_signatures": [list(sig) for sig in self.edge_signatures],
            "components": [component.to_dict() for component in self.components],
            "digest": self.digest,
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any], *, topology: FrameworkTopology
    ) -> "PeriodicNetView":
        if not isinstance(topology, FrameworkTopology):
            raise PeriodicNetViewSerializationError(
                "topology must be a FrameworkTopology for source validation."
            )
        try:
            policy = NetViewPolicy.from_dict(payload["policy"])
            rebuilt = build_periodic_net_view(topology, policy=policy)
            if payload.get("digest") != rebuilt.digest:
                raise PeriodicNetViewSerializationError(
                    "Serialized view digest is incompatible with the supplied topology."
                )
            if payload.get("source_graph_digest") != topology.graph_digest or payload.get(
                "source_topology_digest"
            ) != topology.digest:
                raise PeriodicNetViewSerializationError(
                    "Serialized view source digests do not match the supplied topology."
                )
            if rebuilt.to_dict() != dict(payload):
                raise PeriodicNetViewSerializationError(
                    "Serialized periodic-net view payload is not canonical."
                )
            return rebuilt
        except PeriodicNetViewError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise PeriodicNetViewSerializationError(
                "Invalid serialized PeriodicNetView payload."
            ) from exc


def build_periodic_net_view(
    topology: FrameworkTopology,
    *,
    policy: NetViewPolicy | None = None,
) -> PeriodicNetView:
    """Build the first signature-only periodic-net view.

    The source graph is preserved exactly.  The returned view changes only the
    vertex/edge signatures that future automorphisms must preserve.  Translation
    diagnostics are computed from deterministic fundamental-cycle gains in the
    periodic quotient graph.  The finite subgroup index detects cases where a
    quotient-connected graph still lifts to multiple disconnected periodic nets.
    """
    if not isinstance(topology, FrameworkTopology):
        raise PeriodicNetViewInputError("topology must be a FrameworkTopology.")
    active_policy = policy or NetViewPolicy.unlabeled_framework_net()
    if not isinstance(active_policy, NetViewPolicy):
        raise PeriodicNetViewInputError("policy must be a NetViewPolicy.")
    vertices = tuple(int(x) for x in topology.vertex_atom_indices)
    edge_keys = tuple(edge.key for edge in topology.edges)
    vertex_signatures = tuple(
        _vertex_signature(topology, position, active_policy)
        for position in range(len(vertices))
    )
    edge_signatures = tuple(
        _edge_signature(topology, position, active_policy)
        for position in range(len(edge_keys))
    )
    return PeriodicNetView(
        source_graph_digest=topology.graph_digest,
        source_topology_digest=topology.digest,
        pbc=tuple(bool(x) for x in topology.pbc),
        policy=active_policy,
        vertex_atom_indices=vertices,
        edge_keys=edge_keys,
        vertex_signatures=vertex_signatures,
        edge_signatures=edge_signatures,
        components=_component_analysis(topology),
    )
