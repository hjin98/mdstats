from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
EVIDENCE = ROOT / "benchmarks/mlff_campaign_perf_qual1_cloud_cpu_mpa0_2026-08-17.json"
SPEC = ROOT / "docs/specs/training_data/mlff_campaign_perf_qual1_closure_spec.md"
NEXT_SPEC = ROOT / "docs/specs/training_data/mlff_mvstate_reuse1_selector_repair_handoff_spec.md"


def test_campaign_perf_qual1_historical_release_and_current_manual_are_synchronized() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate CAMPAIGN-PERF-QUAL1 - end-to-end optimization closure - COMPLETE" in text
    assert "Gate MVSTATE-REUSE1 - selector-to-repair sparse-state reuse - COMPLETE" in text
    assert SPEC.is_file() and NEXT_SPEC.is_file()
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV102.md").is_file()


def test_campaign_perf_qual1_graph_remains_closed_historical_authority() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in graph["nodes"]}
    current = nodes["CAMPAIGN_PERF_QUAL1_CLOSURE"]
    assert current["implemented_release"] == "0.20.235a0"
    assert current["implementation_status"] == "implemented_pass_followup_required"
    assert current["scientific_authority_change"] is False
    assert current["runtime_algorithm_change"] is False
    assert current["optimization_program_closed"] is False
    nxt = nodes["MVSTATE_REUSE1_SELECTOR_REPAIR_HANDOFF"]
    assert nxt["implementation_status"] == "implemented_cpu_optimization_closed"
    assert nxt["selector_rank_authority_change"] is False
    assert nxt["repair_objective_authority_change"] is False


def test_campaign_perf_qual1_frozen_evidence_is_exact_and_identifies_shifted_hotspot() -> None:
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert ev["release"] == "0.20.235a0"
    assert ev["architecture_revision"] == 102
    assert ev["acceptance"]["status"] == "PASS_FOLLOWUP_REQUIRED"
    assert ev["acceptance"]["next_gate"] == "MVSTATE-REUSE1"
    assert ev["acceptance"]["scientific_outputs_exact"] is True
    assert ev["acceptance"]["optimization_program_closed"] is False
    assert ev["active_foundation"]["checkpoint_sha256"] == "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    assert ev["active_foundation"]["mh1_compatible"] is True
    assert ev["execution"]["target_chain"]["current"]["speedup_vs_control_at_4_lanes"] > 2.0
    assert ev["scientific"]["feasibility_digest"] == "937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613"
    assert ev["scientific"]["mvidx_digest"] == "e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c"
    assert ev["hotspot_reprofile"]["repair_profile"]["selector_state_replay__select_and_update_calls"] >= 4096
    assert "duplicated" in ev["hotspot_reprofile"]["repair_profile"]["finding"]
    assert ev["restart_and_memory"]["memory_ceiling_violation"] is False


def test_campaign_perf_qual1_history_and_release_records_exist() -> None:
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV102.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.235a0.md").is_file()
    assert "0.20.235a0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert (ROOT / "benchmarks/mlff_campaign_perf_qual1_implementation_manifest_0.20.235a0.json").is_file()
