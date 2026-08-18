"""Runtime-derived compute budgets for density preparation and rendering.

The resource policy deliberately separates host/job discovery from user intent.
Detected CPU and memory availability are hard runtime ceilings.  The default
policy uses configurable fractions of those ceilings.  A wall-time target is
retained only for backwards-compatible metadata and cost diagnostics; it never
rejects, truncates, or times out an otherwise feasible density scene.

Linux cgroup v2 ``memory.max``, ``memory.current``, and ``cpu.max`` semantics
follow the Linux kernel control-group documentation.  Scheduler environment
variables are treated as additional upper bounds rather than as guaranteed
capacity.
"""

from __future__ import annotations

import math
import os
import resource
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

import numpy as np

from .graph_errors import GraphAdapterError, GraphStyleError

RUNTIME_RESOURCE_SNAPSHOT_SCHEMA = "mdstats.runtime-resource-snapshot.v1"
RUNTIME_RESOURCE_BUDGET_SCHEMA = "mdstats.runtime-resource-budget.v1"
DENSITY_TIME_MODEL_SCHEMA = "mdstats.density-time-model.v3"

_DEFAULT_MEMORY_FRACTION = 0.80
_DEFAULT_THREAD_FRACTION = 0.90
_DEFAULT_WALL_TIME_SECONDS = 20.0 * 60.0
_MINIMUM_MEMORY_BUDGET_BYTES = 64 * 1024**2

_ACTIVE_DENSITY_RESOURCE_BUDGET: ContextVar["RuntimeResourceBudget | None"] = ContextVar(
    "mdstats_active_density_resource_budget", default=None
)
_ACTIVE_DENSITY_TIME_MODEL: ContextVar["DensityTimeModel | None"] = ContextVar(
    "mdstats_active_density_time_model", default=None
)



def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise GraphStyleError(f"{name} must be finite and positive.")
    return result


