"""Compatibility adapters from the current composite framework-dynamics scene.

GFX3D-1 does not reimplement current scientific preparation.  This adapter
exposes existing prepared products as named universal prepared-layer records so
new infrastructure can be exercised without changing their definitions.
"""

from __future__ import annotations

from typing import Any

from .contracts import (
    GraphicsLayer3DRequest,
    GraphicsSelection,
    GraphicsScene3DRequest,
    PreparedGraphicsLayer3D,
    PreparedGraphicsScene3D,
)
from .identity import identity_digest
from .manifest import GraphicsSceneManifest

LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA = "mdstats.graphics3d.legacy-framework-dynamics.v1"


def _legacy_identity(kind: str, scene: Any, payload: dict[str, Any]) -> str:
    return identity_digest(
        LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA + "." + kind,
        {
            "source_schema": scene.metadata.get("schema_version"),
            "source_framework_topology_digest": scene.metadata.get("source_framework_topology_digest"),
            "frame_indices": scene.frame_indices,
            "registration_mode": scene.metadata.get("registration_mode"),
            **payload,
        },
    )


def adapt_framework_dynamics_scene(scene: Any) -> PreparedGraphicsScene3D:
    """Expose a current :class:`FrameworkDynamicsScene` through GFX3D contracts.

    This is deliberately a compatibility *view*. It does not recompute or alter
    framework, connectivity, trajectory, or density science.
    """

    from mdstats.plotting.framework_dynamics import FrameworkDynamicsScene

    if not isinstance(scene, FrameworkDynamicsScene):
        raise TypeError("scene must be FrameworkDynamicsScene.")

    requests: list[GraphicsLayer3DRequest] = []
    prepared: list[PreparedGraphicsLayer3D] = []

    framework_request = GraphicsLayer3DRequest(name="framework", layer_type="framework")
    requests.append(framework_request)
    prepared.append(
        PreparedGraphicsLayer3D(
            request=framework_request,
            scientific_identity=_legacy_identity("framework", scene, {}),
            product_refs={"mean_framework": scene.mean_framework},
            provenance={"adapter_schema": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA},
        )
    )

    if scene.atomic_mean_graph is not None:
        request = GraphicsLayer3DRequest(name="atomic connectivity", layer_type="connectivity")
        requests.append(request)
        prepared.append(
            PreparedGraphicsLayer3D(
                request=request,
                scientific_identity=_legacy_identity("connectivity", scene, {"present": True}),
                product_refs={"atomic_mean_graph": scene.atomic_mean_graph},
                provenance={"adapter_schema": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA},
            )
        )

    if scene.trajectory_paths is not None:
        atom_indices = tuple(int(value) for value in scene.trajectory_paths.atom_indices)
        request = GraphicsLayer3DRequest(
            name="trajectory",
            layer_type="trajectory",
            selection=GraphicsSelection(atom_indices=atom_indices),
        )
        requests.append(request)
        prepared.append(
            PreparedGraphicsLayer3D(
                request=request,
                scientific_identity=_legacy_identity("trajectory", scene, {"atom_indices": atom_indices}),
                product_refs={"trajectory_paths": scene.trajectory_paths},
                provenance={"adapter_schema": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA},
            )
        )

    for index, field in enumerate(scene.atomic_density_fields):
        label = str(getattr(field, "field_key", f"atomic density {index + 1}"))
        request = GraphicsLayer3DRequest(name=f"atomic density: {label}", layer_type="density")
        requests.append(request)
        prepared.append(
            PreparedGraphicsLayer3D(
                request=request,
                scientific_identity=_legacy_identity("density", scene, {"field_key": label}),
                product_refs={"density_field": field},
                provenance={"adapter_schema": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA},
            )
        )

    if scene.framework_density_fields is not None:
        for index, field in enumerate(scene.framework_density_fields.fields):
            label = str(getattr(field, "field_key", f"framework density {index + 1}"))
            request = GraphicsLayer3DRequest(name=f"framework density: {label}", layer_type="density")
            requests.append(request)
            prepared.append(
                PreparedGraphicsLayer3D(
                    request=request,
                    scientific_identity=_legacy_identity("framework_density", scene, {"field_key": label}),
                    product_refs={"density_field": field},
                    provenance={"adapter_schema": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA},
                )
            )

    scene_request = GraphicsScene3DRequest(
        layers=tuple(requests),
        scene_options={
            "registration_mode": scene.metadata.get("registration_mode"),
            "display_cell_policy": scene.metadata.get("display_cell_policy"),
        },
        metadata={"legacy_source_schema": scene.metadata.get("schema_version")},
    )
    manifest = GraphicsSceneManifest(
        request=scene_request,
        frame_selection={"frame_indices": tuple(int(v) for v in scene.frame_indices)},
        coordinate_policy={"registration_mode": scene.metadata.get("registration_mode")},
        display_cell_policy={"policy": scene.metadata.get("display_cell_policy")},
        warnings=("Prepared through the GFX3D-1 legacy FrameworkDynamicsScene adapter.",),
    )
    return PreparedGraphicsScene3D(
        layers=tuple(prepared),
        manifest=manifest,
        display_gauge={"cell": scene.display_cell},
        metadata={
            "adapter_schema": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA,
            "legacy_scene_schema": scene.metadata.get("schema_version"),
        },
    )


