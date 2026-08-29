"""P3-C gate evidence: paired TRAIN2 execution through the real runtime,
exact completed-epoch boundary semantics (including n1 = 1), exact
continuation ancestry, and the authenticated failure adapter."""

from __future__ import annotations

import random
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from torch_ema import ExponentialMovingAverage

import mdstats
import tests.test_mlff_target_size_execution_p3a as p3a
from mdstats.training_data import train2_runtime as runtime_mod
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TargetSizeCandidateTrajectory,
    TargetSizeContinuationRequest,
    bind_target_size_boundary_state,
    build_target_size_candidate_trajectory,
    build_target_size_screen_schedule,
    continuation_request_from_boundary,
    initial_target_size_continuation_request,
    load_target_size_boundary_state,
    target_size_evaluation_membership_digest_for_boundary,
    target_size_rung_plan,
    translate_target_size_train2_failure,
    validate_target_size_continuation_request,
)
from mdstats.training_data.target_size_experiment import NumericalFailureKind
from mdstats.training_data.train2_runtime import Train2NumericalFailureRecord
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)


def _env(tmp_path: Path):
    manifest, fa, nb, aggregate, common, index = p3a._common(tmp_path)
    schedule = build_target_size_screen_schedule((1, 3, 10))
    optimizer = MaceOptimizerPolicy(
        max_num_epochs=schedule.n3, batch_size=4, device="cpu"
    )
    context = build_target_size_execution_context(
        aggregate.definition, common, schedule, seed_neutral_optimizer_policy=optimizer
    )
    n = aggregate.definition.qualified_candidate_sizes[0]
    trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=n,
        optimizer_policy=optimizer,
        optimizer_seed=1,
    )
    return aggregate, common, schedule, context, trajectory, optimizer


def _raw_checkpoint(directory: Path, epoch: int) -> Path:
    path = directory / f"model_run-7_epoch-{epoch}.pt"
    torch.save({"epoch": epoch}, path)
    return path


class _NoStepScheduler:
    def step(self, *args, **kwargs) -> None:
        del args, kwargs


def _step(model, optimizer, ema) -> None:
    optimizer.zero_grad(set_to_none=True)
    loss = sum((parameter ** 2).sum() for parameter in model.parameters())
    loss.backward()
    optimizer.step()
    ema.update()


def _run_rung(
    plan,
    checkpoint_dir: Path,
    *,
    start_epoch: int,
    updates_per_epoch: int,
    seed: int,
):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    metrics = checkpoint_dir.parent / "metrics.jsonl"
    if not metrics.is_file():
        metrics.write_text("", encoding="utf-8")
    handler = SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir)))
    train_loader = [object()] * updates_per_epoch
    model = torch.nn.Linear(3, 2, dtype=torch.float64)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4, momentum=0.9)
    ema = ExponentialMovingAverage(model.parameters(), decay=0.95)
    runtime = runtime_mod._Train2Runtime(
        plan,
        model=model,
        optimizer=optimizer,
        lr_scheduler=_NoStepScheduler(),
        ema=ema,
        train_loader=train_loader,
        current_epoch=start_epoch,
        checkpoint_handler=handler,
        logger_path=str(metrics),
        rank=0,
    )
    # Post-restore (pre-training) state of this rung.
    restored_state = [p.detach().clone() for p in model.parameters()]
    restored_torch_rng = torch.get_rng_state()
    for epoch in range(start_epoch, plan.execution_epoch_limit):
        for _ in train_loader:
            _step(model, optimizer, ema)
        _raw_checkpoint(checkpoint_dir, epoch)
        summary = runtime.persist_epoch(epoch=epoch)
        assert summary is not None
        assert runtime.should_pause_after_epoch(epoch) == (
            epoch + 1 >= plan.execution_epoch_limit
        )
    return runtime, summary, restored_state, restored_torch_rng


def _run_full_screen(env, tmp_path: Path):
    aggregate, common, schedule, context, trajectory, optimizer = env
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    updates = trajectory.realization.updates_per_epoch
    states = {}
    start = 0
    for boundary in schedule.fidelity_epochs:
        plan = target_size_rung_plan(
            trajectory, schedule, boundary_epoch=boundary
        )
        runtime, summary, _restored, _r = _run_rung(
            plan,
            checkpoint_dir,
            start_epoch=start,
            updates_per_epoch=updates,
            seed=1,
        )
        # A boundary state is authenticated while that boundary is the latest
        # durable TRAIN2 state, exactly as the coordinator would bind it.
        states[boundary] = bind_target_size_boundary_state(
            trajectory, schedule, summary, checkpoint_directory=checkpoint_dir
        )
        start = boundary
    return checkpoint_dir, states


