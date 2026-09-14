"""Bounded real-MACE acceptance for the reopened execution-semantics seam."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

pytest.importorskip("torch")
pytest.importorskip("e3nn")
pytest.importorskip("mace")

from ase import Atoms
from ase.io import write

from mdstats.training_data._common import TrainingDataInputError, digest
from mdstats.training_data.campaign_target_size_runtime import (
    TARGET_SIZE_MACE_HEAD_NAME,
    mace_run_configuration,
)
from mdstats.training_data.critical_precision_cli import (
    _annotate_mace_collections_with_exported_uids,
    _install_mace_restart_epoch_patch,
)
from mdstats.training_data.mace_compatibility import (
    MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
    MACE_REPLAY_IDENTITY_DOMAIN_CANONICAL,
    _mace_execution_membership_values,
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
    _mace_execution_frame_uid_set_digest,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.replay import canonical_replay_geometry_identity
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


def _write_replay_geometry_frames(
    path: Path, *, count: int, prefix: str
) -> tuple[str, ...]:
    """Write single-source-style replay transport without target frame UIDs."""

    frames = []
    identities = []
    for index in range(count):
        atoms = Atoms(
            "H2",
            positions=((0.0, 0.0, 0.0), (0.75 + 0.01 * index, 0.0, 0.0)),
            cell=(8.0, 8.0, 8.0),
            pbc=True,
        )
        identity = canonical_replay_geometry_identity(atoms)
        identities.append(identity)
        atoms.info.update(
            {
                "REF_energy": float(index) * 0.01,
                "REF_stress": np.zeros(6, dtype=float),
                "replay_geometry_identity": identity,
                "config_weight": 1.0,
                "config_energy_weight": 1.0,
                "config_forces_weight": 1.0,
                "config_stress_weight": 1.0,
            }
        )
        atoms.arrays["REF_forces"] = np.zeros((2, 3), dtype=float)
        frames.append(atoms)
    write(path, frames, format="extxyz")
    return tuple(identities)


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
        "training_mode": "multihead_replay",
        "loss": "universal",
        "huber_delta": 0.01,
        "energy_weight": 1.0,
        "forces_weight": 10.0,
        "stress_weight": 1.0,
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
        training_mode="scratch",
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
    assert evidence["training_mode"] == "scratch"
    assert evidence["huber_delta"] is None
    assert evidence["ordered_head_layout"] == ["Default"]
    assert evidence["target_train_count"] == 5
    assert evidence["replay_train_count"] == 0


def _foundation_authority(
    *,
    training_mode: str,
    target_uids: tuple[str, ...],
    replay_uids: tuple[str, ...] = (),
    batch_size: int = 2,
    ema: bool = True,
    **overrides,
) -> dict:
    multihead = training_mode == "multihead_replay"
    values = dict(
        role="post_selection",
        config_digest=digest({"config": training_mode}),
        method_identity_digest=digest({"method": training_mode}),
        training_mode=training_mode,
        loss_family="universal",
        huber_delta=0.01,
        energy_weight=1.0,
        forces_weight=10.0,
        stress_weight=1.0,
        learning_rate=0.0123,
        ema=ema,
        ema_decay=0.87 if ema else None,
        multiheads_finetuning=multihead,
        force_mh_ft_lr=True if multihead else None,
        real_pt_data_ratio_threshold=0.0 if multihead else None,
        target_train_count=len(target_uids),
        replay_train_count=len(replay_uids),
        batch_size=batch_size,
        target_updates_per_epoch=None,
        target_drop_last=None,
        distributed_allowed=False,
        target_frame_uid_set_digest=mace_frame_uid_set_digest(target_uids),
        replay_frame_uid_set_digest=(
            mace_frame_uid_set_digest(replay_uids) if replay_uids else None
        ),
        target_head_name=(
            POST_SELECTION_TARGET_HEAD_NAME if multihead else "Default"
        ),
        replay_head_name=POST_SELECTION_REPLAY_HEAD_NAME,
    )
    values.update(overrides.pop("authority", {}))
    values.update(overrides)
    return build_mace_execution_authority(**values)


def _huber(x, delta):
    import torch

    absolute = torch.abs(x)
    return torch.where(
        absolute <= delta, 0.5 * torch.square(x), delta * (absolute - 0.5 * delta)
    )


def _hand_universal_loss(reference, prediction, *, delta: float = 0.01):
    """D2 foundation-P5 robust objective, written from the method, not from MACE."""

    import torch

    atoms = (reference.ptr[1:] - reference.ptr[:-1]).to(reference["energy"].dtype)
    energy = torch.mean(
        _huber(
            reference.energy_weight * (reference["energy"] - prediction["energy"]) / atoms,
            delta,
        )
    )
    mask = torch.repeat_interleave(
        reference.forces_weight, reference.ptr[1:] - reference.ptr[:-1]
    ).unsqueeze(-1)
    masked_reference = mask * reference["forces"]
    norm = torch.linalg.norm(masked_reference, dim=-1, keepdim=True)
    factor = torch.where(
        norm < 100.0,
        torch.ones_like(norm),
        torch.where(
            norm < 200.0,
            0.7 * torch.ones_like(norm),
            torch.where(norm < 300.0, 0.4 * torch.ones_like(norm), 0.1 * torch.ones_like(norm)),
        ),
    )
    forces = torch.mean(
        _huber(masked_reference - mask * prediction["forces"], delta * factor)
    )
    stress_mask = reference.stress_weight.view(-1, 1, 1)
    stress = torch.mean(
        _huber(stress_mask * (reference["stress"] - prediction["stress"]), delta)
    )
    return 1.0 * energy + 10.0 * forces + 1.0 * stress


def test_real_multihead_run_train_realizes_foundation_universal_loss_and_exposure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multihead foundation P5 executes native UniversalLoss over replay-first data."""

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
    config = post_selection_mace_run_configuration(
        internal, foundation_model_path=foundation
    )
    authority = _foundation_authority(
        training_mode="multihead_replay",
        target_uids=target_uids,
        replay_uids=replay_uids,
    )
    args, evidence, captured = _run_with_real_parser_and_loader(
        monkeypatch,
        config=config,
        authority=authority,
        config_path=tmp_path / "post-selection-config.yaml",
    )
    assert args.loss == "universal"
    assert args.huber_delta == 0.01
    assert args.lr == pytest.approx(0.0123)
    assert args.ema is True
    assert args.ema_decay == pytest.approx(0.87)
    assert args.force_mh_ft_lr is True
    assert args.real_pt_data_ratio_threshold == 0.0
    assert evidence["loss_class"] == "mace.modules.loss.UniversalLoss"
    assert (
        evidence["huber_delta"],
        evidence["energy_weight"],
        evidence["forces_weight"],
        evidence["stress_weight"],
    ) == (0.01, 1.0, 10.0, 1.0)
    assert evidence["stage_two_enabled"] is False
    assert evidence["target_duplication_factor"] == 1
    assert evidence["target_train_count"] == 5
    assert evidence["replay_train_count"] == 60
    # Native pt_head-first pre-shuffle corpus layout and single-process
    # drop_last geometry: floor((5 + 60) / 2) updates.
    assert evidence["ordered_head_layout"] == [
        POST_SELECTION_REPLAY_HEAD_NAME,
        POST_SELECTION_TARGET_HEAD_NAME,
    ]
    assert evidence["combined_drop_last"] is True
    assert evidence["distributed"] is False
    assert evidence["combined_updates_per_epoch"] == 32
    train_set = captured["train_loader"].dataset
    assert [len(item) for item in train_set.datasets] == [60, 5]

    loss_fn = captured["loss_fn"]
    assert type(loss_fn).__qualname__ == "UniversalLoss"
    reference = next(iter(captured["train_loader"]))
    prediction = {
        "energy": reference["energy"] + 0.3,
        "forces": reference["forces"] + 0.005,
        "stress": reference["stress"] + 0.02,
    }
    observed = float(loss_fn(ref=reference, pred=prediction, ddp=False))
    assert observed == pytest.approx(float(_hand_universal_loss(reference, prediction)))
    # General config_weight is neutral transport, not a foundation-P5 loss layer.
    reweighted = reference.clone()
    reweighted.weight = reweighted.weight * 7.5
    assert float(loss_fn(ref=reweighted, pred=prediction, ddp=False)) == pytest.approx(
        observed
    )


