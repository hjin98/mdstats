"""TRAIN2 one-shot locked post-freeze test and final production publication.

LOCKED-TEST2 is deliberately post-selection.  SELECT2 has already frozen one
production candidate before this module can activate.  The locked target domain
may accept or reject those exact bytes, but it has no API that can rank, select,
or fall back to a different seed/checkpoint/target size.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence
import math

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .eval2 import Eval2TargetMetricRecord

LOCKED_TEST2_VERSION = "0.20.177a0"
LOCKED_TEST2_POLICY_SCHEMA = "mdstats.locked-test2-policy.v1"
LOCKED_TEST2_ACTIVATION_SCHEMA = "mdstats.locked-test2-activation.v1"
LOCKED_TEST2_RESULT_SCHEMA = "mdstats.locked-test2-result.v1"
LOCKED_TEST2_PRODUCTION_SCHEMA = "mdstats.locked-test2-production-model.v1"


def _optional_nonnegative(value: float | None, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise TrainingDataInputError(f"{name} must be finite and nonnegative when present.")
    return result


def _check_digest(payload: Mapping[str, Any], current: str, *, name: str) -> None:
    observed = payload.get("content_digest")
    if observed not in (None, current):
        raise TrainingDataSerializationError(f"{name} content digest mismatch.")


@dataclass(frozen=True, slots=True)
class LockedTest2Policy:
    """One-shot locked-E pass/fail policy with no selection authority."""

    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    maximum_energy_mae_ev_per_atom: float | None = None
    maximum_worst_stratum_force_rmse_ev_per_angstrom: float | None = None
    maximum_force_error_p99_ev_per_angstrom: float | None = None
    maximum_stress_rmse_ev_per_angstrom3: float | None = None
    exact_once: bool = True
    replay_allowed: bool = False
    alternative_selection_allowed: bool = False
    serialization_schema: str = field(default=LOCKED_TEST2_POLICY_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != LOCKED_TEST2_POLICY_SCHEMA:
            raise TrainingDataInputError("Unsupported LOCKED-TEST2 policy schema.")
        force = float(self.maximum_target_force_rmse_ev_per_angstrom)
        if not math.isfinite(force) or force <= 0.0:
            raise TrainingDataInputError("LOCKED-TEST2 target force RMSE ceiling must be finite and positive.")
        object.__setattr__(self, "maximum_target_force_rmse_ev_per_angstrom", force)
        for name in (
            "maximum_energy_mae_ev_per_atom",
            "maximum_worst_stratum_force_rmse_ev_per_angstrom",
            "maximum_force_error_p99_ev_per_angstrom",
            "maximum_stress_rmse_ev_per_angstrom3",
        ):
            object.__setattr__(self, name, _optional_nonnegative(getattr(self, name), name=f"LOCKED-TEST2 {name}"))
        if not self.exact_once or self.replay_allowed or self.alternative_selection_allowed:
            raise TrainingDataInputError(
                "LOCKED-TEST2 v1 must be one-shot, target-only, and unable to select an alternative."
            )

    def rejection_reasons(self, metrics: Eval2TargetMetricRecord) -> tuple[str, ...]:
        reasons: list[str] = []
        if metrics.force_component_rmse_ev_per_angstrom > self.maximum_target_force_rmse_ev_per_angstrom:
            reasons.append("target_force_rmse_threshold_exceeded")
        if self.maximum_energy_mae_ev_per_atom is not None and metrics.energy_mae_ev_per_atom > self.maximum_energy_mae_ev_per_atom:
            reasons.append("energy_mae_threshold_exceeded")
        if self.maximum_worst_stratum_force_rmse_ev_per_angstrom is not None:
            observed = metrics.worst_stratum_force_rmse_ev_per_angstrom
            if observed is None:
                reasons.append("worst_stratum_metric_missing")
            elif observed > self.maximum_worst_stratum_force_rmse_ev_per_angstrom:
                reasons.append("worst_stratum_force_rmse_threshold_exceeded")
        if self.maximum_force_error_p99_ev_per_angstrom is not None and metrics.force_error_p99_ev_per_angstrom > self.maximum_force_error_p99_ev_per_angstrom:
            reasons.append("force_error_p99_threshold_exceeded")
        if self.maximum_stress_rmse_ev_per_angstrom3 is not None:
            observed_stress = metrics.stress_rmse_ev_per_angstrom3
            if observed_stress is None:
                reasons.append("stress_metric_missing")
            elif observed_stress > self.maximum_stress_rmse_ev_per_angstrom3:
                reasons.append("stress_rmse_threshold_exceeded")
        return tuple(reasons)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "maximum_energy_mae_ev_per_atom": self.maximum_energy_mae_ev_per_atom,
            "maximum_worst_stratum_force_rmse_ev_per_angstrom": self.maximum_worst_stratum_force_rmse_ev_per_angstrom,
            "maximum_force_error_p99_ev_per_angstrom": self.maximum_force_error_p99_ev_per_angstrom,
            "maximum_stress_rmse_ev_per_angstrom3": self.maximum_stress_rmse_ev_per_angstrom3,
            "exact_once": True,
            "replay_allowed": False,
            "alternative_selection_allowed": False,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LockedTest2Policy":
        if payload.get("schema") != LOCKED_TEST2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LOCKED-TEST2 policy schema.")
        result = cls(
            maximum_target_force_rmse_ev_per_angstrom=float(payload["maximum_target_force_rmse_ev_per_angstrom"]),
            maximum_energy_mae_ev_per_atom=None if payload.get("maximum_energy_mae_ev_per_atom") is None else float(payload["maximum_energy_mae_ev_per_atom"]),
            maximum_worst_stratum_force_rmse_ev_per_angstrom=None if payload.get("maximum_worst_stratum_force_rmse_ev_per_angstrom") is None else float(payload["maximum_worst_stratum_force_rmse_ev_per_angstrom"]),
            maximum_force_error_p99_ev_per_angstrom=None if payload.get("maximum_force_error_p99_ev_per_angstrom") is None else float(payload["maximum_force_error_p99_ev_per_angstrom"]),
            maximum_stress_rmse_ev_per_angstrom3=None if payload.get("maximum_stress_rmse_ev_per_angstrom3") is None else float(payload["maximum_stress_rmse_ev_per_angstrom3"]),
            exact_once=bool(payload.get("exact_once", True)),
            replay_allowed=bool(payload.get("replay_allowed", False)),
            alternative_selection_allowed=bool(payload.get("alternative_selection_allowed", False)),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("LOCKED-TEST2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LockedTest2ActivationRecord:
    """Immutable scientific activation of locked E for exactly one SELECT2 candidate."""

    campaign_plan_digest: str
    select2_selection_digest: str
    select2_frozen_candidate_digest: str
    target_data_role_freeze_digest: str
    run_plan_digest: str
    optimizer_seed: int
    label_domain_id: str
    frozen_target_model_sha256: str
    frozen_mliap_artifact_sha256: str
    policy: LockedTest2Policy
    sealed_locked_role_digest: str
    locked_artifact_digest: str
    locked_artifact_sha256: str
    locked_artifact_path: str
    locked_frame_uids: tuple[str, ...]
    locked_unit_ids: tuple[str, ...]
    correlation_block_ids: tuple[str, ...]
    activated_at_utc: str
    serialization_schema: str = field(default=LOCKED_TEST2_ACTIVATION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != LOCKED_TEST2_ACTIVATION_SCHEMA:
            raise TrainingDataInputError("Unsupported LOCKED-TEST2 activation schema.")
        for name in (
            "campaign_plan_digest", "select2_selection_digest", "select2_frozen_candidate_digest",
            "target_data_role_freeze_digest", "run_plan_digest", "frozen_target_model_sha256",
            "frozen_mliap_artifact_sha256", "sealed_locked_role_digest", "locked_artifact_digest",
            "locked_artifact_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.optimizer_seed) < 0:
            raise TrainingDataInputError("LOCKED-TEST2 optimizer seed must be nonnegative.")
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        if not self.label_domain_id.strip() or not self.locked_artifact_path.strip() or not self.activated_at_utc.strip():
            raise TrainingDataInputError("LOCKED-TEST2 activation identifiers/paths/timestamp must be non-empty.")
        frames = tuple(validate_digest(v, name="locked_frame_uid") for v in self.locked_frame_uids)
        units = tuple(validate_digest(v, name="locked_unit_id") for v in self.locked_unit_ids)
        blocks = tuple(validate_digest(v, name="correlation_block_id") for v in self.correlation_block_ids)
        if not frames or not units or len(blocks) != len(frames):
            raise TrainingDataInputError("LOCKED-TEST2 activation requires non-empty locked frames/units and one block per frame.")
        if len(set(frames)) != len(frames):
            raise TrainingDataInputError("LOCKED-TEST2 locked frame membership contains duplicates.")
        if any(block not in set(units) for block in blocks):
            raise TrainingDataInputError("LOCKED-TEST2 correlation blocks must belong to locked partition units.")
        object.__setattr__(self, "locked_frame_uids", frames)
        object.__setattr__(self, "locked_unit_ids", units)
        object.__setattr__(self, "correlation_block_ids", blocks)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "select2_selection_digest": self.select2_selection_digest,
            "select2_frozen_candidate_digest": self.select2_frozen_candidate_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "run_plan_digest": self.run_plan_digest,
            "optimizer_seed": self.optimizer_seed,
            "label_domain_id": self.label_domain_id,
            "frozen_target_model_sha256": self.frozen_target_model_sha256,
            "frozen_mliap_artifact_sha256": self.frozen_mliap_artifact_sha256,
            "policy": self.policy.to_dict(),
            "sealed_locked_role_digest": self.sealed_locked_role_digest,
            "locked_artifact_digest": self.locked_artifact_digest,
            "locked_artifact_sha256": self.locked_artifact_sha256,
            "locked_artifact_path": self.locked_artifact_path,
            "locked_frame_uids": list(self.locked_frame_uids),
            "locked_unit_ids": list(self.locked_unit_ids),
            "correlation_block_ids": list(self.correlation_block_ids),
            "activated_at_utc": self.activated_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LockedTest2ActivationRecord":
        if payload.get("schema") != LOCKED_TEST2_ACTIVATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LOCKED-TEST2 activation schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            select2_selection_digest=str(payload["select2_selection_digest"]),
            select2_frozen_candidate_digest=str(payload["select2_frozen_candidate_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            label_domain_id=str(payload["label_domain_id"]),
            frozen_target_model_sha256=str(payload["frozen_target_model_sha256"]),
            frozen_mliap_artifact_sha256=str(payload["frozen_mliap_artifact_sha256"]),
            policy=LockedTest2Policy.from_dict(payload["policy"]),
            sealed_locked_role_digest=str(payload["sealed_locked_role_digest"]),
            locked_artifact_digest=str(payload["locked_artifact_digest"]),
            locked_artifact_sha256=str(payload["locked_artifact_sha256"]),
            locked_artifact_path=str(payload["locked_artifact_path"]),
            locked_frame_uids=tuple(str(v) for v in payload["locked_frame_uids"]),
            locked_unit_ids=tuple(str(v) for v in payload["locked_unit_ids"]),
            correlation_block_ids=tuple(str(v) for v in payload["correlation_block_ids"]),
            activated_at_utc=str(payload["activated_at_utc"]),
        )
        _check_digest(payload, result.content_digest, name="LOCKED-TEST2 activation")
        return result


@dataclass(frozen=True, slots=True)
class LockedTest2ResultRecord:
    activation_digest: str
    frozen_target_model_sha256: str
    target_metrics: Eval2TargetMetricRecord
    prediction_digest: str
    passed: bool
    rejection_reasons: tuple[str, ...]
    evaluated_at_utc: str
    serialization_schema: str = field(default=LOCKED_TEST2_RESULT_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != LOCKED_TEST2_RESULT_SCHEMA:
            raise TrainingDataInputError("Unsupported LOCKED-TEST2 result schema.")
        object.__setattr__(self, "activation_digest", validate_digest(self.activation_digest, name="activation_digest"))
        object.__setattr__(self, "frozen_target_model_sha256", validate_digest(self.frozen_target_model_sha256, name="frozen_target_model_sha256"))
        object.__setattr__(self, "prediction_digest", validate_digest(self.prediction_digest, name="prediction_digest"))
        reasons = tuple(sorted(set(str(v) for v in self.rejection_reasons)))
        object.__setattr__(self, "rejection_reasons", reasons)
        if bool(self.passed) != (len(reasons) == 0):
            raise TrainingDataInputError("LOCKED-TEST2 pass flag disagrees with rejection reasons.")
        if not self.evaluated_at_utc.strip():
            raise TrainingDataInputError("LOCKED-TEST2 result requires evaluation timestamp.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "activation_digest": self.activation_digest,
            "frozen_target_model_sha256": self.frozen_target_model_sha256,
            "target_metrics": self.target_metrics.to_dict(),
            "prediction_digest": self.prediction_digest,
            "passed": self.passed,
            "rejection_reasons": list(self.rejection_reasons),
            "evaluated_at_utc": self.evaluated_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LockedTest2ResultRecord":
        if payload.get("schema") != LOCKED_TEST2_RESULT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LOCKED-TEST2 result schema.")
        result = cls(
            activation_digest=str(payload["activation_digest"]),
            frozen_target_model_sha256=str(payload["frozen_target_model_sha256"]),
            target_metrics=Eval2TargetMetricRecord.from_dict(payload["target_metrics"]),
            prediction_digest=str(payload["prediction_digest"]),
            passed=bool(payload["passed"]),
            rejection_reasons=tuple(str(v) for v in payload.get("rejection_reasons", ())),
            evaluated_at_utc=str(payload["evaluated_at_utc"]),
        )
        _check_digest(payload, result.content_digest, name="LOCKED-TEST2 result")
        return result


@dataclass(frozen=True, slots=True)
class LockedTest2ProductionModelRecord:
    campaign_plan_digest: str
    select2_frozen_candidate_digest: str
    locked_test_activation_digest: str
    locked_test_result_digest: str
    run_plan_digest: str
    optimizer_seed: int
    checkpoint_sha256: str
    checkpoint_epoch: int
    target_model_path: str
    target_model_sha256: str
    target_model_byte_size: int
    mliap_artifact_path: str
    mliap_artifact_sha256: str
    mliap_artifact_byte_size: int
    published_at_utc: str
    serialization_schema: str = field(default=LOCKED_TEST2_PRODUCTION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != LOCKED_TEST2_PRODUCTION_SCHEMA:
            raise TrainingDataInputError("Unsupported LOCKED-TEST2 production schema.")
        for name in (
            "campaign_plan_digest", "select2_frozen_candidate_digest", "locked_test_activation_digest",
            "locked_test_result_digest", "run_plan_digest", "checkpoint_sha256", "target_model_sha256",
            "mliap_artifact_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if int(self.optimizer_seed) < 0 or int(self.checkpoint_epoch) < 0:
            raise TrainingDataInputError("LOCKED-TEST2 production seed/epoch must be nonnegative.")
        if int(self.target_model_byte_size) <= 0 or int(self.mliap_artifact_byte_size) <= 0:
            raise TrainingDataInputError("LOCKED-TEST2 production artifacts must have positive byte sizes.")
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        object.__setattr__(self, "checkpoint_epoch", int(self.checkpoint_epoch))
        object.__setattr__(self, "target_model_byte_size", int(self.target_model_byte_size))
        object.__setattr__(self, "mliap_artifact_byte_size", int(self.mliap_artifact_byte_size))
        if not self.target_model_path.strip() or not self.mliap_artifact_path.strip() or not self.published_at_utc.strip():
            raise TrainingDataInputError("LOCKED-TEST2 production paths/timestamp must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "select2_frozen_candidate_digest": self.select2_frozen_candidate_digest,
            "locked_test_activation_digest": self.locked_test_activation_digest,
            "locked_test_result_digest": self.locked_test_result_digest,
            "run_plan_digest": self.run_plan_digest,
            "optimizer_seed": self.optimizer_seed,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "target_model_path": self.target_model_path,
            "target_model_sha256": self.target_model_sha256,
            "target_model_byte_size": self.target_model_byte_size,
            "mliap_artifact_path": self.mliap_artifact_path,
            "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "mliap_artifact_byte_size": self.mliap_artifact_byte_size,
            "published_at_utc": self.published_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LockedTest2ProductionModelRecord":
        if payload.get("schema") != LOCKED_TEST2_PRODUCTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LOCKED-TEST2 production schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            select2_frozen_candidate_digest=str(payload["select2_frozen_candidate_digest"]),
            locked_test_activation_digest=str(payload["locked_test_activation_digest"]),
            locked_test_result_digest=str(payload["locked_test_result_digest"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            checkpoint_epoch=int(payload["checkpoint_epoch"]),
            target_model_path=str(payload["target_model_path"]),
            target_model_sha256=str(payload["target_model_sha256"]),
            target_model_byte_size=int(payload["target_model_byte_size"]),
            mliap_artifact_path=str(payload["mliap_artifact_path"]),
            mliap_artifact_sha256=str(payload["mliap_artifact_sha256"]),
            mliap_artifact_byte_size=int(payload["mliap_artifact_byte_size"]),
            published_at_utc=str(payload["published_at_utc"]),
        )
        _check_digest(payload, result.content_digest, name="LOCKED-TEST2 production model")
        return result


def build_locked_test2_result(
    activation: LockedTest2ActivationRecord,
    metrics: Eval2TargetMetricRecord,
    *,
    prediction_digest: str,
    evaluated_at_utc: str,
) -> LockedTest2ResultRecord:
    if metrics.target_role_digest != activation.content_digest:
        raise TrainingDataInputError("LOCKED-TEST2 metric role identity must be the activation digest.")
    reasons = activation.policy.rejection_reasons(metrics)
    return LockedTest2ResultRecord(
        activation_digest=activation.content_digest,
        frozen_target_model_sha256=activation.frozen_target_model_sha256,
        target_metrics=metrics,
        prediction_digest=prediction_digest,
        passed=not reasons,
        rejection_reasons=reasons,
        evaluated_at_utc=evaluated_at_utc,
    )


__all__ = [
    "LOCKED_TEST2_VERSION", "LOCKED_TEST2_POLICY_SCHEMA", "LOCKED_TEST2_ACTIVATION_SCHEMA",
    "LOCKED_TEST2_RESULT_SCHEMA", "LOCKED_TEST2_PRODUCTION_SCHEMA", "LockedTest2Policy",
    "LockedTest2ActivationRecord", "LockedTest2ResultRecord", "LockedTest2ProductionModelRecord",
    "build_locked_test2_result",
]
