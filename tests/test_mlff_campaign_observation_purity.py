"""Describing a campaign must never be a way of changing one.

`status` resolved configuration with the create-capable path, opened a writable
campaign store, and projected the lifecycle by *constructing operational state*:
it built a post-selection context, which resolved a trainer, which wrote
``.mdstats/bin`` wrapper scripts. Qualification status was worse -- it built a
whole session, which could re-enter P4/P5 currentness and even run model
inference to decide stress applicability. Both commands could therefore create
the very state they claimed to be reporting, and cost more than some of the work
they described.

These tests bind the repaired capability boundary to observable facts: the
managed workspace and campaign database are byte-identical across an
observational command, and the owners that would make it consequential are
proven not to run.
"""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_lifecycle import (
    LifecycleObservationState,
    project_campaign_lifecycle,
)


def _managed_snapshot(paths) -> dict[str, str]:
    """Every managed path plus the content of every managed file."""

    snapshot: dict[str, str] = {}
    for path in sorted(paths.workspace.rglob("*")):
        key = str(path.relative_to(paths.workspace))
        if path.is_dir():
            snapshot[key] = "<dir>"
        elif path.is_file():
            snapshot[key] = hashlib.sha256(path.read_bytes()).hexdigest()
        else:
            snapshot[key] = "<other>"
    return snapshot


def _database_rows(paths) -> dict[str, list[tuple]]:
    """Logical campaign-store rows, read without opening a writable store."""

    uri = f"file:{paths.state_db}?mode=ro"
    db = sqlite3.connect(uri, uri=True)
    try:
        rows: dict[str, list[tuple]] = {}
        for table in ("meta", "records", "stages", "target_size_campaign_state"):
            rows[table] = sorted(
                db.execute(f"SELECT * FROM {table}").fetchall(), key=repr
            )
        return rows
    finally:
        db.close()


def _forbid_consequential_owners(monkeypatch) -> list[str]:
    """Make every owner that would make observation consequential fail loudly."""

    called: list[str] = []

    def _explode(name):
        def _guard(*args, **kwargs):
            called.append(name)
            raise AssertionError(f"observation reached the consequential owner {name}")

        return _guard

    import mdstats.io as io_module
    from mdstats.training_data import campaign_target_size_runtime as runtime
    from mdstats.training_data import data4_sharded_store
    from mdstats.training_data import neutral_substrate

    monkeypatch.setattr(cli, "_ensure_local_wrappers", _explode("_ensure_local_wrappers"))
    monkeypatch.setattr(io_module, "read_vasp_frames", _explode("read_vasp_frames"))
    monkeypatch.setattr(
        data4_sharded_store,
        "read_data4_sharded_record",
        _explode("read_data4_sharded_record"),
    )
    monkeypatch.setattr(
        runtime,
        "build_prepared_target_size_substrate",
        _explode("build_prepared_target_size_substrate"),
    )
    for attribute in (
        "authenticate_vasp_source_authority",
        "build_canonical_frame_authority",
        "build_neutral_statistical_base",
    ):
        monkeypatch.setattr(neutral_substrate, attribute, _explode(attribute))
    return called


def _prepared(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    _cfg, paths = cli._load_config(config)
    return config, paths


def _selected(tmp_path: Path):
    config, paths = _prepared(tmp_path)
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
    return config, paths


@pytest.mark.parametrize("stage", ["prepared", "selected"])
def test_status_changes_no_managed_state(tmp_path: Path, monkeypatch, capsys, stage):
    config, paths = (
        _prepared(tmp_path) if stage == "prepared" else _selected(tmp_path)
    )
    before_tree = _managed_snapshot(paths)
    before_rows = _database_rows(paths)

    called = _forbid_consequential_owners(monkeypatch)
    assert cli.main(["--config", str(config), "status"]) == 0

    assert called == []
    assert _managed_snapshot(paths) == before_tree
    assert _database_rows(paths) == before_rows
    assert "Campaign status" in capsys.readouterr().out


def test_qualification_status_changes_no_managed_state(
    tmp_path: Path, monkeypatch, capsys
):
    config, paths = _selected(tmp_path)
    before_tree = _managed_snapshot(paths)
    before_rows = _database_rows(paths)

    called = _forbid_consequential_owners(monkeypatch)
    assert cli.main(["--config", str(config), "qualification", "status"]) == 0

    assert called == []
    assert _managed_snapshot(paths) == before_tree
    assert _database_rows(paths) == before_rows
    capsys.readouterr()


def test_status_on_an_absent_workspace_reports_rather_than_creates(tmp_path: Path):
    """Missing state is described as missing, not brought into existence."""

    config, _workspace = p4d._fixture_campaign(tmp_path)
    _cfg, paths = cli._load_config(config)
    state_db = paths.state_db
    state_db.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(state_db) + suffix).unlink(missing_ok=True)
    before = _managed_snapshot(paths)

    assert cli.main(["--config", str(config), "status"]) == 0
    assert _managed_snapshot(paths) == before
    assert not state_db.exists()


def test_the_projection_reads_only_persisted_state(tmp_path: Path, monkeypatch):
    """The lifecycle view is a read over owners, not a construction of them."""

    _config, paths = _selected(tmp_path)
    called = _forbid_consequential_owners(monkeypatch)
    store = CampaignStore(paths.state_db, create=False)
    try:
        snapshot = project_campaign_lifecycle(paths, store)
    finally:
        store.close()

    assert called == []
    assert snapshot.state_revision is not None
    prepare = snapshot.step("current_prepare")
    assert prepare is not None
    assert prepare.state == LifecycleObservationState.COMPLETE
    # P7 is part of the public lifecycle even before it can start.
    assert snapshot.step("post_production_qualification") is not None


def test_a_generation_without_prepared_state_is_reported_as_blocked(tmp_path: Path):
    """Incompleteness is reported as such, not silently as "not started"."""

    from mdstats.training_data.campaign_target_size_cutover import (
        ensure_current_target_size_authorities,
    )
    from mdstats.training_data.campaign_target_size_state import (
        load_target_size_campaign_revision,
    )

    _config, paths = _prepared(tmp_path)
    store = CampaignStore(paths.state_db)
    try:
        revision = load_target_size_campaign_revision(store)
        # Bind a generation that carries no prepared substrate, exactly as a
        # workspace prepared before immutable publication existed carries one.
        ensure_current_target_size_authorities(
            store,
            {
                name: getattr(revision.state, name)
                for name in (
                    "frame_authority_digest",
                    "neutral_statistical_base_digest",
                    "split_exclusion_digest",
                    "policy_digest",
                    "experiment_definition_digest",
                    "aggregate_digest",
                )
            },
            common_preparation_digest=revision.state.common_preparation_digest,
            prepared_manifest_digest=None,
        )
    finally:
        store.close()

    store = CampaignStore(paths.state_db, create=False)
    try:
        snapshot = project_campaign_lifecycle(paths, store)
    finally:
        store.close()
    prepare = snapshot.step("current_prepare")
    assert prepare.state == LifecycleObservationState.BLOCKED
    assert "prepare" in prepare.message
    # Routing still names the command that can repair it.
    assert snapshot.next_command == "prepare"
