from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import mdstats
from mdstats.training_data import adaptive_stop


def _activate(monkeypatch, tmp_path: Path, policy: mdstats.AdaptiveTrainingStopPolicy) -> Path:
    state = tmp_path / "adaptive_training_stop.json"
    monkeypatch.setenv(
        adaptive_stop.ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE,
        json.dumps(policy.to_dict()),
    )
    monkeypatch.setenv(
        adaptive_stop.ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE,
        str(state),
    )
    return state


def test_stop1_default_control_geometry_is_24_36_with_three_epoch_floor() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.target_stop_force_rmse_ev_per_angstrom == pytest.approx(0.024)
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(0.030)
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(0.036)
    assert policy.minimum_epochs_before_adaptive_stop == 3
    assert policy.max_num_epochs == 30

    # The full 30/30 references do not gate lightweight rankability.
    assert policy.candidate_eligible(0.031, 0.029)
    assert policy.candidate_eligible(0.029, 0.031)

    assert policy.stop_reason(epoch=0, target_rmse=0.020, replay_rmse=0.020, foundation_replay_rmse=0.075) is None
    assert policy.stop_reason(epoch=1, target_rmse=0.020, replay_rmse=0.020, foundation_replay_rmse=0.075) is None
    assert policy.stop_reason(epoch=2, target_rmse=0.020, replay_rmse=0.020, foundation_replay_rmse=0.075) == "target_success"


def test_stop1_hard_ceiling_is_independent_of_adaptive_floor() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        minimum_epochs_before_adaptive_stop=50,
        max_num_epochs=2,
    )
    assert policy.stop_reason(epoch=0, target_rmse=0.020, replay_rmse=0.020, foundation_replay_rmse=0.075) is None
    assert policy.stop_reason(epoch=1, target_rmse=0.020, replay_rmse=0.020, foundation_replay_rmse=0.075) == "max_epochs_reached"


def test_stop1_foundation_full_loader_is_one_shot_and_order_safe(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    state_path = _activate(monkeypatch, tmp_path, policy)
    replay_full = tmp_path / "R_full.xyz"
    replay_full.write_text("full true replay\n", encoding="utf-8")
    monkeypatch.setenv(
        adaptive_stop.ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE,
        str(replay_full),
    )

    sentinel = object()
    monkeypatch.setattr(
        adaptive_stop,
        "_validation_loader_from_extxyz",
        lambda *args, **kwargs: sentinel,
    )
    model = SimpleNamespace(heads=["pt_head", "target_head"])
    existing = {"pt_head": object(), "target_head": object()}
    prepared = adaptive_stop.prepare_foundation_full_replay_validation_loader(model, existing)
    assert tuple(prepared)[0] == adaptive_stop.ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD
    assert tuple(prepared)[-1] == "target_head"
    assert prepared[adaptive_stop.ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD] is sentinel

    cleaned = adaptive_stop.remove_foundation_full_replay_validation_loader(prepared)
    assert adaptive_stop.ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD not in cleaned
    assert tuple(cleaned) == tuple(existing)

    # A frozen foundation baseline suppresses the one-shot loader on exact restart.
    frozen = mdstats.AdaptiveTrainingStopState(
        policy_digest=policy.policy_digest,
        foundation_replay_force_rmse_ev_per_angstrom=0.020,
        foundation_replay_threshold_feasible=True,
        foundation_replay_evidence_scope="full_true_dft",
        foundation_replay_artifact_sha256=adaptive_stop.sha256_file_cached(replay_full),
    )
    state_path.write_text(json.dumps(frozen.to_dict()), encoding="utf-8")
    monkeypatch.setattr(
        adaptive_stop,
        "_validation_loader_from_extxyz",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not rebuild R_full")),
    )
    restarted = adaptive_stop.prepare_foundation_full_replay_validation_loader(model, existing)
    assert restarted == existing


def test_stop1_wrapper_injects_and_removes_one_shot_rfull_loader() -> None:
    from mdstats.training_data import critical_precision_cli

    source = Path(critical_precision_cli.__file__).read_text(encoding="utf-8")
    assert "prepare_foundation_full_replay_validation_loader" in source
    assert "remove_foundation_full_replay_validation_loader" in source
    assert "validate_adaptive_stop_foundation_baseline(logger.path)" in source


def test_stop1_control_margins_are_derived_from_resolved_full_criteria() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        maximum_target_force_rmse_ev_per_angstrom=0.040,
        target_score_weight=2.0,
        replay_score_weight=1.0,
    )
    # Standard full criteria are T_max=40 meV/A and, from the 2:1 score
    # geometry, R_max=80 meV/A.  Lightweight stop margins must be derived
    # from those resolved criteria rather than stored as independent 24/36
    # constants.
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(0.080)
    assert policy.target_stop_force_rmse_ev_per_angstrom == pytest.approx(
        0.80 * policy.maximum_target_force_rmse_ev_per_angstrom
    )
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(
        1.20 * policy.maximum_replay_force_rmse_ev_per_angstrom
    )
    assert policy.target_stop_force_rmse_ev_per_angstrom == pytest.approx(0.032)
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(0.096)


def test_stop1_margin_factors_are_configurable_with_80_and_120_percent_defaults() -> None:
    default = mdstats.AdaptiveTrainingStopPolicy()
    assert default.target_stop_fraction == pytest.approx(0.80)
    assert default.replay_stop_multiplier == pytest.approx(1.20)

    custom = mdstats.AdaptiveTrainingStopPolicy(
        target_stop_fraction=0.75, replay_stop_multiplier=1.10
    )
    assert custom.target_stop_force_rmse_ev_per_angstrom == pytest.approx(0.0225)
    assert custom.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(0.033)
