from __future__ import annotations

import mdstats
from mdstats.training_data._common import digest


def _metric(seed: int, size: int, epoch: int, score: float, *, monitor: int | None) -> mdstats.SizeFidelityMetric:
    role = "full_development" if monitor is None else "coarse_monitor"
    return mdstats.SizeFidelityMetric(
        optimizer_seed=seed,
        target_size=size,
        epoch=epoch,
        target_force_score_mev_per_a=score,
        numerical_valid=True,
        target_hard_gates_passed=True,
        evaluation_role_kind=role,
        monitor_configurations=monitor,
        foundation_identity_digest=digest({"foundation": 1}),
        training_policy_digest=digest({"train2": 1}),
        schedule_digest=digest({"schedule": 30}),
        training_run_digest=digest({"run": seed, "size": size}),
        checkpoint_digest=digest({"checkpoint": seed, "size": size, "epoch": epoch}),
        evaluation_role_digest=digest({"role": role, "monitor": monitor}),
        target_evaluation_digest=digest({"eval": seed, "size": size, "epoch": epoch, "monitor": monitor}),
    )


def _matrix(*, epoch3_bad: bool = False):
    sizes = (1024, 2048, 4096, 8192, 16384)
    seeds = (1, 2, 3)
    metrics = []
    for seed in seeds:
        # Eventual target finalists are n16 then n32 for every seed.
        final = {1024: 9.0, 2048: 8.0, 4096: 7.0, 8192: 4.0, 16384: 4.4}
        short = {1024: 8.0, 2048: 7.5, 4096: 7.0, 8192: 4.4, 16384: 4.6}
        coarse3 = {1024: 6.0, 2048: 6.1, 4096: 6.2, 8192: 4.8, 16384: (20.0 if epoch3_bad else 5.0)}
        coarse4 = {1024: 6.0, 2048: 6.1, 4096: 6.2, 8192: 4.6, 16384: 4.8}
        coarse5 = {1024: 6.0, 2048: 6.2, 4096: 6.4, 8192: 4.5, 16384: 4.7}
        by_epoch = {3: coarse3, 4: coarse4, 5: coarse5}
        for size in sizes:
            for epoch in (3, 4, 5):
                base = by_epoch[epoch][size]
                metrics.append(_metric(seed, size, epoch, base, monitor=None))
                # 128 is deliberately non-equivalent: it makes n16 look bad.
                score128 = base + (10.0 if size == 8192 else 0.0)
                metrics.append(_metric(seed, size, epoch, score128, monitor=128))
                # 256+ preserve the full-role promotion decision.
                metrics.append(_metric(seed, size, epoch, base + 0.01, monitor=256))
                metrics.append(_metric(seed, size, epoch, base + 0.02, monitor=512))
                metrics.append(_metric(seed, size, epoch, base + 0.03, monitor=1024))
            metrics.append(_metric(seed, size, 10, short[size], monitor=None))
            metrics.append(_metric(seed, size, 30, final[size], monitor=None))
    return sizes, tuple(metrics)


def _policy():
    return mdstats.TargetSizeStudyPolicy(fidelity_epochs=(3, 10, 30))


def _calibration():
    return mdstats.SizeFidelityCalibrationPolicy(coarse_epoch_candidates=(3, 4, 5))


def test_size_fidelity1_recommends_earliest_faithful_endpoint_and_smallest_equivalent_monitor():
    sizes, metrics = _matrix()
    report = mdstats.build_size_fidelity_qualification(
        dataset_id="synthetic",
        target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
        target_size_policy=_policy(),
        target_sizes=sizes,
        metrics=metrics,
        calibration_policy=_calibration(),
    )
    assert report.passed
    assert report.recommended_coarse_epoch == 3
    assert report.recommended_monitor_configurations == 256
    assert report.recommended_coarse_equivalence_mev_per_a == 1.0
    chosen = next(
        x for x in report.candidate_assessments
        if x.coarse_epoch == 3 and x.monitor_configurations == 256 and x.coarse_equivalence_mev_per_a == 1.0
    )
    assert chosen.monitor_decision_equivalence_rate == 1.0
    assert chosen.coarse_finalist_recall == 1.0
    assert chosen.short_finalist_recall == 1.0
    assert chosen.boundary_miss_count == 0


