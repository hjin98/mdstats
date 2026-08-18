from __future__ import annotations

from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_cli


def _write_default(tmp_path: Path, **kwargs: object) -> tuple[dict, object]:
    path = tmp_path / "campaign.toml"
    text = campaign_cli._config_template(
        workspace="work",
        training_root="training",
        foundation_model="mace-mh-1.model",
        replay_train="replay_train.xyz",
        replay_monitor="replay_monitor.xyz",
        **kwargs,
    )
    path.write_text(text, encoding="utf-8")
    return campaign_cli._load_config(path)


def test_generated_default_is_phase_separated_e3nn_source_cueq_training(tmp_path: Path) -> None:
    cfg, _paths = _write_default(tmp_path)
    source = campaign_cli._acceleration_policy(cfg)
    training = campaign_cli._training_acceleration_policy(cfg)
    assert source.backend is mdstats.MaceAccelerationBackend.E3NN
    assert training.backend is mdstats.MaceAccelerationBackend.CUEQ
    assert campaign_cli._phase_separated_acceleration(cfg)
    optimizer = campaign_cli._optimizer_policy(cfg, seed=1, num_workers=0, paths=None)
    assert optimizer.acceleration_policy.backend is mdstats.MaceAccelerationBackend.CUEQ
    assert optimizer.acceleration_realization_digest is None


def test_generated_training_backend_can_be_overridden_to_e3nn(tmp_path: Path) -> None:
    cfg, _paths = _write_default(tmp_path, training_acceleration_backend="e3nn")
    assert campaign_cli._acceleration_policy(cfg).backend is mdstats.MaceAccelerationBackend.E3NN
    assert campaign_cli._training_acceleration_policy(cfg).backend is mdstats.MaceAccelerationBackend.E3NN


def test_legacy_configuration_without_training_backend_preserves_unified_backend() -> None:
    cfg = {"acceleration": {"backend": "e3nn", "only_cueq": False, "require_available": True}}
    assert not campaign_cli._phase_separated_acceleration(cfg)
    assert campaign_cli._training_acceleration_policy(cfg).backend is mdstats.MaceAccelerationBackend.E3NN
    cfg["acceleration"]["backend"] = "cueq"
    assert campaign_cli._training_acceleration_policy(cfg).backend is mdstats.MaceAccelerationBackend.CUEQ


