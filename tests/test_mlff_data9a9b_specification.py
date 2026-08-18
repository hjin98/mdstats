from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_data9a9b_public_contracts_and_version() -> None:
    assert mdstats.__version__ == "0.20.180a0"
    for name in (
        "ProductionMaterializationPlan",
        "ProductionMaterializationCheckpoint",
        "ProductionMaterializationRecord",
        "build_production_materialization_plan",
        "run_restartable_production_materialization",
        "load_production_materialization",
    ):
        assert hasattr(mdstats, name)


def test_data9a9b_spec_and_manual_state_boundary() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_data9a9b_production_materialization_spec.md").read_text()
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    plan = (ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text()
    for phrase in (
        "exact replay train and monitor artifacts",
        "one final-development job",
        "DATA9B remains closed",
        "filesystem root is a relocatable location hint",
    ):
        assert phrase in spec
    assert "DATA9A9b restartable production DATA6-DATA8 materialization - implemented in 0.20.54a0" in manual
    assert "MLFF-DATA9A9b - production DATA6--DATA8 materialization - implemented in 0.20.54a0" in plan
    assert "does not claim that the full 2,734-frame" in manual


def test_dependency_graph_contains_data9a9b_chain() -> None:
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 45
    nodes = {item["id"] for item in graph["nodes"]}
    required = {
        "PRODUCTION_MATERIALIZATION_PLAN",
        "PRODUCTION_MATERIALIZATION_CHECKPOINT",
        "PRODUCTION_DATA7_ARTIFACTS",
        "PRODUCTION_DATA8_ARTIFACT",
        "PRODUCTION_MATERIALIZATION_RECORD",
    }
    assert required <= nodes
    edges = {(item["from"], item["to"]) for item in graph["edges"]}
    assert ("DATA6_MODEL_SWEEP_CHECKPOINT", "PRODUCTION_MATERIALIZATION_PLAN") in edges
    assert ("PRODUCTION_DATA7_ARTIFACTS", "PRODUCTION_DATA8_ARTIFACT") in edges
    assert ("PRODUCTION_MATERIALIZATION_RECORD", "PRODUCTION_GATE_INTEGRITY_EVIDENCE") in edges
