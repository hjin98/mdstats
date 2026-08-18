from pathlib import Path
from types import SimpleNamespace
import pytest
import mdstats


def _candidate(seed, score):
    return SimpleNamespace(
        content_digest=(f"{seed+1:x}" * 64)[:64], seed=seed,
        final_run_plan_digest=(f"{seed+2:x}" * 64)[:64],
        final_run_id=f"seed{seed}-final", checkpoint_sha256=(f"{seed+3:x}"*64)[:64],
        checkpoint_epoch=5+seed, full_score_ev_per_angstrom=score,
        target_full_rmse_ev_per_angstrom=score, replay_full_rmse_ev_per_angstrom=score,
    )


def _selection(candidates):
    return SimpleNamespace(
        campaign_plan_digest="a"*64, content_digest="b"*64,
        outcome="production_candidate_selected", qualified_candidates=tuple(candidates),
    )


def _member(candidate):
    return SimpleNamespace(
        content_digest=(f"{candidate.seed+8:x}"*64)[:64],
        final_candidate_digest=candidate.content_digest,
        final_run_plan_digest=candidate.final_run_plan_digest,
        checkpoint_sha256=candidate.checkpoint_sha256,
        checkpoint_epoch=candidate.checkpoint_epoch,
        target_head_name="target_head",
        exported_model_path=f"/tmp/seed{candidate.seed}.model",
        exported_model_sha256=(f"{candidate.seed+11:x}"*64)[:64],
    )


def _committee(selection, members):
    return SimpleNamespace(
        campaign_plan_digest="a"*64, final_selection_record_digest=selection.content_digest,
        content_digest="c"*64, members=tuple(members),
    )


def _attempt(candidate, member, rank, passed):
    return mdstats.MlcvPhysicalVerificationAttemptRecord(
        final_candidate_digest=candidate.content_digest,
        committee_member_digest=member.content_digest,
        seed=candidate.seed, final_run_plan_digest=candidate.final_run_plan_digest,
        run_id=candidate.final_run_id, checkpoint_sha256=candidate.checkpoint_sha256,
        checkpoint_epoch=candidate.checkpoint_epoch, candidate_rank=rank,
        exported_model_sha256=member.exported_model_sha256,
        verification_policy_digest=mdstats.MlcvVerificationPolicy().policy_digest,
        verification_case_digests=((f"{rank+12:x}"*64)[:64],),
        passed=passed, rejection_reasons=() if passed else ("energy_drift_threshold_exceeded",),
    )


def test_verify1_fallback_visits_only_qualified_final_candidates_and_stops_at_first_pass():
    candidates = (_candidate(1, .021), _candidate(2, .023), _candidate(3, .025))
    selection = _selection(candidates)
    members = tuple(_member(v) for v in candidates)
    committee = _committee(selection, members)
    campaign = SimpleNamespace(content_digest="a"*64)
    policy = mdstats.MlcvVerificationPolicy()
    attempts = (_attempt(candidates[0], members[0], 1, False), _attempt(candidates[1], members[1], 2, True))
    record = mdstats.build_mlcv_verification_record(campaign, selection, committee, policy, attempts)
    assert record.outcome == "physical_candidate_frozen"
    assert record.frozen_final_candidate_digest == candidates[1].content_digest
    assert record.production_model_published is False
    assert record.locked_test_activated is False
    assert mdstats.MlcvVerificationRecord.from_dict(record.to_dict()).content_digest == record.content_digest


def test_verify1_cannot_skip_or_substitute_final_candidate():
    candidates = (_candidate(1, .021), _candidate(2, .023))
    selection = _selection(candidates)
    members = tuple(_member(v) for v in candidates)
    campaign = SimpleNamespace(content_digest="a"*64)
    committee = _committee(selection, members)
    policy = mdstats.MlcvVerificationPolicy()
    with pytest.raises(mdstats.TrainingDataInputError, match="order/identity"):
        mdstats.build_mlcv_verification_record(
            campaign, selection, committee, policy,
            (_attempt(candidates[1], members[1], 1, True),),
        )


def test_verify1_no_fallback_policy_authorizes_only_best_final_seed():
    candidates = (_candidate(1, .021), _candidate(2, .023))
    selection = _selection(candidates)
    members = tuple(_member(v) for v in candidates)
    campaign = SimpleNamespace(content_digest="a"*64)
    committee = _committee(selection, members)
    policy = mdstats.MlcvVerificationPolicy(fallback_to_next_qualified_final_seed=False)
    attempt = mdstats.MlcvPhysicalVerificationAttemptRecord(
        final_candidate_digest=candidates[0].content_digest, committee_member_digest=members[0].content_digest,
        seed=1, final_run_plan_digest=candidates[0].final_run_plan_digest, run_id=candidates[0].final_run_id,
        checkpoint_sha256=candidates[0].checkpoint_sha256, checkpoint_epoch=candidates[0].checkpoint_epoch,
        candidate_rank=1, exported_model_sha256=members[0].exported_model_sha256,
        verification_policy_digest=policy.policy_digest, verification_case_digests=("d"*64,),
        passed=False, rejection_reasons=("maximum_force_threshold_exceeded",),
    )
    record = mdstats.build_mlcv_verification_record(campaign, selection, committee, policy, (attempt,))
    assert record.outcome == "no_candidate_passed"


