"""Visualization adapters for projected framework topologies.

This module is intentionally downstream of :mod:`mdstats.analysis.framework_topology`.
It never searches atomic paths or decides whether a framework edge exists.  It only
maps an authoritative :class:`~mdstats.analysis.FrameworkTopology` into immutable
renderer-independent graph views and reconstructs frame-local periodic geometry.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

import numpy as np
from ase.data import chemical_symbols
from matplotlib.axes import Axes

from ..analysis._neighbors import minimum_image_geometry
from ..analysis.framework_topology import (
    FrameworkEdgeKey,
    FrameworkEdgePath,
    FrameworkTopology,
)
from ..collection import AtomisticFrameCollection
from .graph_2d import (
    Graph2DRenderOptions,
    GraphLayoutOptions,
    GraphRenderResult,
    plot_decorated_graph_2d,
)
from .graph_3d import (
    Graph3DRenderOptions,
    InteractiveGraphRenderResult,
    plot_decorated_graph_3d,
)
from .graph_errors import GraphAdapterError
from .graph_styles import GraphStyle
from .graph_view import (
    DecoratedGraphView,
    GraphComplexityPolicy,
    GraphFilter,
    GraphFocus,
)
from .periodic_graph import PeriodicDisplayOptions

FRAMEWORK_GRAPH_ADAPTER_SCHEMA = "mdstats.framework-topology-graph-view.v2"
FRAMEWORK_PATH_GRAPH_ADAPTER_SCHEMA = "mdstats.framework-topology-path-view.v2"


class FrameworkGraphDisplayMode(str, Enum):
    """Available framework-topology visualization representations."""

    PROJECTED = "projected"
    ATOMIC_PATHS = "atomic_paths"


@dataclass(frozen=True, order=True, slots=True)
class FrameworkPathSegmentKey:
    """Stable identity of one retained atomic-path segment.

    Segment keys are scoped by their authoritative projected edge.  Therefore two
    projected edges may retain separate diagnostic segments even when they connect
    the same canonical atom pair.
    """

    framework_edge_key: FrameworkEdgeKey
    segment_index: int
    atom_i: int
    atom_j: int

    def __post_init__(self) -> None:
        if not isinstance(self.framework_edge_key, FrameworkEdgeKey):
            raise GraphAdapterError("framework_edge_key must be a FrameworkEdgeKey.")
        for name in ("segment_index", "atom_i", "atom_j"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
                raise GraphAdapterError(f"{name} must be a nonnegative integer.")
            value = int(value)
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        if self.atom_i == self.atom_j:
            raise GraphAdapterError("Atomic-path segments require distinct atoms.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "framework_edge_key": self.framework_edge_key.to_dict(),
            "segment_index": self.segment_index,
            "atom_i": self.atom_i,
            "atom_j": self.atom_j,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameworkPathSegmentKey":
        return cls(
            framework_edge_key=FrameworkEdgeKey.from_dict(
                payload["framework_edge_key"]
            ),
            segment_index=int(payload["segment_index"]),
            atom_i=int(payload["atom_i"]),
            atom_j=int(payload["atom_j"]),
        )


def _coerce_display_mode(
    value: FrameworkGraphDisplayMode | str,
) -> FrameworkGraphDisplayMode:
    if isinstance(value, FrameworkGraphDisplayMode):
        return value
    try:
        return FrameworkGraphDisplayMode(str(value))
    except ValueError as exc:
        raise GraphAdapterError(
            "display_mode must be 'projected' or 'atomic_paths'."
        ) from exc


def _validated_frame_index(
    collection: AtomisticFrameCollection, frame_index: int
) -> int:
    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    if isinstance(frame_index, bool) or not isinstance(frame_index, (int, np.integer)):
        raise GraphAdapterError("frame_index must be an integer collection position.")
    frame = int(frame_index)
    if frame < 0 or frame >= collection.n_frames:
        raise GraphAdapterError(
            f"frame_index={frame} is outside [0, {collection.n_frames})."
        )
    return frame


def _validate_topology_collection(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if not isinstance(topology, FrameworkTopology):
        raise TypeError("topology must be a FrameworkTopology.")
    frame = _validated_frame_index(collection, frame_index)
    if not np.array_equal(topology.pbc, collection.pbc):
        raise GraphAdapterError(
            "Framework topology PBC flags do not match the collection."
        )
    active = topology.resolved_roles.active_atom_indices
    if active.size == 0 or int(active[-1]) >= collection.n_atoms:
        raise GraphAdapterError(
            "Framework topology contains atom indices outside the collection."
        )
    expected_numbers = collection.atomic_numbers[active]
    if not np.array_equal(
        topology.resolved_roles.active_atomic_numbers, expected_numbers
    ):
        raise GraphAdapterError(
            "Framework topology atomic numbers do not match the collection ordering."
        )
    retained_atoms = set(int(x) for x in topology.vertex_atom_indices)
    for edge in topology.edges:
        retained_atoms.update(edge.atomic_path_indices)
    if retained_atoms and max(retained_atoms) >= collection.n_atoms:
        raise GraphAdapterError(
            "A retained framework atomic path references an atom outside the collection."
        )
    cell = np.asarray(collection.cells[frame], dtype=float)
    if (
        cell.shape != (3, 3)
        or np.any(~np.isfinite(cell))
        or abs(float(np.linalg.det(cell))) <= 1.0e-12
    ):
        raise GraphAdapterError("Selected frame cell must be finite and nonsingular.")
    positions = np.asarray(collection.get_wrapped_positions(frame), dtype=float)
    if positions.shape != (collection.n_atoms, 3) or np.any(~np.isfinite(positions)):
        raise GraphAdapterError("Selected frame positions are malformed or nonfinite.")
    return positions, cell, np.asarray(collection.pbc, dtype=bool)


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
    fractional = raw @ np.linalg.inv(cell)
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


def _path_display_shifts(
    positions: np.ndarray,
    edge: FrameworkEdgePath,
    *,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, bool]:
    segment_shifts: list[np.ndarray] = []
    ambiguous = False
    for source, target in zip(
        edge.atomic_path_indices[:-1], edge.atomic_path_indices[1:], strict=True
    ):
        shift, tie = _minimum_image_shift(positions, source, target, cell=cell, pbc=pbc)
        segment_shifts.append(shift)
        ambiguous |= tie
    segments = np.asarray(segment_shifts, dtype=np.int64).reshape((-1, 3))
    total = (
        np.sum(segments, axis=0, dtype=np.int64)
        if len(segments)
        else np.zeros(3, dtype=np.int64)
    )
    return segments, total, ambiguous


def _oriented_shift(
    edge: FrameworkEdgePath,
    shift: np.ndarray,
    source: int,
    target: int,
) -> np.ndarray:
    if source == edge.key.vertex_i and target == edge.key.vertex_j:
        return shift
    if source == edge.key.vertex_j and target == edge.key.vertex_i:
        return -shift
    raise GraphAdapterError("Projected edge traversal endpoint mismatch.")


def _reconstruct_projected_display_geometry(
    topology: FrameworkTopology,
    positions: np.ndarray,
    *,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> tuple[np.ndarray, tuple[np.ndarray, ...], tuple[str, ...]]:
    """Reconstruct frame-local projected and segment shifts.

    The stored atomic path determines a selected-frame path shift for each edge.
    A deterministic projected-vertex gauge maps canonical framework shifts into the
    selected wrapping gauge.  Equality against every retained path is then checked,
    including non-tree winding edges.
    """
    # HARDEN1: batch every retained path segment for this frame through one
    # exact triclinic MIC call.  The previous implementation invoked the same
    # kernel once per segment, multiplying Python/cell-validation overhead on
    # long trajectories.  MIC vectors are independent, so batching is exactly
    # equivalent and preserves the integer image shifts pointwise.
    edge_slices: list[tuple[int, int]] = []
    sources: list[int] = []
    targets: list[int] = []
    for edge in topology.edges:
        start = len(sources)
        for source, target in zip(
            edge.atomic_path_indices[:-1], edge.atomic_path_indices[1:], strict=True
        ):
            sources.append(int(source))
            targets.append(int(target))
        edge_slices.append((start, len(sources)))

    if sources:
        source_array = np.asarray(sources, dtype=np.int64)
        target_array = np.asarray(targets, dtype=np.int64)
        raw = np.asarray(positions[target_array] - positions[source_array], dtype=np.float64)
        _vectors, _distances, all_shifts = minimum_image_geometry(raw, cell=cell, pbc=pbc)
        all_shifts = np.asarray(all_shifts, dtype=np.int64)
        fractional = raw @ np.linalg.inv(cell)
        ties = np.any(
            pbc[None, :]
            & np.isclose(
                np.abs(fractional - np.rint(fractional)),
                0.5,
                rtol=0.0,
                atol=1.0e-10,
            ),
            axis=1,
        )
    else:
        all_shifts = np.empty((0, 3), dtype=np.int64)
        ties = np.empty(0, dtype=bool)

    path_segments: list[np.ndarray] = []
    path_totals: list[np.ndarray] = []
    ambiguous = bool(np.any(ties))
    for start, stop in edge_slices:
        segments = np.asarray(all_shifts[start:stop], dtype=np.int64).reshape((-1, 3))
        path_segments.append(segments)
        path_totals.append(
            np.sum(segments, axis=0, dtype=np.int64)
            if len(segments)
            else np.zeros(3, dtype=np.int64)
        )

    vertices = [int(x) for x in topology.vertex_atom_indices]
    adjacency: dict[int, list[tuple[int, int]]] = {vertex: [] for vertex in vertices}
    for edge_index, edge in enumerate(topology.edges):
        adjacency[edge.key.vertex_i].append((edge.key.vertex_j, edge_index))
        adjacency[edge.key.vertex_j].append((edge.key.vertex_i, edge_index))
    for vertex in adjacency:
        adjacency[vertex].sort(key=lambda item: (item[0], item[1]))

    gauge: dict[int, np.ndarray] = {}
    for root in vertices:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            source = queue.popleft()
            for target, edge_index in adjacency[source]:
                if target in gauge:
                    continue
                edge = topology.edges[edge_index]
                canonical = _oriented_shift(
                    edge,
                    np.asarray(edge.key.image_shift, dtype=np.int64),
                    source,
                    target,
                )
                frame_shift = _oriented_shift(
                    edge, path_totals[edge_index], source, target
                )
                gauge[target] = gauge[source] + frame_shift - canonical
                queue.append(target)

    display = np.empty((topology.n_edges, 3), dtype=np.int64)
    for edge_index, edge in enumerate(topology.edges):
        canonical = np.asarray(edge.key.image_shift, dtype=np.int64)
        reconstructed = canonical - gauge[edge.key.vertex_i] + gauge[edge.key.vertex_j]
        if not np.array_equal(reconstructed, path_totals[edge_index]):
            raise GraphAdapterError(
                "Selected frame atomic paths are incompatible with the canonical "
                f"framework winding for edge {edge.key!r}."
            )
        display[edge_index] = reconstructed
    if np.any(display[:, ~pbc] != 0):
        raise GraphAdapterError(
            "Reconstructed framework shifts are nonzero on a nonperiodic axis."
        )
    for edge, shift in zip(topology.edges, display, strict=True):
        vector = (
            positions[edge.key.vertex_j] + shift @ cell - positions[edge.key.vertex_i]
        )
        if np.any(~np.isfinite(vector)):
            raise GraphAdapterError(
                "Reconstructed projected framework edge vector is nonfinite."
            )
    warnings = (
        (
            (
                "A minimum-image tie was encountered while reconstructing retained "
                "framework atomic paths."
            ),
        )
        if ambiguous
        else ()
    )
    return display, tuple(path_segments), warnings


def _parallel_metadata(
    topology: FrameworkTopology,
) -> tuple[np.ndarray, np.ndarray]:
    by_pair: dict[tuple[int, int], list[int]] = defaultdict(list)
    for index, edge in enumerate(topology.edges):
        by_pair[(edge.key.vertex_i, edge.key.vertex_j)].append(index)
    multiplicity = np.ones(topology.n_edges, dtype=np.int32)
    rank = np.zeros(topology.n_edges, dtype=np.int32)
    for indices in by_pair.values():
        for local_rank, edge_index in enumerate(indices):
            multiplicity[edge_index] = len(indices)
            rank[edge_index] = local_rank
    return multiplicity, rank


def _projected_graph_view(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_index: int,
    positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    display_shifts: np.ndarray,
    adapter_warnings: tuple[str, ...],
) -> DecoratedGraphView:
    vertices = topology.vertex_atom_indices
    atom_to_local = {int(atom): index for index, atom in enumerate(vertices)}
    endpoints = np.asarray(
        [
            (atom_to_local[edge.key.vertex_i], atom_to_local[edge.key.vertex_j])
            for edge in topology.edges
        ],
        dtype=np.int64,
    ).reshape((-1, 2))
    symbols = tuple(
        chemical_symbols[int(number)] for number in topology.vertex_atomic_numbers
    )
    multiplicity, rank = _parallel_metadata(topology)
    source_symbols = tuple(
        chemical_symbols[int(collection.atomic_numbers[edge.key.vertex_i])]
        for edge in topology.edges
    )
    target_symbols = tuple(
        chemical_symbols[int(collection.atomic_numbers[edge.key.vertex_j])]
        for edge in topology.edges
    )
    return DecoratedGraphView(
        node_keys=tuple(int(atom) for atom in vertices),
        edge_keys=topology.edge_keys,
        edge_endpoints=endpoints,
        node_positions_3d=np.asarray(positions[vertices], dtype=float),
        edge_image_shifts=display_shifts,
        cell=cell,
        pbc=pbc,
        node_attributes={
            "atom_index": np.asarray(vertices, dtype=np.int64),
            "atomic_number": np.asarray(topology.vertex_atomic_numbers, dtype=np.int32),
            "symbol": symbols,
            "framework_role": tuple("vertex" for _ in vertices),
            "framework_vertex_index": np.arange(topology.n_vertices, dtype=np.int32),
            "projected_degree": np.asarray(topology.degree, dtype=np.int32),
            "component_id": np.asarray(topology.component_labels, dtype=np.int32),
        },
        edge_attributes={
            "vertex_i": np.asarray(
                [edge.key.vertex_i for edge in topology.edges], dtype=np.int64
            ),
            "vertex_j": np.asarray(
                [edge.key.vertex_j for edge in topology.edges], dtype=np.int64
            ),
            "source_symbol": source_symbols,
            "target_symbol": target_symbols,
            "species_pair": tuple(
                tuple(sorted(pair))
                for pair in zip(source_symbols, target_symbols, strict=True)
            ),
            "rule_id": tuple(edge.key.rule_id for edge in topology.edges),
            "edge_kind": tuple(edge.edge_kind for edge in topology.edges),
            "atomic_path_indices": tuple(
                edge.atomic_path_indices for edge in topology.edges
            ),
            "reverse_atomic_path_indices": tuple(
                edge.oriented(-1).atomic_path_indices for edge in topology.edges
            ),
            "canonical_path_symbols": tuple(
                tuple(
                    chemical_symbols[int(collection.atomic_numbers[index])]
                    for index in edge.atomic_path_indices
                )
                for edge in topology.edges
            ),
            "reverse_path_symbols": tuple(
                tuple(
                    chemical_symbols[int(collection.atomic_numbers[index])]
                    for index in edge.oriented(-1).atomic_path_indices
                )
                for edge in topology.edges
            ),
            "canonical_orientation": tuple(
                "vertex_i_to_vertex_j" for _ in topology.edges
            ),
            "orientation_aware": np.ones(topology.n_edges, dtype=bool),
            "internal_linker_indices": tuple(
                edge.key.internal_linker_indices for edge in topology.edges
            ),
            "internal_linker_symbols": tuple(
                tuple(
                    chemical_symbols[int(number)]
                    for number in edge.internal_linker_atomic_numbers
                )
                for edge in topology.edges
            ),
            "linker_count": np.asarray(
                [len(edge.key.internal_linker_indices) for edge in topology.edges],
                dtype=np.int32,
            ),
            "path_segment_count": np.asarray(
                [len(edge.atomic_path_indices) - 1 for edge in topology.edges],
                dtype=np.int32,
            ),
            "raw_image_shift": tuple(edge.raw_image_shift for edge in topology.edges),
            "canonical_image_shift": tuple(
                edge.key.image_shift for edge in topology.edges
            ),
            "display_image_shift": tuple(
                tuple(int(x) for x in shift) for shift in display_shifts
            ),
            "periodic": np.any(display_shifts != 0, axis=1),
            "parallel_multiplicity": multiplicity,
            "parallel_rank": rank,
        },
        directed=False,
        multigraph=True,
        metadata={
            "adapter_schema_version": FRAMEWORK_GRAPH_ADAPTER_SCHEMA,
            "collection_frame_index": frame_index,
            "frame_id": int(collection.frame_ids[frame_index]),
            "display_mode": FrameworkGraphDisplayMode.PROJECTED.value,
            "source_framework_graph_digest": topology.graph_digest,
            "source_framework_topology_digest": topology.digest,
            "source_connectivity_digest": topology.source_connectivity_digest,
            "mapping_digest": topology.mapping_digest,
            "n_source_vertices": topology.n_vertices,
            "n_source_edges": topology.n_edges,
            "parallel_vertex_pair_count": topology.projection_report.parallel_vertex_pair_count,
            "self_image_edge_count": topology.projection_report.self_image_edge_count,
            "frame_shift_reconstruction": "retained-path gauge reconciliation",
            "edge_semantics": "undirected adjacency with orientation-aware path decoration",
            "adapter_warnings": adapter_warnings,
        },
    )


def _canonical_segment_shifts(edge: FrameworkEdgePath) -> np.ndarray:
    offsets = [
        np.zeros(3, dtype=np.int64),
        *(
            np.asarray(offset, dtype=np.int64)
            for offset in edge.key.internal_linker_image_offsets
        ),
        np.asarray(edge.key.image_shift, dtype=np.int64),
    ]
    shifts = np.asarray(
        [right - left for left, right in zip(offsets[:-1], offsets[1:], strict=True)],
        dtype=np.int64,
    ).reshape((-1, 3))
    if not np.array_equal(
        np.sum(shifts, axis=0, dtype=np.int64),
        np.asarray(edge.key.image_shift, dtype=np.int64),
    ):
        raise GraphAdapterError(
            "Canonical diagnostic segment shifts do not sum to the parent edge shift."
        )
    return shifts


def _segment_kind(
    segment_index: int,
    n_segments: int,
    n_linkers: int,
) -> str:
    if n_linkers == 0:
        return "direct_vertex"
    if segment_index == 0:
        return "vertex_linker"
    if segment_index == n_segments - 1:
        return "linker_vertex"
    return "linker_linker"


def _atomic_path_graph_view(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_index: int,
    positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    projected_display_shifts: np.ndarray,
    path_segment_shifts: tuple[np.ndarray, ...],
    adapter_warnings: tuple[str, ...],
) -> DecoratedGraphView:
    used_linkers = sorted(
        {
            int(atom)
            for edge in topology.edges
            for atom in edge.key.internal_linker_indices
        }
    )
    vertices = [int(atom) for atom in topology.vertex_atom_indices]
    node_atoms = sorted(set(vertices) | set(used_linkers))
    atom_to_local = {atom: position for position, atom in enumerate(node_atoms)}
    vertex_to_position = {atom: position for position, atom in enumerate(vertices)}
    role_by_atom = {
        int(atom): role
        for atom, role in zip(
            topology.resolved_roles.active_atom_indices,
            topology.resolved_roles.roles,
            strict=True,
        )
    }
    active_number_by_atom = {
        int(atom): int(number)
        for atom, number in zip(
            topology.resolved_roles.active_atom_indices,
            topology.resolved_roles.active_atomic_numbers,
            strict=True,
        )
    }
    linker_degree_by_atom = {
        int(atom): int(degree)
        for atom, degree in zip(
            topology.projection_report.linker_atom_indices,
            topology.projection_report.linker_framework_degree,
            strict=True,
        )
    }
    membership = Counter(
        int(atom)
        for edge in topology.edges
        for atom in edge.key.internal_linker_indices
    )
    component_by_atom = {
        atom: int(topology.component_labels[position])
        for atom, position in vertex_to_position.items()
    }
    for edge in topology.edges:
        component = component_by_atom[edge.key.vertex_i]
        if component_by_atom[edge.key.vertex_j] != component:
            raise GraphAdapterError(
                "A projected edge connects vertices assigned to different components."
            )
        for linker in edge.key.internal_linker_indices:
            previous = component_by_atom.setdefault(int(linker), component)
            if previous != component:
                raise GraphAdapterError(
                    "A retained linker is assigned to incompatible projected components."
                )

    edge_keys: list[FrameworkPathSegmentKey] = []
    endpoints: list[tuple[int, int]] = []
    display_shifts: list[tuple[int, int, int]] = []
    canonical_shifts: list[tuple[int, int, int]] = []
    segment_indices: list[int] = []
    atom_i_values: list[int] = []
    atom_j_values: list[int] = []
    source_symbols: list[str] = []
    target_symbols: list[str] = []
    segment_kinds: list[str] = []
    parent_vertex_i: list[int] = []
    parent_vertex_j: list[int] = []
    parent_rule_id: list[str] = []
    parent_edge_kind: list[str] = []
    parent_path: list[tuple[int, ...]] = []
    parent_reverse_path: list[tuple[int, ...]] = []
    parent_path_symbols: list[tuple[str, ...]] = []
    parent_reverse_path_symbols: list[tuple[str, ...]] = []
    parent_shift: list[tuple[int, int, int]] = []

    for edge_index, edge in enumerate(topology.edges):
        canonical = _canonical_segment_shifts(edge)
        frame_segments = path_segment_shifts[edge_index]
        if canonical.shape != frame_segments.shape:
            raise GraphAdapterError(
                "Canonical and frame-local path segment arrays are misaligned."
            )
        if not np.array_equal(
            np.sum(frame_segments, axis=0, dtype=np.int64),
            projected_display_shifts[edge_index],
        ):
            raise GraphAdapterError(
                "Diagnostic segment shifts do not sum to the projected display shift."
            )
        n_segments = len(edge.atomic_path_indices) - 1
        n_linkers = len(edge.key.internal_linker_indices)
        for segment_index, (source, target) in enumerate(
            zip(
                edge.atomic_path_indices[:-1],
                edge.atomic_path_indices[1:],
                strict=True,
            )
        ):
            edge_keys.append(
                FrameworkPathSegmentKey(
                    framework_edge_key=edge.key,
                    segment_index=segment_index,
                    atom_i=int(source),
                    atom_j=int(target),
                )
            )
            endpoints.append((atom_to_local[int(source)], atom_to_local[int(target)]))
            display_shifts.append(tuple(int(x) for x in frame_segments[segment_index]))
            canonical_shifts.append(tuple(int(x) for x in canonical[segment_index]))
            segment_indices.append(segment_index)
            atom_i_values.append(int(source))
            atom_j_values.append(int(target))
            source_symbols.append(
                chemical_symbols[int(collection.atomic_numbers[int(source)])]
            )
            target_symbols.append(
                chemical_symbols[int(collection.atomic_numbers[int(target)])]
            )
            segment_kinds.append(_segment_kind(segment_index, n_segments, n_linkers))
            parent_vertex_i.append(edge.key.vertex_i)
            parent_vertex_j.append(edge.key.vertex_j)
            parent_rule_id.append(edge.key.rule_id)
            parent_edge_kind.append(edge.edge_kind)
            parent_path.append(edge.atomic_path_indices)
            reverse_path = edge.oriented(-1).atomic_path_indices
            parent_reverse_path.append(reverse_path)
            parent_path_symbols.append(
                tuple(
                    chemical_symbols[int(collection.atomic_numbers[index])]
                    for index in edge.atomic_path_indices
                )
            )
            parent_reverse_path_symbols.append(
                tuple(
                    chemical_symbols[int(collection.atomic_numbers[index])]
                    for index in reverse_path
                )
            )
            parent_shift.append(edge.key.image_shift)

    shifts_array = np.asarray(display_shifts, dtype=np.int64).reshape((-1, 3))
    numbers = np.asarray(
        [active_number_by_atom[atom] for atom in node_atoms], dtype=np.int32
    )
    roles = tuple(role_by_atom[atom].value for atom in node_atoms)
    return DecoratedGraphView(
        node_keys=tuple(node_atoms),
        edge_keys=tuple(edge_keys),
        edge_endpoints=np.asarray(endpoints, dtype=np.int64).reshape((-1, 2)),
        node_positions_3d=np.asarray(positions[node_atoms], dtype=float),
        edge_image_shifts=shifts_array,
        cell=cell,
        pbc=pbc,
        node_attributes={
            "atom_index": np.asarray(node_atoms, dtype=np.int64),
            "atomic_number": numbers,
            "symbol": tuple(chemical_symbols[int(number)] for number in numbers),
            "framework_role": roles,
            "framework_vertex_index": np.asarray(
                [vertex_to_position.get(atom, -1) for atom in node_atoms],
                dtype=np.int32,
            ),
            "projected_degree": np.asarray(
                [
                    int(topology.degree[vertex_to_position[atom]])
                    if atom in vertex_to_position
                    else 0
                    for atom in node_atoms
                ],
                dtype=np.int32,
            ),
            "linker_framework_degree": np.asarray(
                [linker_degree_by_atom.get(atom, 0) for atom in node_atoms],
                dtype=np.int32,
            ),
            "projected_path_membership_count": np.asarray(
                [membership.get(atom, 0) for atom in node_atoms], dtype=np.int32
            ),
            "component_id": np.asarray(
                [component_by_atom[atom] for atom in node_atoms], dtype=np.int32
            ),
        },
        edge_attributes={
            "segment_index": np.asarray(segment_indices, dtype=np.int32),
            "atom_i": np.asarray(atom_i_values, dtype=np.int64),
            "atom_j": np.asarray(atom_j_values, dtype=np.int64),
            "source_symbol": tuple(source_symbols),
            "target_symbol": tuple(target_symbols),
            "species_pair": tuple(
                tuple(sorted(pair))
                for pair in zip(source_symbols, target_symbols, strict=True)
            ),
            "segment_kind": tuple(segment_kinds),
            "parent_vertex_i": np.asarray(parent_vertex_i, dtype=np.int64),
            "parent_vertex_j": np.asarray(parent_vertex_j, dtype=np.int64),
            "parent_rule_id": tuple(parent_rule_id),
            "rule_id": tuple(parent_rule_id),
            "parent_edge_kind": tuple(parent_edge_kind),
            "edge_kind": tuple(parent_edge_kind),
            "parent_atomic_path_indices": tuple(parent_path),
            "parent_reverse_atomic_path_indices": tuple(parent_reverse_path),
            "parent_canonical_path_symbols": tuple(parent_path_symbols),
            "parent_reverse_path_symbols": tuple(parent_reverse_path_symbols),
            "parent_canonical_orientation": tuple(
                "vertex_i_to_vertex_j" for _ in edge_keys
            ),
            "parent_orientation_aware": np.ones(len(edge_keys), dtype=bool),
            "parent_canonical_image_shift": tuple(parent_shift),
            "canonical_segment_image_shift": tuple(canonical_shifts),
            "display_image_shift": tuple(display_shifts),
            "periodic": np.any(shifts_array != 0, axis=1),
        },
        directed=False,
        multigraph=True,
        metadata={
            "adapter_schema_version": FRAMEWORK_PATH_GRAPH_ADAPTER_SCHEMA,
            "collection_frame_index": frame_index,
            "frame_id": int(collection.frame_ids[frame_index]),
            "display_mode": FrameworkGraphDisplayMode.ATOMIC_PATHS.value,
            "source_framework_graph_digest": topology.graph_digest,
            "source_framework_topology_digest": topology.digest,
            "source_connectivity_digest": topology.source_connectivity_digest,
            "mapping_digest": topology.mapping_digest,
            "n_source_vertices": topology.n_vertices,
            "n_source_edges": topology.n_edges,
            "displayed_linker_count": len(used_linkers),
            "displayed_segment_count": len(edge_keys),
            "frame_shift_reconstruction": "retained segment minimum-image geometry",
            "edge_semantics": "undirected adjacency with canonical path-segment orientation",
            "adapter_warnings": adapter_warnings,
        },
    )


def graph_view_from_framework_topology(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_index: int,
    display_mode: FrameworkGraphDisplayMode | str = FrameworkGraphDisplayMode.PROJECTED,
) -> DecoratedGraphView:
    """Adapt one authoritative framework topology for generic visualization.

    No atomic connectivity or framework path search is performed.  The selected
    frame supplies only Cartesian coordinates and a wrapping gauge for display.
    """
    mode = _coerce_display_mode(display_mode)
    positions, cell, pbc = _validate_topology_collection(
        collection, topology, frame_index=frame_index
    )
    projected_shifts, segment_shifts, adapter_warnings = (
        _reconstruct_projected_display_geometry(topology, positions, cell=cell, pbc=pbc)
    )
    if mode is FrameworkGraphDisplayMode.PROJECTED:
        return _projected_graph_view(
            collection,
            topology,
            frame_index=frame_index,
            positions=positions,
            cell=cell,
            pbc=pbc,
            display_shifts=projected_shifts,
            adapter_warnings=adapter_warnings,
        )
    return _atomic_path_graph_view(
        collection,
        topology,
        frame_index=frame_index,
        positions=positions,
        cell=cell,
        pbc=pbc,
        projected_display_shifts=projected_shifts,
        path_segment_shifts=segment_shifts,
        adapter_warnings=adapter_warnings,
    )


def plot_framework_topology_2d(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_index: int,
    display_mode: FrameworkGraphDisplayMode | str = FrameworkGraphDisplayMode.PROJECTED,
    layout: GraphLayoutOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    periodic: PeriodicDisplayOptions | None = None,
    options: Graph2DRenderOptions | None = None,
    axes: Axes | None = None,
) -> GraphRenderResult:
    """Adapt and render a projected or atomic-path framework graph in 2-D."""
    mode = _coerce_display_mode(display_mode)
    view = graph_view_from_framework_topology(
        collection,
        topology,
        frame_index=frame_index,
        display_mode=mode,
    )
    return plot_decorated_graph_2d(
        view,
        layout=layout,
        style=style
        or GraphStyle.framework_default(
            diagnostic=mode is FrameworkGraphDisplayMode.ATOMIC_PATHS
        ),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        periodic=periodic,
        options=options,
        axes=axes,
    )


def plot_framework_topology_3d(
    collection: AtomisticFrameCollection,
    topology: FrameworkTopology,
    *,
    frame_index: int,
    display_mode: FrameworkGraphDisplayMode | str = FrameworkGraphDisplayMode.PROJECTED,
    periodic: PeriodicDisplayOptions | None = None,
    style: GraphStyle | None = None,
    focus: GraphFocus | None = None,
    graph_filter: GraphFilter | None = None,
    complexity_policy: GraphComplexityPolicy | None = None,
    options: Graph3DRenderOptions | None = None,
) -> InteractiveGraphRenderResult:
    """Adapt and render a projected or atomic-path framework graph in 3-D."""
    mode = _coerce_display_mode(display_mode)
    view = graph_view_from_framework_topology(
        collection,
        topology,
        frame_index=frame_index,
        display_mode=mode,
    )
    if options is None:
        options = Graph3DRenderOptions(
            edge_color_mode=(
                "midpoint_split"
                if mode is FrameworkGraphDisplayMode.ATOMIC_PATHS
                else "constant"
            )
        )
    return plot_decorated_graph_3d(
        view,
        periodic=periodic,
        style=style
        or GraphStyle.framework_default(
            diagnostic=mode is FrameworkGraphDisplayMode.ATOMIC_PATHS
        ),
        focus=focus,
        graph_filter=graph_filter,
        complexity_policy=complexity_policy,
        options=options,
    )
