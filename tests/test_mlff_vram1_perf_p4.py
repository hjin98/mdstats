from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import mdstats
from mdstats.training_data._common import digest
from tests.test_mlff_data9a9a_production_model_sweep import (
    _CountingCalculator,
    _inputs,
    _provider,
)


def test_vram1_v1_calibration_remains_readable() -> None:
    payload = {
        "schema": "mdstats.mace-batch-capacity-calibration.v1",
        "descriptor_signature_digest": "a" * 64,
        "device": "cpu",
        "requested_max_batch_size": 4,
        "probed_batch_sizes": [1],
        "successful_batch_sizes": [1],
        "recommended_batch_size": 1,
        "descriptor_bytes_per_structure": 1024,
        "graph_bytes_per_structure": 2048,
        "peak_device_bytes_per_structure": None,
        "device_budget_bytes": None,
        "calibration_method": "model_aware_probe_v1",
    }
    payload["content_digest"] = digest(payload)
    restored = mdstats.MaceBatchCapacityCalibration.from_dict(payload)
    assert restored.workload_mode is mdstats.MaceBatchWorkloadMode.DESCRIPTOR_ONLY
    assert restored.calibration_method == "model_aware_probe_v1"
    assert restored.to_dict()["schema"] == "mdstats.mace-batch-capacity-calibration.v2"


def test_vram1_cpu_combined_calibration_is_v2_and_roundtrips() -> None:
    from ase import Atoms
    from tests.test_mlff_data6_mace_native_batch_autograd import _real_mace_provider

    provider, _ = _real_mace_provider()
    atoms = (
        Atoms("H2O", positions=((0, 0, 0), (0.8, 0, 0), (0, 0.8, 0)), cell=(8, 8, 8), pbc=True),
        Atoms("H2O", positions=((0, 0, 0), (0.9, 0, 0), (0, 0.9, 0)), cell=(8, 8, 8), pbc=True),
    )
    calibration = provider.calibrate_batch_capacity(
        atoms,
        mdstats.MaceDescriptorPolicy(),
        maximum_batch_size=4,
        workload_mode=mdstats.MaceBatchWorkloadMode.COMBINED_EVALUATE,
        stress_sample_count=2,
    )
    assert calibration.workload_mode is mdstats.MaceBatchWorkloadMode.COMBINED_EVALUATE
    assert calibration.checkpoint_identity_digest == provider.checkpoint_identity.content_digest
    assert len(calibration.calibration_frame_digests) == 2
    assert calibration.probes and calibration.probes[0].success
    assert calibration.recommended_batch_size == 1  # CPU cannot authorize a VRAM batch.
    assert mdstats.MaceBatchCapacityCalibration.from_dict(calibration.to_dict()) == calibration


class _TrackingBatchProvider:
    def __init__(self, base, *, fail_above: int | None = None, fail_once: bool = False):
        self.base = base
        self.checkpoint_identity = base.checkpoint_identity
        self.fail_above = fail_above
        self.fail_once = fail_once
        self.batch_sizes: list[int] = []

    def get_descriptors(self, atoms, policy):
        return self.base.get_descriptors(atoms, policy)

    def predict(self, atoms):
        return self.base.predict(atoms)

    def get_descriptors_batch(self, atoms_batch, policy):
        return tuple(self.base.get_descriptors(atoms, policy) for atoms in atoms_batch)

    def predict_batch(self, atoms_batch):
        size = len(atoms_batch)
        self.batch_sizes.append(size)
        should_fail = self.fail_above is not None and size > self.fail_above
        if should_fail and (not self.fail_once or self.fail_once):
            if self.fail_once:
                self.fail_once = False
                self.fail_above = None
            raise RuntimeError("CUDA out of memory: synthetic VRAM1 test")
        return tuple(self.base.predict(atoms) for atoms in atoms_batch)


