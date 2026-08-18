"""Role-aware projection of periodic atomic connectivity into framework graphs.

The module contracts explicitly declared linker paths in an immutable
:class:`~mdstats.analysis.AtomicConnectivityState`.  It never rebuilds atomic
bonds from coordinates.  Projected edges retain their complete atom-level path,
periodic translation, linker identities, and rule provenance.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict, deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
from ase.data import atomic_numbers as ASE_ATOMIC_NUMBERS
from ase.data import chemical_symbols
from numpy.typing import ArrayLike, NDArray

from .atomic_connectivity import AtomicConnectivityState

IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]
Shift = tuple[int, int, int]

CANONICAL_FRAMEWORK_MAPPING_SCHEMA = "mdstats.framework-mapping.v2"
CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA = "mdstats.framework-topology.v2"
FRAMEWORK_DIGEST_ALGORITHM = "sha256"


class FrameworkTopologyError(ValueError):
    """Base exception for framework-topology construction and validation."""


class FrameworkMappingError(FrameworkTopologyError):
    """Raised when role or path-rule declarations are invalid or ambiguous."""


class FrameworkProjectionError(FrameworkTopologyError):
    """Raised when a projected periodic path violates a graph invariant."""


class FrameworkComplexityError(FrameworkProjectionError):
    """Raised when a hard path or projected-edge safety limit is exceeded."""


class FrameworkValidationError(FrameworkTopologyError):
    """Raised explicitly from a validation report containing error issues."""


class FrameworkAtomRole(str, Enum):
    """Scientific role of one active atom in a framework projection."""

    VERTEX = "vertex"
    LINKER = "linker"
    SPECTATOR = "spectator"
    EXCLUDED = "excluded"


def _coerce_role(value: FrameworkAtomRole | str, *, name: str) -> FrameworkAtomRole:
    if isinstance(value, FrameworkAtomRole):
        return value
    try:
        return FrameworkAtomRole(str(value))
    except (TypeError, ValueError) as exc:
        raise FrameworkMappingError(f"{name} is not a valid framework role.") from exc


def _coerce_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise FrameworkTopologyError(f"{name} must be an integer.")
    return int(value)


def _positive_int(value: Any, *, name: str) -> int:
    result = _coerce_int(value, name=name)
    if result <= 0:
        raise FrameworkTopologyError(f"{name} must be positive.")
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    result = _coerce_int(value, name=name)
    if result < 0:
        raise FrameworkTopologyError(f"{name} must be nonnegative.")
    return result


def _atomic_number(value: Any, *, name: str = "atomic number") -> int:
    result = _positive_int(value, name=name)
    if result >= len(chemical_symbols):
        raise FrameworkMappingError(f"{name}={result} is not a standard atomic number.")
    return result


def _symbol_to_number(symbol: str) -> int:
    if not isinstance(symbol, str) or not symbol.strip():
        raise FrameworkMappingError("Chemical symbols must be nonempty strings.")
    token = symbol.strip()
    normalized = token[0].upper() + token[1:].lower()
    try:
        return int(ASE_ATOMIC_NUMBERS[normalized])
    except KeyError as exc:
        raise FrameworkMappingError(f"Unknown chemical symbol {symbol!r}.") from exc


def _shift(value: Sequence[int], *, name: str = "image shift") -> Shift:
    if len(value) != 3:
        raise FrameworkTopologyError(f"{name} must contain three integers.")
    return tuple(_coerce_int(component, name=name) for component in value)  # type: ignore[return-value]


def _readonly_array(value: ArrayLike, dtype: Any, *, ndim: int) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise FrameworkTopologyError(f"Expected a {ndim}-D array.")
    array.setflags(write=False)
    return array


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _freeze_mapping(mapping: Mapping[Any, Any]) -> Mapping[Any, Any]:
    return MappingProxyType(dict(mapping))


@dataclass(frozen=True, slots=True)
class FrameworkPathRule:
    """One exact whole-path pattern, canonical modulo complete reversal.

    The endpoint species and ordered linker sequence form one coupled pattern.
    Reversal equivalence applies to the complete path, not independently to the
    endpoints and linker sequence.  Therefore ``A-O-S-B`` is equivalent to
    ``B-S-O-A`` but distinct from ``A-S-O-B``.
    """

    rule_id: str
    linker_atomic_numbers: tuple[int, ...]
    endpoint_atomic_numbers: tuple[int | None, int | None] = (None, None)
    edge_kind: str = "framework"

    def __post_init__(self) -> None:
        if not isinstance(self.rule_id, str) or not self.rule_id.strip():
            raise FrameworkMappingError("rule_id must be a nonempty string.")
        if not isinstance(self.edge_kind, str) or not self.edge_kind.strip():
            raise FrameworkMappingError("edge_kind must be a nonempty string.")
        sequence = tuple(
            _atomic_number(value, name="linker atomic number")
            for value in self.linker_atomic_numbers
        )
        raw_endpoints = tuple(self.endpoint_atomic_numbers)
        if len(raw_endpoints) != 2:
            raise FrameworkMappingError(
                "endpoint_atomic_numbers must contain exactly two entries."
            )
        endpoints: tuple[int | None, int | None] = tuple(
            None
            if value is None
            else _atomic_number(value, name="endpoint atomic number")
            for value in raw_endpoints
        )  # type: ignore[assignment]

        left, right = endpoints
        reverse_sequence = tuple(reversed(sequence))
        forward_key = (
            0 if left is None else left,
            *(int(x) for x in sequence),
            0 if right is None else right,
        )
        reverse_key = (
            0 if right is None else right,
            *(int(x) for x in reverse_sequence),
            0 if left is None else left,
        )
        if reverse_key < forward_key:
            endpoints = (right, left)
            sequence = reverse_sequence

        object.__setattr__(self, "rule_id", self.rule_id.strip())
        object.__setattr__(self, "edge_kind", self.edge_kind.strip())
        object.__setattr__(self, "linker_atomic_numbers", sequence)
        object.__setattr__(self, "endpoint_atomic_numbers", endpoints)

    @property
    def accepted_sequences(self) -> frozenset[tuple[int, ...]]:
        return frozenset(
            {self.linker_atomic_numbers, tuple(reversed(self.linker_atomic_numbers))}
        )

    @property
    def canonical_signature(self) -> tuple[int | None, ...]:
        left, right = self.endpoint_atomic_numbers
        return (left, *self.linker_atomic_numbers, right)

    @property
    def accepted_signatures(self) -> frozenset[tuple[int | None, ...]]:
        signature = self.canonical_signature
        return frozenset({signature, tuple(reversed(signature))})

    @staticmethod
    def _endpoint_matches(pattern: int | None, value: int) -> bool:
        return pattern is None or int(pattern) == int(value)

    def accepts_path(
        self,
        source_atomic_number: int,
        linker_atomic_numbers: Sequence[int],
        target_atomic_number: int,
    ) -> bool:
        candidate_linkers = tuple(int(x) for x in linker_atomic_numbers)
        left, right = self.endpoint_atomic_numbers
        if (
            candidate_linkers == self.linker_atomic_numbers
            and self._endpoint_matches(left, source_atomic_number)
            and self._endpoint_matches(right, target_atomic_number)
        ):
            return True
        return (
            candidate_linkers == tuple(reversed(self.linker_atomic_numbers))
            and self._endpoint_matches(right, source_atomic_number)
            and self._endpoint_matches(left, target_atomic_number)
        )

    @classmethod
    def from_symbols(
        cls,
        rule_id: str,
        linker_symbols: Iterable[str],
        *,
        endpoint_symbols: tuple[str | None, str | None] | None = None,
        edge_kind: str = "framework",
    ) -> "FrameworkPathRule":
        endpoints = (
            (None, None)
            if endpoint_symbols is None
            else tuple(
                None if symbol is None else _symbol_to_number(symbol)
                for symbol in endpoint_symbols
            )
        )
        return cls(
            rule_id=rule_id,
            linker_atomic_numbers=tuple(_symbol_to_number(x) for x in linker_symbols),
            endpoint_atomic_numbers=endpoints,  # type: ignore[arg-type]
            edge_kind=edge_kind,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "linker_atomic_numbers": list(self.linker_atomic_numbers),
            "endpoint_atomic_numbers": [
                None if value is None else int(value)
                for value in self.endpoint_atomic_numbers
            ],
            "edge_kind": self.edge_kind,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkPathRule":
        if "endpoint_atomic_number_pairs" in payload:
            raise FrameworkMappingError(
                "Version-1 endpoint-pair rules cannot be migrated automatically; "
                "declare one orientation-coupled endpoint pattern per rule."
            )
        endpoints = payload.get("endpoint_atomic_numbers", (None, None))
        return cls(
            rule_id=str(payload["rule_id"]),
            linker_atomic_numbers=tuple(
                int(x) for x in payload["linker_atomic_numbers"]
            ),
            endpoint_atomic_numbers=tuple(
                None if value is None else int(value) for value in endpoints
            ),  # type: ignore[arg-type]
            edge_kind=str(payload["edge_kind"]),
        )


def _signatures_overlap(
    left: tuple[int | None, ...], right: tuple[int | None, ...]
) -> bool:
    if len(left) != len(right) or left[1:-1] != right[1:-1]:
        return False
    return (left[0] is None or right[0] is None or left[0] == right[0]) and (
        left[-1] is None or right[-1] is None or left[-1] == right[-1]
    )


def _rules_overlap(left: FrameworkPathRule, right: FrameworkPathRule) -> bool:
    return any(
        _signatures_overlap(left_signature, right_signature)
        for left_signature in left.accepted_signatures
        for right_signature in right.accepted_signatures
    )


@dataclass(frozen=True, slots=True)
class FrameworkMapping:
    """Immutable species/atom roles and exact path-contraction rules."""

    species_roles: Mapping[int, FrameworkAtomRole]
    atom_role_overrides: Mapping[int, FrameworkAtomRole] = field(default_factory=dict)
    path_rules: tuple[FrameworkPathRule, ...] = ()
    unmapped_role: FrameworkAtomRole | None = None
    name: str | None = None
    canonical_schema_version: str = CANONICAL_FRAMEWORK_MAPPING_SCHEMA
    digest_algorithm: str = FRAMEWORK_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        species: dict[int, FrameworkAtomRole] = {}
        for number, role in dict(self.species_roles).items():
            species[_atomic_number(number)] = _coerce_role(role, name="species role")
        overrides: dict[int, FrameworkAtomRole] = {}
        for atom_index, role in dict(self.atom_role_overrides).items():
            index = _nonnegative_int(atom_index, name="atom-role override index")
            overrides[index] = _coerce_role(role, name="atom-role override")
        rules = tuple(self.path_rules)
        if any(not isinstance(rule, FrameworkPathRule) for rule in rules):
            raise FrameworkMappingError(
                "path_rules must contain FrameworkPathRule objects."
            )
        ids = [rule.rule_id for rule in rules]
        if len(ids) != len(set(ids)):
            raise FrameworkMappingError("Framework path-rule IDs must be unique.")
        for i, rule in enumerate(rules):
            for other in rules[i + 1 :]:
                if _rules_overlap(rule, other):
                    raise FrameworkMappingError(
                        f"Path rules {rule.rule_id!r} and {other.rule_id!r} overlap."
                    )
        unmapped = (
            None
            if self.unmapped_role is None
            else _coerce_role(self.unmapped_role, name="unmapped_role")
        )
        if self.name is not None and not isinstance(self.name, str):
            raise FrameworkMappingError("name must be None or a string.")
        if self.canonical_schema_version != CANONICAL_FRAMEWORK_MAPPING_SCHEMA:
            raise FrameworkMappingError("Unsupported framework-mapping schema version.")
        if self.digest_algorithm != FRAMEWORK_DIGEST_ALGORITHM:
            raise FrameworkMappingError("Unsupported framework digest algorithm.")
        object.__setattr__(
            self, "species_roles", _freeze_mapping(dict(sorted(species.items())))
        )
        object.__setattr__(
            self,
            "atom_role_overrides",
            _freeze_mapping(dict(sorted(overrides.items()))),
        )
        object.__setattr__(self, "path_rules", rules)
        object.__setattr__(self, "unmapped_role", unmapped)
        payload = self._identity_payload()
        expected = _digest(payload)
        stored = self.digest or expected
        if stored != expected:
            raise FrameworkMappingError(
                "Stored framework-mapping digest is inconsistent."
            )
        object.__setattr__(self, "digest", stored)

    @property
    def max_linker_atoms(self) -> int:
        return max(
            (len(rule.linker_atomic_numbers) for rule in self.path_rules), default=0
        )

    @property
    def allowed_rule_ids(self) -> tuple[str, ...]:
        return tuple(rule.rule_id for rule in self.path_rules)

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "canonical_schema_version": self.canonical_schema_version,
            "species_roles": [
                [number, role.value] for number, role in self.species_roles.items()
            ],
            "atom_role_overrides": [
                [index, role.value] for index, role in self.atom_role_overrides.items()
            ],
            "path_rules": [rule.to_dict() for rule in self.path_rules],
            "unmapped_role": None
            if self.unmapped_role is None
            else self.unmapped_role.value,
        }

    @classmethod
    def from_symbol_roles(
        cls,
        species_roles: Mapping[str, FrameworkAtomRole | str],
        *,
        atom_role_overrides: Mapping[int, FrameworkAtomRole | str] | None = None,
        path_rules: Iterable[FrameworkPathRule] = (),
        unmapped_role: FrameworkAtomRole | str | None = None,
        name: str | None = None,
    ) -> "FrameworkMapping":
        return cls(
            species_roles={
                _symbol_to_number(symbol): _coerce_role(role, name="species role")
                for symbol, role in species_roles.items()
            },
            atom_role_overrides={}
            if atom_role_overrides is None
            else atom_role_overrides,
            path_rules=tuple(path_rules),
            unmapped_role=unmapped_role,  # normalized in __post_init__
            name=name,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._identity_payload(),
            "name": self.name,
            "digest_algorithm": self.digest_algorithm,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkMapping":
        return cls(
            species_roles={
                int(k): FrameworkAtomRole(v) for k, v in payload["species_roles"]
            },
            atom_role_overrides={
                int(k): FrameworkAtomRole(v) for k, v in payload["atom_role_overrides"]
            },
            path_rules=tuple(
                FrameworkPathRule.from_dict(x) for x in payload["path_rules"]
            ),
            unmapped_role=(
                None
                if payload.get("unmapped_role") is None
                else FrameworkAtomRole(payload["unmapped_role"])
            ),
            name=payload.get("name"),
            canonical_schema_version=str(payload["canonical_schema_version"]),
            digest_algorithm=str(payload["digest_algorithm"]),
            digest=str(payload["digest"]),
        )


@dataclass(frozen=True, slots=True, eq=False)
class ResolvedFrameworkRoles:
    """Role assignment aligned exactly with one connectivity state's active atoms."""

    active_atom_indices: IntArray
    active_atomic_numbers: Int32Array
    roles: tuple[FrameworkAtomRole, ...]
    vertex_atom_indices: IntArray
    linker_atom_indices: IntArray
    spectator_atom_indices: IntArray
    excluded_atom_indices: IntArray
    mapping_digest: str

    def __post_init__(self) -> None:
        active = _readonly_array(self.active_atom_indices, np.int64, ndim=1)
        numbers = _readonly_array(self.active_atomic_numbers, np.int32, ndim=1)
        roles = tuple(_coerce_role(role, name="resolved role") for role in self.roles)
        if active.shape != numbers.shape or len(roles) != active.size:
            raise FrameworkTopologyError("Resolved roles must align with active atoms.")
        if active.size == 0 or np.any(np.diff(active) <= 0):
            raise FrameworkTopologyError(
                "Active atom indices must be nonempty and sorted."
            )
        role_arrays = []
        for value in (
            self.vertex_atom_indices,
            self.linker_atom_indices,
            self.spectator_atom_indices,
            self.excluded_atom_indices,
        ):
            array = _readonly_array(value, np.int64, ndim=1)
            if array.size and np.any(np.diff(array) <= 0):
                raise FrameworkTopologyError(
                    "Role-specific atom arrays must be sorted and unique."
                )
            role_arrays.append(array)
        combined = (
            np.concatenate(role_arrays) if role_arrays else np.empty(0, dtype=np.int64)
        )
        if sorted(int(x) for x in combined) != [int(x) for x in active]:
            raise FrameworkTopologyError(
                "Role-specific atom arrays must partition active atoms."
            )
        expected_by_role = {
            role: tuple(
                int(active[i]) for i, current in enumerate(roles) if current is role
            )
            for role in FrameworkAtomRole
        }
        for role, array in zip(FrameworkAtomRole, role_arrays, strict=True):
            if tuple(int(x) for x in array) != expected_by_role[role]:
                raise FrameworkTopologyError(
                    "Role-specific arrays disagree with roles."
                )
        if not isinstance(self.mapping_digest, str) or len(self.mapping_digest) != 64:
            raise FrameworkTopologyError(
                "mapping_digest must be a SHA-256 hexadecimal string."
            )
        object.__setattr__(self, "active_atom_indices", active)
        object.__setattr__(self, "active_atomic_numbers", numbers)
        object.__setattr__(self, "roles", roles)
        object.__setattr__(self, "vertex_atom_indices", role_arrays[0])
        object.__setattr__(self, "linker_atom_indices", role_arrays[1])
        object.__setattr__(self, "spectator_atom_indices", role_arrays[2])
        object.__setattr__(self, "excluded_atom_indices", role_arrays[3])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ResolvedFrameworkRoles):
            return NotImplemented
        return (
            np.array_equal(self.active_atom_indices, other.active_atom_indices)
            and np.array_equal(self.active_atomic_numbers, other.active_atomic_numbers)
            and self.roles == other.roles
            and self.mapping_digest == other.mapping_digest
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_atom_indices": self.active_atom_indices.tolist(),
            "active_atomic_numbers": self.active_atomic_numbers.tolist(),
            "roles": [role.value for role in self.roles],
            "vertex_atom_indices": self.vertex_atom_indices.tolist(),
            "linker_atom_indices": self.linker_atom_indices.tolist(),
            "spectator_atom_indices": self.spectator_atom_indices.tolist(),
            "excluded_atom_indices": self.excluded_atom_indices.tolist(),
            "mapping_digest": self.mapping_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResolvedFrameworkRoles":
        return cls(
            active_atom_indices=np.asarray(
                payload["active_atom_indices"], dtype=np.int64
            ),
            active_atomic_numbers=np.asarray(
                payload["active_atomic_numbers"], dtype=np.int32
            ),
            roles=tuple(FrameworkAtomRole(x) for x in payload["roles"]),
            vertex_atom_indices=np.asarray(
                payload["vertex_atom_indices"], dtype=np.int64
            ),
            linker_atom_indices=np.asarray(
                payload["linker_atom_indices"], dtype=np.int64
            ),
            spectator_atom_indices=np.asarray(
                payload["spectator_atom_indices"], dtype=np.int64
            ),
            excluded_atom_indices=np.asarray(
                payload["excluded_atom_indices"], dtype=np.int64
            ),
            mapping_digest=str(payload["mapping_digest"]),
        )


def resolve_framework_roles(
    state: AtomicConnectivityState,
    mapping: FrameworkMapping,
) -> ResolvedFrameworkRoles:
    """Resolve atom overrides, species defaults, then an optional fallback role."""
    if not isinstance(state, AtomicConnectivityState):
        raise TypeError("state must be an AtomicConnectivityState.")
    if not isinstance(mapping, FrameworkMapping):
        raise TypeError("mapping must be a FrameworkMapping.")
    roles: list[FrameworkAtomRole] = []
    unresolved: list[tuple[int, int]] = []
    for atom_index, number in zip(
        state.active_atom_indices, state.active_atomic_numbers, strict=True
    ):
        index = int(atom_index)
        atomic_number = int(number)
        if index in mapping.atom_role_overrides:
            role = mapping.atom_role_overrides[index]
        elif atomic_number in mapping.species_roles:
            role = mapping.species_roles[atomic_number]
        elif mapping.unmapped_role is not None:
            role = mapping.unmapped_role
        else:
            unresolved.append((index, atomic_number))
            continue
        roles.append(role)
    if unresolved:
        details = ", ".join(f"atom {i} (Z={z})" for i, z in unresolved[:8])
        suffix = " ..." if len(unresolved) > 8 else ""
        raise FrameworkMappingError(
            f"Active atoms have no framework role: {details}{suffix}"
        )
    active = np.asarray(state.active_atom_indices, dtype=np.int64)
    role_to_indices = {
        role: np.asarray(
            [int(active[i]) for i, current in enumerate(roles) if current is role],
            dtype=np.int64,
        )
        for role in FrameworkAtomRole
    }
    return ResolvedFrameworkRoles(
        active_atom_indices=active,
        active_atomic_numbers=state.active_atomic_numbers,
        roles=tuple(roles),
        vertex_atom_indices=role_to_indices[FrameworkAtomRole.VERTEX],
        linker_atom_indices=role_to_indices[FrameworkAtomRole.LINKER],
        spectator_atom_indices=role_to_indices[FrameworkAtomRole.SPECTATOR],
        excluded_atom_indices=role_to_indices[FrameworkAtomRole.EXCLUDED],
        mapping_digest=mapping.digest,
    )


@dataclass(frozen=True, slots=True)
class FrameworkProjectionOptions:
    """Hard, non-sampling safety limits for lifted-path enumeration."""

    max_linker_atoms: int = 16
    max_candidate_paths: int = 1_000_000
    max_projected_edges: int = 1_000_000

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "max_linker_atoms",
            _nonnegative_int(self.max_linker_atoms, name="max_linker_atoms"),
        )
        object.__setattr__(
            self,
            "max_candidate_paths",
            _positive_int(self.max_candidate_paths, name="max_candidate_paths"),
        )
        object.__setattr__(
            self,
            "max_projected_edges",
            _positive_int(self.max_projected_edges, name="max_projected_edges"),
        )


