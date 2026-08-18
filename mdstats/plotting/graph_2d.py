"""Static two-dimensional rendering for immutable decorated graph views."""

from __future__ import annotations

import warnings as pywarnings
from dataclasses import dataclass
from types import MappingProxyType
from collections.abc import Mapping
from typing import Any, Literal

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.artist import Artist
from matplotlib.axes import Axes
from matplotlib.collections import LineCollection
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.colors import to_rgba
from numpy.typing import NDArray

from .graph_errors import (
    GraphComplexityError,
    GraphLayoutError,
    GraphOptionalDependencyError,
    GraphUnsupportedFeatureError,
)
from .graph_styles import (
    EdgeStyle,
    GraphStyle,
    NodeDisplayMode,
    NodeStyle,
    _node_styles_for_display,
    resolve_edge_styles,
    resolve_node_styles,
)
from .periodic_graph import (
    PeriodicDisplayOptions,
    _deterministic_image_assignment,
    _residual_edge_shifts,
    prepare_periodic_graph_view,
)
from .graph_view import (
    DecoratedGraphView,
    GraphComplexityPolicy,
    GraphComplexityReport,
    GraphFilter,
    GraphFocus,
    GraphKey,
    PreparedGraphView,
    _column_value,
    prepare_graph_view,
)

FloatArray = NDArray[np.float64]


@dataclass(frozen=True, slots=True)
class GraphLayoutOptions:
    """Layout and projection options independent of rendering style."""

    method: Literal["auto", "physical", "spring", "circular", "shell"] = "auto"
    projection: Literal["xy", "xz", "yz", "pca"] | NDArray[np.float64] = "pca"
    center_physical: bool = True
    seed: int = 0
    spring_iterations: int = 100
    spring_k: float | None = None

    def __post_init__(self) -> None:
        if self.method not in {"auto", "physical", "spring", "circular", "shell"}:
            raise GraphLayoutError("Unknown graph layout method.")
        projection = self.projection
        if isinstance(projection, str):
            if projection not in {"xy", "xz", "yz", "pca"}:
                raise GraphLayoutError("Unknown physical projection.")
        else:
            matrix = np.array(projection, dtype=float, copy=True, order="C")
            if matrix.shape != (2, 3) or np.any(~np.isfinite(matrix)):
                raise GraphLayoutError(
                    "A custom projection matrix must be finite with shape (2, 3)."
                )
            if np.linalg.matrix_rank(matrix) != 2 or np.any(
                np.linalg.norm(matrix, axis=1) <= 0.0
            ):
                raise GraphLayoutError("A custom projection matrix must have rank 2.")
            matrix.setflags(write=False)
            object.__setattr__(self, "projection", matrix)
        if isinstance(self.seed, bool) or not isinstance(self.seed, (int, np.integer)):
            raise GraphLayoutError("seed must be an integer.")
        object.__setattr__(self, "seed", int(self.seed))
        if isinstance(self.spring_iterations, bool) or not isinstance(
            self.spring_iterations, (int, np.integer)
        ):
            raise GraphLayoutError("spring_iterations must be a positive integer.")
        iterations = int(self.spring_iterations)
        if iterations <= 0:
            raise GraphLayoutError("spring_iterations must be positive.")
        object.__setattr__(self, "spring_iterations", iterations)
        if self.spring_k is not None:
            value = float(self.spring_k)
            if not np.isfinite(value) or value <= 0.0:
                raise GraphLayoutError("spring_k must be positive and finite.")
            object.__setattr__(self, "spring_k", value)
        object.__setattr__(self, "center_physical", bool(self.center_physical))


@dataclass(frozen=True, slots=True)
class Graph2DRenderOptions:
    """Matplotlib-specific static rendering options."""

    figsize: tuple[float, float] | None = None
    dpi: int = 150
    show_axes: bool | None = None
    equal_aspect: bool = True
    margin_fraction: float = 0.06
    title: str | None = None
    tight_layout: bool = True
    periodic_edge_mode: Literal["translated_segment", "canonical_quotient"] = (
        "translated_segment"
    )
    periodic_node_mode: Literal["canonical", "local_unwrapped"] = "canonical"
    show_periodic_ghosts: bool = True
    allow_parallel_overlap: bool = False

    def __post_init__(self) -> None:
        if self.figsize is not None:
            if len(self.figsize) != 2 or any(
                not np.isfinite(float(x)) or float(x) <= 0.0 for x in self.figsize
            ):
                raise GraphLayoutError(
                    "figsize must contain two positive finite values."
                )
            object.__setattr__(self, "figsize", tuple(float(x) for x in self.figsize))
        if isinstance(self.dpi, bool) or not isinstance(self.dpi, (int, np.integer)):
            raise GraphLayoutError("dpi must be a positive integer.")
        dpi = int(self.dpi)
        if dpi <= 0:
            raise GraphLayoutError("dpi must be positive.")
        object.__setattr__(self, "dpi", dpi)
        margin = float(self.margin_fraction)
        if not np.isfinite(margin) or margin < 0.0:
            raise GraphLayoutError("margin_fraction must be finite and nonnegative.")
        object.__setattr__(self, "margin_fraction", margin)
        if self.periodic_edge_mode not in {"translated_segment", "canonical_quotient"}:
            raise GraphLayoutError("Unknown periodic edge mode.")
        if self.periodic_node_mode not in {"canonical", "local_unwrapped"}:
            raise GraphLayoutError("Unknown periodic node mode.")
        object.__setattr__(self, "equal_aspect", bool(self.equal_aspect))
        object.__setattr__(
            self, "show_periodic_ghosts", bool(self.show_periodic_ghosts)
        )
        object.__setattr__(self, "tight_layout", bool(self.tight_layout))
        object.__setattr__(
            self, "allow_parallel_overlap", bool(self.allow_parallel_overlap)
        )


