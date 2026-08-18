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
    assert mdstats.__version__ == "0.20.140a0"
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
        "preflight",
        "train",
        "evaluate",
        "verify",
        "status",
        "26 meV/atom/ps",
        "external_pseudolabel",
        "bounded_predeployment",
    ):
        assert token in spec or token in guide
    assert "mace_runtime_record" not in spec
    assert "mace_runtime_record" not in guide


def test_data9b3_architecture_and_stage_plan_integration() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    assert "MLFF-DATA9B3 unified campaign CLI and bounded deployment verification - implemented in 0.20.58a0" in manual
    assert "MLFF-DATA9B3 - unified campaign CLI and bounded verification - implemented in 0.20.58a0" in stage
    assert "RDF, coordination, site occupancy, VDOS" in manual
    assert "checkpoint byte" in manual


def test_data9b3_dependency_graph_contract() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    required = {
        "CAMPAIGN_CLI_CONFIGURATION",
        "CAMPAIGN_MANIFEST_APPROVAL",
        "CAMPAIGN_STATE_DATABASE",
        "CAMPAIGN_PREPARATION_GATE",
        "CAMPAIGN_PREFLIGHT_RECORD",
        "CAMPAIGN_STATUS_VIEW",
        "CAMPAIGN_RESULT_SUMMARY",
        "BOUNDED_DEPLOYMENT_VERIFICATION",
        "MLFF_CAMPAIGN_CLI_TOOL",
        "MLFF_CAMPAIGN_USER_GUIDE",
    }
    assert required <= nodes
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    assert ("DATA9A_GATE", "CAMPAIGN_PREPARATION_GATE", "promotion_requires") in edges
    assert ("CAMPAIGN_PREPARATION_GATE", "TRAINING_CAMPAIGN_PLAN", "promotion_requires") in edges
    assert ("CAMPAIGN_PREFLIGHT_RECORD", "TRAINING_RUN_EXECUTION_RECORD", "promotion_requires") in edges
    assert ("PROTOCOL_FREEZE_RECORD", "BOUNDED_DEPLOYMENT_VERIFICATION", "promotion_requires") in edges
