"""Renderer-independent materialization of periodic decorated graphs.

This module converts a compact quotient graph into an explicit display graph.
Replicas and ghost endpoints are presentation objects only: stable scientific
identity remains with the source :class:`~mdstats.plotting.DecoratedGraphView`.
"""

from __future__ import annotations

from collections import Counter, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
from itertools import product
from typing import Any, Literal, TypeAlias

import numpy as np
from numpy.typing import NDArray

from .graph_errors import (
    GraphComplexityError,
    GraphFilterError,
    GraphUnsupportedFeatureError,
    GraphViewValidationError,
)
from .graph_view import (
    AttributeColumn,
    DecoratedGraphView,
    GraphComplexityPolicy,
    GraphFilter,
    GraphFocus,
    GraphKey,
    PreparedGraphView,
    _freeze_metadata,
    prepare_graph_view,
)

PERIODIC_GRAPH_DISPLAY_SCHEMA = "mdstats.periodic-graph-display.v1"
ImageShift: TypeAlias = tuple[int, int, int]


class PeriodicDisplayMode(Enum):
    """Supported explicit materializations of a periodic quotient graph."""

    CANONICAL_CELL = "canonical_cell"
    LOCAL_UNWRAPPED = "local_unwrapped"
    EXPANDED = "expanded"


class PeriodicNodeRole(Enum):
    """Presentation role of a materialized node image."""

    CANONICAL = "canonical"
    REPLICA = "replica"
    GHOST = "ghost"


class PeriodicEdgeRole(Enum):
    """Presentation role of a materialized edge image."""

    PRIMARY = "primary"
    REPLICA = "replica"
    BOUNDARY_GHOST = "boundary_ghost"
    CYCLE_GHOST = "cycle_ghost"


def _shift_tuple(value: Sequence[int], *, name: str) -> ImageShift:
    try:
        items = tuple(value)
    except TypeError as exc:  # pragma: no cover - defensive
        raise GraphViewValidationError(f"{name} must contain three integers.") from exc
    if len(items) != 3 or any(
        isinstance(item, bool) or not isinstance(item, (int, np.integer))
        for item in items
    ):
        raise GraphViewValidationError(f"{name} must contain exactly three integers.")
    return tuple(int(item) for item in items)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class PeriodicNodeKey:
    """Stable display identity of one periodic image of a source node."""

    source_node_key: GraphKey
    image_shift: ImageShift

    def __post_init__(self) -> None:
        try:
            hash(self.source_node_key)
        except Exception as exc:  # pragma: no cover - defensive
            raise GraphViewValidationError("source_node_key must be hashable.") from exc
        object.__setattr__(
            self,
            "image_shift",
            _shift_tuple(self.image_shift, name="image_shift"),
        )


@dataclass(frozen=True, slots=True)
class PeriodicEdgeKey:
    """Stable display identity of one explicit image of a source edge."""

    source_edge_key: GraphKey
    source_image_shift: ImageShift
    target_image_shift: ImageShift

    def __post_init__(self) -> None:
        try:
            hash(self.source_edge_key)
        except Exception as exc:  # pragma: no cover - defensive
            raise GraphViewValidationError("source_edge_key must be hashable.") from exc
        object.__setattr__(
            self,
            "source_image_shift",
            _shift_tuple(self.source_image_shift, name="source_image_shift"),
        )
        object.__setattr__(
            self,
            "target_image_shift",
            _shift_tuple(self.target_image_shift, name="target_image_shift"),
        )


@dataclass(frozen=True, slots=True)
class CanonicalCellDisplay:
    """Display one canonical source-cell population plus boundary ghosts."""

    mode: PeriodicDisplayMode = field(
        default=PeriodicDisplayMode.CANONICAL_CELL,
        init=False,
    )


@dataclass(frozen=True, slots=True)
class LocalUnwrappedDisplay:
    """Display one deterministic unwrapped neighborhood around a source node."""

    center_node_key: GraphKey
    hop_radius: int | None = None
    direction: Literal["both", "out", "in"] = "both"
    mode: PeriodicDisplayMode = field(
        default=PeriodicDisplayMode.LOCAL_UNWRAPPED,
        init=False,
    )

    def __post_init__(self) -> None:
        try:
            hash(self.center_node_key)
        except Exception as exc:  # pragma: no cover - defensive
            raise GraphFilterError("center_node_key must be hashable.") from exc
        if self.hop_radius is not None:
            if isinstance(self.hop_radius, bool) or not isinstance(
                self.hop_radius, (int, np.integer)
            ):
                raise GraphFilterError(
                    "hop_radius must be None or a nonnegative integer."
                )
            radius = int(self.hop_radius)
            if radius < 0:
                raise GraphFilterError("hop_radius must be nonnegative.")
            object.__setattr__(self, "hop_radius", radius)
        if self.direction not in {"both", "out", "in"}:
            raise GraphFilterError("direction must be 'both', 'out', or 'in'.")


