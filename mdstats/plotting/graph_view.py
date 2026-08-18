"""Renderer-independent decorated graph data and selection contracts.

The public classes in this module describe *what* should be drawn.  They do not
contain Matplotlib artists, layout coordinates, or renderer-specific state.
Scientific graph modules remain authoritative; a :class:`DecoratedGraphView`
is an immutable visualization adapter product.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Hashable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from .graph_errors import GraphFilterError, GraphViewValidationError

GraphKey: TypeAlias = Hashable
AttributeScalar: TypeAlias = None | bool | int | float | str | tuple[Any, ...]
AttributeColumn: TypeAlias = NDArray[Any] | tuple[AttributeScalar, ...]

_RESERVED_ATTRIBUTE_PREFIX = "_mdstats_"


def _readonly_array(
    value: Any,
    dtype: Any | None = None,
    *,
    ndim: int | None = None,
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if ndim is not None and array.ndim != ndim:
        raise GraphViewValidationError(
            f"Expected a {ndim}-dimensional array; received shape {array.shape}."
        )
    array.setflags(write=False)
    return array


def _validate_graph_key(key: GraphKey, *, kind: str) -> None:
    try:
        hash(key)
    except Exception as exc:  # pragma: no cover - defensive
        raise GraphViewValidationError(f"{kind} key {key!r} is not hashable.") from exc
    if isinstance(key, float) and np.isnan(key):
        raise GraphViewValidationError(f"{kind} keys cannot contain NaN.")
    if isinstance(key, tuple):
        for item in key:
            _validate_graph_key(item, kind=kind)


def _validate_scalar(value: Any, *, context: str) -> AttributeScalar:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise GraphViewValidationError(f"{context} numeric values must be finite.")
        return number
    if isinstance(value, tuple):
        return tuple(_validate_scalar(item, context=context) for item in value)
    raise GraphViewValidationError(
        f"{context} values must be immutable scalars or tuples; received "
        f"{type(value).__name__}."
    )


def _freeze_metadata(value: Any, *, context: str = "metadata") -> Any:
    """Recursively copy and freeze portable immutable metadata."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not np.isfinite(number):
            raise GraphViewValidationError(f"{context} numeric values must be finite.")
        return number
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True, order="C")
        if np.issubdtype(array.dtype, np.number) and np.any(~np.isfinite(array)):
            raise GraphViewValidationError(f"{context} arrays must be finite.")
        array.setflags(write=False)
        return array
    if isinstance(value, Mapping):
        frozen: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise GraphViewValidationError(
                    f"{context} mapping keys must be nonempty strings."
                )
            frozen[key] = _freeze_metadata(item, context=f"{context}.{key}")
        return MappingProxyType(frozen)
    if isinstance(value, (tuple, list)):
        return tuple(_freeze_metadata(item, context=context) for item in value)
    if isinstance(value, frozenset):
        return frozenset(_freeze_metadata(item, context=context) for item in value)
    # Stable scientific keys such as AtomicEdgeKey are immutable dataclasses.
    if (
        hasattr(value, "__dataclass_fields__")
        and getattr(type(value), "__hash__", None) is not None
    ):
        return value
    raise GraphViewValidationError(
        f"{context} contains unsupported mutable or nonportable value "
        f"{type(value).__name__}."
    )


def _normalize_attribute_column(
    value: AttributeColumn | Sequence[Any],
    *,
    expected_length: int,
    name: str,
    kind: str,
) -> AttributeColumn:
    context = f"{kind} attribute {name!r}"
    if isinstance(value, np.ndarray):
        array = np.array(value, copy=True, order="C")
        if array.ndim != 1 or array.shape[0] != expected_length:
            raise GraphViewValidationError(
                f"{context} must be one-dimensional with length {expected_length}."
            )
        if np.issubdtype(array.dtype, np.number):
            if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
                raise GraphViewValidationError(
                    f"{context} must not contain NaN or infinity."
                )
        elif array.dtype == object:
            normalized = tuple(
                _validate_scalar(item, context=context) for item in array.tolist()
            )
            return normalized
        array.setflags(write=False)
        return array
    values = tuple(value)
    if len(values) != expected_length:
        raise GraphViewValidationError(
            f"{context} must have length {expected_length}; received {len(values)}."
        )
    return tuple(_validate_scalar(item, context=context) for item in values)


