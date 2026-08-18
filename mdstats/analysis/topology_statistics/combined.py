"""Combined atomic/framework topology statistics.

This module is the TS4 layer of the topology-statistics architecture. It aligns
one authoritative :class:`AtomicConnectivityResult` with the
:class:`TopologyCatalog` projected from the same selected frames, invokes the
already implemented atomic and framework statistics branches, and derives only
cross-layer summaries.

The module never rebuilds connectivity, reprojects framework paths, reconciles
new topology classes, or infers chemical mechanisms. Its central products are
an exact atomic-state/framework-class contingency table and, for reconciled
trajectories, an exact classification of every adjacent frame boundary.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ...semantics import FrameSemantics
from ..atomic_connectivity import (
    AtomicConnectivityResult,
    ConnectivityConsistency,
)
from ..topology_catalog import TopologyCatalog
from ._common import (
    TOPOLOGY_STATISTICS_DIGEST_ALGORITHM,
    FrameAxis,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    TopologyStatisticsSerializationError,
    canonical_statistics_json,
)
from .atomic import (
    AtomicConnectivityStatistics,
    AtomicStatisticsOptions,
    compute_atomic_connectivity_statistics,
)
from .framework import (
    FrameworkStatisticsOptions,
    FrameworkTopologyStatistics,
    compute_framework_topology_statistics,
)

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]

CANONICAL_COMBINED_TOPOLOGY_STATISTICS_SCHEMA = (
    "mdstats.topology-statistics.combined.v1"
)


class CrossLayerBoundaryKind(str, Enum):
    """Classification of one adjacent trajectory-frame boundary."""

    STABLE = "stable"
    ATOMIC_ONLY = "atomic_only"
    FRAMEWORK_ONLY = "framework_only"
    COUPLED = "coupled"


class CrossLayerCatalogRegime(str, Enum):
    """Compact descriptive relation between atomic and framework variability."""

    UNIFORM = "uniform_atomic_and_framework"
    ATOMIC_VARIABLE_FRAMEWORK_UNIFORM = "atomic_variable_framework_uniform"
    FRAMEWORK_VARIABLE = "framework_variable"


_BOUNDARY_KIND_ORDER = (
    CrossLayerBoundaryKind.STABLE,
    CrossLayerBoundaryKind.ATOMIC_ONLY,
    CrossLayerBoundaryKind.FRAMEWORK_ONLY,
    CrossLayerBoundaryKind.COUPLED,
)
_BOUNDARY_KIND_TO_CODE = {
    kind: index for index, kind in enumerate(_BOUNDARY_KIND_ORDER)
}


@dataclass(frozen=True, slots=True)
class CombinedStatisticsOptions:
    """Controls atomic, framework, and cross-layer TS4 calculations."""

    atomic_options: AtomicStatisticsOptions = field(
        default_factory=AtomicStatisticsOptions
    )
    framework_options: FrameworkStatisticsOptions = field(
        default_factory=FrameworkStatisticsOptions
    )
    include_boundary_statistics: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.atomic_options, AtomicStatisticsOptions):
            raise TopologyStatisticsInputError(
                "atomic_options must be AtomicStatisticsOptions."
            )
        if not isinstance(self.framework_options, FrameworkStatisticsOptions):
            raise TopologyStatisticsInputError(
                "framework_options must be FrameworkStatisticsOptions."
            )
        if not isinstance(self.include_boundary_statistics, (bool, np.bool_)):
            raise TopologyStatisticsInputError(
                "include_boundary_statistics must be boolean."
            )
        object.__setattr__(
            self, "include_boundary_statistics", bool(self.include_boundary_statistics)
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "atomic_options": self.atomic_options.to_dict(),
            "framework_options": self.framework_options.to_dict(),
            "include_boundary_statistics": self.include_boundary_statistics,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CombinedStatisticsOptions":
        return cls(
            atomic_options=AtomicStatisticsOptions.from_dict(
                _mapping(payload.get("atomic_options", {}), name="atomic_options")
            ),
            framework_options=FrameworkStatisticsOptions.from_dict(
                _mapping(payload.get("framework_options", {}), name="framework_options")
            ),
            include_boundary_statistics=payload.get(
                "include_boundary_statistics", True
            ),
        )


@dataclass(frozen=True, slots=True)
class AtomicStateProjectionStatistics:
    """Framework classes observed among frames assigned to one atomic state."""

    atomic_state_id: int
    framework_class_ids: IntArray
    frame_counts: IntArray
    conditional_probabilities: FloatArray
    dominant_framework_class_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        state_id = _nonnegative_int(self.atomic_state_id, "atomic_state_id")
        class_ids = _readonly_int_array(self.framework_class_ids, ndim=1)
        counts = _readonly_int_array(self.frame_counts, ndim=1)
        probabilities = _readonly_float_array(self.conditional_probabilities, ndim=1)
        if (
            class_ids.size == 0
            or counts.shape != class_ids.shape
            or probabilities.shape != class_ids.shape
        ):
            raise TopologyStatisticsConsistencyError(
                "Atomic-state projection arrays must be aligned and nonempty."
            )
        if np.any(np.diff(class_ids) <= 0) or np.any(counts <= 0):
            raise TopologyStatisticsConsistencyError(
                "Framework class IDs must be sorted and frame counts positive."
            )
        if not np.isclose(float(probabilities.sum()), 1.0, atol=1e-15, rtol=0.0):
            raise TopologyStatisticsConsistencyError(
                "Conditional framework probabilities must sum to one."
            )
        expected = counts.astype(float) / int(counts.sum())
        if not np.allclose(probabilities, expected, atol=1e-15, rtol=0.0):
            raise TopologyStatisticsConsistencyError(
                "Conditional framework probabilities disagree with frame counts."
            )
        dominant = tuple(
            _nonnegative_int(x, "dominant framework class ID")
            for x in self.dominant_framework_class_ids
        )
        expected_dominant = tuple(
            int(class_ids[index]) for index in np.flatnonzero(counts == counts.max())
        )
        if dominant != expected_dominant:
            raise TopologyStatisticsConsistencyError(
                "Dominant framework class IDs disagree with frame counts."
            )
        object.__setattr__(self, "atomic_state_id", state_id)
        object.__setattr__(self, "framework_class_ids", class_ids)
        object.__setattr__(self, "frame_counts", counts)
        object.__setattr__(self, "conditional_probabilities", probabilities)
        object.__setattr__(self, "dominant_framework_class_ids", dominant)

    @property
    def n_framework_classes(self) -> int:
        return int(self.framework_class_ids.size)

    @property
    def is_deterministic(self) -> bool:
        return self.n_framework_classes == 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "atomic_state_id": self.atomic_state_id,
            "framework_class_ids": self.framework_class_ids.tolist(),
            "frame_counts": self.frame_counts.tolist(),
            "conditional_probabilities": self.conditional_probabilities.tolist(),
            "dominant_framework_class_ids": list(self.dominant_framework_class_ids),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AtomicStateProjectionStatistics":
        return cls(
            atomic_state_id=int(payload["atomic_state_id"]),
            framework_class_ids=np.asarray(
                payload["framework_class_ids"], dtype=np.int64
            ),
            frame_counts=np.asarray(payload["frame_counts"], dtype=np.int64),
            conditional_probabilities=np.asarray(
                payload["conditional_probabilities"], dtype=np.float64
            ),
            dominant_framework_class_ids=tuple(
                int(x) for x in payload["dominant_framework_class_ids"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameworkClassCompositionStatistics:
    """Atomic states represented among frames assigned to one framework class."""

    framework_class_id: int
    atomic_state_ids: IntArray
    frame_counts: IntArray
    conditional_probabilities: FloatArray
    dominant_atomic_state_ids: tuple[int, ...]

    def __post_init__(self) -> None:
        class_id = _nonnegative_int(self.framework_class_id, "framework_class_id")
        state_ids = _readonly_int_array(self.atomic_state_ids, ndim=1)
        counts = _readonly_int_array(self.frame_counts, ndim=1)
        probabilities = _readonly_float_array(self.conditional_probabilities, ndim=1)
        if (
            state_ids.size == 0
            or counts.shape != state_ids.shape
            or probabilities.shape != state_ids.shape
        ):
            raise TopologyStatisticsConsistencyError(
                "Framework-class composition arrays must be aligned and nonempty."
            )
        if np.any(np.diff(state_ids) <= 0) or np.any(counts <= 0):
            raise TopologyStatisticsConsistencyError(
                "Atomic state IDs must be sorted and frame counts positive."
            )
        if not np.isclose(float(probabilities.sum()), 1.0, atol=1e-15, rtol=0.0):
            raise TopologyStatisticsConsistencyError(
                "Conditional atomic probabilities must sum to one."
            )
        expected = counts.astype(float) / int(counts.sum())
        if not np.allclose(probabilities, expected, atol=1e-15, rtol=0.0):
            raise TopologyStatisticsConsistencyError(
                "Conditional atomic probabilities disagree with frame counts."
            )
        dominant = tuple(
            _nonnegative_int(x, "dominant atomic state ID")
            for x in self.dominant_atomic_state_ids
        )
        expected_dominant = tuple(
            int(state_ids[index]) for index in np.flatnonzero(counts == counts.max())
        )
        if dominant != expected_dominant:
            raise TopologyStatisticsConsistencyError(
                "Dominant atomic state IDs disagree with frame counts."
            )
        object.__setattr__(self, "framework_class_id", class_id)
        object.__setattr__(self, "atomic_state_ids", state_ids)
        object.__setattr__(self, "frame_counts", counts)
        object.__setattr__(self, "conditional_probabilities", probabilities)
        object.__setattr__(self, "dominant_atomic_state_ids", dominant)

    @property
    def n_atomic_states(self) -> int:
        return int(self.atomic_state_ids.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_class_id": self.framework_class_id,
            "atomic_state_ids": self.atomic_state_ids.tolist(),
            "frame_counts": self.frame_counts.tolist(),
            "conditional_probabilities": self.conditional_probabilities.tolist(),
            "dominant_atomic_state_ids": list(self.dominant_atomic_state_ids),
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "FrameworkClassCompositionStatistics":
        return cls(
            framework_class_id=int(payload["framework_class_id"]),
            atomic_state_ids=np.asarray(payload["atomic_state_ids"], dtype=np.int64),
            frame_counts=np.asarray(payload["frame_counts"], dtype=np.int64),
            conditional_probabilities=np.asarray(
                payload["conditional_probabilities"], dtype=np.float64
            ),
            dominant_atomic_state_ids=tuple(
                int(x) for x in payload["dominant_atomic_state_ids"]
            ),
        )


@dataclass(frozen=True, slots=True)
class CrossLayerContingencyStatistics:
    """Exact frame contingency between atomic states and framework classes."""

    frame_count_matrix: IntArray
    probability_matrix: FloatArray
    atomic_state_projections: tuple[AtomicStateProjectionStatistics, ...]
    framework_class_compositions: tuple[FrameworkClassCompositionStatistics, ...]

    def __post_init__(self) -> None:
        counts = _readonly_int_array(self.frame_count_matrix, ndim=2)
        probabilities = _readonly_float_array(self.probability_matrix, ndim=2)
        if (
            counts.size == 0
            or probabilities.shape != counts.shape
            or np.any(counts < 0)
        ):
            raise TopologyStatisticsConsistencyError(
                "Contingency matrices must be aligned, nonempty, and nonnegative."
            )
        total = int(counts.sum())
        if total <= 0:
            raise TopologyStatisticsConsistencyError(
                "The contingency matrix must contain at least one frame."
            )
        expected_probabilities = counts.astype(float) / total
        if not np.allclose(probabilities, expected_probabilities, atol=1e-15, rtol=0.0):
            raise TopologyStatisticsConsistencyError(
                "Contingency probabilities disagree with frame counts."
            )
        atomic_rows = tuple(self.atomic_state_projections)
        framework_columns = tuple(self.framework_class_compositions)
        if (
            len(atomic_rows) != counts.shape[0]
            or len(framework_columns) != counts.shape[1]
        ):
            raise TopologyStatisticsConsistencyError(
                "Contingency summaries must match matrix dimensions."
            )
        if tuple(x.atomic_state_id for x in atomic_rows) != tuple(
            range(counts.shape[0])
        ):
            raise TopologyStatisticsConsistencyError(
                "Atomic-state projection summaries must use dense sorted IDs."
            )
        if tuple(x.framework_class_id for x in framework_columns) != tuple(
            range(counts.shape[1])
        ):
            raise TopologyStatisticsConsistencyError(
                "Framework-class composition summaries must use dense sorted IDs."
            )
        for state_id, item in enumerate(atomic_rows):
            nonzero = np.flatnonzero(counts[state_id] > 0)
            if not np.array_equal(item.framework_class_ids, nonzero):
                raise TopologyStatisticsConsistencyError(
                    "Atomic-state projection IDs disagree with the contingency matrix."
                )
            if not np.array_equal(item.frame_counts, counts[state_id, nonzero]):
                raise TopologyStatisticsConsistencyError(
                    "Atomic-state projection counts disagree with the contingency matrix."
                )
        for class_id, item in enumerate(framework_columns):
            nonzero = np.flatnonzero(counts[:, class_id] > 0)
            if not np.array_equal(item.atomic_state_ids, nonzero):
                raise TopologyStatisticsConsistencyError(
                    "Framework-class composition IDs disagree with the contingency matrix."
                )
            if not np.array_equal(item.frame_counts, counts[nonzero, class_id]):
                raise TopologyStatisticsConsistencyError(
                    "Framework-class composition counts disagree with the contingency matrix."
                )
        object.__setattr__(self, "frame_count_matrix", counts)
        object.__setattr__(self, "probability_matrix", probabilities)
        object.__setattr__(self, "atomic_state_projections", atomic_rows)
        object.__setattr__(self, "framework_class_compositions", framework_columns)

    @property
    def n_frames(self) -> int:
        return int(self.frame_count_matrix.sum())

    @property
    def n_atomic_states(self) -> int:
        return int(self.frame_count_matrix.shape[0])

    @property
    def n_framework_classes(self) -> int:
        return int(self.frame_count_matrix.shape[1])

    @property
    def atomic_to_framework_compression_ratio(self) -> float:
        return self.n_atomic_states / self.n_framework_classes

    @property
    def atomic_states_per_framework_class(self) -> IntArray:
        values = np.count_nonzero(self.frame_count_matrix, axis=0).astype(np.int64)
        values.setflags(write=False)
        return values

    @property
    def framework_classes_per_atomic_state(self) -> IntArray:
        values = np.count_nonzero(self.frame_count_matrix, axis=1).astype(np.int64)
        values.setflags(write=False)
        return values

    def atomic_state(self, state_id: int) -> AtomicStateProjectionStatistics:
        index = _validated_id(state_id, self.n_atomic_states, "atomic state")
        return self.atomic_state_projections[index]

    def framework_class(self, class_id: int) -> FrameworkClassCompositionStatistics:
        index = _validated_id(class_id, self.n_framework_classes, "framework class")
        return self.framework_class_compositions[index]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frame_count_matrix": self.frame_count_matrix.tolist(),
            "probability_matrix": self.probability_matrix.tolist(),
            "atomic_state_projections": [
                x.to_dict() for x in self.atomic_state_projections
            ],
            "framework_class_compositions": [
                x.to_dict() for x in self.framework_class_compositions
            ],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossLayerContingencyStatistics":
        return cls(
            frame_count_matrix=np.asarray(
                payload["frame_count_matrix"], dtype=np.int64
            ),
            probability_matrix=np.asarray(
                payload["probability_matrix"], dtype=np.float64
            ),
            atomic_state_projections=tuple(
                AtomicStateProjectionStatistics.from_dict(
                    _mapping(x, name="atomic state projection")
                )
                for x in payload["atomic_state_projections"]
            ),
            framework_class_compositions=tuple(
                FrameworkClassCompositionStatistics.from_dict(
                    _mapping(x, name="framework class composition")
                )
                for x in payload["framework_class_compositions"]
            ),
        )


@dataclass(frozen=True, slots=True)
class CrossLayerBoundaryEvent:
    """One non-stable adjacent-frame boundary classified across graph layers."""

    boundary_id: int
    result_position_before: int
    result_position_after: int
    collection_frame_index_before: int
    collection_frame_index_after: int
    frame_id_before: int
    frame_id_after: int
    atomic_state_id_before: int
    atomic_state_id_after: int
    framework_class_id_before: int
    framework_class_id_after: int
    kind: CrossLayerBoundaryKind
    step_before: int | None = None
    step_after: int | None = None
    time_before: float | None = None
    time_after: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "boundary_id",
            "result_position_before",
            "result_position_after",
            "collection_frame_index_before",
            "collection_frame_index_after",
            "atomic_state_id_before",
            "atomic_state_id_after",
            "framework_class_id_before",
            "framework_class_id_after",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        if self.result_position_after != self.result_position_before + 1:
            raise TopologyStatisticsConsistencyError(
                "A cross-layer boundary must connect adjacent result positions."
            )
        if self.collection_frame_index_after <= self.collection_frame_index_before:
            raise TopologyStatisticsConsistencyError(
                "Trajectory collection-frame indices must increase."
            )
        kind = CrossLayerBoundaryKind(self.kind)
        atomic_changed = self.atomic_state_id_before != self.atomic_state_id_after
        framework_changed = (
            self.framework_class_id_before != self.framework_class_id_after
        )
        expected = _boundary_kind(atomic_changed, framework_changed)
        if kind is CrossLayerBoundaryKind.STABLE or kind is not expected:
            raise TopologyStatisticsConsistencyError(
                "Cross-layer event kind disagrees with state changes."
            )
        _validate_optional_pair(self.step_before, self.step_after, "step", integer=True)
        _validate_optional_pair(
            self.time_before, self.time_after, "time", integer=False
        )
        object.__setattr__(self, "kind", kind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_id": self.boundary_id,
            "result_position_before": self.result_position_before,
            "result_position_after": self.result_position_after,
            "collection_frame_index_before": self.collection_frame_index_before,
            "collection_frame_index_after": self.collection_frame_index_after,
            "frame_id_before": self.frame_id_before,
            "frame_id_after": self.frame_id_after,
            "atomic_state_id_before": self.atomic_state_id_before,
            "atomic_state_id_after": self.atomic_state_id_after,
            "framework_class_id_before": self.framework_class_id_before,
            "framework_class_id_after": self.framework_class_id_after,
            "kind": self.kind.value,
            "step_before": self.step_before,
            "step_after": self.step_after,
            "time_before": self.time_before,
            "time_after": self.time_after,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossLayerBoundaryEvent":
        values = dict(payload)
        values["kind"] = CrossLayerBoundaryKind(values["kind"])
        return cls(**values)


@dataclass(frozen=True, slots=True)
class CrossLayerBoundaryStatistics:
    """Exact classification of every adjacent boundary in one trajectory."""

    axis: FrameAxis
    boundary_kind_codes: IntArray
    events: tuple[CrossLayerBoundaryEvent, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.axis, FrameAxis):
            raise TopologyStatisticsConsistencyError("axis has the wrong type.")
        if self.axis.frame_semantics is not FrameSemantics.TRAJECTORY:
            raise TopologyStatisticsConsistencyError(
                "Cross-layer boundary statistics are trajectory-only."
            )
        codes = _readonly_int_array(self.boundary_kind_codes, ndim=1)
        expected_size = max(self.axis.n_frames - 1, 0)
        if (
            codes.size != expected_size
            or np.any(codes < 0)
            or np.any(codes >= len(_BOUNDARY_KIND_ORDER))
        ):
            raise TopologyStatisticsConsistencyError(
                "Boundary-kind codes must align with adjacent trajectory boundaries."
            )
        events = tuple(self.events)
        expected_events = []
        for boundary_position, code in enumerate(codes):
            if int(code) != _BOUNDARY_KIND_TO_CODE[CrossLayerBoundaryKind.STABLE]:
                expected_events.append(boundary_position)
        if [event.result_position_before for event in events] != expected_events:
            raise TopologyStatisticsConsistencyError(
                "Cross-layer event positions disagree with boundary-kind codes."
            )
        for event in events:
            if event.result_position_after >= self.axis.n_frames:
                raise TopologyStatisticsConsistencyError(
                    "A cross-layer event lies outside the frame axis."
                )
            if _BOUNDARY_KIND_TO_CODE[event.kind] != int(
                codes[event.result_position_before]
            ):
                raise TopologyStatisticsConsistencyError(
                    "A cross-layer event kind disagrees with boundary-kind codes."
                )
        object.__setattr__(self, "boundary_kind_codes", codes)
        object.__setattr__(self, "events", events)

    @property
    def n_frame_boundaries(self) -> int:
        return int(self.boundary_kind_codes.size)

    def count(self, kind: CrossLayerBoundaryKind | str) -> int:
        target = CrossLayerBoundaryKind(kind)
        return int(
            np.count_nonzero(self.boundary_kind_codes == _BOUNDARY_KIND_TO_CODE[target])
        )

    @property
    def n_stable_boundaries(self) -> int:
        return self.count(CrossLayerBoundaryKind.STABLE)

    @property
    def n_atomic_only_boundaries(self) -> int:
        return self.count(CrossLayerBoundaryKind.ATOMIC_ONLY)

    @property
    def n_framework_only_boundaries(self) -> int:
        return self.count(CrossLayerBoundaryKind.FRAMEWORK_ONLY)

    @property
    def n_coupled_boundaries(self) -> int:
        return self.count(CrossLayerBoundaryKind.COUPLED)

    @property
    def n_atomic_changed_boundaries(self) -> int:
        return self.n_atomic_only_boundaries + self.n_coupled_boundaries

    @property
    def n_framework_changed_boundaries(self) -> int:
        return self.n_framework_only_boundaries + self.n_coupled_boundaries

    def events_of_kind(
        self, kind: CrossLayerBoundaryKind | str
    ) -> tuple[CrossLayerBoundaryEvent, ...]:
        target = CrossLayerBoundaryKind(kind)
        return tuple(event for event in self.events if event.kind is target)

    def to_dict(self) -> dict[str, Any]:
        return {
            "axis": self.axis.to_dict(),
            "boundary_kind_codes": self.boundary_kind_codes.tolist(),
            "events": [event.to_dict() for event in self.events],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossLayerBoundaryStatistics":
        return cls(
            axis=FrameAxis.from_dict(_mapping(payload["axis"], name="axis")),
            boundary_kind_codes=np.asarray(
                payload["boundary_kind_codes"], dtype=np.int64
            ),
            events=tuple(
                CrossLayerBoundaryEvent.from_dict(_mapping(x, name="boundary event"))
                for x in payload["events"]
            ),
        )


@dataclass(frozen=True, slots=True)
class CrossLayerSummary:
    """Small human- and machine-readable summary of the catalog relation."""

    regime: CrossLayerCatalogRegime
    n_atomic_states: int
    n_framework_classes: int
    atomic_to_framework_compression_ratio: float
    n_atomic_changed_boundaries: int | None
    n_framework_changed_boundaries: int | None
    n_framework_preserving_atomic_boundaries: int | None
    n_framework_changing_atomic_boundaries: int | None

    def __post_init__(self) -> None:
        regime = CrossLayerCatalogRegime(self.regime)
        n_atomic = _positive_int(self.n_atomic_states, "n_atomic_states")
        n_framework = _positive_int(self.n_framework_classes, "n_framework_classes")
        ratio = _finite_float(
            self.atomic_to_framework_compression_ratio,
            "atomic_to_framework_compression_ratio",
        )
        if not np.isclose(ratio, n_atomic / n_framework, atol=1e-15, rtol=0.0):
            raise TopologyStatisticsConsistencyError(
                "Compression ratio disagrees with state and class counts."
            )
        optional_counts = (
            self.n_atomic_changed_boundaries,
            self.n_framework_changed_boundaries,
            self.n_framework_preserving_atomic_boundaries,
            self.n_framework_changing_atomic_boundaries,
        )
        if any(value is None for value in optional_counts) and not all(
            value is None for value in optional_counts
        ):
            raise TopologyStatisticsConsistencyError(
                "Boundary summary counts must be supplied together or omitted together."
            )
        if optional_counts[0] is not None:
            normalized = tuple(
                _nonnegative_int(value, "boundary summary count")
                for value in optional_counts
            )
            if normalized[0] != normalized[2] + normalized[3]:
                raise TopologyStatisticsConsistencyError(
                    "Atomic boundary consequences do not sum to atomic changes."
                )
            object.__setattr__(self, "n_atomic_changed_boundaries", normalized[0])
            object.__setattr__(self, "n_framework_changed_boundaries", normalized[1])
            object.__setattr__(
                self, "n_framework_preserving_atomic_boundaries", normalized[2]
            )
            object.__setattr__(
                self, "n_framework_changing_atomic_boundaries", normalized[3]
            )
        object.__setattr__(self, "regime", regime)
        object.__setattr__(self, "n_atomic_states", n_atomic)
        object.__setattr__(self, "n_framework_classes", n_framework)
        object.__setattr__(self, "atomic_to_framework_compression_ratio", ratio)

    @property
    def interpretation(self) -> str:
        if self.regime is CrossLayerCatalogRegime.UNIFORM:
            return "atomic connectivity and framework topology are both uniform"
        if self.regime is CrossLayerCatalogRegime.ATOMIC_VARIABLE_FRAMEWORK_UNIFORM:
            return "atomic connectivity varies while framework topology remains uniform"
        return "multiple framework topology classes are present"

    def to_dict(self) -> dict[str, Any]:
        return {
            "regime": self.regime.value,
            "n_atomic_states": self.n_atomic_states,
            "n_framework_classes": self.n_framework_classes,
            "atomic_to_framework_compression_ratio": self.atomic_to_framework_compression_ratio,
            "n_atomic_changed_boundaries": self.n_atomic_changed_boundaries,
            "n_framework_changed_boundaries": self.n_framework_changed_boundaries,
            "n_framework_preserving_atomic_boundaries": self.n_framework_preserving_atomic_boundaries,
            "n_framework_changing_atomic_boundaries": self.n_framework_changing_atomic_boundaries,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CrossLayerSummary":
        return cls(
            regime=CrossLayerCatalogRegime(payload["regime"]),
            n_atomic_states=int(payload["n_atomic_states"]),
            n_framework_classes=int(payload["n_framework_classes"]),
            atomic_to_framework_compression_ratio=float(
                payload["atomic_to_framework_compression_ratio"]
            ),
            n_atomic_changed_boundaries=payload["n_atomic_changed_boundaries"],
            n_framework_changed_boundaries=payload["n_framework_changed_boundaries"],
            n_framework_preserving_atomic_boundaries=payload[
                "n_framework_preserving_atomic_boundaries"
            ],
            n_framework_changing_atomic_boundaries=payload[
                "n_framework_changing_atomic_boundaries"
            ],
        )


@dataclass(frozen=True, slots=True)
class TopologyStatistics:
    """Complete TS4 atomic/framework statistics and exact cross-layer alignment."""

    atomic: AtomicConnectivityStatistics
    framework: FrameworkTopologyStatistics
    contingency: CrossLayerContingencyStatistics
    boundary_statistics: CrossLayerBoundaryStatistics | None
    summary: CrossLayerSummary
    options: CombinedStatisticsOptions
    alignment_mode: str
    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_COMBINED_TOPOLOGY_STATISTICS_SCHEMA
    digest_algorithm: str = TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.atomic, AtomicConnectivityStatistics):
            raise TopologyStatisticsConsistencyError("atomic has the wrong type.")
        if not isinstance(self.framework, FrameworkTopologyStatistics):
            raise TopologyStatisticsConsistencyError("framework has the wrong type.")
        if self.atomic.axis.to_dict() != self.framework.axis.to_dict():
            raise TopologyStatisticsConsistencyError(
                "Atomic and framework statistics must use exactly one frame axis."
            )
        if not isinstance(self.contingency, CrossLayerContingencyStatistics):
            raise TopologyStatisticsConsistencyError("contingency has the wrong type.")
        if (
            self.contingency.n_frames != self.atomic.n_frames
            or self.contingency.n_atomic_states != self.atomic.n_states
            or self.contingency.n_framework_classes != self.framework.n_topologies
        ):
            raise TopologyStatisticsConsistencyError(
                "Contingency dimensions disagree with branch statistics."
            )
        if self.boundary_statistics is not None:
            if not isinstance(self.boundary_statistics, CrossLayerBoundaryStatistics):
                raise TopologyStatisticsConsistencyError(
                    "boundary_statistics has the wrong type."
                )
            if self.boundary_statistics.axis.to_dict() != self.atomic.axis.to_dict():
                raise TopologyStatisticsConsistencyError(
                    "Boundary statistics do not use the combined frame axis."
                )
        if not isinstance(self.summary, CrossLayerSummary):
            raise TopologyStatisticsConsistencyError("summary has the wrong type.")
        if (
            self.summary.n_atomic_states != self.atomic.n_states
            or self.summary.n_framework_classes != self.framework.n_topologies
        ):
            raise TopologyStatisticsConsistencyError(
                "Cross-layer summary dimensions disagree with branch statistics."
            )
        if not isinstance(self.options, CombinedStatisticsOptions):
            raise TopologyStatisticsConsistencyError("options has the wrong type.")
        alignment_mode = str(self.alignment_mode).strip()
        if alignment_mode not in {"exact_catalog", "exact_per_frame"}:
            raise TopologyStatisticsConsistencyError(
                "alignment_mode must be exact_catalog or exact_per_frame."
            )
        if (
            self.canonical_schema_version
            != CANONICAL_COMBINED_TOPOLOGY_STATISTICS_SCHEMA
        ):
            raise TopologyStatisticsConsistencyError(
                "Unsupported combined topology-statistics schema."
            )
        if self.digest_algorithm != TOPOLOGY_STATISTICS_DIGEST_ALGORITHM:
            raise TopologyStatisticsConsistencyError(
                "Unsupported combined topology-statistics digest algorithm."
            )
        metadata = MappingProxyType(_deep_copy_mapping(self.metadata))
        object.__setattr__(self, "alignment_mode", alignment_mode)
        object.__setattr__(self, "metadata", metadata)
        expected_digest = _combined_statistics_digest(self)
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise TopologyStatisticsConsistencyError(
                "Stored combined-statistics digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    @property
    def axis(self) -> FrameAxis:
        return self.atomic.axis

    @property
    def n_frames(self) -> int:
        return self.axis.n_frames

    def to_dict(self) -> dict[str, Any]:
        return _combined_statistics_payload(self, include_digest=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyStatistics":
        if (
            payload.get("schema_version")
            != CANONICAL_COMBINED_TOPOLOGY_STATISTICS_SCHEMA
        ):
            raise TopologyStatisticsSerializationError(
                "Unsupported combined topology-statistics schema version."
            )
        if payload.get("object_type") != "TopologyStatistics":
            raise TopologyStatisticsSerializationError(
                "Payload is not a TopologyStatistics object."
            )
        try:
            return cls(
                atomic=AtomicConnectivityStatistics.from_dict(
                    _mapping(payload["atomic"], name="atomic")
                ),
                framework=FrameworkTopologyStatistics.from_dict(
                    _mapping(payload["framework"], name="framework")
                ),
                contingency=CrossLayerContingencyStatistics.from_dict(
                    _mapping(payload["contingency"], name="contingency")
                ),
                boundary_statistics=None
                if payload["boundary_statistics"] is None
                else CrossLayerBoundaryStatistics.from_dict(
                    _mapping(payload["boundary_statistics"], name="boundary_statistics")
                ),
                summary=CrossLayerSummary.from_dict(
                    _mapping(payload["summary"], name="summary")
                ),
                options=CombinedStatisticsOptions.from_dict(
                    _mapping(payload["options"], name="options")
                ),
                alignment_mode=str(payload["alignment_mode"]),
                metadata=_mapping(payload.get("metadata", {}), name="metadata"),
                canonical_schema_version=str(payload["schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, TopologyStatisticsConsistencyError):
                raise
            raise TopologyStatisticsSerializationError(
                "Malformed TopologyStatistics payload."
            ) from exc


def compute_topology_statistics(
    atomic_catalog: AtomicConnectivityResult,
    framework_catalog: TopologyCatalog,
    *,
    steps: ArrayLike | None = None,
    times: ArrayLike | None = None,
    time_unit: str | None = None,
    options: CombinedStatisticsOptions | None = None,
) -> TopologyStatistics:
    """Compute TS4 branch statistics and exact cross-layer alignment.

    The supplied framework catalog must have been constructed from the supplied
    atomic catalog over exactly the same selected frames. Equal length alone is
    not sufficient: frame indices, frame IDs, semantics, and connectivity-state
    assignments are checked exactly.
    """

    if not isinstance(atomic_catalog, AtomicConnectivityResult):
        raise TypeError("atomic_catalog must be an AtomicConnectivityResult.")
    if not isinstance(framework_catalog, TopologyCatalog):
        raise TypeError("framework_catalog must be a TopologyCatalog.")
    effective = CombinedStatisticsOptions() if options is None else options
    if not isinstance(effective, CombinedStatisticsOptions):
        raise TypeError("options must be a CombinedStatisticsOptions instance.")

    semantics, alignment_mode = _validate_catalog_alignment(
        atomic_catalog, framework_catalog
    )
    atomic = compute_atomic_connectivity_statistics(
        atomic_catalog,
        steps=steps,
        times=times,
        time_unit=time_unit,
        options=effective.atomic_options,
    )
    framework = compute_framework_topology_statistics(
        framework_catalog,
        steps=steps,
        times=times,
        time_unit=time_unit,
        options=effective.framework_options,
    )
    if atomic.axis.to_dict() != framework.axis.to_dict():
        raise TopologyStatisticsConsistencyError(
            "Branch statistics produced different frame axes."
        )

    contingency = _compute_contingency(
        atomic_catalog.frame_state_ids,
        framework_catalog.frame_topology_ids,
        atomic_catalog.n_states,
        framework_catalog.n_topologies,
    )
    boundary_statistics = None
    temporal_reason = "disabled_by_option"
    temporal_eligible = (
        semantics is FrameSemantics.TRAJECTORY
        and atomic_catalog.consistency is not ConnectivityConsistency.PER_FRAME
        and framework_catalog.catalog_options.mode == "catalog"
    )
    if effective.include_boundary_statistics and temporal_eligible:
        boundary_statistics = _compute_boundary_statistics(
            atomic.axis,
            atomic_catalog.frame_state_ids,
            framework_catalog.frame_topology_ids,
        )
        temporal_reason = "exact_reconciled_trajectory"
    elif effective.include_boundary_statistics:
        temporal_reason = (
            "ensemble_non_temporal"
            if semantics is FrameSemantics.ENSEMBLE
            else "unreconciled_per_frame_identity"
        )

    summary = _compute_summary(
        atomic_catalog.n_states,
        framework_catalog.n_topologies,
        boundary_statistics,
    )
    metadata = {
        "frame_semantics": semantics.value,
        "boundary_statistics_status": temporal_reason,
        "atomic_catalog_consistency": atomic_catalog.consistency.value,
        "framework_catalog_consistency": framework_catalog.consistency.value,
        "framework_catalog_mode": framework_catalog.catalog_options.mode,
        "source_atomic_state_digests": [
            state.digest for state in atomic_catalog.states
        ],
        "source_framework_catalog_digest": framework_catalog.digest,
        "source_framework_mapping_digest": framework_catalog.mapping.digest,
    }
    return TopologyStatistics(
        atomic=atomic,
        framework=framework,
        contingency=contingency,
        boundary_statistics=boundary_statistics,
        summary=summary,
        options=effective,
        alignment_mode=alignment_mode,
        metadata=metadata,
    )


def _validate_catalog_alignment(
    atomic: AtomicConnectivityResult, framework: TopologyCatalog
) -> tuple[FrameSemantics, str]:
    raw_semantics = atomic.metadata.get("frame_semantics")
    try:
        semantics = FrameSemantics(raw_semantics)
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsInputError(
            "Atomic catalog metadata lacks valid frame_semantics."
        ) from exc
    if framework.frame_semantics is not semantics:
        raise TopologyStatisticsInputError(
            "Atomic and framework catalogs have different frame semantics."
        )
    if not np.array_equal(atomic.frame_indices, framework.frame_indices):
        raise TopologyStatisticsInputError(
            "Atomic and framework catalogs have different selected frame indices."
        )
    if not np.array_equal(atomic.frame_ids, framework.frame_ids):
        raise TopologyStatisticsInputError(
            "Atomic and framework catalogs have different frame IDs or ordering."
        )
    if not np.array_equal(
        atomic.frame_state_ids, framework.frame_connectivity_state_ids
    ):
        raise TopologyStatisticsInputError(
            "Framework catalog connectivity-state assignments do not match the atomic catalog."
        )

    atomic_digests = tuple(state.digest for state in atomic.states)
    if framework.catalog_options.mode == "catalog":
        mapping = np.asarray(framework.connectivity_state_topology_ids, dtype=np.int64)
        if mapping.size != atomic.n_states:
            raise TopologyStatisticsInputError(
                "Framework state-to-topology mapping does not cover every atomic state."
            )
        for topology_id, topology in enumerate(framework.topologies):
            state_ids = np.flatnonzero(mapping == topology_id)
            if state_ids.size == 0 or topology.source_connectivity_digest not in {
                atomic_digests[int(state_id)] for state_id in state_ids
            }:
                raise TopologyStatisticsInputError(
                    "A framework topology representative is not derived from its aligned atomic states."
                )
        return semantics, "exact_catalog"

    for position, topology in enumerate(framework.topologies):
        state_id = int(atomic.frame_state_ids[position])
        if topology.source_connectivity_digest != atomic_digests[state_id]:
            raise TopologyStatisticsInputError(
                "A per-frame framework topology is not derived from the aligned atomic state."
            )
    return semantics, "exact_per_frame"


def _compute_contingency(
    atomic_state_ids: ArrayLike,
    framework_class_ids: ArrayLike,
    n_atomic_states: int,
    n_framework_classes: int,
) -> CrossLayerContingencyStatistics:
    atomic_ids = np.asarray(atomic_state_ids, dtype=np.int64)
    framework_ids = np.asarray(framework_class_ids, dtype=np.int64)
    counts = np.zeros((n_atomic_states, n_framework_classes), dtype=np.int64)
    np.add.at(counts, (atomic_ids, framework_ids), 1)
    probabilities = counts.astype(float) / int(counts.sum())

    atomic_rows = []
    for state_id in range(n_atomic_states):
        class_ids = np.flatnonzero(counts[state_id] > 0).astype(np.int64)
        row_counts = counts[state_id, class_ids]
        row_probabilities = row_counts.astype(float) / int(row_counts.sum())
        dominant = tuple(
            int(class_ids[index])
            for index in np.flatnonzero(row_counts == row_counts.max())
        )
        atomic_rows.append(
            AtomicStateProjectionStatistics(
                atomic_state_id=state_id,
                framework_class_ids=class_ids,
                frame_counts=row_counts,
                conditional_probabilities=row_probabilities,
                dominant_framework_class_ids=dominant,
            )
        )

    framework_columns = []
    for class_id in range(n_framework_classes):
        state_ids = np.flatnonzero(counts[:, class_id] > 0).astype(np.int64)
        column_counts = counts[state_ids, class_id]
        column_probabilities = column_counts.astype(float) / int(column_counts.sum())
        dominant = tuple(
            int(state_ids[index])
            for index in np.flatnonzero(column_counts == column_counts.max())
        )
        framework_columns.append(
            FrameworkClassCompositionStatistics(
                framework_class_id=class_id,
                atomic_state_ids=state_ids,
                frame_counts=column_counts,
                conditional_probabilities=column_probabilities,
                dominant_atomic_state_ids=dominant,
            )
        )
    return CrossLayerContingencyStatistics(
        frame_count_matrix=counts,
        probability_matrix=probabilities,
        atomic_state_projections=tuple(atomic_rows),
        framework_class_compositions=tuple(framework_columns),
    )


def _compute_boundary_statistics(
    axis: FrameAxis,
    atomic_state_ids: ArrayLike,
    framework_class_ids: ArrayLike,
) -> CrossLayerBoundaryStatistics:
    atomic_ids = np.asarray(atomic_state_ids, dtype=np.int64)
    framework_ids = np.asarray(framework_class_ids, dtype=np.int64)
    codes = np.empty(max(axis.n_frames - 1, 0), dtype=np.int64)
    events = []
    event_id = 0
    for before in range(axis.n_frames - 1):
        after = before + 1
        atomic_changed = int(atomic_ids[before]) != int(atomic_ids[after])
        framework_changed = int(framework_ids[before]) != int(framework_ids[after])
        kind = _boundary_kind(atomic_changed, framework_changed)
        codes[before] = _BOUNDARY_KIND_TO_CODE[kind]
        if kind is CrossLayerBoundaryKind.STABLE:
            continue
        events.append(
            CrossLayerBoundaryEvent(
                boundary_id=event_id,
                result_position_before=before,
                result_position_after=after,
                collection_frame_index_before=int(
                    axis.collection_frame_indices[before]
                ),
                collection_frame_index_after=int(axis.collection_frame_indices[after]),
                frame_id_before=int(axis.frame_ids[before]),
                frame_id_after=int(axis.frame_ids[after]),
                atomic_state_id_before=int(atomic_ids[before]),
                atomic_state_id_after=int(atomic_ids[after]),
                framework_class_id_before=int(framework_ids[before]),
                framework_class_id_after=int(framework_ids[after]),
                kind=kind,
                step_before=None if axis.steps is None else int(axis.steps[before]),
                step_after=None if axis.steps is None else int(axis.steps[after]),
                time_before=None if axis.times is None else float(axis.times[before]),
                time_after=None if axis.times is None else float(axis.times[after]),
            )
        )
        event_id += 1
    return CrossLayerBoundaryStatistics(
        axis=axis,
        boundary_kind_codes=codes,
        events=tuple(events),
    )


def _compute_summary(
    n_atomic_states: int,
    n_framework_classes: int,
    boundaries: CrossLayerBoundaryStatistics | None,
) -> CrossLayerSummary:
    if n_framework_classes == 1:
        regime = (
            CrossLayerCatalogRegime.UNIFORM
            if n_atomic_states == 1
            else CrossLayerCatalogRegime.ATOMIC_VARIABLE_FRAMEWORK_UNIFORM
        )
    else:
        regime = CrossLayerCatalogRegime.FRAMEWORK_VARIABLE
    if boundaries is None:
        atomic_changed = framework_changed = preserving = changing = None
    else:
        atomic_changed = boundaries.n_atomic_changed_boundaries
        framework_changed = boundaries.n_framework_changed_boundaries
        preserving = boundaries.n_atomic_only_boundaries
        changing = boundaries.n_coupled_boundaries
    return CrossLayerSummary(
        regime=regime,
        n_atomic_states=n_atomic_states,
        n_framework_classes=n_framework_classes,
        atomic_to_framework_compression_ratio=n_atomic_states / n_framework_classes,
        n_atomic_changed_boundaries=atomic_changed,
        n_framework_changed_boundaries=framework_changed,
        n_framework_preserving_atomic_boundaries=preserving,
        n_framework_changing_atomic_boundaries=changing,
    )


def _boundary_kind(
    atomic_changed: bool, framework_changed: bool
) -> CrossLayerBoundaryKind:
    if atomic_changed and framework_changed:
        return CrossLayerBoundaryKind.COUPLED
    if atomic_changed:
        return CrossLayerBoundaryKind.ATOMIC_ONLY
    if framework_changed:
        return CrossLayerBoundaryKind.FRAMEWORK_ONLY
    return CrossLayerBoundaryKind.STABLE


def _combined_statistics_payload(
    result: TopologyStatistics, *, include_digest: bool
) -> dict[str, Any]:
    payload = {
        "schema_version": result.canonical_schema_version,
        "object_type": "TopologyStatistics",
        "digest_algorithm": result.digest_algorithm,
        "atomic": result.atomic.to_dict(),
        "framework": result.framework.to_dict(),
        "contingency": result.contingency.to_dict(),
        "boundary_statistics": None
        if result.boundary_statistics is None
        else result.boundary_statistics.to_dict(),
        "summary": result.summary.to_dict(),
        "options": result.options.to_dict(),
        "alignment_mode": result.alignment_mode,
        "metadata": _json_safe(result.metadata),
    }
    if include_digest:
        payload["digest"] = result.digest
    return payload


def _combined_statistics_digest(result: TopologyStatistics) -> str:
    payload = _combined_statistics_payload(result, include_digest=False)
    return hashlib.sha256(
        canonical_statistics_json(payload).encode("utf-8")
    ).hexdigest()


def _readonly_int_array(values: ArrayLike, *, ndim: int) -> IntArray:
    array = np.array(values, dtype=np.int64, copy=True)
    if array.ndim != ndim:
        raise TopologyStatisticsConsistencyError(
            f"Expected a {ndim}-dimensional integer array."
        )
    array.setflags(write=False)
    return array


def _readonly_float_array(values: ArrayLike, *, ndim: int) -> FloatArray:
    array = np.array(values, dtype=np.float64, copy=True)
    if array.ndim != ndim or not np.all(np.isfinite(array)):
        raise TopologyStatisticsConsistencyError(
            f"Expected a finite {ndim}-dimensional floating array."
        )
    array.setflags(write=False)
    return array


def _mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TopologyStatisticsSerializationError(f"{name} must be a mapping.")
    return value


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, (bool, np.bool_)):
        raise TopologyStatisticsConsistencyError(f"{name} must be an integer.")
    try:
        integer = int(value)
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsConsistencyError(f"{name} must be an integer.") from exc
    if integer != value or integer < 0:
        raise TopologyStatisticsConsistencyError(
            f"{name} must be a nonnegative integer."
        )
    return integer


def _positive_int(value: Any, name: str) -> int:
    integer = _nonnegative_int(value, name)
    if integer <= 0:
        raise TopologyStatisticsConsistencyError(f"{name} must be positive.")
    return integer


def _finite_float(value: Any, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsConsistencyError(f"{name} must be finite.") from exc
    if not np.isfinite(number):
        raise TopologyStatisticsConsistencyError(f"{name} must be finite.")
    return number


def _validated_id(value: Any, size: int, label: str) -> int:
    index = _nonnegative_int(value, f"{label} ID")
    if index >= size:
        raise KeyError(f"{label.capitalize()} ID {index} is out of range.")
    return index


def _validate_optional_pair(
    before: Any, after: Any, label: str, *, integer: bool
) -> None:
    if (before is None) != (after is None):
        raise TopologyStatisticsConsistencyError(
            f"Boundary {label} metadata must be supplied as a pair."
        )
    if before is None:
        return
    if integer:
        left = _nonnegative_int(before, f"{label}_before")
        right = _nonnegative_int(after, f"{label}_after")
    else:
        left = _finite_float(before, f"{label}_before")
        right = _finite_float(after, f"{label}_after")
    if right <= left:
        raise TopologyStatisticsConsistencyError(
            f"Boundary {label} values must increase."
        )


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _deep_copy_value(item) for key, item in value.items()}


def _deep_copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _deep_copy_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_deep_copy_value(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, Enum):
        return value.value
    return value
