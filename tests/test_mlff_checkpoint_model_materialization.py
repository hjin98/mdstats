from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import torch
import yaml

import mdstats


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(path: Path, *, epoch: int = 3) -> mdstats.CheckpointFileRecord:
    return mdstats.CheckpointFileRecord(
        run_plan_digest="a" * 64,
        candidate_id=f"run:epoch-{epoch}",
        epoch=epoch,
        relative_path=path.name,
        sha256=_sha(path),
        size_bytes=path.stat().st_size,
    )


def test_raw_mace_checkpoint_is_reconstructed_and_cached(tmp_path: Path) -> None:
    checkpoint = tmp_path / "old-name_epoch-3.pt"
    torch.save(
        {
            "model": {"weight": torch.tensor([1.0])},
            "optimizer": {},
            "lr_scheduler": {},
        },
        checkpoint,
    )
    record = _record(checkpoint)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "name": "qualified-model",
                "seed": 17,
                "heads": {"target_head": {}, "replay_head": {}},
            }
        ),
        encoding="utf-8",
    )
    marker = tmp_path / "wrapper-calls.txt"
    wrapper = tmp_path / "fake-mace-train"
    wrapper.write_text(
        "#!/usr/bin/env python\n"
        "import pathlib, sys, torch, yaml\n"
        f"marker = pathlib.Path({str(marker)!r})\n"
        "marker.write_text(marker.read_text() + 'x' if marker.exists() else 'x')\n"
        "args = sys.argv[1:]\n"
        "cfg = pathlib.Path(args[args.index('--config') + 1])\n"
        "payload = yaml.safe_load(cfg.read_text())\n"
        "out = pathlib.Path(payload['model_dir']) / (payload['name'] + '.model')\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "torch.save(torch.nn.Linear(1, 1), out)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    cache = tmp_path / "cache"

    first = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        wrapper_path=wrapper,
    )
    assert first.is_file()
    assert hasattr(torch.load(first, map_location="cpu", weights_only=False), "to")
    assert marker.read_text() == "x"

    second = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        wrapper_path=wrapper,
    )
    assert second == first
    assert marker.read_text() == "x"

    mdstats.remove_materialized_mace_checkpoint_model(second)
    assert not second.exists()
    assert not second.with_suffix(".json").exists()


def test_legacy_checkpoint_reconstruction_child_is_terminated_on_staged_cancellation(
    tmp_path: Path,
) -> None:
    from mdstats.training_data.inference_parallel import inference_start_signal

    checkpoint = tmp_path / "old-name_epoch-3.pt"
    torch.save(
        {
            "model": {"weight": torch.tensor([1.0])},
            "optimizer": {},
            "lr_scheduler": {},
        },
        checkpoint,
    )
    record = _record(checkpoint)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "name": "qualified-model",
                "seed": 17,
                "heads": {"target_head": {}, "replay_head": {}},
            }
        ),
        encoding="utf-8",
    )
    marker = tmp_path / "wrapper-started.txt"
    wrapper = tmp_path / "slow-mace-train"
    wrapper.write_text(
        "#!/usr/bin/env python\n"
        "import pathlib, time\n"
        f"pathlib.Path({str(marker)!r}).write_text('started')\n"
        "time.sleep(30.0)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    cache = tmp_path / "cache"
    phases: list[str] = []

    with inference_start_signal(
        lambda: None,
        phase_callback=phases.append,
        cancellation_requested=marker.exists,
    ):
        with pytest.raises(InterruptedError, match="cancelled"):
            mdstats.materialize_mace_checkpoint_model(
                record,
                checkpoint,
                mace_config_path=config,
                job_working_directory=job_root,
                cache_directory=cache,
                wrapper_path=wrapper,
            )

    assert marker.read_text() == "started"
    assert any("cancelled before legacy checkpoint reconstruction completion" in phase for phase in phases)
    assert not list(cache.glob(".*.staging-*"))


def test_deployable_model_is_used_without_reconstruction(tmp_path: Path) -> None:
    model = tmp_path / "candidate.model"
    torch.save(torch.nn.Linear(2, 1), model)
    record = _record(model, epoch=0)
    config = tmp_path / "config.yaml"
    config.write_text("name: unused\nseed: 1\n", encoding="utf-8")

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        model,
        mace_config_path=config,
        job_working_directory=tmp_path,
        cache_directory=tmp_path / "cache",
        wrapper_path=tmp_path / "does-not-exist",
    )
    assert resolved == model.resolve()