def _target_metrics(rmse):
    return SimpleNamespace(
        force_component_rmse_ev_per_angstrom=rmse,
        energy_mae_ev_per_atom=0.001,
        focus_force_rmse_ev_per_angstrom=(("mobile", rmse),),
        stress_rmse_ev_per_angstrom3=0.001,
        worst_condition_force_rmse_ev_per_angstrom=rmse,
    )


def _retained_policy():
    return SimpleNamespace(
        policy_digest="e"*64,
        maximum_energy_mae_ev_per_atom=0.01,
        maximum_focus_force_rmse_ev_per_angstrom=0.04,
        maximum_stress_rmse_ev_per_angstrom3=0.01,
        maximum_worst_condition_force_rmse_ev_per_angstrom=0.04,
    )


def _frozen_fixture():
    candidate = _candidate(1, .021)
    selection = _selection((candidate,))
    member = _member(candidate)
    committee = _committee(selection, (member,))
    campaign = SimpleNamespace(content_digest="a"*64)
    policy = mdstats.MlcvVerificationPolicy(retained_checkpoint_metric_policy_digest="e"*64)
    attempt = mdstats.MlcvPhysicalVerificationAttemptRecord(
        final_candidate_digest=candidate.content_digest, committee_member_digest=member.content_digest,
        seed=1, final_run_plan_digest=candidate.final_run_plan_digest, run_id=candidate.final_run_id,
        checkpoint_sha256=candidate.checkpoint_sha256, checkpoint_epoch=candidate.checkpoint_epoch,
        candidate_rank=1, exported_model_sha256=member.exported_model_sha256,
        verification_policy_digest=policy.policy_digest, verification_case_digests=("f"*64,), passed=True,
    )
    verification = mdstats.build_mlcv_verification_record(campaign, selection, committee, policy, (attempt,))
    return campaign, selection, member, committee, policy, verification


def test_locked_E_is_one_shot_target_only_and_cannot_select_fallback():
    campaign, selection, member, committee, policy, verification = _frozen_fixture()
    evaluation = SimpleNamespace(
        run_plan_digest=member.final_run_plan_digest,
        candidate_model_sha256=member.exported_model_sha256,
        checkpoint_sha256=member.exported_model_sha256,
        target_monitor_artifact_digest="1"*64, target_monitor_sha256="2"*64,
        replay_configuration_count=0, replay_monitor_artifact_digest=None,
        target_candidate_metrics=_target_metrics(.025), content_digest="3"*64,
    )
    record = mdstats.build_mlcv_locked_test_record(
        campaign, selection, committee, verification, policy, evaluation, _retained_policy(),
        sealed_evaluation_artifact_digest="4"*64, locked_test_artifact_digest="1"*64,
        locked_test_sha256="2"*64,
    )
    assert record.passed
    assert record.evaluation_count == 1
    assert record.fallback_permitted is False
    assert mdstats.MlcvLockedTestRecord.from_dict(record.to_dict()).content_digest == record.content_digest


def test_locked_E_failure_is_failure_evidence_not_fallback():
    campaign, selection, member, committee, policy, verification = _frozen_fixture()
    evaluation = SimpleNamespace(
        run_plan_digest=member.final_run_plan_digest,
        candidate_model_sha256=member.exported_model_sha256,
        checkpoint_sha256=member.exported_model_sha256,
        target_monitor_artifact_digest="1"*64, target_monitor_sha256="2"*64,
        replay_configuration_count=0, replay_monitor_artifact_digest=None,
        target_candidate_metrics=_target_metrics(.035), content_digest="3"*64,
    )
    record = mdstats.build_mlcv_locked_test_record(
        campaign, selection, committee, verification, policy, evaluation, _retained_policy(),
        sealed_evaluation_artifact_digest="4"*64, locked_test_artifact_digest="1"*64,
        locked_test_sha256="2"*64,
    )
    assert not record.passed
    assert "target_force_rmse_threshold_exceeded" in record.rejection_reasons
    assert record.fallback_permitted is False

def test_verify1_policy_freezes_physical_thresholds_and_toml_fallback_name():
    policy = mdstats.MlcvVerificationPolicy(
        maximum_energy_drift_ev_per_atom_per_ps=0.020,
        minimum_pair_distance_angstrom=0.9,
        maximum_force_ev_per_angstrom=80.0,
    )
    payload = policy.to_dict()
    restored = mdstats.MlcvVerificationPolicy.from_dict(payload)
    assert restored.policy_digest == policy.policy_digest
    assert restored.maximum_energy_drift_ev_per_atom_per_ps == pytest.approx(0.020)
    assert restored.minimum_pair_distance_angstrom == pytest.approx(0.9)
    assert restored.maximum_force_ev_per_angstrom == pytest.approx(80.0)
    source = Path("mdstats/training_data/campaign_cli.py").read_text()
    example = Path("campaign.toml.example").read_text()
    assert 'fallback_to_next_qualified_final_seed = true' in source
    assert 'fallback_to_next_qualified_final_seed = true' in example
    assert 'mlcv_locked_test' in source
    assert 'production_best.model' in source
