"""Stage-11E0b registered position-force sample catalogs.

The catalog is the compact evidence boundary between Stage C0 registration and
later statistical site discovery.  It stores one species at a time, retains
registered positions and transformed force covectors, and keeps temporal,
structural, position, force, joint, and PMF-admissible evidence masks separate.
Structural descriptors are resolved lazily after a candidate has been associated
with a persistent framework identity.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from types import MappingProxyType
from typing import Any, Literal, Protocol

import numpy as np
from numpy.typing import NDArray

from ..collection import AtomisticFrameCollection
from ..coordinates.contracts import (
    EvidenceState,
    ForceAdmissibilityContract,
    ForceSourceProvenance,
    GeometricForceTransformStatus,
    PMFForceAdmissibilityStatus,
)
from ..coordinates.registration import FrameRegistrationResult
from ..semantics import FrameSemantics
from .topology_catalog import TopologyCatalog, TopologySegmentStatus

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
BoolArray = NDArray[np.bool_]

TRAJECTORY_SEGMENT_WEIGHTING_SCHEMA = "mdstats.trajectory-segment-weighting.v1"
TOPOLOGY_REGIME_ASSIGNMENT_SCHEMA = "mdstats.topology-regime-assignment.v1"
SAMPLING_STATE_PROVENANCE_SCHEMA = "mdstats.sampling-state-provenance.v1"
PMF_TEMPERATURE_PROVENANCE_SCHEMA = "mdstats.pmf-temperature-provenance.v1"
SAMPLE_FORCE_PROVENANCE_SCHEMA = "mdstats.sample-force-provenance.v1"
SAMPLE_EVIDENCE_MASKS_SCHEMA = "mdstats.sample-evidence-masks.v1"
FRAME_REGISTRATION_GROUP_SCHEMA = "mdstats.frame-registration-group.v1"
FRAMEWORK_ALIGNED_ION_SAMPLE_CATALOG_SCHEMA = (
    "mdstats.framework-aligned-ion-sample-catalog.v1"
)
SITE_SAMPLE_DIGEST_ALGORITHM = "sha256-canonical-json-and-array-bytes-v1"
SITE_SAMPLE_STAGE = "11E0b"


class SiteSampleError(ValueError):
    """Base error for Stage-11E0b sample catalogs."""


class SiteSampleInputError(SiteSampleError):
    """Raised when source, registration, masks, or species inputs disagree."""


class TemporalWeightingError(SiteSampleError):
    """Raised when represented-time segments are ambiguous or inconsistent."""


class RegistrationGroupError(SiteSampleError):
    """Raised when trajectories do not share one certified periodic domain."""


class SampleCatalogSerializationError(SiteSampleError):
    """Raised when a serialized catalog is malformed or tampered with."""


class SegmentKind(str, Enum):
    HEATING = "heating"
    EQUILIBRATION = "equilibration"
    PRODUCTION = "production"
    OTHER = "other"
    UNKNOWN = "unknown"


class EquilibriumStatus(str, Enum):
    DECLARED_EQUILIBRIUM = "declared_equilibrium"
    DECLARED_NONEQUILIBRIUM = "declared_nonequilibrium"
    UNKNOWN = "unknown"


class StationarityStatus(str, Enum):
    TESTED_STATIONARY = "tested_stationary"
    ASSUMED_STATIONARY = "assumed_stationary"
    NONSTATIONARY = "nonstationary"
    UNKNOWN = "unknown"


class PMFTemperatureStatus(str, Enum):
    DECLARED_CONSTANT = "declared_constant"
    FRAMEWISE_OBSERVED = "framewise_observed"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


EvidenceChannel = Literal["position", "force", "joint", "pmf_force"]


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest_payload(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    hasher = hashlib.sha256()
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()


def _readonly_array(
    value: Any,
    *,
    dtype: np.dtype[Any] | type,
    ndim: int,
    name: str,
    shape: tuple[int, ...] | None = None,
) -> np.ndarray:
    array = np.array(value, dtype=dtype, copy=True)
    if array.ndim != ndim:
        raise SiteSampleInputError(
            f"{name} must have {ndim} dimensions; received {array.shape}."
        )
    if shape is not None and array.shape != shape:
        raise SiteSampleInputError(
            f"{name} must have shape {shape}; received {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise SiteSampleInputError(f"{name} contains non-finite values.")
    array.setflags(write=False)
    return array


def _freeze_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise SiteSampleInputError("Metadata contains a non-finite float.")
        return number
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True)
        array.setflags(write=False)
        return array
    if isinstance(value, Mapping):
        return MappingProxyType(
            {
                str(key): _freeze_value(item)
                for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            }
        )
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_value(item) for item in value)
    raise SiteSampleInputError(
        f"Metadata contains unsupported value {type(value).__name__}."
    )


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, tuple):
        return [_json_value(item) for item in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise SiteSampleInputError(
        f"Cannot serialize metadata value {type(value).__name__}."
    )


def _enum(enum_type: type[Enum], value: Any, *, name: str) -> Enum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise SiteSampleInputError(f"{name} must be one of: {allowed}.") from exc


@dataclass(frozen=True, slots=True)
class TrajectorySegmentWeighting:
    """Segment-aware represented-time weights and temporal evidence selection."""

    frame_semantics: FrameSemantics
    frame_indices: IntArray
    frame_ids: IntArray
    segment_ids: Int32Array
    segment_start_mask: BoolArray
    segment_kinds: tuple[SegmentKind, ...]
    included_segment_ids: tuple[int, ...]
    represented_time_weights: FloatArray
    temporal_mask: BoolArray
    weight_units: str
    source_times: FloatArray | None
    signature: str = ""

    def __post_init__(self) -> None:
        semantics = FrameSemantics(self.frame_semantics)
        frames = _readonly_array(
            self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices"
        )
        frame_ids = _readonly_array(
            self.frame_ids,
            dtype=np.int64,
            ndim=1,
            name="frame_ids",
            shape=frames.shape,
        )
        segment_ids = _readonly_array(
            self.segment_ids,
            dtype=np.int32,
            ndim=1,
            name="segment_ids",
            shape=frames.shape,
        )
        starts = _readonly_array(
            self.segment_start_mask,
            dtype=np.bool_,
            ndim=1,
            name="segment_start_mask",
            shape=frames.shape,
        )
        weights = _readonly_array(
            self.represented_time_weights,
            dtype=np.float64,
            ndim=1,
            name="represented_time_weights",
            shape=frames.shape,
        )
        temporal = _readonly_array(
            self.temporal_mask,
            dtype=np.bool_,
            ndim=1,
            name="temporal_mask",
            shape=frames.shape,
        )
        if frames.size == 0 or not starts[0]:
            raise TemporalWeightingError(
                "segment_start_mask must mark the first nonempty frame sequence."
            )
        if np.any(weights < 0.0):
            raise TemporalWeightingError(
                "represented_time_weights must be nonnegative."
            )
        expected_ids = np.cumsum(starts.astype(np.int32)) - 1
        if not np.array_equal(segment_ids, expected_ids):
            raise TemporalWeightingError(
                "segment_ids must be the dense cumulative segment-start labels."
            )
        n_segments = int(segment_ids[-1]) + 1
        kinds = tuple(SegmentKind(item) for item in self.segment_kinds)
        if len(kinds) != n_segments:
            raise TemporalWeightingError(
                "segment_kinds must contain one entry per dense segment ID."
            )
        included = tuple(sorted({int(item) for item in self.included_segment_ids}))
        if any(item < 0 or item >= n_segments for item in included):
            raise TemporalWeightingError(
                "included_segment_ids contain an invalid segment ID."
            )
        expected_temporal = np.isin(segment_ids, np.asarray(included, dtype=np.int32))
        expected_temporal &= weights > 0.0
        if not np.array_equal(temporal, expected_temporal):
            raise TemporalWeightingError(
                "temporal_mask must select exactly positive-weight samples from the "
                "declared included segments."
            )
        if not isinstance(self.weight_units, str) or not self.weight_units:
            raise TemporalWeightingError("weight_units must be a nonempty string.")
        times = None
        if self.source_times is not None:
            times = _readonly_array(
                self.source_times,
                dtype=np.float64,
                ndim=1,
                name="source_times",
                shape=frames.shape,
            )
        payload = {
            "schema": TRAJECTORY_SEGMENT_WEIGHTING_SCHEMA,
            "frame_semantics": semantics.value,
            "frame_indices_digest": _array_digest(frames),
            "frame_ids_digest": _array_digest(frame_ids),
            "segment_ids_digest": _array_digest(segment_ids),
            "segment_start_mask_digest": _array_digest(starts),
            "segment_kinds": [item.value for item in kinds],
            "included_segment_ids": list(included),
            "represented_time_weights_digest": _array_digest(weights),
            "temporal_mask_digest": _array_digest(temporal),
            "weight_units": self.weight_units,
            "source_times_digest": None if times is None else _array_digest(times),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise TemporalWeightingError(
                "Trajectory-segment-weighting signature is inconsistent."
            )
        object.__setattr__(self, "frame_semantics", semantics)
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "segment_ids", segment_ids)
        object.__setattr__(self, "segment_start_mask", starts)
        object.__setattr__(self, "segment_kinds", kinds)
        object.__setattr__(self, "included_segment_ids", included)
        object.__setattr__(self, "represented_time_weights", weights)
        object.__setattr__(self, "temporal_mask", temporal)
        object.__setattr__(self, "source_times", times)
        object.__setattr__(self, "signature", expected)

    @property
    def n_segments(self) -> int:
        return len(self.segment_kinds)

    @property
    def included_represented_time(self) -> float:
        return float(np.sum(self.represented_time_weights[self.temporal_mask]))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRAJECTORY_SEGMENT_WEIGHTING_SCHEMA,
            "frame_semantics": self.frame_semantics.value,
            "frame_indices": self.frame_indices.tolist(),
            "frame_ids": self.frame_ids.tolist(),
            "segment_ids": self.segment_ids.tolist(),
            "segment_start_mask": self.segment_start_mask.tolist(),
            "segment_kinds": [item.value for item in self.segment_kinds],
            "included_segment_ids": list(self.included_segment_ids),
            "represented_time_weights": self.represented_time_weights.tolist(),
            "temporal_mask": self.temporal_mask.tolist(),
            "weight_units": self.weight_units,
            "source_times": None if self.source_times is None else self.source_times.tolist(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrajectorySegmentWeighting":
        if payload.get("schema") != TRAJECTORY_SEGMENT_WEIGHTING_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported trajectory-segment-weighting schema."
            )
        return cls(
            frame_semantics=FrameSemantics(payload["frame_semantics"]),
            frame_indices=np.asarray(payload["frame_indices"], dtype=np.int64),
            frame_ids=np.asarray(payload["frame_ids"], dtype=np.int64),
            segment_ids=np.asarray(payload["segment_ids"], dtype=np.int32),
            segment_start_mask=np.asarray(
                payload["segment_start_mask"], dtype=np.bool_
            ),
            segment_kinds=tuple(SegmentKind(item) for item in payload["segment_kinds"]),
            included_segment_ids=tuple(
                int(item) for item in payload["included_segment_ids"]
            ),
            represented_time_weights=np.asarray(
                payload["represented_time_weights"], dtype=np.float64
            ),
            temporal_mask=np.asarray(payload["temporal_mask"], dtype=np.bool_),
            weight_units=str(payload["weight_units"]),
            source_times=(
                None
                if payload.get("source_times") is None
                else np.asarray(payload["source_times"], dtype=np.float64)
            ),
            signature=str(payload.get("signature", "")),
        )


def _segment_midpoint_weights(times: np.ndarray, starts: np.ndarray) -> np.ndarray:
    weights = np.zeros(times.shape, dtype=np.float64)
    start_indices = np.flatnonzero(starts)
    stops = np.concatenate([start_indices[1:], np.array([times.size], dtype=np.int64)])
    for start, stop in zip(start_indices, stops, strict=True):
        count = int(stop - start)
        if count < 2:
            raise TemporalWeightingError(
                "A trajectory segment with one frame has no represented-time interval; "
                "supply explicit_frame_weights or merge the segment."
            )
        local = times[start:stop]
        dt = np.diff(local)
        if np.any(dt <= 0.0):
            raise TemporalWeightingError(
                "Trajectory times must increase strictly within every segment."
            )
        weights[start] = 0.5 * dt[0]
        weights[stop - 1] = 0.5 * dt[-1]
        if count > 2:
            weights[start + 1 : stop - 1] = 0.5 * (local[2:] - local[:-2])
    return weights


def prepare_trajectory_segment_weighting(
    collection: AtomisticFrameCollection,
    *,
    registration: FrameRegistrationResult | None = None,
    segment_start_frame_indices: Sequence[int] = (),
    segment_kinds: Sequence[SegmentKind | str] | None = None,
    included_segment_ids: Sequence[int] | None = None,
    allow_heating_production_mixture: bool = False,
    explicit_frame_weights: Sequence[float] | np.ndarray | None = None,
    explicit_weight_units: str = "frame",
) -> TrajectorySegmentWeighting:
    """Build segment-aware represented-time weights.

    For trajectories with a physical time axis, each frame receives the adjacent
    half-intervals within its declared continuous segment.  No interval crosses a
    reset boundary.  Multiple trajectory segments require an explicit included
    segment list, preventing heating and production segments from being pooled by
    default.  Independent ensembles receive equal frame weights and no temporal
    continuity claim.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be AtomisticFrameCollection.")
    n_frames = collection.n_frames
    starts = np.zeros(n_frames, dtype=np.bool_)
    starts[0] = True
    if collection.is_ensemble:
        starts[:] = True
    else:
        for value in segment_start_frame_indices:
            index = int(value)
            if index <= 0 or index >= n_frames:
                raise TemporalWeightingError(
                    "segment_start_frame_indices must lie strictly inside the trajectory."
                )
            starts[index] = True
        if registration is not None and registration.translation_branch_lift is not None:
            branch_starts = np.asarray(
                registration.translation_branch_lift.segment_start_mask, dtype=np.bool_
            )
            if branch_starts.shape != starts.shape:
                raise TemporalWeightingError(
                    "Registration branch-reset shape disagrees with the collection."
                )
            starts |= branch_starts
    segment_ids = np.cumsum(starts.astype(np.int32)) - 1
    n_segments = int(segment_ids[-1]) + 1
    if segment_kinds is None:
        kinds = tuple(SegmentKind.UNKNOWN for _ in range(n_segments))
    else:
        kinds = tuple(SegmentKind(item) for item in segment_kinds)
        if len(kinds) != n_segments:
            raise TemporalWeightingError(
                f"segment_kinds must contain {n_segments} entries."
            )

    if included_segment_ids is None:
        if collection.is_trajectory and n_segments > 1:
            raise TemporalWeightingError(
                "A multi-segment trajectory requires explicit included_segment_ids; "
                "segments are not pooled silently."
            )
        included = tuple(range(n_segments))
    else:
        included = tuple(sorted({int(item) for item in included_segment_ids}))
        if not included:
            raise TemporalWeightingError("included_segment_ids must not be empty.")
        if any(item < 0 or item >= n_segments for item in included):
            raise TemporalWeightingError(
                "included_segment_ids contain an invalid segment ID."
            )
    selected_kinds = {kinds[item] for item in included}
    if (
        SegmentKind.HEATING in selected_kinds
        and SegmentKind.PRODUCTION in selected_kinds
        and not allow_heating_production_mixture
    ):
        raise TemporalWeightingError(
            "Heating and production segments may not be pooled unless "
            "allow_heating_production_mixture=True is explicit."
        )

    source_times: np.ndarray | None
    if explicit_frame_weights is not None:
        weights = np.asarray(explicit_frame_weights, dtype=np.float64)
        if weights.shape != (n_frames,) or np.any(~np.isfinite(weights)) or np.any(weights < 0.0):
            raise TemporalWeightingError(
                "explicit_frame_weights must be finite, nonnegative, and frame-aligned."
            )
        units = str(explicit_weight_units)
        source_times = None if collection.times is None else np.asarray(collection.times)
    elif collection.is_ensemble:
        weights = np.ones(n_frames, dtype=np.float64)
        units = "frame"
        source_times = None
    else:
        times = collection.require_time_axis("Stage-11E0b represented-time weighting")
        source_times = np.asarray(times, dtype=np.float64)
        weights = _segment_midpoint_weights(source_times, starts)
        units = "ps"
    temporal = np.isin(segment_ids, np.asarray(included, dtype=np.int32))
    temporal &= weights > 0.0
    return TrajectorySegmentWeighting(
        frame_semantics=collection.frame_semantics,
        frame_indices=np.arange(n_frames, dtype=np.int64),
        frame_ids=collection.frame_ids,
        segment_ids=segment_ids,
        segment_start_mask=starts,
        segment_kinds=kinds,
        included_segment_ids=included,
        represented_time_weights=weights,
        temporal_mask=temporal,
        weight_units=units,
        source_times=source_times,
    )


