from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_cueq_phase2_manual_graph_spec_release_and_final_gpu_handoff_are_synchronized() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_cueq_phase2_selected_head_source_qualification_spec.md").read_text()
    final_gpu = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}

    assert tuple(int(v) for v in mdstats.__version__.split("a",1)[0].split(".")) >= (0, 20, 209)
    for exported in (
        "CUEQ_PHASE2_POLICY_SCHEMA", "CUEQ_PHASE2_CORPUS_SCHEMA", "CUEQ_PHASE2_DATA6_PARITY_SCHEMA",
        "CUEQ_PHASE2_ASSESSMENT_SCHEMA", "CUEQ_PHASE2_QUALIFICATION_SCHEMA", "CUEQ_PHASE2_VERSION",
        "CueqPhase2Policy", "CueqPhase2DevelopmentCorpus", "CueqPhase2Data6ParityRecord",
        "CueqPhase2PathAssessment", "CueqPhase2QualificationRecord", "build_cueq_phase2_qualification",
        "cueq_phase2_execution_realization_digest",
    ):
        assert exported in mdstats.__all__
    assert "revision 59" in manual
    assert "CUEQ-PHASE2 implementation record - 2026-08-15" in manual
    assert "CueqPhase2QualificationRecord.v1" in manual
    assert "Implementation release:** `mdstats 0.20.190a0`" in spec
    assert "CUEQ-PHASE2 final source/DATA6 obligation" in final_gpu
    assert "preflight.2026-08.v6" in final_gpu
    assert graph["architecture_revision"] >= 76
    assert graph["schema_version"] >= 58

    node = nodes["CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL"]
    assert node["implemented_version"] == "0.20.190a0"
    assert node["qualification_schema"] == mdstats.CUEQ_PHASE2_QUALIFICATION_SCHEMA
    assert node["reference_source_kernel_mode"] == "e3nn"
    assert node["candidate_source_kernel_mode"] == "cueq_pure"
    assert node["locked_source_checkpoint_sha256"] == mdstats.CUEQ_PHASE2_MH1_SHA256
    assert node["locked_selected_head_checkpoint_sha256"] == mdstats.CUEQ_PHASE2_SELECTED_HEAD_SHA256
    assert node["original_six_head_cueq_execution_authorized"] is False
    assert node["generated_default_change_authorized"] is False

    final = nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]
    assert final["preflight_schema"].startswith("mdstats.mlff-final-gpu1.preflight.2026-08.v")
    assert final["cueq_phase2_qualification_schema"] == mdstats.CUEQ_PHASE2_QUALIFICATION_SCHEMA


def test_cueq_phase2_sources_and_tool_exist() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_cueq_phase2_selected_head_source_qualification_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV57.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.190a0.md",
        root / "tools/qualify_mlff_cueq_phase2.py",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 500, path
