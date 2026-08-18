from __future__ import annotations

import pytest

import mdstats
from mdstats.training_data._common import digest

SIZES = (128, 256, 512, 1024, 2048, 4096, 8192, 16384)


def _halve_plan(q: int = 8, *, ready: bool = True) -> mdstats.SizeHalve2Plan:
    qualified = SIZES[-q:]
    candidates = tuple(
        mdstats.SizeHalve2Candidate(
            target_size=size,
            materializable=True,
            hard_coverage_qualified=size in qualified,
            repair_rung_digests=(("labels", digest({"rung": size})),),
        )
        for size in SIZES
    )
    outcome = "ready_for_size_fidelity2" if ready else "blocked_insufficient_hard_coverage"
    if not ready:
        qualified = SIZES[-3:]
        candidates = tuple(
            mdstats.SizeHalve2Candidate(
                target_size=size, materializable=True, hard_coverage_qualified=size in qualified,
                repair_rung_digests=(("labels", digest({"rung": size})),),
            ) for size in SIZES
        )
    return mdstats.SizeHalve2Plan(
        dataset_id="synthetic",
        target_multi_view_repair_digest=digest({"repair": 1}),
        target_multi_view_qualification_digest=digest({"qual": 1}),
        policy=mdstats.SizeHalve2Policy(),
        candidates=candidates,
        coverage_qualified_sizes=qualified,
        outcome=outcome,
        decision_reason="fixture",
    )


def _ev(seed: int, size: int, epoch: int, score: float, *, parent=None, boundary_bad: bool = False):
    stage = {3: "coarse", 10: "short", 30: "final"}[epoch]
    kwargs = dict(
        stage=stage, target_size=size, optimizer_seed=seed, completed_epochs=epoch, planned_epochs=30,
        optimizer_update_count=epoch * 10 + size // 128,
        structures_presented=epoch * 100 + size,
        normalized_schedule_progress=epoch / 30.0,
        instantaneous_learning_rate=1.0e-3, wall_time_seconds=float(epoch),
        target_force_score_mev_per_a=float(score), numerical_valid=True, target_hard_gates_passed=True,
        foundation_identity_digest=digest({"foundation": 1}),
        evaluation_role_digest=digest({"role": "target-full"}),
        training_policy_digest=digest({"train2": 1}),
        training_run_digest=digest({"run": seed, "size": size}),
        checkpoint_digest=digest({"checkpoint": seed, "size": size, "epoch": epoch}),
        schedule_digest=digest({"schedule": 30}),
        optimizer_state_digest=digest({"optimizer": seed, "size": size, "epoch": epoch}),
        rng_state_digest=digest({"rng": seed, "size": size, "epoch": epoch}),
        target_evaluation_digest=digest({"eval": seed, "size": size, "epoch": epoch}),
    )
    if stage == "short":
        kwargs.update(
            replay_diagnostic_force_rmse_mev_per_a=10.0,
            replay_evaluation_digest=digest({"replaydiag": seed, "size": size, "epoch": epoch}),
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    elif stage == "final":
        kwargs.update(
            normalized_schedule_progress=1.0,
            replay_evaluation_digest=digest({"replay": seed, "size": size}), replay_admissible=True,
            physical_qualification_passed=True, physical_qualification_digest=digest({"physical": seed, "size": size}),
            parent_checkpoint_digest=parent.checkpoint_digest,
            parent_optimizer_state_digest=parent.optimizer_state_digest,
            parent_rng_state_digest=parent.rng_state_digest,
        )
    return mdstats.TargetSizeTrainingEvidence(**kwargs)


def _checkpoints(plan: mdstats.SizeFidelity2ExecutionPlan, *, bad_coarse=False, bad_short=False, boundary_nonconv=False):
    rows = []
    for seed, size in plan.required_training_runs:
        # Final top-two are n8192/n16384, practically equivalent, so n8192 wins by smaller-size preference.
        final_score = 4.0 if size == 8192 else 4.4 if size == 16384 else 8.0 + (8192 - min(size, 8192)) / 8192.0
        coarse_score = 4.5 if size == 8192 else 4.7 if size == 16384 else 6.0 + (8192 - min(size, 8192)) / 8192.0
        short_score = 4.2 if size == 8192 else 4.4 if size == 16384 else 6.0 + (8192 - min(size, 8192)) / 8192.0
        if bad_coarse and seed == 1 and size == 16384:
            coarse_score = 50.0
        if bad_short and seed == 1 and size == 16384:
            short_score = 50.0
        if boundary_nonconv and seed == 1:
            if size == 16384:
                final_score = 1.0
            elif size == 8192:
                final_score = 4.0
        coarse = _ev(seed, size, 3, coarse_score)
        pred3 = digest({"prediction": seed, "size": size, "epoch": 3})
        monitors = []
        for monitor in plan.policy.monitor_configuration_candidates:
            score = coarse_score
            if monitor == 128 and size == 8192:
                score += 20.0
            monitors.append(mdstats.SizeFidelity2MonitorView(monitor, score, True, True, pred3))
        rows.append(mdstats.SizeFidelity2Checkpoint(coarse, pred3, tuple(monitors)))
        short = _ev(seed, size, 10, short_score, parent=coarse)
        rows.append(mdstats.SizeFidelity2Checkpoint(short, digest({"prediction": seed, "size": size, "epoch": 10})))
        final = _ev(seed, size, 30, final_score, parent=short)
        rows.append(mdstats.SizeFidelity2Checkpoint(final, digest({"prediction": seed, "size": size, "epoch": 30})))
    return tuple(rows)


def test_policy_freezes_q4_to_q8_and_prior_monitor_grid():
    policy = mdstats.SizeFidelity2Policy()
    assert policy.admission_widths == (4, 5, 6, 7, 8)
    assert policy.monitor_configuration_candidates == (128, 256, 512, 1024)
    assert policy.screening_seeds == (1, 2, 3)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.SizeFidelity2Policy(admission_widths=(4, 5, 6, 7))


def test_execution_plan_reuses_one_full_trajectory_matrix_for_all_q_widths():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(8))
    assert plan.status == "ready_for_final_gpu_calibration"
    assert plan.admission_widths == (4, 5, 6, 7, 8)
    assert plan.expected_training_run_count == 24  # 3 seeds x 8 sizes, not one run matrix per q.
    assert plan.expected_full_inference_count == 72
    assert plan.expected_additional_monitor_inference_count == 0
    assert plan.required_checkpoint_epochs == (3, 10, 30)


