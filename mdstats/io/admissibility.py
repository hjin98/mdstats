"""Stage 11E-STAT2 ensemble-specific admissibility and E0b overlays."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping, Sequence, TYPE_CHECKING

import numpy as np

from .control_certificates import (
    EnsembleKind,
    InferenceStatus,
    SimulationControlCertificate,
)
from .production_regimes import (
    ProductionIntervalStatus,
    ProductionRegime,
    ProductionRegimeCatalog,
    RegimeStationarityStatus,
)
from .source_controls import SourceControlError, SourceControlSerializationError
from .trajectory_quality import (
    TrajectoryQualityOutcome,
    TrajectoryQualityVerdict,
)

if TYPE_CHECKING:
    from mdstats.analysis.site_samples import FrameworkAlignedIonSampleCatalog

ENSEMBLE_ADMISSIBILITY_POLICY_SCHEMA = "mdstats.ensemble-admissibility-policy.v1"
REWEIGHTING_PROVENANCE_SCHEMA = "mdstats.reweighting-provenance.v1"
ENSEMBLE_APPROXIMATION_PROVENANCE_SCHEMA = (
    "mdstats.ensemble-approximation-provenance.v1"
)
ADMISSIBILITY_PERMISSION_SCHEMA = "mdstats.admissibility-permission.v1"
REGIME_ADMISSIBILITY_SCHEMA = "mdstats.regime-admissibility.v1"
PMF_ADMISSIBILITY_CERTIFICATE_SCHEMA = "mdstats.pmf-admissibility-certificate.v1"
EVIDENCE_PERMISSION_MASK_SCHEMA = "mdstats.evidence-permission-mask.v1"
EVIDENCE_ADMISSIBILITY_OVERLAY_SCHEMA = "mdstats.evidence-admissibility-overlay.v1"
ENSEMBLE_ADMISSIBILITY_POLICY_VERSION = (
    "mdstats.ensemble-admissibility-policy.2026-07.v1"
)


class AdmissibilityStatus(str, Enum):
    PERMITTED = "permitted"
    CONDITIONAL = "conditional"
    DIAGNOSTIC_ONLY = "diagnostic_only"
    BLOCKED = "blocked"
    NOT_APPLICABLE = "not_applicable"
    UNRESOLVED = "unresolved"


class EvidenceUse(str, Enum):
    DESCRIPTIVE_DENSITY = "descriptive_density"
    MICROCANONICAL_OCCUPANCY = "microcanonical_occupancy"
    CANONICAL_LANDSCAPE = "canonical_landscape"
    NPT_LANDSCAPE = "npt_landscape"
    REWEIGHTED_LANDSCAPE = "reweighted_landscape"
    CONDITIONAL_FORCE = "conditional_force"
    DIAGNOSTIC_ONLY = "diagnostic_only"


class ThermodynamicMeasure(str, Enum):
    DESCRIPTIVE_SPATIAL = "descriptive_spatial_measure"
    MICROCANONICAL_ENERGY_SHELL = "microcanonical_energy_shell"
    CANONICAL_HELMHOLTZ = "canonical_helmholtz"
    ISOTHERMAL_ISOBARIC_GIBBS = "isothermal_isobaric_gibbs"
    REWEIGHTED_TARGET = "reweighted_target_measure"
    CONDITIONAL_FORCE = "mechanical_or_ensemble_conditional_force"
    NONE = "none"


class ReweightingStatus(str, Enum):
    NOT_PROVIDED = "not_provided"
    VERIFIED = "verified"
    DECLARED_ONLY = "declared_only"
    REJECTED = "rejected"


class ApproximationStatus(str, Enum):
    NOT_PROVIDED = "not_provided"
    ACCEPTED = "accepted"
    DECLARED_ONLY = "declared_only"
    REJECTED = "rejected"


class EvidenceBaseChannel(str, Enum):
    POSITION = "position"
    JOINT = "joint"


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


def _array_digest(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    payload = contiguous.dtype.str.encode("ascii")
    payload += repr(contiguous.shape).encode("ascii")
    payload += contiguous.tobytes(order="C")
    return hashlib.sha256(payload).hexdigest()


def _finite_optional(value: Any, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise SourceControlError(f"{name} must be finite or None.")
    return result


def _require_digest(value: str | None, *, name: str, allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    if not isinstance(value, str) or len(value) != 64:
        raise SourceControlError(f"{name} must be a SHA-256 digest.")


@dataclass(frozen=True, slots=True)
class EnsembleAdmissibilityPolicy:
    policy_version: str = ENSEMBLE_ADMISSIBILITY_POLICY_VERSION
    allow_degraded_quality: bool = True
    allow_diagnostic_spatial_evidence: bool = True
    allow_unqualified_diagnostics: bool = False
    require_resolved_bias_for_thermodynamics: bool = True
    require_resolved_constraints_for_thermodynamics: bool = True
    require_resolved_force_provenance: bool = True

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SourceControlError("Admissibility policy version is required.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ENSEMBLE_ADMISSIBILITY_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "allow_degraded_quality": self.allow_degraded_quality,
            "allow_diagnostic_spatial_evidence": self.allow_diagnostic_spatial_evidence,
            "allow_unqualified_diagnostics": self.allow_unqualified_diagnostics,
            "require_resolved_bias_for_thermodynamics": (
                self.require_resolved_bias_for_thermodynamics
            ),
            "require_resolved_constraints_for_thermodynamics": (
                self.require_resolved_constraints_for_thermodynamics
            ),
            "require_resolved_force_provenance": (
                self.require_resolved_force_provenance
            ),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EnsembleAdmissibilityPolicy":
        if payload.get("schema") != ENSEMBLE_ADMISSIBILITY_POLICY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported ensemble-admissibility-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            allow_degraded_quality=bool(payload["allow_degraded_quality"]),
            allow_diagnostic_spatial_evidence=bool(
                payload["allow_diagnostic_spatial_evidence"]
            ),
            allow_unqualified_diagnostics=bool(
                payload["allow_unqualified_diagnostics"]
            ),
            require_resolved_bias_for_thermodynamics=bool(
                payload["require_resolved_bias_for_thermodynamics"]
            ),
            require_resolved_constraints_for_thermodynamics=bool(
                payload["require_resolved_constraints_for_thermodynamics"]
            ),
            require_resolved_force_provenance=bool(
                payload["require_resolved_force_provenance"]
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Ensemble-admissibility-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class ReweightingProvenance:
    source_identity_signature: str
    status: ReweightingStatus = ReweightingStatus.NOT_PROVIDED
    method: str | None = None
    target_measure: str | None = None
    target_temperature_kelvin: float | None = None
    applicable_regime_ids: tuple[str, ...] = ()
    normalized_weights_available: bool = False
    finite_weight_diagnostics_passed: bool = False
    effective_sample_size: float | None = None
    evidence_signature: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_digest(
            self.source_identity_signature, name="source_identity_signature"
        )
        status = ReweightingStatus(self.status)
        regimes = tuple(sorted({str(value) for value in self.applicable_regime_ids}))
        notes = tuple(str(value) for value in self.notes)
        target_temperature = _finite_optional(
            self.target_temperature_kelvin, name="target_temperature_kelvin"
        )
        ess = _finite_optional(self.effective_sample_size, name="effective_sample_size")
        if ess is not None and ess < 0.0:
            raise SourceControlError("effective_sample_size must be nonnegative.")
        _require_digest(
            self.evidence_signature,
            name="evidence_signature",
            allow_none=True,
        )
        if status is ReweightingStatus.VERIFIED:
            if not self.method or not self.target_measure:
                raise SourceControlError(
                    "Verified reweighting requires method and target_measure."
                )
            if not regimes:
                raise SourceControlError(
                    "Verified reweighting requires at least one applicable regime."
                )
            if not self.normalized_weights_available:
                raise SourceControlError(
                    "Verified reweighting requires normalized weights."
                )
            if not self.finite_weight_diagnostics_passed:
                raise SourceControlError(
                    "Verified reweighting requires finite-weight diagnostics."
                )
            if self.evidence_signature is None:
                raise SourceControlError(
                    "Verified reweighting requires an evidence signature."
                )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "applicable_regime_ids", regimes)
        object.__setattr__(self, "target_temperature_kelvin", target_temperature)
        object.__setattr__(self, "effective_sample_size", ess)
        object.__setattr__(self, "notes", notes)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REWEIGHTING_PROVENANCE_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "status": self.status.value,
            "method": self.method,
            "target_measure": self.target_measure,
            "target_temperature_kelvin": self.target_temperature_kelvin,
            "applicable_regime_ids": list(self.applicable_regime_ids),
            "normalized_weights_available": self.normalized_weights_available,
            "finite_weight_diagnostics_passed": self.finite_weight_diagnostics_passed,
            "effective_sample_size": self.effective_sample_size,
            "evidence_signature": self.evidence_signature,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReweightingProvenance":
        if payload.get("schema") != REWEIGHTING_PROVENANCE_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported reweighting-provenance schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            status=ReweightingStatus(payload["status"]),
            method=None if payload.get("method") is None else str(payload["method"]),
            target_measure=(
                None
                if payload.get("target_measure") is None
                else str(payload["target_measure"])
            ),
            target_temperature_kelvin=payload.get("target_temperature_kelvin"),
            applicable_regime_ids=tuple(
                str(value) for value in payload.get("applicable_regime_ids", ())
            ),
            normalized_weights_available=bool(
                payload.get("normalized_weights_available", False)
            ),
            finite_weight_diagnostics_passed=bool(
                payload.get("finite_weight_diagnostics_passed", False)
            ),
            effective_sample_size=payload.get("effective_sample_size"),
            evidence_signature=(
                None
                if payload.get("evidence_signature") is None
                else str(payload["evidence_signature"])
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Reweighting-provenance signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class EnsembleApproximationProvenance:
    source_identity_signature: str
    status: ApproximationStatus = ApproximationStatus.NOT_PROVIDED
    approximation_kind: str | None = None
    target_temperature_kelvin: float | None = None
    applicable_regime_ids: tuple[str, ...] = ()
    evidence_signature: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_digest(
            self.source_identity_signature, name="source_identity_signature"
        )
        status = ApproximationStatus(self.status)
        regimes = tuple(sorted({str(value) for value in self.applicable_regime_ids}))
        temperature = _finite_optional(
            self.target_temperature_kelvin, name="target_temperature_kelvin"
        )
        _require_digest(
            self.evidence_signature,
            name="evidence_signature",
            allow_none=True,
        )
        if status is ApproximationStatus.ACCEPTED:
            if self.approximation_kind not in {"finite_bath", "ensemble_equivalence"}:
                raise SourceControlError(
                    "Accepted approximation_kind must be finite_bath or ensemble_equivalence."
                )
            if temperature is None or temperature <= 0.0:
                raise SourceControlError(
                    "Accepted ensemble approximation requires positive target temperature."
                )
            if not regimes or self.evidence_signature is None:
                raise SourceControlError(
                    "Accepted ensemble approximation requires regimes and evidence signature."
                )
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "target_temperature_kelvin", temperature)
        object.__setattr__(self, "applicable_regime_ids", regimes)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ENSEMBLE_APPROXIMATION_PROVENANCE_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "status": self.status.value,
            "approximation_kind": self.approximation_kind,
            "target_temperature_kelvin": self.target_temperature_kelvin,
            "applicable_regime_ids": list(self.applicable_regime_ids),
            "evidence_signature": self.evidence_signature,
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
    ) -> "EnsembleApproximationProvenance":
        if payload.get("schema") != ENSEMBLE_APPROXIMATION_PROVENANCE_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported ensemble-approximation-provenance schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            status=ApproximationStatus(payload["status"]),
            approximation_kind=(
                None
                if payload.get("approximation_kind") is None
                else str(payload["approximation_kind"])
            ),
            target_temperature_kelvin=payload.get("target_temperature_kelvin"),
            applicable_regime_ids=tuple(
                str(value) for value in payload.get("applicable_regime_ids", ())
            ),
            evidence_signature=(
                None
                if payload.get("evidence_signature") is None
                else str(payload["evidence_signature"])
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Ensemble-approximation-provenance signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class AdmissibilityPermission:
    regime_id: str
    evidence_use: EvidenceUse
    status: AdmissibilityStatus
    measure: ThermodynamicMeasure
    thermodynamic: bool
    temperature_kelvin: float | None = None
    temperature_source_signature: str | None = None
    energy_shell_channel: str | None = None
    energy_shell_source_signature: str | None = None
    approximation_signature: str | None = None
    reweighting_signature: str | None = None
    reasons: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.regime_id:
            raise SourceControlError("Admissibility permission requires regime_id.")
        object.__setattr__(self, "evidence_use", EvidenceUse(self.evidence_use))
        object.__setattr__(self, "status", AdmissibilityStatus(self.status))
        object.__setattr__(self, "measure", ThermodynamicMeasure(self.measure))
        object.__setattr__(
            self,
            "temperature_kelvin",
            _finite_optional(self.temperature_kelvin, name="temperature_kelvin"),
        )
        for name in (
            "temperature_source_signature",
            "energy_shell_source_signature",
            "approximation_signature",
            "reweighting_signature",
        ):
            _require_digest(getattr(self, name), name=name, allow_none=True)
        object.__setattr__(self, "reasons", tuple(str(value) for value in self.reasons))
        object.__setattr__(self, "evidence", tuple(str(value) for value in self.evidence))

    @property
    def enables_mask(self) -> bool:
        return self.status in {
            AdmissibilityStatus.PERMITTED,
            AdmissibilityStatus.CONDITIONAL,
            AdmissibilityStatus.DIAGNOSTIC_ONLY,
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADMISSIBILITY_PERMISSION_SCHEMA,
            "regime_id": self.regime_id,
            "evidence_use": self.evidence_use.value,
            "status": self.status.value,
            "measure": self.measure.value,
            "thermodynamic": self.thermodynamic,
            "temperature_kelvin": self.temperature_kelvin,
            "temperature_source_signature": self.temperature_source_signature,
            "energy_shell_channel": self.energy_shell_channel,
            "energy_shell_source_signature": self.energy_shell_source_signature,
            "approximation_signature": self.approximation_signature,
            "reweighting_signature": self.reweighting_signature,
            "reasons": list(self.reasons),
            "evidence": list(self.evidence),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdmissibilityPermission":
        if payload.get("schema") != ADMISSIBILITY_PERMISSION_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported admissibility-permission schema."
            )
        result = cls(
            regime_id=str(payload["regime_id"]),
            evidence_use=EvidenceUse(payload["evidence_use"]),
            status=AdmissibilityStatus(payload["status"]),
            measure=ThermodynamicMeasure(payload["measure"]),
            thermodynamic=bool(payload["thermodynamic"]),
            temperature_kelvin=payload.get("temperature_kelvin"),
            temperature_source_signature=(
                None
                if payload.get("temperature_source_signature") is None
                else str(payload["temperature_source_signature"])
            ),
            energy_shell_channel=(
                None
                if payload.get("energy_shell_channel") is None
                else str(payload["energy_shell_channel"])
            ),
            energy_shell_source_signature=(
                None
                if payload.get("energy_shell_source_signature") is None
                else str(payload["energy_shell_source_signature"])
            ),
            approximation_signature=(
                None
                if payload.get("approximation_signature") is None
                else str(payload["approximation_signature"])
            ),
            reweighting_signature=(
                None
                if payload.get("reweighting_signature") is None
                else str(payload["reweighting_signature"])
            ),
            reasons=tuple(str(value) for value in payload.get("reasons", ())),
            evidence=tuple(str(value) for value in payload.get("evidence", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Admissibility-permission signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class RegimeAdmissibility:
    regime_id: str
    production_regime_signature: str
    frame_start: int
    frame_stop: int
    ensemble: EnsembleKind
    quality_outcome: TrajectoryQualityOutcome
    stationarity_status: RegimeStationarityStatus
    production_interval_status: ProductionIntervalStatus
    temperature_mean_kelvin: float | None
    temperature_standard_deviation_kelvin: float | None
    temperature_source_signature: str | None
    energy_shell_channel: str | None
    energy_shell_mean_ev: float | None
    energy_shell_standard_deviation_ev: float | None
    energy_shell_source_signature: str | None
    permissions: tuple[AdmissibilityPermission, ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.regime_id or self.frame_start < 0 or self.frame_stop <= self.frame_start:
            raise SourceControlError("Regime admissibility interval is invalid.")
        _require_digest(
            self.production_regime_signature,
            name="production_regime_signature",
        )
        object.__setattr__(self, "ensemble", EnsembleKind(self.ensemble))
        object.__setattr__(
            self, "quality_outcome", TrajectoryQualityOutcome(self.quality_outcome)
        )
        object.__setattr__(
            self,
            "stationarity_status",
            RegimeStationarityStatus(self.stationarity_status),
        )
        object.__setattr__(
            self,
            "production_interval_status",
            ProductionIntervalStatus(self.production_interval_status),
        )
        object.__setattr__(
            self,
            "temperature_mean_kelvin",
            _finite_optional(
                self.temperature_mean_kelvin, name="temperature_mean_kelvin"
            ),
        )
        object.__setattr__(
            self,
            "temperature_standard_deviation_kelvin",
            _finite_optional(
                self.temperature_standard_deviation_kelvin,
                name="temperature_standard_deviation_kelvin",
            ),
        )
        object.__setattr__(
            self,
            "energy_shell_mean_ev",
            _finite_optional(self.energy_shell_mean_ev, name="energy_shell_mean_ev"),
        )
        object.__setattr__(
            self,
            "energy_shell_standard_deviation_ev",
            _finite_optional(
                self.energy_shell_standard_deviation_ev,
                name="energy_shell_standard_deviation_ev",
            ),
        )
        _require_digest(
            self.temperature_source_signature,
            name="temperature_source_signature",
            allow_none=True,
        )
        _require_digest(
            self.energy_shell_source_signature,
            name="energy_shell_source_signature",
            allow_none=True,
        )
        permissions = tuple(self.permissions)
        uses = [item.evidence_use for item in permissions]
        if len(uses) != len(set(uses)):
            raise SourceControlError("A regime may contain one permission per evidence use.")
        if any(item.regime_id != self.regime_id for item in permissions):
            raise SourceControlError("Permission regime IDs must match their parent regime.")
        object.__setattr__(self, "permissions", permissions)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def permission(self, evidence_use: EvidenceUse | str) -> AdmissibilityPermission:
        target = EvidenceUse(evidence_use)
        for item in self.permissions:
            if item.evidence_use is target:
                return item
        raise KeyError(target.value)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REGIME_ADMISSIBILITY_SCHEMA,
            "regime_id": self.regime_id,
            "production_regime_signature": self.production_regime_signature,
            "frame_start": self.frame_start,
            "frame_stop": self.frame_stop,
            "ensemble": self.ensemble.value,
            "quality_outcome": self.quality_outcome.value,
            "stationarity_status": self.stationarity_status.value,
            "production_interval_status": self.production_interval_status.value,
            "temperature_mean_kelvin": self.temperature_mean_kelvin,
            "temperature_standard_deviation_kelvin": (
                self.temperature_standard_deviation_kelvin
            ),
            "temperature_source_signature": self.temperature_source_signature,
            "energy_shell_channel": self.energy_shell_channel,
            "energy_shell_mean_ev": self.energy_shell_mean_ev,
            "energy_shell_standard_deviation_ev": (
                self.energy_shell_standard_deviation_ev
            ),
            "energy_shell_source_signature": self.energy_shell_source_signature,
            "permissions": [item.to_dict() for item in self.permissions],
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RegimeAdmissibility":
        if payload.get("schema") != REGIME_ADMISSIBILITY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported regime-admissibility schema."
            )
        result = cls(
            regime_id=str(payload["regime_id"]),
            production_regime_signature=str(
                payload["production_regime_signature"]
            ),
            frame_start=int(payload["frame_start"]),
            frame_stop=int(payload["frame_stop"]),
            ensemble=EnsembleKind(payload["ensemble"]),
            quality_outcome=TrajectoryQualityOutcome(payload["quality_outcome"]),
            stationarity_status=RegimeStationarityStatus(
                payload["stationarity_status"]
            ),
            production_interval_status=ProductionIntervalStatus(
                payload["production_interval_status"]
            ),
            temperature_mean_kelvin=payload.get("temperature_mean_kelvin"),
            temperature_standard_deviation_kelvin=payload.get(
                "temperature_standard_deviation_kelvin"
            ),
            temperature_source_signature=(
                None
                if payload.get("temperature_source_signature") is None
                else str(payload["temperature_source_signature"])
            ),
            energy_shell_channel=(
                None
                if payload.get("energy_shell_channel") is None
                else str(payload["energy_shell_channel"])
            ),
            energy_shell_mean_ev=payload.get("energy_shell_mean_ev"),
            energy_shell_standard_deviation_ev=payload.get(
                "energy_shell_standard_deviation_ev"
            ),
            energy_shell_source_signature=(
                None
                if payload.get("energy_shell_source_signature") is None
                else str(payload["energy_shell_source_signature"])
            ),
            permissions=tuple(
                AdmissibilityPermission.from_dict(item)
                for item in payload.get("permissions", ())
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Regime-admissibility signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class PmfAdmissibilityCertificate:
    source_identity_signature: str
    simulation_control_certificate_signature: str
    trajectory_quality_verdict_signature: str
    production_regime_catalog_signature: str
    policy_signature: str
    ensemble: EnsembleKind
    regime_admissibility: tuple[RegimeAdmissibility, ...]
    reweighting_provenance: ReweightingProvenance
    approximation_provenance: EnsembleApproximationProvenance
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_identity_signature",
            "simulation_control_certificate_signature",
            "trajectory_quality_verdict_signature",
            "production_regime_catalog_signature",
            "policy_signature",
        ):
            _require_digest(getattr(self, name), name=name)
        object.__setattr__(self, "ensemble", EnsembleKind(self.ensemble))
        records = tuple(self.regime_admissibility)
        ids = [item.regime_id for item in records]
        if len(ids) != len(set(ids)):
            raise SourceControlError("Regime admissibility IDs must be unique.")
        if self.reweighting_provenance.source_identity_signature != self.source_identity_signature:
            raise SourceControlError("Reweighting provenance source identity mismatch.")
        if self.approximation_provenance.source_identity_signature != self.source_identity_signature:
            raise SourceControlError("Approximation provenance source identity mismatch.")
        object.__setattr__(self, "regime_admissibility", records)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def regime(self, regime_id: str) -> RegimeAdmissibility:
        for item in self.regime_admissibility:
            if item.regime_id == regime_id:
                return item
        raise KeyError(regime_id)

    def permission(
        self, regime_id: str, evidence_use: EvidenceUse | str
    ) -> AdmissibilityPermission:
        return self.regime(regime_id).permission(evidence_use)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PMF_ADMISSIBILITY_CERTIFICATE_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "simulation_control_certificate_signature": (
                self.simulation_control_certificate_signature
            ),
            "trajectory_quality_verdict_signature": (
                self.trajectory_quality_verdict_signature
            ),
            "production_regime_catalog_signature": (
                self.production_regime_catalog_signature
            ),
            "policy_signature": self.policy_signature,
            "ensemble": self.ensemble.value,
            "regime_admissibility": [
                item.to_dict() for item in self.regime_admissibility
            ],
            "reweighting_provenance": self.reweighting_provenance.to_dict(),
            "approximation_provenance": self.approximation_provenance.to_dict(),
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
    ) -> "PmfAdmissibilityCertificate":
        if payload.get("schema") != PMF_ADMISSIBILITY_CERTIFICATE_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported PMF-admissibility-certificate schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            simulation_control_certificate_signature=str(
                payload["simulation_control_certificate_signature"]
            ),
            trajectory_quality_verdict_signature=str(
                payload["trajectory_quality_verdict_signature"]
            ),
            production_regime_catalog_signature=str(
                payload["production_regime_catalog_signature"]
            ),
            policy_signature=str(payload["policy_signature"]),
            ensemble=EnsembleKind(payload["ensemble"]),
            regime_admissibility=tuple(
                RegimeAdmissibility.from_dict(item)
                for item in payload.get("regime_admissibility", ())
            ),
            reweighting_provenance=ReweightingProvenance.from_dict(
                payload["reweighting_provenance"]
            ),
            approximation_provenance=EnsembleApproximationProvenance.from_dict(
                payload["approximation_provenance"]
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "PMF-admissibility-certificate signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class EvidencePermissionMask:
    evidence_use: EvidenceUse
    status: AdmissibilityStatus
    base_channel: EvidenceBaseChannel
    sample_mask: np.ndarray

    def __post_init__(self) -> None:
        object.__setattr__(self, "evidence_use", EvidenceUse(self.evidence_use))
        object.__setattr__(self, "status", AdmissibilityStatus(self.status))
        object.__setattr__(self, "base_channel", EvidenceBaseChannel(self.base_channel))
        mask = np.asarray(self.sample_mask, dtype=np.bool_)
        if mask.ndim != 1:
            raise SourceControlError("Evidence permission mask must be one-dimensional.")
        mask = np.array(mask, copy=True)
        mask.setflags(write=False)
        object.__setattr__(self, "sample_mask", mask)

    @property
    def n_selected(self) -> int:
        return int(np.count_nonzero(self.sample_mask))

    def _payload(self, *, include_mask: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": EVIDENCE_PERMISSION_MASK_SCHEMA,
            "evidence_use": self.evidence_use.value,
            "status": self.status.value,
            "base_channel": self.base_channel.value,
            "sample_count": int(self.sample_mask.size),
            "selected_count": self.n_selected,
            "sample_mask_sha256": _array_digest(self.sample_mask),
        }
        if include_mask:
            payload["sample_mask"] = self.sample_mask.tolist()
        return payload

    @property
    def signature(self) -> str:
        return _digest(self._payload(include_mask=False))

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(include_mask=True), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidencePermissionMask":
        if payload.get("schema") != EVIDENCE_PERMISSION_MASK_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported evidence-permission-mask schema."
            )
        if "sample_mask" not in payload:
            raise SourceControlSerializationError(
                "Evidence-permission-mask replay requires sample_mask."
            )
        result = cls(
            evidence_use=EvidenceUse(payload["evidence_use"]),
            status=AdmissibilityStatus(payload["status"]),
            base_channel=EvidenceBaseChannel(payload["base_channel"]),
            sample_mask=np.asarray(payload["sample_mask"], dtype=np.bool_),
        )
        if payload.get("sample_count") not in (None, result.sample_mask.size):
            raise SourceControlSerializationError("Evidence mask sample-count mismatch.")
        if payload.get("selected_count") not in (None, result.n_selected):
            raise SourceControlSerializationError("Evidence mask selected-count mismatch.")
        if payload.get("sample_mask_sha256") not in (
            None,
            _array_digest(result.sample_mask),
        ):
            raise SourceControlSerializationError("Evidence mask digest mismatch.")
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Evidence-permission-mask signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class EvidenceAdmissibilityOverlay:
    source_identity_signature: str
    sample_catalog_signature: str
    pmf_admissibility_certificate_signature: str
    production_regime_catalog_signature: str
    regime_id: str
    production_regime_signature: str
    sample_count: int
    permission_masks: tuple[EvidencePermissionMask, ...]
    pmf_force_mask: np.ndarray
    raw_position_mask_signature: str
    raw_joint_mask_signature: str
    sample_force_provenance_signature: str
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_identity_signature",
            "sample_catalog_signature",
            "pmf_admissibility_certificate_signature",
            "production_regime_catalog_signature",
            "production_regime_signature",
            "raw_position_mask_signature",
            "raw_joint_mask_signature",
            "sample_force_provenance_signature",
        ):
            _require_digest(getattr(self, name), name=name)
        if not self.regime_id or self.sample_count < 0:
            raise SourceControlError("Evidence overlay identity or sample count is invalid.")
        masks = tuple(self.permission_masks)
        uses = [item.evidence_use for item in masks]
        if len(uses) != len(set(uses)):
            raise SourceControlError("Evidence overlay uses must be unique.")
        if any(item.sample_mask.size != self.sample_count for item in masks):
            raise SourceControlError("Evidence overlay masks must align with sample_count.")
        pmf_force_mask = np.asarray(self.pmf_force_mask, dtype=np.bool_)
        if pmf_force_mask.ndim != 1 or pmf_force_mask.size != self.sample_count:
            raise SourceControlError(
                "PMF-force overlay mask must be one-dimensional and sample-aligned."
            )
        try:
            joint_mask = next(
                item.sample_mask
                for item in masks
                if item.evidence_use is EvidenceUse.CONDITIONAL_FORCE
            )
        except StopIteration as exc:
            raise SourceControlError(
                "Evidence overlay requires the conditional-force permission mask."
            ) from exc
        if np.any(pmf_force_mask & ~joint_mask):
            raise SourceControlError(
                "PMF-force overlay mask must be a subset of conditional-force evidence."
            )
        pmf_force_mask = np.array(pmf_force_mask, copy=True)
        pmf_force_mask.setflags(write=False)
        object.__setattr__(self, "permission_masks", masks)
        object.__setattr__(self, "pmf_force_mask", pmf_force_mask)
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def mask_for(self, evidence_use: EvidenceUse | str) -> np.ndarray:
        target = EvidenceUse(evidence_use)
        for item in self.permission_masks:
            if item.evidence_use is target:
                return item.sample_mask
        raise KeyError(target.value)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVIDENCE_ADMISSIBILITY_OVERLAY_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "sample_catalog_signature": self.sample_catalog_signature,
            "pmf_admissibility_certificate_signature": (
                self.pmf_admissibility_certificate_signature
            ),
            "production_regime_catalog_signature": (
                self.production_regime_catalog_signature
            ),
            "regime_id": self.regime_id,
            "production_regime_signature": self.production_regime_signature,
            "sample_count": self.sample_count,
            "permission_masks": [item.to_dict() for item in self.permission_masks],
            "pmf_force_mask": self.pmf_force_mask.tolist(),
            "pmf_force_mask_sha256": _array_digest(self.pmf_force_mask),
            "pmf_force_selected_count": int(np.count_nonzero(self.pmf_force_mask)),
            "raw_position_mask_signature": self.raw_position_mask_signature,
            "raw_joint_mask_signature": self.raw_joint_mask_signature,
            "sample_force_provenance_signature": (
                self.sample_force_provenance_signature
            ),
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceAdmissibilityOverlay":
        if payload.get("schema") != EVIDENCE_ADMISSIBILITY_OVERLAY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported evidence-admissibility-overlay schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            sample_catalog_signature=str(payload["sample_catalog_signature"]),
            pmf_admissibility_certificate_signature=str(
                payload["pmf_admissibility_certificate_signature"]
            ),
            production_regime_catalog_signature=str(
                payload["production_regime_catalog_signature"]
            ),
            regime_id=str(payload["regime_id"]),
            production_regime_signature=str(
                payload["production_regime_signature"]
            ),
            sample_count=int(payload["sample_count"]),
            permission_masks=tuple(
                EvidencePermissionMask.from_dict(item)
                for item in payload.get("permission_masks", ())
            ),
            pmf_force_mask=np.asarray(
                payload.get("pmf_force_mask", ()), dtype=np.bool_
            ),
            raw_position_mask_signature=str(
                payload["raw_position_mask_signature"]
            ),
            raw_joint_mask_signature=str(payload["raw_joint_mask_signature"]),
            sample_force_provenance_signature=str(
                payload["sample_force_provenance_signature"]
            ),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("pmf_force_mask_sha256") not in (
            None,
            _array_digest(result.pmf_force_mask),
        ):
            raise SourceControlSerializationError("PMF-force overlay digest mismatch.")
        if payload.get("pmf_force_selected_count") not in (
            None,
            int(np.count_nonzero(result.pmf_force_mask)),
        ):
            raise SourceControlSerializationError(
                "PMF-force overlay selected-count mismatch."
            )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Evidence-admissibility-overlay signature mismatch."
            )
        return result


def _diagnostic(regime: ProductionRegime, name: str) -> tuple[float | None, float | None]:
    for item in regime.diagnostics:
        if item.observable_name == name:
            return item.mean, item.standard_deviation
    return None, None


def _permission(
    regime: ProductionRegime,
    evidence_use: EvidenceUse,
    status: AdmissibilityStatus,
    measure: ThermodynamicMeasure,
    *,
    thermodynamic: bool,
    temperature_kelvin: float | None = None,
    temperature_source_signature: str | None = None,
    energy_shell_channel: str | None = None,
    energy_shell_source_signature: str | None = None,
    approximation_signature: str | None = None,
    reweighting_signature: str | None = None,
    reasons: Sequence[str] = (),
    evidence: Sequence[str] = (),
) -> AdmissibilityPermission:
    return AdmissibilityPermission(
        regime_id=regime.regime_id,
        evidence_use=evidence_use,
        status=status,
        measure=measure,
        thermodynamic=thermodynamic,
        temperature_kelvin=temperature_kelvin,
        temperature_source_signature=temperature_source_signature,
        energy_shell_channel=energy_shell_channel,
        energy_shell_source_signature=energy_shell_source_signature,
        approximation_signature=approximation_signature,
        reweighting_signature=reweighting_signature,
        reasons=tuple(reasons),
        evidence=tuple(evidence),
    )


def _scientific_base(
    regime: ProductionRegime,
    verdict: TrajectoryQualityVerdict,
    policy: EnsembleAdmissibilityPolicy,
) -> bool:
    if verdict.outcome is TrajectoryQualityOutcome.UNQUALIFIED:
        return False
    if (
        verdict.outcome is TrajectoryQualityOutcome.DEGRADED_QUALITY
        and not policy.allow_degraded_quality
    ):
        return False
    return regime.scientific_use_permitted


def assess_pmf_admissibility(
    *,
    simulation_control_certificate: SimulationControlCertificate,
    trajectory_quality_verdict: TrajectoryQualityVerdict,
    production_regime_catalog: ProductionRegimeCatalog,
    source_identity_signature: str,
    policy: EnsembleAdmissibilityPolicy | None = None,
    reweighting_provenance: ReweightingProvenance | None = None,
    approximation_provenance: EnsembleApproximationProvenance | None = None,
) -> PmfAdmissibilityCertificate:
    """Evaluate preliminary ensemble-specific permissions for each STAT1 regime."""

    _require_digest(source_identity_signature, name="source_identity_signature")
    if simulation_control_certificate.source_identity_signature != source_identity_signature:
        raise SourceControlError("STAT2 source identity does not match ENS1.")
    if trajectory_quality_verdict.source_identity_signature != source_identity_signature:
        raise SourceControlError("STAT2 source identity does not match STAT0.")
    if production_regime_catalog.source_identity_signature != source_identity_signature:
        raise SourceControlError("STAT2 source identity does not match STAT1.")
    if (
        trajectory_quality_verdict.simulation_control_certificate_signature
        != simulation_control_certificate.signature
    ):
        raise SourceControlError("STAT2 ENS1 and STAT0 signatures disagree.")
    if (
        production_regime_catalog.simulation_control_certificate_signature
        != simulation_control_certificate.signature
    ):
        raise SourceControlError("STAT2 ENS1 and STAT1 signatures disagree.")
    if (
        production_regime_catalog.trajectory_quality_verdict_signature
        != trajectory_quality_verdict.signature
    ):
        raise SourceControlError("STAT2 STAT0 and STAT1 signatures disagree.")

    active_policy = policy or EnsembleAdmissibilityPolicy()
    reweighting = reweighting_provenance or ReweightingProvenance(
        source_identity_signature=source_identity_signature
    )
    approximation = approximation_provenance or EnsembleApproximationProvenance(
        source_identity_signature=source_identity_signature
    )
    if reweighting.source_identity_signature != source_identity_signature:
        raise SourceControlError("Reweighting provenance belongs to another source.")
    if approximation.source_identity_signature != source_identity_signature:
        raise SourceControlError("Approximation provenance belongs to another source.")

    certificate = simulation_control_certificate
    verdict = trajectory_quality_verdict
    temperature_stats = verdict.temperature_statistics
    temperature_signature = (
        None if temperature_stats is None else temperature_stats.signature
    )
    energy_stats = verdict.energy_conservation
    energy_signature = energy_stats.signature

    records: list[RegimeAdmissibility] = []
    for regime in production_regime_catalog.regimes:
        scientific = _scientific_base(regime, verdict, active_policy)
        temp_mean, temp_sd = _diagnostic(regime, "ionic_temperature")
        if temp_mean is None and temperature_stats is not None:
            values = np.asarray(
                temperature_stats.temperatures_kelvin, dtype=np.float64
            )[regime.frame_start : regime.frame_stop]
            if values.size:
                temp_mean = float(np.mean(values))
                temp_sd = float(np.std(values))
        energy_name = {
            EnsembleKind.NVE: "total_energy",
            EnsembleKind.NPH: "total_energy",
        }.get(certificate.ensemble)
        shell_mean, shell_sd = (
            _diagnostic(regime, energy_name) if energy_name is not None else (None, None)
        )
        permissions: list[AdmissibilityPermission] = []

        if scientific:
            descriptive_status = AdmissibilityStatus.PERMITTED
            descriptive_reasons = ()
        elif (
            active_policy.allow_diagnostic_spatial_evidence
            and regime.production_interval_status
            in {
                ProductionIntervalStatus.DIAGNOSTIC_ONLY,
                ProductionIntervalStatus.INSUFFICIENT,
            }
            and (
                verdict.outcome is not TrajectoryQualityOutcome.UNQUALIFIED
                or active_policy.allow_unqualified_diagnostics
            )
        ):
            descriptive_status = AdmissibilityStatus.DIAGNOSTIC_ONLY
            descriptive_reasons = (
                "Stationarity or independent-block support is insufficient for thermodynamic promotion.",
            )
        else:
            descriptive_status = AdmissibilityStatus.BLOCKED
            descriptive_reasons = (
                "The regime is rejected or the source is unqualified for scientific use.",
            )
        permissions.append(
            _permission(
                regime,
                EvidenceUse.DESCRIPTIVE_DENSITY,
                descriptive_status,
                ThermodynamicMeasure.DESCRIPTIVE_SPATIAL,
                thermodynamic=False,
                reasons=descriptive_reasons,
                evidence=(
                    f"STAT1 interval={regime.production_interval_status.value}",
                    f"STAT0 quality={verdict.outcome.value}",
                ),
            )
        )
        diagnostic_status = (
            AdmissibilityStatus.PERMITTED
            if descriptive_status is AdmissibilityStatus.DIAGNOSTIC_ONLY
            else AdmissibilityStatus.NOT_APPLICABLE
        )
        permissions.append(
            _permission(
                regime,
                EvidenceUse.DIAGNOSTIC_ONLY,
                diagnostic_status,
                ThermodynamicMeasure.NONE,
                thermodynamic=False,
                reasons=(
                    "Diagnostic-only evidence carries no equilibrium or PMF interpretation.",
                )
                if diagnostic_status is AdmissibilityStatus.PERMITTED
                else (),
            )
        )

        bias_resolved = certificate.bias.status is InferenceStatus.RESOLVED
        bias_absent = bias_resolved and certificate.bias.active is False
        constraints_resolved = certificate.constraints.status is InferenceStatus.RESOLVED
        constraints_absent = constraints_resolved and certificate.constraints.active is False
        thermodynamic_control_ready = certificate.ensemble_dependent_methods_permitted

        micro_status = AdmissibilityStatus.NOT_APPLICABLE
        micro_reasons: tuple[str, ...] = ()
        if certificate.ensemble is EnsembleKind.NVE:
            if not scientific:
                micro_status = AdmissibilityStatus.BLOCKED
                micro_reasons = ("A scientific production regime is required.",)
            elif not thermodynamic_control_ready:
                micro_status = AdmissibilityStatus.UNRESOLVED
                micro_reasons = ("ENS1 ensemble interpretation is unresolved.",)
            elif not bias_absent:
                micro_status = (
                    AdmissibilityStatus.UNRESOLVED
                    if not bias_resolved
                    else AdmissibilityStatus.BLOCKED
                )
                micro_reasons = (
                    "Direct microcanonical occupancy requires affirmative inactive-bias evidence.",
                )
            elif (
                active_policy.require_resolved_constraints_for_thermodynamics
                and not constraints_resolved
            ):
                micro_status = AdmissibilityStatus.UNRESOLVED
                micro_reasons = ("Constraint evidence is unresolved.",)
            elif constraints_absent:
                micro_status = AdmissibilityStatus.PERMITTED
            else:
                micro_status = AdmissibilityStatus.CONDITIONAL
                micro_reasons = (
                    "Active constraints imply a constrained microcanonical measure.",
                )
        permissions.append(
            _permission(
                regime,
                EvidenceUse.MICROCANONICAL_OCCUPANCY,
                micro_status,
                ThermodynamicMeasure.MICROCANONICAL_ENERGY_SHELL,
                thermodynamic=True,
                energy_shell_channel=energy_stats.source_channel,
                energy_shell_source_signature=energy_signature,
                reasons=micro_reasons,
                evidence=(f"ENS1 ensemble={certificate.ensemble.value}",),
            )
        )

        canonical_status = AdmissibilityStatus.NOT_APPLICABLE
        canonical_reasons: tuple[str, ...] = ()
        canonical_approx_signature = None
        canonical_temperature = temp_mean
        canonical_temperature_source_signature = temperature_signature
        if certificate.ensemble is EnsembleKind.NVT:
            if not scientific:
                canonical_status = AdmissibilityStatus.BLOCKED
                canonical_reasons = ("A scientific production regime is required.",)
            elif not thermodynamic_control_ready:
                canonical_status = AdmissibilityStatus.UNRESOLVED
                canonical_reasons = ("ENS1 ensemble interpretation is unresolved.",)
            elif active_policy.require_resolved_bias_for_thermodynamics and not bias_resolved:
                canonical_status = AdmissibilityStatus.UNRESOLVED
                canonical_reasons = ("Bias evidence is unresolved.",)
            elif not bias_absent:
                canonical_status = AdmissibilityStatus.BLOCKED
                canonical_reasons = ("Active bias blocks a direct canonical landscape.",)
            elif (
                active_policy.require_resolved_constraints_for_thermodynamics
                and not constraints_resolved
            ):
                canonical_status = AdmissibilityStatus.UNRESOLVED
                canonical_reasons = ("Constraint evidence is unresolved.",)
            elif constraints_absent:
                canonical_status = AdmissibilityStatus.PERMITTED
            else:
                canonical_status = AdmissibilityStatus.CONDITIONAL
                canonical_reasons = (
                    "Active constraints imply a constrained canonical measure.",
                )
        elif certificate.ensemble is EnsembleKind.NVE:
            approximation_applies = (
                approximation.status is ApproximationStatus.ACCEPTED
                and regime.regime_id in approximation.applicable_regime_ids
            )
            if not scientific:
                canonical_status = AdmissibilityStatus.BLOCKED
                canonical_reasons = ("A scientific production regime is required.",)
            elif not approximation_applies:
                canonical_status = AdmissibilityStatus.BLOCKED
                canonical_reasons = (
                    "NVE density is not silently converted to a canonical PMF.",
                )
            elif not thermodynamic_control_ready:
                canonical_status = AdmissibilityStatus.UNRESOLVED
                canonical_reasons = ("ENS1 ensemble interpretation is unresolved.",)
            elif not bias_absent:
                canonical_status = (
                    AdmissibilityStatus.UNRESOLVED
                    if not bias_resolved
                    else AdmissibilityStatus.BLOCKED
                )
                canonical_reasons = (
                    "An NVE canonical approximation requires affirmative inactive-bias evidence.",
                )
            elif (
                active_policy.require_resolved_constraints_for_thermodynamics
                and not constraints_resolved
            ):
                canonical_status = AdmissibilityStatus.UNRESOLVED
                canonical_reasons = ("Constraint evidence is unresolved.",)
            else:
                canonical_status = AdmissibilityStatus.CONDITIONAL
                canonical_reasons = (
                    "Canonical interpretation is an explicit NVE approximation, not an exact ensemble identity.",
                    *(
                        ("Active constraints imply a constrained approximate measure.",)
                        if not constraints_absent
                        else ()
                    ),
                )
                canonical_approx_signature = approximation.signature
                canonical_temperature = approximation.target_temperature_kelvin
                canonical_temperature_source_signature = approximation.signature
        permissions.append(
            _permission(
                regime,
                EvidenceUse.CANONICAL_LANDSCAPE,
                canonical_status,
                ThermodynamicMeasure.CANONICAL_HELMHOLTZ,
                thermodynamic=True,
                temperature_kelvin=canonical_temperature,
                temperature_source_signature=(
                    canonical_temperature_source_signature
                ),
                approximation_signature=canonical_approx_signature,
                reasons=canonical_reasons,
                evidence=(f"ENS1 ensemble={certificate.ensemble.value}",),
            )
        )

        npt_status = AdmissibilityStatus.NOT_APPLICABLE
        npt_reasons: tuple[str, ...] = ()
        if certificate.ensemble is EnsembleKind.NPT:
            if not scientific:
                npt_status = AdmissibilityStatus.BLOCKED
                npt_reasons = ("A scientific production regime is required.",)
            elif not thermodynamic_control_ready:
                npt_status = AdmissibilityStatus.UNRESOLVED
                npt_reasons = ("ENS1 ensemble interpretation is unresolved.",)
            elif certificate.thermostat.active is not True or certificate.barostat.active is not True:
                npt_status = AdmissibilityStatus.UNRESOLVED
                npt_reasons = ("NpT requires resolved active thermostat and barostat.",)
            elif active_policy.require_resolved_bias_for_thermodynamics and not bias_resolved:
                npt_status = AdmissibilityStatus.UNRESOLVED
                npt_reasons = ("Bias evidence is unresolved.",)
            elif not bias_absent:
                npt_status = AdmissibilityStatus.BLOCKED
                npt_reasons = ("Active bias blocks a direct NpT landscape.",)
            elif (
                active_policy.require_resolved_constraints_for_thermodynamics
                and not constraints_resolved
            ):
                npt_status = AdmissibilityStatus.UNRESOLVED
                npt_reasons = ("Constraint evidence is unresolved.",)
            elif constraints_absent:
                npt_status = AdmissibilityStatus.PERMITTED
            else:
                npt_status = AdmissibilityStatus.CONDITIONAL
                npt_reasons = (
                    "Active constraints imply a constrained Gibbs measure.",
                )
        permissions.append(
            _permission(
                regime,
                EvidenceUse.NPT_LANDSCAPE,
                npt_status,
                ThermodynamicMeasure.ISOTHERMAL_ISOBARIC_GIBBS,
                thermodynamic=True,
                temperature_kelvin=temp_mean,
                temperature_source_signature=temperature_signature,
                reasons=npt_reasons,
                evidence=(
                    f"ENS1 ensemble={certificate.ensemble.value}",
                    "NpT landscape semantics are Gibbs/isothermal-isobaric.",
                ),
            )
        )

        if (
            scientific
            and reweighting.status is ReweightingStatus.VERIFIED
            and regime.regime_id in reweighting.applicable_regime_ids
        ):
            reweighted_status = AdmissibilityStatus.PERMITTED
            reweighted_reasons: tuple[str, ...] = ()
        elif reweighting.status is ReweightingStatus.DECLARED_ONLY:
            reweighted_status = AdmissibilityStatus.BLOCKED
            reweighted_reasons = (
                "Declared reweighting without verified finite normalized weights is insufficient.",
            )
        elif reweighting.status is ReweightingStatus.REJECTED:
            reweighted_status = AdmissibilityStatus.BLOCKED
            reweighted_reasons = ("Reweighting diagnostics rejected the supplied weights.",)
        else:
            reweighted_status = AdmissibilityStatus.NOT_APPLICABLE
            reweighted_reasons = ()
        permissions.append(
            _permission(
                regime,
                EvidenceUse.REWEIGHTED_LANDSCAPE,
                reweighted_status,
                ThermodynamicMeasure.REWEIGHTED_TARGET,
                thermodynamic=True,
                temperature_kelvin=reweighting.target_temperature_kelvin,
                reweighting_signature=(
                    reweighting.signature
                    if reweighting.status is not ReweightingStatus.NOT_PROVIDED
                    else None
                ),
                reasons=reweighted_reasons,
                evidence=(
                    f"reweighting_status={reweighting.status.value}",
                ),
            )
        )

        force = certificate.force_provenance
        if not scientific:
            force_status = AdmissibilityStatus.BLOCKED
            force_reasons = ("A scientific production regime is required.",)
        elif (
            active_policy.require_resolved_force_provenance
            and force.status is not InferenceStatus.RESOLVED
        ):
            force_status = AdmissibilityStatus.UNRESOLVED
            force_reasons = ("Source force provenance is unresolved.",)
        elif force.active is not True:
            force_status = AdmissibilityStatus.BLOCKED
            force_reasons = ("Complete source force arrays are unavailable.",)
        else:
            force_status = AdmissibilityStatus.CONDITIONAL
            force_reasons = (
                "Requires exact E0b joint evidence and C0 PMF-force admissibility.",
            )
        permissions.append(
            _permission(
                regime,
                EvidenceUse.CONDITIONAL_FORCE,
                force_status,
                ThermodynamicMeasure.CONDITIONAL_FORCE,
                thermodynamic=False,
                reasons=force_reasons,
                evidence=(
                    f"force_provider={force.kind}",
                    f"force_status={force.status.value}",
                ),
            )
        )

        records.append(
            RegimeAdmissibility(
                regime_id=regime.regime_id,
                production_regime_signature=regime.signature,
                frame_start=regime.frame_start,
                frame_stop=regime.frame_stop,
                ensemble=certificate.ensemble,
                quality_outcome=verdict.outcome,
                stationarity_status=regime.stationarity_status,
                production_interval_status=regime.production_interval_status,
                temperature_mean_kelvin=temp_mean,
                temperature_standard_deviation_kelvin=temp_sd,
                temperature_source_signature=temperature_signature,
                energy_shell_channel=energy_stats.source_channel,
                energy_shell_mean_ev=shell_mean,
                energy_shell_standard_deviation_ev=shell_sd,
                energy_shell_source_signature=energy_signature,
                permissions=tuple(permissions),
                notes=(
                    "STAT2 permissions do not certify SAMP or grid convergence.",
                    *(
                        ("STAT0 degraded-quality flags remain attached.",)
                        if verdict.outcome is TrajectoryQualityOutcome.DEGRADED_QUALITY
                        else ()
                    ),
                ),
            )
        )

    return PmfAdmissibilityCertificate(
        source_identity_signature=source_identity_signature,
        simulation_control_certificate_signature=certificate.signature,
        trajectory_quality_verdict_signature=verdict.signature,
        production_regime_catalog_signature=production_regime_catalog.signature,
        policy_signature=active_policy.signature,
        ensemble=certificate.ensemble,
        regime_admissibility=tuple(records),
        reweighting_provenance=reweighting,
        approximation_provenance=approximation,
        notes=(
            "No NVE density is silently converted to a canonical PMF.",
            "NpT landscape permission uses Gibbs/isothermal-isobaric semantics.",
            "Every permission is source-, policy-, and regime-bound.",
        ),
    )


def _mask_signature(mask: np.ndarray) -> str:
    return _digest(
        {
            "dtype": "bool",
            "shape": list(mask.shape),
            "sha256": _array_digest(mask),
        }
    )


def prepare_evidence_admissibility_overlay(
    sample_catalog: "FrameworkAlignedIonSampleCatalog",
    *,
    certificate: PmfAdmissibilityCertificate,
    production_regime_catalog: ProductionRegimeCatalog,
    regime_id: str,
) -> EvidenceAdmissibilityOverlay:
    """Intersect one E0b catalog with one exact STAT2 regime permission set."""

    from mdstats.analysis.site_samples import FrameworkAlignedIonSampleCatalog
    from mdstats.coordinates import PMFForceAdmissibilityStatus

    if not isinstance(sample_catalog, FrameworkAlignedIonSampleCatalog):
        raise TypeError("sample_catalog must be FrameworkAlignedIonSampleCatalog.")
    if certificate.production_regime_catalog_signature != production_regime_catalog.signature:
        raise SourceControlError("Overlay STAT2 and STAT1 signatures disagree.")
    if certificate.source_identity_signature != production_regime_catalog.source_identity_signature:
        raise SourceControlError("Overlay source identity does not match STAT1.")
    sample_source_identity = sample_catalog.metadata.get("source_identity_signature")
    if (
        not isinstance(sample_source_identity, str)
        or len(sample_source_identity) != 64
    ):
        raise SourceControlError(
            "E0b sample catalog lacks a signed source_identity_signature binding."
        )
    if sample_source_identity != certificate.source_identity_signature:
        raise SourceControlError("E0b sample catalog belongs to another source.")
    regime_record = certificate.regime(regime_id)
    source_regime = next(
        (item for item in production_regime_catalog.regimes if item.regime_id == regime_id),
        None,
    )
    if source_regime is None:
        raise SourceControlError(f"Unknown production regime {regime_id!r}.")
    if source_regime.signature != regime_record.production_regime_signature:
        raise SourceControlError("Overlay regime signature mismatch.")
    frames = np.asarray(sample_catalog.frame_indices, dtype=np.int64)
    if np.any(frames < 0) or np.any(frames >= production_regime_catalog.block_partition.frame_count):
        raise SourceControlError("Sample catalog frame indices lie outside STAT1 source.")
    regime_mask = (frames >= regime_record.frame_start) & (frames < regime_record.frame_stop)
    raw_position = np.asarray(sample_catalog.evidence_masks.position_mask, dtype=np.bool_)
    raw_joint = np.asarray(sample_catalog.evidence_masks.joint_mask, dtype=np.bool_)
    if raw_position.shape != regime_mask.shape or raw_joint.shape != regime_mask.shape:
        raise SourceControlError("E0b masks do not align with compact sample frames.")

    masks: list[EvidencePermissionMask] = []
    thermodynamic_enabled = False
    for use in (
        EvidenceUse.DESCRIPTIVE_DENSITY,
        EvidenceUse.MICROCANONICAL_OCCUPANCY,
        EvidenceUse.CANONICAL_LANDSCAPE,
        EvidenceUse.NPT_LANDSCAPE,
        EvidenceUse.REWEIGHTED_LANDSCAPE,
        EvidenceUse.CONDITIONAL_FORCE,
        EvidenceUse.DIAGNOSTIC_ONLY,
    ):
        permission = regime_record.permission(use)
        enabled = permission.enables_mask
        if use is EvidenceUse.CONDITIONAL_FORCE:
            base = raw_joint
            channel = EvidenceBaseChannel.JOINT
        else:
            base = raw_position
            channel = EvidenceBaseChannel.POSITION
        mask = base & regime_mask if enabled else np.zeros_like(base)
        if permission.thermodynamic and permission.status in {
            AdmissibilityStatus.PERMITTED,
            AdmissibilityStatus.CONDITIONAL,
        }:
            thermodynamic_enabled = True
        masks.append(
            EvidencePermissionMask(
                evidence_use=use,
                status=permission.status,
                base_channel=channel,
                sample_mask=mask,
            )
        )

    conditional_force_mask = next(
        item.sample_mask
        for item in masks
        if item.evidence_use is EvidenceUse.CONDITIONAL_FORCE
    )
    pmf_force_admissible = (
        sample_catalog.force_provenance.pmf_status
        is PMFForceAdmissibilityStatus.PMF_FORCE_ADMISSIBLE
    )
    pmf_force_mask = (
        conditional_force_mask
        if thermodynamic_enabled and pmf_force_admissible
        else np.zeros_like(conditional_force_mask)
    )
    notes = [
        "The overlay selects exactly one STAT1 regime and never pools regimes implicitly.",
        "Permission masks are exact intersections with immutable E0b raw masks.",
        f"pmf_force_selected_count={int(np.count_nonzero(pmf_force_mask))}",
    ]
    if not pmf_force_admissible:
        notes.append(
            "E0b PMF-force admissibility is not accepted; PMF force evidence remains empty."
        )
    elif not thermodynamic_enabled:
        notes.append(
            "No thermodynamic STAT2 permission is active; PMF force evidence remains empty."
        )

    return EvidenceAdmissibilityOverlay(
        source_identity_signature=certificate.source_identity_signature,
        sample_catalog_signature=sample_catalog.signature,
        pmf_admissibility_certificate_signature=certificate.signature,
        production_regime_catalog_signature=production_regime_catalog.signature,
        regime_id=regime_id,
        production_regime_signature=source_regime.signature,
        sample_count=sample_catalog.n_samples,
        permission_masks=tuple(masks),
        pmf_force_mask=pmf_force_mask,
        raw_position_mask_signature=_mask_signature(raw_position),
        raw_joint_mask_signature=_mask_signature(raw_joint),
        sample_force_provenance_signature=sample_catalog.force_provenance.signature,
        notes=tuple(notes),
    )


__all__ = [
    "ENSEMBLE_ADMISSIBILITY_POLICY_SCHEMA",
    "REWEIGHTING_PROVENANCE_SCHEMA",
    "ENSEMBLE_APPROXIMATION_PROVENANCE_SCHEMA",
    "ADMISSIBILITY_PERMISSION_SCHEMA",
    "REGIME_ADMISSIBILITY_SCHEMA",
    "PMF_ADMISSIBILITY_CERTIFICATE_SCHEMA",
    "EVIDENCE_PERMISSION_MASK_SCHEMA",
    "EVIDENCE_ADMISSIBILITY_OVERLAY_SCHEMA",
    "ENSEMBLE_ADMISSIBILITY_POLICY_VERSION",
    "AdmissibilityStatus",
    "EvidenceUse",
    "ThermodynamicMeasure",
    "ReweightingStatus",
    "ApproximationStatus",
    "EvidenceBaseChannel",
    "EnsembleAdmissibilityPolicy",
    "ReweightingProvenance",
    "EnsembleApproximationProvenance",
    "AdmissibilityPermission",
    "RegimeAdmissibility",
    "PmfAdmissibilityCertificate",
    "EvidencePermissionMask",
    "EvidenceAdmissibilityOverlay",
    "assess_pmf_admissibility",
    "prepare_evidence_admissibility_overlay",
]
