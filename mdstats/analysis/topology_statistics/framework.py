"""Framework-topology statistics derived from completed topology catalogs.

This module is the TS2 layer of the topology-statistics architecture. It
summarizes :class:`~mdstats.analysis.topology_catalog.TopologyCatalog` objects
without rebuilding atomic connectivity, changing framework mappings, or
enumerating rings.

Descriptors are evaluated once per unique framework topology and expanded
through the catalog's frame-to-topology assignment. Whole-path bridge
signatures preserve the Stage 2 rule that a path is equivalent only to reversal
of the complete path.
"""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeAlias

import numpy as np
from ase.data import atomic_numbers, chemical_symbols
from numpy.typing import ArrayLike, NDArray

from ...semantics import FrameSemantics
from ..framework_topology import (
    CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA,
    FrameworkEdgeKey,
    FrameworkEdgePath,
    FrameworkTopology,
)
from ..topology_catalog import (
    CANONICAL_TOPOLOGY_CATALOG_SCHEMA,
    TopologyCatalog,
)
from ._common import (
    DEFAULT_QUANTILES,
    TOPOLOGY_STATISTICS_DIGEST_ALGORITHM,
    CatalogOccupancyStatistics,
    DiscreteCountDistribution,
    FrameAxis,
    ScalarSeries,
    ScalarSummary,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    TopologyStatisticsSerializationError,
    build_frame_axis,
    build_scalar_series,
    canonical_statistics_json,
    compute_catalog_occupancy_statistics,
    compute_discrete_count_distribution,
    compute_scalar_summary,
    expand_state_values_to_frames,
)
from .temporal import (
    EntityPresenceEpisode,
    EntityPresenceStatistics,
    StateTransitionStatistics,
    TemporalStatisticsOptions,
    compute_entity_presence_statistics,
    compute_state_transition_statistics,
)

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]
FrameworkSpeciesPair: TypeAlias = tuple[int, int]

CANONICAL_FRAMEWORK_TOPOLOGY_STATISTICS_SCHEMA = (
    "mdstats.topology-statistics.framework.v2"
)

_DESCRIPTOR_LABELS = {
    "vertex_count": ("Framework vertices", "vertices"),
    "edge_count": ("Projected framework edges", "edges"),
    "component_count": ("Framework components", "components"),
    "isolated_vertex_count": ("Isolated framework vertices", "vertices"),
    "self_image_edge_count": ("Self-image framework edges", "edges"),
    "parallel_endpoint_pair_count": ("Parallel endpoint pairs", "pairs"),
    "parallel_edge_excess_count": ("Excess parallel edges", "edges"),
    "cycle_rank": ("Graph cycle-space rank", "dimension"),
}