class _SingleHeadModel(torch.nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(1, 1)
        self.heads = ["target_head"]

    def forward(self, value):
        return self.linear(value)


def test_single_head_export_does_not_call_mace_select_head(tmp_path: Path) -> None:
    checkpoint = tmp_path / "candidate_epoch-0.pt"
    checkpoint.write_bytes(b"raw-checkpoint")
    checkpoint_sha = _sha(checkpoint)
    model = tmp_path / "candidate.model"
    torch.save(_SingleHeadModel(), model)
    run = mdstats.TrainingCampaignRunPlan(
        run_id="single-final",
        data8_bundle_digest="1" * 64,
        mace_job_artifact_digest="2" * 64,
        job_id="single-final",
        kind=mdstats.MaceJobKind.FINAL_DEVELOPMENT,
        fold_index=None,
        training_mode=mdstats.TrainingMode.NAIVE_FINE_TUNING,
        selection_size=1,
        seed=1,
        protocol_family_digest="3" * 64,
        protocol_variant_digest="4" * 64,
        protocol_digest="5" * 64,
        checkpoint_metric_policy_digest="6" * 64,
        target_monitor_artifact_digest="7" * 64,
        replay_monitor_artifact_digest=None,
        relative_output_directory="single-final",
    )
    decision = mdstats.CheckpointAdmissibilityDecision(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=checkpoint_sha,
        checkpoint_metric_record_digest="8" * 64,
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        outcome=mdstats.CheckpointAdmissibilityOutcome.ADMISSIBLE,
        primary_metric_name="force",
        primary_metric_value=0.1,
    )
    selection = mdstats.CheckpointSelectionRecord(
        run_plan_digest=run.content_digest,
        checkpoint_catalog_digest="9" * 64,
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        decisions=(decision,),
        selected_checkpoint_sha256=checkpoint_sha,
        selected_checkpoint_epoch=0,
        selected_primary_metric_value=0.1,
    )
    output = tmp_path / "target.model"
    member = mdstats.export_target_head_member(
        run,
        selection,
        checkpoint,
        output,
        source_model_path=model,
        policy=mdstats.CommitteeExportPolicy(
            target_head_name="target_head", target_device="cpu", minimum_members=1
        ),
        wrapper_path=tmp_path / "must-not-be-called",
    )
    assert output.is_file()
    restored = torch.load(output, map_location="cpu", weights_only=False)
    assert restored.heads == ["target_head"]
    assert member.source_checkpoint_sha256 == checkpoint_sha


def _linear_checkpoint(path: Path, model: torch.nn.Module, *, epoch: int = 2) -> mdstats.CheckpointFileRecord:
    torch.save(
        {
            "model": model.state_dict(),
            "optimizer": {},
            "lr_scheduler": {},
        },
        path,
    )
    return _record(path, epoch=epoch)


def test_raw_checkpoint_restores_directly_from_completed_training_model(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    cache = run_root / "checkpoint-model-cache"
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump({"name": "qualified-model", "seed": 17, "enable_cueq": False}),
        encoding="utf-8",
    )

    template = torch.nn.Linear(2, 1)
    with torch.no_grad():
        template.weight.fill_(1.0)
        template.bias.fill_(2.0)
    template_path = models / "qualified-model.model"
    torch.save(template, template_path)

    selected = torch.nn.Linear(2, 1)
    with torch.no_grad():
        selected.weight.copy_(torch.tensor([[3.0, -4.0]]))
        selected.bias.fill_(5.0)
    checkpoint = run_root / "selected_epoch-2.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    record = _linear_checkpoint(checkpoint, selected, epoch=2)

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        wrapper_path=tmp_path / "must-not-exist",
    )

    assert resolved.parent == cache
    restored = torch.load(resolved, map_location="cpu", weights_only=False)
    probe = torch.tensor([[0.25, -0.5]])
    assert torch.equal(restored(probe), selected(probe))
    # The stable training model is an immutable architecture template.
    unchanged = torch.load(template_path, map_location="cpu", weights_only=False)
    assert torch.equal(unchanged(probe), template(probe))
    sidecar = resolved.with_suffix(".json")
    payload = __import__("json").loads(sidecar.read_text(encoding="utf-8"))
    assert payload["reconstruction_method"] == "direct_state_restore"


