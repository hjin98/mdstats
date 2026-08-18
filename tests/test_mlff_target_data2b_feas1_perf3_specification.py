from __future__ import annotations

import json
from pathlib import Path

import mdstats


def test_rev90_perf3_release_manual_graph_and_spec_are_synchronized() -> None:
    root = Path(__file__).resolve().parents[1]
    assert mdstats.__version__ == "0.20.223a0"
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_target_data2b_feas1_perf3_spec.md").read_text()
    note = (root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.223a0.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())

    assert "Revision 90 current gate: TARGET-DATA2B-FEAS1-PERF3" in manual
    assert "single-level global work queue" in spec
    assert "target_coverage_feasibility_global_workers" in spec
    assert "profiles completed/total" in spec
    assert "0.20.223a0" in note
    assert graph["architecture_revision"] == 90
    assert graph["schema_version"] == 72
    assert graph["documentation_gate"] == "TARGET_DATA2B_FEAS1_PERF3_GLOBAL_QUEUE"
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["TARGET_DATA2B_FEAS1_PERF3_GLOBAL_QUEUE"]
    assert gate["parallel_tree_workers_per_task"] == 1
    assert gate["campaign_wide_profile_progress"] is True
    assert gate["scientific_digest_changed"] is False
