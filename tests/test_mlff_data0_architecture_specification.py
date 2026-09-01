from __future__ import annotations

import json
from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
MANUAL_PDF = ROOT / "docs/arch_manuals/mlff_training_data_architecture.pdf"
GRAPH = ROOT / "docs/arch_manuals/mlff_training_data_dependency_graph.json"
SPEC = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
SPEC_PDF = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.pdf"
PYPROJECT = ROOT / "pyproject.toml"


def test_current_architecture_manual_describes_revision_107_authorities() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert "architecture_revision: 107" in text
    for token in (
        "one canonical training order pi_train",
        "paired optimizer-seed screen over candidate sizes",
        "post-selection cross-validation on exactly T_selected",
        "fresh final production",
        "reconstructible execution cache",
    ):
        assert token in text
    assert "SIZE_STUDY_EPOCH3" not in text


def test_current_cross_cutting_spec_separates_compatibility_and_execution_identity() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Cross-cutting current-generation invariants",
        "Execution caches, worker scheduling, out-of-core layout",
        "Retired derived target-size state is detected before any semantic deserialization",
        "current-generation identities",
        "fail closed",
    ):
        assert token in text
    assert "No public runtime object is implemented at MLFF-DATA0" not in text






def test_current_architecture_publication_and_version_artifacts_exist() -> None:
    assert MANUAL_PDF.stat().st_size > 10_000
    assert SPEC_PDF.stat().st_size > 5_000
    assert f'version = "{mdstats.__version__}"' in PYPROJECT.read_text(encoding="utf-8")
