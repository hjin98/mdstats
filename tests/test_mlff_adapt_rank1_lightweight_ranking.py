from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data.campaign_cli import _reconcile_lightweight_run_champion


def _sha(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def _protocol(policy: mdstats.AdaptiveTrainingStopPolicy):
    return SimpleNamespace(
        adaptive_stop_policy=policy,
        online_monitor_policy_digest=_sha("online-policy"),
        target_online_monitor_record_digest=_sha("target-monitor"),
        replay_online_monitor_record_digest=_sha("replay-monitor"),
        content_digest=_sha("protocol"),
    )


def _run():
    return SimpleNamespace(content_digest=_sha("run"), run_id="run-a")


def _catalog(epochs: tuple[int, ...]):
    run_digest = _run().content_digest
    records = []
    for epoch in epochs:
        records.append(
            mdstats.CheckpointFileRecord(
                run_plan_digest=run_digest,
                candidate_id=f"run-a:epoch-{epoch}",
                epoch=epoch,
                relative_path=f"model_epoch-{epoch}.pt",
                sha256=_sha(f"checkpoint-{epoch}"),
                size_bytes=123 + epoch,
            )
        )
    return mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run_digest,
        root_directory="/does/not/need/to/exist",
        checkpoints=tuple(records),
        pattern="*epoch*.pt",
    )


def _state(policy, rows, *, stop_epoch: int, stop_reason: str, outcome: str):
    foundation = 0.020
    metrics = tuple(
        mdstats.AdaptiveTrainingEpochMetric(
            epoch=epoch,
            target_force_rmse_ev_per_angstrom=target,
            replay_force_rmse_ev_per_angstrom=replay,
            replay_foundation_force_rmse_ev_per_angstrom=None if replay is None else foundation,
            replay_degradation_force_rmse_ev_per_angstrom=None if replay is None else replay - foundation,
            candidate_eligible=policy.candidate_eligible(target, replay),
            stop_reason=stop_reason if epoch == stop_epoch else None,
        )
        for epoch, target, replay in rows
    )
    return mdstats.AdaptiveTrainingStopState(
        policy_digest=policy.policy_digest,
        foundation_replay_light_force_rmse_ev_per_angstrom=foundation if policy.replay_enabled else None,
        foundation_replay_full_force_rmse_ev_per_angstrom=0.075281 if policy.replay_enabled else None,
        replay_degradation_budget_ev_per_angstrom=(
            policy.replay_degradation_budget_force_rmse_ev_per_angstrom if policy.replay_enabled else None
        ),
        replay_stop_degradation_ev_per_angstrom=(
            policy.replay_stop_degradation_force_rmse_ev_per_angstrom if policy.replay_enabled else None
        ),
        epochs=metrics,
        stop_epoch=stop_epoch,
        stop_reason=stop_reason,
        run_outcome=outcome,
    )


def test_default_one_to_one_ranking_selects_weighted_compromise_without_checkpoint_reads() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    state = _state(
        policy,
        (
            (0, 0.029, 0.025),  # score=(29+5)/2=17.0 meV/A
            (1, 0.024, 0.029),  # score=(24+9)/2=16.5 meV/A -> champion
        ),
        stop_epoch=1,
        stop_reason="target_success",
        outcome="admissible_checkpoint_available",
    )
    # The catalog's root deliberately does not exist. RANK1 must use only the
    # frozen records and therefore cannot open model checkpoints.
    result = mdstats.rank_lightweight_run_champion(
        _run(), _protocol(policy), state, _catalog((0, 1))
    )
    assert result.outcome == "champion_selected"
    assert result.selected_checkpoint_epoch == 1
    assert result.selected_score_ev_per_angstrom == pytest.approx(0.0165)
    assert [item.epoch for item in result.eligible_candidates] == [1, 0]


