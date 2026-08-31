from __future__ import annotations

import pytest

from mdstats.training_data.inference_parallel import (
    AdaptiveInferenceConcurrency,
    CpuTelemetryProbe,
    CpuTelemetrySample,
    InferenceConcurrencyPolicy,
    build_inference_concurrency_plan,
)
from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot
from mdstats.training_data.training_parallel import GpuTelemetrySample

_MIB = 1024 ** 2
_GIB = 1024 ** 3


def _resources(*, cpu: int = 32, ram_gib: int = 128, gpu_available: bool = True) -> SystemResourceSnapshot:
    return SystemResourceSnapshot(
        cpu_threads_available=cpu,
        cpu_fraction=0.90,
        cpu_threads_budget=max(1, int(cpu * 0.90)),
        ram_available_bytes=ram_gib * _GIB,
        ram_fraction=0.80,
        ram_budget_bytes=int(ram_gib * _GIB * 0.80),
        gpu_memory_fraction=0.90,
        gpu=GpuResourceSnapshot(
            available=gpu_available,
            device_count=1 if gpu_available else 0,
            selected_device=0 if gpu_available else None,
            device_name="RTX 3090" if gpu_available else None,
            free_bytes=int(23.6 * _GIB) if gpu_available else None,
            total_bytes=24 * _GIB if gpu_available else None,
            budget_bytes=int(24 * 0.90 * _GIB) if gpu_available else None,
            reason="available" if gpu_available else "CUDA unavailable",
        ),
    )


def _gpu_sample(second: float, used_gib: float, util: float) -> GpuTelemetrySample:
    return GpuTelemetrySample(
        sampled_monotonic=second,
        device_index=0,
        utilization_percent=util,
        used_bytes=int(used_gib * _GIB),
        total_bytes=24 * _GIB,
    )


def test_cuda_inference_starts_one_job_with_ninety_percent_admission_limits() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=8,
        estimated_gpu_memory_mib_per_job=4096.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=8,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    assert plan.initial_jobs == 1
    assert plan.maximum_jobs == 8
    assert plan.gpu_memory_budget_bytes == int(24 * _GIB * 0.90)
    assert plan.gpu_utilization_budget_percent == 90.0
    assert plan.ram_budget_bytes == int(128 * _GIB * 0.80)


def test_cuda_single_job_calibration_filters_near_zero_samples_and_sets_fixed_target() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=6,
        stabilization_seconds=30.0,
        minimum_gpu_activity_fraction=0.01,
        stability_samples=3,
        monitor_interval_seconds=5.0,
        estimated_gpu_memory_mib_per_job=4096.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=6,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)

    # Initialization/IO samples below 1% incremental activity are discarded.
    for second in (5.0, 10.0, 15.0):
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, 1.1, 2.4),
            now=second,
        )
        assert not decision.changed
        assert controller.target_jobs == 1

    # Real work is retained independently for GPU utilization and incremental VRAM.
    for second, used, util in (
        (20.0, 4.0, 22.0),
        (25.0, 4.2, 24.0),
        (30.0, 4.1, 23.0),
    ):
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, used, util),
            now=second,
        )

    assert decision.changed
    assert controller.gpu_calibrated
    assert controller.target_jobs == 3
    assert "retained GPU-utilization samples=3" in decision.reason
    assert "VRAM samples=3" in decision.reason
    assert "highest 5%" in decision.reason
    assert decision.predicted_memory_bytes_at_target is not None
    assert decision.predicted_memory_bytes_at_target < plan.gpu_memory_budget_bytes
    assert decision.predicted_utilization_percent_at_target is not None
    assert decision.predicted_utilization_percent_at_target < 90.0

