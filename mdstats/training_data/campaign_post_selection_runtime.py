"""The current post-selection orchestration: cross-validate, then produce.

This module owns the two public post-selection operations and nothing else.
Both begin the same way - re-establish the current P4 selection through the
canonical adapter - and both end the same way, by publishing an immutable
descendant under a commit-time currentness fence.  In between they are
deliberately asymmetric, because cross-validation and final production are
different roles over one shared method:

```text
current P4 SELECTED authority
 -> current selected-training context
 -> shared method identity
 -> CV policy identity
 -> CV plan from exact T_selected + complete P1 protected-relation projection
 -> fresh fold materialization / TRAIN2 / EVAL2 evidence
 -> exact all-required-fold target-only CV acceptance
 -> final-production policy identity
 -> final-production plan from full T_selected + accepted CV + M3 lineage
 -> fresh final materialization / TRAIN2 / EVAL2
 -> currentness-fenced publication
```

Expensive numerical work enters through two seams that sit strictly below every
owner under acceptance, so bounded tests exercise the real authorization,
lineage, restart, and publication behavior while substituting only MACE.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Deque, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
    load_current_selected_training_contexts,
    select_selected_training_context,
)
from .neutral_substrate.split_exclusion import (
    frame_split_exclusion_component_membership,
)
from .post_selection_cv_acceptance import (
    CvCampaignAcceptance,
    CvFoldAcceptance,
    accept_post_selection_cv_campaign,
    build_cv_fold_acceptance,
    require_cv_acceptance_for_method,
    select_cv_fold_representative,
)
from .post_selection_cv_plan import (
    PostSelectionCvPlan,
    build_cv_fold_run_plan,
    build_post_selection_cv_plan,
    build_selected_relation_projection,
    validate_post_selection_cv_plan,
)
from .post_selection_execution import (
    DATASET_ROLE_CHECKPOINT_MONITOR,
    DATASET_ROLE_OUTER_EVALUATION,
    MacePostSelectionTrainer,
    PostSelectionCancelledError,
    PostSelectionExecutionError,
    PostSelectionMaterialization,
    PostSelectionRunEvidence,
    PostSelectionRungRequest,
    _post_selection_mace_config,
    _build_post_selection_mace_execution_authority,
    _mace_execution_frame_uid_set_digest,
    authenticate_post_selection_provider,
    evaluate_post_selection_dataset,
    fit_post_selection_preparation,
    materialize_post_selection_run,
    post_selection_checkpoint_candidates,
    post_selection_runtime_plan,
)
from .bounded_inference import execution_batch_width
from .post_selection_identity import (
    CvValidationPolicyIdentity,
    FinalProductionPolicyIdentity,
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    PostSelectionMethodIdentity,
    compute_replay_lineage_digest,
    cv_training_budget_policy,
    final_production_training_budget_policy,
    resolve_cv_validation_policy_identity,
    resolve_final_production_policy_identity,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from .post_selection_production import (
    FinalProductionPlan,
    build_final_production_plan,
    build_final_production_run_plan,
    frozen_m3_development_evidence,
    validate_final_production_plan,
)
from .post_selection_publication import (
    FinalProductionPublicationDecision,
    publish_final_production_publication,
    resolve_current_final_production_publication,
)
from .post_selection_store import (
    POINTER_CV_ACCEPTANCE,
    POINTER_CV_PLAN,
    POINTER_FINAL_PLAN,
    open_post_selection_store,
    post_selection_publication_barrier,
    post_selection_root,
    publish_current_post_selection_pointer,
    read_current_post_selection_pointer,
    resolve_current_post_selection_record,
)


@dataclass(frozen=True, slots=True)
class PostSelectionContext:
    """One resolved post-selection invocation: authority plus resolved policy."""

    cfg: Mapping[str, Any]
    paths: Any
    store: Any
    selected: CurrentSelectedTrainingContext
    method: PostSelectionMethodIdentity
    method_policies: Any
    cv_policy: CvValidationPolicyIdentity
    production_policy: FinalProductionPolicyIdentity
    trainer: Any
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None
    # Qualification adds this execution-only value so exposure-time currentness
    # can reconstruct the same resource scope that created the P7 attempt.  It
    # is not a P5 scientific or selection identity.
    qualification_case_workers: int = 1
    _baseline_replay_cache: dict[str, float] = field(
        default_factory=dict, repr=False, compare=False
    )

    @property
    def evidence_store(self) -> Any:
        return open_post_selection_store(self.paths, self.selected.binding)

    def run_root(self, run_identity: str) -> Path:
        root = (
            post_selection_root(self.paths, self.selected.binding.campaign_generation)
            / "runs"
            / run_identity
        )
        root.mkdir(parents=True, exist_ok=True)
        return root


@dataclass(frozen=True, slots=True)
class PostSelectionReplayResolution:
    """Transport the two authenticated replay roles through P5 execution.

    ``train_*`` is the artifact consumed by the replay head and may carry
    foundation-pseudolabels.  ``monitor_*`` is always the independent TRUE_DFT
    admissibility monitor.  This adapter intentionally owns no persistence or
    scientific resolution; its values come from the canonical replay owners.
    """

    interface: str
    train_path: str
    monitor_path: str
    train_artifact: Any
    monitor_artifact: Any
    training_label_mode: Any
    true_label_mode: Any
    source_path: str | None = None
    source_content_digest: str | None = None
    source_sha256: str | None = None
    split_manifest_digest: str | None = None
    true_label_source_sha256: str | None = None
    # Process-local ordered transport from the existing single-source split
    # authority. It is not part of replay lineage or any scientific identity.
    replay_geometry_identities: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        from .replay import ReplayLabelMode

        if self.interface not in {"single_source", "legacy_split"}:
            raise PostSelectionError(
                f"Unsupported P5 replay interface: {self.interface!r}."
            )
        if not str(self.train_path).strip() or not str(self.monitor_path).strip():
            raise PostSelectionError(
                "P5 replay resolution requires both training and monitor paths."
            )
        if self.train_artifact is None or self.monitor_artifact is None:
            raise PostSelectionError(
                "P5 replay resolution requires both training and monitor artifacts."
            )
        try:
            training_mode = ReplayLabelMode(
                getattr(self.training_label_mode, "value", self.training_label_mode)
            )
            monitor_mode = ReplayLabelMode(
                getattr(self.true_label_mode, "value", self.true_label_mode)
            )
        except (TypeError, ValueError) as exc:
            raise PostSelectionError(
                "P5 replay resolution carries an unsupported label semantic."
            ) from exc
        if training_mode not in {
            ReplayLabelMode.TRUE_DFT,
            ReplayLabelMode.FOUNDATION_PSEUDOLABEL,
        }:
            raise PostSelectionError(
                "P5 replay training requires true_dft or foundation_pseudolabel."
            )
        if monitor_mode is not ReplayLabelMode.TRUE_DFT:
            raise PostSelectionError(
                "P5 replay admissibility requires an independent TRUE_DFT monitor."
            )
        for artifact, expected, role in (
            (self.train_artifact, training_mode, "training"),
            (self.monitor_artifact, ReplayLabelMode.TRUE_DFT, "monitor"),
        ):
            observed = getattr(artifact, "label_mode", None)
            if observed is None:
                continue
            try:
                observed = ReplayLabelMode(
                    getattr(observed, "value", observed)
                )
            except (TypeError, ValueError) as exc:
                raise PostSelectionError(
                    f"P5 replay {role} artifact has an unsupported label semantic."
                ) from exc
            if observed is not expected:
                raise PostSelectionError(
                    f"P5 replay {role} artifact label semantic does not match its "
                    "resolved role."
                )
        for path, artifact, role in (
            (self.train_path, self.train_artifact, "training"),
            (self.monitor_path, self.monitor_artifact, "monitor"),
        ):
            artifact_path = getattr(artifact, "path", None)
            if artifact_path is not None and Path(str(artifact_path)).resolve() != Path(path).resolve():
                raise PostSelectionError(
                    f"P5 replay {role} path does not match its authenticated artifact."
                )
        if self.true_label_source_sha256 is not None:
            try:
                object.__setattr__(
                    self,
                    "true_label_source_sha256",
                    validate_digest(
                        self.true_label_source_sha256,
                        name="true_label_source_sha256",
                    ),
                )
            except TrainingDataInputError as exc:
                raise PostSelectionError(
                    "P5 replay TRUE_DFT source identity is not a valid SHA256."
                ) from exc
        if self.replay_geometry_identities is not None:
            identities = tuple(str(value) for value in self.replay_geometry_identities)
            if len(identities) != int(
                getattr(self.train_artifact, "configuration_count", -1)
            ):
                raise PostSelectionError(
                    "P5 replay geometry transport does not match the training artifact count."
                )
            try:
                identities = tuple(
                    validate_digest(value, name="replay_geometry_identity")
                    for value in identities
                )
            except TrainingDataInputError as exc:
                raise PostSelectionError(
                    "P5 replay geometry transport contains an invalid identity."
                ) from exc
            if len(set(identities)) != len(identities):
                raise PostSelectionError(
                    "P5 replay geometry transport contains duplicate identities."
                )
            object.__setattr__(self, "replay_geometry_identities", identities)
        object.__setattr__(self, "train_path", str(self.train_path))
        object.__setattr__(self, "monitor_path", str(self.monitor_path))
        object.__setattr__(self, "training_label_mode", training_mode)
        object.__setattr__(self, "true_label_mode", monitor_mode.value)


def build_post_selection_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    trainer: Any = None,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
    qualification_case_workers: int = 1,
    admit: bool = False,
    n_selected: int | None = None,
) -> PostSelectionContext:
    """Resolve exactly one frozen size's post-selection invocation context.

    It is a selector over :func:`build_post_selection_contexts`, which does all
    the resolution.  ``n_selected`` may be omitted only when the frozen design
    has exactly one size; for a multi-size design there is no single "the"
    selected size and guessing one would silently reduce the requested
    experiment.
    """

    contexts = build_post_selection_contexts(
        cfg,
        paths,
        store,
        trainer=trainer,
        inference_evaluator=inference_evaluator,
        qualification_case_workers=qualification_case_workers,
        admit=admit,
    )
    selected = select_selected_training_context(
        tuple(item.selected for item in contexts), n_selected=n_selected
    )
    return next(
        item for item in contexts if item.selected.n_selected == selected.n_selected
    )


def build_post_selection_contexts(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    trainer: Any = None,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
    qualification_case_workers: int = 1,
    admit: bool = False,
) -> tuple[PostSelectionContext, ...]:
    """Resolve one ready invocation context per frozen size, in frozen order.

    This is the production-owned enumeration of the frozen design.  Every size
    resolves its three identities here, before any expensive work - which is
    exactly what makes them policy rather than evidence - and each reads *its
    own* frozen role horizons rather than whatever the config file says today,
    so an edit to ``campaign.toml`` after admission cannot rewrite an experiment
    that is already running.

    ``admit`` belongs to ``cross-validate`` alone: it is the freeze boundary that
    converts the operator's provisional design into immutable ancestry, and it
    admits the whole collection at once.  Every other caller requires a freeze
    that already happened.

    One shared trainer, one shared method-policy resolution and one shared
    prepared generation serve every size: adding sizes is one more post-selection
    experiment dimension, not one more campaign.
    """

    from ._campaign_cli_core import _cfg, _ensure_local_wrappers

    selected_contexts = load_current_selected_training_contexts(
        cfg, paths, store, admit=admit
    )
    resolved_trainer = trainer
    if resolved_trainer is None:
        visible_interval = max(
            0.05,
            float(
                _cfg(
                    cfg,
                    "execution",
                    "training_progress_interval_seconds",
                    10.0,
                )
            ),
        )
        timeout_value = float(
            _cfg(cfg, "execution", "timeout_seconds", 0.0) or 0.0
        )
        disk_reserve_gib = float(
            _cfg(cfg, "execution", "minimum_free_disk_gib", 20.0) or 0.0
        )
        resolved_trainer = MacePostSelectionTrainer(
            wrapper_path=_ensure_local_wrappers(paths)["mdstats-mace-train"],
            poll_interval_seconds=min(1.0, max(0.05, visible_interval / 4.0)),
            visible_progress_interval_seconds=visible_interval,
            minimum_free_disk_bytes=(
                None
                if disk_reserve_gib <= 0.0
                else int(disk_reserve_gib * 1024**3)
            ),
            timeout_seconds=(None if timeout_value <= 0.0 else timeout_value),
            terminate_grace_seconds=max(
                0.1,
                float(
                    _cfg(cfg, "execution", "terminate_grace_seconds", 30.0)
                ),
            ),
        )
    policies = resolve_post_selection_method_policies(cfg, config_dir=paths.config_dir)
    method = resolve_post_selection_method_identity(cfg, policies=policies)
    contexts = []
    for selected in selected_contexts:
        selected_method = method
        cv_max_num_epochs = None
        production_max_num_epochs = None
        if selected.frozen is not None:
            cv_max_num_epochs = selected.frozen.cv_max_num_epochs
            production_max_num_epochs = selected.frozen.production_max_num_epochs
        if selected.binding.is_legacy_schema:
            evidence_store = open_post_selection_store(
                paths, selected.binding, create=False
            )
            cv_plan_digest = read_current_post_selection_pointer(
                store, binding=selected.binding, kind=POINTER_CV_PLAN
            )
            if cv_plan_digest is not None and evidence_store.has(cv_plan_digest):
                plan = evidence_store.get(cv_plan_digest, PostSelectionCvPlan.from_dict)
                if evidence_store.has(plan.method_identity_digest):
                    selected_method = evidence_store.get(
                        plan.method_identity_digest,
                        PostSelectionMethodIdentity.from_dict,
                    )
        contexts.append(
            PostSelectionContext(
                cfg=cfg,
                paths=paths,
                store=store,
                selected=selected,
                method=selected_method,
                method_policies=policies,
                cv_policy=resolve_cv_validation_policy_identity(
                    cfg, max_num_epochs=cv_max_num_epochs
                ),
                production_policy=resolve_final_production_policy_identity(
                    cfg, max_num_epochs=production_max_num_epochs
                ),
                trainer=resolved_trainer,
                inference_evaluator=inference_evaluator,
                qualification_case_workers=max(1, int(qualification_case_workers)),
            )
        )
    return tuple(contexts)


def _component_block_ids(
    context: CurrentSelectedTrainingContext, frame_uids: Sequence[str]
) -> tuple[str, ...]:
    """Split-exclusion component identity per evaluated frame.

    EVAL2 block statistics must respect the same non-separability P1 owns, so
    the block identity is the canonical component identity rather than anything
    P5 invents.
    """

    authorities = context.authorities
    assignment = dict(
        frame_split_exclusion_component_membership(
            tuple(str(v) for v in frame_uids),
            authorities.split_exclusion,
            frame_authority_digest=authorities.frame_authority.content_digest,
            neutral_unit_catalog_digest=(
                authorities.neutral_base.unit_catalog.content_digest
            ),
        )
    )
    return tuple(assignment[str(uid)] for uid in frame_uids)


def _optimizer_policy_for(
    context: PostSelectionContext, *, seed: int, planned_epochs: int
) -> Any:
    from ._campaign_cli_core import _cfg, _optimizer_policy

    policy = _optimizer_policy(
        context.cfg,
        seed=int(seed),
        num_workers=int(_cfg(context.cfg, "training", "num_workers", 0)),
        paths=context.paths,
        planned_epochs=int(planned_epochs),
    )
    if hasattr(policy, "acceleration_policy") and policy.acceleration_policy is not None:
        if policy.acceleration_policy.backend.value != context.method.acceleration_backend:
            raise PostSelectionError(
                f"Optimizer acceleration backend '{policy.acceleration_policy.backend.value}' "
                f"does not match method acceleration backend '{context.method.acceleration_backend}'."
            )
    return policy


def resolve_post_selection_evaluation_model_state(
    context: PostSelectionContext, *, seed: int, planned_epochs: int
) -> str:
    """Resolve the checkpoint representation from the executed optimizer policy.

    Post-selection uses the same policy-derived convention as the target-size
    evaluator: EMA checkpoints are evaluated as EMA and EMA-free checkpoints
    are evaluated as live state.  This is deliberately derived at the
    authentication call site rather than stored as another method or checkpoint
    identity.
    """

    from .target_size_execution import target_size_evaluation_model_state

    return target_size_evaluation_model_state(
        _optimizer_policy_for(
            context,
            seed=int(seed),
            planned_epochs=int(planned_epochs),
        )
    )


def _resolve_post_selection_replay_resolution(
    context: PostSelectionContext, *, require_train: bool = True
) -> Any | None:
    if not hasattr(context, "paths") or context.paths is None:
        raise PostSelectionError(
            "Replay-enabled post-selection requires configured campaign paths."
        )
    from ._campaign_cli_core import (
        CampaignCliError,
        _build_replay_plan,
        _resolve_true_label_replay_inputs,
        _single_source_replay_context,
        _single_source_replay_config,
    )
    from .replay import ReplayLabelMode, ReplayMode

    # Post-selection is a scientific *read*.  The current single-source
    # interface is resolved through the authenticated published authority, which
    # cannot build foundation predictions, requalify under a changed policy, or
    # create a scientific split; a missing or stale scientific parent routes to
    # `prepare` instead of being rebuilt here.
    if _single_source_replay_config(context.cfg, context.paths) is not None:
        try:
            single_ctx = _single_source_replay_context(context.cfg, context.paths)
        except CampaignCliError as exc:
            raise PostSelectionError(
                f"Single-source replay authority is not current for post-selection: {exc}"
            ) from exc
        if single_ctx is None:
            raise PostSelectionError(
                "Single-source replay is configured but no prepared replay "
                "authority could be authenticated; run `prepare`."
            )
        try:
            return PostSelectionReplayResolution(**dict(single_ctx["resolution_fields"]))
        except KeyError as exc:
            raise PostSelectionError(
                "Prepared single-source replay did not provide a complete "
                f"post-selection resolution: {exc}."
            ) from exc

    # Legacy split replay has one canonical training plan and a separate true
    # label resolver.  In particular, asking the latter for a TRUE_DFT train
    # file must never replace a configured pseudolabel training artifact.
    plan = _build_replay_plan(context.cfg, context.paths)
    if plan is None or plan.mode is ReplayMode.NONE:
        return None
    if plan.mode not in {
        ReplayMode.EXTERNAL_PSEUDOLABEL,
        ReplayMode.EXTERNAL_TRUE_LABEL,
    }:
        raise PostSelectionError(
            "Legacy replay mode does not provide an unambiguous supported P5 "
            "training artifact."
        )
    training_artifact = getattr(plan, "train_artifact", None)
    if training_artifact is None:
        raise PostSelectionError(
            "Legacy replay did not produce a canonical training artifact."
        )
    training_path = getattr(training_artifact, "path", None)
    if training_path is None:
        raise PostSelectionError(
            "Legacy replay training artifact does not identify its source file."
        )

    expected_training_mode = (
        ReplayLabelMode.FOUNDATION_PSEUDOLABEL
        if plan.mode is ReplayMode.EXTERNAL_PSEUDOLABEL
        else ReplayLabelMode.TRUE_DFT
    )
    observed_training_mode = getattr(
        training_artifact, "label_mode", expected_training_mode
    )
    try:
        observed_training_mode = ReplayLabelMode(
            getattr(observed_training_mode, "value", observed_training_mode)
        )
    except (TypeError, ValueError) as exc:
        raise PostSelectionError(
            "Legacy replay training artifact carries an unsupported label semantic."
        ) from exc
    if observed_training_mode is not expected_training_mode:
        raise PostSelectionError(
            "Legacy replay training artifact label semantics do not match the "
            "configured replay mode."
        )

    if plan.mode is ReplayMode.EXTERNAL_PSEUDOLABEL:
        true_resolution = _resolve_true_label_replay_inputs(
            context.cfg, context.paths, require_train=False
        )
        if true_resolution is None:
            raise PostSelectionError(
                "Legacy pseudolabel replay requires an independent TRUE_DFT "
                "replay monitor/source."
            )
    else:
        true_resolution = _resolve_true_label_replay_inputs(
            context.cfg, context.paths, require_train=require_train
        )

    if true_resolution is not None:
        monitor_artifact = true_resolution.monitor_artifact
        monitor_path = true_resolution.monitor_path
        source_path = true_resolution.source_path
    else:
        # A legacy external_true_label campaign may declare already-authenticated
        # TRUE_DFT split files without a separate replay_true_labels root.  The
        # plan's monitor is then both the configured training-plan monitor and
        # the independently authenticated TRUE_DFT monitor role.
        monitor_artifact = getattr(plan, "monitor_artifact", None)
        monitor_path = None if monitor_artifact is None else monitor_artifact.path
        source_path = getattr(plan, "source_replay_path", None)
    if monitor_artifact is None or monitor_path is None:
        raise PostSelectionError(
            "Legacy replay did not produce an independent TRUE_DFT monitor artifact."
        )
    true_label_source_sha256 = None
    if source_path is not None:
        source_file = Path(source_path).expanduser().resolve()
        if not source_file.is_file():
            raise PostSelectionError(
                "Legacy replay TRUE_DFT source identity is missing from disk."
            )
        true_label_source_sha256 = sha256_file_cached(source_file)
    return PostSelectionReplayResolution(
        interface="legacy_split",
        train_path=str(training_path),
        monitor_path=str(monitor_path),
        train_artifact=training_artifact,
        monitor_artifact=monitor_artifact,
        training_label_mode=expected_training_mode,
        true_label_mode=getattr(monitor_artifact, "label_mode", None),
        source_path=None if source_path is None else str(source_path),
        true_label_source_sha256=true_label_source_sha256,
    )


def _retire_post_selection_provider(provider: Any) -> None:
    """Release one evaluation provider through its existing lifecycle owner."""

    if provider is not None and hasattr(provider, "close"):
        provider.close()


def evaluate_post_selection_run_candidates(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    runtime_plan: Any,
    materialization: Any,
    material_directory: Path,
    checkpoint_directory: Path,
    summary: Any,
    monitor_frame_uids: Sequence[str],
    replay_resolution: Any,
) -> tuple[Any, Any, Any]:
    """Evaluate the run's checkpoint candidates and freeze its representative.

    This is the one implementation of "which checkpoint does this run publish,
    and what were its exact M3 target metrics".  It is used both while a run
    executes and when an already completed run's durable representative records
    have to be recovered, so recovery re-evaluates through the real EVAL2 owner
    instead of reconstructing evidence from stored digests.
    """

    from .eval2 import assess_eval2_checkpoint

    selected = context.selected
    admissibility = context.method_policies.checkpoint_admissibility
    extxyz_policy = context.method_policies.extxyz
    optimizer_policy = _optimizer_policy_for(
        context,
        seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
    )
    batch_width = execution_batch_width(optimizer_policy)
    from .target_size_execution import target_size_evaluation_model_state

    evaluation_model_state = target_size_evaluation_model_state(optimizer_policy)

    candidates = post_selection_checkpoint_candidates(
        run_plan=run_plan,
        checkpoint_directory=checkpoint_directory,
        runtime_plan=runtime_plan,
    )
    catalog = _checkpoint_catalog(run_plan, checkpoint_directory)
    monitor_blocks = _component_block_ids(selected, monitor_frame_uids)
    selection_policy = context.method_policies.checkpoint_selection
    records = []
    monitor_metrics_by_identity: dict[str, Any] = {}
    for point in candidates:
        checkpoint = catalog.checkpoint_by_sha256(point.checkpoint_sha256)
        provider, _evaluated = authenticate_post_selection_provider(
            materialization=materialization,
            materialization_directory=material_directory,
            checkpoint_directory=checkpoint_directory,
            checkpoint_name=Path(checkpoint.relative_path).name,
            checkpoint_sha256=checkpoint.sha256,
            checkpoint_epoch=getattr(checkpoint, "epoch", None),
            summary=summary,
            evaluation_model_state=evaluation_model_state,
            allow_forward_override=context.inference_evaluator is not None,
            foundation_model_path=context.method_policies.foundation_model,
        )
        replay_candidate_rmse = None
        replay_foundation_rmse = None
        replay_label_mode = None
        try:
            metrics = evaluate_post_selection_dataset(
                run_plan=run_plan,
                artifact=materialization.checkpoint_monitor_artifact,
                dataset_role=DATASET_ROLE_CHECKPOINT_MONITOR,
                root_directory=material_directory,
                provider=provider,
                block_ids=monitor_blocks,
                execution_batch_width=batch_width,
                extxyz_policy=extxyz_policy,
                inference_evaluator=context.inference_evaluator,
            )
            if admissibility.replay_enabled:
                if (
                    replay_resolution is None
                    or replay_resolution.monitor_artifact is None
                ):
                    raise PostSelectionError(
                        "Missing required TRUE_DFT replay monitor artifact."
                    )
                replay_monitor_artifact = replay_resolution.monitor_artifact
                replay_monitor_path = Path(replay_resolution.monitor_path)
                if not replay_monitor_path.is_file():
                    raise PostSelectionError(
                        f"TRUE_DFT replay monitor file is missing: {replay_monitor_path}"
                    )
                if (
                    sha256_file_cached(replay_monitor_path)
                    != replay_monitor_artifact.sha256
                ):
                    raise PostSelectionError(
                        "TRUE_DFT replay monitor file bytes changed on disk."
                    )

                replay_blocks = tuple(
                    f"replay_block_{i}"
                    for i in range(replay_monitor_artifact.configuration_count)
                )
                candidate_replay_metrics = evaluate_post_selection_dataset(
                    run_plan=run_plan,
                    artifact=replay_monitor_artifact,
                    dataset_role="replay_monitor",
                    root_directory=replay_monitor_path.parent,
                    provider=provider,
                    block_ids=replay_blocks,
                    execution_batch_width=batch_width,
                    extxyz_policy=extxyz_policy,
                    inference_evaluator=context.inference_evaluator,
                )
                replay_candidate_rmse = (
                    candidate_replay_metrics.force_component_rmse_ev_per_angstrom
                )
        finally:
            _retire_post_selection_provider(provider)

        if admissibility.replay_enabled:
            foundation_identity = (
                context.method_policies.foundation_potential_identity
            )
            foundation_model = context.method_policies.foundation_model
            foundation_head = context.method_policies.foundation_head
            if foundation_model is None:
                raise PostSelectionExecutionError(
                    "Replay admissibility evaluation requires a configured foundation model."
                )

            if foundation_identity is None:
                # A foundation-backed replay evaluation without authenticated
                # foundation identity has nothing scientific to key its baseline
                # on.  Substituting the runtime locator would reintroduce
                # location into what is content/head identity.
                raise PostSelectionExecutionError(
                    "Replay admissibility evaluation requires canonical "
                    "foundation identity."
                )
            foundation_content_digest = foundation_identity.canonical_content_digest
            cache_key = digest(
                {
                    "foundation_content_digest": foundation_content_digest,
                    "foundation_head": foundation_head,
                    "monitor_sha256": replay_monitor_artifact.sha256,
                    "monitor_digest": (
                        getattr(replay_monitor_artifact, "content_digest", None)
                        or getattr(
                            replay_monitor_artifact, "logical_digest", None
                        )
                    ),
                    "eval2_metric_policy_digest": (
                        context.method_policies.common_training.eval2_metric_policy_digest
                    ),
                    "default_dtype": (
                        context.method_policies.default_dtype
                    ),
                    "device": context.method_policies.device,
                }
            )
            if cache_key in context._baseline_replay_cache:
                replay_foundation_rmse = context._baseline_replay_cache[
                    cache_key
                ]
            else:
                from .post_selection_execution import (
                    build_post_selection_foundation_baseline_provider,
                )

                baseline_provider = build_post_selection_foundation_baseline_provider(
                    foundation_path=foundation_model,
                    foundation_identity=foundation_identity,
                    foundation_head=foundation_head,
                    device=context.method_policies.device,
                    default_dtype=context.method_policies.default_dtype,
                )
                try:
                    baseline_replay_metrics = evaluate_post_selection_dataset(
                        run_plan=run_plan,
                        artifact=replay_monitor_artifact,
                        dataset_role="replay_monitor_baseline",
                        root_directory=replay_monitor_path.parent,
                        provider=baseline_provider,
                        block_ids=replay_blocks,
                        execution_batch_width=batch_width,
                        extxyz_policy=extxyz_policy,
                        inference_evaluator=context.inference_evaluator,
                    )
                finally:
                    _retire_post_selection_provider(baseline_provider)
                replay_foundation_rmse = (
                    baseline_replay_metrics.force_component_rmse_ev_per_angstrom
                )
                context._baseline_replay_cache[cache_key] = (
                    replay_foundation_rmse
                )
            replay_label_mode = "true_dft"

        record = assess_eval2_checkpoint(
            point,
            evaluation_record_digest=metrics.content_digest,
            target_metrics=metrics,
            admissibility_policy=admissibility,
            replay_candidate_force_rmse_ev_per_angstrom=replay_candidate_rmse,
            replay_foundation_force_rmse_ev_per_angstrom=replay_foundation_rmse,
            replay_label_mode=replay_label_mode,
        )
        records.append(record)
        monitor_metrics_by_identity[record.stable_candidate_identity] = metrics

    representative = select_cv_fold_representative(
        records,
        selection_policy=selection_policy,
        seed_material_digest=run_plan.content_digest,
    )
    monitor_metrics = monitor_metrics_by_identity[
        representative.stable_candidate_identity
    ]

    return catalog, representative, monitor_metrics


def execute_post_selection_run(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    progress_context: Mapping[str, Any] | None = None,
    cancellation_event: Any | None = None,
    progress_callback: Callable[[str], None] | None = None,
    progress_observer: Callable[[Mapping[str, Any]], None] | None = None,
    telemetry_ref: Any | None = None,
    stop_after_training: bool = False,
) -> tuple[PostSelectionRunEvidence, Any, Any] | None:
    """Run one post-selection job end to end and return its bound evidence.

    Order matters and is enforced by construction: the representative is frozen
    from the run's own monitor before the held-out outer data is evaluated at
    all, so outer evidence cannot influence the checkpoint it judges.

    ``stop_after_training`` ends the call at the authenticated TRAIN2 summary
    and returns ``None``. That summary and its materialization are already
    durable, so a later call with the same arguments resumes through the
    existing continuation path and performs EVAL2 without retraining. The TRAIN
    scheduler uses this so one training slot owns TRAIN2 accelerator lifetime
    only and never carries post-TRAIN EVAL2 work.
    """

    run_root = context.run_root(run_plan.run_identity)
    with post_selection_run_activity_lease(run_root):
        return _execute_post_selection_run_locked(
            context,
            run_plan=run_plan,
            budget_policy=budget_policy,
            training_frame_uids=training_frame_uids,
            monitor_frame_uids=monitor_frame_uids,
            outer_evaluation_frame_uids=outer_evaluation_frame_uids,
            run_root=run_root,
            progress_context=progress_context,
            cancellation_event=cancellation_event,
            progress_callback=progress_callback,
            progress_observer=progress_observer,
            telemetry_ref=telemetry_ref,
            stop_after_training=stop_after_training,
        )


_POST_SELECTION_MATERIALIZATION_FILES = frozenset(
    {
        "materialization.json",
        "post_selection_mace_config.yaml",
        "mace_run_config.yaml",
        "target_train.extxyz",
        "target_train.extxyz.manifest.json",
        "checkpoint_monitor.extxyz",
        "checkpoint_monitor.extxyz.manifest.json",
        "outer_evaluation.extxyz",
        "outer_evaluation.extxyz.manifest.json",
    }
)

# These paths are disposable run-owned scratch only.  They are deliberately
# deterministic so a retry can reclaim a directory left behind by an
# interrupted recursive delete, but they never participate in any P5 identity
# or completion decision.
_POST_SELECTION_RETIREMENT_PREFIX = ".tmp_p5_retirement_"
_POST_SELECTION_RETIREMENT_NAMES = ("checkpoints", "materialization")


def _post_selection_retirement_path(run_root: Path, canonical_name: str) -> Path:
    """Return the bounded scratch path for one detached canonical namespace."""

    if canonical_name not in _POST_SELECTION_RETIREMENT_NAMES:
        raise ValueError(f"Unsupported P5 retirement namespace: {canonical_name!r}.")
    return run_root / f"{_POST_SELECTION_RETIREMENT_PREFIX}{canonical_name}"


def _post_selection_directory_or_absent(path: Path, *, label: str) -> bool:
    """Validate one retirement path without following links.

    A canonical recovery namespace or its detached scratch must be a plain
    directory.  In particular, a symlink at either name is never allowed to
    turn a run-owned cleanup into deletion outside the run root.
    """

    try:
        mode = os.lstat(path).st_mode
    except FileNotFoundError:
        return False
    except OSError as exc:
        _post_selection_recovery_error(
            f"Could not inspect P5 {label} path; preserving it.", exc
        )
    if stat.S_ISLNK(mode):
        _post_selection_recovery_error(
            f"P5 {label} path is a symlink; preserving it."
        )
    if not stat.S_ISDIR(mode):
        _post_selection_recovery_error(
            f"P5 {label} path is not a regular directory; preserving it."
        )
    return True


def _reclaim_post_selection_retirement_scratch(
    run_root: Path, canonical_directory: Path, *, canonical_name: str
) -> None:
    """Reclaim one already-detached scratch namespace, if present.

    A scratch destination is only recognized as a retry residue when the live
    canonical namespace is absent.  If both names exist, the destination is
    unknown and this owner preserves both rather than replacing or deleting it.
    """

    scratch = _post_selection_retirement_path(run_root, canonical_name)
    canonical_present = _post_selection_directory_or_absent(
        canonical_directory, label=canonical_name
    )
    scratch_present = _post_selection_directory_or_absent(
        scratch, label=f"{canonical_name} retirement scratch"
    )
    if not scratch_present:
        return
    if canonical_present:
        _post_selection_recovery_error(
            f"P5 {canonical_name} retirement scratch exists while its canonical "
            "namespace is still present; preserving both paths."
        )
    # The canonical name was detached before this scratch could exist.  A
    # recursive failure therefore leaves only disposable scratch behind and
    # cannot manufacture a partial continuation/materialization namespace.
    shutil.rmtree(scratch)


def _detach_post_selection_namespace(
    run_root: Path, canonical_directory: Path, *, canonical_name: str
) -> None:
    """Atomically detach one authenticated namespace, then reclaim its scratch.

    The caller holds the run activity lease and has already completed the full
    recovery authentication/classification.  ``os.rename`` is intentionally
    used rather than ``os.replace``: an existing destination is an integrity
    conflict, never something this owner may overwrite.  Supported P5 writers
    are serialized by the lease, so the preflight and rename form one owner
    transition; an external replacement is still detected on the next
    authentication boundary.
    """

    scratch = _post_selection_retirement_path(run_root, canonical_name)
    canonical_present = _post_selection_directory_or_absent(
        canonical_directory, label=canonical_name
    )
    if _post_selection_directory_or_absent(
        scratch, label=f"{canonical_name} retirement scratch"
    ):
        # A previous invocation detached this namespace and was interrupted
        # during or after reclaim.  Finish only that disposable cleanup before
        # considering the next canonical transition.
        _reclaim_post_selection_retirement_scratch(
            run_root, canonical_directory, canonical_name=canonical_name
        )
    if not canonical_present:
        return

    # The destination was checked absent above and all supported writers hold
    # the same run lease.  Directory rename is the namespace commit point seen
    # by the next invocation; recursive reclaim happens only after it.
    os.rename(canonical_directory, scratch)
    from .target_size_execution import fsync_parent_directory

    fsync_parent_directory(canonical_directory)
    _reclaim_post_selection_retirement_scratch(
        run_root, canonical_directory, canonical_name=canonical_name
    )


def _post_selection_recovery_error(
    message: str, cause: Exception | None = None
) -> None:
    """Raise the typed P5 error used for preserved recovery conflicts."""

    if cause is None:
        raise PostSelectionExecutionError(message)
    raise PostSelectionExecutionError(message) from cause


def _safe_materialization_relative_path(
    root: Path, value: str, *, name: str
) -> Path:
    """Return one in-root materialization path without following an input link."""

    relative = Path(str(value))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        _post_selection_recovery_error(
            f"{name} must be a relative path inside the P5 materialization."
        )
    candidate = root / relative
    resolved_root = root.resolve()
    resolved = candidate.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        _post_selection_recovery_error(
            f"{name} resolves outside the P5 materialization: {value!r}."
        )
    return relative


def _materialization_allowed_nodes(
    root: Path, record: PostSelectionMaterialization | None
) -> frozenset[str]:
    """Return the exact local names current P5 publication can leave behind."""

    names = set(_POST_SELECTION_MATERIALIZATION_FILES)
    if record is not None:
        for artifact_name, artifact in (
            ("target training artifact", record.target_train_artifact),
            ("checkpoint-monitor artifact", record.checkpoint_monitor_artifact),
            ("outer-evaluation artifact", record.outer_evaluation_artifact),
        ):
            if artifact is None:
                continue
            for field in ("relative_path", "sidecar_relative_path"):
                relative = _safe_materialization_relative_path(
                    root,
                    getattr(artifact, field),
                    name=f"{artifact_name} {field}",
                )
                names.add(relative.as_posix())
        relative = _safe_materialization_relative_path(
            root,
            record.mace_config_relative_path,
            name="MACE configuration path",
        )
        names.add(relative.as_posix())
    lock_names = {
        f".{Path(name).name}.lock" for name in names if "/" not in name
    }
    return frozenset(names | lock_names)


def _assert_owned_materialization_tree(
    material_directory: Path,
    *,
    record: PostSelectionMaterialization | None,
) -> None:
    """Reject links/foreign descendants before any run-owned cleanup."""

    if material_directory.is_symlink():
        _post_selection_recovery_error(
            "P5 materialization is a symlink; refusing to classify or remove it."
        )
    if not material_directory.is_dir():
        _post_selection_recovery_error(
            f"P5 materialization path is not a directory: {material_directory}."
        )
    allowed = _materialization_allowed_nodes(material_directory, record)
    for node in material_directory.rglob("*"):
        if node.is_symlink():
            _post_selection_recovery_error(
                f"P5 materialization contains a symlinked node; preserving it: {node}."
            )
        if not node.is_file() and not node.is_dir():
            _post_selection_recovery_error(
                f"P5 materialization contains a non-regular node; preserving it: {node}."
            )
        relative = node.relative_to(material_directory)
        if len(relative.parts) != 1:
            _post_selection_recovery_error(
                "P5 materialization contains an unexpected nested descendant; "
                f"preserving it: {node}."
            )
        name = relative.as_posix()
        if name not in allowed and not name.startswith(".tmp_"):
            _post_selection_recovery_error(
                "P5 materialization contains a descendant this owner did not "
                f"publish; preserving it: {node}."
            )


def _checkpoint_has_durable_entries(checkpoint_directory: Path) -> bool:
    """Ignore only publication-temp/lock residue when probing continuation."""

    for node in checkpoint_directory.iterdir():
        if node.is_symlink():
            _post_selection_recovery_error(
                "TRAIN2 checkpoint directory contains a symlink; preserving it."
            )
        if node.name.startswith(".tmp_") or node.name.endswith(".lock"):
            continue
        return True
    return False


def _authenticate_post_selection_continuation(
    checkpoint_directory: Path,
    *,
    runtime_plan: Any,
) -> tuple[Any | None, int]:
    """Authenticate TRAIN2 state; never infer resumability from a filename."""

    if checkpoint_directory.is_symlink():
        _post_selection_recovery_error(
            "TRAIN2 checkpoint state is a symlink; preserving diagnostic state."
        )
    if not checkpoint_directory.exists():
        return None, 0
    if not checkpoint_directory.is_dir():
        _post_selection_recovery_error(
            "TRAIN2 checkpoint state is not a regular run-owned directory; "
            "preserving it."
        )
    if not _checkpoint_has_durable_entries(checkpoint_directory):
        return None, 0

    from .train2_runtime import validate_train2_runtime_continuation_artifacts

    try:
        summary = validate_train2_runtime_continuation_artifacts(
            checkpoint_directory,
            training_protocol_digest=runtime_plan.training_protocol_digest,
            optimizer_policy_digest=runtime_plan.optimizer_policy_digest,
            budget_policy=runtime_plan.budget_policy,
            learning_rate_policy=runtime_plan.learning_rate_policy,
            structures_per_epoch=runtime_plan.structures_per_epoch,
        )
        # The shared validator permits a different execution limit for target-
        # size boundary reuse. P5 has no rung pause, so bind the result to this
        # exact runtime plan before handing it to the trainer.
        if summary.plan_digest != runtime_plan.content_digest:
            raise TrainingDataInputError(
                "TRAIN2 continuation summary belongs to a different P5 runtime plan."
            )
        if summary.execution_epoch_limit != runtime_plan.execution_epoch_limit:
            raise TrainingDataInputError(
                "TRAIN2 continuation summary belongs to a different P5 execution limit."
            )
    except Exception as exc:
        _post_selection_recovery_error(
            "TRAIN2 checkpoint files exist but do not authenticate as the current "
            "P5 continuation; preserving diagnostic state.",
            exc,
        )
    return summary, int(summary.completed_epochs)


def _validate_post_selection_continuation_execution_evidence(
    context: PostSelectionContext,
    *,
    materialization: PostSelectionMaterialization,
    config_payload: Mapping[str, Any],
    continuation_summary: Any,
    replay_resolution: Any | None,
    optimizer_policy: Any,
) -> None:
    """Bind persisted MACE execution facts to the current materialization.

    TRAIN2 authenticates its own continuation shape and tensor state.  The P5
    materialization is the owner of the exact DATA8 workload, however, so a
    continuation is not reusable until the existing MACE evidence also names
    this materialization's configuration and training membership.  This is an
    owner-local compatibility check, not another restart record or identity.
    """

    from .mace_compatibility import (
        MACE_EXECUTION_EVIDENCE_SCHEMA,
        MACE_EXECUTION_SEMANTICS_VERSION,
        record_mace_execution_evidence,
    )

    evidence = getattr(continuation_summary, "mace_execution_evidence", None)
    if not isinstance(evidence, Mapping):
        _post_selection_recovery_error(
            "TRAIN2 continuation has no persisted MACE execution evidence bound "
            "to the current P5 materialization; preserving diagnostic state."
        )
    evidence = dict(evidence)
    if evidence.get("schema") != MACE_EXECUTION_EVIDENCE_SCHEMA:
        _post_selection_recovery_error(
            "TRAIN2 continuation carries an unsupported MACE execution-evidence "
            "schema; preserving diagnostic state."
        )
    if evidence.get("execution_semantics_version") != MACE_EXECUTION_SEMANTICS_VERSION:
        _post_selection_recovery_error(
            "TRAIN2 continuation carries an unsupported MACE execution-semantics "
            "revision; preserving diagnostic state."
        )
    if evidence.get("role") != "post_selection":
        _post_selection_recovery_error(
            "TRAIN2 continuation MACE execution evidence is not for post-selection; "
            "preserving diagnostic state."
        )
    evidence_digest = evidence.get("evidence_digest")
    if evidence_digest is None or str(evidence_digest) != digest(
        {key: value for key, value in evidence.items() if key != "evidence_digest"}
    ):
        _post_selection_recovery_error(
            "TRAIN2 continuation MACE execution evidence content is inconsistent; "
            "preserving diagnostic state."
        )

    target_artifact = materialization.target_train_artifact
    multihead = bool(config_payload.get("multiheads_finetuning", False))
    replay_artifact = None
    if replay_resolution is not None:
        replay_artifact = getattr(replay_resolution, "train_artifact", None)

    expected_config_digest = materialization.mace_config_digest
    if evidence.get("authority_config_digest") != expected_config_digest:
        _post_selection_recovery_error(
            "TRAIN2 continuation MACE authority does not match the current P5 "
            "materialization configuration; preserving diagnostic state."
        )

    try:
        target_uid_digest = _mace_execution_frame_uid_set_digest(
            target_artifact,
            role="target",
        )
        if target_uid_digest is None:
            raise TrainingDataInputError(
                "P5 materialization target training artifact has no frame-UID authority."
            )
        replay_uid_digest = None
        if multihead:
            if replay_artifact is None:
                raise TrainingDataInputError(
                    "P5 replay materialization has no authenticated training input."
                )
            replay_geometry_identities = getattr(
                replay_resolution, "replay_geometry_identities", None
            )
            if replay_geometry_identities is None:
                replay_uid_digest = _mace_execution_frame_uid_set_digest(
                    replay_artifact,
                    role="replay",
                )
            else:
                from .mace_compatibility import mace_frame_uid_set_digest

                replay_uid_digest = mace_frame_uid_set_digest(
                    replay_geometry_identities
                )
            if replay_uid_digest is None:
                raise TrainingDataInputError(
                    "P5 replay materialization has no exported frame-UID authority."
                )
        # This is continuation authentication, not a new launch. Keep the
        # persisted executable payload intact: projecting it through the
        # current parser would turn an absent historical
        # ``compute_avg_num_neighbors`` control into today's explicit False
        # and would therefore erase the distinction the recovery classifier
        # still has to make.
        executable_payload = dict(config_payload)
        authority = _build_post_selection_mace_execution_authority(
            materialization=materialization,
            internal_payload=config_payload,
            executable_payload=executable_payload,
            optimizer_policy=optimizer_policy,
            replay_train_artifact=replay_artifact,
            replay_geometry_identities=getattr(
                replay_resolution, "replay_geometry_identities", None
            ),
        )
        authenticated = record_mace_execution_evidence(authority, evidence)
        resolved = authenticated.get("resolved_evidence")
        if not isinstance(resolved, Mapping):
            raise TrainingDataInputError(
                "MACE execution authority did not produce resolved evidence."
            )
        if resolved.get("target_frame_uid_set_digest") != target_uid_digest:
            raise TrainingDataInputError(
                "Persisted MACE target frame membership differs from P5 materialization."
            )
        if resolved.get("replay_frame_uid_set_digest") != replay_uid_digest:
            raise TrainingDataInputError(
                "Persisted MACE replay frame membership differs from P5 materialization."
            )
    except Exception as exc:
        _post_selection_recovery_error(
            "TRAIN2 continuation MACE execution evidence is incompatible with the "
            "current P5 materialization; preserving diagnostic state.",
            exc,
        )


def _post_selection_current_training_architecture(
    context: PostSelectionContext,
    *,
    current_config: Mapping[str, Any],
) -> tuple[str, str | None]:
    """Reconstruct the current authorized TRAIN2 architecture once.

    The persisted continuation supplies the historical fact. This helper only
    realizes the current frozen configuration through the existing MACE model
    and CuEq/OEq conversion owners; it creates no restart or architecture
    record of its own.

    Classification is not training. The temporary portable and CuEq/OEq models
    are model-scale accelerator owners, so they are retired here - including on
    the conversion/digest exception paths - rather than left to function-scope
    collection. Otherwise recovery preflight would silently contribute its own
    residency to the baseline that TRAIN2 admission is later measured against.
    """

    from .model_features import (
        build_mace_model_from_configuration,
        mace_model_execution_architecture_digest,
        realize_mace_training_model,
        release_mace_accelerator_residency,
    )

    portable_model = None
    training_model = None
    try:
        portable_model = build_mace_model_from_configuration(
            current_config,
            foundation_model_path=context.method_policies.foundation_model,
        )
        training_model, realization = realize_mace_training_model(
            portable_model, current_config
        )
        return mace_model_execution_architecture_digest(training_model), realization
    finally:
        training_model = None
        portable_model = None
        release_mace_accelerator_residency()


def _validate_post_selection_materialization_artifacts(
    selected: CurrentSelectedTrainingContext,
    *,
    material_directory: Path,
    record: PostSelectionMaterialization,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    preparation: Any,
    extxyz_policy: Any,
) -> None:
    """Re-authenticate DATA8 role artifacts before treating a record as owned."""

    expected = [
        (
            "target training",
            record.target_train_artifact,
            "target_train",
            training_frame_uids,
            preparation.content_digest,
        ),
        (
            "checkpoint monitor",
            record.checkpoint_monitor_artifact,
            "checkpoint_monitor",
            monitor_frame_uids,
            None,
        ),
    ]
    outer_frames = () if outer_evaluation_frame_uids is None else tuple(
        str(value) for value in outer_evaluation_frame_uids
    )
    if outer_frames:
        if record.outer_evaluation_artifact is None:
            _post_selection_recovery_error(
                "P5 materialization is missing its required outer-evaluation artifact."
            )
        expected.append(
            (
                "outer evaluation",
                record.outer_evaluation_artifact,
                "outer_evaluation",
                outer_frames,
                None,
            )
        )
    elif record.outer_evaluation_artifact is not None:
        _post_selection_recovery_error(
            "P5 materialization carries an outer-evaluation artifact for a run "
            "that has no outer-evaluation membership."
        )

    from .target_size_execution import validate_target_size_extxyz_artifact

    authorities = selected.authorities
    for label, artifact, role, frame_uids, preparation_digest in expected:
        if artifact is None:
            _post_selection_recovery_error(
                f"P5 materialization is missing its {label} artifact."
            )
        if artifact.role != role or tuple(artifact.frame_uids) != tuple(
            str(value) for value in frame_uids
        ):
            _post_selection_recovery_error(
                f"P5 materialization {label} membership/role does not match the "
                "current run plan."
            )
        if artifact.common_preparation_digest != preparation_digest:
            _post_selection_recovery_error(
                f"P5 materialization {label} preparation lineage does not match "
                "the current fitted preparation."
            )
        try:
            validate_target_size_extxyz_artifact(
                artifact,
                root_directory=material_directory,
                canonical_frame_authority=authorities.frame_authority,
                policy=extxyz_policy,
                frame_catalog=authorities.frame_catalog,
                frame_data_by_run=authorities.frame_data_by_run,
                frame_array_index=authorities.frame_array_index,
            )
        except Exception as exc:
            _post_selection_recovery_error(
                f"P5 materialization {label} artifact failed authentication; "
                "preserving diagnostic state.",
                exc,
            )


def _classify_post_selection_materialization(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    material_directory: Path,
    run_root: Path,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    preparation: Any,
    optimizer_policy: Any,
    extxyz_policy: Any,
    replay_resolution: Any | None,
    continuation_summary: Any | None,
) -> tuple[PostSelectionMaterialization | None, bool, bool, bool]:
    """Classify existing P5 materialization before any replacement is allowed.

    Returns ``(record, rebuild, use_existing, replace_stale_continuation)``.
    ``rebuild`` is granted only for absent/incomplete or authenticated
    disposable pre-fix scratch. A faithful pre-fix record with valid TRAIN2
    progress is returned for direct reuse because immutable descendant state
    must not be deleted merely to obtain the current configuration spelling.
    The final flag is granted only after the complete authenticated
    immediately-pre-fix representation proves that its persisted actual
    training architecture is stale. It is an execution-local decision; no
    recovery state is persisted.
    """

    if any(
        (run_root / name).exists() or (run_root / name).is_symlink()
        for name in RUN_TERMINAL_RECORD_NAMES
    ):
        _post_selection_recovery_error(
            "P5 run root already carries terminal evidence; refusing to re-enter "
            "its materialization recovery path."
        )
    if material_directory.is_symlink():
        _post_selection_recovery_error(
            "P5 materialization is a symlink; preserving it."
        )
    if not material_directory.exists():
        if continuation_summary is not None:
            _post_selection_recovery_error(
                "TRAIN2 continuation is durable but its P5 materialization is "
                "absent; preserving both sides and refusing to rebuild it."
            )
        return None, False, False, False
    if not material_directory.is_dir():
        _post_selection_recovery_error(
            "P5 materialization is not a regular directory; preserving it."
        )

    record_path = material_directory / "materialization.json"
    if not record_path.exists():
        _assert_owned_materialization_tree(material_directory, record=None)
        if continuation_summary is not None:
            _post_selection_recovery_error(
                "TRAIN2 continuation is durable but P5 materialization publication "
                "is incomplete; preserving both sides and refusing to rebuild it."
            )
        # No final authenticated record means interrupted publication, not a
        # completed record whose bytes failed validation.
        return None, True, False, False
    if record_path.is_symlink() or not record_path.is_file():
        _post_selection_recovery_error(
            "P5 materialization final record is not a regular file; preserving it."
        )
    try:
        payload = json.loads(record_path.read_text(encoding="utf-8"))
        if not isinstance(payload, Mapping):
            raise TrainingDataSerializationError(
                "P5 materialization final record must be a JSON object."
            )
        record = PostSelectionMaterialization.from_dict(payload)
    except Exception as exc:
        _post_selection_recovery_error(
            "P5 materialization final record is malformed or digest-inconsistent; "
            "preserving diagnostic state.",
            exc,
        )
    _assert_owned_materialization_tree(material_directory, record=record)

    if preparation is None:
        _post_selection_recovery_error(
            "P5 materialization requires a current fitted preparation for "
            "authentication; preserving it."
        )

    if (
        record.run_plan_digest != run_plan.content_digest
        or record.run_identity != run_plan.run_identity
        or record.preparation_digest != preparation.content_digest
        or Path(record.output_directory).resolve() != material_directory.resolve()
    ):
        _post_selection_recovery_error(
            "P5 materialization is internally valid but belongs to a different "
            "run, plan, preparation, or output directory; preserving it."
        )
    _validate_post_selection_materialization_artifacts(
        context.selected,
        material_directory=material_directory,
        record=record,
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
        outer_evaluation_frame_uids=outer_evaluation_frame_uids,
        preparation=preparation,
        extxyz_policy=extxyz_policy,
    )
    if record.mace_config_relative_path != "post_selection_mace_config.yaml":
        _post_selection_recovery_error(
            "P5 materialization uses an unsupported internal configuration path; "
            "preserving it."
        )
    _safe_materialization_relative_path(
        material_directory,
        record.mace_config_relative_path,
        name="MACE configuration path",
    )
    config_path = material_directory / record.mace_config_relative_path
    if config_path.is_symlink() or not config_path.is_file():
        _post_selection_recovery_error(
            "P5 materialization MACE configuration is missing or symlinked; "
            "preserving it."
        )
    try:
        config_bytes = config_path.read_bytes()
        config_payload = json.loads(config_bytes.decode("utf-8"))
        if not isinstance(config_payload, Mapping):
            raise TrainingDataSerializationError(
                "P5 materialization MACE configuration must be a JSON object."
            )
        if hashlib.sha256(config_bytes).hexdigest() != record.mace_config_sha256:
            raise TrainingDataInputError(
                "P5 materialization MACE configuration bytes do not match its record."
            )
        if digest(config_payload) != record.mace_config_digest:
            raise TrainingDataInputError(
                "P5 materialization MACE configuration digest does not match its record."
            )
    except Exception as exc:
        _post_selection_recovery_error(
            "P5 materialization MACE configuration is corrupt or inconsistent; "
            "preserving diagnostic state.",
            exc,
        )

    if continuation_summary is not None:
        _validate_post_selection_continuation_execution_evidence(
            context,
            materialization=record,
            config_payload=config_payload,
            continuation_summary=continuation_summary,
            replay_resolution=replay_resolution,
            optimizer_policy=optimizer_policy,
        )

    expected_config = _post_selection_mace_config(
        run_identity=run_plan.run_identity,
        optimizer_seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
        preparation=preparation,
        optimizer_policy=optimizer_policy,
        target_train=record.target_train_artifact,
        monitor=record.checkpoint_monitor_artifact,
        extxyz_policy=extxyz_policy,
        method=context.method,
        mace_architecture=context.method_policies.mace_architecture,
        foundation_head=context.method_policies.foundation_head,
        multiheads_finetuning=(
            context.method_policies.training_mode == "multihead_replay"
        ),
        replay_train=(
            None if replay_resolution is None else replay_resolution.train_path
        ),
        replay_monitor=(
            None if replay_resolution is None else replay_resolution.monitor_path
        ),
    )
    expected_bytes = json.dumps(
        expected_config, indent=2, sort_keys=True
    ).encode("utf-8")
    current = config_payload == expected_config and config_bytes == expected_bytes
    if current:
        return record, False, False, False

    # The only supported pre-fix compatibility is the exact representation
    # immediately before the explicit local-neighbor control was published:
    # the control is absent, and the retired runtime locator may be present.
    # The record, artifacts, method, and every other config field have already
    # authenticated above; neither the stale locator nor a missing control is
    # consulted as a current execution setting.
    legacy_payload = dict(config_payload)
    legacy_locator = legacy_payload.pop("foundation_model", None)
    faithful_pre_fix = (
        context.method_policies.foundation_potential_identity is not None
        and isinstance(legacy_locator, str)
        and bool(legacy_locator.strip())
        and legacy_payload == expected_config
    )
    if faithful_pre_fix:
        if continuation_summary is not None:
            return record, False, True, False
        return record, True, False, False

    historical_payload = dict(config_payload)
    historical_locator = historical_payload.pop("foundation_model", None)
    if "compute_avg_num_neighbors" not in historical_payload:
        valid_historical_locator = historical_locator is None or (
            context.method_policies.foundation_potential_identity is not None
            and isinstance(historical_locator, str)
            and bool(historical_locator.strip())
        )
        expected_historical = dict(expected_config)
        expected_historical.pop("compute_avg_num_neighbors", None)
        if valid_historical_locator and historical_payload == expected_historical:
            if continuation_summary is None:
                # No durable TRAIN2 state exists, so the authenticated
                # pre-fix materialization is disposable interrupted scratch.
                return record, True, False, False

            persisted_architecture = getattr(
                continuation_summary, "model_architecture_digest", None
            )
            if not isinstance(persisted_architecture, str) or not persisted_architecture:
                _post_selection_recovery_error(
                    "P5 pre-fix TRAIN2 continuation has no persisted model architecture "
                    "authority; preserving diagnostic state."
                )
            try:
                current_architecture, _realization = _post_selection_current_training_architecture(
                    context,
                    current_config=expected_config,
                )
            except (
                OSError,
                RuntimeError,
                TypeError,
                ValueError,
                TrainingDataInputError,
            ) as exc:
                _post_selection_recovery_error(
                    "P5 pre-fix TRAIN2 architecture could not be reconstructed through "
                    "the current MACE training-realization owner; preserving diagnostic state.",
                    exc,
                )
            if persisted_architecture == current_architecture:
                # The only difference is the retired configuration spelling;
                # the authenticated actual training realization is current.
                # Reuse the immutable materialization and let the corrected
                # EVAL2 path consume the authenticated continuation.
                return record, False, True, False
            return record, True, False, True
    _post_selection_recovery_error(
        "P5 materialization is internally valid but its protected executable "
        "configuration is foreign to the current run; preserving it."
    )
    return record, False, False, False


@dataclass(frozen=True, slots=True)
class _PostSelectionRunSetup:
    """Authenticated, non-mutating setup shared by execution and preflight."""

    material_directory: Path
    checkpoint_directory: Path
    optimizer_policy: Any
    extxyz_policy: Any
    admissibility: Any
    replay_resolution: Any | None
    preparation: Any | None
    runtime_plan: Any
    continuation_summary: Any | None
    start_epoch: int
    existing_materialization: Any | None
    rebuild_materialization: bool
    use_existing_materialization: bool
    replace_stale_continuation: bool


def _prepare_post_selection_run(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
) -> _PostSelectionRunSetup:
    """Authenticate one run's recoverable state without changing its files."""

    material_directory = context.run_root(run_plan.run_identity) / "materialization"
    checkpoint_directory = context.run_root(run_plan.run_identity) / "checkpoints"
    optimizer_policy = _optimizer_policy_for(
        context, seed=run_plan.optimizer_seed, planned_epochs=run_plan.planned_epochs
    )
    extxyz_policy = context.method_policies.extxyz
    admissibility = context.method_policies.checkpoint_admissibility
    replay_resolution = None
    if admissibility.replay_enabled:
        replay_resolution = _resolve_post_selection_replay_resolution(
            context, require_train=True
        )
        if replay_resolution is None or replay_resolution.monitor_artifact is None:
            raise PostSelectionError(
                "Could not resolve TRUE_DFT replay monitor artifact for replay-enabled run."
            )

    # A durable materialization is fitted from current authority in memory
    # before it is authenticated or replaced. This is the same recovery
    # preparation used by the execution owner; setup itself publishes nothing.
    preparation = None
    if (material_directory / "materialization.json").exists():
        preparation = fit_post_selection_preparation(
            context.selected,
            membership=training_frame_uids,
            owner_plan_digest=run_plan.content_digest,
            common_training_policy=context.method_policies.common_training,
        )
    runtime_plan = post_selection_runtime_plan(
        method=context.method,
        optimizer_policy=optimizer_policy,
        budget_policy=budget_policy,
        structures_per_epoch=(
            len(preparation.membership)
            if preparation is not None
            else len(tuple(str(value) for value in training_frame_uids))
        ),
        learning_rate_policy=context.method_policies.learning_rate_schedule,
        replay_monitor_enabled=admissibility.replay_enabled,
        true_replay_monitor_sha256=(
            replay_resolution.monitor_artifact.sha256
            if replay_resolution is not None
            else None
        ),
        target_head_name=context.method_policies.target_head_name,
        replay_head_name=context.method_policies.replay_head_name,
    )
    continuation_summary, start_epoch = _authenticate_post_selection_continuation(
        checkpoint_directory,
        runtime_plan=runtime_plan,
    )
    (
        existing_materialization,
        rebuild_materialization,
        use_existing_materialization,
        replace_stale_continuation,
    ) = _classify_post_selection_materialization(
        context,
        run_plan=run_plan,
        material_directory=material_directory,
        run_root=context.run_root(run_plan.run_identity),
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
        outer_evaluation_frame_uids=outer_evaluation_frame_uids,
        preparation=preparation,
        optimizer_policy=optimizer_policy,
        extxyz_policy=extxyz_policy,
        replay_resolution=replay_resolution,
        continuation_summary=continuation_summary,
    )
    if replace_stale_continuation:
        # The classifier has authenticated the historical continuation and
        # established that it is the narrowly recognized pre-fix representation
        # with a different actual model architecture.  It must not be handed to
        # the trainer as a resumable predecessor.
        continuation_summary = None
        start_epoch = 0
        existing_materialization = None
    return _PostSelectionRunSetup(
        material_directory=material_directory,
        checkpoint_directory=checkpoint_directory,
        optimizer_policy=optimizer_policy,
        extxyz_policy=extxyz_policy,
        admissibility=admissibility,
        replay_resolution=replay_resolution,
        preparation=preparation,
        runtime_plan=runtime_plan,
        continuation_summary=continuation_summary,
        start_epoch=start_epoch,
        existing_materialization=existing_materialization,
        rebuild_materialization=rebuild_materialization,
        use_existing_materialization=use_existing_materialization,
        replace_stale_continuation=replace_stale_continuation,
    )


