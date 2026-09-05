"""P3-E gate evidence: complete-boundary coordinator, exactly-once commits,
crash-consistent restart reconciliation, P2 reducer sole decision authority."""

from __future__ import annotations

import inspect
import json
import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
from mdstats.training_data.neutral_substrate import build_neutral_split_exclusion_evidence
from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TARGET_SIZE_CELL_COMPLETION_RECORD_SCHEMA,
    TargetSizeCandidateOutcome,
    TargetSizeCellCompletionRecord,
    TargetSizeCompleteBoundaryBatch,
    TargetSizeExecutionHead,
    TargetSizeExecutionResolver,
    TargetSizeRestartAuthority,
    TargetSizeContinuationRequest,
    apply_complete_boundary_batch,
    bind_target_size_boundary_state,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_cell_completion_record,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    collect_boundary_candidate_outcomes,
    collect_boundary_cell_completion_records,
    commit_target_size_boundary_batch,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initialize_target_size_screen,
    initial_target_size_continuation_request,
    load_current_execution_head,
    materialize_target_size_candidate,
    persist_complete_boundary_batch,
    promote_target_size_boundary_snapshot,
    reconcile_target_size_screen_root,
    record_candidate_boundary_outcome,
    run_target_size_direct_boundary_inference,
    run_target_size_eval2_reduction,
    target_size_population_correlation_blocks,
    target_size_rung_plan,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution import coordinator as coordinator_module
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_experiment import ReducerStatus


def _env(tmp_path: Path, *, root_name: str = "screen", batch_size: int = 4):
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, fdr, _ = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule((1, 3, 10))
    optimizer = MaceOptimizerPolicy(
        max_num_epochs=schedule.n3, batch_size=batch_size, device="cpu"
    )
    context = build_target_size_execution_context(
        aggregate.definition, common, schedule, seed_neutral_optimizer_policy=optimizer
    )
    aggregate = aggregate.with_reducer_state(
        context.bind(aggregate.definition, aggregate.reducer_state)
    )
    evidence = build_neutral_split_exclusion_evidence(fa, nb)
    blocks = target_size_population_correlation_blocks(aggregate, evidence)
    root = tmp_path / root_name
    root.mkdir(parents=True, exist_ok=True)
    window = initialize_target_size_screen(root, aggregate, context, common)
    authority = TargetSizeRestartAuthority(
        aggregate=aggregate,
        context=context,
        common=common,
        schedule=schedule,
        seed_neutral_optimizer_policy=optimizer,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=fdr,
        frame_array_index=index,
        correlation_blocks=blocks,
        extxyz_policy=MaceExtxyzPolicy(),
        eval2_policy=context.eval2_metric_policy_digest,
        resolver=TargetSizeExecutionResolver(root),
        bulk_roots={
            "materialization": tmp_path,
            "snapshot": root,
            "evaluation": tmp_path,
            "train2": root,
        },
        allow_forward_override=True,
    )
    return {
        "manifest": manifest,
        "frame_authority": fa,
        "aggregate": aggregate,
        "common": common,
        "index": index,
        "frames": frames,
        "frame_data_by_run": fdr,
        "schedule": schedule,
        "context": context,
        "optimizer": optimizer,
        "blocks": blocks,
        "root": root,
        "window": window,
        "authority": authority,
    }


def _epsilon(size: int, seed: int) -> float:
    return (2.5e-3 * size) + (1.0e-4 * seed)


def _seeded(optimizer, seed: int):
    return replace(optimizer, seed=seed)


def _durable_train2_failure_record(tmp_path: Path, trajectory, schedule, boundary: int):
    """Bind a real raw checkpoint byte digest into a failure test record."""
    checkpoint_directory = tmp_path / (
        f"failure-checkpoint-{trajectory.target_size}-"
        f"{trajectory.optimizer_seed}-{boundary}"
    )
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    raw = p3c._raw_checkpoint(checkpoint_directory, 0)
    record = p3c._failure_record(
        trajectory,
        schedule,
        boundary,
        code="train_nonfinite_model_state",
        failed_epoch=0,
    )
    return replace(
        record,
        raw_checkpoint_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),
    ), checkpoint_directory


def _rung_provenance(env, trajectory, boundary: int):
    planned_rung = target_size_rung_plan(
        trajectory, env["schedule"], boundary_epoch=boundary
    )
    if boundary == env["schedule"].n1:
        predecessor = None
    else:
        previous = env["schedule"].fidelity_epochs[
            env["schedule"].fidelity_epochs.index(boundary) - 1
        ]
        predecessor = TargetSizeContinuationRequest(
            trajectory_digest=trajectory.content_digest,
            predecessor_boundary_epoch=previous,
        )
    return planned_rung, predecessor


