from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_online_monitor_spec.md"
CONFIG_EXAMPLE = ROOT / "campaign.toml.example"


def test_adapt_mon1_normative_defaults():
    text = SPEC.read_text(encoding="utf-8")
    assert "256 configurations" in text
    assert "512 configurations" in text
    assert "balanced_condition_run_time_systematic" in text
    assert "chemistry_size_systematic" in text
    assert "Online monitors never supply gradients." in text
    assert "Monitoring configurations never contribute gradients." in text


def test_adapt_mon1_generated_example_binds_policy_defaults():
    text = CONFIG_EXAMPLE.read_text(encoding="utf-8")
    assert "online_monitor_seed = 161803" in text
    assert "online_target_monitor_configurations = 256" in text
    assert "online_replay_monitor_configurations = 512" in text
