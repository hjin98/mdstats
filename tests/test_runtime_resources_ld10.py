"""LD10 runtime-derived resource policy tests."""
from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path

import numpy as np
import pytest

# The source distribution declares ASE as a dependency, but the constrained
# release-validation container does not provide it.  Load only the plotting
# package under a namespace stub so these resource-policy tests remain isolated
# from unrelated parser imports.  Normal installed-package runs take the usual
# import path.
if importlib.util.find_spec("ase") is None:
    root = Path(__file__).resolve().parents[1]
    mdstats_pkg = types.ModuleType("mdstats")
    mdstats_pkg.__path__ = [str(root / "mdstats")]
    plotting_pkg = types.ModuleType("mdstats.plotting")
    plotting_pkg.__path__ = [str(root / "mdstats" / "plotting")]
    sys.modules.setdefault("mdstats", mdstats_pkg)
    sys.modules.setdefault("mdstats.plotting", plotting_pkg)

runtime_resources = importlib.import_module("mdstats.plotting.runtime_resources")
contracts = importlib.import_module("mdstats.plotting.density_contracts")
mesh_execution = importlib.import_module("mdstats.plotting.density_mesh_execution")
density_planning = importlib.import_module("mdstats.plotting.density_planning")
graph_errors = importlib.import_module("mdstats.plotting.graph_errors")
tiled_fft = importlib.import_module("mdstats.plotting.density_tiled_fft")

DensityTimeModel = runtime_resources.DensityTimeModel
RuntimeResourceSnapshot = runtime_resources.RuntimeResourceSnapshot
derive_density_numeric_limits = runtime_resources.derive_density_numeric_limits
parse_byte_quantity = runtime_resources.parse_byte_quantity
probe_runtime_resources = runtime_resources.probe_runtime_resources
resolve_density_resource_limits = runtime_resources.resolve_density_resource_limits
resolve_runtime_resource_budget = runtime_resources.resolve_runtime_resource_budget
density_resource_budget_scope = runtime_resources.density_resource_budget_scope
active_density_resource_budget = runtime_resources.active_density_resource_budget
density_time_model_scope = runtime_resources.density_time_model_scope
active_density_time_model = runtime_resources.active_density_time_model
DensityOptimizationOptions = contracts.DensityOptimizationOptions
DensityRenderOptions = contracts.DensityRenderOptions
DensityMeshExecutionOptions = mesh_execution.DensityMeshExecutionOptions
DensityPlanningLimits = density_planning.DensityPlanningLimits
GraphComplexityError = graph_errors.GraphComplexityError
DensityHybridExecutorOptions = tiled_fft.DensityHybridExecutorOptions


def snapshot(*, cpus: int = 16, memory: int = 10 * 1024**3) -> RuntimeResourceSnapshot:
    return RuntimeResourceSnapshot(
        logical_cpu_count=max(cpus, 32),
        affinity_cpu_count=cpus,
        cgroup_cpu_quota=None,
        scheduler_cpu_count=cpus,
        available_cpu_count=cpus,
        host_memory_available_bytes=memory,
        cgroup_memory_limit_bytes=memory,
        cgroup_memory_current_bytes=1,
        scheduler_memory_limit_bytes=memory,
        rlimit_as_bytes=None,
        process_rss_bytes=1,
        process_virtual_memory_bytes=1,
        available_memory_bytes=memory,
        metadata={"fixture": True},
    )


def static_model(*, threads: int = 12) -> DensityTimeModel:
    return DensityTimeModel(
        calibration_threads=threads,
        calibration_source="unit_test",
    )


def test_default_budget_uses_ninety_percent_cpu_and_eighty_percent_memory() -> None:
    detected = snapshot(cpus=16, memory=10 * 1024**3)
    budget = resolve_runtime_resource_budget(snapshot=detected, environment={})
    assert budget.max_threads == 14
    assert budget.max_memory_bytes == int(0.8 * 10 * 1024**3)
    assert budget.max_wall_time_seconds == 1200.0
    assert budget.thread_override_source == "runtime_fraction"
    assert budget.memory_override_source == "runtime_fraction"


