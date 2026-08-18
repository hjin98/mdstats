from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from mdstats.graphics3d import (
    DEFAULT_GRAPHICS_LAYER_REGISTRY,
    GraphicsLayer3DRequest,
    GraphicsLayerRegistration,
    GraphicsLayerRegistry,
    GraphicsScene3DRequest,
    GraphicsSceneContext,
    GraphicsSelection,
    PointSet3D,
    PreparedGraphicsLayer3D,
    PreparedGraphicsScene3D,
    prepare_graphics3d_scene,
    render_graphics3d_plotly,
)
from mdstats.graphics3d.browser import GraphicsBrowserBudget, measure_browser_payload
from mdstats.graphics3d.errors import Graphics3DValidationError
from mdstats.graphics3d.manifest import GraphicsSceneManifest
from mdstats.graphics3d.view import resolve_periodic_image_shifts
from tests.test_graphics3d_layers import full_legacy_scene


def _scene_request(*, view=None, priorities=(0, 0)):
    return GraphicsScene3DRequest(
        layers=(
            GraphicsLayer3DRequest("framework", "framework", render_priority=priorities[0]),
            GraphicsLayer3DRequest(
                "Na trajectory", "trajectory", selection=GraphicsSelection(species=("Na",)),
                render_priority=priorities[1],
            ),
        ),
        view={} if view is None else view,
    )


def test_builtin_prepared_layers_no_longer_expose_renderer_source_scene(full_legacy_scene):
    scene = prepare_graphics3d_scene(
        _scene_request(),
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx5-no-source-scene"),
    )
    assert all("source_scene" not in layer.product_refs for layer in scene.layers)
    rendered = render_graphics3d_plotly(scene)
    assert rendered.render_metadata["schema_version"].endswith("gfx3d5.v1")
    assert all(result.metadata["primitive_count"] > 0 for result in rendered.layer_results.values())


def test_view_visibility_camera_and_periodicity_do_not_change_scientific_identity(full_legacy_scene):
    base = prepare_graphics3d_scene(
        _scene_request(),
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx5-view-a"),
    )
    altered = prepare_graphics3d_scene(
        _scene_request(view={"camera": "[111]", "projection": "perspective", "periodic_images": [2, 1, 1], "visible_layers": ["Na trajectory"]}),
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx5-view-b"),
    )
    assert [l.scientific_identity for l in base.layers] == [l.scientific_identity for l in altered.layers]
    result = render_graphics3d_plotly(altered)
    assert result.render_metadata["periodic_image_shifts"] == [[0, 0, 0], [1, 0, 0]]
    assert result.artifact.layout.scene.camera.projection.type == "perspective"
    for index in result.layer_results["framework"].backend_object_indices:
        assert result.artifact.data[index].visible == "legendonly"
    for index in result.layer_results["Na trajectory"].backend_object_indices:
        assert result.artifact.data[index].visible is True


def test_render_priority_controls_backend_order_not_result_schema(full_legacy_scene):
    scene = prepare_graphics3d_scene(
        _scene_request(priorities=(10, -5)),
        context=GraphicsSceneContext(source=full_legacy_scene, source_identity="gfx5-priority"),
    )
    result = render_graphics3d_plotly(scene)
    assert tuple(result.layer_results) == ("framework", "Na trajectory")
    assert min(result.layer_results["Na trajectory"].backend_object_indices) < min(result.layer_results["framework"].backend_object_indices)


def test_periodic_image_resolution_is_deterministic_and_strict():
    assert resolve_periodic_image_shifts({"periodic_images": "2x1x2"}) == (
        (0,0,0), (0,0,1), (1,0,0), (1,0,1)
    )
    assert resolve_periodic_image_shifts({"periodic_images": [[0,0,0], [-1,0,0]]}) == ((0,0,0), (-1,0,0))
    with pytest.raises(Graphics3DValidationError):
        resolve_periodic_image_shifts({"periodic_images": [0,1,1]})


def test_browser_payload_budget_failure_is_explicit():
    primitive = PointSet3D(owner_layer="mock", primitive_id="many", positions=np.zeros((11,3)))
    payload = measure_browser_payload((primitive,))
    with pytest.raises(Graphics3DValidationError, match="browser payload"):
        GraphicsBrowserBudget(max_traces=10, max_points=10, max_faces=10, max_geometry_bytes=10_000).validate(payload)


def test_mock_fifth_layer_uses_common_renderer_without_result_schema_change():
    layer_type = "mock-gfx5"
    @dataclass(frozen=True, slots=True)
    class MockLayer:
        def dependencies(self, request, context): return ()
        def prepare(self, request, resolved_dependencies, context):
            return PreparedGraphicsLayer3D(request=request, scientific_identity=request.scientific_identity, product_refs={})
        def render_primitives(self, prepared, context):
            return (PointSet3D(owner_layer=prepared.request.name, primitive_id="point", positions=np.asarray([[1.,2.,3.]]), scientific_refs=(prepared.scientific_identity,), render_attributes={"name":"Mock"}),)
    registry = GraphicsLayerRegistry()
    for registration in DEFAULT_GRAPHICS_LAYER_REGISTRY.registrations():
        registry.register(registration)
    registry.register(GraphicsLayerRegistration(layer_type=layer_type, schema_version="test.mock.v1", adapter_factory=MockLayer))
    request = GraphicsScene3DRequest(layers=(GraphicsLayer3DRequest("Mock", layer_type),))
    prepared = prepare_graphics3d_scene(request, context=GraphicsSceneContext(source_identity="mock"), registry=registry)
    result = render_graphics3d_plotly(prepared, registry=registry)
    assert tuple(result.layer_results) == ("Mock",)
    assert len(result.artifact.data) == 1
    assert result.layer_results["Mock"].metadata["primitive_count"] == 1


def test_common_plotly_renderer_has_no_builtin_science_family_dispatch():
    source = Path("mdstats/graphics3d/plotly_renderer.py").read_text()
    for token in ('layer_type == "framework"', 'layer_type == "connectivity"', 'layer_type == "trajectory"', 'layer_type == "density"'):
        assert token not in source

def test_config_compiles_priority_and_view_records_without_scientific_pollution():
    from mdstats.graphics3d.config import compile_graphics3d_config
    payload = {
        "scene": {"projection": "perspective", "camera": "[110]", "periodic_images": "2x1x1", "visible_layers": ["framework"]},
        "layer": [{"type": "framework", "name": "framework", "priority": -3}],
    }
    compiled = compile_graphics3d_config(payload, present_species=("Si", "O"))
    assert compiled.request.layers[0].render_priority == -3
    assert compiled.request.view["camera"] == "[110]"
    assert compiled.request.view["periodic_images"] == "2x1x1"
    scientific = compiled.request.scientific_identity
    altered = GraphicsScene3DRequest(layers=compiled.request.layers, view={"camera": "[111]"})
    assert altered.scientific_identity == scientific


def test_cli_accepts_universal_view_overrides():
    from mdstats.graphics3d.cli import parse_arguments
    args = parse_arguments(["traj.lammpstrj", "--layer", "framework", "--camera", "[111]", "--periodic-images", "2x1x1", "--visible-layer", "framework", "--background", "dark"])
    assert args.camera == "[111]"
    assert args.periodic_images == "2x1x1"
    assert args.visible_layer == ["framework"]
    assert args.background == "dark"
