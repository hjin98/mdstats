from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib.util
import json
import os

import pytest

import mdstats
from mdstats.training_data import campaign_cli, campaign_execution, production_model_sweep
from mdstats.training_data._common import TrainingDataInputError


MH1_MODEL = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
MPA0_MODEL = Path(os.environ.get("MDSTATS_TEST_MPA0_MODEL", "/mnt/data/mace-mpa-0-medium.model"))
MH1_SHA256 = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
MPA0_SHA256 = "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"


def _bound_identity(*, head: str, backend: str = "e3nn") -> mdstats.ModelCheckpointIdentity:
    potential = mdstats.FoundationPotentialIdentity(
        reference="/model/mh1.model",
        sha256="1" * 64,
        foundation_head=head,
        model_family="mace_mh_1",
        architecture_signature="2" * 64,
        model_atomic_numbers=(3, 8, 11, 17),
        available_heads=("omol", "omat_pbe"),
        inspection_state="inspected",
    )
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend=backend,
        resolved_kernel_mode="e3nn" if backend == "e3nn" else "cueq_unresolved",
        mace_version="0.3.16",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    acceleration = mdstats.MaceAccelerationPolicy(backend=backend)
    return mdstats.ModelCheckpointIdentity(
        model_family="mace_mh_1",
        checkpoint_locator="/model/mh1.model",
        checkpoint_sha256="1" * 64,
        calculator_class="mace.calculators.MACECalculator",
        model_version="MACE-MH-1",
        supported_atomic_numbers=(3, 8, 11, 17),
        model_supported_atomic_numbers=(3, 8, 11, 17),
        requested_atomic_numbers=(3, 8, 11),
        foundation_potential_digest=potential.canonical_content_digest,
        foundation_inference_digest=inference.content_digest,
        foundation_head=head,
        device="cpu",
        default_dtype="float32",
        metadata=(("acceleration_policy_digest", acceleration.policy_digest),),
    )


def _bound_foundation_contract(*, head: str = "omat_pbe", backend: str = "e3nn"):
    potential = mdstats.FoundationPotentialIdentity(
        reference="/model/mh1.model",
        sha256="1" * 64,
        foundation_head=head,
        model_family="mace_mh_1",
        architecture_signature="2" * 64,
        model_atomic_numbers=(3, 8, 11, 17),
        available_heads=("omol", "omat_pbe"),
        inspection_state="inspected",
    )
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend=backend,
        resolved_kernel_mode="e3nn" if backend == "e3nn" else "cueq_unresolved",
        mace_version="0.3.16",
        adapter_version=mdstats.MACE_ADAPTER_VERSION,
    )
    return potential, inference


def test_inf1_model_checkpoint_v2_is_head_and_execution_aware() -> None:
    omat = _bound_identity(head="omat_pbe")
    omol = _bound_identity(head="omol")
    cueq = _bound_identity(head="omat_pbe", backend="cueq")
    assert omat.to_dict()["schema"] == "mdstats.model-checkpoint-identity.v2"
    assert omat.foundation_bound
    assert omat.foundation_head == "omat_pbe"
    assert omat.model_supported_atomic_numbers == (3, 8, 11, 17)
    assert omat.requested_atomic_numbers == (3, 8, 11)
    assert omat.content_digest != omol.content_digest
    assert omat.content_digest != cueq.content_digest
    assert mdstats.ModelCheckpointIdentity.from_dict(omat.to_dict()) == omat


def test_inf1_legacy_v1_model_identity_round_trip_remains_digest_stable() -> None:
    fixture = Path(__file__).parent / "fixtures" / "mlff_mh1_base0_legacy_mpa0.json"
    payload = json.loads(fixture.read_text(encoding="utf-8"))["model_checkpoint_identity_e3nn"]
    restored = mdstats.ModelCheckpointIdentity.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored.serialization_schema == "mdstats.model-checkpoint-identity.v1"
    assert not restored.foundation_bound


def test_inf1_data6_prediction_reuse_accepts_matching_explicit_head(monkeypatch: pytest.MonkeyPatch) -> None:
    identity = _bound_identity(head="omat_pbe")
    potential, inference = _bound_foundation_contract(head="omat_pbe", backend="e3nn")
    policy = mdstats.CheckpointEvaluationPolicy(
        device="cpu",
        default_dtype="float32",
        replay_baseline_head_name=None,
        foundation_potential_identity=potential,
        foundation_inference_identity=inference,
        acceleration_policy=mdstats.MaceAccelerationPolicy(backend="e3nn"),
    )
    manifest = SimpleNamespace(checkpoint_identity=identity, content_digest="3" * 64)
    sentinel = SimpleNamespace(energy_ev=-1.0)
    monkeypatch.setattr(production_model_sweep, "read_atomic_model_prediction", lambda *a, **k: sentinel)
    matched = campaign_execution._data6_foundation_predictions(
        manifest,
        "/unused",
        ("f0",),
        baseline_sha256=identity.checkpoint_sha256,
        head="omat_pbe",
        policy=policy,
    )
    assert matched is not None and matched[0] == (sentinel,)
    assert campaign_execution._data6_foundation_predictions(
        manifest,
        "/unused",
        ("f0",),
        baseline_sha256=identity.checkpoint_sha256,
        head="omol",
        policy=policy,
    ) is None


