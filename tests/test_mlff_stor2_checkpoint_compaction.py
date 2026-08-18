from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data import campaign_execution


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(path: Path, *, epoch: int = 3, run_digest: str = "1" * 64) -> mdstats.CheckpointFileRecord:
    return mdstats.CheckpointFileRecord(
        run_plan_digest=run_digest,
        candidate_id=f"run:epoch-{epoch}",
        epoch=epoch,
        relative_path=path.name,
        sha256=_sha(path),
        size_bytes=path.stat().st_size,
    )


def _checkpoint(path: Path, model, *, extra_optimizer_elements: int = 100_000) -> mdstats.CheckpointFileRecord:
    import torch

    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": {
                "state": {
                    0: {
                        "exp_avg": torch.ones(extra_optimizer_elements, dtype=torch.float32),
                        "exp_avg_sq": torch.ones(extra_optimizer_elements, dtype=torch.float32),
                    }
                }
            },
            "lr_scheduler": {"last_epoch": 3},
        },
        path,
    )
    return _record(path)


def test_stor2_capsule_is_smaller_and_reconstructs_exact_model_state(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    yaml = pytest.importorskip("yaml")

    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    cache = run_root / "checkpoint-model-cache"
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(yaml.safe_dump({"name": "model", "seed": 1}), encoding="utf-8")

    template = torch.nn.Linear(3, 2)
    torch.save(template, models / "model.model")
    selected = torch.nn.Linear(3, 2)
    with torch.no_grad():
        selected.weight.copy_(torch.tensor([[1.0, 2.0, 3.0], [-1.0, 0.5, 4.0]]))
        selected.bias.copy_(torch.tensor([0.25, -0.75]))
    raw = run_root / "checkpoints" / "model_epoch-3.pt"
    raw.parent.mkdir()
    checkpoint = _checkpoint(raw, selected)

    capsule_path = run_root / "evaluation-capsules" / "epoch-0003.eval-state.pt"
    record = mdstats.create_mace_evaluation_state_capsule(
        checkpoint,
        raw,
        mace_config_path=config,
        cache_directory=cache,
        capsule_path=capsule_path,
    )
    assert raw.is_file()
    assert capsule_path.is_file()
    assert record.source_checkpoint_sha256 == checkpoint.sha256
    assert record.capsule_size_bytes < record.source_checkpoint_size_bytes
    assert record.saved_bytes > 0

    restored_path = mdstats.materialize_mace_checkpoint_model(
        checkpoint,
        capsule_path,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        evaluation_state_capsule=record,
        wrapper_path=tmp_path / "must-not-run",
    )
    restored = torch.load(restored_path, map_location="cpu", weights_only=False)
    for key, value in selected.state_dict().items():
        assert torch.equal(restored.state_dict()[key], value)


def test_stor2_capsule_corruption_fails_closed(tmp_path: Path) -> None:
    torch = pytest.importorskip("torch")
    yaml = pytest.importorskip("yaml")
    run_root = tmp_path / "run"
    (run_root / "models").mkdir(parents=True)
    model = torch.nn.Linear(2, 1)
    torch.save(model, run_root / "models" / "model.model")
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(yaml.safe_dump({"name": "model", "seed": 1}), encoding="utf-8")
    raw = run_root / "checkpoints" / "model_epoch-3.pt"
    raw.parent.mkdir()
    checkpoint = _checkpoint(raw, model, extra_optimizer_elements=10_000)
    capsule = run_root / "evaluation-capsules" / "epoch.eval-state.pt"
    record = mdstats.create_mace_evaluation_state_capsule(
        checkpoint,
        raw,
        mace_config_path=config,
        cache_directory=run_root / "checkpoint-model-cache",
        capsule_path=capsule,
    )
    with capsule.open("ab") as handle:
        handle.write(b"tamper")
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.load_validated_capsule_payload(record, capsule)


def test_prepare_evaluation_accepts_authenticated_capsule_identity(tmp_path: Path, monkeypatch) -> None:
    """CPU preparation may authenticate a capsule before accelerator materialization."""

    torch = pytest.importorskip("torch")
    yaml = pytest.importorskip("yaml")
    run_root = tmp_path / "run"
    (run_root / "models").mkdir(parents=True)
    model = torch.nn.Linear(2, 1)
    torch.save(model, run_root / "models" / "model.model")
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(yaml.safe_dump({"name": "model", "seed": 1}), encoding="utf-8")
    raw = run_root / "checkpoints" / "model_epoch-3.pt"
    raw.parent.mkdir()
    checkpoint = _checkpoint(raw, model, extra_optimizer_elements=10_000)
    capsule = run_root / "evaluation-capsules" / "epoch.eval-state.pt"
    record = mdstats.create_mace_evaluation_state_capsule(
        checkpoint,
        raw,
        mace_config_path=config,
        cache_directory=run_root / "checkpoint-model-cache",
        capsule_path=capsule,
    )

    # This test exercises the source authentication branch without needing a full
    # MACE/ASE monitor.  A changed capsule is rejected before monitor parsing.
    capsule.write_bytes(capsule.read_bytes() + b"x")
    run = type("Run", (), {"target_monitor_artifact_digest": "2" * 64})()
    artifact = type("Artifact", (), {"content_digest": "2" * 64, "sha256": "3" * 64})()
    with pytest.raises(mdstats.TrainingDataInputError, match="capsule"):
        campaign_execution.prepare_mace_checkpoint_evaluation(
            run,
            checkpoint,
            candidate_model_path=capsule,
            evaluation_state_capsule=record,
            target_monitor_path=tmp_path / "missing.xyz",
            target_monitor_artifact=artifact,
        )


def test_stor2_real_mace_capsule_preserves_energy_force_stress(tmp_path: Path, monkeypatch) -> None:
    """STOR2 numerical qualification on an actual MACE 0.3.16 model."""

    monkeypatch.setenv("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    torch = pytest.importorskip("torch")
    np = pytest.importorskip("numpy")
    yaml = pytest.importorskip("yaml")
    pytest.importorskip("mace")
    e3nn = pytest.importorskip("e3nn")
    from copy import deepcopy
    from mace import data, modules, tools

    table = tools.AtomicNumberTable([1, 8])
    model_config = dict(
        r_max=3.0,
        num_bessel=4,
        num_polynomial_cutoff=4,
        max_ell=1,
        interaction_cls=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
        interaction_cls_first=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
        num_interactions=2,
        num_elements=2,
        hidden_irreps=e3nn.o3.Irreps("8x0e + 8x1o"),
        MLP_irreps=e3nn.o3.Irreps("4x0e"),
        gate=torch.nn.functional.silu,
        atomic_energies=np.array([0.1, 0.2]),
        avg_num_neighbors=3.0,
        atomic_numbers=table.zs,
        correlation=2,
        radial_type="bessel",
    )
    template = modules.MACE(**model_config)
    candidate = deepcopy(template)
    with torch.no_grad():
        next(candidate.parameters()).add_(0.015625)

    run_root = tmp_path / "run"
    (run_root / "models").mkdir(parents=True)
    torch.save(template, run_root / "models" / "tiny-mace.model")
    raw = run_root / "checkpoints" / "tiny-mace_epoch-7.pt"
    raw.parent.mkdir()
    torch.save(
        {
            "model": candidate.state_dict(),
            "optimizer": {
                "state": {
                    0: {
                        "exp_avg": torch.ones(500_000, dtype=torch.float32),
                        "exp_avg_sq": torch.ones(500_000, dtype=torch.float32),
                    }
                }
            },
            "lr_scheduler": {"last_epoch": 7},
        },
        raw,
    )
    checkpoint = _record(raw, epoch=7)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump({"name": "tiny-mace", "seed": 11, "enable_cueq": False}),
        encoding="utf-8",
    )
    capsule_path = run_root / "evaluation-capsules" / "epoch-0007.eval-state.pt"
    capsule = mdstats.create_mace_evaluation_state_capsule(
        checkpoint,
        raw,
        mace_config_path=config,
        cache_directory=run_root / "checkpoint-model-cache",
        capsule_path=capsule_path,
    )
    restored_path = mdstats.materialize_mace_checkpoint_model(
        checkpoint,
        capsule_path,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=run_root / "checkpoint-model-cache",
        evaluation_state_capsule=capsule,
        wrapper_path=tmp_path / "must-not-run",
    )
    restored = torch.load(restored_path, map_location="cpu", weights_only=False)

    atoms_config = data.Configuration(
        atomic_numbers=np.array([8, 1, 1]),
        positions=np.array([[0.0, 0.0, 0.0], [0.9, 0.0, 0.0], [-0.2, 0.8, 0.0]]),
        properties={},
        property_weights={},
    )
    atomic_data = data.AtomicData.from_config(atoms_config, z_table=table, cutoff=3.0)
    loader = tools.torch_geometric.dataloader.DataLoader(
        dataset=[atomic_data], batch_size=1, shuffle=False, drop_last=False
    )
    batch = next(iter(loader)).to_dict()
    expected = candidate(batch, training=False, compute_force=True, compute_stress=True)
    actual = restored(batch, training=False, compute_force=True, compute_stress=True)
    for key in ("energy", "forces", "stress"):
        assert torch.allclose(actual[key], expected[key], rtol=0.0, atol=0.0), key
