from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import ast
import json
import shutil

import numpy as np
import pytest
import yaml
from ase import Atoms
from ase.io import read, write

import mdstats
from tests.test_mlff_data7_fitted_metrics_selection import _inputs


RUN_TRAIN_TEXT = '''
heads = sorted(heads, key=lambda x: -1000 if x == "pt_head" else 0)
if ratio_pt_ft < args.real_pt_data_ratio_threshold:
    head_config.collections.train += head_config.collections.train * 2
if args.dry_run:
    return
tools.train(save_all_checkpoints=args.save_all_checkpoints)
'''
TRAIN_TEXT = '''
valid_loss = valid_loss_head  # consider only the last head for the checkpoint
if save_all_checkpoints:
    checkpoint_handler.save()
'''
MULTIHEAD_TEXT = '''
def prepare_pt_head(args, pt_keyspec, foundation_model_num_neighbours):
    return {"valid_file": args.pt_valid_file}
'''


def _probe() -> mdstats.MaceSourceProbe:
    return mdstats.probe_mace_source_texts(
        RUN_TRAIN_TEXT, TRAIN_TEXT, MULTIHEAD_TEXT
    )


def _write_replay(
    path: Path, *, offset: float, count: int, symbols: str = "LiO"
) -> None:
    atoms_list = []
    atom_count = len(Atoms(symbols))
    base_positions = [
        (0.1 + offset, 0.1, 0.1),
        (0.5, 0.5, 0.5),
        (0.75, 0.25, 0.25),
    ]
    if atom_count > len(base_positions):
        raise ValueError("Replay test helper supports at most three atoms.")
    for index in range(count):
        positions = list(base_positions[:atom_count])
        positions[0] = (positions[0][0] + 0.01 * index, positions[0][1], positions[0][2])
        atoms = Atoms(
            symbols,
            scaled_positions=positions,
            cell=np.eye(3) * 10.0,
            pbc=True,
        )
        atoms.info["REF_energy"] = -3.0 + 0.1 * index
        forces = np.zeros((atom_count, 3), dtype=float)
        forces[0, 0] = 0.1
        if atom_count > 1:
            forces[1, 0] = -0.1
        atoms.arrays["REF_forces"] = forces
        atoms.info["REF_stress"] = np.zeros(6)
        atoms_list.append(atoms)
    write(path, atoms_list, format="extxyz")


def _data7_bundles(tmp_path: Path):
    sources, frames, frame_data, data4, data5, data6, domains, _ = _inputs(tmp_path)
    bundles = []
    for domain in domains:
        bundles.append(
            mdstats.build_data7_preparation_bundle(
                sources,
                frames,
                frame_data,
                data4,
                data5,
                data6,
                domain,
                feature_metric_policy=mdstats.FeatureMetricPolicyTemplate(
                    blocks=(mdstats.FeatureBlockPolicy("raw_physical", required=True),)
                ),
                selection_budget_policy=mdstats.SelectionBudgetPolicy(
                    target_sizes=(4, 8)
                ),
            )
        )
    return sources, frames, frame_data, data4, data5, data6, tuple(bundles)


def _foundation(tmp_path: Path) -> mdstats.FoundationCheckpointIdentity:
    path = tmp_path / "mace-mpa-0-medium.model"
    path.write_bytes(b"deterministic-foundation-checkpoint-fixture")
    return mdstats.FoundationCheckpointIdentity.from_file(path)


def test_supplied_ase_version() -> None:
    import ase

    assert ase.__version__ == "3.29.0"


def test_mace_source_probe_locks_v0316_behaviors() -> None:
    probe = _probe()
    assert probe.fixed_file_adapter_supported
    assert probe.pt_head_sorted_first
    assert probe.target_validation_head_is_last
    assert probe.native_checkpoint_uses_last_validation_head
    assert probe.implicit_target_duplication_present
    assert mdstats.MaceSourceProbe.from_dict(probe.to_dict()) == probe
    broken = mdstats.probe_mace_source_texts(
        RUN_TRAIN_TEXT.replace("heads = sorted", "heads = list"),
        TRAIN_TEXT,
        MULTIHEAD_TEXT,
    )
    assert not broken.fixed_file_adapter_supported