def test_size_fidelity1_can_recommend_later_coarse_endpoint_when_epoch3_drops_a_finalist():
    sizes, metrics = _matrix(epoch3_bad=True)
    report = mdstats.build_size_fidelity_qualification(
        dataset_id="synthetic",
        target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
        target_size_policy=_policy(),
        target_sizes=sizes,
        metrics=metrics,
        calibration_policy=_calibration(),
    )
    assert report.passed
    assert report.recommended_coarse_epoch == 4
    epoch3 = [x for x in report.candidate_assessments if x.coarse_epoch == 3 and x.monitor_configurations == 256]
    assert epoch3 and all(not x.passed for x in epoch3)


def test_size_fidelity1_requires_complete_exhaustive_matrix():
    sizes, metrics = _matrix()
    try:
        mdstats.build_size_fidelity_qualification(
            dataset_id="synthetic",
            target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
            target_size_policy=_policy(),
            target_sizes=sizes,
            metrics=metrics[:-1],
            calibration_policy=_calibration(),
        )
    except mdstats.TrainingDataInputError as exc:
        assert "frozen scientific grid" in str(exc)
    else:
        raise AssertionError("incomplete SIZE-FIDELITY1 matrix was accepted")


def test_size_fidelity1_round_trip_and_recompute_validation():
    sizes, metrics = _matrix()
    report = mdstats.build_size_fidelity_qualification(
        dataset_id="synthetic",
        target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
        target_size_policy=_policy(),
        target_sizes=sizes,
        metrics=metrics,
        calibration_policy=_calibration(),
    )
    restored = mdstats.SizeFidelityQualificationReport.from_dict(report.to_dict())
    assert restored.to_dict() == report.to_dict()
    mdstats.validate_size_fidelity_qualification(restored, target_size_policy=_policy())


def test_size_fidelity1_policy_is_bound_to_current_production_defaults():
    policy = mdstats.SizeFidelityCalibrationPolicy()
    policy.validate_against_target_size_policy(mdstats.TargetSizeStudyPolicy())
    assert policy.coarse_epoch_candidates == (1, 2)
    assert policy.coarse_monitor_configuration_candidates == (128, 256, 512, 1024)
    assert policy.coarse_equivalence_candidates_mev_per_a == (1.0, 2.0, 4.0)
    assert policy.screening_seeds == (1, 2, 3)


def test_size_fidelity1_execution_plan_freezes_exhaustive_matrix_and_reuses_full_predictions():
    plan = mdstats.build_size_fidelity_execution_plan(
        dataset_id="synthetic",
        target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
        target_size_policy=_policy(),
        target_sizes=(1024, 2048, 4096, 8192, 16384),
        calibration_policy=_calibration(),
    )
    assert plan.expected_training_run_count == 15
    assert plan.required_checkpoint_epochs == (3, 4, 5, 10, 30)
    assert plan.expected_full_role_inference_count == 75
    assert plan.monitor_views_derived_from_full_predictions
    restored = mdstats.SizeFidelityExecutionPlan.from_dict(plan.to_dict())
    assert restored.to_dict() == plan.to_dict()


def test_size_fidelity1_rejects_extra_unversioned_metric_grid_entries():
    sizes, metrics = _matrix()
    extra = _metric(1, 1024, 6, 5.0, monitor=None)
    try:
        mdstats.build_size_fidelity_qualification(
            dataset_id="synthetic", target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
            target_size_policy=_policy(), target_sizes=sizes, metrics=metrics + (extra,),
            calibration_policy=_calibration(),
        )
    except mdstats.TrainingDataInputError as exc:
        assert "frozen scientific grid" in str(exc)
    else:
        raise AssertionError("extra SIZE-FIDELITY1 metric was silently ignored")


def test_size_fidelity1_rejects_role_identity_drift_across_candidates():
    sizes, metrics = _matrix()
    items = list(metrics)
    original = items[0]
    payload = original.to_dict(); payload.pop("content_digest")
    payload["evaluation_role_digest"] = digest({"wrong_role": 1})
    items[0] = mdstats.SizeFidelityMetric.from_dict(payload)
    try:
        mdstats.build_size_fidelity_qualification(
            dataset_id="synthetic", target_size_candidate_authority_digest=digest({"candidate-authority": 1}),
                target_size_policy=_policy(), target_sizes=sizes, metrics=tuple(items),
                calibration_policy=_calibration(),
        )
    except mdstats.TrainingDataInputError as exc:
        assert "evaluation-role identity" in str(exc)
    else:
        raise AssertionError("SIZE-FIDELITY1 role drift was accepted")
