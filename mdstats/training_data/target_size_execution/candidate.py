"""P3-B candidate realization, trajectory identity, and materialization.

One scientific trajectory exists per required ``(N, optimizer_seed)`` — not
one per rung.  The trajectory binds its accepted parents (experiment
definition, execution context, exact ``T_N`` membership, authorized seed,
seed-neutral training-policy identity, common preparation, replay/foundation
identity) plus the deterministic N/seed-derived realization facts (effective
counts, update geometry, precision, acceleration, harness-validation
artifact identity, full-``n3`` planned updates).

Materialization reuses the proven low-level DATA8/MACE mechanisms (exact
ExtXYZ export with canonical parentage, atomic publication, content-addressed
reuse) through the generic exact-membership primitive in
``target_size_execution.export``; it never enters the legacy
``ProductionMaterializationPlan``/``build_data8_preparation_bundle`` topology.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..mace_export import MaceExtxyzPolicy
from ..protocol import MaceOptimizerPolicy
from ..target_size_experiment import (
    TargetSizeExperimentDefinition,
    target_training_prefix_digest,
)
from .common import (
    TargetSizeCandidatePreparation,
    TargetSizeCommonPreparation,
    project_target_size_candidate_preparation,
)
from .context import TargetSizeExecutionContext
from .persistence import (
    publish_immutable_bytes_create_or_verify,
    publish_immutable_json_create_or_verify,
)
from .export import (
    TargetSizeExtxyzArtifact,
    validate_target_size_extxyz_artifact,
    write_target_size_extxyz_artifact,
)
from .schedule import TargetSizeScreenSchedule

TARGET_SIZE_REALIZATION_SCHEMA = "mdstats.target-size.candidate-realization.v1"
TARGET_SIZE_TRAJECTORY_SCHEMA = "mdstats.target-size.candidate-trajectory.v1"
TARGET_SIZE_MATERIALIZATION_SCHEMA = "mdstats.target-size.candidate-materialization.v1"
TARGET_SIZE_MACE_CONFIG_SCHEMA = "mdstats.target-size.mace-config.v1"


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise TrainingDataInputError(f"{name} must be a positive integer.")
    return int(value)


@dataclass(frozen=True, slots=True)
class TargetSizeCandidateRealization:
    """Deterministic N/seed-derived execution facts for one candidate.

    These are consequences of fixed policy plus ``N``/seed, never additional
    experimental variables.  A stale trajectory whose loader/update geometry
    or precision realization differs from the current exact ``T_N`` must be
    rejected even when the global execution-context digest matches.
    """

    target_train_count: int
    replay_train_count: int
    harness_validation_count: int
    batch_size: int
    structures_per_epoch: int
    updates_per_epoch: int
    planned_updates: int
    planned_structures_presented: int
    default_dtype: str
    precision_schedule_digest: str
    acceleration_realization_digest: str | None
    loader_geometry_digest: str
    optimizer_seed: int
    max_num_epochs: int

    def __post_init__(self) -> None:
        for name in (
            "target_train_count",
            "harness_validation_count",
            "batch_size",
            "structures_per_epoch",
            "updates_per_epoch",
            "planned_updates",
            "planned_structures_presented",
            "max_num_epochs",
        ):
            object.__setattr__(
                self, name, _positive_int(getattr(self, name), name=name)
            )
        replay = int(self.replay_train_count)
        if replay < 0:
            raise TrainingDataInputError(
                "replay_train_count must be nonnegative."
            )
        object.__setattr__(self, "replay_train_count", replay)
        if (
            isinstance(self.optimizer_seed, bool)
            or not isinstance(self.optimizer_seed, int)
            or self.optimizer_seed < 0
        ):
            raise TrainingDataInputError("optimizer_seed must be a nonnegative integer.")
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Unsupported candidate default dtype.")
        object.__setattr__(
            self,
            "precision_schedule_digest",
            validate_digest(
                self.precision_schedule_digest, name="precision_schedule_digest"
            ),
        )
        if self.acceleration_realization_digest is not None:
            object.__setattr__(
                self,
                "acceleration_realization_digest",
                validate_digest(
                    self.acceleration_realization_digest,
                    name="acceleration_realization_digest",
                ),
            )
        object.__setattr__(
            self, "loader_geometry_digest", validate_digest(self.loader_geometry_digest, name="loader_geometry_digest")
        )
        expected_structures = self.target_train_count + self.replay_train_count
        if self.structures_per_epoch != expected_structures:
            raise TrainingDataInputError(
                "Candidate structures_per_epoch must equal target plus replay counts."
            )
        expected_updates = int(
            math.ceil(expected_structures / float(self.batch_size))
        )
        if self.updates_per_epoch != expected_updates:
            raise TrainingDataInputError(
                "Candidate updates_per_epoch must equal ceil(structures/batch)."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_REALIZATION_SCHEMA,
            "target_train_count": self.target_train_count,
            "replay_train_count": self.replay_train_count,
            "harness_validation_count": self.harness_validation_count,
            "batch_size": self.batch_size,
            "structures_per_epoch": self.structures_per_epoch,
            "updates_per_epoch": self.updates_per_epoch,
            "planned_updates": self.planned_updates,
            "planned_structures_presented": self.planned_structures_presented,
            "default_dtype": self.default_dtype,
            "precision_schedule_digest": self.precision_schedule_digest,
            "acceleration_realization_digest": self.acceleration_realization_digest,
            "loader_geometry_digest": self.loader_geometry_digest,
            "optimizer_seed": self.optimizer_seed,
            "max_num_epochs": self.max_num_epochs,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCandidateRealization:
        if payload.get("schema") != TARGET_SIZE_REALIZATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported candidate-realization schema."
            )
        result = cls(
            target_train_count=int(payload["target_train_count"]),
            replay_train_count=int(payload["replay_train_count"]),
            harness_validation_count=int(payload["harness_validation_count"]),
            batch_size=int(payload["batch_size"]),
            structures_per_epoch=int(payload["structures_per_epoch"]),
            updates_per_epoch=int(payload["updates_per_epoch"]),
            planned_updates=int(payload["planned_updates"]),
            planned_structures_presented=int(
                payload["planned_structures_presented"]
            ),
            default_dtype=str(payload["default_dtype"]),
            precision_schedule_digest=str(payload["precision_schedule_digest"]),
            acceleration_realization_digest=(
                None
                if payload.get("acceleration_realization_digest") is None
                else str(payload["acceleration_realization_digest"])
            ),
            loader_geometry_digest=str(payload["loader_geometry_digest"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            max_num_epochs=int(payload["max_num_epochs"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Candidate-realization digest mismatch."
            )
        return result


def derive_target_size_candidate_realization(
    *,
    schedule: TargetSizeScreenSchedule,
    projection: TargetSizeCandidatePreparation,
    common: TargetSizeCommonPreparation,
    optimizer_policy: MaceOptimizerPolicy,
    optimizer_seed: int,
    replay_train_count: int = 0,
) -> TargetSizeCandidateRealization:
    """Derive the deterministic realization for one exact candidate."""

    target_train_count = _positive_int(
        len(projection.candidate_membership), name="target_train_count"
    )
    replay = int(replay_train_count)
    if replay < 0:
        raise TrainingDataInputError("replay_train_count must be nonnegative.")
    harness_count = _positive_int(
        len(common.harness_validation_membership),
        name="harness_validation_count",
    )
    structures_per_epoch = target_train_count + replay
    batch_size = _positive_int(optimizer_policy.batch_size, name="batch_size")
    updates_per_epoch = int(math.ceil(structures_per_epoch / float(batch_size)))
    precision_schedule = optimizer_policy.precision_schedule_policy
    precision_digest = (
        digest({"default_dtype": optimizer_policy.default_dtype, "schedule": None})
        if precision_schedule is None
        else digest(
            {
                "default_dtype": optimizer_policy.default_dtype,
                "schedule": precision_schedule.to_dict(),
            }
        )
    )
    loader_geometry_digest = digest(
        {
            "schema": "mdstats.target-size.loader-geometry.v1",
            "candidate_membership_digest": projection.candidate_membership_digest,
            "harness_validation_membership_digest": (
                common.harness_validation_membership_digest
            ),
            "target_train_count": target_train_count,
            "replay_train_count": replay,
            "batch_size": batch_size,
            "valid_batch_size": optimizer_policy.valid_batch_size,
        }
    )
    return TargetSizeCandidateRealization(
        target_train_count=target_train_count,
        replay_train_count=replay,
        harness_validation_count=harness_count,
        batch_size=batch_size,
        structures_per_epoch=structures_per_epoch,
        updates_per_epoch=updates_per_epoch,
        planned_updates=updates_per_epoch * schedule.n3,
        planned_structures_presented=structures_per_epoch * schedule.n3,
        default_dtype=optimizer_policy.default_dtype,
        precision_schedule_digest=precision_digest,
        acceleration_realization_digest=optimizer_policy.acceleration_realization_digest,
        loader_geometry_digest=loader_geometry_digest,
        optimizer_seed=int(optimizer_seed),
        max_num_epochs=schedule.n3,
    )


@dataclass(frozen=True, slots=True)
class TargetSizeCandidateTrajectory:
    """One scientific trajectory per ``(N, optimizer_seed)``.

    Rung records descend from the trajectory and add active
    boundary/continuation ancestry; they never redefine the candidate.
    """

    experiment_definition_digest: str
    execution_context_digest: str
    target_size: int
    training_order_digest: str
    candidate_membership_digest: str
    candidate_membership: tuple[str, ...]
    optimizer_seed: int
    seed_neutral_training_policy_digest: str
    common_preparation_digest: str
    replay_foundation_identity_digest: str
    realization: TargetSizeCandidateRealization
    evaluation_model_state: str
    candidate_training_protocol_digest: str

    def __post_init__(self) -> None:
        for name in (
            "experiment_definition_digest",
            "execution_context_digest",
            "training_order_digest",
            "candidate_membership_digest",
            "seed_neutral_training_policy_digest",
            "common_preparation_digest",
            "replay_foundation_identity_digest",
            "candidate_training_protocol_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        target_size = _positive_int(self.target_size, name="target_size")
        object.__setattr__(self, "target_size", target_size)
        membership = tuple(str(v) for v in self.candidate_membership)
        if (
            len(membership) != target_size
            or len(set(membership)) != len(membership)
        ):
            raise TrainingDataInputError(
                "Trajectory membership must have exactly target_size unique frames."
            )
        if (
            target_training_prefix_digest(
                self.training_order_digest, target_size, membership
            )
            != self.candidate_membership_digest
        ):
            raise TrainingDataInputError(
                "Trajectory membership does not match its digest."
            )
        object.__setattr__(self, "candidate_membership", membership)
        evaluation_state = str(self.evaluation_model_state)
        if evaluation_state not in ("live", "ema"):
            raise TrainingDataInputError(
                "Trajectory must freeze its evaluation model-state representation."
            )
        object.__setattr__(self, "evaluation_model_state", evaluation_state)
        if (
            self.realization.optimizer_seed != self.optimizer_seed
            or self.realization.target_train_count != target_size
        ):
            raise TrainingDataInputError(
                "Trajectory realization does not bind this candidate."
            )

    def trajectory_id(self) -> str:
        return digest(
            {
                "schema": "mdstats.target-size.trajectory-id.v1",
                "trajectory_digest": self.content_digest,
            }
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_TRAJECTORY_SCHEMA,
            "experiment_definition_digest": self.experiment_definition_digest,
            "execution_context_digest": self.execution_context_digest,
            "target_size": self.target_size,
            "training_order_digest": self.training_order_digest,
            "candidate_membership_digest": self.candidate_membership_digest,
            "candidate_membership": list(self.candidate_membership),
            "optimizer_seed": self.optimizer_seed,
            "seed_neutral_training_policy_digest": (
                self.seed_neutral_training_policy_digest
            ),
            "common_preparation_digest": self.common_preparation_digest,
            "replay_foundation_identity_digest": (
                self.replay_foundation_identity_digest
            ),
            "realization": self.realization.to_dict(),
            "evaluation_model_state": self.evaluation_model_state,
            "candidate_training_protocol_digest": (
                self.candidate_training_protocol_digest
            ),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCandidateTrajectory:
        if payload.get("schema") != TARGET_SIZE_TRAJECTORY_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported candidate-trajectory schema."
            )
        result = cls(
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            execution_context_digest=str(payload["execution_context_digest"]),
            target_size=int(payload["target_size"]),
            training_order_digest=str(payload["training_order_digest"]),
            candidate_membership_digest=str(payload["candidate_membership_digest"]),
            candidate_membership=tuple(
                str(v) for v in payload["candidate_membership"]
            ),
            optimizer_seed=int(payload["optimizer_seed"]),
            seed_neutral_training_policy_digest=str(
                payload["seed_neutral_training_policy_digest"]
            ),
            common_preparation_digest=str(payload["common_preparation_digest"]),
            replay_foundation_identity_digest=str(
                payload["replay_foundation_identity_digest"]
            ),
            realization=TargetSizeCandidateRealization.from_dict(
                payload["realization"]
            ),
            evaluation_model_state=str(
                payload.get("evaluation_model_state", "live")
            ),
            candidate_training_protocol_digest=str(
                payload["candidate_training_protocol_digest"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Candidate-trajectory digest mismatch."
            )
        return result


def build_target_size_candidate_trajectory(
    definition: TargetSizeExperimentDefinition,
    context: TargetSizeExecutionContext,
    common: TargetSizeCommonPreparation,
    schedule: TargetSizeScreenSchedule,
    *,
    target_size: int,
    optimizer_policy: MaceOptimizerPolicy,
    optimizer_seed: int,
    replay_train_count: int = 0,
) -> TargetSizeCandidateTrajectory:
    """Instantiate one authenticated candidate trajectory.

    Only qualified ``N`` values may be instantiated, membership is exactly
    ``definition.candidate_membership(N)``, and the seed must be an exact P2
    policy member.  The candidate optimizer policy must equal the seed-neutral
    template except for the authorized seed.
    """

    context.validate_bindings(definition, common, schedule)
    qualified = definition.qualified_candidate_sizes
    if target_size not in qualified:
        raise TrainingDataInputError(
            "Candidate trajectories accept only qualified candidate sizes."
        )
    if optimizer_seed not in definition.policy.optimizer_seeds:
        raise TrainingDataInputError(
            "Candidate trajectories require an exact P2 policy optimizer seed."
        )
    from .context import validate_candidate_optimizer_policy

    validate_candidate_optimizer_policy(
        context.seed_neutral_optimizer_policy_digest,
        optimizer_policy,
        authorized_seed=optimizer_seed,
    )
    if optimizer_policy.max_num_epochs != schedule.n3:
        raise TrainingDataInputError(
            "Candidate training must run the full-n3 screen budget."
        )
    projection = project_target_size_candidate_preparation(
        common, definition, target_size
    )
    realization = derive_target_size_candidate_realization(
        schedule=schedule,
        projection=projection,
        common=common,
        optimizer_policy=optimizer_policy,
        optimizer_seed=optimizer_seed,
        replay_train_count=replay_train_count,
    )
    candidate_protocol_digest = digest(
        {
            "schema": "mdstats.target-size.candidate-protocol.v1",
            "seed_neutral_training_policy_digest": (
                context.seed_neutral_optimizer_policy_digest
            ),
            "optimizer_seed": optimizer_seed,
            "candidate_membership_digest": projection.candidate_membership_digest,
            "common_preparation_digest": common.content_digest,
            "execution_context_digest": context.content_digest,
            "realization_digest": realization.content_digest,
        }
    )
    return TargetSizeCandidateTrajectory(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=context.content_digest,
        target_size=target_size,
        training_order_digest=definition.training_order.content_digest,
        candidate_membership_digest=projection.candidate_membership_digest,
        candidate_membership=projection.candidate_membership,
        optimizer_seed=optimizer_seed,
        seed_neutral_training_policy_digest=(
            context.seed_neutral_optimizer_policy_digest
        ),
        common_preparation_digest=common.content_digest,
        replay_foundation_identity_digest=digest(
            {
                "schema": "mdstats.target-size.replay-foundation.v1",
                "mode": "none",
                "foundation_checkpoint_digest": None,
                "selected_head_name": None,
            }
        ),
        realization=realization,
        evaluation_model_state=("ema" if optimizer_policy.ema else "live"),
        candidate_training_protocol_digest=candidate_protocol_digest,
    )


def validate_target_size_candidate_trajectory(
    trajectory: TargetSizeCandidateTrajectory,
    definition: TargetSizeExperimentDefinition,
    context: TargetSizeExecutionContext,
    common: TargetSizeCommonPreparation,
    schedule: TargetSizeScreenSchedule,
    *,
    optimizer_policy: MaceOptimizerPolicy,
    replay_train_count: int = 0,
) -> TargetSizeCandidatePreparation:
    """Restart authentication: re-derive the exact candidate and reject stale
    loader/update/precision realizations."""

    context.validate_bindings(definition, common, schedule)
    if trajectory.experiment_definition_digest != definition.content_digest:
        raise TrainingDataInputError(
            "Trajectory binds a different experiment definition."
        )
    if trajectory.execution_context_digest != context.content_digest:
        raise TrainingDataInputError(
            "Trajectory binds a different execution context."
        )
    if trajectory.common_preparation_digest != common.content_digest:
        raise TrainingDataInputError(
            "Trajectory binds a different common preparation."
        )
    if trajectory.optimizer_seed not in definition.policy.optimizer_seeds:
        raise TrainingDataInputError(
            "Trajectory optimizer seed is not in experiment definition seeds."
        )
    if (
        trajectory.seed_neutral_training_policy_digest
        != context.seed_neutral_optimizer_policy_digest
    ):
        raise TrainingDataInputError(
            "Trajectory seed-neutral training policy digest does not match execution context."
        )
    expected_eval_state = "ema" if optimizer_policy.ema else "live"
    if trajectory.evaluation_model_state != expected_eval_state:
        raise TrainingDataInputError(
            f"Trajectory evaluation_model_state '{trajectory.evaluation_model_state}' "
            f"does not match optimizer policy EMA convention '{expected_eval_state}'."
        )
    projection = project_target_size_candidate_preparation(
        common, definition, trajectory.target_size
    )
    if (
        trajectory.candidate_membership_digest
        != projection.candidate_membership_digest
        or trajectory.candidate_membership != projection.candidate_membership
    ):
        raise TrainingDataInputError(
            "Trajectory candidate membership is not the exact P2 T_N."
        )
    from .context import validate_candidate_optimizer_policy

    if optimizer_policy is not None:
        validate_candidate_optimizer_policy(
            context.seed_neutral_optimizer_policy_digest,
            optimizer_policy,
            authorized_seed=trajectory.optimizer_seed,
        )

    expected_realization = derive_target_size_candidate_realization(
        schedule=schedule,
        projection=projection,
        common=common,
        optimizer_policy=optimizer_policy,
        optimizer_seed=trajectory.optimizer_seed,
        replay_train_count=replay_train_count,
    )
    if trajectory.realization.content_digest != expected_realization.content_digest:
        raise TrainingDataInputError(
            "Trajectory realization is stale for the current exact T_N; "
            "loader/update geometry or precision realization differs."
        )

    expected_foundation_digest = digest(
        {
            "schema": "mdstats.target-size.replay-foundation.v1",
            "mode": "none",
            "foundation_checkpoint_digest": None,
            "selected_head_name": None,
        }
    )
    if (
        trajectory.replay_foundation_identity_digest
        != expected_foundation_digest
    ):
        raise TrainingDataInputError(
            "Trajectory replay foundation identity digest must be mode 'none'."
        )
    if getattr(trajectory, "replay_foundation", None) is not None:
        raise TrainingDataInputError(
            "Trajectory replay foundation must be None for P3 screening."
        )

    recomputed_protocol_digest = digest(
        {
            "schema": "mdstats.target-size.candidate-protocol.v1",
            "seed_neutral_training_policy_digest": (
                context.seed_neutral_optimizer_policy_digest
            ),
            "optimizer_seed": trajectory.optimizer_seed,
            "candidate_membership_digest": (
                projection.candidate_membership_digest
            ),
            "common_preparation_digest": common.content_digest,
            "execution_context_digest": context.content_digest,
            "realization_digest": expected_realization.content_digest,
        }
    )
    if (
        trajectory.candidate_training_protocol_digest
        != recomputed_protocol_digest
    ):
        raise TrainingDataInputError(
            "Trajectory candidate training protocol digest mismatch."
        )

    return projection


@dataclass(frozen=True, slots=True)
class TargetSizeCandidateMaterialization:
    """Durable record of one candidate's materialized execution artifacts."""

    trajectory_digest: str
    target_train_artifact: TargetSizeExtxyzArtifact
    harness_validation_artifact: TargetSizeExtxyzArtifact
    mace_config_relative_path: str
    mace_config_sha256: str
    mace_config_digest: str
    output_directory: str = ""
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "trajectory_digest",
            "mace_config_sha256",
            "mace_config_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.target_train_artifact.role != "target_train":
            raise TrainingDataInputError(
                "Candidate materialization requires the target-train artifact."
            )
        if self.harness_validation_artifact.role != "harness_validation":
            raise TrainingDataInputError(
                "Candidate materialization requires the fixed harness-validation artifact."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_MATERIALIZATION_SCHEMA,
            "trajectory_digest": self.trajectory_digest,
            "target_train_artifact": self.target_train_artifact.to_dict(),
            "harness_validation_artifact": (
                self.harness_validation_artifact.to_dict()
            ),
            "mace_config_relative_path": self.mace_config_relative_path,
            "mace_config_sha256": self.mace_config_sha256,
            "mace_config_digest": self.mace_config_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", cached)
        return {
            **payload,
            "output_directory": self.output_directory,
            "content_digest": cached,
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> TargetSizeCandidateMaterialization:
        if payload.get("schema") != TARGET_SIZE_MATERIALIZATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported candidate-materialization schema."
            )
        result = cls(
            trajectory_digest=str(payload["trajectory_digest"]),
            target_train_artifact=TargetSizeExtxyzArtifact.from_dict(
                payload["target_train_artifact"]
            ),
            harness_validation_artifact=TargetSizeExtxyzArtifact.from_dict(
                payload["harness_validation_artifact"]
            ),
            mace_config_relative_path=str(payload["mace_config_relative_path"]),
            mace_config_sha256=str(payload["mace_config_sha256"]),
            mace_config_digest=str(payload["mace_config_digest"]),
            output_directory=str(payload.get("output_directory", "")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Candidate-materialization digest mismatch."
            )
        return result


def _mace_config_for_candidate(
    *,
    trajectory: TargetSizeCandidateTrajectory,
    projection: TargetSizeCandidatePreparation,
    common: TargetSizeCommonPreparation,
    optimizer_policy: MaceOptimizerPolicy,
    target_train: TargetSizeExtxyzArtifact,
    harness_validation: TargetSizeExtxyzArtifact,
    extxyz_policy: MaceExtxyzPolicy,
    mace_architecture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from ..model_features import canonicalize_mace_candidate_architecture

    fitted_e0s = {
        int(z): float(value)
        for z, value in common.fitted_atomic_references.reference_energies_ev
    }
    target_atomic_numbers = set(int(z) for z in target_train.atomic_numbers)
    harness_atomic_numbers = set(int(z) for z in harness_validation.atomic_numbers)
    missing_e0 = sorted(
        (target_atomic_numbers | harness_atomic_numbers) - set(fitted_e0s)
    )
    if missing_e0:
        raise TrainingDataInputError(
            f"Common E0 mapping is missing atomic numbers: {missing_e0}."
        )
    config: dict[str, Any] = {
        "schema": TARGET_SIZE_MACE_CONFIG_SCHEMA,
        "name": f"target-size-n{trajectory.target_size}-seed{trajectory.optimizer_seed}",
        "seed": int(trajectory.optimizer_seed),
        "target_train_file": target_train.relative_path,
        "target_valid_file": harness_validation.relative_path,
        "atomic_numbers": sorted(target_atomic_numbers),
        "E0s": {str(z): fitted_e0s[z] for z in sorted(target_atomic_numbers)},
        "energy_key": extxyz_policy.energy_key,
        "forces_key": extxyz_policy.forces_key,
        "stress_key": extxyz_policy.stress_key,
        "lr": float(optimizer_policy.learning_rate),
        "batch_size": int(optimizer_policy.batch_size),
        "valid_batch_size": int(optimizer_policy.valid_batch_size),
        "num_workers": int(optimizer_policy.num_workers),
        "max_num_epochs": int(trajectory.realization.max_num_epochs),
        "ema": bool(optimizer_policy.ema),
        "ema_decay": float(optimizer_policy.ema_decay),
        "amsgrad": bool(optimizer_policy.amsgrad),
        "weight_decay": float(optimizer_policy.weight_decay),
        "clip_grad": float(optimizer_policy.clip_grad),
        "default_dtype": str(trajectory.realization.default_dtype),
        "device": str(optimizer_policy.device),
        "foundation_model": None,
        "foundation_head": None,
        "multiheads_finetuning": False,
        "mace_architecture": canonicalize_mace_candidate_architecture(
            mace_architecture
        ),
        "multi_head": {
            "target_head": {
                "train_file": target_train.relative_path,
                "valid_file": harness_validation.relative_path,
                "atomic_numbers": sorted(target_atomic_numbers),
                "E0s": {str(z): fitted_e0s[z] for z in sorted(target_atomic_numbers)},
                "energy_key": extxyz_policy.energy_key,
                "forces_key": extxyz_policy.forces_key,
                "stress_key": extxyz_policy.stress_key,
            }
        },
    }
    return config


def materialize_target_size_candidate(
    trajectory: TargetSizeCandidateTrajectory,
    projection: TargetSizeCandidatePreparation,
    common: TargetSizeCommonPreparation,
    *,
    canonical_frame_authority: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    output_directory: str | Path,
    optimizer_policy: MaceOptimizerPolicy,
    extxyz_policy: MaceExtxyzPolicy,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    mace_architecture: Mapping[str, Any] | None = None,
) -> TargetSizeCandidateMaterialization:
    """Materialize one candidate exactly and idempotently.

    Writes the target-train artifact for the exact ``T_N`` membership with the
    projected frozen weights, the fixed non-controlling harness-validation
    artifact from authorized training-side data, and the MACE training
    configuration carrying the authorized seed.  Existing identical
    artifacts are reused; conflicting records fail closed.
    """

    import hashlib

    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    if not isinstance(extxyz_policy, MaceExtxyzPolicy):
        raise TrainingDataInputError(
            "Candidate materialization requires the accepted MaceExtxyzPolicy."
        )
    active_policy = extxyz_policy
    if trajectory.target_size != projection.target_size or (
        trajectory.candidate_membership_digest
        != projection.candidate_membership_digest
    ):
        raise TrainingDataInputError(
            "Materialization requires the projection of this exact trajectory."
        )
    record_path = root / "materialization.json"
    target_train = write_target_size_extxyz_artifact(
        root,
        dataset_id=str(canonical_frame_authority.dataset_id),
        role="target_train",
        filename=f"target_train_n{trajectory.target_size}_seed{trajectory.optimizer_seed}.extxyz",
        frame_uids=projection.candidate_membership,
        canonical_frame_authority=canonical_frame_authority,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        membership_digest=projection.candidate_membership_digest,
        common_preparation_digest=common.content_digest,
        training_weights=projection.frame_weight_table(),
        policy=active_policy,
        frame_array_index=frame_array_index,
    )
    # The fixed harness validation is derived from the common training-side
    # membership only: identical across N and seeds under one context.
    harness_validation = write_target_size_extxyz_artifact(
        root,
        dataset_id=str(canonical_frame_authority.dataset_id),
        role="harness_validation",
        filename=f"harness_validation_fixed.extxyz",
        frame_uids=common.harness_validation_membership,
        canonical_frame_authority=canonical_frame_authority,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        membership_digest=common.harness_validation_membership_digest,
        common_preparation_digest=common.content_digest,
        training_weights=None,
        policy=active_policy,
        frame_array_index=frame_array_index,
    )
    config = _mace_config_for_candidate(
        trajectory=trajectory,
        projection=projection,
        common=common,
        optimizer_policy=optimizer_policy,
        target_train=target_train,
        harness_validation=harness_validation,
        extxyz_policy=active_policy,
        mace_architecture=mace_architecture,
    )
    config_path = root / f"mace_config_n{trajectory.target_size}_seed{trajectory.optimizer_seed}.yaml"
    config_bytes = json.dumps(config, indent=2, sort_keys=True).encode("utf-8")
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    publish_immutable_bytes_create_or_verify(
        config_path, config_bytes, expected_sha256=config_sha256
    )
    record = TargetSizeCandidateMaterialization(
        trajectory_digest=trajectory.content_digest,
        target_train_artifact=target_train,
        harness_validation_artifact=harness_validation,
        mace_config_relative_path=config_path.name,
        mace_config_sha256=config_sha256,
        mace_config_digest=digest(config),
        output_directory=str(root),
    )
    publish_immutable_json_create_or_verify(
        record_path,
        record.to_dict(),
        deserializer=TargetSizeCandidateMaterialization.from_dict,
    )
    return record


def validate_target_size_materialization(
    record: TargetSizeCandidateMaterialization,
    trajectory: TargetSizeCandidateTrajectory,
    *,
    canonical_frame_authority: Any,
    materialization_directory: str | Path | None = None,
    projection: TargetSizeCandidatePreparation | None = None,
    definition: TargetSizeExperimentDefinition | None = None,
    common: TargetSizeCommonPreparation | None = None,
    optimizer_policy: MaceOptimizerPolicy | None = None,
    extxyz_policy: MaceExtxyzPolicy | None = None,
    frame_catalog: Any | None = None,
    frame_data_by_run: Mapping[str, Any] | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
) -> None:
    """Restart authentication of a durable candidate materialization."""

    if record.trajectory_digest != trajectory.content_digest:
        raise TrainingDataInputError(
            "Materialization record binds a different trajectory."
        )
    if record.target_train_artifact.role != "target_train":
        raise TrainingDataInputError(
            "Materialization target-train artifact role mismatch."
        )
    if record.harness_validation_artifact.role != "harness_validation":
        raise TrainingDataInputError(
            "Materialization harness-validation artifact role mismatch."
        )
    if record.target_train_artifact.frame_uids != trajectory.candidate_membership:
        raise TrainingDataInputError(
            "Materialization target-train artifact frame UIDs do not match trajectory candidate membership."
        )
    if (
        record.target_train_artifact.membership_digest
        != trajectory.candidate_membership_digest
    ):
        raise TrainingDataInputError(
            "Materialization target-train artifact membership digest mismatch."
        )
    if common is not None:
        if (
            record.target_train_artifact.common_preparation_digest
            != common.content_digest
        ):
            raise TrainingDataInputError(
                "Materialization target-train common preparation digest mismatch."
            )
        if (
            record.harness_validation_artifact.frame_uids
            != common.harness_validation_membership
        ):
            raise TrainingDataInputError(
                "Materialization harness validation membership mismatch."
            )
        if (
            record.harness_validation_artifact.membership_digest
            != common.harness_validation_membership_digest
        ):
            raise TrainingDataInputError(
                "Materialization harness validation membership digest mismatch."
            )
    root = Path(
        materialization_directory
        if materialization_directory is not None
        else (record.output_directory or ".")
    )
    if not isinstance(extxyz_policy, MaceExtxyzPolicy):
        raise TrainingDataInputError(
            "Materialization validation requires the accepted MaceExtxyzPolicy."
        )
    active_extxyz_policy = extxyz_policy
    validate_target_size_extxyz_artifact(
        record.target_train_artifact,
        root_directory=root,
        canonical_frame_authority=canonical_frame_authority,
        policy=active_extxyz_policy,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )
    validate_target_size_extxyz_artifact(
        record.harness_validation_artifact,
        root_directory=root,
        canonical_frame_authority=canonical_frame_authority,
        policy=active_extxyz_policy,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )
    relative_config = Path(record.mace_config_relative_path)
    if relative_config.is_absolute() or ".." in relative_config.parts:
        raise TrainingDataInputError(
            "Candidate MACE configuration path must remain inside the materialization root."
        )
    config_path = (root / relative_config).resolve()
    try:
        config_path.relative_to(root.resolve())
    except ValueError as exc:
        raise TrainingDataInputError(
            "Candidate MACE configuration path resolves outside the materialization root."
        ) from exc
    if not config_path.is_file():
        raise TrainingDataInputError("Candidate MACE configuration is missing.")
    import hashlib

    config_bytes = config_path.read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != record.mace_config_sha256:
        raise TrainingDataInputError("Candidate MACE configuration bytes changed.")
    try:
        payload = json.loads(config_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TrainingDataSerializationError(
            "Candidate MACE configuration cannot be parsed."
        ) from exc
    if digest(payload) != record.mace_config_digest:
        raise TrainingDataInputError("Candidate MACE configuration content changed.")
    if payload.get("schema") != TARGET_SIZE_MACE_CONFIG_SCHEMA:
        raise TrainingDataSerializationError(
            "Unsupported candidate MACE configuration schema."
        )
    if int(payload["seed"]) != trajectory.optimizer_seed:
        raise TrainingDataInputError(
            "Candidate MACE configuration does not carry the authorized seed."
        )
    from ..model_features import canonicalize_mace_candidate_architecture

    canonicalize_mace_candidate_architecture(payload.get("mace_architecture"))
    if payload["target_train_file"] != record.target_train_artifact.relative_path:
        raise TrainingDataInputError(
            "Candidate MACE configuration does not point at the exact target-train artifact."
        )
    if common is not None and optimizer_policy is not None:
        active_projection = projection
        if active_projection is None and definition is not None:
            active_projection = project_target_size_candidate_preparation(
                common, definition, trajectory.target_size
            )
        if active_projection is not None:
            expected_config = _mace_config_for_candidate(
                trajectory=trajectory,
                projection=active_projection,
                common=common,
                optimizer_policy=optimizer_policy,
                target_train=record.target_train_artifact,
                harness_validation=record.harness_validation_artifact,
                extxyz_policy=active_extxyz_policy,
                mace_architecture=payload["mace_architecture"],
            )
            if record.mace_config_digest != digest(expected_config):
                raise TrainingDataInputError(
                    "Candidate MACE configuration does not match re-derived configuration."
                )


__all__ = [
    "TARGET_SIZE_MACE_CONFIG_SCHEMA",
    "TARGET_SIZE_MATERIALIZATION_SCHEMA",
    "TARGET_SIZE_REALIZATION_SCHEMA",
    "TARGET_SIZE_TRAJECTORY_SCHEMA",
    "TargetSizeCandidateMaterialization",
    "TargetSizeCandidateRealization",
    "TargetSizeCandidateTrajectory",
    "build_target_size_candidate_trajectory",
    "derive_target_size_candidate_realization",
    "materialize_target_size_candidate",
    "validate_target_size_candidate_trajectory",
    "validate_target_size_materialization",
]
