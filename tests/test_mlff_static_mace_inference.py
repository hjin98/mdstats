from __future__ import annotations

import numpy as np
import pytest
from ase import Atoms

from mdstats.training_data.model_features import (
    AtomicModelPrediction,
    StaticInferenceOperatingPointEvidence,
    StaticInferenceRuntimeAuthority,
    StaticInferenceRuntimeProfile,
    StaticMaceInferenceExecutor,
)
from mdstats.training_data._common import digest
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
)


def _atoms(count: int = 9):
    return tuple(
        Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.7 + index * 0.01]])
        for index in range(count)
    )


class _Provider:
    def __init__(self, maximum_batch: int = 100):
        self.maximum_batch = maximum_batch
        self.calls = []

    def predict_batch(self, atoms, *, geometry_identities=None, graph_cache_directory=None):
        self.calls.append((len(atoms), None if geometry_identities is None else tuple(geometry_identities)))
        if len(atoms) > self.maximum_batch:
            raise RuntimeError("CUDA out of memory")
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(value.positions[1, 2]),
                forces_ev_per_angstrom=np.full((2, 3), value.positions[1, 2]),
                stress_ev_per_angstrom3=np.eye(3) * value.positions[1, 2],
            )
            for value in atoms
        )


def test_static_executor_batch_matches_batch_one_reference_and_preserves_order() -> None:
    atoms = _atoms()
    reference = StaticMaceInferenceExecutor(_Provider(), batch_size=1).prediction_channels(atoms)
    provider = _Provider()
    observed = StaticMaceInferenceExecutor(provider, batch_size=4).prediction_channels(
        atoms, geometry_identities=tuple(f"g{index}" for index in range(len(atoms)))
    )
    for channel in reference:
        np.testing.assert_allclose(observed[channel], reference[channel], rtol=0.0, atol=0.0)
    assert provider.calls == [(4, ("g0", "g1", "g2", "g3")), (4, ("g4", "g5", "g6", "g7")), (1, ("g8",))]


def test_static_executor_oom_backoff_is_bounded_and_retains_safe_ceiling() -> None:
    provider = _Provider(maximum_batch=2)
    executor = StaticMaceInferenceExecutor(provider, batch_size=8, maximum_oom_backoffs=4)
    predictions = executor.predict(_atoms())
    assert len(predictions) == 9
    assert executor.oom_backoff_count == 2
    assert executor.learned_safe_batch_size == 2
    assert [size for size, _ in provider.calls] == [8, 4, 2, 2, 2, 2, 1]


def test_static_executor_surfaces_batch_one_oom() -> None:
    executor = StaticMaceInferenceExecutor(_Provider(maximum_batch=0), batch_size=2)
    with pytest.raises(RuntimeError, match="out of memory"):
        executor.predict(_atoms(1))


def test_static_executor_prohibits_concurrent_model_shell_sharing() -> None:
    import threading

    entered = threading.Event()
    release = threading.Event()

    class BlockingProvider(_Provider):
        def predict_batch(self, atoms, **kwargs):
            entered.set()
            release.wait(timeout=2.0)
            return super().predict_batch(atoms, **kwargs)

    executor = StaticMaceInferenceExecutor(BlockingProvider(), batch_size=1)
    worker = threading.Thread(target=lambda: executor.predict(_atoms(1)))
    worker.start()
    assert entered.wait(timeout=1.0)
    with pytest.raises(TrainingDataInputError, match="cannot be shared"):
        executor.predict(_atoms(1))
    release.set()
    worker.join(timeout=2.0)
    assert not worker.is_alive()


def _authority(*, profile=None, ram=20_000, vram=20_000, compatibility=None):
    return StaticInferenceRuntimeAuthority(
        compatibility_digest=compatibility or digest({"fixture": "joint-static"}),
        maximum_batch_size=32,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=ram,
        live_vram_budget_bytes=vram,
        compatible_profile=profile,
    )


