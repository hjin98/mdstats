"""Generic browser-payload accounting for GFX3D-5."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np

from .errors import Graphics3DValidationError
from .primitives import (
    ArrowSet3D, CellWireframe3D, GraphicsPrimitive3D, PointSet3D,
    PolylineSet3D, SegmentSet3D, TextLabelSet3D, TriangleMesh3D,
)


@dataclass(frozen=True, slots=True)
class GraphicsBrowserPayload:
    trace_count: int = 0
    point_count: int = 0
    segment_count: int = 0
    face_count: int = 0
    estimated_geometry_bytes: int = 0

    def to_json_dict(self) -> dict[str, int]:
        return {
            "trace_count": int(self.trace_count),
            "point_count": int(self.point_count),
            "segment_count": int(self.segment_count),
            "face_count": int(self.face_count),
            "estimated_geometry_bytes": int(self.estimated_geometry_bytes),
        }


@dataclass(frozen=True, slots=True)
class GraphicsBrowserBudget:
    max_traces: int = 512
    max_points: int = 5_000_000
    max_faces: int = 1_500_000
    max_geometry_bytes: int = 512 * 1024 * 1024

    @classmethod
    def for_profile(cls, profile: str) -> "GraphicsBrowserBudget":
        key = str(profile).strip().lower()
        if key in {"interactive_browser", "balanced"}:
            return cls()
        if key == "compact":
            return cls(max_traces=320, max_points=2_000_000, max_faces=600_000, max_geometry_bytes=256 * 1024 * 1024)
        if key in {"quality", "raw_reference"}:
            return cls(max_traces=1024, max_points=10_000_000, max_faces=3_000_000, max_geometry_bytes=1024 * 1024 * 1024)
        raise Graphics3DValidationError(f"Unknown GFX3D browser profile {profile!r}.")

    def validate(self, payload: GraphicsBrowserPayload) -> None:
        checks = (
            (payload.trace_count, self.max_traces, "traces"),
            (payload.point_count, self.max_points, "points"),
            (payload.face_count, self.max_faces, "faces"),
            (payload.estimated_geometry_bytes, self.max_geometry_bytes, "geometry bytes"),
        )
        for actual, maximum, label in checks:
            if int(actual) > int(maximum):
                raise Graphics3DValidationError(
                    f"GFX3D browser payload requires {actual} {label}, exceeding the explicit budget {maximum}; "
                    "reduce requested display replication/detail or increase the browser budget explicitly."
                )



def scale_browser_payload(payload: GraphicsBrowserPayload, multiplier: int) -> GraphicsBrowserPayload:
    """Return the exact replicated payload estimate without materializing arrays."""

    count = int(multiplier)
    if count < 1:
        raise Graphics3DValidationError("Browser payload replication multiplier must be >= 1.")
    return GraphicsBrowserPayload(
        trace_count=int(payload.trace_count) * count,
        point_count=int(payload.point_count) * count,
        segment_count=int(payload.segment_count) * count,
        face_count=int(payload.face_count) * count,
        estimated_geometry_bytes=int(payload.estimated_geometry_bytes) * count,
    )


def measure_browser_payload(primitives: Iterable[GraphicsPrimitive3D]) -> GraphicsBrowserPayload:
    traces = points = segments = faces = nbytes = 0
    for primitive in primitives:
        traces += 1
        if isinstance(primitive, PointSet3D):
            points += len(primitive.positions); nbytes += primitive.positions.nbytes
        elif isinstance(primitive, PolylineSet3D):
            points += len(primitive.points); nbytes += primitive.points.nbytes + primitive.offsets.nbytes
        elif isinstance(primitive, SegmentSet3D):
            segments += len(primitive.segments); points += 2 * len(primitive.segments); nbytes += primitive.segments.nbytes
        elif isinstance(primitive, TriangleMesh3D):
            points += len(primitive.vertices); faces += len(primitive.faces); nbytes += primitive.vertices.nbytes + primitive.faces.nbytes
        elif isinstance(primitive, ArrowSet3D):
            points += len(primitive.origins); nbytes += primitive.origins.nbytes + primitive.vectors.nbytes
        elif isinstance(primitive, TextLabelSet3D):
            points += len(primitive.positions); nbytes += primitive.positions.nbytes + sum(len(s.encode("utf8")) for s in primitive.labels)
        elif isinstance(primitive, CellWireframe3D):
            segments += 12; points += 24; nbytes += primitive.cell.nbytes + primitive.origin.nbytes
    return GraphicsBrowserPayload(traces, points, segments, faces, int(nbytes))
