from __future__ import annotations

from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"
SPEC = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.md"
SPEC_PDF = ROOT / "docs/specs/training_data/mlff_data_stage_plan_spec.pdf"
PYPROJECT = ROOT / "pyproject.toml"


def test_current_architecture_manual_describes_current_authorities() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    assert 'status: "proposed D3 renewal candidate pending independent review"' in text
    for token in (
        "one complete TargetTrainingOrder",
        "optional target-size diagnostic screen/reducer",
        "operator-owned provisional design",
        "cross-validate admission",
        "fresh final production and publication decision",
        "authenticated reconstructible build state",
    ):
        assert token in text
    assert "SIZE_STUDY_EPOCH3" not in text


def test_current_cross_cutting_spec_separates_compatibility_and_execution_identity() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "Cross-cutting current-generation invariants",
        "Execution caches, worker scheduling, out-of-core layout",
        "Retired derived target-size state is rejected before reuse rather than translated",
        "current-generation identities",
        "fail-closed current-generation publication",
    ):
        assert token in text
    assert "No public runtime object is implemented at MLFF-DATA0" not in text






def test_current_architecture_publication_and_version_artifacts_exist() -> None:
    # The current D3 manual is a source candidate pending independent review;
    # the historical PDF remains under its snapshot owner.  The current source
    # and the published cross-cutting spec PDF are the canonical artifacts here.
    assert MANUAL.stat().st_size > 10_000
    assert SPEC_PDF.stat().st_size > 5_000
    assert f'version = "{mdstats.__version__}"' in PYPROJECT.read_text(encoding="utf-8")
