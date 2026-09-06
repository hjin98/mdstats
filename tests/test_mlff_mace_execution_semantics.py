"""Bounded real-MACE acceptance for the reopened execution-semantics seam."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("e3nn")
pytest.importorskip("mace")

from ase import Atoms
from ase.io import write

from mdstats.training_data._common import digest
from mdstats.training_data.campaign_target_size_runtime import (
    TARGET_SIZE_MACE_HEAD_NAME,
    mace_run_configuration,
)
from mdstats.training_data.critical_precision_cli import (
    _install_mace_restart_epoch_patch,
)
from mdstats.training_data.mace_compatibility import (
    MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
    build_mace_execution_authority,
    mace_execution_authority_to_environment,
    mace_execution_evidence_from_environment,
    mace_frame_uid_set_digest,
    probe_mace_source_texts,
)
from mdstats.training_data.model_features import (
    canonicalize_mace_candidate_architecture,
    mace_candidate_architecture_defaults,
)
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    POST_SELECTION_REPLAY_HEAD_NAME,
    POST_SELECTION_TARGET_HEAD_NAME,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.target_size_execution import TARGET_SIZE_MACE_CONFIG_SCHEMA


class _StopAfterResolution(RuntimeError):
    """Stop the real run_train path after loss/loader resolution."""


def test_pinned_source_probe_rejects_every_repaired_execution_marker() -> None:
    import mace

    source_root = Path(mace.__file__).resolve().parent.parent
    run_train = (source_root / "mace" / "cli" / "run_train.py").read_text(
        encoding="utf-8"
    )
    train = (source_root / "mace" / "tools" / "train.py").read_text(
        encoding="utf-8"
    )
    multihead = (
        source_root / "mace" / "tools" / "multihead_tools.py"
    ).read_text(encoding="utf-8")
    mutations = (
        (run_train.replace('args.loss = "universal"', "", 1), run_train, multihead),
        (run_train.replace("args.lr = 0.0001", "", 1), run_train, multihead),
        (run_train.replace("head_config.collections.train +=", "", 1), run_train, multihead),
        (run_train.replace("drop_last=(not args.lbfgs)", "drop_last=False"), run_train, multihead),
        (
            run_train.replace(
                "drop_last=(train_sampler is None and not args.lbfgs)",
                "drop_last=False",
                1,
            ),
            run_train,
            multihead,
        ),
    )
    for mutated_run, _unused_train, _unused_multihead in mutations:
        probe = probe_mace_source_texts(mutated_run, train, multihead)
        assert probe.fixed_file_adapter_supported is False


def _write_frames(path: Path, *, count: int, prefix: str) -> tuple[str, ...]:
    uids = []
    frames = []
    for index in range(count):
        uid = f"{prefix}-{index:04d}"
        uids.append(uid)
        atoms = Atoms(
            "H2",
            positions=((0.0, 0.0, 0.0), (0.75 + 0.01 * index, 0.0, 0.0)),
            cell=(8.0, 8.0, 8.0),
            pbc=True,
        )
        atoms.info.update(
            {
                "REF_energy": float(index) * 0.01,
                "REF_stress": np.zeros(6, dtype=float),
                "frame_uid": uid,
                "config_weight": 1.0,
                "config_energy_weight": 1.0,
                "config_forces_weight": 1.0,
                "config_stress_weight": 1.0,
            }
        )
        atoms.arrays["REF_forces"] = np.zeros((2, 3), dtype=float)
        frames.append(atoms)
    write(path, frames, format="extxyz")
    return tuple(uids)


def _architecture() -> dict:
    return canonicalize_mace_candidate_architecture(mace_candidate_architecture_defaults())


def _target_internal_config(
    *, target: Path, valid: Path, batch_size: int = 2
) -> dict:
    return {
        "schema": TARGET_SIZE_MACE_CONFIG_SCHEMA,
        "name": "target-size-execution-semantics",
        "seed": 17,
        "target_train_file": str(target),
        "target_valid_file": str(valid),
        "atomic_numbers": [1],
        "E0s": {"1": 0.0},
        "energy_key": "REF_energy",
        "forces_key": "REF_forces",
        "stress_key": "REF_stress",
        "lr": 0.0123,
        "loss": "stress",
        "energy_weight": 2.0,
        "forces_weight": 7.0,
        "stress_weight": 3.0,
        "batch_size": batch_size,
        "valid_batch_size": batch_size,
        "num_workers": 0,
        "max_num_epochs": 1,
        "ema": False,
        "ema_decay": 0.87,
        "amsgrad": True,
        "weight_decay": 0.0,
        "clip_grad": 10.0,
        "default_dtype": "float64",
        "device": "cpu",
        "compute_avg_num_neighbors": False,
        "multiheads_finetuning": False,
        "mace_architecture": _architecture(),
        "multi_head": {
            TARGET_SIZE_MACE_HEAD_NAME: {
                "train_file": str(target),
                "valid_file": str(valid),
                "atomic_numbers": [1],
                "E0s": {"1": 0.0},
                "energy_key": "REF_energy",
                "forces_key": "REF_forces",
                "stress_key": "REF_stress",
            }
        },
    }


def _post_selection_internal_config(
    *, target: Path, valid: Path, replay: Path, replay_valid: Path, foundation: Path
) -> dict:
    heads = {
        POST_SELECTION_TARGET_HEAD_NAME: {
            "train_file": str(target),
            "valid_file": str(valid),
            "atomic_numbers": [1],
            "E0s": {"1": 0.0},
            "energy_key": "REF_energy",
            "forces_key": "REF_forces",
            "stress_key": "REF_stress",
        },
        POST_SELECTION_REPLAY_HEAD_NAME: {
            "train_file": str(replay),
            "valid_file": str(replay_valid),
            "atomic_numbers": [1],
            "E0s": {"1": 0.0},
            "energy_key": "REF_energy",
            "forces_key": "REF_forces",
            "stress_key": "REF_stress",
        },
    }
    return {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "post-selection-execution-semantics",
        "seed": 19,
        "target_train_file": str(target),
        "target_valid_file": str(valid),
        "pt_train_file": str(replay),
        "pt_valid_file": str(replay_valid),
        "atomic_numbers": [1],
        "E0s": {"1": 0.0},
        "energy_key": "REF_energy",
        "forces_key": "REF_forces",
        "stress_key": "REF_stress",
        "lr": 0.0123,
        "loss": "stress",
        "energy_weight": 2.0,
        "forces_weight": 7.0,
        "stress_weight": 3.0,
        "batch_size": 2,
        "valid_batch_size": 2,
        "num_workers": 0,
        "max_num_epochs": 1,
        "ema": True,
        "ema_decay": 0.87,
        "amsgrad": True,
        "weight_decay": 0.0,
        "clip_grad": 10.0,
        "default_dtype": "float64",
        "device": "cpu",
        "foundation_model": str(foundation),
        "foundation_head": POST_SELECTION_TARGET_HEAD_NAME,
        "multiheads_finetuning": True,
        "force_mh_ft_lr": True,
        "real_pt_data_ratio_threshold": 0.0,
        "target_head_name": POST_SELECTION_TARGET_HEAD_NAME,
        "replay_head_name": POST_SELECTION_REPLAY_HEAD_NAME,
        "heads": heads,
        "mace_architecture": _architecture(),
    }


def _run_with_real_parser_and_loader(
    monkeypatch: pytest.MonkeyPatch,
    *,
    config: dict,
    authority: dict,
    config_path: Path,
) -> tuple[object, dict, dict]:
    """Run real parser/run_train through loss and loader resolution only."""

    import mace.cli.run_train as run_train_module
    from mace.tools.arg_parser import build_default_arg_parser

    config = dict(config)
    config.update(
        {
            "work_dir": str(config_path.parent),
            "model_dir": str(config_path.parent / "models"),
            "checkpoints_dir": str(config_path.parent / "checkpoints"),
            "log_dir": str(config_path.parent / "logs"),
            "results_dir": str(config_path.parent / "results"),
        }
    )
    config_path.write_text(json.dumps(config, sort_keys=True), encoding="utf-8")
    args = build_default_arg_parser().parse_args(["--config", str(config_path)])
    base_run = getattr(run_train_module, "_mdstats_original_run", run_train_module.run)
    run_train_module.run = base_run
    for name in (
        "_mdstats_original_run",
        "_mdstats_execution_semantics_patched",
        "_mdstats_execution_semantics_role",
    ):
        if hasattr(run_train_module, name):
            delattr(run_train_module, name)
    previous_authority = os.environ.get(MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE)
    monkeypatch.setenv(
        MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
        mace_execution_authority_to_environment(authority),
    )
    old_argv = list(sys.argv)
    sys.argv[:] = ["mdstats-mace-train", "train"]
    captured: dict = {}
    try:
        _install_mace_restart_epoch_patch()

        def stop_train(**kwargs):
            captured.update(kwargs)
            raise _StopAfterResolution()

        monkeypatch.setattr(run_train_module.tools, "train", stop_train)
        with pytest.raises(_StopAfterResolution):
            run_train_module.run(args)
        evidence = mace_execution_evidence_from_environment()
        assert evidence is not None
        return args, evidence, captured
    finally:
        sys.argv[:] = old_argv
        if previous_authority is None:
            os.environ.pop(MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE, None)
        else:
            os.environ[MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE] = previous_authority
        run_train_module.run = base_run
        for name in (
            "_mdstats_original_run",
            "_mdstats_execution_semantics_patched",
            "_mdstats_execution_semantics_role",
        ):
            if hasattr(run_train_module, name):
                delattr(run_train_module, name)


@pytest.mark.parametrize("target_count,target_batches", ((5, 3), (4, 2)))
def test_real_target_run_train_retains_target_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    target_count: int,
    target_batches: int,
) -> None:
    target_uids = _write_frames(
        tmp_path / "target.extxyz", count=target_count, prefix="target"
    )
    _write_frames(tmp_path / "valid.extxyz", count=2, prefix="valid")
    internal = _target_internal_config(
        target=tmp_path / "target.extxyz", valid=tmp_path / "valid.extxyz"
    )
    config = mace_run_configuration(internal)
    authority = build_mace_execution_authority(
        role="target_size",
        config_digest=digest(internal),
        method_identity_digest=digest({"method": "target-size-test"}),
        loss_family="stress",
        learning_rate=0.0123,
        ema=False,
        ema_decay=None,
        multiheads_finetuning=False,
        force_mh_ft_lr=None,
        real_pt_data_ratio_threshold=None,
        target_train_count=target_count,
        replay_train_count=0,
        batch_size=2,
        target_updates_per_epoch=target_batches,
        target_drop_last=False,
        distributed_allowed=False,
        target_frame_uid_set_digest=mace_frame_uid_set_digest(target_uids),
        replay_frame_uid_set_digest=None,
        target_head_name=TARGET_SIZE_MACE_HEAD_NAME,
        replay_head_name="pt_head",
    )
    args, evidence, _captured = _run_with_real_parser_and_loader(
        monkeypatch,
        config=config,
        authority=authority,
        config_path=tmp_path / "target-config.yaml",
    )
    assert args.loss == "stress"
    assert evidence["loss_class"] == "mace.modules.loss.WeightedEnergyForcesStressLoss"
    assert evidence["target_train_count"] == target_count
    assert evidence["target_updates_per_epoch"] == target_batches
    assert evidence["target_drop_last"] is False
    assert evidence["target_frame_uid_set_digest"] == mace_frame_uid_set_digest(target_uids)


def test_real_single_head_post_selection_uses_pinned_default_head(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ordinary P5/final single-head configs resolve MACE's ``Default`` head."""

    target_uids = _write_frames(tmp_path / "target.extxyz", count=5, prefix="target")
    _write_frames(tmp_path / "valid.extxyz", count=2, prefix="valid")
    internal = _target_internal_config(
        target=tmp_path / "target.extxyz", valid=tmp_path / "valid.extxyz"
    )
    config = mace_run_configuration(internal)
    config.pop("heads")
    config["multiheads_finetuning"] = False
    authority = build_mace_execution_authority(
        role="post_selection",
        config_digest=digest(internal),
        method_identity_digest=digest({"method": "post-selection-single-head-test"}),
        loss_family="stress",
        learning_rate=0.0123,
        ema=False,
        ema_decay=None,
        multiheads_finetuning=False,
        force_mh_ft_lr=None,
        real_pt_data_ratio_threshold=None,
        target_train_count=5,
        replay_train_count=0,
        batch_size=2,
        target_updates_per_epoch=None,
        target_drop_last=None,
        distributed_allowed=False,
        target_frame_uid_set_digest=mace_frame_uid_set_digest(target_uids),
        replay_frame_uid_set_digest=None,
        target_head_name="Default",
        replay_head_name="pt_head",
    )
    args, evidence, _captured = _run_with_real_parser_and_loader(
        monkeypatch,
        config=config,
        authority=authority,
        config_path=tmp_path / "single-head-config.yaml",
    )
    assert args.multiheads_finetuning is False
    assert evidence["loss_class"] == "mace.modules.loss.WeightedEnergyForcesStressLoss"
    assert evidence["target_train_count"] == 5
    assert evidence["replay_train_count"] == 0