def test_cuda_single_job_calibration_caps_fixed_target_below_ninety_percent() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=6,
        stabilization_seconds=20.0,
        minimum_gpu_activity_fraction=0.01,
        stability_samples=2,
        monitor_interval_seconds=5.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=6,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 5.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    decision = None
    for second, used, util in (
        (5.0, 3.0, 43.0),
        (10.0, 3.1, 45.0),
        (15.0, 3.0, 44.0),
        (20.0, 3.1, 45.0),
    ):
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, used, util),
            now=second,
        )
    assert decision is not None and decision.changed
    # Baseline is 5%; retained incremental utilization is ~39%, so two jobs
    # remain below 90% after the 5% growth margin but three do not.
    assert controller.target_jobs == 2
    predicted_memory, predicted_util = controller._cuda_projection_for_jobs(3)
    assert predicted_util >= 90.0

def test_cuda_calibration_keeps_vram_peak_while_trimming_utilization() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=8,
        stabilization_seconds=20.0,
        minimum_gpu_activity_fraction=0.01,
        gpu_calibration_peak_trim_fraction=0.10,
        gpu_calibration_band_fraction=0.10,
        stability_samples=2,
        monitor_interval_seconds=2.0,
        estimated_gpu_memory_mib_per_job=512.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=8,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)

    # GPU utilization may use the representative upper band, but the extreme
    # allocation remains safety evidence for VRAM admission.
    decision = None
    for index in range(1, 11):
        second = float(index * 2)
        if index <= 8:
            used_gib, util = 2.0, 12.0
        elif index == 9:
            used_gib, util = 5.0, 42.0
        else:
            used_gib, util = 10.0, 92.0
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, used_gib, util),
            now=second,
        )

    assert decision is not None
    assert controller.gpu_calibrated
    # Baseline is 2% GPU and 1 GiB VRAM. Utilization uses the representative
    # 40% increment while VRAM retains the 9-GiB incremental allocation peak.
    assert controller._gpu_estimated_utilization_per_job == 40.0
    assert controller._gpu_estimated_memory_bytes_per_job == 9 * _GIB
    assert controller.target_jobs == 2
    assert "VRAM uses the retained allocation peak" in decision.reason
    assert "next 10%" in decision.reason


def test_cpu_initial_parallelism_respects_ninety_percent_utility_and_eighty_percent_ram() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=0,
        estimated_ram_mib_per_job=8192.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=64,
        device="cpu",
        resources=_resources(cpu=32, ram_gib=64),
        policy=policy,
        gpu_sample=None,
        cpu_sample=CpuTelemetrySample(0.0, 10.0),
    )
    # RAM is the limiting resource: floor(0.8 * 64 / 8) = 6 jobs.
    assert plan.maximum_jobs == 6
    assert 1 <= plan.initial_jobs <= 6
    projected = 10.0 + plan.initial_jobs * plan.estimated_cpu_utilization_per_job
    assert projected <= 90.0


def test_one_job_ram_infeasibility_fails_before_launch() -> None:
    with pytest.raises(ValueError, match="cannot fit one job"):
        build_inference_concurrency_plan(
            task_count=1, device="cpu", resources=_resources(ram_gib=1),
            policy=InferenceConcurrencyPolicy(estimated_ram_mib_per_job=2048.0),
            gpu_sample=None, cpu_sample=CpuTelemetrySample(0.0, 0.0),
        )


def test_live_host_ram_reclamp_can_block_future_replacement() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        estimated_ram_mib_per_job=8192.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cpu",
        resources=_resources(ram_gib=128),
        policy=policy,
        gpu_sample=None,
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)

    decision = controller.observe(
        active_jobs=1,
        workload_active_jobs=1,
        cpu_sample=CpuTelemetrySample(1.0, 10.0),
        live_ram_available_bytes=1 * _GIB,
        now=1.0,
    )

    assert decision.changed
    assert decision.target_jobs == 0
    assert controller.admission_blocked_reason is not None
    assert "host-RAM" in decision.reason


