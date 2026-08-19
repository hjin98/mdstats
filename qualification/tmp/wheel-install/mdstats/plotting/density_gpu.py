"""Optional PAR-DENS5 GPU execution for density kernels.

GPU execution is an execution backend only.  All public helpers in this module
preserve the CPU scientific operator and FP64 accumulation contract.  CUDA is
optional at runtime: mdstats has no hard torch/CuPy dependency, and every auto
path falls back to the qualified CPU implementation when CUDA is unavailable,
insufficiently provisioned, busy, or not predicted to amortize transfer/setup
cost.

The first PAR-DENS5 backend uses PyTorch CUDA when it is already available in
the environment.  At most one major density kernel owns a CUDA device at a time
inside a process.  Device admission is based on 80% of currently free VRAM,
not total board memory, so co-resident workloads remain protected.
"""

from __future__ import annotations

import math
import os
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Literal, Mapping

import numpy as np
from numpy.typing import NDArray

from .graph_errors import GraphAdapterError, GraphStyleError
from .runtime_resources import active_density_resource_budget

DENSITY_GPU_DEVICE_SCHEMA = "mdstats.density-gpu-device.v1"
DENSITY_GPU_POLICY_SCHEMA = "mdstats.density-gpu-policy.v1"
DENSITY_GPU_DECISION_SCHEMA = "mdstats.density-gpu-decision.v1"
DENSITY_GPU_REPORT_SCHEMA = "mdstats.density-gpu-report.v1"

_DEFAULT_VRAM_FRACTION = 0.80
_DEFAULT_TRANSFER_BYTES_PER_SECOND = 12.0 * 1024**3
_DEFAULT_SETUP_SECONDS = 0.003
_DEFAULT_ASSUMED_GPU_SPEEDUP = 3.0
_DEFAULT_MIN_CPU_SECONDS = 0.020

GPUSelectionMode = Literal["auto", "off", "force"]


def _fraction(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or not 0.0 < result <= 1.0:
        raise GraphStyleError(f"{name} must lie in (0, 1].")
    return result


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise GraphStyleError(f"{name} must be finite and positive.")
    return result


def _nonnegative_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise GraphStyleError(f"{name} must be finite and nonnegative.")
    return result


def _mode(value: Any) -> GPUSelectionMode:
    text = str(value).strip().lower()
    if text not in {"auto", "off", "force"}:
        raise GraphStyleError("GPU density mode must be 'auto', 'off', or 'force'.")
    return text  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class DensityGPUDevice:
    provider: str
    device_index: int
    name: str
    total_memory_bytes: int
    free_memory_bytes: int
    usable_memory_bytes: int
    memory_fraction: float = _DEFAULT_VRAM_FRACTION
    compute_capability: str | None = None
    schema_version: str = DENSITY_GPU_DEVICE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_GPU_DEVICE_SCHEMA:
            raise GraphAdapterError(f"Unsupported GPU-device schema {self.schema_version!r}.")
        if self.device_index < 0:
            raise GraphStyleError("device_index must be nonnegative.")
        if not self.provider or not self.name:
            raise GraphStyleError("GPU provider and name must be nonempty.")
        total = int(self.total_memory_bytes)
        free = int(self.free_memory_bytes)
        usable = int(self.usable_memory_bytes)
        fraction = _fraction(self.memory_fraction, name="memory_fraction")
        if total <= 0 or free < 0 or free > total or usable < 0 or usable > free:
            raise GraphStyleError("Invalid GPU memory snapshot.")
        if usable > int(math.floor(fraction * free)):
            raise GraphStyleError("usable_memory_bytes exceeds the declared VRAM fraction.")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "provider": self.provider,
            "device_index": self.device_index,
            "name": self.name,
            "total_memory_bytes": self.total_memory_bytes,
            "free_memory_bytes": self.free_memory_bytes,
            "usable_memory_bytes": self.usable_memory_bytes,
            "memory_fraction": self.memory_fraction,
            "compute_capability": self.compute_capability,
        }