def _execute_post_selection_run_locked(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    run_root: Path,
    progress_context: Mapping[str, Any] | None = None,
    cancellation_event: Any | None = None,
    progress_callback: Callable[[str], None] | None = None,
    progress_observer: Callable[[Mapping[str, Any]], None] | None = None,
    telemetry_ref: Any | None = None,
    stop_after_training: bool = False,
) -> tuple[PostSelectionRunEvidence, Any, Any] | None:
    """The run body, executed while this run root's activity lease is held."""

    from ._campaign_cli_core import _cfg

    context_cfg = getattr(context, "cfg", None)
    selected = context.selected
    setup = _prepare_post_selection_run(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
        outer_evaluation_frame_uids=outer_evaluation_frame_uids,
    )
    material_directory = setup.material_directory
    checkpoint_directory = setup.checkpoint_directory
    optimizer_policy = setup.optimizer_policy
    extxyz_policy = setup.extxyz_policy
    replay_resolution = setup.replay_resolution
    preparation = setup.preparation
    runtime_plan = setup.runtime_plan
    continuation_summary = setup.continuation_summary
    start_epoch = setup.start_epoch
    existing_materialization = setup.existing_materialization
    rebuild_materialization = setup.rebuild_materialization
    use_existing_materialization = setup.use_existing_materialization
    replace_stale_continuation = setup.replace_stale_continuation
    # Finish any detached scratch left by an earlier interrupted invocation
    # before entering the next canonical transition.  The helper refuses to
    # touch a scratch destination while its canonical namespace is present,
    # which keeps an unknown collision fail-closed.
    for canonical_name in _POST_SELECTION_RETIREMENT_NAMES:
        _reclaim_post_selection_retirement_scratch(
            run_root,
            run_root / canonical_name,
            canonical_name=canonical_name,
        )
    if replace_stale_continuation:
        # This occurs only after TRAIN2, materialization, MACE evidence, and
        # the activity lease have all authenticated the stale continuation; no
        # foreign/corrupt canonical state can reach this branch.  Retire the
        # continuation first so the accepted checkpoint-before-materialization
        # ordering remains explicit.
        _detach_post_selection_namespace(
            run_root,
            checkpoint_directory,
            canonical_name="checkpoints",
        )
    if rebuild_materialization or replace_stale_continuation:
        # The classifier has established that this is local, run-owned,
        # nonterminal scratch.  The live namespace is detached before any
        # recursive reclaim, so an interruption cannot expose a partially
        # destroyed canonical materialization to the next invocation.
        _detach_post_selection_namespace(
            run_root,
            material_directory,
            canonical_name="materialization",
        )
    checkpoint_directory.mkdir(parents=True, exist_ok=True)

    if use_existing_materialization:
        materialization = existing_materialization
    else:
        preparation, materialization = materialize_post_selection_run(
            selected,
            run_plan=run_plan,
            method=context.method,
            training_frame_uids=training_frame_uids,
            monitor_frame_uids=monitor_frame_uids,
            outer_evaluation_frame_uids=outer_evaluation_frame_uids,
            optimizer_policy=optimizer_policy,
            extxyz_policy=extxyz_policy,
            output_directory=material_directory,
            preparation=preparation,
            common_training_policy=context.method_policies.common_training,
            mace_architecture=context.method_policies.mace_architecture,
            foundation_head=context.method_policies.foundation_head,
            multiheads_finetuning=(
                context.method_policies.training_mode == "multihead_replay"
            ),
            replay_train=(
                None if replay_resolution is None else replay_resolution.train_path
            ),
            replay_monitor=(
                None if replay_resolution is None else replay_resolution.monitor_path
            ),
        )

    if continuation_summary is not None and (
        continuation_summary.completed_epochs == runtime_plan.execution_epoch_limit
    ):
        # A crash after the last durable epoch but before EVAL2/terminal
        # publication can reuse the fully authenticated summary without asking
        # the trainer seam to perform a zero-epoch call.
        summary = continuation_summary
    else:
        summary = context.trainer(
            PostSelectionRungRequest(
                plan=runtime_plan,
                run_plan=run_plan,
                materialization=materialization,
                materialization_directory=material_directory,
                checkpoint_directory=checkpoint_directory,
                optimizer_policy=optimizer_policy,
                start_epoch=start_epoch,
                foundation_identity=context.method_policies.foundation_potential_identity,
                foundation_model_path=(
                    Path(context.method_policies.foundation_model)
                    if context.method_policies.foundation_model
                    else None
                ),
                replay_train_artifact=(
                    replay_resolution.train_artifact
                    if replay_resolution is not None
                    else None
                ),
                replay_train_path=(
                    Path(replay_resolution.train_path)
                    if replay_resolution is not None
                    and replay_resolution.train_path is not None
                    else None
                ),
                replay_monitor_artifact=(
                    replay_resolution.monitor_artifact
                    if replay_resolution is not None
                    else None
                ),
                replay_monitor_path=(
                    Path(replay_resolution.monitor_path)
                    if replay_resolution is not None
                    and replay_resolution.monitor_path is not None
                    else None
                ),
                replay_geometry_identities=(
                    None
                    if replay_resolution is None
                    else getattr(replay_resolution, "replay_geometry_identities", None)
                ),
                progress_context=progress_context,
                cancellation_event=cancellation_event,
                progress_callback=progress_callback,
                progress_observer=progress_observer,
                telemetry_ref=telemetry_ref,
                optimizer_activity_timeout_seconds=float(
                    120.0
                    if context_cfg is None
                    else _cfg(
                        context_cfg,
                        "execution",
                        "parallel_training_epoch_activity_timeout_seconds",
                        120.0,
                    )
                ),
            )
        )
    if summary is None:
        raise PostSelectionExecutionError(
            "The post-selection trainer returned no authenticated TRAIN2 summary."
        )
    if summary.plan_digest != runtime_plan.content_digest:
        raise PostSelectionExecutionError(
            "The TRAIN2 runtime summary does not belong to this run's runtime plan."
        )

    if stop_after_training:
        # TRAIN2 ownership ends here. The authenticated summary, checkpoints,
        # and materialization are the durable boundary; no additional handoff
        # record is created, and an interruption before EVAL2 resumes from them.
        return None

    catalog, representative, monitor_metrics = evaluate_post_selection_run_candidates(
        context,
        run_plan=run_plan,
        runtime_plan=runtime_plan,
        materialization=materialization,
        material_directory=material_directory,
        checkpoint_directory=checkpoint_directory,
        summary=summary,
        monitor_frame_uids=monitor_frame_uids,
        replay_resolution=replay_resolution,
    )

    outer_metrics = None
    if outer_evaluation_frame_uids:
        checkpoint = catalog.checkpoint_by_sha256(
            representative.trajectory_point.checkpoint_sha256
        )
        provider, _evaluated = authenticate_post_selection_provider(
            materialization=materialization,
            materialization_directory=material_directory,
            checkpoint_directory=checkpoint_directory,
            checkpoint_name=Path(checkpoint.relative_path).name,
            checkpoint_sha256=checkpoint.sha256,
            checkpoint_epoch=getattr(checkpoint, "epoch", None),
            summary=summary,
            evaluation_model_state=resolve_post_selection_evaluation_model_state(
                context,
                seed=run_plan.optimizer_seed,
                planned_epochs=run_plan.planned_epochs,
            ),
            allow_forward_override=context.inference_evaluator is not None,
            foundation_model_path=context.method_policies.foundation_model,
        )
        try:
            outer_metrics = evaluate_post_selection_dataset(
                run_plan=run_plan,
                artifact=materialization.outer_evaluation_artifact,
                dataset_role=DATASET_ROLE_OUTER_EVALUATION,
                root_directory=material_directory,
                provider=provider,
                block_ids=_component_block_ids(selected, outer_evaluation_frame_uids),
                execution_batch_width=execution_batch_width(optimizer_policy),
                extxyz_policy=extxyz_policy,
                inference_evaluator=context.inference_evaluator,
            )
        finally:
            _retire_post_selection_provider(provider)

    evidence = PostSelectionRunEvidence(
        run_plan_digest=run_plan.content_digest,
        run_identity=run_plan.run_identity,
        run_role=run_plan.run_role,
        materialization_digest=materialization.content_digest,
        preparation_digest=preparation.content_digest,
        runtime_summary_digest=summary.content_digest,
        representative_candidate_identity=representative.stable_candidate_identity,
        representative_checkpoint_sha256=(
            representative.trajectory_point.checkpoint_sha256
        ),
        representative_record_digest=representative.content_digest,
        monitor_metric_record_digest=monitor_metrics.content_digest,
        outer_metric_record_digest=(
            None if outer_metrics is None else outer_metrics.content_digest
        ),
    )
    store = context.evidence_store
    store.put(preparation)
    store.put(materialization)
    # The exact records that *decided* this run's representative are durable
    # evidence, not intermediate state.  A later cross-seed publication decision
    # has to authenticate them rather than reconstruct a ranking from digests.
    store.put(representative)
    store.put(monitor_metrics)
    store.put(evidence)
    # Final-production evidence is independently restartable. Publish its
    # run-root proof before the shared scheduler can observe a later sibling
    # failure; CV still waits for its separate fold-acceptance authority.
    if str(getattr(run_plan, "run_role", "")) == "final_production":
        _record_completed_run_evidence(context, run_plan, evidence)
    return evidence, representative, outer_metrics


