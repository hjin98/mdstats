from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path
import hashlib
import json
import pytest

import mdstats


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _champ(run_digest: str, epoch: int, target: float, replay: float, score: float):
    item = mdstats.LightweightCheckpointScore(
        epoch=epoch,
        checkpoint_sha256=_sha(f"checkpoint-{run_digest}-{epoch}"),
        target_force_rmse_ev_per_angstrom=target,
        replay_force_rmse_ev_per_angstrom=replay,
        weighted_score_ev_per_angstrom=score,
        serialization_schema="mdstats.lightweight-checkpoint-score.v1",
    )
    return mdstats.LightweightRunChampionRecord(
        run_plan_digest=run_digest,
        training_protocol_digest=_sha(f"protocol-{run_digest}"),
        adaptive_stop_policy_digest=_sha(f"stop-policy-{run_digest}"),
        adaptive_stop_state_digest=_sha(f"stop-state-{run_digest}"),
        checkpoint_catalog_digest=_sha(f"catalog-{run_digest}"),
        online_monitor_policy_digest=_sha("online-policy"),
        target_online_monitor_record_digest=_sha("target-monitor"),
        replay_online_monitor_record_digest=_sha("replay-monitor"),
        outcome="champion_selected",
        eligible_candidates=(item,),
        selected_checkpoint_sha256=item.checkpoint_sha256,
        selected_checkpoint_epoch=epoch,
        selected_score_ev_per_angstrom=score,
        serialization_schema="mdstats.lightweight-run-champion.v1",
    )


def test_finalist_queue_is_global_top_five_then_next_five_rescue_batches():
    runs=[]; champions={}
    for i, score in enumerate((.030,.021,.029,.024,.025,.023,.026,.022,.028,.027,.031,.032)):
        digest=_sha(f"run-{i}")
        run=SimpleNamespace(content_digest=digest, run_id=f"run-{i}")
        runs.append(run)
        champions[digest]=_champ(digest, i, score, score, score)
    campaign=SimpleNamespace(content_digest=_sha("campaign"), runs=tuple(runs))
    policy=mdstats.AdaptiveFullEvaluationPolicy(finalist_count=5, finalist_rescue_batch_size=5)
    queue=mdstats.build_campaign_finalist_queue(campaign, champions, policy)
    assert [round(x.lightweight_score_ev_per_angstrom,3) for x in queue.candidates[:5]] == [.021,.022,.023,.024,.025]
    assert [x.batch_index for x in queue.candidates] == [1]*5+[2]*5+[3]*2
    restored=mdstats.CampaignFinalistQueueRecord.from_dict(queue.to_dict())
    assert restored == queue


def _metric(count: int, force: float, *, energy=.001, stress=.001, focus=.02, worst=.04):
    return mdstats.ModelDatasetMetricRecord(
        configuration_count=count,
        energy_mae_ev_per_atom=energy,
        force_component_rmse_ev_per_angstrom=force,
        focus_force_rmse_ev_per_angstrom=(("mobile", focus),),
        stress_rmse_ev_per_angstrom3=stress,
        worst_condition_force_rmse_ev_per_angstrom=worst,
        condition_force_rmse_ev_per_angstrom=(("all", force),),
        combined_loss=force,
    )


def _evaluation(finalist, target_force: float, replay_force: float):
    target=_metric(1400,target_force)
    replay=_metric(1987,replay_force)
    baseline=_metric(1987,.020)
    metric=mdstats.CheckpointMetricRecord(
        run_plan_digest=finalist.run_plan_digest,
        checkpoint_sha256=finalist.checkpoint_sha256,
        target_monitor_artifact_digest=_sha("full-target"),
        energy_mae_ev_per_atom=target.energy_mae_ev_per_atom,
        force_component_rmse_ev_per_angstrom=target.force_component_rmse_ev_per_angstrom,
        focus_force_rmse_ev_per_angstrom=target.focus_force_rmse_ev_per_angstrom,
        stress_rmse_ev_per_angstrom3=target.stress_rmse_ev_per_angstrom3,
        worst_condition_force_rmse_ev_per_angstrom=target.worst_condition_force_rmse_ev_per_angstrom,
        target_combined_loss=target.combined_loss,
        replay_monitor_artifact_digest=_sha("replay-lineage"),
        replay_baseline_metric=.020,
        replay_candidate_metric=replay_force,
        replay_degradation_fraction=max(0,replay_force-.020)/.020,
        replay_label_mode=mdstats.ReplayLabelMode.TRUE_DFT,
    )
    return mdstats.CheckpointEvaluationRecord(
        run_plan_digest=finalist.run_plan_digest,
        checkpoint_sha256=finalist.checkpoint_sha256,
        evaluation_policy_digest=_sha("eval-policy"),
        target_monitor_artifact_digest=_sha("full-target"),
        target_monitor_sha256=_sha("full-target-bytes"),
        replay_monitor_artifact_digest=_sha("full-replay"),
        replay_monitor_sha256=_sha("full-replay-bytes"),
        candidate_model_path="candidate.pt",
        candidate_model_sha256=finalist.checkpoint_sha256,
        replay_baseline_model_path="foundation.pt",
        replay_baseline_model_sha256=_sha("foundation"),
        target_configuration_count=1400,
        replay_configuration_count=1987,
        condition_force_rmse_ev_per_angstrom=(("all",target_force),),
        metric_record=metric,
        target_candidate_metrics=target,
        replay_candidate_metrics=replay,
        replay_foundation_metrics=baseline,
    )


