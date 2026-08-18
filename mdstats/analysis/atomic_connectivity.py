"""Periodic atomic connectivity for fixed-population frame collections.

This public module converts geometric pair information into explicit, auditable
atomic graph states.  It deliberately separates three ideas:

* :class:`ConnectivityScope` selects a persistent atom population;
* a connectivity definition states when an atomic edge exists;
* canonical connectivity states describe the resulting periodic graph.

Framework roles, linker contraction, rings, and dynamic spatial regions belong
to later analysis layers.
"""

from __future__ import annotations

import hashlib
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import Counter, deque
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Literal, TypeAlias

import numpy as np
from ase.data import chemical_symbols
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from ._neighbors import PairCounting
from ._verlet_cache import VerletCacheOptions
from .neighbor_search import NeighborSearchOptions, _NeighborSearchExecutor
from .cutoffs import PairCutoffRegistry, coerce_cutoff_registry
from .selection import Species, _atomic_number

IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]

CANONICAL_CONNECTIVITY_SCHEMA = "mdstats.atomic-connectivity.v1"
CONNECTIVITY_DIGEST_ALGORITHM = "sha256"
ATOMIC_CONNECTIVITY_GEOMETRY_CACHE_SCHEMA = "mdstats.atomic-connectivity-geometry-cache.v1"
_STATE_BUILD_CACHE_MAX_ENTRIES = 512