def test_mace_extxyz_round_trip_weights_and_stress(tmp_path: Path) -> None:
    sources, frames, frame_data, _, _, _, bundles = _data7_bundles(tmp_path)
    final = next(
        item for item in bundles if item.domain.kind is mdstats.FeatureFitDomainKind.FINAL_DEVELOPMENT
    )
    selected = final.selection_plan.ladder_levels[-1].frame_uids
    artifact = mdstats.write_mace_extxyz_artifact(
        tmp_path / "export",
        dataset_id=frames.dataset_id,
        role="target_train",
        filename="train.xyz",
        frame_uids=selected,
        frame_catalog=frames,
        frame_data_by_run=frame_data,
        data7_bundle=final,
        training_weights=final.training_weights,
    )
    observed = read(tmp_path / "export" / artifact.relative_path, index=":", format="extxyz")
    assert len(observed) == len(selected)
    assert all("REF_energy" in atoms.info for atoms in observed)
    assert all("REF_forces" in atoms.arrays for atoms in observed)
    assert all(np.asarray(atoms.info["REF_stress"]).shape == (6,) for atoms in observed)
    assert all("config_weight" in atoms.info for atoms in observed)
    assert all("config_forces_weight" in atoms.info for atoms in observed)
    assert all("frame_uid" in atoms.info for atoms in observed)
    assert mdstats.MaceExtxyzArtifact.from_dict(artifact.to_dict()) == artifact


def test_mace_extxyz_preserves_full_precision_positions_and_forces(
    tmp_path: Path,
) -> None:
    _, frames, frame_data, _, _, _, _ = _data7_bundles(tmp_path)
    record = frames.frames[0]
    original = frame_data[record.run_id]
    local_index = int(
        np.flatnonzero(
            np.asarray(original.source_frame_indices) == record.source_frame_index
        )[0]
    )
    fractional = np.array(original.fractional_positions, copy=True)
    fractional[local_index, 0] = np.asarray(
        [0.11234567891234567, 0.22345678912345678, 0.33456789123456789]
    )
    forces = np.array(original.forces_ev_per_angstrom, copy=True)
    forces[local_index, 0] = np.asarray(
        [0.12345678912345678, -0.23456789123456789, 0.34567891234567891]
    )
    modified = replace(
        original,
        fractional_positions=fractional,
        forces_ev_per_angstrom=forces,
    )
    artifact = mdstats.write_mace_extxyz_artifact(
        tmp_path / "precise-export",
        dataset_id=frames.dataset_id,
        role="target_train",
        filename="train.xyz",
        frame_uids=(record.frame_uid,),
        frame_catalog=frames,
        frame_data_by_run={record.run_id: modified},
    )
    observed = read(
        tmp_path / "precise-export" / artifact.relative_path,
        index=0,
        format="extxyz",
    )
    expected_positions = fractional[local_index] @ np.asarray(
        modified.cells_angstrom[local_index]
    )
    np.testing.assert_allclose(observed.positions, expected_positions, rtol=0.0, atol=1e-14)
    np.testing.assert_allclose(
        observed.arrays["REF_forces"],
        forces[local_index],
        rtol=0.0,
        atol=1e-14,
    )


def test_replay_train_monitor_must_be_disjoint(tmp_path: Path) -> None:
    train = tmp_path / "replay_train.xyz"
    monitor = tmp_path / "replay_monitor.xyz"
    _write_replay(train, offset=0.0, count=3)
    _write_replay(monitor, offset=0.2, count=2)
    plan = mdstats.build_local_replay_plan(train, monitor)
    assert plan.ready_for_fixed_file_training
    assert plan.train_count == 3 and plan.monitor_count == 2
    assert mdstats.ReplayPreparationPlan.from_dict(plan.to_dict()) == plan
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.build_local_replay_plan(train, train)


def test_loader_dry_run_declares_implicit_duplication() -> None:
    probe = _probe()
    realization = mdstats.emulate_mace_v0316_loader_dry_run(
        compatibility_probe=probe,
        target_train_count=10,
        target_validation_count=2,
        replay_train_count=1000,
        replay_validation_count=10,
        real_pt_data_ratio_threshold=0.1,
    )
    assert realization.head_order == ("pt_head", "target_head")
    assert realization.validation_head_order[-1] == "target_head"
    assert realization.native_checkpoint_head == "target_head"
    assert realization.implicit_target_duplication_factor == 11
    assert realization.target_train_count_effective == 110
    assert mdstats.MaceLoaderDryRun.from_dict(realization.to_dict()) == realization