def _fraction(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or not 0.0 < result <= 1.0:
        raise GraphStyleError(f"{name} must lie in (0, 1].")
    return result


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text().strip()
    except (OSError, UnicodeError):
        return None


def _parse_positive_int(text: str | None) -> int | None:
    if text is None:
        return None
    try:
        value = int(text.strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def parse_byte_quantity(value: str | int | None) -> int | None:
    """Parse an integer byte count or a compact IEC/SI quantity.

    Accepted suffixes are B, KB, MB, GB, TB and KiB, MiB, GiB, TiB.  Bare
    values are interpreted as bytes.  This parser is intentionally strict so a
    malformed scheduler or package override cannot silently become a tiny cap.
    """

    if value is None:
        return None
    if isinstance(value, bool):
        raise GraphStyleError("Memory quantities cannot be Boolean values.")
    if isinstance(value, (int, np.integer)):
        return _positive_int(value, name="memory quantity")
    text = str(value).strip()
    if not text:
        return None
    normalized = text.upper().replace(" ", "")
    suffixes = (
        ("TIB", 1024**4),
        ("GIB", 1024**3),
        ("MIB", 1024**2),
        ("KIB", 1024),
        ("TB", 1000**4),
        ("GB", 1000**3),
        ("MB", 1000**2),
        ("KB", 1000),
        ("B", 1),
    )
    multiplier = 1
    number = normalized
    for suffix, factor in suffixes:
        if normalized.endswith(suffix):
            number = normalized[: -len(suffix)]
            multiplier = factor
            break
    try:
        numeric = float(number)
    except ValueError as error:
        raise GraphStyleError(f"Invalid memory quantity {value!r}.") from error
    result = int(math.floor(numeric * multiplier))
    if not np.isfinite(numeric) or result <= 0:
        raise GraphStyleError(f"Invalid memory quantity {value!r}.")
    return result


def _proc_memory_available() -> int | None:
    text = _read_text(Path("/proc/meminfo"))
    if text is None:
        return None
    for line in text.splitlines():
        if line.startswith("MemAvailable:"):
            parts = line.split()
            if len(parts) >= 2:
                return int(parts[1]) * 1024
    return None


def _system_physical_memory() -> int | None:
    try:
        pages = int(os.sysconf("SC_PHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, TypeError, ValueError):
        return None
    result = pages * page_size
    return result if result > 0 else None


def _system_available_memory() -> int | None:
    """Return current host memory headroom on non-/proc platforms when possible."""

    try:
        pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
    except (AttributeError, OSError, TypeError, ValueError):
        pages = 0
        page_size = 0
    result = pages * page_size
    if result > 0:
        return result
    try:
        import psutil  # type: ignore[import-not-found]

        available = int(psutil.virtual_memory().available)
    except (ImportError, AttributeError, OSError, TypeError, ValueError):
        return None
    return available if available > 0 else None


def _proc_process_memory() -> tuple[int, int]:
    """Return current RSS and virtual-memory size in bytes when available."""

    text = _read_text(Path("/proc/self/statm"))
    page_size = int(os.sysconf("SC_PAGE_SIZE")) if hasattr(os, "sysconf") else 4096
    if text:
        fields = text.split()
        if len(fields) >= 2:
            try:
                return int(fields[1]) * page_size, int(fields[0]) * page_size
            except ValueError:
                pass
    usage = resource.getrusage(resource.RUSAGE_SELF)
    rss = int(usage.ru_maxrss)
    if sys.platform == "darwin":  # pragma: no cover - Linux validation host
        return rss, rss
    return rss * 1024, rss * 1024


def _cgroup_v2_directory() -> Path | None:
    text = _read_text(Path("/proc/self/cgroup"))
    if text is None:
        return None
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) == 3 and parts[0] == "0" and parts[1] == "":
            relative = parts[2].lstrip("/")
            return Path("/sys/fs/cgroup") / relative
    return None


def _cgroup_v1_directory(controller: str) -> Path | None:
    text = _read_text(Path("/proc/self/cgroup"))
    if text is None:
        return None
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        controllers = set(parts[1].split(","))
        if controller in controllers:
            relative = parts[2].lstrip("/")
            return Path("/sys/fs/cgroup") / controller / relative
    return None


def _cgroup_memory() -> tuple[int | None, int | None, str | None]:
    directory = _cgroup_v2_directory()
    if directory is not None:
        raw_limit = _read_text(directory / "memory.max")
        current = _parse_positive_int(_read_text(directory / "memory.current"))
        if raw_limit is not None:
            limit = None if raw_limit == "max" else _parse_positive_int(raw_limit)
            return limit, current, "cgroup_v2"
    directory = _cgroup_v1_directory("memory")
    if directory is not None:
        limit = _parse_positive_int(_read_text(directory / "memory.limit_in_bytes"))
        current = _parse_positive_int(_read_text(directory / "memory.usage_in_bytes"))
        if limit is not None and limit >= 1 << 60:
            limit = None
        return limit, current, "cgroup_v1"
    return None, None, None


def _cgroup_cpu_quota() -> tuple[float | None, str | None]:
    directory = _cgroup_v2_directory()
    if directory is not None:
        text = _read_text(directory / "cpu.max")
        if text:
            fields = text.split()
            if len(fields) >= 2 and fields[0] != "max":
                quota = _parse_positive_int(fields[0])
                period = _parse_positive_int(fields[1])
                if quota is not None and period is not None:
                    return quota / period, "cgroup_v2"
            elif fields and fields[0] == "max":
                return None, "cgroup_v2"
    directory = _cgroup_v1_directory("cpu")
    if directory is not None:
        quota = _parse_positive_int(_read_text(directory / "cpu.cfs_quota_us"))
        period = _parse_positive_int(_read_text(directory / "cpu.cfs_period_us"))
        if quota is not None and period is not None:
            return quota / period, "cgroup_v1"
    return None, None


def _scheduler_cpu_limit(environment: Mapping[str, str]) -> tuple[int | None, str | None]:
    candidates: list[tuple[int, str]] = []
    for name in (
        "SLURM_CPUS_PER_TASK",
        "SLURM_CPUS_ON_NODE",
        "PBS_NP",
        "NSLOTS",
        "LSB_DJOB_NUMPROC",
    ):
        value = _parse_positive_int(environment.get(name))
        if value is not None:
            candidates.append((value, name))
    if not candidates:
        return None, None
    value, source = min(candidates, key=lambda item: item[0])
    return value, source


def _scheduler_memory_limit(
    environment: Mapping[str, str], *, scheduler_cpu_count: int | None
) -> tuple[int | None, str | None]:
    """Return the most restrictive scheduler-declared memory allocation.

    Batch systems sometimes expose more than one memory variable (for example,
    a requested-memory value and a virtual-memory ceiling).  Treat all parsable
    declarations as concurrent upper bounds rather than trusting whichever name
    happens to appear first.
    """

    candidates: list[tuple[int, str]] = []
    direct_names = (
        "SLURM_MEM_PER_NODE",
        "PBS_RESC_MEM",
        "PBS_VMEM",
        "LSB_MAX_MEM",
    )
    for name in direct_names:
        raw = environment.get(name)
        if raw is None:
            continue
        try:
            if name == "SLURM_MEM_PER_NODE" and raw.strip().replace(".", "", 1).isdigit():
                parsed = int(float(raw) * 1024**2)
            else:
                parsed = parse_byte_quantity(raw)
        except GraphStyleError:
            continue
        if parsed is not None:
            candidates.append((parsed, name))

    raw_per_cpu = environment.get("SLURM_MEM_PER_CPU")
    if raw_per_cpu is not None and scheduler_cpu_count is not None:
        try:
            per_cpu = (
                int(float(raw_per_cpu) * 1024**2)
                if raw_per_cpu.strip().replace(".", "", 1).isdigit()
                else parse_byte_quantity(raw_per_cpu)
            )
        except GraphStyleError:
            per_cpu = None
        if per_cpu is not None:
            candidates.append((per_cpu * scheduler_cpu_count, "SLURM_MEM_PER_CPU"))

    if not candidates:
        return None, None
    value, source = min(candidates, key=lambda item: item[0])
    return value, source


def _rlimit_as_headroom(virtual_memory_bytes: int) -> tuple[int | None, int | None]:
    try:
        soft, _hard = resource.getrlimit(resource.RLIMIT_AS)
    except (AttributeError, OSError, ValueError):
        return None, None
    if soft in (resource.RLIM_INFINITY, -1) or soft <= 0:
        return None, None
    return int(soft), max(0, int(soft) - int(virtual_memory_bytes))


@dataclass(frozen=True, slots=True)
class RuntimeResourceSnapshot:
    """Auditable CPU and memory constraints visible to the current process."""

    logical_cpu_count: int
    affinity_cpu_count: int
    cgroup_cpu_quota: float | None
    scheduler_cpu_count: int | None
    available_cpu_count: int
    host_memory_available_bytes: int
    cgroup_memory_limit_bytes: int | None
    cgroup_memory_current_bytes: int | None
    scheduler_memory_limit_bytes: int | None
    rlimit_as_bytes: int | None
    process_rss_bytes: int
    process_virtual_memory_bytes: int
    available_memory_bytes: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = RUNTIME_RESOURCE_SNAPSHOT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_RESOURCE_SNAPSHOT_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported runtime snapshot schema {self.schema_version!r}."
            )
        for name in (
            "logical_cpu_count",
            "affinity_cpu_count",
            "available_cpu_count",
            "host_memory_available_bytes",
            "process_rss_bytes",
            "process_virtual_memory_bytes",
            "available_memory_bytes",
        ):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))
        for name in (
            "scheduler_cpu_count",
            "cgroup_memory_limit_bytes",
            "cgroup_memory_current_bytes",
            "scheduler_memory_limit_bytes",
            "rlimit_as_bytes",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, _positive_int(value, name=name))
        if self.cgroup_cpu_quota is not None:
            object.__setattr__(
                self,
                "cgroup_cpu_quota",
                _positive_float(self.cgroup_cpu_quota, name="cgroup_cpu_quota"),
            )
        if self.available_cpu_count > self.affinity_cpu_count:
            raise GraphAdapterError("available_cpu_count exceeds CPU affinity.")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "logical_cpu_count": self.logical_cpu_count,
            "affinity_cpu_count": self.affinity_cpu_count,
            "cgroup_cpu_quota": self.cgroup_cpu_quota,
            "scheduler_cpu_count": self.scheduler_cpu_count,
            "available_cpu_count": self.available_cpu_count,
            "host_memory_available_bytes": self.host_memory_available_bytes,
            "cgroup_memory_limit_bytes": self.cgroup_memory_limit_bytes,
            "cgroup_memory_current_bytes": self.cgroup_memory_current_bytes,
            "scheduler_memory_limit_bytes": self.scheduler_memory_limit_bytes,
            "rlimit_as_bytes": self.rlimit_as_bytes,
            "process_rss_bytes": self.process_rss_bytes,
            "process_virtual_memory_bytes": self.process_virtual_memory_bytes,
            "available_memory_bytes": self.available_memory_bytes,
            "metadata": dict(self.metadata),
        }