def p3c_test_boundary_state(env, tmp_path, trajectory, boundary, *, name):
    checkpoint_dir = tmp_path / name
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    plan = target_size_rung_plan(trajectory, env["schedule"], boundary_epoch=boundary)
    _runtime, summary, _restored, _rng = p3c._run_rung(
        plan,
        checkpoint_dir,
        start_epoch=0,
        updates_per_epoch=trajectory.realization.updates_per_epoch,
        seed=1,
    )
    return bind_target_size_boundary_state(
        trajectory, env["schedule"], summary, checkpoint_directory=checkpoint_dir
    )


def _execute_candidate_boundary(env, tmp_path: Path, size: int, seed: int, boundary: int):
    """Run one candidate boundary through real TRAIN2 + real EVAL2 owners."""
    definition = env["aggregate"].definition
    trajectory = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=size,
        optimizer_policy=env["optimizer"] if seed == 1 else _seeded(env["optimizer"], seed),
        optimizer_seed=seed,
    )
    projection = project_target_size_candidate_preparation(
        env["common"], definition, size
    )
    mat_dir = tmp_path / f"mat-{size}-{seed}"
    mat_dir.mkdir(parents=True, exist_ok=True)
    materialization = materialize_target_size_candidate(
        trajectory,
        projection,
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=mat_dir,
        optimizer_policy=trajectory.realization.optimizer_policy if hasattr(trajectory.realization, "optimizer_policy") else env["optimizer"],
        extxyz_policy=env["authority"].extxyz_policy,
        frame_array_index=env["index"],
    )

    name = f"ckpt-{size}-{seed}-{boundary}"
    boundary_state = p3c_test_boundary_state(env, tmp_path, trajectory, boundary, name=name)
    snapshot = promote_target_size_boundary_snapshot(
        trajectory,
        boundary_state,
        checkpoint_directory=tmp_path / name,
        snapshot_root=env["root"],
    )

    boundary_index = env["schedule"].fidelity_epochs.index(boundary)
    evaluation_size = definition.policy.evaluation_sizes[boundary_index]
    eval_dir = tmp_path / f"eval_art_{boundary}"
    eval_dir.mkdir(parents=True, exist_ok=True)
    eval_artifact = write_target_size_evaluation_artifact(
        eval_dir,
        definition=definition,
        evaluation_size=evaluation_size,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )

    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=env["blocks"],
        evaluation_data=eval_artifact,
    )

    view = eval_artifact.build_evaluation_view(eval_dir)
    evaluator = p3d._predictions_evaluator(view, epsilon=_epsilon(size, seed))
    opt_policy = (
        trajectory.realization.optimizer_policy
        if hasattr(trajectory.realization, "optimizer_policy")
        else (env["optimizer"] if seed == 1 else _seeded(env["optimizer"], seed))
    )
    pred_evidence = run_target_size_direct_boundary_inference(
        trajectory=trajectory,
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=opt_policy,
        extxyz_policy=env["authority"].extxyz_policy,
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
        materialization_directory=mat_dir,
        snapshot_root=env["root"],
        evaluation_directory=eval_dir,
        inference_evaluator=evaluator,
    )

    metric_record = run_target_size_eval2_reduction(
        role, eval_artifact, pred_evidence, root_directory=eval_dir
    )
    outcome = evaluate_target_size_boundary(
        role, eval_artifact, pred_evidence, root_directory=eval_dir
    )
    planned_rung, predecessor = _rung_provenance(env, trajectory, boundary)

    completion_record = build_target_size_cell_completion_record(
        window=env["window"],
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        outcome=outcome,
        prediction_evidence=pred_evidence,
        eval2_metric_record=metric_record,
        planned_rung=planned_rung,
        schedule=env["schedule"],
        predecessor_continuation=predecessor,
    )

    return (
        trajectory,
        role,
        snapshot,
        completion_record,
        materialization,
        eval_artifact,
        pred_evidence,
        metric_record,
    )


def _run_boundary_matrix(env, tmp_path: Path, state, *, skip: list | None = None):
    """Execute one complete active matrix, record outcomes, build batch."""
    definition = env["aggregate"].definition
    requirements = derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    boundary, evaluation_size, keys = requirements
    completion_records = []
    for index, (size, seed) in enumerate(keys):
        if skip and index in skip:
            continue
        (
            trajectory,
            role,
            snapshot,
            completion_record,
            materialization,
            eval_artifact,
            pred_evidence,
            metric_record,
        ) = _execute_candidate_boundary(env, tmp_path, size, seed, boundary)
        assert completion_record.boundary_epoch == boundary
        assert completion_record.outcome.evaluation_membership_digest == (
            definition.evaluation_order.membership_digest(evaluation_size)
        )
        completion_records.append(completion_record)
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion_record,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
            planned_rung=_rung_provenance(env, trajectory, completion_record.boundary_epoch)[0],
            predecessor_continuation=_rung_provenance(env, trajectory, completion_record.boundary_epoch)[1],
            restart_authority=env["authority"],
        )
    return boundary, evaluation_size, keys, completion_records


