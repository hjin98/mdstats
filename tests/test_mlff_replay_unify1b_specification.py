from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_replay_unify1b_release_and_architecture_are_synchronized():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    note = (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV78.md").read_text(encoding="utf-8")
    assert "REPLAY-UNIFY1B implementation boundary" in manual
    assert "REPLAY-UNIFY1B implementation boundary" in manual
    assert "12,000 configurations" in manual
    assert "10,000 train plus 2,000 monitor" in manual
    assert "one source pass" in manual
    assert "accidental quadratic hot path" in manual
    assert "Dependency-graph schema:** 60" in note
    assert "0.20.211a0" in note


def test_dependency_graph_records_gate_b_authority_and_keeps_production_switch_deferred():
    graph_path = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 78
    assert graph["schema_version"] >= 60
    nodes = {node["id"]: node for node in graph["nodes"]}
    gate = nodes["REPLAY_UNIFY1B_TRUE_LABEL_MATERIALIZATION"]
    assert gate["implementation_status"] == "implemented_additive_pre_migration"
    assert gate["implemented_release"] == "0.20.211a0"
    assert gate["production_replay_execution_changed"] is False
    assert gate["true_label_cache_schema"] == "mdstats.replay-true-label-cache.v1"
    assert gate["true_label_view_schema"] == "mdstats.replay-true-label-view.v1"
    assert gate["lazy_role_materialization"] is True
    assert gate["dual_role_single_source_pass"] is True
    assert gate["authenticated_cache_hit_source_parse_count"] == 0
    assert gate["supplied_lta_default_split_counts"] == [10000, 2000]
    assert gate["next_gate"] == "REPLAY_UNIFY1C_PSEUDOLABEL_MATERIALIZATION"
    assert nodes["REPLAY_UNIFY1C_PSEUDOLABEL_MATERIALIZATION"]["implementation_status"] in {"planned_frozen", "implemented_additive_pre_migration"}
    assert not (ROOT / "mlff_training_data_dependency_graph.json").exists()
    assert (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json").is_file()


def test_gate_b_public_contract_is_additive_and_legacy_true_label_api_remains_public():
    for name in (
        "ReplayTrueLabelCache",
        "ReplayTrueLabelViewArtifact",
        "ReplaySplitRole",
        "build_replay_true_label_cache",
        "materialize_replay_true_label_views",
    ):
        assert hasattr(mdstats, name), name
    # Gate D still owns the production replay-interface switch.
    assert hasattr(mdstats, "materialize_true_label_replay_split")
    assert hasattr(mdstats, "resolve_true_label_replay_directory")
    assert hasattr(mdstats, "ReplayPreparationPlan")
