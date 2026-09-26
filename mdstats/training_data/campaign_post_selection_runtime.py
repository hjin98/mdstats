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
 -> exact common target monitor M_mon + P1 cross-role separation evidence
 -> CV plan from exact T_selected + complete P1 protected-relation projection + M_mon
 -> fresh fold materialization / TRAIN2 / EVAL2 evidence (checkpoints on M_mon)
 -> exact all-required-fold target-only CV acceptance
 -> final-production policy identity
 -> final-production plan from full T_selected + accepted CV + the same M_mon
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
from typing import Any, Callable, ContextManager, Deque, Mapping, Sequence

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
    CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
    CvCampaignAcceptance,
    CvFoldAcceptance,
    PostSelectionCvRejectedError,
    accept_post_selection_cv_campaign,
    build_cv_fold_acceptance,
    require_cv_acceptance_for_method,
    select_post_selection_representative,
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
    RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
    RUN_OUTCOME_REPRESENTATIVE_SELECTED,
    EvaluationMeasurementIdentity,
    MacePostSelectionTrainer,
    PostSelectionCancelledError,
    PostSelectionExecutionError,
    PostSelectionMaterialization,
    POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_FILENAME,
    FoundationResidualInputs,
    PostSelectionRunEvidence,
    PostSelectionRungRequest,
    _post_selection_mace_config,
    _build_post_selection_mace_execution_authority,
    _mace_execution_frame_uid_set_digest,
    authenticate_post_selection_provider,
    evaluate_post_selection_dataset,
    fit_post_selection_preparation,
    materialize_post_selection_run,
    resolve_foundation_residual_inputs,
    post_selection_checkpoint_candidates,
    post_selection_eval_role_digest,
    post_selection_runtime_plan,
    write_outer_evaluation_transport,
)
from .bounded_inference import execution_batch_width
from .post_selection_identity import (
    CvValidationPolicyIdentity,
    FinalProductionPolicyIdentity,
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    PostSelectionMethodIdentity,
    RETIRED_ASSESSMENT_ONLY_METHOD_FIELDS,
    compute_replay_lineage_digest,
    cv_assessment_position_policy_digest,
    cv_training_budget_policy,
    final_production_training_budget_policy,
    final_seed_assessment_policy_digest,
    post_selection_checkpoint_admissibility,
    resolve_cv_validation_policy_identity,
    resolve_final_production_policy_identity,
    resolve_post_selection_method_identity,
    resolve_post_selection_method_policies,
)
from .post_selection_run_identity import PostSelectionRunRole
from .post_selection_production import (
    FinalProductionPlan,
    build_final_production_plan,
    build_final_production_run_plan,
    validate_final_production_plan,
)
from .post_selection_publication import (
    FinalProductionPublicationDecision,
    publish_final_production_publication,
    resolve_current_final_production_publication,
)
from .post_selection_store import (
    ASSESSMENT_ROLE_CV_FOLD,
    ASSESSMENT_ROLE_FINAL_SEED,
    POINTER_ASSESSMENT_POSITION,
    POINTER_CV_ACCEPTANCE,
    POINTER_CV_PLAN,
    POINTER_FINAL_PLAN,
    POINTER_FINAL_PUBLICATION,
    assessment_position_digest,
    open_post_selection_store,
    post_selection_collection_admission,
    post_selection_collection_signature,
    post_selection_publication_barrier,
    post_selection_root,
    publish_current_post_selection_pointer,
    read_current_post_selection_pointer,
    resolve_current_post_selection_record,
)

