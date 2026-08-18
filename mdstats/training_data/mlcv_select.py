"""MLCV-SELECT1 run-local full checkpoint selection.

Current evidence applies the target gate to absolute target force RMSE and the
replay gate to signed degradation R_full-R0_full. Historical v1 evidence keeps
its original absolute-replay semantics and digest.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .lightweight_rank import LIGHTWEIGHT_RUN_CHAMPION_SCHEMA, LightweightCheckpointScore, LightweightRunChampionRecord
from .mlcv_roles import MlcvDataRole, require_mlcv_topk_selection_role
from .protocol import MaceJobKind

MLCV_RUN_SELECTION_POLICY_SCHEMA = "mdstats.mlcv-run-selection-policy.v2"
MLCV_RUN_SELECTION_POLICY_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-run-selection-policy.v1"})
MLCV_FULL_SELECTION_CANDIDATE_SCHEMA = "mdstats.mlcv-full-selection-candidate.v2"
MLCV_FULL_SELECTION_CANDIDATE_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-full-selection-candidate.v1"})
MLCV_RUN_SELECTION_RECORD_SCHEMA = "mdstats.mlcv-run-selection-record.v2"
MLCV_RUN_SELECTION_RECORD_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-run-selection-record.v1"})


@dataclass(frozen=True, slots=True)
class MlcvRunSelectionPolicy:
    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    replay_degradation_budget_ev_per_angstrom: float | None = None
    target_score_weight: float = 1.0
    replay_score_weight: float = 1.0
    retained_checkpoint_metric_policy_digest: str | None = None
    # Compatibility constructor/legacy-v1 field. Under v2, if supplied while
    # replay_degradation_budget is omitted, it is interpreted as the budget.
    maximum_replay_force_rmse_ev_per_angstrom: float | None = None
    serialization_schema: str = field(default=MLCV_RUN_SELECTION_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_RUN_SELECTION_POLICY_SCHEMA, *MLCV_RUN_SELECTION_POLICY_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV run-selection policy schema.")
        for name in ("maximum_target_force_rmse_ev_per_angstrom", "target_score_weight", "replay_score_weight"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"MLCV-SELECT1 {name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if self.serialization_schema == MLCV_RUN_SELECTION_POLICY_SCHEMA:
            budget = self.replay_degradation_budget_ev_per_angstrom
            if budget is None:
                budget = self.maximum_replay_force_rmse_ev_per_angstrom
            if budget is None:
                budget = self.target_score_weight / self.replay_score_weight * self.maximum_target_force_rmse_ev_per_angstrom
            budget = float(budget)
            if not math.isfinite(budget) or budget <= 0.0:
                raise TrainingDataInputError("MLCV-SELECT1 replay degradation budget must be finite and positive.")
            object.__setattr__(self, "replay_degradation_budget_ev_per_angstrom", budget)
            # Keep the public compatibility attribute numerically useful while
            # never serializing it as an absolute ceiling under v2.
            object.__setattr__(self, "maximum_replay_force_rmse_ev_per_angstrom", budget)
        else:
            value = self.maximum_replay_force_rmse_ev_per_angstrom
            if value is None or not math.isfinite(float(value)) or float(value) <= 0.0:
                raise TrainingDataInputError("Historical MLCV-SELECT1 replay ceiling must be finite and positive.")
            object.__setattr__(self, "maximum_replay_force_rmse_ev_per_angstrom", float(value))
        if self.retained_checkpoint_metric_policy_digest is not None:
            object.__setattr__(self, "retained_checkpoint_metric_policy_digest", validate_digest(self.retained_checkpoint_metric_policy_digest, name="retained_checkpoint_metric_policy_digest"))

    def _payload(self) -> dict[str, Any]:
        if self.serialization_schema in MLCV_RUN_SELECTION_POLICY_LEGACY_SCHEMAS:
            return {
                "schema": self.serialization_schema,
                "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
                "maximum_replay_force_rmse_ev_per_angstrom": self.maximum_replay_force_rmse_ev_per_angstrom,
                "target_score_weight": self.target_score_weight,
                "replay_score_weight": self.replay_score_weight,
                "retained_checkpoint_metric_policy_digest": self.retained_checkpoint_metric_policy_digest,
            }
        return {
            "schema": MLCV_RUN_SELECTION_POLICY_SCHEMA,
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
            "target_score_weight": self.target_score_weight,
            "replay_score_weight": self.replay_score_weight,
            "retained_checkpoint_metric_policy_digest": self.retained_checkpoint_metric_policy_digest,
            "replay_semantics": "foundation_relative_degradation",
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvRunSelectionPolicy":
        schema = payload.get("schema")
        if schema not in {MLCV_RUN_SELECTION_POLICY_SCHEMA, *MLCV_RUN_SELECTION_POLICY_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV run-selection policy schema.")
        result = cls(
            maximum_target_force_rmse_ev_per_angstrom=float(payload["maximum_target_force_rmse_ev_per_angstrom"]),
            replay_degradation_budget_ev_per_angstrom=None if schema in MLCV_RUN_SELECTION_POLICY_LEGACY_SCHEMAS else float(payload["replay_degradation_budget_ev_per_angstrom"]),
            maximum_replay_force_rmse_ev_per_angstrom=None if schema == MLCV_RUN_SELECTION_POLICY_SCHEMA else float(payload["maximum_replay_force_rmse_ev_per_angstrom"]),
            target_score_weight=float(payload["target_score_weight"]), replay_score_weight=float(payload["replay_score_weight"]),
            retained_checkpoint_metric_policy_digest=None if payload.get("retained_checkpoint_metric_policy_digest") is None else str(payload["retained_checkpoint_metric_policy_digest"]),
            serialization_schema=str(schema),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MLCV run-selection policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvFullSelectionCandidateRecord:
    lightweight_rank: int
    checkpoint_sha256: str
    checkpoint_epoch: int
    lightweight_score_ev_per_angstrom: float
    evaluation_record_digest: str
    target_force_rmse_ev_per_angstrom: float
    replay_force_rmse_ev_per_angstrom: float
    full_score_ev_per_angstrom: float
    admissible: bool
    rejection_reasons: tuple[str, ...] = ()
    replay_foundation_force_rmse_ev_per_angstrom: float | None = None
    replay_degradation_force_rmse_ev_per_angstrom: float | None = None
    replay_degradation_budget_ev_per_angstrom: float | None = None
    replay_absolute_ceiling_ev_per_angstrom: float | None = None
    replay_baseline_model_sha256: str | None = None
    serialization_schema: str = field(default=MLCV_FULL_SELECTION_CANDIDATE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_FULL_SELECTION_CANDIDATE_SCHEMA, *MLCV_FULL_SELECTION_CANDIDATE_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV full-selection candidate schema.")
        if int(self.lightweight_rank) <= 0 or int(self.checkpoint_epoch) < 0:
            raise TrainingDataInputError("MLCV-SELECT1 rank/epoch is invalid.")
        object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
        object.__setattr__(self, "evaluation_record_digest", validate_digest(self.evaluation_record_digest, name="evaluation_record_digest"))
        if self.replay_baseline_model_sha256 is not None:
            object.__setattr__(self, "replay_baseline_model_sha256", validate_digest(self.replay_baseline_model_sha256, name="replay_baseline_model_sha256"))
        for name in ("target_force_rmse_ev_per_angstrom", "replay_force_rmse_ev_per_angstrom", "replay_foundation_force_rmse_ev_per_angstrom", "replay_degradation_budget_ev_per_angstrom", "replay_absolute_ceiling_ev_per_angstrom"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"MLCV-SELECT1 {name} must be finite and nonnegative.")
        for name in ("lightweight_score_ev_per_angstrom", "replay_degradation_force_rmse_ev_per_angstrom", "full_score_ev_per_angstrom"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(float(value)):
                raise TrainingDataInputError(f"MLCV-SELECT1 {name} must be finite; signed replay improvement is valid.")
        if self.serialization_schema == MLCV_FULL_SELECTION_CANDIDATE_SCHEMA:
            if any(v is None for v in (self.replay_foundation_force_rmse_ev_per_angstrom, self.replay_degradation_force_rmse_ev_per_angstrom, self.replay_degradation_budget_ev_per_angstrom, self.replay_absolute_ceiling_ev_per_angstrom, self.replay_baseline_model_sha256)):
                raise TrainingDataInputError("Current MLCV-SELECT1 replay evidence requires baseline, degradation, budget, ceiling, and model identity.")
            expected = self.replay_force_rmse_ev_per_angstrom - float(self.replay_foundation_force_rmse_ev_per_angstrom)
            if not math.isclose(expected, float(self.replay_degradation_force_rmse_ev_per_angstrom), rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("MLCV-SELECT1 replay degradation mismatch.")
            expected_ceiling = float(self.replay_foundation_force_rmse_ev_per_angstrom) + float(self.replay_degradation_budget_ev_per_angstrom)
            if not math.isclose(expected_ceiling, float(self.replay_absolute_ceiling_ev_per_angstrom), rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("MLCV-SELECT1 absolute replay ceiling mismatch.")
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        if self.admissible and reasons:
            raise TrainingDataInputError("Admissible MLCV full-selection candidate cannot carry rejection reasons.")
        if not self.admissible and not reasons:
            raise TrainingDataInputError("Rejected MLCV full-selection candidate requires rejection reasons.")
        object.__setattr__(self, "rejection_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        if self.serialization_schema in MLCV_FULL_SELECTION_CANDIDATE_LEGACY_SCHEMAS:
            return {
                "schema": self.serialization_schema,
                "lightweight_rank": int(self.lightweight_rank), "checkpoint_sha256": self.checkpoint_sha256,
                "checkpoint_epoch": int(self.checkpoint_epoch), "lightweight_score_ev_per_angstrom": self.lightweight_score_ev_per_angstrom,
                "evaluation_record_digest": self.evaluation_record_digest,
                "target_force_rmse_ev_per_angstrom": self.target_force_rmse_ev_per_angstrom,
                "replay_force_rmse_ev_per_angstrom": self.replay_force_rmse_ev_per_angstrom,
                "full_score_ev_per_angstrom": self.full_score_ev_per_angstrom,
                "admissible": bool(self.admissible), "rejection_reasons": list(self.rejection_reasons),
            }
        return {
            "schema": MLCV_FULL_SELECTION_CANDIDATE_SCHEMA,
            "lightweight_rank": int(self.lightweight_rank), "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": int(self.checkpoint_epoch), "lightweight_score_ev_per_angstrom": self.lightweight_score_ev_per_angstrom,
            "evaluation_record_digest": self.evaluation_record_digest,
            "target_force_rmse_ev_per_angstrom": self.target_force_rmse_ev_per_angstrom,
            "replay_absolute_force_rmse_ev_per_angstrom": self.replay_force_rmse_ev_per_angstrom,
            "replay_foundation_force_rmse_ev_per_angstrom": self.replay_foundation_force_rmse_ev_per_angstrom,
            "replay_degradation_force_rmse_ev_per_angstrom": self.replay_degradation_force_rmse_ev_per_angstrom,
            "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
            "replay_absolute_ceiling_ev_per_angstrom": self.replay_absolute_ceiling_ev_per_angstrom,
            "replay_baseline_model_sha256": self.replay_baseline_model_sha256,
            "full_score_ev_per_angstrom": self.full_score_ev_per_angstrom,
            "admissible": bool(self.admissible), "rejection_reasons": list(self.rejection_reasons),
            "replay_semantics": "foundation_relative_degradation",
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFullSelectionCandidateRecord":
        schema = payload.get("schema")
        if schema not in {MLCV_FULL_SELECTION_CANDIDATE_SCHEMA, *MLCV_FULL_SELECTION_CANDIDATE_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV full-selection candidate schema.")
        replay = payload.get("replay_absolute_force_rmse_ev_per_angstrom", payload.get("replay_force_rmse_ev_per_angstrom"))
        result = cls(
            lightweight_rank=int(payload["lightweight_rank"]), checkpoint_sha256=str(payload["checkpoint_sha256"]), checkpoint_epoch=int(payload["checkpoint_epoch"]),
            lightweight_score_ev_per_angstrom=float(payload["lightweight_score_ev_per_angstrom"]), evaluation_record_digest=str(payload["evaluation_record_digest"]),
            target_force_rmse_ev_per_angstrom=float(payload["target_force_rmse_ev_per_angstrom"]), replay_force_rmse_ev_per_angstrom=float(replay),
            replay_foundation_force_rmse_ev_per_angstrom=None if payload.get("replay_foundation_force_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_force_rmse_ev_per_angstrom"]),
            replay_degradation_force_rmse_ev_per_angstrom=None if payload.get("replay_degradation_force_rmse_ev_per_angstrom") is None else float(payload["replay_degradation_force_rmse_ev_per_angstrom"]),
            replay_degradation_budget_ev_per_angstrom=None if payload.get("replay_degradation_budget_ev_per_angstrom") is None else float(payload["replay_degradation_budget_ev_per_angstrom"]),
            replay_absolute_ceiling_ev_per_angstrom=None if payload.get("replay_absolute_ceiling_ev_per_angstrom") is None else float(payload["replay_absolute_ceiling_ev_per_angstrom"]),
            replay_baseline_model_sha256=None if payload.get("replay_baseline_model_sha256") is None else str(payload["replay_baseline_model_sha256"]),
            full_score_ev_per_angstrom=float(payload["full_score_ev_per_angstrom"]), admissible=bool(payload["admissible"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())), serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV full-selection candidate digest mismatch.")
        return result


def _retained_safety_reasons(target: Any, retained_policy: Any) -> list[str]:
    reasons: list[str] = []
    if retained_policy.maximum_energy_mae_ev_per_atom is not None and target.energy_mae_ev_per_atom > retained_policy.maximum_energy_mae_ev_per_atom:
        reasons.append("energy_mae_threshold_exceeded")
    if retained_policy.maximum_focus_force_rmse_ev_per_angstrom is not None:
        focus = max((value for _name, value in target.focus_force_rmse_ev_per_angstrom), default=None)
        if focus is None:
            reasons.append("missing_focus_force_rmse")
        elif focus > retained_policy.maximum_focus_force_rmse_ev_per_angstrom:
            reasons.append("focus_force_rmse_threshold_exceeded")
    if retained_policy.maximum_stress_rmse_ev_per_angstrom3 is not None:
        if target.stress_rmse_ev_per_angstrom3 is None:
            reasons.append("missing_stress_rmse")
        elif target.stress_rmse_ev_per_angstrom3 > retained_policy.maximum_stress_rmse_ev_per_angstrom3:
            reasons.append("stress_rmse_threshold_exceeded")
    if retained_policy.maximum_worst_condition_force_rmse_ev_per_angstrom is not None and target.worst_condition_force_rmse_ev_per_angstrom > retained_policy.maximum_worst_condition_force_rmse_ev_per_angstrom:
        reasons.append("worst_condition_force_rmse_threshold_exceeded")
    return reasons


def assess_mlcv_full_selection_candidate(lightweight_rank: int, lightweight: LightweightCheckpointScore, evaluation: Any, policy: MlcvRunSelectionPolicy, retained_policy: Any) -> MlcvFullSelectionCandidateRecord:
    if evaluation.checkpoint_sha256 != lightweight.checkpoint_sha256:
        raise TrainingDataInputError("MLCV-SELECT1 evaluation/checkpoint lineage mismatch.")
    expected_metric_digest = policy.retained_checkpoint_metric_policy_digest
    if expected_metric_digest is not None and retained_policy.policy_digest != expected_metric_digest:
        raise TrainingDataInputError("MLCV-SELECT1 retained checkpoint-metric policy digest mismatch.")
    target = evaluation.target_candidate_metrics
    replay = evaluation.replay_candidate_metrics
    if target is None or replay is None:
        raise TrainingDataInputError("MLCV-SELECT1 requires complete target and TRUE_DFT replay metrics.")
    target_rmse = float(target.force_component_rmse_ev_per_angstrom)
    replay_rmse = float(replay.force_component_rmse_ev_per_angstrom)
    reasons: list[str] = []
    if target_rmse > policy.maximum_target_force_rmse_ev_per_angstrom:
        reasons.append("target_force_rmse_threshold_exceeded")
    reasons.extend(_retained_safety_reasons(target, retained_policy))

    if policy.serialization_schema == MLCV_RUN_SELECTION_POLICY_SCHEMA:
        baseline = evaluation.replay_foundation_metrics
        baseline_sha = evaluation.replay_baseline_model_sha256
        if baseline is None or baseline_sha is None:
            raise TrainingDataInputError("MLCV-SELECT1 v2 requires authenticated foundation metrics on the exact R_full domain.")
        foundation_rmse = float(baseline.force_component_rmse_ev_per_angstrom)
        degradation = replay_rmse - foundation_rmse
        budget = float(policy.replay_degradation_budget_ev_per_angstrom)
        ceiling = foundation_rmse + budget
        if degradation > budget:
            reasons.append("replay_degradation_budget_exceeded")
        replay_term = degradation
        schema = MLCV_FULL_SELECTION_CANDIDATE_SCHEMA
    else:
        foundation_rmse = None
        degradation = None
        budget = None
        ceiling = float(policy.maximum_replay_force_rmse_ev_per_angstrom)
        baseline_sha = None
        if replay_rmse > ceiling:
            reasons.append("replay_force_rmse_threshold_exceeded")
        replay_term = replay_rmse
        schema = "mdstats.mlcv-full-selection-candidate.v1"
    full_score = (policy.target_score_weight * target_rmse + policy.replay_score_weight * replay_term) / (policy.target_score_weight + policy.replay_score_weight)
    return MlcvFullSelectionCandidateRecord(
        lightweight_rank=int(lightweight_rank), checkpoint_sha256=lightweight.checkpoint_sha256, checkpoint_epoch=lightweight.epoch,
        lightweight_score_ev_per_angstrom=lightweight.weighted_score_ev_per_angstrom, evaluation_record_digest=evaluation.content_digest,
        target_force_rmse_ev_per_angstrom=target_rmse, replay_force_rmse_ev_per_angstrom=replay_rmse,
        replay_foundation_force_rmse_ev_per_angstrom=foundation_rmse, replay_degradation_force_rmse_ev_per_angstrom=degradation,
        replay_degradation_budget_ev_per_angstrom=budget, replay_absolute_ceiling_ev_per_angstrom=ceiling,
        replay_baseline_model_sha256=baseline_sha, full_score_ev_per_angstrom=float(full_score),
        admissible=not reasons, rejection_reasons=tuple(reasons), serialization_schema=schema,
    )


@dataclass(frozen=True, slots=True)
class MlcvRunSelectionRecord:
    run_plan_digest: str
    run_id: str
    kind: MaceJobKind
    fold_index: int | None
    seed: int
    lightweight_ranking_record_digest: str
    selection_policy_digest: str
    target_full_role: MlcvDataRole
    target_full_artifact_digest: str
    target_full_sha256: str
    replay_full_role: MlcvDataRole
    replay_full_artifact_digest: str
    replay_full_sha256: str
    evaluated_candidates: tuple[MlcvFullSelectionCandidateRecord, ...]
    outcome: str
    representative_checkpoint_sha256: str | None = None
    representative_checkpoint_epoch: int | None = None
    representative_full_score_ev_per_angstrom: float | None = None
    serialization_schema: str = field(default=MLCV_RUN_SELECTION_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_RUN_SELECTION_RECORD_SCHEMA, *MLCV_RUN_SELECTION_RECORD_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV run-selection record schema.")
        for name in ("run_plan_digest", "lightweight_ranking_record_digest", "selection_policy_digest", "target_full_artifact_digest", "target_full_sha256", "replay_full_artifact_digest", "replay_full_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "kind", MaceJobKind(self.kind)); object.__setattr__(self, "target_full_role", MlcvDataRole(self.target_full_role)); object.__setattr__(self, "replay_full_role", MlcvDataRole(self.replay_full_role))
        require_mlcv_topk_selection_role(self.target_full_role); require_mlcv_topk_selection_role(self.replay_full_role)
        if self.kind is MaceJobKind.CROSS_VALIDATION_FOLD:
            if self.fold_index is None or self.target_full_role is not MlcvDataRole.TARGET_CHECKPOINT_SELECTION:
                raise TrainingDataInputError("Fold SELECT1 records require V_i_full checkpoint-selection authority.")
        elif self.fold_index is not None or self.target_full_role is not MlcvDataRole.TARGET_FINAL_VALIDATION:
            raise TrainingDataInputError("Final SELECT1 records require D_full final-validation authority.")
        if self.replay_full_role is not MlcvDataRole.REPLAY_TRUE_VALIDATION:
            raise TrainingDataInputError("MLCV-SELECT1 replay full evidence must be TRUE_DFT validation authority.")
        candidates = tuple(self.evaluated_candidates)
        if len({v.lightweight_rank for v in candidates}) != len(candidates) or len({v.checkpoint_sha256 for v in candidates}) != len(candidates):
            raise TrainingDataInputError("MLCV-SELECT1 contains duplicate candidate evidence.")
        if tuple(v.lightweight_rank for v in candidates) != tuple(sorted(v.lightweight_rank for v in candidates)):
            raise TrainingDataInputError("MLCV-SELECT1 candidates must be stored in lightweight-rank order.")
        object.__setattr__(self, "evaluated_candidates", candidates)
        if self.outcome not in {"representative_selected", "no_representative"}:
            raise TrainingDataInputError("Unsupported MLCV-SELECT1 run outcome.")
        admissible = self.admissible_candidates
        if self.outcome == "representative_selected":
            if not admissible or self.representative_checkpoint_sha256 is None or self.representative_checkpoint_epoch is None:
                raise TrainingDataInputError("MLCV-SELECT1 representative identity is incomplete.")
            sha = validate_digest(self.representative_checkpoint_sha256, name="representative_checkpoint_sha256"); object.__setattr__(self, "representative_checkpoint_sha256", sha)
            best = admissible[0]
            if sha != best.checkpoint_sha256 or int(self.representative_checkpoint_epoch) != best.checkpoint_epoch:
                raise TrainingDataInputError("MLCV-SELECT1 representative is not the best admissible full-score candidate.")
            score = self.representative_full_score_ev_per_angstrom
            if score is None or not math.isclose(float(score), best.full_score_ev_per_angstrom, rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("MLCV-SELECT1 representative full score mismatch.")
            object.__setattr__(self, "representative_full_score_ev_per_angstrom", float(score))
        elif admissible or any(v is not None for v in (self.representative_checkpoint_sha256, self.representative_checkpoint_epoch, self.representative_full_score_ev_per_angstrom)):
            raise TrainingDataInputError("MLCV-SELECT1 no-representative outcome is inconsistent.")

    @property
    def admissible_candidates(self) -> tuple[MlcvFullSelectionCandidateRecord, ...]:
        current = self.serialization_schema == MLCV_RUN_SELECTION_RECORD_SCHEMA
        return tuple(sorted((v for v in self.evaluated_candidates if v.admissible), key=lambda v: (
            round(v.full_score_ev_per_angstrom, 15), v.target_force_rmse_ev_per_angstrom,
            (v.replay_degradation_force_rmse_ev_per_angstrom if current else v.replay_force_rmse_ev_per_angstrom),
            v.replay_force_rmse_ev_per_angstrom, v.lightweight_rank, v.checkpoint_epoch, v.checkpoint_sha256,
        )))

    @property
    def representative_candidate(self) -> MlcvFullSelectionCandidateRecord | None:
        return None if not self.admissible_candidates else self.admissible_candidates[0]

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema, "run_plan_digest": self.run_plan_digest, "run_id": self.run_id,
            "kind": self.kind.value, "fold_index": self.fold_index, "seed": int(self.seed),
            "lightweight_ranking_record_digest": self.lightweight_ranking_record_digest, "selection_policy_digest": self.selection_policy_digest,
            "target_full_role": self.target_full_role.value, "target_full_artifact_digest": self.target_full_artifact_digest, "target_full_sha256": self.target_full_sha256,
            "replay_full_role": self.replay_full_role.value, "replay_full_artifact_digest": self.replay_full_artifact_digest, "replay_full_sha256": self.replay_full_sha256,
            "evaluated_candidates": [v.to_dict() for v in self.evaluated_candidates], "outcome": self.outcome,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256, "representative_checkpoint_epoch": self.representative_checkpoint_epoch,
            "representative_full_score_ev_per_angstrom": self.representative_full_score_ev_per_angstrom,
        }
        if self.serialization_schema == MLCV_RUN_SELECTION_RECORD_SCHEMA:
            payload["replay_semantics"] = "foundation_relative_degradation"
        return payload

    @property
    def content_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvRunSelectionRecord":
        schema = payload.get("schema")
        if schema not in {MLCV_RUN_SELECTION_RECORD_SCHEMA, *MLCV_RUN_SELECTION_RECORD_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV run-selection record schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]), run_id=str(payload["run_id"]), kind=MaceJobKind(payload["kind"]), fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]), seed=int(payload["seed"]),
            lightweight_ranking_record_digest=str(payload["lightweight_ranking_record_digest"]), selection_policy_digest=str(payload["selection_policy_digest"]),
            target_full_role=MlcvDataRole(payload["target_full_role"]), target_full_artifact_digest=str(payload["target_full_artifact_digest"]), target_full_sha256=str(payload["target_full_sha256"]),
            replay_full_role=MlcvDataRole(payload["replay_full_role"]), replay_full_artifact_digest=str(payload["replay_full_artifact_digest"]), replay_full_sha256=str(payload["replay_full_sha256"]),
            evaluated_candidates=tuple(MlcvFullSelectionCandidateRecord.from_dict(v) for v in payload.get("evaluated_candidates", ())), outcome=str(payload["outcome"]),
            representative_checkpoint_sha256=None if payload.get("representative_checkpoint_sha256") is None else str(payload["representative_checkpoint_sha256"]),
            representative_checkpoint_epoch=None if payload.get("representative_checkpoint_epoch") is None else int(payload["representative_checkpoint_epoch"]),
            representative_full_score_ev_per_angstrom=None if payload.get("representative_full_score_ev_per_angstrom") is None else float(payload["representative_full_score_ev_per_angstrom"]),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV run-selection record digest mismatch.")
        return result


def select_mlcv_run_representative(run: Any, ranking: LightweightRunChampionRecord, evaluations: Sequence[Any], policy: MlcvRunSelectionPolicy, retained_policy: Any, *, target_full_role: MlcvDataRole | str, target_full_artifact_digest: str, target_full_sha256: str, replay_full_artifact_digest: str, replay_full_sha256: str) -> MlcvRunSelectionRecord:
    if policy.serialization_schema == MLCV_RUN_SELECTION_POLICY_SCHEMA and ranking.serialization_schema != LIGHTWEIGHT_RUN_CHAMPION_SCHEMA:
        raise TrainingDataInputError("MLCV-SELECT1 current replay-degradation policy requires current RANK1 evidence; historical rankings are stale and must be regenerated.")
    if ranking.run_plan_digest != run.content_digest:
        raise TrainingDataInputError("MLCV-SELECT1 ranking belongs to a different run.")
    role = MlcvDataRole(target_full_role); require_mlcv_topk_selection_role(role); require_mlcv_topk_selection_role(MlcvDataRole.REPLAY_TRUE_VALIDATION)
    evaluations = tuple(evaluations); by_sha = {v.checkpoint_sha256: v for v in evaluations}
    if len(by_sha) != len(evaluations):
        raise TrainingDataInputError("MLCV-SELECT1 contains duplicate full-evaluation records.")
    expected = {v.checkpoint_sha256 for v in ranking.eligible_candidates}
    if set(by_sha) != expected:
        raise TrainingDataInputError("MLCV-SELECT1 full-evaluation coverage must match the complete retained top-K shortlist.")
    assessed = []
    for rank, lightweight in enumerate(ranking.eligible_candidates, start=1):
        evaluation = by_sha[lightweight.checkpoint_sha256]
        if evaluation.run_plan_digest != run.content_digest:
            raise TrainingDataInputError("MLCV-SELECT1 evaluation belongs to a different run.")
        if evaluation.replay_monitor_artifact_digest != replay_full_artifact_digest or evaluation.replay_monitor_sha256 != replay_full_sha256:
            raise TrainingDataInputError("MLCV-SELECT1 evaluation replay lineage is not the exact R_full authority.")
        assessed.append(assess_mlcv_full_selection_candidate(rank, lightweight, evaluation, policy, retained_policy))
    record_schema = MLCV_RUN_SELECTION_RECORD_SCHEMA if policy.serialization_schema == MLCV_RUN_SELECTION_POLICY_SCHEMA else "mdstats.mlcv-run-selection-record.v1"
    current = record_schema == MLCV_RUN_SELECTION_RECORD_SCHEMA
    admissible = sorted((v for v in assessed if v.admissible), key=lambda v: (
        round(v.full_score_ev_per_angstrom, 15), v.target_force_rmse_ev_per_angstrom,
        (v.replay_degradation_force_rmse_ev_per_angstrom if current else v.replay_force_rmse_ev_per_angstrom),
        v.replay_force_rmse_ev_per_angstrom, v.lightweight_rank, v.checkpoint_epoch, v.checkpoint_sha256,
    ))
    best = admissible[0] if admissible else None
    if best is None:
        return MlcvRunSelectionRecord(
            run_plan_digest=run.content_digest, run_id=run.run_id, kind=run.kind, fold_index=run.fold_index, seed=run.seed,
            lightweight_ranking_record_digest=ranking.content_digest, selection_policy_digest=policy.policy_digest,
            target_full_role=role, target_full_artifact_digest=target_full_artifact_digest, target_full_sha256=target_full_sha256,
            replay_full_role=MlcvDataRole.REPLAY_TRUE_VALIDATION, replay_full_artifact_digest=replay_full_artifact_digest, replay_full_sha256=replay_full_sha256,
            evaluated_candidates=tuple(assessed), outcome="no_representative", serialization_schema=record_schema,
        )
    return MlcvRunSelectionRecord(
        run_plan_digest=run.content_digest, run_id=run.run_id, kind=run.kind, fold_index=run.fold_index, seed=run.seed,
        lightweight_ranking_record_digest=ranking.content_digest, selection_policy_digest=policy.policy_digest,
        target_full_role=role, target_full_artifact_digest=target_full_artifact_digest, target_full_sha256=target_full_sha256,
        replay_full_role=MlcvDataRole.REPLAY_TRUE_VALIDATION, replay_full_artifact_digest=replay_full_artifact_digest, replay_full_sha256=replay_full_sha256,
        evaluated_candidates=tuple(assessed), outcome="representative_selected", representative_checkpoint_sha256=best.checkpoint_sha256,
        representative_checkpoint_epoch=best.checkpoint_epoch, representative_full_score_ev_per_angstrom=best.full_score_ev_per_angstrom,
        serialization_schema=record_schema,
    )