@dataclass(slots=True)
class GraphRenderResult:
    """Matplotlib render output plus traceable scientific-key mappings."""

    figure: Figure
    axes: Axes
    rendered_node_keys: tuple[GraphKey, ...]
    rendered_edge_keys: tuple[GraphKey, ...]
    node_positions_2d: FloatArray
    edge_paths_2d: tuple[FloatArray, ...]
    artist_groups: Mapping[str, tuple[Artist, ...]]
    layout_metadata: Mapping[str, Any]
    style_metadata: Mapping[str, Any]
    selection_metadata: Mapping[str, Any]
    periodic_metadata: Mapping[str, Any]
    complexity: GraphComplexityReport
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        positions = np.array(self.node_positions_2d, dtype=float, copy=True, order="C")
        positions.setflags(write=False)
        paths: list[FloatArray] = []
        for path in self.edge_paths_2d:
            array = np.array(path, dtype=float, copy=True, order="C")
            array.setflags(write=False)
            paths.append(array)
        self.node_positions_2d = positions
        self.edge_paths_2d = tuple(paths)
        self.artist_groups = MappingProxyType(
            {name: tuple(group) for name, group in self.artist_groups.items()}
        )
        self.layout_metadata = MappingProxyType(dict(self.layout_metadata))
        self.style_metadata = MappingProxyType(dict(self.style_metadata))
        self.selection_metadata = MappingProxyType(dict(self.selection_metadata))
        self.periodic_metadata = MappingProxyType(dict(self.periodic_metadata))
        self.warnings = tuple(self.warnings)


def _resolved_layout_method(
    prepared: PreparedGraphView, options: GraphLayoutOptions
) -> Literal["physical", "spring", "circular", "shell"]:
    """Resolve ``auto`` without computing coordinates."""
    if options.method == "auto":
        return "physical" if prepared.node_positions_3d is not None else "spring"
    return options.method


def _periodic_display_geometry(
    prepared: PreparedGraphView,
    options: Graph2DRenderOptions,
    warning_messages: list[str],
    *,
    layout_method: Literal["physical", "spring", "circular", "shell"],
) -> tuple[FloatArray | None, NDArray[np.int64] | None, dict[str, Any]]:
    """Return optional locally unwrapped node positions and residual edge shifts.

    A deterministic spanning forest places neighboring nodes in continuous
    lattice images.  Non-tree periodic winding remains as a residual edge
    shift and is therefore not erased by the display transformation.
    """
    if layout_method != "physical":
        if options.periodic_node_mode != "canonical":
            warning_messages.append(
                "periodic_node_mode is ignored for schematic layouts; "
                "schematic coordinates carry no physical image gauge."
            )
        return (
            prepared.node_positions_3d,
            prepared.edge_image_shifts,
            {
                "node_mode": "not_applicable_schematic",
                "requested_node_mode": options.periodic_node_mode,
                "nonzero_residual_edges": 0,
            },
        )
    if options.periodic_node_mode == "canonical":
        return (
            prepared.node_positions_3d,
            prepared.edge_image_shifts,
            {
                "node_mode": "canonical",
                "nonzero_residual_edges": (
                    0
                    if prepared.edge_image_shifts is None
                    else int(
                        np.count_nonzero(
                            np.any(prepared.edge_image_shifts != 0, axis=1)
                        )
                    )
                ),
            },
        )
    if prepared.node_positions_3d is None or prepared.source_view.cell is None:
        raise GraphLayoutError(
            "local_unwrapped periodic node mode requires physical positions and a cell."
        )
    shifts = (
        np.zeros((len(prepared.edge_keys), 3), dtype=np.int64)
        if prepared.edge_image_shifts is None
        else np.asarray(prepared.edge_image_shifts, dtype=np.int64)
    )
    n_nodes = len(prepared.node_keys)
    preferred_roots: list[int] = []
    focus_payload = prepared.selection_metadata.get("focus")
    if isinstance(focus_payload, Mapping):
        centers = focus_payload.get("center_node_keys", ())
        key_to_local = {key: i for i, key in enumerate(prepared.node_keys)}
        preferred_roots.extend(
            key_to_local[key] for key in centers if key in key_to_local
        )
    image_offsets = _deterministic_image_assignment(
        edge_endpoints=prepared.edge_endpoints,
        edge_shifts=shifts,
        n_nodes=n_nodes,
        preferred_roots=preferred_roots,
        node_order=prepared.node_source_positions,
        edge_order=prepared.edge_source_positions,
    )
    residual = _residual_edge_shifts(prepared.edge_endpoints, shifts, image_offsets)
    unwrapped = (
        np.asarray(prepared.node_positions_3d, dtype=float)
        + image_offsets @ prepared.source_view.cell
    )
    nonzero = int(np.count_nonzero(np.any(residual != 0, axis=1)))
    if nonzero:
        warning_messages.append(
            f"Local unwrapping preserved periodic winding on {nonzero} non-tree edges; "
            "those edges still use translated target segments."
        )
    return (
        unwrapped,
        residual,
        {
            "node_mode": "local_unwrapped",
            "image_offsets": image_offsets.tolist(),
            "nonzero_residual_edges": nonzero,
        },
    )