def adapt_framework_dynamics_render_result(result: Any):
    """Adapt the current fixed-field Plotly result to a generic layer-keyed result.

    Trace ownership is translated only; the original Plotly figure and scientific
    scene remain authoritative and are not re-rendered.
    """

    from mdstats.plotting.framework_dynamics import FrameworkDynamicsRenderResult
    from .render_result import Graphics3DRenderResult, GraphicsLayerRenderResult

    if not isinstance(result, FrameworkDynamicsRenderResult):
        raise TypeError("result must be FrameworkDynamicsRenderResult.")
    prepared = adapt_framework_dynamics_scene(result.scene)

    def flattened(mapping: Any) -> tuple[int, ...]:
        values: set[int] = set()
        for indices in mapping.values():
            values.update(int(value) for value in indices)
        return tuple(sorted(values))

    base_indices = set(result.base_result.cell_trace_indices)
    for mapping in (
        result.base_result.node_trace_indices,
        result.base_result.edge_trace_indices,
        result.base_result.hover_trace_indices,
    ):
        base_indices.update(flattened(mapping))

    layer_results: dict[str, GraphicsLayerRenderResult] = {}
    for layer in prepared.layers:
        name = layer.request.name
        if name == "framework":
            indices = tuple(sorted(int(value) for value in base_indices))
        elif name == "atomic connectivity":
            indices = flattened(result.atomic_mean_graph_trace_indices)
        elif name == "trajectory":
            indices = tuple(sorted(set(flattened(result.trajectory_trace_indices)) | set(result.endpoint_trace_indices)))
        elif name.startswith("atomic density: "):
            key = name.removeprefix("atomic density: ")
            indices = tuple(result.density_trace_indices.get(key, ()))
        elif name.startswith("framework density: "):
            key = name.removeprefix("framework density: ")
            indices = tuple(result.framework_density_trace_indices.get(key, ()))
        else:  # pragma: no cover - compatibility defensive branch
            indices = ()
        layer_results[name] = GraphicsLayerRenderResult(
            layer_name=name,
            backend_object_indices=indices,
            scientific_identity=layer.scientific_identity,
            render_identity=layer.render_identity,
            metadata={"legacy_result_adapter": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA},
        )

    return Graphics3DRenderResult(
        artifact=result.figure,
        scene=prepared,
        layer_results=layer_results,
        render_metadata={
            "legacy_result_adapter": LEGACY_FRAMEWORK_DYNAMICS_ADAPTER_SCHEMA,
            "browser_profile": result.browser_profile,
        },
        warnings=tuple(result.base_result.warnings),
    )
