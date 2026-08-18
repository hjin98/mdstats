from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_audit_eval_perf1_cpu_kernels_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_audit_eval_perf1_cloud_cpu_mpa0_2026-08-17.json"


def test_audit_eval_perf1_historical_release_evidence_remains_available() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate AUDIT-EVAL-PERF1 - Foundation Audit and EVAL2 CPU hardening - COMPLETE" in text
    assert SPEC.is_file()
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV100.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.233a0.md").is_file()


def test_audit_eval_perf1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 100
    assert graph["schema_version"] >= 80
    assert graph["documentation_gate"] in {"AUDIT_EVAL_PERF1_CPU_KERNELS", "REPLAY_PERF1_INDEX_CACHE", "CAMPAIGN_PERF_QUAL1_CLOSURE", "MVSTATE_REUSE1_SELECTOR_REPAIR_HANDOFF"}
    assert any(item["id"] == "REPLAY_PERF1_INDEX_CACHE" for item in graph["nodes"])
    node = next(item for item in graph["nodes"] if item["id"] == "AUDIT_EVAL_PERF1_CPU_KERNELS")
    assert node["implemented_release"] == "0.20.233a0"
    assert node["implementation_status"] == "implemented_cached_metadata_batched_reducers"
    assert node["scientific_authority_change"] is False
    assert node["model_inference_change"] is False
    assert node["gpu_authority_change"] is False
    assert node["eval2_bootstrap_temporary_target_mib"] == 32
    assert node["foundation_additional_model_inference"] is False


def test_audit_eval_perf1_code_contains_exact_execution_contract() -> None:
    eval2 = (ROOT / "mdstats/training_data/eval2.py").read_text(encoding="utf-8")
    audit = (ROOT / "mdstats/training_data/foundation_audit.py").read_text(encoding="utf-8")
    for token in (
        "_Eval2StaticReductionMetadata",
        "_eval2_static_reduction_metadata",
        "bootstrap_target_temporary_bytes = 32 * 1024**2",
        "memory_bounded_batch",
        "vector = np.empty(int(view.total_atom_count)",
    ):
        assert token in eval2
    for token in (
        "shared_frame_array_index",
        "species_groups_by_frame_data",
        "delta_sq = delta * delta",
        "vector_tail_values = np.quantile",
    ):
        assert token in audit


def test_audit_eval_perf1_frozen_benchmark_evidence_is_consistent() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.233a0"
    assert evidence["architecture_revision"] == 100
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "REPLAY-PERF1"
    assert evidence["active_foundation"]["family"] == "MACE-MPA-0 medium"
    assert evidence["active_foundation"]["checkpoint_sha256"] == (
        "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    )
    assert evidence["active_foundation"]["mh1_compatible"] is True
    scientific = evidence["scientific"]
    assert scientific["eval2_metric_control_exact"] is True
    assert scientific["bootstrap_control_exact"] is True
    assert scientific["foundation_control_exact"] is True
    assert scientific["additional_model_inference"] is False
    assert scientific["foundation_model_provider_calls_control"] == scientific["foundation_model_provider_calls_current"]
    assert evidence["execution"]["eval2_target_reduction"]["speedup"] > 1.5
    assert evidence["execution"]["paired_bootstrap"]["speedup"] > 2.0
    assert evidence["execution"]["foundation_audit"]["speedup"] > 1.0


def test_audit_eval_perf1_history_records_are_present() -> None:
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV100.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.233a0.md").is_file()
    assert "## 0.20.233a0 - 2026-08-17" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.20.233a0" in (ROOT / "docs/history/mlff/release_notes/INDEX.md").read_text(encoding="utf-8")