def test_hand_universal_loss_oracle_resolves_dimensional_regimes() -> None:
    """The D2 oracle distinguishes each property's Huber side and force regime."""

    torch = pytest.importorskip("torch")
    from mace.modules.loss import UniversalLoss

    reference = SimpleNamespace(
        ptr=torch.tensor([0, 2]),
        energy_weight=torch.tensor([1.0], dtype=torch.float64),
        forces_weight=torch.tensor([1.0], dtype=torch.float64),
        stress_weight=torch.tensor([1.0], dtype=torch.float64),
        weight=torch.tensor([3.0], dtype=torch.float64),
    )
    tensors = {
        "energy": torch.tensor([1.0], dtype=torch.float64),
        "forces": torch.tensor([[150.0, 0.0, 0.0], [0.0, 0.0, 0.0]], dtype=torch.float64),
        "stress": torch.zeros((1, 3, 3), dtype=torch.float64),
    }

    class _Batch(SimpleNamespace):
        def __getitem__(self, key):
            return tensors[key]

    batch = _Batch(**vars(reference))
    for energy_shift, force_shift, stress_shift in (
        (0.005, 0.004, 0.004),  # quadratic side for every channel
        (0.5, 0.2, 0.3),  # linear side; the 150 eV/A atom uses 0.7 * delta
    ):
        prediction = {
            "energy": tensors["energy"] + energy_shift,
            "forces": tensors["forces"] + force_shift,
            "stress": tensors["stress"] + stress_shift,
        }
        native = UniversalLoss(
            energy_weight=1.0, forces_weight=10.0, stress_weight=1.0, huber_delta=0.01
        )
        assert float(native(ref=batch, pred=prediction, ddp=False)) == pytest.approx(
            float(_hand_universal_loss(batch, prediction))
        )
        # A six-component Voigt stress mean is a different objective.
        voigt = torch.mean(
            _huber(
                (tensors["stress"] - prediction["stress"]).reshape(-1, 9)[:, [0, 4, 8, 5, 2, 1]],
                0.01,
            )
        )
        nine = torch.mean(_huber(tensors["stress"] - prediction["stress"], 0.01))
        if stress_shift:
            assert float(voigt) == pytest.approx(float(nine))  # uniform shift: equal
    off_diagonal = {
        "energy": tensors["energy"],
        "forces": tensors["forces"],
        "stress": torch.tensor(
            [[[0.0, 0.3, 0.0], [0.3, 0.0, 0.0], [0.0, 0.0, 0.0]]], dtype=torch.float64
        ),
    }
    nine = torch.mean(_huber(-off_diagonal["stress"], 0.01))
    voigt = torch.mean(_huber(-off_diagonal["stress"].reshape(-1, 9)[:, [0, 4, 8, 5, 2, 1]], 0.01))
    assert float(nine) != pytest.approx(float(voigt))