def test_missing_gpu_telemetry_constructs_conservative_serial_plan() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        estimated_gpu_memory_mib_per_job=4096.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=None,
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    assert plan.uses_cuda
    assert plan.initial_jobs == 1
    assert plan.maximum_jobs == 4
    assert plan.gpu_total_bytes is None
    assert plan.gpu_memory_budget_bytes is None
    assert plan.baseline_gpu_used_bytes is None
    assert plan.baseline_gpu_utilization_percent is None
    assert plan.gpu_utilization_budget_percent == 90.0
    assert plan.estimated_gpu_bytes_per_job == int(4096.0 * _MIB)
    assert "GPU telemetry unavailable at preflight" in plan.reason
    assert "parallel expansion is disabled until live evidence is observed" in plan.reason


def test_genuine_cuda_device_unavailability_fails_preflight() -> None:
    policy = InferenceConcurrencyPolicy(estimated_gpu_memory_mib_per_job=4096.0)
    with pytest.raises(ValueError, match="CUDA device 'cuda:0' is unavailable"):
        build_inference_concurrency_plan(
            task_count=1,
            device="cuda:0",
            resources=_resources(gpu_available=False),
            policy=policy,
            gpu_sample=None,
            cpu_sample=CpuTelemetrySample(0.0, 0.0),
        )


def test_missing_telemetry_does_not_authorize_parallel_promotion() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=20.0,
        minimum_calibration_seconds=10.0,
        monitor_interval_seconds=1.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=None,
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    # No telemetry samples observed throughout the stabilization window.
    decision = controller.observe(active_jobs=1, gpu_sample=None, now=25.0)
    assert decision.target_jobs == 1
    assert controller.gpu_calibrated
    assert "no GPU telemetry sample was observed during calibration" in decision.reason
    assert "remaining in conservative serial mode" in decision.reason


def test_missing_preflight_telemetry_promotes_when_calibration_evidence_arrives() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=20.0,
        minimum_calibration_seconds=10.0,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=None,
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    decisions = []
    for second in range(1, 15):
        d = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(float(second), 2.0, 10.0),
            now=float(second),
        )
        if d.changed:
            decisions.append(d)
    assert controller.gpu_calibrated
    assert controller.target_jobs > 1
    assert any(d.changed and d.target_jobs > 1 for d in decisions)


def test_preflight_soft_vram_crossing_selects_serial_calibration_posture() -> None:
    """A one-job estimate above the fractional budget is a soft envelope, not
    physical proof that CUDA execution is impossible.

    The plan must keep the conservative one-slot calibration posture and leave
    the actual execution authoritative instead of raising a soft-fraction
    planning failure.
    """
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        estimated_gpu_memory_mib_per_job=4096.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4, device="cuda:0", resources=_resources(), policy=policy,
        gpu_sample=_gpu_sample(0.0, 20.0, 1.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    assert plan.uses_cuda
    assert plan.initial_jobs == 1
    assert plan.maximum_jobs == 4
    assert plan.gpu_memory_budget_bytes == int(24 * _GIB * 0.90)
    assert "soft VRAM admission envelope" in plan.reason
    assert "one calibration job" in plan.reason


def test_measured_one_job_vram_peak_falls_back_to_serial_not_zero() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=300.0,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)

    decision = controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(1.0, 23.0, 20.0),
        now=1.0,
    )

    # The measured peak crosses the soft VRAM envelope, so parallel expansion
    # is capped; the running job itself proves serial viability, so the target
    # floor of one applies and no terminal blocked state may be produced.
    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert controller.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "falls back to serial execution" in decision.reason


def test_live_vram_change_reclamps_future_admission() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4, stabilization_seconds=2.0,
        minimum_calibration_seconds=2.0, stability_samples=2,
        monitor_interval_seconds=1.0, observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4, device="cuda:0", resources=_resources(), policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(1.0, 3.0, 12.0), now=1.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(2.0, 3.0, 12.0), now=2.0)
    assert controller.target_jobs >= 3
    decision = controller.observe(
        active_jobs=1, gpu_sample=_gpu_sample(3.0, 18.0, 12.0), now=3.0
    )
    assert decision.changed
    assert decision.target_jobs == 2
    assert "live VRAM re-clamp" in decision.reason


