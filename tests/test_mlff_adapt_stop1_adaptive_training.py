from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data.adaptive_stop import (
    ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_REPLAY_LIGHT_PATH_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_FOUNDATION_BASELINE_PATH_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_FOUNDATION_MODEL_SHA256_ENVIRONMENT_VARIABLE,
    ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD,
)


def _append(path: Path, *, epoch, head: str, rmse_f: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"mode": "eval", "epoch": epoch, "head": head, "rmse_f": rmse_f}) + "\n")


def _activate(monkeypatch, tmp_path: Path, policy: mdstats.AdaptiveTrainingStopPolicy):
    state = tmp_path / "adaptive_training_stop.json"
    monkeypatch.setenv(ADAPTIVE_STOP_POLICY_ENVIRONMENT_VARIABLE, json.dumps(policy.to_dict()))
    monkeypatch.setenv(ADAPTIVE_STOP_STATE_PATH_ENVIRONMENT_VARIABLE, str(state))
    if policy.replay_enabled and policy.serialization_schema == mdstats.ADAPTIVE_STOP_POLICY_SCHEMA:
        replay_light = tmp_path / "R_light.xyz"
        replay_full = tmp_path / "R_full.xyz"
        replay_light.write_text("light replay domain\n", encoding="utf-8")
        replay_full.write_text("full replay domain\n", encoding="utf-8")
        monkeypatch.setenv(ADAPTIVE_STOP_REPLAY_LIGHT_PATH_ENVIRONMENT_VARIABLE, str(replay_light))
        monkeypatch.setenv(ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE, str(replay_full))
        monkeypatch.setenv(ADAPTIVE_STOP_FOUNDATION_BASELINE_PATH_ENVIRONMENT_VARIABLE, str(tmp_path / "foundation_baseline.json"))
        monkeypatch.setenv(ADAPTIVE_STOP_FOUNDATION_MODEL_SHA256_ENVIRONMENT_VARIABLE, "a" * 64)
    return state


def _append_foundation(log: Path, *, light: float = 0.020, full: float = 0.075281) -> None:
    _append(log, epoch=None, head="pt_head", rmse_f=light)
    _append(log, epoch=None, head=ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD, rmse_f=full)
    _append(log, epoch=None, head="target_head", rmse_f=0.050)


def test_default_weight_geometry_matches_30_24_36_mev() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.maximum_target_force_rmse_ev_per_angstrom == pytest.approx(0.030)
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(0.030)
    assert policy.target_stop_force_rmse_ev_per_angstrom == pytest.approx(0.024)
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(0.036)


@pytest.mark.parametrize(
    ("target_weight", "replay_weight", "expected_replay"),
    [(1.0, 1.0, 0.030), (2.0, 1.0, 0.060), (1.0, 2.0, 0.015)],
)
def test_weight_ratio_derives_replay_boundary(target_weight, replay_weight, expected_replay) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        target_score_weight=target_weight,
        replay_score_weight=replay_weight,
    )
    assert policy.maximum_replay_force_rmse_ev_per_angstrom == pytest.approx(expected_replay)
    assert policy.replay_stop_force_rmse_ev_per_angstrom == pytest.approx(1.2 * expected_replay)


def test_target_success_records_durable_history_and_exact_restart(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=30)
    state_path = _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "results" / "train.txt"
    _append_foundation(log)
    mdstats.validate_adaptive_stop_foundation_baseline(log)

    _append(log, epoch=0, head="pt_head", rmse_f=0.025)
    _append(log, epoch=0, head="target_head", rmse_f=0.029)
    assert not mdstats.adaptive_training_stop_requested(log, 0)

    _append(log, epoch=1, head="pt_head", rmse_f=0.029)
    _append(log, epoch=1, head="target_head", rmse_f=0.0239)
    # The target margin is a heuristic only and cannot fire before three
    # completed epochs by default.
    assert not mdstats.adaptive_training_stop_requested(log, 1)
    _append(log, epoch=2, head="pt_head", rmse_f=0.0295)
    _append(log, epoch=2, head="target_head", rmse_f=0.0238)
    assert mdstats.adaptive_training_stop_requested(log, 2)
    state = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert state.stop_epoch == 2
    assert state.stop_reason == "target_success"
    assert state.run_outcome == "admissible_checkpoint_available"
    assert [item.epoch for item in state.epochs] == [0, 1, 2]
    assert all(item.candidate_eligible for item in state.epochs)

    # Repeating the same durable epoch is idempotent.
    assert mdstats.adaptive_training_stop_requested(log, 2)
    # A MACE restart appends a new epoch=None block for the resumed model. The
    # frozen foundation baseline must not be reinterpreted or changed.
    _append(log, epoch=None, head="pt_head", rmse_f=0.028)
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    restored = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert restored.foundation_replay_light_force_rmse_ev_per_angstrom == pytest.approx(0.020)
    assert restored.foundation_replay_full_force_rmse_ev_per_angstrom == pytest.approx(0.075281)