def test_latest_checkpoint_reuses_completed_training_model_without_reserialization(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    cache = run_root / "checkpoint-model-cache"
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump({"name": "qualified-model", "seed": 17}), encoding="utf-8"
    )

    final_model = torch.nn.Linear(2, 1)
    with torch.no_grad():
        final_model.weight.copy_(torch.tensor([[1.5, -2.5]]))
        final_model.bias.fill_(0.75)
    template_path = models / "qualified-model.model"
    torch.save(final_model, template_path)
    checkpoint = run_root / "qualified-model_epoch-29.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    record = _linear_checkpoint(checkpoint, final_model, epoch=29)

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        wrapper_path=tmp_path / "must-not-exist",
    )

    assert resolved == template_path.resolve()
    assert not cache.exists() or not tuple(cache.glob("checkpoint-*.model"))


def test_direct_restore_matches_real_mace_energy_force_and_stress(tmp_path: Path, monkeypatch) -> None:
    """OPT-EVAL1 correctness gate for an actual MACE 0.3.16 e3nn model."""

    monkeypatch.setenv("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    pytest = __import__("pytest")
    pytest.importorskip("mace")
    e3nn = pytest.importorskip("e3nn")
    import numpy as np
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
    selected = deepcopy(template)
    with torch.no_grad():
        first_parameter = next(selected.parameters())
        first_parameter.add_(0.03125)

    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    template_path = models / "tiny-mace.model"
    torch.save(template, template_path)
    checkpoint = run_root / "tiny-mace_epoch-7.pt"
    record = _linear_checkpoint(checkpoint, selected, epoch=7)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config_path = job_root / "config.yaml"
    config_path.write_text(
        yaml.safe_dump({"name": "tiny-mace", "seed": 11, "enable_cueq": False}),
        encoding="utf-8",
    )

    restored_path = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config_path,
        job_working_directory=job_root,
        cache_directory=run_root / "checkpoint-model-cache",
        wrapper_path=tmp_path / "must-not-exist",
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

    expected = selected(batch, training=False, compute_force=True, compute_stress=True)
    actual = restored(batch, training=False, compute_force=True, compute_stress=True)
    for key in ("energy", "forces", "stress"):
        assert torch.allclose(actual[key], expected[key], rtol=0.0, atol=0.0), key
    assert _sha(checkpoint) == record.sha256


def test_direct_restore_refuses_silent_dtype_cast_and_falls_back(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    cache = run_root / "checkpoint-model-cache"
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(yaml.safe_dump({"name": "qualified-model", "seed": 3}), encoding="utf-8")

    template = torch.nn.Linear(1, 1).float()
    torch.save(template, models / "qualified-model.model")
    selected = torch.nn.Linear(1, 1).double()
    checkpoint = run_root / "qualified-model_epoch-4.pt"
    record = _linear_checkpoint(checkpoint, selected, epoch=4)

    marker = tmp_path / "fallback-called"
    wrapper = tmp_path / "fake-mace-train"
    wrapper.write_text(
        "#!/usr/bin/env python\n"
        "import pathlib, sys, torch, yaml\n"
        f"pathlib.Path({str(marker)!r}).write_text('yes')\n"
        "args=sys.argv[1:]\n"
        "cfg=pathlib.Path(args[args.index('--config')+1])\n"
        "p=yaml.safe_load(cfg.read_text())\n"
        "out=pathlib.Path(p['model_dir'])/(p['name']+'.model')\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "torch.save(torch.nn.Linear(1,1).double(), out)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        wrapper_path=wrapper,
    )
    assert marker.read_text() == "yes"
    payload = __import__("json").loads(resolved.with_suffix(".json").read_text())
    assert payload["reconstruction_method"] == "legacy_restart_export"


def test_direct_restore_uses_guarded_cueq_roundtrip_when_configured(tmp_path: Path, monkeypatch) -> None:
    import sys
    import types

    calls: list[str] = []
    to_cueq = types.ModuleType("mace.cli.convert_e3nn_cueq")
    to_e3nn = types.ModuleType("mace.cli.convert_cueq_e3nn")

    def forward(model, device="cpu"):
        calls.append(f"to_cueq:{device}")
        return model

    def backward(model, device="cpu"):
        calls.append(f"to_e3nn:{device}")
        return model

    to_cueq.run = forward
    to_e3nn.run = backward
    monkeypatch.setitem(sys.modules, "mace.cli.convert_e3nn_cueq", to_cueq)
    monkeypatch.setitem(sys.modules, "mace.cli.convert_cueq_e3nn", to_e3nn)

    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {"name": "qualified-model", "seed": 5, "enable_cueq": True, "only_cueq": False}
        ),
        encoding="utf-8",
    )
    template = torch.nn.Linear(2, 1)
    torch.save(template, models / "qualified-model.model")
    selected = torch.nn.Linear(2, 1)
    with torch.no_grad():
        selected.weight.fill_(7.0)
        selected.bias.fill_(-2.0)
    checkpoint = run_root / "qualified-model_epoch-8.pt"
    record = _linear_checkpoint(checkpoint, selected, epoch=8)

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=run_root / "checkpoint-model-cache",
        wrapper_path=tmp_path / "must-not-exist",
    )
    restored = torch.load(resolved, map_location="cpu", weights_only=False)
    probe = torch.tensor([[1.0, 2.0]])
    assert torch.equal(restored(probe), selected(probe))
    assert calls == ["to_cueq:cpu", "to_e3nn:cpu"]


