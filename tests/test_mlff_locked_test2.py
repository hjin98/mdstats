from __future__ import annotations

import mdstats

D = "a" * 64
E = "b" * 64
F = "c" * 64
G = "d" * 64
H = "e" * 64
I = "f" * 64
J = "1" * 64
K = "2" * 64
L = "3" * 64
M = "4" * 64


def metric(force=0.020, *, energy=0.002, worst=0.025, p99=0.050, stress=0.001):
    return mdstats.Eval2TargetMetricRecord(
        configuration_count=2,
        atom_count=4,
        energy_mae_ev_per_atom=energy,
        relative_energy_rmse_ev_per_atom=0.001,
        force_component_rmse_ev_per_angstrom=force,
        species_macro_force_rmse_ev_per_angstrom=0.021,
        species_force_rmse_ev_per_angstrom=(("Si", 0.021),),
        force_error_p90_ev_per_angstrom=0.030,
        force_error_p95_ev_per_angstrom=0.040,
        force_error_p99_ev_per_angstrom=p99,
        worst_stratum_force_rmse_ev_per_angstrom=worst,
        stratum_force_rmse_ev_per_angstrom=(("species:Si", worst),),
        stress_rmse_ev_per_angstrom3=stress,
        block_metrics=(
            mdstats.Eval2TargetBlockMetric(
                block_id=J,
                force_squared_error_sum=0.0012,
                force_component_count=6,
                configuration_count=1,
            ),
            mdstats.Eval2TargetBlockMetric(
                block_id=K,
                force_squared_error_sum=0.0012,
                force_component_count=6,
                configuration_count=1,
            ),
        ),
        target_role_digest=L,
        prediction_digest=M,
    )


def activation(policy=None):
    return mdstats.LockedTest2ActivationRecord(
        campaign_plan_digest=D,
        select2_selection_digest=E,
        select2_frozen_candidate_digest=F,
        target_data_role_freeze_digest=G,
        run_plan_digest=H,
        optimizer_seed=2,
        label_domain_id="target_dft",
        frozen_target_model_sha256=I,
        frozen_mliap_artifact_sha256="0" * 64,
        policy=policy or mdstats.LockedTest2Policy(),
        sealed_locked_role_digest="5" * 64,
        locked_artifact_digest="6" * 64,
        locked_artifact_sha256="7" * 64,
        locked_artifact_path="/tmp/locked-E.extxyz",
        locked_frame_uids=("8" * 64, "9" * 64),
        locked_unit_ids=(J, K),
        correlation_block_ids=(J, K),
        activated_at_utc="2026-08-14T00:00:00Z",
    )


def test_locked_test2_policy_is_one_shot_target_only():
    policy = mdstats.LockedTest2Policy()
    assert policy.exact_once is True
    assert policy.replay_allowed is False
    assert policy.alternative_selection_allowed is False
    assert policy.maximum_target_force_rmse_ev_per_angstrom == 0.030


def test_locked_test2_force_ceiling_pass_fail():
    a = activation()
    good = mdstats.Eval2TargetMetricRecord.from_dict({**metric(0.020).to_dict(), "target_role_digest": a.content_digest, "content_digest": None})
    bad = mdstats.Eval2TargetMetricRecord.from_dict({**metric(0.031).to_dict(), "target_role_digest": a.content_digest, "content_digest": None})
    passed = mdstats.build_locked_test2_result(a, good, prediction_digest=M, evaluated_at_utc="2026-08-14T00:01:00Z")
    failed = mdstats.build_locked_test2_result(a, bad, prediction_digest=M, evaluated_at_utc="2026-08-14T00:01:00Z")
    assert passed.passed
    assert not failed.passed
    assert failed.rejection_reasons == ("target_force_rmse_threshold_exceeded",)


def test_locked_test2_optional_safety_gates_are_pass_fail_not_ranking():
    p = mdstats.LockedTest2Policy(
        maximum_target_force_rmse_ev_per_angstrom=0.030,
        maximum_energy_mae_ev_per_atom=0.003,
        maximum_worst_stratum_force_rmse_ev_per_angstrom=0.030,
        maximum_force_error_p99_ev_per_angstrom=0.060,
        maximum_stress_rmse_ev_per_angstrom3=0.002,
    )
    a = activation(p)
    raw = metric(force=0.020, energy=0.004, worst=0.031, p99=0.061, stress=0.003).to_dict()
    raw["target_role_digest"] = a.content_digest
    raw["content_digest"] = None
    result = mdstats.build_locked_test2_result(
        a, mdstats.Eval2TargetMetricRecord.from_dict(raw), prediction_digest=M,
        evaluated_at_utc="2026-08-14T00:01:00Z",
    )
    assert not result.passed
    assert set(result.rejection_reasons) == {
        "energy_mae_threshold_exceeded",
        "worst_stratum_force_rmse_threshold_exceeded",
        "force_error_p99_threshold_exceeded",
        "stress_rmse_threshold_exceeded",
    }


