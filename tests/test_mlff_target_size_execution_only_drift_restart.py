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
        # The needle is anchored to the start of a line: an unanchored
        # ``"ema = "`` also matches inside ``schema = "..."``.
        needle = f"\n{key} = "
        if needle in text:
            start = text.index(needle) + 1
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


# ---------------------------------------------------------------------------
# R6-A: an unaccepted first-rung materialization is attempt scratch
# ---------------------------------------------------------------------------


class _MaterializeThenCrashHarness(resume._RestartHarness):
    """Crash inside the trainer, after real materialization has been published.

    ``_execute_candidate_cell`` materializes the candidate and only then calls
    the trainer, so raising here leaves exactly the reported state: immutable
    materialization bytes on disk under the scientific trajectory path, and no
    accepted completion, progress, or head for that cell.
    """

    def train(self, request):
        raise OSError("simulated interruption after materialization")


def _materialization_dirs(paths, revision) -> list[Path]:
    root = resume._screen_root(paths, revision) / "bulk" / "materializations"
    return sorted(p for p in root.glob("*") if p.is_dir()) if root.is_dir() else []


def _accepted_progress_files(paths, revision) -> list[Path]:
    root = resume._screen_root(paths, revision) / "progress"
    return sorted(root.rglob("*.json")) if root.is_dir() else []


@pytest.mark.parametrize(
    "drift",
    [{"num_workers": 5}, {"valid_batch_size": 11}],
    ids=["workers", "valid_batch"],
)
def test_r6a_unaccepted_first_rung_materialization_does_not_block_retry(
    tmp_path: Path, drift: dict
):
    """The reported collision, reproduced and closed at the production owner."""

    config, paths = resume._prepared(tmp_path)

    with pytest.raises(OSError):
        resume._select(config, _MaterializeThenCrashHarness())

    revision = resume._revision(paths)
    # The interrupted attempt really did publish materialization bytes ...
    stale = _materialization_dirs(paths, revision)
    assert stale, "the fixture never reached real materialization"
    stale_config_bytes = {
        path: path.read_bytes()
        for directory in stale
        for path in directory.glob("mace_config_*.yaml")
    }
    assert stale_config_bytes
    # ... and accepted nothing.
    assert _accepted_progress_files(paths, revision) == []
    assert revision.state.terminal is None

    # Only execution-only launch settings change.
    _rewrite_training(config, **drift)

    resumed = resume._RestartHarness()
    assert resume._select(config, resumed) == 0

    # The first rung retried fresh rather than failing create-or-verify, and it
    # retried from the beginning because no continuation authority existed.
    first_rung = resumed.rungs_at(1)
    assert first_rung, "the first boundary never re-executed"
    assert all(resumed.start_epochs[(size, seed, 1)] == 0 for size, seed in first_rung)

    final = resume._revision(paths).state
    assert final.terminal is not None
    # No new scientific generation or execution context was minted to get past
    # the stale attempt.
    assert final.generation == revision.state.generation
    assert final.execution_context_digest == revision.state.execution_context_digest
    # The stale bytes were replaced by the retry's own configuration.
    assert any(
        path.read_bytes() != original
        for path, original in stale_config_bytes.items()
        if path.is_file()
    ) or not any(path.is_file() for path in stale_config_bytes)


def test_r6a_accepted_progress_is_recovered_and_its_materialization_survives(
    tmp_path: Path,
):
    """Accepted evidence is owned by recovery; a retry must not delete it."""

    config, paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)

    revision = resume._revision(paths)
    accepted_before = {
        path: path.read_bytes()
        for directory in _materialization_dirs(paths, revision)
        for path in directory.glob("mace_config_*.yaml")
    }
    assert accepted_before
    assert _accepted_progress_files(paths, revision)

    _rewrite_training(config, num_workers=6)

    resumed = resume._RestartHarness(
        forbidden=(
            {(size, seed, 1) for size, seed in completed_first}
            | {(size, seed, 3) for size, seed in completed_second}
        )
    )
    assert resume._select(config, resumed) == 0
    # Every accepted materialization is byte-identical afterwards: the retry
    # neither deleted nor rewrote a durable parent.
    for path, original in accepted_before.items():
        assert path.is_file(), f"accepted materialization {path} was deleted"
        assert path.read_bytes() == original