def test_data8_naive_jobs_exclude_all_evaluation_from_configs(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    output = tmp_path / "data8_naive"
    result = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=output,
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
    )
    assert len(result.jobs) == 4
    assert sum(job.kind is mdstats.MaceJobKind.CROSS_VALIDATION_FOLD for job in result.jobs) == 3
    assert result.replay_plan.mode is mdstats.ReplayMode.NONE
    assert all(job.loader_dry_run.native_checkpoint_head == "target_head" for job in result.jobs)
    for job in result.jobs:
        command = (output / job.relative_directory / "run_mace.sh").read_text()
        assert "mdstats-mace-train --config mace_config.yaml" in command
        assert "\nmace_run_train " not in command
        config = yaml.safe_load((output / job.config_relative_path).read_text())
        assert "test_file" not in config
        assert "test_dir" not in config
        assert config["multiheads_finetuning"] is False
        heads = ast.literal_eval(config["heads"])
        assert list(heads) == ["target_head"]
        e0s = ast.literal_eval(heads["target_head"]["E0s"])
        assert all(isinstance(key, int) for key in e0s)
        assert ast.literal_eval(config["atomic_numbers"]) == sorted(e0s)
        assert config["loss"] == "universal"
        if job.kind is mdstats.MaceJobKind.CROSS_VALIDATION_FOLD:
            evaluation = next(
                item
                for item in result.fold_evaluation_artifacts
                if item.content_digest == job.fold_evaluation_artifact_digest
            )
            assert evaluation.relative_path not in str(config)
    assert result.sealed_outer_evaluations[0].materialized is False
    assert not (output / "locked_test.xyz").exists()
    assert result.mlcv_role_catalog is not None
    assert result.mlcv_role_catalog.data5_bundle_digest == data5.content_digest
    assert result.mlcv_role_catalog.split_authority == "data5_correlation_aware_partition_units"
    assert (output / "mlcv_role_catalog.json").is_file()
    assert mdstats.Data8PreparationBundle.from_dict(result.to_dict()) == result
    tampered = deepcopy(result.to_dict())
    tampered["notes"] = ["modified"]
    with pytest.raises(mdstats.TrainingDataSerializationError):
        mdstats.Data8PreparationBundle.from_dict(tampered)


def test_data8_multihead_config_and_protocol_identity(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    replay_train = tmp_path / "replay_train.xyz"
    replay_monitor = tmp_path / "replay_monitor.xyz"
    _write_replay(replay_train, offset=0.0, count=5)
    _write_replay(replay_monitor, offset=0.3, count=2)
    replay = mdstats.build_local_replay_plan(
        replay_train,
        replay_monitor,
        head_weight=2.5,
        target_weight=7.0,
    )
    output = tmp_path / "data8_replay"
    result = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=output,
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        replay_plan=replay,
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        real_pt_data_ratio_threshold=0.0,
        require_foundation_residual_e0=False,
    )
    assert result.replay_plan.mode is mdstats.ReplayMode.PRESELECTED
    assert Path(result.replay_plan.train_artifact.path).is_absolute()
    replay_frames = read(result.replay_plan.train_artifact.path, index=":", format="extxyz")
    assert all(float(atoms.info["config_weight"]) == pytest.approx(2.5) for atoms in replay_frames)
    for job in result.jobs:
        command = (output / job.relative_directory / "run_mace.sh").read_text()
        assert "mdstats-mace-train --config mace_config.yaml" in command
        assert "\nmace_run_train " not in command
        config = yaml.safe_load((output / job.config_relative_path).read_text())
        assert config["multiheads_finetuning"] is True
        assert list(ast.literal_eval(config["heads"])) == ["target_head", "pt_head"]
        assert config["pt_train_file"].endswith("replay_train.xyz")
        assert config["pt_valid_file"].endswith("replay_monitor.xyz")
        assert "weight_pt" not in config
        assert "weight_ft" not in config
        assert config["save_all_checkpoints"] is True
        assert config["real_pt_data_ratio_threshold"] == 0.0
        target_train = read(output / job.relative_directory / "target_train.xyz", index=":", format="extxyz")
        sidecar = json.loads(
            (output / job.relative_directory / "target_train.xyz.manifest.json").read_text()
        )
        for atoms in target_train:
            values = sidecar["records"][atoms.info["frame_uid"]]
            assert values["configuration_weight_scale"] == pytest.approx(7.0)
            assert float(atoms.info["config_weight"]) == pytest.approx(
                values["base_configuration_weight"] * 7.0
            )
        assert job.protocol.training_mode is mdstats.TrainingMode.MULTIHEAD_REPLAY
        assert job.protocol.replay_plan_digest == result.replay_plan.content_digest
        assert job.loader_dry_run.head_order == ("pt_head", "target_head")
        assert job.loader_dry_run.implicit_target_duplication_factor == 1


def test_data8_multihead_uses_head_specific_target_elements(
    tmp_path: Path,
) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    replay_train = tmp_path / "replay_train_h.xyz"
    replay_monitor = tmp_path / "replay_monitor_h.xyz"
    _write_replay(replay_train, offset=0.0, count=3, symbols="H")
    _write_replay(replay_monitor, offset=0.3, count=2, symbols="H")
    replay = mdstats.build_local_replay_plan(replay_train, replay_monitor)
    output = tmp_path / "data8_replay_h"
    result = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=output,
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        replay_plan=replay,
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        real_pt_data_ratio_threshold=0.0,
        require_foundation_residual_e0=False,
    )
    for job in result.jobs:
        config = yaml.safe_load((output / job.config_relative_path).read_text())
        atomic_numbers = set(ast.literal_eval(config["atomic_numbers"]))
        heads = ast.literal_eval(config["heads"])
        target_head = heads["target_head"]
        target_numbers = set(ast.literal_eval(target_head["atomic_numbers"]))
        target_e0s = ast.literal_eval(target_head["E0s"])
        assert 1 in atomic_numbers
        assert 1 not in target_numbers
        assert set(target_e0s) == target_numbers
        assert target_numbers < atomic_numbers
        for target_number in target_numbers:
            assert np.isfinite(target_e0s[target_number])


