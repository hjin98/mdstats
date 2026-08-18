from __future__ import annotations

import json
from pathlib import Path
import sys

import numpy as np
import pytest


torch = pytest.importorskip("torch")
pytest.importorskip("e3nn")
pytest.importorskip("torch_ema")
mace = pytest.importorskip("mace")

from e3nn import o3
from torch_ema import ExponentialMovingAverage
from mace import data, modules, tools
from mace.tools import torch_geometric
from mace.modules.loss import WeightedEnergyForcesLoss

from mdstats.training_data.precision_schedule import PrecisionSchedulePolicy, PrecisionStage
from mdstats.training_data.critical_precision import install_mace_critical_fp64_patch
from mdstats.training_data.critical_precision_cli import _install_mace_restart_epoch_patch
from mdstats.training_data import precision_runtime as runtime


@pytest.fixture(autouse=True)
def _reset_runtime(monkeypatch):
    old_default = torch.get_default_dtype()
    old_argv = list(sys.argv)
    monkeypatch.setattr(runtime, "_ACTIVE_PLAN", None)
    monkeypatch.setattr(runtime, "_RESTART_COMPANION", None)
    monkeypatch.setattr(runtime, "_TRANSITION_APPLIED", set())
    try:
        yield
    finally:
        torch.set_default_dtype(old_default)
        sys.argv[:] = old_argv


class _Scheduler:
    def __init__(self, optimizer):
        self.optimizer = optimizer
        self._last_lr = [group["lr"] for group in optimizer.param_groups]
        self.base_lrs = list(self._last_lr)

    def step(self, metrics=None, epoch=None):
        del metrics, epoch
        self._last_lr = [group["lr"] for group in self.optimizer.param_groups]

    def state_dict(self):
        return {"_last_lr": list(self._last_lr), "base_lrs": list(self.base_lrs)}

    def load_state_dict(self, state):
        self._last_lr = list(state["_last_lr"])
        self.base_lrs = list(state["base_lrs"])


def test_prec2_real_mace_0316_force_training_crosses_fp32_fp64_boundary(tmp_path: Path) -> None:
    version = str(getattr(mace, "__version__", ""))
    if version and version != "0.3.16":
        pytest.skip(f"PREC2 source qualification is version-locked to MACE 0.3.16, observed {version}.")

    root = tmp_path / "run"
    checkpoints = root / "checkpoints"
    checkpoints.mkdir(parents=True)
    config = root / "mace_config.yaml"
    config.write_text("{}\n", encoding="utf-8")

    policy = PrecisionSchedulePolicy(
        requested_profile="refine",
        stages=(
            PrecisionStage("float32", 0.5, 1.0),
            PrecisionStage("float64", 0.5, 0.5),
        ),
        minimum_final_stage_epochs=1,
        minimum_final_stage_gradient_updates=0,
        model_dtype="float64",
        critical_operation_dtype="float64",
        evaluation_dtype="float64",
        verification_dtype="float64",
        export_dtype="float64",
    )
    schedule = policy.resolve(max_num_epochs=2, updates_per_epoch=2)
    manifest = {
        "content_digest": "1" * 64,
        "protocol": {
            "content_digest": "2" * 64,
            "optimizer_policy": {"policy_digest": "3" * 64},
            "resolved_precision_schedule": schedule.to_dict(),
        },
    }
    (root / "job_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    sys.argv[:] = [
        "mdstats-mace-train",
        "--config",
        str(config),
        "--checkpoints_dir",
        str(checkpoints),
    ]
    install_mace_critical_fp64_patch()
    _install_mace_restart_epoch_patch()

    torch.manual_seed(11)
    torch.set_default_dtype(torch.float32)
    configuration = data.Configuration(
        atomic_numbers=np.array([8, 1, 1]),
        positions=np.array([[0.0, -2.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]),
        properties={
            "forces": np.array([[0.0, -1.3, 0.0], [1.0, 0.2, 0.0], [0.0, 1.1, 0.3]]),
            "energy": -1.5,
        },
        property_weights={"forces": 1.0, "energy": 1.0},
    )
    table = tools.AtomicNumberTable([1, 8])
    model = modules.ScaleShiftMACE(
        r_max=4.0,
        num_bessel=4,
        num_polynomial_cutoff=3,
        max_ell=1,
        interaction_cls=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
        interaction_cls_first=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
        num_interactions=2,
        num_elements=2,
        hidden_irreps=o3.Irreps("8x0e + 8x1o"),
        MLP_irreps=o3.Irreps("4x0e"),
        gate=torch.nn.functional.silu,
        atomic_energies=np.array([0.0, 0.0]),
        avg_num_neighbors=2.0,
        atomic_numbers=table.zs,
        correlation=2,
        atomic_inter_scale=1.0,
        atomic_inter_shift=0.0,
    )
    atomic_data = data.AtomicData.from_config(configuration, z_table=table, cutoff=4.0)
    train_loader = torch_geometric.dataloader.DataLoader(
        dataset=[atomic_data, atomic_data], batch_size=1, shuffle=False, drop_last=False
    )
    valid_loader = torch_geometric.dataloader.DataLoader(
        dataset=[atomic_data], batch_size=1, shuffle=False, drop_last=False
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=1.0e-4, amsgrad=True)
    scheduler = _Scheduler(optimizer)
    ema = ExponentialMovingAverage(model.parameters(), decay=0.99)
    logger = tools.MetricsLogger(directory=str(root / "results"), tag="tiny_train")
    checkpoint_handler = tools.CheckpointHandler(directory=str(checkpoints), tag="tiny", keep=True)
    loss = WeightedEnergyForcesLoss(energy_weight=1.0, forces_weight=1.0)

    tools.train(
        model=model,
        loss_fn=loss,
        train_loader=train_loader,
        valid_loaders={"Default": valid_loader},
        optimizer=optimizer,
        lr_scheduler=scheduler,
        start_epoch=0,
        max_num_epochs=2,
        patience=999,
        checkpoint_handler=checkpoint_handler,
        logger=logger,
        eval_interval=1,
        output_args={"forces": True, "virials": False, "stress": False},
        device=torch.device("cpu"),
        log_errors="PerAtomRMSE",
        ema=ema,
        max_grad_norm=10.0,
        save_all_checkpoints=True,
    )

    assert {parameter.dtype for parameter in model.parameters()} == {torch.float64}
    assert optimizer.param_groups[0]["lr"] == pytest.approx(5.0e-5)
    assert runtime.latest_resumable_precision_epoch(checkpoints, runtime._ACTIVE_PLAN) == 1
    receipt = runtime.transition_record_path(checkpoints, 1)
    assert receipt.is_file()
    transition = runtime.MacePrecisionStageTransitionRecord.from_dict(
        json.loads(receipt.read_text(encoding="utf-8"))
    )
    assert transition.source_dtype == "float32"
    assert transition.destination_dtype == "float64"
    assert runtime.companion_path(checkpoints).is_file()
