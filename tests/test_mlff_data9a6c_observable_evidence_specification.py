from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_data9a6c_observable_evidence_leakage_spec.md"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
GRAPH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_dependency_graph.json"
THERMO = ROOT / "docs" / "arch_manuals" / "thermomechanical_energetic_validation_architecture.md"
MANUAL_INDEX = ROOT / "mdstats" / "data" / "observable_owner_manuals.json"


def test_data9a6c_spec_freezes_evidence_and_leakage_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Supplied collection identities",
        "TrajectoryGenerationIdentity",
        "ObservableResultIdentity",
        "ObservableEvidenceRole",
        "locked_test",
        "comparison policy + activation -> evidence",
        "source/wheel registry parity",
        "valid JSON release artifacts",
    ):
        assert token in text


def test_mlff_manual_records_data9a6c_and_policy_order() -> None:
    text = ARCH.read_text(encoding="utf-8")
    assert "MLFF-DATA9A6c observable evidence and leakage closure" in text
    assert "Statistical role, policy ordering, and locked-test leakage" in text
    assert "ObservableComparisonPolicy" in text
    assert "ObservableComparisonResult" in text
    assert "ObservableAcceptanceDecision" in text


def test_dependency_graph_places_policy_before_evidence_and_forbids_reverse_edge() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    edges = {(e["from"], e["to"]) for e in graph["edges"]}
    assert ("OBSERVABLE_COMPARISON_POLICY", "OBSERVABLE_VALIDATION_ACTIVATION_RECORD") in edges
    assert ("OBSERVABLE_VALIDATION_ACTIVATION_RECORD", "OBSERVABLE_VALIDATION_EVIDENCE") in edges
    assert ("OBSERVABLE_VALIDATION_EVIDENCE", "OBSERVABLE_COMPARISON_RESULT") in edges
    assert ("OBSERVABLE_COMPARISON_POLICY", "OBSERVABLE_COMPARISON_RESULT") in edges
    assert ("OBSERVABLE_COMPARISON_RESULT", "OBSERVABLE_ACCEPTANCE_DECISION") in edges
    assert ("OBSERVABLE_VALIDATION_EVIDENCE", "LOCKED_TEST_OBSERVABLE_EVIDENCE") in edges
    assert ("OBSERVABLE_VALIDATION_EVIDENCE", "OBSERVABLE_COMPARISON_POLICY") not in edges
    assert any("OBSERVABLE_COMPARISON_POLICY" in item["to"] for item in graph["forbidden_dependencies"])
    assert any("LOCKED_TEST_OBSERVABLE_EVIDENCE" in item["from"] for item in graph["forbidden_dependencies"])
    assert not any(
        "OBSERVABLE_VALIDATION_EVIDENCE" in item["from"]
        and "CHECKPOINT_SELECTION_DECISION" in item["to"]
        for item in graph["forbidden_dependencies"]
    )


def test_thermomechanical_manual_has_expanded_reference_and_phonon_theory() -> None:
    text = THERMO.read_text(encoding="utf-8")
    for token in (
        "magnetic state",
        "electronic occupation/smearing",
        "Harmonic thermodynamic functions",
        "zero-point energy",
        "acoustic sum rule",
        "LO--TO splitting",
        "Multicomponent convex hull",
        "energy above the hull",
        "Thermal conductivity is not owned by the MLFF branch",
    ):
        assert token in text


def test_packaged_owner_manual_index_is_valid() -> None:
    payload = json.loads(MANUAL_INDEX.read_text(encoding="utf-8"))
    assert payload["package_version"] == "0.20.132a0"
    assert "structural-observables-architecture" in payload["manuals"]