@dataclass(frozen=True, slots=True)
class FrameworkStatisticsOptions:
    """Controls optional TS2 framework-topology statistics."""

    include_degree_statistics: bool = True
    include_edge_occupancies: bool = True
    include_transition_statistics: bool = True
    include_temporal_statistics: bool = True
    include_edge_episodes: bool = True
    temporal_options: TemporalStatisticsOptions = field(
        default_factory=TemporalStatisticsOptions
    )
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES

    def __post_init__(self) -> None:
        quantiles = _validated_quantiles(self.quantiles)
        for name in (
            "include_degree_statistics",
            "include_edge_occupancies",
            "include_transition_statistics",
            "include_temporal_statistics",
            "include_edge_episodes",
        ):
            value = getattr(self, name)
            if not isinstance(value, (bool, np.bool_)):
                raise TopologyStatisticsInputError(f"{name} must be boolean.")
            object.__setattr__(self, name, bool(value))
        object.__setattr__(self, "quantiles", quantiles)
        if not isinstance(self.temporal_options, TemporalStatisticsOptions):
            raise TopologyStatisticsInputError(
                "temporal_options must be TemporalStatisticsOptions."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "include_degree_statistics": self.include_degree_statistics,
            "include_edge_occupancies": self.include_edge_occupancies,
            "include_transition_statistics": self.include_transition_statistics,
            "include_temporal_statistics": self.include_temporal_statistics,
            "include_edge_episodes": self.include_edge_episodes,
            "temporal_options": self.temporal_options.to_dict(),
            "quantiles": list(self.quantiles),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkStatisticsOptions":
        return cls(
            include_degree_statistics=payload.get("include_degree_statistics", True),
            include_edge_occupancies=payload.get("include_edge_occupancies", True),
            include_transition_statistics=payload.get(
                "include_transition_statistics", True
            ),
            include_temporal_statistics=payload.get(
                "include_temporal_statistics", True
            ),
            include_edge_episodes=payload.get("include_edge_episodes", True),
            temporal_options=TemporalStatisticsOptions.from_dict(
                _mapping(payload.get("temporal_options", {}), name="temporal_options")
            ),
            quantiles=tuple(
                float(x) for x in payload.get("quantiles", DEFAULT_QUANTILES)
            ),
        )


@dataclass(frozen=True, order=True, slots=True)
class FrameworkBridgeSignature:
    """Chemical whole-path signature modulo reversal of the complete path."""

    path_atomic_numbers: tuple[int, ...]
    rule_id: str
    edge_kind: str

    def __post_init__(self) -> None:
        path = tuple(_atomic_number(value) for value in self.path_atomic_numbers)
        if len(path) < 2:
            raise TopologyStatisticsConsistencyError(
                "A bridge signature requires at least two endpoint species."
            )
        reverse = tuple(reversed(path))
        path = min(path, reverse)
        rule_id = str(self.rule_id).strip()
        edge_kind = str(self.edge_kind).strip()
        if not rule_id or not edge_kind:
            raise TopologyStatisticsConsistencyError(
                "rule_id and edge_kind must be nonempty."
            )
        object.__setattr__(self, "path_atomic_numbers", path)
        object.__setattr__(self, "rule_id", rule_id)
        object.__setattr__(self, "edge_kind", edge_kind)

    @classmethod
    def from_symbols(
        cls,
        path_symbols: Sequence[str],
        *,
        rule_id: str,
        edge_kind: str = "framework",
    ) -> "FrameworkBridgeSignature":
        return cls(
            path_atomic_numbers=tuple(_atomic_number(value) for value in path_symbols),
            rule_id=rule_id,
            edge_kind=edge_kind,
        )

    @property
    def symbols(self) -> tuple[str, ...]:
        return tuple(chemical_symbols[value] for value in self.path_atomic_numbers)

    @property
    def label(self) -> str:
        return "-".join(self.symbols)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path_atomic_numbers": list(self.path_atomic_numbers),
            "rule_id": self.rule_id,
            "edge_kind": self.edge_kind,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkBridgeSignature":
        return cls(
            path_atomic_numbers=tuple(int(x) for x in payload["path_atomic_numbers"]),
            rule_id=str(payload["rule_id"]),
            edge_kind=str(payload["edge_kind"]),
        )


@dataclass(frozen=True, slots=True)
class FrameworkGraphDescriptorStatistics:
    """Exact topology- and frame-resolved statistics for one integer descriptor."""

    descriptor: str
    topology_values: IntArray
    series: ScalarSeries
    distribution: DiscreteCountDistribution

    def __post_init__(self) -> None:
        descriptor = str(self.descriptor).strip()
        if descriptor not in _DESCRIPTOR_LABELS:
            raise TopologyStatisticsConsistencyError(
                f"Unknown framework descriptor: {descriptor!r}."
            )
        values = _readonly_int_array(self.topology_values, ndim=1)
        if values.size == 0 or np.any(values < 0):
            raise TopologyStatisticsConsistencyError(
                "topology_values must be a nonempty nonnegative integer vector."
            )
        if not isinstance(self.series, ScalarSeries) or not isinstance(
            self.distribution, DiscreteCountDistribution
        ):
            raise TopologyStatisticsConsistencyError(
                "series and distribution have the wrong type."
            )
        frame_values = np.asarray(self.series.values, dtype=np.int64)
        if not np.array_equal(frame_values, self.series.values):
            raise TopologyStatisticsConsistencyError(
                "Framework descriptor series must contain integers."
            )
        support, frequencies = np.unique(frame_values, return_counts=True)
        if not np.array_equal(support, self.distribution.support) or not np.array_equal(
            frequencies, self.distribution.frequencies
        ):
            raise TopologyStatisticsConsistencyError(
                "Descriptor distribution disagrees with its frame series."
            )
        object.__setattr__(self, "descriptor", descriptor)
        object.__setattr__(self, "topology_values", values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "descriptor": self.descriptor,
            "topology_values": self.topology_values.tolist(),
            "series": self.series.to_dict(),
            "distribution": self.distribution.to_dict(),
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "FrameworkGraphDescriptorStatistics":
        return cls(
            descriptor=str(payload["descriptor"]),
            topology_values=np.asarray(payload["topology_values"], dtype=np.int64),
            series=ScalarSeries.from_dict(_mapping(payload["series"], name="series")),
            distribution=DiscreteCountDistribution.from_dict(
                _mapping(payload["distribution"], name="distribution")
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkEndpointPairStatistics:
    """Projected-edge counts for one unordered framework endpoint species pair."""

    species_pair: FrameworkSpeciesPair
    topology_edge_counts: IntArray
    edge_count_series: ScalarSeries
    edge_count_distribution: DiscreteCountDistribution

    def __post_init__(self) -> None:
        pair = _canonical_species_pair(self.species_pair)
        values = _readonly_int_array(self.topology_edge_counts, ndim=1)
        if values.size == 0 or np.any(values < 0):
            raise TopologyStatisticsConsistencyError(
                "topology_edge_counts must be nonempty and nonnegative."
            )
        if not isinstance(self.edge_count_series, ScalarSeries) or not isinstance(
            self.edge_count_distribution, DiscreteCountDistribution
        ):
            raise TopologyStatisticsConsistencyError(
                "Endpoint-pair statistics have invalid result objects."
            )
        frame_values = np.asarray(self.edge_count_series.values, dtype=np.int64)
        support, frequencies = np.unique(frame_values, return_counts=True)
        if not np.array_equal(
            support, self.edge_count_distribution.support
        ) or not np.array_equal(frequencies, self.edge_count_distribution.frequencies):
            raise TopologyStatisticsConsistencyError(
                "Endpoint-pair distribution disagrees with its frame series."
            )
        object.__setattr__(self, "species_pair", pair)
        object.__setattr__(self, "topology_edge_counts", values)

    @property
    def symbols(self) -> tuple[str, str]:
        return tuple(chemical_symbols[x] for x in self.species_pair)  # type: ignore[return-value]

    @property
    def label(self) -> str:
        return "-".join(self.symbols)

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_pair": list(self.species_pair),
            "topology_edge_counts": self.topology_edge_counts.tolist(),
            "edge_count_series": self.edge_count_series.to_dict(),
            "edge_count_distribution": self.edge_count_distribution.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkEndpointPairStatistics":
        return cls(
            species_pair=tuple(int(x) for x in payload["species_pair"]),
            topology_edge_counts=np.asarray(
                payload["topology_edge_counts"], dtype=np.int64
            ),
            edge_count_series=ScalarSeries.from_dict(
                _mapping(payload["edge_count_series"], name="edge_count_series")
            ),
            edge_count_distribution=DiscreteCountDistribution.from_dict(
                _mapping(
                    payload["edge_count_distribution"],
                    name="edge_count_distribution",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkBridgeSignatureStatistics:
    """Projected-edge counts for one orientation-aware bridge signature."""

    signature: FrameworkBridgeSignature
    topology_edge_counts: IntArray
    edge_count_series: ScalarSeries
    edge_count_distribution: DiscreteCountDistribution

    def __post_init__(self) -> None:
        if not isinstance(self.signature, FrameworkBridgeSignature):
            raise TopologyStatisticsConsistencyError("signature has the wrong type.")
        values = _readonly_int_array(self.topology_edge_counts, ndim=1)
        if values.size == 0 or np.any(values < 0):
            raise TopologyStatisticsConsistencyError(
                "topology_edge_counts must be nonempty and nonnegative."
            )
        if not isinstance(self.edge_count_series, ScalarSeries) or not isinstance(
            self.edge_count_distribution, DiscreteCountDistribution
        ):
            raise TopologyStatisticsConsistencyError(
                "Bridge-signature statistics have invalid result objects."
            )
        frame_values = np.asarray(self.edge_count_series.values, dtype=np.int64)
        support, frequencies = np.unique(frame_values, return_counts=True)
        if not np.array_equal(
            support, self.edge_count_distribution.support
        ) or not np.array_equal(frequencies, self.edge_count_distribution.frequencies):
            raise TopologyStatisticsConsistencyError(
                "Bridge-signature distribution disagrees with its frame series."
            )
        object.__setattr__(self, "topology_edge_counts", values)

    @property
    def label(self) -> str:
        return self.signature.label

    def to_dict(self) -> dict[str, Any]:
        return {
            "signature": self.signature.to_dict(),
            "topology_edge_counts": self.topology_edge_counts.tolist(),
            "edge_count_series": self.edge_count_series.to_dict(),
            "edge_count_distribution": self.edge_count_distribution.to_dict(),
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "FrameworkBridgeSignatureStatistics":
        return cls(
            signature=FrameworkBridgeSignature.from_dict(
                _mapping(payload["signature"], name="signature")
            ),
            topology_edge_counts=np.asarray(
                payload["topology_edge_counts"], dtype=np.int64
            ),
            edge_count_series=ScalarSeries.from_dict(
                _mapping(payload["edge_count_series"], name="edge_count_series")
            ),
            edge_count_distribution=DiscreteCountDistribution.from_dict(
                _mapping(
                    payload["edge_count_distribution"],
                    name="edge_count_distribution",
                )
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkEdgeOccupancy:
    """Frame occupancy of one canonical projected framework edge."""

    edge_key: FrameworkEdgeKey
    frame_count: int
    probability: float

    def __post_init__(self) -> None:
        if not isinstance(self.edge_key, FrameworkEdgeKey):
            raise TopologyStatisticsConsistencyError("edge_key has the wrong type.")
        count = _nonnegative_int(self.frame_count, name="frame_count")
        probability = _finite_float(self.probability, name="probability")
        if probability < 0.0 or probability > 1.0:
            raise TopologyStatisticsConsistencyError(
                "Framework edge occupancy probability must lie in [0, 1]."
            )
        object.__setattr__(self, "frame_count", count)
        object.__setattr__(self, "probability", probability)

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_key": self.edge_key.to_dict(),
            "frame_count": self.frame_count,
            "probability": self.probability,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkEdgeOccupancy":
        return cls(
            edge_key=FrameworkEdgeKey.from_dict(
                _mapping(payload["edge_key"], name="edge_key")
            ),
            frame_count=int(payload["frame_count"]),
            probability=float(payload["probability"]),
        )


@dataclass(frozen=True, slots=True)
class FrameworkVertexDegreeStatistics:
    """Degree statistics for all framework vertices of one species."""

    atomic_number: int
    vertex_atom_indices: IntArray
    degree_distribution: DiscreteCountDistribution
    mean_degree_series: ScalarSeries
    per_vertex_mean_degree: FloatArray
    per_vertex_population_standard_deviation: FloatArray

    def __post_init__(self) -> None:
        number = _atomic_number(self.atomic_number)
        indices = _readonly_int_array(self.vertex_atom_indices, ndim=1)
        means = _readonly_float_array(self.per_vertex_mean_degree, ndim=1)
        deviations = _readonly_float_array(
            self.per_vertex_population_standard_deviation, ndim=1
        )
        if (
            indices.size == 0
            or means.shape != indices.shape
            or deviations.shape != indices.shape
        ):
            raise TopologyStatisticsConsistencyError(
                "Framework degree arrays must be aligned and nonempty."
            )
        if np.any(np.diff(indices) <= 0) or np.any(deviations < 0.0):
            raise TopologyStatisticsConsistencyError(
                "Framework vertex indices must increase and deviations be nonnegative."
            )
        if not isinstance(
            self.degree_distribution, DiscreteCountDistribution
        ) or not isinstance(self.mean_degree_series, ScalarSeries):
            raise TopologyStatisticsConsistencyError(
                "Framework degree statistics have invalid result objects."
            )
        object.__setattr__(self, "atomic_number", number)
        object.__setattr__(self, "vertex_atom_indices", indices)
        object.__setattr__(self, "per_vertex_mean_degree", means)
        object.__setattr__(self, "per_vertex_population_standard_deviation", deviations)

    @property
    def symbol(self) -> str:
        return chemical_symbols[self.atomic_number]

    def to_dict(self) -> dict[str, Any]:
        return {
            "atomic_number": self.atomic_number,
            "vertex_atom_indices": self.vertex_atom_indices.tolist(),
            "degree_distribution": self.degree_distribution.to_dict(),
            "mean_degree_series": self.mean_degree_series.to_dict(),
            "per_vertex_mean_degree": self.per_vertex_mean_degree.tolist(),
            "per_vertex_population_standard_deviation": self.per_vertex_population_standard_deviation.tolist(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkVertexDegreeStatistics":
        return cls(
            atomic_number=int(payload["atomic_number"]),
            vertex_atom_indices=np.asarray(
                payload["vertex_atom_indices"], dtype=np.int64
            ),
            degree_distribution=DiscreteCountDistribution.from_dict(
                _mapping(payload["degree_distribution"], name="degree_distribution")
            ),
            mean_degree_series=ScalarSeries.from_dict(
                _mapping(payload["mean_degree_series"], name="mean_degree_series")
            ),
            per_vertex_mean_degree=np.asarray(
                payload["per_vertex_mean_degree"], dtype=np.float64
            ),
            per_vertex_population_standard_deviation=np.asarray(
                payload["per_vertex_population_standard_deviation"], dtype=np.float64
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkEndpointPairTransitionCount:
    species_pair: FrameworkSpeciesPair
    additions: int
    removals: int

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "species_pair", _canonical_species_pair(self.species_pair)
        )
        object.__setattr__(
            self, "additions", _nonnegative_int(self.additions, name="additions")
        )
        object.__setattr__(
            self, "removals", _nonnegative_int(self.removals, name="removals")
        )

    @property
    def label(self) -> str:
        return "-".join(chemical_symbols[x] for x in self.species_pair)

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_pair": list(self.species_pair),
            "additions": self.additions,
            "removals": self.removals,
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "FrameworkEndpointPairTransitionCount":
        return cls(
            species_pair=tuple(int(x) for x in payload["species_pair"]),
            additions=int(payload["additions"]),
            removals=int(payload["removals"]),
        )


@dataclass(frozen=True, slots=True)
class FrameworkBridgeTransitionCount:
    signature: FrameworkBridgeSignature
    additions: int
    removals: int

    def __post_init__(self) -> None:
        if not isinstance(self.signature, FrameworkBridgeSignature):
            raise TopologyStatisticsConsistencyError("signature has the wrong type.")
        object.__setattr__(
            self, "additions", _nonnegative_int(self.additions, name="additions")
        )
        object.__setattr__(
            self, "removals", _nonnegative_int(self.removals, name="removals")
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "signature": self.signature.to_dict(),
            "additions": self.additions,
            "removals": self.removals,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkBridgeTransitionCount":
        return cls(
            signature=FrameworkBridgeSignature.from_dict(
                _mapping(payload["signature"], name="signature")
            ),
            additions=int(payload["additions"]),
            removals=int(payload["removals"]),
        )


@dataclass(frozen=True, slots=True)
class FrameworkTransitionAggregateStatistics:
    """Trajectory-wide aggregate effects of stored framework transitions."""

    n_frame_boundaries: int
    n_changed_boundaries: int
    total_added_edges: int
    total_removed_edges: int
    endpoint_pair_counts: tuple[FrameworkEndpointPairTransitionCount, ...]
    bridge_signature_counts: tuple[FrameworkBridgeTransitionCount, ...]
    affected_vertex_atom_indices: IntArray
    affected_vertex_event_counts: IntArray
    affected_linker_atom_indices: IntArray
    affected_linker_event_counts: IntArray

    def __post_init__(self) -> None:
        boundaries = _nonnegative_int(
            self.n_frame_boundaries, name="n_frame_boundaries"
        )
        changed = _nonnegative_int(
            self.n_changed_boundaries, name="n_changed_boundaries"
        )
        added = _nonnegative_int(self.total_added_edges, name="total_added_edges")
        removed = _nonnegative_int(self.total_removed_edges, name="total_removed_edges")
        if changed > boundaries:
            raise TopologyStatisticsConsistencyError(
                "Changed boundaries cannot exceed frame boundaries."
            )
        endpoint_counts = tuple(self.endpoint_pair_counts)
        if tuple(x.species_pair for x in endpoint_counts) != tuple(
            sorted(x.species_pair for x in endpoint_counts)
        ):
            raise TopologyStatisticsConsistencyError(
                "endpoint_pair_counts must be sorted."
            )
        bridge_counts = tuple(self.bridge_signature_counts)
        if tuple(x.signature for x in bridge_counts) != tuple(
            sorted(x.signature for x in bridge_counts)
        ):
            raise TopologyStatisticsConsistencyError(
                "bridge_signature_counts must be sorted."
            )
        if (
            sum(x.additions for x in endpoint_counts) != added
            or sum(x.removals for x in endpoint_counts) != removed
        ):
            raise TopologyStatisticsConsistencyError(
                "Endpoint-pair transition counts disagree with global totals."
            )
        if (
            sum(x.additions for x in bridge_counts) != added
            or sum(x.removals for x in bridge_counts) != removed
        ):
            raise TopologyStatisticsConsistencyError(
                "Bridge transition counts disagree with global totals."
            )
        vertex_indices, vertex_counts = _validated_index_counts(
            self.affected_vertex_atom_indices,
            self.affected_vertex_event_counts,
            label="vertex",
        )
        linker_indices, linker_counts = _validated_index_counts(
            self.affected_linker_atom_indices,
            self.affected_linker_event_counts,
            label="linker",
        )
        object.__setattr__(self, "n_frame_boundaries", boundaries)
        object.__setattr__(self, "n_changed_boundaries", changed)
        object.__setattr__(self, "total_added_edges", added)
        object.__setattr__(self, "total_removed_edges", removed)
        object.__setattr__(self, "endpoint_pair_counts", endpoint_counts)
        object.__setattr__(self, "bridge_signature_counts", bridge_counts)
        object.__setattr__(self, "affected_vertex_atom_indices", vertex_indices)
        object.__setattr__(self, "affected_vertex_event_counts", vertex_counts)
        object.__setattr__(self, "affected_linker_atom_indices", linker_indices)
        object.__setattr__(self, "affected_linker_event_counts", linker_counts)

    @property
    def total_edge_churn(self) -> int:
        return self.total_added_edges + self.total_removed_edges

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_frame_boundaries": self.n_frame_boundaries,
            "n_changed_boundaries": self.n_changed_boundaries,
            "total_added_edges": self.total_added_edges,
            "total_removed_edges": self.total_removed_edges,
            "endpoint_pair_counts": [x.to_dict() for x in self.endpoint_pair_counts],
            "bridge_signature_counts": [
                x.to_dict() for x in self.bridge_signature_counts
            ],
            "affected_vertex_atom_indices": self.affected_vertex_atom_indices.tolist(),
            "affected_vertex_event_counts": self.affected_vertex_event_counts.tolist(),
            "affected_linker_atom_indices": self.affected_linker_atom_indices.tolist(),
            "affected_linker_event_counts": self.affected_linker_event_counts.tolist(),
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "FrameworkTransitionAggregateStatistics":
        return cls(
            n_frame_boundaries=int(payload["n_frame_boundaries"]),
            n_changed_boundaries=int(payload["n_changed_boundaries"]),
            total_added_edges=int(payload["total_added_edges"]),
            total_removed_edges=int(payload["total_removed_edges"]),
            endpoint_pair_counts=tuple(
                FrameworkEndpointPairTransitionCount.from_dict(
                    _mapping(x, name="endpoint transition count")
                )
                for x in payload["endpoint_pair_counts"]
            ),
            bridge_signature_counts=tuple(
                FrameworkBridgeTransitionCount.from_dict(
                    _mapping(x, name="bridge transition count")
                )
                for x in payload["bridge_signature_counts"]
            ),
            affected_vertex_atom_indices=np.asarray(
                payload["affected_vertex_atom_indices"], dtype=np.int64
            ),
            affected_vertex_event_counts=np.asarray(
                payload["affected_vertex_event_counts"], dtype=np.int64
            ),
            affected_linker_atom_indices=np.asarray(
                payload["affected_linker_atom_indices"], dtype=np.int64
            ),
            affected_linker_event_counts=np.asarray(
                payload["affected_linker_event_counts"], dtype=np.int64
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkTemporalStatistics:
    """Exact TS3 trajectory organization for framework classes and edges."""

    state_statistics: StateTransitionStatistics
    edge_keys: tuple[FrameworkEdgeKey, ...]
    edge_episodes: EntityPresenceStatistics | None

    def __post_init__(self) -> None:
        if not isinstance(self.state_statistics, StateTransitionStatistics):
            raise TopologyStatisticsConsistencyError(
                "state_statistics has the wrong type."
            )
        keys = tuple(self.edge_keys)
        if keys != tuple(sorted(set(keys))):
            raise TopologyStatisticsConsistencyError(
                "edge_keys must be unique and sorted."
            )
        if self.edge_episodes is not None:
            if not isinstance(self.edge_episodes, EntityPresenceStatistics):
                raise TopologyStatisticsConsistencyError(
                    "edge_episodes has the wrong type."
                )
            if (
                self.edge_episodes.axis.to_dict()
                != self.state_statistics.axis.to_dict()
            ):
                raise TopologyStatisticsConsistencyError(
                    "Edge episodes and state statistics must use one axis."
                )
            if self.edge_episodes.n_entities != len(keys):
                raise TopologyStatisticsConsistencyError(
                    "Edge episode entity IDs must align with edge_keys."
                )
        object.__setattr__(self, "edge_keys", keys)

    def edge_episode_statistics(
        self, edge_key: FrameworkEdgeKey
    ) -> tuple[EntityPresenceEpisode, ...]:
        if self.edge_episodes is None:
            raise KeyError("Framework edge episodes were disabled.")
        try:
            entity_id = self.edge_keys.index(edge_key)
        except ValueError as exc:
            raise KeyError("Framework edge is not present.") from exc
        return self.edge_episodes.episodes_for(entity_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_statistics": self.state_statistics.to_dict(),
            "edge_keys": [key.to_dict() for key in self.edge_keys],
            "edge_episodes": None
            if self.edge_episodes is None
            else self.edge_episodes.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkTemporalStatistics":
        return cls(
            state_statistics=StateTransitionStatistics.from_dict(
                _mapping(payload["state_statistics"], name="state_statistics")
            ),
            edge_keys=tuple(
                FrameworkEdgeKey.from_dict(_mapping(item, name="framework edge key"))
                for item in payload["edge_keys"]
            ),
            edge_episodes=None
            if payload["edge_episodes"] is None
            else EntityPresenceStatistics.from_dict(
                _mapping(payload["edge_episodes"], name="edge_episodes")
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkTopologyStatistics:
    """Complete TS2 statistical summary of a framework topology catalog."""

    axis: FrameAxis
    catalog_occupancy: CatalogOccupancyStatistics
    vertex_atom_indices: IntArray
    vertex_atomic_numbers: IntArray
    graph_descriptors: tuple[FrameworkGraphDescriptorStatistics, ...]
    endpoint_pair_statistics: tuple[FrameworkEndpointPairStatistics, ...]
    bridge_signature_statistics: tuple[FrameworkBridgeSignatureStatistics, ...]
    degree_statistics: tuple[FrameworkVertexDegreeStatistics, ...] | None
    edge_occupancies: tuple[FrameworkEdgeOccupancy, ...] | None
    edge_occupancy_summary: ScalarSummary | None
    transition_statistics: FrameworkTransitionAggregateStatistics | None
    temporal_statistics: FrameworkTemporalStatistics | None
    options: FrameworkStatisticsOptions
    source_catalog_schema: str
    source_framework_schema: str
    source_catalog_digest: str
    source_mapping_digest: str
    source_topology_digests: tuple[str, ...]
    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_FRAMEWORK_TOPOLOGY_STATISTICS_SCHEMA
    digest_algorithm: str = TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.axis, FrameAxis) or not isinstance(
            self.catalog_occupancy, CatalogOccupancyStatistics
        ):
            raise TopologyStatisticsConsistencyError(
                "axis and catalog_occupancy have the wrong type."
            )
        if (
            self.axis.n_frames != self.catalog_occupancy.n_frames
            or self.axis.frame_semantics is not self.catalog_occupancy.frame_semantics
        ):
            raise TopologyStatisticsConsistencyError(
                "Frame axis and catalog occupancy must align."
            )
        indices = _readonly_int_array(self.vertex_atom_indices, ndim=1)
        numbers = _readonly_int_array(self.vertex_atomic_numbers, ndim=1)
        if (
            indices.size == 0
            or numbers.shape != indices.shape
            or np.any(np.diff(indices) <= 0)
        ):
            raise TopologyStatisticsConsistencyError(
                "Framework vertex arrays must be aligned, nonempty, and sorted."
            )
        descriptors = tuple(self.graph_descriptors)
        if tuple(x.descriptor for x in descriptors) != tuple(_DESCRIPTOR_LABELS):
            raise TopologyStatisticsConsistencyError(
                "graph_descriptors must contain the complete canonical descriptor order."
            )
        for item in descriptors:
            if (
                item.topology_values.size != self.catalog_occupancy.n_states
                or item.series.axis.to_dict() != self.axis.to_dict()
            ):
                raise TopologyStatisticsConsistencyError(
                    "Graph descriptors must align with topology classes and frames."
                )
            expected = expand_state_values_to_frames(
                item.topology_values, self.catalog_occupancy.frame_to_state_id
            )
            if not np.array_equal(expected, item.series.values):
                raise TopologyStatisticsConsistencyError(
                    "A graph descriptor series disagrees with topology assignments."
                )
        endpoint_stats = tuple(self.endpoint_pair_statistics)
        if tuple(x.species_pair for x in endpoint_stats) != tuple(
            sorted(x.species_pair for x in endpoint_stats)
        ):
            raise TopologyStatisticsConsistencyError(
                "endpoint_pair_statistics must be sorted."
            )
        bridge_stats = tuple(self.bridge_signature_statistics)
        if tuple(x.signature for x in bridge_stats) != tuple(
            sorted(x.signature for x in bridge_stats)
        ):
            raise TopologyStatisticsConsistencyError(
                "bridge_signature_statistics must be sorted."
            )
        for item in (*endpoint_stats, *bridge_stats):
            if (
                item.topology_edge_counts.size != self.catalog_occupancy.n_states
                or item.edge_count_series.axis.to_dict() != self.axis.to_dict()
            ):
                raise TopologyStatisticsConsistencyError(
                    "Edge-category statistics must align with topology classes and frames."
                )
        degrees = (
            None if self.degree_statistics is None else tuple(self.degree_statistics)
        )
        if degrees is not None:
            if tuple(x.atomic_number for x in degrees) != tuple(
                sorted(x.atomic_number for x in degrees)
            ):
                raise TopologyStatisticsConsistencyError(
                    "degree_statistics must be sorted by species."
                )
        occupancies = (
            None if self.edge_occupancies is None else tuple(self.edge_occupancies)
        )
        if occupancies is None:
            if self.edge_occupancy_summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "edge_occupancy_summary requires edge_occupancies."
                )
        else:
            if tuple(x.edge_key for x in occupancies) != tuple(
                sorted(x.edge_key for x in occupancies)
            ):
                raise TopologyStatisticsConsistencyError(
                    "edge_occupancies must be sorted by FrameworkEdgeKey."
                )
            for item in occupancies:
                if item.frame_count > self.axis.n_frames or not np.isclose(
                    item.probability,
                    item.frame_count / self.axis.n_frames,
                    rtol=0.0,
                    atol=1e-15,
                ):
                    raise TopologyStatisticsConsistencyError(
                        "A framework edge occupancy disagrees with the frame count."
                    )
            if occupancies:
                if self.edge_occupancy_summary is None:
                    raise TopologyStatisticsConsistencyError(
                        "Nonempty edge occupancies require a summary."
                    )
            elif self.edge_occupancy_summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "An empty edge occupancy collection has no summary."
                )
        if (
            self.transition_statistics is not None
            and self.axis.frame_semantics is not FrameSemantics.TRAJECTORY
        ):
            raise TopologyStatisticsConsistencyError(
                "Framework transition aggregates are trajectory-only."
            )
        if self.temporal_statistics is not None:
            if self.axis.frame_semantics is not FrameSemantics.TRAJECTORY:
                raise TopologyStatisticsConsistencyError(
                    "Detailed framework temporal statistics are trajectory-only."
                )
            if not isinstance(self.temporal_statistics, FrameworkTemporalStatistics):
                raise TopologyStatisticsConsistencyError(
                    "temporal_statistics has the wrong type."
                )
            if (
                self.temporal_statistics.state_statistics.axis.to_dict()
                != self.axis.to_dict()
            ):
                raise TopologyStatisticsConsistencyError(
                    "Detailed temporal statistics do not use the result axis."
                )
            if (
                self.temporal_statistics.state_statistics.n_states
                != self.catalog_occupancy.n_states
            ):
                raise TopologyStatisticsConsistencyError(
                    "Detailed temporal topology count disagrees with catalog occupancy."
                )
        if not isinstance(self.options, FrameworkStatisticsOptions):
            raise TopologyStatisticsConsistencyError("options has the wrong type.")
        if (
            self.source_catalog_schema != CANONICAL_TOPOLOGY_CATALOG_SCHEMA
            or self.source_framework_schema != CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA
        ):
            raise TopologyStatisticsConsistencyError(
                "Unsupported source catalog or framework schema."
            )
        for name, value in (
            ("source_catalog_digest", self.source_catalog_digest),
            ("source_mapping_digest", self.source_mapping_digest),
        ):
            if not isinstance(value, str) or len(value) != 64:
                raise TopologyStatisticsConsistencyError(
                    f"{name} must be a SHA-256 digest."
                )
        topology_digests = tuple(str(x) for x in self.source_topology_digests)
        if len(topology_digests) != self.catalog_occupancy.n_states or any(
            len(x) != 64 for x in topology_digests
        ):
            raise TopologyStatisticsConsistencyError(
                "source_topology_digests must contain one digest per topology class."
            )
        if (
            self.canonical_schema_version
            != CANONICAL_FRAMEWORK_TOPOLOGY_STATISTICS_SCHEMA
            or self.digest_algorithm != TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
        ):
            raise TopologyStatisticsConsistencyError(
                "Unsupported framework statistics schema or digest algorithm."
            )
        metadata = MappingProxyType(_deep_copy_mapping(self.metadata))
        object.__setattr__(self, "vertex_atom_indices", indices)
        object.__setattr__(self, "vertex_atomic_numbers", numbers)
        object.__setattr__(self, "graph_descriptors", descriptors)
        object.__setattr__(self, "endpoint_pair_statistics", endpoint_stats)
        object.__setattr__(self, "bridge_signature_statistics", bridge_stats)
        object.__setattr__(self, "degree_statistics", degrees)
        object.__setattr__(self, "edge_occupancies", occupancies)
        object.__setattr__(self, "source_topology_digests", topology_digests)
        object.__setattr__(self, "metadata", metadata)
        expected_digest = _framework_statistics_digest(self)
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise TopologyStatisticsConsistencyError(
                "Stored framework-statistics digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    @property
    def n_frames(self) -> int:
        return self.axis.n_frames

    @property
    def n_topologies(self) -> int:
        return self.catalog_occupancy.n_states

    def descriptor(self, name: str) -> FrameworkGraphDescriptorStatistics:
        target = str(name).strip()
        for item in self.graph_descriptors:
            if item.descriptor == target:
                return item
        raise KeyError(f"Unknown framework graph descriptor: {target!r}.")

    def endpoint_pair(
        self, left: int | str, right: int | str
    ) -> FrameworkEndpointPairStatistics:
        target = _canonical_species_pair((_atomic_number(left), _atomic_number(right)))
        for item in self.endpoint_pair_statistics:
            if item.species_pair == target:
                return item
        raise KeyError(f"Framework endpoint pair {target} is not present.")

    def bridge_signature(
        self, signature: FrameworkBridgeSignature
    ) -> FrameworkBridgeSignatureStatistics:
        for item in self.bridge_signature_statistics:
            if item.signature == signature:
                return item
        raise KeyError("Framework bridge signature is not present.")

    def species_degree(self, species: int | str) -> FrameworkVertexDegreeStatistics:
        if self.degree_statistics is None:
            raise KeyError("Degree statistics were disabled.")
        target = _atomic_number(species)
        for item in self.degree_statistics:
            if item.atomic_number == target:
                return item
        raise KeyError(f"Framework vertex species {target} is not present.")

    def to_dict(self) -> dict[str, Any]:
        return _framework_statistics_payload(self, include_digest=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkTopologyStatistics":
        if (
            payload.get("schema_version")
            != CANONICAL_FRAMEWORK_TOPOLOGY_STATISTICS_SCHEMA
        ):
            raise TopologyStatisticsSerializationError(
                "Unsupported framework topology-statistics schema version."
            )
        if payload.get("object_type") != "FrameworkTopologyStatistics":
            raise TopologyStatisticsSerializationError(
                "Payload is not a FrameworkTopologyStatistics object."
            )
        try:
            raw_occupancies = payload["edge_occupancies"]
            raw_summary = payload["edge_occupancy_summary"]
            return cls(
                axis=FrameAxis.from_dict(_mapping(payload["axis"], name="axis")),
                catalog_occupancy=CatalogOccupancyStatistics.from_dict(
                    _mapping(payload["catalog_occupancy"], name="catalog_occupancy")
                ),
                vertex_atom_indices=np.asarray(
                    payload["vertex_atom_indices"], dtype=np.int64
                ),
                vertex_atomic_numbers=np.asarray(
                    payload["vertex_atomic_numbers"], dtype=np.int64
                ),
                graph_descriptors=tuple(
                    FrameworkGraphDescriptorStatistics.from_dict(
                        _mapping(x, name="graph descriptor")
                    )
                    for x in payload["graph_descriptors"]
                ),
                endpoint_pair_statistics=tuple(
                    FrameworkEndpointPairStatistics.from_dict(
                        _mapping(x, name="endpoint pair statistics")
                    )
                    for x in payload["endpoint_pair_statistics"]
                ),
                bridge_signature_statistics=tuple(
                    FrameworkBridgeSignatureStatistics.from_dict(
                        _mapping(x, name="bridge signature statistics")
                    )
                    for x in payload["bridge_signature_statistics"]
                ),
                degree_statistics=None
                if payload["degree_statistics"] is None
                else tuple(
                    FrameworkVertexDegreeStatistics.from_dict(
                        _mapping(x, name="degree statistics")
                    )
                    for x in payload["degree_statistics"]
                ),
                edge_occupancies=None
                if raw_occupancies is None
                else tuple(
                    FrameworkEdgeOccupancy.from_dict(_mapping(x, name="edge occupancy"))
                    for x in raw_occupancies
                ),
                edge_occupancy_summary=None
                if raw_summary is None
                else ScalarSummary.from_dict(
                    _mapping(raw_summary, name="edge_occupancy_summary")
                ),
                transition_statistics=None
                if payload["transition_statistics"] is None
                else FrameworkTransitionAggregateStatistics.from_dict(
                    _mapping(
                        payload["transition_statistics"], name="transition_statistics"
                    )
                ),
                temporal_statistics=None
                if payload["temporal_statistics"] is None
                else FrameworkTemporalStatistics.from_dict(
                    _mapping(payload["temporal_statistics"], name="temporal_statistics")
                ),
                options=FrameworkStatisticsOptions.from_dict(
                    _mapping(payload["options"], name="options")
                ),
                source_catalog_schema=str(payload["source_catalog_schema"]),
                source_framework_schema=str(payload["source_framework_schema"]),
                source_catalog_digest=str(payload["source_catalog_digest"]),
                source_mapping_digest=str(payload["source_mapping_digest"]),
                source_topology_digests=tuple(
                    str(x) for x in payload["source_topology_digests"]
                ),
                metadata=_mapping(payload.get("metadata", {}), name="metadata"),
                canonical_schema_version=str(payload["schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, TopologyStatisticsConsistencyError):
                raise
            raise TopologyStatisticsSerializationError(
                "Malformed FrameworkTopologyStatistics payload."
            ) from exc


def compute_framework_topology_statistics(
    catalog: TopologyCatalog,
    *,
    steps: ArrayLike | None = None,
    times: ArrayLike | None = None,
    time_unit: str | None = None,
    options: FrameworkStatisticsOptions | None = None,
) -> FrameworkTopologyStatistics:
    """Compute TS2 statistics from one completed framework topology catalog."""

    if not isinstance(catalog, TopologyCatalog):
        raise TypeError("catalog must be a TopologyCatalog.")
    effective = FrameworkStatisticsOptions() if options is None else options
    if not isinstance(effective, FrameworkStatisticsOptions):
        raise TypeError("options must be a FrameworkStatisticsOptions instance.")

    semantics = catalog.frame_semantics
    axis = build_frame_axis(
        catalog.n_frames,
        frame_semantics=semantics,
        collection_frame_indices=catalog.frame_indices,
        frame_ids=catalog.frame_ids,
        steps=steps,
        times=times,
        time_unit=time_unit,
    )
    occupancy = compute_catalog_occupancy_statistics(
        catalog.frame_topology_ids,
        frame_semantics=semantics,
        n_states=catalog.n_topologies,
    )
    vertex_indices, vertex_numbers = _validate_topology_alignment(catalog)

    graph_descriptors = tuple(
        _compute_graph_descriptor(name, catalog, axis, effective.quantiles)
        for name in _DESCRIPTOR_LABELS
    )

    endpoint_pairs = tuple(sorted(_observed_endpoint_pairs(catalog.topologies)))
    endpoint_stats = tuple(
        _compute_endpoint_pair_statistics(pair, catalog, axis, effective.quantiles)
        for pair in endpoint_pairs
    )

    signatures = tuple(sorted(_observed_bridge_signatures(catalog.topologies)))
    bridge_stats = tuple(
        _compute_bridge_signature_statistics(
            signature, catalog, axis, effective.quantiles
        )
        for signature in signatures
    )

    degree_statistics = (
        _compute_degree_statistics(
            catalog,
            axis,
            occupancy.state_frame_counts,
            vertex_indices,
            vertex_numbers,
            effective.quantiles,
        )
        if effective.include_degree_statistics
        else None
    )

    edge_occupancies = None
    edge_occupancy_summary = None
    if effective.include_edge_occupancies:
        edge_occupancies = _compute_edge_occupancies(
            catalog, occupancy.state_frame_counts
        )
        if edge_occupancies:
            edge_occupancy_summary = compute_scalar_summary(
                [x.probability for x in edge_occupancies],
                quantiles=effective.quantiles,
            )

    transition_statistics = None
    if (
        effective.include_transition_statistics
        and semantics is FrameSemantics.TRAJECTORY
        and catalog.transitions
    ):
        transition_statistics = _compute_transition_aggregates(catalog)

    temporal_statistics = None
    if effective.include_temporal_statistics and semantics is FrameSemantics.TRAJECTORY:
        state_statistics = compute_state_transition_statistics(
            catalog.frame_topology_ids,
            axis,
            n_states=catalog.n_topologies,
            options=effective.temporal_options,
            metadata={"source": "TopologyCatalog"},
        )
        edge_keys: tuple[FrameworkEdgeKey, ...] = ()
        edge_episodes = None
        if effective.include_edge_episodes:
            edge_keys = tuple(
                sorted(
                    {
                        key
                        for topology in catalog.topologies
                        for key in topology.edge_keys
                    }
                )
            )
            edge_id = {key: index for index, key in enumerate(edge_keys)}
            state_edge_ids = tuple(
                tuple(sorted(edge_id[key] for key in topology.edge_keys))
                for topology in catalog.topologies
            )
            edge_episodes = compute_entity_presence_statistics(
                state_edge_ids,
                catalog.frame_topology_ids,
                axis,
                n_entities=len(edge_keys),
                options=effective.temporal_options,
                metadata={"entity_kind": "canonical_framework_edge"},
            )
        temporal_statistics = FrameworkTemporalStatistics(
            state_statistics=state_statistics,
            edge_keys=edge_keys,
            edge_episodes=edge_episodes,
        )

    metadata = {
        "module": "topology_statistics.framework",
        "stage": "TS2",
        "frame_semantics": semantics.value,
        "catalog_consistency": catalog.consistency.value,
        "n_framework_vertices": int(vertex_indices.size),
        "descriptive_only": True,
        "cycle_rank_warning": (
            "cycle_rank is E - V + C and is not a primitive-ring count"
        ),
        "whole_path_orientation_aware": True,
        "catalog_metadata": _json_safe(dict(catalog.metadata)),
    }
    return FrameworkTopologyStatistics(
        axis=axis,
        catalog_occupancy=occupancy,
        vertex_atom_indices=vertex_indices,
        vertex_atomic_numbers=vertex_numbers,
        graph_descriptors=graph_descriptors,
        endpoint_pair_statistics=endpoint_stats,
        bridge_signature_statistics=bridge_stats,
        degree_statistics=degree_statistics,
        edge_occupancies=edge_occupancies,
        edge_occupancy_summary=edge_occupancy_summary,
        transition_statistics=transition_statistics,
        temporal_statistics=temporal_statistics,
        options=effective,
        source_catalog_schema=CANONICAL_TOPOLOGY_CATALOG_SCHEMA,
        source_framework_schema=CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA,
        source_catalog_digest=catalog.digest,
        source_mapping_digest=catalog.mapping.digest,
        source_topology_digests=tuple(x.digest for x in catalog.topologies),
        metadata=metadata,
    )


def _validate_topology_alignment(catalog: TopologyCatalog) -> tuple[IntArray, IntArray]:
    first = catalog.topologies[0]
    indices = np.asarray(first.vertex_atom_indices, dtype=np.int64)
    numbers = np.asarray(first.vertex_atomic_numbers, dtype=np.int64)
    for topology in catalog.topologies:
        if topology.canonical_schema_version != CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA:
            raise TopologyStatisticsInputError(
                "A topology uses an unsupported framework schema."
            )
        if not np.array_equal(
            topology.vertex_atom_indices, indices
        ) or not np.array_equal(topology.vertex_atomic_numbers, numbers):
            raise TopologyStatisticsInputError(
                "All topology classes must share aligned framework vertex identities."
            )
    indices = np.array(indices, copy=True)
    numbers = np.array(numbers, copy=True)
    indices.setflags(write=False)
    numbers.setflags(write=False)
    return indices, numbers


def _topology_descriptor(topology: FrameworkTopology, name: str) -> int:
    if name == "vertex_count":
        return topology.n_vertices
    if name == "edge_count":
        return topology.n_edges
    if name == "component_count":
        return topology.n_components
    if name == "isolated_vertex_count":
        return int(np.count_nonzero(topology.degree == 0))
    if name == "self_image_edge_count":
        return sum(edge.key.vertex_i == edge.key.vertex_j for edge in topology.edges)
    endpoint_counts = Counter(
        (edge.key.vertex_i, edge.key.vertex_j) for edge in topology.edges
    )
    if name == "parallel_endpoint_pair_count":
        return sum(count > 1 for count in endpoint_counts.values())
    if name == "parallel_edge_excess_count":
        return sum(max(0, count - 1) for count in endpoint_counts.values())
    if name == "cycle_rank":
        value = topology.n_edges - topology.n_vertices + topology.n_components
        if value < 0:  # pragma: no cover - graph invariant
            raise TopologyStatisticsConsistencyError(
                "Graph cycle rank cannot be negative."
            )
        return value
    raise KeyError(name)


def _compute_graph_descriptor(
    name: str,
    catalog: TopologyCatalog,
    axis: FrameAxis,
    quantiles: tuple[float, ...],
) -> FrameworkGraphDescriptorStatistics:
    topology_values = np.asarray(
        [_topology_descriptor(topology, name) for topology in catalog.topologies],
        dtype=np.int64,
    )
    frame_values = expand_state_values_to_frames(
        topology_values, catalog.frame_topology_ids
    )
    label, unit = _DESCRIPTOR_LABELS[name]
    return FrameworkGraphDescriptorStatistics(
        descriptor=name,
        topology_values=topology_values,
        series=build_scalar_series(
            label, frame_values, axis, unit=unit, quantiles=quantiles
        ),
        distribution=compute_discrete_count_distribution(
            frame_values, quantiles=quantiles
        ),
    )


def _vertex_number_map(topology: FrameworkTopology) -> dict[int, int]:
    return {
        int(index): int(number)
        for index, number in zip(
            topology.vertex_atom_indices,
            topology.vertex_atomic_numbers,
            strict=True,
        )
    }


def _edge_endpoint_pair(
    edge: FrameworkEdgeKey, number_by_vertex: Mapping[int, int]
) -> FrameworkSpeciesPair:
    return _canonical_species_pair(
        (number_by_vertex[edge.vertex_i], number_by_vertex[edge.vertex_j])
    )


def _edge_bridge_signature(
    edge: FrameworkEdgePath,
    number_by_vertex: Mapping[int, int],
) -> FrameworkBridgeSignature:
    path_numbers = (
        number_by_vertex[edge.key.vertex_i],
        *edge.internal_linker_atomic_numbers,
        number_by_vertex[edge.key.vertex_j],
    )
    return FrameworkBridgeSignature(
        path_atomic_numbers=path_numbers,
        rule_id=edge.key.rule_id,
        edge_kind=edge.edge_kind,
    )


def _observed_endpoint_pairs(
    topologies: Sequence[FrameworkTopology],
) -> set[FrameworkSpeciesPair]:
    result: set[FrameworkSpeciesPair] = set()
    for topology in topologies:
        numbers = _vertex_number_map(topology)
        result.update(_edge_endpoint_pair(edge.key, numbers) for edge in topology.edges)
    return result


def _observed_bridge_signatures(
    topologies: Sequence[FrameworkTopology],
) -> set[FrameworkBridgeSignature]:
    result: set[FrameworkBridgeSignature] = set()
    for topology in topologies:
        numbers = _vertex_number_map(topology)
        result.update(_edge_bridge_signature(edge, numbers) for edge in topology.edges)
    return result


def _compute_endpoint_pair_statistics(
    pair: FrameworkSpeciesPair,
    catalog: TopologyCatalog,
    axis: FrameAxis,
    quantiles: tuple[float, ...],
) -> FrameworkEndpointPairStatistics:
    topology_counts = []
    for topology in catalog.topologies:
        numbers = _vertex_number_map(topology)
        topology_counts.append(
            sum(
                _edge_endpoint_pair(edge.key, numbers) == pair
                for edge in topology.edges
            )
        )
    values = np.asarray(topology_counts, dtype=np.int64)
    frame_values = expand_state_values_to_frames(values, catalog.frame_topology_ids)
    label = "-".join(chemical_symbols[x] for x in pair)
    return FrameworkEndpointPairStatistics(
        species_pair=pair,
        topology_edge_counts=values,
        edge_count_series=build_scalar_series(
            f"{label} projected edges",
            frame_values,
            axis,
            unit="edges",
            quantiles=quantiles,
        ),
        edge_count_distribution=compute_discrete_count_distribution(
            frame_values, quantiles=quantiles
        ),
    )


def _compute_bridge_signature_statistics(
    signature: FrameworkBridgeSignature,
    catalog: TopologyCatalog,
    axis: FrameAxis,
    quantiles: tuple[float, ...],
) -> FrameworkBridgeSignatureStatistics:
    topology_counts = []
    for topology in catalog.topologies:
        numbers = _vertex_number_map(topology)
        topology_counts.append(
            sum(
                _edge_bridge_signature(edge, numbers) == signature
                for edge in topology.edges
            )
        )
    values = np.asarray(topology_counts, dtype=np.int64)
    frame_values = expand_state_values_to_frames(values, catalog.frame_topology_ids)
    return FrameworkBridgeSignatureStatistics(
        signature=signature,
        topology_edge_counts=values,
        edge_count_series=build_scalar_series(
            f"{signature.label} bridges",
            frame_values,
            axis,
            unit="edges",
            quantiles=quantiles,
        ),
        edge_count_distribution=compute_discrete_count_distribution(
            frame_values, quantiles=quantiles
        ),
    )


def _compute_degree_statistics(
    catalog: TopologyCatalog,
    axis: FrameAxis,
    topology_frame_counts: IntArray,
    vertex_indices: IntArray,
    vertex_numbers: IntArray,
    quantiles: tuple[float, ...],
) -> tuple[FrameworkVertexDegreeStatistics, ...]:
    result = []
    topology_degrees = np.stack(
        [np.asarray(topology.degree, dtype=np.int64) for topology in catalog.topologies]
    )
    for number in sorted(set(int(x) for x in vertex_numbers)):
        mask = vertex_numbers == number
        atom_indices = vertex_indices[mask]
        state_values = topology_degrees[:, mask]
        support_frequency: Counter[int] = Counter()
        for topology_id, frame_count in enumerate(topology_frame_counts):
            for degree in state_values[topology_id]:
                support_frequency[int(degree)] += int(frame_count)
        expanded = np.repeat(
            np.asarray(sorted(support_frequency), dtype=np.int64),
            np.asarray(
                [support_frequency[x] for x in sorted(support_frequency)],
                dtype=np.int64,
            ),
        )
        distribution = compute_discrete_count_distribution(
            expanded, quantiles=quantiles
        )
        state_mean = np.mean(state_values, axis=1)
        frame_mean = expand_state_values_to_frames(
            state_mean, catalog.frame_topology_ids
        )
        mean_series = build_scalar_series(
            f"Mean {chemical_symbols[number]} framework degree",
            frame_mean,
            axis,
            unit="degree",
            quantiles=quantiles,
        )
        frame_degree_matrix = topology_degrees[catalog.frame_topology_ids][:, mask]
        result.append(
            FrameworkVertexDegreeStatistics(
                atomic_number=number,
                vertex_atom_indices=atom_indices,
                degree_distribution=distribution,
                mean_degree_series=mean_series,
                per_vertex_mean_degree=np.mean(frame_degree_matrix, axis=0),
                per_vertex_population_standard_deviation=np.std(
                    frame_degree_matrix, axis=0, ddof=0
                ),
            )
        )
    return tuple(result)


def _compute_edge_occupancies(
    catalog: TopologyCatalog, topology_frame_counts: IntArray
) -> tuple[FrameworkEdgeOccupancy, ...]:
    counts: Counter[FrameworkEdgeKey] = Counter()
    for topology_id, topology in enumerate(catalog.topologies):
        frame_count = int(topology_frame_counts[topology_id])
        for key in topology.edge_keys:
            counts[key] += frame_count
    return tuple(
        FrameworkEdgeOccupancy(
            edge_key=key,
            frame_count=counts[key],
            probability=counts[key] / catalog.n_frames,
        )
        for key in sorted(counts)
    )


def _edge_path_by_key(
    topology: FrameworkTopology,
) -> dict[FrameworkEdgeKey, FrameworkEdgePath]:
    return {edge.key: edge for edge in topology.edges}


def _compute_transition_aggregates(
    catalog: TopologyCatalog,
) -> FrameworkTransitionAggregateStatistics:
    endpoint_additions: Counter[FrameworkSpeciesPair] = Counter()
    endpoint_removals: Counter[FrameworkSpeciesPair] = Counter()
    signature_additions: Counter[FrameworkBridgeSignature] = Counter()
    signature_removals: Counter[FrameworkBridgeSignature] = Counter()
    vertex_events: Counter[int] = Counter()
    linker_events: Counter[int] = Counter()
    total_added = 0
    total_removed = 0

    for transition in catalog.transitions:
        source = catalog.topologies[transition.source_topology_id]
        target = catalog.topologies[transition.target_topology_id]
        source_numbers = _vertex_number_map(source)
        target_numbers = _vertex_number_map(target)
        source_paths = _edge_path_by_key(source)
        target_paths = _edge_path_by_key(target)
        for key in transition.added_framework_edges:
            path = target_paths[key]
            endpoint_additions[_edge_endpoint_pair(key, target_numbers)] += 1
            signature_additions[_edge_bridge_signature(path, target_numbers)] += 1
            total_added += 1
        for key in transition.removed_framework_edges:
            path = source_paths[key]
            endpoint_removals[_edge_endpoint_pair(key, source_numbers)] += 1
            signature_removals[_edge_bridge_signature(path, source_numbers)] += 1
            total_removed += 1
        vertex_events.update(transition.affected_vertex_atom_indices)
        linker_events.update(transition.affected_linker_atom_indices)

    endpoint_pairs = sorted(set(endpoint_additions) | set(endpoint_removals))
    signatures = sorted(set(signature_additions) | set(signature_removals))
    vertex_indices = np.asarray(sorted(vertex_events), dtype=np.int64)
    linker_indices = np.asarray(sorted(linker_events), dtype=np.int64)
    return FrameworkTransitionAggregateStatistics(
        n_frame_boundaries=max(0, catalog.n_frames - 1),
        n_changed_boundaries=len(catalog.transitions),
        total_added_edges=total_added,
        total_removed_edges=total_removed,
        endpoint_pair_counts=tuple(
            FrameworkEndpointPairTransitionCount(
                species_pair=pair,
                additions=endpoint_additions[pair],
                removals=endpoint_removals[pair],
            )
            for pair in endpoint_pairs
        ),
        bridge_signature_counts=tuple(
            FrameworkBridgeTransitionCount(
                signature=signature,
                additions=signature_additions[signature],
                removals=signature_removals[signature],
            )
            for signature in signatures
        ),
        affected_vertex_atom_indices=vertex_indices,
        affected_vertex_event_counts=np.asarray(
            [vertex_events[int(x)] for x in vertex_indices], dtype=np.int64
        ),
        affected_linker_atom_indices=linker_indices,
        affected_linker_event_counts=np.asarray(
            [linker_events[int(x)] for x in linker_indices], dtype=np.int64
        ),
    )


def _framework_statistics_payload(
    result: FrameworkTopologyStatistics, *, include_digest: bool
) -> dict[str, Any]:
    payload = {
        "schema_version": result.canonical_schema_version,
        "object_type": "FrameworkTopologyStatistics",
        "digest_algorithm": result.digest_algorithm,
        "axis": result.axis.to_dict(),
        "catalog_occupancy": result.catalog_occupancy.to_dict(),
        "vertex_atom_indices": result.vertex_atom_indices.tolist(),
        "vertex_atomic_numbers": result.vertex_atomic_numbers.tolist(),
        "graph_descriptors": [x.to_dict() for x in result.graph_descriptors],
        "endpoint_pair_statistics": [
            x.to_dict() for x in result.endpoint_pair_statistics
        ],
        "bridge_signature_statistics": [
            x.to_dict() for x in result.bridge_signature_statistics
        ],
        "degree_statistics": None
        if result.degree_statistics is None
        else [x.to_dict() for x in result.degree_statistics],
        "edge_occupancies": None
        if result.edge_occupancies is None
        else [x.to_dict() for x in result.edge_occupancies],
        "edge_occupancy_summary": None
        if result.edge_occupancy_summary is None
        else result.edge_occupancy_summary.to_dict(),
        "transition_statistics": None
        if result.transition_statistics is None
        else result.transition_statistics.to_dict(),
        "temporal_statistics": None
        if result.temporal_statistics is None
        else result.temporal_statistics.to_dict(),
        "options": result.options.to_dict(),
        "source_catalog_schema": result.source_catalog_schema,
        "source_framework_schema": result.source_framework_schema,
        "source_catalog_digest": result.source_catalog_digest,
        "source_mapping_digest": result.source_mapping_digest,
        "source_topology_digests": list(result.source_topology_digests),
        "metadata": _json_safe(dict(result.metadata)),
    }
    if include_digest:
        payload["digest"] = result.digest
    return payload


def _framework_statistics_digest(result: FrameworkTopologyStatistics) -> str:
    encoded = canonical_statistics_json(
        _framework_statistics_payload(result, include_digest=False)
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_species_pair(pair: Sequence[int]) -> FrameworkSpeciesPair:
    if len(pair) != 2:
        raise TopologyStatisticsInputError("A species pair must contain two entries.")
    left = _atomic_number(pair[0])
    right = _atomic_number(pair[1])
    return (left, right) if left <= right else (right, left)


def _atomic_number(value: int | str) -> int:
    if isinstance(value, str):
        symbol = value.strip()
        if symbol not in atomic_numbers:
            raise TopologyStatisticsInputError(f"Unknown chemical symbol: {value!r}.")
        return int(atomic_numbers[symbol])
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TopologyStatisticsInputError(
            "Atomic number must be an integer or symbol."
        )
    number = int(value)
    if number <= 0 or number >= len(chemical_symbols):
        raise TopologyStatisticsInputError(f"Unknown atomic number: {number}.")
    return number


def _validated_quantiles(values: Sequence[float]) -> tuple[float, ...]:
    quantiles = tuple(float(value) for value in values)
    if (
        len(quantiles) < 2
        or quantiles[0] != 0.0
        or quantiles[-1] != 1.0
        or any(not np.isfinite(value) for value in quantiles)
        or any(left >= right for left, right in zip(quantiles, quantiles[1:]))
    ):
        raise TopologyStatisticsInputError(
            "quantiles must be finite, strictly increasing, and span 0 to 1."
        )
    return quantiles


def _validated_index_counts(
    indices: ArrayLike, counts: ArrayLike, *, label: str
) -> tuple[IntArray, IntArray]:
    index_array = _readonly_int_array(indices, ndim=1)
    count_array = _readonly_int_array(counts, ndim=1)
    if index_array.shape != count_array.shape:
        raise TopologyStatisticsConsistencyError(
            f"Affected {label} indices and event counts must align."
        )
    if index_array.size and (
        np.any(np.diff(index_array) <= 0) or np.any(count_array <= 0)
    ):
        raise TopologyStatisticsConsistencyError(
            f"Affected {label} indices must increase and counts be positive."
        )
    return index_array, count_array


def _readonly_int_array(values: ArrayLike, *, ndim: int) -> IntArray:
    array = np.asarray(values)
    if array.ndim != ndim or not np.issubdtype(array.dtype, np.integer):
        raise TopologyStatisticsConsistencyError(f"Expected a {ndim}-D integer array.")
    result = np.array(array, dtype=np.int64, copy=True)
    result.setflags(write=False)
    return result


def _readonly_float_array(values: ArrayLike, *, ndim: int) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise TopologyStatisticsConsistencyError(
            f"Expected a finite {ndim}-D floating array."
        )
    result = np.array(array, copy=True)
    result.setflags(write=False)
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TopologyStatisticsConsistencyError(f"{name} must be an integer.")
    result = int(value)
    if result < 0:
        raise TopologyStatisticsConsistencyError(f"{name} cannot be negative.")
    return result


def _finite_float(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsConsistencyError(f"{name} must be numeric.") from exc
    if not np.isfinite(result):
        raise TopologyStatisticsConsistencyError(f"{name} must be finite.")
    return result


def _mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TopologyStatisticsSerializationError(f"{name} must be a mapping.")
    return value


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _deep_copy_value(item) for key, item in value.items()}


def _deep_copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(_deep_copy_mapping(value))
    if isinstance(value, tuple):
        return tuple(_deep_copy_value(x) for x in value)
    if isinstance(value, list):
        return tuple(_deep_copy_value(x) for x in value)
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(x) for x in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value
