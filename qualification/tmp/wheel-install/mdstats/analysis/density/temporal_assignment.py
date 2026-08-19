"""Stage-11E4 provisional assignment and temporal-persistence diagnostics.

The stage projects source-bound Stage-11E0b position samples onto the supported
periodic cell complex produced by Stage 11E2.  Raw core, basin, transition,
background, unknown, and unresolved memberships remain immutable.  A
preliminary core-entry/basin-retention state machine then reports residence,
excursion, recrossing, stride, censoring, and local decorrelation diagnostics.

Core-set metastability and autocorrelation initial-sequence estimators are
external background methods.  The exact source binding, no-nearest-centre-fill
rule, unsupported-gap policy, preliminary passage taxonomy, and orthogonal
support/pattern statuses are mdstats-specific constructions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import Enum, IntEnum
import hashlib
import json
import math
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from ..site_samples import FrameworkAlignedIonSampleCatalog
from .attractors import (
    AttractorGeometry,
    CellClassification,
    DensityAttractorCatalog,
)
from .force_refinement import ForceRefinementCatalog
from .species import PeriodicSpeciesDensityEstimate

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
Int32Array = NDArray[np.int32]
UInt8Array = NDArray[np.uint8]
BoolArray = NDArray[np.bool_]

TEMPORAL_ASSIGNMENT_STAGE = "11E4"
TEMPORAL_ASSIGNMENT_OPTIONS_SCHEMA = "mdstats.temporal-assignment-options.v1"
TEMPORAL_ASSIGNMENT_RESOURCES_SCHEMA = "mdstats.temporal-assignment-resources.v1"
PROVISIONAL_MEMBERSHIP_SCHEMA = "mdstats.provisional-membership.v1"
CORE_VISIT_INTERVAL_SCHEMA = "mdstats.core-visit-interval.v1"
PRELIMINARY_RESIDENCE_SCHEMA = "mdstats.preliminary-residence.v1"
PRELIMINARY_PASSAGE_SCHEMA = "mdstats.preliminary-passage.v1"
LOCAL_DECORRELATION_SCHEMA = "mdstats.local-decorrelation.v1"
ATTRACTOR_TEMPORAL_DIAGNOSTIC_SCHEMA = "mdstats.attractor-temporal-diagnostic.v1"
STRIDE_SENSITIVITY_SCHEMA = "mdstats.stride-sensitivity.v1"
TEMPORAL_ASSIGNMENT_CATALOG_SCHEMA = "mdstats.temporal-assignment-catalog.v1"


class TemporalAssignmentError(ValueError):
    """Base Stage-11E4 error."""


class TemporalAssignmentInputError(TemporalAssignmentError):
    """Raised when Stage-11E4 inputs violate source or shape contracts."""


class TemporalAssignmentResourceError(TemporalAssignmentError):
    """Raised transactionally before declared work limits are exceeded."""


class TemporalAssignmentSerializationError(TemporalAssignmentError):
    """Raised when serialized Stage-11E4 data are malformed or tampered with."""


class RawMembershipClass(IntEnum):
    EVIDENCE_EXCLUDED = 0
    CORE = 1
    BASIN = 2
    TRANSITION_REGION = 3
    SUPPORTED_BACKGROUND = 4
    UNSUPPORTED_UNKNOWN = 5
    NUMERICALLY_UNRESOLVED = 6
    CORE_OVERLAP = 7


class PassageOutcome(str, Enum):
    JUMP = "jump"
    RETURN_EXCURSION = "return_excursion"
    UNRESOLVED_GAP = "unresolved_gap"
    RIGHT_CENSORED_EXIT = "right_censored_exit"


class DecorrelationStatus(str, Enum):
    RESOLVED = "resolved"
    FRAME_ONLY_IRREGULAR_STRIDE = "frame_only_irregular_stride"
    INSUFFICIENT_SAMPLES = "insufficient_samples"
    ZERO_VARIANCE = "zero_variance"
    NO_RESIDENCE = "no_residence"


class TemporalSupportStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    INSUFFICIENT = "insufficient"
    PERSISTENT = "persistent"
    NONPERSISTENT = "nonpersistent"
    STRIDE_SENSITIVE = "stride_sensitive"


class TemporalEvidencePattern(str, Enum):
    ENSEMBLE_UNAVAILABLE = "ensemble_unavailable"
    NO_CORE_ENTRY = "no_core_entry"
    SINGLE_STATE = "single_state"
    ONE_JUMP = "one_jump"
    REPEATED_HOPPING = "repeated_hopping"
    SHORT_EXCURSION_ONLY = "short_excursion_only"
    EXCURSIONS_ONLY = "excursions_only"
    MIXED_HOPPING_AND_EXCURSIONS = "mixed_hopping_and_excursions"
    UNRESOLVED_GAPS_ONLY = "unresolved_gaps_only"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _array_digest(value: np.ndarray) -> str:
    arr = np.ascontiguousarray(value)
    h = hashlib.sha256()
    h.update(arr.dtype.str.encode("ascii"))
    h.update(str(arr.shape).encode("ascii"))
    h.update(arr.tobytes(order="C"))
    return h.hexdigest()


def _sha(value: Any, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise TemporalAssignmentInputError(f"{name} must be a SHA-256 digest.")
    return value


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str, shape: tuple[int, ...] | None = None) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise TemporalAssignmentInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise TemporalAssignmentInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise TemporalAssignmentInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise TemporalAssignmentInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _positive(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise TemporalAssignmentInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise TemporalAssignmentInputError(f"{name} must be finite and nonnegative.")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise TemporalAssignmentInputError(f"{name} must be a positive integer.")
    return int(value)


@dataclass(frozen=True, slots=True)
class TemporalAssignmentOptions:
    minimum_decorrelation_samples: int = 12
    maximum_autocorrelation_lag: int = 128
    maximum_relative_stride_deviation: float = 0.05
    minimum_persistence_tau_multiples: float = 3.0
    short_excursion_tau_multiple: float = 1.0
    minimum_short_excursion_frames: int = 2
    recrossing_tau_multiple: float = 2.0
    minimum_recrossing_frames: int = 4
    stride_factors: tuple[int, ...] = (1, 2, 4)
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        minimum = _positive_int(self.minimum_decorrelation_samples, "minimum_decorrelation_samples")
        if minimum < 4:
            raise TemporalAssignmentInputError("minimum_decorrelation_samples must be at least four.")
        maximum_lag = _positive_int(self.maximum_autocorrelation_lag, "maximum_autocorrelation_lag")
        deviation = _nonnegative(self.maximum_relative_stride_deviation, "maximum_relative_stride_deviation")
        if deviation >= 1.0:
            raise TemporalAssignmentInputError("maximum_relative_stride_deviation must be smaller than one.")
        persistence = _positive(self.minimum_persistence_tau_multiples, "minimum_persistence_tau_multiples")
        excursion = _positive(self.short_excursion_tau_multiple, "short_excursion_tau_multiple")
        min_excursion = _positive_int(self.minimum_short_excursion_frames, "minimum_short_excursion_frames")
        recross = _positive(self.recrossing_tau_multiple, "recrossing_tau_multiple")
        min_recross = _positive_int(self.minimum_recrossing_frames, "minimum_recrossing_frames")
        factors = tuple(sorted({_positive_int(v, "stride_factors") for v in self.stride_factors}))
        if not factors or factors[0] != 1:
            raise TemporalAssignmentInputError("stride_factors must include one.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": TEMPORAL_ASSIGNMENT_OPTIONS_SCHEMA,
            "minimum_decorrelation_samples": minimum,
            "maximum_autocorrelation_lag": maximum_lag,
            "maximum_relative_stride_deviation": deviation,
            "minimum_persistence_tau_multiples": persistence,
            "short_excursion_tau_multiple": excursion,
            "minimum_short_excursion_frames": min_excursion,
            "recrossing_tau_multiple": recross,
            "minimum_recrossing_frames": min_recross,
            "stride_factors": list(factors),
            "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TemporalAssignmentInputError("Temporal-assignment options signature is inconsistent.")
        for name, value in (
            ("minimum_decorrelation_samples", minimum),
            ("maximum_autocorrelation_lag", maximum_lag),
            ("maximum_relative_stride_deviation", deviation),
            ("minimum_persistence_tau_multiples", persistence),
            ("short_excursion_tau_multiple", excursion),
            ("minimum_short_excursion_frames", min_excursion),
            ("recrossing_tau_multiple", recross),
            ("minimum_recrossing_frames", min_recross),
            ("stride_factors", factors),
            ("metadata", metadata),
            ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TEMPORAL_ASSIGNMENT_OPTIONS_SCHEMA,
            "minimum_decorrelation_samples": self.minimum_decorrelation_samples,
            "maximum_autocorrelation_lag": self.maximum_autocorrelation_lag,
            "maximum_relative_stride_deviation": self.maximum_relative_stride_deviation,
            "minimum_persistence_tau_multiples": self.minimum_persistence_tau_multiples,
            "short_excursion_tau_multiple": self.short_excursion_tau_multiple,
            "minimum_short_excursion_frames": self.minimum_short_excursion_frames,
            "recrossing_tau_multiple": self.recrossing_tau_multiple,
            "minimum_recrossing_frames": self.minimum_recrossing_frames,
            "stride_factors": list(self.stride_factors),
            "metadata": _json_value(self.metadata),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TemporalAssignmentOptions":
        if payload.get("schema") != TEMPORAL_ASSIGNMENT_OPTIONS_SCHEMA:
            raise TemporalAssignmentSerializationError("Unsupported temporal-assignment options schema.")
        return cls(
            minimum_decorrelation_samples=int(payload["minimum_decorrelation_samples"]),
            maximum_autocorrelation_lag=int(payload["maximum_autocorrelation_lag"]),
            maximum_relative_stride_deviation=float(payload["maximum_relative_stride_deviation"]),
            minimum_persistence_tau_multiples=float(payload["minimum_persistence_tau_multiples"]),
            short_excursion_tau_multiple=float(payload["short_excursion_tau_multiple"]),
            minimum_short_excursion_frames=int(payload["minimum_short_excursion_frames"]),
            recrossing_tau_multiple=float(payload["recrossing_tau_multiple"]),
            minimum_recrossing_frames=int(payload["minimum_recrossing_frames"]),
            stride_factors=tuple(int(v) for v in payload["stride_factors"]),
            metadata=dict(payload.get("metadata", {})),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class TemporalAssignmentResourcePolicy:
    max_samples: int = 5_000_000
    max_atoms: int = 100_000
    max_intervals: int = 5_000_000
    max_passages: int = 5_000_000
    max_autocorrelation_terms: int = 500_000_000
    max_output_bytes: int = 1024 * 1024**2
    signature: str = ""

    def __post_init__(self) -> None:
        names = (
            "max_samples", "max_atoms", "max_intervals", "max_passages",
            "max_autocorrelation_terms", "max_output_bytes",
        )
        values = {name: _positive_int(getattr(self, name), name) for name in names}
        expected = _digest({"schema": TEMPORAL_ASSIGNMENT_RESOURCES_SCHEMA, **values})
        if self.signature and self.signature != expected:
            raise TemporalAssignmentInputError("Temporal-assignment resource signature is inconsistent.")
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TEMPORAL_ASSIGNMENT_RESOURCES_SCHEMA,
            "max_samples": self.max_samples,
            "max_atoms": self.max_atoms,
            "max_intervals": self.max_intervals,
            "max_passages": self.max_passages,
            "max_autocorrelation_terms": self.max_autocorrelation_terms,
            "max_output_bytes": self.max_output_bytes,
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TemporalAssignmentResourcePolicy":
        if payload.get("schema") != TEMPORAL_ASSIGNMENT_RESOURCES_SCHEMA:
            raise TemporalAssignmentSerializationError("Unsupported temporal-assignment resource schema.")
        return cls(
            max_samples=int(payload["max_samples"]), max_atoms=int(payload["max_atoms"]),
            max_intervals=int(payload["max_intervals"]), max_passages=int(payload["max_passages"]),
            max_autocorrelation_terms=int(payload["max_autocorrelation_terms"]),
            max_output_bytes=int(payload["max_output_bytes"]),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class ProvisionalMembershipTable:
    sample_catalog_signature: str
    grid_shape: tuple[int, int, int]
    logical_node_indices: IntArray
    raw_classification: UInt8Array
    basin_membership: Int32Array
    core_membership: Int32Array
    position_evidence_mask: BoolArray
    signature: str = ""

    def __post_init__(self) -> None:
        source = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        shape = tuple(_positive_int(v, "grid_shape") for v in self.grid_shape)
        if len(shape) != 3:
            raise TemporalAssignmentInputError("grid_shape must contain three entries.")
        nodes = _readonly(self.logical_node_indices, dtype=np.int64, ndim=1, name="logical_node_indices")
        n = nodes.size
        classes = _readonly(self.raw_classification, dtype=np.uint8, ndim=1, name="raw_classification", shape=(n,))
        valid = {int(v) for v in RawMembershipClass}
        if any(int(v) not in valid for v in np.unique(classes)):
            raise TemporalAssignmentInputError("raw_classification contains an unknown code.")
        basin = _readonly(self.basin_membership, dtype=np.int32, ndim=1, name="basin_membership", shape=(n,))
        core = _readonly(self.core_membership, dtype=np.int32, ndim=1, name="core_membership", shape=(n,))
        evidence = _readonly(self.position_evidence_mask, dtype=np.bool_, ndim=1, name="position_evidence_mask", shape=(n,))
        total_nodes = int(np.prod(shape))
        if np.any((nodes < -1) | (nodes >= total_nodes)):
            raise TemporalAssignmentInputError("logical_node_indices are outside the periodic logical grid.")
        if np.any((~evidence) & (classes != RawMembershipClass.EVIDENCE_EXCLUDED)):
            raise TemporalAssignmentInputError("Samples outside position evidence must be evidence_excluded.")
        if np.any((classes == RawMembershipClass.CORE) & (core < 0)):
            raise TemporalAssignmentInputError("Core-classified samples require one unique core id.")
        if np.any((classes == RawMembershipClass.BASIN) & (basin < 0)):
            raise TemporalAssignmentInputError("Basin-classified samples require one basin id.")
        payload = {
            "schema": PROVISIONAL_MEMBERSHIP_SCHEMA, "sample_catalog_signature": source,
            "grid_shape": list(shape), "node_digest": _array_digest(nodes),
            "classification_digest": _array_digest(classes), "basin_digest": _array_digest(basin),
            "core_digest": _array_digest(core), "evidence_digest": _array_digest(evidence),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TemporalAssignmentInputError("Provisional-membership signature is inconsistent.")
        for name, value in (
            ("sample_catalog_signature", source), ("grid_shape", shape),
            ("logical_node_indices", nodes), ("raw_classification", classes),
            ("basin_membership", basin), ("core_membership", core),
            ("position_evidence_mask", evidence), ("signature", expected),
        ):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PROVISIONAL_MEMBERSHIP_SCHEMA,
            "sample_catalog_signature": self.sample_catalog_signature,
            "grid_shape": list(self.grid_shape),
            "logical_node_indices": self.logical_node_indices.tolist(),
            "raw_classification": self.raw_classification.tolist(),
            "basin_membership": self.basin_membership.tolist(),
            "core_membership": self.core_membership.tolist(),
            "position_evidence_mask": self.position_evidence_mask.tolist(),
            "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProvisionalMembershipTable":
        if payload.get("schema") != PROVISIONAL_MEMBERSHIP_SCHEMA:
            raise TemporalAssignmentSerializationError("Unsupported provisional-membership schema.")
        return cls(
            sample_catalog_signature=str(payload["sample_catalog_signature"]),
            grid_shape=tuple(int(v) for v in payload["grid_shape"]),
            logical_node_indices=np.asarray(payload["logical_node_indices"], dtype=np.int64),
            raw_classification=np.asarray(payload["raw_classification"], dtype=np.uint8),
            basin_membership=np.asarray(payload["basin_membership"], dtype=np.int32),
            core_membership=np.asarray(payload["core_membership"], dtype=np.int32),
            position_evidence_mask=np.asarray(payload["position_evidence_mask"], dtype=np.bool_),
            signature=str(payload.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class CoreVisitInterval:
    interval_id: int
    atom_index: int
    attractor_id: int
    segment_id: int
    sample_indices: IntArray
    represented_time: float
    left_censored: bool
    right_censored: bool
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: int(getattr(self, name)) for name in ("interval_id", "atom_index", "attractor_id", "segment_id")}
        if any(v < 0 for v in values.values()):
            raise TemporalAssignmentInputError("Core-visit identifiers must be nonnegative.")
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        if samples.size == 0 or np.any(samples < 0):
            raise TemporalAssignmentInputError("A core visit requires nonnegative sample indices.")
        represented = _nonnegative(self.represented_time, "represented_time")
        payload = {"schema": CORE_VISIT_INTERVAL_SCHEMA, **values, "samples_digest": _array_digest(samples),
                   "represented_time": represented, "left_censored": bool(self.left_censored),
                   "right_censored": bool(self.right_censored)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise TemporalAssignmentInputError("Core-visit signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "sample_indices", samples); object.__setattr__(self, "represented_time", represented)
        object.__setattr__(self, "left_censored", bool(self.left_censored)); object.__setattr__(self, "right_censored", bool(self.right_censored))
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": CORE_VISIT_INTERVAL_SCHEMA, "interval_id": self.interval_id, "atom_index": self.atom_index,
                "attractor_id": self.attractor_id, "segment_id": self.segment_id, "sample_indices": self.sample_indices.tolist(),
                "represented_time": self.represented_time, "left_censored": self.left_censored,
                "right_censored": self.right_censored, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "CoreVisitInterval":
        if p.get("schema") != CORE_VISIT_INTERVAL_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported core-visit schema.")
        return cls(int(p["interval_id"]), int(p["atom_index"]), int(p["attractor_id"]), int(p["segment_id"]),
                   np.asarray(p["sample_indices"], dtype=np.int64), float(p["represented_time"]), bool(p["left_censored"]),
                   bool(p["right_censored"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class PreliminaryResidenceInterval:
    interval_id: int
    atom_index: int
    attractor_id: int
    segment_id: int
    core_entry_sample_index: int
    retained_sample_indices: IntArray
    first_outside_sample_index: int | None
    represented_time: float
    left_censored: bool
    right_censored: bool
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: int(getattr(self, name)) for name in ("interval_id", "atom_index", "attractor_id", "segment_id", "core_entry_sample_index")}
        if any(v < 0 for v in values.values()): raise TemporalAssignmentInputError("Residence identifiers must be nonnegative.")
        samples = _readonly(self.retained_sample_indices, dtype=np.int64, ndim=1, name="retained_sample_indices")
        if samples.size == 0 or samples[0] != values["core_entry_sample_index"]:
            raise TemporalAssignmentInputError("A residence must begin at its core-entry sample.")
        outside = None if self.first_outside_sample_index is None else int(self.first_outside_sample_index)
        if outside is not None and outside < 0: raise TemporalAssignmentInputError("first_outside_sample_index must be nonnegative.")
        represented = _nonnegative(self.represented_time, "represented_time")
        payload = {"schema": PRELIMINARY_RESIDENCE_SCHEMA, **values, "retained_digest": _array_digest(samples),
                   "first_outside_sample_index": outside, "represented_time": represented,
                   "left_censored": bool(self.left_censored), "right_censored": bool(self.right_censored)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise TemporalAssignmentInputError("Residence signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "retained_sample_indices", samples); object.__setattr__(self, "first_outside_sample_index", outside)
        object.__setattr__(self, "represented_time", represented); object.__setattr__(self, "left_censored", bool(self.left_censored))
        object.__setattr__(self, "right_censored", bool(self.right_censored)); object.__setattr__(self, "signature", expected)

    @property
    def n_samples(self) -> int:
        return int(self.retained_sample_indices.size)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PRELIMINARY_RESIDENCE_SCHEMA, "interval_id": self.interval_id, "atom_index": self.atom_index,
                "attractor_id": self.attractor_id, "segment_id": self.segment_id,
                "core_entry_sample_index": self.core_entry_sample_index,
                "retained_sample_indices": self.retained_sample_indices.tolist(),
                "first_outside_sample_index": self.first_outside_sample_index, "represented_time": self.represented_time,
                "left_censored": self.left_censored, "right_censored": self.right_censored, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PreliminaryResidenceInterval":
        if p.get("schema") != PRELIMINARY_RESIDENCE_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported residence schema.")
        return cls(int(p["interval_id"]), int(p["atom_index"]), int(p["attractor_id"]), int(p["segment_id"]),
                   int(p["core_entry_sample_index"]), np.asarray(p["retained_sample_indices"], dtype=np.int64),
                   None if p.get("first_outside_sample_index") is None else int(p["first_outside_sample_index"]),
                   float(p["represented_time"]), bool(p["left_censored"]), bool(p["right_censored"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class PreliminaryPassage:
    passage_id: int
    atom_index: int
    segment_id: int
    source_attractor_id: int
    target_attractor_id: int | None
    outside_sample_indices: IntArray
    target_core_sample_index: int | None
    outcome: PassageOutcome
    represented_time: float
    contains_unsupported_or_unresolved: bool
    short_excursion: bool = False
    recrossing: bool = False
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: int(getattr(self, name)) for name in ("passage_id", "atom_index", "segment_id", "source_attractor_id")}
        if any(v < 0 for v in values.values()): raise TemporalAssignmentInputError("Passage identifiers must be nonnegative.")
        target = None if self.target_attractor_id is None else int(self.target_attractor_id)
        if target is not None and target < 0: raise TemporalAssignmentInputError("target_attractor_id must be nonnegative.")
        samples = _readonly(self.outside_sample_indices, dtype=np.int64, ndim=1, name="outside_sample_indices")
        if np.any(samples < 0): raise TemporalAssignmentInputError("outside_sample_indices must be nonnegative.")
        target_sample = None if self.target_core_sample_index is None else int(self.target_core_sample_index)
        if target_sample is not None and target_sample < 0: raise TemporalAssignmentInputError("target_core_sample_index must be nonnegative.")
        outcome = PassageOutcome(self.outcome)
        if outcome in {PassageOutcome.JUMP, PassageOutcome.RETURN_EXCURSION} and (target is None or target_sample is None):
            raise TemporalAssignmentInputError("Resolved passage outcomes require a target core.")
        if outcome is PassageOutcome.RETURN_EXCURSION and target != values["source_attractor_id"]:
            raise TemporalAssignmentInputError("A return excursion must return to the source attractor.")
        if outcome is PassageOutcome.JUMP and target == values["source_attractor_id"]:
            raise TemporalAssignmentInputError("A jump must reach a different attractor.")
        represented = _nonnegative(self.represented_time, "represented_time")
        payload = {"schema": PRELIMINARY_PASSAGE_SCHEMA, **values, "target_attractor_id": target,
                   "outside_digest": _array_digest(samples), "target_core_sample_index": target_sample,
                   "outcome": outcome.value, "represented_time": represented,
                   "contains_unsupported_or_unresolved": bool(self.contains_unsupported_or_unresolved),
                   "short_excursion": bool(self.short_excursion), "recrossing": bool(self.recrossing)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise TemporalAssignmentInputError("Passage signature is inconsistent.")
        for name, value in values.items(): object.__setattr__(self, name, value)
        object.__setattr__(self, "target_attractor_id", target); object.__setattr__(self, "outside_sample_indices", samples)
        object.__setattr__(self, "target_core_sample_index", target_sample); object.__setattr__(self, "outcome", outcome)
        object.__setattr__(self, "represented_time", represented)
        object.__setattr__(self, "contains_unsupported_or_unresolved", bool(self.contains_unsupported_or_unresolved))
        object.__setattr__(self, "short_excursion", bool(self.short_excursion)); object.__setattr__(self, "recrossing", bool(self.recrossing))
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PRELIMINARY_PASSAGE_SCHEMA, "passage_id": self.passage_id, "atom_index": self.atom_index,
                "segment_id": self.segment_id, "source_attractor_id": self.source_attractor_id,
                "target_attractor_id": self.target_attractor_id, "outside_sample_indices": self.outside_sample_indices.tolist(),
                "target_core_sample_index": self.target_core_sample_index, "outcome": self.outcome.value,
                "represented_time": self.represented_time,
                "contains_unsupported_or_unresolved": self.contains_unsupported_or_unresolved,
                "short_excursion": self.short_excursion, "recrossing": self.recrossing, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PreliminaryPassage":
        if p.get("schema") != PRELIMINARY_PASSAGE_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported passage schema.")
        return cls(int(p["passage_id"]), int(p["atom_index"]), int(p["segment_id"]), int(p["source_attractor_id"]),
                   None if p.get("target_attractor_id") is None else int(p["target_attractor_id"]),
                   np.asarray(p["outside_sample_indices"], dtype=np.int64),
                   None if p.get("target_core_sample_index") is None else int(p["target_core_sample_index"]),
                   PassageOutcome(p["outcome"]), float(p["represented_time"]),
                   bool(p["contains_unsupported_or_unresolved"]), bool(p.get("short_excursion", False)),
                   bool(p.get("recrossing", False)), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class LocalDecorrelationEstimate:
    attractor_id: int
    status: DecorrelationStatus
    estimator: str
    sample_count: int
    interval_count: int
    maximum_lag_used: int
    autocorrelation: FloatArray
    statistical_inefficiency_frames: float | None
    decorrelation_time_frames: float | None
    median_frame_spacing: float | None
    decorrelation_time: float | None
    time_units: str
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        aid = int(self.attractor_id); samples = int(self.sample_count); intervals = int(self.interval_count); lag = int(self.maximum_lag_used)
        if min(aid, samples, intervals, lag) < 0: raise TemporalAssignmentInputError("Decorrelation counters must be nonnegative.")
        status = DecorrelationStatus(self.status)
        if not isinstance(self.estimator, str) or not self.estimator: raise TemporalAssignmentInputError("estimator must be nonempty.")
        acf = _readonly(self.autocorrelation, dtype=np.float64, ndim=1, name="autocorrelation")
        ineff = None if self.statistical_inefficiency_frames is None else _positive(self.statistical_inefficiency_frames, "statistical_inefficiency_frames")
        tau_frames = None if self.decorrelation_time_frames is None else _positive(self.decorrelation_time_frames, "decorrelation_time_frames")
        spacing = None if self.median_frame_spacing is None else _positive(self.median_frame_spacing, "median_frame_spacing")
        tau = None if self.decorrelation_time is None else _positive(self.decorrelation_time, "decorrelation_time")
        if status in {DecorrelationStatus.RESOLVED, DecorrelationStatus.FRAME_ONLY_IRREGULAR_STRIDE} and tau_frames is None:
            raise TemporalAssignmentInputError("Resolved decorrelation estimates require a frame timescale.")
        payload = {"schema": LOCAL_DECORRELATION_SCHEMA, "attractor_id": aid, "status": status.value,
                   "estimator": self.estimator, "sample_count": samples, "interval_count": intervals,
                   "maximum_lag_used": lag, "acf_digest": _array_digest(acf),
                   "statistical_inefficiency_frames": ineff, "decorrelation_time_frames": tau_frames,
                   "median_frame_spacing": spacing, "decorrelation_time": tau, "time_units": str(self.time_units),
                   "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise TemporalAssignmentInputError("Decorrelation signature is inconsistent.")
        for name, value in (("attractor_id", aid), ("status", status), ("sample_count", samples), ("interval_count", intervals),
                            ("maximum_lag_used", lag), ("autocorrelation", acf), ("statistical_inefficiency_frames", ineff),
                            ("decorrelation_time_frames", tau_frames), ("median_frame_spacing", spacing),
                            ("decorrelation_time", tau), ("time_units", str(self.time_units)), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": LOCAL_DECORRELATION_SCHEMA, "attractor_id": self.attractor_id, "status": self.status.value,
                "estimator": self.estimator, "sample_count": self.sample_count, "interval_count": self.interval_count,
                "maximum_lag_used": self.maximum_lag_used, "autocorrelation": self.autocorrelation.tolist(),
                "statistical_inefficiency_frames": self.statistical_inefficiency_frames,
                "decorrelation_time_frames": self.decorrelation_time_frames, "median_frame_spacing": self.median_frame_spacing,
                "decorrelation_time": self.decorrelation_time, "time_units": self.time_units,
                "diagnostic": self.diagnostic, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "LocalDecorrelationEstimate":
        if p.get("schema") != LOCAL_DECORRELATION_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported decorrelation schema.")
        return cls(int(p["attractor_id"]), DecorrelationStatus(p["status"]), str(p["estimator"]), int(p["sample_count"]),
                   int(p["interval_count"]), int(p["maximum_lag_used"]), np.asarray(p["autocorrelation"], dtype=np.float64),
                   p.get("statistical_inefficiency_frames"), p.get("decorrelation_time_frames"), p.get("median_frame_spacing"),
                   p.get("decorrelation_time"), str(p["time_units"]), p.get("diagnostic"), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class AttractorTemporalDiagnostic:
    attractor_id: int
    support_status: TemporalSupportStatus
    residence_count: int
    uncensored_residence_count: int
    total_represented_time: float
    maximum_residence_time: float
    median_residence_time: float | None
    persistence_ratio: float | None
    decorrelation_signature: str
    diagnostic: str | None = None
    signature: str = ""

    def __post_init__(self) -> None:
        aid = int(self.attractor_id); count = int(self.residence_count); uncensored = int(self.uncensored_residence_count)
        if min(aid, count, uncensored) < 0 or uncensored > count: raise TemporalAssignmentInputError("Invalid temporal counters.")
        status = TemporalSupportStatus(self.support_status)
        total = _nonnegative(self.total_represented_time, "total_represented_time")
        maximum = _nonnegative(self.maximum_residence_time, "maximum_residence_time")
        median = None if self.median_residence_time is None else _nonnegative(self.median_residence_time, "median_residence_time")
        ratio = None if self.persistence_ratio is None else _nonnegative(self.persistence_ratio, "persistence_ratio")
        decor = _sha(self.decorrelation_signature, "decorrelation_signature")
        payload = {"schema": ATTRACTOR_TEMPORAL_DIAGNOSTIC_SCHEMA, "attractor_id": aid, "support_status": status.value,
                   "residence_count": count, "uncensored_residence_count": uncensored, "total_represented_time": total,
                   "maximum_residence_time": maximum, "median_residence_time": median, "persistence_ratio": ratio,
                   "decorrelation_signature": decor, "diagnostic": self.diagnostic}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise TemporalAssignmentInputError("Attractor-temporal signature is inconsistent.")
        for name, value in (("attractor_id", aid), ("support_status", status), ("residence_count", count),
                            ("uncensored_residence_count", uncensored), ("total_represented_time", total),
                            ("maximum_residence_time", maximum), ("median_residence_time", median),
                            ("persistence_ratio", ratio), ("decorrelation_signature", decor), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ATTRACTOR_TEMPORAL_DIAGNOSTIC_SCHEMA, "attractor_id": self.attractor_id,
                "support_status": self.support_status.value, "residence_count": self.residence_count,
                "uncensored_residence_count": self.uncensored_residence_count,
                "total_represented_time": self.total_represented_time,
                "maximum_residence_time": self.maximum_residence_time,
                "median_residence_time": self.median_residence_time, "persistence_ratio": self.persistence_ratio,
                "decorrelation_signature": self.decorrelation_signature, "diagnostic": self.diagnostic,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "AttractorTemporalDiagnostic":
        if p.get("schema") != ATTRACTOR_TEMPORAL_DIAGNOSTIC_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported attractor-temporal schema.")
        return cls(int(p["attractor_id"]), TemporalSupportStatus(p["support_status"]), int(p["residence_count"]),
                   int(p["uncensored_residence_count"]), float(p["total_represented_time"]), float(p["maximum_residence_time"]),
                   p.get("median_residence_time"), p.get("persistence_ratio"), str(p["decorrelation_signature"]),
                   p.get("diagnostic"), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StrideSensitivityDiagnostic:
    stride_factors: tuple[int, ...]
    jump_counts: tuple[int, ...]
    return_excursion_counts: tuple[int, ...]
    unresolved_counts: tuple[int, ...]
    sensitive: bool
    signature: str = ""

    def __post_init__(self) -> None:
        strides = tuple(_positive_int(v, "stride_factors") for v in self.stride_factors)
        jumps = tuple(int(v) for v in self.jump_counts); returns = tuple(int(v) for v in self.return_excursion_counts)
        unresolved = tuple(int(v) for v in self.unresolved_counts)
        if not (len(strides) == len(jumps) == len(returns) == len(unresolved)) or not strides:
            raise TemporalAssignmentInputError("Stride diagnostic arrays must be nonempty and aligned.")
        if any(v < 0 for v in jumps + returns + unresolved): raise TemporalAssignmentInputError("Stride counts must be nonnegative.")
        payload = {"schema": STRIDE_SENSITIVITY_SCHEMA, "stride_factors": list(strides), "jump_counts": list(jumps),
                   "return_excursion_counts": list(returns), "unresolved_counts": list(unresolved), "sensitive": bool(self.sensitive)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise TemporalAssignmentInputError("Stride-sensitivity signature is inconsistent.")
        for name, value in (("stride_factors", strides), ("jump_counts", jumps), ("return_excursion_counts", returns),
                            ("unresolved_counts", unresolved), ("sensitive", bool(self.sensitive)), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STRIDE_SENSITIVITY_SCHEMA, "stride_factors": list(self.stride_factors),
                "jump_counts": list(self.jump_counts), "return_excursion_counts": list(self.return_excursion_counts),
                "unresolved_counts": list(self.unresolved_counts), "sensitive": self.sensitive, "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "StrideSensitivityDiagnostic":
        if p.get("schema") != STRIDE_SENSITIVITY_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported stride schema.")
        return cls(tuple(p["stride_factors"]), tuple(p["jump_counts"]), tuple(p["return_excursion_counts"]),
                   tuple(p["unresolved_counts"]), bool(p["sensitive"]), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class ProvisionalTemporalAssignmentCatalog:
    sample_catalog_signature: str
    density_estimate_signature: str
    attractor_catalog_signature: str
    force_refinement_signature: str | None
    options: TemporalAssignmentOptions
    resources: TemporalAssignmentResourcePolicy
    membership: ProvisionalMembershipTable
    core_visits: tuple[CoreVisitInterval, ...]
    residences: tuple[PreliminaryResidenceInterval, ...]
    passages: tuple[PreliminaryPassage, ...]
    decorrelation_estimates: tuple[LocalDecorrelationEstimate, ...]
    attractor_diagnostics: tuple[AttractorTemporalDiagnostic, ...]
    stride_diagnostic: StrideSensitivityDiagnostic
    temporal_support_status: TemporalSupportStatus
    evidence_pattern: TemporalEvidencePattern
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        source = _sha(self.sample_catalog_signature, "sample_catalog_signature")
        density = _sha(self.density_estimate_signature, "density_estimate_signature")
        attractors = _sha(self.attractor_catalog_signature, "attractor_catalog_signature")
        force = None if self.force_refinement_signature is None else _sha(self.force_refinement_signature, "force_refinement_signature")
        if self.membership.sample_catalog_signature != source: raise TemporalAssignmentInputError("Membership belongs to another sample catalog.")
        visits = tuple(self.core_visits); residences = tuple(self.residences); passages = tuple(self.passages)
        decor = tuple(self.decorrelation_estimates); diagnostics = tuple(self.attractor_diagnostics)
        if tuple(v.interval_id for v in visits) != tuple(range(len(visits))): raise TemporalAssignmentInputError("Core-visit ids must be canonical.")
        if tuple(v.interval_id for v in residences) != tuple(range(len(residences))): raise TemporalAssignmentInputError("Residence ids must be canonical.")
        if tuple(v.passage_id for v in passages) != tuple(range(len(passages))): raise TemporalAssignmentInputError("Passage ids must be canonical.")
        if tuple(v.attractor_id for v in decor) != tuple(range(len(decor))): raise TemporalAssignmentInputError("Decorrelation ids must be canonical.")
        if tuple(v.attractor_id for v in diagnostics) != tuple(range(len(diagnostics))): raise TemporalAssignmentInputError("Attractor diagnostic ids must be canonical.")
        support = TemporalSupportStatus(self.temporal_support_status); pattern = TemporalEvidencePattern(self.evidence_pattern)
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": TEMPORAL_ASSIGNMENT_CATALOG_SCHEMA, "sample_catalog_signature": source,
                   "density_estimate_signature": density, "attractor_catalog_signature": attractors,
                   "force_refinement_signature": force, "options_signature": self.options.signature,
                   "resources_signature": self.resources.signature, "membership_signature": self.membership.signature,
                   "core_visit_signatures": [v.signature for v in visits], "residence_signatures": [v.signature for v in residences],
                   "passage_signatures": [v.signature for v in passages], "decorrelation_signatures": [v.signature for v in decor],
                   "attractor_diagnostic_signatures": [v.signature for v in diagnostics],
                   "stride_diagnostic_signature": self.stride_diagnostic.signature,
                   "temporal_support_status": support.value, "evidence_pattern": pattern.value, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected: raise TemporalAssignmentInputError("Temporal-assignment catalog signature is inconsistent.")
        for name, value in (("sample_catalog_signature", source), ("density_estimate_signature", density),
                            ("attractor_catalog_signature", attractors), ("force_refinement_signature", force),
                            ("core_visits", visits), ("residences", residences), ("passages", passages),
                            ("decorrelation_estimates", decor), ("attractor_diagnostics", diagnostics),
                            ("temporal_support_status", support), ("evidence_pattern", pattern),
                            ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": TEMPORAL_ASSIGNMENT_CATALOG_SCHEMA, "sample_catalog_signature": self.sample_catalog_signature,
                "density_estimate_signature": self.density_estimate_signature,
                "attractor_catalog_signature": self.attractor_catalog_signature,
                "force_refinement_signature": self.force_refinement_signature, "options": self.options.to_dict(),
                "resources": self.resources.to_dict(), "membership": self.membership.to_dict(),
                "core_visits": [v.to_dict() for v in self.core_visits], "residences": [v.to_dict() for v in self.residences],
                "passages": [v.to_dict() for v in self.passages],
                "decorrelation_estimates": [v.to_dict() for v in self.decorrelation_estimates],
                "attractor_diagnostics": [v.to_dict() for v in self.attractor_diagnostics],
                "stride_diagnostic": self.stride_diagnostic.to_dict(),
                "temporal_support_status": self.temporal_support_status.value,
                "evidence_pattern": self.evidence_pattern.value, "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "ProvisionalTemporalAssignmentCatalog":
        if p.get("schema") != TEMPORAL_ASSIGNMENT_CATALOG_SCHEMA: raise TemporalAssignmentSerializationError("Unsupported temporal-assignment catalog schema.")
        return cls(str(p["sample_catalog_signature"]), str(p["density_estimate_signature"]), str(p["attractor_catalog_signature"]),
                   p.get("force_refinement_signature"), TemporalAssignmentOptions.from_dict(p["options"]),
                   TemporalAssignmentResourcePolicy.from_dict(p["resources"]), ProvisionalMembershipTable.from_dict(p["membership"]),
                   tuple(CoreVisitInterval.from_dict(v) for v in p["core_visits"]),
                   tuple(PreliminaryResidenceInterval.from_dict(v) for v in p["residences"]),
                   tuple(PreliminaryPassage.from_dict(v) for v in p["passages"]),
                   tuple(LocalDecorrelationEstimate.from_dict(v) for v in p["decorrelation_estimates"]),
                   tuple(AttractorTemporalDiagnostic.from_dict(v) for v in p["attractor_diagnostics"]),
                   StrideSensitivityDiagnostic.from_dict(p["stride_diagnostic"]),
                   TemporalSupportStatus(p["temporal_support_status"]), TemporalEvidencePattern(p["evidence_pattern"]),
                   dict(p.get("metadata", {})), str(p.get("signature", "")))


def _sample_nodes(frac: np.ndarray, shape: tuple[int, int, int]) -> tuple[np.ndarray, np.ndarray]:
    shape_arr = np.asarray(shape, dtype=np.int64)
    grid = np.floor(np.mod(frac, 1.0) * shape_arr[None, :] + 0.5).astype(np.int64) % shape_arr[None, :]
    flat = np.ravel_multi_index((grid[:, 0], grid[:, 1], grid[:, 2]), shape).astype(np.int64)
    return grid, flat


def _prepare_membership(catalog: FrameworkAlignedIonSampleCatalog, attractors: DensityAttractorCatalog) -> ProvisionalMembershipTable:
    complex_ = attractors.cell_complex
    shape = complex_.grid_shape
    _, flat = _sample_nodes(catalog.registered_wrapped_fractional, shape)
    n = catalog.n_samples
    evidence = np.asarray(catalog.evidence_masks.position_mask, dtype=bool)
    classes = np.full(n, RawMembershipClass.EVIDENCE_EXCLUDED, dtype=np.uint8)
    basin = np.full(n, -1, dtype=np.int32)
    core = np.full(n, -1, dtype=np.int32)
    core_lookup = np.full(int(np.prod(shape)), -1, dtype=np.int32)
    owner_flat = complex_.basin_owner.reshape(-1)
    class_flat = complex_.classification.reshape(-1)
    for item in attractors.provisional_cores:
        if not item.resolved:
            continue
        for node in item.core_node_indices:
            node_i = int(node)
            if node_i >= core_lookup.size:
                raise TemporalAssignmentInputError("A provisional core refers outside the logical grid.")
            if int(owner_flat[node_i]) != item.attractor_id or int(class_flat[node_i]) != int(CellClassification.SUPPORTED_BASIN):
                raise TemporalAssignmentInputError("Resolved provisional cores must be subsets of their supported basins.")
            old = int(core_lookup[node_i])
            core_lookup[node_i] = item.attractor_id if old in {-1, item.attractor_id} else -2
    for i in np.flatnonzero(evidence):
        node = int(flat[i]); code = CellClassification(int(class_flat[node])); owner = int(owner_flat[node]); core_id = int(core_lookup[node])
        if core_id == -2:
            classes[i] = RawMembershipClass.CORE_OVERLAP; core[i] = -2
        elif core_id >= 0:
            classes[i] = RawMembershipClass.CORE; core[i] = core_id; basin[i] = core_id
        elif code is CellClassification.SUPPORTED_BASIN:
            if owner < 0: raise TemporalAssignmentInputError("A supported basin node lacks an owner.")
            classes[i] = RawMembershipClass.BASIN; basin[i] = owner
        elif code is CellClassification.SUPPORTED_TRANSITION_REGION:
            classes[i] = RawMembershipClass.TRANSITION_REGION
        elif code is CellClassification.SUPPORTED_BACKGROUND:
            classes[i] = RawMembershipClass.SUPPORTED_BACKGROUND
        elif code is CellClassification.UNSUPPORTED_UNKNOWN:
            classes[i] = RawMembershipClass.UNSUPPORTED_UNKNOWN
        elif code is CellClassification.NUMERICALLY_UNRESOLVED:
            classes[i] = RawMembershipClass.NUMERICALLY_UNRESOLVED
        else:
            raise TemporalAssignmentInputError("Unknown E2 cell classification.")
    nodes = np.where(evidence, flat, -1)
    return ProvisionalMembershipTable(catalog.signature, shape, nodes, classes, basin, core, evidence)


def _sample_segment_ids(catalog: FrameworkAlignedIonSampleCatalog) -> np.ndarray:
    weighting = catalog.temporal_weighting
    frame_to_segment = {int(frame): int(seg) for frame, seg in zip(weighting.frame_indices, weighting.segment_ids, strict=True)}
    try:
        return np.asarray([frame_to_segment[int(frame)] for frame in catalog.frame_indices], dtype=np.int32)
    except KeyError as exc:
        raise TemporalAssignmentInputError("A compact sample frame is absent from temporal weighting.") from exc


def _valid_sequences(catalog: FrameworkAlignedIonSampleCatalog, membership: ProvisionalMembershipTable) -> list[tuple[int, int, np.ndarray]]:
    segment_ids = _sample_segment_ids(catalog)
    frame_rank = {int(frame): rank for rank, frame in enumerate(catalog.temporal_weighting.frame_indices)}
    sequences: list[tuple[int, int, np.ndarray]] = []
    for atom in catalog.selected_atom_indices:
        indices = np.flatnonzero(catalog.atom_indices == atom)
        order = np.argsort(catalog.frame_indices[indices], kind="stable")
        indices = indices[order]
        current: list[int] = []; current_segment: int | None = None; last_rank: int | None = None
        for sample in indices:
            sample_i = int(sample); valid = bool(membership.position_evidence_mask[sample_i])
            segment = int(segment_ids[sample_i]); rank = frame_rank[int(catalog.frame_indices[sample_i])]
            continuous = valid and current and current_segment == segment and last_rank is not None and rank == last_rank + 1
            if not valid or (current and not continuous):
                if current: sequences.append((int(atom), int(current_segment), np.asarray(current, dtype=np.int64)))
                current = []
            if valid:
                if not current: current_segment = segment
                current.append(sample_i); last_rank = rank
            else:
                current_segment = None; last_rank = None
        if current: sequences.append((int(atom), int(current_segment), np.asarray(current, dtype=np.int64)))
    return sequences


def _weight_sum(catalog: FrameworkAlignedIonSampleCatalog, samples: Sequence[int] | np.ndarray) -> float:
    if len(samples) == 0: return 0.0
    return float(np.sum(catalog.represented_time_weights[np.asarray(samples, dtype=np.int64)]))


def _segment_intervals(
    catalog: FrameworkAlignedIonSampleCatalog,
    membership: ProvisionalMembershipTable,
    sequences: Sequence[tuple[int, int, np.ndarray]],
    resources: TemporalAssignmentResourcePolicy,
) -> tuple[list[CoreVisitInterval], list[PreliminaryResidenceInterval], list[PreliminaryPassage]]:
    visits: list[CoreVisitInterval] = []; residences: list[PreliminaryResidenceInterval] = []; passages: list[PreliminaryPassage] = []
    for atom, segment, sequence in sequences:
        # Exact maximal core visits.
        start = 0
        while start < len(sequence):
            core_id = int(membership.core_membership[sequence[start]])
            if core_id < 0:
                start += 1; continue
            stop = start + 1
            while stop < len(sequence) and int(membership.core_membership[sequence[stop]]) == core_id:
                stop += 1
            visit_samples = sequence[start:stop]
            visits.append(CoreVisitInterval(len(visits), atom, core_id, segment, visit_samples,
                                            _weight_sum(catalog, visit_samples), start == 0, stop == len(sequence)))
            if len(visits) > resources.max_intervals: raise TemporalAssignmentResourceError("Core-visit count exceeds max_intervals.")
            start = stop

        active_id: int | None = None; retained: list[int] = []; active_left = False
        pending_source: int | None = None; outside: list[int] = []; contains_gap = False
        for pos, sample in enumerate(sequence):
            sample_i = int(sample); core_id = int(membership.core_membership[sample_i]); basin_id = int(membership.basin_membership[sample_i])
            raw = RawMembershipClass(int(membership.raw_classification[sample_i]))
            if active_id is not None:
                if core_id == active_id or basin_id == active_id:
                    retained.append(sample_i); continue
                residences.append(PreliminaryResidenceInterval(len(residences), atom, active_id, segment,
                    retained[0], np.asarray(retained, dtype=np.int64), sample_i, _weight_sum(catalog, retained), active_left, False))
                if len(residences) > resources.max_intervals: raise TemporalAssignmentResourceError("Residence count exceeds max_intervals.")
                pending_source = active_id; outside = [sample_i]; contains_gap = raw in {
                    RawMembershipClass.UNSUPPORTED_UNKNOWN, RawMembershipClass.NUMERICALLY_UNRESOLVED, RawMembershipClass.CORE_OVERLAP}
                active_id = None; retained = []; active_left = False
                if core_id >= 0:
                    outcome = PassageOutcome.UNRESOLVED_GAP if contains_gap else (
                        PassageOutcome.RETURN_EXCURSION if core_id == pending_source else PassageOutcome.JUMP)
                    passages.append(PreliminaryPassage(len(passages), atom, segment, pending_source, core_id,
                        np.asarray(outside[:-1], dtype=np.int64), sample_i, outcome, _weight_sum(catalog, outside), contains_gap))
                    pending_source = None; outside = []; contains_gap = False
                    active_id = core_id; retained = [sample_i]
                continue
            if pending_source is not None:
                if raw in {RawMembershipClass.UNSUPPORTED_UNKNOWN, RawMembershipClass.NUMERICALLY_UNRESOLVED, RawMembershipClass.CORE_OVERLAP}:
                    contains_gap = True
                if core_id >= 0:
                    outcome = PassageOutcome.UNRESOLVED_GAP if contains_gap else (
                        PassageOutcome.RETURN_EXCURSION if core_id == pending_source else PassageOutcome.JUMP)
                    passages.append(PreliminaryPassage(len(passages), atom, segment, pending_source, core_id,
                        np.asarray(outside, dtype=np.int64), sample_i, outcome,
                        _weight_sum(catalog, [*outside, sample_i]), contains_gap))
                    if len(passages) > resources.max_passages: raise TemporalAssignmentResourceError("Passage count exceeds max_passages.")
                    pending_source = None; outside = []; contains_gap = False
                    active_id = core_id; retained = [sample_i]
                else:
                    outside.append(sample_i)
                continue
            if core_id >= 0:
                active_id = core_id; retained = [sample_i]; active_left = pos == 0
        if active_id is not None:
            residences.append(PreliminaryResidenceInterval(len(residences), atom, active_id, segment,
                retained[0], np.asarray(retained, dtype=np.int64), None, _weight_sum(catalog, retained), active_left, True))
        elif pending_source is not None:
            passages.append(PreliminaryPassage(len(passages), atom, segment, pending_source, None,
                np.asarray(outside, dtype=np.int64), None, PassageOutcome.RIGHT_CENSORED_EXIT,
                _weight_sum(catalog, outside), contains_gap))
        if len(residences) > resources.max_intervals or len(passages) > resources.max_passages:
            raise TemporalAssignmentResourceError("Temporal interval count exceeds declared resources.")
    return visits, residences, passages


def _periodic_delta(points: np.ndarray, anchor: np.ndarray) -> np.ndarray:
    delta = np.asarray(points, dtype=np.float64) - np.asarray(anchor, dtype=np.float64)
    return delta - np.rint(delta)


def _geyer_initial_positive_sequence(rho: Sequence[float]) -> tuple[float, int]:
    """Return statistical inefficiency and last retained lag.

    The initial-positive sequence uses the conventional paired autocorrelation
    sums ``rho[2m] + rho[2m + 1]``.  Lag zero participates only in the
    positivity test and is not added to the positive-lag sum a second time.
    """
    values = np.asarray(rho, dtype=np.float64)
    if values.ndim != 1 or values.size == 0 or np.any(~np.isfinite(values)):
        raise TemporalAssignmentInputError("Autocorrelation sequence must be finite and one-dimensional.")
    positive_lag_sum = 0.0
    last_retained_lag = 0
    pair_start = 0
    while pair_start < values.size:
        pair_stop = min(pair_start + 2, values.size)
        paired_sum = float(np.sum(values[pair_start:pair_stop]))
        if paired_sum <= 0.0:
            break
        first_positive_lag = max(1, pair_start)
        if first_positive_lag < pair_stop:
            positive_lag_sum += float(np.sum(values[first_positive_lag:pair_stop]))
            last_retained_lag = pair_stop - 1
        pair_start += 2
    inefficiency = max(1.0, 1.0 + 2.0 * positive_lag_sum)
    return inefficiency, last_retained_lag


def _decorrelation(
    catalog: FrameworkAlignedIonSampleCatalog,
    density: PeriodicSpeciesDensityEstimate,
    attractors: DensityAttractorCatalog,
    residences: Sequence[PreliminaryResidenceInterval],
    options: TemporalAssignmentOptions,
) -> list[LocalDecorrelationEstimate]:
    result: list[LocalDecorrelationEstimate] = []
    L = density.analysis_metric.orthonormal_factor
    times = catalog.temporal_weighting.source_times
    for attractor in attractors.attractors:
        intervals = [r for r in residences if r.attractor_id == attractor.attractor_id]
        if not intervals:
            result.append(LocalDecorrelationEstimate(attractor.attractor_id, DecorrelationStatus.NO_RESIDENCE,
                "multivariate_initial_positive_sequence", 0, 0, 0, np.empty(0), None, None, None, None,
                catalog.temporal_weighting.weight_units, "no preliminary residence")); continue
        series: list[np.ndarray] = []; spacings: list[float] = []
        for interval in intervals:
            frac = catalog.registered_wrapped_fractional[interval.retained_sample_indices]
            series.append(_periodic_delta(frac, attractor.anchor_fractional) @ L)
            if times is not None and len(interval.retained_sample_indices) > 1:
                frame_indices = catalog.frame_indices[interval.retained_sample_indices]
                dt = np.diff(times[frame_indices])
                spacings.extend(float(v) for v in dt)
        count = sum(len(v) for v in series)
        if count < options.minimum_decorrelation_samples:
            result.append(LocalDecorrelationEstimate(attractor.attractor_id, DecorrelationStatus.INSUFFICIENT_SAMPLES,
                "multivariate_initial_positive_sequence", count, len(series), 0, np.empty(0), None, None,
                None if not spacings else float(np.median(spacings)), None, catalog.temporal_weighting.weight_units,
                f"samples {count}<{options.minimum_decorrelation_samples}")); continue
        all_values = np.concatenate(series, axis=0); mean = np.mean(all_values, axis=0)
        centered = [values - mean for values in series]
        c0 = float(np.mean(np.sum(np.concatenate(centered, axis=0) ** 2, axis=1)))
        if c0 <= np.finfo(float).tiny:
            result.append(LocalDecorrelationEstimate(attractor.attractor_id, DecorrelationStatus.ZERO_VARIANCE,
                "multivariate_initial_positive_sequence", count, len(series), 0, np.asarray([1.0]), None, None,
                None if not spacings else float(np.median(spacings)), None, catalog.temporal_weighting.weight_units,
                "site-conditioned coordinate variance is zero")); continue
        max_lag = min(options.maximum_autocorrelation_lag, max(len(v) for v in centered) - 1)
        rho = [1.0]
        for lag in range(1, max_lag + 1):
            values = [np.sum(v[:-lag] * v[lag:], axis=1) for v in centered if len(v) > lag]
            if not values: break
            rho.append(float(np.mean(np.concatenate(values)) / c0))
        # Geyer initial-positive paired sequence; the multivariate dot-product
        # autocorrelation is the scalar observable.
        ineff, last = _geyer_initial_positive_sequence(rho)
        tau_frames = 0.5 * ineff
        spacing = None if not spacings else float(np.median(spacings))
        irregular = False
        if spacings and spacing is not None:
            irregular = bool(np.max(np.abs(np.asarray(spacings) - spacing)) > options.maximum_relative_stride_deviation * spacing)
        status = DecorrelationStatus.FRAME_ONLY_IRREGULAR_STRIDE if irregular else DecorrelationStatus.RESOLVED
        tau_time = None if irregular or spacing is None else tau_frames * spacing
        result.append(LocalDecorrelationEstimate(attractor.attractor_id, status,
            "multivariate_initial_positive_sequence", count, len(series), last, np.asarray(rho), ineff, tau_frames,
            spacing, tau_time, catalog.temporal_weighting.weight_units,
            "irregular sampling; frame timescale only" if irregular else None))
    return result


def _classify_passages(
    catalog: FrameworkAlignedIonSampleCatalog,
    passages: Sequence[PreliminaryPassage],
    decorrelation: Sequence[LocalDecorrelationEstimate],
    options: TemporalAssignmentOptions,
) -> list[PreliminaryPassage]:
    tau = {item.attractor_id: item.decorrelation_time_frames for item in decorrelation}
    updated: list[PreliminaryPassage] = []
    for passage in passages:
        short = False
        if passage.outcome is PassageOutcome.RETURN_EXCURSION:
            threshold = options.minimum_short_excursion_frames
            if tau.get(passage.source_attractor_id) is not None:
                threshold = max(threshold, int(math.ceil(options.short_excursion_tau_multiple * float(tau[passage.source_attractor_id]))))
            short = len(passage.outside_sample_indices) <= threshold
        updated.append(replace(passage, short_excursion=short, signature=""))
    recrossing_ids: set[int] = set()
    grouped: dict[tuple[int, int], list[int]] = {}
    for i, passage in enumerate(updated): grouped.setdefault((passage.atom_index, passage.segment_id), []).append(i)
    for indices in grouped.values():
        jumps = [i for i in indices if updated[i].outcome is PassageOutcome.JUMP]
        for first, second in zip(jumps, jumps[1:]):
            a = updated[first]; b = updated[second]
            if a.target_attractor_id == b.source_attractor_id and b.target_attractor_id == a.source_attractor_id:
                threshold = options.minimum_recrossing_frames
                local_tau = tau.get(b.source_attractor_id)
                if local_tau is not None: threshold = max(threshold, int(math.ceil(options.recrossing_tau_multiple * float(local_tau))))
                if b.target_core_sample_index is not None and a.target_core_sample_index is not None:
                    frame_delta = int(catalog.frame_indices[b.target_core_sample_index] - catalog.frame_indices[a.target_core_sample_index])
                    if frame_delta <= threshold: recrossing_ids.update({first, second})
    return [replace(item, recrossing=i in recrossing_ids, signature="") for i, item in enumerate(updated)]


def _attractor_diagnostics(
    attractors: DensityAttractorCatalog,
    residences: Sequence[PreliminaryResidenceInterval],
    decorrelation: Sequence[LocalDecorrelationEstimate],
    options: TemporalAssignmentOptions,
) -> list[AttractorTemporalDiagnostic]:
    result: list[AttractorTemporalDiagnostic] = []
    for attractor, decor in zip(attractors.attractors, decorrelation, strict=True):
        local = [r for r in residences if r.attractor_id == attractor.attractor_id]
        durations = np.asarray([r.represented_time for r in local], dtype=float)
        uncensored = sum(not r.left_censored and not r.right_censored for r in local)
        ratio = None; status = TemporalSupportStatus.INSUFFICIENT; diagnostic = None
        if local and decor.decorrelation_time_frames is not None:
            if decor.decorrelation_time is not None:
                scale = decor.decorrelation_time
                measure = durations
            else:
                scale = decor.decorrelation_time_frames
                measure = np.asarray([r.n_samples for r in local], dtype=float)
            ratio = float(np.max(measure) / max(scale, np.finfo(float).tiny))
            status = TemporalSupportStatus.PERSISTENT if ratio >= options.minimum_persistence_tau_multiples else TemporalSupportStatus.NONPERSISTENT
        elif not local:
            diagnostic = "no core-entered residence"
        else:
            diagnostic = "decorrelation timescale unresolved"
        result.append(AttractorTemporalDiagnostic(attractor.attractor_id, status, len(local), uncensored,
            float(np.sum(durations)), float(np.max(durations)) if len(durations) else 0.0,
            None if len(durations) == 0 else float(np.median(durations)), ratio, decor.signature, diagnostic))
    return result


def _passage_counts_for_stride(
    membership: ProvisionalMembershipTable,
    sequences: Sequence[tuple[int, int, np.ndarray]],
    stride: int,
) -> tuple[int, int, int]:
    jumps = returns = unresolved = 0
    for _, _, raw_sequence in sequences:
        sequence = raw_sequence[::stride]
        active: int | None = None; pending: int | None = None; gap = False
        for sample in sequence:
            core = int(membership.core_membership[sample]); basin = int(membership.basin_membership[sample])
            raw = RawMembershipClass(int(membership.raw_classification[sample]))
            if active is not None:
                if core == active or basin == active: continue
                pending = active; active = None
                gap = raw in {RawMembershipClass.UNSUPPORTED_UNKNOWN, RawMembershipClass.NUMERICALLY_UNRESOLVED, RawMembershipClass.CORE_OVERLAP}
            if pending is not None:
                gap |= raw in {RawMembershipClass.UNSUPPORTED_UNKNOWN, RawMembershipClass.NUMERICALLY_UNRESOLVED, RawMembershipClass.CORE_OVERLAP}
                if core >= 0:
                    if gap: unresolved += 1
                    elif core == pending: returns += 1
                    else: jumps += 1
                    active = core; pending = None; gap = False
            elif core >= 0:
                active = core
        if pending is not None: unresolved += 1
    return jumps, returns, unresolved


def _stride_diagnostic(
    membership: ProvisionalMembershipTable,
    sequences: Sequence[tuple[int, int, np.ndarray]],
    factors: tuple[int, ...],
) -> StrideSensitivityDiagnostic:
    counts = [_passage_counts_for_stride(membership, sequences, factor) for factor in factors]
    jumps = tuple(v[0] for v in counts); returns = tuple(v[1] for v in counts); unresolved = tuple(v[2] for v in counts)
    sensitive = any(count != counts[0] for count in counts[1:])
    return StrideSensitivityDiagnostic(factors, jumps, returns, unresolved, sensitive)


def _pattern(passages: Sequence[PreliminaryPassage], residences: Sequence[PreliminaryResidenceInterval], ensemble: bool) -> TemporalEvidencePattern:
    if ensemble: return TemporalEvidencePattern.ENSEMBLE_UNAVAILABLE
    jumps = sum(p.outcome is PassageOutcome.JUMP for p in passages)
    returns = sum(p.outcome is PassageOutcome.RETURN_EXCURSION for p in passages)
    short = sum(p.outcome is PassageOutcome.RETURN_EXCURSION and p.short_excursion for p in passages)
    unresolved = sum(p.outcome in {PassageOutcome.UNRESOLVED_GAP, PassageOutcome.RIGHT_CENSORED_EXIT} for p in passages)
    if not residences: return TemporalEvidencePattern.NO_CORE_ENTRY
    if jumps and returns: return TemporalEvidencePattern.MIXED_HOPPING_AND_EXCURSIONS
    if jumps == 1: return TemporalEvidencePattern.ONE_JUMP
    if jumps >= 2: return TemporalEvidencePattern.REPEATED_HOPPING
    if returns and short == returns: return TemporalEvidencePattern.SHORT_EXCURSION_ONLY
    if returns: return TemporalEvidencePattern.EXCURSIONS_ONLY
    if unresolved: return TemporalEvidencePattern.UNRESOLVED_GAPS_ONLY
    return TemporalEvidencePattern.SINGLE_STATE


def prepare_provisional_temporal_assignment(
    catalog: FrameworkAlignedIonSampleCatalog,
    density_estimate: PeriodicSpeciesDensityEstimate,
    attractor_catalog: DensityAttractorCatalog,
    *,
    discovery_catalog: FrameworkAlignedIonSampleCatalog | None = None,
    force_refinement: ForceRefinementCatalog | None = None,
    options: TemporalAssignmentOptions | None = None,
    resources: TemporalAssignmentResourcePolicy | None = None,
) -> ProvisionalTemporalAssignmentCatalog:
    """Prepare immutable raw memberships and preliminary temporal diagnostics.

    Transition, background, unsupported, and unresolved samples retain explicit
    non-site labels.  They are never filled by nearest-attractor assignment.
    """
    options = TemporalAssignmentOptions() if options is None else options
    resources = TemporalAssignmentResourcePolicy() if resources is None else resources
    partition_transfer = False
    if density_estimate.catalog_signature != catalog.signature:
        if discovery_catalog is None:
            raise TemporalAssignmentInputError(
                "Density estimate is bound to another sample catalog; an exact "
                "discovery_catalog is required for partition transfer."
            )
        if density_estimate.catalog_signature != discovery_catalog.signature:
            raise TemporalAssignmentInputError(
                "Density estimate is not bound to the supplied discovery catalog."
            )
        scalar_identity = (
            catalog.species_atomic_number == discovery_catalog.species_atomic_number
            and catalog.species_label == discovery_catalog.species_label
            and catalog.selected_atom_indices == discovery_catalog.selected_atom_indices
            and catalog.source_contract_signature == discovery_catalog.source_contract_signature
            and catalog.registration_signature == discovery_catalog.registration_signature
            and catalog.registration_policy_signature == discovery_catalog.registration_policy_signature
            and catalog.topology_assignment.signature == discovery_catalog.topology_assignment.signature
        )
        array_identity = all(
            np.array_equal(getattr(catalog, name), getattr(discovery_catalog, name))
            for name in (
                "frame_indices",
                "frame_ids",
                "atom_indices",
                "registered_positions",
                "registered_wrapped_fractional",
                "registered_image_shifts",
            )
        )
        if not scalar_identity or not array_identity:
            raise TemporalAssignmentInputError(
                "Temporal partition transfer requires exact source, registration, "
                "topology, atom, frame, and registered-coordinate identity."
            )
        partition_transfer = True
    elif discovery_catalog is not None and discovery_catalog.signature != catalog.signature:
        raise TemporalAssignmentInputError(
            "A discovery catalog is unnecessary and must equal the assignment catalog "
            "when no partition transfer is performed."
        )
    if attractor_catalog.density_estimate_signature != density_estimate.signature:
        raise TemporalAssignmentInputError("Attractor catalog is bound to another density estimate.")
    if force_refinement is not None:
        if force_refinement.sample_catalog_signature != catalog.signature or force_refinement.density_estimate_signature != density_estimate.signature or force_refinement.attractor_catalog_signature != attractor_catalog.signature:
            raise TemporalAssignmentInputError("Force refinement is not source-compatible with the E0b/E1/E2 inputs.")
    if catalog.n_samples > resources.max_samples: raise TemporalAssignmentResourceError("Sample count exceeds max_samples.")
    if catalog.n_selected_atoms > resources.max_atoms: raise TemporalAssignmentResourceError("Selected atom count exceeds max_atoms.")
    estimated_terms = catalog.n_samples * min(options.maximum_autocorrelation_lag, max(catalog.temporal_weighting.frame_indices.size - 1, 0))
    if estimated_terms > resources.max_autocorrelation_terms: raise TemporalAssignmentResourceError("Autocorrelation preflight exceeds max_autocorrelation_terms.")
    estimated_output = catalog.n_samples * (8 + 1 + 4 + 4 + 1)
    if estimated_output > resources.max_output_bytes: raise TemporalAssignmentResourceError("Membership output preflight exceeds max_output_bytes.")

    membership = _prepare_membership(catalog, attractor_catalog)
    if catalog.temporal_weighting.frame_semantics.value == "ensemble":
        sequences: list[tuple[int, int, np.ndarray]] = []
        visits: list[CoreVisitInterval] = []; residences: list[PreliminaryResidenceInterval] = []; passages: list[PreliminaryPassage] = []
    else:
        sequences = _valid_sequences(catalog, membership)
        visits, residences, passages = _segment_intervals(catalog, membership, sequences, resources)
    decorrelation = _decorrelation(catalog, density_estimate, attractor_catalog, residences, options)
    passages = _classify_passages(catalog, passages, decorrelation, options)
    diagnostics = _attractor_diagnostics(attractor_catalog, residences, decorrelation, options)
    stride = _stride_diagnostic(membership, sequences, options.stride_factors)
    if catalog.temporal_weighting.frame_semantics.value == "ensemble":
        support = TemporalSupportStatus.UNAVAILABLE
    elif stride.sensitive:
        support = TemporalSupportStatus.STRIDE_SENSITIVE
    elif any(v.support_status is TemporalSupportStatus.PERSISTENT for v in diagnostics):
        support = TemporalSupportStatus.PERSISTENT
    elif any(v.support_status is TemporalSupportStatus.NONPERSISTENT for v in diagnostics):
        support = TemporalSupportStatus.NONPERSISTENT
    else:
        support = TemporalSupportStatus.INSUFFICIENT
    pattern = _pattern(passages, residences, catalog.temporal_weighting.frame_semantics.value == "ensemble")
    metadata = {
        "stage": TEMPORAL_ASSIGNMENT_STAGE,
        "raw_labels_immutable": True,
        "nearest_center_fill_performed": False,
        "final_event_catalog_published": False,
        "partition_transfer_performed": partition_transfer,
        "partition_discovery_catalog_signature": (
            density_estimate.catalog_signature
            if partition_transfer
            else catalog.signature
        ),
        "partition_assignment_catalog_signature": catalog.signature,
        "partition_transfer_identity": (
            "exact_registered_coordinate_identity"
            if partition_transfer
            else "not_applicable"
        ),
        "core_set_background_references": (
            "Sarich, Noe, and Schuette 2010 DOI 10.1137/090764049",
            "Guarnera and Vanden-Eijnden 2016 DOI 10.1063/1.4954769",
        ),
        "autocorrelation_reference": "Geyer 1992 DOI 10.1214/ss/1177011137",
    }
    return ProvisionalTemporalAssignmentCatalog(
        catalog.signature, density_estimate.signature, attractor_catalog.signature,
        None if force_refinement is None else force_refinement.signature,
        options, resources, membership, tuple(visits), tuple(residences), tuple(passages),
        tuple(decorrelation), tuple(diagnostics), stride, support, pattern, metadata,
    )


__all__ = [
    "ATTRACTOR_TEMPORAL_DIAGNOSTIC_SCHEMA", "CORE_VISIT_INTERVAL_SCHEMA", "LOCAL_DECORRELATION_SCHEMA",
    "PRELIMINARY_PASSAGE_SCHEMA", "PRELIMINARY_RESIDENCE_SCHEMA", "PROVISIONAL_MEMBERSHIP_SCHEMA",
    "STRIDE_SENSITIVITY_SCHEMA", "TEMPORAL_ASSIGNMENT_CATALOG_SCHEMA", "TEMPORAL_ASSIGNMENT_OPTIONS_SCHEMA",
    "TEMPORAL_ASSIGNMENT_RESOURCES_SCHEMA", "TEMPORAL_ASSIGNMENT_STAGE", "AttractorTemporalDiagnostic",
    "CoreVisitInterval", "DecorrelationStatus", "LocalDecorrelationEstimate", "PassageOutcome",
    "PreliminaryPassage", "PreliminaryResidenceInterval", "ProvisionalMembershipTable",
    "ProvisionalTemporalAssignmentCatalog", "RawMembershipClass", "StrideSensitivityDiagnostic",
    "TemporalAssignmentError", "TemporalAssignmentInputError", "TemporalAssignmentOptions",
    "TemporalAssignmentResourceError", "TemporalAssignmentResourcePolicy", "TemporalAssignmentSerializationError",
    "TemporalEvidencePattern", "TemporalSupportStatus", "prepare_provisional_temporal_assignment",
]