def authenticated_run_representative_records(
    context: PostSelectionContext, run_plan: Any, evidence: PostSelectionRunEvidence
) -> tuple[Any, Any]:
    """Return one completed run's exact representative EVAL2 and M3 records.

    Newly executed runs publish both records durably, so the normal path is an
    authenticated content-addressed read.  A run root written before those
    records were durable is *re-evaluated through the real EVAL2/provider
    owner* on the exact authenticated checkpoints and frozen M3; the recovered
    records must reproduce the digests the run evidence already bound, or the
    run is not authentic.  Nothing here synthesizes a record from a digest.
    """

    from .eval2 import Eval2CheckpointRecord, Eval2TargetMetricRecord

    store = context.evidence_store
    if store.has(evidence.representative_record_digest) and store.has(
        evidence.monitor_metric_record_digest
    ):
        return (
            store.get(evidence.representative_record_digest, Eval2CheckpointRecord.from_dict),
            store.get(evidence.monitor_metric_record_digest, Eval2TargetMetricRecord.from_dict),
        )
    representative, monitor_metrics = _reevaluate_run_representative_records(
        context, run_plan, evidence
    )
    if (
        representative.content_digest != evidence.representative_record_digest
        or monitor_metrics.content_digest != evidence.monitor_metric_record_digest
    ):
        raise PostSelectionError(
            f"Re-evaluating completed production run {run_plan.run_identity[:12]}... "
            "did not reproduce the representative/monitor evidence it published. "
            "The affected final-production work must be rerun; a publication "
            "decision is never taken on reconstructed evidence."
        )
    store.put(representative)
    store.put(monitor_metrics)
    return representative, monitor_metrics


