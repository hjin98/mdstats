"""Adaptive resource-bounded concurrency for independent MACE training jobs.

CUDA campaigns begin with exactly one process. Additional processes are
admitted one at a time only after every active process has reached sustained
optimizer/epoch work and a fixed-duration telemetry window has been averaged.
The next process must be projected to remain below both the configured VRAM
and GPU-utilization ceilings. Natural GPU-utilization fluctuation is averaged,
not treated as a reason to wait indefinitely.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import atexit
import ctypes
import math
import shutil
import subprocess
import threading
import time
from typing import Deque

from .resources import SystemResourceSnapshot

_MIB = 1024 ** 2
_GIB = 1024 ** 3


def _positive_fraction(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not (0.0 < result <= 1.0):
        raise ValueError(f"{name} must be in (0, 1].")
    return result


@dataclass(frozen=True, slots=True)
class TrainingConcurrencyPolicy:
    """Runtime-only policy for independent training-process concurrency."""

    requested_jobs: int = 0
    minimum_auto_jobs: int = 1
    maximum_auto_jobs: int = 4
    gpu_memory_fraction: float = 0.90
    gpu_utilization_fraction: float = 0.90
    estimated_gpu_memory_mib_per_job: float = 6144.0
    estimated_ram_mib_per_job: float = 8192.0
    epoch_stabilization_seconds: float = 60.0
    stability_samples: int = 12
    stability_relative_tolerance: float = 0.10
    utilization_stability_absolute_tolerance: float = 8.0
    observed_memory_growth_margin: float = 1.05
    observed_utilization_growth_margin: float = 1.05
    monitor_interval_seconds: float = 10.0

    def __post_init__(self) -> None:
        if int(self.requested_jobs) < 0:
            raise ValueError("requested_jobs must be zero (auto) or positive.")
        if int(self.minimum_auto_jobs) <= 0 or int(self.maximum_auto_jobs) <= 0:
            raise ValueError("training concurrency bounds must be positive.")
        if int(self.minimum_auto_jobs) > int(self.maximum_auto_jobs):
            raise ValueError("minimum_auto_jobs cannot exceed maximum_auto_jobs.")
        _positive_fraction(self.gpu_memory_fraction, name="gpu_memory_fraction")
        _positive_fraction(
            self.gpu_utilization_fraction, name="gpu_utilization_fraction"
        )
        if float(self.estimated_gpu_memory_mib_per_job) <= 0.0:
            raise ValueError("estimated_gpu_memory_mib_per_job must be positive.")
        if float(self.estimated_ram_mib_per_job) <= 0.0:
            raise ValueError("estimated_ram_mib_per_job must be positive.")
        if float(self.epoch_stabilization_seconds) < 0.0:
            raise ValueError("epoch_stabilization_seconds must be non-negative.")
        if int(self.stability_samples) < 2:
            raise ValueError("stability_samples must be at least two.")
        if not (0.0 <= float(self.stability_relative_tolerance) <= 1.0):
            raise ValueError("stability_relative_tolerance must be in [0, 1].")
        if float(self.utilization_stability_absolute_tolerance) < 0.0:
            raise ValueError(
                "utilization_stability_absolute_tolerance must be non-negative."
            )
        if float(self.observed_memory_growth_margin) < 1.0:
            raise ValueError("observed_memory_growth_margin must be at least one.")
        if float(self.observed_utilization_growth_margin) < 1.0:
            raise ValueError(
                "observed_utilization_growth_margin must be at least one."
            )
        if float(self.monitor_interval_seconds) <= 0.0:
            raise ValueError("monitor_interval_seconds must be positive.")


@dataclass(frozen=True, slots=True)
class GpuTelemetrySample:
    sampled_monotonic: float
    device_index: int
    utilization_percent: float
    used_bytes: int
    total_bytes: int

    @property
    def free_bytes(self) -> int:
        return max(0, self.total_bytes - self.used_bytes)

    def summary(self) -> str:
        return (
            f"GPU utilization={self.utilization_percent:.0f}%; "
            f"VRAM={self.used_bytes / _GIB:.1f}/{self.total_bytes / _GIB:.1f} GiB"
        )


def cuda_device_index(device: str) -> int:
    requested = str(device)
    if ":" in requested:
        candidate = requested.split(":", 1)[1]
        if candidate.isdigit():
            return int(candidate)
    return 0


class _NvmlUtilization(ctypes.Structure):
    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]


class _NvmlMemory(ctypes.Structure):
    _fields_ = [
        ("total", ctypes.c_ulonglong),
        ("free", ctypes.c_ulonglong),
        ("used", ctypes.c_ulonglong),
    ]


class _NvmlTelemetryBackend:
    """Lazy process-persistent libnvidia-ml wrapper with no Python dependency."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._library: ctypes.CDLL | None = None
        self._initialized = False
        self._failed = False
        self._handles: dict[int, ctypes.c_void_p] = {}

    def _ensure_initialized(self) -> bool:
        with self._lock:
            if self._initialized:
                return True
            if self._failed:
                return False
            try:
                library = ctypes.CDLL("libnvidia-ml.so.1")
                init = getattr(library, "nvmlInit_v2", None) or getattr(library, "nvmlInit")
                get_handle = (
                    getattr(library, "nvmlDeviceGetHandleByIndex_v2", None)
                    or getattr(library, "nvmlDeviceGetHandleByIndex")
                )
                if init is None or get_handle is None:
                    raise RuntimeError("required NVML symbols are unavailable")
                init.restype = ctypes.c_int
                get_handle.argtypes = [ctypes.c_uint, ctypes.POINTER(ctypes.c_void_p)]
                get_handle.restype = ctypes.c_int
                library.nvmlDeviceGetUtilizationRates.argtypes = [
                    ctypes.c_void_p, ctypes.POINTER(_NvmlUtilization)
                ]
                library.nvmlDeviceGetUtilizationRates.restype = ctypes.c_int
                library.nvmlDeviceGetMemoryInfo.argtypes = [
                    ctypes.c_void_p, ctypes.POINTER(_NvmlMemory)
                ]
                library.nvmlDeviceGetMemoryInfo.restype = ctypes.c_int
                if int(init()) != 0:
                    raise RuntimeError("nvmlInit failed")
                self._library = library
                self._initialized = True
                return True
            except Exception:
                self._failed = True
                return False

    def query(self, index: int) -> tuple[float, int, int] | None:
        if not self._ensure_initialized():
            return None
        assert self._library is not None
        with self._lock:
            try:
                handle = self._handles.get(int(index))
                if handle is None:
                    handle = ctypes.c_void_p()
                    get_handle = (
                        getattr(self._library, "nvmlDeviceGetHandleByIndex_v2", None)
                        or getattr(self._library, "nvmlDeviceGetHandleByIndex")
                    )
                    if int(get_handle(ctypes.c_uint(int(index)), ctypes.byref(handle))) != 0:
                        return None
                    self._handles[int(index)] = handle
                utilization = _NvmlUtilization()
                memory = _NvmlMemory()
                if int(
                    self._library.nvmlDeviceGetUtilizationRates(
                        handle, ctypes.byref(utilization)
                    )
                ) != 0:
                    return None
                if int(
                    self._library.nvmlDeviceGetMemoryInfo(
                        handle, ctypes.byref(memory)
                    )
                ) != 0:
                    return None
                return float(utilization.gpu), int(memory.used), int(memory.total)
            except Exception:
                return None

    def shutdown(self) -> None:
        with self._lock:
            if not self._initialized or self._library is None:
                return
            try:
                shutdown = getattr(self._library, "nvmlShutdown", None)
                if shutdown is not None:
                    shutdown()
            except Exception:
                pass
            self._initialized = False
            self._handles.clear()


