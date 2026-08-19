"""Bounded contour-tile planning for LD9-V1.

The scientific density field and HDR threshold are immutable inputs.  This
module partitions exact crossing logical cells into deterministic render tiles,
preflights one-tile raw geometry and transient workspace, and records the
complete work plan without allocating a dense global grid.

Marching-cubes extraction itself is implemented in :mod:`density_tiled_mesh`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

IntArray = NDArray[np.int64]

MESH_EXTRACTION_OPTIONS_SCHEMA = "mdstats.mesh-extraction-options.v1"
CONTOUR_RENDER_TILE_SCHEMA = "mdstats.contour-render-tile.v1"
CONTOUR_TILE_PLAN_SCHEMA = "mdstats.contour-tile-plan.v1"

DEFAULT_RENDER_TILE_SHAPE = (32, 32, 32)
DEFAULT_MAX_CROSSING_CELLS_PER_TILE = 131_072
DEFAULT_MAX_RAW_FACES_PER_TILE = 655_360
DEFAULT_MAX_RAW_VERTICES_PER_TILE = 1_572_864
DEFAULT_MAX_TRANSIENT_MESH_BYTES = 256 * 1024**2
DEFAULT_MAX_TOTAL_CROSSING_CELLS = 4_000_000
DEFAULT_MAX_TOTAL_RAW_FACES = 20_000_000
DEFAULT_MAX_TOTAL_RAW_VERTICES = 60_000_000
DEFAULT_MAX_PLANNING_WORKSPACE_BYTES = 512 * 1024**2


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _shape3(value: Sequence[int], *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphStyleError(f"{name} must contain exactly three entries.")
    return tuple(_positive_int(item, name=f"{name} entry") for item in value)  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class MeshExtractionOptions:
    """Raw tile and transient-workspace limits for one contour extraction."""

    render_tile_shape: tuple[int, int, int] = DEFAULT_RENDER_TILE_SHAPE
    max_crossing_cells_per_tile: int | None = None
    max_raw_faces_per_tile: int | None = None
    max_raw_vertices_per_tile: int | None = None
    max_transient_mesh_bytes: int | None = None
    max_total_crossing_cells: int | None = None
    max_total_raw_faces: int | None = None
    max_total_raw_vertices: int | None = None
    max_planning_workspace_bytes: int | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = MESH_EXTRACTION_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MESH_EXTRACTION_OPTIONS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported mesh-extraction-options schema {self.schema_version!r}."
            )
        object.__setattr__(
            self,
            "render_tile_shape",
            _shape3(self.render_tile_shape, name="render_tile_shape"),
        )
        budget, model, derived = resolve_density_resource_limits()
        tile_cells = int(np.prod(self.render_tile_shape, dtype=object))
        defaults = {
            "max_crossing_cells_per_tile": min(
                tile_cells, derived["max_density_mesh_cells"]
            ),
            "max_raw_faces_per_tile": min(
                5 * tile_cells, derived["max_density_mesh_faces"]
            ),
            "max_raw_vertices_per_tile": min(
                15 * tile_cells, 3 * derived["max_density_mesh_faces"]
            ),
            "max_transient_mesh_bytes": budget.max_memory_bytes,
            "max_total_crossing_cells": derived["max_density_mesh_cells"],
            "max_total_raw_faces": derived["max_density_mesh_faces"],
            "max_total_raw_vertices": 3 * derived["max_density_mesh_faces"],
            "max_planning_workspace_bytes": budget.max_memory_bytes,
        }
        memory_names = {
            "max_transient_mesh_bytes",
            "max_planning_workspace_bytes",
        }
        for name, default in defaults.items():
            current = getattr(self, name)
            resolved = default if current is None else min(default, _positive_int(current, name=name))
            if name in memory_names:
                resolved = min(resolved, budget.max_memory_bytes)
            object.__setattr__(self, name, resolved)
        metadata = dict(freeze_json_mapping(self.metadata))
        metadata.setdefault("resource_policy", "runtime_derived_v1")
        metadata.setdefault("max_threads", budget.max_threads)
        metadata.setdefault("max_wall_time_seconds", budget.max_wall_time_seconds)
        metadata.setdefault("time_model_source", model.calibration_source)
        object.__setattr__(self, "metadata", freeze_json_mapping(metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "render_tile_shape": list(self.render_tile_shape),
            "max_crossing_cells_per_tile": self.max_crossing_cells_per_tile,
            "max_raw_faces_per_tile": self.max_raw_faces_per_tile,
            "max_raw_vertices_per_tile": self.max_raw_vertices_per_tile,
            "max_transient_mesh_bytes": self.max_transient_mesh_bytes,
            "max_total_crossing_cells": self.max_total_crossing_cells,
            "max_total_raw_faces": self.max_total_raw_faces,
            "max_total_raw_vertices": self.max_total_raw_vertices,
            "max_planning_workspace_bytes": self.max_planning_workspace_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MeshExtractionOptions":
        def optional_int(name: str) -> int | None:
            raw = value.get(name)
            return None if raw is None else int(raw)

        return cls(
            render_tile_shape=tuple(value.get("render_tile_shape", DEFAULT_RENDER_TILE_SHAPE)),
            max_crossing_cells_per_tile=optional_int("max_crossing_cells_per_tile"),
            max_raw_faces_per_tile=optional_int("max_raw_faces_per_tile"),
            max_raw_vertices_per_tile=optional_int("max_raw_vertices_per_tile"),
            max_transient_mesh_bytes=optional_int("max_transient_mesh_bytes"),
            max_total_crossing_cells=optional_int("max_total_crossing_cells"),
            max_total_raw_faces=optional_int("max_total_raw_faces"),
            max_total_raw_vertices=optional_int("max_total_raw_vertices"),
            max_planning_workspace_bytes=optional_int("max_planning_workspace_bytes"),
            metadata=value.get("metadata", {}),
            schema_version=str(value.get("schema_version", MESH_EXTRACTION_OPTIONS_SCHEMA)),
        )


@dataclass(frozen=True, slots=True)
class ContourRenderTile:
    """One deterministic logical-cell tile containing contour crossings."""

    tile_index: tuple[int, int, int]
    cell_start: tuple[int, int, int]
    cell_stop: tuple[int, int, int]
    crossing_cell_count: int
    scalar_node_count: int
    raw_face_upper_bound: int
    raw_vertex_upper_bound: int
    estimated_transient_bytes: int
    schema_version: str = CONTOUR_RENDER_TILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CONTOUR_RENDER_TILE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported contour-render-tile schema {self.schema_version!r}."
            )
        tile = tuple(_positive_int(v, name="tile_index entry", minimum=0) for v in self.tile_index)
        start = tuple(_positive_int(v, name="cell_start entry", minimum=0) for v in self.cell_start)
        stop = tuple(_positive_int(v, name="cell_stop entry") for v in self.cell_stop)
        if len(tile) != 3 or len(start) != 3 or len(stop) != 3:
            raise GraphAdapterError("Tile coordinates must contain three entries.")
        if any(stop[a] <= start[a] for a in range(3)):
            raise GraphAdapterError("Each tile stop must exceed its start.")
        object.__setattr__(self, "tile_index", tile)
        object.__setattr__(self, "cell_start", start)
        object.__setattr__(self, "cell_stop", stop)
        for name in (
            "crossing_cell_count",
            "scalar_node_count",
            "raw_face_upper_bound",
            "raw_vertex_upper_bound",
            "estimated_transient_bytes",
        ):
            object.__setattr__(
                self, name, _positive_int(getattr(self, name), name=name)
            )

    @property
    def cell_shape(self) -> tuple[int, int, int]:
        return tuple(self.cell_stop[a] - self.cell_start[a] for a in range(3))

    @property
    def node_shape(self) -> tuple[int, int, int]:
        return tuple(value + 1 for value in self.cell_shape)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "tile_index": list(self.tile_index),
            "cell_start": list(self.cell_start),
            "cell_stop": list(self.cell_stop),
            "cell_shape": list(self.cell_shape),
            "node_shape": list(self.node_shape),
            "crossing_cell_count": self.crossing_cell_count,
            "scalar_node_count": self.scalar_node_count,
            "raw_face_upper_bound": self.raw_face_upper_bound,
            "raw_vertex_upper_bound": self.raw_vertex_upper_bound,
            "estimated_transient_bytes": self.estimated_transient_bytes,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "ContourRenderTile":
        return cls(
            tile_index=tuple(value["tile_index"]),
            cell_start=tuple(value["cell_start"]),
            cell_stop=tuple(value["cell_stop"]),
            crossing_cell_count=int(value["crossing_cell_count"]),
            scalar_node_count=int(value["scalar_node_count"]),
            raw_face_upper_bound=int(value["raw_face_upper_bound"]),
            raw_vertex_upper_bound=int(value["raw_vertex_upper_bound"]),
            estimated_transient_bytes=int(value["estimated_transient_bytes"]),
            schema_version=str(value.get("schema_version", CONTOUR_RENDER_TILE_SCHEMA)),
        )


@dataclass(frozen=True, slots=True)
class ContourTilePlan:
    """Complete bounded render-tile plan for one field and one HDR level."""

    field_key: str
    logical_grid_shape: tuple[int, int, int]
    render_tile_shape: tuple[int, int, int]
    scientific_hdr_threshold: float
    render_level: float
    candidate_cell_count: int
    tiles: tuple[ContourRenderTile, ...]
    total_raw_face_upper_bound: int
    total_raw_vertex_upper_bound: int
    maximum_tile_transient_bytes: int
    planning_bytes: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = CONTOUR_TILE_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != CONTOUR_TILE_PLAN_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported contour-tile-plan schema {self.schema_version!r}."
            )
        if not isinstance(self.field_key, str) or not self.field_key:
            raise GraphAdapterError("field_key must be nonempty.")
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        tile_shape = _shape3(self.render_tile_shape, name="render_tile_shape")
        scientific = float(self.scientific_hdr_threshold)
        render = float(self.render_level)
        if not np.isfinite(scientific) or scientific <= 0.0:
            raise GraphAdapterError("scientific_hdr_threshold must be positive.")
        if not np.isfinite(render) or render <= 0.0:
            raise GraphAdapterError("render_level must be positive.")
        ordered = tuple(self.tiles)
        if not ordered:
            raise GraphAdapterError("Contour tile plan must contain at least one tile.")
        if tuple(sorted(tile.tile_index for tile in ordered)) != tuple(
            tile.tile_index for tile in ordered
        ):
            raise GraphAdapterError("Contour tiles must be lexicographically ordered.")
        candidate_count = _positive_int(
            self.candidate_cell_count, name="candidate_cell_count"
        )
        if sum(tile.crossing_cell_count for tile in ordered) != candidate_count:
            raise GraphAdapterError("Tile crossing-cell counts do not match plan total.")
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "render_tile_shape", tile_shape)
        object.__setattr__(self, "scientific_hdr_threshold", scientific)
        object.__setattr__(self, "render_level", render)
        object.__setattr__(self, "candidate_cell_count", candidate_count)
        object.__setattr__(self, "tiles", ordered)
        for name in (
            "total_raw_face_upper_bound",
            "total_raw_vertex_upper_bound",
            "maximum_tile_transient_bytes",
            "planning_bytes",
        ):
            object.__setattr__(
                self, name, _positive_int(getattr(self, name), name=name)
            )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def tile_count(self) -> int:
        return len(self.tiles)

    def to_json_dict(self, *, include_tiles: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "logical_grid_shape": list(self.logical_grid_shape),
            "render_tile_shape": list(self.render_tile_shape),
            "scientific_hdr_threshold": self.scientific_hdr_threshold,
            "render_level": self.render_level,
            "candidate_cell_count": self.candidate_cell_count,
            "tile_count": self.tile_count,
            "total_raw_face_upper_bound": self.total_raw_face_upper_bound,
            "total_raw_vertex_upper_bound": self.total_raw_vertex_upper_bound,
            "maximum_tile_transient_bytes": self.maximum_tile_transient_bytes,
            "planning_bytes": self.planning_bytes,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_tiles:
            result["tiles"] = [tile.to_json_dict() for tile in self.tiles]
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "ContourTilePlan":
        return cls(
            field_key=str(value["field_key"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            render_tile_shape=tuple(value["render_tile_shape"]),
            scientific_hdr_threshold=float(value["scientific_hdr_threshold"]),
            render_level=float(value["render_level"]),
            candidate_cell_count=int(value["candidate_cell_count"]),
            tiles=tuple(ContourRenderTile.from_json_dict(item) for item in value["tiles"]),
            total_raw_face_upper_bound=int(value["total_raw_face_upper_bound"]),
            total_raw_vertex_upper_bound=int(value["total_raw_vertex_upper_bound"]),
            maximum_tile_transient_bytes=int(value["maximum_tile_transient_bytes"]),
            planning_bytes=int(value["planning_bytes"]),
            metadata=value.get("metadata", {}),
            schema_version=str(value.get("schema_version", CONTOUR_TILE_PLAN_SCHEMA)),
        )


def _tile_transient_upper_bound(
    *, scalar_node_count: int, raw_face_count: int, raw_vertex_count: int
) -> int:
    """Conservative bytes for one scalar brick and one raw marching-cubes result."""

    query_coordinates = scalar_node_count * 3 * np.dtype(np.int64).itemsize
    scalar_values = scalar_node_count * np.dtype(np.float64).itemsize
    scalar_float32 = scalar_node_count * np.dtype(np.float32).itemsize
    raw_vertices = raw_vertex_count * 3 * np.dtype(np.float32).itemsize
    precise_vertices = raw_vertex_count * 3 * np.dtype(np.float64).itemsize
    raw_faces = raw_face_count * 3 * np.dtype(np.int64).itemsize
    remap = raw_vertex_count * np.dtype(np.int64).itemsize
    return int(
        query_coordinates
        + scalar_values
        + scalar_float32
        + raw_vertices
        + precise_vertices
        + raw_faces
        + remap
    )


def plan_contour_render_tiles(
    field: Any,
    candidates: Any,
    *,
    options: MeshExtractionOptions | None = None,
) -> ContourTilePlan:
    """Partition exact crossing cells into deterministic bounded render tiles."""

    resolved = MeshExtractionOptions() if options is None else options
    if not isinstance(resolved, MeshExtractionOptions):
        raise TypeError("options must be MeshExtractionOptions or None.")
    shape = tuple(int(v) for v in field.grid_shape)
    if tuple(int(v) for v in candidates.logical_grid_shape) != shape:
        raise GraphAdapterError("Candidate-cell grid does not match the density field.")
    cells = np.asarray(candidates.cell_indices, dtype=np.int64)
    if cells.ndim != 2 or cells.shape[1:] != (3,) or cells.shape[0] == 0:
        raise GraphAdapterError("Contour planning requires nonempty candidate cells.")
    if cells.shape[0] > resolved.max_total_crossing_cells:
        raise GraphComplexityError(
            f"Contour has {cells.shape[0]} crossing cells, exceeding "
            f"max_total_crossing_cells={resolved.max_total_crossing_cells}."
        )
    tile_shape = np.asarray(resolved.render_tile_shape, dtype=np.int64)
    tile_indices = np.floor_divide(cells, tile_shape[None, :])
    tile_grid = tuple(
        int((shape[a] + resolved.render_tile_shape[a] - 1) // resolved.render_tile_shape[a])
        for a in range(3)
    )
    tile_flat = np.ravel_multi_index(
        (tile_indices[:, 0], tile_indices[:, 1], tile_indices[:, 2]),
        tile_grid,
        order="C",
    ).astype(np.int64, copy=False)
    order = np.argsort(tile_flat, kind="stable")
    ordered_flat = tile_flat[order]
    starts = np.concatenate(
        (
            np.asarray([0], dtype=np.int64),
            np.flatnonzero(ordered_flat[1:] != ordered_flat[:-1]).astype(np.int64) + 1,
        )
    )
    stops = np.concatenate((starts[1:], np.asarray([ordered_flat.size], dtype=np.int64)))
    unique_flat = ordered_flat[starts]
    unique_tiles = np.column_stack(
        np.unravel_index(unique_flat, tile_grid, order="C")
    ).astype(np.int64, copy=False)
    tiles: list[ContourRenderTile] = []
    total_face_upper = 0
    total_vertex_upper = 0
    maximum_transient = 0
    for tile_index_array, start_row, stop_row in zip(
        unique_tiles, starts, stops, strict=True
    ):
        count = int(stop_row - start_row)
        if count > resolved.max_crossing_cells_per_tile:
            raise GraphComplexityError(
                f"Render tile {tuple(int(v) for v in tile_index_array)} contains "
                f"{count} crossing cells, exceeding max_crossing_cells_per_tile="
                f"{resolved.max_crossing_cells_per_tile}."
            )
        cell_start_array = tile_index_array * tile_shape
        cell_stop_array = np.minimum(
            cell_start_array + tile_shape, np.asarray(shape, dtype=np.int64)
        )
        extent = cell_stop_array - cell_start_array
        scalar_nodes = int(np.prod(extent + 1, dtype=object))
        face_upper = 5 * count
        vertex_upper = 12 * count
        if face_upper > resolved.max_raw_faces_per_tile:
            raise GraphComplexityError(
                f"Render tile {tuple(int(v) for v in tile_index_array)} has a "
                f"worst-case {face_upper} raw faces, exceeding "
                f"max_raw_faces_per_tile={resolved.max_raw_faces_per_tile}."
            )
        if vertex_upper > resolved.max_raw_vertices_per_tile:
            raise GraphComplexityError(
                f"Render tile {tuple(int(v) for v in tile_index_array)} has a "
                f"worst-case {vertex_upper} raw vertices, exceeding "
                f"max_raw_vertices_per_tile={resolved.max_raw_vertices_per_tile}."
            )
        transient = _tile_transient_upper_bound(
            scalar_node_count=scalar_nodes,
            raw_face_count=face_upper,
            raw_vertex_count=vertex_upper,
        )
        if transient > resolved.max_transient_mesh_bytes:
            raise GraphComplexityError(
                f"Render tile {tuple(int(v) for v in tile_index_array)} requires an "
                f"estimated {transient} transient bytes, exceeding "
                f"max_transient_mesh_bytes={resolved.max_transient_mesh_bytes}."
            )
        tile = ContourRenderTile(
            tile_index=tuple(int(v) for v in tile_index_array),
            cell_start=tuple(int(v) for v in cell_start_array),
            cell_stop=tuple(int(v) for v in cell_stop_array),
            crossing_cell_count=count,
            scalar_node_count=scalar_nodes,
            raw_face_upper_bound=face_upper,
            raw_vertex_upper_bound=vertex_upper,
            estimated_transient_bytes=transient,
        )
        tiles.append(tile)
        total_face_upper += face_upper
        total_vertex_upper += vertex_upper
        maximum_transient = max(maximum_transient, transient)
    if total_face_upper > resolved.max_total_raw_faces:
        raise GraphComplexityError(
            f"Contour worst-case raw faces {total_face_upper} exceed "
            f"max_total_raw_faces={resolved.max_total_raw_faces}."
        )
    if total_vertex_upper > resolved.max_total_raw_vertices:
        raise GraphComplexityError(
            f"Contour worst-case raw vertices {total_vertex_upper} exceed "
            f"max_total_raw_vertices={resolved.max_total_raw_vertices}."
        )
    planning_bytes = int(
        cells.nbytes
        + tile_indices.nbytes
        + tile_flat.nbytes
        + order.nbytes
        + ordered_flat.nbytes
        + starts.nbytes
        + stops.nbytes
        + unique_tiles.nbytes
    )
    if planning_bytes > resolved.max_planning_workspace_bytes:
        raise GraphComplexityError(
            f"Contour tile planning requires approximately {planning_bytes} bytes, "
            f"exceeding max_planning_workspace_bytes="
            f"{resolved.max_planning_workspace_bytes}."
        )
    return ContourTilePlan(
        field_key=str(field.field_key),
        logical_grid_shape=shape,
        render_tile_shape=resolved.render_tile_shape,
        scientific_hdr_threshold=float(candidates.scientific_hdr_threshold),
        render_level=float(candidates.render_level),
        candidate_cell_count=int(cells.shape[0]),
        tiles=tuple(tiles),
        total_raw_face_upper_bound=total_face_upper,
        total_raw_vertex_upper_bound=total_vertex_upper,
        maximum_tile_transient_bytes=maximum_transient,
        planning_bytes=planning_bytes,
        metadata={
            "tile_grid_shape": list(tile_grid),
            "marching_cubes_max_faces_per_crossing_cell": 5,
            "raw_vertex_upper_bound_per_crossing_cell": 12,
            "global_dense_grid_allocated": False,
        },
    )
