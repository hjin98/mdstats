"""Real pinned-MACE parity for the P5 TRAIN2 -> EVAL2 CuEq realization boundary.

Pinned MACE ``run_train`` is driven with the configuration projected by the real
P5 executable-configuration owner.  Its own e3nn -> CuEq conversion call is the
only seam: it records the portable model MACE built (A) and the CuEq model it
trains (C), then stops before optimisation.  The independent mdstats owners
rebuild the same method from the same configuration (B, D) and must agree with
what MACE actually constructed, including replay-only elements and the
``torch.device`` argument ``run_train`` gives the converter.
"""

from __future__ import annotations

import gc
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("mace")
pytest.importorskip("cuequivariance_torch")

from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.model_features import (
    build_mace_model_from_configuration,
    canonicalize_mace_candidate_architecture,
    mace_model_execution_architecture_digest,
    mace_model_execution_architecture_first_difference,
    realize_mace_training_model,
    restore_mace_portable_model,
)
from mdstats.training_data.post_selection_execution import (
    POST_SELECTION_MACE_CONFIG_SCHEMA,
    post_selection_mace_run_configuration,
)
from mdstats.training_data.target_size_execution.evaluation import (
    EVALUATION_MODEL_STATE_LIVE,
    authenticate_train2_checkpoint_provider,
)
from tests._mlff_tiny_mace import _tiny_mace


pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not torch.cuda.is_available(),
        reason="The phase-separated CuEq TRAIN2 realization is CUDA-specific.",
    ),
]

_TARGET_E0S = {"3": -1.5, "8": -4.5}


def _write_frames(path: Path, symbols: str, count: int) -> None:
    from ase import Atoms
    from ase.io import write

    frames = []
    for index in range(count):
        positions = [(0.8 + 0.3 * index, 0.8, 0.8), (3.2, 3.2, 3.2), (1.9, 3.0, 0.9)]
        atoms = Atoms(symbols, cell=np.eye(3) * 8.0, pbc=True)
        atoms.positions = positions[: len(atoms)]
        atoms.info["REF_energy"] = -10.0 + 0.01 * index
        atoms.arrays["REF_forces"] = np.full((len(atoms), 3), 0.01 * (index + 1))
        frames.append(atoms)
    path.parent.mkdir(parents=True, exist_ok=True)
    write(path, frames, format="extxyz")


