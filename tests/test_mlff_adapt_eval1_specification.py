from __future__ import annotations

from pathlib import Path

import mdstats
from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_adaptive_full_evaluation_spec.md"
ARCH = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_adapt_eval1_release_identity_and_specification() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    text = SPEC.read_text(encoding="utf-8")
    assert "Status: implemented in mdstats 0.20.126a0" in text
    assert 'checkpoint_strategy = "adaptive_topk"' in text
    assert "finalist_count = 5" in text
    assert "finalist_rescue_batch_size = 5" in text
    assert "full_target_evaluation.xyz" in text
    assert "TRUE_DFT" in text
    assert "Naive fine-tuning" in text
    assert "validation-only" in text


def test_adapt_eval1_is_historical_while_mlcv_is_generated_default() -> None:
    source = Path(campaign_cli.__file__).read_text(encoding="utf-8")
    example = (ROOT / "campaign.toml.example").read_text(encoding="utf-8")
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in source
    assert 'checkpoint_strategy = "mlcv_nested_cv"' in example
    assert "finalist_count = 5" in source
    assert "finalist_rescue_batch_size = 5" in source
    # The legacy evaluator remains public/readable rather than being deleted.
    assert mdstats.MultiFidelityEvaluationPolicy().minimum_finalists >= 1


def test_architecture_marks_adapt_eval1_and_verify1_implemented() -> None:
    text = ARCH.read_text(encoding="utf-8")
    start = text.index("## ADAPT-EVAL1")
    section = text[start : start + 7000]
    assert "**Status:** implemented in `mdstats 0.20.126a0`." in section
    assert "### ADAPT-EVAL1 implementation record (`0.20.126a0`)" in section
    verify = text[text.index("## ADAPT-VERIFY1") : text.index("## ADAPT-MIGRATE1")]
    assert "**Status:** implemented in `mdstats 0.20.127a0`." in verify
    assert "### ADAPT-VERIFY1 implementation record (`0.20.127a0`)" in verify
