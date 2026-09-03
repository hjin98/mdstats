from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_vram1_perf_p4_release_authorities_are_synchronized() -> None:
    root = _root()
    assert mdstats.MACE_BATCH_CAPACITY_CALIBRATION_SCHEMA == "mdstats.mace-batch-capacity-calibration.v2"
    assert mdstats.MACE_BATCH_CAPACITY_PROBE_SCHEMA == "mdstats.mace-batch-capacity-probe.v1"
    assert mdstats.DATA6_MODEL_SWEEP_EXECUTION_POLICY_SCHEMA == "mdstats.data6-model-sweep-execution-policy.v4"
    assert mdstats.DATA6_RUNTIME_BATCH_CAP_SCHEMA == "mdstats.data6-runtime-batch-cap.v1"

    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    node = nodes["VRAM1_PERF_P4_MEMORY_PIPELINE"]
    assert node["implementation_status"] == "implemented_cpu_control_plane_deferred_final_gpu_qualification"
    assert node["implemented_version"] == "0.20.186a0"
    assert node["next_implementation_gate"] == "PERF_P5"
    assert node["gpu_qualification_schedule"] == "FINAL_GPU1"


def test_vram1_perf_p4_manual_spec_and_final_gpu_contract_are_current() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_vram1_perf_p4_memory_pipeline_spec.md").read_text()
    final_gpu = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    readme = (root / "README.md").read_text()
    changelog = (root / "CHANGELOG.md").read_text()
    example = (root / "campaign.toml.example").read_text()

    assert "revision 59" in manual
    assert "MaceBatchCapacityCalibration.v2" in manual
    assert "prediction bytes per structure" in manual.lower()
    assert "PERF-P5" in manual and "FINAL-GPU1" in manual
    assert "workload-correct" in spec.lower()
    assert "combined_evaluate" in spec
    assert "Data6RuntimeBatchCap.v1" in spec
    assert "4.72% slower" in spec
    assert "VRAM1 + PERF-P4" in final_gpu
    assert "E3NN-BASELINE" in final_gpu
    assert "VRAM1 + PERF-P4 in 0.20.186a0" in readme
    assert changelog.startswith("## 0.20.209a0 - 2026-08-16")
    for token in (
        "batch_calibration_stress_structures = 8",
        "vram_max_device_fraction = 0.80",
        "vram_reserve_gib = 4.0",
        "batch_throughput_tolerance_fraction = 0.05",
        "pipeline_enabled = true",
        "persistence_queue_depth = 1",
    ):
        assert token in example


def test_vram1_perf_p4_markdown_sources_exist_before_pdf_render() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_vram1_perf_p4_memory_pipeline_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV53.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.186a0.md",
        root / "benchmarks/mlff_vram1_perf_p4_cloud_cpu_2026-08-15.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 1_000, path