def test_mp_shortcut_is_preparation_only_for_fixed_file_adapter(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    monitor = tmp_path / "monitor.xyz"
    _write_replay(monitor, offset=0.4, count=2)
    plan = mdstats.ReplayPreparationPlan(
        mode=mdstats.ReplayMode.MP_SHORTCUT,
        requested_train_count=100,
        monitor_artifact=mdstats.inspect_replay_extxyz(monitor),
    )
    assert not plan.ready_for_fixed_file_training
    with pytest.raises(mdstats.TrainingDataInputError):
        mdstats.build_data8_preparation_bundle(
            sources,
            frames,
            frame_data,
            data5,
            bundles,
            output_directory=tmp_path / "bad",
            foundation_checkpoint=_foundation(tmp_path),
            compatibility_probe=_probe(),
            replay_plan=plan,
        )


def test_data8_parser_version_invalidates_pre_02066_bundle(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    result = mdstats.build_data8_preparation_bundle(
        sources,
        frames,
        frame_data,
        data5,
        bundles,
        output_directory=tmp_path / "data8-version",
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
    )
    payload = result.to_dict()
    payload["parser_version"] = "0.20.65a0"
    with pytest.raises(mdstats.TrainingDataSerializationError, match="parser version"):
        mdstats.Data8PreparationBundle.from_dict(payload)


def test_data8_perf_p2r_fixed_file_cache_is_scientifically_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Cache hits must reproduce the exact fresh DATA8 authority."""

    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    foundation = _foundation(tmp_path)
    output = tmp_path / "data8-cache-target"
    cache = tmp_path / "data8-fixed-cache"
    kwargs = dict(
        source_catalog=sources,
        frame_catalog=frames,
        frame_data_by_run=frame_data,
        data5_bundle=data5,
        data7_bundles=bundles,
        output_directory=output,
        foundation_checkpoint=foundation,
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
    )
    reference = mdstats.build_data8_preparation_bundle(**kwargs)
    reference_payload = reference.to_dict()
    shutil.rmtree(output)

    first_cached = mdstats.build_data8_preparation_bundle(
        **kwargs, shared_fixed_file_cache_directory=cache
    )
    assert first_cached.to_dict() == reference_payload
    generations = tuple(cache.rglob("cache.json"))
    assert generations
    shutil.rmtree(output)

    import mdstats.training_data.mace_export as mace_export

    def forbidden_write(*args, **kwargs):  # pragma: no cover - only called on regression
        raise AssertionError("PERF-P2R cache hit unexpectedly rebuilt ExtXYZ bytes")

    monkeypatch.setattr(mace_export, "_write_extxyz_high_precision", forbidden_write)
    second_cached = mdstats.build_data8_preparation_bundle(
        **kwargs, shared_fixed_file_cache_directory=cache
    )
    assert second_cached.to_dict() == reference_payload
    assert tuple(cache.rglob("cache.json")) == generations


def test_data8_perf_p2r_fixed_file_cache_rejects_corruption(tmp_path: Path) -> None:
    """A corrupted shared generation must never be trusted as a cache hit."""

    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    output = tmp_path / "data8-cache-corrupt-target"
    cache = tmp_path / "data8-fixed-cache-corrupt"
    kwargs = dict(
        source_catalog=sources,
        frame_catalog=frames,
        frame_data_by_run=frame_data,
        data5_bundle=data5,
        data7_bundles=bundles,
        output_directory=output,
        foundation_checkpoint=_foundation(tmp_path),
        compatibility_probe=_probe(),
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        require_foundation_residual_e0=False,
        shared_fixed_file_cache_directory=cache,
    )
    mdstats.build_data8_preparation_bundle(**kwargs)
    generation = next(
        metadata.parent
        for metadata in cache.rglob("cache.json")
        if json.loads(metadata.read_text(encoding="utf-8")).get("schema")
        == "mdstats.perf-p2r-data8-fixed-file-cache.v1"
    )
    artifact = generation / "artifact.xyz"
    artifact.write_bytes(artifact.read_bytes() + b"\n# corrupted\n")
    shutil.rmtree(output)
    with pytest.raises(mdstats.TrainingDataInputError, match="could not be validated"):
        mdstats.build_data8_preparation_bundle(**kwargs)