def test_high_soft_vram_calibration_falls_back_to_serial_target_one() -> None:
    """A successful calibration whose projected one-job VRAM demand exceeds the
    soft fraction caps expansion at one and never blocks the queue."""
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=20.0,
        minimum_calibration_seconds=20.0,
        monitor_interval_seconds=5.0,
        stability_samples=2,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.05,
        estimated_gpu_memory_mib_per_job=22000.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    decision = None
    for second in (5.0, 10.0, 15.0, 20.0, 25.0):
        # Retained utilization samples stay low; no incremental-VRAM sample
        # crosses the activity floor, so the configured estimate is the
        # conservative VRAM fallback and it exceeds the soft fraction.
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, 1.1, 20.0),
            now=second,
        )
        if controller.gpu_calibrated:
            break

    assert decision is not None
    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "fixed projection permits 1" in decision.reason
    assert "falls back to serial execution" in decision.reason
    assert "using the configured VRAM fallback" in decision.reason


def test_high_utilization_calibration_falls_back_to_serial_target_one() -> None:
    """A successful calibration at 95-100% GPU utilization caps expansion at
    one (serial fallback) and never converts success into target zero."""
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=20.0,
        minimum_calibration_seconds=20.0,
        monitor_interval_seconds=5.0,
        stability_samples=2,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.05,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    decision = None
    for second in (5.0, 10.0, 15.0, 20.0, 25.0):
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, 3.0, 97.0),
            now=second,
        )
        if controller.gpu_calibrated:
            break

    assert decision is not None
    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert controller.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "fixed projection permits 1" in decision.reason
    assert "falls back to serial execution" in decision.reason
    # Idle serial launch remains possible: the one-slot target still admits a
    # queued job once the calibrated job has finished.
    idle = controller.observe(active_jobs=0, gpu_sample=None, now=30.0)
    assert idle.target_jobs == 1
    assert controller.admission_blocked_reason is None


def test_one_slot_cuda_ceiling_still_measures_and_keeps_serial_floor() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=1,
        stabilization_seconds=300.0,
        minimum_calibration_seconds=300.0,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=2,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    assert plan.maximum_jobs == 1
    controller = AdaptiveInferenceConcurrency(plan, policy)
    assert not controller.gpu_calibrated

    decision = controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(1.0, 23.0, 20.0),
        now=1.0,
    )

    assert not controller.gpu_calibrated
    assert decision.target_jobs == 1
    decision = controller.complete_first_cuda_job(now=2.0)
    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "fixed projection permits 1" in decision.reason


def test_one_slot_cuda_ceiling_completes_calibration_only_after_first_job() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=1,
        stabilization_seconds=300.0,
        minimum_calibration_seconds=300.0,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=2,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    decision = controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(1.0, 3.0, 12.0),
        now=1.0,
    )

    assert not controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert "complete-first-job" in decision.reason

    decision = controller.complete_first_cuda_job(now=2.0)

    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "calibration complete" in decision.reason


def test_one_slot_cuda_completion_uses_late_peak_and_keeps_serial_floor() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=1,
        stabilization_seconds=300.0,
        minimum_calibration_seconds=300.0,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=2,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.observe(
        active_jobs=1, gpu_sample=_gpu_sample(1.0, 3.0, 12.0), now=1.0
    )
    assert not controller.gpu_calibrated

    decision = controller.complete_first_cuda_job(
        gpu_sample=_gpu_sample(2.0, 23.0, 12.0), now=2.0
    )

    # The late VRAM peak crosses the soft envelope, so the maximum stays at one
    # (which it already was); it must not become terminal infeasibility.
    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "fixed projection permits 1" in decision.reason


