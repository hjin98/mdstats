"""Periodic cell-aware meshing for block-sparse density fields.

Architecture gate LD2-B extracts sparse triangular density shells on logical
cells.  Every candidate cell is owned and contoured exactly once with the
Lewiner marching-cubes implementation supplied by scikit-image.  Lifted
component charts, torus-winding diagnostics, whole-triangle canonical clipping,
and periodic seam validation are project-specific mdstats policies.

Marching cubes follows Lorensen and Cline (SIGGRAPH 1987,
DOI: 10.1145/37402.37422); the topologically consistent case resolution follows
Lewiner et al. (Journal of Graphics Tools 8, 1-15, 2003,
DOI: 10.1080/10867651.2003.10487582).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from itertools import product
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from .density_block_sparse import PeriodicBlockScalarField3D
from .density_packed_field import PeriodicPackedBlockScalarField3D
from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_mesh_contracts import (
    DensityMeshFaceContract,
    evaluate_density_mesh_face_contract,
    legacy_standalone_face_contract,
)
from .density_node_cloud import DensityNodeCloud3D, prepare_density_node_cloud
from .runtime_resources import resolve_density_resource_limits
from .graph_errors import (
    GraphAdapterError,
    GraphComplexityError,
    GraphStyleError,
    GraphUnsupportedFeatureError,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

SPARSE_MESH_CANDIDATE_SCHEMA = "mdstats.sparse-mesh-candidates.v1"
SPARSE_MESH_COMPONENT_SCHEMA = "mdstats.sparse-mesh-component.v1"
SPARSE_MESH_RESOURCES_SCHEMA = "mdstats.sparse-mesh-resources.v1"
SPARSE_MESH_TOPOLOGY_SCHEMA = "mdstats.sparse-mesh-topology.v1"
SPARSE_DENSITY_MESH_SCHEMA = "mdstats.periodic-sparse-density-mesh.v1"
SPARSE_DENSITY_SURFACE_SCHEMA = "mdstats.sparse-density-surface.v1"

DEFAULT_MAX_CANDIDATE_CELLS = 4_000_000
DEFAULT_MAX_RAW_FACES = 20_000_000
DEFAULT_MAX_RAW_VERTICES = 60_000_000
DEFAULT_MAX_MESH_WORKSPACE_BYTES = 512_000_000
DEFAULT_MAX_DENSE_FALLBACK_NODES = 4_000_000

_CORNERS = np.asarray(tuple(product((0, 1), repeat=3)), dtype=np.int64)
_NEIGHBOR_STEPS = np.asarray(
    ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)),
    dtype=np.int64,
)


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _readonly(value: Any, dtype: Any, *, ndim: int, name: str) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise GraphAdapterError(f"{name} must be {ndim}-dimensional.")
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain finite values.")
    array.setflags(write=False)
    return array


def _shape3(value: Sequence[int], *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError(f"{name} must contain three entries.")
    return tuple(_positive_int(item, name=f"{name} entry") for item in value)  # type: ignore[return-value]


def _flat_indices(coordinates: IntArray, shape: tuple[int, int, int]) -> IntArray:
    result = np.ravel_multi_index(
        (coordinates[:, 0], coordinates[:, 1], coordinates[:, 2]), shape, order="C"
    ).astype(np.int64, copy=False)
    return result


def _coordinates(flat: IntArray, shape: tuple[int, int, int]) -> IntArray:
    return np.column_stack(np.unravel_index(flat, shape, order="C")).astype(
        np.int64, copy=False
    )


@dataclass(frozen=True, slots=True)
class SparseMeshCandidateCells:
    """Sorted periodic logical cells whose corners cross one contour level."""

    logical_grid_shape: tuple[int, int, int]
    scientific_hdr_threshold: float
    render_level: float
    flat_indices: IntArray
    cell_indices: IntArray
    adjacent_cell_count: int
    planning_bytes: int
    schema_version: str = SPARSE_MESH_CANDIDATE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_MESH_CANDIDATE_SCHEMA:
            raise GraphAdapterError("Unsupported sparse-mesh-candidate schema.")
        shape = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        flat = _readonly(self.flat_indices, np.int64, ndim=1, name="flat_indices")
        cells = _readonly(self.cell_indices, np.int64, ndim=2, name="cell_indices")
        if cells.shape != (flat.size, 3):
            raise GraphAdapterError("cell_indices must have shape (n_cells, 3).")
        if flat.size and (np.any(flat[1:] <= flat[:-1]) or int(flat[0]) < 0):
            raise GraphAdapterError("Candidate cells must be strictly ordered.")
        if flat.size and int(flat[-1]) >= int(np.prod(shape, dtype=object)):
            raise GraphAdapterError("Candidate cell lies outside logical lattice.")
        if flat.size and not np.array_equal(_coordinates(flat, shape), cells):
            raise GraphAdapterError("Candidate cell coordinates and flat indices disagree.")
        scientific = float(self.scientific_hdr_threshold)
        render = float(self.render_level)
        if not np.isfinite(scientific) or scientific <= 0.0:
            raise GraphAdapterError("scientific_hdr_threshold must be positive.")
        if not np.isfinite(render) or render <= 0.0:
            raise GraphAdapterError("render_level must be positive.")
        object.__setattr__(self, "logical_grid_shape", shape)
        object.__setattr__(self, "flat_indices", flat)
        object.__setattr__(self, "cell_indices", cells)
        object.__setattr__(self, "scientific_hdr_threshold", scientific)
        object.__setattr__(self, "render_level", render)
        object.__setattr__(
            self,
            "adjacent_cell_count",
            _positive_int(self.adjacent_cell_count, name="adjacent_cell_count", minimum=0),
        )
        object.__setattr__(
            self,
            "planning_bytes",
            _positive_int(self.planning_bytes, name="planning_bytes", minimum=0),
        )

    @property
    def candidate_cell_count(self) -> int:
        return int(self.flat_indices.size)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "logical_grid_shape": list(self.logical_grid_shape),
            "scientific_hdr_threshold": self.scientific_hdr_threshold,
            "render_level": self.render_level,
            "candidate_cell_count": self.candidate_cell_count,
            "adjacent_cell_count": self.adjacent_cell_count,
            "planning_bytes": self.planning_bytes,
        }


@dataclass(frozen=True, slots=True)
class LiftedSparseMeshComponent:
    """One deterministic face-connected periodic candidate-cell component."""

    component_index: int
    canonical_cell_indices: IntArray
    lifted_cell_indices: IntArray
    winding_vectors: tuple[tuple[int, int, int], ...] = ()
    schema_version: str = SPARSE_MESH_COMPONENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_MESH_COMPONENT_SCHEMA:
            raise GraphAdapterError("Unsupported sparse-mesh-component schema.")
        canonical = _readonly(
            self.canonical_cell_indices, np.int64, ndim=2, name="canonical_cell_indices"
        )
        lifted = _readonly(
            self.lifted_cell_indices, np.int64, ndim=2, name="lifted_cell_indices"
        )
        if canonical.shape != lifted.shape or canonical.shape[1:] != (3,):
            raise GraphAdapterError("Component cell arrays must align with shape (n, 3).")
        winding = tuple(sorted({tuple(int(x) for x in vector) for vector in self.winding_vectors}))
        winding = tuple(vector for vector in winding if vector != (0, 0, 0))
        object.__setattr__(self, "component_index", _positive_int(self.component_index, name="component_index", minimum=0))
        object.__setattr__(self, "canonical_cell_indices", canonical)
        object.__setattr__(self, "lifted_cell_indices", lifted)
        object.__setattr__(self, "winding_vectors", winding)

    @property
    def cell_count(self) -> int:
        return int(self.canonical_cell_indices.shape[0])

    @property
    def is_winding(self) -> bool:
        return bool(self.winding_vectors)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "component_index": self.component_index,
            "cell_count": self.cell_count,
            "winding_vectors": [list(value) for value in self.winding_vectors],
        }


@dataclass(frozen=True, slots=True)
class SparseMeshResources:
    """Auditable resource counts for one sparse surface preparation."""

    stored_node_count: int
    adjacent_cell_count: int
    candidate_cell_count: int
    component_count: int
    raw_vertex_count: int
    raw_face_count: int
    clipped_vertex_occurrence_count: int
    canonical_vertex_count: int
    canonical_face_count: int
    estimated_peak_bytes: int
    schema_version: str = SPARSE_MESH_RESOURCES_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_MESH_RESOURCES_SCHEMA:
            raise GraphAdapterError("Unsupported sparse-mesh-resources schema.")
        for name in (
            "stored_node_count",
            "adjacent_cell_count",
            "candidate_cell_count",
            "component_count",
            "raw_vertex_count",
            "raw_face_count",
            "clipped_vertex_occurrence_count",
            "canonical_vertex_count",
            "canonical_face_count",
            "estimated_peak_bytes",
        ):
            object.__setattr__(
                self, name, _positive_int(getattr(self, name), name=name, minimum=0)
            )

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            **{
                name: getattr(self, name)
                for name in (
                    "stored_node_count",
                    "adjacent_cell_count",
                    "candidate_cell_count",
                    "component_count",
                    "raw_vertex_count",
                    "raw_face_count",
                    "clipped_vertex_occurrence_count",
                    "canonical_vertex_count",
                    "canonical_face_count",
                    "estimated_peak_bytes",
                )
            },
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "SparseMeshResources":
        return cls(
            schema_version=str(value["schema_version"]),
            stored_node_count=int(value["stored_node_count"]),
            adjacent_cell_count=int(value["adjacent_cell_count"]),
            candidate_cell_count=int(value["candidate_cell_count"]),
            component_count=int(value["component_count"]),
            raw_vertex_count=int(value["raw_vertex_count"]),
            raw_face_count=int(value["raw_face_count"]),
            clipped_vertex_occurrence_count=int(value["clipped_vertex_occurrence_count"]),
            canonical_vertex_count=int(value["canonical_vertex_count"]),
            canonical_face_count=int(value["canonical_face_count"]),
            estimated_peak_bytes=int(value["estimated_peak_bytes"]),
        )


@dataclass(frozen=True, slots=True)
class SparseMeshTopologyDiagnostics:
    """Periodic seam, incidence, and fallback diagnostics."""

    winding_component_count: int
    winding_vectors: tuple[tuple[int, int, int], ...]
    duplicate_face_count_removed: int
    degenerate_face_count_removed: int
    interior_edge_incidence_failures: int
    canonical_boundary_edge_count: int
    paired_boundary_edge_count: int
    unpaired_boundary_edge_count: int
    maximum_boundary_seam_mismatch: float
    maximum_mesh_edge_length: float
    mesh_edge_length_upper_bound: float
    fallback_mode: str = "none"
    schema_version: str = SPARSE_MESH_TOPOLOGY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_MESH_TOPOLOGY_SCHEMA:
            raise GraphAdapterError("Unsupported sparse-mesh-topology schema.")
        for name in (
            "winding_component_count",
            "duplicate_face_count_removed",
            "degenerate_face_count_removed",
            "interior_edge_incidence_failures",
            "canonical_boundary_edge_count",
            "paired_boundary_edge_count",
            "unpaired_boundary_edge_count",
        ):
            object.__setattr__(
                self, name, _positive_int(getattr(self, name), name=name, minimum=0)
            )
        vectors = tuple(sorted({tuple(int(x) for x in value) for value in self.winding_vectors}))
        vectors = tuple(value for value in vectors if value != (0, 0, 0))
        object.__setattr__(self, "winding_vectors", vectors)
        for name in (
            "maximum_boundary_seam_mismatch",
            "maximum_mesh_edge_length",
            "mesh_edge_length_upper_bound",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphAdapterError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if self.fallback_mode not in {
            "none",
            "dense_canonical",
            "node_cloud",
            "tiled_no_local_simplification",
            "coarse_recontour",
        }:
            raise GraphAdapterError("Unsupported sparse mesh fallback mode.")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "winding_component_count": self.winding_component_count,
            "winding_vectors": [list(value) for value in self.winding_vectors],
            "duplicate_face_count_removed": self.duplicate_face_count_removed,
            "degenerate_face_count_removed": self.degenerate_face_count_removed,
            "interior_edge_incidence_failures": self.interior_edge_incidence_failures,
            "canonical_boundary_edge_count": self.canonical_boundary_edge_count,
            "paired_boundary_edge_count": self.paired_boundary_edge_count,
            "unpaired_boundary_edge_count": self.unpaired_boundary_edge_count,
            "maximum_boundary_seam_mismatch": self.maximum_boundary_seam_mismatch,
            "maximum_mesh_edge_length": self.maximum_mesh_edge_length,
            "mesh_edge_length_upper_bound": self.mesh_edge_length_upper_bound,
            "fallback_mode": self.fallback_mode,
        }

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "SparseMeshTopologyDiagnostics":
        return cls(
            schema_version=str(value["schema_version"]),
            winding_component_count=int(value["winding_component_count"]),
            winding_vectors=tuple(tuple(item) for item in value["winding_vectors"]),
            duplicate_face_count_removed=int(value["duplicate_face_count_removed"]),
            degenerate_face_count_removed=int(value["degenerate_face_count_removed"]),
            interior_edge_incidence_failures=int(value["interior_edge_incidence_failures"]),
            canonical_boundary_edge_count=int(value["canonical_boundary_edge_count"]),
            paired_boundary_edge_count=int(value["paired_boundary_edge_count"]),
            unpaired_boundary_edge_count=int(value["unpaired_boundary_edge_count"]),
            maximum_boundary_seam_mismatch=float(value["maximum_boundary_seam_mismatch"]),
            maximum_mesh_edge_length=float(value["maximum_mesh_edge_length"]),
            mesh_edge_length_upper_bound=float(value["mesh_edge_length_upper_bound"]),
            fallback_mode=str(value["fallback_mode"]),
        )


@dataclass(frozen=True, slots=True)
class PeriodicSparseDensityMesh3D:
    """One canonical clipped sparse triangular density shell."""

    vertices_fractional: FloatArray
    vertices_cartesian: FloatArray
    faces: IntArray
    scientific_hdr_threshold: float
    render_level: float
    requested_mass_fraction: float
    achieved_mass_fraction: float
    resources: SparseMeshResources
    topology: SparseMeshTopologyDiagnostics
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = SPARSE_DENSITY_MESH_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_DENSITY_MESH_SCHEMA:
            raise GraphAdapterError("Unsupported sparse-density-mesh schema.")
        fractional = _readonly(
            self.vertices_fractional, np.float64, ndim=2, name="vertices_fractional"
        )
        cartesian = _readonly(
            self.vertices_cartesian, np.float64, ndim=2, name="vertices_cartesian"
        )
        faces = _readonly(self.faces, np.int64, ndim=2, name="faces")
        if fractional.shape != cartesian.shape or fractional.shape[1:] != (3,):
            raise GraphAdapterError("Mesh vertex arrays must align with shape (n, 3).")
        if faces.shape[1:] != (3,):
            raise GraphAdapterError("faces must have shape (n_faces, 3).")
        if faces.size and (int(np.min(faces)) < 0 or int(np.max(faces)) >= fractional.shape[0]):
            raise GraphAdapterError("Mesh face index lies outside vertex array.")
        fraction = float(self.requested_mass_fraction)
        achieved = float(self.achieved_mass_fraction)
        if not 0.0 < fraction < 1.0:
            raise GraphStyleError("requested_mass_fraction must lie in (0, 1).")
        if not fraction <= achieved <= 1.0 + 5.0e-13:
            raise GraphAdapterError("achieved_mass_fraction is inconsistent.")
        object.__setattr__(self, "vertices_fractional", fractional)
        object.__setattr__(self, "vertices_cartesian", cartesian)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(self, "scientific_hdr_threshold", float(self.scientific_hdr_threshold))
        object.__setattr__(self, "render_level", float(self.render_level))
        object.__setattr__(self, "requested_mass_fraction", fraction)
        object.__setattr__(self, "achieved_mass_fraction", min(1.0, achieved))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self, *, include_geometry: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "scientific_hdr_threshold": self.scientific_hdr_threshold,
            "render_level": self.render_level,
            "requested_mass_fraction": self.requested_mass_fraction,
            "achieved_mass_fraction": self.achieved_mass_fraction,
            "resources": self.resources.to_json_dict(),
            "topology": self.topology.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_geometry:
            result["vertices_fractional"] = self.vertices_fractional.tolist()
            result["vertices_cartesian"] = self.vertices_cartesian.tolist()
            result["faces"] = self.faces.tolist()
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicSparseDensityMesh3D":
        for name in ("vertices_fractional", "vertices_cartesian", "faces"):
            if name not in value:
                raise GraphAdapterError("Sparse mesh JSON requires geometry arrays.")
        return cls(
            schema_version=str(value["schema_version"]),
            vertices_fractional=np.asarray(value["vertices_fractional"], dtype=np.float64),
            vertices_cartesian=np.asarray(value["vertices_cartesian"], dtype=np.float64),
            faces=np.asarray(value["faces"], dtype=np.int64),
            scientific_hdr_threshold=float(value["scientific_hdr_threshold"]),
            render_level=float(value["render_level"]),
            requested_mass_fraction=float(value["requested_mass_fraction"]),
            achieved_mass_fraction=float(value["achieved_mass_fraction"]),
            resources=SparseMeshResources.from_json_dict(value["resources"]),
            topology=SparseMeshTopologyDiagnostics.from_json_dict(value["topology"]),
            metadata=value.get("metadata", {}),
        )

    def translated_vertices(
        self, shift: tuple[int, int, int], display_cell: FloatArray
    ) -> FloatArray:
        translation = np.asarray(shift, dtype=np.float64) @ np.asarray(
            display_cell, dtype=np.float64
        )
        result = np.asarray(self.vertices_cartesian, dtype=np.float64) + translation[None, :]
        result.setflags(write=False)
        return result


@dataclass(frozen=True, slots=True)
class PreparedSparseDensitySurface:
    """Sparse mesh result or deterministic node-cloud fallback."""

    render_kind: Literal["mesh", "node_cloud"]
    mesh: PeriodicSparseDensityMesh3D | None
    cloud: DensityNodeCloud3D | None
    fallback_mode: str
    schema_version: str = SPARSE_DENSITY_SURFACE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != SPARSE_DENSITY_SURFACE_SCHEMA:
            raise GraphAdapterError("Unsupported sparse-density-surface schema.")
        if self.render_kind == "mesh":
            if self.mesh is None or self.cloud is not None:
                raise GraphAdapterError("Mesh result requires mesh only.")
        elif self.render_kind == "node_cloud":
            if self.cloud is None or self.mesh is not None:
                raise GraphAdapterError("Node-cloud result requires cloud only.")
        else:
            raise GraphAdapterError("render_kind must be mesh or node_cloud.")
        if self.fallback_mode not in {
            "none",
            "dense_canonical",
            "node_cloud",
            "tiled_no_local_simplification",
            "coarse_recontour",
        }:
            raise GraphAdapterError("Unsupported fallback_mode.")


def _stored_positive_nodes(field: PeriodicBlockScalarField3D) -> tuple[IntArray, FloatArray]:
    coordinates: list[IntArray] = []
    values: list[FloatArray] = []
    for batch_coordinates, batch_values in field.iter_stored_nodes(batch_size=262_144):
        positive = np.asarray(batch_values) > 0.0
        if np.any(positive):
            coordinates.append(np.asarray(batch_coordinates[positive], dtype=np.int64))
            values.append(np.asarray(batch_values[positive], dtype=np.float64))
    if not coordinates:
        raise GraphAdapterError("Sparse density field contains no positive stored nodes.")
    result_coordinates = np.ascontiguousarray(np.concatenate(coordinates, axis=0))
    result_values = np.ascontiguousarray(np.concatenate(values, axis=0))
    result_coordinates.setflags(write=False)
    result_values.setflags(write=False)
    return result_coordinates, result_values


def _float32_render_level(scientific: float, maximum: float) -> float:
    """Return a robust interior level for float32 marching-cubes arithmetic.

    scikit-image evaluates marching cubes in single precision.  A level only one
    ULP below the maximum can therefore collapse all interpolated vertices onto
    the maximal node and be removed as degenerate geometry.  Keep a small,
    deterministic 16-ULP guard from the upper endpoint.  This affects only the
    display contour for a numerically point-like field; the scientific HDR
    threshold remains unchanged and is retained separately in metadata.
    """

    minimum32 = np.float32(0.0)
    maximum32 = np.float32(maximum)
    level32 = np.float32(scientific)
    guarded_maximum = maximum32
    for _ in range(16):
        guarded_maximum = np.nextafter(guarded_maximum, minimum32, dtype=np.float32)
    if not minimum32 < guarded_maximum < maximum32:
        guarded_maximum = np.nextafter(maximum32, minimum32, dtype=np.float32)
    if not minimum32 < level32 <= guarded_maximum:
        level32 = guarded_maximum
    if not minimum32 < level32 < maximum32:
        raise GraphAdapterError("No interior float32 contour level exists for this field.")
    return float(level32)


def identify_sparse_mesh_candidate_cells(
    field: PeriodicBlockScalarField3D,
    mass_fraction: float,
    *,
    max_candidate_cells: int | None = None,
    max_workspace_bytes: int | None = None,
) -> SparseMeshCandidateCells:
    """Identify all logical cells crossing the float32 render level."""

    if not isinstance(field, (PeriodicBlockScalarField3D, PeriodicPackedBlockScalarField3D)):
        raise TypeError("field must be a supported local-sparse periodic scalar field.")
    budget, _model, derived = resolve_density_resource_limits()
    candidate_default = derived["max_density_mesh_cells"]
    candidate_limit = (
        candidate_default
        if max_candidate_cells is None
        else min(candidate_default, _positive_int(max_candidate_cells, name="max_candidate_cells"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    details = field.hdr_details(float(mass_fraction))
    stored_coordinates, stored_values = _stored_positive_nodes(field)
    render_level = _float32_render_level(details.threshold, float(np.max(stored_values)))
    # A crossing cell must contain at least one corner strictly above the
    # float32 contour level.  Starting from only those high nodes is exact and
    # avoids expanding the much larger truncated-Gaussian tail support.
    high_nodes = np.asarray(stored_values, dtype=np.float32) > np.float32(render_level)
    selected_coordinates = stored_coordinates[high_nodes]
    if selected_coordinates.shape[0] == 0:
        raise GraphAdapterError("Requested sparse HDR shell has no nodes above its render level.")
    adjacent_count = int(selected_coordinates.shape[0]) * 8
    estimated = adjacent_count * 8 + adjacent_count * 3 * 8
    if estimated > workspace_limit:
        raise GraphComplexityError(
            f"Sparse mesh candidate planning requires approximately {estimated} bytes, "
            f"exceeding max_workspace_bytes={workspace_limit}."
        )
    shape = field.grid_shape
    shape_array = np.asarray(shape, dtype=np.int64)
    adjacent = np.empty((adjacent_count, 3), dtype=np.int64)
    cursor = 0
    for corner in _CORNERS:
        stop = cursor + selected_coordinates.shape[0]
        adjacent[cursor:stop] = np.mod(selected_coordinates - corner[None, :], shape_array)
        cursor = stop
    adjacent_flat = np.unique(_flat_indices(adjacent, shape)).astype(np.int64, copy=False)
    if adjacent_flat.size > candidate_limit:
        raise GraphComplexityError(
            f"Sparse mesh has {adjacent_flat.size} adjacent logical cells, exceeding "
            f"max_candidate_cells={candidate_limit}."
        )
    adjacent_cells = _coordinates(adjacent_flat, shape)
    qualifying: list[np.ndarray] = []
    batch_size = max(1, min(131_072, workspace_limit // (8 * 3 * 8 + 8 * 8)))
    for start in range(0, adjacent_cells.shape[0], batch_size):
        cells = adjacent_cells[start : start + batch_size]
        queries = np.mod(cells[:, None, :] + _CORNERS[None, :, :], shape_array)
        values = field.gather_node_values(queries.reshape((-1, 3))).reshape((-1, 8))
        values32 = np.asarray(values, dtype=np.float32)
        high = values32 > np.float32(render_level)
        crossing = np.any(high, axis=1) & np.any(~high, axis=1)
        if np.any(crossing):
            qualifying.append(cells[crossing])
    if qualifying:
        cells = np.ascontiguousarray(np.concatenate(qualifying, axis=0), dtype=np.int64)
        flat = _flat_indices(cells, shape)
    else:
        cells = np.empty((0, 3), dtype=np.int64)
        flat = np.empty(0, dtype=np.int64)
    cells.setflags(write=False)
    flat.setflags(write=False)
    planning_bytes = int(
        high_nodes.nbytes
        + selected_coordinates.nbytes
        + adjacent.nbytes
        + adjacent_flat.nbytes
        + adjacent_cells.nbytes
    )
    return SparseMeshCandidateCells(
        logical_grid_shape=shape,
        scientific_hdr_threshold=details.threshold,
        render_level=render_level,
        flat_indices=flat,
        cell_indices=cells,
        adjacent_cell_count=int(adjacent_flat.size),
        planning_bytes=planning_bytes,
    )


def label_periodic_cell_components(
    candidates: SparseMeshCandidateCells,
) -> tuple[LiftedSparseMeshComponent, ...]:
    """Label face-connected cells and detect torus winding with array state.

    The original implementation stored one small NumPy coordinate array per
    visited cell in a Python dictionary.  Diffuse shells contain hundreds of
    thousands of cells, so those transient objects fragmented the allocator and
    made the following tiled extraction path unpredictably slow.  This version
    stores lifted coordinates in one dense ``(n_cells, 3)`` integer array while
    preserving the exact lifted-chart and winding semantics.
    """

    shape = tuple(int(value) for value in candidates.logical_grid_shape)
    sx, sy, sz = shape
    flat = np.asarray(candidates.flat_indices, dtype=np.int64)
    cells = np.asarray(candidates.cell_indices, dtype=np.int64)
    if flat.size == 0:
        return ()
    row_by_flat = {int(value): row for row, value in enumerate(flat.tolist())}
    visited = np.zeros(flat.size, dtype=np.bool_)
    lifted_by_row = np.empty((flat.size, 3), dtype=np.int64)
    components: list[LiftedSparseMeshComponent] = []
    steps = tuple(tuple(int(value) for value in step) for step in _NEIGHBOR_STEPS)
    for root in range(flat.size):
        if visited[root]:
            continue
        lifted_by_row[root] = cells[root]
        queue: deque[int] = deque((root,))
        visited[root] = True
        winding: set[tuple[int, int, int]] = set()
        rows: list[int] = []
        while queue:
            row = queue.popleft()
            rows.append(row)
            cx, cy, cz = (int(value) for value in cells[row])
            lx, ly, lz = (int(value) for value in lifted_by_row[row])
            for dx, dy, dz in steps:
                nx = (cx + dx) % sx
                ny = (cy + dy) % sy
                nz = (cz + dz) % sz
                neighbor_flat = (nx * sy + ny) * sz + nz
                neighbor_row = row_by_flat.get(neighbor_flat)
                if neighbor_row is None:
                    continue
                proposed = (lx + dx, ly + dy, lz + dz)
                if not visited[neighbor_row]:
                    lifted_by_row[neighbor_row] = proposed
                    visited[neighbor_row] = True
                    queue.append(neighbor_row)
                else:
                    previous = lifted_by_row[neighbor_row]
                    residual = (
                        proposed[0] - int(previous[0]),
                        proposed[1] - int(previous[1]),
                        proposed[2] - int(previous[2]),
                    )
                    if residual != (0, 0, 0):
                        winding.add(residual)
                        winding.add(tuple(-value for value in residual))
        ordered_rows = np.asarray(
            sorted(rows, key=lambda value: int(flat[value])), dtype=np.int64
        )
        canonical_component = np.ascontiguousarray(cells[ordered_rows], dtype=np.int64)
        lifted_component = np.ascontiguousarray(
            lifted_by_row[ordered_rows], dtype=np.int64
        )
        components.append(
            LiftedSparseMeshComponent(
                component_index=len(components),
                canonical_cell_indices=canonical_component,
                lifted_cell_indices=lifted_component,
                winding_vectors=tuple(sorted(winding)),
            )
        )
    return tuple(components)


def _clip_polygon_plane(
    polygon: list[np.ndarray], axis: int, bound: float, keep_greater: bool
) -> list[np.ndarray]:
    if not polygon:
        return []

    def inside(point: np.ndarray) -> bool:
        return bool(point[axis] >= bound - 1.0e-14) if keep_greater else bool(
            point[axis] <= bound + 1.0e-14
        )

    output: list[np.ndarray] = []
    previous = polygon[-1]
    previous_inside = inside(previous)
    for current in polygon:
        current_inside = inside(current)
        if current_inside != previous_inside:
            denominator = current[axis] - previous[axis]
            if abs(float(denominator)) > 0.0:
                factor = (bound - previous[axis]) / denominator
                intersection = previous + factor * (current - previous)
                intersection[axis] = bound
                output.append(intersection)
        if current_inside:
            output.append(current)
        previous = current
        previous_inside = current_inside
    return output


def _clip_triangle_to_unit_cube(triangle: FloatArray) -> list[np.ndarray]:
    polygon = [np.asarray(point, dtype=np.float64).copy() for point in triangle]
    for axis in range(3):
        polygon = _clip_polygon_plane(polygon, axis, 0.0, True)
        polygon = _clip_polygon_plane(polygon, axis, 1.0, False)
        if len(polygon) < 3:
            return []
    triangles: list[np.ndarray] = []
    for index in range(1, len(polygon) - 1):
        triangles.append(np.asarray((polygon[0], polygon[index], polygon[index + 1])))
    return triangles


def _component_image_shifts(vertices: FloatArray) -> tuple[tuple[int, int, int], ...]:
    minimum = np.min(vertices, axis=0)
    maximum = np.max(vertices, axis=0)
    ranges: list[range] = []
    for axis in range(3):
        lower = int(np.ceil(-maximum[axis] - 1.0e-12))
        upper = int(np.floor(1.0 - minimum[axis] + 1.0e-12))
        ranges.append(range(lower, upper + 1))
    return tuple(tuple(int(x) for x in value) for value in product(*ranges))


def _canonicalize_triangles(
    triangles_fractional: list[np.ndarray],
    display_cell: FloatArray,
) -> tuple[FloatArray, FloatArray, IntArray, int, int]:
    if not triangles_fractional:
        raise GraphAdapterError("Sparse contour produced no canonical triangles.")
    cell = np.asarray(display_cell, dtype=np.float64)
    reference_length = max(float(np.linalg.norm(vector)) for vector in cell)
    tolerance = max(1.0e-14, 1.0e-10 * reference_length)
    buckets: dict[tuple[int, int, int], list[int]] = {}
    fractional_vertices: list[np.ndarray] = []
    cartesian_vertices: list[np.ndarray] = []
    raw_faces: list[tuple[int, int, int]] = []

    def vertex_id(point: np.ndarray) -> int:
        snapped = np.asarray(point, dtype=np.float64).copy()
        snapped[np.abs(snapped) <= 1.0e-13] = 0.0
        snapped[np.abs(snapped - 1.0) <= 1.0e-13] = 1.0
        cartesian = snapped @ cell
        key = tuple(int(x) for x in np.rint(cartesian / tolerance))
        best: int | None = None
        for delta in product((-1, 0, 1), repeat=3):
            neighbor_key = tuple(key[axis] + delta[axis] for axis in range(3))
            for candidate in buckets.get(neighbor_key, ()):
                if float(np.linalg.norm(cartesian_vertices[candidate] - cartesian)) <= tolerance:
                    if best is None or candidate < best:
                        best = candidate
        if best is not None:
            return best
        index = len(fractional_vertices)
        fractional_vertices.append(snapped)
        cartesian_vertices.append(cartesian)
        buckets.setdefault(key, []).append(index)
        return index

    degenerate = 0
    for triangle in triangles_fractional:
        ids = tuple(vertex_id(point) for point in triangle)
        if len(set(ids)) < 3:
            degenerate += 1
            continue
        points = np.asarray([cartesian_vertices[index] for index in ids])
        area_vector = np.cross(points[1] - points[0], points[2] - points[0])
        if float(np.linalg.norm(area_vector)) <= tolerance * tolerance:
            degenerate += 1
            continue
        raw_faces.append(ids)

    duplicate = 0
    face_by_key: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for face in raw_faces:
        key = tuple(sorted(face))
        if key in face_by_key:
            duplicate += 1
            continue
        rotations = (face, (face[1], face[2], face[0]), (face[2], face[0], face[1]))
        face_by_key[key] = min(rotations)
    if not face_by_key:
        raise GraphAdapterError("Sparse contour contained no nondegenerate faces.")

    fractional_array = np.asarray(fractional_vertices, dtype=np.float64)
    order = np.lexsort(
        (fractional_array[:, 2], fractional_array[:, 1], fractional_array[:, 0])
    )
    inverse = np.empty(order.size, dtype=np.int64)
    inverse[order] = np.arange(order.size, dtype=np.int64)
    fractional_array = np.ascontiguousarray(fractional_array[order])
    cartesian_array = np.ascontiguousarray(fractional_array @ cell)
    faces = np.asarray(
        [tuple(int(inverse[index]) for index in face) for face in face_by_key.values()],
        dtype=np.int64,
    )
    canonical_faces: list[tuple[int, int, int]] = []
    for face in faces:
        value = tuple(int(x) for x in face)
        rotations = (value, (value[1], value[2], value[0]), (value[2], value[0], value[1]))
        canonical_faces.append(min(rotations))
    faces = np.ascontiguousarray(np.asarray(sorted(canonical_faces), dtype=np.int64))
    fractional_array.setflags(write=False)
    cartesian_array.setflags(write=False)
    faces.setflags(write=False)
    return fractional_array, cartesian_array, faces, duplicate, degenerate


def validate_periodic_canonical_mesh(
    vertices_fractional: FloatArray,
    vertices_cartesian: FloatArray,
    faces: IntArray,
    *,
    display_cell: FloatArray,
    logical_grid_shape: tuple[int, int, int],
    winding_component_count: int = 0,
    winding_vectors: tuple[tuple[int, int, int], ...] = (),
    duplicate_face_count_removed: int = 0,
    degenerate_face_count_removed: int = 0,
    fallback_mode: str = "none",
) -> SparseMeshTopologyDiagnostics:
    """Validate incidence and periodic seams with vectorized edge deduplication.

    The former Python dictionary pass scaled with every triangle-edge occurrence
    and dominated diffuse outer shells.  This implementation performs the global
    incidence reduction in NumPy and retains Python work only for the comparatively
    small set of canonical-boundary edges.
    """

    fractional = np.asarray(vertices_fractional, dtype=np.float64)
    cartesian = np.asarray(vertices_cartesian, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    cell = np.asarray(display_cell, dtype=np.float64)
    reference_length = max(float(np.linalg.norm(vector)) for vector in cell)
    tolerance = max(1.0e-14, 1.0e-10 * reference_length)
    fractional_tolerance = 1.0e-10
    if face_array.size:
        edge_occurrences = np.concatenate(
            (
                face_array[:, (0, 1)],
                face_array[:, (1, 2)],
                face_array[:, (2, 0)],
            ),
            axis=0,
        )
        edge_occurrences.sort(axis=1)
        unique_edges, incidence = np.unique(
            edge_occurrences, axis=0, return_counts=True
        )
        del edge_occurrences
    else:
        unique_edges = np.empty((0, 2), dtype=np.int64)
        incidence = np.empty((0,), dtype=np.int64)
    sources = unique_edges[:, 0]
    targets = unique_edges[:, 1]
    maximum_edge = 0.0
    for start in range(0, unique_edges.shape[0], 262_144):
        stop = min(unique_edges.shape[0], start + 262_144)
        differences = cartesian[targets[start:stop]] - cartesian[sources[start:stop]]
        if differences.size:
            maximum_edge = max(
                maximum_edge,
                float(np.max(np.linalg.norm(differences, axis=1))),
            )
    boundary_axis = np.full(unique_edges.shape[0], -1, dtype=np.int8)
    boundary_side = np.full(unique_edges.shape[0], -1, dtype=np.int8)
    source_fractional = fractional[sources]
    target_fractional = fractional[targets]
    unassigned = np.ones(unique_edges.shape[0], dtype=bool)
    for axis in range(3):
        lower = (
            unassigned
            & (np.abs(source_fractional[:, axis]) <= fractional_tolerance)
            & (np.abs(target_fractional[:, axis]) <= fractional_tolerance)
        )
        boundary_axis[lower] = axis
        boundary_side[lower] = 0
        unassigned[lower] = False
        upper = (
            unassigned
            & (np.abs(source_fractional[:, axis] - 1.0) <= fractional_tolerance)
            & (np.abs(target_fractional[:, axis] - 1.0) <= fractional_tolerance)
        )
        boundary_axis[upper] = axis
        boundary_side[upper] = 1
        unassigned[upper] = False
    boundary_mask = boundary_axis >= 0
    interior_failures = int(np.count_nonzero(unassigned & (incidence != 2)))
    interior_failures += int(
        np.count_nonzero(boundary_mask & ~np.isin(incidence, (1, 2)))
    )
    boundary_indices = np.flatnonzero(boundary_mask)
    boundary_count = int(boundary_indices.size)
    boundary_records: dict[tuple[int, int, tuple[int, ...]], list[np.ndarray]] = {}
    for edge_index in boundary_indices.tolist():
        axis = int(boundary_axis[edge_index])
        side = int(boundary_side[edge_index])
        points_f = np.asarray(
            (source_fractional[edge_index], target_fractional[edge_index]),
            dtype=np.float64,
        )
        normalized = points_f.copy()
        normalized[:, axis] = 0.0
        normalized_x = normalized @ cell
        endpoint_keys = sorted(
            tuple(int(value) for value in np.rint(point / tolerance))
            for point in normalized_x
        )
        key = tuple(value for endpoint in endpoint_keys for value in endpoint)
        boundary_records.setdefault((axis, side, key), []).append(normalized_x)
    paired = 0
    unpaired = 0
    maximum_mismatch = 0.0
    axes_and_keys = sorted({(axis, key) for axis, _side, key in boundary_records})
    for axis, key in axes_and_keys:
        lower = boundary_records.get((axis, 0, key), [])
        upper = boundary_records.get((axis, 1, key), [])
        pair_count = min(len(lower), len(upper))
        paired += pair_count * 2
        unpaired += abs(len(lower) - len(upper))
        for left, right in zip(lower[:pair_count], upper[:pair_count], strict=True):
            direct = max(
                float(np.linalg.norm(left[0] - right[0])),
                float(np.linalg.norm(left[1] - right[1])),
            )
            reverse = max(
                float(np.linalg.norm(left[0] - right[1])),
                float(np.linalg.norm(left[1] - right[0])),
            )
            maximum_mismatch = max(maximum_mismatch, min(direct, reverse))
    basis_steps = cell / np.asarray(logical_grid_shape, dtype=np.float64)[:, None]
    upper_bound = sum(float(np.linalg.norm(vector)) for vector in basis_steps) * (
        1.0 + 1.0e-10
    )
    return SparseMeshTopologyDiagnostics(
        winding_component_count=winding_component_count,
        winding_vectors=winding_vectors,
        duplicate_face_count_removed=duplicate_face_count_removed,
        degenerate_face_count_removed=degenerate_face_count_removed,
        interior_edge_incidence_failures=interior_failures,
        canonical_boundary_edge_count=boundary_count,
        paired_boundary_edge_count=paired,
        unpaired_boundary_edge_count=unpaired,
        maximum_boundary_seam_mismatch=maximum_mismatch,
        maximum_mesh_edge_length=maximum_edge,
        mesh_edge_length_upper_bound=upper_bound,
        fallback_mode=fallback_mode,
    )


def _mesh_topology_is_valid(
    topology: SparseMeshTopologyDiagnostics,
    display_cell: Any,
) -> bool:
    reference_length = max(
        float(np.linalg.norm(vector))
        for vector in np.asarray(display_cell, dtype=np.float64)
    )
    return bool(
        topology.interior_edge_incidence_failures == 0
        and topology.unpaired_boundary_edge_count == 0
        and topology.maximum_boundary_seam_mismatch
        <= 1.0e-10 * reference_length
    )


def _coarse_recontour_sparse_field(
    field: PeriodicBlockScalarField3D,
    *,
    render_level: float,
    stride: int,
    max_nodes: int,
    max_faces: int,
) -> tuple[
    FloatArray,
    FloatArray,
    IntArray,
    SparseMeshTopologyDiagnostics,
    dict[str, Any],
]:
    """Recontour one sparse field on a bounded seam-closed display grid.

    This is a visual repair path used only after exact tiled extraction fails
    periodic incidence validation.  It samples the same scientific scalar field
    and uses the same contour level; only the display grid is coarsened.
    """

    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:  # pragma: no cover
        raise GraphUnsupportedFeatureError(
            "Sparse mesh repair recontouring requires scikit-image."
        ) from exc
    original_shape = np.asarray(field.grid_shape, dtype=np.int64)
    coarse_shape = np.maximum(
        8, np.ceil(original_shape / max(1, int(stride))).astype(np.int64)
    )
    while int(np.prod(coarse_shape, dtype=object)) > int(max_nodes) and np.any(
        coarse_shape > 8
    ):
        coarse_shape = np.maximum(
            8, np.floor(coarse_shape * 0.85).astype(np.int64)
        )
    if int(np.prod(coarse_shape, dtype=object)) > int(max_nodes):
        raise GraphComplexityError(
            "Coarse sparse-mesh repair grid exceeds max_dense_fallback_nodes."
        )
    axes = [
        np.floor(np.arange(int(size), dtype=np.float64) * original / size).astype(
            np.int64
        )
        for size, original in zip(coarse_shape, original_shape, strict=True)
    ]
    values = np.empty(tuple(int(value) for value in coarse_shape), dtype=np.float32)
    yz = int(coarse_shape[1] * coarse_shape[2])
    batch_x = max(1, min(int(coarse_shape[0]), int(max_nodes) // max(1, yz)))
    for start in range(0, int(coarse_shape[0]), batch_x):
        stop = min(int(coarse_shape[0]), start + batch_x)
        x, y, z = np.meshgrid(
            axes[0][start:stop], axes[1], axes[2], indexing="ij"
        )
        coordinates = np.column_stack((x.ravel(), y.ravel(), z.ravel()))
        gathered = field.gather_node_values(coordinates)
        values[start:stop] = np.asarray(gathered, dtype=np.float32).reshape(
            (stop - start, int(coarse_shape[1]), int(coarse_shape[2]))
        )
    extended = np.pad(values, ((0, 1), (0, 1), (0, 1)), mode="wrap")
    minimum = np.float32(np.min(extended))
    maximum = np.float32(np.max(extended))
    level = np.float32(render_level)
    if not minimum < level < maximum:
        level = np.nextafter(maximum, minimum, dtype=np.float32)
    if not minimum < level < maximum:
        raise GraphAdapterError(
            "Coarse sparse-mesh repair grid does not bracket the contour level."
        )
    vertices_fractional, faces, _normals, _values = marching_cubes(
        extended,
        level=float(level),
        spacing=tuple(float(1.0 / value) for value in coarse_shape),
        allow_degenerate=False,
        method="lewiner",
    )
    face_array = np.ascontiguousarray(faces, dtype=np.int64)
    if face_array.shape[0] > int(max_faces):
        raise GraphComplexityError(
            "Coarse sparse-mesh repair contour exceeds the raw extraction face limit."
        )
    fractional = np.ascontiguousarray(vertices_fractional, dtype=np.float64)
    cartesian = np.ascontiguousarray(
        fractional @ np.asarray(field.display_cell, dtype=np.float64)
    )
    topology = validate_periodic_canonical_mesh(
        fractional,
        cartesian,
        face_array,
        display_cell=np.asarray(field.display_cell, dtype=np.float64),
        logical_grid_shape=tuple(int(value) for value in coarse_shape),
        fallback_mode="coarse_recontour",
    )
    if not _mesh_topology_is_valid(topology, field.display_cell):
        raise GraphAdapterError(
            "Coarse sparse-mesh repair contour failed periodic incidence validation."
        )
    return (
        fractional,
        cartesian,
        face_array,
        topology,
        {
            "fallback_mode": "coarse_recontour",
            "recontour_stride": int(stride),
            "recontour_grid_shape": tuple(int(value) for value in coarse_shape),
            "render_level": float(level),
        },
    )


def _require_sparse_mesh_face_limit(
    face_count: int,
    face_limit: int,
    *,
    after_simplification: bool,
) -> None:
    """Preserve the historical per-shell terminal face-limit failure.

    This small boundary exists so the mesh-budget revision can lock the three
    reported regressions without allocating hundreds of thousands of test
    triangles. Stage 2 will replace the overloaded visual-limit semantics with
    separate raw-work and scene-fit contracts.
    """

    count = _positive_int(face_count, name="face_count", minimum=0)
    limit = _positive_int(face_limit, name="face_limit")
    if count <= limit:
        return
    qualifier = " after optional simplification" if after_simplification else ""
    raise GraphComplexityError(
        f"Sparse density mesh contains {count} faces{qualifier}, exceeding "
        f"max_mesh_faces={limit}."
    )


def _mesh_nonwinding_components(
    field: PeriodicBlockScalarField3D,
    candidates: SparseMeshCandidateCells,
    components: tuple[LiftedSparseMeshComponent, ...],
    *,
    max_raw_faces: int,
    max_raw_vertices: int,
) -> tuple[FloatArray, FloatArray, IntArray, int, int, int, int, int]:
    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise GraphUnsupportedFeatureError(
            "Sparse mesh rendering requires scikit-image. Install mdstats[interactive]."
        ) from exc
    shape = field.grid_shape
    if candidates.candidate_cell_count * 5 > max_raw_faces:
        raise GraphComplexityError(
            "Sparse mesh worst-case raw faces exceed max_raw_faces before contouring."
        )
    if candidates.candidate_cell_count * 12 > max_raw_vertices:
        raise GraphComplexityError(
            "Sparse mesh worst-case raw vertices exceed max_raw_vertices before contouring."
        )
    shape_array = np.asarray(shape, dtype=np.int64)
    spacing = tuple(float(1.0 / value) for value in shape)
    raw_component_triangles: list[np.ndarray] = []
    raw_vertices = 0
    raw_faces = 0
    level32 = np.float32(candidates.render_level)
    for component in components:
        component_triangles: list[np.ndarray] = []
        for canonical, lifted in zip(
            component.canonical_cell_indices,
            component.lifted_cell_indices,
            strict=True,
        ):
            queries = np.mod(canonical[None, :] + _CORNERS, shape_array)
            values = field.gather_node_values(queries)
            volume = np.empty((2, 2, 2), dtype=np.float32)
            for corner, value in zip(_CORNERS, values, strict=True):
                volume[tuple(corner)] = np.float32(value)
            high = volume > level32
            if not np.any(high) or np.all(high):
                continue
            try:
                vertices, faces, _normals, _surface_values = marching_cubes(
                    volume,
                    level=float(level32),
                    spacing=spacing,
                    allow_degenerate=False,
                    method="lewiner",
                )
            except (RuntimeError, ValueError):
                continue
            raw_vertices += int(vertices.shape[0])
            raw_faces += int(faces.shape[0])
            if raw_vertices > max_raw_vertices:
                raise GraphComplexityError(
                    f"Sparse mesh raw vertices exceed max_raw_vertices={max_raw_vertices}."
                )
            if raw_faces > max_raw_faces:
                raise GraphComplexityError(
                    f"Sparse mesh raw faces exceed max_raw_faces={max_raw_faces}."
                )
            # scikit-image returns float32-interpolated vertex coordinates.
            # Recompute every edge crossing from the shared endpoint values so
            # neighboring owned cells produce bit-identical face vertices.
            local_grid = np.asarray(vertices, dtype=np.float64) / np.asarray(
                spacing, dtype=np.float64
            )[None, :]
            precise = np.empty_like(local_grid)
            for vertex_index, local_vertex in enumerate(local_grid):
                rounded = np.rint(local_vertex).astype(np.int64)
                residual = np.abs(local_vertex - rounded)
                axis = int(np.argmax(residual))
                if float(residual[axis]) <= 1.0e-12:
                    precise[vertex_index] = rounded
                    continue
                endpoint0 = rounded.copy()
                endpoint1 = rounded.copy()
                endpoint0[axis] = 0
                endpoint1[axis] = 1
                value0 = float(volume[tuple(endpoint0)])
                value1 = float(volume[tuple(endpoint1)])
                denominator = value1 - value0
                if denominator == 0.0:
                    factor = float(local_vertex[axis])
                else:
                    factor = (float(level32) - value0) / denominator
                precise[vertex_index] = endpoint0
                precise[vertex_index, axis] = factor
            vertices = (
                np.asarray(lifted, dtype=np.float64)[None, :] + precise
            ) / shape_array[None, :]
            for face in np.asarray(faces, dtype=np.int64):
                component_triangles.append(vertices[face])
        if not component_triangles:
            continue
        component_vertices = np.concatenate(component_triangles, axis=0)
        shifts = _component_image_shifts(component_vertices)
        for shift in shifts:
            translation = np.asarray(shift, dtype=np.float64)
            for triangle in component_triangles:
                raw_component_triangles.extend(
                    _clip_triangle_to_unit_cube(triangle + translation[None, :])
                )
    if not raw_component_triangles:
        raise GraphAdapterError("No triangular surface could be extracted from sparse cells.")
    clipped_occurrences = len(raw_component_triangles) * 3
    fractional, cartesian, faces, duplicates, degenerates = _canonicalize_triangles(
        raw_component_triangles, field.display_cell
    )
    return (
        fractional,
        cartesian,
        faces,
        raw_vertices,
        raw_faces,
        clipped_occurrences,
        duplicates,
        degenerates,
    )


def _dense_fallback_mesh(
    field: PeriodicBlockScalarField3D,
    mass_fraction: float,
    *,
    face_contract: DensityMeshFaceContract,
) -> tuple[FloatArray, FloatArray, IntArray, float]:
    from .atomic_density import PeriodicScalarField3D, density_mesh_arrays

    dense = field.to_dense_values(max_nodes=int(np.prod(field.grid_shape, dtype=object)))
    dense_field = PeriodicScalarField3D(
        field_key=field.field_key,
        label=field.label,
        values=dense,
        display_cell=field.display_cell,
        total_measure=field.total_measure,
        selected_atom_indices=(
            field.selected_atom_indices
            or field.source_provenance.atom_indices
            or (0,)
        ),
        gaussian_bandwidth=field.gaussian_bandwidth,
        sample_positions=field.sample_positions,
        metadata={**field.metadata.to_json_dict(), "sparse_mesh_fallback": "dense_canonical"},
        source_provenance=field.source_provenance,
    )
    cartesian, faces, level = density_mesh_arrays(
        dense_field,
        mass_fraction,
        face_contract=face_contract,
    )
    fractional = np.ascontiguousarray(
        np.asarray(cartesian, dtype=np.float64) @ np.linalg.inv(field.display_cell)
    )
    fractional.setflags(write=False)
    return fractional, cartesian, faces, level


def prepare_sparse_density_mesh(
    field: PeriodicBlockScalarField3D,
    mass_fraction: float,
    *,
    face_contract: DensityMeshFaceContract | None = None,
    max_faces: int | None = None,
    max_candidate_cells: int | None = None,
    max_raw_faces: int | None = None,
    max_raw_vertices: int | None = None,
    max_workspace_bytes: int | None = None,
    max_dense_fallback_nodes: int | None = None,
    allow_cloud_fallback: bool = True,
    cloud_max_points: int = 200_000,
    extraction_method: Literal["tiled", "legacy_cell"] = "tiled",
    extraction_options: Any | None = None,
    simplification_options: Any | None = None,
) -> PreparedSparseDensitySurface:
    """Prepare a canonical sparse mesh or deterministic winding fallback."""

    if not isinstance(field, (PeriodicBlockScalarField3D, PeriodicPackedBlockScalarField3D)):
        raise TypeError("field must be a supported local-sparse periodic scalar field.")
    if face_contract is not None and not isinstance(
        face_contract, DensityMeshFaceContract
    ):
        raise TypeError("face_contract must be DensityMeshFaceContract or None.")
    if face_contract is not None and (max_faces is not None or max_raw_faces is not None):
        raise GraphStyleError(
            "face_contract cannot be combined with legacy max_faces/max_raw_faces."
        )
    requested_face_contract = (
        legacy_standalone_face_contract(
            max_faces=max_faces,
            max_raw_faces=max_raw_faces,
        )
        if face_contract is None
        else face_contract
    )
    budget, _model, derived = resolve_density_resource_limits()
    candidate_default = derived["max_density_mesh_cells"]
    candidate_limit = (
        candidate_default
        if max_candidate_cells is None
        else min(candidate_default, _positive_int(max_candidate_cells, name="max_candidate_cells"))
    )
    raw_face_default = derived["max_density_mesh_faces"]
    resolved_face_contract = requested_face_contract.resolve_raw_limit(
        raw_face_default
    )
    assert resolved_face_contract.raw_extraction_face_limit is not None
    raw_face_limit = int(resolved_face_contract.raw_extraction_face_limit)
    visual_target_faces = resolved_face_contract.visual_target_faces
    standalone_final_face_limit = resolved_face_contract.standalone_final_face_limit
    raw_vertex_default = 3 * derived["max_density_mesh_faces"]
    raw_vertex_limit = (
        raw_vertex_default
        if max_raw_vertices is None
        else min(raw_vertex_default, _positive_int(max_raw_vertices, name="max_raw_vertices"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    dense_default = derived["max_density_voxels"]
    dense_limit = (
        dense_default
        if max_dense_fallback_nodes is None
        else min(dense_default, _positive_int(max_dense_fallback_nodes, name="max_dense_fallback_nodes"))
    )
    if extraction_method not in {"tiled", "legacy_cell"}:
        raise GraphStyleError("extraction_method must be tiled or legacy_cell.")
    if simplification_options is not None:
        from .density_mesh_simplify import MeshSimplificationOptions

        if not isinstance(simplification_options, MeshSimplificationOptions):
            raise TypeError(
                "simplification_options must be MeshSimplificationOptions or None."
            )
    candidates = identify_sparse_mesh_candidate_cells(
        field,
        mass_fraction,
        max_candidate_cells=candidate_limit,
        max_workspace_bytes=workspace_limit,
    )
    if candidates.candidate_cell_count == 0:
        raise GraphAdapterError("Requested sparse HDR shell has no candidate cells.")
    components = label_periodic_cell_components(candidates)
    winding_components = tuple(component for component in components if component.is_winding)
    winding_vectors = tuple(
        sorted({value for component in winding_components for value in component.winding_vectors})
    )
    details = field.hdr_details(float(mass_fraction))
    logical_nodes = int(np.prod(field.grid_shape, dtype=object))
    if winding_components:
        if logical_nodes <= dense_limit:
            fractional, cartesian, faces, level = _dense_fallback_mesh(
                field,
                mass_fraction,
                face_contract=resolved_face_contract,
            )
            face_report = evaluate_density_mesh_face_contract(
                int(faces.shape[0]),
                resolved_face_contract,
            )
            if face_report.standalone_final_limit_met is False:
                assert standalone_final_face_limit is not None
                _require_sparse_mesh_face_limit(
                    int(faces.shape[0]),
                    int(standalone_final_face_limit),
                    after_simplification=False,
                )
            topology = validate_periodic_canonical_mesh(
                fractional,
                cartesian,
                faces,
                display_cell=field.display_cell,
                logical_grid_shape=field.grid_shape,
                winding_component_count=len(winding_components),
                winding_vectors=winding_vectors,
                fallback_mode="dense_canonical",
            )
            resources = SparseMeshResources(
                stored_node_count=field.storage_summary().nonzero_node_count,
                adjacent_cell_count=candidates.adjacent_cell_count,
                candidate_cell_count=candidates.candidate_cell_count,
                component_count=len(components),
                raw_vertex_count=cartesian.shape[0],
                raw_face_count=faces.shape[0],
                clipped_vertex_occurrence_count=cartesian.shape[0],
                canonical_vertex_count=cartesian.shape[0],
                canonical_face_count=faces.shape[0],
                estimated_peak_bytes=int(
                    fractional.nbytes + cartesian.nbytes + faces.nbytes + logical_nodes * 8
                ),
            )
            mesh = PeriodicSparseDensityMesh3D(
                vertices_fractional=fractional,
                vertices_cartesian=cartesian,
                faces=faces,
                scientific_hdr_threshold=details.threshold,
                render_level=level,
                requested_mass_fraction=mass_fraction,
                achieved_mass_fraction=details.achieved_mass_fraction,
                resources=resources,
                topology=topology,
                metadata={
                    "candidate_cells": candidates.to_json_dict(),
                    "components": [component.to_json_dict() for component in components],
                    "fallback_reason": "nonzero_torus_winding",
                    "mesh_face_contract": resolved_face_contract.to_json_dict(),
                    "mesh_face_report": face_report.to_json_dict(),
                    "visual_target_met": face_report.visual_target_met,
                    "visual_target_overage_faces": (
                        face_report.visual_target_overage_faces
                    ),
                },
            )
            return PreparedSparseDensitySurface(
                render_kind="mesh",
                mesh=mesh,
                cloud=None,
                fallback_mode="dense_canonical",
            )
        if allow_cloud_fallback:
            cloud = prepare_density_node_cloud(
                field, mass_fraction, max_points=cloud_max_points
            )
            return PreparedSparseDensitySurface(
                render_kind="node_cloud",
                mesh=None,
                cloud=cloud,
                fallback_mode="node_cloud",
            )
        raise GraphComplexityError(
            "Sparse density shell contains a winding periodic component and exceeds "
            "max_dense_fallback_nodes; enable cloud fallback or use voxel_cloud."
        )

    tiled_metadata: dict[str, Any] = {}
    mesh_fallback_mode = "none"
    validation_grid_shape = tuple(int(value) for value in field.grid_shape)
    validated_pre_simplification_topology: SparseMeshTopologyDiagnostics | None = None
    if extraction_method == "tiled":
        from .density_contour_tiles import MeshExtractionOptions, plan_contour_render_tiles
        from .density_tiled_mesh import extract_tiled_density_mesh

        if extraction_options is None:
            resolved_extraction = MeshExtractionOptions(
                max_crossing_cells_per_tile=max_candidate_cells,
                max_raw_faces_per_tile=max_raw_faces,
                max_raw_vertices_per_tile=max_raw_vertices,
                max_transient_mesh_bytes=max_workspace_bytes,
                max_total_crossing_cells=max_candidate_cells,
                max_total_raw_faces=max_raw_faces,
                max_total_raw_vertices=max_raw_vertices,
                max_planning_workspace_bytes=max_workspace_bytes,
            )
        elif isinstance(extraction_options, MeshExtractionOptions):
            resolved_extraction = extraction_options
        else:
            raise TypeError(
                "extraction_options must be MeshExtractionOptions or None."
            )
        tile_plan = plan_contour_render_tiles(
            field, candidates, options=resolved_extraction
        )
        extraction_attempts: list[dict[str, Any]] = []

        def run_tiled(local_options: Any | None, *, stage: str):
            try:
                result = extract_tiled_density_mesh(
                    field,
                    tile_plan,
                    options=resolved_extraction,
                    local_simplification_options=local_options,
                )
                topology_result = validate_periodic_canonical_mesh(
                    result.vertices_fractional,
                    result.vertices_cartesian,
                    result.faces,
                    display_cell=field.display_cell,
                    logical_grid_shape=field.grid_shape,
                    duplicate_face_count_removed=result.duplicate_face_count_removed,
                    degenerate_face_count_removed=result.degenerate_face_count_removed,
                    fallback_mode=(
                        "tiled_no_local_simplification"
                        if stage == "tiled_no_local_simplification"
                        else "none"
                    ),
                )
                valid = _mesh_topology_is_valid(topology_result, field.display_cell)
                extraction_attempts.append(
                    {
                        "stage": stage,
                        "valid": bool(valid),
                        "faces": int(result.faces.shape[0]),
                        "topology": topology_result.to_json_dict(),
                    }
                )
                return result, topology_result, valid
            except Exception as exc:
                extraction_attempts.append(
                    {
                        "stage": stage,
                        "valid": False,
                        "reason": f"{type(exc).__name__}: {exc}",
                    }
                )
                return None, None, False

        extraction, extraction_topology, extraction_valid = run_tiled(
            simplification_options,
            stage="tiled_requested",
        )
        if (
            not extraction_valid
            and simplification_options is not None
            and bool(getattr(simplification_options, "local_presimplification", False))
        ):
            extraction, extraction_topology, extraction_valid = run_tiled(
                replace(simplification_options, local_presimplification=False),
                stage="tiled_no_local_simplification",
            )
            if extraction_valid:
                mesh_fallback_mode = "tiled_no_local_simplification"
        coarse_metadata: dict[str, Any] | None = None
        if not extraction_valid:
            repair_errors: list[str] = []
            for stride in (2, 3, 4):
                try:
                    (
                        fractional,
                        cartesian,
                        faces,
                        validated_pre_simplification_topology,
                        coarse_metadata,
                    ) = _coarse_recontour_sparse_field(
                        field,
                        render_level=candidates.render_level,
                        stride=stride,
                        max_nodes=dense_limit,
                        max_faces=raw_face_limit,
                    )
                    mesh_fallback_mode = "coarse_recontour"
                    validation_grid_shape = tuple(
                        int(value) for value in coarse_metadata["recontour_grid_shape"]
                    )
                    extraction_attempts.append(
                        {
                            "stage": f"coarse_recontour_stride_{stride}",
                            "valid": True,
                            "faces": int(faces.shape[0]),
                            "topology": validated_pre_simplification_topology.to_json_dict(),
                        }
                    )
                    break
                except Exception as exc:
                    repair_errors.append(f"stride={stride}: {type(exc).__name__}: {exc}")
                    extraction_attempts.append(
                        {
                            "stage": f"coarse_recontour_stride_{stride}",
                            "valid": False,
                            "reason": f"{type(exc).__name__}: {exc}",
                        }
                    )
            else:
                if allow_cloud_fallback:
                    cloud = prepare_density_node_cloud(
                        field, mass_fraction, max_points=cloud_max_points
                    )
                    return PreparedSparseDensitySurface(
                        render_kind="node_cloud",
                        mesh=None,
                        cloud=cloud,
                        fallback_mode="node_cloud",
                    )
                raise GraphAdapterError(
                    "Sparse tiled contour failed periodic incidence validation and "
                    "all coarse-recontour repairs failed: " + "; ".join(repair_errors)
                )
            raw_vertices = int(fractional.shape[0])
            raw_faces = int(faces.shape[0])
            clipped_occurrences = int(fractional.shape[0])
            duplicates_removed = 0
            degenerates_removed = 0
            estimated_peak = int(
                candidates.planning_bytes
                + tile_plan.planning_bytes
                + fractional.nbytes
                + cartesian.nbytes
                + faces.nbytes
            )
        else:
            assert extraction is not None and extraction_topology is not None
            fractional = extraction.vertices_fractional
            cartesian = extraction.vertices_cartesian
            faces = extraction.faces
            raw_vertices = extraction.raw_vertex_count
            raw_faces = extraction.raw_face_count
            clipped_occurrences = extraction.clipped_vertex_occurrence_count
            duplicates_removed = extraction.duplicate_face_count_removed
            degenerates_removed = extraction.degenerate_face_count_removed
            estimated_peak = int(
                candidates.planning_bytes
                + tile_plan.planning_bytes
                + extraction.estimated_peak_bytes
            )
            validated_pre_simplification_topology = extraction_topology
        tiled_metadata = {
            "contour_tile_plan": tile_plan.to_json_dict(include_tiles=True),
            "tiled_extraction": (
                None
                if extraction is None
                else extraction.to_json_dict(include_geometry=False)
            ),
            "mesh_repair_attempts": extraction_attempts,
            "mesh_repair_fallback_mode": mesh_fallback_mode,
            **({"coarse_recontour": coarse_metadata} if coarse_metadata else {}),
        }
    else:
        (
            fractional,
            cartesian,
            faces,
            raw_vertices,
            raw_faces,
            clipped_occurrences,
            duplicates_removed,
            degenerates_removed,
        ) = _mesh_nonwinding_components(
            field,
            candidates,
            components,
            max_raw_faces=raw_face_limit,
            max_raw_vertices=raw_vertex_limit,
        )
        estimated_peak = int(
            candidates.planning_bytes
            + raw_vertices * 3 * 8
            + raw_faces * 3 * 8
            + clipped_occurrences * 3 * 8
            + fractional.nbytes
            + cartesian.nbytes
            + faces.nbytes
        )
        validated_pre_simplification_topology = validate_periodic_canonical_mesh(
            fractional,
            cartesian,
            faces,
            display_cell=field.display_cell,
            logical_grid_shape=field.grid_shape,
            duplicate_face_count_removed=duplicates_removed,
            degenerate_face_count_removed=degenerates_removed,
        )
    if (
        validated_pre_simplification_topology is None
        or not _mesh_topology_is_valid(
            validated_pre_simplification_topology, field.display_cell
        )
    ):
        if allow_cloud_fallback:
            cloud = prepare_density_node_cloud(
                field, mass_fraction, max_points=cloud_max_points
            )
            return PreparedSparseDensitySurface(
                render_kind="node_cloud",
                mesh=None,
                cloud=cloud,
                fallback_mode="node_cloud",
            )
        raise GraphAdapterError(
            "Sparse contour remained invalid after extraction repair attempts."
        )
    base_fractional = fractional
    base_cartesian = cartesian
    base_faces = faces
    base_topology = validated_pre_simplification_topology
    simplification_metadata: dict[str, Any] = {}
    simplified = False
    if simplification_options is not None:
        from .density_mesh_simplify import (
            MeshSimplificationOptions,
            simplify_periodic_density_mesh,
        )

        if not isinstance(simplification_options, MeshSimplificationOptions):
            raise TypeError(
                "simplification_options must be MeshSimplificationOptions or None."
            )
        if simplification_options.enabled:
            resolved_simplification = simplification_options
            if resolved_simplification.target_faces is None:
                default_target = (
                    visual_target_faces
                    if visual_target_faces is not None
                    else standalone_final_face_limit
                )
                if default_target is not None:
                    resolved_simplification = MeshSimplificationOptions.from_json_dict(
                        {
                            **resolved_simplification.to_json_dict(),
                            "target_faces": int(default_target),
                        }
                    )
            simplification = simplify_periodic_density_mesh(
                field,
                fractional,
                cartesian,
                faces,
                contour_level=candidates.render_level,
                options=resolved_simplification,
            )
            fractional = simplification.vertices_fractional
            cartesian = simplification.vertices_cartesian
            faces = simplification.faces
            estimated_peak = max(estimated_peak, simplification.estimated_peak_bytes)
            simplified = True
            simplification_metadata = {
                "mesh_simplification": simplification.to_json_dict(
                    include_geometry=False
                )
            }
    topology = validate_periodic_canonical_mesh(
        fractional,
        cartesian,
        faces,
        display_cell=field.display_cell,
        logical_grid_shape=validation_grid_shape,
        duplicate_face_count_removed=duplicates_removed,
        degenerate_face_count_removed=degenerates_removed,
        fallback_mode=mesh_fallback_mode,
    )
    if not _mesh_topology_is_valid(topology, field.display_cell):
        # A simplification candidate is never allowed to poison a previously
        # valid extraction.  Restore the validated base mesh and let the scene
        # fitter choose a different reduction or recontour path.
        fractional = base_fractional
        cartesian = base_cartesian
        faces = base_faces
        topology = base_topology
        simplified = False
        simplification_metadata = {
            **simplification_metadata,
            "invalid_simplification_fallback": True,
        }
    face_report = evaluate_density_mesh_face_contract(
        int(faces.shape[0]),
        resolved_face_contract,
    )
    if face_report.standalone_final_limit_met is False:
        assert standalone_final_face_limit is not None
        _require_sparse_mesh_face_limit(
            int(faces.shape[0]),
            int(standalone_final_face_limit),
            after_simplification=True,
        )
    if (
        not simplified
        and mesh_fallback_mode == "none"
        and topology.maximum_mesh_edge_length > topology.mesh_edge_length_upper_bound
    ):
        raise GraphAdapterError("Sparse mesh contains an overlong logical-cell edge.")
    if estimated_peak > workspace_limit:
        raise GraphComplexityError(
            f"Sparse mesh estimated peak bytes {estimated_peak} exceed "
            f"max_workspace_bytes={workspace_limit}."
        )
    resources = SparseMeshResources(
        stored_node_count=field.storage_summary().nonzero_node_count,
        adjacent_cell_count=candidates.adjacent_cell_count,
        candidate_cell_count=candidates.candidate_cell_count,
        component_count=len(components),
        raw_vertex_count=raw_vertices,
        raw_face_count=raw_faces,
        clipped_vertex_occurrence_count=clipped_occurrences,
        canonical_vertex_count=fractional.shape[0],
        canonical_face_count=faces.shape[0],
        estimated_peak_bytes=estimated_peak,
    )
    mesh = PeriodicSparseDensityMesh3D(
        vertices_fractional=fractional,
        vertices_cartesian=cartesian,
        faces=faces,
        scientific_hdr_threshold=details.threshold,
        render_level=candidates.render_level,
        requested_mass_fraction=mass_fraction,
        achieved_mass_fraction=details.achieved_mass_fraction,
        resources=resources,
        topology=topology,
        metadata={
            "candidate_cells": candidates.to_json_dict(),
            "components": [component.to_json_dict() for component in components],
            "contouring": (
                "coarse_recontour_lewiner_v1"
                if mesh_fallback_mode == "coarse_recontour"
                else (
                    "bounded_tile_lewiner_v1"
                    if extraction_method == "tiled"
                    else "cell_aware_lewiner_2x2x2"
                )
            ),
            "canonical_clipping": "inside_outside_intersecting_fast_path_v1",
            "mesh_face_contract": resolved_face_contract.to_json_dict(),
            "mesh_face_report": face_report.to_json_dict(),
            "visual_target_met": face_report.visual_target_met,
            "visual_target_overage_faces": face_report.visual_target_overage_faces,
            **tiled_metadata,
            **simplification_metadata,
        },
    )
    return PreparedSparseDensitySurface(
        render_kind="mesh",
        mesh=mesh,
        cloud=None,
        fallback_mode=mesh_fallback_mode,
    )
