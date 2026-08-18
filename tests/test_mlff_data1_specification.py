from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "sampling" / "shared_sampling_primitives_spec.md"
SPEC_PDF = ROOT / "docs" / "specs" / "sampling" / "shared_sampling_primitives_spec.pdf"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
STAGE_PLAN = ROOT / "docs" / "specs" / "training_data" / "mlff_data_stage_plan_spec.md"
PYPROJECT = ROOT / "pyproject.toml"


def test_data1_spec_names_runtime_and_numerical_contracts() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "MLFF-DATA1",
        "mdstats.sampling",
        "AutocorrelationPolicy",
        "AutocorrelationEstimate",
        "CompleteFrameBlockPlan",
        "BalancedAssignmentPlan",
        "PurgedKFoldPlan",
        "initial-positive-sequence",
        "unbiased autocovariance",
        "No autocorrelation is computed across a gap",
        "Stage 11 serialized values",
        "Flyvbjerg",
        "Geyer",
    ):
        assert token in text


def test_data1_and_data2_status_are_current() -> None:
    architecture = ARCH.read_text(encoding="utf-8")
    stage_plan = STAGE_PLAN.read_text(encoding="utf-8")
    assert "MLFF-DATA1 is implemented in `0.20.29a0`" in architecture
    assert "MLFF-DATA2 is implemented in `0.20.30a0`" in architecture
    assert "MLFF-DATA3 is implemented in `0.20.31a0`" in architecture
    assert "MLFF-DATA4 is implemented in `0.20.32a0`" in architecture
    assert "## MLFF-DATA1 - implemented in 0.20.29a0" in stage_plan
    assert "## MLFF-DATA2 - implemented in 0.20.30a0" in stage_plan
    assert "## MLFF-DATA3 - implemented in 0.20.31a0" in stage_plan


def test_data1_public_exports_and_pdf_exist() -> None:
    assert callable(mdstats.integrated_autocorrelation_time)
    assert callable(mdstats.assign_balanced_round_robin)
    assert callable(mdstats.build_complete_frame_block_plan)
    assert SPEC_PDF.stat().st_size > 5_000
    assert 'version = "0.20.140a0"' in PYPROJECT.read_text(encoding="utf-8")