@dataclass(frozen=True, slots=True)
class DensityGPUExecutionPolicy:
    mode: GPUSelectionMode | str = "auto"
    memory_fraction: float = _DEFAULT_VRAM_FRACTION
    transfer_bytes_per_second: float = _DEFAULT_TRANSFER_BYTES_PER_SECOND
    setup_seconds: float = _DEFAULT_SETUP_SECONDS
    assumed_gpu_speedup: float = _DEFAULT_ASSUMED_GPU_SPEEDUP
    min_cpu_seconds: float = _DEFAULT_MIN_CPU_SECONDS
    schema_version: str = DENSITY_GPU_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_GPU_POLICY_SCHEMA:
            raise GraphAdapterError(f"Unsupported GPU-policy schema {self.schema_version!r}.")
        object.__setattr__(self, "mode", _mode(self.mode))
        object.__setattr__(self, "memory_fraction", _fraction(self.memory_fraction, name="memory_fraction"))
        object.__setattr__(self, "transfer_bytes_per_second", _positive_float(self.transfer_bytes_per_second, name="transfer_bytes_per_second"))
        object.__setattr__(self, "setup_seconds", _nonnegative_float(self.setup_seconds, name="setup_seconds"))
        object.__setattr__(self, "assumed_gpu_speedup", _positive_float(self.assumed_gpu_speedup, name="assumed_gpu_speedup"))
        object.__setattr__(self, "min_cpu_seconds", _nonnegative_float(self.min_cpu_seconds, name="min_cpu_seconds"))

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DensityGPUExecutionPolicy":
        env = os.environ if environment is None else environment
        return cls(mode=env.get("MDSTATS_DENSITY_GPU", "auto"))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "memory_fraction": self.memory_fraction,
            "transfer_bytes_per_second": self.transfer_bytes_per_second,
            "setup_seconds": self.setup_seconds,
            "assumed_gpu_speedup": self.assumed_gpu_speedup,
            "min_cpu_seconds": self.min_cpu_seconds,
        }


@dataclass(frozen=True, slots=True)
class DensityGPUDecision:
    kernel: str
    selected: bool
    reason: str
    cpu_estimate_seconds: float
    gpu_estimate_seconds: float | None
    transfer_bytes: int
    required_vram_bytes: int
    device: DensityGPUDevice | None
    mode: str
    schema_version: str = DENSITY_GPU_DECISION_SCHEMA

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "kernel": self.kernel,
            "selected": self.selected,
            "reason": self.reason,
            "cpu_estimate_seconds": self.cpu_estimate_seconds,
            "gpu_estimate_seconds": self.gpu_estimate_seconds,
            "transfer_bytes": self.transfer_bytes,
            "required_vram_bytes": self.required_vram_bytes,
            "device": None if self.device is None else self.device.to_json_dict(),
            "mode": self.mode,
        }


@dataclass(slots=True)
class _GPUJournal:
    decisions: list[DensityGPUDecision] = field(default_factory=list)


_GPU_JOURNAL: ContextVar[_GPUJournal | None] = ContextVar("mdstats_density_gpu_journal", default=None)
_GPU_DEVICE_LOCKS: dict[tuple[str, int], threading.Lock] = {}
_GPU_DEVICE_LOCKS_GUARD = threading.Lock()


@dataclass(slots=True)
class _DensityGPUMajorJob:
    task_id: str
    device_key: tuple[str, int] | None = None
    device: DensityGPUDevice | None = None
    lock: threading.Lock | None = None
    acquired: bool = False
    denied: bool = False


_GPU_MAJOR_JOB: ContextVar[_DensityGPUMajorJob | None] = ContextVar(
    "mdstats_density_gpu_major_job", default=None
)