def probe_runtime_resources() -> RuntimeResourceSnapshot:
    """Inspect CPU affinity, scheduler limits, cgroups, and process memory."""

    environment = os.environ
    logical = max(1, int(os.cpu_count() or 1))
    try:
        affinity = max(1, len(os.sched_getaffinity(0)))
        affinity_source = "sched_getaffinity"
    except (AttributeError, OSError):
        affinity = logical
        affinity_source = "os_cpu_count"
    quota, quota_source = _cgroup_cpu_quota()
    scheduler_cpu, scheduler_cpu_source = _scheduler_cpu_limit(environment)
    cpu_candidates = [affinity]
    if quota is not None:
        cpu_candidates.append(max(1, int(math.floor(quota + 1.0e-12))))
    if scheduler_cpu is not None:
        cpu_candidates.append(scheduler_cpu)
    available_cpu = max(1, min(cpu_candidates))

    rss, virtual = _proc_process_memory()
    host_available = _proc_memory_available()
    if host_available is None:
        host_available = _system_available_memory()
    if host_available is None:
        physical = _system_physical_memory()
        host_available = max(_MINIMUM_MEMORY_BUDGET_BYTES, (physical or rss * 4) - rss)
    cgroup_limit, cgroup_current, cgroup_memory_source = _cgroup_memory()
    scheduler_memory, scheduler_memory_source = _scheduler_memory_limit(
        environment, scheduler_cpu_count=scheduler_cpu
    )
    rlimit_as, rlimit_headroom = _rlimit_as_headroom(virtual)

    memory_headrooms = [host_available]
    if cgroup_limit is not None:
        memory_headrooms.append(max(0, cgroup_limit - (cgroup_current if cgroup_current is not None else rss)))
    if scheduler_memory is not None:
        memory_headrooms.append(max(0, scheduler_memory - rss))
    if rlimit_headroom is not None:
        memory_headrooms.append(rlimit_headroom)
    # Zero headroom from any authoritative source must not be discarded; doing
    # so would incorrectly fall back to a less restrictive host-level value.
    available_memory = max(1, min(memory_headrooms)) if memory_headrooms else _MINIMUM_MEMORY_BUDGET_BYTES

    return RuntimeResourceSnapshot(
        logical_cpu_count=logical,
        affinity_cpu_count=affinity,
        cgroup_cpu_quota=quota,
        scheduler_cpu_count=scheduler_cpu,
        available_cpu_count=available_cpu,
        host_memory_available_bytes=max(1, host_available),
        cgroup_memory_limit_bytes=cgroup_limit,
        cgroup_memory_current_bytes=cgroup_current,
        scheduler_memory_limit_bytes=scheduler_memory,
        rlimit_as_bytes=rlimit_as,
        process_rss_bytes=max(1, rss),
        process_virtual_memory_bytes=max(1, virtual),
        available_memory_bytes=max(1, available_memory),
        metadata={
            "cpu_affinity_source": affinity_source,
            "cgroup_cpu_source": quota_source,
            "scheduler_cpu_source": scheduler_cpu_source,
            "cgroup_memory_source": cgroup_memory_source,
            "scheduler_memory_source": scheduler_memory_source,
        },
    )


@dataclass(frozen=True, slots=True)
class RuntimeResourceBudget:
    """Resolved package-owned compute budget for one complete scene."""

    max_memory_bytes: int
    max_threads: int
    max_wall_time_seconds: float
    memory_fraction: float
    thread_fraction: float
    snapshot: RuntimeResourceSnapshot
    memory_override_source: str
    thread_override_source: str
    wall_time_override_source: str
    memory_override_clamped: bool = False
    thread_override_clamped: bool = False
    schema_version: str = RUNTIME_RESOURCE_BUDGET_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != RUNTIME_RESOURCE_BUDGET_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported runtime budget schema {self.schema_version!r}."
            )
        object.__setattr__(
            self, "max_memory_bytes", _positive_int(self.max_memory_bytes, name="max_memory_bytes")
        )
        object.__setattr__(self, "max_threads", _positive_int(self.max_threads, name="max_threads"))
        object.__setattr__(
            self,
            "max_wall_time_seconds",
            _positive_float(self.max_wall_time_seconds, name="max_wall_time_seconds"),
        )
        object.__setattr__(
            self, "memory_fraction", _fraction(self.memory_fraction, name="memory_fraction")
        )
        object.__setattr__(
            self, "thread_fraction", _fraction(self.thread_fraction, name="thread_fraction")
        )
        if not isinstance(self.snapshot, RuntimeResourceSnapshot):
            raise TypeError("snapshot must be RuntimeResourceSnapshot.")
        if self.max_memory_bytes > self.snapshot.available_memory_bytes:
            raise GraphAdapterError("Resolved memory budget exceeds detected memory availability.")
        if self.max_threads > self.snapshot.available_cpu_count:
            raise GraphAdapterError("Resolved thread budget exceeds detected CPU availability.")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_memory_bytes": self.max_memory_bytes,
            "max_threads": self.max_threads,
            "max_wall_time_seconds": self.max_wall_time_seconds,
            "memory_fraction": self.memory_fraction,
            "thread_fraction": self.thread_fraction,
            "memory_override_source": self.memory_override_source,
            "thread_override_source": self.thread_override_source,
            "wall_time_override_source": self.wall_time_override_source,
            "memory_override_clamped": self.memory_override_clamped,
            "thread_override_clamped": self.thread_override_clamped,
            "snapshot": self.snapshot.to_json_dict(),
        }


