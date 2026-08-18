from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_rev89_feas1_perf2_release_manual_graph_and_spec_are_synchronized() -> None:
    assert mdstats.__version__ == "0.20.222a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV89.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2b_feas1_perf2_spec.md").read_text()
    assert "Revision 89 current gate: TARGET-DATA2B-FEAS1-PERF2" in manual
    assert "0.20.222a0" in note
    assert "target_coverage_feasibility_block_workers" in spec
    assert "Process count is therefore not used as a performance proxy" in spec
    assert "No GPU neighborhood backend is authorized" in spec

    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 89
    assert graph["schema_version"] == 71
    assert graph["documentation_gate"] == "TARGET_DATA2B_FEAS1_PERF2_BLOCK_PARALLEL_PROGRESS"
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["TARGET_DATA2B_FEAS1_PERF2_BLOCK_PARALLEL_PROGRESS"]
    assert gate["scientific_digest_changed"] is False
    assert gate["shared_tree_block_parallelism"] is True
    assert gate["deterministic_witness_order_reduction"] is True
    assert gate["feas1_interval_heartbeat_progress"] is True
    assert gate["mvidx1_block_progress"] is True
    assert gate["gpu_neighborhood_backend_authorized"] is False
