from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import json
import os
import tomllib

import numpy as np
import pytest
from ase import Atoms

import mdstats
from mdstats.training_data import campaign_cli


FIXTURE = Path(__file__).parent / "fixtures" / "mlff_mh1_base0_legacy_mpa0.json"
EVIDENCE = Path(__file__).parents[1] / "audits" / "analysis" / "mlff_mh1_base0_mpa0_regression_evidence.json"
MPA0_MODEL = Path(os.environ.get("MDSTATS_TEST_MPA0_MODEL", "/mnt/data/mace-mpa-0-medium.model"))
FIXTURE_SHA256 = "c22d60aa95d3e8cdca3ab688c9333d9ea026f91db4a5a7c856f9a8c4f98a38a2"
MPA0_SHA256 = "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"


def _fixture() -> dict:
    raw = FIXTURE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FIXTURE_SHA256
    return json.loads(raw)


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text())


def test_base0_legacy_payload_fixture_is_authenticated_and_round_trips() -> None:
    payload = _fixture()
    assert payload["schema"] == "mdstats.mh1-base0-legacy-mpa0-fixtures.v1"
    assert payload["mace_mpa0_sha256"] == MPA0_SHA256

    foundation = mdstats.FoundationCheckpointIdentity.from_dict(payload["foundation_checkpoint_identity"])
    assert foundation.model_family == "MACE-MPA-0"
    assert foundation.foundation_head == "default"
    assert foundation.sha256 == MPA0_SHA256

    for backend in ("e3nn", "cueq"):
        model = mdstats.ModelCheckpointIdentity.from_dict(payload[f"model_checkpoint_identity_{backend}"])
        acceleration = mdstats.MaceAccelerationPolicy.from_dict(payload[f"acceleration_policy_{backend}"])
        evaluation = mdstats.CheckpointEvaluationPolicy.from_dict(payload[f"evaluation_policy_{backend}"])
        assert model.model_family == "MACE-MPA-0"
        assert model.checkpoint_sha256 == MPA0_SHA256
        assert dict(model.metadata)["acceleration_backend"] == backend
        assert acceleration.backend.value == backend
        assert evaluation.acceleration_policy.backend.value == backend
        assert evaluation.target_head_name == "target_head"
        assert evaluation.replay_head_name == "pt_head"
        assert evaluation.replay_baseline_head_name == "pt_head"

    replay = mdstats.ReplayPreparationPlan.from_dict(payload["replay_plan"])
    assert replay.mode is mdstats.ReplayMode.EXTERNAL_PSEUDOLABEL
    assert replay.ready_for_fixed_file_training
    assert replay.train_artifact is not None and replay.monitor_artifact is not None
    assert replay.train_artifact.foundation_checkpoint_digest == MPA0_SHA256
    assert replay.monitor_artifact.foundation_checkpoint_digest == MPA0_SHA256

    deploy = mdstats.DeployVerifyPolicy.from_dict(payload["deploy_verify_policy_fp32"])
    assert deploy.tolerances == (1.0e-5, 1.0e-6)
    assert payload["target_head_export_digest"] == mdstats.target_head_export_digest(
        source_model_sha256="7" * 64,
        target_model_sha256="8" * 64,
        target_head="target_head",
        deployment_dtype="float32",
    )


def test_base0_current_config_template_freezes_explicit_mpa0_e3nn_and_cueq_semantics() -> None:
    evidence = _evidence()
    for backend in ("e3nn", "cueq"):
        text = campaign_cli._config_template(
            workspace="mlff-campaign",
            training_root="/target",
            foundation_model="/fixtures/mace-mpa-0-medium.model",
            replay_train="/fixtures/replay_train.xyz",
            replay_monitor="/fixtures/replay_monitor.xyz",
            foundation_family="mace_mpa_0",
            foundation_head="default",
            acceleration_backend=backend,
            default_device="cuda",
            precision_profile="single",
        )
        cfg = tomllib.loads(text)
        expected = evidence[f"config_template_{backend}"]
        assert cfg["campaign"]["id"] == expected["campaign_id"] == "lta-mpa0-finetune"
        assert cfg["model"]["foundation_name"] == expected["foundation_name"] == "MPA-0-medium"
        assert cfg["model"]["dtype"] == expected["dtype"] == "float32"
        assert cfg["acceleration"]["backend"] == backend
        assert cfg["acceleration"]["only_cueq"] is False
        assert cfg["acceleration"]["require_available"] is True
        assert cfg["training"]["multihead_replay"] == expected["training_multihead_replay"]
        assert cfg["evaluation"]["replay_baseline_head"] == expected["evaluation_replay_baseline_head"] == ""
        assert cfg["verification"]["pes_foundation_head"] == ""


