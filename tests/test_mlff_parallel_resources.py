from __future__ import annotations

from dataclasses import replace

import mdstats

from mdstats.training_data.resources import (
    GpuResourceSnapshot,
    SystemResourceSnapshot,
    resolve_worker_count,
)
from tests.test_mlff_data4_raw_features_events import _framework_catalogs


def _resources(cpu: int, ram: int) -> SystemResourceSnapshot:
    return SystemResourceSnapshot(
        cpu_threads_available=cpu,
        cpu_fraction=0.9,
        cpu_threads_budget=max(1, int(cpu * 0.9)),
        ram_available_bytes=ram,
        ram_fraction=0.8,
        ram_budget_bytes=int(ram * 0.8),
        gpu_memory_fraction=0.9,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "test"),
    )


def test_worker_plan_uses_ninety_percent_cpu_and_eighty_percent_ram_bound() -> None:
    resources = _resources(128, 256 * 1024**3)
    assert resources.cpu_threads_budget == 115
    assert resolve_worker_count(
        task_count=200,
        resources=resources,
        estimated_bytes_per_worker=2 * 1024**3,
    ) == 102
    assert resolve_worker_count(
        task_count=200,
        resources=resources,
        estimated_bytes_per_worker=4 * 1024**3,
    ) == 51
    # Parent-side scientific output is reserved before assigning workers.
    assert resolve_worker_count(
        task_count=200,
        resources=resources,
        estimated_bytes_per_worker=4 * 1024**3,
        reserved_bytes=40 * 1024**3,
    ) == 41
    # Trajectory-level execution cannot exceed the number of independent runs.
    assert resolve_worker_count(
        task_count=27,
        resources=resources,
        estimated_bytes_per_worker=512 * 1024**2,
    ) == 27


def test_parallel_data3_and_data4_preserve_scientific_identity(tmp_path) -> None:
    sources, frames_serial, data = _framework_catalogs(tmp_path)
    targets = {
        name: mdstats.TemperatureTargetEvidence(700.0, 700.0, "test")
        for name in data
    }
    frames_parallel = mdstats.build_training_frame_catalog(
        sources,
        data,
        temperature_targets_by_run=targets,
        parallel_workers=2,
    )
    assert frames_parallel.content_digest == frames_serial.content_digest

    raw_serial = mdstats.build_raw_feature_catalog(
        sources, frames_serial, data, policy=mdstats.RawFeaturePolicy.lta_default()
    )
    raw_parallel = mdstats.build_raw_feature_catalog(
        sources,
        frames_parallel,
        data,
        policy=mdstats.RawFeaturePolicy.lta_default(),
        parallel_workers=2,
    )
    assert raw_parallel.content_digest == raw_serial.content_digest

    lta_policy = mdstats.LtaPartitionProfilePolicy(require_oxygen_framework_coordination=4)
    lta_serial = mdstats.build_lta_partition_feature_catalog(
        frames_serial, data, policy=lta_policy
    )
    lta_parallel = mdstats.build_lta_partition_feature_catalog(
        frames_parallel, data, policy=lta_policy, parallel_workers=2
    )
    assert lta_parallel.content_digest == lta_serial.content_digest

class _BatchProvider:
    def __init__(self, base, *, fail_once=False):
        self.base = base
        self.checkpoint_identity = base.checkpoint_identity
        self.batch_descriptor_calls = 0
        self.batch_prediction_calls = 0
        self.fail_once = fail_once

    def get_descriptors(self, atoms, policy):
        return self.base.get_descriptors(atoms, policy)

    def predict(self, atoms):
        return self.base.predict(atoms)

    def get_descriptors_batch(self, atoms_batch, policy):
        self.batch_descriptor_calls += 1
        return tuple(self.base.get_descriptors(atoms, policy) for atoms in atoms_batch)

    def predict_batch(self, atoms_batch):
        self.batch_prediction_calls += 1
        if self.fail_once and len(atoms_batch) > 1:
            self.fail_once = False
            raise RuntimeError("CUDA out of memory: synthetic test")
        return tuple(self.base.predict(atoms) for atoms in atoms_batch)


def test_data6_uses_batch_provider_and_adaptive_oom(tmp_path):
    from tests.test_mlff_data9a9a_production_model_sweep import _CountingCalculator, _inputs, _provider

    _, frames, frame_data, _, data5, policy = _inputs(tmp_path)
    provider = _BatchProvider(_provider(_CountingCalculator()), fail_once=True)
    result = mdstats.run_restartable_data6_model_sweep(
        frames,
        frame_data,
        data5,
        policy,
        provider,
        tmp_path / "batched-sweep",
        execution_policy=mdstats.Data6ModelSweepExecutionPolicy(
            batch_size=4,
            adaptive_batching=True,
        ),
    )
    assert result.complete
    assert provider.batch_descriptor_calls > 0
    assert provider.batch_prediction_calls > 1


def test_explicit_worker_request_cannot_bypass_cpu_fraction_budget() -> None:
    resources = _resources(cpu=32, ram=8 * 1024**3)
    assert resources.cpu_threads_budget == 28
    assert resolve_worker_count(task_count=64, resources=resources, requested=32) == 28


def test_stage_scope_accounts_native_openmp_separately() -> None:
    from mdstats.training_data.resources import StageResourceScope

    scope = StageResourceScope(
        stage_name="native",
        cpu_threads_available=32,
        cpu_threads_budget=28,
        python_workers=1,
        native_openmp_threads=28,
    )
    assert scope.estimated_nested_cpu_threads == 28
    assert "openmp=28" in scope.summary()


def test_stage_scope_rejects_native_openmp_oversubscription() -> None:
    import pytest
    from mdstats.training_data.resources import StageResourceScope

    with pytest.raises(ValueError, match="nested CPU threads"):
        StageResourceScope(
            stage_name="native-over",
            cpu_threads_available=32,
            cpu_threads_budget=28,
            python_workers=2,
            native_openmp_threads=28,
        )




def test_structural_autotune_capacity_uses_supplied_runtime_budget() -> None:
    from mdstats.training_data.structural_selection import _automatic_structural_worker_cap

    assert _automatic_structural_worker_cap(100, cpu_budget=28) == 28
    assert _automatic_structural_worker_cap(12, cpu_budget=28) == 12
