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
import math
import os
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .bounded_inference import run_bounded_inference
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
)
from .mace_compatibility import (
    MACE_EXECUTABLE_LOSS_FAMILY as _MACE_EXECUTABLE_LOSS_FAMILY,
)
from .mace_compatibility import (
    MACE_REPLAY_FORCE_MH_FT_LR,
    MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
)
from .post_selection_identity import (
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    PostSelectionMethodIdentity,
    canonical_post_selection_head_names,
)
from .progress_timing import (
    ProgressRateTracker,
    format_progress_fraction,
    format_progress_timing_fields,
)

POST_SELECTION_PREPARATION_SCHEMA = "mdstats.post-selection-fitted-preparation.v2"
POST_SELECTION_MATERIALIZATION_SCHEMA = "mdstats.post-selection-materialization.v1"
POST_SELECTION_MACE_CONFIG_SCHEMA = "mdstats.post-selection-mace-config.v2"
#: The executable MACE loss family for post-selection CV and fresh production;
#: the shared owner in ``objectives`` explains why this family and not ``universal``.
POST_SELECTION_MACE_LOSS_FAMILY = _MACE_EXECUTABLE_LOSS_FAMILY
POST_SELECTION_REPLAY_FORCE_MH_FT_LR = MACE_REPLAY_FORCE_MH_FT_LR
POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD = (
    MACE_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
)
# Pinned MACE's ordinary one-head parser projection uses this source-owned
# namespace when no explicit ``heads`` mapping is supplied. Replay paths use
# the canonical target_head mapping below.
POST_SELECTION_SINGLE_HEAD_NAME = "Default"
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
    objective_policy: Any
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
            # The resolved global objective travels with the fitted preparation so
            # CV and final production emit the same coefficients the screen did.
            "objective_policy": self.objective_policy.to_dict(),
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
        from .objectives import FrameTrainingWeight, TrainingObjectivePolicy
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
            objective_policy=TrainingObjectivePolicy.from_dict(
                payload["objective_policy"]
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
        configuration_weights={
            item.frame_uid: item for item in configuration_weights
        },
    )
    return PostSelectionFittedPreparation(
        owner_plan_digest=str(owner_plan_digest),
        dataset_role=dataset_role,
        common_training_policy_digest=policy.content_digest,
        objective_policy=policy.objective_policy,
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

    training_mode = str(method.training_mode).strip()
    if training_mode not in {
        "scratch",
        "naive_fine_tuning",
        "multihead_replay",
    }:
        raise PostSelectionExecutionError(
            f"Unsupported post-selection training mode: {training_mode!r}."
        )
    expected_multihead = training_mode == "multihead_replay"
    if bool(multiheads_finetuning) != expected_multihead:
        raise PostSelectionExecutionError(
            "Post-selection method identity and MACE multihead execution mode "
            "disagree."
        )
    if expected_multihead:
        if not foundation_head:
            raise PostSelectionExecutionError(
                "multihead_replay materialization requires the canonical "
                "foundation head."
            )
        if replay_train is None or replay_monitor is None:
            raise PostSelectionExecutionError(
                "multihead_replay materialization requires both replay training "
                "and independent TRUE_DFT monitor artifacts."
            )
    elif training_mode == "scratch":
        if foundation_head:
            raise PostSelectionExecutionError(
                "scratch materialization cannot carry a foundation checkpoint."
            )
        if replay_train is not None or replay_monitor is not None:
            raise PostSelectionExecutionError(
                "scratch materialization cannot carry replay training fields."
            )
    else:
        if not foundation_head:
            raise PostSelectionExecutionError(
                "naive_fine_tuning materialization requires the canonical "
                "foundation head."
            )
        if replay_train is not None or replay_monitor is not None:
            raise PostSelectionExecutionError(
                "naive_fine_tuning materialization cannot carry replay training "
                "fields."
            )

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
        # The declared mdstats objective is the objective actually optimized, in
        # cross-validation and in final production exactly as in the screen.
        # ``loss="stress"`` selects MACE's WeightedEnergyForcesStressLoss, whose
        # native reductions consume ``config_weight`` and the local property
        # masks linearly; without these keys MACE would default to
        # ``forces_weight=100`` under its own ``weighted`` loss.
        "loss": POST_SELECTION_MACE_LOSS_FAMILY,
        "energy_weight": float(preparation.objective_policy.energy_weight),
        "forces_weight": float(preparation.objective_policy.forces_weight),
        "stress_weight": float(preparation.objective_policy.stress_weight),
        "batch_size": int(optimizer_policy.batch_size),
        "valid_batch_size": int(optimizer_policy.valid_batch_size),
        "num_workers": int(optimizer_policy.num_workers),
        "max_num_epochs": int(planned_epochs),
        "ema": bool(optimizer_policy.ema),
        "ema_decay": float(optimizer_policy.ema_decay),
        # TRAIN2 authenticates each completed epoch against the raw MACE
        # checkpoint for that epoch.  Retaining every checkpoint is the
        # existing checkpoint-control policy, not a post-hoc evidence aid.
        "save_all_checkpoints": True,
        "amsgrad": bool(optimizer_policy.amsgrad),
        "weight_decay": float(optimizer_policy.weight_decay),
        "clip_grad": float(optimizer_policy.clip_grad),
        "default_dtype": str(method.default_dtype),
        "device": str(optimizer_policy.device),
        "method_identity_digest": method.content_digest,
        # MACE 0.3.16 otherwise recomputes this from the local training
        # collection. The fitted value is a common architecture input, so
        # local data must not be allowed to change it between target sizes or
        # replay/target representations.
        "compute_avg_num_neighbors": False,
        "mace_architecture": arch,
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
    }
    if hasattr(optimizer_policy, "eval_interval"):
        config["eval_interval"] = int(optimizer_policy.eval_interval)
    if hasattr(optimizer_policy, "acceleration_policy") and optimizer_policy.acceleration_policy is not None:
        config.update(optimizer_policy.acceleration_policy.training_config())
    if foundation_head:
        # Only the checkpoint's *scientific* selection lives in the immutable
        # execution representation.  The filesystem locator is a runtime
        # address: it is authenticated per launch from the request, so a
        # byte-identical checkpoint reached through a different valid path
        # neither changes this run's identity nor blocks its execution.
        config["foundation_head"] = str(foundation_head)
    if multiheads_finetuning:
        config["multiheads_finetuning"] = True
        # These are explicit mdstats method controls.  MACE 0.3.16 otherwise
        # mutates LR/EMA and may duplicate target frames for low replay ratios.
        config["force_mh_ft_lr"] = POST_SELECTION_REPLAY_FORCE_MH_FT_LR
        config["real_pt_data_ratio_threshold"] = (
            POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
        )
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
    # Parent-side source/split sequence used to compose the authenticated
    # replay set digest. It is not serialized into the child environment.
    replay_geometry_identities: tuple[str, ...] | None = None
    # The following values are execution-only supervision seams. They are not
    # persisted in the TRAIN2 plan, materialization, or evidence identities.
    progress_context: Mapping[str, Any] | None = None
    cancellation_event: Any | None = None
    progress_callback: Callable[[str], None] | None = None
    progress_observer: Callable[[Mapping[str, Any]], None] | None = None
    telemetry_ref: Any | None = None
    # Runtime-only freshness bound for optimizer liveness. It is resolved
    # from the existing execution configuration and is not serialized into any
    # scientific or restart identity.
    optimizer_activity_timeout_seconds: float = 120.0