@contextmanager
def density_gpu_major_job_scope(task_id: str) -> Iterator[None]:
    """Hold one GPU lazily for the lifetime of a scheduled density field.

    The lock is acquired only if a kernel in the field actually passes GPU
    cost/memory admission.  Once acquired it remains owned until the field
    returns, so concurrent species/framework jobs cannot alternate tiles on the
    same device and churn VRAM.
    """

    job = _DensityGPUMajorJob(task_id=str(task_id))
    token = _GPU_MAJOR_JOB.set(job)
    try:
        yield None
    finally:
        if job.acquired and job.lock is not None:
            # Return allocator-reserved VRAM at field granularity, not between
            # individual tiles.  This keeps one species job resident while it
            # works, then avoids starving the next field or an external process.
            if job.device is not None and job.device.provider == "torch_cuda":
                torch = _load_torch_cuda()
                if torch is not None:
                    try:
                        torch.cuda.synchronize(job.device.device_index)
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
            job.lock.release()
            job.acquired = False
        _GPU_MAJOR_JOB.reset(token)


@contextmanager
def density_gpu_journal_scope() -> Iterator[_GPUJournal]:
    journal = _GPUJournal()
    token = _GPU_JOURNAL.set(journal)
    try:
        yield journal
    finally:
        _GPU_JOURNAL.reset(token)


def density_gpu_report(journal: _GPUJournal | None) -> dict[str, Any]:
    decisions = [] if journal is None else list(journal.decisions)
    selected = [item for item in decisions if item.selected]
    devices = {
        (item.device.provider, item.device.device_index): item.device
        for item in decisions
        if item.device is not None
    }
    reason_counts: dict[str, int] = {}
    kernel_counts: dict[str, int] = {}
    selected_kernel_counts: dict[str, int] = {}
    for item in decisions:
        reason_counts[item.reason] = reason_counts.get(item.reason, 0) + 1
        kernel_counts[item.kernel] = kernel_counts.get(item.kernel, 0) + 1
        if item.selected:
            selected_kernel_counts[item.kernel] = selected_kernel_counts.get(item.kernel, 0) + 1
    # Per-tile decisions can number in the thousands.  Persist bounded exemplars
    # plus complete aggregate counts rather than bloating scene provenance.
    sample = decisions[:32]
    return {
        "schema_version": DENSITY_GPU_REPORT_SCHEMA,
        "attempt_count": len(decisions),
        "gpu_selected_count": len(selected),
        "cpu_fallback_count": len(decisions) - len(selected),
        "reason_counts": reason_counts,
        "kernel_counts": kernel_counts,
        "selected_kernel_counts": selected_kernel_counts,
        "devices": [device.to_json_dict() for device in devices.values()],
        "decision_samples": [item.to_json_dict() for item in sample],
        "decision_samples_truncated": len(decisions) > len(sample),
    }


def _record(decision: DensityGPUDecision) -> None:
    journal = _GPU_JOURNAL.get()
    if journal is not None:
        journal.decisions.append(decision)


def _replace_last_with_runtime_fallback(
    decision: DensityGPUDecision, *, reason: str
) -> None:
    fallback = DensityGPUDecision(
        decision.kernel,
        False,
        reason,
        decision.cpu_estimate_seconds,
        decision.gpu_estimate_seconds,
        decision.transfer_bytes,
        decision.required_vram_bytes,
        decision.device,
        decision.mode,
    )
    journal = _GPU_JOURNAL.get()
    if journal is not None:
        for index in range(len(journal.decisions) - 1, -1, -1):
            if journal.decisions[index] == decision:
                journal.decisions[index] = fallback
                break
    job = _GPU_MAJOR_JOB.get()
    if job is not None:
        if job.acquired and job.lock is not None:
            job.lock.release()
        job.acquired = False
        job.lock = None
        job.device_key = None
        job.device = None
        job.denied = True


def _load_torch_cuda() -> Any | None:
    try:
        import torch  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        if not bool(torch.cuda.is_available()) or int(torch.cuda.device_count()) <= 0:
            return None
    except Exception:
        return None
    return torch