@dataclass(frozen=True, order=True, slots=True)
class FrameworkEdgeKey:
    """Canonical identity of one decorated projected multigraph edge."""

    vertex_i: int
    vertex_j: int
    image_shift: Shift
    internal_linker_indices: tuple[int, ...]
    internal_linker_image_offsets: tuple[Shift, ...]
    rule_id: str

    def __post_init__(self) -> None:
        i = _nonnegative_int(self.vertex_i, name="vertex_i")
        j = _nonnegative_int(self.vertex_j, name="vertex_j")
        if i > j:
            raise FrameworkProjectionError(
                "FrameworkEdgeKey requires vertex_i <= vertex_j."
            )
        shift = _shift(self.image_shift)
        internal = tuple(
            _nonnegative_int(x, name="internal linker index")
            for x in self.internal_linker_indices
        )
        offsets = tuple(
            _shift(x, name="internal linker image offset")
            for x in self.internal_linker_image_offsets
        )
        if len(internal) != len(offsets):
            raise FrameworkProjectionError(
                "Linker indices and image offsets must align."
            )
        if len(set(zip(internal, offsets, strict=True))) != len(internal):
            raise FrameworkProjectionError(
                "Lifted internal linker states must be unique."
            )
        if i == j and shift == (0, 0, 0):
            raise FrameworkProjectionError(
                "Zero-shift projected self-edges are invalid."
            )
        if not isinstance(self.rule_id, str) or not self.rule_id:
            raise FrameworkProjectionError("rule_id must be nonempty.")
        object.__setattr__(self, "vertex_i", i)
        object.__setattr__(self, "vertex_j", j)
        object.__setattr__(self, "image_shift", shift)
        object.__setattr__(self, "internal_linker_indices", internal)
        object.__setattr__(self, "internal_linker_image_offsets", offsets)

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertex_i": self.vertex_i,
            "vertex_j": self.vertex_j,
            "image_shift": list(self.image_shift),
            "internal_linker_indices": list(self.internal_linker_indices),
            "internal_linker_image_offsets": [
                list(x) for x in self.internal_linker_image_offsets
            ],
            "rule_id": self.rule_id,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkEdgeKey":
        return cls(
            vertex_i=int(payload["vertex_i"]),
            vertex_j=int(payload["vertex_j"]),
            image_shift=tuple(int(x) for x in payload["image_shift"]),
            internal_linker_indices=tuple(
                int(x) for x in payload["internal_linker_indices"]
            ),
            internal_linker_image_offsets=tuple(
                tuple(int(x) for x in offset)
                for offset in payload["internal_linker_image_offsets"]
            ),
            rule_id=str(payload["rule_id"]),
        )


