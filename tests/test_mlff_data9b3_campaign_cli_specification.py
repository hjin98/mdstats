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
        "T_N",
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
    assert "one prepared target-size generation" in manual
    assert "freezes the collection before numerical CV work" in manual
    assert "init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production" in stage
    assert "downstream qualification" in stage
    assert (
        "the selected target size, and both effective role training horizons are protocol-global"
        not in stage
    )
    assert (
        "Exact target membership, the ordered collection of provisional target sizes"
        in stage
    )
    assert "selected target size and exact global membership identity" not in stage
    assert "one protocol-global target-size decision" not in manual
    assert "final T_selected -> final-training fitted products" not in stage
    assert "it does not redefine those algorithms" in manual
    assert "checkpoint" in manual


def test_data9b3_dependency_graph_contract() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 5
    assert graph["authority_model"] == "d1_d2_d3_d4_layered_mlff_architecture"
    nodes = {node["id"] for node in graph["nodes"]}
    required = {
        "TARGET_SIZE_SPLIT",
        "TARGET_TRAINING_ORDER",
        "TARGET_PREFIX_QUALIFICATION",
        "TARGET_SIZE_GENERATION",
        "COMMON_TARGET_PREPARATION",
        "TARGET_SIZE_SCREEN",
        "PROVISIONAL_DESIGN",
        "FROZEN_TARGET_BINDINGS",
        "POST_SELECTION_CV",
        "FINAL_PRODUCTION",
        "FINAL_PUBLICATION",
        "QUALIFICATION",
    }
    assert required <= nodes
    edges = {(edge["from"], edge["to"], edge["type"]) for edge in graph["edges"]}
    # init -> doctor -> prepare -> select-target-size -> cross-validate -> train-production
    assert ("TARGET_SIZE_SCREEN", "PROVISIONAL_DESIGN", "optional_recommendation_only") in edges
    assert ("PROVISIONAL_DESIGN", "FROZEN_TARGET_BINDINGS", "atomic_freeze") in edges
    assert ("FROZEN_TARGET_BINDINGS", "POST_SELECTION_CV", "authorizes") in edges
    assert ("POST_SELECTION_CV", "FINAL_PRODUCTION", "acceptance_gate") in edges
    assert ("FINAL_PRODUCTION", "FINAL_PUBLICATION", "produces") in edges
    assert ("FINAL_PUBLICATION", "QUALIFICATION", "consumed_by") in edges
    forbidden = {(edge["from"], edge["to"]) for edge in graph["forbidden_edges"]}
    assert ("POST_SELECTION_CV", "FROZEN_TARGET_BINDINGS") in forbidden
