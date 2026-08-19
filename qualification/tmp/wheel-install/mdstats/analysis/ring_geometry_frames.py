"""Stage-11C2 compatible-frame oxygen-ring geometry.

This module maps the fixed Stage-11C1 T/O atom identities and natural-tiling
ring sides onto the compatible frames already certified by Stage 11B.  It
reuses the Stage-11B projected-framework gauge, replays each fixed T-O-T bridge,
and reports instantaneous oxygen-ring geometry without mutating persistent ring
identity.

Closest-fit planes and polygon centroids inherit the Pearson/O'Rourke
construction documented in :mod:`mdstats.analysis.ring_geometry`.  The
reference-aligned in-plane orientation uses the proper orthogonal Procrustes
solution of P. H. Schoenemann, Psychometrika 31, 1-10 (1966),
doi:10.1007/BF02289451.  The periodic source binding, unresolved-state model,
and two-sided natural-tiling replay are mdstats constructions.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from numbers import Integral
from typing import Any, Mapping, Sequence

import numpy as np

from mdstats.collection import AtomisticFrameCollection

from ._neighbors import minimum_image_geometry
from ._periodic_graph import LatticeShift, coerce_lattice_shift
from .atomic_connectivity import AtomicConnectivityResult, AtomicConnectivityState
from .ring_geometry import (
    ReferenceRingGeometry,
    ReferenceRingGeometryCatalog,
    RingGeometryInvariantError,
    RingSideFrame,
    _frame_digest,
    _point_inside_polygon_2d,
    _point_segment_distance_2d,
    _simple_polygon_2d,
)
from .tiling_geometry_frames import (
    FrameTilingGeometryCatalog,
    FrameTilingGeometryStatus,
    MappedTilingFrame,
    _collection_geometry_digest,
    _connectivity_binding_digest,
)

CANONICAL_FRAME_RING_GEOMETRY_SCHEMA = "mdstats.frame-ring-geometry.v1"
FRAME_RING_GEOMETRY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)


class FrameRingGeometryError(ValueError):
    """Base exception for compatible-frame ring geometry."""


class FrameRingGeometryInputError(FrameRingGeometryError):
    """Raised when scientific sources or options violate the 11C2 contract."""


class FrameRingGeometryInvariantError(FrameRingGeometryError):
    """Raised when fixed ring identities cannot be replayed consistently."""


class FrameRingGeometryResourceError(FrameRingGeometryError):
    """Raised transactionally before declared work limits are exceeded."""


class FrameRingGeometrySerializationError(FrameRingGeometryError):
    """Raised when source replay disagrees with serialized output."""


class FrameRingGeometryStatus(str, Enum):
    """Resolution state of one persistent ring in one frame."""

    MAPPED = "mapped"
    REFERENCE_UNRESOLVED = "reference_unresolved"
    TOPOLOGY_MISMATCH = "topology_mismatch"
    MISSING_BRIDGE = "missing_bridge"
    GAUGE_FAILURE = "gauge_failure"
    DEGENERATE_GEOMETRY = "degenerate_geometry"
    UPSTREAM_FRAME_UNRESOLVED = "upstream_frame_unresolved"


class MappedRingFrameStatus(str, Enum):
    """Aggregate state of one mapped frame."""

    MAPPED = "mapped"
    PARTIALLY_MAPPED = "partially_mapped"
    UNRESOLVED = "unresolved"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise FrameRingGeometryInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise FrameRingGeometryInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise FrameRingGeometryInputError(f"{name} must be positive.")
    return result


def _finite(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise FrameRingGeometryInputError(f"{name} must be finite.")
    return result


def _float3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = tuple(_finite(component, name=name) for component in value)
    if len(result) != 3:
        raise FrameRingGeometryInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


def _unit3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    array = np.asarray(_float3(value, name=name), dtype=np.float64)
    if not math.isclose(float(np.linalg.norm(array)), 1.0, rel_tol=1.0e-9, abs_tol=1.0e-9):
        raise FrameRingGeometryInputError(f"{name} must have unit norm.")
    return tuple(float(component) for component in array)  # type: ignore[return-value]


def _points3(
    values: Sequence[Sequence[object]], *, name: str
) -> tuple[tuple[float, float, float], ...]:
    return tuple(_float3(value, name=name) for value in values)


def _shift(value: Sequence[object], *, name: str) -> LatticeShift:
    try:
        return coerce_lattice_shift(value, name=name)
    except ValueError as exc:
        raise FrameRingGeometryInputError(str(exc)) from exc


@dataclass(frozen=True, slots=True)
class FrameRingGeometryOptions:
    """Numerical policy for fixed-identity frame mapping."""

    degeneracy_tolerance: float = 1.0e-12
    path_closure_tolerance: float = 2.0e-8
    subspace_tolerance: float = 1.0e-10

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise FrameRingGeometryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, float]:
        return {name: float(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameRingGeometryOptions":
        return cls(**{name: float(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class FrameRingGeometryResources:
    """Transactional finite-work limits."""

    max_frames: int = 100_000
    max_rings: int = 100_000
    max_vertex_instances: int = 100_000_000
    max_pair_distance_tests: int = 200_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameRingGeometryResources":
        return cls(**{name: int(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class FrameRingGeometry:
    """One persistent natural-tiling ring mapped onto one frame."""

    window_index: int
    face_index: int
    primitive_ring_id: int
    ring_size: int
    status: FrameRingGeometryStatus
    message: str
    t_fractional_vertices: tuple[tuple[float, float, float], ...] = ()
    t_cartesian_vertices: tuple[tuple[float, float, float], ...] = ()
    o_fractional_vertices: tuple[tuple[float, float, float], ...] = ()
    o_cartesian_vertices: tuple[tuple[float, float, float], ...] = ()
    oxygen_vertex_centroid: tuple[float, float, float] | None = None
    oxygen_area_centroid: tuple[float, float, float] | None = None
    oxygen_area_centroid_fractional: tuple[float, float, float] | None = None
    ordered_unit_normal: tuple[float, float, float] | None = None
    side_frames: tuple[RingSideFrame, ...] = ()
    covariance_eigenvalues: tuple[float, float, float] | None = None
    vector_area_magnitude: float | None = None
    projected_area: float | None = None
    perimeter: float | None = None
    planarity_rms: float | None = None
    planarity_max: float | None = None
    puckering_amplitude: float | None = None
    ellipticity: float | None = None
    center_aperture_radius: float | None = None
    t_o_distances: tuple[float, ...] = ()
    o_t_distances: tuple[float, ...] = ()
    center_translation_cartesian: tuple[float, float, float] | None = None
    center_translation_fractional: tuple[float, float, float] | None = None
    reference_normal_dot: float | None = None
    tilt_angle_radians: float | None = None
    in_plane_rotation_radians: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_index", _nonnegative(self.window_index, name="window_index"))
        object.__setattr__(self, "face_index", _nonnegative(self.face_index, name="face_index"))
        object.__setattr__(self, "primitive_ring_id", _nonnegative(self.primitive_ring_id, name="primitive_ring_id"))
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        status = FrameRingGeometryStatus(self.status)
        object.__setattr__(self, "status", status)
        if not isinstance(self.message, str):
            raise FrameRingGeometryInputError("message must be a string.")
        t_frac = _points3(self.t_fractional_vertices, name="t_fractional_vertex")
        t_cart = _points3(self.t_cartesian_vertices, name="t_cartesian_vertex")
        o_frac = _points3(self.o_fractional_vertices, name="o_fractional_vertex")
        o_cart = _points3(self.o_cartesian_vertices, name="o_cartesian_vertex")
        sides = tuple(self.side_frames)
        if status is FrameRingGeometryStatus.MAPPED:
            if not (
                len(t_frac) == len(t_cart) == len(o_frac) == len(o_cart) == self.ring_size
            ):
                raise FrameRingGeometryInputError("Mapped ring polygons must match ring_size.")
            if len(sides) != 2 or any(not isinstance(side, RingSideFrame) for side in sides):
                raise FrameRingGeometryInputError("Mapped rings require two side frames.")
            vector_fields = (
                "oxygen_vertex_centroid",
                "oxygen_area_centroid",
                "oxygen_area_centroid_fractional",
                "ordered_unit_normal",
                "center_translation_cartesian",
                "center_translation_fractional",
            )
            for name in vector_fields:
                value = getattr(self, name)
                if value is None:
                    raise FrameRingGeometryInputError(f"Mapped ring is missing {name}.")
                object.__setattr__(self, name, _float3(value, name=name))
            object.__setattr__(
                self,
                "ordered_unit_normal",
                _unit3(self.ordered_unit_normal, name="ordered_unit_normal"),  # type: ignore[arg-type]
            )
            eigenvalues = self.covariance_eigenvalues
            if eigenvalues is None:
                raise FrameRingGeometryInputError("Mapped ring is missing covariance eigenvalues.")
            eigen = tuple(_finite(value, name="covariance_eigenvalue") for value in eigenvalues)
            if len(eigen) != 3 or tuple(sorted(eigen)) != eigen or any(value < 0 for value in eigen):
                raise FrameRingGeometryInputError("covariance_eigenvalues must be sorted and nonnegative.")
            object.__setattr__(self, "covariance_eigenvalues", eigen)
            positive = {"vector_area_magnitude", "projected_area", "perimeter", "ellipticity"}
            scalar_fields = (
                "vector_area_magnitude",
                "projected_area",
                "perimeter",
                "planarity_rms",
                "planarity_max",
                "puckering_amplitude",
                "ellipticity",
                "center_aperture_radius",
                "reference_normal_dot",
                "tilt_angle_radians",
                "in_plane_rotation_radians",
            )
            for name in scalar_fields:
                value = getattr(self, name)
                if value is None:
                    raise FrameRingGeometryInputError(f"Mapped ring is missing {name}.")
                scalar = _finite(value, name=name)
                if name in positive and scalar <= 0:
                    raise FrameRingGeometryInputError(f"{name} must be positive.")
                if name not in {"in_plane_rotation_radians", "reference_normal_dot"} and scalar < 0:
                    raise FrameRingGeometryInputError(f"{name} must be nonnegative.")
                object.__setattr__(self, name, scalar)
            if not -1.0e-9 <= float(self.reference_normal_dot) <= 1.0 + 1.0e-9:
                raise FrameRingGeometryInputError("reference_normal_dot is outside [-1, 1].")
            if float(self.reference_normal_dot) < -1.0e-9:
                raise FrameRingGeometryInputError("Mapped normal must be sign-aligned to reference.")
            expected_tilt = math.acos(float(np.clip(self.reference_normal_dot, -1.0, 1.0)))
            if not math.isclose(float(self.tilt_angle_radians), expected_tilt, rel_tol=1.0e-9, abs_tol=1.0e-9):
                raise FrameRingGeometryInputError("tilt_angle_radians disagrees with reference_normal_dot.")
            if not -math.pi - 1.0e-9 <= float(self.in_plane_rotation_radians) <= math.pi + 1.0e-9:
                raise FrameRingGeometryInputError("in_plane_rotation_radians must lie in [-pi, pi].")
            if float(self.ellipticity) < 1.0 - 1.0e-9:
                raise FrameRingGeometryInputError("ellipticity must be at least one.")
            t_o = tuple(_finite(value, name="t_o_distance") for value in self.t_o_distances)
            o_t = tuple(_finite(value, name="o_t_distance") for value in self.o_t_distances)
            if len(t_o) != self.ring_size or len(o_t) != self.ring_size or any(value <= 0 for value in (*t_o, *o_t)):
                raise FrameRingGeometryInputError("Mapped bond arrays must be positive and match ring_size.")
            object.__setattr__(self, "t_o_distances", t_o)
            object.__setattr__(self, "o_t_distances", o_t)
            if not np.allclose(
                np.asarray(sides[0].inward_unit_normal),
                -np.asarray(sides[1].inward_unit_normal),
                rtol=0.0,
                atol=1.0e-9,
            ):
                raise FrameRingGeometryInputError("The two dynamic side normals must be opposite.")
        else:
            optional_geometry = (
                self.oxygen_vertex_centroid,
                self.oxygen_area_centroid,
                self.oxygen_area_centroid_fractional,
                self.ordered_unit_normal,
                self.covariance_eigenvalues,
                self.vector_area_magnitude,
                self.projected_area,
                self.perimeter,
                self.planarity_rms,
                self.planarity_max,
                self.puckering_amplitude,
                self.ellipticity,
                self.center_aperture_radius,
                self.center_translation_cartesian,
                self.center_translation_fractional,
                self.reference_normal_dot,
                self.tilt_angle_radians,
                self.in_plane_rotation_radians,
            )
            if any((t_frac, t_cart, o_frac, o_cart, sides, self.t_o_distances, self.o_t_distances)) or any(
                value is not None for value in optional_geometry
            ):
                raise FrameRingGeometryInputError("Unresolved ring records cannot carry partial geometry.")
        object.__setattr__(self, "t_fractional_vertices", t_frac)
        object.__setattr__(self, "t_cartesian_vertices", t_cart)
        object.__setattr__(self, "o_fractional_vertices", o_frac)
        object.__setattr__(self, "o_cartesian_vertices", o_cart)
        object.__setattr__(self, "side_frames", sides)

    @property
    def mapped(self) -> bool:
        return self.status is FrameRingGeometryStatus.MAPPED

    @property
    def geometric_center(self) -> tuple[float, float, float] | None:
        return self.oxygen_area_centroid

    def to_dict(self) -> dict[str, Any]:
        def vector(value: tuple[float, float, float] | None) -> list[float] | None:
            return None if value is None else list(value)

        return {
            "window_index": self.window_index,
            "face_index": self.face_index,
            "primitive_ring_id": self.primitive_ring_id,
            "ring_size": self.ring_size,
            "status": self.status.value,
            "message": self.message,
            "t_fractional_vertices": [list(value) for value in self.t_fractional_vertices],
            "t_cartesian_vertices": [list(value) for value in self.t_cartesian_vertices],
            "o_fractional_vertices": [list(value) for value in self.o_fractional_vertices],
            "o_cartesian_vertices": [list(value) for value in self.o_cartesian_vertices],
            "oxygen_vertex_centroid": vector(self.oxygen_vertex_centroid),
            "oxygen_area_centroid": vector(self.oxygen_area_centroid),
            "oxygen_area_centroid_fractional": vector(self.oxygen_area_centroid_fractional),
            "ordered_unit_normal": vector(self.ordered_unit_normal),
            "side_frames": [side.to_dict() for side in self.side_frames],
            "covariance_eigenvalues": None if self.covariance_eigenvalues is None else list(self.covariance_eigenvalues),
            "vector_area_magnitude": self.vector_area_magnitude,
            "projected_area": self.projected_area,
            "perimeter": self.perimeter,
            "planarity_rms": self.planarity_rms,
            "planarity_max": self.planarity_max,
            "puckering_amplitude": self.puckering_amplitude,
            "ellipticity": self.ellipticity,
            "center_aperture_radius": self.center_aperture_radius,
            "t_o_distances": list(self.t_o_distances),
            "o_t_distances": list(self.o_t_distances),
            "center_translation_cartesian": vector(self.center_translation_cartesian),
            "center_translation_fractional": vector(self.center_translation_fractional),
            "reference_normal_dot": self.reference_normal_dot,
            "tilt_angle_radians": self.tilt_angle_radians,
            "in_plane_rotation_radians": self.in_plane_rotation_radians,
        }


@dataclass(frozen=True, slots=True)
class MappedRingGeometryFrame:
    """Complete ring geometry for one selected collection frame."""

    result_position: int
    collection_frame_index: int
    frame_id: int
    step: int | None
    time: float | None
    status: MappedRingFrameStatus
    upstream_tiling_status: FrameTilingGeometryStatus
    connectivity_state_digest: str
    global_image_shift: LatticeShift
    rings: tuple[FrameRingGeometry, ...]
    diagnostic: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_position", _nonnegative(self.result_position, name="result_position"))
        object.__setattr__(self, "collection_frame_index", _nonnegative(self.collection_frame_index, name="collection_frame_index"))
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, Integral):
            raise FrameRingGeometryInputError("frame_id must be an integer.")
        object.__setattr__(self, "frame_id", int(self.frame_id))
        if self.step is not None:
            object.__setattr__(self, "step", int(self.step))
        if self.time is not None:
            object.__setattr__(self, "time", _finite(self.time, name="time"))
        object.__setattr__(self, "status", MappedRingFrameStatus(self.status))
        object.__setattr__(self, "upstream_tiling_status", FrameTilingGeometryStatus(self.upstream_tiling_status))
        _sha(self.connectivity_state_digest, name="connectivity_state_digest")
        object.__setattr__(self, "global_image_shift", _shift(self.global_image_shift, name="global_image_shift"))
        rings = tuple(self.rings)
        if not rings or tuple(ring.window_index for ring in rings) != tuple(range(len(rings))):
            raise FrameRingGeometryInputError("Frame ring IDs must be nonempty, dense, and ordered.")
        eligible = tuple(
            ring for ring in rings
            if ring.status is not FrameRingGeometryStatus.REFERENCE_UNRESOLVED
        )
        mapped_count = sum(ring.mapped for ring in eligible)
        expected = (
            MappedRingFrameStatus.MAPPED
            if eligible and mapped_count == len(eligible)
            else MappedRingFrameStatus.PARTIALLY_MAPPED
            if mapped_count > 0
            else MappedRingFrameStatus.UNRESOLVED
        )
        if self.status is not expected:
            raise FrameRingGeometryInputError("Frame aggregate status disagrees with ring records.")
        if self.diagnostic is not None and not isinstance(self.diagnostic, str):
            raise FrameRingGeometryInputError("diagnostic must be a string or None.")
        object.__setattr__(self, "rings", rings)

    @property
    def mapped_ring_count(self) -> int:
        return sum(ring.mapped for ring in self.rings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_position": self.result_position,
            "collection_frame_index": self.collection_frame_index,
            "frame_id": self.frame_id,
            "step": self.step,
            "time": self.time,
            "status": self.status.value,
            "upstream_tiling_status": self.upstream_tiling_status.value,
            "connectivity_state_digest": self.connectivity_state_digest,
            "global_image_shift": list(self.global_image_shift),
            "rings": [ring.to_dict() for ring in self.rings],
            "diagnostic": self.diagnostic,
        }


@dataclass(frozen=True, slots=True, eq=False)
class FrameRingGeometryCatalog:
    """Canonical Stage-11C2 compatible-frame ring-geometry result."""

    reference_ring_geometry_digest: str
    frame_tiling_geometry_digest: str
    collection_geometry_digest: str
    connectivity_binding_digest: str
    options: FrameRingGeometryOptions
    resources: FrameRingGeometryResources
    frames: tuple[MappedRingGeometryFrame, ...]
    canonical_schema_version: str = CANONICAL_FRAME_RING_GEOMETRY_SCHEMA
    digest_algorithm: str = FRAME_RING_GEOMETRY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "reference_ring_geometry_digest",
            "frame_tiling_geometry_digest",
            "collection_geometry_digest",
            "connectivity_binding_digest",
        ):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.options, FrameRingGeometryOptions):
            raise FrameRingGeometryInputError("options has the wrong type.")
        if not isinstance(self.resources, FrameRingGeometryResources):
            raise FrameRingGeometryInputError("resources has the wrong type.")
        frames = tuple(self.frames)
        if not frames or tuple(frame.result_position for frame in frames) != tuple(range(len(frames))):
            raise FrameRingGeometryInputError("Frame results must be nonempty and densely ordered.")
        if len({frame.collection_frame_index for frame in frames}) != len(frames):
            raise FrameRingGeometryInputError("Collection frame indices must be unique.")
        identities = tuple(
            (ring.window_index, ring.face_index, ring.primitive_ring_id, ring.ring_size)
            for ring in frames[0].rings
        )
        if any(
            tuple(
                (ring.window_index, ring.face_index, ring.primitive_ring_id, ring.ring_size)
                for ring in frame.rings
            ) != identities
            for frame in frames[1:]
        ):
            raise FrameRingGeometryInputError("Persistent ring identities must agree across frames.")
        if self.canonical_schema_version != CANONICAL_FRAME_RING_GEOMETRY_SCHEMA:
            raise FrameRingGeometryInputError("Unsupported frame-ring geometry schema.")
        if self.digest_algorithm != FRAME_RING_GEOMETRY_DIGEST_ALGORITHM:
            raise FrameRingGeometryInputError("Unsupported frame-ring digest algorithm.")
        object.__setattr__(self, "frames", frames)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise FrameRingGeometryInputError("Stored frame-ring geometry digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, FrameRingGeometryCatalog) and self.digest == other.digest

    @property
    def mapped_frame_count(self) -> int:
        return sum(frame.status is MappedRingFrameStatus.MAPPED for frame in self.frames)

    @property
    def partial_frame_count(self) -> int:
        return sum(frame.status is MappedRingFrameStatus.PARTIALLY_MAPPED for frame in self.frames)

    @property
    def unresolved_frame_count(self) -> int:
        return sum(frame.status is MappedRingFrameStatus.UNRESOLVED for frame in self.frames)

    def ring_metric(self, window_index: int, metric: str) -> np.ndarray:
        index = _nonnegative(window_index, name="window_index")
        allowed = {
            "vector_area_magnitude",
            "projected_area",
            "perimeter",
            "planarity_rms",
            "planarity_max",
            "puckering_amplitude",
            "ellipticity",
            "center_aperture_radius",
            "reference_normal_dot",
            "tilt_angle_radians",
            "in_plane_rotation_radians",
        }
        if metric not in allowed:
            raise FrameRingGeometryInputError(f"Unsupported ring metric {metric!r}.")
        values = np.full(len(self.frames), np.nan, dtype=np.float64)
        for position, frame in enumerate(self.frames):
            if index >= len(frame.rings):
                raise FrameRingGeometryInvariantError("window_index exceeds frame ring count.")
            ring = frame.rings[index]
            if ring.mapped:
                values[position] = float(getattr(ring, metric))
        values.setflags(write=False)
        return values

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "reference_ring_geometry_digest": self.reference_ring_geometry_digest,
            "frame_tiling_geometry_digest": self.frame_tiling_geometry_digest,
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
        reference_geometry: ReferenceRingGeometryCatalog,
        frame_tiling_geometry: FrameTilingGeometryCatalog,
        collection: AtomisticFrameCollection,
        connectivity: AtomicConnectivityResult,
    ) -> "FrameRingGeometryCatalog":
        try:
            rebuilt = map_ring_geometry_to_frames(
                reference_geometry,
                frame_tiling_geometry,
                collection,
                connectivity,
                options=FrameRingGeometryOptions.from_dict(payload["options"]),
                resources=FrameRingGeometryResources.from_dict(payload["resources"]),
            )
            if rebuilt.to_dict() != dict(payload):
                raise FrameRingGeometrySerializationError(
                    "Serialized frame-ring geometry is not canonical for supplied sources."
                )
            return rebuilt
        except FrameRingGeometryError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise FrameRingGeometrySerializationError("Invalid frame-ring geometry payload.") from exc


def _minimum_rotation(source: np.ndarray, target: np.ndarray, tolerance: float) -> np.ndarray:
    source = source / np.linalg.norm(source)
    target = target / np.linalg.norm(target)
    cross = np.cross(source, target)
    sine = float(np.linalg.norm(cross))
    cosine = float(np.clip(np.dot(source, target), -1.0, 1.0))
    if sine <= tolerance:
        if cosine >= 0:
            return np.eye(3, dtype=np.float64)
        # This path should be excluded by sign alignment, but retain a deterministic fallback.
        axis_seed = np.asarray([1.0, 0.0, 0.0])
        if abs(float(np.dot(axis_seed, source))) > 0.9:
            axis_seed = np.asarray([0.0, 1.0, 0.0])
        axis = axis_seed - float(np.dot(axis_seed, source)) * source
        axis /= np.linalg.norm(axis)
        return 2.0 * np.outer(axis, axis) - np.eye(3)
    axis = cross / sine
    skew = np.asarray(
        [[0.0, -axis[2], axis[1]], [axis[2], 0.0, -axis[0]], [-axis[1], axis[0], 0.0]],
        dtype=np.float64,
    )
    return np.eye(3) + sine * skew + (1.0 - cosine) * (skew @ skew)


def _reference_aligned_polygon_geometry(
    points: np.ndarray,
    *,
    reference: ReferenceRingGeometry,
    cell: np.ndarray,
    origin: np.ndarray,
    degeneracy_tolerance: float,
    orientation_tolerance: float,
) -> dict[str, Any]:
    if not reference.resolved:
        raise FrameRingGeometryInvariantError("Reference ring is unresolved.")
    if points.ndim != 2 or points.shape != (reference.ring_size, 3):
        raise FrameRingGeometryInvariantError("Instantaneous O polygon shape disagrees with reference.")
    vertex_center = np.mean(points, axis=0)
    centered = points - vertex_center
    covariance = centered.T @ centered / points.shape[0]
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    normal = np.asarray(eigenvectors[:, 0], dtype=np.float64)
    vector_area = 0.5 * np.sum(np.cross(centered, np.roll(centered, -1, axis=0)), axis=0)
    vector_area_magnitude = float(np.linalg.norm(vector_area))
    if vector_area_magnitude <= degeneracy_tolerance:
        raise FrameRingGeometryInvariantError("The instantaneous O polygon has degenerate vector area.")
    if float(np.dot(normal, vector_area)) < 0:
        normal = -normal
    normal /= np.linalg.norm(normal)
    reference_normal = np.asarray(reference.ordered_unit_normal, dtype=np.float64)
    if float(np.dot(normal, reference_normal)) < 0:
        normal = -normal
    reference_dot = float(np.clip(np.dot(normal, reference_normal), -1.0, 1.0))
    if 1.0 - reference_dot <= max(orientation_tolerance, 1.0e-14):
        reference_dot = 1.0

    rotation = _minimum_rotation(reference_normal, normal, orientation_tolerance)
    reference_u = np.asarray(reference.side_frames[0].axis_u, dtype=np.float64)
    provisional_u = rotation @ reference_u
    provisional_u -= float(np.dot(provisional_u, normal)) * normal
    u_norm = float(np.linalg.norm(provisional_u))
    if u_norm <= orientation_tolerance:
        raise FrameRingGeometryInvariantError("Reference in-plane axis cannot be transported to current plane.")
    provisional_u /= u_norm
    provisional_v = np.cross(normal, provisional_u)
    provisional_v /= np.linalg.norm(provisional_v)

    reference_points = np.asarray(reference.o_cartesian_vertices, dtype=np.float64)
    reference_centered = reference_points - np.mean(reference_points, axis=0)
    reference_v = np.cross(reference_normal, reference_u)
    reference_v /= np.linalg.norm(reference_v)
    reference_2d = np.column_stack((reference_centered @ reference_u, reference_centered @ reference_v))
    current_2d = np.column_stack((centered @ provisional_u, centered @ provisional_v))
    numerator = float(
        np.sum(reference_2d[:, 0] * current_2d[:, 1] - reference_2d[:, 1] * current_2d[:, 0])
    )
    denominator = float(
        np.sum(reference_2d[:, 0] * current_2d[:, 0] + reference_2d[:, 1] * current_2d[:, 1])
    )
    if abs(numerator) <= orientation_tolerance and abs(denominator) <= orientation_tolerance:
        raise FrameRingGeometryInvariantError("O polygon cannot determine a reference-aligned in-plane rotation.")
    in_plane_rotation = math.atan2(numerator, denominator)
    cosine = math.cos(in_plane_rotation)
    sine = math.sin(in_plane_rotation)
    axis_u = cosine * provisional_u + sine * provisional_v
    axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(normal, axis_u)
    axis_v /= np.linalg.norm(axis_v)

    projected = np.column_stack((centered @ axis_u, centered @ axis_v))
    if not _simple_polygon_2d(projected, degeneracy_tolerance):
        raise FrameRingGeometryInvariantError(
            "The instantaneous projected O polygon is self-intersecting or overlapping."
        )
    x = projected[:, 0]
    y = projected[:, 1]
    cross_terms = x * np.roll(y, -1) - np.roll(x, -1) * y
    signed_area = 0.5 * float(np.sum(cross_terms))
    if signed_area <= degeneracy_tolerance:
        raise FrameRingGeometryInvariantError("The instantaneous projected O area is nonpositive.")
    centroid_x = float(np.sum((x + np.roll(x, -1)) * cross_terms) / (6.0 * signed_area))
    centroid_y = float(np.sum((y + np.roll(y, -1)) * cross_terms) / (6.0 * signed_area))
    area_center = vertex_center + centroid_x * axis_u + centroid_y * axis_v
    area_center_fractional = (area_center - origin) @ np.linalg.inv(cell)
    signed_deviations = centered @ normal
    perimeter = sum(
        float(np.linalg.norm(points[(index + 1) % len(points)] - points[index]))
        for index in range(len(points))
    )
    area_center_2d = np.asarray([centroid_x, centroid_y], dtype=np.float64)
    if not _point_inside_polygon_2d(area_center_2d, projected, degeneracy_tolerance):
        raise FrameRingGeometryInvariantError("Instantaneous O-area centroid lies outside polygon.")
    centered_at_area = projected - area_center_2d
    aperture = min(
        _point_segment_distance_2d(
            np.zeros(2, dtype=np.float64),
            centered_at_area[index],
            centered_at_area[(index + 1) % len(points)],
        )
        for index in range(len(points))
    )
    if eigenvalues[1] <= degeneracy_tolerance:
        raise FrameRingGeometryInvariantError("Instantaneous O polygon has degenerate in-plane covariance.")
    ellipticity = math.sqrt(float(eigenvalues[2] / eigenvalues[1]))

    frames: list[RingSideFrame] = []
    for reference_side in reference.side_frames:
        sign = 1.0 if float(np.dot(reference_side.inward_unit_normal, reference_normal)) >= 0 else -1.0
        side_normal = sign * normal
        local_v = np.cross(side_normal, axis_u)
        local_v /= np.linalg.norm(local_v)
        frames.append(
            RingSideFrame(
                side=reference_side.side,
                center=tuple(float(value) for value in area_center),
                inward_unit_normal=tuple(float(value) for value in side_normal),
                axis_u=tuple(float(value) for value in axis_u),
                axis_v=tuple(float(value) for value in local_v),
            )
        )

    return {
        "vertex_center": tuple(float(value) for value in vertex_center),
        "area_center": tuple(float(value) for value in area_center),
        "area_center_fractional": tuple(float(value) for value in area_center_fractional),
        "normal": tuple(float(value) for value in normal),
        "side_frames": tuple(frames),
        "eigenvalues": tuple(float(value) for value in eigenvalues),
        "vector_area_magnitude": vector_area_magnitude,
        "projected_area": signed_area,
        "perimeter": perimeter,
        "planarity_rms": float(np.sqrt(np.mean(signed_deviations * signed_deviations))),
        "planarity_max": float(np.max(np.abs(signed_deviations))),
        "puckering_amplitude": float(np.max(signed_deviations) - np.min(signed_deviations)),
        "ellipticity": ellipticity,
        "center_aperture_radius": aperture,
        "reference_normal_dot": reference_dot,
        "tilt_angle_radians": float(math.acos(reference_dot)),
        "in_plane_rotation_radians": float(in_plane_rotation),
    }


def _unresolved(reference: ReferenceRingGeometry, status: FrameRingGeometryStatus, message: str) -> FrameRingGeometry:
    return FrameRingGeometry(
        window_index=reference.window_index,
        face_index=reference.face_index,
        primitive_ring_id=reference.primitive_ring_id,
        ring_size=reference.ring_size,
        status=status,
        message=message,
    )


def _edge_pair_set(state: AtomicConnectivityState) -> set[tuple[int, int]]:
    return {
        (int(endpoints[0]), int(endpoints[1]))
        for endpoints in np.asarray(state.edge_atom_indices, dtype=np.int64)
    }


def _pair_present(pairs: set[tuple[int, int]], first: int, second: int) -> bool:
    return (min(first, second), max(first, second)) in pairs


def _map_one_ring(
    reference: ReferenceRingGeometry,
    upstream: MappedTilingFrame,
    collection: AtomisticFrameCollection,
    state: AtomicConnectivityState,
    options: FrameRingGeometryOptions,
) -> FrameRingGeometry:
    if not reference.resolved:
        return _unresolved(
            reference,
            FrameRingGeometryStatus.REFERENCE_UNRESOLVED,
            "The persistent Stage-11C1 ring is unresolved.",
        )
    if upstream.status is FrameTilingGeometryStatus.TOPOLOGY_MISMATCH:
        return _unresolved(
            reference,
            FrameRingGeometryStatus.TOPOLOGY_MISMATCH,
            upstream.diagnostic or "The Stage-11B framework topology is incompatible.",
        )
    if upstream.status is not FrameTilingGeometryStatus.MAPPED:
        status = (
            FrameRingGeometryStatus.GAUGE_FAILURE
            if upstream.status is FrameTilingGeometryStatus.CONNECTIVITY_GEOMETRY_MISMATCH
            else FrameRingGeometryStatus.UPSTREAM_FRAME_UNRESOLVED
        )
        return _unresolved(reference, status, upstream.diagnostic or "Stage-11B frame is unresolved.")

    gauges = {
        atom: np.asarray(gauge, dtype=np.int64)
        for atom, gauge in zip(upstream.vertex_atom_indices, upstream.vertex_image_gauges, strict=True)
    }
    wrapped = np.asarray(
        collection.get_wrapped_fractional_positions(upstream.collection_frame_index),
        dtype=np.float64,
    )
    cell = np.asarray(collection.cells[upstream.collection_frame_index], dtype=np.float64)
    origin = np.asarray(collection.origins[upstream.collection_frame_index], dtype=np.float64)
    pbc = np.asarray(collection.pbc, dtype=bool)
    global_shift = np.asarray(upstream.global_image_shift, dtype=np.int64)
    try:
        t_fractional = np.asarray(
            [
                wrapped[ref.atom_index]
                + gauges[ref.atom_index]
                + global_shift
                + np.asarray(ref.image_shift, dtype=np.int64)
                for ref in reference.t_atom_refs
            ],
            dtype=np.float64,
        )
    except KeyError:
        return _unresolved(
            reference,
            FrameRingGeometryStatus.GAUGE_FAILURE,
            "A fixed T atom is absent from the Stage-11B projected-framework gauge.",
        )
    t_cartesian = t_fractional @ cell + origin
    pairs = _edge_pair_set(state)
    oxygen_fractional: list[np.ndarray] = []
    t_o_distances: list[float] = []
    o_t_distances: list[float] = []
    for index, oxygen_ref in enumerate(reference.o_atom_refs):
        source_ref = reference.t_atom_refs[index]
        target_ref = reference.t_atom_refs[(index + 1) % reference.ring_size]
        if not (
            _pair_present(pairs, source_ref.atom_index, oxygen_ref.atom_index)
            and _pair_present(pairs, oxygen_ref.atom_index, target_ref.atom_index)
        ):
            return _unresolved(
                reference,
                FrameRingGeometryStatus.MISSING_BRIDGE,
                "The current connectivity state does not contain the fixed T-O-T bridge.",
            )
        source_gauge_float = t_fractional[index] - wrapped[source_ref.atom_index]
        source_gauge = np.rint(source_gauge_float).astype(np.int64)
        if not np.allclose(
            source_gauge_float,
            source_gauge,
            rtol=0.0,
            atol=options.path_closure_tolerance,
        ):
            return _unresolved(
                reference,
                FrameRingGeometryStatus.GAUGE_FAILURE,
                "Mapped T coordinate is not related to its wrapped atom by an integer image.",
            )
        source_displacement = (wrapped[oxygen_ref.atom_index] - wrapped[source_ref.atom_index]) @ cell
        _vector, _distance, source_to_oxygen = minimum_image_geometry(
            source_displacement, cell=cell, pbc=pbc
        )
        oxygen_gauge = source_gauge + np.asarray(source_to_oxygen, dtype=np.int64)
        oxygen_frac = wrapped[oxygen_ref.atom_index] + oxygen_gauge
        target_displacement = (wrapped[target_ref.atom_index] - wrapped[oxygen_ref.atom_index]) @ cell
        _vector, _distance, oxygen_to_target = minimum_image_geometry(
            target_displacement, cell=cell, pbc=pbc
        )
        replayed_target = oxygen_frac + (
            wrapped[target_ref.atom_index]
            - wrapped[oxygen_ref.atom_index]
            + np.asarray(oxygen_to_target, dtype=np.int64)
        )
        target_fractional = t_fractional[(index + 1) % reference.ring_size]
        if not np.allclose(
            replayed_target,
            target_fractional,
            rtol=0.0,
            atol=options.path_closure_tolerance,
        ):
            return _unresolved(
                reference,
                FrameRingGeometryStatus.GAUGE_FAILURE,
                "The fixed T-O-T bridge does not close onto the mapped target T.",
            )
        oxygen_fractional.append(oxygen_frac)
        oxygen_cart = oxygen_frac @ cell + origin
        t_o_distances.append(float(np.linalg.norm(oxygen_cart - t_cartesian[index])))
        o_t_distances.append(
            float(np.linalg.norm(t_cartesian[(index + 1) % reference.ring_size] - oxygen_cart))
        )

    oxygen_fractional_array = np.asarray(oxygen_fractional, dtype=np.float64)
    oxygen_cartesian = oxygen_fractional_array @ cell + origin
    try:
        descriptors = _reference_aligned_polygon_geometry(
            oxygen_cartesian,
            reference=reference,
            cell=cell,
            origin=origin,
            degeneracy_tolerance=options.degeneracy_tolerance,
            orientation_tolerance=options.subspace_tolerance,
        )
    except (FrameRingGeometryInvariantError, RingGeometryInvariantError) as exc:
        return _unresolved(
            reference,
            FrameRingGeometryStatus.DEGENERATE_GEOMETRY,
            str(exc),
        )
    area_center = np.asarray(descriptors["area_center"], dtype=np.float64)
    area_center_fractional = np.asarray(descriptors["area_center_fractional"], dtype=np.float64)
    return FrameRingGeometry(
        window_index=reference.window_index,
        face_index=reference.face_index,
        primitive_ring_id=reference.primitive_ring_id,
        ring_size=reference.ring_size,
        status=FrameRingGeometryStatus.MAPPED,
        message="",
        t_fractional_vertices=tuple(tuple(float(value) for value in point) for point in t_fractional),
        t_cartesian_vertices=tuple(tuple(float(value) for value in point) for point in t_cartesian),
        o_fractional_vertices=tuple(tuple(float(value) for value in point) for point in oxygen_fractional_array),
        o_cartesian_vertices=tuple(tuple(float(value) for value in point) for point in oxygen_cartesian),
        oxygen_vertex_centroid=descriptors["vertex_center"],
        oxygen_area_centroid=descriptors["area_center"],
        oxygen_area_centroid_fractional=descriptors["area_center_fractional"],
        ordered_unit_normal=descriptors["normal"],
        side_frames=descriptors["side_frames"],
        covariance_eigenvalues=descriptors["eigenvalues"],
        vector_area_magnitude=descriptors["vector_area_magnitude"],
        projected_area=descriptors["projected_area"],
        perimeter=descriptors["perimeter"],
        planarity_rms=descriptors["planarity_rms"],
        planarity_max=descriptors["planarity_max"],
        puckering_amplitude=descriptors["puckering_amplitude"],
        ellipticity=descriptors["ellipticity"],
        center_aperture_radius=descriptors["center_aperture_radius"],
        t_o_distances=tuple(t_o_distances),
        o_t_distances=tuple(o_t_distances),
        center_translation_cartesian=tuple(
            float(value)
            for value in area_center - np.asarray(reference.oxygen_area_centroid, dtype=np.float64)
        ),
        center_translation_fractional=tuple(
            float(value)
            for value in area_center_fractional
            - np.asarray(reference.oxygen_area_centroid_fractional, dtype=np.float64)
        ),
        reference_normal_dot=descriptors["reference_normal_dot"],
        tilt_angle_radians=descriptors["tilt_angle_radians"],
        in_plane_rotation_radians=descriptors["in_plane_rotation_radians"],
    )


def _aggregate_status(rings: Sequence[FrameRingGeometry]) -> MappedRingFrameStatus:
    eligible = tuple(
        ring for ring in rings
        if ring.status is not FrameRingGeometryStatus.REFERENCE_UNRESOLVED
    )
    mapped = sum(ring.mapped for ring in eligible)
    if eligible and mapped == len(eligible):
        return MappedRingFrameStatus.MAPPED
    if mapped:
        return MappedRingFrameStatus.PARTIALLY_MAPPED
    return MappedRingFrameStatus.UNRESOLVED


def _validate_sources(
    reference_geometry: ReferenceRingGeometryCatalog,
    frame_tiling_geometry: FrameTilingGeometryCatalog,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
) -> tuple[int, ...]:
    if not isinstance(reference_geometry, ReferenceRingGeometryCatalog):
        raise FrameRingGeometryInputError("reference_geometry has the wrong type.")
    if not isinstance(frame_tiling_geometry, FrameTilingGeometryCatalog):
        raise FrameRingGeometryInputError("frame_tiling_geometry has the wrong type.")
    if not isinstance(collection, AtomisticFrameCollection):
        raise FrameRingGeometryInputError("collection has the wrong type.")
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise FrameRingGeometryInputError("connectivity has the wrong type.")
    if frame_tiling_geometry.reference_geometry_digest != reference_geometry.tiling_geometry_digest:
        raise FrameRingGeometryInputError("Frame tiling and reference ring catalog use different tiling geometry.")
    if frame_tiling_geometry.periodic_cell_complex_digest != reference_geometry.periodic_cell_complex_digest:
        raise FrameRingGeometryInputError("Frame tiling and reference ring catalog use different cell complexes.")
    if reference_geometry.frame_index >= collection.n_frames:
        raise FrameRingGeometryInputError("Reference-ring frame index exceeds collection.")
    if _frame_digest(collection, reference_geometry.frame_index) != reference_geometry.reference_frame_digest:
        raise FrameRingGeometryInputError("Collection no longer contains the Stage-11C1 reference frame identity.")
    frame_indices = tuple(frame.collection_frame_index for frame in frame_tiling_geometry.frames)
    active_atoms = tuple(int(value) for value in connectivity.resolved_scope.atom_indices)
    collection_digest = _collection_geometry_digest(collection, frame_indices, active_atoms)
    if collection_digest != frame_tiling_geometry.collection_geometry_digest:
        raise FrameRingGeometryInputError("Collection geometry disagrees with Stage-11B binding.")
    connectivity_digest = _connectivity_binding_digest(connectivity, frame_indices)
    if connectivity_digest != frame_tiling_geometry.connectivity_binding_digest:
        raise FrameRingGeometryInputError("Atomic connectivity disagrees with Stage-11B binding.")
    for frame in frame_tiling_geometry.frames:
        state = connectivity.state_for_frame(frame.collection_frame_index)
        if state.digest != frame.connectivity_state_digest:
            raise FrameRingGeometryInputError("Stage-11B frame and atomic connectivity state disagree.")
    return frame_indices


def map_ring_geometry_to_frames(
    reference_geometry: ReferenceRingGeometryCatalog,
    frame_tiling_geometry: FrameTilingGeometryCatalog,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    *,
    options: FrameRingGeometryOptions | None = None,
    resources: FrameRingGeometryResources | None = None,
) -> FrameRingGeometryCatalog:
    """Map persistent Stage-11C1 T/O ring identities over Stage-11B frames."""

    frame_indices = _validate_sources(
        reference_geometry,
        frame_tiling_geometry,
        collection,
        connectivity,
    )
    active_options = options or FrameRingGeometryOptions()
    active_resources = resources or FrameRingGeometryResources()
    if not isinstance(active_options, FrameRingGeometryOptions):
        raise FrameRingGeometryInputError("options must be FrameRingGeometryOptions.")
    if not isinstance(active_resources, FrameRingGeometryResources):
        raise FrameRingGeometryInputError("resources must be FrameRingGeometryResources.")
    n_frames = len(frame_indices)
    n_rings = len(reference_geometry.rings)
    if n_frames > active_resources.max_frames:
        raise FrameRingGeometryResourceError("Selected frame count exceeds max_frames.")
    if n_rings > active_resources.max_rings:
        raise FrameRingGeometryResourceError("Persistent ring count exceeds max_rings.")
    vertex_instances = n_frames * sum(2 * ring.ring_size for ring in reference_geometry.rings)
    if vertex_instances > active_resources.max_vertex_instances:
        raise FrameRingGeometryResourceError("Mapped T/O vertex work exceeds max_vertex_instances.")
    pair_tests = n_frames * sum(2 * ring.ring_size for ring in reference_geometry.rings if ring.resolved)
    if pair_tests > active_resources.max_pair_distance_tests:
        raise FrameRingGeometryResourceError("Bridge minimum-image work exceeds max_pair_distance_tests.")

    frames: list[MappedRingGeometryFrame] = []
    for position, upstream in enumerate(frame_tiling_geometry.frames):
        state = connectivity.state_for_frame(upstream.collection_frame_index)
        rings = tuple(
            _map_one_ring(reference, upstream, collection, state, active_options)
            for reference in reference_geometry.rings
        )
        frames.append(
            MappedRingGeometryFrame(
                result_position=position,
                collection_frame_index=upstream.collection_frame_index,
                frame_id=upstream.frame_id,
                step=upstream.step,
                time=upstream.time,
                status=_aggregate_status(rings),
                upstream_tiling_status=upstream.status,
                connectivity_state_digest=state.digest,
                global_image_shift=upstream.global_image_shift,
                rings=rings,
                diagnostic=upstream.diagnostic,
            )
        )

    active_atoms = tuple(int(value) for value in connectivity.resolved_scope.atom_indices)
    return FrameRingGeometryCatalog(
        reference_ring_geometry_digest=reference_geometry.digest,
        frame_tiling_geometry_digest=frame_tiling_geometry.digest,
        collection_geometry_digest=_collection_geometry_digest(collection, frame_indices, active_atoms),
        connectivity_binding_digest=_connectivity_binding_digest(connectivity, frame_indices),
        options=active_options,
        resources=active_resources,
        frames=tuple(frames),
    )


__all__ = [
    "CANONICAL_FRAME_RING_GEOMETRY_SCHEMA",
    "FRAME_RING_GEOMETRY_DIGEST_ALGORITHM",
    "FrameRingGeometry",
    "FrameRingGeometryCatalog",
    "FrameRingGeometryError",
    "FrameRingGeometryInputError",
    "FrameRingGeometryInvariantError",
    "FrameRingGeometryOptions",
    "FrameRingGeometryResourceError",
    "FrameRingGeometryResources",
    "FrameRingGeometrySerializationError",
    "FrameRingGeometryStatus",
    "MappedRingFrameStatus",
    "MappedRingGeometryFrame",
    "map_ring_geometry_to_frames",
]
