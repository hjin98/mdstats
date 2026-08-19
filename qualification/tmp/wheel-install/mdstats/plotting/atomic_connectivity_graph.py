"""Visualization adapters for atomic-connectivity states and transitions."""

from __future__ import annotations

from collections import deque
from typing import Any, Literal

import numpy as np
from ase.data import chemical_symbols
from matplotlib.axes import Axes

from ..analysis._neighbors import minimum_image_geometry
from ..analysis.atomic_connectivity import (
    AtomicConnectivityResult,
    AtomicConnectivityState,
    AtomicEdgeKey,
)
from ..collection import AtomisticFrameCollection
from .graph_2d import (
    Graph2DRenderOptions,
    GraphLayoutOptions,
    GraphRenderResult,
    plot_decorated_graph_2d,
)
from .graph_errors import GraphAdapterError
from .graph_3d import (
    Graph3DRenderOptions,
    InteractiveGraphRenderResult,
    plot_decorated_graph_3d,
)
from .graph_styles import GraphStyle
from .periodic_graph import PeriodicDisplayOptions
from .graph_view import (
    DecoratedGraphView,
    GraphComplexityPolicy,
    GraphFilter,
    GraphFocus,
)

ATOMIC_GRAPH_ADAPTER_SCHEMA = "mdstats.atomic-connectivity-graph-view.v1"
TRANSITION_GRAPH_ADAPTER_SCHEMA = "mdstats.connectivity-transition-graph-view.v1"


def _validated_frame_index(
    collection: AtomisticFrameCollection, frame_index: int
) -> int:
    if isinstance(frame_index, bool) or not isinstance(frame_index, (int, np.integer)):
        raise GraphAdapterError("frame_index must be an integer collection position.")
    frame = int(frame_index)
    if frame < 0 or frame >= collection.n_frames:
        raise GraphAdapterError(
            f"frame_index={frame} is outside [0, {collection.n_frames})."
        )
    return frame


def _state_for_input(
    connectivity: AtomicConnectivityState | AtomicConnectivityResult,
    frame_index: int,
) -> tuple[AtomicConnectivityState, dict[str, Any]]:
    if isinstance(connectivity, AtomicConnectivityState):
        return connectivity, {
            "connectivity_definition_kind": None,
            "connectivity_consistency": None,
        }
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise TypeError(
            "connectivity must be an AtomicConnectivityState or "
            "AtomicConnectivityResult."
        )
    matches = np.flatnonzero(connectivity.frame_indices == frame_index)
    if matches.size != 1:
        raise GraphAdapterError(
            f"Collection frame {frame_index} is not represented exactly once in the "
            "connectivity result."
        )
    result_position = int(matches[0])
    state_id = int(connectivity.frame_state_ids[result_position])
    return connectivity.states[state_id], {
        "connectivity_definition_kind": connectivity.definition.kind,
        "connectivity_consistency": connectivity.consistency.value,
        "source_state_id": state_id,
        "result_position": result_position,
    }


def _validate_state_collection(
    collection: AtomisticFrameCollection,
    state: AtomicConnectivityState,
    frame: int,
) -> None:
    indices = state.active_atom_indices
    if indices.size == 0 or int(indices[-1]) >= collection.n_atoms:
        raise GraphAdapterError(
            "Connectivity state contains atom indices outside the collection."
        )
    if not np.array_equal(
        state.active_atomic_numbers,
        collection.atomic_numbers[indices],
    ):
        raise GraphAdapterError(
            "Connectivity state atomic numbers do not match the collection ordering."
        )
    if not np.array_equal(state.pbc, collection.pbc):
        raise GraphAdapterError(
            "Connectivity state PBC flags do not match the selected collection frame."
        )
    cell = np.asarray(collection.cells[frame], dtype=float)
    if (
        cell.shape != (3, 3)
        or np.any(~np.isfinite(cell))
        or abs(float(np.linalg.det(cell))) <= 1.0e-12
    ):
        raise GraphAdapterError("Selected frame cell must be finite and nonsingular.")
    positions = collection.get_wrapped_positions(frame)
    if positions.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(positions)):
        raise GraphAdapterError("Selected frame positions are malformed or nonfinite.")


