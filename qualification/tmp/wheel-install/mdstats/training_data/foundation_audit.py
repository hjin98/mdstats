"""FOUNDATION-AUDIT1 target-side zero-shot baseline authority.

The foundation audit is deliberately built from the already completed DATA6
foundation prediction sweep.  No extra model inference is required.  The audit
freezes the exact TARGET-DATA2A development domain, metric policy, structural
conditioning channels, and foundation checkpoint identity before any target
training is authorized.

Later candidate evaluators should reduce their predictions through the same
``TargetModelAuditPolicy``/metric semantics rather than inventing a second
notion of target adequacy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import tempfile
from typing import Any, Mapping, Sequence

import numpy as np
from ase.data import chemical_symbols

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._frame_access import build_frame_array_index
from .difficulty import TrainingDifficultyDomainKind
from .production_model_sweep import read_atomic_model_prediction
from .foundation import FoundationPotentialIdentity, FoundationInferenceIdentity

TARGET_MODEL_AUDIT_POLICY_SCHEMA = "mdstats.target-model-audit-policy.v1"
TARGET_MODEL_SPECIES_FORCE_METRIC_SCHEMA = "mdstats.target-model-species-force-metric.v1"
TARGET_MODEL_FORCE_TAIL_SCHEMA = "mdstats.target-model-force-tail.v1"
TARGET_MODEL_CONDITIONED_BIN_SCHEMA = "mdstats.target-model-conditioned-force-bin.v1"
TARGET_MODEL_CONDITIONED_SUMMARY_SCHEMA = "mdstats.target-model-conditioned-force-summary.v1"
TARGET_MODEL_AUDIT_METRICS_SCHEMA = "mdstats.target-model-audit-metrics.v1"
FOUNDATION_AUDIT_PROBE_CONTRACT_SCHEMA = "mdstats.foundation-audit-probe-contract.v1"
FOUNDATION_AUDIT_DOMAIN_SCHEMA = "mdstats.foundation-audit-domain.v1"
FOUNDATION_TARGET_AUDIT_SCHEMA = "mdstats.foundation-target-audit.v2"
FOUNDATION_TARGET_AUDIT_V1_SCHEMA = "mdstats.foundation-target-audit.v1"
FOUNDATION_AUDIT_VERSION = "mdstats.foundation-audit1.target-baseline.2026-08.v1"


def _finite_nonnegative(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
    return result


def _normalized_quantiles(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result or any(not math.isfinite(value) or value <= 0.0 or value >= 1.0 for value in result):
        raise TrainingDataInputError(f"{name} must contain finite open-unit-interval quantiles.")
    if any(left >= right for left, right in zip(result, result[1:])):
        raise TrainingDataInputError(f"{name} must be strictly increasing.")
    return result


@dataclass(frozen=True, slots=True)
class TargetModelAuditPolicy:
    """Metric semantics shared by foundation and later target candidates."""

    force_tail_quantiles: tuple[float, ...] = (0.90, 0.95, 0.99)
    conditioned_quantile_edges: tuple[float, ...] = (0.0, 0.25, 0.50, 0.75, 1.0)
    conditioned_feature_families: tuple[str, ...] = (
        "pair_distance",
        "angular_environment",
        "coordination",
    )
    force_tail_semantics: str = "per_atom_vector_error_norm"
    policy_version: str = FOUNDATION_AUDIT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "force_tail_quantiles",
            _normalized_quantiles(self.force_tail_quantiles, name="force_tail_quantiles"),
        )
        edges = tuple(float(value) for value in self.conditioned_quantile_edges)
        if (
            len(edges) < 2
            or edges[0] != 0.0
            or edges[-1] != 1.0
            or any(not math.isfinite(value) or value < 0.0 or value > 1.0 for value in edges)
            or any(left >= right for left, right in zip(edges, edges[1:]))
        ):
            raise TrainingDataInputError(
                "conditioned_quantile_edges must be strictly increasing from 0 to 1."
            )
        families = tuple(str(value).strip() for value in self.conditioned_feature_families)
        allowed = {"pair_distance", "angular_environment", "coordination"}
        if not families or len(set(families)) != len(families) or any(value not in allowed for value in families):
            raise TrainingDataInputError("conditioned_feature_families are invalid.")
        if self.force_tail_semantics != "per_atom_vector_error_norm":
            raise TrainingDataInputError("Unsupported FOUNDATION-AUDIT1 force-tail semantics.")
        if not str(self.policy_version).strip():
            raise TrainingDataInputError("FOUNDATION-AUDIT1 policy_version must be non-empty.")
        object.__setattr__(self, "conditioned_quantile_edges", edges)
        object.__setattr__(self, "conditioned_feature_families", families)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MODEL_AUDIT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "force_tail_quantiles": list(self.force_tail_quantiles),
            "conditioned_quantile_edges": list(self.conditioned_quantile_edges),
            "conditioned_feature_families": list(self.conditioned_feature_families),
            "force_tail_semantics": self.force_tail_semantics,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetModelAuditPolicy":
        if payload.get("schema") != TARGET_MODEL_AUDIT_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-model-audit policy schema.")
        result = cls(
            force_tail_quantiles=tuple(float(v) for v in payload["force_tail_quantiles"]),
            conditioned_quantile_edges=tuple(float(v) for v in payload["conditioned_quantile_edges"]),
            conditioned_feature_families=tuple(str(v) for v in payload["conditioned_feature_families"]),
            force_tail_semantics=str(payload["force_tail_semantics"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Target-model-audit policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetModelSpeciesForceMetric:
    atomic_number: int
    symbol: str
    atom_count: int
    component_rmse_ev_per_angstrom: float

    def __post_init__(self) -> None:
        if self.atomic_number <= 0 or self.atom_count <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid target-model species force metric identity.")
        object.__setattr__(
            self,
            "component_rmse_ev_per_angstrom",
            _finite_nonnegative(
                self.component_rmse_ev_per_angstrom,
                name="component_rmse_ev_per_angstrom",
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MODEL_SPECIES_FORCE_METRIC_SCHEMA,
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "atom_count": self.atom_count,
            "component_rmse_ev_per_angstrom": self.component_rmse_ev_per_angstrom,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetModelSpeciesForceMetric":
        if payload.get("schema") != TARGET_MODEL_SPECIES_FORCE_METRIC_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-model species metric schema.")
        result = cls(
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            atom_count=int(payload["atom_count"]),
            component_rmse_ev_per_angstrom=float(payload["component_rmse_ev_per_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-model species metric digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetModelForceTailMetric:
    quantile: float
    vector_error_ev_per_angstrom: float
    component_abs_error_ev_per_angstrom: float

    def __post_init__(self) -> None:
        quantile = float(self.quantile)
        if not math.isfinite(quantile) or quantile <= 0.0 or quantile >= 1.0:
            raise TrainingDataInputError("Force-tail quantile must lie in (0, 1).")
        object.__setattr__(self, "quantile", quantile)
        for name in ("vector_error_ev_per_angstrom", "component_abs_error_ev_per_angstrom"):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MODEL_FORCE_TAIL_SCHEMA,
            "quantile": self.quantile,
            "vector_error_ev_per_angstrom": self.vector_error_ev_per_angstrom,
            "component_abs_error_ev_per_angstrom": self.component_abs_error_ev_per_angstrom,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetModelForceTailMetric":
        if payload.get("schema") != TARGET_MODEL_FORCE_TAIL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-model force-tail schema.")
        result = cls(
            quantile=float(payload["quantile"]),
            vector_error_ev_per_angstrom=float(payload["vector_error_ev_per_angstrom"]),
            component_abs_error_ev_per_angstrom=float(payload["component_abs_error_ev_per_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-model force-tail digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetModelConditionedForceBin:
    quantile_low: float
    quantile_high: float
    feature_value_low: float
    feature_value_high: float
    configuration_count: int
    force_component_rmse_ev_per_angstrom: float

    def __post_init__(self) -> None:
        q0, q1 = float(self.quantile_low), float(self.quantile_high)
        if not (0.0 <= q0 < q1 <= 1.0):
            raise TrainingDataInputError("Conditioned-force bin quantiles are invalid.")
        lo, hi = float(self.feature_value_low), float(self.feature_value_high)
        if not math.isfinite(lo) or not math.isfinite(hi) or lo > hi:
            raise TrainingDataInputError("Conditioned-force feature interval is invalid.")
        if int(self.configuration_count) <= 0:
            raise TrainingDataInputError("Conditioned-force bins must contain at least one configuration.")
        object.__setattr__(self, "quantile_low", q0)
        object.__setattr__(self, "quantile_high", q1)
        object.__setattr__(self, "feature_value_low", lo)
        object.__setattr__(self, "feature_value_high", hi)
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        object.__setattr__(
            self,
            "force_component_rmse_ev_per_angstrom",
            _finite_nonnegative(
                self.force_component_rmse_ev_per_angstrom,
                name="force_component_rmse_ev_per_angstrom",
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MODEL_CONDITIONED_BIN_SCHEMA,
            "quantile_low": self.quantile_low,
            "quantile_high": self.quantile_high,
            "feature_value_low": self.feature_value_low,
            "feature_value_high": self.feature_value_high,
            "configuration_count": self.configuration_count,
            "force_component_rmse_ev_per_angstrom": self.force_component_rmse_ev_per_angstrom,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetModelConditionedForceBin":
        if payload.get("schema") != TARGET_MODEL_CONDITIONED_BIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported conditioned-force bin schema.")
        result = cls(
            quantile_low=float(payload["quantile_low"]),
            quantile_high=float(payload["quantile_high"]),
            feature_value_low=float(payload["feature_value_low"]),
            feature_value_high=float(payload["feature_value_high"]),
            configuration_count=int(payload["configuration_count"]),
            force_component_rmse_ev_per_angstrom=float(payload["force_component_rmse_ev_per_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Conditioned-force bin digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetModelConditionedForceSummary:
    feature_family: str
    feature_name: str
    bins: tuple[TargetModelConditionedForceBin, ...]

    def __post_init__(self) -> None:
        if self.feature_family not in {"pair_distance", "angular_environment", "coordination"}:
            raise TrainingDataInputError("Conditioned-force feature family is invalid.")
        if not self.feature_name.strip():
            raise TrainingDataInputError("Conditioned-force feature name must be non-empty.")
        bins = tuple(self.bins)
        if not bins:
            raise TrainingDataInputError("Conditioned-force summary requires bins.")
        if any(left.quantile_high > right.quantile_low for left, right in zip(bins, bins[1:])):
            raise TrainingDataInputError("Conditioned-force bins must be ordered and non-overlapping in quantile space.")
        object.__setattr__(self, "bins", bins)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MODEL_CONDITIONED_SUMMARY_SCHEMA,
            "feature_family": self.feature_family,
            "feature_name": self.feature_name,
            "bins": [item.to_dict() for item in self.bins],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetModelConditionedForceSummary":
        if payload.get("schema") != TARGET_MODEL_CONDITIONED_SUMMARY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported conditioned-force summary schema.")
        result = cls(
            feature_family=str(payload["feature_family"]),
            feature_name=str(payload["feature_name"]),
            bins=tuple(TargetModelConditionedForceBin.from_dict(item) for item in payload["bins"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Conditioned-force summary digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetModelAuditMetrics:
    configuration_count: int
    atom_count: int
    stress_configuration_count: int
    energy_mae_ev_per_atom: float
    force_component_rmse_ev_per_angstrom: float
    stress_component_rmse_ev_per_angstrom3: float | None
    species_macro_force_rmse_ev_per_angstrom: float
    species_force_metrics: tuple[TargetModelSpeciesForceMetric, ...]
    force_tail_metrics: tuple[TargetModelForceTailMetric, ...]
    conditioned_force_summaries: tuple[TargetModelConditionedForceSummary, ...] = ()

    def __post_init__(self) -> None:
        if int(self.configuration_count) <= 0 or int(self.atom_count) <= 0:
            raise TrainingDataInputError("Target-model audit counts must be positive.")
        if int(self.stress_configuration_count) < 0 or int(self.stress_configuration_count) > int(self.configuration_count):
            raise TrainingDataInputError("Target-model audit stress count is invalid.")
        object.__setattr__(self, "configuration_count", int(self.configuration_count))
        object.__setattr__(self, "atom_count", int(self.atom_count))
        object.__setattr__(self, "stress_configuration_count", int(self.stress_configuration_count))
        for name in (
            "energy_mae_ev_per_atom",
            "force_component_rmse_ev_per_angstrom",
            "species_macro_force_rmse_ev_per_angstrom",
        ):
            object.__setattr__(self, name, _finite_nonnegative(getattr(self, name), name=name))
        if self.stress_component_rmse_ev_per_angstrom3 is not None:
            object.__setattr__(
                self,
                "stress_component_rmse_ev_per_angstrom3",
                _finite_nonnegative(
                    self.stress_component_rmse_ev_per_angstrom3,
                    name="stress_component_rmse_ev_per_angstrom3",
                ),
            )
        species = tuple(sorted(self.species_force_metrics, key=lambda item: item.atomic_number))
        tails = tuple(sorted(self.force_tail_metrics, key=lambda item: item.quantile))
        conditioned = tuple(
            sorted(
                self.conditioned_force_summaries,
                key=lambda item: (item.feature_family, item.feature_name),
            )
        )
        if not species or not tails:
            raise TrainingDataInputError("Target-model audit requires species and tail metrics.")
        object.__setattr__(self, "species_force_metrics", species)
        object.__setattr__(self, "force_tail_metrics", tails)
        object.__setattr__(self, "conditioned_force_summaries", conditioned)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MODEL_AUDIT_METRICS_SCHEMA,
            "configuration_count": self.configuration_count,
            "atom_count": self.atom_count,
            "stress_configuration_count": self.stress_configuration_count,
            "energy_mae_ev_per_atom": self.energy_mae_ev_per_atom,
            "force_component_rmse_ev_per_angstrom": self.force_component_rmse_ev_per_angstrom,
            "stress_component_rmse_ev_per_angstrom3": self.stress_component_rmse_ev_per_angstrom3,
            "species_macro_force_rmse_ev_per_angstrom": self.species_macro_force_rmse_ev_per_angstrom,
            "species_force_metrics": [item.to_dict() for item in self.species_force_metrics],
            "force_tail_metrics": [item.to_dict() for item in self.force_tail_metrics],
            "conditioned_force_summaries": [item.to_dict() for item in self.conditioned_force_summaries],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetModelAuditMetrics":
        if payload.get("schema") != TARGET_MODEL_AUDIT_METRICS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported target-model audit metrics schema.")
        result = cls(
            configuration_count=int(payload["configuration_count"]),
            atom_count=int(payload["atom_count"]),
            stress_configuration_count=int(payload["stress_configuration_count"]),
            energy_mae_ev_per_atom=float(payload["energy_mae_ev_per_atom"]),
            force_component_rmse_ev_per_angstrom=float(payload["force_component_rmse_ev_per_angstrom"]),
            stress_component_rmse_ev_per_angstrom3=(
                None
                if payload.get("stress_component_rmse_ev_per_angstrom3") is None
                else float(payload["stress_component_rmse_ev_per_angstrom3"])
            ),
            species_macro_force_rmse_ev_per_angstrom=float(payload["species_macro_force_rmse_ev_per_angstrom"]),
            species_force_metrics=tuple(TargetModelSpeciesForceMetric.from_dict(item) for item in payload["species_force_metrics"]),
            force_tail_metrics=tuple(TargetModelForceTailMetric.from_dict(item) for item in payload["force_tail_metrics"]),
            conditioned_force_summaries=tuple(
                TargetModelConditionedForceSummary.from_dict(item)
                for item in payload.get("conditioned_force_summaries", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Target-model audit metrics digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FoundationAuditProbeContract:
    """Frozen identity/status slot for a physical probe family.

    FOUNDATION-AUDIT1 freezes these slots even when the exact PES/relaxation
    protocol is intentionally deferred to its later gate.  A later candidate
    comparison may not claim matched probe evidence unless the foundation side
    is materialized under the same frozen probe identity.
    """

    probe_id: str
    status: str
    evidence_digest: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.probe_id.strip():
            raise TrainingDataInputError("Foundation-audit probe_id must be non-empty.")
        allowed = {"materialized", "not_available", "deferred_protocol"}
        if self.status not in allowed:
            raise TrainingDataInputError("Foundation-audit probe status is invalid.")
        if self.status == "materialized" and self.evidence_digest is None:
            raise TrainingDataInputError("Materialized foundation probes require evidence_digest.")
        if self.status != "materialized" and self.evidence_digest is not None:
            raise TrainingDataInputError("Unmaterialized foundation probes cannot claim evidence_digest.")
        if self.evidence_digest is not None:
            object.__setattr__(self, "evidence_digest", validate_digest(self.evidence_digest, name="evidence_digest"))
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FOUNDATION_AUDIT_PROBE_CONTRACT_SCHEMA,
            "probe_id": self.probe_id,
            "status": self.status,
            "evidence_digest": self.evidence_digest,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationAuditProbeContract":
        if payload.get("schema") != FOUNDATION_AUDIT_PROBE_CONTRACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported foundation-audit probe schema.")
        result = cls(
            probe_id=str(payload["probe_id"]),
            status=str(payload["status"]),
            evidence_digest=None if payload.get("evidence_digest") is None else str(payload["evidence_digest"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Foundation-audit probe digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FoundationAuditDomainRecord:
    label_domain_id: str
    frame_uids: tuple[str, ...]
    frame_domain_digest: str
    training_difficulty_catalog_digest: str
    metrics: TargetModelAuditMetrics

    def __post_init__(self) -> None:
        if not self.label_domain_id.strip():
            raise TrainingDataInputError("Foundation-audit label domain must be non-empty.")
        frames = tuple(validate_digest(value, name="frame_uid") for value in self.frame_uids)
        if not frames or len(set(frames)) != len(frames):
            raise TrainingDataInputError("Foundation-audit domain frames must be unique and non-empty.")
        object.__setattr__(self, "frame_uids", frames)
        for name in ("frame_domain_digest", "training_difficulty_catalog_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        expected = digest({"schema": "mdstats.foundation-audit-frame-domain.v1", "label_domain_id": self.label_domain_id, "frame_uids": list(frames)})
        if self.frame_domain_digest != expected:
            raise TrainingDataInputError("Foundation-audit frame-domain digest mismatch.")
        if self.metrics.configuration_count != len(frames):
            raise TrainingDataInputError("Foundation-audit metric/domain count mismatch.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FOUNDATION_AUDIT_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "frame_uids": list(self.frame_uids),
            "frame_domain_digest": self.frame_domain_digest,
            "training_difficulty_catalog_digest": self.training_difficulty_catalog_digest,
            "metrics": self.metrics.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationAuditDomainRecord":
        if payload.get("schema") != FOUNDATION_AUDIT_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported foundation-audit domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            frame_uids=tuple(str(value) for value in payload["frame_uids"]),
            frame_domain_digest=str(payload["frame_domain_digest"]),
            training_difficulty_catalog_digest=str(payload["training_difficulty_catalog_digest"]),
            metrics=TargetModelAuditMetrics.from_dict(payload["metrics"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Foundation-audit domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FoundationTargetAudit:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data5_bundle_digest: str
    data6_bundle_digest: str
    target_data_role_freeze_digest: str
    foundation_checkpoint_identity_digest: str
    foundation_checkpoint_sha256: str
    model_sweep_checkpoint_digest: str
    structural_provider_digests: tuple[str, ...]
    policy: TargetModelAuditPolicy
    domains: tuple[FoundationAuditDomainRecord, ...]
    probe_contracts: tuple[FoundationAuditProbeContract, ...]
    foundation_potential_identity: FoundationPotentialIdentity | None = None
    foundation_inference_identity: FoundationInferenceIdentity | None = None
    audit_version: str = FOUNDATION_AUDIT_VERSION
    serialization_schema: str = field(default=FOUNDATION_TARGET_AUDIT_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.dataset_id.strip() or not self.audit_version.strip():
            raise TrainingDataInputError("Foundation-audit identifiers must be non-empty.")
        if self.serialization_schema not in {FOUNDATION_TARGET_AUDIT_SCHEMA, FOUNDATION_TARGET_AUDIT_V1_SCHEMA}:
            raise TrainingDataInputError("Unsupported foundation-target-audit serialization schema.")
        if (self.foundation_potential_identity is None) != (self.foundation_inference_identity is None):
            raise TrainingDataInputError("Foundation audit potential/inference identities must be both present or both absent.")
        if self.foundation_potential_identity is None and self.serialization_schema == FOUNDATION_TARGET_AUDIT_SCHEMA:
            # Preserve historical direct-construction semantics/digests.
            object.__setattr__(self, "serialization_schema", FOUNDATION_TARGET_AUDIT_V1_SCHEMA)
        if self.foundation_potential_identity is not None:
            if self.serialization_schema != FOUNDATION_TARGET_AUDIT_SCHEMA:
                raise TrainingDataInputError("Canonical foundation audit identities require the v2 schema.")
            if self.foundation_inference_identity.foundation_potential_digest != self.foundation_potential_identity.canonical_content_digest:
                raise TrainingDataInputError("Foundation audit inference/potential identities disagree.")
            if self.foundation_checkpoint_sha256 != self.foundation_potential_identity.sha256:
                raise TrainingDataInputError("Foundation audit checkpoint SHA disagrees with the canonical potential identity.")
        for name in (
            "source_catalog_digest",
            "frame_catalog_digest",
            "data5_bundle_digest",
            "data6_bundle_digest",
            "target_data_role_freeze_digest",
            "foundation_checkpoint_identity_digest",
            "foundation_checkpoint_sha256",
            "model_sweep_checkpoint_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        structural = tuple(sorted(validate_digest(value, name="structural_provider_digest") for value in self.structural_provider_digests))
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        probes = tuple(sorted(self.probe_contracts, key=lambda item: item.probe_id))
        if not domains or len({item.label_domain_id for item in domains}) != len(domains):
            raise TrainingDataInputError("Foundation-audit domains must be unique and non-empty.")
        if len({item.probe_id for item in probes}) != len(probes):
            raise TrainingDataInputError("Foundation-audit probe IDs must be unique.")
        object.__setattr__(self, "structural_provider_digests", structural)
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "probe_contracts", probes)

    def domain(self, label_domain_id: str) -> FoundationAuditDomainRecord:
        for item in self.domains:
            if item.label_domain_id == label_domain_id:
                return item
        raise KeyError(label_domain_id)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "audit_version": self.audit_version,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "foundation_checkpoint_identity_digest": self.foundation_checkpoint_identity_digest,
            "foundation_checkpoint_sha256": self.foundation_checkpoint_sha256,
            "model_sweep_checkpoint_digest": self.model_sweep_checkpoint_digest,
            "structural_provider_digests": list(self.structural_provider_digests),
            "policy": self.policy.to_dict(),
            "domains": [item.to_dict() for item in self.domains],
            "probe_contracts": [item.to_dict() for item in self.probe_contracts],
            **(
                {
                    "foundation_potential_identity": self.foundation_potential_identity.to_dict(),
                    "foundation_inference_identity": self.foundation_inference_identity.to_dict(),
                }
                if self.serialization_schema == FOUNDATION_TARGET_AUDIT_SCHEMA
                else {}
            ),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationTargetAudit":
        if payload.get("schema") not in {FOUNDATION_TARGET_AUDIT_SCHEMA, FOUNDATION_TARGET_AUDIT_V1_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported foundation-target-audit schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            data6_bundle_digest=str(payload["data6_bundle_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            foundation_checkpoint_identity_digest=str(payload["foundation_checkpoint_identity_digest"]),
            foundation_checkpoint_sha256=str(payload["foundation_checkpoint_sha256"]),
            model_sweep_checkpoint_digest=str(payload["model_sweep_checkpoint_digest"]),
            structural_provider_digests=tuple(str(value) for value in payload.get("structural_provider_digests", ())),
            policy=TargetModelAuditPolicy.from_dict(payload["policy"]),
            domains=tuple(FoundationAuditDomainRecord.from_dict(item) for item in payload["domains"]),
            probe_contracts=tuple(FoundationAuditProbeContract.from_dict(item) for item in payload.get("probe_contracts", ())),
            foundation_potential_identity=(None if payload.get("foundation_potential_identity") is None else FoundationPotentialIdentity.from_dict(payload["foundation_potential_identity"])),
            foundation_inference_identity=(None if payload.get("foundation_inference_identity") is None else FoundationInferenceIdentity.from_dict(payload["foundation_inference_identity"])),
            audit_version=str(payload["audit_version"]),
            serialization_schema=str(payload["schema"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Foundation-target-audit digest mismatch.")
        return result


def _structural_base_feature(name: str) -> tuple[str, str] | None:
    """Return (family, base feature) for an aggregated structural channel."""

    parts = str(name).split(":")
    if len(parts) < 4 or parts[0] != "group":
        return None
    base = parts[-2]
    if base in {
        "nearest_neighbor_distance_angstrom",
        "weighted_neighbor_distance_mean_angstrom",
        "weighted_neighbor_distance_std_angstrom",
    }:
        return "pair_distance", base
    if base.startswith("angular_legendre_"):
        return "angular_environment", base
    if base == "smooth_coordination":
        return "coordination", base
    return None


def _conditioned_summaries(
    *,
    frame_uids: Sequence[str],
    frame_force_component_mse: np.ndarray,
    structural_catalogs: Sequence[Any],
    policy: TargetModelAuditPolicy,
) -> tuple[TargetModelConditionedForceSummary, ...]:
    if not structural_catalogs:
        return ()
    requested = tuple(frame_uids)
    selected_families = set(policy.conditioned_feature_families)
    results: list[TargetModelConditionedForceSummary] = []
    # DATA6 currently owns one universal provider by default, but the reducer is
    # intentionally provider-generic and namespaces channels by provider digest.
    for catalog in structural_catalogs:
        try:
            feature_names, values, missing = catalog.frame_feature_matrix(requested)
        except (KeyError, TrainingDataInputError):
            continue
        values = np.asarray(values, dtype=np.float64)
        missing = np.asarray(missing, dtype=np.bool_)
        for column, feature_name in enumerate(feature_names):
            parsed = _structural_base_feature(feature_name)
            if parsed is None or parsed[0] not in selected_families:
                continue
            family, _ = parsed
            valid = ~missing[:, column]
            if np.count_nonzero(valid) < 2:
                continue
            x = values[valid, column]
            mse = frame_force_component_mse[valid]
            edges = np.quantile(x, np.asarray(policy.conditioned_quantile_edges, dtype=np.float64))
            bins: list[TargetModelConditionedForceBin] = []
            for index, (q0, q1) in enumerate(zip(policy.conditioned_quantile_edges, policy.conditioned_quantile_edges[1:])):
                lo, hi = float(edges[index]), float(edges[index + 1])
                if index == len(policy.conditioned_quantile_edges) - 2:
                    selected = (x >= lo) & (x <= hi)
                else:
                    selected = (x >= lo) & (x < hi)
                if not np.any(selected):
                    # Repeated feature values can collapse quantile intervals.
                    # Skip empty bins rather than fabricating evidence.
                    continue
                bins.append(
                    TargetModelConditionedForceBin(
                        quantile_low=float(q0),
                        quantile_high=float(q1),
                        feature_value_low=lo,
                        feature_value_high=hi,
                        configuration_count=int(np.count_nonzero(selected)),
                        force_component_rmse_ev_per_angstrom=float(np.sqrt(np.mean(mse[selected]))),
                    )
                )
            if not bins:
                continue
            results.append(
                TargetModelConditionedForceSummary(
                    feature_family=family,
                    feature_name=f"{catalog.provider_identity.content_digest}:{feature_name}",
                    bins=tuple(bins),
                )
            )
    return tuple(results)


def _metrics_for_domain(
    *,
    frame_uids: Sequence[str],
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    prediction_manifest: Any,
    prediction_root: str,
    structural_catalogs: Sequence[Any],
    policy: TargetModelAuditPolicy,
    temporary_memory_threshold_bytes: int | None = None,
    temporary_directory: str | None = None,
    frame_array_index: Mapping[str, Any] | None = None,
    species_groups_by_frame_data: Mapping[int, tuple[tuple[int, np.ndarray], ...]] | None = None,
) -> TargetModelAuditMetrics:
    # AUDIT-EVAL-PERF1 lets all domains share the immutable DATA3 frame index and
    # per-run species membership.  Direct callers retain the historical local
    # construction path when these execution-only caches are omitted.
    index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    frame_uids_tuple = tuple(str(value) for value in frame_uids)
    if not frame_uids_tuple:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 domain is empty.")
    total_atoms_expected = 0
    for frame_uid in frame_uids_tuple:
        if frame_uid not in index:
            raise TrainingDataInputError("Foundation-audit frame is absent from the frame-array index.")
        record, _frame_data, _local_index = index[frame_uid]
        total_atoms_expected += int(record.atom_count)
    if total_atoms_expected <= 0:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 domain has no atoms.")

    threshold = temporary_memory_threshold_bytes
    if threshold is not None and int(threshold) <= 0:
        raise TrainingDataInputError("temporary_memory_threshold_bytes must be positive when provided.")
    tail_bytes = total_atoms_expected * 4 * np.dtype(np.float64).itemsize
    use_mmap = threshold is not None and tail_bytes > int(threshold)
    temporary = tempfile.TemporaryDirectory(
        prefix="mdstats-foundation-audit-", dir=temporary_directory
    ) if use_mmap else None
    if temporary is None:
        vector = np.empty(total_atoms_expected, dtype=np.float64)
        component_abs = np.empty(total_atoms_expected * 3, dtype=np.float64)
    else:
        root = temporary.name
        vector = np.memmap(
            f"{root}/vector-errors.bin", mode="w+", dtype=np.float64,
            shape=(total_atoms_expected,),
        )
        component_abs = np.memmap(
            f"{root}/component-abs-errors.bin", mode="w+", dtype=np.float64,
            shape=(total_atoms_expected * 3,),
        )
    energy_abs_per_atom = np.empty(len(frame_uids_tuple), dtype=np.float64)
    frame_mse = np.empty(len(frame_uids_tuple), dtype=np.float64)
    force_sq_sum = 0.0
    force_component_count = 0
    stress_sq_sum = 0.0
    stress_component_count = 0
    stress_configuration_count = 0
    species_sq_sum: dict[int, float] = {}
    species_component_count: dict[int, int] = {}
    species_atom_count: dict[int, int] = {}
    total_atoms = 0
    vector_cursor = 0
    component_cursor = 0

    for frame_position, frame_uid in enumerate(frame_uids_tuple):
        record, frame_data, local_index = index[frame_uid]
        if frame_data.energies_ev is None or frame_data.forces_ev_per_angstrom is None:
            raise TrainingDataInputError("FOUNDATION-AUDIT1 requires DFT energy and force labels on every authorized development frame.")
        prediction = read_atomic_model_prediction(prediction_manifest, prediction_root, frame_uid)
        reference_energy = float(frame_data.energies_ev[local_index])
        reference_forces = np.asarray(frame_data.forces_ev_per_angstrom[local_index], dtype=np.float64)
        predicted_forces = np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)
        if reference_forces.shape != predicted_forces.shape or reference_forces.ndim != 2 or reference_forces.shape[1] != 3:
            raise TrainingDataInputError("Foundation-audit prediction/reference force shape mismatch.")
        natoms = int(reference_forces.shape[0])
        if natoms != int(record.atom_count):
            raise TrainingDataInputError("Foundation-audit frame atom count disagrees with DATA3.")
        total_atoms += natoms
        energy_abs_per_atom[frame_position] = abs(float(prediction.energy_ev) - reference_energy) / natoms
        delta = predicted_forces - reference_forces
        delta_sq = delta * delta
        mse = float(np.mean(delta_sq))
        frame_mse[frame_position] = mse
        force_sq_sum += float(np.sum(delta_sq))
        force_component_count += int(delta.size)
        vector[vector_cursor : vector_cursor + natoms] = np.linalg.norm(delta, axis=1)
        vector_cursor += natoms
        flat_abs = np.abs(delta).reshape(-1)
        component_abs[component_cursor : component_cursor + flat_abs.size] = flat_abs
        component_cursor += flat_abs.size
        numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
        if numbers.shape != (natoms,):
            raise TrainingDataInputError("Foundation-audit atomic-number array is misaligned.")
        groups = None if species_groups_by_frame_data is None else species_groups_by_frame_data.get(id(frame_data))
        if groups is None:
            groups = tuple(
                (int(atomic_number), np.flatnonzero(numbers == atomic_number).astype(np.int32, copy=False))
                for atomic_number in np.unique(numbers)
            )
        for z, local_indices in groups:
            selected_sq = delta_sq[local_indices]
            species_sq_sum[z] = species_sq_sum.get(z, 0.0) + float(np.sum(selected_sq))
            species_component_count[z] = species_component_count.get(z, 0) + int(selected_sq.size)
            species_atom_count[z] = species_atom_count.get(z, 0) + int(local_indices.size)
        if frame_data.stresses_ev_per_angstrom3 is not None and prediction.stress_ev_per_angstrom3 is not None:
            reference_stress = np.asarray(frame_data.stresses_ev_per_angstrom3[local_index], dtype=np.float64)
            predicted_stress = np.asarray(prediction.stress_ev_per_angstrom3, dtype=np.float64)
            if reference_stress.shape != predicted_stress.shape:
                raise TrainingDataInputError("Foundation-audit prediction/reference stress shape mismatch.")
            delta_stress = predicted_stress - reference_stress
            stress_sq_sum += float(np.sum(delta_stress * delta_stress))
            stress_component_count += int(delta_stress.size)
            stress_configuration_count += 1

    if total_atoms != total_atoms_expected or vector_cursor != total_atoms_expected or component_cursor != total_atoms_expected * 3:
        raise RuntimeError("FOUNDATION-AUDIT1 exact temporary allocation was not filled completely.")
    species_metrics = tuple(
        TargetModelSpeciesForceMetric(
            atomic_number=atomic_number,
            symbol=chemical_symbols[atomic_number],
            atom_count=species_atom_count[atomic_number],
            component_rmse_ev_per_angstrom=float(
                math.sqrt(species_sq_sum[atomic_number] / species_component_count[atomic_number])
            ),
        )
        for atomic_number in sorted(species_sq_sum)
    )
    tail_quantiles = np.asarray(policy.force_tail_quantiles, dtype=np.float64)
    vector_tail_values = np.quantile(vector, tail_quantiles)
    component_tail_values = np.quantile(component_abs, tail_quantiles)
    tails = tuple(
        TargetModelForceTailMetric(
            quantile=q,
            vector_error_ev_per_angstrom=float(vector_tail_values[index]),
            component_abs_error_ev_per_angstrom=float(component_tail_values[index]),
        )
        for index, q in enumerate(policy.force_tail_quantiles)
    )
    conditioned = _conditioned_summaries(
        frame_uids=frame_uids,
        frame_force_component_mse=np.asarray(frame_mse, dtype=np.float64),
        structural_catalogs=structural_catalogs,
        policy=policy,
    )
    species_macro = float(np.mean([item.component_rmse_ev_per_angstrom for item in species_metrics]))
    result = TargetModelAuditMetrics(
        configuration_count=len(tuple(frame_uids)),
        atom_count=total_atoms,
        stress_configuration_count=stress_configuration_count,
        energy_mae_ev_per_atom=float(np.mean(np.asarray(energy_abs_per_atom, dtype=np.float64))),
        force_component_rmse_ev_per_angstrom=float(math.sqrt(force_sq_sum / force_component_count)),
        stress_component_rmse_ev_per_angstrom3=(
            None if stress_component_count == 0 else float(math.sqrt(stress_sq_sum / stress_component_count))
        ),
        species_macro_force_rmse_ev_per_angstrom=species_macro,
        species_force_metrics=species_metrics,
        force_tail_metrics=tails,
        conditioned_force_summaries=conditioned,
    )
    if isinstance(vector, np.memmap):
        vector.flush()
    if isinstance(component_abs, np.memmap):
        component_abs.flush()
    # Drop memmap references before deleting their temporary directory.
    del vector, component_abs
    if temporary is not None:
        temporary.cleanup()
    return result


def build_foundation_target_audit(
    source_catalog: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data5_bundle: Any,
    data6_bundle: Any,
    target_data_role_freeze: Any,
    model_sweep_artifacts: Any,
    *,
    policy: TargetModelAuditPolicy | None = None,
    probe_contracts: Sequence[FoundationAuditProbeContract] | None = None,
    foundation_potential_identity: FoundationPotentialIdentity | None = None,
    foundation_inference_identity: FoundationInferenceIdentity | None = None,
    temporary_memory_threshold_bytes: int | None = None,
    temporary_directory: str | None = None,
) -> FoundationTargetAudit:
    """Build the immutable FOUNDATION-AUDIT1 record from completed DATA6 evidence."""

    active = TargetModelAuditPolicy() if policy is None else policy
    if source_catalog.content_digest != data6_bundle.source_catalog_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 source/DATA6 lineage mismatch.")
    if frame_catalog.content_digest != data6_bundle.frame_catalog_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 frame/DATA6 lineage mismatch.")
    if data5_bundle.content_digest != data6_bundle.data5_bundle_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 DATA5/DATA6 lineage mismatch.")
    if target_data_role_freeze.source_catalog_digest != source_catalog.content_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 TARGET-DATA2A/source lineage mismatch.")
    if target_data_role_freeze.frame_catalog_digest != frame_catalog.content_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 TARGET-DATA2A/frame lineage mismatch.")
    if target_data_role_freeze.data5_bundle_digest != data5_bundle.content_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 TARGET-DATA2A/DATA5 lineage mismatch.")
    if data6_bundle.checkpoint_identity is None or data6_bundle.prediction_manifest is None:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 requires completed DATA6 foundation predictions.")
    if data6_bundle.model_sweep_checkpoint_digest is None:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 requires DATA6 model-sweep checkpoint identity.")
    if not model_sweep_artifacts.complete or model_sweep_artifacts.prediction_manifest is None:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 requires a complete production model sweep.")
    if model_sweep_artifacts.checkpoint.content_digest != data6_bundle.model_sweep_checkpoint_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 model-sweep/DATA6 checkpoint mismatch.")
    if model_sweep_artifacts.prediction_manifest.content_digest != data6_bundle.prediction_manifest.content_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 prediction-manifest lineage mismatch.")

    difficulty_by_label: dict[str, Any] = {}
    for catalog in data6_bundle.training_difficulty_catalogs:
        if catalog.domain.kind is TrainingDifficultyDomainKind.FINAL_DEVELOPMENT:
            if catalog.domain.label_domain_id in difficulty_by_label:
                raise TrainingDataInputError("FOUNDATION-AUDIT1 found duplicate final-development difficulty domains.")
            difficulty_by_label[catalog.domain.label_domain_id] = catalog

    structural_catalogs = tuple(data6_bundle.universal_structural_features)
    # AUDIT-EVAL-PERF1 static execution metadata.  Building these once avoids
    # re-indexing DATA3 and re-discovering identical per-run species membership
    # for every audit domain/frame; neither cache participates in authority.
    shared_frame_array_index = build_frame_array_index(frame_catalog, frame_data_by_run)
    species_groups_by_frame_data: dict[int, tuple[tuple[int, np.ndarray], ...]] = {}
    for frame_data in frame_data_by_run.values():
        numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
        groups: list[tuple[int, np.ndarray]] = []
        for atomic_number in np.unique(numbers):
            local = np.flatnonzero(numbers == atomic_number).astype(np.int32, copy=False)
            local.setflags(write=False)
            groups.append((int(atomic_number), local))
        species_groups_by_frame_data[id(frame_data)] = tuple(groups)

    domain_records: list[FoundationAuditDomainRecord] = []
    for frozen in target_data_role_freeze.domains:
        difficulty = difficulty_by_label.get(frozen.label_domain_id)
        if difficulty is None:
            raise TrainingDataInputError(
                f"FOUNDATION-AUDIT1 lacks DATA6 final-development residuals for {frozen.label_domain_id!r}."
            )
        authorized = tuple(frozen.size_development_frame_uids)
        if tuple(difficulty.domain.frame_uids) != tuple(sorted(authorized)):
            if set(difficulty.domain.frame_uids) != set(authorized):
                raise TrainingDataInputError(
                    "FOUNDATION-AUDIT1 DATA6 residual domain is not exactly the TARGET-DATA2A development domain."
                )
        authorized = tuple(sorted(authorized))
        frame_domain_digest = digest(
            {
                "schema": "mdstats.foundation-audit-frame-domain.v1",
                "label_domain_id": frozen.label_domain_id,
                "frame_uids": list(authorized),
            }
        )
        metrics = _metrics_for_domain(
            frame_uids=authorized,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            prediction_manifest=model_sweep_artifacts.prediction_manifest,
            prediction_root=str(model_sweep_artifacts.root_directory),
            structural_catalogs=structural_catalogs,
            policy=active,
            temporary_memory_threshold_bytes=temporary_memory_threshold_bytes,
            temporary_directory=temporary_directory,
            frame_array_index=shared_frame_array_index,
            species_groups_by_frame_data=species_groups_by_frame_data,
        )
        domain_records.append(
            FoundationAuditDomainRecord(
                label_domain_id=frozen.label_domain_id,
                frame_uids=authorized,
                frame_domain_digest=frame_domain_digest,
                training_difficulty_catalog_digest=difficulty.content_digest,
                metrics=metrics,
            )
        )

    default_probes = (
        FoundationAuditProbeContract(
            probe_id="finite_displacement_restoring_force",
            status="deferred_protocol",
            notes=(
                "Static FOUNDATION-AUDIT1 identity is frozen now; exact PES-VERIFY1 displacement grid/protocol remains gate-local and must materialize a matched foundation result before candidate comparison.",
            ),
        ),
        FoundationAuditProbeContract(
            probe_id="zero_k_relaxation_geometry_topology",
            status="deferred_protocol",
            notes=(
                "Static FOUNDATION-AUDIT1 identity is frozen now; exact RELAX-VERIFY1 protocol/tolerances remain gate-local and must materialize a matched foundation result before candidate comparison.",
            ),
        ),
    )
    probes = default_probes if probe_contracts is None else tuple(probe_contracts)
    checkpoint = data6_bundle.checkpoint_identity
    if foundation_potential_identity is not None:
        if not getattr(checkpoint, "foundation_bound", False):
            raise TrainingDataInputError("Canonical foundation audit requires head-qualified DATA6 checkpoint identity.")
        if checkpoint.foundation_potential_digest != foundation_potential_identity.canonical_content_digest:
            raise TrainingDataInputError("Foundation audit potential identity disagrees with DATA6.")
        if foundation_inference_identity is None or checkpoint.foundation_inference_digest != foundation_inference_identity.content_digest:
            raise TrainingDataInputError("Foundation audit inference identity disagrees with DATA6.")
    return FoundationTargetAudit(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data5_bundle_digest=data5_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        foundation_checkpoint_identity_digest=checkpoint.content_digest,
        foundation_checkpoint_sha256=checkpoint.checkpoint_sha256,
        model_sweep_checkpoint_digest=data6_bundle.model_sweep_checkpoint_digest,
        structural_provider_digests=tuple(
            catalog.provider_identity.content_digest for catalog in structural_catalogs
        ),
        policy=active,
        domains=tuple(domain_records),
        probe_contracts=tuple(probes),
        foundation_potential_identity=foundation_potential_identity,
        foundation_inference_identity=foundation_inference_identity,
    )


def validate_foundation_target_audit_authority(
    audit: FoundationTargetAudit,
    *,
    source_catalog: Any,
    frame_catalog: Any,
    data5_bundle: Any,
    data6_bundle: Any,
    target_data_role_freeze: Any,
) -> None:
    """Fail closed when a frozen audit no longer matches live campaign authority."""

    expected = {
        "source_catalog_digest": source_catalog.content_digest,
        "frame_catalog_digest": frame_catalog.content_digest,
        "data5_bundle_digest": data5_bundle.content_digest,
        "data6_bundle_digest": data6_bundle.content_digest,
        "target_data_role_freeze_digest": target_data_role_freeze.content_digest,
    }
    for name, value in expected.items():
        if getattr(audit, name) != value:
            raise TrainingDataInputError(f"FOUNDATION-AUDIT1 authority mismatch: {name} changed.")
    if data6_bundle.checkpoint_identity is None:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 live DATA6 foundation identity is missing.")
    if audit.foundation_checkpoint_identity_digest != data6_bundle.checkpoint_identity.content_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 foundation checkpoint identity changed.")
    if audit.foundation_checkpoint_sha256 != data6_bundle.checkpoint_identity.checkpoint_sha256:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 foundation checkpoint bytes changed.")
    if audit.foundation_potential_identity is not None:
        checkpoint = data6_bundle.checkpoint_identity
        if checkpoint.foundation_potential_digest != audit.foundation_potential_identity.canonical_content_digest:
            raise TrainingDataInputError("FOUNDATION-AUDIT1 canonical foundation potential changed.")
        if checkpoint.foundation_inference_digest != audit.foundation_inference_identity.content_digest:
            raise TrainingDataInputError("FOUNDATION-AUDIT1 canonical foundation inference identity changed.")
    if audit.model_sweep_checkpoint_digest != data6_bundle.model_sweep_checkpoint_digest:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 model-sweep checkpoint changed.")
    live_labels = {item.label_domain_id: tuple(sorted(item.size_development_frame_uids)) for item in target_data_role_freeze.domains}
    audit_labels = {item.label_domain_id: tuple(item.frame_uids) for item in audit.domains}
    if audit_labels != live_labels:
        raise TrainingDataInputError("FOUNDATION-AUDIT1 frozen target development domains changed.")