def test_one_slot_cuda_completion_uses_configured_vram_fallback_without_samples() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=1,
        estimated_gpu_memory_mib_per_job=1024.0,
        observed_memory_growth_margin=1.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=2,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)

    decision = controller.complete_first_cuda_job(now=1.0)

    assert controller.gpu_calibrated
    assert decision.target_jobs == 1
    assert "configured VRAM fallback" in decision.reason


def test_live_external_vram_baseline_throttles_additional_admission() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=2.0,
        minimum_calibration_seconds=2.0,
        stability_samples=2,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.1,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(1.0, 3.0, 12.0), now=1.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(2.0, 3.0, 12.0), now=2.0)
    assert controller.target_jobs > 1

    decision = controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(3.0, 21.5, 12.0),
        now=3.0,
    )

    # Soft-envelope saturation: zero *additional* capacity while the active job
    # occupies the target, but the serial floor keeps the queue launchable.
    assert decision.changed
    assert decision.target_jobs == 1
    assert controller.target_jobs == 1
    assert controller.admission_blocked_reason is None
    assert "external VRAM baseline" in decision.reason
    # Repeated saturation while idle must hold the serial floor instead of
    # creating a self-deadlock.
    idle = controller.observe(
        active_jobs=0,
        gpu_sample=_gpu_sample(4.0, 21.5, 0.0),
        now=4.0,
    )
    assert idle.target_jobs == 1
    assert controller.admission_blocked_reason is None




def test_post_calibration_live_vram_saturation_cannot_deadlock_idle_queue() -> None:
    """Live aggregate VRAM above the soft ceiling with an idle queue must hold
    the serial floor instead of collapsing to a terminal zero-capacity state."""
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=2.0,
        minimum_calibration_seconds=2.0,
        stability_samples=2,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4, device="cuda:0", resources=_resources(), policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(1.0, 3.0, 12.0), now=1.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(2.0, 3.0, 12.0), now=2.0)
    assert controller.target_jobs >= 2

    decision = controller.observe(
        active_jobs=0, gpu_sample=_gpu_sample(3.0, 23.0, 0.0), now=3.0
    )

    # Live VRAM reached the ceiling with no active job: no additional capacity
    # is available, but the idle queue stays launchable at the serial floor.
    assert decision.target_jobs == 1
    assert controller.target_jobs == 1
    assert controller.admission_blocked_reason is None
    repeat = controller.observe(
        active_jobs=0, gpu_sample=_gpu_sample(4.0, 23.0, 0.0), now=4.0
    )
    assert repeat.target_jobs == 1
    assert controller.admission_blocked_reason is None


def test_post_calibration_missing_telemetry_holds_instead_of_terminal_block() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=2.0,
        minimum_calibration_seconds=2.0,
        stability_samples=2,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4, device="cuda:0", resources=_resources(), policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 0.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(1.0, 3.0, 12.0), now=1.0)
    controller.observe(active_jobs=1, gpu_sample=_gpu_sample(2.0, 3.0, 12.0), now=2.0)
    assert controller.gpu_calibrated
    assert controller.target_jobs >= 2

    decision = controller.observe(active_jobs=1, gpu_sample=None, now=3.0)

    # Missing/stale telemetry must not invent evidence for a terminal block;
    # the calibrated estimate continues to govern admission conservatively.
    assert not decision.changed
    assert controller.target_jobs >= 2
    assert controller.admission_blocked_reason is None




