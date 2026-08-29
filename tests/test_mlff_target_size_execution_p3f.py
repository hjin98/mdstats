"""P3-F gate evidence: bounded end-to-end through real owners and the
mandatory structural/absence inspection of the assembled P3 path."""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import replace
from pathlib import Path

import pytest

import mdstats
import mdstats.training_data as training_data_pkg
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
import mdstats.training_data.target_size_execution as tee
from mdstats.training_data.neutral_substrate import build_neutral_split_exclusion_evidence
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    bind_target_size_boundary_state,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_cell_completion_record,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    collect_boundary_candidate_outcomes,
    collect_boundary_cell_completion_records,
    commit_target_size_boundary_batch,
    continuation_request_from_boundary,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initial_target_size_continuation_request,
    initialize_target_size_screen,
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
    validate_target_size_continuation_request,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_experiment import ReducerStatus


def _epsilon(size: int, seed: int) -> float:
    return (2.5e-3 * size) + (1.0e-4 * seed)


def _screen_env(tmp_path: Path):
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
    root = tmp_path / "screen"
    root.mkdir(parents=True, exist_ok=True)
    window = initialize_target_size_screen(root, aggregate, context, common)
    return {
        "aggregate": aggregate,
        "common": common,
        "index": index,
        "frames": frames,
        "frame_data_by_run": fdr,
        "frame_authority": fa,
        "schedule": schedule,
        "context": context,
        "optimizer": optimizer,
        "blocks": blocks,
        "root": root,
        "window": window,
    }


class _CandidateLane:
    """One scientific trajectory carried through rung continuation."""

    def __init__(self, env, tmp_path: Path, size: int, seed: int):
        definition = env["aggregate"].definition
        self.policy = (
            env["optimizer"] if seed == env["optimizer"].seed
            else replace(env["optimizer"], seed=seed)
        )
        self.trajectory = build_target_size_candidate_trajectory(
            definition,
            env["context"],
            env["common"],
            env["schedule"],
            target_size=size,
            optimizer_policy=self.policy,
            optimizer_seed=seed,
        )
        self.projection = project_target_size_candidate_preparation(
            env["common"], definition, size
        )
        self.checkpoint_dir = tmp_path / f"lane-{size}-{seed}"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.boundary_state = None
        self.continuation_epochs: list[int] = []

    def materialize(self, env, tmp_path: Path):
        return materialize_target_size_candidate(
            self.trajectory,
            self.projection,
            env["common"],
            canonical_frame_authority=env["frame_authority"],
            frame_catalog=env["frames"],
            frame_data_by_run=env["frame_data_by_run"],
            output_directory=tmp_path / f"mat-{self.trajectory.target_size}-{self.trajectory.optimizer_seed}",
            optimizer_policy=self.policy,
            frame_array_index=env["index"],
        )

    def train_to_boundary(self, env, boundary: int):
        plan = target_size_rung_plan(
            self.trajectory, env["schedule"], boundary_epoch=boundary
        )
        if self.boundary_state is None:
            request = initial_target_size_continuation_request(self.trajectory)
            start_epoch = 0
        else:
            request = continuation_request_from_boundary(self.boundary_state)
            predecessor = validate_target_size_continuation_request(
                request,
                self.trajectory,
                env["schedule"],
                checkpoint_directory=self.checkpoint_dir,
            )
            assert predecessor.completed_epochs == self.continuation_epochs[-1]
            assert predecessor.raw_checkpoint_epoch == self.continuation_epochs[-1] - 1
            start_epoch = self.continuation_epochs[-1]
        _runtime, summary, _state, _rng = p3c._run_rung(
            plan,
            self.checkpoint_dir,
            start_epoch=start_epoch,
            updates_per_epoch=self.trajectory.realization.updates_per_epoch,
            seed=self.trajectory.optimizer_seed,
        )
        assert summary.completed_epochs == boundary
        assert summary.raw_checkpoint_epoch == boundary - 1
        self.continuation_epochs.append(boundary)
        self.boundary_state = bind_target_size_boundary_state(
            self.trajectory,
            env["schedule"],
            summary,
            checkpoint_directory=self.checkpoint_dir,
        )
        return self.boundary_state


