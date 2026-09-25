from __future__ import annotations

from pathlib import Path

from mdstats.training_data import campaign_cli

ROOT = Path(__file__).resolve().parents[1]


def test_train2_cueq_doctor_sanity_policy_is_coarse_and_documented() -> None:
    policy = campaign_cli._training_acceleration_noise_normalized_policy()
    assert policy.repeat_count == 10
    assert policy.warmup_count == 1
    assert policy.stable_channel_abs_ceiling == 1.0e-5
    assert policy.force_distribution_ratio_ceiling == 1.5
    assert policy.force_max_self_factor == 1.5
    assert policy.force_max_absolute_ceiling == 1.0e-4
    assert policy.force_threshold == 1.0e-5

    spec = (
        ROOT / "docs/specs/training_data/mlff_cueq_train_noise_normalized_parity_spec.md"
    ).read_text(encoding="utf-8")
    assert "engineering sanity pre-check" in spec
    assert "not a scientific-equivalence" in spec
    assert "1e-5" in spec
    assert "1.5" in spec
