"""Adaptive CPU/GPU concurrency for independent MLFF inference jobs.

Evaluation and bounded MD verification consist of independent model-inference
jobs. CUDA execution starts with one job, calibrates that single-job workload
for a long fixed interval while filtering near-zero GPU/VRAM observations, and
then reuses peak-safe measured per-job demand to project safe concurrency for
the remaining queue. CPU execution is bounded by the configured thread budget,
available RAM, and a projected host-utilization ceiling.
"""
from __future__ import annotations

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
import math
import os
from pathlib import Path
import time
from typing import Callable, Deque, Iterator, Sequence

from .resources import SystemResourceSnapshot
from .training_parallel import GpuTelemetrySample

_MIB = 1024 ** 2
_GIB = 1024 ** 3


_INFERENCE_START_CALLBACK: ContextVar[Callable[[], None] | None] = ContextVar(
    "mdstats_inference_start_callback",
    default=None,
)
_INFERENCE_PHASE_CALLBACK: ContextVar[Callable[[str], None] | None] = ContextVar(
    "mdstats_inference_phase_callback",
    default=None,
)
_INFERENCE_CANCELLATION_CALLBACK: ContextVar[Callable[[], bool] | None] = ContextVar(
    "mdstats_inference_cancellation_callback", default=None
)
_INFERENCE_LEASE: ContextVar[InferenceLease | None] = ContextVar(
    "mdstats_inference_lease", default=None
)


@dataclass(frozen=True, slots=True)
class InferenceLease:
    """Launch-local outer inference job/RAM envelope (orchestration state only).

    The staged evaluation pipeline owns its RAM sub-budget and grants each
    admitted inference owner a scoped lease.  The nested static-inference
    runtime authority must re-clamp its maximum model-job ceiling and live
    incremental RAM allowance against this lease instead of assuming the whole
    process-global RAM budget is available to it.

    The lease is never part of scientific, checkpoint/cache, persisted-campaign,
    or static-inference runtime-profile compatibility identity.  It only bounds
    the nested operating point for the duration of one admitted inference task.
    """

    maximum_model_jobs: int
    ram_allowance_bytes: int | None = None


@contextmanager
def inference_start_signal(
    callback: Callable[[], None],
    *,
    phase_callback: Callable[[str], None] | None = None,
    cancellation_requested: Callable[[], bool] | None = None,
    lease: InferenceLease | None = None,
) -> Iterator[None]:
    """Bind worker-local adaptive-telemetry and stage callbacks.

    The callback is triggered at the first computation-heavy operation, not
    necessarily at the first model forward pass.  Evaluation may spend most of
    its wall time hashing/loading a checkpoint, reconstructing a deployable
    model, parsing a large monitor, or transferring a model to CUDA.  Those
    stages are therefore part of the utilization sample.  Context variables
    isolate concurrent thread-pool workers without changing the public
    scientific APIs.  The historical function name is retained for backward
    compatibility.

    ``lease`` transports a launch-local outer inference RAM/job lease to the
    nested static-inference runtime authority and is cleared again when the
    worker finishes, so no lease can leak across concurrent tasks.
    """

    token: Token[Callable[[], None] | None] = _INFERENCE_START_CALLBACK.set(
        callback
    )
    phase_token: Token[Callable[[str], None] | None] = (
        _INFERENCE_PHASE_CALLBACK.set(phase_callback)
    )
    cancellation_token: Token[Callable[[], bool] | None] = (
        _INFERENCE_CANCELLATION_CALLBACK.set(cancellation_requested)
    )
    lease_token: Token[InferenceLease | None] = _INFERENCE_LEASE.set(lease)
    try:
        yield
    finally:
        _INFERENCE_LEASE.reset(lease_token)
        _INFERENCE_CANCELLATION_CALLBACK.reset(cancellation_token)
        _INFERENCE_PHASE_CALLBACK.reset(phase_token)
        _INFERENCE_START_CALLBACK.reset(token)


def current_inference_lease() -> InferenceLease | None:
    """Return the launch-local outer inference lease bound in this worker/task.

    Returns ``None`` outside a staged evaluation inference task, so ordinary
    (non-staged) static inference and dynamics retain their historical
    process-global resource semantics.
    """

    return _INFERENCE_LEASE.get()


def inference_cancellation_requested() -> bool:
    """Return the staged scheduler's shared cancellation state in this worker."""

    callback = _INFERENCE_CANCELLATION_CALLBACK.get()
    return False if callback is None else bool(callback())


def report_inference_worker_phase(phase: str) -> None:
    """Expose the active evaluation/verification stage to diagnostics."""

    callback = _INFERENCE_PHASE_CALLBACK.get()
    if callback is not None:
        callback(str(phase).strip() or "initializing")


def mark_inference_workload_started(phase: str | None = None) -> None:
    """Start admission telemetry at the first computation-heavy operation.

    Repeated calls are harmless because the bound scheduler callback is an
    idempotent event.  ``phase`` is reported first so progress output explains
    what work caused telemetry collection to begin.
    """

    if phase is not None:
        report_inference_worker_phase(phase)
    callback = _INFERENCE_START_CALLBACK.get()
    if callback is not None:
        callback()


def mark_true_inference_started() -> None:
    """Backward-compatible alias for the historical first-forward signal.

    New evaluation and verification code should call
    :func:`mark_inference_workload_started` at its first expensive operation.
    Existing callers remain safe and simply mark the workload no later than the
    first model evaluation.
    """

    mark_inference_workload_started()


def _fraction(value: float, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result) or not (0.0 < result <= 1.0):
        raise ValueError(f"{name} must be in (0, 1].")
    return result


@dataclass(frozen=True, slots=True)
class CpuTelemetrySample:
    sampled_monotonic: float
    utilization_percent: float

    def summary(self) -> str:
        return f"CPU utilization={self.utilization_percent:.1f}%"