def _column_value(column: AttributeColumn, position: int) -> AttributeScalar:
    value = column[position]
    if isinstance(value, np.generic):
        return value.item()
    return value


def _serialize_key(key: GraphKey) -> Any:
    if key is None or isinstance(key, (bool, int, float, str)):
        return key
    if isinstance(key, tuple):
        return [_serialize_key(item) for item in key]
    to_dict = getattr(key, "to_dict", None)
    if callable(to_dict):
        return {"type": type(key).__name__, "value": to_dict()}
    return {"type": type(key).__name__, "repr": repr(key)}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    if isinstance(value, np.generic):
        return value.item()
    return value


@dataclass(frozen=True, slots=True)
class DecoratedGraphView:
    """Immutable renderer-independent decorated graph.

    ``edge_endpoints`` stores dense positions into ``node_keys``.  Scientific
    identity remains in the stable node and edge keys.
    """

    node_keys: tuple[GraphKey, ...]
    edge_keys: tuple[GraphKey, ...]
    edge_endpoints: NDArray[np.int64]
    node_positions_3d: NDArray[np.float64] | None = None
    edge_image_shifts: NDArray[np.int64] | None = None
    cell: NDArray[np.float64] | None = None
    pbc: NDArray[np.bool_] | None = None
    node_attributes: Mapping[str, AttributeColumn] = field(default_factory=dict)
    edge_attributes: Mapping[str, AttributeColumn] = field(default_factory=dict)
    directed: bool = False
    multigraph: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        node_keys = tuple(self.node_keys)
        edge_keys = tuple(self.edge_keys)
        for key in node_keys:
            _validate_graph_key(key, kind="Node")
        for key in edge_keys:
            _validate_graph_key(key, kind="Edge")
        if len(set(node_keys)) != len(node_keys):
            raise GraphViewValidationError("node_keys must be unique.")
        if len(set(edge_keys)) != len(edge_keys):
            raise GraphViewValidationError("edge_keys must be unique.")

        endpoints = _readonly_array(self.edge_endpoints, np.int64, ndim=2)
        if endpoints.shape != (len(edge_keys), 2):
            raise GraphViewValidationError(
                "edge_endpoints must have shape (n_edges, 2)."
            )
        if endpoints.size and (
            np.min(endpoints) < 0 or np.max(endpoints) >= len(node_keys)
        ):
            raise GraphViewValidationError(
                "edge_endpoints contain positions outside node_keys."
            )

        positions = None
        if self.node_positions_3d is not None:
            positions = _readonly_array(self.node_positions_3d, np.float64, ndim=2)
            if positions.shape != (len(node_keys), 3):
                raise GraphViewValidationError(
                    "node_positions_3d must have shape (n_nodes, 3)."
                )
            if np.any(~np.isfinite(positions)):
                raise GraphViewValidationError("node_positions_3d must be finite.")

        shifts = None
        if self.edge_image_shifts is not None:
            shifts = _readonly_array(self.edge_image_shifts, np.int64, ndim=2)
            if shifts.shape != (len(edge_keys), 3):
                raise GraphViewValidationError(
                    "edge_image_shifts must have shape (n_edges, 3)."
                )

        cell = None
        if self.cell is not None:
            cell = _readonly_array(self.cell, np.float64, ndim=2)
            if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
                raise GraphViewValidationError("cell must be a finite 3x3 matrix.")
            if abs(float(np.linalg.det(cell))) <= 1.0e-12:
                raise GraphViewValidationError("cell must be nonsingular.")

        pbc = None
        if self.pbc is not None:
            pbc = _readonly_array(self.pbc, np.bool_, ndim=1)
            if pbc.shape != (3,):
                raise GraphViewValidationError("pbc must have shape (3,).")

        if shifts is not None and np.any(shifts != 0):
            if positions is None or cell is None or pbc is None:
                raise GraphViewValidationError(
                    "Nonzero edge shifts require positions, cell, and PBC flags."
                )
        if shifts is not None and pbc is not None and np.any(shifts[:, ~pbc] != 0):
            raise GraphViewValidationError(
                "Image shifts must be zero along nonperiodic axes."
            )

        seen: set[tuple[int, int]] = set()
        if not self.multigraph:
            for source, target in endpoints:
                pair = (
                    (int(source), int(target))
                    if self.directed
                    else tuple(sorted((int(source), int(target))))
                )
                if pair in seen:
                    raise GraphViewValidationError(
                        "A non-multigraph cannot contain duplicate endpoint pairs."
                    )
                seen.add(pair)

        node_attributes: dict[str, AttributeColumn] = {}
        for name, column in self.node_attributes.items():
            if (
                not isinstance(name, str)
                or not name
                or name.startswith(_RESERVED_ATTRIBUTE_PREFIX)
            ):
                raise GraphViewValidationError(
                    "Node attribute names must be nonempty and must not use the "
                    f"reserved prefix {_RESERVED_ATTRIBUTE_PREFIX!r}."
                )
            node_attributes[name] = _normalize_attribute_column(
                column,
                expected_length=len(node_keys),
                name=name,
                kind="node",
            )
        edge_attributes: dict[str, AttributeColumn] = {}
        for name, column in self.edge_attributes.items():
            if (
                not isinstance(name, str)
                or not name
                or name.startswith(_RESERVED_ATTRIBUTE_PREFIX)
            ):
                raise GraphViewValidationError(
                    "Edge attribute names must be nonempty and must not use the "
                    f"reserved prefix {_RESERVED_ATTRIBUTE_PREFIX!r}."
                )
            edge_attributes[name] = _normalize_attribute_column(
                column,
                expected_length=len(edge_keys),
                name=name,
                kind="edge",
            )

        object.__setattr__(self, "node_keys", node_keys)
        object.__setattr__(self, "edge_keys", edge_keys)
        object.__setattr__(self, "edge_endpoints", endpoints)
        object.__setattr__(self, "node_positions_3d", positions)
        object.__setattr__(self, "edge_image_shifts", shifts)
        object.__setattr__(self, "cell", cell)
        object.__setattr__(self, "pbc", pbc)
        object.__setattr__(self, "node_attributes", MappingProxyType(node_attributes))
        object.__setattr__(self, "edge_attributes", MappingProxyType(edge_attributes))
        object.__setattr__(self, "directed", bool(self.directed))
        object.__setattr__(self, "multigraph", bool(self.multigraph))
        object.__setattr__(self, "metadata", _freeze_metadata(dict(self.metadata)))

    @property
    def n_nodes(self) -> int:
        return len(self.node_keys)

    @property
    def n_edges(self) -> int:
        return len(self.edge_keys)

    def node_position(self, key: GraphKey) -> int:
        try:
            return self.node_keys.index(key)
        except ValueError as exc:
            raise KeyError(f"Unknown node key {key!r}.") from exc

    def edge_position(self, key: GraphKey) -> int:
        try:
            return self.edge_keys.index(key)
        except ValueError as exc:
            raise KeyError(f"Unknown edge key {key!r}.") from exc

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_keys": [_serialize_key(key) for key in self.node_keys],
            "edge_keys": [_serialize_key(key) for key in self.edge_keys],
            "edge_endpoints": self.edge_endpoints.tolist(),
            "node_positions_3d": (
                None
                if self.node_positions_3d is None
                else self.node_positions_3d.tolist()
            ),
            "edge_image_shifts": (
                None
                if self.edge_image_shifts is None
                else self.edge_image_shifts.tolist()
            ),
            "cell": None if self.cell is None else self.cell.tolist(),
            "pbc": None if self.pbc is None else self.pbc.tolist(),
            "node_attributes": {
                name: _serialize_value(column)
                for name, column in self.node_attributes.items()
            },
            "edge_attributes": {
                name: _serialize_value(column)
                for name, column in self.edge_attributes.items()
            },
            "directed": self.directed,
            "multigraph": self.multigraph,
            "metadata": _serialize_value(self.metadata),
        }


