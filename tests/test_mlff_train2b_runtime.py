from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
import json
import random

import numpy as np
import pytest
import torch
from torch_ema import ExponentialMovingAverage

import mdstats
from mdstats.training_data import train2_runtime as runtime_mod
from mdstats.training_data import critical_precision_cli


def _h(ch: str) -> str:
    return (ch * 64)[:64]


class _Scheduler:
    def __init__(self) -> None:
        self.calls = 0

    def step(self, *args, **kwargs) -> None:
        del args, kwargs
        self.calls += 1


def _plan(*, limit: int, base_lr: float = 1.0e-4) -> mdstats.Train2RuntimePlan:
    return mdstats.Train2RuntimePlan(
        training_protocol_digest=_h("a"),
        optimizer_policy_digest=_h("b"),
        budget_policy=mdstats.TrainingBudgetPolicy(planned_epochs=30),
        learning_rate_policy=mdstats.LearningRateSchedulePolicy(base_learning_rate=base_lr),
        structures_per_epoch=17,
        execution_epoch_limit=limit,
    )


def _raw_checkpoint(directory: Path, epoch: int) -> Path:
    path = directory / f"model_run-7_epoch-{epoch}.pt"
    torch.save({"epoch": epoch}, path)
    return path


def _step(model: torch.nn.Module, optimizer: torch.optim.Optimizer, ema: ExponentialMovingAverage) -> None:
    optimizer.zero_grad(set_to_none=True)
    loss = sum((parameter ** 2).sum() for parameter in model.parameters())
    loss.backward()
    optimizer.step()
    ema.update()


def test_train2b_10_of_30_resume_keeps_one_schedule_and_restores_exact_companion(tmp_path: Path) -> None:
    random.seed(11)
    np.random.seed(12)
    torch.manual_seed(13)
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    handler = SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir)))
    train_loader = [object(), object(), object()]

    model = torch.nn.Linear(2, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4, momentum=0.9)
    scheduler = _Scheduler()
    ema = ExponentialMovingAverage(model.parameters(), decay=0.95)
    stage_b_plan = _plan(limit=10)
    stage_b = runtime_mod._Train2Runtime(
        stage_b_plan,
        model=model,
        optimizer=optimizer,
        lr_scheduler=scheduler,
        ema=ema,
        train_loader=train_loader,
        current_epoch=0,
        checkpoint_handler=handler,
        logger_path=str(metrics),
        rank=0,
    )
    for epoch in range(10):
        for _ in train_loader:
            _step(model, optimizer, ema)
        _raw_checkpoint(checkpoint_dir, epoch)
        summary = stage_b.persist_epoch(epoch=epoch)
        assert summary is not None
    assert summary.completed_epochs == 10
    assert summary.completed_updates == 30
    assert summary.planned_updates == 90
    assert not summary.complete_budget
    assert scheduler.calls == 0
    assert stage_b.should_pause_after_epoch(9)
    assert not stage_b.should_pause_after_epoch(8)
    assert summary.normalized_progress == pytest.approx(29 / 89)

    live_before = [p.detach().clone() for p in model.parameters()]
    expected_python = random.random()
    expected_numpy = float(np.random.random())
    expected_torch = float(torch.rand(()))

    # Stage C changes only the pause limit. Its runtime-plan digest therefore
    # differs, while every scientific schedule authority stays identical.
    stage_c_plan = _plan(limit=30)
    assert stage_c_plan.content_digest != stage_b_plan.content_digest

    # Perturb all process-local state before constructing the resumed runtime.
    for _ in range(20):
        random.random()
        np.random.random()
        torch.rand(())
    resumed_model = torch.nn.Linear(2, 1)
    for parameter in resumed_model.parameters():
        parameter.data.fill_(123.0)
    resumed_optimizer = torch.optim.SGD(resumed_model.parameters(), lr=1.0e-4, momentum=0.9)
    resumed_scheduler = _Scheduler()
    resumed_ema = ExponentialMovingAverage(resumed_model.parameters(), decay=0.95)
    stage_c = runtime_mod._Train2Runtime(
        stage_c_plan,
        model=resumed_model,
        optimizer=resumed_optimizer,
        lr_scheduler=resumed_scheduler,
        ema=resumed_ema,
        train_loader=train_loader,
        current_epoch=10,
        checkpoint_handler=handler,
        logger_path=str(metrics),
        rank=0,
    )
    for actual, expected in zip(resumed_model.parameters(), live_before):
        torch.testing.assert_close(actual.detach(), expected)
    assert random.random() == pytest.approx(expected_python)
    assert float(np.random.random()) == pytest.approx(expected_numpy)
    assert float(torch.rand(())) == pytest.approx(expected_torch)
    assert stage_c.completed_updates == 30

    # Update 30 is the first update after the durable 10-epoch boundary and
    # must follow the original U=90 trajectory rather than a new 20-epoch one.
    _step(resumed_model, resumed_optimizer, resumed_ema)
    expected_lr = stage_c_plan.learning_rate_policy.learning_rate_for_update(30, 90)
    assert resumed_optimizer.param_groups[0]["lr"] == pytest.approx(expected_lr)
    assert resumed_scheduler.calls == 0