@dataclass(frozen=True, slots=True)
class PostSelectionRunResult:
    """The assessment inputs of one evaluated run, before any assessment record.

    ``candidates`` is the complete ordered (by epoch) checkpoint universe
    assessed under the current hard policy; ``representative`` is its strict
    D2.DEF.059A minimum or ``None`` when no candidate is hard-admissible.
    ``measurements`` are every immutable measurement identity/metric record the
    candidates, representative and held-out evaluation bind; they are durably
    published before any assessment that references them.
    """

    training_root_identity: str
    materialization: Any
    runtime_summary_digest: str
    candidates: tuple[Any, ...]
    representative: Any | None
    monitor_metrics: Any | None
    outer_metrics: Any | None
    measurements: tuple[Any, ...]
    diagnostics: Any


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
    # Qualification-only execution seams are carried with the invocation
    # context so a fresh currentness resolver reuses the same owner seams
    # instead of silently constructing a different deployment identity.
    qualification_deployment_exporter: Callable[..., Any] | None = None
    qualification_mliap_builder: Callable[..., Any] | None = None
    qualification_deployed_evaluator: Callable[..., Any] | None = None
    qualification_dynamics_runner: Callable[..., Any] | None = None
    # Every frozen selected size of this campaign generation.  The common target
    # monitor is separated from all of them, so it never depends on one size.
    governed_selected: tuple[CurrentSelectedTrainingContext, ...] = ()
    # Execution-only binding resolved once per invocation from the stored
    # doctor-frozen TRAIN2 realization.  It never replaces the scientific
    # source identity carried by ``method_policies``.
    train2_foundation_realization: Any | None = None
    _baseline_replay_cache: dict[str, Any] = field(
        default_factory=dict, repr=False, compare=False
    )
    _common_monitor_cache: dict[str, Any] = field(
        default_factory=dict, repr=False, compare=False
    )

    @property
    def train2_foundation_path(self) -> Path | None:
        """The checkpoint that constructs and reconstructs this invocation's TRAIN2.

        Source-only consumers (foundation residuals, replay baselines) keep
        ``method_policies.foundation_model``; the two coincide only when TRAIN2
        is not phase-separated.
        """

        from ._campaign_cli_core import _phase_separated_acceleration

        source = self.method_policies.foundation_model
        if not source:
            return None
        if self.train2_foundation_realization is not None:
            return Path(self.train2_foundation_realization.training_checkpoint_reference)
        if _phase_separated_acceleration(self.cfg):
            raise PostSelectionError(
                "Phase-separated TRAIN2 has no resolved training realization; the "
                "scientific source checkpoint is never a TRAIN2 construction fallback."
            )
        return Path(source)

    def common_target_monitor(self) -> tuple[Any, Any]:
        """Resolve ``(M_mon record, P1 separation evidence)`` for this campaign.

        Sampling happens first, from the neutral label-usable parent; separation
        against every governed selected target set is proven afterwards.  Both
        are deterministic functions of current P1 authority, so recomputation
        reproduces the record every sibling plan binds.
        """

        if "resolved" not in self._common_monitor_cache:
            from .online_monitor import build_common_target_monitor
            from .post_selection_cv_plan import build_common_monitor_separation

            governed = self.governed_selected or (self.selected,)
            if self.selected.binding.content_digest not in {
                item.binding.content_digest for item in governed
            }:
                raise PostSelectionError(
                    "The governed selected target sets do not include this context."
                )
            record = build_common_target_monitor(self.selected.authorities)
            separation = build_common_monitor_separation(governed, record)
            self._common_monitor_cache["resolved"] = (record, separation)
        return self._common_monitor_cache["resolved"]

    def checkpoint_admissibility(self, run_plan: Any) -> Any:
        """Return the authenticated role-effective admissibility of one run.

        The run plan binds the method (shared constraints) and its role policy
        (target ceiling).  Both must be the current authority before a policy
        is composed, so no run is trained or judged under a stale or other-role
        ceiling.
        """

        role = str(getattr(run_plan, "run_role", ""))
        if role == PostSelectionRunRole.POST_SELECTION_CV.value:
            role_policy: Any = self.cv_policy
            bound_policy_digest = getattr(run_plan, "cv_policy_identity_digest", None)
        elif role == PostSelectionRunRole.FINAL_PRODUCTION.value:
            role_policy = self.production_policy
            bound_policy_digest = getattr(
                run_plan, "final_production_policy_digest", None
            )
        else:
            raise PostSelectionError(
                f"Post-selection checkpoint admissibility has no role policy for {role!r}."
            )
        if (
            getattr(run_plan, "method_identity_digest", None)
            != self.method.content_digest
            or bound_policy_digest != role_policy.content_digest
        ):
            raise PostSelectionError(
                f"Run {str(getattr(run_plan, 'run_identity', ''))[:12]}... is not bound "
                f"to the current method and {role} policy; its checkpoints are never "
                "judged under a different admissibility policy."
            )
        return post_selection_checkpoint_admissibility(self.method_policies, role_policy)

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

    from ._campaign_cli_core import (
        _cfg,
        _current_train2_foundation_realization,
        _ensure_local_wrappers,
    )

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
    train2_foundation_realization = _current_train2_foundation_realization(
        cfg, paths, policies.foundation_potential_identity
    )
    configuration = policies.checkpoint_policy_configuration
    for notice in () if configuration is None else configuration.migration_notices:
        print(f"[P5 config] {notice}", flush=True)
    contexts = []
    for selected in selected_contexts:
        cv_max_num_epochs = None
        production_max_num_epochs = None
        if selected.frozen is not None:
            cv_max_num_epochs = selected.frozen.cv_max_num_epochs
            production_max_num_epochs = selected.frozen.production_max_num_epochs
        # A legacy binding never substitutes its stored historical method
        # identity: every current P5 context executes the restored method, and
        # historical plans simply fail currentness against it.
        contexts.append(
            PostSelectionContext(
                cfg=cfg,
                paths=paths,
                store=store,
                selected=selected,
                method=method,
                method_policies=policies,
                cv_policy=resolve_cv_validation_policy_identity(
                    cfg,
                    max_num_epochs=cv_max_num_epochs,
                    training_mode=policies.training_mode,
                ),
                production_policy=resolve_final_production_policy_identity(
                    cfg,
                    max_num_epochs=production_max_num_epochs,
                    training_mode=policies.training_mode,
                ),
                trainer=resolved_trainer,
                inference_evaluator=inference_evaluator,
                qualification_case_workers=max(1, int(qualification_case_workers)),
                governed_selected=tuple(selected_contexts),
                train2_foundation_realization=train2_foundation_realization,
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

    realization = context.train2_foundation_realization
    resolved_realization = (
        {}
        if realization is None
        else {"resolved_training_acceleration_realization": realization}
    )
    policy = _optimizer_policy(
        context.cfg,
        seed=int(seed),
        num_workers=int(_cfg(context.cfg, "training", "num_workers", 0)),
        paths=context.paths,
        planned_epochs=int(planned_epochs),
        **resolved_realization,
    )
    if realization is not None and (
        policy.acceleration_realization_digest != realization.content_digest
        or policy.resolved_acceleration_kernel_mode != realization.training_kernel_mode
    ):
        raise PostSelectionError(
            "Optimizer policy did not preserve the invocation's resolved TRAIN2 "
            "acceleration realization and kernel mode."
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


def _eval2_target_metric_policy_digest() -> str:
    from .target_size_execution import EVAL2_TARGET_METRIC_POLICY_DIGEST

    return EVAL2_TARGET_METRIC_POLICY_DIGEST


def _retire_post_selection_provider(provider: Any) -> None:
    """Release one evaluation provider through its existing lifecycle owner."""

    if provider is not None and hasattr(provider, "close"):
        provider.close()


def _checkpoint_provider_realization(context: PostSelectionContext) -> dict[str, Any]:
    """Numerically material realization of the TRAIN2 checkpoint provider."""

    policies = context.method_policies
    return {
        "provider": "mdstats.p5-train2-checkpoint-mace-provider.v1",
        "default_dtype": str(policies.default_dtype),
        "device": str(policies.device),
        "acceleration_backend": str(policies.acceleration_backend),
        "forward_realization": (
            "native" if context.inference_evaluator is None else "external_override"
        ),
    }


def _foundation_provider_realization(context: PostSelectionContext) -> dict[str, Any]:
    """Numerically material realization of the foundation baseline provider."""

    policies = context.method_policies
    return {
        "provider": "mdstats.p5-foundation-baseline-mace-provider.v1",
        "default_dtype": str(policies.default_dtype),
        "device": str(policies.device),
        "acceleration_backend": "e3nn",
        "forward_realization": (
            "native" if context.inference_evaluator is None else "external_override"
        ),
    }


def _checkpoint_model_state(checkpoint_sha256: str, evaluation_model_state: str) -> dict[str, Any]:
    return {
        "kind": "train2_checkpoint",
        "checkpoint_sha256": validate_digest(str(checkpoint_sha256), name="checkpoint_sha256"),
        "evaluation_model_state": str(evaluation_model_state),
    }


@dataclass(frozen=True, slots=True)
class _ReusableMeasurements:
    """Candidate/outer measurement records offered for exact-equivalence reuse.

    Sources are only already-published immutable records reached by following
    existing locators; nothing is found by scanning.  An offered record is used
    only when its bound measurement identity equals the one the current
    experiment derives - scalar equality is never evidence.
    """

    candidates: Mapping[str, Any] = field(default_factory=dict)
    outer_by_checkpoint: Mapping[str, Any] = field(default_factory=dict)


def _stored_metric(store: Any, digest_value: str | None) -> Any | None:
    from .eval2 import Eval2TargetMetricRecord

    if digest_value is None or not store.has(digest_value):
        return None
    return store.get(digest_value, Eval2TargetMetricRecord.from_dict)


def authenticated_post_selection_candidate_records(
    context: PostSelectionContext,
    *,
    candidate_record_digests: Sequence[str],
    runtime_summary_digest: str,
    representative_record_digest: str | None = None,
) -> tuple[Any, ...]:
    """Authenticate the complete durable candidate universe for one outcome.

    A run assessment is not current merely because its selected record and
    monitor metric can be read.  The outcome was decided from every TRAIN2
    checkpoint, so every referenced candidate, its target metric, measurement
    identity, and any replay metrics must still be present and internally
    consistent.  This is deliberately a read through the existing evidence
    store; it creates no second candidate index or alternate authority.
    """

    from .eval2 import Eval2CheckpointRecord, Eval2TargetMetricRecord

    digests = tuple(
        validate_digest(str(value), name="candidate_record_digest")
        for value in candidate_record_digests
    )
    if not digests or len(set(digests)) != len(digests):
        raise PostSelectionError(
            "A current post-selection outcome must bind a non-empty unique "
            "candidate-record set."
        )
    # The outcome's terminal runtime-summary digest and each checkpoint's
    # trajectory-point runtime-summary digest are distinct authenticated
    # records.  The former closes TRAIN2; the latter describes the checkpoint
    # observation that became a candidate.  Both are required, but they are
    # not expected to be byte-identical.
    validate_digest(str(runtime_summary_digest), name="runtime_summary_digest")
    store = context.evidence_store
    records: list[Any] = []
    for candidate_digest in digests:
        try:
            record = store.get(candidate_digest, Eval2CheckpointRecord.from_dict)
        except Exception as exc:  # noqa: BLE001 - unreadable evidence is stale
            raise PostSelectionError(
                "A current post-selection outcome references an unreadable "
                f"candidate record {candidate_digest[:12]}...; rerun the assessment."
            ) from exc
        if record.content_digest != candidate_digest:
            raise PostSelectionError(
                "A post-selection candidate record was resolved under a different "
                "content identity."
            )
        if record.evaluation_record_digest != record.target_metrics.content_digest:
            raise PostSelectionError(
                "A post-selection candidate does not bind its embedded target "
                "metric record."
            )
        try:
            target_metric = store.get(
                record.evaluation_record_digest, Eval2TargetMetricRecord.from_dict
            )
            store.get(
                record.target_metrics.target_role_digest,
                EvaluationMeasurementIdentity.from_dict,
            )
        except Exception as exc:  # noqa: BLE001 - incomplete evidence is stale
            raise PostSelectionError(
                "A post-selection candidate is missing its durable target metric "
                "or assessment-independent measurement identity."
            ) from exc
        if target_metric.content_digest != record.target_metrics.content_digest:
            raise PostSelectionError(
                "A post-selection candidate's stored target metric differs from "
                "the metric embedded in its candidate record."
            )
        for metric_digest in (
            record.replay_candidate_metric_record_digest,
            record.replay_foundation_metric_record_digest,
        ):
            if metric_digest is None:
                continue
            try:
                replay_metric = store.get(
                    metric_digest, Eval2TargetMetricRecord.from_dict
                )
                store.get(
                    replay_metric.target_role_digest,
                    EvaluationMeasurementIdentity.from_dict,
                )
            except Exception as exc:  # noqa: BLE001 - incomplete evidence is stale
                raise PostSelectionError(
                    "A post-selection candidate is missing a durable replay metric "
                    "or measurement identity."
                ) from exc
        records.append(record)

    checkpoint_digests = tuple(
        record.trajectory_point.checkpoint_sha256 for record in records
    )
    if len(set(checkpoint_digests)) != len(checkpoint_digests):
        raise PostSelectionError(
            "A post-selection outcome binds more than one candidate record to the "
            "same checkpoint bytes."
        )
    if representative_record_digest is not None:
        representative_digest = validate_digest(
            str(representative_record_digest),
            name="representative_record_digest",
        )
        if representative_digest not in digests:
            raise PostSelectionError(
                "A post-selection representative is outside the complete candidate "
                "set."
            )
        representative = next(
            record for record in records if record.content_digest == representative_digest
        )
        if not representative.admissible:
            raise PostSelectionError(
                "A post-selection representative record is not admissible under its "
                "own persisted candidate outcome."
            )
    return tuple(records)


def _publishable_measurement(
    identity: EvaluationMeasurementIdentity, metrics: Any
) -> tuple[Any, Any]:
    if metrics.target_role_digest != identity.content_digest:
        raise PostSelectionExecutionError(
            "An EVAL2 metric record does not bind the measurement identity it claims."
        )
    return identity, metrics


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
    training_root_identity: str,
    reusable: _ReusableMeasurements | None = None,
) -> tuple[tuple[Any, ...], Any | None, Any | None, tuple[Any, ...]]:
    """Assess every governed checkpoint and freeze the strict representative.

    Hard admissibility is composed here, after authenticated TRAIN2, and not
    before.  Every catalogued checkpoint becomes a candidate.  For each one the
    assessment-independent measurement identities are derived first (common
    monitor, candidate TRUE_DFT replay, foundation replay baseline); a
    previously published measurement is reused only when its bound identity is
    exactly equal, otherwise the measurement is recomputed from the preserved
    authenticated checkpoint.  The representative is the D2.DEF.059A minimum
    over hard-admissible candidates, or ``None``.  Returned measurements must be
    published before any assessment binds them.
    """

    from .eval2 import assess_eval2_checkpoint

    selected = context.selected
    admissibility = context.checkpoint_admissibility(run_plan)
    extxyz_policy = context.method_policies.extxyz
    optimizer_policy = _optimizer_policy_for(
        context,
        seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
    )
    batch_width = execution_batch_width(optimizer_policy)
    from .target_size_execution import target_size_evaluation_model_state

    evaluation_model_state = target_size_evaluation_model_state(optimizer_policy)
    offered = reusable or _ReusableMeasurements()
    store = context.evidence_store
    metric_policy = _eval2_target_metric_policy_digest()
    checkpoint_realization = _checkpoint_provider_realization(context)

    candidates = post_selection_checkpoint_candidates(
        run_identity=training_root_identity,
        checkpoint_directory=checkpoint_directory,
        runtime_plan=runtime_plan,
    )
    catalog = _checkpoint_catalog(training_root_identity, checkpoint_directory)
    monitor_blocks = _component_block_ids(selected, monitor_frame_uids)
    monitor_artifact = materialization.checkpoint_monitor_artifact

    replay_monitor_artifact = None
    replay_monitor_path = None
    replay_blocks: tuple[str, ...] = ()
    baseline_identity = None
    if admissibility.replay_enabled:
        if replay_resolution is None or replay_resolution.monitor_artifact is None:
            raise PostSelectionError("Missing required TRUE_DFT replay monitor artifact.")
        replay_monitor_artifact = replay_resolution.monitor_artifact
        replay_monitor_path = Path(replay_resolution.monitor_path)
        if not replay_monitor_path.is_file():
            raise PostSelectionError(
                f"TRUE_DFT replay monitor file is missing: {replay_monitor_path}"
            )
        if sha256_file_cached(replay_monitor_path) != replay_monitor_artifact.sha256:
            raise PostSelectionError("TRUE_DFT replay monitor file bytes changed on disk.")
        replay_blocks = tuple(
            f"replay_block_{i}" for i in range(replay_monitor_artifact.configuration_count)
        )
        foundation_identity = context.method_policies.foundation_potential_identity
        if context.method_policies.foundation_model is None or foundation_identity is None:
            # A replay baseline without authenticated foundation identity has
            # nothing scientific to key on; a runtime locator is not identity.
            raise PostSelectionExecutionError(
                "Replay admissibility evaluation requires a configured, canonically "
                "identified foundation model."
            )
        baseline_identity = post_selection_eval_role_digest(
            dataset_role="replay_monitor_baseline",
            artifact=replay_monitor_artifact,
            model_state={
                "kind": "foundation_checkpoint",
                "foundation_content_digest": foundation_identity.canonical_content_digest,
                "foundation_head": context.method_policies.foundation_head,
            },
            provider_realization=_foundation_provider_realization(context),
            prediction_head=context.method_policies.foundation_head,
            metric_policy_digest=metric_policy,
            block_ids=replay_blocks,
        )

    measurements: list[Any] = []
    baseline_metrics = None
    records = []
    for point in candidates:
        checkpoint = catalog.checkpoint_by_sha256(point.checkpoint_sha256)
        model_state = _checkpoint_model_state(checkpoint.sha256, evaluation_model_state)
        monitor_identity = post_selection_eval_role_digest(
            dataset_role=DATASET_ROLE_CHECKPOINT_MONITOR,
            artifact=monitor_artifact,
            model_state=model_state,
            provider_realization=checkpoint_realization,
            prediction_head=runtime_plan.target_head_name,
            metric_policy_digest=metric_policy,
            block_ids=monitor_blocks,
        )
        replay_identity = (
            None
            if replay_monitor_artifact is None
            else post_selection_eval_role_digest(
                dataset_role="replay_monitor",
                artifact=replay_monitor_artifact,
                model_state=model_state,
                provider_realization=checkpoint_realization,
                prediction_head=runtime_plan.target_head_name,
                metric_policy_digest=metric_policy,
                block_ids=replay_blocks,
            )
        )
        prior = offered.candidates.get(point.checkpoint_sha256)
        metrics = None
        candidate_replay = None
        if prior is not None and prior.trajectory_point == point:
            if prior.target_metrics.target_role_digest == monitor_identity.content_digest:
                metrics = prior.target_metrics
            if replay_identity is not None:
                reused = _stored_metric(store, prior.replay_candidate_metric_record_digest)
                if (
                    reused is not None
                    and reused.target_role_digest == replay_identity.content_digest
                ):
                    candidate_replay = reused
                if baseline_metrics is None:
                    reused = _stored_metric(
                        store, prior.replay_foundation_metric_record_digest
                    )
                    if (
                        reused is not None
                        and reused.target_role_digest == baseline_identity.content_digest
                    ):
                        baseline_metrics = reused
        needs_provider = metrics is None or (
            replay_identity is not None and candidate_replay is None
        )
        if needs_provider:
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
                foundation_model_path=context.train2_foundation_path,
            )
            try:
                if metrics is None:
                    metrics = evaluate_post_selection_dataset(
                        measurement=monitor_identity,
                        artifact=monitor_artifact,
                        dataset_role=DATASET_ROLE_CHECKPOINT_MONITOR,
                        root_directory=material_directory,
                        provider=provider,
                        block_ids=monitor_blocks,
                        execution_batch_width=batch_width,
                        extxyz_policy=extxyz_policy,
                        inference_evaluator=context.inference_evaluator,
                    )
                if replay_identity is not None and candidate_replay is None:
                    candidate_replay = evaluate_post_selection_dataset(
                        measurement=replay_identity,
                        artifact=replay_monitor_artifact,
                        dataset_role="replay_monitor",
                        root_directory=replay_monitor_path.parent,
                        provider=provider,
                        block_ids=replay_blocks,
                        execution_batch_width=batch_width,
                        extxyz_policy=extxyz_policy,
                        inference_evaluator=context.inference_evaluator,
                    )
            finally:
                _retire_post_selection_provider(provider)
        measurements.append(_publishable_measurement(monitor_identity, metrics))
        if replay_identity is not None:
            measurements.append(_publishable_measurement(replay_identity, candidate_replay))
            if baseline_metrics is None:
                cache = context._baseline_replay_cache
                cached = cache.get(baseline_identity.content_digest)
                if cached is not None:
                    baseline_metrics = cached
                else:
                    from .post_selection_execution import (
                        build_post_selection_foundation_baseline_provider,
                    )

                    baseline_provider = build_post_selection_foundation_baseline_provider(
                        foundation_path=context.method_policies.foundation_model,
                        foundation_identity=(
                            context.method_policies.foundation_potential_identity
                        ),
                        foundation_head=context.method_policies.foundation_head,
                        device=context.method_policies.device,
                        default_dtype=context.method_policies.default_dtype,
                    )
                    try:
                        baseline_metrics = evaluate_post_selection_dataset(
                            measurement=baseline_identity,
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
                cache[baseline_identity.content_digest] = baseline_metrics
            measurements.append(_publishable_measurement(baseline_identity, baseline_metrics))
        record = assess_eval2_checkpoint(
            point,
            evaluation_record_digest=metrics.content_digest,
            target_metrics=metrics,
            admissibility_policy=admissibility,
            replay_candidate_force_rmse_ev_per_angstrom=(
                None
                if candidate_replay is None
                else candidate_replay.force_component_rmse_ev_per_angstrom
            ),
            replay_foundation_force_rmse_ev_per_angstrom=(
                None
                if baseline_metrics is None
                else baseline_metrics.force_component_rmse_ev_per_angstrom
            ),
            replay_label_mode=None if candidate_replay is None else "true_dft",
            replay_candidate_metric_record_digest=(
                None if candidate_replay is None else candidate_replay.content_digest
            ),
            replay_foundation_metric_record_digest=(
                None if baseline_metrics is None else baseline_metrics.content_digest
            ),
        )
        records.append(record)

    ordered = tuple(sorted(records, key=lambda item: item.trajectory_point.epoch))
    representative = select_post_selection_representative(ordered)
    monitor_metrics = None if representative is None else representative.target_metrics
    return ordered, representative, monitor_metrics, tuple(measurements)


def _abort_post_selection_run_if_cancelled(
    cancellation_event: Any | None, *, phase: str
) -> None:
    """Leave a run at a recoverable pre-trainer boundary once stopped.

    The scheduler's per-slot stop handle already travels down this path to the
    trainer. Reading the same handle at run-phase boundaries that precede the
    trainer is how a demoted slot stops spending preparation/materialization
    effort it will not use; it is not a second cancellation mechanism and it
    produces the same explicit cancellation outcome the trainer produces, so the
    scheduler classifies it as a retractable demotion rather than a failure.

    Every call site sits before any partial fold evidence exists: the run root
    stays under the existing materialization/checkpoint authority and the next
    attempt resumes through the ordinary continuation path.
    """

    if cancellation_event is not None and cancellation_event.is_set():
        raise PostSelectionCancelledError(
            f"Post-selection run stopped at the {phase} boundary before training."
        )


@dataclass(frozen=True, slots=True)
class _TrainingRoot:
    """Where one run's training bytes live, and under which identity.

    For every post-cutover run the root is ``runs/<training trajectory>``.  A
    legacy root is used only through the one-time historical derivation, which
    proves training equivalence from authenticated stored evidence; its name
    is the historical full-plan-derived run identity and is never renamed.
    """

    path: Path
    identity: str
    legacy: Any | None = None


def resolve_post_selection_training_root(
    context: PostSelectionContext, run_plan: Any
) -> _TrainingRoot:
    """Resolve the current or (one-time) legacy training root of a run position."""

    root = (
        post_selection_root(context.paths, context.selected.binding.campaign_generation)
        / "runs"
        / run_plan.run_identity
    )
    if root.is_dir() and any(root.iterdir()):
        return _TrainingRoot(path=root, identity=run_plan.run_identity)
    legacy = resolve_legacy_training_root(context, run_plan)
    if legacy is not None:
        return _TrainingRoot(path=legacy.root, identity=legacy.root.name, legacy=legacy)
    return _TrainingRoot(path=root, identity=run_plan.run_identity)


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
    reusable: _ReusableMeasurements | None = None,
) -> PostSelectionRunResult | None:
    """Train (if needed), seal, then evaluate one run; publish nothing.

    Order is enforced by construction.  An unsealed root trains under its
    pre-fit trajectory until authenticated terminal TRAIN2, and is then sealed
    as a training-only root *before* EVAL2.  A sealed root is never written
    again: EVAL2 reads it read-only under the same run-activity lease, so
    archive/dedup/reclamation cannot move its bytes mid-evaluation.  The
    representative is frozen from the common monitor before any held-out
    transport exists; held-out EXTXYZ is realized only afterwards, in bounded
    attempt scratch outside the root.  Fresh held-out identity/metric evidence
    is committed before that scratch is reclaimed; the caller publishes the
    remaining returned measurements and assessment outside this lease.

    ``stop_after_training`` ends at the sealed terminal boundary and returns
    ``None``; the TRAIN scheduler uses it so a training slot never carries EVAL2.
    """

    root = resolve_post_selection_training_root(context, run_plan)
    root.path.mkdir(parents=True, exist_ok=True)
    with post_selection_run_activity_lease(root.path):
        return _execute_post_selection_run_locked(
            context,
            run_plan=run_plan,
            budget_policy=budget_policy,
            training_frame_uids=training_frame_uids,
            monitor_frame_uids=monitor_frame_uids,
            outer_evaluation_frame_uids=outer_evaluation_frame_uids,
            root=root,
            progress_context=progress_context,
            cancellation_event=cancellation_event,
            progress_callback=progress_callback,
            progress_observer=progress_observer,
            telemetry_ref=telemetry_ref,
            stop_after_training=stop_after_training,
            reusable=reusable,
        )


_POST_SELECTION_MATERIALIZATION_FILES = frozenset(
    {
        "materialization.json",
        POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_FILENAME,
        "post_selection_mace_config.yaml",
        "mace_run_config.yaml",
        "target_train.extxyz",
        "target_train.extxyz.manifest.json",
        "checkpoint_monitor.extxyz",
        "checkpoint_monitor.extxyz.manifest.json",
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
    from .persistence import fsync_parent_directory

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


def _validate_post_selection_materialization_artifacts(
    selected: CurrentSelectedTrainingContext,
    *,
    material_directory: Path,
    record: PostSelectionMaterialization,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    preparation: Any,
    extxyz_policy: Any,
) -> None:
    """Re-authenticate the training-only DATA8 artifacts before treating a record as owned."""

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
    preparation: Any,
    optimizer_policy: Any,
    extxyz_policy: Any,
    replay_resolution: Any | None,
    continuation_summary: Any | None,
) -> tuple[PostSelectionMaterialization | None, bool]:
    """Classify existing P5 materialization before any replacement is allowed.

    Returns ``(record, rebuild)``.  ``rebuild`` is granted only for an absent
    or interrupted (record-less) materialization.  A complete record must
    authenticate as exactly the current run's executable configuration; any
    other state is preserved for diagnosis.  Pre-restoration representations
    cannot reach this owner as current: their schemas and run identities are
    superseded.
    """

    if any(
        (run_root / name).exists() or (run_root / name).is_symlink()
        for name in (*RUN_TERMINAL_RECORD_NAMES, RUN_COMPLETION_ANCHOR_FILENAME)
    ):
        _post_selection_recovery_error(
            "P5 run root already carries terminal evidence or a completion seal; "
            "refusing to re-enter its materialization recovery path."
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
        return None, False
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
        return None, True
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
        record.training_trajectory_identity != run_plan.training_trajectory_identity
        or record.preparation_digest != preparation.content_digest
        or Path(record.output_directory).resolve() != material_directory.resolve()
    ):
        _post_selection_recovery_error(
            "P5 materialization is internally valid but belongs to a different "
            "training trajectory, preparation, or output directory; preserving it."
        )
    _validate_post_selection_materialization_artifacts(
        context.selected,
        material_directory=material_directory,
        record=record,
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
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
        run_identity=run_plan.training_trajectory_identity,
        optimizer_seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
        preparation=preparation,
        objective=context.method_policies.objective,
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
    if config_payload != expected_config or config_bytes != expected_bytes:
        _post_selection_recovery_error(
            "P5 materialization is internally valid but its protected executable "
            "configuration is foreign to the current run; preserving it."
        )
    return record, False


@dataclass(frozen=True, slots=True)
class _PostSelectionRunSetup:
    """Authenticated, non-mutating setup shared by execution and preflight."""

    material_directory: Path
    checkpoint_directory: Path
    optimizer_policy: Any
    extxyz_policy: Any
    replay_resolution: Any | None
    preparation: Any | None
    runtime_plan: Any
    continuation_summary: Any | None
    start_epoch: int
    rebuild_materialization: bool


def _fit_post_selection_run_preparation(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    material_directory: Path,
    optimizer_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    acquire_residual_inputs: bool,
) -> Any:
    """Fit one run's preparation through the P5 preparation owner.

    Foundation modes need exact selected-head residual inputs over the fit
    membership.  A fresh run acquires them once and publishes them into its
    materialization before any other artifact; a recovering run re-fits from
    that immutable record rather than repeating accelerator inference.  The
    common monitor's and held-out frames are governed transfer consumers whose
    geometry only (the label-blind composition projection) is inspected.
    """

    policy = context.method_policies.preparation
    training = tuple(str(value) for value in training_frame_uids)
    consumers = tuple(str(value) for value in monitor_frame_uids) + tuple(
        () if outer_evaluation_frame_uids is None else outer_evaluation_frame_uids
    )
    inputs = None
    monitor_digest = None
    if policy.is_foundation:
        from .bounded_inference import execution_batch_width
        from .target_size_execution import publish_immutable_json_create_or_verify

        monitor_record, _separation = context.common_target_monitor()
        if tuple(monitor_record.selected_identities) != tuple(
            str(value) for value in monitor_frame_uids
        ):
            raise PostSelectionError(
                "Foundation-P5 checkpoint control must use the exact common target monitor."
            )
        monitor_digest = monitor_record.content_digest
        path = material_directory / POST_SELECTION_FOUNDATION_RESIDUAL_INPUTS_FILENAME
        if path.is_file():
            try:
                inputs = FoundationResidualInputs.from_dict(
                    json.loads(path.read_text(encoding="utf-8"))
                )
            except Exception as exc:
                _post_selection_recovery_error(
                    "P5 foundation-residual inputs are malformed; preserving "
                    "diagnostic state.",
                    exc,
                )
        elif acquire_residual_inputs:
            method_policies = context.method_policies
            inputs = resolve_foundation_residual_inputs(
                context.selected,
                membership=training,
                foundation_model_path=method_policies.foundation_model,
                foundation_identity=method_policies.foundation_potential_identity,
                foundation_head=policy.foundation_head,
                device=method_policies.device,
                default_dtype=method_policies.default_dtype,
                execution_batch_width=execution_batch_width(optimizer_policy),
                inference_evaluator=context.inference_evaluator,
            )
            material_directory.mkdir(parents=True, exist_ok=True)
            publish_immutable_json_create_or_verify(
                path, inputs.to_dict(), deserializer=FoundationResidualInputs.from_dict
            )
        else:
            _post_selection_recovery_error(
                "P5 foundation materialization has no persisted selected-head "
                "residual inputs; preserving diagnostic state."
            )
    return fit_post_selection_preparation(
        context.selected,
        membership=training,
        training_trajectory_identity=run_plan.training_trajectory_identity,
        preparation_policy=policy,
        foundation_residual_inputs=inputs,
        common_monitor_record_digest=monitor_digest,
        consumer_frame_uids=consumers,
    )


def _post_selection_runtime_plan_for(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    optimizer_policy: Any,
    structures_per_epoch: int,
    replay_resolution: Any | None,
) -> Any:
    return post_selection_runtime_plan(
        method=context.method,
        optimizer_policy=optimizer_policy,
        budget_policy=budget_policy,
        structures_per_epoch=int(structures_per_epoch),
        learning_rate_policy=context.method_policies.learning_rate_schedule,
        replay_monitor_enabled=context.method_policies.replay_enabled,
        true_replay_monitor_sha256=(
            replay_resolution.monitor_artifact.sha256
            if replay_resolution is not None
            else None
        ),
        target_head_name=context.method_policies.target_head_name,
        replay_head_name=context.method_policies.replay_head_name,
    )


def _training_replay_resolution(context: PostSelectionContext) -> Any | None:
    """Replay execution comes from the training method/replay lineage only.

    No checkpoint-decision policy is consulted: whether TRAIN2 trains a replay
    head and monitors TRUE_DFT replay is a property of the training method, so
    a changed hard/warning/target/selection policy cannot block or alter
    training recovery.
    """

    if not context.method_policies.replay_enabled:
        return None
    replay_resolution = _resolve_post_selection_replay_resolution(
        context, require_train=True
    )
    if replay_resolution is None or replay_resolution.monitor_artifact is None:
        raise PostSelectionError(
            "Could not resolve TRUE_DFT replay monitor artifact for replay-enabled run."
        )
    return replay_resolution


def _prepare_post_selection_run(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    run_root: Path,
) -> _PostSelectionRunSetup:
    """Authenticate one unsealed run's recoverable state without changing files."""

    material_directory = run_root / "materialization"
    checkpoint_directory = run_root / "checkpoints"
    optimizer_policy = _optimizer_policy_for(
        context, seed=run_plan.optimizer_seed, planned_epochs=run_plan.planned_epochs
    )
    extxyz_policy = context.method_policies.extxyz
    replay_resolution = _training_replay_resolution(context)

    # A durable materialization is fitted from current authority in memory
    # before it is authenticated or replaced. This is the same recovery
    # preparation used by the execution owner; setup itself publishes nothing.
    preparation = None
    if (material_directory / "materialization.json").exists():
        preparation = _fit_post_selection_run_preparation(
            context,
            run_plan=run_plan,
            material_directory=material_directory,
            optimizer_policy=optimizer_policy,
            training_frame_uids=training_frame_uids,
            monitor_frame_uids=monitor_frame_uids,
            outer_evaluation_frame_uids=outer_evaluation_frame_uids,
            acquire_residual_inputs=False,
        )
    runtime_plan = _post_selection_runtime_plan_for(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        optimizer_policy=optimizer_policy,
        structures_per_epoch=(
            len(preparation.membership)
            if preparation is not None
            else len(tuple(str(value) for value in training_frame_uids))
        ),
        replay_resolution=replay_resolution,
    )
    continuation_summary, start_epoch = _authenticate_post_selection_continuation(
        checkpoint_directory,
        runtime_plan=runtime_plan,
    )
    _record, rebuild_materialization = _classify_post_selection_materialization(
        context,
        run_plan=run_plan,
        material_directory=material_directory,
        run_root=run_root,
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
        preparation=preparation,
        optimizer_policy=optimizer_policy,
        extxyz_policy=extxyz_policy,
        replay_resolution=replay_resolution,
        continuation_summary=continuation_summary,
    )
    return _PostSelectionRunSetup(
        material_directory=material_directory,
        checkpoint_directory=checkpoint_directory,
        optimizer_policy=optimizer_policy,
        extxyz_policy=extxyz_policy,
        replay_resolution=replay_resolution,
        preparation=preparation,
        runtime_plan=runtime_plan,
        continuation_summary=continuation_summary,
        start_epoch=start_epoch,
        rebuild_materialization=rebuild_materialization,
    )


@dataclass(frozen=True, slots=True)
class _SealedTrainingState:
    """The authenticated read-only training state of one sealed root."""

    material_directory: Path
    checkpoint_directory: Path
    materialization: Any
    summary: Any
    runtime_plan: Any
    replay_resolution: Any | None


def _authenticate_sealed_training_root(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    root: _TrainingRoot,
    completion: Any,
) -> _SealedTrainingState:
    """Authenticate a sealed training root for EVAL2 without writing to it.

    The compact completion anchor's TRAIN2 terminal proof names the exact
    runtime summary and materialization it sealed; both are re-read and must
    reproduce those digests, the materialization must belong to this run's
    training trajectory, and the summary must belong to the runtime plan the
    current training method derives.  Nothing here publishes, locks, or
    creates a node beneath the root.
    """

    from .train2_runtime import load_train2_runtime_summary

    if root.legacy is not None:
        return _authenticate_legacy_sealed_training_root(
            context,
            run_plan=run_plan,
            budget_policy=budget_policy,
            root=root,
            completion=completion,
        )
    proof = completion.terminal_proof
    if proof is None:
        _post_selection_recovery_error(
            "A post-cutover training root carries a pre-cutover assessment-coupled "
            "completion proof; its training identity is not current."
        )
    material_directory = root.path / "materialization"
    checkpoint_directory = root.path / "checkpoints"
    try:
        payload = _load_owner_record(material_directory / "materialization.json")
        materialization = PostSelectionMaterialization.from_dict(payload)
    except Exception as exc:
        _post_selection_recovery_error(
            "Sealed training root materialization does not authenticate.", exc
        )
    if (
        materialization.content_digest != proof["materialization_digest"]
        or materialization.training_trajectory_identity
        != run_plan.training_trajectory_identity
    ):
        _post_selection_recovery_error(
            "Sealed training root materialization is not the one its completion "
            "proof sealed for this training trajectory."
        )
    try:
        summary = load_train2_runtime_summary(checkpoint_directory)
    except Exception as exc:
        _post_selection_recovery_error(
            "Sealed training root TRAIN2 summary does not authenticate.", exc
        )
    if summary.content_digest != proof["runtime_summary_digest"]:
        _post_selection_recovery_error(
            "Sealed training root TRAIN2 summary is not the terminal summary its "
            "completion proof sealed."
        )
    replay_resolution = _training_replay_resolution(context)
    optimizer_policy = _optimizer_policy_for(
        context, seed=run_plan.optimizer_seed, planned_epochs=run_plan.planned_epochs
    )
    runtime_plan = _post_selection_runtime_plan_for(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        optimizer_policy=optimizer_policy,
        structures_per_epoch=int(materialization.target_train_artifact.configuration_count),
        replay_resolution=replay_resolution,
    )
    if (
        summary.plan_digest != runtime_plan.content_digest
        or proof["runtime_plan_digest"] != runtime_plan.content_digest
    ):
        _post_selection_recovery_error(
            "Sealed training root was trained under a different TRAIN2 runtime plan "
            "than the current training method derives; it is not this trajectory."
        )
    return _SealedTrainingState(
        material_directory=material_directory,
        checkpoint_directory=checkpoint_directory,
        materialization=materialization,
        summary=summary,
        runtime_plan=runtime_plan,
        replay_resolution=replay_resolution,
    )


def _train_post_selection_run(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    run_root: Path,
    progress_context: Mapping[str, Any] | None,
    cancellation_event: Any | None,
    progress_callback: Callable[[str], None] | None,
    progress_observer: Callable[[Mapping[str, Any]], None] | None,
    telemetry_ref: Any | None,
    launch_trainer: bool = True,
) -> bool:
    """Train one unsealed root to authenticated terminal TRAIN2, then seal it.

    ``launch_trainer=False`` is recovery normalization: an authenticated
    terminal continuation is sealed through exactly this path, while a root
    that still needs trainer execution is left untouched and reported by the
    ``False`` return instead of being trained.
    """

    from ._campaign_cli_core import _cfg

    context_cfg = getattr(context, "cfg", None)
    selected = context.selected
    _abort_post_selection_run_if_cancelled(cancellation_event, phase="run-entry")
    setup = _prepare_post_selection_run(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
        outer_evaluation_frame_uids=outer_evaluation_frame_uids,
        run_root=run_root,
    )
    material_directory = setup.material_directory
    checkpoint_directory = setup.checkpoint_directory
    optimizer_policy = setup.optimizer_policy
    replay_resolution = setup.replay_resolution
    preparation = setup.preparation
    runtime_plan = setup.runtime_plan
    continuation_summary = setup.continuation_summary
    terminal = continuation_summary is not None and (
        continuation_summary.completed_epochs == runtime_plan.execution_epoch_limit
    )
    if not terminal and not launch_trainer:
        return False
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
    if setup.rebuild_materialization:
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

    if preparation is None:
        preparation = _fit_post_selection_run_preparation(
            context,
            run_plan=run_plan,
            material_directory=material_directory,
            optimizer_policy=optimizer_policy,
            training_frame_uids=training_frame_uids,
            monitor_frame_uids=monitor_frame_uids,
            outer_evaluation_frame_uids=outer_evaluation_frame_uids,
            acquire_residual_inputs=True,
        )
    preparation, materialization = materialize_post_selection_run(
        selected,
        run_plan=run_plan,
        method=context.method,
        training_frame_uids=training_frame_uids,
        monitor_frame_uids=monitor_frame_uids,
        transfer_consumer_frame_uids=tuple(outer_evaluation_frame_uids or ()),
        optimizer_policy=optimizer_policy,
        extxyz_policy=setup.extxyz_policy,
        output_directory=material_directory,
        preparation=preparation,
        objective=context.method_policies.objective,
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

    if terminal:
        # A crash after the last durable epoch but before the seal can reuse
        # the fully authenticated summary without a zero-epoch trainer call.
        summary = continuation_summary
    else:
        # The last boundary before the trainer takes ownership of a child
        # process: stopping here avoids launching MACE for a slot that has
        # already been demoted, and the materialization just written stays
        # canonical for the restart.
        _abort_post_selection_run_if_cancelled(
            cancellation_event, phase="pre-training"
        )
        summary = context.trainer(
            PostSelectionRungRequest(
                plan=runtime_plan,
                run_plan=run_plan,
                materialization=materialization,
                materialization_directory=material_directory,
                checkpoint_directory=checkpoint_directory,
                optimizer_policy=optimizer_policy,
                start_epoch=setup.start_epoch,
                foundation_identity=context.method_policies.foundation_potential_identity,
                foundation_model_path=context.train2_foundation_path,
                training_realization=context.train2_foundation_realization,
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
    if int(summary.completed_epochs) != int(runtime_plan.budget_policy.planned_epochs):
        raise PostSelectionExecutionError(
            "Fixed-budget TRAIN2 did not reach its terminal epoch; the training root "
            "is not sealable."
        )
    # The realized training records are evidence outside the root; the seal is
    # the root's own create-once completion proof, taken under the run lease.
    store = context.evidence_store
    store.put(preparation)
    store.put(materialization)
    record_post_selection_training_completion(
        run_root,
        runtime_summary=summary,
        runtime_plan_digest=runtime_plan.content_digest,
        materialization_digest=materialization.content_digest,
    )
    return True


def _execute_post_selection_run_locked(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    training_frame_uids: Sequence[str],
    monitor_frame_uids: Sequence[str],
    outer_evaluation_frame_uids: Sequence[str] | None,
    root: _TrainingRoot,
    progress_context: Mapping[str, Any] | None = None,
    cancellation_event: Any | None = None,
    progress_callback: Callable[[str], None] | None = None,
    progress_observer: Callable[[Mapping[str, Any]], None] | None = None,
    telemetry_ref: Any | None = None,
    stop_after_training: bool = False,
    reusable: _ReusableMeasurements | None = None,
) -> PostSelectionRunResult | None:
    """The run body, executed while the training root's activity lease is held."""

    completion, _why = read_post_selection_run_completion(root.path)
    if completion is None:
        if root.legacy is not None:
            _complete_legacy_training_root(
                context,
                run_plan=run_plan,
                budget_policy=budget_policy,
                root=root,
                progress_context=progress_context,
                cancellation_event=cancellation_event,
                progress_callback=progress_callback,
                progress_observer=progress_observer,
                telemetry_ref=telemetry_ref,
            )
        else:
            _train_post_selection_run(
                context,
                run_plan=run_plan,
                budget_policy=budget_policy,
                training_frame_uids=training_frame_uids,
                monitor_frame_uids=monitor_frame_uids,
                outer_evaluation_frame_uids=outer_evaluation_frame_uids,
                run_root=root.path,
                progress_context=progress_context,
                cancellation_event=cancellation_event,
                progress_callback=progress_callback,
                progress_observer=progress_observer,
                telemetry_ref=telemetry_ref,
            )
        completion, why = read_post_selection_run_completion(root.path)
        if completion is None:
            raise PostSelectionExecutionError(
                f"Training root {root.identity[:12]}... is not sealed after terminal "
                f"TRAIN2: {why}"
            )
    if stop_after_training:
        # TRAIN2 ownership ends at the sealed terminal boundary; an interruption
        # before EVAL2 resumes from the seal without any trainer launch.
        return None

    sealed = _authenticate_sealed_training_root(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        root=root,
        completion=completion,
    )
    candidates, representative, monitor_metrics, measurements = (
        evaluate_post_selection_run_candidates(
            context,
            run_plan=run_plan,
            runtime_plan=sealed.runtime_plan,
            materialization=sealed.materialization,
            material_directory=sealed.material_directory,
            checkpoint_directory=sealed.checkpoint_directory,
            summary=sealed.summary,
            monitor_frame_uids=monitor_frame_uids,
            replay_resolution=sealed.replay_resolution,
            training_root_identity=root.identity,
            reusable=reusable,
        )
    )
    outer_metrics = None
    outer_measurements: tuple[Any, ...] = ()
    if representative is not None and outer_evaluation_frame_uids:
        outer_metrics, outer_measurements = _evaluate_held_out_representative(
            context,
            run_plan=run_plan,
            root=root,
            sealed=sealed,
            representative=representative,
            outer_evaluation_frame_uids=outer_evaluation_frame_uids,
            reusable=reusable,
        )
    diagnostics = build_post_selection_checkpoint_diagnostics(
        context,
        run_plan=run_plan,
        candidates=candidates,
        representative=representative,
    )
    return PostSelectionRunResult(
        training_root_identity=root.identity,
        materialization=sealed.materialization,
        runtime_summary_digest=sealed.summary.content_digest,
        candidates=candidates,
        representative=representative,
        monitor_metrics=monitor_metrics,
        outer_metrics=outer_metrics,
        measurements=measurements + outer_measurements,
        diagnostics=diagnostics,
    )


def _evaluate_held_out_representative(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    root: _TrainingRoot,
    sealed: _SealedTrainingState,
    representative: Any,
    outer_evaluation_frame_uids: Sequence[str],
    reusable: _ReusableMeasurements | None,
) -> tuple[Any, tuple[Any, ...]]:
    """Measure the frozen representative on its held-out fold, outside the root.

    The held-out EXTXYZ is realized only now, after D2.DEF.059A froze the
    representative, in bounded attempt-local scratch that is not beneath any
    training root.  A fresh measurement is committed to the existing evidence
    store before this call returns, so the ``TemporaryDirectory`` cleanup is
    downstream of durable measurement publication.  Its exact membership,
    serialized label/reference bytes and transport policy enter the immutable
    measurement identity - the scratch locator does not - so a later retry may
    regenerate identical transport and reuse the published measurement.
    """

    import tempfile

    from .target_size_execution import target_size_evaluation_model_state

    optimizer_policy = _optimizer_policy_for(
        context,
        seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
    )
    evaluation_model_state = target_size_evaluation_model_state(optimizer_policy)
    checkpoint_sha256 = representative.trajectory_point.checkpoint_sha256
    frames = tuple(str(value) for value in outer_evaluation_frame_uids)
    blocks = _component_block_ids(context.selected, frames)
    offered = reusable or _ReusableMeasurements()
    with tempfile.TemporaryDirectory(prefix="mdstats-p5-eval2-held-out-") as scratch:
        scratch_path = Path(scratch).resolve()
        if root.path.resolve() in (scratch_path, *scratch_path.parents):
            raise PostSelectionExecutionError(
                "Held-out EVAL2 transport must be realized outside the training root."
            )
        artifact = write_outer_evaluation_transport(
            context.selected,
            scratch_directory=scratch_path,
            frame_uids=frames,
            extxyz_policy=context.method_policies.extxyz,
        )
        identity = post_selection_eval_role_digest(
            dataset_role=DATASET_ROLE_OUTER_EVALUATION,
            artifact=artifact,
            model_state=_checkpoint_model_state(checkpoint_sha256, evaluation_model_state),
            provider_realization=_checkpoint_provider_realization(context),
            prediction_head=sealed.runtime_plan.target_head_name,
            metric_policy_digest=_eval2_target_metric_policy_digest(),
            block_ids=blocks,
        )
        prior = offered.outer_by_checkpoint.get(checkpoint_sha256)
        if prior is not None and prior.target_role_digest == identity.content_digest:
            # The offered metric and its identity were read from the durable
            # evidence store before this attempt; no caller-side write is
            # needed for a reusable measurement.
            return prior, ()
        catalog = _checkpoint_catalog(root.identity, sealed.checkpoint_directory)
        checkpoint = catalog.checkpoint_by_sha256(checkpoint_sha256)
        provider, _evaluated = authenticate_post_selection_provider(
            materialization=sealed.materialization,
            materialization_directory=sealed.material_directory,
            checkpoint_directory=sealed.checkpoint_directory,
            checkpoint_name=Path(checkpoint.relative_path).name,
            checkpoint_sha256=checkpoint.sha256,
            checkpoint_epoch=getattr(checkpoint, "epoch", None),
            summary=sealed.summary,
            evaluation_model_state=evaluation_model_state,
            allow_forward_override=context.inference_evaluator is not None,
            foundation_model_path=context.train2_foundation_path,
        )
        try:
            metrics = evaluate_post_selection_dataset(
                measurement=identity,
                artifact=artifact,
                dataset_role=DATASET_ROLE_OUTER_EVALUATION,
                root_directory=scratch_path,
                provider=provider,
                block_ids=blocks,
                execution_batch_width=execution_batch_width(optimizer_policy),
                extxyz_policy=context.method_policies.extxyz,
                inference_evaluator=context.inference_evaluator,
            )
        finally:
            _retire_post_selection_provider(provider)
        measurement = _publishable_measurement(identity, metrics)
        # The attempt-local transport must still be live at both immutable
        # object writes.  This is the existing content-addressed evidence owner;
        # no scratch locator or publication marker becomes durable currentness.
        store = context.evidence_store
        store.put(measurement[0])
        store.put(measurement[1])
    # The fresh outer identity and metric are already durable.  Keeping them
    # out of the later generic publication pass avoids a redundant write while
    # leaving monitor/candidate evidence on that existing path.
    return metrics, ()


def publish_post_selection_run_measurements(
    context: PostSelectionContext, result: PostSelectionRunResult
) -> None:
    """Durably publish every measurement and candidate before any assessment.

    Measurement identities are published as their own authenticated records so
    each metric record's bound numerical experiment is inspectable without the
    run or any plan.  Diagnostics are published too, but nothing references
    them: warning evidence is never an assessment parent.
    """

    store = context.evidence_store
    for identity, metrics in result.measurements:
        store.put(identity)
        store.put(metrics)
    for record in result.candidates:
        store.put(record)
    store.put(result.diagnostics)


def build_post_selection_checkpoint_diagnostics(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    candidates: Sequence[Any],
    representative: Any | None,
) -> Any:
    """Diagnostic-only per-checkpoint report; also printed in bounded form.

    A representative whose replay degradation exceeds the diagnostic warning
    threshold is reported as a *warning*, never as a failed run.
    """

    from .post_selection_execution import (
        PostSelectionCheckpointDiagnostics,
        post_selection_checkpoint_diagnostic_rows,
    )

    hard = context.checkpoint_admissibility(run_plan)
    warning = context.method_policies.replay_warning_policy
    rows = post_selection_checkpoint_diagnostic_rows(
        candidates, hard_policy=hard, warning_policy=warning, representative=representative
    )
    diagnostics = PostSelectionCheckpointDiagnostics(
        training_trajectory_identity=run_plan.training_trajectory_identity,
        run_role=str(run_plan.run_role),
        hard_policy=hard.to_dict(),
        warning_policy=None if warning is None else warning.to_dict(),
        rows=rows,
        representative_candidate_identity=(
            None if representative is None else representative.stable_candidate_identity
        ),
    )
    if warning is not None:
        warned = [row for row in rows if row["warning_codes"]]
        print(
            f"[EVAL2 replay] run={run_plan.run_identity[:12]}; checkpoints={len(rows)}; "
            f"warning>{warning.warning_threshold_ev_per_angstrom:g}: {len(warned)}; "
            f"hard>{hard.replay_degradation_hard_limit_ev_per_angstrom:g} rejected: "
            f"{sum(1 for row in rows if 'replay_catastrophic_forgetting_limit_exceeded' in row['hard_rejection_reasons'])}",
            flush=True,
        )
        if diagnostics.representative_warning_codes:
            selected = next(row for row in rows if row["selected"])
            print(
                "[EVAL2 replay] WARNING (diagnostic, not a failure): the selected "
                f"representative epoch {selected['epoch']} has signed replay "
                f"degradation {selected['replay_degradation_ev_per_angstrom']:.6g} "
                f"eV/angstrom above the warning threshold "
                f"{warning.warning_threshold_ev_per_angstrom:g} and within the hard "
                f"limit {hard.replay_degradation_hard_limit_ev_per_angstrom:g}.",
                flush=True,
            )
    return diagnostics


# ---------------------------------------------------------------------------
# One-time historical (pre-cutover) training reuse
# ---------------------------------------------------------------------------


LEGACY_TRAINING_REUSE_SCHEMA = "mdstats.post-selection-legacy-training-reuse.v1"


def _historical_record(store: Any, content_digest: str | None) -> dict[str, Any] | None:
    """One authenticated store object as raw JSON, without current-schema parsing."""

    if content_digest is None:
        return None
    try:
        value = validate_digest(str(content_digest), name="content_digest")
    except TrainingDataInputError:
        return None
    raw = _load_owner_record(store.object_path(value))
    if not isinstance(raw, Mapping):
        return None
    body = {key: item for key, item in raw.items() if key != "content_digest"}
    if str(raw.get("content_digest", "")) != value or digest(body) != value:
        return None
    return dict(raw)


def post_selection_legacy_source_plan_digest(
    context: PostSelectionContext, *, kind: str
) -> str | None:
    """Carry the one authenticated historical plan locator across the cutover.

    It is read from the existing plan pointer *before* a current plan replaces
    it: a historical (pre-cutover) plan is itself the source; a current plan
    carries its own already-derived source forward.  Nothing is scanned.
    """

    from .post_selection_cv_plan import POST_SELECTION_CV_PLAN_SCHEMA_V2
    from .post_selection_production import FINAL_PRODUCTION_PLAN_SCHEMA_V2

    historical_schema = {
        POINTER_CV_PLAN: POST_SELECTION_CV_PLAN_SCHEMA_V2,
        POINTER_FINAL_PLAN: FINAL_PRODUCTION_PLAN_SCHEMA_V2,
    }[kind]
    pointer = read_current_post_selection_pointer(
        context.store, binding=context.selected.binding, kind=kind
    )
    raw = _historical_record(context.evidence_store, pointer)
    if raw is None:
        return None
    binding = raw.get("binding")
    if not isinstance(binding, Mapping) or str(binding.get("content_digest", "")) != (
        context.selected.binding.content_digest
    ):
        return None
    if raw.get("schema") == historical_schema:
        return str(pointer)
    source = raw.get("legacy_source_plan_digest")
    return None if source is None else str(source)


@dataclass(frozen=True, slots=True)
class LegacyTrainingReuse:
    """The one immutable per-trajectory reuse binding of a historical root.

    It records the historical root/run identity, the current pre-fit training
    trajectory, and the exact equivalence proof coordinates.  The root is never
    renamed, copied, linked or rewritten; this binding only authorizes reading
    it (and, if terminal-but-unsealed, its one append-only seal, or, if
    interrupted, continuation under its own historical identities).
    """

    root: Path
    run_role: str
    historical_plan_digest: str
    historical_run_plan_digest: str
    historical_method_identity_digest: str
    training_trajectory_identity: str
    proof: Mapping[str, Any]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LEGACY_TRAINING_REUSE_SCHEMA,
            "historical_run_root": self.root.name,
            "run_role": self.run_role,
            "historical_plan_digest": self.historical_plan_digest,
            "historical_run_plan_digest": self.historical_run_plan_digest,
            "historical_method_identity_digest": self.historical_method_identity_digest,
            "training_trajectory_identity": self.training_trajectory_identity,
            "proof": dict(self.proof),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}


def resolve_legacy_training_root(
    context: PostSelectionContext, run_plan: Any
) -> LegacyTrainingReuse | None:
    """Prove one historical root training-equivalent to a current trajectory.

    The source is only the authenticated historical plan the current plan
    carries; the historical root name is the historical full-plan-derived run
    identity recomputed from it.  Every training-bearing coordinate is compared
    exactly: the v3 method minus only its two retired assessment-only fields,
    selected binding, exact gradient membership, seed, horizon, common monitor,
    replay lineage, and the held-out/monitor label-blind composition identity.
    Any mismatch returns ``None`` (the run trains fresh under its current
    trajectory); nothing is inferred from names, mtimes or scans.
    """

    from .post_selection_cv_plan import PostSelectionCvPlan
    from .post_selection_identity import historical_method_training_projection
    from .post_selection_production import FinalProductionPlan
    from .post_selection_run_identity import post_selection_run_identity

    store = context.evidence_store
    trajectory = run_plan.training_trajectory
    cv = str(run_plan.run_role) == PostSelectionRunRole.POST_SELECTION_CV.value
    try:
        current_plan = (
            store.get(run_plan.cv_plan_digest, PostSelectionCvPlan.from_dict)
            if cv
            else store.get(run_plan.final_plan_digest, FinalProductionPlan.from_dict)
        )
    except Exception:
        return None
    source = current_plan.legacy_source_plan_digest
    historical = _historical_record(store, source)
    if historical is None:
        return None
    binding = historical.get("binding")
    if not isinstance(binding, Mapping) or str(binding.get("content_digest", "")) != (
        trajectory.selected_binding_digest
    ):
        return None
    method_payload = _historical_record(store, historical.get("method_identity_digest"))
    if method_payload is None:
        return None
    try:
        if historical_method_training_projection(method_payload) != (
            context.method.training_projection()
        ):
            return None
    except TrainingDataSerializationError:
        return None
    if (
        historical.get("common_monitor_record_digest")
        != trajectory.common_monitor_record_digest
        or historical.get("replay_lineage_digest") != trajectory.replay_lineage_digest
    ):
        return None
    seed = int(run_plan.optimizer_seed)
    from .post_selection_execution import transfer_consumer_composition_digest

    monitor_record, _separation = context.common_target_monitor()
    monitor_uids = tuple(monitor_record.selected_identities)
    if cv:
        fold_payload = next(
            (
                item
                for item in historical.get("folds", ())
                if int(item.get("fold_index", -1)) == int(run_plan.fold_index)
            ),
            None,
        )
        policy_payload = _historical_record(
            store, historical.get("cv_policy_identity_digest")
        )
        if fold_payload is None or policy_payload is None:
            return None
        training_uids = [str(v) for v in fold_payload["training_frame_uids"]]
        outer_uids = tuple(str(v) for v in fold_payload["outer_evaluation_frame_uids"])
        if (
            seed not in {int(v) for v in historical.get("required_cv_seeds", ())}
            or int(policy_payload.get("cv_max_num_epochs", -1)) != trajectory.planned_epochs
            or digest({"frame_uids": training_uids}) != trajectory.training_membership_digest
            or transfer_consumer_composition_digest(
                context.selected,
                training_mode=context.method.training_mode,
                consumer_frame_uids=monitor_uids + outer_uids,
            )
            != trajectory.transfer_consumer_composition_digest
        ):
            return None
        historical_run_identity = post_selection_run_identity(
            role=PostSelectionRunRole.POST_SELECTION_CV,
            plan_digest=str(source),
            optimizer_seed=seed,
            fold_index=int(run_plan.fold_index),
        )
        historical_run_plan_digest = digest(
            {
                "schema": "mdstats.post-selection-cv-fold-run-plan.v1",
                "cv_plan_digest": str(source),
                "method_identity_digest": str(historical["method_identity_digest"]),
                "cv_policy_identity_digest": str(historical["cv_policy_identity_digest"]),
                "selected_binding_digest": trajectory.selected_binding_digest,
                "fold_index": int(run_plan.fold_index),
                "optimizer_seed": seed,
                "planned_epochs": trajectory.planned_epochs,
                "run_role": PostSelectionRunRole.POST_SELECTION_CV.value,
                "run_identity": historical_run_identity,
            }
        )
    else:
        if (
            seed not in {int(v) for v in historical.get("required_final_seeds", ())}
            or int(historical.get("planned_epochs", -1)) != trajectory.planned_epochs
            or historical.get("target_membership_digest")
            != trajectory.training_membership_digest
            or transfer_consumer_composition_digest(
                context.selected,
                training_mode=context.method.training_mode,
                consumer_frame_uids=monitor_uids,
            )
            != trajectory.transfer_consumer_composition_digest
        ):
            return None
        historical_run_identity = post_selection_run_identity(
            role=PostSelectionRunRole.FINAL_PRODUCTION,
            plan_digest=str(source),
            optimizer_seed=seed,
        )
        historical_run_plan_digest = digest(
            {
                "schema": "mdstats.post-selection-final-production-run-plan.v1",
                "final_plan_digest": str(source),
                "method_identity_digest": str(historical["method_identity_digest"]),
                "final_production_policy_digest": str(
                    historical["final_production_policy_digest"]
                ),
                "selected_binding_digest": trajectory.selected_binding_digest,
                "optimizer_seed": seed,
                "planned_epochs": trajectory.planned_epochs,
                "run_role": PostSelectionRunRole.FINAL_PRODUCTION.value,
                "run_identity": historical_run_identity,
            }
        )
    root = (
        post_selection_root(context.paths, context.selected.binding.campaign_generation)
        / "runs"
        / historical_run_identity
    )
    if root.is_symlink() or not root.is_dir():
        return None
    from .train2_runtime import TRAIN2_RUNTIME_SUMMARY_FILENAME

    if not (root / "checkpoints" / TRAIN2_RUNTIME_SUMMARY_FILENAME).is_file():
        # Without durable TRAIN2 state there is nothing to reuse; a fresh
        # current trajectory is the admissible path.
        return None
    return LegacyTrainingReuse(
        root=root,
        run_role=str(run_plan.run_role),
        historical_plan_digest=str(source),
        historical_run_plan_digest=historical_run_plan_digest,
        historical_method_identity_digest=str(historical["method_identity_digest"]),
        training_trajectory_identity=trajectory.content_digest,
        proof={
            "method_training_projection_digest": digest(
                context.method.training_projection()
            ),
            "retired_method_fields": list(RETIRED_ASSESSMENT_ONLY_METHOD_FIELDS),
            "selected_binding_digest": trajectory.selected_binding_digest,
            "training_membership_digest": trajectory.training_membership_digest,
            "optimizer_seed": seed,
            "planned_epochs": trajectory.planned_epochs,
            "common_monitor_record_digest": trajectory.common_monitor_record_digest,
            "replay_lineage_digest": trajectory.replay_lineage_digest,
            "transfer_consumer_composition_digest": (
                trajectory.transfer_consumer_composition_digest
            ),
        },
    )


@dataclass(frozen=True, slots=True)
class _HistoricalMaterializationView:
    """Read-only view of one historical v2 materialization record.

    It exposes exactly the training transports and configuration identities
    the existing trainer/provider owners consume.  The historical held-out
    outer-evaluation artifact stays in the historical record untouched and is
    never current measurement ancestry.
    """

    payload: Mapping[str, Any]
    target_train_artifact: Any
    checkpoint_monitor_artifact: Any

    @property
    def content_digest(self) -> str:
        return str(self.payload["content_digest"])

    @property
    def preparation_digest(self) -> str:
        return str(self.payload["preparation_digest"])

    @property
    def mace_config_relative_path(self) -> str:
        return str(self.payload["mace_config_relative_path"])

    @property
    def mace_config_sha256(self) -> str:
        return str(self.payload["mace_config_sha256"])

    @property
    def mace_config_digest(self) -> str:
        return str(self.payload["mace_config_digest"])

    def to_dict(self) -> dict[str, Any]:
        return dict(self.payload)


def authenticated_training_materialization(
    run_root: str | os.PathLike[str], *, expected_digest: str
) -> Any:
    """The training materialization a seed assessment bound, read from its root.

    A current root holds a v3 training-only record; an authenticated historical
    root holds its immutable v2 record, exposed read-only through the same
    training-transport/configuration attributes.  Either must reproduce the
    exact digest the assessment bound.
    """

    from .post_selection_execution import POST_SELECTION_MATERIALIZATION_SCHEMA_V2
    from .target_size_execution import TargetSizeExtxyzArtifact

    raw = _load_owner_record(Path(run_root) / "materialization" / "materialization.json")
    if not isinstance(raw, Mapping):
        raise PostSelectionError("Training root materialization is not readable.")
    if raw.get("schema") == POST_SELECTION_MATERIALIZATION_SCHEMA_V2:
        body = {key: value for key, value in raw.items() if key != "content_digest"}
        if digest(body) != str(raw.get("content_digest", "")):
            raise PostSelectionError("Historical materialization digest mismatch.")
        record: Any = _HistoricalMaterializationView(
            payload=dict(raw),
            target_train_artifact=TargetSizeExtxyzArtifact.from_dict(
                raw["target_train_artifact"]
            ),
            checkpoint_monitor_artifact=TargetSizeExtxyzArtifact.from_dict(
                raw["checkpoint_monitor_artifact"]
            ),
        )
    else:
        record = PostSelectionMaterialization.from_dict(raw)
    if record.content_digest != str(expected_digest):
        raise PostSelectionError(
            "Training root materialization is not the one the assessment bound."
        )
    return record


def _authenticate_legacy_training_state(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    root: _TrainingRoot,
) -> tuple[_HistoricalMaterializationView, Any, Any, Any]:
    """Exact realized-state proof of one historical root under its own identities.

    Returns ``(materialization view, historical runtime plan, replay
    resolution, optimizer policy)``.  The historical fitted preparation is
    re-derived in memory from the root's own persisted residual inputs and must
    reproduce the historical preparation digest; artifacts, the generated MACE
    configuration and the TRAIN2 runtime plan must equal what the current
    training method derives under the historical labels.  Nothing is written.
    """

    import dataclasses

    from .post_selection_execution import (
        POST_SELECTION_MATERIALIZATION_SCHEMA_V2,
        POST_SELECTION_PREPARATION_SCHEMA_V3,
    )
    from .target_size_execution import (
        TargetSizeExtxyzArtifact,
        validate_target_size_extxyz_artifact,
    )

    legacy = root.legacy
    material_directory = root.path / "materialization"
    for node in _observe_run_root_nodes(root.path):
        if node["kind"] not in ("file", "directory"):
            _post_selection_recovery_error(
                f"Historical root contains a non-regular node {node['path']!r}; it is "
                "preserved and not reused."
            )
    raw = _load_owner_record(material_directory / "materialization.json")
    body = (
        {key: value for key, value in raw.items() if key != "content_digest"}
        if isinstance(raw, Mapping)
        else None
    )
    if (
        body is None
        or raw.get("schema") != POST_SELECTION_MATERIALIZATION_SCHEMA_V2
        or digest(body) != str(raw.get("content_digest", ""))
        or raw.get("run_identity") != root.path.name
        or raw.get("run_plan_digest") != legacy.historical_run_plan_digest
    ):
        _post_selection_recovery_error(
            "Historical root materialization does not authenticate as the v2 record "
            "of its own historical run position."
        )
    view = _HistoricalMaterializationView(
        payload=dict(raw),
        target_train_artifact=TargetSizeExtxyzArtifact.from_dict(raw["target_train_artifact"]),
        checkpoint_monitor_artifact=TargetSizeExtxyzArtifact.from_dict(
            raw["checkpoint_monitor_artifact"]
        ),
    )
    optimizer_policy = _optimizer_policy_for(
        context, seed=run_plan.optimizer_seed, planned_epochs=run_plan.planned_epochs
    )
    monitor_record, _separation = context.common_target_monitor()
    monitor_uids = tuple(monitor_record.selected_identities)
    training_uids = tuple(view.target_train_artifact.frame_uids)
    outer = raw.get("outer_evaluation_artifact")
    outer_uids = () if outer is None else tuple(str(v) for v in outer["frame_uids"])
    preparation = _fit_post_selection_run_preparation(
        context,
        run_plan=run_plan,
        material_directory=material_directory,
        optimizer_policy=optimizer_policy,
        training_frame_uids=training_uids,
        monitor_frame_uids=monitor_uids,
        outer_evaluation_frame_uids=outer_uids,
        acquire_residual_inputs=False,
    )
    historical_preparation = dict(preparation._payload())
    historical_preparation.pop("training_trajectory_identity")
    historical_preparation["schema"] = POST_SELECTION_PREPARATION_SCHEMA_V3
    historical_preparation["owner_plan_digest"] = legacy.historical_run_plan_digest
    if digest(historical_preparation) != view.preparation_digest:
        _post_selection_recovery_error(
            "Historical root was fitted to a different realized preparation than the "
            "current training method reproduces; it is not training-equivalent."
        )
    authorities = context.selected.authorities
    for artifact, lineage in (
        (view.target_train_artifact, view.preparation_digest),
        (view.checkpoint_monitor_artifact, None),
    ):
        if artifact.common_preparation_digest != lineage:
            _post_selection_recovery_error(
                "Historical training artifact preparation lineage is inconsistent."
            )
        try:
            validate_target_size_extxyz_artifact(
                artifact,
                root_directory=material_directory,
                canonical_frame_authority=authorities.frame_authority,
                policy=context.method_policies.extxyz,
                frame_catalog=authorities.frame_catalog,
                frame_data_by_run=authorities.frame_data_by_run,
                frame_array_index=authorities.frame_array_index,
            )
        except Exception as exc:
            _post_selection_recovery_error(
                "Historical training artifact failed authentication.", exc
            )
    replay_resolution = _training_replay_resolution(context)
    expected_config = _post_selection_mace_config(
        run_identity=root.path.name,
        optimizer_seed=run_plan.optimizer_seed,
        planned_epochs=run_plan.planned_epochs,
        preparation=preparation,
        objective=context.method_policies.objective,
        optimizer_policy=optimizer_policy,
        target_train=view.target_train_artifact,
        monitor=view.checkpoint_monitor_artifact,
        extxyz_policy=context.method_policies.extxyz,
        method=context.method,
        mace_architecture=context.method_policies.mace_architecture,
        foundation_head=context.method_policies.foundation_head,
        multiheads_finetuning=(
            context.method_policies.training_mode == "multihead_replay"
        ),
        replay_train=None if replay_resolution is None else replay_resolution.train_path,
        replay_monitor=(
            None if replay_resolution is None else replay_resolution.monitor_path
        ),
    )
    expected_config["method_identity_digest"] = legacy.historical_method_identity_digest
    config_bytes = (material_directory / view.mace_config_relative_path).read_bytes()
    if (
        hashlib.sha256(config_bytes).hexdigest() != view.mace_config_sha256
        or json.loads(config_bytes.decode("utf-8")) != expected_config
        or digest(expected_config) != view.mace_config_digest
    ):
        _post_selection_recovery_error(
            "Historical generated MACE configuration is not the one the current "
            "training method derives under the historical labels."
        )
    current_runtime_plan = _post_selection_runtime_plan_for(
        context,
        run_plan=run_plan,
        budget_policy=budget_policy,
        optimizer_policy=optimizer_policy,
        structures_per_epoch=len(training_uids),
        replay_resolution=replay_resolution,
    )
    historical_runtime_plan = dataclasses.replace(
        current_runtime_plan,
        training_protocol_digest=legacy.historical_method_identity_digest,
    )
    return view, historical_runtime_plan, replay_resolution, optimizer_policy


def _authenticate_legacy_sealed_training_root(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    root: _TrainingRoot,
    completion: Any,
) -> _SealedTrainingState:
    """Authenticate a sealed historical root for read-only EVAL2 reuse."""

    from .train2_runtime import load_train2_runtime_summary

    closed, why = certify_closed_post_selection_run_root(root.path)
    if not closed:
        _post_selection_recovery_error(
            f"Historical sealed root does not certify as a closed subtree: {why}"
        )
    view, runtime_plan, replay_resolution, _optimizer = _authenticate_legacy_training_state(
        context, run_plan=run_plan, budget_policy=budget_policy, root=root
    )
    checkpoint_directory = root.path / "checkpoints"
    summary = load_train2_runtime_summary(checkpoint_directory)
    proof = completion.terminal_proof
    if (
        summary.plan_digest != runtime_plan.content_digest
        or int(summary.completed_epochs) != int(runtime_plan.budget_policy.planned_epochs)
        or (
            proof is not None
            and (
                proof["runtime_summary_digest"] != summary.content_digest
                or proof["materialization_digest"] != view.content_digest
                or proof["runtime_plan_digest"] != runtime_plan.content_digest
            )
        )
    ):
        _post_selection_recovery_error(
            "Historical sealed root is not the terminal TRAIN2 state of its own "
            "historical runtime identity."
        )
    context.evidence_store.put(root.legacy)
    return _SealedTrainingState(
        material_directory=root.path / "materialization",
        checkpoint_directory=checkpoint_directory,
        materialization=view,
        summary=summary,
        runtime_plan=runtime_plan,
        replay_resolution=replay_resolution,
    )


def _complete_legacy_training_root(
    context: PostSelectionContext,
    *,
    run_plan: Any,
    budget_policy: Any,
    root: _TrainingRoot,
    progress_context: Mapping[str, Any] | None,
    cancellation_event: Any | None,
    progress_callback: Callable[[str], None] | None,
    progress_observer: Callable[[Mapping[str, Any]], None] | None,
    telemetry_ref: Any | None,
    launch_trainer: bool = True,
) -> bool:
    """Continue (if interrupted) and append-only seal one unsealed historical root.

    An interrupted historical trajectory continues only under its own
    historical materialization/config/runtime identities, after the exact
    training-equivalence proof.  Once terminal, the root receives exactly one
    append-only topology manifest + completion anchor under this run-activity
    lease; no pre-existing byte is rewritten, and pre-cutover terminal
    assessment files or an inconsistent partial proof fail closed.

    ``launch_trainer=False`` is recovery normalization: a terminal root is
    sealed exactly as above, while an interrupted one is only authenticated
    and reported by the ``False`` return.
    """

    if any(
        observed_node_kind_is_present(root.path / name)
        for name in RUN_TERMINAL_RECORD_NAMES
    ):
        _post_selection_recovery_error(
            "Historical root carries a terminal assessment record but no valid "
            "completion anchor; this partial proof state is preserved and not reused."
        )
    view, runtime_plan, replay_resolution, optimizer_policy = (
        _authenticate_legacy_training_state(
            context, run_plan=run_plan, budget_policy=budget_policy, root=root
        )
    )
    checkpoint_directory = root.path / "checkpoints"
    summary, start_epoch = _authenticate_post_selection_continuation(
        checkpoint_directory, runtime_plan=runtime_plan
    )
    if summary is None:
        _post_selection_recovery_error(
            "Historical root has no authenticated TRAIN2 continuation to reuse."
        )
    config_payload = json.loads(
        (root.path / "materialization" / view.mace_config_relative_path).read_text(
            encoding="utf-8"
        )
    )
    _validate_post_selection_continuation_execution_evidence(
        context,
        materialization=view,
        config_payload=config_payload,
        continuation_summary=summary,
        replay_resolution=replay_resolution,
        optimizer_policy=optimizer_policy,
    )
    if summary.completed_epochs != runtime_plan.execution_epoch_limit:
        if not launch_trainer:
            return False
        _abort_post_selection_run_if_cancelled(cancellation_event, phase="pre-training")
        summary = context.trainer(
            PostSelectionRungRequest(
                plan=runtime_plan,
                run_plan=run_plan,
                materialization=view,
                materialization_directory=root.path / "materialization",
                checkpoint_directory=checkpoint_directory,
                optimizer_policy=optimizer_policy,
                start_epoch=start_epoch,
                foundation_identity=context.method_policies.foundation_potential_identity,
                foundation_model_path=context.train2_foundation_path,
                training_realization=context.train2_foundation_realization,
                replay_train_artifact=(
                    None if replay_resolution is None else replay_resolution.train_artifact
                ),
                replay_train_path=(
                    None if replay_resolution is None else Path(replay_resolution.train_path)
                ),
                replay_monitor_artifact=(
                    None
                    if replay_resolution is None
                    else replay_resolution.monitor_artifact
                ),
                replay_monitor_path=(
                    None
                    if replay_resolution is None
                    else Path(replay_resolution.monitor_path)
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
            )
        )
        if summary is None or summary.plan_digest != runtime_plan.content_digest:
            raise PostSelectionExecutionError(
                "Historical continuation did not return its own authenticated summary."
            )
    if int(summary.completed_epochs) != int(runtime_plan.budget_policy.planned_epochs):
        raise PostSelectionExecutionError(
            "Historical TRAIN2 did not reach its terminal epoch; not sealable."
        )
    context.evidence_store.put(root.legacy)
    record_post_selection_training_completion(
        root.path,
        runtime_summary=summary,
        runtime_plan_digest=runtime_plan.content_digest,
        materialization_digest=view.content_digest,
    )
    return True


def authenticated_run_representative_records(
    context: PostSelectionContext, run_plan: Any, evidence: PostSelectionRunEvidence
) -> tuple[Any, Any]:
    """Return one completed run's exact representative and monitor EVAL2 records.

    Current runs publish both records durably before their run evidence, so the
    only path is an authenticated content-addressed read.  A record that is
    absent means the run is not current evidence; nothing is re-evaluated or
    synthesized from a digest.
    """

    from .eval2 import Eval2CheckpointRecord, Eval2TargetMetricRecord

    store = context.evidence_store
    authenticated_post_selection_candidate_records(
        context,
        candidate_record_digests=evidence.candidate_record_digests,
        runtime_summary_digest=evidence.runtime_summary_digest,
        representative_record_digest=(
            evidence.representative_record_digest if evidence.selected else None
        ),
    )
    if not evidence.selected:
        raise PostSelectionError(
            f"Final-seed assessment of run {run_plan.run_identity[:12]}... has no "
            "admissible representative; nothing can be published from it."
        )
    if not (
        store.has(evidence.representative_record_digest)
        and store.has(evidence.monitor_metric_record_digest)
    ):
        raise PostSelectionError(
            f"Completed run {run_plan.run_identity[:12]}... lacks its durable "
            "representative or common-monitor metric record; it is not current "
            "evidence and must be rerun."
        )
    return (
        store.get(evidence.representative_record_digest, Eval2CheckpointRecord.from_dict),
        store.get(evidence.monitor_metric_record_digest, Eval2TargetMetricRecord.from_dict),
    )


def _checkpoint_catalog(run_identity: str, checkpoint_directory: Path) -> Any:
    from .post_selection_execution import post_selection_checkpoint_catalog

    return post_selection_checkpoint_catalog(
        run_identity=run_identity, checkpoint_directory=checkpoint_directory
    )


#: Pre-cutover root-local terminal assessment files.  Current P5 never writes
#: them: fold/seed assessments are immutable evidence-store objects behind the
#: position locator.  The names stay known so historical sealed roots remain
#: certifiable and read-only compatible.
FOLD_ACCEPTANCE_FILENAME = "fold-acceptance.json"
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
#: v2 is the training-only terminal proof: authenticated terminal TRAIN2 (the
#: exact runtime summary, runtime plan and materialization) seals the root
#: before any assessment.  v1 anchors named terminal assessment files and
#: remain valid, read-only historical proofs.
RUN_COMPLETION_ANCHOR_SCHEMA = "mdstats.post-selection-run-completion.v2"
RUN_COMPLETION_ANCHOR_SCHEMA_V1 = "mdstats.post-selection-run-completion.v1"
TRAIN2_TERMINAL_PROOF_KIND = "train2_terminal"

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

    from .persistence import artifact_publication_lock

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
    """The compact, O(1) proof that one post-selection run's root is closed.

    ``terminal_proof`` is the v2 TRAIN2 terminal proof of a training-only root;
    it is ``None`` for a historical v1 anchor, whose ``terminal_records`` name
    the pre-cutover assessment files it was sealed after.
    """

    run_root: str
    terminal_records: tuple[str, ...]
    topology_digest: str
    node_count: int
    file_count: int
    directory_count: int
    content_digest: str
    terminal_proof: Mapping[str, Any] | None = None


def _validated_terminal_proof(payload: Mapping[str, Any]) -> dict[str, Any] | None:
    proof = payload.get("terminal_proof")
    if not isinstance(proof, Mapping) or proof.get("kind") != TRAIN2_TERMINAL_PROOF_KIND:
        return None
    result: dict[str, Any] = {"kind": TRAIN2_TERMINAL_PROOF_KIND}
    for name in ("runtime_summary_digest", "runtime_plan_digest", "materialization_digest"):
        value = str(proof.get(name, ""))
        if len(value) != 64:
            return None
        result[name] = value
    try:
        completed = int(proof["completed_epochs"])
        planned = int(proof["planned_epochs"])
    except (KeyError, TypeError, ValueError):
        return None
    if completed <= 0 or completed != planned:
        return None
    result["completed_epochs"] = completed
    result["planned_epochs"] = planned
    return result


def read_post_selection_run_completion(
    run_root: str | os.PathLike[str],
) -> tuple[PostSelectionRunCompletion | None, str]:
    """Validate the compact completion anchor of one run root.

    This is the **one** validating reader every consumer goes through, and it is
    deliberately bounded: it reads a single small record (opened no-follow and
    authenticated as a regular file on the opened descriptor), re-derives that
    record's own digest, checks the run identity it claims, and confirms the
    bound topology manifest is present.  It never reads or hashes the manifest
    and never walks the run, so normal reporting stays independent of how much
    the run holds.  Completion never depends on terminal assessment files still
    being hot: a v2 anchor proves terminal TRAIN2 itself.

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
    raw = _load_owner_record(path)
    schema = raw.get("schema") if isinstance(raw, Mapping) else None
    payload = (
        _self_authenticated(raw, str(schema))
        if schema in (RUN_COMPLETION_ANCHOR_SCHEMA, RUN_COMPLETION_ANCHOR_SCHEMA_V1)
        else None
    )
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
    proof = None
    if schema == RUN_COMPLETION_ANCHOR_SCHEMA:
        proof = _validated_terminal_proof(payload)
        if proof is None:
            return None, (
                "run completion anchor carries no valid terminal TRAIN2 proof, so it "
                "does not certify a finished training root"
            )
        terminal: tuple[str, ...] = (TRAIN2_TERMINAL_PROOF_KIND,)
    else:
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
            terminal_proof=proof,
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


def record_post_selection_training_completion(
    run_root: str | os.PathLike[str],
    *,
    runtime_summary: Any,
    runtime_plan_digest: str,
    materialization_digest: str,
) -> Path:
    """Seal one training-only root at authenticated terminal TRAIN2, once.

    The caller holds the run-activity lease, so no trainer or storage writer
    can race the seal.  Publication order is the contract: the full topology
    manifest first, then the compact anchor - which binds that manifest's
    identity and the TRAIN2 terminal proof - last, as the commit point.  A crash
    between them leaves a manifest nothing points at, which grants nothing.

    It is create-once and never requires a terminal assessment file.  A second
    call verifies the existing proof and stops; it deliberately does **not**
    rescan the tree, because storage may legitimately have moved represented
    members cold since, and a freshly derived set would falsely conflict.  A
    present-but-invalid anchor, a manifest/anchor disagreement, or a
    pre-existing proof that names different terminal state fails closed.  The
    same owner provides the one append-only seal of a terminal-but-unsealed
    legacy root: it records the existing nodes and rewrites none of them.
    """

    from .target_size_execution import publish_immutable_json_create_or_verify

    root = Path(run_root)
    anchor_path = root / RUN_COMPLETION_ANCHOR_FILENAME
    proof = {
        "kind": TRAIN2_TERMINAL_PROOF_KIND,
        "runtime_summary_digest": validate_digest(
            str(runtime_summary.content_digest), name="runtime_summary_digest"
        ),
        "runtime_plan_digest": validate_digest(
            str(runtime_plan_digest), name="runtime_plan_digest"
        ),
        "materialization_digest": validate_digest(
            str(materialization_digest), name="materialization_digest"
        ),
        "completed_epochs": int(runtime_summary.completed_epochs),
        "planned_epochs": int(runtime_summary.planned_epochs),
    }
    if proof["completed_epochs"] != proof["planned_epochs"]:
        raise PostSelectionExecutionError(
            f"Post-selection run {root.name} is not at terminal fixed-budget TRAIN2; "
            "only a terminal training root can be sealed."
        )
    existing, why = read_post_selection_run_completion(root)
    if existing is not None:
        nodes, detail = read_post_selection_run_topology(root, existing)
        if nodes is None:
            raise PostSelectionExecutionError(
                f"Post-selection run {root.name} carries a completion anchor whose "
                f"topology manifest does not authenticate: {detail}"
            )
        if existing.terminal_proof is not None and dict(existing.terminal_proof) != proof:
            raise PostSelectionExecutionError(
                f"Post-selection run {root.name} is already sealed with a different "
                "terminal TRAIN2 proof; completion authority is create-once."
            )
        return anchor_path
    if observed_node_kind_is_present(anchor_path):
        raise PostSelectionExecutionError(
            f"Refusing to republish the completion proof of post-selection run "
            f"{root.name}: an anchor is already present but does not validate "
            f"({why}). Completion authority is create-once, so a disagreement is an "
            "integrity conflict rather than an update."
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
                    "terminal_proof": proof,
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


def observed_node_kind_is_present(path: Path) -> bool:
    from .storage.owners import NODE_ABSENT, observed_node_kind

    return observed_node_kind(path) != NODE_ABSENT


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


# ---------------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _PendingPostSelectionRun:
    """One exact pending CV/final position, carrying its own scientific owner.

    ``context`` and ``budget_policy`` are the owning selected size's; ``slot``
    is the local position inside that size's plan and routes results back to
    it.  ``key`` is execution-only scheduler bookkeeping that is unique within
    one TRAIN wave; it never enters a run plan, position, digest, or record.
    """

    context: PostSelectionContext
    budget_policy: Any
    slot: int
    key: int
    run_plan: Any
    training_frame_uids: tuple[str, ...]
    monitor_frame_uids: tuple[str, ...]
    outer_evaluation_frame_uids: tuple[str, ...] | None
    progress_context: Mapping[str, Any]
    reusable: _ReusableMeasurements | None = None


def _execute_pending_post_selection_run(
    task: _PendingPostSelectionRun, **kwargs: Any
) -> PostSelectionRunResult | None:
    """Run one pending position through the run owner under its own owner."""

    return execute_post_selection_run(
        task.context,
        run_plan=task.run_plan,
        budget_policy=task.budget_policy,
        training_frame_uids=task.training_frame_uids,
        monitor_frame_uids=task.monitor_frame_uids,
        outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
        progress_context=task.progress_context,
        **kwargs,
    )


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
                8192.0,
            )
        ),
        estimated_ram_mib_per_job=float(
            _cfg(
                context.cfg,
                "execution",
                "estimated_training_ram_mib_per_job",
                16384.0,
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
    pending: Sequence[_PendingPostSelectionRun],
) -> None:
    """Reject durable foreign continuations before any sibling reaches EVAL2."""

    for task in sorted(pending, key=lambda item: int(item.key)):
        context = task.context
        root = resolve_post_selection_training_root(context, task.run_plan)
        if root.legacy is not None:
            continue
        run_root = root.path
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
            if read_post_selection_run_completion(run_root)[0] is not None:
                continue
            _prepare_post_selection_run(
                context,
                run_plan=task.run_plan,
                budget_policy=task.budget_policy,
                training_frame_uids=task.training_frame_uids,
                monitor_frame_uids=task.monitor_frame_uids,
                outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
                run_root=run_root,
            )


def _post_selection_scheduler_profile(
    task: _PendingPostSelectionRun,
) -> tuple[tuple[str, Any], ...]:
    """Every per-job fact the single TRAIN controller assumes is shared.

    Values are derived through the same owners the scheduler and the TRAIN2
    run consume.  The optimizer seed and planned horizon are scientific
    identities and are deliberately absent; the size-independent per-job
    RAM/VRAM estimates are part of the concurrency policy itself.
    """

    from ._campaign_cli_core import _cfg

    context = task.context
    cfg = context.cfg
    optimizer = _optimizer_policy_for(
        context,
        seed=task.run_plan.optimizer_seed,
        planned_epochs=task.run_plan.planned_epochs,
    )
    acceleration = getattr(optimizer, "acceleration_policy", None)
    return (
        ("device", str(context.method_policies.device)),
        ("optimizer device", str(optimizer.device)),
        ("learned-model precision", str(optimizer.default_dtype)),
        ("training method/model realization", context.method.content_digest),
        ("batch size", (int(optimizer.batch_size), int(optimizer.valid_batch_size))),
        ("loader workers per job", int(getattr(optimizer, "num_workers", 0))),
        (
            "training acceleration",
            (
                None if acceleration is None else acceleration.backend.value,
                getattr(optimizer, "acceleration_realization_digest", None),
                getattr(optimizer, "resolved_acceleration_kernel_mode", None),
            ),
        ),
        ("replay lineage", task.run_plan.training_trajectory.replay_lineage_digest),
        (
            "concurrency policy and per-job RAM/VRAM estimates",
            _post_selection_training_concurrency_policy(context),
        ),
        (
            "CPU/RAM/GPU allocation",
            tuple(
                float(_cfg(cfg, "performance", name, default))
                for name, default in (
                    ("cpu_fraction", 0.9),
                    ("ram_fraction", 0.8),
                    ("gpu_memory_fraction", 0.9),
                )
            ),
        ),
        (
            "progress interval",
            float(_cfg(cfg, "execution", "training_progress_interval_seconds", 10.0)),
        ),
        ("trainer/process-supervision owner", id(context.trainer)),
    )


def _require_one_post_selection_scheduler_profile(
    pending: Sequence[_PendingPostSelectionRun],
) -> _PendingPostSelectionRun:
    """Prove every TRAIN task shares one resource domain; return its exemplar.

    The existing controller plans one loader geometry and one per-job estimate
    for the whole wave and learns promotion demand from active jobs, so tasks
    may share it only when those facts are identical.  A difference fails
    closed before any trainer starts: choosing one task's values, or a min/max
    over them, would be a different resource model than the controller's.
    """

    reference = pending[0]
    expected = _post_selection_scheduler_profile(reference)
    for task in pending[1:]:
        observed = _post_selection_scheduler_profile(task)
        for (dimension, left), (_same, right) in zip(expected, observed):
            if left != right:
                raise PostSelectionError(
                    "Production TRAIN2 positions cannot share one TRAIN scheduler: "
                    f"their {dimension} differs (N={reference.context.selected.n_selected} "
                    f"seed={reference.run_plan.optimizer_seed}: {left!r}; "
                    f"N={task.context.selected.n_selected} "
                    f"seed={task.run_plan.optimizer_seed}: {right!r}). "
                    "No trainer was launched."
                )
    return reference


def _train_post_selection_pending_runs(
    pending: Sequence[_PendingPostSelectionRun],
    *,
    admission_fence: Callable[[], ContextManager[Any]] | None = None,
) -> tuple[int, ...]:
    """TRAIN exact pending positions through the one adaptive controller.

    ``pending`` holds only positions that still require trainer execution;
    recovery classification is the caller's and precedes this call, so the
    first telemetry observation here is the authoritative admission baseline.
    Each position runs under its own context and budget policy and ends at
    its sealed terminal TRAIN2 boundary: nothing here evaluates, assesses, or
    publishes, so EVAL2 can never hold accelerator memory while a TRAIN2 child
    admitted by this wave is still active.  The returned keys name the
    positions this wave trained; callers route and reduce by their own frozen
    order, never by completion order.

    ``admission_fence`` wraps every ownership transition (dequeue, submit,
    active registration), including a readmission after demotion.  An
    exception from it is a terminal wave failure.
    """

    ordered_pending = tuple(sorted(pending, key=lambda item: int(item.key)))
    if not ordered_pending:
        return ()
    if len({int(task.key) for task in ordered_pending}) != len(ordered_pending):
        raise PostSelectionExecutionError(
            "TRAIN scheduler keys must be unique within one wave."
        )

    from collections import deque
    from concurrent.futures import ALL_COMPLETED, FIRST_COMPLETED, ThreadPoolExecutor, wait
    from contextlib import nullcontext
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

    exemplar = _require_one_post_selection_scheduler_profile(ordered_pending)
    context = exemplar.context
    device = str(context.method_policies.device)
    first_policy = _optimizer_policy_for(
        context,
        seed=exemplar.run_plan.optimizer_seed,
        planned_epochs=exemplar.run_plan.planned_epochs,
    )
    resources = _performance_resources(context.cfg)
    concurrency_policy = _post_selection_training_concurrency_policy(context)
    # The caller's recovery classification has already finished, so this is
    # both the post-recovery observation and the authoritative TRAIN admission
    # baseline; they are the same instant by construction.
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
    telemetry_ref: dict[str, Any] = {"sample": initial_sample}
    # One cooperative stop signal per admitted key. Backoff sets exactly one of
    # them; a terminal abort sets every one of them, which *is* the whole-wave
    # cancellation. A single shared event could not express "stop exactly one
    # owned job", and a second parallel mechanism for the wave would only
    # duplicate this one.
    stop_events: dict[int, threading.Event] = {}
    state_lock = threading.Lock()
    states: dict[int, dict[str, Any]] = {
        task.key: {
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
    trained_keys: list[int] = []
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
                bool(states[task.key].get("true_epoch"))
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
                # Counted from actual scheduler ownership: a submitted key that
                # already failed is never reported as still queued, and a
                # demoted key is queued again rather than counted as failed.
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
            # The whole ownership transition happens inside the fence, so a
            # concurrent currentness change either precedes it (and nothing is
            # dequeued) or follows an admission that has fully completed.
            with admission_fence() if admission_fence is not None else nullcontext():
                task = pending_queue.popleft()
                with state_lock:
                    # A restarted key re-earns its own liveness observations;
                    # the dead attempt's must not be read as current activity.
                    states[task.key].update({"true_epoch": False, "phase": "launching"})
                stop_event = threading.Event()
                stop_events[task.key] = stop_event

                def observe(
                    observation: Mapping[str, Any],
                    *,
                    key: int = task.key,
                ) -> None:
                    with state_lock:
                        states[key].update(dict(observation))

                future = executor.submit(
                    _execute_pending_post_selection_run,
                    task,
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
        with its frozen scientific owner and wave key and resumes later through
        the existing checkpoint/continuation authority - so it never increments
        the failed count and never publishes partial evidence.

        What makes an outcome a demotion is the execution owner's explicit
        cancellation result, never this scheduler's intent: a victim that
        instead failed on its own authority stays a failure.

        The scheduler blocks here until the owned worker has actually returned.
        A future cancellation request is not CUDA teardown: only the worker's
        own completion establishes that the child process exited and its
        finalization ran, so no replacement admission or restart can be ordered
        before that boundary.

        The wait is unbounded on purpose. This future is the whole run, which
        may still be in run-owned preparation or materialization and may not
        have entered the trainer at all, so no subprocess-termination clock
        describes it. Bounding child termination belongs to the process owner,
        which already escalates SIGINT/SIGTERM/SIGKILL and reaps
        unconditionally; whatever verdict that produces arrives here as the
        future's own outcome.
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
            f"slot={victim.key}"
        )
        print(
            f"[TRAIN scheduler] backoff {before}->{before - 1}; slot={victim.key}; "
            f"pre-demotion VRAM={used_text}; "
            f"effective_ceiling={controller.effective_ceiling}",
            flush=True,
        )
        stop_events[victim.key].set()
        wait((victim_future,), return_when=ALL_COMPLETED)
        active.pop(victim_future, None)
        stop_events.pop(victim.key, None)
        with state_lock:
            states[victim.key].update({"true_epoch": False, "phase": "demoted"})
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
            # observed the stop. That key is genuinely done; requeueing it
            # would duplicate completed work.
            trained_keys.append(victim.key)
            completed_count += 1
            outcome = "completed before stopping"
        else:
            pending_queue.appendleft(victim)
            outcome = "returned to the pending/restartable queue"
        post_sample = query_gpu_telemetry(device)
        telemetry_ref["sample"] = post_sample
        _report_post_selection_gpu_occupancy(
            f"post-demotion slot={victim.key} teardown", device, post_sample
        )
        print(
            f"[TRAIN scheduler] slot={victim.key} worker teardown observed; "
            f"{outcome}",
            flush=True,
        )

    executor = ThreadPoolExecutor(
        max_workers=max(1, int(concurrency_plan.maximum_jobs)),
        thread_name_prefix="mdstats-p5-train",
    )
    report("planned", force=True)
    try:
        submit_available(executor)
        report("running", force=True)
        # Whether the idle zero-admission state has already survived one
        # poll-cadence wait and the fresh control observation that follows it.
        idle_zero_admission_rechecked = False
        while active or pending_queue:
            idle_zero_admission = (
                not active
                and pending_queue
                and int(controller.target_jobs) < 1
            )
            if idle_zero_admission and idle_zero_admission_rechecked:
                # Pending work with an idle queue and no feasible key, still
                # true after one normal poll interval and the fresh control
                # observation taken across it, is a terminal resource state;
                # busy-waiting would hide it.
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
                if pending_queue and (idle_zero_admission or admission_blocked):
                    # Nothing owned is running, so only a fresh control
                    # observation can change the decision. Wait exactly one
                    # normal poll interval instead of rechecking in a tight
                    # loop, and make the observation below a genuinely new one
                    # rather than whatever the completing job's own latency
                    # happened to let through the elapsed-time gate.
                    time.sleep(poll_interval)
                    last_sample_at = float("-inf")
            # A recheck is owed exactly once per entry into idle zero
            # admission; recovery to an admissible target clears it.
            idle_zero_admission_rechecked = idle_zero_admission
            first_failure: BaseException | None = None
            for future in done:
                task = active.pop(future)
                stop_events.pop(task.key, None)
                try:
                    future.result()
                    trained_keys.append(task.key)
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
                        bool(states[task.key].get("true_epoch"))
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
    return tuple(trained_keys)


def _offered_measurements(
    store: Any,
    *,
    candidate_record_digests: Sequence[str],
    representative_record_digest: str | None = None,
    outer_metric_record_digest: str | None = None,
    into: dict[str, dict[str, Any]],
) -> None:
    """Collect published candidate/outer records as exact-reuse *offers*."""

    from .eval2 import Eval2CheckpointRecord

    for value in candidate_record_digests:
        if not store.has(value):
            continue
        record = store.get(value, Eval2CheckpointRecord.from_dict)
        into["candidates"].setdefault(record.trajectory_point.checkpoint_sha256, record)
    if representative_record_digest and outer_metric_record_digest:
        outer = _stored_metric(store, outer_metric_record_digest)
        if outer is not None and store.has(representative_record_digest):
            representative = store.get(
                representative_record_digest, Eval2CheckpointRecord.from_dict
            )
            into["outer"].setdefault(
                representative.trajectory_point.checkpoint_sha256, outer
            )


def _reusable(offers: dict[str, dict[str, Any]]) -> _ReusableMeasurements:
    return _ReusableMeasurements(
        candidates=dict(offers["candidates"]), outer_by_checkpoint=dict(offers["outer"])
    )


def _run_post_selection_positions(
    pending: Sequence[_PendingPostSelectionRun],
) -> dict[int, PostSelectionRunResult]:
    """One selected size's CV wave: TRAIN unsealed positions, then serial EVAL2.

    A position whose training root is already sealed (a completed trajectory,
    a policy-only reassessment, or an authenticated historical root) never
    enters the TRAIN scheduler and never launches a trainer.  Every TRAIN2
    child has exited and released the device before post-TRAIN EVAL2 begins,
    and a failed TRAIN wave raises before any evaluation.  Results are keyed
    by local slot.
    """

    from .progress_timing import format_progress_fraction
    from .training_parallel import query_gpu_telemetry

    sealed: list[_PendingPostSelectionRun] = []
    training: list[_PendingPostSelectionRun] = []
    for task in pending:
        root = resolve_post_selection_training_root(task.context, task.run_plan)
        completion, _why = read_post_selection_run_completion(root.path)
        (sealed if completion is not None else training).append(task)
    results: dict[int, PostSelectionRunResult] = {}
    if training:
        device = str(training[0].context.method_policies.device)
        # Bind the admission baseline to the recovery preflight that precedes
        # it. Recovery classification can realize a CUDA training model, so the
        # two observations make any parent-side contribution to the baseline
        # visible instead of silently inflating the TRAIN2 envelope.
        _report_post_selection_gpu_occupancy(
            "pre-recovery-preflight", device, query_gpu_telemetry(device)
        )
        _preflight_post_selection_pending_runs(training)
        trained = _train_post_selection_pending_runs(training)
        by_key = {int(task.key): task for task in training}
        ordered_keys = sorted(trained)
        if ordered_keys:
            _report_post_selection_gpu_occupancy(
                "post-TRAIN EVAL2 entry", device, query_gpu_telemetry(device)
            )
        for index, key in enumerate(ordered_keys):
            task = by_key[key]
            print(
                f"[EVAL2 serial] status=running; "
                f"progress={format_progress_fraction(index, len(ordered_keys))}; "
                f"unit=training-run; slot={task.slot}",
                flush=True,
            )
            result = _execute_pending_post_selection_run(task, reusable=task.reusable)
            if result is None:
                raise PostSelectionExecutionError(
                    "Post-TRAIN EVAL2 returned no bound evidence for slot "
                    f"{task.slot}; the authenticated TRAIN2 continuation is unusable."
                )
            results[task.slot] = result
        if ordered_keys:
            print(
                f"[EVAL2 serial] status=completed; "
                f"progress={format_progress_fraction(len(ordered_keys), len(ordered_keys))}; "
                "unit=training-run",
                flush=True,
            )
    for task in sorted(sealed, key=lambda item: int(item.slot)):
        print(
            "[TRAIN] status=reused; sealed training root; "
            + "; ".join(f"{key}={value}" for key, value in task.progress_context.items()),
            flush=True,
        )
        result = _execute_pending_post_selection_run(task, reusable=task.reusable)
        if result is None:
            raise PostSelectionExecutionError(
                f"Sealed position slot {task.slot} produced no evaluated result."
            )
        results[task.slot] = result
    return results


def _cv_position(context: PostSelectionContext, run_plan: Any, policy_digest: str) -> str:
    return assessment_position_digest(
        assessment_role=ASSESSMENT_ROLE_CV_FOLD,
        assessment_position_policy_digest=policy_digest,
        training_trajectory_identity=run_plan.training_trajectory_identity,
        optimizer_seed=run_plan.optimizer_seed,
        fold_index=run_plan.fold_index,
    )


def _final_position(context: PostSelectionContext, run_plan: Any, policy_digest: str) -> str:
    return assessment_position_digest(
        assessment_role=ASSESSMENT_ROLE_FINAL_SEED,
        assessment_position_policy_digest=policy_digest,
        training_trajectory_identity=run_plan.training_trajectory_identity,
        optimizer_seed=run_plan.optimizer_seed,
        fold_index=None,
    )


def _previous_cv_assessments(context: PostSelectionContext) -> tuple[CvFoldAcceptance, ...]:
    """Fold assessments of the previously current CV verdict, as reuse offers only."""

    try:
        campaign = resolve_current_cv_acceptance(context)
    except Exception:
        return ()
    if campaign is None:
        return ()
    return tuple(
        fold
        for seed in campaign.seed_acceptances
        for fold in seed.fold_acceptances
        if fold.is_current
    )


def execute_post_selection_cross_validation(
    context: PostSelectionContext,
) -> tuple[PostSelectionCvPlan, CvCampaignAcceptance]:
    """Build, execute, and accept the complete selected-only cross-validation.

    Training positions are pre-fit trajectories, so a policy-only edit reuses
    every sealed root with zero trainer launch.  Each fold is then assessed
    under the current hard policy + D2.DEF.059A + outer verdict policy; its
    immutable assessment is published in the evidence store behind the
    position locator, never into the training root.  Published measurements
    are reused only under exact measurement-identity equality.
    """

    selected = context.selected
    projection = build_selected_relation_projection(selected)
    common_monitor, monitor_separation = context.common_target_monitor()
    replay_enabled = context.method_policies.replay_enabled
    replay_resolution = None
    if replay_enabled:
        replay_resolution = _resolve_post_selection_replay_resolution(
            context, require_train=True
        )
    replay_lineage_digest = (
        compute_replay_lineage_digest(replay_resolution)
        if replay_enabled
        else None
    )
    previous = _previous_cv_assessments(context)
    plan = build_post_selection_cv_plan(
        selected,
        context.method,
        context.cv_policy,
        common_monitor=common_monitor,
        monitor_separation=monitor_separation,
        projection=projection,
        replay_lineage_digest=replay_lineage_digest,
        legacy_source_plan_digest=post_selection_legacy_source_plan_digest(
            context, kind=POINTER_CV_PLAN
        ),
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
        store.put(common_monitor)
        store.put(monitor_separation)
        store.put(plan)
        publish_current_post_selection_pointer(
            context.store,
            binding=selected.binding,
            kind=POINTER_CV_PLAN,
            content_digest=plan.content_digest,
        )

    budget_policy = cv_training_budget_policy(context.method, context.cv_policy)
    policy_digest = cv_assessment_position_policy_digest(
        post_selection_checkpoint_admissibility(context.method_policies, context.cv_policy),
        context.cv_policy,
    )
    pending: list[_PendingPostSelectionRun] = []
    positions: dict[int, tuple[Any, str]] = {}
    expected_positions: dict[tuple[int, int], tuple[str, str]] = {}
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
        store.put(run_plan.training_trajectory)
        position = _cv_position(context, run_plan, policy_digest)
        positions[slot] = (run_plan, position)
        expected_positions[(seed, fold_index)] = (
            run_plan.training_trajectory_identity,
            policy_digest,
        )
        offers: dict[str, dict[str, Any]] = {"candidates": {}, "outer": {}}
        sources = list(previous)
        current = resolve_current_post_selection_record(
            context.store,
            context.paths,
            selected,
            kind=POINTER_ASSESSMENT_POSITION,
            deserializer=CvFoldAcceptance.from_dict,
            position=position,
        )
        if current is not None:
            sources.insert(0, current)
        for item in sources:
            if (
                item.training_trajectory_identity == run_plan.training_trajectory_identity
                and item.cv_seed == seed
                and item.fold_index == fold_index
            ):
                _offered_measurements(
                    store,
                    candidate_record_digests=item.candidate_record_digests,
                    representative_record_digest=item.representative_checkpoint_record_digest,
                    outer_metric_record_digest=item.outer_metric_record_digest,
                    into=offers,
                )
        pending.append(
            _PendingPostSelectionRun(
                context=context,
                budget_policy=budget_policy,
                slot=slot,
                key=slot,
                run_plan=run_plan,
                training_frame_uids=tuple(fold.training_frame_uids),
                monitor_frame_uids=tuple(common_monitor.selected_identities),
                outer_evaluation_frame_uids=tuple(fold.outer_evaluation_frame_uids),
                progress_context={
                    "N_selected": selected.n_selected,
                    "run": f"{slot + 1}/{total_runs}",
                    "seed": seed,
                    "fold": f"{fold_index + 1}/{plan.fold_count}",
                    "restored": "executing",
                    "phase": "executing",
                },
                reusable=_reusable(offers),
            )
        )

    results = _run_post_selection_positions(pending)
    acceptances: list[CvFoldAcceptance] = []
    for slot in range(total_runs):
        run_plan, position = positions[slot]
        result = results[slot]
        publish_post_selection_run_measurements(context, result)
        acceptance = build_cv_fold_acceptance(
            run_plan=run_plan,
            candidates=result.candidates,
            representative=result.representative,
            outer_metrics=result.outer_metrics,
            policy=context.cv_policy,
            assessment_position_policy_digest=policy_digest,
            training_root_identity=result.training_root_identity,
            runtime_summary_digest=result.runtime_summary_digest,
        )
        if acceptance.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE:
            print(
                "[EVAL2] status=rejected; "
                f"N_selected={selected.n_selected}; "
                f"seed={run_plan.optimizer_seed}; "
                f"fold={run_plan.fold_index + 1}/{plan.fold_count}; "
                f"candidates={len(acceptance.candidate_record_digests)}; "
                "outcome=no admissible checkpoint (methodological rejection); "
                "mandatory admissibility reasons="
                f"{list(acceptance.checkpoint_rejection_reasons)}",
                flush=True,
            )
        with post_selection_publication_barrier(
            context.paths, selected.binding.campaign_generation
        ):
            store.put(acceptance)
            publish_current_post_selection_pointer(
                context.store,
                binding=selected.binding,
                kind=POINTER_ASSESSMENT_POSITION,
                content_digest=acceptance.content_digest,
                position=position,
            )
        acceptances.append(acceptance)

    campaign = accept_post_selection_cv_campaign(
        plan, context.cv_policy, acceptances, expected_positions=expected_positions
    )
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
    try:
        plan = resolve_current_post_selection_record(
            context.store,
            context.paths,
            context.selected,
            kind=POINTER_CV_PLAN,
            deserializer=PostSelectionCvPlan.from_dict,
        )
    except TrainingDataSerializationError as exc:
        raise PostSelectionError(
            "The published CV plan is a pre-cutover historical plan; it is history, "
            "not current authority. Run `cross-validate` to reclose CV under the "
            f"current policy ({exc})."
        ) from exc
    if plan is not None:
        replay_enabled = context.method_policies.replay_enabled
        replay_resolution = None
        if replay_enabled:
            replay_resolution = _resolve_post_selection_replay_resolution(
                context, require_train=True
            )
        replay_lineage_digest = (
            compute_replay_lineage_digest(replay_resolution)
            if replay_enabled
            else None
        )
        common_monitor, monitor_separation = context.common_target_monitor()
        validate_post_selection_cv_plan(
            plan,
            context.selected,
            common_monitor=common_monitor,
            monitor_separation=monitor_separation,
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
    """The current aggregate CV verdict, or ``None``.

    A historical (pre-cutover) verdict is never relabeled current: it simply
    does not resolve here, so CV must be reclosed under the current policy.
    """

    try:
        record = resolve_current_post_selection_record(
            context.store,
            context.paths,
            context.selected,
            kind=POINTER_CV_ACCEPTANCE,
            deserializer=CvCampaignAcceptance.from_dict,
        )
    except TrainingDataSerializationError:
        return None
    if record is None or not record.is_current:
        return None
    for seed_acceptance in record.seed_acceptances:
        for fold in seed_acceptance.fold_acceptances:
            authenticated_post_selection_candidate_records(
                context,
                candidate_record_digests=fold.candidate_record_digests,
                runtime_summary_digest=fold.runtime_summary_digest,
                representative_record_digest=(
                    fold.representative_checkpoint_record_digest
                    if fold.outcome != CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
                    else None
                ),
            )
    return record


# ---------------------------------------------------------------------------
# Fresh final production
# ---------------------------------------------------------------------------


def _previous_final_assessments(context: PostSelectionContext) -> tuple[Any, ...]:
    """Seed assessments behind the previously current publication, as offers only."""

    from .post_selection_publication import FinalProductionPublicationDecision

    try:
        decision = resolve_current_post_selection_record(
            context.store,
            context.paths,
            context.selected,
            kind=POINTER_FINAL_PUBLICATION,
            deserializer=FinalProductionPublicationDecision.from_dict,
        )
    except Exception:
        return ()
    if decision is None:
        return ()
    store = context.evidence_store
    found = []
    for item in decision.seed_evidence:
        try:
            found.append(store.get(item.run_evidence_digest, PostSelectionRunEvidence.from_dict))
        except Exception:
            continue
    return tuple(found)


@dataclass(frozen=True, slots=True)
class _FinalProductionBundle:
    """One selected size's authorized production plan and its positions.

    It is built in memory (Phase A) and published through the size's own
    binding-scoped owner (Phase B).  ``tasks`` is in
    ``FinalProductionPlan.required_final_seeds`` order, which is also the
    finalization order; ``positions`` holds the matching assessment positions.
    """

    context: PostSelectionContext
    final_plan: FinalProductionPlan
    common_monitor: Any
    monitor_separation: Any
    policy_digest: str
    tasks: tuple[_PendingPostSelectionRun, ...]
    positions: tuple[str, ...]


def _plan_final_production(
    context: PostSelectionContext, *, first_key: int
) -> _FinalProductionBundle:
    """Phase A: authorize and construct one size's production without side effects.

    Current accepted CV is re-authenticated before anything else - the
    second-line fence behind the collection barrier: a missing, stale,
    historical or rejected CV blocks production, including the reuse of
    historically produced final bytes.  Nothing here publishes, makes a
    pointer current, or materializes training state.
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
    replay_enabled = context.method_policies.replay_enabled
    replay_resolution = None
    if replay_enabled:
        replay_resolution = _resolve_post_selection_replay_resolution(
            context, require_train=True
        )
    replay_lineage_digest = (
        compute_replay_lineage_digest(replay_resolution)
        if replay_enabled
        else None
    )
    common_monitor, monitor_separation = context.common_target_monitor()
    previous = _previous_final_assessments(context)
    final_plan = build_final_production_plan(
        selected,
        context.method,
        context.production_policy,
        cv_plan=plan,
        cv_acceptance=acceptance,
        common_monitor=common_monitor,
        monitor_separation=monitor_separation,
        replay_lineage_digest=replay_lineage_digest,
        legacy_source_plan_digest=post_selection_legacy_source_plan_digest(
            context, kind=POINTER_FINAL_PLAN
        ),
    )
    validate_final_production_plan(
        final_plan,
        selected,
        method=context.method,
        common_monitor=common_monitor,
        monitor_separation=monitor_separation,
        policy=context.production_policy,
        replay_lineage_digest=replay_lineage_digest,
    )
    store = context.evidence_store
    budget_policy = final_production_training_budget_policy(
        context.method, context.production_policy
    )
    policy_digest = final_seed_assessment_policy_digest(
        post_selection_checkpoint_admissibility(
            context.method_policies, context.production_policy
        )
    )
    tasks: list[_PendingPostSelectionRun] = []
    positions: list[str] = []
    required_seeds = tuple(final_plan.required_final_seeds)
    total_runs = len(required_seeds)
    for slot, seed in enumerate(required_seeds):
        run_plan = build_final_production_run_plan(final_plan, optimizer_seed=seed)
        position = _final_position(context, run_plan, policy_digest)
        positions.append(position)
        offers: dict[str, dict[str, Any]] = {"candidates": {}, "outer": {}}
        sources = list(previous)
        current = resolve_current_post_selection_record(
            context.store,
            context.paths,
            selected,
            kind=POINTER_ASSESSMENT_POSITION,
            deserializer=PostSelectionRunEvidence.from_dict,
            position=position,
        )
        if current is not None:
            sources.insert(0, current)
        for item in sources:
            if item.training_trajectory_identity == run_plan.training_trajectory_identity:
                _offered_measurements(
                    store, candidate_record_digests=item.candidate_record_digests, into=offers
                )
        tasks.append(
            _PendingPostSelectionRun(
                context=context,
                budget_policy=budget_policy,
                slot=slot,
                key=first_key + slot,
                run_plan=run_plan,
                training_frame_uids=tuple(selected.selected_membership),
                monitor_frame_uids=tuple(common_monitor.selected_identities),
                outer_evaluation_frame_uids=None,
                progress_context={
                    "N_selected": selected.n_selected,
                    "run": f"{slot + 1}/{total_runs}",
                    "seed": seed,
                    "restored": "executing",
                    "phase": "executing",
                },
                reusable=_reusable(offers),
            )
        )
    return _FinalProductionBundle(
        context=context,
        final_plan=final_plan,
        common_monitor=common_monitor,
        monitor_separation=monitor_separation,
        policy_digest=policy_digest,
        tasks=tuple(tasks),
        positions=tuple(positions),
    )


def _require_unique_production_identities(
    bundles: Sequence[_FinalProductionBundle],
) -> None:
    """Fail closed before any launch if two positions would share one run.

    Local seed slots repeat across sizes by construction; only the exact
    scientific run and training-trajectory identities may distinguish them.
    """

    for attribute in ("run_identity", "training_trajectory_identity"):
        seen: dict[str, str] = {}
        for bundle in bundles:
            for task in bundle.tasks:
                value = str(getattr(task.run_plan, attribute))
                owner = (
                    f"N={bundle.context.selected.n_selected} "
                    f"seed={task.run_plan.optimizer_seed}"
                )
                if value in seen:
                    raise PostSelectionExecutionError(
                        f"Final-production positions {seen[value]} and {owner} resolve "
                        f"to the same {attribute.replace('_', ' ')} {value[:12]}...; "
                        "a planning/identity defect, so no trainer was launched."
                    )
                seen[value] = owner


def _publish_final_production_plan(bundle: _FinalProductionBundle) -> None:
    """Phase B: publish one size's plan through its own binding-scoped owner."""

    context = bundle.context
    store = context.evidence_store
    with post_selection_publication_barrier(
        context.paths, context.selected.binding.campaign_generation
    ):
        store.put(context.method)
        store.put(context.production_policy)
        store.put(bundle.common_monitor)
        store.put(bundle.monitor_separation)
        store.put(bundle.final_plan)
        publish_current_post_selection_pointer(
            context.store,
            binding=context.selected.binding,
            kind=POINTER_FINAL_PLAN,
            content_digest=bundle.final_plan.content_digest,
        )
    for task in bundle.tasks:
        store.put(task.run_plan)
        store.put(task.run_plan.training_trajectory)


def _normalize_final_production_recovery(
    tasks: Sequence[_PendingPostSelectionRun],
) -> tuple[_PendingPostSelectionRun, ...]:
    """Resolve every production position to sealed state or ``TRAIN_REQUIRED``.

    Runs before the TRAIN admission baseline and before any child starts.

    Resolving *where* a position's bytes live is a locator question and needs
    no exclusion.  Deciding *what* those bytes mean - fresh, incomplete,
    terminal-but-unsealed, sealed, foreign, reusable, or ``TRAIN_REQUIRED`` -
    is a classification question, and every such decision is taken while this
    position's existing run-activity lease is held.  A locator-time
    observation of an absent or empty root is therefore never a conclusion:
    another owner holding the same lease may be creating, continuing, or
    sealing that exact root, and only the post-lease observation is
    authoritative.  Nothing is inferred from PID, mtime, or pathname, and no
    new lease, registry, or collection lock exists.

    Classification runs through the position's own owner: a post-cutover root
    through the execution owner's terminal continuation path, a historical
    root through the historical recovery owner.  An authenticated
    terminal-but-unsealed root is sealed exactly as those owners seal it, with
    no trainer launch; every sealed root is then authenticated read-only.
    Only positions that still need trainer execution are returned.  The lease
    is released before scheduler admission, so it is never held across the
    wave.  Seals made here are recovery completions and stay durable whatever
    happens later; nothing is evaluated or published.
    """

    required: list[_PendingPostSelectionRun] = []
    resolved_roots: dict[Path, str] = {}
    for task in sorted(tasks, key=lambda item: int(item.key)):
        context = task.context
        root = resolve_post_selection_training_root(context, task.run_plan)
        owner = f"N={context.selected.n_selected} seed={task.run_plan.optimizer_seed}"
        path_key = root.path.absolute()
        if path_key in resolved_roots:
            raise PostSelectionExecutionError(
                f"Final-production positions {resolved_roots[path_key]} and {owner} "
                "resolve to the same training root; no trainer was launched."
            )
        resolved_roots[path_key] = owner
        description = "; ".join(
            f"{key}={value}" for key, value in task.progress_context.items()
        )
        with post_selection_run_activity_lease(root.path):
            if root.legacy is None and not (
                root.path.is_dir() and any(root.path.iterdir())
            ):
                # Authoritative under the lease: no durable trajectory exists
                # and no other owner is mid-transition, so this position
                # genuinely still requires trainer execution.
                required.append(task)
                continue
            completion, _why = read_post_selection_run_completion(root.path)
            recovered = completion is None
            if completion is None:
                arguments: dict[str, Any] = dict(
                    run_plan=task.run_plan,
                    budget_policy=task.budget_policy,
                    progress_context=task.progress_context,
                    cancellation_event=None,
                    progress_callback=None,
                    progress_observer=None,
                    telemetry_ref=None,
                    launch_trainer=False,
                )
                if root.legacy is not None:
                    sealed_now = _complete_legacy_training_root(
                        context, root=root, **arguments
                    )
                else:
                    sealed_now = _train_post_selection_run(
                        context,
                        training_frame_uids=task.training_frame_uids,
                        monitor_frame_uids=task.monitor_frame_uids,
                        outer_evaluation_frame_uids=task.outer_evaluation_frame_uids,
                        run_root=root.path,
                        **arguments,
                    )
                if not sealed_now:
                    required.append(task)
                    continue
                completion, why = read_post_selection_run_completion(root.path)
                if completion is None:
                    raise PostSelectionExecutionError(
                        f"Training root {root.identity[:12]}... is not sealed after "
                        f"terminal recovery normalization: {why}"
                    )
            _authenticate_sealed_training_root(
                context,
                run_plan=task.run_plan,
                budget_policy=task.budget_policy,
                root=root,
                completion=completion,
            )
        print(
            "[TRAIN] status=reused; "
            + (
                "terminal TRAIN2 sealed by recovery; "
                if recovered
                else "sealed training root; "
            )
            + description,
            flush=True,
        )
    return tuple(required)


def _train_final_production_collection(
    bundles: Sequence[_FinalProductionBundle],
    *,
    signature: tuple[int, tuple[str, ...]],
) -> tuple[int, ...]:
    """Normalize recovery, then TRAIN every ``TRAIN_REQUIRED`` position in one wave.

    One scheduler owns every selected size's remaining TRAIN2 work; every
    admission, including readmission after demotion, is linearized against
    target-size generation transitions through the canonical collection
    signature.
    """

    from .training_parallel import query_gpu_telemetry

    tasks = tuple(task for bundle in bundles for task in bundle.tasks)
    devices = dict.fromkeys(str(task.context.method_policies.device) for task in tasks)
    for device in devices:
        # Recovery normalization can realize training-side state, so the
        # admission baseline is observed only after it has finished.
        _report_post_selection_gpu_occupancy(
            "pre-recovery-preflight", device, query_gpu_telemetry(device)
        )
    required = _normalize_final_production_recovery(tasks)
    print(
        f"[TRAIN] production recovery: positions={len(tasks)}; "
        f"train_required={len(required)}; sealed={len(tasks) - len(required)}",
        flush=True,
    )
    store = bundles[0].context.store
    return _train_post_selection_pending_runs(
        required,
        admission_fence=lambda: post_selection_collection_admission(
            store, signature=signature
        ),
    )


def _finalize_final_production(
    bundle: _FinalProductionBundle,
) -> tuple[tuple[PostSelectionRunEvidence, ...], "FinalProductionPublicationDecision"]:
    """Serial EVAL2, per-seed assessment, then final publication of one size.

    Every required seed is evaluated from its sealed root in
    ``required_final_seeds`` order and assessed at its own position (final
    hard policy + D2.DEF.059A only); every candidate and the typed outcome are
    durably published before any failure is reported.
    """

    from .progress_timing import format_progress_fraction

    context = bundle.context
    selected = context.selected
    store = context.evidence_store
    total_runs = len(bundle.tasks)
    results: list[PostSelectionRunResult] = []
    for index, task in enumerate(bundle.tasks):
        print(
            f"[EVAL2 serial] status=running; "
            f"progress={format_progress_fraction(index, total_runs)}; "
            f"unit=training-run; N_selected={selected.n_selected}; "
            f"seed={task.run_plan.optimizer_seed}",
            flush=True,
        )
        result = _execute_pending_post_selection_run(task, reusable=task.reusable)
        if result is None:
            raise PostSelectionExecutionError(
                f"Sealed production position N={selected.n_selected} seed "
                f"{task.run_plan.optimizer_seed} produced no evaluated result."
            )
        results.append(result)
    evidence: list[PostSelectionRunEvidence] = []
    for task, position, result in zip(bundle.tasks, bundle.positions, results):
        run_plan = task.run_plan
        publish_post_selection_run_measurements(context, result)
        representative = result.representative
        reasons = tuple(
            sorted({reason for item in result.candidates for reason in item.rejection_reasons})
        )
        assessment = PostSelectionRunEvidence(
            selected_binding_digest=selected.binding.content_digest,
            assessment_position_policy_digest=bundle.policy_digest,
            training_trajectory_identity=run_plan.training_trajectory_identity,
            training_root_identity=result.training_root_identity,
            optimizer_seed=run_plan.optimizer_seed,
            materialization_digest=result.materialization.content_digest,
            runtime_summary_digest=result.runtime_summary_digest,
            outcome=(
                RUN_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
                if representative is None
                else RUN_OUTCOME_REPRESENTATIVE_SELECTED
            ),
            candidate_record_digests=tuple(item.content_digest for item in result.candidates),
            checkpoint_rejection_reasons=reasons,
            representative_candidate_identity=(
                None if representative is None else representative.stable_candidate_identity
            ),
            representative_checkpoint_sha256=(
                None
                if representative is None
                else representative.trajectory_point.checkpoint_sha256
            ),
            representative_record_digest=(
                None if representative is None else representative.content_digest
            ),
            monitor_metric_record_digest=(
                None if representative is None else result.monitor_metrics.content_digest
            ),
        )
        with post_selection_publication_barrier(
            context.paths, selected.binding.campaign_generation
        ):
            store.put(assessment)
            publish_current_post_selection_pointer(
                context.store,
                binding=selected.binding,
                kind=POINTER_ASSESSMENT_POSITION,
                content_digest=assessment.content_digest,
                position=position,
            )
        evidence.append(assessment)

    rejected = [item for item in evidence if not item.selected]
    if rejected:
        detail = "; ".join(
            f"seed {item.optimizer_seed}: {list(item.checkpoint_rejection_reasons)}"
            for item in rejected
        )
        raise PostSelectionError(
            "No checkpoint passed mandatory hard admissibility for final-production "
            f"{detail} (production checkpoint target-force ceiling "
            f"{context.production_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom}"
            " eV/angstrom). The complete assessed candidate sets and the typed "
            "no-admissible outcome are published; an inadmissible checkpoint is never "
            "promoted to a representative."
        )

    # Deciding which of the completed seeds constitute the released product is
    # the last pre-qualification act, and it belongs here: every input it uses
    # already exists, and no downstream release evidence does yet.
    completion = FinalProductionCompletion(plan=bundle.final_plan, runs=tuple(evidence))
    decision = publish_final_production_publication(context, context.store, completion)
    return tuple(evidence), decision


def resolve_current_final_production_plan(
    context: PostSelectionContext,
) -> FinalProductionPlan | None:
    try:
        plan = resolve_current_post_selection_record(
            context.store,
            context.paths,
            context.selected,
            kind=POINTER_FINAL_PLAN,
            deserializer=FinalProductionPlan.from_dict,
        )
    except TrainingDataSerializationError:
        return None
    if plan is not None:
        replay_enabled = context.method_policies.replay_enabled
        replay_resolution = None
        if replay_enabled:
            replay_resolution = _resolve_post_selection_replay_resolution(
                context, require_train=True
            )
        replay_lineage_digest = (
            compute_replay_lineage_digest(replay_resolution)
            if replay_enabled
            else None
        )
        common_monitor, monitor_separation = context.common_target_monitor()
        validate_final_production_plan(
            plan,
            context.selected,
            method=context.method,
            common_monitor=common_monitor,
            monitor_separation=monitor_separation,
            policy=context.production_policy,
            replay_lineage_digest=replay_lineage_digest,
        )
    return plan


FINAL_PRODUCTION_COMPLETION_SCHEMA = "mdstats.mlff-final-production-completion.v2"


@dataclass(frozen=True, slots=True)
class FinalProductionCompletion:
    """Every required seed's current selected assessment for the exact final plan."""

    plan: FinalProductionPlan
    runs: tuple[PostSelectionRunEvidence, ...]
    content_digest: str = ""

    def __post_init__(self) -> None:
        if not self.runs:
            raise PostSelectionError("Final-production completion requires at least one run.")
        if any(not run.selected for run in self.runs):
            raise PostSelectionError(
                "Final-production completion requires a selected representative for "
                "every required seed."
            )
        payload = {
            "schema": FINAL_PRODUCTION_COMPLETION_SCHEMA,
            "final_plan_digest": self.plan.content_digest,
            "required_final_seeds": list(self.plan.required_final_seeds),
            "run_evidence_digests": [run.content_digest for run in self.runs],
            "training_trajectory_identities": [
                run.training_trajectory_identity for run in self.runs
            ],
        }
        object.__setattr__(self, "content_digest", digest(payload))


def resolve_current_final_production_completion(
    context: PostSelectionContext,
) -> FinalProductionCompletion | None:
    """Every required seed's current assessment, found through its position locator.

    The locator is not authority: each located assessment must bind the exact
    current position (binding, final-seed policy, trajectory, seed) and a
    selected representative, and publication re-authenticates its records.
    """

    plan = resolve_current_final_production_plan(context)
    if plan is None:
        return None
    evidence: list[PostSelectionRunEvidence] = []
    for seed in plan.required_final_seeds:
        run_plan = build_final_production_run_plan(plan, optimizer_seed=seed)
        completed = resolve_current_final_seed_assessment(context, run_plan)
        if completed is None or not completed.selected:
            return None
        evidence.append(completed)
    return FinalProductionCompletion(plan=plan, runs=tuple(evidence))


def resolve_current_final_seed_assessment(
    context: PostSelectionContext, run_plan: Any
) -> PostSelectionRunEvidence | None:
    """The current assessment of one final-seed position, or ``None``.

    Located through the position locator under the *current* final hard policy
    + D2.DEF.059A; the located record must bind exactly that position.
    """

    policy_digest = final_seed_assessment_policy_digest(
        post_selection_checkpoint_admissibility(
            context.method_policies, context.production_policy
        )
    )
    completed = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_ASSESSMENT_POSITION,
        deserializer=PostSelectionRunEvidence.from_dict,
        position=_final_position(context, run_plan, policy_digest),
    )
    if completed is not None and (
        completed.training_trajectory_identity != run_plan.training_trajectory_identity
        or completed.assessment_position_policy_digest != policy_digest
        or completed.optimizer_seed != int(run_plan.optimizer_seed)
        or completed.selected_binding_digest != context.selected.binding.content_digest
    ):
        raise PostSelectionError(
            f"The assessment located for production seed {run_plan.optimizer_seed} "
            "belongs to a different assessment position."
        )
    if completed is not None:
        authenticated_post_selection_candidate_records(
            context,
            candidate_record_digests=completed.candidate_record_digests,
            runtime_summary_digest=completed.runtime_summary_digest,
            representative_record_digest=(
                completed.representative_record_digest
                if completed.selected
                else None
            ),
        )
    return completed


def resolve_current_cv_fold_assessment(
    context: PostSelectionContext, run_plan: Any
) -> CvFoldAcceptance | None:
    """The current assessment of one CV fold position, or ``None``."""

    policy_digest = cv_assessment_position_policy_digest(
        post_selection_checkpoint_admissibility(context.method_policies, context.cv_policy),
        context.cv_policy,
    )
    located = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_ASSESSMENT_POSITION,
        deserializer=CvFoldAcceptance.from_dict,
        position=_cv_position(context, run_plan, policy_digest),
    )
    if located is not None and (
        not located.is_current
        or located.training_trajectory_identity != run_plan.training_trajectory_identity
        or located.assessment_position_policy_digest != policy_digest
        or (located.cv_seed, located.fold_index)
        != (int(run_plan.optimizer_seed), int(run_plan.fold_index))
    ):
        raise PostSelectionError(
            "The assessment located for a CV fold belongs to a different assessment position."
        )
    if located is not None:
        authenticated_post_selection_candidate_records(
            context,
            candidate_record_digests=located.candidate_record_digests,
            runtime_summary_digest=located.runtime_summary_digest,
            representative_record_digest=(
                located.representative_checkpoint_record_digest
                if located.outcome != CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE
                else None
            ),
        )
    return located


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
            f"seeds={list(plan.required_cv_seeds)}, "
            "CV checkpoint target-force ceiling="
            f"{context.cv_policy.checkpoint_maximum_target_force_rmse_ev_per_angstrom} "
            "eV/angstrom.",
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
        raise PostSelectionCvRejectedError(
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


def _print_published_model_products(context: Any, decision: Any) -> None:
    """Print the authoritative usable product of one committed size.

    Discovering the product must not require inspecting internal hash
    directories or running a second command, and it must never point at the
    trainer's run-root terminal ``.model``, which belongs to the last TRAIN2
    epoch rather than the P5-selected representative.  One deterministic line
    per member, in decision member order.
    """

    from .post_selection_model_products import (
        campaign_models_root,
        resolve_current_final_production_model_publication,
    )

    record = resolve_current_final_production_model_publication(context, decision)
    if record is None:  # pragma: no cover - commit precedes this call
        raise PostSelectionError(
            f"N={context.selected.n_selected}: no current model publication resolved "
            "after the authoritative product commit."
        )
    models_root = campaign_models_root(context)
    for member in record.members:
        print(
            f"[PRODUCT] N={context.selected.n_selected} member={member.member_id} "
            f"seed={member.optimizer_seed} head={record.target_head_name} "
            f"model={models_root / member.model_relative_path} "
            f"sha256={member.model_sha256}",
            flush=True,
        )


def execute_current_train_production(args: Any) -> int:
    """`train-production`: fresh full-``T_selected`` production for every size.

    Admission is a collection-wide barrier: the complete frozen design is
    authenticated and every selected size must hold current accepted CV ancestry
    under its own binding and its own ``H_cv`` before *any* new production job
    starts.  Evidence already published by an earlier attempt keeps whatever
    currentness its own identity earns; what the barrier prevents is admitting
    new work that would present a partial experiment as a whole one.

    After the barrier every size is planned in memory under its own second-line
    CV authorization (Phase A) and then published through its own binding
    (Phase B).  Recovery is normalized across the collection, and every
    position still requiring TRAIN2 shares one bounded TRAIN wave.  Only once
    that wave is terminal are sizes finalized - serial EVAL2, per-seed
    assessment, publication - one at a time in frozen order, stopping at the
    first size that fails.  Plan pointers and recovery seals are per binding
    and per root; nothing here is rolled back to imitate collection atomicity.
    """

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
    )
    from .training_parallel import query_gpu_telemetry

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

    def fail(detail: str) -> None:
        _mark_stage(
            store,
            paths,
            "post_selection_final_production",
            StageState.FAILED,
            detail,
        )

    blockers = _cv_admission_blockers(contexts)
    if blockers:
        detail = "; ".join(blockers)
        fail(detail)
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
    # Capture the exact design this invocation is authorized for before any
    # plan is built; every later admission is linearized against it.
    signature = post_selection_collection_signature(
        tuple(context.selected.binding for context in contexts)
    )
    # Recovery classification, before any new TRAIN/EVAL admission.  A size
    # that already owns an exactly replayable decision owes representation at
    # most, and representation is never a reason to retrain: only genuine
    # PRODUCTION_REQUIRED positions enter the accepted global TRAIN wave, and
    # the reclosure/finalization work stays in the serial post-TRAIN path.
    from .post_selection_product_recovery import (
        PRODUCT_COMPLETE,
        PRODUCT_RECLOSURE,
        classify_product_recovery,
        reclose_product_representation,
    )

    classifications: dict[int, Any] = {}
    for context in contexts:
        n_selected = context.selected.n_selected
        try:
            classification = classify_product_recovery(context)
        except Exception as exc:
            fail(f"N={n_selected}: {exc}")
            raise
        classifications[int(n_selected)] = classification
        print(
            f"[PRODUCT] N={n_selected}: {classification.state}; "
            f"{classification.detail}",
            flush=True,
        )
    training_contexts = [
        context
        for context in contexts
        if classifications[int(context.selected.n_selected)].admits_training
    ]
    bundles: list[_FinalProductionBundle] = []
    for context in training_contexts:
        first_key = sum(len(bundle.tasks) for bundle in bundles)
        try:
            bundles.append(_plan_final_production(context, first_key=first_key))
        except Exception as exc:
            fail(f"N={context.selected.n_selected}: {exc}")
            raise
    try:
        _require_unique_production_identities(bundles)
    except Exception as exc:
        fail(str(exc))
        raise
    for bundle in bundles:
        try:
            _publish_final_production_plan(bundle)
        except Exception as exc:
            fail(f"N={bundle.context.selected.n_selected}: {exc}")
            raise
    if bundles:
        try:
            _train_final_production_collection(bundles, signature=signature)
            # Admission of the finalization phase is linearized exactly like a
            # TRAIN admission; later rollover is refused by the commit-time
            # per-binding fences of every assessment and publication.
            with post_selection_collection_admission(store, signature=signature):
                pass
        except Exception as exc:
            fail(f"production TRAIN2 collection wave: {exc}")
            raise
        devices = dict.fromkeys(
            str(bundle.context.method_policies.device) for bundle in bundles
        )
        for device in devices:
            _report_post_selection_gpu_occupancy(
                "post-TRAIN EVAL2 entry", device, query_gpu_telemetry(device)
            )
    bundle_by_size = {
        int(bundle.context.selected.n_selected): bundle for bundle in bundles
    }
    published: list[str] = []
    # Serial finalization in frozen selected-size order: fresh production,
    # representation reclosure and create-or-verify all run here, one size at a
    # time, after the shared TRAIN wave is terminal.
    for context in contexts:
        n_selected = context.selected.n_selected
        classification = classifications[int(n_selected)]
        bundle = bundle_by_size.get(int(n_selected))
        try:
            if bundle is not None:
                evidence, decision = _finalize_final_production(bundle)
                _ok(
                    f"N={n_selected}: trained {len(evidence)} fresh production run(s) "
                    f"on the full T_selected for {bundle.final_plan.planned_epochs} "
                    "frozen production epoch(s), under the cross-validation-accepted "
                    "method"
                )
            elif classification.state in (PRODUCT_COMPLETE, PRODUCT_RECLOSURE):
                decision, _record, _reclosure = reclose_product_representation(
                    context, classification
                )
                _ok(
                    f"N={n_selected}: verified the existing published model "
                    "product; no training or evaluation was required"
                    if classification.state == PRODUCT_COMPLETE
                    else f"N={n_selected}: the existing scientifically valid final "
                    "production was reclosed into a current usable model product "
                    "with no TRAIN2 and no EVAL2"
                )
            else:  # pragma: no cover - every state is handled above
                raise PostSelectionError(
                    f"N={n_selected}: unhandled product recovery state "
                    f"{classification.state!r}."
                )
        except Exception as exc:
            fail(f"N={n_selected}: {exc}")
            raise
        _ok(
            f"N={n_selected}: published the final product under "
            f"`{decision.committee_policy}`: member(s) "
            f"{list(decision.published_member_ids)} on target head "
            f"`{decision.target_head_name}`"
        )
        _print_published_model_products(context, decision)
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
    "execute_post_selection_cross_validation",
    "execute_post_selection_run",
    "resolve_current_cv_acceptance",
    "resolve_current_cv_plan",
    "authenticated_post_selection_candidate_records",
    "authenticated_run_representative_records",
    "evaluate_post_selection_run_candidates",
    "resolve_current_final_production_completion",
    "resolve_current_final_seed_assessment",
    "resolve_current_cv_fold_assessment",
    "resolve_current_final_production_publication",
    "resolve_current_final_production_plan",
    "resolve_post_selection_evaluation_model_state",
]
