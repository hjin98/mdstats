from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_cueq_dep1_manual_graph_spec_and_release_are_synchronized() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_cueq_dep1_runtime_freeze_spec.md").read_text()
    final_gpu = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}

    assert tuple(int(v) for v in mdstats.__version__.split("a",1)[0].split(".")) >= (0, 20, 209)
    assert "revision 55" in manual
    assert "Gate CUEQ-DEP1" in manual
    assert "cuequivariance_ops_torch" in manual
    assert "Implementation release:** `mdstats 0.20.188a0`" in spec
    assert "CUEQ-DEP1 final-runtime obligation" in final_gpu
    assert "preflight.2026-08.v6" in final_gpu
    assert graph["architecture_revision"] >= 76
    assert graph["schema_version"] >= 58
    node = nodes["CUEQ_DEP1_RUNTIME_FREEZE"]
    assert node["implemented_version"] == "0.20.188a0"
    assert node["runtime_schema"] == mdstats.CUEQ_DEP1_RUNTIME_SCHEMA
    assert node["training_kernel_mode"] == "cueq_pure"
    assert node["source_inference_kernel_mode"] == "e3nn"
    assert "cuequivariance-ops-torch-cu13" in node["ops_distribution_candidates"]
    final = nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]
    assert final["preflight_schema"].startswith("mdstats.mlff-final-gpu1.preflight.2026-08.v")
    assert "CUEQ_DEP1_RUNTIME_FREEZE" in final["deferred_gpu_gates"]


def test_cueq_dep1_markdown_sources_and_tools_exist() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_cueq_dep1_runtime_freeze_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV55.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.188a0.md",
        root / "tools/capture_mlff_cueq_dep1_runtime.py",
        root / "tools/run_mlff_final_gpu_qualification.py",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 500, path
