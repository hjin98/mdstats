"""Built-in GFX3D layer adapters.

GFX3D-4 makes the four layer families depend on product-level scientific keys.
Prepared ``FrameworkDynamicsScene`` input remains supported as a historical
compatibility source, but raw CLI scenes no longer expose one monolithic scene
key to every layer.
"""

from __future__ import annotations

from dataclasses import replace

from dataclasses import dataclass
from typing import Any

import numpy as np
from ase.data import atomic_numbers, chemical_symbols
from ase.data.colors import jmol_colors

from .contracts import (
    GraphicsDependencyKey,
    GraphicsDependencyRequest,
    GraphicsLayer3DRequest,
    GraphicsSelection,
    PreparedGraphicsLayer3D,
)
from .context import GraphicsSceneContext
from .errors import Graphics3DDependencyError, Graphics3DValidationError
from .identity import identity_digest
from .registry import GraphicsLayerRegistration, GraphicsLayerRegistry
from .primitives import PointSet3D, PolylineSet3D, SegmentSet3D, TriangleMesh3D
from .providers import (
    CONNECTIVITY_PRODUCT_PROVIDER,
    DENSITY_PRODUCT_PROVIDER,
    FRAMEWORK_PRODUCT_PROVIDER,
    TRAJECTORY_PRODUCT_PROVIDER,
    GraphicsDensityProduct,
    GraphicsScientificProduct,
    resolve_source_dependency,
    source_dependency_key,
)

GFX3D2_LAYER_SCHEMA = "mdstats.graphics3d.layer-adapter.v2"
GFX3D4_LAYER_SCHEMA = "mdstats.graphics3d.layer-adapter.v4"
LEGACY_SCENE_PROVIDER = "framework_dynamics_scene"




def _css_jmol(number: int) -> str:
    rgb = np.asarray(jmol_colors[int(number)], dtype=np.float64)
    return f"rgb({round(rgb[0]*255)}, {round(rgb[1]*255)}, {round(rgb[2]*255)})"


def _framework_render_primitives(prepared: PreparedGraphicsLayer3D) -> tuple[Any, ...]:
    graph = prepared.product_refs["mean_framework"]
    if graph.node_positions_3d is None:
        raise Graphics3DValidationError("Framework topology layer requires finite 3-D node positions.")
    positions = np.asarray(graph.node_positions_3d, dtype=np.float64)
    shifts = (
        np.zeros((len(graph.edge_endpoints), 3), dtype=np.int64)
        if graph.edge_image_shifts is None
        else np.asarray(graph.edge_image_shifts, dtype=np.int64)
    )
    cell = np.asarray(graph.cell, dtype=np.float64) if graph.cell is not None else None
    segments = np.empty((len(graph.edge_endpoints), 2, 3), dtype=np.float64)
    for idx, (edge, shift) in enumerate(zip(graph.edge_endpoints, shifts, strict=True)):
        i, j = map(int, edge)
        segments[idx, 0] = positions[i]
        segments[idx, 1] = positions[j] + (np.asarray(shift, dtype=np.float64) @ cell if cell is not None else 0.0)
    options = dict(prepared.request.render_options)
    edge_color = str(options.get("edge_color", "rgb(100,100,100)"))
    edge_width = float(options.get("edge_width", 3.0))
    edge_opacity = float(options.get("edge_opacity", 0.70))
    node_size = float(options.get("node_size", 7.0))
    node_opacity = float(options.get("node_opacity", 0.96))
    allowed = {"edge_color", "edge_width", "edge_opacity", "node_size", "node_opacity", "show_legend"}
    unknown = set(options) - allowed
    if unknown:
        raise Graphics3DValidationError("Unsupported framework render options: " + ", ".join(sorted(unknown)))
    numbers = graph.node_attributes.get("atomic_number")
    primitives: list[Any] = [
        SegmentSet3D(
            owner_layer=prepared.request.name, primitive_id="framework-edges", segments=segments,
            scientific_refs=(prepared.scientific_identity,),
            render_attributes={"name": "Framework bonds", "color": edge_color, "width": edge_width, "opacity": edge_opacity, "showlegend": False},
        )
    ]
    if numbers is None:
        primitives.append(PointSet3D(
            owner_layer=prepared.request.name, primitive_id="framework-nodes", positions=positions,
            scientific_refs=(prepared.scientific_identity,),
            render_attributes={"name": "Framework", "size": node_size, "color": "rgb(80,80,80)", "opacity": node_opacity, "showlegend": bool(options.get("show_legend", True))},
        ))
    else:
        nums = np.asarray(numbers, dtype=np.int64)
        for number in sorted(set(int(v) for v in nums.tolist())):
            mask = nums == number
            primitives.append(PointSet3D(
                owner_layer=prepared.request.name, primitive_id=f"framework-nodes-{number}", positions=positions[mask],
                scientific_refs=(prepared.scientific_identity,),
                render_attributes={"name": chemical_symbols[number], "size": node_size, "color": _css_jmol(number), "opacity": node_opacity, "showlegend": bool(options.get("show_legend", True))},
            ))
    return tuple(primitives)


