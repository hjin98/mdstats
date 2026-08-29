"""P3-A full-screen TRAIN2 schedule with rung pause limits.

One screen trajectory ends at ``n3 = definition.policy.fidelity_epochs[2]``.
For each candidate the full budget/LR trajectory is derived once and the
rungs ``n1``/``n2``/``n3`` are realized exclusively through
``Train2RuntimePlan.execution_epoch_limit`` pauses inside that one frozen
budget.  Independent rung-normalized LR schedules are never constructed.

The screen-specific ``n3`` horizon is distinct from the fresh
final-production horizon; changing the production-only horizon cannot alter
the screen schedule identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .._common import digest, validate_digest
from .._common import TrainingDataInputError, TrainingDataSerializationError
from ..train2_policy import (
    LearningRateSchedulePolicy,
    TrainingBudgetPolicy,
)
from ..train2_runtime import Train2RuntimePlan

TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA = "mdstats.target-size.screen-schedule.v1"
TARGET_SIZE_SEED_NEUTRAL_POLICY_SCHEMA = "mdstats.target-size.seed-neutral-policy.v1"

FRESH_FINAL_PRODUCTION_HORIZON_EPOCHS = 30


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return int(value)


@dataclass(frozen=True, slots=True)
class TargetSizeScreenSchedule:
    """One frozen full-screen TRAIN2 budget/LR trajectory with rung limits.

    ``production_horizon_epochs`` records the fresh final-production horizon
    for operational bookkeeping only.  It is deliberately excluded from the
    schedule payload/digest: it is not part of the screen's scientific
    identity, and changing it must not invalidate a completed screen.
    """

    fidelity_epochs: tuple[int, int, int]
    budget_policy: TrainingBudgetPolicy
    learning_rate_policy: LearningRateSchedulePolicy
    production_horizon_epochs: int = FRESH_FINAL_PRODUCTION_HORIZON_EPOCHS

    def __post_init__(self) -> None:
        epochs = tuple(
            _positive_int(v, name="fidelity epoch") for v in self.fidelity_epochs
        )
        if len(epochs) != 3 or not (epochs[0] < epochs[1] < epochs[2]):
            raise TrainingDataInputError(
                "Screen fidelity epochs must be three strictly increasing completed-epoch counts."
            )
        object.__setattr__(self, "fidelity_epochs", epochs)
        horizon = _positive_int(
            self.production_horizon_epochs, name="production_horizon_epochs"
        )
        object.__setattr__(self, "production_horizon_epochs", horizon)
        if self.budget_policy.planned_epochs != epochs[2]:
            raise TrainingDataInputError(
                "The full-screen TRAIN2 budget must end exactly at the terminal fidelity epoch."
            )
        if self.budget_policy.allow_performance_driven_termination:
            raise TrainingDataInputError(
                "Screen training forbids performance-driven termination inside the frozen budget."
            )

    @property
    def n1(self) -> int:
        return self.fidelity_epochs[0]

    @property
    def n2(self) -> int:
        return self.fidelity_epochs[1]

    @property
    def n3(self) -> int:
        return self.fidelity_epochs[2]

    def boundary_epochs(self) -> tuple[int, ...]:
        return self.fidelity_epochs

    def validate_boundary_epoch(self, epoch: int) -> int:
        value = _positive_int(epoch, name="boundary epoch")
        if value not in self.fidelity_epochs:
            raise TrainingDataInputError(
                "Boundary epoch is not one of the configured screen rungs."
            )
        return value

    def runtime_plan(
        self,
        *,
        training_protocol_digest: str,
        optimizer_policy_digest: str,
        structures_per_epoch: int,
        execution_epoch_limit: int,
        target_head_name: str = "target_head",
        replay_head_name: str = "pt_head",
    ) -> Train2RuntimePlan:
        """Derive one TRAIN2 runtime plan inside the single frozen budget.

        ``execution_epoch_limit`` is the only rung-varying input: it is the
        pause limit (n1, then n2, then n3) inside the one full-n3 budget.
        """

        limit = _positive_int(execution_epoch_limit, name="execution_epoch_limit")
        if limit not in self.fidelity_epochs:
            raise TrainingDataInputError(
                "Screen execution_epoch_limit must be one of the configured rungs."
            )
        return Train2RuntimePlan(
            training_protocol_digest=validate_digest(
                training_protocol_digest, name="training_protocol_digest"
            ),
            optimizer_policy_digest=validate_digest(
                optimizer_policy_digest, name="optimizer_policy_digest"
            ),
            budget_policy=self.budget_policy,
            learning_rate_policy=self.learning_rate_policy,
            structures_per_epoch=structures_per_epoch,
            target_head_name=target_head_name,
            replay_head_name=replay_head_name,
            execution_epoch_limit=limit,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA,
            "fidelity_epochs": list(self.fidelity_epochs),
            "budget_policy": self.budget_policy.to_dict(),
            "learning_rate_policy": self.learning_rate_policy.to_dict(),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeScreenSchedule:
        if payload.get("schema") != TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size screen-schedule schema."
            )
        result = cls(
            fidelity_epochs=tuple(int(v) for v in payload["fidelity_epochs"]),
            budget_policy=TrainingBudgetPolicy.from_dict(payload["budget_policy"]),
            learning_rate_policy=LearningRateSchedulePolicy.from_dict(
                payload["learning_rate_policy"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size screen-schedule digest mismatch."
            )
        return result


def build_target_size_screen_schedule(
    fidelity_epochs: tuple[int, int, int],
    *,
    learning_rate_policy: LearningRateSchedulePolicy | None = None,
    production_horizon_epochs: int = FRESH_FINAL_PRODUCTION_HORIZON_EPOCHS,
    budget_policy: TrainingBudgetPolicy | None = None,
) -> TargetSizeScreenSchedule:
    """Build the one full-screen TRAIN2 schedule for a P2 policy.

    The budget always ends at ``n3``; the fresh final-production horizon is
    accepted only as non-scientific bookkeeping and never enters the budget
    or the schedule identity.
    """

    epochs = tuple(
        _positive_int(v, name="fidelity epoch") for v in fidelity_epochs
    )
    if len(epochs) != 3 or not (epochs[0] < epochs[1] < epochs[2]):
        raise TrainingDataInputError(
            "Screen fidelity epochs must be three strictly increasing completed-epoch counts."
        )
    active_lr = (
        LearningRateSchedulePolicy() if learning_rate_policy is None else learning_rate_policy
    )
    active_budget = (
        TrainingBudgetPolicy(planned_epochs=epochs[2])
        if budget_policy is None
        else budget_policy
    )
    return TargetSizeScreenSchedule(
        fidelity_epochs=epochs,
        budget_policy=active_budget,
        learning_rate_policy=active_lr,
        production_horizon_epochs=production_horizon_epochs,
    )


__all__ = [
    "FRESH_FINAL_PRODUCTION_HORIZON_EPOCHS",
    "TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA",
    "TARGET_SIZE_SEED_NEUTRAL_POLICY_SCHEMA",
    "TargetSizeScreenSchedule",
    "build_target_size_screen_schedule",
]