def discover_density_gpu(
    *,
    policy: DensityGPUExecutionPolicy | None = None,
    device_index: int = 0,
) -> DensityGPUDevice | None:
    resolved = DensityGPUExecutionPolicy.from_environment() if policy is None else policy
    if resolved.mode == "off":
        return None
    torch = _load_torch_cuda()
    if torch is None:
        return None
    try:
        free, total = torch.cuda.mem_get_info(device_index)
        props = torch.cuda.get_device_properties(device_index)
        capability = None
        major = getattr(props, "major", None)
        minor = getattr(props, "minor", None)
        if major is not None and minor is not None:
            capability = f"{int(major)}.{int(minor)}"
        usable = int(math.floor(resolved.memory_fraction * int(free)))
        return DensityGPUDevice(
            provider="torch_cuda",
            device_index=int(device_index),
            name=str(getattr(props, "name", f"cuda:{device_index}")),
            total_memory_bytes=int(total),
            free_memory_bytes=int(free),
            usable_memory_bytes=max(0, usable),
            memory_fraction=resolved.memory_fraction,
            compute_capability=capability,
        )
    except Exception:
        return None


def decide_gpu_execution(
    *,
    kernel: str,
    cpu_estimate_seconds: float,
    transfer_bytes: int,
    required_vram_bytes: int,
    policy: DensityGPUExecutionPolicy | None = None,
    device: DensityGPUDevice | None = None,
) -> DensityGPUDecision:
    resolved = DensityGPUExecutionPolicy.from_environment() if policy is None else policy
    cpu = _nonnegative_float(cpu_estimate_seconds, name="cpu_estimate_seconds")
    transfer = max(0, int(transfer_bytes))
    required = max(0, int(required_vram_bytes))
    job = _GPU_MAJOR_JOB.get()
    active_device = (
        job.device
        if device is None and job is not None and job.acquired and job.device is not None
        else (discover_density_gpu(policy=resolved) if device is None else device)
    )
    if resolved.mode == "off":
        return DensityGPUDecision(kernel, False, "gpu_disabled", cpu, None, transfer, required, active_device, resolved.mode)
    if active_device is None:
        return DensityGPUDecision(kernel, False, "cuda_unavailable", cpu, None, transfer, required, None, resolved.mode)
    host_budget = active_density_resource_budget()
    if host_budget is not None and transfer > host_budget.max_memory_bytes:
        return DensityGPUDecision(kernel, False, "host_staging_budget_exceeded", cpu, None, transfer, required, active_device, resolved.mode)
    if required > active_device.usable_memory_bytes:
        return DensityGPUDecision(kernel, False, "vram_budget_exceeded", cpu, None, transfer, required, active_device, resolved.mode)
    gpu = resolved.setup_seconds + transfer / resolved.transfer_bytes_per_second + cpu / resolved.assumed_gpu_speedup
    if resolved.mode == "force":
        return DensityGPUDecision(kernel, True, "forced_within_vram_budget", cpu, gpu, transfer, required, active_device, resolved.mode)
    if cpu < resolved.min_cpu_seconds:
        return DensityGPUDecision(kernel, False, "cpu_work_below_gpu_amortization_floor", cpu, gpu, transfer, required, active_device, resolved.mode)
    if gpu >= cpu:
        return DensityGPUDecision(kernel, False, "transfer_setup_cost_not_amortized", cpu, gpu, transfer, required, active_device, resolved.mode)
    return DensityGPUDecision(kernel, True, "predicted_gpu_wall_time_lower", cpu, gpu, transfer, required, active_device, resolved.mode)


def _device_lock(device: DensityGPUDevice) -> threading.Lock:
    key = (device.provider, device.device_index)
    with _GPU_DEVICE_LOCKS_GUARD:
        return _GPU_DEVICE_LOCKS.setdefault(key, threading.Lock())