def _measured_point(batch, jobs, throughput, ram, vram):
    completed = batch * jobs
    return StaticInferenceOperatingPointEvidence(
        batch,
        jobs,
        throughput,
        ram,
        vram,
        completed_structures=completed,
        elapsed_seconds=completed / throughput,
        observed_max_active_jobs=jobs,
        provider_pool_resident_ram_bytes=0,
        provider_pool_resident_vram_bytes=None if vram is None else 0,
        execution_peak_ram_bytes=ram,
        execution_peak_vram_bytes=vram,
    )


def test_joint_runtime_authority_selects_best_safe_near_equivalent_point() -> None:
    authority = _authority(vram=10_000)
    points = (
        _measured_point(8, 1, 100.0, 2_000, 4_000),
        _measured_point(16, 1, 104.0, 3_000, 7_000),
        _measured_point(8, 2, 103.0, 4_000, 9_000),
        _measured_point(16, 2, 120.0, 5_000, 15_000),
    )
    for point in points:
        authority.record(point)

    # The unsafe fastest point is excluded. The 100/s point is within 5% of
    # the safe 104/s peak and wins on lower aggregate resource demand.
    assert authority.selected_point == points[0]


def test_executor_auto_search_exercises_geometric_batches_above_eight() -> None:
    provider = _Provider()
    authority = _authority(ram=1 << 30, vram=None)
    executor = StaticMaceInferenceExecutor(
        provider,
        batch_size=32,
        runtime_authority=authority,
        concurrent_model_jobs=2,
    )

    predictions = executor.predict(_atoms(64))

    assert len(predictions) == 64
    assert [size for size, _ in provider.calls[:3]] == [8, 16, 32]
    # A serial executor is evidence for J=1 only; configured outer concurrency
    # must never be used as a synthetic throughput/evidence multiplier.
    assert {point.concurrent_model_jobs for point in authority.evidence} == {1}


def test_joint_executor_selects_only_actually_executed_fastest_point() -> None:
    import time

    class TimedProvider(_Provider):
        lock = __import__("threading").Lock()
        active = 0

        def predict_batch(self, atoms, **kwargs):
            with self.lock:
                type(self).active += 1
            try:
                time.sleep(0.005)
                with self.lock:
                    concurrent = type(self).active
                delay = 0.02 if len(atoms) == 8 and concurrent >= 2 else 0.20
                time.sleep(delay)
                return super().predict_batch(atoms, **kwargs)
            finally:
                with self.lock:
                    type(self).active -= 1

        def close(self):
            pass

    authority = _authority(ram=1 << 30, vram=None)
    executor = StaticMaceInferenceExecutor(
        TimedProvider(),
        batch_size=32,
        runtime_authority=authority,
        provider_factory=TimedProvider,
    )

    observed = executor.predict(_atoms(64))

    assert len(observed) == 64
    assert authority.selected_point is not None
    assert (authority.selected_point.batch_size, authority.selected_point.concurrent_model_jobs) == (8, 2)
    joint = next(
        point for point in authority.evidence
        if (point.batch_size, point.concurrent_model_jobs) == (8, 2)
    )
    assert joint.observed_max_active_jobs == 2
    assert joint.structures_per_second == pytest.approx(
        joint.completed_structures / joint.elapsed_seconds
    )
    np.testing.assert_allclose(
        [value.energy_ev for value in observed],
        [value.positions[1, 2] for value in _atoms(64)],
        rtol=0.0,
        atol=0.0,
    )


def test_joint_executor_can_select_batch_above_eight_when_really_faster() -> None:
    import time

    class FixedCostProvider(_Provider):
        def predict_batch(self, atoms, **kwargs):
            time.sleep(0.01)
            return super().predict_batch(atoms, **kwargs)

        def close(self):
            pass

    authority = _authority(ram=1 << 30, vram=None)
    StaticMaceInferenceExecutor(
        FixedCostProvider(), batch_size=32, runtime_authority=authority,
        provider_factory=FixedCostProvider,
    ).predict(_atoms(64))

    assert authority.selected_point is not None
    assert authority.selected_point.batch_size > 8


