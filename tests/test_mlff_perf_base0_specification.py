from __future__ import annotations

import json
from pathlib import Path

import mdstats
from mdstats.training_data.performance_baseline import read_perf_base0_record


SCIENTIFIC_DIGEST = "44a5aa8b492cece8d303f83a163ddbeee6d3a340932d4716c53b4ddf28a81e3c"
PRIMARY_EXECUTION_DIGEST = "2c7614fea8dc60594e176e7c4fa17413922c56d67982e881a8fab0eebbc5b18c"
RERUN_EXECUTION_DIGEST = "0d3649ed0dfdb92e3daddb8a7d9a5361b591e0f1e1069156a602afb019fec564"
COMPARISON_DIGEST = "c3d31a3922c89d19cc9a5670b9b4ca8f7ffaa65f82cffa8c16a25c0fb50d5e9e"


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def test_perf_base0_is_public_versioned_and_documented() -> None:
    assert mdstats.PERF_BASE0_VERSION == "mdstats.mlff-perf-base0.2026-08.v1"
    for name in (
        "PerfBase0ArrayReference",
        "PerfBase0JsonReference",
        "PerfBase0ArtifactIdentity",
        "PerfBase0CorpusIdentity",
        "PerfBase0ScientificStage",
        "PerfBase0ExecutionTelemetry",
        "PerfBase0Record",
        "PerfBase0Comparison",
        "PerfBase0StageMeter",
        "compare_perf_base0_records",
        "assert_perf_base0_scientific_equivalence",
        "write_perf_base0_record",
        "read_perf_base0_record",
        "render_perf_base0_markdown",
    ):
        assert hasattr(mdstats, name)

    manual = (_root() / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(
        encoding="utf-8"
    )
    assert "PERF-BASE0 implementation record - 2026-08-15" in manual
    assert "Implementation status (`0.20.178a0`): complete as bounded supplied-data authority" in manual
    assert "37,633 frames" in manual
    assert "PERF-P0 implementation record - 2026-08-15" in manual
    assert "PERF-P1 implementation record - 2026-08-15" in manual
    assert "**VRAM1 + PERF-P4** is the next implementation gate" in manual


def test_perf_base0_primary_and_rerun_freeze_exact_scientific_authority() -> None:
    root = _root()
    primary = read_perf_base0_record(
        root / "audits/analysis/mlff_perf_base0_lta_cloud_cpu_reference.json"
    )
    rerun = read_perf_base0_record(
        root / "benchmarks/mlff_perf_base0_lta_cloud_cpu_repro_run2_2026-08-15.json"
    )

    assert primary.authority_status == "bounded"
    assert rerun.authority_status == "bounded"
    assert primary.scientific_digest == SCIENTIFIC_DIGEST
    assert rerun.scientific_digest == SCIENTIFIC_DIGEST
    assert primary.execution_digest == PRIMARY_EXECUTION_DIGEST
    assert rerun.execution_digest == RERUN_EXECUTION_DIGEST

    corpora = {corpus.corpus_id: corpus for corpus in primary.corpora}
    assert corpora["lta_target_complete"].frame_count == 37_633
    assert corpora["lta_target_complete"].atom_count == 6_322_344
    assert corpora["lta_target_complete"].source_unit_count == 27
    assert corpora["lta_replay_authoritative_splits"].frame_count == 12_000
    assert corpora["lta_replay_authoritative_splits"].atom_count == 364_370

    stage_ids = {stage.stage_id for stage in primary.scientific_stages}
    assert {
        "input_identity",
        "training_ingest",
        "replay_ingest",
        "compact_regression",
        "adversarial_geometry_statistics",
        "target_data2b_exact_radii",
        "target_data2c_exact_fps",
    } <= stage_ids
    assert any("MACE-MH-1 checkpoint" in item for item in primary.limitations)


def test_perf_base0_comparison_authenticates_same_host_reproducibility() -> None:
    path = _root() / "audits/analysis/mlff_perf_base0_reproducibility_comparison.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == "mdstats.perf-base0-comparison.v1"
    assert payload["scientific_match"] is True
    assert payload["mismatches"] == []
    assert payload["reference_scientific_digest"] == SCIENTIFIC_DIGEST
    assert payload["candidate_scientific_digest"] == SCIENTIFIC_DIGEST
    assert payload["content_digest"] == COMPARISON_DIGEST
    assert set(payload["performance"]) == {
        "input_identity",
        "training_ingest",
        "replay_ingest",
        "compact_regression",
        "adversarial_geometry_statistics",
        "target_data2b_exact_radii",
        "target_data2c_exact_fps",
    }


def test_perf_base0_release_notes_freeze_scope_and_next_gate() -> None:
    text = (_root() / "release/PATCH_NOTES_0.20.178a0.md").read_text(encoding="utf-8")
    assert "Complete target corpus: 27 VASP XML files, 37,633 frames" in text
    assert SCIENTIFIC_DIGEST in text
    assert PRIMARY_EXECUTION_DIGEST in text
    assert RERUN_EXECUTION_DIGEST in text
    assert COMPARISON_DIGEST in text
    assert "No MACE-MH-1 checkpoint or GPU was supplied" in text
    assert "`PERF-P0` is the next gate" in text
