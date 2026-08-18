from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _h(ch: str) -> str:
    return (ch * 64)[:64]


def test_train2_policy_roundtrip_and_lr_identity() -> None:
    budget = mdstats.TrainingBudgetPolicy()
    lr = mdstats.LearningRateSchedulePolicy(base_learning_rate=1.0e-4)
    admissibility = mdstats.CheckpointAdmissibilityPolicy()
    selection = mdstats.CheckpointSelectionPolicy()
    assert mdstats.TrainingBudgetPolicy.from_dict(budget.to_dict()) == budget
    assert mdstats.LearningRateSchedulePolicy.from_dict(lr.to_dict()) == lr
    assert mdstats.CheckpointAdmissibilityPolicy.from_dict(admissibility.to_dict()) == admissibility
    assert mdstats.CheckpointSelectionPolicy.from_dict(selection.to_dict()) == selection
    assert lr.multiplier(0.0) == pytest.approx(0.1)
    assert lr.multiplier(0.05) == pytest.approx(1.0)
    assert lr.multiplier(0.80) == pytest.approx(0.1)
    assert lr.multiplier(1.0) == pytest.approx(0.01)
    assert lr.phase(0.01) == "warmup"
    assert lr.phase(0.5) == "adaptation"
    assert lr.phase(0.9) == "refinement"
    assert lr.learning_rate_for_update(0, 101) == pytest.approx(1.0e-5)
    assert lr.learning_rate_for_update(100, 101) == pytest.approx(1.0e-6)


def test_replay_is_hard_constraint_with_zero_ranking_credit() -> None:
    admissibility = mdstats.CheckpointAdmissibilityPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        replay_degradation_budget_ev_per_angstrom=0.030,
    )
    selection = mdstats.CheckpointSelectionPolicy()
    common = dict(target_force_rmse_ev_per_angstrom=0.020, replay_label_mode="true_dft")
    assert admissibility.candidate_admissible(
        **common, replay_degradation_ev_per_angstrom=-0.010
    )
    assert admissibility.candidate_admissible(
        **common, replay_degradation_ev_per_angstrom=0.029
    )
    assert not admissibility.candidate_admissible(
        **common, replay_degradation_ev_per_angstrom=0.031
    )
    # Once both candidates are admissible, their replay values cannot enter the
    # ordering API at all. Identical target evidence therefore yields identical
    # target-side keys except for the explicit stable identity tie-break.
    a = selection.target_rank_key(
        primary_value=0.020,
        secondary_values=(0.030, 0.021, 0.040, 0.050),
        in_refinement_phase=True,
        checkpoint_index=29,
        stable_candidate_identity="a",
    )
    b = selection.target_rank_key(
        primary_value=0.020,
        secondary_values=(0.030, 0.021, 0.040, 0.050),
        in_refinement_phase=True,
        checkpoint_index=29,
        stable_candidate_identity="b",
    )
    assert a[:-1] == b[:-1]
    assert "replay" not in json.dumps(selection.to_dict()).lower()


def test_train2_replay_requires_true_dft_and_target_threshold() -> None:
    policy = mdstats.CheckpointAdmissibilityPolicy()
    assert policy.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.031,
        replay_degradation_ev_per_angstrom=0.010,
        replay_label_mode="true_dft",
    ) == ("target_threshold_exceeded",)
    assert "replay_true_dft_evidence_missing" in policy.failure_reasons(
        target_force_rmse_ev_per_angstrom=0.020,
        replay_degradation_ev_per_angstrom=0.010,
        replay_label_mode="foundation_pseudolabel",
    )
    assert policy.replay_absolute_ceiling_ev_per_angstrom(0.075) == pytest.approx(0.105)


