from __future__ import annotations

from types import SimpleNamespace
import hashlib

import pytest

import mdstats


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _run(run_id: str):
    return SimpleNamespace(content_digest=_sha(run_id), run_id=run_id)


def _protocol(policy):
    return SimpleNamespace(
        adaptive_stop_policy=policy,
        online_monitor_policy_digest=_sha("policy"),
        target_online_monitor_record_digest=_sha("target"),
        replay_online_monitor_record_digest=_sha("replay"),
        content_digest=_sha("protocol"),
    )


def _catalog(run, count: int):
    rows = tuple(
        mdstats.CheckpointFileRecord(
            run_plan_digest=run.content_digest,
            candidate_id=f"{run.run_id}:epoch-{epoch}",
            epoch=epoch,
            relative_path=f"epoch-{epoch}.pt",
            sha256=_sha(f"{run.run_id}-{epoch}"),
            size_bytes=100 + epoch,
        )
        for epoch in range(count)
    )
    return mdstats.CandidateCheckpointCatalog(
        run_plan_digest=run.content_digest,
        root_directory="/missing/by-design",
        checkpoints=rows,
        pattern="*.pt",
    )


def _state(policy, values):
    foundation = 0.075
    metrics = tuple(
        mdstats.AdaptiveTrainingEpochMetric(
            epoch=i,
            target_force_rmse_ev_per_angstrom=t,
            replay_force_rmse_ev_per_angstrom=r,
            replay_foundation_force_rmse_ev_per_angstrom=foundation,
            replay_degradation_force_rmse_ev_per_angstrom=r-foundation,
            candidate_eligible=True,
            stop_reason="max_epochs_reached" if i == len(values) - 1 else None,
        )
        for i, (t, r) in enumerate(values)
    )
    return mdstats.AdaptiveTrainingStopState(
        policy_digest=policy.policy_digest,
        foundation_replay_light_force_rmse_ev_per_angstrom=foundation,
        epochs=metrics,
        stop_epoch=len(values) - 1,
        stop_reason="max_epochs_reached",
        run_outcome="admissible_checkpoint_available",
    )


def test_rank1_is_run_local_and_keeps_five_best_without_checkpoint_reads() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=7)
    values_a = [(0.030 - i * 0.001, 0.020 + i * 0.001) for i in range(7)]
    values_b = [(0.020 + i * 0.001, 0.030 - i * 0.001) for i in range(7)]
    run_a, run_b = _run("a"), _run("b")
    a = mdstats.rank_lightweight_run_topk(run_a, _protocol(policy), _state(policy, values_a), _catalog(run_a, 7))
    b = mdstats.rank_lightweight_run_topk(run_b, _protocol(policy), _state(policy, values_b), _catalog(run_b, 7))
    assert a.rankable_checkpoint_count == b.rankable_checkpoint_count == 7
    assert len(a.eligible_candidates) == len(b.eligible_candidates) == 5
    assert all(x.checkpoint_sha256.startswith("") for x in a.eligible_candidates)
    assert {x.checkpoint_sha256 for x in a.eligible_candidates}.isdisjoint(
        {x.checkpoint_sha256 for x in b.eligible_candidates}
    )


def test_rank1_above_full_threshold_is_still_rankable() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=2)
    run = _run("threshold-free")
    result = mdstats.rank_lightweight_run_topk(
        run,
        _protocol(policy),
        _state(policy, [(0.050, 0.010), (0.010, 0.050)]),
        _catalog(run, 2),
    )
    assert result.rankable_checkpoint_count == 2
    assert len(result.eligible_candidates) == 2


def test_rank1_rejects_outer_cv_authority() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=1)
    run = _run("role")
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.rank_lightweight_run_topk(
            run,
            _protocol(policy),
            _state(policy, [(0.02, 0.02)]),
            _catalog(run, 1),
            target_data_role=mdstats.MlcvDataRole.TARGET_OUTER_CV_EVALUATION,
        )