@dataclass(frozen=True, slots=True)
class FrameworkEdgePath:
    """Atomic provenance for one canonical projected framework edge."""

    key: FrameworkEdgeKey
    atomic_path_indices: tuple[int, ...]
    atomic_edge_image_shifts: tuple[Shift, ...]
    internal_linker_atomic_numbers: tuple[int, ...]
    raw_image_shift: Shift
    edge_kind: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, FrameworkEdgeKey):
            raise FrameworkProjectionError("key must be a FrameworkEdgeKey.")
        path = tuple(
            _nonnegative_int(x, name="atomic path index")
            for x in self.atomic_path_indices
        )
        steps = tuple(
            _shift(x, name="atomic edge image shift")
            for x in self.atomic_edge_image_shifts
        )
        numbers = tuple(
            _atomic_number(x, name="internal linker atomic number")
            for x in self.internal_linker_atomic_numbers
        )
        raw = _shift(self.raw_image_shift, name="raw image shift")
        if len(path) < 2 or len(steps) != len(path) - 1:
            raise FrameworkProjectionError(
                "Atomic paths require n atoms and n-1 edge shifts."
            )
        if path[0] != self.key.vertex_i or path[-1] != self.key.vertex_j:
            raise FrameworkProjectionError(
                "Atomic path endpoints disagree with edge key."
            )
        if path[1:-1] != self.key.internal_linker_indices:
            raise FrameworkProjectionError(
                "Atomic path internal atoms disagree with edge key."
            )
        if len(numbers) != len(self.key.internal_linker_indices):
            raise FrameworkProjectionError(
                "Internal linker atomic numbers are misaligned."
            )
        summed = (
            tuple(int(x) for x in np.sum(np.asarray(steps, dtype=np.int64), axis=0))
            if steps
            else (0, 0, 0)
        )
        if summed != raw:
            raise FrameworkProjectionError(
                "Atomic edge shifts do not sum to raw_image_shift."
            )
        if not isinstance(self.edge_kind, str) or not self.edge_kind:
            raise FrameworkProjectionError("edge_kind must be nonempty.")
        object.__setattr__(self, "atomic_path_indices", path)
        object.__setattr__(self, "atomic_edge_image_shifts", steps)
        object.__setattr__(self, "internal_linker_atomic_numbers", numbers)
        object.__setattr__(self, "raw_image_shift", raw)

    def oriented(self, orientation: Literal[-1, 1] = 1) -> "OrientedFrameworkEdgePath":
        """Return a read-only traversal view in the requested orientation."""
        return OrientedFrameworkEdgePath(self, orientation)

    def oriented_from(self, source_vertex: int) -> "OrientedFrameworkEdgePath":
        """Orient a non-self edge away from ``source_vertex``."""
        source = _nonnegative_int(source_vertex, name="source_vertex")
        if self.key.vertex_i == self.key.vertex_j:
            raise FrameworkProjectionError(
                "Self-image edges require an explicit +1 or -1 orientation."
            )
        if source == self.key.vertex_i:
            return self.oriented(1)
        if source == self.key.vertex_j:
            return self.oriented(-1)
        raise FrameworkProjectionError(
            "source_vertex is not an endpoint of this framework edge."
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key.to_dict(),
            "atomic_path_indices": list(self.atomic_path_indices),
            "atomic_edge_image_shifts": [
                list(x) for x in self.atomic_edge_image_shifts
            ],
            "internal_linker_atomic_numbers": list(self.internal_linker_atomic_numbers),
            "raw_image_shift": list(self.raw_image_shift),
            "edge_kind": self.edge_kind,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkEdgePath":
        return cls(
            key=FrameworkEdgeKey.from_dict(payload["key"]),
            atomic_path_indices=tuple(int(x) for x in payload["atomic_path_indices"]),
            atomic_edge_image_shifts=tuple(
                tuple(int(x) for x in shift)
                for shift in payload["atomic_edge_image_shifts"]
            ),
            internal_linker_atomic_numbers=tuple(
                int(x) for x in payload["internal_linker_atomic_numbers"]
            ),
            raw_image_shift=tuple(int(x) for x in payload["raw_image_shift"]),
            edge_kind=str(payload["edge_kind"]),
        )


@dataclass(frozen=True, slots=True)
class OrientedFrameworkEdgePath:
    """One traversal orientation of a canonical undirected framework edge."""

    edge: FrameworkEdgePath
    orientation: Literal[-1, 1] = 1

    def __post_init__(self) -> None:
        if not isinstance(self.edge, FrameworkEdgePath):
            raise FrameworkProjectionError("edge must be a FrameworkEdgePath.")
        if self.orientation not in (-1, 1):
            raise FrameworkProjectionError("orientation must be +1 or -1.")

    @property
    def source_vertex(self) -> int:
        return (
            self.edge.key.vertex_i if self.orientation == 1 else self.edge.key.vertex_j
        )

    @property
    def target_vertex(self) -> int:
        return (
            self.edge.key.vertex_j if self.orientation == 1 else self.edge.key.vertex_i
        )

    @property
    def image_shift(self) -> Shift:
        if self.orientation == 1:
            return self.edge.key.image_shift
        return tuple(-x for x in self.edge.key.image_shift)

    @property
    def raw_image_shift(self) -> Shift:
        if self.orientation == 1:
            return self.edge.raw_image_shift
        return tuple(-x for x in self.edge.raw_image_shift)

    @property
    def atomic_path_indices(self) -> tuple[int, ...]:
        if self.orientation == 1:
            return self.edge.atomic_path_indices
        return tuple(reversed(self.edge.atomic_path_indices))

    @property
    def atomic_edge_image_shifts(self) -> tuple[Shift, ...]:
        if self.orientation == 1:
            return self.edge.atomic_edge_image_shifts
        return tuple(
            tuple(-component for component in shift)
            for shift in reversed(self.edge.atomic_edge_image_shifts)
        )

    @property
    def internal_linker_indices(self) -> tuple[int, ...]:
        if self.orientation == 1:
            return self.edge.key.internal_linker_indices
        return tuple(reversed(self.edge.key.internal_linker_indices))

    @property
    def internal_linker_atomic_numbers(self) -> tuple[int, ...]:
        if self.orientation == 1:
            return self.edge.internal_linker_atomic_numbers
        return tuple(reversed(self.edge.internal_linker_atomic_numbers))

    @property
    def internal_linker_image_offsets(self) -> tuple[Shift, ...]:
        if self.orientation == 1:
            return self.edge.key.internal_linker_image_offsets
        cumulative = np.zeros(3, dtype=np.int64)
        offsets: list[Shift] = []
        for shift in self.atomic_edge_image_shifts:
            cumulative = cumulative + np.asarray(shift, dtype=np.int64)
            offsets.append(tuple(int(x) for x in cumulative))
        return tuple(offsets[:-1])

    @property
    def rule_id(self) -> str:
        return self.edge.key.rule_id

    @property
    def edge_kind(self) -> str:
        return self.edge.edge_kind

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_key": self.edge.key.to_dict(),
            "orientation": self.orientation,
            "source_vertex": self.source_vertex,
            "target_vertex": self.target_vertex,
            "image_shift": list(self.image_shift),
            "raw_image_shift": list(self.raw_image_shift),
            "atomic_path_indices": list(self.atomic_path_indices),
            "atomic_edge_image_shifts": [
                list(shift) for shift in self.atomic_edge_image_shifts
            ],
            "internal_linker_indices": list(self.internal_linker_indices),
            "internal_linker_atomic_numbers": list(self.internal_linker_atomic_numbers),
            "internal_linker_image_offsets": [
                list(offset) for offset in self.internal_linker_image_offsets
            ],
            "rule_id": self.rule_id,
            "edge_kind": self.edge_kind,
        }


