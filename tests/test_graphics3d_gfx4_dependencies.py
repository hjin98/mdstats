from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from dataclasses import dataclass, field
import threading
import time
import pytest

from mdstats.graphics3d import (
    GraphicsDependencyKey,
    GraphicsLayer3DRequest,
    GraphicsScene3DRequest,
    GraphicsSceneContext,
    GraphicsSelection,
    plan_graphics_scene_dependencies,
)
from mdstats.graphics3d.lta_preset import LTAGraphics3DDependencySource
from mdstats.graphics3d.providers import (
    CONNECTIVITY_PRODUCT_PROVIDER,
    DENSITY_PRODUCT_PROVIDER,
    FRAMEWORK_PRODUCT_PROVIDER,
    TRAJECTORY_PRODUCT_PROVIDER,
    GraphicsScientificProduct,
)


class _PlanningSource:
    def dependency_key(self, provider_type: str) -> GraphicsDependencyKey:
        return GraphicsDependencyKey(provider_type, {"source": "same-science"})

    def resolve_graphics3d_dependency(self, key, context):  # pragma: no cover - planning only
        return GraphicsScientificProduct(key.provider_type, object())


def _request(*layers: GraphicsLayer3DRequest) -> GraphicsScene3DRequest:
    return GraphicsScene3DRequest(layers=tuple(layers))


def test_product_level_dependency_plan_replaces_monolithic_scene_key() -> None:
    request = _request(
        GraphicsLayer3DRequest("framework", "framework"),
        GraphicsLayer3DRequest("connectivity", "connectivity"),
        GraphicsLayer3DRequest("trajectory", "trajectory", selection=GraphicsSelection(species=("Na",))),
        GraphicsLayer3DRequest("density", "density", selection=GraphicsSelection(species=("Na",))),
    )
    plan = plan_graphics_scene_dependencies(
        request, context=GraphicsSceneContext(source=_PlanningSource(), source_identity="raw")
    )
    assert tuple(entry.key.provider_type for entry in plan) == (
        FRAMEWORK_PRODUCT_PROVIDER,
        CONNECTIVITY_PRODUCT_PROVIDER,
        TRAJECTORY_PRODUCT_PROVIDER,
        DENSITY_PRODUCT_PROVIDER,
    )
    assert "framework_dynamics_scene" not in {entry.key.provider_type for entry in plan}


def test_duplicate_density_instances_share_one_dependency_key() -> None:
    request = _request(
        GraphicsLayer3DRequest("Na density A", "density", selection=GraphicsSelection(species=("Na",))),
        GraphicsLayer3DRequest("Na density B", "density", selection=GraphicsSelection(species=("Na",))),
    )
    plan = plan_graphics_scene_dependencies(
        request, context=GraphicsSceneContext(source=_PlanningSource(), source_identity="raw")
    )
    assert len(plan) == 1
    assert plan[0].key.provider_type == DENSITY_PRODUCT_PROVIDER
    assert plan[0].consumers == ("Na density A", "Na density B")


def test_scene_context_single_flight_executes_concurrent_resolver_once() -> None:
    context = GraphicsSceneContext(source_identity="same")
    key = GraphicsDependencyKey("expensive", {"science": 1})
    lock = threading.Lock()
    calls = 0
    token = object()

    def resolver():
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.03)
        return token

    with ThreadPoolExecutor(max_workers=8) as pool:
        values = tuple(pool.map(lambda _: context.resolve_dependency(key, resolver), range(8)))
    assert all(value is token for value in values)
    assert calls == 1
    report = dict(context.dependency_report()[key.identity])
    assert report["resolver_executions"] == 1
    assert report["cache_hits"] == 7
    assert report["wait_hits"] >= 1


def test_cache_state_does_not_change_dependency_identity() -> None:
    key = GraphicsDependencyKey("atomic_trajectory_product", {"source": "abc"})
    before = key.identity
    context = GraphicsSceneContext(source_identity="abc")
    context.resolve_dependency(key, lambda: object())
    context.resolve_dependency(key, lambda: object())
    assert key.identity == before


