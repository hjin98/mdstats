from __future__ import annotations

from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_adaptive_verification_spec.md"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_adapt_verify1_release_identity_and_specification() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    text = SPEC.read_text(encoding="utf-8")
    assert "Status: implemented in `mdstats 0.20.127a0`." in text
    assert "fallback_to_next_full_evaluation_candidate = true" in text
    assert "single -> FP32" in text
    assert "double -> FP64" in text
    assert "scientific_analysis_dtype" in text
    assert "atomically promotes the exact passing bytes" in text
    assert "does not fabricate a" in text and "legacy committee around a fold winner" in text


def test_adapt_verify1_generated_config_and_architecture_are_closed() -> None:
    source = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    example = (ROOT / "campaign.toml.example").read_text(encoding="utf-8")
    assert "fallback_to_next_full_evaluation_candidate = true" in source
    assert "fallback_to_next_full_evaluation_candidate = true" in example
    verify = ARCH.read_text(encoding="utf-8")
    section = verify[verify.index("## ADAPT-VERIFY1") : verify.index("## ADAPT-MIGRATE1")]
    assert "**Status:** implemented in `mdstats 0.20.127a0`." in section
    assert "### ADAPT-VERIFY1 implementation record (`0.20.127a0`)" in section
    assert "first passing candidate" in section
    assert "AdaptiveDeploymentModelRecord" in section
