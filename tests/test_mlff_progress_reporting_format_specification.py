from __future__ import annotations

import json
from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
SPEC = ROOT / "docs/specs/training_data/mlff_progress_reporting_format_spec.md"




def test_progress_format_spec_freezes_canonical_presentation() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "elapsed=HH:MM:SS",
        "eta=HH:MM:SS",
        "eta=--:--:--",
        "progress=completed/total (percent%)",
        "status=phase; phase=...",
        "presentation state only",
    ):
        assert token in text


def test_progress_format_introduction_history_is_preserved_across_later_architecture_revisions() -> None:
    assert (ROOT / "docs/history/mlff/release_notes/PATCH_NOTES_0.20.237a0.md").is_file()
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV103.md").is_file()
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV105.md").is_file()
    assert (ROOT / "docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV106.md").is_file()


def test_progress_format_qualification_record_is_presentation_only() -> None:
    q = json.loads((ROOT / "release/qualification_logs/MLFF_PROGRESS_FORMAT_QUALIFICATION_0.20.237a0.json").read_text(encoding="utf-8"))
    assert q["release"] == "0.20.237a0"
    assert q["architecture_revision"] == 103
    assert q["dependency_graph_schema"] == 83
    assert q["status"] == "PASS_PRESENTATION_ONLY"
    assert q["scientific_authority_change"] is False
    assert q["runtime_algorithm_change"] is False
    assert q["next_gate"] == "FINAL_GPU1_DEFERRED_RELEASE_QUALIFICATION"
    assert q["tests"]["target_data2_scientific_authority"]["passed"] == 111
