"""Closed-loop fitting of periodic density meshes to browser budgets.

This module owns display-complexity adaptation after scientific density fields
and initial meshes have been prepared.  It deliberately does not alter the
scientific HDR threshold.  The controller may simplify an existing periodic
surface or recontour the same scalar field on a coarser logical grid, but it
always validates the exact post-replication browser usage before Plotly
serialization.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Any, Literal

import numpy as np
from numpy.typing import NDArray

from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port
from .density_contracts import FrozenJSONMapping, ScalarField3D, freeze_json_mapping
from .density_mesh_simplify import MeshSimplificationOptions, simplify_periodic_density_mesh
from .density_render_budget import (
    BrowserMeshBudget,
    BrowserMeshBudgetFailure,
    BrowserMeshTraceUsage,
    BrowserMeshUsage,
    evaluate_browser_mesh_budget,
)
from .density_sparse_mesh import validate_periodic_canonical_mesh
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

BROWSER_MESH_PROFILE_SCHEMA = "mdstats.browser-mesh-profile.v1"
DENSITY_SHELL_GEOMETRY_SCHEMA = "mdstats.density-shell-geometry.v1"
DENSITY_SHELL_FIT_ATTEMPT_SCHEMA = "mdstats.density-shell-fit-attempt.v1"
DENSITY_SHELL_FIT_RESULT_SCHEMA = "mdstats.density-shell-fit-result.v1"
DENSITY_SCENE_FIT_REPORT_SCHEMA = "mdstats.density-scene-fit-report.v1"


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _readonly(value: Any, dtype: Any, *, ndim: int, name: str) -> NDArray[Any]:
    array = np.ascontiguousarray(value, dtype=dtype)
    if array.ndim != ndim:
        raise GraphAdapterError(f"{name} must be {ndim}-dimensional.")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class BrowserMeshProfile:
    """Named closed-loop browser fitting policy.

    The budget values are conservative package defaults rather than claims
    about every browser/GPU combination.  Callers may always supply a custom
    :class:`BrowserMeshBudget`.
    """

    name: Literal["compact", "balanced", "quality", "custom"] = "balanced"
    budget: BrowserMeshBudget = field(
        default_factory=lambda: BrowserMeshBudget(
            max_final_density_faces=600_000,
            max_final_density_vertices=450_000,
            max_final_html_bytes=72 * 1024**2,
            max_plotly_traces=96,
            metadata={"profile": "balanced"},
        )
    )
    reserve_fraction: float = 0.10
    max_fit_iterations: int = 4
    allow_recontour: bool = True
    allow_voxel_fallback: bool = False
    minimum_canonical_faces_per_shell: int = 2_000
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = BROWSER_MESH_PROFILE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BROWSER_MESH_PROFILE_SCHEMA:
            raise GraphAdapterError("Unsupported browser-mesh-profile schema.")
        if self.name not in {"compact", "balanced", "quality", "custom"}:
            raise GraphStyleError("Unsupported browser mesh profile name.")
        if not isinstance(self.budget, BrowserMeshBudget):
            raise TypeError("budget must be BrowserMeshBudget.")
        reserve = float(self.reserve_fraction)
        if not np.isfinite(reserve) or not 0.0 <= reserve < 0.5:
            raise GraphStyleError("reserve_fraction must lie in [0, 0.5).")
        object.__setattr__(self, "reserve_fraction", reserve)
        object.__setattr__(
            self,
            "max_fit_iterations",
            _positive_int(self.max_fit_iterations, name="max_fit_iterations"),
        )
        object.__setattr__(
            self,
            "minimum_canonical_faces_per_shell",
            _positive_int(
                self.minimum_canonical_faces_per_shell,
                name="minimum_canonical_faces_per_shell",
                minimum=4,
            ),
        )
        object.__setattr__(self, "allow_recontour", bool(self.allow_recontour))
        object.__setattr__(self, "allow_voxel_fallback", bool(self.allow_voxel_fallback))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @classmethod
    def compact(cls) -> "BrowserMeshProfile":
        return cls(
            name="compact",
            budget=BrowserMeshBudget(
                max_final_density_faces=300_000,
                max_final_density_vertices=225_000,
                max_final_html_bytes=40 * 1024**2,
                max_plotly_traces=72,
                metadata={"profile": "compact"},
            ),
            reserve_fraction=0.12,
            minimum_canonical_faces_per_shell=1_200,
        )

    @classmethod
    def balanced(cls) -> "BrowserMeshProfile":
        return cls()

    @classmethod
    def quality(cls) -> "BrowserMeshProfile":
        return cls(
            name="quality",
            budget=BrowserMeshBudget(
                max_final_density_faces=1_000_000,
                max_final_density_vertices=750_000,
                max_final_html_bytes=128 * 1024**2,
                max_plotly_traces=128,
                metadata={"profile": "quality"},
            ),
            reserve_fraction=0.08,
            minimum_canonical_faces_per_shell=4_000,
        )

    @classmethod
    def custom(cls, budget: BrowserMeshBudget) -> "BrowserMeshProfile":
        return cls(name="custom", budget=budget)

    @classmethod
    def coerce(
        cls,
        value: "BrowserMeshProfile | str | None",
        *,
        custom_budget: BrowserMeshBudget | None = None,
    ) -> "BrowserMeshProfile":
        if isinstance(value, BrowserMeshProfile):
            if custom_budget is not None and value.budget != custom_budget:
                raise GraphStyleError("mesh_profile and browser_budget disagree.")
            return value
        if value is None:
            return cls.custom(custom_budget) if custom_budget is not None else cls.balanced()
        token = str(value)
        if token == "compact":
            profile = cls.compact()
        elif token == "balanced":
            profile = cls.balanced()
        elif token == "quality":
            profile = cls.quality()
        elif token == "custom":
            if custom_budget is None:
                raise GraphStyleError("custom mesh profile requires browser_budget.")
            profile = cls.custom(custom_budget)
        else:
            raise GraphStyleError(f"Unknown browser mesh profile {token!r}.")
        if custom_budget is not None:
            return cls.custom(custom_budget)
        return profile

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "name": self.name,
            "budget": self.budget.to_json_dict(),
            "reserve_fraction": self.reserve_fraction,
            "max_fit_iterations": self.max_fit_iterations,
            "allow_recontour": self.allow_recontour,
            "allow_voxel_fallback": self.allow_voxel_fallback,
            "minimum_canonical_faces_per_shell": self.minimum_canonical_faces_per_shell,
            "metadata": self.metadata.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class DensityShellGeometry:
    """Backend-neutral canonical geometry for one scientific HDR shell."""

    shell_key: str
    field: ScalarField3D
    mass_fraction: float
    contour_level: float
    vertices_fractional: FloatArray
    vertices_cartesian: FloatArray
    faces: IntArray
    display_replication: int = 1
    visual_importance: float = 1.0
    minimum_faces: int = 4
    source_kind: str = "mesh"
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_SHELL_GEOMETRY_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SHELL_GEOMETRY_SCHEMA:
            raise GraphAdapterError("Unsupported density-shell-geometry schema.")
        if not isinstance(self.shell_key, str) or not self.shell_key:
            raise GraphAdapterError("shell_key must be nonempty.")
        if not hasattr(self.field, "grid_shape") or not hasattr(self.field, "display_cell"):
            raise TypeError("field must implement the ScalarField3D protocol.")
        fraction = float(self.mass_fraction)
        level = float(self.contour_level)
        importance = float(self.visual_importance)
        if not np.isfinite(fraction) or not 0.0 < fraction < 1.0:
            raise GraphStyleError("mass_fraction must lie in (0, 1).")
        if not np.isfinite(level) or level <= 0.0:
            raise GraphStyleError("contour_level must be finite and positive.")
        if not np.isfinite(importance) or importance <= 0.0:
            raise GraphStyleError("visual_importance must be finite and positive.")
        fractional = _readonly(
            self.vertices_fractional, np.float64, ndim=2, name="vertices_fractional"
        )
        cartesian = _readonly(
            self.vertices_cartesian, np.float64, ndim=2, name="vertices_cartesian"
        )
        faces = _readonly(self.faces, np.int64, ndim=2, name="faces")
        if fractional.shape != cartesian.shape or fractional.shape[1:] != (3,):
            raise GraphAdapterError("Vertex arrays must align with shape (n, 3).")
        if faces.shape[1:] != (3,):
            raise GraphAdapterError("faces must have shape (n_faces, 3).")
        if faces.size and (int(np.min(faces)) < 0 or int(np.max(faces)) >= fractional.shape[0]):
            raise GraphAdapterError("faces reference invalid vertices.")
        object.__setattr__(self, "mass_fraction", fraction)
        object.__setattr__(self, "contour_level", level)
        object.__setattr__(self, "visual_importance", importance)
        object.__setattr__(self, "vertices_fractional", fractional)
        object.__setattr__(self, "vertices_cartesian", cartesian)
        object.__setattr__(self, "faces", faces)
        object.__setattr__(
            self,
            "display_replication",
            _positive_int(self.display_replication, name="display_replication"),
        )
        object.__setattr__(
            self,
            "minimum_faces",
            _positive_int(self.minimum_faces, name="minimum_faces", minimum=4),
        )
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def face_count(self) -> int:
        return int(self.faces.shape[0])

    @property
    def vertex_count(self) -> int:
        return int(self.vertices_cartesian.shape[0])

    @property
    def serialized_face_count(self) -> int:
        return self.face_count * self.display_replication

    @property
    def serialized_vertex_count(self) -> int:
        return self.vertex_count * self.display_replication

    def with_geometry(
        self,
        vertices_fractional: Any,
        vertices_cartesian: Any,
        faces: Any,
        *,
        source_kind: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> "DensityShellGeometry":
        return replace(
            self,
            vertices_fractional=vertices_fractional,
            vertices_cartesian=vertices_cartesian,
            faces=faces,
            source_kind=source_kind,
            metadata={
                **self.metadata.to_json_dict(),
                **({} if metadata is None else dict(metadata)),
            },
        )


@dataclass(frozen=True, slots=True)
class DensityShellFitAttempt:
    stage: str
    target_faces: int
    input_faces: int
    output_faces: int
    accepted: bool
    reason: str | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_SHELL_FIT_ATTEMPT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SHELL_FIT_ATTEMPT_SCHEMA:
            raise GraphAdapterError("Unsupported density-shell-fit-attempt schema.")
        if not isinstance(self.stage, str) or not self.stage:
            raise GraphAdapterError("stage must be nonempty.")
        for name in ("target_faces", "input_faces", "output_faces"):
            object.__setattr__(
                self,
                name,
                _positive_int(getattr(self, name), name=name, minimum=0),
            )
        object.__setattr__(self, "accepted", bool(self.accepted))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage": self.stage,
            "target_faces": self.target_faces,
            "input_faces": self.input_faces,
            "output_faces": self.output_faces,
            "accepted": self.accepted,
            "reason": self.reason,
            "metadata": self.metadata.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class DensityShellFitResult:
    geometry: DensityShellGeometry
    initial_faces: int
    initial_target_faces: int
    final_target_faces: int
    attempts: tuple[DensityShellFitAttempt, ...]
    fallback_level: str
    target_met: bool
    schema_version: str = DENSITY_SHELL_FIT_RESULT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SHELL_FIT_RESULT_SCHEMA:
            raise GraphAdapterError("Unsupported density-shell-fit-result schema.")
        if not isinstance(self.geometry, DensityShellGeometry):
            raise TypeError("geometry must be DensityShellGeometry.")
        object.__setattr__(self, "attempts", tuple(self.attempts))
        object.__setattr__(self, "target_met", bool(self.target_met))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "shell_key": self.geometry.shell_key,
            "initial_faces": self.initial_faces,
            "initial_target_faces": self.initial_target_faces,
            "final_target_faces": self.final_target_faces,
            "final_faces": self.geometry.face_count,
            "final_vertices": self.geometry.vertex_count,
            "display_replication": self.geometry.display_replication,
            "fallback_level": self.fallback_level,
            "target_met": self.target_met,
            "attempts": [item.to_json_dict() for item in self.attempts],
        }


@dataclass(frozen=True, slots=True)
class DensitySceneFitReport:
    profile: BrowserMeshProfile
    shell_results: tuple[DensityShellFitResult, ...]
    usage: BrowserMeshUsage
    passed: bool
    violations: tuple[str, ...]
    iterations: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_SCENE_FIT_REPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SCENE_FIT_REPORT_SCHEMA:
            raise GraphAdapterError("Unsupported density-scene-fit-report schema.")
        object.__setattr__(self, "shell_results", tuple(self.shell_results))
        object.__setattr__(self, "violations", tuple(str(v) for v in self.violations))
        object.__setattr__(self, "iterations", _positive_int(self.iterations, name="iterations", minimum=0))
        object.__setattr__(self, "passed", bool(self.passed))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "profile": self.profile.to_json_dict(),
            "shell_results": [item.to_json_dict() for item in self.shell_results],
            "usage": self.usage.to_json_dict(),
            "passed": self.passed,
            "violations": list(self.violations),
            "iterations": self.iterations,
            "metadata": self.metadata.to_json_dict(),
        }


def _usage(
    geometries: Sequence[DensityShellGeometry],
    *,
    non_density_trace_count: int,
    metadata: Mapping[str, Any] | None = None,
) -> BrowserMeshUsage:
    return BrowserMeshUsage(
        density_traces=tuple(
            BrowserMeshTraceUsage(
                trace_key=item.shell_key,
                face_count=item.face_count,
                vertex_count=item.vertex_count,
                display_replication=item.display_replication,
                retained_array_bytes=int(item.vertices_cartesian.nbytes + item.faces.nbytes),
                metadata={"source_kind": item.source_kind},
            )
            for item in geometries
        ),
        non_density_trace_count=non_density_trace_count,
        metadata={} if metadata is None else metadata,
    )


def _allocate_targets(
    geometries: Sequence[DensityShellGeometry],
    *,
    profile: BrowserMeshProfile,
) -> dict[str, int]:
    """Allocate exact canonical targets under face and vertex pressure.

    The apportionment starts from a per-shell minimum and distributes the
    remaining serialized-face budget in proportion to current geometric demand
    and visual importance.  It never increases a shell above its current count.
    """

    items = tuple(geometries)
    if not items:
        return {}
    usable_faces = int(
        np.floor(profile.budget.max_final_density_faces * (1.0 - profile.reserve_fraction))
    )
    current_serialized_faces = np.asarray(
        [item.serialized_face_count for item in items], dtype=np.int64
    )
    current_serialized_vertices = np.asarray(
        [item.serialized_vertex_count for item in items], dtype=np.int64
    )
    vertex_scale = min(
        1.0,
        profile.budget.max_final_density_vertices
        / max(1, int(np.sum(current_serialized_vertices))),
    )
    usable_faces = min(
        usable_faces,
        int(np.floor(np.sum(current_serialized_faces) * vertex_scale)),
    )
    minima = np.asarray(
        [
            min(
                item.face_count,
                max(item.minimum_faces, profile.minimum_canonical_faces_per_shell),
            )
            * item.display_replication
            for item in items
        ],
        dtype=np.int64,
    )
    minimum_total = int(np.sum(minima))
    if minimum_total > usable_faces:
        # Retain deterministic nonzero minima. The later irreducible-fit error
        # will explain that the selected profile cannot represent all shells.
        scale = usable_faces / max(1, minimum_total)
        minima = np.asarray(
            [
                max(4 * item.display_replication, int(np.floor(value * scale)))
                for value, item in zip(minima, items, strict=True)
            ],
            dtype=np.int64,
        )
        minimum_total = int(np.sum(minima))
    remaining = max(0, usable_faces - minimum_total)
    capacities = np.maximum(0, current_serialized_faces - minima)
    weights = np.asarray(
        [
            max(1.0, float(capacity)) * float(item.visual_importance)
            for capacity, item in zip(capacities, items, strict=True)
        ],
        dtype=np.float64,
    )
    if remaining > 0 and np.any(capacities > 0):
        weights = np.where(capacities > 0, weights, 0.0)
        shares = remaining * weights / max(float(np.sum(weights)), 1.0)
        extras = np.minimum(capacities, np.floor(shares).astype(np.int64))
    else:
        extras = np.zeros(len(items), dtype=np.int64)
    residual = max(0, remaining - int(np.sum(extras)))
    remainders = shares - np.floor(shares) if remaining > 0 and np.any(capacities > 0) else np.zeros(len(items))
    order = sorted(
        range(len(items)),
        key=lambda index: (-float(remainders[index]), -items[index].visual_importance, items[index].shell_key),
    )
    while residual > 0:
        progressed = False
        for index in order:
            if extras[index] >= capacities[index]:
                continue
            step = items[index].display_replication
            if step > residual:
                continue
            extras[index] += step
            residual -= step
            progressed = True
            if residual <= 0:
                break
        if not progressed:
            break
    serialized_targets = minima + extras
    return {
        item.shell_key: max(4, min(item.face_count, int(serialized_targets[index] // item.display_replication)))
        for index, item in enumerate(items)
    }


def _relaxed_policy(
    base: MeshSimplificationOptions,
    *,
    target_faces: int,
    level: Literal["strict", "browser", "aggressive"],
) -> MeshSimplificationOptions:
    if level == "strict":
        return replace(base, target_faces=target_faces, hard_target=False)
    if level == "browser":
        return replace(
            base,
            target_faces=target_faces,
            max_attempts=max(base.max_attempts, 7),
            aggressiveness=max(base.aggressiveness, 9.0),
            max_surface_error_p99=max(base.max_surface_error_p99, 0.14),
            max_surface_error_max=max(base.max_surface_error_max, 1.5),
            max_implicit_displacement_p99=max(base.max_implicit_displacement_p99, 0.28),
            max_normal_degradation_degrees=max(base.max_normal_degradation_degrees, 72.0),
            max_relative_scalar_residual_p99=max(base.max_relative_scalar_residual_p99, 5.0),
            hard_target=False,
        )
    return replace(
        base,
        target_faces=target_faces,
        max_attempts=max(base.max_attempts, 9),
        aggressiveness=max(base.aggressiveness, 12.0),
        max_surface_error_p99=max(base.max_surface_error_p99, 0.30),
        max_surface_error_max=max(base.max_surface_error_max, 3.0),
        max_implicit_displacement_p99=max(base.max_implicit_displacement_p99, 0.50),
        max_normal_degradation_degrees=max(base.max_normal_degradation_degrees, 88.0),
        max_relative_scalar_residual_p99=max(base.max_relative_scalar_residual_p99, 50.0),
        hard_target=False,
    )


def _validated_candidate(
    geometry: DensityShellGeometry,
    vertices_fractional: Any,
    vertices_cartesian: Any,
    faces: Any,
) -> tuple[FloatArray, FloatArray, IntArray]:
    fractional = np.ascontiguousarray(vertices_fractional, dtype=np.float64)
    cartesian = np.ascontiguousarray(vertices_cartesian, dtype=np.float64)
    face_array = np.ascontiguousarray(faces, dtype=np.int64)
    topology = validate_periodic_canonical_mesh(
        fractional,
        cartesian,
        face_array,
        display_cell=np.asarray(geometry.field.display_cell, dtype=np.float64),
        logical_grid_shape=tuple(int(value) for value in geometry.field.grid_shape),
    )
    tolerance = 1.0e-10 * max(
        float(np.linalg.norm(vector)) for vector in geometry.field.display_cell
    )
    if (
        topology.interior_edge_incidence_failures != 0
        or topology.unpaired_boundary_edge_count != 0
        or topology.maximum_boundary_seam_mismatch > tolerance
    ):
        raise GraphComplexityError(
            "Candidate mesh failed periodic seam/incidence validation."
        )
    return fractional, cartesian, face_array


def _recontour_field(
    geometry: DensityShellGeometry,
    *,
    stride: int,
    max_nodes: int = 4_000_000,
) -> DensityShellGeometry:
    try:
        from skimage.measure import marching_cubes
    except ImportError as exc:  # pragma: no cover
        raise GraphComplexityError("Recontouring requires scikit-image.") from exc
    original_shape = np.asarray(geometry.field.grid_shape, dtype=np.int64)
    coarse_shape = np.maximum(8, np.ceil(original_shape / int(stride)).astype(np.int64))
    while int(np.prod(coarse_shape, dtype=object)) > max_nodes and np.any(coarse_shape > 8):
        coarse_shape = np.maximum(8, np.floor(coarse_shape * 0.85).astype(np.int64))
    axes = [
        np.floor(np.arange(int(size), dtype=np.float64) * original / size).astype(np.int64)
        for size, original in zip(coarse_shape, original_shape, strict=True)
    ]
    values = np.empty(tuple(int(value) for value in coarse_shape), dtype=np.float32)
    yz = int(coarse_shape[1] * coarse_shape[2])
    batch_x = max(1, min(int(coarse_shape[0]), max_nodes // max(1, yz)))
    for start in range(0, int(coarse_shape[0]), batch_x):
        stop = min(int(coarse_shape[0]), start + batch_x)
        x, y, z = np.meshgrid(
            axes[0][start:stop], axes[1], axes[2], indexing="ij"
        )
        coordinates = np.column_stack((x.ravel(), y.ravel(), z.ravel()))
        gathered = geometry.field.gather_node_values(coordinates)
        values[start:stop] = np.asarray(gathered, dtype=np.float32).reshape(
            (stop - start, int(coarse_shape[1]), int(coarse_shape[2]))
        )
    extended = np.pad(values, ((0, 1), (0, 1), (0, 1)), mode="wrap")
    minimum = np.float32(np.min(extended))
    maximum = np.float32(np.max(extended))
    level = np.float32(geometry.contour_level)
    if not minimum < level < maximum:
        level = np.nextafter(maximum, minimum, dtype=np.float32)
    vertices_fractional, faces, _normals, _values = marching_cubes(
        extended,
        level=float(level),
        spacing=tuple(float(1.0 / value) for value in coarse_shape),
        allow_degenerate=False,
        method="lewiner",
    )
    vertices_fractional = np.ascontiguousarray(vertices_fractional, dtype=np.float64)
    vertices_cartesian = vertices_fractional @ np.asarray(
        geometry.field.display_cell, dtype=np.float64
    )
    fractional, cartesian, face_array = _validated_candidate(
        geometry, vertices_fractional, vertices_cartesian, faces
    )
    return geometry.with_geometry(
        fractional,
        cartesian,
        face_array,
        source_kind=f"recontour_stride_{stride}",
        metadata={
            "recontour_stride": int(stride),
            "recontour_grid_shape": tuple(int(value) for value in coarse_shape),
        },
    )


def fit_density_shell(
    geometry: DensityShellGeometry,
    *,
    target_faces: int,
    simplification_options: MeshSimplificationOptions,
    profile: BrowserMeshProfile,
) -> DensityShellFitResult:
    """Fit one shell through the deterministic adaptive reduction ladder."""

    target = max(4, min(geometry.face_count, int(target_faces)))
    attempts: list[DensityShellFitAttempt] = []
    best = geometry
    if geometry.face_count <= target:
        return DensityShellFitResult(
            geometry=geometry,
            initial_faces=geometry.face_count,
            initial_target_faces=target,
            final_target_faces=target,
            attempts=(),
            fallback_level="none",
            target_met=True,
        )

    def attempt_simplification(
        source: DensityShellGeometry,
        *,
        stage: str,
        numerical_target: int,
        policy_level: Literal["strict", "browser", "aggressive"],
    ) -> DensityShellGeometry | None:
        nonlocal best
        try:
            result = simplify_periodic_density_mesh(
                source.field,
                source.vertices_fractional,
                source.vertices_cartesian,
                source.faces,
                contour_level=source.contour_level,
                options=_relaxed_policy(
                    simplification_options,
                    target_faces=max(4, numerical_target),
                    level=policy_level,
                ),
            )
            candidate = source.with_geometry(
                result.vertices_fractional,
                result.vertices_cartesian,
                result.faces,
                source_kind=stage,
                metadata={"simplification": result.to_json_dict(include_geometry=False)},
            )
            if candidate.face_count < best.face_count:
                best = candidate
            attempts.append(
                DensityShellFitAttempt(
                    stage=stage,
                    target_faces=target,
                    input_faces=source.face_count,
                    output_faces=candidate.face_count,
                    accepted=candidate.face_count <= target,
                    metadata={"numerical_target_faces": numerical_target},
                )
            )
            return candidate
        except Exception as exc:
            attempts.append(
                DensityShellFitAttempt(
                    stage=stage,
                    target_faces=target,
                    input_faces=source.face_count,
                    output_faces=source.face_count,
                    accepted=False,
                    reason=f"{type(exc).__name__}: {exc}",
                    metadata={"numerical_target_faces": numerical_target},
                )
            )
            return None

    for stage, numerical_target, policy_level in (
        ("strict_qem", target, "strict"),
        ("browser_qem", target, "browser"),
        ("overshoot_qem_075", max(4, int(np.floor(target * 0.75))), "browser"),
        ("overshoot_qem_050", max(4, int(np.floor(target * 0.50))), "aggressive"),
    ):
        candidate = attempt_simplification(
            geometry,
            stage=stage,
            numerical_target=numerical_target,
            policy_level=policy_level,
        )
        if candidate is not None and candidate.face_count <= target:
            return DensityShellFitResult(
                geometry=candidate,
                initial_faces=geometry.face_count,
                initial_target_faces=target,
                final_target_faces=target,
                attempts=tuple(attempts),
                fallback_level=stage,
                target_met=True,
            )

    if profile.allow_recontour:
        for stride in (2, 3, 4):
            stage = f"recontour_stride_{stride}"
            try:
                recontoured = _recontour_field(geometry, stride=stride)
                attempts.append(
                    DensityShellFitAttempt(
                        stage=stage,
                        target_faces=target,
                        input_faces=geometry.face_count,
                        output_faces=recontoured.face_count,
                        accepted=recontoured.face_count <= target,
                    )
                )
                if recontoured.face_count < best.face_count:
                    best = recontoured
                if recontoured.face_count <= target:
                    return DensityShellFitResult(
                        geometry=recontoured,
                        initial_faces=geometry.face_count,
                        initial_target_faces=target,
                        final_target_faces=target,
                        attempts=tuple(attempts),
                        fallback_level=stage,
                        target_met=True,
                    )
                candidate = attempt_simplification(
                    recontoured,
                    stage=stage + "_qem",
                    numerical_target=target,
                    policy_level="aggressive",
                )
                if candidate is not None and candidate.face_count <= target:
                    return DensityShellFitResult(
                        geometry=candidate,
                        initial_faces=geometry.face_count,
                        initial_target_faces=target,
                        final_target_faces=target,
                        attempts=tuple(attempts),
                        fallback_level=stage + "_qem",
                        target_met=True,
                    )
            except Exception as exc:
                attempts.append(
                    DensityShellFitAttempt(
                        stage=stage,
                        target_faces=target,
                        input_faces=geometry.face_count,
                        output_faces=geometry.face_count,
                        accepted=False,
                        reason=f"{type(exc).__name__}: {exc}",
                    )
                )

    return DensityShellFitResult(
        geometry=best,
        initial_faces=geometry.face_count,
        initial_target_faces=target,
        final_target_faces=target,
        attempts=tuple(attempts),
        fallback_level="irreducible",
        target_met=best.face_count <= target,
    )


def fit_density_scene_to_browser_budget(
    geometries: Sequence[DensityShellGeometry],
    *,
    profile: BrowserMeshProfile,
    non_density_trace_count: int,
    simplification_options: MeshSimplificationOptions | None = None,
    progress: ProgressPortLike | None = None,
) -> tuple[tuple[DensityShellGeometry, ...], DensitySceneFitReport]:
    """Measure, reallocate, refit, and exactly validate one density scene."""

    if not isinstance(profile, BrowserMeshProfile):
        raise TypeError("profile must be BrowserMeshProfile.")
    current = tuple(geometries)
    if any(not isinstance(item, DensityShellGeometry) for item in current):
        raise TypeError("geometries must contain DensityShellGeometry records.")
    policy = MeshSimplificationOptions() if simplification_options is None else simplification_options
    if not isinstance(policy, MeshSimplificationOptions):
        raise TypeError("simplification_options must be MeshSimplificationOptions or None.")
    reporter = ProgressEmitter(
        resolve_progress_port(progress), source="plotting.density_scene_fit"
    )
    initial_faces = {item.shell_key: item.face_count for item in current}
    initial_targets = _allocate_targets(current, profile=profile)
    result_by_key: dict[str, DensityShellFitResult] = {
        item.shell_key: DensityShellFitResult(
            geometry=item,
            initial_faces=item.face_count,
            initial_target_faces=initial_targets.get(item.shell_key, item.face_count),
            final_target_faces=initial_targets.get(item.shell_key, item.face_count),
            attempts=(),
            fallback_level="none",
            target_met=item.face_count <= initial_targets.get(item.shell_key, item.face_count),
        )
        for item in current
    }
    iterations = 0
    for iteration in range(profile.max_fit_iterations + 1):
        iterations = iteration
        usage = _usage(
            current,
            non_density_trace_count=non_density_trace_count,
            metadata={"fit_iteration": iteration, "profile": profile.name},
        )
        budget_report = evaluate_browser_mesh_budget(
            usage, budget=profile.budget
        )
        reporter.update(
            "scene_measurement",
            f"iteration={iteration}, faces={usage.final_density_face_count}, "
            f"vertices={usage.final_density_vertex_count}",
            current=iteration,
            total=profile.max_fit_iterations,
            unit="iterations",
            metadata={
                "faces": usage.final_density_face_count,
                "vertices": usage.final_density_vertex_count,
                "violations": "; ".join(budget_report.violations),
            },
        )
        # HTML bytes are unavailable before serialization; every other hard
        # geometry limit must pass here.
        geometry_violations = tuple(
            value for value in budget_report.violations if not value.startswith("final_html_bytes=")
        )
        if not geometry_violations:
            report = DensitySceneFitReport(
                profile=profile,
                shell_results=tuple(result_by_key[item.shell_key] for item in current),
                usage=usage,
                passed=True,
                violations=(),
                iterations=iteration,
                metadata={
                    "initial_total_faces": sum(initial_faces.values()),
                    "policy": "closed_loop_weighted_periodic_v1",
                },
            )
            reporter.completed(
                "scene_fit",
                f"fit complete at {usage.final_density_face_count} serialized faces",
                metadata={"iterations": iteration},
            )
            return current, report
        if iteration >= profile.max_fit_iterations:
            break
        targets = _allocate_targets(current, profile=profile)
        updated: list[DensityShellGeometry] = []
        reduced = False
        reporter.started(
            "shell_refit",
            "refitting overspending density shells",
            current=0,
            total=len(current),
            unit="shells",
        )
        for position, item in enumerate(current, start=1):
            target = targets[item.shell_key]
            if item.face_count <= target:
                updated.append(item)
                continue
            result = fit_density_shell(
                item,
                target_faces=target,
                simplification_options=policy,
                profile=profile,
            )
            result_by_key[item.shell_key] = replace(
                result,
                initial_faces=initial_faces[item.shell_key],
                initial_target_faces=initial_targets[item.shell_key],
                final_target_faces=target,
            )
            updated.append(result.geometry)
            reduced |= result.geometry.face_count < item.face_count
            reporter.update(
                "shell_refit",
                f"{item.shell_key}: {item.face_count}->{result.geometry.face_count} faces",
                current=position,
                total=len(current),
                unit="shells",
                metadata={
                    "shell_key": item.shell_key,
                    "target_faces": target,
                    "fallback_level": result.fallback_level,
                },
            )
        current = tuple(updated)
        if not reduced:
            break

    usage = _usage(
        current,
        non_density_trace_count=non_density_trace_count,
        metadata={"fit_iteration": iterations, "profile": profile.name},
    )
    budget_report = evaluate_browser_mesh_budget(usage, budget=profile.budget)
    report = DensitySceneFitReport(
        profile=profile,
        shell_results=tuple(result_by_key[item.shell_key] for item in current),
        usage=usage,
        passed=budget_report.passed,
        violations=budget_report.violations,
        iterations=iterations,
        metadata={
            "initial_total_faces": sum(initial_faces.values()),
            "policy": "closed_loop_weighted_periodic_v1",
            "irreducible": True,
        },
    )
    if not report.passed:
        # Preserve the package's structured browser-budget exception while
        # attaching the detailed fitting audit for callers and batch logs.
        failure = BrowserMeshBudgetFailure(budget_report)
        failure.fit_report = report  # type: ignore[attr-defined]
        raise failure
    return current, report