@pytest.fixture(scope="module")
def captured(tmp_path_factory: pytest.TempPathFactory):
    """Run pinned ``run_train`` to its CuEq conversion and capture A and C."""

    import yaml
    from mace import tools
    import mace.cli.run_train as run_train

    root = tmp_path_factory.mktemp("p5-cueq-parity")
    foundation = root / "foundation.model"
    torch.save(
        _tiny_mace(
            interaction_cls_name="RealAgnosticResidualInteractionBlock",
            atomic_numbers=(1, 3, 8),
            heads=["default"],
            seed=7,
            dtype=torch.float64,
        ),
        foundation,
    )
    _write_frames(root / "target_train.extxyz", "LiO", 6)
    _write_frames(root / "target_valid.extxyz", "LiO", 2)
    # Replay carries hydrogen, which the target never contains.
    _write_frames(root / "replay_train.extxyz", "LiOH", 6)
    _write_frames(root / "replay_valid.extxyz", "LiOH", 2)

    head_keys = {"energy_key": "REF_energy", "forces_key": "REF_forces", "stress_key": "REF_stress"}
    payload = {
        "schema": POST_SELECTION_MACE_CONFIG_SCHEMA,
        "name": "p5-cueq-parity",
        "seed": 0,
        "target_train_file": "target_train.extxyz",
        "target_valid_file": "target_valid.extxyz",
        "atomic_numbers": [3, 8],
        "E0s": dict(_TARGET_E0S),
        **head_keys,
        "lr": 1.0e-3,
        "loss": "stress",
        "energy_weight": 1.0,
        "forces_weight": 10.0,
        "stress_weight": 1.0,
        "batch_size": 2,
        "valid_batch_size": 2,
        "num_workers": 0,
        "max_num_epochs": 1,
        "ema": False,
        "save_all_checkpoints": True,
        "amsgrad": True,
        "weight_decay": 0.0,
        "clip_grad": 10.0,
        "default_dtype": "float32",
        "device": "cuda",
        "compute_avg_num_neighbors": False,
        "mace_architecture": canonicalize_mace_candidate_architecture(None),
        "target_head_name": "target_head",
        "replay_head_name": "pt_head",
        "enable_cueq": True,
        "only_cueq": False,
        "foundation_head": "default",
        "multiheads_finetuning": True,
        "force_mh_ft_lr": True,
        "real_pt_data_ratio_threshold": 0.0,
        "pt_train_file": str(root / "replay_train.extxyz"),
        "pt_valid_file": str(root / "replay_valid.extxyz"),
        "heads": {
            "target_head": {
                "train_file": "target_train.extxyz",
                "valid_file": "target_valid.extxyz",
                "atomic_numbers": [3, 8],
                "E0s": dict(_TARGET_E0S),
                **head_keys,
            },
            "pt_head": dict(head_keys),
        },
    }
    executable = post_selection_mace_run_configuration(payload, foundation_model_path=foundation)
    config_path = root / "mace_run_config.yaml"
    config_path.write_text(yaml.safe_dump(executable, sort_keys=False), encoding="utf-8")

    class _Converted(Exception):
        pass

    seen: dict[str, object] = {}
    original = run_train.run_e3nn_to_cueq

    def capture(model, device):
        seen["portable"] = deepcopy(model)
        seen["device"] = device
        seen["training"] = original(model, device=device)
        raise _Converted

    previous_cwd = Path.cwd()
    previous_dtype = torch.get_default_dtype()
    patch = pytest.MonkeyPatch()
    patch.setattr(run_train, "run_e3nn_to_cueq", capture)
    try:
        import os

        os.chdir(root)
        args = tools.build_default_arg_parser().parse_args(
            [
                "--config", str(config_path),
                "--work_dir", str(root),
                "--model_dir", str(root / "models"),
                "--checkpoints_dir", str(root / "checkpoints"),
                "--log_dir", str(root / "logs"),
                "--results_dir", str(root / "results"),
            ]
        )
        with pytest.raises(_Converted):
            run_train.run(args)
    finally:
        patch.undo()
        os.chdir(previous_cwd)
        torch.set_default_dtype(previous_dtype)
    return SimpleNamespace(root=root, foundation=foundation, payload=payload, **seen)


def test_independent_reconstruction_is_the_model_run_train_built(captured) -> None:
    """A == B: portable parity, including the replay-only element."""

    assert 1 in [int(z) for z in captured.portable.atomic_numbers]
    reconstructed = build_mace_model_from_configuration(
        captured.payload, foundation_model_path=captured.foundation
    )
    assert (
        mace_model_execution_architecture_first_difference(captured.portable, reconstructed)
        is None
    )


def test_independent_cueq_realization_is_the_model_run_train_trains(captured) -> None:
    """C == D == F: CuEq parity with the torch.device run_train passes, deterministically."""

    assert isinstance(captured.device, torch.device)
    trained_digest = mace_model_execution_architecture_digest(captured.training)
    digests = []
    for _ in range(2):
        portable = build_mace_model_from_configuration(
            captured.payload, foundation_model_path=captured.foundation
        )
        realized, kind = realize_mace_training_model(portable, captured.payload)
        assert kind == "cueq"
        digests.append(mace_model_execution_architecture_digest(realized))
        del portable, realized
    assert digests == [trained_digest, trained_digest]


@pytest.fixture()
def checkpoint(captured, tmp_path: Path):
    """A native-shaped MACE raw checkpoint of the captured TRAIN2 CuEq model."""

    path = tmp_path / "run-0_epoch-0.pt"
    torch.save(
        {"model": captured.training.state_dict(), "optimizer": {}, "lr_scheduler": {}},
        path,
    )
    import hashlib

    summary = SimpleNamespace(
        model_architecture_digest=mace_model_execution_architecture_digest(captured.training),
        raw_checkpoint_epoch=1,
        ema_state_digest=None,
    )
    return path, hashlib.sha256(path.read_bytes()).hexdigest(), summary


def _authenticate(captured, checkpoint, payload, *, foundation):
    path, sha, summary = checkpoint
    return authenticate_train2_checkpoint_provider(
        raw_checkpoint_path=path,
        raw_checkpoint_sha256=sha,
        companion_path=None,
        companion_sha256=None,
        summary=summary,
        evaluation_model_state=EVALUATION_MODEL_STATE_LIVE,
        config_payload=payload,
        allow_forward_override=False,
        raw_checkpoint_epoch=0,
        foundation_model_path=foundation,
    )