@dataclass(frozen=True, slots=True)
class GraphFocus:
    """Node-induced graph neighborhood selected by graph distance."""

    center_node_keys: tuple[GraphKey, ...]
    hop_radius: int = 1
    direction: Literal["both", "out", "in"] = "both"

    def __post_init__(self) -> None:
        centers = tuple(self.center_node_keys)
        if not centers or len(set(centers)) != len(centers):
            raise GraphFilterError("center_node_keys must be nonempty and unique.")
        if isinstance(self.hop_radius, bool) or not isinstance(
            self.hop_radius, (int, np.integer)
        ):
            raise GraphFilterError("hop_radius must be a nonnegative integer.")
        radius = int(self.hop_radius)
        if radius < 0:
            raise GraphFilterError("hop_radius must be nonnegative.")
        if self.direction not in {"both", "out", "in"}:
            raise GraphFilterError("direction must be 'both', 'out', or 'in'.")
        object.__setattr__(self, "center_node_keys", centers)
        object.__setattr__(self, "hop_radius", radius)


@dataclass(frozen=True, slots=True)
class AttributeSelection:
    """Exact categorical inclusion/exclusion rule for one metadata column."""

    attribute: str
    include_values: tuple[AttributeScalar, ...] | None = None
    exclude_values: tuple[AttributeScalar, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.attribute, str) or not self.attribute:
            raise GraphFilterError("attribute must be a nonempty string.")
        include = (
            None
            if self.include_values is None
            else tuple(
                _validate_scalar(value, context="include_values")
                for value in self.include_values
            )
        )
        exclude = tuple(
            _validate_scalar(value, context="exclude_values")
            for value in self.exclude_values
        )
        object.__setattr__(self, "include_values", include)
        object.__setattr__(self, "exclude_values", exclude)


