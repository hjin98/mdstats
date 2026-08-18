from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest

import mdstats

try:
    import torch as _torch
except ModuleNotFoundError:  # pragma: no cover
    _torch = None

if _torch is not None:
    class _SingleHeadExportModel(_torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.linear = _torch.nn.Linear(1, 1)
            self.heads = ["target_head"]

        def forward(self, x):
            return self.linear(x)


SMOKE_ROOT = Path(os.environ.get('MACE_SMOKE_ROOT', '/mnt/data/work_data9b2/smoke/lta_mpa0_pseudoreplay_smoke_20260730'))


def _h(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _run(target_digest: str, replay_digest: str) -> mdstats.TrainingCampaignRunPlan:
    return mdstats.TrainingCampaignRunPlan(
        run_id='real-mace-smoke',
        data8_bundle_digest=_h('data8'),
        mace_job_artifact_digest=_h('job'),
        job_id='smoke-job',
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=4,
        seed=1,
        protocol_family_digest=_h('family'),
        protocol_variant_digest=_h('variant'),
        protocol_digest=_h('protocol'),
        checkpoint_metric_policy_digest=_h('metric-policy'),
        target_monitor_artifact_digest=target_digest,
        replay_monitor_artifact_digest=replay_digest,
        relative_output_directory='real-smoke',
    )


@pytest.mark.slow
def test_real_multihead_checkpoint_evaluation_and_target_head_export(tmp_path: Path) -> None:
    if not SMOKE_ROOT.is_dir():
        pytest.skip('supplied MACE smoke package not available')
    model = SMOKE_ROOT / 'models' / 'multihead_lta_mpa0_replay_smoke.model'
    target = SMOKE_ROOT / 'data' / 'target_valid.extxyz'
    replay = SMOKE_ROOT / 'data' / 'replay_monitor.extxyz'
    sha = hashlib.sha256(model.read_bytes()).hexdigest()
    from ase.io import read
    target_atoms = read(target, index=":", format="extxyz")
    target_artifact = mdstats.MaceExtxyzArtifact(
        role="checkpoint_monitor",
        relative_path=target.name,
        sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        configuration_count=len(target_atoms),
        frame_uids=tuple(_h(f"target-frame-{i}") for i in range(len(target_atoms))),
        atomic_numbers=tuple(sorted({int(z) for atoms in target_atoms for z in atoms.numbers})),
        policy_digest=_h("target-policy"),
        sidecar_relative_path=target.name + ".manifest.json",
        sidecar_sha256=_h("target-sidecar-file"),
        sidecar_digest=_h("target-sidecar-record"),
    )
    replay_artifact = mdstats.inspect_replay_extxyz(replay)
    run = _run(target_artifact.content_digest, replay_artifact.content_digest)
    checkpoint = mdstats.CheckpointFileRecord(
        run_plan_digest=run.content_digest,
        candidate_id='real-smoke:epoch-0',
        epoch=0,
        relative_path=model.name,
        sha256=sha,
        size_bytes=model.stat().st_size,
    )
    evaluation = mdstats.evaluate_mace_checkpoint(
        run,
        checkpoint,
        candidate_model_path=model,
        target_monitor_path=target,
        target_monitor_artifact=target_artifact,
        replay_monitor_path=replay,
        replay_monitor_artifact=replay_artifact,
        replay_baseline_model_path=model,
        policy=mdstats.CheckpointEvaluationPolicy(condition_keys=()),
    )
    assert evaluation.target_configuration_count == 2
    assert evaluation.replay_configuration_count == 6
    assert evaluation.metric_record.force_component_rmse_ev_per_angstrom == pytest.approx(0.069258, rel=3e-4)
    assert evaluation.metric_record.energy_mae_ev_per_atom < 0.001
    assert evaluation.metric_record.replay_degradation_fraction == pytest.approx(0.0, abs=1e-7)
    assert mdstats.CheckpointEvaluationRecord.from_dict(evaluation.to_dict()) == evaluation

    decision = mdstats.CheckpointAdmissibilityDecision(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=sha,
        checkpoint_metric_record_digest=evaluation.metric_record.content_digest,
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        outcome=mdstats.CheckpointAdmissibilityOutcome.ADMISSIBLE,
        primary_metric_name='target_force_component_rmse',
        primary_metric_value=evaluation.metric_record.force_component_rmse_ev_per_angstrom,
    )
    selection = mdstats.CheckpointSelectionRecord(
        run_plan_digest=run.content_digest,
        checkpoint_catalog_digest=_h('catalog'),
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        decisions=(decision,),
        selected_checkpoint_sha256=sha,
        selected_checkpoint_epoch=0,
        selected_primary_metric_value=evaluation.metric_record.force_component_rmse_ev_per_angstrom,
    )
    output = tmp_path / 'target_head.model'
    member = mdstats.export_target_head_member(
        run,
        selection,
        model,
        output,
        policy=mdstats.CommitteeExportPolicy(minimum_members=1),
    )
    assert output.is_file()
    assert member.byte_size > 0
    assert member.exported_model_sha256 == hashlib.sha256(output.read_bytes()).hexdigest()


def test_target_head_export_is_atomic_on_serialization_failure(tmp_path: Path, monkeypatch) -> None:
    import torch
    from mdstats.training_data import campaign_execution

    if _torch is None:
        pytest.skip("torch unavailable")
    source = tmp_path / "source.model"
    torch.save(_SingleHeadExportModel(), source)
    output = tmp_path / "published.model"
    output.write_bytes(b"previous-valid-model")

    original_save = torch.save

    def fail_save(*args, **kwargs):
        raise RuntimeError("synthetic interrupted serialization")

    monkeypatch.setattr(torch, "save", fail_save)
    with pytest.raises(mdstats.TrainingDataInputError):
        campaign_execution._export_target_head_model(
            source,
            output,
            target_head_name="target_head",
            target_device="cpu",
            wrapper_path=None,
            required_wrapper="mdstats-mace-select-head",
            failure_prefix="test export",
        )
    assert output.read_bytes() == b"previous-valid-model"

    monkeypatch.setattr(torch, "save", original_save)
    campaign_execution._export_target_head_model(
        source,
        output,
        target_head_name="target_head",
        target_device="cpu",
        wrapper_path=None,
        required_wrapper="mdstats-mace-select-head",
        failure_prefix="test export",
    )
    assert output.is_file()
    assert output.read_bytes() != b"previous-valid-model"
