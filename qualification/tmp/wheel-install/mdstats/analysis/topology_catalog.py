"""Exact framework-topology classification across frame collections.

This module is the Stage 3 bridge between single-state framework projection and
ring enumeration.  It projects each canonical atomic-connectivity state through
one immutable :class:`~mdstats.analysis.framework_topology.FrameworkMapping`,
reconciles exact projected topology classes, and records frame groups,
trajectory segments, and transition-local edge differences.

Topology identity is structural and mapping-dependent.  It is defined by the
canonical Stage 2 :class:`FrameworkEdgeKey` records, not by traversal direction,
projection diagnostics, or raw path provenance.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ..collection import AtomisticFrameCollection
from ..semantics import FrameSemantics
from .atomic_connectivity import (
    AtomicConnectivityResult,
    AtomicConnectivityState,
    AtomicEdgeKey,
)
from .framework_topology import (
    CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA,
    FrameworkEdgeKey,
    FrameworkMapping,
    FrameworkProjectionOptions,
    FrameworkTopology,
    FrameworkTopologyError,
    FrameworkValidationRules,
    build_framework_topology,
)

IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
FloatArray = NDArray[np.float64]

CANONICAL_TOPOLOGY_CATALOG_SCHEMA = "mdstats.topology-catalog.v1"
TOPOLOGY_CATALOG_DIGEST_ALGORITHM = "sha256"


class TopologyCatalogError(ValueError):
    """Base class for topology-catalog failures."""


class TopologyCatalogInputError(TopologyCatalogError):
    """Raised when source collection, connectivity, or options are incompatible."""


class TopologyCatalogProjectionError(TopologyCatalogError):
    """Raised when one source connectivity state cannot be projected."""


class TopologyCatalogConsistencyError(TopologyCatalogError):
    """Raised when catalog arrays, classes, segments, or transitions disagree."""


class TopologyCatalogSerializationError(TopologyCatalogError):
    """Raised when a serialized topology catalog is malformed or inconsistent."""


class TopologyConsistency(str, Enum):
    """Cross-frame organization of exact projected framework topologies."""

    UNDEFINED = "undefined"
    UNIFORM = "uniform"
    PARTITIONED = "partitioned"
    PER_FRAME = "per_frame"


class TopologySegmentStatus(str, Enum):
    """Descriptive persistence label for one trajectory topology segment."""

    CONFIRMED = "confirmed"
    TRANSIENT = "transient"


@dataclass(frozen=True, slots=True)
class TopologyCatalogOptions:
    """Classification and transition-storage policy for Stage 3."""

    mode: Literal["catalog", "per_frame"] = "catalog"
    minimum_persistent_frames: int = 1
    include_atomic_edge_differences: bool = True
    include_framework_edge_differences: bool = True

    def __post_init__(self) -> None:
        if self.mode not in {"catalog", "per_frame"}:
            raise TopologyCatalogInputError("mode must be 'catalog' or 'per_frame'.")
        if (
            isinstance(self.minimum_persistent_frames, bool)
            or not isinstance(self.minimum_persistent_frames, (int, np.integer))
            or int(self.minimum_persistent_frames) < 1
        ):
            raise TopologyCatalogInputError(
                "minimum_persistent_frames must be a positive integer."
            )
        object.__setattr__(
            self, "minimum_persistent_frames", int(self.minimum_persistent_frames)
        )
        for name in (
            "include_atomic_edge_differences",
            "include_framework_edge_differences",
        ):
            if type(getattr(self, name)) is not bool:
                raise TopologyCatalogInputError(f"{name} must be a bool.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "minimum_persistent_frames": self.minimum_persistent_frames,
            "include_atomic_edge_differences": self.include_atomic_edge_differences,
            "include_framework_edge_differences": self.include_framework_edge_differences,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyCatalogOptions":
        return cls(
            mode=str(payload["mode"]),  # type: ignore[arg-type]
            minimum_persistent_frames=int(payload["minimum_persistent_frames"]),
            include_atomic_edge_differences=payload["include_atomic_edge_differences"],
            include_framework_edge_differences=payload[
                "include_framework_edge_differences"
            ],
        )


@dataclass(frozen=True, slots=True)
class TopologyFrameGroup:
    """All selected result positions assigned to one topology ID."""

    topology_id: int
    result_positions: IntArray

    def __post_init__(self) -> None:
        topology_id = _nonnegative_int(self.topology_id, name="topology_id")
        positions = _readonly_array(self.result_positions, np.int64, ndim=1)
        if positions.size == 0 or np.any(np.diff(positions) <= 0):
            raise TopologyCatalogConsistencyError(
                "result_positions must be nonempty and strictly increasing."
            )
        object.__setattr__(self, "topology_id", topology_id)
        object.__setattr__(self, "result_positions", positions)

    def to_dict(self) -> dict[str, Any]:
        return {
            "topology_id": self.topology_id,
            "result_positions": self.result_positions.tolist(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyFrameGroup":
        return cls(
            topology_id=int(payload["topology_id"]),
            result_positions=np.asarray(payload["result_positions"], dtype=np.int64),
        )


@dataclass(frozen=True, slots=True)
class TopologySegment:
    """One maximal contiguous topology run in selected trajectory order."""

    segment_id: int
    topology_id: int
    result_position_start: int
    result_position_stop: int
    status: TopologySegmentStatus

    def __post_init__(self) -> None:
        for name in (
            "segment_id",
            "topology_id",
            "result_position_start",
            "result_position_stop",
        ):
            object.__setattr__(
                self, name, _nonnegative_int(getattr(self, name), name=name)
            )
        if self.result_position_stop <= self.result_position_start:
            raise TopologyCatalogConsistencyError(
                "Topology segment interval must be nonempty and half-open."
            )
        object.__setattr__(self, "status", TopologySegmentStatus(self.status))

    @property
    def length(self) -> int:
        return self.result_position_stop - self.result_position_start

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "topology_id": self.topology_id,
            "result_position_start": self.result_position_start,
            "result_position_stop": self.result_position_stop,
            "status": self.status.value,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologySegment":
        return cls(
            segment_id=int(payload["segment_id"]),
            topology_id=int(payload["topology_id"]),
            result_position_start=int(payload["result_position_start"]),
            result_position_stop=int(payload["result_position_stop"]),
            status=TopologySegmentStatus(payload["status"]),
        )


@dataclass(frozen=True, slots=True)
class TopologyTransition:
    """Exact structural change at one adjacent trajectory-segment boundary."""

    transition_id: int
    source_segment_id: int
    target_segment_id: int
    source_topology_id: int
    target_topology_id: int
    source_connectivity_state_id: int
    target_connectivity_state_id: int
    result_position_before: int
    result_position_after: int
    collection_frame_index_before: int
    collection_frame_index_after: int
    frame_id_before: int
    frame_id_after: int
    added_atomic_edges: tuple[AtomicEdgeKey, ...]
    removed_atomic_edges: tuple[AtomicEdgeKey, ...]
    added_framework_edges: tuple[FrameworkEdgeKey, ...]
    removed_framework_edges: tuple[FrameworkEdgeKey, ...]
    affected_atom_indices: tuple[int, ...]
    affected_vertex_atom_indices: tuple[int, ...]
    affected_linker_atom_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        integer_names = (
            "transition_id",
            "source_segment_id",
            "target_segment_id",
            "source_topology_id",
            "target_topology_id",
            "source_connectivity_state_id",
            "target_connectivity_state_id",
            "result_position_before",
            "result_position_after",
            "collection_frame_index_before",
            "collection_frame_index_after",
            "frame_id_before",
            "frame_id_after",
        )
        for name in integer_names:
            object.__setattr__(
                self, name, _nonnegative_int(getattr(self, name), name=name)
            )
        if self.result_position_after != self.result_position_before + 1:
            raise TopologyCatalogConsistencyError(
                "Transition result positions must be adjacent."
            )
        if self.target_segment_id != self.source_segment_id + 1:
            raise TopologyCatalogConsistencyError(
                "Transition segment IDs must be adjacent."
            )
        if self.source_topology_id == self.target_topology_id:
            raise TopologyCatalogConsistencyError(
                "Topology transitions require distinct source and target classes."
            )
        object.__setattr__(
            self,
            "added_atomic_edges",
            _canonical_object_tuple(self.added_atomic_edges, AtomicEdgeKey),
        )
        object.__setattr__(
            self,
            "removed_atomic_edges",
            _canonical_object_tuple(self.removed_atomic_edges, AtomicEdgeKey),
        )
        object.__setattr__(
            self,
            "added_framework_edges",
            _canonical_object_tuple(self.added_framework_edges, FrameworkEdgeKey),
        )
        object.__setattr__(
            self,
            "removed_framework_edges",
            _canonical_object_tuple(self.removed_framework_edges, FrameworkEdgeKey),
        )
        for name in (
            "affected_atom_indices",
            "affected_vertex_atom_indices",
            "affected_linker_atom_indices",
        ):
            object.__setattr__(
                self,
                name,
                tuple(
                    sorted(
                        {
                            _nonnegative_int(value, name=name)
                            for value in getattr(self, name)
                        }
                    )
                ),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "source_segment_id": self.source_segment_id,
            "target_segment_id": self.target_segment_id,
            "source_topology_id": self.source_topology_id,
            "target_topology_id": self.target_topology_id,
            "source_connectivity_state_id": self.source_connectivity_state_id,
            "target_connectivity_state_id": self.target_connectivity_state_id,
            "result_position_before": self.result_position_before,
            "result_position_after": self.result_position_after,
            "collection_frame_index_before": self.collection_frame_index_before,
            "collection_frame_index_after": self.collection_frame_index_after,
            "frame_id_before": self.frame_id_before,
            "frame_id_after": self.frame_id_after,
            "added_atomic_edges": [edge.to_dict() for edge in self.added_atomic_edges],
            "removed_atomic_edges": [
                edge.to_dict() for edge in self.removed_atomic_edges
            ],
            "added_framework_edges": [
                edge.to_dict() for edge in self.added_framework_edges
            ],
            "removed_framework_edges": [
                edge.to_dict() for edge in self.removed_framework_edges
            ],
            "affected_atom_indices": list(self.affected_atom_indices),
            "affected_vertex_atom_indices": list(self.affected_vertex_atom_indices),
            "affected_linker_atom_indices": list(self.affected_linker_atom_indices),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyTransition":
        return cls(
            transition_id=int(payload["transition_id"]),
            source_segment_id=int(payload["source_segment_id"]),
            target_segment_id=int(payload["target_segment_id"]),
            source_topology_id=int(payload["source_topology_id"]),
            target_topology_id=int(payload["target_topology_id"]),
            source_connectivity_state_id=int(payload["source_connectivity_state_id"]),
            target_connectivity_state_id=int(payload["target_connectivity_state_id"]),
            result_position_before=int(payload["result_position_before"]),
            result_position_after=int(payload["result_position_after"]),
            collection_frame_index_before=int(payload["collection_frame_index_before"]),
            collection_frame_index_after=int(payload["collection_frame_index_after"]),
            frame_id_before=int(payload["frame_id_before"]),
            frame_id_after=int(payload["frame_id_after"]),
            added_atomic_edges=tuple(
                AtomicEdgeKey.from_dict(x) for x in payload["added_atomic_edges"]
            ),
            removed_atomic_edges=tuple(
                AtomicEdgeKey.from_dict(x) for x in payload["removed_atomic_edges"]
            ),
            added_framework_edges=tuple(
                FrameworkEdgeKey.from_dict(x) for x in payload["added_framework_edges"]
            ),
            removed_framework_edges=tuple(
                FrameworkEdgeKey.from_dict(x)
                for x in payload["removed_framework_edges"]
            ),
            affected_atom_indices=tuple(payload["affected_atom_indices"]),
            affected_vertex_atom_indices=tuple(payload["affected_vertex_atom_indices"]),
            affected_linker_atom_indices=tuple(payload["affected_linker_atom_indices"]),
        )


@dataclass(frozen=True, slots=True, eq=False)
class TopologyCatalog:
    """Immutable exact topology classes and their cross-frame organization."""

    mapping: FrameworkMapping
    validation_rules: FrameworkValidationRules | None
    projection_options: FrameworkProjectionOptions
    catalog_options: TopologyCatalogOptions
    frame_semantics: FrameSemantics
    consistency: TopologyConsistency

    frame_indices: IntArray
    frame_ids: IntArray
    frame_connectivity_state_ids: Int32Array
    connectivity_state_topology_ids: Int32Array
    frame_topology_ids: Int32Array

    topologies: tuple[FrameworkTopology, ...]
    frame_groups: tuple[TopologyFrameGroup, ...]
    segments: tuple[TopologySegment, ...] | None
    transitions: tuple[TopologyTransition, ...]

    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_TOPOLOGY_CATALOG_SCHEMA
    digest_algorithm: str = TOPOLOGY_CATALOG_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.mapping, FrameworkMapping):
            raise TopologyCatalogConsistencyError("mapping has the wrong type.")
        if self.validation_rules is not None and not isinstance(
            self.validation_rules, FrameworkValidationRules
        ):
            raise TopologyCatalogConsistencyError(
                "validation_rules has the wrong type."
            )
        if not isinstance(self.projection_options, FrameworkProjectionOptions):
            raise TopologyCatalogConsistencyError(
                "projection_options has the wrong type."
            )
        if not isinstance(self.catalog_options, TopologyCatalogOptions):
            raise TopologyCatalogConsistencyError("catalog_options has the wrong type.")
        semantics = FrameSemantics(self.frame_semantics)
        consistency = TopologyConsistency(self.consistency)
        if consistency is TopologyConsistency.UNDEFINED:
            raise TopologyCatalogConsistencyError(
                "Constructed catalogs cannot have UNDEFINED consistency."
            )

        frames = _readonly_array(self.frame_indices, np.int64, ndim=1)
        frame_ids = _readonly_array(self.frame_ids, np.int64, ndim=1)
        state_ids = _readonly_array(self.frame_connectivity_state_ids, np.int32, ndim=1)
        state_topology_ids = _readonly_array(
            self.connectivity_state_topology_ids, np.int32, ndim=1
        )
        topology_ids = _readonly_array(self.frame_topology_ids, np.int32, ndim=1)
        if frames.size == 0 or any(
            array.shape != frames.shape
            for array in (frame_ids, state_ids, topology_ids)
        ):
            raise TopologyCatalogConsistencyError(
                "Frame arrays must be equal, one-dimensional, and nonempty."
            )
        if len(set(int(x) for x in frames)) != frames.size:
            raise TopologyCatalogConsistencyError("frame_indices must be unique.")
        topologies = tuple(self.topologies)
        if not topologies or any(
            not isinstance(topology, FrameworkTopology) for topology in topologies
        ):
            raise TopologyCatalogConsistencyError(
                "topologies must contain at least one FrameworkTopology."
            )
        if np.any(topology_ids < 0) or np.any(topology_ids >= len(topologies)):
            raise TopologyCatalogConsistencyError(
                "frame_topology_ids contain invalid topology IDs."
            )
        if np.any(state_ids < 0):
            raise TopologyCatalogConsistencyError(
                "frame_connectivity_state_ids must be nonnegative."
            )
        if any(
            topology.mapping_digest != self.mapping.digest for topology in topologies
        ):
            raise TopologyCatalogConsistencyError(
                "All stored topologies must use the catalog mapping."
            )
        if any(
            topology.canonical_schema_version != CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA
            for topology in topologies
        ):
            raise TopologyCatalogConsistencyError(
                "Stored topology schema version is incompatible."
            )

        if self.catalog_options.mode == "catalog":
            if state_topology_ids.size == 0:
                raise TopologyCatalogConsistencyError(
                    "Catalog mode requires connectivity_state_topology_ids."
                )
            if np.any(state_ids >= state_topology_ids.size):
                raise TopologyCatalogConsistencyError(
                    "Frame state IDs exceed the state-to-topology mapping."
                )
            if np.any(state_topology_ids < 0) or np.any(
                state_topology_ids >= len(topologies)
            ):
                raise TopologyCatalogConsistencyError(
                    "connectivity_state_topology_ids contain invalid topology IDs."
                )
            if not np.array_equal(topology_ids, state_topology_ids[state_ids]):
                raise TopologyCatalogConsistencyError(
                    "Frame topology IDs disagree with state topology IDs."
                )
            first_occurrence_order = tuple(
                dict.fromkeys(int(value) for value in topology_ids)
            )
            if first_occurrence_order != tuple(range(len(topologies))):
                raise TopologyCatalogConsistencyError(
                    "Topology IDs must follow first occurrence in selected frame order."
                )
            expected_consistency = (
                TopologyConsistency.UNIFORM
                if len(topologies) == 1
                else TopologyConsistency.PARTITIONED
            )
            if consistency is not expected_consistency:
                raise TopologyCatalogConsistencyError(
                    "Catalog consistency disagrees with stored topology count."
                )
            structural_keys = [_framework_structural_key(x) for x in topologies]
            if len(set(structural_keys)) != len(structural_keys):
                raise TopologyCatalogConsistencyError(
                    "Catalog mode contains duplicate exact topology classes."
                )
        else:
            if state_topology_ids.size != 0:
                raise TopologyCatalogConsistencyError(
                    "Per-frame mode requires an empty state-to-topology array."
                )
            if consistency is not TopologyConsistency.PER_FRAME:
                raise TopologyCatalogConsistencyError(
                    "Per-frame mode requires PER_FRAME consistency."
                )
            if len(topologies) != frames.size or not np.array_equal(
                topology_ids, np.arange(frames.size, dtype=np.int32)
            ):
                raise TopologyCatalogConsistencyError(
                    "Per-frame mode requires one public topology per selected frame."
                )

        groups = tuple(self.frame_groups)
        if len(groups) != len(topologies):
            raise TopologyCatalogConsistencyError(
                "There must be one frame group per stored topology."
            )
        if tuple(group.topology_id for group in groups) != tuple(range(len(groups))):
            raise TopologyCatalogConsistencyError(
                "Frame groups must be sorted by dense topology ID."
            )
        grouped_positions = np.concatenate([group.result_positions for group in groups])
        if not np.array_equal(
            np.sort(grouped_positions), np.arange(frames.size, dtype=np.int64)
        ):
            raise TopologyCatalogConsistencyError(
                "Frame groups must partition selected result positions exactly."
            )
        for group in groups:
            expected = np.flatnonzero(topology_ids == group.topology_id)
            if not np.array_equal(group.result_positions, expected):
                raise TopologyCatalogConsistencyError(
                    "Frame-group membership disagrees with frame topology IDs."
                )

        segments = None if self.segments is None else tuple(self.segments)
        transitions = tuple(self.transitions)
        if (
            semantics is FrameSemantics.TRAJECTORY
            and self.catalog_options.mode == "catalog"
        ):
            if segments is None:
                raise TopologyCatalogConsistencyError(
                    "Trajectory catalog mode requires segments."
                )
            _validate_segments(
                segments,
                topology_ids,
                self.catalog_options.minimum_persistent_frames,
            )
            _validate_transitions(
                transitions,
                segments,
                frames,
                frame_ids,
                state_ids,
                topologies,
                self.catalog_options,
            )
        else:
            if segments is not None or transitions:
                raise TopologyCatalogConsistencyError(
                    "Ensemble and per-frame catalogs cannot contain segments or transitions."
                )

        metadata = MappingProxyType(_deep_copy_mapping(self.metadata))
        source_digests = metadata.get("source_connectivity_state_digests")
        if not isinstance(source_digests, tuple) or any(
            not isinstance(item, str) or len(item) != 64 for item in source_digests
        ):
            raise TopologyCatalogConsistencyError(
                "metadata must contain source_connectivity_state_digests."
            )
        if (
            self.catalog_options.mode == "catalog"
            and len(source_digests) != state_topology_ids.size
        ):
            raise TopologyCatalogConsistencyError(
                "Source state digests must align with state-to-topology IDs."
            )
        if np.any(state_ids >= len(source_digests)):
            raise TopologyCatalogConsistencyError(
                "Frame connectivity state IDs exceed source state digests."
            )
        representatives = metadata.get("topology_representative_connectivity_state_ids")
        if not isinstance(representatives, tuple) or len(representatives) != len(
            topologies
        ):
            raise TopologyCatalogConsistencyError(
                "metadata must record one representative state per topology."
            )
        for topology_id, state_id_raw in enumerate(representatives):
            state_id = _nonnegative_int(state_id_raw, name="representative state ID")
            if state_id >= len(source_digests):
                raise TopologyCatalogConsistencyError(
                    "Representative connectivity state ID is out of range."
                )
            if (
                topologies[topology_id].source_connectivity_digest
                != source_digests[state_id]
            ):
                raise TopologyCatalogConsistencyError(
                    "Topology source digest disagrees with representative state."
                )
            if (
                self.catalog_options.mode == "catalog"
                and int(state_topology_ids[state_id]) != topology_id
            ):
                raise TopologyCatalogConsistencyError(
                    "Representative state does not map to its topology class."
                )

        if self.canonical_schema_version != CANONICAL_TOPOLOGY_CATALOG_SCHEMA:
            raise TopologyCatalogConsistencyError(
                "Unsupported topology-catalog schema version."
            )
        if self.digest_algorithm != TOPOLOGY_CATALOG_DIGEST_ALGORITHM:
            raise TopologyCatalogConsistencyError(
                "Unsupported topology-catalog digest algorithm."
            )
        expected_digest = _catalog_digest(
            mapping=self.mapping,
            validation_rules=self.validation_rules,
            projection_options=self.projection_options,
            catalog_options=self.catalog_options,
            frame_semantics=semantics,
            consistency=consistency,
            frame_indices=frames,
            frame_ids=frame_ids,
            frame_connectivity_state_ids=state_ids,
            connectivity_state_topology_ids=state_topology_ids,
            frame_topology_ids=topology_ids,
            topologies=topologies,
            frame_groups=groups,
            segments=segments,
            transitions=transitions,
            source_connectivity_state_digests=source_digests,
        )
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise TopologyCatalogConsistencyError(
                "Stored topology-catalog digest is inconsistent."
            )

        object.__setattr__(self, "frame_semantics", semantics)
        object.__setattr__(self, "consistency", consistency)
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "frame_connectivity_state_ids", state_ids)
        object.__setattr__(self, "connectivity_state_topology_ids", state_topology_ids)
        object.__setattr__(self, "frame_topology_ids", topology_ids)
        object.__setattr__(self, "topologies", topologies)
        object.__setattr__(self, "frame_groups", groups)
        object.__setattr__(self, "segments", segments)
        object.__setattr__(self, "transitions", transitions)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "digest", digest)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TopologyCatalog):
            return NotImplemented
        return self.digest == other.digest and self.to_dict() == other.to_dict()

    def __hash__(self) -> int:
        return int(self.digest[:16], 16)

    @property
    def n_frames(self) -> int:
        return int(self.frame_indices.size)

    @property
    def n_topologies(self) -> int:
        return len(self.topologies)

    @property
    def topology_counts(self) -> IntArray:
        values = np.bincount(
            self.frame_topology_ids, minlength=self.n_topologies
        ).astype(np.int64)
        values.setflags(write=False)
        return values

    @property
    def topology_probabilities(self) -> FloatArray:
        values = self.topology_counts.astype(np.float64) / self.n_frames
        values.setflags(write=False)
        return values

    @property
    def is_uniform(self) -> bool:
        return self.consistency is TopologyConsistency.UNIFORM

    @property
    def is_partitioned(self) -> bool:
        return self.consistency is TopologyConsistency.PARTITIONED

    def topology_id_for_frame(self, frame_index: int) -> int:
        frame = _nonnegative_int(frame_index, name="frame_index")
        positions = np.flatnonzero(self.frame_indices == frame)
        if positions.size == 0:
            raise KeyError(f"Collection frame {frame} is not in this catalog.")
        return int(self.frame_topology_ids[int(positions[0])])

    def topology_for_frame(self, frame_index: int) -> FrameworkTopology:
        return self.topologies[self.topology_id_for_frame(frame_index)]

    def frames_for_topology(self, topology_id: int) -> IntArray:
        group = self.frame_groups[
            _validated_topology_id(topology_id, self.n_topologies)
        ]
        values = self.frame_indices[group.result_positions].copy()
        values.setflags(write=False)
        return values

    def result_positions_for_topology(self, topology_id: int) -> IntArray:
        group = self.frame_groups[
            _validated_topology_id(topology_id, self.n_topologies)
        ]
        values = group.result_positions.copy()
        values.setflags(write=False)
        return values

    def connectivity_states_for_topology(self, topology_id: int) -> Int32Array:
        topology_id = _validated_topology_id(topology_id, self.n_topologies)
        if self.catalog_options.mode == "catalog":
            values = np.flatnonzero(
                self.connectivity_state_topology_ids == topology_id
            ).astype(np.int32)
        else:
            positions = self.frame_groups[topology_id].result_positions
            values = np.unique(self.frame_connectivity_state_ids[positions]).astype(
                np.int32
            )
        values.setflags(write=False)
        return values

    def compare_topologies(
        self, topology_a: int, topology_b: int
    ) -> dict[str, tuple[FrameworkEdgeKey, ...]]:
        a = self.topologies[_validated_topology_id(topology_a, self.n_topologies)]
        b = self.topologies[_validated_topology_id(topology_b, self.n_topologies)]
        added, removed = _framework_edge_difference(a, b)
        return {"added_edges": added, "removed_edges": removed}

    def to_networkx(self, topology_id: int = 0) -> Any:
        return self.topologies[
            _validated_topology_id(topology_id, self.n_topologies)
        ].to_networkx()

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping": self.mapping.to_dict(),
            "validation_rules": None
            if self.validation_rules is None
            else self.validation_rules.to_dict(),
            "projection_options": _projection_options_to_dict(self.projection_options),
            "catalog_options": self.catalog_options.to_dict(),
            "frame_semantics": self.frame_semantics.value,
            "consistency": self.consistency.value,
            "frame_indices": self.frame_indices.tolist(),
            "frame_ids": self.frame_ids.tolist(),
            "frame_connectivity_state_ids": self.frame_connectivity_state_ids.tolist(),
            "connectivity_state_topology_ids": self.connectivity_state_topology_ids.tolist(),
            "frame_topology_ids": self.frame_topology_ids.tolist(),
            "topologies": [topology.to_dict() for topology in self.topologies],
            "frame_groups": [group.to_dict() for group in self.frame_groups],
            "segments": None
            if self.segments is None
            else [segment.to_dict() for segment in self.segments],
            "transitions": [transition.to_dict() for transition in self.transitions],
            "metadata": _json_safe(self.metadata),
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "digest": self.digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyCatalog":
        try:
            segments_payload = payload.get("segments")
            return cls(
                mapping=FrameworkMapping.from_dict(payload["mapping"]),
                validation_rules=(
                    None
                    if payload.get("validation_rules") is None
                    else FrameworkValidationRules.from_dict(payload["validation_rules"])
                ),
                projection_options=_projection_options_from_dict(
                    payload["projection_options"]
                ),
                catalog_options=TopologyCatalogOptions.from_dict(
                    payload["catalog_options"]
                ),
                frame_semantics=FrameSemantics(payload["frame_semantics"]),
                consistency=TopologyConsistency(payload["consistency"]),
                frame_indices=np.asarray(payload["frame_indices"], dtype=np.int64),
                frame_ids=np.asarray(payload["frame_ids"], dtype=np.int64),
                frame_connectivity_state_ids=np.asarray(
                    payload["frame_connectivity_state_ids"], dtype=np.int32
                ),
                connectivity_state_topology_ids=np.asarray(
                    payload["connectivity_state_topology_ids"], dtype=np.int32
                ),
                frame_topology_ids=np.asarray(
                    payload["frame_topology_ids"], dtype=np.int32
                ),
                topologies=tuple(
                    FrameworkTopology.from_dict(item) for item in payload["topologies"]
                ),
                frame_groups=tuple(
                    TopologyFrameGroup.from_dict(item)
                    for item in payload["frame_groups"]
                ),
                segments=(
                    None
                    if segments_payload is None
                    else tuple(
                        TopologySegment.from_dict(item) for item in segments_payload
                    )
                ),
                transitions=tuple(
                    TopologyTransition.from_dict(item)
                    for item in payload.get("transitions", ())
                ),
                metadata=dict(payload.get("metadata", {})),
                canonical_schema_version=str(payload["canonical_schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except TopologyCatalogSerializationError:
            raise
        except (TopologyCatalogError, KeyError, TypeError, ValueError) as exc:
            raise TopologyCatalogSerializationError(
                "Malformed or inconsistent serialized topology catalog."
            ) from exc


def build_topology_catalog(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    mapping: FrameworkMapping,
    *,
    validation_rules: FrameworkValidationRules | None = None,
    projection_options: FrameworkProjectionOptions | None = None,
    catalog_options: TopologyCatalogOptions | None = None,
) -> TopologyCatalog:
    """Classify exact projected framework topologies across selected frames."""
    _validate_build_inputs(collection, connectivity, mapping)
    if validation_rules is not None and not isinstance(
        validation_rules, FrameworkValidationRules
    ):
        raise TypeError("validation_rules must be FrameworkValidationRules or None.")
    projection = projection_options or FrameworkProjectionOptions()
    if not isinstance(projection, FrameworkProjectionOptions):
        raise TypeError(
            "projection_options must be FrameworkProjectionOptions or None."
        )
    options = catalog_options or TopologyCatalogOptions()
    if not isinstance(options, TopologyCatalogOptions):
        raise TypeError("catalog_options must be TopologyCatalogOptions or None.")

    state_order = _source_state_order(
        connectivity.frame_state_ids, connectivity.n_states
    )
    projected: dict[int, FrameworkTopology] = {}
    projection_summaries: list[dict[str, Any] | None] = [None] * connectivity.n_states
    for state_id in state_order:
        try:
            topology = build_framework_topology(
                connectivity.states[state_id],
                mapping,
                validation_rules=validation_rules,
                options=projection,
            )
        except FrameworkTopologyError as exc:
            raise TopologyCatalogProjectionError(
                f"Framework projection failed for connectivity state {state_id} "
                f"({connectivity.states[state_id].digest}): {exc}"
            ) from exc
        projected[state_id] = topology
        projection_summaries[state_id] = _projection_summary(topology)

    frames = np.asarray(connectivity.frame_indices, dtype=np.int64)
    frame_ids = np.asarray(connectivity.frame_ids, dtype=np.int64)
    frame_state_ids = np.asarray(connectivity.frame_state_ids, dtype=np.int32)

    if options.mode == "per_frame":
        topologies = tuple(projected[int(state_id)] for state_id in frame_state_ids)
        frame_topology_ids = np.arange(frames.size, dtype=np.int32)
        state_topology_ids = np.empty(0, dtype=np.int32)
        frame_groups = tuple(
            TopologyFrameGroup(
                topology_id=position,
                result_positions=np.asarray([position], dtype=np.int64),
            )
            for position in range(frames.size)
        )
        consistency = TopologyConsistency.PER_FRAME
        segments = None
        transitions: tuple[TopologyTransition, ...] = ()
        representative_state_ids = tuple(int(x) for x in frame_state_ids)
    else:
        topologies_list: list[FrameworkTopology] = []
        structural_keys: list[tuple[Any, ...]] = []
        digest_buckets: dict[str, list[int]] = {}
        state_topology_ids = np.full(connectivity.n_states, -1, dtype=np.int32)
        representative_state_ids_list: list[int] = []
        for state_id in state_order:
            candidate = projected[state_id]
            candidate_key = _framework_structural_key(candidate)
            match: int | None = None
            for topology_id in digest_buckets.get(
                _topology_bucket_digest(candidate), ()
            ):
                if structural_keys[topology_id] == candidate_key:
                    match = topology_id
                    break
            if match is None:
                match = len(topologies_list)
                topologies_list.append(candidate)
                structural_keys.append(candidate_key)
                representative_state_ids_list.append(state_id)
                digest_buckets.setdefault(
                    _topology_bucket_digest(candidate), []
                ).append(match)
            state_topology_ids[state_id] = match
        topologies = tuple(topologies_list)
        if np.any(state_topology_ids < 0):
            raise TopologyCatalogConsistencyError(
                "Not every source connectivity state was assigned a topology."
            )
        frame_topology_ids = state_topology_ids[frame_state_ids]
        consistency = (
            TopologyConsistency.UNIFORM
            if len(topologies) == 1
            else TopologyConsistency.PARTITIONED
        )
        frame_groups = _build_frame_groups(frame_topology_ids, len(topologies))
        if collection.is_trajectory:
            segments = _build_segments(
                frame_topology_ids, options.minimum_persistent_frames
            )
            transitions = _build_transitions(
                connectivity,
                topologies,
                segments,
                frame_topology_ids,
                options,
            )
        else:
            segments = None
            transitions = ()
        representative_state_ids = tuple(representative_state_ids_list)

    metadata = {
        "module": "topology_catalog",
        "algorithm": "exact_projected_topology_catalog",
        "frame_semantics": collection.frame_semantics.value,
        "source_connectivity_state_count": connectivity.n_states,
        "source_connectivity_state_digests": tuple(
            state.digest for state in connectivity.states
        ),
        "topology_representative_connectivity_state_ids": representative_state_ids,
        "projection_count": len(projected),
        "stored_topology_count": len(topologies),
        "compression_ratio_frames_to_topologies": float(frames.size / len(topologies)),
        "compression_ratio_states_to_topologies": float(
            connectivity.n_states / len(topologies)
        ),
        "transition_count": len(transitions),
        "transient_segment_count": 0
        if segments is None
        else sum(
            segment.status is TopologySegmentStatus.TRANSIENT for segment in segments
        ),
        "source_connectivity_definition_kind": connectivity.definition.kind,
        "source_connectivity_metadata": _json_safe(connectivity.metadata),
        "projection_validation_summaries_by_state": tuple(projection_summaries),
        "framework_topology_schema": CANONICAL_FRAMEWORK_TOPOLOGY_SCHEMA,
        "canonical_schema_version": CANONICAL_TOPOLOGY_CATALOG_SCHEMA,
        "digest_algorithm": TOPOLOGY_CATALOG_DIGEST_ALGORITHM,
    }
    return TopologyCatalog(
        mapping=mapping,
        validation_rules=validation_rules,
        projection_options=projection,
        catalog_options=options,
        frame_semantics=collection.frame_semantics,
        consistency=consistency,
        frame_indices=frames,
        frame_ids=frame_ids,
        frame_connectivity_state_ids=frame_state_ids,
        connectivity_state_topology_ids=state_topology_ids,
        frame_topology_ids=frame_topology_ids,
        topologies=topologies,
        frame_groups=frame_groups,
        segments=segments,
        transitions=transitions,
        metadata=metadata,
    )


def _validate_build_inputs(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    mapping: FrameworkMapping,
) -> None:
    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise TypeError("connectivity must be an AtomicConnectivityResult.")
    if not isinstance(mapping, FrameworkMapping):
        raise TypeError("mapping must be a FrameworkMapping.")
    frames = np.asarray(connectivity.frame_indices, dtype=np.int64)
    if np.any(frames < 0) or np.any(frames >= collection.n_frames):
        raise TopologyCatalogInputError(
            "Connectivity frame indices are outside the source collection."
        )
    if len(set(int(x) for x in frames)) != frames.size:
        raise TopologyCatalogInputError("Connectivity frame indices must be unique.")
    if collection.is_trajectory and np.any(np.diff(frames) <= 0):
        raise TopologyCatalogInputError(
            "Trajectory frame indices must be strictly increasing."
        )
    expected_frame_ids = np.asarray(collection.frame_ids, dtype=np.int64)[frames]
    if not np.array_equal(connectivity.frame_ids, expected_frame_ids):
        raise TopologyCatalogInputError(
            "Connectivity frame IDs do not match the source collection."
        )
    source_semantics = connectivity.metadata.get("frame_semantics")
    if (
        source_semantics is not None
        and source_semantics != collection.frame_semantics.value
    ):
        raise TopologyCatalogInputError(
            "Connectivity and collection frame semantics disagree."
        )
    used_states = set(int(x) for x in connectivity.frame_state_ids)
    if used_states != set(range(connectivity.n_states)):
        raise TopologyCatalogInputError(
            "Every source connectivity state must occur in at least one selected frame."
        )
    reference = connectivity.states[0]
    for state_id, state in enumerate(connectivity.states):
        if not np.array_equal(
            state.active_atom_indices, reference.active_atom_indices
        ) or not np.array_equal(
            state.active_atomic_numbers, reference.active_atomic_numbers
        ):
            raise TopologyCatalogInputError(
                "All connectivity states must use one fixed active atom identity."
            )
        if not np.array_equal(state.pbc, reference.pbc):
            raise TopologyCatalogInputError(
                "All connectivity states must use identical PBC flags."
            )
        if not np.array_equal(
            collection.atomic_numbers[state.active_atom_indices],
            state.active_atomic_numbers,
        ):
            raise TopologyCatalogInputError(
                f"Connectivity state {state_id} atom identities disagree with the collection."
            )
        if not np.array_equal(collection.pbc, state.pbc):
            raise TopologyCatalogInputError(
                f"Connectivity state {state_id} PBC flags disagree with the collection."
            )
    if any(index >= collection.n_atoms for index in mapping.atom_role_overrides):
        raise TopologyCatalogInputError(
            "Framework mapping contains an out-of-range atom-role override."
        )


def _source_state_order(frame_state_ids: Int32Array, n_states: int) -> tuple[int, ...]:
    first_occurrence: dict[int, int] = {}
    for position, state_id_raw in enumerate(frame_state_ids):
        state_id = int(state_id_raw)
        first_occurrence.setdefault(state_id, position)
    return tuple(sorted(range(n_states), key=lambda x: first_occurrence[x]))


def _topology_bucket_digest(topology: FrameworkTopology) -> str:
    """Return the nonauthoritative digest used only to narrow exact comparisons."""
    return topology.digest


def _framework_structural_key(topology: FrameworkTopology) -> tuple[Any, ...]:
    """Return the exact mapping-aware Stage 2 structural identity key."""
    return (
        topology.canonical_schema_version,
        topology.mapping_digest,
        tuple(bool(x) for x in topology.pbc),
        tuple(int(x) for x in topology.vertex_atom_indices),
        tuple(int(x) for x in topology.vertex_atomic_numbers),
        topology.edge_keys,
    )


def _projection_summary(topology: FrameworkTopology) -> dict[str, Any]:
    return {
        "source_connectivity_digest": topology.source_connectivity_digest,
        "topology_digest": topology.digest,
        "graph_digest": topology.graph_digest,
        "n_vertices": topology.n_vertices,
        "n_edges": topology.n_edges,
        "n_components": topology.n_components,
        "projection_report": topology.projection_report.to_dict(),
        "validation": None
        if topology.validation is None
        else topology.validation.to_dict(),
    }


def _build_frame_groups(
    topology_ids: Int32Array, n_topologies: int
) -> tuple[TopologyFrameGroup, ...]:
    return tuple(
        TopologyFrameGroup(
            topology_id=topology_id,
            result_positions=np.flatnonzero(topology_ids == topology_id).astype(
                np.int64
            ),
        )
        for topology_id in range(n_topologies)
    )


def _build_segments(
    topology_ids: Int32Array, minimum_persistent_frames: int
) -> tuple[TopologySegment, ...]:
    segments: list[TopologySegment] = []
    start = 0
    for stop in range(1, topology_ids.size + 1):
        if stop == topology_ids.size or topology_ids[stop] != topology_ids[start]:
            length = stop - start
            status = (
                TopologySegmentStatus.CONFIRMED
                if length >= minimum_persistent_frames
                else TopologySegmentStatus.TRANSIENT
            )
            segments.append(
                TopologySegment(
                    segment_id=len(segments),
                    topology_id=int(topology_ids[start]),
                    result_position_start=start,
                    result_position_stop=stop,
                    status=status,
                )
            )
            start = stop
    return tuple(segments)


def _build_transitions(
    connectivity: AtomicConnectivityResult,
    topologies: tuple[FrameworkTopology, ...],
    segments: tuple[TopologySegment, ...],
    frame_topology_ids: Int32Array,
    options: TopologyCatalogOptions,
) -> tuple[TopologyTransition, ...]:
    transitions: list[TopologyTransition] = []
    for source_segment, target_segment in zip(segments, segments[1:]):
        before = source_segment.result_position_stop - 1
        after = target_segment.result_position_start
        if after != before + 1:
            raise TopologyCatalogConsistencyError(
                "Adjacent topology segments do not share one boundary."
            )
        source_topology_id = int(frame_topology_ids[before])
        target_topology_id = int(frame_topology_ids[after])
        source_state_id = int(connectivity.frame_state_ids[before])
        target_state_id = int(connectivity.frame_state_ids[after])
        added_atomic, removed_atomic = _atomic_edge_difference(
            connectivity.states[source_state_id], connectivity.states[target_state_id]
        )
        added_framework, removed_framework = _framework_edge_difference(
            topologies[source_topology_id], topologies[target_topology_id]
        )
        if not added_framework and not removed_framework:
            raise TopologyCatalogConsistencyError(
                "A topology-changing boundary has no framework-edge difference."
            )
        affected_atomic = {
            atom
            for edge in (*added_atomic, *removed_atomic)
            for atom in (edge.atom_i, edge.atom_j)
        }
        affected_vertices = {
            atom
            for edge in (*added_framework, *removed_framework)
            for atom in (edge.vertex_i, edge.vertex_j)
        }
        affected_linkers = {
            atom
            for edge in (*added_framework, *removed_framework)
            for atom in edge.internal_linker_indices
        }
        affected_atoms = affected_atomic | affected_vertices | affected_linkers
        transitions.append(
            TopologyTransition(
                transition_id=len(transitions),
                source_segment_id=source_segment.segment_id,
                target_segment_id=target_segment.segment_id,
                source_topology_id=source_topology_id,
                target_topology_id=target_topology_id,
                source_connectivity_state_id=source_state_id,
                target_connectivity_state_id=target_state_id,
                result_position_before=before,
                result_position_after=after,
                collection_frame_index_before=int(connectivity.frame_indices[before]),
                collection_frame_index_after=int(connectivity.frame_indices[after]),
                frame_id_before=int(connectivity.frame_ids[before]),
                frame_id_after=int(connectivity.frame_ids[after]),
                added_atomic_edges=added_atomic
                if options.include_atomic_edge_differences
                else (),
                removed_atomic_edges=removed_atomic
                if options.include_atomic_edge_differences
                else (),
                added_framework_edges=added_framework
                if options.include_framework_edge_differences
                else (),
                removed_framework_edges=removed_framework
                if options.include_framework_edge_differences
                else (),
                affected_atom_indices=tuple(affected_atoms),
                affected_vertex_atom_indices=tuple(affected_vertices),
                affected_linker_atom_indices=tuple(affected_linkers),
            )
        )
    return tuple(transitions)


def _atomic_edge_difference(
    source: AtomicConnectivityState, target: AtomicConnectivityState
) -> tuple[tuple[AtomicEdgeKey, ...], tuple[AtomicEdgeKey, ...]]:
    source_edges = set(source.edge_keys)
    target_edges = set(target.edge_keys)
    return tuple(sorted(target_edges - source_edges)), tuple(
        sorted(source_edges - target_edges)
    )


def _framework_edge_difference(
    source: FrameworkTopology, target: FrameworkTopology
) -> tuple[tuple[FrameworkEdgeKey, ...], tuple[FrameworkEdgeKey, ...]]:
    source_edges = set(source.edge_keys)
    target_edges = set(target.edge_keys)
    return tuple(sorted(target_edges - source_edges)), tuple(
        sorted(source_edges - target_edges)
    )


def _validate_segments(
    segments: tuple[TopologySegment, ...],
    topology_ids: Int32Array,
    minimum_persistent_frames: int,
) -> None:
    if not segments:
        raise TopologyCatalogConsistencyError(
            "Trajectory catalog requires at least one topology segment."
        )
    cursor = 0
    for segment_id, segment in enumerate(segments):
        if segment.segment_id != segment_id:
            raise TopologyCatalogConsistencyError("Topology segment IDs must be dense.")
        if segment.result_position_start != cursor:
            raise TopologyCatalogConsistencyError(
                "Topology segments must cover result positions contiguously."
            )
        if np.any(
            topology_ids[segment.result_position_start : segment.result_position_stop]
            != segment.topology_id
        ):
            raise TopologyCatalogConsistencyError(
                "Topology segment membership disagrees with frame assignments."
            )
        expected_status = (
            TopologySegmentStatus.CONFIRMED
            if segment.length >= minimum_persistent_frames
            else TopologySegmentStatus.TRANSIENT
        )
        if segment.status is not expected_status:
            raise TopologyCatalogConsistencyError(
                "Topology segment status disagrees with persistence threshold."
            )
        if segment_id and segments[segment_id - 1].topology_id == segment.topology_id:
            raise TopologyCatalogConsistencyError(
                "Adjacent topology segments must have different topology IDs."
            )
        cursor = segment.result_position_stop
    if cursor != topology_ids.size:
        raise TopologyCatalogConsistencyError(
            "Topology segments do not cover every selected result position."
        )


def _validate_transitions(
    transitions: tuple[TopologyTransition, ...],
    segments: tuple[TopologySegment, ...],
    frame_indices: IntArray,
    frame_ids: IntArray,
    state_ids: Int32Array,
    topologies: tuple[FrameworkTopology, ...],
    options: TopologyCatalogOptions,
) -> None:
    if len(transitions) != max(0, len(segments) - 1):
        raise TopologyCatalogConsistencyError(
            "Transition count must equal the number of segment boundaries."
        )
    for transition_id, transition in enumerate(transitions):
        if transition.transition_id != transition_id:
            raise TopologyCatalogConsistencyError(
                "Topology transition IDs must be dense."
            )
        source = segments[transition.source_segment_id]
        target = segments[transition.target_segment_id]
        before = source.result_position_stop - 1
        after = target.result_position_start
        if (
            transition.result_position_before != before
            or transition.result_position_after != after
            or transition.source_topology_id != source.topology_id
            or transition.target_topology_id != target.topology_id
            or transition.source_connectivity_state_id != int(state_ids[before])
            or transition.target_connectivity_state_id != int(state_ids[after])
            or transition.collection_frame_index_before != int(frame_indices[before])
            or transition.collection_frame_index_after != int(frame_indices[after])
            or transition.frame_id_before != int(frame_ids[before])
            or transition.frame_id_after != int(frame_ids[after])
        ):
            raise TopologyCatalogConsistencyError(
                "Transition boundary metadata disagree with segments and frames."
            )
        added, removed = _framework_edge_difference(
            topologies[source.topology_id], topologies[target.topology_id]
        )
        if not added and not removed:
            raise TopologyCatalogConsistencyError(
                "Topology transition lacks a structural framework difference."
            )
        if options.include_framework_edge_differences:
            if (
                transition.added_framework_edges != added
                or transition.removed_framework_edges != removed
            ):
                raise TopologyCatalogConsistencyError(
                    "Stored framework differences disagree with topology classes."
                )
        elif transition.added_framework_edges or transition.removed_framework_edges:
            raise TopologyCatalogConsistencyError(
                "Framework differences must be omitted when disabled."
            )
        expected_vertices = tuple(
            sorted(
                {
                    atom
                    for edge in (*added, *removed)
                    for atom in (edge.vertex_i, edge.vertex_j)
                }
            )
        )
        expected_linkers = tuple(
            sorted(
                {
                    atom
                    for edge in (*added, *removed)
                    for atom in edge.internal_linker_indices
                }
            )
        )
        if transition.affected_vertex_atom_indices != expected_vertices:
            raise TopologyCatalogConsistencyError(
                "Affected vertices disagree with framework-edge differences."
            )
        if transition.affected_linker_atom_indices != expected_linkers:
            raise TopologyCatalogConsistencyError(
                "Affected linkers disagree with framework-edge differences."
            )
        if not set(expected_vertices + expected_linkers).issubset(
            transition.affected_atom_indices
        ):
            raise TopologyCatalogConsistencyError(
                "Affected atom set omits changed framework-path atoms."
            )
        if options.include_atomic_edge_differences:
            expected_atomic_atoms = {
                atom
                for edge in (
                    *transition.added_atomic_edges,
                    *transition.removed_atomic_edges,
                )
                for atom in (edge.atom_i, edge.atom_j)
            }
            expected_affected = tuple(
                sorted(
                    expected_atomic_atoms
                    | set(expected_vertices)
                    | set(expected_linkers)
                )
            )
            if transition.affected_atom_indices != expected_affected:
                raise TopologyCatalogConsistencyError(
                    "Affected atoms disagree with stored edge differences."
                )
        elif transition.added_atomic_edges or transition.removed_atomic_edges:
            raise TopologyCatalogConsistencyError(
                "Atomic differences must be omitted when disabled."
            )


def _catalog_digest(
    *,
    mapping: FrameworkMapping,
    validation_rules: FrameworkValidationRules | None,
    projection_options: FrameworkProjectionOptions,
    catalog_options: TopologyCatalogOptions,
    frame_semantics: FrameSemantics,
    consistency: TopologyConsistency,
    frame_indices: IntArray,
    frame_ids: IntArray,
    frame_connectivity_state_ids: Int32Array,
    connectivity_state_topology_ids: Int32Array,
    frame_topology_ids: Int32Array,
    topologies: tuple[FrameworkTopology, ...],
    frame_groups: tuple[TopologyFrameGroup, ...],
    segments: tuple[TopologySegment, ...] | None,
    transitions: tuple[TopologyTransition, ...],
    source_connectivity_state_digests: Sequence[str],
) -> str:
    payload = {
        "canonical_schema_version": CANONICAL_TOPOLOGY_CATALOG_SCHEMA,
        "mapping_digest": mapping.digest,
        "validation_rules": None
        if validation_rules is None
        else validation_rules.to_dict(),
        "projection_options": _projection_options_to_dict(projection_options),
        "catalog_options": catalog_options.to_dict(),
        "frame_semantics": frame_semantics.value,
        "consistency": consistency.value,
        "frame_indices": frame_indices.tolist(),
        "frame_ids": frame_ids.tolist(),
        "frame_connectivity_state_ids": frame_connectivity_state_ids.tolist(),
        "connectivity_state_topology_ids": connectivity_state_topology_ids.tolist(),
        "frame_topology_ids": frame_topology_ids.tolist(),
        "source_connectivity_state_digests": list(source_connectivity_state_digests),
        "topology_digests": [topology.digest for topology in topologies],
        "frame_groups": [group.to_dict() for group in frame_groups],
        "segments": None
        if segments is None
        else [segment.to_dict() for segment in segments],
        "transitions": [transition.to_dict() for transition in transitions],
    }
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _projection_options_to_dict(
    options: FrameworkProjectionOptions,
) -> dict[str, int]:
    return {
        "max_linker_atoms": options.max_linker_atoms,
        "max_candidate_paths": options.max_candidate_paths,
        "max_projected_edges": options.max_projected_edges,
    }


def _projection_options_from_dict(
    payload: Mapping[str, Any],
) -> FrameworkProjectionOptions:
    return FrameworkProjectionOptions(
        max_linker_atoms=int(payload["max_linker_atoms"]),
        max_candidate_paths=int(payload["max_candidate_paths"]),
        max_projected_edges=int(payload["max_projected_edges"]),
    )


def _validated_topology_id(value: int, n_topologies: int) -> int:
    topology_id = _nonnegative_int(value, name="topology_id")
    if topology_id >= n_topologies:
        raise IndexError(f"Topology ID {topology_id} is out of range.")
    return topology_id


def _canonical_object_tuple(
    values: Sequence[Any], expected_type: type
) -> tuple[Any, ...]:
    items = tuple(values)
    if any(not isinstance(item, expected_type) for item in items):
        raise TopologyCatalogConsistencyError(
            f"Expected only {expected_type.__name__} objects."
        )
    return tuple(sorted(set(items)))


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TopologyCatalogConsistencyError(f"{name} must be an integer.")
    integer = int(value)
    if integer < 0:
        raise TopologyCatalogConsistencyError(f"{name} must be nonnegative.")
    return integer


def _readonly_array(value: ArrayLike, dtype: Any, *, ndim: int) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True)
    if array.ndim != ndim:
        raise TopologyCatalogConsistencyError(
            f"Expected a {ndim}-dimensional array; received shape {array.shape}."
        )
    array.setflags(write=False)
    return array


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _deep_freeze(item) for key, item in value.items()}


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _deep_freeze(item) for key, item in value.items()}
        )
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    if isinstance(value, list):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(item) for item in value)
    if isinstance(value, set | frozenset):
        return frozenset(_deep_freeze(item) for item in value)
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, frozenset | set):
        return sorted(_json_safe(item) for item in value)
    return value


__all__ = [
    "CANONICAL_TOPOLOGY_CATALOG_SCHEMA",
    "TOPOLOGY_CATALOG_DIGEST_ALGORITHM",
    "TopologyConsistency",
    "TopologySegmentStatus",
    "TopologyCatalogOptions",
    "TopologyFrameGroup",
    "TopologySegment",
    "TopologyTransition",
    "TopologyCatalog",
    "TopologyCatalogError",
    "TopologyCatalogInputError",
    "TopologyCatalogProjectionError",
    "TopologyCatalogConsistencyError",
    "TopologyCatalogSerializationError",
    "build_topology_catalog",
]
