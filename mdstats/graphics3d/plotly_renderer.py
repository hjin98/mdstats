"""Universal Plotly backend over renderer-neutral GFX3D primitives (GFX3D-5)."""
from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from typing import Any

import numpy as np

from .browser import GraphicsBrowserBudget, measure_browser_payload, scale_browser_payload
from .context import GraphicsSceneContext
from .contracts import PreparedGraphicsScene3D
from .errors import Graphics3DRegistryError, Graphics3DValidationError
from .primitives import (
    ArrowSet3D,
    CellWireframe3D,
    GraphicsPrimitive3D,
    PointSet3D,
    PolylineSet3D,
    SegmentSet3D,
    TextLabelSet3D,
    TriangleMesh3D,
)
from .registry import DEFAULT_GRAPHICS_LAYER_REGISTRY, GraphicsLayer3DAdapter, GraphicsLayerRegistry
from .render_result import Graphics3DRenderResult, GraphicsLayerRenderResult
from .view import replicate_primitive, resolve_camera, resolve_cell_mode, resolve_periodic_image_shifts, resolve_view_visibility

GFX3D5_PLOTLY_SCHEMA = "mdstats.graphics3d.plotly-render-result.gfx3d5.v1"


def _legacy_periodic_shifts(periodic: Any) -> tuple[tuple[int, int, int], ...] | None:
    if periodic is None:
        return None
    from mdstats.plotting.periodic_graph import CanonicalCellDisplay, ExpandedCellDisplay, LocalUnwrappedDisplay
    if isinstance(periodic, CanonicalCellDisplay):
        return ((0, 0, 0),)
    if isinstance(periodic, ExpandedCellDisplay):
        ranges = periodic.image_ranges
        return tuple(
            (i, j, k)
            for i in range(ranges[0][0], ranges[0][1] + 1)
            for j in range(ranges[1][0], ranges[1][1] + 1)
            for k in range(ranges[2][0], ranges[2][1] + 1)
        )
    if isinstance(periodic, LocalUnwrappedDisplay):
        raise Graphics3DValidationError(
            "LocalUnwrappedDisplay is graph-specific and is not a universal GFX3D view transform; "
            "use explicit view.periodic_images or keep the legacy graph renderer for that diagnostic."
        )
    raise Graphics3DValidationError(f"Unsupported periodic display object {type(periodic).__name__}.")


def _cell_from_scene(scene: PreparedGraphicsScene3D) -> np.ndarray | None:
    raw = scene.display_gauge.get("cell")
    if raw is None:
        for layer in scene.layers:
            for key in ("mean_framework", "atomic_mean_graph", "density_field"):
                product = layer.product_refs.get(key)
                if product is None:
                    continue
                raw = getattr(product, "cell", None)
                if raw is None:
                    raw = getattr(product, "display_cell", None)
                if raw is not None:
                    break
            if raw is not None:
                break
    if raw is None:
        return None
    cell = np.asarray(raw, dtype=np.float64)
    return cell if cell.shape == (3, 3) else None


def _line_xyz_from_segments(segments: np.ndarray) -> tuple[list[float | None], list[float | None], list[float | None]]:
    x: list[float | None] = []
    y: list[float | None] = []
    z: list[float | None] = []
    for start, stop in np.asarray(segments, dtype=np.float64):
        x.extend((float(start[0]), float(stop[0]), None))
        y.extend((float(start[1]), float(stop[1]), None))
        z.extend((float(start[2]), float(stop[2]), None))
    return x, y, z


def _line_xyz_from_polylines(points: np.ndarray, offsets: np.ndarray) -> tuple[list[float | None], list[float | None], list[float | None]]:
    x: list[float | None] = []
    y: list[float | None] = []
    z: list[float | None] = []
    for start, stop in zip(offsets[:-1], offsets[1:], strict=True):
        segment = points[int(start):int(stop)]
        if len(segment) == 0:
            continue
        x.extend([float(v) for v in segment[:, 0]] + [None])
        y.extend([float(v) for v in segment[:, 1]] + [None])
        z.extend([float(v) for v in segment[:, 2]] + [None])
    return x, y, z


