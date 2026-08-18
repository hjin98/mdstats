from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "benchmarks/mlff_perfbase1_lta_cloud_cpu_mpa0_2026-08-17.json"
REPORT = ROOT / "benchmarks/mlff_perfbase1_lta_cloud_cpu_mpa0_2026-08-17.md"
MANIFEST = ROOT / "benchmarks/mlff_perfbase1_implementation_manifest_0.20.225a0.json"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"


def test_perfbase1_release_record_and_model_generic_authority_are_frozen():
    record = mdstats.read_perfbase1_record(RECORD)
    assert record.source_version == "0.20.225a0"
    assert record.foundation_family == "mace-mpa-0"
    assert record.foundation_variant == "medium"
    assert record.foundation_model_sha256 == "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"
    assert record.scientific_digest == "d16fdb3a52112192789a27f1515380ec29e8ac278e70b6b0bf669753a77e39df"
    assert record.content_digest == "5b8e1d8315cc103d317fd6bb8948bf8f699ef834873e9d2b1983345536d32ece"
    assert MANIFEST.is_file() and REPORT.is_file()


def test_perfbase1_exact_outputs_are_constant_across_worker_schedules():
    record = mdstats.read_perfbase1_record(RECORD)
    expected = {
        "target_data2b_reference_radii": "823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d",
        "target_data2b_feas1": "937214c70d1f2baae883993082f1ceb25bea6007a5a2be0beee045262f5c0613",
        "target_data2c_mvidx1": "e408bd25dcc9b3c515a76ba2de505ca272d2243e7f9079f65e279694c987597c",
        "target_data2c_mvsel1_kernel": "ca1ba32846ff7e9c0074a1f095f5ba1625e7a632bb96d28994bc0088733ad806",
        "replay_unified_extxyz_ingest": "12100732e5b14450645bff77f4db4ab487450ce06aee247f9aedfa99fdb67372",
    }
    assert {w.workload_id for w in record.workloads} == set(expected)
    for workload in record.workloads:
        assert workload.scientific_output_digest == expected[workload.workload_id]
        assert {trial.scientific_output_digest for trial in workload.trials} == {expected[workload.workload_id]}
        assert {trial.schedule_label for trial in workload.trials} == {"serial", "dual", "intermediate", "auto"}
        assert len(workload.trials) == 8


def test_perfbase1_serial_stages_do_not_fake_parallel_allocation():
    record = mdstats.read_perfbase1_record(RECORD)
    by_id = {workload.workload_id: workload for workload in record.workloads}
    for workload_id in ("target_data2c_mvsel1_kernel", "replay_unified_extxyz_ingest"):
        rows = by_id[workload_id].trials
        assert any(t.requested_workers > 1 for t in rows)
        assert all(t.allocated_workers == 1 for t in rows)
    assert any("MACE runtime unavailable" in item for item in record.unavailable_workloads)


def test_perfbase1_graph_retains_frozen_gate_authority_after_later_gates():
    graph = json.loads(GRAPH.read_text())
    assert graph["architecture_revision"] >= 92
    assert graph["schema_version"] >= 74
    node = next(item for item in graph["nodes"] if item["id"] == "PERFBASE1_CAMPAIGN_BASELINES")
    assert node["implementation_status"] == "implemented"
    assert node["implemented_release"] == "0.20.225a0"
    assert node["measurement_only"] is True
    assert node["foundation_generic_record"] is True
    assert node["runtime_optimization_change"] is False
