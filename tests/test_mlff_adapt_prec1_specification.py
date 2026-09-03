from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_binary_model_precision_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_adapt_prec1_release_and_spec_contract():
    text = SPEC.read_text(encoding="utf-8")
    assert "Status: implemented in mdstats 0.20.122a0" in text
    assert "`single`: learned-model" in text
    assert "`double`: the same learned-model lifecycle uses float64" in text
    assert "contains no `[training.precision]` staged schedule" in text
    assert "FP64 scientific-arithmetic invariant" in text
    assert "Historical staged `refine` schedules remain deserializable" in text


def test_adapt_prec1_manual_tracks_completed_adaptive_revision():
    text = MANUAL.read_text(encoding="utf-8")
    assert "## ADAPT-PREC1 - binary model precision" in text
    assert "**Status:** implemented in `mdstats 0.20.122a0`." in text
    mon_start = text.index("## ADAPT-MON1")
    assert "**Status:** `implemented` in `mdstats 0.20.123a0`." in text[mon_start : mon_start + 1400]
    stop_start = text.index("## ADAPT-STOP1")
    assert "**Status:** implemented in `mdstats 0.20.124a0`." in text[stop_start : stop_start + 1000]
    rank_start = text.index("## ADAPT-RANK1")
    assert "**Status:** implemented in `mdstats 0.20.125a0`." in text[rank_start : rank_start + 1000]
    eval_start = text.index("## ADAPT-EVAL1")
    assert "**Status:** implemented in `mdstats 0.20.126a0`." in text[eval_start : eval_start + 1000]
    verify_start = text.index("## ADAPT-VERIFY1")
    assert "**Status:** implemented in `mdstats 0.20.127a0`." in text[verify_start : verify_start + 1000]
    migrate_start = text.index("## ADAPT-MIGRATE1")
    assert "**Status:** implemented in `mdstats 0.20.128a0`." in text[migrate_start : migrate_start + 1200]