def test_p3c_full_n3_schedule_with_rung_pause_limits(tmp_path: Path) -> None:
    aggregate, common, schedule, context, trajectory, optimizer = _env(tmp_path)
    plans = {
        boundary: target_size_rung_plan(
            trajectory, schedule, boundary_epoch=boundary
        )
        for boundary in schedule.fidelity_epochs
    }
    n1, n2, n3 = schedule.fidelity_epochs
    # One frozen budget/LR trajectory; the pause limit is the only variation.
    assert all(
        plan.budget_policy.policy_digest == plans[n1].budget_policy.policy_digest
        and plan.learning_rate_policy.policy_digest
        == plans[n1].learning_rate_policy.policy_digest
        and plan.training_protocol_digest == trajectory.candidate_training_protocol_digest
        and plan.optimizer_policy_digest == trajectory.seed_neutral_training_policy_digest
        and plan.structures_per_epoch == trajectory.realization.structures_per_epoch
        for plan in plans.values()
    )
    assert [plan.execution_epoch_limit for plan in plans.values()] == [n1, n2, n3]
    assert len({plan.content_digest for plan in plans.values()}) == 3
    # Non-rung limits are structurally unreachable.
    with pytest.raises(mdstats.TrainingDataInputError):
        target_size_rung_plan(trajectory, schedule, boundary_epoch=n2 + 1)


def test_p3c_completed_epoch_boundary_semantics_including_n1_equals_one(
    tmp_path: Path,
) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    checkpoint_dir, states = _run_full_screen(env, tmp_path)
    assert schedule.fidelity_epochs[0] == 1
    # The terminal boundary can always be reloaded from durable state.
    terminal = schedule.fidelity_epochs[-1]
    reloaded = load_target_size_boundary_state(
        trajectory,
        schedule,
        boundary_epoch=terminal,
        checkpoint_directory=checkpoint_dir,
    )
    assert reloaded.content_digest == states[terminal].content_digest
    for boundary, state in states.items():
        summary = state.rung_runtime_summary
        # C2 frozen semantics: completed epochs, active limit, raw epoch.
        assert state.boundary_epoch == boundary
        assert summary.completed_epochs == boundary
        assert summary.execution_epoch_limit == boundary
        assert summary.raw_checkpoint_epoch == boundary - 1
        # The off-by-one case n1 = 1 -> raw_checkpoint_epoch = 0.
        if boundary == 1:
            assert summary.raw_checkpoint_epoch == 0
        # Model/optimizer/EMA/RNG/update/LR ancestry is authenticated.
        assert summary.ema_state_digest is not None
        assert trajectory.evaluation_model_state == "ema"
        assert summary.optimizer_state_digest
        assert summary.rng_state_digest
        assert summary.completed_updates == boundary * summary.updates_per_epoch
        assert summary.last_update_index == summary.completed_updates - 1
        # Serialization round-trips the authenticated boundary state.
        from mdstats.training_data.target_size_execution import (
            TargetSizeBoundaryState,
        )

        assert (
            TargetSizeBoundaryState.from_dict(state.to_dict()).content_digest
            == state.content_digest
        )


