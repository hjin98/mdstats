"""MLCV-STOP1 criterion-driven MACE training termination.

For current MLCV evidence, target force RMSE is absolute while replay is
measured as degradation relative to the frozen foundation model on the exact
same replay domain. Historical policy/state schemas remain readable with their
original absolute-replay semantics and digests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path
from typing import Any, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)
from .mlcv_roles import MlcvDataRole, require_mlcv_checkpoint_stopping_role

ADAPTIVE_STOP_POLICY_SCHEMA = "mdstats.adaptive-training-stop-policy.v3"
ADAPTIVE_STOP_POLICY_LEGACY_SCHEMAS = frozenset({
    "mdstats.adaptive-training-stop-policy.v1",
    "mdstats.adaptive-training-stop-policy.v2",
})
ADAPTIVE_STOP_STATE_SCHEMA = "mdstats.adaptive-training-stop-state.v3"
ADAPTIVE_STOP_STATE_LEGACY_SCHEMAS = frozenset({
    "mdstats.adaptive-training-stop-state.v1",
    "mdstats.adaptive-training-stop-state.v2",
})
REPLAY_FOUNDATION_BASELINE_SCHEMA = "mdstats.mlcv-replay-foundation-baseline.v1"
ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE = "MDSTATS_ADAPTIVE_STOP_POLICY"
ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE = "MDSTATS_ADAPTIVE_STOP_STATE_PATH"
ADAPTIVE_STOP_AUXILIARY_REPLAY_PATH_ENVIRONMENT_VARIABLE = "MDSTATS_ADAPTIVE_STOP_AUXILIARY_REPLAY_PATH"
ADAPTIVE_STOP_REPLAY_LIGHT_PATH_ENVIRONMENT_VARIABLE = "MDSTATS_ADAPTIVE_STOP_REPLAY_LIGHT_PATH"
ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE = (
    "MDSTATS_ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH"
)
ADAPTIVE_STOP_FOUNDATION_BASELINE_PATH_ENVIRONMENT_VARIABLE = (
    "MDSTATS_ADAPTIVE_STOP_FOUNDATION_BASELINE_PATH"
)
ADAPTIVE_STOP_FOUNDATION_MODEL_SHA256_ENVIRONMENT_VARIABLE = (
    "MDSTATS_ADAPTIVE_STOP_FOUNDATION_MODEL_SHA256"
)
ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD = "mdstats_foundation_replay_full"
MLCV_TARGET_STOP_FRACTION = 0.80
MLCV_REPLAY_STOP_MULTIPLIER = 1.20


class DeterministicTrainingPreflightError(RuntimeError):
    """A configuration/authority failure that cannot improve on subprocess retry."""


@dataclass(frozen=True, slots=True)
class AdaptiveTrainingStopPolicy:
    """Immutable target/degradation acceptance geometry and stop margins."""

    maximum_target_force_rmse_ev_per_angstrom: float = 0.030
    target_score_weight: float = 1.0
    replay_score_weight: float = 1.0
    target_stop_fraction: float = MLCV_TARGET_STOP_FRACTION
    replay_stop_multiplier: float = MLCV_REPLAY_STOP_MULTIPLIER
    minimum_epochs_before_adaptive_stop: int = 3
    max_num_epochs: int = 30
    replay_enabled: bool = True
    replay_degradation_budget_ev_per_angstrom: float | None = None
    # Historical escape hatch. It is parsed only to preserve v1/v2 digests and
    # has no authority under v3 degradation semantics.
    allow_replay_threshold_below_foundation_baseline: bool = False
    target_head_name: str = "target_head"
    replay_head_name: str = "pt_head"
    serialization_schema: str = field(
        default=ADAPTIVE_STOP_POLICY_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        supported = {ADAPTIVE_STOP_POLICY_SCHEMA, *ADAPTIVE_STOP_POLICY_LEGACY_SCHEMAS}
        if self.serialization_schema not in supported:
            raise TrainingDataInputError("Unsupported adaptive-stop policy serialization schema.")
        numbers = {
            "maximum_target_force_rmse_ev_per_angstrom": self.maximum_target_force_rmse_ev_per_angstrom,
            "target_score_weight": self.target_score_weight,
            "target_stop_fraction": self.target_stop_fraction,
            "replay_stop_multiplier": self.replay_stop_multiplier,
        }
        if self.replay_enabled:
            numbers["replay_score_weight"] = self.replay_score_weight
        for name, value in numbers.items():
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise TrainingDataInputError(f"Adaptive-stop {name} must be finite and positive.")
        if self.replay_degradation_budget_ev_per_angstrom is not None:
            value = float(self.replay_degradation_budget_ev_per_angstrom)
            if not math.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(
                    "Adaptive-stop replay_degradation_budget_ev_per_angstrom must be finite and positive."
                )
            object.__setattr__(self, "replay_degradation_budget_ev_per_angstrom", value)
        if not 0.0 < float(self.target_stop_fraction) < 1.0:
            raise TrainingDataInputError("Adaptive-stop target_stop_fraction must be strictly between zero and one.")
        if float(self.replay_stop_multiplier) <= 1.0:
            raise TrainingDataInputError("Adaptive-stop replay_stop_multiplier must exceed one.")
        if int(self.minimum_epochs_before_adaptive_stop) <= 0:
            raise TrainingDataInputError("Adaptive-stop minimum_epochs_before_adaptive_stop must be positive.")
        if int(self.max_num_epochs) <= 0:
            raise TrainingDataInputError("Adaptive-stop max_num_epochs must be positive.")
        if self.replay_enabled and (not self.target_head_name.strip() or not self.replay_head_name.strip()):
            raise TrainingDataInputError("Adaptive-stop target/replay head names must be non-empty.")
        if not self.replay_enabled and not self.target_head_name.strip():
            raise TrainingDataInputError("Adaptive-stop target head name must be non-empty.")

    @property
    def replay_degradation_budget_force_rmse_ev_per_angstrom(self) -> float | None:
        if not self.replay_enabled:
            return None
        if self.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA and self.replay_degradation_budget_ev_per_angstrom is not None:
            return float(self.replay_degradation_budget_ev_per_angstrom)
        return (
            float(self.target_score_weight)
            / float(self.replay_score_weight)
            * float(self.maximum_target_force_rmse_ev_per_angstrom)
        )

    @property
    def maximum_replay_force_rmse_ev_per_angstrom(self) -> float | None:
        """Compatibility alias.

        In v3 this value is the replay *degradation budget*, not an absolute
        replay-RMSE ceiling. v1/v2 retain their historical absolute meaning.
        """
        return self.replay_degradation_budget_force_rmse_ev_per_angstrom

    @property
    def target_stop_force_rmse_ev_per_angstrom(self) -> float:
        return float(self.target_stop_fraction) * float(self.maximum_target_force_rmse_ev_per_angstrom)

    @property
    def replay_stop_degradation_force_rmse_ev_per_angstrom(self) -> float | None:
        budget = self.replay_degradation_budget_force_rmse_ev_per_angstrom
        return None if budget is None else float(self.replay_stop_multiplier) * budget

    @property
    def replay_stop_force_rmse_ev_per_angstrom(self) -> float | None:
        """Compatibility alias for the degradation-space stop boundary in v3."""
        return self.replay_stop_degradation_force_rmse_ev_per_angstrom

    def replay_absolute_ceiling_ev_per_angstrom(self, foundation_rmse: float) -> float | None:
        budget = self.replay_degradation_budget_force_rmse_ev_per_angstrom
        return None if budget is None else float(foundation_rmse) + budget

    def replay_absolute_stop_ceiling_ev_per_angstrom(self, foundation_rmse: float) -> float | None:
        stop = self.replay_stop_degradation_force_rmse_ev_per_angstrom
        return None if stop is None else float(foundation_rmse) + stop

    def candidate_eligible(self, target_rmse: float, replay_rmse: float | None) -> bool:
        """Return lightweight rankability; full gates are deferred to SELECT1."""
        if not math.isfinite(float(target_rmse)) or float(target_rmse) < 0.0:
            return False
        # v1 was the historical all-eligible/full-gate contract. v2 already
        # switched the lightweight path to finite/rankable semantics.
        if self.serialization_schema == "mdstats.adaptive-training-stop-policy.v1":
            if float(target_rmse) > float(self.maximum_target_force_rmse_ev_per_angstrom):
                return False
            if not self.replay_enabled:
                return True
            threshold = self.maximum_replay_force_rmse_ev_per_angstrom
            return bool(
                replay_rmse is not None and threshold is not None
                and math.isfinite(float(replay_rmse))
                and 0.0 <= float(replay_rmse) <= threshold
            )
        if not self.replay_enabled:
            return True
        return bool(
            replay_rmse is not None
            and math.isfinite(float(replay_rmse))
            and float(replay_rmse) >= 0.0
        )

    def stop_reason(
        self,
        *,
        epoch: int,
        target_rmse: float,
        replay_rmse: float | None,
        foundation_replay_rmse: float | None = None,
        replay_degradation_rmse: float | None = None,
    ) -> str | None:
        completed_epochs = int(epoch) + 1
        margins_active = completed_epochs >= int(self.minimum_epochs_before_adaptive_stop)
        target_hit = bool(
            margins_active and target_rmse <= self.target_stop_force_rmse_ev_per_angstrom
        )
        replay_threshold = self.replay_stop_degradation_force_rmse_ev_per_angstrom
        replay_control_value = replay_rmse
        if self.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA and self.replay_enabled:
            if replay_degradation_rmse is not None:
                replay_control_value = float(replay_degradation_rmse)
            elif replay_rmse is not None and foundation_replay_rmse is not None:
                replay_control_value = float(replay_rmse) - float(foundation_replay_rmse)
            elif replay_rmse is not None:
                raise TrainingDataInputError(
                    "MLCV-STOP1 v3 requires the matched R0_light foundation baseline to evaluate replay exhaustion."
                )
        replay_hit = bool(
            margins_active
            and self.replay_enabled
            and replay_threshold is not None
            and replay_control_value is not None
            and replay_control_value >= replay_threshold
        )
        if target_hit and replay_hit:
            return "target_success_and_replay_exhaustion"
        if target_hit:
            return "target_success"
        if replay_hit:
            return "replay_exhaustion"
        if completed_epochs >= int(self.max_num_epochs):
            return "max_epochs_reached"
        return None

    def _payload(self) -> dict[str, Any]:
        if self.serialization_schema in ADAPTIVE_STOP_POLICY_LEGACY_SCHEMAS:
            payload = {
                "schema": self.serialization_schema,
                "maximum_target_force_rmse_ev_per_angstrom": float(self.maximum_target_force_rmse_ev_per_angstrom),
                "target_score_weight": float(self.target_score_weight),
                "replay_score_weight": float(self.replay_score_weight),
                "target_stop_fraction": float(self.target_stop_fraction),
                "replay_stop_multiplier": float(self.replay_stop_multiplier),
                "max_num_epochs": int(self.max_num_epochs),
                "replay_enabled": bool(self.replay_enabled),
                "allow_replay_threshold_below_foundation_baseline": bool(self.allow_replay_threshold_below_foundation_baseline),
                "target_head_name": self.target_head_name,
                "replay_head_name": self.replay_head_name,
            }
            if self.serialization_schema == "mdstats.adaptive-training-stop-policy.v2":
                payload["minimum_epochs_before_adaptive_stop"] = int(self.minimum_epochs_before_adaptive_stop)
            return payload
        return {
            "schema": ADAPTIVE_STOP_POLICY_SCHEMA,
            "maximum_target_force_rmse_ev_per_angstrom": float(self.maximum_target_force_rmse_ev_per_angstrom),
            "target_score_weight": float(self.target_score_weight),
            "replay_score_weight": float(self.replay_score_weight),
            "replay_degradation_budget_ev_per_angstrom": float(self.replay_degradation_budget_force_rmse_ev_per_angstrom) if self.replay_enabled else None,
            "replay_degradation_budget_is_explicit": self.replay_degradation_budget_ev_per_angstrom is not None,
            "target_stop_fraction": float(self.target_stop_fraction),
            "replay_stop_multiplier": float(self.replay_stop_multiplier),
            "minimum_epochs_before_adaptive_stop": int(self.minimum_epochs_before_adaptive_stop),
            "max_num_epochs": int(self.max_num_epochs),
            "replay_enabled": bool(self.replay_enabled),
            "target_head_name": self.target_head_name,
            "replay_head_name": self.replay_head_name,
            "replay_semantics": "foundation_relative_degradation",
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveTrainingStopPolicy":
        schema = payload.get("schema")
        if schema not in {ADAPTIVE_STOP_POLICY_SCHEMA, *ADAPTIVE_STOP_POLICY_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported adaptive-training-stop policy schema.")
        explicit_budget = None
        if schema == ADAPTIVE_STOP_POLICY_SCHEMA and bool(payload.get("replay_degradation_budget_is_explicit", False)):
            explicit_budget = float(payload["replay_degradation_budget_ev_per_angstrom"])
        result = cls(
            maximum_target_force_rmse_ev_per_angstrom=float(payload["maximum_target_force_rmse_ev_per_angstrom"]),
            target_score_weight=float(payload["target_score_weight"]),
            replay_score_weight=float(payload["replay_score_weight"]),
            target_stop_fraction=float(payload["target_stop_fraction"]),
            replay_stop_multiplier=float(payload["replay_stop_multiplier"]),
            minimum_epochs_before_adaptive_stop=int(
                payload.get("minimum_epochs_before_adaptive_stop", 1 if schema == "mdstats.adaptive-training-stop-policy.v1" else 3)
            ),
            max_num_epochs=int(payload["max_num_epochs"]),
            replay_enabled=bool(payload["replay_enabled"]),
            replay_degradation_budget_ev_per_angstrom=explicit_budget,
            allow_replay_threshold_below_foundation_baseline=bool(
                payload.get("allow_replay_threshold_below_foundation_baseline", False)
            ),
            target_head_name=str(payload.get("target_head_name", "target_head")),
            replay_head_name=str(payload.get("replay_head_name", "pt_head")),
            serialization_schema=str(schema),
        )
        # Authenticate the resolved derived budget too, not merely explicit overrides.
        if schema == ADAPTIVE_STOP_POLICY_SCHEMA and result.replay_enabled:
            stored = float(payload["replay_degradation_budget_ev_per_angstrom"])
            actual = float(result.replay_degradation_budget_force_rmse_ev_per_angstrom)
            if not math.isclose(stored, actual, rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataSerializationError("Adaptive-training-stop degradation budget mismatch.")
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Adaptive-training-stop policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AdaptiveTrainingEpochMetric:
    epoch: int
    target_force_rmse_ev_per_angstrom: float
    replay_force_rmse_ev_per_angstrom: float | None
    candidate_eligible: bool
    stop_reason: str | None = None
    replay_foundation_force_rmse_ev_per_angstrom: float | None = None
    replay_degradation_force_rmse_ev_per_angstrom: float | None = None

    def __post_init__(self) -> None:
        if int(self.epoch) < 0:
            raise TrainingDataInputError("Adaptive-stop epoch must be nonnegative.")
        for name in ("target_force_rmse_ev_per_angstrom", "replay_force_rmse_ev_per_angstrom", "replay_foundation_force_rmse_ev_per_angstrom"):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"Adaptive-stop {name} must be finite and nonnegative.")
        degradation = self.replay_degradation_force_rmse_ev_per_angstrom
        if degradation is not None and not math.isfinite(float(degradation)):
            raise TrainingDataInputError("Adaptive-stop replay degradation must be finite; negative improvements are valid.")
        if self.replay_force_rmse_ev_per_angstrom is not None and self.replay_foundation_force_rmse_ev_per_angstrom is not None:
            expected = float(self.replay_force_rmse_ev_per_angstrom) - float(self.replay_foundation_force_rmse_ev_per_angstrom)
            if degradation is None or not math.isclose(float(degradation), expected, rel_tol=0.0, abs_tol=1e-15):
                raise TrainingDataInputError("Adaptive-stop replay degradation does not match absolute-minus-foundation RMSE.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "epoch": int(self.epoch),
            "target_force_rmse_ev_per_angstrom": float(self.target_force_rmse_ev_per_angstrom),
            "replay_absolute_force_rmse_ev_per_angstrom": None if self.replay_force_rmse_ev_per_angstrom is None else float(self.replay_force_rmse_ev_per_angstrom),
            "replay_foundation_force_rmse_ev_per_angstrom": None if self.replay_foundation_force_rmse_ev_per_angstrom is None else float(self.replay_foundation_force_rmse_ev_per_angstrom),
            "replay_degradation_force_rmse_ev_per_angstrom": None if self.replay_degradation_force_rmse_ev_per_angstrom is None else float(self.replay_degradation_force_rmse_ev_per_angstrom),
            "candidate_eligible": bool(self.candidate_eligible),
            "stop_reason": self.stop_reason,
        }

    def to_legacy_dict(self) -> dict[str, Any]:
        return {
            "epoch": int(self.epoch),
            "target_force_rmse_ev_per_angstrom": float(self.target_force_rmse_ev_per_angstrom),
            "replay_force_rmse_ev_per_angstrom": None if self.replay_force_rmse_ev_per_angstrom is None else float(self.replay_force_rmse_ev_per_angstrom),
            "candidate_eligible": bool(self.candidate_eligible),
            "stop_reason": self.stop_reason,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveTrainingEpochMetric":
        replay = payload.get("replay_absolute_force_rmse_ev_per_angstrom", payload.get("replay_force_rmse_ev_per_angstrom"))
        return cls(
            epoch=int(payload["epoch"]),
            target_force_rmse_ev_per_angstrom=float(payload["target_force_rmse_ev_per_angstrom"]),
            replay_force_rmse_ev_per_angstrom=None if replay is None else float(replay),
            replay_foundation_force_rmse_ev_per_angstrom=None if payload.get("replay_foundation_force_rmse_ev_per_angstrom") is None else float(payload["replay_foundation_force_rmse_ev_per_angstrom"]),
            replay_degradation_force_rmse_ev_per_angstrom=None if payload.get("replay_degradation_force_rmse_ev_per_angstrom") is None else float(payload["replay_degradation_force_rmse_ev_per_angstrom"]),
            candidate_eligible=bool(payload["candidate_eligible"]),
            stop_reason=None if payload.get("stop_reason") is None else str(payload["stop_reason"]),
        )


@dataclass(frozen=True, slots=True)
class AdaptiveTrainingStopState:
    policy_digest: str
    # Compatibility constructor field for historical v1/v2 state. In current
    # v3 it is mirrored to the full-domain baseline but not serialized.
    foundation_replay_force_rmse_ev_per_angstrom: float | None = None
    foundation_replay_threshold_feasible: bool | None = None
    foundation_feasibility_overridden: bool = False
    foundation_replay_evidence_scope: str | None = None
    foundation_replay_artifact_sha256: str | None = None
    foundation_replay_light_force_rmse_ev_per_angstrom: float | None = None
    foundation_replay_full_force_rmse_ev_per_angstrom: float | None = None
    foundation_replay_light_artifact_sha256: str | None = None
    foundation_replay_full_artifact_sha256: str | None = None
    foundation_model_sha256: str | None = None
    replay_degradation_budget_ev_per_angstrom: float | None = None
    replay_stop_degradation_ev_per_angstrom: float | None = None
    replay_light_absolute_ceiling_ev_per_angstrom: float | None = None
    replay_full_absolute_ceiling_ev_per_angstrom: float | None = None
    epochs: tuple[AdaptiveTrainingEpochMetric, ...] = ()
    stop_epoch: int | None = None
    stop_reason: str | None = None
    run_outcome: str = "running"
    serialization_schema: str = field(default=ADAPTIVE_STOP_STATE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        supported = {ADAPTIVE_STOP_STATE_SCHEMA, *ADAPTIVE_STOP_STATE_LEGACY_SCHEMAS}
        if self.serialization_schema not in supported:
            raise TrainingDataInputError("Unsupported adaptive-stop state serialization schema.")
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        # Map the historical baseline field to full baseline for convenient read compatibility.
        if self.serialization_schema == ADAPTIVE_STOP_STATE_SCHEMA:
            if self.foundation_replay_full_force_rmse_ev_per_angstrom is None and self.foundation_replay_force_rmse_ev_per_angstrom is not None:
                object.__setattr__(self, "foundation_replay_full_force_rmse_ev_per_angstrom", float(self.foundation_replay_force_rmse_ev_per_angstrom))
            if self.foundation_replay_force_rmse_ev_per_angstrom is None and self.foundation_replay_full_force_rmse_ev_per_angstrom is not None:
                object.__setattr__(self, "foundation_replay_force_rmse_ev_per_angstrom", float(self.foundation_replay_full_force_rmse_ev_per_angstrom))
        for name in (
            "foundation_replay_force_rmse_ev_per_angstrom",
            "foundation_replay_light_force_rmse_ev_per_angstrom",
            "foundation_replay_full_force_rmse_ev_per_angstrom",
            "replay_degradation_budget_ev_per_angstrom",
            "replay_stop_degradation_ev_per_angstrom",
            "replay_light_absolute_ceiling_ev_per_angstrom",
            "replay_full_absolute_ceiling_ev_per_angstrom",
        ):
            value = getattr(self, name)
            if value is not None and (not math.isfinite(float(value)) or float(value) < 0.0):
                raise TrainingDataInputError(f"Adaptive-stop state {name} must be finite and nonnegative.")
        if self.foundation_replay_evidence_scope not in {None, "full_true_dft", "historical_lightweight_true_dft", "matched_light_full_true_dft"}:
            raise TrainingDataInputError("Unsupported foundation replay evidence scope.")
        for name in (
            "foundation_replay_artifact_sha256",
            "foundation_replay_light_artifact_sha256",
            "foundation_replay_full_artifact_sha256",
            "foundation_model_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        epochs = tuple(sorted(self.epochs, key=lambda item: item.epoch))
        if len({item.epoch for item in epochs}) != len(epochs):
            raise TrainingDataInputError("Adaptive-stop state cannot contain duplicate epochs.")
        object.__setattr__(self, "epochs", epochs)
        if self.stop_epoch is None:
            if self.stop_reason is not None:
                raise TrainingDataInputError("Adaptive-stop reason requires stop_epoch.")
        elif self.stop_reason is None or not any(item.epoch == self.stop_epoch for item in epochs):
            raise TrainingDataInputError("Adaptive-stop stop evidence is incomplete.")
        allowed = {"running", "admissible_checkpoint_available", "no_lightweight_admissible_checkpoint"}
        if self.run_outcome not in allowed:
            raise TrainingDataInputError("Unsupported adaptive-stop run outcome.")

    def _payload(self) -> dict[str, Any]:
        if self.serialization_schema in ADAPTIVE_STOP_STATE_LEGACY_SCHEMAS:
            payload = {
                "schema": self.serialization_schema,
                "policy_digest": self.policy_digest,
                "foundation_replay_force_rmse_ev_per_angstrom": self.foundation_replay_force_rmse_ev_per_angstrom,
                "foundation_replay_threshold_feasible": self.foundation_replay_threshold_feasible,
                "foundation_feasibility_overridden": bool(self.foundation_feasibility_overridden),
                "epochs": [item.to_legacy_dict() for item in self.epochs],
                "stop_epoch": self.stop_epoch,
                "stop_reason": self.stop_reason,
                "run_outcome": self.run_outcome,
            }
            if self.serialization_schema == "mdstats.adaptive-training-stop-state.v2":
                payload.update({
                    "foundation_replay_evidence_scope": self.foundation_replay_evidence_scope,
                    "foundation_replay_artifact_sha256": self.foundation_replay_artifact_sha256,
                })
            return payload
        return {
            "schema": ADAPTIVE_STOP_STATE_SCHEMA,
            "policy_digest": self.policy_digest,
            "replay_semantics": "foundation_relative_degradation",
            "foundation_replay_evidence_scope": self.foundation_replay_evidence_scope,
            "foundation_model_sha256": self.foundation_model_sha256,
            "foundation_replay_light_force_rmse_ev_per_angstrom": self.foundation_replay_light_force_rmse_ev_per_angstrom,
            "foundation_replay_full_force_rmse_ev_per_angstrom": self.foundation_replay_full_force_rmse_ev_per_angstrom,
            "foundation_replay_light_artifact_sha256": self.foundation_replay_light_artifact_sha256,
            "foundation_replay_full_artifact_sha256": self.foundation_replay_full_artifact_sha256,
            "replay_degradation_budget_ev_per_angstrom": self.replay_degradation_budget_ev_per_angstrom,
            "replay_stop_degradation_ev_per_angstrom": self.replay_stop_degradation_ev_per_angstrom,
            "replay_light_absolute_ceiling_ev_per_angstrom": self.replay_light_absolute_ceiling_ev_per_angstrom,
            "replay_full_absolute_ceiling_ev_per_angstrom": self.replay_full_absolute_ceiling_ev_per_angstrom,
            "epochs": [item.to_dict() for item in self.epochs],
            "stop_epoch": self.stop_epoch,
            "stop_reason": self.stop_reason,
            "run_outcome": self.run_outcome,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdaptiveTrainingStopState":
        schema = payload.get("schema")
        if schema not in {ADAPTIVE_STOP_STATE_SCHEMA, *ADAPTIVE_STOP_STATE_LEGACY_SCHEMAS}:
            raise TrainingDataSerializationError("Unsupported adaptive-training-stop state schema.")
        kwargs: dict[str, Any] = dict(
            policy_digest=str(payload["policy_digest"]),
            epochs=tuple(AdaptiveTrainingEpochMetric.from_dict(item) for item in payload.get("epochs", ())),
            stop_epoch=None if payload.get("stop_epoch") is None else int(payload["stop_epoch"]),
            stop_reason=None if payload.get("stop_reason") is None else str(payload["stop_reason"]),
            run_outcome=str(payload.get("run_outcome", "running")),
            serialization_schema=str(schema),
        )
        if schema in ADAPTIVE_STOP_STATE_LEGACY_SCHEMAS:
            kwargs.update(
                foundation_replay_force_rmse_ev_per_angstrom=None if payload.get("foundation_replay_force_rmse_ev_per_angstrom") is None else float(payload["foundation_replay_force_rmse_ev_per_angstrom"]),
                foundation_replay_threshold_feasible=None if payload.get("foundation_replay_threshold_feasible") is None else bool(payload["foundation_replay_threshold_feasible"]),
                foundation_feasibility_overridden=bool(payload.get("foundation_feasibility_overridden", False)),
                foundation_replay_evidence_scope=None if payload.get("foundation_replay_evidence_scope") is None else str(payload["foundation_replay_evidence_scope"]),
                foundation_replay_artifact_sha256=None if payload.get("foundation_replay_artifact_sha256") is None else str(payload["foundation_replay_artifact_sha256"]),
            )
        else:
            kwargs.update(
                foundation_replay_light_force_rmse_ev_per_angstrom=None if payload.get("foundation_replay_light_force_rmse_ev_per_angstrom") is None else float(payload["foundation_replay_light_force_rmse_ev_per_angstrom"]),
                foundation_replay_full_force_rmse_ev_per_angstrom=None if payload.get("foundation_replay_full_force_rmse_ev_per_angstrom") is None else float(payload["foundation_replay_full_force_rmse_ev_per_angstrom"]),
                foundation_replay_light_artifact_sha256=None if payload.get("foundation_replay_light_artifact_sha256") is None else str(payload["foundation_replay_light_artifact_sha256"]),
                foundation_replay_full_artifact_sha256=None if payload.get("foundation_replay_full_artifact_sha256") is None else str(payload["foundation_replay_full_artifact_sha256"]),
                foundation_model_sha256=None if payload.get("foundation_model_sha256") is None else str(payload["foundation_model_sha256"]),
                replay_degradation_budget_ev_per_angstrom=None if payload.get("replay_degradation_budget_ev_per_angstrom") is None else float(payload["replay_degradation_budget_ev_per_angstrom"]),
                replay_stop_degradation_ev_per_angstrom=None if payload.get("replay_stop_degradation_ev_per_angstrom") is None else float(payload["replay_stop_degradation_ev_per_angstrom"]),
                replay_light_absolute_ceiling_ev_per_angstrom=None if payload.get("replay_light_absolute_ceiling_ev_per_angstrom") is None else float(payload["replay_light_absolute_ceiling_ev_per_angstrom"]),
                replay_full_absolute_ceiling_ev_per_angstrom=None if payload.get("replay_full_absolute_ceiling_ev_per_angstrom") is None else float(payload["replay_full_absolute_ceiling_ev_per_angstrom"]),
                foundation_replay_evidence_scope=None if payload.get("foundation_replay_evidence_scope") is None else str(payload["foundation_replay_evidence_scope"]),
            )
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Adaptive-training-stop state digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ReplayFoundationBaselineRecord:
    foundation_model_sha256: str
    replay_light_artifact_sha256: str
    replay_full_artifact_sha256: str
    replay_light_foundation_rmse_ev_per_angstrom: float
    replay_full_foundation_rmse_ev_per_angstrom: float

    def __post_init__(self) -> None:
        for name in ("foundation_model_sha256", "replay_light_artifact_sha256", "replay_full_artifact_sha256"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("replay_light_foundation_rmse_ev_per_angstrom", "replay_full_foundation_rmse_ev_per_angstrom"):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"Foundation replay baseline {name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": REPLAY_FOUNDATION_BASELINE_SCHEMA,
            "foundation_model_sha256": self.foundation_model_sha256,
            "replay_light_artifact_sha256": self.replay_light_artifact_sha256,
            "replay_full_artifact_sha256": self.replay_full_artifact_sha256,
            "replay_light_foundation_rmse_ev_per_angstrom": self.replay_light_foundation_rmse_ev_per_angstrom,
            "replay_full_foundation_rmse_ev_per_angstrom": self.replay_full_foundation_rmse_ev_per_angstrom,
            "replay_semantics": "foundation_relative_degradation",
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ReplayFoundationBaselineRecord":
        if payload.get("schema") != REPLAY_FOUNDATION_BASELINE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported replay-foundation-baseline schema.")
        result = cls(
            foundation_model_sha256=str(payload["foundation_model_sha256"]),
            replay_light_artifact_sha256=str(payload["replay_light_artifact_sha256"]),
            replay_full_artifact_sha256=str(payload["replay_full_artifact_sha256"]),
            replay_light_foundation_rmse_ev_per_angstrom=float(payload["replay_light_foundation_rmse_ev_per_angstrom"]),
            replay_full_foundation_rmse_ev_per_angstrom=float(payload["replay_full_foundation_rmse_ev_per_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Replay-foundation-baseline digest mismatch.")
        return result


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def adaptive_stop_policy_from_environment() -> AdaptiveTrainingStopPolicy | None:
    raw = os.environ.get(ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE)
    if raw in (None, ""):
        return None
    try:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("policy payload must be a JSON object")
        return AdaptiveTrainingStopPolicy.from_dict(payload)
    except Exception as exc:
        raise DeterministicTrainingPreflightError(
            f"MDSTATS_NONRETRYABLE invalid {ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE}: {exc}"
        ) from exc


def _state_path(logger_path: str | Path) -> Path:
    configured = os.environ.get(ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE)
    if configured not in (None, ""):
        return Path(configured).expanduser().resolve()
    logger = Path(logger_path).expanduser().resolve()
    return logger.parent / "adaptive_training_stop.json"


def _load_state(path: Path, policy: AdaptiveTrainingStopPolicy) -> AdaptiveTrainingStopState:
    if not path.is_file():
        return AdaptiveTrainingStopState(policy_digest=policy.policy_digest)
    state = AdaptiveTrainingStopState.from_dict(json.loads(path.read_text(encoding="utf-8")))
    if state.policy_digest != policy.policy_digest:
        raise DeterministicTrainingPreflightError(
            "MDSTATS_NONRETRYABLE adaptive-stop state belongs to a different policy; exact restart is refused."
        )
    return state


def _read_validation_rows(path: str | Path) -> list[dict[str, Any]]:
    logger_path = Path(path)
    rows: list[dict[str, Any]] = []
    if not logger_path.is_file():
        return rows
    with logger_path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("mode") == "eval" and "rmse_f" in item:
                rows.append(item)
    return rows


def _head_metrics(rows: list[dict[str, Any]], *, epoch: int | None, policy: AdaptiveTrainingStopPolicy) -> tuple[float | None, float | None]:
    matching = [item for item in rows if item.get("epoch") == epoch]
    if not matching:
        return None, None
    by_head: dict[str, float] = {}
    for item in matching:
        try:
            value = float(item["rmse_f"])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(value) or value < 0.0:
            continue
        by_head[str(item.get("head", "Default"))] = value
    replay_aliases = {policy.replay_head_name, "pt_head", "replay_head"}
    replay = None
    if policy.replay_enabled:
        for name in (policy.replay_head_name, "pt_head", "replay_head"):
            if name in by_head:
                replay = by_head[name]
                break
    target = by_head.get(policy.target_head_name)
    if target is None:
        for preferred in ("target_head", "Default"):
            if preferred in by_head and preferred not in replay_aliases:
                target = by_head[preferred]
                break
    if target is None:
        candidates = [(name, value) for name, value in by_head.items() if name not in replay_aliases and name != ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD]
        if len(candidates) == 1:
            target = candidates[0][1]
        elif len(candidates) > 1:
            raise RuntimeError("Adaptive-stop validation history contains multiple non-replay heads and no unique target head.")
    return target, replay


def _validation_loader_from_extxyz(model: Any, valid_loaders: Mapping[str, Any], *, path: Path, dataset_head: str) -> Any:
    """Build one deterministic MACE validation loader from immutable extxyz."""
    if not valid_loaders:
        raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 cannot infer validation batching without an existing validation loader.")
    try:
        from mace import data as mace_data
        from mace.data import KeySpecification
        from mace.tools import AtomicNumberTable, torch_geometric
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("MLCV-STOP1 could not import MACE data utilities for replay validation.") from exc
    keys = KeySpecification.from_defaults()
    keys.update(info_keys={"energy": "REF_energy", "stress": "REF_stress"}, arrays_keys={"forces": "REF_forces"})
    heads = list(getattr(model, "heads", [dataset_head]))
    _, configurations = mace_data.load_from_xyz(
        str(path), key_specification=keys, head_name=dataset_head,
        keep_isolated_atoms=True, no_data_ok=False,
    )
    atomic_numbers = getattr(model, "atomic_numbers", None)
    if atomic_numbers is None:
        raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 model does not expose atomic_numbers for replay validation.")
    if hasattr(atomic_numbers, "detach"):
        atomic_numbers = atomic_numbers.detach().cpu().tolist()
    z_table = AtomicNumberTable([int(value) for value in atomic_numbers])
    cutoff = float(getattr(model, "r_max"))
    dataset = [mace_data.AtomicData.from_config(config, z_table=z_table, cutoff=cutoff, heads=heads) for config in configurations]
    if not dataset:
        raise DeterministicTrainingPreflightError(f"MDSTATS_NONRETRYABLE MLCV-STOP1 replay validation domain is empty: {path}")
    reference_loader = next(iter(valid_loaders.values()))
    return torch_geometric.dataloader.DataLoader(
        dataset=dataset,
        batch_size=int(getattr(reference_loader, "batch_size", 1) or 1),
        shuffle=False, drop_last=False,
        pin_memory=bool(getattr(reference_loader, "pin_memory", False)),
        num_workers=int(getattr(reference_loader, "num_workers", 0) or 0),
    )


def _baseline_cache_path() -> Path | None:
    raw = os.environ.get(ADAPTIVE_STOP_FOUNDATION_BASELINE_PATH_ENVIRONMENT_VARIABLE)
    return None if not raw else Path(raw).expanduser().resolve()


def _load_authenticated_shared_baseline(*, light_path: Path, full_path: Path, model_sha: str) -> ReplayFoundationBaselineRecord | None:
    cache = _baseline_cache_path()
    if cache is None or not cache.is_file():
        return None
    try:
        record = ReplayFoundationBaselineRecord.from_dict(json.loads(cache.read_text(encoding="utf-8")))
    except Exception as exc:
        raise DeterministicTrainingPreflightError(f"MDSTATS_NONRETRYABLE invalid shared replay foundation baseline: {exc}") from exc
    expected_light = sha256_file_cached(light_path)
    expected_full = sha256_file_cached(full_path)
    if (
        record.foundation_model_sha256 != model_sha
        or record.replay_light_artifact_sha256 != expected_light
        or record.replay_full_artifact_sha256 != expected_full
    ):
        raise DeterministicTrainingPreflightError(
            "MDSTATS_NONRETRYABLE shared replay foundation baseline lineage does not match the current foundation/R_light/R_full domains."
        )
    return record


def prepare_foundation_full_replay_validation_loader(model: Any, valid_loaders: Mapping[str, Any]) -> dict[str, Any]:
    """Prepend R_full only when a matched foundation baseline is not already frozen."""
    policy = adaptive_stop_policy_from_environment()
    configured = os.environ.get(ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE)
    if policy is None or not policy.replay_enabled or not configured:
        return dict(valid_loaders)
    configured_state = os.environ.get(ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE)
    if configured_state:
        state_path = Path(configured_state).expanduser().resolve()
        if state_path.is_file():
            state = _load_state(state_path, policy)
            if state.serialization_schema == ADAPTIVE_STOP_STATE_SCHEMA and state.foundation_replay_full_force_rmse_ev_per_angstrom is not None:
                return dict(valid_loaders)
            if state.serialization_schema in ADAPTIVE_STOP_STATE_LEGACY_SCHEMAS and state.foundation_replay_force_rmse_ev_per_angstrom is not None:
                return dict(valid_loaders)
    if policy.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA:
        light_raw = os.environ.get(ADAPTIVE_STOP_REPLAY_LIGHT_PATH_ENVIRONMENT_VARIABLE)
        model_sha = os.environ.get(ADAPTIVE_STOP_FOUNDATION_MODEL_SHA256_ENVIRONMENT_VARIABLE)
        full_path = Path(configured).expanduser().resolve()
        if light_raw and model_sha:
            light_path = Path(light_raw).expanduser().resolve()
            if light_path.is_file() and full_path.is_file():
                shared = _load_authenticated_shared_baseline(light_path=light_path, full_path=full_path, model_sha=validate_digest(model_sha, name="foundation_model_sha256"))
                if shared is not None:
                    return dict(valid_loaders)
    path = Path(configured).expanduser().resolve()
    if not path.is_file():
        raise DeterministicTrainingPreflightError(f"MDSTATS_NONRETRYABLE MLCV-STOP1 full TRUE_DFT replay validation is missing: {path}")
    if ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD in valid_loaders:
        return dict(valid_loaders)
    heads = [str(value) for value in getattr(model, "heads", [policy.target_head_name])]
    dataset_head = policy.replay_head_name if policy.replay_head_name in heads else policy.target_head_name
    if dataset_head not in heads:
        if len(heads) != 1:
            raise DeterministicTrainingPreflightError(
                f"MDSTATS_NONRETRYABLE MLCV-STOP1 cannot resolve a replay-validation head from model heads {heads!r}."
            )
        dataset_head = heads[0]
    loader = _validation_loader_from_extxyz(model, valid_loaders, path=path, dataset_head=dataset_head)
    return {ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD: loader, **dict(valid_loaders)}


def remove_foundation_full_replay_validation_loader(valid_loaders: Mapping[str, Any]) -> dict[str, Any]:
    return {name: loader for name, loader in valid_loaders.items() if name != ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD}


def prepare_auxiliary_replay_validation_loader(model: Any, valid_loaders: Mapping[str, Any]) -> dict[str, Any]:
    """Inject the fixed true-label R_light monitor for one-head/naive training."""
    policy = adaptive_stop_policy_from_environment()
    replay_path = os.environ.get(ADAPTIVE_STOP_AUXILIARY_REPLAY_PATH_ENVIRONMENT_VARIABLE)
    if policy is None or not policy.replay_enabled or not replay_path:
        return dict(valid_loaders)
    if policy.replay_head_name in valid_loaders:
        return dict(valid_loaders)
    path = Path(replay_path).expanduser().resolve()
    if not path.is_file():
        raise DeterministicTrainingPreflightError(f"MDSTATS_NONRETRYABLE ADAPT-STOP1 auxiliary true-replay monitor is missing: {path}")
    if not valid_loaders:
        raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE ADAPT-STOP1 cannot infer validation batching without the target loader.")
    target_head = policy.target_head_name
    heads = [str(value) for value in getattr(model, "heads", [target_head])]
    if target_head not in heads:
        if len(heads) != 1:
            raise DeterministicTrainingPreflightError(f"MDSTATS_NONRETRYABLE ADAPT-STOP1 target head {target_head!r} is absent from model heads {heads!r}.")
        target_head = heads[0]
    replay_loader = _validation_loader_from_extxyz(model, valid_loaders, path=path, dataset_head=target_head)
    return {policy.replay_head_name: replay_loader, **dict(valid_loaders)}


def _full_foundation_row(rows: list[dict[str, Any]]) -> float | None:
    full_rows = [item for item in rows if item.get("epoch") is None and str(item.get("head", "")) == ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD]
    for item in reversed(full_rows):
        try:
            value = float(item["rmse_f"])
        except (KeyError, TypeError, ValueError):
            continue
        if math.isfinite(value) and value >= 0.0:
            return value
    return None


def validate_adaptive_stop_foundation_baseline(logger_path: str | Path) -> None:
    """Freeze matched R0_light/R0_full baselines; never use them as feasibility gates."""
    policy = adaptive_stop_policy_from_environment()
    if policy is None or not policy.replay_enabled:
        return
    state_path = _state_path(logger_path)
    state = _load_state(state_path, policy)

    # Historical policy/state evidence retains the old absolute replay meaning.
    if policy.serialization_schema in ADAPTIVE_STOP_POLICY_LEGACY_SCHEMAS:
        if state.foundation_replay_force_rmse_ev_per_angstrom is not None:
            if state.foundation_replay_threshold_feasible is False and not state.foundation_feasibility_overridden:
                raise DeterministicTrainingPreflightError(
                    "MDSTATS_NONRETRYABLE historical replay threshold remains below the frozen foundation baseline."
                )
            return
        rows = _read_validation_rows(logger_path)
        _, replay = _head_metrics(rows, epoch=None, policy=policy)
        if replay is None:
            raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE historical ADAPT-STOP1 requires an initial true-label replay validation row.")
        threshold = policy.maximum_replay_force_rmse_ev_per_angstrom
        assert threshold is not None
        feasible = replay <= threshold
        updated = AdaptiveTrainingStopState(
            policy_digest=policy.policy_digest,
            foundation_replay_force_rmse_ev_per_angstrom=replay,
            foundation_replay_threshold_feasible=feasible,
            foundation_feasibility_overridden=(not feasible and policy.allow_replay_threshold_below_foundation_baseline),
            foundation_replay_evidence_scope="historical_lightweight_true_dft",
            epochs=state.epochs, stop_epoch=state.stop_epoch, stop_reason=state.stop_reason,
            run_outcome=state.run_outcome, serialization_schema=state.serialization_schema,
        )
        _atomic_write_json(state_path, updated.to_dict())
        if not feasible and not policy.allow_replay_threshold_below_foundation_baseline:
            raise DeterministicTrainingPreflightError(
                "MDSTATS_NONRETRYABLE historical derived replay RMSE threshold is below the foundation baseline."
            )
        return

    light_raw = os.environ.get(ADAPTIVE_STOP_REPLAY_LIGHT_PATH_ENVIRONMENT_VARIABLE)
    full_raw = os.environ.get(ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE)
    model_raw = os.environ.get(ADAPTIVE_STOP_FOUNDATION_MODEL_SHA256_ENVIRONMENT_VARIABLE)
    if not light_raw or not full_raw or not model_raw:
        raise DeterministicTrainingPreflightError(
            "MDSTATS_NONRETRYABLE MLCV-STOP1 v3 requires authenticated foundation model, R_light, and R_full bindings."
        )
    light_path = Path(light_raw).expanduser().resolve()
    full_path = Path(full_raw).expanduser().resolve()
    if not light_path.is_file() or not full_path.is_file():
        raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 replay baseline domain is missing.")
    model_sha = validate_digest(model_raw, name="foundation_model_sha256")
    light_sha = sha256_file_cached(light_path)
    full_sha = sha256_file_cached(full_path)

    if state.foundation_replay_light_force_rmse_ev_per_angstrom is not None:
        if state.foundation_model_sha256 != model_sha or state.foundation_replay_light_artifact_sha256 != light_sha or state.foundation_replay_full_artifact_sha256 != full_sha:
            raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 foundation replay baseline lineage changed across exact restart.")
        return

    shared = _load_authenticated_shared_baseline(light_path=light_path, full_path=full_path, model_sha=model_sha)
    if shared is not None:
        light0 = shared.replay_light_foundation_rmse_ev_per_angstrom
        full0 = shared.replay_full_foundation_rmse_ev_per_angstrom
    else:
        rows = _read_validation_rows(logger_path)
        _, light0 = _head_metrics(rows, epoch=None, policy=policy)
        full0 = _full_foundation_row(rows)
        if light0 is None:
            raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 requires the initial matched R_light foundation validation row before epoch 0.")
        if full0 is None:
            raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 requires the one-time matched R_full foundation validation row before epoch 0.")
        shared = ReplayFoundationBaselineRecord(
            foundation_model_sha256=model_sha,
            replay_light_artifact_sha256=light_sha,
            replay_full_artifact_sha256=full_sha,
            replay_light_foundation_rmse_ev_per_angstrom=light0,
            replay_full_foundation_rmse_ev_per_angstrom=full0,
        )
        cache = _baseline_cache_path()
        if cache is not None:
            if cache.is_file():
                # Another process may have won a race; authenticate rather than overwrite.
                existing = ReplayFoundationBaselineRecord.from_dict(json.loads(cache.read_text(encoding="utf-8")))
                if existing.content_digest != shared.content_digest:
                    raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE conflicting shared replay foundation baseline evidence.")
            else:
                _atomic_write_json(cache, shared.to_dict())

    budget = policy.replay_degradation_budget_force_rmse_ev_per_angstrom
    stop_budget = policy.replay_stop_degradation_force_rmse_ev_per_angstrom
    assert budget is not None and stop_budget is not None
    updated = AdaptiveTrainingStopState(
        policy_digest=policy.policy_digest,
        foundation_replay_light_force_rmse_ev_per_angstrom=light0,
        foundation_replay_full_force_rmse_ev_per_angstrom=full0,
        foundation_replay_light_artifact_sha256=light_sha,
        foundation_replay_full_artifact_sha256=full_sha,
        foundation_model_sha256=model_sha,
        foundation_replay_evidence_scope="matched_light_full_true_dft",
        replay_degradation_budget_ev_per_angstrom=budget,
        replay_stop_degradation_ev_per_angstrom=stop_budget,
        replay_light_absolute_ceiling_ev_per_angstrom=light0 + budget,
        replay_full_absolute_ceiling_ev_per_angstrom=full0 + budget,
        epochs=state.epochs, stop_epoch=state.stop_epoch, stop_reason=state.stop_reason,
        run_outcome=state.run_outcome,
    )
    _atomic_write_json(state_path, updated.to_dict())


def adaptive_training_stop_already_terminal(logger_path: str | Path) -> bool:
    policy = adaptive_stop_policy_from_environment()
    if policy is None:
        return False
    state = _load_state(_state_path(logger_path), policy)
    return state.stop_reason is not None and state.stop_epoch is not None


def adaptive_training_stop_requested(logger_path: str | Path, epoch: int, *, target_data_role: MlcvDataRole | str | None = None) -> bool:
    """Record one completed epoch and return whether MACE should stop cleanly."""
    if target_data_role is not None:
        require_mlcv_checkpoint_stopping_role(target_data_role)
    policy = adaptive_stop_policy_from_environment()
    if policy is None:
        return False
    rows = _read_validation_rows(logger_path)
    target, replay = _head_metrics(rows, epoch=int(epoch), policy=policy)
    if target is None:
        raise RuntimeError(f"ADAPT-STOP1 could not find target force RMSE for epoch {epoch}.")
    if policy.replay_enabled and replay is None:
        raise RuntimeError(f"ADAPT-STOP1 could not find true-label replay force RMSE for epoch {epoch}.")
    state_path = _state_path(logger_path)
    state = _load_state(state_path, policy)
    replay_foundation = None
    replay_degradation = None
    if policy.replay_enabled and policy.serialization_schema == ADAPTIVE_STOP_POLICY_SCHEMA:
        replay_foundation = state.foundation_replay_light_force_rmse_ev_per_angstrom
        if replay_foundation is None:
            raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE MLCV-STOP1 cannot score an epoch before R0_light is frozen.")
        replay_degradation = float(replay) - float(replay_foundation)
    eligible = policy.candidate_eligible(target, replay)
    reason = policy.stop_reason(
        epoch=int(epoch), target_rmse=target, replay_rmse=replay,
        foundation_replay_rmse=replay_foundation,
        replay_degradation_rmse=replay_degradation,
    )
    metric = AdaptiveTrainingEpochMetric(
        epoch=int(epoch), target_force_rmse_ev_per_angstrom=target,
        replay_force_rmse_ev_per_angstrom=replay,
        replay_foundation_force_rmse_ev_per_angstrom=replay_foundation,
        replay_degradation_force_rmse_ev_per_angstrom=replay_degradation,
        candidate_eligible=eligible, stop_reason=reason,
    )
    existing = {item.epoch: item for item in state.epochs}
    if int(epoch) in existing:
        prior = existing[int(epoch)]
        if prior != metric:
            raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE adaptive-stop epoch metrics changed across an exact restart.")
        return prior.stop_reason is not None
    if state.stop_reason is not None:
        raise DeterministicTrainingPreflightError("MDSTATS_NONRETRYABLE adaptive-stop state is already terminal; training must not continue past the stop epoch.")
    combined = tuple((*state.epochs, metric))
    terminal = reason is not None
    outcome = "running"
    if terminal:
        outcome = "admissible_checkpoint_available" if any(item.candidate_eligible for item in combined) else "no_lightweight_admissible_checkpoint"
    updated = AdaptiveTrainingStopState(
        policy_digest=policy.policy_digest,
        foundation_replay_force_rmse_ev_per_angstrom=state.foundation_replay_force_rmse_ev_per_angstrom,
        foundation_replay_threshold_feasible=state.foundation_replay_threshold_feasible,
        foundation_feasibility_overridden=state.foundation_feasibility_overridden,
        foundation_replay_evidence_scope=state.foundation_replay_evidence_scope,
        foundation_replay_artifact_sha256=state.foundation_replay_artifact_sha256,
        foundation_replay_light_force_rmse_ev_per_angstrom=state.foundation_replay_light_force_rmse_ev_per_angstrom,
        foundation_replay_full_force_rmse_ev_per_angstrom=state.foundation_replay_full_force_rmse_ev_per_angstrom,
        foundation_replay_light_artifact_sha256=state.foundation_replay_light_artifact_sha256,
        foundation_replay_full_artifact_sha256=state.foundation_replay_full_artifact_sha256,
        foundation_model_sha256=state.foundation_model_sha256,
        replay_degradation_budget_ev_per_angstrom=state.replay_degradation_budget_ev_per_angstrom,
        replay_stop_degradation_ev_per_angstrom=state.replay_stop_degradation_ev_per_angstrom,
        replay_light_absolute_ceiling_ev_per_angstrom=state.replay_light_absolute_ceiling_ev_per_angstrom,
        replay_full_absolute_ceiling_ev_per_angstrom=state.replay_full_absolute_ceiling_ev_per_angstrom,
        epochs=combined, stop_epoch=int(epoch) if terminal else None,
        stop_reason=reason, run_outcome=outcome,
        serialization_schema=state.serialization_schema,
    )
    _atomic_write_json(state_path, updated.to_dict())
    return terminal
