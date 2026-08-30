"""Materialization, TRAIN2 execution, and EVAL2 evidence below the P5 plans.

Everything in this module is a *descendant*: it binds the CV or final-production
run plan it was produced under, and it can never rewrite that plan, the policy
identities above it, or the selected binding at the root.  That direction is the
whole invalidation contract - corrupt or changed fitted evidence invalidates
itself, not its parents.

Two scientific rules shape the code rather than merely being asserted by it.
Fold-local preparation is fitted from the fold's authorized *training* frames
only, so the held-out outer fold cannot leak into E0, weights, or checkpoint
choice.  And nothing here forks a second training engine: preparation reuses the
shared DATA7 fitting seam, export reuses the shared DATA8 ExtXYZ owner, training
reuses the TRAIN2 runtime plan, and evaluation reuses the EVAL2 reduction and
its target-only admissibility/ordering owners.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
)
from .post_selection_identity import (
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    PostSelectionMethodIdentity,
    canonical_post_selection_head_names,
)

POST_SELECTION_PREPARATION_SCHEMA = "mdstats.post-selection-fitted-preparation.v1"
POST_SELECTION_MATERIALIZATION_SCHEMA = "mdstats.post-selection-materialization.v1"
POST_SELECTION_MACE_CONFIG_SCHEMA = "mdstats.post-selection-mace-config.v1"
POST_SELECTION_EVAL_ROLE_SCHEMA = "mdstats.post-selection-eval2-role.v1"
POST_SELECTION_RUN_EVIDENCE_SCHEMA = "mdstats.post-selection-run-evidence.v1"

#: Dataset roles a post-selection run materializes.  ``target_train`` receives
#: gradients; ``checkpoint_monitor`` may control checkpoint choice;
#: ``outer_evaluation`` is held out until the representative is frozen.
DATASET_ROLE_TARGET_TRAIN = "target_train"
DATASET_ROLE_CHECKPOINT_MONITOR = "checkpoint_monitor"
DATASET_ROLE_OUTER_EVALUATION = "outer_evaluation"


class PostSelectionExecutionError(PostSelectionError):
    """A post-selection execution owner refused to produce or accept evidence."""


# ---------------------------------------------------------------------------
# Fitted preparation (fold-local or final)
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionFittedPreparation:
    """Atomic references and training weights fitted over one exact membership.

    The membership is an authorization boundary, not a convenience: a CV fold
    fits only from its gradient-training frames, and final production fits from
    the full ``T_selected``.  The record binds the run plan that authorized the
    fit so a fitted product can always be traced to the exact evidence it was
    allowed to see.
    """

    owner_plan_digest: str
    dataset_role: str
    common_training_policy_digest: str
    membership: tuple[str, ...]
    membership_digest: str
    fitted_atomic_reference_digest: str
    fitted_weights_digest: str
    fitted_atomic_references: Any
    fitted_frame_weights: tuple[Any, ...]

    def __post_init__(self) -> None:
        for name in (
            "owner_plan_digest",
            "common_training_policy_digest",
            "membership_digest",
            "fitted_atomic_reference_digest",
            "fitted_weights_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        membership = tuple(str(v) for v in self.membership)
        if not membership or len(set(membership)) != len(membership):
            raise TrainingDataInputError(
                "A fitted preparation requires a unique non-empty membership."
            )
        if digest({"frame_uids": list(membership)}) != self.membership_digest:
            raise TrainingDataInputError(
                "Fitted preparation membership does not match its digest."
            )
        weights = tuple(self.fitted_frame_weights)
        if tuple(item.frame_uid for item in weights) != tuple(sorted(membership)):
            raise TrainingDataInputError(
                "Fitted weights must cover exactly the fitted membership."
            )
        if (
            digest({"frame_weights": [item.to_dict() for item in weights]})
            != self.fitted_weights_digest
        ):
            raise TrainingDataInputError(
                "Fitted weights do not match their digest."
            )
        object.__setattr__(self, "membership", membership)
        object.__setattr__(self, "fitted_frame_weights", weights)
        object.__setattr__(self, "dataset_role", str(self.dataset_role))

    def frame_weight_table(self) -> Any:
        from .objectives import FrameTrainingWeightTable

        return FrameTrainingWeightTable.from_records(self.fitted_frame_weights)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_PREPARATION_SCHEMA,
            "owner_plan_digest": self.owner_plan_digest,
            "dataset_role": self.dataset_role,
            "common_training_policy_digest": self.common_training_policy_digest,
            "membership": list(self.membership),
            "membership_digest": self.membership_digest,
            "fitted_atomic_reference_digest": self.fitted_atomic_reference_digest,
            "fitted_weights_digest": self.fitted_weights_digest,
            "fitted_atomic_references": self.fitted_atomic_references.to_dict(),
            "fitted_frame_weights": [
                item.to_dict() for item in self.fitted_frame_weights
            ],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionFittedPreparation":
        from .objectives import FrameTrainingWeight
        from .target_size_execution import CommonAtomicReferenceFit

        if payload.get("schema") != POST_SELECTION_PREPARATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection fitted-preparation schema."
            )
        result = cls(
            owner_plan_digest=str(payload["owner_plan_digest"]),
            dataset_role=str(payload["dataset_role"]),
            common_training_policy_digest=str(
                payload["common_training_policy_digest"]
            ),
            membership=tuple(str(v) for v in payload["membership"]),
            membership_digest=str(payload["membership_digest"]),
            fitted_atomic_reference_digest=str(
                payload["fitted_atomic_reference_digest"]
            ),
            fitted_weights_digest=str(payload["fitted_weights_digest"]),
            fitted_atomic_references=CommonAtomicReferenceFit.from_dict(
                payload["fitted_atomic_references"]
            ),
            fitted_frame_weights=tuple(
                FrameTrainingWeight.from_dict(item)
                for item in payload["fitted_frame_weights"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection fitted-preparation digest mismatch."
            )
        return result


def fit_post_selection_preparation(
    context: CurrentSelectedTrainingContext,
    *,
    membership: Sequence[str],
    owner_plan_digest: str,
    common_training_policy: Any = None,
    dataset_role: str = DATASET_ROLE_TARGET_TRAIN,
) -> PostSelectionFittedPreparation:
    """Fit E0 and training weights from one authorized training membership.

    The membership is checked against ``T_selected`` before anything is fitted,
    so a caller cannot widen the fit domain past the selected data even by
    mistake.
    """

    from .target_size_execution import (
        TargetSizeCommonTrainingPolicy,
        fit_common_atomic_reference_energies,
        fit_common_configuration_weights,
        fit_membership_frame_training_weights,
    )

    policy = (
        TargetSizeCommonTrainingPolicy()
        if common_training_policy is None
        else common_training_policy
    )
    frames = tuple(str(v) for v in membership)
    outside = set(frames) - set(context.selected_membership)
    if outside:
        raise PostSelectionExecutionError(
            f"{len(outside)} frame(s) in this preparation membership are outside "
            "T_selected; post-selection preparation is fitted only from selected "
            "training data."
        )
    authorities = context.authorities
    # The foundation checkpoint is part of the non-scratch method identity, but
    # it is not an input to the default from-scratch E0 fit.  Passing that
    # lineage through unconditionally makes a valid naive/multihead
    # post-selection preparation look like a foundation-residual fit and the
    # shared DATA7 owner correctly rejects it.  Only the explicitly selected
    # residual-fit authority may receive foundation fit inputs.
    from .reference_fit import AtomicReferenceFitMode

    foundation_fit_digest = (
        policy.foundation_checkpoint_digest
        if policy.atomic_reference_policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
        else None
    )
    atomic_references = fit_common_atomic_reference_energies(
        authorities.frame_catalog,
        authorities.frame_data_by_run,
        frames,
        policy=policy.atomic_reference_policy,
        frame_array_index=authorities.frame_array_index,
        foundation_checkpoint_digest=foundation_fit_digest,
        foundation_identity_digest=foundation_fit_digest,
    )
    configuration_weights = fit_common_configuration_weights(
        authorities.aggregate.population,
        frames,
        policy=policy.configuration_weight_policy,
    )
    fitted_weights = fit_membership_frame_training_weights(
        authorities.frame_array_index,
        frames,
        objective_policy=policy.objective_policy,
        configuration_weights={
            item.frame_uid: item for item in configuration_weights
        },
    )
    return PostSelectionFittedPreparation(
        owner_plan_digest=str(owner_plan_digest),
        dataset_role=dataset_role,
        common_training_policy_digest=policy.content_digest,
        membership=frames,
        membership_digest=digest({"frame_uids": list(frames)}),
        fitted_atomic_reference_digest=atomic_references.content_digest,
        fitted_weights_digest=digest(
            {"frame_weights": [item.to_dict() for item in fitted_weights]}
        ),
        fitted_atomic_references=atomic_references,
        fitted_frame_weights=fitted_weights,
    )


# ---------------------------------------------------------------------------
# DATA8 materialization
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionMaterialization:
    """The exact DATA8 workload one post-selection run executes."""

    run_plan_digest: str
    run_identity: str
    preparation_digest: str
    target_train_artifact: Any
    checkpoint_monitor_artifact: Any
    outer_evaluation_artifact: Any
    mace_config_relative_path: str
    mace_config_sha256: str
    mace_config_digest: str
    output_directory: str

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "run_identity",
            "preparation_digest",
            "mace_config_sha256",
            "mace_config_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        for name in ("mace_config_relative_path", "output_directory"):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"{name} cannot be empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_MATERIALIZATION_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "run_identity": self.run_identity,
            "preparation_digest": self.preparation_digest,
            "target_train_artifact": self.target_train_artifact.to_dict(),
            "checkpoint_monitor_artifact": self.checkpoint_monitor_artifact.to_dict(),
            "outer_evaluation_artifact": (
                None
                if self.outer_evaluation_artifact is None
                else self.outer_evaluation_artifact.to_dict()
            ),
            "mace_config_relative_path": self.mace_config_relative_path,
            "mace_config_sha256": self.mace_config_sha256,
            "mace_config_digest": self.mace_config_digest,
            "output_directory": self.output_directory,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionMaterialization":
        from .target_size_execution import TargetSizeExtxyzArtifact

        if payload.get("schema") != POST_SELECTION_MATERIALIZATION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection materialization schema."
            )
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            run_identity=str(payload["run_identity"]),
            preparation_digest=str(payload["preparation_digest"]),
            target_train_artifact=TargetSizeExtxyzArtifact.from_dict(
                payload["target_train_artifact"]
            ),
            checkpoint_monitor_artifact=TargetSizeExtxyzArtifact.from_dict(
                payload["checkpoint_monitor_artifact"]
            ),
            outer_evaluation_artifact=(
                None
                if payload.get("outer_evaluation_artifact") is None
                else TargetSizeExtxyzArtifact.from_dict(
                    payload["outer_evaluation_artifact"]
                )
            ),
            mace_config_relative_path=str(payload["mace_config_relative_path"]),
            mace_config_sha256=str(payload["mace_config_sha256"]),
            mace_config_digest=str(payload["mace_config_digest"]),
            output_directory=str(payload["output_directory"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection materialization digest mismatch."
            )
        return result


def _write_role_artifact(
    context: CurrentSelectedTrainingContext,
    *,
    output_directory: Path,
    role: str,
    frame_uids: Sequence[str],
    extxyz_policy: Any,
    preparation: PostSelectionFittedPreparation | None,
) -> Any:
    from .target_size_execution import write_target_size_extxyz_artifact

    authorities = context.authorities
    frames = tuple(str(v) for v in frame_uids)
    return write_target_size_extxyz_artifact(
        output_directory,
        dataset_id=str(authorities.frame_authority.dataset_id),
        role=role,
        filename=f"{role}.extxyz",
        frame_uids=frames,
        canonical_frame_authority=authorities.frame_authority,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        membership_digest=digest({"frame_uids": list(frames)}),
        common_preparation_digest=(
            None if preparation is None else preparation.content_digest
        ),
        training_weights=(
            None if preparation is None else preparation.frame_weight_table()
        ),
        policy=extxyz_policy,
        frame_array_index=authorities.frame_array_index,
    )


def _post_selection_mace_config(
    *,
    run_identity: str,
    optimizer_seed: int,
    planned_epochs: int,
    preparation: PostSelectionFittedPreparation,
    optimizer_policy: Any,
    target_train: Any,
    monitor: Any,
    extxyz_policy: Any,
    method: PostSelectionMethodIdentity,
    mace_architecture: Mapping[str, Any] | None = None,
    foundation_model: str | None = None,
    foundation_head: str | None = None,
    multiheads_finetuning: bool = False,
    replay_train: Any = None,
    replay_monitor: Any = None,
) -> dict[str, Any]:
    """Translate the frozen post-selection run description into MACE arguments.

    Nothing is decided here.  Every value already belongs to the run plan, the
    fitted preparation, or the accepted optimizer policy; this is a rename.
    """

    from .model_features import canonicalize_mace_candidate_architecture

    fitted_e0s = {
        int(z): float(value)
        for z, value in preparation.fitted_atomic_references.reference_energies_ev
    }
    atomic_numbers = set(int(z) for z in target_train.atomic_numbers) | set(
        int(z) for z in monitor.atomic_numbers
    )
    missing = sorted(atomic_numbers - set(fitted_e0s))
    if missing:
        raise PostSelectionExecutionError(
            f"The fold-local E0 fit is missing atomic numbers {missing}; the "
            "authorized training membership does not cover this workload."
        )
    arch = canonicalize_mace_candidate_architecture(mace_architecture)
    config: dict[str, Any] = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": f"post-selection-{run_identity[:16]}",
        "seed": int(optimizer_seed),
        "target_train_file": target_train.relative_path,
        "target_valid_file": monitor.relative_path,
        "atomic_numbers": sorted(atomic_numbers),
        "E0s": {str(z): fitted_e0s[z] for z in sorted(atomic_numbers)},
        "energy_key": extxyz_policy.energy_key,
        "forces_key": extxyz_policy.forces_key,
        "stress_key": extxyz_policy.stress_key,
        "lr": float(optimizer_policy.learning_rate),
        "batch_size": int(optimizer_policy.batch_size),
        "valid_batch_size": int(optimizer_policy.valid_batch_size),
        "num_workers": int(optimizer_policy.num_workers),
        "max_num_epochs": int(planned_epochs),
        "ema": bool(optimizer_policy.ema),
        "ema_decay": float(optimizer_policy.ema_decay),
        "amsgrad": bool(optimizer_policy.amsgrad),
        "weight_decay": float(optimizer_policy.weight_decay),
        "clip_grad": float(optimizer_policy.clip_grad),
        "default_dtype": str(method.default_dtype),
        "device": str(optimizer_policy.device),
        "method_identity_digest": method.content_digest,
        "mace_architecture": arch,
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
    }
    if hasattr(optimizer_policy, "eval_interval"):
        config["eval_interval"] = int(optimizer_policy.eval_interval)
    if hasattr(optimizer_policy, "acceleration_policy") and optimizer_policy.acceleration_policy is not None:
        config.update(optimizer_policy.acceleration_policy.training_config())
    if foundation_model:
        config["foundation_model"] = str(foundation_model)
    if foundation_head:
        config["foundation_head"] = str(foundation_head)
    if multiheads_finetuning:
        config["multiheads_finetuning"] = True
        if replay_train is not None:
            config["pt_train_file"] = (
                replay_train.relative_path
                if hasattr(replay_train, "relative_path")
                else str(replay_train)
            )
        if replay_monitor is not None:
            config["pt_valid_file"] = (
                replay_monitor.relative_path
                if hasattr(replay_monitor, "relative_path")
                else str(replay_monitor)
            )
        config["heads"] = {
            POST_SELECTION_TARGET_HEAD_NAME: {
                "train_file": target_train.relative_path,
                "valid_file": monitor.relative_path,
                "atomic_numbers": sorted(atomic_numbers),
                "E0s": {str(z): fitted_e0s[z] for z in sorted(atomic_numbers)},
                "energy_key": extxyz_policy.energy_key,
                "forces_key": extxyz_policy.forces_key,
                "stress_key": extxyz_policy.stress_key,
            },
            POST_SELECTION_REPLAY_HEAD_NAME: {
                "energy_key": extxyz_policy.energy_key,
                "forces_key": extxyz_policy.forces_key,
                "stress_key": extxyz_policy.stress_key,
            },
        }
    return config


def materialize_post_selection_run(
    context: CurrentSelectedTrainingContext,
    *,
    run_plan: Any,
    method: PostSelectionMethodIdentity,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None = None,
    optimizer_policy: Any,
    extxyz_policy: Any = None,
    output_directory: str | os.PathLike[str],
    preparation: PostSelectionFittedPreparation | None = None,
    common_training_policy: Any = None,
    mace_architecture: Mapping[str, Any] | None = None,
    foundation_model: str | None = None,
    foundation_head: str | None = None,
    multiheads_finetuning: bool = False,
    replay_train: Any = None,
    replay_monitor: Any = None,
) -> tuple[PostSelectionFittedPreparation, PostSelectionMaterialization]:
    """Fit, export, and configure one post-selection run, idempotently.

    Role separation is enforced before any bytes are written: the three
    memberships must be pairwise disjoint and entirely inside ``T_selected``
    (the final-production monitor is the frozen M3 reserve, which is outside
    ``T_selected`` by construction and is passed through unchanged).
    """

    from .mace_export import MaceExtxyzPolicy
    from .target_size_execution import (
        publish_immutable_bytes_create_or_verify,
        publish_immutable_json_create_or_verify,
    )

    policy = MaceExtxyzPolicy() if extxyz_policy is None else extxyz_policy
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    training = tuple(str(v) for v in training_frame_uids)
    monitor_frames = tuple(str(v) for v in monitor_frame_uids)
    outer = (
        ()
        if outer_evaluation_frame_uids is None
        else tuple(str(v) for v in outer_evaluation_frame_uids)
    )
    groups = (set(training), set(monitor_frames), set(outer))
    for position, left in enumerate(groups):
        for right in groups[position + 1 :]:
            if left & right:
                raise PostSelectionExecutionError(
                    "Post-selection training, checkpoint-monitor, and outer "
                    "evaluation memberships must be disjoint."
                )
    fitted = (
        fit_post_selection_preparation(
            context,
            membership=training,
            owner_plan_digest=run_plan.content_digest,
            common_training_policy=common_training_policy,
        )
        if preparation is None
        else preparation
    )
    if set(fitted.membership) != set(training):
        raise PostSelectionExecutionError(
            "The supplied fitted preparation was fitted from a different "
            "membership than this run trains on."
        )
    target_train = _write_role_artifact(
        context,
        output_directory=root,
        role=DATASET_ROLE_TARGET_TRAIN,
        frame_uids=training,
        extxyz_policy=policy,
        preparation=fitted,
    )
    monitor = _write_role_artifact(
        context,
        output_directory=root,
        role=DATASET_ROLE_CHECKPOINT_MONITOR,
        frame_uids=monitor_frames,
        extxyz_policy=policy,
        preparation=None,
    )
    evaluation = (
        None
        if not outer
        else _write_role_artifact(
            context,
            output_directory=root,
            role=DATASET_ROLE_OUTER_EVALUATION,
            frame_uids=outer,
            extxyz_policy=policy,
            preparation=None,
        )
    )
    config = _post_selection_mace_config(
        run_identity=run_plan.run_identity,
        optimizer_seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
        preparation=fitted,
        optimizer_policy=optimizer_policy,
        target_train=target_train,
        monitor=monitor,
        extxyz_policy=policy,
        method=method,
        mace_architecture=mace_architecture,
        foundation_model=foundation_model,
        foundation_head=foundation_head,
        multiheads_finetuning=multiheads_finetuning,
        replay_train=replay_train,
        replay_monitor=replay_monitor,
    )
    config_path = root / "post_selection_mace_config.yaml"
    config_bytes = json.dumps(config, indent=2, sort_keys=True).encode("utf-8")
    config_sha256 = hashlib.sha256(config_bytes).hexdigest()
    publish_immutable_bytes_create_or_verify(
        config_path, config_bytes, expected_sha256=config_sha256
    )
    record = PostSelectionMaterialization(
        run_plan_digest=run_plan.content_digest,
        run_identity=run_plan.run_identity,
        preparation_digest=fitted.content_digest,
        target_train_artifact=target_train,
        checkpoint_monitor_artifact=monitor,
        outer_evaluation_artifact=evaluation,
        mace_config_relative_path=config_path.name,
        mace_config_sha256=config_sha256,
        mace_config_digest=digest(config),
        output_directory=str(root),
    )
    publish_immutable_json_create_or_verify(
        root / "materialization.json",
        record.to_dict(),
        deserializer=PostSelectionMaterialization.from_dict,
    )
    return fitted, record


# ---------------------------------------------------------------------------
# TRAIN2 execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PostSelectionRungRequest:
    """Everything one post-selection TRAIN2 run needs, already authenticated."""

    plan: Any
    run_plan: Any
    materialization: PostSelectionMaterialization
    materialization_directory: Path
    checkpoint_directory: Path
    optimizer_policy: Any
    start_epoch: int = 0
    foundation_identity: Any | None = None
    foundation_model_path: Path | None = None
    replay_train_artifact: Any | None = None
    replay_train_path: Path | None = None
    replay_monitor_artifact: Any | None = None
    replay_monitor_path: Path | None = None


class PostSelectionTrainer(Protocol):
    """The one accepted substitution point for expensive post-selection training.

    It sits strictly below the owner boundary: the run plan, fitted preparation,
    materialization, and TRAIN2 runtime plan handed to it were all produced by
    real owners, and the summary it returns is re-authenticated before it can
    become evidence.
    """

    def __call__(self, request: PostSelectionRungRequest) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class MacePostSelectionTrainer:
    """The production trainer: drives MACE through the accepted wrapper script."""

    wrapper_path: Path

    def __call__(self, request: PostSelectionRungRequest) -> Any:
        import os
        import subprocess
        import yaml

        from ._common import sha256_file_cached
        from .train2_runtime import (
            TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE,
            TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE,
            load_train2_runtime_summary,
        )

        # 1. Internal P5 configuration bytes, SHA256, digest, and schema
        internal_config_path = (
            request.materialization_directory
            / request.materialization.mace_config_relative_path
        )
        if not internal_config_path.is_file():
            raise PostSelectionExecutionError(
                f"Post-selection MACE configuration is missing: {internal_config_path}"
            )
        config_bytes = internal_config_path.read_bytes()
        if (
            hashlib.sha256(config_bytes).hexdigest()
            != request.materialization.mace_config_sha256
        ):
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration bytes changed before training."
            )
        internal_payload = json.loads(config_bytes.decode("utf-8"))
        if digest(internal_payload) != request.materialization.mace_config_digest:
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration content changed before training."
            )
        if internal_payload.get("schema") != POST_SELECTION_MACE_CONFIG_SCHEMA:
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration schema mismatch."
            )
        try:
            configured_target_head, configured_replay_head = (
                canonical_post_selection_head_names(
                    target_head_name=internal_payload.get(
                        "target_head_name", POST_SELECTION_TARGET_HEAD_NAME
                    ),
                    replay_head_name=internal_payload.get(
                        "replay_head_name", POST_SELECTION_REPLAY_HEAD_NAME
                    ),
                )
            )
            plan_target_head, plan_replay_head = canonical_post_selection_head_names(
                target_head_name=getattr(
                    request.plan, "target_head_name", POST_SELECTION_TARGET_HEAD_NAME
                ),
                replay_head_name=getattr(
                    request.plan, "replay_head_name", POST_SELECTION_REPLAY_HEAD_NAME
                ),
            )
        except TrainingDataInputError as exc:
            raise PostSelectionExecutionError(
                "Post-selection runtime and executable configuration disagree "
                "with the canonical P5 fine-tuning head namespace."
            ) from exc
        if (configured_target_head, configured_replay_head) != (
            plan_target_head,
            plan_replay_head,
        ):
            raise PostSelectionExecutionError(
                "Post-selection runtime plan and internal configuration use "
                "different fine-tuning head names."
            )
        if internal_payload.get("multiheads_finetuning"):
            heads = internal_payload.get("heads")
            if not isinstance(heads, Mapping) or set(heads) != {
                POST_SELECTION_TARGET_HEAD_NAME,
                POST_SELECTION_REPLAY_HEAD_NAME,
            }:
                raise PostSelectionExecutionError(
                    "Post-selection multihead configuration must expose exactly "
                    "the canonical target_head and pt_head heads."
                )

        # 2. Target training ExtXYZ at materialization_directory / target_train_artifact.relative_path
        target_train_art = request.materialization.target_train_artifact
        target_train_path = request.materialization_directory / target_train_art.relative_path
        if not target_train_path.is_file():
            raise PostSelectionExecutionError(
                f"Target training ExtXYZ is missing: {target_train_path}"
            )
        if sha256_file_cached(target_train_path) != target_train_art.sha256:
            raise PostSelectionExecutionError(
                "Target training ExtXYZ SHA256 does not match materialization artifact."
            )

        # 3. Target validation/checkpoint-monitor ExtXYZ
        target_valid_art = request.materialization.checkpoint_monitor_artifact
        target_valid_path = request.materialization_directory / target_valid_art.relative_path
        if not target_valid_path.is_file():
            raise PostSelectionExecutionError(
                f"Target validation ExtXYZ is missing: {target_valid_path}"
            )
        if sha256_file_cached(target_valid_path) != target_valid_art.sha256:
            raise PostSelectionExecutionError(
                "Target validation ExtXYZ SHA256 does not match materialization artifact."
            )

        # 4. Foundation checkpoint for non-scratch methods
        if internal_payload.get("foundation_model") or request.foundation_identity is not None or request.foundation_model_path is not None:
            if request.foundation_identity is None or request.foundation_model_path is None:
                raise PostSelectionExecutionError(
                    "Non-scratch training requires canonical foundation identity and path in request."
                )
            f_path = Path(request.foundation_model_path).resolve()
            if not f_path.is_file():
                raise PostSelectionExecutionError(
                    f"Foundation model file is missing: {f_path}"
                )
            if sha256_file_cached(f_path) != request.foundation_identity.sha256:
                raise PostSelectionExecutionError(
                    "Foundation model file SHA256 does not match canonical foundation identity."
                )
            # 5. if internal config contains foundation locator/head, verify agreement
            if internal_payload.get("foundation_model"):
                if Path(internal_payload["foundation_model"]).resolve() != f_path:
                    raise PostSelectionExecutionError(
                        "Internal config foundation_model does not match request foundation model path."
                    )
            if internal_payload.get("foundation_head"):
                if internal_payload["foundation_head"] != request.foundation_identity.foundation_head:
                    raise PostSelectionExecutionError(
                        "Internal config foundation_head does not match request foundation head."
                    )

        # 6. For multihead_replay: replay train path/artifact present and file SHA matches
        if internal_payload.get("multiheads_finetuning") or request.replay_train_artifact is not None or request.replay_train_path is not None:
            if request.replay_train_artifact is None or request.replay_train_path is None:
                raise PostSelectionExecutionError(
                    "multihead_replay training requires replay train artifact and path in request."
                )
            rp_train_p = Path(request.replay_train_path).resolve()
            if not rp_train_p.is_file():
                raise PostSelectionExecutionError(
                    f"Replay train file is missing: {rp_train_p}"
                )
            artifact_path = getattr(request.replay_train_artifact, "path", None)
            if artifact_path is not None and Path(str(artifact_path)).resolve() != rp_train_p:
                raise PostSelectionExecutionError(
                    "Replay train path does not match its authenticated artifact."
                )
            if sha256_file_cached(rp_train_p) != request.replay_train_artifact.sha256:
                raise PostSelectionExecutionError(
                    "Replay train file SHA256 does not match replay train artifact."
                )

        # 7. When replay monitor is passed: replay monitor path/artifact present and file SHA matches
        if request.replay_monitor_artifact is not None or request.replay_monitor_path is not None:
            if request.replay_monitor_artifact is None or request.replay_monitor_path is None:
                raise PostSelectionExecutionError(
                    "Replay monitor requires both artifact and path in request."
                )
            rp_mon_p = Path(request.replay_monitor_path).resolve()
            if not rp_mon_p.is_file():
                raise PostSelectionExecutionError(
                    f"Replay monitor file is missing: {rp_mon_p}"
                )
            artifact_path = getattr(request.replay_monitor_artifact, "path", None)
            if artifact_path is not None and Path(str(artifact_path)).resolve() != rp_mon_p:
                raise PostSelectionExecutionError(
                    "Replay monitor path does not match its authenticated artifact."
                )
            if sha256_file_cached(rp_mon_p) != request.replay_monitor_artifact.sha256:
                raise PostSelectionExecutionError(
                    "Replay monitor file SHA256 does not match replay monitor artifact."
                )
            # 8. when request.plan.replay_monitor_enabled: monitor SHA must equal true_replay_monitor_sha256
            if request.plan.replay_monitor_enabled:
                if request.replay_monitor_artifact.sha256 != request.plan.true_replay_monitor_sha256:
                    raise PostSelectionExecutionError(
                        "Replay monitor SHA256 does not match runtime plan true_replay_monitor_sha256."
                    )
        elif request.plan.replay_monitor_enabled:
            raise PostSelectionExecutionError(
                "Runtime plan requires replay monitor, but none was provided in request."
            )

        # 9. Write executable configuration and execute wrapper subprocess
        executable_payload = post_selection_mace_run_configuration(internal_payload)
        executable_config_path = (
            request.materialization_directory / "mace_run_config.yaml"
        )
        executable_config_path.write_text(
            yaml.safe_dump(executable_payload, sort_keys=False), encoding="utf-8"
        )

        run_root = request.materialization_directory.parent
        command = [
            str(self.wrapper_path),
            "--config",
            str(executable_config_path.name),
            "--model_dir",
            str(run_root / "models"),
            "--checkpoints_dir",
            str(request.checkpoint_directory),
            "--log_dir",
            str(run_root / "logs"),
            "--results_dir",
            str(run_root / "results"),
        ]

        env = dict(os.environ)
        env[TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE] = json.dumps(request.plan.to_dict())
        env["PYTHONHASHSEED"] = str(request.plan.optimizer_policy_digest[:8])
        if hasattr(request.optimizer_policy, "seed"):
            env["PYTHONHASHSEED"] = str(int(request.optimizer_policy.seed))
        if request.plan.replay_monitor_enabled and request.replay_monitor_path is not None:
            env[TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE] = str(
                Path(request.replay_monitor_path).resolve()
            )

        proc = subprocess.run(
            command,
            cwd=str(request.materialization_directory),
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise PostSelectionExecutionError(
                f"Post-selection MACE training failed (exit {proc.returncode}):\n"
                f"{proc.stderr}"
            )

        try:
            summary = load_train2_runtime_summary(request.checkpoint_directory)
        except Exception as exc:
            raise PostSelectionExecutionError(
                "The MACE wrapper exited successfully without a valid canonical "
                "TRAIN2 runtime summary."
            ) from exc
        if summary.plan_digest != request.plan.content_digest:
            raise PostSelectionExecutionError(
                "Loaded TRAIN2 runtime summary plan digest does not match request."
            )
        if summary.optimizer_policy_digest != request.plan.optimizer_policy_digest:
            raise PostSelectionExecutionError(
                "Loaded TRAIN2 runtime summary optimizer policy digest does not match request."
            )
        return summary


def build_post_selection_foundation_baseline_provider(
    *,
    foundation_path: str | Path,
    foundation_identity: Any,
    foundation_head: str | None = None,
    device: str = "cpu",
    default_dtype: str = "float64",
    allow_forward_override: bool = False,
) -> Any:
    """Construct the canonical foundation baseline prediction provider."""

    from ._common import sha256_file_cached
    from .model_features import MaceCalculatorProvider

    path = Path(foundation_path)
    if not path.is_file():
        raise PostSelectionExecutionError(
            f"Foundation baseline checkpoint does not exist: {path}"
        )
    current_sha = sha256_file_cached(path)
    if foundation_identity is not None and hasattr(foundation_identity, "sha256"):
        if current_sha != foundation_identity.sha256:
            raise PostSelectionExecutionError(
                "Foundation baseline model bytes changed on disk (SHA256 mismatch)."
            )
    head = foundation_head or (
        foundation_identity.foundation_head
        if foundation_identity is not None
        and hasattr(foundation_identity, "foundation_head")
        else "default"
    )
    foundation_inference_identity = None
    if foundation_identity is not None and hasattr(foundation_identity, "canonical_content_digest"):
        from .foundation import FoundationInferenceIdentity

        foundation_inference_identity = FoundationInferenceIdentity(
            foundation_potential_digest=foundation_identity.canonical_content_digest,
            default_dtype="float64" if default_dtype == "float64" else "float32",
            backend="e3nn",
            resolved_kernel_mode="eager",
            mace_version="unknown",
            adapter_version="v1",
        )
    return MaceCalculatorProvider.from_model_path(
        path,
        device=device,
        default_dtype=default_dtype,
        foundation_potential_identity=foundation_identity,
        foundation_inference_identity=foundation_inference_identity,
        head=head,
        allow_forward_override=allow_forward_override,
    )


_MACE_CONFIG_PASSTHROUGH_KEYS = (
    "name",
    "seed",
    "atomic_numbers",
    "E0s",
    "energy_key",
    "forces_key",
    "stress_key",
    "lr",
    "batch_size",
    "valid_batch_size",
    "num_workers",
    "max_num_epochs",
    "ema",
    "ema_decay",
    "amsgrad",
    "weight_decay",
    "clip_grad",
    "default_dtype",
    "device",
    "eval_interval",
    "enable_cueq",
    "only_cueq",
)


def post_selection_mace_run_configuration(
    config: Mapping[str, Any]
) -> dict[str, Any]:
    """Rename the frozen post-selection configuration into MACE's argument names."""

    if config.get("schema") != POST_SELECTION_MACE_CONFIG_SCHEMA:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration does not carry the accepted schema."
        )
    try:
        target_head_name, replay_head_name = canonical_post_selection_head_names(
            target_head_name=config.get(
                "target_head_name", POST_SELECTION_TARGET_HEAD_NAME
            ),
            replay_head_name=config.get(
                "replay_head_name", POST_SELECTION_REPLAY_HEAD_NAME
            ),
        )
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration carries a noncanonical "
            "fine-tuning head namespace."
        ) from exc
    result: dict[str, Any] = {
        key: config[key] for key in _MACE_CONFIG_PASSTHROUGH_KEYS if key in config
    }
    result["train_file"] = config["target_train_file"]
    result["valid_file"] = config["target_valid_file"]
    if config.get("foundation_model"):
        result["foundation_model"] = str(config["foundation_model"])
    if config.get("foundation_head"):
        result["foundation_head"] = str(config["foundation_head"])
    if config.get("multiheads_finetuning"):
        result["multiheads_finetuning"] = True
        if "pt_train_file" in config:
            result["pt_train_file"] = config["pt_train_file"]
        if "pt_valid_file" in config:
            result["pt_valid_file"] = config["pt_valid_file"]
        heads = config.get("heads")
        if not isinstance(heads, Mapping) or set(heads) != {
            target_head_name,
            replay_head_name,
        }:
            raise PostSelectionExecutionError(
                "Post-selection multihead configuration must expose exactly "
                f"{target_head_name!r} and {replay_head_name!r}."
            )
        result["heads"] = dict(heads)
    for key, value in dict(config.get("mace_architecture") or {}).items():
        result.setdefault(str(key), value)
    return result