def _oriented_canonical_shift(
    edge: AtomicEdgeKey, source: int, target: int
) -> np.ndarray:
    if source == edge.atom_i and target == edge.atom_j:
        return np.asarray(edge.image_shift, dtype=np.int64)
    if source == edge.atom_j and target == edge.atom_i:
        return -np.asarray(edge.image_shift, dtype=np.int64)
    raise GraphAdapterError("Edge traversal endpoint mismatch.")


def _minimum_image_shift(
    positions: np.ndarray,
    source: int,
    target: int,
    *,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> tuple[np.ndarray, bool]:
    raw = positions[target] - positions[source]
    _, _, shift = minimum_image_geometry(raw, cell=cell, pbc=pbc)
    shift = np.asarray(shift, dtype=np.int64)
    inverse = np.linalg.inv(cell)
    fractional = raw @ inverse
    tie = bool(
        np.any(
            pbc
            & np.isclose(
                np.abs(fractional - np.rint(fractional)),
                0.5,
                rtol=0.0,
                atol=1.0e-10,
            )
        )
    )
    return shift, tie


def _reconstruct_display_shifts(
    collection: AtomisticFrameCollection,
    state: AtomicConnectivityState,
    *,
    frame_index: int,
) -> tuple[np.ndarray, tuple[str, ...]]:
    """Map canonical graph shifts into the selected frame's wrapping gauge.

    The spanning-forest propagation uses minimum-image shifts only on tree
    edges.  Non-tree shifts are reconstructed from the canonical graph so
    periodic winding information is preserved exactly.
    """
    active = [int(value) for value in state.active_atom_indices]
    active_set = set(active)
    positions = np.asarray(collection.get_wrapped_positions(frame_index), dtype=float)
    cell = np.asarray(collection.cells[frame_index], dtype=float)
    pbc = np.asarray(collection.pbc, dtype=bool)
    edges = state.edge_keys
    adjacency: dict[int, list[tuple[int, int]]] = {atom: [] for atom in active}
    for edge_index, edge in enumerate(edges):
        adjacency[edge.atom_i].append((edge.atom_j, edge_index))
        adjacency[edge.atom_j].append((edge.atom_i, edge_index))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], item[1]))

    gauge: dict[int, np.ndarray] = {}
    ambiguous = False
    for root in active:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            source = queue.popleft()
            for target, edge_index in adjacency[source]:
                if target in gauge:
                    continue
                edge = edges[edge_index]
                canonical = _oriented_canonical_shift(edge, source, target)
                mic, tie = _minimum_image_shift(
                    positions,
                    source,
                    target,
                    cell=cell,
                    pbc=pbc,
                )
                ambiguous |= tie
                gauge[target] = gauge[source] + mic - canonical
                queue.append(target)

    if set(gauge) != active_set:  # pragma: no cover - forest covers isolated nodes
        raise GraphAdapterError("Could not assign a display gauge to all active atoms.")
    display = np.empty((len(edges), 3), dtype=np.int64)
    for edge_index, edge in enumerate(edges):
        canonical = np.asarray(edge.image_shift, dtype=np.int64)
        display[edge_index] = canonical - gauge[edge.atom_i] + gauge[edge.atom_j]
    if np.any(display[:, ~pbc] != 0):
        raise GraphAdapterError(
            "Reconstructed display shifts are nonzero along nonperiodic axes."
        )
    for edge, shift in zip(edges, display, strict=True):
        vector = positions[edge.atom_j] + shift @ cell - positions[edge.atom_i]
        if np.any(~np.isfinite(vector)):
            raise GraphAdapterError("Reconstructed periodic edge vector is nonfinite.")
    messages = (
        (
            (
                "A minimum-image tie was encountered while reconstructing frame-local "
                "display shifts."
            ),
        )
        if ambiguous
        else ()
    )
    return display, messages


