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
    TargetSizeEval2Role,
    bind_target_size_boundary_state,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    evaluate_target_size_boundary,
    run_target_size_eval2_reduction,
    target_size_boundary_metric_from_eval2_record,
    target_size_eval2_prediction_digest,
    target_size_population_correlation_blocks,
    target_size_rung_plan,
    translate_target_size_eval2_failure,
    write_target_size_extxyz_artifact,
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
    checkpoint_dir.mkdir()
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


def _view_for(env, tmp_path: Path, frame_uids: tuple[str, ...], *, name: str):
    aggregate = env["aggregate"]
    artifact = write_target_size_extxyz_artifact(
        tmp_path / name,
        dataset_id=env["frame_authority"].dataset_id,
        role="target_train",
        filename=f"{name}.extxyz",
        frame_uids=frame_uids,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        membership_digest="a" * 64,
        common_preparation_digest=env["common"].content_digest,
        training_weights=None,
        frame_array_index=env["index"],
    )
    del aggregate
    atoms = ase.io.read(str(tmp_path / name / artifact.relative_path), index=":")
    return build_evaluation_dataset_view(
        atoms,
        energy_key=MaceExtxyzPolicy().energy_key,
        forces_key=MaceExtxyzPolicy().forces_key,
        stress_key=MaceExtxyzPolicy().stress_key,
        focus_atomic_numbers=(),
        condition_keys=(),
    )


def _predictions_for(view, *, epsilon: float = 2.5e-3):
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


def test_p3d_exact_m_ladder_roles_and_digests(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate = env["aggregate"]
    definition = aggregate.definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    for boundary in env["schedule"].fidelity_epochs:
        state = _boundary_state(env, tmp_path, boundary, name=f"ckpt-{boundary}")
        role = build_target_size_eval2_role(
            trajectory=env["trajectory"],
            boundary_state=state,
            definition=definition,
            schedule=env["schedule"],
            correlation_blocks=blocks,
        )
        index = env["schedule"].fidelity_epochs.index(boundary)
        evaluation_size = definition.policy.evaluation_sizes[index]
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
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state1,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
    )
    # The same authenticated boundary yields the identical role.
    assert (
        build_target_size_eval2_role(
            trajectory=env["trajectory"],
            boundary_state=state1_again,
            definition=definition,
            schedule=env["schedule"],
            correlation_blocks=blocks,
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
        )
    # A different boundary epoch of the same trajectory is a different role:
    # there is no checkpoint-selection surface to confuse the two.
    state10 = _boundary_state(env, tmp_path, 10, name="ckpt-c")
    role10 = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state10,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
    )
    assert role10.evaluation_size == definition.policy.evaluation_sizes[2]
    assert role10.content_digest != role.content_digest


def test_p3d_exact_mev_conversion_and_reference_equivalence(tmp_path: Path) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    state = _boundary_state(env, tmp_path, 1)
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
    )
    view = _view_for(env, tmp_path, tuple(role.evaluation_frame_uids), name="m1-view")
    epsilon = 2.5e-3
    predictions = _predictions_for(view, epsilon=epsilon)
    outcome = evaluate_target_size_boundary(role, view, predictions)
    assert isinstance(outcome, mdstats.TargetSizeBoundaryMetric)
    # Every force component shifted by exactly epsilon.
    assert math.isclose(
        outcome.target_force_rmse_mev_per_a, epsilon * 1000.0, rel_tol=1e-12
    )
    # The EVAL2 record reduces identically to a hand oracle.
    record = run_target_size_eval2_reduction(role, view, predictions)
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
    # Correlation-block reductions agree with the same closed form.
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
    # The frozen transfer applies only the *1000 conversion and exact lineage.
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
    # M1/M2 are exact prefixes of M3: each frame retains its full parent
    # component identity across rungs.
    for index in range(1, 3):
        assert memberships[index - 1] == memberships[index][: m_sizes[index - 1]]
    for membership, size in zip(memberships, m_sizes):
        assert len(membership) == size
        for uid in membership:
            assert blocks[uid] in aggregate.split.constraint_component_digests
    # No prefix-local names: the same frame has the same identity on every rung.
    assert blocks[memberships[0][0]] == blocks[memberships[2][0]]
    # Mixed-relation transitive closure through the shared canonical owner.
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
    # Non-binding evidence is rejected.
    with pytest.raises(mdstats.TrainingDataInputError):
        project_split_exclusion_constraint_components(
            uids,
            evidence,
            frame_authority_digest="0" * 64,
            neutral_unit_catalog_digest="b" * 64,
        )
    # Evidence that does not bind the accepted P2 split is rejected.
    with pytest.raises(mdstats.TrainingDataInputError):
        target_size_population_correlation_blocks(aggregate, evidence)


