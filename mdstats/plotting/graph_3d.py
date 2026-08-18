"""Optional interactive Plotly renderer for decorated spatial graphs.

The module imports Plotly lazily.  Scientific graph identity and periodic
materialization remain owned by :mod:`mdstats.plotting.graph_view` and
:mod:`mdstats.plotting.periodic_graph`, respectively.
"""

from __future__ import annotations

import math
import os
import warnings as pywarnings
from collections import defaultdict
from collections.abc import Mapping
from itertools import product
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
from matplotlib.colors import to_rgba

from .graph_errors import (
    GraphComplexityError,
    GraphOptionalDependencyError,
    GraphStyleError,
    GraphUnsupportedFeatureError,
    GraphVisualizationError,
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
from .graph_view import (
    DecoratedGraphView,
    GraphComplexityPolicy,
    GraphComplexityReport,
    GraphFilter,
    GraphFocus,
    PreparedGraphView,
    _column_value,
    prepare_graph_view,
)
from .periodic_graph import (
    CanonicalCellDisplay,
    PeriodicDisplayOptions,
    PeriodicEdgeKey,
    PeriodicGraphView,
    PeriodicNodeKey,
    prepare_periodic_graph_view,
)


_PLOTLY_MARKERS = {
    "o": "circle",
    "s": "square",
    "^": "triangle-up",
    "v": "triangle-down",
    "d": "diamond",
    "x": "x",
    "+": "cross",
    "*": "star",
}
_PLOTLY_DASHES = {
    "solid": "solid",
    "dashed": "dash",
    "dotted": "dot",
    "dashdot": "dashdot",
}


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


@dataclass(frozen=True, slots=True)
class Graph3DRenderOptions:
    """Plotly-specific options for interactive 3-D graph rendering."""

    width: int = 1000
    height: int = 800
    title: str | None = None
    show_axes: bool = False
    equal_aspect: bool = True
    background: Literal["light", "dark", "transparent"] = "light"
    camera_projection: Literal["perspective", "orthographic"] = "orthographic"
    camera_eye: tuple[float, float, float] | None = None
    uirevision: str | None = "mdstats-graph-3d"
    cell_mode: Literal["auto", "none", "reference", "all", "outer_boundary"] = "auto"
    cell_color: str = "#666666"
    cell_width: float = 3.2
    cell_alpha: float = 0.72
    show_legend: bool = True
    node_hover: bool = True
    edge_hover: bool = True
    hover_float_precision: int = 4
    edge_color_mode: Literal["constant", "midpoint_split", "segmented_gradient"] = (
        "midpoint_split"
    )
    gradient_segments: int = 8
    directed_edge_mode: Literal["reject", "line_only"] = "reject"
    allow_parallel_overlap: bool = False
    max_plotly_traces: int = 512

    def __post_init__(self) -> None:
        object.__setattr__(self, "width", _positive_int(self.width, name="width"))
        object.__setattr__(self, "height", _positive_int(self.height, name="height"))
        if self.title is not None and not isinstance(self.title, str):
            raise GraphStyleError("title must be None or a string.")
        if self.background not in {"light", "dark", "transparent"}:
            raise GraphStyleError("Invalid 3-D background preset.")
        if self.camera_projection not in {"perspective", "orthographic"}:
            raise GraphStyleError("Invalid camera_projection.")
        if self.camera_eye is not None:
            if len(self.camera_eye) != 3:
                raise GraphStyleError("camera_eye must contain three finite values.")
            eye = tuple(float(value) for value in self.camera_eye)
            if any(not np.isfinite(value) for value in eye) or np.linalg.norm(eye) == 0:
                raise GraphStyleError("camera_eye must be finite and nonzero.")
            object.__setattr__(self, "camera_eye", eye)
        if self.uirevision is not None and not isinstance(self.uirevision, str):
            raise GraphStyleError("uirevision must be None or a string.")
        if self.cell_mode not in {
            "auto",
            "none",
            "reference",
            "all",
            "outer_boundary",
        }:
            raise GraphStyleError("Invalid cell_mode.")
        # Validate with the shared color parser.
        try:
            to_rgba(self.cell_color)
        except ValueError as exc:
            raise GraphStyleError("cell_color is invalid.") from exc
        width = float(self.cell_width)
        alpha = float(self.cell_alpha)
        if not np.isfinite(width) or width < 0:
            raise GraphStyleError("cell_width must be finite and nonnegative.")
        if not np.isfinite(alpha) or not 0 <= alpha <= 1:
            raise GraphStyleError("cell_alpha must lie in [0, 1].")
        object.__setattr__(self, "cell_width", width)
        object.__setattr__(self, "cell_alpha", alpha)
        if isinstance(self.hover_float_precision, bool) or not isinstance(
            self.hover_float_precision, (int, np.integer)
        ):
            raise GraphStyleError("hover_float_precision must be an integer.")
        precision = int(self.hover_float_precision)
        if precision < 0 or precision > 12:
            raise GraphStyleError("hover_float_precision must lie in [0, 12].")
        object.__setattr__(self, "hover_float_precision", precision)
        if self.edge_color_mode not in {
            "constant",
            "midpoint_split",
            "segmented_gradient",
        }:
            raise GraphStyleError("Invalid edge_color_mode.")
        object.__setattr__(
            self,
            "gradient_segments",
            _positive_int(self.gradient_segments, name="gradient_segments"),
        )
        if self.gradient_segments < 2:
            raise GraphStyleError("gradient_segments must be at least 2.")
        if self.directed_edge_mode not in {"reject", "line_only"}:
            raise GraphStyleError("Invalid directed_edge_mode.")
        object.__setattr__(
            self,
            "max_plotly_traces",
            _positive_int(self.max_plotly_traces, name="max_plotly_traces"),
        )
        object.__setattr__(self, "show_axes", bool(self.show_axes))
        object.__setattr__(self, "equal_aspect", bool(self.equal_aspect))
        object.__setattr__(self, "show_legend", bool(self.show_legend))
        object.__setattr__(self, "node_hover", bool(self.node_hover))
        object.__setattr__(self, "edge_hover", bool(self.edge_hover))
        object.__setattr__(
            self, "allow_parallel_overlap", bool(self.allow_parallel_overlap)
        )


@dataclass(slots=True)
class InteractiveGraphRenderResult:
    """Interactive Plotly result with stable display/source trace mappings."""

    figure: Any
    periodic_view: PeriodicGraphView
    rendered_node_keys: tuple[PeriodicNodeKey, ...]
    rendered_edge_keys: tuple[PeriodicEdgeKey, ...]
    node_trace_indices: Mapping[str, tuple[int, ...]]
    edge_trace_indices: Mapping[str, tuple[int, ...]]
    hover_trace_indices: Mapping[str, tuple[int, ...]]
    cell_trace_indices: tuple[int, ...]
    complexity: GraphComplexityReport
    style_metadata: Mapping[str, Any]
    render_metadata: Mapping[str, Any]
    warnings: tuple[str, ...]

    def __post_init__(self) -> None:
        self.rendered_node_keys = tuple(self.rendered_node_keys)
        self.rendered_edge_keys = tuple(self.rendered_edge_keys)
        self.node_trace_indices = MappingProxyType(
            {key: tuple(value) for key, value in self.node_trace_indices.items()}
        )
        self.edge_trace_indices = MappingProxyType(
            {key: tuple(value) for key, value in self.edge_trace_indices.items()}
        )
        self.hover_trace_indices = MappingProxyType(
            {key: tuple(value) for key, value in self.hover_trace_indices.items()}
        )
        self.cell_trace_indices = tuple(self.cell_trace_indices)
        self.style_metadata = MappingProxyType(dict(self.style_metadata))
        self.render_metadata = MappingProxyType(dict(self.render_metadata))
        self.warnings = tuple(self.warnings)

    def to_html(
        self,
        *,
        include_plotlyjs: Literal["cdn", "directory"] | bool = "cdn",
        full_html: bool = True,
    ) -> str:
        """Return the current Plotly figure as HTML."""
        try:
            return self.figure.to_html(
                include_plotlyjs=include_plotlyjs,
                full_html=full_html,
            )
        except Exception as exc:  # pragma: no cover - Plotly owns serializer details
            raise GraphVisualizationError(
                "Could not serialize Plotly figure to HTML."
            ) from exc

    def write_html(
        self,
        path: str | os.PathLike[str],
        *,
        include_plotlyjs: Literal["cdn", "directory"] | bool = "cdn",
        full_html: bool = True,
        auto_open: bool = False,
    ) -> None:
        """Write the current Plotly figure to an HTML file."""
        target = Path(path)
        try:
            self.figure.write_html(
                str(target),
                include_plotlyjs=include_plotlyjs,
                full_html=full_html,
                auto_open=auto_open,
            )
        except Exception as exc:
            raise GraphVisualizationError(
                f"Could not write Plotly HTML to {target}."
            ) from exc


def _import_plotly() -> tuple[Any, str]:
    try:
        import plotly
        import plotly.graph_objects as go
    except ImportError as exc:
        raise GraphOptionalDependencyError(
            "Interactive 3-D graph rendering requires Plotly. Install it with "
            "`pip install mdstats[interactive]`."
        ) from exc
    return go, str(plotly.__version__)


def _rgba_string(color: Any, alpha: float = 1.0) -> str:
    red, green, blue, base_alpha = to_rgba(color)
    final_alpha = min(1.0, max(0.0, float(base_alpha) * float(alpha)))
    return (
        f"rgba({round(red * 255)}, {round(green * 255)}, "
        f"{round(blue * 255)}, {final_alpha:.6g})"
    )


def _interpolate_rgba(source: Any, target: Any, fraction: float, alpha: float) -> str:
    left = np.asarray(to_rgba(source), dtype=float)
    right = np.asarray(to_rgba(target), dtype=float)
    value = (1.0 - fraction) * left + fraction * right
    value[3] *= alpha
    return (
        f"rgba({round(value[0] * 255)}, {round(value[1] * 255)}, "
        f"{round(value[2] * 255)}, {float(value[3]):.6g})"
    )


def _node_marker(style: NodeStyle) -> str:
    try:
        return _PLOTLY_MARKERS[style.marker]
    except KeyError as exc:
        raise GraphUnsupportedFeatureError(
            f"Matplotlib marker {style.marker!r} is unsupported by the 3-D renderer."
        ) from exc


def _edge_dash(style: EdgeStyle) -> str:
    try:
        return _PLOTLY_DASHES[style.line_style]
    except KeyError as exc:  # pragma: no cover - style validates literals
        raise GraphUnsupportedFeatureError(
            f"Edge dash {style.line_style!r} is unsupported by Plotly."
        ) from exc


def _attribute_value(column: Any, position: int) -> Any:
    value = _column_value(column, position)
    if isinstance(value, np.generic):
        return value.item()
    return value


def _preferred_attribute_names(attributes: Mapping[str, Any]) -> tuple[str, ...]:
    common = (
        "atom_index",
        "symbol",
        "degree",
        "component_id",
        "affected",
        "ring_id",
        "ring_size",
        "site_id",
        "cage_id",
        "transition_status",
        "species_pair",
        "display_role",
    )
    selected = [name for name in common if name in attributes]
    selected.extend(
        name
        for name in sorted(attributes)
        if name not in selected and name != "image_shift"
    )
    return tuple(selected[:16])


def _format_value(value: Any, precision: int) -> str:
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{precision}f}"
    if isinstance(value, np.ndarray):
        return str(value.tolist())
    return str(value)


