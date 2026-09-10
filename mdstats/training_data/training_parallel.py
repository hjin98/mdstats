"""Adaptive resource-bounded concurrency for independent MACE training jobs.

CUDA campaigns begin with exactly one process only when one process is
currently resource-admissible; zero safe admission is a valid execution state
that callers must represent rather than launch through. Additional processes
are admitted one at a time only after every active process has reached
sustained optimizer/epoch work and a fixed-duration telemetry window has been
averaged. The next process must be projected to remain below both the
configured VRAM and GPU-utilization ceilings. Natural GPU-utilization
fluctuation is averaged, not treated as a reason to wait indefinitely.

Memory safety is evaluated independently of optimizer-activity readiness and of
the current active-job count: true optimizer work is the prerequisite for
estimating scalable demand and promoting concurrency above one, never a
prerequisite for recognizing that current aggregate occupancy already exceeds
the configured envelope.

The configured VRAM fraction is therefore both the admission ceiling and the
live aggregate safety envelope. One trustworthy observation at or above it
blocks any further admission; it is rechecked once so an allocator fluctuation
cannot stop a run, and persistence into the next normal control observation with
owned work active is a hard memory hazard for the whole wave. Throttling future
replacements cannot return memory that running jobs already hold, so it remains
the response to GPU-utilization saturation only.

Live memory observability is judged on the same cadence and fails closed: while
work is active, a missing observation admits nothing, one isolated missing
observation is tolerated only after a safe one, and a second consecutive blind
observation - or any blind observation after an unsafe one - ends the wave. The
bounded transient tolerance is expressed in control observations rather than a
wall clock, so it needs no timestamp, no second monitor, and no operator knob.

This module governs TRAIN2 admission only. The evaluation/inference controller
in ``inference_parallel`` keeps its own accepted serial-floor calibration
contract.
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


class TrainingResourceError(RuntimeError):
    """Current resource facts block automatic TRAIN2 execution."""


class TrainingResourceObservabilityError(TrainingResourceError):
    """No trustworthy current accelerator-memory observation is available.

    Device availability and telemetry availability are separate facts. Without
    a current memory observation there is no basis for admitting a job, so
    automatic admission is refused instead of guessed.
    """


class TrainingAdmissionBlockedError(TrainingResourceError):
    """Pending training work exists but no job is currently admissible."""


class TrainingMemorySafetyError(TrainingResourceError):
    """Owned training stayed above the configured VRAM envelope.

    This is a resource stop taken before the device exhausts itself; it is not
    an observed CUDA out-of-memory failure.
    """


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
    # Runtime-only freshness bound for the child progress observer. This is
    # deliberately separate from the controller's telemetry cadence: a
    # legitimate optimizer step may span more than one telemetry poll.
    epoch_activity_timeout_seconds: float = 120.0

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
        if not math.isfinite(float(self.epoch_activity_timeout_seconds)) or float(
            self.epoch_activity_timeout_seconds
        ) < 0.0:
            raise ValueError(
                "epoch_activity_timeout_seconds must be finite and non-negative."
            )


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
    # How the admission baseline was observed: "telemetry" (aggregate NVML or
    # nvidia-smi), "snapshot" (current free/total device memory only, so no
    # utilization evidence exists), or "not-applicable" for non-CUDA/no-work
    # plans. An unobservable CUDA device never reaches a plan.
    gpu_memory_observation: str = "not-applicable"

    @property
    def zero_safe_admission(self) -> bool:
        """Whether pending work exists but no job is currently admissible."""

        return int(self.task_count) > 0 and int(self.maximum_jobs) <= 0

    @property
    def utilization_telemetry_available(self) -> bool:
        """Whether parallel-promotion evidence can be collected at all."""

        return self.gpu_utilization_budget_percent is not None

    def summary(self) -> str:
        pieces = [
            f"initial={self.initial_jobs}",
            f"ceiling={self.maximum_jobs}",
            f"native CPU threads/job={self.cpu_threads_per_job}",
        ]
        if self.baseline_gpu_used_bytes is not None:
            pieces.append(
                f"baseline VRAM={self.baseline_gpu_used_bytes / _GIB:.1f} GiB"
                f" ({self.gpu_memory_observation})"
            )
        if self.gpu_memory_budget_bytes is not None:
            pieces.append(f"VRAM admission ceiling={self.gpu_memory_budget_bytes / _GIB:.1f} GiB")
            headroom = max(
                0, self.gpu_memory_budget_bytes - int(self.baseline_gpu_used_bytes or 0)
            )
            pieces.append(f"VRAM headroom={headroom / _GIB:.1f} GiB")
        if self.gpu_utilization_budget_percent is not None:
            pieces.append(
                f"GPU-utilization admission ceiling={self.gpu_utilization_budget_percent:.0f}%"
            )
        elif str(self.device).startswith("cuda"):
            pieces.append("GPU-utilization telemetry=unavailable")
        if self.zero_safe_admission:
            pieces.append("zero safe admission")
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
    """Resolve a CPU/RAM/VRAM-bounded process ceiling and one-job start.

    Hard memory feasibility may legitimately resolve to zero jobs. A positive
    ``requested_jobs`` is a maximum cap, and ``minimum_auto_jobs`` means "once
    one job is feasible, do not voluntarily target less than one"; neither is
    permission to launch into an envelope that cannot hold one job.

    For CUDA the baseline comes from current aggregate telemetry when it is
    available, otherwise from the ``SystemResourceSnapshot`` current free/total
    device memory as a memory-only fallback. A CUDA device with no trustworthy
    current memory observation raises
    :class:`TrainingResourceObservabilityError` instead of guessing.
    """

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
            gpu_memory_observation="not-applicable",
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
        # Hard host-memory feasibility. Zero capacity for one training process
        # is zero safe jobs, not one manufactured job.
        ram_process_limit = int(resources.ram_budget_bytes) // estimated_ram

    maximum = min(requested_cap, cpu_process_limit, ram_process_limit)
    infeasible: list[str] = []
    if ram_process_limit <= 0:
        infeasible.append(
            f"host RAM budget holds no {estimated_ram / _GIB:.1f} GiB training process"
        )
    gpu_budget: int | None = None
    utilization_budget: float | None = None
    baseline_used: int | None = None
    baseline_utilization: float | None = None
    estimated_gpu: int | None = None
    is_cuda = str(device).startswith("cuda")
    observation = "not-applicable"
    if is_cuda:
        if gpu_sample is not None:
            observation = "telemetry"
            total_bytes = int(gpu_sample.total_bytes)
            used_bytes = int(gpu_sample.used_bytes)
            baseline_utilization = max(0.0, float(gpu_sample.utilization_percent))
            utilization_budget = 100.0 * float(policy.gpu_utilization_fraction)
        else:
            snapshot = getattr(resources, "gpu", None)
            free_bytes = getattr(snapshot, "free_bytes", None)
            snapshot_total = getattr(snapshot, "total_bytes", None)
            if (
                free_bytes is None
                or snapshot_total is None
                or int(snapshot_total) <= 0
            ):
                raise TrainingResourceObservabilityError(
                    "Automatic CUDA training admission requires a current device "
                    "memory observation; neither GPU telemetry nor the system "
                    "resource snapshot reported one "
                    f"({getattr(snapshot, 'reason', 'no GPU snapshot')})."
                )
            # Memory-only fallback: current capacity is known, but there is no
            # utilization evidence, so only conservative serial work is allowed.
            observation = "snapshot"
            total_bytes = int(snapshot_total)
            used_bytes = max(0, total_bytes - int(free_bytes))
        gpu_budget = int(total_bytes * float(policy.gpu_memory_fraction))
        baseline_used = used_bytes
        estimated_gpu = max(
            1, int(float(policy.estimated_gpu_memory_mib_per_job) * _MIB)
        )
        usable = max(0, gpu_budget - baseline_used)
        gpu_process_limit = usable // estimated_gpu
        maximum = min(maximum, gpu_process_limit)
        if gpu_process_limit <= 0:
            infeasible.append(
                f"baseline {baseline_used / _GIB:.1f} GiB plus a "
                f"{estimated_gpu / _GIB:.1f} GiB job reservation exceeds the "
                f"{gpu_budget / _GIB:.1f} GiB training VRAM envelope"
            )
        if observation == "snapshot":
            maximum = min(maximum, 1)

    maximum = max(0, min(tasks, int(maximum)))
    if not is_cuda:
        maximum = min(maximum, 1)
    # One job starts only while one job is currently admissible. A positive
    # requested_jobs value is a ceiling, not permission to bypass resource
    # admission, and zero safe admission is a valid plan.
    initial = min(1, maximum)
    if maximum <= 0:
        reason = "zero currently admissible training jobs"
        if infeasible:
            reason += ": " + "; ".join(infeasible)
    elif not is_cuda:
        reason = "CPU training remains serial"
    elif observation == "snapshot":
        reason = (
            "CUDA starts one memory-safe job from current free-memory capacity; "
            "GPU-utilization telemetry is unavailable, so no parallel promotion "
            "is authorized"
        )
    else:
        reason = (
            "CUDA starts one job while one job is resource-admissible and ramps "
            "one at a time after sustained epoch telemetry satisfies both VRAM "
            "and utilization projections"
        )

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
        gpu_memory_observation=observation,
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
    # Memory safety is reported separately from promotion readiness above:
    # whether current aggregate occupancy is inside the configured envelope
    # (``None`` when no trustworthy sample exists), and whether that condition
    # has persisted into the next normal control observation and therefore
    # requires stopping owned work before CUDA exhausts the device. The two
    # fields together name the terminal state: ``memory_hazard`` with a
    # ``False`` ``memory_safe`` is a sustained envelope violation, while
    # ``memory_hazard`` with an unknown ``memory_safe`` is sustained loss of the
    # live memory observation that owning accelerator work depends on. Child
    # liveness remains the supervisor's own ``active``/``epoch_active``
    # accounting and is deliberately not duplicated into this record.
    memory_safe: bool | None = None
    memory_hazard: bool = False


class AdaptiveTrainingConcurrency:
    """Ramp after a fixed true-epoch averaging window; throttle replacements.

    Promotion readiness and memory safety are separate judgements. True
    optimizer/epoch activity gates *estimating scalable demand*; it never gates
    recognizing that aggregate occupancy already exceeds the envelope.
    """

    def __init__(self, plan: TrainingConcurrencyPlan, policy: TrainingConcurrencyPolicy):
        self.plan = plan
        self.policy = policy
        self.target_jobs = int(plan.initial_jobs)
        now = time.monotonic()
        self.started_monotonic = now
        self.last_target_change = now
        self._epoch_ready_since: float | None = None
        # Bounded transient tolerance expressed in normal control observations
        # rather than a wall-clock debounce: each flag records that the previous
        # trustworthy/attempted sample was already unsafe or already blind.
        self._memory_unsafe = False
        self._memory_unobserved = False
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
        memory_safe: bool | None = None,
        memory_hazard: bool = False,
    ) -> ConcurrencyDecision:
        # ``target_jobs`` may already have been lowered to the live job count to
        # close admission, so the current target is reported rather than assumed
        # equal to ``previous``.
        target = self.target_jobs
        return ConcurrencyDecision(
            previous,
            target,
            target != previous,
            reason,
            observed,
            predicted_bytes,
            predicted_utilization,
            memory_safe,
            memory_hazard,
        )

    def _close_admission(self, active: int, *, confirmed: bool) -> None:
        """Admit no further TRAIN2 work from an unsafe or blind observation.

        Live work is never targeted away: with owned jobs running, the target
        falls only to the live count, and the whole wave - never an arbitrarily
        selected victim - is the cancellation unit if the condition persists.
        With nothing owned there is no wave to cancel, so the target collapses to
        zero only once the condition survives the bounded recheck, and the
        scheduler's existing idle-queue rule then reports it as the typed
        zero-safe admission failure. ``memory_safe`` on the returned decision is
        what stops the scheduler admitting during the recheck itself.
        """

        if active > 0:
            self.target_jobs = min(self.target_jobs, active)
        elif confirmed:
            self.target_jobs = 0

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
        active = max(0, int(active_jobs))
        epoch_active = max(0, int(epoch_active_jobs))
        if self.plan.gpu_memory_budget_bytes is None:
            # No envelope was ever established, so no sample can be judged
            # against one.
            self._epoch_ready_since = None
            self._memory_unsafe = False
            self._memory_unobserved = False
            self._samples.clear()
            return self._hold(previous, "GPU memory telemetry unavailable", None)

        memory_budget = int(self.plan.gpu_memory_budget_bytes)
        if sample is None:
            # A live memory observation is a precondition for continuing to own
            # accelerator work, not merely for promoting it. Admit nothing more,
            # and let a second consecutive blind control observation - or any
            # blind observation after an already unsafe one, where recovery can
            # no longer be established - end the wave.
            self._epoch_ready_since = None
            self._samples.clear()
            confirmed = self._memory_unsafe or self._memory_unobserved
            self._memory_unobserved = True
            self._close_admission(active, confirmed=confirmed)
            reason = "no trustworthy current GPU-memory observation is available"
            if confirmed and active > 0:
                reason = (
                    f"{reason} and {active} owned TRAIN2 job(s) remain active; "
                    "live memory safety can no longer be established"
                )
            return self._hold(
                previous, reason, None, memory_hazard=confirmed and active > 0
            )

        self._memory_unobserved = False
        # Hard memory safety first, on every trustworthy sample, in every child
        # phase, and at every active-job count. Initialization or validation
        # above the envelope is a memory hazard, not "waiting for true epoch
        # compute", and throttling future replacements cannot return memory that
        # already-running jobs hold.
        memory_safe = int(sample.used_bytes) < memory_budget
        if not memory_safe:
            self._epoch_ready_since = None
            self._samples.clear()
            confirmed = self._memory_unsafe
            self._memory_unsafe = True
            self._close_admission(active, confirmed=confirmed)
            terminal = confirmed and active > 0
            occupancy = (
                f"aggregate VRAM {int(sample.used_bytes) / _GIB:.1f} GiB is at or "
                f"above the {memory_budget / _GIB:.1f} GiB training envelope"
            )
            return self._hold(
                previous,
                f"{occupancy} across consecutive control observations with "
                f"{active} owned TRAIN2 job(s) active"
                if terminal
                else occupancy,
                None,
                memory_safe=False,
                memory_hazard=terminal,
            )
        self._memory_unsafe = False

        if self.plan.gpu_utilization_budget_percent is None:
            # Current memory capacity is known but no utilization evidence
            # exists, so the plan authorized conservative serial work only.
            self._epoch_ready_since = None
            self._samples.clear()
            return self._hold(
                previous,
                "GPU-utilization telemetry unavailable; parallel promotion is "
                "not authorized",
                None,
                memory_safe=memory_safe,
            )

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
                memory_safe=memory_safe,
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
                memory_safe=memory_safe,
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
                memory_safe=memory_safe,
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
                memory_safe,
                False,
            )

        if self.target_jobs >= self.plan.maximum_jobs:
            return self._hold(
                previous,
                "configured/resource concurrency ceiling reached",
                observed,
                memory_safe=memory_safe,
            )
        if active != self.target_jobs:
            return self._hold(
                previous,
                "holding until active jobs match the calibrated target",
                observed,
                memory_safe=memory_safe,
            )

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

        # Projected next-job safety is a different question from whether current
        # aggregate occupancy is inside the envelope (``memory_safe`` above).
        projected_memory_safe = predicted_memory < memory_budget
        projected_utilization_safe = predicted_utilization < utilization_budget
        if not projected_memory_safe or not projected_utilization_safe:
            blockers = []
            if not projected_memory_safe:
                blockers.append(
                    f"predicted VRAM {predicted_memory / _GIB:.1f} GiB >= "
                    f"{memory_budget / _GIB:.1f} GiB"
                )
            if not projected_utilization_safe:
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
                memory_safe=memory_safe,
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
            memory_safe,
            False,
        )