def _projection_matrix(
    prepared: PreparedGraphView,
    options: GraphLayoutOptions,
    warning_messages: list[str],
    *,
    physical_positions: FloatArray | None = None,
) -> tuple[FloatArray, str]:
    projection = options.projection
    if isinstance(projection, np.ndarray):
        return np.asarray(projection, dtype=float), "custom"
    if projection == "xy":
        return np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]), "xy"
    if projection == "xz":
        return np.asarray([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]), "xz"
    if projection == "yz":
        return np.asarray([[0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]), "yz"
    assert projection == "pca"
    positions = (
        prepared.node_positions_3d if physical_positions is None else physical_positions
    )
    assert positions is not None
    if positions.shape[0] < 2:
        return np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]]), "pca-fallback-xy"
    centered = positions - np.mean(positions, axis=0, keepdims=True)
    _, singular, vh = np.linalg.svd(centered, full_matrices=False)
    vectors = np.array(vh[:2], copy=True)
    if vectors.shape[0] < 2:
        vectors = np.asarray([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
    for row in range(2):
        pivot = int(np.argmax(np.abs(vectors[row])))
        if vectors[row, pivot] < 0.0:
            vectors[row] *= -1.0
    if singular.size >= 2:
        scale = max(float(singular[0]), 1.0)
        if abs(float(singular[0] - singular[1])) <= 1.0e-8 * scale:
            warning_messages.append(
                "The leading PCA directions are nearly degenerate; in-plane "
                "orientation is deterministic but physically arbitrary."
            )
    return vectors, "pca"


def _layout_positions(
    prepared: PreparedGraphView,
    options: GraphLayoutOptions,
    warning_messages: list[str],
    *,
    physical_positions: FloatArray | None = None,
) -> tuple[FloatArray, dict[str, Any], FloatArray | None]:
    method = options.method
    source_positions = (
        prepared.node_positions_3d if physical_positions is None else physical_positions
    )
    if method == "auto":
        method = "physical" if source_positions is not None else "spring"
    if method == "physical":
        if source_positions is None:
            raise GraphLayoutError("Physical layout requires node_positions_3d.")
        matrix, projection_name = _projection_matrix(
            prepared, options, warning_messages, physical_positions=source_positions
        )
        positions = source_positions @ matrix.T
        if options.center_physical and positions.size:
            positions = positions - np.mean(positions, axis=0, keepdims=True)
        metadata = {
            "method": "physical",
            "projection": projection_name,
            "projection_matrix": matrix.tolist(),
            "center_physical": options.center_physical,
        }
        return np.asarray(positions, dtype=float), metadata, matrix

    if prepared.node_positions_3d is not None:
        warning_messages.append(
            "A schematic layout was requested for a graph with physical coordinates."
        )
    try:
        import networkx as nx
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise GraphOptionalDependencyError(
            "NetworkX is required for schematic graph layouts."
        ) from exc
    graph = nx.DiGraph() if prepared.source_view.directed else nx.Graph()
    graph.add_nodes_from(range(len(prepared.node_source_positions)))
    graph.add_edges_from((int(i), int(j)) for i, j in prepared.edge_endpoints)
    if method == "spring":
        mapping = nx.spring_layout(
            graph,
            seed=options.seed,
            iterations=options.spring_iterations,
            k=options.spring_k,
            dim=2,
        )
    elif method == "circular":
        mapping = nx.circular_layout(graph, dim=2)
    elif method == "shell":
        mapping = nx.shell_layout(graph, dim=2)
    else:  # pragma: no cover - protected by validation
        raise GraphLayoutError(f"Unsupported layout method {method!r}.")
    positions = np.asarray(
        [mapping[i] for i in range(graph.number_of_nodes())], dtype=float
    )
    return (
        positions,
        {
            "method": method,
            "seed": options.seed if method == "spring" else None,
            "spring_iterations": options.spring_iterations
            if method == "spring"
            else None,
            "spring_k": options.spring_k if method == "spring" else None,
        },
        None,
    )


def _edge_paths(
    prepared: PreparedGraphView,
    node_positions: FloatArray,
    projection: FloatArray | None,
    layout_method: str,
    options: Graph2DRenderOptions,
    warning_messages: list[str],
    *,
    edge_image_shifts: NDArray[np.int64] | None = None,
) -> tuple[FloatArray, ...]:
    paths: list[FloatArray] = []
    shifts = (
        prepared.edge_image_shifts if edge_image_shifts is None else edge_image_shifts
    )
    periodic_count = 0
    for edge_position, (source, target) in enumerate(prepared.edge_endpoints):
        start = node_positions[int(source)]
        end = node_positions[int(target)]
        shift = np.zeros(3, dtype=np.int64) if shifts is None else shifts[edge_position]
        if np.any(shift):
            periodic_count += 1
        if (
            layout_method == "physical"
            and options.periodic_edge_mode == "translated_segment"
            and np.any(shift)
        ):
            if prepared.source_view.cell is None or projection is None:
                raise GraphLayoutError(
                    "Translated periodic edges require a cell and physical projection."
                )
            end = end + (shift @ prepared.source_view.cell) @ projection.T
        paths.append(np.asarray([start, end], dtype=float))
    if periodic_count and options.periodic_edge_mode == "canonical_quotient":
        warning_messages.append(
            "Periodic edges are drawn between canonical endpoints in quotient mode."
        )
    return tuple(paths)


def _requested_label_counts(
    style: GraphStyle, prepared: PreparedGraphView
) -> tuple[int, int]:
    labels = style.labels
    node_count = 0
    edge_count = 0
    if (
        labels.node_attribute is not None
        and style.node_display_mode is not NodeDisplayMode.HIDDEN
    ):
        if labels.node_keys is None:
            node_count = len(prepared.node_keys)
        else:
            available = set(prepared.node_keys)
            unknown = [key for key in labels.node_keys if key not in available]
            if unknown:
                raise GraphLayoutError(
                    f"Unknown requested node label keys: {unknown!r}."
                )
            node_count = len(labels.node_keys)
    if labels.edge_attribute is not None:
        if labels.edge_keys is None:
            edge_count = len(prepared.edge_keys)
        else:
            available = set(prepared.edge_keys)
            unknown = [key for key in labels.edge_keys if key not in available]
            if unknown:
                raise GraphLayoutError(
                    f"Unknown requested edge label keys: {unknown!r}."
                )
            edge_count = len(labels.edge_keys)
    return node_count, edge_count


def _complexity_report(
    view: DecoratedGraphView,
    prepared: PreparedGraphView,
    style: GraphStyle,
    edge_styles: tuple[EdgeStyle, ...],
    policy: GraphComplexityPolicy,
) -> GraphComplexityReport:
    node_labels, edge_labels = _requested_label_counts(style, prepared)
    gradient = sum(
        edge.gradient_segments
        if edge.color_mode == "segmented_gradient"
        else 2
        if edge.color_mode == "midpoint_split"
        else 1
        for edge in edge_styles
    )
    exceeded: list[str] = []
    if len(prepared.node_keys) > policy.max_nodes:
        exceeded.append("nodes")
    if len(prepared.edge_keys) > policy.max_edges:
        exceeded.append("edges")
    if node_labels + edge_labels > policy.max_labels:
        exceeded.append("labels")
    if gradient > policy.max_gradient_segments:
        exceeded.append("gradient_segments")
    return GraphComplexityReport(
        input_nodes=view.n_nodes,
        input_edges=view.n_edges,
        selected_nodes=len(prepared.node_keys),
        selected_edges=len(prepared.edge_keys),
        requested_labels=node_labels + edge_labels,
        estimated_gradient_segments=gradient,
        exceeded_limits=tuple(exceeded),
    )


def _enforce_complexity(
    report: GraphComplexityReport,
    policy: GraphComplexityPolicy,
    warning_messages: list[str],
) -> None:
    if not report.exceeded_limits:
        return
    message = (
        "Graph rendering exceeds limits for "
        + ", ".join(report.exceeded_limits)
        + f" (selected {report.selected_nodes} nodes, {report.selected_edges} edges, "
        + f"{report.requested_labels} labels, "
        + f"{report.estimated_gradient_segments} edge segments)."
    )
    if policy.overflow == "warn_and_render":
        warning_messages.append(message)
        pywarnings.warn(message, RuntimeWarning, stacklevel=3)
        return
    if policy.overflow == "require_focus":
        message += " Apply GraphFocus or GraphFilter, or raise the explicit limits."
    raise GraphComplexityError(message)


def _check_renderer_graph_features(
    prepared: PreparedGraphView,
    options: Graph2DRenderOptions,
    warning_messages: list[str],
) -> None:
    endpoint_pairs: dict[tuple[int, int], int] = {}
    for source, target in prepared.edge_endpoints:
        s, t = int(source), int(target)
        if s == t:
            raise GraphUnsupportedFeatureError(
                "Self-loops are not supported by the first 2-D renderer."
            )
        pair = (s, t) if prepared.source_view.directed else tuple(sorted((s, t)))
        endpoint_pairs[pair] = endpoint_pairs.get(pair, 0) + 1
    has_parallel = any(count > 1 for count in endpoint_pairs.values())
    if has_parallel and not options.allow_parallel_overlap:
        raise GraphUnsupportedFeatureError(
            "Parallel edges require allow_parallel_overlap=True in the first renderer."
        )
    if has_parallel:
        warning_messages.append(
            "Parallel edges are rendered directly on top of one another."
        )


def _style_key_node(style: NodeStyle) -> tuple[Any, ...]:
    return (
        style.face_color,
        style.size,
        style.marker,
        style.alpha,
        style.edge_color,
        style.edge_width,
        style.zorder,
    )


def _style_key_edge(style: EdgeStyle) -> tuple[Any, ...]:
    return (
        style.color,
        style.width,
        style.alpha,
        style.line_style,
        style.color_mode,
        style.gradient_segments,
        style.zorder,
    )


def _rgba_interpolate(
    color_a: Any, color_b: Any, t: float
) -> tuple[float, float, float, float]:
    a = np.asarray(to_rgba(color_a), dtype=float)
    b = np.asarray(to_rgba(color_b), dtype=float)
    return tuple((1.0 - t) * a + t * b)


def _render_edges(
    ax: Axes,
    paths: tuple[FloatArray, ...],
    endpoints: NDArray[np.int64],
    edge_styles: tuple[EdgeStyle, ...],
    node_styles: tuple[NodeStyle, ...],
) -> tuple[Artist, ...]:
    artists: list[Artist] = []
    grouped: dict[tuple[Any, ...], list[int]] = {}
    for index, edge_style in enumerate(edge_styles):
        grouped.setdefault(_style_key_edge(edge_style), []).append(index)
    for indices in grouped.values():
        style = edge_styles[indices[0]]
        segments: list[FloatArray] = []
        colors: list[Any] = []
        for edge_index in indices:
            path = paths[edge_index]
            source, target = endpoints[edge_index]
            source_color = node_styles[int(source)].face_color
            target_color = node_styles[int(target)].face_color
            if style.color_mode == "constant":
                segments.append(path)
                colors.append(style.color)
            elif style.color_mode == "source":
                segments.append(path)
                colors.append(source_color)
            elif style.color_mode == "target":
                segments.append(path)
                colors.append(target_color)
            elif style.color_mode == "midpoint_split":
                midpoint = 0.5 * (path[0] + path[-1])
                segments.extend(
                    (np.asarray([path[0], midpoint]), np.asarray([midpoint, path[-1]]))
                )
                colors.extend((source_color, target_color))
            else:
                points = np.linspace(path[0], path[-1], style.gradient_segments + 1)
                for segment in range(style.gradient_segments):
                    segments.append(points[segment : segment + 2])
                    colors.append(
                        _rgba_interpolate(
                            source_color,
                            target_color,
                            (segment + 0.5) / style.gradient_segments,
                        )
                    )
        collection = LineCollection(
            segments,
            colors=colors,
            linewidths=style.width,
            linestyles=style.line_style,
            alpha=style.alpha,
            zorder=style.zorder,
        )
        ax.add_collection(collection)
        artists.append(collection)
    return tuple(artists)


def _render_periodic_ghost_nodes(
    ax: Axes,
    prepared: PreparedGraphView,
    paths: tuple[FloatArray, ...],
    display_shifts: NDArray[np.int64] | None,
    node_styles: tuple[NodeStyle, ...],
    *,
    enabled: bool,
    layout_method: str,
    periodic_edge_mode: str,
) -> tuple[Artist, ...]:
    """Draw faded translated endpoint copies for nonzero periodic edge shifts."""
    if (
        not enabled
        or layout_method != "physical"
        or periodic_edge_mode != "translated_segment"
        or display_shifts is None
    ):
        return ()
    records: dict[tuple[int, int, int, int], tuple[np.ndarray, NodeStyle]] = {}
    for edge_index, shift in enumerate(display_shifts):
        if not np.any(shift):
            continue
        target = int(prepared.edge_endpoints[edge_index, 1])
        key = (target, int(shift[0]), int(shift[1]), int(shift[2]))
        records[key] = (paths[edge_index][-1], node_styles[target])
    grouped: dict[tuple[Any, ...], list[np.ndarray]] = {}
    for position, style in records.values():
        ghost_style = (
            style.face_color,
            max(8.0, 0.62 * style.size),
            style.marker,
            min(0.35, 0.35 * style.alpha),
            style.edge_color,
            max(0.2, 0.6 * style.edge_width),
            style.zorder - 0.2,
        )
        grouped.setdefault(ghost_style, []).append(position)
    artists: list[Artist] = []
    for ghost_style, positions in grouped.items():
        face_color, size, marker, alpha, edge_color, edge_width, zorder = ghost_style
        coords = np.asarray(positions, dtype=float)
        artist = ax.scatter(
            coords[:, 0],
            coords[:, 1],
            s=size,
            marker=marker,
            c=[face_color],
            alpha=alpha,
            edgecolors=edge_color,
            linewidths=edge_width,
            zorder=zorder,
        )
        artists.append(artist)
    return tuple(artists)


def _render_nodes(
    ax: Axes,
    positions: FloatArray,
    node_styles: tuple[NodeStyle, ...],
) -> tuple[Artist, ...]:
    artists: list[Artist] = []
    grouped: dict[tuple[Any, ...], list[int]] = {}
    for index, node_style in enumerate(node_styles):
        grouped.setdefault(_style_key_node(node_style), []).append(index)
    for indices in grouped.values():
        style = node_styles[indices[0]]
        coords = positions[np.asarray(indices, dtype=np.int64)]
        artist = ax.scatter(
            coords[:, 0],
            coords[:, 1],
            s=style.size,
            marker=style.marker,
            c=[style.face_color],
            alpha=style.alpha,
            edgecolors=style.edge_color,
            linewidths=style.edge_width,
            zorder=style.zorder,
        )
        artists.append(artist)
    return tuple(artists)


def _render_labels(
    ax: Axes,
    prepared: PreparedGraphView,
    positions: FloatArray,
    paths: tuple[FloatArray, ...],
    style: GraphStyle,
) -> tuple[Artist, ...]:
    labels = style.labels
    artists: list[Artist] = []
    if (
        labels.node_attribute is not None
        and style.node_display_mode is not NodeDisplayMode.HIDDEN
    ):
        selected = (
            set(prepared.node_keys)
            if labels.node_keys is None
            else set(labels.node_keys)
        )
        column = prepared.node_attributes[labels.node_attribute]
        for index, key in enumerate(prepared.node_keys):
            if key not in selected:
                continue
            artist = ax.annotate(
                str(_column_value(column, index)),
                xy=positions[index],
                xytext=labels.node_offset_points,
                textcoords="offset points",
                fontsize=labels.font_size,
                zorder=10,
            )
            artists.append(artist)
    if labels.edge_attribute is not None:
        selected = (
            set(prepared.edge_keys)
            if labels.edge_keys is None
            else set(labels.edge_keys)
        )
        column = prepared.edge_attributes[labels.edge_attribute]
        for index, key in enumerate(prepared.edge_keys):
            if key not in selected:
                continue
            midpoint = np.mean(paths[index], axis=0)
            artist = ax.text(
                midpoint[0],
                midpoint[1],
                str(_column_value(column, index)),
                fontsize=labels.font_size,
                ha="center",
                va="center",
                zorder=10,
            )
            artists.append(artist)
    return tuple(artists)


def _add_legend(
    ax: Axes, prepared: PreparedGraphView, style: GraphStyle
) -> tuple[Artist, ...]:
    if style.legend == "none":
        return ()
    handles: list[Artist] = []
    labels: list[str] = []
    node_attrs = prepared.node_attributes
    edge_attrs = prepared.edge_attributes
    if style.node_display_mode is not NodeDisplayMode.HIDDEN and "symbol" in node_attrs:
        symbols = sorted(
            {
                str(_column_value(node_attrs["symbol"], i))
                for i in range(len(prepared.node_keys))
            }
        )
        for symbol in symbols:
            handles.append(
                Line2D(
                    [0],
                    [0],
                    marker="o",
                    linestyle="none",
                    markerfacecolor=style.palette.color_for(symbol),
                    markeredgecolor=(
                        style.palette.color_for(symbol)
                        if style.node_display_mode is NodeDisplayMode.DOTS
                        else "#202020"
                    ),
                    markeredgewidth=(
                        0.0 if style.node_display_mode is NodeDisplayMode.DOTS else 1.0
                    ),
                    markersize=(
                        max(2.0, np.sqrt(style.node_dot_size))
                        if style.node_display_mode is NodeDisplayMode.DOTS
                        else 6
                    ),
                )
            )
            labels.append(symbol)
    if "transition_status" in edge_attrs:
        status_styles = {
            "unchanged": ("#B5B5B5", "solid"),
            "removed": ("#D62728", "dashed"),
            "added": ("#2CA02C", "solid"),
        }
        present = {
            str(_column_value(edge_attrs["transition_status"], i))
            for i in range(len(prepared.edge_keys))
        }
        include_transition_legend = bool({"removed", "added"} & present)
        for status in ("unchanged", "removed", "added"):
            if include_transition_legend and status in present:
                color, linestyle = status_styles[status]
                handles.append(
                    Line2D([0], [0], color=color, linestyle=linestyle, linewidth=2.0)
                )
                labels.append(status.capitalize())
    if not handles:
        return ()
    legend = ax.legend(handles, labels, loc="best", frameon=True, framealpha=0.85)
    return (legend,)


def _set_limits_and_warn_overlap(
    ax: Axes,
    positions: FloatArray,
    paths: tuple[FloatArray, ...],
    options: Graph2DRenderOptions,
    warning_messages: list[str],
    *,
    check_node_overlap: bool = True,
    include_node_positions: bool = True,
) -> None:
    points: list[FloatArray] = []
    if include_node_positions and positions.size:
        points.append(positions)
    points.extend(paths)
    if not points:
        ax.set_xlim(-1.0, 1.0)
        ax.set_ylim(-1.0, 1.0)
        return
    all_points = np.concatenate(points, axis=0)
    minima = np.min(all_points, axis=0)
    maxima = np.max(all_points, axis=0)
    span = maxima - minima
    scale = max(float(np.max(span)), 1.0)
    margin = options.margin_fraction * scale
    for axis_index, setter in enumerate((ax.set_xlim, ax.set_ylim)):
        if span[axis_index] <= 1.0e-14:
            center = 0.5 * (minima[axis_index] + maxima[axis_index])
            setter(center - 0.5 * scale - margin, center + 0.5 * scale + margin)
        else:
            setter(minima[axis_index] - margin, maxima[axis_index] + margin)
    if check_node_overlap and positions.shape[0] > 1:
        delta = positions[:, None, :] - positions[None, :, :]
        distance = np.linalg.norm(delta, axis=2)
        distance[np.eye(distance.shape[0], dtype=bool)] = np.inf
        minimum = float(np.min(distance))
        if minimum < 0.005 * scale:
            warning_messages.append(
                "Some distinct nodes substantially overlap in the selected 2-D projection."
            )


def plot_decorated_graph_2d(
    view: DecoratedGraphView,
    *,
    layout: GraphLayoutOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    periodic: PeriodicDisplayOptions | None = None,
    options: Graph2DRenderOptions | None = None,
    axes: Axes | None = None,
) -> GraphRenderResult:
    """Render a decorated graph as a deterministic static Matplotlib figure."""
    if not isinstance(view, DecoratedGraphView):
        raise TypeError("view must be a DecoratedGraphView.")
    layout = layout or GraphLayoutOptions()
    style = style or GraphStyle.default()
    policy = complexity_policy or GraphComplexityPolicy()
    options = options or Graph2DRenderOptions()
    explicit_periodic_view = None
    if periodic is not None:
        if (
            options.periodic_edge_mode != "translated_segment"
            or options.periodic_node_mode != "canonical"
            or not options.show_periodic_ghosts
        ):
            raise GraphLayoutError(
                "An explicit periodic display request conflicts with legacy 2-D "
                "periodic options. Use their defaults when periodic= is supplied."
            )
        explicit_periodic_view = prepare_periodic_graph_view(
            view,
            periodic=periodic,
            focus=focus,
            graph_filter=graph_filter,
            complexity_policy=policy,
        )
        prepared = prepare_graph_view(
            explicit_periodic_view.graph, focus=None, graph_filter=None
        )
        warning_messages = list(explicit_periodic_view.warnings)
    else:
        prepared = prepare_graph_view(view, focus=focus, graph_filter=graph_filter)
        warning_messages = list(view.metadata.get("adapter_warnings", ()))
    _check_renderer_graph_features(prepared, options, warning_messages)
    resolved_node_styles = resolve_node_styles(style, prepared)
    node_styles = _node_styles_for_display(style, resolved_node_styles)
    edge_styles = resolve_edge_styles(style, prepared)
    if (
        style.node_display_mode is NodeDisplayMode.HIDDEN
        and style.labels.node_attribute is not None
    ):
        warning_messages.append(
            "Node labels are suppressed because node_display_mode='hidden'."
        )
    complexity = _complexity_report(view, prepared, style, edge_styles, policy)
    _enforce_complexity(complexity, policy, warning_messages)
    resolved_layout_method = _resolved_layout_method(prepared, layout)
    if explicit_periodic_view is None:
        physical_positions, display_shifts, node_periodic_metadata = (
            _periodic_display_geometry(
                prepared,
                options,
                warning_messages,
                layout_method=resolved_layout_method,
            )
        )
    else:
        physical_positions = prepared.node_positions_3d
        display_shifts = prepared.edge_image_shifts
        node_periodic_metadata = dict(explicit_periodic_view.periodic_metadata)
    positions, layout_metadata, projection = _layout_positions(
        prepared, layout, warning_messages, physical_positions=physical_positions
    )
    paths = _edge_paths(
        prepared,
        positions,
        projection,
        layout_metadata["method"],
        options,
        warning_messages,
        edge_image_shifts=display_shifts,
    )
    if np.any(~np.isfinite(positions)) or any(
        np.any(~np.isfinite(path)) for path in paths
    ):
        raise GraphLayoutError("Layout produced nonfinite coordinates.")

    if axes is None:
        figure, axes = plt.subplots(figsize=options.figsize, dpi=options.dpi)
    else:
        figure = axes.figure
    axes.set_facecolor(style.background_color)
    figure.patch.set_facecolor(style.background_color)

    edge_artists = _render_edges(
        axes, paths, prepared.edge_endpoints, edge_styles, node_styles
    )
    ghost_artists = _render_periodic_ghost_nodes(
        axes,
        prepared,
        paths,
        display_shifts,
        node_styles,
        enabled=(
            options.show_periodic_ghosts
            and explicit_periodic_view is None
            and style.node_display_mode is not NodeDisplayMode.HIDDEN
        ),
        layout_method=layout_metadata["method"],
        periodic_edge_mode=options.periodic_edge_mode,
    )
    node_artists = (
        ()
        if style.node_display_mode is NodeDisplayMode.HIDDEN
        else _render_nodes(axes, positions, node_styles)
    )
    label_artists = _render_labels(axes, prepared, positions, paths, style)
    legend_artists = _add_legend(axes, prepared, style)

    _set_limits_and_warn_overlap(
        axes,
        positions,
        paths,
        options,
        warning_messages,
        check_node_overlap=style.node_display_mode is not NodeDisplayMode.HIDDEN,
        include_node_positions=style.node_display_mode is not NodeDisplayMode.HIDDEN,
    )
    if options.equal_aspect:
        axes.set_aspect("equal", adjustable="box")
    show_axes = options.show_axes
    if show_axes is None:
        show_axes = layout_metadata["method"] == "physical"
    if show_axes:
        axes.set_xlabel(
            "Projected coordinate 1 (Å)"
            if layout_metadata["method"] == "physical"
            else "Layout x"
        )
        axes.set_ylabel(
            "Projected coordinate 2 (Å)"
            if layout_metadata["method"] == "physical"
            else "Layout y"
        )
    else:
        axes.set_axis_off()
    if options.title:
        axes.set_title(options.title)
    if options.tight_layout:
        figure.tight_layout()

    for message in warning_messages:
        pywarnings.warn(message, RuntimeWarning, stacklevel=2)
    periodic_count = 0
    if display_shifts is not None:
        periodic_count = int(np.count_nonzero(np.any(display_shifts != 0, axis=1)))
    artist_groups = {
        "edges": edge_artists,
        "ghost_nodes": ghost_artists,
        "nodes": node_artists,
        "labels": label_artists,
        "legend": legend_artists,
    }
    return GraphRenderResult(
        figure=figure,
        axes=axes,
        rendered_node_keys=prepared.node_keys,
        rendered_edge_keys=prepared.edge_keys,
        node_positions_2d=positions,
        edge_paths_2d=paths,
        artist_groups=artist_groups,
        layout_metadata={
            **layout_metadata,
            "matplotlib_version": matplotlib.__version__,
        },
        style_metadata={
            "preset": type(style).__name__,
            "legend": style.legend,
            "palette": style.palette.name,
            "node_rule_count": len(style.node_rules),
            "edge_rule_count": len(style.edge_rules),
            "node_display_mode": style.node_display_mode.value,
            "node_dot_size": style.node_dot_size,
        },
        selection_metadata=(
            {
                **dict(prepared.selection_metadata),
                "source_view_metadata": dict(view.metadata),
            }
            if explicit_periodic_view is None
            else {
                **dict(explicit_periodic_view.selection_metadata),
                "source_view_metadata": dict(view.metadata),
            }
        ),
        periodic_metadata=(
            {
                "edge_mode": options.periodic_edge_mode,
                "periodic_edge_count": periodic_count,
                "periodic_ghost_count": sum(
                    len(artist.get_offsets()) for artist in ghost_artists
                ),
                "show_periodic_ghosts": options.show_periodic_ghosts,
                **node_periodic_metadata,
            }
            if explicit_periodic_view is None
            else {
                **dict(explicit_periodic_view.periodic_metadata),
                "renderer_consumed_explicit_periodic_graph": True,
            }
        ),
        complexity=complexity,
        warnings=tuple(warning_messages),
    )


__all__ = [
    "Graph2DRenderOptions",
    "GraphLayoutOptions",
    "GraphRenderResult",
    "plot_decorated_graph_2d",
]