def test_p3c_exact_continuation_ancestry_and_evaluation_parent(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    updates = trajectory.realization.updates_per_epoch
    n1, n2, n3 = schedule.fidelity_epochs
    # Rung 1: initialization -> n1.
    plan1 = target_size_rung_plan(trajectory, schedule, boundary_epoch=n1)
    runtime1, summary1, _initial_state, _rng0 = _run_rung(
        plan1, checkpoint_dir, start_epoch=0, updates_per_epoch=updates, seed=1
    )
    boundary1 = bind_target_size_boundary_state(
        trajectory, schedule, summary1, checkpoint_directory=checkpoint_dir
    )
    live_before = [p.detach().clone() for p in runtime1.model.parameters()]
    torch_state_before = torch.get_rng_state()
    # The exact same authenticated boundary state is the continuation parent.
    request = continuation_request_from_boundary(boundary1)
    predecessor = validate_target_size_continuation_request(
        request,
        trajectory,
        schedule,
        checkpoint_directory=checkpoint_dir,
    )
    assert predecessor.content_digest == summary1.content_digest
    # Rung 2 resumes the exact predecessor state, never the foundation.
    plan2 = target_size_rung_plan(trajectory, schedule, boundary_epoch=n2)
    # Perturb the process RNG before resume: a fresh-seed reinitialization
    # would survive; the runtime must restore the persisted RNG stream.
    for _ in range(7):
        torch.rand(())
    assert not torch.equal(torch_state_before, torch.get_rng_state())
    runtime2, summary2, resumed_initial, restored_rng = _run_rung(
        plan2, checkpoint_dir, start_epoch=n1, updates_per_epoch=updates, seed=1
    )
    # The resumed rung started exactly from the authenticated boundary state.
    for before, after in zip(live_before, resumed_initial):
        assert torch.allclose(before, after)
    # RNG state was restored from the exact persisted boundary stream,
    # never reinitialized by orchestration.
    assert torch.equal(torch_state_before, restored_rng)
    assert summary2.completed_epochs == n2
    assert summary2.completed_updates == n2 * updates
    # Restart-after-boundary: a fresh process-style resume of n2 works.
    boundary2 = bind_target_size_boundary_state(
        trajectory, schedule, summary2, checkpoint_directory=checkpoint_dir
    )
    request2 = continuation_request_from_boundary(boundary2)
    validated = validate_target_size_continuation_request(
        request2, trajectory, schedule, checkpoint_directory=checkpoint_dir
    )
    assert validated.content_digest == summary2.content_digest
    # Rung 3 completes the full screen.
    plan3 = target_size_rung_plan(trajectory, schedule, boundary_epoch=n3)
    runtime3, summary3, _restored3, _r3 = _run_rung(
        plan3, checkpoint_dir, start_epoch=n2, updates_per_epoch=updates, seed=1
    )
    assert summary3.completed_epochs == n3
    assert summary3.complete_budget
    # The terminal boundary has no later rung.
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_continuation_request(
            continuation_request_from_boundary(
                bind_target_size_boundary_state(
                    trajectory,
                    schedule,
                    summary3,
                    checkpoint_directory=checkpoint_dir,
                )
            ),
            trajectory,
            schedule,
            checkpoint_directory=checkpoint_dir,
        )


def test_p3c_foreign_trajectory_or_predecessor_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    definition = aggregate.definition
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    updates = trajectory.realization.updates_per_epoch
    n1, n2, _n3 = schedule.fidelity_epochs
    plan1 = target_size_rung_plan(trajectory, schedule, boundary_epoch=n1)
    _runtime1, summary1, _restored, _r = _run_rung(
        plan1, checkpoint_dir, start_epoch=0, updates_per_epoch=updates, seed=1
    )
    # A different seed is a foreign trajectory even with identical shapes.
    other = build_target_size_candidate_trajectory(
        definition,
        context,
        common,
        schedule,
        target_size=trajectory.target_size,
        optimizer_policy=replace(optimizer, seed=2),
        optimizer_seed=2,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_continuation_request(
            TargetSizeContinuationRequest(
                trajectory_digest=other.content_digest,
                predecessor_boundary_epoch=n1,
            ),
            trajectory,
            schedule,
            checkpoint_directory=checkpoint_dir,
        )
    # A different N is a foreign trajectory.
    sizes = sorted(definition.qualified_candidate_sizes)
    if len(sizes) > 1:
        bigger = build_target_size_candidate_trajectory(
            definition,
            context,
            common,
            schedule,
            target_size=sizes[-1],
            optimizer_policy=optimizer,
            optimizer_seed=1,
        )
        with pytest.raises(mdstats.TrainingDataInputError):
            validate_target_size_continuation_request(
                TargetSizeContinuationRequest(
                    trajectory_digest=bigger.content_digest,
                    predecessor_boundary_epoch=n1,
                ),
                trajectory,
                schedule,
                checkpoint_directory=checkpoint_dir,
            )
    # A non-boundary predecessor is rejected.
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_continuation_request(
            TargetSizeContinuationRequest(
                trajectory_digest=trajectory.content_digest,
                predecessor_boundary_epoch=n1 + 1,
            ),
            trajectory,
            schedule,
            checkpoint_directory=checkpoint_dir,
        )
    # An initialization request has nothing to resume.
    with pytest.raises(mdstats.TrainingDataInputError):
        validate_target_size_continuation_request(
            initial_target_size_continuation_request(trajectory),
            trajectory,
            schedule,
            checkpoint_directory=checkpoint_dir,
        )
    # A stale/foreign summary is not accepted as boundary evidence.
    forged = replace(summary1, completed_epochs=n1 + 1)
    with pytest.raises(mdstats.TrainingDataInputError):
        bind_target_size_boundary_state(
            trajectory, schedule, forged, checkpoint_directory=checkpoint_dir
        )


def test_p3c_wrong_checkpoint_or_representation_rejected(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    updates = trajectory.realization.updates_per_epoch
    n1 = schedule.fidelity_epochs[0]
    plan1 = target_size_rung_plan(trajectory, schedule, boundary_epoch=n1)
    _runtime1, summary1, _restored, _r = _run_rung(
        plan1, checkpoint_dir, start_epoch=0, updates_per_epoch=updates, seed=1
    )
    state = bind_target_size_boundary_state(
        trajectory, schedule, summary1, checkpoint_directory=checkpoint_dir
    )
    # Tampered raw checkpoint bytes fail closed.
    raw = checkpoint_dir / f"model_run-7_epoch-{n1 - 1}.pt"
    original = raw.read_bytes()
    raw.write_bytes(original + b"x")
    with pytest.raises(mdstats.TrainingDataInputError):
        load_target_size_boundary_state(
            trajectory,
            schedule,
            boundary_epoch=n1,
            checkpoint_directory=checkpoint_dir,
        )
    raw.write_bytes(original)
    # A boundary summary produced under a different rung limit is rejected.
    wrong_limit = replace(summary1, execution_epoch_limit=schedule.fidelity_epochs[1])
    with pytest.raises(mdstats.TrainingDataInputError):
        bind_target_size_boundary_state(
            trajectory,
            schedule,
            wrong_limit,
            checkpoint_directory=checkpoint_dir,
        )
    # An EMA-evaluated trajectory cannot bind EMA-free boundary state.
    no_ema = replace(summary1, ema_state_digest=None)
    with pytest.raises((mdstats.TrainingDataInputError, TypeError)):
        bind_target_size_boundary_state(
            trajectory, schedule, no_ema, checkpoint_directory=checkpoint_dir
        )
    # The frozen evaluation representation is derived from the policy, and
    # every candidate uses the same convention.
    from mdstats.training_data.target_size_execution import (
        target_size_evaluation_model_state,
    )

    assert target_size_evaluation_model_state(optimizer) == "ema"
    live_trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        build_target_size_execution_context(
            aggregate.definition,
            common,
            schedule,
            seed_neutral_optimizer_policy=replace(optimizer, ema=False),
        ),
        common,
        schedule,
        target_size=trajectory.target_size,
        optimizer_policy=replace(optimizer, ema=False, seed=1),
        optimizer_seed=1,
    )
    assert live_trajectory.evaluation_model_state == "live"
    assert target_size_evaluation_model_state(replace(optimizer, ema=False)) == "live"


def _failure_record(trajectory, schedule, boundary, *, code, failed_epoch, rung_plan=None):
    plan = rung_plan or target_size_rung_plan(
        trajectory, schedule, boundary_epoch=boundary
    )
    return Train2NumericalFailureRecord(
        failure_code=code,
        reason="authenticated numerical failure",
        failed_epoch=failed_epoch,
        completed_updates=(failed_epoch * trajectory.realization.updates_per_epoch) + 1,
        planned_updates=trajectory.realization.planned_updates,
        execution_epoch_limit=boundary,
        plan_digest=plan.content_digest,
        training_protocol_digest=trajectory.candidate_training_protocol_digest,
        optimizer_policy_digest=trajectory.seed_neutral_training_policy_digest,
        budget_policy_digest=schedule.budget_policy.policy_digest,
        lr_policy_digest=schedule.learning_rate_policy.policy_digest,
        raw_checkpoint_name=f"model_run-7_epoch-{failed_epoch}.pt",
        raw_checkpoint_sha256="a" * 64,
    )


def test_p3c_authenticated_failure_mapping(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    definition = aggregate.definition
    n1 = schedule.fidelity_epochs[0]
    model_failure = translate_target_size_train2_failure(
        _failure_record(
            trajectory, schedule, n1, code="train_nonfinite_model_state", failed_epoch=0
        ),
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=n1,
    )
    assert model_failure.kind is NumericalFailureKind.TRAIN_NONFINITE_MODEL_STATE
    assert model_failure.boundary_epoch == n1
    assert model_failure.target_size == trajectory.target_size
    assert model_failure.optimizer_seed == trajectory.optimizer_seed
    assert model_failure.evaluation_membership_digest == (
        target_size_evaluation_membership_digest_for_boundary(
            definition, schedule, n1
        )
    )
    # EMA failure science is model-state, never optimizer-state.
    ema_failure = translate_target_size_train2_failure(
        _failure_record(
            trajectory, schedule, n1, code="train_nonfinite_ema_state", failed_epoch=0
        ),
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=n1,
    )
    assert ema_failure.kind is NumericalFailureKind.TRAIN_NONFINITE_MODEL_STATE
    assert ema_failure.kind is not NumericalFailureKind.TRAIN_NONFINITE_OPTIMIZER_STATE
    assert ema_failure.content_digest != model_failure.content_digest
    # Optimizer-state science requires a real owner authenticating it; the
    # current TRAIN2 record taxonomy cannot even express it.
    with pytest.raises(mdstats.TrainingDataInputError):
        _failure_record(
            trajectory,
            schedule,
            n1,
            code="train_nonfinite_optimizer_state",
            failed_epoch=0,
        )
    # Evidence is bound to the exact attempt: a different real failure
    # location yields different classification evidence.
    other_location = translate_target_size_train2_failure(
        _failure_record(
            trajectory, schedule, n1, code="train_nonfinite_model_state", failed_epoch=0,
            rung_plan=target_size_rung_plan(trajectory, schedule, boundary_epoch=n1),
        ),
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=n1,
    )
    assert other_location.content_digest == model_failure.content_digest
    moved = translate_target_size_train2_failure(
        _failure_record(
            trajectory, schedule, schedule.fidelity_epochs[1],
            code="train_nonfinite_model_state", failed_epoch=1,
        ),
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=schedule.fidelity_epochs[1],
    )
    assert moved.content_digest != model_failure.content_digest


def test_p3c_pre_boundary_failure_binds_scheduled_boundary(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    definition = aggregate.definition
    n2 = schedule.fidelity_epochs[1]
    # Authenticated failure occurred mid-attempt to reach n2 (real location:
    # epoch 1, 1 update in); the scientific failure binds the scheduled
    # boundary without claiming the candidate reached it.
    record = _failure_record(
        trajectory, schedule, n2, code="train_nonfinite_model_state", failed_epoch=1
    )
    assert record.completed_updates < n2 * trajectory.realization.updates_per_epoch
    failure = translate_target_size_train2_failure(
        record,
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=n2,
    )
    assert failure.boundary_epoch == n2
    # The evidence digest retains the real failure location.
    same_location = translate_target_size_train2_failure(
        replace(
            record,
            reason="another authenticated numerical failure",
        ),
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=n2,
    )
    assert same_location.content_digest != failure.content_digest
    earlier = _failure_record(
        trajectory, schedule, n2, code="train_nonfinite_model_state", failed_epoch=0
    )
    earlier_failure = translate_target_size_train2_failure(
        earlier,
        trajectory=trajectory,
        definition=definition,
        schedule=schedule,
        scheduled_boundary_epoch=n2,
    )
    assert earlier_failure.content_digest != failure.content_digest


def test_p3c_execution_errors_produce_no_scientific_failure(tmp_path: Path) -> None:
    env = _env(tmp_path)
    aggregate, common, schedule, context, trajectory, optimizer = env
    definition = aggregate.definition
    n1 = schedule.fidelity_epochs[0]
    # A record that does not bind this trajectory's rung plan is an
    # execution error, not scientific evidence.
    foreign = _failure_record(
        trajectory, schedule, n1, code="train_nonfinite_model_state", failed_epoch=0
    )
    foreign_plan = replace(
        foreign,
        plan_digest="b" * 64,
    )
    with pytest.raises(mdstats.TrainingDataInputError):
        translate_target_size_train2_failure(
            foreign_plan,
            trajectory=trajectory,
            definition=definition,
            schedule=schedule,
            scheduled_boundary_epoch=n1,
        )
    # A failure record for another boundary is an execution error here.
    with pytest.raises(mdstats.TrainingDataInputError):
        translate_target_size_train2_failure(
            foreign,
            trajectory=trajectory,
            definition=definition,
            schedule=schedule,
            scheduled_boundary_epoch=schedule.fidelity_epochs[1],
        )
    # Corrupt restart state remains an execution error.
    checkpoint_dir = tmp_path / "missing"
    checkpoint_dir.mkdir()
    with pytest.raises(mdstats.TrainingDataInputError):
        load_target_size_boundary_state(
            trajectory,
            schedule,
            boundary_epoch=n1,
            checkpoint_directory=checkpoint_dir,
        )
