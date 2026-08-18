"""Bounded execution policy for browser-density shell preparation.

Execution limits are resolved against the complete-scene CPU and memory budget.
The module never chooses a worker count from a benchmark system.  Wall-time
estimates are advisory only; workers have no implicit scene-derived timeout.
An explicit ``worker_timeout_seconds`` remains available as an opt-in kill switch.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError

DENSITY_MESH_EXECUTION_OPTIONS_SCHEMA = "mdstats.density-mesh-execution-options.v3"
DENSITY_MESH_EXECUTION_REPORT_SCHEMA = "mdstats.density-mesh-execution-report.v1"


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise GraphStyleError(f"{name} must be finite and positive.")
    return result


@dataclass(frozen=True, slots=True)
class DensityMeshExecutionOptions:
    """Scheduler policy for independent density-shell workers.

    Unresolved ``None`` values inherit the complete-scene resource budget.
    Resolution enforces both CPU and memory ceilings.  Memory accounting
    includes the retained parent scene, reserved final geometry, and a
    conservative largest-worker peak; therefore the pool cannot multiply a
    field-sized workspace by an arbitrary CPU-derived worker count.
    """

    max_parallel_shell_workers: int | None = None
    worker_native_threads: int = 1
    worker_timeout_seconds: float | None = None
    worker_memory_bytes: int | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_MESH_EXECUTION_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {
            DENSITY_MESH_EXECUTION_OPTIONS_SCHEMA,
            "mdstats.density-mesh-execution-options.v1",
            "mdstats.density-mesh-execution-options.v2",
        }:
            raise GraphAdapterError(
                f"Unsupported density-mesh execution schema {self.schema_version!r}."
            )
        if self.max_parallel_shell_workers is not None:
            object.__setattr__(
                self,
                "max_parallel_shell_workers",
                _positive_int(
                    self.max_parallel_shell_workers,
                    name="max_parallel_shell_workers",
                ),
            )
        object.__setattr__(
            self,
            "worker_native_threads",
            _positive_int(self.worker_native_threads, name="worker_native_threads"),
        )
        if self.worker_timeout_seconds is not None:
            object.__setattr__(
                self,
                "worker_timeout_seconds",
                _positive_float(
                    self.worker_timeout_seconds, name="worker_timeout_seconds"
                ),
            )
        if self.worker_memory_bytes is not None:
            object.__setattr__(
                self,
                "worker_memory_bytes",
                _positive_int(self.worker_memory_bytes, name="worker_memory_bytes"),
            )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        object.__setattr__(self, "schema_version", DENSITY_MESH_EXECUTION_OPTIONS_SCHEMA)

    def resolve(
        self,
        *,
        max_threads: int,
        remaining_wall_time_seconds: float | None = None,
        max_memory_bytes: int,
        parent_retained_bytes: int,
        final_output_reserve_bytes: int,
        largest_worker_peak_bytes: int,
        isolated_shell_count: int,
    ) -> "DensityMeshExecutionOptions":
        """Resolve worker count against scene-wide CPU and memory ceilings.

        ``remaining_wall_time_seconds`` is accepted for backwards compatibility
        and recorded only as advisory metadata.  It does not clamp worker count
        or worker lifetime.
        """

        thread_limit = _positive_int(max_threads, name="max_threads")
        remaining = (
            None
            if remaining_wall_time_seconds is None
            else _positive_float(
                remaining_wall_time_seconds, name="remaining_wall_time_seconds"
            )
        )
        memory_limit = _positive_int(max_memory_bytes, name="max_memory_bytes")
        parent = _positive_int(
            parent_retained_bytes, name="parent_retained_bytes", minimum=0
        )
        output_reserve = _positive_int(
            final_output_reserve_bytes,
            name="final_output_reserve_bytes",
            minimum=0,
        )
        worker_peak = _positive_int(
            largest_worker_peak_bytes,
            name="largest_worker_peak_bytes",
            minimum=1,
        )
        shell_count = _positive_int(
            isolated_shell_count, name="isolated_shell_count", minimum=0
        )
        requested_native = self.worker_native_threads
        native = min(requested_native, thread_limit)
        thread_worker_cap = max(1, thread_limit // native)
        available_worker_pool = memory_limit - parent - output_reserve
        if shell_count > 0 and available_worker_pool < worker_peak:
            raise GraphComplexityError(
                "Isolated density-shell execution has insufficient scene memory: "
                f"max_memory_bytes={memory_limit}, parent_retained_bytes={parent}, "
                f"final_output_reserve_bytes={output_reserve}, "
                f"largest_worker_peak_bytes={worker_peak}. Increase max_memory_bytes "
                "explicitly or reduce density resolution/browser geometry."
            )
        memory_worker_cap = (
            1 if shell_count == 0 else max(1, available_worker_pool // worker_peak)
        )
        shell_worker_cap = max(1, shell_count)
        requested_workers = (
            thread_worker_cap
            if self.max_parallel_shell_workers is None
            else self.max_parallel_shell_workers
        )
        resolved_workers = min(
            requested_workers,
            thread_worker_cap,
            memory_worker_cap,
            shell_worker_cap,
        )
        requested_timeout = self.worker_timeout_seconds
        resolved_timeout = requested_timeout
        resolved_worker_memory = (
            memory_limit
            if shell_count == 0
            else max(worker_peak, available_worker_pool // resolved_workers)
        )
        if self.worker_memory_bytes is not None:
            resolved_worker_memory = min(
                resolved_worker_memory, self.worker_memory_bytes
            )
            if shell_count > 0 and resolved_worker_memory < worker_peak:
                raise GraphComplexityError(
                    "worker_memory_bytes is below the estimated largest shell-worker "
                    f"peak ({resolved_worker_memory} < {worker_peak})."
                )
        return DensityMeshExecutionOptions(
            max_parallel_shell_workers=resolved_workers,
            worker_native_threads=native,
            worker_timeout_seconds=resolved_timeout,
            worker_memory_bytes=resolved_worker_memory,
            metadata={
                **self.metadata.to_json_dict(),
                "runtime_max_threads": thread_limit,
                "requested_native_threads_per_worker": requested_native,
                "native_threads_per_worker_clamped": requested_native > thread_limit,
                "thread_worker_cap": thread_worker_cap,
                "memory_worker_cap": memory_worker_cap,
                "shell_worker_cap": shell_worker_cap,
                "runtime_max_memory_bytes": memory_limit,
                "parent_retained_bytes": parent,
                "final_output_reserve_bytes": output_reserve,
                "available_worker_pool_bytes": max(0, available_worker_pool),
                "largest_worker_peak_bytes": worker_peak,
                "isolated_shell_count": shell_count,
                "remaining_wall_time_seconds": remaining,
                "wall_time_admission_enforced": False,
                "worker_count_clamped_by_threads": requested_workers > thread_worker_cap,
                "worker_count_clamped_by_memory": requested_workers > memory_worker_cap,
                "worker_count_clamped_by_shell_count": requested_workers > shell_worker_cap,
                "worker_timeout_clamped": False,
                "worker_timeout_source": (
                    "explicit" if requested_timeout is not None else "none"
                ),
            },
        )

    def resolved_worker_count(self, isolated_shell_count: int) -> int:
        count = _positive_int(
            isolated_shell_count, name="isolated_shell_count", minimum=0
        )
        if count <= 1:
            return 1
        if self.max_parallel_shell_workers is None:
            raise GraphAdapterError(
                "DensityMeshExecutionOptions must be resolved before scheduling."
            )
        return min(self.max_parallel_shell_workers, count)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_parallel_shell_workers": self.max_parallel_shell_workers,
            "worker_native_threads": self.worker_native_threads,
            "worker_timeout_seconds": self.worker_timeout_seconds,
            "worker_memory_bytes": self.worker_memory_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityMeshExecutionOptions":
        return cls(
            max_parallel_shell_workers=value.get("max_parallel_shell_workers"),
            worker_native_threads=value.get("worker_native_threads", 1),
            worker_timeout_seconds=value.get("worker_timeout_seconds"),
            worker_memory_bytes=value.get("worker_memory_bytes"),
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", DENSITY_MESH_EXECUTION_OPTIONS_SCHEMA
            ),
        )


@dataclass(frozen=True, slots=True)
class DensityMeshExecutionReport:
    """Auditable scheduling result for one complete scene."""

    isolated_shell_count: int
    parallel_worker_count: int
    wall_seconds: float
    sum_shell_seconds: float
    maximum_shell_seconds: float
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_MESH_EXECUTION_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_MESH_EXECUTION_REPORT_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-mesh execution report schema {self.schema_version!r}."
            )
        object.__setattr__(
            self,
            "isolated_shell_count",
            _positive_int(
                self.isolated_shell_count, name="isolated_shell_count", minimum=0
            ),
        )
        object.__setattr__(
            self,
            "parallel_worker_count",
            _positive_int(self.parallel_worker_count, name="parallel_worker_count"),
        )
        for name in ("wall_seconds", "sum_shell_seconds", "maximum_shell_seconds"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphStyleError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def parallel_efficiency(self) -> float:
        denominator = self.wall_seconds * self.parallel_worker_count
        if denominator <= 0.0:
            return 1.0
        return self.sum_shell_seconds / denominator

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "isolated_shell_count": self.isolated_shell_count,
            "parallel_worker_count": self.parallel_worker_count,
            "wall_seconds": self.wall_seconds,
            "sum_shell_seconds": self.sum_shell_seconds,
            "maximum_shell_seconds": self.maximum_shell_seconds,
            "parallel_efficiency": self.parallel_efficiency,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityMeshExecutionReport":
        return cls(
            isolated_shell_count=value["isolated_shell_count"],
            parallel_worker_count=value["parallel_worker_count"],
            wall_seconds=value["wall_seconds"],
            sum_shell_seconds=value["sum_shell_seconds"],
            maximum_shell_seconds=value["maximum_shell_seconds"],
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", DENSITY_MESH_EXECUTION_REPORT_SCHEMA
            ),
        )