def test_execution_plan_adapts_to_scientifically_available_q6_surface():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(6))
    assert plan.admission_widths == (4, 5, 6)
    assert plan.expected_training_run_count == 18


def test_blocked_size_halve2_never_authorizes_gpu_calibration_work():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(3, ready=False))
    assert plan.status == "blocked_by_size_halve2"
    assert plan.required_training_runs == ()
    assert plan.admission_widths == ()


def test_positive_requalification_retains_finalists_for_every_available_q_and_recommends_256_monitor():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(8))
    report = mdstats.build_size_fidelity2_qualification(plan, _checkpoints(plan))
    assert report.passed
    assert report.recommended_monitor_configurations == 256
    assert report.gpu_qualification_status == "deferred_final_gpu_qualification"
    assert [a.admission_width for a in report.width_assessments] == [4, 5, 6, 7, 8]
    assert all(a.epoch3_finalist_recall == 1.0 for a in report.width_assessments)
    assert all(a.epoch10_finalist_recall == 1.0 for a in report.width_assessments)
    assert all(a.boundary_nonconverged_count == 0 for a in report.width_assessments)
    assert any(dict(a.monitor_decision_equivalence_rates)[128] < 1.0 for a in report.width_assessments)
    assert all(dict(a.monitor_decision_equivalence_rates)[256] == 1.0 for a in report.width_assessments)


def test_epoch3_false_elimination_fails_requalification():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(8))
    report = mdstats.build_size_fidelity2_qualification(plan, _checkpoints(plan, bad_coarse=True))
    assert not report.passed
    assert any(a.epoch3_finalist_recall < 1.0 for a in report.width_assessments)


def test_epoch10_false_elimination_fails_requalification():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(8))
    report = mdstats.build_size_fidelity2_qualification(plan, _checkpoints(plan, bad_short=True))
    assert not report.passed
    assert any(a.epoch10_finalist_recall < 1.0 for a in report.width_assessments)


def test_fixed_16384_ceiling_material_superiority_fails_requalification():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(8))
    report = mdstats.build_size_fidelity2_qualification(plan, _checkpoints(plan, boundary_nonconv=True))
    assert not report.passed
    assert any(a.boundary_nonconverged_count > 0 for a in report.width_assessments)


def test_monitor_view_must_derive_from_same_full_prediction_authority():
    pred = digest({"prediction": 1})
    with pytest.raises(mdstats.TrainingDataInputError, match="derive from"):
        mdstats.SizeFidelity2Checkpoint(
            _ev(1, 16384, 3, 4.0), pred,
            (mdstats.SizeFidelity2MonitorView(256, 4.0, True, True, digest({"other": 1})),),
        )


def test_continuation_ancestry_is_required_in_exhaustive_matrix():
    plan = mdstats.build_size_fidelity2_execution_plan(_halve_plan(4))
    rows = list(_checkpoints(plan))
    idx = next(i for i, row in enumerate(rows) if row.evidence.optimizer_seed == 1 and row.evidence.target_size == 16384 and row.evidence.completed_epochs == 10)
    bad = rows[idx].evidence.to_dict(); bad.pop("content_digest")
    bad["parent_checkpoint_digest"] = digest({"wrong": 1})
    rows[idx] = mdstats.SizeFidelity2Checkpoint(
        mdstats.TargetSizeTrainingEvidence.from_dict(bad), rows[idx].full_prediction_digest
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="continuation ancestry"):
        mdstats.build_size_fidelity2_qualification(plan, tuple(rows))


def test_round_trip_and_recompute_validation():
    halve = _halve_plan(6)
    plan = mdstats.build_size_fidelity2_execution_plan(halve)
    restored_plan = mdstats.SizeFidelity2ExecutionPlan.from_dict(plan.to_dict())
    assert restored_plan.to_dict() == plan.to_dict()
    mdstats.validate_size_fidelity2_execution_plan(restored_plan, size_halve2_plan=halve)
    report = mdstats.build_size_fidelity2_qualification(plan, _checkpoints(plan))
    restored = mdstats.SizeFidelity2QualificationReport.from_dict(report.to_dict())
    assert restored.to_dict() == report.to_dict()
    mdstats.validate_size_fidelity2_qualification(restored, execution_plan=plan)