@dataclass(frozen=True, slots=True)
class TopologyRegimeAssignment:
    """Framewise exact topology regimes and connectivity-flicker evidence."""

    frame_indices: IntArray
    frame_ids: IntArray
    topology_regime_ids: Int32Array
    connectivity_flicker_mask: BoolArray
    structural_mask: BoolArray
    source_topology_catalog_digest: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        frames = _readonly_array(
            self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices"
        )
        frame_ids = _readonly_array(
            self.frame_ids,
            dtype=np.int64,
            ndim=1,
            name="frame_ids",
            shape=frames.shape,
        )
        regimes = _readonly_array(
            self.topology_regime_ids,
            dtype=np.int32,
            ndim=1,
            name="topology_regime_ids",
            shape=frames.shape,
        )
        flicker = _readonly_array(
            self.connectivity_flicker_mask,
            dtype=np.bool_,
            ndim=1,
            name="connectivity_flicker_mask",
            shape=frames.shape,
        )
        structural = _readonly_array(
            self.structural_mask,
            dtype=np.bool_,
            ndim=1,
            name="structural_mask",
            shape=frames.shape,
        )
        if np.any(flicker & structural):
            raise SiteSampleInputError(
                "Connectivity-flicker frames cannot simultaneously be structural evidence."
            )
        if self.source_topology_catalog_digest is not None and len(
            self.source_topology_catalog_digest
        ) != 64:
            raise SiteSampleInputError(
                "source_topology_catalog_digest must be SHA-256 or None."
            )
        payload = {
            "schema": TOPOLOGY_REGIME_ASSIGNMENT_SCHEMA,
            "frame_indices_digest": _array_digest(frames),
            "frame_ids_digest": _array_digest(frame_ids),
            "topology_regime_ids_digest": _array_digest(regimes),
            "connectivity_flicker_mask_digest": _array_digest(flicker),
            "structural_mask_digest": _array_digest(structural),
            "source_topology_catalog_digest": self.source_topology_catalog_digest,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise SiteSampleInputError(
                "Topology-regime-assignment signature is inconsistent."
            )
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "topology_regime_ids", regimes)
        object.__setattr__(self, "connectivity_flicker_mask", flicker)
        object.__setattr__(self, "structural_mask", structural)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TOPOLOGY_REGIME_ASSIGNMENT_SCHEMA,
            "frame_indices": self.frame_indices.tolist(),
            "frame_ids": self.frame_ids.tolist(),
            "topology_regime_ids": self.topology_regime_ids.tolist(),
            "connectivity_flicker_mask": self.connectivity_flicker_mask.tolist(),
            "structural_mask": self.structural_mask.tolist(),
            "source_topology_catalog_digest": self.source_topology_catalog_digest,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TopologyRegimeAssignment":
        if payload.get("schema") != TOPOLOGY_REGIME_ASSIGNMENT_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported topology-regime-assignment schema."
            )
        return cls(
            frame_indices=np.asarray(payload["frame_indices"], dtype=np.int64),
            frame_ids=np.asarray(payload["frame_ids"], dtype=np.int64),
            topology_regime_ids=np.asarray(
                payload["topology_regime_ids"], dtype=np.int32
            ),
            connectivity_flicker_mask=np.asarray(
                payload["connectivity_flicker_mask"], dtype=np.bool_
            ),
            structural_mask=np.asarray(payload["structural_mask"], dtype=np.bool_),
            source_topology_catalog_digest=(
                None
                if payload.get("source_topology_catalog_digest") is None
                else str(payload["source_topology_catalog_digest"])
            ),
            signature=str(payload.get("signature", "")),
        )


