from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_final_gpu1_release_manual_graph_and_spec_are_synchronized() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}
    edges = graph["edges"]
    changelog = (root / "CHANGELOG.md").read_text()
    readme = (root / "README.md").read_text()

    assert tuple(int(part) for part in mdstats.__version__.split("a", 1)[0].split(".")) >= (0, 20, 210)
    assert "revision 59" in manual
    assert "Gate FINAL-GPU1" in manual
    assert "release-handoff implementation (revision 59)" in manual
    assert "final-release blocker rather than an implementation blocker" in manual
    assert "**Gate:** `FINAL-GPU1`" in spec
    assert "gpu_qualification_deferred_until_final_release" in (root / "tools/run_mlff_final_gpu_qualification.py").read_text()
    assert graph["architecture_revision"] >= 77
    assert graph["schema_version"] >= 59
    assert "implementation_requires" in graph["edge_type_definitions"]
    assert "release_qualification_requires" in graph["edge_type_definitions"]
    assert nodes["SIZE_FIDELITY1_COARSE_SCREEN_CALIBRATION"]["implementation_status"] == "implemented_deferred_final_gpu_qualification"
    assert nodes["PERF_P2R_SUCCESSIVE_FIDELITY_EXECUTION"]["implementation_status"] == "implemented_cpu_control_plane_deferred_final_gpu_qualification"
    assert nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]["implemented_version"] == "0.20.209a0"
    assert nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]["cueq_phase2_qualification_schema"] == mdstats.CUEQ_PHASE2_QUALIFICATION_SCHEMA
    final = nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]
    assert final["perf_cert1_qualification_schema"] == mdstats.PERF_CERT1_QUALIFICATION_SCHEMA
    assert final["final_gpu1_policy_schema"] == mdstats.FINAL_GPU1_POLICY_SCHEMA
    assert final["final_gpu1_evidence_schema"] == mdstats.FINAL_GPU1_EVIDENCE_SCHEMA
    assert final["final_gpu1_qualification_schema"] == mdstats.FINAL_GPU1_QUALIFICATION_SCHEMA
    assert final["required_pass_gates"] == list(mdstats.FINAL_GPU1_REQUIRED_PASS_GATES)
    assert final["measure_only_gates"] == list(mdstats.FINAL_GPU1_MEASURE_ONLY_GATES)
    assert final["optional_gates"] == list(mdstats.FINAL_GPU1_OPTIONAL_GATES)
    assert final["runtime_bound_gates"] == list(mdstats.FINAL_GPU1_RUNTIME_BOUND_GATES)
    assert final["handoff_integrity_schema"] == "mdstats.mlff-final-gpu1.handoff-integrity.2026-08.v1"
    assert final["immutable_gate_registration"] is True
    assert "verify" in final["handoff_commands"]
    assert final["generated_default_change_authorized"] is False
    assert {"from": "SIZE_FIDELITY1_COARSE_SCREEN_CALIBRATION", "to": "PERF_P2R_SUCCESSIVE_FIDELITY_EXECUTION", "type": "implementation_requires"} in edges
    assert "## 0.20.210a0 - 2026-08-16" in changelog
    assert "## FINAL-GPU1 v2 in 0.20.209a0" in readme
    assert final["typed_migration_evidence_required"] is True
    assert final["source_tree_migration_activation_cli"] == "tools/activate_mlff_target_mv_migration.py"


def test_final_gpu1_markdown_sources_exist_before_pdf_render() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV50.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.184a0.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.192a0.md",
        root / "docs/guides/mlff_final_gpu1_workstation_runbook.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV59.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV76.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.209a0.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 1_500, path