def test_lta_source_batches_product_resolution_once(monkeypatch, tmp_path: Path) -> None:
    import mdstats.graphics3d.lta_preset as lta

    request = _request(
        GraphicsLayer3DRequest("framework", "framework"),
        GraphicsLayer3DRequest("trajectory", "trajectory", selection=GraphicsSelection(species=("Na",))),
    )
    trajectory = SimpleNamespace(
        n_frames=3,
        n_atoms=4,
        atomic_numbers=[14, 13, 8, 11],
    )
    @dataclass(frozen=True)
    class FakeScene:
        mean_framework: object = "framework-product"
        trajectory_paths: object = "trajectory-product"
        atomic_mean_graph: object = None
        atomic_density_fields: tuple = ()
        framework_density_fields: object = None
        metadata: dict = field(default_factory=dict)

    fake_scene = FakeScene()
    calls = []

    def fake_prepare(*args, **kwargs):
        calls.append(1)
        return fake_scene, {"source": "test"}

    monkeypatch.setattr(lta, "prepare_legacy_source_scene", fake_prepare)
    source = LTAGraphics3DDependencySource(
        trajectory=trajectory,
        request=request,
        input_options={"stride": 1},
        output_path=tmp_path / "scene.html",
        source_identity="trajectory-sha",
    )
    context = GraphicsSceneContext(source=source, source_identity="trajectory-sha")
    fw_key = source.dependency_key(FRAMEWORK_PRODUCT_PROVIDER)
    tr_key = source.dependency_key(TRAJECTORY_PRODUCT_PROVIDER)
    fw = context.resolve_dependency(fw_key, lambda: source.resolve_graphics3d_dependency(fw_key, context))
    tr = context.resolve_dependency(tr_key, lambda: source.resolve_graphics3d_dependency(tr_key, context))
    assert fw.value == "framework-product"
    assert tr.value == "trajectory-product"
    assert calls == [1]
    assert dict(source.preparation_report())["preparation_count"] == 1


def test_lta_source_latches_one_failed_preparation_across_product_keys(
    monkeypatch, tmp_path: Path
) -> None:
    import mdstats.graphics3d.lta_preset as lta

    request = _request(
        GraphicsLayer3DRequest("framework", "framework"),
        GraphicsLayer3DRequest(
            "trajectory", "trajectory", selection=GraphicsSelection(species=("Na",))
        ),
    )
    trajectory = SimpleNamespace(
        n_frames=3,
        n_atoms=4,
        atomic_numbers=[14, 13, 8, 11],
    )
    lock = threading.Lock()
    calls = 0

    def failing_prepare(*args, **kwargs):
        nonlocal calls
        with lock:
            calls += 1
        time.sleep(0.03)
        raise RuntimeError("root science failure")

    monkeypatch.setattr(lta, "prepare_legacy_source_scene", failing_prepare)
    source = LTAGraphics3DDependencySource(
        trajectory=trajectory,
        request=request,
        input_options={"stride": 1},
        output_path=tmp_path / "scene.html",
        source_identity="trajectory-sha",
    )
    context = GraphicsSceneContext(source=source, source_identity="trajectory-sha")
    keys = (
        source.dependency_key(FRAMEWORK_PRODUCT_PROVIDER),
        source.dependency_key(TRAJECTORY_PRODUCT_PROVIDER),
    )

    def resolve(key):
        with pytest.raises(Exception) as exc_info:
            source.resolve_graphics3d_dependency(key, context)
        return exc_info.value

    with ThreadPoolExecutor(max_workers=2) as pool:
        failures = tuple(pool.map(resolve, keys))

    assert calls == 1
    assert all("root science failure" in str(error) for error in failures)
    report = dict(source.preparation_report())
    assert report["preparation_attempt_count"] == 1
    assert report["preparation_count"] == 0
    assert report["failed"] is True
    assert report["failure_type"] == "RuntimeError"
