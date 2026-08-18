from __future__ import annotations

from pathlib import Path

import numpy as np
import yaml
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_cli
from tests.test_mlff_data8_mace_artifacts import _data7_bundles, _foundation, _probe, _write_replay


def _true_replay(path: Path, count: int = 8) -> mdstats.ReplayFileArtifact:
    atoms_list = []
    symbols = ("LiO", "NaCl", "KCl", "AlO", "SiO")
    for index in range(count):
        formula = symbols[index % len(symbols)]
        atoms = Atoms(
            formula,
            scaled_positions=[(0.1 + 0.01 * index, 0.1, 0.1), (0.55, 0.55, 0.55)],
            cell=np.eye(3) * (9.0 + 0.1 * index),
            pbc=True,
        )
        atoms.info["REF_energy"] = -2.0 - 0.05 * index
        forces = np.zeros((len(atoms), 3), dtype=float)
        forces[0, 0] = 0.02 * (index + 1)
        forces[-1, 0] = -forces[0, 0]
        atoms.arrays["REF_forces"] = forces
        atoms.info["REF_stress"] = np.zeros(6)
        atoms_list.append(atoms)
    write(path, atoms_list, format="extxyz")
    return mdstats.inspect_replay_extxyz(path, label_mode=mdstats.ReplayLabelMode.TRUE_DFT)


def test_target_monitor_is_deterministic_common_and_time_spread(tmp_path: Path) -> None:
    _, frames, _, _, data5, _, _ = _data7_bundles(tmp_path)
    domain = data5.outer_partitions[0].label_domain_id
    policy = mdstats.OnlineMonitorPolicy(target_configurations=4, replay_configurations=3, seed=1234)
    first = mdstats.build_target_online_monitor(data5, frames, domain, policy)
    second = mdstats.build_target_online_monitor(data5, frames, domain, policy)
    assert first == second
    assert first.content_digest == second.content_digest
    assert first.realized_size == min(4, sum(v[1] for v in first.stratum_counts))
    assert first.parent_role == "data5_outer_monitor"
    assert all(frames.frame(uid).frame_uid == uid for uid in first.selected_identities)


def test_replay_monitor_is_true_label_deterministic_and_materialized(tmp_path: Path) -> None:
    source = _true_replay(tmp_path / "true_replay.xyz", count=8)
    policy = mdstats.OnlineMonitorPolicy(target_configurations=4, replay_configurations=5, seed=99)
    first = mdstats.build_replay_online_monitor(source, policy)
    second = mdstats.build_replay_online_monitor(source, policy)
    assert first == second
    assert first.realized_size == 5
    artifact = mdstats.materialize_replay_online_monitor(
        source, first, tmp_path / "online_true_replay_monitor.xyz"
    )
    assert artifact.label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    assert artifact.configuration_count == 5
    assert artifact.geometry_identities == first.selected_identities
    assert artifact.label_identities == tuple(source.label_identities[i] for i in first.source_indices)


