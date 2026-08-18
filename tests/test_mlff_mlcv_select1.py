from types import SimpleNamespace

import pytest

import mdstats

D = "a" * 64
E = "b" * 64
F = "c" * 64
G = "d" * 64
H = "e" * 64
I = "f" * 64


def _score(epoch: int, sha: str, t: float, r: float):
    foundation = 0.075
    degradation = r - foundation
    return mdstats.LightweightCheckpointScore(
        epoch=epoch, checkpoint_sha256=sha,
        target_force_rmse_ev_per_angstrom=t, replay_force_rmse_ev_per_angstrom=r,
        replay_foundation_force_rmse_ev_per_angstrom=foundation,
        replay_degradation_force_rmse_ev_per_angstrom=degradation,
        weighted_score_ev_per_angstrom=(t + degradation) / 2,
    )


def _ranking(candidates):
    return mdstats.LightweightRunChampionRecord(
        run_plan_digest=D,
        training_protocol_digest=E,
        adaptive_stop_policy_digest=F,
        adaptive_stop_state_digest=G,
        checkpoint_catalog_digest=H,
        online_monitor_policy_digest=I,
        target_online_monitor_record_digest="1" * 64,
        replay_online_monitor_record_digest="2" * 64,
        outcome="champion_selected",
        eligible_candidates=tuple(candidates),
        selected_checkpoint_sha256=candidates[0].checkpoint_sha256,
        selected_checkpoint_epoch=candidates[0].epoch,
        selected_score_ev_per_angstrom=candidates[0].weighted_score_ev_per_angstrom,
        rankable_checkpoint_count=len(candidates),
        candidate_limit=5,
    )


def _metrics(force: float, *, energy=0.001, stress=0.001, focus=0.020, worst=0.020):
    return mdstats.ModelDatasetMetricRecord(
        configuration_count=16,
        energy_mae_ev_per_atom=energy,
        force_component_rmse_ev_per_angstrom=force,
        focus_force_rmse_ev_per_angstrom=(("mobile_ions", focus),),
        stress_rmse_ev_per_angstrom3=stress,
        worst_condition_force_rmse_ev_per_angstrom=worst,
    )


def _evaluation(sha: str, t: float, r: float, *, digest_char="3"):
    return SimpleNamespace(
        run_plan_digest=D,
        checkpoint_sha256=sha,
        target_monitor_artifact_digest="a" * 64,
        target_monitor_sha256="b" * 64,
        replay_monitor_artifact_digest="c" * 64,
        replay_monitor_sha256="d" * 64,
        target_candidate_metrics=_metrics(t),
        replay_candidate_metrics=_metrics(r),
        replay_foundation_metrics=_metrics(0.075),
        replay_baseline_model_sha256="6" * 64,
        content_digest=digest_char * 64,
    )


def _metric_policy():
    return mdstats.CheckpointMetricPolicy(
        focus_atom_group_ids=("mobile_ions",),
        maximum_energy_mae_ev_per_atom=0.01,
        maximum_focus_force_rmse_ev_per_angstrom=0.05,
        maximum_stress_rmse_ev_per_angstrom3=0.01,
        maximum_worst_condition_force_rmse_ev_per_angstrom=0.05,
    )


def test_stop_factors_are_configurable_but_derived_from_full_criteria():
    policy = mdstats.AdaptiveTrainingStopPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.040,
        target_score_weight=2.0,
        replay_score_weight=1.0,
        target_stop_fraction=0.75,
        replay_stop_multiplier=1.10,
    )
    assert policy.target_stop_force_rmse_ev_per_angstrom == pytest.approx(0.030)
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(0.080)
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(0.088)


def test_select1_applies_full_thresholds_then_chooses_best_full_score():
    c1 = _score(4, "4" * 64, 0.020, 0.020)
    c2 = _score(5, "5" * 64, 0.021, 0.021)
    c3 = _score(6, "6" * 64, 0.022, 0.022)
    ranking = _ranking((c1, c2, c3))
    retained = _metric_policy()
    policy = mdstats.MlcvRunSelectionPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        maximum_replay_force_rmse_ev_per_angstrom=0.030,
        retained_checkpoint_metric_policy_digest=retained.policy_digest,
    )
    evaluations = (
        _evaluation(c1.checkpoint_sha256, 0.031, 0.018, digest_char="7"),  # reject target
        _evaluation(c2.checkpoint_sha256, 0.026, 0.026, digest_char="8"),  # score .026
        _evaluation(c3.checkpoint_sha256, 0.024, 0.027, digest_char="9"),  # score .0255 -> best
    )
    run = SimpleNamespace(
        content_digest=D,
        run_id="multihead-seed1-fold00",
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
        seed=1,
    )
    result = mdstats.select_mlcv_run_representative(
        run,
        ranking,
        evaluations,
        policy,
        retained,
        target_full_role=mdstats.MlcvDataRole.TARGET_CHECKPOINT_SELECTION,
        target_full_artifact_digest="a" * 64,
        target_full_sha256="b" * 64,
        replay_full_artifact_digest="c" * 64,
        replay_full_sha256="d" * 64,
    )
    assert result.outcome == "representative_selected"
    assert result.representative_checkpoint_sha256 == c3.checkpoint_sha256
    assert len(result.evaluated_candidates) == 3
    assert result.evaluated_candidates[0].rejection_reasons == (
        "target_force_rmse_threshold_exceeded",
    )


