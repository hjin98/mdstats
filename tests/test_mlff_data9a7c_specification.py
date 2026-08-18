from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a7c_phase_geometry_profiles_spec.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"


def test_data9a7c_specification_is_present_and_normative() -> None:
    text = SPEC.read_text(encoding="utf-8")
    assert 'version: "0.20.49a0"' in text
    assert "PhaseGeometrySelectionPlan" in text
    assert "An interface is a geometry" in text
    assert "DATA6 schema v3" in text
    assert "physical observable" in text.lower()
    assert "does not infer a material type" in text


def test_architecture_and_stage_plan_record_implementation() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    assert "DATA9A7c in 0.20.49a0" in manual
    assert "DATA9A7c - phase and geometry profiles (implemented in 0.20.49a0)" in manual
    assert "MLFF-DATA9A7c - phase and geometry profiles - implemented in 0.20.49a0" in stage
    assert "Interfaces require two or more declared phases" in manual


def test_dependency_graph_contains_phase_geometry_contracts() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {node["id"] for node in graph["nodes"]}
    assert {
        "PHASE_GEOMETRY_SELECTION_PLAN",
        "PROFILE_BOUND_UNIVERSAL_STRUCTURAL_POLICY",
        "PROFILE_OBSERVABLE_RECOMMENDATIONS",
    } <= nodes
    edges = {(edge["from"], edge["to"]) for edge in graph["edges"]}
    assert ("MATERIAL_PROFILE_CONTRACTS", "PHASE_GEOMETRY_SELECTION_PLAN") in edges
    assert ("PHASE_GEOMETRY_SELECTION_PLAN", "UNIVERSAL_STRUCTURAL_FEATURE_CATALOG") in edges


def test_public_api_and_release_version() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert mdstats.MLFF_DATA6_PARSER_VERSION == "0.20.53a0"
    assert mdstats.MLFF_DATA9A7B_PARSER_VERSION == "0.20.49a0"
    assert mdstats.MLFF_DATA9A7C_PARSER_VERSION == "0.20.49a0"
    assert mdstats.PHASE_GEOMETRY_SELECTION_PLAN_SCHEMA.endswith(".v1")
    assert callable(mdstats.derive_phase_geometry_selection_plan)
    assert callable(mdstats.recommended_observable_ids_for_material_profile)
