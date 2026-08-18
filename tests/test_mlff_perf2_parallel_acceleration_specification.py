from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_perf2_release_and_configuration_contract() -> None:
    assert mdstats.__version__ == "0.20.180a0"
    assert campaign_cli.MLFF_DATA9B3_VERSION == "0.20.99a0"
    template = campaign_cli._config_template(
        workspace="workspace",
        training_root="training",
        foundation_model="model",
        replay_train="train.extxyz",
        replay_monitor="monitor.extxyz",
    )
    for text in (
        "cpu_fraction = 0.90",
        "ram_fraction = 0.80",
        "gpu_memory_fraction = 0.90",
        "source_workers = 0",
        "feature_workers = 0",
        "lta_workers = 0",
        "inference_batch_size = 0",
        "num_workers = 0",
        "parallel_inference_jobs = 0",
        "maximum_parallel_inference_jobs = 0",
        "inference_cpu_utilization_fraction = 0.90",
        "inference_gpu_memory_fraction = 0.90",
        "inference_gpu_utilization_fraction = 0.90",
    ):
        assert text in template


def test_perf2_dependency_graph_contract() -> None:
    graph = json.loads(
        (ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json")
        .read_text(encoding="utf-8")
    )
    assert graph["schema_version"] == 26
    assert graph["architecture_revision"] == 45
    nodes = {item["id"] for item in graph["nodes"]}
    assert {
        "SYSTEM_RESOURCE_SNAPSHOT",
        "CPU_RAM_PARALLEL_EXECUTION_PLAN",
        "GPU_VRAM_BATCH_EXECUTION_PLAN",
        "ISOLATED_TRAJECTORY_WORKER",
        "MACE_DATALOADER_WORKER_PLAN",
        "NATIVE_MACE_GRAPH_BATCH",
        "ADAPTIVE_INFERENCE_CONCURRENCY_PLAN",
        "CPU_INFERENCE_TELEMETRY",
        "GPU_INFERENCE_TELEMETRY",
        "PARALLEL_CHECKPOINT_EVALUATION",
        "PARALLEL_NVE_VERIFICATION",
    } <= nodes
    edges = {(item["from"], item["to"], item["type"]) for item in graph["edges"]}
    assert (
        "SYSTEM_RESOURCE_SNAPSHOT",
        "CPU_RAM_PARALLEL_EXECUTION_PLAN",
        "execution_requires",
    ) in edges
    assert (
        "GPU_VRAM_BATCH_EXECUTION_PLAN",
        "NATIVE_MACE_GRAPH_BATCH",
        "execution_requires",
    ) in edges
    assert (
        "MACE_DATALOADER_WORKER_PLAN",
        "MACE_CONFIG_REALIZATION_RECORD",
        "execution_requires",
    ) in edges
    assert (
        "ADAPTIVE_INFERENCE_CONCURRENCY_PLAN",
        "PARALLEL_CHECKPOINT_EVALUATION",
        "execution_requires",
    ) in edges
    assert (
        "ADAPTIVE_INFERENCE_CONCURRENCY_PLAN",
        "PARALLEL_NVE_VERIFICATION",
        "execution_requires",
    ) in edges