class PostSelectionTrainer(Protocol):
    """The one accepted substitution point for expensive post-selection training.

    It sits strictly below the owner boundary: the run plan, fitted preparation,
    materialization, and TRAIN2 runtime plan handed to it were all produced by
    real owners, and the summary it returns is re-authenticated before it can
    become evidence.
    """

    def __call__(self, request: PostSelectionRungRequest) -> Any:
        ...


def _mace_execution_frame_uid_set_digest(
    artifact: Any,
    *,
    role: str = "target",
) -> str | None:
    """Resolve the exact membership token set consumed by the MACE loader.

    Target DATA8 artifacts already carry their authenticated ``frame_uids``.
    Replay artifacts are resolved through the existing file metadata adapter:
    single-source views use ``replay_geometry_identity`` and supported legacy
    files retain their explicit ``frame_uid`` domain.  No token is inferred
    from order, count, pathname, or a newly generated replay namespace.
    """

    from .mace_compatibility import (
        _mace_execution_membership_values,
        mace_frame_uid_set_digest,
    )

    if role not in {"target", "replay"}:
        raise PostSelectionExecutionError(
            f"Unsupported MACE execution membership role: {role!r}."
        )
    if role == "target":
        values = getattr(artifact, "frame_uids", None)
        if values is None:
            path_value = getattr(artifact, "path", None)
            if path_value is None:
                return None
            values = _mace_execution_membership_values(
                path_value,
                role="target",
                head_name="target",
            )
    else:
        # ReplayFileArtifact already owns the canonical replay geometry
        # identities. Reuse that authenticated sequence at the parent
        # boundary; reparsing the same ExtXYZ here was the first half of the
        # P5 defect and made the child repeat it after MACE loaded its
        # Configuration objects. The path adapter remains the compatibility
        # route for older minimal artifacts that predate geometry identities.
        values = getattr(artifact, "geometry_identities", None)
        if values is None:
            path_value = getattr(artifact, "path", None)
            if path_value is None:
                return None
            values = _mace_execution_membership_values(
                path_value,
                role="replay",
                head_name="replay",
            )
    expected_count = getattr(artifact, "configuration_count", None)
    if expected_count is not None and len(tuple(values)) != int(expected_count):
        raise TrainingDataInputError(
            f"MACE {role} execution membership count differs from its artifact."
        )
    return mace_frame_uid_set_digest(values)


