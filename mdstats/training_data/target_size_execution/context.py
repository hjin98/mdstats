"""P3-A seed-neutral target-size execution context.

The context is the immutable study-wide scientific execution identity.  It
binds the P2 experiment definition, the common preparation, the foundation /
replay identity, the seed-neutral training-policy template, the full-screen
TRAIN2 schedule, the objective/weight/E0 identity, precision/backend
semantics, TRAIN2 checkpoint/continuation policy, the EVAL2 target metric
policy, the fixed non-controlling harness-validation identity, and genuine
MACE compatibility constraints.

It excludes candidate-varying state (``N``, ``T_N`` digests, optimizer seed,
active rung/boundary, survivor set, checkpoints/results) and proven
execution-only state.  ``bind_target_size_execution_context`` from P2 remains
the authority that makes execution evidence admissible; this module only
derives and binds the digest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .._common import digest, validate_digest
from .._common import TrainingDataInputError, TrainingDataSerializationError
from ..protocol import MaceOptimizerPolicy
from ..target_size_experiment import (
    TargetSizeExperimentDefinition,
    TargetSizeReducerState,
    bind_target_size_execution_context,
)
from .common import (
    EVAL2_TARGET_METRIC_POLICY_DIGEST,
    TargetSizeCommonPreparation,
)
from .schedule import (
    TARGET_SIZE_SEED_NEUTRAL_POLICY_SCHEMA,
    TargetSizeScreenSchedule,
)

TARGET_SIZE_EXECUTION_CONTEXT_SCHEMA = "mdstats.target-size.execution-context.v1"

_SEED_NEUTRAL_EXCLUDED_FIELDS = (
    "seed",
    "acceleration_realization_digest",
    "resolved_acceleration_kernel_mode",
)


def seed_neutral_optimizer_policy_digest(
    optimizer_policy: MaceOptimizerPolicy,
) -> str:
    """Canonical seed-neutral training-policy identity.

    The current ``MaceOptimizerPolicy`` embeds ``seed`` (and per-realization
    acceleration fields that are bound per candidate instead).  A
    candidate-specific optimizer-policy digest is therefore not a valid
    global context: the seed-neutral identity removes exactly those fields,
    and every candidate policy must equal the template except for the
    authorized seed and the N-derived realization.
    """

    payload = dict(optimizer_policy._payload())
    for name in _SEED_NEUTRAL_EXCLUDED_FIELDS:
        payload.pop(name, None)
    payload["schema"] = TARGET_SIZE_SEED_NEUTRAL_POLICY_SCHEMA
    return digest(payload)


def validate_candidate_optimizer_policy(
    template_digest: str,
    candidate_policy: MaceOptimizerPolicy,
    *,
    authorized_seed: int,
) -> None:
    """Require a candidate policy to equal the seed-neutral template except
    for the authorized optimizer seed."""

    if seed_neutral_optimizer_policy_digest(candidate_policy) != validate_digest(
        template_digest, name="template_digest"
    ):
        raise TrainingDataInputError(
            "Candidate optimizer policy differs from the seed-neutral training-policy template."
        )
    if int(candidate_policy.seed) != int(authorized_seed):
        raise TrainingDataInputError(
            "Candidate optimizer policy does not carry the authorized optimizer seed."
        )


def exact_screen_optimizer_seeds(
    definition: TargetSizeExperimentDefinition,
) -> tuple[int, ...]:
    """The exact ordered screening seed set is P2 policy, never a P3 override."""

    return tuple(int(v) for v in definition.policy.optimizer_seeds)


def validate_screen_seed_population(
    definition: TargetSizeExperimentDefinition,
    seeds: Any,
) -> tuple[int, ...]:
    """Require an exact ordered seed population equal to P2 policy."""

    expected = exact_screen_optimizer_seeds(definition)
    observed = tuple(int(v) for v in seeds)
    if observed != expected:
        raise TrainingDataInputError(
            "The screening seed population must equal the P2 optimizer-seed "
            "policy exactly and in order; a changed seed set is a P2 policy "
            "change, not an execution override."
        )
    return observed


@dataclass(frozen=True, slots=True)
class TargetSizeExecutionContext:
    experiment_definition_digest: str
    common_preparation_digest: str
    common_training_policy_digest: str
    screen_schedule_digest: str
    seed_neutral_optimizer_policy_digest: str
    foundation_identity_digest: str | None
    replay_exposure_policy_digest: str
    precision_backend_policy_digest: str
    train2_checkpoint_policy_digest: str
    eval2_metric_policy_digest: str
    harness_validation_identity_digest: str
    mace_compatibility_policy_digest: str

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "common_preparation_digest",
            "common_training_policy_digest",
            "screen_schedule_digest",
            "seed_neutral_optimizer_policy_digest",
            "replay_exposure_policy_digest",
            "precision_backend_policy_digest",
            "train2_checkpoint_policy_digest",
            "eval2_metric_policy_digest",
            "harness_validation_identity_digest",
            "mace_compatibility_policy_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.foundation_identity_digest is not None:
            object.__setattr__(
                self,
                "foundation_identity_digest",
                validate_digest(
                    self.foundation_identity_digest,
                    name="foundation_identity_digest",
                ),
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_EXECUTION_CONTEXT_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "common_preparation_digest": self.common_preparation_digest,
            "common_training_policy_digest": self.common_training_policy_digest,
            "screen_schedule_digest": self.screen_schedule_digest,
            "seed_neutral_optimizer_policy_digest": (
                self.seed_neutral_optimizer_policy_digest
            ),
            "foundation_identity_digest": self.foundation_identity_digest,
            "replay_exposure_policy_digest": self.replay_exposure_policy_digest,
            "precision_backend_policy_digest": self.precision_backend_policy_digest,
            "train2_checkpoint_policy_digest": self.train2_checkpoint_policy_digest,
            "eval2_metric_policy_digest": self.eval2_metric_policy_digest,
            "harness_validation_identity_digest": (
                self.harness_validation_identity_digest
            ),
            "mace_compatibility_policy_digest": (
                self.mace_compatibility_policy_digest
            ),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeExecutionContext:
        if payload.get("schema") != TARGET_SIZE_EXECUTION_CONTEXT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size execution-context schema."
            )
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            common_preparation_digest=str(payload["common_preparation_digest"]),
            common_training_policy_digest=str(
                payload["common_training_policy_digest"]
            ),
            screen_schedule_digest=str(payload["screen_schedule_digest"]),
            seed_neutral_optimizer_policy_digest=str(
                payload["seed_neutral_optimizer_policy_digest"]
            ),
            foundation_identity_digest=(
                None
                if payload.get("foundation_identity_digest") is None
                else str(payload["foundation_identity_digest"])
            ),
            replay_exposure_policy_digest=str(
                payload["replay_exposure_policy_digest"]
            ),
            precision_backend_policy_digest=str(
                payload["precision_backend_policy_digest"]
            ),
            train2_checkpoint_policy_digest=str(
                payload["train2_checkpoint_policy_digest"]
            ),
            eval2_metric_policy_digest=str(payload["eval2_metric_policy_digest"]),
            harness_validation_identity_digest=str(
                payload["harness_validation_identity_digest"]
            ),
            mace_compatibility_policy_digest=str(
                payload["mace_compatibility_policy_digest"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Target-size execution-context digest mismatch."
            )
        return result

    def validate_bindings(
        self,
        definition: TargetSizeExperimentDefinition,
        common_preparation: TargetSizeCommonPreparation,
        schedule: TargetSizeScreenSchedule,
    ) -> None:
        """Fail closed unless the context binds the supplied authorities."""

        if self.experiment_definition_digest != definition.content_digest:
            raise TrainingDataInputError(
                "Execution context binds a different experiment definition."
            )
        if self.common_preparation_digest != common_preparation.content_digest:
            raise TrainingDataInputError(
                "Execution context binds a different common preparation."
            )
        if (
            self.common_training_policy_digest
            != common_preparation.common_training_policy_digest
        ):
            raise TrainingDataInputError(
                "Execution context binds a different common training policy."
            )
        if self.screen_schedule_digest != schedule.content_digest:
            raise TrainingDataInputError(
                "Execution context binds a different full-screen TRAIN2 schedule."
            )

    def bind(
        self,
        definition: TargetSizeExperimentDefinition,
        reducer_state: TargetSizeReducerState,
    ) -> TargetSizeReducerState:
        """Bind this context through the P2 owner that admits evidence."""

        return bind_target_size_execution_context(
            definition, reducer_state, self.content_digest
        )


def build_target_size_execution_context(
    definition: TargetSizeExperimentDefinition,
    common_preparation: TargetSizeCommonPreparation,
    schedule: TargetSizeScreenSchedule,
    *,
    seed_neutral_optimizer_policy: MaceOptimizerPolicy,
    foundation_identity_digest: str | None = None,
    precision_backend_policy_digest: str | None = None,
    train2_checkpoint_policy_digest: str | None = None,
    mace_compatibility_policy_digest: str | None = None,
) -> TargetSizeExecutionContext:
    """Build the one seed-neutral execution context for the whole screen.

    Only study-wide identities are accepted.  Candidate size, optimizer seed,
    rung, boundary, survivor set, and worker/resource-only fields are not
    inputs to this builder and cannot enter the context.
    """

    if common_preparation.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Common preparation does not bind the supplied experiment definition."
        )
    return TargetSizeExecutionContext(
        experiment_definition_digest=definition.content_digest,
        common_preparation_digest=common_preparation.content_digest,
        common_training_policy_digest=common_preparation.common_training_policy_digest,
        screen_schedule_digest=schedule.content_digest,
        seed_neutral_optimizer_policy_digest=seed_neutral_optimizer_policy_digest(
            seed_neutral_optimizer_policy
        ),
        foundation_identity_digest=foundation_identity_digest,
        replay_exposure_policy_digest=digest(
            {
                "schema": "mdstats.target-size.replay-exposure.v1",
                "mode": "none",
                "foundation_identity_digest": foundation_identity_digest,
            }
        ),
        precision_backend_policy_digest=(
            digest(
                {
                    "schema": "mdstats.target-size.precision-backend.v1",
                    "default_dtype": seed_neutral_optimizer_policy.default_dtype,
                    "device": seed_neutral_optimizer_policy.device,
                    "batch_size": seed_neutral_optimizer_policy.batch_size,
                    "critical_precision_policy": (
                        seed_neutral_optimizer_policy.critical_precision_policy.to_dict()
                    ),
                }
            )
            if precision_backend_policy_digest is None
            else validate_digest(
                precision_backend_policy_digest,
                name="precision_backend_policy_digest",
            )
        ),
        train2_checkpoint_policy_digest=(
            schedule.budget_policy.policy_digest
            if train2_checkpoint_policy_digest is None
            else validate_digest(
                train2_checkpoint_policy_digest,
                name="train2_checkpoint_policy_digest",
            )
        ),
        eval2_metric_policy_digest=(
            # Frozen global force-component RMSE reduction policy identity;
            # transitively covered by the common training policy digest.
            EVAL2_TARGET_METRIC_POLICY_DIGEST
        ),
        harness_validation_identity_digest=digest(
            {
                "schema": "mdstats.target-size.harness-validation.v1",
                "membership_digest": (
                    common_preparation.harness_validation_membership_digest
                ),
                "non_controlling": True,
            }
        ),
        mace_compatibility_policy_digest=(
            digest(
                {
                    "schema": "mdstats.target-size.mace-compatibility.v1",
                    "acceleration_policy": (
                        seed_neutral_optimizer_policy.acceleration_policy.to_dict()
                    ),
                }
            )
            if mace_compatibility_policy_digest is None
            else validate_digest(
                mace_compatibility_policy_digest,
                name="mace_compatibility_policy_digest",
            )
        ),
    )


__all__ = [
    "TARGET_SIZE_EXECUTION_CONTEXT_SCHEMA",
    "TargetSizeExecutionContext",
    "build_target_size_execution_context",
    "exact_screen_optimizer_seeds",
    "seed_neutral_optimizer_policy_digest",
    "validate_candidate_optimizer_policy",
    "validate_screen_seed_population",
]
