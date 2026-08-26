from __future__ import annotations

from pathlib import Path

import mdstats
from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def test_train2b_manual_runtime_contract() -> None:
    manual = (ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md").read_text(
        encoding="utf-8"
    )
    section = manual.split("## Gate TRAIN2B", 1)[1].split("## Protocol-matched cross-validation", 1)[0]
    assert "durably pauses only at the active exact boundary" in section
    assert "Python/NumPy/Torch CPU/CUDA RNG states" in section
    assert "train2_true_replay" in section
    assert "restores live non-EMA" in section
    assert "parameters, EMA state" in section
    assert "Eliminated-size jobs receive no later authorization" in section


def test_train2b_public_runtime_exports() -> None:
    assert Version(mdstats.__version__) >= Version("0.20.170a0")
    assert mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE == "MDSTATS_TRAIN2_RUNTIME_PLAN"
    assert mdstats.TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE == "MDSTATS_TRAIN2_TRUE_REPLAY_PATH"
    assert mdstats.TRAIN2_TRUE_REPLAY_LOG_HEAD == "train2_true_replay"


def test_train2b_shipped_campaign_example_uses_current_policy() -> None:
    example = (ROOT / "campaign.toml.example").read_text(encoding="utf-8")
    assert 'policy_generation = "train2"' in example
    assert 'checkpoint_strategy = "train2_target_first"' in example
    assert 'allowed_replay_degradation_mev_per_a = 30.0' in example
    assert 'maximum_replay_degradation_fraction' not in example
    assert 'target_score_weight' not in example
    assert 'replay_score_weight' not in example
    assert 'TRAIN2B executes this frozen schedule once per optimizer update' in example
