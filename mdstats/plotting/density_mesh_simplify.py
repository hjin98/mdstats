"""Periodic fidelity-constrained density-mesh simplification for LD9-V2.

The polygon reduction uses quadric-error decimation in the spirit of Garland and
Heckbert, *Surface Simplification Using Quadric Error Metrics* (SIGGRAPH 1997),
through the optional ``fast-simplification`` implementation.  The mdstats
contribution is the periodic safety contract: closed interior components are
simplified directly, nonwinding seam components are reconstructed in the
periodic quotient and lifted to continuous charts before simplification, topology
is checked after every attempt, and the immutable scientific scalar field remains
the fidelity oracle.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import breadth_first_order, connected_components
from scipy.spatial import cKDTree

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_mesh_validation import (
    MeshTopologySummary,
    sample_mesh_surface,
    summarize_mesh_topology,
)
from .graph_errors import (
    GraphAdapterError,
    GraphComplexityError,
    GraphStyleError,
    GraphUnsupportedFeatureError,
)

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

MESH_SIMPLIFICATION_OPTIONS_SCHEMA = "mdstats.mesh-simplification-options.v1"
MESH_SIMPLIFICATION_COMPONENT_SCHEMA = "mdstats.mesh-simplification-component.v1"
IMPLICIT_MESH_FIDELITY_SCHEMA = "mdstats.implicit-mesh-fidelity.v1"
PERIODIC_MESH_SIMPLIFICATION_SCHEMA = "mdstats.periodic-mesh-simplification.v1"


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _nonnegative_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise GraphStyleError(f"{name} must be finite and nonnegative.")
    return result


def _readonly(value: Any, dtype: Any, *, ndim: int, name: str) -> NDArray[Any]:
    result = np.array(value, dtype=dtype, copy=True, order="C")
    if result.ndim != ndim:
        raise GraphAdapterError(f"{name} must be {ndim}-dimensional.")
    if np.issubdtype(result.dtype, np.floating) and np.any(~np.isfinite(result)):
        raise GraphAdapterError(f"{name} must contain finite values.")
    result.setflags(write=False)
    return result


@dataclass(frozen=True, slots=True)
class MeshSimplificationOptions:
    """Bounded simplification and scientific-fidelity policy."""

    enabled: bool = True
    target_faces: int | None = None
    local_presimplification: bool = True
    local_target_fraction: float = 0.70
    min_component_faces: int = 16
    max_attempts: int = 5
    aggressiveness: float = 3.0
    seam_tolerance_fractional: float = 1.0e-12
    projection_iterations: int = 3
    projection_max_step: float = 0.02
    max_samples: int = 30_000
    max_surface_error_p99: float = 0.02
    max_surface_error_max: float = 0.08
    max_implicit_displacement_p99: float = 0.01
    max_normal_degradation_degrees: float = 8.0
    max_relative_scalar_residual_p99: float = 0.08
    require_component_count: bool = True
    require_euler_characteristic: bool = True
    require_boundary_edge_count: bool = True
    require_seam_preservation: bool = True
    hard_target: bool = True
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = MESH_SIMPLIFICATION_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MESH_SIMPLIFICATION_OPTIONS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported mesh-simplification-options schema {self.schema_version!r}."
            )
        object.__setattr__(self, "enabled", bool(self.enabled))
        if self.target_faces is not None:
            object.__setattr__(
                self,
                "target_faces",
                _positive_int(self.target_faces, name="target_faces"),
            )
        fraction = float(self.local_target_fraction)
        if not np.isfinite(fraction) or not 0.0 < fraction <= 1.0:
            raise GraphStyleError("local_target_fraction must lie in (0, 1].")
        object.__setattr__(self, "local_target_fraction", fraction)
        object.__setattr__(
            self,
            "min_component_faces",
            _positive_int(self.min_component_faces, name="min_component_faces", minimum=4),
        )
        object.__setattr__(
            self, "max_attempts", _positive_int(self.max_attempts, name="max_attempts")
        )
        object.__setattr__(
            self, "aggressiveness", _nonnegative_float(self.aggressiveness, name="aggressiveness")
        )
        for name in (
            "seam_tolerance_fractional",
            "projection_max_step",
            "max_surface_error_p99",
            "max_surface_error_max",
            "max_implicit_displacement_p99",
            "max_normal_degradation_degrees",
            "max_relative_scalar_residual_p99",
        ):
            object.__setattr__(self, name, _nonnegative_float(getattr(self, name), name=name))
        object.__setattr__(
            self,
            "projection_iterations",
            _positive_int(self.projection_iterations, name="projection_iterations", minimum=0),
        )
        object.__setattr__(
            self, "max_samples", _positive_int(self.max_samples, name="max_samples")
        )
        for name in (
            "local_presimplification",
            "require_component_count",
            "require_euler_characteristic",
            "require_boundary_edge_count",
            "require_seam_preservation",
            "hard_target",
        ):
            object.__setattr__(self, name, bool(getattr(self, name)))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "enabled": self.enabled,
            "target_faces": self.target_faces,
            "local_presimplification": self.local_presimplification,
            "local_target_fraction": self.local_target_fraction,
            "min_component_faces": self.min_component_faces,
            "max_attempts": self.max_attempts,
            "aggressiveness": self.aggressiveness,
            "seam_tolerance_fractional": self.seam_tolerance_fractional,
            "projection_iterations": self.projection_iterations,
            "projection_max_step": self.projection_max_step,
            "max_samples": self.max_samples,
            "max_surface_error_p99": self.max_surface_error_p99,
            "max_surface_error_max": self.max_surface_error_max,
            "max_implicit_displacement_p99": self.max_implicit_displacement_p99,
            "max_normal_degradation_degrees": self.max_normal_degradation_degrees,
            "max_relative_scalar_residual_p99": self.max_relative_scalar_residual_p99,
            "require_component_count": self.require_component_count,
            "require_euler_characteristic": self.require_euler_characteristic,
            "require_boundary_edge_count": self.require_boundary_edge_count,
            "require_seam_preservation": self.require_seam_preservation,
            "hard_target": self.hard_target,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MeshSimplificationOptions":
        return cls(
            enabled=value.get("enabled", True),
            target_faces=value.get("target_faces"),
            local_presimplification=value.get("local_presimplification", True),
            local_target_fraction=value.get("local_target_fraction", 0.70),
            min_component_faces=value.get("min_component_faces", 16),
            max_attempts=value.get("max_attempts", 5),
            aggressiveness=value.get("aggressiveness", 3.0),
            seam_tolerance_fractional=value.get("seam_tolerance_fractional", 1.0e-12),
            projection_iterations=value.get("projection_iterations", 3),
            projection_max_step=value.get("projection_max_step", 0.02),
            max_samples=value.get("max_samples", 30_000),
            max_surface_error_p99=value.get("max_surface_error_p99", 0.02),
            max_surface_error_max=value.get("max_surface_error_max", 0.08),
            max_implicit_displacement_p99=value.get("max_implicit_displacement_p99", 0.01),
            max_normal_degradation_degrees=value.get("max_normal_degradation_degrees", 8.0),
            max_relative_scalar_residual_p99=value.get("max_relative_scalar_residual_p99", 0.08),
            require_component_count=value.get("require_component_count", True),
            require_euler_characteristic=value.get("require_euler_characteristic", True),
            require_seam_preservation=value.get("require_seam_preservation", True),
            hard_target=value.get("hard_target", True),
            metadata=value.get("metadata", {}),
            schema_version=value.get("schema_version", MESH_SIMPLIFICATION_OPTIONS_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class MeshSimplificationComponentReport:
    component_index: int
    input_faces: int
    target_faces: int
    output_faces: int
    protected: bool
    accepted: bool
    attempts: int
    rejection_reason: str | None = None
    schema_version: str = MESH_SIMPLIFICATION_COMPONENT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MESH_SIMPLIFICATION_COMPONENT_SCHEMA:
            raise GraphAdapterError("Unsupported simplification-component schema.")
        for name in ("component_index", "input_faces", "target_faces", "output_faces", "attempts"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        object.__setattr__(self, "protected", bool(self.protected))
        object.__setattr__(self, "accepted", bool(self.accepted))
        if self.rejection_reason is not None:
            object.__setattr__(self, "rejection_reason", str(self.rejection_reason))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "component_index": self.component_index,
            "input_faces": self.input_faces,
            "target_faces": self.target_faces,
            "output_faces": self.output_faces,
            "protected": self.protected,
            "accepted": self.accepted,
            "attempts": self.attempts,
            "rejection_reason": self.rejection_reason,
        }

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "MeshSimplificationComponentReport":
        return cls(
            component_index=value["component_index"],
            input_faces=value["input_faces"],
            target_faces=value["target_faces"],
            output_faces=value["output_faces"],
            protected=value["protected"],
            accepted=value["accepted"],
            attempts=value["attempts"],
            rejection_reason=value.get("rejection_reason"),
            schema_version=value.get(
                "schema_version", MESH_SIMPLIFICATION_COMPONENT_SCHEMA
            ),
        )


@dataclass(frozen=True, slots=True)
class ImplicitMeshFidelityReport:
    reference_topology: MeshTopologySummary
    candidate_topology: MeshTopologySummary
    sample_count: int
    symmetric_distance_p99: float
    symmetric_distance_max: float
    reference_sampling_distance_p99: float
    reference_sampling_distance_max: float
    excess_surface_distance_p99: float
    excess_surface_distance_max: float
    implicit_displacement_p99: float
    implicit_displacement_max: float
    reference_normal_p99_degrees: float
    candidate_normal_p99_degrees: float
    normal_degradation_degrees: float
    relative_scalar_residual_p99: float
    seam_vertex_count_reference: int
    seam_vertex_count_candidate: int
    violations: tuple[str, ...]
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = IMPLICIT_MESH_FIDELITY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != IMPLICIT_MESH_FIDELITY_SCHEMA:
            raise GraphAdapterError("Unsupported implicit-mesh-fidelity schema.")
        object.__setattr__(self, "sample_count", _positive_int(self.sample_count, name="sample_count"))
        for name in (
            "symmetric_distance_p99", "symmetric_distance_max",
            "reference_sampling_distance_p99", "reference_sampling_distance_max",
            "excess_surface_distance_p99", "excess_surface_distance_max",
            "implicit_displacement_p99", "implicit_displacement_max",
            "reference_normal_p99_degrees", "candidate_normal_p99_degrees",
            "normal_degradation_degrees", "relative_scalar_residual_p99",
        ):
            object.__setattr__(self, name, _nonnegative_float(getattr(self, name), name=name))
        for name in ("seam_vertex_count_reference", "seam_vertex_count_candidate"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        object.__setattr__(self, "violations", tuple(str(v) for v in self.violations))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def passed(self) -> bool:
        return not self.violations

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "passed": self.passed,
            "violations": list(self.violations),
            "reference_topology": self.reference_topology.to_json_dict(),
            "candidate_topology": self.candidate_topology.to_json_dict(),
            "sample_count": self.sample_count,
            "symmetric_distance_p99": self.symmetric_distance_p99,
            "symmetric_distance_max": self.symmetric_distance_max,
            "reference_sampling_distance_p99": self.reference_sampling_distance_p99,
            "reference_sampling_distance_max": self.reference_sampling_distance_max,
            "excess_surface_distance_p99": self.excess_surface_distance_p99,
            "excess_surface_distance_max": self.excess_surface_distance_max,
            "implicit_displacement_p99": self.implicit_displacement_p99,
            "implicit_displacement_max": self.implicit_displacement_max,
            "reference_normal_p99_degrees": self.reference_normal_p99_degrees,
            "candidate_normal_p99_degrees": self.candidate_normal_p99_degrees,
            "normal_degradation_degrees": self.normal_degradation_degrees,
            "relative_scalar_residual_p99": self.relative_scalar_residual_p99,
            "seam_vertex_count_reference": self.seam_vertex_count_reference,
            "seam_vertex_count_candidate": self.seam_vertex_count_candidate,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "ImplicitMeshFidelityReport":
        return cls(
            reference_topology=MeshTopologySummary.from_json_dict(
                value["reference_topology"]
            ),
            candidate_topology=MeshTopologySummary.from_json_dict(
                value["candidate_topology"]
            ),
            sample_count=value["sample_count"],
            symmetric_distance_p99=value["symmetric_distance_p99"],
            symmetric_distance_max=value["symmetric_distance_max"],
            reference_sampling_distance_p99=value[
                "reference_sampling_distance_p99"
            ],
            reference_sampling_distance_max=value[
                "reference_sampling_distance_max"
            ],
            excess_surface_distance_p99=value["excess_surface_distance_p99"],
            excess_surface_distance_max=value["excess_surface_distance_max"],
            implicit_displacement_p99=value["implicit_displacement_p99"],
            implicit_displacement_max=value["implicit_displacement_max"],
            reference_normal_p99_degrees=value[
                "reference_normal_p99_degrees"
            ],
            candidate_normal_p99_degrees=value[
                "candidate_normal_p99_degrees"
            ],
            normal_degradation_degrees=value["normal_degradation_degrees"],
            relative_scalar_residual_p99=value[
                "relative_scalar_residual_p99"
            ],
            seam_vertex_count_reference=value["seam_vertex_count_reference"],
            seam_vertex_count_candidate=value["seam_vertex_count_candidate"],
            violations=tuple(value.get("violations", ())),
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", IMPLICIT_MESH_FIDELITY_SCHEMA
            ),
        )


@dataclass(frozen=True, slots=True)
class PeriodicMeshSimplificationResult:
    vertices_fractional: FloatArray
    vertices_cartesian: FloatArray
    faces: IntArray
    target_faces: int
    input_faces: int
    protected_faces: int
    output_faces: int
    component_reports: tuple[MeshSimplificationComponentReport, ...]
    fidelity: ImplicitMeshFidelityReport
    retained_geometry_bytes: int
    estimated_peak_bytes: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = PERIODIC_MESH_SIMPLIFICATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERIODIC_MESH_SIMPLIFICATION_SCHEMA:
            raise GraphAdapterError("Unsupported periodic-mesh-simplification schema.")
        fractional = _readonly(self.vertices_fractional, np.float64, ndim=2, name="vertices_fractional")
        cartesian = _readonly(self.vertices_cartesian, np.float64, ndim=2, name="vertices_cartesian")
        faces = _readonly(self.faces, np.int64, ndim=2, name="faces")
        if fractional.shape != cartesian.shape or fractional.shape[1:] != (3,):
            raise GraphAdapterError("Simplified vertex arrays must align with shape (n, 3).")
        if faces.shape[1:] != (3,):
            raise GraphAdapterError("Simplified faces must have shape (n, 3).")
        object.__setattr__(self, "vertices_fractional", fractional)
        object.__setattr__(self, "vertices_cartesian", cartesian)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(self, "component_reports", tuple(self.component_reports))
        for name in ("target_faces", "input_faces", "protected_faces", "output_faces", "retained_geometry_bytes", "estimated_peak_bytes"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self, *, include_geometry: bool = False) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "target_faces": self.target_faces,
            "input_faces": self.input_faces,
            "protected_faces": self.protected_faces,
            "output_faces": self.output_faces,
            "vertex_count": int(self.vertices_cartesian.shape[0]),
            "retained_geometry_bytes": self.retained_geometry_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "component_reports": [item.to_json_dict() for item in self.component_reports],
            "fidelity": self.fidelity.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_geometry:
            result.update({
                "vertices_fractional": self.vertices_fractional.tolist(),
                "vertices_cartesian": self.vertices_cartesian.tolist(),
                "faces": self.faces.tolist(),
            })
        return result

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "PeriodicMeshSimplificationResult":
        for name in ("vertices_fractional", "vertices_cartesian", "faces"):
            if name not in value:
                raise GraphAdapterError(
                    "Periodic mesh simplification JSON requires geometry arrays; "
                    "serialize with include_geometry=True."
                )
        result = cls(
            vertices_fractional=np.asarray(
                value["vertices_fractional"], dtype=np.float64
            ),
            vertices_cartesian=np.asarray(
                value["vertices_cartesian"], dtype=np.float64
            ),
            faces=np.asarray(value["faces"], dtype=np.int64),
            target_faces=value["target_faces"],
            input_faces=value["input_faces"],
            protected_faces=value["protected_faces"],
            output_faces=value["output_faces"],
            component_reports=tuple(
                MeshSimplificationComponentReport.from_json_dict(item)
                for item in value.get("component_reports", ())
            ),
            fidelity=ImplicitMeshFidelityReport.from_json_dict(value["fidelity"]),
            retained_geometry_bytes=value["retained_geometry_bytes"],
            estimated_peak_bytes=value["estimated_peak_bytes"],
            metadata=value.get("metadata", {}),
            schema_version=value.get(
                "schema_version", PERIODIC_MESH_SIMPLIFICATION_SCHEMA
            ),
        )
        if int(value.get("vertex_count", result.vertices_cartesian.shape[0])) != int(
            result.vertices_cartesian.shape[0]
        ):
            raise GraphAdapterError(
                "Serialized simplification vertex_count does not match geometry."
            )
        return result


def _require_simplifier():
    try:
        import fast_simplification
    except ImportError as exc:  # pragma: no cover
        raise GraphUnsupportedFeatureError(
            "LD9-V2 simplification requires fast-simplification. Install mdstats[interactive]."
        ) from exc
    return fast_simplification


def _component_labels(vertex_count: int, faces: IntArray) -> tuple[int, NDArray[np.int32]]:
    if faces.size == 0:
        return 0, np.empty(vertex_count, dtype=np.int32)
    edges = np.concatenate((faces[:, (0, 1)], faces[:, (1, 2)], faces[:, (2, 0)]), axis=0)
    rows = np.concatenate((edges[:, 0], edges[:, 1]))
    cols = np.concatenate((edges[:, 1], edges[:, 0]))
    graph = coo_matrix(
        (np.ones(rows.size, dtype=np.uint8), (rows, cols)),
        shape=(vertex_count, vertex_count),
    ).tocsr()
    count, labels = connected_components(graph, directed=False, return_labels=True)
    return int(count), np.asarray(labels, dtype=np.int32)


def _extract_component(vertices: FloatArray, faces: IntArray, face_rows: NDArray[np.int64]):
    """Extract indexed component geometry without a full-scene remapping array."""

    local_faces_global = np.asarray(faces[face_rows], dtype=np.int64)
    used = np.unique(local_faces_global)
    local_faces = np.searchsorted(used, local_faces_global)
    return (
        np.ascontiguousarray(vertices[used], dtype=np.float64),
        np.ascontiguousarray(local_faces, dtype=np.int32),
        used,
    )


def _same_topology(first: MeshTopologySummary, second: MeshTopologySummary) -> bool:
    return (
        first.connected_component_count == second.connected_component_count
        and first.boundary_edge_count == second.boundary_edge_count
        and first.nonmanifold_edge_count == second.nonmanifold_edge_count
        and first.euler_characteristic == second.euler_characteristic
    )


class _PeriodicTrilinearSampler:
    def __init__(self, field: Any):
        self.field = field
        self.shape = np.asarray(field.grid_shape, dtype=np.int64)
        self.cell = np.asarray(field.display_cell, dtype=np.float64)
        self.inverse_cell = np.linalg.inv(self.cell)
        self.corners = np.asarray(
            [(i, j, k) for i in (0, 1) for j in (0, 1) for k in (0, 1)],
            dtype=np.int64,
        )

    def sample_and_gradient(self, cartesian: FloatArray) -> tuple[FloatArray, FloatArray]:
        points = np.asarray(cartesian, dtype=np.float64)
        fractional = points @ self.inverse_cell
        logical = fractional * self.shape[None, :]
        base = np.floor(logical).astype(np.int64)
        offset = logical - base
        coordinates = np.mod(
            base[:, None, :] + self.corners[None, :, :], self.shape[None, None, :]
        )
        values = np.asarray(
            self.field.gather_node_values(coordinates.reshape(-1, 3)), dtype=np.float64
        ).reshape(points.shape[0], 8)
        weights = []
        signs = []
        for axis in range(3):
            high = self.corners[:, axis][None, :] == 1
            weights.append(np.where(high, offset[:, axis, None], 1.0 - offset[:, axis, None]))
            signs.append(np.where(high, 1.0, -1.0))
        wx, wy, wz = weights
        density = np.sum(values * wx * wy * wz, axis=1, dtype=np.float64)
        derivative_logical = np.column_stack(
            (
                np.sum(values * signs[0] * wy * wz, axis=1, dtype=np.float64),
                np.sum(values * wx * signs[1] * wz, axis=1, dtype=np.float64),
                np.sum(values * wx * wy * signs[2], axis=1, dtype=np.float64),
            )
        )
        gradient_fractional = derivative_logical * self.shape[None, :]
        gradient_cartesian = gradient_fractional @ self.inverse_cell.T
        return (
            np.ascontiguousarray(density),
            np.ascontiguousarray(gradient_cartesian),
        )

    def project(self, cartesian: FloatArray, *, level: float, options: MeshSimplificationOptions) -> FloatArray:
        result = np.array(cartesian, dtype=np.float64, copy=True, order="C")
        for _ in range(options.projection_iterations):
            values, gradients = self.sample_and_gradient(result)
            norm2 = np.einsum("ij,ij->i", gradients, gradients)
            valid = norm2 > np.finfo(np.float64).tiny
            if not np.any(valid):
                break
            steps = np.zeros_like(result)
            steps[valid] = ((values[valid] - float(level)) / norm2[valid])[:, None] * gradients[valid]
            lengths = np.linalg.norm(steps, axis=1)
            factors = np.minimum(
                1.0,
                options.projection_max_step / np.maximum(lengths, np.finfo(np.float64).tiny),
            )
            result -= steps * factors[:, None]
        return np.ascontiguousarray(result)


def _normal_errors(points: FloatArray, face_normals: FloatArray, sampler: _PeriodicTrilinearSampler) -> NDArray[np.float64]:
    _values, gradients = sampler.sample_and_gradient(points)
    norms = np.linalg.norm(gradients, axis=1)
    valid = norms > np.finfo(np.float64).tiny
    errors = np.full(points.shape[0], 90.0, dtype=np.float64)
    if np.any(valid):
        unit = gradients[valid] / norms[valid, None]
        dots = np.clip(np.abs(np.einsum("ij,ij->i", face_normals[valid], unit)), 0.0, 1.0)
        errors[valid] = np.degrees(np.arccos(dots))
    return errors


def _seam_mask(vertices_fractional: FloatArray, tolerance: float) -> NDArray[np.bool_]:
    return np.any(
        (np.abs(vertices_fractional) <= tolerance)
        | (np.abs(vertices_fractional - 1.0) <= tolerance),
        axis=1,
    )


def evaluate_implicit_mesh_fidelity(
    field: Any,
    reference_vertices: FloatArray,
    reference_faces: IntArray,
    candidate_vertices: FloatArray,
    candidate_faces: IntArray,
    *,
    contour_level: float,
    options: MeshSimplificationOptions,
) -> ImplicitMeshFidelityReport:
    """Validate topology, sampled geometry, and implicit-field agreement."""

    sampler = _PeriodicTrilinearSampler(field)
    reference_topology = summarize_mesh_topology(reference_vertices, reference_faces)
    candidate_topology = summarize_mesh_topology(candidate_vertices, candidate_faces)
    sample_count = min(options.max_samples, max(1_000, int(candidate_faces.shape[0])))
    ref_points, ref_normals = sample_mesh_surface(
        reference_vertices, reference_faces, max_samples=sample_count, random_seed=17
    )
    ref_points_check, _ref_normals_check = sample_mesh_surface(
        reference_vertices, reference_faces, max_samples=sample_count, random_seed=29
    )
    cand_points, cand_normals = sample_mesh_surface(
        candidate_vertices, candidate_faces, max_samples=sample_count, random_seed=23
    )
    ref_tree = cKDTree(ref_points)
    cand_tree = cKDTree(cand_points)
    cand_to_ref = ref_tree.query(cand_points, k=1)[0]
    ref_to_cand = cand_tree.query(ref_points, k=1)[0]
    symmetric = np.concatenate((cand_to_ref, ref_to_cand))
    ref_check_tree = cKDTree(ref_points_check)
    baseline_forward = ref_check_tree.query(ref_points, k=1)[0]
    baseline_reverse = ref_tree.query(ref_points_check, k=1)[0]
    baseline_symmetric = np.concatenate((baseline_forward, baseline_reverse))
    values, gradients = sampler.sample_and_gradient(cand_points)
    gradient_norms = np.linalg.norm(gradients, axis=1)
    residual = np.abs(values - float(contour_level))
    displacement = residual / np.maximum(gradient_norms, np.finfo(np.float64).tiny)
    relative_residual = residual / max(abs(float(contour_level)), np.finfo(np.float64).tiny)
    reference_normal = _normal_errors(ref_points, ref_normals, sampler)
    candidate_normal = _normal_errors(cand_points, cand_normals, sampler)
    ref_normal_p99 = float(np.quantile(reference_normal, 0.99))
    cand_normal_p99 = float(np.quantile(candidate_normal, 0.99))
    normal_degradation = max(0.0, cand_normal_p99 - ref_normal_p99)
    inverse = np.linalg.inv(np.asarray(field.display_cell, dtype=np.float64))
    ref_fractional = np.asarray(reference_vertices, dtype=np.float64) @ inverse
    cand_fractional = np.asarray(candidate_vertices, dtype=np.float64) @ inverse
    ref_seam = int(np.count_nonzero(_seam_mask(ref_fractional, options.seam_tolerance_fractional)))
    cand_seam = int(np.count_nonzero(_seam_mask(cand_fractional, options.seam_tolerance_fractional)))
    distance_p99 = float(np.quantile(symmetric, 0.99))
    distance_max = float(np.max(symmetric))
    baseline_p99 = float(np.quantile(baseline_symmetric, 0.99))
    baseline_max = float(np.max(baseline_symmetric))
    excess_p99 = max(0.0, distance_p99 - baseline_p99)
    excess_max = max(0.0, distance_max - baseline_max)
    displacement_p99 = float(np.quantile(displacement, 0.99))
    displacement_max = float(np.max(displacement))
    relative_p99 = float(np.quantile(relative_residual, 0.99))
    violations: list[str] = []
    if options.require_component_count and (
        reference_topology.connected_component_count != candidate_topology.connected_component_count
    ):
        violations.append("component_count_changed")
    if options.require_euler_characteristic and (
        reference_topology.euler_characteristic != candidate_topology.euler_characteristic
    ):
        violations.append("euler_characteristic_changed")
    if options.require_boundary_edge_count and (
        reference_topology.boundary_edge_count != candidate_topology.boundary_edge_count
    ):
        violations.append("boundary_edge_count_changed")
    if candidate_topology.nonmanifold_edge_count != reference_topology.nonmanifold_edge_count:
        violations.append("nonmanifold_edge_count_changed")
    if options.require_seam_preservation and ref_seam != cand_seam:
        violations.append("seam_vertex_count_changed")
    if excess_p99 > options.max_surface_error_p99:
        violations.append(f"surface_error_p99_excess={excess_p99:.9g}")
    if displacement_max > options.max_surface_error_max:
        violations.append(f"implicit_displacement_max={displacement_max:.9g}")
    if displacement_p99 > options.max_implicit_displacement_p99:
        violations.append(f"implicit_displacement_p99={displacement_p99:.9g}")
    if normal_degradation > options.max_normal_degradation_degrees:
        violations.append(f"normal_degradation={normal_degradation:.9g}")
    if relative_p99 > options.max_relative_scalar_residual_p99:
        violations.append(f"relative_scalar_residual_p99={relative_p99:.9g}")
    return ImplicitMeshFidelityReport(
        reference_topology=reference_topology,
        candidate_topology=candidate_topology,
        sample_count=sample_count,
        symmetric_distance_p99=distance_p99,
        symmetric_distance_max=distance_max,
        reference_sampling_distance_p99=baseline_p99,
        reference_sampling_distance_max=baseline_max,
        excess_surface_distance_p99=excess_p99,
        excess_surface_distance_max=excess_max,
        implicit_displacement_p99=displacement_p99,
        implicit_displacement_max=displacement_max,
        reference_normal_p99_degrees=ref_normal_p99,
        candidate_normal_p99_degrees=cand_normal_p99,
        normal_degradation_degrees=normal_degradation,
        relative_scalar_residual_p99=relative_p99,
        seam_vertex_count_reference=ref_seam,
        seam_vertex_count_candidate=cand_seam,
        violations=tuple(violations),
        metadata={
            "surface_distance": "symmetric_area_sampled_nearest_excess_over_reference_sampling_v1",
            "implicit_distance": "trilinear_residual_over_gradient_v1",
            "normal_metric": "triangle_to_trilinear_gradient_p99_degradation_v1",
        },
    )


def _has_zero_area_triangles(vertices: FloatArray, faces: Any) -> bool:
    triangles = np.asarray(vertices, dtype=np.float64)[np.asarray(faces, dtype=np.int64)]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    squared = np.einsum("ij,ij->i", cross, cross)
    scale = max(1.0, float(np.max(np.linalg.norm(vertices, axis=1), initial=1.0)))
    return bool(np.any(squared <= (1.0e-14 * scale * scale) ** 2))


def _simplify_component(
    vertices: FloatArray,
    faces: NDArray[np.int32],
    target_faces: int,
    *,
    options: MeshSimplificationOptions,
    sampler: _PeriodicTrilinearSampler,
    contour_level: float,
) -> tuple[FloatArray, NDArray[np.int32], int, str | None]:
    """Return the lowest topology-preserving QEM result found in a bounded search.

    The previous V2 implementation tried the requested target and, after one
    topology failure, accepted the first midpoint toward the raw mesh.  For
    aggressive scene-wide budgets that could retain roughly half of every large
    component even when a much smaller topology-preserving solution existed.
    V3 keeps an explicit failing/passing bracket and performs a bounded binary
    search.  Scientific fidelity is still evaluated globally after components
    are reassembled.
    """

    simplifier = _require_simplifier()
    original_topology = summarize_mesh_topology(vertices, faces)
    requested = max(
        options.min_component_faces,
        min(int(target_faces), int(faces.shape[0])),
    )
    if requested >= faces.shape[0]:
        return np.array(vertices, copy=True), np.array(faces, copy=True), 0, None

    low_failed = requested - 1
    high_passed = int(faces.shape[0])
    candidate_target = requested
    best_vertices = np.array(vertices, copy=True)
    best_faces = np.array(faces, copy=True)
    best_target = high_passed
    rejection: str | None = None
    attempts = 0

    while attempts < options.max_attempts and candidate_target < high_passed:
        attempts += 1
        simplified_vertices, simplified_faces = simplifier.simplify(
            np.array(vertices, dtype=np.float64, copy=True, order="C"),
            np.array(faces, dtype=np.int32, copy=True, order="C"),
            target_count=int(candidate_target),
            agg=options.aggressiveness,
        )
        unprojected_vertices = np.asarray(simplified_vertices, dtype=np.float64)
        simplified_faces = np.asarray(simplified_faces, dtype=np.int32)
        topology = summarize_mesh_topology(unprojected_vertices, simplified_faces)
        if _same_topology(original_topology, topology):
            projected_vertices = sampler.project(
                unprojected_vertices,
                level=contour_level,
                options=options,
            )
            if _has_zero_area_triangles(projected_vertices, simplified_faces):
                projected_vertices = unprojected_vertices
            best_vertices = np.asarray(projected_vertices, dtype=np.float64)
            best_faces = np.asarray(simplified_faces, dtype=np.int32)
            best_target = int(candidate_target)
            high_passed = int(candidate_target)
            rejection = None
        else:
            low_failed = int(candidate_target)
            rejection = "component_topology_changed"

        if high_passed - low_failed <= 1:
            break
        candidate_target = (low_failed + high_passed) // 2

    if best_target >= int(faces.shape[0]):
        return (
            np.array(vertices, copy=True),
            np.array(faces, copy=True),
            attempts,
            rejection,
        )
    return best_vertices, best_faces, attempts, rejection



def _periodic_quotient_mesh(
    fractional: FloatArray,
    faces: IntArray,
    *,
    tolerance: float,
) -> tuple[FloatArray, IntArray]:
    """Merge paired canonical-seam copies into one periodic quotient mesh."""

    canonical = np.asarray(fractional, dtype=np.float64).copy()
    canonical[np.abs(canonical) <= tolerance] = 0.0
    canonical[np.abs(canonical - 1.0) <= tolerance] = 0.0
    keys = np.rint(canonical / tolerance).astype(np.int64)
    _unique_keys, first, inverse = np.unique(
        keys, axis=0, return_index=True, return_inverse=True
    )
    quotient_vertices = np.ascontiguousarray(canonical[first], dtype=np.float64)
    quotient_faces = np.asarray(inverse[np.asarray(faces, dtype=np.int64)], dtype=np.int64)
    valid = (
        (quotient_faces[:, 0] != quotient_faces[:, 1])
        & (quotient_faces[:, 1] != quotient_faces[:, 2])
        & (quotient_faces[:, 2] != quotient_faces[:, 0])
    )
    quotient_faces = quotient_faces[valid]
    sorted_faces = np.sort(quotient_faces, axis=1)
    _unique_faces, retained = np.unique(sorted_faces, axis=0, return_index=True)
    quotient_faces = np.ascontiguousarray(
        quotient_faces[np.sort(retained)], dtype=np.int64
    )
    used = np.unique(quotient_faces)
    remap = np.full(quotient_vertices.shape[0], -1, dtype=np.int64)
    remap[used] = np.arange(used.size, dtype=np.int64)
    return (
        np.ascontiguousarray(quotient_vertices[used], dtype=np.float64),
        np.ascontiguousarray(remap[quotient_faces], dtype=np.int64),
    )


def _lift_periodic_quotient_components(
    canonical_fractional: FloatArray,
    faces: IntArray,
    *,
    tolerance: float,
) -> tuple[FloatArray, NDArray[np.int32]]:
    """Lift each nonwinding quotient component into a continuous chart.

    SciPy constructs one spanning forest in compiled code.  Python then visits
    each used vertex once (rather than every mesh edge), and a final vectorized
    residual check certifies that all non-tree edges are consistent.
    """

    vertices = np.asarray(canonical_fractional, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    component_count, labels = _component_labels(vertices.shape[0], face_array)
    edges = np.concatenate(
        (face_array[:, (0, 1)], face_array[:, (1, 2)], face_array[:, (2, 0)]),
        axis=0,
    )
    edges.sort(axis=1)
    edges = np.unique(edges, axis=0)
    vertex_count = vertices.shape[0]
    roots = np.asarray(
        [int(np.flatnonzero(labels == index)[0]) for index in range(component_count)],
        dtype=np.int64,
    )
    super_root = vertex_count
    rows = np.concatenate(
        (edges[:, 0], edges[:, 1], roots, np.full(roots.size, super_root, dtype=np.int64))
    )
    columns = np.concatenate(
        (edges[:, 1], edges[:, 0], np.full(roots.size, super_root, dtype=np.int64), roots)
    )
    forest_graph = coo_matrix(
        (np.ones(rows.size, dtype=np.uint8), (rows, columns)),
        shape=(vertex_count + 1, vertex_count + 1),
    ).tocsr()
    order, predecessors = breadth_first_order(
        forest_graph, super_root, directed=False, return_predecessors=True
    )
    lifted = np.empty_like(vertices)
    for vertex_value in order[1:]:
        vertex = int(vertex_value)
        predecessor = int(predecessors[vertex])
        if predecessor == super_root:
            lifted[vertex] = vertices[vertex]
            continue
        delta = vertices[vertex] - vertices[predecessor]
        delta -= np.rint(delta)
        lifted[vertex] = lifted[predecessor] + delta
    edge_delta = vertices[edges[:, 1]] - vertices[edges[:, 0]]
    edge_delta -= np.rint(edge_delta)
    residual = (lifted[edges[:, 1]] - lifted[edges[:, 0]]) - edge_delta
    if residual.size and float(np.max(np.abs(residual))) > tolerance:
        raise GraphComplexityError(
            "Periodic quotient component has nonzero winding and cannot use "
            "lifted closed-surface simplification."
        )
    return np.ascontiguousarray(lifted, dtype=np.float64), labels


def _canonicalize_lifted_components(
    component_vertices_fractional: list[FloatArray],
    component_faces: list[IntArray],
    *,
    display_cell: FloatArray,
) -> tuple[FloatArray, FloatArray, IntArray, int, int]:
    """Clip simplified lifted components back into one canonical periodic cell."""

    from .density_sparse_mesh import (
        _canonicalize_triangles,
        _clip_triangle_to_unit_cube,
        _component_image_shifts,
    )

    triangles: list[np.ndarray] = []
    for vertices, faces in zip(
        component_vertices_fractional, component_faces, strict=True
    ):
        for shift in _component_image_shifts(vertices):
            shifted = vertices + np.asarray(shift, dtype=np.float64)[None, :]
            triangle_array = shifted[np.asarray(faces, dtype=np.int64)]
            minimum = np.min(triangle_array, axis=1)
            maximum = np.max(triangle_array, axis=1)
            outside = np.any((maximum < 0.0) | (minimum > 1.0), axis=1)
            inside = np.all((minimum >= 0.0) & (maximum <= 1.0), axis=1)
            for triangle in triangle_array[inside]:
                triangles.append(np.asarray(triangle, dtype=np.float64))
            for triangle in triangle_array[~outside & ~inside]:
                triangles.extend(_clip_triangle_to_unit_cube(triangle))
    return _canonicalize_triangles(triangles, np.asarray(display_cell, dtype=np.float64))


def _simplify_periodic_quotient(
    field: Any,
    fractional: FloatArray,
    cartesian: FloatArray,
    faces: IntArray,
    *,
    contour_level: float,
    target_faces: int,
    options: MeshSimplificationOptions,
) -> tuple[
    FloatArray,
    FloatArray,
    IntArray,
    tuple[MeshSimplificationComponentReport, ...],
    int,
    int,
    dict[str, Any],
]:
    """Simplify seam-crossing nonwinding clouds as closed lifted surfaces."""

    quotient_fractional, quotient_faces = _periodic_quotient_mesh(
        fractional,
        faces,
        tolerance=max(options.seam_tolerance_fractional, 1.0e-12),
    )
    lifted_fractional, labels = _lift_periodic_quotient_components(
        quotient_fractional,
        quotient_faces,
        tolerance=max(options.seam_tolerance_fractional * 10.0, 1.0e-10),
    )
    lifted_cartesian = np.ascontiguousarray(
        lifted_fractional @ np.asarray(field.display_cell, dtype=np.float64),
        dtype=np.float64,
    )
    component_count = int(np.max(labels)) + 1 if labels.size else 0
    face_labels = labels[quotient_faces[:, 0]]
    component_rows = [
        np.flatnonzero(face_labels == component_index)
        for component_index in range(component_count)
    ]
    protected = [int(rows.size) <= options.min_component_faces for rows in component_rows]
    protected_faces = sum(
        int(rows.size)
        for rows, is_protected in zip(component_rows, protected, strict=True)
        if is_protected
    )
    reducible_indices = [
        index for index, is_protected in enumerate(protected) if not is_protected
    ]
    minimum = protected_faces + sum(
        min(options.min_component_faces, int(component_rows[index].size))
        for index in reducible_indices
    )
    resolved_target = int(target_faces)
    if resolved_target < minimum:
        if options.hard_target:
            raise GraphComplexityError(
                f"Requested target_faces={resolved_target} is below the lifted periodic "
                f"topology-safe minimum {minimum}."
            )
        resolved_target = minimum
    reducible_target = max(0, resolved_target - protected_faces)
    minima = {
        index: min(options.min_component_faces, int(component_rows[index].size))
        for index in reducible_indices
    }
    capacities = {
        index: int(component_rows[index].size) - minima[index]
        for index in reducible_indices
    }
    remaining = max(0, reducible_target - sum(minima.values()))
    capacity_sum = sum(capacities.values())
    component_targets: dict[int, int] = {}
    fractions: dict[int, float] = {}
    for index in reducible_indices:
        raw = 0.0 if capacity_sum <= 0 else remaining * capacities[index] / capacity_sum
        fractions[index] = raw
        component_targets[index] = minima[index] + min(
            capacities[index], int(np.floor(raw))
        )
    leftover = reducible_target - sum(component_targets.values())
    for index in sorted(
        reducible_indices,
        key=lambda item: (
            fractions[item] - np.floor(fractions[item]),
            capacities[item],
            -item,
        ),
        reverse=True,
    ):
        if leftover <= 0:
            break
        if component_targets[index] < int(component_rows[index].size):
            component_targets[index] += 1
            leftover -= 1
    sampler = _PeriodicTrilinearSampler(field)
    output_fractional: list[FloatArray] = []
    output_faces: list[IntArray] = []
    reports: list[MeshSimplificationComponentReport] = []
    transient_peak = 0
    inverse_cell = np.linalg.inv(np.asarray(field.display_cell, dtype=np.float64))
    for component_index, (rows, is_protected) in enumerate(
        zip(component_rows, protected, strict=True)
    ):
        local_vertices, local_faces, _used = _extract_component(
            lifted_cartesian, quotient_faces, rows
        )
        if is_protected:
            simplified_vertices = local_vertices
            simplified_faces = local_faces
            attempts = 0
            rejection = None
            component_target = int(rows.size)
            accepted = False
        else:
            component_target = component_targets[component_index]
            simplified_vertices, simplified_faces, attempts, rejection = _simplify_component(
                local_vertices,
                local_faces,
                component_target,
                options=options,
                sampler=sampler,
                contour_level=float(contour_level),
            )
            accepted = int(simplified_faces.shape[0]) < int(local_faces.shape[0])
        component_fractional = np.ascontiguousarray(
            np.asarray(simplified_vertices, dtype=np.float64) @ inverse_cell,
            dtype=np.float64,
        )
        output_fractional.append(component_fractional)
        output_faces.append(np.asarray(simplified_faces, dtype=np.int64))
        transient_peak = max(
            transient_peak,
            int(
                local_vertices.nbytes
                + local_faces.nbytes
                + np.asarray(simplified_vertices).nbytes
                + np.asarray(simplified_faces).nbytes
            ),
        )
        reports.append(
            MeshSimplificationComponentReport(
                component_index=component_index,
                input_faces=int(rows.size),
                target_faces=component_target,
                output_faces=int(simplified_faces.shape[0]),
                protected=is_protected,
                accepted=accepted,
                attempts=attempts,
                rejection_reason=rejection,
            )
        )
    (
        canonical_fractional,
        canonical_cartesian,
        canonical_faces,
        duplicates_removed,
        degenerates_removed,
    ) = _canonicalize_lifted_components(
        output_fractional,
        output_faces,
        display_cell=np.asarray(field.display_cell, dtype=np.float64),
    )
    return (
        canonical_fractional,
        canonical_cartesian,
        canonical_faces,
        tuple(reports),
        protected_faces,
        transient_peak,
        {
            "simplification": "periodic_lifted_component_qem_v1",
            "periodic_quotient_component_count": component_count,
            "canonical_duplicate_faces_removed": duplicates_removed,
            "canonical_degenerate_faces_removed": degenerates_removed,
        },
    )

def simplify_periodic_density_mesh(
    field: Any,
    vertices_fractional: Any,
    vertices_cartesian: Any,
    faces: Any,
    *,
    contour_level: float,
    options: MeshSimplificationOptions | None = None,
) -> PeriodicMeshSimplificationResult:
    """Simplify periodic components while preserving physical topology and valid seams."""

    policy = MeshSimplificationOptions() if options is None else options
    if not isinstance(policy, MeshSimplificationOptions):
        raise TypeError("options must be MeshSimplificationOptions or None.")
    fractional = np.asarray(vertices_fractional, dtype=np.float64)
    cartesian = np.asarray(vertices_cartesian, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    if fractional.shape != cartesian.shape or fractional.ndim != 2 or fractional.shape[1] != 3:
        raise GraphAdapterError("Vertex arrays must align with shape (n, 3).")
    if face_array.ndim != 2 or face_array.shape[1] != 3:
        raise GraphAdapterError("faces must have shape (n, 3).")
    input_faces = int(face_array.shape[0])
    target_faces = input_faces if policy.target_faces is None else min(policy.target_faces, input_faces)
    if not policy.enabled or target_faces >= input_faces:
        fidelity = evaluate_implicit_mesh_fidelity(
            field, cartesian, face_array, cartesian, face_array,
            contour_level=contour_level, options=policy,
        )
        retained = int(fractional.nbytes + cartesian.nbytes + face_array.nbytes)
        return PeriodicMeshSimplificationResult(
            vertices_fractional=fractional,
            vertices_cartesian=cartesian,
            faces=face_array,
            target_faces=target_faces,
            input_faces=input_faces,
            protected_faces=input_faces,
            output_faces=input_faces,
            component_reports=(),
            fidelity=fidelity,
            retained_geometry_bytes=retained,
            estimated_peak_bytes=2 * retained,
            metadata={"simplification": "disabled_or_unnecessary"},
        )
    seam_vertices = _seam_mask(fractional, policy.seam_tolerance_fractional)
    if np.any(seam_vertices):
        (
            candidate_fractional,
            candidate_cartesian,
            candidate_faces,
            quotient_reports,
            quotient_protected_faces,
            quotient_transient_peak,
            quotient_metadata,
        ) = _simplify_periodic_quotient(
            field,
            fractional,
            cartesian,
            face_array,
            contour_level=float(contour_level),
            target_faces=target_faces,
            options=policy,
        )
        periodic_fidelity_policy = replace(
            policy,
            require_component_count=False,
            require_euler_characteristic=False,
            require_boundary_edge_count=False,
            require_seam_preservation=False,
        )
        from .density_sparse_mesh import validate_periodic_canonical_mesh

        canonical_topology = validate_periodic_canonical_mesh(
            candidate_fractional,
            candidate_cartesian,
            candidate_faces,
            display_cell=np.asarray(field.display_cell, dtype=np.float64),
            logical_grid_shape=tuple(int(value) for value in field.grid_shape),
        )
        canonical_valid = (
            canonical_topology.interior_edge_incidence_failures == 0
            and canonical_topology.unpaired_boundary_edge_count == 0
            and canonical_topology.maximum_boundary_seam_mismatch
            <= 1.0e-10
            * max(float(np.linalg.norm(vector)) for vector in field.display_cell)
        )
        if not canonical_valid:
            if policy.hard_target:
                raise GraphComplexityError(
                    "Periodic-quotient simplification produced invalid canonical "
                    "incidence or seam pairing."
                )
            candidate_fractional = np.ascontiguousarray(fractional, dtype=np.float64)
            candidate_cartesian = np.ascontiguousarray(cartesian, dtype=np.float64)
            candidate_faces = np.ascontiguousarray(face_array, dtype=np.int64)
            quotient_reports = tuple(
                replace(
                    report,
                    output_faces=report.input_faces,
                    accepted=False,
                    rejection_reason="canonical_reconstruction_invalid",
                )
                for report in quotient_reports
            )
            quotient_protected_faces = input_faces
            quotient_metadata = {
                **quotient_metadata,
                "canonical_reconstruction_fallback": True,
                "canonical_topology": canonical_topology.to_json_dict(),
            }
        fidelity = evaluate_implicit_mesh_fidelity(
            field,
            cartesian,
            face_array,
            candidate_cartesian,
            candidate_faces,
            contour_level=float(contour_level),
            options=periodic_fidelity_policy,
        )
        if not fidelity.passed:
            raise GraphComplexityError(
                "Simplified periodic-quotient mesh failed fidelity constraints: "
                + ", ".join(fidelity.violations)
            )
        output_face_count = int(candidate_faces.shape[0])
        if policy.hard_target and output_face_count > target_faces:
            raise GraphComplexityError(
                f"Periodic-quotient simplification retained {output_face_count} faces, "
                f"exceeding hard target_faces={target_faces}."
            )
        retained = int(
            candidate_fractional.nbytes
            + candidate_cartesian.nbytes
            + candidate_faces.nbytes
        )
        return PeriodicMeshSimplificationResult(
            vertices_fractional=candidate_fractional,
            vertices_cartesian=candidate_cartesian,
            faces=candidate_faces,
            target_faces=target_faces,
            input_faces=input_faces,
            protected_faces=quotient_protected_faces,
            output_faces=output_face_count,
            component_reports=quotient_reports,
            fidelity=fidelity,
            retained_geometry_bytes=retained,
            estimated_peak_bytes=int(
                retained
                + quotient_transient_peak
                + cartesian.nbytes
                + face_array.nbytes
            ),
            metadata={
                **quotient_metadata,
                "projection": "periodic_trilinear_newton_v1",
                "quadric_error_source": "Garland-Heckbert-1997",
            },
        )
    component_count, labels = _component_labels(cartesian.shape[0], face_array)
    face_labels = labels[face_array[:, 0]]
    component_face_rows = [np.flatnonzero(face_labels == index) for index in range(component_count)]
    protected_flags: list[bool] = []
    protected_faces = 0
    reducible_faces = 0
    for rows in component_face_rows:
        used = np.unique(face_array[rows])
        protected = bool(np.any(seam_vertices[used])) or int(rows.size) <= policy.min_component_faces
        protected_flags.append(protected)
        if protected:
            protected_faces += int(rows.size)
        else:
            reducible_faces += int(rows.size)
    minimum_achievable = protected_faces + sum(
        min(policy.min_component_faces, int(rows.size))
        for rows, protected in zip(component_face_rows, protected_flags, strict=True)
        if not protected
    )
    if target_faces < minimum_achievable:
        if policy.hard_target:
            raise GraphComplexityError(
                f"Requested target_faces={target_faces} is below the periodic/topology-safe "
                f"minimum {minimum_achievable}."
            )
        target_faces = minimum_achievable
    reducible_target = max(0, target_faces - protected_faces)
    reducible_indices = [
        index for index, protected in enumerate(protected_flags) if not protected
    ]
    component_targets: dict[int, int] = {}
    if reducible_indices:
        minima = {
            index: min(policy.min_component_faces, int(component_face_rows[index].size))
            for index in reducible_indices
        }
        # Reserve one face per reducible component when possible because external
        # QEM implementations may terminate one triangle above the requested count.
        allocation_total = max(
            sum(minima.values()),
            reducible_target - len(reducible_indices),
        )
        capacities = {
            index: int(component_face_rows[index].size) - minima[index]
            for index in reducible_indices
        }
        remaining = allocation_total - sum(minima.values())
        capacity_sum = sum(capacities.values())
        raw_extra: dict[int, float] = {}
        for index in reducible_indices:
            raw_extra[index] = (
                0.0 if capacity_sum <= 0 else remaining * capacities[index] / capacity_sum
            )
            component_targets[index] = minima[index] + min(
                capacities[index], int(np.floor(raw_extra[index]))
            )
        leftover = allocation_total - sum(component_targets.values())
        for index in sorted(
            reducible_indices,
            key=lambda item: (
                raw_extra[item] - np.floor(raw_extra[item]), capacities[item], -item
            ),
            reverse=True,
        ):
            if leftover <= 0:
                break
            if component_targets[index] < int(component_face_rows[index].size):
                component_targets[index] += 1
                leftover -= 1
    sampler = _PeriodicTrilinearSampler(field)
    output_vertices: list[FloatArray] = []
    output_faces: list[IntArray] = []
    reports: list[MeshSimplificationComponentReport] = []
    vertex_offset = 0
    transient_peak = 0
    for component_index, (rows, protected) in enumerate(
        zip(component_face_rows, protected_flags, strict=True)
    ):
        local_vertices, local_faces, _used = _extract_component(cartesian, face_array, rows)
        if protected:
            simplified_vertices = local_vertices
            simplified_faces = local_faces
            attempts = 0
            rejection = None
            component_target = int(rows.size)
            accepted = False
        else:
            component_target = component_targets[component_index]
            simplified_vertices, simplified_faces, attempts, rejection = _simplify_component(
                local_vertices,
                local_faces,
                component_target,
                options=policy,
                sampler=sampler,
                contour_level=float(contour_level),
            )
            accepted = int(simplified_faces.shape[0]) < int(local_faces.shape[0])
        output_vertices.append(np.asarray(simplified_vertices, dtype=np.float64))
        output_faces.append(np.asarray(simplified_faces, dtype=np.int64) + vertex_offset)
        vertex_offset += int(simplified_vertices.shape[0])
        transient_peak = max(
            transient_peak,
            int(local_vertices.nbytes + local_faces.nbytes + simplified_vertices.nbytes + simplified_faces.nbytes),
        )
        reports.append(
            MeshSimplificationComponentReport(
                component_index=component_index,
                input_faces=int(rows.size),
                target_faces=component_target,
                output_faces=int(simplified_faces.shape[0]),
                protected=protected,
                accepted=accepted,
                attempts=attempts,
                rejection_reason=rejection,
            )
        )
    candidate_cartesian = np.ascontiguousarray(np.vstack(output_vertices), dtype=np.float64)
    candidate_faces = np.ascontiguousarray(np.vstack(output_faces), dtype=np.int64)
    candidate_fractional = np.ascontiguousarray(
        candidate_cartesian @ np.linalg.inv(np.asarray(field.display_cell, dtype=np.float64)),
        dtype=np.float64,
    )
    candidate_fractional[np.abs(candidate_fractional) <= policy.seam_tolerance_fractional] = 0.0
    candidate_fractional[
        np.abs(candidate_fractional - 1.0) <= policy.seam_tolerance_fractional
    ] = 1.0
    fidelity = evaluate_implicit_mesh_fidelity(
        field,
        cartesian,
        face_array,
        candidate_cartesian,
        candidate_faces,
        contour_level=float(contour_level),
        options=policy,
    )
    if not fidelity.passed:
        raise GraphComplexityError(
            "Simplified mesh failed fidelity constraints: " + ", ".join(fidelity.violations)
        )
    output_face_count = int(candidate_faces.shape[0])
    if policy.hard_target and output_face_count > target_faces:
        raise GraphComplexityError(
            f"Topology-safe simplification retained {output_face_count} faces, exceeding "
            f"hard target_faces={target_faces}."
        )
    retained = int(candidate_fractional.nbytes + candidate_cartesian.nbytes + candidate_faces.nbytes)
    return PeriodicMeshSimplificationResult(
        vertices_fractional=candidate_fractional,
        vertices_cartesian=candidate_cartesian,
        faces=candidate_faces,
        target_faces=target_faces,
        input_faces=input_faces,
        protected_faces=protected_faces,
        output_faces=output_face_count,
        component_reports=tuple(reports),
        fidelity=fidelity,
        retained_geometry_bytes=retained,
        estimated_peak_bytes=int(retained + transient_peak + cartesian.nbytes + face_array.nbytes),
        metadata={
            "simplification": "periodic_component_qem_v1",
            "seam_policy": "protect_entire_seam_touching_component_v1",
            "projection": "periodic_trilinear_newton_v1",
            "quadric_error_source": "Garland-Heckbert-1997",
        },
    )


def presimplify_closed_tile_components(
    vertices_fractional: Any,
    faces: Any,
    protected_vertex_mask: Any,
    vertex_keys: Any,
    *,
    display_cell: Any,
    namespace: int,
    options: MeshSimplificationOptions,
) -> tuple[FloatArray, IntArray, IntArray, dict[str, int]]:
    """Reduce tile-interior closed components without touching shared boundaries.

    Components containing any protected tile-boundary vertex are copied exactly.
    This makes the operation safe for streaming before deterministic inter-tile
    logical-edge assembly.
    """

    fractional = np.asarray(vertices_fractional, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    protected_mask = np.asarray(protected_vertex_mask, dtype=bool)
    if protected_mask.shape != (fractional.shape[0],):
        raise GraphAdapterError("protected_vertex_mask must match the tile vertex count.")
    key_array = np.asarray(vertex_keys, dtype=np.int64)
    if key_array.shape != (fractional.shape[0], 4):
        raise GraphAdapterError("vertex_keys must have shape (n_vertices, 4).")
    # Tile-local reduction is a transient-memory optimization for large components.
    # Applying aggressive QEM to tiny tile meshes adds no useful memory reduction and
    # can amplify vertex-welding sensitivity during later canonical assembly.
    local_face_threshold = max(1_024, 4 * options.min_component_faces)
    if (
        not options.local_presimplification
        or face_array.shape[0] <= local_face_threshold
    ):
        return (
            np.ascontiguousarray(fractional),
            np.ascontiguousarray(face_array),
            np.ascontiguousarray(key_array),
            {"attempted_components": 0, "accepted_components": 0, "input_faces": int(face_array.shape[0]), "output_faces": int(face_array.shape[0])},
        )
    cell = np.asarray(display_cell, dtype=np.float64)
    inverse = np.linalg.inv(cell)
    cartesian = fractional @ cell
    count, labels = _component_labels(fractional.shape[0], face_array)
    face_labels = labels[face_array[:, 0]]
    output_vertices: list[np.ndarray] = []
    output_faces: list[np.ndarray] = []
    output_keys: list[np.ndarray] = []
    offset = 0
    attempted = 0
    accepted = 0
    for component_index in range(count):
        rows = np.flatnonzero(face_labels == component_index)
        local_vertices, local_faces, used = _extract_component(cartesian, face_array, rows)
        is_protected = bool(np.any(protected_mask[used])) or int(rows.size) <= options.min_component_faces
        if is_protected:
            simplified_vertices = local_vertices
            simplified_faces = local_faces
            keys = np.ascontiguousarray(key_array[used])
        else:
            attempted += 1
            target = max(
                options.min_component_faces,
                min(int(rows.size), int(round(rows.size * options.local_target_fraction))),
            )
            simplifier = _require_simplifier()
            simplified_vertices, simplified_faces = simplifier.simplify(
                np.array(local_vertices, dtype=np.float64, copy=True, order="C"),
                np.array(local_faces, dtype=np.int32, copy=True, order="C"),
                target_count=target,
                agg=options.aggressiveness,
            )
            before = summarize_mesh_topology(local_vertices, local_faces)
            after = summarize_mesh_topology(simplified_vertices, simplified_faces)
            if (
                not _same_topology(before, after)
                or _has_zero_area_triangles(
                    np.asarray(simplified_vertices, dtype=np.float64), simplified_faces
                )
            ):
                simplified_vertices = local_vertices
                simplified_faces = local_faces
                keys = np.ascontiguousarray(key_array[used])
            else:
                accepted += 1
                keys = np.column_stack(
                    (
                        np.full(simplified_vertices.shape[0], 5, dtype=np.int64),
                        np.full(
                            simplified_vertices.shape[0], int(namespace), dtype=np.int64
                        ),
                        np.full(
                            simplified_vertices.shape[0],
                            int(component_index),
                            dtype=np.int64,
                        ),
                        np.arange(simplified_vertices.shape[0], dtype=np.int64),
                    )
                )
        simplified_fractional = np.asarray(simplified_vertices, dtype=np.float64) @ inverse
        output_vertices.append(simplified_fractional)
        output_faces.append(np.asarray(simplified_faces, dtype=np.int64) + offset)
        output_keys.append(np.asarray(keys, dtype=np.int64))
        offset += int(simplified_fractional.shape[0])
    vertices_out = np.ascontiguousarray(np.vstack(output_vertices), dtype=np.float64)
    faces_out = np.ascontiguousarray(np.vstack(output_faces), dtype=np.int64)
    return (
        vertices_out,
        faces_out,
        np.ascontiguousarray(np.vstack(output_keys), dtype=np.int64),
        {
            "attempted_components": attempted,
            "accepted_components": accepted,
            "input_faces": int(face_array.shape[0]),
            "output_faces": int(faces_out.shape[0]),
        },
    )
