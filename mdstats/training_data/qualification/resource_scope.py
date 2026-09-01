"""Stable identity for the accepted execution-resource scope.

Resource pressure is an execution concern, not a scientific knob.  The
identity nevertheless belongs in performance/resource evidence: a result
obtained with a different CPU quota, resource fraction, selected accelerator,
or nested stage budget must not be presented as the same target-machine
qualification.  Volatile free-memory observations are intentionally excluded;
they constrain scheduling at execution time but do not make every numerical
record stale merely because another process consumed memory briefly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .._common import digest


RESOURCE_SCOPE_IDENTITY_SCHEMA = "mdstats.qualification-resource-scope.v1"


def _stable_ram_capacity_bytes() -> int | None:
    """Read a capacity limit, never instantaneous free memory."""

    try:
        value = Path("/sys/fs/cgroup/memory.max").read_text(encoding="utf-8").strip()
        if value != "max" and int(value) > 0:
            return int(value)
    except (OSError, ValueError):
        pass
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def resource_scope_payload(resources: Any, scope: Any) -> dict[str, Any]:
    """Return the nonvolatile resource/topology material bound by P7."""

    gpu = getattr(resources, "gpu", None)
    payload: dict[str, Any] = {
        "schema": RESOURCE_SCOPE_IDENTITY_SCHEMA,
        "resources": {
            "cpu_threads_available": int(resources.cpu_threads_available),
            "cpu_threads_budget": int(resources.cpu_threads_budget),
            "cpu_fraction": float(resources.cpu_fraction),
            "ram_fraction": float(resources.ram_fraction),
            # ``ram_available_bytes``/``ram_budget_bytes`` are pressure
            # observations and are intentionally not identity.  The stable
            # capacity and configured fraction still distinguish materially
            # different resource scopes.
            "ram_capacity_bytes": _stable_ram_capacity_bytes(),
            "gpu_memory_fraction": float(resources.gpu_memory_fraction),
            "gpu": {
                "available": bool(getattr(gpu, "available", False)),
                "device_count": int(getattr(gpu, "device_count", 0)),
                "selected_device": getattr(gpu, "selected_device", None),
                "device_name": getattr(gpu, "device_name", None),
                "total_bytes": getattr(gpu, "total_bytes", None),
                # Free VRAM is a volatile scheduler observation.  Bind only
                # the configured budget projected from stable device capacity.
                "budget_bytes": (
                    None
                    if getattr(gpu, "total_bytes", None) is None
                    else int(
                        int(getattr(gpu, "total_bytes"))
                        * float(resources.gpu_memory_fraction)
                    )
                ),
            },
        },
        # The resolved worker counts and nested-thread limits are included so a
        # measurement can be interpreted after restart.  They remain execution
        # scope material only: they never alter scientific membership, thresholds,
        # timestep, precision, or model-selection decisions.
        "stage": {
            "stage_name": str(scope.stage_name),
            "cpu_threads_available": int(scope.cpu_threads_available),
            "cpu_threads_budget": int(scope.cpu_threads_budget),
            "python_workers": int(scope.python_workers),
            "structural_workers": int(scope.structural_workers),
            "tree_workers": int(scope.tree_workers),
            "blas_threads": int(scope.blas_threads),
            "native_openmp_threads": int(scope.native_openmp_threads),
            "pytorch_cpu_workers": int(scope.pytorch_cpu_workers),
            "gpu_jobs": int(scope.gpu_jobs),
            "estimated_nested_cpu_threads": int(scope.estimated_nested_cpu_threads),
            "ram_budget_configured_bytes": (
                None
                if _stable_ram_capacity_bytes() is None
                else int(_stable_ram_capacity_bytes() * float(resources.ram_fraction))
            ),
        },
    }
    return payload


def resource_scope_digest(resources: Any, scope: Any) -> str:
    """Content identity of one accepted execution-resource scope."""

    return digest(resource_scope_payload(resources, scope))


__all__ = [
    "RESOURCE_SCOPE_IDENTITY_SCHEMA",
    "resource_scope_digest",
    "resource_scope_payload",
]