def test_vram1_oom_cap_is_persisted_and_reused_only_for_matching_identity(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    root = tmp_path / "oom-cap"
    provider = _TrackingBatchProvider(_provider(_CountingCalculator()), fail_above=2, fail_once=True)
    first = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            max_new_frames=4,
            batch_size=4,
            adaptive_batching=True,
            pipeline_enabled=True,
            capacity_calibration_digest="1" * 64,
        ),
    )
    assert not first.complete
    assert first.runtime_batch_cap is not None
    assert first.runtime_batch_cap.safe_batch_size == 2
    assert first.runtime_batch_cap.rejected_batch_size == 4
    payload = json.loads((root / "data6_runtime_batch_cap.json").read_text())
    assert mdstats.Data6RuntimeBatchCap.from_dict(payload) == first.runtime_batch_cap

    resumed_provider = _TrackingBatchProvider(_provider(_CountingCalculator()), fail_above=2)
    resumed = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        resumed_provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=4,
            adaptive_batching=True,
            pipeline_enabled=True,
            capacity_calibration_digest="1" * 64,
        ),
    )
    assert resumed.complete
    assert resumed_provider.batch_sizes
    assert max(resumed_provider.batch_sizes) <= 2


def test_perf_p4_pipeline_and_synchronous_execution_are_scientifically_equal(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    sync_root = tmp_path / "sync"
    pipe_root = tmp_path / "pipe"
    sync = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        _provider(_CountingCalculator()),
        sync_root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=4,
            artifact_shard_size=3,
            pipeline_enabled=False,
        ),
    )
    piped = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        _provider(_CountingCalculator()),
        pipe_root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=4,
            artifact_shard_size=3,
            pipeline_enabled=True,
            persistence_queue_depth=1,
        ),
    )
    assert sync.complete and piped.complete
    assert sync.checkpoint.plan.content_digest == piped.checkpoint.plan.content_digest
    assert tuple(r.frame_uid for r in sync.checkpoint.records) == tuple(
        r.frame_uid for r in piped.checkpoint.records
    )
    for uid in sync.checkpoint.plan.descriptor_frame_uids:
        left = mdstats.read_mace_descriptor_array(sync.descriptor_manifest, sync_root, uid)
        right = mdstats.read_mace_descriptor_array(piped.descriptor_manifest, pipe_root, uid)
        assert np.array_equal(left, right)
    for uid in sync.checkpoint.plan.prediction_frame_uids:
        left = mdstats.read_atomic_model_prediction(sync.prediction_manifest, sync_root, uid)
        right = mdstats.read_atomic_model_prediction(piped.prediction_manifest, pipe_root, uid)
        assert left.energy_ev == right.energy_ev
        assert np.array_equal(left.forces_ev_per_angstrom, right.forces_ev_per_angstrom)
        if left.stress_ev_per_angstrom3 is None:
            assert right.stress_ev_per_angstrom3 is None
        else:
            assert np.array_equal(left.stress_ev_per_angstrom3, right.stress_ev_per_angstrom3)


def test_perf_p4_queue_depth_is_fail_closed() -> None:
    for value in (0, 3):
        try:
            mdstats.Data6ModelSweepExecutionPolicy(persistence_queue_depth=value)
        except Exception as exc:
            assert "persistence_queue_depth" in str(exc)
        else:  # pragma: no cover
            raise AssertionError("invalid persistence queue depth was accepted")


def test_vram1_throughput_rule_keeps_smallest_near_best_safe_batch() -> None:
    probe = mdstats.MaceBatchCapacityProbe
    gib = 1024**3
    probes = (
        probe(
            batch_size=1,
            elapsed_seconds=1.0,
            structures_per_second=90.0,
            success=True,
            baseline_reserved_bytes=1 * gib,
            peak_reserved_bytes=2 * gib,
            driver_free_after_bytes=10 * gib,
            driver_total_bytes=16 * gib,
        ),
        probe(
            batch_size=2,
            elapsed_seconds=1.0,
            structures_per_second=100.0,
            success=True,
            baseline_reserved_bytes=1 * gib,
            peak_reserved_bytes=4 * gib,
            driver_free_after_bytes=8 * gib,
            driver_total_bytes=16 * gib,
        ),
        probe(
            batch_size=4,
            elapsed_seconds=1.0,
            structures_per_second=103.0,
            success=True,
            baseline_reserved_bytes=1 * gib,
            peak_reserved_bytes=7 * gib,
            driver_free_after_bytes=5 * gib,
            driver_total_bytes=16 * gib,
        ),
        probe(
            batch_size=8,
            elapsed_seconds=1.0,
            structures_per_second=120.0,
            success=True,
            baseline_reserved_bytes=1 * gib,
            peak_reserved_bytes=13 * gib,
            driver_free_after_bytes=3 * gib,
            driver_total_bytes=16 * gib,
        ),
    )
    result = mdstats.recommend_mace_batch_size_from_probes(
        probes,
        max_device_fraction=0.80,
        reserve_bytes=4 * gib,
        throughput_tolerance_fraction=0.05,
    )
    assert result == 2


