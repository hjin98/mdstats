from __future__ import annotations

from pathlib import Path

import mdstats


ROOT = Path(__file__).resolve().parents[1]


def test_adapt_stop1_spec_and_architecture_mark_gate_implemented() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_adaptive_training_stop_spec.md").read_text()
    architecture = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    assert "implemented in mdstats 0.20.124a0" in spec
    section = architecture.split("## ADAPT-STOP1", 1)[1].split("## ADAPT-RANK1", 1)[0]
    assert "**Status:** implemented in `mdstats 0.20.124a0`." in section
    assert "ADAPT-STOP1 does **not** rank or select" in section


def test_generated_configuration_contains_stop_policy_defaults() -> None:
    from mdstats.training_data.campaign_cli import _config_template

    config = _config_template(workspace="./w", training_root="./t", foundation_model="./f.model", replay_train="./r.extxyz", replay_monitor="./rm.extxyz")
    assert "maximum_target_force_rmse_ev_per_angstrom = 0.030" in config
    assert "target_score_weight = 1.0" in config
    assert "replay_score_weight = 1.0" in config
    assert "target_stop_fraction = 0.80" in config
    assert "replay_stop_multiplier = 1.20" in config
    assert "minimum_epochs_before_adaptive_stop = 3" in config
    assert "allow_replay_threshold_below_foundation_baseline" not in config
    assert "replay_degradation_budget_mev_per_a" in config


def test_default_policy_geometry_and_replay_weight_formula_are_documented() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_adaptive_training_stop_spec.md").read_text()
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.maximum_target_force_rmse_ev_per_angstrom == 0.030
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == 0.030
    assert policy.target_stop_force_rmse_ev_per_angstrom == 0.024
    assert policy.replay_stop_force_rmse_ev_per_angstrom == 0.036
    for token in ("30 meV/A", "24 meV/A", "36 meV/A", "w_T", "w_R"):
        assert token in spec


def test_spec_freezes_checkpoint_then_stop_and_restart_contract() -> None:
    spec = (ROOT / "docs/specs/training_data/mlff_adaptive_training_stop_spec.md").read_text()
    assert "save the epoch checkpoint durably" in spec
    assert "adaptive_training_stop.json" in spec
    assert "skips the epoch" in spec and "loop" in spec
    assert "No extra training epoch is permitted" in spec
    assert "foundation replay baseline" in spec


def test_rank_and_eval_gates_are_closed() -> None:
    architecture = (ROOT / "docs/arch_manuals/mlff_training_data_architecture.md").read_text()
    rank = architecture.split("## ADAPT-RANK1", 1)[1].split("## ADAPT-EVAL1", 1)[0]
    evaluation = architecture.split("## ADAPT-EVAL1", 1)[1].split("## ADAPT-VERIFY1", 1)[0]
    assert "**Status:** implemented in `mdstats 0.20.125a0`." in rank
    assert "**Status:** implemented in `mdstats 0.20.126a0`." in evaluation
