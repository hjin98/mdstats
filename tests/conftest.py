"""Shared deterministic resource fixtures for numerical plotting tests."""

from __future__ import annotations

from pathlib import Path

import pytest


_DENSITY_RESOURCE_MODULES = {
    "test_atomic_density.py",
    "test_framework_density.py",
    "test_framework_dynamics.py",
    "test_stage11e0a_density_facade.py",
    "test_stage_c0b_consumer_migration.py",
}


def _uses_density_runtime_fixture(path: Path) -> bool:
    return path.name.startswith("test_density_") or path.name in _DENSITY_RESOURCE_MODULES


@pytest.fixture(autouse=True)
def deterministic_density_runtime_budget(request):
    """Keep numerical density tests independent of transient host scarcity.

    Production code still probes and enforces the real runtime ceiling.  The
    dedicated runtime-resource tests are deliberately outside this fixture and
    continue to exercise detection, clamping, and nested budget semantics.
    """

    path = Path(str(request.fspath))
    if not _uses_density_runtime_fixture(path):
        yield
        return

    from mdstats import (
        RuntimeResourceSnapshot,
        density_resource_budget_scope,
        resolve_runtime_resource_budget,
    )

    memory = 128 * 1024**3
    snapshot = RuntimeResourceSnapshot(
        logical_cpu_count=16,
        affinity_cpu_count=8,
        cgroup_cpu_quota=None,
        scheduler_cpu_count=8,
        available_cpu_count=8,
        host_memory_available_bytes=memory,
        cgroup_memory_limit_bytes=memory,
        cgroup_memory_current_bytes=1,
        scheduler_memory_limit_bytes=memory,
        rlimit_as_bytes=None,
        process_rss_bytes=1,
        process_virtual_memory_bytes=1,
        available_memory_bytes=memory,
        metadata={"fixture": "deterministic_density_runtime"},
    )
    budget = resolve_runtime_resource_budget(
        max_memory_bytes=64 * 1024**3,
        max_threads=4,
        max_wall_time_seconds=1200.0,
        snapshot=snapshot,
        environment={},
    )
    with density_resource_budget_scope(budget):
        yield
