from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvqual1_release_manual_and_spec_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 72" in manual
    assert "TARGET-DATA2C-MVQUAL1 - implemented independent same-N scientific qualification" in manual
    assert "D_max_MV(N) <= D_max_legacy(N) + 1e-12" in manual
    assert "deferred_final_gpu_qualification" in manual
    assert "revision-64 TARGET-DATA2C v4 remains" in manual
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_mvqual1_same_n_qualification_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.205a0`" in spec
    assert "independent TARGET-DATA2B" in spec
    assert "SIZE-HALVE2" in spec


def test_mvqual1_dependency_graph_marks_gate_implemented_and_next_gate():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["TARGET_DATA2C_MVQUAL1_SAME_N_QUALIFICATION"]
    assert gate["implementation_status"] == "implemented_independent_same_n_qualification"
    assert gate["implemented_release"] == "0.20.205a0"
    assert gate["independent_coverage_rescore"] == "TARGET-DATA2B"
    assert gate["hard_obligation_authority"] == "TARGET-DATA2A+MVIDX1"
    assert gate["all_mv_rungs_independently_rescored_for_capacity"] is True
    assert gate["runtime_selector_changed"] is False
    assert gate["next_gate"] == "SIZE_HALVE2_EIGHT_CANDIDATE_FUNNEL"


def test_mvqual1_code_freezes_independent_nonregression_and_deferred_learning_contracts():
    source = (ROOT / "mdstats/training_data/target_multi_view_qualification.py").read_text()
    cli = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert "score_target_subset_coverage" in source
    assert "indexed_obligation_selected_counts" in source
    assert "same_n_nonregression_failed" in source
    assert "capacity_limited_within_16384" in source
    assert 'deferred_final_gpu_qualification' in source
    assert 'store.put_record("target_multi_view_qualification", plan)' in cli
    assert '"target_multi_view_qualification"' in cli


def test_mvqual1_patch_notes_and_changelog_are_present():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.205a0.md").read_text()
    assert "TARGET-DATA2C-MVQUAL1" in patch
    assert "16,384" in patch
    assert "final consolidated GPU qualification" in patch
