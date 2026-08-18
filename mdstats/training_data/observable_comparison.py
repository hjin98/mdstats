"""Profile-aware comparison and acceptance of analysis-owned observables.

This module belongs to the MLFF orchestration layer.  It consumes native result
objects produced by :mod:`mdstats.analysis`, but it does not reimplement RDF,
coordination, dynamics, spectra, transport, or thermomechanical algorithms.
The policy declares which result fields are compared, how their discrepancy is
scored, and which predeclared thresholds govern checkpoint decisions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from types import MappingProxyType
from typing import Any, Mapping, Sequence

import numpy as np

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    json_value,
    validate_digest,
)
from .observable_validation import (
    MLFFObservableValidationEvidence,
    ObservableEvidenceRole,
    ObservableRecommendationProfile,
)

OBSERVABLE_COMPARISON_THRESHOLDS_SCHEMA = "mdstats.observable-comparison-thresholds.v1"
OBSERVABLE_SCORE_UNCERTAINTY_SCHEMA = "mdstats.observable-score-uncertainty.v1"
OBSERVABLE_COMPARISON_RULE_SCHEMA = "mdstats.observable-comparison-rule.v1"
OBSERVABLE_COMPARISON_POLICY_SCHEMA = "mdstats.observable-comparison-policy.v1"
OBSERVABLE_RULE_COMPARISON_RESULT_SCHEMA = "mdstats.observable-rule-comparison-result.v1"
OBSERVABLE_COMPARISON_RESULT_SCHEMA = "mdstats.observable-comparison-result.v1"
OBSERVABLE_ACCEPTANCE_DECISION_SCHEMA = "mdstats.observable-acceptance-decision.v1"
OBSERVABLE_COMPARISON_VERSION = "mdstats.mlff.observable-comparison.2026-07.v1"
MLFF_DATA9A8_PARSER_VERSION = "0.20.52a0"


class ObservableComparisonMetric(str, Enum):
    """Supported lower-is-better discrepancy metrics."""

    ABSOLUTE_ERROR = "absolute_error"
    SYMMETRIC_RELATIVE_ERROR = "symmetric_relative_error"
    NORMALIZED_RMSE = "normalized_rmse"
    INTEGRATED_ABSOLUTE_ERROR = "integrated_absolute_error"
    JENSEN_SHANNON_DISTANCE = "jensen_shannon_distance"
    PEAK_SHIFT = "peak_shift"
    EXACT_MISMATCH = "exact_mismatch"


class ObservableValueReducer(str, Enum):
    IDENTITY = "identity"
    FIRST = "first"
    LAST = "last"
    MEAN = "mean"
    MAXIMUM = "maximum"
    MINIMUM = "minimum"


class ObservableComparisonOutcome(str, Enum):
    PASS = "pass"
    DEGRADED = "degraded"
    FAIL = "fail"
    INDETERMINATE = "indeterminate"


_OUTCOME_ORDER = {
    ObservableComparisonOutcome.PASS: 0,
    ObservableComparisonOutcome.DEGRADED: 1,
    ObservableComparisonOutcome.FAIL: 2,
    ObservableComparisonOutcome.INDETERMINATE: 3,
}


@dataclass(frozen=True, slots=True)
class ObservableComparisonThresholds:
    """Two-level lower-is-better threshold policy.

    Scores at or below ``quality_max`` pass. Scores above the quality level but
    at or below ``acceptance_max`` are degraded. Larger scores fail.
    """

    quality_max: float
    acceptance_max: float

    def __post_init__(self) -> None:
        quality = float(self.quality_max)
        acceptance = float(self.acceptance_max)
        if not np.isfinite(quality) or not np.isfinite(acceptance):
            raise TrainingDataInputError("Observable thresholds must be finite.")
        if quality < 0.0 or acceptance < quality:
            raise TrainingDataInputError(
                "Observable thresholds require 0 <= quality_max <= acceptance_max."
            )
        object.__setattr__(self, "quality_max", quality)
        object.__setattr__(self, "acceptance_max", acceptance)

    def outcome(self, score: float) -> ObservableComparisonOutcome:
        if not np.isfinite(score):
            return ObservableComparisonOutcome.INDETERMINATE
        if score <= self.quality_max:
            return ObservableComparisonOutcome.PASS
        if score <= self.acceptance_max:
            return ObservableComparisonOutcome.DEGRADED
        return ObservableComparisonOutcome.FAIL

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_COMPARISON_THRESHOLDS_SCHEMA,
            "quality_max": self.quality_max,
            "acceptance_max": self.acceptance_max,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableComparisonThresholds":
        if payload.get("schema") != OBSERVABLE_COMPARISON_THRESHOLDS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported observable threshold schema.")
        result = cls(float(payload["quality_max"]), float(payload["acceptance_max"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable threshold digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableScoreUncertainty:
    """Predeclared standard uncertainty on the *comparison score*.

    Analysis modules remain responsible for scientific uncertainty estimation.
    This record only consumes already justified score-space uncertainties and
    subtracts ``coverage_multiplier * combined_standard_uncertainty`` before
    applying thresholds. It must not be used to manufacture uncertainty from a
    single correlated trajectory.
    """

    reference_standard_uncertainty: float = 0.0
    candidate_standard_uncertainty: float = 0.0
    coverage_multiplier: float = 0.0
    provenance: str = "none"

    def __post_init__(self) -> None:
        for name in (
            "reference_standard_uncertainty",
            "candidate_standard_uncertainty",
            "coverage_multiplier",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if not self.provenance.strip():
            raise TrainingDataInputError("Score-uncertainty provenance must be non-empty.")
        if self.coverage_multiplier > 0.0 and self.provenance == "none":
            raise TrainingDataInputError(
                "Nonzero uncertainty coverage requires explicit uncertainty provenance."
            )

    @property
    def allowance(self) -> float:
        combined = np.hypot(
            self.reference_standard_uncertainty,
            self.candidate_standard_uncertainty,
        )
        return float(self.coverage_multiplier * combined)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_SCORE_UNCERTAINTY_SCHEMA,
            "reference_standard_uncertainty": self.reference_standard_uncertainty,
            "candidate_standard_uncertainty": self.candidate_standard_uncertainty,
            "coverage_multiplier": self.coverage_multiplier,
            "provenance": self.provenance,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableScoreUncertainty":
        if payload.get("schema") != OBSERVABLE_SCORE_UNCERTAINTY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported score-uncertainty schema.")
        result = cls(
            reference_standard_uncertainty=float(payload.get("reference_standard_uncertainty", 0.0)),
            candidate_standard_uncertainty=float(payload.get("candidate_standard_uncertainty", 0.0)),
            coverage_multiplier=float(payload.get("coverage_multiplier", 0.0)),
            provenance=str(payload.get("provenance", "none")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Score-uncertainty digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableComparisonRule:
    """One predeclared comparison of a native analysis-result field."""

    rule_id: str
    call_id: str
    observable_id: str
    metric: ObservableComparisonMetric
    value_path: str
    thresholds: ObservableComparisonThresholds
    axis_path: str | None = None
    reducer: ObservableValueReducer = ObservableValueReducer.IDENTITY
    allow_interpolation: bool = False
    normalization_floor: float = 1.0e-12
    required: bool = True
    weight: float = 1.0
    atom_group_id: str | None = None
    condition_id: str | None = None
    uncertainty: ObservableScoreUncertainty = ObservableScoreUncertainty()
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("rule_id", "call_id", "observable_id", "value_path"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} must be non-empty.")
        object.__setattr__(self, "metric", ObservableComparisonMetric(self.metric))
        object.__setattr__(self, "reducer", ObservableValueReducer(self.reducer))
        floor = float(self.normalization_floor)
        weight = float(self.weight)
        if not np.isfinite(floor) or floor <= 0.0:
            raise TrainingDataInputError("normalization_floor must be positive and finite.")
        if not np.isfinite(weight) or weight <= 0.0:
            raise TrainingDataInputError("Comparison-rule weight must be positive and finite.")
        object.__setattr__(self, "normalization_floor", floor)
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        if self.metric in {
            ObservableComparisonMetric.INTEGRATED_ABSOLUTE_ERROR,
            ObservableComparisonMetric.PEAK_SHIFT,
        } and self.axis_path is None:
            raise TrainingDataInputError(f"Metric {self.metric.value!r} requires axis_path.")
        if self.reducer is not ObservableValueReducer.IDENTITY and self.metric in {
            ObservableComparisonMetric.INTEGRATED_ABSOLUTE_ERROR,
            ObservableComparisonMetric.JENSEN_SHANNON_DISTANCE,
            ObservableComparisonMetric.PEAK_SHIFT,
            ObservableComparisonMetric.NORMALIZED_RMSE,
        }:
            raise TrainingDataInputError(
                "Array comparison metrics require reducer='identity'."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_COMPARISON_RULE_SCHEMA,
            "rule_id": self.rule_id,
            "call_id": self.call_id,
            "observable_id": self.observable_id,
            "metric": self.metric.value,
            "value_path": self.value_path,
            "axis_path": self.axis_path,
            "reducer": self.reducer.value,
            "allow_interpolation": self.allow_interpolation,
            "normalization_floor": self.normalization_floor,
            "required": self.required,
            "weight": self.weight,
            "atom_group_id": self.atom_group_id,
            "condition_id": self.condition_id,
            "thresholds": self.thresholds.to_dict(),
            "uncertainty": self.uncertainty.to_dict(),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableComparisonRule":
        if payload.get("schema") != OBSERVABLE_COMPARISON_RULE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported observable comparison-rule schema.")
        result = cls(
            rule_id=str(payload["rule_id"]),
            call_id=str(payload["call_id"]),
            observable_id=str(payload["observable_id"]),
            metric=ObservableComparisonMetric(str(payload["metric"])),
            value_path=str(payload["value_path"]),
            axis_path=None if payload.get("axis_path") is None else str(payload["axis_path"]),
            reducer=ObservableValueReducer(str(payload.get("reducer", "identity"))),
            allow_interpolation=bool(payload.get("allow_interpolation", False)),
            normalization_floor=float(payload.get("normalization_floor", 1.0e-12)),
            required=bool(payload.get("required", True)),
            weight=float(payload.get("weight", 1.0)),
            atom_group_id=None if payload.get("atom_group_id") is None else str(payload["atom_group_id"]),
            condition_id=None if payload.get("condition_id") is None else str(payload["condition_id"]),
            thresholds=ObservableComparisonThresholds.from_dict(payload["thresholds"]),
            uncertainty=ObservableScoreUncertainty.from_dict(payload.get("uncertainty", {
                "schema": OBSERVABLE_SCORE_UNCERTAINTY_SCHEMA,
                "reference_standard_uncertainty": 0.0,
                "candidate_standard_uncertainty": 0.0,
                "coverage_multiplier": 0.0,
                "provenance": "none",
            })),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable comparison-rule digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableComparisonPolicy:
    """Frozen profile-aware comparison and acceptance policy."""

    policy_id: str
    recipe_digest: str
    recommendation_profile: ObservableRecommendationProfile
    rules: tuple[ObservableComparisonRule, ...]
    material_profile_digest: str | None = None
    allowed_roles: tuple[ObservableEvidenceRole, ...] = (
        ObservableEvidenceRole.CHECKPOINT_MONITOR,
        ObservableEvidenceRole.OUTER_VALIDATION,
        ObservableEvidenceRole.CALIBRATION,
        ObservableEvidenceRole.LOCKED_TEST,
        ObservableEvidenceRole.EXTERNAL_BENCHMARK,
    )
    require_matching_capabilities: bool = True
    require_matching_result_types: bool = True
    accept_degraded: bool = True
    required_indeterminate_is_failure: bool = True
    notes: tuple[str, ...] = ()
    policy_version: str = OBSERVABLE_COMPARISON_VERSION

    def __post_init__(self) -> None:
        if not self.policy_id.strip() or not self.policy_version.strip():
            raise TrainingDataInputError("Comparison policy identifiers must be non-empty.")
        object.__setattr__(self, "recipe_digest", validate_digest(self.recipe_digest, name="recipe_digest"))
        if self.material_profile_digest is not None:
            object.__setattr__(
                self,
                "material_profile_digest",
                validate_digest(self.material_profile_digest, name="material_profile_digest"),
            )
        object.__setattr__(self, "recommendation_profile", ObservableRecommendationProfile(self.recommendation_profile))
        rules = tuple(sorted(self.rules, key=lambda item: item.rule_id))
        if not rules or not any(rule.required for rule in rules):
            raise TrainingDataInputError("A comparison policy requires at least one required rule.")
        if len({rule.rule_id for rule in rules}) != len(rules):
            raise TrainingDataInputError("Comparison rule IDs must be unique.")
        object.__setattr__(self, "rules", rules)
        roles = tuple(sorted({ObservableEvidenceRole(v) for v in self.allowed_roles}, key=lambda v: v.value))
        if not roles:
            raise TrainingDataInputError("Comparison policy must allow at least one evidence role.")
        object.__setattr__(self, "allowed_roles", roles)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_COMPARISON_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "policy_id": self.policy_id,
            "recipe_digest": self.recipe_digest,
            "recommendation_profile": self.recommendation_profile.value,
            "material_profile_digest": self.material_profile_digest,
            "rules": [rule.to_dict() for rule in self.rules],
            "allowed_roles": [role.value for role in self.allowed_roles],
            "require_matching_capabilities": self.require_matching_capabilities,
            "require_matching_result_types": self.require_matching_result_types,
            "accept_degraded": self.accept_degraded,
            "required_indeterminate_is_failure": self.required_indeterminate_is_failure,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableComparisonPolicy":
        if payload.get("schema") != OBSERVABLE_COMPARISON_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported observable comparison-policy schema.")
        result = cls(
            policy_id=str(payload["policy_id"]),
            recipe_digest=str(payload["recipe_digest"]),
            recommendation_profile=ObservableRecommendationProfile(str(payload["recommendation_profile"])),
            material_profile_digest=None if payload.get("material_profile_digest") is None else str(payload["material_profile_digest"]),
            rules=tuple(ObservableComparisonRule.from_dict(item) for item in payload["rules"]),
            allowed_roles=tuple(ObservableEvidenceRole(str(v)) for v in payload["allowed_roles"]),
            require_matching_capabilities=bool(payload.get("require_matching_capabilities", True)),
            require_matching_result_types=bool(payload.get("require_matching_result_types", True)),
            accept_degraded=bool(payload.get("accept_degraded", True)),
            required_indeterminate_is_failure=bool(payload.get("required_indeterminate_is_failure", True)),
            notes=tuple(str(v) for v in payload.get("notes", ())),
            policy_version=str(payload.get("policy_version", OBSERVABLE_COMPARISON_VERSION)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable comparison-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableRuleComparisonResult:
    rule_id: str
    call_id: str
    observable_id: str
    metric: ObservableComparisonMetric
    reference_result_digest: str
    candidate_result_digest: str
    raw_score: float | None
    adjusted_score: float | None
    uncertainty_allowance: float
    outcome: ObservableComparisonOutcome
    required: bool
    weight: float
    reference_summary: Mapping[str, Any]
    candidate_summary: Mapping[str, Any]
    atom_group_id: str | None = None
    condition_id: str | None = None
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "metric", ObservableComparisonMetric(self.metric))
        object.__setattr__(self, "outcome", ObservableComparisonOutcome(self.outcome))
        for name in ("reference_result_digest", "candidate_result_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("raw_score", "adjusted_score"):
            value = getattr(self, name)
            if value is not None and (not np.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"{name} must be nonnegative finite or None.")
        allowance = float(self.uncertainty_allowance)
        if not np.isfinite(allowance) or allowance < 0.0:
            raise TrainingDataInputError("uncertainty_allowance must be finite and nonnegative.")
        object.__setattr__(self, "uncertainty_allowance", allowance)
        object.__setattr__(self, "weight", float(self.weight))
        object.__setattr__(self, "reference_summary", MappingProxyType(dict(json_value(self.reference_summary))))
        object.__setattr__(self, "candidate_summary", MappingProxyType(dict(json_value(self.candidate_summary))))
        object.__setattr__(self, "diagnostics", tuple(str(v) for v in self.diagnostics))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_RULE_COMPARISON_RESULT_SCHEMA,
            "rule_id": self.rule_id,
            "call_id": self.call_id,
            "observable_id": self.observable_id,
            "metric": self.metric.value,
            "reference_result_digest": self.reference_result_digest,
            "candidate_result_digest": self.candidate_result_digest,
            "raw_score": self.raw_score,
            "adjusted_score": self.adjusted_score,
            "uncertainty_allowance": self.uncertainty_allowance,
            "outcome": self.outcome.value,
            "required": self.required,
            "weight": self.weight,
            "reference_summary": dict(self.reference_summary),
            "candidate_summary": dict(self.candidate_summary),
            "atom_group_id": self.atom_group_id,
            "condition_id": self.condition_id,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableRuleComparisonResult":
        if payload.get("schema") != OBSERVABLE_RULE_COMPARISON_RESULT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported rule-comparison result schema.")
        result = cls(
            rule_id=str(payload["rule_id"]), call_id=str(payload["call_id"]),
            observable_id=str(payload["observable_id"]),
            metric=ObservableComparisonMetric(str(payload["metric"])),
            reference_result_digest=str(payload["reference_result_digest"]),
            candidate_result_digest=str(payload["candidate_result_digest"]),
            raw_score=None if payload.get("raw_score") is None else float(payload["raw_score"]),
            adjusted_score=None if payload.get("adjusted_score") is None else float(payload["adjusted_score"]),
            uncertainty_allowance=float(payload["uncertainty_allowance"]),
            outcome=ObservableComparisonOutcome(str(payload["outcome"])),
            required=bool(payload["required"]), weight=float(payload["weight"]),
            reference_summary=dict(payload["reference_summary"]),
            candidate_summary=dict(payload["candidate_summary"]),
            atom_group_id=None if payload.get("atom_group_id") is None else str(payload["atom_group_id"]),
            condition_id=None if payload.get("condition_id") is None else str(payload["condition_id"]),
            diagnostics=tuple(str(v) for v in payload.get("diagnostics", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Rule-comparison result digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableComparisonResult:
    policy_digest: str
    evidence_digest: str
    evidence_role: ObservableEvidenceRole
    rule_results: tuple[ObservableRuleComparisonResult, ...]
    overall_outcome: ObservableComparisonOutcome
    weighted_mean_adjusted_score: float | None
    scope_outcomes: Mapping[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(self, "evidence_digest", validate_digest(self.evidence_digest, name="evidence_digest"))
        object.__setattr__(self, "evidence_role", ObservableEvidenceRole(self.evidence_role))
        object.__setattr__(self, "overall_outcome", ObservableComparisonOutcome(self.overall_outcome))
        results = tuple(sorted(self.rule_results, key=lambda item: item.rule_id))
        if not results or len({item.rule_id for item in results}) != len(results):
            raise TrainingDataInputError("Comparison result requires unique rule results.")
        object.__setattr__(self, "rule_results", results)
        if self.weighted_mean_adjusted_score is not None:
            value = float(self.weighted_mean_adjusted_score)
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError("Weighted comparison score must be finite and nonnegative.")
            object.__setattr__(self, "weighted_mean_adjusted_score", value)
        object.__setattr__(self, "scope_outcomes", MappingProxyType(dict(sorted((str(k), str(v)) for k, v in self.scope_outcomes.items()))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_COMPARISON_RESULT_SCHEMA,
            "policy_digest": self.policy_digest,
            "evidence_digest": self.evidence_digest,
            "evidence_role": self.evidence_role.value,
            "rule_results": [item.to_dict() for item in self.rule_results],
            "overall_outcome": self.overall_outcome.value,
            "weighted_mean_adjusted_score": self.weighted_mean_adjusted_score,
            "scope_outcomes": dict(self.scope_outcomes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableComparisonResult":
        if payload.get("schema") != OBSERVABLE_COMPARISON_RESULT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported observable-comparison result schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]), evidence_digest=str(payload["evidence_digest"]),
            evidence_role=ObservableEvidenceRole(str(payload["evidence_role"])),
            rule_results=tuple(ObservableRuleComparisonResult.from_dict(item) for item in payload["rule_results"]),
            overall_outcome=ObservableComparisonOutcome(str(payload["overall_outcome"])),
            weighted_mean_adjusted_score=None if payload.get("weighted_mean_adjusted_score") is None else float(payload["weighted_mean_adjusted_score"]),
            scope_outcomes=dict(payload.get("scope_outcomes", {})),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable-comparison result digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ObservableAcceptanceDecision:
    policy_digest: str
    comparison_result_digest: str
    evidence_role: ObservableEvidenceRole
    outcome: ObservableComparisonOutcome
    accepted: bool
    blocking_rule_ids: tuple[str, ...]
    degraded_rule_ids: tuple[str, ...]
    advisory_failure_rule_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(self, "comparison_result_digest", validate_digest(self.comparison_result_digest, name="comparison_result_digest"))
        object.__setattr__(self, "evidence_role", ObservableEvidenceRole(self.evidence_role))
        object.__setattr__(self, "outcome", ObservableComparisonOutcome(self.outcome))
        for name in ("blocking_rule_ids", "degraded_rule_ids", "advisory_failure_rule_ids", "reasons"):
            object.__setattr__(self, name, tuple(sorted(set(str(v) for v in getattr(self, name)))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": OBSERVABLE_ACCEPTANCE_DECISION_SCHEMA,
            "policy_digest": self.policy_digest,
            "comparison_result_digest": self.comparison_result_digest,
            "evidence_role": self.evidence_role.value,
            "outcome": self.outcome.value,
            "accepted": self.accepted,
            "blocking_rule_ids": list(self.blocking_rule_ids),
            "degraded_rule_ids": list(self.degraded_rule_ids),
            "advisory_failure_rule_ids": list(self.advisory_failure_rule_ids),
            "reasons": list(self.reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ObservableAcceptanceDecision":
        if payload.get("schema") != OBSERVABLE_ACCEPTANCE_DECISION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported observable-acceptance decision schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            comparison_result_digest=str(payload["comparison_result_digest"]),
            evidence_role=ObservableEvidenceRole(str(payload["evidence_role"])),
            outcome=ObservableComparisonOutcome(str(payload["outcome"])),
            accepted=bool(payload["accepted"]),
            blocking_rule_ids=tuple(str(v) for v in payload.get("blocking_rule_ids", ())),
            degraded_rule_ids=tuple(str(v) for v in payload.get("degraded_rule_ids", ())),
            advisory_failure_rule_ids=tuple(str(v) for v in payload.get("advisory_failure_rule_ids", ())),
            reasons=tuple(str(v) for v in payload.get("reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Observable-acceptance decision digest mismatch.")
        return result


def _resolve_path(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        if not token:
            raise TrainingDataInputError(f"Invalid empty path component in {path!r}.")
        if isinstance(current, Mapping):
            if token not in current:
                raise TrainingDataInputError(f"Result path {path!r} is missing mapping key {token!r}.")
            current = current[token]
        else:
            if not hasattr(current, token):
                raise TrainingDataInputError(
                    f"Result path {path!r} is missing attribute {token!r} on {type(current).__name__}."
                )
            current = getattr(current, token)
    return current


def _reduce_value(value: Any, reducer: ObservableValueReducer) -> Any:
    if reducer is ObservableValueReducer.IDENTITY:
        return value
    array = np.asarray(value)
    if array.size == 0:
        raise TrainingDataInputError("Cannot reduce an empty observable result field.")
    if reducer is ObservableValueReducer.FIRST:
        return array.reshape(-1)[0]
    if reducer is ObservableValueReducer.LAST:
        return array.reshape(-1)[-1]
    numeric = np.asarray(array, dtype=float)
    if reducer is ObservableValueReducer.MEAN:
        return float(np.mean(numeric))
    if reducer is ObservableValueReducer.MAXIMUM:
        return float(np.max(numeric))
    if reducer is ObservableValueReducer.MINIMUM:
        return float(np.min(numeric))
    raise AssertionError(reducer)


def _as_finite_array(value: Any, *, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.size == 0 or not np.all(np.isfinite(result)):
        raise TrainingDataInputError(f"{name} must be nonempty and finite.")
    return result


def _value_summary(value: Any) -> dict[str, Any]:
    if isinstance(value, (str, bool, int, float, np.generic)):
        scalar = value.item() if isinstance(value, np.generic) else value
        return {"kind": "scalar", "value": json_value(scalar)}
    array = np.asarray(value)
    if array.dtype.kind == "O":
        return {"kind": "object", "type": f"{type(value).__module__}.{type(value).__qualname__}"}
    contiguous = np.ascontiguousarray(array)
    header = f"{contiguous.dtype.str}|{contiguous.shape}".encode("ascii")
    hasher = hashlib.sha256()
    hasher.update(header)
    hasher.update(memoryview(contiguous).cast("B"))
    payload: dict[str, Any] = {
        "kind": "array",
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "content_digest": hasher.hexdigest(),
    }
    if array.size and array.dtype.kind in "iuf":
        numeric = np.asarray(array, dtype=float)
        finite = numeric[np.isfinite(numeric)]
        payload["finite_fraction"] = float(finite.size / numeric.size)
        if finite.size:
            payload.update({
                "minimum": float(np.min(finite)),
                "maximum": float(np.max(finite)),
                "mean": float(np.mean(finite)),
            })
    return payload


def _align_continuous_curves(
    reference_axis: np.ndarray,
    reference_values: np.ndarray,
    candidate_axis: np.ndarray,
    candidate_values: np.ndarray,
    *,
    allow_interpolation: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    for name, axis, values in (
        ("reference", reference_axis, reference_values),
        ("candidate", candidate_axis, candidate_values),
    ):
        if axis.ndim != 1 or values.ndim != 1 or axis.shape != values.shape:
            raise TrainingDataInputError(f"{name} curve axis and values must be matching vectors.")
        if np.any(np.diff(axis) <= 0.0):
            raise TrainingDataInputError(f"{name} curve axis must be strictly increasing.")
    if reference_axis.shape == candidate_axis.shape and np.allclose(reference_axis, candidate_axis, rtol=1e-10, atol=1e-12):
        return reference_axis, reference_values, candidate_values
    if not allow_interpolation:
        raise TrainingDataInputError("Comparison curves use different axes and interpolation is disabled.")
    if candidate_axis[0] > reference_axis[0] or candidate_axis[-1] < reference_axis[-1]:
        raise TrainingDataInputError("Candidate curve does not cover the complete reference axis.")
    return reference_axis, reference_values, np.interp(reference_axis, candidate_axis, candidate_values)


def _align_distributions(
    reference_values: np.ndarray,
    candidate_values: np.ndarray,
    reference_axis: np.ndarray | None,
    candidate_axis: np.ndarray | None,
    *,
    allow_interpolation: bool,
) -> tuple[np.ndarray, np.ndarray]:
    if reference_axis is None and candidate_axis is None:
        if reference_values.shape != candidate_values.shape:
            raise TrainingDataInputError("Distribution vectors require matching shapes or explicit supports.")
        return reference_values, candidate_values
    if reference_axis is None or candidate_axis is None:
        raise TrainingDataInputError("Both distributions must declare supports when either support is used.")
    if reference_axis.ndim != 1 or candidate_axis.ndim != 1:
        raise TrainingDataInputError("Distribution supports must be one-dimensional.")
    if reference_axis.shape != reference_values.shape or candidate_axis.shape != candidate_values.shape:
        raise TrainingDataInputError("Distribution supports must match their value vectors.")
    if reference_axis.shape == candidate_axis.shape and np.array_equal(reference_axis, candidate_axis):
        return reference_values, candidate_values
    if allow_interpolation:
        _, ref, cand = _align_continuous_curves(
            reference_axis, reference_values, candidate_axis, candidate_values,
            allow_interpolation=True,
        )
        return ref, cand
    support = np.union1d(reference_axis, candidate_axis)
    ref = np.zeros(support.shape, dtype=float)
    cand = np.zeros(support.shape, dtype=float)
    ref[np.searchsorted(support, reference_axis)] = reference_values
    cand[np.searchsorted(support, candidate_axis)] = candidate_values
    return ref, cand


def _metric_score(
    rule: ObservableComparisonRule,
    reference_value: Any,
    candidate_value: Any,
    reference_axis: Any | None,
    candidate_axis: Any | None,
) -> float:
    metric = rule.metric
    if metric is ObservableComparisonMetric.EXACT_MISMATCH:
        try:
            equal = np.array_equal(np.asarray(reference_value), np.asarray(candidate_value), equal_nan=True)
        except TypeError:
            equal = reference_value == candidate_value
        return 0.0 if bool(equal) else 1.0

    if metric in {
        ObservableComparisonMetric.ABSOLUTE_ERROR,
        ObservableComparisonMetric.SYMMETRIC_RELATIVE_ERROR,
    }:
        reference = float(np.asarray(reference_value))
        candidate = float(np.asarray(candidate_value))
        if not np.isfinite(reference) or not np.isfinite(candidate):
            raise TrainingDataInputError("Scalar comparison values must be finite.")
        difference = abs(candidate - reference)
        if metric is ObservableComparisonMetric.ABSOLUTE_ERROR:
            return difference
        denominator = max(0.5 * (abs(reference) + abs(candidate)), rule.normalization_floor)
        return difference / denominator

    reference = np.asarray(reference_value, dtype=float)
    candidate = np.asarray(candidate_value, dtype=float)
    if reference.size == 0 or candidate.size == 0:
        raise TrainingDataInputError("Comparison vectors must be nonempty.")

    if metric is ObservableComparisonMetric.JENSEN_SHANNON_DISTANCE:
        if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(candidate)):
            raise TrainingDataInputError("Jensen-Shannon inputs must be finite.")
        if reference.ndim != 1 or candidate.ndim != 1:
            raise TrainingDataInputError("Jensen-Shannon distance requires one-dimensional distributions.")
        ref_axis = None if reference_axis is None else _as_finite_array(reference_axis, name="reference support")
        cand_axis = None if candidate_axis is None else _as_finite_array(candidate_axis, name="candidate support")
        reference, candidate = _align_distributions(
            reference, candidate, ref_axis, cand_axis,
            allow_interpolation=rule.allow_interpolation,
        )
        if np.any(reference < 0.0) or np.any(candidate < 0.0):
            raise TrainingDataInputError("Jensen-Shannon inputs must be nonnegative.")
        ref_sum, cand_sum = float(np.sum(reference)), float(np.sum(candidate))
        if ref_sum <= 0.0 or cand_sum <= 0.0:
            raise TrainingDataInputError("Jensen-Shannon inputs must each have positive mass.")
        p, q = reference / ref_sum, candidate / cand_sum
        m = 0.5 * (p + q)
        def _kl(a: np.ndarray, b: np.ndarray) -> float:
            mask = a > 0.0
            return float(np.sum(a[mask] * np.log(a[mask] / b[mask])))
        return float(np.sqrt(max(0.0, 0.5 * (_kl(p, m) + _kl(q, m)))))

    if metric in {
        ObservableComparisonMetric.INTEGRATED_ABSOLUTE_ERROR,
        ObservableComparisonMetric.PEAK_SHIFT,
    }:
        if reference.ndim != 1 or candidate.ndim != 1:
            raise TrainingDataInputError("Curve metrics require one-dimensional values.")
        if not np.all(np.isfinite(reference)) or not np.all(np.isfinite(candidate)):
            raise TrainingDataInputError("Curve values must be finite.")
        ref_axis = _as_finite_array(reference_axis, name="reference axis")
        cand_axis = _as_finite_array(candidate_axis, name="candidate axis")
        axis, reference, candidate = _align_continuous_curves(
            ref_axis, reference, cand_axis, candidate,
            allow_interpolation=rule.allow_interpolation,
        )
        if metric is ObservableComparisonMetric.PEAK_SHIFT:
            return abs(float(axis[int(np.argmax(reference))]) - float(axis[int(np.argmax(candidate))]))
        numerator = float(np.trapezoid(np.abs(candidate - reference), axis))
        denominator = max(float(np.trapezoid(np.abs(reference), axis)), rule.normalization_floor)
        return numerator / denominator

    if reference.shape != candidate.shape:
        raise TrainingDataInputError("Normalized RMSE requires matching array shapes.")
    finite = np.isfinite(reference) & np.isfinite(candidate)
    if not np.any(finite):
        raise TrainingDataInputError("Normalized RMSE has no jointly finite values.")
    reference_finite = reference[finite]
    candidate_finite = candidate[finite]
    numerator = float(np.sqrt(np.mean((candidate_finite - reference_finite) ** 2)))
    denominator = max(float(np.sqrt(np.mean(reference_finite ** 2))), rule.normalization_floor)
    return numerator / denominator


def _scope_key(rule: ObservableComparisonRule) -> str:
    condition = rule.condition_id or "all_conditions"
    group = rule.atom_group_id or "all_atoms"
    return f"condition={condition}|group={group}"


def compare_mlff_observable_validation(
    evidence: MLFFObservableValidationEvidence,
    policy: ObservableComparisonPolicy,
) -> ObservableComparisonResult:
    """Compare paired native results under one predeclared policy."""

    if policy.recipe_digest != evidence.plan.recipe.content_digest:
        raise TrainingDataInputError("Comparison policy recipe does not match validation evidence.")
    if policy.recommendation_profile is not evidence.plan.recommendation_profile:
        raise TrainingDataInputError("Comparison policy recommendation profile does not match the validation plan.")
    if policy.material_profile_digest != evidence.plan.material_profile_contracts_digest:
        raise TrainingDataInputError("Comparison policy material-profile identity does not match the validation plan.")
    role = evidence.plan.activation.role
    if role not in policy.allowed_roles:
        raise TrainingDataInputError(f"Comparison policy does not allow evidence role {role.value!r}.")
    declared_policy = evidence.plan.activation.comparison_policy_digest
    if declared_policy != policy.content_digest:
        raise TrainingDataInputError(
            "Observable evidence was not activated with this predeclared comparison-policy digest."
        )
    if policy.require_matching_capabilities and (
        dict(evidence.reference_execution.capability_digests)
        != dict(evidence.candidate_execution.capability_digests)
    ):
        raise TrainingDataInputError("Reference and candidate observable capabilities differ.")

    calls = {call.call_id: call for call in evidence.plan.recipe.calls}
    rule_results: list[ObservableRuleComparisonResult] = []
    for rule in policy.rules:
        call = calls.get(rule.call_id)
        if call is None or call.observable_id != rule.observable_id:
            raise TrainingDataInputError(
                f"Comparison rule {rule.rule_id!r} does not match the activated recipe."
            )
        if policy.require_matching_result_types:
            pair = evidence.result_type_pairs[rule.call_id]
            if pair[0] != pair[1]:
                raise TrainingDataInputError(
                    f"Comparison rule {rule.rule_id!r} requires matching native result types."
                )
        reference_result = evidence.reference_execution.results[rule.call_id]
        candidate_result = evidence.candidate_execution.results[rule.call_id]
        reference_value = _reduce_value(_resolve_path(reference_result, rule.value_path), rule.reducer)
        candidate_value = _reduce_value(_resolve_path(candidate_result, rule.value_path), rule.reducer)
        reference_axis = None if rule.axis_path is None else _resolve_path(reference_result, rule.axis_path)
        candidate_axis = None if rule.axis_path is None else _resolve_path(candidate_result, rule.axis_path)
        diagnostics: list[str] = []
        raw_score: float | None
        adjusted_score: float | None
        try:
            raw_score = _metric_score(
                rule, reference_value, candidate_value, reference_axis, candidate_axis
            )
            allowance = rule.uncertainty.allowance
            adjusted_score = max(0.0, raw_score - allowance)
            outcome = rule.thresholds.outcome(adjusted_score)
        except (TrainingDataInputError, ValueError, TypeError, IndexError) as exc:
            raw_score = None
            adjusted_score = None
            allowance = rule.uncertainty.allowance
            outcome = ObservableComparisonOutcome.INDETERMINATE
            diagnostics.append(str(exc))
        rule_results.append(ObservableRuleComparisonResult(
            rule_id=rule.rule_id,
            call_id=rule.call_id,
            observable_id=rule.observable_id,
            metric=rule.metric,
            reference_result_digest=evidence.reference_execution.result_identities[rule.call_id].content_digest,
            candidate_result_digest=evidence.candidate_execution.result_identities[rule.call_id].content_digest,
            raw_score=raw_score,
            adjusted_score=adjusted_score,
            uncertainty_allowance=allowance,
            outcome=outcome,
            required=rule.required,
            weight=rule.weight,
            reference_summary=_value_summary(reference_value),
            candidate_summary=_value_summary(candidate_value),
            atom_group_id=rule.atom_group_id,
            condition_id=rule.condition_id,
            diagnostics=tuple(diagnostics),
        ))

    required = [item for item in rule_results if item.required]
    overall = max((item.outcome for item in required), key=lambda value: _OUTCOME_ORDER[value])
    scored = [item for item in rule_results if item.adjusted_score is not None]
    weighted_mean = None
    if scored:
        weighted_mean = float(
            sum(item.weight * float(item.adjusted_score) for item in scored)
            / sum(item.weight for item in scored)
        )
    scopes: dict[str, ObservableComparisonOutcome] = {}
    rules_by_id = {rule.rule_id: rule for rule in policy.rules}
    for item in rule_results:
        key = _scope_key(rules_by_id[item.rule_id])
        current = scopes.get(key, ObservableComparisonOutcome.PASS)
        if _OUTCOME_ORDER[item.outcome] > _OUTCOME_ORDER[current]:
            scopes[key] = item.outcome
    return ObservableComparisonResult(
        policy_digest=policy.content_digest,
        evidence_digest=evidence.to_record().content_digest,
        evidence_role=role,
        rule_results=tuple(rule_results),
        overall_outcome=overall,
        weighted_mean_adjusted_score=weighted_mean,
        scope_outcomes={key: value.value for key, value in sorted(scopes.items())},
    )


def decide_observable_acceptance(
    result: ObservableComparisonResult,
    policy: ObservableComparisonPolicy,
) -> ObservableAcceptanceDecision:
    """Create a checkpoint-facing decision without changing scientific results."""

    if result.policy_digest != policy.content_digest:
        raise TrainingDataInputError("Comparison result does not belong to the supplied policy.")
    required = [item for item in result.rule_results if item.required]
    blocking: list[str] = []
    degraded: list[str] = []
    advisory: list[str] = []
    reasons: list[str] = []
    for item in result.rule_results:
        if item.required:
            if item.outcome is ObservableComparisonOutcome.FAIL:
                blocking.append(item.rule_id)
            elif item.outcome is ObservableComparisonOutcome.INDETERMINATE:
                if policy.required_indeterminate_is_failure:
                    blocking.append(item.rule_id)
                else:
                    degraded.append(item.rule_id)
            elif item.outcome is ObservableComparisonOutcome.DEGRADED:
                degraded.append(item.rule_id)
        elif item.outcome in {ObservableComparisonOutcome.FAIL, ObservableComparisonOutcome.INDETERMINATE}:
            advisory.append(item.rule_id)

    if blocking:
        outcome = ObservableComparisonOutcome.FAIL
        accepted = False
        reasons.append("one_or_more_required_observable_rules_failed")
    elif degraded:
        outcome = ObservableComparisonOutcome.DEGRADED
        accepted = bool(policy.accept_degraded)
        reasons.append("one_or_more_required_observable_rules_are_degraded")
        if not policy.accept_degraded:
            reasons.append("policy_rejects_degraded_observable_results")
    else:
        outcome = ObservableComparisonOutcome.PASS
        accepted = True
    if advisory:
        reasons.append("advisory_observable_rule_failures_present")
    if not required:
        raise TrainingDataInputError("Acceptance decision requires at least one required rule.")
    return ObservableAcceptanceDecision(
        policy_digest=policy.content_digest,
        comparison_result_digest=result.content_digest,
        evidence_role=result.evidence_role,
        outcome=outcome,
        accepted=accepted,
        blocking_rule_ids=tuple(blocking),
        degraded_rule_ids=tuple(degraded),
        advisory_failure_rule_ids=tuple(advisory),
        reasons=tuple(reasons),
    )


def build_profile_aware_observable_comparison_policy(
    *,
    policy_id: str,
    recipe: Any,
    recommendation_profile: ObservableRecommendationProfile | str,
    rules: Sequence[ObservableComparisonRule],
    material_profile_contracts: Any | None = None,
    **kwargs: Any,
) -> ObservableComparisonPolicy:
    """Build a policy bound to one recipe and optional material profile.

    The helper records identity only. It never chooses thresholds, atom groups,
    conditions, or scientific observable parameters on the user's behalf.
    """

    contracts_digest = None
    if material_profile_contracts is not None:
        contracts_digest = validate_digest(
            str(material_profile_contracts.content_digest),
            name="material_profile_contracts_digest",
        )
    return ObservableComparisonPolicy(
        policy_id=policy_id,
        recipe_digest=validate_digest(str(recipe.content_digest), name="recipe_digest"),
        recommendation_profile=ObservableRecommendationProfile(recommendation_profile),
        material_profile_digest=contracts_digest,
        rules=tuple(rules),
        **kwargs,
    )


# Advisory metric templates. Thresholds are deliberately absent: scientifically
# material tolerances must be predeclared by the user or project protocol.
_RECOMMENDED_TEMPLATES: Mapping[str, tuple[Mapping[str, Any], ...]] = {
    "structure.rdf": (
        {"suffix": "curve", "metric": "integrated_absolute_error", "value_path": "g_r", "axis_path": "r", "allow_interpolation": True},
        {"suffix": "peak", "metric": "peak_shift", "value_path": "g_r", "axis_path": "r", "allow_interpolation": True},
    ),
    "structure.coordination": (
        {"suffix": "distribution", "metric": "jensen_shannon_distance", "value_path": "probabilities", "axis_path": "coordination_values"},
        {"suffix": "mean", "metric": "symmetric_relative_error", "value_path": "mean"},
    ),
    "structure.bond_angle": (
        {"suffix": "distribution", "metric": "integrated_absolute_error", "value_path": "angle_weighted_density", "axis_path": "bin_centers", "allow_interpolation": True},
    ),
    "dynamics.msd": (
        {"suffix": "curve", "metric": "normalized_rmse", "value_path": "msd"},
    ),
    "dynamics.vacf": (
        {"suffix": "curve", "metric": "normalized_rmse", "value_path": "scalar_sum"},
    ),
    "spectrum.vacf": (
        {"suffix": "spectrum", "metric": "integrated_absolute_error", "value_path": "scalar_spectrum", "axis_path": "frequencies_thz", "allow_interpolation": True},
    ),
    "spectrum.velocity_welch": (
        {"suffix": "spectrum", "metric": "integrated_absolute_error", "value_path": "scalar_spectrum", "axis_path": "frequencies_thz", "allow_interpolation": True},
    ),
    "spectrum.vdos": (
        {"suffix": "spectrum", "metric": "integrated_absolute_error", "value_path": "total", "axis_path": "frequencies_thz", "allow_interpolation": True},
    ),
    "transport.vacf_diffusion": (
        {"suffix": "running", "metric": "normalized_rmse", "value_path": "running_diffusion_a2_per_ps"},
        {"suffix": "endpoint", "metric": "symmetric_relative_error", "value_path": "running_diffusion_a2_per_ps", "reducer": "last"},
    ),
    "transport.diffusion_plateau": (
        {"suffix": "value", "metric": "symmetric_relative_error", "value_path": "value_a2_per_ps"},
    ),
    "dynamics.self_van_hove": (
        {"suffix": "density", "metric": "normalized_rmse", "value_path": "density"},
    ),
    "dynamics.non_gaussian": (
        {"suffix": "alpha2", "metric": "normalized_rmse", "value_path": "alpha2"},
    ),
    "dynamics.self_intermediate_scattering": (
        {"suffix": "values", "metric": "normalized_rmse", "value_path": "values"},
    ),
    "transport.current_correlation": (
        {"suffix": "curve", "metric": "normalized_rmse", "value_path": "scalar"},
    ),
    "transport.ionic_conductivity": (
        {"suffix": "running", "metric": "normalized_rmse", "value_path": "running_conductivity_s_per_m"},
        {"suffix": "endpoint", "metric": "symmetric_relative_error", "value_path": "running_conductivity_s_per_m", "reducer": "last"},
    ),
    "transport.conductivity_plateau": (
        {"suffix": "value", "metric": "symmetric_relative_error", "value_path": "value_s_per_m"},
    ),
    "transport.nernst_einstein_comparison": (
        {"suffix": "collective", "metric": "symmetric_relative_error", "value_path": "collective_conductivity_s_per_m"},
        {"suffix": "nernst_einstein", "metric": "symmetric_relative_error", "value_path": "nernst_einstein_conductivity_s_per_m"},
    ),
}


def recommended_observable_comparison_templates(
    observable_id: str,
) -> tuple[Mapping[str, Any], ...]:
    """Return metric/extractor suggestions without thresholds or pass claims."""

    return tuple(MappingProxyType(dict(item)) for item in _RECOMMENDED_TEMPLATES.get(str(observable_id), ()))
