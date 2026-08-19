"""Stage 11E-STAT1 source-observable production-regime assessment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np
from scipy.stats import t as student_t

from ..collection import AtomisticFrameCollection
from ..sampling import integrated_autocorrelation_time, split_frame_interval
from .control_certificates import EnsembleKind, SimulationControlCertificate
from .source_controls import (
    FrameEnergyCatalog,
    SourceControlError,
    SourceControlSerializationError,
)
from .trajectory_quality import (
    TrajectoryQualityOutcome,
    TrajectoryQualityVerdict,
)

PRODUCTION_WINDOW_POLICY_SCHEMA = "mdstats.production-window-policy.v1"
QUALITY_DIAGNOSTIC_BLOCK_PARTITION_SCHEMA = (
    "mdstats.quality-diagnostic-block-partition.v1"
)
OBSERVABLE_STATIONARITY_DIAGNOSTIC_SCHEMA = (
    "mdstats.observable-stationarity-diagnostic.v1"
)
CHANGE_POINT_CATALOG_SCHEMA = "mdstats.change-point-catalog.v1"
EXTERNAL_BOUNDARY_ASSESSMENT_SCHEMA = "mdstats.external-boundary-assessment.v1"
PRODUCTION_REGIME_SCHEMA = "mdstats.production-regime.v1"
PRODUCTION_REGIME_CATALOG_SCHEMA = "mdstats.production-regime-catalog.v1"
PRODUCTION_WINDOW_POLICY_VERSION = "mdstats.production-window-policy.2026-07.v1"


class ObservableStationarityStatus(str, Enum):
    STATIONARY = "stationary"
    NONSTATIONARY = "nonstationary"
    INSUFFICIENT = "insufficient"
    UNAVAILABLE = "unavailable"


class ThermalizationEvidenceStatus(str, Enum):
    NO_DETECTED_TRANSIENT = "no_detected_transient"
    TRANSIENT_DETECTED = "transient_detected"
    AMBIGUOUS = "ambiguous"
    INSUFFICIENT = "insufficient"


class RegimeStationarityStatus(str, Enum):
    SUPPORTED = "supported"
    AMBIGUOUS = "ambiguous"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class ProductionIntervalStatus(str, Enum):
    SCIENTIFIC_CANDIDATE = "scientific_candidate"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"


class SelectionConditioningStatus(str, Enum):
    FULL_SOURCE = "full_source"
    EXTERNALLY_BOUNDED_TESTED = "externally_bounded_tested"
    SELECTION_CONDITIONED = "selection_conditioned"


class ProductionCatalogStatus(str, Enum):
    ACCEPTED = "accepted"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    INSUFFICIENT = "insufficient"
    REJECTED = "rejected"


class ChangePointStatus(str, Enum):
    DETECTED = "detected"
    NONE = "none"
    INSUFFICIENT = "insufficient"


class ExternalBoundaryStatus(str, Enum):
    SUPPORTED = "supported"
    REJECTED = "rejected"
    INSUFFICIENT = "insufficient"
    SOURCE_EDGE = "source_edge"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _finite_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SourceControlError(f"{name} must be finite.")
    return result



@dataclass(frozen=True, slots=True)
class ProductionWindowPolicy:
    """Versioned STAT1 block, change-point, and stationarity policy."""

    policy_version: str = PRODUCTION_WINDOW_POLICY_VERSION
    confidence_level: float = 0.95
    minimum_block_frames: int = 32
    minimum_independent_blocks: int = 4
    autocorrelation_block_multiplier: float = 2.0
    change_point_minimum_blocks: int = 3
    change_point_penalty_scale: float = 3.0
    maximum_change_points: int = 4
    external_boundary_shift_threshold: float = 2.5
    trend_z_threshold: float = 2.5
    normalized_span_threshold: float = 1.0
    ambiguous_normalized_span_threshold: float = 3.0
    stationary_primary_fraction: float = 0.75
    early_transient_fraction: float = 0.35
    observable_scale_floor_fraction: float = 1.0e-8

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SourceControlError("Production-window policy version is required.")
        if not 0.0 < self.confidence_level < 1.0:
            raise SourceControlError("confidence_level must lie between zero and one.")
        if self.minimum_block_frames < 2 or self.minimum_independent_blocks < 2:
            raise SourceControlError("Block requirements must be at least two.")
        if self.change_point_minimum_blocks < 2:
            raise SourceControlError("Change-point segments require at least two blocks.")
        if self.maximum_change_points < 0:
            raise SourceControlError("maximum_change_points must be nonnegative.")
        if not 0.0 < self.stationary_primary_fraction <= 1.0:
            raise SourceControlError("stationary_primary_fraction must lie in (0, 1].")
        if not 0.0 < self.early_transient_fraction < 1.0:
            raise SourceControlError("early_transient_fraction must lie in (0, 1).")
        for name in (
            "autocorrelation_block_multiplier",
            "change_point_penalty_scale",
            "external_boundary_shift_threshold",
            "trend_z_threshold",
            "normalized_span_threshold",
            "ambiguous_normalized_span_threshold",
            "observable_scale_floor_fraction",
        ):
            if getattr(self, name) < 0.0:
                raise SourceControlError(f"{name} must be nonnegative.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PRODUCTION_WINDOW_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "confidence_level": self.confidence_level,
            "minimum_block_frames": self.minimum_block_frames,
            "minimum_independent_blocks": self.minimum_independent_blocks,
            "autocorrelation_block_multiplier": self.autocorrelation_block_multiplier,
            "change_point_minimum_blocks": self.change_point_minimum_blocks,
            "change_point_penalty_scale": self.change_point_penalty_scale,
            "maximum_change_points": self.maximum_change_points,
            "external_boundary_shift_threshold": self.external_boundary_shift_threshold,
            "trend_z_threshold": self.trend_z_threshold,
            "normalized_span_threshold": self.normalized_span_threshold,
            "ambiguous_normalized_span_threshold": self.ambiguous_normalized_span_threshold,
            "stationary_primary_fraction": self.stationary_primary_fraction,
            "early_transient_fraction": self.early_transient_fraction,
            "observable_scale_floor_fraction": self.observable_scale_floor_fraction,
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionWindowPolicy":
        if payload.get("schema") != PRODUCTION_WINDOW_POLICY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported production-window-policy schema."
            )
        kwargs = {
            key: value
            for key, value in payload.items()
            if key not in {"schema", "signature"}
        }
        result = cls(**kwargs)
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Production-window-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class QualityDiagnosticBlockPartition:
    source_identity_signature: str
    trajectory_quality_verdict_signature: str
    policy_signature: str
    frame_count: int
    block_length_frames: int
    block_boundaries: tuple[tuple[int, int], ...]
    block_center_times_ps: tuple[float, ...]
    observable_autocorrelation_times_frames: tuple[tuple[str, float], ...]

    def __post_init__(self) -> None:
        for value in (
            self.source_identity_signature,
            self.trajectory_quality_verdict_signature,
            self.policy_signature,
        ):
            if len(value) != 64:
                raise SourceControlError("Block-partition signatures must be SHA-256 digests.")
        boundaries = tuple((int(a), int(b)) for a, b in self.block_boundaries)
        if self.frame_count < 1 or self.block_length_frames < 1:
            raise SourceControlError("Block partition requires positive frame counts.")
        if boundaries:
            if boundaries[0][0] != 0 or boundaries[-1][1] != self.frame_count:
                raise SourceControlError("Block partition must cover the complete source.")
            previous = 0
            for start, stop in boundaries:
                if start != previous or stop <= start:
                    raise SourceControlError("Block partition must be contiguous and nonempty.")
                previous = stop
        object.__setattr__(self, "block_boundaries", boundaries)
        object.__setattr__(
            self,
            "block_center_times_ps",
            tuple(_finite_float(v, name="block center time") for v in self.block_center_times_ps),
        )
        object.__setattr__(
            self,
            "observable_autocorrelation_times_frames",
            tuple((str(name), _finite_float(value, name="autocorrelation time")) for name, value in self.observable_autocorrelation_times_frames),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": QUALITY_DIAGNOSTIC_BLOCK_PARTITION_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "trajectory_quality_verdict_signature": self.trajectory_quality_verdict_signature,
            "policy_signature": self.policy_signature,
            "frame_count": self.frame_count,
            "block_length_frames": self.block_length_frames,
            "block_boundaries": [list(item) for item in self.block_boundaries],
            "block_center_times_ps": list(self.block_center_times_ps),
            "observable_autocorrelation_times_frames": [
                [name, value]
                for name, value in self.observable_autocorrelation_times_frames
            ],
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "QualityDiagnosticBlockPartition":
        if payload.get("schema") != QUALITY_DIAGNOSTIC_BLOCK_PARTITION_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported quality-diagnostic-block-partition schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            trajectory_quality_verdict_signature=str(
                payload["trajectory_quality_verdict_signature"]
            ),
            policy_signature=str(payload["policy_signature"]),
            frame_count=int(payload["frame_count"]),
            block_length_frames=int(payload["block_length_frames"]),
            block_boundaries=tuple(
                (int(item[0]), int(item[1]))
                for item in payload.get("block_boundaries", ())
            ),
            block_center_times_ps=tuple(
                float(value) for value in payload.get("block_center_times_ps", ())
            ),
            observable_autocorrelation_times_frames=tuple(
                (str(item[0]), float(item[1]))
                for item in payload.get(
                    "observable_autocorrelation_times_frames", ()
                )
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Block-partition signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableStationarityDiagnostic:
    observable_name: str
    role: str
    units: str
    frame_start: int
    frame_stop: int
    block_count: int
    mean: float | None
    standard_deviation: float | None
    block_standard_deviation: float | None
    integrated_autocorrelation_time_frames: float | None
    slope_per_ps: float | None
    slope_standard_error_per_ps: float | None
    slope_z_score: float | None
    observation_span_change: float | None
    normalized_span_change: float | None
    status: ObservableStationarityStatus
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.observable_name or not self.units or not self.role:
            raise SourceControlError("Observable diagnostics require names, roles, and units.")
        if self.frame_start < 0 or self.frame_stop <= self.frame_start:
            raise SourceControlError("Observable diagnostic frame interval is invalid.")
        object.__setattr__(self, "status", ObservableStationarityStatus(self.status))
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))
        for name in (
            "mean",
            "standard_deviation",
            "block_standard_deviation",
            "integrated_autocorrelation_time_frames",
            "slope_per_ps",
            "slope_standard_error_per_ps",
            "slope_z_score",
            "observation_span_change",
            "normalized_span_change",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _finite_float(value, name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_STATIONARITY_DIAGNOSTIC_SCHEMA,
            "observable_name": self.observable_name,
            "role": self.role,
            "units": self.units,
            "frame_start": self.frame_start,
            "frame_stop": self.frame_stop,
            "block_count": self.block_count,
            "mean": self.mean,
            "standard_deviation": self.standard_deviation,
            "block_standard_deviation": self.block_standard_deviation,
            "integrated_autocorrelation_time_frames": self.integrated_autocorrelation_time_frames,
            "slope_per_ps": self.slope_per_ps,
            "slope_standard_error_per_ps": self.slope_standard_error_per_ps,
            "slope_z_score": self.slope_z_score,
            "observation_span_change": self.observation_span_change,
            "normalized_span_change": self.normalized_span_change,
            "status": self.status.value,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "ObservableStationarityDiagnostic":
        if payload.get("schema") != OBSERVABLE_STATIONARITY_DIAGNOSTIC_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported observable-stationarity-diagnostic schema."
            )
        def optional(name: str) -> float | None:
            return None if payload.get(name) is None else float(payload[name])
        result = cls(
            observable_name=str(payload["observable_name"]),
            role=str(payload["role"]),
            units=str(payload["units"]),
            frame_start=int(payload["frame_start"]),
            frame_stop=int(payload["frame_stop"]),
            block_count=int(payload["block_count"]),
            mean=optional("mean"),
            standard_deviation=optional("standard_deviation"),
            block_standard_deviation=optional("block_standard_deviation"),
            integrated_autocorrelation_time_frames=optional(
                "integrated_autocorrelation_time_frames"
            ),
            slope_per_ps=optional("slope_per_ps"),
            slope_standard_error_per_ps=optional("slope_standard_error_per_ps"),
            slope_z_score=optional("slope_z_score"),
            observation_span_change=optional("observation_span_change"),
            normalized_span_change=optional("normalized_span_change"),
            status=ObservableStationarityStatus(payload["status"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Observable-stationarity-diagnostic signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class ExternalBoundaryAssessment:
    frame_index: int
    nearest_block_index: int | None
    status: ExternalBoundaryStatus
    maximum_standardized_shift: float | None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.frame_index < 0:
            raise SourceControlError("External boundary frame index must be nonnegative.")
        object.__setattr__(self, "status", ExternalBoundaryStatus(self.status))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EXTERNAL_BOUNDARY_ASSESSMENT_SCHEMA,
            "frame_index": self.frame_index,
            "nearest_block_index": self.nearest_block_index,
            "status": self.status.value,
            "maximum_standardized_shift": self.maximum_standardized_shift,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExternalBoundaryAssessment":
        if payload.get("schema") != EXTERNAL_BOUNDARY_ASSESSMENT_SCHEMA:
            raise SourceControlSerializationError("Unsupported external-boundary-assessment schema.")
        result = cls(
            frame_index=int(payload["frame_index"]),
            nearest_block_index=None if payload.get("nearest_block_index") is None else int(payload["nearest_block_index"]),
            status=ExternalBoundaryStatus(payload["status"]),
            maximum_standardized_shift=None if payload.get("maximum_standardized_shift") is None else float(payload["maximum_standardized_shift"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("External-boundary-assessment signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ChangePointCatalog:
    method: str
    status: ChangePointStatus
    penalty: float | None
    block_indices: tuple[int, ...]
    frame_indices: tuple[int, ...]
    segment_cost: float | None
    external_boundaries: tuple[ExternalBoundaryAssessment, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.method:
            raise SourceControlError("Change-point method is required.")
        object.__setattr__(self, "status", ChangePointStatus(self.status))
        object.__setattr__(self, "block_indices", tuple(int(v) for v in self.block_indices))
        object.__setattr__(self, "frame_indices", tuple(int(v) for v in self.frame_indices))
        object.__setattr__(self, "external_boundaries", tuple(self.external_boundaries))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CHANGE_POINT_CATALOG_SCHEMA,
            "method": self.method,
            "status": self.status.value,
            "penalty": self.penalty,
            "block_indices": list(self.block_indices),
            "frame_indices": list(self.frame_indices),
            "segment_cost": self.segment_cost,
            "external_boundaries": [item.to_dict() for item in self.external_boundaries],
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ChangePointCatalog":
        if payload.get("schema") != CHANGE_POINT_CATALOG_SCHEMA:
            raise SourceControlSerializationError("Unsupported change-point-catalog schema.")
        result = cls(
            method=str(payload["method"]),
            status=ChangePointStatus(payload["status"]),
            penalty=None if payload.get("penalty") is None else float(payload["penalty"]),
            block_indices=tuple(int(v) for v in payload.get("block_indices", ())),
            frame_indices=tuple(int(v) for v in payload.get("frame_indices", ())),
            segment_cost=None if payload.get("segment_cost") is None else float(payload["segment_cost"]),
            external_boundaries=tuple(ExternalBoundaryAssessment.from_dict(item) for item in payload.get("external_boundaries", ())),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Change-point-catalog signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionRegime:
    regime_id: str
    frame_start: int
    frame_stop: int
    time_start_ps: float
    time_stop_ps: float
    block_start: int
    block_stop: int
    diagnostics: tuple[ObservableStationarityDiagnostic, ...]
    thermalization_status: ThermalizationEvidenceStatus
    stationarity_status: RegimeStationarityStatus
    production_interval_status: ProductionIntervalStatus
    selection_conditioning_status: SelectionConditioningStatus
    quality_outcome: TrajectoryQualityOutcome
    scientific_use_permitted: bool
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.regime_id or self.frame_start < 0 or self.frame_stop <= self.frame_start:
            raise SourceControlError("Production regime requires a valid identity and interval.")
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        object.__setattr__(self, "thermalization_status", ThermalizationEvidenceStatus(self.thermalization_status))
        object.__setattr__(self, "stationarity_status", RegimeStationarityStatus(self.stationarity_status))
        object.__setattr__(self, "production_interval_status", ProductionIntervalStatus(self.production_interval_status))
        object.__setattr__(self, "selection_conditioning_status", SelectionConditioningStatus(self.selection_conditioning_status))
        object.__setattr__(self, "quality_outcome", TrajectoryQualityOutcome(self.quality_outcome))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PRODUCTION_REGIME_SCHEMA,
            "regime_id": self.regime_id,
            "frame_start": self.frame_start,
            "frame_stop": self.frame_stop,
            "time_start_ps": self.time_start_ps,
            "time_stop_ps": self.time_stop_ps,
            "block_start": self.block_start,
            "block_stop": self.block_stop,
            "diagnostics": [item.to_dict() for item in self.diagnostics],
            "thermalization_status": self.thermalization_status.value,
            "stationarity_status": self.stationarity_status.value,
            "production_interval_status": self.production_interval_status.value,
            "selection_conditioning_status": self.selection_conditioning_status.value,
            "quality_outcome": self.quality_outcome.value,
            "scientific_use_permitted": self.scientific_use_permitted,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionRegime":
        if payload.get("schema") != PRODUCTION_REGIME_SCHEMA:
            raise SourceControlSerializationError("Unsupported production-regime schema.")
        result = cls(
            regime_id=str(payload["regime_id"]),
            frame_start=int(payload["frame_start"]),
            frame_stop=int(payload["frame_stop"]),
            time_start_ps=float(payload["time_start_ps"]),
            time_stop_ps=float(payload["time_stop_ps"]),
            block_start=int(payload["block_start"]),
            block_stop=int(payload["block_stop"]),
            diagnostics=tuple(
                ObservableStationarityDiagnostic.from_dict(item)
                for item in payload.get("diagnostics", ())
            ),
            thermalization_status=ThermalizationEvidenceStatus(payload["thermalization_status"]),
            stationarity_status=RegimeStationarityStatus(payload["stationarity_status"]),
            production_interval_status=ProductionIntervalStatus(payload["production_interval_status"]),
            selection_conditioning_status=SelectionConditioningStatus(payload["selection_conditioning_status"]),
            quality_outcome=TrajectoryQualityOutcome(payload["quality_outcome"]),
            scientific_use_permitted=bool(payload["scientific_use_permitted"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Production-regime signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionRegimeCatalog:
    source_identity_signature: str
    simulation_control_certificate_signature: str
    trajectory_quality_verdict_signature: str
    policy_signature: str
    block_partition: QualityDiagnosticBlockPartition
    change_points: ChangePointCatalog
    regimes: tuple[ProductionRegime, ...]
    selected_regime_ids: tuple[str, ...]
    overall_status: ProductionCatalogStatus
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value in (
            self.source_identity_signature,
            self.simulation_control_certificate_signature,
            self.trajectory_quality_verdict_signature,
            self.policy_signature,
        ):
            if len(value) != 64:
                raise SourceControlError("Production-catalog signatures must be SHA-256 digests.")
        object.__setattr__(self, "regimes", tuple(self.regimes))
        object.__setattr__(self, "selected_regime_ids", tuple(str(v) for v in self.selected_regime_ids))
        object.__setattr__(self, "overall_status", ProductionCatalogStatus(self.overall_status))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        known = {regime.regime_id for regime in self.regimes}
        if not set(self.selected_regime_ids).issubset(known):
            raise SourceControlError("Selected production regimes must exist in the catalog.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PRODUCTION_REGIME_CATALOG_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "simulation_control_certificate_signature": self.simulation_control_certificate_signature,
            "trajectory_quality_verdict_signature": self.trajectory_quality_verdict_signature,
            "policy_signature": self.policy_signature,
            "block_partition": self.block_partition.to_dict(),
            "change_points": self.change_points.to_dict(),
            "regimes": [regime.to_dict() for regime in self.regimes],
            "selected_regime_ids": list(self.selected_regime_ids),
            "overall_status": self.overall_status.value,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionRegimeCatalog":
        if payload.get("schema") != PRODUCTION_REGIME_CATALOG_SCHEMA:
            raise SourceControlSerializationError("Unsupported production-regime-catalog schema.")
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            simulation_control_certificate_signature=str(payload["simulation_control_certificate_signature"]),
            trajectory_quality_verdict_signature=str(payload["trajectory_quality_verdict_signature"]),
            policy_signature=str(payload["policy_signature"]),
            block_partition=QualityDiagnosticBlockPartition.from_dict(payload["block_partition"]),
            change_points=ChangePointCatalog.from_dict(payload["change_points"]),
            regimes=tuple(ProductionRegime.from_dict(item) for item in payload.get("regimes", ())),
            selected_regime_ids=tuple(str(v) for v in payload.get("selected_regime_ids", ())),
            overall_status=ProductionCatalogStatus(payload["overall_status"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Production-regime-catalog signature mismatch.")
        return result


def _source_observables(
    collection: AtomisticFrameCollection,
    quality_verdict: TrajectoryQualityVerdict,
    energy_catalog: FrameEnergyCatalog,
    control_certificate: SimulationControlCertificate,
) -> dict[str, tuple[np.ndarray, str, str]]:
    observables: dict[str, tuple[np.ndarray, str, str]] = {}
    temperature = quality_verdict.temperature_statistics
    if temperature is not None and len(temperature.temperatures_kelvin) == collection.n_frames:
        observables["ionic_temperature"] = (
            np.asarray(temperature.temperatures_kelvin, dtype=np.float64),
            "K",
            "distribution_primary",
        )

    channel_map = {
        "e_fr_energy": ("potential_energy", "eV", "distribution_primary"),
        "kinetic": ("kinetic_energy", "eV", "distribution_primary"),
        "total": ("total_energy", "eV", "conservation_diagnostic"),
    }
    for source_name, (name, units, role) in channel_map.items():
        channel = energy_catalog.channel(source_name)
        if channel is not None and channel.complete and channel.frame_count == collection.n_frames:
            observables[name] = (channel.as_array(), units, role)

    observables["cell_volume"] = (
        np.asarray(collection.volumes, dtype=np.float64),
        "angstrom^3",
        "cell_primary" if control_certificate.cell_control.active else "cell_diagnostic",
    )
    pressures = collection.pressures
    if pressures is not None and pressures.shape == (collection.n_frames,):
        observables["pressure"] = (
            np.asarray(pressures, dtype=np.float64),
            "eV/angstrom^3",
            "distribution_primary" if control_certificate.cell_control.active else "optional",
        )
    if collection.stresses is not None:
        stress_norm = np.linalg.norm(collection.stresses.reshape(collection.n_frames, -1), axis=1)
        observables["stress_norm"] = (
            np.asarray(stress_norm, dtype=np.float64),
            "eV/angstrom^3",
            "optional",
        )
    if collection.velocities is not None and collection.provenance is not None and collection.provenance.velocity_source == "native":
        momentum = np.einsum("n,tni->ti", collection.masses, collection.velocities)
        observables["center_of_mass_momentum_norm"] = (
            np.linalg.norm(momentum, axis=1),
            "amu*angstrom/ps",
            "optional",
        )
    return observables


def _make_partition(
    *,
    collection: AtomisticFrameCollection,
    observables: Mapping[str, tuple[np.ndarray, str, str]],
    source_identity_signature: str,
    quality_verdict: TrajectoryQualityVerdict,
    policy: ProductionWindowPolicy,
) -> QualityDiagnosticBlockPartition:
    times = collection.require_time_axis("Stage 11E-STAT1")
    tau_items: list[tuple[str, float]] = []
    for name, (values, _, role) in observables.items():
        if role == "optional":
            continue
        values = np.asarray(values, dtype=np.float64)
        chunk_count = min(4, max(1, values.size // policy.minimum_block_frames))
        local_taus: list[float] = []
        for chunk in np.array_split(np.arange(values.size), chunk_count):
            if chunk.size < 3:
                continue
            local_values = values[chunk]
            local_axis = np.arange(chunk.size, dtype=np.float64)
            if np.ptp(local_values) > np.finfo(np.float64).eps:
                design = np.column_stack([local_axis, np.ones(chunk.size)])
                slope, intercept = np.linalg.lstsq(design, local_values, rcond=None)[0]
                residual = local_values - (slope * local_axis + intercept)
            else:
                residual = local_values - np.mean(local_values)
            local_taus.append(integrated_autocorrelation_time(residual))
        tau_items.append((name, max(local_taus, default=0.5)))
    tau_pairs = tuple(sorted(tau_items))
    max_tau = max((value for _, value in tau_pairs), default=0.5)
    block_length = max(
        policy.minimum_block_frames,
        int(math.ceil(policy.autocorrelation_block_multiplier * max_tau)),
    )
    # Use all frames while keeping every block at or above the target length.
    boundaries = tuple(
        (interval.frame_start, interval.frame_stop)
        for interval in split_frame_interval(0, collection.n_frames, block_length)
    )
    centers = tuple(float(np.mean(times[start:stop])) for start, stop in boundaries)
    return QualityDiagnosticBlockPartition(
        source_identity_signature=source_identity_signature,
        trajectory_quality_verdict_signature=quality_verdict.signature,
        policy_signature=policy.signature,
        frame_count=collection.n_frames,
        block_length_frames=block_length,
        block_boundaries=boundaries,
        block_center_times_ps=centers,
        observable_autocorrelation_times_frames=tau_pairs,
    )


def _block_matrix(
    partition: QualityDiagnosticBlockPartition,
    observables: Mapping[str, tuple[np.ndarray, str, str]],
) -> tuple[np.ndarray, tuple[str, ...]]:
    names = tuple(
        name
        for name, (_, _, role) in observables.items()
        if role in {"distribution_primary", "cell_primary"}
    )
    columns: list[np.ndarray] = []
    kept: list[str] = []
    for name in names:
        values = observables[name][0]
        means = np.asarray(
            [float(np.mean(values[start:stop])) for start, stop in partition.block_boundaries]
        )
        scale = float(np.std(means, ddof=1)) if means.size > 1 else 0.0
        if scale <= np.finfo(np.float64).eps:
            continue
        columns.append((means - float(np.mean(means))) / scale)
        kept.append(name)
    if not columns:
        return np.empty((len(partition.block_boundaries), 0)), tuple()
    return np.column_stack(columns), tuple(kept)


def _segment_cost(prefix: np.ndarray, prefix2: np.ndarray, start: int, stop: int) -> float:
    count = stop - start
    if count <= 0:
        return math.inf
    total = prefix[stop] - prefix[start]
    total2 = prefix2[stop] - prefix2[start]
    return float(np.sum(total2 - total * total / count))


def _detect_change_points(
    *,
    partition: QualityDiagnosticBlockPartition,
    observables: Mapping[str, tuple[np.ndarray, str, str]],
    policy: ProductionWindowPolicy,
    external_candidate_boundaries: Sequence[int] = (),
) -> ChangePointCatalog:
    matrix, names = _block_matrix(partition, observables)
    block_count = matrix.shape[0]
    minimum = policy.change_point_minimum_blocks
    external_assessments: list[ExternalBoundaryAssessment] = []
    block_starts = [start for start, _ in partition.block_boundaries]
    for raw_frame_index in external_candidate_boundaries:
        frame_index = int(raw_frame_index)
        if frame_index < 0 or frame_index > partition.frame_count:
            raise SourceControlError("External boundary lies outside the source frame axis.")
        if frame_index in {0, partition.frame_count}:
            external_assessments.append(ExternalBoundaryAssessment(
                frame_index=frame_index,
                nearest_block_index=0 if frame_index == 0 else block_count,
                status=ExternalBoundaryStatus.SOURCE_EDGE,
                maximum_standardized_shift=None,
                notes=("Source-edge provenance retained; no within-source two-sided test is possible.",),
            ))
            continue
        nearest = min(range(1, block_count), key=lambda i: abs(block_starts[i] - frame_index)) if block_count > 1 else None
        if nearest is None or nearest < minimum or block_count - nearest < minimum or matrix.shape[1] == 0:
            external_assessments.append(ExternalBoundaryAssessment(
                frame_index=frame_index,
                nearest_block_index=nearest,
                status=ExternalBoundaryStatus.INSUFFICIENT,
                maximum_standardized_shift=None,
                notes=("Insufficient independent blocks for a two-sided source-observable test.",),
            ))
            continue
        left = np.mean(matrix[max(0, nearest - minimum):nearest], axis=0)
        right = np.mean(matrix[nearest:min(block_count, nearest + minimum)], axis=0)
        shift = float(np.max(np.abs(right - left)))
        external_assessments.append(ExternalBoundaryAssessment(
            frame_index=frame_index,
            nearest_block_index=nearest,
            status=ExternalBoundaryStatus.SUPPORTED if shift >= policy.external_boundary_shift_threshold else ExternalBoundaryStatus.REJECTED,
            maximum_standardized_shift=shift,
            notes=("Boundary was tested against adjacent complete-system block means.",),
        ))
    if block_count < 2 * minimum or matrix.shape[1] == 0:
        return ChangePointCatalog(
            method="penalized_multivariate_least_squares",
            status=ChangePointStatus.INSUFFICIENT,
            penalty=None,
            block_indices=(),
            frame_indices=(),
            segment_cost=None,
            external_boundaries=tuple(external_assessments),
            notes=("Too few independent blocks or varying primary observables.",),
        )

    prefix = np.vstack([np.zeros((1, matrix.shape[1])), np.cumsum(matrix, axis=0)])
    prefix2 = np.vstack([np.zeros((1, matrix.shape[1])), np.cumsum(matrix * matrix, axis=0)])
    penalty = float(
        policy.change_point_penalty_scale
        * matrix.shape[1]
        * math.log(max(2, block_count))
    )
    max_segments = min(policy.maximum_change_points + 1, block_count // minimum)
    dp = np.full((max_segments + 1, block_count + 1), np.inf)
    previous = np.full((max_segments + 1, block_count + 1), -1, dtype=np.int64)
    dp[0, 0] = 0.0
    for segments in range(1, max_segments + 1):
        min_stop = segments * minimum
        for stop in range(min_stop, block_count + 1):
            start_min = (segments - 1) * minimum
            start_max = stop - minimum
            for start in range(start_min, start_max + 1):
                if not math.isfinite(dp[segments - 1, start]):
                    continue
                value = dp[segments - 1, start] + _segment_cost(prefix, prefix2, start, stop)
                if value < dp[segments, stop]:
                    dp[segments, stop] = value
                    previous[segments, stop] = start
    objectives = [
        dp[segments, block_count] + penalty * (segments - 1)
        for segments in range(1, max_segments + 1)
    ]
    best_segments = int(np.argmin(objectives)) + 1
    best_cost = float(dp[best_segments, block_count])
    boundaries: list[int] = []
    stop = block_count
    for segments in range(best_segments, 0, -1):
        start = int(previous[segments, stop])
        if start < 0:
            boundaries = []
            break
        if start > 0:
            boundaries.append(start)
        stop = start
    block_indices = tuple(sorted(boundaries))
    frame_indices = tuple(partition.block_boundaries[index][0] for index in block_indices)
    return ChangePointCatalog(
        method="penalized_multivariate_least_squares",
        status=ChangePointStatus.DETECTED if block_indices else ChangePointStatus.NONE,
        penalty=penalty,
        block_indices=block_indices,
        frame_indices=frame_indices,
        segment_cost=best_cost,
        external_boundaries=tuple(external_assessments),
        notes=("Primary observables: " + ", ".join(names),),
    )


def _observable_diagnostic(
    *,
    name: str,
    values: np.ndarray,
    units: str,
    role: str,
    frame_start: int,
    frame_stop: int,
    block_boundaries: Sequence[tuple[int, int]],
    times: np.ndarray,
    policy: ProductionWindowPolicy,
) -> ObservableStationarityDiagnostic:
    segment = np.asarray(values[frame_start:frame_stop], dtype=np.float64)
    tau = integrated_autocorrelation_time(segment)
    local_blocks = [
        (max(start, frame_start), min(stop, frame_stop))
        for start, stop in block_boundaries
        if start >= frame_start and stop <= frame_stop
    ]
    block_means = np.asarray(
        [float(np.mean(values[start:stop])) for start, stop in local_blocks],
        dtype=np.float64,
    )
    block_times = np.asarray(
        [float(np.mean(times[start:stop])) for start, stop in local_blocks],
        dtype=np.float64,
    )
    mean = float(np.mean(segment))
    sd = float(np.std(segment))
    block_sd = float(np.std(block_means, ddof=1)) if block_means.size > 1 else None
    if block_means.size < policy.minimum_independent_blocks or np.ptp(block_times) <= 0.0:
        return ObservableStationarityDiagnostic(
            observable_name=name,
            role=role,
            units=units,
            frame_start=frame_start,
            frame_stop=frame_stop,
            block_count=int(block_means.size),
            mean=mean,
            standard_deviation=sd,
            block_standard_deviation=block_sd,
            integrated_autocorrelation_time_frames=tau,
            slope_per_ps=None,
            slope_standard_error_per_ps=None,
            slope_z_score=None,
            observation_span_change=None,
            normalized_span_change=None,
            status=ObservableStationarityStatus.INSUFFICIENT,
        )
    design = np.column_stack([block_times, np.ones(block_times.size)])
    slope, intercept = np.linalg.lstsq(design, block_means, rcond=None)[0]
    residual = block_means - (slope * block_times + intercept)
    dof = block_means.size - 2
    denominator = float(np.sum((block_times - np.mean(block_times)) ** 2))
    slope_se = None
    if dof > 0 and denominator > 0.0:
        slope_se = math.sqrt(float(np.dot(residual, residual) / dof) / denominator)
    z_score = None if slope_se in (None, 0.0) else abs(float(slope)) / slope_se
    span = float(slope * (times[frame_stop - 1] - times[frame_start]))
    floor = max(
        abs(mean) * policy.observable_scale_floor_fraction,
        np.finfo(np.float64).eps,
    )
    normalized_span = abs(span) / max(block_sd or 0.0, floor)
    nonstationary = (
        z_score is not None
        and z_score > policy.trend_z_threshold
        and normalized_span > policy.normalized_span_threshold
    )
    return ObservableStationarityDiagnostic(
        observable_name=name,
        role=role,
        units=units,
        frame_start=frame_start,
        frame_stop=frame_stop,
        block_count=int(block_means.size),
        mean=mean,
        standard_deviation=sd,
        block_standard_deviation=block_sd,
        integrated_autocorrelation_time_frames=tau,
        slope_per_ps=float(slope),
        slope_standard_error_per_ps=slope_se,
        slope_z_score=z_score,
        observation_span_change=span,
        normalized_span_change=normalized_span,
        status=(
            ObservableStationarityStatus.NONSTATIONARY
            if nonstationary
            else ObservableStationarityStatus.STATIONARY
        ),
    )


def assess_production_regimes(
    collection: AtomisticFrameCollection,
    *,
    energy_catalog: FrameEnergyCatalog,
    simulation_control_certificate: SimulationControlCertificate,
    trajectory_quality_verdict: TrajectoryQualityVerdict,
    source_identity_signature: str,
    policy: ProductionWindowPolicy | None = None,
    external_candidate_boundaries: Sequence[int] = (),
) -> ProductionRegimeCatalog:
    """Build a source-observable, selection-aware production-regime catalog."""

    collection.require_trajectory("Stage 11E-STAT1 production-regime assessment")
    times = collection.require_time_axis("Stage 11E-STAT1 production-regime assessment")
    if collection.n_frames != energy_catalog.frame_count:
        raise SourceControlError("Energy catalog and trajectory frame counts differ.")
    if source_identity_signature != trajectory_quality_verdict.source_identity_signature:
        raise SourceControlError("STAT1 source identity does not match the STAT0 verdict.")
    if simulation_control_certificate.signature != trajectory_quality_verdict.simulation_control_certificate_signature:
        raise SourceControlError("STAT1 control certificate does not match the STAT0 verdict.")

    active_policy = policy or ProductionWindowPolicy()
    observables = _source_observables(
        collection, trajectory_quality_verdict, energy_catalog, simulation_control_certificate
    )
    partition = _make_partition(
        collection=collection,
        observables=observables,
        source_identity_signature=source_identity_signature,
        quality_verdict=trajectory_quality_verdict,
        policy=active_policy,
    )
    change_points = _detect_change_points(
        partition=partition,
        observables=observables,
        policy=active_policy,
        external_candidate_boundaries=external_candidate_boundaries,
    )
    supported_external_blocks = tuple(
        item.nearest_block_index
        for item in change_points.external_boundaries
        if item.status is ExternalBoundaryStatus.SUPPORTED
        and item.nearest_block_index not in (None, 0, len(partition.block_boundaries))
    )
    combined_boundaries = tuple(sorted(set(change_points.block_indices + supported_external_blocks)))
    block_edges = (0, *combined_boundaries, len(partition.block_boundaries))
    regimes: list[ProductionRegime] = []
    if supported_external_blocks or any(item.status is ExternalBoundaryStatus.SOURCE_EDGE for item in change_points.external_boundaries):
        selection_status = SelectionConditioningStatus.EXTERNALLY_BOUNDED_TESTED
    elif change_points.block_indices:
        selection_status = SelectionConditioningStatus.SELECTION_CONDITIONED
    else:
        selection_status = SelectionConditioningStatus.FULL_SOURCE
    for index, (block_start, block_stop) in enumerate(zip(block_edges[:-1], block_edges[1:])):
        frame_start = partition.block_boundaries[block_start][0]
        frame_stop = partition.block_boundaries[block_stop - 1][1]
        diagnostics = tuple(
            _observable_diagnostic(
                name=name,
                values=values,
                units=units,
                role=role,
                frame_start=frame_start,
                frame_stop=frame_stop,
                block_boundaries=partition.block_boundaries,
                times=times,
                policy=active_policy,
            )
            for name, (values, units, role) in sorted(observables.items())
        )
        primary = [
            item
            for item in diagnostics
            if item.role in {"distribution_primary", "cell_primary"}
        ]
        if not primary or any(item.status is ObservableStationarityStatus.INSUFFICIENT for item in primary):
            stationarity = RegimeStationarityStatus.INSUFFICIENT
        else:
            stationary_fraction = sum(
                item.status is ObservableStationarityStatus.STATIONARY for item in primary
            ) / len(primary)
            if stationary_fraction == 1.0:
                stationarity = RegimeStationarityStatus.SUPPORTED
            elif stationary_fraction >= active_policy.stationary_primary_fraction:
                stationarity = RegimeStationarityStatus.AMBIGUOUS
            else:
                finite_spans = [
                    item.normalized_span_change
                    for item in primary
                    if item.normalized_span_change is not None
                ]
                stationarity = (
                    RegimeStationarityStatus.AMBIGUOUS
                    if finite_spans
                    and max(finite_spans) <= active_policy.ambiguous_normalized_span_threshold
                    else RegimeStationarityStatus.REJECTED
                )

        if len(block_edges) == 2:
            thermalization = (
                ThermalizationEvidenceStatus.INSUFFICIENT
                if stationarity is RegimeStationarityStatus.INSUFFICIENT
                else ThermalizationEvidenceStatus.NO_DETECTED_TRANSIENT
            )
        elif index == 0 and frame_stop / collection.n_frames <= active_policy.early_transient_fraction:
            thermalization = ThermalizationEvidenceStatus.TRANSIENT_DETECTED
        else:
            thermalization = (
                ThermalizationEvidenceStatus.NO_DETECTED_TRANSIENT
                if stationarity is RegimeStationarityStatus.SUPPORTED
                else ThermalizationEvidenceStatus.AMBIGUOUS
            )

        if trajectory_quality_verdict.outcome is TrajectoryQualityOutcome.UNQUALIFIED:
            interval_status = ProductionIntervalStatus.REJECTED
        elif stationarity is RegimeStationarityStatus.SUPPORTED:
            interval_status = ProductionIntervalStatus.SCIENTIFIC_CANDIDATE
        elif stationarity is RegimeStationarityStatus.INSUFFICIENT:
            interval_status = ProductionIntervalStatus.INSUFFICIENT
        elif stationarity is RegimeStationarityStatus.AMBIGUOUS:
            interval_status = ProductionIntervalStatus.DIAGNOSTIC_ONLY
        else:
            interval_status = ProductionIntervalStatus.REJECTED
        scientific = interval_status is ProductionIntervalStatus.SCIENTIFIC_CANDIDATE
        regimes.append(
            ProductionRegime(
                regime_id=f"regime_{index:03d}",
                frame_start=frame_start,
                frame_stop=frame_stop,
                time_start_ps=float(times[frame_start]),
                time_stop_ps=float(times[frame_stop - 1]),
                block_start=block_start,
                block_stop=block_stop,
                diagnostics=diagnostics,
                thermalization_status=thermalization,
                stationarity_status=stationarity,
                production_interval_status=interval_status,
                selection_conditioning_status=selection_status,
                quality_outcome=trajectory_quality_verdict.outcome,
                scientific_use_permitted=scientific,
                notes=(
                    "STAT0 quality flags remain attached and are not repaired by STAT1.",
                ),
            )
        )
    selected = tuple(
        regime.regime_id for regime in regimes if regime.scientific_use_permitted
    )
    if selected:
        overall = ProductionCatalogStatus.ACCEPTED
    elif any(
        regime.production_interval_status is ProductionIntervalStatus.DIAGNOSTIC_ONLY
        for regime in regimes
    ):
        overall = ProductionCatalogStatus.DIAGNOSTIC_ONLY
    elif any(
        regime.production_interval_status is ProductionIntervalStatus.INSUFFICIENT
        for regime in regimes
    ):
        overall = ProductionCatalogStatus.INSUFFICIENT
    else:
        overall = ProductionCatalogStatus.REJECTED
    return ProductionRegimeCatalog(
        source_identity_signature=source_identity_signature,
        simulation_control_certificate_signature=simulation_control_certificate.signature,
        trajectory_quality_verdict_signature=trajectory_quality_verdict.signature,
        policy_signature=active_policy.signature,
        block_partition=partition,
        change_points=change_points,
        regimes=tuple(regimes),
        selected_regime_ids=selected,
        overall_status=overall,
        notes=(
            "Adaptive site density was not used to select production regimes.",
            "Scientific downstream methods must apply their own ensemble-specific admissibility gates.",
        ),
    )


__all__ = [
    "PRODUCTION_WINDOW_POLICY_SCHEMA",
    "QUALITY_DIAGNOSTIC_BLOCK_PARTITION_SCHEMA",
    "OBSERVABLE_STATIONARITY_DIAGNOSTIC_SCHEMA",
    "CHANGE_POINT_CATALOG_SCHEMA",
    "EXTERNAL_BOUNDARY_ASSESSMENT_SCHEMA",
    "PRODUCTION_REGIME_SCHEMA",
    "PRODUCTION_REGIME_CATALOG_SCHEMA",
    "PRODUCTION_WINDOW_POLICY_VERSION",
    "ObservableStationarityStatus",
    "ThermalizationEvidenceStatus",
    "RegimeStationarityStatus",
    "ProductionIntervalStatus",
    "SelectionConditioningStatus",
    "ProductionCatalogStatus",
    "ChangePointStatus",
    "ExternalBoundaryStatus",
    "ProductionWindowPolicy",
    "QualityDiagnosticBlockPartition",
    "ObservableStationarityDiagnostic",
    "ExternalBoundaryAssessment",
    "ChangePointCatalog",
    "ProductionRegime",
    "ProductionRegimeCatalog",
    "assess_production_regimes",
]
