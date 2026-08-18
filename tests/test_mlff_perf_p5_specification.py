from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_perf_p5_release_manual_graph_and_spec_are_synchronized() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_perf_p5_train_eval_persistence_spec.md").read_text()
    final_gpu = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}

    assert mdstats.__version__ == "0.20.209a0"
    assert "revision 59" in manual
    assert "PERF-P5 CPU/control-plane qualification passes" in manual
    assert "46.05% reduction" in manual
    assert "40.82% reduction" in manual
    assert "not promoted" in manual
    assert "Release:** `mdstats 0.20.187a0`" in spec
    assert "buffer protocol" in spec
    assert "train2_persistence.jsonl" in spec
    assert "6.49% slower" in spec
    assert "HDF5 and LMDB" in spec
    assert "PERF-P5 final-GPU obligations" in final_gpu
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58
    node = nodes["PERF_P5_TRAIN_EVAL_PERSISTENCE_REUSE"]
    assert node["implemented_version"] == "0.20.187a0"
    assert node["authority_class"] == "E"
    assert node["gpu_qualification_schedule"] == "FINAL_GPU1"
    assert "PERF_P5_ACCELERATOR_PERSISTENCE_REUSE" in nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]["deferred_gpu_gates"]


def test_perf_p5_markdown_sources_precede_rendered_artifacts() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_perf_p5_train_eval_persistence_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV54.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.187a0.md",
        root / "benchmarks/mlff_perf_p5_cloud_cpu_2026-08-15.md",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 1_000, path
