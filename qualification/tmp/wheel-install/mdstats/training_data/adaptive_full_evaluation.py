"""ADAPT-EVAL1 campaign-wide top-K authoritative full evaluation evidence."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .lightweight_rank import LightweightRunChampionRecord
from .mlcv_roles import MlcvDataRole, require_mlcv_topk_selection_role
from .campaign_execution import CheckpointEvaluationRecord
from .objectives import CheckpointMetricPolicy

ADAPTIVE_FULL_EVALUATION_POLICY_SCHEMA = "mdstats.adaptive-full-evaluation-policy.v1"
CAMPAIGN_FINALIST_QUEUE_SCHEMA = "mdstats.campaign-finalist-queue.v1"
FULL_EVALUATION_CANDIDATE_SCHEMA = "mdstats.full-evaluation-candidate.v1"
ADAPTIVE_FULL_EVALUATION_RECORD_SCHEMA = "mdstats.adaptive-full-evaluation-record.v1"


@dataclass(frozen=True, slots=True)
class AdaptiveFullEvaluationPolicy:
    finalist_count: int = 5
    finalist_rescue_batch_size: int = 5
    target_score_weight: float = 1.0
    replay_score_weight: float = 1.0
    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    maximum_replay_force_rmse_ev_per_angstrom: float = 0.030
    retained_checkpoint_metric_policy_digest: str | None = None

    def __post_init__(self) -> None:
        if int(self.finalist_count) <= 0 or int(self.finalist_rescue_batch_size) <= 0:
            raise TrainingDataInputError("Adaptive full-evaluation finalist batch sizes must be positive.")
        object.__setattr__(self, "finalist_count", int(self.finalist_count))
        object.__setattr__(self, "finalist_rescue_batch_size", int(self.finalist_rescue_batch_size))
        for name in ("target_score_weight", "replay_score_weight"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        for name in (
            "maximum_target_force_rmse_ev_per_angstrom",
            "maximum_replay_force_rmse_ev_per_angstrom",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if self.retained_checkpoint_metric_policy_digest is not None:
            object.__setattr__(
                self,
                "retained_checkpoint_metric_policy_digest",
                validate_digest(
                    self.retained_checkpoint_metric_policy_digest,
                    name="retained_checkpoint_metric_policy_digest",
                ),
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_FULL_EVALUATION_POLICY_SCHEMA,
            "finalist_count": self.finalist_count,
            "finalist_rescue_batch_size": self.finalist_rescue_batch_size,
            "target_score_weight": self.target_score_weight,
            "replay_score_weight": self.replay_score_weight,
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "maximum_replay_force_rmse_ev_per_angstrom": self.maximum_replay_force_rmse_ev_per_angstrom,
            "retained_checkpoint_metric_policy_digest": self.retained_checkpoint_metric_policy_digest,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveFullEvaluationPolicy":
        if payload.get("schema") != ADAPTIVE_FULL_EVALUATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported adaptive-full-evaluation policy schema.")
        result = cls(
            finalist_count=int(payload["finalist_count"]),
            finalist_rescue_batch_size=int(payload["finalist_rescue_batch_size"]),
            target_score_weight=float(payload["target_score_weight"]),
            replay_score_weight=float(payload["replay_score_weight"]),
            maximum_target_force_rmse_ev_per_angstrom=float(payload["maximum_target_force_rmse_ev_per_angstrom"]),
            maximum_replay_force_rmse_ev_per_angstrom=float(payload["maximum_replay_force_rmse_ev_per_angstrom"]),
            retained_checkpoint_metric_policy_digest=(
                None if payload.get("retained_checkpoint_metric_policy_digest") is None
                else str(payload["retained_checkpoint_metric_policy_digest"])
            ),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Adaptive-full-evaluation policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CampaignFinalistCandidate:
    rank: int
    batch_index: int
    run_plan_digest: str
    run_id: str
    champion_record_digest: str
    checkpoint_sha256: str
    checkpoint_epoch: int
    lightweight_score_ev_per_angstrom: float

    def __post_init__(self) -> None:
        if self.rank <= 0 or self.batch_index <= 0 or self.checkpoint_epoch < 0:
            raise TrainingDataInputError("Invalid finalist rank/batch/epoch.")
        for name in ("run_plan_digest", "champion_record_digest", "checkpoint_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not str(self.run_id).strip():
            raise TrainingDataInputError("Finalist run_id must be non-empty.")
        if not math.isfinite(float(self.lightweight_score_ev_per_angstrom)) or float(self.lightweight_score_ev_per_angstrom) < 0.0:
            raise TrainingDataInputError("Finalist lightweight score is invalid.")

    def _payload(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "batch_index": self.batch_index,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "champion_record_digest": self.champion_record_digest,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "lightweight_score_ev_per_angstrom": float(self.lightweight_score_ev_per_angstrom),
        }

    def to_dict(self) -> dict[str, Any]:
        return self._payload()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CampaignFinalistCandidate":
        return cls(
            rank=int(payload["rank"]), batch_index=int(payload["batch_index"]),
            run_plan_digest=str(payload["run_plan_digest"]), run_id=str(payload["run_id"]),
            champion_record_digest=str(payload["champion_record_digest"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]), checkpoint_epoch=int(payload["checkpoint_epoch"]),
            lightweight_score_ev_per_angstrom=float(payload["lightweight_score_ev_per_angstrom"]),
        )


@dataclass(frozen=True, slots=True)
class CampaignFinalistQueueRecord:
    campaign_plan_digest: str
    policy_digest: str
    candidates: tuple[CampaignFinalistCandidate, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "campaign_plan_digest", validate_digest(self.campaign_plan_digest, name="campaign_plan_digest"))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        candidates = tuple(self.candidates)
        if any(item.rank != i for i, item in enumerate(candidates, start=1)):
            raise TrainingDataInputError("Finalist queue ranks must be contiguous from one.")
        if len({item.run_plan_digest for item in candidates}) != len(candidates):
            raise TrainingDataInputError("Finalist queue contains duplicate runs.")
        object.__setattr__(self, "candidates", candidates)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CAMPAIGN_FINALIST_QUEUE_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "policy_digest": self.policy_digest,
            "candidates": [item.to_dict() for item in self.candidates],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CampaignFinalistQueueRecord":
        if payload.get("schema") != CAMPAIGN_FINALIST_QUEUE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported campaign-finalist-queue schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            policy_digest=str(payload["policy_digest"]),
            candidates=tuple(CampaignFinalistCandidate.from_dict(item) for item in payload.get("candidates", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Campaign-finalist-queue digest mismatch.")
        return result


def build_campaign_finalist_queue(
    campaign: Any,
    champion_records: Mapping[str, LightweightRunChampionRecord],
    policy: AdaptiveFullEvaluationPolicy,
    *,
    target_data_role: MlcvDataRole | str | None = None,
) -> CampaignFinalistQueueRecord:
    if target_data_role is not None:
        require_mlcv_topk_selection_role(target_data_role)
    rows: list[tuple[float, float, float, int, str, Any, LightweightRunChampionRecord]] = []
    runs = {run.content_digest: run for run in campaign.runs}
    for run_digest, record in champion_records.items():
        if run_digest not in runs:
            raise TrainingDataInputError("Lightweight champion belongs to a run outside this campaign.")
        if record.run_plan_digest != run_digest:
            raise TrainingDataInputError("Lightweight champion run lineage mismatch.")
        if record.outcome != "champion_selected":
            continue
        assert record.selected_checkpoint_sha256 is not None
        assert record.selected_checkpoint_epoch is not None
        assert record.selected_score_ev_per_angstrom is not None
        selected = record.eligible_candidates[0]
        replay = 0.0 if selected.replay_force_rmse_ev_per_angstrom is None else selected.replay_force_rmse_ev_per_angstrom
        rows.append((
            round(float(record.selected_score_ev_per_angstrom), 15),
            float(selected.target_force_rmse_ev_per_angstrom), float(replay),
            int(record.selected_checkpoint_epoch), record.selected_checkpoint_sha256,
            runs[run_digest], record,
        ))
    rows.sort(key=lambda row: row[:5])
    candidates = []
    for rank, row in enumerate(rows, start=1):
        run, record = row[5], row[6]
        batch_index = 1 if rank <= policy.finalist_count else 2 + (rank - policy.finalist_count - 1) // policy.finalist_rescue_batch_size
        candidates.append(CampaignFinalistCandidate(
            rank=rank, batch_index=batch_index, run_plan_digest=run.content_digest,
            run_id=run.run_id, champion_record_digest=record.content_digest,
            checkpoint_sha256=str(record.selected_checkpoint_sha256),
            checkpoint_epoch=int(record.selected_checkpoint_epoch),
            lightweight_score_ev_per_angstrom=float(record.selected_score_ev_per_angstrom),
        ))
    return CampaignFinalistQueueRecord(
        campaign_plan_digest=campaign.content_digest,
        policy_digest=policy.policy_digest,
        candidates=tuple(candidates),
    )


@dataclass(frozen=True, slots=True)
class FullEvaluationCandidateRecord:
    finalist_rank: int
    finalist_batch_index: int
    run_plan_digest: str
    run_id: str
    checkpoint_sha256: str
    checkpoint_epoch: int
    evaluation_record_digest: str
    target_force_rmse_ev_per_angstrom: float
    replay_force_rmse_ev_per_angstrom: float
    full_score_ev_per_angstrom: float
    admissible: bool
    rejection_reasons: tuple[str, ...] = ()
    replay_foundation_force_rmse_ev_per_angstrom: float | None = None
    replay_absolute_degradation_ev_per_angstrom: float | None = None
    replay_fractional_degradation: float | None = None

    def __post_init__(self) -> None:
        for name in ("run_plan_digest", "checkpoint_sha256", "evaluation_record_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("target_force_rmse_ev_per_angstrom", "replay_force_rmse_ev_per_angstrom", "full_score_ev_per_angstrom"):
            value=float(getattr(self,name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self,name,value)
        reasons=tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        if self.admissible and reasons:
            raise TrainingDataInputError("Admissible full-evaluation candidate cannot carry rejection reasons.")
        if not self.admissible and not reasons:
            raise TrainingDataInputError("Rejected full-evaluation candidate requires rejection reasons.")
        object.__setattr__(self,"rejection_reasons",reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FULL_EVALUATION_CANDIDATE_SCHEMA,
            "finalist_rank": self.finalist_rank,
            "finalist_batch_index": self.finalist_batch_index,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "evaluation_record_digest": self.evaluation_record_digest,
            "target_force_rmse_ev_per_angstrom": self.target_force_rmse_ev_per_angstrom,
            "replay_force_rmse_ev_per_angstrom": self.replay_force_rmse_ev_per_angstrom,
            "full_score_ev_per_angstrom": self.full_score_ev_per_angstrom,
            "admissible": bool(self.admissible),
            "rejection_reasons": list(self.rejection_reasons),
            "replay_foundation_force_rmse_ev_per_angstrom": self.replay_foundation_force_rmse_ev_per_angstrom,
            "replay_absolute_degradation_ev_per_angstrom": self.replay_absolute_degradation_ev_per_angstrom,
            "replay_fractional_degradation": self.replay_fractional_degradation,
        }
    @property
    def content_digest(self) -> str: return digest(self._payload())
    def to_dict(self) -> dict[str, Any]: return {**self._payload(), "content_digest": self.content_digest}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"FullEvaluationCandidateRecord":
        if payload.get("schema")!=FULL_EVALUATION_CANDIDATE_SCHEMA: raise TrainingDataSerializationError("Unsupported full-evaluation-candidate schema.")
        result=cls(
            finalist_rank=int(payload["finalist_rank"]), finalist_batch_index=int(payload["finalist_batch_index"]),
            run_plan_digest=str(payload["run_plan_digest"]), run_id=str(payload["run_id"]), checkpoint_sha256=str(payload["checkpoint_sha256"]), checkpoint_epoch=int(payload["checkpoint_epoch"]),
            evaluation_record_digest=str(payload["evaluation_record_digest"]), target_force_rmse_ev_per_angstrom=float(payload["target_force_rmse_ev_per_angstrom"]), replay_force_rmse_ev_per_angstrom=float(payload["replay_force_rmse_ev_per_angstrom"]), full_score_ev_per_angstrom=float(payload["full_score_ev_per_angstrom"]), admissible=bool(payload["admissible"]), rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons",())),
            replay_foundation_force_rmse_ev_per_angstrom=None if payload.get("replay_foundation_force_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_force_rmse_ev_per_angstrom"]), replay_absolute_degradation_ev_per_angstrom=None if payload.get("replay_absolute_degradation_ev_per_angstrom") is None else float(payload["replay_absolute_degradation_ev_per_angstrom"]), replay_fractional_degradation=None if payload.get("replay_fractional_degradation") is None else float(payload["replay_fractional_degradation"]),
        )
        if payload.get("content_digest") not in (None,result.content_digest): raise TrainingDataSerializationError("Full-evaluation-candidate digest mismatch.")
        return result


def assess_full_evaluation_candidate(
    finalist: CampaignFinalistCandidate,
    evaluation: CheckpointEvaluationRecord,
    policy: AdaptiveFullEvaluationPolicy,
    retained_policy: CheckpointMetricPolicy,
) -> FullEvaluationCandidateRecord:
    if evaluation.run_plan_digest != finalist.run_plan_digest or evaluation.checkpoint_sha256 != finalist.checkpoint_sha256:
        raise TrainingDataInputError("Full evaluation candidate lineage mismatch.")
    expected_metric_digest = policy.retained_checkpoint_metric_policy_digest
    if expected_metric_digest is not None and retained_policy.policy_digest != expected_metric_digest:
        raise TrainingDataInputError(
            "ADAPT-EVAL1 retained checkpoint-metric policy differs from the policy frozen into the full-evaluation plan."
        )
    target = evaluation.target_candidate_metrics
    replay = evaluation.replay_candidate_metrics
    if target is None or replay is None:
        raise TrainingDataInputError("ADAPT-EVAL1 requires complete target and true-replay candidate metrics.")
    t=float(target.force_component_rmse_ev_per_angstrom); r=float(replay.force_component_rmse_ev_per_angstrom)
    reasons=[]
    if t > policy.maximum_target_force_rmse_ev_per_angstrom: reasons.append("target_force_rmse_threshold_exceeded")
    if r > policy.maximum_replay_force_rmse_ev_per_angstrom: reasons.append("replay_force_rmse_threshold_exceeded")
    # Retain all legacy non-replay, non-primary hard safety gates.
    if retained_policy.maximum_energy_mae_ev_per_atom is not None and target.energy_mae_ev_per_atom > retained_policy.maximum_energy_mae_ev_per_atom: reasons.append("energy_mae_threshold_exceeded")
    if retained_policy.maximum_focus_force_rmse_ev_per_angstrom is not None:
        focus=max((v for _,v in target.focus_force_rmse_ev_per_angstrom), default=None)
        if focus is None: reasons.append("missing_focus_force_rmse")
        elif focus > retained_policy.maximum_focus_force_rmse_ev_per_angstrom: reasons.append("focus_force_rmse_threshold_exceeded")
    if retained_policy.maximum_stress_rmse_ev_per_angstrom3 is not None:
        if target.stress_rmse_ev_per_angstrom3 is None: reasons.append("missing_stress_rmse")
        elif target.stress_rmse_ev_per_angstrom3 > retained_policy.maximum_stress_rmse_ev_per_angstrom3: reasons.append("stress_rmse_threshold_exceeded")
    if retained_policy.maximum_worst_condition_force_rmse_ev_per_angstrom is not None and target.worst_condition_force_rmse_ev_per_angstrom > retained_policy.maximum_worst_condition_force_rmse_ev_per_angstrom: reasons.append("worst_condition_force_rmse_threshold_exceeded")
    score=(policy.target_score_weight*t+policy.replay_score_weight*r)/(policy.target_score_weight+policy.replay_score_weight)
    baseline=None if evaluation.replay_foundation_metrics is None else float(evaluation.replay_foundation_metrics.force_component_rmse_ev_per_angstrom)
    absolute=None if baseline is None else r-baseline
    fraction=None if baseline is None or baseline <= 0 else absolute/baseline
    return FullEvaluationCandidateRecord(
        finalist_rank=finalist.rank, finalist_batch_index=finalist.batch_index,
        run_plan_digest=finalist.run_plan_digest, run_id=finalist.run_id,
        checkpoint_sha256=finalist.checkpoint_sha256, checkpoint_epoch=finalist.checkpoint_epoch,
        evaluation_record_digest=evaluation.content_digest,
        target_force_rmse_ev_per_angstrom=t, replay_force_rmse_ev_per_angstrom=r,
        full_score_ev_per_angstrom=float(score), admissible=not reasons,
        rejection_reasons=tuple(reasons), replay_foundation_force_rmse_ev_per_angstrom=baseline,
        replay_absolute_degradation_ev_per_angstrom=absolute,
        replay_fractional_degradation=fraction,
    )


@dataclass(frozen=True, slots=True)
class AdaptiveFullEvaluationRecord:
    campaign_plan_digest: str
    policy_digest: str
    finalist_queue_digest: str
    full_target_artifact_digest: str
    full_replay_artifact_digest: str
    evaluated_candidates: tuple[FullEvaluationCandidateRecord, ...]
    completed_batch_count: int
    outcome: str

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest","policy_digest","finalist_queue_digest","full_target_artifact_digest","full_replay_artifact_digest"):
            object.__setattr__(self,name,validate_digest(getattr(self,name),name=name))
        allowed={"admissible_candidates_available","no_admissible_candidate"}
        if self.outcome not in allowed: raise TrainingDataInputError("Unsupported adaptive full-evaluation outcome.")
        if int(self.completed_batch_count) < 0:
            raise TrainingDataInputError("Adaptive full-evaluation completed_batch_count must be nonnegative.")
        object.__setattr__(self,"completed_batch_count",int(self.completed_batch_count))
        candidates = tuple(self.evaluated_candidates)
        if len({(item.run_plan_digest, item.checkpoint_sha256) for item in candidates}) != len(candidates):
            raise TrainingDataInputError("Adaptive full evaluation contains duplicate candidate identities.")
        has_admissible = any(item.admissible for item in candidates)
        if self.outcome == "admissible_candidates_available" and not has_admissible:
            raise TrainingDataInputError("Adaptive full-evaluation outcome claims an admissible model but none is recorded.")
        if self.outcome == "no_admissible_candidate" and has_admissible:
            raise TrainingDataInputError("Adaptive full-evaluation outcome rejects the pool despite an admissible model.")
        object.__setattr__(self,"evaluated_candidates",candidates)
    @property
    def admissible_candidates(self)->tuple[FullEvaluationCandidateRecord,...]:
        return tuple(sorted((x for x in self.evaluated_candidates if x.admissible), key=lambda x:(round(x.full_score_ev_per_angstrom,15),x.target_force_rmse_ev_per_angstrom,x.replay_force_rmse_ev_per_angstrom,x.finalist_rank,x.checkpoint_sha256)))
    def _payload(self)->dict[str,Any]:
        return {"schema":ADAPTIVE_FULL_EVALUATION_RECORD_SCHEMA,"campaign_plan_digest":self.campaign_plan_digest,"policy_digest":self.policy_digest,"finalist_queue_digest":self.finalist_queue_digest,"full_target_artifact_digest":self.full_target_artifact_digest,"full_replay_artifact_digest":self.full_replay_artifact_digest,"evaluated_candidates":[x.to_dict() for x in self.evaluated_candidates],"completed_batch_count":self.completed_batch_count,"outcome":self.outcome}
    @property
    def content_digest(self)->str:return digest(self._payload())
    def to_dict(self)->dict[str,Any]:return {**self._payload(),"content_digest":self.content_digest}
    @classmethod
    def from_dict(cls,payload:Mapping[str,Any])->"AdaptiveFullEvaluationRecord":
        if payload.get("schema")!=ADAPTIVE_FULL_EVALUATION_RECORD_SCHEMA: raise TrainingDataSerializationError("Unsupported adaptive-full-evaluation-record schema.")
        result=cls(campaign_plan_digest=str(payload["campaign_plan_digest"]),policy_digest=str(payload["policy_digest"]),finalist_queue_digest=str(payload["finalist_queue_digest"]),full_target_artifact_digest=str(payload["full_target_artifact_digest"]),full_replay_artifact_digest=str(payload["full_replay_artifact_digest"]),evaluated_candidates=tuple(FullEvaluationCandidateRecord.from_dict(x) for x in payload.get("evaluated_candidates",())),completed_batch_count=int(payload["completed_batch_count"]),outcome=str(payload["outcome"]))
        if payload.get("content_digest") not in (None,result.content_digest):raise TrainingDataSerializationError("Adaptive-full-evaluation-record digest mismatch.")
        return result