@contextmanager
def _admitted_device(decision: DensityGPUDecision) -> Iterator[bool]:
    if not decision.selected or decision.device is None:
        _record(decision)
        yield False
        return
    lock = _device_lock(decision.device)
    job = _GPU_MAJOR_JOB.get()
    if job is not None:
        key = (decision.device.provider, decision.device.device_index)
        if job.denied:
            fallback = DensityGPUDecision(
                decision.kernel, False, "gpu_busy_single_major_job_policy",
                decision.cpu_estimate_seconds, decision.gpu_estimate_seconds,
                decision.transfer_bytes, decision.required_vram_bytes,
                decision.device, decision.mode,
            )
            _record(fallback)
            yield False
            return
        if job.acquired:
            if job.device_key != key:
                fallback = DensityGPUDecision(
                    decision.kernel, False, "major_job_bound_to_other_gpu",
                    decision.cpu_estimate_seconds, decision.gpu_estimate_seconds,
                    decision.transfer_bytes, decision.required_vram_bytes,
                    decision.device, decision.mode,
                )
                _record(fallback)
                yield False
                return
            _record(decision)
            yield True
            return
        acquired = lock.acquire(blocking=False)
        if not acquired:
            job.denied = True
            fallback = DensityGPUDecision(
                decision.kernel, False, "gpu_busy_single_major_job_policy",
                decision.cpu_estimate_seconds, decision.gpu_estimate_seconds,
                decision.transfer_bytes, decision.required_vram_bytes,
                decision.device, decision.mode,
            )
            _record(fallback)
            yield False
            return
        job.device_key = key
        job.device = decision.device
        job.lock = lock
        job.acquired = True
        _record(decision)
        yield True
        return

    # Standalone low-level calls acquire only for this kernel.  Scheduled scene
    # fields use density_gpu_major_job_scope and therefore hold across all tiles.
    acquired = lock.acquire(blocking=False)
    if not acquired:
        fallback = DensityGPUDecision(
            decision.kernel, False, "gpu_busy_single_major_job_policy",
            decision.cpu_estimate_seconds, decision.gpu_estimate_seconds,
            decision.transfer_bytes, decision.required_vram_bytes,
            decision.device, decision.mode,
        )
        _record(fallback)
        yield False
        return
    _record(decision)
    try:
        yield True
    finally:
        lock.release()


def _torch_cuda_tensor(torch: Any, array: NDArray[Any], device_index: int) -> Any:
    return torch.as_tensor(np.asarray(array), dtype=torch.float64, device=f"cuda:{device_index}")