def _build_post_selection_mace_execution_authority(
    *,
    materialization: PostSelectionMaterialization,
    internal_payload: Mapping[str, Any],
    executable_payload: Mapping[str, Any],
    optimizer_policy: Any,
    replay_train_artifact: Any | None,
    replay_geometry_identities: Sequence[str] | None = None,
    structures_per_epoch: int | None = None,
) -> dict[str, Any]:
    """Build the one MACE authority used by launch and continuation checks."""

    from .mace_compatibility import (
        MACE_REPLAY_IDENTITY_DOMAIN_CANONICAL,
        MACE_REPLAY_IDENTITY_DOMAIN_LEGACY,
        build_mace_execution_authority,
        mace_frame_uid_set_digest,
    )

    target_train_art = materialization.target_train_artifact
    target_uid_digest = _mace_execution_frame_uid_set_digest(
        target_train_art,
        role="target",
    )
    internal_multihead = bool(internal_payload.get("multiheads_finetuning"))
    if internal_multihead:
        replay_count = int(
            getattr(
                replay_train_artifact,
                "configuration_count",
                max(
                    0,
                    int(
                        structures_per_epoch
                        if structures_per_epoch is not None
                        else getattr(optimizer_policy, "structures_per_epoch", 0)
                    )
                    - int(target_train_art.configuration_count),
                ),
            )
        )
    else:
        # A single-head P5/final request has no replay exposure.  Do not infer a
        # synthetic replay count merely because an older minimal fixture used
        # ``structures_per_epoch`` as a total-size hint.
        replay_count = 0
    replay_uid_digest = None
    if replay_train_artifact is not None:
        if replay_geometry_identities is None:
            replay_uid_digest = _mace_execution_frame_uid_set_digest(
                replay_train_artifact,
                role="replay",
            )
        else:
            replay_geometry_identities = tuple(
                validate_digest(str(value), name="replay_geometry_identity")
                for value in replay_geometry_identities
            )
            if len(replay_geometry_identities) != int(
                getattr(replay_train_artifact, "configuration_count", replay_count)
            ):
                raise PostSelectionExecutionError(
                    "P5 replay geometry transport does not match its artifact count."
                )
            replay_uid_digest = mace_frame_uid_set_digest(replay_geometry_identities)

    # Production projections always contain these canonical optimizer fields. A
    # few pre-launch guard fixtures intentionally stop at a minimal config
    # boundary; resolve their omitted values from the already-authenticated
    # optimizer policy so authority construction does not mask the guard being
    # tested.
    def executable_optimizer_value(name: str, default: Any) -> Any:
        if name in executable_payload:
            return executable_payload[name]
        return getattr(optimizer_policy, name, default)

    configured_ema = bool(executable_optimizer_value("ema", True))
    return build_mace_execution_authority(
        role="post_selection",
        config_digest=materialization.mace_config_digest,
        method_identity_digest=internal_payload.get("method_identity_digest"),
        loss_family=executable_optimizer_value(
            "loss", POST_SELECTION_MACE_LOSS_FAMILY
        ),
        learning_rate=float(executable_optimizer_value("lr", 1.0e-4)),
        ema=configured_ema,
        ema_decay=(
            None
            if not configured_ema
            else float(executable_optimizer_value("ema_decay", 0.99999))
        ),
        multiheads_finetuning=internal_multihead,
        force_mh_ft_lr=(
            executable_payload.get("force_mh_ft_lr")
            if internal_multihead
            else None
        ),
        real_pt_data_ratio_threshold=(
            executable_payload.get("real_pt_data_ratio_threshold")
            if internal_multihead
            else None
        ),
        target_train_count=int(target_train_art.configuration_count),
        replay_train_count=replay_count,
        batch_size=int(executable_optimizer_value("batch_size", 2)),
        target_updates_per_epoch=None,
        target_drop_last=None,
        distributed_allowed=True,
        target_frame_uid_set_digest=target_uid_digest,
        replay_frame_uid_set_digest=replay_uid_digest,
        target_head_name=(
            POST_SELECTION_TARGET_HEAD_NAME
            if internal_multihead
            else POST_SELECTION_SINGLE_HEAD_NAME
        ),
        replay_head_name=POST_SELECTION_REPLAY_HEAD_NAME,
        replay_identity_domain=(
            MACE_REPLAY_IDENTITY_DOMAIN_CANONICAL
            if internal_multihead and replay_geometry_identities is not None
            else (
                MACE_REPLAY_IDENTITY_DOMAIN_LEGACY
                if internal_multihead
                else None
            )
        ),
    )


def _terminate_post_selection_process(
    process: subprocess.Popen[Any], *, grace_seconds: float
) -> None:
    """Stop one detached wrapper/process group without leaving descendants."""

    if process.poll() is not None:
        return
    grace = max(0.1, float(grace_seconds))

    def send(signal_number: int) -> None:
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal_number)
            except ProcessLookupError:
                return
        else:  # pragma: no cover - Windows fallback
            if signal_number == signal.SIGKILL:
                process.kill()
            else:
                process.terminate()

    send(signal.SIGINT)
    try:
        process.wait(timeout=grace)
        return
    except subprocess.TimeoutExpired:
        pass
    send(signal.SIGTERM)
    try:
        process.wait(timeout=grace)
        return
    except subprocess.TimeoutExpired:
        pass
    send(signal.SIGKILL)
    process.wait()


def _bounded_process_output(stream: Any, *, limit: int = 64 * 1024) -> str:
    """Read only the diagnostic tail of one completed subprocess stream."""

    try:
        stream.flush()
        stream.seek(0, os.SEEK_END)
        size = int(stream.tell())
        stream.seek(max(0, size - int(limit)), os.SEEK_SET)
        raw = stream.read(int(limit))
    except (OSError, ValueError):
        return ""
    if isinstance(raw, bytes):
        return raw.decode("utf-8", errors="replace")
    return str(raw)


