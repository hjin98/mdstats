from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_data9a9c_public_contracts_and_version() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    for name in (
        "ProductionCorpusPlan", "ProductionExpectedRun",
        "ProfileExtensionEvidenceRequirement", "ProductionCorpusQualificationRecord",
        "build_production_corpus_qualification_record",
    ):
        assert hasattr(mdstats, name)
    assert mdstats.REPLAY_FILE_ARTIFACT_SCHEMA.endswith(".v3")
    assert mdstats.FOUNDATION_CHECKPOINT_IDENTITY_SCHEMA.endswith(".v2")


def test_data9a9c_specification_and_manual_capture_review_fixes() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_data9a9c_production_gate_integrity_spec.md").read_text()
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    stage = (ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text()
    for phrase in (
        "ProductionCorpusPlan", "numerical replay-label identity",
        "foundation_residual_e0_not_materialized", "atomic `data8` symlink switch",
        "Self-verifying materialization loads",
    ):
        assert phrase in spec
    assert "DATA9A9c production-gate integrity closure - implemented in 0.20.55a0" in manual
    assert "MLFF-DATA9A9c - production-gate integrity closure - implemented in 0.20.55a0" in stage
    assert "profile focus-group" in stage


def test_dependency_graph_contains_integrity_gate_chain() -> None:
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {item["id"] for item in graph["nodes"]}
    assert {"PRODUCTION_CORPUS_PLAN", "REPLAY_LABEL_PAYLOAD_IDENTITY",
            "DATA8_ATOMIC_PROMOTION", "PRODUCTION_GATE_INTEGRITY_EVIDENCE"} <= nodes
    edges = {(item["from"], item["to"]) for item in graph["edges"]}
    assert ("PRODUCTION_CORPUS_PLAN", "PRODUCTION_GATE_INTEGRITY_EVIDENCE") in edges
    assert ("PRODUCTION_GATE_INTEGRITY_EVIDENCE", "DATA9A_GATE") in edges
    assert ("PRODUCTION_MATERIALIZATION_RECORD", "DATA9A_GATE") not in edges