def _state_graph_view(
    collection: AtomisticFrameCollection,
    state: AtomicConnectivityState,
    *,
    frame_index: int,
    context: dict[str, Any],
) -> DecoratedGraphView:
    _validate_state_collection(collection, state, frame_index)
    active = state.active_atom_indices
    atom_to_local = {int(atom): position for position, atom in enumerate(active)}
    endpoints = np.asarray(
        [
            (atom_to_local[int(i)], atom_to_local[int(j)])
            for i, j in state.edge_atom_indices
        ],
        dtype=np.int64,
    )
    display_shifts, adapter_warnings = _reconstruct_display_shifts(
        collection, state, frame_index=frame_index
    )
    symbols = tuple(
        chemical_symbols[int(number)] for number in state.active_atomic_numbers
    )
    edge_keys = state.edge_keys
    source_symbols = tuple(
        chemical_symbols[int(collection.atomic_numbers[edge.atom_i])]
        for edge in edge_keys
    )
    target_symbols = tuple(
        chemical_symbols[int(collection.atomic_numbers[edge.atom_j])]
        for edge in edge_keys
    )
    return DecoratedGraphView(
        node_keys=tuple(int(atom) for atom in active),
        edge_keys=edge_keys,
        edge_endpoints=endpoints,
        node_positions_3d=np.asarray(
            collection.get_wrapped_positions(frame_index)[active], dtype=float
        ),
        edge_image_shifts=display_shifts,
        cell=np.asarray(collection.cells[frame_index], dtype=float),
        pbc=np.asarray(collection.pbc, dtype=bool),
        node_attributes={
            "atom_index": np.asarray(active, dtype=np.int64),
            "atomic_number": np.asarray(state.active_atomic_numbers, dtype=np.int32),
            "symbol": symbols,
            "degree": np.asarray(state.degree, dtype=np.int32),
            "component_id": np.asarray(state.component_labels, dtype=np.int32),
            "affected": np.zeros(active.size, dtype=bool),
        },
        edge_attributes={
            "atom_i": np.asarray([edge.atom_i for edge in edge_keys], dtype=np.int64),
            "atom_j": np.asarray([edge.atom_j for edge in edge_keys], dtype=np.int64),
            "source_symbol": source_symbols,
            "target_symbol": target_symbols,
            "species_pair": tuple(
                tuple(sorted((source, target)))
                for source, target in zip(source_symbols, target_symbols, strict=True)
            ),
            "canonical_image_shift": tuple(edge.image_shift for edge in edge_keys),
            "display_image_shift": tuple(
                tuple(int(x) for x in shift) for shift in display_shifts
            ),
            "periodic": np.any(display_shifts != 0, axis=1),
            "transition_status": tuple("unchanged" for _ in edge_keys),
        },
        directed=False,
        multigraph=False,
        metadata={
            "adapter_schema_version": ATOMIC_GRAPH_ADAPTER_SCHEMA,
            "collection_frame_index": frame_index,
            "frame_id": int(collection.frame_ids[frame_index]),
            "source_state_digest": state.digest,
            "display_shift_reconstruction": (
                "Canonical topology was mapped into the selected frame's wrapping "
                "gauge without re-evaluating connectivity."
            ),
            "adapter_warnings": adapter_warnings,
            **context,
        },
    )


def graph_view_from_atomic_connectivity(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityState | AtomicConnectivityResult,
    *,
    frame_index: int,
) -> DecoratedGraphView:
    """Adapt one atomic-connectivity state to a physical decorated graph view."""
    frame = _validated_frame_index(collection, frame_index)
    state, context = _state_for_input(connectivity, frame)
    return _state_graph_view(
        collection,
        state,
        frame_index=frame,
        context=context,
    )


def _display_shift_by_pair(
    collection: AtomisticFrameCollection,
    state: AtomicConnectivityState,
    frame_index: int,
) -> dict[tuple[int, int], tuple[int, int, int]]:
    shifts, _ = _reconstruct_display_shifts(collection, state, frame_index=frame_index)
    return {
        edge.pair: tuple(int(x) for x in shift)
        for edge, shift in zip(state.edge_keys, shifts, strict=True)
    }


