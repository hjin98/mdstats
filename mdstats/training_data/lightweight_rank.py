"""MLCV-RANK1 zero-inference ranking of adaptive-training checkpoints.

Current evidence ranks target absolute error together with signed replay
degradation relative to the matched R0_light foundation baseline. Historical
schemas remain readable without semantic reinterpretation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .adaptive_stop import (
    ADAPTIVE_STOP_POLICY_SCHEMA,
    ADAPTIVE_STOP_STATE_SCHEMA,
    AdaptiveTrainingStopState,
    AdaptiveTrainingStopPolicy,
)
from .mlcv_roles import MlcvDataRole, require_mlcv_checkpoint_ranking_role

LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA = "mdstats.lightweight-checkpoint-score.v2"
LIGHTWEIGHT_CHECKPOINT_SCORE_LEGACY_SCHEMAS = frozenset({"mdstats.lightweight-checkpoint-score.v1"})
LIGHTWEIGHT_RUN_CHAMPION_SCHEMA = "mdstats.lightweight-run-champion.v3"
LIGHTWEIGHT_RUN_CHAMPION_LEGACY_SCHEMAS = frozenset({
    "mdstats.lightweight-run-champion.v1",
    "mdstats.lightweight-run-champion.v2",
})
DEFAULT_LIGHTWEIGHT_TOPK_CANDIDATES = 5


@dataclass(frozen=True, slots=True)
class LightweightCheckpointScore:
    epoch: int
    checkpoint_sha256: str
    target_force_rmse_ev_per_angstrom: float
    replay_force_rmse_ev_per_angstrom: float | None
    weighted_score_ev_per_angstrom: float
    replay_foundation_force_rmse_ev_per_angstrom: float | None = None
    replay_degradation_force_rmse_ev_per_angstrom: float | None = None
    serialization_schema: str = field(default=LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA, *LIGHTWEIGHT_CHECKPOINT_SCORE_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported lightweight-checkpoint-score schema.")
        if int(self.epoch) < 0:
            raise TrainingDataInputError("Lightweight-ranking epoch must be nonnegative.")
        object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
        for name in ("target_force_rmse_ev_per_angstrom", "replay_force_rmse_ev_per_angstrom", "replay_foundation_force_rmse_ev_per_angstrom"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"Lightweight-ranking {name} must be finite and nonnegative.")
        for name in ("replay_degradation_force_rmse_ev_per_angstrom", "weighted_score_ev_per_angstrom"):
            value = getattr(self, name)
            if value is not None and not math.isfinite(float(value)):
                raise TrainingDataInputError(f"Lightweight-ranking {name} must be finite; signed replay improvement is valid.")
        if self.serialization_schema == LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA and self.replay_force_rmse_ev_per_angstrom is not None:
            if self.replay_foundation_force_rmse_ev_per_angstrom is None or self.replay_degradation_force_rmse_ev_per_angstrom is None:
                raise TrainingDataInputError("Current MLCV-RANK1 replay scores require absolute, foundation, and degradation metrics.")
            expected = float(self.replay_force_rmse_ev_per_angstrom) - float(self.replay_foundation_force_rmse_ev_per_angstrom)
            if not math.isclose(expected, float(self.replay_degradation_force_rmse_ev_per_angstrom), rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("MLCV-RANK1 replay degradation does not equal absolute-minus-foundation RMSE.")

    def _payload(self) -> dict[str, Any]:
        if self.serialization_schema in LIGHTWEIGHT_CHECKPOINT_SCORE_LEGACY_SCHEMAS:
            return {
                "schema": self.serialization_schema,
                "epoch": int(self.epoch),
                "checkpoint_sha256": self.checkpoint_sha256,
                "target_force_rmse_ev_per_angstrom": float(self.target_force_rmse_ev_per_angstrom),
                "replay_force_rmse_ev_per_angstrom": None if self.replay_force_rmse_ev_per_angstrom is None else float(self.replay_force_rmse_ev_per_angstrom),
                "weighted_score_ev_per_angstrom": float(self.weighted_score_ev_per_angstrom),
            }
        return {
            "schema": LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA,
            "epoch": int(self.epoch),
            "checkpoint_sha256": self.checkpoint_sha256,
            "target_force_rmse_ev_per_angstrom": float(self.target_force_rmse_ev_per_angstrom),
            "replay_absolute_force_rmse_ev_per_angstrom": None if self.replay_force_rmse_ev_per_angstrom is None else float(self.replay_force_rmse_ev_per_angstrom),
            "replay_foundation_force_rmse_ev_per_angstrom": None if self.replay_foundation_force_rmse_ev_per_angstrom is None else float(self.replay_foundation_force_rmse_ev_per_angstrom),
            "replay_degradation_force_rmse_ev_per_angstrom": None if self.replay_degradation_force_rmse_ev_per_angstrom is None else float(self.replay_degradation_force_rmse_ev_per_angstrom),
            "weighted_score_ev_per_angstrom": float(self.weighted_score_ev_per_angstrom),
            "replay_semantics": "foundation_relative_degradation",
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LightweightCheckpointScore":
        schema = payload.get("schema")
        if schema not in {LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA, *LIGHTWEIGHT_CHECKPOINT_SCORE_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported lightweight-checkpoint-score schema.")
        replay = payload.get("replay_absolute_force_rmse_ev_per_angstrom", payload.get("replay_force_rmse_ev_per_angstrom"))
        result = cls(
            epoch=int(payload["epoch"]), checkpoint_sha256=str(payload["checkpoint_sha256"]),
            target_force_rmse_ev_per_angstrom=float(payload["target_force_rmse_ev_per_angstrom"]),
            replay_force_rmse_ev_per_angstrom=None if replay is None else float(replay),
            replay_foundation_force_rmse_ev_per_angstrom=None if payload.get("replay_foundation_force_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_force_rmse_ev_per_angstrom"]),
            replay_degradation_force_rmse_ev_per_angstrom=None if payload.get("replay_degradation_force_rmse_ev_per_angstrom") is None else float(payload["replay_degradation_force_rmse_ev_per_angstrom"]),
            weighted_score_ev_per_angstrom=float(payload["weighted_score_ev_per_angstrom"]),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Lightweight-checkpoint-score digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LightweightRunChampionRecord:
    run_plan_digest: str
    training_protocol_digest: str
    adaptive_stop_policy_digest: str
    adaptive_stop_state_digest: str
    checkpoint_catalog_digest: str
    online_monitor_policy_digest: str
    target_online_monitor_record_digest: str
    replay_online_monitor_record_digest: str
    outcome: str
    eligible_candidates: tuple[LightweightCheckpointScore, ...] = ()
    selected_checkpoint_sha256: str | None = None
    selected_checkpoint_epoch: int | None = None
    selected_score_ev_per_angstrom: float | None = None
    ranking_order: tuple[str, ...] = (
        "weighted_score",
        "target_force_rmse",
        "replay_degradation_force_rmse",
        "replay_absolute_force_rmse",
        "epoch",
        "checkpoint_sha256",
    )
    rankable_checkpoint_count: int | None = None
    candidate_limit: int | None = None
    serialization_schema: str = LIGHTWEIGHT_RUN_CHAMPION_SCHEMA

    def __post_init__(self) -> None:
        supported = {LIGHTWEIGHT_RUN_CHAMPION_SCHEMA, *LIGHTWEIGHT_RUN_CHAMPION_LEGACY_SCHEMAS}
        if self.serialization_schema not in supported:
            raise TrainingDataInputError("Unsupported lightweight-run ranking schema.")
        for name in (
            "run_plan_digest", "training_protocol_digest", "adaptive_stop_policy_digest",
            "adaptive_stop_state_digest", "checkpoint_catalog_digest", "online_monitor_policy_digest",
            "target_online_monitor_record_digest", "replay_online_monitor_record_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.outcome not in {"champion_selected", "no_lightweight_admissible_checkpoint"}:
            raise TrainingDataInputError("Unsupported lightweight-ranking outcome.")
        candidates = tuple(self.eligible_candidates)
        if len({item.epoch for item in candidates}) != len(candidates) or len({item.checkpoint_sha256 for item in candidates}) != len(candidates):
            raise TrainingDataInputError("Lightweight ranking contains duplicate checkpoint evidence.")
        object.__setattr__(self, "eligible_candidates", candidates)
        object.__setattr__(self, "ranking_order", tuple(str(v) for v in self.ranking_order))
        if self.serialization_schema in {LIGHTWEIGHT_RUN_CHAMPION_SCHEMA, "mdstats.lightweight-run-champion.v2"}:
            limit = DEFAULT_LIGHTWEIGHT_TOPK_CANDIDATES if self.candidate_limit is None else int(self.candidate_limit)
            if limit <= 0:
                raise TrainingDataInputError("Lightweight top-K candidate_limit must be positive.")
            count = len(candidates) if self.rankable_checkpoint_count is None else int(self.rankable_checkpoint_count)
            if count < len(candidates) or len(candidates) > limit:
                raise TrainingDataInputError("Invalid lightweight top-K coverage.")
            object.__setattr__(self, "candidate_limit", limit)
            object.__setattr__(self, "rankable_checkpoint_count", count)
        else:
            object.__setattr__(self, "candidate_limit", None)
            object.__setattr__(self, "rankable_checkpoint_count", None)
        if self.outcome == "champion_selected":
            if not candidates or self.selected_checkpoint_sha256 is None or self.selected_checkpoint_epoch is None:
                raise TrainingDataInputError("Champion-selected ranking lacks checkpoint evidence.")
            sha = validate_digest(self.selected_checkpoint_sha256, name="selected_checkpoint_sha256")
            object.__setattr__(self, "selected_checkpoint_sha256", sha)
            selected = [v for v in candidates if v.checkpoint_sha256 == sha and v.epoch == int(self.selected_checkpoint_epoch)]
            if len(selected) != 1 or candidates[0] != selected[0]:
                raise TrainingDataInputError("Selected lightweight champion is not rank one.")
            score = self.selected_score_ev_per_angstrom
            if score is None or not math.isfinite(float(score)) or not math.isclose(float(score), selected[0].weighted_score_ev_per_angstrom, rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("Selected lightweight champion score mismatch.")
        else:
            if candidates or any(v is not None for v in (self.selected_checkpoint_sha256, self.selected_checkpoint_epoch, self.selected_score_ev_per_angstrom)):
                raise TrainingDataInputError("No-champion ranking cannot carry candidate/selection fields.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "training_protocol_digest": self.training_protocol_digest,
            "adaptive_stop_policy_digest": self.adaptive_stop_policy_digest,
            "adaptive_stop_state_digest": self.adaptive_stop_state_digest,
            "checkpoint_catalog_digest": self.checkpoint_catalog_digest,
            "online_monitor_policy_digest": self.online_monitor_policy_digest,
            "target_online_monitor_record_digest": self.target_online_monitor_record_digest,
            "replay_online_monitor_record_digest": self.replay_online_monitor_record_digest,
            "outcome": self.outcome,
            "eligible_candidates": [item.to_dict() for item in self.eligible_candidates],
            "selected_checkpoint_sha256": self.selected_checkpoint_sha256,
            "selected_checkpoint_epoch": self.selected_checkpoint_epoch,
            "selected_score_ev_per_angstrom": self.selected_score_ev_per_angstrom,
            "ranking_order": list(self.ranking_order),
        }
        if self.serialization_schema in {LIGHTWEIGHT_RUN_CHAMPION_SCHEMA, "mdstats.lightweight-run-champion.v2"}:
            payload.update({
                "rankable_checkpoint_count": self.rankable_checkpoint_count,
                "candidate_limit": self.candidate_limit,
            })
        if self.serialization_schema == LIGHTWEIGHT_RUN_CHAMPION_SCHEMA:
            payload["replay_semantics"] = "foundation_relative_degradation"
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LightweightRunChampionRecord":
        schema = payload.get("schema")
        if schema not in {LIGHTWEIGHT_RUN_CHAMPION_SCHEMA, *LIGHTWEIGHT_RUN_CHAMPION_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported lightweight-run-champion schema.")
        default_order = (
            "weighted_score", "target_force_rmse", "replay_force_rmse", "epoch", "checkpoint_sha256"
        ) if schema in LIGHTWEIGHT_RUN_CHAMPION_LEGACY_SCHEMAS else (
            "weighted_score", "target_force_rmse", "replay_degradation_force_rmse", "replay_absolute_force_rmse", "epoch", "checkpoint_sha256"
        )
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            training_protocol_digest=str(payload["training_protocol_digest"]),
            adaptive_stop_policy_digest=str(payload["adaptive_stop_policy_digest"]),
            adaptive_stop_state_digest=str(payload["adaptive_stop_state_digest"]),
            checkpoint_catalog_digest=str(payload["checkpoint_catalog_digest"]),
            online_monitor_policy_digest=str(payload["online_monitor_policy_digest"]),
            target_online_monitor_record_digest=str(payload["target_online_monitor_record_digest"]),
            replay_online_monitor_record_digest=str(payload["replay_online_monitor_record_digest"]),
            outcome=str(payload["outcome"]),
            eligible_candidates=tuple(LightweightCheckpointScore.from_dict(item) for item in payload.get("eligible_candidates", ())),
            selected_checkpoint_sha256=None if payload.get("selected_checkpoint_sha256") is None else str(payload["selected_checkpoint_sha256"]),
            selected_checkpoint_epoch=None if payload.get("selected_checkpoint_epoch") is None else int(payload["selected_checkpoint_epoch"]),
            selected_score_ev_per_angstrom=None if payload.get("selected_score_ev_per_angstrom") is None else float(payload["selected_score_ev_per_angstrom"]),
            ranking_order=tuple(str(v) for v in payload.get("ranking_order", default_order)),
            rankable_checkpoint_count=None if schema == "mdstats.lightweight-run-champion.v1" else int(payload.get("rankable_checkpoint_count", len(payload.get("eligible_candidates", ())))),
            candidate_limit=None if schema == "mdstats.lightweight-run-champion.v1" else int(payload.get("candidate_limit", DEFAULT_LIGHTWEIGHT_TOPK_CANDIDATES)),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Lightweight-run-champion digest mismatch.")
        return result


def _weighted_score(policy: AdaptiveTrainingStopPolicy, *, target_rmse: float, replay_rmse: float | None, replay_degradation_rmse: float | None = None) -> float:
    target_weight = float(policy.target_score_weight)
    if not policy.replay_enabled:
        return float(target_rmse)
    replay_weight = float(policy.replay_score_weight)
    if policy.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA:
        if replay_degradation_rmse is None:
            raise TrainingDataInputError("Current MLCV-RANK1 requires signed R_light replay degradation.")
        replay_term = float(replay_degradation_rmse)
    else:
        if replay_rmse is None:
            raise TrainingDataInputError("Replay-enabled historical lightweight ranking requires replay RMSE.")
        replay_term = float(replay_rmse)
    return (target_weight * float(target_rmse) + replay_weight * replay_term) / (target_weight + replay_weight)


def _ranking_key(item: LightweightCheckpointScore, *, replay_enabled: bool) -> tuple[float, float, float, float, int, str]:
    degradation = 0.0 if not replay_enabled else (float("inf") if item.replay_degradation_force_rmse_ev_per_angstrom is None else float(item.replay_degradation_force_rmse_ev_per_angstrom))
    absolute = 0.0 if not replay_enabled else (float("inf") if item.replay_force_rmse_ev_per_angstrom is None else float(item.replay_force_rmse_ev_per_angstrom))
    return (
        round(float(item.weighted_score_ev_per_angstrom), 15),
        float(item.target_force_rmse_ev_per_angstrom),
        degradation,
        absolute,
        int(item.epoch),
        item.checkpoint_sha256,
    )


def rank_lightweight_run_champion(run_plan: Any, protocol: Any, stop_state: AdaptiveTrainingStopState, checkpoint_catalog: Any, *, target_data_role: MlcvDataRole | str | None = None, candidate_limit: int = DEFAULT_LIGHTWEIGHT_TOPK_CANDIDATES) -> LightweightRunChampionRecord:
    """Retain deterministic top-K checkpoints without new inference."""
    if target_data_role is not None:
        require_mlcv_checkpoint_ranking_role(target_data_role)
    if int(candidate_limit) <= 0:
        raise TrainingDataInputError("MLCV-RANK1 candidate_limit must be positive.")
    run_digest = str(run_plan.content_digest)
    if checkpoint_catalog.run_plan_digest != run_digest:
        raise TrainingDataInputError("Lightweight ranking checkpoint catalog belongs to another run.")
    policy = getattr(protocol, "adaptive_stop_policy", None)
    if policy is None or stop_state.policy_digest != policy.policy_digest:
        raise TrainingDataInputError("MLCV-RANK1 requires matching adaptive-stop policy/state evidence.")
    if stop_state.stop_reason is None or stop_state.stop_epoch is None:
        raise TrainingDataInputError("MLCV-RANK1 requires terminal adaptive-stop evidence.")
    if policy.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA and stop_state.serialization_schema != ADAPTIVE_STOP_STATE_SCHEMA:
        raise TrainingDataInputError("MLCV-RANK1 current replay-degradation policy cannot reinterpret historical stop evidence; regenerate STOP1 evidence.")
    monitor_fields = {
        "online_monitor_policy_digest": getattr(protocol, "online_monitor_policy_digest", None),
        "target_online_monitor_record_digest": getattr(protocol, "target_online_monitor_record_digest", None),
        "replay_online_monitor_record_digest": getattr(protocol, "replay_online_monitor_record_digest", None),
    }
    if any(value is None for value in monitor_fields.values()):
        raise TrainingDataInputError("MLCV-RANK1 requires complete lightweight/common-monitor lineage.")
    by_epoch = {item.epoch: item for item in checkpoint_catalog.checkpoints}
    state_epochs = {item.epoch for item in stop_state.epochs}
    if state_epochs != set(by_epoch):
        raise TrainingDataInputError("MLCV-RANK1 requires exact epoch coverage between stop history and frozen checkpoint catalog.")

    scored: list[LightweightCheckpointScore] = []
    for metric in stop_state.epochs:
        recomputed_eligible = policy.candidate_eligible(metric.target_force_rmse_ev_per_angstrom, metric.replay_force_rmse_ev_per_angstrom)
        if recomputed_eligible != metric.candidate_eligible:
            raise TrainingDataInputError(f"Adaptive-stop candidate eligibility changed for epoch {metric.epoch}.")
        if not recomputed_eligible:
            continue
        checkpoint = by_epoch[metric.epoch]
        current = policy.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA
        scored.append(LightweightCheckpointScore(
            epoch=metric.epoch,
            checkpoint_sha256=checkpoint.sha256,
            target_force_rmse_ev_per_angstrom=metric.target_force_rmse_ev_per_angstrom,
            replay_force_rmse_ev_per_angstrom=metric.replay_force_rmse_ev_per_angstrom,
            replay_foundation_force_rmse_ev_per_angstrom=metric.replay_foundation_force_rmse_ev_per_angstrom if current else None,
            replay_degradation_force_rmse_ev_per_angstrom=metric.replay_degradation_force_rmse_ev_per_angstrom if current else None,
            weighted_score_ev_per_angstrom=_weighted_score(
                policy,
                target_rmse=metric.target_force_rmse_ev_per_angstrom,
                replay_rmse=metric.replay_force_rmse_ev_per_angstrom,
                replay_degradation_rmse=metric.replay_degradation_force_rmse_ev_per_angstrom,
            ),
            serialization_schema=LIGHTWEIGHT_CHECKPOINT_SCORE_SCHEMA if current else "mdstats.lightweight-checkpoint-score.v1",
        ))
    if policy.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA:
        key = lambda item: _ranking_key(item, replay_enabled=policy.replay_enabled)
        record_schema = LIGHTWEIGHT_RUN_CHAMPION_SCHEMA
        ranking_order = ("weighted_score", "target_force_rmse", "replay_degradation_force_rmse", "replay_absolute_force_rmse", "epoch", "checkpoint_sha256")
    else:
        key = lambda item: (
            round(float(item.weighted_score_ev_per_angstrom), 15),
            float(item.target_force_rmse_ev_per_angstrom),
            float("inf") if item.replay_force_rmse_ev_per_angstrom is None else float(item.replay_force_rmse_ev_per_angstrom),
            int(item.epoch), item.checkpoint_sha256,
        )
        record_schema = "mdstats.lightweight-run-champion.v2"
        ranking_order = ("weighted_score", "target_force_rmse", "replay_force_rmse", "epoch", "checkpoint_sha256")
    all_ranked = tuple(sorted(scored, key=key))
    ranked = all_ranked[: int(candidate_limit)]
    common = dict(
        run_plan_digest=run_digest,
        training_protocol_digest=protocol.content_digest,
        adaptive_stop_policy_digest=policy.policy_digest,
        adaptive_stop_state_digest=stop_state.content_digest,
        checkpoint_catalog_digest=checkpoint_catalog.content_digest,
        online_monitor_policy_digest=str(monitor_fields["online_monitor_policy_digest"]),
        target_online_monitor_record_digest=str(monitor_fields["target_online_monitor_record_digest"]),
        replay_online_monitor_record_digest=str(monitor_fields["replay_online_monitor_record_digest"]),
        ranking_order=ranking_order,
        serialization_schema=record_schema,
    )
    if not ranked:
        if stop_state.run_outcome != "no_lightweight_admissible_checkpoint":
            raise TrainingDataInputError("Adaptive-stop evidence reported rankable checkpoints, but MLCV-RANK1 found none.")
        return LightweightRunChampionRecord(**common, outcome="no_lightweight_admissible_checkpoint", rankable_checkpoint_count=0, candidate_limit=int(candidate_limit))
    if stop_state.run_outcome != "admissible_checkpoint_available":
        raise TrainingDataInputError("Adaptive-stop evidence reported no rankable checkpoint, but MLCV-RANK1 found candidates.")
    selected = ranked[0]
    return LightweightRunChampionRecord(
        **common, outcome="champion_selected", eligible_candidates=ranked,
        selected_checkpoint_sha256=selected.checkpoint_sha256,
        selected_checkpoint_epoch=selected.epoch,
        selected_score_ev_per_angstrom=selected.weighted_score_ev_per_angstrom,
        rankable_checkpoint_count=len(all_ranked), candidate_limit=int(candidate_limit),
    )


def rank_lightweight_run_topk(*args: Any, **kwargs: Any) -> LightweightRunChampionRecord:
    return rank_lightweight_run_champion(*args, **kwargs)