def test_data8_mlcv_mon1_uses_run_local_target_and_true_replay_monitors(tmp_path: Path) -> None:
    sources, frames, frame_data, _, data5, _, bundles = _data7_bundles(tmp_path)
    replay_train = tmp_path / "replay_train.xyz"
    replay_monitor = tmp_path / "replay_monitor.xyz"
    _write_replay(replay_train, offset=0.0, count=5)
    _write_replay(replay_monitor, offset=0.3, count=2)
    replay = mdstats.build_local_replay_plan(replay_train, replay_monitor)
    true_replay = _true_replay(tmp_path / "replay_true.xyz", count=8)
    policy = mdstats.OnlineMonitorPolicy(
        target_configurations=4,
        replay_configurations=5,
        training_diagnostic_configurations=3,
        seed=2026,
    )

    output = tmp_path / "data8_mon1"
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
        online_monitor_policy=policy,
        true_replay_monitor_artifact=true_replay,
        optimizer_policy=mdstats.MaceOptimizerPolicy(device="cpu", max_num_epochs=2),
        real_pt_data_ratio_threshold=0.0,
        require_foundation_residual_e0=False,
    )

    assert result.online_monitor_policy == policy  # retained compatibility input
    assert result.target_online_monitor is None  # common ADAPT-MON1 target membership is retired
    assert result.replay_online_monitor is None
    assert result.mlcv_role_catalog is not None
    assert result.mlcv_monitor_catalog is not None
    assert result.replay_full_validation_artifact is not None
    assert result.online_replay_monitor_artifact is not None
    assert result.replay_full_validation_artifact.label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    assert result.online_replay_monitor_artifact.label_mode is mdstats.ReplayLabelMode.TRUE_DFT
    assert set(result.online_replay_monitor_artifact.geometry_identities).issubset(
        set(result.replay_full_validation_artifact.geometry_identities)
    )
    assert result.online_replay_monitor_artifact.configuration_count == 5
    assert result.replay_full_validation_artifact.configuration_count == 8
    assert (output / "mlcv_monitor_catalog.json").is_file()

    catalog = result.mlcv_monitor_catalog
    assert catalog.policy.target_light_configurations == 4
    assert catalog.policy.replay_light_configurations == 5
    assert catalog.policy.training_diagnostic_configurations == 3
    assert len(catalog.runs) == len(result.jobs)

    for job in result.jobs:
        record = catalog.run(job.job_id)
        assert set(record.target_light_frame_uids).issubset(record.target_full_frame_uids)
        assert set(record.training_diagnostic_frame_uids).issubset(record.training_frame_uids)
        assert not set(record.target_full_frame_uids) & set(record.training_frame_uids)
        assert len(record.target_light_frame_uids) <= 4
        assert len(record.training_diagnostic_frame_uids) <= 3
        assert job.protocol.online_monitor_policy_digest == catalog.policy.policy_digest
        assert job.protocol.target_online_monitor_record_digest == record.content_digest
        assert job.protocol.replay_online_monitor_record_digest == catalog.replay.content_digest
        assert job.protocol.replay_valid_artifact_digest == result.online_replay_monitor_artifact.content_digest
        config = yaml.safe_load((output / job.config_relative_path).read_text())
        assert config["pt_valid_file"].endswith("light_true_replay_validation.xyz")
        assert config["pt_train_file"].endswith("replay_train.xyz")
        assert job.loader_dry_run.target_validation_count == len(record.target_light_frame_uids)
        assert job.loader_dry_run.replay_validation_count == len(catalog.replay.light_geometry_identities)

        job_dir = output / job.relative_directory
        assert (job_dir / "target_valid.xyz").is_file()
        assert (job_dir / "target_checkpoint_full.xyz").is_file()
        assert (job_dir / "target_training_diagnostic.xyz").is_file()
        full = next(
            artifact for artifact in result.target_artifacts
            if artifact.role == "target_checkpoint_full"
            and artifact.frame_uids == record.target_full_frame_uids
        )
        assert campaign_cli._resolve_data8_job_member(
            result, output, job, full.relative_path
        ) == (job_dir / "target_checkpoint_full.xyz").resolve()
        if job.kind is mdstats.MaceJobKind.CROSS_VALIDATION_FOLD:
            assert record.target_statistical_role == "target_checkpoint_selection"
            assert (job_dir / "fold_evaluation.xyz").is_file()
            outer = next(a for a in result.fold_evaluation_artifacts if a.content_digest == job.fold_evaluation_artifact_digest)
            assert not set(record.target_full_frame_uids) & set(outer.frame_uids)
            assert campaign_cli._resolve_data8_job_member(
                result, output, job, outer.relative_path
            ) == (job_dir / "fold_evaluation.xyz").resolve()
        else:
            assert record.target_statistical_role == "target_final_validation"
            assert result.full_target_evaluation_artifact is not None
            assert tuple(result.full_target_evaluation_artifact.frame_uids) == record.target_full_frame_uids

    assert mdstats.Data8PreparationBundle.from_dict(result.to_dict()) == result

