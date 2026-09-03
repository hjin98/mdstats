from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
SPEC = ROOT / "docs/specs/training_data/mlff_staged_precision_profiles_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
EVIDENCE = ROOT / "release/mlff_prec3_profile_activation_qualification.json"


def test_prec3_architecture_is_closed_and_storage_is_next() -> None:
    manual = MANUAL.read_text(encoding="utf-8")
    spec = SPEC.read_text(encoding="utf-8")
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert "PREC3 - campaign integration, qualification, and profile activation - implemented in 0.20.110a0" in manual
    assert "PREC3 implementation closure (0.20.110a0)" in manual
    assert "PREC3 implemented in mdstats 0.20.110a0" in spec
    assert "The post-0.20.105 evaluation, precision, and storage implementation roadmap is complete." in manual
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34


def test_prec3_qualification_evidence_is_transparent_about_cueq() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["package_version"] == "0.20.110a0"
    assert payload["backend_qualification"]["e3nn_real_mace_executed"] is True
    assert payload["backend_qualification"]["cueq_real_runtime_executed"] is False
    assert "unavailable" in payload["backend_qualification"]["cueq_reason"]
    assert payload["scientific_equivalence_claimed"] is False
