from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_data9a7e_specification_and_architecture_status() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_data9a7e_cross_system_qualification_spec.md").read_text()
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    stage = (ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md").read_text()
    assert 'version: "0.20.51a0"' in spec
    assert "DATA9A7e - cross-system qualification (implemented in 0.20.51a0)" in manual
    assert "MLFF-DATA9A7e - cross-system qualification - implemented in 0.20.51a0" in stage
    for token in (
        "ImportIsolationEvidence",
        "CrossSystemQualificationCaseRecord",
        "CrossSystemQualificationSuiteRecord",
        "generic crystalline solid",
        "amorphous solid",
        "homogeneous liquid",
        "multiphase interface",
        "optional LTA extension",
    ):
        assert token in spec


def test_data9a7e_dependency_graph_and_public_api() -> None:
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 34
    nodes = {item["id"] for item in graph["nodes"]}
    assert {
        "CROSS_SYSTEM_QUALIFICATION_POLICY",
        "GENERIC_IMPORT_ISOLATION_EVIDENCE",
        "CROSS_SYSTEM_CASE_QUALIFICATION_EVIDENCE",
        "CROSS_SYSTEM_QUALIFICATION_SUITE",
    } <= nodes
    assert mdstats.__version__ == "0.20.140a0"
    assert mdstats.MLFF_DATA9A7E_PARSER_VERSION == "0.20.51a0"
    assert callable(mdstats.qualify_cross_system_case)
    assert callable(mdstats.build_cross_system_qualification_suite)