def test_train2b_persistence_records_nonfinite_model_state_before_endpoint(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    handler = SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir)))
    loader = [object()]
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)
    ema = ExponentialMovingAverage(model.parameters(), decay=0.9)
    plan = _plan(limit=3)
    runtime = runtime_mod._Train2Runtime(
        plan,
        model=model,
        optimizer=optimizer,
        lr_scheduler=_Scheduler(),
        ema=ema,
        train_loader=loader,
        current_epoch=0,
        checkpoint_handler=handler,
        logger_path=str(metrics),
        rank=0,
    )
    _step(model, optimizer, ema)
    with torch.no_grad():
        next(model.parameters()).view(-1)[0] = float("nan")
    raw = _raw_checkpoint(checkpoint_dir, 0)

    with pytest.raises(mdstats.Train2NumericalFailure) as caught:
        runtime.persist_epoch(epoch=0)
    assert caught.value.failure_code == "train_nonfinite_model_state"
    failure = mdstats.load_train2_numerical_failure(checkpoint_dir)
    assert failure is not None
    assert failure.failure_code == "train_nonfinite_model_state"
    assert failure.plan_digest == plan.content_digest
    assert failure.training_protocol_digest == plan.training_protocol_digest
    assert failure.optimizer_policy_digest == plan.optimizer_policy_digest
    assert failure.execution_epoch_limit == 3
    assert failure.raw_checkpoint_name == raw.name
    assert failure.raw_checkpoint_sha256 == runtime_mod._sha256(raw)
    assert not (checkpoint_dir / runtime_mod.TRAIN2_RUNTIME_SUMMARY_FILENAME).exists()


def test_train2b_restart_rejects_changed_lr_authority(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    handler = SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir)))
    loader = [object()]
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)
    ema = ExponentialMovingAverage(model.parameters(), decay=0.9)
    rt = runtime_mod._Train2Runtime(
        _plan(limit=10), model=model, optimizer=optimizer, lr_scheduler=_Scheduler(), ema=ema,
        train_loader=loader, current_epoch=0, checkpoint_handler=handler,
        logger_path=str(metrics), rank=0,
    )
    for epoch in range(10):
        _step(model, optimizer, ema)
        _raw_checkpoint(checkpoint_dir, epoch)
        rt.persist_epoch(epoch=epoch)

    resumed_model = torch.nn.Linear(1, 1)
    resumed_optimizer = torch.optim.SGD(resumed_model.parameters(), lr=2.0e-4)
    with pytest.raises(mdstats.TrainingDataInputError, match="LR-schedule policy"):
        runtime_mod._Train2Runtime(
            _plan(limit=30, base_lr=2.0e-4), model=resumed_model,
            optimizer=resumed_optimizer, lr_scheduler=_Scheduler(),
            ema=ExponentialMovingAverage(resumed_model.parameters(), decay=0.9),
            train_loader=loader, current_epoch=10, checkpoint_handler=handler,
            logger_path=str(metrics), rank=0,
        )