def test_joint_executor_keeps_one_job_when_second_private_model_is_slower() -> None:
    import time

    created = 0

    class AsymmetricProvider(_Provider):
        def __init__(self):
            nonlocal created
            super().__init__()
            self.delay = 0.004 if created == 0 else 0.08
            created += 1

        def predict_batch(self, atoms, **kwargs):
            time.sleep(self.delay)
            return super().predict_batch(atoms, **kwargs)

        def close(self):
            pass

    base = AsymmetricProvider()
    authority = _authority(ram=1 << 30, vram=None)
    StaticMaceInferenceExecutor(
        base, batch_size=32, runtime_authority=authority,
        provider_factory=AsymmetricProvider,
    ).predict(_atoms(64))

    assert authority.selected_point is not None
    assert authority.selected_point.concurrent_model_jobs == 1


def test_joint_executor_reuses_persistent_private_provider_pool_across_waves() -> None:
    import time

    created = 0
    closed = 0

    class Provider(_Provider):
        def __init__(self, *, private=False):
            nonlocal created
            super().__init__()
            self.private = private
            if private:
                created += 1

        def predict_batch(self, atoms, **kwargs):
            time.sleep(0.004)
            return super().predict_batch(atoms, **kwargs)

        def close(self):
            nonlocal closed
            if self.private:
                closed += 1
                self.private = False

    authority = _authority(ram=1 << 30, vram=None)
    executor = StaticMaceInferenceExecutor(
        Provider(), batch_size=32, runtime_authority=authority,
        provider_factory=lambda: Provider(private=True),
    )

    executor.predict(_atoms(64))
    assert authority.selected_point is not None
    assert authority.selected_point.concurrent_model_jobs == 2
    assert created == 1
    executor.predict(_atoms(64))
    assert created == 1
    assert executor.resident_provider_pool_size == 2
    executor.close()
    assert closed == 1


def test_resource_limited_private_pool_growth_retains_lower_safe_point() -> None:
    import time

    created = 0
    closed = 0

    class Provider(_Provider):
        def __init__(self, private=False):
            nonlocal created
            super().__init__()
            self.private = private
            if private:
                created += 1

        def predict_batch(self, atoms, **kwargs):
            time.sleep(0.003)
            return super().predict_batch(atoms, **kwargs)

        def close(self):
            nonlocal closed
            if self.private:
                closed += 1
                self.private = False

    def factory():
        if created >= 2:
            raise RuntimeError("CUDA out of memory while materializing provider")
        return Provider(private=True)

    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "pool-growth-oom"}),
        maximum_batch_size=32,
        maximum_concurrent_model_jobs=4,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
    )
    executor = StaticMaceInferenceExecutor(
        Provider(), batch_size=32, runtime_authority=authority, provider_factory=factory,
    )

    assert len(executor.predict(_atoms(128))) == 128
    assert any(
        point.concurrent_model_jobs == 4 and point.failure_kind == "provider-pool-oom"
        for point in authority.evidence
    )
    assert authority.selected_point is not None
    assert authority.selected_point.concurrent_model_jobs <= 2
    # The partially grown third private slot was closed; a retained lower pool
    # remains usable until the executor is retired.
    assert closed >= 1
    executor.close()
    assert closed == created


def test_joint_resource_evidence_covers_all_private_model_residency(
    monkeypatch,
) -> None:
    from mdstats.training_data import model_features

    class ResidencyProvider(_Provider):
        live_clones = 0

        def __init__(self, clone=False):
            super().__init__()
            self.clone = clone
            if clone:
                type(self).live_clones += 1

        def close(self):
            if self.clone:
                type(self).live_clones -= 1
                self.clone = False

    class ResidencyMonitor:
        def __init__(self, device):
            pass

        def start(self):
            pass

        def finish(self):
            return 10 + 100 * ResidencyProvider.live_clones, None

    monkeypatch.setattr(model_features, "_StaticInferenceResourceMonitor", ResidencyMonitor)
    authority = _authority(ram=1 << 30, vram=None)
    executor = StaticMaceInferenceExecutor(
        ResidencyProvider(),
        batch_size=32,
        runtime_authority=authority,
        provider_factory=lambda: ResidencyProvider(clone=True),
    )
    executor.predict(_atoms(64))

    single = next(
        point for point in authority.evidence
        if (point.batch_size, point.concurrent_model_jobs) == (8, 1)
    )
    joint = next(
        point for point in authority.evidence
        if (point.batch_size, point.concurrent_model_jobs) == (8, 2)
    )
    assert joint.peak_ram_bytes > single.peak_ram_bytes
    assert joint.provider_pool_resident_ram_bytes > 0
    assert joint.execution_peak_ram_bytes > 0
    assert joint.peak_ram_bytes == (
        joint.provider_pool_resident_ram_bytes + joint.execution_peak_ram_bytes
    )
    executor.close()
    assert ResidencyProvider.live_clones == 0


