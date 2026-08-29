from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

from mdstats.training_data import _campaign_cli_core as campaign_cli_core
from mdstats.training_data import campaign_cli
from mdstats.training_data.storage_accounting import (
    ArtifactOwnershipClass,
    ArtifactRetentionClass,
    CampaignOwnershipBoundary,
    build_campaign_storage_report,
    configured_protected_inputs,
)


def _write_config(tmp_path: Path, *, training_root: str = "../training") -> Path:
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root=training_root,
            foundation_model="../foundation.model",
            replay_train="../replay-train.xyz",
            replay_monitor="../replay-monitor.xyz",
            replay_true_labels="../true-labels",
        ),
        encoding="utf-8",
    )
    return config


def test_stor1_report_counts_logical_allocated_and_unique_inode_bytes(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    protected = configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config)

    checkpoints = paths.runs / "run-a" / "checkpoints"
    checkpoints.mkdir(parents=True)
    first = checkpoints / "epoch-1.pt"
    first.write_bytes(b"x" * 8192)
    second = checkpoints / "epoch-1-hardlink.pt"
    os.link(first, second)
    (paths.results / "metrics.json").write_text("{}\n", encoding="utf-8")

    report = build_campaign_storage_report(paths.workspace, protected_inputs=protected)
    payload = report.to_dict()
    assert payload["schema"] == "mdstats.mlff-campaign-storage-report.v1"
    assert payload["destructive_actions_performed"] is False
    assert payload["totals"]["logical_bytes"] >= 2 * 8192
    assert payload["totals"]["allocated_physical_bytes"] > 0
    assert payload["totals"]["unique_inode_bytes"] < payload["totals"]["logical_bytes"]
    checkpoint_family = next(
        item for item in payload["families"] if item["family"] == "training_checkpoints"
    )
    assert checkpoint_family["retention_class"] == ArtifactRetentionClass.RESTART_CRITICAL.value
    assert checkpoint_family["automatic_reclamation_eligibility"] == "prohibited"


def test_stor1_external_symlink_is_not_traversed_or_owned(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    protected = configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config)

    external = tmp_path / "external-large"
    external.mkdir()
    (external / "do-not-count.bin").write_bytes(b"z" * 1024 * 1024)
    link = paths.internal / "external-link"
    link.symlink_to(external, target_is_directory=True)

    report = build_campaign_storage_report(paths.workspace, protected_inputs=protected)
    payload = report.to_dict()
    assert str(link) in payload["ownership_catalog"]["symlink_escapes"]
    assert payload["totals"]["logical_bytes"] < 1024 * 1024
    link_row = next(item for item in payload["largest_artifacts"] if item["path"] == str(link))
    assert link_row["ownership"] == ArtifactOwnershipClass.CAMPAIGN_OWNED_SYMLINK.value
    assert link_row["symlink_escape"] is True


def test_configured_input_inside_workspace_remains_user_owned(tmp_path: Path) -> None:
    config = _write_config(tmp_path, training_root="work/user-training")
    cfg, paths = campaign_cli._load_config(config)
    training = paths.workspace / "user-training"
    training.mkdir(parents=True)
    (training / "source.xml").write_bytes(b"source")
    protected = configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config)

    report = build_campaign_storage_report(paths.workspace, protected_inputs=protected)
    family = next(
        item for item in report.to_dict()["families"]
        if item["family"] == "configured_input:training_root"
    )
    assert family["ownership"] == ArtifactOwnershipClass.EXTERNAL_USER_INPUT.value
    assert family["retention_class"] == ArtifactRetentionClass.PROTECTED_INPUT.value
    assert family["automatic_reclamation_eligibility"] == "prohibited"
    assert family["manual_reclamation_eligibility"] == "prohibited"


def test_cleanup_authority_denies_external_and_configured_inputs(tmp_path: Path) -> None:
    config = _write_config(tmp_path, training_root="work/user-training")
    cfg, paths = campaign_cli._load_config(config)
    training = paths.workspace / "user-training"
    training.mkdir(parents=True)
    source = training / "source.xml"
    source.write_bytes(b"source")
    external = tmp_path / "external.bin"
    external.write_bytes(b"external")

    boundary = CampaignOwnershipBoundary(
        paths.workspace,
        protected_inputs=configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config),
    )
    report = campaign_cli._CampaignCleanupReport(
        phase="stor1-test", dry_run=False, ownership_boundary=boundary
    )
    campaign_cli._cleanup_remove(report, source, reason="must be denied")
    campaign_cli._cleanup_remove(report, external, reason="must be denied")

    assert source.read_bytes() == b"source"
    assert external.read_bytes() == b"external"
    assert report.actions == []
    assert len(report.skipped) == 2
    assert all("cleanup authority denied" in item for item in report.skipped)


def test_cleanup_symlink_unlinks_only_campaign_link_not_external_target(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-cache"
    external.mkdir()
    payload = external / "important.bin"
    payload.write_bytes(b"keep")
    link = paths.internal / "frame-cache"
    link.symlink_to(external, target_is_directory=True)

    report = campaign_cli._CampaignCleanupReport(
        phase="stor1-test",
        dry_run=False,
        ownership_boundary=CampaignOwnershipBoundary(
            paths.workspace,
            protected_inputs=configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config),
        ),
    )
    campaign_cli._cleanup_remove(report, link, reason="remove campaign link only")
    assert not link.exists()
    assert not link.is_symlink()
    assert payload.read_bytes() == b"keep"
    assert len(report.actions) == 1