@dataclass(frozen=True, slots=True, eq=False)
class FrameworkProjectionReport:
    """Deterministic diagnostics for role resolution and path contraction."""

    role_counts: Mapping[FrameworkAtomRole, int]
    linker_atom_indices: IntArray
    linker_framework_degree: Int32Array
    linker_used: BoolArray
    candidate_path_count: int
    accepted_edge_count: int
    duplicate_path_count: int
    ignored_atomic_edge_count: int
    parallel_vertex_pair_count: int
    self_image_edge_count: int

    def __post_init__(self) -> None:
        counts = {
            role: _nonnegative_int(
                dict(self.role_counts).get(role, 0), name="role count"
            )
            for role in FrameworkAtomRole
        }
        indices = _readonly_array(self.linker_atom_indices, np.int64, ndim=1)
        degree = _readonly_array(self.linker_framework_degree, np.int32, ndim=1)
        used = _readonly_array(self.linker_used, np.bool_, ndim=1)
        if indices.shape != degree.shape or indices.shape != used.shape:
            raise FrameworkTopologyError("Linker diagnostic arrays must align.")
        if indices.size and np.any(np.diff(indices) <= 0):
            raise FrameworkTopologyError("Linker indices must be sorted and unique.")
        for name in (
            "candidate_path_count",
            "accepted_edge_count",
            "duplicate_path_count",
            "ignored_atomic_edge_count",
            "parallel_vertex_pair_count",
            "self_image_edge_count",
        ):
            object.__setattr__(
                self, name, _nonnegative_int(getattr(self, name), name=name)
            )
        object.__setattr__(self, "role_counts", _freeze_mapping(counts))
        object.__setattr__(self, "linker_atom_indices", indices)
        object.__setattr__(self, "linker_framework_degree", degree)
        object.__setattr__(self, "linker_used", used)

    @property
    def unused_linker_atom_indices(self) -> IntArray:
        return _readonly_array(
            self.linker_atom_indices[~self.linker_used], np.int64, ndim=1
        )

    @property
    def dangling_linker_atom_indices(self) -> IntArray:
        return _readonly_array(
            self.linker_atom_indices[self.linker_framework_degree < 2], np.int64, ndim=1
        )

    @property
    def branching_linker_atom_indices(self) -> IntArray:
        return _readonly_array(
            self.linker_atom_indices[self.linker_framework_degree > 2], np.int64, ndim=1
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FrameworkProjectionReport):
            return NotImplemented
        return self.to_dict() == other.to_dict()

    def to_dict(self) -> dict[str, Any]:
        return {
            "role_counts": {
                role.value: int(self.role_counts[role]) for role in FrameworkAtomRole
            },
            "linker_atom_indices": self.linker_atom_indices.tolist(),
            "linker_framework_degree": self.linker_framework_degree.tolist(),
            "linker_used": self.linker_used.tolist(),
            "candidate_path_count": self.candidate_path_count,
            "accepted_edge_count": self.accepted_edge_count,
            "duplicate_path_count": self.duplicate_path_count,
            "ignored_atomic_edge_count": self.ignored_atomic_edge_count,
            "parallel_vertex_pair_count": self.parallel_vertex_pair_count,
            "self_image_edge_count": self.self_image_edge_count,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkProjectionReport":
        return cls(
            role_counts={
                FrameworkAtomRole(k): int(v) for k, v in payload["role_counts"].items()
            },
            linker_atom_indices=np.asarray(
                payload["linker_atom_indices"], dtype=np.int64
            ),
            linker_framework_degree=np.asarray(
                payload["linker_framework_degree"], dtype=np.int32
            ),
            linker_used=np.asarray(payload["linker_used"], dtype=bool),
            candidate_path_count=int(payload["candidate_path_count"]),
            accepted_edge_count=int(payload["accepted_edge_count"]),
            duplicate_path_count=int(payload["duplicate_path_count"]),
            ignored_atomic_edge_count=int(payload["ignored_atomic_edge_count"]),
            parallel_vertex_pair_count=int(payload["parallel_vertex_pair_count"]),
            self_image_edge_count=int(payload["self_image_edge_count"]),
        )


@dataclass(frozen=True, slots=True)
class FrameworkValidationRules:
    """Optional material-specific checks that never modify topology."""

    allowed_vertex_degrees: Mapping[int, frozenset[int]] = field(default_factory=dict)
    allowed_linker_degrees: Mapping[int, frozenset[int]] = field(default_factory=dict)
    expected_vertex_count: int | None = None
    expected_edge_count: int | None = None
    require_single_component: bool = False
    require_all_linkers_used: bool = False
    allow_parallel_edges: bool = True
    allow_self_image_edges: bool = True
    allowed_edge_kinds: frozenset[str] | None = None

    def __post_init__(self) -> None:
        def normalize_degree_map(
            raw: Mapping[int, frozenset[int]], name: str
        ) -> Mapping[int, frozenset[int]]:
            result: dict[int, frozenset[int]] = {}
            for number, degrees in dict(raw).items():
                z = _atomic_number(number, name=f"{name} atomic number")
                values = frozenset(
                    _nonnegative_int(x, name=f"{name} degree") for x in degrees
                )
                if not values:
                    raise FrameworkTopologyError(f"{name} degree sets cannot be empty.")
                result[z] = values
            return _freeze_mapping(dict(sorted(result.items())))

        object.__setattr__(
            self,
            "allowed_vertex_degrees",
            normalize_degree_map(self.allowed_vertex_degrees, "vertex"),
        )
        object.__setattr__(
            self,
            "allowed_linker_degrees",
            normalize_degree_map(self.allowed_linker_degrees, "linker"),
        )
        if self.expected_vertex_count is not None:
            object.__setattr__(
                self,
                "expected_vertex_count",
                _nonnegative_int(
                    self.expected_vertex_count, name="expected_vertex_count"
                ),
            )
        if self.expected_edge_count is not None:
            object.__setattr__(
                self,
                "expected_edge_count",
                _nonnegative_int(self.expected_edge_count, name="expected_edge_count"),
            )
        if self.allowed_edge_kinds is not None:
            kinds = frozenset(str(x) for x in self.allowed_edge_kinds)
            if not kinds or any(not x for x in kinds):
                raise FrameworkTopologyError(
                    "allowed_edge_kinds must contain nonempty strings."
                )
            object.__setattr__(self, "allowed_edge_kinds", kinds)
        for name in (
            "require_single_component",
            "require_all_linkers_used",
            "allow_parallel_edges",
            "allow_self_image_edges",
        ):
            object.__setattr__(self, name, bool(getattr(self, name)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed_vertex_degrees": {
                str(k): sorted(v) for k, v in self.allowed_vertex_degrees.items()
            },
            "allowed_linker_degrees": {
                str(k): sorted(v) for k, v in self.allowed_linker_degrees.items()
            },
            "expected_vertex_count": self.expected_vertex_count,
            "expected_edge_count": self.expected_edge_count,
            "require_single_component": self.require_single_component,
            "require_all_linkers_used": self.require_all_linkers_used,
            "allow_parallel_edges": self.allow_parallel_edges,
            "allow_self_image_edges": self.allow_self_image_edges,
            "allowed_edge_kinds": None
            if self.allowed_edge_kinds is None
            else sorted(self.allowed_edge_kinds),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkValidationRules":
        return cls(
            allowed_vertex_degrees={
                int(k): frozenset(int(x) for x in v)
                for k, v in payload["allowed_vertex_degrees"].items()
            },
            allowed_linker_degrees={
                int(k): frozenset(int(x) for x in v)
                for k, v in payload["allowed_linker_degrees"].items()
            },
            expected_vertex_count=payload.get("expected_vertex_count"),
            expected_edge_count=payload.get("expected_edge_count"),
            require_single_component=bool(
                payload.get("require_single_component", False)
            ),
            require_all_linkers_used=bool(
                payload.get("require_all_linkers_used", False)
            ),
            allow_parallel_edges=bool(payload.get("allow_parallel_edges", True)),
            allow_self_image_edges=bool(payload.get("allow_self_image_edges", True)),
            allowed_edge_kinds=(
                None
                if payload.get("allowed_edge_kinds") is None
                else frozenset(payload["allowed_edge_kinds"])
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkValidationIssue:
    """One stable machine-readable validation finding."""

    code: str
    severity: Literal["warning", "error"]
    message: str
    atom_indices: tuple[int, ...] = ()
    edge_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code:
            raise FrameworkTopologyError("Validation issue code must be nonempty.")
        if self.severity not in {"warning", "error"}:
            raise FrameworkTopologyError("Validation issue severity is invalid.")
        if not isinstance(self.message, str) or not self.message:
            raise FrameworkTopologyError("Validation issue message must be nonempty.")
        object.__setattr__(
            self,
            "atom_indices",
            tuple(
                sorted(
                    {
                        _nonnegative_int(x, name="issue atom index")
                        for x in self.atom_indices
                    }
                )
            ),
        )
        object.__setattr__(
            self,
            "edge_indices",
            tuple(
                sorted(
                    {
                        _nonnegative_int(x, name="issue edge index")
                        for x in self.edge_indices
                    }
                )
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "atom_indices": list(self.atom_indices),
            "edge_indices": list(self.edge_indices),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkValidationIssue":
        return cls(
            code=str(payload["code"]),
            severity=str(payload["severity"]),  # type: ignore[arg-type]
            message=str(payload["message"]),
            atom_indices=tuple(int(x) for x in payload.get("atom_indices", ())),
            edge_indices=tuple(int(x) for x in payload.get("edge_indices", ())),
        )


@dataclass(frozen=True, slots=True)
class FrameworkValidationReport:
    """Nonmutating validation result for one projected topology."""

    rules: FrameworkValidationRules
    issues: tuple[FrameworkValidationIssue, ...]
    summary_counts: Mapping[str, int]

    def __post_init__(self) -> None:
        if not isinstance(self.rules, FrameworkValidationRules):
            raise FrameworkTopologyError("rules must be FrameworkValidationRules.")
        issues = tuple(self.issues)
        if any(not isinstance(issue, FrameworkValidationIssue) for issue in issues):
            raise FrameworkTopologyError(
                "issues must contain FrameworkValidationIssue objects."
            )
        counts = {
            str(k): _nonnegative_int(v, name="validation summary count")
            for k, v in dict(self.summary_counts).items()
        }
        expected = {
            "total": len(issues),
            "errors": sum(issue.severity == "error" for issue in issues),
            "warnings": sum(issue.severity == "warning" for issue in issues),
        }
        expected.update(Counter(issue.code for issue in issues))
        if counts != expected:
            raise FrameworkTopologyError(
                "Validation summary_counts disagree with validation issues."
            )
        object.__setattr__(self, "issues", issues)
        object.__setattr__(
            self, "summary_counts", _freeze_mapping(dict(sorted(counts.items())))
        )

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def raise_for_errors(self) -> None:
        errors = [issue for issue in self.issues if issue.severity == "error"]
        if errors:
            counts = Counter(issue.code for issue in errors)
            summary = ", ".join(
                f"{code}={count}" for code, count in sorted(counts.items())
            )
            raise FrameworkValidationError(f"Framework validation failed: {summary}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "rules": self.rules.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
            "summary_counts": dict(self.summary_counts),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkValidationReport":
        return cls(
            rules=FrameworkValidationRules.from_dict(payload["rules"]),
            issues=tuple(
                FrameworkValidationIssue.from_dict(x) for x in payload["issues"]
            ),
            summary_counts={
                str(k): int(v) for k, v in payload["summary_counts"].items()
            },
        )


def _component_data(
    vertices: Sequence[int], edges: Sequence[FrameworkEdgePath]
) -> tuple[Int32Array, int, Int32Array]:
    positions = {atom: i for i, atom in enumerate(vertices)}
    adjacency: dict[int, set[int]] = {atom: set() for atom in vertices}
    degree = np.zeros(len(vertices), dtype=np.int32)
    for edge in edges:
        i, j = edge.key.vertex_i, edge.key.vertex_j
        if i == j:
            degree[positions[i]] += 2
        else:
            degree[positions[i]] += 1
            degree[positions[j]] += 1
            adjacency[i].add(j)
            adjacency[j].add(i)
    labels_by_atom: dict[int, int] = {}
    component = 0
    for root in vertices:
        if root in labels_by_atom:
            continue
        labels_by_atom[root] = component
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency[current]):
                if neighbor not in labels_by_atom:
                    labels_by_atom[neighbor] = component
                    queue.append(neighbor)
        component += 1
    labels = np.asarray([labels_by_atom[atom] for atom in vertices], dtype=np.int32)
    return labels, component, degree


def _graph_digest(
    vertices: IntArray,
    numbers: Int32Array,
    pbc: BoolArray,
    edges: Sequence[FrameworkEdgePath],
) -> str:
    return _digest(
        {
            "canonical_schema_version": CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA,
            "pbc": [bool(x) for x in pbc],
            "vertices": [
                [int(i), int(z)] for i, z in zip(vertices, numbers, strict=True)
            ],
            "edge_keys": [edge.key.to_dict() for edge in edges],
        }
    )


@dataclass(frozen=True, slots=True, eq=False)
class FrameworkTopology:
    """Immutable periodic decorated multigraph produced from one atomic state."""

    vertex_atom_indices: IntArray
    vertex_atomic_numbers: Int32Array
    pbc: BoolArray
    edges: tuple[FrameworkEdgePath, ...]
    degree: Int32Array
    component_labels: Int32Array
    n_components: int
    resolved_roles: ResolvedFrameworkRoles
    projection_report: FrameworkProjectionReport
    validation: FrameworkValidationReport | None
    source_connectivity_digest: str
    mapping_digest: str
    canonical_schema_version: str = CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA
    digest_algorithm: str = FRAMEWORK_DIGEST_ALGORITHM
    graph_digest: str = ""
    digest: str = ""

    def __post_init__(self) -> None:
        vertices = _readonly_array(self.vertex_atom_indices, np.int64, ndim=1)
        numbers = _readonly_array(self.vertex_atomic_numbers, np.int32, ndim=1)
        pbc = _readonly_array(self.pbc, np.bool_, ndim=1)
        degree = _readonly_array(self.degree, np.int32, ndim=1)
        labels = _readonly_array(self.component_labels, np.int32, ndim=1)
        edges = tuple(self.edges)
        if vertices.size == 0 or np.any(np.diff(vertices) <= 0):
            raise FrameworkTopologyError(
                "Framework vertices must be nonempty and sorted."
            )
        if (
            numbers.shape != vertices.shape
            or degree.shape != vertices.shape
            or labels.shape != vertices.shape
        ):
            raise FrameworkTopologyError("Framework vertex arrays must align.")
        if pbc.shape != (3,):
            raise FrameworkTopologyError("pbc must have shape (3,).")
        if any(not isinstance(edge, FrameworkEdgePath) for edge in edges):
            raise FrameworkTopologyError(
                "edges must contain FrameworkEdgePath objects."
            )
        if [edge.key for edge in edges] != sorted(edge.key for edge in edges):
            raise FrameworkTopologyError(
                "Projected edge records must be sorted by canonical key."
            )
        if len({edge.key for edge in edges}) != len(edges):
            raise FrameworkTopologyError(
                "Exact duplicate projected edge keys are forbidden."
            )
        vertex_set = set(int(x) for x in vertices)
        for edge in edges:
            if (
                edge.key.vertex_i not in vertex_set
                or edge.key.vertex_j not in vertex_set
            ):
                raise FrameworkTopologyError(
                    "Projected edge endpoint is not a framework vertex."
                )
            if any(edge.key.image_shift[k] != 0 for k in range(3) if not bool(pbc[k])):
                raise FrameworkTopologyError(
                    "Projected shift is nonzero on a nonperiodic axis."
                )
        expected_labels, expected_components, expected_degree = _component_data(
            tuple(int(x) for x in vertices), edges
        )
        if not np.array_equal(degree, expected_degree):
            raise FrameworkTopologyError("Stored framework degree is inconsistent.")
        if (
            not np.array_equal(labels, expected_labels)
            or int(self.n_components) != expected_components
        ):
            raise FrameworkTopologyError(
                "Stored framework components are inconsistent."
            )
        if not isinstance(self.resolved_roles, ResolvedFrameworkRoles):
            raise FrameworkTopologyError("resolved_roles has the wrong type.")
        if not np.array_equal(vertices, self.resolved_roles.vertex_atom_indices):
            raise FrameworkTopologyError(
                "Framework vertices disagree with resolved VERTEX roles."
            )
        active_number_by_atom = {
            int(atom): int(number)
            for atom, number in zip(
                self.resolved_roles.active_atom_indices,
                self.resolved_roles.active_atomic_numbers,
                strict=True,
            )
        }
        expected_numbers = np.asarray(
            [active_number_by_atom[int(atom)] for atom in vertices], dtype=np.int32
        )
        if not np.array_equal(numbers, expected_numbers):
            raise FrameworkTopologyError(
                "Framework vertex atomic numbers disagree with resolved roles."
            )
        linker_set = set(int(x) for x in self.resolved_roles.linker_atom_indices)
        for edge in edges:
            if any(
                index not in linker_set for index in edge.key.internal_linker_indices
            ):
                raise FrameworkTopologyError(
                    "Projected edge contains an atom not resolved as LINKER."
                )
            expected_linker_numbers = tuple(
                active_number_by_atom[index]
                for index in edge.key.internal_linker_indices
            )
            if edge.internal_linker_atomic_numbers != expected_linker_numbers:
                raise FrameworkTopologyError(
                    "Projected linker atomic numbers disagree with resolved roles."
                )
            if any(
                shift[axis] != 0
                for shift in (*edge.atomic_edge_image_shifts, edge.raw_image_shift)
                for axis in range(3)
                if not bool(pbc[axis])
            ):
                raise FrameworkTopologyError(
                    "Atomic path shift is nonzero on a nonperiodic axis."
                )
        if not isinstance(self.projection_report, FrameworkProjectionReport):
            raise FrameworkTopologyError("projection_report has the wrong type.")
        if not np.array_equal(
            self.projection_report.linker_atom_indices,
            self.resolved_roles.linker_atom_indices,
        ):
            raise FrameworkTopologyError(
                "Projection report linker indices disagree with resolved roles."
            )
        if self.projection_report.accepted_edge_count != len(edges):
            raise FrameworkTopologyError(
                "Projection report edge count disagrees with topology."
            )
        expected_role_counts = Counter(self.resolved_roles.roles)
        if any(
            self.projection_report.role_counts[role] != expected_role_counts[role]
            for role in FrameworkAtomRole
        ):
            raise FrameworkTopologyError(
                "Projection report role counts disagree with resolved roles."
            )
        if self.validation is not None and not isinstance(
            self.validation, FrameworkValidationReport
        ):
            raise FrameworkTopologyError("validation has the wrong type.")
        if self.mapping_digest != self.resolved_roles.mapping_digest:
            raise FrameworkTopologyError(
                "mapping_digest disagrees with resolved roles."
            )
        if (
            not isinstance(self.source_connectivity_digest, str)
            or len(self.source_connectivity_digest) != 64
        ):
            raise FrameworkTopologyError(
                "source_connectivity_digest must be a SHA-256 digest."
            )
        if self.canonical_schema_version != CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA:
            raise FrameworkTopologyError(
                "Unsupported framework-topology schema version."
            )
        if self.digest_algorithm != FRAMEWORK_DIGEST_ALGORITHM:
            raise FrameworkTopologyError("Unsupported framework digest algorithm.")
        expected_graph = _graph_digest(vertices, numbers, pbc, edges)
        graph_digest = self.graph_digest or expected_graph
        if graph_digest != expected_graph:
            raise FrameworkTopologyError(
                "Stored framework graph digest is inconsistent."
            )
        expected_digest = _digest(
            {"graph_digest": graph_digest, "mapping_digest": self.mapping_digest}
        )
        topology_digest = self.digest or expected_digest
        if topology_digest != expected_digest:
            raise FrameworkTopologyError(
                "Stored framework topology digest is inconsistent."
            )
        object.__setattr__(self, "vertex_atom_indices", vertices)
        object.__setattr__(self, "vertex_atomic_numbers", numbers)
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "degree", degree)
        object.__setattr__(self, "component_labels", labels)
        object.__setattr__(self, "n_components", expected_components)
        object.__setattr__(self, "graph_digest", graph_digest)
        object.__setattr__(self, "digest", topology_digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FrameworkTopology):
            return NotImplemented
        return (
            self.canonical_schema_version == other.canonical_schema_version
            and self.mapping_digest == other.mapping_digest
            and np.array_equal(self.vertex_atom_indices, other.vertex_atom_indices)
            and np.array_equal(self.vertex_atomic_numbers, other.vertex_atomic_numbers)
            and np.array_equal(self.pbc, other.pbc)
            and self.edges == other.edges
        )

    def __hash__(self) -> int:
        return int(self.digest[:16], 16)

    @property
    def n_vertices(self) -> int:
        return int(self.vertex_atom_indices.size)

    @property
    def n_edges(self) -> int:
        return len(self.edges)

    @property
    def edge_keys(self) -> tuple[FrameworkEdgeKey, ...]:
        return tuple(edge.key for edge in self.edges)

    def degree_for_atom(self, atom_index: int) -> int:
        index = _nonnegative_int(atom_index, name="atom_index")
        position = int(np.searchsorted(self.vertex_atom_indices, index))
        if (
            position >= self.n_vertices
            or int(self.vertex_atom_indices[position]) != index
        ):
            raise KeyError(f"Atom {index} is not a framework vertex.")
        return int(self.degree[position])

    def edges_for_atom(self, atom_index: int) -> tuple[FrameworkEdgePath, ...]:
        index = _nonnegative_int(atom_index, name="atom_index")
        if index not in set(int(x) for x in self.vertex_atom_indices):
            raise KeyError(f"Atom {index} is not a framework vertex.")
        return tuple(
            edge
            for edge in self.edges
            if index in (edge.key.vertex_i, edge.key.vertex_j)
        )

    def to_networkx(self) -> Any:
        """Return a derived NetworkX MultiGraph without defining identity."""
        import networkx as nx

        graph = nx.MultiGraph()
        for atom, number, degree, component in zip(
            self.vertex_atom_indices,
            self.vertex_atomic_numbers,
            self.degree,
            self.component_labels,
            strict=True,
        ):
            graph.add_node(
                int(atom),
                atom_index=int(atom),
                atomic_number=int(number),
                symbol=chemical_symbols[int(number)],
                degree=int(degree),
                component_id=int(component),
            )
        for edge_index, edge in enumerate(self.edges):
            graph.add_edge(
                edge.key.vertex_i,
                edge.key.vertex_j,
                key=edge_index,
                edge_index=edge_index,
                rule_id=edge.key.rule_id,
                edge_kind=edge.edge_kind,
                image_shift=edge.key.image_shift,
                raw_image_shift=edge.raw_image_shift,
                internal_linker_indices=edge.key.internal_linker_indices,
                internal_linker_atomic_numbers=edge.internal_linker_atomic_numbers,
                atomic_path_indices=edge.atomic_path_indices,
                reverse_atomic_path_indices=tuple(reversed(edge.atomic_path_indices)),
                atomic_edge_image_shifts=edge.atomic_edge_image_shifts,
                reverse_atomic_edge_image_shifts=edge.oriented(
                    -1
                ).atomic_edge_image_shifts,
                orientation_aware=True,
                canonical_orientation="vertex_i_to_vertex_j",
            )
        graph.graph.update(
            graph_digest=self.graph_digest,
            digest=self.digest,
            mapping_digest=self.mapping_digest,
            pbc=tuple(bool(x) for x in self.pbc),
            canonical_schema_version=self.canonical_schema_version,
        )
        return graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "vertex_atom_indices": self.vertex_atom_indices.tolist(),
            "vertex_atomic_numbers": self.vertex_atomic_numbers.tolist(),
            "pbc": self.pbc.tolist(),
            "edges": [edge.to_dict() for edge in self.edges],
            "degree": self.degree.tolist(),
            "component_labels": self.component_labels.tolist(),
            "n_components": self.n_components,
            "resolved_roles": self.resolved_roles.to_dict(),
            "projection_report": self.projection_report.to_dict(),
            "validation": None
            if self.validation is None
            else self.validation.to_dict(),
            "source_connectivity_digest": self.source_connectivity_digest,
            "mapping_digest": self.mapping_digest,
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "graph_digest": self.graph_digest,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkTopology":
        return cls(
            vertex_atom_indices=np.asarray(
                payload["vertex_atom_indices"], dtype=np.int64
            ),
            vertex_atomic_numbers=np.asarray(
                payload["vertex_atomic_numbers"], dtype=np.int32
            ),
            pbc=np.asarray(payload["pbc"], dtype=bool),
            edges=tuple(FrameworkEdgePath.from_dict(x) for x in payload["edges"]),
            degree=np.asarray(payload["degree"], dtype=np.int32),
            component_labels=np.asarray(payload["component_labels"], dtype=np.int32),
            n_components=int(payload["n_components"]),
            resolved_roles=ResolvedFrameworkRoles.from_dict(payload["resolved_roles"]),
            projection_report=FrameworkProjectionReport.from_dict(
                payload["projection_report"]
            ),
            validation=(
                None
                if payload.get("validation") is None
                else FrameworkValidationReport.from_dict(payload["validation"])
            ),
            source_connectivity_digest=str(payload["source_connectivity_digest"]),
            mapping_digest=str(payload["mapping_digest"]),
            canonical_schema_version=str(payload["canonical_schema_version"]),
            digest_algorithm=str(payload["digest_algorithm"]),
            graph_digest=str(payload["graph_digest"]),
            digest=str(payload["digest"]),
        )


def _oriented_adjacency(
    state: AtomicConnectivityState,
    active_to_role: Mapping[int, FrameworkAtomRole],
) -> dict[int, list[tuple[int, Shift]]]:
    """Return a deterministic framework-relevant atomic gauge.

    The source atomic state is canonical for its full active scope. Adding
    spectator contacts can legitimately change that full-graph gauge. Framework
    projection therefore re-normalizes only the VERTEX/LINKER induced subgraph
    before path traversal. This preserves the same physical framework graph and
    path-local linker images when spectator-only connectivity is added.
    """
    relevant = tuple(
        sorted(
            atom
            for atom, role in active_to_role.items()
            if role in {FrameworkAtomRole.VERTEX, FrameworkAtomRole.LINKER}
        )
    )
    relevant_set = set(relevant)
    raw_edges: list[tuple[int, int, Shift]] = []
    raw_adjacency: dict[int, list[tuple[int, Shift]]] = {atom: [] for atom in relevant}
    for endpoints, raw_shift in zip(
        state.edge_atom_indices, state.edge_image_shifts, strict=True
    ):
        i, j = int(endpoints[0]), int(endpoints[1])
        if i not in relevant_set or j not in relevant_set:
            continue
        shift = tuple(int(x) for x in raw_shift)
        raw_edges.append((i, j, shift))
        raw_adjacency[i].append((j, shift))
        raw_adjacency[j].append((i, tuple(-x for x in shift)))
    for atom in raw_adjacency:
        raw_adjacency[atom].sort(key=lambda item: (item[0], *item[1]))

    gauge: dict[int, np.ndarray] = {}
    for root in relevant:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, shift in raw_adjacency[current]:
                if neighbor in gauge:
                    continue
                gauge[neighbor] = gauge[current] + np.asarray(shift, dtype=np.int64)
                queue.append(neighbor)

    adjacency: dict[int, list[tuple[int, Shift]]] = {atom: [] for atom in relevant}
    for i, j, raw_shift in raw_edges:
        normalized = np.asarray(raw_shift, dtype=np.int64) + gauge[i] - gauge[j]
        shift = tuple(int(x) for x in normalized)
        adjacency[i].append((j, shift))
        adjacency[j].append((i, tuple(-x for x in shift)))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], *item[1]))
    return adjacency


def _reverse_path(
    path: tuple[int, ...],
    steps: tuple[Shift, ...],
) -> tuple[tuple[int, ...], tuple[Shift, ...]]:
    return tuple(reversed(path)), tuple(
        tuple(-x for x in shift) for shift in reversed(steps)
    )


def _path_offsets(steps: Sequence[Shift]) -> tuple[Shift, ...]:
    current = np.zeros(3, dtype=np.int64)
    offsets: list[Shift] = [(0, 0, 0)]
    for shift in steps:
        current = current + np.asarray(shift, dtype=np.int64)
        offsets.append(tuple(int(x) for x in current))
    return tuple(offsets)


def _canonical_path(
    path: tuple[int, ...],
    steps: tuple[Shift, ...],
    internal_numbers: tuple[int, ...],
    rule: FrameworkPathRule,
) -> FrameworkEdgePath:
    def make(
        candidate_path: tuple[int, ...],
        candidate_steps: tuple[Shift, ...],
        candidate_numbers: tuple[int, ...],
    ) -> FrameworkEdgePath:
        offsets = _path_offsets(candidate_steps)
        raw = offsets[-1]
        key = FrameworkEdgeKey(
            vertex_i=candidate_path[0],
            vertex_j=candidate_path[-1],
            image_shift=raw,
            internal_linker_indices=candidate_path[1:-1],
            internal_linker_image_offsets=offsets[1:-1],
            rule_id=rule.rule_id,
        )
        return FrameworkEdgePath(
            key=key,
            atomic_path_indices=candidate_path,
            atomic_edge_image_shifts=candidate_steps,
            internal_linker_atomic_numbers=candidate_numbers,
            raw_image_shift=raw,
            edge_kind=rule.edge_kind,
        )

    if path[0] < path[-1]:
        return make(path, steps, internal_numbers)
    reversed_path, reversed_steps = _reverse_path(path, steps)
    reversed_numbers = tuple(reversed(internal_numbers))
    if path[0] > path[-1]:
        return make(reversed_path, reversed_steps, reversed_numbers)
    forward = make(path, steps, internal_numbers)
    backward = make(reversed_path, reversed_steps, reversed_numbers)
    forward_record = (
        forward.key.image_shift,
        forward.key.internal_linker_indices,
        forward.key.internal_linker_image_offsets,
        forward.atomic_edge_image_shifts,
    )
    backward_record = (
        backward.key.image_shift,
        backward.key.internal_linker_indices,
        backward.key.internal_linker_image_offsets,
        backward.atomic_edge_image_shifts,
    )
    return min(
        (forward_record, forward), (backward_record, backward), key=lambda x: x[0]
    )[1]


def _normalize_framework_gauge(
    vertices: Sequence[int],
    provisional: Sequence[FrameworkEdgePath],
) -> tuple[FrameworkEdgePath, ...]:
    adjacency: dict[int, list[tuple[int, Shift, FrameworkEdgeKey]]] = {
        atom: [] for atom in vertices
    }
    for edge in provisional:
        i, j = edge.key.vertex_i, edge.key.vertex_j
        if i == j:
            continue
        shift = edge.raw_image_shift
        adjacency[i].append((j, shift, edge.key))
        adjacency[j].append((i, tuple(-x for x in shift), edge.key))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], *item[1], item[2]))
    gauge: dict[int, np.ndarray] = {}
    for root in vertices:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, directed_shift, _ in adjacency[current]:
                if neighbor in gauge:
                    continue
                gauge[neighbor] = gauge[current] + np.asarray(
                    directed_shift, dtype=np.int64
                )
                queue.append(neighbor)
    normalized: list[FrameworkEdgePath] = []
    for edge in provisional:
        key = edge.key
        shift = (
            np.asarray(edge.raw_image_shift, dtype=np.int64)
            + gauge[key.vertex_i]
            - gauge[key.vertex_j]
        )
        normalized_key = replace(key, image_shift=tuple(int(x) for x in shift))
        normalized.append(replace(edge, key=normalized_key))
    normalized.sort(key=lambda edge: edge.key)
    if len({edge.key for edge in normalized}) != len(normalized):
        raise FrameworkProjectionError(
            "Framework gauge normalization produced duplicate edge keys."
        )
    return tuple(normalized)