def test_p3d_direct_role_payload_carries_no_legacy_selection_semantics(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    definition = env["aggregate"].definition
    blocks = target_size_population_correlation_blocks(env["aggregate"], env["evidence"])
    state = _boundary_state(env, tmp_path, 1)
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
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
    # There is exactly one selection-free decision surface: the role derives
    # the boundary and evaluation membership from the authenticated state.
    import inspect

    signature = inspect.signature(build_target_size_eval2_role)
    assert "checkpoint" not in str(signature)
    assert "shortlist" not in str(signature)
    assert "evaluation_size" not in inspect.signature(
        build_target_size_eval2_role
    ).parameters
    # An artificially better earlier checkpoint cannot alter the outcome
    # lineage: the metric binds the exact role/checkpoint boundary state.
    view = _view_for(env, tmp_path, tuple(role.evaluation_frame_uids), name="m1")
    better = _predictions_for(view, epsilon=0.0)
    worse = _predictions_for(view, epsilon=9.5e-2)
    better_metric = evaluate_target_size_boundary(role, view, better)
    worse_metric = evaluate_target_size_boundary(role, view, worse)
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
    state = _boundary_state(env, tmp_path, 1)
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=state,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=blocks,
    )
    view = _view_for(env, tmp_path, tuple(role.evaluation_frame_uids), name="m1")
    predictions = _predictions_for(view)
    broken = _predictions_for(view)
    broken[0].forces_ev_per_angstrom[0, 2] = float("nan")
    outcome = evaluate_target_size_boundary(role, view, broken)
    assert isinstance(outcome, mdstats.TargetSizeNumericalFailure)
    assert outcome.kind is NumericalFailureKind.EVAL_NONFINITE_PREDICTION
    assert outcome.boundary_epoch == role.boundary_epoch
    assert outcome.target_size == role.target_size
    assert outcome.optimizer_seed == role.optimizer_seed
    assert outcome.evaluation_membership_digest == role.evaluation_membership_digest
    # Energy prediction non-finiteness maps to the same prediction category.
    broken_energy = _predictions_for(view)
    broken_energy[0].energy_ev = float("inf")
    energy_outcome = evaluate_target_size_boundary(role, view, broken_energy)
    assert energy_outcome.kind is NumericalFailureKind.EVAL_NONFINITE_PREDICTION
    assert energy_outcome.content_digest != outcome.content_digest
    # A failure not bound to this role is an execution error.
    foreign = Eval2NumericalEvaluationError(
        "eval_nonfinite_force_prediction",
        "foreign role",
        target_role_digest="0" * 64,
        prediction_digest="1" * 64,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        translate_target_size_eval2_failure(role, foreign)
    # Shape/lineage errors remain ordinary execution errors.
    wrong_shape = _predictions_for(view)
    wrong_shape[0].forces_ev_per_angstrom = np.zeros((1, 3))
    with pytest.raises(mdstats.TrainingDataInputError):
        evaluate_target_size_boundary(role, view, wrong_shape)
    # Prediction populations that do not match the exact M-membership are rejected.
    with pytest.raises(mdstats.TrainingDataInputError):
        evaluate_target_size_boundary(role, view, predictions + list(predictions))