@contextmanager
def density_resource_budget_scope(budget: RuntimeResourceBudget):
    """Make one resolved scene budget authoritative for nested density calls.

    The scope is context-local, so concurrent threads/tasks do not overwrite one
    another.  Nested low-level APIs inherit the exact scene memory/thread controls
    and the advisory wall-time metadata instead of re-probing and accidentally
    applying another resource fraction.
    """

    if not isinstance(budget, RuntimeResourceBudget):
        raise TypeError("budget must be RuntimeResourceBudget.")
    token = _ACTIVE_DENSITY_RESOURCE_BUDGET.set(budget)
    try:
        yield budget
    finally:
        _ACTIVE_DENSITY_RESOURCE_BUDGET.reset(token)


def active_density_resource_budget() -> RuntimeResourceBudget | None:
    """Return the context-local complete-scene budget, when one is active."""

    return _ACTIVE_DENSITY_RESOURCE_BUDGET.get()


def _resolve_optional_memory(
    explicit: int | str | None, environment: Mapping[str, str]
) -> tuple[int | None, str]:
    if explicit is not None:
        return parse_byte_quantity(explicit), "argument"
    raw = environment.get("MDSTATS_MAX_MEMORY_BYTES")
    if raw is not None:
        return parse_byte_quantity(raw), "MDSTATS_MAX_MEMORY_BYTES"
    return None, "runtime_fraction"


def _resolve_optional_threads(
    explicit: int | None, environment: Mapping[str, str]
) -> tuple[int | None, str]:
    if explicit is not None:
        return _positive_int(explicit, name="max_threads"), "argument"
    raw = environment.get("MDSTATS_MAX_THREADS")
    if raw is not None:
        parsed = _parse_positive_int(raw)
        if parsed is None:
            raise GraphStyleError("MDSTATS_MAX_THREADS must be a positive integer.")
        return parsed, "MDSTATS_MAX_THREADS"
    return None, "runtime_fraction"


def _resolve_optional_wall_time(
    explicit: float | None, environment: Mapping[str, str]
) -> tuple[float, str]:
    if explicit is not None:
        return _positive_float(explicit, name="max_wall_time_seconds"), "argument"
    raw = environment.get("MDSTATS_MAX_WALL_TIME_SECONDS")
    if raw is not None:
        return _positive_float(raw, name="MDSTATS_MAX_WALL_TIME_SECONDS"), "MDSTATS_MAX_WALL_TIME_SECONDS"
    return _DEFAULT_WALL_TIME_SECONDS, "default_20_minutes"


def resolve_runtime_resource_budget(
    *,
    max_memory_bytes: int | str | None = None,
    max_threads: int | None = None,
    max_wall_time_seconds: float | None = None,
    memory_fraction: float = _DEFAULT_MEMORY_FRACTION,
    thread_fraction: float = _DEFAULT_THREAD_FRACTION,
    snapshot: RuntimeResourceSnapshot | None = None,
    environment: Mapping[str, str] | None = None,
) -> RuntimeResourceBudget:
    """Resolve user/environment policy against actual runtime ceilings."""

    memory_fraction = _fraction(memory_fraction, name="memory_fraction")
    thread_fraction = _fraction(thread_fraction, name="thread_fraction")
    active_budget = _ACTIVE_DENSITY_RESOURCE_BUDGET.get()
    if active_budget is not None and snapshot is None and environment is None:
        requested_memory = parse_byte_quantity(max_memory_bytes)
        requested_threads = (
            None if max_threads is None else _positive_int(max_threads, name="max_threads")
        )
        requested_wall = (
            None
            if max_wall_time_seconds is None
            else _positive_float(
                max_wall_time_seconds, name="max_wall_time_seconds"
            )
        )
        resolved_memory = (
            active_budget.max_memory_bytes
            if requested_memory is None
            else min(requested_memory, active_budget.max_memory_bytes)
        )
        resolved_threads = (
            active_budget.max_threads
            if requested_threads is None
            else min(requested_threads, active_budget.max_threads)
        )
        resolved_wall = (
            active_budget.max_wall_time_seconds
            if requested_wall is None
            else min(requested_wall, active_budget.max_wall_time_seconds)
        )
        return RuntimeResourceBudget(
            max_memory_bytes=resolved_memory,
            max_threads=resolved_threads,
            max_wall_time_seconds=resolved_wall,
            memory_fraction=active_budget.memory_fraction,
            thread_fraction=active_budget.thread_fraction,
            snapshot=active_budget.snapshot,
            memory_override_source=(
                "active_scene_budget"
                if requested_memory is None
                else "argument_within_active_scene_budget"
            ),
            thread_override_source=(
                "active_scene_budget"
                if requested_threads is None
                else "argument_within_active_scene_budget"
            ),
            wall_time_override_source=(
                "active_scene_budget"
                if requested_wall is None
                else "argument_within_active_scene_budget"
            ),
            memory_override_clamped=(
                requested_memory is not None
                and requested_memory > active_budget.max_memory_bytes
            ),
            thread_override_clamped=(
                requested_threads is not None
                and requested_threads > active_budget.max_threads
            ),
        )
    resolved_snapshot = probe_runtime_resources() if snapshot is None else snapshot
    if not isinstance(resolved_snapshot, RuntimeResourceSnapshot):
        raise TypeError("snapshot must be RuntimeResourceSnapshot or None.")
    active_environment = os.environ if environment is None else environment

    requested_memory, memory_source = _resolve_optional_memory(
        max_memory_bytes, active_environment
    )
    default_memory = max(
        1, int(math.floor(memory_fraction * resolved_snapshot.available_memory_bytes))
    )
    memory_clamped = False
    if requested_memory is None:
        resolved_memory = default_memory
    else:
        resolved_memory = min(requested_memory, resolved_snapshot.available_memory_bytes)
        memory_clamped = requested_memory > resolved_snapshot.available_memory_bytes

    requested_threads, thread_source = _resolve_optional_threads(
        max_threads, active_environment
    )
    default_threads = max(
        1, int(math.floor(thread_fraction * resolved_snapshot.available_cpu_count))
    )
    thread_clamped = False
    if requested_threads is None:
        resolved_threads = default_threads
    else:
        resolved_threads = min(requested_threads, resolved_snapshot.available_cpu_count)
        thread_clamped = requested_threads > resolved_snapshot.available_cpu_count

    wall_time, wall_source = _resolve_optional_wall_time(
        max_wall_time_seconds, active_environment
    )
    return RuntimeResourceBudget(
        max_memory_bytes=max(1, resolved_memory),
        max_threads=max(1, resolved_threads),
        max_wall_time_seconds=wall_time,
        memory_fraction=memory_fraction,
        thread_fraction=thread_fraction,
        snapshot=resolved_snapshot,
        memory_override_source=memory_source,
        thread_override_source=thread_source,
        wall_time_override_source=wall_source,
        memory_override_clamped=memory_clamped,
        thread_override_clamped=thread_clamped,
    )


