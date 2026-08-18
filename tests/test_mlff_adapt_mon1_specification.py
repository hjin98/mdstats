from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_online_monitor_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
CONFIG_EXAMPLE = ROOT / "campaign.toml.example"


def test_adapt_mon1_release_and_normative_defaults():
    assert mdstats.__version__ == "0.20.140a0"
    text = SPEC.read_text(encoding="utf-8")
    assert "Status: implemented in mdstats 0.20.123a0" in text
    assert "256 configurations" in text
    assert "512 configurations" in text
    assert "balanced_condition_run_time_systematic" in text
    assert "chemistry_size_systematic" in text
    assert "ReplayLabelMode.TRUE_DFT" in text
    assert "must never supply gradients" in text


def test_adapt_mon1_manual_closed_and_stop_gate_closed():
    text = MANUAL.read_text(encoding="utf-8")
    mon = text.index("## ADAPT-MON1")
    stop = text.index("## ADAPT-STOP1")
    assert mon < stop
    assert "**Status:** `implemented` in `mdstats 0.20.123a0`." in text[mon:stop]
    assert "**Status:** implemented in `mdstats 0.20.124a0`." in text[stop : stop + 1000]
    assert "hard-epoch boundary" in text[mon:stop]
    assert "EVAL-MF" in text[mon:stop]


def test_adapt_mon1_generated_example_binds_policy_defaults():
    text = CONFIG_EXAMPLE.read_text(encoding="utf-8")
    assert "online_monitor_seed = 161803" in text
    assert "online_target_monitor_configurations = 256" in text
    assert "online_replay_monitor_configurations = 512" in text