def test_user_overrides_are_clamped_to_actual_runtime_ceiling() -> None:
    detected = snapshot(cpus=8, memory=4 * 1024**3)
    budget = resolve_runtime_resource_budget(
        max_threads=64,
        max_memory_bytes="32GiB",
        max_wall_time_seconds=1800.0,
        snapshot=detected,
        environment={},
    )
    assert budget.max_threads == 8
    assert budget.max_memory_bytes == 4 * 1024**3
    assert budget.max_wall_time_seconds == 1800.0
    assert budget.thread_override_clamped
    assert budget.memory_override_clamped


def test_environment_overrides_are_auditable() -> None:
    detected = snapshot(cpus=16, memory=10 * 1024**3)
    budget = resolve_runtime_resource_budget(
        snapshot=detected,
        environment={
            "MDSTATS_MAX_THREADS": "6",
            "MDSTATS_MAX_MEMORY_BYTES": "3GiB",
            "MDSTATS_MAX_WALL_TIME_SECONDS": "900",
        },
    )
    assert budget.max_threads == 6
    assert budget.max_memory_bytes == 3 * 1024**3
    assert budget.max_wall_time_seconds == 900.0
    assert budget.thread_override_source == "MDSTATS_MAX_THREADS"
    assert budget.memory_override_source == "MDSTATS_MAX_MEMORY_BYTES"
    assert budget.wall_time_override_source == "MDSTATS_MAX_WALL_TIME_SECONDS"


def test_runtime_probe_is_not_cached_and_sees_new_memory_headroom(monkeypatch) -> None:
    values = iter((8 * 1024**3, 4 * 1024**3))
    monkeypatch.setattr(runtime_resources, "_proc_memory_available", lambda: next(values))
    monkeypatch.setattr(runtime_resources, "_proc_process_memory", lambda: (1, 1))
    monkeypatch.setattr(runtime_resources, "_cgroup_memory", lambda: (None, None, None))
    monkeypatch.setattr(runtime_resources, "_scheduler_memory_limit", lambda *a, **k: (None, None))
    monkeypatch.setattr(runtime_resources, "_rlimit_as_headroom", lambda _virtual: (None, None))
    monkeypatch.setattr(runtime_resources, "_cgroup_cpu_quota", lambda: (None, None))
    monkeypatch.setattr(runtime_resources, "_scheduler_cpu_limit", lambda _env: (None, None))
    monkeypatch.setattr(runtime_resources.os, "cpu_count", lambda: 8)
    monkeypatch.setattr(runtime_resources.os, "sched_getaffinity", lambda _pid: set(range(8)))
    first = probe_runtime_resources()
    second = probe_runtime_resources()
    assert first.available_memory_bytes == 8 * 1024**3
    assert second.available_memory_bytes == 4 * 1024**3


def test_numeric_guards_scale_with_runtime_budget_not_fixture_geometry() -> None:
    small = resolve_runtime_resource_budget(
        snapshot=snapshot(cpus=8, memory=2 * 1024**3), environment={}
    )
    large = resolve_runtime_resource_budget(
        snapshot=snapshot(cpus=32, memory=16 * 1024**3), environment={}
    )
    small_limits = derive_density_numeric_limits(
        budget=small, time_model=static_model(threads=small.max_threads)
    )
    large_limits = derive_density_numeric_limits(
        budget=large, time_model=static_model(threads=large.max_threads)
    )
    assert large_limits["max_density_voxels"] == 8 * small_limits["max_density_voxels"]
    assert large_limits["max_density_mesh_faces"] == 8 * small_limits["max_density_mesh_faces"]
    assert abs(
        large_limits["max_density_total_peak_bytes"]
        - 8 * small_limits["max_density_total_peak_bytes"]
    ) <= 8


def test_legacy_count_limit_ignores_time_ceiling() -> None:
    short = runtime_resources.derive_count_limit(
        memory_bytes=1024, bytes_per_item=8, time_seconds=1.0e-9, items_per_second=1.0
    )
    long = runtime_resources.derive_count_limit(
        memory_bytes=1024, bytes_per_item=8, time_seconds=1.0e9, items_per_second=1.0e12
    )
    assert short == long == 128


