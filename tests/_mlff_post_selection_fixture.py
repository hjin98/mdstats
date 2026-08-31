"""Shared real-owner fixture for the P5 post-selection acceptance tests.

The campaign, the CampaignStore, the P1/P2/P3/P4 owners, and every P5 owner run
as production code.  Only MACE is substituted, through two seams that sit
strictly below the owner boundary: a trainer that drives the *real* TRAIN2
runtime with a toy model, and an inference evaluator that returns predictions
for artifacts real owners exported and authenticated.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore

#: A production horizon deliberately different from the screening ladder's n3
#: (10), so every acceptance run proves the two are independent rather than
#: coincidentally equal.
PRODUCTION_MAX_NUM_EPOCHS = 3

POST_SELECTION_CONFIG = """
[post_selection.cv]
fold_count = 2
partition_seed = 7
seeds = [11]
max_num_epochs = 2
acceptance_maximum = 0.5

[post_selection.production]
seeds = [5]
"""


def fixture_config_text(**overrides: str) -> str:
    """The P4 fixture campaign plus a resolved post-selection configuration."""

    text = p4d._CONFIG.replace(
        "seeds = [1, 2]",
        f"seeds = [1, 2]\nmax_num_epochs = {PRODUCTION_MAX_NUM_EPOCHS}",
    ) + POST_SELECTION_CONFIG
    for old, new in overrides.items():
        text = text.replace(old.replace("__", " "), new)
    return text


def build_selected_campaign(
    tmp_path: Path, *, config_text: str | None = None
) -> tuple[Path, Path]:
    """A real campaign driven to a current SELECTED target-size terminal result."""

    template = fixture_config_text() if config_text is None else config_text
    with patch.object(p4d, "_CONFIG", template):
        config, workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    screen = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=screen.train,
            _external_inference_evaluator=screen.evaluate,
        )
        == 0
    )
    return config, workspace


def rewrite_config(config: Path, old: str, new: str) -> None:
    """Edit one configuration line in place, as an operator would.

    The operator-facing `doctor` gate is re-marked afterwards, exactly as the
    base fixture marks it: this suite is about post-selection science, not about
    re-litigating the environment gate on every edit.
    """

    text = config.read_text(encoding="utf-8")
    assert old in text, old
    config.write_text(text.replace(old, new), encoding="utf-8")
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        cli._mark_stage(store, paths, "doctor", cli.StageState.COMPLETE, "fixture")
    finally:
        store.close()


def load_context(config: Path):
    """Resolve `(cfg, paths, store)` for direct owner-level assertions."""

    cfg, paths = cli._load_config(config)
    return cfg, paths, CampaignStore(paths.state_db)


def _seeded_raw_checkpoint(directory, epoch: int, optimizer_seed: int):
    """A toy checkpoint whose bytes actually depend on the optimizer seed.

    Two production seeds are two different trainings and must not produce
    byte-identical checkpoints: a cross-seed decision keyed by checkpoint
    identity would otherwise be ill-defined for reasons that exist only in the
    fixture.
    """

    import torch

    path = directory / f"model_run-7_epoch-{epoch}.pt"
    torch.save({"epoch": epoch, "optimizer_seed": int(optimizer_seed)}, path)
    return path


def train_like_mace(request):
    """Play MACE for one post-selection run through the real TRAIN2 runtime.

    The TRAIN2 runtime, its epoch history, its continuation companion, and its
    runtime summary are all produced by production code; only the model and the
    logged validation numbers are synthetic.
    """

    import random

    import torch
    from torch_ema import ExponentialMovingAverage

    from mdstats.training_data import train2_runtime as runtime_mod

    seed = int(request.run_plan.optimizer_seed)
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    checkpoint_dir = request.checkpoint_directory
    metrics = checkpoint_dir.parent / "metrics.jsonl"
    metrics.parent.mkdir(parents=True, exist_ok=True)
    if not metrics.is_file():
        metrics.write_text("", encoding="utf-8")
    handler = SimpleNamespace(io=SimpleNamespace(directory=str(checkpoint_dir)))
    train_loader = [object()]
    model = torch.nn.Linear(3, 2, dtype=torch.float64)
    optimizer = torch.optim.SGD(model.parameters(), lr=1.0e-4, momentum=0.9)
    ema = ExponentialMovingAverage(model.parameters(), decay=0.95)
    runtime = runtime_mod._Train2Runtime(
        request.plan,
        model=model,
        optimizer=optimizer,
        lr_scheduler=p3c._NoStepScheduler(),
        ema=ema,
        train_loader=train_loader,
        current_epoch=request.start_epoch,
        checkpoint_handler=handler,
        logger_path=str(metrics),
        rank=0,
    )
    summary = None
    for epoch in range(request.start_epoch, request.plan.execution_epoch_limit):
        for _ in train_loader:
            p3c._step(model, optimizer, ema)
        _seeded_raw_checkpoint(checkpoint_dir, epoch, seed)
        with metrics.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps(
                    {
                        "epoch": epoch,
                        "mode": "eval",
                        "head": request.plan.target_head_name,
                        "rmse_f": 0.01 + 0.001 * epoch,
                    }
                )
                + "\n"
            )
        summary = runtime.persist_epoch(epoch=epoch)
    return summary


class PostSelectionHarness:
    """The two bounded numerical seams, plus a record of what was executed."""

    def __init__(
        self,
        force_offset: float = 1.0e-4,
        run_force_offsets: dict[str, float] | None = None,
    ) -> None:
        self.runs: list[str] = []
        self.requests: list[object] = []
        self.force_offset = force_offset
        #: Per-run force error, keyed by a substring of the run identity, so a
        #: test can give two production seeds deliberately different M3 target
        #: metrics.  The toy trainer writes byte-identical logs, so the run's
        #: authenticated checkpoint locator is what distinguishes the runs.
        self.run_force_offsets = dict(run_force_offsets or {})

    def train(self, request):
        from mdstats.training_data.post_selection_execution import (
            post_selection_mace_run_configuration,
        )

        self.runs.append(request.run_plan.run_identity)
        self.requests.append(request)
        config_path = (
            request.materialization_directory
            / request.materialization.mace_config_relative_path
        )
        assert config_path.is_file()
        assert post_selection_mace_run_configuration(
            json.loads(config_path.read_text(encoding="utf-8"))
        )["train_file"]
        return train_like_mace(request)

    def _offset_for(self, provider) -> float:
        identity = getattr(provider, "checkpoint_identity", None)
        locator = "" if identity is None else str(getattr(identity, "checkpoint_locator", ""))
        for key, value in self.run_force_offsets.items():
            if key and key in locator:
                return float(value)
        return float(self.force_offset)

    def evaluate(self, provider, atoms_list):
        from mdstats.training_data.mace_export import MaceExtxyzPolicy

        policy = MaceExtxyzPolicy()
        offset = self._offset_for(provider)
        predictions = []
        for atoms in atoms_list:
            forces = (
                np.asarray(atoms.arrays[policy.forces_key], dtype=np.float64)
                + offset
            )
            stress = atoms.info.get(policy.stress_key)
            stress_3x3 = None
            if stress is not None:
                flat = np.asarray(stress, dtype=np.float64).reshape(-1)
                stress_3x3 = (
                    np.array(
                        [
                            [flat[0], flat[5], flat[4]],
                            [flat[5], flat[1], flat[3]],
                            [flat[4], flat[3], flat[2]],
                        ]
                    )
                    if flat.size == 6
                    else flat.reshape(3, 3)
                )
            predictions.append(
                SimpleNamespace(
                    energy_ev=float(atoms.info[policy.energy_key]),
                    forces_ev_per_angstrom=forces,
                    stress_ev_per_angstrom3=stress_3x3,
                )
            )
        return predictions


def run_cross_validate(config: Path, harness: PostSelectionHarness | None = None) -> int:
    active = PostSelectionHarness() if harness is None else harness
    return p4d._run(
        config,
        "cross-validate",
        _external_post_selection_trainer=active.train,
        _external_inference_evaluator=active.evaluate,
    )


def run_train_production(
    config: Path, harness: PostSelectionHarness | None = None
) -> int:
    active = PostSelectionHarness() if harness is None else harness
    return p4d._run(
        config,
        "train-production",
        _external_post_selection_trainer=active.train,
        _external_inference_evaluator=active.evaluate,
    )
