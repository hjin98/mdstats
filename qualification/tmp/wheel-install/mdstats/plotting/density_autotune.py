"""PAR-DENS6 hardware-local execution auto-tuning for density work.

The auto-tuner owns execution choices only.  It may cap field concurrency,
choose bounded work-group depth, and cap FFT worker counts from a short,
input-independent calibration.  It never changes grid shape, Gaussian/operator
identity, support semantics, density normalization, HDR levels, or cache/
scientific provenance identities.
"""

from __future__ import annotations

import functools
import hashlib
import json
import math
import os
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any, Iterator, Literal, Mapping

import numpy as np
from scipy.fft import fftn, ifftn

from .graph_errors import GraphAdapterError, GraphStyleError
from .runtime_resources import RuntimeResourceBudget

DENSITY_AUTOTUNE_POLICY_SCHEMA = "mdstats.density-autotune-policy.v1"
DENSITY_AUTOTUNE_PROFILE_SCHEMA = "mdstats.density-autotune-profile.v1"
_BASELINE_GROUP_SIZE_MULTIPLIER = 4

AutoTuneMode = Literal["auto", "off"]


def _mode(value: Any) -> AutoTuneMode:
    text = str(value).strip().lower()
    if text not in {"auto", "off"}:
        raise GraphStyleError("Density auto-tune mode must be 'auto' or 'off'.")
    return text  # type: ignore[return-value]


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


@dataclass(frozen=True, slots=True)
class DensityAutoTunePolicy:
    mode: AutoTuneMode | str = "auto"
    calibration_max_seconds: float = 1.0
    schema_version: str = DENSITY_AUTOTUNE_POLICY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_AUTOTUNE_POLICY_SCHEMA:
            raise GraphAdapterError(f"Unsupported density auto-tune policy {self.schema_version!r}.")
        object.__setattr__(self, "mode", _mode(self.mode))
        seconds = float(self.calibration_max_seconds)
        if not np.isfinite(seconds) or seconds <= 0.0:
            raise GraphStyleError("calibration_max_seconds must be finite and positive.")
        object.__setattr__(self, "calibration_max_seconds", seconds)

    @classmethod
    def from_environment(cls, environment: Mapping[str, str] | None = None) -> "DensityAutoTunePolicy":
        env = os.environ if environment is None else environment
        raw_seconds = env.get("MDSTATS_DENSITY_AUTOTUNE_CALIBRATION_SECONDS")
        return cls(
            mode=env.get("MDSTATS_DENSITY_AUTOTUNE", "auto"),
            calibration_max_seconds=(1.0 if raw_seconds is None else float(raw_seconds)),
        )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "calibration_max_seconds": self.calibration_max_seconds,
        }


@dataclass(frozen=True, slots=True)
class DensityAutoTuneProfile:
    mode: str
    max_parallel_tasks: int | None
    group_size_multiplier: int
    fft_worker_cap: int
    direct_fft_selection: str
    cpu_gpu_selection: str
    calibration_wall_seconds: float
    runtime_signature: str
    field_concurrency_selection: str = "bounded_up_to_three_fields_v1"
    group_selection: str = "par_dens3_qualified_baseline_v1"
    fft_selection: str = "calibrated_with_single_worker_guard_v1"
    fft_seconds_by_workers: Mapping[int, float] = field(default_factory=dict)
    group_seconds_by_multiplier: Mapping[int, float] = field(default_factory=dict)
    scientific_identity_includes_profile: bool = False
    schema_version: str = DENSITY_AUTOTUNE_PROFILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_AUTOTUNE_PROFILE_SCHEMA:
            raise GraphAdapterError(f"Unsupported density auto-tune profile {self.schema_version!r}.")
        if self.max_parallel_tasks is not None:
            object.__setattr__(self, "max_parallel_tasks", _positive_int(self.max_parallel_tasks, name="max_parallel_tasks"))
        object.__setattr__(self, "group_size_multiplier", _positive_int(self.group_size_multiplier, name="group_size_multiplier"))
        object.__setattr__(self, "fft_worker_cap", _positive_int(self.fft_worker_cap, name="fft_worker_cap"))
        wall = float(self.calibration_wall_seconds)
        if not np.isfinite(wall) or wall < 0.0:
            raise GraphStyleError("calibration_wall_seconds must be finite and nonnegative.")
        object.__setattr__(self, "calibration_wall_seconds", wall)
        object.__setattr__(self, "fft_seconds_by_workers", dict(self.fft_seconds_by_workers))
        object.__setattr__(self, "group_seconds_by_multiplier", dict(self.group_seconds_by_multiplier))
        if self.scientific_identity_includes_profile:
            raise GraphAdapterError("Density auto-tune profiles are execution-only by contract.")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "mode": self.mode,
            "max_parallel_tasks": self.max_parallel_tasks,
            "group_size_multiplier": self.group_size_multiplier,
            "fft_worker_cap": self.fft_worker_cap,
            "direct_fft_selection": self.direct_fft_selection,
            "cpu_gpu_selection": self.cpu_gpu_selection,
            "calibration_wall_seconds": self.calibration_wall_seconds,
            "runtime_signature": self.runtime_signature,
            "field_concurrency_selection": self.field_concurrency_selection,
            "group_selection": self.group_selection,
            "fft_selection": self.fft_selection,
            "fft_seconds_by_workers": {str(k): v for k, v in sorted(self.fft_seconds_by_workers.items())},
            "group_seconds_by_multiplier": {str(k): v for k, v in sorted(self.group_seconds_by_multiplier.items())},
            "scientific_identity_includes_profile": False,
        }