def _node_hover_text(
    prepared: PreparedGraphView,
    periodic_view: PeriodicGraphView,
    position: int,
    precision: int,
) -> str:
    key = periodic_view.graph.node_keys[position]
    source_position = int(periodic_view.source_node_positions[position])
    source_key = periodic_view.source_view.node_keys[source_position]
    role = periodic_view.node_roles[position].value
    image = tuple(int(value) for value in periodic_view.node_image_shifts[position])
    xyz = np.asarray(periodic_view.graph.node_positions_3d[position], dtype=float)
    lines = [
        f"source node: {source_key}",
        f"display key: {key}",
        f"image shift: {image}",
        f"display role: {role}",
        "position: (" + ", ".join(f"{value:.{precision}f}" for value in xyz) + ")",
    ]
    attrs = prepared.node_attributes
    for name in _preferred_attribute_names(attrs):
        if name in {"display_role"}:
            continue
        lines.append(
            f"{name}: {_format_value(_attribute_value(attrs[name], position), precision)}"
        )
    frame = periodic_view.source_view.metadata.get("collection_frame_index")
    if frame is not None:
        lines.append(f"collection frame: {frame}")
    return "<br>".join(lines)


def _edge_hover_text(
    prepared: PreparedGraphView,
    periodic_view: PeriodicGraphView,
    position: int,
    precision: int,
) -> str:
    source_display, target_display = (
        int(value) for value in periodic_view.graph.edge_endpoints[position]
    )
    source_key = periodic_view.graph.node_keys[source_display]
    target_key = periodic_view.graph.node_keys[target_display]
    xyz0 = np.asarray(
        periodic_view.graph.node_positions_3d[source_display], dtype=float
    )
    xyz1 = np.asarray(
        periodic_view.graph.node_positions_3d[target_display], dtype=float
    )
    length = float(np.linalg.norm(xyz1 - xyz0))
    source_edge_position = int(periodic_view.source_edge_positions[position])
    scientific_edge_key = periodic_view.source_view.edge_keys[source_edge_position]
    lines = [
        f"source edge: {scientific_edge_key}",
        f"display key: {periodic_view.graph.edge_keys[position]}",
        f"source endpoint: {source_key}",
        f"target endpoint: {target_key}",
        f"display role: {periodic_view.edge_roles[position].value}",
        f"length: {length:.{precision}f}",
    ]
    attrs = prepared.edge_attributes
    for name in _preferred_attribute_names(attrs):
        if name in {"display_role", "source_image_shift", "target_image_shift"}:
            continue
        lines.append(
            f"{name}: {_format_value(_attribute_value(attrs[name], position), precision)}"
        )
    return "<br>".join(lines)


