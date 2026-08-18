from types import SimpleNamespace

import pytest

import mdstats


def _metrics(force: float):
    return mdstats.ModelDatasetMetricRecord(
        configuration_count=12,
        energy_mae_ev_per_atom=0.001,
        force_component_rmse_ev_per_angstrom=force,
        focus_force_rmse_ev_per_angstrom=(("mobile_ions", force),),
        stress_rmse_ev_per_angstrom3=0.001,
        worst_condition_force_rmse_ev_per_angstrom=force,
    )


def _selection(run, *, sha: str, epoch: int, replay: float, outcome="representative_selected"):
    if outcome == "no_representative":
        return SimpleNamespace(
            run_plan_digest=run.content_digest,
            fold_index=run.fold_index,
            seed=run.seed,
            outcome=outcome,
            representative_candidate=None,
            content_digest=(str(run.fold_index + 1) * 64)[:64],
        )
    foundation = 0.075
    candidate = SimpleNamespace(
        checkpoint_sha256=sha, checkpoint_epoch=epoch,
        replay_force_rmse_ev_per_angstrom=replay,
        replay_foundation_force_rmse_ev_per_angstrom=foundation,
        replay_degradation_force_rmse_ev_per_angstrom=replay-foundation,
        replay_degradation_budget_ev_per_angstrom=0.030,
    )
    return SimpleNamespace(
        run_plan_digest=run.content_digest,
        fold_index=run.fold_index,
        seed=run.seed,
        outcome=outcome,
        representative_candidate=candidate,
        content_digest=(str(run.fold_index + 1) * 64)[:64],
    )


def _run(fold: int, seed: int = 1):
    return SimpleNamespace(
        content_digest=(hex(10 + fold)[2:] * 64)[:64],
        run_id=f"multihead-seed{seed}-fold{fold:02d}",
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=fold,
        seed=seed,
        protocol_family_digest="a" * 64,
        protocol_variant_digest=(hex(5 + seed)[2:] * 64)[:64],
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
    )


def _final(seed: int = 1):
    return SimpleNamespace(
        content_digest="f" * 64,
        run_id=f"multihead-seed{seed}-final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        seed=seed,
        protocol_family_digest="a" * 64,
        protocol_variant_digest=(hex(5 + seed)[2:] * 64)[:64],
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=512,
    )


def _evaluation(run, sha: str, target: float, artifact="b" * 64, outer_sha="c" * 64):
    return SimpleNamespace(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=sha,
        target_monitor_artifact_digest=artifact,
        target_monitor_sha256=outer_sha,
        replay_monitor_artifact_digest=None,
        replay_configuration_count=0,
        target_candidate_metrics=_metrics(target),
        content_digest="d" * 64,
    )


def _policy():
    return mdstats.MlcvCrossValidationPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        target_score_weight=1.0,
        replay_score_weight=1.0,
    )


def test_agg1_outer_fold_never_reselects_checkpoint_and_uses_select1_replay():
    run = _run(0)
    selection = _selection(run, sha="1" * 64, epoch=7, replay=0.026)
    evaluation = _evaluation(run, "1" * 64, 0.028)
    record = mdstats.build_mlcv_outer_fold_record(
        run, selection, evaluation, _policy(),
        outer_target_artifact_digest="b" * 64,
        outer_target_sha256="c" * 64,
    )
    assert record.survived
    assert record.representative_checkpoint_epoch == 7
    assert record.representative_replay_full_rmse_ev_per_angstrom == pytest.approx(0.026)
    assert record.combined_score_ev_per_angstrom == pytest.approx((0.028 + (0.026-0.075))/2)
    assert record.production_eligible is False

    wrong = _evaluation(run, "2" * 64, 0.020)
    with pytest.raises(mdstats.TrainingDataInputError, match="cannot change"):
        mdstats.build_mlcv_outer_fold_record(
            run, selection, wrong, _policy(),
            outer_target_artifact_digest="b" * 64,
            outer_target_sha256="c" * 64,
        )


def test_agg1_outer_threshold_failure_does_not_trigger_fallback():
    run = _run(1)
    selection = _selection(run, sha="1" * 64, epoch=4, replay=0.020)
    record = mdstats.build_mlcv_outer_fold_record(
        run, selection, _evaluation(run, "1" * 64, 0.031), _policy(),
        outer_target_artifact_digest="b" * 64,
        outer_target_sha256="c" * 64,
    )
    assert record.outcome == "outer_target_threshold_exceeded"
    assert record.representative_checkpoint_sha256 == "1" * 64
    assert record.rejection_reasons == ("outer_target_force_rmse_threshold_exceeded",)


def test_agg1_no_select1_representative_is_explicit_fold_failure_without_inference():
    run = _run(2)
    selection = _selection(run, sha="1" * 64, epoch=1, replay=0.020, outcome="no_representative")
    record = mdstats.build_mlcv_outer_fold_record(
        run, selection, None, _policy(),
        outer_target_artifact_digest="b" * 64,
        outer_target_sha256="c" * 64,
    )
    assert record.outcome == "no_representative"
    assert not record.survived
    assert record.outer_evaluation_record_digest is None


