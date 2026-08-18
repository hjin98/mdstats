from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data.campaign_execution import _classify_nonretryable_training_failure
from mdstats.training_data import campaign_cli


def _metrics(force: float):
    return mdstats.ModelDatasetMetricRecord(
        configuration_count=8,
        energy_mae_ev_per_atom=0.001,
        force_component_rmse_ev_per_angstrom=force,
        focus_force_rmse_ev_per_angstrom=(("mobile_ions", 0.010),),
        stress_rmse_ev_per_angstrom3=0.001,
        worst_condition_force_rmse_ev_per_angstrom=0.010,
    )


def _retained_policy():
    return mdstats.CheckpointMetricPolicy(
        focus_atom_group_ids=("mobile_ions",),
        maximum_energy_mae_ev_per_atom=0.01,
        maximum_focus_force_rmse_ev_per_angstrom=0.05,
        maximum_stress_rmse_ev_per_angstrom3=0.01,
        maximum_worst_condition_force_rmse_ev_per_angstrom=0.05,
    )


def _lightweight(*, replay: float, foundation: float = 0.075281, target: float = 0.020):
    delta = replay - foundation
    return mdstats.LightweightCheckpointScore(
        epoch=3,
        checkpoint_sha256="a" * 64,
        target_force_rmse_ev_per_angstrom=target,
        replay_force_rmse_ev_per_angstrom=replay,
        replay_foundation_force_rmse_ev_per_angstrom=foundation,
        replay_degradation_force_rmse_ev_per_angstrom=delta,
        weighted_score_ev_per_angstrom=(target + delta) / 2.0,
    )


def _evaluation(*, replay: float, foundation: float = 0.075281, target: float = 0.020):
    return SimpleNamespace(
        checkpoint_sha256="a" * 64,
        target_candidate_metrics=_metrics(target),
        replay_candidate_metrics=_metrics(replay),
        replay_foundation_metrics=_metrics(foundation),
        replay_baseline_model_sha256="b" * 64,
        content_digest="c" * 64,
    )


def test_observed_foundation_baseline_yields_105281_mev_absolute_ceiling():
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.replay_degradation_budget_force_rmse_ev_per_angstrom == pytest.approx(0.030)
    assert policy.replay_absolute_ceiling_ev_per_angstrom(0.075281) == pytest.approx(0.105281)
    assert policy.replay_stop_degradation_force_rmse_ev_per_angstrom == pytest.approx(0.036)
    # The multiplier acts on degradation, not on the baseline-plus-budget ceiling.
    assert policy.replay_absolute_stop_ceiling_ev_per_angstrom(0.050) == pytest.approx(0.086)


def test_nondefault_weight_geometry_and_explicit_budget_override():
    derived = mdstats.AdaptiveTrainingStopPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.040,
        target_score_weight=2.0,
        replay_score_weight=1.0,
    )
    assert derived.replay_degradation_budget_force_rmse_ev_per_angstrom == pytest.approx(0.080)
    explicit = mdstats.AdaptiveTrainingStopPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.040,
        target_score_weight=2.0,
        replay_score_weight=1.0,
        replay_degradation_budget_ev_per_angstrom=0.055,
    )
    assert explicit.replay_degradation_budget_force_rmse_ev_per_angstrom == pytest.approx(0.055)


def test_negative_replay_degradation_is_preserved_and_improves_score():
    score = _lightweight(replay=0.070, foundation=0.075281, target=0.020)
    assert score.replay_degradation_force_rmse_ev_per_angstrom == pytest.approx(-0.005281)
    assert score.weighted_score_ev_per_angstrom == pytest.approx((0.020 - 0.005281) / 2.0)
    restored = mdstats.LightweightCheckpointScore.from_dict(score.to_dict())
    assert restored.replay_degradation_force_rmse_ev_per_angstrom < 0.0


def test_select1_accepts_raw_replay_above_30_when_degradation_within_budget():
    retained = _retained_policy()
    policy = mdstats.MlcvRunSelectionPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        retained_checkpoint_metric_policy_digest=retained.policy_digest,
    )
    lightweight = _lightweight(replay=0.100)
    candidate = mdstats.assess_mlcv_full_selection_candidate(
        1, lightweight, _evaluation(replay=0.100), policy, retained
    )
    assert candidate.replay_force_rmse_ev_per_angstrom == pytest.approx(0.100)
    assert candidate.replay_degradation_force_rmse_ev_per_angstrom == pytest.approx(0.024719)
    assert candidate.replay_absolute_ceiling_ev_per_angstrom == pytest.approx(0.105281)
    assert candidate.admissible


