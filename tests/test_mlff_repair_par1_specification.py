from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_repair_par1_deterministic_parallel_proposals_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_repair_par1_cloud_cpu_mpa0_2026-08-17.json"


def test_repair_par1_release_manual_and_package_metadata_are_synchronized() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate REPAIR-PAR1 - deterministic parallel repair proposals - COMPLETE" in text
    assert "**Next gate.** `MVQUAL-PAR1`." in text
    assert "adaptive" in text
    assert "historical removal-shortlist order" in text
    assert SPEC.is_file()


def test_repair_par1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 98
    assert graph["schema_version"] >= 78
    node = next(item for item in graph["nodes"] if item["id"] == "REPAIR_PAR1_PROPOSAL_QUEUE")
    assert node["implementation_status"] == "implemented_deterministic_parallel_proposals"
    assert node["implemented_release"] == "0.20.231a0"
    assert node["sequential_repair_authority_changed"] is False
    assert node["scientific_authority_change"] is False
    assert node["canonical_winner_reduction"] == "historical_removal_shortlist_order"


def test_repair_par1_code_contains_exact_execution_contract() -> None:
    repair = (ROOT / "mdstats/training_data/target_multi_view_repair.py").read_text(encoding="utf-8")
    campaign = (ROOT / "mdstats/training_data/campaign_cli.py").read_text(encoding="utf-8")
    for token in (
        "_RepairProposalScratch",
        "_candidate_removal_metrics",
        "_best_repair_proposal",
        "DeterministicWorkQueue",
        "rank_by_candidate",
        "_REPAIR_PARALLEL_EDGE_WORK_THRESHOLD",
        'proposal_optimized=(execution_mode == "optimized")',
    ):
        assert token in repair
    assert "target_multi_view_repair_workers" in campaign
    assert "TARGET-DATA2C-REPAIR-PAR1" in campaign


def test_repair_par1_history_records_are_present() -> None:
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV98.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.231a0.md").is_file()
    assert "## 0.20.231a0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_repair_par1_frozen_benchmark_evidence_is_consistent() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.231a0"
    assert evidence["architecture_revision"] == 98
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "MVQUAL-PAR1"
    assert evidence["active_foundation"]["family"] == "MACE-MPA-0 medium"
    assert evidence["active_foundation"]["checkpoint_sha256"] == (
        "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    )
    assert evidence["active_foundation"]["mh1_compatible"] is True
    scientific = evidence["scientific"]
    assert scientific["standard_repair_plan_digest"] == (
        "5dcb048b02ae2670d48d15f3f610b5814b611b2339df4ec4b265a52615b9545b"
    )
    assert scientific["medium_proposal_result_digest"] == (
        "1a09e7745aa534bed757334ad9d365099e28635050ec63f1244421e4b859a9b1"
    )
    assert scientific["large_proposal_result_digest"] == (
        "9fda146806fc12f7c4d8030877e3a09cd206cef01eb6f821be0010c468b41994"
    )
    assert scientific["worker_count_trace_exact"] is True
    medium = evidence["execution"]["medium_2048_candidate_proposal"]
    large = evidence["execution"]["large_8192_candidate_proposal"]
    assert medium["speedup"] > 10.0
    assert medium["adaptive_parallel_dispatch"] is False
    assert large["serial_vectorization_speedup"] > 2.0
    assert large["four_lane_end_to_end_speedup"] > 4.0
    assert large["one_to_four_lane_scaling"] > 1.2
    assert large["adaptive_parallel_dispatch"] is True
