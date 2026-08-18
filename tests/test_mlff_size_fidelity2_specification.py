from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_size_fidelity2_release_public_surface_and_graph_are_synchronized():
    assert tuple(int(v) for v in mdstats.__version__.split("a",1)[0].split(".")) >= (0, 20, 209)
    assert mdstats.SIZE_FIDELITY2_VERSION == "mdstats.size-fidelity2.mv-survivor-requalification.2026-08.v1"
    for name in (
        "SizeFidelity2Policy", "SizeFidelity2MonitorView", "SizeFidelity2Checkpoint",
        "SizeFidelity2ExecutionPlan", "SizeFidelity2WidthAssessment", "SizeFidelity2QualificationReport",
        "build_size_fidelity2_execution_plan", "build_size_fidelity2_qualification",
        "validate_size_fidelity2_execution_plan", "validate_size_fidelity2_qualification",
    ):
        assert hasattr(mdstats, name), name
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] >= 76
    assert graph["schema_version"] >= 58
    node = next(v for v in graph["nodes"] if v["id"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION")
    assert node["implementation_status"] == "implemented_pre_migration_control_plane_gpu_deferred"
    assert node["implemented_release"] == "0.20.207a0"
    assert node["admission_widths"] == [4, 5, 6, 7, 8]
    assert node["single_trajectory_matrix_reused_across_q"] is True
    assert node["additional_monitor_inference_count"] == 0
    assert node["production_authority_changed"] is False
    assert node["next_gate"] == "TARGET-DATA2C-MVMIGRATE1"


def test_size_fidelity2_docs_freeze_survivor_recall_monitor_and_gpu_defer_contracts():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_size_fidelity2_mv_survivor_requalification_spec.md").read_text()
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.207a0.md").read_text()
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert "revision 74" in manual
    assert "N_runs = N_seeds * q_max" in manual
    assert "Required finalist recall is `1.0`" in manual
    assert "zero model-inference passes" in manual
    assert "deferred_final_gpu_qualification" in manual
    assert "**Gate:** `SIZE-FIDELITY2`" in spec
    assert "**Release:** `mdstats 0.20.207a0`" in spec
    assert "q=4..8" in spec or "q = 4" in spec
    assert "Additional monitor-model inference count is therefore exactly zero" in spec
    assert "FINAL-GPU1" in spec
    assert "SIZE-FIDELITY2" in patch and "zero additional model inference" in patch
    assert "## 0.20.209a0 - 2026-08-16" in changelog


def test_size_fidelity2_campaign_receipt_and_pre_migration_order_are_explicit():
    source = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"size_fidelity2_execution_plan"' in source
    assert "_ensure_size_fidelity2_execution_plan" in source
    prepare = source.index("target_multi_view_qualification = _ensure_target_multi_view_qualification")
    halve = source.index("size_halve2_plan = _ensure_size_halve2_plan", prepare)
    fidelity = source.index("_ensure_size_fidelity2_execution_plan(", halve)
    legacy = source.index("size_convergence = _ensure_target_size_convergence", fidelity)
    assert prepare < halve < fidelity < legacy
    assert "positive execution deferred to FINAL-GPU1" in source


def test_size_fidelity2_root_and_canonical_graph_manual_mirrors_match():
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()
    assert not (ROOT / "mlff_training_data_architecture.md").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").is_file()
