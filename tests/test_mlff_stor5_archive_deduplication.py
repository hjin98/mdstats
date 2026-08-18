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


def test_stor5_deduplicate_exact_immutable_files_after_freeze(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "verify")
    store.put_record("protocol_freeze", _freeze_authority())
    left = paths.internal / "evaluation-predictions" / "a.bin"
    right = paths.internal / "model-sweep" / "b.bin"
    left.parent.mkdir(parents=True); right.parent.mkdir(parents=True)
    payload = b"duplicate-scientific-bytes" * 4096
    left.write_bytes(payload); right.write_bytes(payload)

    args = SimpleNamespace(config=str(config), apply=False)
    assert campaign_cli.command_deduplicate(args) == 0
    assert left.stat().st_ino != right.stat().st_ino
    plan = json.loads((paths.results / "deduplication-report.json").read_text())
    assert plan["group_count"] == 1
    assert plan["potential_reclaimed_bytes"] >= len(payload)

    args.apply = True
    assert campaign_cli.command_deduplicate(args) == 0
    assert left.read_bytes() == payload == right.read_bytes()
    assert (left.stat().st_dev, left.stat().st_ino) == (right.stat().st_dev, right.stat().st_ino)
    assert (paths.internal / "content-store").is_dir()


def test_stor5_deduplicate_requires_verified_frozen_campaign(tmp_path: Path) -> None:
    config = _config(tmp_path)
    with pytest.raises(campaign_cli.CampaignCliError, match="verification.*protocol freeze"):
        campaign_cli.command_deduplicate(SimpleNamespace(config=str(config), apply=True))


def test_stor5_archive_apply_is_reversible_and_preserves_production(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    _complete(store, paths, "verify")
    store.put_record("protocol_freeze", _freeze_authority())
    production = paths.models / "production.model"
    production.write_bytes(b"production-model")
    prediction = paths.internal / "evaluation-predictions" / "pred.bin"
    prediction.parent.mkdir(parents=True)
    prediction_bytes = b"prediction" * 1000
    prediction.write_bytes(prediction_bytes)
    data_file = paths.data / "variant" / "data8" / "train.extxyz"
    data_file.parent.mkdir(parents=True)
    data_bytes = b"data8-hot" * 2000
    data_file.write_bytes(data_bytes)

    assert campaign_cli.command_cleanup(_cleanup_args(config, tier="archive", apply=True)) == 0
    assert not prediction.exists()
    assert not paths.data.exists()
    assert production.read_bytes() == b"production-model"
    receipt = store.get_payload("cold_archive:latest")
    manifest_path = paths.workspace / receipt["manifest_relative_path"]
    archive_path = paths.workspace / receipt["archive_relative_path"]
    assert manifest_path.is_file() and archive_path.is_file()
    assert campaign_cli.command_archive(SimpleNamespace(config=str(config), archive_action="verify")) == 0

    plan = json.loads((paths.results / "manual-reclamation-plan-archive.json").read_text())
    assert plan["archive_representation_required"] is False
    assert plan["archive_representation"]["verified"] is True
    assert plan["capability_report"]["capabilities"]["metric_only_recomputation"]["status"] == "preserved_via_archive"

    assert campaign_cli.command_archive(SimpleNamespace(config=str(config), archive_action="restore")) == 0
    assert prediction.read_bytes() == prediction_bytes
    assert data_file.read_bytes() == data_bytes
    assert production.read_bytes() == b"production-model"


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


def test_stor5_archive_prunes_orphan_dedup_content_objects(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    _complete(store, paths, "verify")
    store.put_record("protocol_freeze", _freeze_authority())
    (paths.models / "production.model").write_bytes(b"production")
    a = paths.internal / "evaluation-predictions" / "a.bin"
    b = paths.data / "variant" / "b.bin"
    a.parent.mkdir(parents=True); b.parent.mkdir(parents=True)
    payload = b"dedup-then-archive" * 4096
    a.write_bytes(payload); b.write_bytes(payload)
    assert campaign_cli.command_deduplicate(SimpleNamespace(config=str(config), apply=True)) == 0
    assert a.stat().st_ino == b.stat().st_ino
    assert any((paths.internal / "content-store").rglob("*"))

    assert campaign_cli.command_cleanup(_cleanup_args(config, tier="archive", apply=True)) == 0
    content_store = paths.internal / "content-store"
    assert not content_store.exists() or not any(p.is_file() for p in content_store.rglob("*"))
    assert campaign_cli.command_archive(SimpleNamespace(config=str(config), archive_action="restore")) == 0
    assert a.read_bytes() == payload and b.read_bytes() == payload
