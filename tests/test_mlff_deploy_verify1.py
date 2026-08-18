from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from ase import Atoms

import mdstats
from mdstats.training_data import deploy_verify as dv


def _h(text: str) -> str:
    import hashlib
    return hashlib.sha256(text.encode()).hexdigest()


def _role() -> SimpleNamespace:
    frames = tuple(_h(f"frame-{i}") for i in range(8))
    blocks = (_h("b0"), _h("b0"), _h("b0"), _h("b1"), _h("b1"), _h("b2"), _h("b3"), _h("b3"))
    return SimpleNamespace(
        content_digest=_h("role"),
        evaluation_frame_uids=frames,
        correlation_block_ids=blocks,
    )


def _comparison(a: float = 0.0) -> mdstats.DeployVerifyComparison:
    return mdstats.compare_prediction_channels(
        {"energy": np.array([1.0]), "forces": np.array([0.0, 1.0, 2.0])},
        {"energy": np.array([1.0 + a]), "forces": np.array([0.0, 1.0, 2.0 + a])},
        reference_identity="source",
        observed_identity="target",
        rtol=1e-5,
        atol=1e-6,
    )


def test_probe_set_is_deterministic_and_block_balanced():
    role = _role()
    probe = mdstats.build_deploy_verify_probe_set(
        role,
        target_artifact_digest=_h("artifact"),
        target_artifact_sha256=_h("bytes"),
        maximum_configurations=4,
    )
    assert len(probe.frame_uids) == 4
    assert len(set(probe.correlation_block_ids)) == 4
    assert probe == mdstats.build_deploy_verify_probe_set(
        role,
        target_artifact_digest=_h("artifact"),
        target_artifact_sha256=_h("bytes"),
        maximum_configurations=4,
    )
    assert mdstats.DeployVerifyProbeSet.from_dict(probe.to_dict()) == probe


def test_prediction_comparison_requires_energy_and_forces_and_detects_mismatch():
    assert _comparison(0.0).passed
    bad = _comparison(1e-2)
    assert not bad.passed
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.compare_prediction_channels(
            {"energy": np.array([1.0])}, {"energy": np.array([1.0])},
            reference_identity="a", observed_identity="b", rtol=1e-5, atol=1e-6,
        )


def test_policy_roundtrip_and_dtype_tolerances():
    p32 = mdstats.DeployVerifyPolicy(model_dtype="float32")
    p64 = mdstats.DeployVerifyPolicy(model_dtype="float64")
    assert p32.tolerances == (1e-5, 1e-6)
    assert p64.tolerances == (1e-9, 1e-10)
    assert mdstats.DeployVerifyPolicy.from_dict(p32.to_dict()) == p32


def test_run_record_binds_probe_mliap_and_both_parity_layers():
    probe = mdstats.build_deploy_verify_probe_set(
        _role(), target_artifact_digest=_h("artifact"), target_artifact_sha256=_h("bytes"), maximum_configurations=3
    )
    comp = _comparison(0.0)
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
        run_plan_digest=_h("run"), eval2_run_record_digest=_h("eval2"),
        policy=mdstats.DeployVerifyPolicy(model_dtype="float32"), probe_set=probe,
        selected_checkpoint_sha256=_h("ckpt"), selected_checkpoint_epoch=29,
        selected_checkpoint_model_sha256=_h("whole"), target_head_name="target_head",
        target_only_model_path="target.model", target_only_model_sha256=_h("target"),
        target_head_export_digest=mdstats.target_head_export_digest(source_model_sha256=_h("whole"), target_model_sha256=_h("target"), target_head="target_head", deployment_dtype="float32"),
        mliap_artifact_path="target.model-mliap_lammps.pt", mliap_artifact_sha256=_h("mliap"),
        mliap_export_digest=_h("export"), checkpoint_to_target_comparison=comp,
        target_to_lammps_comparison=comp, lammps_run0=run0,
    )
    assert record.passed
    assert mdstats.DeployVerifyRunRecord.from_dict(record.to_dict()) == record
    campaign = mdstats.DeployVerifyCampaignRecord(
        campaign_plan_digest=_h("campaign"), target_size_convergence_digest=_h("conv"),
        run_records=(record,), stage_context="production",
    )
    assert mdstats.DeployVerifyCampaignRecord.from_dict(campaign.to_dict()) == campaign


