"""Complete fixed-file MACE training-protocol identities and job artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
import math

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .acceleration import MaceAccelerationPolicy, MaceAccelerationKernelMode
from .adaptive_stop import AdaptiveTrainingStopPolicy
from .train2_policy import (
    TrainingBudgetPolicy, LearningRateSchedulePolicy, CheckpointAdmissibilityPolicy,
    CheckpointSelectionPolicy, validate_train2_policy_set,
)
from .critical_precision import MaceCriticalPrecisionPolicy
from .precision_schedule import PrecisionSchedulePolicy, ResolvedPrecisionSchedule
from .mace_compatibility import MaceCheckpointControlPolicy, MaceExposureBackend, MaceLoaderDryRun, MaceSourceProbe
from .replay import ReplayPreparationPlan, ReplayMode
from .foundation import FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA, FoundationCheckpointIdentity

MACE_OPTIMIZER_POLICY_SCHEMA = "mdstats.mace-optimizer-policy.v6"
MACE_OPTIMIZER_POLICY_V5_SCHEMA = "mdstats.mace-optimizer-policy.v5"
MACE_OPTIMIZER_POLICY_V4_SCHEMA = "mdstats.mace-optimizer-policy.v4"
MACE_OPTIMIZER_POLICY_V3_SCHEMA = "mdstats.mace-optimizer-policy.v3"
MACE_OPTIMIZER_POLICY_V2_SCHEMA = "mdstats.mace-optimizer-policy.v2"
MACE_OPTIMIZER_POLICY_LEGACY_SCHEMA = "mdstats.mace-optimizer-policy.v1"
TRAINING_PROTOCOL_IDENTITY_SCHEMA = "mdstats.training-protocol-identity.v7"
TRAINING_PROTOCOL_IDENTITY_V6_SCHEMA = "mdstats.training-protocol-identity.v6"
TRAINING_PROTOCOL_IDENTITY_V5_SCHEMA = "mdstats.training-protocol-identity.v5"
TRAINING_PROTOCOL_IDENTITY_V4_SCHEMA = "mdstats.training-protocol-identity.v4"
TRAINING_PROTOCOL_IDENTITY_V3_SCHEMA = "mdstats.training-protocol-identity.v3"
TRAINING_PROTOCOL_IDENTITY_V2_SCHEMA = "mdstats.training-protocol-identity.v2"
MACE_JOB_ARTIFACT_SCHEMA = "mdstats.mace-job-artifact.v1"
SEALED_EVALUATION_ARTIFACT_SCHEMA = "mdstats.sealed-evaluation-artifact.v1"


class TrainingMode(str, Enum):
    NAIVE_FINE_TUNING = "naive_fine_tuning"
    MULTIHEAD_REPLAY = "multihead_replay"


class MaceJobKind(str, Enum):
    FINAL_DEVELOPMENT = "final_development"
    CROSS_VALIDATION_FOLD = "cross_validation_fold"


@dataclass(frozen=True, slots=True)
class MaceOptimizerPolicy:
    learning_rate: float = 1.0e-4
    batch_size: int = 1
    valid_batch_size: int = 1
    num_workers: int = 0
    max_num_epochs: int = 30
    eval_interval: int = 1
    ema: bool = True
    ema_decay: float = 0.99999
    amsgrad: bool = True
    weight_decay: float = 1.0e-6
    clip_grad: float = 10.0
    default_dtype: str = "float64"
    device: str = "cuda"
    seed: int = 1
    critical_precision_policy: MaceCriticalPrecisionPolicy = field(
        default_factory=MaceCriticalPrecisionPolicy
    )
    acceleration_policy: MaceAccelerationPolicy = field(
        default_factory=MaceAccelerationPolicy
    )
    acceleration_realization_digest: str | None = None
    resolved_acceleration_kernel_mode: str | None = None
    precision_schedule_policy: PrecisionSchedulePolicy | None = None

    def __post_init__(self) -> None:
        if self.learning_rate <= 0.0 or self.batch_size <= 0 or self.valid_batch_size <= 0:
            raise TrainingDataInputError("MACE optimizer sizes and learning rate must be positive.")
        if self.num_workers < 0:
            raise TrainingDataInputError("MACE num_workers must be non-negative.")
        if self.max_num_epochs <= 0 or self.eval_interval <= 0 or self.seed < 0:
            raise TrainingDataInputError("MACE epoch and seed settings are invalid.")
        if not (0.0 < self.ema_decay < 1.0) or self.weight_decay < 0.0 or self.clip_grad <= 0.0:
            raise TrainingDataInputError("MACE optimizer regularization settings are invalid.")
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Unsupported MACE dtype.")
        if (self.acceleration_realization_digest is None) != (self.resolved_acceleration_kernel_mode is None):
            raise TrainingDataInputError(
                "MACE optimizer acceleration realization digest/mode must be both present or both absent."
            )
        if self.acceleration_realization_digest is not None:
            object.__setattr__(
                self, "acceleration_realization_digest",
                validate_digest(self.acceleration_realization_digest, name="acceleration_realization_digest")
            )
            mode = MaceAccelerationKernelMode(str(self.resolved_acceleration_kernel_mode))
            if mode is MaceAccelerationKernelMode.CUEQ_UNRESOLVED:
                raise TrainingDataInputError("MACE optimizer cannot bind an unresolved CuEq realization.")
            if mode.backend is not self.acceleration_policy.backend:
                raise TrainingDataInputError("MACE optimizer acceleration realization/backend mismatch.")
            if (
                self.acceleration_policy.backend.value == "cueq"
                and mode is not MaceAccelerationKernelMode.CUEQ_PURE
            ):
                raise TrainingDataInputError(
                    "MACE 0.3.16 training supports the qualified pure-CuEq training kernel only; "
                    "CuEq+OEQ hybrid is inference-only."
                )
            object.__setattr__(self, "resolved_acceleration_kernel_mode", mode.value)
        if self.precision_schedule_policy is not None:
            if self.precision_schedule_policy.stages[0].dtype != self.default_dtype:
                raise TrainingDataInputError(
                    "MACE default_dtype must equal the first configured precision stage dtype."
                )
            if (
                self.precision_schedule_policy.critical_operation_dtype
                != self.critical_precision_policy.canonical_dtype
            ):
                raise TrainingDataInputError(
                    "MACE critical-precision policy dtype must equal the configured "
                    "precision schedule critical_operation_dtype."
                )

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": (
                MACE_OPTIMIZER_POLICY_SCHEMA
                if self.acceleration_realization_digest is not None
                else MACE_OPTIMIZER_POLICY_V5_SCHEMA
                if self.precision_schedule_policy is not None
                else MACE_OPTIMIZER_POLICY_V4_SCHEMA
            ),
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "valid_batch_size": self.valid_batch_size,
            "num_workers": self.num_workers,
            "max_num_epochs": self.max_num_epochs,
            "eval_interval": self.eval_interval,
            "ema": self.ema,
            "ema_decay": self.ema_decay,
            "amsgrad": self.amsgrad,
            "weight_decay": self.weight_decay,
            "clip_grad": self.clip_grad,
            "default_dtype": self.default_dtype,
            "device": self.device,
            "seed": self.seed,
            "critical_precision_policy": self.critical_precision_policy.to_dict(),
            "acceleration_policy": self.acceleration_policy.to_dict(),
        }
        if self.acceleration_realization_digest is not None:
            payload["acceleration_realization_digest"] = self.acceleration_realization_digest
            payload["resolved_acceleration_kernel_mode"] = self.resolved_acceleration_kernel_mode
        if self.precision_schedule_policy is not None:
            payload["precision_schedule_policy"] = self.precision_schedule_policy.to_dict()
        return payload

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceOptimizerPolicy":
        schema = payload.get("schema")
        if schema not in {
            MACE_OPTIMIZER_POLICY_SCHEMA,
            MACE_OPTIMIZER_POLICY_V5_SCHEMA,
            MACE_OPTIMIZER_POLICY_V4_SCHEMA,
            MACE_OPTIMIZER_POLICY_V3_SCHEMA,
            MACE_OPTIMIZER_POLICY_V2_SCHEMA,
            MACE_OPTIMIZER_POLICY_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported MACE optimizer schema.")
        result = cls(
            learning_rate=float(payload["learning_rate"]),
            batch_size=int(payload["batch_size"]),
            valid_batch_size=int(payload["valid_batch_size"]),
            num_workers=int(payload.get("num_workers", 0)),
            max_num_epochs=int(payload["max_num_epochs"]),
            eval_interval=int(payload["eval_interval"]),
            ema=bool(payload["ema"]),
            ema_decay=float(payload["ema_decay"]),
            amsgrad=bool(payload["amsgrad"]),
            weight_decay=float(payload["weight_decay"]),
            clip_grad=float(payload["clip_grad"]),
            default_dtype=str(payload["default_dtype"]),
            device=str(payload["device"]),
            seed=int(payload["seed"]),
            critical_precision_policy=(
                MaceCriticalPrecisionPolicy()
                if payload.get("critical_precision_policy") is None
                else MaceCriticalPrecisionPolicy.from_dict(
                    payload["critical_precision_policy"]
                )
            ),
            acceleration_policy=(
                MaceAccelerationPolicy()
                if payload.get("acceleration_policy") is None
                else MaceAccelerationPolicy.from_dict(payload["acceleration_policy"])
            ),
            acceleration_realization_digest=(
                None if payload.get("acceleration_realization_digest") is None
                else str(payload["acceleration_realization_digest"])
            ),
            resolved_acceleration_kernel_mode=(
                None if payload.get("resolved_acceleration_kernel_mode") is None
                else str(payload["resolved_acceleration_kernel_mode"])
            ),
            precision_schedule_policy=(
                None
                if payload.get("precision_schedule_policy") is None
                else PrecisionSchedulePolicy.from_dict(payload["precision_schedule_policy"])
            ),
        )
        expected_digest = result.policy_digest
        if schema in {MACE_OPTIMIZER_POLICY_V5_SCHEMA, MACE_OPTIMIZER_POLICY_V4_SCHEMA, MACE_OPTIMIZER_POLICY_V3_SCHEMA, MACE_OPTIMIZER_POLICY_V2_SCHEMA, MACE_OPTIMIZER_POLICY_LEGACY_SCHEMA}:
            legacy_payload = {
                "schema": schema,
                "learning_rate": result.learning_rate,
                "batch_size": result.batch_size,
                "valid_batch_size": result.valid_batch_size,
                "max_num_epochs": result.max_num_epochs,
                "eval_interval": result.eval_interval,
                "ema": result.ema,
                "ema_decay": result.ema_decay,
                "amsgrad": result.amsgrad,
                "weight_decay": result.weight_decay,
                "clip_grad": result.clip_grad,
                "default_dtype": result.default_dtype,
                "device": result.device,
                "seed": result.seed,
            }
            if schema in {MACE_OPTIMIZER_POLICY_V5_SCHEMA, MACE_OPTIMIZER_POLICY_V4_SCHEMA}:
                legacy_payload["num_workers"] = result.num_workers
            if schema in {MACE_OPTIMIZER_POLICY_V5_SCHEMA, MACE_OPTIMIZER_POLICY_V4_SCHEMA, MACE_OPTIMIZER_POLICY_V3_SCHEMA, MACE_OPTIMIZER_POLICY_V2_SCHEMA}:
                legacy_payload["critical_precision_policy"] = result.critical_precision_policy.to_dict()
            if schema in {MACE_OPTIMIZER_POLICY_V5_SCHEMA, MACE_OPTIMIZER_POLICY_V4_SCHEMA, MACE_OPTIMIZER_POLICY_V3_SCHEMA}:
                legacy_payload["acceleration_policy"] = result.acceleration_policy.to_dict()
            if schema == MACE_OPTIMIZER_POLICY_V5_SCHEMA and result.precision_schedule_policy is not None:
                legacy_payload["precision_schedule_policy"] = result.precision_schedule_policy.to_dict()
            expected_digest = digest(
                legacy_payload
            )
        if payload.get("policy_digest") not in (None, expected_digest):
            raise TrainingDataSerializationError("MACE optimizer digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingProtocolIdentity:
    training_mode: TrainingMode
    foundation_checkpoint: FoundationCheckpointIdentity
    compatibility_probe_digest: str
    data7_bundle_digest: str
    target_train_artifact_digest: str
    target_valid_artifact_digest: str
    replay_plan_digest: str | None
    training_objective_policy_digest: str
    configuration_weight_policy_digest: str
    checkpoint_metric_policy_digest: str
    checkpoint_control_policy: MaceCheckpointControlPolicy
    optimizer_policy: MaceOptimizerPolicy
    selection_size: int
    exposure_backend: MaceExposureBackend = MaceExposureBackend.NATIVE_MACE_FIXED
    real_pt_data_ratio_threshold: float = 0.1
    resolved_precision_schedule: ResolvedPrecisionSchedule | None = None
    online_monitor_policy_digest: str | None = None
    target_online_monitor_record_digest: str | None = None
    replay_online_monitor_record_digest: str | None = None
    replay_valid_artifact_digest: str | None = None
    adaptive_stop_policy: AdaptiveTrainingStopPolicy | None = None
    training_budget_policy: TrainingBudgetPolicy | None = None
    learning_rate_schedule_policy: LearningRateSchedulePolicy | None = None
    checkpoint_admissibility_policy: CheckpointAdmissibilityPolicy | None = None
    checkpoint_selection_policy: CheckpointSelectionPolicy | None = None
    selected_head_qualification_digest: str | None = None
    training_foundation_checkpoint_reference: str | None = None
    training_foundation_checkpoint_sha256: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "training_mode", TrainingMode(self.training_mode))
        object.__setattr__(self, "exposure_backend", MaceExposureBackend(self.exposure_backend))
        for name in (
            "compatibility_probe_digest",
            "data7_bundle_digest",
            "target_train_artifact_digest",
            "target_valid_artifact_digest",
            "training_objective_policy_digest",
            "configuration_weight_policy_digest",
            "checkpoint_metric_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.replay_plan_digest is not None:
            object.__setattr__(self, "replay_plan_digest", validate_digest(self.replay_plan_digest, name="replay_plan_digest"))
        for name in (
            "online_monitor_policy_digest",
            "target_online_monitor_record_digest",
            "replay_online_monitor_record_digest",
            "replay_valid_artifact_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        training_foundation_fields = (
            self.selected_head_qualification_digest,
            self.training_foundation_checkpoint_reference,
            self.training_foundation_checkpoint_sha256,
        )
        if any(value is not None for value in training_foundation_fields) and any(value is None for value in training_foundation_fields):
            raise TrainingDataInputError(
                "Selected-head training foundation requires qualification digest, reference, and SHA together."
            )
        if self.selected_head_qualification_digest is not None:
            object.__setattr__(
                self,
                "selected_head_qualification_digest",
                validate_digest(self.selected_head_qualification_digest, name="selected_head_qualification_digest"),
            )
            reference = str(self.training_foundation_checkpoint_reference).strip()
            if not reference:
                raise TrainingDataInputError("Selected-head training checkpoint reference must be non-empty.")
            object.__setattr__(self, "training_foundation_checkpoint_reference", reference)
            object.__setattr__(
                self,
                "training_foundation_checkpoint_sha256",
                validate_digest(str(self.training_foundation_checkpoint_sha256), name="training_foundation_checkpoint_sha256"),
            )
        monitor_fields = (
            self.online_monitor_policy_digest,
            self.target_online_monitor_record_digest,
            self.replay_online_monitor_record_digest,
            self.replay_valid_artifact_digest,
        )
        if any(value is not None for value in monitor_fields) and any(value is None for value in monitor_fields):
            raise TrainingDataInputError(
                "ADAPT-MON1 protocol evidence requires policy, target record, replay record, and replay-valid artifact together."
            )
        train2_active = validate_train2_policy_set(
            budget=self.training_budget_policy,
            learning_rate=self.learning_rate_schedule_policy,
            admissibility=self.checkpoint_admissibility_policy,
            selection=self.checkpoint_selection_policy,
        )
        if train2_active and self.adaptive_stop_policy is not None:
            raise TrainingDataInputError(
                "TRAIN2 policy authority and historical AdaptiveTrainingStopPolicy are mutually exclusive."
            )
        if train2_active:
            if self.online_monitor_policy_digest is None:
                raise TrainingDataInputError("TRAIN2 requires authenticated target/replay monitor evidence.")
            if self.optimizer_policy.eval_interval != 1:
                raise TrainingDataInputError("TRAIN2 requires eval_interval=1 for complete checkpoint diagnostics.")
            assert self.training_budget_policy is not None
            assert self.learning_rate_schedule_policy is not None
            assert self.checkpoint_admissibility_policy is not None
            if self.training_budget_policy.planned_epochs != self.optimizer_policy.max_num_epochs:
                raise TrainingDataInputError("TRAIN2 epoch budget disagrees with optimizer policy.")
            if not math.isclose(
                self.learning_rate_schedule_policy.base_learning_rate,
                self.optimizer_policy.learning_rate,
                rel_tol=0.0, abs_tol=1e-18,
            ):
                raise TrainingDataInputError("TRAIN2 base LR disagrees with optimizer policy.")
            expected_replay = self.training_mode is TrainingMode.MULTIHEAD_REPLAY
            if bool(self.checkpoint_admissibility_policy.replay_enabled) != expected_replay:
                raise TrainingDataInputError("TRAIN2 replay admissibility disagrees with training mode.")
            if not self.checkpoint_control_policy.save_all_checkpoints:
                raise TrainingDataInputError("TRAIN2 requires durable per-epoch checkpoints.")

        if self.adaptive_stop_policy is not None:
            if self.online_monitor_policy_digest is None:
                raise TrainingDataInputError("ADAPT-STOP1 requires ADAPT-MON1 online-monitor evidence.")
            if self.optimizer_policy.eval_interval != 1:
                raise TrainingDataInputError("ADAPT-STOP1 requires eval_interval=1 so every epoch has monitor evidence.")
            expected_replay = self.training_mode is TrainingMode.MULTIHEAD_REPLAY
            if bool(self.adaptive_stop_policy.replay_enabled) != expected_replay:
                raise TrainingDataInputError("Adaptive-stop replay_enabled disagrees with the training mode.")
            if self.adaptive_stop_policy.max_num_epochs != self.optimizer_policy.max_num_epochs:
                raise TrainingDataInputError("Adaptive-stop epoch ceiling disagrees with optimizer policy.")
            if self.adaptive_stop_policy.target_head_name != self.checkpoint_control_policy.target_head_name:
                raise TrainingDataInputError("Adaptive-stop target head disagrees with checkpoint-control policy.")
            if (
                self.adaptive_stop_policy.replay_enabled
                and self.adaptive_stop_policy.replay_head_name != self.checkpoint_control_policy.replay_head_name
            ):
                raise TrainingDataInputError("Adaptive-stop replay head disagrees with checkpoint-control policy.")
            if not self.checkpoint_control_policy.save_all_checkpoints:
                raise TrainingDataInputError("ADAPT-STOP1 requires one durable checkpoint for every evaluated epoch.")
        if self.training_mode is TrainingMode.MULTIHEAD_REPLAY and self.replay_plan_digest is None:
            raise TrainingDataInputError("Multi-head replay protocols require a replay plan.")
        if self.training_mode is TrainingMode.NAIVE_FINE_TUNING and self.replay_plan_digest is not None:
            raise TrainingDataInputError("Naive protocols cannot carry replay plans.")
        if self.selection_size <= 0:
            raise TrainingDataInputError("Training-protocol selection size must be positive.")
        if self.exposure_backend is not MaceExposureBackend.NATIVE_MACE_FIXED:
            raise TrainingDataInputError("The first DATA8 adapter supports only fixed-file exposure.")
        object.__setattr__(self, "real_pt_data_ratio_threshold", float(self.real_pt_data_ratio_threshold))
        if self.real_pt_data_ratio_threshold < 0.0:
            raise TrainingDataInputError("Replay-ratio threshold must be nonnegative.")
        if self.resolved_precision_schedule is not None:
            policy = self.optimizer_policy.precision_schedule_policy
            if policy is None:
                raise TrainingDataInputError(
                    "Resolved precision schedules require an optimizer precision-schedule policy."
                )
            if self.resolved_precision_schedule.max_num_epochs != self.optimizer_policy.max_num_epochs:
                raise TrainingDataInputError("Resolved precision schedule epoch budget disagrees with optimizer policy.")
            if self.resolved_precision_schedule.stages[0].dtype != self.optimizer_policy.default_dtype:
                raise TrainingDataInputError("Resolved precision schedule first dtype disagrees with optimizer policy.")
            if self.resolved_precision_schedule.requested_profile != policy.requested_profile:
                raise TrainingDataInputError("Resolved precision schedule profile disagrees with optimizer policy.")
            for name in (
                "model_dtype", "critical_operation_dtype", "evaluation_dtype",
                "verification_dtype", "export_dtype",
            ):
                if getattr(self.resolved_precision_schedule, name) != getattr(policy, name):
                    raise TrainingDataInputError(
                        f"Resolved precision schedule {name} disagrees with optimizer policy."
                    )

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": (
                TRAINING_PROTOCOL_IDENTITY_SCHEMA
                if self.selected_head_qualification_digest is not None
                else TRAINING_PROTOCOL_IDENTITY_V6_SCHEMA
                if self.training_budget_policy is not None
                else TRAINING_PROTOCOL_IDENTITY_V5_SCHEMA
                if self.adaptive_stop_policy is not None
                else TRAINING_PROTOCOL_IDENTITY_V4_SCHEMA
                if self.online_monitor_policy_digest is not None
                else TRAINING_PROTOCOL_IDENTITY_V3_SCHEMA
                if self.resolved_precision_schedule is not None
                else TRAINING_PROTOCOL_IDENTITY_V2_SCHEMA
            ),
            "training_mode": self.training_mode.value,
            "foundation_checkpoint": self.foundation_checkpoint.to_dict(),
            "compatibility_probe_digest": self.compatibility_probe_digest,
            "data7_bundle_digest": self.data7_bundle_digest,
            "target_train_artifact_digest": self.target_train_artifact_digest,
            "target_valid_artifact_digest": self.target_valid_artifact_digest,
            "replay_plan_digest": self.replay_plan_digest,
            "training_objective_policy_digest": self.training_objective_policy_digest,
            "configuration_weight_policy_digest": self.configuration_weight_policy_digest,
            "checkpoint_metric_policy_digest": self.checkpoint_metric_policy_digest,
            "checkpoint_control_policy": self.checkpoint_control_policy.to_dict(),
            "optimizer_policy": self.optimizer_policy.to_dict(),
            "selection_size": self.selection_size,
            "exposure_backend": self.exposure_backend.value,
            "real_pt_data_ratio_threshold": self.real_pt_data_ratio_threshold,
        }
        if self.resolved_precision_schedule is not None:
            payload["resolved_precision_schedule"] = self.resolved_precision_schedule.to_dict()
        if self.online_monitor_policy_digest is not None:
            payload.update({
                "online_monitor_policy_digest": self.online_monitor_policy_digest,
                "target_online_monitor_record_digest": self.target_online_monitor_record_digest,
                "replay_online_monitor_record_digest": self.replay_online_monitor_record_digest,
                "replay_valid_artifact_digest": self.replay_valid_artifact_digest,
            })
        if self.adaptive_stop_policy is not None:
            payload["adaptive_stop_policy"] = self.adaptive_stop_policy.to_dict()
        if self.training_budget_policy is not None:
            payload.update({
                "training_budget_policy": self.training_budget_policy.to_dict(),
                "learning_rate_schedule_policy": self.learning_rate_schedule_policy.to_dict(),
                "checkpoint_admissibility_policy": self.checkpoint_admissibility_policy.to_dict(),
                "checkpoint_selection_policy": self.checkpoint_selection_policy.to_dict(),
            })
        if self.selected_head_qualification_digest is not None:
            payload.update({
                "selected_head_qualification_digest": self.selected_head_qualification_digest,
                "training_foundation_checkpoint_reference": self.training_foundation_checkpoint_reference,
                "training_foundation_checkpoint_sha256": self.training_foundation_checkpoint_sha256,
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingProtocolIdentity":
        if payload.get("schema") not in {TRAINING_PROTOCOL_IDENTITY_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V6_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V5_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V4_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V3_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V2_SCHEMA, "mdstats.training-protocol-identity.v1"}:
            raise TrainingDataSerializationError("Unsupported training-protocol schema.")
        result = cls(
            training_mode=TrainingMode(payload["training_mode"]),
            foundation_checkpoint=FoundationCheckpointIdentity.from_dict(payload["foundation_checkpoint"]),
            compatibility_probe_digest=str(payload["compatibility_probe_digest"]),
            data7_bundle_digest=str(payload["data7_bundle_digest"]),
            target_train_artifact_digest=str(payload["target_train_artifact_digest"]),
            target_valid_artifact_digest=str(payload["target_valid_artifact_digest"]),
            replay_plan_digest=None if payload.get("replay_plan_digest") is None else str(payload["replay_plan_digest"]),
            training_objective_policy_digest=str(payload["training_objective_policy_digest"]),
            configuration_weight_policy_digest=str(payload["configuration_weight_policy_digest"]),
            checkpoint_metric_policy_digest=str(payload["checkpoint_metric_policy_digest"]),
            checkpoint_control_policy=MaceCheckpointControlPolicy.from_dict(payload["checkpoint_control_policy"]),
            optimizer_policy=MaceOptimizerPolicy.from_dict(payload["optimizer_policy"]),
            selection_size=int(payload.get("selection_size", 1)),
            exposure_backend=MaceExposureBackend(payload["exposure_backend"]),
            real_pt_data_ratio_threshold=float(payload["real_pt_data_ratio_threshold"]),
            resolved_precision_schedule=(
                None
                if payload.get("resolved_precision_schedule") is None
                else ResolvedPrecisionSchedule.from_dict(payload["resolved_precision_schedule"])
            ),
            online_monitor_policy_digest=None if payload.get("online_monitor_policy_digest") is None else str(payload["online_monitor_policy_digest"]),
            target_online_monitor_record_digest=None if payload.get("target_online_monitor_record_digest") is None else str(payload["target_online_monitor_record_digest"]),
            replay_online_monitor_record_digest=None if payload.get("replay_online_monitor_record_digest") is None else str(payload["replay_online_monitor_record_digest"]),
            replay_valid_artifact_digest=None if payload.get("replay_valid_artifact_digest") is None else str(payload["replay_valid_artifact_digest"]),
            adaptive_stop_policy=(
                None
                if payload.get("adaptive_stop_policy") is None
                else AdaptiveTrainingStopPolicy.from_dict(payload["adaptive_stop_policy"])
            ),
            training_budget_policy=(
                None if payload.get("training_budget_policy") is None
                else TrainingBudgetPolicy.from_dict(payload["training_budget_policy"])
            ),
            learning_rate_schedule_policy=(
                None if payload.get("learning_rate_schedule_policy") is None
                else LearningRateSchedulePolicy.from_dict(payload["learning_rate_schedule_policy"])
            ),
            checkpoint_admissibility_policy=(
                None if payload.get("checkpoint_admissibility_policy") is None
                else CheckpointAdmissibilityPolicy.from_dict(payload["checkpoint_admissibility_policy"])
            ),
            checkpoint_selection_policy=(
                None if payload.get("checkpoint_selection_policy") is None
                else CheckpointSelectionPolicy.from_dict(payload["checkpoint_selection_policy"])
            ),
            selected_head_qualification_digest=(
                None if payload.get("selected_head_qualification_digest") is None
                else str(payload["selected_head_qualification_digest"])
            ),
            training_foundation_checkpoint_reference=(
                None if payload.get("training_foundation_checkpoint_reference") is None
                else str(payload["training_foundation_checkpoint_reference"])
            ),
            training_foundation_checkpoint_sha256=(
                None if payload.get("training_foundation_checkpoint_sha256") is None
                else str(payload["training_foundation_checkpoint_sha256"])
            ),
        )
        if payload.get("schema") in {TRAINING_PROTOCOL_IDENTITY_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V6_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V5_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V4_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V3_SCHEMA, TRAINING_PROTOCOL_IDENTITY_V2_SCHEMA} and payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-protocol digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SealedEvaluationArtifact:
    role: str
    label_domain_id: str
    frame_uids: tuple[str, ...]
    frame_catalog_digest: str
    data5_bundle_digest: str
    materialized: bool = False
    activation_requirement: str = "ProtocolFreezeRecord"

    def __post_init__(self) -> None:
        frames = tuple(validate_digest(v, name="frame_uid") for v in self.frame_uids)
        if len(set(frames)) != len(frames):
            raise TrainingDataInputError("Sealed evaluation frames must be unique.")
        object.__setattr__(self, "frame_uids", frames)
        for name in ("frame_catalog_digest", "data5_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.materialized:
            raise TrainingDataInputError("DATA8 outer locked tests must remain unmaterialized.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SEALED_EVALUATION_ARTIFACT_SCHEMA,
            "role": self.role,
            "label_domain_id": self.label_domain_id,
            "frame_uids": list(self.frame_uids),
            "frame_catalog_digest": self.frame_catalog_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "materialized": self.materialized,
            "activation_requirement": self.activation_requirement,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SealedEvaluationArtifact":
        if payload.get("schema") != SEALED_EVALUATION_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported sealed-evaluation schema.")
        result = cls(
            role=str(payload["role"]),
            label_domain_id=str(payload["label_domain_id"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            materialized=bool(payload["materialized"]),
            activation_requirement=str(payload["activation_requirement"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Sealed-evaluation digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceJobArtifact:
    job_id: str
    kind: MaceJobKind
    fold_index: int | None
    relative_directory: str
    config_relative_path: str
    config_sha256: str
    command_relative_path: str
    command_sha256: str
    target_train_artifact_digest: str
    target_valid_artifact_digest: str
    fold_evaluation_artifact_digest: str | None
    replay_plan_digest: str | None
    protocol: TrainingProtocolIdentity
    loader_dry_run: MaceLoaderDryRun

    def __post_init__(self) -> None:
        object.__setattr__(self, "kind", MaceJobKind(self.kind))
        for name in (
            "config_sha256",
            "command_sha256",
            "target_train_artifact_digest",
            "target_valid_artifact_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("fold_evaluation_artifact_digest", "replay_plan_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.kind is MaceJobKind.CROSS_VALIDATION_FOLD:
            if self.fold_index is None or self.fold_evaluation_artifact_digest is None:
                raise TrainingDataInputError("Cross-validation jobs require fold and evaluation artifact.")
        elif self.fold_index is not None or self.fold_evaluation_artifact_digest is not None:
            raise TrainingDataInputError("Final-development job cannot carry fold evaluation.")
        if self.protocol.compatibility_probe_digest != self.loader_dry_run.compatibility_probe_digest:
            raise TrainingDataInputError("MACE job compatibility-probe lineage mismatch.")
        if self.protocol.target_train_artifact_digest != self.target_train_artifact_digest:
            raise TrainingDataInputError("MACE job target-train lineage mismatch.")
        if self.protocol.target_valid_artifact_digest != self.target_valid_artifact_digest:
            raise TrainingDataInputError("MACE job target-valid lineage mismatch.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_JOB_ARTIFACT_SCHEMA,
            "job_id": self.job_id,
            "kind": self.kind.value,
            "fold_index": self.fold_index,
            "relative_directory": self.relative_directory,
            "config_relative_path": self.config_relative_path,
            "config_sha256": self.config_sha256,
            "command_relative_path": self.command_relative_path,
            "command_sha256": self.command_sha256,
            "target_train_artifact_digest": self.target_train_artifact_digest,
            "target_valid_artifact_digest": self.target_valid_artifact_digest,
            "fold_evaluation_artifact_digest": self.fold_evaluation_artifact_digest,
            "replay_plan_digest": self.replay_plan_digest,
            "protocol": self.protocol.to_dict(),
            "loader_dry_run": self.loader_dry_run.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceJobArtifact":
        if payload.get("schema") != MACE_JOB_ARTIFACT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE-job schema.")
        result = cls(
            job_id=str(payload["job_id"]),
            kind=MaceJobKind(payload["kind"]),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
            relative_directory=str(payload["relative_directory"]),
            config_relative_path=str(payload["config_relative_path"]),
            config_sha256=str(payload["config_sha256"]),
            command_relative_path=str(payload["command_relative_path"]),
            command_sha256=str(payload["command_sha256"]),
            target_train_artifact_digest=str(payload["target_train_artifact_digest"]),
            target_valid_artifact_digest=str(payload["target_valid_artifact_digest"]),
            fold_evaluation_artifact_digest=None if payload.get("fold_evaluation_artifact_digest") is None else str(payload["fold_evaluation_artifact_digest"]),
            replay_plan_digest=None if payload.get("replay_plan_digest") is None else str(payload["replay_plan_digest"]),
            protocol=TrainingProtocolIdentity.from_dict(payload["protocol"]),
            loader_dry_run=MaceLoaderDryRun.from_dict(payload["loader_dry_run"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE-job digest mismatch.")
        return result