def test_real_multihead_run_train_retains_native_loss_and_replay_controls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target_uids = _write_frames(tmp_path / "target.extxyz", count=5, prefix="target")
    _write_frames(tmp_path / "target-valid.extxyz", count=2, prefix="target-valid")
    replay_uids = _write_frames(tmp_path / "replay.extxyz", count=60, prefix="replay")
    _write_frames(tmp_path / "replay-valid.extxyz", count=2, prefix="replay-valid")

    from tests._mlff_tiny_mace import _tiny_mace

    foundation = tmp_path / "foundation.model"
    torch = pytest.importorskip("torch")
    torch.save(
        _tiny_mace(
            atomic_numbers=(1,),
            heads=[POST_SELECTION_TARGET_HEAD_NAME],
            dtype=torch.float64,
        ),
        foundation,
    )
    internal = _post_selection_internal_config(
        target=tmp_path / "target.extxyz",
        valid=tmp_path / "target-valid.extxyz",
        replay=tmp_path / "replay.extxyz",
        replay_valid=tmp_path / "replay-valid.extxyz",
        foundation=foundation,
    )
    config = post_selection_mace_run_configuration(internal)
    authority = build_mace_execution_authority(
        role="post_selection",
        config_digest=digest(internal),
        method_identity_digest=digest({"method": "post-selection-test"}),
        loss_family="stress",
        learning_rate=0.0123,
        ema=True,
        ema_decay=0.87,
        multiheads_finetuning=True,
        force_mh_ft_lr=True,
        real_pt_data_ratio_threshold=0.0,
        target_train_count=5,
        replay_train_count=60,
        batch_size=2,
        target_updates_per_epoch=None,
        target_drop_last=None,
        distributed_allowed=True,
        target_frame_uid_set_digest=mace_frame_uid_set_digest(target_uids),
        replay_frame_uid_set_digest=mace_frame_uid_set_digest(replay_uids),
        target_head_name=POST_SELECTION_TARGET_HEAD_NAME,
        replay_head_name=POST_SELECTION_REPLAY_HEAD_NAME,
    )
    args, evidence, captured = _run_with_real_parser_and_loader(
        monkeypatch,
        config=config,
        authority=authority,
        config_path=tmp_path / "post-selection-config.yaml",
    )
    assert args.loss == "stress"
    assert args.lr == pytest.approx(0.0123)
    assert args.ema is True
    assert args.ema_decay == pytest.approx(0.87)
    assert args.force_mh_ft_lr is True
    assert args.real_pt_data_ratio_threshold == 0.0
    assert evidence["loss_class"] == "mace.modules.loss.WeightedEnergyForcesStressLoss"
    assert evidence["target_duplication_factor"] == 1
    assert evidence["target_train_count"] == 5
    assert evidence["replay_train_count"] == 60

    loss_fn = captured["loss_fn"]
    assert float(loss_fn.energy_weight) == pytest.approx(2.0)
    assert float(loss_fn.forces_weight) == pytest.approx(7.0)
    assert float(loss_fn.stress_weight) == pytest.approx(3.0)
    reference = next(iter(captured["train_loader"]))
    prediction = {
        "energy": reference["energy"] + 0.3,
        "forces": reference["forces"] + 0.05,
        "stress": reference["stress"] + 0.02,
    }
    observed = float(loss_fn(ref=reference, pred=prediction, ddp=False))
    atoms_per_config = reference.ptr[1:] - reference.ptr[:-1]
    expected_energy = torch.mean(
        reference.weight
        * reference.energy_weight
        * torch.square((reference["energy"] - prediction["energy"]) / atoms_per_config)
    )
    repeated_weight = torch.repeat_interleave(
        reference.weight, atoms_per_config
    ).unsqueeze(-1)
    repeated_forces_weight = torch.repeat_interleave(
        reference.forces_weight, atoms_per_config
    ).unsqueeze(-1)
    expected_forces = torch.mean(
        repeated_weight
        * repeated_forces_weight
        * torch.square(reference["forces"] - prediction["forces"])
    )
    expected_stress = torch.mean(
        reference.stress_weight.view(-1, 1, 1)
        * torch.square(reference["stress"] - prediction["stress"])
    )
    expected = (
        2.0 * expected_energy + 7.0 * expected_forces + 3.0 * expected_stress
    )
    assert observed == pytest.approx(float(expected))
