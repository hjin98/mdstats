"""Atomic-connectivity statistics derived from completed graph catalogs.

This module is the TS1 layer of the topology-statistics architecture.  It
summarizes :class:`~mdstats.analysis.atomic_connectivity.AtomicConnectivityResult`
objects without rebuilding neighbors, changing connectivity definitions, or
assigning temporal meaning to unordered ensembles.

The implementation evaluates graph descriptors once per unique connectivity
state and expands only compact scalar arrays through the frame-to-state map.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, TypeAlias

import numpy as np
from ase.data import atomic_numbers, chemical_symbols
from numpy.typing import ArrayLike, NDArray

from ...semantics import FrameSemantics
from ..atomic_connectivity import (
    CANONICAL_CONNECTIVITY_SCHEMA,
    AtomicConnectivityResult,
    AtomicConnectivityState,
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
AtomicSpeciesPair: TypeAlias = tuple[int, int]

CANONICAL_ATOMIC_TOPOLOGY_STATISTICS_SCHEMA = "mdstats.topology-statistics.atomic.v2"


@dataclass(frozen=True, slots=True)
class AtomicStatisticsOptions:
    """Controls optional TS1 atomic-connectivity statistics.

    ``species_pairs=None`` selects every species pair observed in at least one
    catalog state.  An explicit pair list may include a chemically possible pair
    with zero observed contacts, which produces a delta distribution at zero.
    """

    species_pairs: tuple[AtomicSpeciesPair, ...] | None = None
    include_degree_statistics: bool = True
    include_contact_occupancies: bool = True
    include_transition_statistics: bool = True
    include_temporal_statistics: bool = True
    include_contact_episodes: bool = True
    temporal_options: TemporalStatisticsOptions = field(
        default_factory=TemporalStatisticsOptions
    )
    quantiles: tuple[float, ...] = DEFAULT_QUANTILES

    def __post_init__(self) -> None:
        pairs = None
        if self.species_pairs is not None:
            pairs = tuple(_canonical_species_pair(pair) for pair in self.species_pairs)
            if len(set(pairs)) != len(pairs):
                raise TopologyStatisticsInputError(
                    "species_pairs contains duplicate canonical pairs."
                )
            pairs = tuple(sorted(pairs))
        quantiles = _validated_quantiles(self.quantiles)
        for name in (
            "include_degree_statistics",
            "include_contact_occupancies",
            "include_transition_statistics",
            "include_temporal_statistics",
            "include_contact_episodes",
        ):
            if not isinstance(getattr(self, name), (bool, np.bool_)):
                raise TopologyStatisticsInputError(f"{name} must be boolean.")
        object.__setattr__(self, "species_pairs", pairs)
        object.__setattr__(self, "quantiles", quantiles)
        object.__setattr__(
            self, "include_degree_statistics", bool(self.include_degree_statistics)
        )
        object.__setattr__(
            self, "include_contact_occupancies", bool(self.include_contact_occupancies)
        )
        object.__setattr__(
            self,
            "include_transition_statistics",
            bool(self.include_transition_statistics),
        )
        object.__setattr__(
            self, "include_temporal_statistics", bool(self.include_temporal_statistics)
        )
        object.__setattr__(
            self, "include_contact_episodes", bool(self.include_contact_episodes)
        )
        if not isinstance(self.temporal_options, TemporalStatisticsOptions):
            raise TopologyStatisticsInputError(
                "temporal_options must be TemporalStatisticsOptions."
            )

    @classmethod
    def from_species_pairs(
        cls,
        species_pairs: Sequence[tuple[int | str, int | str]],
        **kwargs: Any,
    ) -> "AtomicStatisticsOptions":
        """Construct options from atomic numbers or chemical symbols."""

        normalized = tuple(
            _canonical_species_pair((_atomic_number(left), _atomic_number(right)))
            for left, right in species_pairs
        )
        return cls(species_pairs=normalized, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_pairs": None
            if self.species_pairs is None
            else [list(pair) for pair in self.species_pairs],
            "include_degree_statistics": self.include_degree_statistics,
            "include_contact_occupancies": self.include_contact_occupancies,
            "include_transition_statistics": self.include_transition_statistics,
            "include_temporal_statistics": self.include_temporal_statistics,
            "include_contact_episodes": self.include_contact_episodes,
            "temporal_options": self.temporal_options.to_dict(),
            "quantiles": list(self.quantiles),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicStatisticsOptions":
        raw_pairs = payload.get("species_pairs")
        return cls(
            species_pairs=None
            if raw_pairs is None
            else tuple(tuple(int(x) for x in pair) for pair in raw_pairs),
            include_degree_statistics=payload.get("include_degree_statistics", True),
            include_contact_occupancies=payload.get(
                "include_contact_occupancies", True
            ),
            include_transition_statistics=payload.get(
                "include_transition_statistics", True
            ),
            include_temporal_statistics=payload.get(
                "include_temporal_statistics", True
            ),
            include_contact_episodes=payload.get("include_contact_episodes", True),
            temporal_options=TemporalStatisticsOptions.from_dict(
                _mapping(payload.get("temporal_options", {}), name="temporal_options")
            ),
            quantiles=tuple(
                float(x) for x in payload.get("quantiles", DEFAULT_QUANTILES)
            ),
        )


@dataclass(frozen=True, order=True, slots=True)
class AtomicContactKey:
    """Gauge-invariant identity of one atomic contact.

    Atomic connectivity states may use different periodic gauges.  Because the
    first atomic-connectivity schema forbids parallel edges, the unordered atom
    pair is the persistent contact identity across states.
    """

    atom_i: int
    atom_j: int

    def __post_init__(self) -> None:
        i = _nonnegative_int(self.atom_i, name="atom_i")
        j = _nonnegative_int(self.atom_j, name="atom_j")
        if i == j:
            raise TopologyStatisticsConsistencyError(
                "Atomic contacts require two distinct atom indices."
            )
        if i > j:
            i, j = j, i
        object.__setattr__(self, "atom_i", i)
        object.__setattr__(self, "atom_j", j)

    @property
    def pair(self) -> tuple[int, int]:
        return (self.atom_i, self.atom_j)

    def to_dict(self) -> dict[str, Any]:
        return {"atom_i": self.atom_i, "atom_j": self.atom_j}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicContactKey":
        return cls(atom_i=int(payload["atom_i"]), atom_j=int(payload["atom_j"]))


@dataclass(frozen=True, slots=True)
class AtomicContactOccupancy:
    """Observed frame occupancy of one gauge-invariant atomic contact."""

    contact: AtomicContactKey
    frame_count: int
    probability: float

    def __post_init__(self) -> None:
        if not isinstance(self.contact, AtomicContactKey):
            raise TopologyStatisticsConsistencyError("contact has the wrong type.")
        count = _nonnegative_int(self.frame_count, name="frame_count")
        probability = _finite_float(self.probability, name="probability")
        if probability < 0.0 or probability > 1.0:
            raise TopologyStatisticsConsistencyError(
                "Contact occupancy probability must lie in [0, 1]."
            )
        object.__setattr__(self, "frame_count", count)
        object.__setattr__(self, "probability", probability)

    def to_dict(self) -> dict[str, Any]:
        return {
            "contact": self.contact.to_dict(),
            "frame_count": self.frame_count,
            "probability": self.probability,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicContactOccupancy":
        return cls(
            contact=AtomicContactKey.from_dict(
                _mapping(payload["contact"], name="contact")
            ),
            frame_count=int(payload["frame_count"]),
            probability=float(payload["probability"]),
        )


@dataclass(frozen=True, slots=True)
class AtomicPairContactStatistics:
    """Exact per-frame contact statistics for one unordered species pair."""

    species_pair: AtomicSpeciesPair
    state_contact_counts: IntArray
    contact_count_series: ScalarSeries
    contact_count_distribution: DiscreteCountDistribution
    contact_occupancies: tuple[AtomicContactOccupancy, ...] | None
    contact_occupancy_summary: ScalarSummary | None

    def __post_init__(self) -> None:
        pair = _canonical_species_pair(self.species_pair)
        state_counts = _readonly_int_array(self.state_contact_counts, ndim=1)
        if np.any(state_counts < 0):
            raise TopologyStatisticsConsistencyError(
                "state_contact_counts cannot be negative."
            )
        if not isinstance(self.contact_count_series, ScalarSeries):
            raise TopologyStatisticsConsistencyError(
                "contact_count_series has the wrong type."
            )
        if not isinstance(self.contact_count_distribution, DiscreteCountDistribution):
            raise TopologyStatisticsConsistencyError(
                "contact_count_distribution has the wrong type."
            )
        values = np.asarray(self.contact_count_series.values, dtype=np.int64)
        if not np.array_equal(values, self.contact_count_series.values):
            raise TopologyStatisticsConsistencyError(
                "Contact-count series must contain integers."
            )
        expected_support, expected_frequencies = np.unique(values, return_counts=True)
        if not np.array_equal(
            expected_support, self.contact_count_distribution.support
        ) or not np.array_equal(
            expected_frequencies, self.contact_count_distribution.frequencies
        ):
            raise TopologyStatisticsConsistencyError(
                "Contact-count distribution disagrees with the frame series."
            )

        occupancies = self.contact_occupancies
        summary = self.contact_occupancy_summary
        if occupancies is None:
            if summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "contact_occupancy_summary requires contact_occupancies."
                )
        else:
            occupancies = tuple(occupancies)
            if tuple(sorted(item.contact for item in occupancies)) != tuple(
                item.contact for item in occupancies
            ):
                raise TopologyStatisticsConsistencyError(
                    "contact_occupancies must be sorted by canonical contact key."
                )
            if occupancies:
                if summary is None:
                    raise TopologyStatisticsConsistencyError(
                        "Nonempty contact_occupancies require contact_occupancy_summary."
                    )
                expected_summary = _summary_from_values(
                    np.asarray([item.probability for item in occupancies]),
                    summary.quantile_probabilities,
                )
                if expected_summary.to_dict() != summary.to_dict():
                    raise TopologyStatisticsConsistencyError(
                        "contact_occupancy_summary disagrees with contact records."
                    )
            elif summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "An empty contact_occupancy collection has no occupancy summary."
                )

        object.__setattr__(self, "species_pair", pair)
        object.__setattr__(self, "state_contact_counts", state_counts)
        object.__setattr__(self, "contact_occupancies", occupancies)

    @property
    def symbols(self) -> tuple[str, str]:
        return tuple(chemical_symbols[value] for value in self.species_pair)  # type: ignore[return-value]

    @property
    def label(self) -> str:
        left, right = self.symbols
        return f"{left}-{right}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_pair": list(self.species_pair),
            "state_contact_counts": self.state_contact_counts.tolist(),
            "contact_count_series": self.contact_count_series.to_dict(),
            "contact_count_distribution": self.contact_count_distribution.to_dict(),
            "contact_occupancies": None
            if self.contact_occupancies is None
            else [item.to_dict() for item in self.contact_occupancies],
            "contact_occupancy_summary": None
            if self.contact_occupancy_summary is None
            else self.contact_occupancy_summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicPairContactStatistics":
        raw_occupancies = payload["contact_occupancies"]
        raw_summary = payload["contact_occupancy_summary"]
        return cls(
            species_pair=tuple(int(x) for x in payload["species_pair"]),
            state_contact_counts=np.asarray(
                payload["state_contact_counts"], dtype=np.int64
            ),
            contact_count_series=ScalarSeries.from_dict(
                _mapping(payload["contact_count_series"], name="contact_count_series")
            ),
            contact_count_distribution=DiscreteCountDistribution.from_dict(
                _mapping(
                    payload["contact_count_distribution"],
                    name="contact_count_distribution",
                )
            ),
            contact_occupancies=None
            if raw_occupancies is None
            else tuple(
                AtomicContactOccupancy.from_dict(
                    _mapping(item, name="contact occupancy")
                )
                for item in raw_occupancies
            ),
            contact_occupancy_summary=None
            if raw_summary is None
            else ScalarSummary.from_dict(
                _mapping(raw_summary, name="contact_occupancy_summary")
            ),
        )


@dataclass(frozen=True, slots=True)
class AtomicSpeciesDegreeStatistics:
    """Degree statistics for all active atoms of one species."""

    atomic_number: int
    atom_indices: IntArray
    degree_distribution: DiscreteCountDistribution
    mean_degree_series: ScalarSeries
    per_atom_mean_degree: FloatArray
    per_atom_population_standard_deviation: FloatArray

    def __post_init__(self) -> None:
        number = _positive_int(self.atomic_number, name="atomic_number")
        if number >= len(chemical_symbols):
            raise TopologyStatisticsConsistencyError("Unknown atomic number.")
        indices = _readonly_int_array(self.atom_indices, ndim=1)
        means = _readonly_float_array(self.per_atom_mean_degree, ndim=1)
        deviations = _readonly_float_array(
            self.per_atom_population_standard_deviation, ndim=1
        )
        if indices.size == 0 or np.any(np.diff(indices) <= 0):
            raise TopologyStatisticsConsistencyError(
                "atom_indices must be nonempty and strictly increasing."
            )
        if means.shape != indices.shape or deviations.shape != indices.shape:
            raise TopologyStatisticsConsistencyError(
                "Per-atom degree summaries must align with atom_indices."
            )
        if np.any(means < 0.0) or np.any(deviations < 0.0):
            raise TopologyStatisticsConsistencyError(
                "Degree means and deviations cannot be negative."
            )
        if not isinstance(self.degree_distribution, DiscreteCountDistribution):
            raise TopologyStatisticsConsistencyError(
                "degree_distribution has the wrong type."
            )
        if not isinstance(self.mean_degree_series, ScalarSeries):
            raise TopologyStatisticsConsistencyError(
                "mean_degree_series has the wrong type."
            )
        object.__setattr__(self, "atomic_number", number)
        object.__setattr__(self, "atom_indices", indices)
        object.__setattr__(self, "per_atom_mean_degree", means)
        object.__setattr__(self, "per_atom_population_standard_deviation", deviations)

    @property
    def symbol(self) -> str:
        return chemical_symbols[self.atomic_number]

    @property
    def n_atoms(self) -> int:
        return int(self.atom_indices.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "atomic_number": self.atomic_number,
            "atom_indices": self.atom_indices.tolist(),
            "degree_distribution": self.degree_distribution.to_dict(),
            "mean_degree_series": self.mean_degree_series.to_dict(),
            "per_atom_mean_degree": self.per_atom_mean_degree.tolist(),
            "per_atom_population_standard_deviation": self.per_atom_population_standard_deviation.tolist(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicSpeciesDegreeStatistics":
        return cls(
            atomic_number=int(payload["atomic_number"]),
            atom_indices=np.asarray(payload["atom_indices"], dtype=np.int64),
            degree_distribution=DiscreteCountDistribution.from_dict(
                _mapping(payload["degree_distribution"], name="degree_distribution")
            ),
            mean_degree_series=ScalarSeries.from_dict(
                _mapping(payload["mean_degree_series"], name="mean_degree_series")
            ),
            per_atom_mean_degree=np.asarray(
                payload["per_atom_mean_degree"], dtype=np.float64
            ),
            per_atom_population_standard_deviation=np.asarray(
                payload["per_atom_population_standard_deviation"], dtype=np.float64
            ),
        )


@dataclass(frozen=True, slots=True)
class AtomicPairTransitionCount:
    """Aggregate edge additions and removals for one species pair."""

    species_pair: AtomicSpeciesPair
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
    def churn(self) -> int:
        return self.additions + self.removals

    @property
    def net_change(self) -> int:
        return self.additions - self.removals

    @property
    def label(self) -> str:
        left, right = (chemical_symbols[value] for value in self.species_pair)
        return f"{left}-{right}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_pair": list(self.species_pair),
            "additions": self.additions,
            "removals": self.removals,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicPairTransitionCount":
        return cls(
            species_pair=tuple(int(x) for x in payload["species_pair"]),
            additions=int(payload["additions"]),
            removals=int(payload["removals"]),
        )


@dataclass(frozen=True, slots=True)
class AtomicTransitionAggregateStatistics:
    """Trajectory-only aggregate changes between adjacent analyzed frames."""

    n_frame_boundaries: int
    n_changed_boundaries: int
    total_added_edges: int
    total_removed_edges: int
    pair_counts: tuple[AtomicPairTransitionCount, ...]
    affected_atom_indices: IntArray
    affected_atom_event_counts: IntArray

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
                "n_changed_boundaries cannot exceed n_frame_boundaries."
            )
        pair_counts = tuple(self.pair_counts)
        if tuple(sorted(item.species_pair for item in pair_counts)) != tuple(
            item.species_pair for item in pair_counts
        ):
            raise TopologyStatisticsConsistencyError(
                "pair_counts must be sorted by canonical species pair."
            )
        if (
            sum(item.additions for item in pair_counts) != added
            or sum(item.removals for item in pair_counts) != removed
        ):
            raise TopologyStatisticsConsistencyError(
                "Pair transition totals disagree with global totals."
            )
        indices = _readonly_int_array(self.affected_atom_indices, ndim=1)
        counts = _readonly_int_array(self.affected_atom_event_counts, ndim=1)
        if indices.shape != counts.shape:
            raise TopologyStatisticsConsistencyError(
                "Affected atom indices and event counts must align."
            )
        if indices.size and (np.any(np.diff(indices) <= 0) or np.any(counts <= 0)):
            raise TopologyStatisticsConsistencyError(
                "Affected atoms must be sorted and have positive event counts."
            )
        object.__setattr__(self, "n_frame_boundaries", boundaries)
        object.__setattr__(self, "n_changed_boundaries", changed)
        object.__setattr__(self, "total_added_edges", added)
        object.__setattr__(self, "total_removed_edges", removed)
        object.__setattr__(self, "pair_counts", pair_counts)
        object.__setattr__(self, "affected_atom_indices", indices)
        object.__setattr__(self, "affected_atom_event_counts", counts)

    @property
    def total_edge_churn(self) -> int:
        return self.total_added_edges + self.total_removed_edges

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_frame_boundaries": self.n_frame_boundaries,
            "n_changed_boundaries": self.n_changed_boundaries,
            "total_added_edges": self.total_added_edges,
            "total_removed_edges": self.total_removed_edges,
            "pair_counts": [item.to_dict() for item in self.pair_counts],
            "affected_atom_indices": self.affected_atom_indices.tolist(),
            "affected_atom_event_counts": self.affected_atom_event_counts.tolist(),
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "AtomicTransitionAggregateStatistics":
        return cls(
            n_frame_boundaries=int(payload["n_frame_boundaries"]),
            n_changed_boundaries=int(payload["n_changed_boundaries"]),
            total_added_edges=int(payload["total_added_edges"]),
            total_removed_edges=int(payload["total_removed_edges"]),
            pair_counts=tuple(
                AtomicPairTransitionCount.from_dict(
                    _mapping(item, name="pair transition count")
                )
                for item in payload["pair_counts"]
            ),
            affected_atom_indices=np.asarray(
                payload["affected_atom_indices"], dtype=np.int64
            ),
            affected_atom_event_counts=np.asarray(
                payload["affected_atom_event_counts"], dtype=np.int64
            ),
        )


@dataclass(frozen=True, slots=True)
class AtomicTemporalStatistics:
    """Exact TS3 trajectory organization for atomic states and contacts."""

    state_statistics: StateTransitionStatistics
    contact_keys: tuple[AtomicContactKey, ...]
    contact_episodes: EntityPresenceStatistics | None

    def __post_init__(self) -> None:
        if not isinstance(self.state_statistics, StateTransitionStatistics):
            raise TopologyStatisticsConsistencyError(
                "state_statistics has the wrong type."
            )
        keys = tuple(self.contact_keys)
        if keys != tuple(sorted(set(keys))):
            raise TopologyStatisticsConsistencyError(
                "contact_keys must be unique and sorted."
            )
        if self.contact_episodes is not None:
            if not isinstance(self.contact_episodes, EntityPresenceStatistics):
                raise TopologyStatisticsConsistencyError(
                    "contact_episodes has the wrong type."
                )
            if (
                self.contact_episodes.axis.to_dict()
                != self.state_statistics.axis.to_dict()
            ):
                raise TopologyStatisticsConsistencyError(
                    "Contact episodes and state statistics must use one axis."
                )
            if self.contact_episodes.n_entities != len(keys):
                raise TopologyStatisticsConsistencyError(
                    "Contact episode entity IDs must align with contact_keys."
                )
        object.__setattr__(self, "contact_keys", keys)

    def contact_episode_statistics(
        self, contact: AtomicContactKey
    ) -> tuple[EntityPresenceEpisode, ...]:
        if self.contact_episodes is None:
            raise KeyError("Contact episodes were disabled.")
        try:
            entity_id = self.contact_keys.index(contact)
        except ValueError as exc:
            raise KeyError(f"Contact {contact.pair} is not present.") from exc
        return self.contact_episodes.episodes_for(entity_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_statistics": self.state_statistics.to_dict(),
            "contact_keys": [key.to_dict() for key in self.contact_keys],
            "contact_episodes": None
            if self.contact_episodes is None
            else self.contact_episodes.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicTemporalStatistics":
        return cls(
            state_statistics=StateTransitionStatistics.from_dict(
                _mapping(payload["state_statistics"], name="state_statistics")
            ),
            contact_keys=tuple(
                AtomicContactKey.from_dict(_mapping(item, name="contact key"))
                for item in payload["contact_keys"]
            ),
            contact_episodes=None
            if payload["contact_episodes"] is None
            else EntityPresenceStatistics.from_dict(
                _mapping(payload["contact_episodes"], name="contact_episodes")
            ),
        )


@dataclass(frozen=True, slots=True)
class AtomicConnectivityStatistics:
    """Complete TS1 statistical summary of an atomic-connectivity catalog."""

    axis: FrameAxis
    catalog_occupancy: CatalogOccupancyStatistics
    active_atom_indices: IntArray
    active_atomic_numbers: IntArray
    total_edge_series: ScalarSeries
    total_edge_distribution: DiscreteCountDistribution
    pair_statistics: tuple[AtomicPairContactStatistics, ...]
    degree_statistics: tuple[AtomicSpeciesDegreeStatistics, ...] | None
    transition_statistics: AtomicTransitionAggregateStatistics | None
    temporal_statistics: AtomicTemporalStatistics | None
    options: AtomicStatisticsOptions
    source_definition_kind: str
    source_connectivity_schema: str
    source_state_digests: tuple[str, ...]
    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_ATOMIC_TOPOLOGY_STATISTICS_SCHEMA
    digest_algorithm: str = TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.axis, FrameAxis):
            raise TopologyStatisticsConsistencyError("axis has the wrong type.")
        if not isinstance(self.catalog_occupancy, CatalogOccupancyStatistics):
            raise TopologyStatisticsConsistencyError(
                "catalog_occupancy has the wrong type."
            )
        if self.catalog_occupancy.n_frames != self.axis.n_frames:
            raise TopologyStatisticsConsistencyError(
                "Catalog occupancy and frame axis must align."
            )
        if self.catalog_occupancy.frame_semantics is not self.axis.frame_semantics:
            raise TopologyStatisticsConsistencyError(
                "Catalog occupancy and axis semantics disagree."
            )
        active_indices = _readonly_int_array(self.active_atom_indices, ndim=1)
        active_numbers = _readonly_int_array(self.active_atomic_numbers, ndim=1)
        if active_indices.size == 0 or active_numbers.shape != active_indices.shape:
            raise TopologyStatisticsConsistencyError(
                "Active atom indices and atomic numbers must be aligned and nonempty."
            )
        if np.any(np.diff(active_indices) <= 0):
            raise TopologyStatisticsConsistencyError(
                "active_atom_indices must be strictly increasing."
            )
        if np.any(active_numbers <= 0) or np.any(
            active_numbers >= len(chemical_symbols)
        ):
            raise TopologyStatisticsConsistencyError(
                "active_atomic_numbers contains an unknown species."
            )
        atom_number_by_index = {
            int(index): int(number)
            for index, number in zip(active_indices, active_numbers, strict=True)
        }
        if not isinstance(self.total_edge_series, ScalarSeries):
            raise TopologyStatisticsConsistencyError(
                "total_edge_series has the wrong type."
            )
        if self.total_edge_series.axis.to_dict() != self.axis.to_dict():
            raise TopologyStatisticsConsistencyError(
                "total_edge_series does not use the result frame axis."
            )
        total_values = np.asarray(self.total_edge_series.values, dtype=np.int64)
        expected_support, expected_frequencies = np.unique(
            total_values, return_counts=True
        )
        if not np.array_equal(
            expected_support, self.total_edge_distribution.support
        ) or not np.array_equal(
            expected_frequencies, self.total_edge_distribution.frequencies
        ):
            raise TopologyStatisticsConsistencyError(
                "total_edge_distribution disagrees with total_edge_series."
            )

        pairs = tuple(self.pair_statistics)
        if tuple(sorted(item.species_pair for item in pairs)) != tuple(
            item.species_pair for item in pairs
        ):
            raise TopologyStatisticsConsistencyError(
                "pair_statistics must be sorted by species pair."
            )
        for item in pairs:
            if item.state_contact_counts.size != self.catalog_occupancy.n_states:
                raise TopologyStatisticsConsistencyError(
                    "Pair state counts must align with catalog states."
                )
            if item.contact_count_series.axis.to_dict() != self.axis.to_dict():
                raise TopologyStatisticsConsistencyError(
                    "Pair series does not use the result frame axis."
                )
            expected_frame_counts = expand_state_values_to_frames(
                item.state_contact_counts, self.catalog_occupancy.frame_to_state_id
            )
            if not np.array_equal(
                expected_frame_counts, item.contact_count_series.values
            ):
                raise TopologyStatisticsConsistencyError(
                    "Pair frame series disagrees with state counts and assignments."
                )
            if item.contact_occupancies is not None:
                for occupancy in item.contact_occupancies:
                    if (
                        occupancy.contact.atom_i not in atom_number_by_index
                        or occupancy.contact.atom_j not in atom_number_by_index
                    ):
                        raise TopologyStatisticsConsistencyError(
                            "An contact occupancy endpoint lies outside the active atom scope."
                        )
                    if (
                        _contact_species_pair(occupancy.contact, atom_number_by_index)
                        != item.species_pair
                    ):
                        raise TopologyStatisticsConsistencyError(
                            "An contact occupancy is assigned to the wrong species pair."
                        )
                    if occupancy.frame_count > self.axis.n_frames or not np.isclose(
                        occupancy.probability,
                        occupancy.frame_count / self.axis.n_frames,
                        rtol=0.0,
                        atol=1e-15,
                    ):
                        raise TopologyStatisticsConsistencyError(
                            "An contact occupancy disagrees with the result frame count."
                        )

        degrees = (
            None if self.degree_statistics is None else tuple(self.degree_statistics)
        )
        if degrees is not None and tuple(
            sorted(item.atomic_number for item in degrees)
        ) != tuple(item.atomic_number for item in degrees):
            raise TopologyStatisticsConsistencyError(
                "degree_statistics must be sorted by atomic number."
            )
        if degrees is not None:
            expected_species = tuple(
                sorted(set(int(value) for value in active_numbers))
            )
            if tuple(item.atomic_number for item in degrees) != expected_species:
                raise TopologyStatisticsConsistencyError(
                    "degree_statistics must contain every active species exactly once."
                )
            for item in degrees:
                expected_indices = active_indices[active_numbers == item.atomic_number]
                if not np.array_equal(item.atom_indices, expected_indices):
                    raise TopologyStatisticsConsistencyError(
                        "Degree-statistics atom indices disagree with the active scope."
                    )
        if (
            self.transition_statistics is not None
            and self.axis.frame_semantics is not FrameSemantics.TRAJECTORY
        ):
            raise TopologyStatisticsConsistencyError(
                "Transition aggregates are valid only for trajectories."
            )
        if self.temporal_statistics is not None:
            if self.axis.frame_semantics is not FrameSemantics.TRAJECTORY:
                raise TopologyStatisticsConsistencyError(
                    "Detailed temporal statistics are valid only for trajectories."
                )
            if not isinstance(self.temporal_statistics, AtomicTemporalStatistics):
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
                    "Detailed temporal state count disagrees with catalog occupancy."
                )
        if not isinstance(self.options, AtomicStatisticsOptions):
            raise TopologyStatisticsConsistencyError("options has the wrong type.")
        definition_kind = str(self.source_definition_kind).strip()
        if not definition_kind:
            raise TopologyStatisticsConsistencyError(
                "source_definition_kind cannot be empty."
            )
        if self.source_connectivity_schema != CANONICAL_CONNECTIVITY_SCHEMA:
            raise TopologyStatisticsConsistencyError(
                "Unsupported source connectivity schema."
            )
        state_digests = tuple(str(value) for value in self.source_state_digests)
        if len(state_digests) != self.catalog_occupancy.n_states or any(
            len(value) != 64 for value in state_digests
        ):
            raise TopologyStatisticsConsistencyError(
                "source_state_digests must contain one SHA-256 digest per state."
            )
        if self.canonical_schema_version != CANONICAL_ATOMIC_TOPOLOGY_STATISTICS_SCHEMA:
            raise TopologyStatisticsConsistencyError(
                "Unsupported atomic statistics schema version."
            )
        if self.digest_algorithm != TOPOLOGY_STATISTICS_DIGEST_ALGORITHM:
            raise TopologyStatisticsConsistencyError(
                "Unsupported atomic statistics digest algorithm."
            )
        metadata = MappingProxyType(_deep_copy_mapping(self.metadata))
        object.__setattr__(self, "active_atom_indices", active_indices)
        object.__setattr__(self, "active_atomic_numbers", active_numbers)
        object.__setattr__(self, "pair_statistics", pairs)
        object.__setattr__(self, "degree_statistics", degrees)
        object.__setattr__(self, "source_definition_kind", definition_kind)
        object.__setattr__(self, "source_state_digests", state_digests)
        object.__setattr__(self, "metadata", metadata)
        expected_digest = _atomic_statistics_digest(self)
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise TopologyStatisticsConsistencyError(
                "Stored atomic-statistics digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    @property
    def n_frames(self) -> int:
        return self.axis.n_frames

    @property
    def n_states(self) -> int:
        return self.catalog_occupancy.n_states

    def pair(self, left: int | str, right: int | str) -> AtomicPairContactStatistics:
        target = _canonical_species_pair((_atomic_number(left), _atomic_number(right)))
        for item in self.pair_statistics:
            if item.species_pair == target:
                return item
        raise KeyError(
            f"Species pair {target} is not present in this statistics result."
        )

    def species_degree(self, species: int | str) -> AtomicSpeciesDegreeStatistics:
        if self.degree_statistics is None:
            raise KeyError("Degree statistics were disabled.")
        target = _atomic_number(species)
        for item in self.degree_statistics:
            if item.atomic_number == target:
                return item
        raise KeyError(f"Species {target} is not present in degree statistics.")

    def to_dict(self) -> dict[str, Any]:
        return _atomic_statistics_payload(self, include_digest=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicConnectivityStatistics":
        if payload.get("schema_version") != CANONICAL_ATOMIC_TOPOLOGY_STATISTICS_SCHEMA:
            raise TopologyStatisticsSerializationError(
                "Unsupported atomic topology-statistics schema version."
            )
        if payload.get("object_type") != "AtomicConnectivityStatistics":
            raise TopologyStatisticsSerializationError(
                "Payload is not an AtomicConnectivityStatistics object."
            )
        try:
            return cls(
                axis=FrameAxis.from_dict(_mapping(payload["axis"], name="axis")),
                catalog_occupancy=CatalogOccupancyStatistics.from_dict(
                    _mapping(payload["catalog_occupancy"], name="catalog_occupancy")
                ),
                active_atom_indices=np.asarray(
                    payload["active_atom_indices"], dtype=np.int64
                ),
                active_atomic_numbers=np.asarray(
                    payload["active_atomic_numbers"], dtype=np.int64
                ),
                total_edge_series=ScalarSeries.from_dict(
                    _mapping(payload["total_edge_series"], name="total_edge_series")
                ),
                total_edge_distribution=DiscreteCountDistribution.from_dict(
                    _mapping(
                        payload["total_edge_distribution"],
                        name="total_edge_distribution",
                    )
                ),
                pair_statistics=tuple(
                    AtomicPairContactStatistics.from_dict(
                        _mapping(item, name="pair statistics")
                    )
                    for item in payload["pair_statistics"]
                ),
                degree_statistics=None
                if payload["degree_statistics"] is None
                else tuple(
                    AtomicSpeciesDegreeStatistics.from_dict(
                        _mapping(item, name="degree statistics")
                    )
                    for item in payload["degree_statistics"]
                ),
                transition_statistics=None
                if payload["transition_statistics"] is None
                else AtomicTransitionAggregateStatistics.from_dict(
                    _mapping(
                        payload["transition_statistics"],
                        name="transition_statistics",
                    )
                ),
                temporal_statistics=None
                if payload["temporal_statistics"] is None
                else AtomicTemporalStatistics.from_dict(
                    _mapping(payload["temporal_statistics"], name="temporal_statistics")
                ),
                options=AtomicStatisticsOptions.from_dict(
                    _mapping(payload["options"], name="options")
                ),
                source_definition_kind=str(payload["source_definition_kind"]),
                source_connectivity_schema=str(payload["source_connectivity_schema"]),
                source_state_digests=tuple(
                    str(value) for value in payload["source_state_digests"]
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
                "Malformed AtomicConnectivityStatistics payload."
            ) from exc


def compute_atomic_connectivity_statistics(
    catalog: AtomicConnectivityResult,
    *,
    steps: ArrayLike | None = None,
    times: ArrayLike | None = None,
    time_unit: str | None = None,
    options: AtomicStatisticsOptions | None = None,
) -> AtomicConnectivityStatistics:
    """Compute TS1 statistics from one completed atomic-connectivity catalog.

    The function evaluates state descriptors once per unique catalog state.  It
    never rebuilds connectivity and never interprets ensemble storage order as a
    time sequence.
    """

    if not isinstance(catalog, AtomicConnectivityResult):
        raise TypeError("catalog must be an AtomicConnectivityResult.")
    effective = AtomicStatisticsOptions() if options is None else options
    if not isinstance(effective, AtomicStatisticsOptions):
        raise TypeError("options must be an AtomicStatisticsOptions instance.")

    semantics = _catalog_frame_semantics(catalog)
    axis = build_frame_axis(
        int(catalog.frame_indices.size),
        frame_semantics=semantics,
        collection_frame_indices=catalog.frame_indices,
        frame_ids=catalog.frame_ids,
        steps=steps,
        times=times,
        time_unit=time_unit,
    )
    occupancy = compute_catalog_occupancy_statistics(
        catalog.frame_state_ids,
        frame_semantics=semantics,
        n_states=catalog.n_states,
    )
    atom_indices, atomic_numbers_by_position = _validate_catalog_state_alignment(
        catalog
    )
    atom_number_by_index = {
        int(index): int(number)
        for index, number in zip(atom_indices, atomic_numbers_by_position, strict=True)
    }

    state_total_edges = np.asarray(
        [state.n_edges for state in catalog.states], dtype=np.int64
    )
    frame_total_edges = expand_state_values_to_frames(
        state_total_edges, catalog.frame_state_ids
    )
    total_edge_series = build_scalar_series(
        "Total atomic edges",
        frame_total_edges,
        axis,
        unit="edges",
        quantiles=effective.quantiles,
    )
    total_edge_distribution = compute_discrete_count_distribution(
        frame_total_edges, quantiles=effective.quantiles
    )

    observed_pairs = _observed_species_pairs(catalog.states, atom_number_by_index)
    selected_pairs = (
        observed_pairs if effective.species_pairs is None else effective.species_pairs
    )
    active_species = set(int(value) for value in atomic_numbers_by_position)
    for pair in selected_pairs:
        if pair[0] not in active_species or pair[1] not in active_species:
            raise TopologyStatisticsInputError(
                f"Requested species pair {pair} contains a species outside the resolved scope."
            )

    pair_statistics = tuple(
        _compute_pair_statistics(
            pair,
            catalog,
            axis,
            occupancy.state_frame_counts,
            atom_number_by_index,
            include_contact_occupancies=effective.include_contact_occupancies,
            quantiles=effective.quantiles,
        )
        for pair in selected_pairs
    )

    degree_statistics = (
        _compute_degree_statistics(
            catalog,
            axis,
            occupancy.state_frame_counts,
            atom_indices,
            atomic_numbers_by_position,
            quantiles=effective.quantiles,
        )
        if effective.include_degree_statistics
        else None
    )

    transition_statistics = None
    if (
        effective.include_transition_statistics
        and semantics is FrameSemantics.TRAJECTORY
    ):
        transition_statistics = _compute_transition_aggregates(
            catalog, atom_number_by_index
        )

    temporal_statistics = None
    if effective.include_temporal_statistics and semantics is FrameSemantics.TRAJECTORY:
        state_statistics = compute_state_transition_statistics(
            catalog.frame_state_ids,
            axis,
            n_states=catalog.n_states,
            options=effective.temporal_options,
            metadata={"source": "AtomicConnectivityResult"},
        )
        contact_keys: tuple[AtomicContactKey, ...] = ()
        contact_episodes = None
        if effective.include_contact_episodes:
            contact_keys = tuple(
                sorted(
                    {
                        AtomicContactKey(*edge.pair)
                        for state in catalog.states
                        for edge in state.edge_keys
                    }
                )
            )
            contact_id = {key: index for index, key in enumerate(contact_keys)}
            state_contact_ids = tuple(
                tuple(
                    sorted(
                        contact_id[AtomicContactKey(*edge.pair)]
                        for edge in state.edge_keys
                    )
                )
                for state in catalog.states
            )
            contact_episodes = compute_entity_presence_statistics(
                state_contact_ids,
                catalog.frame_state_ids,
                axis,
                n_entities=len(contact_keys),
                options=effective.temporal_options,
                metadata={"entity_kind": "gauge_invariant_atomic_contact"},
            )
        temporal_statistics = AtomicTemporalStatistics(
            state_statistics=state_statistics,
            contact_keys=contact_keys,
            contact_episodes=contact_episodes,
        )

    metadata = {
        "module": "topology_statistics.atomic",
        "stage": "TS1",
        "frame_semantics": semantics.value,
        "catalog_consistency": catalog.consistency.value,
        "n_active_atoms": int(atom_indices.size),
        "catalog_metadata": _json_safe(dict(catalog.metadata)),
        "descriptive_only": True,
        "contact_wording": (
            "Atomic edges are summarized as contacts unless the source connectivity "
            "definition supports a stronger interpretation."
        ),
    }
    return AtomicConnectivityStatistics(
        axis=axis,
        catalog_occupancy=occupancy,
        active_atom_indices=atom_indices,
        active_atomic_numbers=atomic_numbers_by_position,
        total_edge_series=total_edge_series,
        total_edge_distribution=total_edge_distribution,
        pair_statistics=pair_statistics,
        degree_statistics=degree_statistics,
        transition_statistics=transition_statistics,
        temporal_statistics=temporal_statistics,
        options=effective,
        source_definition_kind=catalog.definition.kind,
        source_connectivity_schema=CANONICAL_CONNECTIVITY_SCHEMA,
        source_state_digests=tuple(state.digest for state in catalog.states),
        metadata=metadata,
    )


def _compute_pair_statistics(
    pair: AtomicSpeciesPair,
    catalog: AtomicConnectivityResult,
    axis: FrameAxis,
    state_frame_counts: IntArray,
    atom_number_by_index: Mapping[int, int],
    *,
    include_contact_occupancies: bool,
    quantiles: tuple[float, ...],
) -> AtomicPairContactStatistics:
    state_counts = np.zeros(catalog.n_states, dtype=np.int64)
    contact_frame_counts: dict[AtomicContactKey, int] = defaultdict(int)
    for state_id, state in enumerate(catalog.states):
        matching = tuple(
            edge
            for edge in state.edge_keys
            if _edge_species_pair(edge, atom_number_by_index) == pair
        )
        state_counts[state_id] = len(matching)
        if include_contact_occupancies and state_frame_counts[state_id] > 0:
            weight = int(state_frame_counts[state_id])
            for edge in matching:
                contact_frame_counts[AtomicContactKey(*edge.pair)] += weight
    frame_counts = expand_state_values_to_frames(state_counts, catalog.frame_state_ids)
    label = f"{chemical_symbols[pair[0]]}-{chemical_symbols[pair[1]]} contacts"
    series = build_scalar_series(
        label, frame_counts, axis, unit="edges", quantiles=quantiles
    )
    distribution = compute_discrete_count_distribution(
        frame_counts, quantiles=quantiles
    )
    occupancies = None
    occupancy_summary = None
    if include_contact_occupancies:
        occupancies = tuple(
            AtomicContactOccupancy(
                contact=contact,
                frame_count=count,
                probability=count / axis.n_frames,
            )
            for contact, count in sorted(contact_frame_counts.items())
        )
        if occupancies:
            values = np.asarray(
                [item.probability for item in occupancies], dtype=np.float64
            )
            occupancy_summary = _summary_from_values(values, quantiles)
    return AtomicPairContactStatistics(
        species_pair=pair,
        state_contact_counts=state_counts,
        contact_count_series=series,
        contact_count_distribution=distribution,
        contact_occupancies=occupancies,
        contact_occupancy_summary=occupancy_summary,
    )


def _compute_degree_statistics(
    catalog: AtomicConnectivityResult,
    axis: FrameAxis,
    state_frame_counts: IntArray,
    atom_indices: IntArray,
    atomic_numbers_by_position: IntArray,
    *,
    quantiles: tuple[float, ...],
) -> tuple[AtomicSpeciesDegreeStatistics, ...]:
    state_degree = np.stack(
        [np.asarray(state.degree, dtype=np.int64) for state in catalog.states], axis=0
    )
    frame_weights = state_frame_counts.astype(np.float64)
    total_frames = float(axis.n_frames)
    results: list[AtomicSpeciesDegreeStatistics] = []
    for atomic_number in sorted(
        set(int(value) for value in atomic_numbers_by_position)
    ):
        mask = atomic_numbers_by_position == atomic_number
        species_indices = atom_indices[mask]
        species_state_degree = state_degree[:, mask]
        state_mean_degree = np.mean(species_state_degree, axis=1)
        frame_mean_degree = expand_state_values_to_frames(
            state_mean_degree, catalog.frame_state_ids
        )
        mean_series = build_scalar_series(
            f"Mean {chemical_symbols[atomic_number]} degree",
            frame_mean_degree,
            axis,
            unit="edges/atom",
            quantiles=quantiles,
        )

        unique_degree, inverse = np.unique(species_state_degree, return_inverse=True)
        frequencies = np.zeros(unique_degree.size, dtype=np.int64)
        reshaped = inverse.reshape(species_state_degree.shape)
        for state_id, weight in enumerate(state_frame_counts):
            if weight:
                frequencies += np.bincount(
                    reshaped[state_id], minlength=unique_degree.size
                ).astype(np.int64) * int(weight)
        degree_distribution = _distribution_from_support_frequencies(
            unique_degree.astype(np.int64), frequencies, quantiles
        )

        per_atom_mean = (
            np.sum(species_state_degree * frame_weights[:, None], axis=0) / total_frames
        )
        per_atom_variance = (
            np.sum(
                (species_state_degree - per_atom_mean[None, :]) ** 2
                * frame_weights[:, None],
                axis=0,
            )
            / total_frames
        )
        results.append(
            AtomicSpeciesDegreeStatistics(
                atomic_number=atomic_number,
                atom_indices=species_indices,
                degree_distribution=degree_distribution,
                mean_degree_series=mean_series,
                per_atom_mean_degree=per_atom_mean,
                per_atom_population_standard_deviation=np.sqrt(per_atom_variance),
            )
        )
    return tuple(results)


def _compute_transition_aggregates(
    catalog: AtomicConnectivityResult,
    atom_number_by_index: Mapping[int, int],
) -> AtomicTransitionAggregateStatistics:
    pair_additions: dict[AtomicSpeciesPair, int] = defaultdict(int)
    pair_removals: dict[AtomicSpeciesPair, int] = defaultdict(int)
    affected_counts: dict[int, int] = defaultdict(int)
    changed_boundaries = 0
    total_added = 0
    total_removed = 0
    state_edges = [
        {AtomicContactKey(*edge.pair) for edge in state.edge_keys}
        for state in catalog.states
    ]
    assignments = np.asarray(catalog.frame_state_ids, dtype=np.int64)
    for position in range(1, assignments.size):
        left = int(assignments[position - 1])
        right = int(assignments[position])
        if left == right:
            continue
        added = state_edges[right] - state_edges[left]
        removed = state_edges[left] - state_edges[right]
        if not added and not removed:
            continue
        changed_boundaries += 1
        total_added += len(added)
        total_removed += len(removed)
        boundary_atoms: set[int] = set()
        for edge in added:
            pair_additions[_contact_species_pair(edge, atom_number_by_index)] += 1
            boundary_atoms.update(edge.pair)
        for edge in removed:
            pair_removals[_contact_species_pair(edge, atom_number_by_index)] += 1
            boundary_atoms.update(edge.pair)
        for atom_index in boundary_atoms:
            affected_counts[atom_index] += 1
    pairs = sorted(set(pair_additions) | set(pair_removals))
    affected_indices = np.asarray(sorted(affected_counts), dtype=np.int64)
    affected_event_counts = np.asarray(
        [affected_counts[int(index)] for index in affected_indices], dtype=np.int64
    )
    return AtomicTransitionAggregateStatistics(
        n_frame_boundaries=max(0, assignments.size - 1),
        n_changed_boundaries=changed_boundaries,
        total_added_edges=total_added,
        total_removed_edges=total_removed,
        pair_counts=tuple(
            AtomicPairTransitionCount(
                species_pair=pair,
                additions=pair_additions[pair],
                removals=pair_removals[pair],
            )
            for pair in pairs
        ),
        affected_atom_indices=affected_indices,
        affected_atom_event_counts=affected_event_counts,
    )


def _validate_catalog_state_alignment(
    catalog: AtomicConnectivityResult,
) -> tuple[IntArray, IntArray]:
    expected_indices = np.asarray(catalog.resolved_scope.atom_indices, dtype=np.int64)
    expected_numbers = np.asarray(catalog.resolved_scope.atomic_numbers, dtype=np.int64)
    for state in catalog.states:
        if not np.array_equal(
            state.active_atom_indices, expected_indices
        ) or not np.array_equal(state.active_atomic_numbers, expected_numbers):
            raise TopologyStatisticsInputError(
                "All connectivity states must share the catalog resolved atom scope."
            )
        if state.canonical_schema_version != CANONICAL_CONNECTIVITY_SCHEMA:
            raise TopologyStatisticsInputError(
                "A connectivity state uses an unsupported canonical schema."
            )
    indices = np.array(expected_indices, copy=True)
    numbers = np.array(expected_numbers, copy=True)
    indices.setflags(write=False)
    numbers.setflags(write=False)
    return indices, numbers


def _catalog_frame_semantics(catalog: AtomicConnectivityResult) -> FrameSemantics:
    raw = catalog.metadata.get("frame_semantics")
    try:
        return FrameSemantics(raw)
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsInputError(
            "AtomicConnectivityResult metadata lacks valid frame_semantics."
        ) from exc


def _observed_species_pairs(
    states: Sequence[AtomicConnectivityState],
    atom_number_by_index: Mapping[int, int],
) -> tuple[AtomicSpeciesPair, ...]:
    pairs = {
        _edge_species_pair(edge, atom_number_by_index)
        for state in states
        for edge in state.edge_keys
    }
    return tuple(sorted(pairs))


def _edge_species_pair(
    edge: Any, atom_number_by_index: Mapping[int, int]
) -> AtomicSpeciesPair:
    try:
        return _canonical_species_pair(
            (atom_number_by_index[edge.atom_i], atom_number_by_index[edge.atom_j])
        )
    except KeyError as exc:  # pragma: no cover - protected by catalog invariants
        raise TopologyStatisticsInputError(
            "An edge endpoint lies outside the resolved atom scope."
        ) from exc


def _contact_species_pair(
    contact: AtomicContactKey, atom_number_by_index: Mapping[int, int]
) -> AtomicSpeciesPair:
    try:
        return _canonical_species_pair(
            (
                atom_number_by_index[contact.atom_i],
                atom_number_by_index[contact.atom_j],
            )
        )
    except KeyError as exc:  # pragma: no cover - protected by result invariants
        raise TopologyStatisticsInputError(
            "A contact endpoint lies outside the active atom scope."
        ) from exc


def _distribution_from_support_frequencies(
    support: IntArray,
    frequencies: IntArray,
    quantiles: tuple[float, ...],
) -> DiscreteCountDistribution:
    support = np.asarray(support, dtype=np.int64)
    frequencies = np.asarray(frequencies, dtype=np.int64)
    keep = frequencies > 0
    support = support[keep]
    frequencies = frequencies[keep]
    if support.size == 0:
        raise TopologyStatisticsConsistencyError(
            "A weighted count distribution cannot be empty."
        )
    total = int(np.sum(frequencies, dtype=np.int64))
    probabilities = frequencies.astype(np.float64) / total
    summary = _summary_from_support_frequencies(support, frequencies, quantiles)
    modes = tuple(int(value) for value in support[frequencies == np.max(frequencies)])
    return DiscreteCountDistribution(
        support=support,
        frequencies=frequencies,
        probabilities=probabilities,
        summary=summary,
        modes=modes,
    )


def _summary_from_support_frequencies(
    support: IntArray,
    frequencies: IntArray,
    quantiles: tuple[float, ...],
) -> ScalarSummary:
    total = int(np.sum(frequencies, dtype=np.int64))
    probabilities = frequencies.astype(np.float64) / total
    values = support.astype(np.float64)
    mean = float(np.dot(values, probabilities))
    variance = float(np.dot((values - mean) ** 2, probabilities))
    quantile_values = np.asarray(
        [_weighted_linear_quantile(support, frequencies, q) for q in quantiles],
        dtype=np.float64,
    )
    median_position = quantiles.index(0.5) if 0.5 in quantiles else None
    median = (
        float(quantile_values[median_position])
        if median_position is not None
        else _weighted_linear_quantile(support, frequencies, 0.5)
    )
    return ScalarSummary(
        count=total,
        mean=mean,
        population_standard_deviation=float(np.sqrt(max(0.0, variance))),
        minimum=float(support[0]),
        maximum=float(support[-1]),
        median=float(median),
        quantile_probabilities=np.asarray(quantiles, dtype=np.float64),
        quantile_values=quantile_values,
        is_constant=bool(support.size == 1),
    )


def _weighted_linear_quantile(
    support: IntArray, frequencies: IntArray, probability: float
) -> float:
    total = int(np.sum(frequencies, dtype=np.int64))
    position = probability * (total - 1)
    lower = int(np.floor(position))
    upper = int(np.ceil(position))
    fraction = position - lower
    cumulative = np.cumsum(frequencies)
    lower_value = float(support[int(np.searchsorted(cumulative, lower, side="right"))])
    upper_value = float(support[int(np.searchsorted(cumulative, upper, side="right"))])
    return lower_value + fraction * (upper_value - lower_value)


def _summary_from_values(
    values: ArrayLike, quantiles: Sequence[float]
) -> ScalarSummary:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size == 0 or not np.all(np.isfinite(array)):
        raise TopologyStatisticsConsistencyError(
            "Summary values must be a finite nonempty vector."
        )
    probabilities = _validated_quantiles(tuple(float(x) for x in quantiles))
    quantile_values = np.quantile(array, probabilities)
    minimum = float(np.min(array))
    maximum = float(np.max(array))
    return ScalarSummary(
        count=int(array.size),
        mean=float(np.mean(array)),
        population_standard_deviation=float(np.std(array, ddof=0)),
        minimum=minimum,
        maximum=maximum,
        median=float(np.median(array)),
        quantile_probabilities=np.asarray(probabilities, dtype=np.float64),
        quantile_values=np.asarray(quantile_values, dtype=np.float64),
        is_constant=minimum == maximum,
    )


def _atomic_statistics_payload(
    result: AtomicConnectivityStatistics, *, include_digest: bool
) -> dict[str, Any]:
    payload = {
        "schema_version": result.canonical_schema_version,
        "object_type": "AtomicConnectivityStatistics",
        "digest_algorithm": result.digest_algorithm,
        "axis": result.axis.to_dict(),
        "catalog_occupancy": result.catalog_occupancy.to_dict(),
        "active_atom_indices": result.active_atom_indices.tolist(),
        "active_atomic_numbers": result.active_atomic_numbers.tolist(),
        "total_edge_series": result.total_edge_series.to_dict(),
        "total_edge_distribution": result.total_edge_distribution.to_dict(),
        "pair_statistics": [item.to_dict() for item in result.pair_statistics],
        "degree_statistics": None
        if result.degree_statistics is None
        else [item.to_dict() for item in result.degree_statistics],
        "transition_statistics": None
        if result.transition_statistics is None
        else result.transition_statistics.to_dict(),
        "temporal_statistics": None
        if result.temporal_statistics is None
        else result.temporal_statistics.to_dict(),
        "options": result.options.to_dict(),
        "source_definition_kind": result.source_definition_kind,
        "source_connectivity_schema": result.source_connectivity_schema,
        "source_state_digests": list(result.source_state_digests),
        "metadata": _json_safe(dict(result.metadata)),
    }
    if include_digest:
        payload["digest"] = result.digest
    return payload


def _atomic_statistics_digest(result: AtomicConnectivityStatistics) -> str:
    encoded = canonical_statistics_json(
        _atomic_statistics_payload(result, include_digest=False)
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_species_pair(pair: Sequence[int]) -> AtomicSpeciesPair:
    if len(pair) != 2:
        raise TopologyStatisticsInputError("A species pair must contain two entries.")
    left = _positive_int(pair[0], name="species atomic number")
    right = _positive_int(pair[1], name="species atomic number")
    if left >= len(chemical_symbols) or right >= len(chemical_symbols):
        raise TopologyStatisticsInputError("Unknown species atomic number.")
    return (left, right) if left <= right else (right, left)


def _atomic_number(value: int | str) -> int:
    if isinstance(value, str):
        symbol = value.strip()
        if symbol not in atomic_numbers:
            raise TopologyStatisticsInputError(f"Unknown chemical symbol: {value!r}.")
        return int(atomic_numbers[symbol])
    return _positive_int(value, name="atomic number")


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


def _readonly_int_array(values: ArrayLike, *, ndim: int) -> IntArray:
    array = np.asarray(values)
    if (
        array.ndim != ndim
        or not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsConsistencyError(
            f"Expected a {ndim}-dimensional integer array."
        )
    result = np.array(array, dtype=np.int64, copy=True)
    result.setflags(write=False)
    return result


def _readonly_float_array(values: ArrayLike, *, ndim: int) -> FloatArray:
    array = np.asarray(values)
    if array.ndim != ndim or not np.issubdtype(array.dtype, np.number):
        raise TopologyStatisticsConsistencyError(
            f"Expected a {ndim}-dimensional numeric array."
        )
    result = np.array(array, dtype=np.float64, copy=True)
    if not np.all(np.isfinite(result)):
        raise TopologyStatisticsConsistencyError("Array contains nonfinite values.")
    result.setflags(write=False)
    return result


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TopologyStatisticsConsistencyError(f"{name} must be an integer.")
    result = int(value)
    if result <= 0:
        raise TopologyStatisticsConsistencyError(f"{name} must be positive.")
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
        raise TopologyStatisticsConsistencyError(f"{name} must be an integer.")
    result = int(value)
    if result < 0:
        raise TopologyStatisticsConsistencyError(f"{name} cannot be negative.")
    return result


def _finite_float(value: Any, *, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise TopologyStatisticsConsistencyError(f"{name} must be numeric.")
    result = float(value)
    if not np.isfinite(result):
        raise TopologyStatisticsConsistencyError(f"{name} must be finite.")
    return result


def _mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TopologyStatisticsSerializationError(f"{name} must be a mapping.")
    return value


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(json.dumps(_json_safe(value), allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsConsistencyError(
            "metadata must be JSON-compatible and finite."
        ) from exc


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, FrameSemantics):
        return value.value
    return value


__all__ = [
    "CANONICAL_ATOMIC_TOPOLOGY_STATISTICS_SCHEMA",
    "AtomicConnectivityStatistics",
    "AtomicContactKey",
    "AtomicContactOccupancy",
    "AtomicPairContactStatistics",
    "AtomicPairTransitionCount",
    "AtomicSpeciesDegreeStatistics",
    "AtomicStatisticsOptions",
    "AtomicTransitionAggregateStatistics",
    "compute_atomic_connectivity_statistics",
]