def test_storage_cli_writes_read_only_report(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    (paths.runs / "run-a" / "checkpoints").mkdir(parents=True)
    (paths.runs / "run-a" / "checkpoints" / "epoch.pt").write_bytes(b"x" * 1024)

    rc = campaign_cli.command_storage(SimpleNamespace(config=str(config), top=5))
    assert rc == 0
    destination = paths.results / "storage-report.json"
    payload = json.loads(destination.read_text(encoding="utf-8"))
    assert payload["read_only_gate"] == "STOR1"
    assert payload["destructive_actions_performed"] is False
    assert len(payload["largest_artifacts"]) <= 5


def test_materialization_record_path_does_not_confer_external_cleanup_authority(tmp_path: Path, monkeypatch) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    external_root = tmp_path / "external-materialization"
    stale = external_root / ".data8-staging-old"
    stale.mkdir(parents=True)
    payload = stale / "user-owned.bin"
    payload.write_bytes(b"do-not-delete")
    old = __import__("time").time() - 24 * 3600
    os.utime(stale, (old, old))

    # The cleanup owner resolves this helper from the core module, so the
    # substitution has to be installed there; patching the facade re-export
    # leaves the production lookup untouched.
    monkeypatch.setattr(
        campaign_cli_core,
        "_current_materialization_roots",
        lambda _store: {external_root.resolve()},
    )
    report = campaign_cli._CampaignCleanupReport(
        phase="stor1-test",
        dry_run=False,
        ownership_boundary=CampaignOwnershipBoundary(
            paths.workspace,
            protected_inputs=configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config),
        ),
    )
    campaign_cli._cleanup_materialization_storage(
        report,
        paths,
        store,
        stale_before=__import__("time").time() - 6 * 3600,
    )
    assert payload.read_bytes() == b"do-not-delete"
    assert report.actions == []
    assert any("failed ownership checks" in item or "cleanup authority denied" in item for item in report.skipped)


def test_stor1_largest_artifacts_include_directory_aggregate(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    root = paths.runs / "run-big" / "checkpoints"
    root.mkdir(parents=True)
    (root / "a.pt").write_bytes(b"a" * 4096)
    (root / "b.pt").write_bytes(b"b" * 2048)
    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
        largest_limit=50,
    )
    row = next(
        item for item in report.to_dict()["largest_artifacts"]
        if item["path"] == str(root)
    )
    assert row["kind"] == "directory"
    assert row["logical_bytes"] >= 6144


def test_storage_cli_refuses_report_write_through_results_symlink(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-results"
    external.mkdir()
    paths.results.rmdir()
    paths.results.symlink_to(external, target_is_directory=True)

    rc = campaign_cli.command_storage(SimpleNamespace(config=str(config), top=5))
    assert rc == 0
    assert not (external / "storage-report.json").exists()


def test_cleanup_does_not_traverse_external_runs_symlink(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-runs"
    victim = external / "run-a" / "checkpoint-model-cache" / "important.bin"
    victim.parent.mkdir(parents=True)
    victim.write_bytes(b"keep")
    paths.runs.rmdir()
    paths.runs.symlink_to(external, target_is_directory=True)
    store = campaign_cli.CampaignStore(paths.state_db)

    report = campaign_cli._campaign_cleanup(
        cfg,
        paths,
        store,
        phase="stor1-test",
        dry_run=False,
        include_preparation_caches=False,
    )
    assert victim.read_bytes() == b"keep"
    assert any("run-tree cleanup skipped" in item for item in report.skipped)


def test_preflight_cleanup_refuses_external_symlink_root(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    store.put_record("preflight_smoke", {"passed": True})
    external = tmp_path / "external-preflight"
    external.mkdir()
    victim = external / "heavy.bin"
    victim.write_bytes(b"keep")
    link = paths.internal / "preflight-smoke"
    link.symlink_to(external, target_is_directory=True)
    report = campaign_cli._CampaignCleanupReport(
        phase="stor1-test",
        dry_run=False,
        ownership_boundary=CampaignOwnershipBoundary(
            paths.workspace,
            protected_inputs=configured_protected_inputs(
                cfg, config_dir=paths.config_dir, config_path=paths.config
            ),
        ),
    )
    campaign_cli._cleanup_preflight_heavy_artifacts(report, paths, store)
    assert victim.read_bytes() == b"keep"
    assert not (external / "retained-diagnostic.json").exists()
    assert any("failed traversal ownership checks" in item for item in report.skipped)


def test_manual_cleanup_refuses_external_campaign_state_symlink(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-state"
    external.mkdir()
    paths.internal.rmdir()
    paths.internal.symlink_to(external, target_is_directory=True)

    try:
        campaign_cli.command_cleanup(
            SimpleNamespace(
                config=str(config),
                keep_preparation_caches=False,
                keep_unselected_checkpoints=False,
                dry_run=False,
            )
        )
    except campaign_cli.CampaignCliError as exc:
        assert "campaign state database is outside" in str(exc)
    else:
        raise AssertionError("cleanup must fail closed before opening an external state database")
    assert not (external / "campaign.sqlite3").exists()


def test_stor2_capsules_have_distinct_storage_retention_family(tmp_path: Path) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    capsule_root = paths.runs / "run-a" / "evaluation-capsules"
    capsule_root.mkdir(parents=True)
    (capsule_root / "epoch-0001.eval-state.pt").write_bytes(b"capsule" * 100)
    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
    )
    family = next(
        item for item in report.to_dict()["families"]
        if item["family"] == "evaluation_state_capsules"
    )
    assert family["retention_class"] == ArtifactRetentionClass.EVALUATION_CAPSULE.value
    assert family["automatic_reclamation_eligibility"] == "prohibited"
