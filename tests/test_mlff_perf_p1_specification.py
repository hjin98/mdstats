from __future__ import annotations

import json
from pathlib import Path

import mdstats


REFERENCE_DIGEST = "4f46dfaa6c366ede1cd4d19cf5fb8be65cfe49067b5aff85d668e0078915f9b8"
SCIENTIFIC_DIGEST = "ff08ca4aee884f1aaf4bf1969454bb75fc9e875eb8c29d57c46fe0100dadb12e"
FPS_DIGEST = "574e356bf8590c11dfac8d404357ab2751825e441dc713fd3d3cc3536a21b748"
NEIGHBOR_DIGEST = "8a6157004024d3c0964e3ca129dd884a555314209f6441d726ec02e0b99781ac"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _evidence() -> dict[str, object]:
    return json.loads(
        (_root() / "audits/analysis/mlff_perf_p1_lta_cloud_cpu_2026-08-15.json").read_text(
            encoding="utf-8"
        )
    )


def test_perf_p1_version_and_normative_documents_are_synchronized() -> None:
    assert mdstats.__version__ == "0.20.185a0"
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(
        encoding="utf-8"
    )
    spec = (
        root / "docs/specs/training_data/mlff_perf_p1_shared_exact_selection_spec.md"
    ).read_text(encoding="utf-8")
    revision = (root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV46.md").read_text(encoding="utf-8")
    release = (root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.180a0.md").read_text(encoding="utf-8")

    assert "PERF-P1 implementation record - 2026-08-15" in manual
    assert "Implementation status (`0.20.180a0`): complete" in manual
    assert "Historical `PERF-P2` remains archived at `0.20.181a0`" in manual
    assert "Release:** `mdstats 0.20.180a0`" in spec
    assert "Next gate:** `PERF-P2`" in spec
    assert "PERF-P1 shared exact selection" in revision
    assert "PERF-P1" in release
    assert "# References" in spec


def test_perf_p1_benchmark_freezes_exactness_and_material_improvement() -> None:
    e = _evidence()
    assert e["schema"] == "mdstats.mlff-perf-p1-benchmark.v1"
    assert e["source_version"] == "0.20.180a0"
    assert e["scientific_digest"] == SCIENTIFIC_DIGEST
    s = e["scientific"]
    assert s["reference_content_digest"] == REFERENCE_DIGEST
    assert s["matrix_exact"] is True
    assert s["fps_order_exact"] is True
    assert s["coverage_report_exact"] is True
    assert s["wide_fps_exact"] is True
    assert s["selected_neighbor_exact"] is True
    assert s["fps_order_digest"] == FPS_DIGEST
    assert s["selected_neighbor_minima_sha256"] == NEIGHBOR_DIGEST

    x = e["execution"]
    assert x["target_frames"] == 37_633
    assert x["target_matrix_shape"] == [37_633, 50]
    assert x["fps"]["p1_summary"]["wall_seconds"]["median"] < x["fps"]["legacy_summary"]["wall_seconds"]["median"]
    assert x["wide_fps"]["p1"]["wall_seconds"] < x["wide_fps"]["legacy"]["wall_seconds"]
    assert x["selected_neighbor"]["p1"]["persistent_bytes"] == 65_536
    assert x["selected_neighbor"]["legacy"]["persistent_bytes"] == 536_870_912
    assert x["selected_neighbor"]["p1"]["rss_peak_mib"] < x["selected_neighbor"]["legacy"]["rss_peak_mib"]
    # Qualification is honest about the measured four-rung regression.
    assert x["coverage"]["p1_summary"]["wall_seconds"]["median"] > x["coverage"]["legacy_summary"]["wall_seconds"]["median"]


def test_perf_p1_dependency_graph_and_release_indexes_are_current() -> None:
    root = _root()
    graph = json.loads(
        (root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text(
            encoding="utf-8"
        )
    )
    nodes = {node["id"]: node for node in graph["nodes"]}
    assert graph["schema_version"] == 34
    assert graph["architecture_revision"] == 52
    assert nodes["PERF_P1_EXACT_SELECTION_WORKSPACE"]["implementation_status"] == "implemented"
    assert nodes["PERF_P1_PROGRESSIVE_COVERAGE_STATE"]["implemented_version"] == "0.20.180a0"
    assert nodes["PERF_P1_DATA7_LINEAR_NEIGHBOR_STATE"]["implemented_version"] == "0.20.180a0"
    assert nodes["PERF_P1_QUALIFICATION_EVIDENCE"]["implementation_status"] == "implemented"
    assert nodes["PERF_P2_LAZY_TARGET_LADDER_V2"]["implementation_status"] == "implemented"
    assert nodes["PERF_P2_LAZY_TARGET_LADDER_V2"]["implemented_version"] == "0.20.181a0"

    changelog = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert changelog.startswith("## 0.20.185a0 - 2026-08-15")
    assert "`mdstats 0.20.180a0` completes bounded **PERF-P1**" in readme


def test_perf_p1_rendered_documents_are_packaged() -> None:
    root = _root()
    for path in (
        root / "docs/arch_manuals/mlff_training_data_architecture.pdf",
        root / "docs/specs/training_data/mlff_perf_p1_shared_exact_selection_spec.pdf",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV46.pdf",
        root / "audits/analysis/mlff_perf_p1_lta_cloud_cpu_2026-08-15.pdf",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.180a0.pdf",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 10_000, path