def test_live_resource_shrink_blocks_private_pool_growth_before_factory(monkeypatch) -> None:
    from mdstats.training_data import resources

    authority = _authority(ram=1 << 30, vram=None)
    for batch in authority.candidate_batch_sizes:
        authority.record(_measured_point(batch, 1, 1.0, 100, None))
    created = 0

    def factory():
        nonlocal created
        created += 1
        return _Provider()

    # J=1 remains admissible, but its measured envelope makes the first J=2
    # growth inadmissible.  The factory must not be entered for that rejected
    # material transition.
    monkeypatch.setattr(resources, "available_memory_bytes", lambda: 150)
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=32, runtime_authority=authority,
        provider_factory=factory,
    )
    assert len(executor.predict(_atoms(64))) == 64
    assert created == 0


def test_serial_executor_records_point_local_ram_delta_not_process_high_water(
    monkeypatch,
) -> None:
    from mdstats.training_data import model_features

    samples = iter((10_000, 10_000, 12_500, 12_500))
    monkeypatch.setattr(
        model_features,
        "_current_process_rss_bytes",
        lambda: next(samples, 12_500),
    )
    authority = _authority(vram=None)
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=1, runtime_authority=authority
    )

    executor.predict(_atoms(1))

    assert authority.evidence[0].peak_ram_bytes == 2_500


def test_measured_batch_one_resource_breach_blocks_all_replacement_work(
    monkeypatch,
) -> None:
    from mdstats.training_data import model_features

    class UnsafeMonitor:
        def __init__(self, device):
            pass

        def start(self):
            pass

        def finish(self):
            return 100, None

    monkeypatch.setattr(model_features, "_StaticInferenceResourceMonitor", UnsafeMonitor)
    provider = _Provider()
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "one-job-unsafe"}),
        maximum_batch_size=1,
        maximum_concurrent_model_jobs=1,
        live_ram_budget_bytes=10,
        live_vram_budget_bytes=None,
        cold_start_batch_size=1,
    )
    executor = StaticMaceInferenceExecutor(
        provider, batch_size=1, runtime_authority=authority
    )

    with pytest.raises(TrainingDataInputError, match="no future prediction"):
        executor.predict(_atoms(2))

    assert len(provider.calls) == 1


def test_cuda_resource_monitor_retains_transient_live_peak(monkeypatch) -> None:
    import time

    from mdstats.training_data import model_features, training_parallel
    from mdstats.training_data.training_parallel import GpuTelemetrySample

    # Initial planning, pre-wave admission, and the mandatory post-growth
    # admission consume three samples before the execution-region monitor.
    used = iter((10, 10, 10, 10, 90, 20, 20))
    monkeypatch.setattr(model_features, "_current_process_rss_bytes", lambda: 1_000)
    monkeypatch.setattr(
        training_parallel,
        "query_gpu_telemetry",
        lambda device: GpuTelemetrySample(
            sampled_monotonic=time.monotonic(),
            device_index=0,
            utilization_percent=1.0,
            used_bytes=next(used, 20),
            total_bytes=1_000,
        ),
    )

    class SlowProvider(_Provider):
        def predict_batch(self, atoms, **kwargs):
            time.sleep(0.008)
            return super().predict_batch(atoms, **kwargs)

    authority = _authority(vram=1_000)
    StaticMaceInferenceExecutor(
        SlowProvider(), batch_size=1, runtime_authority=authority, device="cuda:0"
    ).predict(_atoms(1))

    assert authority.evidence[0].peak_vram_bytes == 80


