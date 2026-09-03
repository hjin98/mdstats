from __future__ import annotations

import json
from pathlib import Path

import mdstats


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_perf_cert1_manual_graph_spec_release_and_final_gpu_handoff_are_synchronized() -> None:
    root = _root()
    manual = (root / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    spec = (root / "docs/specs/training_data/mlff_perf_cert1_end_to_end_certification_spec.md").read_text()
    final_gpu = (root / "docs/specs/training_data/mlff_final_gpu1_deferred_qualification_spec.md").read_text()
    graph = json.loads((root / "docs/arch_manuals/mlff_training_data_dependency_graph.json").read_text())
    nodes = {item["id"]: item for item in graph["nodes"]}
    edges = graph["edges"]

    for exported in (
        "PERF_CERT1_POLICY_SCHEMA", "PERF_CERT1_TELEMETRY_SCHEMA", "PERF_CERT1_PROFILE_SCHEMA",
        "PERF_CERT1_UPSTREAM_SCHEMA", "PERF_CERT1_ASSESSMENT_SCHEMA", "PERF_CERT1_QUALIFICATION_SCHEMA",
        "PERF_CERT1_VERSION", "PerfCert1Policy", "PerfCert1Telemetry", "PerfCert1ProfileRecord",
        "PerfCert1UpstreamAuthority", "PerfCert1ProfileAssessment", "PerfCert1QualificationRecord",
        "build_perf_cert1_qualification",
    ):
        assert exported in mdstats.__all__

    assert "revision 59" in manual
    assert "PERF-CERT1 implementation record - 2026-08-15" in manual
    assert "PerfCert1QualificationRecord.v1" in manual
    assert "Implementation release:** `mdstats 0.20.191a0`" in spec
    assert "Different final checkpoint bytes are allowed" in spec
    assert "CUEQ-PHASE2 remains optional" in spec
    assert "generated_default_change_authorized=false" in spec
    assert "PERF-CERT1 final end-to-end obligation" in final_gpu
    assert "preflight.2026-08.v6" in final_gpu
    assert graph["architecture_revision"] == 76
    assert graph["schema_version"] == 58

    node = nodes["PERF_CERT1_END_TO_END_CERTIFICATION"]
    assert node["implemented_version"] == "0.20.191a0"
    assert node["qualification_schema"] == mdstats.PERF_CERT1_QUALIFICATION_SCHEMA
    assert node["cueq_phase2_optional"] is True
    assert node["strict_positive_speedup_required"] is True
    assert node["generated_default_change_authorized"] is False

    assert {"from": "CUEQ_PHASE1_TRAINING_ONLY_QUALIFICATION", "to": "PERF_CERT1_END_TO_END_CERTIFICATION", "type": "release_qualification_requires"} in edges
    assert {"from": "CUEQ_PHASE2_SELECTED_HEAD_SOURCE_EXECUTION_OPTIONAL", "to": "PERF_CERT1_END_TO_END_CERTIFICATION", "type": "optional_enrichment"} in edges
    assert {"from": "PERF_P5_TRAIN_EVAL_PERSISTENCE_REUSE", "to": "PERF_CERT1_END_TO_END_CERTIFICATION", "type": "release_qualification_requires"} in edges

    final = nodes["FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"]
    assert final["implemented_version"] == "0.20.192a0"
    assert final["preflight_schema"] == "mdstats.mlff-final-gpu1.preflight.2026-08.v6"
    assert final["perf_cert1_qualification_schema"] == mdstats.PERF_CERT1_QUALIFICATION_SCHEMA


def test_perf_cert1_sources_and_tool_exist() -> None:
    root = _root()
    for path in (
        root / "docs/specs/training_data/mlff_perf_cert1_end_to_end_certification_spec.md",
        root / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV58.md",
        root / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.191a0.md",
        root / "tools/qualify_mlff_perf_cert1.py",
    ):
        assert path.is_file(), path
        assert path.stat().st_size > 500, path