def test_weight_ratio_changes_score_without_lightweight_threshold_prefilter() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        target_score_weight=2.0,
        replay_score_weight=1.0,
    )
    # R_max = 60 meV/A is only a future full-validation gate. Epoch 2 remains
    # lightweight-rankable and wins on the weighted monitor score.
    state = _state(
        policy,
        (
            (0, 0.029, 0.040),
            (1, 0.026, 0.050),
            (2, 0.031, 0.010),
        ),
        stop_epoch=2,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    result = mdstats.rank_lightweight_run_champion(
        _run(), _protocol(policy), state, _catalog((0, 1, 2))
    )
    assert [item.epoch for item in result.eligible_candidates] == [2, 0, 1]
    assert result.selected_checkpoint_epoch == 2
    assert result.eligible_candidates[0].weighted_score_ev_per_angstrom == pytest.approx(
        (2 * 0.031 + (0.010 - 0.020)) / 3
    )


def test_deterministic_ties_use_target_then_replay_then_epoch_then_sha() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    state = _state(
        policy,
        (
            (0, 0.026, 0.028),  # score 0.027
            (1, 0.025, 0.029),  # score 0.027; lower target wins
            (2, 0.025, 0.029),  # exact metric tie; earlier epoch 1 wins
        ),
        stop_epoch=2,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    result = mdstats.rank_lightweight_run_champion(
        _run(), _protocol(policy), state, _catalog((0, 1, 2))
    )
    assert [item.epoch for item in result.eligible_candidates] == [1, 2, 0]
    assert result.selected_checkpoint_epoch == 1


def test_above_threshold_epochs_remain_lightweight_rankable() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=2)
    state = _state(
        policy,
        ((0, 0.031, 0.025), (1, 0.032, 0.026)),
        stop_epoch=1,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    result = mdstats.rank_lightweight_run_champion(
        _run(), _protocol(policy), state, _catalog((0, 1))
    )
    assert result.outcome == "champion_selected"
    assert result.selected_checkpoint_epoch == 0
    assert [item.epoch for item in result.eligible_candidates] == [0, 1]


def test_ranking_requires_exact_epoch_and_common_monitor_lineage() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    state = _state(
        policy,
        ((0, 0.029, 0.025),),
        stop_epoch=0,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="exact epoch coverage"):
        mdstats.rank_lightweight_run_champion(
            _run(), _protocol(policy), state, _catalog((0, 1))
        )
    broken_protocol = _protocol(policy)
    broken_protocol.target_online_monitor_record_digest = None
    with pytest.raises(mdstats.TrainingDataInputError, match="common-monitor lineage"):
        mdstats.rank_lightweight_run_champion(
            _run(), broken_protocol, state, _catalog((0,))
        )


def test_record_roundtrip_and_run_local_reconciliation_are_idempotent(tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    protocol = _protocol(policy)
    run = _run()
    catalog = _catalog((0, 1))
    state = _state(
        policy,
        ((0, 0.029, 0.025), (1, 0.024, 0.029)),
        stop_epoch=1,
        stop_reason="target_success",
        outcome="admissible_checkpoint_available",
    )
    first = _reconcile_lightweight_run_champion(
        run, SimpleNamespace(protocol=protocol), tmp_path, state, catalog
    )
    assert first is not None
    path = tmp_path / "lightweight_run_champion.json"
    assert path.is_file()
    restored = mdstats.LightweightRunChampionRecord.from_dict(json.loads(path.read_text()))
    assert restored == first
    second = _reconcile_lightweight_run_champion(
        run, SimpleNamespace(protocol=protocol), tmp_path, state, catalog
    )
    assert second == first

    payload = json.loads(path.read_text())
    payload["selected_checkpoint_epoch"] = 0
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(Exception, match="Invalid ADAPT-RANK1 evidence|disagrees"):
        _reconcile_lightweight_run_champion(
            run, SimpleNamespace(protocol=protocol), tmp_path, state, catalog
        )


def test_target_only_run_ranks_by_target_rmse_without_replay_metric() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(replay_enabled=False)
    metrics = (
        mdstats.AdaptiveTrainingEpochMetric(
            epoch=0,
            target_force_rmse_ev_per_angstrom=0.029,
            replay_force_rmse_ev_per_angstrom=None,
            candidate_eligible=True,
        ),
        mdstats.AdaptiveTrainingEpochMetric(
            epoch=1,
            target_force_rmse_ev_per_angstrom=0.023,
            replay_force_rmse_ev_per_angstrom=None,
            candidate_eligible=True,
            stop_reason="target_success",
        ),
    )
    state = mdstats.AdaptiveTrainingStopState(
        policy_digest=policy.policy_digest,
        epochs=metrics,
        stop_epoch=1,
        stop_reason="target_success",
        run_outcome="admissible_checkpoint_available",
    )
    result = mdstats.rank_lightweight_run_champion(
        _run(), _protocol(policy), state, _catalog((0, 1))
    )
    assert result.selected_checkpoint_epoch == 1
    assert result.selected_score_ev_per_angstrom == pytest.approx(0.023)
    assert result.eligible_candidates[0].replay_force_rmse_ev_per_angstrom is None


def test_mlcv_rank1_retains_only_five_best_per_run_without_duplication() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=8)
    rows = tuple(
        (epoch, 0.020 + 0.001 * epoch, 0.020 + 0.0005 * epoch)
        for epoch in range(8)
    )
    state = _state(
        policy,
        rows,
        stop_epoch=7,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    result = mdstats.rank_lightweight_run_topk(
        _run(), _protocol(policy), state, _catalog(tuple(range(8)))
    )
    assert result.candidate_limit == 5
    assert result.rankable_checkpoint_count == 8
    assert len(result.eligible_candidates) == 5
    assert [item.epoch for item in result.eligible_candidates] == [0, 1, 2, 3, 4]
    assert len({item.checkpoint_sha256 for item in result.eligible_candidates}) == 5


def test_mlcv_rank1_fewer_than_five_keeps_exact_available_count() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=3)
    state = _state(
        policy,
        ((0, 0.025, 0.025), (1, 0.024, 0.026), (2, 0.023, 0.027)),
        stop_epoch=2,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    result = mdstats.rank_lightweight_run_topk(
        _run(), _protocol(policy), state, _catalog((0, 1, 2))
    )
    assert result.rankable_checkpoint_count == 3
    assert len(result.eligible_candidates) == 3
    assert {item.epoch for item in result.eligible_candidates} == {0, 1, 2}


def test_mlcv_rank1_candidate_limit_is_validated() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=1)
    state = _state(
        policy,
        ((0, 0.025, 0.025),),
        stop_epoch=0,
        stop_reason="max_epochs_reached",
        outcome="admissible_checkpoint_available",
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="candidate_limit"):
        mdstats.rank_lightweight_run_topk(
            _run(), _protocol(policy), state, _catalog((0,)), candidate_limit=0
        )