def post_selection_runtime_plan(
    *,
    method: PostSelectionMethodIdentity,
    optimizer_policy: Any,
    budget_policy: Any,
    structures_per_epoch: int,
    learning_rate_policy: Any = None,
    replay_monitor_enabled: bool = False,
    true_replay_monitor_sha256: str | None = None,
    target_head_name: str = POST_SELECTION_TARGET_HEAD_NAME,
    replay_head_name: str = POST_SELECTION_REPLAY_HEAD_NAME,
) -> Any:
    """Build the TRAIN2 runtime plan for one post-selection role.

    The budget arrives from the *role* policy - the CV budget for a fold, the
    configured production horizon for a final run - while the method identity
    and the LR/optimizer policies are shared.  That is the identity split made
    executable.
    """

    from .train2_policy import LearningRateSchedulePolicy
    from .train2_runtime import Train2RuntimePlan

    try:
        target_head_name, replay_head_name = canonical_post_selection_head_names(
            target_head_name=target_head_name,
            replay_head_name=replay_head_name,
        )
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            "Post-selection TRAIN2 runtime plan carries a noncanonical "
            "fine-tuning head namespace."
        ) from exc

    return Train2RuntimePlan(
        training_protocol_digest=method.content_digest,
        optimizer_policy_digest=optimizer_policy.policy_digest,
        budget_policy=budget_policy,
        learning_rate_policy=(
            LearningRateSchedulePolicy()
            if learning_rate_policy is None
            else learning_rate_policy
        ),
        structures_per_epoch=int(structures_per_epoch),
        replay_monitor_enabled=bool(replay_monitor_enabled),
        target_head_name=target_head_name,
        replay_head_name=replay_head_name,
        true_replay_monitor_sha256=true_replay_monitor_sha256,
        execution_epoch_limit=int(budget_policy.planned_epochs),
    )


