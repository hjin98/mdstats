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


def test_static_executor_honors_staged_cancellation_before_next_batch() -> None:
    from mdstats.training_data.inference_parallel import inference_start_signal

    provider = _Provider()
    executor = StaticMaceInferenceExecutor(provider, batch_size=2)
    phases: list[str] = []
    with inference_start_signal(
        lambda: None,
        phase_callback=phases.append,
        cancellation_requested=lambda: True,
    ):
        with pytest.raises(InterruptedError, match="cancelled"):
            executor.predict(_atoms(4))
    assert provider.calls == []
    assert any("cancelled before static inference batch" in phase for phase in phases)


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
        estimated_provider_resident_ram_bytes=1,
        estimated_provider_resident_vram_bytes=None if vram is None else 1,
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
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "live-growth-block"}),
        maximum_batch_size=32,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=100,
    )
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
        estimated_provider_resident_ram_bytes=1,
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
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "live-growth"}),
        maximum_batch_size=32,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=100,
    )
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

    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "live-growth-block"}),
        maximum_batch_size=32,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=100,
    )
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


def test_v4_runtime_profile_is_rejected_for_pre_reproducible_residency(tmp_path) -> None:
    path = tmp_path / "v4-profile.json"
    path.write_text(
        '{"schema":"mdstats.static-inference-runtime-profile.v4"}',
        encoding="utf-8",
    )
    assert StaticInferenceRuntimeProfile.load_compatible(
        path, compatibility_digest=digest({"fixture": "joint-static"})
    ) is None


def test_valid_v5_runtime_profile_is_refused_after_2d_failure_learning_fix(tmp_path) -> None:
    """A v5 ceiling may have been contaminated by the old J>1 backoff bug."""

    current = _authority(vram=None)
    current.record(_measured_point(8, 1, 10.0, 1, None))
    legacy = current.profile().to_dict()
    legacy["schema"] = "mdstats.static-inference-runtime-profile.v5"
    legacy["evidence_semantics"] = (
        "persistent-provider-required-residency-plus-steady-state-execution-peak.v5"
    )
    legacy["learned_safe_batch_ceiling"] = 1
    legacy["content_digest"] = digest({
        key: value for key, value in legacy.items() if key != "content_digest"
    })
    path = tmp_path / "v5-profile.json"
    path.write_text(__import__("json").dumps(legacy), encoding="utf-8")

    assert StaticInferenceRuntimeProfile.load_compatible(
        path, compatibility_digest=current.compatibility_digest
    ) is None
    rebuilt = _authority(vram=None)
    assert rebuilt.learned_safe_batch_ceiling == rebuilt.maximum_batch_size


def test_v6_profile_round_trips_and_compatibility_identity_excludes_v5() -> None:
    from mdstats.training_data import model_features

    authority = _authority(vram=None)
    authority.record(_measured_point(8, 1, 10.0, 1, None))
    profile = authority.profile()
    assert profile.to_dict()["schema"] == "mdstats.static-inference-runtime-profile.v6"
    assert StaticInferenceRuntimeProfile.from_dict(profile.to_dict()) == profile

    payload = {"fixture": "compatibility-v6"}
    current = StaticInferenceRuntimeAuthority.compatibility_key(payload)
    legacy = digest({
        "schema": "mdstats.static-inference-compatibility.v2",
        "evidence_semantics": (
            "persistent-provider-required-residency-plus-steady-state-execution-peak.v5"
        ),
        **payload,
    })
    assert current != legacy
    assert model_features.STATIC_INFERENCE_EVIDENCE_SEMANTICS.endswith(".v6")


def test_provider_requirement_never_collapses_to_zero_allocator_delta(monkeypatch) -> None:
    from mdstats.training_data import model_features

    class ZeroMonitor:
        def __init__(self, device): pass
        def start(self): pass
        def finish(self): return 0, None

    monkeypatch.setattr(model_features, "_StaticInferenceResourceMonitor", ZeroMonitor)
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "required-floor"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=100,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=5,
    )
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=8, runtime_authority=authority,
        provider_factory=_Provider,
    )
    executor._ensure_provider_pool(2)
    assert executor.provider_pool_resident_ram_bytes >= 5
    assert authority.provider_residency_estimate()[0] >= 5


def test_j_dependent_execution_oom_preserves_lower_j_batch_capability() -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "two-dimensional-oom"}),
        maximum_batch_size=32,
        maximum_concurrent_model_jobs=4,
        live_ram_budget_bytes=1 << 20,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=1,
    )
    authority.record(StaticInferenceOperatingPointEvidence(
        16, 4, 0.0, 0, None, feasible=False, failure_kind="execution-oom"
    ))
    assert authority.learned_safe_batch_ceiling == 32
    candidates = authority.candidate_operating_points(
        available_structures=128, concurrency_available=True
    )
    assert (16, 1) in candidates and (16, 2) in candidates
    assert (16, 4) not in candidates


