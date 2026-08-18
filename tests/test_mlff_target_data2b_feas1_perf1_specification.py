from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_rev88_feas1_perf1_release_manual_graph_and_spec_are_synchronized() -> None:
    assert mdstats.__version__ == "0.20.221a0"
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV88.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_target_data2b_feas1_perf1_spec.md").read_text()
    assert "Revision 88 current gate: TARGET-DATA2B-FEAS1-PERF1" in manual
    assert "0.20.221a0" in note
    assert "target_coverage_feasibility_family_workers" in spec
    assert "No GPU neighborhood backend is authorized" in spec

    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] == 88
    assert graph["schema_version"] == 70
    assert graph["documentation_gate"] == "TARGET_DATA2B_FEAS1_PERF1_EXACT_HARDENING"
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["TARGET_DATA2B_FEAS1_PERF1_EXACT_HARDENING"]
    assert gate["scientific_digest_changed"] is False
    assert gate["vectorized_row_candidate_deduplication"] is True
    assert gate["historical_fp64_accumulation_order_preserved"] is True
    assert gate["gpu_neighborhood_backend_authorized"] is False
