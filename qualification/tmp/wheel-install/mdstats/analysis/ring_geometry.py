"""Stage-11C1 source-bound reference geometry for natural-tiling rings.

This module binds each natural-tiling window to its primitive projected T ring,
the exact framework edge paths that decorate that ring, and one atomistic
reference frame.  It resolves the ordered bridging-oxygen polygon, computes a
purely geometric oxygen-ring center and best-fit plane, and creates two
persistent side-local frames from the translated tile incidences.

The polygon-plane construction follows Pearson's closest-fit-plane formulation
(K. Pearson, Philosophical Magazine 2, 559-572, 1901;
doi:10.1080/14786440109462720).  The ordered polygon area and area-centroid
formulas are standard Green-theorem identities in the computational-geometry
form summarized by J. O'Rourke, *Computational Geometry in C*, 2nd ed.
Their source-bound periodic assembly and two-sided natural-tiling binding are
mdstats constructions.
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
from ._periodic_graph import LatticeShift, add_shift, coerce_lattice_shift
from .atomic_connectivity import AtomicConnectivityResult, AtomicEdgeKey, AtomicConnectivityState
from .framework_topology import FrameworkTopology
from .periodic_cell_complex import PeriodicCellComplex
from .primitive_ring import PrimitiveRing, PrimitiveRingStep
from .primitive_ring_index import PrimitiveRingIndex
from .tiling_geometry import TileSideRef, TilingGeometryCatalog
from .tiling_geometry_frames import _canonical_vertex_coordinates

CANONICAL_REFERENCE_RING_GEOMETRY_SCHEMA = "mdstats.reference-ring-geometry.v1"
REFERENCE_RING_GEOMETRY_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
ZERO_SHIFT: LatticeShift = (0, 0, 0)


class RingGeometryError(ValueError):
    """Base exception for persistent ring geometry."""


class RingGeometryInputError(RingGeometryError):
    """Raised when source objects or options violate the Stage-11C1 contract."""


class RingGeometryInvariantError(RingGeometryError):
    """Raised when source-bound ring identities cannot be replayed consistently."""


class RingGeometryResourceError(RingGeometryError):
    """Raised transactionally before declared finite work limits are exceeded."""


class RingGeometrySerializationError(RingGeometryError):
    """Raised when deterministic replay disagrees with serialized output."""


class RingGeometryStatus(str, Enum):
    """Resolution state of one natural-tiling window."""

    RESOLVED = "resolved"
    MISSING_OR_AMBIGUOUS_OXYGEN_BRIDGE = "missing-or-ambiguous-oxygen-bridge"
    DEGENERATE_OXYGEN_POLYGON = "degenerate-oxygen-polygon"
    SOURCE_PATH_MISMATCH = "source-path-mismatch"


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
        raise RingGeometryInputError(f"{name} must be a SHA-256 digest.")
    return value


def _nonnegative(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise RingGeometryInputError(f"{name} must be a nonnegative integer.")
    return int(value)


def _positive(value: object, *, name: str) -> int:
    result = _nonnegative(value, name=name)
    if result == 0:
        raise RingGeometryInputError(f"{name} must be positive.")
    return result


def _finite(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise RingGeometryInputError(f"{name} must be finite.")
    return result


def _float3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = tuple(_finite(component, name=name) for component in value)
    if len(result) != 3:
        raise RingGeometryInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


def _unit3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = np.asarray(_float3(value, name=name), dtype=np.float64)
    norm = float(np.linalg.norm(result))
    if not math.isclose(norm, 1.0, rel_tol=1.0e-9, abs_tol=1.0e-9):
        raise RingGeometryInputError(f"{name} must have unit norm.")
    return tuple(float(component) for component in result)  # type: ignore[return-value]


def _points3(
    values: Sequence[Sequence[object]], *, name: str
) -> tuple[tuple[float, float, float], ...]:
    return tuple(_float3(value, name=name) for value in values)


def _frame_digest(collection: AtomisticFrameCollection, frame_index: int) -> str:
    """Hash scientific identity of the selected atomistic reference frame."""

    digest = hashlib.sha256()
    digest.update(b"mdstats.reference-ring-frame.v1\0")
    for array in (
        np.asarray(collection.atomic_numbers, dtype="<i4"),
        np.asarray(collection.pbc, dtype=np.uint8),
        np.asarray(collection.cells[frame_index], dtype="<f8"),
        np.asarray(collection.origins[frame_index], dtype="<f8"),
        np.asarray(collection.fractional_positions[frame_index], dtype="<f8"),
    ):
        digest.update(np.asarray(array.shape, dtype="<i8").tobytes())
        digest.update(np.ascontiguousarray(array).tobytes())
    digest.update(np.asarray([int(collection.frame_ids[frame_index])], dtype="<i8").tobytes())
    return digest.hexdigest()


@dataclass(frozen=True, order=True, slots=True)
class RingAtomRef:
    """One atom and integer image in the canonical ring-placement gauge."""

    atom_index: int
    image_shift: LatticeShift

    def __post_init__(self) -> None:
        object.__setattr__(self, "atom_index", _nonnegative(self.atom_index, name="atom_index"))
        try:
            shift = coerce_lattice_shift(self.image_shift, name="image_shift")
        except ValueError as exc:
            raise RingGeometryInputError(str(exc)) from exc
        object.__setattr__(self, "image_shift", shift)

    def to_dict(self) -> dict[str, Any]:
        return {"atom_index": self.atom_index, "image_shift": list(self.image_shift)}


@dataclass(frozen=True, slots=True)
class RingSideFrame:
    """Persistent local frame directed from a ring plane into one adjacent tile."""

    side: TileSideRef
    center: tuple[float, float, float]
    inward_unit_normal: tuple[float, float, float]
    axis_u: tuple[float, float, float]
    axis_v: tuple[float, float, float]

    def __post_init__(self) -> None:
        if not isinstance(self.side, TileSideRef):
            raise RingGeometryInputError("side must be a TileSideRef.")
        object.__setattr__(self, "center", _float3(self.center, name="center"))
        normal = np.asarray(_unit3(self.inward_unit_normal, name="inward_unit_normal"))
        axis_u = np.asarray(_unit3(self.axis_u, name="axis_u"))
        axis_v = np.asarray(_unit3(self.axis_v, name="axis_v"))
        if abs(float(np.dot(normal, axis_u))) > 1.0e-9:
            raise RingGeometryInputError("axis_u must be perpendicular to the side normal.")
        if abs(float(np.dot(normal, axis_v))) > 1.0e-9 or abs(float(np.dot(axis_u, axis_v))) > 1.0e-9:
            raise RingGeometryInputError("The local ring frame must be orthonormal.")
        if float(np.dot(np.cross(axis_u, axis_v), normal)) < 1.0 - 1.0e-9:
            raise RingGeometryInputError("The local ring frame must be right handed.")
        object.__setattr__(self, "inward_unit_normal", tuple(float(x) for x in normal))
        object.__setattr__(self, "axis_u", tuple(float(x) for x in axis_u))
        object.__setattr__(self, "axis_v", tuple(float(x) for x in axis_v))

    def to_dict(self) -> dict[str, Any]:
        return {
            "side": self.side.to_dict(),
            "center": list(self.center),
            "inward_unit_normal": list(self.inward_unit_normal),
            "axis_u": list(self.axis_u),
            "axis_v": list(self.axis_v),
        }


@dataclass(frozen=True, slots=True)
class ReferenceRingGeometry:
    """Source-bound T/O geometry of one natural-tiling window."""

    window_index: int
    face_index: int
    face_digest: str
    primitive_ring_id: int
    primitive_ring_digest: str
    ring_size: int
    status: RingGeometryStatus
    message: str
    t_atom_refs: tuple[RingAtomRef, ...] = ()
    o_atom_refs: tuple[RingAtomRef, ...] = ()
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

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_index", _nonnegative(self.window_index, name="window_index"))
        object.__setattr__(self, "face_index", _nonnegative(self.face_index, name="face_index"))
        _sha(self.face_digest, name="face_digest")
        object.__setattr__(self, "primitive_ring_id", _nonnegative(self.primitive_ring_id, name="primitive_ring_id"))
        _sha(self.primitive_ring_digest, name="primitive_ring_digest")
        object.__setattr__(self, "ring_size", _positive(self.ring_size, name="ring_size"))
        status = RingGeometryStatus(self.status)
        object.__setattr__(self, "status", status)
        if not isinstance(self.message, str):
            raise RingGeometryInputError("message must be a string.")
        t_refs = tuple(self.t_atom_refs)
        o_refs = tuple(self.o_atom_refs)
        t_frac = _points3(self.t_fractional_vertices, name="t_fractional_vertex")
        t_cart = _points3(self.t_cartesian_vertices, name="t_cartesian_vertex")
        o_frac = _points3(self.o_fractional_vertices, name="o_fractional_vertex")
        o_cart = _points3(self.o_cartesian_vertices, name="o_cartesian_vertex")
        sides = tuple(self.side_frames)
        if status is RingGeometryStatus.RESOLVED:
            if not (
                len(t_refs)
                == len(o_refs)
                == len(t_frac)
                == len(t_cart)
                == len(o_frac)
                == len(o_cart)
                == self.ring_size
            ):
                raise RingGeometryInputError("Resolved ring polygons must align with ring_size.")
            if len(sides) != 2:
                raise RingGeometryInputError("A resolved natural-tiling ring requires two side frames.")
            if any(not isinstance(value, RingAtomRef) for value in (*t_refs, *o_refs)):
                raise RingGeometryInputError("Ring atom references have the wrong type.")
            if any(not isinstance(value, RingSideFrame) for value in sides):
                raise RingGeometryInputError("side_frames have the wrong type.")
            required = (
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
            )
            if any(value is None for value in required):
                raise RingGeometryInputError("Resolved ring geometry is missing descriptors.")
            object.__setattr__(self, "oxygen_vertex_centroid", _float3(self.oxygen_vertex_centroid, name="oxygen_vertex_centroid"))  # type: ignore[arg-type]
            object.__setattr__(self, "oxygen_area_centroid", _float3(self.oxygen_area_centroid, name="oxygen_area_centroid"))  # type: ignore[arg-type]
            object.__setattr__(self, "oxygen_area_centroid_fractional", _float3(self.oxygen_area_centroid_fractional, name="oxygen_area_centroid_fractional"))  # type: ignore[arg-type]
            object.__setattr__(self, "ordered_unit_normal", _unit3(self.ordered_unit_normal, name="ordered_unit_normal"))  # type: ignore[arg-type]
            eigenvalues = tuple(_finite(value, name="covariance_eigenvalue") for value in self.covariance_eigenvalues)  # type: ignore[union-attr]
            if len(eigenvalues) != 3 or any(value < 0 for value in eigenvalues) or tuple(sorted(eigenvalues)) != eigenvalues:
                raise RingGeometryInputError("covariance_eigenvalues must be three sorted nonnegative values.")
            object.__setattr__(self, "covariance_eigenvalues", eigenvalues)
            for name in (
                "vector_area_magnitude",
                "projected_area",
                "perimeter",
                "planarity_rms",
                "planarity_max",
                "puckering_amplitude",
                "ellipticity",
                "center_aperture_radius",
            ):
                value = _finite(getattr(self, name), name=name)
                if value < 0 or (name in {"vector_area_magnitude", "projected_area", "perimeter", "ellipticity"} and value <= 0):
                    raise RingGeometryInputError(f"{name} has an invalid value.")
                object.__setattr__(self, name, value)
            if float(self.ellipticity) < 1.0 - 1.0e-9:
                raise RingGeometryInputError("ellipticity must be at least one.")
            t_o = tuple(_finite(value, name="t_o_distance") for value in self.t_o_distances)
            o_t = tuple(_finite(value, name="o_t_distance") for value in self.o_t_distances)
            if len(t_o) != self.ring_size or len(o_t) != self.ring_size or any(value <= 0 for value in (*t_o, *o_t)):
                raise RingGeometryInputError("Resolved T-O distance arrays must be positive and match ring_size.")
            object.__setattr__(self, "t_o_distances", t_o)
            object.__setattr__(self, "o_t_distances", o_t)
            if not np.allclose(
                np.asarray(sides[0].inward_unit_normal),
                -np.asarray(sides[1].inward_unit_normal),
                rtol=0.0,
                atol=1.0e-9,
            ):
                raise RingGeometryInputError("The two side normals must be opposite.")
        else:
            if any((t_refs, o_refs, t_frac, t_cart, o_frac, o_cart, sides)):
                raise RingGeometryInputError("Unresolved ring records cannot carry partial polygon geometry.")
        object.__setattr__(self, "t_atom_refs", t_refs)
        object.__setattr__(self, "o_atom_refs", o_refs)
        object.__setattr__(self, "t_fractional_vertices", t_frac)
        object.__setattr__(self, "t_cartesian_vertices", t_cart)
        object.__setattr__(self, "o_fractional_vertices", o_frac)
        object.__setattr__(self, "o_cartesian_vertices", o_cart)
        object.__setattr__(self, "side_frames", sides)

    @property
    def resolved(self) -> bool:
        return self.status is RingGeometryStatus.RESOLVED

    @property
    def geometric_center(self) -> tuple[float, float, float] | None:
        """Default purely geometric ring center: oxygen polygon area centroid."""

        return self.oxygen_area_centroid

    def to_dict(self) -> dict[str, Any]:
        def optional_vector(value: tuple[float, float, float] | None) -> list[float] | None:
            return None if value is None else list(value)

        return {
            "window_index": self.window_index,
            "face_index": self.face_index,
            "face_digest": self.face_digest,
            "primitive_ring_id": self.primitive_ring_id,
            "primitive_ring_digest": self.primitive_ring_digest,
            "ring_size": self.ring_size,
            "status": self.status.value,
            "message": self.message,
            "t_atom_refs": [value.to_dict() for value in self.t_atom_refs],
            "o_atom_refs": [value.to_dict() for value in self.o_atom_refs],
            "t_fractional_vertices": [list(value) for value in self.t_fractional_vertices],
            "t_cartesian_vertices": [list(value) for value in self.t_cartesian_vertices],
            "o_fractional_vertices": [list(value) for value in self.o_fractional_vertices],
            "o_cartesian_vertices": [list(value) for value in self.o_cartesian_vertices],
            "oxygen_vertex_centroid": optional_vector(self.oxygen_vertex_centroid),
            "oxygen_area_centroid": optional_vector(self.oxygen_area_centroid),
            "oxygen_area_centroid_fractional": optional_vector(self.oxygen_area_centroid_fractional),
            "ordered_unit_normal": optional_vector(self.ordered_unit_normal),
            "side_frames": [value.to_dict() for value in self.side_frames],
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
        }


@dataclass(frozen=True, slots=True)
class RingGeometryOptions:
    """Numerical and chemical resolution policy for Stage-11C1."""

    oxygen_atomic_number: int = 8
    degeneracy_tolerance: float = 1.0e-12
    path_closure_tolerance: float = 2.0e-8
    require_exact_source_connectivity: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "oxygen_atomic_number", _positive(self.oxygen_atomic_number, name="oxygen_atomic_number"))
        if not isinstance(self.require_exact_source_connectivity, bool):
            raise RingGeometryInputError("require_exact_source_connectivity must be boolean.")
        for name in ("degeneracy_tolerance", "path_closure_tolerance"):
            value = _finite(getattr(self, name), name=name)
            if value <= 0:
                raise RingGeometryInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "oxygen_atomic_number": self.oxygen_atomic_number,
            "degeneracy_tolerance": self.degeneracy_tolerance,
            "path_closure_tolerance": self.path_closure_tolerance,
            "require_exact_source_connectivity": self.require_exact_source_connectivity,
        }


@dataclass(frozen=True, slots=True)
class RingGeometryResources:
    """Transactional finite-work limits."""

    max_windows: int = 100_000
    max_ring_size: int = 256
    max_pair_distance_tests: int = 10_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}


@dataclass(frozen=True, slots=True, eq=False)
class ReferenceRingGeometryCatalog:
    """Persistent Stage-11C1 geometry catalog for all tiling windows."""

    tiling_geometry_digest: str
    periodic_cell_complex_digest: str
    primitive_ring_catalog_digest: str
    framework_topology_digest: str
    connectivity_state_digest: str
    source_connectivity_exact_match: bool
    framework_path_binding_digest: str
    reference_frame_digest: str
    frame_index: int
    frame_id: int
    options: RingGeometryOptions
    rings: tuple[ReferenceRingGeometry, ...]
    canonical_schema_version: str = CANONICAL_REFERENCE_RING_GEOMETRY_SCHEMA
    digest_algorithm: str = REFERENCE_RING_GEOMETRY_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "tiling_geometry_digest",
            "periodic_cell_complex_digest",
            "primitive_ring_catalog_digest",
            "framework_topology_digest",
            "connectivity_state_digest",
            "framework_path_binding_digest",
            "reference_frame_digest",
        ):
            _sha(getattr(self, name), name=name)
        if not isinstance(self.source_connectivity_exact_match, bool):
            raise RingGeometryInputError("source_connectivity_exact_match must be boolean.")
        object.__setattr__(self, "frame_index", _nonnegative(self.frame_index, name="frame_index"))
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, Integral):
            raise RingGeometryInputError("frame_id must be an integer.")
        object.__setattr__(self, "frame_id", int(self.frame_id))
        if not isinstance(self.options, RingGeometryOptions):
            raise RingGeometryInputError("options must be RingGeometryOptions.")
        rings = tuple(self.rings)
        if tuple(value.window_index for value in rings) != tuple(range(len(rings))):
            raise RingGeometryInputError("Ring geometry window IDs must be dense and ordered.")
        if self.canonical_schema_version != CANONICAL_REFERENCE_RING_GEOMETRY_SCHEMA:
            raise RingGeometryInputError("Unsupported reference-ring geometry schema.")
        if self.digest_algorithm != REFERENCE_RING_GEOMETRY_DIGEST_ALGORITHM:
            raise RingGeometryInputError("Unsupported reference-ring digest algorithm.")
        object.__setattr__(self, "rings", rings)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise RingGeometryInputError("Stored reference-ring geometry digest is inconsistent.")
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, ReferenceRingGeometryCatalog) and self.digest == other.digest

    @property
    def resolved_count(self) -> int:
        return sum(value.resolved for value in self.rings)

    @property
    def unresolved_count(self) -> int:
        return len(self.rings) - self.resolved_count

    def ring_for_window(self, window_index: int) -> ReferenceRingGeometry:
        index = _nonnegative(window_index, name="window_index")
        if index >= len(self.rings):
            raise RingGeometryInputError("window_index is outside this catalog.")
        return self.rings[index]

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "tiling_geometry_digest": self.tiling_geometry_digest,
            "periodic_cell_complex_digest": self.periodic_cell_complex_digest,
            "primitive_ring_catalog_digest": self.primitive_ring_catalog_digest,
            "framework_topology_digest": self.framework_topology_digest,
            "connectivity_state_digest": self.connectivity_state_digest,
            "source_connectivity_exact_match": self.source_connectivity_exact_match,
            "framework_path_binding_digest": self.framework_path_binding_digest,
            "reference_frame_digest": self.reference_frame_digest,
            "frame_index": self.frame_index,
            "frame_id": self.frame_id,
            "options": self.options.to_dict(),
            "rings": [value.to_dict() for value in self.rings],
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
        tiling_geometry: TilingGeometryCatalog,
        complex_: PeriodicCellComplex,
        ring_index: PrimitiveRingIndex,
        topology: FrameworkTopology,
        collection: AtomisticFrameCollection,
        connectivity: AtomicConnectivityResult,
    ) -> "ReferenceRingGeometryCatalog":
        try:
            options = RingGeometryOptions(**dict(payload["options"]))
            rebuilt = build_reference_ring_geometry_catalog(
                tiling_geometry,
                complex_,
                ring_index,
                topology,
                collection,
                connectivity,
                frame_index=int(payload["frame_index"]),
                options=options,
            )
            if rebuilt.to_dict() != dict(payload):
                raise RingGeometrySerializationError(
                    "Serialized reference-ring geometry is not canonical for the supplied sources."
                )
            return rebuilt
        except RingGeometryError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise RingGeometrySerializationError("Invalid reference-ring geometry payload.") from exc


def _oriented_ring_support(
    ring: PrimitiveRing,
    orientation: int,
) -> tuple[tuple[int, ...], tuple[PrimitiveRingStep, ...]]:
    if orientation == 1:
        return tuple(range(ring.size)), ring.steps
    vertex_indices = tuple(reversed(range(ring.size)))
    steps = tuple(
        ring.steps[(ring.size - 2 - index) % ring.size].reversed()
        for index in range(ring.size)
    )
    return vertex_indices, steps


def _raw_minimum_image_shift(
    wrapped_source: np.ndarray,
    wrapped_target: np.ndarray,
    *,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> np.ndarray:
    displacement = (wrapped_target - wrapped_source) @ cell
    _vector, _distance, shift = minimum_image_geometry(displacement, cell=cell, pbc=pbc)
    return np.asarray(shift, dtype=np.int64)


def _orientation_2d(first: np.ndarray, second: np.ndarray, third: np.ndarray) -> float:
    return float(
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def _point_on_segment_2d(
    point: np.ndarray, start: np.ndarray, end: np.ndarray, tolerance: float
) -> bool:
    if abs(_orientation_2d(start, end, point)) > tolerance:
        return False
    return bool(
        min(start[0], end[0]) - tolerance <= point[0] <= max(start[0], end[0]) + tolerance
        and min(start[1], end[1]) - tolerance <= point[1] <= max(start[1], end[1]) + tolerance
    )


def _segments_intersect_2d(
    first_start: np.ndarray,
    first_end: np.ndarray,
    second_start: np.ndarray,
    second_end: np.ndarray,
    tolerance: float,
) -> bool:
    orientations = (
        _orientation_2d(first_start, first_end, second_start),
        _orientation_2d(first_start, first_end, second_end),
        _orientation_2d(second_start, second_end, first_start),
        _orientation_2d(second_start, second_end, first_end),
    )
    if orientations[0] * orientations[1] < -tolerance * tolerance and orientations[2] * orientations[3] < -tolerance * tolerance:
        return True
    return any(
        abs(value) <= tolerance and _point_on_segment_2d(point, start, end, tolerance)
        for value, point, start, end in (
            (orientations[0], second_start, first_start, first_end),
            (orientations[1], second_end, first_start, first_end),
            (orientations[2], first_start, second_start, second_end),
            (orientations[3], first_end, second_start, second_end),
        )
    )


def _simple_polygon_2d(points: np.ndarray, tolerance: float) -> bool:
    count = len(points)
    for first in range(count):
        first_next = (first + 1) % count
        for second in range(first + 1, count):
            second_next = (second + 1) % count
            if first == second or first_next == second or second_next == first:
                continue
            if first == 0 and second_next == 0:
                continue
            if _segments_intersect_2d(
                points[first], points[first_next], points[second], points[second_next], tolerance
            ):
                return False
    return True


def _point_inside_polygon_2d(point: np.ndarray, polygon: np.ndarray, tolerance: float) -> bool:
    winding = 0
    for start, end in zip(polygon, np.roll(polygon, -1, axis=0), strict=True):
        if _point_on_segment_2d(point, start, end, tolerance):
            return True
        if start[1] <= point[1]:
            if end[1] > point[1] and _orientation_2d(start, end, point) > tolerance:
                winding += 1
        elif end[1] <= point[1] and _orientation_2d(start, end, point) < -tolerance:
            winding -= 1
    return winding != 0


def _point_segment_distance_2d(point: np.ndarray, start: np.ndarray, end: np.ndarray) -> float:
    direction = end - start
    denominator = float(np.dot(direction, direction))
    if denominator == 0.0:
        return float(np.linalg.norm(point - start))
    parameter = float(np.dot(point - start, direction) / denominator)
    parameter = min(1.0, max(0.0, parameter))
    return float(np.linalg.norm(point - (start + parameter * direction)))


def _polygon_geometry(
    points: np.ndarray,
    *,
    cell: np.ndarray,
    origin: np.ndarray,
    side_a: TileSideRef,
    side_b: TileSideRef,
    tolerance: float,
) -> dict[str, Any]:
    if points.ndim != 2 or points.shape[1] != 3 or points.shape[0] < 3:
        raise RingGeometryInvariantError("An oxygen ring requires at least three 3D points.")
    vertex_center = np.mean(points, axis=0)
    centered = points - vertex_center
    covariance = centered.T @ centered / points.shape[0]
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    normal = np.asarray(eigenvectors[:, 0], dtype=np.float64)
    vector_area = 0.5 * np.sum(
        np.cross(centered, np.roll(centered, -1, axis=0)), axis=0
    )
    vector_area_magnitude = float(np.linalg.norm(vector_area))
    if vector_area_magnitude <= tolerance:
        raise RingGeometryInvariantError("The ordered oxygen polygon has a degenerate vector area.")
    if float(np.dot(normal, vector_area)) < 0:
        normal = -normal
    normal /= np.linalg.norm(normal)

    axis_u = None
    for point in centered:
        candidate = point - float(np.dot(point, normal)) * normal
        norm = float(np.linalg.norm(candidate))
        if norm > tolerance:
            axis_u = candidate / norm
            break
    if axis_u is None:
        raise RingGeometryInvariantError("The oxygen polygon cannot define an in-plane axis.")
    axis_v = np.cross(normal, axis_u)
    axis_v /= np.linalg.norm(axis_v)
    projected = np.column_stack((centered @ axis_u, centered @ axis_v))
    if not _simple_polygon_2d(projected, tolerance):
        raise RingGeometryInvariantError(
            "The projected oxygen polygon is self-intersecting or has overlapping edges."
        )
    x = projected[:, 0]
    y = projected[:, 1]
    cross_terms = x * np.roll(y, -1) - np.roll(x, -1) * y
    signed_area = 0.5 * float(np.sum(cross_terms))
    if signed_area <= tolerance:
        raise RingGeometryInvariantError(
            "The ordered oxygen polygon has nonpositive or degenerate projected area."
        )
    centroid_x = float(np.sum((x + np.roll(x, -1)) * cross_terms) / (6.0 * signed_area))
    centroid_y = float(np.sum((y + np.roll(y, -1)) * cross_terms) / (6.0 * signed_area))
    area_center = vertex_center + centroid_x * axis_u + centroid_y * axis_v
    inverse_cell = np.linalg.inv(cell)
    area_center_fractional = (area_center - origin) @ inverse_cell
    signed_deviations = centered @ normal
    absolute_deviations = np.abs(signed_deviations)
    perimeter = sum(
        float(np.linalg.norm(points[(index + 1) % len(points)] - points[index]))
        for index in range(len(points))
    )
    area_center_2d = np.asarray([centroid_x, centroid_y], dtype=np.float64)
    if not _point_inside_polygon_2d(area_center_2d, projected, tolerance):
        raise RingGeometryInvariantError(
            "The projected oxygen area centroid lies outside the simple polygon."
        )
    centered_at_area = projected - area_center_2d
    aperture = min(
        _point_segment_distance_2d(
            np.zeros(2, dtype=np.float64),
            centered_at_area[index],
            centered_at_area[(index + 1) % len(points)],
        )
        for index in range(len(points))
    )
    if eigenvalues[1] <= tolerance:
        raise RingGeometryInvariantError("The oxygen polygon has a degenerate in-plane covariance.")
    ellipticity = math.sqrt(float(eigenvalues[2] / eigenvalues[1]))

    side_a_normal = -float(side_a.incidence_orientation) * normal
    side_b_normal = -float(side_b.incidence_orientation) * normal
    if float(np.dot(side_a_normal, side_b_normal)) > -1.0 + 1.0e-9:
        raise RingGeometryInvariantError("Natural-tiling side incidences do not produce opposite ring normals.")

    frames = []
    for side, side_normal in ((side_a, side_a_normal), (side_b, side_b_normal)):
        local_u = axis_u
        local_v = np.cross(side_normal, local_u)
        local_v /= np.linalg.norm(local_v)
        frames.append(
            RingSideFrame(
                side=side,
                center=tuple(float(value) for value in area_center),
                inward_unit_normal=tuple(float(value) for value in side_normal),
                axis_u=tuple(float(value) for value in local_u),
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
        "planarity_max": float(np.max(absolute_deviations)),
        "puckering_amplitude": float(np.max(signed_deviations) - np.min(signed_deviations)),
        "ellipticity": ellipticity,
        "center_aperture_radius": aperture,
    }


def _unresolved(
    *,
    window_index: int,
    face_index: int,
    face_digest: str,
    ring: PrimitiveRing,
    status: RingGeometryStatus,
    message: str,
) -> ReferenceRingGeometry:
    return ReferenceRingGeometry(
        window_index=window_index,
        face_index=face_index,
        face_digest=face_digest,
        primitive_ring_id=ring.ring_id,
        primitive_ring_digest=ring.digest,
        ring_size=ring.size,
        status=status,
        message=message,
    )


def _validate_framework_path_binding(
    topology: FrameworkTopology,
    state: AtomicConnectivityState,
) -> str:
    """Validate and hash the framework-relevant atomic path binding.

    Spectator-only connectivity is deliberately excluded: framework projection
    already declares those atoms irrelevant to the T/O ring identity.
    """

    state_numbers = {
        int(atom): int(number)
        for atom, number in zip(
            state.active_atom_indices, state.active_atomic_numbers, strict=True
        )
    }
    for atom, number, role in zip(
        topology.resolved_roles.active_atom_indices,
        topology.resolved_roles.active_atomic_numbers,
        topology.resolved_roles.roles,
        strict=True,
    ):
        if role.value not in {"vertex", "linker"}:
            continue
        if state_numbers.get(int(atom)) != int(number):
            raise RingGeometryInputError(
                "Selected connectivity state does not contain the required framework atoms."
            )

    state_edges = set(state.edge_keys)
    required: set[AtomicEdgeKey] = set()
    for path in topology.edges:
        for atom_i, atom_j, shift in zip(
            path.atomic_path_indices[:-1],
            path.atomic_path_indices[1:],
            path.atomic_edge_image_shifts,
            strict=True,
        ):
            edge = AtomicEdgeKey(int(atom_i), int(atom_j), tuple(int(x) for x in shift))
            required.add(edge)
            if edge not in state_edges:
                raise RingGeometryInputError(
                    "Selected connectivity state cannot replay every framework T-O-T path."
                )
    payload = [
        [edge.atom_i, edge.atom_j, *edge.image_shift]
        for edge in sorted(required)
    ]
    return _digest(payload)


def build_reference_ring_geometry_catalog(
    tiling_geometry: TilingGeometryCatalog,
    complex_: PeriodicCellComplex,
    ring_index: PrimitiveRingIndex,
    topology: FrameworkTopology,
    collection: AtomisticFrameCollection,
    connectivity: AtomicConnectivityResult,
    *,
    frame_index: int = 0,
    options: RingGeometryOptions | None = None,
    resources: RingGeometryResources | None = None,
) -> ReferenceRingGeometryCatalog:
    """Build persistent T/O ring geometry from one atomistic reference frame.

    Missing or ambiguous single-oxygen bridge paths are retained as explicit
    unresolved records.  Source-object mismatches fail transactionally before
    per-ring work begins.
    """

    if not isinstance(tiling_geometry, TilingGeometryCatalog):
        raise RingGeometryInputError("tiling_geometry must be a TilingGeometryCatalog.")
    if not isinstance(complex_, PeriodicCellComplex):
        raise RingGeometryInputError("complex_ must be a PeriodicCellComplex.")
    if not isinstance(ring_index, PrimitiveRingIndex):
        raise RingGeometryInputError("ring_index must be a PrimitiveRingIndex.")
    if not isinstance(topology, FrameworkTopology):
        raise RingGeometryInputError("topology must be a FrameworkTopology.")
    if not isinstance(collection, AtomisticFrameCollection):
        raise RingGeometryInputError("collection must be an AtomisticFrameCollection.")
    if not isinstance(connectivity, AtomicConnectivityResult):
        raise RingGeometryInputError("connectivity must be an AtomicConnectivityResult.")
    frame = _nonnegative(frame_index, name="frame_index")
    if frame >= collection.n_frames:
        raise RingGeometryInputError("frame_index exceeds the collection.")
    active_options = options or RingGeometryOptions()
    active_resources = resources or RingGeometryResources()
    if not isinstance(active_options, RingGeometryOptions):
        raise RingGeometryInputError("options must be RingGeometryOptions.")
    if not isinstance(active_resources, RingGeometryResources):
        raise RingGeometryInputError("resources must be RingGeometryResources.")

    if tiling_geometry.periodic_cell_complex_digest != complex_.digest:
        raise RingGeometryInputError("Tiling geometry and periodic cell complex disagree.")
    if tiling_geometry.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise RingGeometryInputError("Tiling geometry and primitive-ring index disagree.")
    if complex_.primitive_ring_catalog_digest != ring_index.catalog_digest:
        raise RingGeometryInputError("Cell complex and primitive-ring index disagree.")
    if complex_.topology_graph_digest != topology.graph_digest:
        raise RingGeometryInputError("Cell complex and framework topology graph disagree.")
    if ring_index.topology_graph_digest != topology.graph_digest:
        raise RingGeometryInputError("Primitive-ring index and framework topology graph disagree.")
    if tuple(bool(value) for value in collection.pbc) != tuple(bool(value) for value in topology.pbc):
        raise RingGeometryInputError("Collection and framework topology periodicity disagree.")
    if not bool(connectivity.metadata.get("unique_minimum_image_only", False)):
        raise RingGeometryInputError(
            "Reference ring geometry requires unique-minimum-image atomic connectivity."
        )
    if len(tiling_geometry.windows) > active_resources.max_windows:
        raise RingGeometryResourceError("Window count exceeds max_windows.")
    if any(window.ring_size > active_resources.max_ring_size for window in tiling_geometry.windows):
        raise RingGeometryResourceError("A ring exceeds max_ring_size.")
    pair_tests = sum(
        window.ring_size * 2 + window.ring_size * max(0, window.ring_size - 3) // 2
        for window in tiling_geometry.windows
    )
    if pair_tests > active_resources.max_pair_distance_tests:
        raise RingGeometryResourceError("Bridge geometry work exceeds max_pair_distance_tests.")

    state = connectivity.state_for_frame(frame)
    source_connectivity_exact_match = topology.source_connectivity_digest == state.digest
    if active_options.require_exact_source_connectivity and not source_connectivity_exact_match:
        raise RingGeometryInputError(
            "Framework topology was not built from the selected complete connectivity state."
        )
    framework_path_binding_digest = _validate_framework_path_binding(topology, state)
    if np.max(topology.resolved_roles.active_atom_indices) >= collection.n_atoms:
        raise RingGeometryInputError("Framework atom indices exceed the collection size.")
    active_numbers = np.asarray(collection.atomic_numbers, dtype=np.int32)
    for atom, number in zip(
        topology.resolved_roles.active_atom_indices,
        topology.resolved_roles.active_atomic_numbers,
        strict=True,
    ):
        if int(active_numbers[int(atom)]) != int(number):
            raise RingGeometryInputError("Collection atomic numbers disagree with framework topology.")

    canonical_vertices, _global_shift, _gauges = _canonical_vertex_coordinates(
        collection, frame, state, topology
    )
    wrapped = np.asarray(collection.get_wrapped_fractional_positions(frame), dtype=np.float64)
    cell = np.asarray(collection.cells[frame], dtype=np.float64)
    origin = np.asarray(collection.origins[frame], dtype=np.float64)
    pbc = np.asarray(collection.pbc, dtype=bool)

    records: list[ReferenceRingGeometry] = []
    for window in tiling_geometry.windows:
        face = complex_.face_placements[window.face_index]
        ring = ring_index.ring_for_key(face.ring_placement.ring_key)
        if ring.size != window.ring_size:
            raise RingGeometryInvariantError("Window ring size disagrees with primitive-ring source.")
        vertex_order, oriented_steps = _oriented_ring_support(ring, face.orientation)
        base_shift = add_shift(face.ring_placement.image_shift, window.side_a.face_image_shift)
        t_refs = tuple(
            RingAtomRef(
                ring.vertex_walk[index].atom_index,
                add_shift(ring.vertex_walk[index].image_shift, base_shift),
            )
            for index in vertex_order
        )
        t_fractional = np.asarray(
            [
                canonical_vertices[ref.atom_index]
                + np.asarray(ref.image_shift, dtype=np.float64)
                for ref in t_refs
            ],
            dtype=np.float64,
        )
        t_cartesian = t_fractional @ cell + origin

        oxygen_refs: list[RingAtomRef] = []
        oxygen_fractional: list[np.ndarray] = []
        t_o_distances: list[float] = []
        o_t_distances: list[float] = []
        unresolved: ReferenceRingGeometry | None = None
        for edge_position, step in enumerate(oriented_steps):
            source_ref = t_refs[edge_position]
            target_ref = t_refs[(edge_position + 1) % ring.size]
            if step.edge_index >= len(topology.edges):
                unresolved = _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.SOURCE_PATH_MISMATCH,
                    message="Primitive-ring step references an absent framework edge.",
                )
                break
            path = topology.edges[step.edge_index].oriented(step.orientation)
            if path.source_vertex != source_ref.atom_index or path.target_vertex != target_ref.atom_index:
                unresolved = _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.SOURCE_PATH_MISMATCH,
                    message="Oriented framework edge endpoints disagree with the ring walk.",
                )
                break
            if (
                len(path.internal_linker_indices) != 1
                or len(path.atomic_path_indices) != 3
                or path.internal_linker_atomic_numbers != (active_options.oxygen_atomic_number,)
            ):
                unresolved = _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.MISSING_OR_AMBIGUOUS_OXYGEN_BRIDGE,
                    message="Each T-T ring edge must resolve to exactly one bridging oxygen.",
                )
                break
            oxygen_atom = path.internal_linker_indices[0]
            if int(active_numbers[oxygen_atom]) != active_options.oxygen_atomic_number:
                unresolved = _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.MISSING_OR_AMBIGUOUS_OXYGEN_BRIDGE,
                    message="Resolved bridge atom does not have the configured oxygen atomic number.",
                )
                break
            source_gauge_float = t_fractional[edge_position] - wrapped[source_ref.atom_index]
            source_gauge = np.rint(source_gauge_float).astype(np.int64)
            if not np.allclose(source_gauge_float, source_gauge, rtol=0.0, atol=active_options.path_closure_tolerance):
                unresolved = _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.SOURCE_PATH_MISMATCH,
                    message="Lifted T coordinate does not differ from its wrapped atom by an integer image.",
                )
                break
            source_to_oxygen = _raw_minimum_image_shift(
                wrapped[source_ref.atom_index],
                wrapped[oxygen_atom],
                cell=cell,
                pbc=pbc,
            )
            oxygen_gauge = source_gauge + source_to_oxygen
            oxygen_frac = wrapped[oxygen_atom] + oxygen_gauge
            oxygen_to_target = _raw_minimum_image_shift(
                wrapped[oxygen_atom],
                wrapped[target_ref.atom_index],
                cell=cell,
                pbc=pbc,
            )
            replayed_target = oxygen_frac + (
                wrapped[target_ref.atom_index] - wrapped[oxygen_atom] + oxygen_to_target
            )
            target_fractional = t_fractional[(edge_position + 1) % ring.size]
            if not np.allclose(
                replayed_target,
                target_fractional,
                rtol=0.0,
                atol=active_options.path_closure_tolerance,
            ):
                unresolved = _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.SOURCE_PATH_MISMATCH,
                    message="The atomistic T-O-T bridge does not close onto the lifted ring edge.",
                )
                break
            oxygen_refs.append(
                RingAtomRef(
                    oxygen_atom,
                    tuple(int(value) for value in oxygen_gauge),  # type: ignore[arg-type]
                )
            )
            oxygen_fractional.append(oxygen_frac)
            oxygen_cart = oxygen_frac @ cell + origin
            t_o_distances.append(float(np.linalg.norm(oxygen_cart - t_cartesian[edge_position])))
            o_t_distances.append(
                float(
                    np.linalg.norm(
                        t_cartesian[(edge_position + 1) % ring.size] - oxygen_cart
                    )
                )
            )

        if unresolved is not None:
            records.append(unresolved)
            continue
        oxygen_fractional_array = np.asarray(oxygen_fractional, dtype=np.float64)
        oxygen_cartesian = oxygen_fractional_array @ cell + origin
        try:
            descriptors = _polygon_geometry(
                oxygen_cartesian,
                cell=cell,
                origin=origin,
                side_a=window.side_a,
                side_b=window.side_b,
                tolerance=active_options.degeneracy_tolerance,
            )
        except RingGeometryInvariantError as exc:
            records.append(
                _unresolved(
                    window_index=window.window_index,
                    face_index=window.face_index,
                    face_digest=window.face_digest,
                    ring=ring,
                    status=RingGeometryStatus.DEGENERATE_OXYGEN_POLYGON,
                    message=str(exc),
                )
            )
            continue
        records.append(
            ReferenceRingGeometry(
                window_index=window.window_index,
                face_index=window.face_index,
                face_digest=window.face_digest,
                primitive_ring_id=ring.ring_id,
                primitive_ring_digest=ring.digest,
                ring_size=ring.size,
                status=RingGeometryStatus.RESOLVED,
                message="",
                t_atom_refs=t_refs,
                o_atom_refs=tuple(oxygen_refs),
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
            )
        )

    return ReferenceRingGeometryCatalog(
        tiling_geometry_digest=tiling_geometry.digest,
        periodic_cell_complex_digest=complex_.digest,
        primitive_ring_catalog_digest=ring_index.catalog_digest,
        framework_topology_digest=topology.digest,
        connectivity_state_digest=state.digest,
        source_connectivity_exact_match=source_connectivity_exact_match,
        framework_path_binding_digest=framework_path_binding_digest,
        reference_frame_digest=_frame_digest(collection, frame),
        frame_index=frame,
        frame_id=int(collection.frame_ids[frame]),
        options=active_options,
        rings=tuple(records),
    )


__all__ = [
    "CANONICAL_REFERENCE_RING_GEOMETRY_SCHEMA",
    "REFERENCE_RING_GEOMETRY_DIGEST_ALGORITHM",
    "ReferenceRingGeometry",
    "ReferenceRingGeometryCatalog",
    "RingAtomRef",
    "RingGeometryError",
    "RingGeometryInputError",
    "RingGeometryInvariantError",
    "RingGeometryOptions",
    "RingGeometryResourceError",
    "RingGeometryResources",
    "RingGeometrySerializationError",
    "RingGeometryStatus",
    "RingSideFrame",
    "build_reference_ring_geometry_catalog",
]
