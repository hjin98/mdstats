from __future__ import annotations

from pathlib import Path
import copy
import json

import pytest

import mdstats
from mdstats.training_data import precision_runtime as runtime


torch = pytest.importorskip("torch")
torch_ema = pytest.importorskip("torch_ema")


@pytest.fixture(autouse=True)
def _restore_torch_default_dtype():
    original = torch.get_default_dtype()
    torch.set_default_dtype(torch.float32)
    try:
        yield
    finally:
        torch.set_default_dtype(original)



class _IO:
    def __init__(self, directory: Path, tag: str = "tiny"):
        self.directory = str(directory)
        self.tag = tag
        self.swa_start = None

    def _get_checkpoint_filename(self, epoch: int, swa_start=None) -> str:
        del swa_start
        return f"{self.tag}_epoch-{epoch}.pt"


class _Handler:
    def __init__(self, directory: Path):
        self.io = _IO(directory)


def _plan(tmp_path: Path) -> runtime.PrecisionRuntimePlan:
    policy = mdstats.PrecisionSchedulePolicy(
        requested_profile="test_refine",
        stages=(
            mdstats.PrecisionStage("float32", 0.5, 1.0),
            mdstats.PrecisionStage("float64", 0.5, 0.5),
        ),
        minimum_final_stage_epochs=1,
        minimum_final_stage_gradient_updates=0,
        model_dtype="float64",
        critical_operation_dtype="float64",
        evaluation_dtype="float64",
        verification_dtype="float64",
        export_dtype="float64",
    )
    schedule = policy.resolve(max_num_epochs=2, updates_per_epoch=1)
    return runtime.PrecisionRuntimePlan(
        job_manifest_path=str(tmp_path / "job_manifest.json"),
        job_digest="1" * 64,
        protocol_digest="2" * 64,
        optimizer_policy_digest="3" * 64,
        schedule=schedule,
        checkpoints_dir=str(tmp_path / "checkpoints"),
    )


def _step(model, optimizer, ema, x, y):
    optimizer.zero_grad(set_to_none=True)
    loss = torch.nn.functional.mse_loss(model(x), y)
    loss.backward()
    optimizer.step()
    ema.update()
    return float(loss.detach())


def _save_mace_style_checkpoint(path: Path, model, optimizer, scheduler, ema) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ema.average_parameters():
        torch.save(
            {
                "model": copy.deepcopy(model.state_dict()),
                "optimizer": copy.deepcopy(optimizer.state_dict()),
                "lr_scheduler": copy.deepcopy(scheduler.state_dict()),
            },
            path,
        )


def _assert_optimizer_equal(a, b):
    sa = list(a.state.values())
    sb = list(b.state.values())
    assert len(sa) == len(sb)
    for left, right in zip(sa, sb):
        assert left.keys() == right.keys()
        for key in left:
            if torch.is_tensor(left[key]):
                assert torch.equal(left[key].cpu(), right[key].cpu())
            else:
                assert left[key] == right[key]


def test_prec2_promotes_model_adam_amsgrad_ema_and_lr(tmp_path: Path, monkeypatch) -> None:
    plan = _plan(tmp_path)
    monkeypatch.setattr(runtime, "_ACTIVE_PLAN", plan)
    monkeypatch.setattr(runtime, "_RESTART_COMPANION", None)
    monkeypatch.setattr(runtime, "_TRANSITION_APPLIED", set())

    torch.manual_seed(7)
    model = torch.nn.Sequential(torch.nn.Linear(3, 8), torch.nn.SiLU(), torch.nn.Linear(8, 1)).float()
    optimizer = torch.optim.Adam(model.parameters(), lr=1.0e-4, amsgrad=True)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.95)
    ema = torch_ema.ExponentialMovingAverage(model.parameters(), decay=0.99)
    x = torch.randn(5, 3)
    y = torch.randn(5, 1)
    _step(model, optimizer, ema, x, y)

    handler = _Handler(Path(plan.checkpoints_dir))
    raw0 = Path(handler.io.directory) / handler.io._get_checkpoint_filename(0)
    _save_mace_style_checkpoint(raw0, model, optimizer, scheduler, ema)
    runtime.persist_precision_runtime_companion(
        model=model,
        optimizer=optimizer,
        lr_scheduler=scheduler,
        ema=ema,
        checkpoint_handler=handler,
        epoch=0,
    )

    record = runtime.apply_precision_stage_boundary(
        model=model,
        optimizer=optimizer,
        lr_scheduler=scheduler,
        ema=ema,
        loss_fn=torch.nn.MSELoss(),
        epoch=1,
    )
    assert record is not None
    assert record.source_dtype == "float32"
    assert record.destination_dtype == "float64"
    assert record.learning_rates_before == pytest.approx((1.0e-4,))
    assert record.learning_rates_after == pytest.approx((5.0e-5,))
    assert {p.dtype for p in model.parameters()} == {torch.float64}
    assert {b.dtype for b in model.buffers() if b.is_floating_point()} <= {torch.float64}
    assert runtime.optimizer_dtype_inventory(optimizer) == {
        "float64": sum(
            int(v.numel())
            for state in optimizer.state.values()
            for v in state.values()
            if torch.is_tensor(v) and v.is_floating_point()
        )
    }
    assert set(runtime.ema_dtype_inventory(ema)) == {"float64"}
    receipt = runtime.transition_record_path(handler.io.directory, 1)
    assert receipt.is_file()
    assert runtime.MacePrecisionStageTransitionRecord.from_dict(json.loads(receipt.read_text())) == record