def test_train2b_authenticated_continuation_rejects_tampered_companion(tmp_path: Path) -> None:
    """A raw checkpoint plus summary is not resumable without its companion."""

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)
    runtime = runtime_mod._Train2Runtime(
        _plan(limit=3),
        model=model,
        optimizer=optimizer,
        lr_scheduler=_Scheduler(),
        ema=ExponentialMovingAverage(model.parameters(), decay=0.9),
        train_loader=[object()],
        current_epoch=0,
        checkpoint_handler=SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir))),
        logger_path=str(metrics),
        rank=0,
    )
    _step(model, optimizer, runtime.ema)
    _raw_checkpoint(checkpoint_dir, 0)
    summary = runtime.persist_epoch(epoch=0)
    assert summary is not None

    companion = checkpoint_dir / runtime_mod.TRAIN2_RUNTIME_COMPANION_FILENAME
    companion.write_bytes(b"not an authenticated torch companion")
    with pytest.raises((mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError), match="companion"):
        mdstats.validate_train2_runtime_continuation_artifacts(
            checkpoint_dir,
            training_protocol_digest=summary.training_protocol_digest,
            optimizer_policy_digest=summary.optimizer_policy_digest,
            budget_policy=_plan(limit=3).budget_policy,
            learning_rate_policy=_plan(limit=3).learning_rate_policy,
            structures_per_epoch=17,
        )


def _authentic_runtime_and_summary(
    checkpoint_dir: Path, metrics: Path, *, limit: int = 3
) -> tuple[runtime_mod._Train2Runtime, mdstats.Train2RuntimeSummary]:
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)
    runtime = runtime_mod._Train2Runtime(
        _plan(limit=limit),
        model=model,
        optimizer=optimizer,
        lr_scheduler=_Scheduler(),
        ema=ExponentialMovingAverage(model.parameters(), decay=0.9),
        train_loader=[object()],
        current_epoch=0,
        checkpoint_handler=SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir))),
        logger_path=str(metrics),
        rank=0,
    )
    _step(model, optimizer, runtime.ema)
    _raw_checkpoint(checkpoint_dir, 0)
    summary = runtime.persist_epoch(epoch=0)
    assert summary is not None
    return runtime, summary


def _load_companion(checkpoint_dir: Path) -> dict:
    return torch.load(
        checkpoint_dir / runtime_mod.TRAIN2_RUNTIME_COMPANION_FILENAME,
        map_location="cpu",
        weights_only=False,
    )


def _save_companion(checkpoint_dir: Path, payload: dict) -> None:
    torch.save(payload, checkpoint_dir / runtime_mod.TRAIN2_RUNTIME_COMPANION_FILENAME)


def _validate(checkpoint_dir: Path, summary) -> mdstats.Train2RuntimeSummary:
    return mdstats.validate_train2_runtime_continuation_artifacts(
        checkpoint_dir,
        training_protocol_digest=summary.training_protocol_digest,
        optimizer_policy_digest=summary.optimizer_policy_digest,
        budget_policy=_plan(limit=3).budget_policy,
        learning_rate_policy=_plan(limit=3).learning_rate_policy,
        structures_per_epoch=17,
    )


def test_train2b_scheduler_validator_rejects_tampered_live_parameter_value(tmp_path: Path) -> None:
    """A syntactically valid companion with one modified live-parameter value fails closed."""

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    _, summary = _authentic_runtime_and_summary(checkpoint_dir, metrics)

    payload = _load_companion(checkpoint_dir)
    payload["live_parameters"][0] = payload["live_parameters"][0] + 1.0
    _save_companion(checkpoint_dir, payload)

    with pytest.raises(mdstats.TrainingDataSerializationError, match="live-parameter"):
        _validate(checkpoint_dir, summary)


def test_train2b_scheduler_validator_rejects_tampered_ema_state_value(tmp_path: Path) -> None:
    """A syntactically valid companion with one modified EMA tensor value fails closed."""

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    _, summary = _authentic_runtime_and_summary(checkpoint_dir, metrics)

    payload = _load_companion(checkpoint_dir)
    payload["ema_state"]["shadow_params"][0] = payload["ema_state"]["shadow_params"][0] + 1.0
    _save_companion(checkpoint_dir, payload)

    with pytest.raises(mdstats.TrainingDataSerializationError, match="EMA"):
        _validate(checkpoint_dir, summary)