def test_real_naive_foundation_run_train_uses_universal_loss_and_drop_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Single-head foundation P5 does not inherit P3/scratch weighted semantics."""

    target_uids = _write_frames(tmp_path / "target.extxyz", count=5, prefix="target")
    _write_frames(tmp_path / "valid.extxyz", count=2, prefix="valid")
    internal = _target_internal_config(
        target=tmp_path / "target.extxyz", valid=tmp_path / "valid.extxyz"
    )
    config = mace_run_configuration(internal)
    config.pop("heads")
    config.update(
        {
            "multiheads_finetuning": False,
            "loss": "universal",
            "huber_delta": 0.01,
            "energy_weight": 1.0,
            "forces_weight": 10.0,
            "stress_weight": 1.0,
        }
    )
    authority = _foundation_authority(
        training_mode="naive_fine_tuning", target_uids=target_uids, ema=False
    )
    args, evidence, captured = _run_with_real_parser_and_loader(
        monkeypatch,
        config=config,
        authority=authority,
        config_path=tmp_path / "naive-config.yaml",
    )
    assert args.loss == "universal"
    assert evidence["loss_class"] == "mace.modules.loss.UniversalLoss"
    assert evidence["ordered_head_layout"] == ["Default"]
    assert evidence["combined_drop_last"] is True
    assert evidence["combined_updates_per_epoch"] == 2
    assert len(captured["train_loader"]) == 2


@pytest.mark.parametrize(
    "overrides,match",
    (
        ({"loss_family": "stress"}, "universal"),
        ({"huber_delta": 0.02}, "huber_delta"),
        ({"forces_weight": 100.0}, "forces_weight"),
        ({"distributed_allowed": True}, "single-process"),
        ({"authority": {"training_mode": "scratch"}}, "stress"),
        ({"authority": {"training_mode": None}}, "training mode"),
    ),
)
def test_foundation_execution_authority_rejects_nonconforming_method(
    overrides: dict, match: str
) -> None:
    with pytest.raises(TrainingDataInputError, match=match):
        _foundation_authority(
            training_mode="multihead_replay",
            target_uids=("t",),
            replay_uids=("r",),
            **overrides,
        )


def test_target_size_and_scratch_authority_keep_weighted_loss() -> None:
    """Restoring foundation P5 does not globally flip P3 or P5 scratch."""

    common = dict(
        config_digest="a" * 64,
        learning_rate=0.01,
        ema=False,
        ema_decay=None,
        multiheads_finetuning=False,
        force_mh_ft_lr=None,
        real_pt_data_ratio_threshold=None,
        target_train_count=4,
        replay_train_count=0,
        batch_size=2,
        target_frame_uid_set_digest=None,
        replay_frame_uid_set_digest=None,
    )
    for role, extra in (
        ("target_size", {"target_updates_per_epoch": 2, "target_drop_last": False, "distributed_allowed": False}),
        ("post_selection", {"training_mode": "scratch", "distributed_allowed": True}),
    ):
        authority = build_mace_execution_authority(
            role=role, loss_family="stress", **common, **extra
        )
        assert authority["loss_family"] == "stress"
        with pytest.raises(TrainingDataInputError):
            build_mace_execution_authority(
                role=role, loss_family="universal", huber_delta=0.01,
                energy_weight=1.0, forces_weight=10.0, stress_weight=1.0,
                **common, **extra,
            )


def test_foundation_evidence_rejects_reversed_corpus_layout_and_truncation_drift() -> None:
    from mdstats.training_data.mace_compatibility import record_mace_execution_evidence

    authority = _foundation_authority(
        training_mode="multihead_replay", target_uids=("t0", "t1"), replay_uids=("r0",)
    )
    evidence = {
        "role": "post_selection",
        "training_mode": "multihead_replay",
        "loss_family": "universal",
        "loss_class": "mace.modules.loss.UniversalLoss",
        "huber_delta": 0.01,
        "energy_weight": 1.0,
        "forces_weight": 10.0,
        "stress_weight": 1.0,
        "stage_two_enabled": False,
        "learning_rate": 0.0123,
        "ema": True,
        "ema_decay": 0.87,
        "multiheads_finetuning": True,
        "force_mh_ft_lr": True,
        "real_pt_data_ratio_threshold": 0.0,
        "target_train_count": 2,
        "replay_train_count": 1,
        "target_duplication_factor": 1,
        "target_batch_size": 2,
        "target_updates_per_epoch": None,
        "target_drop_last": None,
        "distributed": False,
        "target_frame_uid_set_digest": authority["target_frame_uid_set_digest"],
        "replay_frame_uid_set_digest": authority["replay_frame_uid_set_digest"],
        "combined_train_count": 3,
        "ordered_head_layout": [POST_SELECTION_REPLAY_HEAD_NAME, POST_SELECTION_TARGET_HEAD_NAME],
        "combined_drop_last": True,
        "combined_updates_per_epoch": 1,
    }
    assert record_mace_execution_evidence(authority, evidence)["resolved_evidence"]
    for key, value, match in (
        ("ordered_head_layout", [POST_SELECTION_TARGET_HEAD_NAME, POST_SELECTION_REPLAY_HEAD_NAME], "layout"),
        ("combined_drop_last", False, "drop_last"),
        ("combined_updates_per_epoch", 2, "floor"),
        ("loss_class", "mace.modules.loss.WeightedEnergyForcesStressLoss", "UniversalLoss"),
        ("stage_two_enabled", True, "stage-two"),
    ):
        with pytest.raises(TrainingDataInputError, match=match):
            record_mace_execution_evidence(authority, {**evidence, key: value})


def test_replay_block_order_is_method_bearing_under_a_fixed_seed() -> None:
    """Swapping replay/target corpus blocks changes the shuffled example mapping."""

    torch = pytest.importorskip("torch")
    replay = [f"r{i}" for i in range(6)]
    target = [f"t{i}" for i in range(3)]
    permutation = torch.randperm(9, generator=torch.Generator().manual_seed(19)).tolist()
    replay_first = [(replay + target)[index] for index in permutation]
    target_first = [(target + replay)[index] for index in permutation]
    assert replay_first != target_first


def test_real_multihead_single_source_replay_uses_geometry_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real MACE loader authenticates replay geometry identity without UID metadata."""

    target_uids = _write_frames(
        tmp_path / "target.extxyz", count=5, prefix="target"
    )
    _write_frames(tmp_path / "target-valid.extxyz", count=2, prefix="target-valid")
    replay_identities = _write_replay_geometry_frames(
        tmp_path / "replay.extxyz", count=6, prefix="replay"
    )
    _write_replay_geometry_frames(
        tmp_path / "replay-valid.extxyz", count=2, prefix="replay-valid"
    )

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
    config = post_selection_mace_run_configuration(
        internal, foundation_model_path=foundation
    )
    authority = build_mace_execution_authority(
        role="post_selection",
        config_digest=digest(internal),
        method_identity_digest=digest({"method": "single-source-replay-test"}),
        training_mode="multihead_replay",
        loss_family="universal",
        huber_delta=0.01,
        energy_weight=1.0,
        forces_weight=10.0,
        stress_weight=1.0,
        learning_rate=0.0123,
        ema=True,
        ema_decay=0.87,
        multiheads_finetuning=True,
        force_mh_ft_lr=True,
        real_pt_data_ratio_threshold=0.0,
        target_train_count=5,
        replay_train_count=6,
        batch_size=2,
        target_updates_per_epoch=None,
        target_drop_last=None,
        distributed_allowed=False,
        target_frame_uid_set_digest=mace_frame_uid_set_digest(target_uids),
        replay_frame_uid_set_digest=mace_frame_uid_set_digest(replay_identities),
        target_head_name=POST_SELECTION_TARGET_HEAD_NAME,
        replay_head_name=POST_SELECTION_REPLAY_HEAD_NAME,
    )
    _args, evidence, _captured = _run_with_real_parser_and_loader(
        monkeypatch,
        config=config,
        authority=authority,
        config_path=tmp_path / "single-source-replay-config.yaml",
    )
    assert evidence["target_train_count"] == 5
    assert evidence["replay_train_count"] == 6
    assert evidence["target_frame_uid_set_digest"] == mace_frame_uid_set_digest(
        target_uids
    )
    assert evidence["replay_frame_uid_set_digest"] == mace_frame_uid_set_digest(
        replay_identities
    )
    assert _mace_execution_membership_values(
        tmp_path / "replay.extxyz", role="replay", head_name="pt_head"
    ) == replay_identities


