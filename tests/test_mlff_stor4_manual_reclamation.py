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


def test_safe_and_cache_tiers_execute_and_generate_plans(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    frame_cache = paths.internal / "frame-cache"
    frame_cache.mkdir(parents=True)
    (frame_cache / "cache.mmap").write_bytes(b"frames" * 1024)

    run_dir = paths.runs / "run-inactive"
    run_dir.mkdir(parents=True)
    model_cache = run_dir / "checkpoint-model-cache"
    model_cache.mkdir()
    (model_cache / "cache.pt").write_bytes(b"cached-model")

    # Safe tier (dry run): retains frame-cache and checkpoint-model-cache
    assert campaign_cli.command_cleanup(_args(config, tier="safe", dry_run=True)) == 0
    assert frame_cache.is_dir()
    assert model_cache.is_dir()
    plan = json.loads((paths.results / "manual-reclamation-plan-safe.json").read_text(encoding="utf-8"))
    assert plan["requested_tier"] == "safe"
    assert plan["schema"] == "mdstats.mlff-manual-reclamation-plan.v1"
    assert plan["capability_report"]["declared_capability_losses"] == []

    # Cache tier (apply): retains frame-cache, removes inactive-run checkpoint-model-cache
    assert campaign_cli.command_cleanup(_args(config, tier="cache", dry_run=False)) == 0
    assert frame_cache.is_dir(), "frame-cache must be retained in P6"
    assert not model_cache.exists(), "inactive checkpoint-model-cache must be removed by cache tier"
    plan_cache = json.loads((paths.results / "manual-reclamation-plan-cache.json").read_text(encoding="utf-8"))
    assert plan_cache["requested_tier"] == "cache"
    assert "faster_checkpoint_reevaluation" in plan_cache["capability_report"]["declared_capability_losses"]


def test_consequential_tiers_fail_closed_to_reset(tmp_path: Path) -> None:
    config = _config(tmp_path)
    for tier in ("recompute", "compact", "archive"):
        with pytest.raises(campaign_cli.CampaignCliError, match="CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1"):
            campaign_cli.command_cleanup(_args(config, tier=tier))


def test_cache_symlink_escape_unlinks_only_campaign_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    external = tmp_path / "external-cache"
    external.mkdir()
    important = external / "user.bin"
    important.write_bytes(b"never-delete")
    run_dir = paths.runs / "run-a"
    run_dir.mkdir(parents=True)
    link = run_dir / "checkpoint-model-cache"
    link.symlink_to(external, target_is_directory=True)

    assert campaign_cli.command_cleanup(_args(config, tier="cache", dry_run=False)) == 0
    assert not link.is_symlink()
    assert important.read_bytes() == b"never-delete"


def test_storage_report_exposes_transitional_storage_structure(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    (paths.internal / "frame-cache").mkdir(parents=True)
    (paths.internal / "frame-cache" / "cache.mmap").write_bytes(b"f" * 1024)
    (paths.runs / "run-a" / "checkpoint-model-cache").mkdir(parents=True)
    (paths.runs / "run-a" / "checkpoint-model-cache" / "m.pt").write_bytes(b"m" * 1024)
    report = build_campaign_storage_report(
        paths.workspace,
        protected_inputs=configured_protected_inputs(
            cfg, config_dir=paths.config_dir, config_path=paths.config
        ),
    ).to_dict()
    assert report["schema"] == "mdstats.mlff-campaign-storage-report.v1"
    assert report["totals"]["logical_bytes"] >= 2048


