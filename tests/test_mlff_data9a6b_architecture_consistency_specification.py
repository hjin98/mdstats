from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_ARCH = ROOT / "docs" / "history" / "mlff" / "manual_snapshots" / "mlff_training_data_architecture_rev090_full.md"
THERMO = ROOT / "docs" / "arch_manuals" / "thermomechanical_energetic_validation_architecture.md"
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_data9a6b_architecture_consistency_spec.md"
HISTORICAL_GRAPH = ROOT / "docs" / "history" / "mlff" / "manual_snapshots" / "mlff_training_data_dependency_graph_pre_doc_gov1.json"


def test_consistency_spec_freezes_ownership_and_lineage() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "ObservableCollectionIdentity",
        "TrajectoryGenerationIdentity",
        "construction-time dependency",
        "ObservableRecommendationProfile",
        "DATA9A7a",
        "DATA9A7e",
        "thermomechanical and energetic validation architecture",
    ):
        assert token in text


def test_historical_mlff_manual_makes_generic_profile_normative() -> None:
    # DATA9A6b is explicitly superseded by DATA9A6c.  Its generic/LTA claim is
    # retained under the historical manual owner, not projected onto the
    # current proposed D3 renewal candidate.
    text = HISTORICAL_ARCH.read_text(encoding="utf-8")
    assert "LTA is an optional profile extension" in text
    assert "ObservableRecommendationProfile" in text
    assert "DATA9A7a" in text
    assert "DATA9A7e" in text
    assert "No LAMMPS-specific implementation stage" in text


def test_thermomechanical_manual_defines_theory_and_stages() -> None:
    text = THERMO.read_text(encoding="utf-8")
    for token in (
        "Equation of state and equilibrium volume",
        "Elastic constants and mechanical stability",
        "Thermal expansion, compressibility, and heat capacity",
        "Stress autocorrelation and viscosity",
        "Harmonic phonons and quasiharmonic thermodynamics",
        "Surface energies",
        "Interface energy and work of adhesion",
        "Defect formation and binding energies",
        "Migration paths and barriers",
        "TE0 - Architecture and common records",
        "TE8 - Cross-system qualification",
        "The initial release of this manual is architectural",
        "Harmonic thermodynamic functions",
        "zero-point energy",
        "LO--TO splitting",
        "Multicomponent convex hull",
        "energy above the hull",
        "Transport ownership and thermal conductivity",
    ):
        assert token in text


def test_dependency_graph_treats_lta_as_optional() -> None:
    graph = json.loads(HISTORICAL_GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] == 103
    nodes = {node["id"] for node in graph["nodes"]}
    assert "MATERIAL_PROFILE_IDENTITY" in nodes
    assert "LTA_PROFILE_EXTENSION" in nodes
    optional = {
        (edge["from"], edge["to"])
        for edge in graph["edges"]
        if edge["type"] == "optional_enrichment"
    }
    assert ("LTA_PROFILE_EXTENSION", "OPTIONAL_PROFILE_EXTENSION_PROVIDER") in optional
    assert ("OPTIONAL_PROFILE_EXTENSION_PROVIDER", "PROFILE_SELECTION_FEATURE_CATALOGS") in optional
    assert ("PROFILE_SELECTION_FEATURE_CATALOGS", "SELECTION_FEATURE_CATALOGS") in optional
