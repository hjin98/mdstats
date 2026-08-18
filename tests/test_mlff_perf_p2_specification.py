from __future__ import annotations

import json
from pathlib import Path

import mdstats


SCIENTIFIC_DIGEST = "ae55c560995791174ac63e2d894ec685d74a02c389eb0a955d87e77cfd9f18f9"
EARLY_SIGNATURE = "1b91c9790753ccef5de367609ed4a452af6632c5d112a4f84bc922b329a4c261"
EARLY_V2_PLAN = "af29ca65e44741e7e5b49b5da16cbe1a37b8b761b9e3f51be81641e6f75f7db9"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _evidence() -> dict[str, object]:
    return json.loads((_root() / "audits/analysis/mlff_perf_p2_lta_cloud_cpu_2026-08-15.json").read_text())


def test_perf_p2_release_manual_spec_and_graph_are_synchronized() -> None:
    root = _root()
    assert mdstats.__version__ == "0.20.185a0"
    assert mdstats.TARGET_DATA_LADDER_VERSION == "mdstats.target-data2c.ladder.2026-08.v3"
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_perf_p2_lazy_target_ladder_spec.md").read_text()
    revision = (root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV47.md").read_text()
    release = (root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.181a0.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {node["id"]: node for node in graph["nodes"]}

    assert "Historical gate PERF-P2" in manual
    assert "superseded for generated campaigns" in manual
    assert "PERF-P2R" in manual
    assert "Release:** `mdstats 0.20.181a0`" in spec
    assert "historical and superseded for generated campaigns" in spec
    assert "PERF-P2 lazy TARGET-DATA2C authority v2" in revision
    assert "PERF-P2" in release
    assert graph["schema_version"] == 34
    assert graph["architecture_revision"] == 52
    assert nodes["PERF_P2_LAZY_TARGET_LADDER_V2"]["implementation_status"] == "implemented"
    assert nodes["PERF_P2_LAZY_TARGET_LADDER_V2"]["implemented_version"] == "0.20.181a0"
    assert nodes["PERF_P2_QUALIFICATION_EVIDENCE"]["implementation_status"] == "implemented"
    assert nodes["PERF_P2_LAZY_TARGET_LADDER_V2"]["current_status"] == "historical_superseded"
    assert nodes["SIZE_HALVE1_TARGET_SIZE_CORRECTION"]["implemented_version"] == "0.20.182a0"
    assert nodes["PERF_P2R_SUCCESSIVE_FIDELITY_EXECUTION"]["implementation_status"] == "implemented_cpu_control_plane_deferred_final_gpu_qualification"
    assert nodes["PERF_P3_CPU_STRUCTURAL_REDUCTION"]["implementation_status"] == "implemented_cpu_qualified"


def test_perf_p2_benchmark_freezes_decision_equivalence_and_early_stop_gain() -> None:
    evidence = _evidence()
    assert evidence["schema"] == "mdstats.mlff-perf-p2-benchmark.v1"
    assert evidence["source_version"] == "0.20.181a0"
    assert evidence["scientific_digest"] == SCIENTIFIC_DIGEST
    assert evidence["execution"]["repeats"] == 3
    assert evidence["scientific"]["worker_invariance"]["exact"] is True

    early = evidence["scientific"]["cases"]["early_stop"]
    assert early["equivalence"]["stage_a_survivor_sizes_exact"] is True
    assert early["equivalence"]["survivor_evidence_exact"] is True
    assert early["equivalence"]["v2_signature_digest"] == EARLY_SIGNATURE
    assert early["v2_structure"]["content_digest"] == EARLY_V2_PLAN
    assert early["v2_structure"]["materialized_target_sizes"] == [128, 256, 512, 1024]
    assert early["v2_structure"]["intentionally_unmaterialized_target_sizes"] == [2048, 4096, 8192]

    fallback = evidence["scientific"]["cases"]["fallback"]
    assert fallback["equivalence"]["stage_a_survivor_sizes_exact"] is True
    assert fallback["equivalence"]["survivor_evidence_exact"] is True
    assert fallback["v2_structure"]["materialized_target_sizes"] == [128, 256, 512, 1024, 2048, 4096, 8192]

    x = evidence["execution"]["cases"]["early_stop"]
    assert x["v2_summary"]["wall_seconds"]["max"] < x["v1_summary"]["wall_seconds"]["min"]
    assert x["v2_summary"]["wall_seconds"]["median"] < 0.25 * x["v1_summary"]["wall_seconds"]["median"]
    assert early["v2_structure"]["serialized_json_bytes"] < 0.15 * early["v1_structure"]["serialized_json_bytes"]