def _train2_protocol(*, adaptive: mdstats.AdaptiveTrainingStopPolicy | None = None):
    optimizer = mdstats.MaceOptimizerPolicy(
        learning_rate=1.0e-4,
        max_num_epochs=30,
        eval_interval=1,
        device="cpu",
        default_dtype="float32",
    )
    kwargs = dict(
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        foundation_checkpoint=mdstats.FoundationCheckpointIdentity(
            reference="foundation.model", sha256="0" * 64
        ),
        compatibility_probe_digest="1" * 64,
        data7_bundle_digest="2" * 64,
        target_train_artifact_digest="3" * 64,
        target_valid_artifact_digest="4" * 64,
        replay_plan_digest="5" * 64,
        training_objective_policy_digest="6" * 64,
        configuration_weight_policy_digest="7" * 64,
        checkpoint_metric_policy_digest="8" * 64,
        checkpoint_control_policy=mdstats.MaceCheckpointControlPolicy(),
        optimizer_policy=optimizer,
        selection_size=512,
        online_monitor_policy_digest="9" * 64,
        target_online_monitor_record_digest="a" * 64,
        replay_online_monitor_record_digest="b" * 64,
        replay_valid_artifact_digest="c" * 64,
        adaptive_stop_policy=adaptive,
    )
    if adaptive is None:
        kwargs.update(
            training_budget_policy=mdstats.TrainingBudgetPolicy(),
            learning_rate_schedule_policy=mdstats.LearningRateSchedulePolicy(
                base_learning_rate=1.0e-4
            ),
            checkpoint_admissibility_policy=mdstats.CheckpointAdmissibilityPolicy(),
            checkpoint_selection_policy=mdstats.CheckpointSelectionPolicy(),
        )
    return mdstats.TrainingProtocolIdentity(**kwargs)


def test_train2_protocol_is_v6_and_roundtrips_without_reinterpreting_v5() -> None:
    train2 = _train2_protocol()
    payload = train2.to_dict()
    assert payload["schema"] == "mdstats.training-protocol-identity.v6"
    assert "adaptive_stop_policy" not in payload
    assert mdstats.TrainingProtocolIdentity.from_dict(payload) == train2

    legacy = _train2_protocol(adaptive=mdstats.AdaptiveTrainingStopPolicy())
    legacy_payload = legacy.to_dict()
    assert legacy_payload["schema"] == "mdstats.training-protocol-identity.v5"
    assert "training_budget_policy" not in legacy_payload
    assert mdstats.TrainingProtocolIdentity.from_dict(legacy_payload).content_digest == legacy.content_digest


def test_train2_and_adaptive_authorities_cannot_mix() -> None:
    train2 = _train2_protocol()
    with pytest.raises(mdstats.TrainingDataInputError, match="mutually exclusive"):
        mdstats.TrainingProtocolIdentity(
            training_mode=train2.training_mode,
            foundation_checkpoint=train2.foundation_checkpoint,
            compatibility_probe_digest=train2.compatibility_probe_digest,
            data7_bundle_digest=train2.data7_bundle_digest,
            target_train_artifact_digest=train2.target_train_artifact_digest,
            target_valid_artifact_digest=train2.target_valid_artifact_digest,
            replay_plan_digest=train2.replay_plan_digest,
            training_objective_policy_digest=train2.training_objective_policy_digest,
            configuration_weight_policy_digest=train2.configuration_weight_policy_digest,
            checkpoint_metric_policy_digest=train2.checkpoint_metric_policy_digest,
            checkpoint_control_policy=train2.checkpoint_control_policy,
            optimizer_policy=train2.optimizer_policy,
            selection_size=train2.selection_size,
            online_monitor_policy_digest=train2.online_monitor_policy_digest,
            target_online_monitor_record_digest=train2.target_online_monitor_record_digest,
            replay_online_monitor_record_digest=train2.replay_online_monitor_record_digest,
            replay_valid_artifact_digest=train2.replay_valid_artifact_digest,
            adaptive_stop_policy=mdstats.AdaptiveTrainingStopPolicy(),
            training_budget_policy=train2.training_budget_policy,
            learning_rate_schedule_policy=train2.learning_rate_schedule_policy,
            checkpoint_admissibility_policy=train2.checkpoint_admissibility_policy,
            checkpoint_selection_policy=train2.checkpoint_selection_policy,
        )