def test_wall_time_target_does_not_scale_operation_caps() -> None:
    detected = snapshot(cpus=16, memory=8 * 1024**3)
    short = resolve_runtime_resource_budget(
        max_wall_time_seconds=300, snapshot=detected, environment={}
    )
    long = resolve_runtime_resource_budget(
        max_wall_time_seconds=1200, snapshot=detected, environment={}
    )
    model = static_model(threads=short.max_threads)
    short_limits = derive_density_numeric_limits(budget=short, time_model=model)
    long_limits = derive_density_numeric_limits(budget=long, time_model=model)
    assert long_limits["max_density_kernel_pairs"] == short_limits["max_density_kernel_pairs"]
    assert long_limits["max_density_fields"] == short_limits["max_density_fields"]
    assert short_limits["max_density_kernel_pairs"] == np.iinfo(np.int64).max


def test_coherent_resolver_uses_one_injected_snapshot() -> None:
    detected = snapshot(cpus=20, memory=5 * 1024**3)
    budget, model, limits = resolve_density_resource_limits(
        snapshot=detected,
        environment={},
        time_model=static_model(threads=16),
    )
    assert budget.max_threads == 18
    assert budget.max_memory_bytes == 4 * 1024**3
    assert model.calibration_source == "unit_test"
    assert limits["max_density_total_peak_bytes"] == budget.max_memory_bytes


def test_optimization_resolution_uses_the_supplied_scene_budget() -> None:
    scene_budget = resolve_runtime_resource_budget(
        max_threads=3,
        max_memory_bytes="256MiB",
        max_wall_time_seconds=90,
        snapshot=snapshot(cpus=16, memory=2 * 1024**3),
        environment={},
    )
    resolved = DensityOptimizationOptions(
        sparse_pair_chunk_size=10**9,
        hybrid_fft_workers=64,
    ).resolve(runtime_budget=scene_budget)
    assert resolved.hybrid_fft_workers == 3
    assert resolved.sparse_pair_chunk_size < 10**9
    assert resolved.metadata["runtime_max_memory_bytes"] == 256 * 1024**2
    assert resolved.metadata["runtime_max_threads"] == 3
    assert resolved.metadata["runtime_max_wall_time_seconds"] == 90


def test_legacy_low_level_limits_cannot_relax_primary_budget(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_resources,
        "probe_runtime_resources",
        lambda: snapshot(cpus=8, memory=512 * 1024**2),
    )
    limits = DensityPlanningLimits(
        max_density_voxels=10**18,
        max_density_kernel_pairs=10**18,
        max_density_total_peak_bytes=10**18,
        max_density_threads=10**6,
        max_density_wall_time_seconds=120.0,
        time_model=static_model(threads=8),
    )
    assert limits.max_density_total_peak_bytes == 512 * 1024**2
    assert limits.max_density_threads == 8
    assert limits.max_density_voxels < 10**18
    # Operation-only expert caps are no longer tightened from wall time.
    assert limits.max_density_kernel_pairs == 10**18


def test_worker_count_is_limited_by_memory_as_well_as_cpu() -> None:
    options = DensityMeshExecutionOptions().resolve(
        max_threads=16,
        remaining_wall_time_seconds=1200.0,
        max_memory_bytes=8 * 1024**3,
        parent_retained_bytes=2 * 1024**3,
        final_output_reserve_bytes=1 * 1024**3,
        largest_worker_peak_bytes=1 * 1024**3,
        isolated_shell_count=12,
    )
    assert options.max_parallel_shell_workers == 5
    assert options.worker_memory_bytes == 1 * 1024**3
    assert options.metadata["memory_worker_cap"] == 5
    assert options.metadata["worker_count_clamped_by_memory"] is True
    assert options.worker_timeout_seconds is None
    assert options.metadata["wall_time_admission_enforced"] is False



def test_explicit_worker_timeout_is_not_clamped_by_scene_wall_target() -> None:
    options = DensityMeshExecutionOptions(worker_timeout_seconds=3600.0).resolve(
        max_threads=4,
        remaining_wall_time_seconds=1.0,
        max_memory_bytes=2 * 1024**3,
        parent_retained_bytes=256 * 1024**2,
        final_output_reserve_bytes=256 * 1024**2,
        largest_worker_peak_bytes=256 * 1024**2,
        isolated_shell_count=2,
    )
    assert options.worker_timeout_seconds == 3600.0
    assert options.metadata["worker_timeout_clamped"] is False
    assert options.metadata["wall_time_admission_enforced"] is False