def _node_legend_label(prepared: PreparedGraphView, position: int) -> str:
    if "symbol" in prepared.node_attributes:
        return str(_attribute_value(prepared.node_attributes["symbol"], position))
    role = str(_attribute_value(prepared.node_attributes["display_role"], position))
    return "Nodes" if role == "canonical" else role.replace("_", " ").title()


def _edge_legend_label(prepared: PreparedGraphView, position: int) -> str:
    if "transition_status" in prepared.edge_attributes:
        status = str(
            _attribute_value(prepared.edge_attributes["transition_status"], position)
        )
        return status.title()
    return "Edges"


def _node_label_text(
    style: GraphStyle,
    periodic_view: PeriodicGraphView,
    prepared: PreparedGraphView,
    position: int,
) -> str | None:
    labels = style.labels
    if labels.node_attribute is None:
        return None
    display_key = periodic_view.graph.node_keys[position]
    source_key = display_key.source_node_key
    if (
        labels.node_keys is not None
        and display_key not in labels.node_keys
        and source_key not in labels.node_keys
    ):
        return None
    return str(
        _attribute_value(prepared.node_attributes[labels.node_attribute], position)
    )


def _validate_graph_features(
    periodic_view: PeriodicGraphView,
    options: Graph3DRenderOptions,
    warning_messages: list[str],
) -> None:
    graph = periodic_view.graph
    if graph.directed:
        if options.directed_edge_mode == "reject":
            raise GraphUnsupportedFeatureError(
                "Directed graphs require directed_edge_mode='line_only' in G5."
            )
        warning_messages.append(
            "Directed edges are rendered as lines without 3-D arrowheads; direction "
            "is available through endpoint order and hover metadata."
        )
    pairs: dict[tuple[int, int], int] = {}
    overlap = False
    for source, target in graph.edge_endpoints:
        source_i, target_i = int(source), int(target)
        if source_i == target_i:
            raise GraphUnsupportedFeatureError(
                "Coincident self-loops are unsupported by the 3-D renderer."
            )
        pair = (
            (source_i, target_i)
            if graph.directed
            else tuple(sorted((source_i, target_i)))
        )
        if pair in pairs:
            overlap = True
        pairs[pair] = pairs.get(pair, 0) + 1
    if overlap:
        if not options.allow_parallel_overlap:
            raise GraphUnsupportedFeatureError(
                "Parallel display edges overlap in the straight-line 3-D renderer. "
                "Set allow_parallel_overlap=True to render them intentionally."
            )
        warning_messages.append(
            "Parallel display edges overlap exactly because curved separation is deferred."
        )


