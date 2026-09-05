"""One fresh workspace, driven through the whole public campaign.

Every package had its own assembled test, and every one of them passed while the
assembled *campaign* did not work: the cross-package transitions - what `status`
says between stages, what survives a restart, what storage may touch while a
stage is current, and whether the lifecycle even mentions the stage that comes
next - were nobody's test. This is that test.

It drives the real parser and dispatch from an empty workspace forward, and it
re-observes and reopens between every stage rather than at the end, because a
campaign that only works when run start-to-finish in one process is not
restartable and this is the only place that would notice.

The numerical seams are the accepted bounded ones and sit below the owners under
acceptance; the lifecycle, currentness, persistence, storage and observation
paths are all production code.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import tests._mlff_post_selection_fixture as p5
import tests._mlff_qualification_fixture as fx
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_lifecycle import (
    LifecycleObservationState,
    project_campaign_lifecycle,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    load_target_size_campaign_revision,
)

_REPO = Path(__file__).resolve().parents[1]


class _Observer:
    """Observe and reopen between stages, and remember what was seen."""

    def __init__(self, config: Path) -> None:
        self.config = config
        _cfg, self.paths = cli._load_config(config)
        self.seen: list[tuple[str, str | None, str | None]] = []

    def snapshot(self):
        """Reopen the campaign from scratch and project its lifecycle."""

        store = CampaignStore(self.paths.state_db, create=False)
        try:
            return project_campaign_lifecycle(self.paths, store)
        finally:
            store.close()

    def revision(self):
        store = CampaignStore(self.paths.state_db, create=False)
        try:
            return load_target_size_campaign_revision(store)
        finally:
            store.close()

    def observe(self, label: str):
        """`status` twice, then record what the lifecycle says."""

        before = self._managed()
        assert cli.main(["--config", str(self.config), "status"]) == 0
        assert cli.main(["--config", str(self.config), "status"]) == 0
        assert self._managed() == before, f"status mutated state at {label}"
        snapshot = self.snapshot()
        self.seen.append((label, snapshot.next_command, snapshot.state_revision))
        return snapshot

    def _managed(self) -> dict[str, int]:
        return {
            str(path.relative_to(self.paths.workspace)): (
                path.stat().st_size if path.is_file() else -1
            )
            for path in sorted(self.paths.workspace.rglob("*"))
        }


def _storage_is_safe_here(config: Path) -> None:
    """Storage observation and a dry run are admissible at any point."""

    assert cli.main(["--config", str(config), "storage", "report"]) == 0
    assert (
        cli.main(
            ["--config", str(config), "storage", "cleanup", "--tier", "safe", "--dry-run"]
        )
        == 0
    )


@pytest.mark.slow
def test_the_public_campaign_runs_end_to_end_with_restart_at_every_boundary(
    tmp_path: Path, capsys
):
    template = fx.fixture_config_text()

    # --- 1-2. fresh workspace, then prepare -------------------------------
    from unittest.mock import patch

    with patch.object(p4d, "_CONFIG", template):
        config, workspace = p4d._fixture_campaign(tmp_path)
    observer = _Observer(config)

    initial = observer.observe("before prepare")
    assert initial.next_command == "prepare"
    assert initial.generation is None

    assert p4d._run(config, "prepare") == 0

    # --- 3-5. reopen, observe, and let storage look around ----------------
    prepared = observer.observe("after prepare")
    assert prepared.generation == 1
    assert prepared.step("current_prepare").state == (
        LifecycleObservationState.COMPLETE
    )
    assert prepared.next_command == "select-target-size"
    _storage_is_safe_here(config)

    # --- 6-8. select, reopen, observe -------------------------------------
    screen = p5._SelectedSizeScreenHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    selected = observer.observe("after select")
    assert selected.generation == 1, "screening must not advance the generation"
    assert selected.step("target_size_selection").state == (
        LifecycleObservationState.COMPLETE
    )
    assert selected.next_command == "cross-validate"
    revision = observer.revision()
    assert revision.state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
    selected_membership = revision.state.terminal.selected_membership_digest
    _storage_is_safe_here(config)

    # --- 9-11. cross-validate, reopen, observe ----------------------------
    post = p5.PostSelectionHarness()
    assert p5.run_cross_validate(config, post) == 0
    validated = observer.observe("after cross-validate")
    assert validated.step("post_selection_cv").state == (
        LifecycleObservationState.COMPLETE
    )
    assert validated.next_command == "train-production"
    # Cross-validation is a statement about the method, not about the data.
    assert (
        observer.revision().state.terminal.selected_membership_digest
        == selected_membership
    )

    # --- 12-15. final production, freeze, reopen, observe -----------------
    assert p5.run_train_production(config, post) == 0
    produced = observer.observe("after train-production")
    assert produced.step("final_production").state == (
        LifecycleObservationState.COMPLETE
    )
    # The campaign is emphatically not complete here: the product is frozen but
    # unqualified, and this is exactly where the old lifecycle stopped.
    assert produced.next_command == "qualification run"
    assert (
        observer.revision().state.terminal.selected_membership_digest
        == selected_membership
    )
    _storage_is_safe_here(config)

    # --- 16. qualification status, before qualification has ever run ------
    harness = fx.QualificationHarness()
    fx.attach_labels(harness, config)
    before_status = observer._managed()
    assert fx.run_qualification_command(config, "status", harness=harness) == 0
    assert observer._managed() == before_status, "qualification status mutated state"

    # --- 17-18. qualification run stops truthfully at waiting_for_reference
    assert fx.run_qualification_command(config, "run", harness=harness) == 0
    waiting = observer.observe("after qualification run (waiting)")
    qualification = waiting.step("post_production_qualification")
    assert qualification.state == LifecycleObservationState.WAITING, (
        qualification.message
    )
    assert "waiting for independent external reference" in qualification.message
    # Waiting is a nonterminal product state: it is neither a failure nor an
    # invitation to activate locked evidence.
    assert waiting.terminal_step is None
    assert waiting.next_command == "qualification run"

    # --- 19. a genuine process boundary, not just a new store handle ------
    completed = subprocess.run(
        [
            sys.executable,
            "tools/mdstats-mlff-campaign.py",
            "--config",
            str(config),
            "status",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO),
        check=True,
    )
    assert "qualification" in completed.stdout
    assert "activate-locked" not in completed.stdout

    # Nothing across the whole campaign regressed the current revision, and the
    # generation never moved after preparation.
    revisions = [item[2] for item in observer.seen if item[2] is not None]
    collapsed = [
        value
        for index, value in enumerate(revisions)
        if index == 0 or value != revisions[index - 1]
    ]
    # A revision the campaign has moved past never comes back as current.
    assert len(collapsed) == len(set(collapsed)), collapsed
    assert observer.revision().state.generation == 1

    with capsys.disabled():
        print("\n[assembled lifecycle] observed next-command at each boundary:")
        for label, next_command, _revision in observer.seen:
            print(f"  {label:<38} -> {next_command}")
        print(
            "  NOTE: supplying the reference bundle and reaching a terminal "
            "release verdict is blocked by the P7 bounded-fixture relaxation "
            "defect recorded in the integration progress note."
        )
