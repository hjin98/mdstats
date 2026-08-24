from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

import numpy as np
from ase import Atoms
from ase.io import write

import mdstats
from mdstats.training_data import campaign_execution
from mdstats.training_data.data7_archive import read_data7_archive, write_data7_archive
from mdstats.training_data.model_features import (
    read_mace_descriptor_record_array,
    read_mace_descriptor_summary,
)
from tests.test_mlff_campaign_performance import _catalog, _frame_data
from tests.test_mlff_data7_fitted_metrics_selection import _inputs as _data7_inputs
from tests.test_mlff_data9a9a_production_model_sweep import (
    _CountingCalculator,
    _inputs as _sweep_inputs,
    _provider,
)


def _memmap_base(value: np.ndarray) -> np.memmap | None:
    current = value
    while current is not None:
        if isinstance(current, np.memmap):
            return current
        current = getattr(current, "base", None)
    return None


def test_frame_cache_v2_restores_shared_read_only_memmaps(tmp_path: Path) -> None:
    catalog = _catalog()
    manifest = mdstats.write_frame_data_cache(
        catalog, {"run-a": _frame_data()}, tmp_path / "cache"
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    record = payload["records"][0]
    assert record["storage_kind"] == "npy_directory"
    restored = mdstats.load_frame_data_cache(catalog, tmp_path / "cache")["run-a"]
    assert _memmap_base(restored.cells_angstrom) is not None
    assert _memmap_base(restored.fractional_positions) is not None
    assert not restored.cells_angstrom.flags.writeable


def test_data6_multiframe_shards_persist_exact_descriptors_and_summaries(
    tmp_path: Path,
) -> None:
    _, frames, frame_data, _, data5, policy = _sweep_inputs(tmp_path)
    root = tmp_path / "sweep"
    result = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        _provider(_CountingCalculator()),
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            artifact_shard_size=3
        ),
    )
    descriptor_records = result.descriptor_manifest.records
    prediction_records = result.prediction_manifest.records
    assert descriptor_records and prediction_records
    assert all(record.storage_kind == "npz_shard" for record in descriptor_records)
    assert all(record.storage_kind == "npz_shard" for record in prediction_records)
    assert len({record.relative_path for record in descriptor_records}) < len(
        descriptor_records
    )
    assert len({record.relative_path for record in prediction_records}) < len(
        prediction_records
    )

    record = descriptor_records[0]
    descriptor = read_mace_descriptor_record_array(record, root)
    frame_uid = record.frame_uid
    frame_record = frames.frame(frame_uid)
    species = tuple(
        sorted(int(value) for value in set(frame_data[frame_record.run_id].atomic_numbers))
    )
    persisted = read_mace_descriptor_summary(
        result.descriptor_manifest, root, frame_uid, species
    )
    assert persisted is not None
    values, missing = persisted
    dimension = descriptor.shape[1]
    np.testing.assert_allclose(values[:dimension], np.mean(descriptor, axis=0))
    np.testing.assert_allclose(
        values[dimension : 2 * dimension], np.std(descriptor, axis=0)
    )
    assert not np.any(missing[: 2 * dimension])
    prediction = mdstats.read_atomic_model_prediction(
        result.prediction_manifest, root, prediction_records[0].frame_uid
    )
    assert prediction.forces_ev_per_angstrom.shape[1] == 3


def test_data7_archive_memmaps_matrix_and_keeps_metric_arrays_native(
    tmp_path: Path,
) -> None:
    sources, frames, frame_data, data4, data5, data6, _, final = _data7_inputs(
        tmp_path, model=True
    )
    policy = mdstats.FeatureMetricPolicyTemplate(
        blocks=(
            mdstats.FeatureBlockPolicy("raw_physical", required=True),
            mdstats.FeatureBlockPolicy(
                "mace_summary", required=True, pca_components=3
            ),
        )
    )
    bundle = mdstats.build_data7_preparation_bundle(
        sources,
        frames,
        frame_data,
        data4,
        data5,
        data6,
        final,
        feature_metric_policy=policy,
        selection_budget_policy=mdstats.SelectionBudgetPolicy(
            target_sizes=(8,)
        ),
        mace_descriptor_root=tmp_path / "descriptors",
    )
    archive_path = tmp_path / "domain.data7.zip"
    sha256 = write_data7_archive(bundle, archive_path)
    restored = read_data7_archive(archive_path, expected_sha256=sha256)
    assert _memmap_base(restored.fitted_metric.frame_feature_table.values) is not None
    assert all(
        isinstance(metric.center, np.ndarray)
        and isinstance(metric.scale, np.ndarray)
        and isinstance(metric.projection, np.ndarray)
        for metric in restored.fitted_metric.block_metrics
    )
    with zipfile.ZipFile(archive_path, "r") as archive:
        manifest = json.loads(archive.read("manifest.json"))
    first = manifest["fitted_metric"]["block_metrics"][0]
    assert "projection" not in first
    assert first["projection_member"].endswith("projection.npy")