class CpuTelemetryProbe:
    """Stateful aggregate CPU probe normalized to the effective allocation.

    Per-CPU counters are restricted to the process affinity mask when Linux
    exposes them.  If a cgroup or scheduler quota makes the effective CPU
    allocation smaller than that affinity mask, measured busy-core usage is
    scaled to the effective capacity rather than to the complete host.
    """

    def __init__(self, *, capacity_threads: int | None = None) -> None:
        try:
            affinity = tuple(sorted(int(value) for value in os.sched_getaffinity(0)))
        except (AttributeError, OSError):
            affinity = ()
        self._cpu_ids = affinity
        observed_capacity = len(affinity) or int(os.cpu_count() or 1)
        self._capacity_threads = max(
            1,
            observed_capacity
            if capacity_threads is None
            else int(capacity_threads),
        )
        self._previous: tuple[int, int, int] | None = None

    def _read_proc_stat(self) -> tuple[int, int, int] | None:
        try:
            lines = Path("/proc/stat").read_text(encoding="utf-8").splitlines()
        except OSError:
            return None
        selected = set(self._cpu_ids)
        totals: list[tuple[int, int]] = []
        for line in lines:
            fields = line.split()
            if not fields:
                continue
            name = fields[0]
            if name == "cpu":
                aggregate_fields = fields
                continue
            if not name.startswith("cpu") or not name[3:].isdigit():
                continue
            cpu_id = int(name[3:])
            if selected and cpu_id not in selected:
                continue
            try:
                values = [int(value) for value in fields[1:]]
            except ValueError:
                return None
            if len(values) < 4:
                return None
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            totals.append((sum(values), idle))
        if totals:
            return (
                sum(value[0] for value in totals),
                sum(value[1] for value in totals),
                len(totals),
            )
        try:
            values = [int(value) for value in aggregate_fields[1:]]
        except (UnboundLocalError, ValueError):
            return None
        if len(values) < 4:
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return sum(values), idle, int(os.cpu_count() or 1)

    def sample(self, *, blocking_seconds: float = 0.0) -> CpuTelemetrySample | None:
        first = self._read_proc_stat()
        if first is None:
            return None
        if self._previous is None:
            self._previous = first
            if blocking_seconds > 0.0:
                time.sleep(float(blocking_seconds))
                first = self._read_proc_stat()
                if first is None:
                    return None
            else:
                return None
        previous_total, previous_idle, _ = self._previous
        total, idle, observed_threads = first
        self._previous = first
        total_delta = total - previous_total
        idle_delta = idle - previous_idle
        if total_delta <= 0:
            return None
        raw_utilization = (
            100.0 * max(0, total_delta - max(0, idle_delta)) / total_delta
        )
        # Convert utilization of the observed affinity set into utilization of
        # the smaller effective cgroup/scheduler allocation when necessary.
        capacity_scale = max(1.0, observed_threads / self._capacity_threads)
        utilization = raw_utilization * capacity_scale
        return CpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            utilization_percent=max(0.0, min(100.0, utilization)),
        )

    def reset(self) -> None:
        """Discard prior counters so the next sample starts a fresh interval."""

        self._previous = self._read_proc_stat()


@dataclass(frozen=True, slots=True)
class InferenceConcurrencyPolicy:
    """Runtime-only resource policy shared by evaluation and verification."""

    requested_jobs: int = 0
    maximum_auto_jobs: int = 0
    cpu_utilization_fraction: float = 0.90
    gpu_memory_fraction: float = 0.90
    gpu_utilization_fraction: float = 0.90
    estimated_gpu_memory_mib_per_job: float = 4096.0
    estimated_ram_mib_per_job: float = 4096.0
    stabilization_seconds: float = 120.0
    minimum_calibration_seconds: float = 20.0
    calibration_stability_relative_tolerance: float = 0.10
    cpu_stabilization_seconds: float = 20.0
    minimum_gpu_activity_fraction: float = 0.01
    gpu_calibration_peak_trim_fraction: float = 0.05
    gpu_calibration_band_fraction: float = 0.10
    # Deprecated direct-constructor alias retained for compatibility. When set,
    # it supplies the band width used after the peak trim. Campaign TOML parsing
    # maps the historical key to gpu_calibration_band_fraction instead.
    gpu_calibration_upper_tail_fraction: float | None = None
    stability_samples: int = 3
    observed_memory_growth_margin: float = 1.05
    observed_utilization_growth_margin: float = 1.05
    monitor_interval_seconds: float = 2.0

    def __post_init__(self) -> None:
        if int(self.requested_jobs) < 0:
            raise ValueError("requested_jobs must be zero (auto) or positive.")
        if int(self.maximum_auto_jobs) < 0:
            raise ValueError("maximum_auto_jobs must be zero (unbounded) or positive.")
        _fraction(self.cpu_utilization_fraction, name="cpu_utilization_fraction")
        _fraction(self.gpu_memory_fraction, name="gpu_memory_fraction")
        _fraction(self.gpu_utilization_fraction, name="gpu_utilization_fraction")
        if float(self.estimated_gpu_memory_mib_per_job) <= 0.0:
            raise ValueError("estimated_gpu_memory_mib_per_job must be positive.")
        if float(self.estimated_ram_mib_per_job) <= 0.0:
            raise ValueError("estimated_ram_mib_per_job must be positive.")
        if float(self.stabilization_seconds) < 0.0:
            raise ValueError("stabilization_seconds must be non-negative.")
        if float(self.minimum_calibration_seconds) < 0.0:
            raise ValueError("minimum_calibration_seconds must be nonnegative.")
        if float(self.minimum_calibration_seconds) > float(self.stabilization_seconds):
            object.__setattr__(self, "minimum_calibration_seconds", float(self.stabilization_seconds))
        if not (0.0 <= float(self.calibration_stability_relative_tolerance) < 1.0):
            raise ValueError("calibration_stability_relative_tolerance must lie in [0, 1).")
        if float(self.cpu_stabilization_seconds) < 0.0:
            raise ValueError("cpu_stabilization_seconds must be non-negative.")
        minimum_activity = float(self.minimum_gpu_activity_fraction)
        if not math.isfinite(minimum_activity) or not (0.0 <= minimum_activity < 1.0):
            raise ValueError("minimum_gpu_activity_fraction must be in [0, 1).")
        peak_trim = float(self.gpu_calibration_peak_trim_fraction)
        if not math.isfinite(peak_trim) or not (0.0 <= peak_trim < 1.0):
            raise ValueError("gpu_calibration_peak_trim_fraction must be in [0, 1).")
        band = float(
            self.gpu_calibration_band_fraction
            if self.gpu_calibration_upper_tail_fraction is None
            else self.gpu_calibration_upper_tail_fraction
        )
        if not math.isfinite(band) or not (0.0 < band <= 1.0):
            raise ValueError("gpu_calibration_band_fraction must be in (0, 1].")
        if peak_trim + band > 1.0:
            raise ValueError(
                "gpu_calibration_peak_trim_fraction + gpu_calibration_band_fraction "
                "must not exceed 1."
            )
        if int(self.stability_samples) < 2:
            raise ValueError("stability_samples must be at least two.")
        if float(self.observed_memory_growth_margin) < 1.0:
            raise ValueError("observed_memory_growth_margin must be at least one.")
        if float(self.observed_utilization_growth_margin) < 1.0:
            raise ValueError("observed_utilization_growth_margin must be at least one.")
        if float(self.monitor_interval_seconds) <= 0.0:
            raise ValueError("monitor_interval_seconds must be positive.")