# ---------------------------------------------------------------------------
# R6-C: general [training].ema_decay is inert for target-size science
# ---------------------------------------------------------------------------


def test_r6c_general_ema_decay_is_not_screen_identity_when_ema_is_disabled(
    tmp_path: Path,
):
    """An EMA-disabled screen survives a post-selection-only EMA-decay edit.

    With EMA off there is no EMA state to decay, so the generic value has no
    target-size effect at all - but it used to be written into the immutable
    candidate configuration and compared during scientific materialization
    replay, which let this edit reject an accepted trajectory at ``n2``.
    """

    config, paths = resume._prepared(tmp_path)
    _rewrite_training(config, ema=False)
    completed_first, completed_second = _interrupt_after_first_boundary(config)
    before = resume._revision(paths).state

    _rewrite_training(config, ema_decay=0.987)

    resumed = resume._RestartHarness(
        forbidden=(
            {(size, seed, 1) for size, seed in completed_first}
            | {(size, seed, 3) for size, seed in completed_second}
        )
    )
    assert resume._select(config, resumed) == 0
    executed_second = resumed.rungs_at(3)
    assert executed_second
    assert all(
        resumed.start_epochs[(size, seed, 3)] == 1 for size, seed in executed_second
    )
    final = resume._revision(paths).state
    assert final.terminal is not None
    assert final.generation == before.generation
    assert final.execution_context_digest == before.execution_context_digest


def test_r6c_ema_disabled_candidate_config_omits_ema_decay(tmp_path: Path):
    """The inert key is absent from the immutable configuration entirely."""

    import json

    config, paths = resume._prepared(tmp_path)
    _rewrite_training(config, ema=False)
    assert resume._select(config, resume._RestartHarness()) == 0

    revision = resume._revision(paths)
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for directory in _materialization_dirs(paths, revision)
        for path in directory.glob("mace_config_*.yaml")
    ]
    assert payloads, "the screen materialized no candidate configuration"
    for payload in payloads:
        assert payload["ema"] is False
        assert "ema_decay" not in payload


def test_r6c_ema_enabled_candidate_config_carries_the_realized_beta(tmp_path: Path):
    """With EMA on, the realized normalization beta is present and scientific."""

    import json

    config, paths = resume._prepared(tmp_path)
    assert resume._select(config, resume._RestartHarness()) == 0

    revision = resume._revision(paths)
    payloads = [
        json.loads(path.read_text(encoding="utf-8"))
        for directory in _materialization_dirs(paths, revision)
        for path in directory.glob("mace_config_*.yaml")
    ]
    assert payloads
    for payload in payloads:
        assert payload["ema"] is True
        assert 0.0 < float(payload["ema_decay"]) < 1.0
    # The realized beta is size-normalized, so candidates of different N do not
    # all carry the generic configured value.
    assert len({float(p["ema_decay"]) for p in payloads}) > 1


@pytest.mark.parametrize("enabled", [True, False], ids=["off_to_on", "on_to_off"])
def test_r6c_toggling_ema_is_genuine_scientific_drift(tmp_path: Path, enabled: bool):
    """EMA enable/disable changes what EVAL2 consumes, so it must reject."""

    config, _paths = resume._prepared(tmp_path)
    _rewrite_training(config, ema=not enabled)
    completed_first, completed_second = _interrupt_after_first_boundary(config)

    _rewrite_training(config, ema=enabled)

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


def test_r6c_reference_ema_decay_drift_still_fails_closed(tmp_path: Path):
    """With EMA on, the *normalization* reference beta is real screen science."""

    config, _paths = resume._prepared(tmp_path)
    completed_first, completed_second = _interrupt_after_first_boundary(config)

    text = config.read_text(encoding="utf-8")
    text += (
        "\n[target_data.size_convergence.optimizer_normalization]\n"
        "reference_ema_decay = 0.9995\n"
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