_CURRENT_PROFILE: ContextVar[DensityAutoTuneProfile | None] = ContextVar(
    "mdstats_density_autotune_profile", default=None
)


@contextmanager
def density_autotune_scope(profile: DensityAutoTuneProfile) -> Iterator[DensityAutoTuneProfile]:
    if not isinstance(profile, DensityAutoTuneProfile):
        raise TypeError("profile must be DensityAutoTuneProfile.")
    token = _CURRENT_PROFILE.set(profile)
    try:
        yield profile
    finally:
        _CURRENT_PROFILE.reset(token)


def current_density_autotune_profile() -> DensityAutoTuneProfile | None:
    return _CURRENT_PROFILE.get()


def autotuned_max_parallel_tasks() -> int | None:
    profile = current_density_autotune_profile()
    if profile is None or profile.max_parallel_tasks is None:
        return None
    return max(1, int(profile.max_parallel_tasks))


def autotuned_group_size_multiplier(*, default: int = 4) -> int:
    """Return the live chunk-depth multiplier without delaying lease growth.

    A calibration may prefer a deeper group when executor setup dominates, but
    PAR-DENS3 cooperative leases need short groups while sibling fields are
    still competing for CPU tokens.  Keep the previously qualified depth until
    the current task has reached its preferred worker allocation; only then may
    the calibrated deeper group be used.  This is execution-only and never
    changes row ownership or reduction order.
    """

    profile = current_density_autotune_profile()
    tuned = max(1, int(default if profile is None else profile.group_size_multiplier))
    if tuned <= int(default):
        return tuned
    try:
        from .density_scheduler import current_density_worker_lease

        lease = current_density_worker_lease()
    except ImportError:  # pragma: no cover - defensive import-cycle guard
        lease = None
    if lease is not None and int(lease.workers) < int(lease.resources.preferred_workers):
        return max(1, min(tuned, int(default)))
    return tuned


def autotuned_fft_worker_count(requested: int) -> int:
    requested = max(1, int(requested))
    profile = current_density_autotune_profile()
    if profile is None:
        return requested
    return max(1, min(requested, profile.fft_worker_cap))