def _reevaluate_run_representative_records(
    context: PostSelectionContext, run_plan: Any, evidence: PostSelectionRunEvidence
) -> tuple[Any, Any]:
    """Recover a legacy run's representative records through the real owner."""

    from .post_selection_execution import (
        PostSelectionFittedPreparation,
        PostSelectionMaterialization,
    )
    from .train2_runtime import load_train2_runtime_summary

    run_root = context.run_root(run_plan.run_identity)
    material_directory = run_root / "materialization"
    checkpoint_directory = run_root / "checkpoints"
    materialization = context.evidence_store.get(
        evidence.materialization_digest, PostSelectionMaterialization.from_dict
    )
    preparation = context.evidence_store.get(
        evidence.preparation_digest, PostSelectionFittedPreparation.from_dict
    )
    summary = load_train2_runtime_summary(checkpoint_directory)
    if summary.content_digest != evidence.runtime_summary_digest:
        raise PostSelectionError(
            f"The stored TRAIN2 runtime summary for {run_plan.run_identity[:12]}... "
            "does not match the summary its run evidence bound."
        )
    admissibility = context.method_policies.checkpoint_admissibility
    replay_resolution = None
    if admissibility.replay_enabled:
        replay_resolution = _resolve_post_selection_replay_resolution(
            context, require_train=True
        )
    optimizer_policy = _optimizer_policy_for(
        context, seed=run_plan.optimizer_seed, planned_epochs=run_plan.planned_epochs
    )
    _m3_size, m3_membership, _m3_digest = frozen_m3_development_evidence(context.selected)
    runtime_plan = post_selection_runtime_plan(
        method=context.method,
        optimizer_policy=optimizer_policy,
        budget_policy=final_production_training_budget_policy(
            context.method, context.production_policy
        ),
        structures_per_epoch=len(preparation.membership),
        learning_rate_policy=context.method_policies.learning_rate_schedule,
        replay_monitor_enabled=admissibility.replay_enabled,
        true_replay_monitor_sha256=(
            replay_resolution.monitor_artifact.sha256
            if replay_resolution is not None and replay_resolution.monitor_artifact is not None
            else None
        ),
        target_head_name=context.method_policies.target_head_name,
        replay_head_name=context.method_policies.replay_head_name,
    )
    if summary.plan_digest != runtime_plan.content_digest:
        raise PostSelectionError(
            f"The completed production run {run_plan.run_identity[:12]}... cannot be "
            "deterministically re-evaluated: its runtime plan is no longer "
            "reproducible from current authority. Rerun the affected work."
        )
    _catalog, representative, monitor_metrics = evaluate_post_selection_run_candidates(
        context,
        run_plan=run_plan,
        runtime_plan=runtime_plan,
        materialization=materialization,
        material_directory=material_directory,
        checkpoint_directory=checkpoint_directory,
        summary=summary,
        monitor_frame_uids=m3_membership,
        replay_resolution=replay_resolution,
    )
    return representative, monitor_metrics