def test_replay_exhaustion_preserves_earlier_admissible_checkpoint(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    state_path = _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "train.txt"
    _append_foundation(log)
    mdstats.validate_adaptive_stop_foundation_baseline(log)

    _append(log, epoch=0, head="pt_head", rmse_f=0.029)
    _append(log, epoch=0, head="target_head", rmse_f=0.028)
    assert not mdstats.adaptive_training_stop_requested(log, 0)

    _append(log, epoch=1, head="pt_head", rmse_f=0.0561)
    _append(log, epoch=1, head="target_head", rmse_f=0.026)
    assert not mdstats.adaptive_training_stop_requested(log, 1)
    _append(log, epoch=2, head="pt_head", rmse_f=0.0562)
    _append(log, epoch=2, head="target_head", rmse_f=0.026)
    assert mdstats.adaptive_training_stop_requested(log, 2)
    state = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert state.stop_reason == "replay_exhaustion"
    # Crossing either full-validation reference threshold on R_light/T_light
    # never disqualifies the checkpoint at STOP1.
    assert all(item.candidate_eligible for item in state.epochs)
    assert state.run_outcome == "admissible_checkpoint_available"


def test_epoch_ceiling_and_no_admissible_outcome(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(max_num_epochs=3)
    state_path = _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "train.txt"
    _append_foundation(log)
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    for epoch in range(3):
        _append(log, epoch=epoch, head="pt_head", rmse_f=0.029)
        _append(log, epoch=epoch, head="target_head", rmse_f=0.031)
        stopped = mdstats.adaptive_training_stop_requested(log, epoch)
        assert stopped is (epoch == 2)
    state = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert state.stop_reason == "max_epochs_reached"
    assert state.run_outcome == "admissible_checkpoint_available"


def test_foundation_baseline_establishes_zero_even_above_degradation_budget(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        target_score_weight=1.0,
        replay_score_weight=2.0,
    )
    state_path = _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "train.txt"
    _append_foundation(log, light=0.040, full=0.075281)
    # A 15 meV/A degradation budget is not an absolute RMSE feasibility gate.
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    state = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert state.foundation_replay_light_force_rmse_ev_per_angstrom == pytest.approx(0.040)
    assert state.foundation_replay_full_force_rmse_ev_per_angstrom == pytest.approx(0.075281)
    assert state.replay_degradation_budget_ev_per_angstrom == pytest.approx(0.015)
    assert state.replay_full_absolute_ceiling_ev_per_angstrom == pytest.approx(0.090281)
    assert "allow_replay_threshold_below_foundation_baseline" not in policy.to_dict()

def test_naive_training_uses_target_only_stopping(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(replay_enabled=False)
    state_path = _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "train.txt"
    _append(log, epoch=None, head="target_head", rmse_f=0.050)
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    for epoch in range(3):
        _append(log, epoch=epoch, head="target_head", rmse_f=0.023)
        assert mdstats.adaptive_training_stop_requested(log, epoch) is (epoch == 2)
    state = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert state.stop_reason == "target_success"
    assert state.epochs[0].replay_force_rmse_ev_per_angstrom is None


def test_policy_roundtrip_and_validation() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        target_score_weight=2.0,
        replay_score_weight=1.0,
        target_stop_fraction=0.8,
        replay_stop_multiplier=1.2,
    )
    assert mdstats.AdaptiveTrainingStopPolicy.from_dict(policy.to_dict()) == policy
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.AdaptiveTrainingStopPolicy(target_stop_fraction=1.0)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.AdaptiveTrainingStopPolicy(replay_stop_multiplier=1.0)
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.AdaptiveTrainingStopPolicy(minimum_epochs_before_adaptive_stop=0)


def test_terminal_state_is_visible_before_restart_epoch_loop(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "train.txt"
    _append_foundation(log)
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    assert not mdstats.adaptive_training_stop_already_terminal(log)
    for epoch in range(3):
        _append(log, epoch=epoch, head="pt_head", rmse_f=0.029)
        _append(log, epoch=epoch, head="target_head", rmse_f=0.023)
        assert mdstats.adaptive_training_stop_requested(log, epoch) is (epoch == 2)
    assert mdstats.adaptive_training_stop_already_terminal(log)


def test_lightweight_full_threshold_crossing_is_not_disqualification() -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.candidate_eligible(0.031, 0.029)
    assert policy.candidate_eligible(0.029, 0.031)
    assert policy.candidate_eligible(0.050, 0.050)


def test_foundation_baselines_are_matched_to_light_and_full_domains(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy()
    state_path = _activate(monkeypatch, tmp_path, policy)
    replay_full = tmp_path / "R_full.xyz"
    replay_full.write_text("immutable full replay evidence\n", encoding="utf-8")
    monkeypatch.setenv(
        ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_PATH_ENVIRONMENT_VARIABLE, str(replay_full)
    )
    log = tmp_path / "train.txt"
    # R_light and R_full deliberately have different baselines; both must be preserved.
    _append(log, epoch=None, head="pt_head", rmse_f=0.010)
    _append(log, epoch=None, head=ADAPTIVE_STOP_FOUNDATION_REPLAY_FULL_LOG_HEAD, rmse_f=0.025)
    _append(log, epoch=None, head="target_head", rmse_f=0.050)
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    state = mdstats.AdaptiveTrainingStopState.from_dict(json.loads(state_path.read_text()))
    assert state.foundation_replay_light_force_rmse_ev_per_angstrom == pytest.approx(0.010)
    assert state.foundation_replay_full_force_rmse_ev_per_angstrom == pytest.approx(0.025)
    assert state.foundation_replay_evidence_scope == "matched_light_full_true_dft"
    assert state.foundation_replay_light_artifact_sha256 is not None
    assert state.foundation_replay_full_artifact_sha256 is not None


def test_hard_epoch_ceiling_preempts_minimum_floor_when_budget_is_short(monkeypatch, tmp_path: Path) -> None:
    policy = mdstats.AdaptiveTrainingStopPolicy(
        minimum_epochs_before_adaptive_stop=5, max_num_epochs=2
    )
    _activate(monkeypatch, tmp_path, policy)
    log = tmp_path / "train.txt"
    _append_foundation(log)
    mdstats.validate_adaptive_stop_foundation_baseline(log)
    for epoch in range(2):
        _append(log, epoch=epoch, head="pt_head", rmse_f=0.020)
        _append(log, epoch=epoch, head="target_head", rmse_f=0.020)
        stopped = mdstats.adaptive_training_stop_requested(log, epoch)
        assert stopped is (epoch == 1)
    state = mdstats.AdaptiveTrainingStopState.from_dict(
        json.loads((tmp_path / "adaptive_training_stop.json").read_text())
    )
    assert state.stop_reason == "max_epochs_reached"


def test_legacy_v1_policy_round_trips_identity_and_behavior() -> None:
    from mdstats.training_data.adaptive_stop import ADAPTIVE_STOP_POLICY_LEGACY_SCHEMAS

    legacy_schema = "mdstats.adaptive-training-stop-policy.v1"
    payload = {
        "schema": legacy_schema,
        "maximum_target_force_rmse_ev_per_angstrom": 0.030,
        "target_score_weight": 1.0,
        "replay_score_weight": 1.0,
        "target_stop_fraction": 0.80,
        "replay_stop_multiplier": 1.20,
        "max_num_epochs": 30,
        "replay_enabled": True,
        "allow_replay_threshold_below_foundation_baseline": False,
        "target_head_name": "target_head",
        "replay_head_name": "pt_head",
    }
    from mdstats.training_data._common import digest

    payload["policy_digest"] = digest(payload)
    restored = mdstats.AdaptiveTrainingStopPolicy.from_dict(payload)
    assert restored.policy_digest == payload["policy_digest"]
    assert restored.to_dict() == payload
    assert restored.minimum_epochs_before_adaptive_stop == 1
    assert not restored.candidate_eligible(0.031, 0.020)
    assert not restored.candidate_eligible(0.020, 0.031)


def test_the_active_stop_policy_schema_and_training_horizon_are_current() -> None:
    """The stop policy's own defaults, and the horizon the template still sets.

    Consolidated from the retired MLCV-STOP1 gate specification. The stop
    fractions it asserted are no longer generated into `campaign.toml`; the
    policy object owns them now, so that is where they are asserted. The
    training horizon the template does still emit is kept.
    """

    from mdstats.training_data.campaign_cli import _config_template

    config = _config_template(
        workspace="./w",
        training_root="./t",
        foundation_model="./f.model",
        replay_train="./r.extxyz",
        replay_monitor="./rm.extxyz",
    )
    assert "max_num_epochs = 30" in config

    assert mdstats.ADAPTIVE_STOP_POLICY_SCHEMA == "mdstats.adaptive-training-stop-policy.v3"
    policy = mdstats.AdaptiveTrainingStopPolicy()
    assert policy.serialization_schema == mdstats.ADAPTIVE_STOP_POLICY_SCHEMA
    assert policy.minimum_epochs_before_adaptive_stop == 3
    assert policy.target_stop_fraction == 0.80
    assert policy.replay_stop_multiplier == 1.20
