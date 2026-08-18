from __future__ import annotations

import json
from pathlib import Path

import mdstats
import mdstats.training_data.target_coverage_feasibility as feasibility

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
SPEC = ROOT / "docs/specs/training_data/mlff_parcore1_deterministic_work_queue_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
REV = ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV93.md"
PATCH = ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.226a0.md"
EVIDENCE = ROOT / "benchmarks/mlff_parcore1_feas1_cloud_cpu_mpa0_2026-08-17.json"
MANIFEST = ROOT / "benchmarks/mlff_parcore1_implementation_manifest_0.20.226a0.json"


def test_parcore1_release_manual_and_spec_are_retained_after_successor() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "PARCORE1 - shared deterministic CPU scheduler - COMPLETE" in text
    assert "**Succeeded by.** `NEIGHBOR1` in `0.20.227a0`." in text
    assert SPEC.is_file() and REV.is_file() and PATCH.is_file()
    assert "mdstats 0.20.226a0" in SPEC.read_text(encoding="utf-8")
    assert "mdstats 0.20.226a0" in REV.read_text(encoding="utf-8")


def test_parcore1_dependency_graph_closes_gate_and_advances_neighbor1() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 93
    assert graph["schema_version"] >= 75
    node = next(item for item in graph["nodes"] if item["id"] == "PARCORE1_DETERMINISTIC_WORK_QUEUE")
    assert node["implementation_status"] == "implemented"
    assert node["implemented_release"] == "0.20.226a0"
    assert node["scientific_authority_change"] is False
    assert node["runtime_optimization_change"] is True
    assert node["feas1_consumer_migrated"] is True
    assert node["bounded_ready_inflight_completed"] is True
    assert node["ordered_reducer"] is True
    assert node["memory_backpressure"] is True
    assert node["numa_affinity_activated"] is False
    assert node["scientific_output_digest"] == "937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613"


def test_parcore1_feas1_no_longer_owns_private_executor() -> None:
    source = Path(feasibility.__file__).read_text(encoding="utf-8")
    assert "ThreadPoolExecutor" not in source
    assert "DeterministicWorkQueue" in source
    assert "backend=parcore1-deterministic-work-queue" in source
    assert "resource_scope=scope" in Path(ROOT / "mdstats/training_data/campaign_cli.py").read_text(encoding="utf-8")


def test_parcore1_public_contract_is_foundation_generic() -> None:
    for name in (
        "DeterministicWorkQueue", "DeterministicWorkItem", "DeterministicWorkCompletion",
        "DeterministicWorkQueueSnapshot", "DeterministicOrderedReducer", "StageResourceScope",
    ):
        assert hasattr(mdstats, name)
    spec = SPEC.read_text(encoding="utf-8")
    assert "MACE-MPA-0 medium" in spec
    assert "MACE-MH-1" in spec
    assert "foundation-specific" in spec


def test_parcore1_benchmark_evidence_is_exact_and_non_regressive() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.226a0"
    assert evidence["active_foundation"]["family"] == "mace-mpa-0"
    assert evidence["active_foundation"]["mh1_supported_by_same_contract"] is True
    assert evidence["workload"]["scientific_output_digest"] == "937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613"
    assert evidence["acceptance"]["exact_output_equality"] is True
    assert evidence["acceptance"]["all_allocated_auto_lanes_observed_active"] is True
    assert evidence["acceptance"]["no_measured_full_budget_throughput_regression"] is True
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "NEIGHBOR1"
    assert MANIFEST.is_file()