def test_base0_synthetic_pipeline_fingerprints_cover_data6_through_deployment_contracts() -> None:
    evidence = _evidence()
    schemas = evidence["current_schemas"]
    assert schemas == {
        "foundation_checkpoint_identity": "mdstats.foundation-checkpoint-identity.v2",
        "model_checkpoint_identity": "mdstats.model-checkpoint-identity.v1",
        "mace_descriptor_manifest": "mdstats.mace-descriptor-manifest.v1",
        "fitted_feature_metric": "mdstats.fitted-feature-metric.v2",
        "replay_file_artifact": "mdstats.replay-file-artifact.v3",
        "replay_preparation_plan": "mdstats.replay-preparation-plan.v3",
        "data8_preparation_bundle": "mdstats.data8-preparation-bundle.v5",
        "checkpoint_evaluation_policy": "mdstats.checkpoint-evaluation-policy.v5",
        "production_materialization_plan": "mdstats.production-materialization-plan.v6",
    }
    synthetic = evidence["synthetic_pipeline"]
    assert synthetic["data6_bundle_digest"] == "5efb745fd2f317a40053962b822300b36eee898f10b633d8ec7c952a20ce24c9"
    assert synthetic["data6_descriptor_manifest_digest"] == "a07b8fd183bde4aefeba3a0a1a7b0988af10377375a380795788efde9638de28"
    assert synthetic["data6_prediction_manifest_digest"] == "15fc7556dd9f90ac08ec1ca3e917c8d61b1f73cb5f1a017dadef70ccdb3c194e"
    assert synthetic["data7_final_metric_shape"] == [36, 77]
    assert synthetic["data7_selection_sizes"] == [8, 16, 24]
    assert synthetic["data8_e3nn_config"]["foundation_head"] == "default"
    assert synthetic["data8_e3nn_config"]["enable_cueq"] is False
    assert synthetic["data8_cueq_config"]["foundation_head"] == "default"
    assert synthetic["data8_cueq_config"]["enable_cueq"] is True
    assert synthetic["data8_cueq_config"]["only_cueq"] is False
    assert synthetic["production_materialization_plan_schema"] == "mdstats.production-materialization-plan.v5"
    assert evidence["cueq_numeric_status"].startswith("not_run_in_BASE0")


@pytest.mark.slow
def test_base0_real_mpa0_e3nn_numeric_reference() -> None:
    if importlib.util.find_spec("mace") is None:
        pytest.skip("real MACE environment is not active")
    if not MPA0_MODEL.is_file():
        pytest.skip("locked MPA-0 checkpoint is not mounted")
    assert hashlib.sha256(MPA0_MODEL.read_bytes()).hexdigest() == MPA0_SHA256

    from mace.calculators import MACECalculator

    evidence = _evidence()["real_mpa0_e3nn_numeric_reference"]
    structure = evidence["structure"]
    base = Atoms(
        numbers=structure["atomic_numbers"],
        positions=np.asarray(structure["positions_angstrom"], dtype=float),
        cell=np.asarray(structure["cell_angstrom"], dtype=float),
        pbc=structure["pbc"],
    )
    for dtype in ("float32", "float64"):
        atoms = base.copy()
        calc = MACECalculator(
            model_paths=str(MPA0_MODEL),
            head="default",
            device="cpu",
            default_dtype=dtype,
            enable_cueq=False,
        )
        atoms.calc = calc
        energy = float(atoms.get_potential_energy())
        forces = np.asarray(atoms.get_forces(), dtype=float)
        descriptor = np.asarray(calc.get_descriptors(atoms, invariants_only=True))
        expected = evidence[dtype]
        atol = 2.0e-6 if dtype == "float32" else 2.0e-10
        assert energy == pytest.approx(expected["energy_ev"], rel=0.0, abs=atol)
        assert float(np.sqrt(np.mean(forces * forces))) == pytest.approx(
            expected["force_rms_ev_per_angstrom"], rel=0.0, abs=atol
        )
        assert float(np.max(np.abs(forces))) == pytest.approx(
            expected["force_abs_max_ev_per_angstrom"], rel=0.0, abs=atol
        )
        assert list(descriptor.shape) == expected["descriptor_shape"] == [6, 256]
        assert float(descriptor.sum()) == pytest.approx(expected["descriptor_sum"], rel=0.0, abs=5.0e-6 if dtype == "float32" else 5.0e-10)
        assert float(np.sqrt(np.mean(descriptor * descriptor))) == pytest.approx(
            expected["descriptor_rms"], rel=0.0, abs=5.0e-7 if dtype == "float32" else 5.0e-11
        )
        observed_sha = hashlib.sha256(descriptor.astype("<f8").tobytes()).hexdigest()
        assert observed_sha == expected["descriptor_f64_bytes_sha256"]