class _PostSelectionTrainingProgress:
    """Observe the existing MACE metrics stream for one supervised child."""

    def __init__(
        self,
        request: PostSelectionRungRequest,
        *,
        metric_path: Path,
        initial_summary: Any | None,
        summary_loader: Callable[[Path], Any],
    ) -> None:
        self.metric_path = metric_path
        self.summary_loader = summary_loader
        self._launch_completed_updates = max(
            0,
            int(getattr(initial_summary, "completed_updates", 0) or 0),
        )
        self.last_visible_monotonic: float | None = None
        self.started_monotonic = time.monotonic()
        self.metric_offset = (
            metric_path.stat().st_size if metric_path.is_file() else 0
        )
        self.metric_remainder = ""
        self.optimizer_updates_since_launch = 0
        try:
            self.optimizer_activity_timeout_seconds = float(
                getattr(request, "optimizer_activity_timeout_seconds", 120.0)
            )
        except (TypeError, ValueError) as exc:
            raise PostSelectionExecutionError(
                "Post-selection optimizer activity timeout is invalid."
            ) from exc
        if (
            self.optimizer_activity_timeout_seconds < 0.0
            or not math.isfinite(self.optimizer_activity_timeout_seconds)
        ):
            raise PostSelectionExecutionError(
                "Post-selection optimizer activity timeout must be finite and non-negative."
            )
        self.last_optimizer_update_monotonic: float | None = None
        self.last_loss: Any | None = None
        self.last_metric_epoch: int | None = None
        self.phase = "launching"
        self.execution_phase = "launching"
        self.summary = initial_summary
        self.summary_signature: tuple[int, int] | None = None
        self.completed_updates = self._launch_completed_updates
        planned = getattr(initial_summary, "planned_updates", None)
        self.planned_updates = (
            None if planned in (None, 0) else max(1, int(planned))
        )
        self.completed_epochs = max(
            0,
            int(getattr(initial_summary, "completed_epochs", 0) or 0),
        )
        self.planned_epochs = max(
            0,
            int(
                getattr(
                    getattr(request.plan, "budget_policy", None),
                    "planned_epochs",
                    0,
                )
                or 0
            ),
        )
        if self.planned_updates is None:
            structures = getattr(request.plan, "structures_per_epoch", None)
            # The post-selection runtime plan retains the target-side
            # structures-presented identity for compatibility.  MACE's
            # multihead loader, however, takes one combined target+replay
            # collection, so the launch-time progress projection must use that
            # authenticated loader count until the durable summary publishes
            # its exact ``len(train_loader)`` value.
            target_artifact = getattr(
                getattr(request.materialization, "target_train_artifact", None),
                "configuration_count",
                None,
            )
            replay_artifact = getattr(
                request.replay_train_artifact, "configuration_count", None
            )
            if target_artifact is not None:
                structures = int(target_artifact) + (
                    int(replay_artifact)
                    if bool(getattr(request.plan, "replay_monitor_enabled", False))
                    and replay_artifact is not None
                    else 0
                )
            batch_size = getattr(request.optimizer_policy, "batch_size", None)
            if (
                structures is not None
                and batch_size is not None
                and int(structures) > 0
                and int(batch_size) > 0
                and self.planned_epochs > 0
            ):
                # Current post-selection execution retains MACE's native
                # ``drop_last=True`` training-loader geometry. The target-size
                # owner has a separate authenticated ``drop_last=False``
                # rewrite, but this shared P5 trainer does not; use the same
                # floor update count that TRAIN2 will observe after MACE
                # constructs the real loader. The durable summary still
                # supersedes this launch-time projection when available.
                projected_updates = (
                    int(structures) // int(batch_size)
                    * self.planned_epochs
                )
                # A small fold can be below MACE's native full-batch
                # projection. Until TRAIN2 publishes the actual loader
                # geometry, retain an unknown horizon rather than exposing a
                # zero denominator that makes a live optimizer event look
                # invalid (and cannot satisfy the progress contract).
                if projected_updates > 0:
                    self.planned_updates = projected_updates
        self.last_learning_rate = getattr(
            initial_summary, "instantaneous_learning_rate", None
        )
        self.tracker = ProgressRateTracker(
            completed=self.completed_updates,
            started_at=self.started_monotonic,
        )

    def _read_metrics(self) -> None:
        if not self.metric_path.is_file():
            return
        try:
            size = int(self.metric_path.stat().st_size)
        except OSError:
            return
        if size < self.metric_offset:
            raise PostSelectionExecutionError(
                "MACE training metrics stream was truncated during execution."
            )
        if size == self.metric_offset:
            return
        with self.metric_path.open("rb") as stream:
            stream.seek(self.metric_offset)
            chunk = stream.read()
        self.metric_offset += len(chunk)
        text = self.metric_remainder + chunk.decode("utf-8", errors="replace")
        lines = text.splitlines(keepends=True)
        self.metric_remainder = ""
        if lines and not lines[-1].endswith(("\n", "\r")):
            self.metric_remainder = lines.pop()
        for line in lines:
            try:
                record = json.loads(line)
            except (TypeError, ValueError):
                continue
            if not isinstance(record, Mapping):
                continue
            mode = str(record.get("mode", ""))
            if mode == "opt":
                # MetricsLogger writes this record only after MACE's optimizer
                # step returns. Validation records never enter this numerator.
                self.optimizer_updates_since_launch += 1
                self.phase = "training"
                self.execution_phase = "training"
                self.last_optimizer_update_monotonic = time.monotonic()
            elif mode == "eval":
                self.phase = "validation"
                self.execution_phase = "validation"
            if "loss" in record:
                self.last_loss = record.get("loss")
            if record.get("epoch") is not None:
                try:
                    self.last_metric_epoch = int(record["epoch"])
                except (TypeError, ValueError):
                    pass

    def refresh(self, checkpoint_directory: Path) -> dict[str, Any]:
        summary_path = checkpoint_directory / "train2_runtime.json"
        if summary_path.is_file():
            try:
                stat = summary_path.stat()
                signature = (int(stat.st_size), int(stat.st_mtime_ns))
            except OSError:
                signature = None
            if signature is not None and signature != self.summary_signature:
                try:
                    self.summary = self.summary_loader(checkpoint_directory)
                except Exception:
                    # Atomic publication can briefly expose a partial file. The
                    # next control poll retries it; the child remains supervised.
                    pass
                else:
                    self.summary_signature = signature
        phase = getattr(self.summary, "phase", None)
        if phase and self.execution_phase == "launching":
            # A durable TRAIN2 phase may describe a learning-rate phase such
            # as ``adaptation``. Keep it visible until the first live MACE
            # record, but never treat that summary phase as optimizer-active
            # scheduler evidence.
            self.phase = str(phase)
            if str(phase) in {"training", "validation"}:
                self.execution_phase = str(phase)
        learning_rate = getattr(
            self.summary, "instantaneous_learning_rate", self.last_learning_rate
        )
        if learning_rate is not None:
            self.last_learning_rate = learning_rate
        # Read after the durable summary so a current validation metric remains
        # the visible phase during a long evaluation interval instead of being
        # overwritten by the summary's learning-rate phase.
        self._read_metrics()
        durable_updates = int(
            getattr(self.summary, "completed_updates", 0) or 0
        )
        self.completed_updates = max(
            durable_updates,
            self._launch_completed_updates + self.optimizer_updates_since_launch,
        )
        planned = getattr(self.summary, "planned_updates", None)
        if planned not in (None, 0):
            self.planned_updates = max(1, int(planned))
        epochs = getattr(self.summary, "completed_epochs", None)
        if epochs is not None:
            self.completed_epochs = max(self.completed_epochs, int(epochs))
        now = time.monotonic()
        last_update = self.last_optimizer_update_monotonic
        optimizer_active = (
            self.execution_phase == "training"
            and self.optimizer_updates_since_launch > 0
            and last_update is not None
            and 0.0 <= now - last_update <= self.optimizer_activity_timeout_seconds
        )
        return {
            "completed_updates": int(self.completed_updates),
            "planned_updates": self.planned_updates,
            "completed_epochs": int(self.completed_epochs),
            "planned_epochs": int(self.planned_epochs),
            "phase": self.phase,
            "true_epoch": bool(optimizer_active),
            "loss": self.last_loss,
            "learning_rate": self.last_learning_rate,
            "optimizer_updates_since_launch": int(
                self.optimizer_updates_since_launch
            ),
        }

    def emit(
        self,
        request: PostSelectionRungRequest,
        *,
        checkpoint_directory: Path,
        visible_interval_seconds: float,
        status: str,
        force: bool = False,
    ) -> dict[str, Any]:
        observation = self.refresh(checkpoint_directory)
        callback = request.progress_observer
        if callback is not None:
            callback({**observation, "status": status, "alive": status == "running"})
        now = time.monotonic()
        last_visible = getattr(self, "last_visible_monotonic", None)
        interval = max(0.05, float(visible_interval_seconds))
        should_emit = force or last_visible is None or now - last_visible >= interval
        if not should_emit:
            return observation
        self.last_visible_monotonic = now
        total = observation["planned_updates"]
        if total is None:
            progress = f"{observation['completed_updates']:,}/? (--.-%)"
            timing_total = max(1, int(observation["completed_updates"]) + 1)
        else:
            progress = format_progress_fraction(
                int(observation["completed_updates"]), int(total)
            )
            timing_total = int(total)
        snapshot = self.tracker.snapshot(
            completed=int(observation["completed_updates"]),
            total=timing_total,
            now=now,
        )
        eta = snapshot.eta_seconds if total is not None else None
        timing = format_progress_timing_fields(
            elapsed_seconds=snapshot.elapsed_seconds,
            eta_seconds=eta,
            recent_rate=snapshot.recent_rate,
            average_rate=snapshot.average_rate,
            rate_unit="gradient-update/s",
        )
        telemetry = None
        if isinstance(request.telemetry_ref, Mapping):
            telemetry = request.telemetry_ref.get("sample")
        if telemetry is None:
            gpu_fields = ("gpu=unavailable", "vram=unavailable")
        else:
            total_bytes = max(1, int(getattr(telemetry, "total_bytes", 0)))
            used_bytes = max(0, int(getattr(telemetry, "used_bytes", 0)))
            gpu_fields = (
                f"gpu={float(getattr(telemetry, 'utilization_percent', 0.0)):.0f}%",
                f"vram={used_bytes / 1024**3:.1f}/{total_bytes / 1024**3:.1f}GiB",
            )
        fields = [
            f"[TRAIN] status={status}",
            f"progress={progress}",
            "unit=gradient-update",
            f"phase={observation['phase']}",
            f"epoch={observation['completed_epochs']}/{observation['planned_epochs']}",
            timing,
            *gpu_fields,
        ]
        if observation["loss"] is not None:
            fields.append(f"loss={observation['loss']}")
        if observation["learning_rate"] is not None:
            fields.append(f"lr={observation['learning_rate']}")
        for key, value in (request.progress_context or {}).items():
            fields.append(f"{key}={value}")
        line = "; ".join(fields)
        if request.progress_callback is None:
            print(line, flush=True)
        else:
            request.progress_callback(line)
        return observation