def test_prec2_latest_only_companion_restores_exact_live_and_ema_state(tmp_path: Path, monkeypatch) -> None:
    plan = _plan(tmp_path)
    monkeypatch.setattr(runtime, "_ACTIVE_PLAN", plan)
    monkeypatch.setattr(runtime, "_RESTART_COMPANION", None)
    monkeypatch.setattr(runtime, "_TRANSITION_APPLIED", set())

    torch.manual_seed(19)
    model = torch.nn.Linear(2, 1).float()
    optimizer = torch.optim.Adam(model.parameters(), lr=1.0e-4, amsgrad=True)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.9)
    ema = torch_ema.ExponentialMovingAverage(model.parameters(), decay=0.9)
    handler = _Handler(Path(plan.checkpoints_dir))
    x0 = torch.randn(4, 2)
    y0 = torch.randn(4, 1)
    _step(model, optimizer, ema, x0, y0)
    raw0 = Path(handler.io.directory) / handler.io._get_checkpoint_filename(0)
    _save_mace_style_checkpoint(raw0, model, optimizer, scheduler, ema)
    runtime.persist_precision_runtime_companion(
        model=model, optimizer=optimizer, lr_scheduler=scheduler, ema=ema,
        checkpoint_handler=handler, epoch=0,
    )
    runtime.apply_precision_stage_boundary(
        model=model, optimizer=optimizer, lr_scheduler=scheduler, ema=ema,
        loss_fn=torch.nn.MSELoss(), epoch=1,
    )

    x1 = torch.randn(4, 2, dtype=torch.float64)
    y1 = torch.randn(4, 1, dtype=torch.float64)
    _step(model, optimizer, ema, x1, y1)
    raw1 = Path(handler.io.directory) / handler.io._get_checkpoint_filename(1)
    _save_mace_style_checkpoint(raw1, model, optimizer, scheduler, ema)
    runtime.persist_precision_runtime_companion(
        model=model, optimizer=optimizer, lr_scheduler=scheduler, ema=ema,
        checkpoint_handler=handler, epoch=1,
    )
    assert runtime.latest_resumable_precision_epoch(handler.io.directory, plan) == 1

    # Uninterrupted branch performs one more identical update.
    model_a = copy.deepcopy(model)
    optimizer_a = torch.optim.Adam(model_a.parameters(), lr=1.0e-4, amsgrad=True)
    optimizer_a.load_state_dict(copy.deepcopy(optimizer.state_dict()))
    ema_a = torch_ema.ExponentialMovingAverage(model_a.parameters(), decay=0.9)
    ema_state = ema.state_dict()
    ema_a.load_state_dict({
        "decay": ema_state["decay"],
        "num_updates": ema_state["num_updates"],
        "shadow_params": [v.detach().clone() for v in ema_state["shadow_params"]],
        "collected_params": None if ema_state["collected_params"] is None else [v.detach().clone() for v in ema_state["collected_params"]],
    })

    # Restart branch mirrors MACE: construct at checkpoint dtype, load raw EMA
    # model + optimizer/scheduler, then restore the mdstats live/EMA companion.
    checkpoint = torch.load(raw1, map_location="cpu", weights_only=False)
    model_b = torch.nn.Linear(2, 1).double()
    optimizer_b = torch.optim.Adam(model_b.parameters(), lr=1.0e-4, amsgrad=True)
    scheduler_b = torch.optim.lr_scheduler.ExponentialLR(optimizer_b, gamma=0.9)
    model_b.load_state_dict(checkpoint["model"])
    optimizer_b.load_state_dict(checkpoint["optimizer"])
    scheduler_b.load_state_dict(checkpoint["lr_scheduler"])
    ema_b = torch_ema.ExponentialMovingAverage(model_b.parameters(), decay=0.9)
    companion = runtime._load_companion(runtime.companion_path(handler.io.directory), plan=plan)
    monkeypatch.setattr(runtime, "_RESTART_COMPANION", companion)
    runtime.restore_restart_companion_into_ema(ema_b, list(model_b.parameters()))

    for pa, pb in zip(model_a.parameters(), model_b.parameters()):
        assert torch.equal(pa, pb)
    _assert_optimizer_equal(optimizer_a, optimizer_b)
    for pa, pb in zip(ema_a.shadow_params, ema_b.shadow_params):
        assert torch.equal(pa, pb)

    x2 = torch.randn(6, 2, dtype=torch.float64)
    y2 = torch.randn(6, 1, dtype=torch.float64)
    _step(model_a, optimizer_a, ema_a, x2, y2)
    _step(model_b, optimizer_b, ema_b, x2, y2)
    for pa, pb in zip(model_a.parameters(), model_b.parameters()):
        assert torch.equal(pa, pb)
    _assert_optimizer_equal(optimizer_a, optimizer_b)
    for pa, pb in zip(ema_a.shadow_params, ema_b.shadow_params):
        assert torch.equal(pa, pb)


