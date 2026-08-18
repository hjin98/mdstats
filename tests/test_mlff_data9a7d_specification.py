from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_data9a7d_spec_and_architecture_are_present() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_data9a7d_profile_extension_migration_spec.md").read_text()
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    stage = (ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text()
    assert 'version: "0.20.50a0"' in spec
    assert "ProfileFeatureCatalog" in spec
    assert "DATA9A7d - optional porous, zeolite, and LTA extensions (implemented in 0.20.50a0)" in manual
    assert "MLFF-DATA9A7d - optional profile-extension and LTA migration - implemented in 0.20.50a0" in stage


def test_data9a7d_dependency_graph_contract() -> None:
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {item["id"] for item in graph["nodes"]}
    assert {
        "OPTIONAL_PROFILE_EXTENSION_PROVIDER",
        "PROFILE_PARTITION_FEATURE_CATALOGS",
        "PROFILE_SELECTION_FEATURE_CATALOGS",
        "FOCUS_ATOM_GROUP_POLICY",
        "PROFILE_ENVIRONMENT_COVERAGE",
        "PROFILE_EXTENSION_COVERAGE_EVIDENCE",
    } <= nodes
    assert not any(
        edge["from"] == "LTA_PROFILE_EXTENSION"
        and edge["to"] in {"PARTITION_CRITICAL_PROFILE_FEATURES", "SELECTION_FEATURE_CATALOGS"}
        for edge in graph["edges"]
    )


def test_data9a7d_runtime_versions() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert mdstats.MLFF_DATA6_PARSER_VERSION == "0.20.53a0"
    assert mdstats.MLFF_DATA9A7D_PARSER_VERSION == "0.20.50a0"