def _rules_by_sequence(
    mapping: FrameworkMapping,
) -> tuple[
    dict[tuple[int, ...], tuple[FrameworkPathRule, ...]], frozenset[tuple[int, ...]]
]:
    exact: dict[tuple[int, ...], list[FrameworkPathRule]] = defaultdict(list)
    prefixes: set[tuple[int, ...]] = {()}
    for rule in mapping.path_rules:
        for sequence in rule.accepted_sequences:
            exact[sequence].append(rule)
            for length in range(len(sequence) + 1):
                prefixes.add(sequence[:length])
    return (
        {
            sequence: tuple(sorted(rules, key=lambda rule: rule.rule_id))
            for sequence, rules in exact.items()
        },
        frozenset(prefixes),
    )


def build_framework_topology(
    state: AtomicConnectivityState,
    mapping: FrameworkMapping,
    *,
    validation_rules: FrameworkValidationRules | None = None,
    options: FrameworkProjectionOptions | None = None,
) -> FrameworkTopology:
    """Project one atomic connectivity state into an immutable framework graph."""
    if not isinstance(state, AtomicConnectivityState):
        raise TypeError("state must be an AtomicConnectivityState.")
    if not isinstance(mapping, FrameworkMapping):
        raise TypeError("mapping must be a FrameworkMapping.")
    if validation_rules is not None and not isinstance(
        validation_rules, FrameworkValidationRules
    ):
        raise TypeError("validation_rules must be FrameworkValidationRules or None.")
    limits = options or FrameworkProjectionOptions()
    if not isinstance(limits, FrameworkProjectionOptions):
        raise TypeError("options must be FrameworkProjectionOptions or None.")
    if mapping.max_linker_atoms > limits.max_linker_atoms:
        raise FrameworkComplexityError(
            "Mapping linker length exceeds max_linker_atoms before traversal."
        )
    if limits.max_linker_atoms == 0 and mapping.max_linker_atoms > 0:
        raise FrameworkComplexityError(
            "max_linker_atoms=0 is valid only for direct-edge mappings."
        )
    roles = resolve_framework_roles(state, mapping)
    if roles.vertex_atom_indices.size == 0:
        raise FrameworkMappingError("Framework projection resolved zero vertices.")
    active_to_role = {
        int(atom): role
        for atom, role in zip(roles.active_atom_indices, roles.roles, strict=True)
    }
    active_to_number = {
        int(atom): int(number)
        for atom, number in zip(
            roles.active_atom_indices, roles.active_atomic_numbers, strict=True
        )
    }
    adjacency = _oriented_adjacency(state, active_to_role)
    exact_rules, accepted_prefixes = _rules_by_sequence(mapping)

    linker_positions = {
        int(atom): i for i, atom in enumerate(roles.linker_atom_indices)
    }
    linker_degree = np.zeros(roles.linker_atom_indices.size, dtype=np.int32)
    ignored_atomic_edges = 0
    for endpoints in state.edge_atom_indices:
        i, j = int(endpoints[0]), int(endpoints[1])
        role_i, role_j = active_to_role[i], active_to_role[j]
        if role_i in {
            FrameworkAtomRole.SPECTATOR,
            FrameworkAtomRole.EXCLUDED,
        } or role_j in {FrameworkAtomRole.SPECTATOR, FrameworkAtomRole.EXCLUDED}:
            ignored_atomic_edges += 1
        if role_i is FrameworkAtomRole.LINKER and role_j in {
            FrameworkAtomRole.VERTEX,
            FrameworkAtomRole.LINKER,
        }:
            linker_degree[linker_positions[i]] += 1
        if role_j is FrameworkAtomRole.LINKER and role_i in {
            FrameworkAtomRole.VERTEX,
            FrameworkAtomRole.LINKER,
        }:
            linker_degree[linker_positions[j]] += 1

    accepted: dict[tuple[Any, ...], FrameworkEdgePath] = {}
    candidate_count = 0
    duplicate_count = 0
    for source in (int(x) for x in roles.vertex_atom_indices):
        stack: list[
            tuple[
                int,
                Shift,
                tuple[int, ...],
                tuple[Shift, ...],
                tuple[int, ...],
                frozenset[tuple[int, Shift]],
            ]
        ] = [(source, (0, 0, 0), (source,), (), (), frozenset({(source, (0, 0, 0))}))]
        while stack:
            current, current_offset, path, steps, linker_numbers, visited = stack.pop()
            next_states: list[tuple[int, Shift]] = []
            for neighbor, shift in adjacency[current]:
                next_offset_arr = np.asarray(
                    current_offset, dtype=np.int64
                ) + np.asarray(shift, dtype=np.int64)
                next_offset = tuple(int(x) for x in next_offset_arr)
                next_states.append((neighbor, next_offset))
            # Reverse insertion makes the LIFO stack visit sorted adjacency first.
            for (neighbor, next_offset), (_, shift) in reversed(
                list(zip(next_states, adjacency[current], strict=True))
            ):
                role = active_to_role[neighbor]
                if role in {FrameworkAtomRole.SPECTATOR, FrameworkAtomRole.EXCLUDED}:
                    continue
                candidate_count += 1
                if candidate_count > limits.max_candidate_paths:
                    raise FrameworkComplexityError(
                        "Lifted framework candidate-path limit exceeded."
                    )
                new_path = (*path, neighbor)
                new_steps = (*steps, shift)
                lifted = (neighbor, next_offset)
                if role is FrameworkAtomRole.VERTEX:
                    if neighbor == source and next_offset == (0, 0, 0):
                        continue
                    rules = exact_rules.get(linker_numbers, ())
                    endpoint_rules = [
                        rule
                        for rule in rules
                        if rule.accepts_path(
                            active_to_number[source],
                            linker_numbers,
                            active_to_number[neighbor],
                        )
                    ]
                    if len(endpoint_rules) > 1:
                        raise FrameworkMappingError(
                            "More than one path rule accepted one terminal path."
                        )
                    if not endpoint_rules:
                        continue
                    edge = _canonical_path(
                        new_path, new_steps, linker_numbers, endpoint_rules[0]
                    )
                    record = (
                        edge.key.vertex_i,
                        edge.key.vertex_j,
                        edge.raw_image_shift,
                        edge.key.internal_linker_indices,
                        edge.key.internal_linker_image_offsets,
                        edge.key.rule_id,
                        edge.atomic_edge_image_shifts,
                    )
                    if record in accepted:
                        duplicate_count += 1
                    else:
                        if len(accepted) >= limits.max_projected_edges:
                            raise FrameworkComplexityError(
                                "Projected framework-edge limit exceeded."
                            )
                        accepted[record] = edge
                    continue
                assert role is FrameworkAtomRole.LINKER
                if len(linker_numbers) >= limits.max_linker_atoms:
                    continue
                if lifted in visited:
                    continue
                new_numbers = (*linker_numbers, active_to_number[neighbor])
                if new_numbers not in accepted_prefixes:
                    continue
                stack.append(
                    (
                        neighbor,
                        next_offset,
                        new_path,
                        new_steps,
                        new_numbers,
                        visited | {lifted},
                    )
                )

    provisional = tuple(
        sorted(
            accepted.values(),
            key=lambda edge: (
                edge.key.vertex_i,
                edge.key.vertex_j,
                edge.raw_image_shift,
                edge.key.internal_linker_indices,
                edge.key.internal_linker_image_offsets,
                edge.key.rule_id,
            ),
        )
    )
    edges = _normalize_framework_gauge(
        tuple(int(x) for x in roles.vertex_atom_indices), provisional
    )
    vertex_numbers = np.asarray(
        [active_to_number[int(atom)] for atom in roles.vertex_atom_indices],
        dtype=np.int32,
    )
    component_labels, n_components, degree = _component_data(
        tuple(int(x) for x in roles.vertex_atom_indices), edges
    )
    used_linkers = {
        linker for edge in edges for linker in edge.key.internal_linker_indices
    }
    linker_used = np.asarray(
        [int(atom) in used_linkers for atom in roles.linker_atom_indices], dtype=bool
    )
    pair_counts = Counter((edge.key.vertex_i, edge.key.vertex_j) for edge in edges)
    report = FrameworkProjectionReport(
        role_counts=Counter(roles.roles),
        linker_atom_indices=roles.linker_atom_indices,
        linker_framework_degree=linker_degree,
        linker_used=linker_used,
        candidate_path_count=candidate_count,
        accepted_edge_count=len(edges),
        duplicate_path_count=duplicate_count,
        ignored_atomic_edge_count=ignored_atomic_edges,
        parallel_vertex_pair_count=sum(
            1 for count in pair_counts.values() if count > 1
        ),
        self_image_edge_count=sum(
            1 for edge in edges if edge.key.vertex_i == edge.key.vertex_j
        ),
    )
    topology = FrameworkTopology(
        vertex_atom_indices=roles.vertex_atom_indices,
        vertex_atomic_numbers=vertex_numbers,
        pbc=state.pbc,
        edges=edges,
        degree=degree,
        component_labels=component_labels,
        n_components=n_components,
        resolved_roles=roles,
        projection_report=report,
        validation=None,
        source_connectivity_digest=state.digest,
        mapping_digest=mapping.digest,
    )
    if validation_rules is not None:
        validation = validate_framework_topology(topology, validation_rules)
        topology = replace(topology, validation=validation)
    return topology