def test_multihead_target_export_runs_in_process_without_wrapper(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    pytest = __import__("pytest")
    pytest.importorskip("mace")
    e3nn = pytest.importorskip("e3nn")
    import numpy as np
    from mace import modules

    model = modules.ScaleShiftMACE(
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
        atomic_energies=np.array([[0.1, 0.2], [0.3, 0.4]]),
        avg_num_neighbors=3.0,
        atomic_numbers=[1, 8],
        correlation=2,
        radial_type="bessel",
        heads=["pt_head", "target_head"],
        atomic_inter_scale=[1.0, 1.0],
        atomic_inter_shift=[0.0, 0.0],
    )
    source_model = tmp_path / "multi.model"
    torch.save(model, source_model)

    checkpoint = tmp_path / "selected_epoch-0.pt"
    checkpoint.write_bytes(b"checkpoint-identity")
    sha = _sha(checkpoint)
    run = mdstats.TrainingCampaignRunPlan(
        run_id="mh-fold-00",
        data8_bundle_digest="1" * 64,
        mace_job_artifact_digest="2" * 64,
        job_id="mh-fold-00",
        kind=mdstats.MaceJobKind.CROSS_VALIDATION_FOLD,
        fold_index=0,
        training_mode=mdstats.TrainingMode.MULTIHEAD_REPLAY,
        selection_size=1,
        seed=1,
        protocol_family_digest="3" * 64,
        protocol_variant_digest="4" * 64,
        protocol_digest="5" * 64,
        checkpoint_metric_policy_digest="6" * 64,
        target_monitor_artifact_digest="7" * 64,
        replay_monitor_artifact_digest="8" * 64,
        relative_output_directory="mh-fold-00",
    )
    decision = mdstats.CheckpointAdmissibilityDecision(
        run_plan_digest=run.content_digest,
        checkpoint_sha256=sha,
        checkpoint_metric_record_digest="9" * 64,
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        outcome=mdstats.CheckpointAdmissibilityOutcome.ADMISSIBLE,
        primary_metric_name="force",
        primary_metric_value=0.1,
    )
    selection = mdstats.CheckpointSelectionRecord(
        run_plan_digest=run.content_digest,
        checkpoint_catalog_digest="a" * 64,
        checkpoint_metric_policy_digest=run.checkpoint_metric_policy_digest,
        decisions=(decision,),
        selected_checkpoint_sha256=sha,
        selected_checkpoint_epoch=0,
        selected_primary_metric_value=0.1,
    )
    output = tmp_path / "target.model"
    member = mdstats.export_target_head_verification_model(
        run,
        selection,
        checkpoint,
        output,
        source_model_path=source_model,
        policy=mdstats.CommitteeExportPolicy(
            target_head_name="target_head", target_device="cpu", minimum_members=1
        ),
        wrapper_path=tmp_path / "must-not-exist",
    )
    restored = torch.load(output, map_location="cpu", weights_only=False)
    assert restored.heads == ["target_head"]
    assert member.exported_model_sha256 == _sha(output)


class _MixedBufferModel(torch.nn.Module):
    """Tiny model with FP32 learned parameters and an intentional FP64 buffer."""

    def __init__(self) -> None:
        super().__init__()
        self.linear = torch.nn.Linear(1, 1).float()
        self.register_buffer("reference_accumulator", torch.tensor([1.0], dtype=torch.float64))

    def forward(self, value):
        return self.linear(value)


def test_direct_restore_accepts_fp32_parameters_with_fp64_buffer(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    models = run_root / "models"
    models.mkdir(parents=True)
    cache = run_root / "checkpoint-model-cache"
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "name": "qualified-model",
                "seed": 17,
                "default_dtype": "float32",
                "enable_cueq": False,
            }
        ),
        encoding="utf-8",
    )

    template = _MixedBufferModel()
    torch.save(template, models / "qualified-model.model")
    selected = _MixedBufferModel()
    with torch.no_grad():
        selected.linear.weight.fill_(3.0)
        selected.linear.bias.fill_(-2.0)
        selected.reference_accumulator.fill_(7.25)
    checkpoint = run_root / "selected_epoch-2.pt"
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    record = _linear_checkpoint(checkpoint, selected, epoch=2)

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=cache,
        wrapper_path=tmp_path / "must-not-exist",
    )

    restored = torch.load(resolved, map_location="cpu", weights_only=False)
    assert next(restored.parameters()).dtype == torch.float32
    assert restored.reference_accumulator.dtype == torch.float64
    assert torch.equal(restored.linear.weight, selected.linear.weight)
    assert torch.equal(restored.linear.bias, selected.linear.bias)
    assert torch.equal(restored.reference_accumulator, selected.reference_accumulator)
    payload = __import__("json").loads(resolved.with_suffix(".json").read_text())
    assert payload["reconstruction_method"] == "direct_state_restore"


