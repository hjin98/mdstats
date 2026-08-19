"""Renderer-neutral graphical primitive contracts for GFX3D."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .errors import Graphics3DValidationError
from .identity import canonical_value

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


def _readonly(value: Any, *, dtype: Any, ndim: int, name: str) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if array.ndim != ndim:
        raise Graphics3DValidationError(f"{name} must have ndim={ndim}; got {array.shape}.")
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise Graphics3DValidationError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


def _metadata(value: Mapping[str, Any]) -> Mapping[str, Any]:
    normalized = canonical_value(value)
    assert isinstance(normalized, dict)
    return MappingProxyType(normalized)


@dataclass(frozen=True, slots=True)
class GraphicsPrimitive3D:
    owner_layer: str
    primitive_id: str
    render_attributes: Mapping[str, Any] = field(default_factory=dict)
    scientific_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        owner = str(self.owner_layer).strip()
        primitive_id = str(self.primitive_id).strip()
        if not owner or not primitive_id:
            raise Graphics3DValidationError("owner_layer and primitive_id must be nonempty.")
        object.__setattr__(self, "owner_layer", owner)
        object.__setattr__(self, "primitive_id", primitive_id)
        object.__setattr__(self, "render_attributes", _metadata(self.render_attributes))
        object.__setattr__(self, "scientific_refs", tuple(str(value) for value in self.scientific_refs))


@dataclass(frozen=True, slots=True)
class PointSet3D(GraphicsPrimitive3D):
    positions: FloatArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        positions = _readonly(self.positions, dtype=np.float64, ndim=2, name="positions")
        if positions.shape[1:] != (3,):
            raise Graphics3DValidationError("PointSet3D positions must have shape (N, 3).")
        object.__setattr__(self, "positions", positions)


@dataclass(frozen=True, slots=True)
class PolylineSet3D(GraphicsPrimitive3D):
    points: FloatArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    offsets: IntArray = field(default_factory=lambda: np.asarray([0], dtype=np.int64))

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        points = _readonly(self.points, dtype=np.float64, ndim=2, name="points")
        offsets = _readonly(self.offsets, dtype=np.int64, ndim=1, name="offsets")
        if points.shape[1:] != (3,):
            raise Graphics3DValidationError("PolylineSet3D points must have shape (N, 3).")
        if offsets.size < 1 or offsets[0] != 0 or offsets[-1] != len(points) or np.any(np.diff(offsets) < 0):
            raise Graphics3DValidationError("PolylineSet3D offsets must span points monotonically from 0 to N.")
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "offsets", offsets)


@dataclass(frozen=True, slots=True)
class SegmentSet3D(GraphicsPrimitive3D):
    segments: FloatArray = field(default_factory=lambda: np.empty((0, 2, 3), dtype=np.float64))

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        segments = _readonly(self.segments, dtype=np.float64, ndim=3, name="segments")
        if segments.shape[1:] != (2, 3):
            raise Graphics3DValidationError("SegmentSet3D segments must have shape (N, 2, 3).")
        object.__setattr__(self, "segments", segments)


@dataclass(frozen=True, slots=True)
class TriangleMesh3D(GraphicsPrimitive3D):
    vertices: FloatArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    faces: IntArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.int64))

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        vertices = _readonly(self.vertices, dtype=np.float64, ndim=2, name="vertices")
        faces = _readonly(self.faces, dtype=np.int64, ndim=2, name="faces")
        if vertices.shape[1:] != (3,) or faces.shape[1:] != (3,):
            raise Graphics3DValidationError("TriangleMesh3D vertices/faces must have shapes (N,3)/(M,3).")
        if faces.size and (np.any(faces < 0) or np.any(faces >= len(vertices))):
            raise Graphics3DValidationError("TriangleMesh3D faces reference invalid vertices.")
        object.__setattr__(self, "vertices", vertices)
        object.__setattr__(self, "faces", faces)


@dataclass(frozen=True, slots=True)
class ArrowSet3D(GraphicsPrimitive3D):
    origins: FloatArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    vectors: FloatArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        origins = _readonly(self.origins, dtype=np.float64, ndim=2, name="origins")
        vectors = _readonly(self.vectors, dtype=np.float64, ndim=2, name="vectors")
        if origins.shape != vectors.shape or origins.shape[1:] != (3,):
            raise Graphics3DValidationError("ArrowSet3D origins/vectors must both have shape (N,3).")
        object.__setattr__(self, "origins", origins)
        object.__setattr__(self, "vectors", vectors)


@dataclass(frozen=True, slots=True)
class TextLabelSet3D(GraphicsPrimitive3D):
    positions: FloatArray = field(default_factory=lambda: np.empty((0, 3), dtype=np.float64))
    labels: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        positions = _readonly(self.positions, dtype=np.float64, ndim=2, name="positions")
        if positions.shape[1:] != (3,) or len(self.labels) != len(positions):
            raise Graphics3DValidationError("TextLabelSet3D positions/labels must align with shape (N,3).")
        object.__setattr__(self, "positions", positions)
        object.__setattr__(self, "labels", tuple(str(value) for value in self.labels))


@dataclass(frozen=True, slots=True)
class CellWireframe3D(GraphicsPrimitive3D):
    cell: FloatArray = field(default_factory=lambda: np.eye(3, dtype=np.float64))
    origin: FloatArray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))

    def __post_init__(self) -> None:
        GraphicsPrimitive3D.__post_init__(self)
        cell = _readonly(self.cell, dtype=np.float64, ndim=2, name="cell")
        origin = _readonly(self.origin, dtype=np.float64, ndim=1, name="origin")
        if cell.shape != (3, 3) or origin.shape != (3,) or abs(float(np.linalg.det(cell))) <= 1e-12:
            raise Graphics3DValidationError("CellWireframe3D requires a nonsingular 3x3 cell and 3-vector origin.")
        object.__setattr__(self, "cell", cell)
        object.__setattr__(self, "origin", origin)


@dataclass(frozen=True, slots=True)
class LegendGroup:
    name: str
    owner_layer: str
    initially_visible: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.name).strip() or not str(self.owner_layer).strip():
            raise Graphics3DValidationError("LegendGroup name and owner_layer must be nonempty.")
        object.__setattr__(self, "name", str(self.name).strip())
        object.__setattr__(self, "owner_layer", str(self.owner_layer).strip())
        object.__setattr__(self, "metadata", _metadata(self.metadata))