@dataclass(frozen=True, slots=True)
class DensityTimeModel:
    """Conservative runtime model for density cost estimation and backend choice.

    Wall-time estimates are advisory diagnostics only; they are not feasibility
    constraints and never terminate an otherwise memory-feasible density run.
    Preparation rates are measured while native numerical libraries are limited
    to ``calibration_threads``.  Mesh rates are one-worker rates because each
    isolated shell worker defaults to one native thread.  The model is based on
    synthetic, input-independent kernels; no structure, trajectory, grid, or
    benchmark scene contributes to these values.
    """

    samples_per_second: float = 2_000_000.0
    stencil_values_per_second: float = 8_000_000.0
    kernel_pairs_per_second: float = 4_000_000.0
    dense_nodes_per_second: float = 1_000_000.0
    direct_index_pairs_per_second: float = 4_000_000.0
    direct_reduction_pairs_per_second: float = 4_000_000.0
    support_region_operations_per_second: float = 2_000_000.0
    fft_work_units_per_second: float = 20_000_000.0
    mesh_cells_per_second: float = 500_000.0
    mesh_faces_per_second: float = 250_000.0
    fixed_seconds_per_field: float = 0.25
    fixed_seconds_per_shell: float = 0.15
    process_startup_seconds: float = 0.35
    parallel_efficiency: float = 0.70
    safety_multiplier: float = 2.0
    calibration_threads: int = 1
    calibration_source: str = "conservative_static_v3"
    calibration_wall_seconds: float = 0.0
    calibration_metadata: Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DENSITY_TIME_MODEL_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {
            DENSITY_TIME_MODEL_SCHEMA,
            "mdstats.density-time-model.v2",
            "mdstats.density-time-model.v1",
        }:
            raise GraphAdapterError(
                f"Unsupported density-time-model schema {self.schema_version!r}."
            )
        for name in (
            "samples_per_second",
            "stencil_values_per_second",
            "kernel_pairs_per_second",
            "dense_nodes_per_second",
            "direct_index_pairs_per_second",
            "direct_reduction_pairs_per_second",
            "support_region_operations_per_second",
            "fft_work_units_per_second",
            "mesh_cells_per_second",
            "mesh_faces_per_second",
            "safety_multiplier",
        ):
            object.__setattr__(self, name, _positive_float(getattr(self, name), name=name))
        for name in (
            "fixed_seconds_per_field",
            "fixed_seconds_per_shell",
            "process_startup_seconds",
            "calibration_wall_seconds",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphStyleError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        efficiency = float(self.parallel_efficiency)
        if not np.isfinite(efficiency) or not 0.0 < efficiency <= 1.0:
            raise GraphStyleError("parallel_efficiency must lie in (0, 1].")
        object.__setattr__(self, "parallel_efficiency", efficiency)
        object.__setattr__(
            self,
            "calibration_threads",
            _positive_int(self.calibration_threads, name="calibration_threads"),
        )
        if not isinstance(self.calibration_source, str) or not self.calibration_source:
            raise GraphStyleError("calibration_source must be a nonempty string.")
        metadata = dict(self.calibration_metadata)
        object.__setattr__(self, "calibration_metadata", MappingProxyType(metadata))
        object.__setattr__(self, "schema_version", DENSITY_TIME_MODEL_SCHEMA)

    def to_json_dict(self) -> dict[str, Any]:
        result = {name: getattr(self, name) for name in self.__dataclass_fields__}
        result["calibration_metadata"] = dict(self.calibration_metadata)
        return result

    def estimate_preparation_seconds(
        self,
        *,
        field_count: int,
        sample_count: int,
        stencil_value_count: int,
        kernel_pair_count: int,
        dense_node_count: int,
    ) -> float:
        field_count = max(0, int(field_count))
        raw = (
            field_count * self.fixed_seconds_per_field
            + max(0, int(sample_count)) / self.samples_per_second
            + max(0, int(stencil_value_count)) / self.stencil_values_per_second
            + max(0, int(kernel_pair_count)) / self.kernel_pairs_per_second
            + max(0, int(dense_node_count)) / self.dense_nodes_per_second
        )
        return self.safety_multiplier * raw

    def estimate_mesh_seconds(
        self,
        *,
        shell_count: int,
        mesh_cell_count: int,
        mesh_face_count: int,
        max_workers: int,
        isolated_workers: bool = True,
    ) -> float:
        shell_count = max(0, int(shell_count))
        if shell_count == 0:
            return 0.0
        workers = max(1, min(max(1, int(max_workers)), shell_count))
        serial_kernel = (
            shell_count * self.fixed_seconds_per_shell
            + max(0, int(mesh_cell_count)) / self.mesh_cells_per_second
            + max(0, int(mesh_face_count)) / self.mesh_faces_per_second
        )
        if workers == 1:
            parallelized = serial_kernel
        else:
            parallelized = serial_kernel / (workers * self.parallel_efficiency)
        startup = (
            shell_count * self.process_startup_seconds / workers
            if isolated_workers
            else 0.0
        )
        return self.safety_multiplier * (parallelized + startup)


def _timed_rate(item_count: int, operation: Any, *, repeats: int = 3) -> float:
    """Return a median-throughput estimate rather than an optimistic best run."""

    operation()
    elapsed_values: list[float] = []
    for _ in range(max(1, repeats)):
        started = time.perf_counter()
        operation()
        elapsed = time.perf_counter() - started
        if elapsed > 0.0 and np.isfinite(elapsed):
            elapsed_values.append(elapsed)
    if not elapsed_values:
        return 1.0
    return float(item_count) / float(np.median(np.asarray(elapsed_values)))


@contextmanager
def density_time_model_scope(model: DensityTimeModel):
    """Make one pre-calibrated density time model authoritative for nested calls.

    Production scene realization must not launch synthetic PAR-DENS calibration
    from worker threads.  The model is execution/cost evidence resolved once at
    scene entry and inherited context-locally by scheduled field tasks.
    """

    if not isinstance(model, DensityTimeModel):
        raise TypeError("model must be DensityTimeModel.")
    token = _ACTIVE_DENSITY_TIME_MODEL.set(model)
    try:
        yield model
    finally:
        _ACTIVE_DENSITY_TIME_MODEL.reset(token)


def active_density_time_model() -> DensityTimeModel | None:
    """Return the context-local pre-calibrated density time model, if active."""

    return _ACTIVE_DENSITY_TIME_MODEL.get()


def calibrate_density_time_model(max_threads: int | None = None) -> DensityTimeModel:
    """Return a cached, input-independent throughput model for a thread budget.

    Even standalone calls are clamped to the active scene allocation (when
    present) or to a fresh runtime probe.  Calibration therefore cannot create
    an oversubscribed thread pool merely because an expert option or serialized
    record contains a larger number.
    """

    active_budget = active_density_resource_budget()
    if active_budget is not None:
        runtime_thread_ceiling = active_budget.max_threads
    else:
        runtime_thread_ceiling = probe_runtime_resources().available_cpu_count
    if max_threads is None:
        threads = (
            runtime_thread_ceiling
            if active_budget is not None
            else max(
                1,
                int(math.floor(_DEFAULT_THREAD_FRACTION * runtime_thread_ceiling)),
            )
        )
    else:
        threads = min(
            _positive_int(max_threads, name="max_threads"), runtime_thread_ceiling
        )
    disabled = os.environ.get("MDSTATS_DISABLE_TIME_CALIBRATION", "").strip() in {
        "1", "true", "True"
    }
    return _calibrate_density_time_model_cached(threads, disabled)


@lru_cache(maxsize=32)
def _calibrate_density_time_model_cached(
    calibration_threads: int, disabled: bool
) -> DensityTimeModel:
    """Calibrate the operations executed by the production density backends.

    PAR-DENS1 intentionally measures irregular destination-index generation,
    grouped/bincount reduction, packed support-region bit operations, and
    worker-aware ``scipy.fft`` transforms.  The benchmark is synthetic and
    input-independent: trajectory coordinates never participate in calibration.
    """

    metadata_base: dict[str, Any] = {
        "calibration_policy": "par_dens1_execution_faithful_v1",
        "array_dtype": "float64",
        "index_dtype": "int64",
        "calibration_threads": int(calibration_threads),
    }
    if disabled:
        return DensityTimeModel(
            calibration_threads=calibration_threads,
            calibration_source="conservative_static_disabled_v3",
            calibration_metadata={**metadata_base, "disabled": True},
        )
    started = time.perf_counter()
    try:
        try:
            from threadpoolctl import threadpool_limits
        except ImportError:  # pragma: no cover - base dependency in packaged builds
            from contextlib import nullcontext

            def threadpool_limits(*, limits: int):
                return nullcontext()

        from scipy.fft import irfftn, next_fast_len, rfftn

        # CIC/sample-coordinate preparation: production-like floor/fold arithmetic.
        n_samples = 262_144
        x = np.linspace(-3.0, 3.0, n_samples, dtype=np.float64)
        y = np.linspace(2.0, -2.0, n_samples, dtype=np.float64)
        z = np.linspace(-1.0, 1.0, n_samples, dtype=np.float64)

        # Irregular direct realization calibration.  The destination pattern is
        # deliberately non-contiguous and repeats targets, matching the cost class
        # of sparse scatter/grouped reduction rather than a contiguous vector sum.
        contribution_count = 524_288
        source_index = np.arange(contribution_count, dtype=np.int64)
        destination_count = contribution_count // 5 + 97
        weights = 0.5 + (source_index % 1024).astype(np.float64) / 1024.0
        offset_cycle = np.asarray(
            [0, 1, 7, 19, 43, 89, 181, 367, 733, 1459, 2917, 5839, 11681],
            dtype=np.int64,
        )

        def destination_indices() -> np.ndarray:
            offsets = offset_cycle[source_index % offset_cycle.size]
            return (source_index * 104729 + offsets * 8191) % destination_count

        destinations = destination_indices()

        # Support-atlas bit-region work.  uint64 OR/shift/reduction reflects the
        # packed bitset operations used by LD8 support dilation without depending
        # on any real scene.
        support_words = 131_072
        word_source = (
            np.arange(support_words, dtype=np.uint64) * np.uint64(11400714819323198485)
        )
        shifted = np.empty_like(word_source)

        def support_region_operation() -> int:
            np.left_shift(word_source, np.uint64(1), out=shifted)
            np.bitwise_or(shifted, word_source, out=shifted)
            return int(np.bitwise_xor.reduce(shifted, dtype=np.uint64))

        # FFT overlap-add calibration uses scipy.fft and the exact production
        # worker control rather than numpy.fft's unrelated threading semantics.
        tile_shape = (32, 32, 32)
        kernel_shape = (17, 17, 17)
        padded_shape = tuple(
            int(next_fast_len(tile_shape[axis] + kernel_shape[axis] - 1))
            for axis in range(3)
        )
        fft_values = np.sin(
            np.arange(np.prod(padded_shape), dtype=np.float64).reshape(padded_shape)
            / 17.0
        )
        fft_output_shape = padded_shape

        def fft_round_trip() -> np.ndarray:
            spectrum = rfftn(fft_values, workers=calibration_threads)
            return irfftn(spectrum, s=fft_output_shape, workers=calibration_threads)

        with threadpool_limits(limits=calibration_threads):
            sample_rate_measured = _timed_rate(
                n_samples,
                lambda: (x - np.floor(x), y - np.floor(y), z - np.floor(z)),
            )
            direct_index_rate = _timed_rate(
                contribution_count, destination_indices, repeats=3
            )
            direct_bincount_rate = _timed_rate(
                contribution_count,
                lambda: np.bincount(
                    destinations, weights=weights, minlength=destination_count
                ),
                repeats=3,
            )

            def direct_add_at_reduction() -> np.ndarray:
                accumulator = np.zeros(destination_count, dtype=np.float64)
                np.add.at(accumulator, destinations, weights)
                return accumulator

            direct_add_at_rate = _timed_rate(
                contribution_count, direct_add_at_reduction, repeats=3
            )
            # Production has both bounded bincount and np.add.at paths.  Cost
            # admission must not price the direct executor from the faster one
            # alone, so use the slower measured irregular reduction rate.
            direct_reduction_rate = min(direct_bincount_rate, direct_add_at_rate)
            support_rate = _timed_rate(
                support_words, support_region_operation, repeats=3
            )
            fft_node_rate = _timed_rate(
                int(np.prod(padded_shape)), fft_round_trip, repeats=3
            )

        padded_nodes = int(np.prod(padded_shape, dtype=object))
        fft_work_units = padded_nodes * max(1.0, math.log2(max(2, padded_nodes)))
        # Convert the measured node rate to N log2(N) work units per second.
        fft_work_rate = fft_node_rate * max(1.0, math.log2(max(2, padded_nodes)))

        # Mesh calibration remains one-worker because mesh extraction is isolated
        # independently from density-field execution.
        mesh_shape = (64, 64, 64)
        axis = np.linspace(-1.0, 1.0, mesh_shape[0], dtype=np.float64)
        gx, gy, gz = np.meshgrid(axis, axis, axis, indexing="ij")
        scalar = gx * gx + gy * gy + gz * gz
        threshold = 0.7

        def mesh_scan() -> int:
            low = np.minimum.reduce(
                (
                    scalar[:-1, :-1, :-1], scalar[1:, :-1, :-1],
                    scalar[:-1, 1:, :-1], scalar[:-1, :-1, 1:],
                    scalar[1:, 1:, :-1], scalar[1:, :-1, 1:],
                    scalar[:-1, 1:, 1:], scalar[1:, 1:, 1:],
                )
            )
            high = np.maximum.reduce(
                (
                    scalar[:-1, :-1, :-1], scalar[1:, :-1, :-1],
                    scalar[:-1, 1:, :-1], scalar[:-1, :-1, 1:],
                    scalar[1:, 1:, :-1], scalar[1:, :-1, 1:],
                    scalar[:-1, 1:, 1:], scalar[1:, 1:, 1:],
                )
            )
            return int(np.count_nonzero((low <= threshold) & (high >= threshold)))

        mesh_cells = int(np.prod(np.asarray(mesh_shape) - 1))
        with threadpool_limits(limits=1):
            mesh_rate_measured = _timed_rate(mesh_cells, mesh_scan, repeats=3)
            face_rate_measured = mesh_rate_measured
            mesh_source = "scalar_crossing_scan"
            try:
                from skimage.measure import marching_cubes

                def actual_contour() -> int:
                    _vertices, faces, _normals, _values = marching_cubes(
                        scalar, level=threshold, allow_degenerate=False
                    )
                    return int(faces.shape[0])

                face_count = max(1, actual_contour())
                face_rate_measured = _timed_rate(face_count, actual_contour, repeats=3)
                mesh_source = "skimage_marching_cubes"
            except (ImportError, ValueError, RuntimeError):
                pass

        # Keep conservative admission fractions.  They reserve substantial room
        # for Python orchestration/cache misses while preserving the measured
        # ordering between the actual direct and FFT cost classes.
        transient_bytes = int(
            source_index.nbytes
            + destinations.nbytes
            + weights.nbytes
            + word_source.nbytes
            + shifted.nbytes
            + fft_values.nbytes
            + (padded_nodes // 2 + 1) * np.dtype(np.complex128).itemsize
        )
        calibration_metadata = {
            **metadata_base,
            "direct_contribution_count": contribution_count,
            "direct_destination_count": destination_count,
            "direct_bincount_pairs_per_second_measured": float(direct_bincount_rate),
            "direct_add_at_pairs_per_second_measured": float(direct_add_at_rate),
            "direct_reduction_pairs_per_second_measured": float(direct_reduction_rate),
            "direct_reduction_calibration_policy": "slower_of_bincount_and_add_at_v1",
            "support_word_count": support_words,
            "tile_shape": list(tile_shape),
            "kernel_shape": list(kernel_shape),
            "fft_padded_shape": list(padded_shape),
            "fft_padded_nodes": padded_nodes,
            "fft_work_units": float(fft_work_units),
            "source_occupancy": float(contribution_count / destination_count),
            "temporary_memory_bytes": transient_bytes,
            "fft_backend": "scipy.fft.pocketfft",
            "mesh_backend": mesh_source,
        }
        return DensityTimeModel(
            samples_per_second=max(100_000.0, 0.08 * sample_rate_measured),
            stencil_values_per_second=max(100_000.0, 0.06 * direct_index_rate),
            kernel_pairs_per_second=max(100_000.0, 0.06 * direct_reduction_rate),
            dense_nodes_per_second=max(50_000.0, 0.08 * fft_node_rate),
            direct_index_pairs_per_second=max(100_000.0, 0.06 * direct_index_rate),
            direct_reduction_pairs_per_second=max(100_000.0, 0.06 * direct_reduction_rate),
            support_region_operations_per_second=max(50_000.0, 0.08 * support_rate),
            fft_work_units_per_second=max(250_000.0, 0.08 * fft_work_rate),
            mesh_cells_per_second=max(25_000.0, 0.025 * mesh_rate_measured),
            mesh_faces_per_second=max(12_500.0, 0.02 * face_rate_measured),
            fixed_seconds_per_field=0.35,
            fixed_seconds_per_shell=0.20,
            process_startup_seconds=0.50,
            parallel_efficiency=0.65,
            safety_multiplier=2.0,
            calibration_threads=calibration_threads,
            calibration_source=f"par_dens1_runtime_execution_calibration_v1:{mesh_source}",
            calibration_wall_seconds=time.perf_counter() - started,
            calibration_metadata=calibration_metadata,
        )
    except Exception as error:
        return DensityTimeModel(
            calibration_threads=calibration_threads,
            calibration_source="conservative_static_fallback_v3",
            calibration_wall_seconds=time.perf_counter() - started,
            calibration_metadata={
                **metadata_base,
                "fallback": True,
                "error_type": type(error).__name__,
            },
        )


def derive_count_limit(
    *, memory_bytes: int, bytes_per_item: int, time_seconds: float, items_per_second: float
) -> int:
    """Return the largest positive count satisfying the memory ceiling.

    ``time_seconds`` and ``items_per_second`` are retained in the public signature
    for backwards compatibility.  They are validated as advisory inputs but do
    not constrain the returned count; density execution is not wall-time bounded.
    """

    memory_limit = _positive_int(memory_bytes, name="memory_bytes") // _positive_int(
        bytes_per_item, name="bytes_per_item"
    )
    _positive_float(time_seconds, name="time_seconds")
    _positive_float(items_per_second, name="items_per_second")
    return max(1, memory_limit)


def derive_density_numeric_limits(
    *, budget: RuntimeResourceBudget, time_model: DensityTimeModel
) -> dict[str, int]:
    """Derive broad numeric guardrails from host budgets, never an input scene.

    Density feasibility is memory/structure bounded, not wall-time bounded.
    ``max_wall_time_seconds`` remains part of the runtime budget for backwards
    compatible metadata and advisory cost reporting, but it does not derive
    operation-count caps.  Explicit expert operation caps supplied by callers
    continue to be honored by the low-level APIs.
    """

    if not isinstance(budget, RuntimeResourceBudget):
        raise TypeError("budget must be RuntimeResourceBudget.")
    if not isinstance(time_model, DensityTimeModel):
        raise TypeError("time_model must be DensityTimeModel.")
    memory = budget.max_memory_bytes
    # Operation-only defaults must not impose an implicit wall-time ceiling.
    # Use the largest signed 64-bit count as the package default; callers can
    # still request stricter explicit caps where desired.
    unbounded_operation_count = int(np.iinfo(np.int64).max)

    def memory_count(bytes_per_item: int) -> int:
        return max(1, memory // _positive_int(bytes_per_item, name="bytes_per_item"))

    return {
        "max_trajectory_points": memory_count(48),
        "max_density_voxels": memory_count(320),
        "max_density_samples": memory_count(128),
        "max_density_stencil_values": memory_count(16),
        "max_density_nonzero_nodes": memory_count(64),
        "max_density_stored_block_values": memory_count(64),
        "max_density_blocks": memory_count(128),
        "max_density_component_values": memory_count(32),
        "max_density_mesh_cells": memory_count(64),
        "max_density_mesh_faces": memory_count(96),
        "max_density_render_points": memory_count(32),
        "max_density_kernel_pairs": unbounded_operation_count,
        "max_density_fields": memory_count(32 * 1024**2),
        "max_trajectory_traces": max(64, 16 * budget.max_threads),
        "max_density_traces": max(64, 16 * budget.max_threads),
        "max_density_sample_bytes": memory,
        "max_density_planning_bytes": memory,
        "max_density_total_peak_bytes": memory,
    }

def resolve_density_resource_limits(
    *,
    max_memory_bytes: int | str | None = None,
    max_threads: int | None = None,
    max_wall_time_seconds: float | None = None,
    memory_fraction: float = _DEFAULT_MEMORY_FRACTION,
    thread_fraction: float = _DEFAULT_THREAD_FRACTION,
    snapshot: RuntimeResourceSnapshot | None = None,
    environment: Mapping[str, str] | None = None,
    time_model: DensityTimeModel | None = None,
) -> tuple[RuntimeResourceBudget, DensityTimeModel, Mapping[str, int]]:
    """Resolve one coherent runtime budget, time model, and numeric guardrails.

    Low-level public density APIs use this helper only when callers omit their
    expert limits.  The returned counts are therefore derived from the active
    host/job allocation, never from an example trajectory, cell, prior benchmark
    scene, or wall-time admission objective.  Wall time is advisory metadata only.
    """

    budget = resolve_runtime_resource_budget(
        max_memory_bytes=max_memory_bytes,
        max_threads=max_threads,
        max_wall_time_seconds=max_wall_time_seconds,
        memory_fraction=memory_fraction,
        thread_fraction=thread_fraction,
        snapshot=snapshot,
        environment=environment,
    )
    inherited_model = active_density_time_model() if time_model is None else None
    model = (
        inherited_model
        if inherited_model is not None
        else (
            calibrate_density_time_model(max_threads=budget.max_threads)
            if time_model is None
            else time_model
        )
    )
    if not isinstance(model, DensityTimeModel):
        raise TypeError("time_model must be DensityTimeModel or None.")
    return budget, model, MappingProxyType(
        derive_density_numeric_limits(budget=budget, time_model=model)
    )

