"""ADAPT-VERIFY1 final verification, fallback, and deployment evidence."""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .adaptive_full_evaluation import (
    AdaptiveFullEvaluationRecord,
    FullEvaluationCandidateRecord,
)

ADAPTIVE_VERIFICATION_POLICY_SCHEMA = "mdstats.adaptive-verification-policy.v1"
ADAPTIVE_VERIFICATION_CANDIDATE_SCHEMA = "mdstats.adaptive-verification-candidate.v1"
ADAPTIVE_VERIFICATION_RECORD_SCHEMA = "mdstats.adaptive-verification-record.v1"
ADAPTIVE_DEPLOYMENT_MODEL_SCHEMA = "mdstats.adaptive-deployment-model.v1"
ADAPTIVE_PROTOCOL_FREEZE_SCHEMA = "mdstats.adaptive-protocol-freeze.v1"


@dataclass(frozen=True, slots=True)
class AdaptiveVerificationPolicy:
    fallback_to_next_admissible_candidate: bool = True
    model_inference_dtype: str = "float32"
    scientific_analysis_dtype: str = "float64"

    def __post_init__(self) -> None:
        model_dtype = str(self.model_inference_dtype).strip().lower()
        if model_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError(
                "Adaptive verification model_inference_dtype must be float32 or float64."
            )
        analysis_dtype = str(self.scientific_analysis_dtype).strip().lower()
        if analysis_dtype != "float64":
            raise TrainingDataInputError(
                "ADAPT-VERIFY1 scientific_analysis_dtype is an invariant float64."
            )
        object.__setattr__(self, "model_inference_dtype", model_dtype)
        object.__setattr__(self, "scientific_analysis_dtype", analysis_dtype)
        object.__setattr__(
            self,
            "fallback_to_next_admissible_candidate",
            bool(self.fallback_to_next_admissible_candidate),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_VERIFICATION_POLICY_SCHEMA,
            "fallback_to_next_admissible_candidate": self.fallback_to_next_admissible_candidate,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveVerificationPolicy":
        if payload.get("schema") != ADAPTIVE_VERIFICATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported adaptive-verification policy schema.")
        result = cls(
            fallback_to_next_admissible_candidate=bool(
                payload["fallback_to_next_admissible_candidate"]
            ),
            model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Adaptive-verification policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AdaptiveVerificationCandidateRecord:
    adaptive_full_evaluation_digest: str
    verification_policy_digest: str
    full_evaluation_candidate_digest: str
    finalist_rank: int
    finalist_batch_index: int
    run_plan_digest: str
    run_id: str
    checkpoint_sha256: str
    checkpoint_epoch: int
    full_score_ev_per_angstrom: float
    target_force_rmse_ev_per_angstrom: float
    replay_force_rmse_ev_per_angstrom: float
    candidate_model_sha256: str
    model_inference_dtype: str
    scientific_analysis_dtype: str
    verification_case_digests: tuple[str, ...]
    passed: bool
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "adaptive_full_evaluation_digest",
            "verification_policy_digest",
            "full_evaluation_candidate_digest",
            "run_plan_digest",
            "checkpoint_sha256",
            "candidate_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.finalist_rank <= 0 or self.finalist_batch_index <= 0 or self.checkpoint_epoch < 0:
            raise TrainingDataInputError("Adaptive verification candidate rank/batch/epoch is invalid.")
        if not str(self.run_id).strip():
            raise TrainingDataInputError("Adaptive verification candidate run_id is empty.")
        for name in (
            "full_score_ev_per_angstrom",
            "target_force_rmse_ev_per_angstrom",
            "replay_force_rmse_ev_per_angstrom",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        dtype = str(self.model_inference_dtype).strip().lower()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Adaptive verification candidate model dtype is invalid.")
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError("Adaptive verification scientific analysis must remain float64.")
        object.__setattr__(self, "model_inference_dtype", dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")
        cases = tuple(validate_digest(value, name="verification_case_digest") for value in self.verification_case_digests)
        if not cases:
            raise TrainingDataInputError("Adaptive verification candidate requires at least one verification case.")
        if len(set(cases)) != len(cases):
            raise TrainingDataInputError("Adaptive verification candidate contains duplicate cases.")
        object.__setattr__(self, "verification_case_digests", cases)
        reasons = tuple(sorted(set(str(value) for value in self.rejection_reasons)))
        if self.passed and reasons:
            raise TrainingDataInputError("Passing adaptive verification candidate cannot carry rejection reasons.")
        if not self.passed and not reasons:
            raise TrainingDataInputError("Failed adaptive verification candidate requires rejection reasons.")
        object.__setattr__(self, "rejection_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_VERIFICATION_CANDIDATE_SCHEMA,
            "adaptive_full_evaluation_digest": self.adaptive_full_evaluation_digest,
            "verification_policy_digest": self.verification_policy_digest,
            "full_evaluation_candidate_digest": self.full_evaluation_candidate_digest,
            "finalist_rank": self.finalist_rank,
            "finalist_batch_index": self.finalist_batch_index,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "full_score_ev_per_angstrom": self.full_score_ev_per_angstrom,
            "target_force_rmse_ev_per_angstrom": self.target_force_rmse_ev_per_angstrom,
            "replay_force_rmse_ev_per_angstrom": self.replay_force_rmse_ev_per_angstrom,
            "candidate_model_sha256": self.candidate_model_sha256,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "verification_case_digests": list(self.verification_case_digests),
            "passed": bool(self.passed),
            "rejection_reasons": list(self.rejection_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveVerificationCandidateRecord":
        if payload.get("schema") != ADAPTIVE_VERIFICATION_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported adaptive-verification candidate schema.")
        result = cls(
            adaptive_full_evaluation_digest=str(payload["adaptive_full_evaluation_digest"]),
            verification_policy_digest=str(payload["verification_policy_digest"]),
            full_evaluation_candidate_digest=str(payload["full_evaluation_candidate_digest"]),
            finalist_rank=int(payload["finalist_rank"]),
            finalist_batch_index=int(payload["finalist_batch_index"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            run_id=str(payload["run_id"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            checkpoint_epoch=int(payload["checkpoint_epoch"]),
            full_score_ev_per_angstrom=float(payload["full_score_ev_per_angstrom"]),
            target_force_rmse_ev_per_angstrom=float(payload["target_force_rmse_ev_per_angstrom"]),
            replay_force_rmse_ev_per_angstrom=float(payload["replay_force_rmse_ev_per_angstrom"]),
            candidate_model_sha256=str(payload["candidate_model_sha256"]),
            model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]),
            verification_case_digests=tuple(str(v) for v in payload["verification_case_digests"]),
            passed=bool(payload["passed"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Adaptive-verification candidate digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AdaptiveVerificationRecord:
    campaign_plan_digest: str
    adaptive_full_evaluation_digest: str
    verification_policy_digest: str
    attempts: tuple[AdaptiveVerificationCandidateRecord, ...]
    outcome: str
    selected_attempt_digest: str | None = None

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "adaptive_full_evaluation_digest", "verification_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        attempts = tuple(self.attempts)
        if not attempts:
            raise TrainingDataInputError("Adaptive verification requires at least one attempted candidate.")
        ranks = [v.finalist_rank for v in attempts]
        if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
            raise TrainingDataInputError("Adaptive verification attempts must follow unique finalist-rank order.")
        object.__setattr__(self, "attempts", attempts)
        allowed = {"verified_candidate_selected", "no_candidate_passed"}
        if self.outcome not in allowed:
            raise TrainingDataInputError("Unsupported adaptive verification outcome.")
        passing = tuple(v for v in attempts if v.passed)
        if self.outcome == "verified_candidate_selected":
            if len(passing) != 1 or passing[-1] is not attempts[-1]:
                raise TrainingDataInputError("Adaptive verification must stop immediately at the first passing candidate.")
            expected = passing[0].content_digest
            if self.selected_attempt_digest is None:
                object.__setattr__(self, "selected_attempt_digest", expected)
            elif validate_digest(self.selected_attempt_digest, name="selected_attempt_digest") != expected:
                raise TrainingDataInputError("Adaptive verification selected-attempt digest mismatch.")
        else:
            if passing or self.selected_attempt_digest is not None:
                raise TrainingDataInputError("No-candidate-passed outcome cannot carry a selected attempt.")

    @property
    def selected_attempt(self) -> AdaptiveVerificationCandidateRecord | None:
        return next((v for v in self.attempts if v.passed), None)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_VERIFICATION_RECORD_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "adaptive_full_evaluation_digest": self.adaptive_full_evaluation_digest,
            "verification_policy_digest": self.verification_policy_digest,
            "attempts": [v.to_dict() for v in self.attempts],
            "outcome": self.outcome,
            "selected_attempt_digest": self.selected_attempt_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveVerificationRecord":
        if payload.get("schema") != ADAPTIVE_VERIFICATION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported adaptive-verification record schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            adaptive_full_evaluation_digest=str(payload["adaptive_full_evaluation_digest"]),
            verification_policy_digest=str(payload["verification_policy_digest"]),
            attempts=tuple(AdaptiveVerificationCandidateRecord.from_dict(v) for v in payload["attempts"]),
            outcome=str(payload["outcome"]),
            selected_attempt_digest=(None if payload.get("selected_attempt_digest") is None else str(payload["selected_attempt_digest"])),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Adaptive-verification record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AdaptiveDeploymentModelRecord:
    campaign_plan_digest: str
    adaptive_full_evaluation_digest: str
    adaptive_verification_digest: str
    selected_full_evaluation_candidate_digest: str
    selected_verification_attempt_digest: str
    run_plan_digest: str
    run_id: str
    checkpoint_sha256: str
    checkpoint_epoch: int
    target_head_name: str
    model_inference_dtype: str
    scientific_analysis_dtype: str
    exported_model_path: str
    exported_model_sha256: str
    byte_size: int

    def __post_init__(self) -> None:
        for name in (
            "campaign_plan_digest", "adaptive_full_evaluation_digest", "adaptive_verification_digest",
            "selected_full_evaluation_candidate_digest", "selected_verification_attempt_digest",
            "run_plan_digest", "checkpoint_sha256", "exported_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.checkpoint_epoch < 0 or self.byte_size <= 0:
            raise TrainingDataInputError("Adaptive deployment checkpoint epoch/size is invalid.")
        if not str(self.run_id).strip() or not str(self.target_head_name).strip():
            raise TrainingDataInputError("Adaptive deployment run/head identity is empty.")
        dtype = str(self.model_inference_dtype).strip().lower()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Adaptive deployment model dtype is invalid.")
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError("Adaptive deployment scientific analysis must remain float64.")
        object.__setattr__(self, "model_inference_dtype", dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_DEPLOYMENT_MODEL_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "adaptive_full_evaluation_digest": self.adaptive_full_evaluation_digest,
            "adaptive_verification_digest": self.adaptive_verification_digest,
            "selected_full_evaluation_candidate_digest": self.selected_full_evaluation_candidate_digest,
            "selected_verification_attempt_digest": self.selected_verification_attempt_digest,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "target_head_name": self.target_head_name,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "exported_model_path": self.exported_model_path,
            "exported_model_sha256": self.exported_model_sha256,
            "byte_size": self.byte_size,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveDeploymentModelRecord":
        if payload.get("schema") != ADAPTIVE_DEPLOYMENT_MODEL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported adaptive-deployment model schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            adaptive_full_evaluation_digest=str(payload["adaptive_full_evaluation_digest"]),
            adaptive_verification_digest=str(payload["adaptive_verification_digest"]),
            selected_full_evaluation_candidate_digest=str(payload["selected_full_evaluation_candidate_digest"]),
            selected_verification_attempt_digest=str(payload["selected_verification_attempt_digest"]),
            run_plan_digest=str(payload["run_plan_digest"]), run_id=str(payload["run_id"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]), checkpoint_epoch=int(payload["checkpoint_epoch"]),
            target_head_name=str(payload["target_head_name"]), model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]), exported_model_path=str(payload["exported_model_path"]),
            exported_model_sha256=str(payload["exported_model_sha256"]), byte_size=int(payload["byte_size"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Adaptive-deployment model digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AdaptiveProtocolFreezeRecord:
    production_qualification_digest: str
    campaign_plan_digest: str
    adaptive_full_evaluation_digest: str
    adaptive_verification_digest: str
    adaptive_deployment_model_digest: str
    selected_full_evaluation_candidate_digest: str
    full_target_artifact_digest: str
    full_replay_artifact_digest: str
    exported_model_sha256: str
    model_inference_dtype: str
    scientific_analysis_dtype: str
    frozen_at_utc: str

    def __post_init__(self) -> None:
        for name in (
            "production_qualification_digest", "campaign_plan_digest", "adaptive_full_evaluation_digest",
            "adaptive_verification_digest", "adaptive_deployment_model_digest",
            "selected_full_evaluation_candidate_digest", "full_target_artifact_digest",
            "full_replay_artifact_digest", "exported_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        dtype = str(self.model_inference_dtype).strip().lower()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Adaptive protocol-freeze model dtype is invalid.")
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError("Adaptive protocol-freeze analysis dtype must remain float64.")
        if not str(self.frozen_at_utc).strip():
            raise TrainingDataInputError("Adaptive protocol freeze requires a timestamp.")
        object.__setattr__(self, "model_inference_dtype", dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ADAPTIVE_PROTOCOL_FREEZE_SCHEMA,
            "production_qualification_digest": self.production_qualification_digest,
            "campaign_plan_digest": self.campaign_plan_digest,
            "adaptive_full_evaluation_digest": self.adaptive_full_evaluation_digest,
            "adaptive_verification_digest": self.adaptive_verification_digest,
            "adaptive_deployment_model_digest": self.adaptive_deployment_model_digest,
            "selected_full_evaluation_candidate_digest": self.selected_full_evaluation_candidate_digest,
            "full_target_artifact_digest": self.full_target_artifact_digest,
            "full_replay_artifact_digest": self.full_replay_artifact_digest,
            "exported_model_sha256": self.exported_model_sha256,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "frozen_at_utc": self.frozen_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveProtocolFreezeRecord":
        if payload.get("schema") != ADAPTIVE_PROTOCOL_FREEZE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported adaptive protocol-freeze schema.")
        result = cls(
            production_qualification_digest=str(payload["production_qualification_digest"]),
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            adaptive_full_evaluation_digest=str(payload["adaptive_full_evaluation_digest"]),
            adaptive_verification_digest=str(payload["adaptive_verification_digest"]),
            adaptive_deployment_model_digest=str(payload["adaptive_deployment_model_digest"]),
            selected_full_evaluation_candidate_digest=str(payload["selected_full_evaluation_candidate_digest"]),
            full_target_artifact_digest=str(payload["full_target_artifact_digest"]),
            full_replay_artifact_digest=str(payload["full_replay_artifact_digest"]),
            exported_model_sha256=str(payload["exported_model_sha256"]),
            model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]),
            frozen_at_utc=str(payload["frozen_at_utc"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Adaptive protocol-freeze digest mismatch.")
        return result


def ordered_admissible_candidates(
    record: AdaptiveFullEvaluationRecord,
    *,
    fallback_to_next_admissible_candidate: bool = True,
) -> tuple[FullEvaluationCandidateRecord, ...]:
    """Return the exact ADAPT-VERIFY1 verification order."""
    candidates = record.admissible_candidates
    if not candidates:
        raise TrainingDataInputError("ADAPT-VERIFY1 requires at least one fully admissible EVAL1 candidate.")
    return candidates if fallback_to_next_admissible_candidate else candidates[:1]


def verification_rejection_reasons(
    cases: Sequence[Mapping[str, Any]],
    *,
    maximum_energy_drift_ev_per_atom_per_ps: float,
    minimum_pair_distance_angstrom: float,
    maximum_force_ev_per_angstrom: float,
) -> tuple[str, ...]:
    reasons: set[str] = set()
    for case in cases:
        if not bool(case.get("finite", False)):
            reasons.add("nonfinite_nve_observable")
        if float(case.get("absolute_energy_drift_ev_per_atom_per_ps", math.inf)) > float(maximum_energy_drift_ev_per_atom_per_ps):
            reasons.add("energy_drift_threshold_exceeded")
        if float(case.get("minimum_pair_distance_angstrom", -math.inf)) < float(minimum_pair_distance_angstrom):
            reasons.add("minimum_pair_distance_threshold_violated")
        if float(case.get("maximum_force_ev_per_angstrom", math.inf)) > float(maximum_force_ev_per_angstrom):
            reasons.add("maximum_force_threshold_exceeded")
    return tuple(sorted(reasons))


__all__ = [
    "ADAPTIVE_VERIFICATION_POLICY_SCHEMA",
    "ADAPTIVE_VERIFICATION_CANDIDATE_SCHEMA",
    "ADAPTIVE_VERIFICATION_RECORD_SCHEMA",
    "ADAPTIVE_DEPLOYMENT_MODEL_SCHEMA",
    "ADAPTIVE_PROTOCOL_FREEZE_SCHEMA",
    "AdaptiveVerificationPolicy",
    "AdaptiveVerificationCandidateRecord",
    "AdaptiveVerificationRecord",
    "AdaptiveDeploymentModelRecord",
    "AdaptiveProtocolFreezeRecord",
    "ordered_admissible_candidates",
    "verification_rejection_reasons",
]
