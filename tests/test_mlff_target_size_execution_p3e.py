"""P3-E gate evidence: complete-boundary coordinator, exactly-once commits,
crash-consistent restart reconciliation, P2 reducer sole decision authority."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TargetSizeCompleteBoundaryBatch,
    apply_complete_boundary_batch,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    collect_boundary_candidate_outcomes,
    commit_target_size_boundary_batch,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initialize_target_size_screen,
    load_current_execution_head,
    persist_complete_boundary_batch,
    reconcile_target_size_screen_root,
    record_candidate_boundary_outcome,
    target_size_population_correlation_blocks,
    target_size_rung_plan,
    bind_target_size_boundary_state,
)
from mdstats.training_data.target_size_execution import coordinator as coordinator_module
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_experiment import ReducerStatus
from mdstats.training_data.neutral_substrate import build_neutral_split_exclusion_evidence
import tests.test_mlff_target_size_execution_p3d as p3d


def _env(tmp_path: Path, *, root_name: str = "screen"):
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    frames, fdr, _ = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule((1, 3, 10))
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    context = build_target_size_execution_context(
        aggregate.definition, common, schedule, seed_neutral_optimizer_policy=optimizer
    )
    aggregate = aggregate.with_reducer_state(
        context.bind(aggregate.definition, aggregate.reducer_state)
    )
    evidence = build_neutral_split_exclusion_evidence(fa, nb)
    blocks = target_size_population_correlation_blocks(aggregate, evidence)
    root = tmp_path / root_name
    root.mkdir()
    window = initialize_target_size_screen(root, aggregate, context, common)
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
    }


def _epsilon(size: int, seed: int) -> float:
    # Deterministic distinct per-candidate scores: larger N is worse, so the
    # smallest candidate size must eventually be selected.
    return (2.5e-3 * size) + (1.0e-4 * seed)


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
    name = f"ckpt-{size}-{seed}-{boundary}"
    state = p3c_test_boundary_state(env, tmp_path, trajectory, boundary, name=name)
    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=state,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=env["blocks"],
    )
    view = p3d._view_for(
        env, tmp_path, tuple(role.evaluation_frame_uids), name=f"view-{size}-{seed}-{boundary}"
    )
    predictions = p3d._predictions_for(view, epsilon=_epsilon(size, seed))
    outcome = evaluate_target_size_boundary(role, view, predictions)
    return trajectory, role, state, outcome


def _seeded(optimizer, seed: int):
    from dataclasses import replace

    return replace(optimizer, seed=seed)


def p3c_test_boundary_state(env, tmp_path, trajectory, boundary, *, name):
    checkpoint_dir = tmp_path / name
    checkpoint_dir.mkdir()
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


def env_like(env):
    return env


def _run_boundary_matrix(env, tmp_path: Path, state, *, skip: list | None = None):
    """Execute one complete active matrix, record outcomes, build batch."""

    definition = env["aggregate"].definition
    requirements = derive_active_boundary_requirements(definition, state)
    assert requirements is not None
    boundary, evaluation_size, keys = requirements
    outcomes = []
    for index, (size, seed) in enumerate(keys):
        if skip and index in skip:
            continue
        trajectory, role, state_boundary, outcome = _execute_candidate_boundary(
            env, tmp_path, size, seed, boundary
        )
        assert outcome.boundary_epoch == boundary
        assert outcome.evaluation_membership_digest == (
            definition.evaluation_order.membership_digest(evaluation_size)
        )
        outcomes.append(outcome)
        record_candidate_boundary_outcome(env["root"], env["window"], trajectory, outcome)
    return boundary, evaluation_size, keys, outcomes


def _full_matrix(env, tmp_path, state):
    boundary, evaluation_size, keys, outcomes = _run_boundary_matrix(env, tmp_path, state)
    assert len(outcomes) == len(keys)
    definition = env["aggregate"].definition
    batch = build_complete_boundary_batch(definition, state, outcomes)
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
    boundary, evaluation_size, keys, outcomes = _run_boundary_matrix(env, tmp_path, state)
    assert len(keys) == len(definition.policy.optimizer_seeds) * len(state.active_candidate_sizes)
    assert list(keys) == sorted(keys)  # exact P2 size-major/seed-minor order
    batch = build_complete_boundary_batch(definition, state, outcomes)
    assert batch.boundary_epoch == boundary
    assert batch.evaluation_membership_digest == (
        definition.evaluation_order.membership_digest(evaluation_size)
    )
    assert tuple(batch.active_candidate_sizes) == tuple(state.active_candidate_sizes)
    # Reordered (even perfectly keyed) matrices are rejected.
    shuffled = tuple(reversed(list(outcomes)))
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, shuffled)
    # Missing one candidate outcome.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, outcomes[:-1])
    # Duplicated candidate outcome.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(
            definition, state, tuple(outcomes) + (outcomes[-1],)
        )
    # Foreign seed substitution.
    foreign = [
        mdstats.TargetSizeBoundaryMetric(
            experiment_definition_digest=definition.content_digest,
            execution_context_digest=state.execution_context_digest,
            target_size=keys[-1][0],
            optimizer_seed=999,
            boundary_epoch=boundary,
            evaluation_membership_digest=definition.evaluation_order.membership_digest(evaluation_size),
            target_force_rmse_mev_per_a=1.0,
        )
        if index == len(outcomes) - 1
        else outcome
        for index, outcome in enumerate(outcomes)
    ]
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, tuple(foreign))


def test_p3e_partial_outcomes_never_advance_reducer(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, outcomes = _run_boundary_matrix(
        env, tmp_path, state, skip=[1]
    )
    assert len(outcomes) == len(keys) - 1
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, outcomes)
    collected = collect_boundary_candidate_outcomes(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(collected) == len(outcomes)
    # The reducer state remains exactly the pre-boundary state; no head exists.
    assert load_current_execution_head(env["root"]) is None
    assert state.completed_boundary_epochs == ()


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
    outcomes: list = []
    for index, (size, seed) in enumerate(keys):
        try:
            if index == 1:
                _boom()
            trajectory, _role, _state_b, outcome = _execute_candidate_boundary(
                env, tmp_path, size, seed, boundary
            )
            record_candidate_boundary_outcome(
                env["root"], env["window"], trajectory, outcome
            )
            outcomes.append(outcome)
        except OSError:
            exec_failed.append(f"{size}:{seed}")
    assert exec_failed == [f"{keys[1][0]}:{keys[1][1]}"]
    # Partial matrix: no batch, no reducer advance.
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(
            definition,
            state,
            collect_boundary_candidate_outcomes(
                env["root"], env["window"], boundary_epoch=boundary
            ),
        )
    assert load_current_execution_head(env["root"]) is None
    # Retrying the failed work completes the same boundary without duplicates.
    size, seed = keys[1]
    trajectory, _role, _state_b, outcome = _execute_candidate_boundary(
        env, tmp_path, size, seed, boundary
    )
    record_candidate_boundary_outcome(env["root"], env["window"], trajectory, outcome)
    recover_outcomes = collect_boundary_candidate_outcomes(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(recover_outcomes) == len(keys)
    batch = build_complete_boundary_batch(definition, state, recover_outcomes)
    head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
    validate_reconciled = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
    )
    assert validate_reconciled.content_digest == head.content_digest


def test_p3e_outcome_publication_idempotent_and_conflicts_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, outcomes = _run_boundary_matrix(env, tmp_path, state)
    # Re-recording the identical outcome is a no-op.
    trajectory = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=keys[0][0],
        optimizer_policy=env["optimizer"],
        optimizer_seed=keys[0][1],
    )
    record_candidate_boundary_outcome(
        env["root"], env["window"], trajectory, outcomes[0]
    )
    collected = collect_boundary_candidate_outcomes(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(collected) == len(outcomes)
    # A conflicting outcome for the same candidate is rejected.
    forged = mdstats.TargetSizeBoundaryMetric(
        experiment_definition_digest=definition.content_digest,
        execution_context_digest=state.execution_context_digest,
        target_size=keys[0][0],
        optimizer_seed=keys[0][1],
        boundary_epoch=boundary,
        evaluation_membership_digest=outcomes[0].evaluation_membership_digest,
        target_force_rmse_mev_per_a=123.0,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        record_candidate_boundary_outcome(env["root"], env["window"], trajectory, forged)


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
        # Eliminated candidates receive no later ordinary screening work.
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
    # Only P2 reducer transitions produced any selection.
    if final.status is ReducerStatus.SELECTED:
        assert final.selected_target_size is not None
        assert final.selected_membership_digest == (
            definition.training_order.candidate_digest(final.selected_target_size)
        )
    # The finished screen has no active work afterwards.
    assert derive_active_boundary_requirements(definition, final) is None
    # Restart reconstruction reproduces exactly the same accepted state.
    head = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
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
    with pytest.raises(mdstats.TrainingDataInputError):
        reconcile_target_size_screen_root(
            env["root"], env["aggregate"], different_context, env["common"]
        )
    # A second initialize call with different authority fails closed.
    with pytest.raises(mdstats.TrainingDataInputError):
        initialize_target_size_screen(
            env["root"], env["aggregate"], different_context, env["common"]
        )


def test_p3e_worker_concurrency_and_no_reducer_access(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    boundary, evaluation_size, keys, outcomes = _run_boundary_matrix(env, tmp_path, state)
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
    by_key = {(o.target_size, o.optimizer_seed): o for o in outcomes}

    def _worker(key):
        record_candidate_boundary_outcome(
            env["root"], env["window"], trajectories[key], by_key[key]
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(_worker, list(keys) * 2 + list(reversed(keys))))
    collected = collect_boundary_candidate_outcomes(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(collected) == len(keys)
    assert tuple((o.target_size, o.optimizer_seed) for o in collected) == keys
    # No reducer transition was possible during worker activity.
    assert load_current_execution_head(env["root"]) is None
    # Only now, through the coordinator commit path.
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
    trajectory, role, state_boundary, outcome_one = _execute_candidate_boundary(
        env, tmp_path, keys[0][0], keys[0][1], boundary
    )
    head = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
    )
    assert head is None

    # (b) After only some boundary outcomes exist: still pre-state.
    record_candidate_boundary_outcome(env["root"], env["window"], trajectory, outcome_one)
    assert load_current_execution_head(env["root"]) is None
    partial = collect_boundary_candidate_outcomes(
        env["root"], env["window"], boundary_epoch=boundary
    )
    assert len(partial) == 1
    with pytest.raises(mdstats.TrainingDataInputError):
        build_complete_boundary_batch(definition, state, partial)

    # (c) Finish the matrix; persist the batch but do not commit (crash point).
    outcomes = [outcome_one]
    for size, seed in keys[1:]:
        trajectory2, _r, _s, outcome2 = _execute_candidate_boundary(
            env, tmp_path, size, seed, boundary
        )
        record_candidate_boundary_outcome(env["root"], env["window"], trajectory2, outcome2)
        outcomes.append(outcome2)
    outcomes = tuple(
        collect_boundary_candidate_outcomes(
            env["root"], env["window"], boundary_epoch=boundary
        )
    )
    batch = build_complete_boundary_batch(definition, state, outcomes)
    persist_complete_boundary_batch(env["root"], batch)
    repaired = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
    )
    assert repaired is not None
    direct_state = apply_complete_boundary_batch(definition, state, batch)
    assert repaired.post_state.content_digest == direct_state.content_digest
    assert repaired.batch_digest == batch.content_digest

    # (d) Simulate loss of only the current-head pointer (post-batch, post-head).
    current_path = env["root"] / "current_head.json"
    current_path.unlink()
    orphaned = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
    )
    assert orphaned.content_digest == repaired.content_digest
    assert load_current_execution_head(env["root"]).content_digest == repaired.content_digest

    # (e) Already committed state is validated, never reapplied.
    again = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
    )
    assert again.content_digest == repaired.content_digest
    # The committed history replays exactly through P2.
    final_state = load_current_execution_head(env["root"]).post_state
    mdstats.validate_target_size_reducer_state(definition, final_state)
    assert final_state.completed_boundary_epochs == (boundary,)

    # (f) A conflicting batch for the same pre-state fails closed.
    forged = TargetSizeCompleteBoundaryBatch(
        pre_state_digest=state.content_digest,
        experiment_definition_digest=batch.experiment_definition_digest,
        execution_context_digest=batch.execution_context_digest,
        boundary_epoch=boundary,
        evaluation_membership_digest=batch.evaluation_membership_digest,
        active_candidate_sizes=batch.active_candidate_sizes,
        optimizer_seeds=batch.optimizer_seeds,
        outcomes=tuple(
            mdstats.TargetSizeNumericalFailure(
                experiment_definition_digest=definition.content_digest,
                execution_context_digest=o.execution_context_digest,
                target_size=o.target_size,
                optimizer_seed=o.optimizer_seed,
                boundary_epoch=o.boundary_epoch,
                evaluation_membership_digest=o.evaluation_membership_digest,
                kind=mdstats.NumericalFailureKind.EVAL_NONFINITE_PREDICTION,
                classification_evidence_digest="b" * 64,
            )
            for o in batch.outcomes
        ),
    )
    assert forged.content_digest != batch.content_digest
    (env["root"] / "batches" / f"{forged.content_digest}.json").write_text(
        json.dumps(forged.to_dict())
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        reconcile_target_size_screen_root(
            env["root"], env["aggregate"], env["context"], env["common"]
        )


def test_p3e_execution_only_invariance_no_cv_or_prod_drift(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    state = env["aggregate"].reducer_state
    batch, head = _full_matrix(env, tmp_path, state)
    # Production-horizon fluctuations never enter screen identity.
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