def graph_view_from_connectivity_transition(
    collection: AtomisticFrameCollection,
    result: AtomicConnectivityResult,
    *,
    transition_id: int,
    coordinate_frame: Literal["before", "after"] = "after",
) -> DecoratedGraphView:
    """Build a union diagnostic view for one atomic connectivity transition."""
    if not isinstance(result, AtomicConnectivityResult):
        raise TypeError("result must be an AtomicConnectivityResult.")
    if coordinate_frame not in {"before", "after"}:
        raise GraphAdapterError("coordinate_frame must be 'before' or 'after'.")
    matches = [
        item for item in result.transitions if item.transition_id == transition_id
    ]
    if len(matches) != 1:
        raise GraphAdapterError(
            f"Transition ID {transition_id} is not present exactly once."
        )
    transition = matches[0]
    source = result.states[transition.source_state_id]
    target = result.states[transition.target_state_id]
    if not np.array_equal(source.active_atom_indices, target.active_atom_indices):
        raise GraphAdapterError(
            "Transition states use different active atom identities."
        )
    frame = (
        transition.collection_frame_index_before
        if coordinate_frame == "before"
        else transition.collection_frame_index_after
    )
    frame = _validated_frame_index(collection, frame)
    _validate_state_collection(collection, source, frame)
    _validate_state_collection(collection, target, frame)

    source_edges = {edge.pair: edge for edge in source.edge_keys}
    target_edges = {edge.pair: edge for edge in target.edge_keys}
    source_display = _display_shift_by_pair(collection, source, frame)
    target_display = _display_shift_by_pair(collection, target, frame)
    all_pairs = sorted(set(source_edges) | set(target_edges))
    atom_to_local = {
        int(atom): position for position, atom in enumerate(source.active_atom_indices)
    }
    selected_state = source if coordinate_frame == "before" else target
    statuses: list[str] = []
    edge_keys: list[tuple[str, int, int]] = []
    endpoints: list[tuple[int, int]] = []
    display_shifts: list[tuple[int, int, int]] = []
    source_canonical: list[tuple[int, int, int] | None] = []
    target_canonical: list[tuple[int, int, int] | None] = []
    for pair in all_pairs:
        in_source = pair in source_edges
        in_target = pair in target_edges
        status = (
            "unchanged"
            if in_source and in_target
            else "removed"
            if in_source
            else "added"
        )
        statuses.append(status)
        edge_keys.append((status, pair[0], pair[1]))
        endpoints.append((atom_to_local[pair[0]], atom_to_local[pair[1]]))
        if status == "removed":
            display_shifts.append(source_display[pair])
        elif status == "added":
            display_shifts.append(target_display[pair])
        else:
            chosen = source_display if coordinate_frame == "before" else target_display
            display_shifts.append(chosen[pair])
        source_canonical.append(source_edges[pair].image_shift if in_source else None)
        target_canonical.append(target_edges[pair].image_shift if in_target else None)

    active = source.active_atom_indices
    symbols = tuple(
        chemical_symbols[int(number)] for number in source.active_atomic_numbers
    )
    edge_source_symbols = tuple(
        chemical_symbols[int(collection.atomic_numbers[pair[0]])] for pair in all_pairs
    )
    edge_target_symbols = tuple(
        chemical_symbols[int(collection.atomic_numbers[pair[1]])] for pair in all_pairs
    )
    affected = set(transition.affected_atom_indices)
    shifts_array = np.asarray(display_shifts, dtype=np.int64).reshape((-1, 3))
    return DecoratedGraphView(
        node_keys=tuple(int(atom) for atom in active),
        edge_keys=tuple(edge_keys),
        edge_endpoints=np.asarray(endpoints, dtype=np.int64).reshape((-1, 2)),
        node_positions_3d=np.asarray(
            collection.get_wrapped_positions(frame)[active], dtype=float
        ),
        edge_image_shifts=shifts_array,
        cell=np.asarray(collection.cells[frame], dtype=float),
        pbc=np.asarray(collection.pbc, dtype=bool),
        node_attributes={
            "atom_index": np.asarray(active, dtype=np.int64),
            "atomic_number": np.asarray(source.active_atomic_numbers, dtype=np.int32),
            "symbol": symbols,
            "degree": np.asarray(selected_state.degree, dtype=np.int32),
            "component_id": np.asarray(selected_state.component_labels, dtype=np.int32),
            "affected": np.asarray(
                [int(atom) in affected for atom in active], dtype=bool
            ),
        },
        edge_attributes={
            "transition_status": tuple(statuses),
            "source_canonical_image_shift": tuple(source_canonical),
            "target_canonical_image_shift": tuple(target_canonical),
            "display_image_shift": tuple(display_shifts),
            "atom_i": np.asarray([pair[0] for pair in all_pairs], dtype=np.int64),
            "atom_j": np.asarray([pair[1] for pair in all_pairs], dtype=np.int64),
            "source_symbol": edge_source_symbols,
            "target_symbol": edge_target_symbols,
            "species_pair": tuple(
                tuple(sorted(pair))
                for pair in zip(edge_source_symbols, edge_target_symbols, strict=True)
            ),
            "periodic": np.any(shifts_array != 0, axis=1),
        },
        directed=False,
        multigraph=False,
        metadata={
            "adapter_schema_version": TRANSITION_GRAPH_ADAPTER_SCHEMA,
            "transition_id": transition.transition_id,
            "source_state_id": transition.source_state_id,
            "target_state_id": transition.target_state_id,
            "coordinate_frame": coordinate_frame,
            "collection_frame_index": frame,
            "frame_id": int(collection.frame_ids[frame]),
            "connectivity_definition_kind": result.definition.kind,
            "connectivity_consistency": result.consistency.value,
            "diagnostic_union_graph": True,
        },
    )