# ---------------------------------------------------------------------------
# EVAL2 evidence
# ---------------------------------------------------------------------------


def post_selection_eval_role_digest(
    *, run_plan: Any, dataset_role: str, artifact: Any
) -> str:
    """Identity of one exact (run, dataset role, evaluation membership) position."""

    frame_uids = (
        list(artifact.frame_uids)
        if hasattr(artifact, "frame_uids")
        else [f"replay_frame_{i}" for i in range(getattr(artifact, "configuration_count", 0))]
    )
    membership_digest = (
        getattr(artifact, "membership_digest", None)
        or getattr(artifact, "geometry_set_digest", None)
        or digest({"frame_uids": frame_uids})
    )
    return digest(
        {
            "schema": POST_SELECTION_EVAL_ROLE_SCHEMA,
            "run_plan_digest": run_plan.content_digest,
            "run_identity": run_plan.run_identity,
            "run_role": run_plan.run_role,
            "dataset_role": str(dataset_role),
            "evaluation_membership_digest": membership_digest,
            "evaluation_frame_uids": frame_uids,
            "artifact_sha256": artifact.sha256,
        }
    )


def _authenticated_atoms(artifact: Any, root_directory: Path) -> list[Any]:
    import ase.io

    if hasattr(artifact, "path") and Path(str(artifact.path)).is_absolute():
        path = Path(artifact.path)
    else:
        rel = getattr(artifact, "relative_path", getattr(artifact, "path", ""))
        path = root_directory / rel
    if not path.is_file():
        raise PostSelectionExecutionError(
            f"Post-selection evaluation artifact is missing: {path}"
        )
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != artifact.sha256:
        raise PostSelectionExecutionError(
            "Post-selection evaluation artifact bytes changed on disk."
        )
    return ase.io.read(io.StringIO(raw.decode("utf-8")), format="extxyz", index=":")