def test_checkpoint_evaluation_batches_and_reuses_provider() -> None:
    frames = []
    predictions = []
    for index in range(5):
        atoms = Atoms(
            "LiO",
            positions=[[0.0, 0.0, 0.0], [1.0 + index * 0.01, 0.0, 0.0]],
            cell=np.eye(3) * 5.0,
            pbc=True,
        )
        atoms.info["REF_energy"] = float(index)
        atoms.arrays["REF_forces"] = np.zeros((2, 3), dtype=np.float64)
        atoms.info["REF_stress"] = np.zeros(6, dtype=np.float64)
        frames.append(atoms)
        predictions.append(
            mdstats.AtomicModelPrediction(
                energy_ev=float(index),
                forces_ev_per_angstrom=np.zeros((2, 3), dtype=np.float64),
                stress_ev_per_angstrom3=np.zeros((3, 3), dtype=np.float64),
            )
        )

    class Provider:
        def __init__(self):
            self.heads: list[str | None] = []
            self.batch_sizes: list[int] = []
            self.cursor = 0

        def set_head(self, head):
            self.heads.append(head)

        def predict_batch(self, batch):
            self.batch_sizes.append(len(batch))
            first = self.cursor
            self.cursor += len(batch)
            return tuple(predictions[first : first + len(batch)])

    provider = Provider()
    policy = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), batch_size=3
    )
    import threading
    from mdstats.training_data.inference_parallel import inference_start_signal

    inference_started = threading.Event()
    with inference_start_signal(inference_started.set):
        metrics = campaign_execution._evaluate_model_on_atoms(
            Path("unused.model"),
            tuple(frames),
            head="target_head",
            policy=policy,
            provider=provider,
        )
    assert inference_started.is_set()
    assert provider.heads == ["target_head"]
    assert provider.batch_sizes == [3, 2]
    assert metrics["energy_mae_ev_per_atom"] == 0.0
    assert metrics["force_component_rmse_ev_per_angstrom"] == 0.0
    assert metrics["stress_rmse_ev_per_angstrom3"] == 0.0
    assert metrics["condition_force_rmse_ev_per_angstrom"] == ()
    assert metrics["worst_condition_force_rmse_ev_per_angstrom"] == 0.0


def test_monitor_cache_is_bound_to_authenticated_file_identity(tmp_path: Path) -> None:
    monitor = tmp_path / "monitor.xyz"
    atoms = Atoms("H", positions=[[0.0, 0.0, 0.0]])
    write(monitor, [atoms], format="extxyz")
    monitor_sha = hashlib.sha256(monitor.read_bytes()).hexdigest()
    campaign_execution._as_atoms_tuple_cached.cache_clear()
    first = campaign_execution._as_atoms_list(
        monitor, expected_sha256=monitor_sha, use_cache=True
    )
    second = campaign_execution._as_atoms_list(
        monitor, expected_sha256=monitor_sha, use_cache=True
    )
    assert first is second
    assert not hasattr(campaign_execution, "_baseline_metrics_cached")


def test_shard_summary_and_energy_readers_do_not_materialize_heavy_members(
    tmp_path: Path, monkeypatch
) -> None:
    import mdstats.training_data.model_features as feature_module
    import mdstats.training_data.production_model_sweep as sweep_module

    _, frames, frame_data, _, data5, policy = _sweep_inputs(tmp_path)
    root = tmp_path / "selective-shards"
    result = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        _provider(_CountingCalculator()),
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            artifact_shard_size=3
        ),
    )

    descriptor_record = result.descriptor_manifest.records[0]
    frame_record = frames.frame(descriptor_record.frame_uid)
    species = tuple(
        sorted(
            int(value)
            for value in set(frame_data[frame_record.run_id].atomic_numbers)
        )
    )
    prediction_record = result.prediction_manifest.records[0]

    accessed_descriptor_members: list[str] = []
    real_descriptor_load = feature_module.np.load

    class TrackingArchive:
        def __init__(self, archive, accessed):
            self._archive = archive
            self._accessed = accessed

        @property
        def files(self):
            return self._archive.files

        def __getitem__(self, name):
            self._accessed.append(str(name))
            return self._archive[name]

        def __enter__(self):
            self._archive.__enter__()
            return self

        def __exit__(self, *args):
            return self._archive.__exit__(*args)

    def tracked_descriptor_load(*args, **kwargs):
        return TrackingArchive(
            real_descriptor_load(*args, **kwargs), accessed_descriptor_members
        )

    feature_module._load_descriptor_shard_cached.cache_clear()
    monkeypatch.setattr(feature_module.np, "load", tracked_descriptor_load)
    summary = read_mace_descriptor_summary(
        result.descriptor_manifest,
        root,
        descriptor_record.frame_uid,
        species,
    )
    assert summary is not None
    assert "descriptor_values" not in accessed_descriptor_members
    assert "descriptor_offsets" not in accessed_descriptor_members
    # Revision 4 maps stored NPY members directly from the NPZ file, so the
    # legacy ``numpy.load`` interception sees no member materialization at all.
    assert set(accessed_descriptor_members) in (
        set(),
        {
            "summary_global_mean",
            "summary_global_std",
            "summary_species_atomic_numbers",
            "summary_species_present",
            "summary_species_mean",
        },
    )

    accessed_prediction_members: list[str] = []
    real_prediction_load = sweep_module.np.load

    def tracked_prediction_load(*args, **kwargs):
        return TrackingArchive(
            real_prediction_load(*args, **kwargs), accessed_prediction_members
        )

    sweep_module._load_prediction_shard_cached.cache_clear()
    monkeypatch.setattr(sweep_module.np, "load", tracked_prediction_load)
    energy = sweep_module.read_atomic_model_prediction_energy(
        result.prediction_manifest,
        root,
        prediction_record.frame_uid,
    )
    assert np.isfinite(energy)
    assert accessed_prediction_members in ([], ["energies"])
