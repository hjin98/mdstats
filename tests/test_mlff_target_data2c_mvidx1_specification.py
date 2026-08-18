from pathlib import Path
import json

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mvidx1_release_manual_and_spec_are_synchronized():
    assert mdstats.__version__ == "0.20.209a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "revision 68" in manual
    assert "TARGET-DATA2C-MVIDX1 - implemented exact sparse bidirectional coverage" in manual
    assert "witness_offsets + witness_candidates" in manual
    assert "candidate_offsets + candidate_witnesses" in manual
    assert "TARGET-DATA2C selector behavior remains revision-64 v4" in manual
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2c_mvidx1_sparse_coverage_index_spec.md").read_text()
    assert "**Release:** `mdstats 0.20.201a0`" in spec
    assert "uint32" in spec and "uint64" in spec
    assert "TARGET-DATA2C-MVSEL1" in spec


def test_mvidx1_dependency_graph_marks_gate_implemented_and_next_gate_planned():
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    assert graph["documentation_gate"] == "SIZE_FIDELITY2_MV_SURVIVOR_REQUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    index = nodes["TARGET_DATA2C_MVIDX1_COVERAGE_INDEX"]
    assert index["implementation_status"] == "implemented_index_substrate"
    assert index["implemented_release"] == "0.20.201a0"
    assert index["record_name"] == "target_coverage_sparse_index"
    assert index["runtime_selector_changed"] is False
    assert index["candidate_index_dtype"] == "uint32"
    assert index["offset_dtype"] == "uint64"
    assert nodes["TARGET_DATA2C_MVSEL1_PROGRESSIVE_SELECTOR"]["implementation_status"] == "implemented_diagnostic_pre_migration"
    assert any(
        edge["from"] == "TARGET_DATA2B_FEAS1_FULL_POOL_FEASIBILITY"
        and edge["to"] == "TARGET_DATA2C_MVIDX1_COVERAGE_INDEX"
        and edge["type"] == "implementation_requires"
        for edge in graph["edges"]
    )


def test_mvidx1_campaign_integration_and_native_persistence_are_present():
    cli = (ROOT / "mdstats/training_data/campaign_cli.py").read_text()
    assert '"target_coverage_sparse_index"' in cli
    assert "_ensure_target_coverage_sparse_index" in cli
    assert "TARGET-DATA2C v4 unchanged" in cli
    assert "build_target_coverage_sparse_index" in cli
    store = (ROOT / "mdstats/training_data/target_coverage_sparse_index_store.py").read_text()
    assert "content-addressed" in store.lower() or "target-coverage-sparse-index-" in store
    assert "np.save" in store
    assert "mmap_mode" in store


def test_mvidx1_changelog_and_patch_notes_are_current():
    changelog = (ROOT / "CHANGELOG.md").read_text()
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    patch = (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.201a0.md").read_text()
    assert "TARGET-DATA2C-MVIDX1" in patch
    assert "pre-migration" in patch
