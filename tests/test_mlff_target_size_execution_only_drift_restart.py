"""Acceptance D: an active screen survives execution-only drift, not method drift.

``validate_target_size_materialization`` used to re-derive the whole immutable
candidate MACE configuration from the *current* optimizer policy, and candidate
loader geometry hashed ``valid_batch_size``.  A mid-screen ``num_workers`` or
harness-validation batch-width change - pure resource retuning - therefore
rejected a scientifically valid materialization during an ordinary resume.

These tests drive the real production owner: the ``select-target-size`` command,
its restart authority, ``resolve_target_size_candidate_for_resume()``, and the
``n1 -> n2`` continuation.  Execution-only drift between invocations must not
create a new scientific trajectory or re-run published cells; genuine method
drift must still fail closed before training resumes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mdstats.training_data._common import TrainingDataInputError

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
import tests.test_mlff_target_size_partial_boundary_resume as resume


def _rewrite_training(config: Path, **keys) -> None:
    """Edit ``[training]`` keys in the real campaign configuration file."""

    text = config.read_text(encoding="utf-8")
    for key, value in keys.items():
        literal = str(value).lower() if isinstance(value, bool) else str(value)
        needle = f"{key} = "
        if needle in text:
            start = text.index(needle)
            end = text.index("\n", start)
            text = text[:start] + f"{key} = {literal}" + text[end:]
        else:
            text = text.replace("[training]\n", f"[training]\n{key} = {literal}\n", 1)
    config.write_text(text, encoding="utf-8")


def _interrupt_after_first_boundary(config: Path):
    """Publish some cells at boundary 1, then interrupt operationally."""

    interrupted = resume._RestartHarness(stop_after=1, stop_at_epoch_limit=3)
    with pytest.raises(OSError):
        resume._select(config, interrupted)
    completed_first = interrupted.rungs_at(1)
    completed_second = interrupted.rungs_at(3)
    assert completed_first, "the first boundary never committed"
    assert len(completed_second) == 1
    return completed_first, completed_second


@pytest.mark.parametrize(
    "drift",
    [
        {"num_workers": 3},
        {"valid_batch_size": 9},
        {"num_workers": 2, "valid_batch_size": 7},
    ],
    ids=["workers", "valid_batch", "both"],
)
def test_d_execution_only_drift_resumes_without_new_scientific_identity(
    tmp_path: Path, drift: dict
):
    """Settings A execute ``n1``; only execution-only settings change; ``n2`` resumes."""

    config, paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)
    interrupted_state = resume._revision(paths).state
    execution_context_before = interrupted_state.execution_context_digest
    generation_before = interrupted_state.generation

    # Only execution-only launch settings change between invocations.
    _rewrite_training(config, **drift)

    resumed = resume._RestartHarness(
        forbidden=(
            {(size, seed, 1) for size, seed in completed_first}
            | {(size, seed, 3) for size, seed in completed_second}
        )
    )
    assert resume._select(config, resumed) == 0

    # No committed boundary and no recovered current-boundary cell was re-run:
    # the drifted invocation authenticated the existing materializations.
    assert resumed.rungs_at(1) == []
    executed_second = resumed.rungs_at(3)
    assert set(executed_second).isdisjoint(set(completed_second))
    # The survivors that still needed work continued from the authenticated
    # predecessor rung rather than starting a fresh trajectory.
    assert executed_second, "the drifted resume executed no continuation"
    assert all(
        resumed.start_epochs[(size, seed, 3)] == 1 for size, seed in executed_second
    )

    final_state = resume._revision(paths).state
    assert final_state.terminal is not None
    # No new scientific generation and no new execution context were created.
    assert final_state.generation == generation_before
    assert final_state.execution_context_digest == execution_context_before


def test_d_execution_only_drift_reaches_the_same_conclusion(tmp_path: Path):
    """Resource retuning changes what runs, never what the screen concludes."""

    drifted_config, drifted_paths = resume._prepared(tmp_path / "drifted")
    completed_first, completed_second = _interrupt_after_first_boundary(drifted_config)
    _rewrite_training(drifted_config, num_workers=3, valid_batch_size=9)
    assert (
        resume._select(
            drifted_config,
            resume._RestartHarness(
                forbidden=(
                    {(size, seed, 1) for size, seed in completed_first}
                    | {(size, seed, 3) for size, seed in completed_second}
                )
            ),
        )
        == 0
    )

    clean_config, clean_paths = resume._prepared(tmp_path / "clean")
    assert resume._select(clean_config, resume._RestartHarness()) == 0

    drifted_state = resume._revision(drifted_paths).state
    clean_state = resume._revision(clean_paths).state
    assert drifted_state.terminal is not None
    assert (
        drifted_state.adopted_reducer_state_digest
        == clean_state.adopted_reducer_state_digest
    )


@pytest.mark.parametrize(
    "drift",
    [
        {"batch_size": 8},
        {"ema": False},
        {"amsgrad": False},
        {"weight_decay": 5.0e-5},
        {"clip_grad": 3.0},
    ],
    ids=["batch_size", "ema", "amsgrad", "weight_decay", "clip_grad"],
)
def test_d_scientific_optimizer_drift_still_fails_closed(tmp_path: Path, drift: dict):
    """Real method drift must be rejected before any continuation trains."""

    config, _paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)

    _rewrite_training(config, **drift)

    forbidden = resume._RestartHarness(
        forbidden={
            (size, seed, epoch)
            for epoch, cells in ((1, completed_first), (3, completed_second))
            for size, seed in cells
        }
    )
    with pytest.raises(Exception) as excinfo:
        resume._select(config, forbidden)
    assert not isinstance(excinfo.value, AssertionError), (
        "scientific drift silently re-ran a published cell instead of failing closed"
    )


def test_d_precision_drift_still_fails_closed(tmp_path: Path):
    """A learned-model dtype change is method drift, not resource retuning."""

    config, _paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)

    text = config.read_text(encoding="utf-8")
    assert "[training]" in text
    text = text.replace("[training]\n", '[training]\ndtype = "float64"\n', 1)
    text = text.replace(
        "[campaign]\n", '[campaign]\nprecision_profile = "double"\n', 1
    )
    config.write_text(text, encoding="utf-8")

    forbidden = resume._RestartHarness(
        forbidden={
            (size, seed, epoch)
            for epoch, cells in ((1, completed_first), (3, completed_second))
            for size, seed in cells
        }
    )
    with pytest.raises(Exception) as excinfo:
        resume._select(config, forbidden)
    assert not isinstance(excinfo.value, AssertionError)


def test_d_target_size_normalization_reference_drift_still_fails_closed(
    tmp_path: Path,
):
    """The screen's own LR/EMA authority is scientific identity."""

    config, _paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)

    text = config.read_text(encoding="utf-8")
    text += (
        "\n[target_data.size_convergence.optimizer_normalization]\n"
        "reference_target_size = 512\n"
        "reference_learning_rate = 5.0e-4\n"
        "reference_ema_decay = 0.999\n"
    )
    config.write_text(text, encoding="utf-8")

    forbidden = resume._RestartHarness(
        forbidden={
            (size, seed, epoch)
            for epoch, cells in ((1, completed_first), (3, completed_second))
            for size, seed in cells
        }
    )
    with pytest.raises(Exception) as excinfo:
        resume._select(config, forbidden)
    assert not isinstance(excinfo.value, AssertionError)


def test_d_general_training_learning_rate_is_not_screen_identity(tmp_path: Path):
    """``[training].learning_rate`` is post-selection authority, not the screen."""

    config, paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)
    before = resume._revision(paths).state.execution_context_digest

    text = config.read_text(encoding="utf-8")
    text = text.replace(
        "[training]\n", "[training]\nlearning_rate = 7.5e-4\nema_decay = 0.995\n", 1
    )
    config.write_text(text, encoding="utf-8")

    resumed = resume._RestartHarness(
        forbidden=(
            {(size, seed, 1) for size, seed in completed_first}
            | {(size, seed, 3) for size, seed in completed_second}
        )
    )
    assert resume._select(config, resumed) == 0
    state = resume._revision(paths).state
    assert state.terminal is not None
    assert state.execution_context_digest == before
