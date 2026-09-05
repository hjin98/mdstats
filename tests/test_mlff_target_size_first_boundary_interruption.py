"""Absence of a checkpoint is not an empty checkpoint authority.

A production `select-target-size` run once died before it made any useful
candidate progress with ``TrainingDataInputError: Checkpoint catalog cannot be
empty.`` The defect was not a missing empty-container special case. It was a
state-model error: "no durable checkpoint has been produced yet" was represented
as though a checkpoint authority existed and happened to contain zero members,
so restart read absence of state as malformed state.

The distinction the current owners must keep is three-way:

.. code-block:: text

    no accepted boundary yet         -> no continuation authority exists
                                     -> retry the first rung fresh
    complete authenticated boundary  -> continue from exactly it
    claimed boundary, bytes missing  -> corruption; fail closed

These tests exercise the real `select-target-size` scheduling, the real rung
request the production trainer receives, and the real boundary binder. Only the
MACE numerical work is substituted, below those owners.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    load_target_size_campaign_revision,
)


class _InterruptingTrainer:
    """Die at the first rung, exactly as a killed TRAIN2 child would.

    Partial checkpoint bytes are left behind on purpose: an interrupted attempt
    really does leave scratch, and the point of the test is that scratch never
    becomes authority.
    """

    def __init__(self) -> None:
        self.requests: list[object] = []
        self.workspaces: list[Path] = []

    def __call__(self, request):
        self.requests.append(request)
        self.workspaces.append(Path(request.checkpoint_directory))
        (request.checkpoint_directory / "candidate_epoch-0.pt").write_bytes(
            b"partial-attempt-bytes"
        )
        (request.checkpoint_directory / "train2_runtime.json").write_text(
            json.dumps({"schema": "not-a-real-summary"}), encoding="utf-8"
        )
        raise KeyboardInterrupt("simulated interruption before any boundary")


class _RecordingHarness(p4d._BoundedNumericalHarness):
    """The ordinary bounded harness, plus what the first rung was asked to do."""

    def __init__(self) -> None:
        super().__init__()
        self.start_epochs: list[int] = []
        self.first_workspace_contents: list[tuple[str, ...]] = []

    def train(self, request):
        self.start_epochs.append(int(request.start_epoch))
        self.first_workspace_contents.append(
            tuple(
                sorted(
                    path.name
                    for path in Path(request.checkpoint_directory).iterdir()
                )
            )
        )
        return super().train(request)


def _prepared(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    _cfg, paths = cli._load_config(config)
    return config, paths


def _revision(paths):
    store = CampaignStore(paths.state_db)
    try:
        return load_target_size_campaign_revision(store)
    finally:
        store.close()


def test_interruption_before_any_boundary_creates_no_checkpoint_authority(
    tmp_path: Path,
):
    config, paths = _prepared(tmp_path)
    before = _revision(paths)

    interrupting = _InterruptingTrainer()
    with pytest.raises(KeyboardInterrupt):
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=interrupting,
            _external_inference_evaluator=None,
        )
    assert interrupting.requests, "the first rung never reached the trainer"

    after = _revision(paths)
    # No boundary was accepted, so no scientific evidence exists: the reducer did
    # not advance and no head was adopted. An interrupted attempt is not a
    # result, and it is certainly not a scientific failure.
    assert after.state.generation == before.state.generation
    assert after.state.adopted_execution_head_digest is None
    assert after.state.terminal is None
    assert after.state.lifecycle in (
        TargetSizeLifecycle.AUTHORITIES_BOUND,
        TargetSizeLifecycle.SCREEN_ACTIVE,
    )

    # The partial attempt bytes exist on disk, which is exactly the condition
    # under which the original bug reinterpreted scratch as authority.
    workspace = interrupting.workspaces[0]
    assert (workspace / "candidate_epoch-0.pt").is_file()


def test_the_retry_runs_the_first_rung_fresh_and_ignores_partial_bytes(
    tmp_path: Path,
):
    config, paths = _prepared(tmp_path)

    interrupting = _InterruptingTrainer()
    with pytest.raises(KeyboardInterrupt):
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=interrupting,
            _external_inference_evaluator=None,
        )
    stale_workspace = interrupting.workspaces[0]
    assert (stale_workspace / "candidate_epoch-0.pt").is_file()

    harness = _RecordingHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )

    assert harness.start_epochs, "the retry never re-entered the first rung"
    # The first rung is entered fresh: there is no predecessor to continue from,
    # so no continuation start epoch and no continuation flag can appear.
    assert harness.start_epochs[0] == 0
    # ...and it does not inherit the interrupted attempt's uncommitted bytes.
    assert "candidate_epoch-0.pt" not in harness.first_workspace_contents[0]
    assert "train2_runtime.json" not in harness.first_workspace_contents[0]

    revision = _revision(paths)
    assert revision.state.adopted_execution_head_digest is not None


def test_the_first_rung_has_no_continuation_path_at_all(tmp_path: Path):
    """The two states are structurally different, not two modes of one path.

    The resume owner exists only for a rung that has an authenticated exact
    predecessor. Asking it to resume the first rung is not a special case it
    handles leniently -- there is nothing to resume, and saying so is what keeps
    "nothing yet" from being represented as an empty continuation authority.

    Corrupt, foreign, and tampered *predecessor* continuation state is covered
    at the same owner by the P3A4/P3A7 restart negatives; this closes the other
    half of the distinction.
    """

    import tests.test_mlff_target_size_execution_p3f as p3f
    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.target_size_execution import (
        initialize_target_size_screen,
        resolve_target_size_candidate_for_resume,
    )

    env = p3f._screen_env(tmp_path)
    initialize_target_size_screen(
        env["root"], env["aggregate"], env["context"], env["common"]
    )
    definition = env["aggregate"].definition
    target_size = definition.qualified_candidate_sizes[0]
    optimizer_seed = definition.policy.optimizer_seeds[0]

    with pytest.raises(TrainingDataInputError) as excinfo:
        resolve_target_size_candidate_for_resume(
            env["root"],
            env["authority"],
            boundary_epoch=env["schedule"].n1,
            target_size=int(target_size),
            optimizer_seed=int(optimizer_seed),
            state=env["aggregate"].reducer_state,
        )
    assert "no predecessor continuation" in str(excinfo.value)
