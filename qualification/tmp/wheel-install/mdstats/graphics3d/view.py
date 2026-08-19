"""Renderer-neutral GFX3D view and periodic-display semantics (GFX3D-5)."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from itertools import product
from typing import Any

import numpy as np

from .errors import Graphics3DValidationError
from .primitives import (
    ArrowSet3D,
    CellWireframe3D,
    GraphicsPrimitive3D,
    PointSet3D,
    PolylineSet3D,
    SegmentSet3D,
    TextLabelSet3D,
    TriangleMesh3D,
)


def _triplet(value: Any, *, name: str, integer: bool = False) -> tuple[Any, Any, Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 3:
        raise Graphics3DValidationError(f"{name} must contain exactly three values.")
    if integer:
        if any(not isinstance(v, (int, np.integer)) or isinstance(v, (bool, np.bool_)) for v in value):
            raise Graphics3DValidationError(f"{name} must contain exact integers; fractional values are not allowed.")
        result = tuple(int(v) for v in value)
    else:
        try:
            result = tuple(float(v) for v in value)
        except (TypeError, ValueError) as exc:
            raise Graphics3DValidationError(f"{name} must contain three numeric values.") from exc
        if not np.all(np.isfinite(result)):
            raise Graphics3DValidationError(f"{name} must contain only finite values.")
    return result  # type: ignore[return-value]


def resolve_periodic_image_shifts(view: Mapping[str, Any]) -> tuple[tuple[int, int, int], ...]:
    """Resolve one scene-wide periodic display declaration.

    Supported forms for ``view.periodic_images`` are:
    - omitted / ``"reference"`` / ``"1x1x1"`` -> only the canonical image;
    - ``"NxMxK"`` or ``[N, M, K]`` -> nonnegative image counts from the reference cell;
    - ``[[i,j,k], ...]`` -> explicit integer image shifts;
    - ``{counts=[N,M,K], origin=[i,j,k]}`` -> shifted rectangular image block.
    """
    raw = view.get("periodic_images")
    if raw is None or raw in ("reference", "1x1x1", "none"):
        return ((0, 0, 0),)
    if isinstance(raw, str):
        text = raw.strip().lower().replace("×", "x")
        parts = text.split("x")
        if len(parts) != 3:
            raise Graphics3DValidationError(
                "view.periodic_images string must be 'reference' or an NxMxK count such as '2x2x1'."
            )
        try:
            counts = tuple(int(v) for v in parts)
        except ValueError as exc:
            raise Graphics3DValidationError(
                "view.periodic_images NxMxK values must be positive integers."
            ) from exc
        origin = (0, 0, 0)
    elif isinstance(raw, Mapping):
        unknown = set(raw) - {"counts", "origin"}
        if unknown:
            raise Graphics3DValidationError(
                "Unsupported view.periodic_images mapping keys: " + ", ".join(sorted(map(str, unknown)))
            )
        counts = _triplet(raw.get("counts", (1, 1, 1)), name="periodic_images.counts", integer=True)
        origin = _triplet(raw.get("origin", (0, 0, 0)), name="periodic_images.origin", integer=True)
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        if len(raw) == 3 and all(isinstance(v, (int, np.integer)) and not isinstance(v, bool) for v in raw):
            counts = tuple(int(v) for v in raw)
            origin = (0, 0, 0)
        else:
            shifts = tuple(_triplet(item, name="periodic image shift", integer=True) for item in raw)
            if not shifts:
                raise Graphics3DValidationError("view.periodic_images explicit shift list cannot be empty.")
            return tuple(dict.fromkeys(shifts))
    else:
        raise Graphics3DValidationError("Unsupported view.periodic_images declaration.")
    if any(int(v) <= 0 for v in counts):
        raise Graphics3DValidationError("periodic image counts must be positive integers.")
    return tuple(
        (int(origin[0] + i), int(origin[1] + j), int(origin[2] + k))
        for i, j, k in product(range(int(counts[0])), range(int(counts[1])), range(int(counts[2])))
    )


def resolve_view_visibility(view: Mapping[str, Any], layer_names: Sequence[str]) -> frozenset[str] | None:
    raw = view.get("visible_layers")
    if raw is None:
        return None
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        raise Graphics3DValidationError("view.visible_layers must be an array of layer names.")
    values = tuple(str(v).strip() for v in raw)
    unknown = set(values) - set(layer_names)
    if unknown:
        raise Graphics3DValidationError(
            "view.visible_layers names are not present in the scene: " + ", ".join(sorted(unknown))
        )
    return frozenset(values)


def resolve_camera(view: Mapping[str, Any]) -> dict[str, Any]:
    projection = str(view.get("projection", "orthographic"))
    if projection not in {"orthographic", "perspective"}:
        raise Graphics3DValidationError("view.projection must be 'orthographic' or 'perspective'.")
    camera: dict[str, Any] = {"projection": {"type": projection}}
    raw = view.get("camera")
    if raw is None:
        return camera
    if isinstance(raw, str):
        key = raw.strip().lower().replace("[", "").replace("]", "")
        directions = {
            "100": (1.8, 0.0, 0.0),
            "010": (0.0, 1.8, 0.0),
            "001": (0.0, 0.0, 1.8),
            "110": (1.35, 1.35, 0.0),
            "101": (1.35, 0.0, 1.35),
            "011": (0.0, 1.35, 1.35),
            "111": (1.2, 1.2, 1.2),
            "isometric": (1.2, 1.2, 1.2),
        }
        if key not in directions:
            raise Graphics3DValidationError(
                "Unknown camera preset; use [100], [010], [001], [110], [101], [011], [111], or isometric."
            )
        eye = directions[key]
        camera["eye"] = dict(zip(("x", "y", "z"), eye, strict=True))
        return camera
    if isinstance(raw, Mapping):
        unknown = set(raw) - {"eye", "up", "center"}
        if unknown:
            raise Graphics3DValidationError(
                "Unsupported view.camera mapping keys: " + ", ".join(sorted(map(str, unknown)))
            )
        if "eye" in raw:
            eye = _triplet(raw["eye"], name="camera.eye")
            if np.linalg.norm(np.asarray(eye, dtype=float)) == 0:
                raise Graphics3DValidationError("camera.eye must be finite and nonzero.")
            camera["eye"] = dict(zip(("x", "y", "z"), eye, strict=True))
        if "up" in raw:
            up = _triplet(raw["up"], name="camera.up")
            if np.linalg.norm(np.asarray(up, dtype=float)) == 0:
                raise Graphics3DValidationError("camera.up must be finite and nonzero.")
            camera["up"] = dict(zip(("x", "y", "z"), up, strict=True))
        if "center" in raw:
            center = _triplet(raw["center"], name="camera.center")
            camera["center"] = dict(zip(("x", "y", "z"), center, strict=True))
        return camera
    eye = _triplet(raw, name="view.camera")
    if not np.all(np.isfinite(eye)) or np.linalg.norm(np.asarray(eye, dtype=float)) == 0:
        raise Graphics3DValidationError("view.camera eye must be finite and nonzero.")
    camera["eye"] = dict(zip(("x", "y", "z"), eye, strict=True))
    return camera


def resolve_cell_mode(view: Mapping[str, Any]) -> str:
    mode = str(view.get("cell_mode", "reference")).strip().lower()
    if mode not in {"reference", "none"}:
        raise Graphics3DValidationError("view.cell_mode must be 'reference' or 'none'.")
    return mode


def replicate_primitive(
    primitive: GraphicsPrimitive3D,
    *,
    cell: np.ndarray | None,
    shifts: Sequence[tuple[int, int, int]],
) -> tuple[GraphicsPrimitive3D, ...]:
    """Replicate one primitive by scene-wide lattice image shifts."""
    if len(shifts) == 1 and tuple(shifts[0]) == (0, 0, 0):
        return (primitive,)
    if cell is None:
        raise Graphics3DValidationError("Periodic display replication requires a scene display cell.")
    matrix = np.asarray(cell, dtype=np.float64)
    if matrix.shape != (3, 3):
        raise Graphics3DValidationError("Scene display cell must have shape (3,3).")
    result: list[GraphicsPrimitive3D] = []
    for shift in shifts:
        delta = np.asarray(shift, dtype=np.float64) @ matrix
        attrs = {**dict(primitive.render_attributes), "image_shift": tuple(int(v) for v in shift)}
        pid = primitive.primitive_id + f"@{shift[0]},{shift[1]},{shift[2]}"
        common = dict(
            owner_layer=primitive.owner_layer,
            primitive_id=pid,
            render_attributes=attrs,
            scientific_refs=primitive.scientific_refs,
        )
        if isinstance(primitive, PointSet3D):
            value = PointSet3D(**common, positions=primitive.positions + delta)
        elif isinstance(primitive, PolylineSet3D):
            value = PolylineSet3D(**common, points=primitive.points + delta, offsets=primitive.offsets)
        elif isinstance(primitive, SegmentSet3D):
            value = SegmentSet3D(**common, segments=primitive.segments + delta)
        elif isinstance(primitive, TriangleMesh3D):
            value = TriangleMesh3D(**common, vertices=primitive.vertices + delta, faces=primitive.faces)
        elif isinstance(primitive, ArrowSet3D):
            value = ArrowSet3D(**common, origins=primitive.origins + delta, vectors=primitive.vectors)
        elif isinstance(primitive, TextLabelSet3D):
            value = TextLabelSet3D(**common, positions=primitive.positions + delta, labels=primitive.labels)
        elif isinstance(primitive, CellWireframe3D):
            value = CellWireframe3D(**common, cell=primitive.cell, origin=primitive.origin + delta)
        else:  # pragma: no cover - future primitive must opt into replication explicitly
            raise Graphics3DValidationError(
                f"Periodic display replication does not support primitive type {type(primitive).__name__}."
            )
        result.append(value)
    return tuple(result)
