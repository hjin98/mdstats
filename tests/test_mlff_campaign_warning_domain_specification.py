from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_rev87_warning_domain_is_retained_under_current_release() -> None:
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV87.md").read_text()
    spec = (ROOT / "docs/specs/training_data/mlff_campaign_warning_domain_spec.md").read_text()
    assert "Revision 87 historical gate: WARN-DOMAIN1" in manual
    assert "0.20.220a0" in note
    assert "WARNING:root:" in spec
    assert "worker thread" in spec
    graph = json.loads((ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    assert graph["architecture_revision"] >= 88
    assert graph["schema_version"] >= 70
    assert graph["documentation_gate"] == "TARGET_DATA2B_FEAS1_PERF1_EXACT_HARDENING"
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["CAMPAIGN_WARNING_DOMAIN"]
    assert gate["root_logger_mace_capture"] is True
    assert gate["worker_thread_scope_merge"] is True
    assert gate["raw_upstream_warning_leak_allowed"] is False
    assert gate["scientific_authority_changed"] is False
