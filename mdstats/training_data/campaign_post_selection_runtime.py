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

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ._common import TrainingDataInputError, digest, sha256_file_cached, validate_digest
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionError,
    load_current_selected_training_context,
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
    PostSelectionExecutionError,
    PostSelectionRunEvidence,
    PostSelectionRungRequest,
    authenticate_post_selection_provider,
    evaluate_post_selection_dataset,
    materialize_post_selection_run,
    post_selection_checkpoint_candidates,
    post_selection_runtime_plan,
)
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
    resolve_current_post_selection_record,
)

#: Live vs EMA evaluation convention for post-selection runs.  It is a method
#: property, not a per-run choice, and matches the accepted TRAIN2 convention.
POST_SELECTION_EVALUATION_MODEL_STATE = "live"


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
    expected_revision: Any = None,
    qualification_case_workers: int = 1,
) -> PostSelectionContext:
    """Re-establish current P4 authority and resolve all three P5 identities.

    The three identities are resolved here, before any expensive work, which is
    exactly what makes them policy rather than evidence: nothing they depend on
    has been produced yet.
    """

    from ._campaign_cli_core import _ensure_local_wrappers

    selected = load_current_selected_training_context(
        cfg, paths, store, expected_revision=expected_revision
    )
    resolved_trainer = trainer
    if resolved_trainer is None:
        resolved_trainer = MacePostSelectionTrainer(
            wrapper_path=_ensure_local_wrappers(paths)["mdstats-mace-train"]
        )
    policies = resolve_post_selection_method_policies(cfg)
    return PostSelectionContext(
        cfg=cfg,
        paths=paths,
        store=store,
        selected=selected,
        method=resolve_post_selection_method_identity(cfg, policies=policies),
        method_policies=policies,
        cv_policy=resolve_cv_validation_policy_identity(cfg),
        production_policy=resolve_final_production_policy_identity(cfg),
        trainer=resolved_trainer,
        inference_evaluator=inference_evaluator,
        qualification_case_workers=max(1, int(qualification_case_workers)),
    )


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


