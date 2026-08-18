from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.training_data.progress_timing import ProgressRateTracker
from tests.test_mlff_data9a9a_production_model_sweep import (
    _CountingCalculator,
    _inputs,
    _provider,
)


def test_data6_eta_uses_cumulative_work_rate_not_callback_burst_rate() -> None:
    tracker = ProgressRateTracker(
        completed=0,
        started_at=0.0,
        minimum_recent_window_seconds=1.0,
    )
    # Reproduce the reported order of magnitude: 3,100 frames at ~20.07 frame/s.
    elapsed = 3100.0 / 20.07
    first = tracker.snapshot(completed=3100, total=36759, now=elapsed)
    assert first.average_rate == pytest.approx(20.07)
    assert first.recent_rate == pytest.approx(20.07)
    assert first.eta_seconds == pytest.approx((36759 - 3100) / 20.07)
    assert first.eta_seconds / 60.0 == pytest.approx(27.95, rel=2.0e-3)

    # A hundred already-computed completion callbacks arrive 50 ms later.  The
    # recent estimator must not interpret callback draining as numerical work.
    burst = tracker.snapshot(completed=3200, total=36759, now=elapsed + 0.05)
    assert burst.recent_rate == pytest.approx(first.recent_rate)
    assert burst.recent_rate < 100.0
    assert burst.eta_seconds is not None
    assert burst.eta_seconds > 20.0 * 60.0


def test_progress_rate_tracker_resets_after_restored_checkpoint() -> None:
    tracker = ProgressRateTracker(completed=0, started_at=0.0)
    tracker.reset(completed=3000, now=100.0)
    timing = tracker.snapshot(completed=3100, total=36759, now=105.0)
    assert timing.average_rate == pytest.approx(20.0)
    assert timing.recent_rate == pytest.approx(20.0)
    assert timing.eta_seconds == pytest.approx((36759 - 3100) / 20.0)


def test_model_sweep_coalesces_batched_progress_callbacks(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    provider = _provider(_CountingCalculator())
    events: list[tuple[int, int, str]] = []
    result = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        tmp_path / "coalesced-progress",
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=128,
            artifact_shard_size=1,
            checkpoint_interval=1,
        ),
        progress_callback=lambda completed, total, uid: events.append(
            (completed, total, uid)
        ),
    )
    assert result.complete
    non_restore = [event for event in events if event[2] != "restored-checkpoint"]
    # One numerical batch may create many shard records, but progress is emitted
    # once after that persistence drain rather than once per record.
    assert len(non_restore) == 1
    assert non_restore[0][0] == len(result.checkpoint.completed_frame_uids)
    assert non_restore[0][1] == len(result.checkpoint.plan.requested_frame_uids)


def test_generic_progress_reporter_ignores_immediate_restart_burst(monkeypatch, capsys) -> None:
    import mdstats.training_data.campaign_cli as campaign_cli

    times = iter((100.0, 100.01, 110.01))
    monkeypatch.setattr(campaign_cli.time, "monotonic", lambda: next(times))
    reporter = campaign_cli._ProgressReporter("TEST", 3)
    reporter.item_done(1, "cached", "already complete")
    first = capsys.readouterr().out
    assert "eta=--:--:--" in first

    reporter.item_done(2, "real", "computed")
    second = capsys.readouterr().out
    # The first cached item is the baseline; one real item in ten seconds leaves
    # one item and therefore predicts ~10 s, not ~5 s from counting the cache hit.
    assert "eta=00:00:10" in second
