"""Stage-11B mapping of a certified natural tiling onto compatible frames.

The scientific tiling remains the source-bound :class:`PeriodicCellComplex`.
This module reconstructs the same lifted vertex, face, window, and tile identities
in atomistic trajectory or ensemble frames whose exact projected framework graph
matches that source.  Geometry is descriptive: thermally nonplanar faces are
retained as fixed boundary-vertex fan surfaces and never redefine the tiling.

Periodic image gauges are replayed from the existing atomic-connectivity and
framework-topology normalization rules.  No nearest-image guess is made at the
projected-net level.  The only minimum-image replay occurs for the underlying
atomic edges, for which ``AtomicConnectivityResult`` already declares the unique
minimum-image convention.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
import hashlib
import itertools
import json
import math
from numbers import Integral
from typing import Any, Mapping, Sequence

import numpy as np

from mdstats.collection import AtomisticFrameCollection

from ._neighbors import minimum_image_geometry
from ._periodic_graph import LatticeShift, add_shift
from .atomic_connectivity import AtomicConnectivityResult, AtomicConnectivityState
from .framework_topology import (
    FrameworkAtomRole,
    FrameworkEdgeKey,
    FrameworkTopology,
    build_framework_topology,
)
from .periodic_cell_complex import PeriodicCellComplex
from .periodic_net_embedding import PeriodicNetEmbedding
from .primitive_ring import LiftedVertexRef
from .primitive_ring_index import PrimitiveRingIndex
from .tiling_geometry import (
    TileFaceGeometry,
    TilingGeometryCatalog,
)
from .topology_catalog import TopologyCatalog

CANONICAL_FRAME_TILING_GEOMETRY_SCHEMA = "mdstats.frame-tiling-geometry.v1"
FRAME_TILING_GEOMETRY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)


class FrameTilingGeometryError(ValueError):
    """Base error for Stage-11B compatible-frame geometry."""


class FrameTilingGeometryInputError(FrameTilingGeometryError):
    """Raised when source objects or options violate the public contract."""


class FrameTilingGeometryInvariantError(FrameTilingGeometryError):
    """Raised when source records disagree before frame mapping begins."""


class FrameTilingGeometryResourceError(FrameTilingGeometryError):
    """Raised transactionally before declared finite work limits are exceeded."""


class FrameTilingGeometrySerializationError(FrameTilingGeometryError):
    """Raised when deterministic source replay disagrees with stored output."""


class FrameTilingGeometryStatus(str, Enum):
    """Per-frame result state."""

    MAPPED = "mapped"
    TOPOLOGY_MISMATCH = "topology_mismatch"
    CONNECTIVITY_GEOMETRY_MISMATCH = "connectivity_geometry_mismatch"
    DEGENERATE_GEOMETRY = "degenerate_geometry"


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise FrameTilingGeometryInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise FrameTilingGeometryInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise FrameTilingGeometryInputError(f"{name} must be positive.")
    return result


def _finite(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise FrameTilingGeometryInputError(f"{name} must be finite.")
    return result


def _float_tuple(value: Sequence[object], *, name: str, length: int = 3) -> tuple[float, ...]:
    result = tuple(_finite(item, name=name) for item in value)
    if len(result) != length:
        raise FrameTilingGeometryInputError(f"{name} must contain {length} values.")
    return result


def _int_shift(value: Sequence[object], *, name: str) -> LatticeShift:
    result = tuple(int(item) for item in value)
    if len(result) != 3:
        raise FrameTilingGeometryInputError(f"{name} must contain three integers.")
    return result  # type: ignore[return-value]


def _array_digest_payload(array: np.ndarray) -> dict[str, Any]:
    contiguous = np.ascontiguousarray(array)
    return {
        "dtype": contiguous.dtype.str,
        "shape": list(contiguous.shape),
        "sha256": hashlib.sha256(contiguous.tobytes(order="C")).hexdigest(),
    }


def _collection_geometry_digest(
    collection: AtomisticFrameCollection,
    frame_indices: Sequence[int],
    active_atom_indices: Sequence[int],
) -> str:
    frames = np.asarray(frame_indices, dtype=np.int64)
    atoms = np.asarray(active_atom_indices, dtype=np.int64)
    return _digest(
        {
            "schema": "mdstats.frame-tiling-collection-binding.v1",
            "frame_semantics": collection.frame_semantics.value,
            "frame_indices": frames.tolist(),
            "frame_ids": np.asarray(collection.frame_ids, dtype=np.int64)[frames].tolist(),
            "atomic_numbers": np.asarray(collection.atomic_numbers, dtype=np.int32)[atoms].tolist(),
            "pbc": np.asarray(collection.pbc, dtype=bool).tolist(),
            "cells": _array_digest_payload(np.asarray(collection.cells, dtype=np.float64)[frames]),
            "origins": _array_digest_payload(np.asarray(collection.origins, dtype=np.float64)[frames]),
            "fractional_positions": _array_digest_payload(
                np.asarray(collection.fractional_positions, dtype=np.float64)[np.ix_(frames, atoms)]
            ),
        }
    )


def _connectivity_binding_digest(
    connectivity: AtomicConnectivityResult,
    frame_indices: Sequence[int],
) -> str:
    records = []
    for frame in frame_indices:
        state = connectivity.state_for_frame(int(frame))
        records.append((int(frame), int(connectivity.frame_ids[np.flatnonzero(connectivity.frame_indices == frame)[0]]), state.digest))
    return _digest(
        {
            "schema": "mdstats.frame-tiling-connectivity-binding.v1",
            "definition": connectivity.definition.to_dict(),
            "resolved_scope": connectivity.resolved_scope.to_dict(),
            "records": records,
        }
    )


@dataclass(frozen=True, slots=True)
class FrameTilingGeometryOptions:
    """Numerical interpretation policy for mapped descriptive geometry."""

    degeneracy_tolerance: float = 1.0e-12
    planarity_tolerance: float = 1.0e-3
    window_match_tolerance: float = 1.0e-8
    volume_closure_relative_tolerance: float = 1.0e-8
    volume_closure_absolute_tolerance: float = 1.0e-8

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = _finite(getattr(self, name), name=name)
            if value < 0:
                raise FrameTilingGeometryInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, float]:
        return {name: float(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameTilingGeometryOptions":
        return cls(**{name: float(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class FrameTilingGeometryResources:
    """Transactional finite-work limits."""

    max_frames: int = 100_000
    max_vertices: int = 100_000
    max_tile_faces: int = 1_000_000
    max_vertex_instances: int = 10_000_000
    max_pair_distance_tests: int = 100_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameTilingGeometryResources":
        return cls(**{name: int(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class FrameTileFaceGeometry:
    """One oriented scientific tile side in one compatible frame."""

    side_index: int
    fractional_vertices: tuple[tuple[float, float, float], ...]
    cartesian_vertices: tuple[tuple[float, float, float], ...]
    fractional_center: tuple[float, float, float]
    cartesian_center: tuple[float, float, float]
    area_weighted_unit_normal: tuple[float, float, float]
    area: float
    perimeter: float
    planarity_rms: float
    planarity_max: float
    projected_aperture_radius: float
    planar_aperture_certified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "side_index", _nonnegative(self.side_index, name="side_index"))
        fractional = tuple(
            _float_tuple(point, name="fractional_vertex") for point in self.fractional_vertices
        )
        cartesian = tuple(
            _float_tuple(point, name="cartesian_vertex") for point in self.cartesian_vertices
        )
        if len(fractional) < 3 or len(fractional) != len(cartesian):
            raise FrameTilingGeometryInputError(
                "Frame face vertices must align and contain at least three points."
            )
        object.__setattr__(self, "fractional_vertices", fractional)
        object.__setattr__(self, "cartesian_vertices", cartesian)
        object.__setattr__(
            self, "fractional_center", _float_tuple(self.fractional_center, name="fractional_center")
        )
        object.__setattr__(
            self, "cartesian_center", _float_tuple(self.cartesian_center, name="cartesian_center")
        )
        normal = _float_tuple(
            self.area_weighted_unit_normal, name="area_weighted_unit_normal"
        )
        if not math.isclose(sum(value * value for value in normal), 1.0, rel_tol=1e-8, abs_tol=1e-8):
            raise FrameTilingGeometryInputError("Stored face normal must be unit length.")
        object.__setattr__(self, "area_weighted_unit_normal", normal)
        for name in (
            "area",
            "perimeter",
            "planarity_rms",
            "planarity_max",
            "projected_aperture_radius",
        ):
            value = _finite(getattr(self, name), name=name)
            if value < 0 or (name in {"area", "perimeter"} and value == 0):
                raise FrameTilingGeometryInputError(f"{name} has an invalid value.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "planar_aperture_certified", bool(self.planar_aperture_certified))

    def to_dict(self) -> dict[str, Any]:
        return {
            "side_index": self.side_index,
            "fractional_vertices": [list(point) for point in self.fractional_vertices],
            "cartesian_vertices": [list(point) for point in self.cartesian_vertices],
            "fractional_center": list(self.fractional_center),
            "cartesian_center": list(self.cartesian_center),
            "area_weighted_unit_normal": list(self.area_weighted_unit_normal),
            "area": self.area,
            "perimeter": self.perimeter,
            "planarity_rms": self.planarity_rms,
            "planarity_max": self.planarity_max,
            "projected_aperture_radius": self.projected_aperture_radius,
            "planar_aperture_certified": self.planar_aperture_certified,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameTileFaceGeometry":
        return cls(
            side_index=int(payload["side_index"]),
            fractional_vertices=tuple(tuple(point) for point in payload["fractional_vertices"]),
            cartesian_vertices=tuple(tuple(point) for point in payload["cartesian_vertices"]),
            fractional_center=tuple(payload["fractional_center"]),
            cartesian_center=tuple(payload["cartesian_center"]),
            area_weighted_unit_normal=tuple(payload["area_weighted_unit_normal"]),
            area=float(payload["area"]),
            perimeter=float(payload["perimeter"]),
            planarity_rms=float(payload["planarity_rms"]),
            planarity_max=float(payload["planarity_max"]),
            projected_aperture_radius=float(payload["projected_aperture_radius"]),
            planar_aperture_certified=bool(payload["planar_aperture_certified"]),
        )


@dataclass(frozen=True, slots=True)
class FrameNaturalTileGeometry:
    """One scientific natural tile realized in one frame."""

    tile_index: int
    fractional_center: tuple[float, float, float]
    cartesian_center: tuple[float, float, float]
    signed_volume: float
    volume: float
    surface_area: float
    equivalent_sphere_radius: float
    sphericity: float
    diameter: float
    orientation_preserved: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_index", _nonnegative(self.tile_index, name="tile_index"))
        object.__setattr__(
            self, "fractional_center", _float_tuple(self.fractional_center, name="fractional_center")
        )
        object.__setattr__(
            self, "cartesian_center", _float_tuple(self.cartesian_center, name="cartesian_center")
        )
        signed = _finite(self.signed_volume, name="signed_volume")
        volume = _finite(self.volume, name="volume")
        if volume <= 0 or not math.isclose(volume, abs(signed), rel_tol=1e-10, abs_tol=1e-12):
            raise FrameTilingGeometryInputError("volume must equal abs(signed_volume) and be positive.")
        object.__setattr__(self, "signed_volume", signed)
        object.__setattr__(self, "volume", volume)
        for name in ("surface_area", "equivalent_sphere_radius", "sphericity", "diameter"):
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise FrameTilingGeometryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "orientation_preserved", bool(self.orientation_preserved))

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "fractional_center": list(self.fractional_center),
            "cartesian_center": list(self.cartesian_center),
            "signed_volume": self.signed_volume,
            "volume": self.volume,
            "surface_area": self.surface_area,
            "equivalent_sphere_radius": self.equivalent_sphere_radius,
            "sphericity": self.sphericity,
            "diameter": self.diameter,
            "orientation_preserved": self.orientation_preserved,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameNaturalTileGeometry":
        return cls(
            tile_index=int(payload["tile_index"]),
            fractional_center=tuple(payload["fractional_center"]),
            cartesian_center=tuple(payload["cartesian_center"]),
            signed_volume=float(payload["signed_volume"]),
            volume=float(payload["volume"]),
            surface_area=float(payload["surface_area"]),
            equivalent_sphere_radius=float(payload["equivalent_sphere_radius"]),
            sphericity=float(payload["sphericity"]),
            diameter=float(payload["diameter"]),
            orientation_preserved=bool(payload["orientation_preserved"]),
        )


@dataclass(frozen=True, slots=True)
class FrameWindowGeometry:
    """One topological window with frame-dependent descriptive geometry."""

    window_index: int
    cartesian_center: tuple[float, float, float]
    area: float
    side_area_mismatch: float
    projected_aperture_radius: float
    planarity_rms: float
    planarity_max: float
    planar_aperture_certified: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_index", _nonnegative(self.window_index, name="window_index"))
        object.__setattr__(
            self, "cartesian_center", _float_tuple(self.cartesian_center, name="cartesian_center")
        )
        for name in (
            "area",
            "side_area_mismatch",
            "projected_aperture_radius",
            "planarity_rms",
            "planarity_max",
        ):
            value = _finite(getattr(self, name), name=name)
            if value < 0 or (name == "area" and value == 0):
                raise FrameTilingGeometryInputError(f"{name} has an invalid value.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "planar_aperture_certified", bool(self.planar_aperture_certified))

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "cartesian_center": list(self.cartesian_center),
            "area": self.area,
            "side_area_mismatch": self.side_area_mismatch,
            "projected_aperture_radius": self.projected_aperture_radius,
            "planarity_rms": self.planarity_rms,
            "planarity_max": self.planarity_max,
            "planar_aperture_certified": self.planar_aperture_certified,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameWindowGeometry":
        return cls(
            window_index=int(payload["window_index"]),
            cartesian_center=tuple(payload["cartesian_center"]),
            area=float(payload["area"]),
            side_area_mismatch=float(payload["side_area_mismatch"]),
            projected_aperture_radius=float(payload["projected_aperture_radius"]),
            planarity_rms=float(payload["planarity_rms"]),
            planarity_max=float(payload["planarity_max"]),
            planar_aperture_certified=bool(payload["planar_aperture_certified"]),
        )


@dataclass(frozen=True, slots=True)
class MappedTilingFrame:
    """Complete per-frame result, including explicit unresolved states."""

    result_position: int
    collection_frame_index: int
    frame_id: int
    step: int | None
    time: float | None
    status: FrameTilingGeometryStatus
    topology_graph_digest: str | None
    connectivity_state_digest: str
    global_image_shift: LatticeShift
    vertex_atom_indices: tuple[int, ...]
    vertex_image_gauges: tuple[LatticeShift, ...]
    tiles: tuple[FrameNaturalTileGeometry, ...]
    tile_faces: tuple[FrameTileFaceGeometry, ...]
    windows: tuple[FrameWindowGeometry, ...]
    cell_volume: float
    total_tile_volume: float | None
    volume_closure_error: float | None
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        for name in ("result_position", "collection_frame_index", "frame_id"):
            object.__setattr__(self, name, _nonnegative(getattr(self, name), name=name))
        if self.step is not None:
            object.__setattr__(self, "step", int(self.step))
        if self.time is not None:
            object.__setattr__(self, "time", _finite(self.time, name="time"))
        status = FrameTilingGeometryStatus(self.status)
        object.__setattr__(self, "status", status)
        if self.topology_graph_digest is not None:
            _sha(self.topology_graph_digest, name="topology_graph_digest")
        _sha(self.connectivity_state_digest, name="connectivity_state_digest")
        object.__setattr__(
            self, "global_image_shift", _int_shift(self.global_image_shift, name="global_image_shift")
        )
        atoms = tuple(_nonnegative(value, name="vertex atom index") for value in self.vertex_atom_indices)
        gauges = tuple(_int_shift(value, name="vertex image gauge") for value in self.vertex_image_gauges)
        if atoms != tuple(sorted(set(atoms))) or len(atoms) != len(gauges):
            raise FrameTilingGeometryInputError(
                "vertex_atom_indices must be sorted, unique, and aligned with gauges."
            )
        object.__setattr__(self, "vertex_atom_indices", atoms)
        object.__setattr__(self, "vertex_image_gauges", gauges)
        tiles = tuple(self.tiles)
        faces = tuple(self.tile_faces)
        windows = tuple(self.windows)
        object.__setattr__(self, "tiles", tiles)
        object.__setattr__(self, "tile_faces", faces)
        object.__setattr__(self, "windows", windows)
        cell_volume = _finite(self.cell_volume, name="cell_volume")
        if cell_volume <= 0:
            raise FrameTilingGeometryInputError("cell_volume must be positive.")
        object.__setattr__(self, "cell_volume", cell_volume)
        if status is FrameTilingGeometryStatus.MAPPED:
            if self.topology_graph_digest is None or not tiles or not faces or not windows:
                raise FrameTilingGeometryInputError("Mapped frames require complete geometry.")
            total = _finite(self.total_tile_volume, name="total_tile_volume")
            closure = _finite(self.volume_closure_error, name="volume_closure_error")
            if total <= 0 or closure < 0:
                raise FrameTilingGeometryInputError("Mapped frame volume fields are invalid.")
            object.__setattr__(self, "total_tile_volume", total)
            object.__setattr__(self, "volume_closure_error", closure)
        else:
            if tiles or faces or windows or self.total_tile_volume is not None or self.volume_closure_error is not None:
                raise FrameTilingGeometryInputError(
                    "Unmapped frames must not contain partial geometric records."
                )
        if self.diagnostic is not None and not isinstance(self.diagnostic, str):
            raise FrameTilingGeometryInputError("diagnostic must be None or a string.")

    @property
    def mapped(self) -> bool:
        return self.status is FrameTilingGeometryStatus.MAPPED

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_position": self.result_position,
            "collection_frame_index": self.collection_frame_index,
            "frame_id": self.frame_id,
            "step": self.step,
            "time": self.time,
            "status": self.status.value,
            "topology_graph_digest": self.topology_graph_digest,
            "connectivity_state_digest": self.connectivity_state_digest,
            "global_image_shift": list(self.global_image_shift),
            "vertex_atom_indices": list(self.vertex_atom_indices),
            "vertex_image_gauges": [list(value) for value in self.vertex_image_gauges],
            "tiles": [value.to_dict() for value in self.tiles],
            "tile_faces": [value.to_dict() for value in self.tile_faces],
            "windows": [value.to_dict() for value in self.windows],
            "cell_volume": self.cell_volume,
            "total_tile_volume": self.total_tile_volume,
            "volume_closure_error": self.volume_closure_error,
            "diagnostic": self.diagnostic,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MappedTilingFrame":
        return cls(
            result_position=int(payload["result_position"]),
            collection_frame_index=int(payload["collection_frame_index"]),
            frame_id=int(payload["frame_id"]),
            step=None if payload["step"] is None else int(payload["step"]),
            time=None if payload["time"] is None else float(payload["time"]),
            status=FrameTilingGeometryStatus(payload["status"]),
            topology_graph_digest=payload["topology_graph_digest"],
            connectivity_state_digest=str(payload["connectivity_state_digest"]),
            global_image_shift=tuple(payload["global_image_shift"]),
            vertex_atom_indices=tuple(payload["vertex_atom_indices"]),
            vertex_image_gauges=tuple(tuple(value) for value in payload["vertex_image_gauges"]),
            tiles=tuple(FrameNaturalTileGeometry.from_dict(value) for value in payload["tiles"]),
            tile_faces=tuple(FrameTileFaceGeometry.from_dict(value) for value in payload["tile_faces"]),
            windows=tuple(FrameWindowGeometry.from_dict(value) for value in payload["windows"]),
            cell_volume=float(payload["cell_volume"]),
            total_tile_volume=None if payload["total_tile_volume"] is None else float(payload["total_tile_volume"]),
            volume_closure_error=None if payload["volume_closure_error"] is None else float(payload["volume_closure_error"]),
            diagnostic=payload.get("diagnostic"),
        )


@dataclass(frozen=True, slots=True, eq=False)
class FrameTilingGeometryCatalog:
    """Persistent Stage-11B geometry mapped over selected compatible frames."""

    reference_geometry_digest: str
    periodic_cell_complex_digest: str
    periodic_net_embedding_digest: str
    primitive_ring_catalog_digest: str
    topology_catalog_digest: str
    collection_geometry_digest: str
    connectivity_binding_digest: str
    options: FrameTilingGeometryOptions
    resources: FrameTilingGeometryResources
    frames: tuple[MappedTilingFrame, ...]
    canonical_schema_version: str = CANONICAL_FRAME_TILING_GEOMETRY_SCHEMA
    digest_algorithm: str = FRAME_TILING_GEOMETRY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "reference_geometry_digest",
            "periodic_cell_complex_digest",
            "periodic_net_embedding_digest",
            "primitive_ring_catalog_digest",
            "topology_catalog_digest",
            "collection_geometry_digest",
            "connectivity_binding_digest",
        ):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.options, FrameTilingGeometryOptions):
            raise FrameTilingGeometryInputError("options has the wrong type.")
        if not isinstance(self.resources, FrameTilingGeometryResources):
            raise FrameTilingGeometryInputError("resources has the wrong type.")
        frames = tuple(self.frames)
        if not frames or tuple(frame.result_position for frame in frames) != tuple(range(len(frames))):
            raise FrameTilingGeometryInputError("Frame results must be nonempty and densely ordered.")
        if len({frame.collection_frame_index for frame in frames}) != len(frames):
            raise FrameTilingGeometryInputError("Collection frame indices must be unique.")
        if self.canonical_schema_version != CANONICAL_FRAME_TILING_GEOMETRY_SCHEMA:
            raise FrameTilingGeometryInputError("Unsupported frame-geometry schema.")
        if self.digest_algorithm != FRAME_TILING_GEOMETRY_DIGEST_ALGORITHM:
            raise FrameTilingGeometryInputError("Unsupported frame-geometry digest algorithm.")
        object.__setattr__(self, "frames", frames)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FrameTilingGeometryInputError("Stored frame-geometry digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrameTilingGeometryCatalog) and self.digest == other.digest

    @property
    def mapped_frame_count(self) -> int:
        return sum(frame.mapped for frame in self.frames)

    @property
    def unresolved_frame_count(self) -> int:
        return len(self.frames) - self.mapped_frame_count

    @property
    def mapped_frame_indices(self) -> tuple[int, ...]:
        return tuple(frame.collection_frame_index for frame in self.frames if frame.mapped)

    def tile_metric(self, tile_index: int, metric: str) -> np.ndarray:
        """Return one frame-aligned tile metric with NaN for unresolved frames."""

        index = _nonnegative(tile_index, name="tile_index")
        allowed = {
            "volume",
            "surface_area",
            "equivalent_sphere_radius",
            "sphericity",
            "diameter",
        }
        if metric not in allowed:
            raise FrameTilingGeometryInputError(f"Unsupported tile metric {metric!r}.")
        values = np.full(len(self.frames), np.nan, dtype=np.float64)
        for position, frame in enumerate(self.frames):
            if frame.mapped:
                if index >= len(frame.tiles):
                    raise FrameTilingGeometryInvariantError("tile_index exceeds mapped tile count.")
                values[position] = float(getattr(frame.tiles[index], metric))
        values.setflags(write=False)
        return values

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "reference_geometry_digest": self.reference_geometry_digest,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "periodic_net_embedding_digest": self.periodic_net_embedding_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "topology_catalog_digest": self.topology_catalog_digest,
            "collection_geometry_digest": self.collection_geometry_digest,
            "connectivity_binding_digest": self.connectivity_binding_digest,
            "options": self.options.to_dict(),
            "resources": self.resources.to_dict(),
            "frames": [frame.to_dict() for frame in self.frames],
        }
        if include_digest:
            payload["digest"] = self.digest
        return payload

    def to_dict(self) -> dict[str, Any]:
        return self._payload(True)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        reference_geometry: TilingGeometryCatalog,
        complex_: PeriodicCellComplex,
        embedding: PeriodicNetEmbedding,
        ring_index: PrimitiveRingIndex,
        collection: AtomisticFrameCollection,
        connectivity: AtomicConnectivityResult,
        topology_catalog: TopologyCatalog,
    ) -> "FrameTilingGeometryCatalog":
        options = FrameTilingGeometryOptions.from_dict(payload["options"])
        resources = FrameTilingGeometryResources.from_dict(payload["resources"])
        frame_indices = tuple(
            int(item["collection_frame_index"]) for item in payload["frames"]
        )
        rebuilt = map_tiling_geometry_to_frames(
            reference_geometry,
            complex_,
            embedding,
            ring_index,
            collection,
            connectivity,
            topology_catalog,
            frame_indices=frame_indices,
            options=options,
            resources=resources,
        )
        if rebuilt.to_dict() != dict(payload):
            raise FrameTilingGeometrySerializationError(
                "Serialized compatible-frame geometry is not canonical for the supplied sources."
            )
        return rebuilt


def _selected_frames(
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    topology_catalog: TopologyCatalog,
    frame_indices: Sequence[int] | None,
) -> tuple[int, ...]:
    if frame_indices is None:
        frames = tuple(int(value) for value in topology_catalog.frame_indices)
    else:
        frames = tuple(_nonnegative(value, name="frame_index") for value in frame_indices)
    if not frames or len(set(frames)) != len(frames):
        raise FrameTilingGeometryInputError("frame_indices must be nonempty and unique.")
    if collection.is_trajectory and tuple(sorted(frames)) != frames:
        raise FrameTilingGeometryInputError(
            "Trajectory frame_indices must be strictly increasing."
        )
    connectivity_frames = set(int(value) for value in connectivity.frame_indices)
    topology_frames = set(int(value) for value in topology_catalog.frame_indices)
    for frame in frames:
        if frame >= collection.n_frames:
            raise FrameTilingGeometryInputError("A selected frame lies outside the collection.")
        if frame not in connectivity_frames or frame not in topology_frames:
            raise FrameTilingGeometryInputError(
                "Every selected frame must be present in connectivity and topology catalogs."
            )
        cpos = int(np.flatnonzero(connectivity.frame_indices == frame)[0])
        tpos = int(np.flatnonzero(topology_catalog.frame_indices == frame)[0])
        expected_id = int(collection.frame_ids[frame])
        if int(connectivity.frame_ids[cpos]) != expected_id or int(topology_catalog.frame_ids[tpos]) != expected_id:
            raise FrameTilingGeometryInputError("Frame IDs disagree across source objects.")
    return frames


def _validate_sources(
    reference_geometry: TilingGeometryCatalog,
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    topology_catalog: TopologyCatalog,
) -> None:
    if not isinstance(reference_geometry, TilingGeometryCatalog):
        raise FrameTilingGeometryInputError("reference_geometry must be a TilingGeometryCatalog.")
    if not isinstance(complex_, PeriodicCellComplex):
        raise FrameTilingGeometryInputError("complex_ must be a PeriodicCellComplex.")
    if not isinstance(embedding, PeriodicNetEmbedding):
        raise FrameTilingGeometryInputError("embedding must be a PeriodicNetEmbedding.")
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise FrameTilingGeometryInputError("ring_index must be a PrimitiveRingIndex.")
    if not isinstance(collection, AtomisticFrameCollection):
        raise FrameTilingGeometryInputError("collection must be an AtomisticFrameCollection.")
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise FrameTilingGeometryInputError("connectivity must be an AtomicConnectivityResult.")
    if not isinstance(topology_catalog, TopologyCatalog):
        raise FrameTilingGeometryInputError("topology_catalog must be a TopologyCatalog.")
    if reference_geometry.periodic_cell_complex_digest != complex_.digest:
        raise FrameTilingGeometryInputError("Reference geometry and cell complex disagree.")
    if reference_geometry.periodic_net_embedding_digest != embedding.digest:
        raise FrameTilingGeometryInputError("Reference geometry and embedding disagree.")
    if reference_geometry.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise FrameTilingGeometryInputError("Reference geometry and ring index disagree.")
    if complex_.periodic_net_embedding_digest != embedding.digest:
        raise FrameTilingGeometryInputError("Cell complex and embedding disagree.")
    if complex_.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise FrameTilingGeometryInputError("Cell complex and ring index disagree.")
    if tuple(bool(value) for value in collection.pbc) != tuple(bool(value) for value in topology_catalog.topologies[0].pbc):
        raise FrameTilingGeometryInputError("Collection periodicity disagrees with topology catalog.")
    if collection.frame_semantics is not topology_catalog.frame_semantics:
        raise FrameTilingGeometryInputError("Collection and topology catalog frame semantics disagree.")
    if tuple(int(value) for value in embedding.vertex_atom_indices) != tuple(
        int(value) for value in ring_index.catalog.vertex_atom_indices
    ):
        raise FrameTilingGeometryInvariantError("Embedding and ring-index vertices disagree.")
    if any(atom >= collection.n_atoms for atom in embedding.vertex_atom_indices):
        raise FrameTilingGeometryInputError("Framework vertex atom index exceeds collection size.")
    if not bool(connectivity.metadata.get("unique_minimum_image_only", False)):
        raise FrameTilingGeometryInputError(
            "Compatible-frame gauge replay requires unique-minimum-image atomic connectivity."
        )


def _state_physical_gauge(
    collection: AtomisticFrameCollection,
    frame_index: int,
    state: AtomicConnectivityState,
) -> dict[int, np.ndarray]:
    wrapped = collection.get_wrapped_fractional_positions(frame_index)
    cell = np.asarray(collection.cells[frame_index], dtype=np.float64)
    raw_records: list[tuple[int, int, np.ndarray]] = []
    adjacency: dict[int, list[tuple[int, np.ndarray]]] = {
        int(atom): [] for atom in state.active_atom_indices
    }
    for endpoints, normalized_shift in zip(
        state.edge_atom_indices, state.edge_image_shifts, strict=True
    ):
        i, j = int(endpoints[0]), int(endpoints[1])
        if i == j:
            raw_shift = np.asarray(normalized_shift, dtype=np.int64)
        else:
            displacement = (wrapped[j] - wrapped[i]) @ cell
            _vector, _distance, raw_shift = minimum_image_geometry(
                displacement, cell=cell, pbc=collection.pbc
            )
            raw_shift = np.asarray(raw_shift, dtype=np.int64)
        raw_records.append((i, j, raw_shift))
        adjacency[i].append((j, raw_shift))
        adjacency[j].append((i, -raw_shift))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], *item[1].tolist()))

    gauge: dict[int, np.ndarray] = {}
    for root in sorted(adjacency):
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, raw_shift in adjacency[current]:
                if neighbor in gauge:
                    continue
                gauge[neighbor] = gauge[current] + raw_shift
                queue.append(neighbor)

    for (i, j, raw_shift), normalized_shift in zip(
        raw_records, state.edge_image_shifts, strict=True
    ):
        replayed = raw_shift + gauge[i] - gauge[j]
        if not np.array_equal(replayed, normalized_shift):
            raise FrameTilingGeometryInvariantError(
                "Atomic minimum-image replay does not reproduce the stored connectivity gauge."
            )
    return gauge


def _framework_relevant_gauge(
    state: AtomicConnectivityState, topology: FrameworkTopology
) -> dict[int, np.ndarray]:
    roles = {
        int(atom): role
        for atom, role in zip(
            topology.resolved_roles.active_atom_indices,
            topology.resolved_roles.roles,
            strict=True,
        )
    }
    relevant = tuple(
        sorted(
            atom
            for atom, role in roles.items()
            if role in {FrameworkAtomRole.VERTEX, FrameworkAtomRole.LINKER}
        )
    )
    adjacency: dict[int, list[tuple[int, np.ndarray]]] = {atom: [] for atom in relevant}
    for endpoints, shift in zip(state.edge_atom_indices, state.edge_image_shifts, strict=True):
        i, j = int(endpoints[0]), int(endpoints[1])
        if i not in adjacency or j not in adjacency:
            continue
        directed = np.asarray(shift, dtype=np.int64)
        adjacency[i].append((j, directed))
        adjacency[j].append((i, -directed))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], *item[1].tolist()))
    gauge: dict[int, np.ndarray] = {}
    for root in relevant:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, shift in adjacency[current]:
                if neighbor in gauge:
                    continue
                gauge[neighbor] = gauge[current] + shift
                queue.append(neighbor)
    return gauge


def _projected_framework_gauge(topology: FrameworkTopology) -> dict[int, np.ndarray]:
    vertices = tuple(int(value) for value in topology.vertex_atom_indices)
    adjacency: dict[int, list[tuple[int, np.ndarray, FrameworkEdgeKey]]] = {
        atom: [] for atom in vertices
    }
    for edge in topology.edges:
        i, j = edge.key.vertex_i, edge.key.vertex_j
        if i == j:
            continue
        shift = np.asarray(edge.raw_image_shift, dtype=np.int64)
        adjacency[i].append((j, shift, edge.key))
        adjacency[j].append((i, -shift, edge.key))
    for atom in adjacency:
        adjacency[atom].sort(key=lambda item: (item[0], *item[1].tolist(), item[2]))
    gauge: dict[int, np.ndarray] = {}
    for root in vertices:
        if root in gauge:
            continue
        gauge[root] = np.zeros(3, dtype=np.int64)
        queue: deque[int] = deque([root])
        while queue:
            current = queue.popleft()
            for neighbor, shift, _edge_key in adjacency[current]:
                if neighbor in gauge:
                    continue
                gauge[neighbor] = gauge[current] + shift
                queue.append(neighbor)
    return gauge


def _canonical_vertex_coordinates(
    collection: AtomisticFrameCollection,
    frame_index: int,
    state: AtomicConnectivityState,
    topology: FrameworkTopology,
) -> tuple[dict[int, np.ndarray], LatticeShift, tuple[LatticeShift, ...]]:
    state_gauge = _state_physical_gauge(collection, frame_index, state)
    relevant_gauge = _framework_relevant_gauge(state, topology)
    projected_gauge = _projected_framework_gauge(topology)
    wrapped = collection.get_wrapped_fractional_positions(frame_index)
    vertices = tuple(int(value) for value in topology.vertex_atom_indices)
    combined = {
        atom: state_gauge[atom] + relevant_gauge[atom] + projected_gauge[atom]
        for atom in vertices
    }
    anchor = vertices[0]
    anchor_base = wrapped[anchor] + combined[anchor]
    if collection.is_trajectory:
        target = np.asarray(collection.fractional_positions[frame_index, anchor], dtype=np.float64)
        shift_float = target - anchor_base
        global_shift_array = np.rint(shift_float).astype(np.int64)
        if not np.allclose(shift_float, global_shift_array, rtol=0.0, atol=2.0e-9):
            raise FrameTilingGeometryInvariantError(
                "Trajectory anchor cannot be reconciled with an integer image shift."
            )
    else:
        global_shift_array = -np.floor(anchor_base).astype(np.int64)
    coordinates = {
        atom: np.asarray(wrapped[atom], dtype=np.float64)
        + combined[atom]
        + global_shift_array
        for atom in vertices
    }
    global_shift: LatticeShift = tuple(int(value) for value in global_shift_array)  # type: ignore[assignment]
    gauges = tuple(
        tuple(int(value) for value in combined[atom])  # type: ignore[misc]
        for atom in vertices
    )
    return coordinates, global_shift, gauges


def _reference_side_refs(
    reference_face: TileFaceGeometry,
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
) -> tuple[LiftedVertexRef, ...]:
    side = reference_face.side
    face = complex_.face_placements[side.face_index]
    ring = ring_index.ring_for_key(face.ring_placement.ring_key)
    base_shift = add_shift(face.ring_placement.image_shift, side.face_image_shift)
    refs = tuple(
        LiftedVertexRef(ref.atom_index, add_shift(ref.image_shift, base_shift))
        for ref in ring.vertex_walk
    )
    if face.orientation == -1:
        refs = tuple(reversed(refs))
    points = tuple(
        embedding.fractional_coordinate(ref.atom_index, ref.image_shift) for ref in refs
    )
    if points == reference_face.fractional_vertices:
        return refs
    reversed_refs = tuple(reversed(refs))
    reversed_points = tuple(
        embedding.fractional_coordinate(ref.atom_index, ref.image_shift)
        for ref in reversed_refs
    )
    if reversed_points == reference_face.fractional_vertices:
        return reversed_refs
    raise FrameTilingGeometryInvariantError(
        "Reference tile-face orientation cannot be replayed from its scientific sources."
    )


def _point_segment_distance_2d(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    direction = end - start
    denominator = float(np.dot(direction, direction))
    if denominator == 0.0:
        return float(np.linalg.norm(point - start))
    parameter = float(np.dot(point - start, direction) / denominator)
    parameter = min(1.0, max(0.0, parameter))
    return float(np.linalg.norm(point - (start + parameter * direction)))


def _projected_convex_contains_origin(points: np.ndarray, tolerance: float) -> bool:
    signs: list[int] = []
    center_signs: list[int] = []
    for index in range(len(points)):
        first = points[index]
        second = points[(index + 1) % len(points)]
        third = points[(index + 2) % len(points)]
        edge = second - first
        next_edge = third - second
        turn = float(edge[0] * next_edge[1] - edge[1] * next_edge[0])
        side = float(edge[0] * (-first[1]) - edge[1] * (-first[0]))
        if abs(turn) <= tolerance or abs(side) <= tolerance:
            return False
        signs.append(1 if turn > 0 else -1)
        center_signs.append(1 if side > 0 else -1)
    return len(set(signs)) == 1 and len(set(center_signs)) == 1 and signs[0] == center_signs[0]


def _map_face(
    reference_face: TileFaceGeometry,
    refs: Sequence[LiftedVertexRef],
    canonical_coordinates: Mapping[int, np.ndarray],
    cell: np.ndarray,
    origin: np.ndarray,
    options: FrameTilingGeometryOptions,
) -> FrameTileFaceGeometry:
    fractional = np.asarray(
        [canonical_coordinates[ref.atom_index] + np.asarray(ref.image_shift, dtype=np.float64) for ref in refs],
        dtype=np.float64,
    )
    cartesian = fractional @ cell + origin
    fractional_center = np.mean(fractional, axis=0)
    cartesian_center = np.mean(cartesian, axis=0)
    area = 0.0
    area_vector = np.zeros(3, dtype=np.float64)
    for index in range(len(cartesian)):
        first = cartesian[index] - cartesian_center
        second = cartesian[(index + 1) % len(cartesian)] - cartesian_center
        cross = np.cross(first, second)
        triangle_area = 0.5 * float(np.linalg.norm(cross))
        if triangle_area <= options.degeneracy_tolerance:
            raise FrameTilingGeometryInvariantError("A mapped face fan contains a degenerate triangle.")
        area += triangle_area
        area_vector += 0.5 * cross
    normal_norm = float(np.linalg.norm(area_vector))
    if normal_norm <= options.degeneracy_tolerance:
        raise FrameTilingGeometryInvariantError("A mapped face has a degenerate area vector.")
    unit_normal = area_vector / normal_norm
    perimeter = sum(
        float(np.linalg.norm(cartesian[(index + 1) % len(cartesian)] - cartesian[index]))
        for index in range(len(cartesian))
    )
    centered = cartesian - cartesian_center
    _u, _singular, vh = np.linalg.svd(centered, full_matrices=False)
    best_normal = np.asarray(vh[-1], dtype=np.float64)
    if float(np.dot(best_normal, unit_normal)) < 0:
        best_normal = -best_normal
    deviations = np.abs(centered @ best_normal)
    planarity_rms = float(np.sqrt(np.mean(deviations * deviations)))
    planarity_max = float(np.max(deviations))
    basis = np.asarray(vh[:2], dtype=np.float64)
    projected = centered @ basis.T
    aperture = min(
        _point_segment_distance_2d(
            np.zeros(2, dtype=np.float64),
            projected[index],
            projected[(index + 1) % len(projected)],
        )
        for index in range(len(projected))
    )
    convex_contains = _projected_convex_contains_origin(
        projected, max(options.degeneracy_tolerance, 1.0e-14)
    )
    planar_aperture = convex_contains and planarity_max <= options.planarity_tolerance
    return FrameTileFaceGeometry(
        side_index=reference_face.side_index,
        fractional_vertices=tuple(tuple(float(value) for value in point) for point in fractional),
        cartesian_vertices=tuple(tuple(float(value) for value in point) for point in cartesian),
        fractional_center=tuple(float(value) for value in fractional_center),
        cartesian_center=tuple(float(value) for value in cartesian_center),
        area_weighted_unit_normal=tuple(float(value) for value in unit_normal),
        area=area,
        perimeter=perimeter,
        planarity_rms=planarity_rms,
        planarity_max=planarity_max,
        projected_aperture_radius=aperture,
        planar_aperture_certified=planar_aperture,
    )


def _map_tile(
    tile_index: int,
    reference_geometry: TilingGeometryCatalog,
    frame_faces: Sequence[FrameTileFaceGeometry],
    side_refs: Sequence[Sequence[LiftedVertexRef]],
    cell: np.ndarray,
    resources: FrameTilingGeometryResources,
    options: FrameTilingGeometryOptions,
) -> FrameNaturalTileGeometry:
    reference_tile = reference_geometry.tiles[tile_index]
    faces = [frame_faces[index] for index in reference_tile.side_indices]
    identity_to_fractional: dict[tuple[int, LatticeShift], np.ndarray] = {}
    identity_to_cartesian: dict[tuple[int, LatticeShift], np.ndarray] = {}
    for face in faces:
        refs = side_refs[face.side_index]
        for ref, fractional, cartesian in zip(
            refs, face.fractional_vertices, face.cartesian_vertices, strict=True
        ):
            identity = (ref.atom_index, ref.image_shift)
            frac = np.asarray(fractional, dtype=np.float64)
            cart = np.asarray(cartesian, dtype=np.float64)
            if identity in identity_to_cartesian:
                if not np.allclose(identity_to_cartesian[identity], cart, rtol=1e-10, atol=options.window_match_tolerance):
                    raise FrameTilingGeometryInvariantError(
                        "One lifted vertex identity maps to inconsistent Cartesian positions."
                    )
            else:
                identity_to_fractional[identity] = frac
                identity_to_cartesian[identity] = cart
    unique_cartesian = tuple(identity_to_cartesian.values())
    if len(unique_cartesian) < 4:
        raise FrameTilingGeometryInvariantError("A mapped tile has fewer than four vertices.")
    pair_tests = len(unique_cartesian) * (len(unique_cartesian) - 1) // 2
    if pair_tests > resources.max_pair_distance_tests:
        raise FrameTilingGeometryResourceError("Tile diameter work exceeds max_pair_distance_tests.")
    reference_point = np.mean(np.vstack(unique_cartesian), axis=0)
    signed_volume = 0.0
    centroid_numerator = np.zeros(3, dtype=np.float64)
    for face in faces:
        center = np.asarray(face.cartesian_center, dtype=np.float64)
        vertices = tuple(np.asarray(point, dtype=np.float64) for point in face.cartesian_vertices)
        for index in range(len(vertices)):
            first = center
            second = vertices[index]
            third = vertices[(index + 1) % len(vertices)]
            tetra = float(
                np.dot(
                    first - reference_point,
                    np.cross(second - reference_point, third - reference_point),
                )
                / 6.0
            )
            signed_volume += tetra
            tetra_center = (reference_point + first + second + third) / 4.0
            centroid_numerator += tetra * tetra_center
    if abs(signed_volume) <= options.degeneracy_tolerance:
        raise FrameTilingGeometryInvariantError("A mapped tile has zero signed volume.")
    cartesian_center = centroid_numerator / signed_volume
    inverse_cell = np.linalg.inv(cell)
    fractional_center = (cartesian_center - np.zeros(3)) @ inverse_cell
    # Cartesian centers include origin; the caller passes origin-shifted vertices.
    # Remove the common origin through the first vertex identity before conversion.
    any_identity = next(iter(identity_to_fractional))
    any_frac = identity_to_fractional[any_identity]
    any_cart = identity_to_cartesian[any_identity]
    inferred_origin = any_cart - any_frac @ cell
    fractional_center = (cartesian_center - inferred_origin) @ inverse_cell
    volume = abs(signed_volume)
    surface_area = sum(face.area for face in faces)
    diameter = max(
        float(np.linalg.norm(left - right))
        for left, right in itertools.combinations(unique_cartesian, 2)
    )
    equivalent_radius = (3.0 * volume / (4.0 * math.pi)) ** (1.0 / 3.0)
    sphericity = math.pi ** (1.0 / 3.0) * (6.0 * volume) ** (2.0 / 3.0) / surface_area
    return FrameNaturalTileGeometry(
        tile_index=tile_index,
        fractional_center=tuple(float(value) for value in fractional_center),
        cartesian_center=tuple(float(value) for value in cartesian_center),
        signed_volume=signed_volume,
        volume=volume,
        surface_area=surface_area,
        equivalent_sphere_radius=equivalent_radius,
        sphericity=sphericity,
        diameter=diameter,
        orientation_preserved=signed_volume > 0,
    )


def _map_windows(
    reference_geometry: TilingGeometryCatalog,
    frame_faces: Sequence[FrameTileFaceGeometry],
    options: FrameTilingGeometryOptions,
) -> tuple[FrameWindowGeometry, ...]:
    by_scientific_face: dict[int, list[FrameTileFaceGeometry]] = defaultdict(list)
    side_reference = {face.side_index: face for face in reference_geometry.tile_faces}
    for face in frame_faces:
        by_scientific_face[side_reference[face.side_index].side.face_index].append(face)
    windows: list[FrameWindowGeometry] = []
    for reference_window in reference_geometry.windows:
        sides = sorted(
            by_scientific_face[reference_window.face_index], key=lambda value: value.side_index
        )
        if len(sides) != 2:
            raise FrameTilingGeometryInvariantError("A mapped window does not have two sides.")
        first, second = sides
        mismatch = abs(first.area - second.area)
        scale = max(first.area, second.area, 1.0)
        if mismatch > options.window_match_tolerance * scale:
            raise FrameTilingGeometryInvariantError(
                "The two translated sides of one mapped window have inconsistent areas."
            )
        aperture_mismatch = abs(
            first.projected_aperture_radius - second.projected_aperture_radius
        )
        if aperture_mismatch > options.window_match_tolerance * max(
            first.projected_aperture_radius, second.projected_aperture_radius, 1.0
        ):
            raise FrameTilingGeometryInvariantError(
                "The two translated sides of one mapped window have inconsistent aperture radii."
            )
        windows.append(
            FrameWindowGeometry(
                window_index=reference_window.window_index,
                cartesian_center=first.cartesian_center,
                area=0.5 * (first.area + second.area),
                side_area_mismatch=mismatch,
                projected_aperture_radius=0.5
                * (
                    first.projected_aperture_radius
                    + second.projected_aperture_radius
                ),
                planarity_rms=max(first.planarity_rms, second.planarity_rms),
                planarity_max=max(first.planarity_max, second.planarity_max),
                planar_aperture_certified=(
                    first.planar_aperture_certified
                    and second.planar_aperture_certified
                ),
            )
        )
    return tuple(windows)


def _map_one_frame(
    result_position: int,
    frame_index: int,
    reference_geometry: TilingGeometryCatalog,
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    topology_catalog: TopologyCatalog,
    side_refs: Sequence[Sequence[LiftedVertexRef]],
    options: FrameTilingGeometryOptions,
    resources: FrameTilingGeometryResources,
) -> MappedTilingFrame:
    state = connectivity.state_for_frame(frame_index)
    topology = build_framework_topology(
        state,
        topology_catalog.mapping,
        validation_rules=topology_catalog.validation_rules,
        options=topology_catalog.projection_options,
    )
    frame_id = int(collection.frame_ids[frame_index])
    step = None if collection.steps is None else int(collection.steps[frame_index])
    time = None if collection.times is None else float(collection.times[frame_index])
    cell = np.asarray(collection.cells[frame_index], dtype=np.float64)
    origin = np.asarray(collection.origins[frame_index], dtype=np.float64)
    cell_volume = abs(float(np.linalg.det(cell)))
    if topology.graph_digest != complex_.topology_graph_digest:
        return MappedTilingFrame(
            result_position=result_position,
            collection_frame_index=frame_index,
            frame_id=frame_id,
            step=step,
            time=time,
            status=FrameTilingGeometryStatus.TOPOLOGY_MISMATCH,
            topology_graph_digest=topology.graph_digest,
            connectivity_state_digest=state.digest,
            global_image_shift=ZERO_SHIFT,
            vertex_atom_indices=tuple(int(value) for value in topology.vertex_atom_indices),
            vertex_image_gauges=tuple(ZERO_SHIFT for _ in topology.vertex_atom_indices),
            tiles=(),
            tile_faces=(),
            windows=(),
            cell_volume=cell_volume,
            total_tile_volume=None,
            volume_closure_error=None,
            diagnostic="The projected framework graph differs from the certified tiling source.",
        )
    try:
        coordinates, global_shift, gauges = _canonical_vertex_coordinates(
            collection, frame_index, state, topology
        )
    except FrameTilingGeometryInvariantError as exc:
        return MappedTilingFrame(
            result_position=result_position,
            collection_frame_index=frame_index,
            frame_id=frame_id,
            step=step,
            time=time,
            status=FrameTilingGeometryStatus.CONNECTIVITY_GEOMETRY_MISMATCH,
            topology_graph_digest=topology.graph_digest,
            connectivity_state_digest=state.digest,
            global_image_shift=ZERO_SHIFT,
            vertex_atom_indices=tuple(int(value) for value in topology.vertex_atom_indices),
            vertex_image_gauges=tuple(ZERO_SHIFT for _ in topology.vertex_atom_indices),
            tiles=(),
            tile_faces=(),
            windows=(),
            cell_volume=cell_volume,
            total_tile_volume=None,
            volume_closure_error=None,
            diagnostic=str(exc),
        )
    try:
        frame_faces = tuple(
            _map_face(
                reference_face,
                side_refs[reference_face.side_index],
                coordinates,
                cell,
                origin,
                options,
            )
            for reference_face in reference_geometry.tile_faces
        )
        tiles = tuple(
            _map_tile(
                tile_index,
                reference_geometry,
                frame_faces,
                side_refs,
                cell,
                resources,
                options,
            )
            for tile_index in range(len(reference_geometry.tiles))
        )
        if any(not tile.orientation_preserved for tile in tiles):
            raise FrameTilingGeometryInvariantError(
                "One or more mapped tile surfaces reversed orientation."
            )
        windows = _map_windows(reference_geometry, frame_faces, options)
        total_volume = sum(tile.volume for tile in tiles)
        closure = abs(total_volume - cell_volume)
        tolerance = options.volume_closure_absolute_tolerance + options.volume_closure_relative_tolerance * cell_volume
        if closure > tolerance:
            raise FrameTilingGeometryInvariantError(
                "Mapped tile volumes do not close to the instantaneous cell volume."
            )
    except FrameTilingGeometryInvariantError as exc:
        return MappedTilingFrame(
            result_position=result_position,
            collection_frame_index=frame_index,
            frame_id=frame_id,
            step=step,
            time=time,
            status=FrameTilingGeometryStatus.DEGENERATE_GEOMETRY,
            topology_graph_digest=topology.graph_digest,
            connectivity_state_digest=state.digest,
            global_image_shift=global_shift,
            vertex_atom_indices=tuple(int(value) for value in topology.vertex_atom_indices),
            vertex_image_gauges=gauges,
            tiles=(),
            tile_faces=(),
            windows=(),
            cell_volume=cell_volume,
            total_tile_volume=None,
            volume_closure_error=None,
            diagnostic=str(exc),
        )
    return MappedTilingFrame(
        result_position=result_position,
        collection_frame_index=frame_index,
        frame_id=frame_id,
        step=step,
        time=time,
        status=FrameTilingGeometryStatus.MAPPED,
        topology_graph_digest=topology.graph_digest,
        connectivity_state_digest=state.digest,
        global_image_shift=global_shift,
        vertex_atom_indices=tuple(int(value) for value in topology.vertex_atom_indices),
        vertex_image_gauges=gauges,
        tiles=tiles,
        tile_faces=frame_faces,
        windows=windows,
        cell_volume=cell_volume,
        total_tile_volume=total_volume,
        volume_closure_error=closure,
    )


def map_tiling_geometry_to_frames(
    reference_geometry: TilingGeometryCatalog,
    complex_: PeriodicCellComplex,
    embedding: PeriodicNetEmbedding,
    ring_index: PrimitiveRingIndex,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    topology_catalog: TopologyCatalog,
    *,
    frame_indices: Sequence[int] | None = None,
    options: FrameTilingGeometryOptions | None = None,
    resources: FrameTilingGeometryResources | None = None,
) -> FrameTilingGeometryCatalog:
    """Map one certified natural tiling onto compatible collection frames.

    Scientific identity is inherited unchanged from ``complex_``.  Every selected
    frame is rebuilt through the supplied atomic connectivity and framework
    mapping.  A topology mismatch or unreplayable periodic gauge remains an
    explicit per-frame outcome instead of mutating the natural tiling.
    """

    _validate_sources(
        reference_geometry,
        complex_,
        embedding,
        ring_index,
        collection,
        connectivity,
        topology_catalog,
    )
    selected = _selected_frames(collection, connectivity, topology_catalog, frame_indices)
    active_options = options or FrameTilingGeometryOptions()
    active_resources = resources or FrameTilingGeometryResources()
    if not isinstance(active_options, FrameTilingGeometryOptions):
        raise FrameTilingGeometryInputError("options must be FrameTilingGeometryOptions.")
    if not isinstance(active_resources, FrameTilingGeometryResources):
        raise FrameTilingGeometryInputError("resources must be FrameTilingGeometryResources.")
    if len(selected) > active_resources.max_frames:
        raise FrameTilingGeometryResourceError("Selected frame count exceeds max_frames.")
    if embedding.n_vertices > active_resources.max_vertices:
        raise FrameTilingGeometryResourceError("Framework vertex count exceeds max_vertices.")
    if len(reference_geometry.tile_faces) > active_resources.max_tile_faces:
        raise FrameTilingGeometryResourceError("Tile-side count exceeds max_tile_faces.")
    vertex_instances = len(selected) * sum(
        len(face.fractional_vertices) for face in reference_geometry.tile_faces
    )
    if vertex_instances > active_resources.max_vertex_instances:
        raise FrameTilingGeometryResourceError(
            "Mapped face-vertex work exceeds max_vertex_instances."
        )

    side_refs = tuple(
        _reference_side_refs(face, complex_, embedding, ring_index)
        for face in reference_geometry.tile_faces
    )
    frames = tuple(
        _map_one_frame(
            position,
            frame,
            reference_geometry,
            complex_,
            embedding,
            ring_index,
            collection,
            connectivity,
            topology_catalog,
            side_refs,
            active_options,
            active_resources,
        )
        for position, frame in enumerate(selected)
    )
    active_atoms = tuple(int(value) for value in connectivity.resolved_scope.atom_indices)
    return FrameTilingGeometryCatalog(
        reference_geometry_digest=reference_geometry.digest,
        periodic_cell_complex_digest=complex_.digest,
        periodic_net_embedding_digest=embedding.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        topology_catalog_digest=topology_catalog.digest,
        collection_geometry_digest=_collection_geometry_digest(
            collection, selected, active_atoms
        ),
        connectivity_binding_digest=_connectivity_binding_digest(
            connectivity, selected
        ),
        options=active_options,
        resources=active_resources,
        frames=frames,
    )


__all__ = [
    "CANONICAL_FRAME_TILING_GEOMETRY_SCHEMA",
    "FRAME_TILING_GEOMETRY_DIGEST_ALGORITHM",
    "FrameNaturalTileGeometry",
    "FrameTileFaceGeometry",
    "FrameTilingGeometryCatalog",
    "FrameTilingGeometryError",
    "FrameTilingGeometryInputError",
    "FrameTilingGeometryInvariantError",
    "FrameTilingGeometryOptions",
    "FrameTilingGeometryResourceError",
    "FrameTilingGeometryResources",
    "FrameTilingGeometrySerializationError",
    "FrameTilingGeometryStatus",
    "FrameWindowGeometry",
    "MappedTilingFrame",
    "map_tiling_geometry_to_frames",
]