def prepare_topology_regime_assignment(
    collection: AtomisticFrameCollection,
    *,
    topology_catalog: TopologyCatalog | None = None,
    topology_regime_ids: Sequence[int] | np.ndarray | None = None,
    connectivity_flicker_mask: Sequence[bool] | np.ndarray | None = None,
    structural_mask: Sequence[bool] | np.ndarray | None = None,
    mark_transition_boundaries_as_flicker: bool = True,
) -> TopologyRegimeAssignment:
    """Build framewise topology regimes from a catalog or explicit arrays."""

    n_frames = collection.n_frames
    frames = np.arange(n_frames, dtype=np.int64)
    if topology_catalog is not None and topology_regime_ids is not None:
        raise SiteSampleInputError(
            "Supply topology_catalog or topology_regime_ids, not both."
        )
    digest = None
    if topology_catalog is not None:
        if topology_catalog.frame_semantics is not collection.frame_semantics:
            raise SiteSampleInputError(
                "Topology catalog frame semantics disagree with the collection."
            )
        selected = np.asarray(topology_catalog.frame_indices, dtype=np.int64)
        if np.any(selected < 0) or np.any(selected >= n_frames):
            raise SiteSampleInputError(
                "Topology catalog frame indices lie outside the collection."
            )
        if not np.array_equal(collection.frame_ids[selected], topology_catalog.frame_ids):
            raise SiteSampleInputError(
                "Topology catalog frame IDs disagree with the collection."
            )
        regimes = np.full(n_frames, -1, dtype=np.int32)
        regimes[selected] = np.asarray(topology_catalog.frame_topology_ids, dtype=np.int32)
        flicker = np.zeros(n_frames, dtype=np.bool_)
        if topology_catalog.segments is not None:
            for segment in topology_catalog.segments:
                if segment.status is TopologySegmentStatus.TRANSIENT:
                    positions = np.arange(
                        segment.result_position_start,
                        segment.result_position_stop,
                        dtype=np.int64,
                    )
                    flicker[selected[positions]] = True
        if mark_transition_boundaries_as_flicker:
            for transition in topology_catalog.transitions:
                flicker[transition.collection_frame_index_before] = True
                flicker[transition.collection_frame_index_after] = True
        digest = topology_catalog.digest
    else:
        regimes = (
            np.full(n_frames, -1, dtype=np.int32)
            if topology_regime_ids is None
            else np.asarray(topology_regime_ids, dtype=np.int32)
        )
        if regimes.shape != (n_frames,):
            raise SiteSampleInputError(
                "topology_regime_ids must align with collection frames."
            )
        flicker = (
            np.zeros(n_frames, dtype=np.bool_)
            if connectivity_flicker_mask is None
            else np.asarray(connectivity_flicker_mask, dtype=np.bool_)
        )
        if flicker.shape != (n_frames,):
            raise SiteSampleInputError(
                "connectivity_flicker_mask must align with collection frames."
            )
    if connectivity_flicker_mask is not None and topology_catalog is not None:
        extra = np.asarray(connectivity_flicker_mask, dtype=np.bool_)
        if extra.shape != (n_frames,):
            raise SiteSampleInputError(
                "connectivity_flicker_mask must align with collection frames."
            )
        flicker |= extra
    if structural_mask is None:
        structural = ~flicker
    else:
        structural = np.asarray(structural_mask, dtype=np.bool_)
        if structural.shape != (n_frames,):
            raise SiteSampleInputError(
                "structural_mask must align with collection frames."
            )
        structural &= ~flicker
    return TopologyRegimeAssignment(
        frame_indices=frames,
        frame_ids=collection.frame_ids,
        topology_regime_ids=regimes,
        connectivity_flicker_mask=flicker,
        structural_mask=structural,
        source_topology_catalog_digest=digest,
    )