def test_train2b_scheduler_validator_rejects_tampered_rng_state_value(tmp_path: Path) -> None:
    """A syntactically valid companion with one modified RNG state value fails closed."""

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    _, summary = _authentic_runtime_and_summary(checkpoint_dir, metrics)

    payload = _load_companion(checkpoint_dir)
    payload["rng_state"]["python"]["state"][0] = int(payload["rng_state"]["python"]["state"][0]) + 1
    _save_companion(checkpoint_dir, payload)

    with pytest.raises(mdstats.TrainingDataSerializationError, match="RNG"):
        _validate(checkpoint_dir, summary)


def test_train2b_restart_activation_rejects_tampered_live_parameter_before_applying_state(
    tmp_path: Path,
) -> None:
    """`_restore_continuation` itself must authenticate content, not only the scheduler validator."""

    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    _authentic_runtime_and_summary(checkpoint_dir, metrics, limit=10)

    payload = _load_companion(checkpoint_dir)
    payload["live_parameters"][0] = payload["live_parameters"][0] + 1.0
    _save_companion(checkpoint_dir, payload)

    resumed_model = torch.nn.Linear(1, 1)
    original_parameters = [p.detach().clone() for p in resumed_model.parameters()]
    resumed_optimizer = torch.optim.SGD(resumed_model.parameters(), lr=1.0e-4)
    with pytest.raises(mdstats.TrainingDataSerializationError, match="live-parameter"):
        runtime_mod._Train2Runtime(
            _plan(limit=10),
            model=resumed_model,
            optimizer=resumed_optimizer,
            lr_scheduler=_Scheduler(),
            ema=ExponentialMovingAverage(resumed_model.parameters(), decay=0.9),
            train_loader=[object()],
            current_epoch=1,
            checkpoint_handler=SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir))),
            logger_path=str(metrics),
            rank=0,
        )
    # The rejected companion must never have mutated the resumed model.
    for actual, original in zip(resumed_model.parameters(), original_parameters):
        torch.testing.assert_close(actual.detach(), original)


def test_train2b_activation_rejects_restored_epoch_beyond_active_boundary(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)

    with pytest.raises(mdstats.TrainingDataInputError, match="exceeds its active execution boundary"):
        runtime_mod._Train2Runtime(
            _plan(limit=3),
            model=model,
            optimizer=optimizer,
            lr_scheduler=_Scheduler(),
            ema=ExponentialMovingAverage(model.parameters(), decay=0.9),
            train_loader=[object()],
            current_epoch=4,
            checkpoint_handler=SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir))),
            logger_path=str(metrics),
            rank=0,
        )


def test_train2b_restart_rejects_changed_full_horizon(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    handler = SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir)))
    loader = [object()]
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)
    rt = runtime_mod._Train2Runtime(
        _plan(limit=10), model=model, optimizer=optimizer, lr_scheduler=_Scheduler(), ema=ExponentialMovingAverage(model.parameters(), decay=0.9),
        train_loader=loader, current_epoch=0, checkpoint_handler=handler,
        logger_path=str(metrics), rank=0,
    )
    for epoch in range(10):
        _step(model, optimizer, rt.ema)
        _raw_checkpoint(checkpoint_dir, epoch)
        rt.persist_epoch(epoch=epoch)

    changed_horizon = mdstats.Train2RuntimePlan(
        training_protocol_digest=_h("a"),
        optimizer_policy_digest=_h("b"),
        budget_policy=mdstats.TrainingBudgetPolicy(planned_epochs=40),
        learning_rate_policy=mdstats.LearningRateSchedulePolicy(base_learning_rate=1.0e-4),
        structures_per_epoch=17,
        execution_epoch_limit=40,
    )
    resumed_model = torch.nn.Linear(1, 1)
    resumed_optimizer = torch.optim.SGD(resumed_model.parameters(), lr=1.0e-4)
    with pytest.raises(mdstats.TrainingDataInputError, match="training-budget policy"):
        runtime_mod._Train2Runtime(
            changed_horizon,
            model=resumed_model,
            optimizer=resumed_optimizer,
            lr_scheduler=_Scheduler(),
            ema=ExponentialMovingAverage(resumed_model.parameters(), decay=0.9),
            train_loader=loader,
            current_epoch=10,
            checkpoint_handler=handler,
            logger_path=str(metrics),
            rank=0,
        )