@dataclass(frozen=True, slots=True)
class ExpandedCellDisplay:
    """Display a rectangular inclusive range of primary lattice images."""

    image_ranges: tuple[
        tuple[int, int],
        tuple[int, int],
        tuple[int, int],
    ] = ((0, 0), (0, 0), (0, 0))
    mode: PeriodicDisplayMode = field(
        default=PeriodicDisplayMode.EXPANDED,
        init=False,
    )

    def __post_init__(self) -> None:
        ranges = tuple(tuple(item) for item in self.image_ranges)
        if len(ranges) != 3:
            raise GraphViewValidationError("image_ranges must contain three intervals.")
        normalized: list[tuple[int, int]] = []
        for axis, interval in enumerate(ranges):
            if len(interval) != 2 or any(
                isinstance(value, bool) or not isinstance(value, (int, np.integer))
                for value in interval
            ):
                raise GraphViewValidationError(
                    f"image_ranges[{axis}] must contain two integers."
                )
            lower, upper = int(interval[0]), int(interval[1])
            if lower > upper:
                raise GraphViewValidationError(
                    f"image_ranges[{axis}] must satisfy lower <= upper."
                )
            normalized.append((lower, upper))
        object.__setattr__(self, "image_ranges", tuple(normalized))


PeriodicDisplayOptions: TypeAlias = (
    CanonicalCellDisplay | LocalUnwrappedDisplay | ExpandedCellDisplay
)