def test_replay_execution_membership_rejects_mixed_identity_domains(tmp_path: Path) -> None:
    """A replay file cannot select identity fields independently per frame."""

    path = tmp_path / "mixed-replay.extxyz"
    _write_replay_geometry_frames(path, count=2, prefix="replay")
    from ase.io import read, write

    frames = read(path, index=":", format="extxyz")
    frames[0].info["frame_uid"] = "legacy-frame-0"
    write(path, frames, format="extxyz")
    with pytest.raises(TrainingDataInputError, match="identity"):
        _mace_execution_membership_values(
            path, role="replay", head_name=POST_SELECTION_REPLAY_HEAD_NAME
        )


def test_post_selection_launch_resolves_single_source_replay_identity(
    tmp_path: Path,
) -> None:
    """The P5 launch owner binds its replay artifact to existing geometry identity."""

    path = tmp_path / "replay.extxyz"
    identities = _write_replay_geometry_frames(path, count=3, prefix="replay")
    artifact = SimpleNamespace(path=path, configuration_count=len(identities))

    assert _mace_execution_frame_uid_set_digest(
        artifact, role="replay"
    ) == mace_frame_uid_set_digest(identities)


@pytest.mark.parametrize("periodic", [False, True])
def test_canonical_replay_identity_is_stable_across_mace_configuration_boundary(
    periodic: bool,
) -> None:
    """The existing canonical identity survives source-to-MACE representation."""

    from mace.data import Configuration

    atoms = Atoms(
        "H2",
        positions=((0.0, 0.0, 0.0), (0.75, 0.0, 0.0)),
        cell=(8.0, 8.0, 8.0) if periodic else None,
        pbc=periodic,
    )
    loaded = Configuration(
        atomic_numbers=np.asarray(atoms.numbers, dtype=np.int64),
        positions=np.asarray(atoms.positions, dtype=np.float64),
        properties={},
        property_weights={},
        cell=None if not periodic else np.asarray(atoms.cell.array, dtype=np.float64),
        pbc=None if not periodic else tuple(bool(value) for value in atoms.pbc),
    )
    assert canonical_replay_geometry_identity(atoms) == canonical_replay_geometry_identity(
        loaded
    )


