"""P3-D gate evidence: direct exact-checkpoint EVAL2 on exact P2 M_i
memberships with canonical P1 correlation blocks and the frozen metric
transfer."""

from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import ase.io
import numpy as np
import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
from mdstats.training_data.eval2 import Eval2NumericalEvaluationError
from mdstats.training_data.evaluation_views import build_evaluation_dataset_view
from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.neutral_substrate import (
    NeutralSplitExclusionEvidence,
    NeutralSplitExclusionGroup,
    build_neutral_split_exclusion_evidence,
    frame_split_exclusion_component_membership,
    project_split_exclusion_constraint_components,
)
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TARGET_SIZE_BOUNDARY_SNAPSHOT_SCHEMA,
    TARGET_SIZE_EVALUATION_ARTIFACT_SCHEMA,
    TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA,
    TargetSizeBoundarySnapshot,
    TargetSizeBoundaryState,
    TargetSizeEval2Role,
    TargetSizeEvaluationArtifact,
    TargetSizePredictionEntry,
    TargetSizePredictionEvidence,
    bind_target_size_boundary_state,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    evaluate_target_size_boundary,
    materialize_target_size_candidate,
    promote_target_size_boundary_snapshot,
    run_target_size_direct_boundary_inference,
    run_target_size_eval2_reduction,
    target_size_boundary_metric_from_eval2_record,
    target_size_eval2_prediction_digest,
    target_size_population_correlation_blocks,
    target_size_rung_plan,
    translate_target_size_eval2_failure,
    validate_target_size_boundary_snapshot,
    validate_target_size_evaluation_artifact,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.common import (
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_experiment import NumericalFailureKind


def _env(tmp_path: Path):
    manifest, frame_authority, neutral_base, aggregate, common, index = p3a._common(
        tmp_path
    )
    frames, frame_data_by_run, _ = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule((1, 3, 10))
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    context = build_target_size_execution_context(
        aggregate.definition, common, schedule, seed_neutral_optimizer_policy=optimizer
    )
    trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=aggregate.definition.qualified_candidate_sizes[0],
        optimizer_policy=optimizer,
        optimizer_seed=1,
    )
    evidence = build_neutral_split_exclusion_evidence(frame_authority, neutral_base)
    return {
        "frame_authority": frame_authority,
        "neutral_base": neutral_base,
        "aggregate": aggregate,
        "common": common,
        "index": index,
        "frames": frames,
        "frame_data_by_run": frame_data_by_run,
        "schedule": schedule,
        "context": context,
        "trajectory": trajectory,
        "optimizer": optimizer,
        "evidence": evidence,
    }


def _boundary_state(env, tmp_path: Path, boundary: int, *, name: str = "checkpoints"):
    trajectory, schedule = env["trajectory"], env["schedule"]
    checkpoint_dir = tmp_path / name
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    plan = target_size_rung_plan(trajectory, schedule, boundary_epoch=boundary)
    _runtime, summary, _restored, _rng = p3c._run_rung(
        plan,
        checkpoint_dir,
        start_epoch=0,
        updates_per_epoch=trajectory.realization.updates_per_epoch,
        seed=1,
    )
    return bind_target_size_boundary_state(
        trajectory, schedule, summary, checkpoint_directory=checkpoint_dir
    )


def _eval_artifact_for(env, tmp_path: Path, evaluation_size: int, *, name: str):
    out_dir = tmp_path / name
    out_dir.mkdir(parents=True, exist_ok=True)
    return write_target_size_evaluation_artifact(
        out_dir,
        definition=env["aggregate"].definition,
        evaluation_size=evaluation_size,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )


def _materialization_for(env, tmp_path: Path):
    definition = env["aggregate"].definition
    trajectory = env["trajectory"]
    projection = project_target_size_candidate_preparation(
        env["common"], definition, trajectory.target_size
    )
    out_dir = tmp_path / "materialization"
    out_dir.mkdir(parents=True, exist_ok=True)
    return materialize_target_size_candidate(
        trajectory,
        projection,
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=out_dir,
        optimizer_policy=env["optimizer"],
        frame_array_index=env["index"],
    )