def test_vram1_mismatched_persisted_cap_does_not_clamp_new_identity(tmp_path: Path) -> None:
    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    root = tmp_path / "mismatched-cap"
    first_provider = _TrackingBatchProvider(_provider(_CountingCalculator()), fail_above=2, fail_once=True)
    first = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        first_provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            max_new_frames=4,
            batch_size=4,
            adaptive_batching=True,
            capacity_calibration_digest="1" * 64,
        ),
    )
    assert first.runtime_batch_cap is not None
    old_identity = first.runtime_batch_cap.identity_digest

    second_provider = _TrackingBatchProvider(_provider(_CountingCalculator()), fail_above=2, fail_once=True)
    second = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        second_provider,
        root,
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=4,
            adaptive_batching=True,
            capacity_calibration_digest="2" * 64,
        ),
    )
    assert second.complete
    assert second_provider.batch_sizes and second_provider.batch_sizes[0] == 4
    assert second.runtime_batch_cap is not None
    assert second.runtime_batch_cap.identity_digest != old_identity
    assert second.runtime_batch_cap.safe_batch_size == 2


def test_vram1_live_vram_reclamp_is_stricter_than_calibrated_cap(monkeypatch) -> None:
    import torch
    from mdstats.training_data import campaign_cli
    from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot

    gib = 1024**3
    resources = SystemResourceSnapshot(
        cpu_threads_available=8,
        cpu_fraction=0.9,
        cpu_threads_budget=7,
        ram_available_bytes=32 * gib,
        ram_fraction=0.8,
        ram_budget_bytes=24 * gib,
        gpu_memory_fraction=0.9,
        gpu=GpuResourceSnapshot(
            available=True,
            device_count=1,
            selected_device=0,
            device_name="synthetic-gpu",
            free_bytes=5 * gib,
            total_bytes=16 * gib,
            budget_bytes=6 * gib,
            reason="",
        ),
    )
    monkeypatch.setattr(campaign_cli._core, "_performance_resources", lambda cfg: resources)
    monkeypatch.setattr(torch.cuda, "mem_get_info", lambda device=None: (5 * gib, 16 * gib))
    monkeypatch.setattr(torch.cuda, "memory_reserved", lambda device=None: 3 * gib)

    calibration = mdstats.MaceBatchCapacityCalibration(
        descriptor_signature_digest="a" * 64,
        checkpoint_identity_digest="b" * 64,
        device="cuda:0",
        workload_mode=mdstats.MaceBatchWorkloadMode.COMBINED_EVALUATE,
        requested_max_batch_size=8,
        probed_batch_sizes=(1, 2, 4, 8),
        successful_batch_sizes=(1, 2, 4, 8),
        recommended_batch_size=8,
        descriptor_bytes_per_structure=1024,
        graph_bytes_per_structure=2048,
        peak_device_bytes_per_structure=1 * gib,
        max_device_fraction=0.80,
        reserve_bytes=4 * gib,
    )
    cfg = {
        "model": {
            "device": "cuda:0",
            "inference_batch_size": 0,
            "maximum_inference_batch_size": 8,
            "pipeline_enabled": False,
        }
    }
    batch, _, estimate = campaign_cli._resolve_model_sweep_batch_size(
        cfg, task_count=100, calibration=calibration
    )
    assert estimate == 1 * gib
    assert batch == 1