def evaluate_post_selection_dataset(
    *,
    run_plan: Any,
    artifact: Any,
    dataset_role: str,
    root_directory: str | os.PathLike[str],
    provider: Any,
    block_ids: Sequence[str],
    extxyz_policy: Any = None,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
) -> Any:
    """Reduce one authenticated dataset evaluation through the EVAL2 engine.

    The artifact bytes are re-hashed before they are read, and the reduction is
    the shared EVAL2 owner rather than a P5-local metric implementation, so a
    post-selection metric means exactly what a screening metric means.
    """

    import numpy as np

    from .eval2 import eval2_target_metrics_from_prediction_view
    from .evaluation_views import build_evaluation_dataset_view

    root = Path(root_directory)
    atoms_list = _authenticated_atoms(artifact, root)
    frame_count = (
        len(artifact.frame_uids)
        if hasattr(artifact, "frame_uids")
        else int(getattr(artifact, "configuration_count", len(atoms_list)))
    )
    if len(atoms_list) != frame_count:
        raise PostSelectionExecutionError(
            "Post-selection evaluation artifact frame count mismatch."
        )
    if len(block_ids) != len(atoms_list):
        raise PostSelectionExecutionError(
            "Post-selection evaluation requires one split-exclusion component "
            "identity per evaluated frame."
        )
    from .mace_export import MaceExtxyzPolicy

    keys = MaceExtxyzPolicy() if extxyz_policy is None else extxyz_policy
    artifact_policy = getattr(
        artifact, "extxyz_policy_digest", getattr(artifact, "policy_digest", None)
    )
    if artifact_policy is not None and keys.policy_digest != artifact_policy:
        raise PostSelectionExecutionError(
            "The evaluation artifact was exported under a different ExtXYZ policy "
            "than this evaluation reads it with."
        )
    view = build_evaluation_dataset_view(
        atoms_list,
        energy_key=keys.energy_key,
        forces_key=keys.forces_key,
        stress_key=keys.stress_key,
        focus_atomic_numbers=(),
        condition_keys=(),
    )
    if inference_evaluator is not None:
        raw_predictions = inference_evaluator(provider, atoms_list)
    else:
        raw_predictions = provider.predict_batch(atoms_list)
    if len(raw_predictions) != len(atoms_list):
        raise PostSelectionExecutionError(
            "Post-selection inference returned the wrong number of predictions."
        )
    role_digest = post_selection_eval_role_digest(
        run_plan=run_plan, dataset_role=dataset_role, artifact=artifact
    )
    prediction_digest = digest(
        {
            "schema": "mdstats.post-selection-eval2-predictions.v1",
            "role_digest": role_digest,
            "predictions": [
                {
                    "energy_ev": float(item.energy_ev),
                    "forces_ev_per_angstrom": np.asarray(
                        item.forces_ev_per_angstrom, dtype=np.float64
                    ).tolist(),
                }
                for item in raw_predictions
            ],
        }
    )
    return eval2_target_metrics_from_prediction_view(
        view,
        raw_predictions,
        block_ids=list(block_ids),
        target_role_digest=role_digest,
        prediction_digest=prediction_digest,
    )