def test_init_defaults_training_to_cueq_but_source_to_e3nn(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    assert campaign_cli.main([
        "--config", str(config), "init", "--workspace", "work"
    ]) == 0
    text = config.read_text(encoding="utf-8")
    assert 'backend = "e3nn"' in text
    assert 'training_backend = "cueq"' in text
    cfg, _ = campaign_cli._load_config(config)
    assert campaign_cli._acceleration_policy(cfg).backend is mdstats.MaceAccelerationBackend.E3NN
    assert campaign_cli._training_acceleration_policy(cfg).backend is mdstats.MaceAccelerationBackend.CUEQ


def test_training_realization_roundtrip_and_tamper_guard() -> None:
    record = mdstats.TrainingAccelerationRealizationRecord(
        requested_backend="cueq",
        training_kernel_mode="cueq_pure",
        device="cuda",
        dtype="float32",
        training_checkpoint_reference="selected-head.model",
        training_checkpoint_sha256="a" * 64,
        selected_head_qualification_digest="b" * 64,
        mace_version="0.3.16",
        cueq_versions=(("cuequivariance", "0.test"),),
        training_parity_record_digest="c" * 64,
        qualified=True,
    )
    payload = record.to_dict()
    assert mdstats.TrainingAccelerationRealizationRecord.from_dict(payload) == record
    payload["training_checkpoint_reference"] = "changed.model"
    with pytest.raises(Exception, match="digest mismatch"):
        mdstats.TrainingAccelerationRealizationRecord.from_dict(payload)


def test_phase_separated_default_never_implies_source_cueq() -> None:
    cfg = {
        "acceleration": {
            "backend": "e3nn",
            "training_backend": "cueq",
            "only_cueq": False,
            "require_available": True,
        }
    }
    assert campaign_cli._training_acceleration_policy(cfg).enable_cueq
    assert not campaign_cli._acceleration_policy(cfg).enable_cueq


def test_optimizer_loads_training_realization_not_source_realization(tmp_path: Path) -> None:
    cfg, paths = _write_default(tmp_path)
    checkpoint = tmp_path / "selected-head.model"
    checkpoint.write_bytes(b"selected-head-training-bytes")
    training = mdstats.TrainingAccelerationRealizationRecord(
        requested_backend="cueq",
        training_kernel_mode="cueq_pure",
        device=str(cfg["training"]["device"]),
        dtype=str(cfg["training"]["dtype"]),
        training_checkpoint_reference=str(checkpoint.resolve()),
        training_checkpoint_sha256=campaign_cli._sha256(checkpoint),
        selected_head_qualification_digest="b" * 64,
        mace_version="0.3.16",
        cueq_versions=(("cuequivariance", "test"),),
        training_parity_record_digest="c" * 64,
        qualified=True,
    )
    store = campaign_cli.CampaignStore(paths.state_db)
    store.put_record("training_acceleration_realization", training)
    optimizer = campaign_cli._optimizer_policy(cfg, seed=7, num_workers=0, paths=paths)
    assert optimizer.acceleration_policy.backend is mdstats.MaceAccelerationBackend.CUEQ
    assert optimizer.resolved_acceleration_kernel_mode == "cueq_pure"
    assert optimizer.acceleration_realization_digest == training.content_digest


def test_training_parity_policy_restores_tight_stable_channels_and_separates_force_authority() -> None:
    source = mdstats.MaceAccelerationParityPolicy()
    stable = campaign_cli._training_acceleration_parity_policy()
    force = campaign_cli._training_acceleration_noise_normalized_policy()
    assert source.tolerance("float32") == (1.0e-5, 1.0e-6)
    assert stable.tolerance("float32") == (1.0e-5, 1.0e-6)
    assert stable.tolerance("float64") == source.tolerance("float64")
    assert force.repeat_count == 10
    assert force.warmup_count == 1
    assert force.force_distribution_quantile == 99.0
    assert force.force_distribution_ratio_ceiling == 1.25
    assert force.force_max_self_factor == 1.5
    assert force.force_max_absolute_ceiling == 1.0e-4
    assert force.stable_channel_abs_ceiling == 1.0e-6


def test_train2_force_authority_is_not_the_stable_channel_allclose_ceiling() -> None:
    import numpy as np
    deltas = np.asarray([2.384e-7, 8.911e-6, 1.660e-7, 2.883e-7])
    zeros = np.zeros_like(deltas)
    rtol, atol = campaign_cli._training_acceleration_parity_policy().tolerance("float32")
    assert not np.allclose(deltas, zeros, rtol=rtol, atol=atol)
    # The force component is intentionally not authorized by this one-shot
    # stable-channel policy; it is handled by the noise-normalized all-pairs gate.
    assert campaign_cli._training_acceleration_noise_normalized_policy().force_threshold == 1.0e-5


def test_foundation_contract_phase_separated_keys_match_doctor_contract(tmp_path: Path) -> None:
    cfg, _paths = _write_default(tmp_path)
    contract = campaign_cli._foundation_configuration_contract(cfg)
    assert contract["source_backend"] == "e3nn"
    assert contract["training_backend"] == "cueq"
    assert contract["phase_separated"] is True
    assert "backend" not in contract


def test_historical_selected_head_one_shot_force_envelope_is_no_longer_authorizing() -> None:
    import numpy as np
    deltas = np.asarray([3.576e-7, 1.490e-6, 1.564e-8, 1.570e-6])
    zeros = np.zeros_like(deltas)
    rtol, atol = campaign_cli._training_acceleration_parity_policy().tolerance("float32")
    assert (rtol, atol) == (1.0e-5, 1.0e-6)
    assert not np.allclose(deltas, zeros, rtol=rtol, atol=atol)
    assert campaign_cli._training_acceleration_noise_normalized_policy().force_distribution_ratio_ceiling == 1.25
