"""Stage-C0A3 registered structural geometry integration.

Physical ring and tiling geometry remains authoritative for bond lengths,
apertures, areas, and volumes.  This module applies one resolved Stage-C0A2
affine registration to persistent structural identities and reconstructs local
orthonormal registered frames from transformed atoms.  It never promotes an
affinely transformed physical frame axis into a registered orthonormal frame.
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
from mdstats.coordinates.registration import FrameRegistrationResult
from mdstats.semantics import FrameSemantics

from .ring_boundary import (
    RingBoundaryStatus,
    StructuralRingBoundary,
    StructuralRingBoundaryCatalog,
)
from .ring_geometry import RingAtomRef
from .ring_geometry_frames import (
    FrameRingGeometry,
    FrameRingGeometryCatalog,
    FrameRingGeometryStatus,
)
from .tiling_geometry_frames import (
    FrameTilingGeometryCatalog,
    FrameTilingGeometryStatus,
    MappedTilingFrame,
)

CANONICAL_REGISTERED_STRUCTURAL_VIEW_SCHEMA = (
    "mdstats.registered-structural-geometry-view.v1"
)
REGISTERED_STRUCTURAL_VIEW_DIGEST_ALGORITHM = "sha256-canonical-json-v1"
REGISTERED_RING_FRAME_METHOD = "transformed-atoms-best-fit-plane-v1"


class RegisteredStructuralViewError(ValueError):
    """Base exception for Stage-C0A3 structural registration."""


class RegisteredStructuralViewInputError(RegisteredStructuralViewError):
    """Raised when options, records, or source types are invalid."""


class RegisteredStructuralViewSourceError(RegisteredStructuralViewError):
    """Raised when upstream source bindings cannot be reconciled."""


class RegisteredStructuralViewInvariantError(RegisteredStructuralViewError):
    """Raised when transformed geometry violates a scientific invariant."""


class RegisteredStructuralViewResourceError(RegisteredStructuralViewError):
    """Raised before a declared finite-work limit is exceeded."""


class RegisteredStructuralViewSerializationError(RegisteredStructuralViewError):
    """Raised when serialized output is not canonical for supplied sources."""


class RegisteredRingViewStatus(str, Enum):
    RESOLVED = "resolved"
    PHYSICAL_RING_UNRESOLVED = "physical-ring-unresolved"
    BOUNDARY_UNRESOLVED = "boundary-unresolved"
    IDENTITY_MISMATCH = "identity-mismatch"
    REGISTERED_GEOMETRY_DEGENERATE = "registered-geometry-degenerate"
    ORIENTATION_DISCONTINUITY = "orientation-discontinuity"


class RegisteredStructuralFrameStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
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


def _array_digest(value: object) -> str:
    array = np.ascontiguousarray(np.asarray(value))
    hasher = hashlib.sha256()
    hasher.update(array.dtype.str.encode("ascii"))
    hasher.update(str(array.shape).encode("ascii"))
    hasher.update(array.tobytes(order="C"))
    return hasher.hexdigest()


def _sha(value: object, *, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise RegisteredStructuralViewInputError(f"{name} must be a SHA-256 digest.")
    return value


def _positive_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise RegisteredStructuralViewInputError(f"{name} must be a positive integer.")
    return int(value)


def _nonnegative_int(value: object, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) < 0:
        raise RegisteredStructuralViewInputError(f"{name} must be nonnegative.")
    return int(value)


def _finite(value: object, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise RegisteredStructuralViewInputError(f"{name} must be finite.")
    return result


def _float3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    result = tuple(_finite(item, name=name) for item in value)
    if len(result) != 3:
        raise RegisteredStructuralViewInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


def _int3(value: Sequence[object], *, name: str) -> tuple[int, int, int]:
    result = tuple(int(item) for item in value)
    if len(result) != 3:
        raise RegisteredStructuralViewInputError(f"{name} must contain three values.")
    return result  # type: ignore[return-value]


def _points3(
    values: Sequence[Sequence[object]], *, name: str
) -> tuple[tuple[float, float, float], ...]:
    return tuple(_float3(value, name=name) for value in values)


def _unit3(value: Sequence[object], *, name: str) -> tuple[float, float, float]:
    array = np.asarray(_float3(value, name=name), dtype=np.float64)
    norm = float(np.linalg.norm(array))
    if norm <= np.finfo(float).tiny:
        raise RegisteredStructuralViewInputError(f"{name} must be nonzero.")
    if not math.isclose(norm, 1.0, rel_tol=1.0e-9, abs_tol=1.0e-9):
        raise RegisteredStructuralViewInputError(f"{name} must be unit length.")
    return tuple(float(item) for item in array)  # type: ignore[return-value]


def _collection_binding_digest(collection: AtomisticFrameCollection) -> str:
    payload = {
        "frame_semantics": collection.frame_semantics.value,
        "frame_ids": _array_digest(collection.frame_ids),
        "atomic_numbers": _array_digest(collection.atomic_numbers),
        "pbc": _array_digest(collection.pbc),
        "cells": _array_digest(collection.cells),
        "origins": _array_digest(collection.origins),
        "fractional_positions": _array_digest(collection.fractional_positions),
    }
    return _digest(payload)


@dataclass(frozen=True, slots=True)
class RegisteredStructuralViewOptions:
    coordinate_tolerance: float = 1.0e-8
    degeneracy_tolerance: float = 1.0e-10
    orthonormality_tolerance: float = 1.0e-9
    minimum_orientation_continuity_dot: float = 0.0
    enforce_trajectory_orientation_continuity: bool = True

    def __post_init__(self) -> None:
        for name in (
            "coordinate_tolerance",
            "degeneracy_tolerance",
            "orthonormality_tolerance",
        ):
            value = _finite(getattr(self, name), name=name)
            if value <= 0.0:
                raise RegisteredStructuralViewInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        dot = _finite(
            self.minimum_orientation_continuity_dot,
            name="minimum_orientation_continuity_dot",
        )
        if dot < -1.0 or dot > 1.0:
            raise RegisteredStructuralViewInputError(
                "minimum_orientation_continuity_dot must lie in [-1, 1]."
            )
        object.__setattr__(self, "minimum_orientation_continuity_dot", dot)
        if not isinstance(self.enforce_trajectory_orientation_continuity, bool):
            raise RegisteredStructuralViewInputError(
                "enforce_trajectory_orientation_continuity must be boolean."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "coordinate_tolerance": self.coordinate_tolerance,
            "degeneracy_tolerance": self.degeneracy_tolerance,
            "orthonormality_tolerance": self.orthonormality_tolerance,
            "minimum_orientation_continuity_dot": self.minimum_orientation_continuity_dot,
            "enforce_trajectory_orientation_continuity": self.enforce_trajectory_orientation_continuity,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RegisteredStructuralViewOptions":
        return cls(
            coordinate_tolerance=float(payload["coordinate_tolerance"]),
            degeneracy_tolerance=float(payload["degeneracy_tolerance"]),
            orthonormality_tolerance=float(payload["orthonormality_tolerance"]),
            minimum_orientation_continuity_dot=float(
                payload["minimum_orientation_continuity_dot"]
            ),
            enforce_trajectory_orientation_continuity=bool(
                payload["enforce_trajectory_orientation_continuity"]
            ),
        )


@dataclass(frozen=True, slots=True)
class RegisteredStructuralViewResources:
    max_frames: int = 100_000
    max_ring_instances: int = 10_000_000
    max_linked_atom_instances: int = 200_000_000
    max_tile_instances: int = 10_000_000
    max_tile_face_vertex_instances: int = 200_000_000
    max_window_instances: int = 20_000_000

    def __post_init__(self) -> None:
        for name in self.__dataclass_fields__:
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name))

    def to_dict(self) -> dict[str, int]:
        return {name: int(getattr(self, name)) for name in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RegisteredStructuralViewResources":
        return cls(**{name: int(payload[name]) for name in cls.__dataclass_fields__})


@dataclass(frozen=True, slots=True)
class LinkedStructuralAtomEmbedding:
    boundary_kind: str
    cyclic_index: int
    atom_ref: RingAtomRef
    atomic_number: int
    element: str
    oxygen_environment_signature: str | None
    crystallographic_alias: str | None
    physical_cartesian: tuple[float, float, float]
    registered_cartesian: tuple[float, float, float]
    registered_fractional_unwrapped: tuple[float, float, float]
    registered_fractional_wrapped: tuple[float, float, float]
    registered_image_shift: tuple[int, int, int]
    periodic_image_residual: float

    def __post_init__(self) -> None:
        if self.boundary_kind not in {"T", "O"}:
            raise RegisteredStructuralViewInputError("boundary_kind must be T or O.")
        object.__setattr__(
            self, "cyclic_index", _nonnegative_int(self.cyclic_index, name="cyclic_index")
        )
        if not isinstance(self.atom_ref, RingAtomRef):
            raise RegisteredStructuralViewInputError("atom_ref must be RingAtomRef.")
        object.__setattr__(
            self, "atomic_number", _positive_int(self.atomic_number, name="atomic_number")
        )
        if not isinstance(self.element, str) or not self.element:
            raise RegisteredStructuralViewInputError("element must be nonempty.")
        for name in (
            "physical_cartesian",
            "registered_cartesian",
            "registered_fractional_unwrapped",
            "registered_fractional_wrapped",
        ):
            object.__setattr__(self, name, _float3(getattr(self, name), name=name))
        object.__setattr__(
            self,
            "registered_image_shift",
            _int3(self.registered_image_shift, name="registered_image_shift"),
        )
        residual = _finite(self.periodic_image_residual, name="periodic_image_residual")
        if residual < 0.0:
            raise RegisteredStructuralViewInputError(
                "periodic_image_residual must be nonnegative."
            )
        object.__setattr__(self, "periodic_image_residual", residual)

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_kind": self.boundary_kind,
            "cyclic_index": self.cyclic_index,
            "atom_ref": self.atom_ref.to_dict(),
            "atomic_number": self.atomic_number,
            "element": self.element,
            "oxygen_environment_signature": self.oxygen_environment_signature,
            "crystallographic_alias": self.crystallographic_alias,
            "physical_cartesian": list(self.physical_cartesian),
            "registered_cartesian": list(self.registered_cartesian),
            "registered_fractional_unwrapped": list(
                self.registered_fractional_unwrapped
            ),
            "registered_fractional_wrapped": list(self.registered_fractional_wrapped),
            "registered_image_shift": list(self.registered_image_shift),
            "periodic_image_residual": self.periodic_image_residual,
        }


@dataclass(frozen=True, slots=True)
class PhysicalRingGeometrySnapshot:
    center: tuple[float, float, float]
    axis_u: tuple[float, float, float]
    axis_v: tuple[float, float, float]
    ordered_unit_normal: tuple[float, float, float]
    t_cartesian_vertices: tuple[tuple[float, float, float], ...]
    o_cartesian_vertices: tuple[tuple[float, float, float], ...]
    projected_area: float
    perimeter: float
    center_aperture_radius: float
    planarity_rms: float
    planarity_max: float
    t_o_distances: tuple[float, ...]
    o_t_distances: tuple[float, ...]

    def __post_init__(self) -> None:
        for name in ("center", "axis_u", "axis_v", "ordered_unit_normal"):
            value = _unit3(getattr(self, name), name=name) if name != "center" else _float3(getattr(self, name), name=name)
            object.__setattr__(self, name, value)
        t_points = _points3(self.t_cartesian_vertices, name="t_cartesian_vertex")
        o_points = _points3(self.o_cartesian_vertices, name="o_cartesian_vertex")
        if not t_points or len(t_points) != len(o_points):
            raise RegisteredStructuralViewInputError(
                "Physical T/O vertex arrays must be nonempty and aligned."
            )
        object.__setattr__(self, "t_cartesian_vertices", t_points)
        object.__setattr__(self, "o_cartesian_vertices", o_points)
        for name in (
            "projected_area",
            "perimeter",
            "center_aperture_radius",
            "planarity_rms",
            "planarity_max",
        ):
            value = _finite(getattr(self, name), name=name)
            if value < 0.0 or (name in {"projected_area", "perimeter"} and value <= 0.0):
                raise RegisteredStructuralViewInputError(f"{name} has an invalid value.")
            object.__setattr__(self, name, value)
        for name in ("t_o_distances", "o_t_distances"):
            values = tuple(_finite(value, name=name) for value in getattr(self, name))
            if len(values) != len(t_points) or any(value <= 0.0 for value in values):
                raise RegisteredStructuralViewInputError(
                    f"{name} must be positive and match ring size."
                )
            object.__setattr__(self, name, values)

    def to_dict(self) -> dict[str, Any]:
        return {
            "center": list(self.center),
            "axis_u": list(self.axis_u),
            "axis_v": list(self.axis_v),
            "ordered_unit_normal": list(self.ordered_unit_normal),
            "t_cartesian_vertices": [list(value) for value in self.t_cartesian_vertices],
            "o_cartesian_vertices": [list(value) for value in self.o_cartesian_vertices],
            "projected_area": self.projected_area,
            "perimeter": self.perimeter,
            "center_aperture_radius": self.center_aperture_radius,
            "planarity_rms": self.planarity_rms,
            "planarity_max": self.planarity_max,
            "t_o_distances": list(self.t_o_distances),
            "o_t_distances": list(self.o_t_distances),
        }


@dataclass(frozen=True, slots=True)
class RegisteredOrthonormalRingFrame:
    method: str
    center: tuple[float, float, float]
    axis_u: tuple[float, float, float]
    axis_v: tuple[float, float, float]
    ordered_unit_normal: tuple[float, float, float]
    covariance_eigenvalues: tuple[float, float, float]
    projected_area: float
    perimeter: float
    projected_aperture_radius: float
    planarity_rms: float
    planarity_max: float
    minimum_projected_atom_radius: float
    orthonormality_error: float
    transformed_physical_axes_orthogonality_error: float
    transformed_center_reconstruction_error: float
    normal_continuity_dot: float | None
    axis_u_continuity_dot: float | None

    def __post_init__(self) -> None:
        if self.method != REGISTERED_RING_FRAME_METHOD:
            raise RegisteredStructuralViewInputError(
                "Unsupported registered ring-frame reconstruction method."
            )
        object.__setattr__(self, "center", _float3(self.center, name="center"))
        for name in ("axis_u", "axis_v", "ordered_unit_normal"):
            object.__setattr__(self, name, _unit3(getattr(self, name), name=name))
        eigen = tuple(_finite(value, name="covariance_eigenvalue") for value in self.covariance_eigenvalues)
        if len(eigen) != 3 or tuple(sorted(eigen)) != eigen or any(value < 0.0 for value in eigen):
            raise RegisteredStructuralViewInputError(
                "covariance_eigenvalues must be three sorted nonnegative values."
            )
        object.__setattr__(self, "covariance_eigenvalues", eigen)
        for name in (
            "projected_area",
            "perimeter",
            "projected_aperture_radius",
            "planarity_rms",
            "planarity_max",
            "minimum_projected_atom_radius",
            "orthonormality_error",
            "transformed_physical_axes_orthogonality_error",
            "transformed_center_reconstruction_error",
        ):
            value = _finite(getattr(self, name), name=name)
            if value < 0.0 or (name in {"projected_area", "perimeter"} and value <= 0.0):
                raise RegisteredStructuralViewInputError(f"{name} has an invalid value.")
            object.__setattr__(self, name, value)
        for name in ("normal_continuity_dot", "axis_u_continuity_dot"):
            value = getattr(self, name)
            if value is not None:
                scalar = _finite(value, name=name)
                if scalar < -1.0 - 1.0e-9 or scalar > 1.0 + 1.0e-9:
                    raise RegisteredStructuralViewInputError(f"{name} lies outside [-1, 1].")
                object.__setattr__(self, name, float(np.clip(scalar, -1.0, 1.0)))

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "center": list(self.center),
            "axis_u": list(self.axis_u),
            "axis_v": list(self.axis_v),
            "ordered_unit_normal": list(self.ordered_unit_normal),
            "covariance_eigenvalues": list(self.covariance_eigenvalues),
            "projected_area": self.projected_area,
            "perimeter": self.perimeter,
            "projected_aperture_radius": self.projected_aperture_radius,
            "planarity_rms": self.planarity_rms,
            "planarity_max": self.planarity_max,
            "minimum_projected_atom_radius": self.minimum_projected_atom_radius,
            "orthonormality_error": self.orthonormality_error,
            "transformed_physical_axes_orthogonality_error": self.transformed_physical_axes_orthogonality_error,
            "transformed_center_reconstruction_error": self.transformed_center_reconstruction_error,
            "normal_continuity_dot": self.normal_continuity_dot,
            "axis_u_continuity_dot": self.axis_u_continuity_dot,
        }


@dataclass(frozen=True, slots=True)
class RegisteredRingEmbedding:
    center_fractional_unwrapped: tuple[float, float, float]
    center_fractional_wrapped: tuple[float, float, float]
    center_image_shift: tuple[int, int, int]
    t_atoms: tuple[LinkedStructuralAtomEmbedding, ...]
    o_atoms: tuple[LinkedStructuralAtomEmbedding, ...]
    frame: RegisteredOrthonormalRingFrame

    def __post_init__(self) -> None:
        for name in ("center_fractional_unwrapped", "center_fractional_wrapped"):
            object.__setattr__(self, name, _float3(getattr(self, name), name=name))
        object.__setattr__(
            self, "center_image_shift", _int3(self.center_image_shift, name="center_image_shift")
        )
        t_atoms = tuple(self.t_atoms)
        o_atoms = tuple(self.o_atoms)
        if not t_atoms or len(t_atoms) != len(o_atoms):
            raise RegisteredStructuralViewInputError(
                "Registered T/O atom embeddings must be nonempty and aligned."
            )
        if any(atom.boundary_kind != "T" for atom in t_atoms) or any(
            atom.boundary_kind != "O" for atom in o_atoms
        ):
            raise RegisteredStructuralViewInputError(
                "Registered T/O atom embeddings use the wrong boundary kind."
            )
        if not isinstance(self.frame, RegisteredOrthonormalRingFrame):
            raise RegisteredStructuralViewInputError(
                "frame must be RegisteredOrthonormalRingFrame."
            )
        object.__setattr__(self, "t_atoms", t_atoms)
        object.__setattr__(self, "o_atoms", o_atoms)

    def to_dict(self) -> dict[str, Any]:
        return {
            "center_fractional_unwrapped": list(self.center_fractional_unwrapped),
            "center_fractional_wrapped": list(self.center_fractional_wrapped),
            "center_image_shift": list(self.center_image_shift),
            "t_atoms": [value.to_dict() for value in self.t_atoms],
            "o_atoms": [value.to_dict() for value in self.o_atoms],
            "frame": self.frame.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RegisteredRingStructuralView:
    window_index: int
    face_index: int
    primitive_ring_id: int
    ring_size: int
    status: RegisteredRingViewStatus
    message: str
    physical: PhysicalRingGeometrySnapshot | None
    registered: RegisteredRingEmbedding | None

    def __post_init__(self) -> None:
        for name in ("window_index", "face_index", "primitive_ring_id"):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        object.__setattr__(self, "ring_size", _positive_int(self.ring_size, name="ring_size"))
        object.__setattr__(self, "status", RegisteredRingViewStatus(self.status))
        if not isinstance(self.message, str):
            raise RegisteredStructuralViewInputError("message must be a string.")
        if self.status is RegisteredRingViewStatus.RESOLVED:
            if self.physical is None or self.registered is None:
                raise RegisteredStructuralViewInputError(
                    "Resolved ring views require physical and registered records."
                )
            if len(self.registered.t_atoms) != self.ring_size:
                raise RegisteredStructuralViewInputError(
                    "Resolved registered ring atom count disagrees with ring_size."
                )
        elif self.registered is not None:
            raise RegisteredStructuralViewInputError(
                "Unresolved ring views cannot carry partial registered geometry."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "face_index": self.face_index,
            "primitive_ring_id": self.primitive_ring_id,
            "ring_size": self.ring_size,
            "status": self.status.value,
            "message": self.message,
            "physical": None if self.physical is None else self.physical.to_dict(),
            "registered": None if self.registered is None else self.registered.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class RegisteredTileCageEmbedding:
    tile_index: int
    physical_center: tuple[float, float, float]
    registered_center: tuple[float, float, float]
    registered_fractional_unwrapped: tuple[float, float, float]
    registered_fractional_wrapped: tuple[float, float, float]
    registered_image_shift: tuple[int, int, int]
    physical_volume: float
    physical_surface_area: float
    physical_equivalent_sphere_radius: float
    physical_sphericity: float
    physical_diameter: float
    physical_orientation_preserved: bool
    structural_role: str = "natural_tile_cage"

    def __post_init__(self) -> None:
        object.__setattr__(self, "tile_index", _nonnegative_int(self.tile_index, name="tile_index"))
        if self.structural_role != "natural_tile_cage":
            raise RegisteredStructuralViewInputError("Unsupported tile/cage structural role.")
        for name in (
            "physical_center",
            "registered_center",
            "registered_fractional_unwrapped",
            "registered_fractional_wrapped",
        ):
            object.__setattr__(self, name, _float3(getattr(self, name), name=name))
        object.__setattr__(
            self, "registered_image_shift", _int3(self.registered_image_shift, name="registered_image_shift")
        )
        for name in (
            "physical_volume",
            "physical_surface_area",
            "physical_equivalent_sphere_radius",
            "physical_sphericity",
            "physical_diameter",
        ):
            value = _finite(getattr(self, name), name=name)
            if value <= 0.0:
                raise RegisteredStructuralViewInputError(f"{name} must be positive.")
            object.__setattr__(self, name, value)
        if not isinstance(self.physical_orientation_preserved, bool):
            raise RegisteredStructuralViewInputError(
                "physical_orientation_preserved must be boolean."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tile_index": self.tile_index,
            "structural_role": self.structural_role,
            "physical_center": list(self.physical_center),
            "registered_center": list(self.registered_center),
            "registered_fractional_unwrapped": list(self.registered_fractional_unwrapped),
            "registered_fractional_wrapped": list(self.registered_fractional_wrapped),
            "registered_image_shift": list(self.registered_image_shift),
            "physical_volume": self.physical_volume,
            "physical_surface_area": self.physical_surface_area,
            "physical_equivalent_sphere_radius": self.physical_equivalent_sphere_radius,
            "physical_sphericity": self.physical_sphericity,
            "physical_diameter": self.physical_diameter,
            "physical_orientation_preserved": self.physical_orientation_preserved,
        }


@dataclass(frozen=True, slots=True)
class RegisteredTileFaceEmbedding:
    side_index: int
    physical_vertices: tuple[tuple[float, float, float], ...]
    registered_vertices: tuple[tuple[float, float, float], ...]
    physical_center: tuple[float, float, float]
    registered_center: tuple[float, float, float]
    registered_unit_normal: tuple[float, float, float]
    physical_area: float
    physical_perimeter: float
    physical_projected_aperture_radius: float
    physical_planarity_rms: float
    physical_planarity_max: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "side_index", _nonnegative_int(self.side_index, name="side_index"))
        physical = _points3(self.physical_vertices, name="physical_vertex")
        registered = _points3(self.registered_vertices, name="registered_vertex")
        if len(physical) < 3 or len(physical) != len(registered):
            raise RegisteredStructuralViewInputError(
                "Tile-face physical and registered vertices must align."
            )
        object.__setattr__(self, "physical_vertices", physical)
        object.__setattr__(self, "registered_vertices", registered)
        object.__setattr__(self, "physical_center", _float3(self.physical_center, name="physical_center"))
        object.__setattr__(self, "registered_center", _float3(self.registered_center, name="registered_center"))
        object.__setattr__(self, "registered_unit_normal", _unit3(self.registered_unit_normal, name="registered_unit_normal"))
        for name in (
            "physical_area",
            "physical_perimeter",
            "physical_projected_aperture_radius",
            "physical_planarity_rms",
            "physical_planarity_max",
        ):
            value = _finite(getattr(self, name), name=name)
            if value < 0.0 or (name in {"physical_area", "physical_perimeter"} and value <= 0.0):
                raise RegisteredStructuralViewInputError(f"{name} has an invalid value.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "side_index": self.side_index,
            "physical_vertices": [list(value) for value in self.physical_vertices],
            "registered_vertices": [list(value) for value in self.registered_vertices],
            "physical_center": list(self.physical_center),
            "registered_center": list(self.registered_center),
            "registered_unit_normal": list(self.registered_unit_normal),
            "physical_area": self.physical_area,
            "physical_perimeter": self.physical_perimeter,
            "physical_projected_aperture_radius": self.physical_projected_aperture_radius,
            "physical_planarity_rms": self.physical_planarity_rms,
            "physical_planarity_max": self.physical_planarity_max,
        }


@dataclass(frozen=True, slots=True)
class RegisteredWindowEmbedding:
    window_index: int
    physical_center: tuple[float, float, float]
    registered_center: tuple[float, float, float]
    registered_fractional_unwrapped: tuple[float, float, float]
    registered_fractional_wrapped: tuple[float, float, float]
    registered_image_shift: tuple[int, int, int]
    physical_area: float
    physical_projected_aperture_radius: float
    physical_planarity_rms: float
    physical_planarity_max: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "window_index", _nonnegative_int(self.window_index, name="window_index"))
        for name in (
            "physical_center",
            "registered_center",
            "registered_fractional_unwrapped",
            "registered_fractional_wrapped",
        ):
            object.__setattr__(self, name, _float3(getattr(self, name), name=name))
        object.__setattr__(
            self, "registered_image_shift", _int3(self.registered_image_shift, name="registered_image_shift")
        )
        for name in (
            "physical_area",
            "physical_projected_aperture_radius",
            "physical_planarity_rms",
            "physical_planarity_max",
        ):
            value = _finite(getattr(self, name), name=name)
            if value < 0.0 or (name == "physical_area" and value <= 0.0):
                raise RegisteredStructuralViewInputError(f"{name} has an invalid value.")
            object.__setattr__(self, name, value)

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_index": self.window_index,
            "physical_center": list(self.physical_center),
            "registered_center": list(self.registered_center),
            "registered_fractional_unwrapped": list(self.registered_fractional_unwrapped),
            "registered_fractional_wrapped": list(self.registered_fractional_wrapped),
            "registered_image_shift": list(self.registered_image_shift),
            "physical_area": self.physical_area,
            "physical_projected_aperture_radius": self.physical_projected_aperture_radius,
            "physical_planarity_rms": self.physical_planarity_rms,
            "physical_planarity_max": self.physical_planarity_max,
        }


@dataclass(frozen=True, slots=True)
class RegisteredStructuralFrameView:
    result_position: int
    collection_frame_index: int
    frame_id: int
    status: RegisteredStructuralFrameStatus
    registered_cell: tuple[tuple[float, float, float], ...]
    rings: tuple[RegisteredRingStructuralView, ...]
    tiles: tuple[RegisteredTileCageEmbedding, ...]
    tile_faces: tuple[RegisteredTileFaceEmbedding, ...]
    windows: tuple[RegisteredWindowEmbedding, ...]
    diagnostics: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_position", _nonnegative_int(self.result_position, name="result_position"))
        object.__setattr__(self, "collection_frame_index", _nonnegative_int(self.collection_frame_index, name="collection_frame_index"))
        if isinstance(self.frame_id, bool) or not isinstance(self.frame_id, Integral):
            raise RegisteredStructuralViewInputError("frame_id must be an integer.")
        object.__setattr__(self, "status", RegisteredStructuralFrameStatus(self.status))
        cell = _points3(self.registered_cell, name="registered_cell_row")
        if len(cell) != 3 or abs(float(np.linalg.det(np.asarray(cell)))) <= np.finfo(float).tiny:
            raise RegisteredStructuralViewInputError("registered_cell must be full rank.")
        object.__setattr__(self, "registered_cell", cell)
        rings = tuple(self.rings)
        if tuple(value.window_index for value in rings) != tuple(range(len(rings))):
            raise RegisteredStructuralViewInputError(
                "Frame ring views must be densely ordered by window_index."
            )
        tiles = tuple(self.tiles)
        if tiles and tuple(value.tile_index for value in tiles) != tuple(range(len(tiles))):
            raise RegisteredStructuralViewInputError(
                "Frame tile/cage views must be densely ordered by tile_index."
            )
        faces = tuple(self.tile_faces)
        if faces and tuple(value.side_index for value in faces) != tuple(range(len(faces))):
            raise RegisteredStructuralViewInputError(
                "Frame tile-face views must be densely ordered by side_index."
            )
        windows = tuple(self.windows)
        if windows and tuple(value.window_index for value in windows) != tuple(range(len(windows))):
            raise RegisteredStructuralViewInputError(
                "Frame window views must be densely ordered by window_index."
            )
        object.__setattr__(self, "rings", rings)
        object.__setattr__(self, "tiles", tiles)
        object.__setattr__(self, "tile_faces", faces)
        object.__setattr__(self, "windows", windows)
        object.__setattr__(self, "diagnostics", tuple(str(value) for value in self.diagnostics))

    @property
    def resolved_ring_count(self) -> int:
        return sum(value.status is RegisteredRingViewStatus.RESOLVED for value in self.rings)

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_position": self.result_position,
            "collection_frame_index": self.collection_frame_index,
            "frame_id": self.frame_id,
            "status": self.status.value,
            "registered_cell": [list(value) for value in self.registered_cell],
            "rings": [value.to_dict() for value in self.rings],
            "tiles": [value.to_dict() for value in self.tiles],
            "tile_faces": [value.to_dict() for value in self.tile_faces],
            "windows": [value.to_dict() for value in self.windows],
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True, slots=True, eq=False)
class RegisteredStructuralGeometryView:
    collection_binding_digest: str
    registration_signature: str
    frame_ring_geometry_digest: str
    ring_boundary_digest: str
    frame_tiling_geometry_digest: str | None
    options: RegisteredStructuralViewOptions
    resources: RegisteredStructuralViewResources
    frames: tuple[RegisteredStructuralFrameView, ...]
    canonical_schema_version: str = CANONICAL_REGISTERED_STRUCTURAL_VIEW_SCHEMA
    digest_algorithm: str = REGISTERED_STRUCTURAL_VIEW_DIGEST_ALGORITHM
    digest: str = ""

    def __post_init__(self) -> None:
        for name in (
            "collection_binding_digest",
            "registration_signature",
            "frame_ring_geometry_digest",
            "ring_boundary_digest",
        ):
            _sha(getattr(self, name), name=name)
        if self.frame_tiling_geometry_digest is not None:
            _sha(self.frame_tiling_geometry_digest, name="frame_tiling_geometry_digest")
        if not isinstance(self.options, RegisteredStructuralViewOptions):
            raise RegisteredStructuralViewInputError("options has the wrong type.")
        if not isinstance(self.resources, RegisteredStructuralViewResources):
            raise RegisteredStructuralViewInputError("resources has the wrong type.")
        frames = tuple(self.frames)
        if not frames or tuple(frame.result_position for frame in frames) != tuple(range(len(frames))):
            raise RegisteredStructuralViewInputError(
                "Registered structural frames must be nonempty and densely ordered."
            )
        if len({frame.collection_frame_index for frame in frames}) != len(frames):
            raise RegisteredStructuralViewInputError(
                "Registered structural collection frame indices must be unique."
            )
        if self.canonical_schema_version != CANONICAL_REGISTERED_STRUCTURAL_VIEW_SCHEMA:
            raise RegisteredStructuralViewInputError(
                "Unsupported registered structural-view schema."
            )
        if self.digest_algorithm != REGISTERED_STRUCTURAL_VIEW_DIGEST_ALGORITHM:
            raise RegisteredStructuralViewInputError(
                "Unsupported registered structural-view digest algorithm."
            )
        object.__setattr__(self, "frames", frames)
        expected = _digest(self._payload(False))
        if self.digest and self.digest != expected:
            raise RegisteredStructuralViewInputError(
                "Stored registered structural-view digest is inconsistent."
            )
        object.__setattr__(self, "digest", self.digest or expected)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, RegisteredStructuralGeometryView) and self.digest == other.digest

    @property
    def resolved_frame_count(self) -> int:
        return sum(frame.status is RegisteredStructuralFrameStatus.RESOLVED for frame in self.frames)

    def frame_for_collection_index(self, frame_index: int) -> RegisteredStructuralFrameView:
        index = _nonnegative_int(frame_index, name="frame_index")
        matches = [frame for frame in self.frames if frame.collection_frame_index == index]
        if len(matches) != 1:
            raise RegisteredStructuralViewInputError(
                f"Expected one registered structural frame for collection index {index}."
            )
        return matches[0]

    def _payload(self, include_digest: bool) -> dict[str, Any]:
        payload = {
            "canonical_schema_version": self.canonical_schema_version,
            "digest_algorithm": self.digest_algorithm,
            "collection_binding_digest": self.collection_binding_digest,
            "registration_signature": self.registration_signature,
            "frame_ring_geometry_digest": self.frame_ring_geometry_digest,
            "ring_boundary_digest": self.ring_boundary_digest,
            "frame_tiling_geometry_digest": self.frame_tiling_geometry_digest,
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
        collection: AtomisticFrameCollection,
        registration: FrameRegistrationResult,
        frame_ring_geometry: FrameRingGeometryCatalog,
        ring_boundaries: StructuralRingBoundaryCatalog,
        frame_tiling_geometry: FrameTilingGeometryCatalog | None = None,
    ) -> "RegisteredStructuralGeometryView":
        try:
            rebuilt = build_registered_structural_geometry_view(
                collection,
                registration,
                frame_ring_geometry,
                ring_boundaries,
                frame_tiling_geometry=frame_tiling_geometry,
                options=RegisteredStructuralViewOptions.from_dict(payload["options"]),
                resources=RegisteredStructuralViewResources.from_dict(payload["resources"]),
            )
            if rebuilt.to_dict() != dict(payload):
                raise RegisteredStructuralViewSerializationError(
                    "Serialized registered structural view is not canonical for supplied sources."
                )
            return rebuilt
        except RegisteredStructuralViewError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise RegisteredStructuralViewSerializationError(
                "Invalid registered structural-view payload."
            ) from exc


def _wrapped_fractional(
    point: np.ndarray, cell: np.ndarray, pbc: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    fractional = point @ np.linalg.inv(cell)
    wrapped = np.array(fractional, copy=True)
    shifts = np.zeros(3, dtype=np.int64)
    for axis, periodic in enumerate(pbc):
        if periodic:
            shifts[axis] = math.floor(float(wrapped[axis]))
            wrapped[axis] -= shifts[axis]
    return fractional, wrapped, shifts


def _point_segment_distance(point: np.ndarray, first: np.ndarray, second: np.ndarray) -> float:
    direction = second - first
    denominator = float(np.dot(direction, direction))
    if denominator <= np.finfo(float).tiny:
        return float(np.linalg.norm(point - first))
    parameter = float(np.clip(np.dot(point - first, direction) / denominator, 0.0, 1.0))
    return float(np.linalg.norm(point - (first + parameter * direction)))


def _reconstruct_frame(
    o_points: np.ndarray,
    origin_point: np.ndarray,
    *,
    physical: PhysicalRingGeometrySnapshot,
    affine_matrix: np.ndarray,
    transformed_physical_center: np.ndarray,
    previous_frame: RegisteredOrthonormalRingFrame | None,
    options: RegisteredStructuralViewOptions,
) -> RegisteredOrthonormalRingFrame:
    if o_points.ndim != 2 or o_points.shape[0] < 3 or o_points.shape[1] != 3:
        raise RegisteredStructuralViewInvariantError(
            "Registered oxygen polygon must contain at least three 3D points."
        )
    vertex_center = np.mean(o_points, axis=0)
    centered = o_points - vertex_center
    covariance = centered.T @ centered / o_points.shape[0]
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    eigenvalues = np.maximum(eigenvalues, 0.0)
    normal = np.asarray(eigenvectors[:, 0], dtype=np.float64)
    vector_area = 0.5 * np.sum(
        np.cross(centered, np.roll(centered, -1, axis=0)), axis=0
    )
    vector_area_norm = float(np.linalg.norm(vector_area))
    if vector_area_norm <= options.degeneracy_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Transformed oxygen polygon has degenerate vector area."
        )
    if float(np.dot(normal, vector_area)) < 0.0:
        normal = -normal
    normal /= np.linalg.norm(normal)

    seed = centered[int(np.argmax(np.linalg.norm(centered, axis=1)))]
    seed = seed - float(np.dot(seed, normal)) * normal
    seed_norm = float(np.linalg.norm(seed))
    if seed_norm <= options.degeneracy_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Transformed oxygen polygon cannot define an in-plane projection basis."
        )
    provisional_u = seed / seed_norm
    provisional_v = np.cross(normal, provisional_u)
    provisional_v /= np.linalg.norm(provisional_v)
    projected = np.column_stack((centered @ provisional_u, centered @ provisional_v))
    x = projected[:, 0]
    y = projected[:, 1]
    cross_terms = x * np.roll(y, -1) - np.roll(x, -1) * y
    signed_area = 0.5 * float(np.sum(cross_terms))
    if signed_area <= options.degeneracy_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Transformed oxygen polygon has nonpositive projected area."
        )
    centroid_x = float(
        np.sum((x + np.roll(x, -1)) * cross_terms) / (6.0 * signed_area)
    )
    centroid_y = float(
        np.sum((y + np.roll(y, -1)) * cross_terms) / (6.0 * signed_area)
    )
    center = vertex_center + centroid_x * provisional_u + centroid_y * provisional_v

    radial = origin_point - center
    radial = radial - float(np.dot(radial, normal)) * normal
    radial_norm = float(np.linalg.norm(radial))
    if radial_norm <= options.degeneracy_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Persistent cyclic-origin atom is singular in the registered ring plane."
        )
    axis_u = radial / radial_norm
    axis_v = np.cross(normal, axis_u)
    axis_v /= np.linalg.norm(axis_v)
    axis_u = np.cross(axis_v, normal)
    axis_u /= np.linalg.norm(axis_u)

    local = np.column_stack(
        ((o_points - center) @ axis_u, (o_points - center) @ axis_v)
    )
    projected_radii = np.linalg.norm(local, axis=1)
    minimum_radius = float(np.min(projected_radii))
    if minimum_radius <= options.degeneracy_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "At least one transformed oxygen atom has a singular angular coordinate."
        )
    perimeter = float(
        sum(
            np.linalg.norm(o_points[(index + 1) % len(o_points)] - o_points[index])
            for index in range(len(o_points))
        )
    )
    aperture = min(
        _point_segment_distance(
            np.zeros(2, dtype=np.float64),
            local[index],
            local[(index + 1) % len(local)],
        )
        for index in range(len(local))
    )
    deviations = (o_points - vertex_center) @ normal
    planarity_rms = float(np.sqrt(np.mean(np.square(deviations))))
    planarity_max = float(np.max(np.abs(deviations)))
    basis = np.vstack((axis_u, axis_v, normal))
    orthonormality_error = float(np.linalg.norm(basis @ basis.T - np.eye(3)))
    if orthonormality_error > options.orthonormality_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Reconstructed registered ring frame is not orthonormal."
        )

    transformed_axes = np.vstack(
        (
            np.asarray(physical.axis_u) @ affine_matrix,
            np.asarray(physical.axis_v) @ affine_matrix,
            np.asarray(physical.ordered_unit_normal) @ affine_matrix,
        )
    )
    transformed_axes /= np.linalg.norm(transformed_axes, axis=1)[:, None]
    transformed_axis_error = float(
        np.linalg.norm(transformed_axes @ transformed_axes.T - np.eye(3))
    )
    center_error = float(np.linalg.norm(center - transformed_physical_center))
    normal_continuity = None
    axis_continuity = None
    if previous_frame is not None:
        normal_continuity = float(
            np.clip(
                np.dot(previous_frame.ordered_unit_normal, normal),
                -1.0,
                1.0,
            )
        )
        axis_continuity = float(
            np.clip(np.dot(previous_frame.axis_u, axis_u), -1.0, 1.0)
        )

    return RegisteredOrthonormalRingFrame(
        method=REGISTERED_RING_FRAME_METHOD,
        center=tuple(float(value) for value in center),
        axis_u=tuple(float(value) for value in axis_u),
        axis_v=tuple(float(value) for value in axis_v),
        ordered_unit_normal=tuple(float(value) for value in normal),
        covariance_eigenvalues=tuple(float(value) for value in eigenvalues),
        projected_area=signed_area,
        perimeter=perimeter,
        projected_aperture_radius=float(aperture),
        planarity_rms=planarity_rms,
        planarity_max=planarity_max,
        minimum_projected_atom_radius=minimum_radius,
        orthonormality_error=orthonormality_error,
        transformed_physical_axes_orthogonality_error=transformed_axis_error,
        transformed_center_reconstruction_error=center_error,
        normal_continuity_dot=normal_continuity,
        axis_u_continuity_dot=axis_continuity,
    )


def _physical_snapshot(geometry: FrameRingGeometry) -> PhysicalRingGeometrySnapshot:
    if not geometry.mapped:
        raise RegisteredStructuralViewInvariantError(
            "Cannot create a physical snapshot from an unresolved frame ring."
        )
    side = geometry.side_frames[0]
    return PhysicalRingGeometrySnapshot(
        center=geometry.oxygen_area_centroid,  # type: ignore[arg-type]
        axis_u=side.axis_u,
        axis_v=side.axis_v,
        ordered_unit_normal=geometry.ordered_unit_normal,  # type: ignore[arg-type]
        t_cartesian_vertices=geometry.t_cartesian_vertices,
        o_cartesian_vertices=geometry.o_cartesian_vertices,
        projected_area=float(geometry.projected_area),
        perimeter=float(geometry.perimeter),
        center_aperture_radius=float(geometry.center_aperture_radius),
        planarity_rms=float(geometry.planarity_rms),
        planarity_max=float(geometry.planarity_max),
        t_o_distances=geometry.t_o_distances,
        o_t_distances=geometry.o_t_distances,
    )


def _validate_ring_identity(
    geometry: FrameRingGeometry, boundary: StructuralRingBoundary, tolerance: float
) -> None:
    if (
        geometry.window_index != boundary.window_index
        or geometry.face_index != boundary.face_index
        or geometry.primitive_ring_id != boundary.primitive_ring_id
        or geometry.ring_size != boundary.ring_size
    ):
        raise RegisteredStructuralViewSourceError(
            "C2 and C3 ring identities disagree."
        )
    if geometry.mapped and boundary.status is RingBoundaryStatus.RESOLVED:
        if tuple(atom.atom_ref for atom in boundary.t_atoms) == () or tuple(
            atom.atom_ref for atom in boundary.o_atoms
        ) == ():
            raise RegisteredStructuralViewSourceError(
                "Resolved C3 boundary has no persistent atom identities."
            )
        if not np.allclose(
            np.asarray([atom.cartesian for atom in boundary.t_atoms]),
            np.asarray(geometry.t_cartesian_vertices),
            rtol=0.0,
            atol=tolerance,
        ) or not np.allclose(
            np.asarray([atom.cartesian for atom in boundary.o_atoms]),
            np.asarray(geometry.o_cartesian_vertices),
            rtol=0.0,
            atol=tolerance,
        ):
            raise RegisteredStructuralViewSourceError(
                "C2 and C3 physical ring coordinates disagree."
            )


def _linked_atom(
    source: Any,
    *,
    frame_index: int,
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    options: RegisteredStructuralViewOptions,
) -> LinkedStructuralAtomEmbedding:
    physical = np.asarray(source.cartesian, dtype=np.float64)
    registered = registration.transform_positions(physical, frame_index=frame_index)
    cell = np.asarray(registration.registered_cells[frame_index], dtype=np.float64)
    base = np.asarray(
        registration.registered_unwrapped_cartesian[frame_index, source.atom_ref.atom_index],
        dtype=np.float64,
    )
    fractional_delta = (registered - base) @ np.linalg.inv(cell)
    image = np.zeros(3, dtype=np.int64)
    for axis, periodic in enumerate(collection.pbc):
        if periodic:
            image[axis] = int(np.rint(fractional_delta[axis]))
        elif abs(float(fractional_delta[axis])) > options.coordinate_tolerance:
            raise RegisteredStructuralViewSourceError(
                "A structural atom requires a nonperiodic registered image shift."
            )
    reconstructed = base + image @ cell
    residual = float(np.linalg.norm(reconstructed - registered))
    if residual > options.coordinate_tolerance:
        raise RegisteredStructuralViewSourceError(
            "Transformed structural atom does not close on the registered lattice: "
            f"residual={residual:.6g}."
        )
    frac, wrapped, absolute_image = _wrapped_fractional(
        registered, cell, np.asarray(collection.pbc, dtype=bool)
    )
    if float(np.linalg.norm((wrapped + absolute_image) @ cell - registered)) > options.coordinate_tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Registered atom wrapped/image reconstruction failed."
        )
    return LinkedStructuralAtomEmbedding(
        boundary_kind=source.boundary_kind,
        cyclic_index=source.cyclic_index,
        atom_ref=source.atom_ref,
        atomic_number=source.atomic_number,
        element=source.element,
        oxygen_environment_signature=source.oxygen_environment_signature,
        crystallographic_alias=source.crystallographic_alias,
        physical_cartesian=tuple(float(value) for value in physical),
        registered_cartesian=tuple(float(value) for value in registered),
        registered_fractional_unwrapped=tuple(float(value) for value in frac),
        registered_fractional_wrapped=tuple(float(value) for value in wrapped),
        registered_image_shift=tuple(int(value) for value in image),
        periodic_image_residual=residual,
    )


def _origin_registered_point(
    boundary: StructuralRingBoundary,
    t_atoms: tuple[LinkedStructuralAtomEmbedding, ...],
    o_atoms: tuple[LinkedStructuralAtomEmbedding, ...],
) -> np.ndarray:
    origin = boundary.cyclic_origin_atom
    if origin is None:
        raise RegisteredStructuralViewInvariantError(
            "Resolved C3 boundary has no cyclic-origin atom."
        )
    matches = [
        atom
        for atom in (*t_atoms, *o_atoms)
        if atom.atom_ref == origin
    ]
    if len(matches) != 1:
        raise RegisteredStructuralViewInvariantError(
            "Cyclic-origin atom is not unique in the linked registered boundary."
        )
    return np.asarray(matches[0].registered_cartesian, dtype=np.float64)


def _ring_view(
    geometry: FrameRingGeometry,
    boundary: StructuralRingBoundary,
    *,
    frame_index: int,
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    options: RegisteredStructuralViewOptions,
    previous_frame: RegisteredOrthonormalRingFrame | None,
    continuity_required: bool,
) -> RegisteredRingStructuralView:
    _validate_ring_identity(geometry, boundary, options.coordinate_tolerance)
    identity = {
        "window_index": geometry.window_index,
        "face_index": geometry.face_index,
        "primitive_ring_id": geometry.primitive_ring_id,
        "ring_size": geometry.ring_size,
    }
    if geometry.status is not FrameRingGeometryStatus.MAPPED:
        return RegisteredRingStructuralView(
            **identity,
            status=RegisteredRingViewStatus.PHYSICAL_RING_UNRESOLVED,
            message=geometry.message,
            physical=None,
            registered=None,
        )
    physical = _physical_snapshot(geometry)
    if boundary.status is not RingBoundaryStatus.RESOLVED:
        return RegisteredRingStructuralView(
            **identity,
            status=RegisteredRingViewStatus.BOUNDARY_UNRESOLVED,
            message=boundary.message,
            physical=physical,
            registered=None,
        )
    try:
        t_atoms = tuple(
            _linked_atom(
                source,
                frame_index=frame_index,
                collection=collection,
                registration=registration,
                options=options,
            )
            for source in boundary.t_atoms
        )
        o_atoms = tuple(
            _linked_atom(
                source,
                frame_index=frame_index,
                collection=collection,
                registration=registration,
                options=options,
            )
            for source in boundary.o_atoms
        )
        transformed_center = registration.transform_positions(
            np.asarray(physical.center), frame_index=frame_index
        )
        reconstructed = _reconstruct_frame(
            np.asarray([atom.registered_cartesian for atom in o_atoms]),
            _origin_registered_point(boundary, t_atoms, o_atoms),
            physical=physical,
            affine_matrix=np.asarray(registration.affine_matrices[frame_index]),
            transformed_physical_center=np.asarray(transformed_center),
            previous_frame=previous_frame if continuity_required else None,
            options=options,
        )
        if continuity_required and previous_frame is not None:
            continuity_values = (
                reconstructed.normal_continuity_dot,
                reconstructed.axis_u_continuity_dot,
            )
            if any(
                value is not None
                and value < options.minimum_orientation_continuity_dot
                for value in continuity_values
            ):
                return RegisteredRingStructuralView(
                    **identity,
                    status=RegisteredRingViewStatus.ORIENTATION_DISCONTINUITY,
                    message=(
                        "Registered ring orientation continuity failed: "
                        f"normal_dot={reconstructed.normal_continuity_dot}, "
                        f"axis_u_dot={reconstructed.axis_u_continuity_dot}."
                    ),
                    physical=physical,
                    registered=None,
                )
        cell = np.asarray(registration.registered_cells[frame_index])
        frac, wrapped, shift = _wrapped_fractional(
            np.asarray(reconstructed.center), cell, np.asarray(collection.pbc, dtype=bool)
        )
        registered = RegisteredRingEmbedding(
            center_fractional_unwrapped=tuple(float(value) for value in frac),
            center_fractional_wrapped=tuple(float(value) for value in wrapped),
            center_image_shift=tuple(int(value) for value in shift),
            t_atoms=t_atoms,
            o_atoms=o_atoms,
            frame=reconstructed,
        )
        return RegisteredRingStructuralView(
            **identity,
            status=RegisteredRingViewStatus.RESOLVED,
            message="Registered structural ring resolved.",
            physical=physical,
            registered=registered,
        )
    except RegisteredStructuralViewSourceError:
        raise
    except RegisteredStructuralViewError as exc:
        return RegisteredRingStructuralView(
            **identity,
            status=RegisteredRingViewStatus.REGISTERED_GEOMETRY_DEGENERATE,
            message=str(exc),
            physical=physical,
            registered=None,
        )


def _transform_center(
    point: Sequence[float],
    *,
    frame_index: int,
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    registered = registration.transform_positions(
        np.asarray(point, dtype=np.float64), frame_index=frame_index
    )
    cell = np.asarray(registration.registered_cells[frame_index])
    frac, wrapped, shift = _wrapped_fractional(
        registered, cell, np.asarray(collection.pbc, dtype=bool)
    )
    return registered, frac, wrapped, shift


def _registered_face_normal(points: np.ndarray, tolerance: float) -> np.ndarray:
    centered = points - np.mean(points, axis=0)
    area_vector = 0.5 * np.sum(
        np.cross(centered, np.roll(centered, -1, axis=0)), axis=0
    )
    norm = float(np.linalg.norm(area_vector))
    if norm <= tolerance:
        raise RegisteredStructuralViewInvariantError(
            "Transformed tile face has degenerate vector area."
        )
    return area_vector / norm


def _tiling_embeddings(
    frame: MappedTilingFrame | None,
    *,
    catalog_supplied: bool,
    frame_index: int,
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    options: RegisteredStructuralViewOptions,
) -> tuple[
    tuple[RegisteredTileCageEmbedding, ...],
    tuple[RegisteredTileFaceEmbedding, ...],
    tuple[RegisteredWindowEmbedding, ...],
    tuple[str, ...],
]:
    if frame is None:
        diagnostics = (
            ("Optional tiling catalog has no frame for this collection index.",)
            if catalog_supplied
            else ()
        )
        return (), (), (), diagnostics
    if frame.status is not FrameTilingGeometryStatus.MAPPED:
        return (), (), (), (f"Frame tiling unresolved: {frame.diagnostic or frame.status.value}",)
    tiles: list[RegisteredTileCageEmbedding] = []
    for tile in frame.tiles:
        registered, frac, wrapped, shift = _transform_center(
            tile.cartesian_center,
            frame_index=frame_index,
            collection=collection,
            registration=registration,
        )
        tiles.append(
            RegisteredTileCageEmbedding(
                tile_index=tile.tile_index,
                physical_center=tile.cartesian_center,
                registered_center=tuple(float(value) for value in registered),
                registered_fractional_unwrapped=tuple(float(value) for value in frac),
                registered_fractional_wrapped=tuple(float(value) for value in wrapped),
                registered_image_shift=tuple(int(value) for value in shift),
                physical_volume=tile.volume,
                physical_surface_area=tile.surface_area,
                physical_equivalent_sphere_radius=tile.equivalent_sphere_radius,
                physical_sphericity=tile.sphericity,
                physical_diameter=tile.diameter,
                physical_orientation_preserved=tile.orientation_preserved,
            )
        )
    faces: list[RegisteredTileFaceEmbedding] = []
    for face in frame.tile_faces:
        physical_vertices = np.asarray(face.cartesian_vertices, dtype=np.float64)
        registered_vertices = registration.transform_positions(
            physical_vertices, frame_index=frame_index
        )
        center = registration.transform_positions(
            np.asarray(face.cartesian_center), frame_index=frame_index
        )
        normal = _registered_face_normal(
            registered_vertices, options.degeneracy_tolerance
        )
        faces.append(
            RegisteredTileFaceEmbedding(
                side_index=face.side_index,
                physical_vertices=face.cartesian_vertices,
                registered_vertices=tuple(
                    tuple(float(value) for value in point)
                    for point in registered_vertices
                ),
                physical_center=face.cartesian_center,
                registered_center=tuple(float(value) for value in center),
                registered_unit_normal=tuple(float(value) for value in normal),
                physical_area=face.area,
                physical_perimeter=face.perimeter,
                physical_projected_aperture_radius=face.projected_aperture_radius,
                physical_planarity_rms=face.planarity_rms,
                physical_planarity_max=face.planarity_max,
            )
        )
    windows: list[RegisteredWindowEmbedding] = []
    for window in frame.windows:
        registered, frac, wrapped, shift = _transform_center(
            window.cartesian_center,
            frame_index=frame_index,
            collection=collection,
            registration=registration,
        )
        windows.append(
            RegisteredWindowEmbedding(
                window_index=window.window_index,
                physical_center=window.cartesian_center,
                registered_center=tuple(float(value) for value in registered),
                registered_fractional_unwrapped=tuple(float(value) for value in frac),
                registered_fractional_wrapped=tuple(float(value) for value in wrapped),
                registered_image_shift=tuple(int(value) for value in shift),
                physical_area=window.area,
                physical_projected_aperture_radius=window.projected_aperture_radius,
                physical_planarity_rms=window.planarity_rms,
                physical_planarity_max=window.planarity_max,
            )
        )
    return tuple(tiles), tuple(faces), tuple(windows), ()


def _preflight(
    frame_ring_geometry: FrameRingGeometryCatalog,
    frame_tiling_geometry: FrameTilingGeometryCatalog | None,
    resources: RegisteredStructuralViewResources,
) -> None:
    n_frames = len(frame_ring_geometry.frames)
    if n_frames > resources.max_frames:
        raise RegisteredStructuralViewResourceError("Frame count exceeds max_frames.")
    ring_instances = sum(len(frame.rings) for frame in frame_ring_geometry.frames)
    if ring_instances > resources.max_ring_instances:
        raise RegisteredStructuralViewResourceError(
            "Ring-instance count exceeds max_ring_instances."
        )
    atom_instances = sum(
        2 * ring.ring_size for frame in frame_ring_geometry.frames for ring in frame.rings
    )
    if atom_instances > resources.max_linked_atom_instances:
        raise RegisteredStructuralViewResourceError(
            "Linked T/O atom count exceeds max_linked_atom_instances."
        )
    if frame_tiling_geometry is not None:
        tile_instances = sum(len(frame.tiles) for frame in frame_tiling_geometry.frames)
        face_vertices = sum(
            len(face.cartesian_vertices)
            for frame in frame_tiling_geometry.frames
            for face in frame.tile_faces
        )
        window_instances = sum(len(frame.windows) for frame in frame_tiling_geometry.frames)
        if tile_instances > resources.max_tile_instances:
            raise RegisteredStructuralViewResourceError(
                "Tile/cage count exceeds max_tile_instances."
            )
        if face_vertices > resources.max_tile_face_vertex_instances:
            raise RegisteredStructuralViewResourceError(
                "Tile-face vertex count exceeds max_tile_face_vertex_instances."
            )
        if window_instances > resources.max_window_instances:
            raise RegisteredStructuralViewResourceError(
                "Window count exceeds max_window_instances."
            )


def _validate_sources(
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    frame_ring_geometry: FrameRingGeometryCatalog,
    ring_boundaries: StructuralRingBoundaryCatalog,
    frame_tiling_geometry: FrameTilingGeometryCatalog | None,
) -> dict[int, MappedTilingFrame]:
    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    if not isinstance(registration, FrameRegistrationResult):
        raise TypeError("registration must be FrameRegistrationResult.")
    if not isinstance(frame_ring_geometry, FrameRingGeometryCatalog):
        raise TypeError("frame_ring_geometry must be FrameRingGeometryCatalog.")
    if not isinstance(ring_boundaries, StructuralRingBoundaryCatalog):
        raise TypeError("ring_boundaries must be StructuralRingBoundaryCatalog.")
    if frame_tiling_geometry is not None and not isinstance(
        frame_tiling_geometry, FrameTilingGeometryCatalog
    ):
        raise TypeError("frame_tiling_geometry must be FrameTilingGeometryCatalog or None.")
    if registration.registered_unwrapped_cartesian.shape[:2] != (
        collection.n_frames,
        collection.n_atoms,
    ):
        raise RegisteredStructuralViewSourceError(
            "Registration dimensions disagree with the collection."
        )
    if ring_boundaries.frame_ring_geometry_digest != frame_ring_geometry.digest:
        raise RegisteredStructuralViewSourceError(
            "C3 boundary catalog is not bound to the supplied C2 frame-ring catalog."
        )
    if len(frame_ring_geometry.frames) != len(ring_boundaries.frames):
        raise RegisteredStructuralViewSourceError(
            "C2 and C3 frame counts disagree."
        )
    for geometry_frame, boundary_frame in zip(
        frame_ring_geometry.frames, ring_boundaries.frames, strict=True
    ):
        if (
            geometry_frame.result_position != boundary_frame.result_position
            or geometry_frame.collection_frame_index
            != boundary_frame.collection_frame_index
            or geometry_frame.frame_id != boundary_frame.frame_id
        ):
            raise RegisteredStructuralViewSourceError(
                "C2 and C3 frame identities disagree."
            )
        index = geometry_frame.collection_frame_index
        if index >= collection.n_frames:
            raise RegisteredStructuralViewSourceError(
                "Structural frame index lies outside the collection."
            )
        if int(collection.frame_ids[index]) != geometry_frame.frame_id:
            raise RegisteredStructuralViewSourceError(
                "Structural frame ID disagrees with the collection."
            )
        if len(geometry_frame.rings) != len(boundary_frame.boundaries):
            raise RegisteredStructuralViewSourceError(
                "C2 and C3 ring counts disagree."
            )
    tiling_map: dict[int, MappedTilingFrame] = {}
    if frame_tiling_geometry is not None:
        for frame in frame_tiling_geometry.frames:
            if frame.collection_frame_index in tiling_map:
                raise RegisteredStructuralViewSourceError(
                    "Optional tiling catalog contains duplicate collection frame indices."
                )
            if frame.collection_frame_index >= collection.n_frames:
                raise RegisteredStructuralViewSourceError(
                    "Optional tiling frame index lies outside the collection."
                )
            if int(collection.frame_ids[frame.collection_frame_index]) != frame.frame_id:
                raise RegisteredStructuralViewSourceError(
                    "Optional tiling frame ID disagrees with the collection."
                )
            tiling_map[frame.collection_frame_index] = frame
    return tiling_map


def build_registered_structural_geometry_view(
    collection: AtomisticFrameCollection,
    registration: FrameRegistrationResult,
    frame_ring_geometry: FrameRingGeometryCatalog,
    ring_boundaries: StructuralRingBoundaryCatalog,
    *,
    frame_tiling_geometry: FrameTilingGeometryCatalog | None = None,
    options: RegisteredStructuralViewOptions | None = None,
    resources: RegisteredStructuralViewResources | None = None,
) -> RegisteredStructuralGeometryView:
    """Build one immutable physical/registered structural geometry view."""

    active_options = options or RegisteredStructuralViewOptions()
    active_resources = resources or RegisteredStructuralViewResources()
    if not isinstance(active_options, RegisteredStructuralViewOptions):
        raise RegisteredStructuralViewInputError(
            "options must be RegisteredStructuralViewOptions."
        )
    if not isinstance(active_resources, RegisteredStructuralViewResources):
        raise RegisteredStructuralViewInputError(
            "resources must be RegisteredStructuralViewResources."
        )
    tiling_map = _validate_sources(
        collection,
        registration,
        frame_ring_geometry,
        ring_boundaries,
        frame_tiling_geometry,
    )
    _preflight(frame_ring_geometry, frame_tiling_geometry, active_resources)

    previous_frames: dict[int, RegisteredOrthonormalRingFrame] = {}
    output_frames: list[RegisteredStructuralFrameView] = []
    reset_indices = set(registration.policy.segment_reset_frame_indices)
    trajectory = collection.frame_semantics is FrameSemantics.TRAJECTORY

    for geometry_frame, boundary_frame in zip(
        frame_ring_geometry.frames, ring_boundaries.frames, strict=True
    ):
        frame_index = geometry_frame.collection_frame_index
        if frame_index in reset_indices:
            previous_frames.clear()
        continuity_required = (
            trajectory and active_options.enforce_trajectory_orientation_continuity
        )
        rings: list[RegisteredRingStructuralView] = []
        for geometry, boundary in zip(
            geometry_frame.rings, boundary_frame.boundaries, strict=True
        ):
            view = _ring_view(
                geometry,
                boundary,
                frame_index=frame_index,
                collection=collection,
                registration=registration,
                options=active_options,
                previous_frame=previous_frames.get(geometry.window_index),
                continuity_required=continuity_required,
            )
            rings.append(view)
            if view.status is RegisteredRingViewStatus.RESOLVED:
                previous_frames[view.window_index] = view.registered.frame  # type: ignore[union-attr]
            else:
                previous_frames.pop(view.window_index, None)

        tiles, faces, windows, tiling_diagnostics = _tiling_embeddings(
            tiling_map.get(frame_index),
            catalog_supplied=frame_tiling_geometry is not None,
            frame_index=frame_index,
            collection=collection,
            registration=registration,
            options=active_options,
        )
        diagnostics = list(tiling_diagnostics)
        unresolved_rings = [
            view for view in rings if view.status is not RegisteredRingViewStatus.RESOLVED
        ]
        if unresolved_rings:
            diagnostics.append(
                f"{len(unresolved_rings)} of {len(rings)} registered ring views unresolved."
            )
        if not rings or len(unresolved_rings) == len(rings):
            status = RegisteredStructuralFrameStatus.UNRESOLVED
        elif unresolved_rings or tiling_diagnostics:
            status = RegisteredStructuralFrameStatus.PARTIAL
        else:
            status = RegisteredStructuralFrameStatus.RESOLVED
        output_frames.append(
            RegisteredStructuralFrameView(
                result_position=geometry_frame.result_position,
                collection_frame_index=frame_index,
                frame_id=geometry_frame.frame_id,
                status=status,
                registered_cell=tuple(
                    tuple(float(value) for value in row)
                    for row in registration.registered_cells[frame_index]
                ),
                rings=tuple(rings),
                tiles=tiles,
                tile_faces=faces,
                windows=windows,
                diagnostics=tuple(diagnostics),
            )
        )

    return RegisteredStructuralGeometryView(
        collection_binding_digest=_collection_binding_digest(collection),
        registration_signature=registration.signature,
        frame_ring_geometry_digest=frame_ring_geometry.digest,
        ring_boundary_digest=ring_boundaries.digest,
        frame_tiling_geometry_digest=(
            None if frame_tiling_geometry is None else frame_tiling_geometry.digest
        ),
        options=active_options,
        resources=active_resources,
        frames=tuple(output_frames),
    )


__all__ = [
    "CANONICAL_REGISTERED_STRUCTURAL_VIEW_SCHEMA",
    "REGISTERED_RING_FRAME_METHOD",
    "REGISTERED_STRUCTURAL_VIEW_DIGEST_ALGORITHM",
    "LinkedStructuralAtomEmbedding",
    "PhysicalRingGeometrySnapshot",
    "RegisteredOrthonormalRingFrame",
    "RegisteredRingEmbedding",
    "RegisteredRingStructuralView",
    "RegisteredRingViewStatus",
    "RegisteredStructuralFrameStatus",
    "RegisteredStructuralFrameView",
    "RegisteredStructuralGeometryView",
    "RegisteredStructuralViewError",
    "RegisteredStructuralViewInputError",
    "RegisteredStructuralViewInvariantError",
    "RegisteredStructuralViewOptions",
    "RegisteredStructuralViewResourceError",
    "RegisteredStructuralViewResources",
    "RegisteredStructuralViewSerializationError",
    "RegisteredStructuralViewSourceError",
    "RegisteredTileCageEmbedding",
    "RegisteredTileFaceEmbedding",
    "RegisteredWindowEmbedding",
    "build_registered_structural_geometry_view",
]