@dataclass(frozen=True, slots=True)
class InferenceConcurrencyPlan:
    task_count: int
    device: str
    initial_jobs: int
    maximum_jobs: int
    cpu_threads_per_job: int
    ram_budget_bytes: int | None
    ram_budget_fraction: float
    estimated_ram_bytes_per_job: int
    cpu_utilization_budget_percent: float
    baseline_cpu_utilization_percent: float | None
    estimated_cpu_utilization_per_job: float
    gpu_memory_budget_bytes: int | None
    gpu_total_bytes: int | None
    gpu_utilization_budget_percent: float | None
    baseline_gpu_used_bytes: int | None
    baseline_gpu_utilization_percent: float | None
    estimated_gpu_bytes_per_job: int | None
    reason: str

    @property
    def uses_cuda(self) -> bool:
        return str(self.device).startswith("cuda")

    def summary(self) -> str:
        pieces = [
            f"initial={self.initial_jobs}",
            f"ceiling={self.maximum_jobs}",
            f"native CPU threads/job={self.cpu_threads_per_job}",
            f"RAM budget={'unknown' if self.ram_budget_bytes is None else f'{self.ram_budget_bytes / _GIB:.1f} GiB'}",
        ]
        if self.uses_cuda:
            if self.gpu_memory_budget_bytes is not None:
                pieces.append(f"VRAM admission envelope={self.gpu_memory_budget_bytes / _GIB:.1f} GiB")
            if self.gpu_utilization_budget_percent is not None:
                pieces.append(f"GPU-utilization admission envelope={self.gpu_utilization_budget_percent:.0f}%")
        else:
            pieces.append(f"CPU-utilization admission ceiling={self.cpu_utilization_budget_percent:.0f}%")
        pieces.append(self.reason)
        return "; ".join(pieces)