def test_prec2_batch_cast_preserves_integer_graph_indices() -> None:
    class Batch:
        def __init__(self):
            self.pos = torch.randn(3, 3, dtype=torch.float32)
            self.edge_index = torch.tensor([[0, 1], [1, 2]], dtype=torch.int64)
        def apply(self, fn):
            self.pos = fn(self.pos)
            self.edge_index = fn(self.edge_index)
            return self

    model = torch.nn.Linear(3, 1).double()
    batch = runtime.cast_batch_to_model_dtype(Batch(), model)
    assert batch.pos.dtype == torch.float64
    assert batch.edge_index.dtype == torch.int64


def test_prec2_campaign_restart_uses_companion_epoch_not_newer_unpaired_raw(tmp_path: Path, monkeypatch) -> None:
    plan = _plan(tmp_path)
    monkeypatch.setattr(runtime, "_ACTIVE_PLAN", plan)
    checkpoint_dir = Path(plan.checkpoints_dir)
    checkpoint_dir.mkdir(parents=True)
    # Build a minimal valid companion for epoch zero by using the normal writer.
    model = torch.nn.Linear(1, 1).float()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4, amsgrad=True)
    scheduler = torch.optim.lr_scheduler.ExponentialLR(optimizer, gamma=0.9)
    ema = torch_ema.ExponentialMovingAverage(model.parameters(), decay=0.9)
    _step(model, optimizer, ema, torch.ones(1, 1), torch.zeros(1, 1))
    handler = _Handler(checkpoint_dir)
    raw0 = checkpoint_dir / handler.io._get_checkpoint_filename(0)
    _save_mace_style_checkpoint(raw0, model, optimizer, scheduler, ema)
    runtime.persist_precision_runtime_companion(
        model=model, optimizer=optimizer, lr_scheduler=scheduler, ema=ema,
        checkpoint_handler=handler, epoch=0,
    )
    # Simulate a crash after MACE wrote epoch 1 but before companion commit.
    torch.save({"model": {}, "optimizer": {}, "lr_scheduler": {}}, checkpoint_dir / "tiny_epoch-1.pt")
    assert runtime.latest_resumable_precision_epoch(checkpoint_dir, plan) == 0


def test_prec2_source_contract_matches_supplied_mace_0316() -> None:
    import inspect
    import mace.tools

    source = inspect.getsource(mace.tools.train)
    assert source.count("    epoch = start_epoch\n") == 1
    assert source.count("        if epoch > start_epoch:\n") == 2
    assert source.count("        # Train\n") == 1
    assert source.count(
        "                        keep_last = False or save_all_checkpoints\n"
        "        if distributed:\n"
        "            torch.distributed.barrier()\n"
    ) == 1
