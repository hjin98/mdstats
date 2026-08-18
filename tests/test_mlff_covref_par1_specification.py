from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_covref_par1_reference_radius_parallel_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_covref_par1_cloud_cpu_mpa0_2026-08-17.json"


def test_covref_par1_release_docs_are_retained() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate COVREF-PAR1 - TARGET-DATA2B exact CPU parallelization - COMPLETE" in text
    assert "one native cKDTree worker/task" in text
    assert SPEC.is_file()


def test_covref_par1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 96
    node = next(item for item in graph["nodes"] if item["id"] == "COVREF_PAR1_GLOBAL_BLOCK_QUEUE")
    assert node["implementation_status"] == "implemented"
    assert node["implemented_release"] == "0.20.229a0"
    assert node["scientific_authority_change"] is False
    assert node["single_native_tree_worker_per_task"] is True
    assert node["radius_scientific_output_digest"] == "823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d"


def test_covref_par1_frozen_benchmark_evidence() -> None:
    assert EVIDENCE.is_file()
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.229a0"
    assert evidence["architecture_revision"] == 96
    assert evidence["scientific"]["perfbase1_radius_digest"] == "823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d"
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "MVKERNEL1"
    assert evidence["execution"]["supplied_cache"]["new_three_lane_median_seconds"] < evidence["execution"]["supplied_cache"]["old_three_native_median_seconds"]
