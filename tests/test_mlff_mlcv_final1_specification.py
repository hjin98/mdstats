from pathlib import Path
import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_mlcv_final_selection_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_mlcv_final1_specification_is_shipped_and_current():
    assert mdstats.__version__ == "0.20.140a0"
    text = SPEC.read_text(encoding="utf-8")
    assert "implemented in mdstats 0.20.137a0" in text
    assert "Fold models" in text and "permanently excluded" in text
    assert "production_best" in text and "verification candidate" in text
    assert 'seed_mode = "optimizer_only"' in text
    assert 'seed_mode = "optimizer_and_cv_partition"' in text


def test_architecture_marks_final1_implemented_and_verify1_next():
    text = MANUAL.read_text(encoding="utf-8")
    assert "`MLCV-FINAL1` - **implemented in 0.20.137a0**" in text
    assert "The nine-gate conventional-CV correction is complete." in text
