from __future__ import annotations

import json
from pathlib import Path

import mdstats
import mdstats.training_data.target_coverage_sparse_index as mvidx

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
SPEC = ROOT / "docs/specs/training_data/mlff_neighbor1_exact_neighborhood_spec.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
REV = ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV94.md"
PATCH = ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.227a0.md"
EVIDENCE = ROOT / "benchmarks/mlff_neighbor1_feas_mvidx_cloud_cpu_mpa0_2026-08-17.json"


def test_neighbor1_release_manual_and_spec_are_current() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate NEIGHBOR1 - shared FEAS1/MVIDX exact-neighborhood engine - COMPLETE" in text
    assert "MVIDX-REUSE1" in text
    assert SPEC.is_file() and REV.is_file() and PATCH.is_file() and EVIDENCE.is_file()


def test_neighbor1_dependency_graph_closes_gate_and_advances_sparse_transpose() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 94
    assert graph["schema_version"] >= 76
    assert graph["documentation_gate"] in {node["id"] for node in graph["nodes"]}
    assert "MVIDX_REUSE1_SPARSE_TRANSPOSE" in {node["id"] for node in graph["nodes"]}
    node = next(item for item in graph["nodes"] if item["id"] == "NEIGHBOR1_SHARED_EXACT_ENGINE")
    assert node["implementation_status"] == "implemented"
    assert node["implemented_release"] == "0.20.227a0"
    assert node["scientific_authority_change"] is False
    assert node["runtime_optimization_change"] is True
    assert node["mvidx_second_geometry_sweep_on_cache_hit"] is False
    assert node["native_array_persistence"] is True
    assert node["final_csr_ram_admitted_before_materialization"] is True
    assert node["feas1_scientific_output_digest"] == "937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613"
    assert node["mvidx_scientific_output_digest"] == "e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c"


def test_neighbor1_mvidx_source_has_no_private_geometry_implementation() -> None:
    source = Path(mvidx.__file__).read_text(encoding="utf-8")
    assert "cKDTree" not in source
    assert "query_ball_point" not in source
    assert "build_target_coverage_exact_neighborhood_store" in source
    assert "exact_neighborhood_store" in source


def test_neighbor1_public_contract_is_foundation_generic() -> None:
    for name in (
        "ExactNeighborhoodEngine",
        "TargetCoverageExactNeighborhoodStore",
        "build_target_coverage_feasibility_artifacts",
        "build_target_coverage_exact_neighborhood_store",
        "write_target_coverage_exact_neighborhood_native_record",
        "read_target_coverage_exact_neighborhood_native_record",
    ):
        assert hasattr(mdstats, name)
    spec = SPEC.read_text(encoding="utf-8")
    assert "MACE-MPA-0 medium" in spec
    assert "MACE-MH-1" in spec
    assert "foundation-model-specific" in spec


def test_neighbor1_benchmark_evidence_is_exact_and_materially_faster() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.227a0"
    assert evidence["active_foundation"]["family"] == "mace-mpa-0"
    assert evidence["active_foundation"]["mh1_supported_by_same_contract"] is True
    assert evidence["workload"]["feas1_digest"] == "937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613"
    assert evidence["workload"]["neighbor1_digest"] == "0220c89084fe957e85eb1e1c87a581eaa44869f11cb98bee7f7bd8cdafd3d74e"
    assert evidence["workload"]["mvidx1_digest"] == "e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c"
    acceptance = evidence["acceptance"]
    assert acceptance["exact_feas1_digest_preserved"] is True
    assert acceptance["exact_mvidx1_digest_preserved"] is True
    assert acceptance["neighbor_store_digest_invariant"] is True
    assert acceptance["final_csr_memory_admitted_before_materialization"] is True
    assert acceptance["three_lane_end_to_end_speedup"] > 1.5
    assert acceptance["status"] == "PASS"
    assert acceptance["next_gate"] == "MVIDX-REUSE1"