def _resolve_post_selection_replay_resolution(
    context: PostSelectionContext, *, require_train: bool = True
) -> Any | None:
    if not hasattr(context, "paths") or context.paths is None:
        raise PostSelectionError(
            "Replay-enabled post-selection requires configured campaign paths."
        )
    from ._campaign_cli_core import (
        _build_replay_plan,
        _resolve_true_label_replay_inputs,
        _single_source_replay_context,
    )
    from .replay import ReplayLabelMode, ReplayMode

    single_ctx = _single_source_replay_context(context.cfg, context.paths)
    if single_ctx is not None:
        plan = single_ctx.get("plan")
        true_resolution = single_ctx.get("true_resolution")
        if plan is None or true_resolution is None:
            raise PostSelectionError(
                "Single-source replay did not produce both training and TRUE_DFT "
                "monitor authorities."
            )
        training_artifact = getattr(plan, "train_artifact", None)
        if training_artifact is None:
            raise PostSelectionError(
                "Single-source replay did not produce a canonical training artifact."
            )
        training_path = getattr(training_artifact, "path", None)
        if training_path is None:
            raise PostSelectionError(
                "Single-source replay training artifact does not identify its source file."
            )
        monitor_artifact = getattr(true_resolution, "monitor_artifact", None)
        monitor_path = getattr(true_resolution, "monitor_path", None)
        if monitor_artifact is None or monitor_path is None:
            raise PostSelectionError(
                "Single-source replay did not produce an independent TRUE_DFT "
                "monitor artifact."
            )
        source_art = single_ctx.get("replay_source")
        split_manifest = single_ctx.get("replay_split_manifest")
        return PostSelectionReplayResolution(
            interface="single_source",
            train_path=str(training_path),
            monitor_path=str(monitor_path),
            train_artifact=training_artifact,
            monitor_artifact=monitor_artifact,
            training_label_mode=getattr(training_artifact, "label_mode", None),
            true_label_mode=getattr(monitor_artifact, "label_mode", None),
            source_path=(None if source_art is None else str(source_art.path)),
            source_content_digest=(
                None if source_art is None else source_art.content_digest
            ),
            source_sha256=None if source_art is None else source_art.sha256,
            split_manifest_digest=(
                None if split_manifest is None else split_manifest.content_digest
            ),
        )

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
            summary=summary,
            evaluation_model_state=POST_SELECTION_EVALUATION_MODEL_STATE,
            allow_forward_override=context.inference_evaluator is not None,
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

            foundation_content_digest = (
                foundation_identity.canonical_content_digest
                if foundation_identity is not None
                else digest({"foundation_model": foundation_model})
            )
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
                        context.method_policies.common_training.default_dtype
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
                    default_dtype=context.method_policies.common_training.default_dtype,
                )
                try:
                    baseline_replay_metrics = evaluate_post_selection_dataset(
                        run_plan=run_plan,
                        artifact=replay_monitor_artifact,
                        dataset_role="replay_monitor_baseline",
                        root_directory=replay_monitor_path.parent,
                        provider=baseline_provider,
                        block_ids=replay_blocks,
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
) -> tuple[PostSelectionRunEvidence, Any, Any]:
    """Run one post-selection job end to end and return its bound evidence.

    Order matters and is enforced by construction: the representative is frozen
    from the run's own monitor before the held-out outer data is evaluated at
    all, so outer evidence cannot influence the checkpoint it judges.
    """

    selected = context.selected
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
) -> tuple[PostSelectionRunEvidence, Any, Any]:
    """The run body, executed while this run root's activity lease is held."""

    selected = context.selected
    material_directory = run_root / "materialization"
    checkpoint_directory = run_root / "checkpoints"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
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
        common_training_policy=context.method_policies.common_training,
        mace_architecture=context.method_policies.mace_architecture,
        foundation_model=context.method_policies.foundation_model,
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
    runtime_plan = post_selection_runtime_plan(
        method=context.method,
        optimizer_policy=optimizer_policy,
        budget_policy=budget_policy,
        structures_per_epoch=len(preparation.membership),
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
    summary = context.trainer(
        PostSelectionRungRequest(
            plan=runtime_plan,
            run_plan=run_plan,
            materialization=materialization,
            materialization_directory=material_directory,
            checkpoint_directory=checkpoint_directory,
            optimizer_policy=optimizer_policy,
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
                if replay_resolution is not None and replay_resolution.train_path is not None
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
        )
    )
    if summary.plan_digest != runtime_plan.content_digest:
        raise PostSelectionExecutionError(
            "The TRAIN2 runtime summary does not belong to this run's runtime plan."
        )

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
            summary=summary,
            evaluation_model_state=POST_SELECTION_EVALUATION_MODEL_STATE,
            allow_forward_override=context.inference_evaluator is not None,
        )
        try:
            outer_metrics = evaluate_post_selection_dataset(
                run_plan=run_plan,
                artifact=materialization.outer_evaluation_artifact,
                dataset_role=DATASET_ROLE_OUTER_EVALUATION,
                root_directory=material_directory,
                provider=provider,
                block_ids=_component_block_ids(selected, outer_evaluation_frame_uids),
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

#: The exact set of files this owner produced under one run root, written when
#: the run reaches its terminal record.  Digests and sizes are deliberately not
#: repeated here - they belong to the evidence records - but the *membership* is,
#: because membership is the one thing a downstream consumer cannot re-derive
#: and must not guess.  A consumer that wants to treat the run tree as a closed
#: unit asks this owner, and gets a yes only if what is on disk is exactly what
#: P5 wrote.
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
        RUN_MEMBER_MANIFEST_FILENAME,
    )
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


def _run_root_relative_files(root: Path) -> list[str]:
    """Every regular file under one run root, as sorted POSIX relative paths."""

    members: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        if path.name in _OWNED_LOCK_NAMES:
            continue
        members.append(relative)
    return sorted(members)


def record_post_selection_run_members(run_root: str | os.PathLike[str]) -> Path:
    """Freeze the exact member set this owner produced under one run root.

    Written once, when the run reaches its terminal record, so that a later
    consumer can ask P5 - rather than guess from pathnames - whether a run tree
    still contains exactly what P5 put there.
    """

    from .target_size_execution import publish_mutable_json_atomic

    root = Path(run_root)
    destination = root / RUN_MEMBER_MANIFEST_FILENAME
    members = [
        name
        for name in _run_root_relative_files(root)
        if name != RUN_MEMBER_MANIFEST_FILENAME
    ]
    publish_mutable_json_atomic(
        destination,
        {
            "schema": RUN_MEMBER_MANIFEST_SCHEMA,
            "run_root": root.name,
            "members": members,
            "member_count": len(members),
        },
    )
    return destination