def test_p3f_bounded_end_to_end_through_real_owners(tmp_path: Path) -> None:
    env = _screen_env(tmp_path)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    state = env["aggregate"].reducer_state

    lanes: dict[tuple[int, int], _CandidateLane] = {}
    cells: dict[tuple[int, int], dict] = {}
    materialized: dict[tuple[int, int], object] = {}
    committed_heads: list = []

    while not state.is_terminal:
        requirements = derive_active_boundary_requirements(definition, state)
        assert requirements is not None
        boundary, evaluation_size, keys = requirements
        boundary_index = schedule.fidelity_epochs.index(boundary)
        eval_dir = tmp_path / f"eval_data_{boundary}"
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

        for size, seed in keys:
            if (size, seed) not in lanes:
                lanes[(size, seed)] = _CandidateLane(env, tmp_path, size, seed)
            lane = lanes[(size, seed)]
            if (size, seed) not in materialized:
                materialized[(size, seed)] = lane.materialize(env, tmp_path)
            boundary_state = lane.train_to_boundary(env, boundary)
            snapshot = promote_target_size_boundary_snapshot(
                lane.trajectory,
                boundary_state,
                checkpoint_directory=lane.checkpoint_dir,
                snapshot_root=env["root"],
            )
            role = build_target_size_eval2_role(
                trajectory=lane.trajectory,
                boundary_state=snapshot,
                definition=definition,
                schedule=schedule,
                correlation_blocks=env["blocks"],
                evaluation_data=eval_artifact,
            )
            view = eval_artifact.build_evaluation_view(eval_dir)
            evaluator = p3d._predictions_evaluator(view, epsilon=_epsilon(size, seed))
            mat_lane_dir = tmp_path / f"mat-{lane.trajectory.target_size}-{lane.trajectory.optimizer_seed}"
            pred_evidence = run_target_size_direct_boundary_inference(
                trajectory=lane.trajectory,
                materialization=materialized[(size, seed)],
                boundary_state=snapshot,
                role=role,
                evaluation_data=eval_artifact,
                canonical_frame_authority=env["frame_authority"],
                definition=definition,
                context=env["context"],
                common=env["common"],
                schedule=schedule,
                optimizer_policy=lane.policy,
                materialization_directory=mat_lane_dir,
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
            completion_record = build_target_size_cell_completion_record(
                window=env["window"],
                trajectory=lane.trajectory,
                materialization=materialized[(size, seed)],
                boundary_snapshot=snapshot,
                eval2_role=role,
                evaluation_data=eval_artifact,
                outcome=outcome,
                prediction_evidence=pred_evidence,
                eval2_metric_record=metric_record,
            )
            record_candidate_boundary_outcome(
                env["root"],
                env["window"],
                lane.trajectory,
                completion_record,
                materialization=materialized[(size, seed)],
                boundary_snapshot=snapshot,
                eval2_role=role,
                evaluation_data=eval_artifact,
                prediction_evidence=pred_evidence,
                eval2_metric_record=metric_record,
            )
        collected = collect_boundary_cell_completion_records(
            env["root"], env["window"], boundary_epoch=boundary
        )
        cells[boundary] = [
            (rec.target_size, rec.optimizer_seed,
             rec.outcome.target_force_rmse_mev_per_a
             if isinstance(rec.outcome, mdstats.TargetSizeBoundaryMetric) else None)
            for rec in collected
        ]
        batch = build_complete_boundary_batch(definition, state, collected)
        persist_complete_boundary_batch(env["root"], batch)
        if boundary == schedule.fidelity_epochs[1]:
            # Simulate a crash between batch persistence and head publication
            repaired = reconcile_target_size_screen_root(
                env["root"],
                env["aggregate"],
                env["context"],
                env["common"],
                schedule=schedule,
            )
            head = repaired
        else:
            head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
        committed_heads.append(head)
        opened = reconcile_target_size_screen_root(
            env["root"],
            env["aggregate"],
            env["context"],
            env["common"],
            schedule=schedule,
        )
        assert opened.content_digest == head.content_digest
        state = head.post_state

    assert state.is_terminal
    assert state.status is ReducerStatus.SELECTED
    assert len(committed_heads) == len(schedule.fidelity_epochs)
    selected_digest = definition.training_order.candidate_digest(
        state.selected_target_size
    )
    assert state.selected_membership_digest == selected_digest
    assert lanes[(state.selected_target_size, definition.policy.optimizer_seeds[0])].continuation_epochs == list(
        schedule.fidelity_epochs
    )
    for lane in lanes.values():
        assert lane.continuation_epochs and lane.continuation_epochs[0] == schedule.fidelity_epochs[0]
    final_head = reconcile_target_size_screen_root(
        env["root"],
        env["aggregate"],
        env["context"],
        env["common"],
        schedule=schedule,
    )
    assert final_head.post_state.content_digest == state.content_digest
    mdstats.validate_target_size_reducer_state(definition, final_head.post_state)
    loaded_head = load_current_execution_head(env["root"])
    assert loaded_head.post_state_digest == state.content_digest


def _module_identifiers(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    attrs = {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
    strings = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    return names | attrs | strings


_FORBIDDEN_AUTHORITY_TOKENS = (
    "label_domain_id",
    "label_domain",
    "frame_catalog_digest",
    "data7_bundle_digest",
    "data5_bundle_digest",
    "selection_size",
    "selection_ladder",
    "cv_fold",
    "fold_index",
    "pre_target_cv",
    "candidate_complement",
    "development_complement",
    "checkpoint_shortlist",
    "shortlist",
    "rescue",
    "bootstrap",
    "ProductionMaterializationPlan",
    "build_data8_preparation_bundle",
    "FeatureFitDomain",
)


def test_p3f_absence_of_retired_scientific_authority_in_package() -> None:
    import importlib

    modules = [
        "common",
        "schedule",
        "context",
        "export",
        "candidate",
        "execution",
        "evaluation",
        "coordinator",
    ]
    for name in modules:
        module = importlib.import_module(f"mdstats.training_data.target_size_execution.{name}")
        identifiers = _module_identifiers(module)
        for token in _FORBIDDEN_AUTHORITY_TOKENS:
            assert token not in identifiers, f"{name}: {token}"


def test_p3f_p3_path_unreachable_from_production_surface() -> None:
    assert "target_size_execution" not in training_data_pkg.__all__
    import inspect as _inspect
    import re

    init_source = _inspect.getsource(training_data_pkg)
    assert not re.search(r"(?<![\w])target_size_execution(?![\w])", init_source)
    import subprocess, sys

    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import mdstats, mdstats.training_data as td; "
            "import sys; "
            "sys.exit(0 if (not hasattr(mdstats, 'target_size_execution') "
            "and not hasattr(td, 'target_size_execution')) else 3)",
        ],
        capture_output=True,
        check=False,
    )
    assert probe.returncode == 0, probe.stderr.decode(errors="replace")
    cli_modules = (
        "_campaign_cli_core",
        "campaign_cli",
        "campaign_control",
        "campaign_execution",
        "critical_precision_cli",
        "production_materialization",
        "production_model_sweep",
        "production_qualification",
    )
    import importlib

    for name in cli_modules:
        module = importlib.import_module(f"mdstats.training_data.{name}")
        identifiers = _module_identifiers(module)
        assert "target_size_execution" not in identifiers
        source = inspect.getsource(module)
        assert not re.search(r"(?<![\w])target_size_execution(?![\w])", source)


def _deep_keys(payload, out: set) -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            out.add(str(key))
            _deep_keys(value, out)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            _deep_keys(item, out)


def test_p3f_serialized_payloads_carry_no_retired_fields(tmp_path: Path) -> None:
    env = _screen_env(tmp_path)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    state = env["aggregate"].reducer_state

    lane = _CandidateLane(env, tmp_path, definition.qualified_candidate_sizes[0], 1)
    materialization = lane.materialize(env, tmp_path)
    boundary_state = lane.train_to_boundary(env, schedule.fidelity_epochs[0])
    snapshot = promote_target_size_boundary_snapshot(
        lane.trajectory,
        boundary_state,
        checkpoint_directory=lane.checkpoint_dir,
        snapshot_root=env["root"],
    )
    eval_artifact = write_target_size_evaluation_artifact(
        tmp_path / "eval_data",
        definition=definition,
        evaluation_size=definition.policy.evaluation_sizes[0],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )
    role = build_target_size_eval2_role(
        trajectory=lane.trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=schedule,
        correlation_blocks=env["blocks"],
        evaluation_data=eval_artifact,
    )

    payloads = [
        env["window"].to_dict(),
        env["context"].to_dict(),
        env["context"].policy_digest_payload() if hasattr(env["context"], "policy_digest_payload") else {},
        lane.trajectory.to_dict(),
        lane.trajectory.realization.to_dict(),
        materialization.to_dict(),
        boundary_state.to_dict(),
        snapshot.to_dict(),
        role.to_dict(),
        eval_artifact.to_dict(),
    ]
    keys: set[str] = set()
    for payload in payloads:
        _deep_keys(payload, keys)
    forbidden_keys = {
        "label_domain_id",
        "frame_catalog_digest",
        "data7_bundle_digest",
        "data5_bundle_digest",
        "selection_size",
        "selection_ladder",
        "cv_fold",
        "fold_index",
        "coarse_fallback",
        "checkpoint_shortlist",
        "shortlist",
        "rescue",
        "identical_checkpoint_pool",
    }
    assert not (keys & forbidden_keys)
    text = json.dumps(lane.trajectory.to_dict())
    assert "candidate_membership_digest" in text
    assert "optimizer_seed" in text


def test_p3f_adversarial_restart_orphan_and_fork_heads(tmp_path: Path) -> None:
    env = _screen_env(tmp_path)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    state = env["aggregate"].reducer_state

    # Run boundary 0 matrix and commit batch
    requirements = derive_active_boundary_requirements(definition, state)
    boundary, evaluation_size, keys = requirements
    eval_dir = tmp_path / f"eval_data_{boundary}"
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
    for size, seed in keys:
        lane = _CandidateLane(env, tmp_path, size, seed)
        mat = lane.materialize(env, tmp_path)
        boundary_state = lane.train_to_boundary(env, boundary)
        snapshot = promote_target_size_boundary_snapshot(
            lane.trajectory,
            boundary_state,
            checkpoint_directory=lane.checkpoint_dir,
            snapshot_root=env["root"],
        )
        role = build_target_size_eval2_role(
            trajectory=lane.trajectory,
            boundary_state=snapshot,
            definition=definition,
            schedule=schedule,
            correlation_blocks=env["blocks"],
            evaluation_data=eval_artifact,
        )
        view = eval_artifact.build_evaluation_view(eval_dir)
        evaluator = p3d._predictions_evaluator(view, epsilon=_epsilon(size, seed))
        mat_lane_dir = tmp_path / f"mat-{lane.trajectory.target_size}-{lane.trajectory.optimizer_seed}"
        pred_evidence = run_target_size_direct_boundary_inference(
            trajectory=lane.trajectory,
            materialization=mat,
            boundary_state=snapshot,
            role=role,
            evaluation_data=eval_artifact,
            canonical_frame_authority=env["frame_authority"],
            definition=definition,
            context=env["context"],
            common=env["common"],
            schedule=schedule,
            optimizer_policy=lane.policy,
            materialization_directory=mat_lane_dir,
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
        completion_record = build_target_size_cell_completion_record(
            window=env["window"],
            trajectory=lane.trajectory,
            materialization=mat,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            outcome=outcome,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
        )
        record_candidate_boundary_outcome(
            env["root"],
            env["window"],
            lane.trajectory,
            completion_record,
            materialization=mat,
            boundary_snapshot=snapshot,
            eval2_role=role,
            evaluation_data=eval_artifact,
            prediction_evidence=pred_evidence,
            eval2_metric_record=metric_record,
        )
    collected = collect_boundary_cell_completion_records(
        env["root"], env["window"], boundary_epoch=boundary
    )
    batch = build_complete_boundary_batch(definition, state, collected)
    head = commit_target_size_boundary_batch(env["root"], definition, state, batch)

    # 1. Test orphan head in heads/
    orphan_head = replace(head, batch_digest="0" * 64)
    orphan_path = env["root"] / "heads" / f"{orphan_head.content_digest}.json"
    orphan_path.write_text(json.dumps(orphan_head.to_dict()))
    with pytest.raises(mdstats.TrainingDataInputError, match="Fork detected|Orphan head detected"):
        reconcile_target_size_screen_root(
            env["root"],
            env["aggregate"],
            env["context"],
            env["common"],
            schedule=schedule,
        )
    orphan_path.unlink()

    # 2. Test conflicting completion records for the same cell
    from mdstats.training_data.target_size_execution import translate_target_size_train2_failure

    train_fail_rec = p3c._failure_record(
        lane.trajectory,
        schedule,
        boundary,
        code="train_nonfinite_model_state",
        failed_epoch=0,
    )
    train_fail_outcome = translate_target_size_train2_failure(
        train_fail_rec,
        trajectory=lane.trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=boundary,
    )
    conflicting_comp = build_target_size_cell_completion_record(
        window=env["window"],
        trajectory=lane.trajectory,
        materialization=mat,
        failure_record=train_fail_rec,
        outcome=train_fail_outcome,
        kind="train2_failure",
    )
    conflicting_path = env["root"] / "completions" / str(boundary) / f"{conflicting_comp.content_digest}.json"
    conflicting_path.write_text(json.dumps(conflicting_comp.to_dict()))
    with pytest.raises(mdstats.TrainingDataInputError, match="Conflicting completion records"):
        reconcile_target_size_screen_root(
            env["root"],
            env["aggregate"],
            env["context"],
            env["common"],
            schedule=schedule,
        )
    conflicting_path.unlink()

    # Clean reconciliation succeeds
    reconciled = reconcile_target_size_screen_root(
        env["root"],
        env["aggregate"],
        env["context"],
        env["common"],
        schedule=schedule,
    )
    assert reconciled.content_digest == head.content_digest


def test_p3f_subprocess_fresh_continuation_and_replay(tmp_path: Path) -> None:
    """F-R5.1: Mid-screen fresh-process continuation + terminal replay."""
    import subprocess
    import sys

    script_path = tmp_path / "subprocess_runner.py"
    script_code = '''
import sys
from pathlib import Path
from dataclasses import replace
import mdstats
from mdstats.training_data.neutral_substrate import build_neutral_split_exclusion_evidence
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    bind_target_size_boundary_state,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_cell_completion_record,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    collect_boundary_cell_completion_records,
    commit_target_size_boundary_batch,
    continuation_request_from_boundary,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initial_target_size_continuation_request,
    initialize_target_size_screen,
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
    validate_target_size_continuation_request,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import project_target_size_candidate_preparation
from mdstats.training_data.target_size_execution.context import build_target_size_execution_context
from mdstats.training_data.target_size_experiment import ReducerStatus
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d

def get_env(root_dir: Path, mode: str):
    p1_dir = root_dir / f"p1_{mode}"
    p1_dir.mkdir(parents=True, exist_ok=True)
    manifest, fa, nb, aggregate, common, index = p3a._common(p1_dir)
    frames, fdr, _ = p3a._frame_arrays(p1_dir, manifest)
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
    screen_root = root_dir / "screen"
    screen_root.mkdir(parents=True, exist_ok=True)
    return {
        "aggregate": aggregate,
        "common": common,
        "index": index,
        "frames": frames,
        "frame_data_by_run": fdr,
        "frame_authority": fa,
        "schedule": schedule,
        "context": context,
        "optimizer": optimizer,
        "blocks": blocks,
        "root": screen_root,
    }

def run_step(mode: str, root_dir_str: str):
    root_dir = Path(root_dir_str)
    env = get_env(root_dir, mode)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    screen_root = env["root"]

    if mode == "process_a":
        window = initialize_target_size_screen(
            screen_root, env["aggregate"], env["context"], env["common"]
        )
        state = env["aggregate"].reducer_state
        requirements = derive_active_boundary_requirements(definition, state)
        assert requirements is not None
        boundary, evaluation_size, keys = requirements
        assert boundary == 1

        eval_dir = root_dir / f"eval_data_{boundary}"
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
        for size, seed in keys:
            policy = (
                env["optimizer"] if seed == env["optimizer"].seed
                else replace(env["optimizer"], seed=seed)
            )
            trajectory = build_target_size_candidate_trajectory(
                definition, env["context"], env["common"], schedule,
                target_size=size, optimizer_policy=policy, optimizer_seed=seed
            )
            projection = project_target_size_candidate_preparation(env["common"], definition, size)
            lane_dir = root_dir / f"lane-{size}-{seed}"
            lane_dir.mkdir(parents=True, exist_ok=True)
            mat_dir = root_dir / f"mat-{size}-{seed}"
            mat = materialize_target_size_candidate(
                trajectory, projection, env["common"],
                canonical_frame_authority=env["frame_authority"],
                frame_catalog=env["frames"],
                frame_data_by_run=env["frame_data_by_run"],
                output_directory=mat_dir,
                optimizer_policy=policy,
                frame_array_index=env["index"],
            )
            plan = target_size_rung_plan(trajectory, schedule, boundary_epoch=boundary)
            _runtime, summary, _state, _rng = p3c._run_rung(
                plan, lane_dir, start_epoch=0,
                updates_per_epoch=trajectory.realization.updates_per_epoch,
                seed=seed,
            )
            b_state = bind_target_size_boundary_state(
                trajectory, schedule, summary, checkpoint_directory=lane_dir
            )
            snapshot = promote_target_size_boundary_snapshot(
                trajectory, b_state, checkpoint_directory=lane_dir, snapshot_root=screen_root
            )
            role = build_target_size_eval2_role(
                trajectory=trajectory, boundary_state=snapshot,
                definition=definition, schedule=schedule,
                correlation_blocks=env["blocks"], evaluation_data=eval_artifact
            )
            view = eval_artifact.build_evaluation_view(eval_dir)
            evaluator = p3d._predictions_evaluator(view, epsilon=(2.5e-3 * size) + (1.0e-4 * seed))
            pred = run_target_size_direct_boundary_inference(
                trajectory=trajectory, materialization=mat, boundary_state=snapshot,
                role=role, evaluation_data=eval_artifact,
                canonical_frame_authority=env["frame_authority"], definition=definition,
                context=env["context"], common=env["common"], schedule=schedule,
                optimizer_policy=policy, materialization_directory=mat_dir,
                snapshot_root=screen_root, evaluation_directory=eval_dir,
                inference_evaluator=evaluator
            )
            metric_record = run_target_size_eval2_reduction(role, eval_artifact, pred, root_directory=eval_dir)
            outcome = evaluate_target_size_boundary(role, eval_artifact, pred, root_directory=eval_dir)
            comp = build_target_size_cell_completion_record(
                window=window, trajectory=trajectory, materialization=mat,
                boundary_snapshot=snapshot, eval2_role=role, evaluation_data=eval_artifact,
                outcome=outcome, prediction_evidence=pred, eval2_metric_record=metric_record
            )
            record_candidate_boundary_outcome(
                screen_root, window, trajectory, comp,
                materialization=mat, boundary_snapshot=snapshot,
                eval2_role=role, evaluation_data=eval_artifact,
                prediction_evidence=pred, eval2_metric_record=metric_record
            )
        collected = collect_boundary_cell_completion_records(screen_root, window, boundary_epoch=boundary)
        batch0 = build_complete_boundary_batch(definition, state, collected)
        head0 = commit_target_size_boundary_batch(screen_root, definition, state, batch0)
        assert head0.post_state.completed_boundary_epochs == (1,)
        sys.exit(0)

    elif mode == "process_b":
        reconciled = reconcile_target_size_screen_root(
            screen_root, env["aggregate"], env["context"], env["common"], schedule=schedule
        )
        assert reconciled is not None
        head = reconciled
        state = head.post_state
        assert state.completed_boundary_epochs == (1,)
        window = initialize_target_size_screen(
            screen_root, env["aggregate"], env["context"], env["common"]
        )

        while not state.is_terminal:
            requirements = derive_active_boundary_requirements(definition, state)
            assert requirements is not None
            boundary, evaluation_size, keys = requirements
            eval_dir = root_dir / f"eval_data_{boundary}"
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
            for size, seed in keys:
                policy = (
                    env["optimizer"] if seed == env["optimizer"].seed
                    else replace(env["optimizer"], seed=seed)
                )
                trajectory = build_target_size_candidate_trajectory(
                    definition, env["context"], env["common"], schedule,
                    target_size=size, optimizer_policy=policy, optimizer_seed=seed
                )
                projection = project_target_size_candidate_preparation(env["common"], definition, size)
                lane_dir = root_dir / f"lane-{size}-{seed}"
                mat_dir = root_dir / f"mat-{size}-{seed}"
                mat = materialize_target_size_candidate(
                    trajectory, projection, env["common"],
                    canonical_frame_authority=env["frame_authority"],
                    frame_catalog=env["frames"],
                    frame_data_by_run=env["frame_data_by_run"],
                    output_directory=mat_dir,
                    optimizer_policy=policy,
                    frame_array_index=env["index"],
                )
                plan = target_size_rung_plan(trajectory, schedule, boundary_epoch=boundary)
                prev_boundary = schedule.fidelity_epochs[schedule.fidelity_epochs.index(boundary) - 1]
                _runtime, summary, _state, _rng = p3c._run_rung(
                    plan, lane_dir, start_epoch=prev_boundary,
                    updates_per_epoch=trajectory.realization.updates_per_epoch,
                    seed=seed,
                )
                b_state = bind_target_size_boundary_state(
                    trajectory, schedule, summary, checkpoint_directory=lane_dir
                )
                snapshot = promote_target_size_boundary_snapshot(
                    trajectory, b_state, checkpoint_directory=lane_dir, snapshot_root=screen_root
                )
                role = build_target_size_eval2_role(
                    trajectory=trajectory, boundary_state=snapshot,
                    definition=definition, schedule=schedule,
                    correlation_blocks=env["blocks"], evaluation_data=eval_artifact
                )
                view = eval_artifact.build_evaluation_view(eval_dir)
                evaluator = p3d._predictions_evaluator(view, epsilon=(2.5e-3 * size) + (1.0e-4 * seed))
                pred = run_target_size_direct_boundary_inference(
                    trajectory=trajectory, materialization=mat, boundary_state=snapshot,
                    role=role, evaluation_data=eval_artifact,
                    canonical_frame_authority=env["frame_authority"], definition=definition,
                    context=env["context"], common=env["common"], schedule=schedule,
                    optimizer_policy=policy, materialization_directory=mat_dir,
                    snapshot_root=screen_root, evaluation_directory=eval_dir,
                    inference_evaluator=evaluator
                )
                metric_record = run_target_size_eval2_reduction(role, eval_artifact, pred, root_directory=eval_dir)
                outcome = evaluate_target_size_boundary(role, eval_artifact, pred, root_directory=eval_dir)
                comp = build_target_size_cell_completion_record(
                    window=window, trajectory=trajectory, materialization=mat,
                    boundary_snapshot=snapshot, eval2_role=role, evaluation_data=eval_artifact,
                    outcome=outcome, prediction_evidence=pred, eval2_metric_record=metric_record
                )
                record_candidate_boundary_outcome(
                    screen_root, window, trajectory, comp,
                    materialization=mat, boundary_snapshot=snapshot,
                    eval2_role=role, evaluation_data=eval_artifact,
                    prediction_evidence=pred, eval2_metric_record=metric_record
                )
            collected = collect_boundary_cell_completion_records(screen_root, window, boundary_epoch=boundary)
            batch = build_complete_boundary_batch(definition, state, collected)
            head = commit_target_size_boundary_batch(screen_root, definition, state, batch)
            state = head.post_state
        assert state.is_terminal
        assert state.status is ReducerStatus.SELECTED
        sys.exit(0)

    elif mode == "process_c":
        reconciled = reconcile_target_size_screen_root(
            screen_root, env["aggregate"], env["context"], env["common"], schedule=schedule
        )
        assert reconciled is not None
        assert reconciled.post_state.is_terminal
        assert reconciled.post_state.status is ReducerStatus.SELECTED
        mdstats.validate_target_size_reducer_state(definition, reconciled.post_state)
        sys.exit(0)

if __name__ == "__main__":
    run_step(sys.argv[1], sys.argv[2])
'''
    script_path.write_text(script_code)

    import os
    repo_root = str(Path(__file__).resolve().parent.parent)
    sub_env = {**os.environ, "PYTHONPATH": repo_root}

    # 1. Run Process A (n1 boundary)
    p_a = subprocess.run(
        [sys.executable, str(script_path), "process_a", str(tmp_path)],
        capture_output=True,
        env=sub_env,
    )
    assert p_a.returncode == 0, p_a.stderr.decode()

    # 2. Run Process B (n2 & n3 rungs to terminal)
    p_b = subprocess.run(
        [sys.executable, str(script_path), "process_b", str(tmp_path)],
        capture_output=True,
        env=sub_env,
    )
    assert p_b.returncode == 0, p_b.stderr.decode()

    # 3. Run Process C (fresh full scientific replay and verification)
    p_c = subprocess.run(
        [sys.executable, str(script_path), "process_c", str(tmp_path)],
        capture_output=True,
        env=sub_env,
    )
    assert p_c.returncode == 0, p_c.stderr.decode()


def test_p3f_adversarial_matrix_and_error_paths(tmp_path: Path) -> None:
    """F-R5.4: Explicit adversarial failure checks."""
    env = _screen_env(tmp_path)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    state = env["aggregate"].reducer_state
    window = env["window"]

    # 1. Structural check: Eval2Role requires snapshot and evaluation_data_digest
    lane = _CandidateLane(env, tmp_path, definition.qualified_candidate_sizes[0], 1)
    mat = lane.materialize(env, tmp_path)
    b_state = lane.train_to_boundary(env, 1)

    eval_artifact = write_target_size_evaluation_artifact(
        tmp_path / "eval_data_adv",
        definition=definition,
        evaluation_size=definition.policy.evaluation_sizes[0],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )

    # Passing mutable TargetSizeBoundaryState instead of TargetSizeBoundarySnapshot is rejected
    with pytest.raises(mdstats.TrainingDataInputError):
        build_target_size_eval2_role(
            trajectory=lane.trajectory,
            boundary_state=b_state,  # type: ignore
            definition=definition,
            schedule=schedule,
            correlation_blocks=env["blocks"],
            evaluation_data=eval_artifact,
        )

    snapshot = promote_target_size_boundary_snapshot(
        lane.trajectory,
        b_state,
        checkpoint_directory=lane.checkpoint_dir,
        snapshot_root=env["root"],
    )

    role = build_target_size_eval2_role(
        trajectory=lane.trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=schedule,
        correlation_blocks=env["blocks"],
        evaluation_data=eval_artifact,
    )

    # 2. Forged Evaluation view is rejected during reduction
    from types import SimpleNamespace
    fake_view = SimpleNamespace(
        evaluation_view_digest=eval_artifact.evaluation_view_digest,
        configuration_count=eval_artifact.evaluation_size,
    )
    eval_dir = tmp_path / "eval_data_adv"
    evaluator = p3d._predictions_evaluator(eval_artifact.build_evaluation_view(eval_dir), epsilon=1e-3)
    pred_evidence = run_target_size_direct_boundary_inference(
        trajectory=lane.trajectory,
        materialization=mat,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=schedule,
        optimizer_policy=lane.policy,
        materialization_directory=tmp_path / f"mat-{lane.trajectory.target_size}-{lane.trajectory.optimizer_seed}",
        snapshot_root=env["root"],
        evaluation_directory=eval_dir,
        inference_evaluator=evaluator,
    )

    with pytest.raises((mdstats.TrainingDataInputError, TypeError)):
        run_target_size_eval2_reduction(
            role,
            eval_artifact,
            pred_evidence,
            root_directory=eval_dir,
            evaluation_view=fake_view,  # type: ignore
        )

    # 3. Mismatched resolver filename vs content digest is rejected
    metric_rec = run_target_size_eval2_reduction(role, eval_artifact, pred_evidence, root_directory=eval_dir)
    comp = build_target_size_cell_completion_record(
        window=window,
        trajectory=lane.trajectory,
        materialization=mat,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        outcome=evaluate_target_size_boundary(role, eval_artifact, pred_evidence, root_directory=eval_dir),
        prediction_evidence=pred_evidence,
        eval2_metric_record=metric_rec,
    )
    record_candidate_boundary_outcome(
        env["root"],
        window,
        lane.trajectory,
        comp,
        materialization=mat,
        boundary_snapshot=snapshot,
        eval2_role=role,
        evaluation_data=eval_artifact,
        prediction_evidence=pred_evidence,
        eval2_metric_record=metric_rec,
    )
    # Tamper with snapshot filename stem
    snap_file = env["root"] / "snapshots" / f"{snapshot.content_digest}.json"
    wrong_snap_file = env["root"] / "snapshots" / f"{'1' * 64}.json"
    wrong_snap_file.write_text(snap_file.read_text())
    with pytest.raises(mdstats.TrainingDataInputError):
        reconcile_target_size_screen_root(
            env["root"], env["aggregate"], env["context"], env["common"], schedule=schedule
        )
    wrong_snap_file.unlink()


