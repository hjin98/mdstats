from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md"
GUIDE = ROOT / "docs/guides/mlff_campaign_cli_user_guide.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
TOOL = ROOT / "tools/mdstats-mlff-campaign.py"


def test_data9b3_version_and_user_surface() -> None:
    assert mdstats.__version__ == "0.20.242a0"
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    assert TOOL.is_file()
    assert TOOL.stat().st_mode & 0o111
    spec = SPEC.read_text(encoding="utf-8")
    guide = GUIDE.read_text(encoding="utf-8")
    for token in (
        "python tools/mdstats-mlff-campaign.py",
        "campaign.toml",
        "campaign.sqlite3",
        "init",
        "doctor",
        "prepare",
        "select-target-size",
        "cross-validate",
        "train-production",
        "status",
        "advance",
        "target_size_power_max",
        "post_selection.cv",
        "N_selected",
        "T_selected",
    ):
        assert token in spec or token in guide
    assert "--config <frozen-campaign.toml> verify" not in spec
    assert "--config campaign.toml verify" not in guide
    assert "preflight" not in spec
    assert "preflight" not in guide
    assert "mace_runtime_record" not in spec
    assert "mace_runtime_record" not in guide


def test_data9b3_architecture_and_stage_plan_integration() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    assert "one target-size architecture" in manual
    assert "post-selection cross-validation on exactly T_selected" in manual
    assert "init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production" in stage
    assert "downstream qualification" in stage
    assert "does not redefine RDF, MSD, VACF, VDOS" in manual
    assert "checkpoint" in manual


def test_data9b3_dependency_graph_contract() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 3
    assert graph["authority_model"] == "single_generation_current_dependency_architecture"
    nodes = {node["id"] for node in graph["nodes"]}
    required = {
        "TARGET_SIZE_DEVELOPMENT_SPLIT",
        "CANONICAL_TRAINING_ORDER",
        "CANONICAL_EVALUATION_LADDER",
        "COMMON_TARGET_SIZE_PREPARATION",
        "TARGET_SIZE_POLICY",
        "TARGET_SIZE_DECISION",
        "CURRENT_SELECTED_SET",
        "POST_SELECTION_CV_ACCEPTANCE",
        "FRESH_FINAL_PRODUCTION",
        "OUT_OF_FOLD_PROTOCOL_EVIDENCE",
        "DEPLOYMENT_ARTIFACTS",
    }
    assert required <= nodes
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    assert ("TARGET_SIZE_DECISION", "CURRENT_SELECTED_SET", "produces") in edges
    assert ("CURRENT_SELECTED_SET", "POST_SELECTION_CV_ACCEPTANCE", "identity_requires") in edges
    assert ("POST_SELECTION_CV_ACCEPTANCE", "FRESH_FINAL_PRODUCTION", "promotion_requires") in edges
    assert ("FRESH_FINAL_PRODUCTION", "FROZEN_TRAINING_PROTOCOL", "identity_requires") in edges
    assert "retired target-size migration" in "\n".join(graph["forbidden_current_paths"])