def test_train2b_runtime_plan_and_summary_roundtrip(tmp_path: Path) -> None:
    plan = _plan(limit=10)
    assert mdstats.Train2RuntimePlan.from_dict(plan.to_dict()) == plan
    payload = json.dumps(plan.to_dict())
    assert '"execution_epoch_limit": 10' in payload


def test_train2b_source_qualified_mace_loop_patch_installs(monkeypatch: pytest.MonkeyPatch) -> None:
    import mace.tools as mace_tools

    original = mace_tools.train
    plan = _plan(limit=10)
    monkeypatch.setenv(mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE, json.dumps(plan.to_dict()))
    try:
        critical_precision_cli._install_mace_restart_epoch_patch()
        patched = mace_tools.train
        assert patched is not original
        assert patched.__code__.co_filename == "<mdstats-mace-precision-train>"
        # The patched function imports these hooks inside its body.
        names = set(patched.__code__.co_names)
        assert "activate_train2_runtime" in names
        assert "persist_train2_runtime_epoch" in names
        assert "train2_runtime_should_pause_after_epoch" in names
    finally:
        mace_tools.train = original
        runtime_mod._ACTIVE_RUNTIME = None

def test_train2b_patched_mace_loop_runs_exact_10_epoch_pause_without_patience_stop(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import mace.tools as mace_tools

    original = mace_tools.train
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    metrics = tmp_path / "metrics.jsonl"
    metrics.write_text("", encoding="utf-8")
    plan = _plan(limit=10)
    monkeypatch.setenv(mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE, json.dumps(plan.to_dict()))

    class Handler:
        def __init__(self) -> None:
            self.io = SimpleNamespace(directory=str(checkpoint_dir))

        def save(self, state, epochs: int, keep_last: bool = False) -> None:
            del state, keep_last
            _raw_checkpoint(checkpoint_dir, int(epochs))

    logger = SimpleNamespace(path=str(metrics))
    model = torch.nn.Linear(1, 1)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4)
    scheduler = _Scheduler()
    loader = [object(), object()]
    epochs_seen: list[int] = []

    try:
        critical_precision_cli._install_mace_restart_epoch_patch()
        patched = mace_tools.train

        def fake_train_one_epoch(**kwargs) -> None:
            epoch = int(kwargs["epoch"])
            epochs_seen.append(epoch)
            opt = kwargs["optimizer"]
            for _ in kwargs["data_loader"]:
                opt.step()
            with metrics.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"epoch": epoch, "mode": "opt", "loss": 1.0}) + "\n")

        def fake_evaluate(**kwargs):
            del kwargs
            # Strictly worsening validation would normally trip patience=1.
            value = float(len(epochs_seen) + 1)
            return value, {"rmse_f": value, "rmse_e_per_atom": value}

        def fake_valid_err_log(loss, eval_metrics, logger_obj, log_errors, epoch, name) -> None:
            del loss, log_errors
            if epoch is None:
                return
            with Path(logger_obj.path).open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({
                    "epoch": int(epoch), "mode": "eval", "head": str(name),
                    "rmse_f": float(eval_metrics["rmse_f"]),
                }) + "\n")

        patched.__globals__["train_one_epoch"] = fake_train_one_epoch
        patched.__globals__["evaluate"] = fake_evaluate
        patched.__globals__["valid_err_log"] = fake_valid_err_log
        patched(
            model=model,
            loss_fn=torch.nn.Identity(),
            train_loader=loader,
            valid_loaders={"target": [object()]},
            optimizer=optimizer,
            lr_scheduler=scheduler,
            start_epoch=0,
            max_num_epochs=30,
            patience=1,
            checkpoint_handler=Handler(),
            logger=logger,
            eval_interval=1,
            output_args={},
            device=torch.device("cpu"),
            log_errors="RMSE",
            swa=None,
            ema=None,
            max_grad_norm=10.0,
            log_wandb=False,
            distributed=False,
            save_all_checkpoints=True,
            plotter=None,
            distributed_model=None,
            train_sampler=None,
            rank=0,
        )
        assert epochs_seen == list(range(10))
        assert scheduler.calls == 0
        summary = mdstats.load_train2_runtime_summary(checkpoint_dir)
        assert summary.completed_epochs == 10
        assert summary.completed_updates == 20
        assert summary.planned_updates == 60
        assert summary.execution_epoch_limit == 10
        assert not summary.complete_budget
        history = [json.loads(line) for line in (checkpoint_dir / "train2_history.jsonl").read_text().splitlines()]
        assert len(history) == 10
        assert history[-1]["phase"] == plan.learning_rate_policy.phase(19 / 59)
        persistence = [
            json.loads(line)
            for line in (checkpoint_dir / "train2_persistence.jsonl").read_text().splitlines()
        ]
        assert len(persistence) == 10
        assert persistence[-1]["schema"] == "mdstats.train2-persistence-telemetry.v1"
        assert persistence[-1]["hash_transport"] == "python-buffer-protocol-chunked-v1"
        assert persistence[-1]["total_persistence_seconds"] >= 0.0
    finally:
        mace_tools.train = original
        runtime_mod._ACTIVE_RUNTIME = None