def test_legacy_restart_export_uses_data8_dtype_for_mixed_buffer_checkpoint(tmp_path: Path) -> None:
    checkpoint = tmp_path / "mixed_epoch-3.pt"
    torch.save(
        {
            "model": {
                "learned_weight": torch.tensor([1.0], dtype=torch.float32),
                "reference_buffer": torch.tensor([2.0], dtype=torch.float64),
            },
            "optimizer": {},
            "lr_scheduler": {},
        },
        checkpoint,
    )
    record = _record(checkpoint, epoch=3)
    job_root = tmp_path / "job"
    job_root.mkdir()
    config = job_root / "config.yaml"
    config.write_text(
        yaml.safe_dump(
            {
                "name": "qualified-model",
                "seed": 19,
                "default_dtype": "float32",
            }
        ),
        encoding="utf-8",
    )
    marker = tmp_path / "derived-default-dtype.txt"
    wrapper = tmp_path / "fake-mace-train"
    wrapper.write_text(
        "#!/usr/bin/env python\n"
        "import pathlib, sys, torch, yaml\n"
        f"marker = pathlib.Path({str(marker)!r})\n"
        "args = sys.argv[1:]\n"
        "cfg = pathlib.Path(args[args.index('--config') + 1])\n"
        "payload = yaml.safe_load(cfg.read_text())\n"
        "marker.write_text(str(payload['default_dtype']))\n"
        "out = pathlib.Path(payload['model_dir']) / (payload['name'] + '.model')\n"
        "out.parent.mkdir(parents=True, exist_ok=True)\n"
        "torch.save(torch.nn.Linear(1, 1).float(), out)\n",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    resolved = mdstats.materialize_mace_checkpoint_model(
        record,
        checkpoint,
        mace_config_path=config,
        job_working_directory=job_root,
        cache_directory=tmp_path / "cache",
        wrapper_path=wrapper,
    )

    assert resolved.is_file()
    assert marker.read_text() == "float32"
    payload = __import__("json").loads(resolved.with_suffix(".json").read_text())
    assert payload["reconstruction_method"] == "legacy_restart_export"
