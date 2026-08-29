"""Current production target-size orchestration for `prepare` and `select-target-size`.

This module is the only production orchestration for target-size work after the
runtime cutover.  It owns *sequencing* and nothing scientific: candidate
qualification, the split, training and evaluation order, reducer advancement,
candidate realization, materialization, TRAIN2 continuation, EVAL2 reduction,
immutable publication, and crash replay all remain with their accepted P1, P2,
and P3 owners.  What lives here is the call order between those owners and the
campaign store, plus the process launcher that gives one candidate rung to MACE.

The division of labour between the two public commands is deliberate and
enforced:

``prepare`` reconstructs the current scientific substrate - P1 source and frame
authority, the neutral statistical base, the P2 experiment definition, and the
one common preparation - all of which are deterministic and independent of any
candidate size.  It cannot select ``N``, run the reducer, train a candidate, or
rank anything, and there is no code path here by which it could.

``select-target-size`` owns the screen.  It reconciles the existing P3 root
before scheduling anything new, derives the active matrix from the authenticated
reducer state, executes only the surviving cells through P3 owners, publishes
through P3, reconciles, and CAS-adopts the exact reconciled head - repeating
only while the P2 reducer says the experiment is nonterminal.

Expensive numerical work has exactly one seam, below the accepted owner
boundary: :class:`TargetSizeBoundaryTrainer` produces the TRAIN2 runtime summary
for one rung.  Everything above it - configuration parsing, authority
construction, materialization validation, provider and checkpoint
authentication, publication, reconciliation, and adoption - is real production
code in every invocation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence
import json
import os
import subprocess
import sys

from ._common import TrainingDataError, TrainingDataInputError

TARGET_SIZE_EXECUTION_ROOT_NAME = "target-size"


class TargetSizeRuntimeError(TrainingDataError):
    """The current target-size runtime cannot proceed."""


# ---------------------------------------------------------------------------
# Current scientific authority construction (shared by both commands)
# ---------------------------------------------------------------------------


def resolve_neutral_partition_policy(cfg: Mapping[str, Any]) -> Any:
    """Map the campaign ``[partition]`` namespace onto the P1 partition policy.

    This is configuration translation only.  Every value comes from the same
    ``[partition]`` keys the rest of the campaign already exposes, and every
    unset key keeps the accepted P1 default, so the neutral substrate's own
    policy remains the authority on what these settings mean.
    """

    import mdstats
    from ._campaign_cli_core import _cfg
    from .neutral_substrate import NeutralPartitionPolicy, NeutralRoleBudget

    defaults = NeutralRoleBudget()
    policy_defaults = NeutralPartitionPolicy()
    block_defaults = policy_defaults.block_policy
    explicit_block = _cfg(cfg, "partition", "explicit_block_length_frames", None)
    return NeutralPartitionPolicy(
        role_budget=NeutralRoleBudget(
            development_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "development_minimum_independent_units",
                    defaults.development_minimum_independent_units,
                )
            ),
            outer_monitor_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "outer_monitor_minimum_independent_units",
                    defaults.outer_monitor_minimum_independent_units,
                )
            ),
            calibration_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "calibration_minimum_independent_units",
                    defaults.calibration_minimum_independent_units,
                )
            ),
            locked_interpolation_test_minimum_independent_units=int(
                _cfg(
                    cfg,
                    "partition",
                    "locked_interpolation_test_minimum_independent_units",
                    defaults.locked_interpolation_test_minimum_independent_units,
                )
            ),
            purge_units_between_roles=int(
                _cfg(
                    cfg,
                    "partition",
                    "purge_units_between_roles",
                    defaults.purge_units_between_roles,
                )
            ),
            allow_calibration_deferral=bool(
                _cfg(
                    cfg,
                    "partition",
                    "allow_calibration_deferral",
                    defaults.allow_calibration_deferral,
                )
            ),
        ),
        block_policy=mdstats.CompleteFrameBlockPolicy(
            minimum_block_frames=int(
                _cfg(
                    cfg,
                    "partition",
                    "minimum_block_frames",
                    block_defaults.minimum_block_frames,
                )
            ),
            explicit_block_length_frames=(
                None if explicit_block is None else int(explicit_block)
            ),
        ),
        minimum_units_per_condition_for_full_outer_roles=int(
            _cfg(
                cfg,
                "partition",
                "minimum_units_per_condition_for_full_outer_roles",
                policy_defaults.minimum_units_per_condition_for_full_outer_roles,
            )
        ),
    )


@dataclass(frozen=True, slots=True)
class CurrentTargetSizeAuthorities:
    """One reconstructed current P1/P2/P3 authority bundle.

    Every member is rebuilt from source inputs through its accepted owner.  The
    campaign store holds only their identities, so nothing here is ever restored
    from a mutable campaign row.
    """

    manifest: Any
    source_catalog: Any
    source_authority: Any
    frame_authority: Any
    feature_evidence: Any
    neutral_base: Any
    split_exclusion: Any
    aggregate: Any
    common: Any
    frame_catalog: Any
    frame_data_by_run: Mapping[str, Any]
    frame_array_index: Mapping[str, Any]

    @property
    def identity(self) -> dict[str, str]:
        return {
            "frame_authority_digest": self.frame_authority.content_digest,
            "neutral_statistical_base_digest": self.neutral_base.content_digest,
            "split_exclusion_digest": self.split_exclusion.content_digest,
            "policy_digest": self.aggregate.policy.content_digest,
            "experiment_definition_digest": self.aggregate.definition.content_digest,
            "aggregate_digest": self.aggregate.content_digest,
        }


def build_current_target_size_authorities(
    cfg: Mapping[str, Any], paths: Any, store: Any
) -> CurrentTargetSizeAuthorities:
    """Rebuild the current P1 -> P2 -> P3-common chain through its owners.

    Only lower-level content-addressed inputs whose identity is independent of
    retired target-size semantics are reused, and each is re-validated by the
    owner that consumes it.  No retired selector, role-domain, coverage, or
    qualification record participates.
    """

    import mdstats
    from ._campaign_cli_core import (
        _ensure_manifest,
        _load_or_rebuild_frame_data,
        _path_cfg,
    )
    from ._frame_access import build_frame_array_index
    from .neutral_substrate import (
        build_neutral_feature_evidence_from_data4_bundle,
        build_neutral_split_exclusion_evidence,
        build_neutral_statistical_base,
        build_source_authority_from_data2_catalog,
        build_vasp_canonical_frame_authority,
    )
    from .target_size_execution import build_target_size_common_preparation
    from .target_size_experiment import (
        build_target_size_statistical_aggregate,
        resolve_target_size_policy_from_config,
    )

    training_root = _path_cfg(cfg, paths, "training_root")
    if training_root is None:
        raise TargetSizeRuntimeError(
            "The current target-size runtime requires [data].training_root."
        )
    manifest = _ensure_manifest(cfg, paths, approve=False)
    source_catalog = store.get_record(
        "source_catalog", mdstats.TrainingDataSourceCatalog
    )
    data4 = store.get_record("data4", mdstats.Data4FeatureBundle)
    frame_catalog = store.get_record("frame_catalog", mdstats.TrainingFrameCatalog)

    source_authority = build_source_authority_from_data2_catalog(
        source_catalog, manifest=manifest
    )
    frame_authority = build_vasp_canonical_frame_authority(
        source_authority, base_directory=training_root
    )
    feature_evidence = build_neutral_feature_evidence_from_data4_bundle(
        source_authority, frame_authority, data4
    )
    neutral_base = build_neutral_statistical_base(
        source_authority,
        frame_authority,
        feature_evidence,
        policy=resolve_neutral_partition_policy(cfg),
    )
    split_exclusion = build_neutral_split_exclusion_evidence(
        frame_authority, neutral_base
    )
    aggregate = build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=resolve_target_size_policy_from_config(cfg),
    )
    frame_data_by_run = _load_or_rebuild_frame_data(cfg, paths, source_catalog)
    frame_array_index = build_frame_array_index(frame_catalog, frame_data_by_run)
    common = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )
    return CurrentTargetSizeAuthorities(
        manifest=manifest,
        source_catalog=source_catalog,
        source_authority=source_authority,
        frame_authority=frame_authority,
        feature_evidence=feature_evidence,
        neutral_base=neutral_base,
        split_exclusion=split_exclusion,
        aggregate=aggregate,
        common=common,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
    )


def current_target_size_execution_root(paths: Any, generation: int) -> Path:
    """Campaign-owned durable execution root for one canonical generation."""

    return (
        Path(paths.internal) / TARGET_SIZE_EXECUTION_ROOT_NAME / f"g{int(generation)}"
    )


def current_target_size_execution_root_locator(paths: Any, generation: int) -> str:
    root = current_target_size_execution_root(paths, generation)
    return root.relative_to(Path(paths.workspace)).as_posix()


# ---------------------------------------------------------------------------
# The one expensive-work seam: executing a single candidate rung
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TargetSizeRungRequest:
    """Everything a TRAIN2 rung needs, already authenticated by P3 owners."""

    plan: Any
    trajectory: Any
    materialization: Any
    materialization_directory: Path
    checkpoint_directory: Path
    start_epoch: int
    optimizer_policy: Any


class TargetSizeBoundaryTrainer(Protocol):
    """Execute one candidate rung and return its TRAIN2 runtime summary.

    This is the only accepted substitution point for expensive numerical work.
    It sits strictly below the owner boundary: the trajectory, materialization,
    rung plan, predecessor continuation, and checkpoint workspace handed to it
    were all produced and validated by real P3 owners, and everything it returns
    is re-authenticated by ``bind_target_size_boundary_state`` before it can
    become evidence.
    """

    def __call__(self, request: TargetSizeRungRequest) -> Any:
        ...


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
)


def mace_run_configuration(target_size_config: Mapping[str, Any]) -> dict[str, Any]:
    """Translate the canonical P3 candidate configuration into MACE arguments.

    P3 owns the scientific description of a candidate run - exact membership
    files, the common E0 mapping, the frozen optimizer policy, and the
    architecture.  MACE's command line expects its own key names, so this
    adapter renames and flattens without deciding anything: no value here is
    computed, defaulted, or overridden.
    """

    from .target_size_execution import TARGET_SIZE_MACE_CONFIG_SCHEMA

    if target_size_config.get("schema") != TARGET_SIZE_MACE_CONFIG_SCHEMA:
        raise TargetSizeRuntimeError(
            "Candidate MACE configuration does not carry the accepted P3 schema."
        )
    config: dict[str, Any] = {
        key: target_size_config[key]
        for key in _MACE_CONFIG_PASSTHROUGH_KEYS
        if key in target_size_config
    }
    config["train_file"] = target_size_config["target_train_file"]
    config["valid_file"] = target_size_config["target_valid_file"]
    architecture = target_size_config.get("mace_architecture") or {}
    for key, value in dict(architecture).items():
        # The architecture is canonicalized by the model-feature owner; it never
        # overrides an optimizer or data key the candidate configuration set.
        config.setdefault(str(key), value)
    return config


@dataclass(frozen=True, slots=True)
class MaceTargetSizeBoundaryTrainer:
    """Production rung executor: run MACE through the qualified wrapper.

    The wrapper is the same qualified ``mdstats-mace-train`` entry point the
    rest of the campaign uses, so critical-precision policy, warning handling,
    and the TRAIN2 runtime hooks are all active.  The rung plan travels in the
    environment exactly as it does for ordinary campaign training, which is what
    makes exact completed-epoch continuation work.
    """

    wrapper_path: Path
    environment: Mapping[str, str] | None = None
    timeout_seconds: float | None = None

    def __call__(self, request: TargetSizeRungRequest) -> Any:
        import mdstats

        run_root = request.checkpoint_directory.parent
        model_dir = run_root / "models"
        log_dir = run_root / "logs"
        result_dir = run_root / "results"
        for directory in (
            model_dir,
            log_dir,
            result_dir,
            request.checkpoint_directory,
        ):
            directory.mkdir(parents=True, exist_ok=True)

        source = json.loads(
            (
                request.materialization_directory
                / request.materialization.mace_config_relative_path
            ).read_text(encoding="utf-8")
        )
        run_config = mace_run_configuration(source)
        config_path = run_root / "mace_run_config.yaml"
        config_path.write_text(
            json.dumps(run_config, indent=2, sort_keys=True), encoding="utf-8"
        )

        environment = dict(os.environ)
        environment.update(dict(self.environment or {}))
        environment[mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE] = json.dumps(
            request.plan.to_dict(), sort_keys=True, separators=(",", ":")
        )
        environment["PYTHONHASHSEED"] = str(int(request.trajectory.optimizer_seed))
        command = [
            str(self.wrapper_path),
            "--config",
            str(config_path),
            "--model_dir",
            str(model_dir),
            "--checkpoints_dir",
            str(request.checkpoint_directory),
            "--log_dir",
            str(log_dir),
            "--results_dir",
            str(result_dir),
        ]
        if request.start_epoch > 0:
            command.append("--restart_latest")
        completed = subprocess.run(
            command,
            cwd=str(request.materialization_directory),
            env=environment,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise TargetSizeRuntimeError(
                "Candidate TRAIN2 rung failed for "
                f"n={request.trajectory.target_size} "
                f"seed={request.trajectory.optimizer_seed} "
                f"boundary={request.plan.execution_epoch_limit}: "
                f"exit status {completed.returncode}. Logs: {log_dir}"
            )
        return mdstats.load_train2_runtime_summary(request.checkpoint_directory)


# ---------------------------------------------------------------------------
# `prepare`: reconstruct the current substrate; never select N
# ---------------------------------------------------------------------------


def execute_current_prepare(args: Any) -> int:
    """Rebuild the current target-size scientific substrate.

    This performs, resumes, or reuses the destructive generation cutover and
    then binds the reconstructed P1/P2 identities plus the one common
    preparation.  It deliberately stops there: no candidate is selected,
    trained, materialized, or ranked, and the P2 reducer is not advanced.
    """

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _atomic_json,
        _load_config,
        _mark_stage,
        _ok,
        _prepare_catalog,
        _print_header,
        _require_stage_complete,
    )
    from .campaign_target_size_cutover import ensure_current_target_size_authorities
    from .campaign_target_size_view import write_target_size_result_view

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    _require_stage_complete(store, paths, "doctor")
    _print_header("Preparing the current target-size scientific substrate")
    _mark_stage(
        store,
        paths,
        "prepare",
        StageState.RUNNING,
        "rebuilding the current P1/P2 substrate and common preparation",
    )
    try:
        if bool(getattr(args, "rebuild_catalog", False)) or not store.has_record("data5"):
            _prepare_catalog(
                cfg,
                paths,
                store,
                approve_manifest=bool(getattr(args, "approve_manifest", False)),
                refresh_inferences=bool(getattr(args, "refresh_inferences", False)),
            )
        else:
            _ok(
                "lower-level source, frame, and feature inputs are present and will be "
                "re-validated by the current P1 owners"
            )
        authorities = build_current_target_size_authorities(cfg, paths, store)
        revision = ensure_current_target_size_authorities(
            store,
            authorities.identity,
            common_preparation_digest=authorities.common.content_digest,
        )
    except Exception as exc:
        _mark_stage(store, paths, "prepare", StageState.FAILED, str(exc))
        raise
    _ok(
        "current target-size substrate is bound: canonical generation "
        f"{revision.state.generation}; "
        f"experiment={revision.state.experiment_definition_digest[:12]}...; "
        f"common preparation={authorities.common.content_digest[:12]}..."
    )
    print(
        "`prepare` does not select a target size. The candidate ladder "
        f"{list(authorities.aggregate.definition.qualified_candidate_sizes)} is a "
        "configured experiment definition, and the paired-seed screen that decides "
        "N is owned by `select-target-size`.",
        flush=True,
    )
    _atomic_json(
        paths.results / "target-size-state.json",
        write_target_size_result_view(
            paths.results / "target-size-state.json", revision
        ),
    )
    _mark_stage(
        store,
        paths,
        "prepare",
        StageState.COMPLETE,
        f"current target-size substrate bound at generation {revision.state.generation}",
    )
    print("Next: `preflight`, then `select-target-size`.", flush=True)
    return 0


# ---------------------------------------------------------------------------
# `select-target-size`: the only current screening entrypoint
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _ScreenContext:
    cfg: Mapping[str, Any]
    paths: Any
    store: Any
    authorities: CurrentTargetSizeAuthorities
    aggregate: Any
    schedule: Any
    context: Any
    optimizer_policy: Any
    correlation_blocks: Mapping[str, str]
    extxyz_policy: Any
    root: Path
    window: Any
    authority: Any
    trainer: TargetSizeBoundaryTrainer
    inference_evaluator: Callable[..., Any] | None


def _bulk_roots(root: Path) -> dict[str, Path]:
    """Campaign-owned bulk roots, all inside the protected execution root."""

    roots = {
        "materialization": root / "bulk" / "materializations",
        "snapshot": root / "bulk" / "snapshots",
        "evaluation": root / "bulk" / "evaluations",
        "train2": root / "bulk" / "train2",
    }
    for path in roots.values():
        path.mkdir(parents=True, exist_ok=True)
    return roots


def build_screen_context(
    cfg: Mapping[str, Any],
    paths: Any,
    store: Any,
    revision: Any,
    *,
    trainer: TargetSizeBoundaryTrainer | None = None,
    inference_evaluator: Callable[..., Any] | None = None,
) -> _ScreenContext:
    """Construct the complete P3 screen context for the current generation."""

    from ._campaign_cli_core import (
        _ensure_local_wrappers,
        _optimizer_policy,
        _cfg,
    )
    from .mace_export import MaceExtxyzPolicy
    from .target_size_execution import (
        TargetSizeExecutionResolver,
        TargetSizeRestartAuthority,
        build_target_size_execution_context,
        build_target_size_screen_schedule,
        initialize_target_size_screen,
        target_size_population_correlation_blocks,
    )

    authorities = build_current_target_size_authorities(cfg, paths, store)
    observed = authorities.identity
    for name, value in observed.items():
        if getattr(revision.state, name) != value:
            raise TargetSizeRuntimeError(
                "The reconstructed current target-size scientific identity no longer "
                f"matches the persisted canonical generation ({name}). Run `prepare` "
                "to start a fresh generation; existing screen evidence is never "
                "reinterpreted under a changed identity."
            )
    aggregate = authorities.aggregate
    definition = aggregate.definition
    schedule = build_target_size_screen_schedule(definition.policy.fidelity_epochs)
    seeds = tuple(definition.policy.optimizer_seeds)
    optimizer_policy = _optimizer_policy(
        cfg,
        seed=int(seeds[0]),
        num_workers=int(_cfg(cfg, "training", "num_workers", 0)),
        paths=paths,
        planned_epochs=int(schedule.n3),
    )
    context = build_target_size_execution_context(
        definition,
        authorities.common,
        schedule,
        seed_neutral_optimizer_policy=optimizer_policy,
    )
    aggregate = aggregate.with_reducer_state(
        context.bind(definition, aggregate.reducer_state)
    )
    root = current_target_size_execution_root(paths, revision.state.generation)
    root.mkdir(parents=True, exist_ok=True)
    window = initialize_target_size_screen(
        root, aggregate, context, authorities.common
    )
    blocks = target_size_population_correlation_blocks(
        aggregate, authorities.split_exclusion
    )
    extxyz_policy = MaceExtxyzPolicy()
    authority = TargetSizeRestartAuthority(
        aggregate=aggregate,
        context=context,
        common=authorities.common,
        schedule=schedule,
        seed_neutral_optimizer_policy=optimizer_policy,
        canonical_frame_authority=authorities.frame_authority,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        frame_array_index=authorities.frame_array_index,
        correlation_blocks=blocks,
        extxyz_policy=extxyz_policy,
        eval2_policy=context.eval2_metric_policy_digest,
        resolver=TargetSizeExecutionResolver(root),
        bulk_roots=_bulk_roots(root),
        # P3 owns this seam: a forward override is admitted only when the
        # caller actually supplied one, so ordinary production still requires a
        # pinned MACE state dict and refuses any reconstruction fallback.
        allow_forward_override=inference_evaluator is not None,
    )
    if trainer is None:
        trainer = MaceTargetSizeBoundaryTrainer(
            wrapper_path=_ensure_local_wrappers(paths)["mdstats-mace-train"]
        )
    return _ScreenContext(
        cfg=cfg,
        paths=paths,
        store=store,
        authorities=authorities,
        aggregate=aggregate,
        schedule=schedule,
        context=context,
        optimizer_policy=optimizer_policy,
        correlation_blocks=blocks,
        extxyz_policy=extxyz_policy,
        root=root,
        window=window,
        authority=authority,
        trainer=trainer,
        inference_evaluator=inference_evaluator,
    )


def _execute_candidate_cell(
    screen: _ScreenContext, *, target_size: int, optimizer_seed: int, boundary: int, state: Any
) -> Any:
    """Run one surviving ``(N, seed)`` cell through the real P3 owners."""

    from dataclasses import replace as _replace

    from .target_size_execution import (
        TargetSizeContinuationRequest,
        bind_target_size_boundary_state,
        build_target_size_candidate_trajectory,
        build_target_size_cell_completion_record,
        build_target_size_eval2_role,
        evaluate_target_size_boundary,
        materialize_target_size_candidate,
        project_target_size_candidate_preparation,
        promote_target_size_boundary_snapshot,
        record_candidate_boundary_outcome,
        resolve_target_size_candidate_for_resume,
        run_target_size_direct_boundary_inference,
        run_target_size_eval2_reduction,
        target_size_rung_plan,
        write_target_size_evaluation_artifact,
    )

    authorities = screen.authorities
    definition = screen.aggregate.definition
    schedule = screen.schedule
    boundary_index = schedule.fidelity_epochs.index(int(boundary))
    materialization_root = screen.authority.bulk_root("materialization")

    if boundary_index == 0:
        optimizer = _replace(screen.optimizer_policy, seed=int(optimizer_seed))
        trajectory = build_target_size_candidate_trajectory(
            definition,
            screen.context,
            authorities.common,
            schedule,
            target_size=int(target_size),
            optimizer_policy=optimizer,
            optimizer_seed=int(optimizer_seed),
        )
        projection = project_target_size_candidate_preparation(
            authorities.common, definition, int(target_size)
        )
        materialization_directory = (
            materialization_root / trajectory.content_digest
        )
        materialization_directory.mkdir(parents=True, exist_ok=True)
        materialization = materialize_target_size_candidate(
            trajectory,
            projection,
            authorities.common,
            canonical_frame_authority=authorities.frame_authority,
            frame_catalog=authorities.frame_catalog,
            frame_data_by_run=authorities.frame_data_by_run,
            output_directory=materialization_directory,
            optimizer_policy=optimizer,
            extxyz_policy=screen.extxyz_policy,
            frame_array_index=authorities.frame_array_index,
        )
        checkpoint_directory = (
            screen.authority.bulk_root("train2")
            / trajectory.content_digest
            / f"boundary_{int(boundary)}"
        )
        checkpoint_directory.mkdir(parents=True, exist_ok=True)
        start_epoch = 0
        predecessor_continuation = None
    else:
        resolved = resolve_target_size_candidate_for_resume(
            screen.root,
            screen.authority,
            boundary_epoch=int(boundary),
            target_size=int(target_size),
            optimizer_seed=int(optimizer_seed),
            state=state,
        )
        trajectory = resolved.trajectory
        optimizer = resolved.optimizer_policy
        materialization = resolved.materialization
        materialization_directory = Path(materialization.output_directory)
        checkpoint_directory = resolved.checkpoint_directory
        start_epoch = int(resolved.start_epoch)
        predecessor_continuation = TargetSizeContinuationRequest(
            trajectory_digest=trajectory.content_digest,
            predecessor_boundary_epoch=int(
                schedule.fidelity_epochs[boundary_index - 1]
            ),
        )

    planned_rung = target_size_rung_plan(
        trajectory, schedule, boundary_epoch=int(boundary)
    )
    summary = screen.trainer(
        TargetSizeRungRequest(
            plan=planned_rung,
            trajectory=trajectory,
            materialization=materialization,
            materialization_directory=materialization_directory,
            checkpoint_directory=checkpoint_directory,
            start_epoch=start_epoch,
            optimizer_policy=optimizer,
        )
    )
    boundary_state = bind_target_size_boundary_state(
        trajectory, schedule, summary, checkpoint_directory=checkpoint_directory
    )
    snapshot = promote_target_size_boundary_snapshot(
        trajectory,
        boundary_state,
        checkpoint_directory=checkpoint_directory,
        snapshot_root=screen.authority.bulk_root("snapshot"),
    )
    evaluation_size = int(definition.policy.evaluation_sizes[boundary_index])
    evaluation_directory = (
        screen.authority.bulk_root("evaluation") / f"boundary_{int(boundary)}"
    )
    evaluation_directory.mkdir(parents=True, exist_ok=True)
    evaluation_artifact = write_target_size_evaluation_artifact(
        evaluation_directory,
        definition=definition,
        evaluation_size=evaluation_size,
        canonical_frame_authority=authorities.frame_authority,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        policy=screen.extxyz_policy,
        frame_array_index=authorities.frame_array_index,
    )
    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=schedule,
        correlation_blocks=screen.correlation_blocks,
        evaluation_data=evaluation_artifact,
    )
    prediction_evidence = run_target_size_direct_boundary_inference(
        trajectory=trajectory,
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=evaluation_artifact,
        canonical_frame_authority=authorities.frame_authority,
        definition=definition,
        context=screen.context,
        common=authorities.common,
        schedule=schedule,
        optimizer_policy=optimizer,
        extxyz_policy=screen.extxyz_policy,
        frame_catalog=authorities.frame_catalog,
        frame_data_by_run=authorities.frame_data_by_run,
        frame_array_index=authorities.frame_array_index,
        materialization_directory=materialization_directory,
        snapshot_root=screen.authority.bulk_root("snapshot"),
        evaluation_directory=evaluation_directory,
        inference_evaluator=screen.inference_evaluator,
    )
    metric_record = run_target_size_eval2_reduction(
        role,
        evaluation_artifact,
        prediction_evidence,
        root_directory=evaluation_directory,
    )
    outcome = evaluate_target_size_boundary(
        role,
        evaluation_artifact,
        prediction_evidence,
        root_directory=evaluation_directory,
    )
    completion_record = build_target_size_cell_completion_record(
        window=screen.window,
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=evaluation_artifact,
        outcome=outcome,
        prediction_evidence=prediction_evidence,
        eval2_metric_record=metric_record,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor_continuation,
        schedule=schedule,
        definition=definition,
        checkpoint_directory=checkpoint_directory,
    )
    record_candidate_boundary_outcome(
        screen.root,
        screen.window,
        trajectory,
        completion_record,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=evaluation_artifact,
        prediction_evidence=prediction_evidence,
        eval2_metric_record=metric_record,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor_continuation,
        restart_authority=screen.authority,
    )
    return completion_record


def execute_current_select_target_size(
    args: Any,
    *,
    trainer: TargetSizeBoundaryTrainer | None = None,
    inference_evaluator: Callable[..., Any] | None = None,
) -> int:
    """Run or resume the complete current paired-seed target-size screen."""

    from ._campaign_cli_core import (
        CampaignStore,
        StageState,
        _load_config,
        _mark_stage,
        _ok,
        _print_header,
    )
    from .campaign_target_size_adoption import (
        adopt_reconciled_execution_head,
        reconcile_and_adopt_target_size_head,
    )
    from .campaign_target_size_cutover import require_current_target_size_runtime
    from .campaign_target_size_state import (
        TargetSizeCampaignState,
        TargetSizeLifecycle,
        TargetSizeRegime,
        TargetSizeTransitionKind,
        commit_target_size_campaign_transition,
        load_target_size_campaign_revision,
    )
    from .campaign_target_size_terminal import (
        commit_terminal_projection,
        load_validated_target_size_terminal_result,
        validate_terminal_projection,
    )
    from .campaign_target_size_view import write_target_size_result_view
    from .target_size_execution import (
        TargetSizeExecutionResolver,
        build_complete_boundary_batch,
        commit_target_size_boundary_batch,
        derive_active_boundary_requirements,
    )

    cfg, paths = _load_config(args.config)
    store = CampaignStore(paths.state_db)
    revision = require_current_target_size_runtime(store)
    if revision.state.lifecycle in (
        TargetSizeLifecycle.TERMINAL_SELECTED,
        TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
    ):
        validated = load_validated_target_size_terminal_result(
            cfg, paths, store, revision=revision
        )
        resolver = TargetSizeExecutionResolver(
            current_target_size_execution_root(paths, revision.state.generation)
        )
        write_target_size_result_view(
            paths.results / "target-size-state.json",
            revision,
            resolver=resolver,
            definition=validated.authorities.aggregate.definition,
        )
        _report_terminal_state(validated)
        return 0

    _print_header("Target-size selection - controlled configurable fidelity")
    print(
        "Epoch is a controlled variable during this operation: only the exact "
        "configured screen boundary checkpoints contribute to ranking.",
        flush=True,
    )
    screen = build_screen_context(
        cfg,
        paths,
        store,
        revision,
        trainer=trainer,
        inference_evaluator=inference_evaluator,
    )
    _mark_stage(
        store,
        paths,
        "target_size_selection",
        StageState.RUNNING,
        f"screening canonical generation {revision.state.generation}",
    )
    state = screen.aggregate.reducer_state
    try:
        revision = commit_target_size_campaign_transition(
            store,
            kind=TargetSizeTransitionKind.OPEN_ATTEMPT,
            expected=revision.expectation(),
            successor=TargetSizeCampaignState(
                regime=TargetSizeRegime.CURRENT,
                generation=revision.state.generation,
                lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
                attempt=screen.window.content_digest,
                frame_authority_digest=revision.state.frame_authority_digest,
                neutral_statistical_base_digest=(
                    revision.state.neutral_statistical_base_digest
                ),
                split_exclusion_digest=revision.state.split_exclusion_digest,
                policy_digest=revision.state.policy_digest,
                experiment_definition_digest=(
                    revision.state.experiment_definition_digest
                ),
                aggregate_digest=revision.state.aggregate_digest,
                execution_context_digest=screen.context.content_digest,
                common_preparation_digest=screen.authorities.common.content_digest,
                screen_window_digest=screen.window.content_digest,
                execution_root=current_target_size_execution_root_locator(
                    paths, revision.state.generation
                ),
                adopted_execution_head_digest=(
                    revision.state.adopted_execution_head_digest
                ),
                adopted_reducer_state_digest=(
                    revision.state.adopted_reducer_state_digest
                ),
            ),
        ).revision

        # Always reconcile the existing root before scheduling anything new.
        revision, head = reconcile_and_adopt_target_size_head(
            store, revision, root=screen.root, authority=screen.authority
        )
        if head is not None:
            state = head.post_state
            _ok(
                "reconciled existing screen evidence: head="
                f"{head.content_digest[:12]}...; status={state.status.value}"
            )

        while not state.is_terminal:
            requirements = derive_active_boundary_requirements(
                screen.aggregate.definition, state
            )
            if requirements is None:
                break
            boundary, _evaluation_size, keys = requirements
            print(
                f"Boundary {boundary}: executing {len(keys)} surviving "
                f"(N, optimizer seed) cells.",
                flush=True,
            )
            completion_records = []
            for size, seed in keys:
                completion_records.append(
                    _execute_candidate_cell(
                        screen,
                        target_size=int(size),
                        optimizer_seed=int(seed),
                        boundary=int(boundary),
                        state=state,
                    )
                )
            batch = build_complete_boundary_batch(
                screen.aggregate.definition, state, completion_records
            )
            head = commit_target_size_boundary_batch(
                screen.root, screen.aggregate.definition, state, batch
            )
            revision = adopt_reconciled_execution_head(store, revision, head)
            state = head.post_state
            _ok(
                f"boundary {boundary} committed: head={head.content_digest[:12]}...; "
                f"status={state.status.value}"
            )

        if state.is_terminal and head is not None:
            # The terminal head, its reducer digest, and the derived selection
            # are one claim, committed together.
            revision = commit_terminal_projection(
                store, revision, head, definition=screen.aggregate.definition
            )
            # Nothing is reported before the persisted projection has been
            # re-derived from authenticated P2/P3 state.
            validate_terminal_projection(
                revision,
                resolver=screen.authority.resolver,
                definition=screen.aggregate.definition,
            )
    except Exception as exc:
        _mark_stage(
            store, paths, "target_size_selection", StageState.FAILED, str(exc)
        )
        raise

    write_target_size_result_view(
        paths.results / "target-size-state.json",
        revision,
        resolver=screen.authority.resolver,
        definition=screen.aggregate.definition,
    )
    _mark_stage(
        store,
        paths,
        "target_size_selection",
        StageState.COMPLETE if state.is_terminal else StageState.WAITING,
        f"reducer status {state.status.value}",
    )
    revision = load_target_size_campaign_revision(store)
    if revision.state.terminal is not None:
        _report_terminal_state(revision.state.terminal)
    else:
        print(
            f"Target-size screen is operationally resumable: reducer status "
            f"{state.status.value}. Re-run `select-target-size` to continue.",
            flush=True,
        )
    return 0


def _report_terminal_state(terminal_or_validated: Any) -> None:
    from .campaign_target_size_terminal import (
        TargetSizeTerminalProjection,
        TargetSizeTerminalProjectionError,
        ValidatedTargetSizeTerminalResult,
    )

    if isinstance(terminal_or_validated, ValidatedTargetSizeTerminalResult):
        terminal = terminal_or_validated.projection
    elif isinstance(terminal_or_validated, TargetSizeTerminalProjection):
        terminal = terminal_or_validated
    else:
        raise TargetSizeTerminalProjectionError(
            "Terminal state reporting requires a validated terminal result or projection, "
            f"not {type(terminal_or_validated).__name__}."
        )
    if terminal.is_selection:
        print(
            f"Target size is already selected and frozen: N={terminal.selected_target_size}.",
            flush=True,
        )
    else:
        print(
            "Target-size selection is scientifically terminal: "
            f"{terminal.reducer_status}; "
            f"{', '.join(terminal.terminal_reason_codes) or 'no further candidates'}.",
            flush=True,
        )


__all__ = [
    "CurrentTargetSizeAuthorities",
    "TARGET_SIZE_EXECUTION_ROOT_NAME",
    "TargetSizeRuntimeError",
    "MaceTargetSizeBoundaryTrainer",
    "TargetSizeBoundaryTrainer",
    "TargetSizeRungRequest",
    "build_current_target_size_authorities",
    "build_screen_context",
    "execute_current_prepare",
    "execute_current_select_target_size",
    "mace_run_configuration",
    "resolve_neutral_partition_policy",
    "current_target_size_execution_root",
    "current_target_size_execution_root_locator",
]