def test_agg1_seed_statistics_use_sample_sd_and_keep_components_separate():
    runs = tuple(_run(i) for i in range(3)) + (_final(),)
    targets = (0.024, 0.026, 0.028)
    replays = (0.020, 0.025, 0.030)
    records = []
    for run, target, replay in zip(runs[:3], targets, replays):
        selection = _selection(run, sha=(str(run.fold_index + 1) * 64), epoch=5, replay=replay)
        evaluation = _evaluation(run, selection.representative_candidate.checkpoint_sha256, target)
        records.append(mdstats.build_mlcv_outer_fold_record(
            run, selection, evaluation, _policy(),
            outer_target_artifact_digest="b" * 64,
            outer_target_sha256="c" * 64,
        ))
    campaign = SimpleNamespace(content_digest="e" * 64)
    agg = mdstats.aggregate_mlcv_seed_cv(campaign, runs, records, _policy())
    assert agg.outcome == "cv_robust"
    assert agg.target_summary.mean_ev_per_angstrom == pytest.approx(0.026)
    assert agg.target_summary.sample_standard_deviation_ev_per_angstrom == pytest.approx(0.002)
    assert agg.target_summary.minimum_ev_per_angstrom == pytest.approx(0.024)
    assert agg.target_summary.maximum_ev_per_angstrom == pytest.approx(0.028)
    assert agg.target_summary.range_ev_per_angstrom == pytest.approx(0.004)
    assert agg.target_summary.worst_fold_index == 2
    assert agg.replay_summary.values_ev_per_angstrom == pytest.approx(tuple(v-0.075 for v in replays))
    assert agg.replay_absolute_summary.values_ev_per_angstrom == pytest.approx(replays)
    assert agg.combined_summary.values_ev_per_angstrom == pytest.approx(tuple((t + (r-0.075))/2 for t, r in zip(targets, replays)))
    restored = mdstats.MlcvSeedCvAggregateRecord.from_dict(agg.to_dict())
    assert restored.content_digest == agg.content_digest


def test_agg1_all_fold_survival_is_hard_but_dispersion_has_no_hard_gate():
    runs = tuple(_run(i) for i in range(3)) + (_final(),)
    records = []
    for run, target in zip(runs[:3], (0.005, 0.029, 0.031)):
        selection = _selection(run, sha=(str(run.fold_index + 1) * 64), epoch=5, replay=0.020)
        records.append(mdstats.build_mlcv_outer_fold_record(
            run, selection,
            _evaluation(run, selection.representative_candidate.checkpoint_sha256, target),
            _policy(), outer_target_artifact_digest="b" * 64, outer_target_sha256="c" * 64,
        ))
    agg = mdstats.aggregate_mlcv_seed_cv(SimpleNamespace(content_digest="e" * 64), runs, records, _policy())
    assert agg.outcome == "cv_failed"
    assert "fold_2:outer_target_threshold_exceeded" in agg.failure_reasons
    assert agg.dispersion_authority == "diagnostic_only"
    assert agg.target_summary.sample_standard_deviation_ev_per_angstrom > 0


def test_agg1_role_authority_rejects_checkpoint_selection_role_for_outer_cv():
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.require_mlcv_outer_cv_evaluation_role(mdstats.MlcvDataRole.TARGET_CHECKPOINT_SELECTION)

def test_agg1_campaign_outcome_fails_if_any_seed_cv_fails():
    policy = _policy()
    campaign = SimpleNamespace(content_digest="e" * 64)
    def seed_agg(seed, outcome):
        # Build real aggregates so count/outcome invariants are exercised.
        runs = tuple(_run(i, seed=seed) for i in range(3)) + (_final(seed),)
        # Align variant identity across fold/final helper instances.
        for run in runs:
            pass
        records = []
        for run in runs[:3]:
            selection = _selection(run, sha=(str(run.fold_index + 1) * 64), epoch=2, replay=0.020)
            target = 0.031 if (outcome == "cv_failed" and run.fold_index == 2) else 0.025
            records.append(mdstats.build_mlcv_outer_fold_record(
                run, selection,
                _evaluation(run, selection.representative_candidate.checkpoint_sha256, target),
                policy, outer_target_artifact_digest="b" * 64, outer_target_sha256="c" * 64,
            ))
        return mdstats.aggregate_mlcv_seed_cv(campaign, runs, records, policy)
    good = seed_agg(1, "cv_robust")
    bad = seed_agg(2, "cv_failed")
    result = mdstats.aggregate_mlcv_campaign_cv(campaign, (good, bad), policy)
    assert result.outcome == "cv_failed"
    assert result.robust_seed_count == 1
    assert result.failed_seed_count == 1
    assert result.production_selection_created is False
    assert result.next_gate == "MLCV-FINAL1"