def test_post_calibration_gpu_utilization_spike_does_not_throttle_fixed_target() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=10.0,
        minimum_gpu_activity_fraction=0.01,
        gpu_calibration_peak_trim_fraction=0.10,
        gpu_calibration_band_fraction=0.10,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    # Ten retained samples: trim the one 70% increment and use the next
    # representative 35% increment, which permits two jobs.
    for index in range(1, 11):
        if index <= 8:
            used_gib, util = 3.0, 20.0
        elif index == 9:
            used_gib, util = 4.0, 37.0
        else:
            used_gib, util = 5.0, 72.0
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(float(index), used_gib, util),
            now=float(index),
        )
    assert controller.gpu_calibrated
    assert controller.target_jobs == 2

    # A later instantaneous 98% utilization spike is not a reason to ratchet
    # concurrency down. Resident memory remains below the hard 90% VRAM guard.
    spike = controller.observe(
        active_jobs=2,
        gpu_sample=_gpu_sample(20.0, 8.0, 98.0),
        now=20.0,
    )
    assert not spike.changed
    assert controller.target_jobs == 2
    assert "fixed single-job calibration estimate" in spike.reason
    assert spike.predicted_utilization_percent_at_target is not None
    assert spike.predicted_utilization_percent_at_target < 90.0


def test_post_calibration_hard_vram_guard_can_still_throttle() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=3,
        stabilization_seconds=2.0,
        minimum_gpu_activity_fraction=0.01,
        gpu_calibration_peak_trim_fraction=0.10,
        gpu_calibration_band_fraction=0.10,
        monitor_interval_seconds=1.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=3,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    controller.observe(
        active_jobs=1, gpu_sample=_gpu_sample(1.0, 3.0, 20.0), now=1.0
    )
    controller.observe(
        active_jobs=1, gpu_sample=_gpu_sample(2.0, 3.0, 20.0), now=2.0
    )
    assert controller.target_jobs >= 2
    controller.target_jobs = 2
    decision = controller.observe(
        active_jobs=2, gpu_sample=_gpu_sample(3.0, 22.0, 50.0), now=3.0
    )
    assert decision.changed
    assert decision.target_jobs == 1
    assert "live VRAM safety override" in decision.reason


def test_cpu_probe_scales_affinity_usage_to_smaller_effective_allocation(monkeypatch) -> None:
    samples = iter(
        (
            (1000, 800, 8),
            (1800, 1200, 8),
        )
    )
    probe = CpuTelemetryProbe(capacity_threads=4)
    monkeypatch.setattr(probe, "_read_proc_stat", lambda: next(samples))
    assert probe.sample() is None
    measured = probe.sample()
    assert measured is not None
    # Raw affinity utilization is 50%; normalized from eight visible CPUs to a
    # four-thread effective quota it is 100%.
    assert measured.utilization_percent == 100.0


def test_cuda_calibration_starts_at_launch_and_survives_zero_activity_and_job_turnover() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4,
        stabilization_seconds=30.0,
        minimum_gpu_activity_fraction=0.01,
        stability_samples=2,
        monitor_interval_seconds=5.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 1.0),
        cpu_sample=CpuTelemetrySample(0.0, 2.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)

    # Launch/setup is sampled, but near-zero activity is discarded rather than
    # pulling the average toward zero.
    for second in (5.0, 10.0):
        decision = controller.observe(
            active_jobs=1,
            workload_active_jobs=0,
            gpu_sample=_gpu_sample(second, 1.1, 1.2),
            now=second,
        )
        assert not decision.changed
        assert "retained nonzero samples: GPU=0, VRAM=0" in decision.reason

    # The first short task can finish; calibration state must survive while the
    # next task is admitted serially.
    paused = controller.observe(active_jobs=0, gpu_sample=None, now=12.0)
    assert not paused.changed
    assert not controller.gpu_calibrated

    controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(20.0, 4.0, 31.0),
        now=20.0,
    )
    decision = controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(30.0, 4.0, 31.0),
        now=30.0,
    )
    assert decision.changed
    assert controller.gpu_calibrated
    assert controller.target_jobs >= 2

def test_worker_local_workload_signal_is_explicit_early_and_idempotent() -> None:
    import threading

    from mdstats.training_data.inference_parallel import (
        inference_start_signal,
        mark_inference_workload_started,
        mark_true_inference_started,
        report_inference_worker_phase,
    )

    event = threading.Event()
    phases: list[str] = []
    assert not event.is_set()
    with inference_start_signal(event.set, phase_callback=phases.append):
        assert not event.is_set()
        report_inference_worker_phase("checking checkpoint paths")
        mark_inference_workload_started("authenticating checkpoint artifact")
        mark_inference_workload_started()
        # The historical first-forward marker remains a harmless alias.
        mark_true_inference_started()
        assert event.is_set()
    assert phases == [
        "checking checkpoint paths",
        "authenticating checkpoint artifact",
    ]