@dataclass(frozen=True, slots=True)
class SamplingStateProvenance:
    equilibrium_status: EquilibriumStatus = EquilibriumStatus.UNKNOWN
    stationarity_status: StationarityStatus = StationarityStatus.UNKNOWN
    declaration_source: str = "unspecified"
    notes: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        equilibrium = EquilibriumStatus(self.equilibrium_status)
        stationarity = StationarityStatus(self.stationarity_status)
        source = str(self.declaration_source)
        if not source:
            raise SiteSampleInputError("declaration_source must be nonempty.")
        notes = tuple(str(item) for item in self.notes)
        payload = {
            "schema": SAMPLING_STATE_PROVENANCE_SCHEMA,
            "equilibrium_status": equilibrium.value,
            "stationarity_status": stationarity.value,
            "declaration_source": source,
            "notes": list(notes),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise SiteSampleInputError(
                "Sampling-state-provenance signature is inconsistent."
            )
        object.__setattr__(self, "equilibrium_status", equilibrium)
        object.__setattr__(self, "stationarity_status", stationarity)
        object.__setattr__(self, "declaration_source", source)
        object.__setattr__(self, "notes", notes)
        object.__setattr__(self, "signature", expected)

    @property
    def supports_equilibrium_pmf(self) -> bool:
        return (
            self.equilibrium_status is EquilibriumStatus.DECLARED_EQUILIBRIUM
            and self.stationarity_status
            in {
                StationarityStatus.ASSUMED_STATIONARY,
                StationarityStatus.TESTED_STATIONARY,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SAMPLING_STATE_PROVENANCE_SCHEMA,
            "equilibrium_status": self.equilibrium_status.value,
            "stationarity_status": self.stationarity_status.value,
            "declaration_source": self.declaration_source,
            "notes": list(self.notes),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SamplingStateProvenance":
        if payload.get("schema") != SAMPLING_STATE_PROVENANCE_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported sampling-state-provenance schema."
            )
        return cls(
            equilibrium_status=EquilibriumStatus(payload["equilibrium_status"]),
            stationarity_status=StationarityStatus(payload["stationarity_status"]),
            declaration_source=str(payload["declaration_source"]),
            notes=tuple(str(item) for item in payload.get("notes", ())),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class PMFTemperatureProvenance:
    status: PMFTemperatureStatus = PMFTemperatureStatus.UNKNOWN
    temperature_kelvin: float | None = None
    observed_range_kelvin: tuple[float, float] | None = None
    source: str = "unspecified"
    signature: str = ""

    def __post_init__(self) -> None:
        status = PMFTemperatureStatus(self.status)
        temperature = None if self.temperature_kelvin is None else float(self.temperature_kelvin)
        observed = self.observed_range_kelvin
        if temperature is not None and (not np.isfinite(temperature) or temperature <= 0.0):
            raise SiteSampleInputError("temperature_kelvin must be finite and positive.")
        if status is PMFTemperatureStatus.DECLARED_CONSTANT and temperature is None:
            raise SiteSampleInputError(
                "declared_constant PMF temperature requires temperature_kelvin."
            )
        if status is not PMFTemperatureStatus.DECLARED_CONSTANT and temperature is not None:
            raise SiteSampleInputError(
                "temperature_kelvin is reserved for declared_constant provenance."
            )
        normalized_range = None
        if observed is not None:
            if len(observed) != 2:
                raise SiteSampleInputError(
                    "observed_range_kelvin must contain lower and upper bounds."
                )
            lower, upper = (float(observed[0]), float(observed[1]))
            if not np.isfinite(lower + upper) or lower <= 0.0 or upper < lower:
                raise SiteSampleInputError("Invalid observed temperature range.")
            normalized_range = (lower, upper)
        source = str(self.source)
        if not source:
            raise SiteSampleInputError("PMF temperature source must be nonempty.")
        payload = {
            "schema": PMF_TEMPERATURE_PROVENANCE_SCHEMA,
            "status": status.value,
            "temperature_kelvin": temperature,
            "observed_range_kelvin": (
                None if normalized_range is None else list(normalized_range)
            ),
            "source": source,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise SiteSampleInputError(
                "PMF-temperature-provenance signature is inconsistent."
            )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "temperature_kelvin", temperature)
        object.__setattr__(self, "observed_range_kelvin", normalized_range)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "signature", expected)

    @property
    def supports_fixed_temperature_pmf(self) -> bool:
        return self.status is PMFTemperatureStatus.DECLARED_CONSTANT

    @classmethod
    def declared_constant(
        cls, temperature_kelvin: float, *, source: str
    ) -> "PMFTemperatureProvenance":
        return cls(
            status=PMFTemperatureStatus.DECLARED_CONSTANT,
            temperature_kelvin=temperature_kelvin,
            source=source,
        )

    @classmethod
    def from_collection(
        cls, collection: AtomisticFrameCollection, *, source: str = "collection.temperatures"
    ) -> "PMFTemperatureProvenance":
        if collection.temperatures is None:
            return cls(status=PMFTemperatureStatus.UNAVAILABLE, source=source)
        values = np.asarray(collection.temperatures, dtype=np.float64)
        return cls(
            status=PMFTemperatureStatus.FRAMEWISE_OBSERVED,
            observed_range_kelvin=(float(np.min(values)), float(np.max(values))),
            source=source,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PMF_TEMPERATURE_PROVENANCE_SCHEMA,
            "status": self.status.value,
            "temperature_kelvin": self.temperature_kelvin,
            "observed_range_kelvin": (
                None
                if self.observed_range_kelvin is None
                else list(self.observed_range_kelvin)
            ),
            "source": self.source,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PMFTemperatureProvenance":
        if payload.get("schema") != PMF_TEMPERATURE_PROVENANCE_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported PMF-temperature-provenance schema."
            )
        observed = payload.get("observed_range_kelvin")
        return cls(
            status=PMFTemperatureStatus(payload["status"]),
            temperature_kelvin=(
                None
                if payload.get("temperature_kelvin") is None
                else float(payload["temperature_kelvin"])
            ),
            observed_range_kelvin=(
                None
                if observed is None
                else (float(observed[0]), float(observed[1]))
            ),
            source=str(payload["source"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class SampleForceProvenance:
    source_provenance: ForceSourceProvenance
    geometric_status: GeometricForceTransformStatus
    pmf_status: PMFForceAdmissibilityStatus
    bias_force_evidence: EvidenceState
    registration_signature: str
    transformed_force_available: bool
    reasons: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.source_provenance, ForceSourceProvenance):
            raise SiteSampleInputError(
                "source_provenance must be ForceSourceProvenance."
            )
        geometric = GeometricForceTransformStatus(self.geometric_status)
        pmf = PMFForceAdmissibilityStatus(self.pmf_status)
        bias = EvidenceState(self.bias_force_evidence)
        if bias is not self.source_provenance.bias_or_constraint_force:
            raise SiteSampleInputError(
                "bias_force_evidence must match source force provenance."
            )
        if not isinstance(self.registration_signature, str) or len(self.registration_signature) != 64:
            raise SiteSampleInputError("registration_signature must be SHA-256.")
        reasons = tuple(str(item) for item in self.reasons)
        payload = {
            "schema": SAMPLE_FORCE_PROVENANCE_SCHEMA,
            "source_provenance": self.source_provenance.to_dict(),
            "geometric_status": geometric.value,
            "pmf_status": pmf.value,
            "bias_force_evidence": bias.value,
            "registration_signature": self.registration_signature,
            "transformed_force_available": bool(self.transformed_force_available),
            "reasons": list(reasons),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise SiteSampleInputError("Sample-force-provenance signature is inconsistent.")
        object.__setattr__(self, "geometric_status", geometric)
        object.__setattr__(self, "pmf_status", pmf)
        object.__setattr__(self, "bias_force_evidence", bias)
        object.__setattr__(self, "transformed_force_available", bool(self.transformed_force_available))
        object.__setattr__(self, "reasons", reasons)
        object.__setattr__(self, "signature", expected)

    @classmethod
    def from_registration(
        cls, registration: FrameRegistrationResult
    ) -> "SampleForceProvenance":
        contract = registration.force_admissibility
        return cls(
            source_provenance=contract.source_provenance,
            geometric_status=contract.geometric_status,
            pmf_status=contract.pmf_status,
            bias_force_evidence=contract.source_provenance.bias_or_constraint_force,
            registration_signature=registration.signature,
            transformed_force_available=registration.transformed_forces is not None,
            reasons=contract.reasons,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SAMPLE_FORCE_PROVENANCE_SCHEMA,
            "source_provenance": self.source_provenance.to_dict(),
            "geometric_status": self.geometric_status.value,
            "pmf_status": self.pmf_status.value,
            "bias_force_evidence": self.bias_force_evidence.value,
            "registration_signature": self.registration_signature,
            "transformed_force_available": self.transformed_force_available,
            "reasons": list(self.reasons),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SampleForceProvenance":
        if payload.get("schema") != SAMPLE_FORCE_PROVENANCE_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported sample-force-provenance schema."
            )
        source = payload.get("source_provenance")
        if not isinstance(source, Mapping):
            raise SampleCatalogSerializationError(
                "Missing source force provenance."
            )
        return cls(
            source_provenance=ForceSourceProvenance.from_mapping(source),
            geometric_status=GeometricForceTransformStatus(payload["geometric_status"]),
            pmf_status=PMFForceAdmissibilityStatus(payload["pmf_status"]),
            bias_force_evidence=EvidenceState(payload["bias_force_evidence"]),
            registration_signature=str(payload["registration_signature"]),
            transformed_force_available=bool(payload["transformed_force_available"]),
            reasons=tuple(str(item) for item in payload.get("reasons", ())),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class SampleEvidenceMasks:
    position_source_mask: BoolArray
    force_source_mask: BoolArray
    temporal_mask: BoolArray
    structural_mask: BoolArray
    connectivity_flicker_mask: BoolArray
    position_mask: BoolArray
    force_mask: BoolArray
    joint_mask: BoolArray
    pmf_force_mask: BoolArray
    signature: str = ""

    def __post_init__(self) -> None:
        source_position = _readonly_array(
            self.position_source_mask,
            dtype=np.bool_,
            ndim=1,
            name="position_source_mask",
        )
        shape = source_position.shape
        arrays: dict[str, np.ndarray] = {}
        for name in (
            "force_source_mask",
            "temporal_mask",
            "structural_mask",
            "connectivity_flicker_mask",
            "position_mask",
            "force_mask",
            "joint_mask",
            "pmf_force_mask",
        ):
            arrays[name] = _readonly_array(
                getattr(self, name),
                dtype=np.bool_,
                ndim=1,
                name=name,
                shape=shape,
            )
        if np.any(arrays["connectivity_flicker_mask"] & arrays["structural_mask"]):
            raise SiteSampleInputError(
                "Connectivity-flicker samples cannot be structural evidence."
            )
        expected_position = source_position & arrays["temporal_mask"] & arrays["structural_mask"]
        expected_force = arrays["force_source_mask"] & arrays["temporal_mask"] & arrays["structural_mask"]
        if not np.array_equal(arrays["position_mask"], expected_position):
            raise SiteSampleInputError(
                "position_mask must equal position_source & temporal & structural."
            )
        if not np.array_equal(arrays["force_mask"], expected_force):
            raise SiteSampleInputError(
                "force_mask must equal force_source & temporal & structural."
            )
        if not np.array_equal(
            arrays["joint_mask"], arrays["position_mask"] & arrays["force_mask"]
        ):
            raise SiteSampleInputError(
                "joint_mask must equal the exact position/force intersection."
            )
        if np.any(arrays["pmf_force_mask"] & ~arrays["joint_mask"]):
            raise SiteSampleInputError("pmf_force_mask must be a subset of joint_mask.")
        payload = {
            "schema": SAMPLE_EVIDENCE_MASKS_SCHEMA,
            "position_source_mask_digest": _array_digest(source_position),
            **{f"{name}_digest": _array_digest(array) for name, array in arrays.items()},
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise SiteSampleInputError("Sample-evidence-mask signature is inconsistent.")
        object.__setattr__(self, "position_source_mask", source_position)
        for name, array in arrays.items():
            object.__setattr__(self, name, array)
        object.__setattr__(self, "signature", expected)

    @property
    def n_samples(self) -> int:
        return int(self.position_mask.size)

    def mask_for(self, channel: EvidenceChannel) -> BoolArray:
        if channel == "position":
            return self.position_mask
        if channel == "force":
            return self.force_mask
        if channel == "joint":
            return self.joint_mask
        if channel == "pmf_force":
            return self.pmf_force_mask
        raise SiteSampleInputError(f"Unknown evidence channel {channel!r}.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SAMPLE_EVIDENCE_MASKS_SCHEMA,
            "position_source_mask": self.position_source_mask.tolist(),
            "force_source_mask": self.force_source_mask.tolist(),
            "temporal_mask": self.temporal_mask.tolist(),
            "structural_mask": self.structural_mask.tolist(),
            "connectivity_flicker_mask": self.connectivity_flicker_mask.tolist(),
            "position_mask": self.position_mask.tolist(),
            "force_mask": self.force_mask.tolist(),
            "joint_mask": self.joint_mask.tolist(),
            "pmf_force_mask": self.pmf_force_mask.tolist(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SampleEvidenceMasks":
        if payload.get("schema") != SAMPLE_EVIDENCE_MASKS_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported sample-evidence-mask schema."
            )
        return cls(
            **{
                name: np.asarray(payload[name], dtype=np.bool_)
                for name in (
                    "position_source_mask",
                    "force_source_mask",
                    "temporal_mask",
                    "structural_mask",
                    "connectivity_flicker_mask",
                    "position_mask",
                    "force_mask",
                    "joint_mask",
                    "pmf_force_mask",
                )
            },
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class FrameRegistrationGroupMember:
    member_index: int
    source_contract_signature: str
    registration_signature: str
    n_frames: int
    maximum_internal_cell_deviation: float

    def __post_init__(self) -> None:
        index = int(self.member_index)
        n_frames = int(self.n_frames)
        deviation = float(self.maximum_internal_cell_deviation)
        if index < 0 or n_frames < 1:
            raise RegistrationGroupError(
                "Registration-group member index and frame count are invalid."
            )
        for name in ("source_contract_signature", "registration_signature"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise RegistrationGroupError(f"{name} must be SHA-256.")
        if not np.isfinite(deviation) or deviation < 0.0:
            raise RegistrationGroupError(
                "maximum_internal_cell_deviation must be finite and nonnegative."
            )
        object.__setattr__(self, "member_index", index)
        object.__setattr__(self, "n_frames", n_frames)
        object.__setattr__(self, "maximum_internal_cell_deviation", deviation)

    def to_dict(self) -> dict[str, Any]:
        return {
            "member_index": self.member_index,
            "source_contract_signature": self.source_contract_signature,
            "registration_signature": self.registration_signature,
            "n_frames": self.n_frames,
            "maximum_internal_cell_deviation": self.maximum_internal_cell_deviation,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameRegistrationGroupMember":
        return cls(
            member_index=int(payload["member_index"]),
            source_contract_signature=str(payload["source_contract_signature"]),
            registration_signature=str(payload["registration_signature"]),
            n_frames=int(payload["n_frames"]),
            maximum_internal_cell_deviation=float(
                payload["maximum_internal_cell_deviation"]
            ),
        )


@dataclass(frozen=True, slots=True)
class FrameRegistrationGroup:
    shared_registered_cell: FloatArray
    periodic_axes: BoolArray
    analysis_metric_digest: str
    members: tuple[FrameRegistrationGroupMember, ...]
    relative_tolerance: float
    maximum_cross_member_cell_deviation: float
    signature: str = ""

    def __post_init__(self) -> None:
        cell = _readonly_array(
            self.shared_registered_cell,
            dtype=np.float64,
            ndim=2,
            name="shared_registered_cell",
            shape=(3, 3),
        )
        pbc = _readonly_array(
            self.periodic_axes,
            dtype=np.bool_,
            ndim=1,
            name="periodic_axes",
            shape=(3,),
        )
        if abs(float(np.linalg.det(cell))) <= np.finfo(float).tiny:
            raise RegistrationGroupError("Shared registered cell is singular.")
        members = tuple(self.members)
        if not members or tuple(item.member_index for item in members) != tuple(
            range(len(members))
        ):
            raise RegistrationGroupError(
                "Registration-group members must use dense ordered indices."
            )
        if len({item.registration_signature for item in members}) != len(members):
            raise RegistrationGroupError(
                "Registration-group member signatures must be unique."
            )
        metric_digest = str(self.analysis_metric_digest)
        if len(metric_digest) != 64:
            raise RegistrationGroupError("analysis_metric_digest must be SHA-256.")
        cross_deviation = float(self.maximum_cross_member_cell_deviation)
        if not np.isfinite(cross_deviation) or cross_deviation < 0.0:
            raise RegistrationGroupError(
                "maximum_cross_member_cell_deviation must be finite and nonnegative."
            )
        tolerance = float(self.relative_tolerance)
        if not np.isfinite(tolerance) or tolerance <= 0.0:
            raise RegistrationGroupError("relative_tolerance must be finite and positive.")
        payload = {
            "schema": FRAME_REGISTRATION_GROUP_SCHEMA,
            "shared_registered_cell_digest": _array_digest(cell),
            "periodic_axes": pbc.tolist(),
            "analysis_metric_digest": metric_digest,
            "members": [item.to_dict() for item in members],
            "relative_tolerance": tolerance,
            "maximum_cross_member_cell_deviation": cross_deviation,
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise RegistrationGroupError("Registration-group signature is inconsistent.")
        object.__setattr__(self, "shared_registered_cell", cell)
        object.__setattr__(self, "periodic_axes", pbc)
        object.__setattr__(self, "members", members)
        object.__setattr__(self, "analysis_metric_digest", metric_digest)
        object.__setattr__(
            self, "maximum_cross_member_cell_deviation", cross_deviation
        )
        object.__setattr__(self, "relative_tolerance", tolerance)
        object.__setattr__(self, "signature", expected)

    def member_index_for_registration(self, registration_signature: str) -> int:
        matches = [
            item.member_index
            for item in self.members
            if item.registration_signature == registration_signature
        ]
        if not matches:
            raise RegistrationGroupError(
                "Registration result is not a member of this group."
            )
        return matches[0]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FRAME_REGISTRATION_GROUP_SCHEMA,
            "shared_registered_cell": self.shared_registered_cell.tolist(),
            "periodic_axes": self.periodic_axes.tolist(),
            "analysis_metric_digest": self.analysis_metric_digest,
            "members": [item.to_dict() for item in self.members],
            "relative_tolerance": self.relative_tolerance,
            "maximum_cross_member_cell_deviation": self.maximum_cross_member_cell_deviation,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameRegistrationGroup":
        if payload.get("schema") != FRAME_REGISTRATION_GROUP_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported frame-registration-group schema."
            )
        return cls(
            shared_registered_cell=np.asarray(
                payload["shared_registered_cell"], dtype=np.float64
            ),
            periodic_axes=np.asarray(payload["periodic_axes"], dtype=np.bool_),
            analysis_metric_digest=str(payload["analysis_metric_digest"]),
            members=tuple(
                FrameRegistrationGroupMember.from_dict(item)
                for item in payload["members"]
            ),
            relative_tolerance=float(payload["relative_tolerance"]),
            maximum_cross_member_cell_deviation=float(
                payload["maximum_cross_member_cell_deviation"]
            ),
            signature=str(payload.get("signature", "")),
        )


def prepare_frame_registration_group(
    members: Sequence[tuple[AtomisticFrameCollection, FrameRegistrationResult]],
    *,
    relative_tolerance: float = 1.0e-10,
) -> FrameRegistrationGroup:
    """Certify multiple registrations on one fixed periodic domain."""

    if not members:
        raise RegistrationGroupError("At least one registration-group member is required.")
    tolerance = float(relative_tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise RegistrationGroupError("relative_tolerance must be finite and positive.")
    reference_collection, reference_registration = members[0]
    reference_cell = np.asarray(reference_registration.registered_cells[0], dtype=np.float64)
    reference_pbc = np.asarray(reference_collection.pbc, dtype=np.bool_)
    scale = max(float(np.linalg.norm(reference_cell)), np.finfo(float).tiny)
    metric_digest = reference_registration.analysis_metric.digest
    records: list[FrameRegistrationGroupMember] = []
    cross_max = 0.0
    for index, (collection, registration) in enumerate(members):
        if not isinstance(collection, AtomisticFrameCollection) or not isinstance(
            registration, FrameRegistrationResult
        ):
            raise TypeError(
                "Registration-group members must be (AtomisticFrameCollection, "
                "FrameRegistrationResult) pairs."
            )
        if registration.registered_cells.shape[0] != collection.n_frames:
            raise RegistrationGroupError(
                f"Member {index} registration frame count is inconsistent."
            )
        if not np.array_equal(collection.pbc, reference_pbc):
            raise RegistrationGroupError(
                f"Member {index} periodic axes differ from the shared domain."
            )
        if registration.analysis_metric.digest != metric_digest:
            raise RegistrationGroupError(
                f"Member {index} analysis geometry metric differs."
            )
        internal = float(
            np.max(
                np.linalg.norm(
                    np.asarray(registration.registered_cells) - registration.registered_cells[0],
                    axis=(1, 2),
                )
            )
            / scale
        )
        cross = float(np.linalg.norm(registration.registered_cells[0] - reference_cell) / scale)
        if internal > tolerance:
            raise RegistrationGroupError(
                f"Member {index} does not have a fixed registered cell: {internal:.6g}."
            )
        if cross > tolerance:
            raise RegistrationGroupError(
                f"Member {index} registered cell differs from the shared domain: {cross:.6g}."
            )
        cross_max = max(cross_max, cross)
        records.append(
            FrameRegistrationGroupMember(
                member_index=index,
                source_contract_signature=registration.source_contract_signature,
                registration_signature=registration.signature,
                n_frames=collection.n_frames,
                maximum_internal_cell_deviation=internal,
            )
        )
    return FrameRegistrationGroup(
        shared_registered_cell=reference_cell,
        periodic_axes=reference_pbc,
        analysis_metric_digest=metric_digest,
        members=tuple(records),
        relative_tolerance=tolerance,
        maximum_cross_member_cell_deviation=cross_max,
    )


@dataclass(frozen=True, slots=True)
class SpeciesSampleEvidenceView:
    catalog_signature: str
    channel: EvidenceChannel
    sample_indices: IntArray
    frame_indices: IntArray
    frame_ids: IntArray
    atom_indices: IntArray
    positions: FloatArray
    forces: FloatArray | None
    represented_time_weights: FloatArray
    topology_regime_ids: Int32Array

    def __post_init__(self) -> None:
        indices = _readonly_array(
            self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices"
        )
        n = indices.size
        for name, dtype in (
            ("frame_indices", np.int64),
            ("frame_ids", np.int64),
            ("atom_indices", np.int64),
            ("topology_regime_ids", np.int32),
        ):
            object.__setattr__(
                self,
                name,
                _readonly_array(
                    getattr(self, name),
                    dtype=dtype,
                    ndim=1,
                    name=name,
                    shape=(n,),
                ),
            )
        positions = _readonly_array(
            self.positions,
            dtype=np.float64,
            ndim=2,
            name="positions",
            shape=(n, 3),
        )
        forces = None
        if self.forces is not None:
            forces = _readonly_array(
                self.forces,
                dtype=np.float64,
                ndim=2,
                name="forces",
                shape=(n, 3),
            )
        weights = _readonly_array(
            self.represented_time_weights,
            dtype=np.float64,
            ndim=1,
            name="represented_time_weights",
            shape=(n,),
        )
        object.__setattr__(self, "sample_indices", indices)
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "forces", forces)
        object.__setattr__(self, "represented_time_weights", weights)

    @property
    def total_ion_time(self) -> float:
        return float(np.sum(self.represented_time_weights))

    @property
    def normalized_weights(self) -> FloatArray:
        total = self.total_ion_time
        if total <= 0.0:
            raise SiteSampleInputError(
                f"Evidence channel {self.channel!r} has zero represented time."
            )
        result = np.asarray(self.represented_time_weights / total, dtype=np.float64)
        result.setflags(write=False)
        return result


class StructuralAnnotationResolver(Protocol):
    def __call__(
        self,
        catalog: "FrameworkAlignedIonSampleCatalog",
        sample_indices: IntArray,
    ) -> Mapping[str, Any]: ...


class LazyStructuralAnnotationView:
    """Resolve structural descriptors only for an explicitly requested subset."""

    __slots__ = ("_catalog", "_resolver", "_cache")

    def __init__(
        self,
        catalog: "FrameworkAlignedIonSampleCatalog",
        resolver: StructuralAnnotationResolver,
    ) -> None:
        if not callable(resolver):
            raise TypeError("resolver must be callable.")
        self._catalog = catalog
        self._resolver = resolver
        self._cache: dict[tuple[int, ...], Mapping[str, Any]] = {}

    @property
    def catalog_signature(self) -> str:
        return self._catalog.signature

    def resolve(
        self,
        *,
        channel: EvidenceChannel = "position",
        sample_indices: Sequence[int] | np.ndarray | None = None,
    ) -> Mapping[str, Any]:
        if sample_indices is None:
            indices = self._catalog.sample_indices_for(channel)
        else:
            indices = np.asarray(sample_indices, dtype=np.int64)
            if indices.ndim != 1 or np.any(indices < 0) or np.any(
                indices >= self._catalog.n_samples
            ):
                raise SiteSampleInputError(
                    "Structural annotation sample_indices are invalid."
                )
        key = tuple(int(item) for item in indices)
        if key in self._cache:
            return self._cache[key]
        readonly = np.array(indices, dtype=np.int64, copy=True)
        readonly.setflags(write=False)
        raw = self._resolver(self._catalog, readonly)
        if not isinstance(raw, Mapping):
            raise SiteSampleInputError(
                "Structural annotation resolver must return a mapping."
            )
        frozen: dict[str, Any] = {}
        for name, value in raw.items():
            array = np.asarray(value)
            if array.ndim == 0 or array.shape[0] != readonly.size:
                raise SiteSampleInputError(
                    f"Structural annotation {name!r} must have leading length "
                    f"{readonly.size}."
                )
            copy = np.array(array, copy=True)
            copy.setflags(write=False)
            frozen[str(name)] = copy
        result = MappingProxyType(frozen)
        self._cache[key] = result
        return result


@dataclass(frozen=True, slots=True)
class FrameworkAlignedIonSampleCatalog:
    species_atomic_number: int
    species_label: str
    selected_atom_indices: tuple[int, ...]
    frame_indices: IntArray
    frame_ids: IntArray
    atom_indices: IntArray
    registered_positions: FloatArray
    registered_wrapped_fractional: FloatArray
    registered_image_shifts: IntArray
    transformed_forces: FloatArray | None
    represented_time_weights: FloatArray
    topology_regime_ids: Int32Array
    evidence_masks: SampleEvidenceMasks
    temporal_weighting: TrajectorySegmentWeighting
    topology_assignment: TopologyRegimeAssignment
    force_provenance: SampleForceProvenance
    sampling_state: SamplingStateProvenance
    pmf_temperature: PMFTemperatureProvenance
    source_contract_signature: str
    registration_signature: str
    registration_policy_signature: str
    registration_group_signature: str | None = None
    registration_group_member_index: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        atomic_number = int(self.species_atomic_number)
        if atomic_number <= 0:
            raise SiteSampleInputError("species_atomic_number must be positive.")
        label = str(self.species_label)
        if not label:
            raise SiteSampleInputError("species_label must be nonempty.")
        selected = tuple(int(item) for item in self.selected_atom_indices)
        if not selected or len(set(selected)) != len(selected) or min(selected) < 0:
            raise SiteSampleInputError(
                "selected_atom_indices must be unique, nonnegative, and nonempty."
            )
        frames = _readonly_array(
            self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices"
        )
        n = frames.size
        frame_ids = _readonly_array(
            self.frame_ids,
            dtype=np.int64,
            ndim=1,
            name="frame_ids",
            shape=(n,),
        )
        atoms = _readonly_array(
            self.atom_indices,
            dtype=np.int64,
            ndim=1,
            name="atom_indices",
            shape=(n,),
        )
        positions = _readonly_array(
            self.registered_positions,
            dtype=np.float64,
            ndim=2,
            name="registered_positions",
            shape=(n, 3),
        )
        wrapped = _readonly_array(
            self.registered_wrapped_fractional,
            dtype=np.float64,
            ndim=2,
            name="registered_wrapped_fractional",
            shape=(n, 3),
        )
        shifts = _readonly_array(
            self.registered_image_shifts,
            dtype=np.int64,
            ndim=2,
            name="registered_image_shifts",
            shape=(n, 3),
        )
        forces = None
        if self.transformed_forces is not None:
            forces = _readonly_array(
                self.transformed_forces,
                dtype=np.float64,
                ndim=2,
                name="transformed_forces",
                shape=(n, 3),
            )
        weights = _readonly_array(
            self.represented_time_weights,
            dtype=np.float64,
            ndim=1,
            name="represented_time_weights",
            shape=(n,),
        )
        regimes = _readonly_array(
            self.topology_regime_ids,
            dtype=np.int32,
            ndim=1,
            name="topology_regime_ids",
            shape=(n,),
        )
        if self.evidence_masks.n_samples != n:
            raise SiteSampleInputError(
                "Evidence masks do not align with compact samples."
            )
        if n != self.temporal_weighting.frame_indices.size * len(selected):
            raise SiteSampleInputError(
                "Compact sample count must equal frames times selected atoms."
            )
        if not np.array_equal(
            np.unique(atoms), np.asarray(sorted(selected), dtype=np.int64)
        ):
            raise SiteSampleInputError(
                "Compact atom indices disagree with selected_atom_indices."
            )
        for name in (
            "source_contract_signature",
            "registration_signature",
            "registration_policy_signature",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise SiteSampleInputError(f"{name} must be SHA-256.")
        if self.force_provenance.registration_signature != self.registration_signature:
            raise SiteSampleInputError(
                "Force provenance and catalog registration signatures disagree."
            )
        if self.registration_group_signature is None:
            if self.registration_group_member_index is not None:
                raise SiteSampleInputError(
                    "registration_group_member_index requires a group signature."
                )
        else:
            if len(self.registration_group_signature) != 64:
                raise SiteSampleInputError(
                    "registration_group_signature must be SHA-256."
                )
            if self.registration_group_member_index is None or self.registration_group_member_index < 0:
                raise SiteSampleInputError(
                    "A grouped catalog requires a nonnegative member index."
                )
        metadata = _freeze_value(self.metadata)
        if not isinstance(metadata, Mapping):
            raise SiteSampleInputError("metadata must be a mapping.")
        payload = {
            "schema": FRAMEWORK_ALIGNED_ION_SAMPLE_CATALOG_SCHEMA,
            "digest_algorithm": SITE_SAMPLE_DIGEST_ALGORITHM,
            "species_atomic_number": atomic_number,
            "species_label": label,
            "selected_atom_indices": list(selected),
            "frame_indices_digest": _array_digest(frames),
            "frame_ids_digest": _array_digest(frame_ids),
            "atom_indices_digest": _array_digest(atoms),
            "registered_positions_digest": _array_digest(positions),
            "registered_wrapped_fractional_digest": _array_digest(wrapped),
            "registered_image_shifts_digest": _array_digest(shifts),
            "transformed_forces_digest": None if forces is None else _array_digest(forces),
            "represented_time_weights_digest": _array_digest(weights),
            "topology_regime_ids_digest": _array_digest(regimes),
            "evidence_masks_signature": self.evidence_masks.signature,
            "temporal_weighting_signature": self.temporal_weighting.signature,
            "topology_assignment_signature": self.topology_assignment.signature,
            "force_provenance_signature": self.force_provenance.signature,
            "sampling_state_signature": self.sampling_state.signature,
            "pmf_temperature_signature": self.pmf_temperature.signature,
            "source_contract_signature": self.source_contract_signature,
            "registration_signature": self.registration_signature,
            "registration_policy_signature": self.registration_policy_signature,
            "registration_group_signature": self.registration_group_signature,
            "registration_group_member_index": self.registration_group_member_index,
            "metadata": _json_value(metadata),
        }
        expected = _digest_payload(payload)
        if self.signature and self.signature != expected:
            raise SiteSampleInputError("Sample-catalog signature is inconsistent.")
        object.__setattr__(self, "species_atomic_number", atomic_number)
        object.__setattr__(self, "species_label", label)
        object.__setattr__(self, "selected_atom_indices", selected)
        object.__setattr__(self, "frame_indices", frames)
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "atom_indices", atoms)
        object.__setattr__(self, "registered_positions", positions)
        object.__setattr__(self, "registered_wrapped_fractional", wrapped)
        object.__setattr__(self, "registered_image_shifts", shifts)
        object.__setattr__(self, "transformed_forces", forces)
        object.__setattr__(self, "represented_time_weights", weights)
        object.__setattr__(self, "topology_regime_ids", regimes)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    @property
    def n_samples(self) -> int:
        return int(self.frame_indices.size)

    @property
    def n_selected_atoms(self) -> int:
        return len(self.selected_atom_indices)

    def sample_indices_for(self, channel: EvidenceChannel) -> IntArray:
        indices = np.flatnonzero(self.evidence_masks.mask_for(channel)).astype(np.int64)
        indices.setflags(write=False)
        return indices

    def evidence_view(self, channel: EvidenceChannel) -> SpeciesSampleEvidenceView:
        indices = self.sample_indices_for(channel)
        forces = None
        if channel in {"force", "joint", "pmf_force"}:
            if self.transformed_forces is None:
                raise SiteSampleInputError(
                    f"Evidence channel {channel!r} requires transformed forces."
                )
            forces = self.transformed_forces[indices]
        return SpeciesSampleEvidenceView(
            catalog_signature=self.signature,
            channel=channel,
            sample_indices=indices,
            frame_indices=self.frame_indices[indices],
            frame_ids=self.frame_ids[indices],
            atom_indices=self.atom_indices[indices],
            positions=self.registered_positions[indices],
            forces=forces,
            represented_time_weights=self.represented_time_weights[indices],
            topology_regime_ids=self.topology_regime_ids[indices],
        )

    def structural_annotations(
        self, resolver: StructuralAnnotationResolver
    ) -> LazyStructuralAnnotationView:
        return LazyStructuralAnnotationView(self, resolver)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FRAMEWORK_ALIGNED_ION_SAMPLE_CATALOG_SCHEMA,
            "digest_algorithm": SITE_SAMPLE_DIGEST_ALGORITHM,
            "species_atomic_number": self.species_atomic_number,
            "species_label": self.species_label,
            "selected_atom_indices": list(self.selected_atom_indices),
            "frame_indices": self.frame_indices.tolist(),
            "frame_ids": self.frame_ids.tolist(),
            "atom_indices": self.atom_indices.tolist(),
            "registered_positions": self.registered_positions.tolist(),
            "registered_wrapped_fractional": self.registered_wrapped_fractional.tolist(),
            "registered_image_shifts": self.registered_image_shifts.tolist(),
            "transformed_forces": (
                None if self.transformed_forces is None else self.transformed_forces.tolist()
            ),
            "represented_time_weights": self.represented_time_weights.tolist(),
            "topology_regime_ids": self.topology_regime_ids.tolist(),
            "evidence_masks": self.evidence_masks.to_dict(),
            "temporal_weighting": self.temporal_weighting.to_dict(),
            "topology_assignment": self.topology_assignment.to_dict(),
            "force_provenance": self.force_provenance.to_dict(),
            "sampling_state": self.sampling_state.to_dict(),
            "pmf_temperature": self.pmf_temperature.to_dict(),
            "source_contract_signature": self.source_contract_signature,
            "registration_signature": self.registration_signature,
            "registration_policy_signature": self.registration_policy_signature,
            "registration_group_signature": self.registration_group_signature,
            "registration_group_member_index": self.registration_group_member_index,
            "metadata": _json_value(self.metadata),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkAlignedIonSampleCatalog":
        if payload.get("schema") != FRAMEWORK_ALIGNED_ION_SAMPLE_CATALOG_SCHEMA:
            raise SampleCatalogSerializationError(
                "Unsupported framework-aligned-ion-sample-catalog schema."
            )
        if payload.get("digest_algorithm") != SITE_SAMPLE_DIGEST_ALGORITHM:
            raise SampleCatalogSerializationError(
                "Unsupported sample-catalog digest algorithm."
            )
        force_values = payload.get("transformed_forces")
        return cls(
            species_atomic_number=int(payload["species_atomic_number"]),
            species_label=str(payload["species_label"]),
            selected_atom_indices=tuple(
                int(item) for item in payload["selected_atom_indices"]
            ),
            frame_indices=np.asarray(payload["frame_indices"], dtype=np.int64),
            frame_ids=np.asarray(payload["frame_ids"], dtype=np.int64),
            atom_indices=np.asarray(payload["atom_indices"], dtype=np.int64),
            registered_positions=np.asarray(
                payload["registered_positions"], dtype=np.float64
            ),
            registered_wrapped_fractional=np.asarray(
                payload["registered_wrapped_fractional"], dtype=np.float64
            ),
            registered_image_shifts=np.asarray(
                payload["registered_image_shifts"], dtype=np.int64
            ),
            transformed_forces=(
                None
                if force_values is None
                else np.asarray(force_values, dtype=np.float64)
            ),
            represented_time_weights=np.asarray(
                payload["represented_time_weights"], dtype=np.float64
            ),
            topology_regime_ids=np.asarray(
                payload["topology_regime_ids"], dtype=np.int32
            ),
            evidence_masks=SampleEvidenceMasks.from_dict(payload["evidence_masks"]),
            temporal_weighting=TrajectorySegmentWeighting.from_dict(
                payload["temporal_weighting"]
            ),
            topology_assignment=TopologyRegimeAssignment.from_dict(
                payload["topology_assignment"]
            ),
            force_provenance=SampleForceProvenance.from_dict(
                payload["force_provenance"]
            ),
            sampling_state=SamplingStateProvenance.from_dict(
                payload["sampling_state"]
            ),
            pmf_temperature=PMFTemperatureProvenance.from_dict(
                payload["pmf_temperature"]
            ),
            source_contract_signature=str(payload["source_contract_signature"]),
            registration_signature=str(payload["registration_signature"]),
            registration_policy_signature=str(payload["registration_policy_signature"]),
            registration_group_signature=(
                None
                if payload.get("registration_group_signature") is None
                else str(payload["registration_group_signature"])
            ),
            registration_group_member_index=(
                None
                if payload.get("registration_group_member_index") is None
                else int(payload["registration_group_member_index"])
            ),
            metadata=payload.get("metadata", {}),
            signature=str(payload.get("signature", "")),
        )


def _selected_mask(
    value: Sequence[bool] | np.ndarray | None,
    *,
    n_frames: int,
    n_atoms: int,
    selected: np.ndarray,
    default: bool,
    name: str,
) -> np.ndarray:
    if value is None:
        return np.full((n_frames, selected.size), default, dtype=np.bool_)
    array = np.asarray(value, dtype=np.bool_)
    if array.shape == (n_frames, n_atoms):
        return np.asarray(array[:, selected], dtype=np.bool_)
    if array.shape == (n_frames, selected.size):
        return np.asarray(array, dtype=np.bool_)
    raise SiteSampleInputError(
        f"{name} must have shape {(n_frames, n_atoms)} or "
        f"{(n_frames, selected.size)}; received {array.shape}."
    )


def _validate_registration_binding(
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
) -> None:
    expected_shape = (collection.n_frames, collection.n_atoms, 3)
    if registration.registered_unwrapped_cartesian.shape != expected_shape:
        raise SiteSampleInputError(
            "Registration coordinate shape disagrees with the collection."
        )
    source = collection.get_positions()
    transformed = np.einsum(
        "tni,tij->tnj", source, registration.affine_matrices, optimize=True
    ) + registration.affine_translations[:, None, :]
    error = float(
        np.max(
            np.linalg.norm(
                transformed - registration.registered_unwrapped_cartesian, axis=-1
            )
        )
    )
    tolerance = max(
        10.0 * float(registration.policy.round_trip_tolerance),
        32.0 * np.finfo(float).eps * max(float(np.max(np.abs(transformed))), 1.0),
    )
    if error > tolerance:
        raise SiteSampleInputError(
            "Registration result is not geometrically bound to this collection: "
            f"maximum error {error:.6g}."
        )


def prepare_framework_aligned_ion_sample_catalog(
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    *,
    species_atomic_number: int | None = None,
    atom_indices: Sequence[int] | np.ndarray | None = None,
    species_label: str | None = None,
    temporal_weighting: TrajectorySegmentWeighting | None = None,
    topology_assignment: TopologyRegimeAssignment | None = None,
    position_source_mask: Sequence[bool] | np.ndarray | None = None,
    force_source_mask: Sequence[bool] | np.ndarray | None = None,
    sampling_state: SamplingStateProvenance | None = None,
    pmf_temperature: PMFTemperatureProvenance | None = None,
    registration_group: FrameRegistrationGroup | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> FrameworkAlignedIonSampleCatalog:
    """Construct one compact registered species sample catalog."""

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be AtomisticFrameCollection.")
    if not isinstance(registration, FrameRegistrationResult):
        raise TypeError("registration must be FrameRegistrationResult.")
    _validate_registration_binding(collection, registration)
    if atom_indices is None:
        if species_atomic_number is None:
            raise SiteSampleInputError(
                "Supply species_atomic_number or explicit atom_indices."
            )
        selected = np.flatnonzero(
            collection.atomic_numbers == int(species_atomic_number)
        ).astype(np.int64)
    else:
        selected = np.asarray(atom_indices, dtype=np.int64)
        if selected.ndim != 1 or selected.size == 0:
            raise SiteSampleInputError("atom_indices must be a nonempty vector.")
        if len(set(int(item) for item in selected)) != selected.size:
            raise SiteSampleInputError("atom_indices must be unique.")
        if np.any(selected < 0) or np.any(selected >= collection.n_atoms):
            raise SiteSampleInputError("atom_indices lie outside the collection.")
    if selected.size == 0:
        raise SiteSampleInputError("No atoms match the requested species.")
    selected_numbers = np.unique(collection.atomic_numbers[selected])
    if selected_numbers.size != 1:
        raise SiteSampleInputError(
            "A species sample catalog may contain only one atomic number."
        )
    atomic_number = int(selected_numbers[0])
    if species_atomic_number is not None and int(species_atomic_number) != atomic_number:
        raise SiteSampleInputError(
            "species_atomic_number disagrees with selected atom indices."
        )
    label = str(species_label) if species_label is not None else f"Z{atomic_number}"

    temporal = temporal_weighting or prepare_trajectory_segment_weighting(
        collection, registration=registration
    )
    if not np.array_equal(temporal.frame_ids, collection.frame_ids):
        raise SiteSampleInputError(
            "Temporal weighting is not bound to the source collection."
        )
    topology = topology_assignment or prepare_topology_regime_assignment(collection)
    if not np.array_equal(topology.frame_ids, collection.frame_ids):
        raise SiteSampleInputError(
            "Topology assignment is not bound to the source collection."
        )

    n_frames = collection.n_frames
    position_source = _selected_mask(
        position_source_mask,
        n_frames=n_frames,
        n_atoms=collection.n_atoms,
        selected=selected,
        default=True,
        name="position_source_mask",
    )
    force_available = registration.transformed_forces is not None
    force_source = _selected_mask(
        force_source_mask,
        n_frames=n_frames,
        n_atoms=collection.n_atoms,
        selected=selected,
        default=force_available,
        name="force_source_mask",
    )
    if not force_available and np.any(force_source):
        raise SiteSampleInputError(
            "force_source_mask selects samples but transformed forces are unavailable."
        )

    frame_indices = np.repeat(np.arange(n_frames, dtype=np.int64), selected.size)
    frame_ids = np.repeat(collection.frame_ids, selected.size)
    compact_atoms = np.tile(selected, n_frames)
    positions = registration.registered_unwrapped_cartesian[:, selected, :].reshape(-1, 3)
    wrapped = registration.registered_wrapped_fractional[:, selected, :].reshape(-1, 3)
    shifts = registration.registered_image_shifts[:, selected, :].reshape(-1, 3)
    forces = None
    if registration.transformed_forces is not None:
        forces = registration.transformed_forces[:, selected, :].reshape(-1, 3)
    weights = np.repeat(temporal.represented_time_weights, selected.size)
    regimes = np.repeat(topology.topology_regime_ids, selected.size)
    temporal_mask = np.repeat(temporal.temporal_mask, selected.size)
    structural_mask = np.repeat(topology.structural_mask, selected.size)
    flicker_mask = np.repeat(topology.connectivity_flicker_mask, selected.size)
    position_source_flat = position_source.reshape(-1)
    force_source_flat = force_source.reshape(-1)
    position_mask = position_source_flat & temporal_mask & structural_mask
    force_mask = force_source_flat & temporal_mask & structural_mask
    joint_mask = position_mask & force_mask

    state = sampling_state or SamplingStateProvenance()
    temperature = pmf_temperature or PMFTemperatureProvenance()
    force_provenance = SampleForceProvenance.from_registration(registration)
    pmf_global = (
        registration.force_admissibility.pmf_force_admissible
        and state.supports_equilibrium_pmf
        and temperature.supports_fixed_temperature_pmf
    )
    pmf_mask = joint_mask & pmf_global
    masks = SampleEvidenceMasks(
        position_source_mask=position_source_flat,
        force_source_mask=force_source_flat,
        temporal_mask=temporal_mask,
        structural_mask=structural_mask,
        connectivity_flicker_mask=flicker_mask,
        position_mask=position_mask,
        force_mask=force_mask,
        joint_mask=joint_mask,
        pmf_force_mask=pmf_mask,
    )

    group_signature = None
    group_member_index = None
    if registration_group is not None:
        group_member_index = registration_group.member_index_for_registration(
            registration.signature
        )
        group_signature = registration_group.signature

    return FrameworkAlignedIonSampleCatalog(
        species_atomic_number=atomic_number,
        species_label=label,
        selected_atom_indices=tuple(int(item) for item in selected),
        frame_indices=frame_indices,
        frame_ids=frame_ids,
        atom_indices=compact_atoms,
        registered_positions=positions,
        registered_wrapped_fractional=wrapped,
        registered_image_shifts=shifts,
        transformed_forces=forces,
        represented_time_weights=weights,
        topology_regime_ids=regimes,
        evidence_masks=masks,
        temporal_weighting=temporal,
        topology_assignment=topology,
        force_provenance=force_provenance,
        sampling_state=state,
        pmf_temperature=temperature,
        source_contract_signature=registration.source_contract_signature,
        registration_signature=registration.signature,
        registration_policy_signature=registration.policy.signature,
        registration_group_signature=group_signature,
        registration_group_member_index=group_member_index,
        metadata={
            "stage": SITE_SAMPLE_STAGE,
            "compact_layout": "frame_major_species_atoms",
            "position_coordinate_frame": "registered_cartesian",
            "force_coordinate_frame": "registered_covector",
            "density_force_joint_subset_exact": True,
            "structural_annotations_eagerly_materialized": False,
            "weight_units": temporal.weight_units,
            **({} if metadata is None else dict(metadata)),
            **(
                {
                    "source_identity_signature": collection.metadata[
                        "source_trajectory_bundle_signature"
                    ]
                }
                if isinstance(
                    collection.metadata.get("source_trajectory_bundle_signature"),
                    str,
                )
                else {}
            ),
        },
    )


__all__ = [
    "FRAMEWORK_ALIGNED_ION_SAMPLE_CATALOG_SCHEMA",
    "FRAME_REGISTRATION_GROUP_SCHEMA",
    "PMF_TEMPERATURE_PROVENANCE_SCHEMA",
    "SAMPLE_EVIDENCE_MASKS_SCHEMA",
    "SAMPLE_FORCE_PROVENANCE_SCHEMA",
    "SAMPLING_STATE_PROVENANCE_SCHEMA",
    "SITE_SAMPLE_DIGEST_ALGORITHM",
    "SITE_SAMPLE_STAGE",
    "TOPOLOGY_REGIME_ASSIGNMENT_SCHEMA",
    "TRAJECTORY_SEGMENT_WEIGHTING_SCHEMA",
    "EquilibriumStatus",
    "FrameRegistrationGroup",
    "FrameRegistrationGroupMember",
    "FrameworkAlignedIonSampleCatalog",
    "LazyStructuralAnnotationView",
    "PMFTemperatureProvenance",
    "PMFTemperatureStatus",
    "RegistrationGroupError",
    "SampleCatalogSerializationError",
    "SampleEvidenceMasks",
    "SampleForceProvenance",
    "SamplingStateProvenance",
    "SegmentKind",
    "SiteSampleError",
    "SiteSampleInputError",
    "SpeciesSampleEvidenceView",
    "StationarityStatus",
    "StructuralAnnotationResolver",
    "TemporalWeightingError",
    "TopologyRegimeAssignment",
    "TrajectorySegmentWeighting",
    "prepare_frame_registration_group",
    "prepare_framework_aligned_ion_sample_catalog",
    "prepare_topology_regime_assignment",
    "prepare_trajectory_segment_weighting",
]