def test_full_score_applies_target_and_replay_boundaries_before_ranking():
    finalist=mdstats.CampaignFinalistCandidate(
        rank=1,batch_index=1,run_plan_digest=_sha("run"),run_id="run",
        champion_record_digest=_sha("champ"),checkpoint_sha256=_sha("checkpoint"),
        checkpoint_epoch=5,lightweight_score_ev_per_angstrom=.025,
    )
    retained=mdstats.CheckpointMetricPolicy(
        focus_atomic_numbers=(3,11,19),
        maximum_energy_mae_ev_per_atom=.005,
        maximum_focus_force_rmse_ev_per_angstrom=.10,
        maximum_stress_rmse_ev_per_angstrom3=.02,
        maximum_worst_condition_force_rmse_ev_per_angstrom=.15,
    )
    policy=mdstats.AdaptiveFullEvaluationPolicy(
        target_score_weight=1,replay_score_weight=1,
        maximum_target_force_rmse_ev_per_angstrom=.030,
        maximum_replay_force_rmse_ev_per_angstrom=.030,
        retained_checkpoint_metric_policy_digest=retained.policy_digest,
    )
    accepted=mdstats.assess_full_evaluation_candidate(finalist,_evaluation(finalist,.028,.029),policy,retained)
    assert accepted.admissible
    assert accepted.full_score_ev_per_angstrom == pytest.approx(.0285)
    assert accepted.replay_absolute_degradation_ev_per_angstrom == pytest.approx(.009)
    rejected=mdstats.assess_full_evaluation_candidate(finalist,_evaluation(finalist,.020,.031),policy,retained)
    assert not rejected.admissible
    assert "replay_force_rmse_threshold_exceeded" in rejected.rejection_reasons


def test_two_to_one_target_weight_derives_sixty_mev_replay_limit_contract():
    stop=mdstats.AdaptiveTrainingStopPolicy(target_score_weight=2,replay_score_weight=1)
    assert stop.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(.060)
    policy=mdstats.AdaptiveFullEvaluationPolicy(
        target_score_weight=2,replay_score_weight=1,
        maximum_target_force_rmse_ev_per_angstrom=.030,
        maximum_replay_force_rmse_ev_per_angstrom=.060,
    )
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(.060)


def test_naive_production_stop_policy_uses_true_replay_score_geometry() -> None:
    from mdstats.training_data import campaign_cli

    policy = campaign_cli._adaptive_training_stop_policy(
        {
            "acceptance": {"maximum_target_force_rmse_ev_per_angstrom": 0.030},
            "evaluation": {"target_score_weight": 1.0, "replay_score_weight": 1.0},
            "training": {"max_num_epochs": 30},
        },
        replay_head_name="replay_monitor",
    )
    assert policy.replay_enabled
    assert policy.replay_head_name == "replay_monitor"
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(0.030)


def test_naive_auxiliary_true_replay_loader_is_inserted_before_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("mace")
    torch = pytest.importorskip("torch")
    np = pytest.importorskip("numpy")
    ase = pytest.importorskip("ase")
    from ase.io import write
    from torch.utils.data import DataLoader
    from mdstats.training_data import adaptive_stop

    replay_path = tmp_path / "true-replay.xyz"
    atoms = ase.Atoms("H", positions=[[0.0, 0.0, 0.0]], cell=[5.0, 5.0, 5.0], pbc=True)
    atoms.info["REF_energy"] = 0.1
    atoms.info["REF_stress"] = np.zeros(6)
    atoms.arrays["REF_forces"] = np.zeros((1, 3))
    write(replay_path, [atoms], format="extxyz")

    policy = mdstats.AdaptiveTrainingStopPolicy(
        target_head_name="target_head", replay_head_name="replay_monitor"
    )
    monkeypatch.setenv(
        adaptive_stop.ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE,
        json.dumps(policy.to_dict()),
    )
    monkeypatch.setenv(
        adaptive_stop.ADAPTIVE_STOP_AUXILIARY_REPLAY_PATH_ENVIRONMENT_VARIABLE,
        str(replay_path),
    )

    class Model:
        heads = ["target_head"]
        atomic_numbers = torch.tensor([1])
        r_max = torch.tensor(3.0)

    base_loader = DataLoader([1], batch_size=1)
    loaders = adaptive_stop.prepare_auxiliary_replay_validation_loader(
        Model(), {"target_head": base_loader}
    )
    assert list(loaders) == ["replay_monitor", "target_head"]
    assert len(loaders["replay_monitor"].dataset) == 1
    assert int(loaders["replay_monitor"].dataset[0].head.item()) == 0