def _connectivity_render_primitives(prepared: PreparedGraphicsLayer3D) -> tuple[Any, ...]:
    from mdstats.plotting.framework_dynamics import AtomicMeanGraph3DRenderOptions
    graph = prepared.product_refs["atomic_mean_graph"]
    opts = AtomicMeanGraph3DRenderOptions(**dict(prepared.request.render_options))
    positions = np.asarray(graph.display_positions, dtype=np.float64)
    cell = np.asarray(graph.display_cell, dtype=np.float64)
    segments = np.empty((len(graph.edge_endpoints), 2, 3), dtype=np.float64)
    for idx, ((i, j), shift) in enumerate(zip(graph.edge_endpoints, graph.edge_image_shifts, strict=True)):
        segments[idx, 0] = positions[int(i)]
        segments[idx, 1] = positions[int(j)] + np.asarray(shift, dtype=np.float64) @ cell
    primitives: list[Any] = []
    if len(segments):
        primitives.append(SegmentSet3D(
            owner_layer=prepared.request.name, primitive_id="connectivity-edges", segments=segments,
            scientific_refs=(prepared.scientific_identity,),
            render_attributes={"name": "Atomic bonds", "color": opts.edge_color, "width": opts.edge_width, "opacity": opts.edge_opacity, "showlegend": opts.show_legend},
        ))
    numbers = np.asarray(graph.atomic_numbers, dtype=np.int64)
    atoms = tuple(int(v) for v in graph.atom_indices)
    for number in sorted(set(int(v) for v in numbers.tolist())):
        mask = numbers == number
        hover = tuple(f"atom={atoms[i]}<br>species={chemical_symbols[number]}" for i in np.flatnonzero(mask))
        primitives.append(PointSet3D(
            owner_layer=prepared.request.name, primitive_id=f"connectivity-nodes-{number}", positions=positions[mask],
            scientific_refs=(prepared.scientific_identity,),
            render_attributes={"name": chemical_symbols[number], "size": opts.node_size, "color": _css_jmol(number), "opacity": opts.node_opacity, "showlegend": opts.show_legend, "hovertext": hover},
        ))
    return tuple(primitives)