def _canonical_domain_authority(*, target_digest: str, replay_digest: str) -> dict:
    return build_mace_execution_authority(
        role="post_selection",
        config_digest="a" * 64,
        method_identity_digest="b" * 64,
        training_mode="multihead_replay",
        loss_family="universal",
        huber_delta=0.01,
        energy_weight=1.0,
        forces_weight=10.0,
        stress_weight=1.0,
        learning_rate=0.0123,
        ema=False,
        ema_decay=None,
        multiheads_finetuning=True,
        force_mh_ft_lr=True,
        real_pt_data_ratio_threshold=0.0,
        target_train_count=1,
        replay_train_count=1,
        batch_size=1,
        target_updates_per_epoch=None,
        target_drop_last=None,
        distributed_allowed=False,
        target_frame_uid_set_digest=target_digest,
        replay_frame_uid_set_digest=replay_digest,
        target_head_name=POST_SELECTION_TARGET_HEAD_NAME,
        replay_head_name=POST_SELECTION_REPLAY_HEAD_NAME,
        replay_identity_domain=MACE_REPLAY_IDENTITY_DOMAIN_CANONICAL,
    )


def test_current_single_source_replay_domain_fails_without_file_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A canonical loaded-geometry mismatch cannot reopen replay ExtXYZ."""

    import mdstats.training_data.mace_compatibility as compatibility

    target_path = tmp_path / "target.extxyz"
    target_uid = _write_frames(target_path, count=1, prefix="target")[0]
    replay_path = tmp_path / "replay.extxyz"
    replay_path.write_text("not reread", encoding="utf-8")
    target_item = Atoms(
        "H2",
        positions=((0.0, 0.0, 0.0), (0.75, 0.0, 0.0)),
        cell=(8.0, 8.0, 8.0),
        pbc=True,
    )
    target_item.info["frame_uid"] = target_uid
    replay_item = Atoms(
        "H2",
        positions=((0.0, 0.0, 0.0), (0.75, 0.0, 0.0)),
        cell=(8.0, 8.0, 8.0),
        pbc=True,
    )
    expected_replay = canonical_replay_geometry_identity(replay_item)
    authority = _canonical_domain_authority(
        target_digest=mace_frame_uid_set_digest((target_uid,)),
        replay_digest=mace_frame_uid_set_digest((expected_replay,)),
    )
    monkeypatch.setenv(
        MACE_EXECUTION_AUTHORITY_ENVIRONMENT_VARIABLE,
        mace_execution_authority_to_environment(authority),
    )
    original_membership_values = compatibility._mace_execution_membership_values

    def fail_replay_file_scan(paths, *, role, head_name):
        if role == "replay":
            raise AssertionError("current canonical replay reopened its ExtXYZ")
        return original_membership_values(paths, role=role, head_name=head_name)

    monkeypatch.setattr(
        compatibility,
        "_mace_execution_membership_values",
        fail_replay_file_scan,
    )
    heads = [
        SimpleNamespace(
            head_name=POST_SELECTION_TARGET_HEAD_NAME,
            train_file=[target_path],
            collections=SimpleNamespace(train=[target_item]),
        ),
        SimpleNamespace(
            head_name=POST_SELECTION_REPLAY_HEAD_NAME,
            train_file=[replay_path],
            collections=SimpleNamespace(train=[replay_item]),
        ),
    ]

    _annotate_mace_collections_with_exported_uids(head_configs=heads)
    assert replay_item.frame_uid == expected_replay

    replay_item.positions[1, 0] += 1.0e-4
    with pytest.raises(RuntimeError, match="could not be authenticated"):
        _annotate_mace_collections_with_exported_uids(head_configs=heads)