def test_locked_test2_records_round_trip_and_production_binds_result():
    a = activation()
    a2 = mdstats.LockedTest2ActivationRecord.from_dict(a.to_dict())
    assert a2 == a
    raw = metric().to_dict(); raw["target_role_digest"] = a.content_digest; raw["content_digest"] = None
    r = mdstats.build_locked_test2_result(
        a, mdstats.Eval2TargetMetricRecord.from_dict(raw), prediction_digest=M,
        evaluated_at_utc="2026-08-14T00:01:00Z",
    )
    assert mdstats.LockedTest2ResultRecord.from_dict(r.to_dict()) == r
    production = mdstats.LockedTest2ProductionModelRecord(
        campaign_plan_digest=D,
        select2_frozen_candidate_digest=F,
        locked_test_activation_digest=a.content_digest,
        locked_test_result_digest=r.content_digest,
        run_plan_digest=H,
        optimizer_seed=2,
        checkpoint_sha256=I,
        checkpoint_epoch=29,
        target_model_path="/tmp/production_best.model",
        target_model_sha256="0" * 64,
        target_model_byte_size=100,
        mliap_artifact_path="/tmp/production_best-mliap_lammps.pt",
        mliap_artifact_sha256="1" * 64,
        mliap_artifact_byte_size=200,
        published_at_utc="2026-08-14T00:02:00Z",
    )
    assert mdstats.LockedTest2ProductionModelRecord.from_dict(production.to_dict()) == production


def test_existing_activation_authenticates_in_place_and_refuses_policy_change(tmp_path):
    import hashlib
    from types import SimpleNamespace
    import pytest
    from mdstats.training_data import campaign_cli

    locked = tmp_path / "locked-E.extxyz"
    locked.write_bytes(b"sealed locked E\n")
    sha = hashlib.sha256(locked.read_bytes()).hexdigest()
    policy = mdstats.LockedTest2Policy()
    existing = mdstats.LockedTest2ActivationRecord(
        campaign_plan_digest=D,
        select2_selection_digest=E,
        select2_frozen_candidate_digest=F,
        target_data_role_freeze_digest=G,
        run_plan_digest=H,
        optimizer_seed=2,
        label_domain_id="target_dft",
        frozen_target_model_sha256=I,
        frozen_mliap_artifact_sha256="0" * 64,
        policy=policy,
        sealed_locked_role_digest="5" * 64,
        locked_artifact_digest="6" * 64,
        locked_artifact_sha256=sha,
        locked_artifact_path=str(locked),
        locked_frame_uids=("8" * 64, "9" * 64),
        locked_unit_ids=(J, K),
        correlation_block_ids=(J, K),
        activated_at_utc="2026-08-14T00:00:00Z",
    )
    args = dict(
        existing=existing,
        campaign=SimpleNamespace(content_digest=D),
        selection=SimpleNamespace(content_digest=E),
        frozen=SimpleNamespace(
            content_digest=F, run_plan_digest=H, optimizer_seed=2,
            target_model_sha256=I, mliap_artifact_sha256="0" * 64,
        ),
        role_freeze=SimpleNamespace(content_digest=G),
        sealed_role=SimpleNamespace(content_digest="5" * 64),
        label_domain_id="target_dft",
        locked_units=(J, K),
        block_ids=(J, K),
        policy=policy,
    )
    before = locked.read_bytes()
    returned = campaign_cli._validate_existing_locked_test2_activation(**args)
    assert returned == locked.resolve()
    assert locked.read_bytes() == before

    args["policy"] = mdstats.LockedTest2Policy(maximum_target_force_rmse_ev_per_angstrom=0.029)
    with pytest.raises(campaign_cli.CampaignCliError, match="already activated"):
        campaign_cli._validate_existing_locked_test2_activation(**args)
    assert locked.read_bytes() == before


def test_existing_activation_refuses_changed_or_missing_locked_bytes(tmp_path):
    import hashlib
    from types import SimpleNamespace
    import pytest
    from mdstats.training_data import campaign_cli

    locked = tmp_path / "locked-E.extxyz"
    locked.write_bytes(b"sealed locked E\n")
    sha = hashlib.sha256(locked.read_bytes()).hexdigest()
    policy = mdstats.LockedTest2Policy()
    existing = mdstats.LockedTest2ActivationRecord(
        campaign_plan_digest=D, select2_selection_digest=E, select2_frozen_candidate_digest=F,
        target_data_role_freeze_digest=G, run_plan_digest=H, optimizer_seed=2, label_domain_id="target_dft",
        frozen_target_model_sha256=I, frozen_mliap_artifact_sha256="0" * 64, policy=policy,
        sealed_locked_role_digest="5" * 64, locked_artifact_digest="6" * 64, locked_artifact_sha256=sha,
        locked_artifact_path=str(locked), locked_frame_uids=("8" * 64, "9" * 64),
        locked_unit_ids=(J, K), correlation_block_ids=(J, K), activated_at_utc="2026-08-14T00:00:00Z",
    )
    args = dict(
        existing=existing, campaign=SimpleNamespace(content_digest=D), selection=SimpleNamespace(content_digest=E),
        frozen=SimpleNamespace(content_digest=F, run_plan_digest=H, optimizer_seed=2, target_model_sha256=I, mliap_artifact_sha256="0" * 64),
        role_freeze=SimpleNamespace(content_digest=G), sealed_role=SimpleNamespace(content_digest="5" * 64),
        label_domain_id="target_dft", locked_units=(J, K), block_ids=(J, K), policy=policy,
    )
    locked.write_bytes(b"tampered\n")
    with pytest.raises(campaign_cli.CampaignCliError, match="Refusing rematerialization"):
        campaign_cli._validate_existing_locked_test2_activation(**args)
