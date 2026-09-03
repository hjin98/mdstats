from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_data9a8_observable_comparison_spec.md"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
STAGE = ROOT / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.md"
BRIDGE = ROOT / "docs" / "specs" / "training_data" / "mlff_observable_validation_bridge_spec.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"


def test_data9a8_specification_freezes_ownership_and_policy_ordering() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        'version: "0.20.52a0"',
        "analysis-owned",
        "ObservableComparisonThresholds",
        "ObservableScoreUncertainty",
        "ObservableComparisonPolicy",
        "ObservableComparisonResult",
        "ObservableAcceptanceDecision",
        "predeclared",
        "Jensen--Shannon distance",
        "Development-stage compatibility cleanup",
        "DATA4/DATA6 historical bundle readers",
    ):
        assert token in text


def test_manuals_mark_data9a8_implemented_and_keep_analysis_ownership() -> None:
    arch = ARCH.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    bridge = BRIDGE.read_text(encoding="utf-8")
    assert "MLFF-DATA9A8 profile-aware observable comparison policies - implemented in 0.20.52a0" in arch
    assert "MLFF-DATA9A8 - profile-aware observable comparison policies - implemented in 0.20.52a0" in stage
    assert "Revision 0.20.52a0 implements" in bridge
    assert "Physical observable calculation is not owned by `mdstats.training_data`" in arch


def test_dependency_graph_places_policy_upstream_and_forbids_posthoc_thresholds() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    for node in (
        "OBSERVABLE_COMPARISON_RULES",
        "OBSERVABLE_SCORE_UNCERTAINTY",
        "OBSERVABLE_SCOPE_AGGREGATION",
        "PREDECLARED_OBSERVABLE_THRESHOLDS",
        "OBSERVABLE_COMPARISON_POLICY",
        "OBSERVABLE_COMPARISON_RESULT",
        "OBSERVABLE_ACCEPTANCE_DECISION",
    ):
        assert node in nodes
    edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert ("PREDECLARED_OBSERVABLE_THRESHOLDS", "OBSERVABLE_COMPARISON_POLICY") in edges
    assert ("OBSERVABLE_COMPARISON_POLICY", "OBSERVABLE_COMPARISON_RESULT") in edges
    assert ("OBSERVABLE_COMPARISON_RESULT", "OBSERVABLE_ACCEPTANCE_DECISION") in edges
    forbidden = json.dumps(graph["forbidden_dependencies"])
    assert "PREDECLARED_OBSERVABLE_THRESHOLDS" in forbidden
    assert "LOCKED_TEST_OBSERVABLE_EVIDENCE" in forbidden


def test_public_runtime_exposes_data9a8_without_removed_aliases() -> None:
    assert mdstats.MLFF_DATA9A8_PARSER_VERSION == "0.20.52a0"
    assert mdstats.ObservableComparisonPolicy
    assert mdstats.compare_mlff_observable_validation
    assert not hasattr(mdstats, "MaterialValidationProfile")
    assert not hasattr(mdstats, "MLFFTrajectoryGenerationIdentity")