def _full_matrix(env, tmp_path, state):
    boundary, evaluation_size, keys, completion_records = _run_boundary_matrix(env, tmp_path, state)
    assert len(completion_records) == len(keys)
    definition = env["aggregate"].definition
    batch = build_complete_boundary_batch(definition, state, completion_records)
    head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
    return batch, head


def test_p3e_coordinator_source_has_no_ranking_authority() -> None:
    import ast

    source = inspect.getsource(coordinator_module)
    tree = ast.parse(source)
    identifiers = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
    } | {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
    }
    forbidden_identifiers = {
        "practical_equivalence",
        "equivalence_margin",
        "survivor",
        "finalist",
        "best_score",
        "selected_target_size",
        "selected_membership_digest",
    }
    assert not (identifiers & forbidden_identifiers)
    # No numeric averaging/ranking semantics enter coordinator code.
    forbidden_calls = {"mean", "argmin", "argmax", "sort_scores"}
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Name, ast.Attribute))
    ]
    call_names = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in calls
    }
    assert not (call_names & forbidden_calls)
    # Exactly one transition call site exists; it is the real P2 owner.
    advance_calls = [
        node for node in calls
        if (node.func.id if isinstance(node.func, ast.Name) else node.func.attr)
        == "advance_target_size_reducer"
    ]
    assert len(advance_calls) == 1
    # The frozen P2 reducer is the only selection surface: coordinator never
    # constructs TargetSizeReducerState itself (states pass through only).
    assert "TargetSizeReducerState(" not in source


def test_p3e_exact_matrix_ordering_and_negative_shapes(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, completion_records = _run_boundary_matrix(env, tmp_path, state)
    assert len(keys) == len(definition.policy.optimizer_seeds) * len(state.active_candidate_sizes)
    assert list(keys) == sorted(keys)  # exact P2 size-major/seed-minor order
    batch = build_complete_boundary_batch(definition, state, completion_records)
    assert batch.boundary_epoch == boundary
    assert batch.evaluation_membership_digest == (
        definition.evaluation_order.membership_digest(evaluation_size)
    )
    assert tuple(batch.active_candidate_sizes) == tuple(state.active_candidate_sizes)
    # Reordered (even perfectly keyed) matrices are rejected.
    shuffled = tuple(reversed(list(completion_records)))
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, shuffled)
    # Missing one candidate completion record.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, completion_records[:-1])
    # Duplicated candidate completion record.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(
            definition, state, tuple(completion_records) + (completion_records[-1],)
        )
    # Foreign seed substitution.
    foreign_rec = replace(
        completion_records[-1],
        optimizer_seed=999,
        outcome=replace(completion_records[-1].outcome, optimizer_seed=999),
        outcome_digest=replace(completion_records[-1].outcome, optimizer_seed=999).content_digest,
    )
    foreign = tuple(completion_records[:-1]) + (foreign_rec,)
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, foreign)


def test_p3e_partial_outcomes_never_advance_reducer(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, completion_records = _run_boundary_matrix(
        env, tmp_path, state, skip=[1]
    )
    assert len(completion_records) == len(keys) - 1
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, completion_records)
    collected = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(collected) == len(completion_records)
    # The reducer state remains exactly the pre-boundary state; no head exists.
    assert load_current_execution_head(env["root"]) is None
    assert state.completed_boundary_epochs == ()


def test_p3e_publication_requires_complete_parent_graph_before_progress(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    state = env["aggregate"].reducer_state
    requirements = derive_active_boundary_requirements(
        env["aggregate"].definition, state
    )
    assert requirements is not None
    boundary, _evaluation_size, keys = requirements
    (
        trajectory,
        role,
        snapshot,
        completion_record,
        materialization,
        eval_artifact,
        pred_evidence,
        metric_record,
    ) = _execute_candidate_boundary(env, tmp_path, keys[0][0], keys[0][1], boundary)
    resolver = env["authority"].resolver
    completion_path = resolver.completion_path(
        boundary, completion_record.content_digest
    )
    progress_path = resolver.progress_path(
        env["window"].content_digest,
        boundary,
        completion_record.target_size,
        completion_record.optimizer_seed,
    )
    assert not resolver.materialization_path(
        materialization.content_digest
    ).exists()

    # The completion is valid in memory, but its mandatory metadata parents
    # have not yet been published into this screen root.  Omitted arguments
    # must resolve through the typed resolver and fail before publication.
    with pytest.raises(mdstats.TrainingDataInputError):
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion_record,
            restart_authority=env["authority"],
        )
    assert not completion_path.exists()
    assert not progress_path.exists()

    planned_rung, predecessor = _rung_provenance(
        env, trajectory, completion_record.boundary_epoch
    )
    first = record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion_record,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=pred_evidence,
        eval2_metric_record=metric_record,
        planned_rung=planned_rung,
        predecessor_continuation=predecessor,
        restart_authority=env["authority"],
    )
    retry = record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion_record,
        restart_authority=env["authority"],
    )
    assert retry == first
    assert completion_path.is_file()
    assert progress_path.is_file()

    # Removing a mandatory parent turns the same omitted-parent retry into a
    # typed failure; an existing valid completion is never silently replaced.
    resolver.evaluation_artifact_path(eval_artifact.content_digest).unlink()
    with pytest.raises(mdstats.TrainingDataInputError):
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory,
            completion_record,
            restart_authority=env["authority"],
        )
    assert completion_path.is_file()
    assert progress_path.is_file()


