from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data.replay_index import (
    REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA,
    REPLAY_SOURCE_INDEX_SCHEMA,
)

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_replay_perf1_index_cache_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_replay_perf1_cloud_cpu_mpa0_2026-08-17.json"


def test_replay_perf1_historical_release_record_and_current_manual_are_synchronized() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate REPLAY-PERF1 - replay index/cache and chunk materialization - COMPLETE" in text
    assert SPEC.is_file()
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV101.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.234a0.md").is_file()


def test_replay_perf1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    node = next(item for item in graph["nodes"] if item["id"] == "REPLAY_PERF1_INDEX_CACHE")
    assert node["implemented_release"] == "0.20.234a0"
    assert node["implementation_status"] == "implemented_source_index_indexed_materialization"
    assert node["source_index_schema"] == REPLAY_SOURCE_INDEX_SCHEMA
    assert node["source_index_receipt_schema"] == REPLAY_SOURCE_INDEX_RECEIPT_SCHEMA
    assert node["scientific_authority_change"] is False
    assert node["parser_parallelism"] == "serial_measured_authority"


def test_replay_perf1_code_contains_exact_index_and_integration_contract() -> None:
    index_code = (ROOT / "mdstats/training_data/replay_index.py").read_text(encoding="utf-8")
    replay_code = (ROOT / "mdstats/training_data/replay.py").read_text(encoding="utf-8")
    pseudo_code = (ROOT / "mdstats/training_data/replay_pseudolabel.py").read_text(encoding="utf-8")
    campaign = (ROOT / "mdstats/training_data/campaign_cli.py").read_text(encoding="utf-8")
    for token in (
        "class ReplaySourceIndex",
        "_scan_extxyz_frame_ranges",
        "iter_indexed_replay_frames",
        "source_artifact_digest",
        "source_index_digest",
        "frame_offsets",
        "frame_lengths",
        "atom_counts",
    ):
        assert token in index_code
    assert "source_index: ReplaySourceIndex | None = None" in replay_code
    assert "source_index: ReplaySourceIndex | None = None" in pseudo_code
    assert 'replay_root / "source-index"' in campaign
    assert "source_index=source_index" in campaign


def test_replay_perf1_frozen_benchmark_evidence_is_consistent() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.234a0"
    assert evidence["architecture_revision"] == 101
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "CAMPAIGN-PERF-QUAL1"
    assert evidence["active_foundation"]["family"] == "MACE-MPA-0 medium"
    assert evidence["active_foundation"]["checkpoint_sha256"] == (
        "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    )
    assert evidence["active_foundation"]["mh1_compatible"] is True
    assert evidence["inputs"]["replay_source_sha256"] == (
        "187eed42fb2d6cf5e7e745ffed0ce34541e92c6a35ec9e654520cd3c7198403c"
    )
    assert evidence["scientific"]["monitor_control_exact"] is True
    assert evidence["scientific"]["full_materialization_control_exact"] is True
    assert evidence["execution"]["monitor_only_true_label_materialization"]["speedup"] > 2.5
    assert evidence["execution"]["full_source_parse_identity"]["speedup"] > 1.0
    assert evidence["execution"]["train_monitor_true_label_materialization"]["speedup"] > 1.0


def test_replay_perf1_history_records_are_present() -> None:
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV101.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.234a0.md").is_file()
    assert "0.20.234a0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.20.234a0" in (ROOT / "docs/history/mlff/release_notes/INDEX.md").read_text(encoding="utf-8")
