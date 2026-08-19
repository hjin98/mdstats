"""MLCV-VERIFY1 physical verification, locked-test, and production publication authority.

Physical verification may fall back only across already-qualified FINAL1 final-seed
representatives.  The first physical passer is frozen.  After that point fallback
ends permanently: the locked target test E is activated and evaluated exactly once
on the frozen candidate.  Locked-test failure is review/failure evidence, never a
model-selection signal.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .mlcv_roles import MlcvDataRole, MlcvEvidenceOperation, require_mlcv_role

MLCV_VERIFICATION_POLICY_SCHEMA = "mdstats.mlcv-verification-policy.v1"
MLCV_PHYSICAL_ATTEMPT_SCHEMA = "mdstats.mlcv-physical-verification-attempt.v1"
MLCV_VERIFICATION_RECORD_SCHEMA = "mdstats.mlcv-verification-record.v1"
MLCV_LOCKED_TEST_RECORD_SCHEMA = "mdstats.mlcv-locked-test-record.v1"
MLCV_PRODUCTION_MODEL_SCHEMA = "mdstats.mlcv-production-model.v1"


@dataclass(frozen=True, slots=True)
class MlcvVerificationPolicy:
    fallback_to_next_qualified_final_seed: bool = True
    model_inference_dtype: str = "float32"
    scientific_analysis_dtype: str = "float64"
    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    maximum_energy_drift_ev_per_atom_per_ps: float = 0.026
    minimum_pair_distance_angstrom: float = 0.8
    maximum_force_ev_per_angstrom: float = 100.0
    retained_checkpoint_metric_policy_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "fallback_to_next_qualified_final_seed", bool(self.fallback_to_next_qualified_final_seed))
        model_dtype = str(self.model_inference_dtype).strip().lower()
        if model_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("MLCV-VERIFY1 model_inference_dtype must be float32 or float64.")
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError("MLCV-VERIFY1 scientific_analysis_dtype is invariant float64.")
        object.__setattr__(self, "model_inference_dtype", model_dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")
        threshold = float(self.maximum_target_force_rmse_ev_per_angstrom)
        if not math.isfinite(threshold) or threshold <= 0.0:
            raise TrainingDataInputError("MLCV-VERIFY1 locked-test target threshold must be finite and positive.")
        object.__setattr__(self, "maximum_target_force_rmse_ev_per_angstrom", threshold)
        drift = float(self.maximum_energy_drift_ev_per_atom_per_ps)
        minimum_distance = float(self.minimum_pair_distance_angstrom)
        maximum_force = float(self.maximum_force_ev_per_angstrom)
        if not math.isfinite(drift) or drift <= 0.0:
            raise TrainingDataInputError("MLCV-VERIFY1 energy-drift threshold must be finite and positive.")
        if not math.isfinite(minimum_distance) or minimum_distance <= 0.0:
            raise TrainingDataInputError("MLCV-VERIFY1 minimum pair-distance threshold must be finite and positive.")
        if not math.isfinite(maximum_force) or maximum_force <= 0.0:
            raise TrainingDataInputError("MLCV-VERIFY1 maximum-force threshold must be finite and positive.")
        object.__setattr__(self, "maximum_energy_drift_ev_per_atom_per_ps", drift)
        object.__setattr__(self, "minimum_pair_distance_angstrom", minimum_distance)
        object.__setattr__(self, "maximum_force_ev_per_angstrom", maximum_force)
        if self.retained_checkpoint_metric_policy_digest is not None:
            object.__setattr__(self, "retained_checkpoint_metric_policy_digest", validate_digest(
                self.retained_checkpoint_metric_policy_digest,
                name="retained_checkpoint_metric_policy_digest",
            ))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_VERIFICATION_POLICY_SCHEMA,
            "fallback_to_next_qualified_final_seed": self.fallback_to_next_qualified_final_seed,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "maximum_energy_drift_ev_per_atom_per_ps": self.maximum_energy_drift_ev_per_atom_per_ps,
            "minimum_pair_distance_angstrom": self.minimum_pair_distance_angstrom,
            "maximum_force_ev_per_angstrom": self.maximum_force_ev_per_angstrom,
            "retained_checkpoint_metric_policy_digest": self.retained_checkpoint_metric_policy_digest,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvVerificationPolicy":
        if payload.get("schema") != MLCV_VERIFICATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV verification-policy schema.")
        result = cls(
            fallback_to_next_qualified_final_seed=bool(payload["fallback_to_next_qualified_final_seed"]),
            model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]),
            maximum_target_force_rmse_ev_per_angstrom=float(payload["maximum_target_force_rmse_ev_per_angstrom"]),
            maximum_energy_drift_ev_per_atom_per_ps=float(payload.get("maximum_energy_drift_ev_per_atom_per_ps", 0.026)),
            minimum_pair_distance_angstrom=float(payload.get("minimum_pair_distance_angstrom", 0.8)),
            maximum_force_ev_per_angstrom=float(payload.get("maximum_force_ev_per_angstrom", 100.0)),
            retained_checkpoint_metric_policy_digest=(None if payload.get("retained_checkpoint_metric_policy_digest") is None else str(payload["retained_checkpoint_metric_policy_digest"])),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MLCV verification-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvPhysicalVerificationAttemptRecord:
    final_candidate_digest: str
    committee_member_digest: str
    seed: int
    final_run_plan_digest: str
    run_id: str
    checkpoint_sha256: str
    checkpoint_epoch: int
    candidate_rank: int
    exported_model_sha256: str
    verification_policy_digest: str
    verification_case_digests: tuple[str, ...]
    passed: bool
    rejection_reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "final_candidate_digest", "committee_member_digest", "final_run_plan_digest",
            "checkpoint_sha256", "exported_model_sha256", "verification_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.seed) < 0 or int(self.checkpoint_epoch) < 0 or int(self.candidate_rank) <= 0:
            raise TrainingDataInputError("MLCV-VERIFY1 attempt seed/epoch/rank is invalid.")
        if not str(self.run_id).strip():
            raise TrainingDataInputError("MLCV-VERIFY1 attempt run_id is empty.")
        cases = tuple(validate_digest(v, name="verification_case_digest") for v in self.verification_case_digests)
        if not cases or len(set(cases)) != len(cases):
            raise TrainingDataInputError("MLCV-VERIFY1 attempt requires unique physical-verification cases.")
        object.__setattr__(self, "verification_case_digests", cases)
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        if self.passed and reasons:
            raise TrainingDataInputError("Passing MLCV physical-verification attempt cannot carry rejection reasons.")
        if not self.passed and not reasons:
            raise TrainingDataInputError("Failed MLCV physical-verification attempt requires rejection reasons.")
        object.__setattr__(self, "rejection_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_PHYSICAL_ATTEMPT_SCHEMA,
            "final_candidate_digest": self.final_candidate_digest,
            "committee_member_digest": self.committee_member_digest,
            "seed": int(self.seed),
            "final_run_plan_digest": self.final_run_plan_digest,
            "run_id": self.run_id,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": int(self.checkpoint_epoch),
            "candidate_rank": int(self.candidate_rank),
            "exported_model_sha256": self.exported_model_sha256,
            "verification_policy_digest": self.verification_policy_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvPhysicalVerificationAttemptRecord":
        if payload.get("schema") != MLCV_PHYSICAL_ATTEMPT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV physical-verification attempt schema.")
        result = cls(
            final_candidate_digest=str(payload["final_candidate_digest"]),
            committee_member_digest=str(payload["committee_member_digest"]),
            seed=int(payload["seed"]), final_run_plan_digest=str(payload["final_run_plan_digest"]),
            run_id=str(payload["run_id"]), checkpoint_sha256=str(payload["checkpoint_sha256"]),
            checkpoint_epoch=int(payload["checkpoint_epoch"]), candidate_rank=int(payload["candidate_rank"]),
            exported_model_sha256=str(payload["exported_model_sha256"]),
            verification_policy_digest=str(payload["verification_policy_digest"]),
            verification_case_digests=tuple(str(v) for v in payload["verification_case_digests"]),
            passed=bool(payload["passed"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV physical-verification attempt digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvVerificationRecord:
    campaign_plan_digest: str
    final_selection_record_digest: str
    final_committee_record_digest: str
    verification_policy_digest: str
    attempts: tuple[MlcvPhysicalVerificationAttemptRecord, ...]
    outcome: str
    frozen_attempt_digest: str | None = None
    frozen_final_candidate_digest: str | None = None
    frozen_committee_member_digest: str | None = None
    production_model_published: bool = False
    locked_test_activated: bool = False

    def __post_init__(self) -> None:
        for name in ("campaign_plan_digest", "final_selection_record_digest", "final_committee_record_digest", "verification_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        attempts = tuple(self.attempts)
        if not attempts:
            raise TrainingDataInputError("MLCV-VERIFY1 requires at least one physical-verification attempt.")
        if tuple(v.candidate_rank for v in attempts) != tuple(range(1, len(attempts) + 1)):
            raise TrainingDataInputError("MLCV-VERIFY1 attempts must preserve FINAL1 verification order without gaps.")
        if sum(v.passed for v in attempts) > 1 or any(v.passed for v in attempts[:-1]):
            raise TrainingDataInputError("MLCV-VERIFY1 stops at the first physical-verification passer.")
        object.__setattr__(self, "attempts", attempts)
        if self.production_model_published or self.locked_test_activated:
            raise TrainingDataInputError("Physical-verification record precedes locked-test activation/publication.")
        if self.outcome not in {"physical_candidate_frozen", "no_candidate_passed"}:
            raise TrainingDataInputError("Unsupported MLCV physical-verification outcome.")
        if self.outcome == "physical_candidate_frozen":
            if not attempts[-1].passed:
                raise TrainingDataInputError("Frozen MLCV candidate requires a passing terminal physical attempt.")
            frozen = attempts[-1]
            expected = (frozen.content_digest, frozen.final_candidate_digest, frozen.committee_member_digest)
            observed = (self.frozen_attempt_digest, self.frozen_final_candidate_digest, self.frozen_committee_member_digest)
            if observed != expected:
                raise TrainingDataInputError("MLCV frozen physical candidate identity mismatch.")
        else:
            if any(v.passed for v in attempts):
                raise TrainingDataInputError("No-candidate-passed MLCV outcome contains a passing attempt.")
            if any(v is not None for v in (self.frozen_attempt_digest, self.frozen_final_candidate_digest, self.frozen_committee_member_digest)):
                raise TrainingDataInputError("Failed MLCV physical verification cannot freeze a candidate.")

    @property
    def frozen_attempt(self) -> MlcvPhysicalVerificationAttemptRecord | None:
        return None if self.outcome != "physical_candidate_frozen" else self.attempts[-1]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_VERIFICATION_RECORD_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "final_selection_record_digest": self.final_selection_record_digest,
            "final_committee_record_digest": self.final_committee_record_digest,
            "verification_policy_digest": self.verification_policy_digest,
            "attempts": [v.to_dict() for v in self.attempts],
            "outcome": self.outcome,
            "frozen_attempt_digest": self.frozen_attempt_digest,
            "frozen_final_candidate_digest": self.frozen_final_candidate_digest,
            "frozen_committee_member_digest": self.frozen_committee_member_digest,
            "production_model_published": False,
            "locked_test_activated": False,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvVerificationRecord":
        if payload.get("schema") != MLCV_VERIFICATION_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV verification-record schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            final_selection_record_digest=str(payload["final_selection_record_digest"]),
            final_committee_record_digest=str(payload["final_committee_record_digest"]),
            verification_policy_digest=str(payload["verification_policy_digest"]),
            attempts=tuple(MlcvPhysicalVerificationAttemptRecord.from_dict(v) for v in payload["attempts"]),
            outcome=str(payload["outcome"]),
            frozen_attempt_digest=None if payload.get("frozen_attempt_digest") is None else str(payload["frozen_attempt_digest"]),
            frozen_final_candidate_digest=None if payload.get("frozen_final_candidate_digest") is None else str(payload["frozen_final_candidate_digest"]),
            frozen_committee_member_digest=None if payload.get("frozen_committee_member_digest") is None else str(payload["frozen_committee_member_digest"]),
            production_model_published=bool(payload.get("production_model_published", False)),
            locked_test_activated=bool(payload.get("locked_test_activated", False)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV verification-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvLockedTestRecord:
    campaign_plan_digest: str
    final_selection_record_digest: str
    verification_record_digest: str
    verification_policy_digest: str
    frozen_final_candidate_digest: str
    frozen_committee_member_digest: str
    frozen_exported_model_sha256: str
    locked_test_role: MlcvDataRole
    sealed_evaluation_artifact_digest: str
    locked_test_artifact_digest: str
    locked_test_sha256: str
    evaluation_record_digest: str
    target_force_rmse_ev_per_angstrom: float
    passed: bool
    rejection_reasons: tuple[str, ...] = ()
    evaluation_count: int = 1
    fallback_permitted: bool = False

    def __post_init__(self) -> None:
        for name in (
            "campaign_plan_digest", "final_selection_record_digest", "verification_record_digest",
            "verification_policy_digest", "frozen_final_candidate_digest", "frozen_committee_member_digest",
            "frozen_exported_model_sha256", "sealed_evaluation_artifact_digest", "locked_test_artifact_digest",
            "locked_test_sha256", "evaluation_record_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        role = MlcvDataRole(self.locked_test_role)
        require_mlcv_role(role, MlcvEvidenceOperation.LOCKED_TEST_EVALUATION, context="MLCV locked test")
        if role is not MlcvDataRole.TARGET_LOCKED_TEST:
            raise TrainingDataInputError("MLCV locked test must use TARGET_LOCKED_TEST authority.")
        object.__setattr__(self, "locked_test_role", role)
        value = float(self.target_force_rmse_ev_per_angstrom)
        if not math.isfinite(value) or value < 0.0:
            raise TrainingDataInputError("MLCV locked-test target RMSE is invalid.")
        object.__setattr__(self, "target_force_rmse_ev_per_angstrom", value)
        if int(self.evaluation_count) != 1 or self.fallback_permitted:
            raise TrainingDataInputError("MLCV locked E is exactly one-shot and cannot authorize fallback.")
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        if self.passed and reasons:
            raise TrainingDataInputError("Passing locked-test record cannot carry rejection reasons.")
        if not self.passed and not reasons:
            raise TrainingDataInputError("Failed locked-test record requires rejection reasons.")
        object.__setattr__(self, "rejection_reasons", reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_LOCKED_TEST_RECORD_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "final_selection_record_digest": self.final_selection_record_digest,
            "verification_record_digest": self.verification_record_digest,
            "verification_policy_digest": self.verification_policy_digest,
            "frozen_final_candidate_digest": self.frozen_final_candidate_digest,
            "frozen_committee_member_digest": self.frozen_committee_member_digest,
            "frozen_exported_model_sha256": self.frozen_exported_model_sha256,
            "locked_test_role": self.locked_test_role.value,
            "sealed_evaluation_artifact_digest": self.sealed_evaluation_artifact_digest,
            "locked_test_artifact_digest": self.locked_test_artifact_digest,
            "locked_test_sha256": self.locked_test_sha256,
            "evaluation_record_digest": self.evaluation_record_digest,
            "target_force_rmse_ev_per_angstrom": self.target_force_rmse_ev_per_angstrom,
            "passed": bool(self.passed),
            "rejection_reasons": list(self.rejection_reasons),
            "evaluation_count": 1,
            "fallback_permitted": False,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvLockedTestRecord":
        if payload.get("schema") != MLCV_LOCKED_TEST_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV locked-test schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            final_selection_record_digest=str(payload["final_selection_record_digest"]),
            verification_record_digest=str(payload["verification_record_digest"]),
            verification_policy_digest=str(payload["verification_policy_digest"]),
            frozen_final_candidate_digest=str(payload["frozen_final_candidate_digest"]),
            frozen_committee_member_digest=str(payload["frozen_committee_member_digest"]),
            frozen_exported_model_sha256=str(payload["frozen_exported_model_sha256"]),
            locked_test_role=MlcvDataRole(payload["locked_test_role"]),
            sealed_evaluation_artifact_digest=str(payload["sealed_evaluation_artifact_digest"]),
            locked_test_artifact_digest=str(payload["locked_test_artifact_digest"]),
            locked_test_sha256=str(payload["locked_test_sha256"]),
            evaluation_record_digest=str(payload["evaluation_record_digest"]),
            target_force_rmse_ev_per_angstrom=float(payload["target_force_rmse_ev_per_angstrom"]),
            passed=bool(payload["passed"]), rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
            evaluation_count=int(payload.get("evaluation_count", 1)), fallback_permitted=bool(payload.get("fallback_permitted", False)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV locked-test digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MlcvProductionModelRecord:
    campaign_plan_digest: str
    final_selection_record_digest: str
    verification_record_digest: str
    locked_test_record_digest: str
    selected_final_candidate_digest: str
    selected_verification_attempt_digest: str
    selected_committee_member_digest: str
    run_plan_digest: str
    run_id: str
    seed: int
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
            "campaign_plan_digest", "final_selection_record_digest", "verification_record_digest",
            "locked_test_record_digest", "selected_final_candidate_digest", "selected_verification_attempt_digest",
            "selected_committee_member_digest", "run_plan_digest", "checkpoint_sha256", "exported_model_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.seed) < 0 or int(self.checkpoint_epoch) < 0 or int(self.byte_size) <= 0:
            raise TrainingDataInputError("MLCV production model seed/epoch/size is invalid.")
        if not self.run_id.strip() or not self.target_head_name.strip() or not self.exported_model_path.strip():
            raise TrainingDataInputError("MLCV production model identity/path is incomplete.")
        dtype = str(self.model_inference_dtype).strip().lower()
        if dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("MLCV production model dtype is invalid.")
        if str(self.scientific_analysis_dtype).strip().lower() != "float64":
            raise TrainingDataInputError("MLCV production scientific arithmetic must remain float64.")
        object.__setattr__(self, "model_inference_dtype", dtype)
        object.__setattr__(self, "scientific_analysis_dtype", "float64")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MLCV_PRODUCTION_MODEL_SCHEMA,
            "campaign_plan_digest": self.campaign_plan_digest,
            "final_selection_record_digest": self.final_selection_record_digest,
            "verification_record_digest": self.verification_record_digest,
            "locked_test_record_digest": self.locked_test_record_digest,
            "selected_final_candidate_digest": self.selected_final_candidate_digest,
            "selected_verification_attempt_digest": self.selected_verification_attempt_digest,
            "selected_committee_member_digest": self.selected_committee_member_digest,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "seed": int(self.seed),
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": int(self.checkpoint_epoch),
            "target_head_name": self.target_head_name,
            "model_inference_dtype": self.model_inference_dtype,
            "scientific_analysis_dtype": self.scientific_analysis_dtype,
            "exported_model_path": self.exported_model_path,
            "exported_model_sha256": self.exported_model_sha256,
            "byte_size": int(self.byte_size),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MlcvProductionModelRecord":
        if payload.get("schema") != MLCV_PRODUCTION_MODEL_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MLCV production-model schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]), final_selection_record_digest=str(payload["final_selection_record_digest"]),
            verification_record_digest=str(payload["verification_record_digest"]), locked_test_record_digest=str(payload["locked_test_record_digest"]),
            selected_final_candidate_digest=str(payload["selected_final_candidate_digest"]), selected_verification_attempt_digest=str(payload["selected_verification_attempt_digest"]),
            selected_committee_member_digest=str(payload["selected_committee_member_digest"]), run_plan_digest=str(payload["run_plan_digest"]),
            run_id=str(payload["run_id"]), seed=int(payload["seed"]), checkpoint_sha256=str(payload["checkpoint_sha256"]),
            checkpoint_epoch=int(payload["checkpoint_epoch"]), target_head_name=str(payload["target_head_name"]), model_inference_dtype=str(payload["model_inference_dtype"]),
            scientific_analysis_dtype=str(payload["scientific_analysis_dtype"]), exported_model_path=str(payload["exported_model_path"]),
            exported_model_sha256=str(payload["exported_model_sha256"]), byte_size=int(payload["byte_size"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MLCV production-model digest mismatch.")
        return result


def build_mlcv_production_model_record(
    campaign: Any,
    final_selection: Any,
    committee: Any,
    verification: MlcvVerificationRecord,
    locked_test: MlcvLockedTestRecord,
    policy: MlcvVerificationPolicy,
    *,
    exported_model_path: str,
    exported_model_sha256: str,
    byte_size: int,
) -> MlcvProductionModelRecord:
    if verification.outcome != "physical_candidate_frozen" or verification.frozen_attempt is None:
        raise TrainingDataInputError("Production publication requires a frozen physical-verification candidate.")
    if not locked_test.passed:
        raise TrainingDataInputError("Production publication requires locked E to pass.")
    if verification.campaign_plan_digest != campaign.content_digest or locked_test.campaign_plan_digest != campaign.content_digest:
        raise TrainingDataInputError("MLCV production-model campaign lineage mismatch.")
    if verification.final_selection_record_digest != final_selection.content_digest or locked_test.final_selection_record_digest != final_selection.content_digest:
        raise TrainingDataInputError("MLCV production-model final-selection lineage mismatch.")
    if verification.final_committee_record_digest != committee.content_digest:
        raise TrainingDataInputError("MLCV production-model committee lineage mismatch.")
    if verification.verification_policy_digest != policy.policy_digest or locked_test.verification_policy_digest != policy.policy_digest:
        raise TrainingDataInputError("MLCV production-model verification-policy lineage mismatch.")
    if locked_test.verification_record_digest != verification.content_digest:
        raise TrainingDataInputError("MLCV production-model locked-test/verification lineage mismatch.")
    frozen = verification.frozen_attempt
    member = next((v for v in committee.members if v.content_digest == frozen.committee_member_digest), None)
    if member is None:
        raise TrainingDataInputError("Frozen verification member is absent from FINAL1 committee.")
    candidate = next((v for v in final_selection.qualified_candidates if v.content_digest == frozen.final_candidate_digest), None)
    if candidate is None:
        raise TrainingDataInputError("Frozen verification candidate is absent from FINAL1 authority.")
    if locked_test.frozen_final_candidate_digest != candidate.content_digest or locked_test.frozen_committee_member_digest != member.content_digest:
        raise TrainingDataInputError("Locked E did not evaluate the frozen FINAL1 identity.")
    if locked_test.frozen_exported_model_sha256 != member.exported_model_sha256:
        raise TrainingDataInputError("Locked E model bytes differ from FINAL1 committee export.")
    published_sha = validate_digest(exported_model_sha256, name="exported_model_sha256")
    if published_sha != member.exported_model_sha256:
        raise TrainingDataInputError("Published production bytes differ from physically verified/locked-tested bytes.")
    return MlcvProductionModelRecord(
        campaign_plan_digest=campaign.content_digest,
        final_selection_record_digest=final_selection.content_digest,
        verification_record_digest=verification.content_digest,
        locked_test_record_digest=locked_test.content_digest,
        selected_final_candidate_digest=candidate.content_digest,
        selected_verification_attempt_digest=frozen.content_digest,
        selected_committee_member_digest=member.content_digest,
        run_plan_digest=candidate.final_run_plan_digest,
        run_id=candidate.final_run_id,
        seed=candidate.seed,
        checkpoint_sha256=candidate.checkpoint_sha256,
        checkpoint_epoch=candidate.checkpoint_epoch,
        target_head_name=member.target_head_name,
        model_inference_dtype=policy.model_inference_dtype,
        scientific_analysis_dtype=policy.scientific_analysis_dtype,
        exported_model_path=str(exported_model_path),
        exported_model_sha256=published_sha,
        byte_size=int(byte_size),
    )


def ordered_mlcv_physical_candidates(final_selection: Any, *, fallback_enabled: bool = True) -> tuple[Any, ...]:
    if getattr(final_selection, "outcome", None) != "production_candidate_selected":
        raise TrainingDataInputError("MLCV-VERIFY1 requires FINAL1 production-candidate evidence.")
    values = tuple(final_selection.qualified_candidates)
    if not values:
        raise TrainingDataInputError("MLCV-VERIFY1 requires at least one qualified final representative.")
    return values if fallback_enabled else values[:1]


def build_mlcv_verification_record(
    campaign: Any,
    final_selection: Any,
    committee: Any,
    policy: MlcvVerificationPolicy,
    attempts: Sequence[MlcvPhysicalVerificationAttemptRecord],
) -> MlcvVerificationRecord:
    if final_selection.campaign_plan_digest != campaign.content_digest or committee.campaign_plan_digest != campaign.content_digest:
        raise TrainingDataInputError("MLCV-VERIFY1 campaign lineage mismatch.")
    if committee.final_selection_record_digest != final_selection.content_digest:
        raise TrainingDataInputError("MLCV-VERIFY1 committee/final-selection lineage mismatch.")
    candidate_order = ordered_mlcv_physical_candidates(
        final_selection, fallback_enabled=policy.fallback_to_next_qualified_final_seed
    )
    member_by_candidate = {v.final_candidate_digest: v for v in committee.members}
    attempts = tuple(attempts)
    if not attempts:
        raise TrainingDataInputError("MLCV-VERIFY1 requires physical-verification attempts.")
    if len(attempts) > len(candidate_order):
        raise TrainingDataInputError("MLCV-VERIFY1 attempt count exceeds authorized qualified final candidates.")
    for index, attempt in enumerate(attempts, start=1):
        candidate = candidate_order[index - 1]
        member = member_by_candidate.get(candidate.content_digest)
        if member is None:
            raise TrainingDataInputError("MLCV-VERIFY1 candidate is absent from qualified FINAL1 committee.")
        if attempt.candidate_rank != index or attempt.final_candidate_digest != candidate.content_digest or attempt.committee_member_digest != member.content_digest:
            raise TrainingDataInputError("MLCV-VERIFY1 attempt order/identity differs from FINAL1 authority.")
        if attempt.final_run_plan_digest != candidate.final_run_plan_digest or attempt.seed != candidate.seed:
            raise TrainingDataInputError("MLCV-VERIFY1 attempt final-run lineage mismatch.")
        if attempt.checkpoint_sha256 != candidate.checkpoint_sha256 or attempt.checkpoint_epoch != candidate.checkpoint_epoch:
            raise TrainingDataInputError("MLCV-VERIFY1 cannot substitute another checkpoint during physical fallback.")
        if attempt.exported_model_sha256 != member.exported_model_sha256:
            raise TrainingDataInputError("MLCV-VERIFY1 attempt model bytes differ from the qualified FINAL1 export.")
        if attempt.verification_policy_digest != policy.policy_digest:
            raise TrainingDataInputError("MLCV-VERIFY1 attempt policy mismatch.")
        if attempt.passed and index != len(attempts):
            raise TrainingDataInputError("MLCV-VERIFY1 may not continue after the first physical passer.")
    passed = attempts[-1].passed
    if not passed and len(attempts) != len(candidate_order):
        raise TrainingDataInputError("MLCV-VERIFY1 failed evidence is incomplete; authorized fallback candidates remain untested.")
    frozen = attempts[-1] if passed else None
    return MlcvVerificationRecord(
        campaign_plan_digest=campaign.content_digest,
        final_selection_record_digest=final_selection.content_digest,
        final_committee_record_digest=committee.content_digest,
        verification_policy_digest=policy.policy_digest,
        attempts=attempts,
        outcome="physical_candidate_frozen" if passed else "no_candidate_passed",
        frozen_attempt_digest=None if frozen is None else frozen.content_digest,
        frozen_final_candidate_digest=None if frozen is None else frozen.final_candidate_digest,
        frozen_committee_member_digest=None if frozen is None else frozen.committee_member_digest,
    )


def _locked_target_safety_reasons(target: Any, retained_policy: Any) -> list[str]:
    reasons: list[str] = []
    if retained_policy.maximum_energy_mae_ev_per_atom is not None:
        if target.energy_mae_ev_per_atom is None:
            reasons.append("missing_energy_mae")
        elif target.energy_mae_ev_per_atom > retained_policy.maximum_energy_mae_ev_per_atom:
            reasons.append("energy_mae_threshold_exceeded")
    if retained_policy.maximum_focus_force_rmse_ev_per_angstrom is not None:
        values = tuple(v for _, v in target.focus_force_rmse_ev_per_angstrom)
        if not values:
            reasons.append("missing_focus_force_rmse")
        elif max(values) > retained_policy.maximum_focus_force_rmse_ev_per_angstrom:
            reasons.append("focus_force_rmse_threshold_exceeded")
    if retained_policy.maximum_stress_rmse_ev_per_angstrom3 is not None:
        if target.stress_rmse_ev_per_angstrom3 is None:
            reasons.append("missing_stress_rmse")
        elif target.stress_rmse_ev_per_angstrom3 > retained_policy.maximum_stress_rmse_ev_per_angstrom3:
            reasons.append("stress_rmse_threshold_exceeded")
    if (
        retained_policy.maximum_worst_condition_force_rmse_ev_per_angstrom is not None
        and target.worst_condition_force_rmse_ev_per_angstrom
        > retained_policy.maximum_worst_condition_force_rmse_ev_per_angstrom
    ):
        reasons.append("worst_condition_force_rmse_threshold_exceeded")
    return reasons


def build_mlcv_locked_test_record(
    campaign: Any,
    final_selection: Any,
    committee: Any,
    verification: MlcvVerificationRecord,
    policy: MlcvVerificationPolicy,
    evaluation: Any,
    retained_policy: Any,
    *,
    sealed_evaluation_artifact_digest: str,
    locked_test_artifact_digest: str,
    locked_test_sha256: str,
) -> MlcvLockedTestRecord:
    if verification.outcome != "physical_candidate_frozen" or verification.frozen_attempt is None:
        raise TrainingDataInputError("Locked E may activate only after one physical-verification candidate is frozen.")
    if verification.campaign_plan_digest != campaign.content_digest or verification.final_selection_record_digest != final_selection.content_digest:
        raise TrainingDataInputError("MLCV locked-test campaign/final-selection lineage mismatch.")
    if verification.final_committee_record_digest != committee.content_digest or verification.verification_policy_digest != policy.policy_digest:
        raise TrainingDataInputError("MLCV locked-test verification/committee lineage mismatch.")
    frozen = verification.frozen_attempt
    member = next((v for v in committee.members if v.content_digest == frozen.committee_member_digest), None)
    if member is None:
        raise TrainingDataInputError("Frozen MLCV verification member is absent from FINAL1 committee.")
    if evaluation.run_plan_digest != frozen.final_run_plan_digest:
        raise TrainingDataInputError("Locked E evaluation belongs to a different final run.")
    if evaluation.candidate_model_sha256 != member.exported_model_sha256 or evaluation.checkpoint_sha256 != member.exported_model_sha256:
        raise TrainingDataInputError("Locked E must evaluate the exact frozen exported model bytes.")
    if evaluation.target_monitor_artifact_digest != validate_digest(locked_test_artifact_digest, name="locked_test_artifact_digest"):
        raise TrainingDataInputError("Locked E evaluation artifact lineage mismatch.")
    if evaluation.target_monitor_sha256 != validate_digest(locked_test_sha256, name="locked_test_sha256"):
        raise TrainingDataInputError("Locked E evaluation bytes changed.")
    if evaluation.replay_configuration_count != 0 or evaluation.replay_monitor_artifact_digest is not None:
        raise TrainingDataInputError("Locked E is target-only post-freeze evidence; replay cannot enter this gate.")
    target = evaluation.target_candidate_metrics
    if target is None:
        raise TrainingDataInputError("Locked E evaluation requires target metrics.")
    expected_metric = policy.retained_checkpoint_metric_policy_digest
    if expected_metric is not None and retained_policy.policy_digest != expected_metric:
        raise TrainingDataInputError("Locked E retained metric-policy digest mismatch.")
    rmse = float(target.force_component_rmse_ev_per_angstrom)
    reasons: list[str] = []
    if rmse > policy.maximum_target_force_rmse_ev_per_angstrom:
        reasons.append("target_force_rmse_threshold_exceeded")
    reasons.extend(_locked_target_safety_reasons(target, retained_policy))
    return MlcvLockedTestRecord(
        campaign_plan_digest=campaign.content_digest,
        final_selection_record_digest=final_selection.content_digest,
        verification_record_digest=verification.content_digest,
        verification_policy_digest=policy.policy_digest,
        frozen_final_candidate_digest=frozen.final_candidate_digest,
        frozen_committee_member_digest=frozen.committee_member_digest,
        frozen_exported_model_sha256=member.exported_model_sha256,
        locked_test_role=MlcvDataRole.TARGET_LOCKED_TEST,
        sealed_evaluation_artifact_digest=sealed_evaluation_artifact_digest,
        locked_test_artifact_digest=locked_test_artifact_digest,
        locked_test_sha256=locked_test_sha256,
        evaluation_record_digest=evaluation.content_digest,
        target_force_rmse_ev_per_angstrom=rmse,
        passed=not reasons,
        rejection_reasons=tuple(reasons),
    )


__all__ = [
    "MLCV_VERIFICATION_POLICY_SCHEMA", "MLCV_PHYSICAL_ATTEMPT_SCHEMA", "MLCV_VERIFICATION_RECORD_SCHEMA",
    "MLCV_LOCKED_TEST_RECORD_SCHEMA", "MLCV_PRODUCTION_MODEL_SCHEMA", "MlcvVerificationPolicy",
    "MlcvPhysicalVerificationAttemptRecord", "MlcvVerificationRecord", "MlcvLockedTestRecord",
    "MlcvProductionModelRecord", "ordered_mlcv_physical_candidates", "build_mlcv_verification_record",
    "build_mlcv_locked_test_record", "build_mlcv_production_model_record",
]