@dataclass(frozen=True, slots=True)
class MacePostSelectionTrainer:
    """The production trainer: drives MACE through the accepted wrapper script."""

    wrapper_path: Path
    poll_interval_seconds: float = 1.0
    visible_progress_interval_seconds: float = 10.0
    minimum_free_disk_bytes: int | None = None
    timeout_seconds: float | None = None
    terminate_grace_seconds: float = 30.0

    def __call__(self, request: PostSelectionRungRequest) -> Any:
        import os
        import subprocess

        import yaml

        from ._common import sha256_file_cached
        from .precision_runtime import MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE
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
        configured_method_digest = internal_payload.get("method_identity_digest")
        runtime_method_digest = getattr(
            request.plan, "training_protocol_digest", None
        )
        if (
            configured_method_digest is not None
            and runtime_method_digest is not None
            and str(configured_method_digest) != str(runtime_method_digest)
        ):
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration method identity does not "
                "match the TRAIN2 runtime plan."
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
        internal_multihead = bool(internal_payload.get("multiheads_finetuning"))
        runtime_multihead = bool(
            getattr(request.plan, "replay_monitor_enabled", False)
        )
        if internal_multihead != runtime_multihead:
            raise PostSelectionExecutionError(
                "Post-selection MACE configuration and TRAIN2 runtime plan "
                "disagree about replay execution."
            )
        if internal_multihead:
            heads = internal_payload.get("heads")
            if not isinstance(heads, Mapping) or set(heads) != {
                POST_SELECTION_TARGET_HEAD_NAME,
                POST_SELECTION_REPLAY_HEAD_NAME,
            }:
                raise PostSelectionExecutionError(
                    "Post-selection multihead configuration must expose exactly "
                    "the canonical target_head and pt_head heads."
                )
            if request.replay_train_artifact is None or request.replay_train_path is None:
                raise PostSelectionExecutionError(
                    "Multihead post-selection configuration requires the "
                    "authenticated replay training request artifact and path."
                )
            if request.replay_monitor_artifact is None or request.replay_monitor_path is None:
                raise PostSelectionExecutionError(
                    "Multihead post-selection configuration requires the "
                    "authenticated TRUE_DFT monitor request artifact and path."
                )
        elif any(
            key in internal_payload
            for key in ("pt_train_file", "pt_valid_file", "heads")
        ) or any(
            value is not None
            for value in (
                request.replay_train_artifact,
                request.replay_train_path,
                request.replay_monitor_artifact,
                request.replay_monitor_path,
            )
        ):
            raise PostSelectionExecutionError(
                "Non-multihead post-selection configuration cannot carry replay "
                "training fields."
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

        # 4. Foundation checkpoint for non-scratch methods.  The executable
        # configuration and authenticated request must agree on whether this
        # method is foundation-backed; otherwise a scratch request could carry
        # an unclaimed foundation input that never entered its identity.
        internal_foundation_head = internal_payload.get("foundation_head")
        internal_has_foundation = bool(internal_foundation_head)
        request_has_foundation = (
            request.foundation_identity is not None
            or request.foundation_model_path is not None
        )
        if internal_has_foundation != request_has_foundation:
            raise PostSelectionExecutionError(
                "Post-selection foundation configuration and authenticated "
                "request disagree about foundation execution."
            )
        authenticated_foundation_path: Path | None = None
        if internal_has_foundation:
            if request.foundation_identity is None or request.foundation_model_path is None:
                raise PostSelectionExecutionError(
                    "Non-scratch training requires canonical foundation identity and path in request."
                )
            # 5. The locator is a runtime address, so it is re-authenticated
            # here rather than compared against a stored pathname: the bytes and
            # the selected head reached through the current locator are what the
            # frozen method actually bound.
            f_path = Path(request.foundation_model_path).resolve()
            if not f_path.is_file():
                raise PostSelectionExecutionError(
                    f"Foundation model file is missing: {f_path}"
                )
            if sha256_file_cached(f_path) != request.foundation_identity.sha256:
                raise PostSelectionExecutionError(
                    "Foundation model file SHA256 does not match canonical foundation identity."
                )
            if internal_foundation_head != request.foundation_identity.foundation_head:
                raise PostSelectionExecutionError(
                    "Internal config foundation_head does not match request foundation head."
                )
            authenticated_foundation_path = f_path

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

        if internal_multihead:
            def configured_path(name: str) -> Path:
                raw = internal_payload.get(name)
                if raw in (None, ""):
                    raise PostSelectionExecutionError(
                        f"Multihead post-selection configuration is missing {name}."
                    )
                path = Path(str(raw))
                if not path.is_absolute():
                    path = request.materialization_directory / path
                return path.resolve()

            if configured_path("pt_train_file") != Path(
                request.replay_train_path
            ).resolve():
                raise PostSelectionExecutionError(
                    "Executable pt_train_file does not match the authenticated "
                    "replay training request path."
                )
            if configured_path("pt_valid_file") != Path(
                request.replay_monitor_path
            ).resolve():
                raise PostSelectionExecutionError(
                    "Executable pt_valid_file does not match the authenticated "
                    "TRUE_DFT monitor request path."
                )

        # 9. Write executable configuration and execute wrapper subprocess
        executable_payload = post_selection_mace_run_configuration(
            internal_payload, foundation_model_path=authenticated_foundation_path
        )
        executable_config_path = (
            request.materialization_directory / "mace_run_config.yaml"
        )
        executable_config_path.write_text(
            yaml.safe_dump(executable_payload, sort_keys=False), encoding="utf-8"
        )

        # The wrapper receives a process-local authority derived only from the
        # authenticated materialization and runtime plan.  It is not a user
        # configuration escape hatch: the wrapper validates every field again
        # after MACE's own argument-mutation region and records the resolved
        # facts in the existing TRAIN2 summary.
        from .mace_compatibility import (
            MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
            mace_execution_authority_to_environment,
        )

        authority = _build_post_selection_mace_execution_authority(
            materialization=request.materialization,
            internal_payload=internal_payload,
            executable_payload=executable_payload,
            optimizer_policy=request.optimizer_policy,
            replay_train_artifact=request.replay_train_artifact,
            replay_geometry_identities=request.replay_geometry_identities,
            structures_per_epoch=getattr(request.plan, "structures_per_epoch", None),
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
        if int(request.start_epoch) > 0:
            command.append("--restart_latest")

        env = dict(os.environ)
        if int(request.start_epoch) > 0:
            env[MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE] = str(
                int(request.start_epoch) - 1
            )
        else:
            env.pop(MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE, None)
        env[MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE] = (
            mace_execution_authority_to_environment(authority)
        )
        env[TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE] = json.dumps(request.plan.to_dict())
        env["PYTHONHASHSEED"] = str(request.plan.optimizer_policy_digest[:8])
        if hasattr(request.optimizer_policy, "seed"):
            env["PYTHONHASHSEED"] = str(int(request.optimizer_policy.seed))
        if request.plan.replay_monitor_enabled and request.replay_monitor_path is not None:
            env[TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE] = str(
                Path(request.replay_monitor_path).resolve()
            )

        # MACE's MetricsLogger is the existing live-training observation
        # stream. Start at its current byte boundary so a restart's historical
        # lines cannot be counted twice; the authenticated TRAIN2 summary
        # supplies the durable predecessor numerator and exact denominator.
        seed_value = internal_payload.get(
            "seed", getattr(request.optimizer_policy, "seed", 0)
        )
        try:
            seed_text = str(int(seed_value))
        except (TypeError, ValueError):
            seed_text = str(seed_value)
        metric_path = run_root / "results" / (
            f"{internal_payload.get('name', 'post-selection')}_run-{seed_text}_train.txt"
        )
        initial_summary = None
        if (request.checkpoint_directory / "train2_runtime.json").is_file():
            try:
                initial_summary = load_train2_runtime_summary(
                    request.checkpoint_directory
                )
            except Exception:
                # Continuation authentication above remains authoritative. A
                # transient/legacy summary is simply not used for the first
                # heartbeat and is retried by the observer after launch.
                initial_summary = None
        progress = _PostSelectionTrainingProgress(
            request,
            metric_path=metric_path,
            initial_summary=initial_summary,
            summary_loader=load_train2_runtime_summary,
        )
        process: subprocess.Popen[Any] | None = None
        poll_interval = max(0.05, float(self.poll_interval_seconds))
        try:
            with tempfile.TemporaryFile(mode="w+b") as stdout_file, tempfile.TemporaryFile(
                mode="w+b"
            ) as stderr_file:
                process = subprocess.Popen(
                    command,
                    cwd=str(request.materialization_directory),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    start_new_session=(os.name == "posix"),
                )
                while True:
                    return_code = process.poll()
                    if return_code is None:
                        if (
                            request.cancellation_event is not None
                            and request.cancellation_event.is_set()
                        ):
                            _terminate_post_selection_process(
                                process,
                                grace_seconds=self.terminate_grace_seconds,
                            )
                            progress.emit(
                                request,
                                checkpoint_directory=request.checkpoint_directory,
                                visible_interval_seconds=self.visible_progress_interval_seconds,
                                status="cancelled",
                                force=True,
                            )
                            raise PostSelectionExecutionError(
                                "Post-selection MACE training was cancelled."
                            )
                        if self.minimum_free_disk_bytes is not None:
                            try:
                                free_bytes = int(shutil.disk_usage(run_root).free)
                            except OSError:
                                free_bytes = None
                            if (
                                free_bytes is not None
                                and free_bytes < int(self.minimum_free_disk_bytes)
                            ):
                                _terminate_post_selection_process(
                                    process,
                                    grace_seconds=self.terminate_grace_seconds,
                                )
                                progress.emit(
                                    request,
                                    checkpoint_directory=request.checkpoint_directory,
                                    visible_interval_seconds=self.visible_progress_interval_seconds,
                                    status="stopped-disk",
                                    force=True,
                                )
                                raise PostSelectionExecutionError(
                                    "Post-selection MACE training stopped because the "
                                    "configured free-disk reserve was reached."
                                )
                        if self.timeout_seconds is not None:
                            elapsed = time.monotonic() - progress.started_monotonic
                            if elapsed >= float(self.timeout_seconds):
                                _terminate_post_selection_process(
                                    process,
                                    grace_seconds=self.terminate_grace_seconds,
                                )
                                progress.emit(
                                    request,
                                    checkpoint_directory=request.checkpoint_directory,
                                    visible_interval_seconds=self.visible_progress_interval_seconds,
                                    status="stopped-timeout",
                                    force=True,
                                )
                                raise PostSelectionExecutionError(
                                    "Post-selection MACE training exceeded its configured timeout."
                                )
                    progress.emit(
                        request,
                        checkpoint_directory=request.checkpoint_directory,
                        visible_interval_seconds=self.visible_progress_interval_seconds,
                        status=(
                            "running"
                            if return_code is None
                            else ("completed" if return_code == 0 else "failed")
                        ),
                        force=return_code is not None,
                    )
                    if return_code is not None:
                        stdout_tail = _bounded_process_output(stdout_file)
                        stderr_tail = _bounded_process_output(stderr_file)
                        break
                    time.sleep(poll_interval)
        except BaseException:
            if process is not None and process.poll() is None:
                _terminate_post_selection_process(
                    process,
                    grace_seconds=self.terminate_grace_seconds,
                )
            raise
        if return_code != 0:
            raise PostSelectionExecutionError(
                f"Post-selection MACE training failed (exit {return_code}):\n"
                f"stdout:\n{stdout_tail}\n"
                f"stderr:\n{stderr_tail}"
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
) -> Any:
    """Construct the canonical foundation baseline prediction provider.

    Foundation replay baselines always use the deployable MACE provider.  Any
    bounded numerical substitution belongs below ``from_model_path`` in tests;
    this owner must retain its checkpoint, head, dtype, and inference-identity
    validation path.
    """

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
    "loss",
    "force_mh_ft_lr",
    "real_pt_data_ratio_threshold",
    "energy_weight",
    "forces_weight",
    "stress_weight",
    "batch_size",
    "valid_batch_size",
    "num_workers",
    "max_num_epochs",
    "ema",
    "ema_decay",
    "save_all_checkpoints",
    "amsgrad",
    "weight_decay",
    "clip_grad",
    "default_dtype",
    "device",
    "eval_interval",
    "enable_cueq",
    "only_cueq",
    "compute_avg_num_neighbors",
)


def post_selection_mace_run_configuration(
    config: Mapping[str, Any],
    *,
    foundation_model_path: str | Path | None = None,
) -> dict[str, Any]:
    """Project the frozen post-selection configuration into MACE arguments.

    Renaming, explicit architecture projection, and the pinned parser's
    scalar-literal spelling all happen here; the canonical configuration and its
    digests are untouched.

    ``foundation_model_path`` is the authenticated *current* runtime locator of
    the foundation checkpoint.  It is supplied per launch rather than stored,
    because the immutable configuration owns the checkpoint's scientific
    selection while the filesystem address it is reached through is not part of
    the method.
    """

    from .mace_compatibility import (
        encode_mace_executable_configuration,
        project_mace_architecture_arguments,
    )

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
    if foundation_model_path is not None:
        result["foundation_model"] = str(foundation_model_path)
    if config.get("foundation_head"):
        result["foundation_head"] = str(config["foundation_head"])
    multihead = bool(config.get("multiheads_finetuning"))
    replay_fields_present = any(
        key in config for key in ("pt_train_file", "pt_valid_file", "heads")
    )
    if not multihead and replay_fields_present:
        raise PostSelectionExecutionError(
            "Non-multihead post-selection MACE configuration cannot expose "
            "replay training files or heads."
        )
    if not multihead and any(
        key in config for key in ("force_mh_ft_lr", "real_pt_data_ratio_threshold")
    ):
        raise PostSelectionExecutionError(
            "Non-multihead post-selection MACE configuration cannot carry "
            "multihead replay controls."
        )
    # MACE 0.3.16's parser default is ``True``. Emit the ordinary single-head
    # value explicitly as well, otherwise a no-replay P5/final request is
    # silently promoted into multihead execution.
    result["multiheads_finetuning"] = multihead
    if config.get("compute_avg_num_neighbors", False) is not False:
        raise PostSelectionExecutionError(
            "Post-selection MACE execution must disable local average-neighbor recomputation."
        )
    result["compute_avg_num_neighbors"] = False
    if multihead:
        configured_force = config.get(
            "force_mh_ft_lr", POST_SELECTION_REPLAY_FORCE_MH_FT_LR
        )
        configured_threshold = config.get(
            "real_pt_data_ratio_threshold",
            POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD,
        )
        if configured_force is not POST_SELECTION_REPLAY_FORCE_MH_FT_LR:
            raise PostSelectionExecutionError(
                "Post-selection replay must explicitly force the authenticated "
                "MACE LR/EMA settings."
            )
        try:
            threshold_matches = (
                float(configured_threshold)
                == POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
            )
        except (TypeError, ValueError):
            threshold_matches = False
        if not threshold_matches:
            raise PostSelectionExecutionError(
                "Post-selection replay must explicitly disable MACE target duplication."
            )
        # Emit the controls even for legacy in-memory fixtures that predate the
        # repaired internal schema; the parser-facing bytes must never depend on
        # a MACE default.
        result["force_mh_ft_lr"] = POST_SELECTION_REPLAY_FORCE_MH_FT_LR
        result["real_pt_data_ratio_threshold"] = (
            POST_SELECTION_REPLAY_REAL_PT_DATA_RATIO_THRESHOLD
        )
        if not config.get("pt_train_file") or not config.get("pt_valid_file"):
            raise PostSelectionExecutionError(
                "Post-selection multihead configuration must expose both "
                "pt_train_file and pt_valid_file."
            )
        result["pt_train_file"] = config["pt_train_file"]
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
    for key, value in project_mace_architecture_arguments(
        config.get("mace_architecture")
    ).items():
        # The internal architecture head list is mdstats metadata and must never
        # become MACE's dataset-head argument; only the P5 multihead mapping can
        # set ``heads``.
        result.setdefault(key, value)
    try:
        return encode_mace_executable_configuration(result)
    except TrainingDataInputError as exc:
        raise PostSelectionExecutionError(
            f"Post-selection MACE configuration cannot be spelled for MACE: {exc}"
        ) from exc


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

    training_mode = str(getattr(method, "training_mode", "")).strip()
    if training_mode not in {
        "scratch",
        "naive_fine_tuning",
        "multihead_replay",
    }:
        raise PostSelectionExecutionError(
            f"Unsupported post-selection training mode: {training_mode!r}."
        )
    replay_enabled = training_mode == "multihead_replay"
    if bool(replay_monitor_enabled) != replay_enabled:
        raise PostSelectionExecutionError(
            "Post-selection method identity and TRAIN2 replay execution mode "
            "disagree."
        )

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
    execution_batch_width: int,
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
    # The evaluation population is scientific membership; the device batch is
    # not. Post-selection evaluation shares the bounded execution boundary with
    # target-size EVAL2 so the same oversized-batch failure cannot reappear on
    # a CV monitor, replay, or outer population.
    raw_predictions = run_bounded_inference(
        provider,
        atoms_list,
        batch_width=execution_batch_width,
        forward=inference_evaluator,
    )
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
    checkpoint_epoch: int | None = None,
    foundation_model_path: str | os.PathLike[str] | None = None,
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
    effective_summary = summary
    effective_companion_path: Path | None = checkpoint_root / "train2_runtime.pt"
    effective_checkpoint_epoch = checkpoint_epoch
    if effective_checkpoint_epoch is None:
        import re

        match = re.search(r"_epoch-(\d+)\.pt$", Path(checkpoint_name).name)
        if match is not None:
            effective_checkpoint_epoch = int(match.group(1))
    if effective_checkpoint_epoch is not None:
        from .train2_runtime import (
            load_train2_runtime_boundary_summary,
        )

        try:
            candidate_summary = load_train2_runtime_boundary_summary(
                checkpoint_root, effective_checkpoint_epoch
            )
        except TrainingDataInputError:
            latest_epoch = getattr(summary, "raw_checkpoint_epoch", None)
            if latest_epoch != effective_checkpoint_epoch:
                raise PostSelectionExecutionError(
                    "The selected TRAIN2 checkpoint has no authenticated per-epoch runtime boundary."
                )
        else:
            if candidate_summary.raw_checkpoint_sha256 != checkpoint_sha256:
                raise PostSelectionExecutionError(
                    "The selected TRAIN2 checkpoint disagrees with its per-epoch runtime boundary."
                )
            for field in (
                "plan_digest",
                "training_protocol_digest",
                "optimizer_policy_digest",
                "budget_policy_digest",
                "lr_policy_digest",
                "model_architecture_digest",
                "mace_execution_evidence",
            ):
                if getattr(candidate_summary, field, None) != getattr(summary, field, None):
                    raise PostSelectionExecutionError(
                        "The selected TRAIN2 boundary does not belong to the authenticated run authority."
                    )
            summary_epoch = getattr(summary, "raw_checkpoint_epoch", None)
            if isinstance(summary, Mapping) and summary_epoch is None:
                summary_epoch = summary.get("raw_checkpoint_epoch")
            if summary_epoch is None:
                raise PostSelectionExecutionError(
                    "The authenticated TRAIN2 run summary has no latest checkpoint epoch."
                )
            if int(effective_checkpoint_epoch) != int(summary_epoch):
                # The immutable boundary record and raw checkpoint are the
                # complete historical evaluation authority.  Do not retain or
                # consult a second full-model state archive for this path.
                # A bounded forward override may still need the latest-only
                # companion to construct its explicit synthetic provider shell
                # when a toy checkpoint has no native model state.  Native MACE
                # earlier-checkpoint authentication ignores this path and uses
                # the raw checkpoint plus its immutable boundary only.
                effective_companion_path = (
                    checkpoint_root / "train2_runtime.pt"
                    if allow_forward_override
                    else None
                )
    provider, evaluated_digest, _companion = authenticate_train2_checkpoint_provider(
        raw_checkpoint_path=checkpoint_root / checkpoint_name,
        raw_checkpoint_sha256=checkpoint_sha256,
        companion_path=effective_companion_path,
        companion_sha256=(
            None
            if effective_companion_path is None
            else _companion_sha256(effective_companion_path)
        ),
        summary=effective_summary,
        evaluation_model_state=evaluation_model_state,
        config_payload=config_payload,
        allow_forward_override=allow_forward_override,
        raw_checkpoint_epoch=effective_checkpoint_epoch,
        foundation_model_path=foundation_model_path,
    )
    return provider, evaluated_digest


def _companion_sha256(companion: Path) -> str:
    companion = Path(companion)
    if not companion.is_file():
        raise PostSelectionExecutionError(
            f"TRAIN2 continuation companion missing: {companion}."
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