def _checkpoint_catalog(run_plan: Any, checkpoint_directory: Path) -> Any:
    from .post_selection_execution import post_selection_checkpoint_catalog

    return post_selection_checkpoint_catalog(
        run_plan=run_plan, checkpoint_directory=checkpoint_directory
    )


#: Filename of one fold's completed acceptance inside its own run directory.
#: Fold evidence is content-addressed like everything else, but a restart needs
#: to find it by *position* rather than by digest, so the position record lives
#: beside the run it describes.
FOLD_ACCEPTANCE_FILENAME = "fold-acceptance.json"

#: The same idea for one completed final-production job.
RUN_EVIDENCE_FILENAME = "run-evidence.json"

#: One completed run's terminal proof is deliberately **two** records with two
#: different cost classes.
#:
#: The full *topology manifest* names every node - regular file and directory -
#: this owner produced under the run root.  Membership is the one thing a
#: downstream consumer cannot re-derive and must not guess, and it has to cover
#: directories as well as files, because a recursive delete removes directory
#: nodes too: an unexpected *empty* directory that no file path mentions would
#: otherwise vanish under an authorized ``rmtree``.  That record is inherently
#: O(number of descendants).
#:
#: The compact *completion anchor* is the commit point, and it is O(1).  It says
#: that this run finished, which terminal evidence it published, and the content
#: identity of the topology manifest that goes with it.  Normal storage
#: reporting validates only this record, so describing a campaign never costs
#: anything proportional to how much bulk a run holds; exact closed-subtree
#: certification is the only path that pays for the full manifest.
RUN_TOPOLOGY_MANIFEST_FILENAME = "run-topology.json"
RUN_TOPOLOGY_MANIFEST_SCHEMA = "mdstats.post-selection-run-topology.v1"
RUN_COMPLETION_ANCHOR_FILENAME = "run-completion.json"
RUN_COMPLETION_ANCHOR_SCHEMA = "mdstats.post-selection-run-completion.v1"

#: The superseded single-file development anchor.  It was never a released
#: durable authority, and it is not one now: a run root carrying only this file
#: is diagnosable but grants no consequential storage authority.  The name stays
#: known so a leftover copy is recognized as this owner's own residue rather
#: than mistaken for an unexpected descendant.
RUN_MEMBER_MANIFEST_FILENAME = "run-members.json"
RUN_MEMBER_MANIFEST_SCHEMA = "mdstats.post-selection-run-members.v1"

#: Advisory lock files this owner's own publication primitive leaves beside the
#: records it writes.  They are P5 infrastructure, not run evidence: they are
#: never members, and they never make a run root look uncertified.
_OWNED_LOCK_NAMES: frozenset[str] = frozenset(
    f".{name}.lock"
    for name in (
        FOLD_ACCEPTANCE_FILENAME,
        RUN_EVIDENCE_FILENAME,
        RUN_TOPOLOGY_MANIFEST_FILENAME,
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_MEMBER_MANIFEST_FILENAME,
    )
)

#: Every top-level name this owner writes as completion infrastructure rather
#: than as run content.  These are never manifest nodes and never unexpected
#: descendants.
RUN_COMPLETION_INFRASTRUCTURE_NAMES: frozenset[str] = frozenset(
    {
        RUN_TOPOLOGY_MANIFEST_FILENAME,
        RUN_COMPLETION_ANCHOR_FILENAME,
        RUN_MEMBER_MANIFEST_FILENAME,
        *_OWNED_LOCK_NAMES,
    }
)

#: Terminal evidence kinds this owner actually publishes.  A completion anchor
#: that names anything else is not describing a run this owner finished.
RUN_TERMINAL_RECORD_NAMES: frozenset[str] = frozenset(
    {FOLD_ACCEPTANCE_FILENAME, RUN_EVIDENCE_FILENAME}
)

#: Advisory activity lease guarding one run root's write lifetime.  P5 holds it
#: while it materializes, trains, and publishes that run; anything that wants to
#: change the run tree's representation must hold it exclusively first.
#:
#: The lease file lives *beside* the run root rather than inside it, so a run
#: root's contents stay exactly what this owner's execution wrote and remain
#: certifiable as a closed subtree.
RUN_ACTIVITY_LEASE_SUFFIX = ".run-activity"


def post_selection_run_activity_lease(run_root: str | os.PathLike[str]):
    """The owner-local no-write lease for one post-selection run root.

    Generation supersession is not a liveness proof: P5 deliberately permits a
    run that began under an older selected binding to keep executing, and only
    refuses *publication* once a newer campaign revision is current.  A process
    that started while ``g1`` was current can therefore still be writing
    ``g1/runs/...`` long after ``g2`` became current.

    This lease is what makes that provable rather than guessed.  The real
    execution path below holds it for the run's whole write lifetime, and any
    consumer that wants to archive, deduplicate, or otherwise re-represent the
    run tree must acquire it exclusively.  It is an advisory ``flock``, so a
    crashed holder is released by the kernel and no PID, age, or pathname
    inference is ever needed.

    Lock order: a run-activity lease is always acquired *before* the
    generation's publication barrier, never after, so P5 execution and storage
    share one cycle-free order.
    """

    from .target_size_execution import artifact_publication_lock

    root = Path(run_root)
    root.parent.mkdir(parents=True, exist_ok=True)
    return artifact_publication_lock(
        root.parent / f".{root.name}{RUN_ACTIVITY_LEASE_SUFFIX}"
    )


