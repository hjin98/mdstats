from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats

from mdstats.training_data import campaign_cli
from mdstats.training_data.storage_accounting import (
    build_campaign_storage_report,
    configured_protected_inputs,
)




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


def _args(config: Path, *, tier: str, apply: bool = False, dry_run: bool = False):
    return SimpleNamespace(
        config=str(config),
        tier=tier,
        apply=apply,
        dry_run=dry_run,
        keep_preparation_caches=False,
        keep_unselected_checkpoints=True,
    )


def _complete(store: campaign_cli.CampaignStore, paths: campaign_cli.CampaignPaths, stage: str) -> None:
    campaign_cli._mark_stage(store, paths, stage, campaign_cli.StageState.COMPLETE, "complete")


def test_recompute_tier_defaults_to_plan_only_and_reports_capability_loss(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    predictions = paths.internal / "evaluation-predictions"
    sweep = paths.internal / "model-sweep"
    predictions.mkdir(); sweep.mkdir()
    (predictions / "p.bin").write_bytes(b"p" * 1024)
    (sweep / "s.bin").write_bytes(b"s" * 2048)

    assert campaign_cli.command_cleanup(_args(config, tier="recompute")) == 0
    assert predictions.is_dir()
    assert sweep.is_dir()
    payload = json.loads((paths.results / "manual-reclamation-plan-recompute.json").read_text())
    assert payload["requested_tier"] == "recompute"
    assert payload["capability_report"]["capabilities"]["metric_only_recomputation"]["status"] == "lost"
    assert payload["capability_report"]["capabilities"]["data7_reselection"]["status"] == "preserved_with_recomputation"
    assert payload["planned_reclaimed_bytes"] >= 3072


def test_recompute_apply_removes_scientific_caches_but_keeps_production_and_logs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    _complete(store, paths, "verify")
    for name in ("evaluation-predictions", "model-sweep", "true-label-replay"):
        root = paths.internal / name
        root.mkdir()
        (root / "cache.bin").write_bytes(name.encode() * 64)
    production = paths.models / "production.model"
    production.write_bytes(b"production")
    log = paths.results / "keep.log"
    log.write_text("diagnostic", encoding="utf-8")

    assert campaign_cli.command_cleanup(_args(config, tier="recompute", apply=True)) == 0
    for name in ("evaluation-predictions", "model-sweep", "true-label-replay"):
        assert not (paths.internal / name).exists()
    assert production.read_bytes() == b"production"
    assert log.read_text(encoding="utf-8") == "diagnostic"
    events = [json.loads(line) for line in (paths.results / "cleanup-manifest.jsonl").read_text().splitlines()]
    event = next(item for item in reversed(events) if item.get("trigger") == "manual_tier:recompute")
    assert "metric_only_recomputation" in event["capability_loss"]
    assert "data7_reselection_without_reinference" in event["capability_loss"]


def test_compact_requires_apply_and_preserves_production_artifacts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    _complete(store, paths, "verify")
    store.put_record("protocol_freeze", _freeze_authority())

    production = paths.models / "final-target.model"
    production.write_bytes(b"production-model")
    selected_raw = paths.runs / "run-a" / "checkpoints" / "selected.pt"
    selected_raw.parent.mkdir(parents=True)
    selected_raw.write_bytes(b"selected-raw")
    capsule = paths.runs / "run-a" / "evaluation-capsules" / "epoch-0001.eval-state.pt"
    capsule.parent.mkdir(parents=True)
    capsule.write_bytes(b"capsule")
    run_model = paths.runs / "run-a" / "models" / "epoch.model"
    run_model.parent.mkdir(parents=True)
    run_model.write_bytes(b"run-model")
    log = paths.runs / "run-a" / "logs" / "train.log"
    log.parent.mkdir(parents=True)
    log.write_text("keep", encoding="utf-8")
    materialized = paths.data / "variant" / "data8" / "train.xyz"
    materialized.parent.mkdir(parents=True)
    materialized.write_bytes(b"data8")

    # Consequential tiers are plan-only unless --apply is explicit.
    assert campaign_cli.command_cleanup(_args(config, tier="compact")) == 0
    assert capsule.is_file() and run_model.is_file() and materialized.is_file()

    assert campaign_cli.command_cleanup(_args(config, tier="compact", apply=True)) == 0
    assert not capsule.exists()
    assert not run_model.exists()
    assert not paths.data.exists()
    assert production.read_bytes() == b"production-model"
    assert selected_raw.read_bytes() == b"selected-raw"
    assert log.read_text(encoding="utf-8") == "keep"
    compact = store.get_payload("manual_reclamation:compact")
    assert compact["selected_production_checkpoint_retained"] is True
    assert compact["production_models_retained"] is True


def test_archive_tier_dry_run_requires_stor5_representation_and_ineligible_apply_is_nondestructive(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    victim = paths.internal / "evaluation-predictions"
    victim.mkdir(); (victim / "p.bin").write_bytes(b"keep")

    assert campaign_cli.command_cleanup(_args(config, tier="archive", dry_run=True)) == 0
    payload = json.loads((paths.results / "manual-reclamation-plan-archive.json").read_text())
    assert payload["archive_representation_required"] is True
    assert (victim / "p.bin").read_bytes() == b"keep"

    # STOR5 is implemented now, but this campaign has not completed evaluation,
    # so the scientific cache is not an eligible consequential archive action.
    assert campaign_cli.command_cleanup(_args(config, tier="archive", apply=True)) == 0
    assert (victim / "p.bin").read_bytes() == b"keep"


def test_recompute_symlink_escape_unlinks_only_campaign_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    _complete(store, paths, "evaluate")
    external = tmp_path / "external-predictions"
    external.mkdir()
    important = external / "user.bin"
    important.write_bytes(b"never-delete")
    link = paths.internal / "evaluation-predictions"
    link.symlink_to(external, target_is_directory=True)

    assert campaign_cli.command_cleanup(_args(config, tier="recompute", apply=True)) == 0
    assert not link.is_symlink()
    assert important.read_bytes() == b"never-delete"


def test_storage_report_exposes_stor4_manual_tiers(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    (paths.internal / "evaluation-predictions").mkdir()
    (paths.internal / "evaluation-predictions" / "p.bin").write_bytes(b"p")
    (paths.runs / "run-a" / "evaluation-capsules").mkdir(parents=True)
    (paths.runs / "run-a" / "evaluation-capsules" / "c.eval-state.pt").write_bytes(b"c")
    (paths.data / "variant").mkdir(parents=True)
    (paths.data / "variant" / "data.bin").write_bytes(b"d")
    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
    ).to_dict()
    families = {item["family"]: item for item in report["families"]}
    assert families["evaluation-predictions"]["manual_reclamation_eligibility"] == "recompute"
    assert families["evaluation_state_capsules"]["manual_reclamation_eligibility"].startswith("compact")
    assert families["data7_data8_materializations"]["manual_reclamation_eligibility"].startswith("compact")


def test_completed_checkpoint_catalog_accepts_intentional_stor4_nonselected_loss(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    root = paths.runs / "run-a" / "checkpoints"
    root.mkdir(parents=True)
    selected = root / "selected.pt"
    selected.write_bytes(b"selected")
    selected_sha = campaign_cli._sha256(selected)

    class Checkpoint:
        def __init__(self, epoch, relative_path, sha):
            self.epoch = epoch
            self.relative_path = relative_path
            self.sha256 = sha
            self.run_plan_digest = "run"

    class Catalog:
        root_directory = str(root)
        checkpoints = (
            Checkpoint(1, "missing.pt", "a" * 64),
            Checkpoint(2, "selected.pt", selected_sha),
        )

    store.put_record(
        "checkpoint_retention:run-a",
        {
            "schema": "mdstats.mlff-checkpoint-retention.v2",
            "selected_checkpoint_sha256": selected_sha,
        },
    )
    ok, _ = campaign_cli._completed_checkpoint_storage_matches(paths, store, "run-a", Catalog())
    assert ok is False

    store.put_record(
        "manual_reclamation:compact",
        {
            "schema": "mdstats.mlff-manual-compact-retention.v1",
            "compacted_run_ids": ["run-a"],
            "selected_production_checkpoint_retained": True,
        },
    )
    ok, detail = campaign_cli._completed_checkpoint_storage_matches(paths, store, "run-a", Catalog())
    assert ok is True
    assert "verified" in detail
