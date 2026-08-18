from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_mvqual_par1_global_scoring_queue_spec.md"
EVIDENCE = ROOT / "benchmarks/mlff_mvqual_par1_cloud_cpu_mpa0_2026-08-17.json"


def test_mvqual_par1_historical_release_and_current_manual_retain_gate_contract() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "Gate MVQUAL-PAR1 - global same-N scoring queue - COMPLETE" in text
    assert SPEC.is_file()
    assert "Implemented in mdstats 0.20.232a0 / MLFF architecture revision 99" in SPEC.read_text(encoding="utf-8")


def test_mvqual_par1_dependency_graph_is_closed() -> None:
    graph = json.loads(GRAPH.read_text(encoding="utf-8"))
    assert graph["architecture_revision"] >= 99
    assert graph["schema_version"] >= 79
    node = next(item for item in graph["nodes"] if item["id"] == "MVQUAL_PAR1_GLOBAL_SCORING_QUEUE")
    assert node["implemented_release"] == "0.20.232a0"
    assert node["implementation_status"] == "implemented_global_same_n_scoring_queue"
    assert node["parallel_granularity"] == "domain_selector_target_size_score"
    assert node["native_tree_workers_per_task"] == 1
    assert node["blas_threads_per_task"] == 1
    assert node["automatic_worker_ceiling"] == 4
    assert node["scientific_authority_change"] is False


def test_mvqual_par1_code_contains_exact_execution_contract() -> None:
    qualification = (ROOT / "mdstats/training_data/target_multi_view_qualification.py").read_text(encoding="utf-8")
    campaign = (ROOT / "mdstats/training_data/campaign_cli.py").read_text(encoding="utf-8")
    for token in (
        "_mvqual_score_job",
        "_estimate_mvqual_score_memory_bytes",
        "DeterministicWorkQueue",
        "scoring_workers",
        "manage_resource_scope=resource_scope is not None",
        "execution_telemetry_callback",
    ):
        assert token in qualification
    assert "target_multi_view_qualification_workers" in campaign
    assert "TARGET-DATA2C-MVQUAL-PAR1" in campaign
    assert "min(budget, available, 4)" in campaign


def test_mvqual_par1_history_records_are_present() -> None:
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV99.md").is_file()
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.232a0.md").is_file()
    assert "## 0.20.232a0" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "0.20.232a0" in (ROOT / "docs/history/mlff/release_notes/INDEX.md").read_text(encoding="utf-8")


def test_mvqual_par1_frozen_benchmark_evidence_is_consistent() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert evidence["release"] == "0.20.232a0"
    assert evidence["architecture_revision"] == 99
    assert evidence["acceptance"]["status"] == "PASS"
    assert evidence["acceptance"]["next_gate"] == "AUDIT-EVAL-PERF1"
    assert evidence["active_foundation"]["family"] == "MACE-MPA-0 medium"
    assert evidence["active_foundation"]["checkpoint_sha256"] == (
        "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    )
    assert evidence["active_foundation"]["mh1_compatible"] is True
    scientific = evidence["scientific"]
    assert scientific["qualification_plan_digest"] == (
        "2ebd7f5dc2b560e3150fe4849e7098be2eff56469779f15b2befda74059fc90b"
    )
    assert scientific["control_current_plan_exact"] is True
    assert scientific["worker_count_plan_exact"] is True
    paired = evidence["execution"]["paired_four_lane"]
    scaling = evidence["execution"]["current_scaling"]
    assert paired["speedup"] > 1.5
    assert scaling["one_to_two_speedup"] > 1.3
    assert scaling["automatic_worker_ceiling"] == 4
    assert scaling["4_lanes"]["max_busy_workers"] == 4
    assert evidence["execution"]["queue_probe"]["jobs_finished"] == 12
