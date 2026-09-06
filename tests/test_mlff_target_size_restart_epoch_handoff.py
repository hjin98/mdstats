"""The target-size launcher must state the epoch it intends to restart from.

A production ``select-target-size`` run committed its first fidelity boundary
and then died at the next one with ``KeyError: 'MDSTATS_MACE_RESTART_EPOCH'``
inside the qualified MACE restart patch.  Nothing was wrong with the
checkpoint, the predecessor authentication, or the continuation workspace: the
launcher passed ``--restart_latest`` without ever saying which raw checkpoint
epoch the run was supposed to resume from, so the wrapper's fail-closed
verifier had nothing to verify against.

The two responsibilities are deliberately separate and both are required.  The
launcher owns *intent* -- it holds the authenticated completed-epoch boundary
P3 resolved -- and the wrapper owns *verification* of what MACE actually
loaded.  These tests pin the launcher half of that contract, including the
completed-epoch to raw-checkpoint-epoch translation:

.. code-block:: text

    request.start_epoch          completed predecessor epochs (P3 / TRAIN2)
    MDSTATS_MACE_RESTART_EPOCH   request.start_epoch - 1 (zero-based MACE)

Only the subprocess is substituted; the real production trainer builds the
real argv and the real child environment from a real materialized candidate.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
import tests.test_mlff_target_size_execution_p3e as p3e
import tests.test_mlff_target_size_p3_realized_mace_architecture as arch
from mdstats.training_data import campaign_target_size_runtime as runtime
from mdstats.training_data.campaign_target_size_runtime import (
    MaceTargetSizeBoundaryTrainer,
    TargetSizeRungRequest,
)
from mdstats.training_data.precision_runtime import (
    MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE,
)
from mdstats.training_data.target_size_execution import target_size_rung_plan


class _LaunchSpy:
    """Stand in for the child process only; everything above it is production."""

    def __init__(self) -> None:
        self.commands: list[list[str]] = []
        self.environments: list[dict[str, str]] = []

    def __call__(self, command, **kwargs):
        self.commands.append(list(command))
        self.environments.append(dict(kwargs["env"]))
        return SimpleNamespace(returncode=0)


@pytest.fixture
def candidate(tmp_path: Path):
    """One real materialized candidate, as the production launcher receives it."""

    env = p3e._env(tmp_path, batch_size=1)
    trajectory, materialization, directory = arch._materialize(
        env, tmp_path, target_size=2, optimizer_seed=1
    )
    return SimpleNamespace(
        env=env,
        trajectory=trajectory,
        materialization=materialization,
        directory=directory,
    )


def _launch(candidate, tmp_path: Path, monkeypatch, *, start_epoch: int,
            boundary: int, environment=None) -> _LaunchSpy:
    spy = _LaunchSpy()
    monkeypatch.setattr(runtime.subprocess, "run", spy)
    monkeypatch.setattr(mdstats, "load_train2_runtime_summary", lambda directory: None)
    checkpoint_directory = tmp_path / f"train2-start{start_epoch}" / "checkpoints"
    trainer = MaceTargetSizeBoundaryTrainer(
        wrapper_path=tmp_path / "mdstats-mace-train", environment=environment
    )
    trainer(
        TargetSizeRungRequest(
            plan=target_size_rung_plan(
                candidate.trajectory, candidate.env["schedule"], boundary_epoch=boundary
            ),
            trajectory=candidate.trajectory,
            materialization=candidate.materialization,
            materialization_directory=candidate.directory,
            checkpoint_directory=checkpoint_directory,
            start_epoch=start_epoch,
            optimizer_policy=candidate.env["optimizer"],
        )
    )
    assert len(spy.commands) == 1
    return spy


def test_fresh_rung_launches_with_no_restart_authority_at_all(
    candidate, tmp_path: Path, monkeypatch
):
    """A first rung has no predecessor, so it may not inherit one either.

    A stale value can reach the child from the parent shell (an earlier manual
    restart) or from an injected launcher environment.  Either one would make
    the wrapper verify this fresh run against somebody else's checkpoint.
    """

    monkeypatch.setenv(MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE, "7")
    spy = _launch(
        candidate,
        tmp_path,
        monkeypatch,
        start_epoch=0,
        boundary=candidate.env["schedule"].n1,
        environment={MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE: "99"},
    )
    assert "--restart_latest" not in spy.commands[0]
    assert MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE not in spy.environments[0]


@pytest.mark.parametrize(
    ("start_epoch", "boundary", "expected"),
    [(1, 3, "0"), (3, 10, "2")],
)
def test_continuation_exports_the_raw_predecessor_checkpoint_epoch(
    candidate, tmp_path: Path, monkeypatch, start_epoch, boundary, expected
):
    """``start_epoch`` counts completed epochs; MACE counts checkpoints from 0.

    The reported failure crossed boundary 1 -> boundary 3, where one completed
    epoch means MACE must load raw checkpoint epoch 0 and resume at epoch 1.
    Exporting ``start_epoch`` unchanged would be an off-by-one that either
    replays or skips an optimizer epoch.
    """

    monkeypatch.delenv(MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE, raising=False)
    spy = _launch(
        candidate,
        tmp_path,
        monkeypatch,
        start_epoch=start_epoch,
        boundary=boundary,
    )
    assert "--restart_latest" in spy.commands[0]
    assert spy.environments[0][MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE] == expected


def test_authenticated_request_state_overrides_ambient_restart_epoch(
    candidate, tmp_path: Path, monkeypatch
):
    """Authenticated P3 state wins; ambient state never reaches MACE.

    Passing the conflict through would hand the wrapper a contradiction it
    could only resolve by failing, and would make a correct continuation depend
    on the cleanliness of the parent shell.
    """

    monkeypatch.setenv(MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE, "7")
    spy = _launch(
        candidate,
        tmp_path,
        monkeypatch,
        start_epoch=3,
        boundary=10,
        environment={MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE: "99"},
    )
    assert spy.environments[0][MACE_RESTART_EPOCH_ENVIRONMENT_VARIABLE] == "2"
