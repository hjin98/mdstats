from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from ase import Atoms

import mdstats
from mdstats.training_data import _campaign_cli_core as campaign_core


def _sha256(path: Path) -> str:
    return campaign_core._sha256(path)


class _Store:
    def __init__(self, records=None):
        self.records = dict(records or {})

    def get_record(self, key, _record_type):
        return self.records[key]

    def get_record_optional(self, key, _record_type):
        return self.records.get(key)

    def put_record(self, key, value):
        self.records[key] = value

    def delete_record(self, key):
        self.records.pop(key, None)


def test_deploy_command_consumer_uses_real_inference_execution_plan(tmp_path, monkeypatch):
    target_path = tmp_path / "target.extxyz"
    target_path.write_bytes(b"target-data")
    checkpoint_path = tmp_path / "checkpoint.pt"
    checkpoint_path.write_bytes(b"checkpoint")
    source_model = tmp_path / "source.model"
    source_model.write_bytes(b"source-model")
    target_model = tmp_path / "target-only.model"
    mliap_path = tmp_path / "target-mliap.pt"
    lammps = tmp_path / "lmp"
    lammps.write_bytes(b"lammps")

    eval2 = SimpleNamespace(
        outcome="selected", selected_checkpoint=object(), content_digest="eval2",
        selected_checkpoint_sha256=_sha256(checkpoint_path), selected_checkpoint_epoch=7,
    )
    store = _Store({"eval2_run:run-0": eval2})
    run = SimpleNamespace(run_id="run-0", content_digest="run-digest")
    checkpoint = SimpleNamespace(
        sha256=_sha256(checkpoint_path), relative_path=checkpoint_path.name, epoch=7,
    )
    catalog = SimpleNamespace(root_directory=str(tmp_path), checkpoints=(checkpoint,))
    artifact = SimpleNamespace(content_digest="artifact", sha256=_sha256(target_path))
    role = SimpleNamespace(content_digest="role")
    probe = SimpleNamespace(
        configuration_indices=(0,), frame_uids=("frame-0",), content_digest="probe",
    )
    atoms = Atoms("Li", cell=[5, 5, 5], pbc=True)
    policy = SimpleNamespace(maximum_probe_configurations=1, tolerances=(1e-9, 1e-10))
    job = SimpleNamespace(
        relative_directory=".", config_relative_path="config.yaml",
        protocol=SimpleNamespace(
            checkpoint_control_policy=SimpleNamespace(target_head_name="target")
        ),
    )
    (tmp_path / "config.yaml").write_text("model: test\n", encoding="utf-8")

    monkeypatch.setattr(campaign_core, "_eval2_target_role_for_run", lambda **kwargs: role)
    monkeypatch.setattr(
        campaign_core, "_eval2_target_artifact_for_run",
        lambda **kwargs: (artifact, target_path),
    )
    monkeypatch.setattr(campaign_core, "_evaluation_checkpoint_catalog", lambda *args: catalog)
    monkeypatch.setattr(campaign_core, "_indexed_target_atoms", lambda **kwargs: {0: atoms})
    monkeypatch.setattr(mdstats, "build_deploy_verify_probe_set", lambda *args, **kwargs: probe)
    monkeypatch.setattr(mdstats, "materialize_mace_checkpoint_model", lambda *args, **kwargs: source_model)

    def export_target(*args, **kwargs):
        target_model.write_bytes(b"target-model")
        return _sha256(target_model), None

    monkeypatch.setattr(mdstats, "export_target_head_model_artifact", export_target)
    monkeypatch.setattr(
        mdstats, "TargetHeadDeploymentIdentity",
        lambda **kwargs: SimpleNamespace(content_digest="deployment-identity"),
    )
    monkeypatch.setattr(mdstats, "target_head_export_digest", lambda **kwargs: "export-digest")
    seen_batch_sizes = []

    def predict(*args, batch_size, **kwargs):
        seen_batch_sizes.append(batch_size)
        return {"energy": np.zeros(1), "forces": np.zeros(3), "stress": np.zeros((1, 3, 3))}

    monkeypatch.setattr(mdstats, "predict_mace_model_on_probe", predict)
    monkeypatch.setattr(
        mdstats, "compare_prediction_channels",
        lambda *args, **kwargs: SimpleNamespace(passed=True),
    )

    def export_mliap(*args, **kwargs):
        mliap_path.write_bytes(b"mliap")
        return mliap_path, "mliap-export"

    monkeypatch.setattr(mdstats, "export_mliap_lammps_artifact", export_mliap)
    run0 = SimpleNamespace(content_digest="run0")
    monkeypatch.setattr(
        mdstats, "run_lammps_mliap_run0",
        lambda *args, **kwargs: (
            {"energy": np.zeros(1), "forces": np.zeros(3), "stress": np.zeros((1, 3, 3))},
            run0,
        ),
    )
    record = SimpleNamespace(content_digest="deploy-record")
    monkeypatch.setattr(mdstats, "DeployVerifyRunRecord", lambda **kwargs: record)

    result = campaign_core._deploy_verify_one_train2_run(
        cfg={"evaluation": {"inference_batch_policy": "fixed", "fixed_inference_batch_size": 5}},
        paths=SimpleNamespace(
            runs=tmp_path / "runs", models=tmp_path / "models", internal=tmp_path / "internal"
        ),
        store=store, run=run, job=job, bundle=object(), root=tmp_path,
        execution=object(), target_size_study=object(), repair2=object(), role_freeze=object(),
        policy=policy, model_dtype="float64", local_wrappers={
            "mdstats-mace-train": tmp_path / "train", "mdstats-mace-select-head": tmp_path / "head"
        },
    )

    assert result is record
    assert seen_batch_sizes[:2] == [5, 5]
    assert store.records["inference_execution_plan:deploy:run-0"].selected_batch_size == 5