def _cell_segments(cell: np.ndarray, origin: np.ndarray) -> np.ndarray:
    corners = np.asarray(
        [origin + np.asarray((i, j, k), dtype=float) @ cell for i in (0, 1) for j in (0, 1) for k in (0, 1)],
        dtype=np.float64,
    )
    keys = [(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    by_key = {key: corners[pos] for pos, key in enumerate(keys)}
    edges = []
    for key in keys:
        for axis in range(3):
            if key[axis] == 0:
                other = list(key); other[axis] = 1
                edges.append((by_key[key], by_key[tuple(other)]))
    return np.asarray(edges, dtype=np.float64)


def _primitive_trace(go: Any, primitive: GraphicsPrimitive3D, *, visible: bool, legend_group: str, group_title: str | None) -> Any:
    a = dict(primitive.render_attributes)
    name = str(a.get("name", primitive.primitive_id))
    showlegend = bool(a.get("showlegend", True))
    common = {
        "name": name,
        "legendgroup": legend_group,
        "showlegend": showlegend,
        "visible": True if visible else "legendonly",
        "hoverinfo": "skip",
    }
    if group_title is not None:
        common["legendgrouptitle"] = {"text": group_title}
    if isinstance(primitive, PointSet3D):
        marker: dict[str, Any] = {
            "size": float(a.get("size", 5.0)),
            "color": a.get("color", "rgb(80,80,80)"),
            "opacity": float(a.get("opacity", 1.0)),
            "symbol": a.get("symbol", "circle"),
        }
        intensities = a.get("intensities")
        if intensities is not None:
            marker.update({"color": intensities, "colorscale": [[0.0, a.get("color", "#999999")], [1.0, a.get("color", "#999999")]], "cmin": 0.0, "cmax": 1.0, "showscale": False})
        hover = a.get("hovertext")
        if hover is not None:
            common.update({"hoverinfo": None, "hovertext": hover, "hovertemplate": "%{hovertext}<extra></extra>"})
        return go.Scatter3d(x=primitive.positions[:, 0], y=primitive.positions[:, 1], z=primitive.positions[:, 2], mode="markers", marker=marker, **common)
    if isinstance(primitive, SegmentSet3D):
        x, y, z = _line_xyz_from_segments(primitive.segments)
        return go.Scatter3d(x=x, y=y, z=z, mode="lines", line={"color": a.get("color", "#777777"), "width": float(a.get("width", 2.0)), "dash": a.get("dash", "solid")}, opacity=float(a.get("opacity", 1.0)), **common)
    if isinstance(primitive, PolylineSet3D):
        x, y, z = _line_xyz_from_polylines(primitive.points, primitive.offsets)
        hover = a.get("hovertext")
        if hover is not None:
            hover_values = tuple(hover)
            if len(hover_values) != len(primitive.points):
                raise Graphics3DValidationError("Polyline hovertext must align one-to-one with primitive points.")
            expanded_hover: list[str | None] = []
            for start, stop in zip(primitive.offsets[:-1], primitive.offsets[1:], strict=True):
                expanded_hover.extend(str(v) for v in hover_values[int(start):int(stop)])
                expanded_hover.append(None)
            common.update({"hoverinfo": None, "text": expanded_hover, "hovertemplate": "%{text}<extra></extra>"})
        return go.Scatter3d(x=x, y=y, z=z, mode="lines", line={"color": a.get("color", "#777777"), "width": float(a.get("width", 2.0)), "dash": a.get("dash", "solid")}, opacity=float(a.get("opacity", 1.0)), **common)
    if isinstance(primitive, TriangleMesh3D):
        return go.Mesh3d(x=primitive.vertices[:, 0], y=primitive.vertices[:, 1], z=primitive.vertices[:, 2], i=primitive.faces[:, 0], j=primitive.faces[:, 1], k=primitive.faces[:, 2], color=a.get("color", "#6699cc"), opacity=float(a.get("opacity", 0.35)), flatshading=bool(a.get("flatshading", False)), lighting=a.get("lighting", {"ambient": 0.72, "diffuse": 0.58, "specular": 0.12, "roughness": 0.88, "fresnel": 0.04}), **common)
    if isinstance(primitive, ArrowSet3D):
        # Plotly cones are the backend-neutral arrow realization.
        return go.Cone(x=primitive.origins[:, 0], y=primitive.origins[:, 1], z=primitive.origins[:, 2], u=primitive.vectors[:, 0], v=primitive.vectors[:, 1], w=primitive.vectors[:, 2], colorscale=[[0, a.get("color", "#555555")], [1, a.get("color", "#555555")]], showscale=False, sizemode="absolute", sizeref=float(a.get("size", 1.0)), opacity=float(a.get("opacity", 1.0)), **common)
    if isinstance(primitive, TextLabelSet3D):
        return go.Scatter3d(x=primitive.positions[:, 0], y=primitive.positions[:, 1], z=primitive.positions[:, 2], mode="text", text=primitive.labels, textfont={"color": a.get("color", "#222222"), "size": int(a.get("size", 12))}, **common)
    if isinstance(primitive, CellWireframe3D):
        x, y, z = _line_xyz_from_segments(_cell_segments(primitive.cell, primitive.origin))
        return go.Scatter3d(x=x, y=y, z=z, mode="lines", line={"color": a.get("color", "#666666"), "width": float(a.get("width", 3.2))}, opacity=float(a.get("opacity", 0.72)), **common)
    raise Graphics3DValidationError(f"Plotly backend does not support primitive type {type(primitive).__name__}.")


def _primitive_positions(primitives: list[GraphicsPrimitive3D]) -> np.ndarray:
    arrays: list[np.ndarray] = []
    for p in primitives:
        if isinstance(p, PointSet3D): arrays.append(p.positions)
        elif isinstance(p, PolylineSet3D): arrays.append(p.points)
        elif isinstance(p, SegmentSet3D): arrays.append(p.segments.reshape(-1,3))
        elif isinstance(p, TriangleMesh3D): arrays.append(p.vertices)
        elif isinstance(p, ArrowSet3D): arrays.extend((p.origins, p.origins + p.vectors))
        elif isinstance(p, TextLabelSet3D): arrays.append(p.positions)
        elif isinstance(p, CellWireframe3D): arrays.append(_cell_segments(p.cell, p.origin).reshape(-1,3))
    arrays = [a for a in arrays if len(a)]
    return np.concatenate(arrays, axis=0) if arrays else np.zeros((1,3), dtype=float)


def _scene_ranges(positions: np.ndarray) -> tuple[list[float], list[float], list[float]]:
    lo = np.min(positions, axis=0); hi = np.max(positions, axis=0)
    span = hi - lo
    span[span < 1e-9] = max(float(np.max(span)), 1.0)
    pad = 0.05 * span
    return tuple([float(a), float(b)] for a, b in zip(lo-pad, hi+pad, strict=True))  # type: ignore[return-value]



def _resolve_mesh_profile(mesh_profile: Any, browser_profile: str) -> Any:
    """Return the density scene mesh profile used by universal rendering.

    GFX3D historically treated the density mesh profile as a per-shell hint and
    the generic browser profile as an unrelated final cap.  The two contracts
    now share one scene authority so density fitting happens before the generic
    payload preflight.
    """

    from mdstats.plotting.density_scene_fit import BrowserMeshProfile

    if mesh_profile is not None:
        if not isinstance(mesh_profile, BrowserMeshProfile):
            return BrowserMeshProfile.coerce(mesh_profile)
        return mesh_profile
    token = str(browser_profile).strip().lower()
    if token == "compact":
        return BrowserMeshProfile.compact()
    if token in {"quality", "raw_reference"}:
        return BrowserMeshProfile.quality()
    return BrowserMeshProfile.balanced()


def _density_scene_render_resources(
    scene: PreparedGraphicsScene3D,
    *,
    shifts: tuple[tuple[int, int, int], ...],
    mesh_profile: Any,
) -> dict[str, Any]:
    """Allocate one post-replication density face budget across all HDR shells."""

    from mdstats.plotting.atomic_density import AtomicDensity3DRenderOptions
    from mdstats.plotting.density_mesh_simplify import MeshSimplificationOptions
    from mdstats.plotting.density_scene_budget import (
        DensitySceneAllocationOptions,
        DensitySceneShellRequest,
        allocate_density_scene_budget,
    )

    allocation_options = DensitySceneAllocationOptions()
    requests: list[DensitySceneShellRequest] = []
    shell_importance = allocation_options.shell_importance
    replication = max(1, len(shifts))
    for layer in scene.layers:
        field = layer.product_refs.get("density_field")
        if field is None:
            continue
        opts = AtomicDensity3DRenderOptions(**dict(layer.request.render_options))
        if opts.render_mode != "mesh":
            continue
        for position, fraction in enumerate(opts.mass_fractions):
            details = field.hdr_details(float(fraction))
            importance = shell_importance[min(position, len(shell_importance) - 1)]
            requests.append(
                DensitySceneShellRequest(
                    shell_key=f"{layer.request.name}:{field.field_key}:{float(fraction):.12g}",
                    field_key=str(field.field_key),
                    label=str(field.label),
                    mass_fraction=float(fraction),
                    selected_node_count=int(details.selected_node_count),
                    display_replication=replication,
                    visual_importance=float(importance),
                    max_canonical_faces=int(opts.standalone_final_mesh_faces),
                    metadata={"owner_layer": layer.request.name, "shell_position": position},
                )
            )
    plan = allocate_density_scene_budget(
        requests,
        budget=mesh_profile.budget,
        options=allocation_options,
    )
    # Match the already-qualified legacy scene fitting policy.  These are
    # display-only constraints: scientific HDR thresholds/fields are unchanged.
    simplification = MeshSimplificationOptions(
        local_target_fraction=0.25,
        min_component_faces=4,
        max_attempts=6,
        aggressiveness=7.0,
        max_samples=10_000,
        max_surface_error_p99=0.06,
        max_surface_error_max=0.24,
        max_implicit_displacement_p99=0.04,
        max_normal_degradation_degrees=30.0,
        max_relative_scalar_residual_p99=0.35,
        hard_target=False,
    )
    return {
        "density_scene_budget_plan": plan,
        "density_mesh_simplification_options": simplification,
    }


def _fit_density_primitives_to_scene_budget(
    canonical_by_layer: dict[str, tuple[GraphicsPrimitive3D, ...]],
    scene: PreparedGraphicsScene3D,
    *,
    shifts: tuple[tuple[int, int, int], ...],
    mesh_profile: Any,
) -> tuple[dict[str, tuple[GraphicsPrimitive3D, ...]], dict[str, Any] | None]:
    """Closed-loop fit all density meshes under one browser budget.

    Per-shell extraction tries to meet the allocated target first.  This second
    pass is intentionally conditional and only runs if the aggregate geometry
    still overspends (for example because a topology-preserving simplification
    rejected its target).  That converts the old terminal 1.5M-face failure
    into the existing deterministic scene fitter instead of silently emitting
    an oversized browser artifact.
    """

    from mdstats.plotting.density_mesh_simplify import MeshSimplificationOptions
    from mdstats.plotting.density_node_cloud import prepare_density_node_cloud
    from mdstats.plotting.density_render_budget import (
        BrowserMeshBudgetFailure, BrowserMeshTraceUsage, BrowserMeshUsage, evaluate_browser_mesh_budget,
    )
    from mdstats.plotting.density_scene_fit import DensityShellGeometry, fit_density_scene_to_browser_budget

    layer_by_name = {layer.request.name: layer for layer in scene.layers}
    geometries: list[DensityShellGeometry] = []
    primitive_key_by_shell: dict[str, tuple[str, int]] = {}
    non_density_trace_count = 0
    replication = max(1, len(shifts))
    density_usage: list[BrowserMeshTraceUsage] = []
    for layer_name, primitives in canonical_by_layer.items():
        layer = layer_by_name[layer_name]
        field = layer.product_refs.get("density_field")
        for index, primitive in enumerate(primitives):
            if not isinstance(primitive, TriangleMesh3D) or field is None or "mass_fraction" not in primitive.render_attributes:
                non_density_trace_count += replication
                continue
            attrs = dict(primitive.render_attributes)
            shell_key = f"{layer_name}:{field.field_key}:{float(attrs['mass_fraction']):.12g}"
            cell = np.asarray(field.display_cell, dtype=np.float64)
            fractional = np.ascontiguousarray(np.asarray(primitive.vertices, dtype=np.float64) @ np.linalg.inv(cell))
            geometry = DensityShellGeometry(
                shell_key=shell_key,
                field=field,
                mass_fraction=float(attrs["mass_fraction"]),
                contour_level=float(attrs["hdr_threshold"]),
                vertices_fractional=fractional,
                vertices_cartesian=np.asarray(primitive.vertices, dtype=np.float64),
                faces=np.asarray(primitive.faces, dtype=np.int64),
                display_replication=replication,
                visual_importance=1.0,
                minimum_faces=min(int(primitive.faces.shape[0]), max(4, mesh_profile.minimum_canonical_faces_per_shell)),
                source_kind="gfx3d_density_mesh",
                metadata={"owner_layer": layer_name, "primitive_id": primitive.primitive_id},
            )
            geometries.append(geometry)
            primitive_key_by_shell[shell_key] = (layer_name, index)
            density_usage.append(BrowserMeshTraceUsage(
                trace_key=shell_key,
                face_count=int(primitive.faces.shape[0]),
                vertex_count=int(primitive.vertices.shape[0]),
                display_replication=replication,
                retained_array_bytes=int(primitive.vertices.nbytes + primitive.faces.nbytes),
            ))
    if not geometries:
        return canonical_by_layer, None
    initial_report = evaluate_browser_mesh_budget(
        BrowserMeshUsage(
            density_traces=tuple(density_usage),
            non_density_trace_count=non_density_trace_count,
        ),
        budget=mesh_profile.budget,
    )
    geometry_violations = tuple(v for v in initial_report.violations if not v.startswith("final_html_bytes="))
    if not geometry_violations:
        return canonical_by_layer, None

    fit_failure: BrowserMeshBudgetFailure | None = None
    try:
        fitted, report = fit_density_scene_to_browser_budget(
            geometries,
            profile=mesh_profile,
            non_density_trace_count=non_density_trace_count,
            simplification_options=MeshSimplificationOptions(
                local_target_fraction=0.25,
                min_component_faces=4,
                max_attempts=6,
                aggressiveness=7.0,
                max_samples=10_000,
                max_surface_error_p99=0.06,
                max_surface_error_max=0.24,
                max_implicit_displacement_p99=0.04,
                max_normal_degradation_degrees=30.0,
                max_relative_scalar_residual_p99=0.35,
                hard_target=False,
            ),
        )
    except BrowserMeshBudgetFailure as error:
        fit_failure = error
        fitted = ()
        report = None

    updated = {name: list(items) for name, items in canonical_by_layer.items()}
    if fit_failure is None:
        for geometry in fitted:
            layer_name, index = primitive_key_by_shell[geometry.shell_key]
            original = updated[layer_name][index]
            assert isinstance(original, TriangleMesh3D)
            attrs = dict(original.render_attributes)
            attrs.update({
                "scene_fit_applied": True,
                "scene_fit_source_kind": geometry.source_kind,
                "scene_fit_faces": int(geometry.face_count),
            })
            updated[layer_name][index] = TriangleMesh3D(
                owner_layer=original.owner_layer,
                primitive_id=original.primitive_id,
                vertices=geometry.vertices_cartesian,
                faces=geometry.faces,
                scientific_refs=original.scientific_refs,
                render_attributes=attrs,
            )
        return (
            {name: tuple(items) for name, items in updated.items()},
            report.to_json_dict() if report is not None else None,
        )

    # Universal-viewer safety valve: if topology-preserving simplification and
    # recontouring cannot satisfy the scene budget, retain the exact scientific
    # HDR threshold but switch the least-visible/highest-cost shells to the
    # deterministic HDR node-cloud representation.  This is preferable to a
    # terminal browser-budget failure after expensive density preparation.
    remaining_faces = sum(item.serialized_face_count for item in geometries)
    face_limit = int(mesh_profile.budget.max_final_density_faces)
    candidates = sorted(
        geometries,
        key=lambda item: (
            float(dict(updated[primitive_key_by_shell[item.shell_key][0]][primitive_key_by_shell[item.shell_key][1]].render_attributes).get("opacity", 1.0)),
            -item.serialized_face_count,
            item.shell_key,
        ),
    )
    fallback_shells: list[str] = []
    for geometry in candidates:
        if remaining_faces <= face_limit:
            break
        layer_name, index = primitive_key_by_shell[geometry.shell_key]
        original = updated[layer_name][index]
        assert isinstance(original, TriangleMesh3D)
        layer = layer_by_name[layer_name]
        field = layer.product_refs["density_field"]
        cloud_max_points = 40_000
        try:
            from mdstats.plotting.atomic_density import AtomicDensity3DRenderOptions
            cloud_max_points = AtomicDensity3DRenderOptions(**dict(layer.request.render_options)).cloud_max_points
        except Exception:
            pass
        cloud = prepare_density_node_cloud(
            field, geometry.mass_fraction, max_points=int(cloud_max_points)
        )
        attrs = dict(original.render_attributes)
        attrs.update({
            "scene_fit_applied": True,
            "scene_budget_fallback": "node_cloud",
            "sparse_fallback_mode": "scene_budget_node_cloud",
            "size": 2.2,
            "intensities": cloud.relative_intensities.tolist(),
        })
        updated[layer_name][index] = PointSet3D(
            owner_layer=original.owner_layer,
            primitive_id=original.primitive_id + "-budget-cloud",
            positions=cloud.cartesian_positions,
            scientific_refs=original.scientific_refs,
            render_attributes=attrs,
        )
        remaining_faces -= geometry.serialized_face_count
        fallback_shells.append(geometry.shell_key)
    if remaining_faces > face_limit:
        raise fit_failure
    return (
        {name: tuple(items) for name, items in updated.items()},
        {
            "passed": True,
            "fallback": "node_cloud",
            "fallback_shells": fallback_shells,
            "remaining_serialized_density_faces": int(remaining_faces),
            "original_fit_failure": fit_failure.to_json_dict(),
        },
    )

def render_graphics3d_plotly(
    scene: PreparedGraphicsScene3D,
    *,
    periodic: Any = None,
    browser_profile: str = "interactive_browser",
    mesh_profile: Any = None,
    registry: GraphicsLayerRegistry = DEFAULT_GRAPHICS_LAYER_REGISTRY,
) -> Graphics3DRenderResult:
    """Render a prepared GFX3D scene using only renderer-neutral primitives."""
    if not isinstance(scene, PreparedGraphicsScene3D):
        raise Graphics3DValidationError("scene must be PreparedGraphicsScene3D.")
    if not scene.layers:
        raise Graphics3DValidationError("Prepared GFX3D scene has no enabled layers.")
    import plotly.graph_objects as go

    view = dict(scene.manifest.request.view)
    legacy_shifts = _legacy_periodic_shifts(periodic)
    shifts = legacy_shifts if legacy_shifts is not None else resolve_periodic_image_shifts(view)
    cell = _cell_from_scene(scene)
    cell_mode = resolve_cell_mode(view)
    layer_names = tuple(layer.request.name for layer in scene.layers)
    visible_override = resolve_view_visibility(view, layer_names)

    profile_name = browser_profile
    if mesh_profile is not None:
        profile_name = str(getattr(mesh_profile, "name", getattr(mesh_profile, "profile", profile_name)))
        if profile_name not in {"compact", "balanced", "quality", "interactive_browser", "raw_reference", "custom"}:
            profile_name = "balanced"
    resolved_mesh_profile = _resolve_mesh_profile(mesh_profile, browser_profile)
    density_render_resources = _density_scene_render_resources(
        scene, shifts=shifts, mesh_profile=resolved_mesh_profile
    )

    render_context = GraphicsSceneContext(
        source=scene,
        source_identity=getattr(scene.manifest, "scene_identity", None),
        resources={
            "mesh_profile": resolved_mesh_profile,
            "browser_profile": browser_profile,
            **density_render_resources,
        },
    )
    canonical_by_layer: dict[str, tuple[GraphicsPrimitive3D, ...]] = {}
    ordered_layers = sorted(
        enumerate(scene.layers),
        key=lambda item: (item[1].request.render_priority, item[0]),
    )
    for _, layer in ordered_layers:
        registration = registry.get(layer.request.layer_type)
        adapter = registration.adapter_factory()
        if not isinstance(adapter, GraphicsLayer3DAdapter):
            raise Graphics3DRegistryError(
                f"Adapter for {layer.request.layer_type!r} does not satisfy GraphicsLayer3DAdapter."
            )
        canonical = tuple(adapter.render_primitives(layer, render_context))
        if any(not isinstance(p, GraphicsPrimitive3D) for p in canonical):
            raise Graphics3DValidationError(
                f"Layer {layer.request.name!r} emitted a non-GFX3D primitive."
            )
        canonical_by_layer[layer.request.name] = canonical

    canonical_by_layer, density_scene_fit_report = _fit_density_primitives_to_scene_budget(
        canonical_by_layer, scene, shifts=shifts, mesh_profile=resolved_mesh_profile
    )
    canonical_all: list[GraphicsPrimitive3D] = [
        primitive
        for _, layer in ordered_layers
        for primitive in canonical_by_layer[layer.request.name]
    ]

    # The display cell is scene/view state, not framework-layer content.  This
    # keeps density-only, trajectory-only, and future ring/site scenes visually
    # self-contained without inventing a framework dependency.
    canonical_scene_primitives: tuple[GraphicsPrimitive3D, ...] = ()
    if cell_mode == "reference" and cell is not None:
        canonical_scene_primitives = (
            CellWireframe3D(
                owner_layer="__scene__",
                primitive_id="scene-cell",
                cell=cell,
                origin=np.zeros(3, dtype=np.float64),
                scientific_refs=(),
                render_attributes={
                    "name": "Unit cell",
                    "color": "#666666",
                    "width": 3.2,
                    "opacity": 0.72,
                    "showlegend": False,
                    "view_role": "cell",
                },
            ),
        )
        canonical_all.extend(canonical_scene_primitives)

    # Fail before allocating replicated primitive arrays.  Periodic replication
    # is an exact multiplicative display transform for every canonical primitive.
    canonical_payload = measure_browser_payload(canonical_all)
    predicted_payload = scale_browser_payload(canonical_payload, len(shifts))
    base_budget = GraphicsBrowserBudget.for_profile(
        "balanced" if profile_name == "custom" else profile_name
    )
    # An explicit/custom density face budget must propagate through the universal
    # browser preflight too.  Reserve the exact non-density faces on top of the
    # density budget instead of retaining the unrelated historical 1.5M cap.
    density_faces_canonical = sum(
        len(primitive.faces)
        for layer in scene.layers
        if layer.product_refs.get("density_field") is not None
        for primitive in canonical_by_layer.get(layer.request.name, ())
        if isinstance(primitive, TriangleMesh3D) and "mass_fraction" in primitive.render_attributes
    )
    non_density_faces_serialized = max(0, predicted_payload.face_count - density_faces_canonical * len(shifts))
    budget = replace(
        base_budget,
        max_faces=max(
            int(base_budget.max_faces),
            int(resolved_mesh_profile.budget.max_final_density_faces) + int(non_density_faces_serialized),
        ),
    )
    budget.validate(predicted_payload)

    materialized_by_layer: dict[str, tuple[GraphicsPrimitive3D, ...]] = {}
    all_materialized: list[GraphicsPrimitive3D] = []
    for _, layer in ordered_layers:
        expanded: list[GraphicsPrimitive3D] = []
        for primitive in canonical_by_layer[layer.request.name]:
            expanded.extend(replicate_primitive(primitive, cell=cell, shifts=shifts))
        materialized_by_layer[layer.request.name] = tuple(expanded)
        all_materialized.extend(expanded)
    materialized_scene: list[GraphicsPrimitive3D] = []
    for primitive in canonical_scene_primitives:
        materialized_scene.extend(replicate_primitive(primitive, cell=cell, shifts=shifts))
    all_materialized.extend(materialized_scene)

    payload = measure_browser_payload(all_materialized)
    budget.validate(payload)
    if payload != predicted_payload:
        raise Graphics3DValidationError(
            "GFX3D browser payload prediction disagrees with materialized payload; "
            "periodic replication accounting is not trustworthy."
        )

    figure = go.Figure()
    temporary_indices: dict[str, list[int]] = {name: [] for name in layer_names}
    warnings: list[str] = []

    # Scene-owned cell traces render behind layer content and are intentionally
    # absent from layer trace ownership/legend groups.
    scene_trace_indices: list[int] = []
    for primitive in materialized_scene:
        figure.add_trace(
            _primitive_trace(
                go,
                primitive,
                visible=True,
                legend_group="__scene__",
                group_title=None,
            )
        )
        scene_trace_indices.append(len(figure.data) - 1)

    for _, layer in ordered_layers:
        visible = (
            layer.request.initially_visible
            if visible_override is None
            else layer.request.name in visible_override
        )
        first_group_trace = True
        for primitive in materialized_by_layer[layer.request.name]:
            trace = _primitive_trace(
                go,
                primitive,
                visible=visible,
                legend_group=layer.request.name,
                group_title=layer.request.name if first_group_trace else None,
            )
            first_group_trace = False
            figure.add_trace(trace)
            temporary_indices[layer.request.name].append(len(figure.data) - 1)

    positions = _primitive_positions(all_materialized)
    ranges = _scene_ranges(positions)
    show_axes = bool(view.get("show_axes", False))
    background = str(view.get("background", "light"))
    if background == "dark":
        paper, scene_color, font = "#111111", "#111111", "#F2F2F2"
    elif background == "transparent":
        paper, scene_color, font = "rgba(0,0,0,0)", "rgba(0,0,0,0)", "#202020"
    elif background == "light":
        paper, scene_color, font = "white", "white", "#202020"
    else:
        raise Graphics3DValidationError(
            "view.background must be 'light', 'dark', or 'transparent'."
        )
    axis = {
        "visible": show_axes,
        "showgrid": show_axes,
        "zeroline": False,
        "showbackground": show_axes,
        "backgroundcolor": scene_color,
    }
    figure.update_layout(
        width=int(view.get("width", 1000)),
        height=int(view.get("height", 800)),
        paper_bgcolor=paper,
        plot_bgcolor=paper,
        font={"color": font},
        scene={
            "xaxis": {**axis, "title": "x", "range": ranges[0]},
            "yaxis": {**axis, "title": "y", "range": ranges[1]},
            "zaxis": {**axis, "title": "z", "range": ranges[2]},
            "camera": resolve_camera(view),
            "aspectmode": "data",
            "bgcolor": scene_color,
        },
        legend={"itemsizing": "constant", "groupclick": "togglegroup", "tracegroupgap": 4},
        uirevision="mdstats-gfx3d-v1",
    )

    layer_results = OrderedDict()
    for layer in scene.layers:
        layer_payload = measure_browser_payload(materialized_by_layer.get(layer.request.name, ()))
        layer_results[layer.request.name] = GraphicsLayerRenderResult(
            layer_name=layer.request.name,
            backend_object_indices=tuple(temporary_indices[layer.request.name]),
            legend_group=layer.request.name,
            scientific_identity=layer.scientific_identity,
            render_identity=layer.render_identity,
            metadata={
                "renderer": "plotly",
                "gfx3d_gate": "GFX3D-HARDEN1",
                "primitive_count": len(canonical_by_layer.get(layer.request.name, ())),
                "display_primitive_count": len(materialized_by_layer.get(layer.request.name, ())),
                "browser_payload": layer_payload.to_json_dict(),
                "render_priority": int(layer.request.render_priority),
            },
        )
    return Graphics3DRenderResult(
        artifact=figure,
        scene=scene,
        layer_results=layer_results,
        render_metadata={
            "renderer": "plotly",
            "schema_version": GFX3D5_PLOTLY_SCHEMA,
            "layer_count": len(scene.layers),
            "periodic_image_shifts": tuple(tuple(v) for v in shifts),
            "browser_profile": profile_name,
            "browser_payload": payload.to_json_dict(),
            "browser_payload_pre_materialization": predicted_payload.to_json_dict(),
            "browser_budget_pre_materialization_passed": True,
            "density_scene_fit": density_scene_fit_report,
            "density_scene_budget_plan": density_render_resources["density_scene_budget_plan"].to_json_dict(),
            "browser_budget": {
                "max_traces": budget.max_traces,
                "max_points": budget.max_points,
                "max_faces": budget.max_faces,
                "max_geometry_bytes": budget.max_geometry_bytes,
            },
            "scene_trace_indices": tuple(scene_trace_indices),
            "scene_cell_mode": cell_mode,
            "view": view,
            "scientific_identity_includes_view": False,
        },
        warnings=tuple(warnings),
    )