def _runtime_signature(budget: RuntimeResourceBudget) -> str:
    snapshot = budget.snapshot
    payload = {
        "max_threads": budget.max_threads,
        "max_memory_bytes": budget.max_memory_bytes,
        "available_cpu_count": snapshot.available_cpu_count,
        "logical_cpu_count": snapshot.logical_cpu_count,
        "affinity_cpu_count": snapshot.affinity_cpu_count,
        "scheduler_cpu_count": snapshot.scheduler_cpu_count,
        "cgroup_cpu_quota": snapshot.cgroup_cpu_quota,
        "cgroup_memory_limit_bytes": snapshot.cgroup_memory_limit_bytes,
        "scheduler_memory_limit_bytes": snapshot.scheduler_memory_limit_bytes,
        "numpy": np.__version__,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _median_seconds(operation, *, repeats: int = 2) -> float:
    operation()
    values: list[float] = []
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        operation()
        elapsed = time.perf_counter() - started
        if np.isfinite(elapsed) and elapsed > 0.0:
            values.append(float(elapsed))
    return float(np.median(np.asarray(values, dtype=np.float64))) if values else math.inf


def _candidate_workers(max_threads: int) -> tuple[int, ...]:
    values = {1, max_threads}
    for value in (2, 4, 8, 16):
        if value <= max_threads:
            values.add(value)
    return tuple(sorted(values))


def _calibrate_fft_workers(max_threads: int) -> dict[int, float]:
    # 96^3 is still a sub-second local probe on the supported CPU path, but is
    # large enough to represent production density FFTs.  The former 48^3
    # probe was dominated by worker-startup noise and could incorrectly prefer
    # one worker even when real sparse-support FFT work benefited from more.
    rng = np.random.default_rng(60810)
    data = rng.random((96, 96, 96), dtype=np.float64)
    result: dict[int, float] = {}
    for workers in _candidate_workers(max_threads):
        def run() -> None:
            transformed = fftn(data, workers=workers)
            ifftn(transformed, workers=workers)
        result[workers] = _median_seconds(run, repeats=2)
    return result


def _calibrate_group_multiplier(max_threads: int) -> dict[int, float]:
    # Measure scheduler/batch overhead using GIL-releasing NumPy kernels.  The
    # chosen multiplier only changes how many independent rows are queued before
    # the next cooperative lease check; row ownership and reduction order stay
    # canonical.
    from concurrent.futures import ThreadPoolExecutor

    workers = max(1, min(max_threads, 4))
    rng = np.random.default_rng(60811)
    payloads = tuple(rng.random(4096, dtype=np.float64) for _ in range(64))

    def kernel(array: np.ndarray) -> float:
        return float(np.dot(array, array))

    result: dict[int, float] = {}
    for multiplier in (1, 2, 4, 8):
        def run() -> None:
            cursor = 0
            while cursor < len(payloads):
                rows = payloads[cursor : cursor + multiplier * workers]
                if workers == 1:
                    tuple(kernel(row) for row in rows)
                else:
                    with ThreadPoolExecutor(max_workers=workers) as pool:
                        tuple(pool.map(kernel, rows))
                cursor += len(rows)
        result[multiplier] = _median_seconds(run, repeats=2)
    return result


@functools.lru_cache(maxsize=32)
def _calibrate_cached(runtime_signature: str, max_threads: int, mode: str) -> DensityAutoTuneProfile:
    started = time.perf_counter()
    if mode == "off":
        return DensityAutoTuneProfile(
            mode="off",
            max_parallel_tasks=None,
            group_size_multiplier=4,
            fft_worker_cap=max(1, max_threads),
            direct_fft_selection="par_dens1_calibrated_time_model",
            cpu_gpu_selection="par_dens5_policy_no_autotune_override",
            calibration_wall_seconds=0.0,
            runtime_signature=runtime_signature,
        )
    fft_seconds = _calibrate_fft_workers(max_threads)
    group_seconds = _calibrate_group_multiplier(max_threads)

    # PAR-DENS3 already qualified the live task allocation as the FFT worker
    # ceiling.  PAR-DENS6 may reduce that ceiling only when the representative
    # FFT probe shows a large (>20%) win; near-ties retain the qualified path.
    # This avoids turning small timing noise into a production regression.
    best_fft_candidate = min(fft_seconds, key=lambda workers: (fft_seconds[workers], workers))
    baseline_fft_workers = max(fft_seconds)
    baseline_fft_seconds = fft_seconds[baseline_fft_workers]
    if (
        best_fft_candidate != baseline_fft_workers
        and np.isfinite(baseline_fft_seconds)
        and fft_seconds[best_fft_candidate] <= 0.80 * baseline_fft_seconds
    ):
        best_fft = best_fft_candidate
        fft_selection = "calibrated_reduction_gt20pct_gain_v1"
    else:
        best_fft = baseline_fft_workers
        fft_selection = "par_dens3_live_worker_fail_safe_v1"

    # Chunk-depth probes are retained as diagnostic hardware evidence, but the
    # production selector keeps the PAR-DENS3-qualified multiplier of four.
    # The real Na-LTA authorization workload demonstrated why: an isolated
    # executor microbenchmark cannot model cooperative lease growth between
    # concurrently running fields, and a deeper group can delay CPU-token
    # redistribution.  A future workload-aware calibrator may replace this
    # fail-safe without changing scientific identity.
    best_group = _BASELINE_GROUP_SIZE_MULTIPLIER
    group_selection = "par_dens3_qualified_baseline_after_probe_v1"
    # Field concurrency is deliberately conservative.  Three covers the common
    # Na/Si/O or cation/framework scene while leaving each field at least one
    # CPU token; the scheduler still applies aggregate memory admission.
    parallel_tasks = max(1, min(3, max_threads))
    return DensityAutoTuneProfile(
        mode="auto",
        max_parallel_tasks=parallel_tasks,
        group_size_multiplier=best_group,
        fft_worker_cap=best_fft,
        direct_fft_selection="par_dens1_calibrated_time_model",
        cpu_gpu_selection="par_dens5_transfer_vram_cost_model",
        calibration_wall_seconds=time.perf_counter() - started,
        runtime_signature=runtime_signature,
        field_concurrency_selection="bounded_up_to_three_fields_v1",
        group_selection=group_selection,
        fft_selection=fft_selection,
        fft_seconds_by_workers=fft_seconds,
        group_seconds_by_multiplier=group_seconds,
    )


def resolve_density_autotune_profile(
    budget: RuntimeResourceBudget,
    *,
    policy: DensityAutoTunePolicy | None = None,
) -> DensityAutoTuneProfile:
    if not isinstance(budget, RuntimeResourceBudget):
        raise TypeError("budget must be RuntimeResourceBudget.")
    resolved = DensityAutoTunePolicy.from_environment() if policy is None else policy
    if not isinstance(resolved, DensityAutoTunePolicy):
        raise TypeError("policy must be DensityAutoTunePolicy or None.")
    signature = _runtime_signature(budget)
    return _calibrate_cached(signature, int(budget.max_threads), str(resolved.mode))


__all__ = [
    "DENSITY_AUTOTUNE_POLICY_SCHEMA",
    "DENSITY_AUTOTUNE_PROFILE_SCHEMA",
    "DensityAutoTunePolicy",
    "DensityAutoTuneProfile",
    "autotuned_fft_worker_count",
    "autotuned_max_parallel_tasks",
    "autotuned_group_size_multiplier",
    "current_density_autotune_profile",
    "density_autotune_scope",
    "resolve_density_autotune_profile",
]
