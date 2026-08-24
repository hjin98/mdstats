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
from mdstats.training_data._common import TrainingDataInputError


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


def test_joint_runtime_authority_selects_best_safe_near_equivalent_point() -> None:
    authority = _authority(vram=10_000)
    points = (
        StaticInferenceOperatingPointEvidence(8, 1, 100.0, 2_000, 4_000),
        StaticInferenceOperatingPointEvidence(16, 1, 104.0, 3_000, 7_000),
        StaticInferenceOperatingPointEvidence(8, 2, 103.0, 4_000, 9_000),
        StaticInferenceOperatingPointEvidence(16, 2, 120.0, 5_000, 15_000),
    )
    for point in points:
        authority.record(point)

    # The unsafe fastest point is excluded. The 100/s point is within 5% of
    # the safe 104/s peak and wins on lower aggregate resource demand.
    assert authority.selected_point == points[0]


def test_executor_auto_search_exercises_geometric_batches_above_eight() -> None:
    provider = _Provider()
    authority = _authority(vram=None)
    executor = StaticMaceInferenceExecutor(
        provider,
        batch_size=32,
        runtime_authority=authority,
        concurrent_model_jobs=2,
    )

    predictions = executor.predict(_atoms(64))

    assert len(predictions) == 64
    assert [size for size, _ in provider.calls[:3]] == [8, 16, 32]
    assert {point.concurrent_model_jobs for point in authority.evidence} == {2}


def test_runtime_profile_reuse_requires_compatibility_and_live_reclamps() -> None:
    original = _authority()
    low = StaticInferenceOperatingPointEvidence(8, 1, 100.0, 2_000, 4_000)
    high = StaticInferenceOperatingPointEvidence(16, 2, 130.0, 8_000, 12_000)
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

    selected = reused.reclamp(live_ram_budget_bytes=3_000, live_vram_budget_bytes=5_000)
    assert selected == low
    assert not reused.reused_compatible_profile


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
    assert [size for size, _ in first_provider.calls[:3]] == [8, 16, 32]
    profiles = tuple((tmp_path / "static-inference-runtime-profiles").glob("*.json"))
    assert len(profiles) == 1
    profile = StaticInferenceRuntimeProfile.from_dict(
        __import__("json").loads(profiles[0].read_text(encoding="utf-8"))
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