def post_selection_checkpoint_catalog(
    *, run_plan: Any, checkpoint_directory: str | os.PathLike[str]
) -> Any:
    """Inventory the durable checkpoint bytes this run actually produced.

    The glob matches only epoch-stamped checkpoints, which is what the TRAIN2
    naming convention writes; the continuation companion and any other sibling
    ``.pt`` state in the same directory is deliberately not a candidate.
    """

    from .campaign_control import inventory_checkpoint_files

    return inventory_checkpoint_files(
        checkpoint_directory,
        run_plan_digest=run_plan.content_digest,
        run_id=run_plan.run_identity,
        pattern="*epoch*.pt",
    )


def post_selection_checkpoint_candidates(
    *,
    run_plan: Any,
    checkpoint_directory: str | os.PathLike[str],
    runtime_plan: Any,
) -> tuple[Any, ...]:
    """Authenticate this run's TRAIN2 history into EVAL2 trajectory points."""

    from .eval2 import read_train2_trajectory_points

    catalog = post_selection_checkpoint_catalog(
        run_plan=run_plan, checkpoint_directory=checkpoint_directory
    )
    try:
        canonical_post_selection_head_names(
            target_head_name=runtime_plan.target_head_name,
            replay_head_name=runtime_plan.replay_head_name,
        )
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            "Post-selection checkpoint trajectory uses a noncanonical "
            "fine-tuning head namespace."
        ) from exc
    return read_train2_trajectory_points(
        checkpoint_directory,
        checkpoint_catalog=catalog,
        target_head_name=runtime_plan.target_head_name,
    )