def validate_framework_topology(
    topology: FrameworkTopology,
    rules: FrameworkValidationRules,
) -> FrameworkValidationReport:
    """Validate a framework topology without mutating or repairing it."""
    if not isinstance(topology, FrameworkTopology):
        raise TypeError("topology must be a FrameworkTopology.")
    if not isinstance(rules, FrameworkValidationRules):
        raise TypeError("rules must be FrameworkValidationRules.")
    issues: list[FrameworkValidationIssue] = []

    def add(
        code: str, message: str, *, atoms: Iterable[int] = (), edges: Iterable[int] = ()
    ) -> None:
        issues.append(
            FrameworkValidationIssue(
                code=code,
                severity="error",
                message=message,
                atom_indices=tuple(atoms),
                edge_indices=tuple(edges),
            )
        )

    if (
        rules.expected_vertex_count is not None
        and topology.n_vertices != rules.expected_vertex_count
    ):
        add(
            "unexpected_vertex_count",
            f"Expected {rules.expected_vertex_count} vertices; found {topology.n_vertices}.",
            atoms=topology.vertex_atom_indices,
        )
    if (
        rules.expected_edge_count is not None
        and topology.n_edges != rules.expected_edge_count
    ):
        add(
            "unexpected_edge_count",
            f"Expected {rules.expected_edge_count} edges; found {topology.n_edges}.",
            edges=range(topology.n_edges),
        )
    for position, (atom, number, degree) in enumerate(
        zip(
            topology.vertex_atom_indices,
            topology.vertex_atomic_numbers,
            topology.degree,
            strict=True,
        )
    ):
        allowed = rules.allowed_vertex_degrees.get(int(number))
        if allowed is not None and int(degree) not in allowed:
            add(
                "invalid_vertex_degree",
                f"Atom {int(atom)} has projected degree {int(degree)}; allowed={sorted(allowed)}.",
                atoms=(int(atom),),
            )
    active_number = {
        int(atom): int(number)
        for atom, number in zip(
            topology.resolved_roles.active_atom_indices,
            topology.resolved_roles.active_atomic_numbers,
            strict=True,
        )
    }
    for atom, degree in zip(
        topology.projection_report.linker_atom_indices,
        topology.projection_report.linker_framework_degree,
        strict=True,
    ):
        allowed = rules.allowed_linker_degrees.get(active_number[int(atom)])
        if allowed is not None and int(degree) not in allowed:
            add(
                "invalid_linker_degree",
                f"Linker atom {int(atom)} has framework-relevant atomic degree {int(degree)}; allowed={sorted(allowed)}.",
                atoms=(int(atom),),
            )
    if rules.require_single_component and topology.n_components != 1:
        add(
            "disconnected_framework",
            f"Framework has {topology.n_components} connected components.",
            atoms=topology.vertex_atom_indices,
        )
    if rules.require_all_linkers_used:
        unused = topology.projection_report.unused_linker_atom_indices
        if unused.size:
            add(
                "unused_linker",
                f"{unused.size} resolved linker atoms are unused.",
                atoms=unused,
            )
    pair_to_edges: dict[tuple[int, int], list[int]] = defaultdict(list)
    for edge_index, edge in enumerate(topology.edges):
        pair_to_edges[(edge.key.vertex_i, edge.key.vertex_j)].append(edge_index)
    if not rules.allow_parallel_edges:
        for pair, edge_indices in sorted(pair_to_edges.items()):
            if len(edge_indices) > 1:
                add(
                    "parallel_edge_not_allowed",
                    f"Vertex pair {pair} has {len(edge_indices)} projected edges.",
                    atoms=pair,
                    edges=edge_indices,
                )
    if not rules.allow_self_image_edges:
        for edge_index, edge in enumerate(topology.edges):
            if edge.key.vertex_i == edge.key.vertex_j:
                add(
                    "self_image_edge_not_allowed",
                    f"Projected edge {edge_index} is a self-image edge.",
                    atoms=(edge.key.vertex_i,),
                    edges=(edge_index,),
                )
    if rules.allowed_edge_kinds is not None:
        for edge_index, edge in enumerate(topology.edges):
            if edge.edge_kind not in rules.allowed_edge_kinds:
                add(
                    "unexpected_edge_kind",
                    f"Projected edge {edge_index} has edge kind {edge.edge_kind!r}.",
                    atoms=(edge.key.vertex_i, edge.key.vertex_j),
                    edges=(edge_index,),
                )
    code_counts = Counter(issue.code for issue in issues)
    summary: dict[str, int] = {
        "total": len(issues),
        "errors": sum(issue.severity == "error" for issue in issues),
        "warnings": sum(issue.severity == "warning" for issue in issues),
    }
    summary.update(code_counts)
    return FrameworkValidationReport(
        rules=rules, issues=tuple(issues), summary_counts=summary
    )


__all__ = [
    "CANONICAL_FRAMEWORK_MAPPING_SCHEMA",
    "CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA",
    "FRAMEWORK_DIGEST_ALGORITHM",
    "FrameworkAtomRole",
    "FrameworkComplexityError",
    "FrameworkEdgeKey",
    "FrameworkEdgePath",
    "OrientedFrameworkEdgePath",
    "FrameworkMapping",
    "FrameworkMappingError",
    "FrameworkPathRule",
    "FrameworkProjectionError",
    "FrameworkProjectionOptions",
    "FrameworkProjectionReport",
    "FrameworkTopology",
    "FrameworkTopologyError",
    "FrameworkValidationError",
    "FrameworkValidationIssue",
    "FrameworkValidationReport",
    "FrameworkValidationRules",
    "ResolvedFrameworkRoles",
    "build_framework_topology",
    "resolve_framework_roles",
    "validate_framework_topology",
]
