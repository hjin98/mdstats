from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_mvstate_reuse1_selector_repair_handoff_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_mvstate_reuse1_cloud_cpu_mpa0_2026-08-17.json"


def test_mvstate_reuse1_historical_release_and_current_manual_are_synchronized() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture_revision: 103" in text
    assert "Gate MVSTATE-REUSE1 - selector-to-repair sparse-state reuse - COMPLETE" in text
    assert "CPU OPTIMIZATION CLOSED" in text
    assert SPEC.is_file()


def test_mvstate_reuse1_graph_closes_cpu_program_and_hands_to_final_gpu1() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] == 103
    assert graph["schema_version"] == 83
    assert graph["documentation_gate"] == "MVSTATE_REUSE1_SELECTOR_REPAIR_HANDOFF"
    assert graph["next_gate"] == "FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"
    nodes = {node["id"]: node for node in graph["nodes"]}
    current = nodes["MVSTATE_REUSE1_SELECTOR_REPAIR_HANDOFF"]
    assert current["implemented_release"] == "0.20.236a0"
    assert current["implementation_status"] == "implemented_cpu_optimization_closed"
    assert current["optimization_program_closed"] is True
    assert current["scientific_authority_change"] is False
    assert current["selector_rank_authority_change"] is False
    assert current["repair_objective_authority_change"] is False
    assert current["next_gate"] == "FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"


def test_mvstate_reuse1_evidence_is_exact_and_material() -> None:
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert ev["release"] == "0.20.236a0"
    assert ev["architecture_revision"] == 103
    assert ev["acceptance"]["status"] == "PASS_CPU_OPTIMIZATION_CLOSED"
    assert ev["acceptance"]["cpu_optimization_program_closed"] is True
    assert ev["acceptance"]["next_gate"] == "FINAL-GPU1"
    assert ev["acceptance"]["scientific_outputs_exact"] is True
    assert ev["active_foundation"]["checkpoint_sha256"] == "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    assert ev["active_foundation"]["mh1_compatible"] is True
    assert ev["scientific"]["repair_digest"] == "ab7dc752555114bcd756913187e1d0eb7069c2e9a093f2a8a41130f485cdc33f"
    assert ev["state_cache"]["content_digest"] == "9904a0c96c83f4fdfe47558dc115d59664ab1a5a5456e687b9d7d3c75c1912db"
    assert ev["execution"]["target_chain_mvstate"]["repair_speedup"] > 1.2
    assert ev["execution"]["target_chain_mvstate"]["speedup_vs_control_fresh_including_cache_write"] > 1.05
    assert ev["execution"]["cumulative_vs_perfbase1_0_20_225"]["speedup_fresh_including_mvstate_cache_write"] > 2.4
    assert ev["exactness_decisions"]["pure_checkpoint_reconciliation_after_repair_divergence"] == "rejected"


def test_mvstate_reuse1_code_and_history_contracts_exist() -> None:
    code = (ROOT / "mdstats/training_data/target_multi_view_selection_state.py").read_text(encoding="utf-8")
    store = (ROOT / "mdstats/training_data/target_multi_view_selection_state_store.py").read_text(encoding="utf-8")
    repair = (ROOT / "mdstats/training_data/target_multi_view_repair.py").read_text(encoding="utf-8")
    campaign = (ROOT / "mdstats/training_data/campaign_cli.py").read_text(encoding="utf-8")
    for token in ("TargetMultiViewSelectionStateCache", "verify_state_replay", "restore_domain_state"):
        assert token in code
    assert "np.savez" in store and '"array_bundle"' in store
    assert "repair_has_diverged" in repair and "selection_state_cache" in repair
    assert "target_multi_view_selection_state_cache" in campaign
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV103.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.236a0.md").is_file()
    assert (ROOT / "benchmarks/mlff_mvstate_reuse1_implementation_manifest_0.20.236a0.json").is_file()
