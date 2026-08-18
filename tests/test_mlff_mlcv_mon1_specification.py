from __future__ import annotations

from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_mlcv_mon1_release_and_architecture_record() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    assert mdstats.MLFF_DATA8_PARSER_VERSION == "0.20.132a0"
    text = MANUAL.read_text(encoding="utf-8")
    assert "MLCV-MON1 in `0.20.132a0`" in text or "MLCV-MON1 in 0.20.132a0" in text
    assert "MLCV-MON1 implementation record (`0.20.132a0`)" in text
    assert "V_i_light" in text and "V_i_full" in text
    assert "D_light" in text and "D_full" in text
    assert "R_light" in text and "R_full" in text
    assert "target_train_diagnostic" in text


def test_mlcv_mon1_public_monitor_contract() -> None:
    assert mdstats.MLCV_MONITOR_POLICY_SCHEMA == "mdstats.mlcv-monitor-policy.v1"
    assert mdstats.MLCV_MONITOR_CATALOG_SCHEMA == "mdstats.mlcv-monitor-catalog.v1"
    policy = mdstats.MlcvMonitorPolicy()
    assert policy.target_light_configurations == 256
    assert policy.replay_light_configurations == 512
    assert policy.training_diagnostic_configurations == 256
    for name in (
        "MlcvMonitorPolicy",
        "MlcvRunMonitorRecord",
        "MlcvReplayMonitorRecord",
        "MlcvMonitorCatalog",
        "write_mlcv_diagnostic_history",
    ):
        assert name in mdstats.__all__


def test_mlcv_mon1_does_not_claim_later_gates() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    section = text[text.index("### MLCV-MON1 implementation record") : text.index("### MLCV-STOP1 acceptance gate")]
    assert "does **not** yet change" in section
    assert "lightweight 30/30 candidate-eligibility rule" in section
    assert "MLCV-STOP1" in section
