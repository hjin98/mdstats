from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a7b_universal_structural_selection_spec.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
STAGE = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
ANALYSIS_MODULE = ROOT / "mdstats/analysis/local_structure.py"
MLFF_MODULE = ROOT / "mdstats/training_data/structural_selection.py"


def test_data9a7b_spec_freezes_theory_ownership_and_compatibility() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "smooth coordination",
        "Radial environment features",
        "Angular moments",
        "bond-orientational order",
        "mdstats.analysis.local_structure",
        "UniversalStructuralFeatureCatalog",
        "DATA6 policy and bundle schemas advance to v2",
        "DATA6-v1",
        "sealed or provenance-only roles",
        "universal_structural",
        "MACE descriptors",
    ):
        assert token in text


def test_data9a7b_manual_and_stage_mark_implementation() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    stage = STAGE.read_text(encoding="utf-8")
    assert "DATA9A7b in 0.20.48a0" in manual
    assert "DATA9A7b - universal structural selection providers (implemented in 0.20.48a0)" in manual
    assert "MLFF-DATA9A7b - universal structural selection providers - implemented in 0.20.48a0" in stage
    assert "does not interpret smooth edges as chemical bonds" in manual


def test_data9a7b_dependency_graph_has_analysis_to_selection_chain() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {item["id"] for item in graph["nodes"]}
    assert {
        "ANALYSIS_LOCAL_STRUCTURE_FEATURES",
        "UNIVERSAL_STRUCTURAL_FEATURE_CATALOG",
        "GENERIC_STRUCTURAL_EVENT_CATALOG",
    } <= nodes
    edges = {(item["from"], item["to"], item["type"]) for item in graph["edges"]}
    assert ("ANALYSIS_LOCAL_STRUCTURE_FEATURES", "UNIVERSAL_STRUCTURAL_FEATURE_CATALOG", "execution_requires") in edges
    assert ("ATOM_GROUP_CATALOG", "UNIVERSAL_STRUCTURAL_FEATURE_CATALOG", "execution_requires") in edges
    assert ("UNIVERSAL_STRUCTURAL_FEATURE_CATALOG", "SELECTION_FEATURE_CATALOGS", "execution_requires") in edges
    assert ("GENERIC_STRUCTURAL_EVENT_CATALOG", "FINAL_SELECTION_MASTER_ORDER", "optional_enrichment") in edges


def test_data9a7b_ownership_modules_are_separate_and_generic() -> None:
    analysis = ANALYSIS_MODULE.read_text(encoding="utf-8")
    mlff = MLFF_MODULE.read_text(encoding="utf-8")
    assert "mdstats.training_data" not in analysis
    assert "compute_local_structure_features" in analysis
    assert "from mdstats.analysis.local_structure" in mlff
    assert "lta_selection" not in mlff
    assert "ring_center" not in mlff


def test_data9a7b_public_exports_and_release_version() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert mdstats.MLFF_DATA6_PARSER_VERSION == "0.20.53a0"
    assert mdstats.MLFF_DATA9A7B_PARSER_VERSION == "0.20.49a0"
    assert callable(mdstats.compute_local_structure_features)
    assert callable(mdstats.build_universal_structural_feature_catalog)