def _predictions_evaluator(view, *, epsilon: float = 2.5e-3):
    def _eval(boundary_state, atoms_list):
        predictions = []
        for frame_index in range(view.configuration_count):
            start = int(view.force_offsets[frame_index])
            stop = int(view.force_offsets[frame_index + 1])
            stress = (
                np.asarray(view.reference_stresses[frame_index], dtype=np.float64)
                if bool(view.stress_present[frame_index])
                else None
            )
            stress_3x3 = None
            if stress is not None:
                stress_3x3 = np.array(
                    [
                        [stress[0], stress[5], stress[4]],
                        [stress[5], stress[1], stress[3]],
                        [stress[4], stress[3], stress[2]],
                    ]
                )
            predictions.append(
                SimpleNamespace(
                    energy_ev=float(view.reference_energies[frame_index]),
                    forces_ev_per_angstrom=np.asarray(
                        view.reference_forces[start:stop], dtype=np.float64
                    )
                    + epsilon,
                    stress_ev_per_angstrom3=stress_3x3,
                )
            )
        return predictions

    return _eval


def test_p3d_exact_m_ladder_roles_and_digests(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate = env["aggregate"]
    definition = aggregate.definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    for boundary in env["schedule"].fidelity_epochs:
        state = _boundary_state(env, tmp_path, boundary, name=f"ckpt-{boundary}")
        index = env["schedule"].fidelity_epochs.index(boundary)
        evaluation_size = definition.policy.evaluation_sizes[index]
        eval_artifact = _eval_artifact_for(
            env, tmp_path, evaluation_size, name=f"eval-art-{boundary}"
        )
        role = build_target_size_eval2_role(
            trajectory=env["trajectory"],
            boundary_state=state,
            definition=definition,
            schedule=env["schedule"],
            correlation_blocks=blocks,
            evaluation_data=eval_artifact,
        )
        assert role.evaluation_size == evaluation_size
        assert role.evaluation_frame_uids == definition.evaluation_membership(
            evaluation_size
        )
        assert role.evaluation_membership_digest == (
            definition.evaluation_order.membership_digest(evaluation_size)
        )
        assert role.boundary_epoch == boundary
        assert role.boundary_state_digest == state.content_digest
        assert role.target_size == env["trajectory"].target_size
        assert role.optimizer_seed == env["trajectory"].optimizer_seed
        assert len(role.correlation_block_ids) == evaluation_size
        assert role.evaluation_data_digest == eval_artifact.content_digest
        # Block identities come from canonical P1 split components.
        assert set(role.correlation_block_ids) <= set(
            aggregate.split.constraint_component_digests
        )
        assert TargetSizeEval2Role.from_dict(role.to_dict()).content_digest == (
            role.content_digest
        )


def test_p3d_role_authenticates_exact_boundary_checkpoint_identity(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    state1 = _boundary_state(env, tmp_path, 1, name="ckpt-a")
    state1_again = _boundary_state(env, tmp_path, 1, name="ckpt-b")
    eval_artifact1 = _eval_artifact_for(env, tmp_path, 1, name="eval-1")
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state1,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact1,
    )
    # The same authenticated boundary yields the identical role.
    assert (
        build_target_size_eval2_role(
            trajectory=env["trajectory"],
            boundary_state=state1_again,
            definition=definition,
            schedule=env["schedule"],
            correlation_blocks=blocks,
            evaluation_data=eval_artifact1,
        ).content_digest
        == role.content_digest
    )
    # A boundary state from another trajectory is rejected.
    other = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=env["trajectory"].target_size,
        optimizer_policy=replace(env["optimizer"], seed=2),
        optimizer_seed=2,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        build_target_size_eval2_role(
            trajectory=env["trajectory"],
            boundary_state=replace(state1, trajectory_digest=other.content_digest),
            definition=definition,
            schedule=env["schedule"],
            correlation_blocks=blocks,
            evaluation_data=eval_artifact1,
        )
    # A different boundary epoch of the same trajectory is a different role.
    state10 = _boundary_state(env, tmp_path, 10, name="ckpt-c")
    eval_artifact10 = _eval_artifact_for(env, tmp_path, definition.policy.evaluation_sizes[2], name="eval-10")
    role10 = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state10,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact10,
    )
    assert role10.evaluation_size == definition.policy.evaluation_sizes[2]
    assert role10.content_digest != role.content_digest