def _requested_label_count(style: GraphStyle, periodic_view: PeriodicGraphView) -> int:
    labels = style.labels
    if (
        labels.node_attribute is None
        or style.node_display_mode is NodeDisplayMode.HIDDEN
    ):
        return 0
    if labels.node_keys is None:
        return periodic_view.graph.n_nodes
    requested = set(labels.node_keys)
    return sum(
        key in requested or key.source_node_key in requested
        for key in periodic_view.graph.node_keys
    )


def _complexity_report(
    view: DecoratedGraphView,
    periodic_view: PeriodicGraphView,
    style: GraphStyle,
    options: Graph3DRenderOptions,
    policy: GraphComplexityPolicy,
) -> GraphComplexityReport:
    labels = _requested_label_count(style, periodic_view)
    edge_count = periodic_view.graph.n_edges
    primitives = (
        edge_count
        if options.edge_color_mode == "constant"
        else 2 * edge_count
        if options.edge_color_mode == "midpoint_split"
        else options.gradient_segments * edge_count
    )
    exceeded: list[str] = []
    if periodic_view.graph.n_nodes > policy.max_nodes:
        exceeded.append("max_nodes")
    if edge_count > policy.max_edges:
        exceeded.append("max_edges")
    if labels > policy.max_labels:
        exceeded.append("max_labels")
    if primitives > policy.max_gradient_segments:
        exceeded.append("max_gradient_segments")
    return GraphComplexityReport(
        input_nodes=view.n_nodes,
        input_edges=view.n_edges,
        selected_nodes=periodic_view.graph.n_nodes,
        selected_edges=edge_count,
        requested_labels=labels,
        estimated_gradient_segments=primitives,
        exceeded_limits=tuple(exceeded),
    )


