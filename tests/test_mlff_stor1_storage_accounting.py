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


def _tree_signature(root: Path) -> dict[str, tuple[int, int, int]]:
    """Mode, size, and mtime of everything beneath one campaign workspace."""

    signature: dict[str, tuple[int, int, int]] = {}
    for path in sorted(Path(root).rglob("*")):
        try:
            stats = path.lstat()
        except OSError:
            continue
        signature[str(path.relative_to(root))] = (
            int(stats.st_mode), int(stats.st_size), int(stats.st_mtime_ns)
        )
    return signature


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
    for candidate in (source, external):
        authorized, detail = boundary.destructive_authorization(candidate)
        assert not authorized
        assert detail
    assert source.read_bytes() == b"source"
    assert external.read_bytes() == b"external"


def test_boundary_authorizes_a_campaign_symlink_object_but_never_its_target(
    tmp_path: Path,
) -> None:
    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-cache"
    external.mkdir()
    payload = external / "important.bin"
    payload.write_bytes(b"keep")
    paths.internal.mkdir(parents=True, exist_ok=True)
    link = paths.internal / "frame-cache"
    link.symlink_to(external, target_is_directory=True)

    boundary = CampaignOwnershipBoundary(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
    )
    authorized, _detail = boundary.destructive_authorization(link)
    assert authorized, "the campaign-owned link object itself is unlinkable"
    traversal, _detail = boundary.traversal_authorization(link)
    assert not traversal, "the external target is never traversed"
    authorized, _detail = boundary.destructive_authorization(payload)
    assert not authorized
    assert payload.read_bytes() == b"keep"

def test_storage_cli_reports_without_writing_into_the_workspace(tmp_path: Path) -> None:
    """The report is a description, not an artifact it deposits in the campaign.

    Writing `results/storage-report.json` was a state-producing side effect of a
    nominally read-only command; the repaired contract returns the payload to the
    caller and prints it, and leaves the workspace exactly as it found it.
    """

    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    (paths.runs / "run-a" / "checkpoints").mkdir(parents=True)
    (paths.runs / "run-a" / "checkpoints" / "epoch.pt").write_bytes(b"x" * 1024)
    campaign_cli_core.CampaignStore(paths.state_db).close()
    before = _tree_signature(paths.workspace)

    for deep in (False, True):
        rc = campaign_cli.command_storage(
            SimpleNamespace(config=str(config), top=5, deep=deep)
        )
        assert rc == 0
    assert not (paths.results / "storage-report.json").exists()
    assert not (paths.results / "storage-deep-audit.json").exists()
    assert _tree_signature(paths.workspace) == before


def test_storage_report_on_an_uninitialized_campaign_creates_nothing(
    tmp_path: Path,
) -> None:
    config = _write_config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config, ensure=False)
    try:
        campaign_cli.command_storage(
            SimpleNamespace(config=str(config), top=5, deep=False)
        )
    except campaign_cli_core.CampaignCliError as exc:
        assert "missing" in str(exc)
    else:  # pragma: no cover - the observational open must refuse
        raise AssertionError("an uninitialized campaign was reported as initialized")
    assert not paths.state_db.exists()




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

    campaign_cli_core.CampaignStore(paths.state_db).close()
    rc = campaign_cli.command_storage(
        SimpleNamespace(config=str(config), top=5, deep=False)
    )
    assert rc == 0
    assert not (external / "storage-report.json").exists()


def test_cleanup_does_not_traverse_an_external_records_symlink(tmp_path: Path) -> None:
    from types import SimpleNamespace as _NS

    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-records"
    external.mkdir()
    victim = external / "orphan-payload.bin"
    victim.write_bytes(b"keep")
    paths.ensure()
    store = campaign_cli.CampaignStore(paths.state_db)
    try:
        (paths.internal / "records").symlink_to(external, target_is_directory=True)
        from mdstats.training_data.storage import commands as storage_commands

        boundary = campaign_cli._campaign_ownership_boundary(cfg, paths, store)
        context = storage_commands.StorageCommandContext(cfg, paths, store, boundary)
        payload = storage_commands.storage_cleanup(
            context, _NS(tier="safe", apply=True, dry_run=False)
        )
        planned = {item["path"] for item in payload["execution"]["completed_actions"]}
        assert str(victim) not in planned
    finally:
        store.close()
    assert victim.read_bytes() == b"keep"


def test_executor_unlinks_a_campaign_symlink_without_touching_its_target(
    tmp_path: Path,
) -> None:
    from mdstats.training_data.storage.executor import remove_durably

    config = _write_config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    external = tmp_path / "external-cache"
    external.mkdir()
    victim = external / "heavy.bin"
    victim.write_bytes(b"keep")
    link = paths.internal / "temporary-symlink"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(external, target_is_directory=True)
    boundary = CampaignOwnershipBoundary(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
    )
    authorized, _detail = boundary.destructive_authorization(link)
    assert authorized
    assert remove_durably(link)
    assert victim.read_bytes() == b"keep"
    assert not link.exists() and not link.is_symlink()


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
                config=str(config), tier="safe", apply=False, dry_run=True
            )
        )
    except campaign_cli.CampaignCliError as exc:
        assert "outside the campaign ownership boundary" in str(exc)
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
