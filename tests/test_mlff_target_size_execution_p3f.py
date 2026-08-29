"""P3-F gate evidence: bounded end-to-end through real owners and the
mandatory structural/absence inspection of the assembled P3 path."""

from __future__ import annotations

import ast
import inspect
import json
from dataclasses import replace
from pathlib import Path

import mdstats
import mdstats.training_data as training_data_pkg
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
import mdstats.training_data.target_size_execution as tee
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    bind_target_size_boundary_state,
    build_complete_boundary_batch,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    collect_boundary_candidate_outcomes,
    commit_target_size_boundary_batch,
    continuation_request_from_boundary,
    derive_active_boundary_requirements,
    evaluate_target_size_boundary,
    initial_target_size_continuation_request,
    initialize_target_size_screen,
    load_current_execution_head,
    materialize_target_size_candidate,
    persist_complete_boundary_batch,
    reconcile_target_size_screen_root,
    record_candidate_boundary_outcome,
    target_size_population_correlation_blocks,
    target_size_rung_plan,
    validate_target_size_continuation_request,
)
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_experiment import ReducerStatus
from mdstats.training_data.neutral_substrate import build_neutral_split_exclusion_evidence


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
    root.mkdir()
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
        self.checkpoint_dir.mkdir()
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
        for size, seed in keys:
            if (size, seed) not in lanes:
                lanes[(size, seed)] = _CandidateLane(env, tmp_path, size, seed)
            lane = lanes[(size, seed)]
            # Current-generation exact export/materialization (real owner).
            if (size, seed) not in materialized:
                materialized[(size, seed)] = lane.materialize(env, tmp_path)
            # TRAIN2 to the exact completed boundary, via real continuation.
            boundary_state = lane.train_to_boundary(env, boundary)
            role = build_target_size_eval2_role(
                trajectory=lane.trajectory,
                boundary_state=boundary_state,
                definition=definition,
                schedule=schedule,
                correlation_blocks=env["blocks"],
            )
            # Exact-checkpoint EVAL2 on the exact active M_i membership.
            assert role.evaluation_size == definition.policy.evaluation_sizes[boundary_index]
            view = p3d._view_for(
                env,
                tmp_path,
                tuple(role.evaluation_frame_uids),
                name=f"f1-view-{size}-{seed}-{boundary}",
            )
            predictions = p3d._predictions_for(view, epsilon=_epsilon(size, seed))
            outcome = evaluate_target_size_boundary(role, view, predictions)
            record_candidate_boundary_outcome(
                env["root"], env["window"], lane.trajectory, outcome
            )
        collected = collect_boundary_candidate_outcomes(
            env["root"], env["window"], boundary_epoch=boundary
        )
        cells[boundary] = [
            (outcome.target_size, outcome.optimizer_seed,
             outcome.target_force_rmse_mev_per_a
             if isinstance(outcome, mdstats.TargetSizeBoundaryMetric) else None)
            for outcome in collected
        ]
        batch = build_complete_boundary_batch(definition, state, collected)
        # Crash-crisp order: batch persisted before commit in a mixed run.
        persist_complete_boundary_batch(env["root"], batch)
        if boundary == schedule.fidelity_epochs[1]:
            # Simulate a crash between batch persistence and head publication:
            # reconciliation must apply exactly once and publish the head.
            repaired = reconcile_target_size_screen_root(
                env["root"], env["aggregate"], env["context"], env["common"]
            )
            head = repaired
        else:
            head = commit_target_size_boundary_batch(env["root"], definition, state, batch)
        committed_heads.append(head)
        # Restart/reopen reproduces exactly this accepted state.
        opened = reconcile_target_size_screen_root(
            env["root"], env["aggregate"], env["context"], env["common"]
        )
        assert opened.content_digest == head.content_digest
        state = head.post_state

    assert state.is_terminal
    assert state.status is ReducerStatus.SELECTED
    assert len(committed_heads) == len(schedule.fidelity_epochs)
    # Exact terminal identity comes only from the P2 terminal state.
    selected_digest = definition.training_order.candidate_digest(
        state.selected_target_size
    )
    assert state.selected_membership_digest == selected_digest
    assert lanes[(state.selected_target_size, definition.policy.optimizer_seeds[0])].continuation_epochs == list(
        schedule.fidelity_epochs
    )
    # Every lane observed the exact completed epochs; the raw checkpoint index
    # is exactly n_i - 1 throughout.
    for lane in lanes.values():
        assert lane.continuation_epochs and lane.continuation_epochs[0] == schedule.fidelity_epochs[0]
    # Restart/reopen after terminal: reproduce identical accepted state and
    # replay the complete history through the P2 owner.
    final_head = reconcile_target_size_screen_root(
        env["root"], env["aggregate"], env["context"], env["common"]
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
    from mdstats.training_data import target_size_execution as pkg
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
    # Not declared in the production namespace contract.
    assert "target_size_execution" not in training_data_pkg.__all__
    import ast as _ast
    import inspect as _inspect

    import re

    init_source = _inspect.getsource(training_data_pkg)
    assert not re.search(r"(?<![\w])target_size_execution(?![\w])", init_source)
    # A pristine interpreter importing the production package must not see it.
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
    # No production CLI/campaign runtime references the P3 package.
    import re as _re
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
        assert not _re.search(r"(?<![\w])target_size_execution(?![\w])", source)


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
    role = build_target_size_eval2_role(
        trajectory=lane.trajectory,
        boundary_state=boundary_state,
        definition=definition,
        schedule=schedule,
        correlation_blocks=env["blocks"],
    )

    payloads = [
        env["window"].to_dict(),
        env["context"].to_dict(),
        env["context"].policy_digest_payload() if hasattr(env["context"], "policy_digest_payload") else {},
        lane.trajectory.to_dict(),
        lane.trajectory.realization.to_dict(),
        materialization.to_dict(),
        boundary_state.to_dict(),
        role.to_dict(),
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
    # Scientific identity fields exist and are digest-shaped where expected.
    text = json.dumps(lane.trajectory.to_dict())
    assert "candidate_membership_digest" in text
    assert "optimizer_seed" in text