def test_p3e_execution_errors_leave_reducer_unchanged(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    requirements = derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    boundary, evaluation_size, keys = requirements

    def _boom():
        raise OSError("simulated resource exhaustion")

    exec_failed: list[str] = []
    completion_records: list = []
    for index, (size, seed) in enumerate(keys):
        try:
            if index == 1:
                _boom()
            (
                trajectory,
                role,
                snapshot,
                completion_record,
                materialization,
                eval_artifact,
                pred_evidence,
                metric_record,
            ) = _execute_candidate_boundary(
                env, tmp_path, size, seed, boundary
            )
            record_candidate_boundary_outcome(
                env["root"],
                env["window"],
                trajectory,
                completion_record,
                materialization=materialization,
                boundary_snapshot=snapshot,
                eval2_role=role,
                evaluation_data=eval_artifact,
                prediction_evidence=pred_evidence,
                eval2_metric_record=metric_record,
                planned_rung=_rung_provenance(env, trajectory, completion_record.boundary_epoch)[0],
                predecessor_continuation=_rung_provenance(env, trajectory, completion_record.boundary_epoch)[1],
                restart_authority=env["authority"],
            )
            completion_records.append(completion_record)
        except OSError:
            exec_failed.append(f"{size}:{seed}")
    assert exec_failed == [f"{keys[1][0]}:{keys[1][1]}"]
    # Partial matrix: no batch, no reducer advance.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(
            definition,
            state,
            collect_boundary_cell_completion_records(
                env["root"], env["window"], boundary_epoch=boundary
            ),
        )
    assert load_current_execution_head(env["root"]) is None
    # Retrying the failed work completes the same boundary without duplicates.
    size, seed = keys[1]
    (
        trajectory,
        role,
        snapshot,
        completion_record,
        materialization,
        eval_artifact,
        pred_evidence,
        metric_record,
    ) = _execute_candidate_boundary(
        env, tmp_path, size, seed, boundary
    )
    record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        completion_record,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=pred_evidence,
        eval2_metric_record=metric_record,
        planned_rung=_rung_provenance(env, trajectory, completion_record.boundary_epoch)[0],
        predecessor_continuation=_rung_provenance(env, trajectory, completion_record.boundary_epoch)[1],
        restart_authority=env["authority"],
    )
    recover_records = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(recover_records) == len(keys)
    batch = build_complete_boundary_batch(definition, state, recover_records)
    head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
    validate_reconciled = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert validate_reconciled.content_digest == head.content_digest