def test_default_peak_trim_uses_85_to_95_percentile_band() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=8,
        stabilization_seconds=40.0,
        minimum_calibration_seconds=40.0,
        minimum_gpu_activity_fraction=0.01,
        stability_samples=2,
        monitor_interval_seconds=2.0,
        estimated_gpu_memory_mib_per_job=512.0,
        observed_memory_growth_margin=1.0,
        observed_utilization_growth_margin=1.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=8,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0),
        cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)

    # Twenty retained samples make the default fractions exact: trim the single
    # highest point (5%), then average the next two points (10%).
    decision = None
    values = [12.0] * 17 + [42.0, 52.0, 92.0]
    memory_gib = [2.0] * 17 + [5.0, 6.0, 10.0]
    for index, (used, util) in enumerate(zip(memory_gib, values), start=1):
        second = float(index * 2)
        decision = controller.observe(
            active_jobs=1,
            gpu_sample=_gpu_sample(second, used, util),
            now=second,
        )

    assert decision is not None and controller.gpu_calibrated
    # Utilization averages the next two increments, while VRAM retains the
    # 9-GiB incremental allocation peak.
    assert controller._gpu_estimated_utilization_per_job == 45.0
    assert controller._gpu_estimated_memory_bytes_per_job == 9 * _GIB
    assert "highest 5%" in decision.reason
    assert "next 10%" in decision.reason


def test_cuda_calibration_converges_after_minimum_stable_representative_evidence() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=4, stabilization_seconds=120.0,
        minimum_calibration_seconds=20.0, calibration_stability_relative_tolerance=0.05,
        stability_samples=3, monitor_interval_seconds=5.0,
        estimated_gpu_memory_mib_per_job=512.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=4, device="cuda:0", resources=_resources(), policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 2.0), cpu_sample=CpuTelemetrySample(0.0, 3.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    for second in (5.0, 10.0, 15.0):
        decision = controller.observe(
            active_jobs=1, gpu_sample=_gpu_sample(second, 4.0, 40.0), now=second,
        )
        assert not controller.gpu_calibrated
    decision = controller.observe(
        active_jobs=1, gpu_sample=_gpu_sample(20.0, 4.0, 40.0), now=20.0,
    )
    assert controller.gpu_calibrated
    assert "calibration complete" in decision.reason











def test_cuda_calibration_ignores_missing_polls_without_resetting_fixed_clock() -> None:
    policy = InferenceConcurrencyPolicy(
        maximum_auto_jobs=3,
        stabilization_seconds=20.0,
        minimum_gpu_activity_fraction=0.01,
        stability_samples=2,
        monitor_interval_seconds=5.0,
        estimated_gpu_memory_mib_per_job=1024.0,
    )
    plan = build_inference_concurrency_plan(
        task_count=3,
        device="cuda:0",
        resources=_resources(),
        policy=policy,
        gpu_sample=_gpu_sample(0.0, 1.0, 1.0),
        cpu_sample=CpuTelemetrySample(0.0, 2.0),
    )
    controller = AdaptiveInferenceConcurrency(plan, policy)
    controller.start_calibration(now=0.0)
    controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(5.0, 4.0, 30.0),
        now=5.0,
    )
    missing = controller.observe(active_jobs=1, gpu_sample=None, now=10.0)
    assert "10/20s" in missing.reason
    decision = controller.observe(
        active_jobs=1,
        gpu_sample=_gpu_sample(20.0, 4.0, 30.0),
        now=20.0,
    )
    assert decision.changed
    assert controller.gpu_calibrated





