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

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ._common import digest
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
    PostSelectionMethodIdentity,
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
from .post_selection_run_identity import PostSelectionRunRole
from .post_selection_store import (
    POINTER_CV_ACCEPTANCE,
    POINTER_CV_PLAN,
    POINTER_FINAL_PLAN,
    open_post_selection_store,
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


def build_post_selection_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    *,
    trainer: Any = None,
    inference_evaluator: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
    expected_revision: Any = None,
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

    return _optimizer_policy(
        context.cfg,
        seed=int(seed),
        num_workers=int(_cfg(context.cfg, "training", "num_workers", 0)),
        paths=context.paths,
        planned_epochs=int(planned_epochs),
    )


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

    from .eval2 import assess_eval2_checkpoint

    selected = context.selected
    run_root = context.run_root(run_plan.run_identity)
    material_directory = run_root / "materialization"
    checkpoint_directory = run_root / "checkpoints"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    optimizer_policy = _optimizer_policy_for(
        context, seed=run_plan.optimizer_seed, planned_epochs=run_plan.planned_epochs
    )
    extxyz_policy = context.method_policies.extxyz
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
    )
    runtime_plan = post_selection_runtime_plan(
        method=context.method,
        optimizer_policy=optimizer_policy,
        budget_policy=budget_policy,
        structures_per_epoch=len(preparation.membership),
        learning_rate_policy=context.method_policies.learning_rate_schedule,
    )
    summary = context.trainer(
        PostSelectionRungRequest(
            plan=runtime_plan,
            run_plan=run_plan,
            materialization=materialization,
            materialization_directory=material_directory,
            checkpoint_directory=checkpoint_directory,
            optimizer_policy=optimizer_policy,
        )
    )
    if summary.plan_digest != runtime_plan.content_digest:
        raise PostSelectionExecutionError(
            "The TRAIN2 runtime summary does not belong to this run's runtime plan."
        )

    candidates = post_selection_checkpoint_candidates(
        run_plan=run_plan,
        checkpoint_directory=checkpoint_directory,
        runtime_plan=runtime_plan,
    )
    catalog = _checkpoint_catalog(run_plan, checkpoint_directory)
    monitor_blocks = _component_block_ids(selected, monitor_frame_uids)
    admissibility = context.method_policies.checkpoint_admissibility
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
        record = assess_eval2_checkpoint(
            point,
            evaluation_record_digest=metrics.content_digest,
            target_metrics=metrics,
            admissibility_policy=admissibility,
            replay_candidate_force_rmse_ev_per_angstrom=None,
            replay_foundation_force_rmse_ev_per_angstrom=None,
            replay_label_mode=None,
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
    store.put(evidence)
    return evidence, representative, outer_metrics


def _checkpoint_catalog(run_plan: Any, checkpoint_directory: Path) -> Any:
    from .post_selection_execution import post_selection_checkpoint_catalog

    return post_selection_checkpoint_catalog(
        run_plan=run_plan, checkpoint_directory=checkpoint_directory
    )


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
    plan = build_post_selection_cv_plan(
        selected, context.method, context.cv_policy, projection=projection
    )
    store = context.evidence_store
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
        acceptances.append(acceptance)

    campaign = accept_post_selection_cv_campaign(plan, context.cv_policy, acceptances)
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
        validate_post_selection_cv_plan(plan, context.selected)
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
) -> tuple[FinalProductionPlan, tuple[PostSelectionRunEvidence, ...]]:
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
    final_plan = build_final_production_plan(
        selected,
        context.method,
        context.production_policy,
        cv_plan=plan,
        cv_acceptance=acceptance,
    )
    validate_final_production_plan(
        final_plan,
        selected,
        method=context.method,
        policy=context.production_policy,
    )
    store = context.evidence_store
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
        run_evidence, _representative, _outer = execute_post_selection_run(
            context,
            run_plan=run_plan,
            budget_policy=budget_policy,
            training_frame_uids=selected.selected_membership,
            monitor_frame_uids=m3_membership,
            outer_evaluation_frame_uids=None,
        )
        evidence.append(run_evidence)
    return final_plan, tuple(evidence)


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
        validate_final_production_plan(
            plan,
            context.selected,
            method=context.method,
            policy=context.production_policy,
        )
    return plan


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
        final_plan, evidence = execute_final_production(context)
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
    _mark_stage(
        store,
        paths,
        "post_selection_final_production",
        StageState.COMPLETE,
        f"final plan {final_plan.content_digest[:12]}",
    )
    return 0


__all__ = [
    "POST_SELECTION_EVALUATION_MODEL_STATE",
    "PostSelectionContext",
    "build_post_selection_context",
    "execute_current_cross_validate",
    "execute_current_train_production",
    "execute_final_production",
    "execute_post_selection_cross_validation",
    "execute_post_selection_run",
    "resolve_current_cv_acceptance",
    "resolve_current_cv_plan",
    "resolve_current_final_production_plan",
]
