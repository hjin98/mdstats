"""Bounded tiled marching-cubes extraction for LD9-V1.

Each render tile owns a disjoint rectangular set of logical cells and includes
one node halo on its positive faces.  Lewiner marching cubes is invoked once per
owned tile.  Vertices shared by adjacent tiles are merged with deterministic
logical-grid-edge keys; seam-plane copies at fractional 0 and 1 remain distinct
so the canonical periodic cut can be validated and rendered correctly.

The implementation follows the marching-cubes geometry of Lorensen and Cline
(SIGGRAPH 1987, DOI: 10.1145/37402.37422) and the topologically consistent case
resolution of Lewiner et al. (JGT 2003, DOI: 10.1080/10867651.2003.10487582).
Tile ownership, logical-edge indexing, periodic seam handling, and bounded
resource contracts are mdstats-specific.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Hashable

import numpy as np
from numpy.typing import NDArray

from .density_contour_tiles import ContourTilePlan, MeshExtractionOptions
from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import (
    GraphAdapterError,
    GraphComplexityError,
    GraphUnsupportedFeatureError,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

TILED_MESH_TILE_REPORT_SCHEMA = "mdstats.tiled-mesh-tile-report.v2"
TILED_MESH_TILE_REPORT_LEGACY_SCHEMA = "mdstats.tiled-mesh-tile-report.v1"
TILED_MESH_EXTRACTION_SCHEMA = "mdstats.tiled-mesh-extraction.v2"
TILED_MESH_EXTRACTION_LEGACY_SCHEMA = "mdstats.tiled-mesh-extraction.v1"


def _readonly(value: Any, dtype: Any, *, ndim: int, name: str) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise GraphAdapterError(f"{name} must be {ndim}-dimensional.")
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain finite values.")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class TiledMeshTileReport:
    """Actual extraction and fast-path counts for one released render tile."""

    tile_index: tuple[int, int, int]
    crossing_cell_count: int
    scalar_node_count: int
    marching_cubes_call_count: int
    raw_vertex_count: int
    raw_face_count: int
    new_indexed_vertex_count: int
    retained_face_count: int
    wholly_inside_face_count: int
    wholly_outside_face_count: int
    boundary_intersecting_face_count: int
    clipped_output_face_count: int
    estimated_transient_bytes: int
    local_presimplification_attempted_components: int = 0
    local_presimplification_accepted_components: int = 0
    local_presimplification_input_faces: int = 0
    local_presimplification_output_faces: int = 0
    schema_version: str = TILED_MESH_TILE_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {
            TILED_MESH_TILE_REPORT_SCHEMA,
            TILED_MESH_TILE_REPORT_LEGACY_SCHEMA,
        }:
            raise GraphAdapterError(
                f"Unsupported tiled-mesh-tile-report schema {self.schema_version!r}."
            )
        if self.schema_version == TILED_MESH_TILE_REPORT_LEGACY_SCHEMA:
            object.__setattr__(self, "schema_version", TILED_MESH_TILE_REPORT_SCHEMA)
        if len(self.tile_index) != 3:
            raise GraphAdapterError("tile_index must have three entries.")
        object.__setattr__(self, "tile_index", tuple(int(v) for v in self.tile_index))
        for name in (
            "crossing_cell_count",
            "scalar_node_count",
            "marching_cubes_call_count",
            "raw_vertex_count",
            "raw_face_count",
            "new_indexed_vertex_count",
            "retained_face_count",
            "wholly_inside_face_count",
            "wholly_outside_face_count",
            "boundary_intersecting_face_count",
            "clipped_output_face_count",
            "estimated_transient_bytes",
            "local_presimplification_attempted_components",
            "local_presimplification_accepted_components",
            "local_presimplification_input_faces",
            "local_presimplification_output_faces",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tile_index": list(self.tile_index),
            **{
                name: getattr(self, name)
                for name in (
                    "crossing_cell_count",
                    "scalar_node_count",
                    "marching_cubes_call_count",
                    "raw_vertex_count",
                    "raw_face_count",
                    "new_indexed_vertex_count",
                    "retained_face_count",
                    "wholly_inside_face_count",
                    "wholly_outside_face_count",
                    "boundary_intersecting_face_count",
                    "clipped_output_face_count",
                    "estimated_transient_bytes",
                    "local_presimplification_attempted_components",
                    "local_presimplification_accepted_components",
                    "local_presimplification_input_faces",
                    "local_presimplification_output_faces",
                )
            },
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "TiledMeshTileReport":
        return cls(
            tile_index=tuple(value["tile_index"]),
            crossing_cell_count=int(value["crossing_cell_count"]),
            scalar_node_count=int(value["scalar_node_count"]),
            marching_cubes_call_count=int(value["marching_cubes_call_count"]),
            raw_vertex_count=int(value["raw_vertex_count"]),
            raw_face_count=int(value["raw_face_count"]),
            new_indexed_vertex_count=int(value["new_indexed_vertex_count"]),
            retained_face_count=int(value["retained_face_count"]),
            wholly_inside_face_count=int(value["wholly_inside_face_count"]),
            wholly_outside_face_count=int(value["wholly_outside_face_count"]),
            boundary_intersecting_face_count=int(
                value["boundary_intersecting_face_count"]
            ),
            clipped_output_face_count=int(value["clipped_output_face_count"]),
            estimated_transient_bytes=int(value["estimated_transient_bytes"]),
            local_presimplification_attempted_components=int(value.get("local_presimplification_attempted_components", 0)),
            local_presimplification_accepted_components=int(value.get("local_presimplification_accepted_components", 0)),
            local_presimplification_input_faces=int(value.get("local_presimplification_input_faces", 0)),
            local_presimplification_output_faces=int(value.get("local_presimplification_output_faces", 0)),
            schema_version=str(
                value.get("schema_version", TILED_MESH_TILE_REPORT_SCHEMA)
            ),
        )


@dataclass(frozen=True, slots=True)
class TiledMeshExtractionResult:
    """Indexed canonical mesh and bounded extraction evidence."""

    vertices_fractional: FloatArray
    vertices_cartesian: FloatArray
    faces: IntArray
    tile_reports: tuple[TiledMeshTileReport, ...]
    raw_vertex_count: int
    raw_face_count: int
    duplicate_face_count_removed: int
    degenerate_face_count_removed: int
    clipped_vertex_occurrence_count: int
    maximum_tile_transient_bytes: int
    retained_geometry_bytes: int
    estimated_peak_bytes: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = TILED_MESH_EXTRACTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {
            TILED_MESH_EXTRACTION_SCHEMA,
            TILED_MESH_EXTRACTION_LEGACY_SCHEMA,
        }:
            raise GraphAdapterError(
                f"Unsupported tiled-mesh-extraction schema {self.schema_version!r}."
            )
        if self.schema_version == TILED_MESH_EXTRACTION_LEGACY_SCHEMA:
            object.__setattr__(self, "schema_version", TILED_MESH_EXTRACTION_SCHEMA)
        fractional = _readonly(
            self.vertices_fractional, np.float64, ndim=2, name="vertices_fractional"
        )
        cartesian = _readonly(
            self.vertices_cartesian, np.float64, ndim=2, name="vertices_cartesian"
        )
        faces = _readonly(self.faces, np.int64, ndim=2, name="faces")
        if fractional.shape != cartesian.shape or fractional.shape[1:] != (3,):
            raise GraphAdapterError("Vertex arrays must align with shape (n, 3).")
        if faces.shape[1:] != (3,):
            raise GraphAdapterError("faces must have shape (n, 3).")
        if faces.size and (
            int(np.min(faces)) < 0 or int(np.max(faces)) >= fractional.shape[0]
        ):
            raise GraphAdapterError("Face index lies outside the vertex array.")
        object.__setattr__(self, "vertices_fractional", fractional)
        object.__setattr__(self, "vertices_cartesian", cartesian)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(self, "tile_reports", tuple(self.tile_reports))
        for name in (
            "raw_vertex_count",
            "raw_face_count",
            "duplicate_face_count_removed",
            "degenerate_face_count_removed",
            "clipped_vertex_occurrence_count",
            "maximum_tile_transient_bytes",
            "retained_geometry_bytes",
            "estimated_peak_bytes",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def marching_cubes_call_count(self) -> int:
        return sum(item.marching_cubes_call_count for item in self.tile_reports)

    def to_json_dict(self, *, include_geometry: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "vertex_count": int(self.vertices_fractional.shape[0]),
            "face_count": int(self.faces.shape[0]),
            "tile_count": len(self.tile_reports),
            "marching_cubes_call_count": self.marching_cubes_call_count,
            "raw_vertex_count": self.raw_vertex_count,
            "raw_face_count": self.raw_face_count,
            "duplicate_face_count_removed": self.duplicate_face_count_removed,
            "degenerate_face_count_removed": self.degenerate_face_count_removed,
            "clipped_vertex_occurrence_count": self.clipped_vertex_occurrence_count,
            "maximum_tile_transient_bytes": self.maximum_tile_transient_bytes,
            "retained_geometry_bytes": self.retained_geometry_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "tile_reports": [item.to_json_dict() for item in self.tile_reports],
            "metadata": self.metadata.to_json_dict(),
        }
        if include_geometry:
            result.update(
                {
                    "vertices_fractional": self.vertices_fractional.tolist(),
                    "vertices_cartesian": self.vertices_cartesian.tolist(),
                    "faces": self.faces.tolist(),
                }
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "TiledMeshExtractionResult":
        for name in ("vertices_fractional", "vertices_cartesian", "faces"):
            if name not in value:
                raise GraphAdapterError(
                    "Tiled mesh extraction JSON requires geometry arrays; "
                    "serialize with include_geometry=True."
                )
        result = cls(
            vertices_fractional=np.asarray(value["vertices_fractional"], dtype=np.float64),
            vertices_cartesian=np.asarray(value["vertices_cartesian"], dtype=np.float64),
            faces=np.asarray(value["faces"], dtype=np.int64),
            tile_reports=tuple(
                TiledMeshTileReport.from_json_dict(item)
                for item in value.get("tile_reports", ())
            ),
            raw_vertex_count=int(value["raw_vertex_count"]),
            raw_face_count=int(value["raw_face_count"]),
            duplicate_face_count_removed=int(value["duplicate_face_count_removed"]),
            degenerate_face_count_removed=int(value["degenerate_face_count_removed"]),
            clipped_vertex_occurrence_count=int(value["clipped_vertex_occurrence_count"]),
            maximum_tile_transient_bytes=int(value["maximum_tile_transient_bytes"]),
            retained_geometry_bytes=int(value["retained_geometry_bytes"]),
            estimated_peak_bytes=int(value["estimated_peak_bytes"]),
            metadata=value.get("metadata", {}),
            schema_version=str(value.get("schema_version", TILED_MESH_EXTRACTION_SCHEMA)),
        )
        if int(value.get("vertex_count", result.vertices_fractional.shape[0])) != result.vertices_fractional.shape[0]:
            raise GraphAdapterError("Serialized tiled-mesh vertex_count does not match geometry.")
        if int(value.get("face_count", result.faces.shape[0])) != result.faces.shape[0]:
            raise GraphAdapterError("Serialized tiled-mesh face_count does not match geometry.")
        if int(value.get("tile_count", len(result.tile_reports))) != len(result.tile_reports):
            raise GraphAdapterError("Serialized tiled-mesh tile_count does not match reports.")
        return result


class _IndexedMeshBuilder:
    """Array-backed occurrence builder with compiled final reconciliation.

    Tiles append immutable vertex-key and face-occurrence arrays.  Cross-tile
    vertex welding, coordinate consistency, degenerate rejection, duplicate-face
    removal, and canonical ordering are deferred to one NumPy sort/reduce pass.
    """

    def __init__(self) -> None:
        self.key_chunks: list[np.ndarray] = []
        self.vertex_chunks: list[np.ndarray] = []
        self.vertex_owner_chunks: list[np.ndarray] = []
        self.face_chunks: list[np.ndarray] = []
        self.face_owner_chunks: list[np.ndarray] = []
        self.vertex_occurrence_count = 0
        self.face_occurrence_count = 0

    def add_vertices(
        self,
        keys: np.ndarray,
        coordinates: np.ndarray,
        *,
        owner: int,
    ) -> np.ndarray:
        key_array = np.asarray(keys, dtype=np.int64)
        coordinate_array = np.asarray(coordinates, dtype=np.float64)
        if key_array.ndim != 2 or key_array.shape[1:] != (4,):
            raise GraphAdapterError("Tiled-mesh vertex keys must have shape (n, 4).")
        if coordinate_array.shape != (key_array.shape[0], 3):
            raise GraphAdapterError("Vertex coordinates must align with key rows.")
        start = self.vertex_occurrence_count
        stop = start + key_array.shape[0]
        self.key_chunks.append(np.ascontiguousarray(key_array))
        self.vertex_chunks.append(np.ascontiguousarray(coordinate_array))
        self.vertex_owner_chunks.append(
            np.full(key_array.shape[0], int(owner), dtype=np.int32)
        )
        self.vertex_occurrence_count = stop
        return np.arange(start, stop, dtype=np.int64)

    def add_faces(self, faces: np.ndarray, *, owner: int) -> int:
        face_array = np.asarray(faces, dtype=np.int64)
        if face_array.size == 0:
            return 0
        if face_array.ndim != 2 or face_array.shape[1:] != (3,):
            raise GraphAdapterError("Tiled-mesh faces must have shape (n, 3).")
        self.face_chunks.append(np.ascontiguousarray(face_array))
        self.face_owner_chunks.append(
            np.full(face_array.shape[0], int(owner), dtype=np.int32)
        )
        self.face_occurrence_count += int(face_array.shape[0])
        return int(face_array.shape[0])

    @property
    def faces(self) -> bool:
        return self.face_occurrence_count > 0


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
            if denominator != 0.0:
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
    return [
        np.asarray((polygon[0], polygon[index], polygon[index + 1]), dtype=np.float64)
        for index in range(1, len(polygon) - 1)
    ]


def _geometric_keys(points: np.ndarray) -> np.ndarray:
    values = np.asarray(points, dtype=np.float64)
    if values.ndim != 2 or values.shape[1:] != (3,):
        raise GraphAdapterError("Geometric key points must have shape (n, 3).")
    scale = 10**13
    return np.column_stack(
        (
            np.full(values.shape[0], 4, dtype=np.int64),
            np.rint(values * scale).astype(np.int64),
        )
    )


def _geometric_key(point: np.ndarray) -> tuple[int, int, int, int]:
    return tuple(int(value) for value in _geometric_keys(np.asarray(point)[None, :])[0])


def _gather_tile_volume(field: Any, start: np.ndarray, stop: np.ndarray) -> np.ndarray:
    shape = np.asarray(field.grid_shape, dtype=np.int64)
    node_shape = tuple(int(stop[a] - start[a] + 1) for a in range(3))
    local = np.indices(node_shape, dtype=np.int64).reshape(3, -1).T
    lifted = local + start[None, :]
    canonical = np.mod(lifted, shape[None, :])
    values = field.gather_node_values(canonical)
    volume = np.asarray(values, dtype=np.float32).reshape(node_shape)
    return volume


def _precise_vertices_and_keys(
    raw_vertices: np.ndarray,
    volume: np.ndarray,
    *,
    cell_start: np.ndarray,
    logical_shape: np.ndarray,
    level32: np.float32,
) -> tuple[np.ndarray, np.ndarray]:
    """Recover exact logical-edge coordinates with vectorized NumPy kernels."""

    local = np.asarray(raw_vertices, dtype=np.float64)
    if local.ndim != 2 or local.shape[1:] != (3,):
        raise GraphAdapterError("raw_vertices must have shape (n, 3).")
    count = int(local.shape[0])
    nearest = np.rint(local).astype(np.int64)
    residual = np.abs(local - nearest)
    axes = np.argmax(residual, axis=1).astype(np.int64, copy=False)
    rows = np.arange(count, dtype=np.int64)
    maximum_residual = residual[rows, axes]
    node_mask = maximum_residual <= 1.0e-10
    edge_mask = ~node_mask

    precise_lifted = np.empty_like(local)
    key_matrix = np.empty((count, 4), dtype=np.int64)
    if np.any(node_mask):
        lifted_nodes = nearest[node_mask] + np.asarray(cell_start, dtype=np.int64)[None, :]
        precise_lifted[node_mask] = lifted_nodes
        key_matrix[node_mask, 0] = 3
        key_matrix[node_mask, 1:] = lifted_nodes

    edge_rows = np.flatnonzero(edge_mask).astype(np.int64, copy=False)
    if edge_rows.size:
        edge_axes = axes[edge_rows]
        local_edge = local[edge_rows]
        endpoint0 = nearest[edge_rows].copy()
        local_rows = np.arange(edge_rows.size, dtype=np.int64)
        endpoint0[local_rows, edge_axes] = np.floor(
            local_edge[local_rows, edge_axes] + 1.0e-7
        ).astype(np.int64)
        endpoint1 = endpoint0.copy()
        endpoint1[local_rows, edge_axes] += 1
        volume_shape = np.asarray(volume.shape, dtype=np.int64)
        if np.any(endpoint0 < 0) or np.any(endpoint1 >= volume_shape[None, :]):
            raise GraphAdapterError("Marching-cubes vertex does not lie on a tile edge.")
        value0 = np.asarray(
            volume[endpoint0[:, 0], endpoint0[:, 1], endpoint0[:, 2]],
            dtype=np.float64,
        )
        value1 = np.asarray(
            volume[endpoint1[:, 0], endpoint1[:, 1], endpoint1[:, 2]],
            dtype=np.float64,
        )
        denominator = value1 - value0
        geometric_factor = local_edge[local_rows, edge_axes] - endpoint0[
            local_rows, edge_axes
        ]
        factors = np.divide(
            float(level32) - value0,
            denominator,
            out=geometric_factor.copy(),
            where=denominator != 0.0,
        )
        factors = np.clip(factors, 0.0, 1.0)
        precise = endpoint0.astype(np.float64)
        precise[local_rows, edge_axes] += factors
        lifted_base = endpoint0 + np.asarray(cell_start, dtype=np.int64)[None, :]
        precise_lifted[edge_rows] = precise + np.asarray(cell_start, dtype=np.float64)[None, :]
        key_matrix[edge_rows, 0] = edge_axes
        key_matrix[edge_rows, 1:] = lifted_base

    fractional = precise_lifted / np.asarray(logical_shape, dtype=np.float64)[None, :]
    fractional[np.abs(fractional) < 2.0e-14] = 0.0
    fractional[np.abs(fractional - 1.0) < 2.0e-14] = 1.0
    return fractional, np.ascontiguousarray(key_matrix)


def _key_sort_token(key: Hashable) -> tuple[int, int, int, int]:
    if isinstance(key, tuple) and len(key) == 4 and key[0] == "clip":
        return (4, int(key[1]), int(key[2]), int(key[3]))
    if isinstance(key, tuple) and len(key) == 4:
        return tuple(int(v) for v in key)  # type: ignore[return-value]
    raise GraphAdapterError("Unsupported tiled-mesh vertex key.")


def _finalize_indexed_geometry(
    builder: _IndexedMeshBuilder,
    field: Any,
    level32: np.float32,
    *,
    tile_count: int,
) -> tuple[np.ndarray, np.ndarray, int, int, np.ndarray, np.ndarray]:
    """Weld occurrence geometry with array sort/reduce kernels."""

    if not builder.face_chunks or not builder.key_chunks:
        raise GraphAdapterError("No indexed tiled geometry was accumulated.")
    keys = np.concatenate(builder.key_chunks, axis=0)
    source_vertices = np.concatenate(builder.vertex_chunks, axis=0)
    vertex_owners = np.concatenate(builder.vertex_owner_chunks, axis=0)
    occurrence_faces = np.concatenate(builder.face_chunks, axis=0)
    face_owners = np.concatenate(builder.face_owner_chunks, axis=0)

    unique_keys, first_occurrence, occurrence_to_unique = np.unique(
        keys,
        axis=0,
        return_index=True,
        return_inverse=True,
    )
    reference_vertices = source_vertices[first_occurrence]
    mismatch = float(
        np.max(
            np.abs(source_vertices - reference_vertices[occurrence_to_unique]),
            initial=0.0,
        )
    )
    if mismatch > 2.0e-13:
        raise GraphAdapterError(
            "Logical-edge key produced inconsistent vertex coordinates."
        )
    new_vertices_by_tile = np.bincount(
        vertex_owners[first_occurrence], minlength=tile_count
    ).astype(np.int64, copy=False)

    shape = np.asarray(field.grid_shape, dtype=np.int64)
    coordinates = np.empty((unique_keys.shape[0], 3), dtype=np.float64)
    marker = unique_keys[:, 0]
    clip_mask = marker >= 4
    if np.any(clip_mask):
        coordinates[clip_mask] = reference_vertices[clip_mask]
    node_mask = marker == 3
    if np.any(node_mask):
        coordinates[node_mask] = unique_keys[node_mask, 1:] / shape[None, :]
    edge_mask = marker < 3
    if np.any(edge_mask):
        edge_rows = np.flatnonzero(edge_mask).astype(np.int64, copy=False)
        edge_axes = unique_keys[edge_rows, 0].astype(np.int64, copy=False)
        bases = unique_keys[edge_rows, 1:].astype(np.int64, copy=False)
        endpoints0 = np.mod(bases, shape[None, :])
        endpoints1 = endpoints0.copy()
        local_rows = np.arange(endpoints1.shape[0], dtype=np.int64)
        endpoints1[local_rows, edge_axes] = (
            endpoints1[local_rows, edge_axes] + 1
        ) % shape[edge_axes]
        values0 = np.asarray(field.gather_node_values(endpoints0), dtype=np.float64)
        values1 = np.asarray(field.gather_node_values(endpoints1), dtype=np.float64)
        denominators = values1 - values0
        factors = np.divide(
            float(level32) - values0,
            denominators,
            out=np.full(values0.size, 0.5, dtype=np.float64),
            where=denominators != 0.0,
        )
        factors = np.clip(factors, 0.0, 1.0)
        precise = bases.astype(np.float64)
        precise[local_rows, edge_axes] += factors
        coordinates[edge_rows] = precise / shape[None, :]
    coordinates[np.abs(coordinates) < 2.0e-14] = 0.0
    coordinates[np.abs(coordinates - 1.0) < 2.0e-14] = 1.0

    faces = occurrence_to_unique[occurrence_faces]
    repeated_vertex = (
        (faces[:, 0] == faces[:, 1])
        | (faces[:, 1] == faces[:, 2])
        | (faces[:, 0] == faces[:, 2])
    )
    cartesian = coordinates @ np.asarray(field.display_cell, dtype=np.float64)
    triangle_points = cartesian[faces]
    twice_area = np.linalg.norm(
        np.cross(
            triangle_points[:, 1] - triangle_points[:, 0],
            triangle_points[:, 2] - triangle_points[:, 0],
        ),
        axis=1,
    )
    reference_length = max(
        float(np.linalg.norm(vector))
        for vector in np.asarray(field.display_cell, dtype=np.float64)
    )
    area_tolerance = max(1.0e-14, 1.0e-10 * reference_length) ** 2
    degenerate_mask = repeated_vertex | (twice_area <= area_tolerance)
    degenerate_count = int(np.count_nonzero(degenerate_mask))
    faces = faces[~degenerate_mask]
    retained_owners = face_owners[~degenerate_mask]
    if faces.size == 0:
        raise GraphAdapterError("Tiled contour contained no nondegenerate faces.")

    unordered = np.sort(faces, axis=1)
    _unique_unordered, first_faces = np.unique(
        unordered, axis=0, return_index=True
    )
    duplicate_count = int(faces.shape[0] - first_faces.size)
    faces = faces[first_faces]
    retained_owners = retained_owners[first_faces]
    minimum_positions = np.argmin(faces, axis=1)
    gather = (minimum_positions[:, None] + np.arange(3)[None, :]) % 3
    faces = np.take_along_axis(faces, gather, axis=1)
    face_order = np.lexsort((faces[:, 2], faces[:, 1], faces[:, 0]))
    faces = faces[face_order]
    retained_owners = retained_owners[face_order]
    retained_faces_by_tile = np.bincount(
        retained_owners, minlength=tile_count
    ).astype(np.int64, copy=False)
    return (
        np.ascontiguousarray(coordinates),
        np.ascontiguousarray(faces),
        duplicate_count,
        degenerate_count,
        new_vertices_by_tile,
        retained_faces_by_tile,
    )


def extract_tiled_density_mesh(
    field: Any,
    plan: ContourTilePlan,
    *,
    options: MeshExtractionOptions | None = None,
    local_simplification_options: Any | None = None,
) -> TiledMeshExtractionResult:
    """Extract one indexed contour by bounded tile-level marching cubes."""

    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise GraphUnsupportedFeatureError(
            "Tiled density meshing requires scikit-image. Install mdstats[interactive]."
        ) from exc
    resolved = MeshExtractionOptions() if options is None else options
    if not isinstance(resolved, MeshExtractionOptions):
        raise TypeError("options must be MeshExtractionOptions or None.")
    resolved_local_simplification = None
    if local_simplification_options is not None:
        from .density_mesh_simplify import MeshSimplificationOptions
        if not isinstance(local_simplification_options, MeshSimplificationOptions):
            raise TypeError(
                "local_simplification_options must be MeshSimplificationOptions or None."
            )
        if local_simplification_options.local_presimplification:
            resolved_local_simplification = local_simplification_options
    if str(field.field_key) != plan.field_key or tuple(field.grid_shape) != plan.logical_grid_shape:
        raise GraphAdapterError("Contour tile plan does not match the density field.")
    if resolved.render_tile_shape != plan.render_tile_shape:
        raise GraphAdapterError("Extraction tile shape does not match the approved plan.")
    builder = _IndexedMeshBuilder()
    report_payloads: list[dict[str, Any]] = []
    total_raw_vertices = 0
    total_raw_faces = 0
    clipped_occurrences = 0
    maximum_transient = 0
    level32 = np.float32(plan.render_level)
    logical_shape = np.asarray(plan.logical_grid_shape, dtype=np.float64)
    for tile_owner, tile in enumerate(plan.tiles):
        start = np.asarray(tile.cell_start, dtype=np.int64)
        stop = np.asarray(tile.cell_stop, dtype=np.int64)
        volume = _gather_tile_volume(field, start, stop)
        if int(volume.size) != tile.scalar_node_count:
            raise GraphAdapterError("Tile scalar-node count disagrees with its plan.")
        minimum = float(np.min(volume))
        maximum = float(np.max(volume))
        if not minimum <= float(level32) <= maximum or minimum == maximum:
            raise GraphAdapterError(
                "A planned crossing tile does not bracket the contour level."
            )
        vertices, faces, _normals, _values = marching_cubes(
            volume,
            level=float(level32),
            spacing=(1.0, 1.0, 1.0),
            allow_degenerate=False,
            method="lewiner",
        )
        raw_vertex_count = int(vertices.shape[0])
        raw_face_count = int(faces.shape[0])
        if raw_vertex_count > resolved.max_raw_vertices_per_tile:
            raise GraphComplexityError(
                f"Tile {tile.tile_index} produced {raw_vertex_count} raw vertices, "
                f"exceeding max_raw_vertices_per_tile="
                f"{resolved.max_raw_vertices_per_tile}."
            )
        if raw_face_count > resolved.max_raw_faces_per_tile:
            raise GraphComplexityError(
                f"Tile {tile.tile_index} produced {raw_face_count} raw faces, "
                f"exceeding max_raw_faces_per_tile={resolved.max_raw_faces_per_tile}."
            )
        total_raw_vertices += raw_vertex_count
        total_raw_faces += raw_face_count
        if total_raw_vertices > resolved.max_total_raw_vertices:
            raise GraphComplexityError("Total raw vertex limit exceeded during tiled extraction.")
        if total_raw_faces > resolved.max_total_raw_faces:
            raise GraphComplexityError("Total raw face limit exceeded during tiled extraction.")
        fractional, keys = _precise_vertices_and_keys(
            vertices,
            volume,
            cell_start=start,
            logical_shape=logical_shape,
            level32=level32,
        )
        local_report = {
            "attempted_components": 0,
            "accepted_components": 0,
            "input_faces": raw_face_count,
            "output_faces": raw_face_count,
        }
        if resolved_local_simplification is not None:
            from .density_mesh_simplify import presimplify_closed_tile_components
            cell_shape = (stop - start).astype(np.float64)
            protected_vertex_mask = np.any(
                (np.asarray(vertices, dtype=np.float64) <= 1.0e-7)
                | (np.abs(np.asarray(vertices, dtype=np.float64) - cell_shape[None, :]) <= 1.0e-7),
                axis=1,
            )
            namespace = (
                int(tile.tile_index[0]) * 10**12
                + int(tile.tile_index[1]) * 10**6
                + int(tile.tile_index[2])
            )
            fractional, faces, keys, local_report = presimplify_closed_tile_components(
                fractional,
                np.asarray(faces, dtype=np.int64),
                protected_vertex_mask,
                keys,
                display_cell=field.display_cell,
                namespace=namespace,
                options=resolved_local_simplification,
            )
        indexed_vertex_count = int(fractional.shape[0])
        raw_to_global = builder.add_vertices(
            np.asarray(keys, dtype=np.int64),
            fractional,
            owner=tile_owner,
        )
        face_array = np.asarray(faces, dtype=np.int64)
        triangles = fractional[face_array]
        inside_mask = np.all(
            (triangles >= -1.0e-13) & (triangles <= 1.0 + 1.0e-13),
            axis=(1, 2),
        )
        below = np.all(triangles < -1.0e-13, axis=1)
        above = np.all(triangles > 1.0 + 1.0e-13, axis=1)
        outside_mask = (~inside_mask) & np.any(below | above, axis=1)
        intersecting_mask = ~(inside_mask | outside_mask)
        inside_count = int(np.count_nonzero(inside_mask))
        outside_count = int(np.count_nonzero(outside_mask))
        intersecting_count = int(np.count_nonzero(intersecting_mask))
        if inside_count:
            builder.add_faces(
                raw_to_global[face_array[inside_mask]], owner=tile_owner
            )
        clipped_face_count = 0
        clipped_face_parts: list[np.ndarray] = []
        for triangle in triangles[intersecting_mask]:
            clipped = _clip_triangle_to_unit_cube(triangle)
            if not clipped:
                continue
            clipped_array = np.asarray(clipped, dtype=np.float64).reshape(-1, 3)
            clipped_array = np.clip(clipped_array, 0.0, 1.0)
            clipped_indices = builder.add_vertices(
                _geometric_keys(clipped_array),
                clipped_array,
                owner=tile_owner,
            ).reshape(-1, 3)
            clipped_face_parts.append(clipped_indices)
            clipped_occurrences += int(clipped_array.shape[0])
            clipped_face_count += int(clipped_indices.shape[0])
        if clipped_face_parts:
            builder.add_faces(
                np.concatenate(clipped_face_parts, axis=0), owner=tile_owner
            )
        actual_transient = int(
            volume.nbytes
            + vertices.nbytes
            + faces.nbytes
            + fractional.nbytes
            + raw_to_global.nbytes
        )
        if actual_transient > resolved.max_transient_mesh_bytes:
            raise GraphComplexityError(
                f"Tile {tile.tile_index} used approximately {actual_transient} transient "
                f"bytes, exceeding max_transient_mesh_bytes="
                f"{resolved.max_transient_mesh_bytes}."
            )
        maximum_transient = max(maximum_transient, actual_transient)
        report_payloads.append(
            {
                "tile_index": tile.tile_index,
                "crossing_cell_count": tile.crossing_cell_count,
                "scalar_node_count": tile.scalar_node_count,
                "marching_cubes_call_count": 1,
                "raw_vertex_count": raw_vertex_count,
                "raw_face_count": raw_face_count,
                "new_indexed_vertex_count": 0,
                "retained_face_count": 0,
                "wholly_inside_face_count": inside_count,
                "wholly_outside_face_count": outside_count,
                "boundary_intersecting_face_count": intersecting_count,
                "clipped_output_face_count": clipped_face_count,
                "estimated_transient_bytes": actual_transient,
                "local_presimplification_attempted_components": int(local_report["attempted_components"]),
                "local_presimplification_accepted_components": int(local_report["accepted_components"]),
                "local_presimplification_input_faces": int(local_report["input_faces"]),
                "local_presimplification_output_faces": int(local_report["output_faces"]),
            }
        )
        # All dense tile arrays and raw marching-cubes geometry become unreachable
        # here.  Only indexed final geometry and the small immutable report remain.
        del volume, vertices, faces, fractional, raw_to_global
    if not builder.faces:
        raise GraphAdapterError("No triangular surface could be extracted from contour tiles.")
    (
        vertices_fractional,
        faces_array,
        duplicate_count,
        degenerate_count,
        new_vertices_by_tile,
        retained_faces_by_tile,
    ) = _finalize_indexed_geometry(
        builder, field, level32, tile_count=plan.tile_count
    )
    reports = tuple(
        TiledMeshTileReport(
            **{
                **payload,
                "new_indexed_vertex_count": int(new_vertices_by_tile[index]),
                "retained_face_count": int(retained_faces_by_tile[index]),
            }
        )
        for index, payload in enumerate(report_payloads)
    )
    cell = np.asarray(field.display_cell, dtype=np.float64)
    vertices_cartesian = np.ascontiguousarray(vertices_fractional @ cell)
    retained = int(
        vertices_fractional.nbytes + vertices_cartesian.nbytes + faces_array.nbytes
    )
    estimated_peak = retained + maximum_transient
    vertices_fractional.setflags(write=False)
    vertices_cartesian.setflags(write=False)
    faces_array.setflags(write=False)
    return TiledMeshExtractionResult(
        vertices_fractional=vertices_fractional,
        vertices_cartesian=vertices_cartesian,
        faces=faces_array,
        tile_reports=reports,
        raw_vertex_count=total_raw_vertices,
        raw_face_count=total_raw_faces,
        duplicate_face_count_removed=duplicate_count,
        degenerate_face_count_removed=degenerate_count,
        clipped_vertex_occurrence_count=clipped_occurrences,
        maximum_tile_transient_bytes=maximum_transient,
        retained_geometry_bytes=retained,
        estimated_peak_bytes=estimated_peak,
        metadata={
            "contouring": "bounded_tile_lewiner_v1",
            "vertex_indexing": "array_sort_unique_logical_grid_edge_keys_v2",
            "clipping_fast_path": "inside_outside_intersecting_v1",
            "raw_tile_geometry_retained_after_tile": False,
            "global_dense_grid_allocated": False,
            "render_tile_shape": list(plan.render_tile_shape),
            "tile_count": plan.tile_count,
            "local_presimplification": (
                "closed_tile_interior_qem_v1"
                if resolved_local_simplification is not None
                else "disabled"
            ),
        },
    )