def _enforce_complexity(
    report: GraphComplexityReport,
    policy: GraphComplexityPolicy,
    warning_messages: list[str],
) -> None:
    if not report.exceeded_limits:
        return
    message = "3-D rendering exceeds complexity limits: " + ", ".join(
        report.exceeded_limits
    )
    if policy.overflow in {"error", "require_focus"}:
        raise GraphComplexityError(message + ". Reduce focus or periodic image ranges.")
    warning_messages.append(message + "; rendering because overflow='warn_and_render'.")


def _cell_segments(
    cell: np.ndarray, shift: np.ndarray, span: np.ndarray | None = None
) -> list[tuple[np.ndarray, np.ndarray]]:
    span = (
        np.ones(3, dtype=np.int64) if span is None else np.asarray(span, dtype=np.int64)
    )
    corners: dict[tuple[int, int, int], np.ndarray] = {}
    for bits in product((0, 1), repeat=3):
        fractional = (
            np.asarray(shift, dtype=float) + np.asarray(bits, dtype=float) * span
        )
        corners[bits] = fractional @ cell
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    for bits in product((0, 1), repeat=3):
        for axis in range(3):
            if bits[axis] != 0:
                continue
            other = list(bits)
            other[axis] = 1
            segments.append((corners[bits], corners[tuple(other)]))
    return segments


def _wireframe_segments(
    periodic_view: PeriodicGraphView,
    options: Graph3DRenderOptions,
) -> tuple[list[tuple[np.ndarray, np.ndarray]], str]:
    mode = options.cell_mode
    cell = periodic_view.source_view.cell
    if mode == "auto":
        mode = "reference" if cell is not None else "none"
    if mode == "none":
        return [], mode
    if cell is None:
        raise GraphUnsupportedFeatureError(
            f"cell_mode={mode!r} requires a finite cell."
        )
    cell_array = np.asarray(cell, dtype=float)
    if mode == "reference":
        return _cell_segments(cell_array, np.zeros(3, dtype=np.int64)), mode
    if mode == "all":
        segments: list[tuple[np.ndarray, np.ndarray]] = []
        seen: set[tuple[tuple[float, ...], tuple[float, ...]]] = set()
        for shift in periodic_view.primary_cell_image_shifts:
            for start, stop in _cell_segments(cell_array, shift):
                a = tuple(np.round(start, 12))
                b = tuple(np.round(stop, 12))
                key = tuple(sorted((a, b)))  # type: ignore[assignment]
                if key not in seen:
                    seen.add(key)
                    segments.append((start, stop))
        return segments, mode
    if mode == "outer_boundary":
        ranges = periodic_view.periodic_metadata.get("image_ranges")
        if ranges is None:
            raise GraphUnsupportedFeatureError(
                "outer_boundary requires an expanded rectangular image range."
            )
        lower = np.asarray([interval[0] for interval in ranges], dtype=np.int64)
        span = np.asarray(
            [interval[1] - interval[0] + 1 for interval in ranges], dtype=np.int64
        )
        return _cell_segments(cell_array, lower, span), mode
    raise GraphUnsupportedFeatureError(f"Unsupported cell_mode={mode!r}.")


def _scene_ranges(
    positions: np.ndarray, warning_messages: list[str]
) -> list[list[float]]:
    if positions.size == 0:
        return [[-0.5, 0.5], [-0.5, 0.5], [-0.5, 0.5]]
    minima = np.min(positions, axis=0)
    maxima = np.max(positions, axis=0)
    extents = maxima - minima
    max_extent = max(float(np.max(extents)), 1.0)
    ranges: list[list[float]] = []
    padded = False
    for low, high, extent in zip(minima, maxima, extents, strict=True):
        if float(extent) <= 1.0e-12:
            pad = 0.05 * max_extent
            ranges.append([float(low - pad), float(high + pad)])
            padded = True
        else:
            pad = 0.03 * float(extent)
            ranges.append([float(low - pad), float(high + pad)])
    if padded:
        warning_messages.append(
            "Equal-aspect display added range padding along a degenerate coordinate axis."
        )
    return ranges


