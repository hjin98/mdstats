"""A claimed continuation whose bytes are gone is corruption, never a fresh start.

This is the other half of the exact-boundary contract. Once a boundary has been
accepted, later rungs are its scientific descendants: `n2` continues from exactly
the `n1` state, and the trajectory identity means nothing if that link can be
quietly re-forged. The failure mode that matters is not a crash - it is a silent
restart from epoch zero, which produces a different trajectory under the same
identity and reports it as the same experiment.

So each required predecessor component is destroyed in turn, through the
assembled campaign rather than at a helper, and the screen must fail closed with
the reducer untouched. The negatives at the resume owner itself (tampered
trajectory, foreign optimizer convention) are covered by the P3A4/P3A7 suites;
what is established here is that the *campaign* inherits them.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import TrainingDataError
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    load_target_size_campaign_revision,
)


class _StopsAfterFirstBoundary(p4d._BoundedNumericalHarness):
    """Complete the first boundary for every cell, then die like a killed job."""

    def __init__(self, first_boundary: int) -> None:
        super().__init__()
        self._first_boundary = int(first_boundary)

    def train(self, request):
        if int(request.plan.execution_epoch_limit) > self._first_boundary:
            raise KeyboardInterrupt("interrupted before the continuation rung")
        return super().train(request)


class _RecordingHarness(p4d._BoundedNumericalHarness):
    """An ordinary harness that remembers the start epoch of every rung."""

    def __init__(self) -> None:
        super().__init__()
        self.start_epochs: list[tuple[int, int]] = []

    def train(self, request):
        self.start_epochs.append(
            (int(request.plan.execution_epoch_limit), int(request.start_epoch))
        )
        return super().train(request)


def _revision(paths):
    store = CampaignStore(paths.state_db, create=False)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def _screen_stopped_after_first_boundary(tmp_path: Path):
    """A campaign with one accepted boundary and an open continuation ahead."""

    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    _cfg, paths = cli._load_config(config)

    first_boundary = 1
    harness = _StopsAfterFirstBoundary(first_boundary)
    with pytest.raises(KeyboardInterrupt):
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )

    revision = _revision(paths)
    assert revision.state.lifecycle is TargetSizeLifecycle.SCREEN_ACTIVE
    assert revision.state.adopted_execution_head_digest is not None
    return config, paths, revision


def _snapshot_files(paths, revision) -> list[Path]:
    root = paths.workspace / revision.state.execution_root
    snapshots = root / "bulk" / "snapshots"
    assert snapshots.is_dir(), "the accepted boundary published no snapshot"
    return sorted(path for path in snapshots.rglob("*") if path.is_file())


@pytest.mark.parametrize(
    ("label", "suffix", "mode"),
    [
        ("raw checkpoint deleted", ".pt", "delete"),
        ("raw checkpoint corrupted", ".pt", "corrupt"),
        ("runtime summary deleted", "train2_runtime.json", "delete"),
        ("runtime summary corrupted", "train2_runtime.json", "corrupt"),
        ("continuation companion deleted", "train2_runtime.pt", "delete"),
        ("continuation companion corrupted", "train2_runtime.pt", "corrupt"),
    ],
)
def test_a_destroyed_predecessor_component_fails_closed(
    tmp_path: Path, label: str, suffix: str, mode: str
):
    config, paths, before = _screen_stopped_after_first_boundary(tmp_path)

    victims = [
        path
        for path in _snapshot_files(paths, before)
        if path.name == suffix
        or (suffix == ".pt" and path.suffix == ".pt" and "train2_runtime" not in path.name)
    ]
    if not victims:
        pytest.skip(f"this boundary published no {suffix} component")
    victim = victims[0]
    if mode == "delete":
        victim.unlink()
    else:
        victim.write_bytes(b"corrupted-continuation-bytes")

    resumed = _RecordingHarness()
    with pytest.raises(TrainingDataError):
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=resumed.train,
            _external_inference_evaluator=resumed.evaluate,
        )

    # The decisive property: no later rung was started from scratch. A silent
    # fresh start would be a different trajectory wearing the same identity.
    assert all(
        start == 0 for boundary, start in resumed.start_epochs if boundary == 1
    ), resumed.start_epochs
    assert not [
        (boundary, start)
        for boundary, start in resumed.start_epochs
        if boundary > 1 and start == 0
    ], f"{label}: a continuation rung fresh-started from epoch zero"

    # ...and the reducer is exactly where the accepted evidence left it.
    after = _revision(paths)
    assert after.state.adopted_execution_head_digest == (
        before.state.adopted_execution_head_digest
    )
    assert after.state.adopted_reducer_state_digest == (
        before.state.adopted_reducer_state_digest
    )
    assert after.state.terminal is None
    assert after.state.generation == before.state.generation


def test_a_foreign_predecessor_summary_is_refused(tmp_path: Path):
    """Well-formed state from another candidate is still not this ancestry."""

    config, paths, before = _screen_stopped_after_first_boundary(tmp_path)
    summaries = [
        path
        for path in _snapshot_files(paths, before)
        if path.name == "train2_runtime.json"
    ]
    assert len(summaries) >= 2, (
        "this check needs two candidate snapshots to swap between"
    )
    first, second = summaries[0], summaries[1]
    payload = json.loads(second.read_text(encoding="utf-8"))
    if payload == json.loads(first.read_text(encoding="utf-8")):
        pytest.skip("the two candidate summaries are byte-identical")
    first.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    resumed = _RecordingHarness()
    with pytest.raises(TrainingDataError):
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=resumed.train,
            _external_inference_evaluator=resumed.evaluate,
        )
    assert not [
        (boundary, start)
        for boundary, start in resumed.start_epochs
        if boundary > 1 and start == 0
    ]
    after = _revision(paths)
    assert after.state.adopted_execution_head_digest == (
        before.state.adopted_execution_head_digest
    )
    assert after.state.terminal is None


def test_an_ordinary_interruption_leaves_the_reducer_untouched(tmp_path: Path):
    """Case 8: process death is not a scientific result.

    An interrupted screen must be resumable into exactly the same experiment,
    and the accepted evidence it already produced must be reused rather than
    recomputed.
    """

    config, paths, before = _screen_stopped_after_first_boundary(tmp_path)

    resumed = _RecordingHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=resumed.train,
            _external_inference_evaluator=resumed.evaluate,
        )
        == 0
    )
    # The accepted first boundary was not re-executed...
    assert all(boundary > 1 for boundary, _start in resumed.start_epochs), (
        resumed.start_epochs
    )
    # ...and every continuation rung continued rather than restarted.
    assert all(start > 0 for _boundary, start in resumed.start_epochs), (
        resumed.start_epochs
    )
    after = _revision(paths)
    assert after.state.generation == before.state.generation