def _readonly_array(
    value: Any, dtype: Any, *, shape_tail: tuple[int, ...] = ()
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if shape_tail and array.shape[-len(shape_tail) :] != shape_tail:
        raise GraphViewValidationError(
            f"Array must end with shape {shape_tail}; received {array.shape}."
        )
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class PeriodicGraphView:
    """Explicit periodic display graph plus complete source/display mappings."""

    source_view: DecoratedGraphView
    graph: DecoratedGraphView
    mode: PeriodicDisplayMode
    source_node_positions: NDArray[np.int64]
    source_edge_positions: NDArray[np.int64]
    node_image_shifts: NDArray[np.int64]
    node_roles: tuple[PeriodicNodeRole, ...]
    edge_roles: tuple[PeriodicEdgeRole, ...]
    primary_cell_image_shifts: NDArray[np.int64]
    selection_metadata: Mapping[str, Any]
    periodic_metadata: Mapping[str, Any]
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        n_nodes, n_edges = self.graph.n_nodes, self.graph.n_edges
        source_nodes = _readonly_array(self.source_node_positions, np.int64)
        source_edges = _readonly_array(self.source_edge_positions, np.int64)
        shifts = _readonly_array(self.node_image_shifts, np.int64, shape_tail=(3,))
        primary = _readonly_array(
            np.asarray(self.primary_cell_image_shifts, dtype=np.int64).reshape((-1, 3)),
            np.int64,
            shape_tail=(3,),
        )
        if source_nodes.shape != (n_nodes,) or source_edges.shape != (n_edges,):
            raise GraphViewValidationError(
                "Periodic source mappings have invalid lengths."
            )
        if shifts.shape != (n_nodes, 3):
            raise GraphViewValidationError(
                "node_image_shifts must have shape (n_nodes, 3)."
            )
        if source_nodes.size and (
            np.min(source_nodes) < 0 or np.max(source_nodes) >= self.source_view.n_nodes
        ):
            raise GraphViewValidationError("source_node_positions are out of range.")
        if source_edges.size and (
            np.min(source_edges) < 0 or np.max(source_edges) >= self.source_view.n_edges
        ):
            raise GraphViewValidationError("source_edge_positions are out of range.")
        node_roles = tuple(self.node_roles)
        edge_roles = tuple(self.edge_roles)
        if len(node_roles) != n_nodes or len(edge_roles) != n_edges:
            raise GraphViewValidationError(
                "Periodic role sequences have invalid lengths."
            )
        if self.graph.node_positions_3d is None:
            raise GraphViewValidationError(
                "Materialized periodic graph requires 3-D positions."
            )
        if self.graph.edge_image_shifts is not None and np.any(
            self.graph.edge_image_shifts != 0
        ):
            raise GraphViewValidationError(
                "Materialized periodic graph must not retain unresolved edge shifts."
            )
        object.__setattr__(self, "source_node_positions", source_nodes)
        object.__setattr__(self, "source_edge_positions", source_edges)
        object.__setattr__(self, "node_image_shifts", shifts)
        object.__setattr__(self, "primary_cell_image_shifts", primary)
        object.__setattr__(self, "node_roles", node_roles)
        object.__setattr__(self, "edge_roles", edge_roles)
        object.__setattr__(
            self,
            "selection_metadata",
            _freeze_metadata(
                dict(self.selection_metadata), context="selection_metadata"
            ),
        )
        object.__setattr__(
            self,
            "periodic_metadata",
            _freeze_metadata(dict(self.periodic_metadata), context="periodic_metadata"),
        )
        object.__setattr__(self, "warnings", tuple(self.warnings))


def _validate_periodic_source(
    prepared: PreparedGraphView,
    periodic: PeriodicDisplayOptions,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    if prepared.node_positions_3d is None:
        raise GraphViewValidationError(
            "Periodic display preparation requires finite node_positions_3d."
        )
    positions = np.asarray(prepared.node_positions_3d, dtype=float)
    shifts = (
        np.zeros((len(prepared.edge_keys), 3), dtype=np.int64)
        if prepared.edge_image_shifts is None
        else np.asarray(prepared.edge_image_shifts, dtype=np.int64)
    )
    source = prepared.source_view
    pbc = (
        np.zeros(3, dtype=bool)
        if source.pbc is None
        else np.asarray(source.pbc, dtype=bool)
    )
    if np.any(shifts[:, ~pbc] != 0):
        raise GraphViewValidationError(
            "Edge image shifts are nonzero along nonperiodic axes."
        )
    needs_cell = bool(np.any(shifts != 0)) or not isinstance(
        periodic, CanonicalCellDisplay
    )
    cell = None if source.cell is None else np.asarray(source.cell, dtype=float)
    if needs_cell and cell is None:
        raise GraphViewValidationError(
            "The selected periodic display mode requires a finite cell."
        )
    if isinstance(periodic, (LocalUnwrappedDisplay, ExpandedCellDisplay)):
        if source.pbc is None or prepared.edge_image_shifts is None:
            raise GraphViewValidationError(
                "Local and expanded display require pbc and edge_image_shifts."
            )
    if isinstance(periodic, ExpandedCellDisplay):
        for axis, interval in enumerate(periodic.image_ranges):
            if not pbc[axis] and interval != (0, 0):
                raise GraphViewValidationError(
                    "Nonperiodic axes must use image range (0, 0)."
                )
    return positions, shifts, cell


def _complexity_message(exceeded: list[str], mode: PeriodicDisplayMode) -> str:
    return (
        f"Periodic {mode.value} materialization exceeds: {', '.join(exceeded)}. "
        "Reduce source focus/filtering or the requested image range."
    )


def _enforce_counts(
    *,
    nodes: int,
    edges: int,
    policy: GraphComplexityPolicy,
    mode: PeriodicDisplayMode,
    warning_messages: list[str],
    stage: str,
) -> None:
    exceeded: list[str] = []
    if nodes > policy.max_nodes:
        exceeded.append(f"max_nodes ({nodes} > {policy.max_nodes})")
    if edges > policy.max_edges:
        exceeded.append(f"max_edges ({edges} > {policy.max_edges})")
    if not exceeded:
        return
    message = f"{stage}: {_complexity_message(exceeded, mode)}"
    if policy.overflow in {"error", "require_focus"}:
        raise GraphComplexityError(message)
    warning_messages.append(message)


def _take_column(column: AttributeColumn, positions: Sequence[int]) -> AttributeColumn:
    if isinstance(column, np.ndarray):
        result = np.array(column[np.asarray(positions, dtype=np.int64)], copy=True)
        result.setflags(write=False)
        return result
    return tuple(column[int(position)] for position in positions)


def _build_display_graph(
    *,
    prepared: PreparedGraphView,
    node_keys: list[PeriodicNodeKey],
    edge_keys: list[PeriodicEdgeKey],
    edge_endpoints: list[tuple[int, int]],
    node_source_local: list[int],
    edge_source_local: list[int],
    node_shifts: list[ImageShift],
    node_roles: list[PeriodicNodeRole],
    edge_roles: list[PeriodicEdgeRole],
    cell: np.ndarray | None,
    pbc: np.ndarray,
    mode: PeriodicDisplayMode,
) -> tuple[DecoratedGraphView, np.ndarray, np.ndarray]:
    reserved_node = {"display_role", "image_shift"}
    reserved_edge = {
        "display_role",
        "source_image_shift",
        "target_image_shift",
    }
    if reserved_node & set(prepared.source_view.node_attributes):
        raise GraphViewValidationError(
            "Source node attributes conflict with reserved periodic display columns."
        )
    if reserved_edge & set(prepared.source_view.edge_attributes):
        raise GraphViewValidationError(
            "Source edge attributes conflict with reserved periodic display columns."
        )

    source_node_positions = [
        int(prepared.node_source_positions[local]) for local in node_source_local
    ]
    source_edge_positions = [
        int(prepared.edge_source_positions[local]) for local in edge_source_local
    ]
    shifts_array = np.asarray(node_shifts, dtype=np.int64).reshape((-1, 3))
    source_positions = np.asarray(prepared.source_view.node_positions_3d, dtype=float)
    if cell is None:
        display_positions = source_positions[np.asarray(source_node_positions)]
    else:
        display_positions = (
            source_positions[np.asarray(source_node_positions)] + shifts_array @ cell
        )

    node_attributes: dict[str, AttributeColumn] = {
        name: _take_column(column, source_node_positions)
        for name, column in prepared.source_view.node_attributes.items()
    }
    edge_attributes: dict[str, AttributeColumn] = {
        name: _take_column(column, source_edge_positions)
        for name, column in prepared.source_view.edge_attributes.items()
    }
    node_attributes["display_role"] = tuple(role.value for role in node_roles)
    node_attributes["image_shift"] = tuple(node_shifts)
    edge_attributes["display_role"] = tuple(role.value for role in edge_roles)
    edge_attributes["source_image_shift"] = tuple(
        key.source_image_shift for key in edge_keys
    )
    edge_attributes["target_image_shift"] = tuple(
        key.target_image_shift for key in edge_keys
    )

    graph = DecoratedGraphView(
        node_keys=tuple(node_keys),
        edge_keys=tuple(edge_keys),
        edge_endpoints=np.asarray(edge_endpoints, dtype=np.int64).reshape((-1, 2)),
        node_positions_3d=np.asarray(display_positions, dtype=float).reshape((-1, 3)),
        edge_image_shifts=np.zeros((len(edge_keys), 3), dtype=np.int64),
        cell=prepared.source_view.cell,
        pbc=prepared.source_view.pbc,
        node_attributes=node_attributes,
        edge_attributes=edge_attributes,
        directed=prepared.source_view.directed,
        multigraph=prepared.source_view.multigraph,
        metadata={
            "periodic_display_schema": PERIODIC_GRAPH_DISPLAY_SCHEMA,
            "periodic_display_mode": mode.value,
            "source_view_metadata": dict(prepared.source_view.metadata),
        },
    )
    return (
        graph,
        np.asarray(source_node_positions, dtype=np.int64),
        np.asarray(source_edge_positions, dtype=np.int64),
    )


def _intern_node(
    *,
    key: PeriodicNodeKey,
    role: PeriodicNodeRole,
    source_local: int,
    node_index: dict[PeriodicNodeKey, int],
    node_keys: list[PeriodicNodeKey],
    node_source_local: list[int],
    node_shifts: list[ImageShift],
    node_roles: list[PeriodicNodeRole],
) -> int:
    existing = node_index.get(key)
    if existing is not None:
        # A primary image has stronger presentation status than a ghost.
        if (
            node_roles[existing] is PeriodicNodeRole.GHOST
            and role is not PeriodicNodeRole.GHOST
        ):
            node_roles[existing] = role
        return existing
    index = len(node_keys)
    node_index[key] = index
    node_keys.append(key)
    node_source_local.append(source_local)
    node_shifts.append(key.image_shift)
    node_roles.append(role)
    return index


def _canonical_materialization(
    prepared: PreparedGraphView,
    shifts: np.ndarray,
) -> tuple[
    list[PeriodicNodeKey],
    list[PeriodicEdgeKey],
    list[tuple[int, int]],
    list[int],
    list[int],
    list[ImageShift],
    list[PeriodicNodeRole],
    list[PeriodicEdgeRole],
    list[ImageShift],
    list[ImageShift],
]:
    node_index: dict[PeriodicNodeKey, int] = {}
    node_keys: list[PeriodicNodeKey] = []
    node_source_local: list[int] = []
    node_shifts: list[ImageShift] = []
    node_roles: list[PeriodicNodeRole] = []
    zero: ImageShift = (0, 0, 0)
    for local, source_key in enumerate(prepared.node_keys):
        _intern_node(
            key=PeriodicNodeKey(source_key, zero),
            role=PeriodicNodeRole.CANONICAL,
            source_local=local,
            node_index=node_index,
            node_keys=node_keys,
            node_source_local=node_source_local,
            node_shifts=node_shifts,
            node_roles=node_roles,
        )

    edge_keys: list[PeriodicEdgeKey] = []
    edge_endpoints: list[tuple[int, int]] = []
    edge_source_local: list[int] = []
    edge_roles: list[PeriodicEdgeRole] = []
    residuals: list[ImageShift] = []
    for edge_local, (source_local, target_local) in enumerate(prepared.edge_endpoints):
        source_local, target_local = int(source_local), int(target_local)
        if source_local == target_local:
            raise GraphUnsupportedFeatureError(
                "Self-loop periodic materialization is not supported in G4."
            )
        shift = tuple(int(value) for value in shifts[edge_local])
        source_key = PeriodicNodeKey(prepared.node_keys[source_local], zero)
        target_key = PeriodicNodeKey(prepared.node_keys[target_local], shift)
        source_display = node_index[source_key]
        target_display = _intern_node(
            key=target_key,
            role=(
                PeriodicNodeRole.CANONICAL if shift == zero else PeriodicNodeRole.GHOST
            ),
            source_local=target_local,
            node_index=node_index,
            node_keys=node_keys,
            node_source_local=node_source_local,
            node_shifts=node_shifts,
            node_roles=node_roles,
        )
        edge_keys.append(PeriodicEdgeKey(prepared.edge_keys[edge_local], zero, shift))
        edge_endpoints.append((source_display, target_display))
        edge_source_local.append(edge_local)
        edge_roles.append(
            PeriodicEdgeRole.PRIMARY
            if shift == zero
            else PeriodicEdgeRole.BOUNDARY_GHOST
        )
        if shift != zero:
            residuals.append(shift)
    return (
        node_keys,
        edge_keys,
        edge_endpoints,
        node_source_local,
        edge_source_local,
        node_shifts,
        node_roles,
        edge_roles,
        [zero],
        residuals,
    )


def _local_node_selection(
    prepared: PreparedGraphView,
    options: LocalUnwrappedDisplay,
) -> tuple[set[int], int]:
    key_to_local = {key: i for i, key in enumerate(prepared.node_keys)}
    if options.center_node_key not in key_to_local:
        raise GraphFilterError(
            f"Local center node {options.center_node_key!r} does not survive source selection."
        )
    center = key_to_local[options.center_node_key]
    out_adj: list[list[int]] = [[] for _ in prepared.node_keys]
    in_adj: list[list[int]] = [[] for _ in prepared.node_keys]
    for source, target in prepared.edge_endpoints:
        source_i, target_i = int(source), int(target)
        out_adj[source_i].append(target_i)
        in_adj[target_i].append(source_i)
        if not prepared.source_view.directed:
            out_adj[target_i].append(source_i)
            in_adj[source_i].append(target_i)
    selected = {center}
    queue: deque[tuple[int, int]] = deque([(center, 0)])
    while queue:
        node, depth = queue.popleft()
        if options.hop_radius is not None and depth >= options.hop_radius:
            continue
        if not prepared.source_view.directed or options.direction == "both":
            neighbors = set(out_adj[node]) | set(in_adj[node])
        elif options.direction == "out":
            neighbors = set(out_adj[node])
        else:
            neighbors = set(in_adj[node])
        for neighbor in sorted(neighbors):
            if neighbor not in selected:
                selected.add(neighbor)
                queue.append((neighbor, depth + 1))
    return selected, center


def _deterministic_image_assignment(
    *,
    edge_endpoints: NDArray[np.int64],
    edge_shifts: NDArray[np.int64],
    n_nodes: int,
    preferred_roots: Sequence[int] = (),
    selected_nodes: set[int] | None = None,
    node_order: Sequence[int] | None = None,
    edge_order: Sequence[int] | None = None,
) -> NDArray[np.int64]:
    """Assign deterministic lattice images through a spanning forest.

    This private helper is the single implementation used by G4 and by the
    backward-compatible 2-D local-unwrapping path.  Edge shifts follow the
    stored source-to-target orientation.
    """
    selected = set(range(n_nodes)) if selected_nodes is None else set(selected_nodes)
    node_rank = (
        list(range(n_nodes)) if node_order is None else [int(x) for x in node_order]
    )
    edge_rank = (
        list(range(len(edge_endpoints)))
        if edge_order is None
        else [int(x) for x in edge_order]
    )
    adjacency: list[list[tuple[int, int, int]]] = [[] for _ in range(n_nodes)]
    for edge_local, (source, target) in enumerate(edge_endpoints):
        source_i, target_i = int(source), int(target)
        if source_i not in selected or target_i not in selected:
            continue
        adjacency[source_i].append((target_i, edge_local, 1))
        adjacency[target_i].append((source_i, edge_local, -1))
    for source in selected:
        adjacency[source].sort(
            key=lambda item: (node_rank[item[0]], edge_rank[item[1]], item[2])
        )
    roots = [int(root) for root in preferred_roots if int(root) in selected]
    roots.extend(
        node
        for node in sorted(selected, key=lambda item: node_rank[item])
        if node not in roots
    )
    offsets = np.zeros((n_nodes, 3), dtype=np.int64)
    assigned = np.zeros(n_nodes, dtype=bool)
    for root in roots:
        if assigned[root]:
            continue
        assigned[root] = True
        queue: deque[int] = deque([root])
        while queue:
            source = queue.popleft()
            for target, edge_local, orientation in adjacency[source]:
                if assigned[target]:
                    continue
                offsets[target] = (
                    offsets[source] + orientation * edge_shifts[edge_local]
                )
                assigned[target] = True
                queue.append(target)
    return offsets


def _residual_edge_shifts(
    edge_endpoints: NDArray[np.int64],
    edge_shifts: NDArray[np.int64],
    node_image_shifts: NDArray[np.int64],
) -> NDArray[np.int64]:
    residual = np.empty_like(edge_shifts)
    for edge_local, (source, target) in enumerate(edge_endpoints):
        residual[edge_local] = (
            edge_shifts[edge_local]
            + node_image_shifts[int(source)]
            - node_image_shifts[int(target)]
        )
    return residual


def _local_materialization(
    prepared: PreparedGraphView,
    shifts: np.ndarray,
    options: LocalUnwrappedDisplay,
) -> tuple[
    list[PeriodicNodeKey],
    list[PeriodicEdgeKey],
    list[tuple[int, int]],
    list[int],
    list[int],
    list[ImageShift],
    list[PeriodicNodeRole],
    list[PeriodicEdgeRole],
    list[ImageShift],
    list[ImageShift],
    tuple[GraphKey, ...],
]:
    selected, center = _local_node_selection(prepared, options)
    local_edges = [
        edge_local
        for edge_local, (source, target) in enumerate(prepared.edge_endpoints)
        if int(source) in selected and int(target) in selected
    ]

    assigned_array = _deterministic_image_assignment(
        edge_endpoints=prepared.edge_endpoints,
        edge_shifts=shifts,
        n_nodes=len(prepared.node_keys),
        preferred_roots=(center,),
        selected_nodes=selected,
        node_order=prepared.node_source_positions,
        edge_order=prepared.edge_source_positions,
    )
    assigned = {source_local: assigned_array[source_local] for source_local in selected}

    node_index: dict[PeriodicNodeKey, int] = {}
    node_keys: list[PeriodicNodeKey] = []
    node_source_local: list[int] = []
    node_shifts: list[ImageShift] = []
    node_roles: list[PeriodicNodeRole] = []
    for source_local in sorted(
        selected, key=lambda i: int(prepared.node_source_positions[i])
    ):
        shift = tuple(int(value) for value in assigned[source_local])
        _intern_node(
            key=PeriodicNodeKey(prepared.node_keys[source_local], shift),
            role=(
                PeriodicNodeRole.CANONICAL
                if shift == (0, 0, 0)
                else PeriodicNodeRole.REPLICA
            ),
            source_local=source_local,
            node_index=node_index,
            node_keys=node_keys,
            node_source_local=node_source_local,
            node_shifts=node_shifts,
            node_roles=node_roles,
        )

    edge_keys: list[PeriodicEdgeKey] = []
    edge_endpoints: list[tuple[int, int]] = []
    edge_source_local: list[int] = []
    edge_roles: list[PeriodicEdgeRole] = []
    residuals: list[ImageShift] = []
    for edge_local in local_edges:
        source_local, target_local = (
            int(value) for value in prepared.edge_endpoints[edge_local]
        )
        if source_local == target_local:
            raise GraphUnsupportedFeatureError(
                "Self-loop periodic materialization is not supported in G4."
            )
        source_shift = tuple(int(value) for value in assigned[source_local])
        assigned_target_shift = tuple(int(value) for value in assigned[target_local])
        expected_target = tuple(
            int(value) for value in (assigned[source_local] + shifts[edge_local])
        )
        residual = tuple(
            int(value)
            for value in (
                assigned[source_local] + shifts[edge_local] - assigned[target_local]
            )
        )
        source_key = PeriodicNodeKey(prepared.node_keys[source_local], source_shift)
        source_display = node_index[source_key]
        if residual == (0, 0, 0):
            target_key = PeriodicNodeKey(
                prepared.node_keys[target_local], assigned_target_shift
            )
            target_display = node_index[target_key]
            edge_role = PeriodicEdgeRole.PRIMARY
        else:
            target_key = PeriodicNodeKey(
                prepared.node_keys[target_local], expected_target
            )
            target_display = _intern_node(
                key=target_key,
                role=PeriodicNodeRole.GHOST,
                source_local=target_local,
                node_index=node_index,
                node_keys=node_keys,
                node_source_local=node_source_local,
                node_shifts=node_shifts,
                node_roles=node_roles,
            )
            edge_role = PeriodicEdgeRole.CYCLE_GHOST
            residuals.append(residual)
        edge_keys.append(
            PeriodicEdgeKey(
                prepared.edge_keys[edge_local],
                source_shift,
                target_key.image_shift,
            )
        )
        edge_endpoints.append((source_display, target_display))
        edge_source_local.append(edge_local)
        edge_roles.append(edge_role)

    primary_shifts = sorted(
        {
            tuple(int(value) for value in assigned[source_local])
            for source_local in selected
        }
    )
    omitted = tuple(
        prepared.node_keys[index]
        for index in range(len(prepared.node_keys))
        if index not in selected
    )
    return (
        node_keys,
        edge_keys,
        edge_endpoints,
        node_source_local,
        edge_source_local,
        node_shifts,
        node_roles,
        edge_roles,
        primary_shifts,
        residuals,
        omitted,
    )


def _expanded_shifts(options: ExpandedCellDisplay) -> list[ImageShift]:
    axes = [range(lower, upper + 1) for lower, upper in options.image_ranges]
    return [tuple(int(value) for value in shift) for shift in product(*axes)]  # type: ignore[list-item]


def _expanded_materialization(
    prepared: PreparedGraphView,
    shifts: np.ndarray,
    options: ExpandedCellDisplay,
) -> tuple[
    list[PeriodicNodeKey],
    list[PeriodicEdgeKey],
    list[tuple[int, int]],
    list[int],
    list[int],
    list[ImageShift],
    list[PeriodicNodeRole],
    list[PeriodicEdgeRole],
    list[ImageShift],
    list[ImageShift],
]:
    primary_shifts = _expanded_shifts(options)
    primary_set = set(primary_shifts)
    node_index: dict[PeriodicNodeKey, int] = {}
    node_keys: list[PeriodicNodeKey] = []
    node_source_local: list[int] = []
    node_shifts: list[ImageShift] = []
    node_roles: list[PeriodicNodeRole] = []
    for image_shift in primary_shifts:
        role = (
            PeriodicNodeRole.CANONICAL
            if image_shift == (0, 0, 0)
            else PeriodicNodeRole.REPLICA
        )
        for source_local, source_key in enumerate(prepared.node_keys):
            _intern_node(
                key=PeriodicNodeKey(source_key, image_shift),
                role=role,
                source_local=source_local,
                node_index=node_index,
                node_keys=node_keys,
                node_source_local=node_source_local,
                node_shifts=node_shifts,
                node_roles=node_roles,
            )

    edge_keys: list[PeriodicEdgeKey] = []
    edge_endpoints: list[tuple[int, int]] = []
    edge_source_local: list[int] = []
    edge_roles: list[PeriodicEdgeRole] = []
    boundary_shifts: list[ImageShift] = []
    for source_image in primary_shifts:
        source_vector = np.asarray(source_image, dtype=np.int64)
        for edge_local, (source_local, target_local) in enumerate(
            prepared.edge_endpoints
        ):
            source_local, target_local = int(source_local), int(target_local)
            if source_local == target_local:
                raise GraphUnsupportedFeatureError(
                    "Self-loop periodic materialization is not supported in G4."
                )
            target_image = tuple(
                int(value) for value in source_vector + shifts[edge_local]
            )
            source_key = PeriodicNodeKey(prepared.node_keys[source_local], source_image)
            target_key = PeriodicNodeKey(prepared.node_keys[target_local], target_image)
            source_display = node_index[source_key]
            if target_image in primary_set:
                target_display = node_index[target_key]
                edge_role = (
                    PeriodicEdgeRole.PRIMARY
                    if source_image == (0, 0, 0)
                    else PeriodicEdgeRole.REPLICA
                )
            else:
                target_display = _intern_node(
                    key=target_key,
                    role=PeriodicNodeRole.GHOST,
                    source_local=target_local,
                    node_index=node_index,
                    node_keys=node_keys,
                    node_source_local=node_source_local,
                    node_shifts=node_shifts,
                    node_roles=node_roles,
                )
                edge_role = PeriodicEdgeRole.BOUNDARY_GHOST
                boundary_shifts.append(target_image)
            edge_keys.append(
                PeriodicEdgeKey(
                    prepared.edge_keys[edge_local],
                    source_image,
                    target_image,
                )
            )
            edge_endpoints.append((source_display, target_display))
            edge_source_local.append(edge_local)
            edge_roles.append(edge_role)
    return (
        node_keys,
        edge_keys,
        edge_endpoints,
        node_source_local,
        edge_source_local,
        node_shifts,
        node_roles,
        edge_roles,
        primary_shifts,
        boundary_shifts,
    )


def _overlap_warning(positions: np.ndarray) -> str | None:
    if len(positions) < 2:
        return None
    rounded = np.round(np.asarray(positions, dtype=float), decimals=10)
    _, counts = np.unique(rounded, axis=0, return_counts=True)
    duplicates = int(np.sum(counts[counts > 1] - 1))
    if duplicates:
        return (
            f"{duplicates} display nodes share Cartesian coordinates with another "
            "periodic node image."
        )
    return None


def prepare_periodic_graph_view(
    view: DecoratedGraphView,
    *,
    periodic: PeriodicDisplayOptions | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
) -> PeriodicGraphView:
    """Materialize a periodic decorated graph for renderer-independent display.

    Focus and filtering are applied to the source graph before any periodic
    replication.  Every display object retains an exact mapping to its source
    node or edge position.
    """
    if not isinstance(view, DecoratedGraphView):
        raise TypeError("view must be a DecoratedGraphView.")
    periodic = periodic or CanonicalCellDisplay()
    if not isinstance(
        periodic, (CanonicalCellDisplay, LocalUnwrappedDisplay, ExpandedCellDisplay)
    ):
        raise TypeError("periodic must be a supported PeriodicDisplayOptions value.")
    policy = complexity_policy or GraphComplexityPolicy()
    prepared = prepare_graph_view(view, focus=focus, graph_filter=graph_filter)
    positions, shifts, cell = _validate_periodic_source(prepared, periodic)
    pbc = (
        np.zeros(3, dtype=bool)
        if view.pbc is None
        else np.asarray(view.pbc, dtype=bool)
    )
    warning_messages: list[str] = list(view.metadata.get("adapter_warnings", ()))
    if prepared.edge_endpoints.shape[0] == 0:
        warning_messages.append("The selected graph has no edges.")

    n_source_nodes = len(prepared.node_keys)
    n_source_edges = len(prepared.edge_keys)
    if isinstance(periodic, CanonicalCellDisplay):
        estimated_nodes = n_source_nodes + n_source_edges
        estimated_edges = n_source_edges
    elif isinstance(periodic, LocalUnwrappedDisplay):
        selected, _ = _local_node_selection(prepared, periodic)
        local_edges = sum(
            int(source) in selected and int(target) in selected
            for source, target in prepared.edge_endpoints
        )
        estimated_nodes = len(selected) + local_edges
        estimated_edges = local_edges
    else:
        n_cells = len(_expanded_shifts(periodic))
        estimated_nodes = n_cells * (n_source_nodes + n_source_edges)
        estimated_edges = n_cells * n_source_edges
    _enforce_counts(
        nodes=estimated_nodes,
        edges=estimated_edges,
        policy=policy,
        mode=periodic.mode,
        warning_messages=warning_messages,
        stage="Conservative pre-allocation estimate",
    )

    omitted_local: tuple[GraphKey, ...] = ()
    if isinstance(periodic, CanonicalCellDisplay):
        materialized = _canonical_materialization(prepared, shifts)
        (
            node_keys,
            edge_keys,
            edge_endpoints,
            node_source_local,
            edge_source_local,
            node_shifts,
            node_roles,
            edge_roles,
            primary_shifts,
            residuals,
        ) = materialized
    elif isinstance(periodic, LocalUnwrappedDisplay):
        materialized_local = _local_materialization(prepared, shifts, periodic)
        (
            node_keys,
            edge_keys,
            edge_endpoints,
            node_source_local,
            edge_source_local,
            node_shifts,
            node_roles,
            edge_roles,
            primary_shifts,
            residuals,
            omitted_local,
        ) = materialized_local
        if residuals:
            warning_messages.append(
                f"Residual periodic winding required {len(residuals)} cycle ghost edges."
            )
        if omitted_local:
            warning_messages.append(
                f"Local display omitted {len(omitted_local)} selected nodes outside "
                "the center component or hop neighborhood."
            )
    else:
        materialized = _expanded_materialization(prepared, shifts, periodic)
        (
            node_keys,
            edge_keys,
            edge_endpoints,
            node_source_local,
            edge_source_local,
            node_shifts,
            node_roles,
            edge_roles,
            primary_shifts,
            residuals,
        ) = materialized
        lengths = np.asarray(
            [upper - lower + 1 for lower, upper in periodic.image_ranges], dtype=float
        )
        positive = lengths[lengths > 0]
        if positive.size and np.max(positive) / np.min(positive) >= 8.0:
            warning_messages.append("The expanded image range is highly anisotropic.")

    _enforce_counts(
        nodes=len(node_keys),
        edges=len(edge_keys),
        policy=policy,
        mode=periodic.mode,
        warning_messages=warning_messages,
        stage="Final materialization",
    )
    if len(set(edge_keys)) != len(edge_keys):
        raise GraphViewValidationError("Periodic display edge keys are not unique.")

    graph, source_node_positions, source_edge_positions = _build_display_graph(
        prepared=prepared,
        node_keys=node_keys,
        edge_keys=edge_keys,
        edge_endpoints=edge_endpoints,
        node_source_local=node_source_local,
        edge_source_local=edge_source_local,
        node_shifts=node_shifts,
        node_roles=node_roles,
        edge_roles=edge_roles,
        cell=cell,
        pbc=pbc,
        mode=periodic.mode,
    )
    overlap = _overlap_warning(np.asarray(graph.node_positions_3d, dtype=float))
    if overlap is not None:
        warning_messages.append(overlap)
    role_nodes = Counter(role.value for role in node_roles)
    role_edges = Counter(role.value for role in edge_roles)
    ghost_count = role_nodes.get(PeriodicNodeRole.GHOST.value, 0)
    primary_count = max(1, len(node_keys) - ghost_count)
    if ghost_count / primary_count > 0.5:
        warning_messages.append(
            "The ghost-to-primary display-node ratio exceeds 0.5; consider a local "
            "or expanded view with a more suitable range."
        )

    mode_payload: dict[str, Any] = {}
    if isinstance(periodic, LocalUnwrappedDisplay):
        mode_payload = {
            "center_node_key": periodic.center_node_key,
            "hop_radius": periodic.hop_radius,
            "direction": periodic.direction,
            "omitted_local_node_keys": omitted_local,
        }
    elif isinstance(periodic, ExpandedCellDisplay):
        mode_payload = {"image_ranges": periodic.image_ranges}

    periodic_metadata = {
        "schema_version": PERIODIC_GRAPH_DISPLAY_SCHEMA,
        "mode": periodic.mode.value,
        "source_nodes": view.n_nodes,
        "source_edges": view.n_edges,
        "selected_source_nodes": n_source_nodes,
        "selected_source_edges": n_source_edges,
        "display_nodes": len(node_keys),
        "display_edges": len(edge_keys),
        "node_role_counts": dict(role_nodes),
        "edge_role_counts": dict(role_edges),
        "primary_cell_image_shifts": tuple(primary_shifts),
        "residual_winding_vectors": tuple(residuals),
        "cell_present": view.cell is not None,
        "pbc": tuple(bool(value) for value in pbc),
        "conservative_estimate_nodes": estimated_nodes,
        "conservative_estimate_edges": estimated_edges,
        "warnings": tuple(warning_messages),
        **mode_payload,
    }
    selection_metadata = {
        **dict(prepared.selection_metadata),
        "omitted_local_node_keys": omitted_local,
    }
    return PeriodicGraphView(
        source_view=view,
        graph=graph,
        mode=periodic.mode,
        source_node_positions=source_node_positions,
        source_edge_positions=source_edge_positions,
        node_image_shifts=np.asarray(node_shifts, dtype=np.int64).reshape((-1, 3)),
        node_roles=tuple(node_roles),
        edge_roles=tuple(edge_roles),
        primary_cell_image_shifts=np.asarray(primary_shifts, dtype=np.int64).reshape(
            (-1, 3)
        ),
        selection_metadata=selection_metadata,
        periodic_metadata=periodic_metadata,
        warnings=tuple(warning_messages),
    )


__all__ = [
    "CanonicalCellDisplay",
    "ExpandedCellDisplay",
    "LocalUnwrappedDisplay",
    "PERIODIC_GRAPH_DISPLAY_SCHEMA",
    "PeriodicDisplayMode",
    "PeriodicDisplayOptions",
    "PeriodicEdgeKey",
    "PeriodicEdgeRole",
    "PeriodicGraphView",
    "PeriodicNodeKey",
    "PeriodicNodeRole",
    "prepare_periodic_graph_view",
]
