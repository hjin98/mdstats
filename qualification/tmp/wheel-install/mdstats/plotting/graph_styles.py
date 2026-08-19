"""Declarative metadata-driven graph styles shared by visualization backends."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Literal

import numpy as np
from matplotlib.colors import is_color_like
from matplotlib.markers import MarkerStyle
from matplotlib.typing import ColorType as ColorLike

from .graph_errors import GraphStyleError
from .graph_view import (
    AttributeScalar,
    PreparedGraphView,
    _column_value,
)


def _validate_color(value: Any, *, name: str) -> ColorLike:
    if not is_color_like(value):
        raise GraphStyleError(f"{name}={value!r} is not a valid Matplotlib color.")
    return value


def _finite_nonnegative(value: Any, *, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise GraphStyleError(f"{name} must be numeric.") from exc
    if not np.isfinite(result) or result < 0.0:
        raise GraphStyleError(f"{name} must be finite and nonnegative.")
    return result


def _validate_alpha(value: Any, *, name: str = "alpha") -> float:
    result = _finite_nonnegative(value, name=name)
    if result > 1.0:
        raise GraphStyleError(f"{name} must lie in [0, 1].")
    return result


def _validate_marker(marker: Any) -> str:
    if not isinstance(marker, str) or not marker:
        raise GraphStyleError("marker must be a nonempty Matplotlib marker string.")
    try:
        MarkerStyle(marker)
    except Exception as exc:
        raise GraphStyleError(f"Invalid Matplotlib marker {marker!r}.") from exc
    return marker


@dataclass(frozen=True, slots=True)
class ChemicalColorPalette:
    """Named chemical-symbol palette used only for visualization."""

    colors: Mapping[str, ColorLike]
    fallback_color: ColorLike = "#808080"
    name: str = "mdstats-default"

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise GraphStyleError("Palette name must be a nonempty string.")
        normalized: dict[str, ColorLike] = {}
        for symbol, color in dict(self.colors).items():
            if not isinstance(symbol, str) or not symbol:
                raise GraphStyleError("Palette symbols must be nonempty strings.")
            normalized[symbol] = _validate_color(color, name=f"color[{symbol!r}]")
        object.__setattr__(self, "colors", MappingProxyType(normalized))
        object.__setattr__(
            self,
            "fallback_color",
            _validate_color(self.fallback_color, name="fallback_color"),
        )

    @classmethod
    def default(cls) -> "ChemicalColorPalette":
        # Familiar atomistic conventions, chosen for visual distinction in 2-D.
        return cls(
            {
                "H": "#FFFFFF",
                "C": "#404040",
                "N": "#4B3FBA",
                "O": "#E53935",
                "F": "#90E050",
                "Si": "#2D67C7",
                "Al": "#32C7D9",
                "P": "#F28E2B",
                "S": "#F2D13D",
                "Cl": "#2CA02C",
                "Li": "#C7A6FF",
                "Na": "#8F63D8",
                "K": "#5A2D91",
            }
        )

    @classmethod
    def monochrome(cls) -> "ChemicalColorPalette":
        return cls({}, fallback_color="#707070", name="mdstats-monochrome")

    def with_overrides(
        self, overrides: Mapping[str, ColorLike]
    ) -> "ChemicalColorPalette":
        merged = dict(self.colors)
        merged.update(dict(overrides))
        return ChemicalColorPalette(
            merged,
            fallback_color=self.fallback_color,
            name=f"{self.name}+overrides",
        )

    def color_for(self, symbol: str) -> ColorLike:
        return self.colors.get(symbol, self.fallback_color)


@dataclass(frozen=True, slots=True)
class NodeStyle:
    face_color: ColorLike = "#808080"
    size: float = 36.0
    marker: str = "o"
    alpha: float = 1.0
    edge_color: ColorLike = "#202020"
    edge_width: float = 0.75
    zorder: float = 3.0

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "face_color", _validate_color(self.face_color, name="face_color")
        )
        object.__setattr__(
            self, "edge_color", _validate_color(self.edge_color, name="edge_color")
        )
        object.__setattr__(self, "size", _finite_nonnegative(self.size, name="size"))
        object.__setattr__(self, "marker", _validate_marker(self.marker))
        object.__setattr__(self, "alpha", _validate_alpha(self.alpha))
        object.__setattr__(
            self, "edge_width", _finite_nonnegative(self.edge_width, name="edge_width")
        )
        zorder = float(self.zorder)
        if not np.isfinite(zorder):
            raise GraphStyleError("zorder must be finite.")
        object.__setattr__(self, "zorder", zorder)


@dataclass(frozen=True, slots=True)
class NodeStylePatch:
    face_color: ColorLike | None = None
    size: float | None = None
    marker: str | None = None
    alpha: float | None = None
    edge_color: ColorLike | None = None
    edge_width: float | None = None
    zorder: float | None = None

    def __post_init__(self) -> None:
        if self.face_color is not None:
            _validate_color(self.face_color, name="face_color")
        if self.edge_color is not None:
            _validate_color(self.edge_color, name="edge_color")
        if self.size is not None:
            _finite_nonnegative(self.size, name="size")
        if self.marker is not None:
            _validate_marker(self.marker)
        if self.alpha is not None:
            _validate_alpha(self.alpha)
        if self.edge_width is not None:
            _finite_nonnegative(self.edge_width, name="edge_width")
        if self.zorder is not None and not np.isfinite(float(self.zorder)):
            raise GraphStyleError("zorder must be finite.")

    def apply(self, style: NodeStyle) -> NodeStyle:
        values = {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if getattr(self, item.name) is not None
        }
        return replace(style, **values)


@dataclass(frozen=True, slots=True)
class EdgeStyle:
    color: ColorLike = "#707070"
    width: float = 1.2
    alpha: float = 0.65
    line_style: Literal["solid", "dashed", "dotted", "dashdot"] = "solid"
    color_mode: Literal[
        "constant",
        "source",
        "target",
        "midpoint_split",
        "segmented_gradient",
    ] = "constant"
    gradient_segments: int = 8
    zorder: float = 1.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "color", _validate_color(self.color, name="color"))
        object.__setattr__(self, "width", _finite_nonnegative(self.width, name="width"))
        object.__setattr__(self, "alpha", _validate_alpha(self.alpha))
        if self.line_style not in {"solid", "dashed", "dotted", "dashdot"}:
            raise GraphStyleError("Invalid edge line_style.")
        if self.color_mode not in {
            "constant",
            "source",
            "target",
            "midpoint_split",
            "segmented_gradient",
        }:
            raise GraphStyleError("Invalid edge color_mode.")
        if isinstance(self.gradient_segments, bool) or not isinstance(
            self.gradient_segments, (int, np.integer)
        ):
            raise GraphStyleError("gradient_segments must be an integer.")
        segments = int(self.gradient_segments)
        if segments < 2:
            raise GraphStyleError("gradient_segments must be at least 2.")
        object.__setattr__(self, "gradient_segments", segments)
        zorder = float(self.zorder)
        if not np.isfinite(zorder):
            raise GraphStyleError("zorder must be finite.")
        object.__setattr__(self, "zorder", zorder)


@dataclass(frozen=True, slots=True)
class EdgeStylePatch:
    color: ColorLike | None = None
    width: float | None = None
    alpha: float | None = None
    line_style: Literal["solid", "dashed", "dotted", "dashdot"] | None = None
    color_mode: (
        Literal[
            "constant",
            "source",
            "target",
            "midpoint_split",
            "segmented_gradient",
        ]
        | None
    ) = None
    gradient_segments: int | None = None
    zorder: float | None = None

    def __post_init__(self) -> None:
        if self.color is not None:
            _validate_color(self.color, name="color")
        if self.width is not None:
            _finite_nonnegative(self.width, name="width")
        if self.alpha is not None:
            _validate_alpha(self.alpha)
        if self.line_style is not None and self.line_style not in {
            "solid",
            "dashed",
            "dotted",
            "dashdot",
        }:
            raise GraphStyleError("Invalid edge line_style.")
        if self.color_mode is not None and self.color_mode not in {
            "constant",
            "source",
            "target",
            "midpoint_split",
            "segmented_gradient",
        }:
            raise GraphStyleError("Invalid edge color_mode.")
        if self.gradient_segments is not None:
            if (
                isinstance(self.gradient_segments, bool)
                or not isinstance(self.gradient_segments, (int, np.integer))
                or int(self.gradient_segments) < 2
            ):
                raise GraphStyleError("gradient_segments must be an integer >= 2.")
        if self.zorder is not None and not np.isfinite(float(self.zorder)):
            raise GraphStyleError("zorder must be finite.")

    def apply(self, style: EdgeStyle) -> EdgeStyle:
        values = {
            item.name: getattr(self, item.name)
            for item in fields(self)
            if getattr(self, item.name) is not None
        }
        return replace(style, **values)


@dataclass(frozen=True, slots=True)
class NodeStyleRule:
    attribute: str
    values: tuple[AttributeScalar, ...]
    patch: NodeStylePatch
    priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.attribute, str) or not self.attribute:
            raise GraphStyleError("Node style rule attribute must be nonempty.")
        if not self.values:
            raise GraphStyleError("Node style rule values cannot be empty.")
        object.__setattr__(self, "values", tuple(self.values))
        object.__setattr__(self, "priority", int(self.priority))


@dataclass(frozen=True, slots=True)
class EdgeStyleRule:
    attribute: str
    values: tuple[AttributeScalar, ...]
    patch: EdgeStylePatch
    priority: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.attribute, str) or not self.attribute:
            raise GraphStyleError("Edge style rule attribute must be nonempty.")
        if not self.values:
            raise GraphStyleError("Edge style rule values cannot be empty.")
        object.__setattr__(self, "values", tuple(self.values))
        object.__setattr__(self, "priority", int(self.priority))


@dataclass(frozen=True, slots=True)
class GraphLabelOptions:
    node_attribute: str | None = None
    edge_attribute: str | None = None
    node_keys: tuple[Any, ...] | None = None
    edge_keys: tuple[Any, ...] | None = None
    font_size: float = 8.0
    node_offset_points: tuple[float, float] = (3.0, 3.0)

    def __post_init__(self) -> None:
        for name in ("node_attribute", "edge_attribute"):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, str) or not value):
                raise GraphStyleError(f"{name} must be None or a nonempty string.")
        object.__setattr__(
            self, "node_keys", None if self.node_keys is None else tuple(self.node_keys)
        )
        object.__setattr__(
            self, "edge_keys", None if self.edge_keys is None else tuple(self.edge_keys)
        )
        font_size = _finite_nonnegative(self.font_size, name="font_size")
        if font_size == 0.0:
            raise GraphStyleError("font_size must be positive.")
        object.__setattr__(self, "font_size", font_size)
        if len(self.node_offset_points) != 2 or any(
            not np.isfinite(float(x)) for x in self.node_offset_points
        ):
            raise GraphStyleError("node_offset_points must contain two finite values.")
        object.__setattr__(
            self, "node_offset_points", tuple(float(x) for x in self.node_offset_points)
        )


class NodeDisplayMode(str, Enum):
    """Global node-marker presentation mode shared by all renderers."""

    MARKERS = "markers"
    DOTS = "dots"
    HIDDEN = "hidden"


def _coerce_node_display_mode(value: NodeDisplayMode | str) -> NodeDisplayMode:
    if isinstance(value, NodeDisplayMode):
        return value
    try:
        return NodeDisplayMode(str(value))
    except ValueError as exc:
        raise GraphStyleError(
            "node_display_mode must be 'markers', 'dots', or 'hidden'."
        ) from exc


@dataclass(frozen=True, slots=True)
class GraphStyle:
    node_default: NodeStyle = field(default_factory=NodeStyle)
    edge_default: EdgeStyle = field(default_factory=EdgeStyle)
    node_rules: tuple[NodeStyleRule, ...] = ()
    edge_rules: tuple[EdgeStyleRule, ...] = ()
    labels: GraphLabelOptions = field(default_factory=GraphLabelOptions)
    palette: ChemicalColorPalette = field(default_factory=ChemicalColorPalette.default)
    background_color: ColorLike = "white"
    legend: Literal["auto", "none", "all"] = "auto"
    node_display_mode: NodeDisplayMode | str = NodeDisplayMode.MARKERS
    node_dot_size: float = 16.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_rules", tuple(self.node_rules))
        object.__setattr__(self, "edge_rules", tuple(self.edge_rules))
        object.__setattr__(
            self,
            "background_color",
            _validate_color(self.background_color, name="background_color"),
        )
        if self.legend not in {"auto", "none", "all"}:
            raise GraphStyleError("legend must be 'auto', 'none', or 'all'.")
        object.__setattr__(
            self, "node_display_mode", _coerce_node_display_mode(self.node_display_mode)
        )
        dot_size = _finite_nonnegative(self.node_dot_size, name="node_dot_size")
        if dot_size == 0.0:
            raise GraphStyleError("node_dot_size must be positive.")
        object.__setattr__(self, "node_dot_size", dot_size)

    @classmethod
    def default(cls) -> "GraphStyle":
        return cls()

    @classmethod
    def atomic_default(
        cls, palette: ChemicalColorPalette | None = None
    ) -> "GraphStyle":
        palette = palette or ChemicalColorPalette.default()
        rules = tuple(
            NodeStyleRule(
                attribute="symbol",
                values=(symbol,),
                patch=NodeStylePatch(face_color=color),
            )
            for symbol, color in palette.colors.items()
        )
        return cls(
            node_default=NodeStyle(
                face_color=palette.fallback_color,
                size=44.0,
                edge_color="#202020",
                edge_width=0.75,
            ),
            edge_default=EdgeStyle(
                color="#909090",
                width=1.45,
                alpha=0.72,
                color_mode="midpoint_split",
            ),
            node_rules=rules,
            palette=palette,
            legend="auto",
        )

    @classmethod
    def framework_default(
        cls,
        palette: ChemicalColorPalette | None = None,
        *,
        diagnostic: bool = False,
        node_display_mode: NodeDisplayMode | str = NodeDisplayMode.MARKERS,
        node_dot_size: float = 16.0,
    ) -> "GraphStyle":
        """Return a framework-aware projected or atomic-path diagnostic style."""
        palette = palette or ChemicalColorPalette.default()
        species_rules = tuple(
            NodeStyleRule(
                attribute="symbol",
                values=(symbol,),
                patch=NodeStylePatch(face_color=color),
            )
            for symbol, color in palette.colors.items()
        )
        if diagnostic:
            return cls(
                node_default=NodeStyle(
                    face_color=palette.fallback_color,
                    size=44.0,
                    edge_color="#202020",
                    edge_width=0.75,
                ),
                edge_default=EdgeStyle(
                    color="#8A8A8A",
                    width=1.25,
                    alpha=0.72,
                    color_mode="midpoint_split",
                ),
                node_rules=(
                    *species_rules,
                    NodeStyleRule(
                        attribute="framework_role",
                        values=("linker",),
                        patch=NodeStylePatch(size=25.0, edge_width=0.45),
                        priority=10,
                    ),
                ),
                palette=palette,
                legend="auto",
                node_display_mode=node_display_mode,
                node_dot_size=node_dot_size,
            )
        return cls(
            node_default=NodeStyle(
                face_color=palette.fallback_color,
                size=48.0,
                edge_color="#202020",
                edge_width=0.8,
            ),
            edge_default=EdgeStyle(
                color="#777777",
                width=1.65,
                alpha=0.82,
                color_mode="constant",
            ),
            node_rules=species_rules,
            edge_rules=(
                EdgeStyleRule(
                    attribute="edge_kind",
                    values=("direct",),
                    patch=EdgeStylePatch(color="#303030", width=1.55),
                ),
                EdgeStyleRule(
                    attribute="edge_kind",
                    values=("oxygen_bridge", "O_bridge", "single_O_bridge"),
                    patch=EdgeStylePatch(color="#D94B45", width=1.75),
                    priority=5,
                ),
                EdgeStyleRule(
                    attribute="edge_kind",
                    values=("sulfur_bridge", "S_bridge", "single_S_bridge"),
                    patch=EdgeStylePatch(color="#D6A900", width=1.75),
                    priority=5,
                ),
                EdgeStyleRule(
                    attribute="edge_kind",
                    values=("oxygen_oxygen_bridge", "O_O_bridge"),
                    patch=EdgeStylePatch(
                        color="#D94B45", width=1.65, line_style="dashed"
                    ),
                    priority=5,
                ),
                EdgeStyleRule(
                    attribute="edge_kind",
                    values=("sulfur_sulfur_bridge", "S_S_bridge"),
                    patch=EdgeStylePatch(
                        color="#D6A900", width=1.65, line_style="dashed"
                    ),
                    priority=5,
                ),
            ),
            palette=palette,
            legend="auto",
            node_display_mode=node_display_mode,
            node_dot_size=node_dot_size,
        )

    @classmethod
    def transition_default(
        cls, palette: ChemicalColorPalette | None = None
    ) -> "GraphStyle":
        base = cls.atomic_default(palette)
        return cls(
            node_default=base.node_default,
            edge_default=EdgeStyle(
                color="#B5B5B5", width=1.0, alpha=0.40, color_mode="constant"
            ),
            node_rules=(
                *base.node_rules,
                NodeStyleRule(
                    attribute="affected",
                    values=(True,),
                    patch=NodeStylePatch(
                        size=68.0, edge_color="#111111", edge_width=2.0
                    ),
                    priority=10,
                ),
            ),
            edge_rules=(
                EdgeStyleRule(
                    attribute="transition_status",
                    values=("unchanged",),
                    patch=EdgeStylePatch(color="#B5B5B5", width=1.0, alpha=0.40),
                ),
                EdgeStyleRule(
                    attribute="transition_status",
                    values=("removed",),
                    patch=EdgeStylePatch(
                        color="#D62728", width=2.5, alpha=0.95, line_style="dashed"
                    ),
                    priority=10,
                ),
                EdgeStyleRule(
                    attribute="transition_status",
                    values=("added",),
                    patch=EdgeStylePatch(
                        color="#2CA02C", width=2.5, alpha=0.95, line_style="solid"
                    ),
                    priority=10,
                ),
            ),
            palette=base.palette,
            legend="auto",
        )

    @classmethod
    def publication(cls) -> "GraphStyle":
        return cls(
            node_default=NodeStyle(size=32.0, edge_width=0.6),
            edge_default=EdgeStyle(width=1.0, alpha=0.65),
            legend="auto",
        )


def _node_styles_for_display(
    style: GraphStyle, resolved: tuple[NodeStyle, ...]
) -> tuple[NodeStyle, ...]:
    """Return renderer-facing node styles without changing scientific selection."""
    if style.node_display_mode is NodeDisplayMode.MARKERS:
        return resolved
    if style.node_display_mode is NodeDisplayMode.HIDDEN:
        return resolved
    return tuple(
        replace(
            item,
            size=style.node_dot_size,
            marker="o",
            edge_color=item.face_color,
            edge_width=0.0,
        )
        for item in resolved
    )


def validate_style_for_view(style: GraphStyle, view: PreparedGraphView) -> None:
    for rule in style.node_rules:
        if rule.attribute not in view.node_attributes:
            raise GraphStyleError(
                f"Node style rule references missing attribute {rule.attribute!r}."
            )
    for rule in style.edge_rules:
        if rule.attribute not in view.edge_attributes:
            raise GraphStyleError(
                f"Edge style rule references missing attribute {rule.attribute!r}."
            )
    labels = style.labels
    if (
        labels.node_attribute is not None
        and labels.node_attribute not in view.node_attributes
    ):
        raise GraphStyleError(
            f"Node labels reference missing attribute {labels.node_attribute!r}."
        )
    if (
        labels.edge_attribute is not None
        and labels.edge_attribute not in view.edge_attributes
    ):
        raise GraphStyleError(
            f"Edge labels reference missing attribute {labels.edge_attribute!r}."
        )


def resolve_node_styles(
    style: GraphStyle, view: PreparedGraphView
) -> tuple[NodeStyle, ...]:
    validate_style_for_view(style, view)
    ordered = sorted(
        enumerate(style.node_rules), key=lambda item: (item[1].priority, item[0])
    )
    resolved: list[NodeStyle] = []
    attrs = view.node_attributes
    for position in range(len(view.node_source_positions)):
        current = style.node_default
        for _, rule in ordered:
            if _column_value(attrs[rule.attribute], position) in rule.values:
                current = rule.patch.apply(current)
        resolved.append(current)
    return tuple(resolved)


def resolve_edge_styles(
    style: GraphStyle, view: PreparedGraphView
) -> tuple[EdgeStyle, ...]:
    validate_style_for_view(style, view)
    ordered = sorted(
        enumerate(style.edge_rules), key=lambda item: (item[1].priority, item[0])
    )
    resolved: list[EdgeStyle] = []
    attrs = view.edge_attributes
    for position in range(len(view.edge_source_positions)):
        current = style.edge_default
        for _, rule in ordered:
            if _column_value(attrs[rule.attribute], position) in rule.values:
                current = rule.patch.apply(current)
        resolved.append(current)
    return tuple(resolved)


__all__ = [
    "ChemicalColorPalette",
    "EdgeStyle",
    "EdgeStylePatch",
    "EdgeStyleRule",
    "GraphLabelOptions",
    "GraphStyle",
    "NodeDisplayMode",
    "NodeStyle",
    "NodeStylePatch",
    "NodeStyleRule",
]
