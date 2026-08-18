"""Stage 11E-STAT0 ionic-temperature and trajectory-quality assessment."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping, Sequence
import warnings

import numpy as np
from ase.neighborlist import primitive_neighbor_list
from scipy.stats import t as student_t

from ..collection import AtomisticFrameCollection
from ..exceptions import FrameCollectionError
from .control_certificates import EnsembleKind, SimulationControlCertificate
from .source_controls import (
    FrameEnergyCatalog,
    NumericalMDQualityControls,
    SourceControlError,
    SourceControlSerializationError,
)

BOLTZMANN_CONSTANT_EV_PER_K = 8.617333262145e-5
TRAJECTORY_QUALITY_POLICY_SCHEMA = "mdstats.trajectory-quality-policy.v1"
IONIC_TEMPERATURE_DEFINITION_SCHEMA = "mdstats.ionic-temperature-definition.v1"
IONIC_TEMPERATURE_STATISTICS_SCHEMA = "mdstats.ionic-temperature-statistics.v1"
ENERGY_CONSERVATION_STATISTICS_SCHEMA = "mdstats.energy-conservation-statistics.v1"
TRAJECTORY_QUALITY_CHECK_SCHEMA = "mdstats.trajectory-quality-check.v1"
REALIZED_ENSEMBLE_CONSISTENCY_SCHEMA = "mdstats.realized-ensemble-consistency.v1"
TRAJECTORY_QUALITY_VERDICT_SCHEMA = "mdstats.trajectory-quality-verdict.v1"
TRAJECTORY_QUALITY_POLICY_VERSION = "mdstats.trajectory-quality-policy.2026-07.v2"


class TrajectoryDegradedQualityWarning(UserWarning):
    """Warn that a trajectory remains usable with material quality limitations."""


class TrajectoryIntegrityError(FrameCollectionError):
    """Raised when STAT0 finds catastrophic trajectory-integrity failure."""


class TrajectoryQualityOutcome(str, Enum):
    STRICTLY_QUALIFIED = "strictly_qualified"
    DEGRADED_QUALITY = "degraded_quality"
    UNQUALIFIED = "unqualified"


class QualityCheckSeverity(str, Enum):
    HARD_INTEGRITY = "hard_integrity"
    SOFT_QUALITY = "soft_quality"
    DIAGNOSTIC = "diagnostic"


class QualityCheckStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    UNAVAILABLE = "unavailable"
    INSUFFICIENT = "insufficient"
    NOT_APPLICABLE = "not_applicable"




class DiagnosticRequirement(str, Enum):
    HARD_INTEGRITY_REQUIRED = "hard_integrity_required"
    VERDICT_CRITICAL = "verdict_critical"
    METHOD_SPECIFIC = "method_specific"
    OPTIONAL = "optional"


class RealizedEnsembleConsistencyStatus(str, Enum):
    CONSISTENT = "consistent"
    DEGRADED = "degraded"
    INSUFFICIENT = "insufficient"
    INCONSISTENT = "inconsistent"


class TemperatureStabilityStatus(str, Enum):
    STABLE = "stable"
    DRIFTING = "drifting"
    INSUFFICIENT = "insufficient"
    UNAVAILABLE = "unavailable"


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


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SourceControlError("Quality records cannot serialize non-finite values.")
        return value
    if isinstance(value, np.generic):
        return _json_value(value.item())
    if isinstance(value, Mapping):
        return {str(k): _json_value(v) for k, v in sorted(value.items())}
    if isinstance(value, (tuple, list, np.ndarray)):
        return [_json_value(v) for v in value]
    return str(value)


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None


@dataclass(frozen=True, slots=True)
class TrajectoryQualityPolicy:
    """Versioned thresholds for the first STAT0 implementation."""

    policy_version: str = TRAJECTORY_QUALITY_POLICY_VERSION
    confidence_level: float = 0.95
    minimum_independent_blocks: int = 4
    minimum_block_frames: int = 16
    strict_ediff_ev: float = 1.0e-6
    warning_ediff_ev: float = 1.0e-4
    strict_nve_drift_ev_per_atom_ps: float = 1.0e-3
    catastrophic_nve_drift_ev_per_atom_ps: float = 2.6e-2
    catastrophic_energy_jump_ev_per_atom: float = 1.0
    catastrophic_force_norm_ev_per_angstrom: float = 100.0
    catastrophic_speed_angstrom_per_ps: float = 1000.0
    catastrophic_overlap_angstrom: float = 0.35
    temperature_ci_half_width_kelvin: float = 5.0
    temperature_ci_relative_fraction: float = 0.05
    temperature_span_drift_kelvin: float = 5.0
    temperature_span_drift_sd_fraction: float = 0.5
    target_temperature_relative_tolerance: float = 0.10
    target_temperature_absolute_tolerance_kelvin: float = 20.0
    strict_potim_fs_heavy_atoms: float = 2.0
    strict_potim_fs_hydrogen: float = 0.5
    total_energy_identity_tolerance_ev_per_atom: float = 1.0e-8
    strict_fixed_cell_relative_deviation: float = 1.0e-10
    inactive_thermostat_energy_tolerance_ev: float = 1.0e-8
    nve_hard_reference_temperature_kelvin: float = 300.0
    nve_hard_reference_time_ps: float = 1.0

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SourceControlError("Trajectory quality policy version is required.")
        if not 0.0 < self.confidence_level < 1.0:
            raise SourceControlError("confidence_level must lie between zero and one.")
        if self.minimum_independent_blocks < 2 or self.minimum_block_frames < 2:
            raise SourceControlError("Block requirements must be at least two.")
        for name, value in self._payload().items():
            if name in {"schema", "policy_version", "minimum_independent_blocks", "minimum_block_frames"}:
                continue
            if isinstance(value, (int, float)) and value < 0:
                raise SourceControlError(f"Policy value {name} must be nonnegative.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAJECTORY_QUALITY_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "confidence_level": self.confidence_level,
            "minimum_independent_blocks": self.minimum_independent_blocks,
            "minimum_block_frames": self.minimum_block_frames,
            "strict_ediff_ev": self.strict_ediff_ev,
            "warning_ediff_ev": self.warning_ediff_ev,
            "strict_nve_drift_ev_per_atom_ps": self.strict_nve_drift_ev_per_atom_ps,
            "catastrophic_nve_drift_ev_per_atom_ps": self.catastrophic_nve_drift_ev_per_atom_ps,
            "catastrophic_energy_jump_ev_per_atom": self.catastrophic_energy_jump_ev_per_atom,
            "catastrophic_force_norm_ev_per_angstrom": self.catastrophic_force_norm_ev_per_angstrom,
            "catastrophic_speed_angstrom_per_ps": self.catastrophic_speed_angstrom_per_ps,
            "catastrophic_overlap_angstrom": self.catastrophic_overlap_angstrom,
            "temperature_ci_half_width_kelvin": self.temperature_ci_half_width_kelvin,
            "temperature_ci_relative_fraction": self.temperature_ci_relative_fraction,
            "temperature_span_drift_kelvin": self.temperature_span_drift_kelvin,
            "temperature_span_drift_sd_fraction": self.temperature_span_drift_sd_fraction,
            "target_temperature_relative_tolerance": self.target_temperature_relative_tolerance,
            "target_temperature_absolute_tolerance_kelvin": self.target_temperature_absolute_tolerance_kelvin,
            "strict_potim_fs_heavy_atoms": self.strict_potim_fs_heavy_atoms,
            "strict_potim_fs_hydrogen": self.strict_potim_fs_hydrogen,
            "total_energy_identity_tolerance_ev_per_atom": self.total_energy_identity_tolerance_ev_per_atom,
            "strict_fixed_cell_relative_deviation": self.strict_fixed_cell_relative_deviation,
            "inactive_thermostat_energy_tolerance_ev": self.inactive_thermostat_energy_tolerance_ev,
            "nve_hard_reference_temperature_kelvin": self.nve_hard_reference_temperature_kelvin,
            "nve_hard_reference_time_ps": self.nve_hard_reference_time_ps,
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrajectoryQualityPolicy":
        if payload.get("schema") != TRAJECTORY_QUALITY_POLICY_SCHEMA:
            raise SourceControlSerializationError("Unsupported trajectory-quality-policy schema.")
        kwargs = {key: value for key, value in payload.items() if key not in {"schema", "signature"}}
        result = cls(**kwargs)
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Trajectory-quality-policy signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class IonicTemperatureDefinition:
    source_identity_signature: str
    energy_catalog_signature: str
    kinetic_energy_channel: str
    kinetic_energy_source_path: str
    atom_count: int
    active_coordinate_count: int
    fixed_coordinate_count: int
    constraint_count: int
    center_of_mass_translation_removed: bool
    degrees_of_freedom: int
    dof_basis: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.source_identity_signature) != 64 or len(self.energy_catalog_signature) != 64:
            raise SourceControlError("Temperature-definition source signatures must be SHA-256 digests.")
        if self.atom_count < 1 or self.degrees_of_freedom < 1:
            raise SourceControlError("Temperature definition requires positive atom and degree counts.")
        if self.active_coordinate_count < self.degrees_of_freedom:
            raise SourceControlError("Active coordinate count cannot be smaller than degrees of freedom.")
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": IONIC_TEMPERATURE_DEFINITION_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "energy_catalog_signature": self.energy_catalog_signature,
            "kinetic_energy_channel": self.kinetic_energy_channel,
            "kinetic_energy_source_path": self.kinetic_energy_source_path,
            "atom_count": self.atom_count,
            "active_coordinate_count": self.active_coordinate_count,
            "fixed_coordinate_count": self.fixed_coordinate_count,
            "constraint_count": self.constraint_count,
            "center_of_mass_translation_removed": self.center_of_mass_translation_removed,
            "degrees_of_freedom": self.degrees_of_freedom,
            "dof_basis": self.dof_basis,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IonicTemperatureDefinition":
        if payload.get("schema") != IONIC_TEMPERATURE_DEFINITION_SCHEMA:
            raise SourceControlSerializationError("Unsupported ionic-temperature-definition schema.")
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            energy_catalog_signature=str(payload["energy_catalog_signature"]),
            kinetic_energy_channel=str(payload["kinetic_energy_channel"]),
            kinetic_energy_source_path=str(payload["kinetic_energy_source_path"]),
            atom_count=int(payload["atom_count"]),
            active_coordinate_count=int(payload["active_coordinate_count"]),
            fixed_coordinate_count=int(payload["fixed_coordinate_count"]),
            constraint_count=int(payload["constraint_count"]),
            center_of_mass_translation_removed=bool(payload["center_of_mass_translation_removed"]),
            degrees_of_freedom=int(payload["degrees_of_freedom"]),
            dof_basis=str(payload["dof_basis"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Ionic-temperature-definition signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class IonicTemperatureStatistics:
    definition_signature: str
    temperatures_kelvin: tuple[float, ...]
    represented_time_mean_kelvin: float
    represented_time_standard_deviation_kelvin: float
    minimum_kelvin: float
    maximum_kelvin: float
    integrated_autocorrelation_time_frames: float
    effective_sample_count: float
    block_length_frames: int
    block_means_kelvin: tuple[float, ...]
    mean_standard_error_kelvin: float | None
    confidence_level: float
    mean_confidence_interval_kelvin: tuple[float, float] | None
    drift_kelvin_per_ps: float | None
    drift_confidence_interval_kelvin_per_ps: tuple[float, float] | None
    observation_span_change_kelvin: float | None
    stability_status: TemperatureStabilityStatus

    def __post_init__(self) -> None:
        if len(self.definition_signature) != 64:
            raise SourceControlError("Temperature statistics require a definition signature.")
        values = tuple(float(value) for value in self.temperatures_kelvin)
        if not values or not all(math.isfinite(value) for value in values):
            raise SourceControlError("Temperature statistics require finite samples.")
        object.__setattr__(self, "temperatures_kelvin", values)
        object.__setattr__(self, "block_means_kelvin", tuple(float(value) for value in self.block_means_kelvin))
        object.__setattr__(self, "stability_status", TemperatureStabilityStatus(self.stability_status))

    def _payload(self, *, include_series: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": IONIC_TEMPERATURE_STATISTICS_SCHEMA,
            "definition_signature": self.definition_signature,
            "represented_time_mean_kelvin": self.represented_time_mean_kelvin,
            "represented_time_standard_deviation_kelvin": self.represented_time_standard_deviation_kelvin,
            "minimum_kelvin": self.minimum_kelvin,
            "maximum_kelvin": self.maximum_kelvin,
            "integrated_autocorrelation_time_frames": self.integrated_autocorrelation_time_frames,
            "effective_sample_count": self.effective_sample_count,
            "block_length_frames": self.block_length_frames,
            "block_means_kelvin": list(self.block_means_kelvin),
            "mean_standard_error_kelvin": self.mean_standard_error_kelvin,
            "confidence_level": self.confidence_level,
            "mean_confidence_interval_kelvin": None if self.mean_confidence_interval_kelvin is None else list(self.mean_confidence_interval_kelvin),
            "drift_kelvin_per_ps": self.drift_kelvin_per_ps,
            "drift_confidence_interval_kelvin_per_ps": None if self.drift_confidence_interval_kelvin_per_ps is None else list(self.drift_confidence_interval_kelvin_per_ps),
            "observation_span_change_kelvin": self.observation_span_change_kelvin,
            "stability_status": self.stability_status.value,
            "temperature_series_sha256": _digest(list(self.temperatures_kelvin)),
        }
        if include_series:
            payload["temperatures_kelvin"] = list(self.temperatures_kelvin)
        return payload

    @property
    def signature(self) -> str:
        return _digest(self._payload(include_series=False))

    def to_dict(self, *, include_series: bool = True) -> dict[str, Any]:
        return {**self._payload(include_series=include_series), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "IonicTemperatureStatistics":
        if payload.get("schema") != IONIC_TEMPERATURE_STATISTICS_SCHEMA:
            raise SourceControlSerializationError("Unsupported ionic-temperature-statistics schema.")
        if "temperatures_kelvin" not in payload:
            raise SourceControlSerializationError("Temperature reconstruction requires the series.")
        result = cls(
            definition_signature=str(payload["definition_signature"]),
            temperatures_kelvin=tuple(float(value) for value in payload["temperatures_kelvin"]),
            represented_time_mean_kelvin=float(payload["represented_time_mean_kelvin"]),
            represented_time_standard_deviation_kelvin=float(payload["represented_time_standard_deviation_kelvin"]),
            minimum_kelvin=float(payload["minimum_kelvin"]),
            maximum_kelvin=float(payload["maximum_kelvin"]),
            integrated_autocorrelation_time_frames=float(payload["integrated_autocorrelation_time_frames"]),
            effective_sample_count=float(payload["effective_sample_count"]),
            block_length_frames=int(payload["block_length_frames"]),
            block_means_kelvin=tuple(float(value) for value in payload.get("block_means_kelvin", ())),
            mean_standard_error_kelvin=_float_or_none(payload.get("mean_standard_error_kelvin")),
            confidence_level=float(payload["confidence_level"]),
            mean_confidence_interval_kelvin=None if payload.get("mean_confidence_interval_kelvin") is None else tuple(float(value) for value in payload["mean_confidence_interval_kelvin"]),
            drift_kelvin_per_ps=_float_or_none(payload.get("drift_kelvin_per_ps")),
            drift_confidence_interval_kelvin_per_ps=None if payload.get("drift_confidence_interval_kelvin_per_ps") is None else tuple(float(value) for value in payload["drift_confidence_interval_kelvin_per_ps"]),
            observation_span_change_kelvin=_float_or_none(payload.get("observation_span_change_kelvin")),
            stability_status=TemperatureStabilityStatus(payload["stability_status"]),
        )
        if payload.get("temperature_series_sha256") not in (None, _digest(list(result.temperatures_kelvin))):
            raise SourceControlSerializationError("Temperature-series digest mismatch.")
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Ionic-temperature-statistics signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class EnergyConservationStatistics:
    ensemble: EnsembleKind
    source_channel: str | None
    frame_count: int
    initial_ev: float | None
    final_ev: float | None
    mean_ev: float | None
    standard_deviation_ev: float | None
    drift_ev_per_ps: float | None
    drift_ev_per_atom_ps: float | None
    observation_span_change_ev: float | None
    detrended_standard_deviation_ev: float | None
    maximum_step_jump_ev: float | None
    maximum_step_jump_ev_per_atom: float | None
    identity_residual_max_ev: float | None
    status: QualityCheckStatus
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "ensemble", EnsembleKind(self.ensemble))
        object.__setattr__(self, "status", QualityCheckStatus(self.status))
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ENERGY_CONSERVATION_STATISTICS_SCHEMA,
            "ensemble": self.ensemble.value,
            "source_channel": self.source_channel,
            "frame_count": self.frame_count,
            "initial_ev": self.initial_ev,
            "final_ev": self.final_ev,
            "mean_ev": self.mean_ev,
            "standard_deviation_ev": self.standard_deviation_ev,
            "drift_ev_per_ps": self.drift_ev_per_ps,
            "drift_ev_per_atom_ps": self.drift_ev_per_atom_ps,
            "observation_span_change_ev": self.observation_span_change_ev,
            "detrended_standard_deviation_ev": self.detrended_standard_deviation_ev,
            "maximum_step_jump_ev": self.maximum_step_jump_ev,
            "maximum_step_jump_ev_per_atom": self.maximum_step_jump_ev_per_atom,
            "identity_residual_max_ev": self.identity_residual_max_ev,
            "status": self.status.value,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EnergyConservationStatistics":
        if payload.get("schema") != ENERGY_CONSERVATION_STATISTICS_SCHEMA:
            raise SourceControlSerializationError("Unsupported energy-conservation schema.")
        result = cls(
            ensemble=EnsembleKind(payload["ensemble"]),
            source_channel=None if payload.get("source_channel") is None else str(payload["source_channel"]),
            frame_count=int(payload["frame_count"]),
            initial_ev=_float_or_none(payload.get("initial_ev")),
            final_ev=_float_or_none(payload.get("final_ev")),
            mean_ev=_float_or_none(payload.get("mean_ev")),
            standard_deviation_ev=_float_or_none(payload.get("standard_deviation_ev")),
            drift_ev_per_ps=_float_or_none(payload.get("drift_ev_per_ps")),
            drift_ev_per_atom_ps=_float_or_none(payload.get("drift_ev_per_atom_ps")),
            observation_span_change_ev=_float_or_none(payload.get("observation_span_change_ev")),
            detrended_standard_deviation_ev=_float_or_none(payload.get("detrended_standard_deviation_ev")),
            maximum_step_jump_ev=_float_or_none(payload.get("maximum_step_jump_ev")),
            maximum_step_jump_ev_per_atom=_float_or_none(payload.get("maximum_step_jump_ev_per_atom")),
            identity_residual_max_ev=_float_or_none(payload.get("identity_residual_max_ev")),
            status=QualityCheckStatus(payload["status"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Energy-conservation signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RealizedEnsembleConsistency:
    source_identity_signature: str
    simulation_control_certificate_signature: str
    control_inferred_ensemble: EnsembleKind
    status: RealizedEnsembleConsistencyStatus
    cell_volume_relative_range: float | None
    cell_matrix_relative_deviation: float | None
    inactive_thermostat_energy_max_abs_ev: float | None
    nve_energy_drift_ev_per_atom_ps: float | None
    evidence: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.source_identity_signature) != 64 or len(self.simulation_control_certificate_signature) != 64:
            raise SourceControlError("Realized-ensemble signatures must be SHA-256 digests.")
        object.__setattr__(self, "control_inferred_ensemble", EnsembleKind(self.control_inferred_ensemble))
        object.__setattr__(self, "status", RealizedEnsembleConsistencyStatus(self.status))
        object.__setattr__(self, "evidence", tuple(str(value) for value in self.evidence))
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REALIZED_ENSEMBLE_CONSISTENCY_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "simulation_control_certificate_signature": self.simulation_control_certificate_signature,
            "control_inferred_ensemble": self.control_inferred_ensemble.value,
            "status": self.status.value,
            "cell_volume_relative_range": self.cell_volume_relative_range,
            "cell_matrix_relative_deviation": self.cell_matrix_relative_deviation,
            "inactive_thermostat_energy_max_abs_ev": self.inactive_thermostat_energy_max_abs_ev,
            "nve_energy_drift_ev_per_atom_ps": self.nve_energy_drift_ev_per_atom_ps,
            "evidence": list(self.evidence),
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RealizedEnsembleConsistency":
        if payload.get("schema") != REALIZED_ENSEMBLE_CONSISTENCY_SCHEMA:
            raise SourceControlSerializationError("Unsupported realized-ensemble-consistency schema.")
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            simulation_control_certificate_signature=str(payload["simulation_control_certificate_signature"]),
            control_inferred_ensemble=EnsembleKind(payload["control_inferred_ensemble"]),
            status=RealizedEnsembleConsistencyStatus(payload["status"]),
            cell_volume_relative_range=_float_or_none(payload.get("cell_volume_relative_range")),
            cell_matrix_relative_deviation=_float_or_none(payload.get("cell_matrix_relative_deviation")),
            inactive_thermostat_energy_max_abs_ev=_float_or_none(payload.get("inactive_thermostat_energy_max_abs_ev")),
            nve_energy_drift_ev_per_atom_ps=_float_or_none(payload.get("nve_energy_drift_ev_per_atom_ps")),
            evidence=tuple(str(value) for value in payload.get("evidence", ())),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Realized-ensemble-consistency signature mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrajectoryQualityCheck:
    check_id: str
    severity: QualityCheckSeverity
    status: QualityCheckStatus
    requirement: DiagnosticRequirement = DiagnosticRequirement.VERDICT_CRITICAL
    measured_value: Any = None
    threshold: Any = None
    units: str | None = None
    message: str = ""
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.check_id:
            raise SourceControlError("Quality check id must be non-empty.")
        object.__setattr__(self, "severity", QualityCheckSeverity(self.severity))
        object.__setattr__(self, "status", QualityCheckStatus(self.status))
        object.__setattr__(self, "requirement", DiagnosticRequirement(self.requirement))
        object.__setattr__(self, "evidence", tuple(str(value) for value in self.evidence))

    @property
    def is_material(self) -> bool:
        return self.severity is not QualityCheckSeverity.DIAGNOSTIC and self.status in {
            QualityCheckStatus.FAIL,
            QualityCheckStatus.WARNING,
            QualityCheckStatus.INSUFFICIENT,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRAJECTORY_QUALITY_CHECK_SCHEMA,
            "check_id": self.check_id,
            "severity": self.severity.value,
            "status": self.status.value,
            "requirement": self.requirement.value,
            "measured_value": _json_value(self.measured_value),
            "threshold": _json_value(self.threshold),
            "units": self.units,
            "message": self.message,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrajectoryQualityCheck":
        return cls(
            check_id=str(payload["check_id"]),
            severity=QualityCheckSeverity(payload["severity"]),
            status=QualityCheckStatus(payload["status"]),
            requirement=DiagnosticRequirement(payload.get("requirement", "verdict_critical")),
            measured_value=payload.get("measured_value"),
            threshold=payload.get("threshold"),
            units=None if payload.get("units") is None else str(payload["units"]),
            message=str(payload.get("message", "")),
            evidence=tuple(str(value) for value in payload.get("evidence", ())),
        )


@dataclass(frozen=True, slots=True)
class TrajectoryQualityVerdict:
    source_identity_signature: str
    simulation_control_certificate_signature: str
    numerical_quality_controls_signature: str
    energy_catalog_signature: str
    policy_signature: str
    outcome: TrajectoryQualityOutcome
    temperature_definition: IonicTemperatureDefinition | None
    temperature_statistics: IonicTemperatureStatistics | None
    energy_conservation: EnergyConservationStatistics
    realized_ensemble_consistency: RealizedEnsembleConsistency
    checks: tuple[TrajectoryQualityCheck, ...]
    degraded_reasons: tuple[str, ...] = ()
    unqualified_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_identity_signature",
            "simulation_control_certificate_signature",
            "numerical_quality_controls_signature",
            "energy_catalog_signature",
            "policy_signature",
        ):
            if len(getattr(self, name)) != 64:
                raise SourceControlError(f"{name} must be a SHA-256 digest.")
        object.__setattr__(self, "outcome", TrajectoryQualityOutcome(self.outcome))
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "degraded_reasons", tuple(str(value) for value in self.degraded_reasons))
        object.__setattr__(self, "unqualified_reasons", tuple(str(value) for value in self.unqualified_reasons))

    @property
    def analysis_may_continue(self) -> bool:
        return self.outcome is not TrajectoryQualityOutcome.UNQUALIFIED

    def _payload(self, *, include_series: bool = True) -> dict[str, Any]:
        return {
            "schema": TRAJECTORY_QUALITY_VERDICT_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "simulation_control_certificate_signature": self.simulation_control_certificate_signature,
            "numerical_quality_controls_signature": self.numerical_quality_controls_signature,
            "energy_catalog_signature": self.energy_catalog_signature,
            "policy_signature": self.policy_signature,
            "outcome": self.outcome.value,
            "temperature_definition": None if self.temperature_definition is None else self.temperature_definition.to_dict(),
            "temperature_statistics": None if self.temperature_statistics is None else self.temperature_statistics.to_dict(include_series=include_series),
            "energy_conservation": self.energy_conservation.to_dict(),
            "realized_ensemble_consistency": self.realized_ensemble_consistency.to_dict(),
            "checks": [check.to_dict() for check in self.checks],
            "degraded_reasons": list(self.degraded_reasons),
            "unqualified_reasons": list(self.unqualified_reasons),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload(include_series=False))

    def to_dict(self, *, include_series: bool = True) -> dict[str, Any]:
        return {**self._payload(include_series=include_series), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrajectoryQualityVerdict":
        if payload.get("schema") != TRAJECTORY_QUALITY_VERDICT_SCHEMA:
            raise SourceControlSerializationError("Unsupported trajectory-quality-verdict schema.")
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            simulation_control_certificate_signature=str(payload["simulation_control_certificate_signature"]),
            numerical_quality_controls_signature=str(payload["numerical_quality_controls_signature"]),
            energy_catalog_signature=str(payload["energy_catalog_signature"]),
            policy_signature=str(payload["policy_signature"]),
            outcome=TrajectoryQualityOutcome(payload["outcome"]),
            temperature_definition=None if payload.get("temperature_definition") is None else IonicTemperatureDefinition.from_dict(payload["temperature_definition"]),
            temperature_statistics=None if payload.get("temperature_statistics") is None else IonicTemperatureStatistics.from_dict(payload["temperature_statistics"]),
            energy_conservation=EnergyConservationStatistics.from_dict(payload["energy_conservation"]),
            realized_ensemble_consistency=RealizedEnsembleConsistency.from_dict(payload["realized_ensemble_consistency"]),
            checks=tuple(TrajectoryQualityCheck.from_dict(item) for item in payload.get("checks", ())),
            degraded_reasons=tuple(str(value) for value in payload.get("degraded_reasons", ())),
            unqualified_reasons=tuple(str(value) for value in payload.get("unqualified_reasons", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError("Trajectory-quality-verdict signature mismatch.")
        return result


def _represented_time_weights(times: np.ndarray) -> np.ndarray:
    n = times.size
    if n == 1:
        return np.ones(1, dtype=np.float64)
    dt = np.diff(times)
    weights = np.empty(n, dtype=np.float64)
    weights[0] = 0.5 * dt[0]
    weights[-1] = 0.5 * dt[-1]
    if n > 2:
        weights[1:-1] = 0.5 * (dt[:-1] + dt[1:])
    if not np.all(weights > 0.0):
        return np.ones(n, dtype=np.float64)
    return weights


def _autocorrelation_time(values: np.ndarray) -> float:
    n = values.size
    if n < 3:
        return 0.5
    centered = values - np.mean(values)
    variance = float(np.dot(centered, centered) / n)
    if variance <= np.finfo(np.float64).eps:
        return 0.5
    size = 1 << (2 * n - 1).bit_length()
    transformed = np.fft.rfft(centered, n=size)
    acov = np.fft.irfft(transformed * np.conjugate(transformed), n=size)[:n]
    acov /= np.arange(n, 0, -1, dtype=np.float64)
    rho = acov / acov[0]
    tau = 0.5
    index = 1
    while index < n:
        if index + 1 < n:
            pair = float(rho[index] + rho[index + 1])
            if pair <= 0.0:
                break
            tau += pair
            index += 2
        else:
            if rho[index] <= 0.0:
                break
            tau += float(rho[index])
            index += 1
    return max(0.5, min(float(tau), 0.5 * n))


def _block_statistics(
    values: np.ndarray,
    times: np.ndarray,
    *,
    tau_frames: float,
    policy: TrajectoryQualityPolicy,
) -> tuple[int, np.ndarray, np.ndarray, float | None, tuple[float, float] | None, float | None, tuple[float, float] | None]:
    block_length = max(policy.minimum_block_frames, int(math.ceil(2.0 * tau_frames)))
    block_count = values.size // block_length
    if block_count < 2:
        return block_length, np.empty(0), np.empty(0), None, None, None, None
    used = block_count * block_length
    block_values = values[:used].reshape(block_count, block_length).mean(axis=1)
    block_times = times[:used].reshape(block_count, block_length).mean(axis=1)
    standard_error = float(np.std(block_values, ddof=1) / math.sqrt(block_count))
    alpha = 1.0 - policy.confidence_level
    critical = float(student_t.ppf(1.0 - alpha / 2.0, df=block_count - 1))
    mean_value = float(np.mean(block_values))
    mean_ci = (mean_value - critical * standard_error, mean_value + critical * standard_error)
    if block_count < 3 or np.ptp(block_times) <= 0.0:
        return block_length, block_values, block_times, standard_error, mean_ci, None, None
    design = np.column_stack([block_times, np.ones(block_count)])
    slope, intercept = np.linalg.lstsq(design, block_values, rcond=None)[0]
    residual = block_values - (slope * block_times + intercept)
    dof = block_count - 2
    if dof <= 0:
        return block_length, block_values, block_times, standard_error, mean_ci, float(slope), None
    s2 = float(np.dot(residual, residual) / dof)
    denominator = float(np.sum((block_times - np.mean(block_times)) ** 2))
    if denominator <= 0.0:
        return block_length, block_values, block_times, standard_error, mean_ci, float(slope), None
    slope_se = math.sqrt(s2 / denominator)
    critical_slope = float(student_t.ppf(1.0 - alpha / 2.0, df=dof))
    slope_ci = (float(slope - critical_slope * slope_se), float(slope + critical_slope * slope_se))
    return block_length, block_values, block_times, standard_error, mean_ci, float(slope), slope_ci


def _temperature_definition(
    *,
    collection: AtomisticFrameCollection,
    energy_catalog: FrameEnergyCatalog,
    source_identity_signature: str,
    control_certificate: SimulationControlCertificate,
) -> IonicTemperatureDefinition | None:
    channel = energy_catalog.channel("kinetic")
    if channel is None or not channel.complete:
        return None
    active_coordinates = 3 * collection.n_atoms
    constraint_count = 0
    fixed_coordinates = 0
    notes: list[str] = []
    if control_certificate.constraints.active is True:
        statuses = control_certificate.constraints.parameter("iconst_statuses", ())
        constraint_count = sum(1 for value in statuses if int(value) == 0)
        notes.append("Bound ICONST statuses were used for the constraint count.")
    elif control_certificate.constraints.status.value == "unresolved":
        notes.append("No bound constraint count was available; VASP periodic default was used.")
    remove_com = bool(np.all(collection.pbc) and collection.n_atoms > 1)
    dof = active_coordinates - fixed_coordinates - constraint_count - (3 if remove_com else 0)
    if dof < 1:
        return None
    return IonicTemperatureDefinition(
        source_identity_signature=source_identity_signature,
        energy_catalog_signature=energy_catalog.signature,
        kinetic_energy_channel=channel.source_name,
        kinetic_energy_source_path=channel.source_path,
        atom_count=collection.n_atoms,
        active_coordinate_count=active_coordinates,
        fixed_coordinate_count=fixed_coordinates,
        constraint_count=constraint_count,
        center_of_mass_translation_removed=remove_com,
        degrees_of_freedom=dof,
        dof_basis=("periodic_vasp_3N_minus_3" if remove_com and constraint_count == 0 else "active_coordinates_minus_constraints"),
        notes=tuple(notes),
    )


def _temperature_statistics(
    definition: IonicTemperatureDefinition,
    energy_catalog: FrameEnergyCatalog,
    times: np.ndarray,
    policy: TrajectoryQualityPolicy,
) -> IonicTemperatureStatistics:
    channel = energy_catalog.channel(definition.kinetic_energy_channel)
    assert channel is not None
    kinetic = channel.as_array()
    temperatures = 2.0 * kinetic / (definition.degrees_of_freedom * BOLTZMANN_CONSTANT_EV_PER_K)
    weights = _represented_time_weights(times)
    weight_sum = float(np.sum(weights))
    mean = float(np.sum(weights * temperatures) / weight_sum)
    variance = float(np.sum(weights * (temperatures - mean) ** 2) / weight_sum)
    sd = math.sqrt(max(0.0, variance))
    tau = _autocorrelation_time(temperatures)
    effective = min(float(temperatures.size), float(temperatures.size / (2.0 * tau)))
    block_length, block_means, _, standard_error, mean_ci, slope, slope_ci = _block_statistics(
        temperatures, times, tau_frames=tau, policy=policy
    )
    span_change = None if slope is None else float(slope * (times[-1] - times[0]))
    if block_means.size < policy.minimum_independent_blocks:
        stability = TemperatureStabilityStatus.INSUFFICIENT
    else:
        allowed_span = max(
            policy.temperature_span_drift_kelvin,
            policy.temperature_span_drift_sd_fraction * sd,
        )
        significant = slope_ci is not None and (slope_ci[0] > 0.0 or slope_ci[1] < 0.0)
        stability = (
            TemperatureStabilityStatus.DRIFTING
            if span_change is not None and significant and abs(span_change) > allowed_span
            else TemperatureStabilityStatus.STABLE
        )
    return IonicTemperatureStatistics(
        definition_signature=definition.signature,
        temperatures_kelvin=tuple(float(value) for value in temperatures),
        represented_time_mean_kelvin=mean,
        represented_time_standard_deviation_kelvin=sd,
        minimum_kelvin=float(np.min(temperatures)),
        maximum_kelvin=float(np.max(temperatures)),
        integrated_autocorrelation_time_frames=tau,
        effective_sample_count=effective,
        block_length_frames=block_length,
        block_means_kelvin=tuple(float(value) for value in block_means),
        mean_standard_error_kelvin=standard_error,
        confidence_level=policy.confidence_level,
        mean_confidence_interval_kelvin=mean_ci,
        drift_kelvin_per_ps=slope,
        drift_confidence_interval_kelvin_per_ps=slope_ci,
        observation_span_change_kelvin=span_change,
        stability_status=stability,
    )


def _energy_conservation(
    *,
    collection: AtomisticFrameCollection,
    energy_catalog: FrameEnergyCatalog,
    control_certificate: SimulationControlCertificate,
    policy: TrajectoryQualityPolicy,
) -> EnergyConservationStatistics:
    if control_certificate.ensemble is not EnsembleKind.NVE:
        return EnergyConservationStatistics(
            ensemble=control_certificate.ensemble,
            source_channel=None,
            frame_count=collection.n_frames,
            initial_ev=None,
            final_ev=None,
            mean_ev=None,
            standard_deviation_ev=None,
            drift_ev_per_ps=None,
            drift_ev_per_atom_ps=None,
            observation_span_change_ev=None,
            detrended_standard_deviation_ev=None,
            maximum_step_jump_ev=None,
            maximum_step_jump_ev_per_atom=None,
            identity_residual_max_ev=None,
            status=QualityCheckStatus.NOT_APPLICABLE,
            notes=("NVE total-energy conservation is not the active ensemble-specific check.",),
        )
    total_channel = energy_catalog.channel("total")
    if total_channel is None or not total_channel.complete or collection.times is None:
        return EnergyConservationStatistics(
            ensemble=control_certificate.ensemble,
            source_channel=None if total_channel is None else total_channel.source_name,
            frame_count=collection.n_frames,
            initial_ev=None,
            final_ev=None,
            mean_ev=None,
            standard_deviation_ev=None,
            drift_ev_per_ps=None,
            drift_ev_per_atom_ps=None,
            observation_span_change_ev=None,
            detrended_standard_deviation_ev=None,
            maximum_step_jump_ev=None,
            maximum_step_jump_ev_per_atom=None,
            identity_residual_max_ev=None,
            status=QualityCheckStatus.UNAVAILABLE,
            notes=("Complete NVE total energy and physical time are required.",),
        )
    values = total_channel.as_array()
    times = collection.times
    if values.size < 2 or np.ptp(times) <= 0.0:
        return EnergyConservationStatistics(
            ensemble=control_certificate.ensemble,
            source_channel=total_channel.source_name,
            frame_count=collection.n_frames,
            initial_ev=float(values[0]),
            final_ev=float(values[-1]),
            mean_ev=float(np.mean(values)),
            standard_deviation_ev=float(np.std(values)),
            drift_ev_per_ps=None,
            drift_ev_per_atom_ps=None,
            observation_span_change_ev=None,
            detrended_standard_deviation_ev=None,
            maximum_step_jump_ev=None,
            maximum_step_jump_ev_per_atom=None,
            identity_residual_max_ev=None,
            status=QualityCheckStatus.INSUFFICIENT,
        )
    design = np.column_stack([times, np.ones(times.size)])
    slope, intercept = np.linalg.lstsq(design, values, rcond=None)[0]
    fitted = slope * times + intercept
    residual = values - fitted
    max_jump = float(np.max(np.abs(np.diff(values))))
    identity_residual: float | None = None
    kinetic = energy_catalog.channel("kinetic")
    electronic = energy_catalog.channel("e_fr_energy")
    if kinetic is not None and electronic is not None and kinetic.complete and electronic.complete:
        identity_residual = float(np.max(np.abs(values - (kinetic.as_array() + electronic.as_array()))))
    drift_per_atom = float(slope / collection.n_atoms)
    status = (
        QualityCheckStatus.PASS
        if abs(drift_per_atom) <= policy.strict_nve_drift_ev_per_atom_ps
        else QualityCheckStatus.WARNING
    )
    return EnergyConservationStatistics(
        ensemble=control_certificate.ensemble,
        source_channel=total_channel.source_name,
        frame_count=values.size,
        initial_ev=float(values[0]),
        final_ev=float(values[-1]),
        mean_ev=float(np.mean(values)),
        standard_deviation_ev=float(np.std(values)),
        drift_ev_per_ps=float(slope),
        drift_ev_per_atom_ps=drift_per_atom,
        observation_span_change_ev=float(slope * (times[-1] - times[0])),
        detrended_standard_deviation_ev=float(np.std(residual)),
        maximum_step_jump_ev=max_jump,
        maximum_step_jump_ev_per_atom=max_jump / collection.n_atoms,
        identity_residual_max_ev=identity_residual,
        status=status,
    )


def _catastrophic_overlap_distance(
    collection: AtomisticFrameCollection, cutoff: float
) -> float | None:
    positions = collection.get_wrapped_positions()
    for frame_index in range(collection.n_frames):
        distances = primitive_neighbor_list(
            "d",
            collection.pbc,
            collection.cells[frame_index],
            positions[frame_index],
            cutoff,
            self_interaction=False,
            use_scaled_positions=False,
        )
        if distances.size:
            return float(np.min(distances))
    return None


def _target_temperature(control_certificate: SimulationControlCertificate) -> float | None:
    values: list[float] = []
    for name in ("TEBEG", "TEEND", "target_temperature_kelvin"):
        value = control_certificate.thermostat.parameter(name)
        if value is None:
            continue
        try:
            values.append(float(value))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    if max(values) - min(values) > 1.0e-10:
        return None
    return values[0]


def _check(
    check_id: str,
    severity: QualityCheckSeverity,
    status: QualityCheckStatus,
    *,
    requirement: DiagnosticRequirement | None = None,
    measured_value: Any = None,
    threshold: Any = None,
    units: str | None = None,
    message: str = "",
    evidence: Sequence[str] = (),
) -> TrajectoryQualityCheck:
    if requirement is None:
        requirement = {
            QualityCheckSeverity.HARD_INTEGRITY: DiagnosticRequirement.HARD_INTEGRITY_REQUIRED,
            QualityCheckSeverity.SOFT_QUALITY: DiagnosticRequirement.VERDICT_CRITICAL,
            QualityCheckSeverity.DIAGNOSTIC: DiagnosticRequirement.OPTIONAL,
        }[severity]
    return TrajectoryQualityCheck(
        check_id=check_id,
        severity=severity,
        status=status,
        requirement=requirement,
        measured_value=measured_value,
        threshold=threshold,
        units=units,
        message=message,
        evidence=tuple(evidence),
    )


def _realized_ensemble_consistency(
    *,
    collection: AtomisticFrameCollection,
    energy_catalog: FrameEnergyCatalog,
    control_certificate: SimulationControlCertificate,
    energy: EnergyConservationStatistics,
    policy: TrajectoryQualityPolicy,
    source_identity_signature: str,
) -> RealizedEnsembleConsistency:
    volumes = collection.volumes
    volume_mean = float(np.mean(volumes))
    volume_relative_range = None if volume_mean <= 0.0 else float(np.ptp(volumes) / volume_mean)
    reference_cell_norm = float(np.linalg.norm(collection.cells[0]))
    cell_matrix_relative_deviation = (
        None
        if reference_cell_norm <= 0.0
        else float(np.max(np.linalg.norm(collection.cells - collection.cells[0], axis=(1, 2))) / reference_cell_norm)
    )
    thermostat_values: list[np.ndarray] = []
    for channel_name in ("nosepot", "nosekinetic"):
        channel = energy_catalog.channel(channel_name)
        if channel is not None and channel.complete:
            thermostat_values.append(np.abs(channel.as_array()))
    thermostat_max = None if not thermostat_values else float(max(np.max(value) for value in thermostat_values))
    notes: list[str] = []
    evidence: list[str] = [f"control ensemble={control_certificate.ensemble.value}"]
    status = RealizedEnsembleConsistencyStatus.INSUFFICIENT
    if control_certificate.ensemble is EnsembleKind.NVE:
        status = RealizedEnsembleConsistencyStatus.CONSISTENT
        if (
            control_certificate.cell_control.active is False
            and cell_matrix_relative_deviation is not None
            and cell_matrix_relative_deviation > policy.strict_fixed_cell_relative_deviation
        ):
            status = RealizedEnsembleConsistencyStatus.INCONSISTENT
            notes.append("Control-inferred fixed cell conflicts with observed cell-matrix variation.")
        if control_certificate.thermostat.active is False and thermostat_max is not None and thermostat_max > policy.inactive_thermostat_energy_tolerance_ev:
            status = RealizedEnsembleConsistencyStatus.INCONSISTENT
            notes.append("Inactive thermostat conflicts with nonzero thermostat-energy channels.")
        if energy.drift_ev_per_atom_ps is None:
            if status is RealizedEnsembleConsistencyStatus.CONSISTENT:
                status = RealizedEnsembleConsistencyStatus.INSUFFICIENT
            notes.append("NVE conserved-energy drift could not be evaluated.")
        elif abs(energy.drift_ev_per_atom_ps) > policy.catastrophic_nve_drift_ev_per_atom_ps:
            status = RealizedEnsembleConsistencyStatus.INCONSISTENT
        elif abs(energy.drift_ev_per_atom_ps) > policy.strict_nve_drift_ev_per_atom_ps and status is RealizedEnsembleConsistencyStatus.CONSISTENT:
            status = RealizedEnsembleConsistencyStatus.DEGRADED
            notes.append("Observed NVE energy drift exceeds the strict conservation tolerance.")
        evidence.extend(("cell-volume trace", "source total-energy trace"))
    else:
        notes.append("The first realized-consistency implementation is diagnostic-only outside NVE.")
    return RealizedEnsembleConsistency(
        source_identity_signature=source_identity_signature,
        simulation_control_certificate_signature=control_certificate.signature,
        control_inferred_ensemble=control_certificate.ensemble,
        status=status,
        cell_volume_relative_range=volume_relative_range,
        cell_matrix_relative_deviation=cell_matrix_relative_deviation,
        inactive_thermostat_energy_max_abs_ev=thermostat_max,
        nve_energy_drift_ev_per_atom_ps=energy.drift_ev_per_atom_ps,
        evidence=tuple(evidence),
        notes=tuple(notes),
    )


def assess_trajectory_quality(
    collection: AtomisticFrameCollection,
    *,
    energy_catalog: FrameEnergyCatalog,
    numerical_quality_controls: NumericalMDQualityControls,
    simulation_control_certificate: SimulationControlCertificate,
    source_identity_signature: str,
    policy: TrajectoryQualityPolicy | None = None,
    emit_warning: bool = True,
    raise_on_unqualified: bool = True,
) -> TrajectoryQualityVerdict:
    """Evaluate the Stage-11E-STAT0 quality of one complete source segment."""

    active_policy = TrajectoryQualityPolicy() if policy is None else policy
    collection.require_trajectory("trajectory quality assessment")
    if collection.n_frames != energy_catalog.frame_count:
        raise SourceControlError(
            "Trajectory quality requires an energy catalog aligned to the evaluated frames."
        )
    if numerical_quality_controls.present_ionic_steps != collection.n_frames:
        raise SourceControlError(
            "Numerical quality controls must align to the evaluated frame segment."
        )
    if simulation_control_certificate.source_identity_signature != source_identity_signature:
        raise SourceControlError("Control certificate and evaluated source identity differ.")

    checks: list[TrajectoryQualityCheck] = []
    checks.append(_check("integrity.frame_count", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if collection.n_frames > 0 else QualityCheckStatus.FAIL, measured_value=collection.n_frames, threshold=1, units="frames"))
    checks.append(_check("integrity.atom_count", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if collection.n_atoms > 0 else QualityCheckStatus.FAIL, measured_value=collection.n_atoms, threshold=1, units="atoms"))
    checks.append(_check("integrity.positions_complete", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if numerical_quality_controls.positions_complete else QualityCheckStatus.FAIL, measured_value=numerical_quality_controls.positions_complete))
    checks.append(_check("integrity.cells_complete", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if numerical_quality_controls.cells_complete else QualityCheckStatus.FAIL, measured_value=numerical_quality_controls.cells_complete))

    determinants = np.linalg.det(collection.cells)
    checks.append(_check("integrity.positive_cell_determinant", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if np.all(determinants > 1.0e-12) else QualityCheckStatus.FAIL, measured_value=float(np.min(determinants)), threshold=1.0e-12, units="Angstrom^3"))

    times = collection.times
    assert times is not None
    step_uniform = collection.steps is None or collection.steps.size < 3 or np.all(np.diff(collection.steps) == np.diff(collection.steps)[0])
    time_uniform = times.size < 3 or np.allclose(np.diff(times), np.diff(times)[0], rtol=1.0e-10, atol=1.0e-14)
    checks.append(_check("integrity.uniform_frame_axis", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if step_uniform and time_uniform else QualityCheckStatus.FAIL, measured_value={"step_uniform": step_uniform, "time_uniform": time_uniform}))

    overlap_distance = _catastrophic_overlap_distance(
        collection, active_policy.catastrophic_overlap_angstrom
    )
    checks.append(
        _check(
            "integrity.minimum_atomic_distance",
            QualityCheckSeverity.HARD_INTEGRITY,
            QualityCheckStatus.PASS if overlap_distance is None else QualityCheckStatus.FAIL,
            measured_value=(
                {"lower_bound": active_policy.catastrophic_overlap_angstrom}
                if overlap_distance is None
                else overlap_distance
            ),
            threshold=active_policy.catastrophic_overlap_angstrom,
            units="Angstrom",
            message=(
                "No pair was found below the catastrophic-overlap cutoff."
                if overlap_distance is None
                else "At least one pair violates the catastrophic-overlap cutoff."
            ),
        )
    )

    if collection.forces is None:
        checks.append(_check("integrity.maximum_force_norm", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE, message="Force field is unavailable."))
    else:
        max_force = float(np.max(np.linalg.norm(collection.forces, axis=2)))
        checks.append(_check("integrity.maximum_force_norm", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if max_force <= active_policy.catastrophic_force_norm_ev_per_angstrom else QualityCheckStatus.FAIL, measured_value=max_force, threshold=active_policy.catastrophic_force_norm_ev_per_angstrom, units="eV/Angstrom"))

    if collection.velocities is None:
        checks.append(_check("integrity.maximum_speed", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE, message="Velocity field is unavailable."))
    else:
        max_speed = float(np.max(np.linalg.norm(collection.velocities, axis=2)))
        checks.append(_check("integrity.maximum_speed", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if max_speed <= active_policy.catastrophic_speed_angstrom_per_ps else QualityCheckStatus.FAIL, measured_value=max_speed, threshold=active_policy.catastrophic_speed_angstrom_per_ps, units="Angstrom/ps"))

    controls = numerical_quality_controls
    checks.append(
        _check(
            "quality.source_xml_completion",
            QualityCheckSeverity.SOFT_QUALITY,
            QualityCheckStatus.PASS
            if controls.source_parse_complete
            else QualityCheckStatus.WARNING,
            measured_value=controls.source_parse_complete,
            message=(
                "Source XML parsed to its closing root tag."
                if controls.source_parse_complete
                else str(controls.source_parse_warning)
            ),
        )
    )
    if controls.requested_ionic_steps is None:
        checks.append(_check("quality.requested_step_completion", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE))
    else:
        completed = controls.present_ionic_steps >= controls.requested_ionic_steps
        checks.append(_check("quality.requested_step_completion", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if completed else QualityCheckStatus.WARNING, measured_value=controls.present_ionic_steps, threshold=controls.requested_ionic_steps, units="ionic steps"))

    reached = [value for value in controls.scf_iteration_limit_reached if value is not None]
    if not reached:
        checks.append(_check("quality.scf_iteration_limit", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE))
    else:
        fraction = float(np.mean(reached))
        checks.append(_check("quality.scf_iteration_limit", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if fraction == 0.0 else QualityCheckStatus.WARNING, measured_value=fraction, threshold=0.0, units="fraction of ionic steps"))

    if controls.ediff_ev is None:
        checks.append(_check("quality.ediff", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE))
    else:
        if controls.ediff_ev <= active_policy.strict_ediff_ev:
            status = QualityCheckStatus.PASS
        elif controls.ediff_ev <= active_policy.warning_ediff_ev:
            status = QualityCheckStatus.WARNING
        else:
            status = QualityCheckStatus.FAIL
        checks.append(_check("quality.ediff", QualityCheckSeverity.SOFT_QUALITY, status, measured_value=controls.ediff_ev, threshold={"strict": active_policy.strict_ediff_ev, "maximum_manageable": active_policy.warning_ediff_ev}, units="eV"))

    prec = (controls.prec_effective or controls.prec_explicit or "").strip().lower()
    checks.append(_check("quality.prec", QualityCheckSeverity.SOFT_QUALITY if prec else QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.PASS if prec.startswith("accura") else (QualityCheckStatus.WARNING if prec else QualityCheckStatus.UNAVAILABLE), measured_value=controls.prec_effective or controls.prec_explicit, threshold="Accurate"))

    lreal = controls.lreal_effective
    lreal_false = lreal is False or str(lreal).strip().lower() in {"f", "false", ".false."}
    checks.append(_check("quality.lreal", QualityCheckSeverity.SOFT_QUALITY if lreal is not None else QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.PASS if lreal_false else (QualityCheckStatus.WARNING if lreal is not None else QualityCheckStatus.UNAVAILABLE), measured_value=lreal, threshold=False, message="Real-space projection may reduce precision in demanding MD thermodynamics." if not lreal_false and lreal is not None else ""))

    if controls.potim_fs is None:
        checks.append(_check("quality.potim", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE))
    else:
        contains_hydrogen = bool(np.any(collection.atomic_numbers == 1))
        threshold = active_policy.strict_potim_fs_hydrogen if contains_hydrogen else active_policy.strict_potim_fs_heavy_atoms
        checks.append(_check("quality.potim", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if controls.potim_fs <= threshold else QualityCheckStatus.WARNING, measured_value=controls.potim_fs, threshold=threshold, units="fs"))

    temperature_definition = _temperature_definition(collection=collection, energy_catalog=energy_catalog, source_identity_signature=source_identity_signature, control_certificate=simulation_control_certificate)
    temperature_statistics = None if temperature_definition is None else _temperature_statistics(temperature_definition, energy_catalog, times, active_policy)
    if temperature_statistics is None:
        checks.append(_check("quality.ionic_temperature", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE, message="Complete ionic kinetic energy is unavailable."))
    else:
        if temperature_statistics.mean_confidence_interval_kelvin is None:
            checks.append(_check("quality.temperature_mean_confidence", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.INSUFFICIENT, measured_value=temperature_statistics.effective_sample_count, threshold=active_policy.minimum_independent_blocks))
        else:
            half_width = 0.5 * (temperature_statistics.mean_confidence_interval_kelvin[1] - temperature_statistics.mean_confidence_interval_kelvin[0])
            allowed = max(active_policy.temperature_ci_half_width_kelvin, active_policy.temperature_ci_relative_fraction * temperature_statistics.represented_time_mean_kelvin)
            checks.append(_check("quality.temperature_mean_confidence", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if half_width <= allowed else QualityCheckStatus.WARNING, measured_value=half_width, threshold=allowed, units="K"))
        checks.append(_check("quality.temperature_stability", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if temperature_statistics.stability_status is TemperatureStabilityStatus.STABLE else (QualityCheckStatus.WARNING if temperature_statistics.stability_status is TemperatureStabilityStatus.DRIFTING else QualityCheckStatus.INSUFFICIENT), measured_value=temperature_statistics.observation_span_change_kelvin, threshold=max(active_policy.temperature_span_drift_kelvin, active_policy.temperature_span_drift_sd_fraction * temperature_statistics.represented_time_standard_deviation_kelvin), units="K over observed span"))
        target = _target_temperature(simulation_control_certificate)
        if target is None or simulation_control_certificate.ensemble not in {EnsembleKind.NVT, EnsembleKind.NPT}:
            checks.append(_check("quality.target_temperature", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.NOT_APPLICABLE, measured_value=temperature_statistics.represented_time_mean_kelvin, message="No authoritative fixed thermostat target applies."))
        else:
            deviation = abs(temperature_statistics.represented_time_mean_kelvin - target)
            allowed = max(active_policy.target_temperature_absolute_tolerance_kelvin, active_policy.target_temperature_relative_tolerance * target)
            checks.append(_check("quality.target_temperature", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if deviation <= allowed else QualityCheckStatus.WARNING, measured_value=deviation, threshold=allowed, units="K"))

    energy = _energy_conservation(collection=collection, energy_catalog=energy_catalog, control_certificate=simulation_control_certificate, policy=active_policy)
    if energy.status is QualityCheckStatus.NOT_APPLICABLE:
        checks.append(_check("quality.nve_energy_conservation", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.NOT_APPLICABLE, requirement=DiagnosticRequirement.METHOD_SPECIFIC))
    elif energy.status in {QualityCheckStatus.UNAVAILABLE, QualityCheckStatus.INSUFFICIENT}:
        checks.append(
            _check(
                "quality.nve_energy_conservation",
                QualityCheckSeverity.SOFT_QUALITY,
                QualityCheckStatus.INSUFFICIENT,
                message="Complete multi-frame NVE conserved-energy evidence is unavailable.",
            )
        )
    else:
        assert energy.drift_ev_per_atom_ps is not None
        catastrophic = abs(energy.drift_ev_per_atom_ps) > active_policy.catastrophic_nve_drift_ev_per_atom_ps
        if catastrophic:
            drift_status = QualityCheckStatus.FAIL
            severity = QualityCheckSeverity.HARD_INTEGRITY
        elif abs(energy.drift_ev_per_atom_ps) <= active_policy.strict_nve_drift_ev_per_atom_ps:
            drift_status = QualityCheckStatus.PASS
            severity = QualityCheckSeverity.SOFT_QUALITY
        else:
            drift_status = QualityCheckStatus.WARNING
            severity = QualityCheckSeverity.SOFT_QUALITY
        checks.append(_check("quality.nve_energy_drift", severity, drift_status, measured_value=energy.drift_ev_per_atom_ps, threshold={"strict": active_policy.strict_nve_drift_ev_per_atom_ps, "catastrophic": active_policy.catastrophic_nve_drift_ev_per_atom_ps}, units="eV/(atom ps)"))
        assert energy.maximum_step_jump_ev_per_atom is not None
        checks.append(_check("integrity.maximum_energy_jump", QualityCheckSeverity.HARD_INTEGRITY, QualityCheckStatus.PASS if energy.maximum_step_jump_ev_per_atom <= active_policy.catastrophic_energy_jump_ev_per_atom else QualityCheckStatus.FAIL, measured_value=energy.maximum_step_jump_ev_per_atom, threshold=active_policy.catastrophic_energy_jump_ev_per_atom, units="eV/atom/frame"))
        if energy.identity_residual_max_ev is None:
            checks.append(_check("quality.energy_identity", QualityCheckSeverity.DIAGNOSTIC, QualityCheckStatus.UNAVAILABLE))
        else:
            residual_per_atom = energy.identity_residual_max_ev / collection.n_atoms
            checks.append(_check("quality.energy_identity", QualityCheckSeverity.SOFT_QUALITY, QualityCheckStatus.PASS if residual_per_atom <= active_policy.total_energy_identity_tolerance_ev_per_atom else QualityCheckStatus.WARNING, measured_value=residual_per_atom, threshold=active_policy.total_energy_identity_tolerance_ev_per_atom, units="eV/atom"))

    realized_consistency = _realized_ensemble_consistency(
        collection=collection,
        energy_catalog=energy_catalog,
        control_certificate=simulation_control_certificate,
        energy=energy,
        policy=active_policy,
        source_identity_signature=source_identity_signature,
    )
    if simulation_control_certificate.cell_control.active is False:
        cell_deviation = realized_consistency.cell_matrix_relative_deviation
        checks.append(
            _check(
                "quality.fixed_cell_consistency",
                QualityCheckSeverity.SOFT_QUALITY,
                QualityCheckStatus.PASS
                if cell_deviation is not None and cell_deviation <= active_policy.strict_fixed_cell_relative_deviation
                else QualityCheckStatus.WARNING
                if cell_deviation is not None
                else QualityCheckStatus.INSUFFICIENT,
                measured_value=cell_deviation,
                threshold=active_policy.strict_fixed_cell_relative_deviation,
                units="relative Frobenius deviation",
            )
        )
    else:
        checks.append(
            _check(
                "quality.fixed_cell_consistency",
                QualityCheckSeverity.DIAGNOSTIC,
                QualityCheckStatus.NOT_APPLICABLE,
                requirement=DiagnosticRequirement.METHOD_SPECIFIC,
            )
        )
    if simulation_control_certificate.thermostat.active is False:
        thermostat_max = realized_consistency.inactive_thermostat_energy_max_abs_ev
        checks.append(
            _check(
                "quality.inactive_thermostat_consistency",
                QualityCheckSeverity.SOFT_QUALITY if thermostat_max is not None else QualityCheckSeverity.DIAGNOSTIC,
                QualityCheckStatus.PASS
                if thermostat_max is not None and thermostat_max <= active_policy.inactive_thermostat_energy_tolerance_ev
                else QualityCheckStatus.WARNING
                if thermostat_max is not None
                else QualityCheckStatus.UNAVAILABLE,
                requirement=(
                    DiagnosticRequirement.VERDICT_CRITICAL
                    if thermostat_max is not None
                    else DiagnosticRequirement.OPTIONAL
                ),
                measured_value=thermostat_max,
                threshold=active_policy.inactive_thermostat_energy_tolerance_ev,
                units="eV",
            )
        )
    else:
        checks.append(
            _check(
                "quality.inactive_thermostat_consistency",
                QualityCheckSeverity.DIAGNOSTIC,
                QualityCheckStatus.NOT_APPLICABLE,
                requirement=DiagnosticRequirement.METHOD_SPECIFIC,
            )
        )

    checks.append(
        _check(
            "diagnostic.realized_ensemble_consistency",
            QualityCheckSeverity.DIAGNOSTIC,
            (
                QualityCheckStatus.PASS
                if realized_consistency.status is RealizedEnsembleConsistencyStatus.CONSISTENT
                else QualityCheckStatus.WARNING
                if realized_consistency.status in {RealizedEnsembleConsistencyStatus.DEGRADED, RealizedEnsembleConsistencyStatus.INCONSISTENT}
                else QualityCheckStatus.INSUFFICIENT
            ),
            requirement=DiagnosticRequirement.METHOD_SPECIFIC,
            measured_value=realized_consistency.status.value,
            evidence=realized_consistency.evidence,
        )
    )

    unqualified_reasons = tuple(check.check_id for check in checks if check.severity is QualityCheckSeverity.HARD_INTEGRITY and check.status is QualityCheckStatus.FAIL)
    degraded_reasons = tuple(check.check_id for check in checks if check.severity is QualityCheckSeverity.SOFT_QUALITY and check.status in {QualityCheckStatus.FAIL, QualityCheckStatus.WARNING, QualityCheckStatus.INSUFFICIENT})
    if unqualified_reasons:
        outcome = TrajectoryQualityOutcome.UNQUALIFIED
    elif degraded_reasons:
        outcome = TrajectoryQualityOutcome.DEGRADED_QUALITY
    else:
        outcome = TrajectoryQualityOutcome.STRICTLY_QUALIFIED

    verdict = TrajectoryQualityVerdict(
        source_identity_signature=source_identity_signature,
        simulation_control_certificate_signature=simulation_control_certificate.signature,
        numerical_quality_controls_signature=numerical_quality_controls.signature,
        energy_catalog_signature=energy_catalog.signature,
        policy_signature=active_policy.signature,
        outcome=outcome,
        temperature_definition=temperature_definition,
        temperature_statistics=temperature_statistics,
        energy_conservation=energy,
        realized_ensemble_consistency=realized_consistency,
        checks=tuple(checks),
        degraded_reasons=degraded_reasons,
        unqualified_reasons=unqualified_reasons,
    )
    if outcome is TrajectoryQualityOutcome.UNQUALIFIED and raise_on_unqualified:
        raise TrajectoryIntegrityError(
            "Trajectory is unqualified because catastrophic integrity checks failed: "
            + ", ".join(unqualified_reasons)
        )
    if outcome is TrajectoryQualityOutcome.DEGRADED_QUALITY and emit_warning:
        warnings.warn(
            "Trajectory has degraded quality but remains analyzable: "
            + ", ".join(degraded_reasons),
            TrajectoryDegradedQualityWarning,
            stacklevel=2,
        )
    return verdict


__all__ = [
    "BOLTZMANN_CONSTANT_EV_PER_K",
    "ENERGY_CONSERVATION_STATISTICS_SCHEMA",
    "IONIC_TEMPERATURE_DEFINITION_SCHEMA",
    "IONIC_TEMPERATURE_STATISTICS_SCHEMA",
    "TRAJECTORY_QUALITY_CHECK_SCHEMA",
    "TRAJECTORY_QUALITY_POLICY_SCHEMA",
    "TRAJECTORY_QUALITY_POLICY_VERSION",
    "TRAJECTORY_QUALITY_VERDICT_SCHEMA",
    "DiagnosticRequirement",
    "EnergyConservationStatistics",
    "IonicTemperatureDefinition",
    "IonicTemperatureStatistics",
    "QualityCheckSeverity",
    "REALIZED_ENSEMBLE_CONSISTENCY_SCHEMA",
    "RealizedEnsembleConsistency",
    "RealizedEnsembleConsistencyStatus",
    "QualityCheckStatus",
    "TemperatureStabilityStatus",
    "TrajectoryDegradedQualityWarning",
    "TrajectoryIntegrityError",
    "TrajectoryQualityCheck",
    "TrajectoryQualityOutcome",
    "TrajectoryQualityPolicy",
    "TrajectoryQualityVerdict",
    "assess_trajectory_quality",
]