def test_production_j4_backoff_records_only_a_two_dimensional_boundary(monkeypatch) -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "production-j4-backoff"}),
        maximum_batch_size=16,
        maximum_concurrent_model_jobs=4,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=1,
    )
    for jobs, throughput in ((1, 100.0), (2, 200.0), (4, 300.0)):
        authority.record(_measured_point(16, jobs, throughput, 1, None))
    authority.reused_compatible_profile = True
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=16, runtime_authority=authority,
        provider_factory=_Provider,
    )
    requested_jobs: list[int] = []

    def wave(values, identities, *, batch_size, concurrent_jobs):
        requested_jobs.append(concurrent_jobs)
        resident = executor.provider_pool_resident_ram_bytes
        predicted = _Provider().predict_batch(values)
        backed_off = concurrent_jobs == 4
        return (
            predicted, 1.0, resident + 1, None, concurrent_jobs,
            8 if backed_off else batch_size, 1 if backed_off else 0,
            resident, None, 1, None,
        )

    monkeypatch.setattr(executor, "_run_joint_wave", wave)
    observed = executor.predict(_atoms(80))

    assert requested_jobs == [4, 1]
    assert authority.learned_safe_batch_ceiling == 16
    assert (16, 4) in authority.failed_execution_boundaries
    assert authority._safe(next(
        point for point in authority.evidence
        if (point.batch_size, point.concurrent_model_jobs) == (16, 1) and point.feasible
    ))
    assert authority._safe(next(
        point for point in authority.evidence
        if (point.batch_size, point.concurrent_model_jobs) == (16, 2) and point.feasible
    ))
    np.testing.assert_allclose(
        [value.energy_ev for value in observed],
        [value.positions[1, 2] for value in _atoms(80)], rtol=0.0, atol=0.0,
    )


def test_production_j1_backoff_still_tightens_the_single_provider_ceiling(monkeypatch) -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "production-j1-backoff"}),
        maximum_batch_size=16,
        maximum_concurrent_model_jobs=1,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=1,
    )
    authority.record(_measured_point(16, 1, 100.0, 1, None))
    authority.reused_compatible_profile = True
    executor = StaticMaceInferenceExecutor(_Provider(), batch_size=16, runtime_authority=authority)

    def wave(values, identities, *, batch_size, concurrent_jobs):
        return (
            _Provider().predict_batch(values), 1.0, 1, None, 1, 8, 1,
            0, None, 1, None,
        )

    monkeypatch.setattr(executor, "_run_joint_wave", wave)
    assert len(executor.predict(_atoms(16))) == 16
    assert authority.learned_safe_batch_ceiling == 8


@pytest.mark.parametrize("maximum_jobs", (4, 8))
def test_fresh_growth_without_residency_estimate_is_single_provider_only(maximum_jobs) -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": f"fresh-j{maximum_jobs}"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=maximum_jobs,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
    )
    created = 0

    def factory():
        nonlocal created
        created += 1
        return _Provider()

    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=8, runtime_authority=authority, provider_factory=factory,
    )
    assert authority.candidate_concurrencies == (1,)
    assert len(executor.predict(_atoms(16))) == 16
    assert created == 0


def test_residency_estimate_restores_geometric_growth_and_profile_reuse() -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "fresh-geometric"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=8,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=1,
    )
    assert authority.candidate_concurrencies == (1, 2, 4, 8)

    original = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "profile-j2"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=100,
        live_vram_budget_bytes=None,
        estimated_provider_resident_ram_bytes=1,
    )
    original.record(_measured_point(8, 1, 10.0, 1, None))
    original.record(_measured_point(8, 2, 20.0, 2, None))
    reused = StaticInferenceRuntimeAuthority(
        compatibility_digest=original.compatibility_digest,
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=2,
        live_ram_budget_bytes=100,
        live_vram_budget_bytes=None,
        compatible_profile=original.profile(),
    )
    assert reused.reused_compatible_profile
    assert reused.selected_point is not None
    assert reused.selected_point.concurrent_model_jobs == 2


def test_cuda_growth_requires_a_complete_ram_and_vram_residency_requirement() -> None:
    authority = StaticInferenceRuntimeAuthority(
        compatibility_digest=digest({"fixture": "fresh-cuda-requirement"}),
        maximum_batch_size=8,
        maximum_concurrent_model_jobs=4,
        live_ram_budget_bytes=1 << 30,
        live_vram_budget_bytes=1 << 30,
        estimated_provider_resident_ram_bytes=1,
        estimated_provider_resident_vram_bytes=None,
    )
    assert authority.candidate_concurrencies == (1,)