_NVML_TELEMETRY = _NvmlTelemetryBackend()
atexit.register(_NVML_TELEMETRY.shutdown)


def _query_gpu_telemetry_nvml(index: int) -> GpuTelemetrySample | None:
    values = _NVML_TELEMETRY.query(index)
    if values is None:
        return None
    utilization, used_bytes, total_bytes = values
    return GpuTelemetrySample(
        sampled_monotonic=time.monotonic(),
        device_index=int(index),
        utilization_percent=float(utilization),
        used_bytes=int(used_bytes),
        total_bytes=int(total_bytes),
    )


def _query_gpu_telemetry_nvidia_smi(index: int) -> GpuTelemetrySample | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        result = subprocess.run(
            (
                "nvidia-smi",
                f"--id={index}",
                "--query-gpu=utilization.gpu,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ),
            check=False,
            capture_output=True,
            text=True,
            timeout=2.0,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return None
        utilization, used_mib, total_mib = [
            value.strip() for value in result.stdout.splitlines()[0].split(",")
        ]
        return GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=index,
            utilization_percent=float(utilization),
            used_bytes=int(float(used_mib) * _MIB),
            total_bytes=int(float(total_mib) * _MIB),
        )
    except Exception:
        return None


def query_gpu_telemetry(device: str) -> GpuTelemetrySample | None:
    """Return one GPU sample using persistent NVML, with ``nvidia-smi`` fallback.

    Direct libnvidia-ml calls avoid spawning a process on every 10-second
    scheduler poll. The fallback preserves compatibility on hosts where the
    driver library is not discoverable from the Python process.
    """

    if not str(device).startswith("cuda"):
        return None
    index = cuda_device_index(device)
    sample = _query_gpu_telemetry_nvml(index)
    if sample is not None:
        return sample
    return _query_gpu_telemetry_nvidia_smi(index)


@dataclass(frozen=True, slots=True)
class TrainingConcurrencyPlan:
    task_count: int
    device: str
    initial_jobs: int
    maximum_jobs: int
    cpu_threads_per_job: int
    loader_workers_per_job: int
    ram_budget_bytes: int | None
    estimated_ram_bytes_per_job: int
    gpu_memory_budget_bytes: int | None
    gpu_utilization_budget_percent: float | None
    baseline_gpu_used_bytes: int | None
    baseline_gpu_utilization_percent: float | None
    estimated_gpu_bytes_per_job: int | None
    auto_scaled: bool
    reason: str

    def summary(self) -> str:
        pieces = [
            f"initial={self.initial_jobs}",
            f"ceiling={self.maximum_jobs}",
            f"native CPU threads/job={self.cpu_threads_per_job}",
        ]
        if self.gpu_memory_budget_bytes is not None:
            pieces.append(f"VRAM admission ceiling={self.gpu_memory_budget_bytes / _GIB:.1f} GiB")
        if self.gpu_utilization_budget_percent is not None:
            pieces.append(
                f"GPU-utilization admission ceiling={self.gpu_utilization_budget_percent:.0f}%"
            )
        if self.estimated_gpu_bytes_per_job is not None:
            pieces.append(
                f"initial VRAM estimate/job={self.estimated_gpu_bytes_per_job / _GIB:.1f} GiB"
            )
        pieces.append(self.reason)
        return "; ".join(pieces)


def build_training_concurrency_plan(
    *,
    task_count: int,
    device: str,
    loader_workers_per_job: int,
    resources: SystemResourceSnapshot,
    policy: TrainingConcurrencyPolicy,
    gpu_sample: GpuTelemetrySample | None,
) -> TrainingConcurrencyPlan:
    """Resolve a CPU/RAM/VRAM-bounded process ceiling and one-job start."""

    tasks = max(0, int(task_count))
    loaders = max(0, int(loader_workers_per_job))
    if tasks == 0:
        return TrainingConcurrencyPlan(
            task_count=0,
            device=str(device),
            initial_jobs=0,
            maximum_jobs=0,
            cpu_threads_per_job=1,
            loader_workers_per_job=loaders,
            ram_budget_bytes=resources.ram_budget_bytes,
            estimated_ram_bytes_per_job=int(policy.estimated_ram_mib_per_job * _MIB),
            gpu_memory_budget_bytes=None,
            gpu_utilization_budget_percent=None,
            baseline_gpu_used_bytes=None,
            baseline_gpu_utilization_percent=None,
            estimated_gpu_bytes_per_job=None,
            auto_scaled=policy.requested_jobs == 0,
            reason="no pending jobs",
        )

    requested_cap = (
        int(policy.maximum_auto_jobs)
        if int(policy.requested_jobs) == 0
        else int(policy.requested_jobs)
    )
    requested_cap = max(1, min(tasks, requested_cap))

    process_cpu_cost = max(1, 1 + loaders)
    cpu_process_limit = max(1, resources.cpu_threads_budget // process_cpu_cost)

    estimated_ram = max(1, int(float(policy.estimated_ram_mib_per_job) * _MIB))
    if resources.ram_budget_bytes is None:
        ram_process_limit = tasks
    else:
        ram_process_limit = max(1, int(resources.ram_budget_bytes) // estimated_ram)

    maximum = min(requested_cap, cpu_process_limit, ram_process_limit)
    gpu_budget: int | None = None
    utilization_budget: float | None = None
    baseline_used: int | None = None
    baseline_utilization: float | None = None
    estimated_gpu: int | None = None
    cuda_measured = str(device).startswith("cuda") and gpu_sample is not None
    if cuda_measured:
        assert gpu_sample is not None
        gpu_budget = int(gpu_sample.total_bytes * float(policy.gpu_memory_fraction))
        utilization_budget = 100.0 * float(policy.gpu_utilization_fraction)
        baseline_used = int(gpu_sample.used_bytes)
        baseline_utilization = max(0.0, float(gpu_sample.utilization_percent))
        estimated_gpu = max(
            1, int(float(policy.estimated_gpu_memory_mib_per_job) * _MIB)
        )
        usable = max(0, gpu_budget - baseline_used)
        gpu_process_limit = max(1, usable // estimated_gpu)
        maximum = min(maximum, gpu_process_limit)

    maximum = max(1, min(tasks, int(maximum)))
    # CUDA always begins with one real job.  A positive requested_jobs value is
    # a ceiling, not permission to bypass phase/resource admission.
    initial = 1
    if str(device).startswith("cuda"):
        reason = (
            "CUDA starts one job and ramps one at a time after sustained epoch "
            "telemetry satisfies both VRAM and utilization projections"
        )
    else:
        reason = "CPU training remains serial"
        maximum = 1

    native_threads = max(
        1,
        resources.cpu_threads_budget // max(1, maximum * process_cpu_cost),
    )
    return TrainingConcurrencyPlan(
        task_count=tasks,
        device=str(device),
        initial_jobs=initial,
        maximum_jobs=maximum,
        cpu_threads_per_job=native_threads,
        loader_workers_per_job=loaders,
        ram_budget_bytes=resources.ram_budget_bytes,
        estimated_ram_bytes_per_job=estimated_ram,
        gpu_memory_budget_bytes=gpu_budget,
        gpu_utilization_budget_percent=utilization_budget,
        baseline_gpu_used_bytes=baseline_used,
        baseline_gpu_utilization_percent=baseline_utilization,
        estimated_gpu_bytes_per_job=estimated_gpu,
        auto_scaled=int(policy.requested_jobs) == 0,
        reason=reason,
    )


@dataclass(frozen=True, slots=True)
class ConcurrencyDecision:
    previous_target: int
    target_jobs: int
    changed: bool
    reason: str
    observed_bytes_per_job: int | None
    predicted_bytes_at_target: int | None
    predicted_utilization_percent_at_target: float | None


class AdaptiveTrainingConcurrency:
    """Ramp after a fixed true-epoch averaging window; throttle replacements."""

    def __init__(self, plan: TrainingConcurrencyPlan, policy: TrainingConcurrencyPolicy):
        self.plan = plan
        self.policy = policy
        self.target_jobs = int(plan.initial_jobs)
        now = time.monotonic()
        self.started_monotonic = now
        self.last_target_change = now
        self._epoch_ready_since: float | None = None
        averaging_samples = math.ceil(
            float(policy.epoch_stabilization_seconds)
            / float(policy.monitor_interval_seconds)
        )
        self._samples: Deque[tuple[float, int, float, int]] = deque(
            maxlen=max(
                24,
                int(policy.stability_samples) * 4,
                averaging_samples + 8,
            )
        )
        self._peak_observed_per_job = 0

    @property
    def peak_observed_bytes_per_job(self) -> int | None:
        return None if self._peak_observed_per_job <= 0 else self._peak_observed_per_job

    def _hold(
        self,
        previous: int,
        reason: str,
        observed: int | None,
        *,
        predicted_bytes: int | None = None,
        predicted_utilization: float | None = None,
    ) -> ConcurrencyDecision:
        return ConcurrencyDecision(
            previous,
            previous,
            False,
            reason,
            observed,
            predicted_bytes,
            predicted_utilization,
        )

    def observe(
        self,
        sample: GpuTelemetrySample | None,
        *,
        active_jobs: int,
        epoch_active_jobs: int,
        now: float | None = None,
    ) -> ConcurrencyDecision:
        previous = self.target_jobs
        current_time = time.monotonic() if now is None else float(now)
        if (
            sample is None
            or self.plan.gpu_memory_budget_bytes is None
            or self.plan.gpu_utilization_budget_percent is None
        ):
            self._epoch_ready_since = None
            self._samples.clear()
            return self._hold(previous, "GPU telemetry unavailable", None)

        active = max(0, int(active_jobs))
        epoch_active = max(0, int(epoch_active_jobs))
        baseline_memory = int(self.plan.baseline_gpu_used_bytes or 0)
        baseline_util = float(self.plan.baseline_gpu_utilization_percent or 0.0)
        observed: int | None = None

        all_in_true_epoch = active > 0 and epoch_active >= active
        if not all_in_true_epoch:
            self._epoch_ready_since = None
            self._samples.clear()
            return self._hold(
                previous,
                f"waiting for true epoch compute ({epoch_active}/{active} active jobs)",
                None,
            )

        if self._epoch_ready_since is None:
            self._epoch_ready_since = current_time
            self._samples.clear()

        incremental = max(0, int(sample.used_bytes) - baseline_memory)
        if active > 0:
            observed = max(1, math.ceil(incremental / active))
            self._peak_observed_per_job = max(self._peak_observed_per_job, observed)
        self._samples.append(
            (
                current_time,
                int(sample.used_bytes),
                float(sample.utilization_percent),
                active,
            )
        )

        epoch_age = current_time - self._epoch_ready_since
        if epoch_age < float(self.policy.epoch_stabilization_seconds):
            return self._hold(
                previous,
                "true epoch compute is warming up "
                f"({epoch_age:.0f}/{self.policy.epoch_stabilization_seconds:.0f}s)",
                observed,
            )

        same_level = [
            item
            for item in self._samples
            if item[3] == active and item[0] >= float(self._epoch_ready_since)
        ]
        duration_required = max(
            2,
            math.ceil(
                float(self.policy.epoch_stabilization_seconds)
                / float(self.policy.monitor_interval_seconds)
            ),
        )
        required = max(int(self.policy.stability_samples), duration_required)
        if len(same_level) < required:
            return self._hold(
                previous,
                f"averaging true-epoch telemetry ({len(same_level)}/{required} samples)",
                observed,
            )
        # Average the full fixed-duration calibration window. GPU kernels, data
        # loading, and validation naturally fluctuate; variance is not evidence
        # that the epoch has failed to stabilize. Admission depends on the
        # measured mean resource demand over the requested window.
        window = same_level
        used_values = [item[1] for item in window]
        util_values = [item[2] for item in window]
        mean_used = sum(used_values) / len(used_values)
        mean_util = sum(util_values) / len(util_values)

        memory_budget = int(self.plan.gpu_memory_budget_bytes)
        utilization_budget = float(self.plan.gpu_utilization_budget_percent)

        # Do not kill already-running work. If a newly calibrated level is
        # saturated on average, lower the replacement target so concurrency
        # falls by one when an active run finishes.
        if active > 1 and (
            mean_used >= memory_budget
            or mean_util >= utilization_budget
        ):
            self.target_jobs = min(self.target_jobs, active - 1)
            self.last_target_change = current_time
            self._epoch_ready_since = None
            self._samples.clear()
            limiting = []
            if mean_used >= memory_budget:
                limiting.append("VRAM")
            if mean_util >= utilization_budget:
                limiting.append("GPU utilization")
            return ConcurrencyDecision(
                previous,
                self.target_jobs,
                self.target_jobs != previous,
                "stable post-add saturation exceeded the "
                + " and ".join(limiting)
                + " ceiling; future replacements throttled",
                observed,
                int(mean_used),
                mean_util,
            )

        if self.target_jobs >= self.plan.maximum_jobs:
            return self._hold(previous, "configured/resource concurrency ceiling reached", observed)
        if active != self.target_jobs:
            return self._hold(previous, "holding until active jobs match the calibrated target", observed)

        candidate = min(self.plan.maximum_jobs, self.target_jobs + 1)
        stable_incremental_memory = max(0.0, mean_used - baseline_memory)
        stable_memory_per_job = max(1, math.ceil(stable_incremental_memory / active))
        memory_estimate = max(
            stable_memory_per_job,
            int(self.plan.estimated_gpu_bytes_per_job or 1),
        )
        predicted_memory = baseline_memory + math.ceil(
            candidate
            * memory_estimate
            * float(self.policy.observed_memory_growth_margin)
        )

        stable_incremental_util = max(0.0, mean_util - baseline_util)
        utilization_per_job = stable_incremental_util / active
        predicted_utilization = baseline_util + (
            candidate
            * utilization_per_job
            * float(self.policy.observed_utilization_growth_margin)
        )

        memory_safe = predicted_memory < memory_budget
        utilization_safe = predicted_utilization < utilization_budget
        if not memory_safe or not utilization_safe:
            blockers = []
            if not memory_safe:
                blockers.append(
                    f"predicted VRAM {predicted_memory / _GIB:.1f} GiB >= "
                    f"{memory_budget / _GIB:.1f} GiB"
                )
            if not utilization_safe:
                blockers.append(
                    f"predicted GPU utilization {predicted_utilization:.1f}% >= "
                    f"{utilization_budget:.1f}%"
                )
            return self._hold(
                previous,
                "next job not admitted: " + "; ".join(blockers),
                memory_estimate,
                predicted_bytes=predicted_memory,
                predicted_utilization=predicted_utilization,
            )

        self.target_jobs = candidate
        self.last_target_change = current_time
        self._epoch_ready_since = None
        self._samples.clear()
        return ConcurrencyDecision(
            previous,
            candidate,
            True,
            "fixed-window true-epoch averages project both VRAM and GPU utilization below their ceilings",
            memory_estimate,
            predicted_memory,
            predicted_utilization,
        )