def build_inference_concurrency_plan(
    *,
    task_count: int,
    device: str,
    resources: SystemResourceSnapshot,
    policy: InferenceConcurrencyPolicy,
    gpu_sample: GpuTelemetrySample | None,
    cpu_sample: CpuTelemetrySample | None,
) -> InferenceConcurrencyPlan:
    """Resolve RAM/CPU plus GPU telemetry bounded independent-job concurrency."""

    tasks = max(0, int(task_count))
    estimated_ram = max(1, int(float(policy.estimated_ram_mib_per_job) * _MIB))
    cpu_budget_percent = 100.0 * float(policy.cpu_utilization_fraction)
    baseline_cpu = None if cpu_sample is None else float(cpu_sample.utilization_percent)
    if tasks == 0:
        return InferenceConcurrencyPlan(
            task_count=0,
            device=str(device),
            initial_jobs=0,
            maximum_jobs=0,
            cpu_threads_per_job=1,
            ram_budget_bytes=resources.ram_budget_bytes,
            ram_budget_fraction=float(resources.ram_fraction),
            estimated_ram_bytes_per_job=estimated_ram,
            cpu_utilization_budget_percent=cpu_budget_percent,
            baseline_cpu_utilization_percent=baseline_cpu,
            estimated_cpu_utilization_per_job=100.0 / max(1, resources.cpu_threads_available),
            gpu_memory_budget_bytes=None,
            gpu_total_bytes=None,
            gpu_utilization_budget_percent=None,
            baseline_gpu_used_bytes=None,
            baseline_gpu_utilization_percent=None,
            estimated_gpu_bytes_per_job=None,
            reason="no pending jobs",
        )

    if int(policy.requested_jobs) > 0:
        requested_cap = int(policy.requested_jobs)
    elif int(policy.maximum_auto_jobs) > 0:
        requested_cap = int(policy.maximum_auto_jobs)
    else:
        requested_cap = tasks
    requested_cap = max(1, min(tasks, requested_cap))

    if resources.ram_budget_bytes is None:
        ram_limit = tasks
    else:
        ram_limit = int(resources.ram_budget_bytes) // estimated_ram
        if ram_limit < 1:
            raise ValueError(
                "Inference RAM admission cannot fit one job: "
                f"budget={int(resources.ram_budget_bytes)} bytes, "
                f"estimated_job={estimated_ram} bytes."
            )
    maximum = min(requested_cap, max(1, resources.cpu_threads_budget), ram_limit)
    maximum = min(tasks, maximum)
    threads_per_job = max(1, resources.cpu_threads_budget // maximum)
    estimated_cpu_per_job = 100.0 * threads_per_job / max(1, resources.cpu_threads_available)

    gpu_budget = None
    gpu_total = None
    gpu_util_budget = None
    baseline_gpu_used = None
    baseline_gpu_util = None
    estimated_gpu = None
    if str(device).startswith("cuda"):
        if not resources.gpu.available:
            raise ValueError(
                f"CUDA device {device!r} is unavailable: {resources.gpu.reason}."
            )
        estimated_gpu = max(1, int(float(policy.estimated_gpu_memory_mib_per_job) * _MIB))
        gpu_util_budget = 100.0 * float(policy.gpu_utilization_fraction)
        if gpu_sample is None:
            reason = (
                "CUDA starts one job for fixed single-job calibration; "
                "GPU telemetry unavailable at preflight, so parallel expansion is disabled until live evidence is observed"
            )
        else:
            gpu_total = int(gpu_sample.total_bytes)
            gpu_budget = int(gpu_total * float(policy.gpu_memory_fraction))
            baseline_gpu_used = int(gpu_sample.used_bytes)
            baseline_gpu_util = max(0.0, float(gpu_sample.utilization_percent))
            one_job_projection = baseline_gpu_used + math.ceil(
                estimated_gpu * float(policy.observed_memory_growth_margin)
            )
            # The fractional VRAM ceiling is a soft parallel-expansion envelope,
            # not physical device-memory proof.  A pre-calibration one-job
            # estimate crossing it therefore selects the conservative one-slot
            # calibration posture instead of rejecting the plan; the real CUDA
            # execution remains authoritative for genuine one-job infeasibility
            # (a true OOM surfaces as an execution failure).
            if one_job_projection > gpu_budget:
                reason = (
                    "estimated one-job VRAM exceeds the soft VRAM admission "
                    f"envelope (projected={one_job_projection} bytes, "
                    f"ceiling={gpu_budget} bytes); CUDA still starts one "
                    "calibration job because actual execution, not the soft "
                    "fractional envelope, is authoritative for one-job viability"
                )
            else:
                reason = (
                    "CUDA starts one job for fixed single-job GPU/VRAM calibration; "
                    f"remaining concurrency is projected below {gpu_util_budget:.0f}% ceilings from measured per-job demand"
                )
        # Do not use the configured per-job VRAM guess as a pre-calibration
        # concurrency cap. CUDA runs exactly one job until the measured
        # single-job calibration is complete; the retained VRAM samples then
        # become authoritative for remaining-job projection. The configured
        # estimate is only a fallback if no >=activity-floor VRAM sample is
        # observed during calibration.
        threads_per_job = max(1, resources.cpu_threads_budget // maximum)
        estimated_cpu_per_job = 100.0 * threads_per_job / max(1, resources.cpu_threads_available)
        initial = 1
    else:
        if baseline_cpu is None:
            initial = maximum
            reason = "CPU telemetry unavailable; using the 90%-thread and 80%-RAM bounds"
        else:
            headroom = max(0.0, cpu_budget_percent - baseline_cpu)
            projected = max(1, int(math.floor(headroom / max(estimated_cpu_per_job, 1.0e-9))))
            initial = max(1, min(maximum, projected))
            reason = f"CPU jobs are admitted under the {cpu_budget_percent:.0f}% projected host-utilization ceiling"

    return InferenceConcurrencyPlan(
        task_count=tasks,
        device=str(device),
        initial_jobs=initial,
        maximum_jobs=maximum,
        cpu_threads_per_job=threads_per_job,
        ram_budget_bytes=resources.ram_budget_bytes,
        ram_budget_fraction=float(resources.ram_fraction),
        estimated_ram_bytes_per_job=estimated_ram,
        cpu_utilization_budget_percent=cpu_budget_percent,
        baseline_cpu_utilization_percent=baseline_cpu,
        estimated_cpu_utilization_per_job=estimated_cpu_per_job,
        gpu_memory_budget_bytes=gpu_budget,
        gpu_total_bytes=gpu_total,
        gpu_utilization_budget_percent=gpu_util_budget,
        baseline_gpu_used_bytes=baseline_gpu_used,
        baseline_gpu_utilization_percent=baseline_gpu_util,
        estimated_gpu_bytes_per_job=estimated_gpu,
        reason=reason,
    )


@dataclass(frozen=True, slots=True)
class InferenceConcurrencyDecision:
    previous_target: int
    target_jobs: int
    changed: bool
    reason: str
    predicted_memory_bytes_at_target: int | None = None
    predicted_utilization_percent_at_target: float | None = None


class AdaptiveInferenceConcurrency:
    """Adaptive admission for evaluation/verification inference work.

    CUDA evaluation/verification deliberately uses a *single-job calibration*
    rather than repeatedly extrapolating short mixed-stage windows.  One job is
    kept active at a time for the configured calibration duration (300 seconds
    by default). GPU-utilization and incremental-VRAM samples below the
    configured activity floor (1% by default) are discarded independently.
    GPU-utilization samples use an upper-band estimate, while every retained VRAM
    allocation peak remains safety evidence. Future admission is re-clamped from
    live aggregate VRAM before additional jobs are launched.

    CPU execution retains the shorter workload-window controller because host
    utilization is continuous enough to estimate directly and is independently
    bounded by the 90% CPU and 80% RAM policies.
    """

    def __init__(self, plan: InferenceConcurrencyPlan, policy: InferenceConcurrencyPolicy):
        self.plan = plan
        self.policy = policy
        self.target_jobs = int(plan.initial_jobs)

        cpu_averaging_samples = math.ceil(
            float(policy.cpu_stabilization_seconds)
            / float(policy.monitor_interval_seconds)
        )
        self._samples: Deque[tuple[float, float, int, int | None]] = deque(
            maxlen=max(
                24,
                int(policy.stability_samples) * 4,
                cpu_averaging_samples + 8,
            )
        )
        self._level_started: float | None = None

        gpu_averaging_samples = math.ceil(
            float(policy.stabilization_seconds)
            / float(policy.monitor_interval_seconds)
        )
        gpu_buffer = max(64, gpu_averaging_samples + 32)
        self._gpu_util_samples: Deque[tuple[float, float]] = deque(maxlen=gpu_buffer)
        self._gpu_memory_samples: Deque[tuple[float, int]] = deque(maxlen=gpu_buffer)
        self._gpu_calibration_started: float | None = None
        # A one-job ceiling limits promotion; it is not evidence that the one
        # admitted CUDA job fits after model/provider residency is established.
        # Every CUDA plan therefore observes the first real job before allowing
        # queued replacement work to launch.
        self._gpu_calibrated = bool(not plan.uses_cuda)
        self._gpu_estimated_utilization_per_job: float | None = None
        self._gpu_estimated_memory_bytes_per_job: int | None = None
        self._gpu_calibration_samples_seen = 0
        self._gpu_total_bytes: int | None = self.plan.gpu_total_bytes
        self._gpu_memory_budget_bytes: int | None = self.plan.gpu_memory_budget_bytes
        self._admission_blocked_reason: str | None = None

    @property
    def gpu_calibrated(self) -> bool:
        return bool(self._gpu_calibrated)

    @property
    def admission_blocked_reason(self) -> str | None:
        """Actionable terminal reason when no future job is admissible."""

        return self._admission_blocked_reason

    def start_calibration(self, *, now: float | None = None) -> None:
        """Start the fixed single-job CUDA calibration clock.

        The runner calls this as soon as the first CUDA task is submitted. In
        OPT-EVAL4 evaluation this means the accelerator stage after CPU monitor
        preparation; checkpoint/model materialization, accelerator conversion,
        transfer, and inference remain inside the calibrated region. Verification
        may still include broader per-case setup. Near-zero GPU/VRAM observations
        are filtered later instead of moving the start boundary deeper into the task.
        """

        if not self.plan.uses_cuda or self._gpu_calibrated:
            return
        if self._gpu_calibration_started is None:
            self._gpu_calibration_started = (
                time.monotonic() if now is None else float(now)
            )

    def _hold(
        self,
        reason: str,
        *,
        predicted_memory: int | None = None,
        predicted_utilization: float | None = None,
    ) -> InferenceConcurrencyDecision:
        return InferenceConcurrencyDecision(
            self.target_jobs,
            self.target_jobs,
            False,
            reason,
            predicted_memory,
            predicted_utilization,
        )

    def _cuda_projection_for_jobs(self, jobs: int) -> tuple[int, float]:
        baseline_memory = int(self.plan.baseline_gpu_used_bytes or 0)
        baseline_util = float(self.plan.baseline_gpu_utilization_percent or 0.0)
        memory_per_job = max(1, int(self._gpu_estimated_memory_bytes_per_job or 1))
        util_per_job = max(0.0, float(self._gpu_estimated_utilization_per_job or 0.0))
        predicted_memory = baseline_memory + math.ceil(
            max(0, int(jobs))
            * memory_per_job
            * float(self.policy.observed_memory_growth_margin)
        )
        predicted_util = baseline_util + (
            max(0, int(jobs))
            * util_per_job
            * float(self.policy.observed_utilization_growth_margin)
        )
        return predicted_memory, predicted_util

    def _gpu_calibration_band_fraction(self) -> float:
        legacy = self.policy.gpu_calibration_upper_tail_fraction
        if legacy is not None:
            return float(legacy)
        return float(self.policy.gpu_calibration_band_fraction)

    def _trimmed_upper_band_mean(
        self, values: list[float]
    ) -> tuple[float, int, int]:
        """Return a peak-trimmed upper-band mean for bursty GPU workloads.

        Evaluation accelerator stages and verification cases are bursty workloads.
        Their very highest telemetry points are often short kernel-launch or allocation spikes and
        are a poor basis for fixed concurrency. We therefore discard the highest
        configured fraction first (5% by default), then average the next upper
        band (10% by default). With the defaults this is approximately
        the 85th--95th percentile band of retained, non-negligible samples.

        ``floor`` is used for the peak-trim count so tiny sample sets still
        contribute data; the selected band uses ``ceil`` and always contains at
        least one value.
        """

        if not values:
            raise ValueError("trimmed upper-band mean requires at least one sample")
        ordered = sorted((float(value) for value in values), reverse=True)
        trim_fraction = float(self.policy.gpu_calibration_peak_trim_fraction)
        band_fraction = self._gpu_calibration_band_fraction()
        trim_count = min(len(ordered) - 1, math.floor(len(ordered) * trim_fraction))
        band_count = max(1, math.ceil(len(ordered) * band_fraction))
        stop = min(len(ordered), trim_count + band_count)
        selected = ordered[trim_count:stop]
        if not selected:
            selected = [ordered[-1]]
        return sum(selected) / len(selected), len(selected), trim_count

    def _finish_cuda_calibration(self) -> InferenceConcurrencyDecision:
        threshold_percent = 100.0 * float(self.policy.minimum_gpu_activity_fraction)
        total_bytes = int(self._gpu_total_bytes or self.plan.gpu_total_bytes or 0)
        threshold_bytes = (
            max(
                1,
                math.ceil(
                    total_bytes * float(self.policy.minimum_gpu_activity_fraction)
                ),
            )
            if total_bytes > 0
            else 1
        )

        # GPU utilization and VRAM are filtered independently.  This is
        # important for multi-stage jobs: model loading may allocate VRAM while
        # executing few kernels, whereas short inference bursts may have high
        # utilization without materially changing resident memory.
        util_band_count = 0
        memory_band_count = 0
        util_trim_count = 0
        memory_trim_count = 0
        if self._gpu_util_samples:
            utilization_per_job, util_band_count, util_trim_count = (
                self._trimmed_upper_band_mean(
                    [value for _, value in self._gpu_util_samples]
                )
            )
        else:
            # No >=1% sample in a long calibration means GPU compute is below
            # our observable floor.  Use the floor itself rather than zero so
            # projection remains conservative and finite.
            utilization_per_job = threshold_percent

        if self._gpu_memory_samples:
            # Allocation peaks are safety evidence, not utilization noise. Keep
            # the highest observed incremental residency even when GPU
            # utilization uses a trimmed upper band for throughput projection.
            memory_per_job = max(value for _, value in self._gpu_memory_samples)
            memory_band_count = 1
        else:
            # If resident growth never crossed the activity floor, retain the
            # configured VRAM estimate as a conservative fallback.
            memory_per_job = max(
                threshold_bytes,
                int(self.plan.estimated_gpu_bytes_per_job or threshold_bytes),
            )

        self._gpu_estimated_utilization_per_job = max(
            threshold_percent,
            float(utilization_per_job),
        )
        self._gpu_estimated_memory_bytes_per_job = max(1, int(memory_per_job))
        self._gpu_calibrated = True

        memory_budget = (
            int(self._gpu_memory_budget_bytes)
            if self._gpu_memory_budget_bytes is not None
            else (
                int(self.plan.gpu_memory_budget_bytes)
                if self.plan.gpu_memory_budget_bytes is not None
                else (
                    int(total_bytes * float(self.policy.gpu_memory_fraction))
                    if total_bytes > 0
                    else None
                )
            )
        )
        util_budget = (
            float(self.plan.gpu_utilization_budget_percent)
            if self.plan.gpu_utilization_budget_percent is not None
            else 100.0 * float(self.policy.gpu_utilization_fraction)
        )
        # The completed one-slot calibration is direct evidence that serial
        # execution of this job/resource profile is viable.  Soft GPU-utilization
        # and fractional-VRAM envelopes regulate additional concurrency above
        # that serial floor; they can never reduce the target below one.
        safe_jobs = 1
        safe_memory, safe_util = self._cuda_projection_for_jobs(1)
        if (
            (self._gpu_calibration_samples_seen > 0 or self.plan.gpu_memory_budget_bytes is not None)
            and memory_budget is not None
            and util_budget is not None
        ):
            for jobs in range(2, int(self.plan.maximum_jobs) + 1):
                predicted_memory, predicted_util = self._cuda_projection_for_jobs(jobs)
                if predicted_memory < memory_budget and predicted_util < util_budget:
                    safe_jobs = jobs
                    safe_memory, safe_util = predicted_memory, predicted_util
                    continue
                break

        previous = self.target_jobs
        self.target_jobs = max(1, min(int(self.plan.maximum_jobs), safe_jobs))
        serial_fallback = (
            self.target_jobs == 1
            and int(self.plan.maximum_jobs) > 1
            and (
                memory_budget is None
                or safe_memory >= memory_budget
                or safe_util >= util_budget
            )
        )
        util_count = len(self._gpu_util_samples)
        memory_count = len(self._gpu_memory_samples)
        fallback_bits: list[str] = []
        if self._gpu_calibration_samples_seen == 0 and self.plan.gpu_memory_budget_bytes is None:
            fallback_bits.append(
                "no GPU telemetry sample was observed during calibration; remaining in conservative serial mode"
            )
        else:
            if util_count == 0:
                fallback_bits.append(
                    f"no GPU-utilization sample reached {threshold_percent:.1f}%; using the activity floor"
                )
            if memory_count == 0:
                fallback_bits.append(
                    f"no incremental-VRAM sample reached {threshold_percent:.1f}%; using the configured VRAM fallback"
                )
        fallback = "" if not fallback_bits else "; " + "; ".join(fallback_bits)
        reason = (
            "single-job calibration complete: "
            f"retained GPU-utilization samples={util_count}, VRAM samples={memory_count}; "
            f"GPU upper-band estimate discards {util_trim_count} sample(s) from the highest "
            f"{100.0 * self.policy.gpu_calibration_peak_trim_fraction:.0f}% and averages "
            f"{util_band_count} sample(s) from the next {100.0 * self._gpu_calibration_band_fraction():.0f}%; "
            f"VRAM uses the retained allocation peak from {memory_count} sample(s); "
            f"per-job estimate={self._gpu_estimated_utilization_per_job:.1f}% GPU, "
            f"{self._gpu_estimated_memory_bytes_per_job / _GIB:.2f} GiB VRAM; "
            f"fixed projection permits {self.target_jobs} concurrent job(s)"
            + fallback
        )
        if serial_fallback and (self._gpu_calibration_samples_seen > 0 or self.plan.gpu_memory_budget_bytes is not None):
            reason += (
                "; soft GPU envelope does not permit parallel expansion, so CUDA "
                "admission falls back to serial execution (target one, never zero)"
            )
        return InferenceConcurrencyDecision(
            previous,
            self.target_jobs,
            self.target_jobs != previous,
            reason,
            safe_memory,
            safe_util,
        )

    def _observe_cuda(
        self,
        *,
        active_jobs: int,
        gpu_sample: GpuTelemetrySample | None,
        now: float,
    ) -> InferenceConcurrencyDecision:
        active = max(0, int(active_jobs))
        self.start_calibration(now=now)

        if not self._gpu_calibrated:
            if active > 1:
                # This should not occur because CUDA initial_jobs is one.  Fail
                # safely by refusing further promotion rather than learning a
                # contaminated multi-job baseline.
                return self._hold(
                    "single-job calibration requires concurrency=1; holding admission"
                )
            if gpu_sample is not None and active == 1:
                self._gpu_calibration_samples_seen += 1
                if self._gpu_total_bytes is None and gpu_sample.total_bytes:
                    self._gpu_total_bytes = int(gpu_sample.total_bytes)
                    self._gpu_memory_budget_bytes = int(
                        self._gpu_total_bytes * float(self.policy.gpu_memory_fraction)
                    )
                baseline_memory = int(self.plan.baseline_gpu_used_bytes or 0)
                baseline_util = float(self.plan.baseline_gpu_utilization_percent or 0.0)
                total_bytes = int(
                    self._gpu_total_bytes or self.plan.gpu_total_bytes or gpu_sample.total_bytes or 0
                )
                threshold_percent = 100.0 * float(
                    self.policy.minimum_gpu_activity_fraction
                )
                incremental_util = max(
                    0.0,
                    float(gpu_sample.utilization_percent) - baseline_util,
                )
                incremental_memory = max(
                    0,
                    int(gpu_sample.used_bytes) - baseline_memory,
                )
                incremental_memory_percent = (
                    0.0
                    if total_bytes <= 0
                    else 100.0 * incremental_memory / total_bytes
                )
                if incremental_util >= threshold_percent:
                    self._gpu_util_samples.append((now, incremental_util))
                if incremental_memory_percent >= threshold_percent:
                    self._gpu_memory_samples.append((now, incremental_memory))
                memory_budget = (
                    int(self._gpu_memory_budget_bytes)
                    if self._gpu_memory_budget_bytes is not None
                    else (
                        int(self.plan.gpu_memory_budget_bytes)
                        if self.plan.gpu_memory_budget_bytes is not None
                        else (
                            int(total_bytes * float(self.policy.gpu_memory_fraction))
                            if total_bytes > 0
                            else 0
                        )
                    )
                )
                measured_one_job = baseline_memory + math.ceil(
                    incremental_memory
                    * float(self.policy.observed_memory_growth_margin)
                )
                # Preserve the established multi-job fail-closed guard. Only
                # one-slot plans defer classification to the job boundary.
                if (
                    int(self.plan.maximum_jobs) > 1
                    and incremental_memory > 0
                    and memory_budget > 0
                    and measured_one_job > memory_budget
                ):
                    # The measured peak crosses the soft VRAM envelope, so no
                    # further parallel expansion is admitted; the running job
                    # itself remains viable evidence, so the serial floor keeps
                    # the target at one instead of blocking the queue.
                    previous = self.target_jobs
                    self._gpu_estimated_memory_bytes_per_job = incremental_memory
                    self._gpu_estimated_utilization_per_job = max(
                        threshold_percent, incremental_util
                    )
                    self._gpu_calibrated = True
                    self.target_jobs = 1
                    reason = (
                        "measured single-job VRAM peak exceeds the configured ceiling; "
                        f"projected={measured_one_job} bytes, ceiling={memory_budget} bytes; "
                        "CUDA admission falls back to serial execution (target one, never zero)"
                    )
                    return InferenceConcurrencyDecision(
                        previous,
                        1,
                        previous != 1,
                        reason,
                        measured_one_job,
                        self._cuda_projection_for_jobs(1)[1],
                    )
                # A one-job ceiling prevents promotion, but it does not make a
                # single early sample evidence for the complete job envelope.
                # The scheduler calls ``complete_first_cuda_job`` at the first
                # task-completion boundary, after which these retained peaks can
                # safely govern replacement admission.
                if int(self.plan.maximum_jobs) == 1:
                    return self._hold(
                        "one-slot CUDA calibration retains complete-first-job telemetry "
                        "until the admitted job finishes"
                    )

            started = self._gpu_calibration_started
            age = 0.0 if started is None else max(0.0, now - started)
            sample_floor = int(self.policy.stability_samples)

            def stable(values: Sequence[float]) -> bool:
                if len(values) < sample_floor:
                    return False
                recent = tuple(float(value) for value in values[-sample_floor:])
                scale = max(max(abs(value) for value in recent), 1.0e-12)
                spread = max(recent) - min(recent)
                return spread / scale <= float(
                    self.policy.calibration_stability_relative_tolerance
                )

            sufficient = bool(
                age >= float(self.policy.minimum_calibration_seconds)
                and stable([value for _, value in self._gpu_util_samples])
                and stable([float(value) for _, value in self._gpu_memory_samples])
            )
            if not sufficient and age < float(self.policy.stabilization_seconds):
                return self._hold(
                    "single-job GPU/VRAM calibration awaiting sufficient stable evidence "
                    f"({age:.0f}/{self.policy.stabilization_seconds:.0f}s); "
                    f"retained nonzero samples: GPU={len(self._gpu_util_samples)}, "
                    f"VRAM={len(self._gpu_memory_samples)}"
                )
            return self._finish_cuda_calibration()

        # After the one-time calibration, its per-job estimate is authoritative
        # for GPU-utilization admission. Short utilization spikes are expected in
        # these multi-stage jobs and MUST NOT ratchet concurrency downward. Live
        # telemetry is retained only for the hard VRAM guard, where ignoring an
        # excursion can cause an allocation failure/OOM rather than merely high
        # device occupancy.
        if gpu_sample is not None:
            if self._gpu_total_bytes is None and gpu_sample.total_bytes:
                self._gpu_total_bytes = int(gpu_sample.total_bytes)
                self._gpu_memory_budget_bytes = int(
                    self._gpu_total_bytes * float(self.policy.gpu_memory_fraction)
                )
            total_bytes = int(
                self._gpu_total_bytes or self.plan.gpu_total_bytes or gpu_sample.total_bytes or 0
            )
            memory_budget = self._gpu_memory_budget_bytes or (
                int(self.plan.gpu_memory_budget_bytes)
                if self.plan.gpu_memory_budget_bytes is not None
                else (
                    int(total_bytes * float(self.policy.gpu_memory_fraction))
                    if total_bytes > 0
                    else None
                )
            )
            if memory_budget is not None:
                live_used = int(gpu_sample.used_bytes)
                if live_used >= memory_budget:
                    # Soft-envelope saturation: active jobs occupy the available
                    # capacity, so additional launches are throttled.  Active jobs
                    # survive the downshift and the serial floor keeps the target at
                    # one, so an idle queue can always still admit one job.
                    previous = self.target_jobs
                    self.target_jobs = max(1, active - 1)
                    return InferenceConcurrencyDecision(
                        previous,
                        self.target_jobs,
                        self.target_jobs != previous,
                        "live VRAM safety override: aggregate VRAM reached the configured "
                        "ceiling; additional CUDA launches are throttled until active "
                        "jobs drain below the concurrency target",
                        live_used,
                        self._cuda_projection_for_jobs(self.target_jobs)[1],
                    )
                per_job = max(1, int(self._gpu_estimated_memory_bytes_per_job or 1))
                margin = float(self.policy.observed_memory_growth_margin)
                estimated_external_baseline = max(
                    int(self.plan.baseline_gpu_used_bytes or 0),
                    live_used - active * per_job,
                )
                replacement_projection = estimated_external_baseline + math.ceil(
                    per_job * margin
                )
                if replacement_projection > memory_budget:
                    # Zero *additional* capacity while active jobs occupy the
                    # target is ordinary saturation; the serial floor keeps an idle
                    # queue launchable, so this soft-envelope re-clamp never sets a
                    # terminal zero-target state.
                    previous = self.target_jobs
                    self.target_jobs = max(1, active)
                    return InferenceConcurrencyDecision(
                        previous,
                        self.target_jobs,
                        self.target_jobs != previous,
                        "live external VRAM baseline leaves insufficient headroom for an "
                        f"additional calibrated inference job; projected={replacement_projection} "
                        f"bytes, ceiling={memory_budget} bytes; queued CUDA work continues "
                        "once active jobs drain below the concurrency target",
                        replacement_projection,
                        self._cuda_projection_for_jobs(1)[1],
                    )
                live_limit = max(0, active)
                for jobs in range(max(0, active), int(self.target_jobs) + 1):
                    additional = max(0, jobs - active)
                    projected_live = live_used + math.ceil(additional * per_job * margin)
                    if projected_live <= memory_budget:
                        live_limit = jobs
                        continue
                    break
                if live_limit < self.target_jobs:
                    previous = self.target_jobs
                    self.target_jobs = max(1, live_limit)
                    if self.target_jobs == previous:
                        predicted_memory, predicted_util = self._cuda_projection_for_jobs(
                            self.target_jobs
                        )
                        return self._hold(
                            "live VRAM re-clamp holds the serial floor for queued CUDA work",
                            predicted_memory=predicted_memory,
                            predicted_utilization=predicted_util,
                        )
                    return InferenceConcurrencyDecision(
                        previous,
                        live_limit,
                        True,
                        "live VRAM re-clamp reduced future admission before launching another job",
                        live_used + math.ceil(max(0, live_limit - active) * per_job * margin),
                        self._cuda_projection_for_jobs(live_limit)[1],
                    )

        predicted_memory, predicted_util = self._cuda_projection_for_jobs(
            self.target_jobs
        )
        return self._hold(
            "using fixed single-job calibration estimate for remaining jobs",
            predicted_memory=predicted_memory,
            predicted_utilization=predicted_util,
        )

    def complete_first_cuda_job(
        self,
        *,
        gpu_sample: GpuTelemetrySample | None = None,
        now: float | None = None,
    ) -> InferenceConcurrencyDecision:
        """Finalize a one-slot CUDA calibration at its first-job boundary.

        The optional final sample is deliberately processed as active work before
        finalization.  This prevents a final transient allocation from being lost
        merely because the parent scheduler has already removed the completed
        future from its active set.
        """

        if not self.plan.uses_cuda or self._gpu_calibrated:
            return self._hold("CUDA calibration is already complete or not required")
        if int(self.plan.maximum_jobs) != 1:
            return self._hold("multi-job CUDA calibration remains telemetry-window driven")
        current = time.monotonic() if now is None else float(now)
        if gpu_sample is not None:
            # Retain the final active observation without allowing the one-slot
            # path in _observe_cuda to close early.
            self._observe_cuda(active_jobs=1, gpu_sample=gpu_sample, now=current)
        return self._finish_cuda_calibration()

    def _observe_cpu(
        self,
        *,
        active_jobs: int,
        workload_active_jobs: int | None,
        inference_active_jobs: int | None,
        cpu_sample: CpuTelemetrySample | None,
        now: float,
    ) -> InferenceConcurrencyDecision:
        current = float(now)
        active = max(0, int(active_jobs))
        if active <= 0:
            self._samples.clear()
            self._level_started = None
            return self._hold("no active jobs to calibrate")

        if workload_active_jobs is not None and inference_active_jobs is not None:
            if int(workload_active_jobs) != int(inference_active_jobs):
                raise ValueError(
                    "workload_active_jobs and legacy inference_active_jobs disagree."
                )
        workload_active = (
            active
            if workload_active_jobs is None and inference_active_jobs is None
            else max(
                0,
                int(
                    workload_active_jobs
                    if workload_active_jobs is not None
                    else inference_active_jobs
                ),
            )
        )
        if workload_active < active:
            self._samples.clear()
            self._level_started = None
            return self._hold(
                "waiting for computation-heavy workload "
                f"({workload_active}/{active} active jobs)"
            )
        if cpu_sample is None:
            self._samples.clear()
            self._level_started = None
            return self._hold("CPU telemetry unavailable")

        utilization = float(cpu_sample.utilization_percent)
        if self._level_started is None or (
            self._samples and self._samples[-1][2] != active
        ):
            self._level_started = current
            self._samples.clear()
        self._samples.append((current, utilization, active, None))
        age = current - float(self._level_started)
        window_seconds = float(self.policy.cpu_stabilization_seconds)
        if age < window_seconds:
            return self._hold(
                "CPU workload telemetry warming up "
                f"({age:.0f}/{window_seconds:.0f}s)"
            )
        window_start = current - window_seconds
        same_level = [
            item
            for item in self._samples
            if item[2] == active
            and (
                window_seconds <= 0.0
                or item[0] >= max(float(self._level_started), window_start)
            )
        ]
        duration_required = max(
            2,
            math.ceil(window_seconds / float(self.policy.monitor_interval_seconds)),
        )
        required = max(int(self.policy.stability_samples), duration_required)
        if len(same_level) < required:
            return self._hold(
                "averaging CPU workload telemetry over the fixed window "
                f"({len(same_level)}/{required} samples)"
            )
        mean_util = sum(item[1] for item in same_level) / len(same_level)
        previous = self.target_jobs
        util_budget = float(self.plan.cpu_utilization_budget_percent)
        if active > 1 and mean_util >= util_budget:
            self.target_jobs = min(self.target_jobs, active - 1)
            self._samples.clear()
            self._level_started = None
            return InferenceConcurrencyDecision(
                previous,
                self.target_jobs,
                self.target_jobs != previous,
                f"measured CPU utilization exceeded {util_budget:.0f}%; future replacements throttled",
                None,
                mean_util,
            )
        if self.target_jobs >= self.plan.maximum_jobs:
            return self._hold("configured/resource concurrency ceiling reached")
        if active != self.target_jobs:
            return self._hold("holding until active jobs match the calibrated target")
        candidate = min(self.plan.maximum_jobs, self.target_jobs + 1)
        baseline = float(self.plan.baseline_cpu_utilization_percent or 0.0)
        observed_per_job = max(
            float(self.plan.estimated_cpu_utilization_per_job),
            max(0.0, mean_util - baseline) / active,
        )
        predicted_util = baseline + (
            candidate
            * observed_per_job
            * float(self.policy.observed_utilization_growth_margin)
        )
        if predicted_util >= util_budget:
            return self._hold(
                f"next inference job not admitted: projected CPU utilization {predicted_util:.1f}% >= {util_budget:.1f}%",
                predicted_utilization=predicted_util,
            )
        self.target_jobs = candidate
        self._samples.clear()
        self._level_started = None
        return InferenceConcurrencyDecision(
            previous,
            candidate,
            True,
            f"fixed-window CPU workload averages project utilization below {util_budget:.0f}%",
            None,
            predicted_util,
        )

    @property
    def gpu_calibrated(self) -> bool:
        """Whether the one-time CUDA admission calibration has completed."""

        return bool(self._gpu_calibrated)

    def observe(
        self,
        *,
        active_jobs: int,
        workload_active_jobs: int | None = None,
        inference_active_jobs: int | None = None,
        gpu_sample: GpuTelemetrySample | None = None,
        cpu_sample: CpuTelemetrySample | None = None,
        live_ram_available_bytes: int | None = None,
        now: float | None = None,
    ) -> InferenceConcurrencyDecision:
        current = time.monotonic() if now is None else float(now)
        if live_ram_available_bytes is not None:
            available = max(0, int(live_ram_available_bytes))
            estimate = max(1, int(self.plan.estimated_ram_bytes_per_job))
            active = max(0, int(active_jobs))
            future_available = available + active * estimate
            live_limit = math.floor(
                future_available * float(self.plan.ram_budget_fraction) / estimate
            )
            live_limit = min(int(self.plan.maximum_jobs), max(0, live_limit))
            if live_limit < self.target_jobs:
                previous = self.target_jobs
                self.target_jobs = live_limit
                if live_limit == 0:
                    self._admission_blocked_reason = (
                        "live host-RAM headroom cannot admit one future inference job; "
                        f"available={available} bytes, estimated_job={estimate} bytes"
                    )
                return InferenceConcurrencyDecision(
                    previous,
                    live_limit,
                    previous != live_limit,
                    self._admission_blocked_reason
                    or "live host-RAM re-clamp reduced future inference admission",
                    live_limit * estimate,
                    None,
                )
        if self.plan.uses_cuda:
            return self._observe_cuda(
                active_jobs=active_jobs,
                gpu_sample=gpu_sample,
                now=current,
            )
        return self._observe_cpu(
            active_jobs=active_jobs,
            workload_active_jobs=workload_active_jobs,
            inference_active_jobs=inference_active_jobs,
            cpu_sample=cpu_sample,
            now=current,
        )
