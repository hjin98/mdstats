from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import hashlib

import numpy as np
import pytest

import mdstats
from mdstats.training_data import deploy_verify as dv


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _probe() -> mdstats.DeployVerifyProbeSet:
    return mdstats.DeployVerifyProbeSet(
        target_role_digest=_h("role"),
        target_artifact_digest=_h("artifact"),
        target_artifact_sha256=_h("artifact-bytes"),
        frame_uids=(_h("frame"),),
        correlation_block_ids=(_h("block"),),
        configuration_indices=(0,),
    )


def _comparison() -> mdstats.DeployVerifyComparison:
    return mdstats.compare_prediction_channels(
        {"energy": np.asarray([1.0]), "forces": np.asarray([0.0, 1.0, 2.0])},
        {"energy": np.asarray([1.0]), "forces": np.asarray([0.0, 1.0, 2.0])},
        reference_identity="reference",
        observed_identity="observed",
        rtol=1e-5,
        atol=1e-6,
    )


def _identity() -> mdstats.TargetHeadDeploymentIdentity:
    return mdstats.TargetHeadDeploymentIdentity(
        run_plan_digest=_h("run"),
        eval2_run_record_digest=_h("eval2"),
        source_model_sha256=_h("trained-multihead"),
        target_model_sha256=_h("learned-target"),
        target_head="target_head",
        deployment_dtype="float64",
    )


def test_deploy1_target_identity_is_role_explicit_and_not_foundation_extraction() -> None:
    identity = _identity()
    assert identity.source_artifact_role == "trained_candidate_multihead"
    assert identity.target_artifact_role == "learned_target_head"
    assert mdstats.TargetHeadDeploymentIdentity.from_dict(identity.to_dict()) == identity
    with pytest.raises(mdstats.TrainingDataInputError, match="trained candidate"):
        mdstats.TargetHeadDeploymentIdentity(
            run_plan_digest=_h("run"),
            eval2_run_record_digest=_h("eval2"),
            source_model_sha256=_h("mh1-foundation"),
            target_model_sha256=_h("extract1-omat-pbe"),
            target_head="omat_pbe",
            deployment_dtype="float64",
            source_artifact_role="foundation_multihead",
            target_artifact_role="selected_foundation_head",
        )


def test_deploy1_v2_export_digest_binds_learned_target_identity_and_preserves_v1() -> None:
    identity = _identity()
    legacy = mdstats.target_head_export_digest(
        source_model_sha256=identity.source_model_sha256,
        target_model_sha256=identity.target_model_sha256,
        target_head=identity.target_head,
        deployment_dtype=identity.deployment_dtype,
    )
    canonical = mdstats.target_head_export_digest(
        source_model_sha256=identity.source_model_sha256,
        target_model_sha256=identity.target_model_sha256,
        target_head=identity.target_head,
        deployment_dtype=identity.deployment_dtype,
        target_head_deployment_identity_digest=identity.content_digest,
    )
    assert canonical != legacy


def test_deploy1_run_v2_binds_target_and_mliap_to_learned_target_identity() -> None:
    identity = _identity()
    probe = _probe()
    comp = _comparison()
    run0 = mdstats.LammpsRun0Record(
        executable_path="/opt/lmp",
        executable_sha256=_h("lmp"),
        command_arguments=("-k", "on"),
        mliap_artifact_sha256=_h("mliap"),
        element_order=("Li", "O"),
        probe_set_digest=probe.content_digest,
        predictions_sha256=_h("pred"),
    )
    record = mdstats.DeployVerifyRunRecord(
        run_plan_digest=identity.run_plan_digest,
        eval2_run_record_digest=identity.eval2_run_record_digest,
        policy=mdstats.DeployVerifyPolicy(model_dtype="float64"),
        probe_set=probe,
        selected_checkpoint_sha256=_h("checkpoint"),
        selected_checkpoint_epoch=1,
        selected_checkpoint_model_sha256=identity.source_model_sha256,
        target_head_name=identity.target_head,
        target_only_model_path="target.model",
        target_only_model_sha256=identity.target_model_sha256,
        target_head_export_digest=mdstats.target_head_export_digest(
            source_model_sha256=identity.source_model_sha256,
            target_model_sha256=identity.target_model_sha256,
            target_head=identity.target_head,
            deployment_dtype=identity.deployment_dtype,
            target_head_deployment_identity_digest=identity.content_digest,
        ),
        mliap_artifact_path="target.model-mliap_lammps.pt",
        mliap_artifact_sha256=_h("mliap"),
        mliap_export_digest=_h("mliap-export"),
        checkpoint_to_target_comparison=comp,
        target_to_lammps_comparison=comp,
        lammps_run0=run0,
        target_head_deployment_identity=identity,
        mliap_source_identity_digest=identity.content_digest,
    )
    assert record.to_dict()["schema"] == "mdstats.deploy-verify-run.v2"
    assert mdstats.DeployVerifyRunRecord.from_dict(record.to_dict()) == record

    with pytest.raises(mdstats.TrainingDataInputError, match="ML-IAP source identity"):
        mdstats.DeployVerifyRunRecord(
            **{
                **{k: getattr(record, k) for k in record.__dataclass_fields__ if k not in {"mliap_source_identity_digest", "serialization_schema"}},
                "mliap_source_identity_digest": _h("wrong-role"),
            }
        )


def test_deploy1_mliap_export_digest_binds_learned_target_identity(tmp_path: Path, monkeypatch) -> None:
    target = tmp_path / "learned-target.model"
    target.write_bytes(b"learned-target")
    identity = _identity()

    def fake_run(command, **kwargs):
        staged = Path(command[3])
        Path(str(staged) + "-mliap_lammps.pt").write_bytes(b"mliap")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dv.subprocess, "run", fake_run)
    _, legacy = mdstats.export_mliap_lammps_artifact(
        target,
        tmp_path / "legacy",
        model_dtype="float64",
        target_head="target_head",
        require_runtime_capability=False,
    )
    _, canonical = mdstats.export_mliap_lammps_artifact(
        target,
        tmp_path / "canonical",
        model_dtype="float64",
        target_head="target_head",
        source_identity_digest=identity.content_digest,
        require_runtime_capability=False,
    )
    assert legacy != canonical


def test_deploy1_real_mliap_runtime_probe_fails_closed_without_cueq() -> None:
    capability = mdstats.probe_mliap_export_runtime("/mnt/data/mh1_gate11_env/bin/python")
    if capability.mace_version != "0.3.16":
        pytest.skip("locked MACE 0.3.16 deployment runtime is not mounted")
    assert not capability.passed
    assert "cuequivariance_unavailable" in capability.failure_reasons
    assert "cuequivariance_torch_unavailable" in capability.failure_reasons
    assert mdstats.MliapExportRuntimeCapability.from_dict(capability.to_dict()) == capability
