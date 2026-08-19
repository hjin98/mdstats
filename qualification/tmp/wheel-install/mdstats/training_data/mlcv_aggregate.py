"""MLCV-AGG1 conventional cross-validation aggregation.

Outer-fold target evaluation remains target-only. Replay evidence is reused
from the frozen SELECT1 representative and, for current evidence, its combined
score uses signed R_full-R0_full degradation. Historical v1 records retain
absolute-replay semantics.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from statistics import mean, stdev
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .mlcv_roles import MlcvDataRole, MlcvEvidenceOperation, require_mlcv_role
from .protocol import MaceJobKind

MLCV_CV_POLICY_SCHEMA = "mdstats.mlcv-cv-policy.v2"
MLCV_CV_POLICY_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-cv-policy.v1"})
MLCV_OUTER_FOLD_EVALUATION_SCHEMA = "mdstats.mlcv-outer-fold-evaluation.v2"
MLCV_OUTER_FOLD_EVALUATION_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-outer-fold-evaluation.v1"})
MLCV_METRIC_SUMMARY_SCHEMA = "mdstats.mlcv-metric-summary.v2"
MLCV_METRIC_SUMMARY_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-metric-summary.v1"})
MLCV_SEED_CV_AGGREGATE_SCHEMA = "mdstats.mlcv-seed-cv-aggregate.v2"
MLCV_SEED_CV_AGGREGATE_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-seed-cv-aggregate.v1"})
MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA = "mdstats.mlcv-campaign-cv-aggregate.v2"
MLCV_CAMPAIGN_CV_AGGREGATE_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-campaign-cv-aggregate.v1"})


@dataclass(frozen=True, slots=True)
class MlcvCrossValidationPolicy:
    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    target_score_weight: float = 1.0
    replay_score_weight: float = 1.0
    replay_degradation_budget_ev_per_angstrom: float | None = None
    require_all_folds: bool = True
    dispersion_gate_enabled: bool = False
    serialization_schema: str = field(default=MLCV_CV_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_CV_POLICY_SCHEMA, *MLCV_CV_POLICY_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV CV-policy schema.")
        for name in ("maximum_target_force_rmse_ev_per_angstrom", "target_score_weight", "replay_score_weight"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"MLCV-AGG1 {name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if self.serialization_schema == MLCV_CV_POLICY_SCHEMA:
            budget = self.replay_degradation_budget_ev_per_angstrom
            if budget is None:
                budget = self.target_score_weight / self.replay_score_weight * self.maximum_target_force_rmse_ev_per_angstrom
            budget = float(budget)
            if not math.isfinite(budget) or budget <= 0.0:
                raise TrainingDataInputError("MLCV-AGG1 replay degradation budget must be finite and positive.")
            object.__setattr__(self, "replay_degradation_budget_ev_per_angstrom", budget)
        if not self.require_all_folds:
            raise TrainingDataInputError("MLCV-AGG1 requires all configured folds to survive.")
        if self.dispersion_gate_enabled:
            raise TrainingDataInputError("MLCV-AGG1 keeps cross-fold dispersion diagnostic-only.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "target_score_weight": self.target_score_weight,
            "replay_score_weight": self.replay_score_weight,
            "require_all_folds": self.require_all_folds,
            "dispersion_gate_enabled": self.dispersion_gate_enabled,
        }
        if self.serialization_schema == MLCV_CV_POLICY_SCHEMA:
            payload.update({
                "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
                "replay_semantics": "foundation_relative_degradation",
            })
        return payload

    @property
    def policy_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvCrossValidationPolicy":
        schema = payload.get("schema")
        if schema not in {MLCV_CV_POLICY_SCHEMA, *MLCV_CV_POLICY_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV CV-policy schema.")
        result = cls(
            maximum_target_force_rmse_ev_per_angstrom=float(payload["maximum_target_force_rmse_ev_per_angstrom"]),
            target_score_weight=float(payload["target_score_weight"]), replay_score_weight=float(payload["replay_score_weight"]),
            replay_degradation_budget_ev_per_angstrom=None if schema in MLCV_CV_POLICY_LEGACY_SCHEMAS else float(payload["replay_degradation_budget_ev_per_angstrom"]),
            require_all_folds=bool(payload.get("require_all_folds", True)), dispersion_gate_enabled=bool(payload.get("dispersion_gate_enabled", False)),
            serialization_schema=str(schema),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MLCV CV-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvOuterFoldEvaluationRecord:
    run_plan_digest: str
    run_id: str
    seed: int
    fold_index: int
    selection_record_digest: str
    outer_target_role: MlcvDataRole
    outer_target_artifact_digest: str
    outer_target_sha256: str
    policy_digest: str
    outcome: str
    representative_checkpoint_sha256: str | None = None
    representative_checkpoint_epoch: int | None = None
    outer_evaluation_record_digest: str | None = None
    outer_target_force_rmse_ev_per_angstrom: float | None = None
    representative_replay_full_rmse_ev_per_angstrom: float | None = None
    representative_replay_foundation_full_rmse_ev_per_angstrom: float | None = None
    representative_replay_degradation_full_rmse_ev_per_angstrom: float | None = None
    replay_degradation_budget_ev_per_angstrom: float | None = None
    combined_score_ev_per_angstrom: float | None = None
    rejection_reasons: tuple[str, ...] = ()
    production_eligible: bool = False
    serialization_schema: str = field(default=MLCV_OUTER_FOLD_EVALUATION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_OUTER_FOLD_EVALUATION_SCHEMA, *MLCV_OUTER_FOLD_EVALUATION_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV outer-fold evaluation schema.")
        for name in ("run_plan_digest", "selection_record_digest", "outer_target_artifact_digest", "outer_target_sha256", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.outer_evaluation_record_digest is not None:
            object.__setattr__(self, "outer_evaluation_record_digest", validate_digest(self.outer_evaluation_record_digest, name="outer_evaluation_record_digest"))
        object.__setattr__(self, "outer_target_role", MlcvDataRole(self.outer_target_role))
        require_mlcv_role(self.outer_target_role, MlcvEvidenceOperation.OUTER_CV_EVALUATION, context="MLCV outer-fold evaluation")
        if self.outer_target_role is not MlcvDataRole.TARGET_OUTER_CV_EVALUATION:
            raise TrainingDataInputError("MLCV-AGG1 outer-fold evidence must use TARGET_OUTER_CV_EVALUATION authority.")
        if int(self.fold_index) < 0 or int(self.seed) < 0 or self.production_eligible:
            raise TrainingDataInputError("MLCV-AGG1 fold identity/production authority is invalid.")
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons))); object.__setattr__(self, "rejection_reasons", reasons)
        if self.outcome not in {"passed", "no_representative", "outer_target_threshold_exceeded"}:
            raise TrainingDataInputError("Unsupported MLCV outer-fold outcome.")
        optional_metrics = (
            self.outer_target_force_rmse_ev_per_angstrom, self.representative_replay_full_rmse_ev_per_angstrom,
            self.representative_replay_foundation_full_rmse_ev_per_angstrom, self.representative_replay_degradation_full_rmse_ev_per_angstrom,
            self.replay_degradation_budget_ev_per_angstrom, self.combined_score_ev_per_angstrom,
        )
        if self.outcome == "no_representative":
            if any(v is not None for v in (self.representative_checkpoint_sha256, self.representative_checkpoint_epoch, self.outer_evaluation_record_digest, *optional_metrics)) or not reasons:
                raise TrainingDataInputError("No-representative outer-fold record carries evaluation values or lacks a reason.")
            return
        if self.representative_checkpoint_sha256 is None or self.representative_checkpoint_epoch is None or self.outer_evaluation_record_digest is None:
            raise TrainingDataInputError("Evaluated outer-fold records require frozen representative/evaluation identity.")
        object.__setattr__(self, "representative_checkpoint_sha256", validate_digest(self.representative_checkpoint_sha256, name="representative_checkpoint_sha256"))
        if int(self.representative_checkpoint_epoch) < 0:
            raise TrainingDataInputError("Outer-fold representative epoch is invalid.")
        for name in ("outer_target_force_rmse_ev_per_angstrom", "representative_replay_full_rmse_ev_per_angstrom", "representative_replay_foundation_full_rmse_ev_per_angstrom", "replay_degradation_budget_ev_per_angstrom"):
            value = getattr(self, name)
            if self.serialization_schema in MLCV_OUTER_FOLD_EVALUATION_LEGACY_SCHEMAS and name in {"representative_replay_foundation_full_rmse_ev_per_angstrom", "replay_degradation_budget_ev_per_angstrom"}:
                continue
            if value is None or not math.isfinite(float(value)) or float(value) < 0.0:
                raise TrainingDataInputError(f"MLCV-AGG1 {name} must be finite and nonnegative.")
        if self.serialization_schema == MLCV_OUTER_FOLD_EVALUATION_SCHEMA:
            deg = self.representative_replay_degradation_full_rmse_ev_per_angstrom
            if deg is None or not math.isfinite(float(deg)):
                raise TrainingDataInputError("MLCV-AGG1 replay degradation must be finite; negative improvement is valid.")
            expected = float(self.representative_replay_full_rmse_ev_per_angstrom) - float(self.representative_replay_foundation_full_rmse_ev_per_angstrom)
            if not math.isclose(expected, float(deg), rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("MLCV-AGG1 replay degradation mismatch.")
        if self.combined_score_ev_per_angstrom is None or not math.isfinite(float(self.combined_score_ev_per_angstrom)):
            raise TrainingDataInputError("MLCV-AGG1 combined score must be finite.")
        if self.outcome == "passed" and reasons:
            raise TrainingDataInputError("Passing outer-fold record cannot carry rejection reasons.")
        if self.outcome != "passed" and not reasons:
            raise TrainingDataInputError("Rejected outer-fold record requires rejection reasons.")

    @property
    def survived(self) -> bool: return self.outcome == "passed"

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema, "run_plan_digest": self.run_plan_digest, "run_id": self.run_id,
            "seed": int(self.seed), "fold_index": int(self.fold_index), "selection_record_digest": self.selection_record_digest,
            "outer_target_role": self.outer_target_role.value, "outer_target_artifact_digest": self.outer_target_artifact_digest,
            "outer_target_sha256": self.outer_target_sha256, "policy_digest": self.policy_digest, "outcome": self.outcome,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "representative_checkpoint_epoch": self.representative_checkpoint_epoch,
            "outer_evaluation_record_digest": self.outer_evaluation_record_digest,
            "outer_target_force_rmse_ev_per_angstrom": self.outer_target_force_rmse_ev_per_angstrom,
            "representative_replay_full_rmse_ev_per_angstrom": self.representative_replay_full_rmse_ev_per_angstrom,
            "combined_score_ev_per_angstrom": self.combined_score_ev_per_angstrom,
            "rejection_reasons": list(self.rejection_reasons), "production_eligible": False,
        }
        if self.serialization_schema == MLCV_OUTER_FOLD_EVALUATION_SCHEMA:
            payload.update({
                "representative_replay_foundation_full_rmse_ev_per_angstrom": self.representative_replay_foundation_full_rmse_ev_per_angstrom,
                "representative_replay_degradation_full_rmse_ev_per_angstrom": self.representative_replay_degradation_full_rmse_ev_per_angstrom,
                "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
                "replay_semantics": "foundation_relative_degradation",
            })
        return payload

    @property
    def content_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvOuterFoldEvaluationRecord":
        schema = payload.get("schema")
        if schema not in {MLCV_OUTER_FOLD_EVALUATION_SCHEMA, *MLCV_OUTER_FOLD_EVALUATION_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV outer-fold evaluation schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]), run_id=str(payload["run_id"]), seed=int(payload["seed"]), fold_index=int(payload["fold_index"]), selection_record_digest=str(payload["selection_record_digest"]),
            outer_target_role=MlcvDataRole(payload["outer_target_role"]), outer_target_artifact_digest=str(payload["outer_target_artifact_digest"]), outer_target_sha256=str(payload["outer_target_sha256"]), policy_digest=str(payload["policy_digest"]), outcome=str(payload["outcome"]),
            representative_checkpoint_sha256=None if payload.get("representative_checkpoint_sha256") is None else str(payload["representative_checkpoint_sha256"]), representative_checkpoint_epoch=None if payload.get("representative_checkpoint_epoch") is None else int(payload["representative_checkpoint_epoch"]),
            outer_evaluation_record_digest=None if payload.get("outer_evaluation_record_digest") is None else str(payload["outer_evaluation_record_digest"]), outer_target_force_rmse_ev_per_angstrom=None if payload.get("outer_target_force_rmse_ev_per_angstrom") is None else float(payload["outer_target_force_rmse_ev_per_angstrom"]),
            representative_replay_full_rmse_ev_per_angstrom=None if payload.get("representative_replay_full_rmse_ev_per_angstrom") is None else float(payload["representative_replay_full_rmse_ev_per_angstrom"]),
            representative_replay_foundation_full_rmse_ev_per_angstrom=None if payload.get("representative_replay_foundation_full_rmse_ev_per_angstrom") is None else float(payload["representative_replay_foundation_full_rmse_ev_per_angstrom"]), representative_replay_degradation_full_rmse_ev_per_angstrom=None if payload.get("representative_replay_degradation_full_rmse_ev_per_angstrom") is None else float(payload["representative_replay_degradation_full_rmse_ev_per_angstrom"]),
            replay_degradation_budget_ev_per_angstrom=None if payload.get("replay_degradation_budget_ev_per_angstrom") is None else float(payload["replay_degradation_budget_ev_per_angstrom"]), combined_score_ev_per_angstrom=None if payload.get("combined_score_ev_per_angstrom") is None else float(payload["combined_score_ev_per_angstrom"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())), production_eligible=bool(payload.get("production_eligible", False)), serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV outer-fold evaluation digest mismatch.")
        return result


def build_mlcv_outer_fold_record(run: Any, selection: Any, evaluation: Any | None, policy: MlcvCrossValidationPolicy, *, outer_target_artifact_digest: str, outer_target_sha256: str) -> MlcvOuterFoldEvaluationRecord:
    if run.kind is not MaceJobKind.CROSS_VALIDATION_FOLD or run.fold_index is None:
        raise TrainingDataInputError("MLCV-AGG1 outer evaluation requires a cross-validation fold run.")
    if selection.run_plan_digest != run.content_digest or selection.fold_index != run.fold_index:
        raise TrainingDataInputError("MLCV-AGG1 selection/run lineage mismatch.")
    if selection.outcome != "representative_selected":
        if evaluation is not None:
            raise TrainingDataInputError("MLCV-AGG1 cannot evaluate an alternate checkpoint when a fold has no representative.")
        return MlcvOuterFoldEvaluationRecord(
            run_plan_digest=run.content_digest, run_id=run.run_id, seed=run.seed, fold_index=run.fold_index,
            selection_record_digest=selection.content_digest, outer_target_role=MlcvDataRole.TARGET_OUTER_CV_EVALUATION,
            outer_target_artifact_digest=outer_target_artifact_digest, outer_target_sha256=outer_target_sha256,
            policy_digest=policy.policy_digest, outcome="no_representative", rejection_reasons=("no_full_selection_admissible_checkpoint",),
            serialization_schema=MLCV_OUTER_FOLD_EVALUATION_SCHEMA if policy.serialization_schema == MLCV_CV_POLICY_SCHEMA else "mdstats.mlcv-outer-fold-evaluation.v1",
        )
    representative = selection.representative_candidate
    if representative is None or evaluation is None:
        raise TrainingDataInputError("MLCV-AGG1 selected fold representative requires outer evaluation evidence.")
    if evaluation.run_plan_digest != run.content_digest or evaluation.checkpoint_sha256 != representative.checkpoint_sha256:
        raise TrainingDataInputError("MLCV-AGG1 outer evaluation cannot change the frozen representative.")
    if evaluation.target_monitor_artifact_digest != outer_target_artifact_digest or evaluation.target_monitor_sha256 != outer_target_sha256:
        raise TrainingDataInputError("MLCV-AGG1 outer evaluation artifact lineage mismatch.")
    if evaluation.replay_monitor_artifact_digest is not None or evaluation.replay_configuration_count != 0:
        raise TrainingDataInputError("MLCV-AGG1 outer-fold inference must be target-only; replay is reused from SELECT1.")
    target = evaluation.target_candidate_metrics
    if target is None:
        raise TrainingDataInputError("MLCV-AGG1 outer evaluation requires target candidate metrics.")
    target_rmse = float(target.force_component_rmse_ev_per_angstrom)
    replay_rmse = float(representative.replay_force_rmse_ev_per_angstrom)
    current = policy.serialization_schema == MLCV_CV_POLICY_SCHEMA
    if current:
        foundation = representative.replay_foundation_force_rmse_ev_per_angstrom
        degradation = representative.replay_degradation_force_rmse_ev_per_angstrom
        budget = representative.replay_degradation_budget_ev_per_angstrom
        if foundation is None or degradation is None or budget is None:
            raise TrainingDataInputError("MLCV-AGG1 current evidence requires SELECT1 replay baseline/degradation/budget.")
        if not math.isclose(float(budget), float(policy.replay_degradation_budget_ev_per_angstrom), rel_tol=0.0, abs_tol=1e-15):
            raise TrainingDataInputError("MLCV-AGG1 replay degradation budget differs from SELECT1 authority.")
        replay_term = float(degradation)
        schema = MLCV_OUTER_FOLD_EVALUATION_SCHEMA
    else:
        foundation = degradation = budget = None
        replay_term = replay_rmse
        schema = "mdstats.mlcv-outer-fold-evaluation.v1"
    combined = (policy.target_score_weight * target_rmse + policy.replay_score_weight * replay_term) / (policy.target_score_weight + policy.replay_score_weight)
    passed = target_rmse <= policy.maximum_target_force_rmse_ev_per_angstrom
    return MlcvOuterFoldEvaluationRecord(
        run_plan_digest=run.content_digest, run_id=run.run_id, seed=run.seed, fold_index=run.fold_index,
        selection_record_digest=selection.content_digest, outer_target_role=MlcvDataRole.TARGET_OUTER_CV_EVALUATION,
        outer_target_artifact_digest=outer_target_artifact_digest, outer_target_sha256=outer_target_sha256, policy_digest=policy.policy_digest,
        outcome="passed" if passed else "outer_target_threshold_exceeded", representative_checkpoint_sha256=representative.checkpoint_sha256,
        representative_checkpoint_epoch=representative.checkpoint_epoch, outer_evaluation_record_digest=evaluation.content_digest,
        outer_target_force_rmse_ev_per_angstrom=target_rmse, representative_replay_full_rmse_ev_per_angstrom=replay_rmse,
        representative_replay_foundation_full_rmse_ev_per_angstrom=foundation, representative_replay_degradation_full_rmse_ev_per_angstrom=degradation,
        replay_degradation_budget_ev_per_angstrom=budget, combined_score_ev_per_angstrom=float(combined),
        rejection_reasons=() if passed else ("outer_target_force_rmse_threshold_exceeded",), serialization_schema=schema,
    )


@dataclass(frozen=True, slots=True)
class MlcvMetricSummary:
    metric_name: str
    fold_indices: tuple[int, ...]
    values_ev_per_angstrom: tuple[float, ...]
    mean_ev_per_angstrom: float
    sample_standard_deviation_ev_per_angstrom: float | None
    minimum_ev_per_angstrom: float
    maximum_ev_per_angstrom: float
    range_ev_per_angstrom: float
    worst_fold_index: int
    signed_values_allowed: bool = False
    serialization_schema: str = field(default=MLCV_METRIC_SUMMARY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_METRIC_SUMMARY_SCHEMA, *MLCV_METRIC_SUMMARY_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV metric-summary schema.")
        indices = tuple(int(v) for v in self.fold_indices); values = tuple(float(v) for v in self.values_ev_per_angstrom)
        if not values or len(indices) != len(values) or len(set(indices)) != len(indices):
            raise TrainingDataInputError("MLCV metric summary requires unique fold-indexed values.")
        allow_signed = bool(self.signed_values_allowed) if self.serialization_schema == MLCV_METRIC_SUMMARY_SCHEMA else False
        if any(not math.isfinite(v) or (not allow_signed and v < 0.0) for v in values):
            raise TrainingDataInputError("MLCV metric summary contains invalid values.")
        object.__setattr__(self, "fold_indices", indices); object.__setattr__(self, "values_ev_per_angstrom", values)
        for name in ("mean_ev_per_angstrom", "minimum_ev_per_angstrom", "maximum_ev_per_angstrom"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or (not allow_signed and value < 0.0):
                raise TrainingDataInputError(f"MLCV metric summary {name} is invalid.")
            object.__setattr__(self, name, value)
        rng = float(self.range_ev_per_angstrom)
        if not math.isfinite(rng) or rng < 0.0:
            raise TrainingDataInputError("MLCV metric summary range is invalid.")
        object.__setattr__(self, "range_ev_per_angstrom", rng)
        sd = self.sample_standard_deviation_ev_per_angstrom
        if sd is not None and (not math.isfinite(float(sd)) or float(sd) < 0.0):
            raise TrainingDataInputError("MLCV metric summary sample standard deviation is invalid.")
        if sd is not None: object.__setattr__(self, "sample_standard_deviation_ev_per_angstrom", float(sd))
        if self.worst_fold_index not in indices:
            raise TrainingDataInputError("MLCV metric summary worst fold is absent from coverage.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema, "metric_name": self.metric_name, "fold_indices": list(self.fold_indices),
            "values_ev_per_angstrom": list(self.values_ev_per_angstrom), "mean_ev_per_angstrom": self.mean_ev_per_angstrom,
            "sample_standard_deviation_ev_per_angstrom": self.sample_standard_deviation_ev_per_angstrom,
            "minimum_ev_per_angstrom": self.minimum_ev_per_angstrom, "maximum_ev_per_angstrom": self.maximum_ev_per_angstrom,
            "range_ev_per_angstrom": self.range_ev_per_angstrom, "worst_fold_index": self.worst_fold_index,
        }
        if self.serialization_schema == MLCV_METRIC_SUMMARY_SCHEMA:
            payload["signed_values_allowed"] = bool(self.signed_values_allowed)
        return payload

    @property
    def content_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "content_digest": self.content_digest}
    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvMetricSummary":
        schema = payload.get("schema")
        if schema not in {MLCV_METRIC_SUMMARY_SCHEMA, *MLCV_METRIC_SUMMARY_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV metric-summary schema.")
        result = cls(metric_name=str(payload["metric_name"]), fold_indices=tuple(int(v) for v in payload["fold_indices"]), values_ev_per_angstrom=tuple(float(v) for v in payload["values_ev_per_angstrom"]), mean_ev_per_angstrom=float(payload["mean_ev_per_angstrom"]), sample_standard_deviation_ev_per_angstrom=None if payload.get("sample_standard_deviation_ev_per_angstrom") is None else float(payload["sample_standard_deviation_ev_per_angstrom"]), minimum_ev_per_angstrom=float(payload["minimum_ev_per_angstrom"]), maximum_ev_per_angstrom=float(payload["maximum_ev_per_angstrom"]), range_ev_per_angstrom=float(payload["range_ev_per_angstrom"]), worst_fold_index=int(payload["worst_fold_index"]), signed_values_allowed=bool(payload.get("signed_values_allowed", False)), serialization_schema=str(schema))
        if payload.get("content_digest") not in (None, result.content_digest): raise TrainingDataSerializationError("MLCV metric-summary digest mismatch.")
        return result


def summarize_mlcv_fold_metric(metric_name: str, values: Sequence[tuple[int, float]], *, signed_values_allowed: bool = False) -> MlcvMetricSummary | None:
    ordered = tuple(sorted((int(i), float(v)) for i, v in values))
    if not ordered: return None
    indices = tuple(i for i, _ in ordered); data = tuple(v for _, v in ordered); maximum = max(data)
    return MlcvMetricSummary(metric_name=metric_name, fold_indices=indices, values_ev_per_angstrom=data, mean_ev_per_angstrom=float(mean(data)), sample_standard_deviation_ev_per_angstrom=None if len(data) < 2 else float(stdev(data)), minimum_ev_per_angstrom=float(min(data)), maximum_ev_per_angstrom=float(maximum), range_ev_per_angstrom=float(maximum-min(data)), worst_fold_index=min(i for i, value in ordered if value == maximum), signed_values_allowed=signed_values_allowed)


@dataclass(frozen=True, slots=True)
class MlcvSeedCvAggregateRecord:
    campaign_plan_digest: str
    protocol_family_digest: str
    protocol_variant_digest: str
    training_mode: str
    selection_size: int
    seed: int
    policy_digest: str
    expected_fold_count: int
    fold_records: tuple[MlcvOuterFoldEvaluationRecord, ...]
    outcome: str
    target_summary: MlcvMetricSummary | None
    replay_summary: MlcvMetricSummary | None
    combined_summary: MlcvMetricSummary | None
    replay_absolute_summary: MlcvMetricSummary | None = None
    failure_reasons: tuple[str, ...] = ()
    dispersion_authority: str = "diagnostic_only"
    serialization_schema: str = field(default=MLCV_SEED_CV_AGGREGATE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_SEED_CV_AGGREGATE_SCHEMA, *MLCV_SEED_CV_AGGREGATE_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV seed-CV aggregate schema.")
        for name in ("campaign_plan_digest", "protocol_family_digest", "protocol_variant_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        folds = tuple(sorted(self.fold_records, key=lambda v: v.fold_index))
        if len({v.fold_index for v in folds}) != len(folds) or any(v.seed != self.seed or v.policy_digest != self.policy_digest for v in folds):
            raise TrainingDataInputError("MLCV seed aggregate fold lineage mismatch.")
        object.__setattr__(self, "fold_records", folds)
        if self.expected_fold_count < 0 or self.outcome not in {"cv_robust", "cv_failed", "cv_not_performed"}:
            raise TrainingDataInputError("Invalid MLCV seed aggregate outcome/coverage.")
        reasons = tuple(sorted(set(str(v) for v in self.failure_reasons))); object.__setattr__(self, "failure_reasons", reasons)
        if self.dispersion_authority != "diagnostic_only": raise TrainingDataInputError("MLCV-AGG1 dispersion must remain diagnostic-only.")
        if self.expected_fold_count == 0:
            if self.outcome != "cv_not_performed" or folds: raise TrainingDataInputError("Zero-fold variant must be cv_not_performed.")
        elif self.outcome == "cv_robust":
            if len(folds) != self.expected_fold_count or not all(v.survived for v in folds) or reasons: raise TrainingDataInputError("Robust seed aggregate requires all-fold survival.")
        elif not reasons: raise TrainingDataInputError("Failed MLCV seed aggregate requires failure reasons.")

    @property
    def all_fold_survival(self) -> bool: return self.outcome == "cv_robust"
    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema, "campaign_plan_digest": self.campaign_plan_digest,
            "protocol_family_digest": self.protocol_family_digest, "protocol_variant_digest": self.protocol_variant_digest,
            "training_mode": self.training_mode, "selection_size": int(self.selection_size), "seed": int(self.seed),
            "policy_digest": self.policy_digest, "expected_fold_count": int(self.expected_fold_count), "fold_records": [v.to_dict() for v in self.fold_records],
            "outcome": self.outcome, "target_summary": None if self.target_summary is None else self.target_summary.to_dict(),
            "replay_summary": None if self.replay_summary is None else self.replay_summary.to_dict(), "combined_summary": None if self.combined_summary is None else self.combined_summary.to_dict(),
            "failure_reasons": list(self.failure_reasons), "dispersion_authority": self.dispersion_authority,
        }
        if self.serialization_schema == MLCV_SEED_CV_AGGREGATE_SCHEMA:
            payload.update({"replay_absolute_summary": None if self.replay_absolute_summary is None else self.replay_absolute_summary.to_dict(), "replay_semantics": "foundation_relative_degradation"})
        return payload
    @property
    def content_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "content_digest": self.content_digest}
    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvSeedCvAggregateRecord":
        schema = payload.get("schema")
        if schema not in {MLCV_SEED_CV_AGGREGATE_SCHEMA, *MLCV_SEED_CV_AGGREGATE_LEGACY_SCHEMAS}: raise TrainingDataSerializationError("Unsupported MLCV seed-CV aggregate schema.")
        result = cls(campaign_plan_digest=str(payload["campaign_plan_digest"]), protocol_family_digest=str(payload["protocol_family_digest"]), protocol_variant_digest=str(payload["protocol_variant_digest"]), training_mode=str(payload["training_mode"]), selection_size=int(payload["selection_size"]), seed=int(payload["seed"]), policy_digest=str(payload["policy_digest"]), expected_fold_count=int(payload["expected_fold_count"]), fold_records=tuple(MlcvOuterFoldEvaluationRecord.from_dict(v) for v in payload.get("fold_records", ())), outcome=str(payload["outcome"]), target_summary=None if payload.get("target_summary") is None else MlcvMetricSummary.from_dict(payload["target_summary"]), replay_summary=None if payload.get("replay_summary") is None else MlcvMetricSummary.from_dict(payload["replay_summary"]), combined_summary=None if payload.get("combined_summary") is None else MlcvMetricSummary.from_dict(payload["combined_summary"]), replay_absolute_summary=None if payload.get("replay_absolute_summary") is None else MlcvMetricSummary.from_dict(payload["replay_absolute_summary"]), failure_reasons=tuple(str(v) for v in payload.get("failure_reasons", ())), dispersion_authority=str(payload.get("dispersion_authority", "diagnostic_only")), serialization_schema=str(schema))
        if payload.get("content_digest") not in (None, result.content_digest): raise TrainingDataSerializationError("MLCV seed-CV aggregate digest mismatch.")
        return result


def aggregate_mlcv_seed_cv(campaign: Any, runs: Sequence[Any], fold_records: Sequence[MlcvOuterFoldEvaluationRecord], policy: MlcvCrossValidationPolicy) -> MlcvSeedCvAggregateRecord:
    runs = tuple(runs)
    if not runs: raise TrainingDataInputError("MLCV-AGG1 seed aggregation requires a campaign variant.")
    seeds={int(v.seed) for v in runs}; variants={v.protocol_variant_digest for v in runs}; families={v.protocol_family_digest for v in runs}; modes={v.training_mode.value for v in runs}; sizes={int(v.selection_size) for v in runs}
    if any(len(v)!=1 for v in (seeds,variants,families,modes,sizes)): raise TrainingDataInputError("MLCV-AGG1 seed aggregation mixes incompatible variants.")
    folds=tuple(sorted((v for v in runs if v.kind is MaceJobKind.CROSS_VALIDATION_FOLD), key=lambda v:int(v.fold_index))); expected=len(folds); records=tuple(sorted(fold_records,key=lambda v:v.fold_index))
    schema = MLCV_SEED_CV_AGGREGATE_SCHEMA if policy.serialization_schema == MLCV_CV_POLICY_SCHEMA else "mdstats.mlcv-seed-cv-aggregate.v1"
    if expected==0:
        if records: raise TrainingDataInputError("MLCV-AGG1 received outer-fold evidence for zero-fold variant.")
        return MlcvSeedCvAggregateRecord(campaign_plan_digest=campaign.content_digest, protocol_family_digest=next(iter(families)), protocol_variant_digest=next(iter(variants)), training_mode=next(iter(modes)), selection_size=next(iter(sizes)), seed=next(iter(seeds)), policy_digest=policy.policy_digest, expected_fold_count=0, fold_records=(), outcome="cv_not_performed", target_summary=None, replay_summary=None, combined_summary=None, replay_absolute_summary=None, serialization_schema=schema)
    expected_by_index={int(v.fold_index):v for v in folds}
    if set(v.fold_index for v in records)!=set(expected_by_index): raise TrainingDataInputError("MLCV-AGG1 requires one outer-fold record per fold.")
    for record in records:
        run=expected_by_index[record.fold_index]
        if record.run_plan_digest!=run.content_digest or record.seed!=run.seed or record.policy_digest!=policy.policy_digest: raise TrainingDataInputError("MLCV-AGG1 fold record/campaign lineage mismatch.")
    failures=[f"fold_{v.fold_index}:{v.outcome}" for v in records if not v.survived]
    target_values=[(v.fold_index,v.outer_target_force_rmse_ev_per_angstrom) for v in records if v.outer_target_force_rmse_ev_per_angstrom is not None]
    absolute_values=[(v.fold_index,v.representative_replay_full_rmse_ev_per_angstrom) for v in records if v.representative_replay_full_rmse_ev_per_angstrom is not None]
    if policy.serialization_schema == MLCV_CV_POLICY_SCHEMA:
        replay_values=[(v.fold_index,v.representative_replay_degradation_full_rmse_ev_per_angstrom) for v in records if v.representative_replay_degradation_full_rmse_ev_per_angstrom is not None]
        replay_name="representative_replay_full_degradation_rmse"; signed=True
    else:
        replay_values=absolute_values; replay_name="representative_replay_full_rmse"; signed=False
    combined_values=[(v.fold_index,v.combined_score_ev_per_angstrom) for v in records if v.combined_score_ev_per_angstrom is not None]
    outcome="cv_robust" if len(records)==expected and all(v.survived for v in records) else "cv_failed"
    return MlcvSeedCvAggregateRecord(campaign_plan_digest=campaign.content_digest, protocol_family_digest=next(iter(families)), protocol_variant_digest=next(iter(variants)), training_mode=next(iter(modes)), selection_size=next(iter(sizes)), seed=next(iter(seeds)), policy_digest=policy.policy_digest, expected_fold_count=expected, fold_records=records, outcome=outcome, target_summary=summarize_mlcv_fold_metric("outer_target_force_rmse",target_values), replay_summary=summarize_mlcv_fold_metric(replay_name,replay_values,signed_values_allowed=signed), replay_absolute_summary=None if schema.endswith(".v1") else summarize_mlcv_fold_metric("representative_replay_full_absolute_rmse",absolute_values), combined_summary=summarize_mlcv_fold_metric("outer_target_plus_replay_degradation_combined_score" if signed else "outer_target_plus_replay_combined_score",combined_values,signed_values_allowed=signed), failure_reasons=tuple(failures), serialization_schema=schema)


@dataclass(frozen=True, slots=True)
class MlcvCampaignCvAggregateRecord:
    campaign_plan_digest: str
    policy_digest: str
    seed_aggregates: tuple[MlcvSeedCvAggregateRecord, ...]
    outcome: str
    robust_seed_count: int
    failed_seed_count: int
    cv_not_performed_seed_count: int
    production_selection_created: bool = False
    next_gate: str = "MLCV-FINAL1"
    serialization_schema: str = field(default=MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA, repr=False, compare=False)
    def __post_init__(self)->None:
        if self.serialization_schema not in {MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA,*MLCV_CAMPAIGN_CV_AGGREGATE_LEGACY_SCHEMAS}: raise TrainingDataInputError("Unsupported MLCV campaign-CV aggregate schema.")
        for name in ("campaign_plan_digest","policy_digest"): object.__setattr__(self,name,validate_digest(getattr(self,name),name=name))
        values=tuple(sorted(self.seed_aggregates,key=lambda v:(v.training_mode,v.selection_size,v.seed)))
        if not values or any(v.campaign_plan_digest!=self.campaign_plan_digest or v.policy_digest!=self.policy_digest for v in values): raise TrainingDataInputError("MLCV campaign CV aggregate lineage mismatch.")
        object.__setattr__(self,"seed_aggregates",values); robust=sum(v.outcome=="cv_robust" for v in values); failed=sum(v.outcome=="cv_failed" for v in values); skipped=sum(v.outcome=="cv_not_performed" for v in values)
        if (self.robust_seed_count,self.failed_seed_count,self.cv_not_performed_seed_count)!=(robust,failed,skipped): raise TrainingDataInputError("MLCV campaign CV outcome counts are inconsistent.")
        expected="cv_failed" if failed else ("cv_not_performed" if skipped==len(values) else "cv_robust")
        if self.outcome!=expected or self.production_selection_created: raise TrainingDataInputError("MLCV campaign CV outcome/authority is inconsistent.")
    def _payload(self)->dict[str,Any]:
        p={"schema":self.serialization_schema,"campaign_plan_digest":self.campaign_plan_digest,"policy_digest":self.policy_digest,"seed_aggregates":[v.to_dict() for v in self.seed_aggregates],"outcome":self.outcome,"robust_seed_count":self.robust_seed_count,"failed_seed_count":self.failed_seed_count,"cv_not_performed_seed_count":self.cv_not_performed_seed_count,"production_selection_created":False,"next_gate":self.next_gate}
        if self.serialization_schema==MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA:p["replay_semantics"]="foundation_relative_degradation"
        return p
    @property
    def content_digest(self)->str:return digest(self._payload())
    def to_dict(self)->dict[str,Any]:return {**self._payload(),"content_digest":self.content_digest}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"MlcvCampaignCvAggregateRecord":
        schema=payload.get("schema")
        if schema not in {MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA,*MLCV_CAMPAIGN_CV_AGGREGATE_LEGACY_SCHEMAS}:raise TrainingDataSerializationError("Unsupported MLCV campaign-CV aggregate schema.")
        r=cls(campaign_plan_digest=str(payload["campaign_plan_digest"]),policy_digest=str(payload["policy_digest"]),seed_aggregates=tuple(MlcvSeedCvAggregateRecord.from_dict(v) for v in payload["seed_aggregates"]),outcome=str(payload["outcome"]),robust_seed_count=int(payload["robust_seed_count"]),failed_seed_count=int(payload["failed_seed_count"]),cv_not_performed_seed_count=int(payload["cv_not_performed_seed_count"]),production_selection_created=bool(payload.get("production_selection_created",False)),next_gate=str(payload.get("next_gate","MLCV-FINAL1")),serialization_schema=str(schema))
        if payload.get("content_digest") not in (None,r.content_digest):raise TrainingDataSerializationError("MLCV campaign-CV aggregate digest mismatch.")
        return r


def aggregate_mlcv_campaign_cv(campaign: Any, seed_aggregates: Sequence[MlcvSeedCvAggregateRecord], policy: MlcvCrossValidationPolicy) -> MlcvCampaignCvAggregateRecord:
    values=tuple(seed_aggregates)
    if not values: raise TrainingDataInputError("MLCV-AGG1 campaign aggregation requires seed aggregates.")
    failed=sum(v.outcome=="cv_failed" for v in values); robust=sum(v.outcome=="cv_robust" for v in values); skipped=sum(v.outcome=="cv_not_performed" for v in values); outcome="cv_failed" if failed else ("cv_not_performed" if skipped==len(values) else "cv_robust")
    return MlcvCampaignCvAggregateRecord(campaign_plan_digest=campaign.content_digest,policy_digest=policy.policy_digest,seed_aggregates=values,outcome=outcome,robust_seed_count=robust,failed_seed_count=failed,cv_not_performed_seed_count=skipped,serialization_schema=MLCV_CAMPAIGN_CV_AGGREGATE_SCHEMA if policy.serialization_schema==MLCV_CV_POLICY_SCHEMA else "mdstats.mlcv-campaign-cv-aggregate.v1")
