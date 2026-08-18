from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]


def test_mlcv_select1_release_and_specification_surface():
    assert f'version = "{mdstats.__version__}"' in (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    spec = (ROOT / "docs/specs/training_data/mlff_mlcv_run_selection_spec.md").read_text(encoding="utf-8")
    assert "MLCV-SELECT1" in spec
    assert "V_i_full" in spec
    assert "D_full" in spec
    assert "R_full" in spec
    assert "TARGET_OUTER_CV_EVALUATION" in spec
    assert "representative_selected" in spec
    assert "no_representative" in spec


def test_mlcv_select1_architecture_gate_marked_implemented():
    manual = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text(encoding="utf-8")
    assert "MLCV-SELECT1` - **implemented in 0.20.135a0**" in manual
    assert "MLCV-SELECT1 implementation record (`0.20.135a0`)" in manual
    assert "every retained RANK1 v2 candidate is evaluated" in manual


def test_generated_config_keeps_configurable_stop_factor_defaults():
    text = (ROOT / "campaign.toml.example").read_text(encoding="utf-8")
    assert "target_stop_fraction = 0.80" in text
    assert "replay_stop_multiplier = 1.20" in text
    assert "both factors are configurable" in text
