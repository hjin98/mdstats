from __future__ import annotations

import numpy as np
import pytest
from scipy.fft import ifftn, fftn

from mdstats.plotting import density_gpu
from mdstats.plotting.density_gpu import (
    DENSITY_GPU_REPORT_SCHEMA,
    DensityGPUDevice,
    DensityGPUExecutionPolicy,
    decide_gpu_execution,
    density_gpu_journal_scope,
    density_gpu_report,
    discover_density_gpu,
    try_gpu_circular_fft_convolution,
)
from mdstats.plotting.density_contracts import DensityKernelOptions
from mdstats.plotting.density_kernel import smooth_periodic_node_masses


def _device(*, free: int = 8 * 1024**3, fraction: float = 0.80) -> DensityGPUDevice:
    return DensityGPUDevice(
        provider="fixture_cuda",
        device_index=0,
        name="Fixture GPU",
        total_memory_bytes=12 * 1024**3,
        free_memory_bytes=free,
        usable_memory_bytes=int(fraction * free),
        memory_fraction=fraction,
        compute_capability="8.6",
    )


def test_gpu_policy_defaults_to_eighty_percent_vram_and_auto_mode() -> None:
    policy = DensityGPUExecutionPolicy()
    assert policy.mode == "auto"
    assert policy.memory_fraction == pytest.approx(0.80)
    assert policy.to_json_dict()["memory_fraction"] == pytest.approx(0.80)


def test_gpu_selection_prices_transfer_setup_and_vram() -> None:
    device = _device()
    policy = DensityGPUExecutionPolicy(
        mode="auto",
        setup_seconds=0.01,
        transfer_bytes_per_second=10_000_000_000.0,
        assumed_gpu_speedup=4.0,
        min_cpu_seconds=0.0,
    )
    chosen = decide_gpu_execution(
        kernel="fixture",
        cpu_estimate_seconds=2.0,
        transfer_bytes=100_000_000,
        required_vram_bytes=1_000_000_000,
        policy=policy,
        device=device,
    )
    assert chosen.selected is True
    assert chosen.reason == "predicted_gpu_wall_time_lower"
    assert chosen.gpu_estimate_seconds == pytest.approx(0.52)

    transfer_bound = decide_gpu_execution(
        kernel="fixture",
        cpu_estimate_seconds=0.05,
        transfer_bytes=2_000_000_000,
        required_vram_bytes=1_000_000_000,
        policy=policy,
        device=device,
    )
    assert transfer_bound.selected is False
    assert transfer_bound.reason == "transfer_setup_cost_not_amortized"

    vram_bound = decide_gpu_execution(
        kernel="fixture",
        cpu_estimate_seconds=10.0,
        transfer_bytes=1,
        required_vram_bytes=device.usable_memory_bytes + 1,
        policy=policy,
        device=device,
    )
    assert vram_bound.selected is False
    assert vram_bound.reason == "vram_budget_exceeded"


def test_cuda_absence_is_clean_cpu_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(density_gpu, "_load_torch_cuda", lambda: None)
    assert discover_density_gpu(policy=DensityGPUExecutionPolicy(mode="auto")) is None
    with density_gpu_journal_scope() as journal:
        result = try_gpu_circular_fft_convolution(
            np.ones((8, 8, 8), dtype=np.float64),
            np.ones((8, 8, 8), dtype=np.float64),
            cpu_estimate_seconds=10.0,
            policy=DensityGPUExecutionPolicy(mode="auto"),
        )
    assert result is None
    report = density_gpu_report(journal)
    assert report["schema_version"] == DENSITY_GPU_REPORT_SCHEMA
    assert report["gpu_selected_count"] == 0
    assert report["cpu_fallback_count"] == 1
    assert report["decision_samples"][0]["reason"] == "cuda_unavailable"


def test_gpu_disabled_dense_smoothing_is_identical_to_qualified_cpu_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MDSTATS_DENSITY_GPU", "off")
    rng = np.random.default_rng(42)
    mass = rng.random((10, 11, 12), dtype=np.float64)
    mass /= np.sum(mass, dtype=np.float64)
    smoothed, metadata = smooth_periodic_node_masses(
        mass,
        np.diag([10.0, 11.0, 12.0]),
        0.7,
        DensityKernelOptions(),
    )
    assert smoothed.dtype == np.float64
    assert np.sum(smoothed, dtype=np.float64) == pytest.approx(1.0, abs=5e-13)
    assert metadata["fft_execution_backend"] == "scipy_fft_cpu"
    assert metadata["gpu_execution_is_scientifically_neutral"] is True


