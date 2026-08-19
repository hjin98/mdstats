"""Trajectory-only temporal statistics for topology-derived catalogs.

This module is the TS3 shared temporal layer.  It converts an authoritative
trajectory state assignment into exact residence intervals, transition events,
transition-count matrices, return lags, cumulative event counts, and generic
entity-presence episodes.  Atomic and framework statistics reuse these objects
without redefining temporal conventions.

The module never infers time ordering for ensembles.  Every public computation
requires a :class:`~mdstats.analysis.topology_statistics.FrameAxis` with
``FrameSemantics.TRAJECTORY``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ...semantics import FrameSemantics
from ._common import (
    DEFAULT_QUANTILES,
    TOPOLOGY_STATISTICS_DIGEST_ALGORITHM,
    DiscreteCountDistribution,
    FrameAxis,
    ScalarSeries,
    ScalarSummary,
    TopologyStatisticsConsistencyError,
    TopologyStatisticsInputError,
    TopologyStatisticsSerializationError,
    build_scalar_series,
    canonical_statistics_json,
    compute_discrete_count_distribution,
    compute_scalar_summary,
)

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]

CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA = (
    "mdstats.topology-statistics.temporal.v1"
)


@dataclass(frozen=True, slots=True)
class TemporalStatisticsOptions:
    """Controls exact TS3 temporal summaries.

    ``quantiles`` are used for dwell-, return-, and episode-length summaries.
    Transition probabilities, rates, autocorrelation, and censoring-corrected
    survival estimators are deliberately outside TS3.
    """

    quantiles: tuple[float, ...] = DEFAULT_QUANTILES

    def __post_init__(self) -> None:
        object.__setattr__(self, "quantiles", _validated_quantiles(self.quantiles))

    def to_dict(self) -> dict[str, Any]:
        return {"quantiles": list(self.quantiles)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TemporalStatisticsOptions":
        return cls(
            quantiles=tuple(
                float(value) for value in payload.get("quantiles", DEFAULT_QUANTILES)
            )
        )


@dataclass(frozen=True, slots=True)
class StateResidenceInterval:
    """One maximal half-open residence interval ``[start, stop)``."""

    interval_id: int
    state_id: int
    result_position_start: int
    result_position_stop: int
    collection_frame_index_start: int
    collection_frame_index_end: int
    frame_id_start: int
    frame_id_end: int
    n_frames: int
    sample_span: int
    step_start: int | None = None
    step_end: int | None = None
    step_span: int | None = None
    time_start: float | None = None
    time_end: float | None = None
    time_span: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "interval_id",
            "state_id",
            "result_position_start",
            "result_position_stop",
            "collection_frame_index_start",
            "collection_frame_index_end",
            "n_frames",
            "sample_span",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        if self.result_position_stop <= self.result_position_start:
            raise TopologyStatisticsConsistencyError(
                "A residence interval must contain at least one frame."
            )
        expected_frames = self.result_position_stop - self.result_position_start
        if self.n_frames != expected_frames:
            raise TopologyStatisticsConsistencyError(
                "n_frames disagrees with the half-open interval bounds."
            )
        if self.sample_span != self.n_frames - 1:
            raise TopologyStatisticsConsistencyError(
                "sample_span must equal n_frames - 1."
            )
        if self.collection_frame_index_end < self.collection_frame_index_start:
            raise TopologyStatisticsConsistencyError(
                "Collection frame indices must be nondecreasing within an interval."
            )
        _validate_optional_axis_span(
            self.step_start, self.step_end, self.step_span, integer=True, label="step"
        )
        _validate_optional_axis_span(
            self.time_start, self.time_end, self.time_span, integer=False, label="time"
        )

    @property
    def result_position_end(self) -> int:
        """Inclusive final result position."""

        return self.result_position_stop - 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "interval_id": self.interval_id,
            "state_id": self.state_id,
            "result_position_start": self.result_position_start,
            "result_position_stop": self.result_position_stop,
            "collection_frame_index_start": self.collection_frame_index_start,
            "collection_frame_index_end": self.collection_frame_index_end,
            "frame_id_start": self.frame_id_start,
            "frame_id_end": self.frame_id_end,
            "n_frames": self.n_frames,
            "sample_span": self.sample_span,
            "step_start": self.step_start,
            "step_end": self.step_end,
            "step_span": self.step_span,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "time_span": self.time_span,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateResidenceInterval":
        return cls(**dict(payload))


@dataclass(frozen=True, slots=True)
class StateTransitionEvent:
    """One exact changed-state boundary between adjacent trajectory frames."""

    transition_id: int
    result_position_before: int
    result_position_after: int
    source_state_id: int
    target_state_id: int
    collection_frame_index_before: int
    collection_frame_index_after: int
    frame_id_before: int
    frame_id_after: int
    step_before: int | None = None
    step_after: int | None = None
    time_before: float | None = None
    time_after: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "transition_id",
            "result_position_before",
            "result_position_after",
            "source_state_id",
            "target_state_id",
            "collection_frame_index_before",
            "collection_frame_index_after",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        if self.result_position_after != self.result_position_before + 1:
            raise TopologyStatisticsConsistencyError(
                "A transition event must connect adjacent result positions."
            )
        if self.source_state_id == self.target_state_id:
            raise TopologyStatisticsConsistencyError(
                "StateTransitionEvent represents changed-state boundaries only."
            )
        if self.collection_frame_index_after <= self.collection_frame_index_before:
            raise TopologyStatisticsConsistencyError(
                "Trajectory collection-frame indices must increase across an event."
            )
        if (self.step_before is None) != (self.step_after is None):
            raise TopologyStatisticsConsistencyError(
                "Transition step metadata must be supplied as a pair."
            )
        if self.step_before is not None and self.step_after <= self.step_before:
            raise TopologyStatisticsConsistencyError("Transition steps must increase.")
        if (self.time_before is None) != (self.time_after is None):
            raise TopologyStatisticsConsistencyError(
                "Transition time metadata must be supplied as a pair."
            )
        if self.time_before is not None:
            before = _finite_float(self.time_before, "time_before")
            after = _finite_float(self.time_after, "time_after")
            if after <= before:
                raise TopologyStatisticsConsistencyError(
                    "Transition times must increase."
                )
            object.__setattr__(self, "time_before", before)
            object.__setattr__(self, "time_after", after)

    def to_dict(self) -> dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "result_position_before": self.result_position_before,
            "result_position_after": self.result_position_after,
            "source_state_id": self.source_state_id,
            "target_state_id": self.target_state_id,
            "collection_frame_index_before": self.collection_frame_index_before,
            "collection_frame_index_after": self.collection_frame_index_after,
            "frame_id_before": self.frame_id_before,
            "frame_id_after": self.frame_id_after,
            "step_before": self.step_before,
            "step_after": self.step_after,
            "time_before": self.time_before,
            "time_after": self.time_after,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateTransitionEvent":
        return cls(**dict(payload))


@dataclass(frozen=True, slots=True)
class StateResidenceStatistics:
    """Residence and recurrence summaries for one declared state."""

    state_id: int
    interval_ids: IntArray
    total_frames: int
    frame_length_distribution: DiscreteCountDistribution | None
    time_span_summary: ScalarSummary | None
    return_frame_lags: IntArray
    return_frame_lag_distribution: DiscreteCountDistribution | None
    return_time_lags: FloatArray | None
    return_time_lag_summary: ScalarSummary | None

    def __post_init__(self) -> None:
        state_id = _nonnegative_int(self.state_id, "state_id")
        interval_ids = _readonly_int_array(self.interval_ids)
        if interval_ids.size and np.any(np.diff(interval_ids) <= 0):
            raise TopologyStatisticsConsistencyError(
                "interval_ids must be strictly increasing."
            )
        total_frames = _nonnegative_int(self.total_frames, "total_frames")
        return_frames = _readonly_int_array(self.return_frame_lags)
        if np.any(return_frames <= 0):
            raise TopologyStatisticsConsistencyError(
                "Return-frame lags must be strictly positive."
            )
        if interval_ids.size == 0:
            if total_frames != 0 or self.frame_length_distribution is not None:
                raise TopologyStatisticsConsistencyError(
                    "An unobserved state cannot carry residence frames."
                )
        elif self.frame_length_distribution is None:
            raise TopologyStatisticsConsistencyError(
                "Observed states require a frame-length distribution."
            )
        else:
            if self.frame_length_distribution.summary.count != interval_ids.size:
                raise TopologyStatisticsConsistencyError(
                    "Frame-length distribution count must equal the visit count."
                )
            reconstructed_frames = int(
                np.dot(
                    self.frame_length_distribution.support,
                    self.frame_length_distribution.frequencies,
                )
            )
            if reconstructed_frames != total_frames:
                raise TopologyStatisticsConsistencyError(
                    "Frame-length distribution disagrees with total_frames."
                )
        if return_frames.size == 0:
            if self.return_frame_lag_distribution is not None:
                raise TopologyStatisticsConsistencyError(
                    "Empty return lags cannot have a distribution."
                )
        elif self.return_frame_lag_distribution is None:
            raise TopologyStatisticsConsistencyError(
                "Nonempty return lags require a distribution."
            )
        elif self.return_frame_lag_distribution.summary.count != return_frames.size:
            raise TopologyStatisticsConsistencyError(
                "Return-frame distribution count disagrees with return lags."
            )
        return_times = (
            None
            if self.return_time_lags is None
            else _readonly_float_array(self.return_time_lags)
        )
        if return_times is not None and np.any(return_times <= 0.0):
            raise TopologyStatisticsConsistencyError(
                "Return-time lags must be strictly positive."
            )
        if return_times is None:
            if self.return_time_lag_summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "Return-time summary requires return-time lags."
                )
        elif return_times.size == 0:
            if self.return_time_lag_summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "Empty return-time lags cannot have a summary."
                )
        elif self.return_time_lag_summary is None:
            raise TopologyStatisticsConsistencyError(
                "Nonempty return-time lags require a summary."
            )
        if return_times is not None and return_times.size != return_frames.size:
            raise TopologyStatisticsConsistencyError(
                "Return-frame and return-time lags must align."
            )
        if (
            self.time_span_summary is not None
            and self.time_span_summary.count != interval_ids.size
        ):
            raise TopologyStatisticsConsistencyError(
                "Time-span summary count must equal the visit count."
            )
        if (
            self.return_time_lag_summary is not None
            and self.return_time_lag_summary.count != return_frames.size
        ):
            raise TopologyStatisticsConsistencyError(
                "Return-time summary count disagrees with return lags."
            )
        object.__setattr__(self, "state_id", state_id)
        object.__setattr__(self, "interval_ids", interval_ids)
        object.__setattr__(self, "total_frames", total_frames)
        object.__setattr__(self, "return_frame_lags", return_frames)
        object.__setattr__(self, "return_time_lags", return_times)

    @property
    def n_visits(self) -> int:
        return int(self.interval_ids.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "interval_ids": self.interval_ids.tolist(),
            "total_frames": self.total_frames,
            "frame_length_distribution": None
            if self.frame_length_distribution is None
            else self.frame_length_distribution.to_dict(),
            "time_span_summary": None
            if self.time_span_summary is None
            else self.time_span_summary.to_dict(),
            "return_frame_lags": self.return_frame_lags.tolist(),
            "return_frame_lag_distribution": None
            if self.return_frame_lag_distribution is None
            else self.return_frame_lag_distribution.to_dict(),
            "return_time_lags": None
            if self.return_time_lags is None
            else self.return_time_lags.tolist(),
            "return_time_lag_summary": None
            if self.return_time_lag_summary is None
            else self.return_time_lag_summary.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateResidenceStatistics":
        return cls(
            state_id=int(payload["state_id"]),
            interval_ids=np.asarray(payload["interval_ids"], dtype=np.int64),
            total_frames=int(payload["total_frames"]),
            frame_length_distribution=None
            if payload["frame_length_distribution"] is None
            else DiscreteCountDistribution.from_dict(
                _mapping(
                    payload["frame_length_distribution"], "frame_length_distribution"
                )
            ),
            time_span_summary=None
            if payload["time_span_summary"] is None
            else ScalarSummary.from_dict(
                _mapping(payload["time_span_summary"], "time_span_summary")
            ),
            return_frame_lags=np.asarray(payload["return_frame_lags"], dtype=np.int64),
            return_frame_lag_distribution=None
            if payload["return_frame_lag_distribution"] is None
            else DiscreteCountDistribution.from_dict(
                _mapping(
                    payload["return_frame_lag_distribution"],
                    "return_frame_lag_distribution",
                )
            ),
            return_time_lags=None
            if payload["return_time_lags"] is None
            else np.asarray(payload["return_time_lags"], dtype=np.float64),
            return_time_lag_summary=None
            if payload["return_time_lag_summary"] is None
            else ScalarSummary.from_dict(
                _mapping(payload["return_time_lag_summary"], "return_time_lag_summary")
            ),
        )


@dataclass(frozen=True, slots=True)
class StateTransitionStatistics:
    """Exact temporal organization of one trajectory state assignment."""

    axis: FrameAxis
    n_states: int
    frame_to_state_id: IntArray
    residence_intervals: tuple[StateResidenceInterval, ...]
    state_residence_statistics: tuple[StateResidenceStatistics, ...]
    transition_events: tuple[StateTransitionEvent, ...]
    adjacent_count_matrix: IntArray
    changed_count_matrix: IntArray
    cumulative_changed_boundaries: ScalarSeries
    dwell_frame_distribution: DiscreteCountDistribution
    dwell_time_span_summary: ScalarSummary | None
    options: TemporalStatisticsOptions
    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA
    digest_algorithm: str = TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _require_trajectory_axis(self.axis)
        n_states = _positive_int(self.n_states, "n_states")
        assignments = _readonly_int_array(self.frame_to_state_id)
        if assignments.size != self.axis.n_frames or np.any(assignments >= n_states):
            raise TopologyStatisticsConsistencyError(
                "frame_to_state_id must align with the axis and declared states."
            )
        intervals = tuple(self.residence_intervals)
        if not intervals:
            raise TopologyStatisticsConsistencyError(
                "A nonempty trajectory requires at least one residence interval."
            )
        if tuple(interval.interval_id for interval in intervals) != tuple(
            range(len(intervals))
        ):
            raise TopologyStatisticsConsistencyError(
                "Residence interval IDs must be dense and ordered."
            )
        cursor = 0
        for interval in intervals:
            if interval.result_position_start != cursor:
                raise TopologyStatisticsConsistencyError(
                    "Residence intervals must partition the trajectory contiguously."
                )
            expected = assignments[
                interval.result_position_start : interval.result_position_stop
            ]
            if not np.all(expected == interval.state_id):
                raise TopologyStatisticsConsistencyError(
                    "Residence interval state disagrees with frame assignments."
                )
            cursor = interval.result_position_stop
        if cursor != self.axis.n_frames:
            raise TopologyStatisticsConsistencyError(
                "Residence intervals do not cover the complete trajectory."
            )
        per_state = tuple(self.state_residence_statistics)
        if len(per_state) != n_states or tuple(x.state_id for x in per_state) != tuple(
            range(n_states)
        ):
            raise TopologyStatisticsConsistencyError(
                "State residence statistics must cover dense state IDs."
            )
        for item in per_state:
            expected_ids = np.asarray(
                [
                    interval.interval_id
                    for interval in intervals
                    if interval.state_id == item.state_id
                ],
                dtype=np.int64,
            )
            if not np.array_equal(item.interval_ids, expected_ids):
                raise TopologyStatisticsConsistencyError(
                    "Per-state interval IDs disagree with residence intervals."
                )
        events = tuple(self.transition_events)
        if tuple(event.transition_id for event in events) != tuple(range(len(events))):
            raise TopologyStatisticsConsistencyError(
                "Transition event IDs must be dense and ordered."
            )
        adjacent = _readonly_int_matrix(self.adjacent_count_matrix, n_states)
        changed = _readonly_int_matrix(self.changed_count_matrix, n_states)
        if np.any(np.diag(changed) != 0):
            raise TopologyStatisticsConsistencyError(
                "changed_count_matrix must have a zero diagonal."
            )
        expected_adjacent = np.zeros((n_states, n_states), dtype=np.int64)
        for left, right in zip(assignments[:-1], assignments[1:], strict=True):
            expected_adjacent[int(left), int(right)] += 1
        expected_changed = expected_adjacent.copy()
        np.fill_diagonal(expected_changed, 0)
        if not np.array_equal(adjacent, expected_adjacent) or not np.array_equal(
            changed, expected_changed
        ):
            raise TopologyStatisticsConsistencyError(
                "Transition-count matrices disagree with frame assignments."
            )
        if len(events) != int(np.sum(expected_changed, dtype=np.int64)):
            raise TopologyStatisticsConsistencyError(
                "Transition-event count disagrees with changed boundaries."
            )
        expected_boundaries = np.flatnonzero(assignments[1:] != assignments[:-1]) + 1
        for event, after in zip(events, expected_boundaries, strict=True):
            before = int(after) - 1
            if (
                event.result_position_before != before
                or event.result_position_after != int(after)
                or event.source_state_id != int(assignments[before])
                or event.target_state_id != int(assignments[int(after)])
            ):
                raise TopologyStatisticsConsistencyError(
                    "Transition-event records disagree with frame assignments."
                )
        if not isinstance(self.cumulative_changed_boundaries, ScalarSeries):
            raise TopologyStatisticsConsistencyError(
                "cumulative_changed_boundaries has the wrong type."
            )
        if self.cumulative_changed_boundaries.axis.to_dict() != self.axis.to_dict():
            raise TopologyStatisticsConsistencyError(
                "Cumulative event series does not use the result axis."
            )
        expected_cumulative = np.concatenate(
            [
                np.asarray([0], dtype=np.int64),
                np.cumsum(assignments[1:] != assignments[:-1], dtype=np.int64),
            ]
        )
        if not np.array_equal(
            self.cumulative_changed_boundaries.values, expected_cumulative
        ):
            raise TopologyStatisticsConsistencyError(
                "Cumulative event series disagrees with state assignments."
            )
        lengths = np.asarray([x.n_frames for x in intervals], dtype=np.int64)
        support, frequencies = np.unique(lengths, return_counts=True)
        if not np.array_equal(
            support, self.dwell_frame_distribution.support
        ) or not np.array_equal(frequencies, self.dwell_frame_distribution.frequencies):
            raise TopologyStatisticsConsistencyError(
                "Dwell-frame distribution disagrees with residence intervals."
            )
        if self.axis.times is None:
            if self.dwell_time_span_summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "Physical dwell spans require physical times."
                )
        elif self.dwell_time_span_summary is None:
            raise TopologyStatisticsConsistencyError(
                "Physical times require a dwell-time span summary."
            )
        if not isinstance(self.options, TemporalStatisticsOptions):
            raise TopologyStatisticsConsistencyError("options has the wrong type.")
        if (
            self.canonical_schema_version
            != CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA
        ):
            raise TopologyStatisticsConsistencyError(
                "Unsupported temporal-statistics schema version."
            )
        if self.digest_algorithm != TOPOLOGY_STATISTICS_DIGEST_ALGORITHM:
            raise TopologyStatisticsConsistencyError(
                "Unsupported temporal-statistics digest algorithm."
            )
        metadata = MappingProxyType(_deep_copy_mapping(self.metadata))
        object.__setattr__(self, "n_states", n_states)
        object.__setattr__(self, "frame_to_state_id", assignments)
        object.__setattr__(self, "residence_intervals", intervals)
        object.__setattr__(self, "state_residence_statistics", per_state)
        object.__setattr__(self, "transition_events", events)
        object.__setattr__(self, "adjacent_count_matrix", adjacent)
        object.__setattr__(self, "changed_count_matrix", changed)
        object.__setattr__(self, "metadata", metadata)
        expected_digest = _state_temporal_digest(self)
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise TopologyStatisticsConsistencyError(
                "Stored temporal-statistics digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    @property
    def n_frames(self) -> int:
        return self.axis.n_frames

    @property
    def n_intervals(self) -> int:
        return len(self.residence_intervals)

    @property
    def n_changed_boundaries(self) -> int:
        return len(self.transition_events)

    def state(self, state_id: int) -> StateResidenceStatistics:
        index = _nonnegative_int(state_id, "state_id")
        if index >= self.n_states:
            raise KeyError(f"State {index} is outside this result.")
        return self.state_residence_statistics[index]

    def to_dict(self) -> dict[str, Any]:
        return _state_temporal_payload(self, include_digest=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateTransitionStatistics":
        if (
            payload.get("schema_version")
            != CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA
        ):
            raise TopologyStatisticsSerializationError(
                "Unsupported temporal-statistics schema version."
            )
        if payload.get("object_type") != "StateTransitionStatistics":
            raise TopologyStatisticsSerializationError(
                "Payload is not a StateTransitionStatistics object."
            )
        try:
            return cls(
                axis=FrameAxis.from_dict(_mapping(payload["axis"], "axis")),
                n_states=int(payload["n_states"]),
                frame_to_state_id=np.asarray(
                    payload["frame_to_state_id"], dtype=np.int64
                ),
                residence_intervals=tuple(
                    StateResidenceInterval.from_dict(_mapping(x, "residence interval"))
                    for x in payload["residence_intervals"]
                ),
                state_residence_statistics=tuple(
                    StateResidenceStatistics.from_dict(
                        _mapping(x, "state residence statistics")
                    )
                    for x in payload["state_residence_statistics"]
                ),
                transition_events=tuple(
                    StateTransitionEvent.from_dict(_mapping(x, "transition event"))
                    for x in payload["transition_events"]
                ),
                adjacent_count_matrix=np.asarray(
                    payload["adjacent_count_matrix"], dtype=np.int64
                ),
                changed_count_matrix=np.asarray(
                    payload["changed_count_matrix"], dtype=np.int64
                ),
                cumulative_changed_boundaries=ScalarSeries.from_dict(
                    _mapping(
                        payload["cumulative_changed_boundaries"],
                        "cumulative_changed_boundaries",
                    )
                ),
                dwell_frame_distribution=DiscreteCountDistribution.from_dict(
                    _mapping(
                        payload["dwell_frame_distribution"], "dwell_frame_distribution"
                    )
                ),
                dwell_time_span_summary=None
                if payload["dwell_time_span_summary"] is None
                else ScalarSummary.from_dict(
                    _mapping(
                        payload["dwell_time_span_summary"], "dwell_time_span_summary"
                    )
                ),
                options=TemporalStatisticsOptions.from_dict(
                    _mapping(payload["options"], "options")
                ),
                metadata=_mapping(payload.get("metadata", {}), "metadata"),
                canonical_schema_version=str(payload["schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, TopologyStatisticsConsistencyError):
                raise
            raise TopologyStatisticsSerializationError(
                "Malformed StateTransitionStatistics payload."
            ) from exc


@dataclass(frozen=True, slots=True)
class EntityPresenceEpisode:
    """One maximal episode in which one dense entity ID is present."""

    episode_id: int
    entity_id: int
    result_position_start: int
    result_position_stop: int
    n_frames: int
    sample_span: int
    left_censored: bool
    right_censored: bool
    time_start: float | None = None
    time_end: float | None = None
    time_span: float | None = None

    def __post_init__(self) -> None:
        for name in (
            "episode_id",
            "entity_id",
            "result_position_start",
            "result_position_stop",
            "n_frames",
            "sample_span",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name))
        if self.result_position_stop <= self.result_position_start:
            raise TopologyStatisticsConsistencyError(
                "An entity episode must contain at least one frame."
            )
        if self.n_frames != self.result_position_stop - self.result_position_start:
            raise TopologyStatisticsConsistencyError(
                "Entity episode n_frames disagrees with its bounds."
            )
        if self.sample_span != self.n_frames - 1:
            raise TopologyStatisticsConsistencyError(
                "Entity episode sample_span must equal n_frames - 1."
            )
        if not isinstance(self.left_censored, (bool, np.bool_)) or not isinstance(
            self.right_censored, (bool, np.bool_)
        ):
            raise TopologyStatisticsConsistencyError(
                "Episode censoring flags must be boolean."
            )
        object.__setattr__(self, "left_censored", bool(self.left_censored))
        object.__setattr__(self, "right_censored", bool(self.right_censored))
        _validate_optional_axis_span(
            self.time_start, self.time_end, self.time_span, integer=False, label="time"
        )

    @property
    def result_position_end(self) -> int:
        return self.result_position_stop - 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "entity_id": self.entity_id,
            "result_position_start": self.result_position_start,
            "result_position_stop": self.result_position_stop,
            "n_frames": self.n_frames,
            "sample_span": self.sample_span,
            "left_censored": self.left_censored,
            "right_censored": self.right_censored,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "time_span": self.time_span,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EntityPresenceEpisode":
        return cls(**dict(payload))


@dataclass(frozen=True, slots=True)
class EntityPresenceStatistics:
    """Generic dense-entity episode statistics shared by atomic and framework layers."""

    axis: FrameAxis
    n_entities: int
    episodes: tuple[EntityPresenceEpisode, ...]
    entity_episode_counts: IntArray
    entity_total_frame_counts: IntArray
    entity_occupancy_probabilities: FloatArray
    episode_frame_length_distribution: DiscreteCountDistribution | None
    episode_time_span_summary: ScalarSummary | None
    options: TemporalStatisticsOptions
    metadata: Mapping[str, Any]
    canonical_schema_version: str = CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA
    digest_algorithm: str = TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        _require_trajectory_axis(self.axis)
        n_entities = _nonnegative_int(self.n_entities, "n_entities")
        episodes = tuple(self.episodes)
        if tuple(x.episode_id for x in episodes) != tuple(range(len(episodes))):
            raise TopologyStatisticsConsistencyError(
                "Entity episode IDs must be dense and ordered."
            )
        if any(x.entity_id >= n_entities for x in episodes):
            raise TopologyStatisticsConsistencyError(
                "An entity episode references an invalid entity ID."
            )
        episode_counts = _readonly_int_array(self.entity_episode_counts)
        frame_counts = _readonly_int_array(self.entity_total_frame_counts)
        probabilities = _readonly_float_array(self.entity_occupancy_probabilities)
        if any(
            array.size != n_entities
            for array in (episode_counts, frame_counts, probabilities)
        ):
            raise TopologyStatisticsConsistencyError(
                "Per-entity arrays must match n_entities."
            )
        if np.any(probabilities < 0.0) or np.any(probabilities > 1.0):
            raise TopologyStatisticsConsistencyError(
                "Entity occupancy probabilities must lie in [0, 1]."
            )
        expected_probabilities = frame_counts.astype(np.float64) / self.axis.n_frames
        if not np.allclose(probabilities, expected_probabilities, rtol=0.0, atol=1e-15):
            raise TopologyStatisticsConsistencyError(
                "Entity occupancy probabilities disagree with frame counts."
            )
        observed_counts = np.zeros(n_entities, dtype=np.int64)
        observed_frames = np.zeros(n_entities, dtype=np.int64)
        for episode in episodes:
            observed_counts[episode.entity_id] += 1
            observed_frames[episode.entity_id] += episode.n_frames
        if not np.array_equal(observed_counts, episode_counts) or not np.array_equal(
            observed_frames, frame_counts
        ):
            raise TopologyStatisticsConsistencyError(
                "Entity episode aggregates disagree with episode records."
            )
        if episodes:
            if self.episode_frame_length_distribution is None:
                raise TopologyStatisticsConsistencyError(
                    "Nonempty entity episodes require a length distribution."
                )
            if self.episode_frame_length_distribution.summary.count != len(episodes):
                raise TopologyStatisticsConsistencyError(
                    "Episode-length distribution count disagrees with episodes."
                )
        elif self.episode_frame_length_distribution is not None:
            raise TopologyStatisticsConsistencyError(
                "Empty entity episodes cannot have a length distribution."
            )
        if self.axis.times is None:
            if self.episode_time_span_summary is not None:
                raise TopologyStatisticsConsistencyError(
                    "Episode time spans require physical times."
                )
        elif episodes and self.episode_time_span_summary is None:
            raise TopologyStatisticsConsistencyError(
                "Physical times and nonempty episodes require a time-span summary."
            )
        if not isinstance(self.options, TemporalStatisticsOptions):
            raise TopologyStatisticsConsistencyError("options has the wrong type.")
        if (
            self.canonical_schema_version
            != CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA
            or self.digest_algorithm != TOPOLOGY_STATISTICS_DIGEST_ALGORITHM
        ):
            raise TopologyStatisticsConsistencyError(
                "Unsupported entity-episode schema or digest algorithm."
            )
        if (
            self.episode_time_span_summary is not None
            and self.episode_time_span_summary.count != len(episodes)
        ):
            raise TopologyStatisticsConsistencyError(
                "Episode time-span summary count disagrees with episodes."
            )
        metadata = MappingProxyType(_deep_copy_mapping(self.metadata))
        object.__setattr__(self, "n_entities", n_entities)
        object.__setattr__(self, "episodes", episodes)
        object.__setattr__(self, "entity_episode_counts", episode_counts)
        object.__setattr__(self, "entity_total_frame_counts", frame_counts)
        object.__setattr__(self, "entity_occupancy_probabilities", probabilities)
        object.__setattr__(self, "metadata", metadata)
        expected_digest = _entity_episode_digest(self)
        digest = self.digest or expected_digest
        if digest != expected_digest:
            raise TopologyStatisticsConsistencyError(
                "Stored entity-episode digest is inconsistent."
            )
        object.__setattr__(self, "digest", digest)

    def episodes_for(self, entity_id: int) -> tuple[EntityPresenceEpisode, ...]:
        target = _nonnegative_int(entity_id, "entity_id")
        if target >= self.n_entities:
            raise KeyError(f"Entity {target} is outside this result.")
        return tuple(x for x in self.episodes if x.entity_id == target)

    def to_dict(self) -> dict[str, Any]:
        return _entity_episode_payload(self, include_digest=True)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EntityPresenceStatistics":
        if (
            payload.get("schema_version")
            != CANONICAL_TEMPORAL_TOPOLOGY_STATISTICS_SCHEMA
        ):
            raise TopologyStatisticsSerializationError(
                "Unsupported temporal-statistics schema version."
            )
        if payload.get("object_type") != "EntityPresenceStatistics":
            raise TopologyStatisticsSerializationError(
                "Payload is not an EntityPresenceStatistics object."
            )
        try:
            return cls(
                axis=FrameAxis.from_dict(_mapping(payload["axis"], "axis")),
                n_entities=int(payload["n_entities"]),
                episodes=tuple(
                    EntityPresenceEpisode.from_dict(_mapping(x, "entity episode"))
                    for x in payload["episodes"]
                ),
                entity_episode_counts=np.asarray(
                    payload["entity_episode_counts"], dtype=np.int64
                ),
                entity_total_frame_counts=np.asarray(
                    payload["entity_total_frame_counts"], dtype=np.int64
                ),
                entity_occupancy_probabilities=np.asarray(
                    payload["entity_occupancy_probabilities"], dtype=np.float64
                ),
                episode_frame_length_distribution=None
                if payload["episode_frame_length_distribution"] is None
                else DiscreteCountDistribution.from_dict(
                    _mapping(
                        payload["episode_frame_length_distribution"],
                        "episode_frame_length_distribution",
                    )
                ),
                episode_time_span_summary=None
                if payload["episode_time_span_summary"] is None
                else ScalarSummary.from_dict(
                    _mapping(
                        payload["episode_time_span_summary"],
                        "episode_time_span_summary",
                    )
                ),
                options=TemporalStatisticsOptions.from_dict(
                    _mapping(payload["options"], "options")
                ),
                metadata=_mapping(payload.get("metadata", {}), "metadata"),
                canonical_schema_version=str(payload["schema_version"]),
                digest_algorithm=str(payload["digest_algorithm"]),
                digest=str(payload["digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            if isinstance(exc, TopologyStatisticsConsistencyError):
                raise
            raise TopologyStatisticsSerializationError(
                "Malformed EntityPresenceStatistics payload."
            ) from exc


def compute_state_transition_statistics(
    frame_to_state_id: ArrayLike,
    axis: FrameAxis,
    *,
    n_states: int | None = None,
    options: TemporalStatisticsOptions | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> StateTransitionStatistics:
    """Compute exact state residence and transition statistics for a trajectory."""

    _require_trajectory_axis(axis)
    effective = TemporalStatisticsOptions() if options is None else options
    if not isinstance(effective, TemporalStatisticsOptions):
        raise TypeError("options must be TemporalStatisticsOptions.")
    assignments = _strict_state_ids(frame_to_state_id)
    if assignments.size != axis.n_frames:
        raise TopologyStatisticsInputError(
            "frame_to_state_id must align with the supplied frame axis."
        )
    inferred = int(np.max(assignments)) + 1
    declared = inferred if n_states is None else _positive_int(n_states, "n_states")
    if inferred > declared:
        raise TopologyStatisticsInputError(
            "A frame state ID exceeds the declared state count."
        )

    intervals = _build_residence_intervals(assignments, axis)
    events = _build_transition_events(assignments, axis)
    adjacent = np.zeros((declared, declared), dtype=np.int64)
    for left, right in zip(assignments[:-1], assignments[1:], strict=True):
        adjacent[int(left), int(right)] += 1
    changed = adjacent.copy()
    np.fill_diagonal(changed, 0)
    cumulative = np.concatenate(
        [
            np.asarray([0], dtype=np.int64),
            np.cumsum(assignments[1:] != assignments[:-1], dtype=np.int64),
        ]
    )
    cumulative_series = build_scalar_series(
        "Cumulative changed-state boundaries",
        cumulative,
        axis,
        unit="events",
        quantiles=effective.quantiles,
    )
    dwell_lengths = np.asarray([x.n_frames for x in intervals], dtype=np.int64)
    dwell_distribution = compute_discrete_count_distribution(
        dwell_lengths, quantiles=effective.quantiles
    )
    dwell_time_summary = None
    if axis.times is not None:
        dwell_time_summary = compute_scalar_summary(
            [float(x.time_span) for x in intervals], quantiles=effective.quantiles
        )
    per_state = _build_state_residence_statistics(
        declared, intervals, axis, effective.quantiles
    )
    result_metadata = {
        "module": "topology_statistics.temporal",
        "stage": "TS3",
        "descriptive_only": True,
        "transition_events_exclude_self_boundaries": True,
        "adjacent_count_matrix_includes_self_boundaries": True,
        "duration_convention": "sample_span_between_first_and_last_stored_instants",
    }
    if metadata:
        result_metadata.update(_deep_copy_mapping(metadata))
    return StateTransitionStatistics(
        axis=axis,
        n_states=declared,
        frame_to_state_id=assignments,
        residence_intervals=intervals,
        state_residence_statistics=per_state,
        transition_events=events,
        adjacent_count_matrix=adjacent,
        changed_count_matrix=changed,
        cumulative_changed_boundaries=cumulative_series,
        dwell_frame_distribution=dwell_distribution,
        dwell_time_span_summary=dwell_time_summary,
        options=effective,
        metadata=result_metadata,
    )


def compute_entity_presence_statistics(
    state_entity_ids: Sequence[Sequence[int] | ArrayLike],
    frame_to_state_id: ArrayLike,
    axis: FrameAxis,
    *,
    n_entities: int | None = None,
    options: TemporalStatisticsOptions | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> EntityPresenceStatistics:
    """Compute exact episodes for dense integer entities attached to catalog states."""

    _require_trajectory_axis(axis)
    effective = TemporalStatisticsOptions() if options is None else options
    if not isinstance(effective, TemporalStatisticsOptions):
        raise TypeError("options must be TemporalStatisticsOptions.")
    assignments = _strict_state_ids(frame_to_state_id)
    if assignments.size != axis.n_frames:
        raise TopologyStatisticsInputError(
            "frame_to_state_id must align with the supplied frame axis."
        )
    states = tuple(_strict_entity_id_set(values) for values in state_entity_ids)
    if not states:
        raise TopologyStatisticsInputError("state_entity_ids cannot be empty.")
    if np.any(assignments >= len(states)):
        raise TopologyStatisticsInputError(
            "A frame state ID exceeds the state_entity_ids collection."
        )
    maximum = max((max(values) for values in states if values), default=-1) + 1
    declared = (
        maximum if n_entities is None else _nonnegative_int(n_entities, "n_entities")
    )
    if maximum > declared:
        raise TopologyStatisticsInputError(
            "An entity ID exceeds the declared entity count."
        )

    episodes = _build_entity_episodes(states, assignments, axis)
    episode_counts = np.zeros(declared, dtype=np.int64)
    frame_counts = np.zeros(declared, dtype=np.int64)
    for episode in episodes:
        episode_counts[episode.entity_id] += 1
        frame_counts[episode.entity_id] += episode.n_frames
    probabilities = frame_counts.astype(np.float64) / axis.n_frames
    length_distribution = None
    time_summary = None
    if episodes:
        length_distribution = compute_discrete_count_distribution(
            [x.n_frames for x in episodes], quantiles=effective.quantiles
        )
        if axis.times is not None:
            time_summary = compute_scalar_summary(
                [float(x.time_span) for x in episodes], quantiles=effective.quantiles
            )
    result_metadata = {
        "module": "topology_statistics.temporal",
        "stage": "TS3",
        "entity_identity": "dense_ids_defined_by_consuming_statistics_module",
        "episode_duration_convention": "sample_span_between_first_and_last_stored_instants",
        "censoring": "boundary flags only; no censoring-corrected survival estimator",
    }
    if metadata:
        result_metadata.update(_deep_copy_mapping(metadata))
    return EntityPresenceStatistics(
        axis=axis,
        n_entities=declared,
        episodes=episodes,
        entity_episode_counts=episode_counts,
        entity_total_frame_counts=frame_counts,
        entity_occupancy_probabilities=probabilities,
        episode_frame_length_distribution=length_distribution,
        episode_time_span_summary=time_summary,
        options=effective,
        metadata=result_metadata,
    )


def _build_residence_intervals(
    assignments: IntArray, axis: FrameAxis
) -> tuple[StateResidenceInterval, ...]:
    starts = [0]
    starts.extend(
        int(x) for x in np.flatnonzero(assignments[1:] != assignments[:-1]) + 1
    )
    stops = starts[1:] + [assignments.size]
    intervals = []
    for interval_id, (start, stop) in enumerate(zip(starts, stops, strict=True)):
        end = stop - 1
        intervals.append(
            StateResidenceInterval(
                interval_id=interval_id,
                state_id=int(assignments[start]),
                result_position_start=start,
                result_position_stop=stop,
                collection_frame_index_start=int(axis.collection_frame_indices[start]),
                collection_frame_index_end=int(axis.collection_frame_indices[end]),
                frame_id_start=int(axis.frame_ids[start]),
                frame_id_end=int(axis.frame_ids[end]),
                n_frames=stop - start,
                sample_span=end - start,
                step_start=None if axis.steps is None else int(axis.steps[start]),
                step_end=None if axis.steps is None else int(axis.steps[end]),
                step_span=None
                if axis.steps is None
                else int(axis.steps[end] - axis.steps[start]),
                time_start=None if axis.times is None else float(axis.times[start]),
                time_end=None if axis.times is None else float(axis.times[end]),
                time_span=None
                if axis.times is None
                else float(axis.times[end] - axis.times[start]),
            )
        )
    return tuple(intervals)


def _build_transition_events(
    assignments: IntArray, axis: FrameAxis
) -> tuple[StateTransitionEvent, ...]:
    boundaries = np.flatnonzero(assignments[1:] != assignments[:-1]) + 1
    events = []
    for transition_id, after in enumerate(boundaries):
        before = int(after) - 1
        after = int(after)
        events.append(
            StateTransitionEvent(
                transition_id=transition_id,
                result_position_before=before,
                result_position_after=after,
                source_state_id=int(assignments[before]),
                target_state_id=int(assignments[after]),
                collection_frame_index_before=int(
                    axis.collection_frame_indices[before]
                ),
                collection_frame_index_after=int(axis.collection_frame_indices[after]),
                frame_id_before=int(axis.frame_ids[before]),
                frame_id_after=int(axis.frame_ids[after]),
                step_before=None if axis.steps is None else int(axis.steps[before]),
                step_after=None if axis.steps is None else int(axis.steps[after]),
                time_before=None if axis.times is None else float(axis.times[before]),
                time_after=None if axis.times is None else float(axis.times[after]),
            )
        )
    return tuple(events)


def _build_state_residence_statistics(
    n_states: int,
    intervals: tuple[StateResidenceInterval, ...],
    axis: FrameAxis,
    quantiles: tuple[float, ...],
) -> tuple[StateResidenceStatistics, ...]:
    result = []
    for state_id in range(n_states):
        selected = [x for x in intervals if x.state_id == state_id]
        interval_ids = np.asarray([x.interval_id for x in selected], dtype=np.int64)
        total_frames = sum(x.n_frames for x in selected)
        length_distribution = None
        time_summary = None
        if selected:
            length_distribution = compute_discrete_count_distribution(
                [x.n_frames for x in selected], quantiles=quantiles
            )
            if axis.times is not None:
                time_summary = compute_scalar_summary(
                    [float(x.time_span) for x in selected], quantiles=quantiles
                )
        return_frames = np.asarray(
            [
                right.result_position_start - left.result_position_end
                for left, right in zip(selected, selected[1:])
            ],
            dtype=np.int64,
        )
        return_distribution = None
        if return_frames.size:
            return_distribution = compute_discrete_count_distribution(
                return_frames, quantiles=quantiles
            )
        return_times = None
        return_time_summary = None
        if axis.times is not None:
            return_times = np.asarray(
                [
                    float(right.time_start) - float(left.time_end)
                    for left, right in zip(selected, selected[1:])
                ],
                dtype=np.float64,
            )
            if return_times.size:
                return_time_summary = compute_scalar_summary(
                    return_times, quantiles=quantiles
                )
        result.append(
            StateResidenceStatistics(
                state_id=state_id,
                interval_ids=interval_ids,
                total_frames=total_frames,
                frame_length_distribution=length_distribution,
                time_span_summary=time_summary,
                return_frame_lags=return_frames,
                return_frame_lag_distribution=return_distribution,
                return_time_lags=return_times,
                return_time_lag_summary=return_time_summary,
            )
        )
    return tuple(result)


def _build_entity_episodes(
    state_entities: tuple[tuple[int, ...], ...], assignments: IntArray, axis: FrameAxis
) -> tuple[EntityPresenceEpisode, ...]:
    open_starts: dict[int, int] = {}
    records: list[tuple[int, int, int]] = []
    previous: set[int] = set()
    for position, state_id in enumerate(assignments):
        current = set(state_entities[int(state_id)])
        for entity_id in sorted(current - previous):
            open_starts[entity_id] = position
        for entity_id in sorted(previous - current):
            records.append((entity_id, open_starts.pop(entity_id), position))
        previous = current
    stop = assignments.size
    for entity_id in sorted(previous):
        records.append((entity_id, open_starts.pop(entity_id), stop))
    records.sort(key=lambda value: (value[1], value[0], value[2]))
    episodes = []
    for episode_id, (entity_id, start, stop) in enumerate(records):
        end = stop - 1
        episodes.append(
            EntityPresenceEpisode(
                episode_id=episode_id,
                entity_id=entity_id,
                result_position_start=start,
                result_position_stop=stop,
                n_frames=stop - start,
                sample_span=end - start,
                left_censored=start == 0,
                right_censored=stop == assignments.size,
                time_start=None if axis.times is None else float(axis.times[start]),
                time_end=None if axis.times is None else float(axis.times[end]),
                time_span=None
                if axis.times is None
                else float(axis.times[end] - axis.times[start]),
            )
        )
    return tuple(episodes)


def _state_temporal_payload(
    result: StateTransitionStatistics, *, include_digest: bool
) -> dict[str, Any]:
    payload = {
        "schema_version": result.canonical_schema_version,
        "object_type": "StateTransitionStatistics",
        "digest_algorithm": result.digest_algorithm,
        "axis": result.axis.to_dict(),
        "n_states": result.n_states,
        "frame_to_state_id": result.frame_to_state_id.tolist(),
        "residence_intervals": [x.to_dict() for x in result.residence_intervals],
        "state_residence_statistics": [
            x.to_dict() for x in result.state_residence_statistics
        ],
        "transition_events": [x.to_dict() for x in result.transition_events],
        "adjacent_count_matrix": result.adjacent_count_matrix.tolist(),
        "changed_count_matrix": result.changed_count_matrix.tolist(),
        "cumulative_changed_boundaries": result.cumulative_changed_boundaries.to_dict(),
        "dwell_frame_distribution": result.dwell_frame_distribution.to_dict(),
        "dwell_time_span_summary": None
        if result.dwell_time_span_summary is None
        else result.dwell_time_span_summary.to_dict(),
        "options": result.options.to_dict(),
        "metadata": _json_safe(dict(result.metadata)),
    }
    if include_digest:
        payload["digest"] = result.digest
    return payload


def _state_temporal_digest(result: StateTransitionStatistics) -> str:
    encoded = canonical_statistics_json(
        _state_temporal_payload(result, include_digest=False)
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _entity_episode_payload(
    result: EntityPresenceStatistics, *, include_digest: bool
) -> dict[str, Any]:
    payload = {
        "schema_version": result.canonical_schema_version,
        "object_type": "EntityPresenceStatistics",
        "digest_algorithm": result.digest_algorithm,
        "axis": result.axis.to_dict(),
        "n_entities": result.n_entities,
        "episodes": [x.to_dict() for x in result.episodes],
        "entity_episode_counts": result.entity_episode_counts.tolist(),
        "entity_total_frame_counts": result.entity_total_frame_counts.tolist(),
        "entity_occupancy_probabilities": result.entity_occupancy_probabilities.tolist(),
        "episode_frame_length_distribution": None
        if result.episode_frame_length_distribution is None
        else result.episode_frame_length_distribution.to_dict(),
        "episode_time_span_summary": None
        if result.episode_time_span_summary is None
        else result.episode_time_span_summary.to_dict(),
        "options": result.options.to_dict(),
        "metadata": _json_safe(dict(result.metadata)),
    }
    if include_digest:
        payload["digest"] = result.digest
    return payload


def _entity_episode_digest(result: EntityPresenceStatistics) -> str:
    encoded = canonical_statistics_json(
        _entity_episode_payload(result, include_digest=False)
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_trajectory_axis(axis: FrameAxis) -> None:
    if not isinstance(axis, FrameAxis):
        raise TypeError("axis must be a FrameAxis.")
    if axis.frame_semantics is not FrameSemantics.TRAJECTORY:
        raise TopologyStatisticsInputError(
            "Temporal topology statistics require trajectory semantics; ensemble order is not time."
        )


def _strict_state_ids(values: ArrayLike) -> IntArray:
    array = np.asarray(values)
    if array.ndim != 1 or array.size == 0:
        raise TopologyStatisticsInputError(
            "State assignments must be a nonempty one-dimensional array."
        )
    if array.dtype.kind not in "iu" or array.dtype.kind == "b":
        raise TopologyStatisticsInputError("State assignments must be integers.")
    result = np.asarray(array, dtype=np.int64)
    if np.any(result < 0):
        raise TopologyStatisticsInputError("State assignments must be nonnegative.")
    result = np.array(result, copy=True)
    result.setflags(write=False)
    return result


def _strict_entity_id_set(values: Sequence[int] | ArrayLike) -> tuple[int, ...]:
    array = np.asarray(values)
    if array.size == 0:
        return ()
    if array.ndim != 1 or array.dtype.kind not in "iu" or array.dtype.kind == "b":
        raise TopologyStatisticsInputError(
            "Each state entity collection must contain integer IDs."
        )
    result = tuple(sorted({int(value) for value in array}))
    if result and result[0] < 0:
        raise TopologyStatisticsInputError("Entity IDs must be nonnegative.")
    return result


def _readonly_int_array(values: ArrayLike) -> IntArray:
    array = np.asarray(values)
    if array.ndim != 1 or array.dtype.kind not in "iu" or array.dtype.kind == "b":
        raise TopologyStatisticsConsistencyError(
            "Expected a one-dimensional integer array."
        )
    result = np.asarray(array, dtype=np.int64).copy()
    result.setflags(write=False)
    return result


def _readonly_float_array(values: ArrayLike) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise TopologyStatisticsConsistencyError(
            "Expected a finite one-dimensional float array."
        )
    result = array.copy()
    result.setflags(write=False)
    return result


def _readonly_int_matrix(values: ArrayLike, size: int) -> IntArray:
    array = np.asarray(values)
    if (
        array.shape != (size, size)
        or array.dtype.kind not in "iu"
        or array.dtype.kind == "b"
    ):
        raise TopologyStatisticsConsistencyError(
            f"Expected an integer matrix with shape ({size}, {size})."
        )
    result = np.asarray(array, dtype=np.int64).copy()
    if np.any(result < 0):
        raise TopologyStatisticsConsistencyError("Count matrices cannot be negative.")
    result.setflags(write=False)
    return result


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


def _validate_optional_axis_span(
    start: Any, end: Any, span: Any, *, integer: bool, label: str
) -> None:
    values = (start, end, span)
    if all(value is None for value in values):
        return
    if any(value is None for value in values):
        raise TopologyStatisticsConsistencyError(
            f"{label} start, end, and span must be supplied together."
        )
    if integer:
        start_value = int(start)
        end_value = int(end)
        span_value = int(span)
    else:
        start_value = _finite_float(start, f"{label}_start")
        end_value = _finite_float(end, f"{label}_end")
        span_value = _finite_float(span, f"{label}_span")
    if end_value < start_value or not np.isclose(
        span_value, end_value - start_value, rtol=0.0, atol=1e-12
    ):
        raise TopologyStatisticsConsistencyError(
            f"{label} span must equal end - start and cannot be negative."
        )


def _positive_int(value: Any, name: str) -> int:
    result = _nonnegative_int(value, name)
    if result == 0:
        raise TopologyStatisticsConsistencyError(f"{name} must be positive.")
    return result


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise TopologyStatisticsConsistencyError(f"{name} must be an integer.")
    result = int(value)
    if result < 0:
        raise TopologyStatisticsConsistencyError(f"{name} must be nonnegative.")
    return result


def _finite_float(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result):
        raise TopologyStatisticsConsistencyError(f"{name} must be finite.")
    return result


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TopologyStatisticsSerializationError(f"{name} must be a mapping.")
    return value


def _deep_copy_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): _deep_copy_value(item) for key, item in value.items()}


def _deep_copy_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return _deep_copy_mapping(value)
    if isinstance(value, tuple):
        return tuple(_deep_copy_value(x) for x in value)
    if isinstance(value, list):
        return tuple(_deep_copy_value(x) for x in value)
    if isinstance(value, np.ndarray):
        return tuple(_deep_copy_value(x) for x in value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value