def test_perf_p4_host_queue_residency_clamps_batch(monkeypatch) -> None:
    from mdstats.training_data import campaign_cli
    from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot

    resources = SystemResourceSnapshot(
        cpu_threads_available=8,
        cpu_fraction=0.9,
        cpu_threads_budget=7,
        ram_available_bytes=1000,
        ram_fraction=0.8,
        ram_budget_bytes=650,
        gpu_memory_fraction=0.9,
        gpu=GpuResourceSnapshot(
            available=False,
            device_count=0,
            selected_device=None,
            device_name=None,
            free_bytes=None,
            total_bytes=None,
            budget_bytes=None,
            reason="cpu fixture",
        ),
    )
    monkeypatch.setattr(campaign_cli._core, "_performance_resources", lambda cfg: resources)
    calibration = mdstats.MaceBatchCapacityCalibration(
        descriptor_signature_digest="a" * 64,
        checkpoint_identity_digest="b" * 64,
        device="cpu",
        workload_mode=mdstats.MaceBatchWorkloadMode.COMBINED_EVALUATE,
        requested_max_batch_size=8,
        probed_batch_sizes=(8,),
        successful_batch_sizes=(8,),
        recommended_batch_size=8,
        descriptor_bytes_per_structure=30,
        graph_bytes_per_structure=40,
        prediction_bytes_per_structure=30,
    )
    # This deliberately omits detailed probe records to isolate the host-residency
    # equation: 100 bytes/frame * 3 resident slots.
    batch, _, _ = campaign_cli._resolve_model_sweep_batch_size(
        {
            "model": {
                "device": "cpu",
                "inference_batch_size": 8,
                "maximum_inference_batch_size": 8,
                "pipeline_enabled": True,
                "persistence_queue_depth": 1,
            }
        },
        task_count=100,
        calibration=calibration,
    )
    assert batch == 2


def test_perf_p4_real_foundations_prepared_and_direct_batches_match_exactly() -> None:
    import hashlib
    import os
    import warnings

    import pytest
    from ase import Atoms

    pytest.importorskip("mace")
    from mace.calculators import MACECalculator

    structures = (
        Atoms("NaCl", positions=((0, 0, 0), (2.6, 2.6, 2.6)), cell=(5.2, 5.2, 5.2), pbc=True),
        Atoms("NaCl", positions=((0, 0, 0), (2.68, 2.6, 2.6)), cell=(5.2, 5.2, 5.2), pbc=True),
    )
    for env_name, head in (
        ("MDSTATS_TEST_MH1_MODEL", "omat_pbe"),
        ("MDSTATS_TEST_MPA0_MODEL", "default"),
    ):
        raw = os.environ.get(env_name)
        if not raw:
            pytest.skip(f"{env_name} is not set")
        path = Path(raw)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            calculator = MACECalculator(
                model_paths=str(path), head=head, device="cpu", default_dtype="float64"
            )
        identity = mdstats.ModelCheckpointIdentity(
            model_family="MACE",
            checkpoint_locator=str(path),
            checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            calculator_class="mace.calculators.MACECalculator",
            model_version="0.3.16",
            supported_atomic_numbers=tuple(int(v) for v in calculator.z_table.zs),
            device="cpu",
            default_dtype="float64",
        )
        provider = mdstats.MaceCalculatorProvider.from_calculator(
            calculator, checkpoint_identity=identity
        )
        policy = mdstats.MaceDescriptorPolicy(invariants_only=True)
        direct_descriptors, direct_predictions = provider.evaluate_batch(structures, policy)
        prepared = provider.prepare_evaluate_batch(structures)
        prepared_descriptors, prepared_predictions = provider.evaluate_prepared_batch(prepared, policy)
        for left, right in zip(direct_descriptors, prepared_descriptors, strict=True):
            assert np.array_equal(left, right)
        for left, right in zip(direct_predictions, prepared_predictions, strict=True):
            assert left.energy_ev == right.energy_ev
            assert np.array_equal(left.forces_ev_per_angstrom, right.forces_ev_per_angstrom)
            if left.stress_ev_per_angstrom3 is None:
                assert right.stress_ev_per_angstrom3 is None
            else:
                assert np.array_equal(left.stress_ev_per_angstrom3, right.stress_ev_per_angstrom3)