def plot_atomic_connectivity_2d(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityState | AtomicConnectivityResult,
    *,
    frame_index: int,
    layout: GraphLayoutOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    periodic: PeriodicDisplayOptions | None = None,
    options: Graph2DRenderOptions | None = None,
    axes: Axes | None = None,
) -> GraphRenderResult:
    """Adapt and render one atomic connectivity state."""
    view = graph_view_from_atomic_connectivity(
        collection, connectivity, frame_index=frame_index
    )
    return plot_decorated_graph_2d(
        view,
        layout=layout,
        style=style or GraphStyle.atomic_default(),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        periodic=periodic,
        options=options,
        axes=axes,
    )


def plot_connectivity_transition_2d(
    collection: AtomisticFrameCollection,
    result: AtomicConnectivityResult,
    *,
    transition_id: int,
    coordinate_frame: Literal["before", "after"] = "after",
    layout: GraphLayoutOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    periodic: PeriodicDisplayOptions | None = None,
    options: Graph2DRenderOptions | None = None,
    axes: Axes | None = None,
) -> GraphRenderResult:
    """Adapt and render one connectivity transition diagnostic graph."""
    view = graph_view_from_connectivity_transition(
        collection,
        result,
        transition_id=transition_id,
        coordinate_frame=coordinate_frame,
    )
    return plot_decorated_graph_2d(
        view,
        layout=layout,
        style=style or GraphStyle.transition_default(),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        periodic=periodic,
        options=options,
        axes=axes,
    )


def plot_atomic_connectivity_3d(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityState | AtomicConnectivityResult,
    *,
    frame_index: int,
    periodic: PeriodicDisplayOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    options: Graph3DRenderOptions | None = None,
) -> InteractiveGraphRenderResult:
    """Adapt and render one atomic-connectivity state in interactive 3-D."""
    view = graph_view_from_atomic_connectivity(
        collection, connectivity, frame_index=frame_index
    )
    return plot_decorated_graph_3d(
        view,
        periodic=periodic,
        style=style or GraphStyle.atomic_default(),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        options=options,
    )


def plot_connectivity_transition_3d(
    collection: AtomisticFrameCollection,
    result: AtomicConnectivityResult,
    *,
    transition_id: int,
    coordinate_frame: Literal["before", "after"] = "after",
    periodic: PeriodicDisplayOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    options: Graph3DRenderOptions | None = None,
) -> InteractiveGraphRenderResult:
    """Adapt and render one atomic-connectivity transition in 3-D."""
    view = graph_view_from_connectivity_transition(
        collection,
        result,
        transition_id=transition_id,
        coordinate_frame=coordinate_frame,
    )
    return plot_decorated_graph_3d(
        view,
        periodic=periodic,
        style=style or GraphStyle.transition_default(),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        options=options,
    )


__all__ = [
    "graph_view_from_atomic_connectivity",
    "graph_view_from_connectivity_transition",
    "plot_atomic_connectivity_2d",
    "plot_atomic_connectivity_3d",
    "plot_connectivity_transition_2d",
    "plot_connectivity_transition_3d",
]