@dataclass(frozen=True, slots=True)
class GraphFilter:
    """Explicit deterministic node and edge filters."""

    include_node_keys: tuple[GraphKey, ...] | None = None
    exclude_node_keys: tuple[GraphKey, ...] = ()
    include_edge_keys: tuple[GraphKey, ...] | None = None
    exclude_edge_keys: tuple[GraphKey, ...] = ()
    node_attribute_selections: tuple[AttributeSelection, ...] = ()
    edge_attribute_selections: tuple[AttributeSelection, ...] = ()
    keep_isolated_nodes: bool = True

    def __post_init__(self) -> None:
        for name in (
            "include_node_keys",
            "exclude_node_keys",
            "include_edge_keys",
            "exclude_edge_keys",
        ):
            value = getattr(self, name)
            normalized = None if value is None else tuple(value)
            if normalized is not None and len(set(normalized)) != len(normalized):
                raise GraphFilterError(f"{name} must not contain duplicates.")
            object.__setattr__(self, name, normalized)
        object.__setattr__(
            self,
            "node_attribute_selections",
            tuple(self.node_attribute_selections),
        )
        object.__setattr__(
            self,
            "edge_attribute_selections",
            tuple(self.edge_attribute_selections),
        )
        object.__setattr__(self, "keep_isolated_nodes", bool(self.keep_isolated_nodes))


