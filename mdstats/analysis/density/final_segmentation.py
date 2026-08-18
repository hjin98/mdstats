"""Stage-11E6 final hysteretic segmentation and residence statistics.

This stage converts immutable Stage-11E4 spatial labels and optional Stage-11E5b
moving-region memberships into final core-entry/basin-retention state histories.
Unsupported space, assignment conflicts, segment boundaries, and moving-boundary
crossings remain explicit.  Residence, passage, occupancy, censoring, and
threshold/stride sensitivity statistics are reported without constructing paths,
rates, barriers, or a kinetic network.

Core-set hysteresis and survival/residence summaries are standard background.
The exact source binding, immutable-label policy, static/dynamic counterfactuals,
boundary-induced event policy, ambiguity bounds, and stability certificate are
mdstats-specific constructions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum, IntEnum
import hashlib
import json
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ...semantics import FrameSemantics
from ..site_samples import FrameworkAlignedIonSampleCatalog
from .geometry_conditioning import (
    AssignmentConflictStatus,
    CrossingDriveStatus,
    GeometryConditionedSiteCatalog,
    RegionMembership,
)
from .temporal_assignment import (
    ProvisionalTemporalAssignmentCatalog,
    RawMembershipClass,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
UInt8Array = NDArray[np.uint8]
BoolArray = NDArray[np.bool_]

FINAL_SEGMENTATION_STAGE = "11E6"
FINAL_SEGMENTATION_OPTIONS_SCHEMA = "mdstats.final-segmentation-options.v1"
FINAL_SEGMENTATION_RESOURCES_SCHEMA = "mdstats.final-segmentation-resources.v1"
FINAL_MEMBERSHIP_TABLE_SCHEMA = "mdstats.final-membership-table.v1"
FINAL_RESIDENCE_INTERVAL_SCHEMA = "mdstats.final-residence-interval.v1"
FINAL_PASSAGE_INTERVAL_SCHEMA = "mdstats.final-passage-interval.v1"
STATE_RESIDENCE_STATISTICS_SCHEMA = "mdstats.state-residence-statistics.v1"
SEGMENTATION_SENSITIVITY_SCHEMA = "mdstats.segmentation-sensitivity.v1"
FINAL_SEGMENTATION_CATALOG_SCHEMA = "mdstats.final-segmentation-catalog.v1"


class FinalSegmentationError(ValueError):
    """Base Stage-11E6 error."""


class FinalSegmentationInputError(FinalSegmentationError):
    """Raised when source binding or input arrays are inconsistent."""


class FinalSegmentationResourceError(FinalSegmentationError):
    """Raised transactionally before declared work limits are exceeded."""


class FinalSegmentationSerializationError(FinalSegmentationError):
    """Raised when serialized Stage-11E6 data are malformed or tampered with."""


class FinalMembershipClass(IntEnum):
    EVIDENCE_EXCLUDED = 0
    OUTSIDE = 1
    BASIN = 2
    CORE = 3
    UNSUPPORTED_UNKNOWN = 4
    NUMERICALLY_UNRESOLVED = 5
    ASSIGNMENT_CONFLICT = 6


class FinalMembershipSource(str, Enum):
    FROZEN_E4 = "frozen_e4"
    SELECTED_GEOMETRY = "selected_geometry"
    REQUIRE_STATIC_DYNAMIC_AGREEMENT = "require_static_dynamic_agreement"


class BoundaryInducedPolicy(str, Enum):
    RECORD = "record"
    MARK_UNRESOLVED = "mark_unresolved"
    EXCLUDE_EVENT = "exclude_event"


class FinalPassageOutcome(str, Enum):
    RESOLVED_TRANSITION = "resolved_transition"
    RETAINED_EXCURSION = "retained_excursion"
    RETURN_EXCURSION = "return_excursion"
    RECROSSING = "recrossing"
    UNRESOLVED_GAP = "unresolved_gap"
    ASSIGNMENT_CONFLICT = "assignment_conflict"
    BOUNDARY_INDUCED = "boundary_induced"
    RIGHT_CENSORED_EXIT = "right_censored_exit"


class SegmentationStabilityStatus(str, Enum):
    STABLE = "stable"
    UNSTABLE = "unstable"
    INSUFFICIENT_EVENTS = "insufficient_events"
    ENSEMBLE_UNAVAILABLE = "ensemble_unavailable"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii")); h.update(str(arr.shape).encode("ascii")); h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise FinalSegmentationInputError(f"{name} must be a SHA-256 digest.")
    return value


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise FinalSegmentationInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise FinalSegmentationInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise FinalSegmentationInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise FinalSegmentationInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise FinalSegmentationInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise FinalSegmentationInputError(f"{name} must be finite and nonnegative.")
    return result


def _fraction(value: Any, name: str) -> float:
    result = _nonnegative(value, name)
    if result > 1.0:
        raise FinalSegmentationInputError(f"{name} must not exceed one.")
    return result


@dataclass(frozen=True, slots=True)
class FinalSegmentationOptions:
    membership_source: FinalMembershipSource = FinalMembershipSource.FROZEN_E4
    minimum_core_entry_frames: int = 2
    minimum_basin_exit_frames: int = 2
    recrossing_window_frames: int = 4
    boundary_induced_policy: BoundaryInducedPolicy = BoundaryInducedPolicy.RECORD
    sensitivity_thresholds: tuple[tuple[int, int], ...] = ((1, 1), (2, 2), (3, 3))
    sensitivity_stride_factors: tuple[int, ...] = (1, 2, 4)
    maximum_transition_count_relative_change: float = 0.25
    maximum_occupancy_absolute_change: float = 0.05
    minimum_events_for_stability: int = 2
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        source = FinalMembershipSource(self.membership_source)
        entry = _positive_int(self.minimum_core_entry_frames, "minimum_core_entry_frames")
        exit_frames = _positive_int(self.minimum_basin_exit_frames, "minimum_basin_exit_frames")
        recross = _positive_int(self.recrossing_window_frames, "recrossing_window_frames")
        boundary = BoundaryInducedPolicy(self.boundary_induced_policy)
        thresholds = tuple(sorted({(_positive_int(a, "sensitivity entry"), _positive_int(b, "sensitivity exit")) for a, b in self.sensitivity_thresholds}))
        if (entry, exit_frames) not in thresholds:
            thresholds = tuple(sorted((*thresholds, (entry, exit_frames))))
        strides = tuple(sorted({_positive_int(v, "sensitivity_stride_factors") for v in self.sensitivity_stride_factors}))
        if not strides or strides[0] != 1:
            raise FinalSegmentationInputError("sensitivity_stride_factors must include one.")
        transition_tol = _nonnegative(self.maximum_transition_count_relative_change, "maximum_transition_count_relative_change")
        occupancy_tol = _fraction(self.maximum_occupancy_absolute_change, "maximum_occupancy_absolute_change")
        minimum_events = _positive_int(self.minimum_events_for_stability, "minimum_events_for_stability")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": FINAL_SEGMENTATION_OPTIONS_SCHEMA, "membership_source": source.value,
            "minimum_core_entry_frames": entry, "minimum_basin_exit_frames": exit_frames,
            "recrossing_window_frames": recross, "boundary_induced_policy": boundary.value,
            "sensitivity_thresholds": [list(v) for v in thresholds], "sensitivity_stride_factors": list(strides),
            "maximum_transition_count_relative_change": transition_tol,
            "maximum_occupancy_absolute_change": occupancy_tol,
            "minimum_events_for_stability": minimum_events, "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Final-segmentation options signature is inconsistent.")
        for name, value in (
            ("membership_source", source), ("minimum_core_entry_frames", entry),
            ("minimum_basin_exit_frames", exit_frames), ("recrossing_window_frames", recross),
            ("boundary_induced_policy", boundary), ("sensitivity_thresholds", thresholds),
            ("sensitivity_stride_factors", strides), ("maximum_transition_count_relative_change", transition_tol),
            ("maximum_occupancy_absolute_change", occupancy_tol), ("minimum_events_for_stability", minimum_events),
            ("metadata", metadata), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FINAL_SEGMENTATION_OPTIONS_SCHEMA, "membership_source": self.membership_source.value,
            "minimum_core_entry_frames": self.minimum_core_entry_frames,
            "minimum_basin_exit_frames": self.minimum_basin_exit_frames,
            "recrossing_window_frames": self.recrossing_window_frames,
            "boundary_induced_policy": self.boundary_induced_policy.value,
            "sensitivity_thresholds": [list(v) for v in self.sensitivity_thresholds],
            "sensitivity_stride_factors": list(self.sensitivity_stride_factors),
            "maximum_transition_count_relative_change": self.maximum_transition_count_relative_change,
            "maximum_occupancy_absolute_change": self.maximum_occupancy_absolute_change,
            "minimum_events_for_stability": self.minimum_events_for_stability,
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalSegmentationOptions":
        if payload.get("schema") != FINAL_SEGMENTATION_OPTIONS_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported final-segmentation options schema.")
        return cls(
            membership_source=FinalMembershipSource(payload["membership_source"]),
            minimum_core_entry_frames=int(payload["minimum_core_entry_frames"]),
            minimum_basin_exit_frames=int(payload["minimum_basin_exit_frames"]),
            recrossing_window_frames=int(payload["recrossing_window_frames"]),
            boundary_induced_policy=BoundaryInducedPolicy(payload["boundary_induced_policy"]),
            sensitivity_thresholds=tuple((int(v[0]), int(v[1])) for v in payload["sensitivity_thresholds"]),
            sensitivity_stride_factors=tuple(int(v) for v in payload["sensitivity_stride_factors"]),
            maximum_transition_count_relative_change=float(payload["maximum_transition_count_relative_change"]),
            maximum_occupancy_absolute_change=float(payload["maximum_occupancy_absolute_change"]),
            minimum_events_for_stability=int(payload["minimum_events_for_stability"]),
            metadata=dict(payload.get("metadata", {})), signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class FinalSegmentationResourcePolicy:
    max_samples: int = 10_000_000
    max_states: int = 100_000
    max_residences: int = 2_000_000
    max_passages: int = 2_000_000
    max_sensitivity_runs: int = 128
    max_output_bytes: int = 2_000_000_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name) for name in (
            "max_samples", "max_states", "max_residences", "max_passages", "max_sensitivity_runs", "max_output_bytes")}
        payload = {"schema": FINAL_SEGMENTATION_RESOURCES_SCHEMA, **values}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Final-segmentation resources signature is inconsistent.")
        for name, value in (*values.items(), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FINAL_SEGMENTATION_RESOURCES_SCHEMA, **{name: getattr(self, name) for name in (
            "max_samples", "max_states", "max_residences", "max_passages", "max_sensitivity_runs", "max_output_bytes")}, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalSegmentationResourcePolicy":
        if payload.get("schema") != FINAL_SEGMENTATION_RESOURCES_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported final-segmentation resources schema.")
        return cls(**{name: int(payload[name]) for name in (
            "max_samples", "max_states", "max_residences", "max_passages", "max_sensitivity_runs", "max_output_bytes")},
            signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class FinalMembershipTable:
    sample_catalog_signature: str
    source_membership_signature: str
    geometry_catalog_signature: str | None
    membership_source: FinalMembershipSource
    membership_class: UInt8Array
    state_ids: Int32Array
    region_membership: UInt8Array
    conflict_mask: BoolArray
    boundary_induced_mask: BoolArray
    signature: str = ""

    def __post_init__(self) -> None:
        source = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        membership = _sha(self.source_membership_signature, "source_membership_signature")
        geometry = None if self.geometry_catalog_signature is None else _sha(self.geometry_catalog_signature, "geometry_catalog_signature")
        mode = FinalMembershipSource(self.membership_source)
        classes = _readonly(self.membership_class, dtype=np.uint8, ndim=1, name="membership_class")
        n = classes.size
        states = _readonly(self.state_ids, dtype=np.int32, ndim=1, name="state_ids", shape=(n,))
        regions = _readonly(self.region_membership, dtype=np.uint8, ndim=1, name="region_membership", shape=(n,))
        conflicts = _readonly(self.conflict_mask, dtype=np.bool_, ndim=1, name="conflict_mask", shape=(n,))
        boundary = _readonly(self.boundary_induced_mask, dtype=np.bool_, ndim=1, name="boundary_induced_mask", shape=(n,))
        valid_classes = {int(v) for v in FinalMembershipClass}
        if any(int(v) not in valid_classes for v in np.unique(classes)):
            raise FinalSegmentationInputError("membership_class contains an unknown code.")
        if np.any(regions > int(RegionMembership.CORE)):
            raise FinalSegmentationInputError("region_membership contains an unknown code.")
        assigned = np.isin(classes, [int(FinalMembershipClass.BASIN), int(FinalMembershipClass.CORE)])
        if np.any(assigned & (states < 0)) or np.any(~assigned & (states >= 0)):
            raise FinalSegmentationInputError("State ids must exist exactly for basin/core membership.")
        if np.any(conflicts != (classes == int(FinalMembershipClass.ASSIGNMENT_CONFLICT))):
            raise FinalSegmentationInputError("conflict_mask must match assignment-conflict membership.")
        payload = {
            "schema": FINAL_MEMBERSHIP_TABLE_SCHEMA, "sample_catalog_signature": source,
            "source_membership_signature": membership, "geometry_catalog_signature": geometry,
            "membership_source": mode.value, "class_digest": _array_digest(classes),
            "state_digest": _array_digest(states), "region_digest": _array_digest(regions),
            "conflict_digest": _array_digest(conflicts), "boundary_digest": _array_digest(boundary),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Final-membership signature is inconsistent.")
        for name, value in (
            ("sample_catalog_signature", source), ("source_membership_signature", membership),
            ("geometry_catalog_signature", geometry), ("membership_source", mode),
            ("membership_class", classes), ("state_ids", states), ("region_membership", regions),
            ("conflict_mask", conflicts), ("boundary_induced_mask", boundary), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    @property
    def n_samples(self) -> int:
        return int(self.state_ids.size)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FINAL_MEMBERSHIP_TABLE_SCHEMA, "sample_catalog_signature": self.sample_catalog_signature,
            "source_membership_signature": self.source_membership_signature,
            "geometry_catalog_signature": self.geometry_catalog_signature, "membership_source": self.membership_source.value,
            "membership_class": self.membership_class.tolist(), "state_ids": self.state_ids.tolist(),
            "region_membership": self.region_membership.tolist(), "conflict_mask": self.conflict_mask.tolist(),
            "boundary_induced_mask": self.boundary_induced_mask.tolist(), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalMembershipTable":
        if payload.get("schema") != FINAL_MEMBERSHIP_TABLE_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported final-membership schema.")
        return cls(
            str(payload["sample_catalog_signature"]), str(payload["source_membership_signature"]),
            payload.get("geometry_catalog_signature"), FinalMembershipSource(payload["membership_source"]),
            np.asarray(payload["membership_class"], dtype=np.uint8), np.asarray(payload["state_ids"], dtype=np.int32),
            np.asarray(payload["region_membership"], dtype=np.uint8), np.asarray(payload["conflict_mask"], dtype=np.bool_),
            np.asarray(payload["boundary_induced_mask"], dtype=np.bool_), str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class FinalResidenceInterval:
    residence_id: int
    atom_index: int
    state_id: int
    segment_id: int
    sample_indices: IntArray
    represented_time: float
    core_time: float
    basin_time: float
    retained_excursion_time: float
    left_censored: bool
    right_censored: bool
    signature: str = ""

    def __post_init__(self) -> None:
        ids = {name: int(getattr(self, name)) for name in ("residence_id", "atom_index", "state_id", "segment_id")}
        if any(v < 0 for v in ids.values()):
            raise FinalSegmentationInputError("Residence identifiers must be nonnegative.")
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        if samples.size == 0 or np.any(samples < 0):
            raise FinalSegmentationInputError("A residence requires nonnegative samples.")
        represented = _nonnegative(self.represented_time, "represented_time")
        core = _nonnegative(self.core_time, "core_time"); basin = _nonnegative(self.basin_time, "basin_time")
        excursion = _nonnegative(self.retained_excursion_time, "retained_excursion_time")
        if abs((core + basin + excursion) - represented) > max(1e-10, 1e-10 * represented):
            raise FinalSegmentationInputError("Residence time components must sum to represented_time.")
        payload = {"schema": FINAL_RESIDENCE_INTERVAL_SCHEMA, **ids, "samples_digest": _array_digest(samples),
                   "represented_time": represented, "core_time": core, "basin_time": basin,
                   "retained_excursion_time": excursion, "left_censored": bool(self.left_censored),
                   "right_censored": bool(self.right_censored)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Final-residence signature is inconsistent.")
        for name, value in (*ids.items(), ("sample_indices", samples), ("represented_time", represented),
                            ("core_time", core), ("basin_time", basin), ("retained_excursion_time", excursion),
                            ("left_censored", bool(self.left_censored)), ("right_censored", bool(self.right_censored)),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FINAL_RESIDENCE_INTERVAL_SCHEMA, "residence_id": self.residence_id,
                "atom_index": self.atom_index, "state_id": self.state_id, "segment_id": self.segment_id,
                "sample_indices": self.sample_indices.tolist(), "represented_time": self.represented_time,
                "core_time": self.core_time, "basin_time": self.basin_time,
                "retained_excursion_time": self.retained_excursion_time, "left_censored": self.left_censored,
                "right_censored": self.right_censored, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalResidenceInterval":
        if payload.get("schema") != FINAL_RESIDENCE_INTERVAL_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported final-residence schema.")
        return cls(int(payload["residence_id"]), int(payload["atom_index"]), int(payload["state_id"]),
                   int(payload["segment_id"]), np.asarray(payload["sample_indices"], dtype=np.int64),
                   float(payload["represented_time"]), float(payload["core_time"]), float(payload["basin_time"]),
                   float(payload["retained_excursion_time"]), bool(payload["left_censored"]),
                   bool(payload["right_censored"]), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class FinalPassageInterval:
    passage_id: int
    atom_index: int
    segment_id: int
    source_state_id: int | None
    target_state_id: int | None
    sample_indices: IntArray
    represented_time: float
    outcome: FinalPassageOutcome
    contains_unknown: bool
    contains_conflict: bool
    boundary_induced: bool
    counted_transition: bool
    signature: str = ""

    def __post_init__(self) -> None:
        passage = int(self.passage_id); atom = int(self.atom_index); segment = int(self.segment_id)
        if min(passage, atom, segment) < 0:
            raise FinalSegmentationInputError("Passage identifiers must be nonnegative.")
        source = None if self.source_state_id is None else int(self.source_state_id)
        target = None if self.target_state_id is None else int(self.target_state_id)
        if source is not None and source < 0 or target is not None and target < 0:
            raise FinalSegmentationInputError("Passage state ids must be nonnegative or None.")
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        if np.any(samples < 0):
            raise FinalSegmentationInputError("Passage samples must be nonnegative.")
        represented = _nonnegative(self.represented_time, "represented_time")
        outcome = FinalPassageOutcome(self.outcome)
        counted = bool(self.counted_transition)
        if counted and (outcome is not FinalPassageOutcome.RESOLVED_TRANSITION or source is None or target is None or source == target):
            raise FinalSegmentationInputError("Only resolved changes of state may count as transitions.")
        payload = {"schema": FINAL_PASSAGE_INTERVAL_SCHEMA, "passage_id": passage, "atom_index": atom,
                   "segment_id": segment, "source_state_id": source, "target_state_id": target,
                   "samples_digest": _array_digest(samples), "represented_time": represented,
                   "outcome": outcome.value, "contains_unknown": bool(self.contains_unknown),
                   "contains_conflict": bool(self.contains_conflict), "boundary_induced": bool(self.boundary_induced),
                   "counted_transition": counted}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Final-passage signature is inconsistent.")
        for name, value in (
            ("passage_id", passage), ("atom_index", atom), ("segment_id", segment),
            ("source_state_id", source), ("target_state_id", target), ("sample_indices", samples),
            ("represented_time", represented), ("outcome", outcome),
            ("contains_unknown", bool(self.contains_unknown)), ("contains_conflict", bool(self.contains_conflict)),
            ("boundary_induced", bool(self.boundary_induced)), ("counted_transition", counted), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FINAL_PASSAGE_INTERVAL_SCHEMA, "passage_id": self.passage_id,
                "atom_index": self.atom_index, "segment_id": self.segment_id,
                "source_state_id": self.source_state_id, "target_state_id": self.target_state_id,
                "sample_indices": self.sample_indices.tolist(), "represented_time": self.represented_time,
                "outcome": self.outcome.value, "contains_unknown": self.contains_unknown,
                "contains_conflict": self.contains_conflict, "boundary_induced": self.boundary_induced,
                "counted_transition": self.counted_transition, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalPassageInterval":
        if payload.get("schema") != FINAL_PASSAGE_INTERVAL_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported final-passage schema.")
        return cls(int(payload["passage_id"]), int(payload["atom_index"]), int(payload["segment_id"]),
                   payload.get("source_state_id"), payload.get("target_state_id"),
                   np.asarray(payload["sample_indices"], dtype=np.int64), float(payload["represented_time"]),
                   FinalPassageOutcome(payload["outcome"]), bool(payload["contains_unknown"]),
                   bool(payload["contains_conflict"]), bool(payload["boundary_induced"]),
                   bool(payload["counted_transition"]), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StateResidenceStatistics:
    state_id: int
    residence_count: int
    uncensored_residence_count: int
    resolved_departure_count: int
    total_ion_time: float
    mean_residence_time: float | None
    median_residence_time: float | None
    mean_occupancy_lower: float
    mean_occupancy_upper: float
    vacancy_fraction_lower: float
    vacancy_fraction_upper: float
    multiple_occupancy_fraction_lower: float
    multiple_occupancy_fraction_upper: float
    signature: str = ""

    def __post_init__(self) -> None:
        state = int(self.state_id)
        counts = {name: int(getattr(self, name)) for name in ("residence_count", "uncensored_residence_count", "resolved_departure_count")}
        if state < 0 or any(v < 0 for v in counts.values()) or counts["uncensored_residence_count"] > counts["residence_count"]:
            raise FinalSegmentationInputError("Invalid residence-statistic identifiers or counts.")
        ion_time = _nonnegative(self.total_ion_time, "total_ion_time")
        mean = None if self.mean_residence_time is None else _nonnegative(self.mean_residence_time, "mean_residence_time")
        median = None if self.median_residence_time is None else _nonnegative(self.median_residence_time, "median_residence_time")
        occupancy_lower = _nonnegative(self.mean_occupancy_lower, "mean_occupancy_lower")
        occupancy_upper = _nonnegative(self.mean_occupancy_upper, "mean_occupancy_upper")
        if occupancy_lower > occupancy_upper + 1e-12:
            raise FinalSegmentationInputError("Occupancy lower bound exceeds upper bound.")
        fractions = {name: _fraction(getattr(self, name), name) for name in (
            "vacancy_fraction_lower", "vacancy_fraction_upper", "multiple_occupancy_fraction_lower", "multiple_occupancy_fraction_upper")}
        if fractions["vacancy_fraction_lower"] > fractions["vacancy_fraction_upper"] + 1e-12:
            raise FinalSegmentationInputError("Vacancy lower bound exceeds upper bound.")
        if fractions["multiple_occupancy_fraction_lower"] > fractions["multiple_occupancy_fraction_upper"] + 1e-12:
            raise FinalSegmentationInputError("Multiple-occupancy lower bound exceeds upper bound.")
        payload = {"schema": STATE_RESIDENCE_STATISTICS_SCHEMA, "state_id": state, **counts,
                   "total_ion_time": ion_time, "mean_residence_time": mean, "median_residence_time": median,
                   "mean_occupancy_lower": occupancy_lower, "mean_occupancy_upper": occupancy_upper, **fractions}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("State-residence-statistics signature is inconsistent.")
        for name, value in (("state_id", state), *counts.items(), ("total_ion_time", ion_time),
                            ("mean_residence_time", mean), ("median_residence_time", median),
                            ("mean_occupancy_lower", occupancy_lower), ("mean_occupancy_upper", occupancy_upper),
                            *fractions.items(), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STATE_RESIDENCE_STATISTICS_SCHEMA, **{name: getattr(self, name) for name in (
            "state_id", "residence_count", "uncensored_residence_count", "resolved_departure_count",
            "total_ion_time", "mean_residence_time", "median_residence_time", "mean_occupancy_lower",
            "mean_occupancy_upper", "vacancy_fraction_lower", "vacancy_fraction_upper",
            "multiple_occupancy_fraction_lower", "multiple_occupancy_fraction_upper")}, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateResidenceStatistics":
        if payload.get("schema") != STATE_RESIDENCE_STATISTICS_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported state-residence-statistics schema.")
        return cls(*(payload.get(name) for name in (
            "state_id", "residence_count", "uncensored_residence_count", "resolved_departure_count",
            "total_ion_time", "mean_residence_time", "median_residence_time", "mean_occupancy_lower",
            "mean_occupancy_upper", "vacancy_fraction_lower", "vacancy_fraction_upper",
            "multiple_occupancy_fraction_lower", "multiple_occupancy_fraction_upper")),
            signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class SegmentationSensitivityRecord:
    minimum_core_entry_frames: int
    minimum_basin_exit_frames: int
    stride_factor: int
    residence_count: int
    resolved_transition_count: int
    occupancy_by_state: tuple[tuple[int, float], ...]
    maximum_transition_relative_change: float
    maximum_occupancy_absolute_change: float
    signature: str = ""

    def __post_init__(self) -> None:
        entry = _positive_int(self.minimum_core_entry_frames, "minimum_core_entry_frames")
        exit_frames = _positive_int(self.minimum_basin_exit_frames, "minimum_basin_exit_frames")
        stride = _positive_int(self.stride_factor, "stride_factor")
        residences = int(self.residence_count); transitions = int(self.resolved_transition_count)
        if residences < 0 or transitions < 0:
            raise FinalSegmentationInputError("Sensitivity counts must be nonnegative.")
        occupancy = tuple((int(k), _nonnegative(v, "occupancy")) for k, v in self.occupancy_by_state)
        if tuple(k for k, _ in occupancy) != tuple(sorted({k for k, _ in occupancy})):
            raise FinalSegmentationInputError("Sensitivity occupancies must have sorted unique state ids.")
        transition_change = _nonnegative(self.maximum_transition_relative_change, "maximum_transition_relative_change")
        occupancy_change = _nonnegative(self.maximum_occupancy_absolute_change, "maximum_occupancy_absolute_change")
        payload = {"schema": SEGMENTATION_SENSITIVITY_SCHEMA, "minimum_core_entry_frames": entry,
                   "minimum_basin_exit_frames": exit_frames, "stride_factor": stride,
                   "residence_count": residences, "resolved_transition_count": transitions,
                   "occupancy_by_state": [[k, v] for k, v in occupancy],
                   "maximum_transition_relative_change": transition_change,
                   "maximum_occupancy_absolute_change": occupancy_change}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Segmentation-sensitivity signature is inconsistent.")
        for name, value in (("minimum_core_entry_frames", entry), ("minimum_basin_exit_frames", exit_frames),
                            ("stride_factor", stride), ("residence_count", residences),
                            ("resolved_transition_count", transitions), ("occupancy_by_state", occupancy),
                            ("maximum_transition_relative_change", transition_change),
                            ("maximum_occupancy_absolute_change", occupancy_change), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SEGMENTATION_SENSITIVITY_SCHEMA,
                "minimum_core_entry_frames": self.minimum_core_entry_frames,
                "minimum_basin_exit_frames": self.minimum_basin_exit_frames,
                "stride_factor": self.stride_factor, "residence_count": self.residence_count,
                "resolved_transition_count": self.resolved_transition_count,
                "occupancy_by_state": [[k, v] for k, v in self.occupancy_by_state],
                "maximum_transition_relative_change": self.maximum_transition_relative_change,
                "maximum_occupancy_absolute_change": self.maximum_occupancy_absolute_change,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SegmentationSensitivityRecord":
        if payload.get("schema") != SEGMENTATION_SENSITIVITY_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported segmentation-sensitivity schema.")
        return cls(int(payload["minimum_core_entry_frames"]), int(payload["minimum_basin_exit_frames"]),
                   int(payload["stride_factor"]), int(payload["residence_count"]),
                   int(payload["resolved_transition_count"]),
                   tuple((int(v[0]), float(v[1])) for v in payload["occupancy_by_state"]),
                   float(payload["maximum_transition_relative_change"]),
                   float(payload["maximum_occupancy_absolute_change"]), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class FinalHystereticSegmentationCatalog:
    sample_catalog_signature: str
    validated_frozen_catalog_signature: str
    provisional_temporal_catalog_signature: str
    geometry_catalog_signature: str | None
    options: FinalSegmentationOptions
    resources: FinalSegmentationResourcePolicy
    membership: FinalMembershipTable
    assigned_state_ids: Int32Array
    residence_ids: Int32Array
    passage_ids: Int32Array
    residences: tuple[FinalResidenceInterval, ...]
    passages: tuple[FinalPassageInterval, ...]
    state_statistics: tuple[StateResidenceStatistics, ...]
    sensitivity_records: tuple[SegmentationSensitivityRecord, ...]
    stability_status: SegmentationStabilityStatus
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        sources = {name: _sha(getattr(self, name), name) for name in (
            "sample_catalog_signature", "validated_frozen_catalog_signature", "provisional_temporal_catalog_signature")}
        geometry = None if self.geometry_catalog_signature is None else _sha(self.geometry_catalog_signature, "geometry_catalog_signature")
        if self.membership.sample_catalog_signature != sources["sample_catalog_signature"]:
            raise FinalSegmentationInputError("Final membership belongs to another sample catalog.")
        n = self.membership.n_samples
        assigned = _readonly(self.assigned_state_ids, dtype=np.int32, ndim=1, name="assigned_state_ids", shape=(n,))
        residence_ids = _readonly(self.residence_ids, dtype=np.int32, ndim=1, name="residence_ids", shape=(n,))
        passage_ids = _readonly(self.passage_ids, dtype=np.int32, ndim=1, name="passage_ids", shape=(n,))
        residences = tuple(self.residences); passages = tuple(self.passages); stats = tuple(self.state_statistics)
        sensitivity = tuple(self.sensitivity_records); status = SegmentationStabilityStatus(self.stability_status)
        if tuple(v.residence_id for v in residences) != tuple(range(len(residences))):
            raise FinalSegmentationInputError("Residence ids must be canonical.")
        if tuple(v.passage_id for v in passages) != tuple(range(len(passages))):
            raise FinalSegmentationInputError("Passage ids must be canonical.")
        if tuple(v.state_id for v in stats) != tuple(sorted(v.state_id for v in stats)):
            raise FinalSegmentationInputError("State statistics must be sorted by state id.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": FINAL_SEGMENTATION_CATALOG_SCHEMA, **sources, "geometry_catalog_signature": geometry,
                   "options_signature": self.options.signature, "resources_signature": self.resources.signature,
                   "membership_signature": self.membership.signature, "assigned_digest": _array_digest(assigned),
                   "residence_id_digest": _array_digest(residence_ids), "passage_id_digest": _array_digest(passage_ids),
                   "residences": [v.signature for v in residences], "passages": [v.signature for v in passages],
                   "state_statistics": [v.signature for v in stats], "sensitivity": [v.signature for v in sensitivity],
                   "stability_status": status.value, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise FinalSegmentationInputError("Final-segmentation catalog signature is inconsistent.")
        for name, value in (*sources.items(), ("geometry_catalog_signature", geometry),
                            ("assigned_state_ids", assigned), ("residence_ids", residence_ids),
                            ("passage_ids", passage_ids), ("residences", residences), ("passages", passages),
                            ("state_statistics", stats), ("sensitivity_records", sensitivity),
                            ("stability_status", status), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FINAL_SEGMENTATION_CATALOG_SCHEMA,
                "sample_catalog_signature": self.sample_catalog_signature,
                "validated_frozen_catalog_signature": self.validated_frozen_catalog_signature,
                "provisional_temporal_catalog_signature": self.provisional_temporal_catalog_signature,
                "geometry_catalog_signature": self.geometry_catalog_signature, "options": self.options.to_dict(),
                "resources": self.resources.to_dict(), "membership": self.membership.to_dict(),
                "assigned_state_ids": self.assigned_state_ids.tolist(), "residence_ids": self.residence_ids.tolist(),
                "passage_ids": self.passage_ids.tolist(), "residences": [v.to_dict() for v in self.residences],
                "passages": [v.to_dict() for v in self.passages],
                "state_statistics": [v.to_dict() for v in self.state_statistics],
                "sensitivity_records": [v.to_dict() for v in self.sensitivity_records],
                "stability_status": self.stability_status.value, "metadata": _json_value(self.metadata),
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalHystereticSegmentationCatalog":
        if payload.get("schema") != FINAL_SEGMENTATION_CATALOG_SCHEMA:
            raise FinalSegmentationSerializationError("Unsupported final-segmentation catalog schema.")
        return cls(str(payload["sample_catalog_signature"]), str(payload["validated_frozen_catalog_signature"]),
                   str(payload["provisional_temporal_catalog_signature"]), payload.get("geometry_catalog_signature"),
                   FinalSegmentationOptions.from_dict(payload["options"]),
                   FinalSegmentationResourcePolicy.from_dict(payload["resources"]),
                   FinalMembershipTable.from_dict(payload["membership"]),
                   np.asarray(payload["assigned_state_ids"], dtype=np.int32),
                   np.asarray(payload["residence_ids"], dtype=np.int32),
                   np.asarray(payload["passage_ids"], dtype=np.int32),
                   tuple(FinalResidenceInterval.from_dict(v) for v in payload["residences"]),
                   tuple(FinalPassageInterval.from_dict(v) for v in payload["passages"]),
                   tuple(StateResidenceStatistics.from_dict(v) for v in payload["state_statistics"]),
                   tuple(SegmentationSensitivityRecord.from_dict(v) for v in payload["sensitivity_records"]),
                   SegmentationStabilityStatus(payload["stability_status"]), dict(payload.get("metadata", {})),
                   str(payload.get("signature", "")))


def _frozen_membership(temporal: ProvisionalTemporalAssignmentCatalog) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    raw = temporal.membership.raw_classification
    basin = temporal.membership.basin_membership
    core = temporal.membership.core_membership
    n = raw.size
    classes = np.full(n, int(FinalMembershipClass.OUTSIDE), dtype=np.uint8)
    states = np.full(n, -1, dtype=np.int32)
    regions = np.full(n, int(RegionMembership.OUTSIDE), dtype=np.uint8)
    for i in range(n):
        item = RawMembershipClass(int(raw[i]))
        if item is RawMembershipClass.EVIDENCE_EXCLUDED:
            classes[i] = int(FinalMembershipClass.EVIDENCE_EXCLUDED)
        elif item is RawMembershipClass.CORE:
            classes[i] = int(FinalMembershipClass.CORE); states[i] = int(core[i]); regions[i] = int(RegionMembership.CORE)
        elif item is RawMembershipClass.BASIN:
            classes[i] = int(FinalMembershipClass.BASIN); states[i] = int(basin[i]); regions[i] = int(RegionMembership.BASIN)
        elif item is RawMembershipClass.UNSUPPORTED_UNKNOWN:
            classes[i] = int(FinalMembershipClass.UNSUPPORTED_UNKNOWN)
        elif item is RawMembershipClass.NUMERICALLY_UNRESOLVED:
            classes[i] = int(FinalMembershipClass.NUMERICALLY_UNRESOLVED)
        elif item is RawMembershipClass.CORE_OVERLAP:
            classes[i] = int(FinalMembershipClass.ASSIGNMENT_CONFLICT)
    return classes, states, regions


def _geometry_membership(geometry: GeometryConditionedSiteCatalog, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    classes = np.full(n, int(FinalMembershipClass.OUTSIDE), dtype=np.uint8)
    states = np.full(n, -1, dtype=np.int32)
    regions = np.full(n, int(RegionMembership.OUTSIDE), dtype=np.uint8)
    boundary = np.zeros(n, dtype=np.bool_)
    values: dict[tuple[int, int], RegionMembership] = {}
    for refinement in geometry.refinements:
        for sample, membership in zip(refinement.sample_indices, refinement.selected_membership, strict=True):
            values[(int(sample), refinement.state_id)] = RegionMembership(int(membership))
        for crossing in refinement.crossings:
            if crossing.boundary_induced_crossing or crossing.drive_status is CrossingDriveStatus.BOUNDARY_INDUCED:
                if 0 <= crossing.sample_index_before < n: boundary[crossing.sample_index_before] = True
                if 0 <= crossing.sample_index_after < n: boundary[crossing.sample_index_after] = True
    for record in geometry.assignment_conflicts:
        i = int(record.sample_index)
        if i < 0 or i >= n:
            raise FinalSegmentationInputError("Geometry conflict sample lies outside the sample catalog.")
        if record.status in (AssignmentConflictStatus.UNIQUE_CORE, AssignmentConflictStatus.UNIQUE_BASIN) and len(record.selected_state_ids) == 1:
            state = int(record.selected_state_ids[0]); membership = values.get((i, state), RegionMembership.OUTSIDE)
            if membership is RegionMembership.CORE:
                classes[i] = int(FinalMembershipClass.CORE); states[i] = state; regions[i] = int(RegionMembership.CORE)
            elif membership is RegionMembership.BASIN:
                classes[i] = int(FinalMembershipClass.BASIN); states[i] = state; regions[i] = int(RegionMembership.BASIN)
        elif record.status in (
            AssignmentConflictStatus.MULTIPLE_CORE_OVERLAP, AssignmentConflictStatus.MULTIPLE_BASIN_OVERLAP,
            AssignmentConflictStatus.STATIC_DYNAMIC_CONFLICT, AssignmentConflictStatus.ASSIGNMENT_UNRESOLVED,
        ):
            classes[i] = int(FinalMembershipClass.ASSIGNMENT_CONFLICT)
    return classes, states, regions, boundary


def _prepare_final_membership(
    temporal: ProvisionalTemporalAssignmentCatalog,
    geometry: GeometryConditionedSiteCatalog | None,
    options: FinalSegmentationOptions,
) -> FinalMembershipTable:
    frozen_classes, frozen_states, frozen_regions = _frozen_membership(temporal)
    n = frozen_classes.size
    boundary = np.zeros(n, dtype=np.bool_)
    if options.membership_source is FinalMembershipSource.FROZEN_E4:
        classes, states, regions = frozen_classes, frozen_states, frozen_regions
    else:
        if geometry is None:
            raise FinalSegmentationInputError("Selected or agreement membership requires a Stage-11E5b catalog.")
        dynamic_classes, dynamic_states, dynamic_regions, boundary = _geometry_membership(geometry, n)
        # Preserve immutable unsupported/excluded E4 evidence classes.
        immutable = np.isin(frozen_classes, [
            int(FinalMembershipClass.EVIDENCE_EXCLUDED), int(FinalMembershipClass.UNSUPPORTED_UNKNOWN),
            int(FinalMembershipClass.NUMERICALLY_UNRESOLVED)])
        dynamic_classes[immutable] = frozen_classes[immutable]; dynamic_states[immutable] = -1; dynamic_regions[immutable] = 0
        if options.membership_source is FinalMembershipSource.SELECTED_GEOMETRY:
            classes, states, regions = dynamic_classes, dynamic_states, dynamic_regions
        else:
            agree = (frozen_classes == dynamic_classes) & (frozen_states == dynamic_states) & (frozen_regions == dynamic_regions)
            classes, states, regions = frozen_classes.copy(), frozen_states.copy(), frozen_regions.copy()
            disagreement = ~agree & ~immutable
            classes[disagreement] = int(FinalMembershipClass.ASSIGNMENT_CONFLICT)
            states[disagreement] = -1; regions[disagreement] = int(RegionMembership.OUTSIDE)
    conflicts = classes == int(FinalMembershipClass.ASSIGNMENT_CONFLICT)
    return FinalMembershipTable(
        temporal.sample_catalog_signature, temporal.membership.signature,
        None if geometry is None else geometry.signature, options.membership_source,
        classes, states, regions, conflicts, boundary,
    )


def _sample_segment_ids(catalog: FrameworkAlignedIonSampleCatalog) -> np.ndarray:
    frame_to_segment = {int(frame): int(seg) for frame, seg in zip(
        catalog.temporal_weighting.frame_indices, catalog.temporal_weighting.segment_ids, strict=True)}
    try:
        return np.asarray([frame_to_segment[int(frame)] for frame in catalog.frame_indices], dtype=np.int32)
    except KeyError as exc:
        raise FinalSegmentationInputError("A compact sample frame is absent from temporal weighting.") from exc


def _sequences(catalog: FrameworkAlignedIonSampleCatalog, stride: int) -> list[tuple[int, int, np.ndarray]]:
    segment_ids = _sample_segment_ids(catalog)
    frame_rank = {int(frame): rank for rank, frame in enumerate(catalog.temporal_weighting.frame_indices)}
    result: list[tuple[int, int, np.ndarray]] = []
    for atom in catalog.selected_atom_indices:
        indices = np.flatnonzero(catalog.atom_indices == atom)
        indices = indices[np.argsort(catalog.frame_indices[indices], kind="stable")]
        current: list[int] = []; current_segment: int | None = None; last_rank: int | None = None
        for sample in indices:
            i = int(sample); seg = int(segment_ids[i]); rank = frame_rank[int(catalog.frame_indices[i])]
            continuous = current and seg == current_segment and last_rank is not None and rank == last_rank + 1
            if current and not continuous:
                result.append((int(atom), int(current_segment), np.asarray(current[::stride], dtype=np.int64))); current = []
            if not current: current_segment = seg
            current.append(i); last_rank = rank
        if current:
            result.append((int(atom), int(current_segment), np.asarray(current[::stride], dtype=np.int64)))
    return result


def _qualified_core(sequence: np.ndarray, membership: FinalMembershipTable, minimum: int) -> np.ndarray:
    result = np.full(sequence.size, -1, dtype=np.int32)
    i = 0
    while i < sequence.size:
        sample = int(sequence[i]); state = int(membership.state_ids[sample])
        is_core = membership.membership_class[sample] == int(FinalMembershipClass.CORE)
        if not is_core:
            i += 1; continue
        j = i + 1
        while j < sequence.size:
            other = int(sequence[j])
            if membership.membership_class[other] != int(FinalMembershipClass.CORE) or int(membership.state_ids[other]) != state:
                break
            j += 1
        if j - i >= minimum:
            result[i:j] = state
        i = j
    return result


def _time(catalog: FrameworkAlignedIonSampleCatalog, samples: Sequence[int]) -> float:
    if not samples: return 0.0
    return float(np.sum(catalog.represented_time_weights[np.asarray(samples, dtype=np.int64)]))


def _interval_components(catalog: FrameworkAlignedIonSampleCatalog, membership: FinalMembershipTable, samples: Sequence[int], state: int) -> tuple[float, float, float]:
    core = basin = excursion = 0.0
    for sample in samples:
        weight = float(catalog.represented_time_weights[int(sample)])
        if int(membership.state_ids[int(sample)]) == state and membership.membership_class[int(sample)] == int(FinalMembershipClass.CORE): core += weight
        elif int(membership.state_ids[int(sample)]) == state and membership.membership_class[int(sample)] == int(FinalMembershipClass.BASIN): basin += weight
        else: excursion += weight
    return core, basin, excursion


def _segment_once(
    catalog: FrameworkAlignedIonSampleCatalog,
    membership: FinalMembershipTable,
    *, entry_frames: int, exit_frames: int, stride: int,
    boundary_policy: BoundaryInducedPolicy, recrossing_window: int,
    collect_records: bool = True,
) -> tuple[list[FinalResidenceInterval], list[FinalPassageInterval], np.ndarray, np.ndarray, np.ndarray]:
    n = catalog.n_samples
    assigned = np.full(n, -1, dtype=np.int32); residence_ids = np.full(n, -1, dtype=np.int32); passage_ids = np.full(n, -1, dtype=np.int32)
    residences: list[FinalResidenceInterval] = []; passages: list[FinalPassageInterval] = []
    for atom, segment, sequence in _sequences(catalog, stride):
        if sequence.size == 0: continue
        qcore = _qualified_core(sequence, membership, entry_frames)
        active: int | None = None; residence_samples: list[int] = []; pending: list[int] = []
        active_left = False; open_source: int | None = None; open_samples: list[int] = []
        open_unknown = False; open_conflict = False; open_boundary = False

        def close_residence(right_censored: bool) -> None:
            nonlocal residence_samples
            if active is None or not residence_samples: return
            core, basin, excursion = _interval_components(catalog, membership, residence_samples, active)
            rid = len(residences)
            interval = FinalResidenceInterval(rid, atom, active, segment, np.asarray(residence_samples, dtype=np.int64),
                                              _time(catalog, residence_samples), core, basin, excursion,
                                              active_left, right_censored)
            residences.append(interval)
            for s in residence_samples:
                assigned[s] = active; residence_ids[s] = rid
            residence_samples = []

        def add_passage(target: int | None, outcome: FinalPassageOutcome, samples: Sequence[int], *, counted: bool) -> None:
            nonlocal open_source, open_unknown, open_conflict, open_boundary
            boundary_induced = open_boundary or any(bool(membership.boundary_induced_mask[s]) for s in samples)
            final_outcome = outcome; final_counted = counted
            if boundary_induced and outcome is FinalPassageOutcome.RESOLVED_TRANSITION:
                if boundary_policy is BoundaryInducedPolicy.MARK_UNRESOLVED:
                    final_outcome = FinalPassageOutcome.BOUNDARY_INDUCED; final_counted = False
                elif boundary_policy is BoundaryInducedPolicy.EXCLUDE_EVENT:
                    final_outcome = FinalPassageOutcome.BOUNDARY_INDUCED; final_counted = False
            pid = len(passages)
            interval = FinalPassageInterval(pid, atom, segment, open_source, target,
                                            np.asarray(samples, dtype=np.int64), _time(catalog, list(samples)),
                                            final_outcome, open_unknown, open_conflict, boundary_induced, final_counted)
            passages.append(interval)
            for s in samples:
                if passage_ids[s] < 0: passage_ids[s] = pid
            open_source = None; open_unknown = open_conflict = open_boundary = False

        for pos, sample_value in enumerate(sequence):
            sample = int(sample_value); state = int(membership.state_ids[sample]); cls = FinalMembershipClass(int(membership.membership_class[sample]))
            qualified = int(qcore[pos])
            in_active_basin = active is not None and state == active and cls in (FinalMembershipClass.CORE, FinalMembershipClass.BASIN)
            if active is not None:
                if in_active_basin:
                    if pending:
                        open_source = active
                        open_unknown = any(FinalMembershipClass(int(membership.membership_class[s])) in (FinalMembershipClass.UNSUPPORTED_UNKNOWN, FinalMembershipClass.NUMERICALLY_UNRESOLVED) for s in pending)
                        open_conflict = any(bool(membership.conflict_mask[s]) for s in pending)
                        open_boundary = any(bool(membership.boundary_induced_mask[s]) for s in pending)
                        add_passage(active, FinalPassageOutcome.RETAINED_EXCURSION, pending, counted=False)
                        residence_samples.extend(pending); pending = []
                    residence_samples.append(sample)
                    continue
                if qualified >= 0 and qualified != active:
                    source = active; close_residence(False)
                    open_source = source; open_samples = [*pending]
                    open_unknown |= any(FinalMembershipClass(int(membership.membership_class[s])) in (FinalMembershipClass.UNSUPPORTED_UNKNOWN, FinalMembershipClass.NUMERICALLY_UNRESOLVED) for s in open_samples)
                    open_conflict |= any(bool(membership.conflict_mask[s]) for s in open_samples)
                    open_boundary |= any(bool(membership.boundary_induced_mask[s]) for s in open_samples)
                    if open_unknown:
                        outcome = FinalPassageOutcome.UNRESOLVED_GAP; counted = False
                    elif open_conflict:
                        outcome = FinalPassageOutcome.ASSIGNMENT_CONFLICT; counted = False
                    else:
                        outcome = FinalPassageOutcome.RESOLVED_TRANSITION; counted = True
                    add_passage(qualified, outcome, open_samples, counted=counted)
                    active = qualified; active_left = False; residence_samples = [sample]; pending = []; open_samples = []
                    continue
                pending.append(sample)
                if len(pending) >= exit_frames:
                    source = active; close_residence(False); active = None
                    open_source = source; open_samples = list(pending); pending = []
                    open_unknown = any(FinalMembershipClass(int(membership.membership_class[s])) in (FinalMembershipClass.UNSUPPORTED_UNKNOWN, FinalMembershipClass.NUMERICALLY_UNRESOLVED) for s in open_samples)
                    open_conflict = any(bool(membership.conflict_mask[s]) for s in open_samples)
                    open_boundary = any(bool(membership.boundary_induced_mask[s]) for s in open_samples)
                continue

            if open_source is not None:
                if sample not in open_samples: open_samples.append(sample)
                open_unknown |= cls in (FinalMembershipClass.UNSUPPORTED_UNKNOWN, FinalMembershipClass.NUMERICALLY_UNRESOLVED)
                open_conflict |= cls is FinalMembershipClass.ASSIGNMENT_CONFLICT
                open_boundary |= bool(membership.boundary_induced_mask[sample])
                if qualified >= 0:
                    if open_unknown:
                        outcome = FinalPassageOutcome.UNRESOLVED_GAP; counted = False
                    elif open_conflict:
                        outcome = FinalPassageOutcome.ASSIGNMENT_CONFLICT; counted = False
                    elif qualified == open_source:
                        outcome = FinalPassageOutcome.RECROSSING if len(open_samples) <= recrossing_window else FinalPassageOutcome.RETURN_EXCURSION
                        counted = False
                    else:
                        outcome = FinalPassageOutcome.RESOLVED_TRANSITION; counted = True
                    target = qualified; add_passage(target, outcome, open_samples[:-1], counted=counted)
                    active = target; active_left = False; residence_samples = [sample]; open_samples = []
                continue

            if qualified >= 0:
                active = qualified; active_left = pos == 0; residence_samples = [sample]

        if active is not None:
            if pending:
                residence_samples.extend(pending)
            close_residence(True)
        elif open_source is not None:
            add_passage(None, FinalPassageOutcome.RIGHT_CENSORED_EXIT, open_samples, counted=False)
    return residences, passages, assigned, residence_ids, passage_ids


def _frame_weights(catalog: FrameworkAlignedIonSampleCatalog) -> dict[int, float]:
    return {int(frame): float(weight) for frame, weight, valid in zip(
        catalog.temporal_weighting.frame_indices, catalog.temporal_weighting.represented_time_weights,
        catalog.temporal_weighting.temporal_mask, strict=True) if valid}


def _state_statistics(
    catalog: FrameworkAlignedIonSampleCatalog,
    membership: FinalMembershipTable,
    residences: Sequence[FinalResidenceInterval],
    passages: Sequence[FinalPassageInterval],
    assigned: np.ndarray,
) -> tuple[StateResidenceStatistics, ...]:
    state_ids = sorted({int(v) for v in membership.state_ids if v >= 0})
    frame_weights = _frame_weights(catalog); total_time = float(sum(frame_weights.values()))
    by_frame: dict[int, list[int]] = {}
    ambiguous_by_frame: dict[int, int] = {}
    for i, frame in enumerate(catalog.frame_indices):
        f = int(frame)
        if f not in frame_weights: continue
        by_frame.setdefault(f, []).append(int(assigned[i]))
        if membership.membership_class[i] in (
            int(FinalMembershipClass.UNSUPPORTED_UNKNOWN), int(FinalMembershipClass.NUMERICALLY_UNRESOLVED),
            int(FinalMembershipClass.ASSIGNMENT_CONFLICT)):
            ambiguous_by_frame[f] = ambiguous_by_frame.get(f, 0) + 1
    result: list[StateResidenceStatistics] = []
    for state in state_ids:
        state_res = [r for r in residences if r.state_id == state]
        uncensored = [r for r in state_res if not r.left_censored and not r.right_censored]
        durations = np.asarray([r.represented_time for r in uncensored], dtype=float)
        departures = sum(1 for p in passages if p.source_state_id == state and p.counted_transition)
        lower_occ = upper_occ = vacancy_lower = vacancy_upper = multiple_lower = multiple_upper = 0.0
        for frame, weight in frame_weights.items():
            values = by_frame.get(frame, [])
            count = sum(v == state for v in values); ambiguous = ambiguous_by_frame.get(frame, 0)
            lower_occ += weight * count; upper_occ += weight * (count + ambiguous)
            if count == 0 and ambiguous == 0: vacancy_lower += weight
            if count == 0: vacancy_upper += weight
            if count > 1: multiple_lower += weight
            if count + ambiguous > 1: multiple_upper += weight
        scale = max(total_time, np.finfo(float).eps)
        result.append(StateResidenceStatistics(
            state, len(state_res), len(uncensored), departures,
            float(sum(r.represented_time for r in state_res)),
            None if durations.size == 0 else float(np.mean(durations)),
            None if durations.size == 0 else float(np.median(durations)),
            lower_occ / scale, upper_occ / scale,
            vacancy_lower / scale, vacancy_upper / scale,
            multiple_lower / scale, multiple_upper / scale,
        ))
    return tuple(result)


def _occupancy_map(stats: Sequence[StateResidenceStatistics]) -> dict[int, float]:
    return {v.state_id: v.mean_occupancy_lower for v in stats}


def _sensitivity(
    catalog: FrameworkAlignedIonSampleCatalog,
    membership: FinalMembershipTable,
    options: FinalSegmentationOptions,
    baseline_residences: Sequence[FinalResidenceInterval],
    baseline_passages: Sequence[FinalPassageInterval],
    baseline_stats: Sequence[StateResidenceStatistics],
    resources: FinalSegmentationResourcePolicy,
) -> tuple[tuple[SegmentationSensitivityRecord, ...], SegmentationStabilityStatus]:
    if catalog.temporal_weighting.frame_semantics is FrameSemantics.ENSEMBLE:
        return (), SegmentationStabilityStatus.ENSEMBLE_UNAVAILABLE
    settings = [(e, x, s) for e, x in options.sensitivity_thresholds for s in options.sensitivity_stride_factors]
    if len(settings) > resources.max_sensitivity_runs:
        raise FinalSegmentationResourceError("Sensitivity runs exceed max_sensitivity_runs.")
    baseline_transition = sum(p.counted_transition for p in baseline_passages)
    baseline_occupancy = _occupancy_map(baseline_stats)
    records: list[SegmentationSensitivityRecord] = []
    worst_transition = 0.0; worst_occupancy = 0.0
    for entry, exit_frames, stride in settings:
        if entry == options.minimum_core_entry_frames and exit_frames == options.minimum_basin_exit_frames and stride == 1:
            residences = list(baseline_residences); passages = list(baseline_passages); stats = list(baseline_stats)
        else:
            residences, passages, assigned, _, _ = _segment_once(
                catalog, membership, entry_frames=entry, exit_frames=exit_frames, stride=stride,
                boundary_policy=options.boundary_induced_policy, recrossing_window=options.recrossing_window_frames)
            stats = list(_state_statistics(catalog, membership, residences, passages, assigned))
        transitions = sum(p.counted_transition for p in passages)
        transition_change = abs(transitions - baseline_transition) / max(1, baseline_transition)
        occupancy = _occupancy_map(stats)
        keys = set(baseline_occupancy) | set(occupancy)
        occupancy_change = max((abs(occupancy.get(k, 0.0) - baseline_occupancy.get(k, 0.0)) for k in keys), default=0.0)
        worst_transition = max(worst_transition, transition_change); worst_occupancy = max(worst_occupancy, occupancy_change)
        records.append(SegmentationSensitivityRecord(entry, exit_frames, stride, len(residences), transitions,
            tuple(sorted(occupancy.items())), transition_change, occupancy_change))
    if baseline_transition < options.minimum_events_for_stability:
        status = SegmentationStabilityStatus.INSUFFICIENT_EVENTS
    elif worst_transition <= options.maximum_transition_count_relative_change and worst_occupancy <= options.maximum_occupancy_absolute_change:
        status = SegmentationStabilityStatus.STABLE
    else:
        status = SegmentationStabilityStatus.UNSTABLE
    return tuple(records), status


def prepare_final_hysteretic_segmentation(
    sample_catalog: FrameworkAlignedIonSampleCatalog,
    validated_frozen_catalog: Any,
    provisional_temporal_catalog: ProvisionalTemporalAssignmentCatalog,
    *,
    geometry_catalog: GeometryConditionedSiteCatalog | None = None,
    options: FinalSegmentationOptions | None = None,
    resources: FinalSegmentationResourcePolicy | None = None,
) -> FinalHystereticSegmentationCatalog:
    """Build final source-bound hysteretic state histories and residence statistics."""
    options = options or FinalSegmentationOptions()
    resources = resources or FinalSegmentationResourcePolicy()
    validated_signature = _sha(getattr(validated_frozen_catalog, "signature", None), "validated_frozen_catalog.signature")
    if provisional_temporal_catalog.sample_catalog_signature != sample_catalog.signature:
        raise FinalSegmentationInputError("E4 temporal assignments do not belong to the supplied sample catalog.")
    validated_sample = getattr(validated_frozen_catalog, "sample_catalog_signature", None)
    if validated_sample is not None and validated_sample != sample_catalog.signature:
        raise FinalSegmentationInputError("E5 validated states do not belong to the supplied sample catalog.")
    validated_temporal = getattr(validated_frozen_catalog, "temporal_assignment_signature", None)
    if validated_temporal is not None and validated_temporal != provisional_temporal_catalog.signature:
        raise FinalSegmentationInputError("E5 validated states do not belong to the supplied E4 temporal catalog.")
    validated_density = getattr(validated_frozen_catalog, "density_estimate_signature", None)
    if validated_density is not None and validated_density != provisional_temporal_catalog.density_estimate_signature:
        raise FinalSegmentationInputError("E5 and E4 density-estimate signatures disagree.")
    validated_attractors = getattr(validated_frozen_catalog, "attractor_catalog_signature", None)
    if validated_attractors is not None and validated_attractors != provisional_temporal_catalog.attractor_catalog_signature:
        raise FinalSegmentationInputError("E5 and E4 attractor-catalog signatures disagree.")
    if geometry_catalog is not None and geometry_catalog.validated_frozen_catalog_signature != validated_signature:
        raise FinalSegmentationInputError("E5b geometry catalog does not belong to the supplied validated catalog.")
    if sample_catalog.n_samples > resources.max_samples:
        raise FinalSegmentationResourceError("samples exceed max_samples")
    membership = _prepare_final_membership(provisional_temporal_catalog, geometry_catalog, options)
    state_ids_present = {int(v) for v in membership.state_ids if v >= 0}
    state_count = len(state_ids_present)
    validated_states = getattr(validated_frozen_catalog, "states", None)
    if validated_states is not None:
        valid_state_ids = {int(v.state_id) for v in validated_states}
        if not state_ids_present.issubset(valid_state_ids):
            raise FinalSegmentationInputError("Final membership contains a state absent from the validated E5 catalog.")
    if state_count > resources.max_states:
        raise FinalSegmentationResourceError("states exceed max_states")
    if sample_catalog.temporal_weighting.frame_semantics is FrameSemantics.ENSEMBLE:
        residences: list[FinalResidenceInterval] = []; passages: list[FinalPassageInterval] = []
        assigned = np.full(sample_catalog.n_samples, -1, dtype=np.int32)
        residence_ids = np.full(sample_catalog.n_samples, -1, dtype=np.int32)
        passage_ids = np.full(sample_catalog.n_samples, -1, dtype=np.int32)
    else:
        residences, passages, assigned, residence_ids, passage_ids = _segment_once(
            sample_catalog, membership, entry_frames=options.minimum_core_entry_frames,
            exit_frames=options.minimum_basin_exit_frames, stride=1,
            boundary_policy=options.boundary_induced_policy, recrossing_window=options.recrossing_window_frames)
    if len(residences) > resources.max_residences:
        raise FinalSegmentationResourceError("residences exceed max_residences")
    if len(passages) > resources.max_passages:
        raise FinalSegmentationResourceError("passages exceed max_passages")
    stats = _state_statistics(sample_catalog, membership, residences, passages, assigned)
    sensitivity, stability = _sensitivity(sample_catalog, membership, options, residences, passages, stats, resources)
    estimated_bytes = int(
        membership.membership_class.nbytes + membership.state_ids.nbytes + membership.region_membership.nbytes +
        membership.conflict_mask.nbytes + membership.boundary_induced_mask.nbytes + assigned.nbytes +
        residence_ids.nbytes + passage_ids.nbytes + sum(r.sample_indices.nbytes for r in residences) +
        sum(p.sample_indices.nbytes for p in passages))
    if estimated_bytes > resources.max_output_bytes:
        raise FinalSegmentationResourceError("estimated output exceeds max_output_bytes")
    return FinalHystereticSegmentationCatalog(
        sample_catalog.signature, validated_signature, provisional_temporal_catalog.signature,
        None if geometry_catalog is None else geometry_catalog.signature, options, resources, membership,
        assigned, residence_ids, passage_ids, tuple(residences), tuple(passages), stats, sensitivity, stability,
        metadata={
            "weight_units": sample_catalog.temporal_weighting.weight_units,
            "frame_semantics": sample_catalog.temporal_weighting.frame_semantics.value,
            "immutable_raw_labels": True,
            "nearest_center_fill": False,
            "transition_paths_deferred_to_stage": "11E6b",
            "rates_deferred": True,
        },
    )


__all__ = [
    "FINAL_SEGMENTATION_STAGE", "FINAL_SEGMENTATION_OPTIONS_SCHEMA", "FINAL_SEGMENTATION_RESOURCES_SCHEMA",
    "FINAL_MEMBERSHIP_TABLE_SCHEMA", "FINAL_RESIDENCE_INTERVAL_SCHEMA", "FINAL_PASSAGE_INTERVAL_SCHEMA",
    "STATE_RESIDENCE_STATISTICS_SCHEMA", "SEGMENTATION_SENSITIVITY_SCHEMA", "FINAL_SEGMENTATION_CATALOG_SCHEMA",
    "FinalSegmentationError", "FinalSegmentationInputError", "FinalSegmentationResourceError",
    "FinalSegmentationSerializationError", "FinalMembershipClass", "FinalMembershipSource",
    "BoundaryInducedPolicy", "FinalPassageOutcome", "SegmentationStabilityStatus",
    "FinalSegmentationOptions", "FinalSegmentationResourcePolicy", "FinalMembershipTable",
    "FinalResidenceInterval", "FinalPassageInterval", "StateResidenceStatistics",
    "SegmentationSensitivityRecord", "FinalHystereticSegmentationCatalog",
    "prepare_final_hysteretic_segmentation",
]