def test_train2b_true_dft_replay_monitor_is_diagnostic_and_authenticated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mdstats.training_data import adaptive_stop

    replay = tmp_path / "replay_true.xyz"
    replay.write_bytes(b"true-dft-replay\n")
    plan = mdstats.Train2RuntimePlan(
        training_protocol_digest=_h("a"), optimizer_policy_digest=_h("b"),
        budget_policy=mdstats.TrainingBudgetPolicy(planned_epochs=30),
        learning_rate_policy=mdstats.LearningRateSchedulePolicy(base_learning_rate=1.0e-4),
        structures_per_epoch=17, replay_monitor_enabled=True,
        target_head_name="target_head", replay_head_name="pt_head",
        true_replay_monitor_sha256=runtime_mod._sha256(replay), execution_epoch_limit=10,
    )
    monkeypatch.setenv(mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE, json.dumps(plan.to_dict()))
    monkeypatch.setenv(mdstats.TRAIN2_TRUE_REPLAY_PATH_ENVIRONMENT_VARIABLE, str(replay))
    observed = {}

    def fake_loader(model, valid_loaders, *, path, dataset_head):
        observed.update(path=path, dataset_head=dataset_head, valid=tuple(valid_loaders))
        return "TRUE_DFT_LOADER"

    monkeypatch.setattr(adaptive_stop, "_validation_loader_from_extxyz", fake_loader)
    model = SimpleNamespace(heads=["pt_head", "target_head"])
    result = runtime_mod.prepare_train2_true_replay_validation_loader(
        model, {"target_head": "TARGET"}
    )
    assert result[mdstats.TRAIN2_TRUE_REPLAY_LOG_HEAD] == "TRUE_DFT_LOADER"
    assert result["target_head"] == "TARGET"
    assert observed["dataset_head"] == "pt_head"
    assert observed["path"] == replay.resolve()

    replay.write_bytes(b"changed\n")
    with pytest.raises(mdstats.TrainingDataInputError, match="missing or changed"):
        runtime_mod.prepare_train2_true_replay_validation_loader(model, {"target_head": "TARGET"})


def test_train2b_rejects_retired_staged_precision_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mdstats.training_data import precision_runtime

    plan = _plan(limit=10)
    monkeypatch.setenv(mdstats.TRAIN2_RUNTIME_ENVIRONMENT_VARIABLE, json.dumps(plan.to_dict()))
    monkeypatch.setattr(
        precision_runtime,
        "configure_precision_runtime_from_argv",
        lambda argv: SimpleNamespace(staged=True),
    )
    with pytest.raises(RuntimeError, match="one fixed FP32 or FP64 precision stage"):
        critical_precision_cli._install_mace_restart_epoch_patch()