def test_select1_final_requires_d_full_authority_and_fold_rejects_outer_c():
    candidate = _score(4, "4" * 64, 0.020, 0.020)
    ranking = _ranking((candidate,))
    retained = _metric_policy()
    policy = mdstats.MlcvRunSelectionPolicy(
        retained_checkpoint_metric_policy_digest=retained.policy_digest
    )
    evaluation = (_evaluation(candidate.checkpoint_sha256, 0.020, 0.020),)
    fold = SimpleNamespace(
        content_digest=D,
        run_id="fold",
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
        seed=1,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.select_mlcv_run_representative(
            fold, ranking, evaluation, policy, retained,
            target_full_role=mdstats.MlcvDataRole.TARGET_OUTER_CV_EVALUATION,
            target_full_artifact_digest="a"*64, target_full_sha256="b"*64,
            replay_full_artifact_digest="c"*64, replay_full_sha256="d"*64,
        )
    final = SimpleNamespace(
        content_digest=D,
        run_id="final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        seed=1,
    )
    result = mdstats.select_mlcv_run_representative(
        final, ranking, evaluation, policy, retained,
        target_full_role=mdstats.MlcvDataRole.TARGET_FINAL_VALIDATION,
        target_full_artifact_digest="a"*64, target_full_sha256="b"*64,
        replay_full_artifact_digest="c"*64, replay_full_sha256="d"*64,
    )
    assert result.outcome == "representative_selected"


def test_select1_records_explicit_no_representative_when_all_topk_fail():
    candidate = _score(2, "4" * 64, 0.020, 0.020)
    ranking = _ranking((candidate,))
    retained = _metric_policy()
    policy = mdstats.MlcvRunSelectionPolicy(
        retained_checkpoint_metric_policy_digest=retained.policy_digest
    )
    run = SimpleNamespace(
        content_digest=D,
        run_id="final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        seed=3,
    )
    result = mdstats.select_mlcv_run_representative(
        run, ranking, (_evaluation(candidate.checkpoint_sha256, 0.040, 0.040),),
        policy, retained,
        target_full_role=mdstats.MlcvDataRole.TARGET_FINAL_VALIDATION,
        target_full_artifact_digest="a"*64, target_full_sha256="b"*64,
        replay_full_artifact_digest="c"*64, replay_full_sha256="d"*64,
    )
    assert result.outcome == "no_representative"
    assert result.representative_candidate is None


def test_campaign_toml_stop_factors_feed_protocol_policy():
    from mdstats.training_data.campaign_cli import _adaptive_training_stop_policy

    cfg = {
        "acceptance": {"maximum_target_force_rmse_ev_per_angstrom": 0.040},
        "evaluation": {"target_score_weight": 2.0, "replay_score_weight": 1.0},
        "training": {
            "target_stop_fraction": 0.70,
            "replay_stop_multiplier": 1.25,
            "minimum_epochs_before_adaptive_stop": 4,
            "max_num_epochs": 28,
        },
    }
    policy = _adaptive_training_stop_policy(cfg)
    assert policy.target_stop_fraction == pytest.approx(0.70)
    assert policy.replay_stop_multiplier == pytest.approx(1.25)
    assert policy.target_stop_force_rmse_ev_per_angstrom == pytest.approx(0.028)
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(0.080)
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(0.100)


def test_select1_record_round_trip_preserves_representative():
    candidate = _score(1, "4" * 64, 0.020, 0.020)
    ranking = _ranking((candidate,))
    retained = _metric_policy()
    policy = mdstats.MlcvRunSelectionPolicy(
        retained_checkpoint_metric_policy_digest=retained.policy_digest
    )
    run = SimpleNamespace(
        content_digest=D,
        run_id="final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        seed=2,
    )
    record = mdstats.select_mlcv_run_representative(
        run, ranking, (_evaluation(candidate.checkpoint_sha256, 0.020, 0.020),),
        policy, retained,
        target_full_role=mdstats.MlcvDataRole.TARGET_FINAL_VALIDATION,
        target_full_artifact_digest="a"*64, target_full_sha256="b"*64,
        replay_full_artifact_digest="c"*64, replay_full_sha256="d"*64,
    )
    restored = mdstats.MlcvRunSelectionRecord.from_dict(record.to_dict())
    assert restored.content_digest == record.content_digest
    assert restored.representative_checkpoint_sha256 == candidate.checkpoint_sha256
