"""P4-G assembled integration: the complete current target-size lifecycle in one
flow, through the real CLI entrypoint, the real campaign store, and the real
P1/P2/P3 and storage owners.

`prepare` -> `select-target-size` -> terminal projection -> fresh-process reload
-> storage accounting -> safe cleanup -> replay, with only MACE's numerical work
substituted below the accepted owner boundary.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from types import SimpleNamespace

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    load_target_size_campaign_history,
    load_target_size_campaign_revision,
)
from mdstats.training_data.campaign_target_size_runtime import (
    build_current_target_size_authorities,
)
from mdstats.training_data.campaign_target_size_terminal import (
    validate_terminal_projection,
)
from mdstats.training_data.target_size_execution import TargetSizeExecutionResolver


def test_p4g_assembled_current_target_size_lifecycle(tmp_path: Path, capsys):
    config, workspace = p4d._fixture_campaign(tmp_path)
    state_db = workspace / ".mdstats" / "campaign.sqlite3"

    # 1. The real CLI entrypoint drives preparation.
    assert cli.main(["--config", str(config), "prepare"]) == 0
    output = capsys.readouterr().out
    assert "does not select a target size" in output

    store = CampaignStore(state_db)
    try:
        prepared = load_target_size_campaign_revision(store)
        assert prepared.state.regime is TargetSizeRegime.CURRENT
        assert prepared.state.terminal is None
    finally:
        store.close()

    # 2. The screen runs to a terminal P2 outcome.
    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    assert harness.rungs and harness.inferences

    # 3. A fresh store handle re-derives the terminal projection from
    #    authenticated P2/P3 state rather than trusting what is stored.
    cfg, paths = cli._load_config(config)
    store = CampaignStore(state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        assert revision.state.lifecycle in (
            TargetSizeLifecycle.TERMINAL_SELECTED,
            TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
        )
        definition = build_current_target_size_authorities(
            cfg, paths, store
        ).aggregate.definition
        resolver = TargetSizeExecutionResolver(
            workspace / revision.state.execution_root
        )
        head = validate_terminal_projection(
            revision, resolver=resolver, definition=definition
        )
        assert head.content_digest == revision.state.adopted_execution_head_digest

        # One canonical generation across the whole lifecycle, and one
        # append-only chain with no fork.
        history = load_target_size_campaign_history(store)
        assert {item.state.generation for item in history} == {0, 1}
        assert [item.sequence for item in history] == list(range(len(history)))
        kinds = [item.transition_kind for item in history]
        assert kinds[0] is TargetSizeTransitionKind.INITIALIZE
        assert TargetSizeTransitionKind.BEGIN_CUTOVER in kinds
        assert TargetSizeTransitionKind.COMPLETE_CUTOVER in kinds
        assert TargetSizeTransitionKind.ADOPT_EXECUTION_HEAD in kinds
        assert kinds[-1] in (
            TargetSizeTransitionKind.RECORD_TERMINAL_SELECTION,
            TargetSizeTransitionKind.RECORD_TERMINAL_SCIENTIFIC_FAILURE,
        )
    finally:
        store.close()

    # 4. Storage accounting sees the promoted evidence, and safe cleanup cannot
    #    touch it even when everything is aged well past every stale threshold.
    assert cli.main(["--config", str(config), "storage", "report"]) == 0
    assert cli.main(["--config", str(config), "storage", "report", "--deep"]) == 0
    payload = json.loads(
        (paths.results / "storage-report.json").read_text(encoding="utf-8")
    )
    owners = {item["owner"] for item in payload["owner_families"]}
    assert "p3" in owners, sorted(owners)
    deep = json.loads(
        (paths.results / "storage-deep-audit.json").read_text(encoding="utf-8")
    )
    families = {item["family"] for item in deep["families"]}
    assert any(name.startswith("target_size_") for name in families), sorted(families)

    root = workspace / revision.state.execution_root
    before = {
        path: path.stat().st_size for path in sorted(root.rglob("*")) if path.is_file()
    }
    old = time.time() - 90 * 86_400
    for path in before:
        os.utime(path, (old, old))
    store = CampaignStore(state_db)
    try:
        from types import SimpleNamespace

        from mdstats.training_data.storage import commands as storage_commands

        boundary = cli._campaign_ownership_boundary(cfg, paths, store)
        storage_commands.storage_cleanup(
            storage_commands.StorageCommandContext(cfg, paths, store, boundary),
            SimpleNamespace(tier="safe", apply=True, dry_run=False),
        )
    finally:
        store.close()
    after = {
        path: path.stat().st_size for path in sorted(root.rglob("*")) if path.is_file()
    }
    assert after == before

    # 5. Replay after cleanup is identical and retrains nothing.
    replay = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=replay.train,
            _external_inference_evaluator=replay.evaluate,
        )
        == 0
    )
    assert replay.rungs == []

    store = CampaignStore(state_db)
    try:
        final = load_target_size_campaign_revision(store)
        assert final.state.terminal == revision.state.terminal
        assert final.state.generation == revision.state.generation
    finally:
        store.close()


def test_p4g_assembled_lifecycle_reports_status_without_retired_authority(
    tmp_path: Path,
):
    """After the cutover, the operator surfaces still work with the retired
    selector record quarantined."""

    config, workspace = p4d._fixture_campaign(tmp_path)
    seed = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    seed.put_record(
        "target_size_study",
        {"schema": "retired", "outcome": "selected", "selected_target_size": 96},
    )
    seed.close()

    assert cli.main(["--config", str(config), "prepare"]) == 0
    # `status` derives its view without the retired record and must not crash.
    assert cli.main(["--config", str(config), "status"]) == 0
    assert cli.main(["--config", str(config), "storage", "report"]) == 0

    store = CampaignStore(workspace / ".mdstats" / "campaign.sqlite3")
    try:
        assert not store.has_record("target_size_study")
    finally:
        store.close()
