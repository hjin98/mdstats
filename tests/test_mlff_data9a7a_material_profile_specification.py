from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_data9a7a_material_profile_contracts_spec.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
MODULE = ROOT / "mdstats/training_data/material_profiles.py"


def test_data9a7a_spec_and_manual_freeze_the_declarative_boundary() -> None:
    spec = SPEC.read_text(encoding="utf-8")
    manual = MANUAL.read_text(encoding="utf-8")
    for token in (
        "MaterialProfileIdentity",
        "PhaseComponentIdentity",
        "AtomGroupCatalog",
        "ConditionAxisCatalog",
        "IndependenceAxisCatalog",
        "SystemProfileProvider",
        "explicitly declare",
        "does **not** calculate",
        "DATA4 schema v2",
    ):
        assert token in spec
    assert "implemented in 0.20.47a0" in manual
    assert "An interface composes" in manual or "solid-liquid interface" in manual
    assert "optional" in manual and "LTA" in manual


def test_data9a7a_runtime_module_does_not_import_lta() -> None:
    text = MODULE.read_text(encoding="utf-8")
    assert "lta_profile" not in text
    assert "lta_selection" not in text
    assert "class SystemProfileProvider" in text
    assert "class MaterialProfileContracts" in text


def test_data9a7a_dependency_graph_contains_contract_chain() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {item["id"] for item in graph["nodes"]}
    required = {
        "MATERIAL_PROFILE_PROVIDER_IDENTITY",
        "PHASE_COMPONENT_IDENTITIES",
        "MATERIAL_PROFILE_IDENTITY",
        "ATOM_GROUP_CATALOG",
        "CONDITION_AXIS_CATALOG",
        "INDEPENDENCE_AXIS_CATALOG",
        "MATERIAL_PROFILE_CONTRACTS",
    }
    assert required <= nodes
    edges = {(item["from"], item["to"], item["type"]) for item in graph["edges"]}
    assert ("MATERIAL_PROFILE_PROVIDER_IDENTITY", "MATERIAL_PROFILE_IDENTITY", "source_identity_requires") in edges
    assert ("PHASE_COMPONENT_IDENTITIES", "MATERIAL_PROFILE_IDENTITY", "execution_requires") in edges
    for source in ("MATERIAL_PROFILE_IDENTITY", "ATOM_GROUP_CATALOG", "CONDITION_AXIS_CATALOG", "INDEPENDENCE_AXIS_CATALOG"):
        assert (source, "MATERIAL_PROFILE_CONTRACTS", "execution_requires") in edges
    assert ("LTA_PROFILE_EXTENSION", "OPTIONAL_PROFILE_EXTENSION_PROVIDER", "optional_enrichment") in edges
    assert ("OPTIONAL_PROFILE_EXTENSION_PROVIDER", "PROFILE_SELECTION_FEATURE_CATALOGS", "optional_enrichment") in edges
    assert ("PROFILE_SELECTION_FEATURE_CATALOGS", "SELECTION_FEATURE_CATALOGS", "optional_enrichment") in edges


def test_release_version_is_data9a7a() -> None:
    assert 'version = "0.20.140a0"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
