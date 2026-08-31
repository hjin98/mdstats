from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

from mdstats.training_data import campaign_cli


def _config(tmp_path: Path) -> Path:
    path = tmp_path / "campaign.toml"
    path.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="../training",
            foundation_model="../foundation.model",
            replay_train="../replay-train.xyz",
            replay_monitor="../replay-monitor.xyz",
            replay_true_labels="../true-labels",
        ),
        encoding="utf-8",
    )
    return path


def test_stor3_reclaims_graph_cache_only_after_authoritative_evaluation(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    graph = paths.internal / "evaluation-graphs"
    predictions = paths.internal / "evaluation-predictions"
    model_sweep = paths.internal / "model-sweep"
    graph.mkdir(); predictions.mkdir(); model_sweep.mkdir()
    (graph / "graph.bin").write_bytes(b"g" * 4096)
    (predictions / "prediction.bin").write_bytes(b"p" * 4096)
    (model_sweep / "prediction.bin").write_bytes(b"m" * 4096)

    before = campaign_cli._campaign_cleanup(cfg, paths, store, phase="before-eval")
    assert graph.is_dir()
    assert not any("evaluation graph/view" in item["reason"] for item in before.actions)

    store.set_stage("evaluate", campaign_cli.StageState.COMPLETE, "authoritative evaluation complete")
    after = campaign_cli._campaign_cleanup(cfg, paths, store, phase="evaluate-end")
    assert not graph.exists()
    assert predictions.is_dir()
    assert model_sweep.is_dir()
    action = next(item for item in after.actions if "evaluation graph/view" in item["reason"])
    assert action["cleanup_class"] == "reconstructable_cache"
    assert action["capability_loss"] == []
    assert "authoritative_checkpoint_metrics" in action["preserved_capabilities"]


def test_stor3_cleanup_manifest_is_append_only_and_records_predelete_identity(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    store.set_stage("evaluate", campaign_cli.StageState.COMPLETE, "complete")

    graph = paths.internal / "evaluation-graphs"
    graph.mkdir(); (graph / "first.bin").write_bytes(b"one")
    campaign_cli._campaign_cleanup(cfg, paths, store, phase="first")

    graph.mkdir(); (graph / "second.bin").write_bytes(b"two")
    campaign_cli._campaign_cleanup(cfg, paths, store, phase="second")

    manifest = paths.results / "cleanup-manifest.jsonl"
    lines = [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line]
    assert len(lines) >= 2
    first, second = lines[-2:]
    assert first["schema"] == "mdstats.mlff-campaign-cleanup-manifest.v1"
    assert first["event_digest"] != second["event_digest"]
    assert first["capability_loss"] == []
    assert first["actions"]
    identity = first["actions"][0]["prior_identity"]
    assert identity["schema"] == "mdstats.mlff-filesystem-identity.v1"
    assert identity["kind"] in {"directory", "file", "symlink"}


def test_stor3_never_reclaims_scientific_prediction_caches(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    store.set_stage("evaluate", campaign_cli.StageState.COMPLETE, "complete")
    for name in ("evaluation-predictions", "model-sweep", "true-label-replay"):
        root = paths.internal / name
        root.mkdir()
        (root / "keep.bin").write_bytes(b"keep")
    campaign_cli._campaign_cleanup(cfg, paths, store, phase="safe-only", include_preparation_caches=True)
    for name in ("evaluation-predictions", "model-sweep", "true-label-replay"):
        assert (paths.internal / name / "keep.bin").read_bytes() == b"keep"


def test_stor3_graph_symlink_escape_unlinks_only_campaign_link(tmp_path: Path) -> None:
    config = _config(tmp_path)
    cfg, paths = campaign_cli._load_config(config)
    store = campaign_cli.CampaignStore(paths.state_db)
    store.set_stage("evaluate", campaign_cli.StageState.COMPLETE, "complete")
    external = tmp_path / "external-graphs"
    external.mkdir()
    important = external / "user.bin"
    important.write_bytes(b"never-delete")
    link = paths.internal / "evaluation-graphs"
    link.symlink_to(external, target_is_directory=True)

    campaign_cli._campaign_cleanup(cfg, paths, store, phase="symlink-safe")
    assert not link.is_symlink()
    assert important.read_bytes() == b"never-delete"




def test_storage_report_marks_stor3_reconstructable_classes_as_automatic_safe(tmp_path: Path) -> None:
    config = _config(tmp_path)
    _cfg, paths = campaign_cli._load_config(config)
    graph = paths.internal / "evaluation-graphs"
    graph.mkdir(); (graph / "g.bin").write_bytes(b"g")
    campaign_cli.command_storage(SimpleNamespace(config=str(config), top=50))
    payload = json.loads((paths.results / "storage-report.json").read_text(encoding="utf-8"))
    family = next(item for item in payload["families"] if item["family"] == "evaluation-graphs")
    assert family["automatic_reclamation_eligibility"] == "stor3_automatic_safe"