def test_resource_classifier_and_pool_shrink_are_type_aware_and_once_only(monkeypatch) -> None:
    import errno

    assert StaticMaceInferenceExecutor._is_oom(MemoryError())
    assert StaticMaceInferenceExecutor._is_oom(OSError(errno.ENOMEM, "full"))
    released: list[None] = []
    monkeypatch.setattr(
        StaticMaceInferenceExecutor, "_release_cuda_cache", staticmethod(lambda: released.append(None))
    )
    executor = StaticMaceInferenceExecutor(_Provider(), batch_size=1, device="cuda:0")
    executor._provider_pool.extend((_Provider(), _Provider(), _Provider()))
    executor._provider_pool_resident_ram_bytes.extend((1, 1, 1))
    executor._provider_pool_resident_vram_bytes.extend((None, None, None))
    executor._provider_pool_observed_ram_bytes.extend((0, 0, 0))
    executor._provider_pool_observed_vram_bytes.extend((None, None, None))
    executor._retire_private_providers(keep_jobs=2)
    assert executor.resident_provider_pool_size == 2
    assert len(released) == 1
    executor._retire_private_providers(keep_jobs=2)
    assert len(released) == 1

    cpu_executor = StaticMaceInferenceExecutor(_Provider(), batch_size=1, device="cpu")
    cpu_executor._provider_pool.extend((_Provider(), _Provider(), _Provider()))
    cpu_executor._provider_pool_resident_ram_bytes.extend((1, 1, 1))
    cpu_executor._provider_pool_resident_vram_bytes.extend((None, None, None))
    cpu_executor._provider_pool_observed_ram_bytes.extend((0, 0, 0))
    cpu_executor._provider_pool_observed_vram_bytes.extend((None, None, None))
    cpu_executor._retire_private_providers(keep_jobs=2)
    assert len(released) == 1


def test_private_mace_pool_retirement_defers_cache_release_to_the_executor(monkeypatch) -> None:
    from mdstats.training_data.model_features import MaceCalculatorProvider

    retired: list[bool] = []
    monkeypatch.setattr(
        MaceCalculatorProvider,
        "close",
        lambda self, *, release_cuda_memory=True: retired.append(release_cuda_memory),
    )
    released: list[None] = []
    monkeypatch.setattr(
        StaticMaceInferenceExecutor, "_release_cuda_cache", staticmethod(lambda: released.append(None))
    )
    executor = StaticMaceInferenceExecutor(_Provider(), batch_size=1, device="cuda:0")
    first_private = object.__new__(MaceCalculatorProvider)
    second_private = object.__new__(MaceCalculatorProvider)
    executor._provider_pool.extend((_Provider(), first_private, second_private))
    executor._provider_pool_resident_ram_bytes.extend((1, 1, 1))
    executor._provider_pool_resident_vram_bytes.extend((None, None, None))
    executor._provider_pool_observed_ram_bytes.extend((0, 0, 0))
    executor._provider_pool_observed_vram_bytes.extend((None, None, None))

    executor._retire_private_providers(keep_jobs=1)

    assert retired == [False, False]
    assert len(released) == 1


@pytest.mark.parametrize("failure", (MemoryError("full"), OSError(12, "full")))
def test_first_private_growth_failure_releases_cuda_cache_once(monkeypatch, failure) -> None:
    released: list[None] = []
    monkeypatch.setattr(
        StaticMaceInferenceExecutor, "_release_cuda_cache", lambda self: released.append(None)
    )
    base = _Provider()
    executor = StaticMaceInferenceExecutor(
        base, batch_size=1, device="cuda:0", provider_factory=lambda: (_ for _ in ()).throw(failure)
    )

    with pytest.raises(type(failure)):
        executor._ensure_provider_pool(2)

    assert executor.resident_provider_pool_size == 1
    assert executor.provider is base
    assert len(released) == 1


def test_later_private_growth_failure_rolls_back_once_without_leak(monkeypatch) -> None:
    released: list[None] = []
    monkeypatch.setattr(
        StaticMaceInferenceExecutor, "_release_cuda_cache", lambda self: released.append(None)
    )
    closed: list[str] = []

    class Provider(_Provider):
        def __init__(self, name):
            super().__init__()
            self.name = name

        def close(self):
            closed.append(self.name)

    attempts = iter((Provider("first"), MemoryError("full")))

    def factory():
        value = next(attempts)
        if isinstance(value, BaseException):
            raise value
        return value

    executor = StaticMaceInferenceExecutor(
        Provider("base"), batch_size=1, device="cuda:0",
        provider_factory=factory,
    )

    with pytest.raises(MemoryError):
        executor._ensure_provider_pool(3)

    assert executor.resident_provider_pool_size == 1
    assert closed == ["first"]
    assert len(released) == 1


