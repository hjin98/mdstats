"""Graph-independent statistical primitives for topology-derived analysis.

This private module is the TS0 foundation for atomic-connectivity and framework-
topology statistics.  It owns exact discrete distributions, descriptive scalar
summaries, catalog occupancy statistics, frame/time axes, immutable scalar
series, and deterministic state-to-frame expansion.

The module deliberately knows nothing about atomic edges, projected framework
edges, chemical species, ring identities, or transition mechanisms.  Later
statistics modules consume these primitives without redefining graph identity.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike, NDArray

from ...semantics import FrameSemantics, coerce_frame_semantics

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]
NumericArray = NDArray[np.int64] | NDArray[np.float64]

CANONICAL_TOPOLOGY_STATISTICS_COMMON_SCHEMA = "mdstats.topology-statistics.common.v1"
TOPOLOGY_STATISTICS_DIGEST_ALGORITHM = "sha256"
DEFAULT_QUANTILES = (0.0, 0.25, 0.5, 0.75, 1.0)


class TopologyStatisticsError(ValueError):
    """Base class for topology-statistics validation failures."""


class TopologyStatisticsInputError(TopologyStatisticsError):
    """Raised when a statistical input or axis is malformed."""


class TopologyStatisticsConsistencyError(TopologyStatisticsError):
    """Raised when a result object's arrays or summaries disagree."""


class TopologyStatisticsSerializationError(TopologyStatisticsError):
    """Raised when serialized common-statistics data are incompatible."""


