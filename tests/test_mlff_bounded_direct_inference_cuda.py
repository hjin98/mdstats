"""Real-provider CUDA evidence for the bounded direct-EVAL2 execution boundary.

The blocker this closes was a CUDA out-of-memory: the exact-``M`` evaluation
population was handed to ``predict_batch`` as one native derivative-bearing
graph batch, so peak VRAM scaled with the boundary's scientific size. A CPU test
cannot establish that claim - it has no VRAM to run out of - so this suite
executes the production direct-inference owner against a **real authenticated
MACE checkpoint on the GPU**, with no forward override anywhere, and records
what the device actually did.

It is a bounded smoke, not production qualification: a tiny architecture, one
candidate, and a handful of frames. The claim under test is structural - the
population is partitioned before native graph materialization, one authenticated
provider state serves every chunk, and the evidence is unchanged - and that
claim does not need a production-scale workload to be established.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

pytestmark = pytest.mark.skipif(
    not torch.cuda.is_available(),
    reason="the VRAM claim is only meaningful on a CUDA device",
)

from mace.tools.checkpoint import CheckpointHandler, CheckpointState  # noqa: E402

import tests.test_mlff_target_size_execution_p3c as p3c  # noqa: E402
import tests.test_mlff_target_size_execution_p3d as p3d  # noqa: E402
import tests.test_mlff_target_size_execution_p3e as p3e  # noqa: E402
from mdstats.training_data._common import digest  # noqa: E402
from mdstats.training_data.model_features import (  # noqa: E402
    MaceCalculatorProvider,
    _AuthenticatedParameterShell,
    build_mace_model_from_configuration,
    mace_model_execution_architecture_digest,
)
from mdstats.training_data.target_size_execution import (  # noqa: E402
    bind_target_size_boundary_state,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    evaluate_target_size_boundary,
    materialize_target_size_candidate,
    project_target_size_candidate_preparation,
    promote_target_size_boundary_snapshot,
    run_target_size_direct_boundary_inference,
    target_size_rung_plan,
    write_target_size_evaluation_artifact,
)
from mdstats.training_data.target_size_execution.context import (  # noqa: E402
    build_target_size_execution_context,
)
from mdstats.training_data.train2_runtime import _tensor_state_digest  # noqa: E402

#: The boundary whose exact-M population exceeds the bound below.
_BOUNDARY = 3
#: Deliberately narrower than that population, so chunking must happen.
_VALID_BATCH_SIZE = 1


def _real_boundary(
    trajectory, plan, checkpoint_directory: Path, mace_config_path: Path
):
    """Publish a real MACE checkpoint as this rung's durable TRAIN2 state.

    The rung runtime, companion, and summary come from the production TRAIN2
    persistence owner; only the raw checkpoint bytes are replaced with a real
    model of the candidate's own architecture, which is what makes the provider
    reconstruct an actual MACE model instead of a parameter shell.
    """

    model = build_mace_model_from_configuration(
        json.loads(mace_config_path.read_text(encoding="utf-8"))
    )
    architecture_digest = mace_model_execution_architecture_digest(model)

    _runtime, base_summary, _restored, _rng = p3c._run_rung(
        plan,
        checkpoint_directory,
        start_epoch=0,
        updates_per_epoch=trajectory.realization.updates_per_epoch,
        seed=int(trajectory.optimizer_seed),
    )

    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    lr_scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.99)
    tag = "model_run-7"
    handler = CheckpointHandler(directory=str(checkpoint_directory), tag=tag, keep=True)
    handler.save(
        state=CheckpointState(model, optimizer, lr_scheduler),
        epochs=_BOUNDARY - 1,
        keep_last=True,
    )
    live = [parameter.detach().cpu().clone() for parameter in model.parameters()]

    raw_path = checkpoint_directory / f"{tag}_epoch-{_BOUNDARY - 1}.pt"
    raw_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    live_digest = _tensor_state_digest(
        live, schema="mdstats.train2-live-parameters.v1"
    )

    companion_path = checkpoint_directory / "train2_runtime.pt"
    companion = torch.load(companion_path, map_location="cpu", weights_only=False)
    companion["raw_checkpoint_sha256"] = raw_sha
    companion["live_parameters"] = live
    companion["ema_state"] = None
    companion["model_architecture_digest"] = architecture_digest
    torch.save(companion, companion_path)

    summary = replace(
        base_summary,
        raw_checkpoint_sha256=raw_sha,
        optimizer_state_digest=digest(
            {
                "schema": "mdstats.train2-optimizer-state-reference.v1",
                "raw_checkpoint_sha256": raw_sha,
                "training_protocol_digest": plan.training_protocol_digest,
                "optimizer_policy_digest": plan.optimizer_policy_digest,
                "completed_updates": base_summary.completed_updates,
            }
        ),
        live_parameter_digest=live_digest,
        ema_state_digest=None,
        model_architecture_digest=architecture_digest,
    )
    (checkpoint_directory / "train2_runtime.json").write_text(
        json.dumps(summary.to_dict(), sort_keys=True), encoding="utf-8"
    )
    return summary, live_digest


def test_real_mace_cuda_direct_eval2_is_bounded_and_unchanged(
    tmp_path: Path, monkeypatch, capsys
):
    env = p3e._env(tmp_path)
    definition = env["aggregate"].definition
    schedule = env["schedule"]
    boundary_index = schedule.fidelity_epochs.index(_BOUNDARY)
    evaluation_size = int(definition.policy.evaluation_sizes[boundary_index])
    assert evaluation_size > _VALID_BATCH_SIZE, (
        "the smoke is meaningless unless the population exceeds the batch bound"
    )

    optimizer_policy = replace(
        env["optimizer"],
        device="cuda",
        valid_batch_size=_VALID_BATCH_SIZE,
        ema=False,
    )
    context = build_target_size_execution_context(
        definition,
        env["common"],
        schedule,
        seed_neutral_optimizer_policy=optimizer_policy,
    )
    target_size = definition.qualified_candidate_sizes[0]
    trajectory = build_target_size_candidate_trajectory(
        definition,
        context,
        env["common"],
        schedule,
        target_size=int(target_size),
        optimizer_policy=optimizer_policy,
        optimizer_seed=int(definition.policy.optimizer_seeds[0]),
    )

    materialization_directory = tmp_path / "materialization"
    materialization_directory.mkdir(parents=True, exist_ok=True)
    materialization = materialize_target_size_candidate(
        trajectory,
        project_target_size_candidate_preparation(
            env["common"], definition, int(target_size)
        ),
        env["common"],
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        output_directory=materialization_directory,
        optimizer_policy=optimizer_policy,
        extxyz_policy=env["authority"].extxyz_policy,
        frame_array_index=env["index"],
    )
    checkpoint_directory = tmp_path / "cuda-boundary"
    checkpoint_directory.mkdir(parents=True, exist_ok=True)
    plan = target_size_rung_plan(trajectory, schedule, boundary_epoch=_BOUNDARY)
    summary, live_digest = _real_boundary(
        trajectory,
        plan,
        checkpoint_directory,
        materialization_directory / materialization.mace_config_relative_path,
    )

    boundary_state = bind_target_size_boundary_state(
        trajectory, schedule, summary, checkpoint_directory=checkpoint_directory
    )
    snapshot = promote_target_size_boundary_snapshot(
        trajectory,
        boundary_state,
        checkpoint_directory=checkpoint_directory,
        snapshot_root=env["root"],
    )
    evaluation_directory = tmp_path / "evaluation"
    evaluation_directory.mkdir(parents=True, exist_ok=True)
    evaluation_data = write_target_size_evaluation_artifact(
        evaluation_directory,
        definition=definition,
        evaluation_size=evaluation_size,
        canonical_frame_authority=env["frame_authority"],
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )
    role = build_target_size_eval2_role(
        trajectory=trajectory,
        boundary_state=snapshot,
        definition=definition,
        schedule=schedule,
        correlation_blocks=env["blocks"],
        evaluation_data=evaluation_data,
    )

    # Observe the real provider without replacing it: every native device batch
    # this records is one the production owner actually submitted.
    widths: list[int] = []
    providers: list[object] = []
    real_predict_batch = MaceCalculatorProvider.predict_batch

    def _observing(provider, atoms_batch, **kwargs):
        widths.append(len(atoms_batch))
        providers.append(provider)
        return real_predict_batch(provider, atoms_batch, **kwargs)

    def _forbid_shell(*args, **kwargs):
        raise AssertionError("the CUDA smoke must not fall back to a parameter shell")

    monkeypatch.setattr(MaceCalculatorProvider, "predict_batch", _observing)
    monkeypatch.setattr(
        MaceCalculatorProvider, "from_authenticated_parameter_state", _forbid_shell
    )

    device_name = torch.cuda.get_device_name(0)
    free_before, total = torch.cuda.mem_get_info()
    torch.cuda.reset_peak_memory_stats()

    evidence = run_target_size_direct_boundary_inference(
        trajectory=trajectory,
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=evaluation_data,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=context,
        common=env["common"],
        schedule=schedule,
        optimizer_policy=optimizer_policy,
        materialization_directory=materialization_directory,
        snapshot_root=env["root"],
        evaluation_directory=evaluation_directory,
        root_directory=env["root"],
        extxyz_policy=env["authority"].extxyz_policy,
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
    )

    peak_allocated = torch.cuda.max_memory_allocated()
    peak_reserved = torch.cuda.max_memory_reserved()

    # The population was partitioned before native graph materialization.
    assert widths, "the real provider never received a device batch"
    assert max(widths) <= _VALID_BATCH_SIZE
    assert sum(widths) == evaluation_size
    assert len(widths) > 1, "a population larger than the bound ran as one batch"
    # One authenticated provider state served every chunk of the role.
    assert len({id(item) for item in providers}) == 1
    provider = providers[0]
    assert not isinstance(provider.model, _AuthenticatedParameterShell)

    # Scientific content is untouched by how it was scheduled onto the device.
    assert evidence.prediction_count == evaluation_size
    assert evidence.evaluation_size == evaluation_size
    assert evidence.role_digest == role.content_digest
    assert evidence.evaluated_model_state_digest == live_digest
    assert evidence.device == provider.device == "cuda"
    assert evidence.default_dtype == provider.default_dtype

    # The reduction accepts this evidence exactly as it accepts CPU evidence.
    metric = evaluate_target_size_boundary(
        role, evaluation_data, evidence, root_directory=evaluation_directory
    )
    assert metric.boundary_epoch == _BOUNDARY
    assert metric.evaluation_membership_digest == (
        evaluation_data.evaluation_membership_digest
    )
    assert metric.target_force_rmse_mev_per_a >= 0.0

    with capsys.disabled():
        print(
            "\n[cuda direct-EVAL2 smoke] "
            f"device={device_name}; "
            f"total={total / 1024 ** 3:.2f} GiB; "
            f"free_before={free_before / 1024 ** 3:.2f} GiB; "
            f"valid_batch_size={_VALID_BATCH_SIZE}; "
            f"population={evaluation_size}; "
            f"observed_chunk_widths={widths}; "
            f"peak_allocated={peak_allocated / 1024 ** 2:.1f} MiB; "
            f"peak_reserved={peak_reserved / 1024 ** 2:.1f} MiB"
        )
