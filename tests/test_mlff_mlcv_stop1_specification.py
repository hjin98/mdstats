from __future__ import annotations

from pathlib import Path

import mdstats
from mdstats.training_data.campaign_cli import _config_template


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_mlcv_stop1_release_and_architecture_record() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    text = MANUAL.read_text(encoding="utf-8")
    assert "MLCV-STOP1 implementation record (`0.20.133a0`)" in text
    assert "lightweight stopping heuristics only" in text
    assert "minimum_epochs_before_adaptive_stop" in text
    assert "R_full" in text and "full TRUE_DFT" in text


def test_mlcv_stop1_generated_defaults() -> None:
    config = _config_template(
        workspace="./w",
        training_root="./t",
        foundation_model="./f.model",
        replay_train="./r.extxyz",
        replay_monitor="./rm.extxyz",
    )
    assert "target_stop_fraction = 0.80" in config
    assert "replay_stop_multiplier = 1.20" in config
    assert "minimum_epochs_before_adaptive_stop = 3" in config
    assert "max_num_epochs = 30" in config


def test_mlcv_stop1_policy_schema_is_v3_and_legacy_schemas_remain_readable() -> None:
    assert mdstats.ADAPTIVE_STOP_POLICY_SCHEMA == "mdstats.adaptive-training-stop-policy.v3"
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.serialization_schema == mdstats.ADAPTIVE_STOP_POLICY_SCHEMA
    assert policy.minimum_epochs_before_adaptive_stop == 3