def test_p3e_outcome_publication_idempotent_and_conflicts_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, completion_records = _run_boundary_matrix(env, tmp_path, state)
    trajectory = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=keys[0][0],
        optimizer_policy=env["optimizer"],
        optimizer_seed=keys[0][1],
    )
    # Re-recording the identical completion record is a no-op.
    record_candidate_boundary_outcome(
        env["root"], env["window"], trajectory, completion_records[0],
        restart_authority=env["authority"],
    )
    collected = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(collected) == len(completion_records)
    # A conflicting completion record for the same candidate is rejected.
    forged_outcome = mdstats.TargetSizeBoundaryMetric(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=state.execution_context_digest,
        target_size=keys[0][0],
        optimizer_seed=keys[0][1],
        boundary_epoch=boundary,
        evaluation_membership_digest=completion_records[0].outcome.evaluation_membership_digest,
        target_force_rmse_mev_per_a=123.0,
    )
    forged = replace(
        completion_records[0],
        outcome=forged_outcome,
        outcome_digest=forged_outcome.content_digest,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        record_candidate_boundary_outcome(
            env["root"], env["window"], trajectory, forged,
            restart_authority=env["authority"],
        )


def test_p3e_full_lifecycle_elimination_and_terminal_selection(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    sizes_before = tuple(state.active_candidate_sizes)
    assert len(sizes_before) >= 2

    # Boundary 0.
    batch0, head0 = _full_matrix(env, tmp_path, state)
    state1 = head0.post_state
    if not state1.is_terminal:
        assert state1.status is ReducerStatus.AWAITING_SECOND_BOUNDARY
        active1 = set(state1.active_candidate_sizes)
        assert active1 <= set(sizes_before)
        eliminated = set(sizes_before) - active1
        requirements1 = derive_active_boundary_requirements(definition, state1)
        assert requirements1 is not None
        keys1 = requirements1[2]
        assert {size for size, _seed in keys1} == active1
        assert not (eliminated & {size for size, _seed in keys1})

        batch1, head1 = _full_matrix(env, tmp_path, state1)
        state2 = head1.post_state
        if not state2.is_terminal:
            assert state2.status is ReducerStatus.AWAITING_TERMINAL_BOUNDARY
            assert len(state2.active_candidate_sizes) == 2
            batch2, head2 = _full_matrix(env, tmp_path, state2)
            final = head2.post_state
        else:
            final = state2
    else:
        final = state1
    assert final.is_terminal
    if final.status is ReducerStatus.SELECTED:
        assert final.selected_target_size is not None
        assert final.selected_membership_digest == (
            definition.training_order.candidate_digest(final.selected_target_size)
        )
    assert derive_active_boundary_requirements(definition, final) is None
    head = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert head.post_state.content_digest == final.content_digest
    mdstats.validate_target_size_reducer_state(definition, head.post_state)


def test_p3e_stale_context_preparation_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    _full_matrix(env, tmp_path, state)
    from dataclasses import replace as _replace

    different_context = build_target_size_execution_context(
        definition,
        env["common"],
        env["schedule"],
        seed_neutral_optimizer_policy=_replace(env["optimizer"], learning_rate=2e-4),
    )
    with pytest.raises(TypeError):
        reconcile_target_size_screen_root(
            env["root"],
            env["aggregate"],
            different_context,
            env["common"],
            schedule=env["schedule"],
        )
    with pytest.raises(mdstats.TrainingDataInputError):
        initialize_target_size_screen(
            env["root"], env["aggregate"], different_context, env["common"]
        )


def test_p3e_worker_concurrency_and_no_reducer_access(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, completion_records = _run_boundary_matrix(env, tmp_path, state)
    import shutil

    progress_dir = env["root"] / "progress" / str(boundary)
    if progress_dir.is_dir():
        shutil.rmtree(progress_dir)

    trajectories = {
        (size, seed): build_target_size_candidate_trajectory(
            definition,
            env["context"],
            env["common"],
            env["schedule"],
            target_size=size,
            optimizer_policy=_seeded(env["optimizer"], seed),
            optimizer_seed=seed,
        )
        for size, seed in keys
    }
    by_key = {(r.target_size, r.optimizer_seed): r for r in completion_records}

    def _worker(key):
        record_candidate_boundary_outcome(
            env["root"], env["window"], trajectories[key], by_key[key],
            restart_authority=env["authority"],
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_worker, list(keys) * 2 + list(reversed(keys))))
    collected = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(collected) == len(keys)
    assert tuple((r.target_size, r.optimizer_seed) for r in collected) == keys
    assert load_current_execution_head(env["root"]) is None
    batch = build_complete_boundary_batch(definition, state, collected)
    head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
    assert head.post_state.content_digest != state.content_digest


def test_p3e_crash_repair_convergence_all_positions(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    requirements = derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    boundary, evaluation_size, keys = requirements

    # (a) After candidate TRAIN2 persistence, before any outcome: safe.
    (
        trajectory,
        role,
        snapshot,
        rec_one,
        mat_one,
        eval_one,
        pred_one,
        metric_one,
    ) = _execute_candidate_boundary(
        env, tmp_path, keys[0][0], keys[0][1], boundary
    )
    head = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert head is None

    # (b) After only some boundary outcomes exist: still pre-state.
    record_candidate_boundary_outcome(
        env["root"],
        env["window"],
        trajectory,
        rec_one,
        materialization=mat_one,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_one,
        prediction_evidence=pred_one,
        eval2_metric_record=metric_one,
        planned_rung=_rung_provenance(env, trajectory, rec_one.boundary_epoch)[0],
        predecessor_continuation=_rung_provenance(env, trajectory, rec_one.boundary_epoch)[1],
        restart_authority=env["authority"],
    )
    assert load_current_execution_head(env["root"]) is None
    partial = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(partial) == 1
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, partial)

    # (c) Finish the matrix; persist the batch but do not commit (crash point).
    completion_records = [rec_one]
    for size, seed in keys[1:]:
        (
            trajectory2,
            role2,
            snapshot2,
            rec2,
            mat2,
            eval2,
            pred2,
            metric2,
        ) = _execute_candidate_boundary(
            env, tmp_path, size, seed, boundary
        )
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            trajectory2,
            rec2,
            materialization=mat2,
            boundary_snapshot=snapshot2,
            eval2_role=role2,
            evaluation_data=eval2,
            prediction_evidence=pred2,
            eval2_metric_record=metric2,
            planned_rung=_rung_provenance(env, trajectory2, rec2.boundary_epoch)[0],
            predecessor_continuation=_rung_provenance(env, trajectory2, rec2.boundary_epoch)[1],
            restart_authority=env["authority"],
        )
        completion_records.append(rec2)
    completion_records = tuple(
        collect_boundary_cell_completion_records(
            env["root"], env["window"], boundary_epoch=boundary
        )
    )
    batch = build_complete_boundary_batch(definition, state, completion_records)
    persist_complete_boundary_batch(env["root"], batch)
    repaired = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert repaired is not None
    direct_state = apply_complete_boundary_batch(definition, state, batch)
    assert repaired.post_state.content_digest == direct_state.content_digest
    assert repaired.batch_digest == batch.content_digest

    # (d) Simulate loss of only the current-head pointer (post-batch, post-head).
    current_path = env["root"] / "current_head.json"
    current_path.unlink()
    orphaned = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert orphaned.content_digest == repaired.content_digest
    assert load_current_execution_head(env["root"]).content_digest == repaired.content_digest

    # (e) Already committed state is validated, never reapplied.
    again = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert again.content_digest == repaired.content_digest
    final_state = load_current_execution_head(env["root"]).post_state
    mdstats.validate_target_size_reducer_state(definition, final_state)
    assert final_state.completed_boundary_epochs == (boundary,)


def test_p3e_execution_only_invariance_no_cv_or_prod_drift(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    batch, head = _full_matrix(env, tmp_path, state)
    same_schedule = build_target_size_screen_schedule((1, 3, 10), production_horizon_epochs=41)
    assert same_schedule.content_digest == env["schedule"].content_digest
    forbidden = (
        "cv_fold",
        "fold_index",
        "label_domain",
        "coarse_fallback",
        "development_complement",
        "excluded_prefix",
        "production_horizon",
        "num_workers",
        "harness_validation",
    )
    for payload in (
        env["window"].to_dict(),
        batch.to_dict(),
        head.to_dict(),
    ):
        text = json.dumps(payload)
        for token in forbidden:
            assert token not in text


def test_p3e_head_ancestry_chain_and_negative_validations(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state

    # Boundary 0 -> Genesis head (parent_head_digest is None)
    batch0, head0 = _full_matrix(env, tmp_path, state)
    assert head0.parent_head_digest is None

    # Boundary 1 -> Child head links parent_head_digest to head0
    batch1, head1 = _full_matrix(env, tmp_path, head0.post_state)
    assert head1.parent_head_digest == head0.content_digest

    # Corrupting parent pointer fails closed during reconciliation
    forged_head = replace(head1, parent_head_digest="0" * 64)
    forged_path = env["root"] / "heads" / f"{forged_head.content_digest}.json"
    forged_path.write_text(json.dumps(forged_head.to_dict()))
    (env["root"] / "current_head.json").write_text(json.dumps(forged_head.to_dict()))

    with pytest.raises(mdstats.TrainingDataInputError):
        reconcile_target_size_screen_root(
            env["root"], env["authority"]
        )

    # Restore valid current head
    (env["root"] / "current_head.json").write_text(json.dumps(head1.to_dict()))
    forged_path.unlink()
    reconciled = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert reconciled.content_digest == head1.content_digest


def test_p3e_review3_discriminated_cell_completion_record_variants(
    tmp_path: Path,
) -> None:
    from mdstats.training_data.eval2 import Eval2NumericalEvaluationError
    from mdstats.training_data.train2_runtime import Train2NumericalFailureRecord
    from mdstats.training_data.target_size_execution import (
        TargetSizeExecutionResolver,
    )
    from mdstats.training_data.target_size_experiment import (
        NumericalFailureKind,
        TargetSizeBoundaryMetric,
        TargetSizeNumericalFailure,
    )

    env = _env(tmp_path)
    definition = env["aggregate"].definition
    size0 = definition.qualified_candidate_sizes[0]
    seed0 = definition.policy.optimizer_seeds[0]
    state = env["aggregate"].reducer_state
    window = env["window"]
    (
        trajectory,
        role,
        snapshot,
        comp_success,
        materialization,
        eval_artifact,
        pred_evidence,
        metric_record,
    ) = _execute_candidate_boundary(env, tmp_path, size0, seed0, 1)

    # 1. Success completion record variant
    assert comp_success.kind == "success"
    assert isinstance(comp_success.outcome, TargetSizeBoundaryMetric)
    assert comp_success.boundary_snapshot_digest is not None
    assert comp_success.eval2_role_digest is not None
    assert comp_success.evaluation_data_digest is not None
    assert comp_success.eval2_metric_record_digest is not None
    assert comp_success.prediction_evidence_digest is not None

    # Success variant cannot be built without mandatory evaluation evidence
    with pytest.raises(mdstats.TrainingDataInputError):
        build_target_size_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=pred_evidence,
            eval2_metric_record=None,
        )

    # 2. TRAIN2 failure completion record variant
    train_fail_rec, failure_checkpoint_directory = _durable_train2_failure_record(
        tmp_path, trajectory, env["schedule"], 1
    )
    from mdstats.training_data.target_size_execution import translate_target_size_train2_failure

    train_fail_outcome = translate_target_size_train2_failure(
        train_fail_rec,
        trajectory=trajectory,
        definition=definition,
        schedule=env["schedule"],
        scheduled_boundary_epoch=1,
    )
    comp_train_fail = build_target_size_cell_completion_record(
        window=window,
        trajectory=trajectory,
        materialization=materialization,
        failure_record=train_fail_rec,
        outcome=train_fail_outcome,
        planned_rung=target_size_rung_plan(
            trajectory, env["schedule"], boundary_epoch=1
        ),
        schedule=env["schedule"],
        definition=definition,
        predecessor_continuation=initial_target_size_continuation_request(trajectory),
        checkpoint_directory=failure_checkpoint_directory,
        kind="train2_failure",
    )
    assert comp_train_fail.kind == "train2_failure"
    assert isinstance(comp_train_fail.outcome, TargetSizeNumericalFailure)
    assert (
        comp_train_fail.outcome.kind
        is NumericalFailureKind.TRAIN_NONFINITE_MODEL_STATE
    )
    assert comp_train_fail.boundary_snapshot_digest is None
    assert comp_train_fail.eval2_role_digest is None
    assert comp_train_fail.evaluation_data_digest is None

    # TRAIN2 failure variant rejects binding snapshot/eval2 digests
    with pytest.raises(mdstats.TrainingDataInputError):
        replace(
            comp_train_fail,
            boundary_snapshot_digest=snapshot.content_digest,
        )

    # 3. EVAL2 failure completion record variant
    eval_fail_err = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "NaN force predicted",
        target_role_digest=role.content_digest,
        prediction_digest=pred_evidence.prediction_payload_digest,
    )
    comp_eval_fail = build_target_size_cell_completion_record(
        window=window,
        trajectory=trajectory,
        materialization=materialization,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=pred_evidence,
        failure_record=eval_fail_err,
        planned_rung=target_size_rung_plan(
            trajectory, env["schedule"], boundary_epoch=snapshot.boundary_epoch
        ),
        schedule=env["schedule"],
        kind="eval2_failure",
    )
    assert comp_eval_fail.kind == "eval2_failure"
    assert isinstance(comp_eval_fail.outcome, TargetSizeNumericalFailure)
    assert (
        comp_eval_fail.outcome.kind
        is NumericalFailureKind.EVAL_NONFINITE_PREDICTION
    )
    assert comp_eval_fail.boundary_snapshot_digest == snapshot.content_digest
    assert comp_eval_fail.eval2_role_digest == role.content_digest


def test_p3e_review3_resolver_graph_persistence_and_replay(
    tmp_path: Path,
) -> None:
    from mdstats.training_data.target_size_execution import (
        TargetSizeExecutionResolver,
    )

    env = _env(tmp_path)
    resolver = TargetSizeExecutionResolver(env["root"])
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state

    # Run full matrix and commit batch
    batch0, head0 = _full_matrix(env, tmp_path, state)

    # Check resolver paths exist
    assert resolver.batch_path(batch0.content_digest).is_file()
    assert resolver.head_path(head0.content_digest).is_file()
    for comp_digest in batch0.completion_record_digests:
        assert resolver.completion_path(batch0.boundary_epoch, comp_digest).is_file()

    # Reconcile successfully verifies loaded content digests
    reconciled = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert reconciled.content_digest == head0.content_digest

    # Corrupting content of a completion record causes reconcile to reject with mismatch
    first_comp_digest = batch0.completion_record_digests[0]
    comp_file = resolver.completion_path(batch0.boundary_epoch, first_comp_digest)
    original_data = comp_file.read_text(encoding="utf-8")
    tampered_data = json.loads(original_data)
    tampered_data["target_size"] = 99999
    comp_file.write_text(json.dumps(tampered_data), encoding="utf-8")

    with pytest.raises((mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)):
        reconcile_target_size_screen_root(
            env["root"], env["authority"]
        )

    # Restore valid completion file
    comp_file.write_text(original_data, encoding="utf-8")
    reconciled_clean = reconcile_target_size_screen_root(
        env["root"], env["authority"]
    )
    assert reconciled_clean.content_digest == head0.content_digest


def test_p3e_pass_b_persistence_cas_and_failure_diagnostics(tmp_path: Path) -> None:
    """Pass B: CAS commit semantics, raw failure diagnostics, and persistence create-or-verify."""
    from mdstats.training_data.eval2 import Eval2NumericalEvaluationError
    from mdstats.training_data.target_size_execution.persistence import (
        publish_immutable_bytes_create_or_verify,
        publish_immutable_json_create_or_verify,
    )
    from mdstats.training_data.target_size_execution import (
        build_target_size_eval2_failure_cell_completion_record,
        build_target_size_success_cell_completion_record,
        build_target_size_train2_failure_cell_completion_record,
    )

    env = _env(tmp_path, root_name="screen_pass_b")
    definition = env["aggregate"].definition
    size0 = definition.qualified_candidate_sizes[0]
    seed0 = definition.policy.optimizer_seeds[0]
    window = env["window"]
    (
        trajectory,
        role,
        snapshot,
        comp_success,
        materialization,
        eval_artifact,
        pred_evidence,
        metric_record,
    ) = _execute_candidate_boundary(env, tmp_path, size0, seed0, 1)

    # 1. CAS commit retry idempotency vs conflicting child heads
    state = env["aggregate"].reducer_state
    batch0, head0 = _full_matrix(env, tmp_path, state)

    # Idempotent retry: re-committing the exact same batch on same root returns the same head
    head_retry = commit_target_size_boundary_batch(
        env["root"],
        definition,
        state,
        batch0,
    )
    assert head_retry.content_digest == head0.content_digest

    # Conflicting commit: wrong pre-state fails under CAS lock
    with pytest.raises(mdstats.TrainingDataInputError, match="pre-state"):
        commit_target_size_boundary_batch(
            env["root"],
            definition,
            head0.post_state,  # mismatch with batch0.pre_state
            batch0,
        )

    # 2. Raw TRAIN2 failure builder validation
    train_fail_rec, failure_checkpoint_directory = _durable_train2_failure_record(
        tmp_path, trajectory, env["schedule"], 1
    )
    plan_n1 = target_size_rung_plan(trajectory, env["schedule"], boundary_epoch=1)

    # Rejects pretranslated TargetSizeNumericalFailure as failure_record
    from mdstats.training_data.target_size_execution import translate_target_size_train2_failure
    derived_outcome = translate_target_size_train2_failure(
        train_fail_rec,
        trajectory=trajectory,
        definition=definition,
        schedule=env["schedule"],
        scheduled_boundary_epoch=1,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="Train2NumericalFailureRecord"):
        build_target_size_train2_failure_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            failure_record=derived_outcome,  # Wrong type: must be Train2NumericalFailureRecord
            planned_rung=plan_n1,
            schedule=env["schedule"],
        )

    # n1 rung rejects predecessor continuation
    with pytest.raises(mdstats.TrainingDataInputError, match="Initial n1 ancestry"):
        build_target_size_train2_failure_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            failure_record=train_fail_rec,
            planned_rung=plan_n1,
            schedule=env["schedule"],
            definition=definition,
            predecessor_continuation=snapshot,
            checkpoint_directory=failure_checkpoint_directory,
        )

    # Proper n1 build succeeds
    comp_train2 = build_target_size_train2_failure_cell_completion_record(
        window=window,
        trajectory=trajectory,
        materialization=materialization,
        failure_record=train_fail_rec,
        planned_rung=plan_n1,
        schedule=env["schedule"],
        definition=definition,
        predecessor_continuation=initial_target_size_continuation_request(trajectory),
        checkpoint_directory=failure_checkpoint_directory,
    )
    assert comp_train2.kind == "train2_failure"
    assert comp_train2.planned_rung_digest == plan_n1.content_digest

    # 3. Raw EVAL2 failure builder validation: rejects mismatched prediction digest
    forged_eval_err = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "NaN force predicted",
        target_role_digest=role.content_digest,
        prediction_digest="0" * 64,  # Mismatched prediction payload digest
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="prediction payload"):
        build_target_size_eval2_failure_cell_completion_record(
            window=window,
            trajectory=trajectory,
            materialization=materialization,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=pred_evidence,
            failure_record=forged_eval_err,
            planned_rung=plan_n1,
            schedule=env["schedule"],
        )

    # 4. Persistence primitives create-or-verify
    test_json_file = tmp_path / "persistence_test" / "test.json"
    payload = {"schema": "test.v1", "value": 42}
    publish_immutable_json_create_or_verify(test_json_file, payload)
    assert test_json_file.is_file()

    # Create-or-verify with identical payload succeeds
    publish_immutable_json_create_or_verify(test_json_file, payload)

    # Create-or-verify with differing payload fails
    with pytest.raises(mdstats.TrainingDataInputError, match="Conflicting"):
        publish_immutable_json_create_or_verify(test_json_file, {"schema": "test.v1", "value": 99})
