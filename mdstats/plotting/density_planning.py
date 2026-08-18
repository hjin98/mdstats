"""Bounded transactional planning for periodic density scenes.

Architecture gate LD0-R3 separates conservative metadata bounds, exact integer
index planning, and global approval from floating density allocation.  The current implementation plans the dense backend with either
``legacy_spectral_v1`` or ``discrete_periodized_v1``. Sparse-specific counts
remain zero until their owning gates are implemented.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np
from numpy.typing import NDArray

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import (
    DensityTimeModel,
    calibrate_density_time_model,
    derive_density_numeric_limits,
    resolve_runtime_resource_budget,
)

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]

DENSITY_PLANNING_LIMITS_SCHEMA = "mdstats.density-planning-limits.v1"
DENSITY_PHASE_A_PLAN_SCHEMA = "mdstats.density-phase-a-field-plan.v1"
DENSITY_PHASE_B_PLAN_SCHEMA = "mdstats.density-phase-b-field-plan.v1"
DENSITY_SCENE_PLAN_SCHEMA = "mdstats.density-scene-plan.v3"
_DENSITY_SCENE_PLAN_V1_SCHEMA = "mdstats.density-scene-plan.v1"
_DENSITY_SCENE_PLAN_V2_SCHEMA = "mdstats.density-scene-plan.v2"
_LEGACY_DENSITY_SCENE_PLAN_SCHEMAS = frozenset({
    _DENSITY_SCENE_PLAN_V1_SCHEMA,
    _DENSITY_SCENE_PLAN_V2_SCHEMA,
})


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a nonnegative integer.")
    result = int(value)
    if result < 0:
        raise GraphStyleError(f"{name} must be nonnegative.")
    return result


def _positive_int(value: Any, *, name: str) -> int:
    result = _nonnegative_int(value, name=name)
    if result == 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _readonly_int_array(value: Any, *, name: str) -> IntArray:
    array = np.array(value, dtype=np.int64, copy=True, order="C")
    if array.ndim != 1:
        raise GraphAdapterError(f"{name} must be one-dimensional.")
    if np.any(array < 0):
        raise GraphAdapterError(f"{name} must contain nonnegative indices.")
    if array.size > 1 and np.any(array[1:] <= array[:-1]):
        raise GraphAdapterError(f"{name} must be strictly increasing and unique.")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class DensityPlanningLimits:
    """Resolved low-level density limits.

    Direct construction is runtime-derived when values are omitted.  Complete
    framework scenes normally obtain this record from
    :class:`FrameworkDynamicsResources`; explicit values remain available for
    tests and expert policies.
    """

    max_density_fields: int | None = None
    max_density_voxels: int | None = None
    max_density_samples: int | None = None
    max_density_sample_bytes: int | None = None
    max_density_planning_bytes: int | None = None
    max_density_stencil_values: int | None = None
    max_density_nonzero_nodes: int | None = None
    max_density_stored_block_values: int | None = None
    max_density_blocks: int | None = None
    max_density_kernel_pairs: int | None = None
    max_density_component_values: int | None = None
    max_density_mesh_cells: int | None = None
    max_density_mesh_faces: int | None = None
    max_density_render_points: int | None = None
    max_density_total_peak_bytes: int | None = None
    max_density_threads: int | None = None
    max_density_wall_time_seconds: float | None = None
    time_model: DensityTimeModel | None = None
    schema_version: str = DENSITY_PLANNING_LIMITS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_PLANNING_LIMITS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-planning limits schema {self.schema_version!r}."
            )
        numeric_names = (
            "max_density_fields",
            "max_density_voxels",
            "max_density_samples",
            "max_density_sample_bytes",
            "max_density_planning_bytes",
            "max_density_stencil_values",
            "max_density_nonzero_nodes",
            "max_density_stored_block_values",
            "max_density_blocks",
            "max_density_kernel_pairs",
            "max_density_component_values",
            "max_density_mesh_cells",
            "max_density_mesh_faces",
            "max_density_render_points",
            "max_density_total_peak_bytes",
        )
        # Primary memory/thread controls are authoritative. Wall time is
        # advisory metadata only. Legacy low-level values may tighten the
        # memory/structural guardrails but cannot relax them or bypass current
        # runtime constraints after deserialization on a smaller allocation.
        budget = resolve_runtime_resource_budget(
            max_memory_bytes=self.max_density_total_peak_bytes,
            max_threads=self.max_density_threads,
            max_wall_time_seconds=self.max_density_wall_time_seconds,
        )
        model = (
            calibrate_density_time_model(max_threads=budget.max_threads)
            if self.time_model is None
            else self.time_model
        )
        if not isinstance(model, DensityTimeModel):
            raise TypeError("time_model must be DensityTimeModel or None.")
        derived = derive_density_numeric_limits(budget=budget, time_model=model)
        for name in numeric_names:
            current = getattr(self, name)
            resolved = (
                derived[name]
                if current is None
                else min(derived[name], _positive_int(current, name=name))
            )
            object.__setattr__(self, name, resolved)
        object.__setattr__(self, "max_density_threads", budget.max_threads)
        object.__setattr__(
            self, "max_density_wall_time_seconds", budget.max_wall_time_seconds
        )
        object.__setattr__(self, "time_model", model)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
                if name not in {"schema_version", "time_model"}
            },
            "time_model": self.time_model.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityPlanningLimits":
        data = dict(value)
        time_model = data.get("time_model")
        if isinstance(time_model, Mapping):
            data["time_model"] = DensityTimeModel(**dict(time_model))
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DensityPhaseAFieldPlan:
    """Conservative metadata-only bounds for one density field."""

    field_key: str
    source_kind: str
    construction_order: int
    sample_count_upper: int
    sample_bytes_upper: int
    logical_node_count_upper: int
    cic_insertions_upper: int
    stencil_value_count_upper: int
    nonzero_node_count_upper: int
    stored_value_count_upper: int
    stored_block_count_upper: int
    kernel_pair_count_upper: int
    component_value_count_upper: int
    mesh_cell_count_upper: int
    mesh_face_count_upper: int
    render_point_count_upper: int
    retained_bytes_upper: int
    transient_bytes_upper: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_PHASE_A_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_PHASE_A_PLAN_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported phase-A plan schema {self.schema_version!r}."
            )
        if not self.field_key or not self.source_kind:
            raise GraphAdapterError("field_key and source_kind must be nonempty.")
        object.__setattr__(
            self,
            "construction_order",
            _nonnegative_int(self.construction_order, name="construction_order"),
        )
        for name in (
            "sample_count_upper",
            "sample_bytes_upper",
            "logical_node_count_upper",
            "cic_insertions_upper",
            "stencil_value_count_upper",
            "nonzero_node_count_upper",
            "stored_value_count_upper",
            "stored_block_count_upper",
            "kernel_pair_count_upper",
            "component_value_count_upper",
            "mesh_cell_count_upper",
            "mesh_face_count_upper",
            "render_point_count_upper",
            "retained_bytes_upper",
            "transient_bytes_upper",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if self.nonzero_node_count_upper > self.logical_node_count_upper:
            raise GraphAdapterError("Phase-A nonzero-node bound exceeds logical-node bound.")
        backend = str(freeze_json_mapping(self.metadata).get("backend", "dense"))
        if backend == "dense" and self.stored_value_count_upper < self.logical_node_count_upper:
            raise GraphAdapterError("Dense Phase-A stored-value bound is below logical nodes.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        result = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name not in {"metadata"}
        }
        result["metadata"] = self.metadata.to_json_dict()
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityPhaseAFieldPlan":
        return cls(**dict(value))


@dataclass(frozen=True, slots=True)
class DensityPhaseBFieldPlan:
    """Exact dense-backend index plan for one density field."""

    field_key: str
    source_kind: str
    construction_order: int
    sample_count: int
    sample_bytes: int
    grid_shape: tuple[int, int, int]
    logical_node_count: int
    occupied_cic_node_indices: IntArray
    nonzero_node_count_upper: int
    stored_value_count: int
    stored_block_count: int
    stencil_value_count: int
    kernel_pair_count: int
    component_value_count: int
    mesh_cell_count: int
    mesh_face_count_upper: int
    render_point_count_upper: int
    planning_bytes: int
    retained_bytes: int
    transient_bytes_upper: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_PHASE_B_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_PHASE_B_PLAN_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported phase-B plan schema {self.schema_version!r}."
            )
        if not self.field_key or not self.source_kind:
            raise GraphAdapterError("field_key and source_kind must be nonempty.")
        order = _nonnegative_int(self.construction_order, name="construction_order")
        shape = tuple(_positive_int(v, name="grid_shape entry") for v in self.grid_shape)
        if len(shape) != 3:
            raise GraphAdapterError("grid_shape must contain three entries.")
        logical = _positive_int(self.logical_node_count, name="logical_node_count")
        if logical != int(np.prod(shape, dtype=object)):
            raise GraphAdapterError("logical_node_count does not match grid_shape.")
        indices = _readonly_int_array(
            self.occupied_cic_node_indices,
            name="occupied_cic_node_indices",
        )
        if indices.size and int(indices[-1]) >= logical:
            raise GraphAdapterError("occupied CIC node index exceeds the logical grid.")
        object.__setattr__(self, "construction_order", order)
        object.__setattr__(self, "grid_shape", shape)
        object.__setattr__(self, "logical_node_count", logical)
        object.__setattr__(self, "occupied_cic_node_indices", indices)
        for name in (
            "sample_count",
            "sample_bytes",
            "nonzero_node_count_upper",
            "stored_value_count",
            "stored_block_count",
            "stencil_value_count",
            "kernel_pair_count",
            "component_value_count",
            "mesh_cell_count",
            "mesh_face_count_upper",
            "render_point_count_upper",
            "planning_bytes",
            "retained_bytes",
            "transient_bytes_upper",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if self.nonzero_node_count_upper > logical:
            raise GraphAdapterError("nonzero_node_count_upper exceeds logical nodes.")
        backend = str(freeze_json_mapping(self.metadata).get("backend", "dense"))
        if backend == "dense" and self.stored_value_count < logical:
            raise GraphAdapterError("Dense stored_value_count is below logical nodes.")
        if indices.size > self.nonzero_node_count_upper:
            raise GraphAdapterError("Occupied CIC nodes exceed the nonzero-node upper bound.")
        if self.planning_bytes < int(indices.nbytes):
            raise GraphAdapterError("planning_bytes is below retained planning-array bytes.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def occupied_cic_node_count(self) -> int:
        return int(self.occupied_cic_node_indices.size)

    def to_json_dict(self, *, include_indices: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            name: getattr(self, name)
            for name in self.__dataclass_fields__
            if name not in {"occupied_cic_node_indices", "metadata"}
        }
        result["occupied_cic_node_count"] = self.occupied_cic_node_count
        if include_indices:
            result["occupied_cic_node_indices"] = self.occupied_cic_node_indices.tolist()
        result["metadata"] = self.metadata.to_json_dict()
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityPhaseBFieldPlan":
        data = dict(value)
        data.pop("occupied_cic_node_count", None)
        if "occupied_cic_node_indices" not in data:
            raise GraphAdapterError("Phase-B JSON requires occupied_cic_node_indices.")
        data["occupied_cic_node_indices"] = np.asarray(
            data["occupied_cic_node_indices"], dtype=np.int64
        )
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DensityScenePlan:
    """Globally approved Phase-A/Phase-B/Phase-C density transaction."""

    phase_a_fields: tuple[DensityPhaseAFieldPlan, ...]
    phase_b_fields: tuple[DensityPhaseBFieldPlan, ...]
    limits: DensityPlanningLimits
    phase_a_approved: bool
    phase_b_approved: bool
    phase_c_approved: bool
    planning_bytes: int
    retained_bytes: int
    estimated_peak_bytes: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_SCENE_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {DENSITY_SCENE_PLAN_SCHEMA, *_LEGACY_DENSITY_SCENE_PLAN_SCHEMAS}:
            raise GraphAdapterError(
                f"Unsupported density-scene plan schema {self.schema_version!r}."
            )
        if not isinstance(self.limits, DensityPlanningLimits):
            raise TypeError("limits must be DensityPlanningLimits.")
        phase_a = tuple(self.phase_a_fields)
        phase_b = tuple(self.phase_b_fields)
        if tuple(v.construction_order for v in phase_a) != tuple(range(len(phase_a))):
            raise GraphAdapterError("Phase-A construction orders must be contiguous from zero.")
        if tuple(v.construction_order for v in phase_b) != tuple(range(len(phase_b))):
            raise GraphAdapterError("Phase-B construction orders must be contiguous from zero.")
        if tuple(v.field_key for v in phase_a) != tuple(v.field_key for v in phase_b):
            raise GraphAdapterError("Phase-A and Phase-B field orders do not match.")
        object.__setattr__(self, "phase_a_fields", phase_a)
        object.__setattr__(self, "phase_b_fields", phase_b)
        for name in ("planning_bytes", "retained_bytes", "estimated_peak_bytes"):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if self.phase_c_approved and not (self.phase_a_approved and self.phase_b_approved):
            raise GraphAdapterError("Phase C cannot be approved before Phases A and B.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def _legacy_execution_identity_payload(self) -> dict[str, Any]:
        """Return the complete historical execution-plan identity payload.

        Version-1 scene approvals intentionally included runtime limits, calibrated
        timing evidence, storage backend choice, and estimated memory.  Keep this
        exact payload for historical deserialization/digest compatibility and expose
        the same information under :attr:`execution_plan_id` for version 2.
        """

        return {
            "schema_version": self.schema_version,
            "fields": [v.to_json_dict(include_indices=False) for v in self.phase_b_fields],
            "limits": self.limits.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
            "planning_bytes": self.planning_bytes,
            "retained_bytes": self.retained_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
        }

    @staticmethod
    def _scientific_field_identity_v1(field_plan: DensityPhaseBFieldPlan) -> dict[str, Any]:
        """Return the PAR-DENS2/v2 scientific identity projection.

        This projection is frozen for historical v2 digest compatibility.  It
        intentionally reflects the exact 0.20.141a0 exclusion set, even though
        PAR-DENS3 identifies additional execution-only sparse/hybrid metadata.
        """

        metadata = field_plan.metadata.to_json_dict()
        for key in (
            "backend",
            "backend_selection",
            "phase_b_execution_planner",
            "kernel_pair_semantics",
            "exact_contribution_count",
            "direct_pair_count",
            "fft_padded_node_count",
            "hybrid_estimated_wall_seconds",
            "estimated_wall_seconds",
            "time_model_source",
        ):
            metadata.pop(key, None)
        return {
            "field_key": field_plan.field_key,
            "source_kind": field_plan.source_kind,
            "construction_order": field_plan.construction_order,
            "sample_count": field_plan.sample_count,
            "grid_shape": list(field_plan.grid_shape),
            "logical_node_count": field_plan.logical_node_count,
            "metadata": metadata,
        }

    @staticmethod
    def _scientific_field_identity_v2(field_plan: DensityPhaseBFieldPlan) -> dict[str, Any]:
        """Return PAR-DENS3 worker/storage/executor-neutral field identity."""

        metadata = field_plan.metadata.to_json_dict()
        # These keys describe representation, executor selection, cache state,
        # calibrated cost, or memory/work decomposition.  None changes the
        # continuous density definition.  Keep them in execution_plan_id and
        # serialized diagnostics, but never in the scientific/cache authority.
        execution_only = {
            "backend",
            "backend_selection",
            "block_shape",
            "block_lattice_shape",
            "active_target_node_count",
            "valid_block_value_count",
            "allocated_block_value_count",
            "partial_block_count",
            "rendering_available_from_ld2",
            "sparse_evaluation_mode",
            "sparse_realization_mode",
            "phase_b_execution_planner",
            "phase_b_support_planner",
            "stencil_cache_enabled",
            "stencil_cache_hit_during_planning",
            "routing_cache_hit_during_planning",
            "source_block_count",
            "source_node_count",
            "support_atlas_target_block_count",
            "support_atlas_target_node_count",
            "hybrid_compute_tile_count",
            "hybrid_direct_tile_count",
            "hybrid_fft_tile_count",
            "exact_contribution_count",
            "direct_pair_count",
            "fft_padded_node_count",
            "hybrid_estimated_wall_seconds",
            "hybrid_predicted_peak_bytes",
            "hybrid_plan_identity",
            "kernel_pair_semantics",
            "nominal_all_direct_pairs_are_diagnostic_only",
            "streaming_scatter",
            "streaming_scatter_chunk_pair_upper",
            "sparse_pair_chunk_size",
            "sparse_group_batch_size",
            "estimated_wall_seconds",
            "time_model_source",
            "fft_workers",
            "fft_worker_source",
            "fft_worker_policy",
            "fft_worker_execution_policy",
            "max_threads",
            "max_wall_time_seconds",
            "resource_policy",
            "pair_chunk_source",
            "timing_overrides_are_tightening_only",
        }
        for key in execution_only:
            metadata.pop(key, None)
        return {
            "field_key": field_plan.field_key,
            "source_kind": field_plan.source_kind,
            "construction_order": field_plan.construction_order,
            "sample_count": field_plan.sample_count,
            "grid_shape": list(field_plan.grid_shape),
            "logical_node_count": field_plan.logical_node_count,
            "metadata": metadata,
        }

    def _scientific_identity_payload_v1(self) -> dict[str, Any]:
        """Return the frozen 0.20.141a0/v2 scientific identity payload."""

        metadata = self.metadata.to_json_dict()
        scientific_metadata = {
            key: value
            for key, value in metadata.items()
            if key
            not in {
                "backend", "total_stored_values", "total_dense_voxels",
                "total_nonzero_node_upper", "total_stencil_values",
                "total_blocks", "total_kernel_pairs",
                "total_direct_kernel_pairs", "total_exact_contributions",
                "total_fft_padded_nodes", "hybrid_field_count",
                "hybrid_estimated_wall_seconds_raw", "nonhybrid_kernel_pairs",
                "kernel_pair_semantics", "total_mesh_cells",
                "total_mesh_faces_upper", "total_render_points_upper",
                "estimated_preparation_wall_seconds",
                "max_density_wall_time_seconds", "wall_time_admission_enforced",
                "wall_time_budget_exceeded", "max_density_threads",
                "density_time_model",
            }
        }
        return {
            "schema_version": _DENSITY_SCENE_PLAN_V2_SCHEMA,
            "identity_semantics": "worker_backend_neutral_scientific_plan_v1",
            "fields": [
                self._scientific_field_identity_v1(field_plan)
                for field_plan in self.phase_b_fields
            ],
            "metadata": scientific_metadata,
        }

    def _scientific_identity_payload(self) -> dict[str, Any]:
        """Return the PAR-DENS3 scientific identity payload."""

        old = self._scientific_identity_payload_v1()
        return {
            "schema_version": DENSITY_SCENE_PLAN_SCHEMA,
            "identity_semantics": "worker_storage_executor_neutral_scientific_plan_v2",
            "fields": [
                self._scientific_field_identity_v2(field_plan)
                for field_plan in self.phase_b_fields
            ],
            "metadata": old["metadata"],
        }

    @staticmethod
    def _hash_identity_payload(payload: Mapping[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(encoded.encode("ascii")).hexdigest()

    @property
    def execution_plan_id(self) -> str:
        """Hash the complete resource/backend execution plan for diagnostics."""

        return self._hash_identity_payload(self._legacy_execution_identity_payload())

    @property
    def approval_id(self) -> str:
        """Return the authoritative scene identity.

        Historical v1 plans retain their exact resource-sensitive digest. New v2
        plans use worker/backend-neutral scientific identity; the complete execution
        realization remains auditable through :attr:`execution_plan_id`.
        """

        if self.schema_version == _DENSITY_SCENE_PLAN_V1_SCHEMA:
            return self.execution_plan_id
        if self.schema_version == _DENSITY_SCENE_PLAN_V2_SCHEMA:
            return self._hash_identity_payload(self._scientific_identity_payload_v1())
        return self._hash_identity_payload(self._scientific_identity_payload())

    def to_json_dict(self, *, include_indices: bool = False) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "phase_a_fields": [v.to_json_dict() for v in self.phase_a_fields],
            "phase_b_fields": [v.to_json_dict(include_indices=include_indices) for v in self.phase_b_fields],
            "limits": self.limits.to_json_dict(),
            "phase_a_approved": self.phase_a_approved,
            "phase_b_approved": self.phase_b_approved,
            "phase_c_approved": self.phase_c_approved,
            "planning_bytes": self.planning_bytes,
            "retained_bytes": self.retained_bytes,
            "estimated_peak_bytes": self.estimated_peak_bytes,
            "approval_id": self.approval_id,
            "metadata": self.metadata.to_json_dict(),
        }
        if self.schema_version in {DENSITY_SCENE_PLAN_SCHEMA, _DENSITY_SCENE_PLAN_V2_SCHEMA}:
            result["execution_plan_id"] = self.execution_plan_id
            result["approval_identity_semantics"] = (
                "worker_storage_executor_neutral_scientific_plan_v2"
                if self.schema_version == DENSITY_SCENE_PLAN_SCHEMA
                else "worker_backend_neutral_scientific_plan_v1"
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityScenePlan":
        data = dict(value)
        data.pop("approval_id", None)
        data.pop("execution_plan_id", None)
        data.pop("approval_identity_semantics", None)
        return cls(
            schema_version=str(data["schema_version"]),
            phase_a_fields=tuple(
                DensityPhaseAFieldPlan.from_json_dict(item)
                for item in data["phase_a_fields"]
            ),
            phase_b_fields=tuple(
                DensityPhaseBFieldPlan.from_json_dict(item)
                for item in data["phase_b_fields"]
            ),
            limits=DensityPlanningLimits.from_json_dict(data["limits"]),
            phase_a_approved=bool(data["phase_a_approved"]),
            phase_b_approved=bool(data["phase_b_approved"]),
            phase_c_approved=bool(data["phase_c_approved"]),
            planning_bytes=int(data["planning_bytes"]),
            retained_bytes=int(data["retained_bytes"]),
            estimated_peak_bytes=int(data["estimated_peak_bytes"]),
            metadata=data.get("metadata", {}),
        )


def sample_byte_count(sample_count: int, *, include_groups: bool = False) -> int:
    """Return bytes for positions, weights, and optional int64 group identifiers."""

    count = _nonnegative_int(sample_count, name="sample_count")
    return count * (32 + (8 if include_groups else 0))


def dense_retained_bytes(
    logical_node_count: int,
    *,
    sample_count: int = 0,
    store_sample_positions: bool = False,
) -> int:
    nodes = _nonnegative_int(logical_node_count, name="logical_node_count")
    samples = _nonnegative_int(sample_count, name="sample_count")
    return 8 * nodes + (24 * samples if store_sample_positions else 0)


def dense_transient_bytes(logical_node_count: int, sample_count: int) -> int:
    """Conservative package-owned workspace bound for dense preparation."""

    nodes = _nonnegative_int(logical_node_count, name="logical_node_count")
    samples = _nonnegative_int(sample_count, name="sample_count")
    return 256 * nodes + 64 * samples + sample_byte_count(samples)


def occupied_cic_node_indices(
    fractional_positions: FloatArray,
    grid_shape: tuple[int, int, int],
    *,
    max_planning_bytes: int,
) -> IntArray:
    """Return exact sorted periodic CIC target-node indices without a dense grid."""

    fractional = np.asarray(fractional_positions, dtype=np.float64)
    if fractional.ndim != 2 or fractional.shape[1:] != (3,):
        raise GraphAdapterError("fractional_positions must have shape (n_samples, 3).")
    if np.any(~np.isfinite(fractional)):
        raise GraphAdapterError("fractional_positions must be finite.")
    shape = tuple(_positive_int(v, name="grid_shape entry") for v in grid_shape)
    if len(shape) != 3:
        raise GraphAdapterError("grid_shape must contain three entries.")
    count = int(fractional.shape[0])
    temporary_upper = 8 * count * 8 + max(8, min(8 * count, int(np.prod(shape)))) * 8
    if temporary_upper > int(max_planning_bytes):
        raise GraphComplexityError(
            "Phase B occupied-CIC planning requires at most "
            f"{temporary_upper} bytes, exceeding max_density_planning_bytes="
            f"{int(max_planning_bytes)}."
        )
    if count == 0:
        result = np.empty(0, dtype=np.int64)
        result.setflags(write=False)
        return result
    folded = fractional - np.floor(fractional)
    scale = np.asarray(shape, dtype=np.float64)
    scaled = folded * scale
    base = np.floor(scaled).astype(np.int64)
    delta = scaled - base
    chunks: list[IntArray] = []
    for ox in (0, 1):
        wx = (1.0 - delta[:, 0]) if ox == 0 else delta[:, 0]
        ix = (base[:, 0] + ox) % shape[0]
        for oy in (0, 1):
            wy = (1.0 - delta[:, 1]) if oy == 0 else delta[:, 1]
            iy = (base[:, 1] + oy) % shape[1]
            for oz in (0, 1):
                wz = (1.0 - delta[:, 2]) if oz == 0 else delta[:, 2]
                mask = wx * wy * wz > 0.0
                if not np.any(mask):
                    continue
                iz = (base[:, 2] + oz) % shape[2]
                flat = np.ravel_multi_index(
                    (ix[mask], iy[mask], iz[mask]), shape, order="C"
                ).astype(np.int64, copy=False)
                chunks.append(flat)
    if not chunks:
        result = np.empty(0, dtype=np.int64)
    else:
        result = np.unique(np.concatenate(chunks)).astype(np.int64, copy=False)
    result.setflags(write=False)
    return result


def _check_limit(*, phase: str, context: str, value: int, limit: int, name: str) -> None:
    if value > limit:
        raise GraphComplexityError(
            f"{phase} density planning for {context} requires {value} for {name}, "
            f"exceeding {name}={limit}."
        )


def _validate_phase_a_limits(
    fields: Sequence[DensityPhaseAFieldPlan], limits: DensityPlanningLimits
) -> None:
    if len(fields) > limits.max_density_fields:
        raise GraphComplexityError(
            f"Phase A density planning requested {len(fields)} fields, exceeding "
            f"the remaining max_density_fields={limits.max_density_fields}."
        )
    for field_plan in fields:
        context = repr(field_plan.field_key)
        for value, limit, name in (
            (field_plan.sample_count_upper, limits.max_density_samples, "max_density_samples"),
            (field_plan.sample_bytes_upper, limits.max_density_sample_bytes, "max_density_sample_bytes"),
            (field_plan.stencil_value_count_upper, limits.max_density_stencil_values, "max_density_stencil_values"),
            (field_plan.nonzero_node_count_upper, limits.max_density_nonzero_nodes, "max_density_nonzero_nodes"),
            (field_plan.stored_value_count_upper, limits.max_density_stored_block_values, "max_density_stored_block_values"),
            (field_plan.stored_block_count_upper, limits.max_density_blocks, "max_density_blocks"),
            (field_plan.kernel_pair_count_upper, limits.max_density_kernel_pairs, "max_density_kernel_pairs"),
            (field_plan.component_value_count_upper, limits.max_density_component_values, "max_density_component_values"),
            (field_plan.mesh_cell_count_upper, limits.max_density_mesh_cells, "max_density_mesh_cells"),
            (field_plan.mesh_face_count_upper, limits.max_density_mesh_faces, "max_density_mesh_faces"),
            (field_plan.render_point_count_upper, limits.max_density_render_points, "max_density_render_points"),
        ):
            _check_limit(phase="Phase A", context=context, value=value, limit=limit, name=name)



def validate_density_phase_a(
    fields: Sequence[DensityPhaseAFieldPlan],
    limits: DensityPlanningLimits,
) -> tuple[DensityPhaseAFieldPlan, ...]:
    """Validate and return deterministic Phase-A field bounds."""

    result = tuple(fields)
    if tuple(v.construction_order for v in result) != tuple(range(len(result))):
        raise GraphAdapterError("Phase-A construction orders must be contiguous from zero.")
    _validate_phase_a_limits(result, limits)
    return result

def _validate_phase_b_against_a(
    phase_a: DensityPhaseAFieldPlan, phase_b: DensityPhaseBFieldPlan
) -> None:
    comparisons = (
        (phase_b.sample_count, phase_a.sample_count_upper, "sample_count"),
        (phase_b.sample_bytes, phase_a.sample_bytes_upper, "sample_bytes"),
        (phase_b.logical_node_count, phase_a.logical_node_count_upper, "logical_node_count"),
        (phase_b.occupied_cic_node_count, phase_a.nonzero_node_count_upper, "occupied_cic_node_count"),
        (phase_b.stored_value_count, phase_a.stored_value_count_upper, "stored_value_count"),
        (phase_b.stored_block_count, phase_a.stored_block_count_upper, "stored_block_count"),
        (phase_b.stencil_value_count, phase_a.stencil_value_count_upper, "stencil_value_count"),
        (phase_b.kernel_pair_count, phase_a.kernel_pair_count_upper, "kernel_pair_count"),
        (phase_b.component_value_count, phase_a.component_value_count_upper, "component_value_count"),
        (phase_b.mesh_cell_count, phase_a.mesh_cell_count_upper, "mesh_cell_count"),
        (phase_b.mesh_face_count_upper, phase_a.mesh_face_count_upper, "mesh_face_count_upper"),
        (phase_b.render_point_count_upper, phase_a.render_point_count_upper, "render_point_count_upper"),
        (phase_b.retained_bytes, phase_a.retained_bytes_upper, "retained_bytes"),
        (phase_b.transient_bytes_upper, phase_a.transient_bytes_upper, "transient_bytes_upper"),
    )
    for exact, upper, name in comparisons:
        if exact > upper:
            raise GraphComplexityError(
                f"Phase-B planner defect for {phase_b.field_key!r}: exact {name}={exact} "
                f"exceeds Phase-A bound {upper}."
            )


def plan_density_scene(
    *,
    phase_a_fields: Sequence[DensityPhaseAFieldPlan],
    phase_b_fields: Sequence[DensityPhaseBFieldPlan],
    limits: DensityPlanningLimits,
    metadata: Mapping[str, Any] | None = None,
) -> DensityScenePlan:
    """Approve one dense density scene after Phase-A and Phase-B planning."""

    phase_a = tuple(phase_a_fields)
    phase_b = tuple(phase_b_fields)
    _validate_phase_a_limits(phase_a, limits)
    if len(phase_a) != len(phase_b):
        raise GraphAdapterError("Phase-A and Phase-B field counts differ.")
    if tuple(v.field_key for v in phase_a) != tuple(v.field_key for v in phase_b):
        raise GraphAdapterError("Phase-A and Phase-B field orders differ.")
    for upper, exact in zip(phase_a, phase_b, strict=True):
        _validate_phase_b_against_a(upper, exact)

    planning_bytes = int(sum(v.planning_bytes for v in phase_b))
    retained_bytes = int(sum(v.retained_bytes for v in phase_b))
    total_stored_values = int(sum(v.stored_value_count for v in phase_b))
    total_dense_voxels = int(
        sum(
            v.stored_value_count
            for v in phase_b
            if str(v.metadata.get("backend", "dense")) == "dense"
        )
    )
    total_samples = int(sum(v.sample_count for v in phase_b))
    total_sample_bytes = int(sum(v.sample_bytes for v in phase_b))
    total_nonzero = int(sum(v.nonzero_node_count_upper for v in phase_b))
    total_stencil_values = int(sum(v.stencil_value_count for v in phase_b))
    total_blocks = int(sum(v.stored_block_count for v in phase_b))
    total_kernel_pairs = int(sum(v.kernel_pair_count for v in phase_b))
    hybrid_fields = tuple(
        v
        for v in phase_b
        if str(v.metadata.get("phase_b_execution_planner", ""))
        == "ld8_s3_hybrid_exact_v1"
    )
    hybrid_estimated_wall_seconds_raw = float(
        sum(
            float(v.metadata.get("hybrid_estimated_wall_seconds", 0.0))
            for v in hybrid_fields
        )
    )
    total_exact_contributions = int(
        sum(
            int(v.metadata.get("exact_contribution_count", v.kernel_pair_count))
            for v in phase_b
        )
    )
    total_fft_padded_nodes = int(
        sum(int(v.metadata.get("fft_padded_node_count", 0)) for v in hybrid_fields)
    )
    nonhybrid_kernel_pairs = int(
        sum(
            v.kernel_pair_count
            for v in phase_b
            if str(v.metadata.get("phase_b_execution_planner", ""))
            != "ld8_s3_hybrid_exact_v1"
        )
    )
    total_mesh_cells = int(sum(v.mesh_cell_count for v in phase_b))
    total_mesh_faces = int(sum(v.mesh_face_count_upper for v in phase_b))
    total_render_points = int(sum(v.render_point_count_upper for v in phase_b))

    for value, limit, name in (
        (planning_bytes, limits.max_density_planning_bytes, "max_density_planning_bytes"),
        (total_dense_voxels, limits.max_density_voxels, "max_density_voxels"),
        (total_samples, limits.max_density_samples, "max_density_samples"),
        (total_sample_bytes, limits.max_density_sample_bytes, "max_density_sample_bytes"),
        (total_nonzero, limits.max_density_nonzero_nodes, "max_density_nonzero_nodes"),
        (total_stencil_values, limits.max_density_stencil_values, "max_density_stencil_values"),
        (total_stored_values, limits.max_density_stored_block_values, "max_density_stored_block_values"),
        (total_blocks, limits.max_density_blocks, "max_density_blocks"),
        (total_mesh_cells, limits.max_density_mesh_cells, "max_density_mesh_cells"),
        (total_mesh_faces, limits.max_density_mesh_faces, "max_density_mesh_faces"),
        (total_render_points, limits.max_density_render_points, "max_density_render_points"),
    ):
        _check_limit(phase="Phase C", context="the scene", value=value, limit=limit, name=name)

    if total_kernel_pairs > limits.max_density_kernel_pairs:
        raise GraphComplexityError(
            "Phase C density planning requires "
            f"{total_kernel_pairs} actual direct/legacy kernel pairs, exceeding "
            f"max_density_kernel_pairs={limits.max_density_kernel_pairs}. "
            f"Hybrid fields={len(hybrid_fields)}, nominal exact contributions="
            f"{total_exact_contributions}, FFT padded nodes={total_fft_padded_nodes}. "
            "Nominal all-direct contributions are diagnostic only and were not "
            "used as the hybrid direct-pair count."
        )

    retained_before = 0
    estimated_peak = planning_bytes
    for field_plan in phase_b:
        estimated_peak = max(
            estimated_peak,
            planning_bytes + retained_before + field_plan.transient_bytes_upper,
        )
        retained_before += field_plan.retained_bytes
    estimated_peak = max(estimated_peak, planning_bytes + retained_bytes)
    _check_limit(
        phase="Phase C",
        context="the scene",
        value=estimated_peak,
        limit=limits.max_density_total_peak_bytes,
        name="max_density_total_peak_bytes",
    )

    # Hybrid local-sparse fields already carry the calibrated mixed direct/FFT
    # executor estimate.  Do not reinterpret their nominal exact contribution
    # count as all-direct work.  Legacy sparse plans still use kernel-pair work.
    common_raw_seconds = (
        len(phase_b) * limits.time_model.fixed_seconds_per_field
        + total_samples / limits.time_model.samples_per_second
        + total_stencil_values / limits.time_model.stencil_values_per_second
    )
    execution_raw_seconds = (
        hybrid_estimated_wall_seconds_raw
        + nonhybrid_kernel_pairs / limits.time_model.kernel_pairs_per_second
        + total_dense_voxels / limits.time_model.dense_nodes_per_second
    )
    estimated_preparation_seconds = limits.time_model.safety_multiplier * (
        common_raw_seconds + execution_raw_seconds
    )
    operators = tuple(
        sorted({str(field.metadata.get("operator", "unspecified")) for field in phase_b})
    )
    return DensityScenePlan(
        phase_a_fields=phase_a,
        phase_b_fields=phase_b,
        limits=limits,
        phase_a_approved=True,
        phase_b_approved=True,
        phase_c_approved=True,
        planning_bytes=planning_bytes,
        retained_bytes=retained_bytes,
        estimated_peak_bytes=estimated_peak,
        metadata={
            "backend": (
                next(iter({str(v.metadata.get("backend", "dense")) for v in phase_b}))
                if len({str(v.metadata.get("backend", "dense")) for v in phase_b}) == 1
                else "mixed"
            ),
            "operators": list(operators),
            "operator": operators[0] if len(operators) == 1 else "mixed",
            "total_fields": len(phase_b),
            "total_samples": total_samples,
            "total_sample_bytes": total_sample_bytes,
            "total_logical_nodes": int(sum(v.logical_node_count for v in phase_b)),
            "total_stored_values": total_stored_values,
            "total_dense_voxels": total_dense_voxels,
            "total_nonzero_node_upper": total_nonzero,
            "total_stencil_values": total_stencil_values,
            "total_blocks": total_blocks,
            "total_kernel_pairs": total_kernel_pairs,
            "total_direct_kernel_pairs": total_kernel_pairs,
            "total_exact_contributions": total_exact_contributions,
            "total_fft_padded_nodes": total_fft_padded_nodes,
            "hybrid_field_count": len(hybrid_fields),
            "hybrid_estimated_wall_seconds_raw": hybrid_estimated_wall_seconds_raw,
            "nonhybrid_kernel_pairs": nonhybrid_kernel_pairs,
            "kernel_pair_semantics": "actual_direct_pairs_for_hybrid; all_direct_pairs_for_legacy",
            "total_mesh_cells": total_mesh_cells,
            "total_mesh_faces_upper": total_mesh_faces,
            "total_render_points_upper": total_render_points,
            "estimated_preparation_wall_seconds": estimated_preparation_seconds,
            "max_density_wall_time_seconds": limits.max_density_wall_time_seconds,
            "wall_time_admission_enforced": False,
            "wall_time_budget_exceeded": bool(
                estimated_preparation_seconds > limits.max_density_wall_time_seconds
            ),
            "max_density_threads": limits.max_density_threads,
            "density_time_model": limits.time_model.to_json_dict(),
            **({} if metadata is None else dict(metadata)),
        },
    )


def validate_realized_fields(
    plan: DensityScenePlan,
    fields: Sequence[Any],
) -> dict[str, int]:
    """Verify realized dense fields do not exceed their approved Phase-B plans."""

    realized = tuple(fields)
    if len(realized) != len(plan.phase_b_fields):
        raise GraphComplexityError(
            "Realized density field count does not match the approved scene plan."
        )
    realized_retained = 0
    realized_nonzero = 0
    for field_obj, field_plan in zip(realized, plan.phase_b_fields, strict=True):
        if str(field_obj.field_key) != field_plan.field_key:
            raise GraphComplexityError(
                f"Realized field {field_obj.field_key!r} does not match approved "
                f"field {field_plan.field_key!r}."
            )
        shape = tuple(int(v) for v in field_obj.grid_shape)
        if shape != field_plan.grid_shape:
            raise GraphComplexityError(
                f"Realized grid {shape} for {field_plan.field_key!r} differs from "
                f"approved grid {field_plan.grid_shape}."
            )
        summary = field_obj.storage_summary()
        if summary.stored_value_count > field_plan.stored_value_count:
            raise GraphComplexityError(
                f"Realized stored values for {field_plan.field_key!r} exceed approval."
            )
        if summary.nonzero_node_count > field_plan.nonzero_node_count_upper:
            raise GraphComplexityError(
                f"Realized nonzero nodes for {field_plan.field_key!r} exceed approval."
            )
        retained = int(summary.realized_bytes or summary.estimated_bytes)
        if getattr(field_obj, "sample_positions", None) is not None:
            retained += int(field_obj.sample_positions.nbytes)
        if retained > field_plan.retained_bytes:
            raise GraphComplexityError(
                f"Realized retained bytes for {field_plan.field_key!r} exceed approval."
            )
        realized_retained += retained
        realized_nonzero += int(summary.nonzero_node_count)
    if realized_retained > plan.retained_bytes:
        raise GraphComplexityError("Realized scene retained bytes exceed approval.")
    return {
        "realized_retained_bytes": realized_retained,
        "realized_nonzero_nodes": realized_nonzero,
        "estimated_peak_bytes": plan.estimated_peak_bytes,
        "estimated_retained_bytes": plan.retained_bytes,
        "retained_overestimate_bytes": plan.retained_bytes - realized_retained,
    }
