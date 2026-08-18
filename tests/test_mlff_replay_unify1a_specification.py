from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_replay_unify1a_release_and_architecture_are_synchronized():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV77.md").read_text(encoding="utf-8")
    assert "REPLAY-UNIFY1A implementation boundary" in manual
    assert "0.20.210a0" in note
    assert "REPLAY-UNIFY1A" in manual
    assert "12,000" in manual and "10,000" in manual and "2,000" in manual
    assert "Five independently fingerprinted replay layers" in manual
    assert "Dependency-graph schema:** 59" in note


def test_dependency_graph_records_frozen_five_gate_replay_migration():
    graph_path = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 77
    assert graph["schema_version"] >= 59
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["REPLAY_UNIFY1A_SINGLE_SOURCE_AUTHORITY"]
    assert gate["implementation_status"] == "implemented_additive_pre_migration"
    assert gate["production_replay_execution_changed"] is False
    assert gate["default_split_ratio"] == [5, 1]
    assert gate["acceptance_12000_counts"] == [10000, 2000]
    assert gate["next_gate"] == "REPLAY_UNIFY1B_TRUE_LABEL_MATERIALIZATION"
    assert "REPLAY_UNIFY1B_TRUE_LABEL_MATERIALIZATION" in nodes
    assert nodes["REPLAY_UNIFY1E_MIGRATION_HARDENING"]["final_gpu1_bundle_regeneration_required"] is True
    final_gpu = nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]
    assert isinstance(final_gpu["workstation_bundle_current"], bool)
    assert final_gpu["regeneration_gate"] in {"REPLAY_UNIFY1E_MIGRATION_HARDENING", "CUEQ_DEFAULT1_HF2_TRAIN2_FP32_PARITY_CEILING", "CUEQ_TRAIN2_NOISE_NORMALIZED_PARITY"}
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()


def test_new_replay_authorities_are_public_without_replacing_legacy_contracts():
    for name in (
        "ReplaySingleSourceConfig",
        "ReplaySourceArtifact",
        "ReplaySplitManifest",
        "canonical_replay_geometry_identity",
        "inspect_replay_source_extxyz",
        "build_replay_split_manifest",
        "single_source_replay_config_from_campaign",
    ):
        assert hasattr(mdstats, name), name
    # Existing live replay plan remains public until the integration gate.
    assert hasattr(mdstats, "ReplayPreparationPlan")
    assert hasattr(mdstats, "build_local_replay_plan")
