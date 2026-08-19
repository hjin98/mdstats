"""Universal GFX3D scene preparation over shared scientific dependencies."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .contracts import PreparedGraphicsScene3D, GraphicsScene3DRequest
from .context import GraphicsSceneContext
from .errors import Graphics3DDependencyError, Graphics3DRegistryError
from .layers import resolve_builtin_dependency
from .providers import GraphicsScientificProduct
from .manifest import GraphicsSceneManifest
from .registry import DEFAULT_GRAPHICS_LAYER_REGISTRY, GraphicsLayer3DAdapter, GraphicsLayerRegistry
from .scene import plan_graphics_scene_dependencies


def _dependency_workers(context: GraphicsSceneContext, count: int) -> int:
    if count <= 1:
        return 1
    resources = context.resources
    maximum = getattr(resources, "max_threads", None)
    if maximum is None and isinstance(resources, dict):
        maximum = resources.get("max_threads")
    try:
        maximum = int(maximum) if maximum is not None else 1
    except (TypeError, ValueError):
        maximum = 1
    return max(1, min(int(count), maximum))


def prepare_graphics3d_scene(
    request: GraphicsScene3DRequest,
    *,
    context: GraphicsSceneContext,
    registry: GraphicsLayerRegistry = DEFAULT_GRAPHICS_LAYER_REGISTRY,
) -> PreparedGraphicsScene3D:
    """Prepare enabled GFX3D layers from one shared scientific context.

    GFX3D-4 resolves product-level scientific dependencies. Equal scientific
    keys are single-flight cached by :class:`GraphicsSceneContext`; independent
    keys may begin concurrently, while source providers remain responsible for
    their owning subsystem's CPU/RAM admission and may batch qualified joint
    work internally.
    """

    plan = plan_graphics_scene_dependencies(request, context=context, registry=registry)

    def resolve_entry(entry):
        return context.resolve_dependency(
            entry.key,
            lambda key=entry.key: resolve_builtin_dependency(key, context),
        )

    workers = _dependency_workers(context, len(plan))
    if workers == 1:
        values = tuple(resolve_entry(entry) for entry in plan)
    else:
        with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="mdstats-gfx3d-dependency") as executor:
            futures = tuple(executor.submit(resolve_entry, entry) for entry in plan)
            # Construction order is authority; completion order is not.
            values = tuple(future.result() for future in futures)

    resolved_by_provider: dict[str, Any] = {
        entry.key.provider_type: value for entry, value in zip(plan, values, strict=True)
    }

    prepared = []
    for layer_request in request.enabled_layers:
        registration = registry.get(layer_request.layer_type)
        adapter = registration.adapter_factory()
        if not isinstance(adapter, GraphicsLayer3DAdapter):
            raise Graphics3DRegistryError(
                f"Adapter factory for {layer_request.layer_type!r} did not satisfy GraphicsLayer3DAdapter."
            )
        prepared.append(adapter.prepare(layer_request, resolved_by_provider, context))

    # Scene gauge/selection metadata must come from renderer-neutral product
    # authorities, never from an embedded compatibility scene.  Historical
    # in-memory FrameworkDynamicsScene input remains supported as a direct
    # legacy dependency value.
    scientific_products = tuple(value for value in values if isinstance(value, GraphicsScientificProduct))
    legacy_scene = next(
        (value for value in values if not isinstance(value, GraphicsScientificProduct) and hasattr(value, "display_cell")),
        None,
    )
    display_cells = [product.display_cell for product in scientific_products if product.display_cell is not None]
    display_cell = display_cells[0] if display_cells else getattr(legacy_scene, "display_cell", None)
    if display_cells:
        import numpy as np
        reference_cell = np.asarray(display_cells[0], dtype=np.float64)
        if any(not np.array_equal(np.asarray(cell, dtype=np.float64), reference_cell) for cell in display_cells[1:]):
            raise Graphics3DDependencyError("Resolved GFX3D scientific products disagree on the scene display cell.")
    source_metadata = {} if legacy_scene is None else dict(getattr(legacy_scene, "metadata", {}))
    product_provenance = [dict(product.provenance) for product in scientific_products]
    if product_provenance:
        for key in ("source_scene_schema", "source_framework_topology_digest", "registration_mode", "display_cell_policy"):
            values_for_key = {item.get(key) for item in product_provenance if item.get(key) is not None}
            if len(values_for_key) > 1:
                raise Graphics3DDependencyError(f"Resolved GFX3D scientific products disagree on {key!r}.")
            if values_for_key:
                source_metadata[key] = next(iter(values_for_key))
    if display_cell is None:
        for layer in prepared:
            for product in layer.product_refs.values():
                candidate = getattr(product, "display_cell", None)
                if candidate is None:
                    candidate = getattr(product, "cell", None)
                if candidate is not None:
                    display_cell = candidate
                    break
            if display_cell is not None:
                break
    provider_report = {}
    source = context.source
    report_method = getattr(source, "preparation_report", None)
    if callable(report_method):
        provider_report = dict(report_method())

    frame_sequences = [product.frame_indices for product in scientific_products if product.frame_indices]
    if frame_sequences and any(tuple(values) != tuple(frame_sequences[0]) for values in frame_sequences[1:]):
        raise Graphics3DDependencyError("Resolved GFX3D scientific products disagree on selected frame indices.")
    resolved_frames = (
        tuple(int(v) for v in frame_sequences[0])
        if frame_sequences
        else tuple(int(v) for v in getattr(legacy_scene, "frame_indices", ()))
    )

    manifest = GraphicsSceneManifest(
        request=request,
        dependency_plan=plan,
        frame_selection={"frame_indices": resolved_frames},
        coordinate_policy={"registration_mode": source_metadata.get("registration_mode")},
        display_cell_policy={"policy": source_metadata.get("display_cell_policy")},
    )
    return PreparedGraphicsScene3D(
        layers=tuple(prepared),
        manifest=manifest,
        display_gauge={} if display_cell is None else {"cell": display_cell},
        metadata={
            "schema_version": "mdstats.graphics3d.prepared-scene.gfx3d5.v1",
            "source_scene_schema": source_metadata.get("source_scene_schema", source_metadata.get("schema_version")),
            "dependency_cache_report": dict(context.cache_report()),
            "dependency_execution_report": {
                identity: dict(record) for identity, record in context.dependency_report().items()
            },
            "dependency_parallel_workers": int(workers),
            "dependency_cache_identity_includes_hit_state": False,
            "dependency_cache_policy": "in_memory_single_flight_v1",
            "durable_dependency_cache": False,
            "source_provider_report": provider_report,
        },
    )