def plot_decorated_graph_3d(
    view: DecoratedGraphView,
    *,
    periodic: PeriodicDisplayOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    options: Graph3DRenderOptions | None = None,
) -> InteractiveGraphRenderResult:
    """Render a decorated graph as an interactive Plotly 3-D scene."""
    if not isinstance(view, DecoratedGraphView):
        raise TypeError("view must be a DecoratedGraphView.")
    style = style or GraphStyle.default()
    policy = complexity_policy or GraphComplexityPolicy()
    options = options or Graph3DRenderOptions()
    if not isinstance(style, GraphStyle):
        raise TypeError("style must be a GraphStyle.")
    go, plotly_version = _import_plotly()

    periodic_view = prepare_periodic_graph_view(
        view,
        periodic=periodic or CanonicalCellDisplay(),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=policy,
    )
    graph = periodic_view.graph
    if graph.node_positions_3d is None or np.any(~np.isfinite(graph.node_positions_3d)):
        raise GraphUnsupportedFeatureError(
            "3-D rendering requires finite node positions."
        )
    prepared = prepare_graph_view(graph, focus=None, graph_filter=None)
    warning_messages: list[str] = list(periodic_view.warnings)
    _validate_graph_features(periodic_view, options, warning_messages)
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
    complexity = _complexity_report(view, periodic_view, style, options, policy)
    _enforce_complexity(complexity, policy, warning_messages)

    positions = np.asarray(graph.node_positions_3d, dtype=float)
    node_groups: dict[tuple[Any, ...], list[int]] = defaultdict(list)
    if style.node_display_mode is not NodeDisplayMode.HIDDEN:
        for position, node_style in enumerate(node_styles):
            marker = _node_marker(node_style)
            label = _node_legend_label(prepared, position)
            key = (
                marker,
                _rgba_string(node_style.face_color, node_style.alpha),
                max(2.0, math.sqrt(max(node_style.size, 0.0))),
                _rgba_string(node_style.edge_color, node_style.alpha),
                node_style.edge_width,
                label,
            )
            node_groups[key].append(position)

    # Build line primitive groups before creating traces so trace complexity is exact.
    edge_groups: dict[tuple[Any, ...], dict[str, Any]] = {}

    def append_segment(
        *,
        start: np.ndarray,
        stop: np.ndarray,
        color: str,
        edge_style: EdgeStyle,
        label: str,
        edge_position: int,
    ) -> None:
        group_key = (
            color,
            edge_style.width,
            _edge_dash(edge_style),
            label,
        )
        payload = edge_groups.setdefault(
            group_key,
            {"x": [], "y": [], "z": [], "edge_positions": []},
        )
        payload["x"].extend((float(start[0]), float(stop[0]), None))
        payload["y"].extend((float(start[1]), float(stop[1]), None))
        payload["z"].extend((float(start[2]), float(stop[2]), None))
        payload["edge_positions"].append(edge_position)

    for edge_position, (source, target) in enumerate(graph.edge_endpoints):
        source_i, target_i = int(source), int(target)
        start = positions[source_i]
        stop = positions[target_i]
        edge_style = edge_styles[edge_position]
        label = _edge_legend_label(prepared, edge_position)
        if options.edge_color_mode == "constant":
            append_segment(
                start=start,
                stop=stop,
                color=_rgba_string(edge_style.color, edge_style.alpha),
                edge_style=edge_style,
                label=label,
                edge_position=edge_position,
            )
        elif options.edge_color_mode == "midpoint_split":
            midpoint = 0.5 * (start + stop)
            append_segment(
                start=start,
                stop=midpoint,
                color=_rgba_string(
                    node_styles[source_i].face_color,
                    edge_style.alpha * node_styles[source_i].alpha,
                ),
                edge_style=edge_style,
                label=label,
                edge_position=edge_position,
            )
            append_segment(
                start=midpoint,
                stop=stop,
                color=_rgba_string(
                    node_styles[target_i].face_color,
                    edge_style.alpha * node_styles[target_i].alpha,
                ),
                edge_style=edge_style,
                label=label,
                edge_position=edge_position,
            )
        else:
            for segment in range(options.gradient_segments):
                t0 = segment / options.gradient_segments
                t1 = (segment + 1) / options.gradient_segments
                midpoint_fraction = 0.5 * (t0 + t1)
                append_segment(
                    start=(1.0 - t0) * start + t0 * stop,
                    stop=(1.0 - t1) * start + t1 * stop,
                    color=_interpolate_rgba(
                        node_styles[source_i].face_color,
                        node_styles[target_i].face_color,
                        midpoint_fraction,
                        edge_style.alpha,
                    ),
                    edge_style=edge_style,
                    label=label,
                    edge_position=edge_position,
                )

    cell_segments, resolved_cell_mode = _wireframe_segments(periodic_view, options)
    projected_trace_count = (
        len(node_groups)
        + len(edge_groups)
        + (1 if options.edge_hover and graph.n_edges else 0)
        + (1 if cell_segments else 0)
    )
    if projected_trace_count > options.max_plotly_traces:
        raise GraphComplexityError(
            f"3-D rendering requires {projected_trace_count} Plotly traces, exceeding "
            f"max_plotly_traces={options.max_plotly_traces}."
        )

    figure = go.Figure()
    node_trace_indices: dict[str, list[int]] = defaultdict(list)
    edge_trace_indices: dict[str, list[int]] = defaultdict(list)
    hover_trace_indices: dict[str, list[int]] = defaultdict(list)
    cell_trace_indices: list[int] = []
    legend_seen: set[str] = set()
    show_legend = options.show_legend and style.legend != "none"

    for group_key, indices in node_groups.items():
        marker, color, size, outline_color, outline_width, label = group_key
        hover = [
            _node_hover_text(
                prepared, periodic_view, position, options.hover_float_precision
            )
            for position in indices
        ]
        labels = [
            _node_label_text(style, periodic_view, prepared, position)
            for position in indices
        ]
        mode = (
            "markers+text" if any(value is not None for value in labels) else "markers"
        )
        trace = go.Scatter3d(
            x=positions[indices, 0],
            y=positions[indices, 1],
            z=positions[indices, 2],
            mode=mode,
            text=labels if mode == "markers+text" else None,
            textposition="top center",
            textfont={"size": style.labels.font_size},
            marker={
                "symbol": marker,
                "color": color,
                "size": size,
                "line": {"color": outline_color, "width": outline_width},
            },
            name=label,
            legendgroup=f"node:{label}",
            showlegend=show_legend and label not in legend_seen,
            hovertext=hover if options.node_hover else None,
            hovertemplate="%{hovertext}<extra></extra>" if options.node_hover else None,
            hoverinfo=None if options.node_hover else "skip",
        )
        if trace.showlegend:
            legend_seen.add(label)
        figure.add_trace(trace)
        node_trace_indices[label].append(len(figure.data) - 1)

    for group_key, payload in edge_groups.items():
        color, width, dash, label = group_key
        trace = go.Scatter3d(
            x=payload["x"],
            y=payload["y"],
            z=payload["z"],
            mode="lines",
            line={"color": color, "width": width, "dash": dash},
            name=label,
            legendgroup=f"edge:{label}",
            showlegend=show_legend and label not in legend_seen,
            hoverinfo="skip",
        )
        if trace.showlegend:
            legend_seen.add(label)
        figure.add_trace(trace)
        edge_trace_indices[label].append(len(figure.data) - 1)

    if options.edge_hover and graph.n_edges:
        midpoints = 0.5 * (
            positions[graph.edge_endpoints[:, 0]]
            + positions[graph.edge_endpoints[:, 1]]
        )
        hover = [
            _edge_hover_text(
                prepared, periodic_view, position, options.hover_float_precision
            )
            for position in range(graph.n_edges)
        ]
        figure.add_trace(
            go.Scatter3d(
                x=midpoints[:, 0],
                y=midpoints[:, 1],
                z=midpoints[:, 2],
                mode="markers",
                marker={"size": 7, "color": "rgba(0,0,0,0.01)"},
                showlegend=False,
                hovertext=hover,
                hovertemplate="%{hovertext}<extra></extra>",
                name="Edge metadata",
            )
        )
        hover_trace_indices["edge_midpoints"].append(len(figure.data) - 1)

    if cell_segments:
        x: list[float | None] = []
        y: list[float | None] = []
        z: list[float | None] = []
        for start, stop in cell_segments:
            x.extend((float(start[0]), float(stop[0]), None))
            y.extend((float(start[1]), float(stop[1]), None))
            z.extend((float(start[2]), float(stop[2]), None))
        figure.add_trace(
            go.Scatter3d(
                x=x,
                y=y,
                z=z,
                mode="lines",
                line={
                    "color": _rgba_string(options.cell_color, options.cell_alpha),
                    "width": options.cell_width,
                },
                name="Unit cell",
                legendgroup="cell",
                showlegend=show_legend,
                hoverinfo="skip",
            )
        )
        cell_trace_indices.append(len(figure.data) - 1)

    if options.background == "light":
        paper_color, scene_color, font_color = "white", "white", "#202020"
    elif options.background == "dark":
        paper_color, scene_color, font_color = "#111111", "#111111", "#F2F2F2"
    else:
        paper_color, scene_color, font_color = (
            "rgba(0,0,0,0)",
            "rgba(0,0,0,0)",
            "#202020",
        )
        warning_messages.append(
            "Transparent 3-D backgrounds may reduce contrast in some HTML viewers."
        )

    ranges = _scene_ranges(positions, warning_messages)
    axis_common = {
        "visible": options.show_axes,
        "showgrid": options.show_axes,
        "zeroline": False,
        "showbackground": options.show_axes,
        "backgroundcolor": scene_color,
    }
    scene = {
        "xaxis": {**axis_common, "title": "x", "range": ranges[0]},
        "yaxis": {**axis_common, "title": "y", "range": ranges[1]},
        "zaxis": {**axis_common, "title": "z", "range": ranges[2]},
        "camera": {
            "projection": {"type": options.camera_projection},
            **(
                {"eye": dict(zip(("x", "y", "z"), options.camera_eye, strict=True))}
                if options.camera_eye is not None
                else {}
            ),
        },
        "bgcolor": scene_color,
    }
    if options.equal_aspect:
        extents = np.asarray(
            [axis_range[1] - axis_range[0] for axis_range in ranges], dtype=float
        )
        max_extent = float(np.max(extents)) if extents.size else 1.0
        if not np.isfinite(max_extent) or max_extent <= 0.0:
            max_extent = 1.0
        aspectratio = {
            axis: float(extent / max_extent) if extent > 0.0 else 1.0
            for axis, extent in zip(("x", "y", "z"), extents, strict=True)
        }
        scene["aspectmode"] = "manual"
        scene["aspectratio"] = aspectratio
    else:
        scene["aspectmode"] = "auto"
    if not options.show_axes and not cell_segments:
        warning_messages.append(
            "Axes and unit-cell wireframes are both hidden; absolute orientation may be unclear."
        )
    if graph.n_nodes > 5000 or graph.n_edges > 10000:
        warning_messages.append(
            "The interactive hover payload is large and may affect browser performance."
        )

    figure.update_layout(
        width=options.width,
        height=options.height,
        title=options.title,
        scene=scene,
        paper_bgcolor=paper_color,
        plot_bgcolor=scene_color,
        font={"color": font_color},
        showlegend=show_legend,
        uirevision=options.uirevision,
        margin={"l": 0, "r": 0, "t": 50 if options.title else 10, "b": 0},
    )

    if len(figure.data) > options.max_plotly_traces:  # defensive exact check
        raise GraphComplexityError(
            "Final Plotly trace count exceeds max_plotly_traces."
        )
    for message in warning_messages:
        pywarnings.warn(message, RuntimeWarning, stacklevel=2)

    return InteractiveGraphRenderResult(
        figure=figure,
        periodic_view=periodic_view,
        rendered_node_keys=tuple(periodic_view.graph.node_keys),
        rendered_edge_keys=tuple(periodic_view.graph.edge_keys),
        node_trace_indices={
            key: tuple(value) for key, value in node_trace_indices.items()
        },
        edge_trace_indices={
            key: tuple(value) for key, value in edge_trace_indices.items()
        },
        hover_trace_indices={
            key: tuple(value) for key, value in hover_trace_indices.items()
        },
        cell_trace_indices=tuple(cell_trace_indices),
        complexity=complexity,
        style_metadata={
            "palette": style.palette.name,
            "legend": style.legend,
            "node_rule_count": len(style.node_rules),
            "edge_rule_count": len(style.edge_rules),
            "node_display_mode": style.node_display_mode.value,
            "node_dot_size": style.node_dot_size,
        },
        render_metadata={
            "plotly_version": plotly_version,
            "trace_count": len(figure.data),
            "node_trace_count": sum(
                len(value) for value in node_trace_indices.values()
            ),
            "edge_trace_count": sum(
                len(value) for value in edge_trace_indices.values()
            ),
            "hover_trace_count": sum(
                len(value) for value in hover_trace_indices.values()
            ),
            "cell_trace_count": len(cell_trace_indices),
            "cell_line_count": len(cell_segments),
            "cell_mode": resolved_cell_mode,
            "edge_color_mode": options.edge_color_mode,
            "edge_line_primitives": complexity.estimated_gradient_segments,
            "camera_projection": options.camera_projection,
            "equal_aspect": options.equal_aspect,
            "node_display_mode": style.node_display_mode.value,
        },
        warnings=tuple(warning_messages),
    )


__all__ = [
    "Graph3DRenderOptions",
    "InteractiveGraphRenderResult",
    "plot_decorated_graph_3d",
]