def test_select1_rejects_degradation_over_budget_without_score_compensation():
    retained = _retained_policy()
    policy = mdstats.MlcvRunSelectionPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        retained_checkpoint_metric_policy_digest=retained.policy_digest,
    )
    lightweight = _lightweight(replay=0.106, target=0.001)
    candidate = mdstats.assess_mlcv_full_selection_candidate(
        1, lightweight, _evaluation(replay=0.106, target=0.001), policy, retained
    )
    assert candidate.replay_degradation_force_rmse_ev_per_angstrom == pytest.approx(0.030719)
    assert not candidate.admissible
    assert "replay_degradation_budget_exceeded" in candidate.rejection_reasons


def test_migration_stale_boundary_never_reinterprets_historical_schemas():
    assert mdstats.mlcv_replay_semantics_stale_boundary(
        {"schema": "mdstats.adaptive-training-stop-policy.v2"}
    ) == "MLCV-STOP1"
    assert mdstats.mlcv_replay_semantics_stale_boundary(
        {"schema": "mdstats.lightweight-run-champion.v2"}
    ) == "MLCV-RANK1"
    assert mdstats.mlcv_replay_semantics_stale_boundary(
        {"schema": "mdstats.mlcv-run-selection-record.v1"}
    ) == "MLCV-SELECT1"
    assert mdstats.mlcv_replay_semantics_stale_boundary(
        {"schema": "mdstats.mlcv-campaign-cv-aggregate.v1"}
    ) == "MLCV-AGG1"
    assert mdstats.mlcv_replay_semantics_stale_boundary(
        {"schema": "mdstats.mlcv-final-selection-record.v1"}
    ) == "MLCV-FINAL1"
    assert mdstats.mlcv_replay_semantics_stale_boundary(
        {"schema": mdstats.MLCV_FINAL_SELECTION_RECORD_SCHEMA}
    ) is None


def test_scheduler_classifies_policy_preflight_as_nonretryable(tmp_path: Path):
    stdout = tmp_path / "stdout.log"
    stderr = tmp_path / "stderr.log"
    stdout.write_text("", encoding="utf-8")
    stderr.write_text(
        "RuntimeError: MDSTATS_NONRETRYABLE MLCV-STOP1 baseline lineage mismatch\n",
        encoding="utf-8",
    )
    result = _classify_nonretryable_training_failure(stdout, stderr, "nonzero_exit:1")
    assert result is not None and result.startswith("nonretryable:policy_or_authority_preflight:")
    stderr.write_text("CUDA process exited unexpectedly\n", encoding="utf-8")
    assert _classify_nonretryable_training_failure(stdout, stderr, "nonzero_exit:1") is None


def test_lifecycle_reconcile_archives_legacy_authority_before_advancing(tmp_path: Path):
    campaign = SimpleNamespace(content_digest="9" * 64)
    bundle = SimpleNamespace(
        mlcv_role_catalog=SimpleNamespace(content_digest="1" * 64),
        mlcv_monitor_catalog=SimpleNamespace(content_digest="2" * 64),
    )
    legacy = mdstats.MlcvLifecycleAuthorityRecord(
        campaign_plan_digest="8" * 64,
        role_catalog_digests=("1" * 64,),
        monitor_catalog_digests=("2" * 64,),
        authority_version=mdstats.MLCV_LIFECYCLE_AUTHORITY_LEGACY_VERSION,
        serialization_schema=mdstats.MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA,
    )
    store = campaign_cli.CampaignStore(tmp_path / "campaign.sqlite3")
    try:
        store.put_record("mlcv_lifecycle_authority", legacy)
        current = campaign_cli._reconcile_mlcv_lifecycle_authority(
            campaign, (bundle,), store, requested_checkpoint_strategy="mlcv_nested_cv"
        )
        assert current.serialization_schema == mdstats.MLCV_LIFECYCLE_AUTHORITY_SCHEMA
        assert current.campaign_plan_digest == campaign.content_digest
        historical_key = f"historical_mlcv_lifecycle_authority:{legacy.content_digest}"
        assert store.has_record(historical_key)
        archived = store.get_record(historical_key, mdstats.MlcvLifecycleAuthorityRecord)
        assert archived.serialization_schema == mdstats.MLCV_LIFECYCLE_AUTHORITY_LEGACY_SCHEMA
        assert archived.content_digest == legacy.content_digest
        assert store.get_record(
            "mlcv_lifecycle_authority", mdstats.MlcvLifecycleAuthorityRecord
        ).content_digest == current.content_digest
    finally:
        store.close()
