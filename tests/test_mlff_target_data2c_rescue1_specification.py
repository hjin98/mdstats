from __future__ import annotations

import json
from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]


def test_target_data2c_rescue1_release_and_authority_are_current() -> None:
    assert mdstats.__version__ == "0.20.209a0"
    assert mdstats.TARGET_DATA_LADDER_VERSION == "mdstats.target-data2c.ladder.2026-08.v4"
    assert mdstats.TARGET_DATA_LADDER_PLAN_SCHEMA == "mdstats.target-data-ladder-plan.v4"
    assert mdstats.TARGET_DATA_LADDER_V3_VERSION == "mdstats.target-data2c.ladder.2026-08.v3"


def test_target_data2c_rescue1_graph_and_manual_are_synchronized() -> None:
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    root_graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_rescue1_bounded_upper_ladder_spec.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    nodes = {item["id"]: item for item in graph["nodes"]}

    assert graph == root_graph
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    node = nodes["TARGET_DATA2C_RESCUE1_BOUNDED_UPPER_LADDER"]
    assert node["implemented_version"] == "0.20.197a0"
    assert node["maximum_training_pool_fraction"] == "7/8"
    assert node["minimum_eval2_complement_fraction"] == "1/8"
    assert node["coverage_threshold_relaxed"] is False
    assert "revision 64" in manual
    assert "bounded upper-ladder rescue" in manual
    assert "0.95" in manual
    assert "7/8" in manual and "1/8" in manual
    assert "**Release:** `mdstats 0.20.197a0`" in spec
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")


def test_campaign_binds_rescue_to_convergence_qualifier_requirement() -> None:
    from mdstats.training_data import campaign_cli

    source = Path(campaign_cli.__file__).read_text()
    assert "minimum_coverage_qualifiers=convergence_policy.min_coverage_qualifiers" in source
    assert "coverage_rescue_min_qualifiers != convergence_policy.min_coverage_qualifiers" in source
