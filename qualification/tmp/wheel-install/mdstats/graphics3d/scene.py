"""Scene normalization and dependency planning for GFX3D-1."""

from __future__ import annotations

from .contracts import GraphicsDependencyRequest, GraphicsScene3DRequest
from .context import GraphicsSceneContext
from .dependencies import GraphicsDependencyPlanEntry, deduplicate_dependency_requests
from .errors import Graphics3DRegistryError, Graphics3DValidationError
from .manifest import GraphicsSceneManifest
from .registry import DEFAULT_GRAPHICS_LAYER_REGISTRY, GraphicsLayerRegistry


def plan_graphics_scene_dependencies(
    request: GraphicsScene3DRequest,
    *,
    context: GraphicsSceneContext | None = None,
    registry: GraphicsLayerRegistry = DEFAULT_GRAPHICS_LAYER_REGISTRY,
) -> tuple[GraphicsDependencyPlanEntry, ...]:
    """Collect and deduplicate dependency requests for enabled layers."""

    if not isinstance(request, GraphicsScene3DRequest):
        raise Graphics3DValidationError("request must be GraphicsScene3DRequest.")
    resolved_context = context or GraphicsSceneContext()
    dependencies: list[GraphicsDependencyRequest] = []
    for layer in request.enabled_layers:
        registration = registry.get(layer.layer_type)
        unsupported = layer.selection.active_fields() - registration.supported_selection_fields
        if unsupported:
            raise Graphics3DValidationError(
                f"Layer {layer.name!r} of type {layer.layer_type!r} does not support selection fields: "
                + ", ".join(sorted(unsupported))
            )
        adapter = registration.adapter_factory()
        from .registry import GraphicsLayer3DAdapter
        if not isinstance(adapter, GraphicsLayer3DAdapter):
            raise Graphics3DRegistryError(
                f"Adapter factory for layer type {layer.layer_type!r} did not return "
                "an object satisfying GraphicsLayer3DAdapter."
            )
        layer_dependencies = tuple(adapter.dependencies(layer, resolved_context))
        for dependency in layer_dependencies:
            if dependency.consumer_layer is None:
                dependency = GraphicsDependencyRequest(
                    key=dependency.key,
                    role=dependency.role,
                    consumer_layer=layer.name,
                )
            dependencies.append(dependency)
    return deduplicate_dependency_requests(dependencies)


def build_graphics_scene_manifest(
    request: GraphicsScene3DRequest,
    *,
    context: GraphicsSceneContext | None = None,
    registry: GraphicsLayerRegistry = DEFAULT_GRAPHICS_LAYER_REGISTRY,
    **manifest_kwargs: object,
) -> GraphicsSceneManifest:
    plan = plan_graphics_scene_dependencies(request, context=context, registry=registry)
    return GraphicsSceneManifest(request=request, dependency_plan=plan, **manifest_kwargs)
