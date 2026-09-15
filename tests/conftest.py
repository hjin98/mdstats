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


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "real_target_order: reach prepare's real multi-view target-order owner instead of the "
        "below-claim downstream substitute",
    )


@pytest.fixture(autouse=True, scope="module")
def substitute_target_order_owner_for_downstream_campaign_tests(request):
    """Downstream MLFF campaign fixtures are far below the target-order method's scale.

    Their claims concern P2/P3/publication/post-selection behavior, not how
    ``pi_train`` is built, so ``prepare`` receives the deterministic substitute
    from ``tests/support/target_order_substitute.py``.  The substitute is
    module-scoped so module-scoped campaign fixtures receive it too.  Suites
    that claim the target-order chain itself opt out with a module-level
    ``pytestmark = pytest.mark.real_target_order``.
    """

    path = Path(str(request.fspath))
    if not path.name.startswith("test_mlff_") or request.node.get_closest_marker("real_target_order"):
        yield
        return
    from tests.support.target_order_substitute import substitute_prepare_target_order

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(
            "mdstats.training_data.campaign_target_size_runtime._build_current_target_training_order",
            substitute_prepare_target_order,
        )
        yield