def test_pes_command_consumer_uses_real_inference_execution_plan(tmp_path, monkeypatch):
    foundation = tmp_path / "foundation.model"
    foundation.write_bytes(b"foundation")
    candidate = tmp_path / "candidate.model"
    candidate.write_bytes(b"candidate")
    atoms = (Atoms("Li", cell=[5, 5, 5], pbc=True),)
    probe_set = SimpleNamespace(
        content_digest="pes-probes", probes=(SimpleNamespace(probe_uid="probe-0"),)
    )
    request = SimpleNamespace(manifest_path="manifest", extxyz_path="request")
    reference = SimpleNamespace(
        probe_set_digest="pes-probes", reference_path=str(tmp_path / "reference.extxyz"),
        reference_sha256="reference-sha", protocol_digest="protocol", protocol_source="test",
        source_file_sha256s=(),
    )
    Path(reference.reference_path).write_bytes(b"reference")
    reference.reference_sha256 = _sha256(Path(reference.reference_path))
    qualification = SimpleNamespace(passed=True, failed_mode_count=0)
    deploy_probe = SimpleNamespace(
        content_digest="deploy-probe", configuration_indices=(0,),
        target_role_digest="role", target_artifact_digest="artifact", target_artifact_sha256="bytes",
    )
    deploy_run = SimpleNamespace(
        probe_set=deploy_probe, target_only_model_path=str(candidate),
        target_only_model_sha256=_sha256(candidate), run_plan_digest="run-plan",
        content_digest="deploy-run",
    )
    deploy = SimpleNamespace(
        campaign_plan_digest="campaign", target_size_study_digest="study",
        content_digest="deploy", run_records=(deploy_run,), stage_context="production",
    )
    campaign = SimpleNamespace(content_digest="campaign")
    target_study = SimpleNamespace(content_digest="study")
    foundation_audit = SimpleNamespace(
        foundation_checkpoint_sha256=_sha256(foundation), content_digest="foundation-audit",
        foundation_potential_identity=None, foundation_inference_identity=None,
    )
    store = _Store({"pes_verify_reference": reference})

    monkeypatch.setattr(campaign_core, "_load_verified_target_size_study_authority", lambda store: target_study)
    monkeypatch.setattr(campaign_core, "_load_verified_foundation_audit_authority", lambda store: foundation_audit)
    monkeypatch.setattr(campaign_core, "_path_cfg", lambda *args: foundation)
    monkeypatch.setattr(campaign_core, "_pes_verify_common_target", lambda **kwargs: (atoms, object()))
    monkeypatch.setattr(campaign_core, "_material_profile_contracts", lambda cfg: ())
    monkeypatch.setattr(campaign_core, "_canonical_foundation_head", lambda cfg: "foundation")
    monkeypatch.setattr(campaign_core, "_mark_stage", lambda *args, **kwargs: None)
    monkeypatch.setattr(campaign_core, "_atomic_json", lambda *args, **kwargs: None)
    monkeypatch.setattr(campaign_core, "_ok", lambda *args, **kwargs: None)
    monkeypatch.setattr(campaign_core, "_command_verify_train2_relax", lambda *args, **kwargs: 0)
    monkeypatch.setattr(mdstats, "build_pes_probe_set", lambda *args, **kwargs: (probe_set, atoms))
    monkeypatch.setattr(mdstats, "write_pes_probe_request", lambda *args, **kwargs: request)
    monkeypatch.setattr(
        mdstats, "load_pes_reference_extxyz",
        lambda *args, **kwargs: (reference, atoms, {"reference": True}),
    )
    seen_batch_sizes = []

    def predict(*args, batch_size, **kwargs):
        seen_batch_sizes.append(batch_size)
        return {"view": True}

    monkeypatch.setattr(mdstats, "predict_mace_model_on_probe", predict)
    monkeypatch.setattr(mdstats, "prediction_payload_from_mace_view", lambda *args: {"prediction": True})
    monkeypatch.setattr(mdstats, "assess_pes_model", lambda *args, **kwargs: qualification)
    run_record = SimpleNamespace(
        passed=True, run_plan_digest="run-plan", content_digest="pes-run"
    )
    monkeypatch.setattr(mdstats, "PESVerifyRunRecord", lambda **kwargs: run_record)
    authority = SimpleNamespace(
        all_candidates_failed=False, passed_run_count=1, run_records=(run_record,),
        to_dict=lambda: {},
    )
    monkeypatch.setattr(mdstats, "PESVerifyCampaignRecord", lambda **kwargs: authority)

    result = campaign_core._command_verify_train2_pes(
        argparse.Namespace(),
        cfg={"evaluation": {"inference_batch_policy": "fixed", "fixed_inference_batch_size": 6}},
        paths=SimpleNamespace(config_dir=tmp_path, results=tmp_path / "results", internal=tmp_path / "internal"),
        store=store, campaign=campaign, model_dtype="float64", deploy=deploy,
    )

    assert result == 0
    assert seen_batch_sizes == [6, 6]
    assert store.records["inference_execution_plan:pes"].selected_batch_size == 6
    plan = campaign_core._evaluation_inference_execution_plan(
        {"evaluation": {"inference_batch_policy": "fixed", "fixed_inference_batch_size": 6}}
    )
    assert plan.selected_batch_size == 6
    assert not hasattr(plan, "selected_inference_batch_size")