def test_worker_native_threads_cannot_exceed_scene_thread_budget() -> None:
    options = DensityMeshExecutionOptions(worker_native_threads=32).resolve(
        max_threads=6,
        remaining_wall_time_seconds=1200.0,
        max_memory_bytes=8 * 1024**3,
        parent_retained_bytes=2 * 1024**3,
        final_output_reserve_bytes=1 * 1024**3,
        largest_worker_peak_bytes=512 * 1024**2,
        isolated_shell_count=4,
    )
    assert options.worker_native_threads == 6
    assert options.max_parallel_shell_workers == 1
    assert options.metadata["native_threads_per_worker_clamped"]

def test_worker_resolution_rejects_scene_without_one_worker_headroom() -> None:
    with pytest.raises(GraphComplexityError, match="insufficient scene memory"):
        DensityMeshExecutionOptions().resolve(
            max_threads=16,
            remaining_wall_time_seconds=1200.0,
            max_memory_bytes=4 * 1024**3,
            parent_retained_bytes=3 * 1024**3,
            final_output_reserve_bytes=768 * 1024**2,
            largest_worker_peak_bytes=512 * 1024**2,
            isolated_shell_count=2,
        )


def test_low_level_optimization_defaults_follow_runtime_env(monkeypatch) -> None:
    monkeypatch.setenv("MDSTATS_MAX_THREADS", "2")
    monkeypatch.setenv("MDSTATS_MAX_MEMORY_BYTES", "128MiB")
    unresolved = DensityOptimizationOptions()
    assert unresolved.hybrid_fft_workers is None
    assert unresolved.sparse_pair_chunk_size is None
    options = unresolved.resolve()
    assert options.hybrid_fft_workers <= 2
    assert options.sparse_pair_chunk_size >= 4096
    assert options.metadata["resource_policy"] == "runtime_derived_v2"
    assert options.metadata["sparse_pair_chunk_source"] == "runtime_memory_per_thread"
    assert options.metadata["hybrid_fft_workers_source"] == "runtime_thread_budget"



def test_hybrid_executor_serialized_controls_cannot_relax_active_budget() -> None:
    scene_budget = resolve_runtime_resource_budget(
        max_threads=2,
        max_memory_bytes="64MiB",
        max_wall_time_seconds=60,
        snapshot=snapshot(cpus=8, memory=1024**3),
        environment={},
    )
    model = static_model(threads=2)
    with density_resource_budget_scope(scene_budget):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                tiled_fft,
                "resolve_density_resource_limits",
                lambda *args, **kwargs: (
                    scene_budget,
                    model,
                    derive_density_numeric_limits(
                        budget=scene_budget, time_model=model
                    ),
                ),
            )
            options = DensityHybridExecutorOptions(
                pair_chunk_size=10**9,
                fft_workers=64,
                direct_pair_seconds=1.0e-30,
                fft_work_seconds=1.0e-30,
                fft_fixed_seconds=0.0,
            )
    assert options.fft_workers == 2
    assert options.pair_chunk_size < 10**9
    assert options.direct_pair_seconds >= 1.0 / model.kernel_pairs_per_second
    assert options.fft_fixed_seconds >= model.fixed_seconds_per_field
    assert options.metadata["timing_overrides_are_tightening_only"]

def test_browser_geometry_profile_is_separate_from_host_budget(monkeypatch) -> None:
    monkeypatch.setenv("MDSTATS_MAX_MEMORY_BYTES", "128MiB")
    monkeypatch.setenv("MDSTATS_MAX_THREADS", "2")
    render = DensityRenderOptions()
    assert render.max_mesh_faces == 250_000
    assert render.cloud_max_points == 40_000



def test_active_scene_budget_is_inherited_without_double_fraction() -> None:
    scene_budget = resolve_runtime_resource_budget(
        max_threads=10,
        max_memory_bytes="1GiB",
        max_wall_time_seconds=600,
        snapshot=snapshot(cpus=16, memory=4 * 1024**3),
        environment={},
    )
    assert active_density_resource_budget() is None
    with density_resource_budget_scope(scene_budget):
        inherited = resolve_runtime_resource_budget()
        assert inherited.max_memory_bytes == 1024**3
        assert inherited.max_threads == 10
        assert inherited.max_wall_time_seconds == 600.0
        assert inherited.memory_override_source == "active_scene_budget"
        assert inherited.thread_override_source == "active_scene_budget"
        assert inherited.wall_time_override_source == "active_scene_budget"
        assert inherited.snapshot is scene_budget.snapshot