def test_v1_runtime_profile_is_rejected_for_old_evidence_semantics(tmp_path) -> None:
    path = tmp_path / "legacy-profile.json"
    path.write_text(
        '{"schema":"mdstats.static-inference-runtime-profile.v1"}',
        encoding="utf-8",
    )
    assert StaticInferenceRuntimeProfile.load_compatible(
        path, compatibility_digest=digest({"fixture": "joint-static"})
    ) is None


def test_v2_runtime_profile_is_rejected_for_pre_persistent_pool_semantics(tmp_path) -> None:
    path = tmp_path / "v2-profile.json"
    path.write_text(
        '{"schema":"mdstats.static-inference-runtime-profile.v2"}',
        encoding="utf-8",
    )
    assert StaticInferenceRuntimeProfile.load_compatible(
        path, compatibility_digest=digest({"fixture": "joint-static"})
    ) is None


def test_v3_runtime_profile_is_rejected_for_pre_marginal_pool_semantics(tmp_path) -> None:
    path = tmp_path / "v3-profile.json"
    path.write_text(
        '{"schema":"mdstats.static-inference-runtime-profile.v3"}',
        encoding="utf-8",
    )
    assert StaticInferenceRuntimeProfile.load_compatible(
        path, compatibility_digest=digest({"fixture": "joint-static"})
    ) is None


def test_v4_feasible_evidence_requires_explicit_consistent_components() -> None:
    point = _measured_point(8, 1, 100.0, 2_000, 4_000)
    malformed = point.to_dict()
    malformed.pop("execution_peak_ram_bytes")
    with pytest.raises(TrainingDataSerializationError, match="required resource components"):
        StaticInferenceOperatingPointEvidence.from_dict(malformed)
    with pytest.raises(TrainingDataInputError, match="must equal residency"):
        StaticInferenceOperatingPointEvidence(
            8, 1, 100.0, 2_000, 4_000,
            completed_structures=8,
            elapsed_seconds=0.08,
            observed_max_active_jobs=1,
            provider_pool_resident_ram_bytes=0,
            provider_pool_resident_vram_bytes=0,
            execution_peak_ram_bytes=1_999,
            execution_peak_vram_bytes=4_000,
        )


def test_live_reclamp_uses_policy_fraction_of_current_availability() -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "live-coordinate"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=80 * 1024**3,
        live_vram_budget_bytes=int(21.6 * 1024**3),
        ram_policy_fraction=0.80,
        vram_policy_fraction=0.90,
    )
    authority.reclamp(
        live_ram_available_bytes=10 * 1024**3,
        live_vram_available_bytes=6 * 1024**3,
    )
    assert authority.live_ram_budget_bytes == 8 * 1024**3
    assert authority.live_vram_budget_bytes == int(5.4 * 1024**3)


def test_resident_pool_is_admitted_against_only_its_execution_transient(monkeypatch) -> None:
    from mdstats.training_data import resources

    original = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "warm-pool-marginal"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=14,
        live_vram_budget_bytes=None,
        ram_policy_fraction=1.0,
    )
    original.record(_measured_point(8, 1, 10.0, 4, None))
    original.record(
        StaticInferenceOperatingPointEvidence(
            8, 2, 20.0, 14, None,
            completed_structures=16,
            elapsed_seconds=0.8,
            observed_max_active_jobs=2,
            provider_pool_resident_ram_bytes=10,
            execution_peak_ram_bytes=4,
        )
    )
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=original.compatibility_digest,
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=14,
        live_vram_budget_bytes=None,
        ram_policy_fraction=1.0,
        compatible_profile=original.profile(),
    )
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=8, runtime_authority=authority
    )
    executor._provider_pool.append(_Provider())
    executor._provider_pool_resident_ram_bytes.append(10)
    executor._provider_pool_resident_vram_bytes.append(None)
    monkeypatch.setattr(resources, "available_memory_bytes", lambda: 4)

    assert len(executor.predict(_atoms(16))) == 16