def _perturbations(captured):
    without_replay_hydrogen = dict(captured.payload)
    without_replay_hydrogen["pt_train_file"] = str(captured.root / "target_train.extxyz")
    without_replay_hydrogen["pt_valid_file"] = str(captured.root / "target_valid.extxyz")
    return {
        "dtype": (dict(captured.payload, default_dtype="float64"), captured.foundation),
        "replay_elements": (without_replay_hydrogen, captured.foundation),
        "foundation": (captured.payload, None),
    }


@pytest.mark.parametrize("perturbation", ["dtype", "replay_elements", "foundation"])
def test_perturbed_method_is_rejected_before_state_load(
    captured, checkpoint, perturbation: str
) -> None:
    payload, foundation = _perturbations(captured)[perturbation]
    with pytest.raises(
        TrainingDataInputError,
        match=r"differ in the cueq realization: .*first_difference=",
    ):
        _authenticate(captured, checkpoint, payload, foundation=foundation)


def test_scratch_normalization_perturbation_is_rejected_before_state_load(
    captured, tmp_path: Path
) -> None:
    """Frozen avg_num_neighbors binds the scratch CuEq realization.

    With a foundation, pinned MACE takes the normalization from the foundation,
    so the configured value is only authoritative for scratch training.
    """

    import hashlib

    scratch = {
        key: value
        for key, value in captured.payload.items()
        if key
        not in {
            "foundation_head",
            "multiheads_finetuning",
            "force_mh_ft_lr",
            "real_pt_data_ratio_threshold",
            "pt_train_file",
            "pt_valid_file",
            "heads",
        }
    }
    trained, _kind = realize_mace_training_model(
        build_mace_model_from_configuration(scratch), scratch
    )
    path = tmp_path / "scratch_epoch-0.pt"
    torch.save({"model": trained.state_dict(), "optimizer": {}, "lr_scheduler": {}}, path)
    summary = SimpleNamespace(
        model_architecture_digest=mace_model_execution_architecture_digest(trained),
        raw_checkpoint_epoch=1,
        ema_state_digest=None,
    )
    del trained
    architecture = dict(scratch["mace_architecture"], avg_num_neighbors=2.5)
    with pytest.raises(
        TrainingDataInputError,
        match=r"differ in the cueq realization: .*first_difference=not visible in checkpoint state",
    ):
        _authenticate(
            captured,
            (path, hashlib.sha256(path.read_bytes()).hexdigest(), summary),
            dict(scratch, mace_architecture=architecture),
            foundation=None,
        )


def test_rejected_realization_does_not_stay_resident(captured, checkpoint) -> None:
    payload, foundation = _perturbations(captured)["replay_elements"]
    torch.cuda.synchronize()
    after = []
    for _ in range(3):
        with pytest.raises(TrainingDataInputError):
            _authenticate(captured, checkpoint, payload, foundation=foundation)
        gc.collect()
        torch.cuda.synchronize()
        after.append(torch.cuda.memory_allocated())
    assert after[2] <= after[0]


def test_authentic_state_reaches_the_portable_projection_guard(captured, checkpoint) -> None:
    """The authentic realization authenticates; EVAL2 then stops at A1 step 6.

    The raw state loads into the independently realized CuEq model.  The only
    remaining failure is the accepted portable round-trip guard, which the
    native pinned-MACE projection cannot satisfy for foundation-backed CuEq.
    """

    with pytest.raises(
        TrainingDataInputError,
        match=r"round-trip changed the portable architecture: realization=cueq; .*first_difference=parameters",
    ):
        _authenticate(captured, checkpoint, captured.payload, foundation=captured.foundation)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "SERIOUS CHALLENGE (D3 amendment A1 step 6): pinned MACE's native CuEq->e3nn "
        "projection rebuilds the model from extracted config, turning the foundation-"
        "loaded bessel_weights Parameter into a buffer and recomputing CG U-matrices, so "
        "a foundation-backed CuEq model cannot project back to its configuration's "
        "canonical portable architecture."
    ),
)
def test_native_projection_preserves_the_canonical_portable_architecture(captured) -> None:
    portable = build_mace_model_from_configuration(
        captured.payload, foundation_model_path=captured.foundation
    )
    projected = restore_mace_portable_model(captured.training, captured.payload)
    assert mace_model_execution_architecture_first_difference(portable, projected) is None