def recorded_post_selection_run_members(
    run_root: str | os.PathLike[str],
) -> tuple[str, ...]:
    """The member set this owner recorded for one run root, or empty."""

    path = Path(run_root) / RUN_MEMBER_MANIFEST_FILENAME
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    if payload.get("schema") != RUN_MEMBER_MANIFEST_SCHEMA:
        return ()
    return tuple(sorted(str(item) for item in payload.get("members", ())))


def certify_closed_post_selection_run_root(
    run_root: str | os.PathLike[str],
) -> tuple[bool, str]:
    """Whether P5 certifies every descendant of one run root as its own.

    Two things must hold. The run must be finished, and what is on disk must be
    contained in the member set P5 recorded when it finished. The second
    condition is what turns "beneath a P5 directory" into "produced by P5": a
    file dropped into ``checkpoints/`` by anything else is not in the recorded
    set and makes the whole run root uncertified.
    """

    root = Path(run_root)
    if not root.is_dir() or root.is_symlink():
        return False, f"{root} is not a plain directory"
    try:
        children = sorted(entry.name for entry in os.scandir(root))
    except OSError as exc:
        return False, f"{root} could not be enumerated: {exc}"
    terminal = {FOLD_ACCEPTANCE_FILENAME, RUN_EVIDENCE_FILENAME} & set(children)
    if not terminal:
        return False, (
            "run root carries no terminal fold-acceptance/run-evidence record, so the "
            "owner cannot certify the run is finished"
        )
    # There is deliberately no pathname allowlist here. The run directory is
    # delegated to the configured trainer, which writes its own layout inside it
    # (per-epoch metric logs, framework results/logs trees, and so on). Guessing
    # that layout is exactly the pathname inference this certification exists to
    # replace; the recorded member set below is the owner's own answer.
    manifest_path = root / RUN_MEMBER_MANIFEST_FILENAME
    if not manifest_path.is_file():
        return False, (
            "run root carries no recorded member manifest, so this owner cannot "
            "certify which descendants it produced"
        )
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return False, f"run member manifest is unreadable ({exc})"
    if payload.get("schema") != RUN_MEMBER_MANIFEST_SCHEMA:
        return False, "run member manifest carries an unsupported schema"
    recorded = set(payload.get("members", ()))
    observed = {
        name
        for name in _run_root_relative_files(root)
        if name != RUN_MEMBER_MANIFEST_FILENAME
    }
    extra = sorted(observed - recorded)
    if extra:
        return False, f"run root contains descendant(s) P5 did not write: {extra[:5]}"
    # A recorded member that is *absent* means content has legitimately left the
    # tree - reclaimed into a cold archive, for instance. The guarantee this
    # certification makes is that nothing foreign is present, not that nothing
    # has been removed.
    return True, (
        "terminal run whose descendants all belong to the member set P5 recorded"
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
    acceptances: list[CvFoldAcceptance] = []
    for seed, fold_index in plan.required_run_matrix:
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
            acceptances.append(completed)
            continue
        _evidence, representative, outer_metrics = execute_post_selection_run(
            context,
            run_plan=run_plan,
            budget_policy=budget_policy,
            training_frame_uids=fold.training_frame_uids,
            monitor_frame_uids=fold.checkpoint_monitor_frame_uids,
            outer_evaluation_frame_uids=fold.outer_evaluation_frame_uids,
        )
        if outer_metrics is None:
            raise PostSelectionError(
                f"CV fold {fold_index} produced no held-out outer evaluation."
            )
        acceptance = build_cv_fold_acceptance(
            run_plan=run_plan,
            representative=representative,
            outer_metrics=outer_metrics,
            policy=context.cv_policy,
        )
        store.put(acceptance)
        _record_completed_fold_acceptance(context, run_plan, acceptance)
        acceptances.append(acceptance)

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
    evidence: list[PostSelectionRunEvidence] = []
    for seed in final_plan.required_final_seeds:
        run_plan = build_final_production_run_plan(final_plan, optimizer_seed=seed)
        store.put(run_plan)
        completed = _completed_run_evidence(context, run_plan)
        if completed is not None:
            evidence.append(completed)
            continue
        run_evidence, _representative, _outer = execute_post_selection_run(
            context,
            run_plan=run_plan,
            budget_policy=budget_policy,
            training_frame_uids=selected.selected_membership,
            monitor_frame_uids=m3_membership,
            outer_evaluation_frame_uids=None,
        )
        _record_completed_run_evidence(context, run_plan, run_evidence)
        evidence.append(run_evidence)

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
    """`cross-validate`: the only current post-selection CV entrypoint."""

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
    context = build_post_selection_context(
        cfg,
        paths,
        store,
        trainer=getattr(args, "_external_post_selection_trainer", None),
        inference_evaluator=getattr(args, "_external_inference_evaluator", None),
    )
    _mark_stage(
        store,
        paths,
        "post_selection_cross_validation",
        StageState.RUNNING,
        f"cross-validating N_selected={context.selected.n_selected}",
    )
    try:
        plan, acceptance = execute_post_selection_cross_validation(context)
    except Exception as exc:
        _mark_stage(
            store,
            paths,
            "post_selection_cross_validation",
            StageState.FAILED,
            str(exc),
        )
        raise
    print(
        f"Cross-validated the exact selected dataset: N_selected="
        f"{context.selected.n_selected}, K={plan.fold_count}, "
        f"seeds={list(plan.required_cv_seeds)}.",
        flush=True,
    )
    if not acceptance.accepted:
        _mark_stage(
            store,
            paths,
            "post_selection_cross_validation",
            StageState.FAILED,
            "; ".join(acceptance.rejection_reasons),
        )
        raise PostSelectionError(
            "Post-selection cross-validation rejected the training method: "
            f"{list(acceptance.rejection_reasons)}. This is a methodological "
            "result, not a target-size result: the selected N and its evidence "
            "are unchanged, and final production is not authorized."
        )
    _ok(
        "every required fold of every required CV seed passed the configured "
        f"target-only predicate ({context.cv_policy.acceptance_metric} <= "
        f"{context.cv_policy.acceptance_maximum})"
    )
    _mark_stage(
        store,
        paths,
        "post_selection_cross_validation",
        StageState.COMPLETE,
        f"cv acceptance {acceptance.content_digest[:12]}",
    )
    print("Next: `train-production`.", flush=True)
    return 0


def execute_current_train_production(args: Any) -> int:
    """`train-production`: fresh full-``T_selected`` production training."""

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
    context = build_post_selection_context(
        cfg,
        paths,
        store,
        trainer=getattr(args, "_external_post_selection_trainer", None),
        inference_evaluator=getattr(args, "_external_inference_evaluator", None),
    )
    _mark_stage(
        store,
        paths,
        "post_selection_final_production",
        StageState.RUNNING,
        f"producing N_selected={context.selected.n_selected}",
    )
    try:
        final_plan, evidence, decision = execute_final_production(context)
    except Exception as exc:
        _mark_stage(
            store,
            paths,
            "post_selection_final_production",
            StageState.FAILED,
            str(exc),
        )
        raise
    _ok(
        f"trained {len(evidence)} fresh production run(s) on the full "
        f"T_selected (N={final_plan.n_selected}) for "
        f"{final_plan.planned_epochs} configured [training].max_num_epochs, "
        "under the cross-validation-accepted method"
    )
    _ok(
        f"published the final product under `{decision.committee_policy}`: "
        f"member(s) {list(decision.published_member_ids)} on target head "
        f"`{decision.target_head_name}`"
    )
    _mark_stage(
        store,
        paths,
        "post_selection_final_production",
        StageState.COMPLETE,
        f"final publication {decision.content_digest[:12]}",
    )
    return 0


__all__ = [
    "FOLD_ACCEPTANCE_FILENAME",
    "FinalProductionCompletion",
    "POST_SELECTION_EVALUATION_MODEL_STATE",
    "POST_SELECTION_REPLAY_HEAD_NAME",
    "POST_SELECTION_TARGET_HEAD_NAME",
    "RUN_EVIDENCE_FILENAME",
    "PostSelectionContext",
    "PostSelectionReplayResolution",
    "build_post_selection_context",
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
]