def try_gpu_cic_deposition(
    fractional: NDArray[np.float64],
    sample_weights: NDArray[np.float64],
    shape: tuple[int, int, int],
    *,
    cpu_estimate_seconds: float,
    policy: DensityGPUExecutionPolicy | None = None,
) -> NDArray[np.float64] | None:
    """Return deterministic-order FP64 CUDA CIC deposition, or ``None``.

    Contributions are sorted by flattened target node and reduced by cumulative
    segment sums before a unique-index assignment.  This avoids concurrent
    writes to the final grid and keeps the FP64 numerical contract explicit.
    """

    frac = np.asarray(fractional, dtype=np.float64, order="C")
    weights = np.asarray(sample_weights, dtype=np.float64, order="C")
    if frac.ndim != 2 or frac.shape[1:] != (3,) or weights.shape != (frac.shape[0],):
        raise GraphAdapterError("GPU CIC requires fractional shape (n, 3) and aligned weights.")
    if any(int(v) <= 0 for v in shape):
        raise GraphAdapterError("GPU CIC shape entries must be positive.")
    n = int(frac.shape[0])
    nodes = int(np.prod(shape, dtype=object))
    # Conservative live arrays: input + base/delta + 8 target indices +
    # contributions + sorted copies + prefix/segment workspace + output.
    # Sorting/grouping keeps several O(8N) int64/float64 arrays live at once
    # (targets, contributions, permutation, sorted copies, unique/count/prefix
    # workspaces).  Keep admission intentionally conservative so the 80%-of-free
    # VRAM contract remains a protection limit rather than an optimistic estimate.
    required = int(frac.nbytes + weights.nbytes + n * 768 + nodes * 8)
    transfer = int(frac.nbytes + weights.nbytes + nodes * 8)
    decision = decide_gpu_execution(
        kernel="cic_deposition",
        cpu_estimate_seconds=cpu_estimate_seconds,
        transfer_bytes=transfer,
        required_vram_bytes=required,
        policy=policy,
    )
    with _admitted_device(decision) as admitted:
        if not admitted:
            return None
        torch = _load_torch_cuda()
        if torch is None or decision.device is None:
            _replace_last_with_runtime_fallback(decision, reason="cuda_disappeared_cpu_fallback")
            return None
        try:
            with torch.cuda.device(decision.device.device_index):
                f = _torch_cuda_tensor(torch, frac, decision.device.device_index)
                w = _torch_cuda_tensor(torch, weights, decision.device.device_index)
                scale = torch.tensor(shape, dtype=torch.float64, device=f.device)
                scaled = f * scale
                base = torch.floor(scaled).to(dtype=torch.int64)
                delta = scaled - base.to(dtype=torch.float64)
                flat_parts = []
                contribution_parts = []
                sy, sz = int(shape[1]), int(shape[2])
                for ox in (0, 1):
                    wx = (1.0 - delta[:, 0]) if ox == 0 else delta[:, 0]
                    ix = torch.remainder(base[:, 0] + ox, int(shape[0]))
                    for oy in (0, 1):
                        wy = (1.0 - delta[:, 1]) if oy == 0 else delta[:, 1]
                        iy = torch.remainder(base[:, 1] + oy, int(shape[1]))
                        for oz in (0, 1):
                            wz = (1.0 - delta[:, 2]) if oz == 0 else delta[:, 2]
                            iz = torch.remainder(base[:, 2] + oz, int(shape[2]))
                            flat_parts.append((ix * sy + iy) * sz + iz)
                            contribution_parts.append(w * wx * wy * wz)
                flat = torch.cat(flat_parts)
                contributions = torch.cat(contribution_parts)
                try:
                    order = torch.argsort(flat, stable=True)
                except TypeError:  # older torch fallback
                    order = torch.argsort(flat)
                sorted_flat = flat[order]
                sorted_values = contributions[order]
                unique, counts = torch.unique_consecutive(sorted_flat, return_counts=True)
                cumulative = torch.cumsum(sorted_values, dim=0, dtype=torch.float64)
                ends = torch.cumsum(counts, dim=0) - 1
                segment_ends = cumulative[ends]
                previous = torch.cat(
                    (
                        torch.zeros(1, dtype=torch.float64, device=f.device),
                        segment_ends[:-1],
                    )
                )
                segment_sums = segment_ends - previous
                grid = torch.zeros(nodes, dtype=torch.float64, device=f.device)
                grid[unique] = segment_sums
                torch.cuda.synchronize(decision.device.device_index)
                return grid.reshape(shape).detach().cpu().numpy().astype(np.float64, copy=False)
        except Exception:
            _replace_last_with_runtime_fallback(decision, reason="gpu_execution_failed_cpu_fallback")
            return None