def test_inf1_foundation_bound_provider_cannot_switch_heads() -> None:
    class Calc:
        available_heads = ("omol", "omat_pbe")
        head = "omat_pbe"
        def get_descriptors(self, *args, **kwargs):
            return []
    provider = mdstats.MaceCalculatorProvider.from_calculator(
        Calc(), checkpoint_identity=_bound_identity(head="omat_pbe")
    )
    provider.set_head("omat_pbe")
    with pytest.raises(TrainingDataInputError, match="frozen to head"):
        provider.set_head("omol")


@pytest.mark.slow
def test_inf1_real_mh1_and_mpa0_provider_and_named_head_e0(tmp_path: Path) -> None:
    if importlib.util.find_spec("mace") is None:
        pytest.skip("real MACE environment is not active")
    if not (MH1_MODEL.is_file() and MPA0_MODEL.is_file()):
        pytest.skip("locked MH-1/MPA-0 checkpoints are not mounted")
    assert hashlib.sha256(MH1_MODEL.read_bytes()).hexdigest() == MH1_SHA256
    assert hashlib.sha256(MPA0_MODEL.read_bytes()).hexdigest() == MPA0_SHA256

    def load_cfg(model: Path, family: str, head: str):
        cfg_path = tmp_path / f"{family}-{head}.toml"
        cfg_path.write_text(
            campaign_cli._config_template(
                workspace=str(tmp_path / f"work-{family}-{head}"),
                training_root=str(tmp_path / "training"),
                foundation_model=str(model),
                replay_train=str(tmp_path / "train.xyz"),
                replay_monitor=str(tmp_path / "monitor.xyz"),
                replay_true_labels=str(tmp_path / "true"),
                foundation_family=family,
                foundation_head=head,
                acceleration_backend="e3nn",
                default_device="cpu",
            ),
            encoding="utf-8",
        )
        return campaign_cli._load_config(cfg_path)

    cfg, paths = load_cfg(MH1_MODEL, "mace_mh_1", "omat_pbe")
    identity = campaign_cli._model_checkpoint_identity(cfg, paths)
    assert identity.checkpoint_sha256 == MH1_SHA256
    assert identity.foundation_head == "omat_pbe"
    assert len(identity.model_supported_atomic_numbers) == 89
    assert set(identity.requested_atomic_numbers).issubset(identity.model_supported_atomic_numbers)
    provider, returned = campaign_cli._provider(cfg, paths, checkpoint_identity=identity)
    assert returned.content_digest == identity.content_digest
    assert provider._calculator.head == "omat_pbe"

    potential = campaign_cli._resolved_foundation_potential_identity(cfg, paths)
    omat_e0 = campaign_cli._extract_foundation_e0(
        MH1_MODEL, (3, 8, 11, 17), foundation_identity=potential
    )
    cfg_omol, paths_omol = load_cfg(MH1_MODEL, "mace_mh_1", "omol")
    potential_omol = campaign_cli._resolved_foundation_potential_identity(cfg_omol, paths_omol)
    omol_e0 = campaign_cli._extract_foundation_e0(
        MH1_MODEL, (3, 8, 11, 17), foundation_identity=potential_omol
    )
    assert any(abs(omat_e0[z] - omol_e0[z]) > 1.0e-12 for z in omat_e0)
    assert campaign_cli._model_checkpoint_identity(cfg_omol, paths_omol).content_digest != identity.content_digest

    cfg_mpa, paths_mpa = load_cfg(MPA0_MODEL, "mace_mpa_0", "default")
    mpa_identity = campaign_cli._model_checkpoint_identity(cfg_mpa, paths_mpa)
    assert mpa_identity.checkpoint_sha256 == MPA0_SHA256
    assert mpa_identity.foundation_head == "default"
    mpa_provider, _ = campaign_cli._provider(cfg_mpa, paths_mpa, checkpoint_identity=mpa_identity)
    assert mpa_provider._calculator.head == "default"


@pytest.mark.slow
def test_inf1_invalid_mh1_head_fails_before_calculator_construction(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if importlib.util.find_spec("mace") is None or not MH1_MODEL.is_file():
        pytest.skip("real MACE environment/checkpoint unavailable")
    cfg_path = tmp_path / "bad.toml"
    cfg_path.write_text(
        campaign_cli._config_template(
            workspace=str(tmp_path / "work"), training_root=str(tmp_path / "training"),
            foundation_model=str(MH1_MODEL), replay_train="train.xyz", replay_monitor="monitor.xyz",
            replay_true_labels="true", foundation_family="mace_mh_1", foundation_head="not_a_head",
            acceleration_backend="e3nn", default_device="cpu",
        ), encoding="utf-8"
    )
    cfg, paths = campaign_cli._load_config(cfg_path)
    import mace.calculators
    called = False
    original = mace.calculators.MACECalculator
    class Trap:
        def __init__(self, *args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("calculator must not be reached")
    monkeypatch.setattr(mace.calculators, "MACECalculator", Trap)
    with pytest.raises(campaign_cli.CampaignCliError, match="unavailable"):
        campaign_cli._provider(cfg, paths)
    assert called is False
    monkeypatch.setattr(mace.calculators, "MACECalculator", original)