def test_p3d_exact_mev_conversion_and_reference_equivalence(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    state = _boundary_state(env, tmp_path, 1, name="ckpt-mev")
    snapshot = promote_target_size_boundary_snapshot(
        env["trajectory"],
        state,
        checkpoint_directory=tmp_path / "ckpt-mev",
        snapshot_root=tmp_path / "snap_root_mev",
    )
    eval_artifact = _eval_artifact_for(env, tmp_path, 1, name="eval-mev")
    materialization = _materialization_for(env, tmp_path)
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact,
    )
    view = eval_artifact.build_evaluation_view(tmp_path / "eval-mev")
    epsilon = 2.5e-3
    evaluator = _predictions_evaluator(view, epsilon=epsilon)
    pred_evidence = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_mev",
        evaluation_directory=tmp_path / "eval-mev",
        inference_evaluator=evaluator,
    )
    assert pred_evidence.role_digest == role.content_digest
    assert pred_evidence.evaluation_data_digest == eval_artifact.content_digest
    assert pred_evidence.prediction_count == role.evaluation_size

    outcome = evaluate_target_size_boundary(
        role, eval_artifact, pred_evidence, root_directory=tmp_path / "eval-mev"
    )
    assert isinstance(outcome, mdstats.TargetSizeBoundaryMetric)
    assert math.isclose(
        outcome.target_force_rmse_mev_per_a, epsilon * 1000.0, rel_tol=1e-12
    )

    record = run_target_size_eval2_reduction(
        role, eval_artifact, pred_evidence, root_directory=tmp_path / "eval-mev"
    )
    total_sse = sum(
        3.0 * int(view.atom_counts[i]) * epsilon * epsilon
        for i in range(view.configuration_count)
    )
    total_components = sum(3 * int(view.atom_counts[i]) for i in range(view.configuration_count))
    assert math.isclose(
        record.force_component_rmse_ev_per_angstrom,
        math.sqrt(total_sse / total_components),
        rel_tol=1e-12,
    )
    for block in record.block_metrics:
        assert math.isclose(
            block.force_rmse_ev_per_angstrom, epsilon, rel_tol=1e-12
        )
        assert math.isclose(
            block.force_squared_error_sum,
            block.force_component_count * epsilon * epsilon,
            rel_tol=1e-12,
        )
    assert record.target_role_digest == role.content_digest
    metric = target_size_boundary_metric_from_eval2_record(role, record)
    assert metric.evaluation_membership_digest == role.evaluation_membership_digest
    assert metric.boundary_epoch == role.boundary_epoch