def test_generated_config_uses_train2_and_omits_historical_controls() -> None:
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="foundation.model",
        replay_train="train.xyz",
        replay_monitor="monitor.xyz",
    )
    assert 'policy_generation = "train2"' in text
    assert "allowed_replay_degradation_mev_per_a = 30.0" in text
    assert 'checkpoint_strategy = "train2_target_first"' in text
    assert "target_stop_fraction =" not in text
    assert "replay_stop_multiplier =" not in text
    assert "target_score_weight =" not in text
    assert "replay_score_weight =" not in text
    assert "maximum_replay_degradation_fraction =" not in text


def test_train2_config_rejects_historical_controls() -> None:
    cfg = {
        "training": {"policy_generation": "train2", "target_stop_fraction": 0.8},
        "evaluation": {},
    }
    with pytest.raises(campaign_cli.CampaignCliError, match="cannot silently reinterpret"):
        campaign_cli._validate_train2_migration_config(cfg)
    with pytest.raises(campaign_cli.CampaignCliError, match="cannot silently reinterpret"):
        campaign_cli._validate_train2_migration_config({
            "training": {"policy_generation": "train2"},
            "acceptance": {"maximum_replay_degradation_fraction": 0.20},
        })
    assert campaign_cli._training_policy_generation({"training": {}}) == "adaptive_stop_v3"


def test_train2_policy_factory_has_no_replay_score_weights() -> None:
    cfg = {
        "training": {
            "policy_generation": "train2",
            "max_num_epochs": 30,
            "eval_interval": 1,
            "learning_rate": 1.0e-4,
        },
        "acceptance": {
            "maximum_target_force_rmse_ev_per_angstrom": 0.030,
            "allowed_replay_degradation_mev_per_a": 30.0,
        },
        "evaluation": {"finalist_count": 5},
        "target_data": {"size_convergence": {"practical_equivalence_mev_per_a": 1.0}},
    }
    budget, lr, admissibility, selection = campaign_cli._train2_policy_set(
        cfg, require_replay=True
    )
    assert budget.planned_epochs == 30
    assert lr.base_learning_rate == pytest.approx(1.0e-4)
    assert admissibility.replay_degradation_budget_ev_per_angstrom == pytest.approx(0.030)
    assert selection.practical_equivalence_ev_per_angstrom == pytest.approx(0.001)
    assert not any("weight" in key.lower() and "replay" in key.lower() for key in selection.to_dict())


def test_production_materialization_v6_roundtrip_binds_train2_authority(tmp_path: Path) -> None:
    from dataclasses import replace
    from tests.test_mlff_data9a9b_production_materialization import _fixture

    *_, legacy_plan, _calc = _fixture(tmp_path)
    assert legacy_plan.plan_schema == "mdstats.production-materialization-plan.v5"
    true_replay = mdstats.inspect_replay_extxyz(
        Path(legacy_plan.replay_plan.monitor_artifact.path),
        label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    budget = mdstats.TrainingBudgetPolicy(planned_epochs=legacy_plan.optimizer_policy.max_num_epochs)
    lr = mdstats.LearningRateSchedulePolicy(base_learning_rate=legacy_plan.optimizer_policy.learning_rate)
    admissibility = mdstats.CheckpointAdmissibilityPolicy(replay_enabled=legacy_plan.require_replay)
    selection = mdstats.CheckpointSelectionPolicy()
    plan = replace(
        legacy_plan,
        plan_schema="mdstats.production-materialization-plan.v6",
        online_monitor_policy=mdstats.OnlineMonitorPolicy(
            target_configurations=1,
            replay_configurations=1,
            training_diagnostic_configurations=1,
        ),
        true_replay_monitor_artifact=true_replay,
        adaptive_stop_policy=None,
        training_budget_policy=budget,
        learning_rate_schedule_policy=lr,
        checkpoint_admissibility_policy=admissibility,
        checkpoint_selection_policy=selection,
    )
    payload = plan.to_dict()
    assert payload["schema"] == "mdstats.production-materialization-plan.v6"
    assert "adaptive_stop_policy" not in payload
    assert payload["checkpoint_admissibility_policy"]["replay_degradation_budget_ev_per_angstrom"] == pytest.approx(0.030)
    restored = mdstats.ProductionMaterializationPlan.from_dict(payload)
    assert restored.content_digest == plan.content_digest
    assert restored.training_budget_policy == budget
    assert restored.checkpoint_selection_policy == selection
