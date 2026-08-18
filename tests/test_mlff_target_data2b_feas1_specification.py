from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_feas1_release_manual_and_spec_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 67" in manual
    assert "TARGET-DATA2B-FEAS1 - implemented" in manual
    assert "correlation-unit-excluded support" in manual
    assert "K_min_lower_bound" in manual
    assert "TARGET-DATA2C selector behavior remains revision-64 v4" in manual
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2b_feas1_support_capacity_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.200a0`" in spec
    assert "16384" in spec
    assert "provably_capacity_infeasible" in spec


def test_feas1_dependency_graph_marks_gate_implemented_and_next_gate_planned():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    feas = nodes["TARGET_DATA2B_FEAS1_FULL_POOL_FEASIBILITY"]
    assert feas["implementation_status"] == "implemented_diagnostic_only"
    assert feas["implemented_release"] == "0.20.200a0"
    assert feas["fixed_candidate_ceiling"] == 16384
    assert feas["correlation_interval_count_is_hard_lower_bound"] is True
    assert nodes["TARGET_DATA2C_MVIDX1_COVERAGE_INDEX"]["implementation_status"] == "implemented_index_substrate"
    assert any(
        edge["from"] == "TARGET_DATA2B_COVERAGE_REFERENCE_V2"
        and edge["to"] == "TARGET_DATA2B_FEAS1_FULL_POOL_FEASIBILITY"
        and edge["type"] == "execution_requires"
        for edge in graph["edges"]
    )


def test_feas1_campaign_integration_is_diagnostic_only():
    cli = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"target_coverage_feasibility"' in cli
    assert "_ensure_target_coverage_feasibility" in cli
    assert "TARGET-DATA2C v4 unchanged" in cli
    assert "build_target_coverage_feasibility_report" in cli


def test_feas1_changelog_and_patch_notes_are_current():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.200a0.md").read_text()
    assert "TARGET-DATA2B-FEAS1" in patch
    assert "diagnostic-only" in patch
