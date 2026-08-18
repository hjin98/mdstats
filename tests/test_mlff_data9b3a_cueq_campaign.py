from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import sys

import numpy as np
import pytest
import yaml

import mdstats
from mdstats.training_data import campaign_cli
from tests.test_mlff_data8_mace_artifacts import _data7_bundles, _foundation, _probe


def test_acceleration_policy_roundtrip_and_optimizer_identity() -> None:
    acceleration = mdstats.MaceAccelerationPolicy(
        backend=mdstats.MaceAccelerationBackend.CUEQ,
        only_cueq=False,
        require_available=True,
    )
    assert acceleration.enable_cueq
    assert acceleration.calculator_kwargs() == {"enable_cueq": True}
    assert acceleration.training_config() == {"enable_cueq": True, "only_cueq": False}
    assert mdstats.MaceAccelerationPolicy.from_dict(acceleration.to_dict()) == acceleration

    optimizer = mdstats.MaceOptimizerPolicy(
        device="cuda",
        default_dtype="float32",
        acceleration_policy=acceleration,
    )
    restored = mdstats.MaceOptimizerPolicy.from_dict(optimizer.to_dict())
    assert restored == optimizer
    assert restored.acceleration_policy.backend is mdstats.MaceAccelerationBackend.CUEQ


def test_data8_emits_cueq_flags_and_protocol_digest(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    acceleration = mdstats.MaceAccelerationPolicy(backend="cueq")
    result = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / "data8-cueq",
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(
            device="cuda",
            default_dtype="float32",
            max_num_epochs=2,
            acceleration_policy=acceleration,
            acceleration_realization_digest="a" * 64,
            resolved_acceleration_kernel_mode="cueq_pure",
        ),
        require_foundation_residual_e0=False,
    )
    for job in result.jobs:
        payload = yaml.safe_load((Path(result.output_directory) / job.config_relative_path).read_text())
        assert payload["enable_cueq"] is True
        assert payload["enable_oeq"] is False
        assert payload["only_cueq"] is False
        assert job.protocol.optimizer_policy.acceleration_policy == acceleration
        assert job.protocol.optimizer_policy.resolved_acceleration_kernel_mode == "cueq_pure"


def test_init_allows_explicit_cueq_and_freezes_it(tmp_path: Path) -> None:
    config = tmp_path / "campaign.toml"
    assert campaign_cli.main([
        "--config", str(config), "init", "--workspace", "work", "--backend", "cueq"
    ]) == 0
    text = config.read_text(encoding="utf-8")
    assert '[acceleration]' in text
    assert 'backend = "cueq"' in text
    assert 'only_cueq = false' in text
    cfg, _ = campaign_cli._load_config(config)
    assert campaign_cli._acceleration_policy(cfg).enable_cueq


def test_auto_backend_is_rejected_after_initialization() -> None:
    with pytest.raises(campaign_cli.CampaignCliError, match="not permitted"):
        campaign_cli._acceleration_policy({"acceleration": {"backend": "auto"}})


def test_checkpoint_evaluation_policy_carries_cueq() -> None:
    policy = mdstats.CheckpointEvaluationPolicy(
        acceleration_policy=mdstats.MaceAccelerationPolicy(backend="cueq")
    )
    restored = mdstats.CheckpointEvaluationPolicy.from_dict(policy.to_dict())
    assert restored.acceleration_policy.enable_cueq
    assert restored.policy_digest == policy.policy_digest


def test_provider_passes_cueq_to_mace_calculator(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    pytest.importorskip("mace")
    model = tmp_path / "model.model"
    model.write_bytes(b"model")
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model=str(model),
            replay_train="train.xyz",
            replay_monitor="monitor.xyz",
            acceleration_backend="cueq",
        ),
        encoding="utf-8",
    )
    cfg, paths = campaign_cli._load_config(config)
    captured: dict[str, object] = {}

    class FakeCalculator:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def get_descriptors(self, *args, **kwargs):
            return np.zeros((1, 1))

    fake_calculators = SimpleNamespace(MACECalculator=FakeCalculator)
    monkeypatch.setitem(sys.modules, "mace.calculators", fake_calculators)
    monkeypatch.setattr(mdstats, "install_mace_critical_fp64_patch", lambda *a, **k: None)
    potential = mdstats.FoundationPotentialIdentity(
        reference=str(model),
        sha256=campaign_cli._sha256(model),
        foundation_head="omat_pbe",
        model_family="mace_mh_1",
        architecture_signature="a" * 64,
        model_atomic_numbers=(3, 8, 11, 13, 14, 19),
        available_heads=("omol", "omat_pbe"),
        inspection_state="inspected",
    )
    monkeypatch.setattr(campaign_cli, "_resolved_foundation_potential_identity", lambda *a, **k: potential)
    inference = campaign_cli._foundation_inference_identity(
        cfg, potential, adapter_version=mdstats.MACE_ADAPTER_VERSION,
        resolved_kernel_mode="cueq_pure",
    )
    realization = mdstats.AccelerationRealizationRecord(
        requested_backend="cueq", resolved_kernel_mode="cueq_pure",
        training_kernel_mode="cueq_pure", device="cuda", dtype="float32",
        foundation_inference_identity_digest=inference.content_digest,
        mace_version="0.3.16", cueq_versions=(("cueq-core", "test"),),
        inference_parity_record_digest="b" * 64,
        training_parity_record_digest="c" * 64,
        qualified=True,
    )
    monkeypatch.setattr(campaign_cli, "_stored_acceleration_realization", lambda *a, **k: realization)
    _, checkpoint = campaign_cli._provider(cfg, paths)
    assert captured["enable_cueq"] is True
    assert captured["enable_oeq"] is False
    assert captured["head"] == "omat_pbe"
    assert checkpoint.foundation_head == "omat_pbe"
    assert dict(checkpoint.metadata)["acceleration_backend"] == "cueq"


def test_campaign_policy_binds_acceleration_probe_digest() -> None:
    probe_digest = "a" * 64
    policy = mdstats.TrainingCampaignPolicy(acceleration_probe_digest=probe_digest)
    restored = mdstats.TrainingCampaignPolicy.from_dict(policy.to_dict())
    assert restored.acceleration_probe_digest == probe_digest


def test_doctor_selects_periodic_replay_geometry_for_cueq_stress_smoke(tmp_path: Path) -> None:
    from ase import Atoms
    from ase.io import write

    replay = tmp_path / "replay.extxyz"
    isolated = Atoms("He", positions=[[0.0, 0.0, 0.0]], pbc=False)
    periodic = Atoms(
        "NaCl",
        positions=[[0.0, 0.0, 0.0], [2.5, 2.5, 2.5]],
        cell=[5.0, 5.0, 5.0],
        pbc=True,
    )
    write(replay, [isolated, periodic], format="extxyz")
    config = tmp_path / "campaign.toml"
    config.write_text(
        campaign_cli._config_template(
            workspace="work",
            training_root="training",
            foundation_model="model.model",
            replay_train=str(replay),
            replay_monitor=str(replay),
            acceleration_backend="cueq",
        ),
        encoding="utf-8",
    )
    cfg, paths = campaign_cli._load_config(config)
    selected = campaign_cli._doctor_sample_atoms(cfg, paths)
    assert selected is not None
    assert bool(np.all(selected.pbc))
    assert selected.get_chemical_formula() == "ClNa"