@dataclass(frozen=True, slots=True)
class GraphComplexityPolicy:
    """Hard rendering limits; the renderer never silently samples data."""

    max_nodes: int = 1500
    max_edges: int = 3000
    max_labels: int = 100
    max_gradient_segments: int = 20000
    overflow: Literal["error", "require_focus", "warn_and_render"] = "require_focus"

    def __post_init__(self) -> None:
        for name in (
            "max_nodes",
            "max_edges",
            "max_labels",
            "max_gradient_segments",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise GraphViewValidationError(f"{name} must be a positive integer.")
            value = int(value)
            if value <= 0:
                raise GraphViewValidationError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        if self.overflow not in {"error", "require_focus", "warn_and_render"}:
            raise GraphViewValidationError("Invalid complexity overflow policy.")


@dataclass(frozen=True, slots=True)
class GraphComplexityReport:
    input_nodes: int
    input_edges: int
    selected_nodes: int
    selected_edges: int
    requested_labels: int
    estimated_gradient_segments: int
    exceeded_limits: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "input_nodes",
            "input_edges",
            "selected_nodes",
            "selected_edges",
            "requested_labels",
            "estimated_gradient_segments",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphViewValidationError(f"{name} cannot be negative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "exceeded_limits", tuple(self.exceeded_limits))


@dataclass(frozen=True, slots=True)
class PreparedGraphView:
    """Private display selection preserving source positions and provenance."""

    source_view: DecoratedGraphView
    node_source_positions: NDArray[np.int64]
    edge_source_positions: NDArray[np.int64]
    edge_endpoints: NDArray[np.int64]
    node_positions_3d: NDArray[np.float64] | None
    edge_image_shifts: NDArray[np.int64] | None
    selection_metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "node_source_positions",
            _readonly_array(self.node_source_positions, np.int64, ndim=1),
        )
        object.__setattr__(
            self,
            "edge_source_positions",
            _readonly_array(self.edge_source_positions, np.int64, ndim=1),
        )
        object.__setattr__(
            self,
            "edge_endpoints",
            _readonly_array(self.edge_endpoints, np.int64, ndim=2),
        )
        if self.node_positions_3d is not None:
            object.__setattr__(
                self,
                "node_positions_3d",
                _readonly_array(self.node_positions_3d, np.float64, ndim=2),
            )
        if self.edge_image_shifts is not None:
            object.__setattr__(
                self,
                "edge_image_shifts",
                _readonly_array(self.edge_image_shifts, np.int64, ndim=2),
            )
        object.__setattr__(
            self, "selection_metadata", _freeze_metadata(dict(self.selection_metadata))
        )

    @property
    def node_keys(self) -> tuple[GraphKey, ...]:
        return tuple(
            self.source_view.node_keys[int(i)] for i in self.node_source_positions
        )

    @property
    def edge_keys(self) -> tuple[GraphKey, ...]:
        return tuple(
            self.source_view.edge_keys[int(i)] for i in self.edge_source_positions
        )

    @property
    def node_attributes(self) -> Mapping[str, AttributeColumn]:
        result: dict[str, AttributeColumn] = {}
        for name, column in self.source_view.node_attributes.items():
            if isinstance(column, np.ndarray):
                values = np.array(column[self.node_source_positions], copy=True)
                values.setflags(write=False)
                result[name] = values
            else:
                result[name] = tuple(column[int(i)] for i in self.node_source_positions)
        return MappingProxyType(result)

    @property
    def edge_attributes(self) -> Mapping[str, AttributeColumn]:
        result: dict[str, AttributeColumn] = {}
        for name, column in self.source_view.edge_attributes.items():
            if isinstance(column, np.ndarray):
                values = np.array(column[self.edge_source_positions], copy=True)
                values.setflags(write=False)
                result[name] = values
            else:
                result[name] = tuple(column[int(i)] for i in self.edge_source_positions)
        return MappingProxyType(result)


def _focus_node_positions(
    view: DecoratedGraphView, focus: GraphFocus | None
) -> set[int]:
    if focus is None:
        return set(range(view.n_nodes))
    key_to_position = {key: i for i, key in enumerate(view.node_keys)}
    unknown = [key for key in focus.center_node_keys if key not in key_to_position]
    if unknown:
        raise GraphFilterError(f"Unknown focus node keys: {unknown!r}.")
    centers = [key_to_position[key] for key in focus.center_node_keys]
    out_adj: list[list[int]] = [[] for _ in range(view.n_nodes)]
    in_adj: list[list[int]] = [[] for _ in range(view.n_nodes)]
    for source, target in view.edge_endpoints:
        s, t = int(source), int(target)
        out_adj[s].append(t)
        in_adj[t].append(s)
        if not view.directed:
            out_adj[t].append(s)
            in_adj[s].append(t)
    selected = set(centers)
    queue = deque((node, 0) for node in centers)
    while queue:
        node, depth = queue.popleft()
        if depth >= focus.hop_radius:
            continue
        if not view.directed or focus.direction == "both":
            neighbors = set(out_adj[node]) | set(in_adj[node])
        elif focus.direction == "out":
            neighbors = set(out_adj[node])
        else:
            neighbors = set(in_adj[node])
        for neighbor in sorted(neighbors):
            if neighbor not in selected:
                selected.add(neighbor)
                queue.append((neighbor, depth + 1))
    return selected


def _selection_mask(
    columns: Mapping[str, AttributeColumn],
    selections: tuple[AttributeSelection, ...],
    size: int,
    *,
    kind: str,
) -> NDArray[np.bool_]:
    mask = np.ones(size, dtype=bool)
    for selection in selections:
        if selection.attribute not in columns:
            raise GraphFilterError(f"Unknown {kind} attribute {selection.attribute!r}.")
        column = columns[selection.attribute]
        include = (
            None if selection.include_values is None else set(selection.include_values)
        )
        exclude = set(selection.exclude_values)
        local = np.ones(size, dtype=bool)
        for index in range(size):
            value = _column_value(column, index)
            if include is not None:
                local[index] = value in include
            if value in exclude:
                local[index] = False
        mask &= local
    return mask


def prepare_graph_view(
    view: DecoratedGraphView,
    *,
    focus: GraphFocus | None,
    graph_filter: GraphFilter | None,
) -> PreparedGraphView:
    """Apply focus and deterministic filters without mutating the source view."""
    selected_nodes = _focus_node_positions(view, focus)
    graph_filter = graph_filter or GraphFilter()
    node_key_to_pos = {key: i for i, key in enumerate(view.node_keys)}
    edge_key_to_pos = {key: i for i, key in enumerate(view.edge_keys)}

    def resolve_keys(
        keys: tuple[GraphKey, ...] | None, mapping: Mapping[GraphKey, int], kind: str
    ):
        if keys is None:
            return None
        unknown = [key for key in keys if key not in mapping]
        if unknown:
            raise GraphFilterError(f"Unknown {kind} keys: {unknown!r}.")
        return {mapping[key] for key in keys}

    include_nodes = resolve_keys(
        graph_filter.include_node_keys, node_key_to_pos, "node"
    )
    exclude_nodes = (
        resolve_keys(graph_filter.exclude_node_keys, node_key_to_pos, "node") or set()
    )
    if include_nodes is not None:
        selected_nodes &= include_nodes
    selected_nodes -= exclude_nodes

    node_attr_mask = _selection_mask(
        view.node_attributes,
        graph_filter.node_attribute_selections,
        view.n_nodes,
        kind="node",
    )
    selected_nodes &= set(np.flatnonzero(node_attr_mask).tolist())

    selected_edges = {
        edge_position
        for edge_position, (source, target) in enumerate(view.edge_endpoints)
        if int(source) in selected_nodes and int(target) in selected_nodes
    }
    include_edges = resolve_keys(
        graph_filter.include_edge_keys, edge_key_to_pos, "edge"
    )
    exclude_edges = (
        resolve_keys(graph_filter.exclude_edge_keys, edge_key_to_pos, "edge") or set()
    )
    if include_edges is not None:
        selected_edges &= include_edges
    selected_edges -= exclude_edges
    edge_attr_mask = _selection_mask(
        view.edge_attributes,
        graph_filter.edge_attribute_selections,
        view.n_edges,
        kind="edge",
    )
    selected_edges &= set(np.flatnonzero(edge_attr_mask).tolist())

    if not graph_filter.keep_isolated_nodes:
        incident: set[int] = set()
        for edge_position in selected_edges:
            source, target = view.edge_endpoints[edge_position]
            incident.update((int(source), int(target)))
        selected_nodes &= incident
        selected_edges = {
            edge_position
            for edge_position in selected_edges
            if int(view.edge_endpoints[edge_position, 0]) in selected_nodes
            and int(view.edge_endpoints[edge_position, 1]) in selected_nodes
        }

    node_positions = np.asarray(sorted(selected_nodes), dtype=np.int64)
    edge_positions = np.asarray(sorted(selected_edges), dtype=np.int64)
    reindex = {int(source): target for target, source in enumerate(node_positions)}
    endpoints = np.empty((edge_positions.size, 2), dtype=np.int64)
    for local_edge, source_edge in enumerate(edge_positions):
        source, target = view.edge_endpoints[int(source_edge)]
        endpoints[local_edge] = (reindex[int(source)], reindex[int(target)])

    positions = (
        None
        if view.node_positions_3d is None
        else np.asarray(view.node_positions_3d[node_positions], dtype=float)
    )
    shifts = (
        None
        if view.edge_image_shifts is None
        else np.asarray(view.edge_image_shifts[edge_positions], dtype=np.int64)
    )
    metadata = {
        "input_nodes": view.n_nodes,
        "input_edges": view.n_edges,
        "selected_nodes": int(node_positions.size),
        "selected_edges": int(edge_positions.size),
        "omitted_node_keys": tuple(
            view.node_keys[i] for i in range(view.n_nodes) if i not in selected_nodes
        ),
        "omitted_edge_keys": tuple(
            view.edge_keys[i] for i in range(view.n_edges) if i not in selected_edges
        ),
        "focus": None
        if focus is None
        else {
            "center_node_keys": focus.center_node_keys,
            "hop_radius": focus.hop_radius,
            "direction": focus.direction,
        },
        "filter_applied": graph_filter != GraphFilter(),
    }
    return PreparedGraphView(
        source_view=view,
        node_source_positions=node_positions,
        edge_source_positions=edge_positions,
        edge_endpoints=endpoints,
        node_positions_3d=positions,
        edge_image_shifts=shifts,
        selection_metadata=metadata,
    )


__all__ = [
    "AttributeColumn",
    "AttributeScalar",
    "AttributeSelection",
    "DecoratedGraphView",
    "GraphComplexityPolicy",
    "GraphComplexityReport",
    "GraphFilter",
    "GraphFocus",
    "GraphKey",
]
