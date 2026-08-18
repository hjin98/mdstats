"""Deterministic mesh-fidelity and topology metrics for LD9 validation.

The routines in this module compare display meshes without changing scientific
fields or render geometry.  They provide the LD9-V0 metric definitions used to
calibrate later simplification stages.  Surface sampling and nearest-neighbour
comparison are project-specific validation utilities; polygonal simplification
itself is not implemented here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphStyleError

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

MESH_TOPOLOGY_SUMMARY_SCHEMA = "mdstats.mesh-topology-summary.v1"
MESH_FIDELITY_OPTIONS_SCHEMA = "mdstats.mesh-fidelity-options.v1"
MESH_FIDELITY_REPORT_SCHEMA = "mdstats.mesh-fidelity-report.v1"


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _mesh_arrays(vertices: Any, faces: Any) -> tuple[FloatArray, IntArray]:
    vertex_array = np.asarray(vertices, dtype=np.float64)
    face_array = np.asarray(faces, dtype=np.int64)
    if vertex_array.ndim != 2 or vertex_array.shape[1:] != (3,):
        raise GraphAdapterError("vertices must have shape (n_vertices, 3).")
    if face_array.ndim != 2 or face_array.shape[1:] != (3,):
        raise GraphAdapterError("faces must have shape (n_faces, 3).")
    if np.any(~np.isfinite(vertex_array)):
        raise GraphAdapterError("vertices must be finite.")
    if face_array.size:
        if int(np.min(face_array)) < 0 or int(np.max(face_array)) >= vertex_array.shape[0]:
            raise GraphAdapterError("faces contain an out-of-range vertex index.")
        if np.any(
            (face_array[:, 0] == face_array[:, 1])
            | (face_array[:, 1] == face_array[:, 2])
            | (face_array[:, 2] == face_array[:, 0])
        ):
            raise GraphAdapterError("faces must not contain repeated vertex indices.")
    return (
        np.ascontiguousarray(vertex_array, dtype=np.float64),
        np.ascontiguousarray(face_array, dtype=np.int64),
    )


def _triangle_geometry(
    vertices: FloatArray, faces: IntArray
) -> tuple[FloatArray, FloatArray, FloatArray]:
    triangles = vertices[faces]
    cross = np.cross(triangles[:, 1] - triangles[:, 0], triangles[:, 2] - triangles[:, 0])
    lengths = np.linalg.norm(cross, axis=1)
    if np.any(lengths <= 0.0):
        raise GraphAdapterError("Mesh contains a zero-area triangle.")
    normals = cross / lengths[:, None]
    areas = 0.5 * lengths
    centroids = np.mean(triangles, axis=1)
    return areas, normals, centroids


@dataclass(frozen=True, slots=True)
class MeshTopologySummary:
    """Basic indexed-triangle topology counts for one mesh."""

    vertex_count: int
    edge_count: int
    face_count: int
    connected_component_count: int
    boundary_edge_count: int
    nonmanifold_edge_count: int
    euler_characteristic: int
    schema_version: str = MESH_TOPOLOGY_SUMMARY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MESH_TOPOLOGY_SUMMARY_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported mesh-topology-summary schema {self.schema_version!r}."
            )
        for name in (
            "vertex_count",
            "edge_count",
            "face_count",
            "connected_component_count",
            "boundary_edge_count",
            "nonmanifold_edge_count",
        ):
            object.__setattr__(
                self,
                name,
                _positive_int(getattr(self, name), name=name, minimum=0),
            )
        object.__setattr__(self, "euler_characteristic", int(self.euler_characteristic))

    @property
    def is_closed_two_manifold(self) -> bool:
        return self.boundary_edge_count == 0 and self.nonmanifold_edge_count == 0

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "vertex_count": self.vertex_count,
            "edge_count": self.edge_count,
            "face_count": self.face_count,
            "connected_component_count": self.connected_component_count,
            "boundary_edge_count": self.boundary_edge_count,
            "nonmanifold_edge_count": self.nonmanifold_edge_count,
            "euler_characteristic": self.euler_characteristic,
            "is_closed_two_manifold": self.is_closed_two_manifold,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MeshTopologySummary":
        return cls(
            vertex_count=value["vertex_count"],
            edge_count=value["edge_count"],
            face_count=value["face_count"],
            connected_component_count=value["connected_component_count"],
            boundary_edge_count=value["boundary_edge_count"],
            nonmanifold_edge_count=value["nonmanifold_edge_count"],
            euler_characteristic=value["euler_characteristic"],
            schema_version=value.get("schema_version", MESH_TOPOLOGY_SUMMARY_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class MeshFidelityOptions:
    """Sampling and acceptance policy for reference/candidate mesh comparison."""

    max_samples: int = 50_000
    random_seed: int = 0
    max_surface_error: float = 0.02
    max_normal_error_degrees: float = 8.0
    max_scalar_residual: float | None = None
    require_component_count: bool = True
    require_euler_characteristic: bool = True
    require_closed_two_manifold_match: bool = True
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = MESH_FIDELITY_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MESH_FIDELITY_OPTIONS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported mesh-fidelity-options schema {self.schema_version!r}."
            )
        object.__setattr__(
            self,
            "max_samples",
            _positive_int(self.max_samples, name="max_samples"),
        )
        if isinstance(self.random_seed, bool) or not isinstance(
            self.random_seed, (int, np.integer)
        ):
            raise GraphStyleError("random_seed must be an integer.")
        object.__setattr__(self, "random_seed", int(self.random_seed))
        for name in ("max_surface_error", "max_normal_error_degrees"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphStyleError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        if self.max_scalar_residual is not None:
            residual = float(self.max_scalar_residual)
            if not np.isfinite(residual) or residual < 0.0:
                raise GraphStyleError(
                    "max_scalar_residual must be finite and nonnegative or None."
                )
            object.__setattr__(self, "max_scalar_residual", residual)
        object.__setattr__(
            self, "require_component_count", bool(self.require_component_count)
        )
        object.__setattr__(
            self,
            "require_euler_characteristic",
            bool(self.require_euler_characteristic),
        )
        object.__setattr__(
            self,
            "require_closed_two_manifold_match",
            bool(self.require_closed_two_manifold_match),
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_samples": self.max_samples,
            "random_seed": self.random_seed,
            "max_surface_error": self.max_surface_error,
            "max_normal_error_degrees": self.max_normal_error_degrees,
            "max_scalar_residual": self.max_scalar_residual,
            "require_component_count": self.require_component_count,
            "require_euler_characteristic": self.require_euler_characteristic,
            "require_closed_two_manifold_match": self.require_closed_two_manifold_match,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MeshFidelityOptions":
        return cls(
            max_samples=value.get("max_samples", 50_000),
            random_seed=value.get("random_seed", 0),
            max_surface_error=value.get("max_surface_error", 0.02),
            max_normal_error_degrees=value.get(
                "max_normal_error_degrees", 8.0
            ),
            max_scalar_residual=value.get("max_scalar_residual"),
            require_component_count=value.get("require_component_count", True),
            require_euler_characteristic=value.get(
                "require_euler_characteristic", True
            ),
            require_closed_two_manifold_match=value.get(
                "require_closed_two_manifold_match", True
            ),
            metadata=value.get("metadata", {}),
            schema_version=value.get("schema_version", MESH_FIDELITY_OPTIONS_SCHEMA),
        )


@dataclass(frozen=True, slots=True)
class MeshFidelityReport:
    """Symmetric sampled geometry, normal, scalar, and topology comparison."""

    reference_topology: MeshTopologySummary
    candidate_topology: MeshTopologySummary
    reference_sample_count: int
    candidate_sample_count: int
    symmetric_distance_median: float
    symmetric_distance_p99: float
    symmetric_distance_max: float
    normal_error_median_degrees: float
    normal_error_p99_degrees: float
    normal_error_max_degrees: float
    scalar_residual_median: float | None
    scalar_residual_p99: float | None
    scalar_residual_max: float | None
    violations: tuple[str, ...]
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = MESH_FIDELITY_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != MESH_FIDELITY_REPORT_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported mesh-fidelity-report schema {self.schema_version!r}."
            )
        object.__setattr__(
            self,
            "reference_sample_count",
            _positive_int(
                self.reference_sample_count,
                name="reference_sample_count",
                minimum=0,
            ),
        )
        object.__setattr__(
            self,
            "candidate_sample_count",
            _positive_int(
                self.candidate_sample_count,
                name="candidate_sample_count",
                minimum=0,
            ),
        )
        for name in (
            "symmetric_distance_median",
            "symmetric_distance_p99",
            "symmetric_distance_max",
            "normal_error_median_degrees",
            "normal_error_p99_degrees",
            "normal_error_max_degrees",
        ):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value < 0.0:
                raise GraphAdapterError(f"{name} must be finite and nonnegative.")
            object.__setattr__(self, name, value)
        for name in (
            "scalar_residual_median",
            "scalar_residual_p99",
            "scalar_residual_max",
        ):
            value = getattr(self, name)
            if value is not None:
                number = float(value)
                if not np.isfinite(number) or number < 0.0:
                    raise GraphAdapterError(f"{name} must be nonnegative or None.")
                object.__setattr__(self, name, number)
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
            "reference_sample_count": self.reference_sample_count,
            "candidate_sample_count": self.candidate_sample_count,
            "symmetric_distance_median": self.symmetric_distance_median,
            "symmetric_distance_p99": self.symmetric_distance_p99,
            "symmetric_distance_max": self.symmetric_distance_max,
            "normal_error_median_degrees": self.normal_error_median_degrees,
            "normal_error_p99_degrees": self.normal_error_p99_degrees,
            "normal_error_max_degrees": self.normal_error_max_degrees,
            "scalar_residual_median": self.scalar_residual_median,
            "scalar_residual_p99": self.scalar_residual_p99,
            "scalar_residual_max": self.scalar_residual_max,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "MeshFidelityReport":
        return cls(
            reference_topology=MeshTopologySummary.from_json_dict(
                value["reference_topology"]
            ),
            candidate_topology=MeshTopologySummary.from_json_dict(
                value["candidate_topology"]
            ),
            reference_sample_count=value["reference_sample_count"],
            candidate_sample_count=value["candidate_sample_count"],
            symmetric_distance_median=value["symmetric_distance_median"],
            symmetric_distance_p99=value["symmetric_distance_p99"],
            symmetric_distance_max=value["symmetric_distance_max"],
            normal_error_median_degrees=value["normal_error_median_degrees"],
            normal_error_p99_degrees=value["normal_error_p99_degrees"],
            normal_error_max_degrees=value["normal_error_max_degrees"],
            scalar_residual_median=value.get("scalar_residual_median"),
            scalar_residual_p99=value.get("scalar_residual_p99"),
            scalar_residual_max=value.get("scalar_residual_max"),
            violations=tuple(value.get("violations", ())),
            metadata=value.get("metadata", {}),
            schema_version=value.get("schema_version", MESH_FIDELITY_REPORT_SCHEMA),
        )


def summarize_mesh_topology(vertices: Any, faces: Any) -> MeshTopologySummary:
    """Return deterministic topology counts using vectorized edge incidence.

    This path is used repeatedly during simplification.  A Python dictionary and
    set traversal over every triangle edge made diffuse six-hundred-thousand-face
    shells take minutes.  NumPy performs edge canonicalization and incidence
    counting, while SciPy labels the sparse vertex graph in compiled code.
    """

    vertex_array, face_array = _mesh_arrays(vertices, faces)
    if face_array.size == 0:
        return MeshTopologySummary(
            vertex_count=0,
            edge_count=0,
            face_count=0,
            connected_component_count=0,
            boundary_edge_count=0,
            nonmanifold_edge_count=0,
            euler_characteristic=0,
        )
    edge_occurrences = np.concatenate(
        (
            face_array[:, (0, 1)],
            face_array[:, (1, 2)],
            face_array[:, (2, 0)],
        ),
        axis=0,
    )
    edge_occurrences.sort(axis=1)
    unique_edges, incidence = np.unique(
        edge_occurrences, axis=0, return_counts=True
    )
    used_vertices = np.unique(face_array)
    rows = np.concatenate((unique_edges[:, 0], unique_edges[:, 1]))
    columns = np.concatenate((unique_edges[:, 1], unique_edges[:, 0]))
    graph = coo_matrix(
        (np.ones(rows.size, dtype=np.uint8), (rows, columns)),
        shape=(vertex_array.shape[0], vertex_array.shape[0]),
    ).tocsr()
    _count, labels = connected_components(graph, directed=False, return_labels=True)
    components = int(np.unique(labels[used_vertices]).size)
    boundary = int(np.count_nonzero(incidence == 1))
    nonmanifold = int(np.count_nonzero(incidence > 2))
    used_count = int(used_vertices.size)
    edge_count = int(unique_edges.shape[0])
    euler = used_count - edge_count + int(face_array.shape[0])
    return MeshTopologySummary(
        vertex_count=used_count,
        edge_count=edge_count,
        face_count=int(face_array.shape[0]),
        connected_component_count=components,
        boundary_edge_count=boundary,
        nonmanifold_edge_count=nonmanifold,
        euler_characteristic=euler,
    )


def sample_mesh_surface(
    vertices: Any,
    faces: Any,
    *,
    max_samples: int,
    random_seed: int = 0,
) -> tuple[FloatArray, FloatArray]:
    """Return deterministic area-weighted points and parent-face normals."""

    vertex_array, face_array = _mesh_arrays(vertices, faces)
    if face_array.shape[0] == 0:
        return (
            np.empty((0, 3), dtype=np.float64),
            np.empty((0, 3), dtype=np.float64),
        )
    sample_count = _positive_int(max_samples, name="max_samples")
    areas, normals, _ = _triangle_geometry(vertex_array, face_array)
    probabilities = areas / float(np.sum(areas, dtype=np.float64))
    rng = np.random.default_rng(int(random_seed))
    chosen = rng.choice(
        face_array.shape[0], size=sample_count, replace=True, p=probabilities
    )
    triangles = vertex_array[face_array[chosen]]
    uv = rng.random((sample_count, 2))
    reflected = np.sum(uv, axis=1) > 1.0
    uv[reflected] = 1.0 - uv[reflected]
    points = (
        triangles[:, 0]
        + uv[:, 0, None] * (triangles[:, 1] - triangles[:, 0])
        + uv[:, 1, None] * (triangles[:, 2] - triangles[:, 0])
    )
    return (
        np.ascontiguousarray(points, dtype=np.float64),
        np.ascontiguousarray(normals[chosen], dtype=np.float64),
    )


def _summary(values: FloatArray) -> tuple[float, float, float]:
    if values.size == 0:
        return 0.0, 0.0, 0.0
    return (
        float(np.median(values)),
        float(np.quantile(values, 0.99)),
        float(np.max(values)),
    )


def compare_mesh_fidelity(
    reference_vertices: Any,
    reference_faces: Any,
    candidate_vertices: Any,
    candidate_faces: Any,
    *,
    options: MeshFidelityOptions | None = None,
    scalar_sampler: Callable[[FloatArray], FloatArray] | None = None,
    contour_level: float | None = None,
) -> MeshFidelityReport:
    """Compare one candidate mesh to one raw reference mesh.

    The symmetric distance is measured between deterministic area-weighted sample
    clouds.  Normal error uses the nearest sample in the opposite cloud and ignores
    global orientation by taking the absolute dot product.  When ``scalar_sampler``
    is supplied, it is evaluated on candidate samples and compared with
    ``contour_level``.
    """

    policy = MeshFidelityOptions() if options is None else options
    if not isinstance(policy, MeshFidelityOptions):
        raise TypeError("options must be MeshFidelityOptions or None.")
    ref_vertices, ref_faces = _mesh_arrays(reference_vertices, reference_faces)
    cand_vertices, cand_faces = _mesh_arrays(candidate_vertices, candidate_faces)
    reference_topology = summarize_mesh_topology(ref_vertices, ref_faces)
    candidate_topology = summarize_mesh_topology(cand_vertices, cand_faces)

    ref_points, ref_normals = sample_mesh_surface(
        ref_vertices,
        ref_faces,
        max_samples=policy.max_samples,
        random_seed=policy.random_seed,
    )
    cand_points, cand_normals = sample_mesh_surface(
        cand_vertices,
        cand_faces,
        max_samples=policy.max_samples,
        random_seed=policy.random_seed,
    )
    if ref_points.size == 0 or cand_points.size == 0:
        raise GraphAdapterError("Mesh fidelity requires nonempty reference and candidate meshes.")

    ref_tree = cKDTree(ref_points)
    cand_tree = cKDTree(cand_points)
    cand_to_ref_distance, cand_to_ref = ref_tree.query(cand_points, k=1)
    ref_to_cand_distance, ref_to_cand = cand_tree.query(ref_points, k=1)
    symmetric = np.concatenate((cand_to_ref_distance, ref_to_cand_distance)).astype(
        np.float64, copy=False
    )

    cand_dot = np.einsum(
        "ij,ij->i", cand_normals, ref_normals[np.asarray(cand_to_ref, dtype=np.int64)]
    )
    ref_dot = np.einsum(
        "ij,ij->i", ref_normals, cand_normals[np.asarray(ref_to_cand, dtype=np.int64)]
    )
    dots = np.clip(np.abs(np.concatenate((cand_dot, ref_dot))), 0.0, 1.0)
    normal_errors = np.degrees(np.arccos(dots))

    distance_median, distance_p99, distance_max = _summary(symmetric)
    normal_median, normal_p99, normal_max = _summary(normal_errors)

    residual_median: float | None = None
    residual_p99: float | None = None
    residual_max: float | None = None
    if scalar_sampler is not None:
        if contour_level is None or not np.isfinite(float(contour_level)):
            raise GraphStyleError(
                "A finite contour_level is required when scalar_sampler is provided."
            )
        sampled = np.asarray(scalar_sampler(cand_points), dtype=np.float64)
        if sampled.shape != (cand_points.shape[0],) or np.any(~np.isfinite(sampled)):
            raise GraphAdapterError(
                "scalar_sampler must return one finite value per candidate sample."
            )
        residuals = np.abs(sampled - float(contour_level))
        residual_median, residual_p99, residual_max = _summary(residuals)

    violations: list[str] = []
    if distance_max > policy.max_surface_error:
        violations.append(
            f"surface_error={distance_max:.17g}>{policy.max_surface_error:.17g}"
        )
    if normal_p99 > policy.max_normal_error_degrees:
        violations.append(
            "normal_error_p99_degrees="
            f"{normal_p99:.17g}>{policy.max_normal_error_degrees:.17g}"
        )
    if (
        policy.max_scalar_residual is not None
        and residual_max is not None
        and residual_max > policy.max_scalar_residual
    ):
        violations.append(
            f"scalar_residual={residual_max:.17g}>{policy.max_scalar_residual:.17g}"
        )
    if (
        policy.require_component_count
        and reference_topology.connected_component_count
        != candidate_topology.connected_component_count
    ):
        violations.append(
            "component_count="
            f"{candidate_topology.connected_component_count}!="
            f"{reference_topology.connected_component_count}"
        )
    if (
        policy.require_euler_characteristic
        and reference_topology.euler_characteristic
        != candidate_topology.euler_characteristic
    ):
        violations.append(
            "euler_characteristic="
            f"{candidate_topology.euler_characteristic}!="
            f"{reference_topology.euler_characteristic}"
        )
    if (
        policy.require_closed_two_manifold_match
        and reference_topology.is_closed_two_manifold
        != candidate_topology.is_closed_two_manifold
    ):
        violations.append(
            "closed_two_manifold="
            f"{candidate_topology.is_closed_two_manifold}!="
            f"{reference_topology.is_closed_two_manifold}"
        )

    return MeshFidelityReport(
        reference_topology=reference_topology,
        candidate_topology=candidate_topology,
        reference_sample_count=int(ref_points.shape[0]),
        candidate_sample_count=int(cand_points.shape[0]),
        symmetric_distance_median=distance_median,
        symmetric_distance_p99=distance_p99,
        symmetric_distance_max=distance_max,
        normal_error_median_degrees=normal_median,
        normal_error_p99_degrees=normal_p99,
        normal_error_max_degrees=normal_max,
        scalar_residual_median=residual_median,
        scalar_residual_p99=residual_p99,
        scalar_residual_max=residual_max,
        violations=tuple(violations),
        metadata={
            "distance_metric": "symmetric_sampled_nearest_neighbor_v1",
            "normal_metric": "absolute_nearest_sample_angle_v1",
            "sampling": "deterministic_area_weighted_v1",
        },
    )
