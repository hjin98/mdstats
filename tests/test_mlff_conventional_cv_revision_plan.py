from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_release_records_architecture_only_mlcv_revision():
    assert f'version = "{mdstats.__version__}"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    text = MANUAL.read_text(encoding="utf-8")
    assert "Post-0.20.129 conventional-CV checkpoint-selection and final-model revision" in text
    assert "MLCV-ROLE1 implemented in" in text and "remaining MLCV gates" in text
    for gate in (
        "MLCV-ROLE1",
        "MLCV-MON1",
        "MLCV-STOP1",
        "MLCV-RANK1",
        "MLCV-SELECT1",
        "MLCV-AGG1",
        "MLCV-FINAL1",
        "MLCV-VERIFY1",
        "MLCV-MIGRATE1",
    ):
        assert gate in text


def test_outer_cv_fold_has_no_checkpoint_selection_authority():
    text = MANUAL.read_text(encoding="utf-8")
    assert "The outer CV fold `C_i` is never used for early stopping" in text
    assert "fold top-five target selection uses `V_i_full`, never `C_i`" in text
    assert "each fold representative is evaluated once on its untouched outer fold" in text


def test_lightweight_thresholds_are_control_not_acceptance():
    text = MANUAL.read_text(encoding="utf-8")
    assert "training-control heuristics on lightweight validation only" in text
    assert "Any checkpoint with complete finite" in text and "lightweight target/replay metrics is rankable" in text
    assert "30 meV/A target and the resolved replay ceiling are component-wise hard gates" in text


def test_only_final_development_models_can_be_exported():
    text = MANUAL.read_text(encoding="utf-8")
    assert "CV folds are evidence about the **training recipe**" in text
    assert "Only those final representatives are eligible for production selection" in text
    assert "one qualified final representative per seed, when available" in text
    assert "locked test `E` is activated" in text and "evaluated exactly once" in text
