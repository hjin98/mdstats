from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "sampling" / "shared_sampling_primitives_spec.md"


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


def test_data1_public_exports_exist() -> None:
    assert callable(mdstats.integrated_autocorrelation_time)
    assert callable(mdstats.assign_balanced_round_robin)
    assert callable(mdstats.build_complete_frame_block_plan)