class AtomicConnectivityGeometryCache:
    """Thread-safe cache of exact per-frame neighbor geometry requests.

    The cache is intentionally execution-local and stores only exact neighbor
    list results for identical collection/frame/species-index/cutoff requests.
    This is sufficient to reuse the expensive Si--O/Al--O geometry shared by
    framework-only and broader atomic-connectivity evaluations without making
    cache state part of canonical connectivity digests.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[tuple[Any, ...], Any] = {}
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _request_key(
        collection: AtomisticFrameCollection,
        *,
        frame_index: int,
        center_indices: ArrayLike,
        candidate_neighbor_indices: ArrayLike,
        cutoff: Any,
        pair_counting: PairCounting,
        atom_block_size: int,
        neighbor_search: _NeighborSearchExecutor,
    ) -> tuple[Any, ...]:
        centers = np.ascontiguousarray(np.asarray(center_indices, dtype=np.int64))
        candidates = np.ascontiguousarray(
            np.asarray(candidate_neighbor_indices, dtype=np.int64)
        )
        radius = float(getattr(cutoff, "radius", cutoff))
        # Neighbor-search backend/cache settings are execution policy, not part
        # of the exact neighbor-list result.  Omitting them lets a stateless
        # frame-parallel consumer reuse geometry produced earlier by a sequential
        # Verlet-backed framework pass.  The scientific request key still fixes
        # collection, frame, atom populations, cutoff, pair counting, and block
        # partition exactly.
        return (
            id(collection),
            int(frame_index),
            centers.shape,
            centers.tobytes(),
            candidates.shape,
            candidates.tobytes(),
            radius,
            PairCounting(pair_counting).value,
            int(atom_block_size),
        )

    def get_or_build(
        self,
        collection: AtomisticFrameCollection,
        *,
        frame_index: int,
        center_indices: ArrayLike,
        candidate_neighbor_indices: ArrayLike,
        cutoff: Any,
        pair_counting: PairCounting,
        atom_block_size: int,
        neighbor_search: _NeighborSearchExecutor,
    ) -> Any:
        key = self._request_key(
            collection,
            frame_index=frame_index,
            center_indices=center_indices,
            candidate_neighbor_indices=candidate_neighbor_indices,
            cutoff=cutoff,
            pair_counting=pair_counting,
            atom_block_size=atom_block_size,
            neighbor_search=neighbor_search,
        )
        with self._lock:
            cached = self._items.get(key)
            if cached is not None:
                self._hits += 1
                return cached
        result = neighbor_search.build_neighbor_list(
            frame_index=frame_index,
            center_indices=center_indices,
            candidate_neighbor_indices=candidate_neighbor_indices,
            cutoff=cutoff,
            pair_counting=pair_counting,
            block_size=atom_block_size,
        )
        with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                self._hits += 1
                return existing
            self._items[key] = result
            self._misses += 1
        return result

    def to_dict(self) -> dict[str, Any]:
        with self._lock:
            return {
                "schema": ATOMIC_CONNECTIVITY_GEOMETRY_CACHE_SCHEMA,
                "entries": len(self._items),
                "hits": int(self._hits),
                "misses": int(self._misses),
                "scientific_identity_includes_cache_state": False,
            }


class AtomicConnectivityError(ValueError):
    """Base class for atomic-connectivity validation failures."""


class ConnectivityScopeError(AtomicConnectivityError):
    """Raised when a persistent atom scope is malformed or empty."""


class ConnectivityDefinitionError(AtomicConnectivityError):
    """Raised when a connectivity definition is inconsistent."""


class ConnectivityFrameSelectionError(AtomicConnectivityError):
    """Raised when selected frames are incompatible with a definition."""


class ConnectivityGeometryError(AtomicConnectivityError):
    """Raised when periodic edge geometry cannot be represented safely."""


def _normalize_species_tuple(
    values: Sequence[Species] | None, *, name: str
) -> tuple[int, ...] | None:
    if values is None:
        return None
    if isinstance(values, (str, bytes)):
        values = (values,)  # type: ignore[assignment]
    numbers = tuple(_atomic_number(value) for value in values)
    if len(set(numbers)) != len(numbers):
        raise ConnectivityScopeError(f"{name} contains duplicate species.")
    return tuple(sorted(numbers))


def _normalize_index_tuple(
    values: Sequence[int] | None, *, name: str
) -> tuple[int, ...] | None:
    if values is None:
        return None
    if len(values) == 0:
        return ()
    raw = np.asarray(values)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise ConnectivityScopeError(f"{name} must be a one-dimensional integer list.")
    indices = tuple(int(value) for value in raw)
    if any(index < 0 for index in indices):
        raise ConnectivityScopeError(f"{name} cannot contain negative indices.")
    if len(set(indices)) != len(indices):
        raise ConnectivityScopeError(f"{name} contains duplicate atom indices.")
    return tuple(sorted(indices))


@dataclass(frozen=True, slots=True)
class ConnectivityScope:
    """Persistent atom-identity selection for connectivity evaluation.

    Inclusion sources are combined by union.  Species and explicit atom
    exclusions are then removed, with exclusions taking precedence.
    """

    included_species: tuple[int, ...] | None = None
    included_atom_indices: tuple[int, ...] | None = None
    excluded_species: tuple[int, ...] = ()
    excluded_atom_indices: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        included_species = _normalize_species_tuple(
            self.included_species, name="included_species"
        )
        included_indices = _normalize_index_tuple(
            self.included_atom_indices, name="included_atom_indices"
        )
        excluded_species = _normalize_species_tuple(
            self.excluded_species, name="excluded_species"
        )
        excluded_indices = _normalize_index_tuple(
            self.excluded_atom_indices, name="excluded_atom_indices"
        )
        object.__setattr__(self, "included_species", included_species)
        object.__setattr__(self, "included_atom_indices", included_indices)
        object.__setattr__(self, "excluded_species", excluded_species or ())
        object.__setattr__(self, "excluded_atom_indices", excluded_indices or ())

    @classmethod
    def all(cls) -> "ConnectivityScope":
        """Return a scope containing every atom unless explicitly excluded."""
        return cls()

    @classmethod
    def from_selection(
        cls,
        *,
        included_species: Sequence[Species] | None = None,
        included_atom_indices: Sequence[int] | None = None,
        excluded_species: Sequence[Species] | None = None,
        excluded_atom_indices: Sequence[int] | None = None,
    ) -> "ConnectivityScope":
        """Construct a scope from chemical symbols/numbers and atom indices."""
        return cls(
            included_species=_normalize_species_tuple(
                included_species, name="included_species"
            ),
            included_atom_indices=_normalize_index_tuple(
                included_atom_indices, name="included_atom_indices"
            ),
            excluded_species=_normalize_species_tuple(
                excluded_species, name="excluded_species"
            )
            or (),
            excluded_atom_indices=_normalize_index_tuple(
                excluded_atom_indices, name="excluded_atom_indices"
            )
            or (),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "included_species": (
                None if self.included_species is None else list(self.included_species)
            ),
            "included_atom_indices": (
                None
                if self.included_atom_indices is None
                else list(self.included_atom_indices)
            ),
            "excluded_species": list(self.excluded_species),
            "excluded_atom_indices": list(self.excluded_atom_indices),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ConnectivityScope":
        return cls(
            included_species=_optional_tuple(payload.get("included_species")),
            included_atom_indices=_optional_tuple(payload.get("included_atom_indices")),
            excluded_species=tuple(payload.get("excluded_species", ())),
            excluded_atom_indices=tuple(payload.get("excluded_atom_indices", ())),
        )


@dataclass(frozen=True, slots=True)
class ResolvedConnectivityScope:
    """Collection-specific immutable realization of a connectivity scope."""

    atom_indices: IntArray
    atomic_numbers: Int32Array
    canonical_key: tuple[Any, ...]

    def __post_init__(self) -> None:
        indices = _readonly_array(self.atom_indices, np.int64, ndim=1)
        numbers = _readonly_array(self.atomic_numbers, np.int32, ndim=1)
        if indices.size == 0:
            raise ConnectivityScopeError("Resolved connectivity scope is empty.")
        if numbers.shape != indices.shape:
            raise ConnectivityScopeError(
                "Resolved atomic numbers must match atom-index shape."
            )
        if np.any(np.diff(indices) <= 0):
            raise ConnectivityScopeError(
                "Resolved atom indices must be strictly increasing."
            )
        object.__setattr__(self, "atom_indices", indices)
        object.__setattr__(self, "atomic_numbers", numbers)
        object.__setattr__(self, "canonical_key", tuple(self.canonical_key))

    @property
    def n_atoms(self) -> int:
        return int(self.atom_indices.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_indices": self.atom_indices.tolist(),
            "atomic_numbers": self.atomic_numbers.tolist(),
            "canonical_key": _json_safe(self.canonical_key),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ResolvedConnectivityScope":
        return cls(
            atom_indices=np.asarray(payload["atom_indices"], dtype=np.int64),
            atomic_numbers=np.asarray(payload["atomic_numbers"], dtype=np.int32),
            canonical_key=_to_tuple(payload["canonical_key"]),
        )


@dataclass(frozen=True, order=True, slots=True)
class AtomicEdgeKey:
    """Canonical periodic edge between two distinct global atom indices."""

    atom_i: int
    atom_j: int
    image_shift: tuple[int, int, int] = (0, 0, 0)

    def __post_init__(self) -> None:
        i = _coerce_int(self.atom_i, name="atom_i")
        j = _coerce_int(self.atom_j, name="atom_j")
        if i < 0 or j < 0:
            raise ConnectivityGeometryError("Atomic edge indices must be nonnegative.")
        shift = _coerce_shift(self.image_shift)
        if i == j:
            if shift == (0, 0, 0):
                raise ConnectivityGeometryError("Zero-shift self-edges are invalid.")
            raise ConnectivityGeometryError(
                "Nonzero self-image edges are unsupported in the first release."
            )
        if i > j:
            i, j = j, i
            shift = tuple(-value for value in shift)
        object.__setattr__(self, "atom_i", i)
        object.__setattr__(self, "atom_j", j)
        object.__setattr__(self, "image_shift", shift)

    @property
    def pair(self) -> tuple[int, int]:
        return (self.atom_i, self.atom_j)

    def reversed(self) -> tuple[int, int, tuple[int, int, int]]:
        return (
            self.atom_j,
            self.atom_i,
            tuple(-value for value in self.image_shift),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "atom_i": self.atom_i,
            "atom_j": self.atom_j,
            "image_shift": list(self.image_shift),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicEdgeKey":
        return cls(
            atom_i=int(payload["atom_i"]),
            atom_j=int(payload["atom_j"]),
            image_shift=tuple(int(value) for value in payload["image_shift"]),
        )


def _trusted_atomic_edge_key(
    atom_i: int, atom_j: int, image_shift: ArrayLike
) -> AtomicEdgeKey:
    """Fast internal constructor for neighbor-kernel output already validated.

    Neighbor-list kernels guarantee finite in-scope distinct atom indices and an
    integer three-component lattice shift.  Re-running the public dataclass's
    generic coercion machinery for every retained pair was a major connectivity
    hotspot.  This helper performs only the canonical endpoint orientation step.
    """

    i = int(atom_i)
    j = int(atom_j)
    raw = np.asarray(image_shift, dtype=np.int64)
    shift = (int(raw[0]), int(raw[1]), int(raw[2]))
    if i > j:
        i, j = j, i
        shift = (-shift[0], -shift[1], -shift[2])
    edge = object.__new__(AtomicEdgeKey)
    object.__setattr__(edge, "atom_i", i)
    object.__setattr__(edge, "atom_j", j)
    object.__setattr__(edge, "image_shift", shift)
    return edge


@dataclass(frozen=True, slots=True)
class DistanceConnectivity:
    """Instantaneous strict-cutoff atomic connectivity."""

    cutoffs: PairCutoffRegistry
    scope: ConnectivityScope = field(default_factory=ConnectivityScope.all)

    def __post_init__(self) -> None:
        object.__setattr__(self, "cutoffs", coerce_cutoff_registry(self.cutoffs))
        if not isinstance(self.scope, ConnectivityScope):
            raise TypeError("scope must be a ConnectivityScope.")
        if not self.cutoffs.cutoffs:
            raise ConnectivityDefinitionError("Distance connectivity needs cutoffs.")

    @property
    def kind(self) -> str:
        return "distance"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "cutoffs": self.cutoffs.to_dict(),
            "scope": self.scope.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class HystereticDistanceConnectivity:
    """Two-cutoff connectivity for ordered trajectories."""

    formation_cutoffs: PairCutoffRegistry
    breaking_cutoffs: PairCutoffRegistry
    scope: ConnectivityScope = field(default_factory=ConnectivityScope.all)
    initial_state: Literal["formation_cutoff", "explicit_edges"] = "formation_cutoff"
    initial_edges: tuple[AtomicEdgeKey, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConnectivityScope):
            raise TypeError("scope must be a ConnectivityScope.")
        formation = coerce_cutoff_registry(self.formation_cutoffs)
        breaking = coerce_cutoff_registry(self.breaking_cutoffs)
        _require_same_registry_pairs(formation, breaking, "hysteretic")
        for pair in formation.cutoffs:
            if formation.cutoffs[pair].radius >= breaking.cutoffs[pair].radius:
                raise ConnectivityDefinitionError(
                    f"Hysteretic cutoff for {pair} requires formation < breaking."
                )
        if self.initial_state not in {"formation_cutoff", "explicit_edges"}:
            raise ConnectivityDefinitionError(
                "initial_state must be 'formation_cutoff' or 'explicit_edges'."
            )
        edges = None
        if self.initial_state == "explicit_edges":
            if self.initial_edges is None:
                raise ConnectivityDefinitionError(
                    "explicit_edges initialization requires initial_edges."
                )
            edges = _normalize_edge_tuple(self.initial_edges)
        elif self.initial_edges is not None:
            raise ConnectivityDefinitionError(
                "initial_edges is only valid with initial_state='explicit_edges'."
            )
        object.__setattr__(self, "formation_cutoffs", formation)
        object.__setattr__(self, "breaking_cutoffs", breaking)
        object.__setattr__(self, "initial_edges", edges)

    @property
    def kind(self) -> str:
        return "hysteretic_distance"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "formation_cutoffs": self.formation_cutoffs.to_dict(),
            "breaking_cutoffs": self.breaking_cutoffs.to_dict(),
            "scope": self.scope.to_dict(),
            "initial_state": self.initial_state,
            "initial_edges": (
                None
                if self.initial_edges is None
                else [edge.to_dict() for edge in self.initial_edges]
            ),
        }


@dataclass(frozen=True, slots=True)
class ReferenceDistanceConnectivity:
    """Reference-state connectivity for trajectories or independent ensembles."""

    discovery_cutoffs: PairCutoffRegistry
    formation_cutoffs: PairCutoffRegistry
    retention_cutoffs: PairCutoffRegistry
    reference_frame: int = 0
    scope: ConnectivityScope = field(default_factory=ConnectivityScope.all)

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConnectivityScope):
            raise TypeError("scope must be a ConnectivityScope.")
        discovery = coerce_cutoff_registry(self.discovery_cutoffs)
        formation = coerce_cutoff_registry(self.formation_cutoffs)
        retention = coerce_cutoff_registry(self.retention_cutoffs)
        _require_same_registry_pairs(discovery, formation, "reference")
        _require_same_registry_pairs(discovery, retention, "reference")
        for pair in discovery.cutoffs:
            r_form = formation.cutoffs[pair].radius
            r_discover = discovery.cutoffs[pair].radius
            r_retain = retention.cutoffs[pair].radius
            if not (r_form <= r_discover < r_retain):
                raise ConnectivityDefinitionError(
                    f"Reference cutoffs for {pair} require formation <= "
                    "discovery < retention."
                )
        reference = _coerce_int(self.reference_frame, name="reference_frame")
        object.__setattr__(self, "discovery_cutoffs", discovery)
        object.__setattr__(self, "formation_cutoffs", formation)
        object.__setattr__(self, "retention_cutoffs", retention)
        object.__setattr__(self, "reference_frame", reference)

    @property
    def kind(self) -> str:
        return "reference_distance"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "discovery_cutoffs": self.discovery_cutoffs.to_dict(),
            "formation_cutoffs": self.formation_cutoffs.to_dict(),
            "retention_cutoffs": self.retention_cutoffs.to_dict(),
            "reference_frame": self.reference_frame,
            "scope": self.scope.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class ExplicitConnectivity:
    """Uniform or frame-indexed externally supplied atomic edges."""

    scope: ConnectivityScope = field(default_factory=ConnectivityScope.all)
    uniform_edges: tuple[AtomicEdgeKey, ...] | None = None
    frame_edges: Mapping[int, tuple[AtomicEdgeKey, ...]] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ConnectivityScope):
            raise TypeError("scope must be a ConnectivityScope.")
        has_uniform = self.uniform_edges is not None
        has_frames = self.frame_edges is not None
        if has_uniform == has_frames:
            raise ConnectivityDefinitionError(
                "Exactly one of uniform_edges and frame_edges must be supplied."
            )
        if has_uniform:
            object.__setattr__(
                self, "uniform_edges", _normalize_edge_tuple(self.uniform_edges or ())
            )
            object.__setattr__(self, "frame_edges", None)
        else:
            if not isinstance(self.frame_edges, Mapping):
                raise ConnectivityDefinitionError("frame_edges must be a mapping.")
            normalized: dict[int, tuple[AtomicEdgeKey, ...]] = {}
            for frame, edges in self.frame_edges.items():
                index = _coerce_int(frame, name="frame_edges key")
                if index < 0:
                    raise ConnectivityDefinitionError(
                        "frame_edges keys must be nonnegative collection positions."
                    )
                normalized[index] = _normalize_edge_tuple(edges)
            object.__setattr__(self, "frame_edges", MappingProxyType(normalized))
            object.__setattr__(self, "uniform_edges", None)

    @property
    def kind(self) -> str:
        return "explicit"

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "scope": self.scope.to_dict(),
            "uniform_edges": (
                None
                if self.uniform_edges is None
                else [edge.to_dict() for edge in self.uniform_edges]
            ),
            "frame_edges": (
                None
                if self.frame_edges is None
                else {
                    str(frame): [edge.to_dict() for edge in edges]
                    for frame, edges in sorted(self.frame_edges.items())
                }
            ),
        }


AtomicConnectivityDefinition: TypeAlias = (
    DistanceConnectivity
    | HystereticDistanceConnectivity
    | ReferenceDistanceConnectivity
    | ExplicitConnectivity
)


class ConnectivityConsistency(str, Enum):
    """Cross-frame organization of atomic connectivity states."""

    UNIFORM = "uniform"
    PARTITIONED = "partitioned"
    PER_FRAME = "per_frame"


@dataclass(frozen=True, slots=True, eq=False)
class AtomicConnectivityState:
    """One immutable canonical periodic atomic graph."""

    active_atom_indices: IntArray
    active_atomic_numbers: Int32Array
    pbc: BoolArray
    edge_atom_indices: IntArray
    edge_image_shifts: IntArray
    degree: Int32Array
    component_labels: Int32Array
    n_components: int
    canonical_schema_version: str = CANONICAL_CONNECTIVITY_SCHEMA
    digest_algorithm: str = CONNECTIVITY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        active = _readonly_array(self.active_atom_indices, np.int64, ndim=1)
        numbers = _readonly_array(self.active_atomic_numbers, np.int32, ndim=1)
        periodic = _readonly_array(self.pbc, np.bool_, ndim=1)
        endpoints = _readonly_array(self.edge_atom_indices, np.int64, ndim=2)
        shifts = _readonly_array(self.edge_image_shifts, np.int64, ndim=2)
        degree = _readonly_array(self.degree, np.int32, ndim=1)
        labels = _readonly_array(self.component_labels, np.int32, ndim=1)
        if numbers.shape != active.shape or degree.shape != active.shape:
            raise AtomicConnectivityError(
                "Active atomic numbers and degree must match active atom shape."
            )
        if labels.shape != active.shape:
            raise AtomicConnectivityError(
                "component_labels must match active atom shape."
            )
        if periodic.shape != (3,):
            raise AtomicConnectivityError("pbc must have shape (3,).")
        if endpoints.ndim != 2 or endpoints.shape[1:] != (2,):
            raise AtomicConnectivityError("edge_atom_indices must have shape (E, 2).")
        if shifts.shape != (endpoints.shape[0], 3):
            raise AtomicConnectivityError("edge_image_shifts must have shape (E, 3).")
        if active.size == 0 or np.any(np.diff(active) <= 0):
            raise AtomicConnectivityError(
                "active_atom_indices must be nonempty and strictly increasing."
            )
        active_set = set(int(value) for value in active)
        seen_pairs: set[tuple[int, int]] = set()
        records: list[tuple[int, int, int, int, int]] = []
        for endpoint, shift in zip(endpoints, shifts, strict=True):
            edge = AtomicEdgeKey(
                int(endpoint[0]), int(endpoint[1]), tuple(int(x) for x in shift)
            )
            if edge.atom_i not in active_set or edge.atom_j not in active_set:
                raise AtomicConnectivityError(
                    "State edge endpoint lies outside active scope."
                )
            if edge.pair in seen_pairs:
                raise AtomicConnectivityError(
                    "Parallel atomic edges are unsupported in the first release."
                )
            seen_pairs.add(edge.pair)
            records.append((*edge.pair, *edge.image_shift))
        if records != sorted(records):
            raise AtomicConnectivityError(
                "State edges must be lexicographically sorted."
            )
        if np.any(shifts[:, ~periodic] != 0):
            raise AtomicConnectivityError(
                "Image shifts must be zero along nonperiodic axes."
            )
        n_components = _coerce_int(self.n_components, name="n_components")
        if n_components < 1:
            raise AtomicConnectivityError("n_components must be positive.")
        if labels.size and (np.min(labels) < 0 or np.max(labels) >= n_components):
            raise AtomicConnectivityError("component_labels are out of range.")
        expected_digest = _state_digest(active, numbers, periodic, endpoints, shifts)
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise AtomicConnectivityError("Stored connectivity digest is inconsistent.")
        if self.canonical_schema_version != CANONICAL_CONNECTIVITY_SCHEMA:
            raise AtomicConnectivityError("Unsupported connectivity schema version.")
        if self.digest_algorithm != CONNECTIVITY_DIGEST_ALGORITHM:
            raise AtomicConnectivityError("Unsupported connectivity digest algorithm.")
        object.__setattr__(self, "active_atom_indices", active)
        object.__setattr__(self, "active_atomic_numbers", numbers)
        object.__setattr__(self, "pbc", periodic)
        object.__setattr__(self, "edge_atom_indices", endpoints)
        object.__setattr__(self, "edge_image_shifts", shifts)
        object.__setattr__(self, "degree", degree)
        object.__setattr__(self, "component_labels", labels)
        object.__setattr__(self, "n_components", n_components)
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AtomicConnectivityState):
            return NotImplemented
        return _states_equal(self, other)

    def __hash__(self) -> int:
        return int(self.digest[:16], 16)

    @property
    def n_active_atoms(self) -> int:
        return int(self.active_atom_indices.size)

    @property
    def n_edges(self) -> int:
        return int(self.edge_atom_indices.shape[0])

    @property
    def edge_keys(self) -> tuple[AtomicEdgeKey, ...]:
        return tuple(
            AtomicEdgeKey(int(pair[0]), int(pair[1]), tuple(int(x) for x in shift))
            for pair, shift in zip(
                self.edge_atom_indices, self.edge_image_shifts, strict=True
            )
        )

    def degree_for_atom(self, atom_index: int) -> int:
        index = _coerce_int(atom_index, name="atom_index")
        position = int(np.searchsorted(self.active_atom_indices, index))
        if (
            position >= self.n_active_atoms
            or self.active_atom_indices[position] != index
        ):
            raise KeyError(f"Atom {index} is outside this connectivity state.")
        return int(self.degree[position])

    def to_networkx(self) -> Any:
        """Return a derived NetworkX graph without affecting canonical identity."""
        import networkx as nx

        graph = nx.Graph()
        for index, atomic_number, degree, component in zip(
            self.active_atom_indices,
            self.active_atomic_numbers,
            self.degree,
            self.component_labels,
            strict=True,
        ):
            graph.add_node(
                int(index),
                atomic_number=int(atomic_number),
                symbol=chemical_symbols[int(atomic_number)],
                degree=int(degree),
                component=int(component),
            )
        for edge in self.edge_keys:
            graph.add_edge(
                edge.atom_i,
                edge.atom_j,
                image_shift=edge.image_shift,
            )
        graph.graph.update(
            digest=self.digest,
            pbc=tuple(bool(value) for value in self.pbc),
            canonical_schema_version=self.canonical_schema_version,
        )
        return graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_atom_indices": self.active_atom_indices.tolist(),
            "active_atomic_numbers": self.active_atomic_numbers.tolist(),
            "pbc": self.pbc.tolist(),
            "edge_atom_indices": self.edge_atom_indices.tolist(),
            "edge_image_shifts": self.edge_image_shifts.tolist(),
            "degree": self.degree.tolist(),
            "component_labels": self.component_labels.tolist(),
            "n_components": self.n_components,
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicConnectivityState":
        return cls(
            active_atom_indices=np.asarray(
                payload["active_atom_indices"], dtype=np.int64
            ),
            active_atomic_numbers=np.asarray(
                payload["active_atomic_numbers"], dtype=np.int32
            ),
            pbc=np.asarray(payload["pbc"], dtype=bool),
            edge_atom_indices=np.asarray(
                payload["edge_atom_indices"], dtype=np.int64
            ).reshape(-1, 2),
            edge_image_shifts=np.asarray(
                payload["edge_image_shifts"], dtype=np.int64
            ).reshape(-1, 3),
            degree=np.asarray(payload["degree"], dtype=np.int32),
            component_labels=np.asarray(payload["component_labels"], dtype=np.int32),
            n_components=int(payload["n_components"]),
            canonical_schema_version=str(payload["canonical_schema_version"]),
            digest_algorithm=str(payload["digest_algorithm"]),
            digest=str(payload["digest"]),
        )


@dataclass(frozen=True, slots=True)
class ConnectivitySegment:
    """Contiguous run of one state in an analyzed trajectory sequence."""

    segment_id: int
    state_id: int
    result_position_start: int
    result_position_stop: int

    def __post_init__(self) -> None:
        for name in (
            "segment_id",
            "state_id",
            "result_position_start",
            "result_position_stop",
        ):
            object.__setattr__(self, name, _coerce_int(getattr(self, name), name=name))
        if self.segment_id < 0 or self.state_id < 0:
            raise AtomicConnectivityError("Segment identifiers must be nonnegative.")
        if (
            self.result_position_start < 0
            or self.result_position_stop <= self.result_position_start
        ):
            raise AtomicConnectivityError(
                "Segment interval must be nonempty and half-open."
            )


@dataclass(frozen=True, slots=True)
class ConnectivityTransition:
    """Exact atomic-pair change between consecutive trajectory segments."""

    transition_id: int
    source_state_id: int
    target_state_id: int
    result_position_before: int
    result_position_after: int
    collection_frame_index_before: int
    collection_frame_index_after: int
    frame_id_before: int
    frame_id_after: int
    added_edges: tuple[AtomicEdgeKey, ...]
    removed_edges: tuple[AtomicEdgeKey, ...]
    affected_atom_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        integer_names = (
            "transition_id",
            "source_state_id",
            "target_state_id",
            "result_position_before",
            "result_position_after",
            "collection_frame_index_before",
            "collection_frame_index_after",
            "frame_id_before",
            "frame_id_after",
        )
        for name in integer_names:
            object.__setattr__(self, name, _coerce_int(getattr(self, name), name=name))
        object.__setattr__(self, "added_edges", _normalize_edge_tuple(self.added_edges))
        object.__setattr__(
            self, "removed_edges", _normalize_edge_tuple(self.removed_edges)
        )
        affected = tuple(
            sorted(
                {
                    _coerce_int(x, name="affected atom")
                    for x in self.affected_atom_indices
                }
            )
        )
        object.__setattr__(self, "affected_atom_indices", affected)


@dataclass(frozen=True, slots=True)
class AtomicConnectivityResult:
    """Connectivity states and their organization across selected frames."""

    definition: AtomicConnectivityDefinition
    resolved_scope: ResolvedConnectivityScope
    consistency: ConnectivityConsistency
    frame_indices: IntArray
    frame_ids: IntArray
    frame_state_ids: Int32Array
    states: tuple[AtomicConnectivityState, ...]
    segments: tuple[ConnectivitySegment, ...] | None
    transitions: tuple[ConnectivityTransition, ...]
    metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        if not isinstance(
            self.definition,
            (
                DistanceConnectivity,
                HystereticDistanceConnectivity,
                ReferenceDistanceConnectivity,
                ExplicitConnectivity,
            ),
        ):
            raise TypeError("Unsupported atomic connectivity definition.")
        frames = _readonly_array(self.frame_indices, np.int64, ndim=1)
        frame_ids = _readonly_array(self.frame_ids, np.int64, ndim=1)
        state_ids = _readonly_array(self.frame_state_ids, np.int32, ndim=1)
        if (
            frames.size == 0
            or frame_ids.shape != frames.shape
            or state_ids.shape != frames.shape
        ):
            raise AtomicConnectivityError(
                "frame_indices, frame_ids, and frame_state_ids must be equal nonempty arrays."
            )
        states = tuple(self.states)
        if not states:
            raise AtomicConnectivityError("Connectivity result has no states.")
        if np.any(state_ids < 0) or np.any(state_ids >= len(states)):
            raise AtomicConnectivityError("frame_state_ids contain invalid state IDs.")
        consistency = ConnectivityConsistency(self.consistency)
        if consistency is ConnectivityConsistency.UNIFORM and len(states) != 1:
            raise AtomicConnectivityError("UNIFORM results require exactly one state.")
        if consistency is ConnectivityConsistency.PARTITIONED and len(states) < 2:
            raise AtomicConnectivityError(
                "PARTITIONED results require multiple states."
            )
        if consistency is ConnectivityConsistency.PER_FRAME:
            if len(states) != frames.size or not np.array_equal(
                state_ids, np.arange(frames.size)
            ):
                raise AtomicConnectivityError(
                    "PER_FRAME results require one state per frame in result order."
                )
            if self.segments is not None or self.transitions:
                raise AtomicConnectivityError(
                    "PER_FRAME results cannot contain segments or transitions."
                )
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "frame_state_ids", state_ids)
        object.__setattr__(self, "states", states)
        object.__setattr__(self, "consistency", consistency)
        object.__setattr__(
            self, "segments", None if self.segments is None else tuple(self.segments)
        )
        object.__setattr__(self, "transitions", tuple(self.transitions))
        object.__setattr__(
            self, "metadata", MappingProxyType(_deep_copy_mapping(self.metadata))
        )

    @property
    def n_states(self) -> int:
        return len(self.states)

    @property
    def state_counts(self) -> IntArray:
        return np.bincount(self.frame_state_ids, minlength=self.n_states).astype(
            np.int64
        )

    @property
    def state_probabilities(self) -> NDArray[np.float64]:
        return self.state_counts.astype(float) / self.frame_state_ids.size

    def state_for_frame(self, frame_index: int) -> AtomicConnectivityState:
        frame = _coerce_int(frame_index, name="frame_index")
        positions = np.flatnonzero(self.frame_indices == frame)
        if positions.size == 0:
            raise KeyError(f"Collection frame {frame} is not in this result.")
        return self.states[int(self.frame_state_ids[int(positions[0])])]

    def frames_for_state(self, state_id: int) -> IntArray:
        index = _validated_state_id(state_id, self.n_states)
        return self.frame_indices[self.frame_state_ids == index].copy()

    def edge_presence(self, edge: AtomicEdgeKey) -> BoolArray:
        target = AtomicEdgeKey(edge.atom_i, edge.atom_j, edge.image_shift)
        pair = target.pair
        state_presence = np.asarray(
            [pair in {item.pair for item in state.edge_keys} for state in self.states],
            dtype=bool,
        )
        return state_presence[self.frame_state_ids]

    def compare_states(
        self, state_a: int, state_b: int
    ) -> dict[str, tuple[AtomicEdgeKey, ...]]:
        a = self.states[_validated_state_id(state_a, self.n_states)]
        b = self.states[_validated_state_id(state_b, self.n_states)]
        added, removed = _edge_pair_difference(a, b)
        return {"added_edges": added, "removed_edges": removed}

    def to_networkx(self, state_id: int = 0) -> Any:
        return self.states[_validated_state_id(state_id, self.n_states)].to_networkx()

    def to_dict(self) -> dict[str, Any]:
        return {
            "definition": _definition_to_dict(self.definition),
            "resolved_scope": self.resolved_scope.to_dict(),
            "consistency": self.consistency.value,
            "frame_indices": self.frame_indices.tolist(),
            "frame_ids": self.frame_ids.tolist(),
            "frame_state_ids": self.frame_state_ids.tolist(),
            "states": [state.to_dict() for state in self.states],
            "segments": (
                None
                if self.segments is None
                else [
                    {
                        "segment_id": item.segment_id,
                        "state_id": item.state_id,
                        "result_position_start": item.result_position_start,
                        "result_position_stop": item.result_position_stop,
                    }
                    for item in self.segments
                ]
            ),
            "transitions": [
                {
                    "transition_id": item.transition_id,
                    "source_state_id": item.source_state_id,
                    "target_state_id": item.target_state_id,
                    "result_position_before": item.result_position_before,
                    "result_position_after": item.result_position_after,
                    "collection_frame_index_before": item.collection_frame_index_before,
                    "collection_frame_index_after": item.collection_frame_index_after,
                    "frame_id_before": item.frame_id_before,
                    "frame_id_after": item.frame_id_after,
                    "added_edges": [edge.to_dict() for edge in item.added_edges],
                    "removed_edges": [edge.to_dict() for edge in item.removed_edges],
                    "affected_atom_indices": list(item.affected_atom_indices),
                }
                for item in self.transitions
            ],
            "metadata": _json_safe(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicConnectivityResult":
        segments_payload = payload.get("segments")
        segments = None
        if segments_payload is not None:
            segments = tuple(ConnectivitySegment(**item) for item in segments_payload)
        transitions = tuple(
            ConnectivityTransition(
                transition_id=item["transition_id"],
                source_state_id=item["source_state_id"],
                target_state_id=item["target_state_id"],
                result_position_before=item["result_position_before"],
                result_position_after=item["result_position_after"],
                collection_frame_index_before=item["collection_frame_index_before"],
                collection_frame_index_after=item["collection_frame_index_after"],
                frame_id_before=item["frame_id_before"],
                frame_id_after=item["frame_id_after"],
                added_edges=tuple(
                    AtomicEdgeKey.from_dict(x) for x in item["added_edges"]
                ),
                removed_edges=tuple(
                    AtomicEdgeKey.from_dict(x) for x in item["removed_edges"]
                ),
                affected_atom_indices=tuple(item["affected_atom_indices"]),
            )
            for item in payload.get("transitions", ())
        )
        return cls(
            definition=_definition_from_dict(payload["definition"]),
            resolved_scope=ResolvedConnectivityScope.from_dict(
                payload["resolved_scope"]
            ),
            consistency=ConnectivityConsistency(payload["consistency"]),
            frame_indices=np.asarray(payload["frame_indices"], dtype=np.int64),
            frame_ids=np.asarray(payload["frame_ids"], dtype=np.int64),
            frame_state_ids=np.asarray(payload["frame_state_ids"], dtype=np.int32),
            states=tuple(
                AtomicConnectivityState.from_dict(item) for item in payload["states"]
            ),
            segments=segments,
            transitions=transitions,
            metadata=dict(payload.get("metadata", {})),
        )


def build_atomic_connectivity_state(
    collection: AtomisticFrameCollection,
    definition: DistanceConnectivity | ExplicitConnectivity,
    *,
    frame_index: int,
    atom_block_size: int = 256,
    neighbor_search_options: NeighborSearchOptions | None = None,
) -> AtomicConnectivityState:
    """Build one state for a stateless single-frame connectivity definition."""
    frame = _validated_single_frame(collection, frame_index)
    block = _validated_block_size(atom_block_size)
    resolved = _resolve_connectivity_scope(collection, definition.scope)
    neighbor_search = _NeighborSearchExecutor(
        collection, options=neighbor_search_options, selected_frame_count=1
    )
    if isinstance(definition, DistanceConnectivity):
        _validate_registry_for_frames(
            definition.cutoffs, collection, np.asarray([frame])
        )
        edges, eligible = _enumerate_distance_edges(
            collection,
            frame_index=frame,
            resolved_scope=resolved,
            cutoffs=definition.cutoffs,
            atom_block_size=block,
            neighbor_search=neighbor_search,
        )
        if not eligible:
            raise ConnectivityDefinitionError(
                "No registered cutoff pair has eligible atoms in the resolved scope."
            )
    elif isinstance(definition, ExplicitConnectivity):
        edges = _explicit_edges_for_frame(definition, frame)
        _validate_edges_against_scope(edges, resolved, collection)
    else:  # pragma: no cover - protected by type annotation and explicit check
        raise TypeError(
            "Single-frame construction supports distance or explicit connectivity."
        )
    return _build_state(
        collection,
        resolved,
        tuple(edges.values()) if isinstance(edges, dict) else edges,
    )



def _merge_frame_parallel_neighbor_diagnostics(
    diagnostics: Sequence[Mapping[str, Any]],
    *,
    options: NeighborSearchOptions,
    selected_frame_count: int,
    workers: int,
) -> dict[str, Any]:
    """Merge stateless frame-local neighbor diagnostics deterministically."""

    backend_counts: Counter[str] = Counter()
    fallback_events: Counter[str] = Counter()
    resolution_reasons: Counter[str] = Counter()
    request_digests: list[str] = []
    requests: list[Mapping[str, Any]] = []
    candidates = accepted = evaluations = 0
    backend_policy_values: set[str] = set()
    backend_selected_values: set[str] = set()
    for item in diagnostics:
        backend_counts.update(dict(item.get("backend_counts", {})))
        fallback_events.update(dict(item.get("fallback_events", {})))
        resolution_reasons.update(dict(item.get("cache_resolution_reasons", {})))
        request_digests.extend(str(v) for v in item.get("request_digests", ()))
        requests.extend(item.get("requests", ()))
        candidates += int(item.get("candidate_pair_evaluations", 0))
        accepted += int(item.get("accepted_pairs", 0))
        evaluations += int(item.get("evaluations", 0))
        policy = str(item.get("backend_policy", "none"))
        selected = str(item.get("backend_selected", "none"))
        if policy != "none":
            backend_policy_values.add(policy)
        if selected != "none":
            backend_selected_values.add(selected)
    backend_policy = (
        next(iter(backend_policy_values))
        if len(backend_policy_values) == 1
        else ("mixed" if backend_policy_values else "none")
    )
    backend_selected = (
        next(iter(backend_selected_values))
        if len(backend_selected_values) == 1
        else ("mixed" if backend_selected_values else "none")
    )
    return {
        "schema": "mdstats.periodic-neighbor-search.v2",
        "frame_semantics": "trajectory",
        "backend_requested": options.backend,
        "backend_policy": backend_policy,
        "backend_selected": backend_selected,
        "cache_mode_requested": options.cache_mode,
        "cache_mode_selected": "none",
        "cache_resolution_reasons": dict(sorted(resolution_reasons.items())),
        "cache_disabled_during_run": False,
        "cache_disable_reasons": {},
        "zero_reuse_rebuild_limit": options.max_consecutive_zero_reuse_rebuilds,
        "skin": options.skin,
        "selected_frame_count": int(selected_frame_count),
        "evaluations": evaluations,
        "request_digests": request_digests,
        "backend_counts": dict(sorted(backend_counts.items())),
        "candidate_pair_evaluations": candidates,
        "accepted_pairs": accepted,
        "candidate_efficiency": 0.0 if candidates == 0 else accepted / candidates,
        "fallback_events": dict(sorted(fallback_events.items())),
        "options": options.to_dict(),
        "requests": list(requests),
        "cache_statistics": None,
        "cell_list_rebuild_count": 0,
        "cache_reuse_frame_count": 0,
        "mean_frames_per_rebuild": 0.0,
        "median_frames_per_rebuild": 0.0,
        "rebuild_reason_counts": {},
        "minimum_safety_margin_by_rebuild_interval": [],
        "minimum_singular_value_by_rebuild_interval": [],
        "par_dens4_frame_parallel_geometry": True,
        "par_dens4_parallel_workers": int(workers),
        "par_dens4_hysteresis_fold": "deterministic_collection_frame_order_v1",
    }


def _prepare_hysteretic_geometry_parallel(
    collection: AtomisticFrameCollection,
    *,
    frames: IntArray,
    resolved_scope: ResolvedConnectivityScope,
    breaking_cutoffs: PairCutoffRegistry,
    formation_cutoffs: PairCutoffRegistry,
    atom_block_size: int,
    options: NeighborSearchOptions | None,
    geometry_cache: AtomicConnectivityGeometryCache | None,
    workers: int,
) -> tuple[
    tuple[tuple[dict[tuple[int, int], AtomicEdgeKey], dict[tuple[int, int], AtomicEdgeKey], bool], ...],
    Mapping[str, Any],
]:
    """Compute independent outer/inner candidate geometry before hysteresis."""

    base_options = NeighborSearchOptions() if options is None else options
    # Stateful Verlet reuse is sequential by construction.  The PAR-DENS4
    # geometric stage instead uses exact stateless requests on independent
    # frames, then applies hysteresis once in authoritative frame order.
    stateless = replace(base_options, cache_mode="none")

    frame_values = [int(frame) for frame in frames]
    actual_workers = max(1, min(int(workers), len(frame_values)))

    # Amortize executor construction and diagnostics bookkeeping across a
    # contiguous frame chunk.  Each chunk remains stateless with respect to
    # Verlet reuse, while its output order is exactly the input frame order.
    # Contiguous chunks also make deterministic reassembly trivial.
    chunk_arrays = np.array_split(np.asarray(frame_values, dtype=np.int64), actual_workers)
    chunks = [tuple(int(value) for value in chunk) for chunk in chunk_arrays if chunk.size]

    def evaluate_chunk(chunk: tuple[int, ...]):
        executor = _NeighborSearchExecutor(
            collection,
            options=stateless,
            selected_frame_count=len(chunk),
        )
        values = []
        for frame in chunk:
            outer, inner, eligible = _enumerate_nested_distance_edges(
                collection,
                frame_index=frame,
                resolved_scope=resolved_scope,
                outer_cutoffs=breaking_cutoffs,
                inner_cutoffs=formation_cutoffs,
                atom_block_size=atom_block_size,
                neighbor_search=executor,
                geometry_cache=geometry_cache,
            )
            values.append((outer, inner, eligible))
        return tuple(values), executor.diagnostics().to_dict()

    if actual_workers <= 1:
        evaluated_chunks = [evaluate_chunk(chunks[0])]
    else:
        with ThreadPoolExecutor(
            max_workers=actual_workers,
            thread_name_prefix="mdstats-connectivity-geometry",
        ) as pool:
            evaluated_chunks = list(pool.map(evaluate_chunk, chunks))
    candidates = tuple(
        candidate
        for chunk_candidates, _diagnostics in evaluated_chunks
        for candidate in chunk_candidates
    )
    neighbor_diagnostics = _merge_frame_parallel_neighbor_diagnostics(
        [item[1] for item in evaluated_chunks],
        options=stateless,
        selected_frame_count=len(frame_values),
        workers=actual_workers,
    )
    return candidates, neighbor_diagnostics


def compute_atomic_connectivity(
    collection: AtomisticFrameCollection,
    definition: AtomicConnectivityDefinition,
    *,
    frame_indices: ArrayLike | None = None,
    state_mode: Literal["catalog", "per_frame"] = "catalog",
    atom_block_size: int = 256,
    neighbor_search_options: NeighborSearchOptions | None = None,
    verlet_cache_options: VerletCacheOptions | None = None,
    geometry_cache: AtomicConnectivityGeometryCache | None = None,
    parallel_frame_workers: int = 1,
    progress_callback: Callable[[int, int], None] | None = None,
) -> AtomicConnectivityResult:
    """Evaluate an atomic connectivity definition over selected frames."""
    if not isinstance(
        definition,
        (
            DistanceConnectivity,
            HystereticDistanceConnectivity,
            ReferenceDistanceConnectivity,
            ExplicitConnectivity,
        ),
    ):
        raise TypeError("definition is not a supported atomic connectivity definition.")
    frames = _validated_frames(collection, frame_indices)
    block = _validated_block_size(atom_block_size)
    parallel_workers = _coerce_int(parallel_frame_workers, name="parallel_frame_workers")
    if parallel_workers <= 0:
        raise ValueError("parallel_frame_workers must be positive.")
    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable or None.")
    progress_total = int(frames.size)
    progress_interval = max(1, min(1000, max(1, progress_total // 20)))
    progress_last = 0

    def report_progress(processed: int, *, force: bool = False) -> None:
        nonlocal progress_last
        value = int(processed)
        if progress_callback is None:
            return
        if force or value >= progress_total or value - progress_last >= progress_interval:
            progress_callback(value, progress_total)
            progress_last = value

    if geometry_cache is not None and not isinstance(
        geometry_cache, AtomicConnectivityGeometryCache
    ):
        raise TypeError("geometry_cache must be AtomicConnectivityGeometryCache or None.")
    if state_mode not in {"catalog", "per_frame"}:
        raise ValueError("state_mode must be 'catalog' or 'per_frame'.")
    resolved = _resolve_connectivity_scope(collection, definition.scope)
    # Equal raw periodic edge sets occur frequently in MD, especially for a
    # stable framework.  Canonical gauge normalization/digest construction is
    # deterministic, so reuse the immutable state within this evaluation.
    state_build_cache: dict[tuple[AtomicEdgeKey, ...], AtomicConnectivityState] = {}
    diagnostics: list[str] = []
    if neighbor_search_options is not None and not isinstance(
        neighbor_search_options, NeighborSearchOptions
    ):
        raise TypeError(
            "neighbor_search_options must be a NeighborSearchOptions instance."
        )
    if verlet_cache_options is not None and not isinstance(
        verlet_cache_options, VerletCacheOptions
    ):
        raise TypeError("verlet_cache_options must be a VerletCacheOptions instance.")
    if neighbor_search_options is not None and verlet_cache_options is not None:
        raise ValueError(
            "Pass neighbor_search_options or legacy verlet_cache_options, not both."
        )
    effective_neighbor_options = neighbor_search_options
    if verlet_cache_options is not None:
        effective_neighbor_options = NeighborSearchOptions(
            backend="cell_list",
            cache_mode="verlet",
            skin=verlet_cache_options.skin,
            deformation_aware=verlet_cache_options.deformation_aware,
            safety_tolerance=verlet_cache_options.safety_tolerance,
            max_cell_condition_number=verlet_cache_options.max_cell_condition_number,
            cell_list_options=verlet_cache_options.cell_list_options,
        )
        diagnostics.append(
            "verlet_cache_options is retained for compatibility; "
            "prefer neighbor_search_options."
        )
    neighbor_search = _NeighborSearchExecutor(
        collection,
        options=effective_neighbor_options,
        selected_frame_count=int(frames.size),
    )

    if isinstance(definition, DistanceConnectivity):
        _validate_registry_for_frames(definition.cutoffs, collection, frames)
        frame_states = []
        eligible_any = False
        for frame in frames:
            edges, eligible = _enumerate_distance_edges(
                collection,
                frame_index=int(frame),
                resolved_scope=resolved,
                cutoffs=definition.cutoffs,
                atom_block_size=block,
                neighbor_search=neighbor_search,
                geometry_cache=geometry_cache,
            )
            eligible_any |= eligible
            frame_states.append(
                _build_state(collection, resolved, tuple(edges.values()), state_cache=state_build_cache)
            )
            report_progress(len(frame_states))
        if not eligible_any:
            raise ConnectivityDefinitionError(
                "No registered cutoff pair has eligible atoms in the resolved scope."
            )

    elif isinstance(definition, ExplicitConnectivity):
        frame_states = []
        for frame in frames:
            edges = _explicit_edges_for_frame(definition, int(frame))
            _validate_edges_against_scope(edges, resolved, collection)
            frame_states.append(_build_state(collection, resolved, edges, state_cache=state_build_cache))
            report_progress(len(frame_states))

    elif isinstance(definition, HystereticDistanceConnectivity):
        collection.require_trajectory("Hysteretic atomic connectivity")
        if frames.size > 1 and not np.array_equal(
            np.diff(frames), np.ones(frames.size - 1, dtype=np.int64)
        ):
            raise ConnectivityFrameSelectionError(
                "Hysteretic connectivity requires increasing contiguous unit-stride frames."
            )
        _validate_registry_for_frames(definition.formation_cutoffs, collection, frames)
        _validate_registry_for_frames(definition.breaking_cutoffs, collection, frames)
        parallel_neighbor_diagnostics: Mapping[str, Any] | None = None
        if parallel_workers > 1 and frames.size > 1:
            candidates, parallel_neighbor_diagnostics = _prepare_hysteretic_geometry_parallel(
                collection,
                frames=frames,
                resolved_scope=resolved,
                breaking_cutoffs=definition.breaking_cutoffs,
                formation_cutoffs=definition.formation_cutoffs,
                atom_block_size=block,
                options=effective_neighbor_options,
                geometry_cache=geometry_cache,
                workers=parallel_workers,
            )
            if definition.initial_state == "formation_cutoff":
                _breaking0, forming, eligible = candidates[0]
                if not eligible:
                    raise ConnectivityDefinitionError(
                        "No hysteretic cutoff pair has eligible atoms in the resolved scope."
                    )
                current = forming
            else:
                assert definition.initial_edges is not None
                _validate_edges_against_scope(
                    definition.initial_edges, resolved, collection
                )
                _validate_edges_against_registry(
                    definition.initial_edges, definition.formation_cutoffs, collection
                )
                current = {edge.pair: edge for edge in definition.initial_edges}
            frame_states = [_build_state(collection, resolved, tuple(current.values()), state_cache=state_build_cache)]
            report_progress(1)
            for breaking, forming, _eligible in candidates[1:]:
                retained = {pair: breaking[pair] for pair in current if pair in breaking}
                for pair, edge in forming.items():
                    if pair not in current:
                        retained[pair] = edge
                current = retained
                frame_states.append(
                    _build_state(collection, resolved, tuple(current.values()), state_cache=state_build_cache)
                )
                report_progress(len(frame_states))
            diagnostics.append(
                "PAR-DENS4 evaluated hysteretic geometric candidates in frame-parallel "
                "stateless workers and applied the stateful hysteresis fold in deterministic "
                "collection-frame order."
            )
        else:
            if definition.initial_state == "formation_cutoff":
                _, forming, eligible = _enumerate_nested_distance_edges(
                    collection,
                    frame_index=int(frames[0]),
                    resolved_scope=resolved,
                    outer_cutoffs=definition.breaking_cutoffs,
                    inner_cutoffs=definition.formation_cutoffs,
                    atom_block_size=block,
                    neighbor_search=neighbor_search,
                    geometry_cache=geometry_cache,
                )
                if not eligible:
                    raise ConnectivityDefinitionError(
                        "No hysteretic cutoff pair has eligible atoms in the resolved scope."
                    )
                current = forming
            else:
                assert definition.initial_edges is not None
                _validate_edges_against_scope(
                    definition.initial_edges, resolved, collection
                )
                _validate_edges_against_registry(
                    definition.initial_edges, definition.formation_cutoffs, collection
                )
                current = {edge.pair: edge for edge in definition.initial_edges}
            frame_states = [_build_state(collection, resolved, tuple(current.values()), state_cache=state_build_cache)]
            report_progress(1)
            for frame in frames[1:]:
                breaking, forming, _ = _enumerate_nested_distance_edges(
                    collection,
                    frame_index=int(frame),
                    resolved_scope=resolved,
                    outer_cutoffs=definition.breaking_cutoffs,
                    inner_cutoffs=definition.formation_cutoffs,
                    atom_block_size=block,
                    neighbor_search=neighbor_search,
                    geometry_cache=geometry_cache,
                )
                retained = {pair: breaking[pair] for pair in current if pair in breaking}
                for pair, edge in forming.items():
                    if pair not in current:
                        retained[pair] = edge
                current = retained
                frame_states.append(
                    _build_state(collection, resolved, tuple(current.values()), state_cache=state_build_cache)
                )
                report_progress(len(frame_states))

    else:
        assert isinstance(definition, ReferenceDistanceConnectivity)
        reference = _validated_single_frame(collection, definition.reference_frame)
        all_validation_frames = np.unique(
            np.concatenate([frames, np.asarray([reference])])
        )
        _validate_registry_for_frames(
            definition.discovery_cutoffs, collection, all_validation_frames
        )
        _validate_registry_for_frames(
            definition.formation_cutoffs, collection, all_validation_frames
        )
        _validate_registry_for_frames(
            definition.retention_cutoffs, collection, all_validation_frames
        )
        _, reference_edges, eligible = _enumerate_nested_distance_edges(
            collection,
            frame_index=reference,
            resolved_scope=resolved,
            outer_cutoffs=definition.retention_cutoffs,
            inner_cutoffs=definition.discovery_cutoffs,
            atom_block_size=block,
            neighbor_search=neighbor_search,
            geometry_cache=geometry_cache,
        )
        if not eligible:
            raise ConnectivityDefinitionError(
                "No reference cutoff pair has eligible atoms in the resolved scope."
            )
        reference_pairs = set(reference_edges)
        frame_states = []
        for frame in frames:
            retention, formation, _ = _enumerate_nested_distance_edges(
                collection,
                frame_index=int(frame),
                resolved_scope=resolved,
                outer_cutoffs=definition.retention_cutoffs,
                inner_cutoffs=definition.formation_cutoffs,
                atom_block_size=block,
                neighbor_search=neighbor_search,
                geometry_cache=geometry_cache,
            )
            selected = {
                pair: retention[pair] for pair in reference_pairs if pair in retention
            }
            for pair, edge in formation.items():
                if pair not in reference_pairs:
                    selected[pair] = edge
            frame_states.append(
                _build_state(collection, resolved, tuple(selected.values()), state_cache=state_build_cache)
            )
            report_progress(len(frame_states))

    report_progress(progress_total, force=True)
    if (
        isinstance(definition, HystereticDistanceConnectivity)
        and "parallel_neighbor_diagnostics" in locals()
        and parallel_neighbor_diagnostics is not None
    ):
        neighbor_diagnostics = dict(parallel_neighbor_diagnostics)
    else:
        neighbor_diagnostics = neighbor_search.diagnostics().to_dict()
    if geometry_cache is not None:
        neighbor_diagnostics = {
            **dict(neighbor_diagnostics),
            "geometry_cache": geometry_cache.to_dict(),
        }
    neighbor_diagnostics["par_dens4_parallel_frame_workers"] = int(parallel_workers)
    neighbor_diagnostics["canonical_state_build_cache_entries"] = int(len(state_build_cache))
    neighbor_diagnostics["canonical_state_build_cache_max_entries"] = int(_STATE_BUILD_CACHE_MAX_ENTRIES)
    neighbor_diagnostics["canonical_state_build_cache_enabled"] = True

    return _assemble_result(
        collection,
        definition,
        resolved,
        frames,
        frame_states,
        state_mode=state_mode,
        atom_block_size=block,
        diagnostics=diagnostics,
        neighbor_search_diagnostics=neighbor_diagnostics,
    )



def project_atomic_connectivity_subset(
    collection: AtomisticFrameCollection,
    source: AtomicConnectivityResult,
    target_definition: HystereticDistanceConnectivity,
) -> AtomicConnectivityResult:
    """Project a broader hysteretic connectivity result onto an exact pair subset.

    This execution helper is intended for pipelines that need both a broad
    atomic graph and a framework-only graph with identical hysteresis rules for
    the shared pairs.  Computing the broad graph once and canonicalizing its
    pair-subset avoids a second trajectory-wide neighbor search and, unlike a
    cross-pass geometry cache, has bounded memory independent of frame count.

    The projection is exact only when the target uses ``formation_cutoff``
    initialization and every target formation/breaking cutoff is present with
    exactly the same radius in the source definition.  Those conditions are
    validated here rather than assumed by callers.
    """

    if not isinstance(source, AtomicConnectivityResult):
        raise TypeError("source must be an AtomicConnectivityResult.")
    if not isinstance(source.definition, HystereticDistanceConnectivity):
        raise ConnectivityDefinitionError(
            "Connectivity subset projection currently requires a hysteretic source definition."
        )
    if not isinstance(target_definition, HystereticDistanceConnectivity):
        raise ConnectivityDefinitionError(
            "Connectivity subset projection currently requires a hysteretic target definition."
        )
    if source.definition.initial_state != "formation_cutoff" or target_definition.initial_state != "formation_cutoff":
        raise ConnectivityDefinitionError(
            "Connectivity subset projection requires formation_cutoff initialization."
        )

    target_resolved = _resolve_connectivity_scope(collection, target_definition.scope)
    source_atoms = set(int(value) for value in source.resolved_scope.atom_indices)
    target_atoms = set(int(value) for value in target_resolved.atom_indices)
    if not target_atoms.issubset(source_atoms):
        raise ConnectivityScopeError(
            "Projected connectivity scope must be a subset of the source scope."
        )

    source_formation = source.definition.formation_cutoffs.cutoffs
    source_breaking = source.definition.breaking_cutoffs.cutoffs
    target_formation = target_definition.formation_cutoffs.cutoffs
    target_breaking = target_definition.breaking_cutoffs.cutoffs
    for pair, cutoff in target_formation.items():
        source_cutoff = source_formation.get(pair)
        if source_cutoff is None or float(source_cutoff.radius) != float(cutoff.radius):
            raise ConnectivityDefinitionError(
                f"Projected formation cutoff for pair {pair} is not identical to the source."
            )
    for pair, cutoff in target_breaking.items():
        source_cutoff = source_breaking.get(pair)
        if source_cutoff is None or float(source_cutoff.radius) != float(cutoff.radius):
            raise ConnectivityDefinitionError(
                f"Projected breaking cutoff for pair {pair} is not identical to the source."
            )

    target_pairs = frozenset(target_formation)
    numbers = np.asarray(collection.atomic_numbers, dtype=np.int32)
    membership = np.zeros(collection.n_atoms, dtype=np.bool_)
    membership[target_resolved.atom_indices] = True
    projected_unique: list[AtomicConnectivityState] = []
    state_build_cache: dict[tuple[AtomicEdgeKey, ...], AtomicConnectivityState] = {}

    for state in source.states:
        endpoints = np.asarray(state.edge_atom_indices, dtype=np.int64)
        shifts = np.asarray(state.edge_image_shifts, dtype=np.int64)
        retained: list[AtomicEdgeKey] = []
        for endpoint, shift in zip(endpoints, shifts, strict=True):
            atom_i = int(endpoint[0])
            atom_j = int(endpoint[1])
            if not (membership[atom_i] and membership[atom_j]):
                continue
            species_pair = tuple(sorted((int(numbers[atom_i]), int(numbers[atom_j]))))
            if species_pair not in target_pairs:
                continue
            retained.append(_trusted_atomic_edge_key(atom_i, atom_j, shift))
        projected_unique.append(
            _build_state(
                collection,
                target_resolved,
                tuple(retained),
                state_cache=state_build_cache,
            )
        )

    frame_states = [projected_unique[int(state_id)] for state_id in source.frame_state_ids]
    projected = _assemble_result(
        collection,
        target_definition,
        target_resolved,
        np.asarray(source.frame_indices, dtype=np.int64),
        frame_states,
        state_mode="catalog",
        atom_block_size=int(source.metadata.get("atom_block_size", 256)),
        diagnostics=[
            "exact pair-subset projection from broader hysteretic connectivity",
        ],
        neighbor_search_diagnostics={
            "backend": "projected_exact_pair_subset",
            "source_state_count": int(source.n_states),
            "projected_state_build_cache_entries": int(len(state_build_cache)),
            "scientific_identity_includes_cache_state": False,
        },
    )
    metadata = dict(projected.metadata)
    metadata["projection"] = {
        "mode": "exact_hysteretic_pair_subset_v1",
        "source_definition": source.definition.to_dict(),
        "source_state_count": int(source.n_states),
        "target_state_count": int(projected.n_states),
        "neighbor_geometry_recomputed": False,
    }
    return AtomicConnectivityResult(
        definition=projected.definition,
        resolved_scope=projected.resolved_scope,
        consistency=projected.consistency,
        frame_indices=projected.frame_indices,
        frame_ids=projected.frame_ids,
        frame_state_ids=projected.frame_state_ids,
        states=projected.states,
        segments=projected.segments,
        transitions=projected.transitions,
        metadata=metadata,
    )


def _assemble_result(
    collection: AtomisticFrameCollection,
    definition: AtomicConnectivityDefinition,
    resolved: ResolvedConnectivityScope,
    frames: IntArray,
    frame_states: Sequence[AtomicConnectivityState],
    *,
    state_mode: str,
    atom_block_size: int,
    diagnostics: list[str],
    neighbor_search_diagnostics: Mapping[str, Any],
) -> AtomicConnectivityResult:
    if state_mode == "per_frame":
        states = tuple(frame_states)
        state_ids = np.arange(len(states), dtype=np.int32)
        consistency = ConnectivityConsistency.PER_FRAME
        segments = None
        transitions: tuple[ConnectivityTransition, ...] = ()
    else:
        states, state_ids = _catalog_states(frame_states)
        consistency = (
            ConnectivityConsistency.UNIFORM
            if len(states) == 1
            else ConnectivityConsistency.PARTITIONED
        )
        if collection.is_trajectory:
            segments = _build_segments(state_ids)
            transitions = _build_transitions(
                states,
                segments,
                frames,
                np.asarray(collection.frame_ids, dtype=np.int64)[frames],
            )
        else:
            segments = None
            transitions = ()
    metadata = {
        "module": "atomic_connectivity",
        "definition_kind": definition.kind,
        "state_mode": state_mode,
        "frame_semantics": collection.frame_semantics.value,
        "strict_cutoff_inequality": "distance < cutoff",
        "canonical_schema_version": CANONICAL_CONNECTIVITY_SCHEMA,
        "digest_algorithm": CONNECTIVITY_DIGEST_ALGORITHM,
        "periodic_gauge": "smallest-root deterministic spanning forest",
        "unique_minimum_image_only": True,
        "atom_block_size": atom_block_size,
        "diagnostics": diagnostics,
        "neighbor_search": _json_safe(dict(neighbor_search_diagnostics)),
        "neighbor_cache": _json_safe(
            neighbor_search_diagnostics.get("cache_statistics")
        ),
        "provenance": (
            None
            if collection.provenance is None
            else _json_safe(asdict(collection.provenance))
        ),
    }
    return AtomicConnectivityResult(
        definition=definition,
        resolved_scope=resolved,
        consistency=consistency,
        frame_indices=frames,
        frame_ids=np.asarray(collection.frame_ids, dtype=np.int64)[frames],
        frame_state_ids=state_ids,
        states=states,
        segments=segments,
        transitions=transitions,
        metadata=metadata,
    )


def _resolve_connectivity_scope(
    collection: AtomisticFrameCollection, scope: ConnectivityScope
) -> ResolvedConnectivityScope:
    numbers = np.asarray(collection.atomic_numbers, dtype=np.int32)
    all_indices = set(range(collection.n_atoms))
    inclusion_supplied = (
        scope.included_species is not None or scope.included_atom_indices is not None
    )
    if inclusion_supplied:
        included: set[int] = set()
        if scope.included_species is not None:
            present_species = set(int(value) for value in np.unique(numbers))
            missing = set(scope.included_species) - present_species
            if missing:
                names = [chemical_symbols[value] for value in sorted(missing)]
                raise ConnectivityScopeError(
                    f"Explicitly included species are absent: {names}."
                )
            included.update(
                int(index)
                for index in np.flatnonzero(np.isin(numbers, scope.included_species))
            )
        if scope.included_atom_indices is not None:
            _validate_scope_indices(scope.included_atom_indices, collection.n_atoms)
            included.update(scope.included_atom_indices)
    else:
        included = all_indices
    if scope.excluded_species:
        excluded_species_indices = set(
            int(index)
            for index in np.flatnonzero(np.isin(numbers, scope.excluded_species))
        )
        included.difference_update(excluded_species_indices)
    if scope.excluded_atom_indices:
        _validate_scope_indices(scope.excluded_atom_indices, collection.n_atoms)
        included.difference_update(scope.excluded_atom_indices)
    if not included:
        raise ConnectivityScopeError("Connectivity scope resolves to zero atoms.")
    indices = np.asarray(sorted(included), dtype=np.int64)
    selected_numbers = numbers[indices].astype(np.int32, copy=True)
    key = (
        "resolved_scope_v1",
        tuple(int(value) for value in indices),
        tuple(int(value) for value in selected_numbers),
    )
    return ResolvedConnectivityScope(indices, selected_numbers, key)


def _build_requested_neighbor_list(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    center_indices: ArrayLike,
    candidate_neighbor_indices: ArrayLike,
    cutoff: Any,
    pair_counting: PairCounting,
    atom_block_size: int,
    neighbor_search: _NeighborSearchExecutor,
    geometry_cache: AtomicConnectivityGeometryCache | None = None,
):
    if geometry_cache is not None:
        return geometry_cache.get_or_build(
            collection,
            frame_index=frame_index,
            center_indices=center_indices,
            candidate_neighbor_indices=candidate_neighbor_indices,
            cutoff=cutoff,
            pair_counting=pair_counting,
            atom_block_size=atom_block_size,
            neighbor_search=neighbor_search,
        )
    return neighbor_search.build_neighbor_list(
        frame_index=frame_index,
        center_indices=center_indices,
        candidate_neighbor_indices=candidate_neighbor_indices,
        cutoff=cutoff,
        pair_counting=pair_counting,
        block_size=atom_block_size,
    )



def _nested_star_batch(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    resolved_scope: ResolvedConnectivityScope,
    outer_cutoffs: PairCutoffRegistry,
    inner_cutoffs: PairCutoffRegistry,
    atom_block_size: int,
    neighbor_search: _NeighborSearchExecutor,
    geometry_cache: AtomicConnectivityGeometryCache | None,
) -> tuple[
    dict[tuple[int, int], AtomicEdgeKey],
    dict[tuple[int, int], AtomicEdgeKey],
    bool,
] | None:
    """Batch heterospecies pair registries that form one species star.

    LTA connectivity is the canonical case: Si--O, Al--O, and Na/Li/K--O all
    share oxygen.  Evaluating those pairs separately performs several MIC
    kernels and neighbor-list constructions over the same total Cartesian pair
    set.  A single hub-vs-spokes request at the largest outer cutoff is exactly
    equivalent after filtering every accepted pair by its own registered outer
    and inner radius.

    ``None`` means the registry does not have a safely batchable star shape and
    the established per-pair implementation remains authoritative.
    """

    pairs = tuple(sorted(outer_cutoffs.cutoffs))
    if len(pairs) < 2 or any(a == b for a, b in pairs):
        return None
    common = set(pairs[0])
    for pair in pairs[1:]:
        common.intersection_update(pair)
    if len(common) != 1:
        return None
    hub = int(next(iter(common)))
    spokes = tuple(sorted({int(b if a == hub else a) for a, b in pairs}))
    if len(spokes) != len(pairs):
        return None
    if frozenset(inner_cutoffs.cutoffs) != frozenset(pairs):
        return None

    scoped_numbers = resolved_scope.atomic_numbers
    scoped_indices = resolved_scope.atom_indices
    center_indices = scoped_indices[scoped_numbers == hub]
    candidate_indices = scoped_indices[np.isin(scoped_numbers, spokes)]
    if center_indices.size == 0 or candidate_indices.size == 0:
        return ({}, {}, False)

    max_outer = max(float(outer_cutoffs.cutoffs[pair].radius) for pair in pairs)
    result = _build_requested_neighbor_list(
        collection,
        frame_index=frame_index,
        center_indices=center_indices,
        candidate_neighbor_indices=candidate_indices,
        cutoff=max_outer,
        pair_counting=PairCounting.DIRECTED,
        atom_block_size=atom_block_size,
        neighbor_search=neighbor_search,
        geometry_cache=geometry_cache,
    )
    numbers = np.asarray(collection.atomic_numbers, dtype=np.int32)
    outer_edges: dict[tuple[int, int], AtomicEdgeKey] = {}
    inner_edges: dict[tuple[int, int], AtomicEdgeKey] = {}
    centers = np.repeat(result.center_indices, result.coordination_counts)
    neighbors = np.asarray(result.neighbor_indices, dtype=np.int64)
    distances = np.asarray(result.distances, dtype=np.float64)
    center_numbers = numbers[centers]
    neighbor_numbers = numbers[neighbors]
    outer_radius = np.zeros(distances.shape, dtype=np.float64)
    inner_radius = np.zeros(distances.shape, dtype=np.float64)
    for pair in pairs:
        a, b = pair
        pair_mask = ((center_numbers == a) & (neighbor_numbers == b)) | (
            (center_numbers == b) & (neighbor_numbers == a)
        )
        if np.any(pair_mask):
            outer_radius[pair_mask] = float(outer_cutoffs.cutoffs[pair].radius)
            inner_radius[pair_mask] = float(inner_cutoffs.cutoffs[pair].radius)
    retained_indices = np.flatnonzero((outer_radius > 0.0) & (distances < outer_radius))
    for slot in retained_indices:
        center = int(centers[slot])
        neighbor = int(neighbors[slot])
        edge = _trusted_atomic_edge_key(center, neighbor, result.image_shifts[slot])
        previous = outer_edges.get(edge.pair)
        if previous is not None and previous != edge:
            raise ConnectivityGeometryError(
                "Parallel periodic edges between one atom pair are unsupported."
            )
        outer_edges[edge.pair] = edge
        if distances[slot] < inner_radius[slot]:
            inner_edges[edge.pair] = edge
    return outer_edges, inner_edges, True


def _enumerate_nested_distance_edges(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    resolved_scope: ResolvedConnectivityScope,
    outer_cutoffs: PairCutoffRegistry,
    inner_cutoffs: PairCutoffRegistry,
    atom_block_size: int,
    neighbor_search: _NeighborSearchExecutor,
    geometry_cache: AtomicConnectivityGeometryCache | None = None,
) -> tuple[
    dict[tuple[int, int], AtomicEdgeKey],
    dict[tuple[int, int], AtomicEdgeKey],
    bool,
]:
    """Enumerate an outer cutoff and inner subset in one geometry pass."""
    batched = _nested_star_batch(
        collection,
        frame_index=frame_index,
        resolved_scope=resolved_scope,
        outer_cutoffs=outer_cutoffs,
        inner_cutoffs=inner_cutoffs,
        atom_block_size=atom_block_size,
        neighbor_search=neighbor_search,
        geometry_cache=geometry_cache,
    )
    if batched is not None:
        return batched
    scoped_numbers = resolved_scope.atomic_numbers
    scoped_indices = resolved_scope.atom_indices
    outer_edges: dict[tuple[int, int], AtomicEdgeKey] = {}
    inner_edges: dict[tuple[int, int], AtomicEdgeKey] = {}
    eligible_pair_type = False
    for pair, outer_cutoff in sorted(outer_cutoffs.cutoffs.items()):
        inner_radius = inner_cutoffs.cutoffs[pair].radius
        a, b = pair
        indices_a = scoped_indices[scoped_numbers == a]
        indices_b = scoped_indices[scoped_numbers == b]
        if a == b:
            if indices_a.size < 2:
                continue
            eligible_pair_type = True
            result = _build_requested_neighbor_list(
                collection,
                frame_index=frame_index,
                center_indices=indices_a,
                candidate_neighbor_indices=indices_a,
                cutoff=outer_cutoff,
                pair_counting=PairCounting.UNORDERED_IDENTICAL,
                atom_block_size=atom_block_size,
                neighbor_search=neighbor_search,
                geometry_cache=geometry_cache,
            )
        else:
            if indices_a.size == 0 or indices_b.size == 0:
                continue
            eligible_pair_type = True
            result = _build_requested_neighbor_list(
                collection,
                frame_index=frame_index,
                center_indices=indices_a,
                candidate_neighbor_indices=indices_b,
                cutoff=outer_cutoff,
                pair_counting=PairCounting.DIRECTED,
                atom_block_size=atom_block_size,
                neighbor_search=neighbor_search,
                geometry_cache=geometry_cache,
            )
        centers = np.repeat(result.center_indices, result.coordination_counts)
        for center, neighbor, shift, distance in zip(
            centers,
            result.neighbor_indices,
            result.image_shifts,
            result.distances,
            strict=True,
        ):
            edge = _trusted_atomic_edge_key(center, neighbor, shift)
            previous = outer_edges.get(edge.pair)
            if previous is not None and previous != edge:
                raise ConnectivityGeometryError(
                    "Parallel periodic edges between one atom pair are unsupported."
                )
            outer_edges[edge.pair] = edge
            if float(distance) < inner_radius:
                inner_edges[edge.pair] = edge
    return outer_edges, inner_edges, eligible_pair_type


def _enumerate_distance_edges(
    collection: AtomisticFrameCollection,
    *,
    frame_index: int,
    resolved_scope: ResolvedConnectivityScope,
    cutoffs: PairCutoffRegistry,
    atom_block_size: int,
    neighbor_search: _NeighborSearchExecutor,
    geometry_cache: AtomicConnectivityGeometryCache | None = None,
) -> tuple[dict[tuple[int, int], AtomicEdgeKey], bool]:
    scoped_numbers = resolved_scope.atomic_numbers
    scoped_indices = resolved_scope.atom_indices
    edges: dict[tuple[int, int], AtomicEdgeKey] = {}
    eligible_pair_type = False
    for pair, cutoff in sorted(cutoffs.cutoffs.items()):
        a, b = pair
        indices_a = scoped_indices[scoped_numbers == a]
        indices_b = scoped_indices[scoped_numbers == b]
        if a == b:
            if indices_a.size < 2:
                continue
            eligible_pair_type = True
            result = _build_requested_neighbor_list(
                collection,
                frame_index=frame_index,
                center_indices=indices_a,
                candidate_neighbor_indices=indices_a,
                cutoff=cutoff,
                pair_counting=PairCounting.UNORDERED_IDENTICAL,
                atom_block_size=atom_block_size,
                neighbor_search=neighbor_search,
                geometry_cache=geometry_cache,
            )
        else:
            if indices_a.size == 0 or indices_b.size == 0:
                continue
            eligible_pair_type = True
            result = _build_requested_neighbor_list(
                collection,
                frame_index=frame_index,
                center_indices=indices_a,
                candidate_neighbor_indices=indices_b,
                cutoff=cutoff,
                pair_counting=PairCounting.DIRECTED,
                atom_block_size=atom_block_size,
                neighbor_search=neighbor_search,
                geometry_cache=geometry_cache,
            )
        centers = np.repeat(result.center_indices, result.coordination_counts)
        for center, neighbor, shift in zip(
            centers, result.neighbor_indices, result.image_shifts, strict=True
        ):
            edge = _trusted_atomic_edge_key(center, neighbor, shift)
            previous = edges.get(edge.pair)
            if previous is not None and previous != edge:
                raise ConnectivityGeometryError(
                    "Parallel periodic edges between one atom pair are unsupported."
                )
            edges[edge.pair] = edge
    return edges, eligible_pair_type


def _state_from_canonical_arrays(
    *,
    active_atom_indices: IntArray,
    active_atomic_numbers: Int32Array,
    pbc: BoolArray,
    edge_atom_indices: IntArray,
    edge_image_shifts: IntArray,
    degree: Int32Array,
    component_labels: Int32Array,
    n_components: int,
) -> AtomicConnectivityState:
    """Construct an internally proven canonical state without re-validating edges.

    ``AtomicConnectivityState`` remains a defensive public constructor.  The
    connectivity engine, however, has already canonicalized and validated every
    edge before reaching this point.  Re-instantiating ``AtomicEdgeKey`` for
    every edge of every frame was one of the dominant costs in long GFX3D
    trajectories.  This private factory freezes the owned canonical arrays and
    computes the unchanged authoritative digest exactly once.
    """

    active = np.asarray(active_atom_indices, dtype=np.int64)
    numbers = np.asarray(active_atomic_numbers, dtype=np.int32)
    periodic = np.asarray(pbc, dtype=np.bool_)
    endpoints = np.ascontiguousarray(edge_atom_indices, dtype=np.int64)
    shifts = np.ascontiguousarray(edge_image_shifts, dtype=np.int64)
    degrees = np.ascontiguousarray(degree, dtype=np.int32)
    labels = np.ascontiguousarray(component_labels, dtype=np.int32)
    for array in (active, numbers, periodic, endpoints, shifts, degrees, labels):
        # Inputs owned by the canonical engine are never mutated after state
        # construction.  Sharing the persistent scope arrays across frames also
        # avoids two 168-element copies per state in long trajectories.
        array.setflags(write=False)
    digest = _state_digest(active, numbers, periodic, endpoints, shifts)
    state = object.__new__(AtomicConnectivityState)
    object.__setattr__(state, "active_atom_indices", active)
    object.__setattr__(state, "active_atomic_numbers", numbers)
    object.__setattr__(state, "pbc", periodic)
    object.__setattr__(state, "edge_atom_indices", endpoints)
    object.__setattr__(state, "edge_image_shifts", shifts)
    object.__setattr__(state, "degree", degrees)
    object.__setattr__(state, "component_labels", labels)
    object.__setattr__(state, "n_components", int(n_components))
    object.__setattr__(state, "canonical_schema_version", CANONICAL_CONNECTIVITY_SCHEMA)
    object.__setattr__(state, "digest_algorithm", CONNECTIVITY_DIGEST_ALGORITHM)
    object.__setattr__(state, "digest", digest)
    return state


def _normalize_periodic_gauge_arrays(
    active_atom_indices: IntArray,
    edges: Sequence[AtomicEdgeKey],
    pbc: BoolArray,
    *,
    edges_are_normalized: bool = False,
) -> tuple[IntArray, IntArray, Int32Array, int, Int32Array]:
    """Array-oriented equivalent of :func:`_normalize_periodic_gauge`.

    Endpoint pairs are unique, so canonical gauge normalization can change only
    their image labels, never pair ordering.  Keeping endpoints/shifts as arrays
    removes hundreds of thousands of temporary ``AtomicEdgeKey`` validations
    from long trajectories while preserving the exact canonical state and digest.
    """

    active = tuple(int(value) for value in active_atom_indices)
    active_set = set(active)
    raw_edges = tuple(edges) if edges_are_normalized else _normalize_edge_tuple(edges)
    edge_count = len(raw_edges)
    endpoints = np.empty((edge_count, 2), dtype=np.int64)
    shifts = np.empty((edge_count, 3), dtype=np.int64)
    positions = {atom: index for index, atom in enumerate(active)}
    adjacency: list[list[tuple[int, int, int]]] = [[] for _ in active]

    for edge_index, edge in enumerate(raw_edges):
        if edge.atom_i not in active_set or edge.atom_j not in active_set:
            raise ConnectivityScopeError("Edge endpoint lies outside resolved scope.")
        shift = edge.image_shift
        if any((not bool(pbc[axis])) and int(shift[axis]) != 0 for axis in range(3)):
            raise ConnectivityGeometryError(
                "Edge image shift is nonzero along a nonperiodic axis."
            )
        endpoints[edge_index, 0] = edge.atom_i
        endpoints[edge_index, 1] = edge.atom_j
        shifts[edge_index, :] = shift
        left = positions[edge.atom_i]
        right = positions[edge.atom_j]
        adjacency[left].append((right, edge_index, 1))
        adjacency[right].append((left, edge_index, -1))

    # raw_edges is already sorted by (atom_i, atom_j, shift).  The edge pair is
    # unique, so adjacency iteration is deterministic by neighboring atom index.
    for items in adjacency:
        items.sort(key=lambda item: (item[0], item[1], item[2]))

    gauge = np.zeros((len(active), 3), dtype=np.int64)
    assigned = np.zeros(len(active), dtype=np.bool_)
    labels = np.empty(len(active), dtype=np.int32)
    component = 0
    for root in range(len(active)):
        if assigned[root]:
            continue
        assigned[root] = True
        labels[root] = component
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, edge_index, direction in adjacency[current]:
                if assigned[neighbor]:
                    continue
                edge_shift = shifts[edge_index]
                gauge[neighbor] = gauge[current] + (edge_shift if direction > 0 else -edge_shift)
                assigned[neighbor] = True
                labels[neighbor] = component
                queue.append(neighbor)
        component += 1

    if edge_count:
        local_left = np.fromiter(
            (positions[int(value)] for value in endpoints[:, 0]),
            dtype=np.int64,
            count=edge_count,
        )
        local_right = np.fromiter(
            (positions[int(value)] for value in endpoints[:, 1]),
            dtype=np.int64,
            count=edge_count,
        )
        shifts = shifts + gauge[local_left] - gauge[local_right]
        degree = np.bincount(
            np.concatenate((local_left, local_right)), minlength=len(active)
        ).astype(np.int32, copy=False)
    else:
        degree = np.zeros(len(active), dtype=np.int32)
    return endpoints, shifts, labels, component, degree


def _build_state(
    collection: AtomisticFrameCollection,
    resolved: ResolvedConnectivityScope,
    edges: Sequence[AtomicEdgeKey],
    *,
    state_cache: dict[tuple[AtomicEdgeKey, ...], AtomicConnectivityState] | None = None,
) -> AtomicConnectivityState:
    normalized_edges = _normalize_edge_tuple(edges)
    if state_cache is not None:
        cached = state_cache.get(normalized_edges)
        if cached is not None:
            return cached
    pbc = np.asarray(collection.pbc, dtype=bool)
    endpoints, shifts, labels, n_components, degree = _normalize_periodic_gauge_arrays(
        resolved.atom_indices, normalized_edges, pbc, edges_are_normalized=True
    )
    state = _state_from_canonical_arrays(
        active_atom_indices=resolved.atom_indices,
        active_atomic_numbers=resolved.atomic_numbers,
        pbc=pbc,
        edge_atom_indices=endpoints,
        edge_image_shifts=shifts,
        degree=degree,
        component_labels=labels,
        n_components=n_components,
    )
    if state_cache is not None:
        # Retaining every raw ``AtomicEdgeKey`` tuple is counterproductive for
        # highly fragmented trajectories: a 10k-frame run can otherwise keep
        # millions of Python edge objects alive solely as cache keys.  The
        # cache exists only to avoid repeating canonicalization for nearby
        # recurring states, so a bounded FIFO window preserves the common-case
        # speedup while making memory independent of trajectory length.
        if len(state_cache) >= _STATE_BUILD_CACHE_MAX_ENTRIES:
            state_cache.pop(next(iter(state_cache)))
        state_cache[normalized_edges] = state
    return state


def _normalize_periodic_gauge(
    active_atom_indices: IntArray,
    edges: Sequence[AtomicEdgeKey],
    pbc: BoolArray,
) -> tuple[tuple[AtomicEdgeKey, ...], Int32Array, int, Int32Array]:
    active = tuple(int(value) for value in active_atom_indices)
    active_set = set(active)
    raw_edges = _normalize_edge_tuple(edges)
    pair_seen: set[tuple[int, int]] = set()
    adjacency: dict[int, list[tuple[int, np.ndarray]]] = {atom: [] for atom in active}
    for edge in raw_edges:
        if edge.atom_i not in active_set or edge.atom_j not in active_set:
            raise ConnectivityScopeError("Edge endpoint lies outside resolved scope.")
        if edge.pair in pair_seen:
            raise ConnectivityGeometryError(
                "Parallel periodic atomic edges are unsupported in the first release."
            )
        pair_seen.add(edge.pair)
        shift = np.asarray(edge.image_shift, dtype=np.int64)
        if np.any(shift[~pbc] != 0):
            raise ConnectivityGeometryError(
                "Edge image shift is nonzero along a nonperiodic axis."
            )
        adjacency[edge.atom_i].append((edge.atom_j, shift))
        adjacency[edge.atom_j].append((edge.atom_i, -shift))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], *item[1].tolist()))

    gauge: dict[int, np.ndarray] = {}
    component_by_atom: dict[int, int] = {}
    component = 0
    for root in active:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        component_by_atom[root] = component
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, directed_shift in adjacency[current]:
                if neighbor in gauge:
                    continue
                gauge[neighbor] = gauge[current] + directed_shift
                component_by_atom[neighbor] = component
                queue.append(neighbor)
        component += 1

    normalized: list[AtomicEdgeKey] = []
    for edge in raw_edges:
        shift = (
            np.asarray(edge.image_shift, dtype=np.int64)
            + gauge[edge.atom_i]
            - gauge[edge.atom_j]
        )
        normalized.append(
            AtomicEdgeKey(edge.atom_i, edge.atom_j, tuple(int(x) for x in shift))
        )
    normalized_tuple = tuple(sorted(normalized))
    labels = np.asarray([component_by_atom[atom] for atom in active], dtype=np.int32)
    degree = np.zeros(len(active), dtype=np.int32)
    positions = {atom: index for index, atom in enumerate(active)}
    for edge in normalized_tuple:
        degree[positions[edge.atom_i]] += 1
        degree[positions[edge.atom_j]] += 1
    return normalized_tuple, labels, component, degree


def _catalog_states(
    frame_states: Sequence[AtomicConnectivityState],
) -> tuple[tuple[AtomicConnectivityState, ...], Int32Array]:
    groups: dict[str, list[int]] = {}
    unique: list[AtomicConnectivityState] = []
    frame_unique_indices: list[int] = []
    for state in frame_states:
        match_index: int | None = None
        for candidate_index in groups.get(state.digest, []):
            if _states_equal(unique[candidate_index], state):
                match_index = candidate_index
                break
        if match_index is None:
            match_index = len(unique)
            unique.append(state)
            groups.setdefault(state.digest, []).append(match_index)
        frame_unique_indices.append(match_index)
    order = sorted(range(len(unique)), key=lambda index: _state_sort_key(unique[index]))
    remap = {old: new for new, old in enumerate(order)}
    states = tuple(unique[old] for old in order)
    ids = np.asarray([remap[old] for old in frame_unique_indices], dtype=np.int32)
    return states, ids


def _build_segments(state_ids: Int32Array) -> tuple[ConnectivitySegment, ...]:
    segments: list[ConnectivitySegment] = []
    start = 0
    for position in range(1, state_ids.size + 1):
        if position == state_ids.size or state_ids[position] != state_ids[start]:
            segments.append(
                ConnectivitySegment(
                    segment_id=len(segments),
                    state_id=int(state_ids[start]),
                    result_position_start=start,
                    result_position_stop=position,
                )
            )
            start = position
    return tuple(segments)


def _build_transitions(
    states: tuple[AtomicConnectivityState, ...],
    segments: tuple[ConnectivitySegment, ...],
    frame_indices: IntArray,
    frame_ids: IntArray,
) -> tuple[ConnectivityTransition, ...]:
    transitions: list[ConnectivityTransition] = []
    for before, after in zip(segments[:-1], segments[1:], strict=True):
        position_before = before.result_position_stop - 1
        position_after = after.result_position_start
        added, removed = _edge_pair_difference(
            states[before.state_id], states[after.state_id]
        )
        affected = tuple(
            sorted(
                {
                    atom
                    for edge in (*added, *removed)
                    for atom in (edge.atom_i, edge.atom_j)
                }
            )
        )
        transitions.append(
            ConnectivityTransition(
                transition_id=len(transitions),
                source_state_id=before.state_id,
                target_state_id=after.state_id,
                result_position_before=position_before,
                result_position_after=position_after,
                collection_frame_index_before=int(frame_indices[position_before]),
                collection_frame_index_after=int(frame_indices[position_after]),
                frame_id_before=int(frame_ids[position_before]),
                frame_id_after=int(frame_ids[position_after]),
                added_edges=added,
                removed_edges=removed,
                affected_atom_indices=affected,
            )
        )
    return tuple(transitions)


def _edge_pair_difference(
    source: AtomicConnectivityState,
    target: AtomicConnectivityState,
) -> tuple[tuple[AtomicEdgeKey, ...], tuple[AtomicEdgeKey, ...]]:
    """Return pair additions/removals without materializing both full edge maps.

    Canonical state endpoints are lexicographically sorted and pair-unique.  A
    linear merge therefore finds the same pair-only transition semantics while
    constructing ``AtomicEdgeKey`` objects only for the usually tiny changed
    subset.  This is important for GFX3D trajectories with thousands of short
    connectivity-state segments.
    """

    source_pairs = np.asarray(source.edge_atom_indices, dtype=np.int64)
    target_pairs = np.asarray(target.edge_atom_indices, dtype=np.int64)
    source_shifts = np.asarray(source.edge_image_shifts, dtype=np.int64)
    target_shifts = np.asarray(target.edge_image_shifts, dtype=np.int64)
    i = 0
    j = 0
    added: list[AtomicEdgeKey] = []
    removed: list[AtomicEdgeKey] = []
    while i < source_pairs.shape[0] and j < target_pairs.shape[0]:
        source_pair = (int(source_pairs[i, 0]), int(source_pairs[i, 1]))
        target_pair = (int(target_pairs[j, 0]), int(target_pairs[j, 1]))
        if source_pair == target_pair:
            i += 1
            j += 1
        elif source_pair < target_pair:
            removed.append(
                AtomicEdgeKey(
                    source_pair[0],
                    source_pair[1],
                    tuple(int(value) for value in source_shifts[i]),
                )
            )
            i += 1
        else:
            added.append(
                AtomicEdgeKey(
                    target_pair[0],
                    target_pair[1],
                    tuple(int(value) for value in target_shifts[j]),
                )
            )
            j += 1
    while i < source_pairs.shape[0]:
        removed.append(
            AtomicEdgeKey(
                int(source_pairs[i, 0]),
                int(source_pairs[i, 1]),
                tuple(int(value) for value in source_shifts[i]),
            )
        )
        i += 1
    while j < target_pairs.shape[0]:
        added.append(
            AtomicEdgeKey(
                int(target_pairs[j, 0]),
                int(target_pairs[j, 1]),
                tuple(int(value) for value in target_shifts[j]),
            )
        )
        j += 1
    return tuple(added), tuple(removed)


def _explicit_edges_for_frame(
    definition: ExplicitConnectivity, frame_index: int
) -> tuple[AtomicEdgeKey, ...]:
    if definition.uniform_edges is not None:
        return definition.uniform_edges
    assert definition.frame_edges is not None
    try:
        return definition.frame_edges[frame_index]
    except KeyError as exc:
        raise ConnectivityFrameSelectionError(
            f"Explicit connectivity has no edge set for collection frame {frame_index}."
        ) from exc


def _validate_edges_against_scope(
    edges: Sequence[AtomicEdgeKey],
    resolved: ResolvedConnectivityScope,
    collection: AtomisticFrameCollection,
) -> None:
    active = set(int(value) for value in resolved.atom_indices)
    for edge in edges:
        if edge.atom_i >= collection.n_atoms or edge.atom_j >= collection.n_atoms:
            raise ConnectivityScopeError("Explicit edge contains an out-of-range atom.")
        if edge.atom_i not in active or edge.atom_j not in active:
            raise ConnectivityScopeError("Explicit edge endpoint lies outside scope.")
        shift = np.asarray(edge.image_shift, dtype=np.int64)
        if np.any(shift[~np.asarray(collection.pbc, dtype=bool)] != 0):
            raise ConnectivityGeometryError(
                "Explicit edge shifts must be zero along nonperiodic axes."
            )


def _validate_edges_against_registry(
    edges: Sequence[AtomicEdgeKey],
    registry: PairCutoffRegistry,
    collection: AtomisticFrameCollection,
) -> None:
    numbers = np.asarray(collection.atomic_numbers, dtype=np.int32)
    for edge in edges:
        pair = tuple(sorted((int(numbers[edge.atom_i]), int(numbers[edge.atom_j]))))
        if pair not in registry.cutoffs:
            raise ConnectivityDefinitionError(
                f"Initial edge {edge.pair} uses unregistered species pair {pair}."
            )


def _definition_to_dict(definition: AtomicConnectivityDefinition) -> dict[str, Any]:
    return definition.to_dict()


def _definition_from_dict(payload: Mapping[str, Any]) -> AtomicConnectivityDefinition:
    kind = payload["kind"]
    scope = ConnectivityScope.from_dict(payload["scope"])
    if kind == "distance":
        return DistanceConnectivity(
            cutoffs=_registry_from_dict(payload["cutoffs"]), scope=scope
        )
    if kind == "hysteretic_distance":
        initial_payload = payload.get("initial_edges")
        return HystereticDistanceConnectivity(
            formation_cutoffs=_registry_from_dict(payload["formation_cutoffs"]),
            breaking_cutoffs=_registry_from_dict(payload["breaking_cutoffs"]),
            scope=scope,
            initial_state=payload["initial_state"],
            initial_edges=(
                None
                if initial_payload is None
                else tuple(AtomicEdgeKey.from_dict(item) for item in initial_payload)
            ),
        )
    if kind == "reference_distance":
        return ReferenceDistanceConnectivity(
            discovery_cutoffs=_registry_from_dict(payload["discovery_cutoffs"]),
            formation_cutoffs=_registry_from_dict(payload["formation_cutoffs"]),
            retention_cutoffs=_registry_from_dict(payload["retention_cutoffs"]),
            reference_frame=int(payload["reference_frame"]),
            scope=scope,
        )
    if kind == "explicit":
        uniform = payload.get("uniform_edges")
        frame_payload = payload.get("frame_edges")
        return ExplicitConnectivity(
            scope=scope,
            uniform_edges=(
                None
                if uniform is None
                else tuple(AtomicEdgeKey.from_dict(item) for item in uniform)
            ),
            frame_edges=(
                None
                if frame_payload is None
                else {
                    int(frame): tuple(AtomicEdgeKey.from_dict(item) for item in edges)
                    for frame, edges in frame_payload.items()
                }
            ),
        )
    raise ConnectivityDefinitionError(f"Unknown connectivity definition kind {kind!r}.")


def _registry_from_dict(payload: Mapping[str, Any]) -> PairCutoffRegistry:
    from .cutoffs import PairCutoff

    cutoffs = []
    for item in payload.values():
        cutoffs.append(PairCutoff.from_dict(item))
    return PairCutoffRegistry.from_cutoffs(cutoffs)


def _state_digest(
    active: IntArray,
    numbers: Int32Array,
    pbc: BoolArray,
    endpoints: IntArray,
    shifts: IntArray,
) -> str:
    payload = {
        "schema": CANONICAL_CONNECTIVITY_SCHEMA,
        "active_atom_indices": np.asarray(active, dtype=np.int64).tolist(),
        "active_atomic_numbers": np.asarray(numbers, dtype=np.int32).tolist(),
        "pbc": np.asarray(pbc, dtype=bool).astype(int).tolist(),
        "edge_atom_indices": np.asarray(endpoints, dtype=np.int64)
        .reshape(-1, 2)
        .tolist(),
        "edge_image_shifts": np.asarray(shifts, dtype=np.int64).reshape(-1, 3).tolist(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _state_sort_key(state: AtomicConnectivityState) -> tuple[Any, ...]:
    return (
        tuple(int(x) for x in state.active_atom_indices),
        tuple(int(x) for x in state.active_atomic_numbers),
        tuple(bool(x) for x in state.pbc),
        tuple(tuple(int(x) for x in row) for row in state.edge_atom_indices),
        tuple(tuple(int(x) for x in row) for row in state.edge_image_shifts),
    )


def _states_equal(a: AtomicConnectivityState, b: AtomicConnectivityState) -> bool:
    return (
        a.canonical_schema_version == b.canonical_schema_version
        and np.array_equal(a.active_atom_indices, b.active_atom_indices)
        and np.array_equal(a.active_atomic_numbers, b.active_atomic_numbers)
        and np.array_equal(a.pbc, b.pbc)
        and np.array_equal(a.edge_atom_indices, b.edge_atom_indices)
        and np.array_equal(a.edge_image_shifts, b.edge_image_shifts)
    )


def _normalize_edge_tuple(edges: Sequence[AtomicEdgeKey]) -> tuple[AtomicEdgeKey, ...]:
    normalized = tuple(
        edge if isinstance(edge, AtomicEdgeKey) else AtomicEdgeKey(*edge)  # type: ignore[arg-type]
        for edge in edges
    )
    pairs: dict[tuple[int, int], AtomicEdgeKey] = {}
    for edge in normalized:
        previous = pairs.get(edge.pair)
        if previous is not None:
            if previous != edge:
                raise ConnectivityGeometryError(
                    "Parallel periodic atomic edges are unsupported."
                )
            raise ConnectivityGeometryError("Duplicate atomic edge supplied.")
        pairs[edge.pair] = edge
    return tuple(sorted(normalized))


def _require_same_registry_pairs(
    first: PairCutoffRegistry, second: PairCutoffRegistry, name: str
) -> None:
    if set(first.cutoffs) != set(second.cutoffs):
        raise ConnectivityDefinitionError(
            f"{name.capitalize()} cutoff registries must contain identical pair keys."
        )


def _validate_registry_for_frames(
    registry: PairCutoffRegistry,
    collection: AtomisticFrameCollection,
    frames: IntArray,
) -> None:
    registry.validate_for_collection(collection, frame_indices=frames)


def _validated_frames(
    collection: AtomisticFrameCollection, frame_indices: ArrayLike | None
) -> IntArray:
    if frame_indices is None:
        return np.arange(collection.n_frames, dtype=np.int64)
    raw = np.asarray(frame_indices)
    if raw.ndim != 1 or not np.issubdtype(raw.dtype, np.integer):
        raise ConnectivityFrameSelectionError(
            "frame_indices must be a one-dimensional integer array."
        )
    frames = raw.astype(np.int64, copy=True)
    if frames.size == 0:
        raise ConnectivityFrameSelectionError("frame_indices is empty.")
    frames[frames < 0] += collection.n_frames
    if np.any(frames < 0) or np.any(frames >= collection.n_frames):
        raise ConnectivityFrameSelectionError(
            "frame_indices contains an invalid frame."
        )
    if np.unique(frames).size != frames.size:
        raise ConnectivityFrameSelectionError("frame_indices contains duplicates.")
    return frames


def _validated_single_frame(
    collection: AtomisticFrameCollection, frame_index: int
) -> int:
    frame = _coerce_int(frame_index, name="frame_index")
    if frame < 0:
        frame += collection.n_frames
    if frame < 0 or frame >= collection.n_frames:
        raise ConnectivityFrameSelectionError("frame_index is outside the collection.")
    return frame


def _validated_block_size(value: int) -> int:
    block = _coerce_int(value, name="atom_block_size")
    if block <= 0:
        raise ValueError("atom_block_size must be positive.")
    return block


def _validated_state_id(value: int, n_states: int) -> int:
    index = _coerce_int(value, name="state_id")
    if index < 0 or index >= n_states:
        raise IndexError("state_id is outside the result.")
    return index


def _validate_scope_indices(indices: Sequence[int], n_atoms: int) -> None:
    if any(index < 0 or index >= n_atoms for index in indices):
        raise ConnectivityScopeError(
            "Connectivity scope contains an out-of-range atom."
        )


def _readonly_array(value: ArrayLike, dtype: Any, *, ndim: int) -> NDArray[Any]:
    array = np.ascontiguousarray(np.asarray(value, dtype=dtype)).copy()
    if array.ndim != ndim:
        raise AtomicConnectivityError(f"Expected a {ndim}-dimensional array.")
    array.setflags(write=False)
    return array


def _coerce_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TypeError(f"{name} must be an integer.")
    return int(value)


def _coerce_shift(value: Sequence[int]) -> tuple[int, int, int]:
    raw = np.asarray(value)
    if raw.shape != (3,) or not np.issubdtype(raw.dtype, np.integer):
        raise ConnectivityGeometryError(
            "image_shift must be a three-item integer tuple."
        )
    return tuple(int(item) for item in raw)  # type: ignore[return-value]


def _optional_tuple(value: Any) -> tuple[Any, ...] | None:
    return None if value is None else tuple(value)


def _to_tuple(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_to_tuple(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((key, _to_tuple(item)) for key, item in value.items()))
    return value


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    copied = _json_safe(value)
    if not isinstance(copied, dict):
        raise TypeError("metadata must serialize to a mapping.")
    return copied


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)