def _canonical_node_path(root: Path, path: Path) -> str | None:
    """The canonical POSIX-relative locator of one node, or ``None`` if unusable."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        return None
    parts = relative.parts
    if not parts or any(part in ("", ".", "..") for part in parts):
        return None
    if parts[0] in RUN_COMPLETION_INFRASTRUCTURE_NAMES:
        return None
    return relative.as_posix()


def _observe_run_root_nodes(root: Path) -> list[dict[str, str]]:
    """Every node present under one run root, classified without following links.

    Symlinks and special objects are *observed*, not skipped. Dropping them here
    would make a symlink substituted at a recorded member name simply vanish from
    the comparison instead of contradicting the closed-subtree proof, which is
    exactly the substitution this certification has to catch.
    """

    from .storage.owners import NODE_ABSENT, observed_node_kind

    nodes: list[dict[str, str]] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            relative = _canonical_node_path(root, path)
            if relative is None:
                continue
            kind = observed_node_kind(path)
            if kind == NODE_ABSENT:
                continue
            nodes.append({"path": relative, "kind": kind})
            if kind == "directory":
                stack.append(path)
    return sorted(nodes, key=lambda item: item["path"])


def _run_root_nodes(root: Path) -> list[dict[str, str]]:
    """The nodes this owner records as its own: plain files and directories.

    Directories are recorded deliberately.  A recursive delete removes directory
    nodes as well as files, so a manifest that named only files would leave an
    unexpected empty directory covered by nothing and free to disappear inside an
    otherwise authorized ``rmtree``.  Symlinks and special objects are never
    recorded: nothing this owner writes is one, so their presence is a
    contradiction rather than a member.
    """

    return [
        item
        for item in _observe_run_root_nodes(root)
        if item["kind"] in ("file", "directory")
    ]


def _sealed(payload: dict[str, Any]) -> dict[str, Any]:
    """One canonical record plus its own content identity."""

    body = {key: value for key, value in payload.items() if key != "content_digest"}
    return {**body, "content_digest": digest(body)}


def _self_authenticated(payload: Any, schema: str) -> dict[str, Any] | None:
    """A record whose schema matches and whose own digest re-derives, or ``None``."""

    if not isinstance(payload, Mapping):
        return None
    if payload.get("schema") != schema:
        return None
    recorded = str(payload.get("content_digest", ""))
    body = {key: value for key, value in dict(payload).items() if key != "content_digest"}
    if not recorded or recorded != digest(body):
        return None
    return dict(payload)


def _load_owner_record(path: Path) -> Any | None:
    """Parse one owner authority file, refusing anything but a real regular file.

    The read goes through the strict no-follow reader rather than
    ``read_text()``: a symlink substituted at ``run-completion.json`` or
    ``run-topology.json`` would otherwise let bytes from outside the owner's own
    record participate in destructive certification.
    """

    from .storage.owners import read_owner_record_bytes

    raw = read_owner_record_bytes(path)
    if raw is None:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None


@dataclass(frozen=True, slots=True)
class PostSelectionRunCompletion:
    """The compact, O(1) proof that one post-selection run finished."""

    run_root: str
    terminal_records: tuple[str, ...]
    topology_digest: str
    node_count: int
    file_count: int
    directory_count: int
    content_digest: str


def read_post_selection_run_completion(
    run_root: str | os.PathLike[str],
) -> tuple[PostSelectionRunCompletion | None, str]:
    """Validate the compact completion anchor of one run root.

    This is the **one** validating reader every consumer goes through, and it is
    deliberately bounded: it reads a single small record, re-derives that
    record's own digest, checks the run identity it claims, and confirms the
    bound topology manifest is present.  It never reads or hashes the manifest
    and never walks the run, so normal reporting stays independent of how much
    the run holds.

    Ambiguity reduces authority.  A missing, malformed, unsupported, tampered,
    or copied-for-another-run anchor returns ``None`` with a truthful reason; it
    never degrades into a guessed member set.
    """

    root = Path(run_root)
    from .storage.owners import NODE_FILE, observed_node_kind

    path = root / RUN_COMPLETION_ANCHOR_FILENAME
    if observed_node_kind(path) != NODE_FILE:
        legacy = root / RUN_MEMBER_MANIFEST_FILENAME
        if observed_node_kind(legacy) == NODE_FILE:
            return None, (
                "run root carries only the superseded single-file completion record, "
                "which is diagnosable but grants no consequential authority"
            )
        return None, (
            "run root carries no retained completion anchor, so this owner cannot "
            "certify that it finished or which descendants it produced"
        )
    payload = _self_authenticated(_load_owner_record(path), RUN_COMPLETION_ANCHOR_SCHEMA)
    if payload is None:
        return None, (
            "run completion anchor is unreadable, carries an unsupported schema, or "
            "does not authenticate against its own recorded identity"
        )
    if str(payload.get("run_root", "")) != root.name:
        return None, (
            "run completion anchor names a different run root, so it was copied "
            "rather than published for this run"
        )
    terminal = tuple(str(item) for item in payload.get("terminal_records", ()))
    if not terminal or not set(terminal) <= RUN_TERMINAL_RECORD_NAMES:
        return None, (
            "run completion anchor names no recognized terminal evidence record, so "
            "it does not certify a finished run"
        )
    topology_digest = str(payload.get("topology_digest", ""))
    if len(topology_digest) != 64:
        return None, "run completion anchor binds no topology manifest identity"
    try:
        node_count = int(payload["node_count"])
        file_count = int(payload["file_count"])
        directory_count = int(payload["directory_count"])
    except (KeyError, TypeError, ValueError):
        return None, "run completion anchor carries an unusable node accounting"
    if node_count != file_count + directory_count or node_count < 0:
        return None, "run completion anchor node accounting is self-inconsistent"
    if observed_node_kind(root / RUN_TOPOLOGY_MANIFEST_FILENAME) != NODE_FILE:
        return None, (
            "the topology manifest this completion anchor binds is missing, so exact "
            "ownership of the run tree cannot be established"
        )
    return (
        PostSelectionRunCompletion(
            run_root=root.name,
            terminal_records=tuple(sorted(terminal)),
            topology_digest=topology_digest,
            node_count=node_count,
            file_count=file_count,
            directory_count=directory_count,
            content_digest=str(payload["content_digest"]),
        ),
        f"completion anchor published with {', '.join(sorted(terminal))}",
    )


def read_post_selection_run_topology(
    run_root: str | os.PathLike[str], completion: PostSelectionRunCompletion
) -> tuple[tuple[dict[str, str], ...] | None, str]:
    """Authenticate the full member/topology manifest against its anchor.

    Only exact closed-subtree certification calls this: it is the O(member-count)
    half of the proof, and paying for it is what buys the right to recurse
    destructively.
    """

    root = Path(run_root)
    payload = _self_authenticated(
        _load_owner_record(root / RUN_TOPOLOGY_MANIFEST_FILENAME), RUN_TOPOLOGY_MANIFEST_SCHEMA
    )
    if payload is None:
        return None, (
            "run topology manifest is unreadable, carries an unsupported schema, or "
            "does not authenticate against its own recorded identity"
        )
    if str(payload.get("content_digest", "")) != completion.topology_digest:
        return None, (
            "run topology manifest is not the one this run's completion anchor "
            "bound; the proof is inconsistent and grants nothing"
        )
    if str(payload.get("run_root", "")) != root.name:
        return None, "run topology manifest names a different run root"
    raw = payload.get("nodes", ())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return None, "run topology manifest records no usable node set"
    nodes: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, Mapping):
            return None, "run topology manifest contains a malformed node entry"
        relative = str(item.get("path", ""))
        kind = str(item.get("kind", ""))
        if kind not in ("file", "directory"):
            return None, f"run topology manifest records an unsupported node kind: {kind!r}"
        parts = tuple(relative.split("/")) if relative else ()
        if (
            not parts
            or relative.startswith("/")
            or any(part in ("", ".", "..") for part in parts)
            or parts[0] in RUN_COMPLETION_INFRASTRUCTURE_NAMES
        ):
            return None, f"run topology manifest records a non-canonical path: {relative!r}"
        if relative in seen:
            return None, f"run topology manifest records a duplicate node: {relative!r}"
        seen.add(relative)
        nodes.append({"path": relative, "kind": kind})
    if len(nodes) != completion.node_count:
        return None, (
            "run topology manifest node count disagrees with the completion anchor"
        )
    directories = {item["path"] for item in nodes if item["kind"] == "directory"}
    if sum(1 for item in nodes if item["kind"] == "file") != completion.file_count:
        return None, "run topology manifest file accounting disagrees with its anchor"
    if len(directories) != completion.directory_count:
        return None, "run topology manifest directory accounting disagrees with its anchor"
    for item in nodes:
        parent = "/".join(item["path"].split("/")[:-1])
        if parent and parent not in directories:
            return None, (
                f"run topology manifest records {item['path']!r} without its parent "
                "directory; the topology is not self-consistent"
            )
    return tuple(nodes), "topology manifest authenticated against its completion anchor"


def recorded_post_selection_run_members(
    run_root: str | os.PathLike[str],
) -> tuple[str, ...]:
    """Every node path this owner recorded for one run root, or empty.

    Files *and* directories, because the caller uses this to decide what a
    recursive action may make disappear.
    """

    completion, _why = read_post_selection_run_completion(run_root)
    if completion is None:
        return ()
    nodes, _detail = read_post_selection_run_topology(run_root, completion)
    if nodes is None:
        return ()
    return tuple(sorted(item["path"] for item in nodes))


def post_selection_run_is_complete(
    run_root: str | os.PathLike[str],
) -> tuple[bool, str]:
    """Bounded completion authority: does a valid compact anchor exist?

    This is what normal reporting asks.  It deliberately does not prove that the
    tree still contains exactly what P5 recorded - that is the expensive
    question, and consequential planning is the only caller that has to answer
    it - but it is the same completion authority, so a run whose terminal
    evidence has legitimately gone cold is still reported as finished.
    """

    completion, why = read_post_selection_run_completion(run_root)
    return completion is not None, why


def record_post_selection_run_members(run_root: str | os.PathLike[str]) -> Path:
    """Freeze this owner's terminal completion proof, once.

    Publication order is the contract: the terminal evidence is already durable,
    the full topology manifest is published next, and the compact anchor - which
    binds that manifest's identity - is published last and is therefore the
    commit point.  A crash between the two leaves a manifest nothing points at,
    which grants nothing, rather than an anchor pointing at a manifest that does
    not exist.

    It is create-once.  A second terminal publication verifies the existing
    proof; it deliberately does **not** rescan the tree first, because by then
    storage may legitimately have moved represented members into a cold archive
    and a freshly derived set would falsely look like a conflicting claim.
    """

    from .target_size_execution import publish_immutable_json_create_or_verify

    root = Path(run_root)
    anchor_path = root / RUN_COMPLETION_ANCHOR_FILENAME
    terminal = sorted(
        name for name in sorted(RUN_TERMINAL_RECORD_NAMES) if (root / name).is_file()
    )
    existing, why = read_post_selection_run_completion(root)
    if existing is not None:
        # An immutable proof already exists. Verify it and stop; the depleted hot
        # tree is not evidence about what the completed run produced.
        nodes, detail = read_post_selection_run_topology(root, existing)
        if nodes is None:
            raise PostSelectionExecutionError(
                f"Post-selection run {root.name} carries a completion anchor whose "
                f"topology manifest does not authenticate: {detail}"
            )
        return anchor_path
    if anchor_path.is_file():
        raise PostSelectionExecutionError(
            f"Refusing to republish the completion proof of post-selection run "
            f"{root.name}: an anchor is already present but does not validate "
            f"({why}). Completion authority is create-once, so a disagreement is an "
            "integrity conflict rather than an update."
        )
    if not terminal:
        raise PostSelectionExecutionError(
            f"Refusing to record post-selection run completion for {root.name}: no "
            "terminal fold-acceptance or run-evidence record is durable yet. The "
            "completion proof is only ever written downstream of the evidence it "
            "certifies."
        )
    nodes = _run_root_nodes(root)
    topology = _sealed(
        {
            "schema": RUN_TOPOLOGY_MANIFEST_SCHEMA,
            "run_root": root.name,
            "nodes": nodes,
            "node_count": len(nodes),
        }
    )
    try:
        publish_immutable_json_create_or_verify(
            root / RUN_TOPOLOGY_MANIFEST_FILENAME, topology
        )
        publish_immutable_json_create_or_verify(
            anchor_path,
            _sealed(
                {
                    "schema": RUN_COMPLETION_ANCHOR_SCHEMA,
                    "run_root": root.name,
                    "terminal_records": terminal,
                    "topology_locator": RUN_TOPOLOGY_MANIFEST_FILENAME,
                    "topology_digest": topology["content_digest"],
                    "node_count": len(nodes),
                    "file_count": sum(1 for item in nodes if item["kind"] == "file"),
                    "directory_count": sum(
                        1 for item in nodes if item["kind"] == "directory"
                    ),
                }
            ),
        )
    except (TrainingDataInputError, TrainingDataSerializationError) as exc:
        raise PostSelectionExecutionError(
            f"Refusing to rewrite the completion proof of post-selection run "
            f"{root.name}: {exc}. A completed run's member set is create-once owner "
            "authority, so a disagreement is an integrity conflict, not an update."
        ) from exc
    return anchor_path


def certified_post_selection_run_nodes(
    run_root: str | os.PathLike[str],
) -> tuple[tuple[str, str], ...]:
    """Every ``(path, kind)`` this owner recorded for one run root, or empty."""

    completion, _why = read_post_selection_run_completion(run_root)
    if completion is None:
        return ()
    nodes, _detail = read_post_selection_run_topology(run_root, completion)
    if nodes is None:
        return ()
    return tuple(sorted((item["path"], item["kind"]) for item in nodes))


def certify_closed_post_selection_run_root(
    run_root: str | os.PathLike[str],
) -> tuple[bool, str]:
    """Whether P5 certifies every descendant of one run root as its own.

    Two things must hold. The run must be finished, and every traversable node
    on disk - file *and* directory - must belong to the topology P5 recorded when
    it finished. The second condition is what turns "beneath a P5 directory" into
    "produced by P5": a file dropped into ``checkpoints/`` by anything else, or
    an empty directory nobody recorded, is not in the manifest and makes the
    whole run root uncertified.

    Completion is proved by the retained anchor, deliberately *not* by finding
    the terminal fold-acceptance/run-evidence file still hot. That file is an
    ordinary archive member: an interrupted cold reclamation may already have
    removed it while other represented members are still hot, and requiring it
    here would leave that reclamation unable to finish on the next process.
    """

    from .storage.owners import NODE_DIRECTORY, observed_node_kind

    root = Path(run_root)
    if observed_node_kind(root) != NODE_DIRECTORY:
        return False, f"{root} is not a plain directory"
    # There is deliberately no pathname allowlist here. The run directory is
    # delegated to the configured trainer, which writes its own layout inside it
    # (per-epoch metric logs, framework results/logs trees, and so on). Guessing
    # that layout is exactly the pathname inference this certification exists to
    # replace; the recorded topology below is the owner's own answer.
    completion, why = read_post_selection_run_completion(root)
    if completion is None:
        return False, why
    nodes, detail = read_post_selection_run_topology(root, completion)
    if nodes is None:
        return False, detail
    recorded = {item["path"]: item["kind"] for item in nodes}
    contradictions: list[str] = []
    for item in _observe_run_root_nodes(root):
        expected = recorded.get(item["path"])
        if expected is None:
            contradictions.append(f"{item['path']} ({item['kind']} P5 did not write)")
        elif expected != item["kind"]:
            contradictions.append(
                f"{item['path']} (recorded {expected}, found {item['kind']})"
            )
    if contradictions:
        return False, (
            "run root contains descendant(s) P5 did not write: "
            f"{contradictions[:5]}"
        )
    # A recorded node that is *absent* means content has legitimately left the
    # tree - reclaimed into a cold archive, for instance. The guarantee this
    # certification makes is that nothing foreign is present, not that nothing
    # has been removed.
    return True, (
        "terminal run whose descendants all belong to the topology P5 recorded "
        f"when it published {', '.join(completion.terminal_records)}"
    )


def _completed_fold_acceptance(
    context: PostSelectionContext, run_plan: Any
) -> CvFoldAcceptance | None:
    """Reuse a completed fold on restart, after re-checking what it binds.

    An interrupted cross-validation must not retrain folds that already
    finished - with real MACE that is the difference between resuming and
    starting over. Reuse is still conditional: the stored acceptance must belong
    to this exact run plan and must have been judged under the current
    acceptance predicate, or it is not evidence about the campaign being run now.
    """

    path = context.run_root(run_plan.run_identity) / FOLD_ACCEPTANCE_FILENAME
    if not path.is_file():
        return None
    acceptance = CvFoldAcceptance.from_dict(
        json.loads(path.read_text(encoding="utf-8"))
    )
    policy = context.cv_policy
    if (
        acceptance.run_plan_digest != run_plan.content_digest
        or acceptance.cv_plan_digest != run_plan.cv_plan_digest
        or acceptance.acceptance_metric != policy.acceptance_metric
        or acceptance.acceptance_maximum != policy.acceptance_maximum
    ):
        raise PostSelectionError(
            f"Stored evidence for cross-validation run "
            f"{run_plan.run_identity[:12]}... does not belong to the current plan or "
            "acceptance predicate. Post-selection evidence is never reinterpreted "
            "under a changed policy."
        )
    return acceptance


def _record_completed_fold_acceptance(
    context: PostSelectionContext, run_plan: Any, acceptance: CvFoldAcceptance
) -> None:
    from .target_size_execution import publish_immutable_json_create_or_verify

    run_root = context.run_root(run_plan.run_identity)
    publish_immutable_json_create_or_verify(
        run_root / FOLD_ACCEPTANCE_FILENAME,
        acceptance.to_dict(),
        deserializer=CvFoldAcceptance.from_dict,
    )
    record_post_selection_run_members(run_root)


def _completed_run_evidence(
    context: PostSelectionContext, run_plan: Any
) -> PostSelectionRunEvidence | None:
    """Reuse a completed final-production job on restart."""

    path = context.run_root(run_plan.run_identity) / RUN_EVIDENCE_FILENAME
    if not path.is_file():
        return None
    evidence = PostSelectionRunEvidence.from_dict(
        json.loads(path.read_text(encoding="utf-8"))
    )
    if evidence.run_plan_digest != run_plan.content_digest:
        raise PostSelectionError(
            f"Stored evidence for production run {run_plan.run_identity[:12]}... "
            "belongs to a different run plan."
        )
    return evidence


def _record_completed_run_evidence(
    context: PostSelectionContext, run_plan: Any, evidence: PostSelectionRunEvidence
) -> None:
    from .target_size_execution import publish_immutable_json_create_or_verify

    run_root = context.run_root(run_plan.run_identity)
    publish_immutable_json_create_or_verify(
        run_root / RUN_EVIDENCE_FILENAME,
        evidence.to_dict(),
        deserializer=PostSelectionRunEvidence.from_dict,
    )
    record_post_selection_run_members(run_root)


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _PendingPostSelectionRun:
    """One exact pending CV/final slot admitted to the shared scheduler."""

    slot: int
    run_plan: Any
    training_frame_uids: tuple[str, ...]
    monitor_frame_uids: tuple[str, ...]
    outer_evaluation_frame_uids: tuple[str, ...] | None
    progress_context: Mapping[str, Any]


def _post_selection_training_concurrency_policy(
    context: PostSelectionContext,
) -> Any:
    """Resolve the existing runtime-only adaptive training policy from config."""

    from ._campaign_cli_core import _cfg
    from .training_parallel import TrainingConcurrencyPolicy

    return TrainingConcurrencyPolicy(
        requested_jobs=int(_cfg(context.cfg, "execution", "parallel_training_jobs", 0)),
        minimum_auto_jobs=int(
            _cfg(context.cfg, "execution", "minimum_parallel_training_jobs", 1)
        ),
        maximum_auto_jobs=int(
            _cfg(context.cfg, "execution", "maximum_parallel_training_jobs", 4)
        ),
        gpu_memory_fraction=float(
            _cfg(context.cfg, "execution", "training_gpu_memory_fraction", 0.90)
        ),
        gpu_utilization_fraction=float(
            _cfg(context.cfg, "execution", "training_gpu_utilization_fraction", 0.90)
        ),
        estimated_gpu_memory_mib_per_job=float(
            _cfg(
                context.cfg,
                "execution",
                "estimated_training_vram_mib_per_job",
                6144.0,
            )
        ),
        estimated_ram_mib_per_job=float(
            _cfg(
                context.cfg,
                "execution",
                "estimated_training_ram_mib_per_job",
                8192.0,
            )
        ),
        epoch_stabilization_seconds=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_epoch_stabilization_seconds",
                60.0,
            )
        ),
        stability_samples=int(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_epoch_stability_samples",
                12,
            )
        ),
        stability_relative_tolerance=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_stability_relative_tolerance",
                0.10,
            )
        ),
        utilization_stability_absolute_tolerance=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_utilization_stability_absolute_tolerance",
                8.0,
            )
        ),
        observed_memory_growth_margin=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_memory_growth_margin",
                1.05,
            )
        ),
        observed_utilization_growth_margin=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_utilization_growth_margin",
                1.05,
            )
        ),
        monitor_interval_seconds=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_monitor_interval_seconds",
                10.0,
            )
        ),
        epoch_activity_timeout_seconds=float(
            _cfg(
                context.cfg,
                "execution",
                "parallel_training_epoch_activity_timeout_seconds",
                120.0,
            )
        ),
    )


def _report_post_selection_gpu_occupancy(
    stage: str, device: str, sample: Any
) -> None:
    """Print one aggregate GPU occupancy observation at a named boundary.

    Aggregate occupancy is authoritative for admission regardless of which
    process owns it. This is diagnostics only and carries no completion or
    scientific authority.
    """

    if not str(device).startswith("cuda"):
        return
    observed = (
        "unavailable"
        if sample is None
        else str(sample.summary()).replace(";", ",")
    )
    print(f"[TRAIN scheduler] occupancy at {stage}: {observed}", flush=True)


def _preflight_post_selection_pending_runs(
    context: PostSelectionContext,
    *,
    pending: Sequence[_PendingPostSelectionRun],
    budget_policy: Any,
) -> None:
    """Reject durable foreign continuations before any sibling reaches EVAL2."""

    for task in sorted(pending, key=lambda item: int(item.slot)):
        run_root = context.run_root(task.run_plan.run_identity)
        checkpoint_directory = run_root / "checkpoints"
        if not checkpoint_directory.exists() and not checkpoint_directory.is_symlink():
            continue
        if (
            checkpoint_directory.is_dir()
            and not _checkpoint_has_durable_entries(checkpoint_directory)
        ):
            continue
        # Use the exact same setup/authentication owner as execution. Holding
        # the existing activity lease makes this read-only classification safe
        # against another P5 process while keeping it free of publication or
        # replacement side effects.
        with post_selection_run_activity_lease(run_root):
            _prepare_post_selection_run(
                context,
                run_plan=task.run_plan,
                budget_policy=budget_policy,
                training_frame_uids=task.training_frame_uids,
                monitor_frame_uids=task.monitor_frame_uids,
                outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
            )


def _execute_post_selection_pending_runs(
    context: PostSelectionContext,
    *,
    pending: Sequence[_PendingPostSelectionRun],
    budget_policy: Any,
) -> dict[int, tuple[PostSelectionRunEvidence, Any, Any]]:
    """Run exact pending slots through the existing adaptive controller.

    The caller constructs ``pending`` only after it has materialized every
    canonical run plan and classified reusable evidence. This function owns
    admission and supervision, but it never reorders or ranks the returned
    scientific evidence: callers reduce results by the frozen slot number.

    One scheduler slot corresponds to TRAIN2 ownership only. Post-TRAIN EVAL2
    runs afterwards through the same run path, so a fold entering EVAL2 can
    never hold accelerator memory while an independently admitted TRAIN2 child
    is still active, and the scheduler's VRAM telemetry window describes TRAIN2
    rather than a mixed TRAIN/EVAL phase.
    """

    if not pending:
        return {}

    from collections import deque
    from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED, ThreadPoolExecutor, wait
    import threading
    import time

    from ._campaign_cli_core import _cfg, _performance_resources
    from .progress_timing import ProgressRateTracker, format_progress_fraction, format_progress_timing_fields
    from .training_parallel import (
        AdaptiveTrainingConcurrency,
        TrainingAdmissionBlockedError,
        TrainingMemorySafetyError,
        TrainingResourceObservabilityError,
        build_training_concurrency_plan,
        query_gpu_telemetry,
    )

    ordered_pending = tuple(sorted(pending, key=lambda item: int(item.slot)))
    device = str(context.method_policies.device)
    # Bind the admission baseline to the recovery preflight that precedes it.
    # Recovery classification can realize a CUDA training model, so the two
    # observations make any parent-side contribution to the baseline visible
    # instead of silently inflating the envelope TRAIN2 is measured against.
    _report_post_selection_gpu_occupancy(
        "pre-recovery-preflight", device, query_gpu_telemetry(device)
    )
    _preflight_post_selection_pending_runs(
        context,
        pending=ordered_pending,
        budget_policy=budget_policy,
    )
    first_policy = _optimizer_policy_for(
        context,
        seed=ordered_pending[0].run_plan.optimizer_seed,
        planned_epochs=ordered_pending[0].run_plan.planned_epochs,
    )
    resources = _performance_resources(context.cfg)
    concurrency_policy = _post_selection_training_concurrency_policy(context)
    # This is both the post-preflight observation and the authoritative TRAIN
    # admission baseline; they are the same instant by construction.
    initial_sample = query_gpu_telemetry(device)
    _report_post_selection_gpu_occupancy(
        "post-recovery-preflight TRAIN admission", device, initial_sample
    )
    concurrency_plan = build_training_concurrency_plan(
        task_count=len(ordered_pending),
        device=device,
        loader_workers_per_job=int(getattr(first_policy, "num_workers", 0)),
        resources=resources,
        policy=concurrency_policy,
        gpu_sample=initial_sample,
    )
    controller = AdaptiveTrainingConcurrency(concurrency_plan, concurrency_policy)
    # The execution owner states its own observe-stop/terminate/reap bound; the
    # scheduler never derives one, so an outer barrier cannot expire before the
    # termination path it already authorized. An owner that declares none keeps
    # sole authority over its stop duration and the barrier stays unbounded.
    teardown_bound = getattr(context.trainer, "cancellation_teardown_seconds", None)
    teardown_bound = None if teardown_bound is None else float(teardown_bound)
    telemetry_ref: dict[str, Any] = {"sample": initial_sample}
    # One cooperative stop signal per admitted slot. Backoff sets exactly one of
    # them; a terminal abort sets every one of them, which *is* the whole-wave
    # cancellation. A single shared event could not express "stop exactly one
    # owned job", and a second parallel mechanism for the wave would only
    # duplicate this one.
    stop_events: dict[int, threading.Event] = {}
    state_lock = threading.Lock()
    states: dict[int, dict[str, Any]] = {
        task.slot: {
            "completed_updates": 0,
            "completed_epochs": 0,
            "true_epoch": False,
            # ``phase`` is child-reported MACE execution state only. The
            # active-future mapping below is the scheduler's liveness owner;
            # submission/completion must not overwrite this observation field.
            "phase": "launching",
        }
        for task in ordered_pending
    }
    started = time.monotonic()
    outer_tracker = ProgressRateTracker(completed=0, started_at=started)
    completed_count = 0
    failed_count = 0
    # Restartable pending work. A memory-pressure demotion returns its task
    # here; it is neither a completion nor a scientific failure.
    pending_queue: Deque[_PendingPostSelectionRun] = deque(ordered_pending)
    # Insertion-ordered by construction, so the last key is the most recently
    # admitted currently active owned job - the deterministic backoff victim.
    active: dict[Any, _PendingPostSelectionRun] = {}
    trained_slots: list[int] = []
    last_sample_at = started
    last_report_at: float | None = None
    last_decision_reason = "initial one-job admission"
    # Set from the last control observation: admission stops on any unsafe or
    # unobservable aggregate-memory state, including while nothing is owned.
    admission_blocked = False
    visible_interval = max(
        0.05,
        float(
            _cfg(
                context.cfg,
                "execution",
                "training_progress_interval_seconds",
                10.0,
            )
        ),
    )
    poll_interval = min(
        1.0,
        max(0.05, float(concurrency_policy.monitor_interval_seconds) / 4.0),
    )

    def report(status: str, *, force: bool = False) -> None:
        nonlocal last_report_at
        now = time.monotonic()
        if (
            not force
            and last_report_at is not None
            and now - last_report_at < visible_interval
        ):
            return
        with state_lock:
            active_count = len(active)
            true_epoch_count = sum(
                bool(states[task.slot].get("true_epoch"))
                for task in active.values()
            )
        snapshot = outer_tracker.snapshot(
            completed=completed_count,
            total=len(ordered_pending),
            now=now,
        )
        sample = telemetry_ref.get("sample")
        if sample is None:
            gpu_fields = ("gpu=unavailable", "vram=unavailable")
        else:
            gpu_fields = (
                f"gpu={float(getattr(sample, 'utilization_percent', 0.0)):.0f}%",
                f"vram={int(getattr(sample, 'used_bytes', 0)) / 1024**3:.1f}/"
                f"{int(getattr(sample, 'total_bytes', 0)) / 1024**3:.1f}GiB",
            )
        plan_summary = concurrency_plan.summary().replace(";", ",")
        timing = format_progress_timing_fields(
            elapsed_seconds=snapshot.elapsed_seconds,
            eta_seconds=snapshot.eta_seconds,
            recent_rate=snapshot.recent_rate,
            average_rate=snapshot.average_rate,
            rate_unit="training-run/s",
        )
        line = "; ".join(
            (
                f"[TRAIN scheduler] status={status}",
                f"progress={format_progress_fraction(completed_count, len(ordered_pending))}",
                "unit=training-run",
                f"active_jobs={active_count}",
                f"true_epoch_jobs={true_epoch_count}",
                f"target_jobs={controller.target_jobs}",
                f"ceiling={concurrency_plan.maximum_jobs}",
                f"effective_ceiling={controller.effective_ceiling}",
                # Counted from actual scheduler ownership: a submitted slot that
                # already failed is never reported as still queued, and a
                # demoted slot is queued again rather than counted as failed.
                f"queued_jobs={len(pending_queue)}",
                f"completed_jobs={completed_count}",
                f"failed_jobs={failed_count}",
                timing,
                *gpu_fields,
                f"plan={plan_summary}",
                f"last_decision={last_decision_reason.replace(';', ',')}",
            )
        )
        print(line, flush=True)
        last_report_at = now

    def submit_available(executor: ThreadPoolExecutor) -> None:
        if admission_blocked:
            # The last control observation was over the envelope or blind. No
            # new accelerator work is admitted until a trustworthy safe
            # observation returns; the controller decides whether the condition
            # is transient or terminal.
            return
        # A zero target is a truthful resource state, not a value to floor.
        target = max(0, int(controller.target_jobs))
        while pending_queue and len(active) < target:
            task = pending_queue.popleft()
            with state_lock:
                # A restarted slot re-earns its own liveness observations; the
                # dead attempt's must not be read as current epoch activity.
                states[task.slot].update({"true_epoch": False, "phase": "launching"})
            stop_event = threading.Event()
            stop_events[task.slot] = stop_event

            def observe(
                observation: Mapping[str, Any],
                *,
                slot: int = task.slot,
            ) -> None:
                with state_lock:
                    states[slot].update(dict(observation))

            future = executor.submit(
                execute_post_selection_run,
                context,
                run_plan=task.run_plan,
                budget_policy=budget_policy,
                training_frame_uids=task.training_frame_uids,
                monitor_frame_uids=task.monitor_frame_uids,
                outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
                progress_context=task.progress_context,
                cancellation_event=stop_event,
                progress_observer=observe,
                telemetry_ref=telemetry_ref,
                stop_after_training=True,
            )
            active[future] = task

    def demote_most_recently_admitted(pre_sample: Any) -> None:
        """Retract one prior admission and prove its resource lifetime is gone.

        Reverse-most-recent-promotion: ``active`` is insertion-ordered by
        admission, so the last key is the victim. A resource demotion is not a
        scientific failure - the task returns to the pending/restartable queue
        with its frozen slot identity and resumes later through the existing
        checkpoint/continuation authority - so it never increments the failed
        count and never publishes partial evidence.

        What makes an outcome a demotion is the execution owner's explicit
        cancellation result, never this scheduler's intent: a victim that
        instead failed on its own authority stays a failure.

        The scheduler blocks here until the owned worker has actually returned.
        A future cancellation request is not CUDA teardown: only the worker's
        own completion establishes that the child process exited and its
        finalization ran, so no replacement admission or restart can be ordered
        before that boundary. How long that is allowed to take belongs to the
        execution owner's termination contract, not to any control-loop or
        liveness cadence.
        """

        nonlocal completed_count, failed_count, last_decision_reason
        victim_future = next(reversed(active))
        victim = active[victim_future]
        before = len(active)
        used_text = (
            "unavailable"
            if pre_sample is None
            else f"{int(getattr(pre_sample, 'used_bytes', 0)) / 1024**3:.1f} GiB"
        )
        last_decision_reason = (
            f"backoff {before}->{before - 1}: aggregate VRAM {used_text} remained "
            f"above the soft training envelope; demoting most recently admitted "
            f"slot={victim.slot}"
        )
        print(
            f"[TRAIN scheduler] backoff {before}->{before - 1}; slot={victim.slot}; "
            f"pre-demotion VRAM={used_text}; "
            f"effective_ceiling={controller.effective_ceiling}",
            flush=True,
        )
        stop_events[victim.slot].set()
        # Bounded only by the execution owner's own declared termination
        # contract, which is the authority for how long its terminate/reap
        # sequence may legitimately take. Expiry therefore means owned TRAIN2
        # lifetime cleanup itself failed and no safe owned execution state can
        # be re-established.
        _done, not_done = wait(
            (victim_future,),
            timeout=teardown_bound,
            return_when=ALL_COMPLETED,
        )
        if not_done:
            raise TrainingMemorySafetyError(
                f"Owned TRAIN2 slot {victim.slot} did not quiesce within the "
                f"execution owner's own {teardown_bound:.1f}s child "
                "termination/reaping bound after its demotion request, so its "
                "accelerator lifetime cannot be confirmed released and no safe "
                "owned execution state can be re-established."
            )
        active.pop(victim_future, None)
        stop_events.pop(victim.slot, None)
        with state_lock:
            states[victim.slot].update({"true_epoch": False, "phase": "demoted"})
        error = victim_future.exception()
        if error is not None and not isinstance(error, PostSelectionCancelledError):
            # Asking a job to stop is not evidence that it raised *because* it
            # was asked. Only the execution owner's explicit cancellation
            # outcome is retractable resource work; a backend fault, a MACE
            # nonzero exit, a CUDA failure, an interrupt or a programmer error
            # that races the request keeps its own authority and escapes into
            # the existing terminal path instead of being requeued. It is
            # counted exactly as any other owned-job failure would be.
            failed_count += 1
            raise error
        if error is None:
            # The worker reached its authenticated TRAIN2 summary before it
            # observed the stop. That slot is genuinely done; requeueing it
            # would duplicate completed work.
            trained_slots.append(victim.slot)
            completed_count += 1
            outcome = "completed before stopping"
        else:
            pending_queue.appendleft(victim)
            outcome = "returned to the pending/restartable queue"
        post_sample = query_gpu_telemetry(device)
        telemetry_ref["sample"] = post_sample
        _report_post_selection_gpu_occupancy(
            f"post-demotion slot={victim.slot} teardown", device, post_sample
        )
        print(
            f"[TRAIN scheduler] slot={victim.slot} worker teardown observed; "
            f"{outcome}",
            flush=True,
        )

    def complete_eval2_for_trained_slots() -> dict[
        int, tuple[PostSelectionRunEvidence, Any, Any]
    ]:
        """Finish every authenticated TRAIN2 slot through the same run path.

        Every TRAIN2 child has exited and released the device before this runs.
        The authenticated TRAIN2 summary lets the existing continuation logic
        skip retraining, so no second scheduler, lease, or handoff record is
        involved, and each run reaches its own durable publication boundary in
        frozen slot order. This runs only after the whole TRAIN wave succeeded:
        a failed wave raises before any post-TRAIN evaluation begins.
        """

        completed: dict[int, tuple[PostSelectionRunEvidence, Any, Any]] = {}
        if not trained_slots:
            return completed
        _report_post_selection_gpu_occupancy(
            "post-TRAIN EVAL2 entry", device, query_gpu_telemetry(device)
        )
        by_slot = {int(task.slot): task for task in ordered_pending}
        ordered_slots = sorted(trained_slots)
        for index, slot in enumerate(ordered_slots):
            task = by_slot[slot]
            print(
                f"[EVAL2 serial] status=running; "
                f"progress={format_progress_fraction(index, len(ordered_slots))}; "
                f"unit=training-run; slot={slot}",
                flush=True,
            )
            result = execute_post_selection_run(
                context,
                run_plan=task.run_plan,
                budget_policy=budget_policy,
                training_frame_uids=task.training_frame_uids,
                monitor_frame_uids=task.monitor_frame_uids,
                outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
                progress_context=task.progress_context,
                telemetry_ref=telemetry_ref,
            )
            if result is None:
                raise PostSelectionExecutionError(
                    "Post-TRAIN EVAL2 returned no bound evidence for slot "
                    f"{slot}; the authenticated TRAIN2 continuation is unusable."
                )
            completed[slot] = result
        print(
            f"[EVAL2 serial] status=completed; "
            f"progress={format_progress_fraction(len(ordered_slots), len(ordered_slots))}; "
            "unit=training-run",
            flush=True,
        )
        return completed

    executor = ThreadPoolExecutor(
        max_workers=max(1, int(concurrency_plan.maximum_jobs)),
        thread_name_prefix="mdstats-p5-train",
    )
    report("planned", force=True)
    try:
        submit_available(executor)
        report("running", force=True)
        while active or pending_queue:
            if (
                not active
                and pending_queue
                and int(controller.target_jobs) < 1
            ):
                # Pending work with an idle queue and no feasible slot is a
                # terminal resource state; busy-waiting would hide it.
                raise TrainingAdmissionBlockedError(
                    f"{len(pending_queue)} pending TRAIN2 job(s) "
                    "remain but no job is currently resource-admissible: "
                    f"{concurrency_plan.summary()}"
                )
            if active:
                done, _ = wait(
                    tuple(active),
                    timeout=poll_interval,
                    return_when=FIRST_COMPLETED,
                )
            else:
                done = set()
                if admission_blocked and pending_queue:
                    time.sleep(poll_interval)
            first_failure: BaseException | None = None
            for future in done:
                task = active.pop(future)
                stop_events.pop(task.slot, None)
                try:
                    future.result()
                    trained_slots.append(task.slot)
                    completed_count += 1
                except BaseException as exc:
                    failed_count += 1
                    if first_failure is None:
                        first_failure = exc
            if first_failure is not None:
                raise first_failure

            now = time.monotonic()
            if now - last_sample_at >= float(concurrency_policy.monitor_interval_seconds):
                sample = query_gpu_telemetry(device)
                telemetry_ref["sample"] = sample
                with state_lock:
                    active_count = len(active)
                    true_epoch_count = sum(
                        bool(states[task.slot].get("true_epoch"))
                        for task in active.values()
                    )
                decision = controller.observe(
                    sample,
                    active_jobs=active_count,
                    epoch_active_jobs=true_epoch_count,
                    now=now,
                )
                last_decision_reason = decision.reason
                admission_blocked = (
                    decision.memory_safe is not True
                    if concurrency_plan.gpu_memory_budget_bytes is not None
                    else False
                )
                last_sample_at = now
                if decision.memory_backoff and active:
                    # Sustained soft-envelope pressure above the minimum owned
                    # concurrency. The controller has already closed this level;
                    # the scheduler retracts exactly one prior admission and
                    # reclaims it before any further scheduling decision.
                    demote_most_recently_admitted(sample)
                    report("running", force=True)
                    continue
                if decision.memory_hazard:
                    # A resource stop before CUDA exhausts the device, routed
                    # through the existing cancellation/reaping path. An unknown
                    # ``memory_safe`` means the live observation itself was lost,
                    # which is the observability failure rather than an observed
                    # envelope violation.
                    if decision.memory_safe is None:
                        raise TrainingResourceObservabilityError(
                            "Stopping owned TRAIN2 execution because live GPU "
                            f"memory safety is unobservable: {decision.reason}"
                        )
                    raise TrainingMemorySafetyError(
                        "Stopping owned TRAIN2 execution before CUDA out of "
                        f"memory: {decision.reason}"
                    )

            submit_available(executor)
            report("running", force=bool(done))
            if not done and active:
                report("running")
        report("training-completed", force=True)
    except BaseException as exc:
        # Terminal/global abort: signal every owned child, not one victim.
        for event in stop_events.values():
            event.set()
        for future in active:
            future.cancel()
        report(
            "cancelled"
            if isinstance(exc, (KeyboardInterrupt, SystemExit))
            else "failed",
            force=True,
        )
        executor.shutdown(wait=True, cancel_futures=True)
        # A failed TRAIN wave ends this invocation. Owned children have been
        # signalled and reaped above, and no fresh accelerator work may begin on
        # a device whose TRAIN2 state is unknown or already unsafe. Progress is
        # not lost: every authenticated TRAIN2 summary is durable, so the next
        # healthy invocation resumes outstanding TRAIN2/EVAL2 work through the
        # ordinary continuation path instead of a same-invocation sibling EVAL2.
        raise
    executor.shutdown(wait=True, cancel_futures=True)
    return complete_eval2_for_trained_slots()


def execute_post_selection_cross_validation(
    context: PostSelectionContext,
) -> tuple[PostSelectionCvPlan, CvCampaignAcceptance]:
    """Build, execute, and accept the complete selected-only cross-validation.

    A rerun of the same plan is a resume: fold evidence is content-addressed and
    reused when it already exists, and the current selected binding is
    re-authenticated before any of it is trusted.
    """

    selected = context.selected
    projection = build_selected_relation_projection(selected)
    admissibility = context.method_policies.checkpoint_admissibility
    replay_resolution = None
    if admissibility.replay_enabled:
        replay_resolution = _resolve_post_selection_replay_resolution(
            context, require_train=True
        )
    replay_lineage_digest = (
        compute_replay_lineage_digest(replay_resolution)
        if admissibility.replay_enabled
        else None
    )
    plan = build_post_selection_cv_plan(
        selected,
        context.method,
        context.cv_policy,
        projection=projection,
        replay_lineage_digest=replay_lineage_digest,
    )
    store = context.evidence_store
    # The policy identities are persisted as records, not just as digests, so a
    # later reader can reproduce exactly which resolved configuration authorized
    # this campaign without re-reading a possibly edited campaign.toml.  The
    # object publications and the pointer that makes one of them current share
    # the owner's publication barrier, so a concurrent storage mutation cannot
    # observe the object-before-pointer window half-open.
    with post_selection_publication_barrier(
        context.paths, selected.binding.campaign_generation
    ):
        store.put(context.method)
        store.put(context.cv_policy)
        store.put(projection)
        store.put(plan)
        publish_current_post_selection_pointer(
            context.store,
            binding=selected.binding,
            kind=POINTER_CV_PLAN,
            content_digest=plan.content_digest,
        )

    budget_policy = cv_training_budget_policy(context.method, context.cv_policy)
    acceptances_by_slot: dict[int, CvFoldAcceptance] = {}
    pending: list[_PendingPostSelectionRun] = []
    required_runs = tuple(plan.required_run_matrix)
    total_runs = len(required_runs)
    for slot, (seed, fold_index) in enumerate(required_runs):
        fold = plan.fold(fold_index)
        run_plan = build_cv_fold_run_plan(
            plan,
            fold_index=fold_index,
            optimizer_seed=seed,
            planned_epochs=context.cv_policy.cv_max_num_epochs,
        )
        store.put(run_plan)
        completed = _completed_fold_acceptance(context, run_plan)
        if completed is not None:
            acceptances_by_slot[slot] = completed
            print(
                "[TRAIN] status=reused; "
                f"N_selected={selected.n_selected}; run={slot + 1}/{total_runs}; "
                f"seed={seed}; fold={fold_index + 1}/{plan.fold_count}; "
                "restored=reused; phase=reused",
                flush=True,
            )
            continue
        pending.append(
            _PendingPostSelectionRun(
                slot=slot,
                run_plan=run_plan,
                training_frame_uids=tuple(fold.training_frame_uids),
                monitor_frame_uids=tuple(fold.checkpoint_monitor_frame_uids),
                outer_evaluation_frame_uids=tuple(fold.outer_evaluation_frame_uids),
                progress_context={
                    "N_selected": selected.n_selected,
                    "run": f"{slot + 1}/{total_runs}",
                    "seed": seed,
                    "fold": f"{fold_index + 1}/{plan.fold_count}",
                    "restored": "executing",
                    "phase": "executing",
                },
            )
        )

    results = _execute_post_selection_pending_runs(
        context,
        pending=pending,
        budget_policy=budget_policy,
    )
    for task in pending:
        _evidence, representative, outer_metrics = results[task.slot]
        if outer_metrics is None:
            raise PostSelectionError(
                f"CV fold {task.run_plan.fold_index} produced no held-out outer evaluation."
            )
        acceptance = build_cv_fold_acceptance(
            run_plan=task.run_plan,
            representative=representative,
            outer_metrics=outer_metrics,
            policy=context.cv_policy,
        )
        store.put(acceptance)
        _record_completed_fold_acceptance(context, task.run_plan, acceptance)
        acceptances_by_slot[task.slot] = acceptance

    acceptances = [acceptances_by_slot[slot] for slot in range(total_runs)]

    campaign = accept_post_selection_cv_campaign(plan, context.cv_policy, acceptances)
    with post_selection_publication_barrier(
        context.paths, selected.binding.campaign_generation
    ):
        store.put(campaign)
        publish_current_post_selection_pointer(
            context.store,
            binding=selected.binding,
            kind=POINTER_CV_ACCEPTANCE,
            content_digest=campaign.content_digest,
        )
    return plan, campaign


def resolve_current_cv_plan(context: PostSelectionContext) -> PostSelectionCvPlan | None:
    plan = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_CV_PLAN,
        deserializer=PostSelectionCvPlan.from_dict,
    )
    if plan is not None:
        admissibility = context.method_policies.checkpoint_admissibility
        replay_resolution = None
        if admissibility.replay_enabled:
            replay_resolution = _resolve_post_selection_replay_resolution(
                context, require_train=True
            )
        replay_lineage_digest = (
            compute_replay_lineage_digest(replay_resolution)
            if admissibility.replay_enabled
            else None
        )
        validate_post_selection_cv_plan(
            plan,
            context.selected,
            replay_lineage_digest=replay_lineage_digest,
        )
        if plan.method_identity_digest != context.method.content_digest:
            raise PostSelectionError(
                "The stored CV plan validated a different training method "
                f"({plan.method_identity_digest[:12]}...) than current authority resolves "
                f"({context.method.content_digest[:12]}...). Run `cross-validate` to validate "
                "the current method."
            )
        if plan.cv_policy_identity_digest != context.cv_policy.content_digest:
            raise PostSelectionError(
                "The stored CV plan used a different cross-validation policy "
                f"({plan.cv_policy_identity_digest[:12]}...) than current authority resolves "
                f"({context.cv_policy.content_digest[:12]}...). Run `cross-validate` to validate "
                "under the current policy."
            )
    return plan


def resolve_current_cv_acceptance(
    context: PostSelectionContext,
) -> CvCampaignAcceptance | None:
    return resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_CV_ACCEPTANCE,
        deserializer=CvCampaignAcceptance.from_dict,
    )


# ---------------------------------------------------------------------------
# Fresh final production
# ---------------------------------------------------------------------------


def execute_final_production(
    context: PostSelectionContext,
) -> tuple[
    FinalProductionPlan,
    tuple[PostSelectionRunEvidence, ...],
    "FinalProductionPublicationDecision",
]:
    """Authorize and run fresh full-``T_selected`` production.

    Authorization is checked before any bytes are written: a missing, stale, or
    method-mismatched cross-validation stops the command here rather than after
    it has produced a model that looks legitimate.
    """

    selected = context.selected
    plan = resolve_current_cv_plan(context)
    acceptance = resolve_current_cv_acceptance(context)
    if plan is None or acceptance is None:
        raise PostSelectionError(
            "Final production requires a current accepted post-selection "
            "cross-validation of this exact method. Run `cross-validate` first; "
            "there is no production path that skips methodological validation."
        )
    require_cv_acceptance_for_method(
        acceptance,
        plan=plan,
        method_identity_digest=context.method.content_digest,
        selected_binding_digest=selected.binding.content_digest,
    )
    admissibility = context.method_policies.checkpoint_admissibility
    replay_resolution = None
    if admissibility.replay_enabled:
        replay_resolution = _resolve_post_selection_replay_resolution(
            context, require_train=True
        )
    replay_lineage_digest = (
        compute_replay_lineage_digest(replay_resolution)
        if admissibility.replay_enabled
        else None
    )
    final_plan = build_final_production_plan(
        selected,
        context.method,
        context.production_policy,
        cv_plan=plan,
        cv_acceptance=acceptance,
        replay_lineage_digest=replay_lineage_digest,
    )
    validate_final_production_plan(
        final_plan,
        selected,
        method=context.method,
        policy=context.production_policy,
        replay_lineage_digest=replay_lineage_digest,
    )
    store = context.evidence_store
    with post_selection_publication_barrier(
        context.paths, selected.binding.campaign_generation
    ):
        store.put(context.method)
        store.put(context.production_policy)
        store.put(final_plan)
        publish_current_post_selection_pointer(
            context.store,
            binding=selected.binding,
            kind=POINTER_FINAL_PLAN,
            content_digest=final_plan.content_digest,
        )

    _m3_size, m3_membership, _m3_digest = frozen_m3_development_evidence(selected)
    budget_policy = final_production_training_budget_policy(
        context.method, context.production_policy
    )
    evidence_by_slot: dict[int, PostSelectionRunEvidence] = {}
    pending: list[_PendingPostSelectionRun] = []
    required_seeds = tuple(final_plan.required_final_seeds)
    total_runs = len(required_seeds)
    for slot, seed in enumerate(required_seeds):
        run_plan = build_final_production_run_plan(final_plan, optimizer_seed=seed)
        store.put(run_plan)
        completed = _completed_run_evidence(context, run_plan)
        if completed is not None:
            evidence_by_slot[slot] = completed
            print(
                "[TRAIN] status=reused; "
                f"N_selected={selected.n_selected}; run={slot + 1}/{total_runs}; "
                f"seed={seed}; restored=reused; phase=reused",
                flush=True,
            )
            continue
        pending.append(
            _PendingPostSelectionRun(
                slot=slot,
                run_plan=run_plan,
                training_frame_uids=tuple(selected.selected_membership),
                monitor_frame_uids=tuple(m3_membership),
                outer_evaluation_frame_uids=None,
                progress_context={
                    "N_selected": selected.n_selected,
                    "run": f"{slot + 1}/{total_runs}",
                    "seed": seed,
                    "restored": "executing",
                    "phase": "executing",
                },
            )
        )

    results = _execute_post_selection_pending_runs(
        context,
        pending=pending,
        budget_policy=budget_policy,
    )
    for task in pending:
        run_evidence, _representative, _outer = results[task.slot]
        evidence_by_slot[task.slot] = run_evidence

    evidence = [evidence_by_slot[slot] for slot in range(total_runs)]

    # Deciding which of the completed seeds constitute the released product is
    # the last pre-qualification act, and it belongs here: every input it uses
    # already exists, and no downstream release evidence does yet.  Taking the
    # decision any later would let release evidence choose the product.
    completion = FinalProductionCompletion(plan=final_plan, runs=tuple(evidence))
    decision = publish_final_production_publication(context, context.store, completion)
    return final_plan, tuple(evidence), decision


def resolve_current_final_production_plan(
    context: PostSelectionContext,
) -> FinalProductionPlan | None:
    plan = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_FINAL_PLAN,
        deserializer=FinalProductionPlan.from_dict,
    )
    if plan is not None:
        admissibility = context.method_policies.checkpoint_admissibility
        replay_resolution = None
        if admissibility.replay_enabled:
            replay_resolution = _resolve_post_selection_replay_resolution(
                context, require_train=True
            )
        replay_lineage_digest = (
            compute_replay_lineage_digest(replay_resolution)
            if admissibility.replay_enabled
            else None
        )
        validate_final_production_plan(
            plan,
            context.selected,
            method=context.method,
            policy=context.production_policy,
            replay_lineage_digest=replay_lineage_digest,
        )
    return plan


FINAL_PRODUCTION_COMPLETION_SCHEMA = "mdstats.mlff-final-production-completion.v1"


@dataclass(frozen=True, slots=True)
class FinalProductionCompletion:
    """Truthful completed run evidence for the exact current final plan."""

    plan: FinalProductionPlan
    runs: tuple[PostSelectionRunEvidence, ...]
    content_digest: str = ""

    def __post_init__(self) -> None:
        if not self.runs:
            raise PostSelectionError("Final-production completion requires at least one run.")
        payload = {
            "schema": FINAL_PRODUCTION_COMPLETION_SCHEMA,
            "final_plan_digest": self.plan.content_digest,
            "required_final_seeds": list(self.plan.required_final_seeds),
            "run_evidence_digests": [run.content_digest for run in self.runs],
            "run_identities": [run.run_identity for run in self.runs],
        }
        object.__setattr__(self, "content_digest", digest(payload))


def resolve_current_final_production_completion(
    context: PostSelectionContext,
) -> FinalProductionCompletion | None:
    """Verify that every required final run has authenticated completed evidence."""

    plan = resolve_current_final_production_plan(context)
    if plan is None:
        return None
    evidence: list[PostSelectionRunEvidence] = []
    for seed in plan.required_final_seeds:
        run_plan = build_final_production_run_plan(plan, optimizer_seed=seed)
        completed = _completed_run_evidence(context, run_plan)
        if completed is None:
            return None
        if completed.run_plan_digest != run_plan.content_digest:
            raise PostSelectionError(
                f"Stored evidence for production run {run_plan.run_identity[:12]}... "
                "belongs to a different run plan."
            )
        evidence.append(completed)
    return FinalProductionCompletion(plan=plan, runs=tuple(evidence))


# ---------------------------------------------------------------------------
# Public commands
# ---------------------------------------------------------------------------



def execute_current_cross_validate(args: Any) -> int:
    """`cross-validate`: freeze the whole design, then validate every size.

    Freeze is atomic and collection-wide: ``N``, the exact ``T_selected``
    membership and both effective role horizons of *every* selected size become
    immutable ancestry before one numerical CV job is admitted.  The outer
    iteration is deliberately serial over sizes, so the existing fold/seed
    workers, MACE subprocesses and library thread pools keep the one effective
    resource allocation they already own; the size dimension adds no scheduler
    and claims no additional machine.
    """

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _print_header("Post-selection cross-validation of the frozen training method")
    contexts = build_post_selection_contexts(
        cfg,
        paths,
        store,
        trainer=getattr(args, "_external_post_selection_trainer", None),
        inference_evaluator=getattr(args, "_external_inference_evaluator", None),
        admit=True,
    )
    sizes = [context.selected.n_selected for context in contexts]
    _ok(
        f"froze the downstream design: {len(contexts)} selected size(s) {sizes}"
    )
    for index, context in enumerate(contexts, start=1):
        _ok(
            f"  [{index}] N_selected={context.selected.n_selected}; "
            f"T_selected={context.selected.selected_membership_digest[:12]}...; "
            f"CV horizon {context.cv_policy.cv_max_num_epochs}; production horizon "
            f"{context.production_policy.production_max_num_epochs}; selection source "
            f"{context.selected.frozen.selection_source}"
        )
    _mark_stage(
        store,
        paths,
        "post_selection_cross_validation",
        StageState.RUNNING,
        f"cross-validating selected sizes {sizes}",
    )
    rejected: list[tuple[int, tuple[str, ...]]] = []
    for context in contexts:
        n_selected = context.selected.n_selected
        try:
            plan, acceptance = execute_post_selection_cross_validation(context)
        except Exception as exc:
            _mark_stage(
                store,
                paths,
                "post_selection_cross_validation",
                StageState.FAILED,
                f"N={n_selected}: {exc}",
            )
            raise
        print(
            f"Cross-validated the exact selected dataset: N_selected="
            f"{n_selected}, K={plan.fold_count}, "
            f"seeds={list(plan.required_cv_seeds)}.",
            flush=True,
        )
        if acceptance.accepted:
            _ok(
                f"N={n_selected}: every required fold of every required CV seed "
                f"passed the configured target-only predicate "
                f"({context.cv_policy.acceptance_metric} <= "
                f"{context.cv_policy.acceptance_maximum})"
            )
            continue
        # A rejected size stays visibly rejected and keeps its place in the
        # design. Sibling evidence already gathered stays valid and reusable;
        # what is refused is calling the campaign accepted.  The frozen
        # collection defines the experiment, so a methodological rejection of
        # one size never removes a later size from it: every requested size is
        # cross-validated and only then is the campaign verdict reduced.
        rejected.append((n_selected, tuple(acceptance.rejection_reasons)))
    if rejected:
        detail = "; ".join(
            f"N={size}: {list(reasons)}" for size, reasons in rejected
        )
        _mark_stage(
            store,
            paths,
            "post_selection_cross_validation",
            StageState.FAILED,
            detail,
        )
        raise PostSelectionError(
            "Post-selection cross-validation rejected the training method for "
            f"{detail}. This is a methodological result, not a target-size "
            "result: the frozen design and its evidence are unchanged, no "
            "selected size was dropped, and final production is not authorized "
            "for any size."
        )
    _mark_stage(
        store,
        paths,
        "post_selection_cross_validation",
        StageState.COMPLETE,
        f"cv acceptance for selected sizes {sizes}",
    )
    print("Next: `train-production`.", flush=True)
    return 0


def _cv_admission_blockers(
    contexts: "tuple[PostSelectionContext, ...]",
) -> tuple[str, ...]:
    """Every frozen size that has no current accepted CV ancestry of its own.

    This is the collection-wide production barrier.  It runs before any new
    production job so a requested multi-size experiment can never quietly turn
    into the successful subset of it.
    """

    blockers: list[str] = []
    for context in contexts:
        n_selected = context.selected.n_selected
        try:
            plan = resolve_current_cv_plan(context)
        except Exception as exc:  # noqa: BLE001 - reported, not interpreted
            blockers.append(f"N={n_selected}: CV plan is unreadable or stale ({exc})")
            continue
        if plan is None:
            blockers.append(f"N={n_selected}: no current cross-validation plan exists")
            continue

        try:
            acceptance = resolve_current_cv_acceptance(context)
        except Exception as exc:  # noqa: BLE001 - reported, not interpreted
            blockers.append(f"N={n_selected}: CV acceptance is unreadable ({exc})")
            continue
        if acceptance is None:
            blockers.append(
                f"N={n_selected}: no current cross-validation acceptance exists"
            )
            continue

        try:
            require_cv_acceptance_for_method(
                acceptance,
                plan=plan,
                method_identity_digest=context.method.content_digest,
                selected_binding_digest=context.selected.binding.content_digest,
            )
        except Exception as exc:  # noqa: BLE001 - reported, not interpreted
            blockers.append(f"N={n_selected}: cross-validation is not accepted ({exc})")
            continue
    return tuple(blockers)


def execute_current_train_production(args: Any) -> int:
    """`train-production`: fresh full-``T_selected`` production for every size.

    Admission is a collection-wide barrier: the complete frozen design is
    authenticated and every selected size must hold current accepted CV ancestry
    under its own binding and its own ``H_cv`` before *any* new production job
    starts.  Evidence already published by an earlier attempt keeps whatever
    currentness its own identity earns; what the barrier prevents is admitting
    new work that would present a partial experiment as a whole one.
    """

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _print_header("Fresh final production on the complete selected dataset")
    contexts = build_post_selection_contexts(
        cfg,
        paths,
        store,
        trainer=getattr(args, "_external_post_selection_trainer", None),
        inference_evaluator=getattr(args, "_external_inference_evaluator", None),
    )
    sizes = [context.selected.n_selected for context in contexts]
    blockers = _cv_admission_blockers(contexts)
    if blockers:
        detail = "; ".join(blockers)
        _mark_stage(
            store,
            paths,
            "post_selection_final_production",
            StageState.FAILED,
            detail,
        )
        raise PostSelectionError(
            "Final production is not admitted: the frozen design requests selected "
            f"sizes {sizes}, and {detail}. No production run was started for any "
            "size. Existing immutable evidence is untouched; resolve the blocking "
            "size(s) with `cross-validate` and rerun."
        )
    _mark_stage(
        store,
        paths,
        "post_selection_final_production",
        StageState.RUNNING,
        f"producing selected sizes {sizes}",
    )
    published: list[str] = []
    for context in contexts:
        n_selected = context.selected.n_selected
        try:
            final_plan, evidence, decision = execute_final_production(context)
        except Exception as exc:
            _mark_stage(
                store,
                paths,
                "post_selection_final_production",
                StageState.FAILED,
                f"N={n_selected}: {exc}",
            )
            raise
        _ok(
            f"N={n_selected}: trained {len(evidence)} fresh production run(s) on "
            f"the full T_selected for {final_plan.planned_epochs} frozen "
            "production epoch(s), under the cross-validation-accepted method"
        )
        _ok(
            f"N={n_selected}: published the final product under "
            f"`{decision.committee_policy}`: member(s) "
            f"{list(decision.published_member_ids)} on target head "
            f"`{decision.target_head_name}`"
        )
        published.append(f"N={n_selected} {decision.content_digest[:12]}")
    _mark_stage(
        store,
        paths,
        "post_selection_final_production",
        StageState.COMPLETE,
        f"final publications {published}",
    )
    if len(contexts) > 1:
        from .campaign_lifecycle import MULTI_SIZE_TERMINAL_MESSAGE

        print(MULTI_SIZE_TERMINAL_MESSAGE, flush=True)
    return 0


__all__ = [
    "FOLD_ACCEPTANCE_FILENAME",
    "FinalProductionCompletion",
    "POST_SELECTION_REPLAY_HEAD_NAME",
    "POST_SELECTION_TARGET_HEAD_NAME",
    "RUN_EVIDENCE_FILENAME",
    "PostSelectionContext",
    "PostSelectionReplayResolution",
    "build_post_selection_context",
    "build_post_selection_contexts",
    "execute_current_cross_validate",
    "execute_current_train_production",
    "execute_final_production",
    "execute_post_selection_cross_validation",
    "execute_post_selection_run",
    "resolve_current_cv_acceptance",
    "resolve_current_cv_plan",
    "authenticated_run_representative_records",
    "evaluate_post_selection_run_candidates",
    "resolve_current_final_production_completion",
    "resolve_current_final_production_publication",
    "resolve_current_final_production_plan",
    "resolve_post_selection_evaluation_model_state",
]
