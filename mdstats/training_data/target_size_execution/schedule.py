"""P3-A full-screen TRAIN2 schedule, rung pause limits, and optimizer normalization.

One screen trajectory ends at ``n3 = definition.policy.fidelity_epochs[2]``.
For each candidate the full budget/LR trajectory is derived once and the
rungs ``n1``/``n2``/``n3`` are realized exclusively through
``Train2RuntimePlan.execution_epoch_limit`` pauses inside that one frozen
budget.  Independent rung-normalized LR schedules are never constructed.

The screen-specific ``n3`` horizon is distinct from the fresh
final-production horizon; changing the production-only horizon cannot alter
the screen schedule identity.

This module also owns the target-size optimizer-normalization policy.  A
target-size candidate at cardinality ``N`` performs ``ceil(N/B)`` optimizer
updates per epoch under a fixed number of dataset passes, so a larger ``N``
receives strictly more optimizer progress at the same nominal learning rate
and EMA decay.  That confound is not part of the question the screen asks -
"how much unique target data is needed" - so amplitude is normalized against
one configurable reference size while every other optimizer setting stays
fixed across candidates.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from .._common import digest, validate_digest
from .._common import TrainingDataInputError, TrainingDataSerializationError
from ..train2_policy import (
    LearningRateSchedulePolicy,
    TrainingBudgetPolicy,
)
from ..train2_runtime import Train2RuntimePlan

TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA = "mdstats.target-size.screen-schedule.v2"
TARGET_SIZE_SEED_NEUTRAL_POLICY_SCHEMA = "mdstats.target-size.seed-neutral-policy.v1"
TARGET_SIZE_OPTIMIZER_NORMALIZATION_SCHEMA = (
    "mdstats.target-size.optimizer-normalization-policy.v1"
)

FRESH_FINAL_PRODUCTION_HORIZON_EPOCHS = 30

#: Fixed defaults for the target-size optimizer-normalization reference point.
DEFAULT_REFERENCE_TARGET_SIZE = 1024
DEFAULT_REFERENCE_LEARNING_RATE = 1.0e-4
DEFAULT_REFERENCE_EMA_DECAY = 0.99999

#: The specification-owned normalization algorithm.  The reference *values* are
#: user-configurable; the algorithm identity is not a user plugin string.
TARGET_SIZE_NORMALIZATION_ALGORITHM = "batch_aware_inverse_update_scaling.v1"


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return int(value)


@dataclass(frozen=True, slots=True)
class TargetSizeOptimizerNormalizationPolicy:
    """Normalize optimizer-progress amplitude against one reference target size.

    Under the screen's fixed number of dataset passes and fixed batch size ``B``,
    candidate ``N`` performs ``U_N = ceil(N/B)`` optimizer updates per epoch.
    Holding the nominal learning rate and EMA decay fixed therefore gives larger
    candidates strictly more optimizer progress, which is a second independent
    variable the target-size experiment never intended to introduce.

    The correction is exact and batch-aware::

        U_ref = ceil(N_ref / B)
        U_N   = ceil(N / B)
        s_N   = U_ref / U_N
        LR(N)   = reference_learning_rate * s_N
        beta(N) = reference_ema_decay ** s_N

    so that ``LR(N) * U_N`` and ``beta(N) ** U_N`` are invariant in ``N``, and an
    exact doubling of update geometry halves the learning rate and takes the
    square root of the EMA decay.  There is deliberately no cap, floor,
    clipping, survivor-dependent rescaling, or candidate-specific override: any
    of those would reintroduce an unmodelled size-dependent variable.

    This is a first-order progress normalization, not a claim of exact
    optimizer-path equivalence.  Minibatch noise, Adam moment history, and the
    finite discretization of the analytic LR curve remain accepted residuals.
    """

    reference_target_size: int = DEFAULT_REFERENCE_TARGET_SIZE
    reference_learning_rate: float = DEFAULT_REFERENCE_LEARNING_RATE
    reference_ema_decay: float = DEFAULT_REFERENCE_EMA_DECAY
    algorithm: str = TARGET_SIZE_NORMALIZATION_ALGORITHM

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference_target_size",
            _positive_int(self.reference_target_size, name="reference_target_size"),
        )
        lr = float(self.reference_learning_rate)
        if not math.isfinite(lr) or lr <= 0.0:
            raise TrainingDataInputError(
                "reference_learning_rate must be finite and strictly positive."
            )
        object.__setattr__(self, "reference_learning_rate", lr)
        beta = float(self.reference_ema_decay)
        if not math.isfinite(beta) or not 0.0 < beta < 1.0:
            raise TrainingDataInputError(
                "reference_ema_decay must be finite and satisfy 0 < beta < 1."
            )
        object.__setattr__(self, "reference_ema_decay", beta)
        if self.algorithm != TARGET_SIZE_NORMALIZATION_ALGORITHM:
            raise TrainingDataInputError(
                "Only the specification-owned target-size normalization algorithm "
                f"{TARGET_SIZE_NORMALIZATION_ALGORITHM!r} is supported."
            )

    def reference_updates_per_epoch(self, batch_size: int) -> int:
        """``U_ref = ceil(N_ref / B)`` for the authenticated screen batch size."""

        batch = _positive_int(batch_size, name="batch_size")
        return int(math.ceil(self.reference_target_size / float(batch)))

    def optimizer_progress_scale(
        self, *, batch_size: int, updates_per_epoch: int
    ) -> float:
        """``s_N = U_ref / U_N`` from the candidate's actual update geometry."""

        observed = _positive_int(updates_per_epoch, name="updates_per_epoch")
        return self.reference_updates_per_epoch(batch_size) / float(observed)

    def effective_base_learning_rate(self, scale: float) -> float:
        value = self.reference_learning_rate * float(scale)
        if not math.isfinite(value) or value <= 0.0:
            raise TrainingDataInputError(
                "Normalized target-size learning rate is not finite and positive."
            )
        return value

    def effective_ema_decay(self, scale: float) -> float:
        value = float(self.reference_ema_decay) ** float(scale)
        if not math.isfinite(value) or not 0.0 < value < 1.0:
            raise TrainingDataInputError(
                "Normalized target-size EMA decay left the open interval (0, 1)."
            )
        return value

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_OPTIMIZER_NORMALIZATION_SCHEMA,
            "algorithm": self.algorithm,
            "reference_target_size": self.reference_target_size,
            "reference_learning_rate": self.reference_learning_rate,
            "reference_ema_decay": self.reference_ema_decay,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def policy_digest(self) -> str:
        return self.content_digest

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizeOptimizerNormalizationPolicy:
        if payload.get("schema") != TARGET_SIZE_OPTIMIZER_NORMALIZATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size optimizer-normalization policy schema."
            )
        result = cls(
            reference_target_size=int(payload["reference_target_size"]),
            reference_learning_rate=float(payload["reference_learning_rate"]),
            reference_ema_decay=float(payload["reference_ema_decay"]),
            algorithm=str(payload["algorithm"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size optimizer-normalization policy digest mismatch."
            )
        return result


def resolve_target_size_optimizer_normalization_policy(
    config: Mapping[str, Any],
) -> TargetSizeOptimizerNormalizationPolicy:
    """Resolve ``[target_data.size_convergence.optimizer_normalization]``.

    This is the sole reference-value authority for the screen.  ``[training]``
    ``learning_rate`` is a production-side setting and never supplies the screen
    reference amplitude, so a candidate's realized LR cannot silently depend on
    two competing configuration owners.
    """

    target_data = config.get("target_data", {})
    if not isinstance(target_data, Mapping):
        raise TrainingDataInputError("[target_data] must be a table.")
    size = target_data.get("size_convergence", {})
    if not isinstance(size, Mapping):
        raise TrainingDataInputError("[target_data.size_convergence] must be a table.")
    table = size.get("optimizer_normalization", {})
    if not isinstance(table, Mapping):
        raise TrainingDataInputError(
            "[target_data.size_convergence.optimizer_normalization] must be a table."
        )
    return TargetSizeOptimizerNormalizationPolicy(
        reference_target_size=int(
            table.get("reference_target_size", DEFAULT_REFERENCE_TARGET_SIZE)
        ),
        reference_learning_rate=float(
            table.get("reference_learning_rate", DEFAULT_REFERENCE_LEARNING_RATE)
        ),
        reference_ema_decay=float(
            table.get("reference_ema_decay", DEFAULT_REFERENCE_EMA_DECAY)
        ),
    )


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
    normalization_policy: TargetSizeOptimizerNormalizationPolicy = field(
        default_factory=TargetSizeOptimizerNormalizationPolicy
    )
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

    def realized_learning_rate_policy(
        self, effective_base_learning_rate: float
    ) -> LearningRateSchedulePolicy:
        """The candidate LR schedule: reference shape, normalized amplitude.

        Only ``base_learning_rate`` differs from the reference policy.  The
        phase fractions and the normalized-progress multiplier shape are
        deliberately identical across candidates, because the confound being
        removed is amplitude per unit of data, not schedule shape.
        """

        value = float(effective_base_learning_rate)
        if not math.isfinite(value) or value <= 0.0:
            raise TrainingDataInputError(
                "A realized target-size learning rate must be finite and positive."
            )
        return replace(self.learning_rate_policy, base_learning_rate=value)

    def runtime_plan(
        self,
        *,
        training_protocol_digest: str,
        optimizer_policy_digest: str,
        structures_per_epoch: int,
        execution_epoch_limit: int,
        learning_rate_policy: LearningRateSchedulePolicy | None = None,
        target_head_name: str = "target_head",
        replay_head_name: str = "pt_head",
    ) -> Train2RuntimePlan:
        """Derive one TRAIN2 runtime plan inside the single frozen budget.

        ``execution_epoch_limit`` is the only rung-varying input: it is the
        pause limit (n1, then n2, then n3) inside the one full-n3 budget.
        ``learning_rate_policy`` carries the candidate's realized normalized
        amplitude; it is derived once per candidate from the full candidate
        geometry and is byte-identical across that candidate's rungs.
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
            learning_rate_policy=(
                self.learning_rate_policy
                if learning_rate_policy is None
                else learning_rate_policy
            ),
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
            "normalization_policy": self.normalization_policy.to_dict(),
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
            normalization_policy=TargetSizeOptimizerNormalizationPolicy.from_dict(
                payload["normalization_policy"]
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
    normalization_policy: TargetSizeOptimizerNormalizationPolicy | None = None,
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
    active_normalization = (
        TargetSizeOptimizerNormalizationPolicy()
        if normalization_policy is None
        else normalization_policy
    )
    active_lr = (
        LearningRateSchedulePolicy() if learning_rate_policy is None else learning_rate_policy
    )
    # The normalization policy is the sole amplitude authority for the screen.
    # Binding the reference LR into the schedule's own policy removes the second
    # competing default and makes ``s_N == 1`` reproduce it exactly.
    active_lr = replace(
        active_lr, base_learning_rate=active_normalization.reference_learning_rate
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
        normalization_policy=active_normalization,
        production_horizon_epochs=production_horizon_epochs,
    )


__all__ = [
    "DEFAULT_REFERENCE_EMA_DECAY",
    "DEFAULT_REFERENCE_LEARNING_RATE",
    "DEFAULT_REFERENCE_TARGET_SIZE",
    "FRESH_FINAL_PRODUCTION_HORIZON_EPOCHS",
    "TARGET_SIZE_NORMALIZATION_ALGORITHM",
    "TARGET_SIZE_OPTIMIZER_NORMALIZATION_SCHEMA",
    "TARGET_SIZE_SCREEN_SCHEDULE_SCHEMA",
    "TARGET_SIZE_SEED_NEUTRAL_POLICY_SCHEMA",
    "TargetSizeOptimizerNormalizationPolicy",
    "TargetSizeScreenSchedule",
    "build_target_size_screen_schedule",
    "resolve_target_size_optimizer_normalization_policy",
]