def test_forced_gpu_helper_matches_cpu_fp64_when_cuda_is_available() -> None:
    device = discover_density_gpu(policy=DensityGPUExecutionPolicy(mode="force"))
    if device is None:
        pytest.skip("CUDA runtime unavailable on this test host")
    rng = np.random.default_rng(7)
    mass = rng.random((16, 16, 16), dtype=np.float64)
    kernel = rng.random((16, 16, 16), dtype=np.float64)
    gpu = try_gpu_circular_fft_convolution(
        mass,
        kernel,
        cpu_estimate_seconds=1.0,
        policy=DensityGPUExecutionPolicy(mode="force"),
    )
    assert gpu is not None
    cpu = ifftn(fftn(mass) * fftn(kernel)).real
    scale = max(1.0, float(np.max(np.abs(cpu))))
    assert float(np.max(np.abs(gpu - cpu))) <= 5.0e-12 * scale


def test_forced_gpu_cic_matches_cpu_when_cuda_is_available() -> None:
    device = discover_density_gpu(policy=DensityGPUExecutionPolicy(mode="force"))
    if device is None:
        pytest.skip("CUDA runtime unavailable on this test host")
    from mdstats.plotting.atomic_density import _deposit_cic
    rng = np.random.default_rng(11)
    fractional = rng.random((2048, 3), dtype=np.float64)
    weights = rng.random(2048, dtype=np.float64)
    weights /= np.sum(weights, dtype=np.float64)
    # Keep the reference CPU path explicit rather than routing through _deposit_cic,
    # which may itself select CUDA under the current environment.
    shape = (32, 33, 34)
    grid = np.zeros(shape, dtype=np.float64)
    scaled = fractional * np.asarray(shape, dtype=np.float64)
    base = np.floor(scaled).astype(np.int64)
    delta = scaled - base
    for ox in (0, 1):
        wx = (1.0 - delta[:, 0]) if ox == 0 else delta[:, 0]
        ix = (base[:, 0] + ox) % shape[0]
        for oy in (0, 1):
            wy = (1.0 - delta[:, 1]) if oy == 0 else delta[:, 1]
            iy = (base[:, 1] + oy) % shape[1]
            for oz in (0, 1):
                wz = (1.0 - delta[:, 2]) if oz == 0 else delta[:, 2]
                iz = (base[:, 2] + oz) % shape[2]
                np.add.at(grid, (ix, iy, iz), weights * wx * wy * wz)
    gpu = density_gpu.try_gpu_cic_deposition(
        fractional,
        weights,
        shape,
        cpu_estimate_seconds=1.0,
        policy=DensityGPUExecutionPolicy(mode="force"),
    )
    assert gpu is not None
    assert np.sum(gpu, dtype=np.float64) == pytest.approx(np.sum(grid, dtype=np.float64), abs=5e-13)
    scale = max(1.0, float(np.max(np.abs(grid))))
    assert float(np.max(np.abs(gpu - grid))) <= 2.0e-12 * scale


def test_scene_scheduler_propagates_gpu_journal_into_worker_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    from mdstats.plotting.density_scheduler import (
        DensityScheduledTask,
        DensitySceneScheduler,
        DensityTaskResources,
    )
    from mdstats.plotting.runtime_resources import RuntimeResourceBudget, RuntimeResourceSnapshot

    monkeypatch.setenv("MDSTATS_DENSITY_GPU", "off")
    snapshot = RuntimeResourceSnapshot(
        logical_cpu_count=4,
        affinity_cpu_count=4,
        cgroup_cpu_quota=None,
        scheduler_cpu_count=None,
        available_cpu_count=4,
        host_memory_available_bytes=2 * 1024**3,
        cgroup_memory_limit_bytes=None,
        cgroup_memory_current_bytes=None,
        scheduler_memory_limit_bytes=None,
        rlimit_as_bytes=None,
        process_rss_bytes=1,
        process_virtual_memory_bytes=1,
        available_memory_bytes=2 * 1024**3,
    )
    budget = RuntimeResourceBudget(
        max_memory_bytes=1024**3,
        max_threads=2,
        max_wall_time_seconds=1200.0,
        memory_fraction=0.8,
        thread_fraction=0.9,
        snapshot=snapshot,
        memory_override_source="fixture",
        thread_override_source="fixture",
        wall_time_override_source="fixture",
    )
    scheduler = DensitySceneScheduler(budget)
    resources = DensityTaskResources(
        task_id="gpu-journal-propagation",
        construction_order=0,
        retained_bytes=1,
        transient_bytes=1,
        minimum_workers=1,
        preferred_workers=1,
        backend="fixture",
    )

    def task(_lease):
        decision = decide_gpu_execution(
            kernel="journal_fixture",
            cpu_estimate_seconds=1.0,
            transfer_bytes=1,
            required_vram_bytes=1,
        )
        # Record through a real helper so this exercises the scheduler worker
        # context, not just decision construction.
        with density_gpu._admitted_device(decision) as admitted:
            assert admitted is False
        return 7

    with density_gpu_journal_scope() as journal:
        assert scheduler.run((DensityScheduledTask(resources=resources, function=task),)) == (7,)
    report = density_gpu_report(journal)
    assert report["attempt_count"] == 1
    assert report["reason_counts"] == {"gpu_disabled": 1}