def authenticate_post_selection_provider(
    *,
    materialization: PostSelectionMaterialization,
    materialization_directory: str | os.PathLike[str],
    checkpoint_directory: str | os.PathLike[str],
    checkpoint_name: str,
    checkpoint_sha256: str,
    summary: Any,
    evaluation_model_state: str,
    allow_forward_override: bool,
) -> tuple[Any, str]:
    """Authenticate one post-selection checkpoint through the shared provider owner.

    This is the same TRAIN2 provider authentication the target-size screen uses;
    post-selection evaluation does not get a weaker checkpoint-provenance rule
    just because it happens later in the lifecycle.
    """

    from .target_size_execution import authenticate_train2_checkpoint_provider

    material_root = Path(materialization_directory)
    config_path = material_root / materialization.mace_config_relative_path
    config_bytes = config_path.read_bytes()
    if hashlib.sha256(config_bytes).hexdigest() != materialization.mace_config_sha256:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration bytes changed before evaluation."
        )
    config_payload = json.loads(config_bytes.decode("utf-8"))
    if digest(config_payload) != materialization.mace_config_digest:
        raise PostSelectionExecutionError(
            "Post-selection MACE configuration content changed before evaluation."
        )
    checkpoint_root = Path(checkpoint_directory)
    provider, evaluated_digest, _companion = authenticate_train2_checkpoint_provider(
        raw_checkpoint_path=checkpoint_root / checkpoint_name,
        raw_checkpoint_sha256=checkpoint_sha256,
        companion_path=checkpoint_root / "train2_runtime.pt",
        companion_sha256=_companion_sha256(checkpoint_root),
        summary=summary,
        evaluation_model_state=evaluation_model_state,
        config_payload=config_payload,
        allow_forward_override=allow_forward_override,
    )
    return provider, evaluated_digest


