from __future__ import annotations

from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9b1_campaign_checkpoint_control_spec.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"


def test_data9b1_spec_and_version_are_present() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert "Version: 0.20.56a0" in text
    assert "TrainingCampaignPlan" in text
    assert "CheckpointSelectionRecord" in text
    assert "mdstats-mace-train" in text
    assert mdstats.__version__ == "0.20.140a0"
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")


def test_data9b1_is_integrated_into_manual_and_stage_plan() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    assert "MLFF-DATA9B1 campaign and checkpoint control - implemented in 0.20.56a0" in manual
    assert "MLFF-DATA9B1 - campaign and checkpoint control - implemented in 0.20.56a0" in stage
    assert "does not launch long MACE jobs" in manual
    assert "MLFF-DATA9B2 - execution, aggregation, committee, and freeze" in stage


def test_data9b1_dependency_graph_nodes_and_gates() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] == 34
    nodes = {item["id"] for item in graph["nodes"]}
    for node in (
        "TRAINING_CAMPAIGN_POLICY",
        "TRAINING_CAMPAIGN_PLAN",
        "TRAINING_CAMPAIGN_RUN_PLAN",
        "CANDIDATE_CHECKPOINT_CATALOG",
        "CHECKPOINT_METRIC_RECORD",
        "CHECKPOINT_ADMISSIBILITY_DECISION",
        "CHECKPOINT_SELECTION_RECORD",
    ):
        assert node in nodes
    edges = {(item["from"], item["to"], item["type"]) for item in graph["edges"]}
    assert ("DATA9A_GATE", "TRAINING_CAMPAIGN_PLAN", "gates") in edges
    assert ("CHECKPOINT_METRIC_RECORD", "CHECKPOINT_ADMISSIBILITY_DECISION", "execution_requires") in edges
    assert ("CHECKPOINT_SELECTION_RECORD", "CHECKPOINT_SELECTION_DECISION", "execution_requires") in edges