def test_p3d_blocks_stable_across_m_rungs_and_transitive_chains(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate = env["aggregate"]
    definition = aggregate.definition
    blocks = target_size_population_correlation_blocks(aggregate, env["evidence"])
    m_sizes = definition.policy.evaluation_sizes
    memberships = [definition.evaluation_membership(m) for m in m_sizes]
    for index in range(1, 3):
        assert memberships[index - 1] == memberships[index][: m_sizes[index - 1]]
    for membership, size in zip(memberships, m_sizes):
        assert len(membership) == size
        for uid in membership:
            assert blocks[uid] in aggregate.split.constraint_component_digests
    assert blocks[memberships[0][0]] == blocks[memberships[2][0]]
    uids = tuple(f"{c}" * 64 for c in "1234")
    evidence = NeutralSplitExclusionEvidence(
        dataset_id="synthetic",
        frame_authority_digest="a" * 64,
        unit_catalog_digest="b" * 64,
        groups=(
            NeutralSplitExclusionGroup(
                relation_kind="correlation_unit", relation_key="c" * 64, frame_uids=(uids[0], uids[1])
            ),
            NeutralSplitExclusionGroup(
                relation_kind="geometry_duplicate", relation_key="d" * 64, frame_uids=(uids[1], uids[2])
            ),
        ),
    )
    components = project_split_exclusion_constraint_components(
        uids,
        evidence,
        frame_authority_digest="a" * 64,
        neutral_unit_catalog_digest="b" * 64,
    )
    assert set(components) == {tuple(sorted(uids[:3])), (uids[3],)}
    assignment = dict(
        frame_split_exclusion_component_membership(
            uids,
            evidence,
            frame_authority_digest="a" * 64,
            neutral_unit_catalog_digest="b" * 64,
        )
    )
    assert assignment[uids[0]] == assignment[uids[2]]
    assert assignment[uids[3]] != assignment[uids[0]]
    with pytest.raises(mdstats.TrainingDataInputError):
        project_split_exclusion_constraint_components(
            uids,
            evidence,
            frame_authority_digest="0" * 64,
            neutral_unit_catalog_digest="b" * 64,
        )
    with pytest.raises(mdstats.TrainingDataInputError):
        target_size_population_correlation_blocks(aggregate, evidence)


def test_p3d_direct_role_payload_carries_no_legacy_selection_semantics(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    state = _boundary_state(env, tmp_path, 1, name="ckpt-legacy")
    snapshot = promote_target_size_boundary_snapshot(
        env["trajectory"],
        state,
        checkpoint_directory=tmp_path / "ckpt-legacy",
        snapshot_root=tmp_path / "snap_root_legacy",
    )
    eval_artifact = _eval_artifact_for(env, tmp_path, 1, name="eval-legacy")
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact,
    )
    forbidden = {
        "label_domain_id",
        "cv_fold",
        "fold_index",
        "complement",
        "coarse_fallback",
        "development_complement",
        "excluded_prefix",
        "selected_checkpoint",
        "shortlist",
        "rescue",
        "replay_admissibility",
        "bootstrap",
        "role_version",
        "role_freeze",
        "harness_validation",
    }
    payload_text = json.dumps(role.to_dict())
    for token in forbidden:
        assert token not in payload_text

    import inspect
    signature = inspect.signature(build_target_size_eval2_role)
    assert "checkpoint" not in str(signature)
    assert "shortlist" not in str(signature)

    materialization = _materialization_for(env, tmp_path)
    view = eval_artifact.build_evaluation_view(tmp_path / "eval-legacy")
    better_eval = _predictions_evaluator(view, epsilon=0.0)
    worse_eval = _predictions_evaluator(view, epsilon=9.5e-2)
    better_pred = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_legacy",
        evaluation_directory=tmp_path / "eval-legacy",
        inference_evaluator=better_eval,
    )
    worse_pred = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_legacy",
        evaluation_directory=tmp_path / "eval-legacy",
        inference_evaluator=worse_eval,
    )
    better_metric = evaluate_target_size_boundary(
        role, eval_artifact, better_pred, root_directory=tmp_path / "eval-legacy"
    )
    worse_metric = evaluate_target_size_boundary(
        role, eval_artifact, worse_pred, root_directory=tmp_path / "eval-legacy"
    )
    assert worse_metric.target_force_rmse_mev_per_a > (
        better_metric.target_force_rmse_mev_per_a
    )
    assert better_metric.content_digest != worse_metric.content_digest