def _trajectory_polylines(paths: Any, atom_positions: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    points: list[np.ndarray] = []
    offsets = [0]
    for local_index in atom_positions:
        coords = np.asarray(paths.display_positions[int(local_index)], dtype=np.float64)
        breaks = np.asarray(paths.segment_breaks[int(local_index)], dtype=bool)
        start = 0
        for position, is_break in enumerate(breaks):
            if is_break:
                segment = coords[start:position+1]
                if len(segment) >= 2:
                    points.append(segment); offsets.append(offsets[-1] + len(segment))
                start = position + 1
        segment = coords[start:]
        if len(segment) >= 2:
            points.append(segment); offsets.append(offsets[-1] + len(segment))
    if not points:
        return np.empty((0,3), dtype=np.float64), np.asarray([0], dtype=np.int64)
    return np.concatenate(points, axis=0), np.asarray(offsets, dtype=np.int64)


def _trajectory_hovertext(paths: Any, atom_positions: np.ndarray) -> tuple[str, ...]:
    """Return hover labels aligned exactly with ``_trajectory_polylines`` points."""

    labels: list[str] = []
    for local_index in atom_positions:
        local = int(local_index)
        atom = int(paths.atom_indices[local])
        symbol = chemical_symbols[int(paths.atomic_numbers[local])]
        n_frames = len(paths.frame_indices)
        breaks = np.asarray(paths.segment_breaks[local], dtype=bool)
        start = 0
        spans: list[tuple[int, int]] = []
        for position, is_break in enumerate(breaks):
            if is_break:
                stop = position + 1
                if stop - start >= 2:
                    spans.append((start, stop))
                start = position + 1
        if n_frames - start >= 2:
            spans.append((start, n_frames))
        for left, right in spans:
            for frame_position in range(left, right):
                time_text = (
                    ""
                    if paths.times is None
                    else f"<br>time={float(paths.times[frame_position]):.6g} fs"
                )
                labels.append(
                    f"atom={atom} ({symbol})<br>frame={int(paths.frame_indices[frame_position])}"
                    f"<br>frame_id={int(paths.frame_ids[frame_position])}{time_text}"
                )
    return tuple(labels)


def _trajectory_render_primitives(prepared: PreparedGraphicsLayer3D) -> tuple[Any, ...]:
    from mdstats.plotting.framework_dynamics import Trajectory3DRenderOptions
    paths = prepared.product_refs["trajectory_paths"]
    opts = Trajectory3DRenderOptions(**dict(prepared.request.render_options))
    numbers = np.asarray(paths.atomic_numbers, dtype=np.int64)
    primitives: list[Any] = []
    groups = [(number, np.flatnonzero(numbers == number)) for number in sorted(set(int(v) for v in numbers.tolist()))]
    if not opts.group_by_species:
        groups = [(int(numbers[i]), np.asarray([i], dtype=np.int64)) for i in range(len(numbers))]
    for group_position, (number, indices) in enumerate(groups):
        points, offsets = _trajectory_polylines(paths, indices)
        if len(points):
            label = chemical_symbols[number] if opts.group_by_species else f"{chemical_symbols[number]} atom {paths.atom_indices[int(indices[0])]}"
            attributes = {
                "name": label,
                "color": _css_jmol(number),
                "width": opts.line_width,
                "opacity": opts.opacity,
                "showlegend": opts.show_legend,
            }
            if opts.enable_hover:
                hover = _trajectory_hovertext(paths, indices)
                if len(hover) != len(points):
                    raise Graphics3DValidationError("Trajectory hover labels are not aligned with rendered polyline points.")
                attributes["hovertext"] = hover
            primitives.append(PolylineSet3D(
                owner_layer=prepared.request.name, primitive_id=f"trajectory-{group_position}", points=points, offsets=offsets,
                scientific_refs=(prepared.scientific_identity,),
                render_attributes=attributes,
            ))
        if opts.show_start_end and len(indices):
            starts = np.asarray(paths.display_positions, dtype=np.float64)[indices, 0, :]
            ends = np.asarray(paths.display_positions, dtype=np.float64)[indices, -1, :]
            start_attributes = {"name": "start", "color": _css_jmol(number), "size": opts.endpoint_size, "opacity": 1.0, "symbol": "circle", "showlegend": False}
            end_attributes = {"name": "end", "color": _css_jmol(number), "size": opts.endpoint_size, "opacity": 1.0, "symbol": "diamond", "showlegend": False}
            if opts.enable_hover:
                start_attributes["hovertext"] = tuple(
                    f"start: {chemical_symbols[int(paths.atomic_numbers[int(local)])]} atom {int(paths.atom_indices[int(local)])}"
                    for local in indices
                )
                end_attributes["hovertext"] = tuple(
                    f"end: {chemical_symbols[int(paths.atomic_numbers[int(local)])]} atom {int(paths.atom_indices[int(local)])}"
                    for local in indices
                )
            primitives.append(PointSet3D(
                owner_layer=prepared.request.name, primitive_id=f"trajectory-start-{group_position}", positions=starts,
                scientific_refs=(prepared.scientific_identity,), render_attributes=start_attributes,
            ))
            primitives.append(PointSet3D(
                owner_layer=prepared.request.name, primitive_id=f"trajectory-end-{group_position}", positions=ends,
                scientific_refs=(prepared.scientific_identity,), render_attributes=end_attributes,
            ))
    return tuple(primitives)


def _density_render_primitives(prepared: PreparedGraphicsLayer3D, context: GraphicsSceneContext) -> tuple[Any, ...]:
    from mdstats.plotting.atomic_density import (
        AtomicDensity3DRenderOptions,
        density_mesh_arrays,
        density_voxel_cloud_arrays,
    )
    from mdstats.plotting.density_contracts import LOCAL_SPARSE_BACKEND
    from mdstats.plotting.density_mesh_contracts import DensityMeshFaceContract
    from mdstats.plotting.density_sparse_mesh import prepare_sparse_density_mesh
    from mdstats.plotting.density_node_cloud import prepare_density_node_cloud
    from mdstats.plotting.graph_errors import GraphComplexityError

    field = prepared.product_refs["density_field"]
    opts = AtomicDensity3DRenderOptions(**dict(prepared.request.render_options))
    number = None
    if prepared.request.selection.species and len(prepared.request.selection.species) == 1:
        number = int(atomic_numbers[prepared.request.selection.species[0]])
    color = _css_jmol(number) if number is not None else "rgb(70,110,210)"
    fractions = tuple(float(v) for v in opts.mass_fractions)
    primitives: list[Any] = []
    if opts.render_mode == "mesh":
        maximum = int(opts.standalone_final_mesh_faces)
        resources = context.resources
        scene_budget_plan = None
        simplification_base = None
        if isinstance(resources, dict):
            profile = resources.get("mesh_profile")
            budget = getattr(profile, "budget", None)
            if budget is not None:
                maximum = min(maximum, int(getattr(budget, "max_final_density_faces", maximum)))
            scene_budget_plan = resources.get("density_scene_budget_plan")
            simplification_base = resources.get("density_mesh_simplification_options")
        n = max(1, len(fractions) - 1)
        for position, fraction in enumerate(fractions):
            alpha = opts.inner_opacity + (opts.outer_opacity - opts.inner_opacity) * (position / n)
            if getattr(field, "storage_backend", None) == LOCAL_SPARSE_BACKEND:
                try:
                    # GFX3D owns a *scene* browser budget, so a per-shell face
                    # count is a visual target rather than the legacy standalone
                    # renderer's hard final limit.  Let the generic browser
                    # preflight enforce the authoritative aggregate scene cap.
                    shell_key = f"{prepared.request.name}:{field.field_key}:{float(fraction):.12g}"
                    target_faces = maximum
                    if scene_budget_plan is not None:
                        target_faces = int(
                            scene_budget_plan.allocation_for(shell_key).target_canonical_faces
                        )
                    face_contract = DensityMeshFaceContract.scene_controller(
                        raw_extraction_face_limit=max(maximum, 8 * maximum),
                        visual_target_faces=target_faces,
                        metadata={"owner": "mdstats.graphics3d", "shell_key": shell_key},
                    )
                    simplification = None
                    if simplification_base is not None:
                        shell_fidelity = (
                            {
                                "max_surface_error_p99": 0.11,
                                "max_surface_error_max": 1.20,
                                "max_implicit_displacement_p99": 0.23,
                                "max_normal_degradation_degrees": 66.0,
                                "max_relative_scalar_residual_p99": 3.20,
                            },
                            {
                                "max_surface_error_p99": 0.10,
                                "max_surface_error_max": 0.50,
                                "max_implicit_displacement_p99": 0.10,
                                "max_normal_degradation_degrees": 50.0,
                                "max_relative_scalar_residual_p99": 2.0,
                            },
                            {
                                "max_surface_error_p99": 0.35,
                                "max_surface_error_max": 2.5,
                                "max_implicit_displacement_p99": 0.40,
                                "max_normal_degradation_degrees": 85.0,
                                "max_relative_scalar_residual_p99": 40.0,
                            },
                        )[min(position, 2)]
                        simplification = replace(
                            simplification_base,
                            target_faces=target_faces,
                            hard_target=False,
                            **shell_fidelity,
                        )
                    surface = prepare_sparse_density_mesh(
                        field,
                        fraction,
                        face_contract=face_contract,
                        allow_cloud_fallback=True,
                        cloud_max_points=opts.cloud_max_points,
                        simplification_options=simplification,
                    )
                except GraphComplexityError as error:
                    # A valid scientific sparse field must not make the universal
                    # viewer fail merely because its explicit contour marginally
                    # exceeds the browser face contract.  Fall back to the same
                    # deterministic HDR node cloud used by the legacy renderer.
                    if "max_mesh_faces" not in str(error):
                        raise
                    cloud = prepare_density_node_cloud(
                        field, fraction, max_points=opts.cloud_max_points
                    )
                    from mdstats.plotting.density_sparse_mesh import PreparedSparseDensitySurface
                    surface = PreparedSparseDensitySurface(
                        render_kind="node_cloud",
                        mesh=None,
                        cloud=cloud,
                        fallback_mode="node_cloud",
                    )
                if surface.render_kind == "node_cloud":
                    assert surface.cloud is not None
                    cloud = surface.cloud
                    primitives.append(PointSet3D(
                        owner_layer=prepared.request.name,
                        primitive_id=f"density-shell-cloud-{position}",
                        positions=cloud.cartesian_positions,
                        scientific_refs=(prepared.scientific_identity, str(field.field_key)),
                        render_attributes={
                            "name": str(field.label),
                            "size": opts.cloud_point_size,
                            "color": color,
                            "opacity": float(opts.cloud_opacity),
                            "showlegend": bool(opts.show_legend and position == len(fractions) - 1),
                            "intensities": cloud.relative_intensities.tolist(),
                            "hdr_threshold": float(cloud.hdr_details.threshold),
                            "sparse_fallback_mode": surface.fallback_mode,
                        },
                    ))
                    continue
                assert surface.mesh is not None
                mesh = surface.mesh
                vertices = mesh.vertices_cartesian
                faces = mesh.faces
                threshold = mesh.scientific_hdr_threshold
                sparse_metadata = {
                    "render_level": float(mesh.render_level),
                    "achieved_mass_fraction": float(mesh.achieved_mass_fraction),
                    "sparse_fallback_mode": surface.fallback_mode,
                }
            else:
                vertices, faces, threshold = density_mesh_arrays(field, fraction, max_faces=maximum)
                sparse_metadata = {}
            primitives.append(TriangleMesh3D(
                owner_layer=prepared.request.name, primitive_id=f"density-shell-{position}", vertices=vertices, faces=faces,
                scientific_refs=(prepared.scientific_identity, str(field.field_key)),
                render_attributes={
                    "name": str(field.label),
                    "color": color,
                    "opacity": float(alpha),
                    "showlegend": bool(opts.show_legend and position == len(fractions)-1),
                    "mass_fraction": fraction,
                    "hdr_threshold": float(threshold),
                    **sparse_metadata,
                },
            ))
    else:
        points, intensities, threshold = density_voxel_cloud_arrays(field, fractions[-1], max_points=opts.cloud_max_points)
        primitives.append(PointSet3D(
            owner_layer=prepared.request.name, primitive_id="density-cloud", positions=points,
            scientific_refs=(prepared.scientific_identity, str(field.field_key)),
            render_attributes={"name": str(field.label), "size": opts.cloud_point_size, "color": color, "opacity": opts.cloud_opacity, "showlegend": opts.show_legend, "intensities": intensities.tolist(), "hdr_threshold": float(threshold)},
        ))
    if opts.show_samples and getattr(field, "sample_positions", None) is not None:
        samples = np.asarray(field.sample_positions, dtype=np.float64).reshape(-1,3)
        primitives.append(PointSet3D(
            owner_layer=prepared.request.name, primitive_id="density-samples", positions=samples,
            scientific_refs=(prepared.scientific_identity,),
            render_attributes={"name": f"{field.label} samples", "size": opts.sample_size, "color": color, "opacity": opts.sample_opacity, "showlegend": False},
        ))
    return tuple(primitives)

def _legacy_scene_key(context: GraphicsSceneContext) -> GraphicsDependencyKey:
    return GraphicsDependencyKey(
        LEGACY_SCENE_PROVIDER,
        {"source_identity": context.source_identity or "in-memory-framework-dynamics-scene"},
    )


def _dependency_key(context: GraphicsSceneContext, product_provider: str) -> GraphicsDependencyKey:
    from mdstats.plotting.framework_dynamics import FrameworkDynamicsScene

    if isinstance(context.source, FrameworkDynamicsScene):
        return _legacy_scene_key(context)
    return source_dependency_key(context, product_provider)


def resolve_builtin_dependency(key: GraphicsDependencyKey, context: GraphicsSceneContext) -> Any:
    """Resolve one built-in dependency through legacy or GFX3D-4 authority."""

    if key.provider_type == LEGACY_SCENE_PROVIDER:
        from mdstats.plotting.framework_dynamics import FrameworkDynamicsScene

        source = context.source
        if not isinstance(source, FrameworkDynamicsScene):
            raise Graphics3DDependencyError(
                "Legacy framework_dynamics_scene dependency requires context.source to be "
                "a prepared FrameworkDynamicsScene."
            )
        return source
    return resolve_source_dependency(key, context)


def _resolved_product(
    resolved_dependencies: dict[str, Any],
    *,
    product_provider: str,
) -> tuple[Any, Any]:
    """Return ``(scientific value, renderer-neutral source authority)``.

    Raw-source GFX3D products return their :class:`GraphicsScientificProduct`
    authority.  Historical in-memory ``FrameworkDynamicsScene`` input remains
    supported as a compatibility source, but no raw-source product embeds that
    composite scene.
    """

    if product_provider in resolved_dependencies:
        product = resolved_dependencies[product_provider]
        if not isinstance(product, GraphicsScientificProduct):
            raise Graphics3DDependencyError(
                f"Dependency {product_provider!r} is not GraphicsScientificProduct."
            )
        return product.value, product
    scene = _scene_from_dependencies(resolved_dependencies)
    if product_provider == FRAMEWORK_PRODUCT_PROVIDER:
        return scene.mean_framework, scene
    if product_provider == CONNECTIVITY_PRODUCT_PROVIDER:
        return scene.atomic_mean_graph, scene
    if product_provider == TRAJECTORY_PRODUCT_PROVIDER:
        return scene.trajectory_paths, scene
    if product_provider == DENSITY_PRODUCT_PROVIDER:
        return scene, scene
    raise Graphics3DDependencyError(f"Unknown built-in product {product_provider!r}.")


def _source_metadata(authority: Any) -> dict[str, Any]:
    if isinstance(authority, GraphicsScientificProduct):
        return dict(authority.provenance)
    return dict(getattr(authority, "metadata", {}))



def _validate_prepared_analysis_options(
    request: GraphicsLayer3DRequest, *, allowed: frozenset[str] = frozenset()
) -> None:
    unknown = set(request.analysis_options) - set(allowed)
    if unknown:
        raise Graphics3DValidationError(
            f"GFX3D-2 layer {request.name!r} cannot apply scientific analysis options "
            f"to an already-prepared product: {', '.join(sorted(unknown))}. "
            "Raw scientific preparation is deferred to the owning provider/GFX3D-4."
        )

def _scene_from_dependencies(resolved_dependencies: dict[str, Any]) -> Any:
    try:
        return resolved_dependencies[LEGACY_SCENE_PROVIDER]
    except KeyError as error:
        raise Graphics3DDependencyError(
            f"Missing required {LEGACY_SCENE_PROVIDER!r} dependency."
        ) from error


def _selection_mask(
    atom_indices: tuple[int, ...], atomic_numbers_array: np.ndarray, selection: GraphicsSelection
) -> np.ndarray:
    mask = np.ones(len(atom_indices), dtype=bool)
    any_node_selector = False
    if selection.atom_indices:
        any_node_selector = True
        allowed = set(int(v) for v in selection.atom_indices)
        mask &= np.asarray([int(v) in allowed for v in atom_indices], dtype=bool)
    if selection.species:
        any_node_selector = True
        allowed_numbers = {int(atomic_numbers[s]) for s in selection.species}
        mask &= np.asarray([int(v) in allowed_numbers for v in atomic_numbers_array], dtype=bool)
    if not any_node_selector:
        mask[:] = True
    return mask


def _filter_trajectory(paths: Any, selection: GraphicsSelection) -> Any:
    if not selection.atom_indices and not selection.species:
        return paths
    from mdstats.plotting.framework_dynamics import TrajectoryPathSet

    mask = _selection_mask(paths.atom_indices, np.asarray(paths.atomic_numbers), selection)
    selected = np.flatnonzero(mask)
    if selected.size == 0:
        raise Graphics3DValidationError("Trajectory layer selection resolved to no prepared atoms.")
    return TrajectoryPathSet(
        atom_indices=tuple(int(paths.atom_indices[i]) for i in selected),
        atomic_numbers=np.asarray(paths.atomic_numbers)[selected],
        frame_indices=paths.frame_indices,
        frame_ids=paths.frame_ids,
        times=paths.times,
        continuous_positions=np.asarray(paths.continuous_positions)[selected],
        display_positions=np.asarray(paths.display_positions)[selected],
        lattice_images=np.asarray(paths.lattice_images)[selected],
        segment_breaks=np.asarray(paths.segment_breaks)[selected],
        display_mode=paths.display_mode,
        selection_label=selection.species and "/".join(selection.species) or paths.selection_label,
    )


def _filter_connectivity(graph: Any, selection: GraphicsSelection) -> Any:
    if not selection.active_fields():
        return graph
    unsupported = selection.active_fields() - {"species", "atom_indices", "pairs"}
    if unsupported:
        raise Graphics3DValidationError(
            "Atomic connectivity GFX3D-2 adapter cannot apply selection fields: "
            + ", ".join(sorted(unsupported))
        )
    from mdstats.plotting.framework_dynamics import AtomicMeanGraph

    atoms = tuple(int(v) for v in graph.atom_indices)
    numbers = np.asarray(graph.atomic_numbers, dtype=np.int64)
    node_mask = _selection_mask(atoms, numbers, selection)
    endpoints = np.asarray(graph.edge_endpoints, dtype=np.int64)
    edge_mask = np.ones(endpoints.shape[0], dtype=bool)
    if selection.pairs:
        allowed_pairs = {
            tuple(sorted((int(atomic_numbers[a]), int(atomic_numbers[b]))))
            for a, b in selection.pairs
        }
        pair_values = [
            tuple(sorted((int(numbers[i]), int(numbers[j])))) for i, j in endpoints
        ]
        edge_mask &= np.asarray([pair in allowed_pairs for pair in pair_values], dtype=bool)
        if not selection.atom_indices and not selection.species:
            node_mask[:] = False
            if np.any(edge_mask):
                node_mask[np.unique(endpoints[edge_mask])] = True
    edge_mask &= node_mask[endpoints[:, 0]] & node_mask[endpoints[:, 1]]
    selected_nodes = np.flatnonzero(node_mask)
    if selected_nodes.size == 0:
        raise Graphics3DValidationError("Connectivity layer selection resolved to no prepared atoms.")
    old_to_new = np.full(len(atoms), -1, dtype=np.int64)
    old_to_new[selected_nodes] = np.arange(selected_nodes.size, dtype=np.int64)
    selected_edges = endpoints[edge_mask]
    if selected_edges.size:
        selected_edges = old_to_new[selected_edges]
    else:
        selected_edges = np.empty((0, 2), dtype=np.int64)
    return AtomicMeanGraph(
        atom_indices=tuple(atoms[i] for i in selected_nodes),
        atomic_numbers=numbers[selected_nodes],
        display_positions=np.asarray(graph.display_positions)[selected_nodes],
        edge_endpoints=selected_edges,
        edge_image_shifts=np.asarray(graph.edge_image_shifts)[edge_mask],
        edge_occupancies=np.asarray(graph.edge_occupancies)[edge_mask],
        display_cell=graph.display_cell,
        pbc=graph.pbc,
        mode=graph.mode,
        metadata={**dict(graph.metadata), "gfx3d_selection_filtered": True},
    )


def _density_candidates(source: Any) -> list[tuple[Any, str]]:
    if isinstance(source, GraphicsDensityProduct):
        atomic_fields = source.atomic_density_fields
        framework_fields = source.framework_density_fields
    else:
        atomic_fields = source.atomic_density_fields
        framework_fields = source.framework_density_fields
    candidates: list[tuple[Any, str]] = [(field, "atomic") for field in atomic_fields]
    if framework_fields is not None:
        for field in framework_fields.fields:
            candidates.append((field, str(field.source_provenance.source_kind)))
    return candidates


def _select_density(source: Any, request: GraphicsLayer3DRequest) -> tuple[Any, str]:
    candidates = _density_candidates(source)
    if not candidates:
        raise Graphics3DValidationError("Density layer requested but the prepared source has no density fields.")
    field_key = request.analysis_options.get("field_key") or request.metadata.get("field_key")
    source_kind = request.analysis_options.get("source_kind") or request.metadata.get("source_kind")
    if field_key is not None:
        candidates = [(f, k) for f, k in candidates if str(f.field_key) == str(field_key)]
    if source_kind is not None:
        candidates = [
            (f, k)
            for f, k in candidates
            if str(k) == str(source_kind) or str(f.source_provenance.source_kind) == str(source_kind)
        ]
    selection = request.selection
    if selection.atom_indices:
        wanted = tuple(sorted(int(v) for v in selection.atom_indices))
        candidates = [
            (f, k)
            for f, k in candidates
            if tuple(sorted(int(v) for v in f.source_provenance.atom_indices)) == wanted
        ]
    if selection.species:
        # Existing density provenance is atom-index authoritative. Recover species
        # only from already-prepared scene products; never guess from a field name.
        wanted_numbers = {int(atomic_numbers[s]) for s in selection.species}
        if isinstance(source, GraphicsDensityProduct):
            number_by_atom = {int(i): int(z) for i, z in source.atomic_number_by_atom.items()}
        else:
            number_by_atom: dict[int, int] = {
                int(i): int(z)
                for i, z in dict(source.metadata.get("gfx3d_atomic_number_by_atom", {})).items()
            }
            if source.atomic_mean_graph is not None:
                number_by_atom.update(
                    {int(i): int(z) for i, z in zip(source.atomic_mean_graph.atom_indices, source.atomic_mean_graph.atomic_numbers)}
                )
            if source.trajectory_paths is not None:
                number_by_atom.update(
                    {int(i): int(z) for i, z in zip(source.trajectory_paths.atom_indices, source.trajectory_paths.atomic_numbers)}
                )
        proven: list[tuple[Any, str]] = []
        for field, kind in candidates:
            atoms = tuple(int(v) for v in field.source_provenance.atom_indices)
            if atoms and all(index in number_by_atom for index in atoms):
                field_numbers = {number_by_atom[index] for index in atoms}
                if field_numbers == wanted_numbers:
                    proven.append((field, kind))
                    continue
            metadata = dict(field.source_provenance.metadata)
            labels = metadata.get("species") or metadata.get("species_symbols")
            if isinstance(labels, str):
                labels = [labels]
            if labels is not None and {int(atomic_numbers[str(v)]) for v in labels} == wanted_numbers:
                proven.append((field, kind))
        candidates = proven
    if len(candidates) != 1:
        keys = tuple(str(f.field_key) for f, _ in candidates)
        if not candidates:
            raise Graphics3DValidationError(
                f"Density layer {request.name!r} did not match any prepared density field."
            )
        raise Graphics3DValidationError(
            f"Density layer {request.name!r} is ambiguous across prepared fields {keys}; "
            "specify analysis_options.field_key/source_kind or an exact atom-index selection."
        )
    return candidates[0]


@dataclass(frozen=True, slots=True)
class FrameworkTopologyLayer:
    """Independent framework-topology layer adapter."""

    def dependencies(self, request: GraphicsLayer3DRequest, context: GraphicsSceneContext):
        return (GraphicsDependencyRequest(_dependency_key(context, FRAMEWORK_PRODUCT_PROVIDER)),)

    def prepare(self, request, resolved_dependencies, context):
        _validate_prepared_analysis_options(request)
        mean_framework, authority = _resolved_product(resolved_dependencies, product_provider=FRAMEWORK_PRODUCT_PROVIDER)
        source_metadata = _source_metadata(authority)
        identity = identity_digest(
            GFX3D2_LAYER_SCHEMA + ".framework",
            {"request": request.scientific_identity, "source": source_metadata.get("source_framework_topology_digest")},
        )
        return PreparedGraphicsLayer3D(
            request=request,
            scientific_identity=identity,
            product_refs={"mean_framework": mean_framework},
            provenance={"adapter_schema": GFX3D2_LAYER_SCHEMA, "source_scene_schema": source_metadata.get("source_scene_schema", source_metadata.get("schema_version"))},
        )

    def render_primitives(self, prepared, context):
        return _framework_render_primitives(prepared)


@dataclass(frozen=True, slots=True)
class AtomicConnectivityLayer:
    """Independent averaged atomic-connectivity layer adapter."""

    def dependencies(self, request: GraphicsLayer3DRequest, context: GraphicsSceneContext):
        return (GraphicsDependencyRequest(_dependency_key(context, CONNECTIVITY_PRODUCT_PROVIDER)),)

    def prepare(self, request, resolved_dependencies, context):
        _validate_prepared_analysis_options(request)
        source_graph, _authority = _resolved_product(resolved_dependencies, product_provider=CONNECTIVITY_PRODUCT_PROVIDER)
        if source_graph is None:
            raise Graphics3DValidationError(
                "Atomic connectivity layer requested but the prepared source scene has no atomic_mean_graph."
            )
        graph = _filter_connectivity(source_graph, request.selection)
        identity = identity_digest(
            GFX3D2_LAYER_SCHEMA + ".connectivity",
            {"request": request.scientific_identity, "source_mode": graph.mode, "atoms": graph.atom_indices},
        )
        return PreparedGraphicsLayer3D(
            request=request,
            scientific_identity=identity,
            product_refs={"atomic_mean_graph": graph},
            provenance={"adapter_schema": GFX3D2_LAYER_SCHEMA},
        )

    def render_primitives(self, prepared, context):
        return _connectivity_render_primitives(prepared)


@dataclass(frozen=True, slots=True)
class AtomicTrajectoryLayer:
    """Independent prepared atomic-trajectory layer adapter."""

    def dependencies(self, request: GraphicsLayer3DRequest, context: GraphicsSceneContext):
        return (GraphicsDependencyRequest(_dependency_key(context, TRAJECTORY_PRODUCT_PROVIDER)),)

    def prepare(self, request, resolved_dependencies, context):
        _validate_prepared_analysis_options(request)
        source_paths, _authority = _resolved_product(resolved_dependencies, product_provider=TRAJECTORY_PRODUCT_PROVIDER)
        if source_paths is None:
            raise Graphics3DValidationError(
                "Atomic trajectory layer requested but the prepared source scene has no trajectory_paths."
            )
        paths = _filter_trajectory(source_paths, request.selection)
        identity = identity_digest(
            GFX3D2_LAYER_SCHEMA + ".trajectory",
            {"request": request.scientific_identity, "atoms": paths.atom_indices, "mode": str(paths.display_mode)},
        )
        return PreparedGraphicsLayer3D(
            request=request,
            scientific_identity=identity,
            product_refs={"trajectory_paths": paths},
            provenance={"adapter_schema": GFX3D2_LAYER_SCHEMA},
        )

    def render_primitives(self, prepared, context):
        return _trajectory_render_primitives(prepared)


@dataclass(frozen=True, slots=True)
class AtomicDensityLayer:
    """Independent current atomic/framework density field layer adapter.

    The public layer type remains ``density``. ``source_kind`` in analysis
    options identifies framework density channels when needed.
    """

    def dependencies(self, request: GraphicsLayer3DRequest, context: GraphicsSceneContext):
        return (GraphicsDependencyRequest(_dependency_key(context, DENSITY_PRODUCT_PROVIDER)),)

    def prepare(self, request, resolved_dependencies, context):
        _validate_prepared_analysis_options(request, allowed=frozenset({"field_key", "source_kind"}))
        density_source, _authority = _resolved_product(resolved_dependencies, product_provider=DENSITY_PRODUCT_PROVIDER)
        field, source_kind = _select_density(density_source, request)
        identity = identity_digest(
            GFX3D2_LAYER_SCHEMA + ".density",
            {
                "request": request.scientific_identity,
                "field_key": field.field_key,
                "source_kind": field.source_provenance.source_kind,
                "field_schema": field.schema_version,
            },
        )
        return PreparedGraphicsLayer3D(
            request=request,
            scientific_identity=identity,
            product_refs={"density_field": field, "density_source_kind": source_kind},
            provenance={"adapter_schema": GFX3D2_LAYER_SCHEMA, "field_key": str(field.field_key), "source_kind": source_kind},
        )

    def render_primitives(self, prepared, context):
        return _density_render_primitives(prepared, context)


def register_builtin_graphics3d_layers(registry: GraphicsLayerRegistry) -> None:
    """Register the four GFX3D-2 built-in layer families exactly once."""

    registrations = (
        GraphicsLayerRegistration(
            layer_type="framework",
            schema_version=GFX3D4_LAYER_SCHEMA + ".framework",
            adapter_factory=FrameworkTopologyLayer,
            supported_selection_fields=frozenset(),
            required_dependency_providers=(FRAMEWORK_PRODUCT_PROVIDER,),
        ),
        GraphicsLayerRegistration(
            layer_type="connectivity",
            schema_version=GFX3D4_LAYER_SCHEMA + ".connectivity",
            adapter_factory=AtomicConnectivityLayer,
            supported_selection_fields=frozenset({"species", "atom_indices", "pairs"}),
            required_dependency_providers=(CONNECTIVITY_PRODUCT_PROVIDER,),
        ),
        GraphicsLayerRegistration(
            layer_type="trajectory",
            schema_version=GFX3D4_LAYER_SCHEMA + ".trajectory",
            adapter_factory=AtomicTrajectoryLayer,
            supported_selection_fields=frozenset({"species", "atom_indices"}),
            required_dependency_providers=(TRAJECTORY_PRODUCT_PROVIDER,),
        ),
        GraphicsLayerRegistration(
            layer_type="density",
            schema_version=GFX3D4_LAYER_SCHEMA + ".density",
            adapter_factory=AtomicDensityLayer,
            supported_selection_fields=frozenset({"species", "atom_indices"}),
            required_dependency_providers=(DENSITY_PRODUCT_PROVIDER,),
        ),
    )
    for registration in registrations:
        if registration.layer_type not in registry:
            registry.register(registration)