def test_nonresource_private_growth_failure_propagates_after_exact_cleanup(monkeypatch) -> None:
    released: list[None] = []
    monkeypatch.setattr(
        StaticMaceInferenceExecutor,
        "_release_cuda_cache",
        lambda self: released.append(None) if self.device.startswith("cuda") else None,
    )
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=1, device="cuda:0",
        provider_factory=lambda: (_ for _ in ()).throw(ValueError("bad provider")),
    )

    with pytest.raises(ValueError, match="bad provider"):
        executor._ensure_provider_pool(2)

    assert executor.resident_provider_pool_size == 1
    assert len(released) == 1


def test_cpu_private_growth_failure_never_releases_cuda_cache(monkeypatch) -> None:
    released: list[None] = []
    monkeypatch.setattr(
        StaticMaceInferenceExecutor,
        "_release_cuda_cache",
        lambda self: released.append(None) if self.device.startswith("cuda") else None,
    )
    executor = StaticMaceInferenceExecutor(
        _Provider(), batch_size=1, device="cpu",
        provider_factory=lambda: (_ for _ in ()).throw(MemoryError("full")),
    )

    with pytest.raises(MemoryError):
        executor._ensure_provider_pool(2)

    assert released == []


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


def test_auto_profile_reuses_runtime_architecture_across_checkpoint_weights(
    tmp_path, monkeypatch
) -> None:
    """Calibration compatibility is execution-structural, not checkpoint-weight identity."""

    import mdstats
    from types import SimpleNamespace
    from mdstats.training_data import campaign_execution, model_features, resources
    from mdstats.training_data.resources import GpuResourceSnapshot, SystemResourceSnapshot

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
        def __init__(self, *, exact_identity: str, runtime_architecture: str):
            super().__init__()
            self.checkpoint_identity = SimpleNamespace(content_digest=exact_identity)
            self.runtime_architecture_digest = runtime_architecture

        def set_head(self, head):
            pass

        def close(self):
            pass

    architecture = digest({"fixture": "same-runtime-architecture"})
    model_a = tmp_path / "model-a.pt"
    model_b = tmp_path / "model-b.pt"
    model_a.write_bytes(b"checkpoint-a-weights")
    model_b.write_bytes(b"checkpoint-b-weights")
    atoms = _atoms(24)
    geometry_ids = tuple(digest({"geometry": index}) for index in range(len(atoms)))
    plan = mdstats.InferenceExecutionPlan(
        batch_policy="auto",
        selected_batch_size=2,
        maximum_batch_size=8,
        selected_concurrent_model_jobs=1,
    )
    policy = mdstats.CheckpointEvaluationPolicy(
        condition_keys=(), device="cpu", default_dtype="float64"
    )
    graph_cache = tmp_path / "evaluation-graphs"

    first_provider = Provider(
        exact_identity=digest({"checkpoint": "a"}),
        runtime_architecture=architecture,
    )
    first = campaign_execution._predict_model_on_atoms(
        model_a,
        atoms,
        head=None,
        policy=policy,
        execution_plan=plan,
        provider=first_provider,
        geometry_identities=geometry_ids,
        graph_cache_directory=graph_cache,
    )
    profiles = tuple((tmp_path / "static-inference-runtime-profiles").glob("*.json"))
    assert len(profiles) == 1
    profile = StaticInferenceRuntimeProfile.from_dict(
        __import__("json").loads(profiles[0].read_text(encoding="utf-8"))
    )

    second_provider = Provider(
        exact_identity=digest({"checkpoint": "b"}),
        runtime_architecture=architecture,
    )
    second = campaign_execution._predict_model_on_atoms(
        model_b,
        atoms,
        head=None,
        policy=policy,
        execution_plan=plan,
        provider=second_provider,
        geometry_identities=geometry_ids,
        graph_cache_directory=graph_cache,
    )
    # Different scientific checkpoint identities share exactly one runtime
    # profile only because their explicit execution architecture identity agrees.
    assert first_provider.checkpoint_identity.content_digest != second_provider.checkpoint_identity.content_digest
    assert len(tuple((tmp_path / "static-inference-runtime-profiles").glob("*.json"))) == 1
    assert second_provider.calls
    assert second_provider.calls[0][0] == profile.selected_batch_size
    np.testing.assert_allclose(
        [value.energy_ev for value in second],
        [value.energy_ev for value in first],
        rtol=0.0,
        atol=0.0,
    )

    incompatible_provider = Provider(
        exact_identity=digest({"checkpoint": "c"}),
        runtime_architecture=digest({"fixture": "different-runtime-architecture"}),
    )
    campaign_execution._predict_model_on_atoms(
        model_b,
        atoms,
        head=None,
        policy=policy,
        execution_plan=plan,
        provider=incompatible_provider,
        geometry_identities=geometry_ids,
        graph_cache_directory=graph_cache,
    )
    assert len(tuple((tmp_path / "static-inference-runtime-profiles").glob("*.json"))) == 2