@dataclass(frozen=True, slots=True)
class ScalarSummary:
    """Descriptive population statistics for one nonempty scalar sample.

    ``population_standard_deviation`` uses ``ddof=0`` because the object
    summarizes the analyzed collection itself.  It is not an uncertainty
    estimate for an independent parent population.
    """

    count: int
    mean: float
    population_standard_deviation: float
    minimum: float
    maximum: float
    median: float
    quantile_probabilities: FloatArray
    quantile_values: FloatArray
    is_constant: bool

    def __post_init__(self) -> None:
        count = _positive_int(self.count, name="count")
        scalars = {
            "mean": self.mean,
            "population_standard_deviation": self.population_standard_deviation,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "median": self.median,
        }
        normalized = {
            name: _finite_float(value, name=name) for name, value in scalars.items()
        }
        if normalized["population_standard_deviation"] < 0.0:
            raise TopologyStatisticsConsistencyError(
                "population_standard_deviation cannot be negative."
            )
        if normalized["minimum"] > normalized["maximum"]:
            raise TopologyStatisticsConsistencyError("minimum cannot exceed maximum.")
        tolerance = _scale_tolerance(
            normalized["minimum"], normalized["median"], normalized["maximum"]
        )
        if not (
            normalized["minimum"] - tolerance
            <= normalized["median"]
            <= normalized["maximum"] + tolerance
        ):
            raise TopologyStatisticsConsistencyError(
                "median must lie between minimum and maximum."
            )

        probabilities = _validated_quantiles(self.quantile_probabilities)
        values = _readonly_float_array(self.quantile_values, ndim=1, finite=True)
        if values.shape != probabilities.shape:
            raise TopologyStatisticsConsistencyError(
                "quantile_values must match quantile_probabilities."
            )
        if np.any(np.diff(values) < -tolerance):
            raise TopologyStatisticsConsistencyError(
                "quantile_values must be nondecreasing."
            )
        if values.size:
            if not np.isclose(
                values[0], normalized["minimum"], rtol=0.0, atol=tolerance
            ):
                raise TopologyStatisticsConsistencyError(
                    "The zero quantile must equal the minimum."
                )
            if not np.isclose(
                values[-1], normalized["maximum"], rtol=0.0, atol=tolerance
            ):
                raise TopologyStatisticsConsistencyError(
                    "The unit quantile must equal the maximum."
                )

        is_constant = _strict_bool(self.is_constant, name="is_constant")
        expected_constant = normalized["minimum"] == normalized["maximum"]
        if is_constant != expected_constant:
            raise TopologyStatisticsConsistencyError(
                "is_constant disagrees with minimum and maximum."
            )
        if is_constant and normalized["population_standard_deviation"] != 0.0:
            raise TopologyStatisticsConsistencyError(
                "A constant sample must have zero population standard deviation."
            )

        object.__setattr__(self, "count", count)
        for name, value in normalized.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "quantile_probabilities", probabilities)
        object.__setattr__(self, "quantile_values", values)
        object.__setattr__(self, "is_constant", is_constant)

    def to_dict(self) -> dict[str, Any]:
        return _typed_payload(
            "ScalarSummary",
            {
                "count": self.count,
                "mean": self.mean,
                "population_standard_deviation": self.population_standard_deviation,
                "minimum": self.minimum,
                "maximum": self.maximum,
                "median": self.median,
                "quantile_probabilities": self.quantile_probabilities.tolist(),
                "quantile_values": self.quantile_values.tolist(),
                "is_constant": self.is_constant,
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ScalarSummary":
        _validate_typed_payload(payload, "ScalarSummary")
        return cls(
            count=int(payload["count"]),
            mean=float(payload["mean"]),
            population_standard_deviation=float(
                payload["population_standard_deviation"]
            ),
            minimum=float(payload["minimum"]),
            maximum=float(payload["maximum"]),
            median=float(payload["median"]),
            quantile_probabilities=np.asarray(
                payload["quantile_probabilities"], dtype=np.float64
            ),
            quantile_values=np.asarray(payload["quantile_values"], dtype=np.float64),
            is_constant=payload["is_constant"],
        )


@dataclass(frozen=True, slots=True)
class DiscreteCountDistribution:
    """Exact probability mass function for nonnegative integer counts."""

    support: IntArray
    frequencies: IntArray
    probabilities: FloatArray
    summary: ScalarSummary
    modes: tuple[int, ...]

    def __post_init__(self) -> None:
        support = _readonly_int_array(self.support, ndim=1)
        frequencies = _readonly_int_array(self.frequencies, ndim=1)
        probabilities = _readonly_float_array(self.probabilities, ndim=1, finite=True)
        if (
            support.size == 0
            or support.shape != frequencies.shape
            or support.shape != probabilities.shape
        ):
            raise TopologyStatisticsConsistencyError(
                "support, frequencies, and probabilities must be nonempty and aligned."
            )
        if np.any(support < 0) or np.any(np.diff(support) <= 0):
            raise TopologyStatisticsConsistencyError(
                "support must contain strictly increasing nonnegative counts."
            )
        if np.any(frequencies <= 0):
            raise TopologyStatisticsConsistencyError("frequencies must be positive.")
        if np.any(probabilities < 0.0):
            raise TopologyStatisticsConsistencyError(
                "probabilities cannot be negative."
            )
        total = int(np.sum(frequencies, dtype=np.int64))
        expected_probabilities = frequencies.astype(np.float64) / total
        if not np.allclose(probabilities, expected_probabilities, rtol=0.0, atol=1e-15):
            raise TopologyStatisticsConsistencyError(
                "probabilities disagree with integer frequencies."
            )
        if not isinstance(self.summary, ScalarSummary):
            raise TopologyStatisticsConsistencyError("summary has the wrong type.")
        if self.summary.count != total:
            raise TopologyStatisticsConsistencyError(
                "summary count disagrees with distribution frequency."
            )
        expected_mean = float(np.dot(support.astype(np.float64), probabilities))
        if not np.isclose(self.summary.mean, expected_mean, rtol=0.0, atol=1e-13):
            raise TopologyStatisticsConsistencyError(
                "summary mean disagrees with the exact distribution."
            )
        if self.summary.minimum != float(support[0]) or self.summary.maximum != float(
            support[-1]
        ):
            raise TopologyStatisticsConsistencyError(
                "summary extrema disagree with the exact support."
            )

        modes = tuple(_nonnegative_int(value, name="mode") for value in self.modes)
        if not modes or tuple(sorted(set(modes))) != modes:
            raise TopologyStatisticsConsistencyError(
                "modes must be a nonempty sorted tuple of unique counts."
            )
        maximum_frequency = int(np.max(frequencies))
        expected_modes = tuple(
            int(value) for value in support[frequencies == maximum_frequency]
        )
        if modes != expected_modes:
            raise TopologyStatisticsConsistencyError(
                "modes disagree with the maximum-frequency support values."
            )

        object.__setattr__(self, "support", support)
        object.__setattr__(self, "frequencies", frequencies)
        object.__setattr__(self, "probabilities", probabilities)
        object.__setattr__(self, "modes", modes)

    @property
    def n_observations(self) -> int:
        return self.summary.count

    @property
    def n_support_values(self) -> int:
        return int(self.support.size)

    @property
    def is_constant(self) -> bool:
        return self.summary.is_constant

    def frequency_for(self, count: int) -> int:
        value = _nonnegative_int(count, name="count")
        position = int(np.searchsorted(self.support, value))
        if position >= self.support.size or int(self.support[position]) != value:
            return 0
        return int(self.frequencies[position])

    def probability_for(self, count: int) -> float:
        value = _nonnegative_int(count, name="count")
        position = int(np.searchsorted(self.support, value))
        if position >= self.support.size or int(self.support[position]) != value:
            return 0.0
        return float(self.probabilities[position])

    def to_dict(self) -> dict[str, Any]:
        return _typed_payload(
            "DiscreteCountDistribution",
            {
                "support": self.support.tolist(),
                "frequencies": self.frequencies.tolist(),
                "probabilities": self.probabilities.tolist(),
                "summary": self.summary.to_dict(),
                "modes": list(self.modes),
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DiscreteCountDistribution":
        _validate_typed_payload(payload, "DiscreteCountDistribution")
        return cls(
            support=np.asarray(payload["support"], dtype=np.int64),
            frequencies=np.asarray(payload["frequencies"], dtype=np.int64),
            probabilities=np.asarray(payload["probabilities"], dtype=np.float64),
            summary=ScalarSummary.from_dict(
                _mapping(payload["summary"], name="summary")
            ),
            modes=tuple(int(value) for value in payload["modes"]),
        )


@dataclass(frozen=True, slots=True)
class StateFrameGroup:
    """Selected result positions assigned to one dense catalog state ID."""

    state_id: int
    result_positions: IntArray

    def __post_init__(self) -> None:
        state_id = _nonnegative_int(self.state_id, name="state_id")
        positions = _readonly_int_array(self.result_positions, ndim=1)
        if positions.size and (
            np.any(positions < 0) or np.any(np.diff(positions) <= 0)
        ):
            raise TopologyStatisticsConsistencyError(
                "result_positions must be strictly increasing and nonnegative."
            )
        object.__setattr__(self, "state_id", state_id)
        object.__setattr__(self, "result_positions", positions)

    @property
    def frame_count(self) -> int:
        return int(self.result_positions.size)

    @property
    def first_result_position(self) -> int | None:
        return (
            None if self.result_positions.size == 0 else int(self.result_positions[0])
        )

    @property
    def last_result_position(self) -> int | None:
        return (
            None if self.result_positions.size == 0 else int(self.result_positions[-1])
        )

    def to_dict(self) -> dict[str, Any]:
        return _typed_payload(
            "StateFrameGroup",
            {
                "state_id": self.state_id,
                "result_positions": self.result_positions.tolist(),
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateFrameGroup":
        _validate_typed_payload(payload, "StateFrameGroup")
        return cls(
            state_id=int(payload["state_id"]),
            result_positions=np.asarray(payload["result_positions"], dtype=np.int64),
        )


@dataclass(frozen=True, slots=True)
class CatalogOccupancyStatistics:
    """Collection-wide occupancy and diversity of dense catalog state IDs."""

    frame_semantics: FrameSemantics
    frame_to_state_id: IntArray
    state_frame_counts: IntArray
    state_probabilities: FloatArray
    first_result_positions: IntArray
    last_result_positions: IntArray
    visit_counts: IntArray | None
    frame_groups: tuple[StateFrameGroup, ...]
    dominant_state_ids: tuple[int, ...]
    singleton_state_ids: tuple[int, ...]
    shannon_state_entropy: float
    effective_state_count: float

    def __post_init__(self) -> None:
        semantics = coerce_frame_semantics(self.frame_semantics)
        frame_ids = _readonly_int_array(self.frame_to_state_id, ndim=1)
        counts = _readonly_int_array(self.state_frame_counts, ndim=1)
        probabilities = _readonly_float_array(
            self.state_probabilities, ndim=1, finite=True
        )
        first = _readonly_int_array(self.first_result_positions, ndim=1)
        last = _readonly_int_array(self.last_result_positions, ndim=1)
        if frame_ids.size == 0 or counts.size == 0:
            raise TopologyStatisticsConsistencyError(
                "Catalog occupancy requires at least one frame and one declared state."
            )
        if any(array.shape != counts.shape for array in (probabilities, first, last)):
            raise TopologyStatisticsConsistencyError(
                "State-level occupancy arrays must have equal shape."
            )
        if np.any(frame_ids < 0) or np.any(frame_ids >= counts.size):
            raise TopologyStatisticsConsistencyError(
                "frame_to_state_id contains an invalid dense state ID."
            )
        expected_counts = np.bincount(frame_ids, minlength=counts.size).astype(np.int64)
        if not np.array_equal(counts, expected_counts):
            raise TopologyStatisticsConsistencyError(
                "state_frame_counts disagree with frame_to_state_id."
            )
        expected_probabilities = counts.astype(np.float64) / frame_ids.size
        if not np.allclose(probabilities, expected_probabilities, rtol=0.0, atol=1e-15):
            raise TopologyStatisticsConsistencyError(
                "state_probabilities disagree with state_frame_counts."
            )
        expected_first = np.full(counts.size, -1, dtype=np.int64)
        expected_last = np.full(counts.size, -1, dtype=np.int64)
        for state_id in range(counts.size):
            positions = np.flatnonzero(frame_ids == state_id)
            if positions.size:
                expected_first[state_id] = int(positions[0])
                expected_last[state_id] = int(positions[-1])
        if not np.array_equal(first, expected_first) or not np.array_equal(
            last, expected_last
        ):
            raise TopologyStatisticsConsistencyError(
                "First/last positions disagree with frame assignments."
            )

        groups = tuple(self.frame_groups)
        if len(groups) != counts.size or tuple(
            group.state_id for group in groups
        ) != tuple(range(counts.size)):
            raise TopologyStatisticsConsistencyError(
                "frame_groups must contain one dense, state-ID-ordered group per state."
            )
        for group in groups:
            expected = np.flatnonzero(frame_ids == group.state_id).astype(np.int64)
            if not np.array_equal(group.result_positions, expected):
                raise TopologyStatisticsConsistencyError(
                    "A frame group disagrees with frame_to_state_id."
                )

        visits: IntArray | None
        if semantics is FrameSemantics.TRAJECTORY:
            if self.visit_counts is None:
                raise TopologyStatisticsConsistencyError(
                    "Trajectory occupancy requires visit_counts."
                )
            visits = _readonly_int_array(self.visit_counts, ndim=1)
            if visits.shape != counts.shape:
                raise TopologyStatisticsConsistencyError(
                    "visit_counts must align with declared states."
                )
            expected_visits = _trajectory_visit_counts(frame_ids, counts.size)
            if not np.array_equal(visits, expected_visits):
                raise TopologyStatisticsConsistencyError(
                    "visit_counts disagree with trajectory state runs."
                )
        else:
            if self.visit_counts is not None:
                raise TopologyStatisticsConsistencyError(
                    "Ensemble occupancy cannot assign temporal visit counts."
                )
            visits = None

        dominant = tuple(
            _nonnegative_int(value, name="dominant state ID")
            for value in self.dominant_state_ids
        )
        singleton = tuple(
            _nonnegative_int(value, name="singleton state ID")
            for value in self.singleton_state_ids
        )
        if tuple(sorted(set(dominant))) != dominant or not dominant:
            raise TopologyStatisticsConsistencyError(
                "dominant_state_ids must be a nonempty sorted unique tuple."
            )
        if tuple(sorted(set(singleton))) != singleton:
            raise TopologyStatisticsConsistencyError(
                "singleton_state_ids must be sorted and unique."
            )
        expected_dominant = tuple(
            int(value) for value in np.flatnonzero(counts == np.max(counts))
        )
        expected_singleton = tuple(int(value) for value in np.flatnonzero(counts == 1))
        if dominant != expected_dominant or singleton != expected_singleton:
            raise TopologyStatisticsConsistencyError(
                "Dominant or singleton state IDs disagree with frame counts."
            )

        entropy = _finite_float(
            self.shannon_state_entropy, name="shannon_state_entropy"
        )
        effective = _finite_float(
            self.effective_state_count, name="effective_state_count"
        )
        if entropy < 0.0 or effective < 1.0:
            raise TopologyStatisticsConsistencyError(
                "Entropy must be nonnegative and effective_state_count at least one."
            )
        positive = probabilities[probabilities > 0.0]
        expected_entropy = float(-np.sum(positive * np.log(positive)))
        expected_effective = float(np.exp(expected_entropy))
        if not np.isclose(entropy, expected_entropy, rtol=0.0, atol=1e-14):
            raise TopologyStatisticsConsistencyError(
                "shannon_state_entropy disagrees with state probabilities."
            )
        if not np.isclose(effective, expected_effective, rtol=0.0, atol=1e-14):
            raise TopologyStatisticsConsistencyError(
                "effective_state_count disagrees with Shannon entropy."
            )

        object.__setattr__(self, "frame_semantics", semantics)
        object.__setattr__(self, "frame_to_state_id", frame_ids)
        object.__setattr__(self, "state_frame_counts", counts)
        object.__setattr__(self, "state_probabilities", probabilities)
        object.__setattr__(self, "first_result_positions", first)
        object.__setattr__(self, "last_result_positions", last)
        object.__setattr__(self, "visit_counts", visits)
        object.__setattr__(self, "frame_groups", groups)
        object.__setattr__(self, "dominant_state_ids", dominant)
        object.__setattr__(self, "singleton_state_ids", singleton)
        object.__setattr__(self, "shannon_state_entropy", entropy)
        object.__setattr__(self, "effective_state_count", effective)

    @property
    def n_frames(self) -> int:
        return int(self.frame_to_state_id.size)

    @property
    def n_states(self) -> int:
        return int(self.state_frame_counts.size)

    @property
    def n_observed_states(self) -> int:
        return int(np.count_nonzero(self.state_frame_counts))

    @property
    def unobserved_state_ids(self) -> tuple[int, ...]:
        return tuple(
            int(value) for value in np.flatnonzero(self.state_frame_counts == 0)
        )

    def to_dict(self) -> dict[str, Any]:
        return _typed_payload(
            "CatalogOccupancyStatistics",
            {
                "frame_semantics": self.frame_semantics.value,
                "frame_to_state_id": self.frame_to_state_id.tolist(),
                "state_frame_counts": self.state_frame_counts.tolist(),
                "state_probabilities": self.state_probabilities.tolist(),
                "first_result_positions": self.first_result_positions.tolist(),
                "last_result_positions": self.last_result_positions.tolist(),
                "visit_counts": None
                if self.visit_counts is None
                else self.visit_counts.tolist(),
                "frame_groups": [group.to_dict() for group in self.frame_groups],
                "dominant_state_ids": list(self.dominant_state_ids),
                "singleton_state_ids": list(self.singleton_state_ids),
                "shannon_state_entropy": self.shannon_state_entropy,
                "effective_state_count": self.effective_state_count,
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CatalogOccupancyStatistics":
        _validate_typed_payload(payload, "CatalogOccupancyStatistics")
        raw_visits = payload["visit_counts"]
        return cls(
            frame_semantics=FrameSemantics(payload["frame_semantics"]),
            frame_to_state_id=np.asarray(payload["frame_to_state_id"], dtype=np.int64),
            state_frame_counts=np.asarray(
                payload["state_frame_counts"], dtype=np.int64
            ),
            state_probabilities=np.asarray(
                payload["state_probabilities"], dtype=np.float64
            ),
            first_result_positions=np.asarray(
                payload["first_result_positions"], dtype=np.int64
            ),
            last_result_positions=np.asarray(
                payload["last_result_positions"], dtype=np.int64
            ),
            visit_counts=(
                None if raw_visits is None else np.asarray(raw_visits, dtype=np.int64)
            ),
            frame_groups=tuple(
                StateFrameGroup.from_dict(_mapping(item, name="frame_group"))
                for item in payload["frame_groups"]
            ),
            dominant_state_ids=tuple(
                int(value) for value in payload["dominant_state_ids"]
            ),
            singleton_state_ids=tuple(
                int(value) for value in payload["singleton_state_ids"]
            ),
            shannon_state_entropy=float(payload["shannon_state_entropy"]),
            effective_state_count=float(payload["effective_state_count"]),
        )


@dataclass(frozen=True, slots=True)
class FrameAxis:
    """Immutable alignment metadata for per-frame or per-sample statistics."""

    frame_semantics: FrameSemantics
    collection_frame_indices: IntArray
    frame_ids: IntArray
    steps: IntArray | None = None
    times: FloatArray | None = None
    time_unit: str | None = None

    def __post_init__(self) -> None:
        semantics = coerce_frame_semantics(self.frame_semantics)
        indices = _readonly_int_array(self.collection_frame_indices, ndim=1)
        frame_ids = _readonly_int_array(self.frame_ids, ndim=1)
        if indices.size == 0 or frame_ids.shape != indices.shape:
            raise TopologyStatisticsConsistencyError(
                "Frame axis arrays must be equal, one-dimensional, and nonempty."
            )
        if (
            np.any(indices < 0)
            or len(set(int(value) for value in indices)) != indices.size
        ):
            raise TopologyStatisticsConsistencyError(
                "collection_frame_indices must be unique and nonnegative."
            )
        if len(set(int(value) for value in frame_ids)) != frame_ids.size:
            raise TopologyStatisticsConsistencyError("frame_ids must be unique.")
        if semantics is FrameSemantics.TRAJECTORY and np.any(np.diff(indices) <= 0):
            raise TopologyStatisticsConsistencyError(
                "Trajectory collection_frame_indices must be strictly increasing."
            )

        steps: IntArray | None
        times: FloatArray | None
        unit: str | None
        if semantics is FrameSemantics.ENSEMBLE:
            if (
                self.steps is not None
                or self.times is not None
                or self.time_unit is not None
            ):
                raise TopologyStatisticsConsistencyError(
                    "Ensemble axes cannot carry trajectory steps or physical times."
                )
            steps = None
            times = None
            unit = None
        else:
            steps = (
                None if self.steps is None else _readonly_int_array(self.steps, ndim=1)
            )
            if steps is not None:
                if steps.shape != indices.shape or np.any(np.diff(steps) <= 0):
                    raise TopologyStatisticsConsistencyError(
                        "Trajectory steps must align with frames and be strictly increasing."
                    )
            times = (
                None
                if self.times is None
                else _readonly_float_array(self.times, ndim=1, finite=True)
            )
            if times is not None:
                if times.shape != indices.shape or np.any(np.diff(times) <= 0.0):
                    raise TopologyStatisticsConsistencyError(
                        "Trajectory times must align with frames and be strictly increasing."
                    )
                if self.time_unit is None or not str(self.time_unit).strip():
                    raise TopologyStatisticsConsistencyError(
                        "time_unit is required when physical times are supplied."
                    )
                unit = str(self.time_unit).strip()
            else:
                if self.time_unit is not None:
                    raise TopologyStatisticsConsistencyError(
                        "time_unit cannot be supplied without physical times."
                    )
                unit = None

        object.__setattr__(self, "frame_semantics", semantics)
        object.__setattr__(self, "collection_frame_indices", indices)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "steps", steps)
        object.__setattr__(self, "times", times)
        object.__setattr__(self, "time_unit", unit)

    @property
    def n_frames(self) -> int:
        return int(self.collection_frame_indices.size)

    @property
    def result_positions(self) -> IntArray:
        values = np.arange(self.n_frames, dtype=np.int64)
        values.setflags(write=False)
        return values

    @property
    def has_physical_time(self) -> bool:
        return self.times is not None

    @property
    def x_values(self) -> NumericArray:
        if self.times is not None:
            values: NumericArray = self.times.copy()
        elif self.steps is not None:
            values = self.steps.copy()
        else:
            values = self.result_positions
        values.setflags(write=False)
        return values

    @property
    def x_label(self) -> str:
        if self.times is not None:
            return f"Time ({self.time_unit})"
        if self.steps is not None:
            return "Simulation step"
        return (
            "Frame index"
            if self.frame_semantics is FrameSemantics.TRAJECTORY
            else "Sample index"
        )

    def to_dict(self) -> dict[str, Any]:
        return _typed_payload(
            "FrameAxis",
            {
                "frame_semantics": self.frame_semantics.value,
                "collection_frame_indices": self.collection_frame_indices.tolist(),
                "frame_ids": self.frame_ids.tolist(),
                "steps": None if self.steps is None else self.steps.tolist(),
                "times": None if self.times is None else self.times.tolist(),
                "time_unit": self.time_unit,
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameAxis":
        _validate_typed_payload(payload, "FrameAxis")
        raw_steps = payload["steps"]
        raw_times = payload["times"]
        return cls(
            frame_semantics=FrameSemantics(payload["frame_semantics"]),
            collection_frame_indices=np.asarray(
                payload["collection_frame_indices"], dtype=np.int64
            ),
            frame_ids=np.asarray(payload["frame_ids"], dtype=np.int64),
            steps=None if raw_steps is None else np.asarray(raw_steps, dtype=np.int64),
            times=None
            if raw_times is None
            else np.asarray(raw_times, dtype=np.float64),
            time_unit=payload["time_unit"],
        )


@dataclass(frozen=True, slots=True)
class ScalarSeries:
    """One immutable scalar descriptor aligned with a :class:`FrameAxis`."""

    name: str
    values: NumericArray
    axis: FrameAxis
    summary: ScalarSummary
    unit: str | None = None

    def __post_init__(self) -> None:
        name = str(self.name).strip()
        if not name:
            raise TopologyStatisticsConsistencyError(
                "ScalarSeries name cannot be empty."
            )
        values = _readonly_numeric_array(self.values, ndim=1, finite=True)
        if not isinstance(self.axis, FrameAxis):
            raise TopologyStatisticsConsistencyError("axis has the wrong type.")
        if values.size != self.axis.n_frames:
            raise TopologyStatisticsConsistencyError(
                "ScalarSeries values must align with the frame axis."
            )
        if not isinstance(self.summary, ScalarSummary):
            raise TopologyStatisticsConsistencyError("summary has the wrong type.")
        expected = compute_scalar_summary(
            values, quantiles=self.summary.quantile_probabilities
        )
        if not _scalar_summaries_equal(self.summary, expected):
            raise TopologyStatisticsConsistencyError(
                "ScalarSeries summary disagrees with values."
            )
        unit = None if self.unit is None else str(self.unit).strip()
        if unit == "":
            raise TopologyStatisticsConsistencyError("unit cannot be an empty string.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "unit", unit)

    @property
    def is_integer(self) -> bool:
        return np.issubdtype(self.values.dtype, np.integer)

    def to_dict(self) -> dict[str, Any]:
        return _typed_payload(
            "ScalarSeries",
            {
                "name": self.name,
                "value_dtype": "int64" if self.is_integer else "float64",
                "values": self.values.tolist(),
                "axis": self.axis.to_dict(),
                "summary": self.summary.to_dict(),
                "unit": self.unit,
            },
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ScalarSeries":
        _validate_typed_payload(payload, "ScalarSeries")
        dtype_name = str(payload["value_dtype"])
        if dtype_name not in {"int64", "float64"}:
            raise TopologyStatisticsSerializationError(
                "ScalarSeries value_dtype must be 'int64' or 'float64'."
            )
        dtype = np.int64 if dtype_name == "int64" else np.float64
        return cls(
            name=str(payload["name"]),
            values=np.asarray(payload["values"], dtype=dtype),
            axis=FrameAxis.from_dict(_mapping(payload["axis"], name="axis")),
            summary=ScalarSummary.from_dict(
                _mapping(payload["summary"], name="summary")
            ),
            unit=payload["unit"],
        )


def compute_scalar_summary(
    values: ArrayLike,
    *,
    quantiles: Sequence[float] | ArrayLike = DEFAULT_QUANTILES,
) -> ScalarSummary:
    """Return descriptive population statistics for one nonempty scalar sample."""

    data = _readonly_numeric_array(values, ndim=1, finite=True)
    if data.size == 0:
        raise TopologyStatisticsInputError("values cannot be empty.")
    probabilities = _validated_quantiles(quantiles)
    floating = data.astype(np.float64, copy=False)
    quantile_values = np.quantile(floating, probabilities, method="linear")
    standard_deviation = float(np.std(floating, ddof=0))
    minimum = float(np.min(floating))
    maximum = float(np.max(floating))
    if minimum == maximum:
        standard_deviation = 0.0
    return ScalarSummary(
        count=int(data.size),
        mean=float(np.mean(floating)),
        population_standard_deviation=standard_deviation,
        minimum=minimum,
        maximum=maximum,
        median=float(np.median(floating)),
        quantile_probabilities=probabilities,
        quantile_values=np.asarray(quantile_values, dtype=np.float64),
        is_constant=minimum == maximum,
    )


def compute_discrete_count_distribution(
    counts: ArrayLike,
    *,
    quantiles: Sequence[float] | ArrayLike = DEFAULT_QUANTILES,
) -> DiscreteCountDistribution:
    """Return the exact PMF and descriptive summary of integer graph counts."""

    data = _strict_count_array(counts)
    if data.size == 0:
        raise TopologyStatisticsInputError("counts cannot be empty.")
    support, frequencies = np.unique(data, return_counts=True)
    support = support.astype(np.int64, copy=False)
    frequencies = frequencies.astype(np.int64, copy=False)
    probabilities = frequencies.astype(np.float64) / data.size
    maximum_frequency = int(np.max(frequencies))
    modes = tuple(int(value) for value in support[frequencies == maximum_frequency])
    return DiscreteCountDistribution(
        support=support,
        frequencies=frequencies,
        probabilities=probabilities,
        summary=compute_scalar_summary(data, quantiles=quantiles),
        modes=modes,
    )


def compute_catalog_occupancy_statistics(
    frame_to_state_id: ArrayLike,
    *,
    frame_semantics: FrameSemantics | str,
    n_states: int | None = None,
) -> CatalogOccupancyStatistics:
    """Summarize dense catalog-state occupancy over selected frames.

    ``n_states`` may exceed the largest observed state ID so a filtered frame
    selection can preserve the parent catalog's declared state space.  Such
    states receive zero occupancy and first/last positions of ``-1``.
    """

    assignments = _strict_state_id_array(frame_to_state_id)
    if assignments.size == 0:
        raise TopologyStatisticsInputError("frame_to_state_id cannot be empty.")
    semantics = coerce_frame_semantics(frame_semantics)
    inferred = int(np.max(assignments)) + 1
    if n_states is None:
        state_count = inferred
    else:
        state_count = _positive_int(n_states, name="n_states")
        if state_count < inferred:
            raise TopologyStatisticsInputError(
                "n_states is smaller than an observed state ID."
            )

    counts = np.bincount(assignments, minlength=state_count).astype(np.int64)
    probabilities = counts.astype(np.float64) / assignments.size
    first = np.full(state_count, -1, dtype=np.int64)
    last = np.full(state_count, -1, dtype=np.int64)
    groups: list[StateFrameGroup] = []
    for state_id in range(state_count):
        positions = np.flatnonzero(assignments == state_id).astype(np.int64)
        groups.append(StateFrameGroup(state_id=state_id, result_positions=positions))
        if positions.size:
            first[state_id] = int(positions[0])
            last[state_id] = int(positions[-1])

    visits = (
        _trajectory_visit_counts(assignments, state_count)
        if semantics is FrameSemantics.TRAJECTORY
        else None
    )
    positive = probabilities[probabilities > 0.0]
    entropy = float(-np.sum(positive * np.log(positive)))
    return CatalogOccupancyStatistics(
        frame_semantics=semantics,
        frame_to_state_id=assignments,
        state_frame_counts=counts,
        state_probabilities=probabilities,
        first_result_positions=first,
        last_result_positions=last,
        visit_counts=visits,
        frame_groups=tuple(groups),
        dominant_state_ids=tuple(
            int(value) for value in np.flatnonzero(counts == np.max(counts))
        ),
        singleton_state_ids=tuple(int(value) for value in np.flatnonzero(counts == 1)),
        shannon_state_entropy=entropy,
        effective_state_count=float(np.exp(entropy)),
    )


def build_frame_axis(
    n_frames: int,
    *,
    frame_semantics: FrameSemantics | str,
    collection_frame_indices: ArrayLike | None = None,
    frame_ids: ArrayLike | None = None,
    steps: ArrayLike | None = None,
    times: ArrayLike | None = None,
    time_unit: str | None = None,
) -> FrameAxis:
    """Build validated frame/sample alignment metadata.

    Ensemble axes reject ``steps``, ``times``, and ``time_unit`` because stored
    ensemble order has no temporal meaning.
    """

    count = _positive_int(n_frames, name="n_frames")
    indices = (
        np.arange(count, dtype=np.int64)
        if collection_frame_indices is None
        else _strict_integer_vector(
            collection_frame_indices, name="collection_frame_indices"
        )
    )
    identifiers = (
        indices.copy()
        if frame_ids is None
        else _strict_integer_vector(frame_ids, name="frame_ids")
    )
    if indices.size != count or identifiers.size != count:
        raise TopologyStatisticsInputError(
            "collection_frame_indices and frame_ids must match n_frames."
        )
    return FrameAxis(
        frame_semantics=coerce_frame_semantics(frame_semantics),
        collection_frame_indices=indices,
        frame_ids=identifiers,
        steps=None if steps is None else _strict_integer_vector(steps, name="steps"),
        times=None if times is None else _strict_float_vector(times, name="times"),
        time_unit=time_unit,
    )


def build_scalar_series(
    name: str,
    values: ArrayLike,
    axis: FrameAxis,
    *,
    unit: str | None = None,
    quantiles: Sequence[float] | ArrayLike = DEFAULT_QUANTILES,
) -> ScalarSeries:
    """Build one immutable scalar series and its descriptive summary."""

    data = _readonly_numeric_array(values, ndim=1, finite=True)
    return ScalarSeries(
        name=name,
        values=data,
        axis=axis,
        summary=compute_scalar_summary(data, quantiles=quantiles),
        unit=unit,
    )


def expand_state_values_to_frames(
    state_values: ArrayLike,
    frame_to_state_id: ArrayLike,
) -> NDArray[Any]:
    """Expand state-level values through a dense frame-to-state assignment.

    The leading axis of ``state_values`` is the state axis.  Any trailing shape
    is preserved.  The returned array is a defensive, read-only copy.
    """

    values = np.asarray(state_values)
    if values.ndim == 0 or values.shape[0] == 0:
        raise TopologyStatisticsInputError(
            "state_values must have a nonempty leading state axis."
        )
    assignments = _strict_state_id_array(frame_to_state_id)
    if assignments.size == 0:
        raise TopologyStatisticsInputError("frame_to_state_id cannot be empty.")
    if int(np.max(assignments)) >= values.shape[0]:
        raise TopologyStatisticsInputError(
            "frame_to_state_id references a state outside state_values."
        )
    expanded = np.array(values[assignments], copy=True)
    expanded.setflags(write=False)
    return expanded


def canonical_statistics_json(payload: Mapping[str, Any]) -> str:
    """Return deterministic compact JSON for a JSON-compatible payload."""

    try:
        return json.dumps(
            _json_safe(payload),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise TopologyStatisticsSerializationError(
            "Payload is not deterministically JSON serializable."
        ) from exc


def topology_statistics_payload_digest(payload: Mapping[str, Any]) -> str:
    """Return a stable SHA-256 digest of a JSON-compatible payload."""

    encoded = canonical_statistics_json(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _trajectory_visit_counts(assignments: IntArray, n_states: int) -> IntArray:
    visits = np.zeros(n_states, dtype=np.int64)
    starts = np.empty(assignments.size, dtype=np.bool_)
    starts[0] = True
    if assignments.size > 1:
        starts[1:] = assignments[1:] != assignments[:-1]
    np.add.at(visits, assignments[starts], 1)
    visits.setflags(write=False)
    return visits


def _scalar_summaries_equal(left: ScalarSummary, right: ScalarSummary) -> bool:
    return (
        left.count == right.count
        and left.is_constant == right.is_constant
        and np.isclose(left.mean, right.mean, rtol=0.0, atol=1e-14)
        and np.isclose(
            left.population_standard_deviation,
            right.population_standard_deviation,
            rtol=0.0,
            atol=1e-14,
        )
        and np.isclose(left.minimum, right.minimum, rtol=0.0, atol=1e-14)
        and np.isclose(left.maximum, right.maximum, rtol=0.0, atol=1e-14)
        and np.isclose(left.median, right.median, rtol=0.0, atol=1e-14)
        and np.array_equal(left.quantile_probabilities, right.quantile_probabilities)
        and np.allclose(
            left.quantile_values, right.quantile_values, rtol=0.0, atol=1e-14
        )
    )


def _strict_count_array(values: ArrayLike) -> IntArray:
    array = np.asarray(values)
    if (
        array.ndim != 1
        or not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsInputError(
            "counts must be a one-dimensional integer array."
        )
    result = np.array(array, dtype=np.int64, copy=True)
    if np.any(result < 0):
        raise TopologyStatisticsInputError("counts cannot be negative.")
    result.setflags(write=False)
    return result


def _strict_state_id_array(values: ArrayLike) -> IntArray:
    array = np.asarray(values)
    if (
        array.ndim != 1
        or not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsInputError(
            "frame_to_state_id must be a one-dimensional integer array."
        )
    result = np.array(array, dtype=np.int64, copy=True)
    if np.any(result < 0):
        raise TopologyStatisticsInputError("State IDs cannot be negative.")
    result.setflags(write=False)
    return result


def _strict_integer_vector(values: ArrayLike, *, name: str) -> IntArray:
    array = np.asarray(values)
    if (
        array.ndim != 1
        or not np.issubdtype(array.dtype, np.integer)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsInputError(
            f"{name} must be a one-dimensional integer array."
        )
    result = np.array(array, dtype=np.int64, copy=True)
    result.setflags(write=False)
    return result


def _strict_float_vector(values: ArrayLike, *, name: str) -> FloatArray:
    array = np.asarray(values)
    if (
        array.ndim != 1
        or not np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsInputError(
            f"{name} must be a one-dimensional numeric array."
        )
    result = np.array(array, dtype=np.float64, copy=True)
    if not np.all(np.isfinite(result)):
        raise TopologyStatisticsInputError(f"{name} must contain only finite values.")
    result.setflags(write=False)
    return result


def _readonly_numeric_array(
    values: ArrayLike,
    *,
    ndim: int,
    finite: bool,
) -> NumericArray:
    array = np.asarray(values)
    if (
        array.ndim != ndim
        or not np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsInputError(
            f"Expected a {ndim}-dimensional numeric array."
        )
    dtype = np.int64 if np.issubdtype(array.dtype, np.integer) else np.float64
    result: NumericArray = np.array(array, dtype=dtype, copy=True)
    if finite and not np.all(np.isfinite(result)):
        raise TopologyStatisticsInputError("Numeric values must be finite.")
    result.setflags(write=False)
    return result


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


def _readonly_float_array(
    values: ArrayLike,
    *,
    ndim: int,
    finite: bool,
) -> FloatArray:
    array = np.asarray(values)
    if (
        array.ndim != ndim
        or not np.issubdtype(array.dtype, np.number)
        or np.issubdtype(array.dtype, np.bool_)
    ):
        raise TopologyStatisticsConsistencyError(
            f"Expected a {ndim}-dimensional numeric array."
        )
    result = np.array(array, dtype=np.float64, copy=True)
    if finite and not np.all(np.isfinite(result)):
        raise TopologyStatisticsConsistencyError("Numeric values must be finite.")
    result.setflags(write=False)
    return result


def _validated_quantiles(values: Sequence[float] | ArrayLike) -> FloatArray:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or array.size < 2 or not np.all(np.isfinite(array)):
        raise TopologyStatisticsInputError(
            "quantiles must be a finite one-dimensional sequence with at least two values."
        )
    if array[0] != 0.0 or array[-1] != 1.0 or np.any(np.diff(array) <= 0.0):
        raise TopologyStatisticsInputError(
            "quantiles must be strictly increasing from 0 to 1 inclusive."
        )
    result = np.array(array, dtype=np.float64, copy=True)
    result.setflags(write=False)
    return result


def _positive_int(value: Any, *, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, np.integer))
        or int(value) < 1
    ):
        raise TopologyStatisticsInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative_int(value: Any, *, name: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, np.integer))
        or int(value) < 0
    ):
        raise TopologyStatisticsConsistencyError(
            f"{name} must be a nonnegative integer."
        )
    return int(value)


def _finite_float(value: Any, *, name: str) -> float:
    if isinstance(value, bool):
        raise TopologyStatisticsConsistencyError(f"{name} must be a finite float.")
    result = float(value)
    if not np.isfinite(result):
        raise TopologyStatisticsConsistencyError(f"{name} must be finite.")
    return result


def _strict_bool(value: Any, *, name: str) -> bool:
    if type(value) is not bool:
        raise TopologyStatisticsConsistencyError(f"{name} must be a bool.")
    return value


def _scale_tolerance(*values: float) -> float:
    return 1e-13 * max(1.0, *(abs(value) for value in values))


def _typed_payload(object_type: str, fields: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": CANONICAL_TOPOLOGY_STATISTICS_COMMON_SCHEMA,
        "object_type": object_type,
        **dict(fields),
    }


def _validate_typed_payload(payload: Mapping[str, Any], object_type: str) -> None:
    if payload.get("schema_version") != CANONICAL_TOPOLOGY_STATISTICS_COMMON_SCHEMA:
        raise TopologyStatisticsSerializationError(
            "Unsupported topology-statistics common schema version."
        )
    if payload.get("object_type") != object_type:
        raise TopologyStatisticsSerializationError(
            f"Expected serialized object_type {object_type!r}."
        )


def _mapping(value: Any, *, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TopologyStatisticsSerializationError(f"{name} must be a mapping.")
    return value


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, FrameSemantics):
        return value.value
    if isinstance(value, tuple | list):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"Unsupported JSON value {type(value).__name__}.")


__all__ = [
    "CANONICAL_TOPOLOGY_STATISTICS_COMMON_SCHEMA",
    "TOPOLOGY_STATISTICS_DIGEST_ALGORITHM",
    "DEFAULT_QUANTILES",
    "TopologyStatisticsError",
    "TopologyStatisticsInputError",
    "TopologyStatisticsConsistencyError",
    "TopologyStatisticsSerializationError",
    "ScalarSummary",
    "DiscreteCountDistribution",
    "StateFrameGroup",
    "CatalogOccupancyStatistics",
    "FrameAxis",
    "ScalarSeries",
    "compute_scalar_summary",
    "compute_discrete_count_distribution",
    "compute_catalog_occupancy_statistics",
    "build_frame_axis",
    "build_scalar_series",
    "expand_state_values_to_frames",
    "canonical_statistics_json",
    "topology_statistics_payload_digest",
]