def test_active_scene_budget_allows_only_tightening_overrides() -> None:
    scene_budget = resolve_runtime_resource_budget(
        max_threads=8,
        max_memory_bytes="1GiB",
        max_wall_time_seconds=600,
        snapshot=snapshot(cpus=16, memory=4 * 1024**3),
        environment={},
    )
    with density_resource_budget_scope(scene_budget):
        tightened = resolve_runtime_resource_budget(
            max_threads=3,
            max_memory_bytes="256MiB",
            max_wall_time_seconds=90,
        )
        assert tightened.max_threads == 3
        assert tightened.max_memory_bytes == 256 * 1024**2
        assert tightened.max_wall_time_seconds == 90.0
        relaxed = resolve_runtime_resource_budget(
            max_threads=64,
            max_memory_bytes="64GiB",
            max_wall_time_seconds=3600,
        )
        assert relaxed.max_threads == scene_budget.max_threads
        assert relaxed.max_memory_bytes == scene_budget.max_memory_bytes
        assert relaxed.max_wall_time_seconds == scene_budget.max_wall_time_seconds
        assert relaxed.thread_override_clamped
        assert relaxed.memory_override_clamped


def test_active_scene_budget_scope_restores_outer_context() -> None:
    outer = resolve_runtime_resource_budget(
        max_threads=8,
        max_memory_bytes="1GiB",
        max_wall_time_seconds=600,
        snapshot=snapshot(cpus=16, memory=4 * 1024**3),
        environment={},
    )
    inner = resolve_runtime_resource_budget(
        max_threads=2,
        max_memory_bytes="128MiB",
        max_wall_time_seconds=30,
        snapshot=snapshot(cpus=16, memory=4 * 1024**3),
        environment={},
    )
    with density_resource_budget_scope(outer):
        assert active_density_resource_budget() is outer
        with density_resource_budget_scope(inner):
            assert active_density_resource_budget() is inner
        assert active_density_resource_budget() is outer
    assert active_density_resource_budget() is None



def test_active_density_time_model_prevents_nested_recalibration(monkeypatch) -> None:
    scene_budget = resolve_runtime_resource_budget(
        max_threads=8,
        max_memory_bytes="1GiB",
        max_wall_time_seconds=600,
        snapshot=snapshot(cpus=16, memory=4 * 1024**3),
        environment={},
    )
    model = static_model(threads=8)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("nested production density code recalibrated the time model")

    monkeypatch.setattr(runtime_resources, "calibrate_density_time_model", forbidden)
    assert active_density_time_model() is None
    with density_resource_budget_scope(scene_budget), density_time_model_scope(model):
        budget, inherited, limits = resolve_density_resource_limits()
        assert budget.max_threads == scene_budget.max_threads
        assert budget.max_memory_bytes == scene_budget.max_memory_bytes
        assert inherited is model
        assert limits["max_density_voxels"] > 0
        assert active_density_time_model() is model
    assert active_density_time_model() is None
    assert calls == []

def test_memory_quantity_parser_is_explicit_about_units() -> None:
    assert parse_byte_quantity("1GiB") == 1024**3
    assert parse_byte_quantity("1GB") == 1000**3
    assert parse_byte_quantity(4096) == 4096
    with pytest.raises(Exception, match="Invalid memory quantity"):
        parse_byte_quantity("many")


def test_scheduler_memory_uses_most_restrictive_declared_limit() -> None:
    value, source = runtime_resources._scheduler_memory_limit(
        {
            "SLURM_MEM_PER_NODE": "8192",  # MiB by Slurm convention
            "PBS_VMEM": "6GiB",
            "PBS_RESC_MEM": "7GiB",
        },
        scheduler_cpu_count=8,
    )
    assert value == 6 * 1024**3
    assert source == "PBS_VMEM"


def test_standalone_calibration_cannot_oversubscribe_runtime(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_resources,
        "probe_runtime_resources",
        lambda: snapshot(cpus=6, memory=2 * 1024**3),
    )
    captured: dict[str, int] = {}

    def fake_cached(threads: int, disabled: bool) -> DensityTimeModel:
        captured["threads"] = threads
        return static_model(threads=threads)

    monkeypatch.setattr(
        runtime_resources, "_calibrate_density_time_model_cached", fake_cached
    )
    model = runtime_resources.calibrate_density_time_model(max_threads=128)
    assert captured["threads"] == 6
    assert model.calibration_threads == 6