def test_p3d_eval2_failure_translation_and_execution_error_separation(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    state = _boundary_state(env, tmp_path, 1, name="ckpt-fail")
    snapshot = promote_target_size_boundary_snapshot(
        env["trajectory"],
        state,
        checkpoint_directory=tmp_path / "ckpt-fail",
        snapshot_root=tmp_path / "snap_root_fail",
    )
    eval_artifact = _eval_artifact_for(env, tmp_path, 1, name="eval-fail")
    materialization = _materialization_for(env, tmp_path)
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact,
    )
    view = eval_artifact.build_evaluation_view(tmp_path / "eval-fail")

    def _broken_force_eval(bs, atoms):
        preds = _predictions_evaluator(view)(bs, atoms)
        preds[0].forces_ev_per_angstrom[0, 2] = float("nan")
        return preds

    broken_pred = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_fail",
        evaluation_directory=tmp_path / "eval-fail",
        inference_evaluator=_broken_force_eval,
    )
    outcome = evaluate_target_size_boundary(
        role, eval_artifact, broken_pred, root_directory=tmp_path / "eval-fail"
    )
    assert isinstance(outcome, mdstats.TargetSizeNumericalFailure)
    assert outcome.kind is NumericalFailureKind.EVAL_NONFINITE_PREDICTION
    assert outcome.boundary_epoch == role.boundary_epoch
    assert outcome.target_size == role.target_size
    assert outcome.optimizer_seed == role.optimizer_seed
    assert outcome.evaluation_membership_digest == role.evaluation_membership_digest

    def _broken_energy_eval(bs, atoms):
        preds = _predictions_evaluator(view)(bs, atoms)
        preds[0].energy_ev = float("inf")
        return preds

    broken_energy_pred = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_fail",
        evaluation_directory=tmp_path / "eval-fail",
        inference_evaluator=_broken_energy_eval,
    )
    energy_outcome = evaluate_target_size_boundary(
        role, eval_artifact, broken_energy_pred, root_directory=tmp_path / "eval-fail"
    )
    assert energy_outcome.kind is NumericalFailureKind.EVAL_NONFINITE_PREDICTION
    assert energy_outcome.content_digest != outcome.content_digest

    foreign = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "foreign role",
        target_role_digest="0" * 64,
        prediction_digest="1" * 64,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        translate_target_size_eval2_failure(role, foreign)

    # Negative inference tests:
    # 1. Foreign trajectory
    other_traj = build_target_size_candidate_trajectory(
        definition,
        env["context"],
        env["common"],
        env["schedule"],
        target_size=env["trajectory"].target_size,
        optimizer_policy=replace(env["optimizer"], seed=2),
        optimizer_seed=2,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        run_target_size_direct_boundary_inference(
            trajectory=other_traj,
            materialization=materialization,
            boundary_state=snapshot,
            role=role,
            evaluation_data=eval_artifact,
            canonical_frame_authority=env["frame_authority"],
            definition=definition,
            context=env["context"],
            common=env["common"],
            schedule=env["schedule"],
            optimizer_policy=env["optimizer"],
            materialization_directory=tmp_path / "materialization",
            snapshot_root=tmp_path / "snap_root_fail",
            evaluation_directory=tmp_path / "eval-fail",
            inference_evaluator=_predictions_evaluator(view),
        )
    # 2. Foreign evaluation data
    eval_artifact_m2 = _eval_artifact_for(
        env, tmp_path, definition.policy.evaluation_sizes[1], name="eval-m2"
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        run_target_size_direct_boundary_inference(
            trajectory=env["trajectory"],
            materialization=materialization,
            boundary_state=snapshot,
            role=role,
            evaluation_data=eval_artifact_m2,
            canonical_frame_authority=env["frame_authority"],
            definition=definition,
            context=env["context"],
            common=env["common"],
            schedule=env["schedule"],
            optimizer_policy=env["optimizer"],
            materialization_directory=tmp_path / "materialization",
            snapshot_root=tmp_path / "snap_root_fail",
            evaluation_directory=tmp_path / "eval-m2",
            inference_evaluator=_predictions_evaluator(view),
        )


def test_p3d_boundary_snapshot_promotion_and_validation(tmp_path: Path) -> None:
    env = _env(tmp_path)
    state = _boundary_state(env, tmp_path, 1, name="ckpt-snap")
    snapshot = promote_target_size_boundary_snapshot(
        env["trajectory"],
        state,
        checkpoint_directory=tmp_path / "ckpt-snap",
        snapshot_root=tmp_path / "snap_root",
    )
    assert snapshot.boundary_epoch == 1
    assert snapshot.trajectory_digest == env["trajectory"].content_digest

    # Validation succeeds on authentic snapshot
    summary = validate_target_size_boundary_snapshot(
        snapshot,
        snapshot_root=tmp_path / "snap_root",
        trajectory=env["trajectory"],
        schedule=env["schedule"],
    )
    assert summary.completed_epochs == 1

    # Tampered raw checkpoint fails
    raw_path = tmp_path / "snap_root" / snapshot.snapshot_relative_dir / snapshot.raw_checkpoint_name
    raw_bytes = raw_path.read_bytes()
    raw_path.write_bytes(raw_bytes + b"tamper")
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_boundary_snapshot(
            snapshot,
            snapshot_root=tmp_path / "snap_root",
            trajectory=env["trajectory"],
            schedule=env["schedule"],
        )
    raw_path.write_bytes(raw_bytes)

    # Tampered companion fails
    comp_path = tmp_path / "snap_root" / snapshot.snapshot_relative_dir / "train2_runtime.pt"
    comp_bytes = comp_path.read_bytes()
    comp_path.write_bytes(comp_bytes + b"tamper")
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_boundary_snapshot(
            snapshot,
            snapshot_root=tmp_path / "snap_root",
            trajectory=env["trajectory"],
            schedule=env["schedule"],
        )


def test_p3d_review3_prediction_evidence_immutability_and_authentication(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    state = _boundary_state(env, tmp_path, 1, name="ckpt-r3")
    snapshot = promote_target_size_boundary_snapshot(
        env["trajectory"],
        state,
        checkpoint_directory=tmp_path / "ckpt-r3",
        snapshot_root=tmp_path / "snap_root_r3",
    )
    eval_artifact = _eval_artifact_for(
        env,
        tmp_path,
        env["aggregate"].definition.policy.evaluation_sizes[0],
        name="eval-r3",
    )
    blocks = target_size_population_correlation_blocks(
        env["aggregate"], env["evidence"]
    )
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=snapshot,
        definition=env["aggregate"].definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact,
    )
    materialization = _materialization_for(env, tmp_path)
    view = eval_artifact.build_evaluation_view(tmp_path / "eval-r3")
    evaluator = _predictions_evaluator(view)

    # 1. Distinct locators test with mandatory authorities
    evidence = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=env["aggregate"].definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_r3",
        evaluation_directory=tmp_path / "eval-r3",
        inference_evaluator=evaluator,
    )
    assert evidence.prediction_count == role.evaluation_size

    # 2. Immutability test on prediction entry
    entry = evidence.predictions[0]
    assert entry.forces_ev_per_angstrom is not None
    assert not entry.forces_ev_per_angstrom.flags.writeable
    with pytest.raises(ValueError):
        entry.forces_ev_per_angstrom[0, 0] = 999.0

    # 3. Payload digest mismatch test on construction
    with pytest.raises(mdstats.TrainingDataInputError):
        replace(evidence, prediction_payload_digest="0" * 64)

    # 4. Recomputed payload digest equality
    from mdstats.training_data.target_size_execution import (
        target_size_eval2_prediction_digest_from_role_digest,
    )

    recomputed = target_size_eval2_prediction_digest_from_role_digest(
        role.content_digest, evidence.predictions
    )
    assert evidence.prediction_payload_digest == recomputed

    # 5. Snapshot promoter conflict detection on pre-existing differing raw checkpoint
    snap_dir = tmp_path / "snap_root_r3" / snapshot.snapshot_relative_dir
    fake_raw = snap_dir / snapshot.raw_checkpoint_name
    original_bytes = fake_raw.read_bytes()
    fake_raw.write_bytes(original_bytes + b"conflict")
    with pytest.raises(mdstats.TrainingDataInputError):
        promote_target_size_boundary_snapshot(
            env["trajectory"],
            state,
            checkpoint_directory=tmp_path / "ckpt-r3",
            snapshot_root=tmp_path / "snap_root_r3",
        )
    fake_raw.write_bytes(original_bytes)


def test_p3d_review3_evaluation_view_bypass_prevention(tmp_path: Path) -> None:
    env = _env(tmp_path)
    state = _boundary_state(env, tmp_path, 1, name="ckpt-bypass")
    snapshot = promote_target_size_boundary_snapshot(
        env["trajectory"],
        state,
        checkpoint_directory=tmp_path / "ckpt-bypass",
        snapshot_root=tmp_path / "snap_root_bypass",
    )
    eval_artifact = _eval_artifact_for(
        env,
        tmp_path,
        env["aggregate"].definition.policy.evaluation_sizes[0],
        name="eval-bypass",
    )
    blocks = target_size_population_correlation_blocks(
        env["aggregate"], env["evidence"]
    )
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=snapshot,
        definition=env["aggregate"].definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
        evaluation_data=eval_artifact,
    )
    view = eval_artifact.build_evaluation_view(tmp_path / "eval-bypass")
    evaluator = _predictions_evaluator(view)
    evidence = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=_materialization_for(env, tmp_path),
        boundary_state=snapshot,
        role=role,
        evaluation_data=eval_artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=env["aggregate"].definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "snap_root_bypass",
        evaluation_directory=tmp_path / "eval-bypass",
        inference_evaluator=evaluator,
    )

    # Reduction with matching view succeeds
    rec = run_target_size_eval2_reduction(
        role,
        eval_artifact,
        evidence,
        view=view,
    )
    assert rec.configuration_count == role.evaluation_size

    # Reduction with mismatched view digest fails
    fake_view = SimpleNamespace(
        evaluation_view_digest="0" * 64,
        configuration_count=role.evaluation_size,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        run_target_size_eval2_reduction(
            role,
            eval_artifact,
            evidence,
            view=fake_view,
        )

    # Generic view without evaluation_view_digest is rejected
    generic_view = SimpleNamespace(
        configuration_count=role.evaluation_size,
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="Generic EvaluationDatasetView"):
        run_target_size_eval2_reduction(
            role,
            eval_artifact,
            evidence,
            view=generic_view,
        )


def test_p3d_review4_exact_m_byte_and_frame_order_validation(tmp_path: Path) -> None:
    env = _env(tmp_path)
    eval_artifact = _eval_artifact_for(
        env,
        tmp_path,
        env["aggregate"].definition.policy.evaluation_sizes[0],
        name="eval-r4",
    )
    # Valid artifact passes
    validate_target_size_evaluation_artifact(
        eval_artifact,
        root_directory=tmp_path / "eval-r4",
        definition=env["aggregate"].definition,
        canonical_frame_authority=env["frame_authority"],
    )

    # Reordered ExtXYZ frames on disk must fail
    extxyz_file = tmp_path / "eval-r4" / eval_artifact.relative_path
    frames = ase.io.read(str(extxyz_file), index=":")
    if len(frames) > 1:
        reordered = list(reversed(frames))
        ase.io.write(str(extxyz_file), reordered)
        with pytest.raises(mdstats.TrainingDataInputError):
            validate_target_size_evaluation_artifact(
                eval_artifact,
                root_directory=tmp_path / "eval-r4",
                definition=env["aggregate"].definition,
                canonical_frame_authority=env["frame_authority"],
            )
        ase.io.write(str(extxyz_file), frames)