def _companion_sha256(checkpoint_directory: Path) -> str:
    companion = checkpoint_directory / "train2_runtime.pt"
    if not companion.is_file():
        raise PostSelectionExecutionError(
            f"TRAIN2 continuation companion missing in {checkpoint_directory}."
        )
    return hashlib.sha256(companion.read_bytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class PostSelectionRunEvidence:
    """Realized evidence of one post-selection run, bound to its plan."""

    run_plan_digest: str
    run_identity: str
    run_role: str
    materialization_digest: str
    preparation_digest: str
    runtime_summary_digest: str
    representative_candidate_identity: str
    representative_checkpoint_sha256: str
    representative_record_digest: str
    monitor_metric_record_digest: str
    outer_metric_record_digest: str | None

    def __post_init__(self) -> None:
        for name in (
            "run_plan_digest",
            "run_identity",
            "materialization_digest",
            "preparation_digest",
            "runtime_summary_digest",
            "representative_checkpoint_sha256",
            "representative_record_digest",
            "monitor_metric_record_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.outer_metric_record_digest is not None:
            object.__setattr__(
                self,
                "outer_metric_record_digest",
                validate_digest(
                    self.outer_metric_record_digest,
                    name="outer_metric_record_digest",
                ),
            )
        identity = str(self.representative_candidate_identity).strip()
        if not identity:
            raise TrainingDataInputError(
                "Run evidence requires its frozen representative identity."
            )
        object.__setattr__(self, "representative_candidate_identity", identity)
        object.__setattr__(self, "run_role", str(self.run_role))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": POST_SELECTION_RUN_EVIDENCE_SCHEMA,
            "run_plan_digest": self.run_plan_digest,
            "run_identity": self.run_identity,
            "run_role": self.run_role,
            "materialization_digest": self.materialization_digest,
            "preparation_digest": self.preparation_digest,
            "runtime_summary_digest": self.runtime_summary_digest,
            "representative_candidate_identity": self.representative_candidate_identity,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "representative_record_digest": self.representative_record_digest,
            "monitor_metric_record_digest": self.monitor_metric_record_digest,
            "outer_metric_record_digest": self.outer_metric_record_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PostSelectionRunEvidence":
        if payload.get("schema") != POST_SELECTION_RUN_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported post-selection run-evidence schema."
            )
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            run_identity=str(payload["run_identity"]),
            run_role=str(payload["run_role"]),
            materialization_digest=str(payload["materialization_digest"]),
            preparation_digest=str(payload["preparation_digest"]),
            runtime_summary_digest=str(payload["runtime_summary_digest"]),
            representative_candidate_identity=str(
                payload["representative_candidate_identity"]
            ),
            representative_checkpoint_sha256=str(
                payload["representative_checkpoint_sha256"]
            ),
            representative_record_digest=str(payload["representative_record_digest"]),
            monitor_metric_record_digest=str(payload["monitor_metric_record_digest"]),
            outer_metric_record_digest=(
                None
                if payload.get("outer_metric_record_digest") is None
                else str(payload["outer_metric_record_digest"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Post-selection run-evidence digest mismatch."
            )
        return result


__all__ = [
    "DATASET_ROLE_CHECKPOINT_MONITOR",
    "DATASET_ROLE_OUTER_EVALUATION",
    "DATASET_ROLE_TARGET_TRAIN",
    "POST_SELECTION_EVAL_ROLE_SCHEMA",
    "POST_SELECTION_MACE_CONFIG_SCHEMA",
    "POST_SELECTION_MATERIALIZATION_SCHEMA",
    "POST_SELECTION_PREPARATION_SCHEMA",
    "POST_SELECTION_RUN_EVIDENCE_SCHEMA",
    "POST_SELECTION_REPLAY_HEAD_NAME",
    "POST_SELECTION_TARGET_HEAD_NAME",
    "MacePostSelectionTrainer",
    "PostSelectionExecutionError",
    "PostSelectionFittedPreparation",
    "PostSelectionMaterialization",
    "PostSelectionRunEvidence",
    "PostSelectionRungRequest",
    "PostSelectionTrainer",
    "authenticate_post_selection_provider",
    "build_post_selection_foundation_baseline_provider",
    "evaluate_post_selection_dataset",
    "fit_post_selection_preparation",
    "materialize_post_selection_run",
    "post_selection_checkpoint_candidates",
    "post_selection_checkpoint_catalog",
    "post_selection_eval_role_digest",
    "post_selection_mace_run_configuration",
    "post_selection_runtime_plan",
]