def test_target_head_export_identity_is_recomputed_and_fail_closed():
    probe = mdstats.build_deploy_verify_probe_set(
        _role(), target_artifact_digest=_h("artifact"), target_artifact_sha256=_h("bytes"), maximum_configurations=2
    )
    comp = _comparison(0.0)
    run0 = mdstats.LammpsRun0Record(
        executable_path="/opt/lmp", executable_sha256=_h("lmp"), command_arguments=(),
        mliap_artifact_sha256=_h("mliap"), element_order=("Li",),
        probe_set_digest=probe.content_digest, predictions_sha256=_h("pred"),
    )
    with pytest.raises(mdstats.TrainingDataInputError, match="target-head export identity"):
        mdstats.DeployVerifyRunRecord(
            run_plan_digest=_h("run"), eval2_run_record_digest=_h("eval2"),
            policy=mdstats.DeployVerifyPolicy(model_dtype="float32"), probe_set=probe,
            selected_checkpoint_sha256=_h("ckpt"), selected_checkpoint_epoch=29,
            selected_checkpoint_model_sha256=_h("whole"), target_head_name="target_head",
            target_only_model_path="target.model", target_only_model_sha256=_h("target"),
            target_head_export_digest=_h("tampered-export"),
            mliap_artifact_path="mliap.pt", mliap_artifact_sha256=_h("mliap"),
            mliap_export_digest=_h("export"), checkpoint_to_target_comparison=comp,
            target_to_lammps_comparison=comp, lammps_run0=run0,
        )


def test_failed_comparison_cannot_be_frozen():
    probe = mdstats.build_deploy_verify_probe_set(
        _role(), target_artifact_digest=_h("artifact"), target_artifact_sha256=_h("bytes"), maximum_configurations=2
    )
    run0 = mdstats.LammpsRun0Record(
        executable_path="/opt/lmp", executable_sha256=_h("lmp"), command_arguments=(),
        mliap_artifact_sha256=_h("mliap"), element_order=("Li",),
        probe_set_digest=probe.content_digest, predictions_sha256=_h("pred"),
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.DeployVerifyRunRecord(
            run_plan_digest=_h("run"), eval2_run_record_digest=_h("eval2"),
            policy=mdstats.DeployVerifyPolicy(model_dtype="float32"), probe_set=probe,
            selected_checkpoint_sha256=_h("ckpt"), selected_checkpoint_epoch=29,
            selected_checkpoint_model_sha256=_h("whole"), target_head_name="target_head",
            target_only_model_path="target.model", target_only_model_sha256=_h("target"),
            target_head_export_digest=mdstats.target_head_export_digest(source_model_sha256=_h("whole"), target_model_sha256=_h("target"), target_head="target_head", deployment_dtype="float32"),
            mliap_artifact_path="mliap.pt", mliap_artifact_sha256=_h("mliap"),
            mliap_export_digest=_h("export"), checkpoint_to_target_comparison=_comparison(1e-2),
            target_to_lammps_comparison=_comparison(0.0), lammps_run0=run0,
        )


def test_lammps_run0_contract_parses_energy_forces_and_stress(tmp_path: Path, monkeypatch):
    executable = tmp_path / "lmp"
    executable.write_bytes(b"fake-lammps")
    executable.chmod(0o755)
    mliap = tmp_path / "mliap.pt"
    mliap.write_bytes(b"mliap")
    target = tmp_path / "target.model"
    target.write_bytes(b"target")
    atoms = Atoms("LiO", positions=[[0, 0, 0], [1.5, 0, 0]], cell=[5, 5, 5], pbc=True)
    monkeypatch.setattr(dv, "_model_element_order", lambda path: ("Li", "O"))

    def fake_run(command, cwd, **kwargs):
        cwd = Path(cwd)
        (cwd / "metrics.txt").write_text("-3.0 1 2 3 4 5 6\n")
        (cwd / "forces.dump").write_text(
            "ITEM: TIMESTEP\n0\nITEM: NUMBER OF ATOMS\n2\nITEM: BOX BOUNDS pp pp pp\n0 5\n0 5\n0 5\n"
            "ITEM: ATOMS id type fx fy fz\n2 2 4 5 6\n1 1 1 2 3\n"
        )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(dv.subprocess, "run", fake_run)
    predictions, record = mdstats.run_lammps_mliap_run0(
        mliap, target, (atoms,), probe_set_digest=_h("probe"),
        lammps_executable=executable, work_directory=tmp_path / "run0",
    )
    assert predictions["energy"].tolist() == [-3.0]
    assert predictions["forces"].tolist() == [1, 2, 3, 4, 5, 6]
    assert predictions["stress"].shape == (1, 3, 3)
    assert record.probe_set_digest == _h("probe")
