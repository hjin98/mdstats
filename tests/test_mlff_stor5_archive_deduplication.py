from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats

from mdstats.training_data import campaign_cli
from mdstats.training_data.storage_accounting import build_campaign_storage_report, configured_protected_inputs




def _freeze_authority():
    return mdstats.ProtocolFreezeAuthorityRecord(
        authority_kind="historical_committee",
        campaign_plan_digest="1" * 64,
        production_qualification_digest="2" * 64,
        source_record_schema=mdstats.PROTOCOL_FREEZE_RECORD_SCHEMA,
        source_record_digest="3" * 64,
        protected_model_sha256=("4" * 64,),
        frozen_at_utc="2026-08-01T00:00:00+00:00",
    )

def _config(tmp_path: Path) -> Path:
    (tmp_path / "training").mkdir()
    (tmp_path / "foundation.model").write_bytes(b"foundation")
    (tmp_path / "replay-train.xyz").write_text("", encoding="utf-8")
    (tmp_path / "replay-monitor.xyz").write_text("", encoding="utf-8")
    (tmp_path / "true-labels").mkdir()
    path = tmp_path / "campaign.toml"
    path.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model="foundation.model",
            replay_train="replay-train.xyz",
            replay_monitor="replay-monitor.xyz",
            replay_true_labels="true-labels",
        ),
        encoding="utf-8",
    )
    return path


def _complete(store: campaign_cli.CampaignStore, paths: campaign_cli.CampaignPaths, stage: str) -> None:
    campaign_cli._mark_stage(store, paths, stage, campaign_cli.StageState.COMPLETE, "complete")


def _cleanup_args(config: Path, *, tier: str, apply: bool = False, dry_run: bool = False):
    return SimpleNamespace(
        config=str(config), tier=tier, apply=apply, dry_run=dry_run,
        keep_preparation_caches=False, keep_unselected_checkpoints=True,
    )








def test_stor5_archive_corruption_fails_closed(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    victim = paths.internal / "evaluation-predictions" / "pred.bin"
    victim.parent.mkdir(parents=True); victim.write_bytes(b"important" * 1000)
    assert campaign_cli.command_archive(SimpleNamespace(config=str(config), archive_action="create")) == 0
    receipt = store.get_payload("cold_archive:latest")
    archive_path = paths.workspace / receipt["archive_relative_path"]
    with archive_path.open("ab") as handle:
        handle.write(b"corruption")
    with pytest.raises(campaign_cli.CampaignCliError, match="verification failed"):
        campaign_cli.command_archive(SimpleNamespace(config=str(config), archive_action="verify"))
    assert victim.is_file()


def test_stor5_archive_never_traverses_external_symlink(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    external = tmp_path / "external"
    external.mkdir(); important = external / "user.bin"; important.write_bytes(b"never-touch")
    link = paths.internal / "evaluation-predictions"
    link.symlink_to(external, target_is_directory=True)
    assert campaign_cli.command_cleanup(_cleanup_args(config, tier="archive", apply=True)) == 0
    assert important.read_bytes() == b"never-touch"
    assert not link.exists() and not link.is_symlink()


def test_stor5_storage_report_classifies_archive_and_content_store(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    content = paths.internal / "content-store" / "sha256" / "aa" / "obj"
    archive = paths.internal / "cold-archive" / "cold-x.tar.gz"
    content.parent.mkdir(parents=True); archive.parent.mkdir(parents=True)
    content.write_bytes(b"content"); archive.write_bytes(b"archive")
    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(cfg, config_dir=paths.config_dir, config_path=paths.config),
    ).to_dict()
    families = {item["family"]: item for item in report["families"]}
    assert families["immutable_content_store"]["manual_reclamation_eligibility"] == "stor5_managed"
    assert families["cold_archive"]["manual_reclamation_eligibility"] == "stor5_managed"