def test_runtime_profile_reuse_requires_compatibility_and_live_reclamps() -> None:
    original = _authority()
    low = _measured_point(8, 1, 100.0, 2_000, 4_000)
    high = _measured_point(16, 2, 130.0, 8_000, 12_000)
    original.record(low)
    original.record(high)
    profile = original.profile()
    assert StaticInferenceRuntimeProfile.from_dict(profile.to_dict()) == profile

    reused = _authority(profile=profile)
    assert reused.reused_compatible_profile
    assert reused.next_batch_size(32) == profile.selected_batch_size

    stale = _authority(
        profile=profile,
        compatibility=digest({"fixture": "different-runtime"}),
    )
    assert not stale.reused_compatible_profile
    assert stale.next_batch_size(32) == 8

    selected = reused.reclamp(
        live_ram_available_bytes=3_750,
        live_vram_available_bytes=5_556,
    )
    # Profile evidence remains a source of measured candidates. The executor's
    # marginal current-state admission selects/falls back at wave launch rather
    # than rejecting this fresh-baseline aggregate here.
    assert selected == high
    assert reused.reused_compatible_profile


def test_oom_backoff_feeds_authoritative_safe_batch_ceiling() -> None:
    authority = _authority(vram=None)
    executor = StaticMaceInferenceExecutor(
        _Provider(maximum_batch=8),
        batch_size=32,
        runtime_authority=authority,
    )
    assert len(executor.predict(_atoms(40))) == 40
    assert authority.learned_safe_batch_ceiling <= 8
    assert all(
        point.batch_size <= 8
        for point in authority.evidence
        if point.feasible
    )


def test_auto_execution_path_persists_and_reuses_compatible_profile(
    tmp_path, monkeypatch
) -> None:
    import mdstats
    from mdstats.training_data import campaign_execution, resources
    from mdstats.training_data.resources import (
        GpuResourceSnapshot,
        SystemResourceSnapshot,
    )

    snapshot = SystemResourceSnapshot(
        cpu_threads_available=8,
        cpu_fraction=0.90,
        cpu_threads_budget=7,
        ram_available_bytes=1 << 60,
        ram_fraction=0.80,
        ram_budget_bytes=1 << 59,
        gpu_memory_fraction=0.90,
        gpu=GpuResourceSnapshot(False, 0, None, None, None, None, None, "cpu"),
    )
    monkeypatch.setattr(resources, "detect_system_resources", lambda **kwargs: snapshot)

    class Provider(_Provider):
        def set_head(self, head):
            pass

        def close(self):
            pass

    from mdstats.training_data import model_features
    monkeypatch.setattr(
        model_features.MaceCalculatorProvider,
        "from_model_path",
        classmethod(lambda cls, *args, **kwargs: Provider()),
    )

    model = tmp_path / "model.pt"
    model.write_bytes(b"runtime-profile-fixture")
    graph_cache = tmp_path / "evaluation-graphs"
    atoms = _atoms(64)
    plan = mdstats.InferenceExecutionPlan(
        batch_policy="auto",
        selected_batch_size=8,
        maximum_batch_size=32,
        selected_concurrent_model_jobs=2,
    )
    policy = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), device="cpu", default_dtype="float64"
    )

    first_provider = Provider()
    first = campaign_execution._predict_model_on_atoms(
        model,
        atoms,
        head=None,
        policy=policy,
        execution_plan=plan,
        provider=first_provider,
        graph_cache_directory=graph_cache,
    )
    assert any(size > 8 for size, _ in first_provider.calls)
    profiles = tuple((tmp_path / "static-inference-runtime-profiles").glob("*.json"))
    assert len(profiles) == 1
    profile = StaticInferenceRuntimeProfile.from_dict(
        __import__("json").loads(profiles[0].read_text(encoding="utf-8"))
    )
    assert all(
        point.provider_pool_resident_ram_bytes + point.execution_peak_ram_bytes
        == point.peak_ram_bytes
        for point in profile.evidence
        if point.feasible
    )

    reused_provider = Provider()
    reused = campaign_execution._predict_model_on_atoms(
        model,
        atoms,
        head=None,
        policy=policy,
        execution_plan=plan,
        provider=reused_provider,
        graph_cache_directory=graph_cache,
    )

    assert reused_provider.calls
    assert reused_provider.calls[0][0] == profile.selected_batch_size
    assert len(reused) == len(first) == len(atoms)
    np.testing.assert_allclose(
        [value.energy_ev for value in reused],
        [value.energy_ev for value in first],
        rtol=0.0,
        atol=0.0,
    )
