"""MLCV-FINAL1 final-seed comparison and committee authority.

Only full-development representatives created by MLCV-SELECT1 may enter this
layer.  Conventional CV evidence from MLCV-AGG1 acts as a protocol gate; fold
models are never candidates.  The best qualified final seed is selected from
immutable D_full + R_full metrics, while every qualified final seed is retained
as the logical active-learning committee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .protocol import MaceJobKind

MLCV_FINAL_SELECTION_POLICY_SCHEMA = "mdstats.mlcv-final-selection-policy.v1"
MLCV_FINAL_SEED_CANDIDATE_SCHEMA = "mdstats.mlcv-final-seed-candidate.v2"
MLCV_FINAL_SEED_CANDIDATE_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-final-seed-candidate.v1"})
MLCV_FINAL_SELECTION_RECORD_SCHEMA = "mdstats.mlcv-final-selection-record.v2"
MLCV_FINAL_SELECTION_RECORD_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-final-selection-record.v1"})
MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA = "mdstats.mlcv-final-committee-member.v2"
MLCV_FINAL_COMMITTEE_MEMBER_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-final-committee-member.v1"})
MLCV_FINAL_COMMITTEE_SCHEMA = "mdstats.mlcv-final-committee.v2"
MLCV_FINAL_COMMITTEE_LEGACY_SCHEMAS = frozenset({"mdstats.mlcv-final-committee.v1"})


@dataclass(frozen=True, slots=True)
class MlcvFinalSelectionPolicy:
    """Authority for final-seed comparison.

    A configured CV campaign must be robust before production selection may be
    created.  Explicit zero-fold campaigns may proceed, but their record keeps
    ``cv_not_performed`` visible and therefore does not fabricate CV evidence.
    """

    require_campaign_cv_robust: bool = True
    allow_cv_not_performed: bool = True

    def __post_init__(self) -> None:
        if not self.require_campaign_cv_robust:
            raise TrainingDataInputError(
                "MLCV-FINAL1 v1 requires configured CV evidence to gate production selection."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_FINAL_SELECTION_POLICY_SCHEMA,
            "require_campaign_cv_robust": self.require_campaign_cv_robust,
            "allow_cv_not_performed": self.allow_cv_not_performed,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFinalSelectionPolicy":
        if payload.get("schema") != MLCV_FINAL_SELECTION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV final-selection policy schema.")
        result = cls(
            require_campaign_cv_robust=bool(payload.get("require_campaign_cv_robust", True)),
            allow_cv_not_performed=bool(payload.get("allow_cv_not_performed", True)),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MLCV final-selection policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvFinalSeedCandidateRecord:
    seed: int
    protocol_variant_digest: str
    final_run_plan_digest: str
    final_run_id: str
    seed_cv_aggregate_digest: str
    seed_cv_outcome: str
    run_selection_record_digest: str
    run_selection_outcome: str
    checkpoint_sha256: str | None = None
    checkpoint_epoch: int | None = None
    target_full_rmse_ev_per_angstrom: float | None = None
    replay_full_rmse_ev_per_angstrom: float | None = None
    full_score_ev_per_angstrom: float | None = None
    replay_foundation_full_rmse_ev_per_angstrom: float | None = None
    replay_degradation_full_rmse_ev_per_angstrom: float | None = None
    replay_degradation_budget_ev_per_angstrom: float | None = None
    replay_absolute_ceiling_ev_per_angstrom: float | None = None
    replay_baseline_model_sha256: str | None = None
    qualified: bool = False
    rejection_reasons: tuple[str, ...] = ()
    serialization_schema: str = field(default=MLCV_FINAL_SEED_CANDIDATE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_FINAL_SEED_CANDIDATE_SCHEMA, *MLCV_FINAL_SEED_CANDIDATE_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV final-seed candidate schema.")
        if int(self.seed) < 0 or not self.final_run_id.strip():
            raise TrainingDataInputError("MLCV-FINAL1 seed/run identity is invalid.")
        for name in (
            "protocol_variant_digest", "final_run_plan_digest",
            "seed_cv_aggregate_digest", "run_selection_record_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.seed_cv_outcome not in {"cv_robust", "cv_failed", "cv_not_performed"}:
            raise TrainingDataInputError("MLCV-FINAL1 received an unsupported seed-CV outcome.")
        if self.run_selection_outcome not in {"representative_selected", "no_representative"}:
            raise TrainingDataInputError("MLCV-FINAL1 received an unsupported final-run selection outcome.")
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        object.__setattr__(self, "rejection_reasons", reasons)
        if self.replay_baseline_model_sha256 is not None:
            object.__setattr__(self, "replay_baseline_model_sha256", validate_digest(self.replay_baseline_model_sha256, name="replay_baseline_model_sha256"))
        has_rep = self.checkpoint_sha256 is not None
        if has_rep:
            object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
            if self.checkpoint_epoch is None or int(self.checkpoint_epoch) < 0:
                raise TrainingDataInputError("MLCV-FINAL1 representative epoch is invalid.")
            for name in ("target_full_rmse_ev_per_angstrom", "replay_full_rmse_ev_per_angstrom"):
                value = getattr(self, name)
                if value is None or not math.isfinite(float(value)) or float(value) < 0.0:
                    raise TrainingDataInputError(f"MLCV-FINAL1 {name} must be finite and nonnegative.")
                object.__setattr__(self, name, float(value))
            if self.full_score_ev_per_angstrom is None or not math.isfinite(float(self.full_score_ev_per_angstrom)):
                raise TrainingDataInputError("MLCV-FINAL1 full score must be finite; signed replay improvement is valid.")
            object.__setattr__(self, "full_score_ev_per_angstrom", float(self.full_score_ev_per_angstrom))
            if self.serialization_schema == MLCV_FINAL_SEED_CANDIDATE_SCHEMA:
                for name in ("replay_foundation_full_rmse_ev_per_angstrom", "replay_degradation_budget_ev_per_angstrom", "replay_absolute_ceiling_ev_per_angstrom"):
                    value = getattr(self, name)
                    if value is None or not math.isfinite(float(value)) or float(value) < 0.0:
                        raise TrainingDataInputError(f"MLCV-FINAL1 {name} must be finite and nonnegative.")
                    object.__setattr__(self, name, float(value))
                degradation = self.replay_degradation_full_rmse_ev_per_angstrom
                if degradation is None or not math.isfinite(float(degradation)):
                    raise TrainingDataInputError("MLCV-FINAL1 replay degradation must be finite; negative improvement is valid.")
                object.__setattr__(self, "replay_degradation_full_rmse_ev_per_angstrom", float(degradation))
                if self.replay_baseline_model_sha256 is None:
                    raise TrainingDataInputError("MLCV-FINAL1 requires authenticated foundation replay identity.")
                expected = float(self.replay_full_rmse_ev_per_angstrom) - float(self.replay_foundation_full_rmse_ev_per_angstrom)
                if not math.isclose(expected, float(degradation), rel_tol=0.0, abs_tol=1e-15):
                    raise TrainingDataInputError("MLCV-FINAL1 replay degradation mismatch.")
                expected_ceiling = float(self.replay_foundation_full_rmse_ev_per_angstrom) + float(self.replay_degradation_budget_ev_per_angstrom)
                if not math.isclose(expected_ceiling, float(self.replay_absolute_ceiling_ev_per_angstrom), rel_tol=0.0, abs_tol=1e-15):
                    raise TrainingDataInputError("MLCV-FINAL1 replay absolute ceiling mismatch.")
        else:
            if any(value is not None for value in (
                self.checkpoint_epoch,
                self.target_full_rmse_ev_per_angstrom,
                self.replay_full_rmse_ev_per_angstrom, self.full_score_ev_per_angstrom,
                self.replay_foundation_full_rmse_ev_per_angstrom, self.replay_degradation_full_rmse_ev_per_angstrom,
                self.replay_degradation_budget_ev_per_angstrom, self.replay_absolute_ceiling_ev_per_angstrom,
                self.replay_baseline_model_sha256,
            )):
                raise TrainingDataInputError("MLCV-FINAL1 no-representative candidate cannot carry model metrics.")
        if self.qualified:
            if not has_rep or reasons:
                raise TrainingDataInputError("Qualified MLCV final candidate requires a representative and no rejection reasons.")
        elif not reasons:
            raise TrainingDataInputError("Rejected MLCV final candidate requires rejection reasons.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema, "seed": int(self.seed),
            "protocol_variant_digest": self.protocol_variant_digest, "final_run_plan_digest": self.final_run_plan_digest,
            "final_run_id": self.final_run_id, "seed_cv_aggregate_digest": self.seed_cv_aggregate_digest,
            "seed_cv_outcome": self.seed_cv_outcome, "run_selection_record_digest": self.run_selection_record_digest,
            "run_selection_outcome": self.run_selection_outcome, "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch, "target_full_rmse_ev_per_angstrom": self.target_full_rmse_ev_per_angstrom,
            "replay_full_rmse_ev_per_angstrom": self.replay_full_rmse_ev_per_angstrom,
            "full_score_ev_per_angstrom": self.full_score_ev_per_angstrom, "qualified": bool(self.qualified),
            "rejection_reasons": list(self.rejection_reasons),
        }
        if self.serialization_schema == MLCV_FINAL_SEED_CANDIDATE_SCHEMA:
            payload.update({
                "replay_foundation_full_rmse_ev_per_angstrom": self.replay_foundation_full_rmse_ev_per_angstrom,
                "replay_degradation_full_rmse_ev_per_angstrom": self.replay_degradation_full_rmse_ev_per_angstrom,
                "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
                "replay_absolute_ceiling_ev_per_angstrom": self.replay_absolute_ceiling_ev_per_angstrom,
                "replay_baseline_model_sha256": self.replay_baseline_model_sha256,
                "replay_semantics": "foundation_relative_degradation",
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFinalSeedCandidateRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_FINAL_SEED_CANDIDATE_SCHEMA, *MLCV_FINAL_SEED_CANDIDATE_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV final-seed candidate schema.")
        result = cls(
            seed=int(payload["seed"]),
            protocol_variant_digest=str(payload["protocol_variant_digest"]),
            final_run_plan_digest=str(payload["final_run_plan_digest"]),
            final_run_id=str(payload["final_run_id"]),
            seed_cv_aggregate_digest=str(payload["seed_cv_aggregate_digest"]),
            seed_cv_outcome=str(payload["seed_cv_outcome"]),
            run_selection_record_digest=str(payload["run_selection_record_digest"]),
            run_selection_outcome=str(payload["run_selection_outcome"]),
            checkpoint_sha256=None if payload.get("checkpoint_sha256") is None else str(payload["checkpoint_sha256"]),
            checkpoint_epoch=None if payload.get("checkpoint_epoch") is None else int(payload["checkpoint_epoch"]),
            target_full_rmse_ev_per_angstrom=None if payload.get("target_full_rmse_ev_per_angstrom") is None else float(payload["target_full_rmse_ev_per_angstrom"]),
            replay_full_rmse_ev_per_angstrom=None if payload.get("replay_full_rmse_ev_per_angstrom") is None else float(payload["replay_full_rmse_ev_per_angstrom"]),
            full_score_ev_per_angstrom=None if payload.get("full_score_ev_per_angstrom") is None else float(payload["full_score_ev_per_angstrom"]),
            replay_foundation_full_rmse_ev_per_angstrom=None if payload.get("replay_foundation_full_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_full_rmse_ev_per_angstrom"]),
            replay_degradation_full_rmse_ev_per_angstrom=None if payload.get("replay_degradation_full_rmse_ev_per_angstrom") is None else float(payload["replay_degradation_full_rmse_ev_per_angstrom"]),
            replay_degradation_budget_ev_per_angstrom=None if payload.get("replay_degradation_budget_ev_per_angstrom") is None else float(payload["replay_degradation_budget_ev_per_angstrom"]),
            replay_absolute_ceiling_ev_per_angstrom=None if payload.get("replay_absolute_ceiling_ev_per_angstrom") is None else float(payload["replay_absolute_ceiling_ev_per_angstrom"]),
            replay_baseline_model_sha256=None if payload.get("replay_baseline_model_sha256") is None else str(payload["replay_baseline_model_sha256"]),
            qualified=bool(payload.get("qualified", False)),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV final-seed candidate digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvFinalSelectionRecord:
    campaign_plan_digest: str
    campaign_cv_aggregate_digest: str
    campaign_cv_outcome: str
    policy_digest: str
    candidates: tuple[MlcvFinalSeedCandidateRecord, ...]
    outcome: str
    production_best_candidate_digest: str | None = None
    production_best_seed: int | None = None
    qualified_committee_candidate_digests: tuple[str, ...] = ()
    production_model_published: bool = False
    next_gate: str = "MLCV-VERIFY1"
    serialization_schema: str = field(default=MLCV_FINAL_SELECTION_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_FINAL_SELECTION_RECORD_SCHEMA, *MLCV_FINAL_SELECTION_RECORD_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV final-selection record schema.")
        for name in ("campaign_plan_digest", "campaign_cv_aggregate_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.campaign_cv_outcome not in {"cv_robust", "cv_failed", "cv_not_performed"}:
            raise TrainingDataInputError("MLCV-FINAL1 campaign CV outcome is invalid.")
        candidates = tuple(sorted(self.candidates, key=lambda v: v.seed))
        if not candidates or len({v.seed for v in candidates}) != len(candidates):
            raise TrainingDataInputError("MLCV-FINAL1 requires unique final candidates by seed.")
        object.__setattr__(self, "candidates", candidates)
        if self.production_model_published:
            raise TrainingDataInputError("MLCV-FINAL1 cannot publish the production model before physical verification.")
        if self.next_gate != "MLCV-VERIFY1":
            raise TrainingDataInputError("MLCV-FINAL1 v1 must hand authority to MLCV-VERIFY1.")
        allowed = {"production_candidate_selected", "cv_failed", "no_qualified_final_representative"}
        if self.outcome not in allowed:
            raise TrainingDataInputError("Unsupported MLCV-FINAL1 outcome.")
        qualified = self.qualified_candidates
        digests = tuple(v.content_digest for v in qualified)
        if self.outcome == "production_candidate_selected":
            if tuple(self.qualified_committee_candidate_digests) != digests:
                raise TrainingDataInputError("MLCV-FINAL1 committee membership must exactly match all qualified final seeds.")
            if not qualified or self.production_best_candidate_digest is None or self.production_best_seed is None:
                raise TrainingDataInputError("MLCV-FINAL1 selected outcome requires one best qualified final candidate.")
            best = qualified[0]
            if self.production_best_candidate_digest != best.content_digest or int(self.production_best_seed) != best.seed:
                raise TrainingDataInputError("MLCV-FINAL1 production-best identity is not the deterministic best qualified final candidate.")
        else:
            if self.qualified_committee_candidate_digests:
                raise TrainingDataInputError("Failed MLCV-FINAL1 outcome cannot publish committee membership.")
            if self.production_best_candidate_digest is not None or self.production_best_seed is not None:
                raise TrainingDataInputError("Failed MLCV-FINAL1 outcome cannot carry a production-best candidate.")
            if self.outcome == "cv_failed" and self.campaign_cv_outcome != "cv_failed":
                raise TrainingDataInputError("MLCV-FINAL1 cv_failed outcome requires failed campaign CV evidence.")

    @property
    def qualified_candidates(self) -> tuple[MlcvFinalSeedCandidateRecord, ...]:
        return tuple(sorted(
            (v for v in self.candidates if v.qualified),
            key=lambda v: (
                round(float(v.full_score_ev_per_angstrom), 15),
                float(v.target_full_rmse_ev_per_angstrom),
                float(v.replay_degradation_full_rmse_ev_per_angstrom) if self.serialization_schema == MLCV_FINAL_SELECTION_RECORD_SCHEMA else float(v.replay_full_rmse_ev_per_angstrom),
                float(v.replay_full_rmse_ev_per_angstrom),
                v.seed,
                int(v.checkpoint_epoch),
                str(v.checkpoint_sha256),
            ),
        ))

    @property
    def production_best_candidate(self) -> MlcvFinalSeedCandidateRecord | None:
        return None if not self.qualified_candidates else self.qualified_candidates[0]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "campaign_cv_aggregate_digest": self.campaign_cv_aggregate_digest,
            "campaign_cv_outcome": self.campaign_cv_outcome,
            "policy_digest": self.policy_digest,
            "candidates": [v.to_dict() for v in self.candidates],
            "outcome": self.outcome,
            "production_best_candidate_digest": self.production_best_candidate_digest,
            "production_best_seed": self.production_best_seed,
            "qualified_committee_candidate_digests": list(self.qualified_committee_candidate_digests),
            "production_model_published": False,
            "next_gate": self.next_gate,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFinalSelectionRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_FINAL_SELECTION_RECORD_SCHEMA, *MLCV_FINAL_SELECTION_RECORD_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV final-selection record schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            campaign_cv_aggregate_digest=str(payload["campaign_cv_aggregate_digest"]),
            campaign_cv_outcome=str(payload["campaign_cv_outcome"]),
            policy_digest=str(payload["policy_digest"]),
            candidates=tuple(MlcvFinalSeedCandidateRecord.from_dict(v) for v in payload["candidates"]),
            outcome=str(payload["outcome"]),
            production_best_candidate_digest=None if payload.get("production_best_candidate_digest") is None else str(payload["production_best_candidate_digest"]),
            production_best_seed=None if payload.get("production_best_seed") is None else int(payload["production_best_seed"]),
            qualified_committee_candidate_digests=tuple(str(v) for v in payload.get("qualified_committee_candidate_digests", ())),
            production_model_published=bool(payload.get("production_model_published", False)),
            next_gate=str(payload.get("next_gate", "MLCV-VERIFY1")),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV final-selection record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvFinalCommitteeMemberRecord:
    final_candidate_digest: str
    seed: int
    final_run_plan_digest: str
    run_selection_record_digest: str
    checkpoint_sha256: str
    checkpoint_epoch: int
    full_score_ev_per_angstrom: float
    target_head_name: str
    exported_model_path: str
    exported_model_sha256: str
    byte_size: int
    replay_absolute_full_rmse_ev_per_angstrom: float | None = None
    replay_foundation_full_rmse_ev_per_angstrom: float | None = None
    replay_degradation_full_rmse_ev_per_angstrom: float | None = None
    replay_degradation_budget_ev_per_angstrom: float | None = None
    serialization_schema: str = field(default=MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA, *MLCV_FINAL_COMMITTEE_MEMBER_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV final committee-member schema.")
        for name in (
            "final_candidate_digest", "final_run_plan_digest", "run_selection_record_digest",
            "checkpoint_sha256", "exported_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.seed < 0 or self.checkpoint_epoch < 0 or self.byte_size <= 0:
            raise TrainingDataInputError("MLCV-FINAL1 committee member metadata are invalid.")
        if not self.target_head_name.strip() or not self.exported_model_path.strip():
            raise TrainingDataInputError("MLCV-FINAL1 committee member paths/head are empty.")
        if not math.isfinite(float(self.full_score_ev_per_angstrom)):
            raise TrainingDataInputError("MLCV-FINAL1 committee member score is invalid.")
        object.__setattr__(self, "full_score_ev_per_angstrom", float(self.full_score_ev_per_angstrom))
        if self.serialization_schema == MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA:
            for name in ("replay_absolute_full_rmse_ev_per_angstrom", "replay_foundation_full_rmse_ev_per_angstrom", "replay_degradation_budget_ev_per_angstrom"):
                value = getattr(self, name)
                if value is None or not math.isfinite(float(value)) or float(value) < 0.0:
                    raise TrainingDataInputError(f"MLCV-FINAL1 committee {name} must be finite and nonnegative.")
                object.__setattr__(self, name, float(value))
            degradation = self.replay_degradation_full_rmse_ev_per_angstrom
            if degradation is None or not math.isfinite(float(degradation)):
                raise TrainingDataInputError("MLCV-FINAL1 committee replay degradation must be finite.")
            object.__setattr__(self, "replay_degradation_full_rmse_ev_per_angstrom", float(degradation))

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "final_candidate_digest": self.final_candidate_digest,
            "seed": self.seed,
            "final_run_plan_digest": self.final_run_plan_digest,
            "run_selection_record_digest": self.run_selection_record_digest,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "full_score_ev_per_angstrom": self.full_score_ev_per_angstrom,
            "target_head_name": self.target_head_name,
            "exported_model_path": self.exported_model_path,
            "exported_model_sha256": self.exported_model_sha256,
            "byte_size": self.byte_size,
        }
        if self.serialization_schema == MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA:
            payload.update({
                "replay_absolute_full_rmse_ev_per_angstrom": self.replay_absolute_full_rmse_ev_per_angstrom,
                "replay_foundation_full_rmse_ev_per_angstrom": self.replay_foundation_full_rmse_ev_per_angstrom,
                "replay_degradation_full_rmse_ev_per_angstrom": self.replay_degradation_full_rmse_ev_per_angstrom,
                "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
                "replay_semantics": "foundation_relative_degradation",
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFinalCommitteeMemberRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_FINAL_COMMITTEE_MEMBER_SCHEMA, *MLCV_FINAL_COMMITTEE_MEMBER_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV final committee-member schema.")
        result = cls(
            final_candidate_digest=str(payload["final_candidate_digest"]), seed=int(payload["seed"]),
            final_run_plan_digest=str(payload["final_run_plan_digest"]),
            run_selection_record_digest=str(payload["run_selection_record_digest"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]), checkpoint_epoch=int(payload["checkpoint_epoch"]),
            full_score_ev_per_angstrom=float(payload["full_score_ev_per_angstrom"]),
            target_head_name=str(payload["target_head_name"]), exported_model_path=str(payload["exported_model_path"]),
            exported_model_sha256=str(payload["exported_model_sha256"]), byte_size=int(payload["byte_size"]),
            replay_absolute_full_rmse_ev_per_angstrom=None if payload.get("replay_absolute_full_rmse_ev_per_angstrom") is None else float(payload["replay_absolute_full_rmse_ev_per_angstrom"]),
            replay_foundation_full_rmse_ev_per_angstrom=None if payload.get("replay_foundation_full_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_full_rmse_ev_per_angstrom"]),
            replay_degradation_full_rmse_ev_per_angstrom=None if payload.get("replay_degradation_full_rmse_ev_per_angstrom") is None else float(payload["replay_degradation_full_rmse_ev_per_angstrom"]),
            replay_degradation_budget_ev_per_angstrom=None if payload.get("replay_degradation_budget_ev_per_angstrom") is None else float(payload["replay_degradation_budget_ev_per_angstrom"]),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV final committee-member digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvFinalCommitteeRecord:
    campaign_plan_digest: str
    final_selection_record_digest: str
    members: tuple[MlcvFinalCommitteeMemberRecord, ...]
    production_best_member_digest: str
    production_model_published: bool = False
    serialization_schema: str = field(default=MLCV_FINAL_COMMITTEE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema not in {MLCV_FINAL_COMMITTEE_SCHEMA, *MLCV_FINAL_COMMITTEE_LEGACY_SCHEMAS}:
            raise TrainingDataInputError("Unsupported MLCV final committee schema.")
        object.__setattr__(self, "campaign_plan_digest", validate_digest(self.campaign_plan_digest, name="campaign_plan_digest"))
        object.__setattr__(self, "final_selection_record_digest", validate_digest(self.final_selection_record_digest, name="final_selection_record_digest"))
        members = tuple(sorted(self.members, key=lambda v: v.seed))
        if not members or len({v.seed for v in members}) != len(members):
            raise TrainingDataInputError("MLCV-FINAL1 committee requires unique qualified final seeds.")
        object.__setattr__(self, "members", members)
        best = validate_digest(self.production_best_member_digest, name="production_best_member_digest")
        object.__setattr__(self, "production_best_member_digest", best)
        if best not in {v.content_digest for v in members}:
            raise TrainingDataInputError("MLCV-FINAL1 production-best committee member is absent.")
        if self.production_model_published:
            raise TrainingDataInputError("MLCV-FINAL1 committee cannot claim verified production publication.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "final_selection_record_digest": self.final_selection_record_digest,
            "members": [v.to_dict() for v in self.members],
            "production_best_member_digest": self.production_best_member_digest,
            "production_model_published": False,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvFinalCommitteeRecord":
        schema = str(payload.get("schema", ""))
        if schema not in {MLCV_FINAL_COMMITTEE_SCHEMA, *MLCV_FINAL_COMMITTEE_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported MLCV final committee schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            final_selection_record_digest=str(payload["final_selection_record_digest"]),
            members=tuple(MlcvFinalCommitteeMemberRecord.from_dict(v) for v in payload["members"]),
            production_best_member_digest=str(payload["production_best_member_digest"]),
            production_model_published=bool(payload.get("production_model_published", False)),
            serialization_schema=schema,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV final committee digest mismatch.")
        return result


def build_mlcv_final_selection(
    campaign: Any,
    campaign_cv: Any,
    seed_cv_aggregates: Sequence[Any],
    final_run_selections: Sequence[Any],
    policy: MlcvFinalSelectionPolicy = MlcvFinalSelectionPolicy(),
) -> MlcvFinalSelectionRecord:
    """Compare only final-development representatives across optimizer seeds."""

    if campaign_cv.campaign_plan_digest != campaign.content_digest:
        raise TrainingDataInputError("MLCV-FINAL1 campaign-CV evidence belongs to another campaign.")
    seed_cv_values = tuple(seed_cv_aggregates)
    seed_cv = {int(v.seed): v for v in seed_cv_values}
    if len(seed_cv) != len(seed_cv_values):
        raise TrainingDataInputError("MLCV-FINAL1 contains duplicate seed-CV aggregates.")
    # FINAL1 must consume the exact seed-CV records already authenticated by
    # the campaign-level AGG1 aggregate.  Matching seeds/outcomes alone are
    # insufficient because a stale or substituted seed record could otherwise
    # alter production eligibility without changing campaign_cv identity.
    embedded_seed_cv = tuple(getattr(campaign_cv, "seed_aggregates", ()))
    if embedded_seed_cv:
        embedded_by_seed = {int(v.seed): v for v in embedded_seed_cv}
        if len(embedded_by_seed) != len(embedded_seed_cv):
            raise TrainingDataInputError("MLCV-FINAL1 campaign-CV evidence contains duplicate seed aggregates.")
        if set(embedded_by_seed) != set(seed_cv):
            raise TrainingDataInputError("MLCV-FINAL1 seed-CV inputs do not match campaign-CV seed coverage.")
        if any(embedded_by_seed[seed].content_digest != seed_cv[seed].content_digest for seed in seed_cv):
            raise TrainingDataInputError("MLCV-FINAL1 seed-CV inputs differ from campaign-CV authenticated evidence.")
    selections = {v.run_plan_digest: v for v in final_run_selections}
    if len(selections) != len(tuple(final_run_selections)):
        raise TrainingDataInputError("MLCV-FINAL1 contains duplicate final-run selection records.")

    final_runs = tuple(run for run in campaign.runs if run.kind is MaceJobKind.FINAL_DEVELOPMENT)
    if not final_runs:
        raise TrainingDataInputError("MLCV-FINAL1 requires final-development runs.")
    if any(run.kind is not MaceJobKind.FINAL_DEVELOPMENT for run in final_runs):
        raise TrainingDataInputError("MLCV-FINAL1 cannot consume fold models.")
    expected_seeds = {int(run.seed) for run in final_runs}
    if set(seed_cv) != expected_seeds:
        raise TrainingDataInputError("MLCV-FINAL1 seed-CV coverage must match final-development seeds exactly.")
    if set(selections) != {run.content_digest for run in final_runs}:
        raise TrainingDataInputError("MLCV-FINAL1 selection coverage must match final-development runs exactly.")

    # Comparable final models must have been judged on the same D_full/R_full
    # domains under the same SELECT1 acceptance geometry.
    selected_records = [selections[run.content_digest] for run in final_runs]
    if any(getattr(v, "serialization_schema", None) != "mdstats.mlcv-run-selection-record.v2" for v in selected_records):
        raise TrainingDataInputError("MLCV-FINAL1 detected stale absolute-replay SELECT1 evidence; regenerate from MLCV-SELECT1.")
    if len({v.selection_policy_digest for v in selected_records}) != 1:
        raise TrainingDataInputError("MLCV-FINAL1 final seeds use different SELECT1 policies.")
    if len({(v.target_full_artifact_digest, v.target_full_sha256) for v in selected_records}) != 1:
        raise TrainingDataInputError("MLCV-FINAL1 final seeds were not evaluated on identical D_full evidence.")
    if len({(v.replay_full_artifact_digest, v.replay_full_sha256) for v in selected_records}) != 1:
        raise TrainingDataInputError("MLCV-FINAL1 final seeds were not evaluated on identical R_full evidence.")

    candidates: list[MlcvFinalSeedCandidateRecord] = []
    for run in sorted(final_runs, key=lambda r: r.seed):
        selection = selections[run.content_digest]
        if selection.kind is not MaceJobKind.FINAL_DEVELOPMENT or selection.fold_index is not None:
            raise TrainingDataInputError("MLCV-FINAL1 received a fold selection in the final-run slot.")
        if int(selection.seed) != int(run.seed):
            raise TrainingDataInputError("MLCV-FINAL1 final selection seed lineage mismatch.")
        cv = seed_cv[int(run.seed)]
        if cv.protocol_variant_digest != run.protocol_variant_digest:
            raise TrainingDataInputError("MLCV-FINAL1 seed-CV and final-run variant lineage mismatch.")
        reasons: list[str] = []
        if cv.outcome == "cv_failed":
            reasons.append("seed_cv_failed")
        elif cv.outcome == "cv_not_performed" and not policy.allow_cv_not_performed:
            reasons.append("cv_not_performed_disallowed")
        representative = selection.representative_candidate
        if selection.outcome != "representative_selected" or representative is None:
            reasons.append("no_final_representative")
        candidates.append(MlcvFinalSeedCandidateRecord(
            seed=run.seed,
            protocol_variant_digest=run.protocol_variant_digest,
            final_run_plan_digest=run.content_digest,
            final_run_id=run.run_id,
            seed_cv_aggregate_digest=cv.content_digest,
            seed_cv_outcome=cv.outcome,
            run_selection_record_digest=selection.content_digest,
            run_selection_outcome=selection.outcome,
            checkpoint_sha256=None if representative is None else representative.checkpoint_sha256,
            checkpoint_epoch=None if representative is None else representative.checkpoint_epoch,
            target_full_rmse_ev_per_angstrom=None if representative is None else representative.target_force_rmse_ev_per_angstrom,
            replay_full_rmse_ev_per_angstrom=None if representative is None else representative.replay_force_rmse_ev_per_angstrom,
            full_score_ev_per_angstrom=None if representative is None else representative.full_score_ev_per_angstrom,
            replay_foundation_full_rmse_ev_per_angstrom=None if representative is None else representative.replay_foundation_force_rmse_ev_per_angstrom,
            replay_degradation_full_rmse_ev_per_angstrom=None if representative is None else representative.replay_degradation_force_rmse_ev_per_angstrom,
            replay_degradation_budget_ev_per_angstrom=None if representative is None else representative.replay_degradation_budget_ev_per_angstrom,
            replay_absolute_ceiling_ev_per_angstrom=None if representative is None else representative.replay_absolute_ceiling_ev_per_angstrom,
            replay_baseline_model_sha256=None if representative is None else representative.replay_baseline_model_sha256,
            qualified=not reasons,
            rejection_reasons=tuple(reasons),
        ))

    # Conventional CV is a recipe-level gate.  If any configured seed/fold
    # combination failed, AGG1 marks the campaign CV failed and FINAL1 cannot
    # publish a production candidate or committee from that protocol identity.
    campaign_cv_failed = campaign_cv.outcome == "cv_failed"
    qualified = tuple(sorted(
        (v for v in candidates if v.qualified),
        key=lambda v: (
            round(float(v.full_score_ev_per_angstrom), 15),
            float(v.target_full_rmse_ev_per_angstrom),
            float(v.replay_degradation_full_rmse_ev_per_angstrom),
            float(v.replay_full_rmse_ev_per_angstrom),
            v.seed,
            int(v.checkpoint_epoch),
            str(v.checkpoint_sha256),
        ),
    ))
    if campaign_cv_failed:
        outcome = "cv_failed"
        committee: tuple[str, ...] = ()
        best = None
    elif not qualified:
        outcome = "no_qualified_final_representative"
        committee = ()
        best = None
    else:
        outcome = "production_candidate_selected"
        committee = tuple(v.content_digest for v in qualified)
        best = qualified[0]
    return MlcvFinalSelectionRecord(
        campaign_plan_digest=campaign.content_digest,
        campaign_cv_aggregate_digest=campaign_cv.content_digest,
        campaign_cv_outcome=campaign_cv.outcome,
        policy_digest=policy.policy_digest,
        candidates=tuple(candidates),
        outcome=outcome,
        production_best_candidate_digest=None if best is None else best.content_digest,
        production_best_seed=None if best is None else best.seed,
        qualified_committee_candidate_digests=committee,
    )