def try_gpu_linear_fft_convolution(
    source: NDArray[np.float64],
    kernel: NDArray[np.float64],
    padded_shape: tuple[int, int, int],
    *,
    cpu_estimate_seconds: float,
    kernel_name: str = "linear_fft_convolution",
    policy: DensityGPUExecutionPolicy | None = None,
) -> NDArray[np.float64] | None:
    """Return FP64 CUDA linear convolution, or ``None`` for CPU fallback."""

    source_np = np.asarray(source, dtype=np.float64, order="C")
    kernel_np = np.asarray(kernel, dtype=np.float64, order="C")
    padded_nodes = int(np.prod(padded_shape, dtype=object))
    spectrum_nodes = int(padded_shape[0] * padded_shape[1] * (padded_shape[2] // 2 + 1))
    transfer = int(source_np.nbytes + kernel_np.nbytes + padded_nodes * 8)
    # Account for padded real work arrays, both spectra, the multiplied spectrum,
    # inverse-transform output, and FFT workspace headroom.  Over-estimation is
    # preferred to an OOM because GPU acceleration is optional.
    required = int(
        source_np.nbytes
        + kernel_np.nbytes
        + 4 * padded_nodes * 8
        + 4 * spectrum_nodes * 16
    )
    decision = decide_gpu_execution(
        kernel=kernel_name,
        cpu_estimate_seconds=cpu_estimate_seconds,
        transfer_bytes=transfer,
        required_vram_bytes=required,
        policy=policy,
    )
    with _admitted_device(decision) as admitted:
        if not admitted:
            return None
        torch = _load_torch_cuda()
        if torch is None or decision.device is None:
            _replace_last_with_runtime_fallback(decision, reason="cuda_disappeared_cpu_fallback")
            return None
        try:
            with torch.cuda.device(decision.device.device_index):
                src = _torch_cuda_tensor(torch, source_np, decision.device.device_index)
                ker = _torch_cuda_tensor(torch, kernel_np, decision.device.device_index)
                spectrum = torch.fft.rfftn(src, s=padded_shape)
                kernel_spectrum = torch.fft.rfftn(ker, s=padded_shape)
                spectrum = spectrum * kernel_spectrum
                result = torch.fft.irfftn(spectrum, s=padded_shape)
                torch.cuda.synchronize(decision.device.device_index)
                return result.detach().cpu().numpy().astype(np.float64, copy=False)
        except Exception:
            # Optional acceleration is never allowed to make an otherwise valid
            # CPU calculation fail.  Record the final CPU fallback, not merely
            # the earlier admission decision.
            _replace_last_with_runtime_fallback(decision, reason="gpu_execution_failed_cpu_fallback")
            return None


def try_gpu_circular_fft_convolution(
    mass: NDArray[np.float64],
    kernel: NDArray[np.float64],
    *,
    cpu_estimate_seconds: float,
    kernel_name: str = "circular_fft_convolution",
    policy: DensityGPUExecutionPolicy | None = None,
) -> NDArray[np.float64] | None:
    """Return FP64 CUDA circular convolution on equal-shaped 3-D grids."""

    mass_np = np.asarray(mass, dtype=np.float64, order="C")
    kernel_np = np.asarray(kernel, dtype=np.float64, order="C")
    if mass_np.shape != kernel_np.shape or mass_np.ndim != 3:
        raise GraphAdapterError("GPU circular convolution requires equal-shaped 3-D arrays.")
    nodes = int(mass_np.size)
    complex_nodes = int(mass_np.shape[0] * mass_np.shape[1] * (mass_np.shape[2] // 2 + 1))
    transfer = int(mass_np.nbytes + kernel_np.nbytes + mass_np.nbytes)
    # Full complex FFTs can transiently retain lhs/rhs spectra, their product,
    # and inverse output.  Include all of them plus real inputs/output.
    required = int(3 * nodes * 8 + 4 * complex_nodes * 16)
    decision = decide_gpu_execution(
        kernel=kernel_name,
        cpu_estimate_seconds=cpu_estimate_seconds,
        transfer_bytes=transfer,
        required_vram_bytes=required,
        policy=policy,
    )
    with _admitted_device(decision) as admitted:
        if not admitted:
            return None
        torch = _load_torch_cuda()
        if torch is None or decision.device is None:
            _replace_last_with_runtime_fallback(decision, reason="cuda_disappeared_cpu_fallback")
            return None
        try:
            with torch.cuda.device(decision.device.device_index):
                lhs = _torch_cuda_tensor(torch, mass_np, decision.device.device_index)
                rhs = _torch_cuda_tensor(torch, kernel_np, decision.device.device_index)
                result = torch.fft.ifftn(torch.fft.fftn(lhs) * torch.fft.fftn(rhs)).real
                torch.cuda.synchronize(decision.device.device_index)
                return result.detach().cpu().numpy().astype(np.float64, copy=False)
        except Exception:
            _replace_last_with_runtime_fallback(decision, reason="gpu_execution_failed_cpu_fallback")
            return None


def try_gpu_spectral_filter(
    mass: NDArray[np.float64],
    real_spectral_kernel: NDArray[np.float64],
    *,
    cpu_estimate_seconds: float,
    kernel_name: str = "spectral_gaussian_filter",
    policy: DensityGPUExecutionPolicy | None = None,
) -> NDArray[np.float64] | None:
    """Return FP64 CUDA inverse FFT of ``FFT(mass) * real_spectral_kernel``."""

    mass_np = np.asarray(mass, dtype=np.float64, order="C")
    kernel_np = np.asarray(real_spectral_kernel, dtype=np.float64, order="C")
    if mass_np.shape != kernel_np.shape or mass_np.ndim != 3:
        raise GraphAdapterError("GPU spectral filtering requires equal-shaped 3-D arrays.")
    nodes = int(mass_np.size)
    transfer = int(mass_np.nbytes + kernel_np.nbytes + mass_np.nbytes)
    # Retain the real input/filter/output plus FFT, product, and inverse complex
    # work arrays.  The explicit headroom keeps admission fail-safe.
    required = int((3 * nodes * 8) + (3 * nodes * 16))
    decision = decide_gpu_execution(
        kernel=kernel_name,
        cpu_estimate_seconds=cpu_estimate_seconds,
        transfer_bytes=transfer,
        required_vram_bytes=required,
        policy=policy,
    )
    with _admitted_device(decision) as admitted:
        if not admitted:
            return None
        torch = _load_torch_cuda()
        if torch is None or decision.device is None:
            _replace_last_with_runtime_fallback(decision, reason="cuda_disappeared_cpu_fallback")
            return None
        try:
            with torch.cuda.device(decision.device.device_index):
                lhs = _torch_cuda_tensor(torch, mass_np, decision.device.device_index)
                filt = _torch_cuda_tensor(torch, kernel_np, decision.device.device_index)
                result = torch.fft.ifftn(torch.fft.fftn(lhs) * filt).real
                torch.cuda.synchronize(decision.device.device_index)
                return result.detach().cpu().numpy().astype(np.float64, copy=False)
        except Exception:
            _replace_last_with_runtime_fallback(decision, reason="gpu_execution_failed_cpu_fallback")
            return None


def estimate_fft_cpu_seconds(node_count: int, *, work_units_per_second: float) -> float:
    nodes = max(1, int(node_count))
    rate = _positive_float(work_units_per_second, name="work_units_per_second")
    work = nodes * max(1.0, math.log2(max(2, nodes)))
    return work / rate


__all__ = [
    "DENSITY_GPU_DEVICE_SCHEMA",
    "DENSITY_GPU_POLICY_SCHEMA",
    "DENSITY_GPU_DECISION_SCHEMA",
    "DENSITY_GPU_REPORT_SCHEMA",
    "DensityGPUDevice",
    "DensityGPUExecutionPolicy",
    "DensityGPUDecision",
    "density_gpu_journal_scope",
    "density_gpu_major_job_scope",
    "density_gpu_report",
    "discover_density_gpu",
    "decide_gpu_execution",
    "estimate_fft_cpu_seconds",
    "try_gpu_cic_deposition",
    "try_gpu_linear_fft_convolution",
    "try_gpu_circular_fft_convolution",
    "try_gpu_spectral_filter",
]
