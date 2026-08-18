from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_mlcv_cross_validation_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_mlcv_agg1_specification_is_shipped_and_current():
    assert mdstats.__version__ == "0.20.140a0"
    text = SPEC.read_text(encoding="utf-8")
    assert "implemented in mdstats 0.20.136a0" in text
    assert "cannot trigger fallback to another epoch" in text
    assert "sample standard deviation" in text
    assert "diagnostic-only" in text
    assert "permanently production-ineligible" in text


def test_architecture_marks_agg1_implemented_and_final1_next():
    text = MANUAL.read_text(encoding="utf-8")
    assert "`MLCV-AGG1` - **implemented in 0.20.136a0**" in text
    assert "The nine-gate conventional-CV correction is complete." in text
