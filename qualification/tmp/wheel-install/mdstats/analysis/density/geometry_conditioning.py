"""Stage-11E5b optional geometry-conditioned site refinement.

The stage fits one frozen, framework-only affine predictor for a statistical
site center without changing the Stage-11E2/E5 state identity.  Discovery
assignments are never recomputed during fitting.  Candidate models are selected
on separate selection blocks and are retained only when untouched final-
validation evidence does not contradict the gain.

Weighted linear regression and held-out model comparison are standard
background.  The exact source binding, frozen-assignment protocol, translated
nested-region semantics, static/dynamic counterfactual membership, moving-
boundary diagnostics, and occupancy bounds are mdstats-specific constructions.
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

from .coordination_fingerprints import (
    CoordinationFingerprintCatalog,
    CoordinationFingerprintStatus,
    StateCoordinationFingerprint,
)
from .evidence_validation import EvidenceBlockPlan, ValidatedFrozenCatalog

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

GEOMETRY_CONDITIONING_STAGE = "11E5b"
GEOMETRY_CONDITIONING_OPTIONS_SCHEMA = "mdstats.geometry-conditioning-options.v1"
GEOMETRY_CONDITIONING_RESOURCES_SCHEMA = "mdstats.geometry-conditioning-resources.v1"
FRAMEWORK_PREDICTOR_TABLE_SCHEMA = "mdstats.framework-predictor-table.v1"
FROZEN_REGION_DEFINITION_SCHEMA = "mdstats.frozen-region-definition.v1"
GEOMETRY_CENTER_MODEL_SCHEMA = "mdstats.geometry-center-model.v1"
GEOMETRY_MODEL_SCORE_SCHEMA = "mdstats.geometry-model-score.v1"
BOUNDARY_CROSSING_DIAGNOSTIC_SCHEMA = "mdstats.boundary-crossing-diagnostic.v1"
STATE_GEOMETRY_REFINEMENT_SCHEMA = "mdstats.state-geometry-refinement.v1"
ASSIGNMENT_CONFLICT_RECORD_SCHEMA = "mdstats.assignment-conflict-record.v1"
STATE_OCCUPANCY_BOUNDS_SCHEMA = "mdstats.state-occupancy-bounds.v1"
GEOMETRY_CONDITIONED_CATALOG_SCHEMA = "mdstats.geometry-conditioned-catalog.v1"


class GeometryConditioningError(ValueError):
    """Base Stage-11E5b error."""


class GeometryConditioningInputError(GeometryConditioningError):
    """Raised when source contracts or sample arrays are inconsistent."""


class GeometryConditioningResourceError(GeometryConditioningError):
    """Raised transactionally before declared E5b work limits are exceeded."""


class GeometryConditioningSerializationError(GeometryConditioningError):
    """Raised when serialized E5b data are malformed or tampered with."""


class GeometryModelDecision(str, Enum):
    STATIC_RETAINED = "static_retained"
    DYNAMIC_RETAINED = "dynamic_retained"
    INSUFFICIENT_DISCOVERY_SUPPORT = "insufficient_discovery_support"
    INSUFFICIENT_SELECTION_SUPPORT = "insufficient_selection_support"
    INDEPENDENT_VALIDATION_UNAVAILABLE = "independent_validation_unavailable"
    FINAL_VALIDATION_CONTRADICTED = "final_validation_contradicted"
    RANK_DEFICIENT = "rank_deficient"
    ILL_CONDITIONED = "ill_conditioned"
    UNRESOLVED = "unresolved"


class CenterModelKind(str, Enum):
    STATIC = "static"
    AFFINE_FRAMEWORK = "affine_framework"


class RegionMembership(IntEnum):
    OUTSIDE = 0
    BASIN = 1
    CORE = 2


class AssignmentConflictStatus(str, Enum):
    UNIQUE_CORE = "unique_core"
    UNIQUE_BASIN = "unique_basin"
    MULTIPLE_CORE_OVERLAP = "multiple_core_overlap"
    MULTIPLE_BASIN_OVERLAP = "multiple_basin_overlap"
    STATIC_DYNAMIC_CONFLICT = "static_dynamic_conflict"
    OUTSIDE_SUPPORTED_REGIONS = "outside_supported_regions"
    ASSIGNMENT_UNRESOLVED = "assignment_unresolved"


class CrossingDriveStatus(str, Enum):
    NO_CROSSING = "no_crossing"
    ION_DRIVEN = "ion_driven"
    BOUNDARY_INDUCED = "boundary_induced"
    MIXED = "mixed"
    UNRESOLVED = "unresolved"


class BlockRole(str, Enum):
    DISCOVERY = "discovery"
    SELECTION = "selection"
    FINAL_VALIDATION = "final_validation"


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
        raise GeometryConditioningInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise GeometryConditioningInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise GeometryConditioningInputError(f"{name} must be finite and nonnegative.")
    return result


def _fraction(value: Any, name: str) -> float:
    result = _nonnegative(value, name)
    if result > 1.0:
        raise GeometryConditioningInputError(f"{name} must not exceed one.")
    return result


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or int(value) <= 0:
        raise GeometryConditioningInputError(f"{name} must be a positive integer.")
    return int(value)


def _readonly(
    value: Any,
    *,
    dtype: Any,
    ndim: int,
    name: str,
    shape: tuple[int, ...] | None = None,
) -> np.ndarray:
    arr = np.array(value, dtype=dtype, copy=True, order="C")
    if arr.ndim != ndim or (shape is not None and arr.shape != shape):
        raise GeometryConditioningInputError(f"{name} has invalid shape {arr.shape}.")
    if np.issubdtype(arr.dtype, np.floating) and np.any(~np.isfinite(arr)):
        raise GeometryConditioningInputError(f"{name} contains non-finite values.")
    arr.setflags(write=False)
    return arr


def _freeze(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, (float, np.floating)):
        result = float(value)
        if not np.isfinite(result):
            raise GeometryConditioningInputError("Metadata contains a non-finite float.")
        return result
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, Mapping):
        return MappingProxyType({str(k): _freeze(v) for k, v in sorted(value.items(), key=lambda p: str(p[0]))})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    raise GeometryConditioningInputError(f"Unsupported metadata value {type(value).__name__}.")


def _json_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_value(v) for v in value]
    if isinstance(value, np.generic):
        return _json_value(value.item())
    return value


def _weighted_rms(residual: np.ndarray, weights: np.ndarray) -> float:
    return float(np.sqrt(np.sum(weights * np.sum(residual * residual, axis=1)) / np.sum(weights)))


def _weighted_covariance(residual: np.ndarray, weights: np.ndarray) -> np.ndarray:
    total = float(np.sum(weights))
    mean = np.sum(weights[:, None] * residual, axis=0) / total
    centered = residual - mean
    return np.einsum("n,ni,nj->ij", weights, centered, centered) / total


def _membership(points: np.ndarray, centers: np.ndarray, core_radius: float, basin_radius: float) -> np.ndarray:
    distance = np.linalg.norm(points - centers, axis=1)
    result = np.full(points.shape[0], int(RegionMembership.OUTSIDE), dtype=np.int64)
    result[distance <= basin_radius] = int(RegionMembership.BASIN)
    result[distance <= core_radius] = int(RegionMembership.CORE)
    return result


@dataclass(frozen=True, slots=True)
class GeometryConditioningOptions:
    minimum_discovery_samples: int = 8
    minimum_selection_samples: int = 6
    minimum_validation_samples: int = 6
    minimum_relative_selection_improvement: float = 0.10
    maximum_relative_validation_degradation: float = 0.05
    maximum_condition_number: float = 1.0e8
    regularization: float = 0.0
    boundary_induced_ratio: float = 0.5
    crossing_tolerance: float = 1.0e-10
    maximum_core_overlap_fraction: float = 0.10
    maximum_basin_overlap_fraction: float = 0.25
    maximum_unresolved_fraction: float = 0.10
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        counts = {name: _positive_int(getattr(self, name), name) for name in (
            "minimum_discovery_samples", "minimum_selection_samples", "minimum_validation_samples")}
        values = {
            "minimum_relative_selection_improvement": _fraction(self.minimum_relative_selection_improvement, "minimum_relative_selection_improvement"),
            "maximum_relative_validation_degradation": _fraction(self.maximum_relative_validation_degradation, "maximum_relative_validation_degradation"),
            "maximum_condition_number": _positive(self.maximum_condition_number, "maximum_condition_number"),
            "regularization": _nonnegative(self.regularization, "regularization"),
            "boundary_induced_ratio": _nonnegative(self.boundary_induced_ratio, "boundary_induced_ratio"),
            "crossing_tolerance": _nonnegative(self.crossing_tolerance, "crossing_tolerance"),
            "maximum_core_overlap_fraction": _fraction(self.maximum_core_overlap_fraction, "maximum_core_overlap_fraction"),
            "maximum_basin_overlap_fraction": _fraction(self.maximum_basin_overlap_fraction, "maximum_basin_overlap_fraction"),
            "maximum_unresolved_fraction": _fraction(self.maximum_unresolved_fraction, "maximum_unresolved_fraction"),
        }
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": GEOMETRY_CONDITIONING_OPTIONS_SCHEMA, **counts, **values, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Geometry-conditioning options signature is inconsistent.")
        for name, value in {**counts, **values}.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        names = (
            "minimum_discovery_samples", "minimum_selection_samples", "minimum_validation_samples",
            "minimum_relative_selection_improvement", "maximum_relative_validation_degradation",
            "maximum_condition_number", "regularization", "boundary_induced_ratio", "crossing_tolerance",
            "maximum_core_overlap_fraction", "maximum_basin_overlap_fraction", "maximum_unresolved_fraction",
        )
        return {"schema": GEOMETRY_CONDITIONING_OPTIONS_SCHEMA, **{n: getattr(self, n) for n in names},
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeometryConditioningOptions":
        if payload.get("schema") != GEOMETRY_CONDITIONING_OPTIONS_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported geometry-conditioning options schema.")
        names = (
            "minimum_discovery_samples", "minimum_selection_samples", "minimum_validation_samples",
            "minimum_relative_selection_improvement", "maximum_relative_validation_degradation",
            "maximum_condition_number", "regularization", "boundary_induced_ratio", "crossing_tolerance",
            "maximum_core_overlap_fraction", "maximum_basin_overlap_fraction", "maximum_unresolved_fraction",
        )
        return cls(**{n: payload[n] for n in names}, metadata=payload.get("metadata", {}), signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class GeometryConditioningResourcePolicy:
    max_states: int = 100_000
    max_samples: int = 100_000_000
    max_predictor_values: int = 100_000_000
    max_crossings: int = 100_000_000
    max_conflict_records: int = 100_000_000
    max_serialized_records: int = 200_000_000
    signature: str = ""

    def __post_init__(self) -> None:
        values = {name: _positive_int(getattr(self, name), name) for name in (
            "max_states", "max_samples", "max_predictor_values", "max_crossings",
            "max_conflict_records", "max_serialized_records")}
        expected = _digest({"schema": GEOMETRY_CONDITIONING_RESOURCES_SCHEMA, **values})
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Geometry-conditioning resources signature is inconsistent.")
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        names = ("max_states", "max_samples", "max_predictor_values", "max_crossings", "max_conflict_records", "max_serialized_records")
        return {"schema": GEOMETRY_CONDITIONING_RESOURCES_SCHEMA, **{n: getattr(self, n) for n in names}, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeometryConditioningResourcePolicy":
        if payload.get("schema") != GEOMETRY_CONDITIONING_RESOURCES_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported geometry-conditioning resources schema.")
        names = ("max_states", "max_samples", "max_predictor_values", "max_crossings", "max_conflict_records", "max_serialized_records")
        return cls(**{n: payload[n] for n in names}, signature=str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class FrameworkPredictorTable:
    state_id: int
    candidate_index: int
    persistent_identity: str
    sample_indices: IntArray
    frame_indices: IntArray
    segment_ids: IntArray
    predictor_names: tuple[str, ...]
    predictor_values: FloatArray
    registered_structural_view_digest: str
    framework_only: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        sid, candidate = int(self.state_id), int(self.candidate_index)
        if min(sid, candidate) < 0:
            raise GeometryConditioningInputError("State and candidate indices must be nonnegative.")
        identity = str(self.persistent_identity)
        if not identity:
            raise GeometryConditioningInputError("persistent_identity must be nonempty.")
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        n = samples.size
        frames = _readonly(self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices", shape=(n,))
        segments = _readonly(self.segment_ids, dtype=np.int64, ndim=1, name="segment_ids", shape=(n,))
        names = tuple(str(v) for v in self.predictor_names)
        if not names or len(set(names)) != len(names):
            raise GeometryConditioningInputError("predictor_names must be nonempty and unique.")
        values = _readonly(self.predictor_values, dtype=np.float64, ndim=2, name="predictor_values", shape=(n, len(names)))
        if not self.framework_only:
            raise GeometryConditioningInputError("Stage 11E5b predictors must be framework-only.")
        digest = _sha(self.registered_structural_view_digest, "registered_structural_view_digest")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": FRAMEWORK_PREDICTOR_TABLE_SCHEMA, "state_id": sid, "candidate_index": candidate,
                   "persistent_identity": identity, "sample_indices": _array_digest(samples),
                   "frame_indices": _array_digest(frames), "segment_ids": _array_digest(segments),
                   "predictor_names": list(names), "predictor_values": _array_digest(values),
                   "registered_structural_view_digest": digest, "framework_only": True,
                   "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Framework-predictor-table signature is inconsistent.")
        for name, value in (("state_id", sid), ("candidate_index", candidate), ("persistent_identity", identity),
                            ("sample_indices", samples), ("frame_indices", frames), ("segment_ids", segments),
                            ("predictor_names", names), ("predictor_values", values),
                            ("registered_structural_view_digest", digest), ("framework_only", True),
                            ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FRAMEWORK_PREDICTOR_TABLE_SCHEMA, "state_id": self.state_id,
                "candidate_index": self.candidate_index, "persistent_identity": self.persistent_identity,
                "sample_indices": self.sample_indices.tolist(), "frame_indices": self.frame_indices.tolist(),
                "segment_ids": self.segment_ids.tolist(), "predictor_names": list(self.predictor_names),
                "predictor_values": self.predictor_values.tolist(),
                "registered_structural_view_digest": self.registered_structural_view_digest,
                "framework_only": self.framework_only, "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkPredictorTable":
        if payload.get("schema") != FRAMEWORK_PREDICTOR_TABLE_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported framework-predictor-table schema.")
        return cls(int(payload["state_id"]), int(payload["candidate_index"]), str(payload["persistent_identity"]),
                   np.asarray(payload["sample_indices"], dtype=np.int64), np.asarray(payload["frame_indices"], dtype=np.int64),
                   np.asarray(payload["segment_ids"], dtype=np.int64), tuple(payload["predictor_names"]),
                   np.asarray(payload["predictor_values"], dtype=float), str(payload["registered_structural_view_digest"]),
                   bool(payload.get("framework_only", True)), dict(payload.get("metadata", {})), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class FrozenRegionDefinition:
    state_id: int
    candidate_index: int
    persistent_identity: str
    center: tuple[float, float, float]
    core_radius: float
    basin_radius: float
    validated_frozen_catalog_signature: str
    signature: str = ""

    def __post_init__(self) -> None:
        sid, candidate = int(self.state_id), int(self.candidate_index)
        if min(sid, candidate) < 0:
            raise GeometryConditioningInputError("State and candidate indices must be nonnegative.")
        identity = str(self.persistent_identity)
        center = tuple(float(v) for v in self.center)
        if len(center) != 3 or not np.all(np.isfinite(center)):
            raise GeometryConditioningInputError("center must contain three finite coordinates.")
        core = _positive(self.core_radius, "core_radius")
        basin = _positive(self.basin_radius, "basin_radius")
        if core >= basin:
            raise GeometryConditioningInputError("core_radius must be strictly smaller than basin_radius.")
        source = _sha(self.validated_frozen_catalog_signature, "validated_frozen_catalog_signature")
        payload = {"schema": FROZEN_REGION_DEFINITION_SCHEMA, "state_id": sid, "candidate_index": candidate,
                   "persistent_identity": identity, "center": list(center), "core_radius": core,
                   "basin_radius": basin, "validated_frozen_catalog_signature": source}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Frozen-region-definition signature is inconsistent.")
        for name, value in (("state_id", sid), ("candidate_index", candidate), ("persistent_identity", identity),
                            ("center", center), ("core_radius", core), ("basin_radius", basin),
                            ("validated_frozen_catalog_signature", source), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": FROZEN_REGION_DEFINITION_SCHEMA, "state_id": self.state_id,
                "candidate_index": self.candidate_index, "persistent_identity": self.persistent_identity,
                "center": list(self.center), "core_radius": self.core_radius, "basin_radius": self.basin_radius,
                "validated_frozen_catalog_signature": self.validated_frozen_catalog_signature, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrozenRegionDefinition":
        if payload.get("schema") != FROZEN_REGION_DEFINITION_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported frozen-region-definition schema.")
        return cls(int(payload["state_id"]), int(payload["candidate_index"]), str(payload["persistent_identity"]),
                   tuple(payload["center"]), float(payload["core_radius"]), float(payload["basin_radius"]),
                   str(payload["validated_frozen_catalog_signature"]), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class GeometryCenterModel:
    kind: CenterModelKind
    predictor_names: tuple[str, ...]
    predictor_mean: FloatArray
    intercept: FloatArray
    coefficients: FloatArray
    fit_rank: int
    parameter_count: int
    condition_number: float
    sample_count: int
    weighted_residual_rms: float
    residual_covariance: FloatArray
    signature: str = ""

    def __post_init__(self) -> None:
        kind = CenterModelKind(self.kind)
        names = tuple(str(v) for v in self.predictor_names)
        p = len(names)
        mean = _readonly(self.predictor_mean, dtype=np.float64, ndim=1, name="predictor_mean", shape=(p,))
        intercept = _readonly(self.intercept, dtype=np.float64, ndim=1, name="intercept", shape=(3,))
        coefficients = _readonly(self.coefficients, dtype=np.float64, ndim=2, name="coefficients", shape=(p, 3))
        rank, parameters, count = int(self.fit_rank), int(self.parameter_count), int(self.sample_count)
        if min(rank, parameters, count) < 0 or rank > parameters or parameters != p + 1:
            raise GeometryConditioningInputError("Invalid center-model rank or sample counters.")
        condition = float(self.condition_number)
        if not np.isfinite(condition) or condition < 0:
            raise GeometryConditioningInputError("condition_number must be finite and nonnegative.")
        rms = _nonnegative(self.weighted_residual_rms, "weighted_residual_rms")
        covariance = _readonly(self.residual_covariance, dtype=np.float64, ndim=2, name="residual_covariance", shape=(3, 3))
        payload = {"schema": GEOMETRY_CENTER_MODEL_SCHEMA, "kind": kind.value, "predictor_names": list(names),
                   "predictor_mean": _array_digest(mean), "intercept": _array_digest(intercept),
                   "coefficients": _array_digest(coefficients), "fit_rank": rank, "parameter_count": parameters,
                   "condition_number": condition, "sample_count": count, "weighted_residual_rms": rms,
                   "residual_covariance": _array_digest(covariance)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Geometry-center-model signature is inconsistent.")
        for name, value in (("kind", kind), ("predictor_names", names), ("predictor_mean", mean),
                            ("intercept", intercept), ("coefficients", coefficients), ("fit_rank", rank),
                            ("parameter_count", parameters), ("condition_number", condition), ("sample_count", count),
                            ("weighted_residual_rms", rms), ("residual_covariance", covariance), ("signature", expected)):
            object.__setattr__(self, name, value)

    def predict(self, values: Sequence[Sequence[float]]) -> np.ndarray:
        x = np.asarray(values, dtype=float)
        if x.ndim != 2 or x.shape[1] != len(self.predictor_names):
            raise GeometryConditioningInputError("Predictor values do not match the center model.")
        return self.intercept[None, :] + (x - self.predictor_mean[None, :]) @ self.coefficients

    def to_dict(self) -> dict[str, Any]:
        return {"schema": GEOMETRY_CENTER_MODEL_SCHEMA, "kind": self.kind.value,
                "predictor_names": list(self.predictor_names), "predictor_mean": self.predictor_mean.tolist(),
                "intercept": self.intercept.tolist(), "coefficients": self.coefficients.tolist(),
                "fit_rank": self.fit_rank, "parameter_count": self.parameter_count,
                "condition_number": self.condition_number, "sample_count": self.sample_count,
                "weighted_residual_rms": self.weighted_residual_rms,
                "residual_covariance": self.residual_covariance.tolist(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeometryCenterModel":
        if payload.get("schema") != GEOMETRY_CENTER_MODEL_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported geometry-center-model schema.")
        return cls(CenterModelKind(payload["kind"]), tuple(payload["predictor_names"]),
                   np.asarray(payload["predictor_mean"], dtype=float), np.asarray(payload["intercept"], dtype=float),
                   np.asarray(payload["coefficients"], dtype=float), int(payload["fit_rank"]),
                   int(payload["parameter_count"]), float(payload["condition_number"]), int(payload["sample_count"]),
                   float(payload["weighted_residual_rms"]), np.asarray(payload["residual_covariance"], dtype=float),
                   str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class GeometryModelScore:
    role: BlockRole
    sample_count: int
    static_rms: float | None
    dynamic_rms: float | None
    relative_improvement: float | None
    signature: str = ""

    def __post_init__(self) -> None:
        role = BlockRole(self.role)
        count = int(self.sample_count)
        if count < 0:
            raise GeometryConditioningInputError("sample_count must be nonnegative.")
        values: dict[str, float | None] = {}
        for name in ("static_rms", "dynamic_rms"):
            value = getattr(self, name)
            values[name] = None if value is None else _nonnegative(value, name)
        improvement = self.relative_improvement
        if improvement is not None:
            improvement = float(improvement)
            if not np.isfinite(improvement):
                raise GeometryConditioningInputError("relative_improvement must be finite when present.")
        if (values["static_rms"] is None) != (values["dynamic_rms"] is None):
            raise GeometryConditioningInputError("Static and dynamic RMS values must be jointly present.")
        payload = {"schema": GEOMETRY_MODEL_SCORE_SCHEMA, "role": role.value, "sample_count": count,
                   **values, "relative_improvement": improvement}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Geometry-model-score signature is inconsistent.")
        for name, value in (("role", role), ("sample_count", count), ("static_rms", values["static_rms"]),
                            ("dynamic_rms", values["dynamic_rms"]), ("relative_improvement", improvement),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": GEOMETRY_MODEL_SCORE_SCHEMA, "role": self.role.value, "sample_count": self.sample_count,
                "static_rms": self.static_rms, "dynamic_rms": self.dynamic_rms,
                "relative_improvement": self.relative_improvement, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeometryModelScore":
        if payload.get("schema") != GEOMETRY_MODEL_SCORE_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported geometry-model-score schema.")
        return cls(BlockRole(payload["role"]), int(payload["sample_count"]), payload.get("static_rms"),
                   payload.get("dynamic_rms"), payload.get("relative_improvement"), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class BoundaryCrossingDiagnostic:
    previous_sample_index: int
    sample_index: int
    static_before: RegionMembership
    static_after: RegionMembership
    dynamic_before: RegionMembership
    dynamic_after: RegionMembership
    ion_displacement_norm: float
    center_displacement_norm: float
    comoving_displacement_norm: float
    boundary_displacement_norm: float
    drive_status: CrossingDriveStatus
    boundary_induced_crossing: bool
    signature: str = ""

    def __post_init__(self) -> None:
        previous, sample = int(self.previous_sample_index), int(self.sample_index)
        if min(previous, sample) < 0 or previous == sample:
            raise GeometryConditioningInputError("Crossing sample indices must be distinct and nonnegative.")
        memberships = tuple(RegionMembership(v) for v in (self.static_before, self.static_after, self.dynamic_before, self.dynamic_after))
        values = {name: _nonnegative(getattr(self, name), name) for name in (
            "ion_displacement_norm", "center_displacement_norm", "comoving_displacement_norm", "boundary_displacement_norm")}
        drive = CrossingDriveStatus(self.drive_status)
        boundary = bool(self.boundary_induced_crossing)
        if boundary != (drive is CrossingDriveStatus.BOUNDARY_INDUCED):
            raise GeometryConditioningInputError("boundary_induced_crossing must agree with drive_status.")
        payload = {"schema": BOUNDARY_CROSSING_DIAGNOSTIC_SCHEMA, "previous_sample_index": previous,
                   "sample_index": sample, "memberships": [int(v) for v in memberships], **values,
                   "drive_status": drive.value, "boundary_induced_crossing": boundary}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Boundary-crossing signature is inconsistent.")
        for name, value in (("previous_sample_index", previous), ("sample_index", sample),
                            ("static_before", memberships[0]), ("static_after", memberships[1]),
                            ("dynamic_before", memberships[2]), ("dynamic_after", memberships[3]),
                            *(values.items()), ("drive_status", drive), ("boundary_induced_crossing", boundary),
                            ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": BOUNDARY_CROSSING_DIAGNOSTIC_SCHEMA,
                "previous_sample_index": self.previous_sample_index, "sample_index": self.sample_index,
                "static_before": int(self.static_before), "static_after": int(self.static_after),
                "dynamic_before": int(self.dynamic_before), "dynamic_after": int(self.dynamic_after),
                "ion_displacement_norm": self.ion_displacement_norm,
                "center_displacement_norm": self.center_displacement_norm,
                "comoving_displacement_norm": self.comoving_displacement_norm,
                "boundary_displacement_norm": self.boundary_displacement_norm,
                "drive_status": self.drive_status.value,
                "boundary_induced_crossing": self.boundary_induced_crossing, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "BoundaryCrossingDiagnostic":
        if payload.get("schema") != BOUNDARY_CROSSING_DIAGNOSTIC_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported boundary-crossing schema.")
        return cls(int(payload["previous_sample_index"]), int(payload["sample_index"]),
                   RegionMembership(int(payload["static_before"])), RegionMembership(int(payload["static_after"])),
                   RegionMembership(int(payload["dynamic_before"])), RegionMembership(int(payload["dynamic_after"])),
                   float(payload["ion_displacement_norm"]), float(payload["center_displacement_norm"]),
                   float(payload["comoving_displacement_norm"]), float(payload["boundary_displacement_norm"]),
                   CrossingDriveStatus(payload["drive_status"]), bool(payload["boundary_induced_crossing"]),
                   str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StateGeometryConditionedRefinement:
    state_id: int
    candidate_index: int
    persistent_identity: str
    fingerprint_signature: str
    predictor_table_signature: str
    frozen_region_signature: str
    decision: GeometryModelDecision
    selected_model_kind: CenterModelKind
    sample_indices: IntArray
    frame_indices: IntArray
    ion_atom_indices: IntArray
    segment_ids: IntArray
    represented_time_weights: FloatArray
    local_coordinates: FloatArray
    static_model: GeometryCenterModel
    dynamic_model: GeometryCenterModel | None
    block_scores: tuple[GeometryModelScore, ...]
    candidate_dynamic_centers: FloatArray
    selected_centers: FloatArray
    static_membership: IntArray
    dynamic_membership: IntArray
    selected_membership: IntArray
    comoving_displacements: FloatArray
    center_displacements: FloatArray
    boundary_displacements: FloatArray
    crossings: tuple[BoundaryCrossingDiagnostic, ...]
    static_residual_covariance: FloatArray
    dynamic_residual_covariance: FloatArray | None
    diagnostics: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        sid, candidate = int(self.state_id), int(self.candidate_index)
        if min(sid, candidate) < 0:
            raise GeometryConditioningInputError("State and candidate indices must be nonnegative.")
        identity = str(self.persistent_identity)
        if not identity:
            raise GeometryConditioningInputError("persistent_identity must be nonempty.")
        source_digests = {name: _sha(getattr(self, name), name) for name in (
            "fingerprint_signature", "predictor_table_signature", "frozen_region_signature")}
        decision = GeometryModelDecision(self.decision)
        selected_kind = CenterModelKind(self.selected_model_kind)
        samples = _readonly(self.sample_indices, dtype=np.int64, ndim=1, name="sample_indices")
        n = samples.size
        frames = _readonly(self.frame_indices, dtype=np.int64, ndim=1, name="frame_indices", shape=(n,))
        ions = _readonly(self.ion_atom_indices, dtype=np.int64, ndim=1, name="ion_atom_indices", shape=(n,))
        segments = _readonly(self.segment_ids, dtype=np.int64, ndim=1, name="segment_ids", shape=(n,))
        weights = _readonly(self.represented_time_weights, dtype=np.float64, ndim=1, name="represented_time_weights", shape=(n,))
        if np.any(weights <= 0):
            raise GeometryConditioningInputError("represented_time_weights must be positive.")
        local = _readonly(self.local_coordinates, dtype=np.float64, ndim=2, name="local_coordinates", shape=(n, 3))
        candidate_centers = _readonly(self.candidate_dynamic_centers, dtype=np.float64, ndim=2, name="candidate_dynamic_centers", shape=(n, 3))
        selected_centers = _readonly(self.selected_centers, dtype=np.float64, ndim=2, name="selected_centers", shape=(n, 3))
        static_membership = _readonly(self.static_membership, dtype=np.int64, ndim=1, name="static_membership", shape=(n,))
        dynamic_membership = _readonly(self.dynamic_membership, dtype=np.int64, ndim=1, name="dynamic_membership", shape=(n,))
        selected_membership = _readonly(self.selected_membership, dtype=np.int64, ndim=1, name="selected_membership", shape=(n,))
        for arr, name in ((static_membership, "static_membership"), (dynamic_membership, "dynamic_membership"), (selected_membership, "selected_membership")):
            if np.any(~np.isin(arr, [int(v) for v in RegionMembership])):
                raise GeometryConditioningInputError(f"{name} contains invalid membership values.")
        comoving = _readonly(self.comoving_displacements, dtype=np.float64, ndim=2, name="comoving_displacements", shape=(n, 3))
        center_disp = _readonly(self.center_displacements, dtype=np.float64, ndim=2, name="center_displacements", shape=(n, 3))
        boundary_disp = _readonly(self.boundary_displacements, dtype=np.float64, ndim=1, name="boundary_displacements", shape=(n,))
        static_cov = _readonly(self.static_residual_covariance, dtype=np.float64, ndim=2, name="static_residual_covariance", shape=(3, 3))
        dynamic_cov = None if self.dynamic_residual_covariance is None else _readonly(
            self.dynamic_residual_covariance, dtype=np.float64, ndim=2, name="dynamic_residual_covariance", shape=(3, 3))
        if selected_kind is CenterModelKind.AFFINE_FRAMEWORK and self.dynamic_model is None:
            raise GeometryConditioningInputError("Dynamic selection requires a dynamic model.")
        if decision is GeometryModelDecision.DYNAMIC_RETAINED and selected_kind is not CenterModelKind.AFFINE_FRAMEWORK:
            raise GeometryConditioningInputError("Dynamic decision must select the affine framework model.")
        if decision is not GeometryModelDecision.DYNAMIC_RETAINED and selected_kind is not CenterModelKind.STATIC:
            raise GeometryConditioningInputError("Non-retained dynamic models must leave the static model selected.")
        scores = tuple(self.block_scores)
        if tuple(v.role for v in scores) != tuple(BlockRole):
            raise GeometryConditioningInputError("block_scores must contain discovery, selection, and final-validation records in order.")
        crossings = tuple(self.crossings)
        diagnostics = tuple(str(v) for v in self.diagnostics)
        payload = {"schema": STATE_GEOMETRY_REFINEMENT_SCHEMA, "state_id": sid, "candidate_index": candidate,
                   "persistent_identity": identity, **source_digests, "decision": decision.value,
                   "selected_model_kind": selected_kind.value, "sample_indices": _array_digest(samples),
                   "frame_indices": _array_digest(frames), "ion_atom_indices": _array_digest(ions),
                   "segment_ids": _array_digest(segments), "weights": _array_digest(weights),
                   "local_coordinates": _array_digest(local), "static_model": self.static_model.signature,
                   "dynamic_model": None if self.dynamic_model is None else self.dynamic_model.signature,
                   "block_scores": [v.signature for v in scores], "candidate_dynamic_centers": _array_digest(candidate_centers),
                   "selected_centers": _array_digest(selected_centers), "static_membership": _array_digest(static_membership),
                   "dynamic_membership": _array_digest(dynamic_membership), "selected_membership": _array_digest(selected_membership),
                   "comoving_displacements": _array_digest(comoving), "center_displacements": _array_digest(center_disp),
                   "boundary_displacements": _array_digest(boundary_disp), "crossings": [v.signature for v in crossings],
                   "static_residual_covariance": _array_digest(static_cov),
                   "dynamic_residual_covariance": None if dynamic_cov is None else _array_digest(dynamic_cov),
                   "diagnostics": list(diagnostics)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("State-geometry-refinement signature is inconsistent.")
        for name, value in (("state_id", sid), ("candidate_index", candidate), ("persistent_identity", identity),
                            *(source_digests.items()), ("decision", decision), ("selected_model_kind", selected_kind),
                            ("sample_indices", samples), ("frame_indices", frames), ("ion_atom_indices", ions),
                            ("segment_ids", segments), ("represented_time_weights", weights), ("local_coordinates", local),
                            ("block_scores", scores), ("candidate_dynamic_centers", candidate_centers),
                            ("selected_centers", selected_centers), ("static_membership", static_membership),
                            ("dynamic_membership", dynamic_membership), ("selected_membership", selected_membership),
                            ("comoving_displacements", comoving), ("center_displacements", center_disp),
                            ("boundary_displacements", boundary_disp), ("crossings", crossings),
                            ("static_residual_covariance", static_cov), ("dynamic_residual_covariance", dynamic_cov),
                            ("diagnostics", diagnostics), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STATE_GEOMETRY_REFINEMENT_SCHEMA, "state_id": self.state_id,
                "candidate_index": self.candidate_index, "persistent_identity": self.persistent_identity,
                "fingerprint_signature": self.fingerprint_signature,
                "predictor_table_signature": self.predictor_table_signature,
                "frozen_region_signature": self.frozen_region_signature,
                "decision": self.decision.value, "selected_model_kind": self.selected_model_kind.value,
                "sample_indices": self.sample_indices.tolist(), "frame_indices": self.frame_indices.tolist(),
                "ion_atom_indices": self.ion_atom_indices.tolist(), "segment_ids": self.segment_ids.tolist(),
                "represented_time_weights": self.represented_time_weights.tolist(),
                "local_coordinates": self.local_coordinates.tolist(), "static_model": self.static_model.to_dict(),
                "dynamic_model": None if self.dynamic_model is None else self.dynamic_model.to_dict(),
                "block_scores": [v.to_dict() for v in self.block_scores],
                "candidate_dynamic_centers": self.candidate_dynamic_centers.tolist(),
                "selected_centers": self.selected_centers.tolist(),
                "static_membership": self.static_membership.tolist(),
                "dynamic_membership": self.dynamic_membership.tolist(),
                "selected_membership": self.selected_membership.tolist(),
                "comoving_displacements": self.comoving_displacements.tolist(),
                "center_displacements": self.center_displacements.tolist(),
                "boundary_displacements": self.boundary_displacements.tolist(),
                "crossings": [v.to_dict() for v in self.crossings],
                "static_residual_covariance": self.static_residual_covariance.tolist(),
                "dynamic_residual_covariance": None if self.dynamic_residual_covariance is None else self.dynamic_residual_covariance.tolist(),
                "diagnostics": list(self.diagnostics), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateGeometryConditionedRefinement":
        if payload.get("schema") != STATE_GEOMETRY_REFINEMENT_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported state-geometry-refinement schema.")
        return cls(int(payload["state_id"]), int(payload["candidate_index"]), str(payload["persistent_identity"]),
                   str(payload["fingerprint_signature"]), str(payload["predictor_table_signature"]),
                   str(payload["frozen_region_signature"]), GeometryModelDecision(payload["decision"]),
                   CenterModelKind(payload["selected_model_kind"]), np.asarray(payload["sample_indices"], dtype=np.int64),
                   np.asarray(payload["frame_indices"], dtype=np.int64), np.asarray(payload["ion_atom_indices"], dtype=np.int64),
                   np.asarray(payload["segment_ids"], dtype=np.int64), np.asarray(payload["represented_time_weights"], dtype=float),
                   np.asarray(payload["local_coordinates"], dtype=float), GeometryCenterModel.from_dict(payload["static_model"]),
                   None if payload.get("dynamic_model") is None else GeometryCenterModel.from_dict(payload["dynamic_model"]),
                   tuple(GeometryModelScore.from_dict(v) for v in payload["block_scores"]),
                   np.asarray(payload["candidate_dynamic_centers"], dtype=float), np.asarray(payload["selected_centers"], dtype=float),
                   np.asarray(payload["static_membership"], dtype=np.int64), np.asarray(payload["dynamic_membership"], dtype=np.int64),
                   np.asarray(payload["selected_membership"], dtype=np.int64), np.asarray(payload["comoving_displacements"], dtype=float),
                   np.asarray(payload["center_displacements"], dtype=float), np.asarray(payload["boundary_displacements"], dtype=float),
                   tuple(BoundaryCrossingDiagnostic.from_dict(v) for v in payload["crossings"]),
                   np.asarray(payload["static_residual_covariance"], dtype=float),
                   None if payload.get("dynamic_residual_covariance") is None else np.asarray(payload["dynamic_residual_covariance"], dtype=float),
                   tuple(payload.get("diagnostics", ())), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class AssignmentConflictRecord:
    sample_index: int
    static_core_state_ids: tuple[int, ...]
    static_basin_state_ids: tuple[int, ...]
    dynamic_core_state_ids: tuple[int, ...]
    dynamic_basin_state_ids: tuple[int, ...]
    selected_state_ids: tuple[int, ...]
    status: AssignmentConflictStatus
    signature: str = ""

    def __post_init__(self) -> None:
        sample = int(self.sample_index)
        if sample < 0:
            raise GeometryConditioningInputError("sample_index must be nonnegative.")
        groups = {}
        for name in ("static_core_state_ids", "static_basin_state_ids", "dynamic_core_state_ids", "dynamic_basin_state_ids", "selected_state_ids"):
            values = tuple(sorted({int(v) for v in getattr(self, name)}))
            if values and values[0] < 0:
                raise GeometryConditioningInputError(f"{name} must contain nonnegative state ids.")
            groups[name] = values
        status = AssignmentConflictStatus(self.status)
        payload = {"schema": ASSIGNMENT_CONFLICT_RECORD_SCHEMA, "sample_index": sample,
                   **{k: list(v) for k, v in groups.items()}, "status": status.value}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Assignment-conflict signature is inconsistent.")
        object.__setattr__(self, "sample_index", sample)
        for name, value in groups.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": ASSIGNMENT_CONFLICT_RECORD_SCHEMA, "sample_index": self.sample_index,
                "static_core_state_ids": list(self.static_core_state_ids),
                "static_basin_state_ids": list(self.static_basin_state_ids),
                "dynamic_core_state_ids": list(self.dynamic_core_state_ids),
                "dynamic_basin_state_ids": list(self.dynamic_basin_state_ids),
                "selected_state_ids": list(self.selected_state_ids), "status": self.status.value, "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AssignmentConflictRecord":
        if payload.get("schema") != ASSIGNMENT_CONFLICT_RECORD_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported assignment-conflict schema.")
        return cls(int(payload["sample_index"]), tuple(payload["static_core_state_ids"]),
                   tuple(payload["static_basin_state_ids"]), tuple(payload["dynamic_core_state_ids"]),
                   tuple(payload["dynamic_basin_state_ids"]), tuple(payload["selected_state_ids"]),
                   AssignmentConflictStatus(payload["status"]), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class StateOccupancyBounds:
    state_id: int
    lower_weight: float
    upper_weight: float
    total_weight: float
    lower_fraction: float
    upper_fraction: float
    core_overlap_fraction: float
    basin_overlap_fraction: float
    unresolved_fraction: float
    signature: str = ""

    def __post_init__(self) -> None:
        state = int(self.state_id)
        if state < 0:
            raise GeometryConditioningInputError("state_id must be nonnegative.")
        lower = _nonnegative(self.lower_weight, "lower_weight")
        upper = _nonnegative(self.upper_weight, "upper_weight")
        total = _nonnegative(self.total_weight, "total_weight")
        if lower > upper + 1e-12 or upper > total + 1e-12:
            raise GeometryConditioningInputError("Occupancy weights must satisfy lower <= upper <= total.")
        fractions = {name: _fraction(getattr(self, name), name) for name in (
            "lower_fraction", "upper_fraction", "core_overlap_fraction", "basin_overlap_fraction", "unresolved_fraction")}
        payload = {"schema": STATE_OCCUPANCY_BOUNDS_SCHEMA, "state_id": state, "lower_weight": lower,
                   "upper_weight": upper, "total_weight": total, **fractions}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("State-occupancy-bounds signature is inconsistent.")
        for name, value in (("state_id", state), ("lower_weight", lower), ("upper_weight", upper),
                            ("total_weight", total), *(fractions.items()), ("signature", expected)):
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": STATE_OCCUPANCY_BOUNDS_SCHEMA, "state_id": self.state_id,
                "lower_weight": self.lower_weight, "upper_weight": self.upper_weight,
                "total_weight": self.total_weight, "lower_fraction": self.lower_fraction,
                "upper_fraction": self.upper_fraction, "core_overlap_fraction": self.core_overlap_fraction,
                "basin_overlap_fraction": self.basin_overlap_fraction, "unresolved_fraction": self.unresolved_fraction,
                "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StateOccupancyBounds":
        if payload.get("schema") != STATE_OCCUPANCY_BOUNDS_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported state-occupancy-bounds schema.")
        return cls(int(payload["state_id"]), float(payload["lower_weight"]), float(payload["upper_weight"]),
                   float(payload["total_weight"]), float(payload["lower_fraction"]), float(payload["upper_fraction"]),
                   float(payload["core_overlap_fraction"]), float(payload["basin_overlap_fraction"]),
                   float(payload["unresolved_fraction"]), str(payload.get("signature", "")))


@dataclass(frozen=True, slots=True)
class GeometryConditionedSiteCatalog:
    validated_frozen_catalog_signature: str
    coordination_fingerprint_catalog_signature: str
    registered_structural_view_digest: str
    block_plan_signature: str
    options: GeometryConditioningOptions
    resources: GeometryConditioningResourcePolicy
    refinements: tuple[StateGeometryConditionedRefinement, ...]
    assignment_conflicts: tuple[AssignmentConflictRecord, ...]
    occupancy_bounds: tuple[StateOccupancyBounds, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        sources = {name: _sha(getattr(self, name), name) for name in (
            "validated_frozen_catalog_signature", "coordination_fingerprint_catalog_signature",
            "registered_structural_view_digest", "block_plan_signature")}
        refinements = tuple(self.refinements)
        if tuple(v.state_id for v in refinements) != tuple(sorted(v.state_id for v in refinements)):
            raise GeometryConditioningInputError("Refinements must be ordered by state id.")
        if len({v.state_id for v in refinements}) != len(refinements):
            raise GeometryConditioningInputError("Stage 11E5b accepts one selected structural association per state.")
        conflicts = tuple(self.assignment_conflicts)
        if tuple(v.sample_index for v in conflicts) != tuple(sorted(v.sample_index for v in conflicts)):
            raise GeometryConditioningInputError("Assignment conflicts must be ordered by sample index.")
        bounds = tuple(self.occupancy_bounds)
        if tuple(v.state_id for v in bounds) != tuple(v.state_id for v in refinements):
            raise GeometryConditioningInputError("Occupancy bounds must align with refinements.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": GEOMETRY_CONDITIONED_CATALOG_SCHEMA, **sources,
                   "options_signature": self.options.signature, "resources_signature": self.resources.signature,
                   "refinements": [v.signature for v in refinements], "assignment_conflicts": [v.signature for v in conflicts],
                   "occupancy_bounds": [v.signature for v in bounds], "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise GeometryConditioningInputError("Geometry-conditioned-catalog signature is inconsistent.")
        for name, value in (*sources.items(), ("refinements", refinements), ("assignment_conflicts", conflicts),
                            ("occupancy_bounds", bounds), ("metadata", metadata), ("signature", expected)):
            object.__setattr__(self, name, value)

    def for_state(self, state_id: int) -> StateGeometryConditionedRefinement:
        for item in self.refinements:
            if item.state_id == int(state_id):
                return item
        raise KeyError(state_id)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": GEOMETRY_CONDITIONED_CATALOG_SCHEMA,
                "validated_frozen_catalog_signature": self.validated_frozen_catalog_signature,
                "coordination_fingerprint_catalog_signature": self.coordination_fingerprint_catalog_signature,
                "registered_structural_view_digest": self.registered_structural_view_digest,
                "block_plan_signature": self.block_plan_signature, "options": self.options.to_dict(),
                "resources": self.resources.to_dict(), "refinements": [v.to_dict() for v in self.refinements],
                "assignment_conflicts": [v.to_dict() for v in self.assignment_conflicts],
                "occupancy_bounds": [v.to_dict() for v in self.occupancy_bounds],
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "GeometryConditionedSiteCatalog":
        if payload.get("schema") != GEOMETRY_CONDITIONED_CATALOG_SCHEMA:
            raise GeometryConditioningSerializationError("Unsupported geometry-conditioned-catalog schema.")
        return cls(str(payload["validated_frozen_catalog_signature"]),
                   str(payload["coordination_fingerprint_catalog_signature"]),
                   str(payload["registered_structural_view_digest"]), str(payload["block_plan_signature"]),
                   GeometryConditioningOptions.from_dict(payload["options"]),
                   GeometryConditioningResourcePolicy.from_dict(payload["resources"]),
                   tuple(StateGeometryConditionedRefinement.from_dict(v) for v in payload["refinements"]),
                   tuple(AssignmentConflictRecord.from_dict(v) for v in payload["assignment_conflicts"]),
                   tuple(StateOccupancyBounds.from_dict(v) for v in payload["occupancy_bounds"]),
                   dict(payload.get("metadata", {})), str(payload.get("signature", "")))


def _fit_affine_model(
    local: np.ndarray,
    predictors: np.ndarray,
    weights: np.ndarray,
    mask: np.ndarray,
    names: tuple[str, ...],
    options: GeometryConditioningOptions,
) -> tuple[GeometryCenterModel | None, GeometryModelDecision | None]:
    count = int(np.sum(mask))
    p = predictors.shape[1]
    if count < options.minimum_discovery_samples:
        return None, GeometryModelDecision.INSUFFICIENT_DISCOVERY_SUPPORT
    x = predictors[mask]
    y = local[mask]
    w = weights[mask]
    mean = np.average(x, axis=0, weights=w)
    design = np.column_stack((np.ones(count), x - mean))
    weighted = design * np.sqrt(w)[:, None]
    rank = int(np.linalg.matrix_rank(weighted))
    parameters = p + 1
    singular = np.linalg.svd(weighted, compute_uv=False)
    condition = float(np.inf if singular.size == 0 or singular[-1] <= 0 else singular[0] / singular[-1])
    if rank < parameters:
        return None, GeometryModelDecision.RANK_DEFICIENT
    if not np.isfinite(condition) or condition > options.maximum_condition_number:
        return None, GeometryModelDecision.ILL_CONDITIONED
    lhs = design.T @ (w[:, None] * design)
    if options.regularization > 0:
        penalty = np.eye(parameters)
        penalty[0, 0] = 0.0
        lhs = lhs + options.regularization * penalty
    rhs = design.T @ (w[:, None] * y)
    beta = np.linalg.solve(lhs, rhs)
    predicted = design @ beta
    residual = y - predicted
    return GeometryCenterModel(
        CenterModelKind.AFFINE_FRAMEWORK,
        names,
        mean,
        beta[0],
        beta[1:],
        rank,
        parameters,
        condition,
        count,
        _weighted_rms(residual, w),
        _weighted_covariance(residual, w),
    ), None


def _score_block(
    role: BlockRole,
    mask: np.ndarray,
    local: np.ndarray,
    weights: np.ndarray,
    static_centers: np.ndarray,
    dynamic_centers: np.ndarray | None,
) -> GeometryModelScore:
    count = int(np.sum(mask))
    if count == 0 or dynamic_centers is None:
        return GeometryModelScore(role, count, None, None, None)
    static_rms = _weighted_rms(local[mask] - static_centers[mask], weights[mask])
    dynamic_rms = _weighted_rms(local[mask] - dynamic_centers[mask], weights[mask])
    scale = max(static_rms, np.finfo(float).eps)
    return GeometryModelScore(role, count, static_rms, dynamic_rms, (static_rms - dynamic_rms) / scale)


def analyze_geometry_conditioned_state_samples(
    *,
    fingerprint: StateCoordinationFingerprint,
    predictor_table: FrameworkPredictorTable,
    frozen_region: FrozenRegionDefinition,
    block_plan: EvidenceBlockPlan,
    options: GeometryConditioningOptions | None = None,
) -> StateGeometryConditionedRefinement:
    """Fit and validate one frozen-assignment framework-conditioned center model."""
    options = options or GeometryConditioningOptions()
    if fingerprint.status is not CoordinationFingerprintStatus.RESOLVED:
        raise GeometryConditioningInputError("Geometry conditioning requires a resolved E5a fingerprint.")
    key = (fingerprint.state_id, fingerprint.candidate_index, fingerprint.persistent_identity)
    if key != (predictor_table.state_id, predictor_table.candidate_index, predictor_table.persistent_identity):
        raise GeometryConditioningInputError("Predictor table does not belong to the fingerprint.")
    if key != (frozen_region.state_id, frozen_region.candidate_index, frozen_region.persistent_identity):
        raise GeometryConditioningInputError("Frozen region does not belong to the fingerprint.")
    if not np.array_equal(fingerprint.sample_indices, predictor_table.sample_indices) or not np.array_equal(fingerprint.frame_indices, predictor_table.frame_indices):
        raise GeometryConditioningInputError("Predictor samples must exactly align with the E5a fingerprint.")
    n = fingerprint.sample_indices.size
    local = np.asarray(fingerprint.local_coordinates)
    weights = np.asarray(fingerprint.represented_time_weights)
    predictors = np.asarray(predictor_table.predictor_values)
    static_center = np.asarray(frozen_region.center)
    static_centers = np.repeat(static_center[None, :], n, axis=0)
    frames = np.asarray(fingerprint.frame_indices)
    discovery = np.isin(frames, block_plan.discovery_frame_indices)
    selection = np.isin(frames, block_plan.selection_frame_indices)
    validation = np.isin(frames, block_plan.final_validation_frame_indices)
    dynamic_model, fit_failure = _fit_affine_model(local, predictors, weights, discovery, predictor_table.predictor_names, options)
    dynamic_centers = static_centers.copy() if dynamic_model is None else dynamic_model.predict(predictors)
    scores = (
        _score_block(BlockRole.DISCOVERY, discovery, local, weights, static_centers, dynamic_centers if dynamic_model else None),
        _score_block(BlockRole.SELECTION, selection, local, weights, static_centers, dynamic_centers if dynamic_model else None),
        _score_block(BlockRole.FINAL_VALIDATION, validation, local, weights, static_centers, dynamic_centers if dynamic_model else None),
    )
    decision = fit_failure or GeometryModelDecision.STATIC_RETAINED
    diagnostics: list[str] = ["mobile_ion_coordinates_not_used_as_predictors", "frozen_discovery_assignments_not_recomputed"]
    if dynamic_model is not None:
        selection_score, validation_score = scores[1], scores[2]
        if selection_score.sample_count < options.minimum_selection_samples:
            decision = GeometryModelDecision.INSUFFICIENT_SELECTION_SUPPORT
        elif selection_score.relative_improvement is None or selection_score.relative_improvement < options.minimum_relative_selection_improvement:
            decision = GeometryModelDecision.STATIC_RETAINED
            diagnostics.append("selection_residual_gain_below_threshold")
        elif validation_score.sample_count < options.minimum_validation_samples:
            decision = GeometryModelDecision.INDEPENDENT_VALIDATION_UNAVAILABLE
        elif validation_score.dynamic_rms is None or validation_score.static_rms is None:
            decision = GeometryModelDecision.INDEPENDENT_VALIDATION_UNAVAILABLE
        elif validation_score.dynamic_rms > validation_score.static_rms * (1.0 + options.maximum_relative_validation_degradation):
            decision = GeometryModelDecision.FINAL_VALIDATION_CONTRADICTED
            diagnostics.append("final_validation_contradicted_selection_gain")
        else:
            decision = GeometryModelDecision.DYNAMIC_RETAINED
            diagnostics.append("dynamic_model_confirmed_on_final_validation")
    selected_kind = CenterModelKind.AFFINE_FRAMEWORK if decision is GeometryModelDecision.DYNAMIC_RETAINED else CenterModelKind.STATIC
    selected_centers = dynamic_centers if selected_kind is CenterModelKind.AFFINE_FRAMEWORK else static_centers
    static_model = GeometryCenterModel(
        CenterModelKind.STATIC,
        predictor_table.predictor_names,
        np.zeros(len(predictor_table.predictor_names)),
        static_center,
        np.zeros((len(predictor_table.predictor_names), 3)),
        1,
        len(predictor_table.predictor_names) + 1,
        1.0,
        int(np.sum(discovery)),
        _weighted_rms(local[discovery] - static_centers[discovery], weights[discovery]) if np.any(discovery) else 0.0,
        _weighted_covariance(local[discovery] - static_centers[discovery], weights[discovery]) if np.any(discovery) else np.zeros((3, 3)),
    )
    static_membership = _membership(local, static_centers, frozen_region.core_radius, frozen_region.basin_radius)
    dynamic_membership = _membership(local, dynamic_centers, frozen_region.core_radius, frozen_region.basin_radius)
    selected_membership = dynamic_membership if selected_kind is CenterModelKind.AFFINE_FRAMEWORK else static_membership
    comoving = np.zeros_like(local)
    center_disp = np.zeros_like(local)
    boundary_disp = np.zeros(n)
    crossings: list[BoundaryCrossingDiagnostic] = []
    order = np.lexsort((frames, predictor_table.segment_ids, fingerprint.ion_atom_indices))
    previous_by_key: dict[tuple[int, int], int] = {}
    for index in order:
        key_pair = (int(fingerprint.ion_atom_indices[index]), int(predictor_table.segment_ids[index]))
        previous = previous_by_key.get(key_pair)
        if previous is not None:
            ion_delta = local[index] - local[previous]
            c_delta = dynamic_centers[index] - dynamic_centers[previous]
            comoving_delta = (local[index] - dynamic_centers[index]) - (local[previous] - dynamic_centers[previous])
            comoving[index] = comoving_delta
            center_disp[index] = c_delta
            boundary_disp[index] = np.linalg.norm(c_delta)
            static_changed = static_membership[index] != static_membership[previous]
            dynamic_changed = dynamic_membership[index] != dynamic_membership[previous]
            ion_norm = float(np.linalg.norm(ion_delta))
            center_norm = float(np.linalg.norm(c_delta))
            comoving_norm = float(np.linalg.norm(comoving_delta))
            if not dynamic_changed:
                drive = CrossingDriveStatus.NO_CROSSING
            elif (not static_changed and center_norm > options.crossing_tolerance and
                  ion_norm <= options.boundary_induced_ratio * max(center_norm, options.crossing_tolerance)):
                drive = CrossingDriveStatus.BOUNDARY_INDUCED
            elif static_changed and ion_norm > options.boundary_induced_ratio * max(center_norm, options.crossing_tolerance):
                drive = CrossingDriveStatus.ION_DRIVEN
            else:
                drive = CrossingDriveStatus.MIXED
            crossings.append(BoundaryCrossingDiagnostic(
                int(fingerprint.sample_indices[previous]), int(fingerprint.sample_indices[index]),
                RegionMembership(int(static_membership[previous])), RegionMembership(int(static_membership[index])),
                RegionMembership(int(dynamic_membership[previous])), RegionMembership(int(dynamic_membership[index])),
                ion_norm, center_norm, comoving_norm, center_norm, drive,
                drive is CrossingDriveStatus.BOUNDARY_INDUCED,
            ))
        previous_by_key[key_pair] = int(index)
    static_residual = local - static_centers
    dynamic_residual = local - dynamic_centers
    return StateGeometryConditionedRefinement(
        fingerprint.state_id,
        fingerprint.candidate_index,
        fingerprint.persistent_identity,
        fingerprint.signature,
        predictor_table.signature,
        frozen_region.signature,
        decision,
        selected_kind,
        fingerprint.sample_indices,
        fingerprint.frame_indices,
        fingerprint.ion_atom_indices,
        predictor_table.segment_ids,
        fingerprint.represented_time_weights,
        fingerprint.local_coordinates,
        static_model,
        dynamic_model,
        scores,
        dynamic_centers,
        selected_centers,
        static_membership,
        dynamic_membership,
        selected_membership,
        comoving,
        center_disp,
        boundary_disp,
        tuple(crossings),
        _weighted_covariance(static_residual, weights),
        None if dynamic_model is None else _weighted_covariance(dynamic_residual, weights),
        tuple(diagnostics),
    )


def _conflict_records(refinements: Sequence[StateGeometryConditionedRefinement]) -> tuple[AssignmentConflictRecord, ...]:
    by_sample: dict[int, list[tuple[int, RegionMembership, RegionMembership, RegionMembership, bool]]] = {}
    for refinement in refinements:
        for i, sample in enumerate(refinement.sample_indices):
            by_sample.setdefault(int(sample), []).append((
                refinement.state_id,
                RegionMembership(int(refinement.static_membership[i])),
                RegionMembership(int(refinement.dynamic_membership[i])),
                RegionMembership(int(refinement.selected_membership[i])),
                refinement.dynamic_model is not None,
            ))
    records = []
    for sample, values in sorted(by_sample.items()):
        static_core = tuple(v[0] for v in values if v[1] is RegionMembership.CORE)
        static_basin = tuple(v[0] for v in values if v[1] >= RegionMembership.BASIN)
        dynamic_core = tuple(v[0] for v in values if v[2] is RegionMembership.CORE)
        dynamic_basin = tuple(v[0] for v in values if v[2] >= RegionMembership.BASIN)
        selected = tuple(v[0] for v in values if v[3] >= RegionMembership.BASIN)
        if len(dynamic_core) > 1:
            status = AssignmentConflictStatus.MULTIPLE_CORE_OVERLAP
        elif len(dynamic_basin) > 1:
            status = AssignmentConflictStatus.MULTIPLE_BASIN_OVERLAP
        elif len(static_basin) == 1 and len(dynamic_basin) == 1 and static_basin != dynamic_basin:
            status = AssignmentConflictStatus.STATIC_DYNAMIC_CONFLICT
        elif len(selected) == 1:
            membership = next(v[3] for v in values if v[0] == selected[0])
            status = AssignmentConflictStatus.UNIQUE_CORE if membership is RegionMembership.CORE else AssignmentConflictStatus.UNIQUE_BASIN
        elif len(selected) == 0:
            status = AssignmentConflictStatus.OUTSIDE_SUPPORTED_REGIONS
        else:
            status = AssignmentConflictStatus.ASSIGNMENT_UNRESOLVED
        records.append(AssignmentConflictRecord(sample, static_core, static_basin, dynamic_core, dynamic_basin, selected, status))
    return tuple(records)


def _occupancy_bounds(
    refinements: Sequence[StateGeometryConditionedRefinement],
    conflicts: Sequence[AssignmentConflictRecord],
) -> tuple[StateOccupancyBounds, ...]:
    sample_weight: dict[int, float] = {}
    for refinement in refinements:
        for sample, weight in zip(refinement.sample_indices, refinement.represented_time_weights, strict=True):
            sample_weight.setdefault(int(sample), float(weight))
    total = float(sum(sample_weight.values()))
    result: list[StateOccupancyBounds] = []
    for state in (v.state_id for v in refinements):
        lower = upper = core_overlap = basin_overlap = unresolved = 0.0
        for record in conflicts:
            w = sample_weight.get(record.sample_index, 0.0)
            if state in record.selected_state_ids:
                upper += w
                if record.status in (AssignmentConflictStatus.UNIQUE_CORE, AssignmentConflictStatus.UNIQUE_BASIN):
                    lower += w
            if state in record.dynamic_core_state_ids and record.status is AssignmentConflictStatus.MULTIPLE_CORE_OVERLAP:
                core_overlap += w
            if state in record.dynamic_basin_state_ids and record.status is AssignmentConflictStatus.MULTIPLE_BASIN_OVERLAP:
                basin_overlap += w
            if state in record.selected_state_ids and record.status in (
                AssignmentConflictStatus.ASSIGNMENT_UNRESOLVED, AssignmentConflictStatus.STATIC_DYNAMIC_CONFLICT):
                unresolved += w
        scale = max(total, np.finfo(float).eps)
        result.append(StateOccupancyBounds(
            state, lower, upper, total, lower / scale, upper / scale,
            core_overlap / scale, basin_overlap / scale, unresolved / scale,
        ))
    return tuple(result)


def prepare_geometry_conditioned_site_catalog(
    validated_catalog: ValidatedFrozenCatalog,
    fingerprint_catalog: CoordinationFingerprintCatalog,
    predictor_tables: Sequence[FrameworkPredictorTable],
    frozen_regions: Sequence[FrozenRegionDefinition],
    *,
    options: GeometryConditioningOptions | None = None,
    resources: GeometryConditioningResourcePolicy | None = None,
) -> GeometryConditionedSiteCatalog:
    """Prepare one-pass framework-conditioned site refinements for selected associations."""
    options = options or GeometryConditioningOptions()
    resources = resources or GeometryConditioningResourcePolicy()
    if fingerprint_catalog.validated_frozen_catalog_signature != validated_catalog.signature:
        raise GeometryConditioningInputError("E5a fingerprints do not belong to the supplied E5 catalog.")
    tables = tuple(predictor_tables)
    regions = tuple(frozen_regions)
    if len(tables) != len(regions):
        raise GeometryConditioningInputError("Each predictor table requires one frozen region definition.")
    if len(tables) > resources.max_states:
        raise GeometryConditioningResourceError("states exceed max_states")
    table_map = {(v.state_id, v.candidate_index): v for v in tables}
    region_map = {(v.state_id, v.candidate_index): v for v in regions}
    if len(table_map) != len(tables) or len(region_map) != len(regions):
        raise GeometryConditioningInputError("Predictor and frozen-region keys must be unique.")
    if len({v.state_id for v in tables}) != len(tables):
        raise GeometryConditioningInputError("Select at most one structural association per state for E5b refinement.")
    fingerprints = {(v.state_id, v.candidate_index): v for v in fingerprint_catalog.fingerprints}
    total_samples = sum(v.sample_indices.size for v in tables)
    total_predictors = sum(v.predictor_values.size for v in tables)
    if total_samples > resources.max_samples:
        raise GeometryConditioningResourceError("samples exceed max_samples")
    if total_predictors > resources.max_predictor_values:
        raise GeometryConditioningResourceError("predictor values exceed max_predictor_values")
    refinements: list[StateGeometryConditionedRefinement] = []
    for key in sorted(table_map):
        table = table_map[key]
        region = region_map.get(key)
        fingerprint = fingerprints.get(key)
        if region is None or fingerprint is None:
            raise GeometryConditioningInputError(f"Missing frozen region or fingerprint for state/candidate {key}.")
        if table.registered_structural_view_digest != fingerprint_catalog.registered_structural_view_digest:
            raise GeometryConditioningInputError("Predictor table and E5a structural view disagree.")
        if region.validated_frozen_catalog_signature != validated_catalog.signature:
            raise GeometryConditioningInputError("Frozen region does not belong to the supplied E5 catalog.")
        refinements.append(analyze_geometry_conditioned_state_samples(
            fingerprint=fingerprint,
            predictor_table=table,
            frozen_region=region,
            block_plan=validated_catalog.block_plan,
            options=options,
        ))
    crossing_count = sum(len(v.crossings) for v in refinements)
    if crossing_count > resources.max_crossings:
        raise GeometryConditioningResourceError("crossings exceed max_crossings")
    conflicts = _conflict_records(refinements)
    if len(conflicts) > resources.max_conflict_records:
        raise GeometryConditioningResourceError("assignment conflicts exceed max_conflict_records")
    bounds = _occupancy_bounds(refinements, conflicts)
    diagnostics = []
    for refinement, bound in zip(refinements, bounds, strict=True):
        if bound.core_overlap_fraction > options.maximum_core_overlap_fraction:
            diagnostics.append(f"state_{refinement.state_id}_core_overlap_exceeds_gate")
        if bound.basin_overlap_fraction > options.maximum_basin_overlap_fraction:
            diagnostics.append(f"state_{refinement.state_id}_basin_overlap_exceeds_gate")
        if bound.unresolved_fraction > options.maximum_unresolved_fraction:
            diagnostics.append(f"state_{refinement.state_id}_unresolved_fraction_exceeds_gate")
    serialized_records = len(refinements) + len(conflicts) + len(bounds) + crossing_count
    if serialized_records > resources.max_serialized_records:
        raise GeometryConditioningResourceError("serialized records exceed max_serialized_records")
    return GeometryConditionedSiteCatalog(
        validated_catalog.signature,
        fingerprint_catalog.signature,
        fingerprint_catalog.registered_structural_view_digest,
        validated_catalog.block_plan.signature,
        options,
        resources,
        tuple(refinements),
        conflicts,
        bounds,
        {
            "algorithm": "one_pass_frozen_assignment_affine_framework_center_v1",
            "mobile_ion_predictors_forbidden": True,
            "static_dynamic_membership_jointly_reported": True,
            "moving_regions_translate_frozen_shapes": True,
            "diagnostics": tuple(diagnostics),
        },
    )


__all__ = [
    "ASSIGNMENT_CONFLICT_RECORD_SCHEMA",
    "BOUNDARY_CROSSING_DIAGNOSTIC_SCHEMA",
    "FRAMEWORK_PREDICTOR_TABLE_SCHEMA",
    "FROZEN_REGION_DEFINITION_SCHEMA",
    "GEOMETRY_CENTER_MODEL_SCHEMA",
    "GEOMETRY_CONDITIONED_CATALOG_SCHEMA",
    "GEOMETRY_CONDITIONING_OPTIONS_SCHEMA",
    "GEOMETRY_CONDITIONING_RESOURCES_SCHEMA",
    "GEOMETRY_CONDITIONING_STAGE",
    "GEOMETRY_MODEL_SCORE_SCHEMA",
    "STATE_GEOMETRY_REFINEMENT_SCHEMA",
    "STATE_OCCUPANCY_BOUNDS_SCHEMA",
    "AssignmentConflictRecord",
    "AssignmentConflictStatus",
    "BlockRole",
    "BoundaryCrossingDiagnostic",
    "CenterModelKind",
    "CrossingDriveStatus",
    "FrameworkPredictorTable",
    "FrozenRegionDefinition",
    "GeometryCenterModel",
    "GeometryConditionedSiteCatalog",
    "GeometryConditioningError",
    "GeometryConditioningInputError",
    "GeometryConditioningOptions",
    "GeometryConditioningResourceError",
    "GeometryConditioningResourcePolicy",
    "GeometryConditioningSerializationError",
    "GeometryModelDecision",
    "GeometryModelScore",
    "RegionMembership",
    "StateGeometryConditionedRefinement",
    "StateOccupancyBounds",
    "analyze_geometry_conditioned_state_samples",
    "prepare_geometry_conditioned_site_catalog",
]
