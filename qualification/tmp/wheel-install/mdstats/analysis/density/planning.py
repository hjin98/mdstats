"""Backend-neutral scientific density grid planning for Stage 11E-GR1.

The planner chooses a logical periodic grid before any storage backend is
considered.  Rendering, mesh, browser, trace, and HTML policies are not valid
inputs to this module.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence

import numpy as np

from ._frozen_json import FrozenJSONMapping, freeze_json_mapping
from .grid_geometry import (
    DensityGridGeometry,
    density_grid_intervals,
    prepare_density_grid_geometry,
    resolve_density_grid_shape,
)
from .numerical_errors import (
    DensityNumericalInputError,
    DensityNumericalResourceError,
    DensityNumericalSerializationError,
)
from .resources import ScientificDensityResourcePolicy

DENSITY_LOGICAL_GRID_PLAN_SCHEMA = "mdstats.density-logical-grid-plan.v1"
DENSITY_NESTED_GRID_LADDER_SCHEMA = "mdstats.density-nested-grid-ladder.v1"
DENSITY_FIELD_REUSE_KEY_SCHEMA = "mdstats.density-field-reuse-key.v1"
DENSITY_BACKEND_CANDIDATE_PLAN_SCHEMA = (
    "mdstats.density-backend-candidate-plan.v1"
)
DENSITY_BACKEND_SELECTION_PLAN_SCHEMA = (
    "mdstats.density-backend-selection-plan.v1"
)


class DensityGridPlanStatus(str, Enum):
    """Resolution outcome of a logical-grid plan."""

    TARGET_REACHED = "target_reached"
    BUDGET_LIMITED = "budget_limited"
    LEVEL_LIMITED = "level_limited"


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _signature(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("ascii")).hexdigest()


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise DensityNumericalInputError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise DensityNumericalInputError(f"{name} must be positive.")
    return result


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise DensityNumericalInputError(f"{name} must be a nonnegative integer.")
    result = int(value)
    if result < 0:
        raise DensityNumericalInputError(f"{name} must be nonnegative.")
    return result


def _positive_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise DensityNumericalInputError(f"{name} must be finite and positive.")
    return result


def _nonnegative_float(value: Any, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise DensityNumericalInputError(
            f"{name} must be finite and nonnegative."
        )
    return result


def _nonempty(value: Any, *, name: str) -> str:
    result = str(value)
    if not result:
        raise DensityNumericalInputError(f"{name} must be nonempty.")
    return result


def _voxel_count(shape: tuple[int, int, int]) -> int:
    return int(np.prod(shape, dtype=object))


def _same_cell(left: DensityGridGeometry, right: DensityGridGeometry) -> bool:
    return bool(
        np.allclose(
            left.display_cell,
            right.display_cell,
            rtol=0.0,
            atol=5.0e-15,
        )
    )


def density_logical_grid_signature(geometry: DensityGridGeometry) -> str:
    """Return a backend-independent signature of one logical periodic grid."""

    if not isinstance(geometry, DensityGridGeometry):
        raise TypeError("geometry must be DensityGridGeometry.")
    return _signature(
        {
            "schema_version": "mdstats.density-logical-grid-identity.v1",
            "display_cell": geometry.display_cell.tolist(),
            "grid_shape": list(geometry.grid_shape),
            "realized_intervals": list(geometry.realized_intervals),
            "voxel_volume": geometry.voxel_volume,
        }
    )


def _geometry_for_shape(
    cell: Any,
    shape: tuple[int, int, int],
    *,
    requested_interval: float | None,
    metadata: Mapping[str, Any] | None = None,
) -> DensityGridGeometry:
    base = prepare_density_grid_geometry(cell, grid_shape=shape, metadata=metadata)
    return DensityGridGeometry(
        display_cell=base.display_cell,
        grid_shape=base.grid_shape,
        requested_grid_interval=requested_interval,
        realized_intervals=base.realized_intervals,
        grid_step_vectors=base.grid_step_vectors,
        cell_volume=base.cell_volume,
        voxel_volume=base.voxel_volume,
        metadata=base.metadata,
    )


def _resolve_voxel_limit(
    *,
    resource_policy: ScientificDensityResourcePolicy | None,
    max_logical_voxels: int | None,
) -> tuple[int, str]:
    if resource_policy is not None and max_logical_voxels is not None:
        raise DensityNumericalInputError(
            "max_logical_voxels cannot be combined with resource_policy."
        )
    if resource_policy is not None:
        if not isinstance(resource_policy, ScientificDensityResourcePolicy):
            raise TypeError(
                "resource_policy must be ScientificDensityResourcePolicy or None."
            )
        return resource_policy.max_total_voxels, resource_policy.signature
    if max_logical_voxels is None:
        raise DensityNumericalInputError(
            "A scientific resource_policy or max_logical_voxels is required."
        )
    limit = _positive_int(max_logical_voxels, name="max_logical_voxels")
    return limit, _signature(
        {
            "schema_version": "mdstats.explicit-density-voxel-limit.v1",
            "max_logical_voxels": limit,
            "resource_domain": "scientific_density",
        }
    )


@dataclass(frozen=True, slots=True)
class DensityLogicalGridPlan:
    """Signed target and finest-feasible logical-grid decision."""

    target_geometry: DensityGridGeometry
    selected_geometry: DensityGridGeometry
    coarsest_geometry: DensityGridGeometry
    max_logical_voxels: int
    scientific_resource_signature: str
    status: DensityGridPlanStatus | str
    reason_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_LOGICAL_GRID_PLAN_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_LOGICAL_GRID_PLAN_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported logical-grid plan schema {self.schema_version!r}."
            )
        if not all(
            isinstance(item, DensityGridGeometry)
            for item in (
                self.target_geometry,
                self.selected_geometry,
                self.coarsest_geometry,
            )
        ):
            raise TypeError("All logical-grid plan geometries must be DensityGridGeometry.")
        if not _same_cell(self.target_geometry, self.selected_geometry) or not _same_cell(
            self.target_geometry, self.coarsest_geometry
        ):
            raise DensityNumericalInputError(
                "Logical-grid plan geometries must use the same display cell."
            )
        limit = _positive_int(
            self.max_logical_voxels, name="max_logical_voxels"
        )
        if self.selected_geometry.logical_voxel_count > limit:
            raise DensityNumericalInputError(
                "selected_geometry exceeds max_logical_voxels."
            )
        if self.coarsest_geometry.logical_voxel_count > limit:
            raise DensityNumericalInputError(
                "coarsest_geometry exceeds max_logical_voxels."
            )
        resource_signature = _nonempty(
            self.scientific_resource_signature,
            name="scientific_resource_signature",
        )
        try:
            status = DensityGridPlanStatus(self.status)
        except ValueError as error:
            raise DensityNumericalInputError(
                f"Unsupported logical-grid plan status {self.status!r}."
            ) from error
        reasons = tuple(_nonempty(item, name="reason_code") for item in self.reason_codes)
        if len(set(reasons)) != len(reasons):
            raise DensityNumericalInputError("reason_codes must be unique.")
        target_reached = (
            self.selected_geometry.grid_shape == self.target_geometry.grid_shape
        )
        if status is DensityGridPlanStatus.TARGET_REACHED and not target_reached:
            raise DensityNumericalInputError(
                "target_reached status requires the target grid shape."
            )
        if status is DensityGridPlanStatus.BUDGET_LIMITED:
            if target_reached:
                raise DensityNumericalInputError(
                    "budget_limited status cannot select the target grid shape."
                )
            if self.target_geometry.logical_voxel_count <= limit:
                raise DensityNumericalInputError(
                    "budget_limited status requires the target grid to exceed the limit."
                )
            if "unresolved_due_to_resolution_budget" not in reasons:
                raise DensityNumericalInputError(
                    "budget_limited plans require unresolved_due_to_resolution_budget."
                )
        metadata = freeze_json_mapping(self.metadata)
        object.__setattr__(self, "max_logical_voxels", limit)
        object.__setattr__(self, "scientific_resource_signature", resource_signature)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(
            self,
            "signature",
            _signature(self.to_json_dict(include_signature=False)),
        )

    @property
    def target_reached(self) -> bool:
        return self.status is DensityGridPlanStatus.TARGET_REACHED

    @property
    def budget_limited(self) -> bool:
        return self.status is DensityGridPlanStatus.BUDGET_LIMITED

    @property
    def logical_grid_signature(self) -> str:
        return density_logical_grid_signature(self.selected_geometry)

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "target_geometry": self.target_geometry.to_json_dict(),
            "selected_geometry": self.selected_geometry.to_json_dict(),
            "coarsest_geometry": self.coarsest_geometry.to_json_dict(),
            "max_logical_voxels": self.max_logical_voxels,
            "scientific_resource_signature": self.scientific_resource_signature,
            "status": self.status.value,
            "target_reached": self.target_reached,
            "budget_limited": self.budget_limited,
            "reason_codes": list(self.reason_codes),
            "logical_grid_signature": self.logical_grid_signature,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "DensityLogicalGridPlan":
        expected = payload.get("signature")
        result = cls(
            target_geometry=DensityGridGeometry.from_json_dict(
                payload["target_geometry"]
            ),
            selected_geometry=DensityGridGeometry.from_json_dict(
                payload["selected_geometry"]
            ),
            coarsest_geometry=DensityGridGeometry.from_json_dict(
                payload["coarsest_geometry"]
            ),
            max_logical_voxels=payload["max_logical_voxels"],
            scientific_resource_signature=str(
                payload["scientific_resource_signature"]
            ),
            status=str(payload["status"]),
            reason_codes=tuple(payload.get("reason_codes", ())),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if expected is not None and str(expected) != result.signature:
            raise DensityNumericalSerializationError(
                "Logical-grid plan signature mismatch."
            )
        if payload.get("logical_grid_signature", result.logical_grid_signature) != result.logical_grid_signature:
            raise DensityNumericalSerializationError(
                "Logical-grid identity mismatch."
            )
        return result


def plan_finest_feasible_density_grid(
    cell: Any,
    *,
    target_interval: float,
    coarsest_interval: float,
    resource_policy: ScientificDensityResourcePolicy | None = None,
    max_logical_voxels: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DensityLogicalGridPlan:
    """Choose the finest automatic logical grid within a scientific voxel limit.

    This is the analysis-owned equivalent of the established plotting oracle.
    It never changes a kernel and never selects a storage backend.
    """

    target = _nonnegative_float(target_interval, name="target_interval")
    coarsest = _positive_float(coarsest_interval, name="coarsest_interval")
    limit, resource_signature = _resolve_voxel_limit(
        resource_policy=resource_policy,
        max_logical_voxels=max_logical_voxels,
    )
    target_geometry = (
        prepare_density_grid_geometry(
            cell,
            grid_interval=target,
            metadata={"planner_role": "requested_target"},
        )
        if target > 0.0
        else None
    )
    coarsest_geometry = prepare_density_grid_geometry(
        cell,
        grid_interval=coarsest,
        metadata={"planner_role": "coarsest_admissible"},
    )
    if target_geometry is not None and target_geometry.logical_voxel_count <= limit:
        return DensityLogicalGridPlan(
            target_geometry=target_geometry,
            selected_geometry=target_geometry,
            coarsest_geometry=coarsest_geometry,
            max_logical_voxels=limit,
            scientific_resource_signature=resource_signature,
            status=DensityGridPlanStatus.TARGET_REACHED,
            metadata={} if metadata is None else metadata,
        )
    if coarsest_geometry.logical_voxel_count > limit:
        raise DensityNumericalResourceError(
            "The coarsest density grid requires "
            f"{coarsest_geometry.logical_voxel_count} voxels, exceeding the "
            f"scientific logical-voxel limit {limit}."
        )
    low = max(0.0, target)
    high = coarsest
    if high < low:
        # A coarser target that itself exceeds the budget cannot be repaired by
        # searching toward a finer nominal interval.
        raise DensityNumericalResourceError(
            "coarsest_interval must not be finer than an infeasible target_interval."
        )
    for _ in range(80):
        middle = 0.5 * (low + high)
        shape = resolve_density_grid_shape(
            cell, grid_shape=None, grid_interval=middle
        )
        if _voxel_count(shape) > limit:
            low = middle
        else:
            high = middle
    selected_shape = resolve_density_grid_shape(
        cell, grid_shape=None, grid_interval=high
    )
    selected_geometry = _geometry_for_shape(
        cell,
        selected_shape,
        requested_interval=high,
        metadata={"planner_role": "finest_feasible"},
    )
    if target_geometry is None:
        infeasible_interval = float(np.nextafter(high, 0.0))
        infeasible_shape = resolve_density_grid_shape(
            cell, grid_shape=None, grid_interval=infeasible_interval
        )
        while _voxel_count(infeasible_shape) <= limit:
            infeasible_interval *= 0.5
            infeasible_shape = resolve_density_grid_shape(
                cell, grid_shape=None, grid_interval=infeasible_interval
            )
        target_geometry = _geometry_for_shape(
            cell,
            infeasible_shape,
            requested_interval=infeasible_interval,
            metadata={
                "planner_role": "unbounded_requested_target",
                "requested_target_interval": 0.0,
            },
        )
    return DensityLogicalGridPlan(
        target_geometry=target_geometry,
        selected_geometry=selected_geometry,
        coarsest_geometry=coarsest_geometry,
        max_logical_voxels=limit,
        scientific_resource_signature=resource_signature,
        status=DensityGridPlanStatus.BUDGET_LIMITED,
        reason_codes=("unresolved_due_to_resolution_budget",),
        metadata={} if metadata is None else metadata,
    )


@dataclass(frozen=True, slots=True)
class DensityNestedGridLadder:
    """Signed exactly nested logical-grid ladder with a fixed refinement factor."""

    levels: tuple[DensityGridGeometry, ...]
    requested_finest_geometry: DensityGridGeometry
    coarsest_interval: float
    finest_interval: float
    refinement_factor: int
    max_levels: int
    max_logical_voxels: int
    scientific_resource_signature: str
    status: DensityGridPlanStatus | str
    reason_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_NESTED_GRID_LADDER_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_NESTED_GRID_LADDER_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported nested-grid ladder schema {self.schema_version!r}."
            )
        levels = tuple(self.levels)
        if not levels or not all(isinstance(item, DensityGridGeometry) for item in levels):
            raise DensityNumericalInputError(
                "levels must contain at least one DensityGridGeometry."
            )
        if not isinstance(self.requested_finest_geometry, DensityGridGeometry):
            raise TypeError("requested_finest_geometry must be DensityGridGeometry.")
        coarsest = _positive_float(self.coarsest_interval, name="coarsest_interval")
        finest = _positive_float(self.finest_interval, name="finest_interval")
        if finest > coarsest:
            raise DensityNumericalInputError(
                "finest_interval cannot exceed coarsest_interval."
            )
        factor = _positive_int(self.refinement_factor, name="refinement_factor")
        if factor < 2:
            raise DensityNumericalInputError("refinement_factor must be at least 2.")
        maximum_levels = _positive_int(self.max_levels, name="max_levels")
        if len(levels) > maximum_levels:
            raise DensityNumericalInputError("levels exceed max_levels.")
        limit = _positive_int(self.max_logical_voxels, name="max_logical_voxels")
        resource_signature = _nonempty(
            self.scientific_resource_signature,
            name="scientific_resource_signature",
        )
        base_cell = levels[0].display_cell
        for index, level in enumerate(levels):
            if not np.allclose(level.display_cell, base_cell, rtol=0.0, atol=5.0e-15):
                raise DensityNumericalInputError(
                    "All ladder levels must use the same display cell."
                )
            if level.logical_voxel_count > limit:
                raise DensityNumericalInputError(
                    "A ladder level exceeds max_logical_voxels."
                )
            if index:
                expected = tuple(
                    factor * value for value in levels[index - 1].grid_shape
                )
                if level.grid_shape != expected:
                    raise DensityNumericalInputError(
                        "Nested-grid ladder shapes must refine exactly by refinement_factor."
                    )
        if not np.allclose(
            self.requested_finest_geometry.display_cell,
            base_cell,
            rtol=0.0,
            atol=5.0e-15,
        ):
            raise DensityNumericalInputError(
                "requested_finest_geometry must use the ladder display cell."
            )
        try:
            status = DensityGridPlanStatus(self.status)
        except ValueError as error:
            raise DensityNumericalInputError(
                f"Unsupported ladder status {self.status!r}."
            ) from error
        reasons = tuple(_nonempty(item, name="reason_code") for item in self.reason_codes)
        target_reached = max(levels[-1].realized_intervals) <= finest * (
            1.0 + 5.0e-15
        )
        if status is DensityGridPlanStatus.TARGET_REACHED and not target_reached:
            raise DensityNumericalInputError(
                "target_reached ladder does not meet finest_interval."
            )
        if status is DensityGridPlanStatus.BUDGET_LIMITED:
            if target_reached:
                raise DensityNumericalInputError(
                    "budget_limited ladder already reaches finest_interval."
                )
            if "unresolved_due_to_resolution_budget" not in reasons:
                raise DensityNumericalInputError(
                    "budget_limited ladders require unresolved_due_to_resolution_budget."
                )
        if status is DensityGridPlanStatus.LEVEL_LIMITED:
            if target_reached:
                raise DensityNumericalInputError(
                    "level_limited ladder already reaches finest_interval."
                )
            if "unresolved_due_to_ladder_depth" not in reasons:
                raise DensityNumericalInputError(
                    "level_limited ladders require unresolved_due_to_ladder_depth."
                )
        object.__setattr__(self, "levels", levels)
        object.__setattr__(self, "coarsest_interval", coarsest)
        object.__setattr__(self, "finest_interval", finest)
        object.__setattr__(self, "refinement_factor", factor)
        object.__setattr__(self, "max_levels", maximum_levels)
        object.__setattr__(self, "max_logical_voxels", limit)
        object.__setattr__(self, "scientific_resource_signature", resource_signature)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        object.__setattr__(
            self,
            "signature",
            _signature(self.to_json_dict(include_signature=False)),
        )

    @property
    def finest_feasible_geometry(self) -> DensityGridGeometry:
        return self.levels[-1]

    @property
    def target_reached(self) -> bool:
        return self.status is DensityGridPlanStatus.TARGET_REACHED

    @property
    def budget_limited(self) -> bool:
        return self.status is DensityGridPlanStatus.BUDGET_LIMITED

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "levels": [item.to_json_dict() for item in self.levels],
            "requested_finest_geometry": self.requested_finest_geometry.to_json_dict(),
            "coarsest_interval": self.coarsest_interval,
            "finest_interval": self.finest_interval,
            "refinement_factor": self.refinement_factor,
            "max_levels": self.max_levels,
            "max_logical_voxels": self.max_logical_voxels,
            "scientific_resource_signature": self.scientific_resource_signature,
            "status": self.status.value,
            "target_reached": self.target_reached,
            "budget_limited": self.budget_limited,
            "reason_codes": list(self.reason_codes),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "DensityNestedGridLadder":
        expected = payload.get("signature")
        result = cls(
            levels=tuple(
                DensityGridGeometry.from_json_dict(item)
                for item in payload["levels"]
            ),
            requested_finest_geometry=DensityGridGeometry.from_json_dict(
                payload["requested_finest_geometry"]
            ),
            coarsest_interval=payload["coarsest_interval"],
            finest_interval=payload["finest_interval"],
            refinement_factor=payload["refinement_factor"],
            max_levels=payload["max_levels"],
            max_logical_voxels=payload["max_logical_voxels"],
            scientific_resource_signature=str(
                payload["scientific_resource_signature"]
            ),
            status=str(payload["status"]),
            reason_codes=tuple(payload.get("reason_codes", ())),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if expected is not None and str(expected) != result.signature:
            raise DensityNumericalSerializationError(
                "Nested-grid ladder signature mismatch."
            )
        return result


def plan_deterministic_density_grid_ladder(
    cell: Any,
    *,
    coarsest_interval: float,
    finest_interval: float,
    refinement_factor: int = 2,
    max_levels: int = 16,
    resource_policy: ScientificDensityResourcePolicy | None = None,
    max_logical_voxels: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> DensityNestedGridLadder:
    """Build an exactly nested, deterministic, backend-independent grid ladder."""

    coarsest = _positive_float(coarsest_interval, name="coarsest_interval")
    finest = _positive_float(finest_interval, name="finest_interval")
    if finest > coarsest:
        raise DensityNumericalInputError(
            "finest_interval cannot exceed coarsest_interval."
        )
    factor = _positive_int(refinement_factor, name="refinement_factor")
    if factor < 2:
        raise DensityNumericalInputError("refinement_factor must be at least 2.")
    maximum_levels = _positive_int(max_levels, name="max_levels")
    limit, resource_signature = _resolve_voxel_limit(
        resource_policy=resource_policy,
        max_logical_voxels=max_logical_voxels,
    )
    base_shape = resolve_density_grid_shape(
        cell, grid_shape=None, grid_interval=coarsest
    )
    base = _geometry_for_shape(
        cell,
        base_shape,
        requested_interval=coarsest,
        metadata={"ladder_level": 0},
    )
    if base.logical_voxel_count > limit:
        raise DensityNumericalResourceError(
            "The coarsest ladder level requires "
            f"{base.logical_voxel_count} voxels, exceeding the scientific "
            f"logical-voxel limit {limit}."
        )
    levels = [base]
    requested = base
    next_shape = base_shape
    target_reached = max(base.realized_intervals) <= finest * (1.0 + 5.0e-15)
    stopped_by_budget = False
    stopped_by_depth = False
    while not target_reached:
        if len(levels) >= maximum_levels:
            stopped_by_depth = True
            break
        next_shape = tuple(factor * value for value in next_shape)
        requested_interval = coarsest / float(factor ** len(levels))
        requested = _geometry_for_shape(
            cell,
            next_shape,
            requested_interval=requested_interval,
            metadata={"ladder_level": len(levels)},
        )
        if requested.logical_voxel_count > limit:
            stopped_by_budget = True
            break
        levels.append(requested)
        target_reached = max(requested.realized_intervals) <= finest * (
            1.0 + 5.0e-15
        )
    if target_reached:
        status = DensityGridPlanStatus.TARGET_REACHED
        reasons: tuple[str, ...] = ()
        requested_finest = levels[-1]
    elif stopped_by_budget:
        status = DensityGridPlanStatus.BUDGET_LIMITED
        reasons = ("unresolved_due_to_resolution_budget",)
        requested_finest = requested
    else:
        status = DensityGridPlanStatus.LEVEL_LIMITED
        reasons = ("unresolved_due_to_ladder_depth",)
        requested_finest = requested
    return DensityNestedGridLadder(
        levels=tuple(levels),
        requested_finest_geometry=requested_finest,
        coarsest_interval=coarsest,
        finest_interval=finest,
        refinement_factor=factor,
        max_levels=maximum_levels,
        max_logical_voxels=limit,
        scientific_resource_signature=resource_signature,
        status=status,
        reason_codes=reasons,
        metadata={} if metadata is None else metadata,
    )


@dataclass(frozen=True, slots=True)
class DensityFieldReuseKey:
    """Backend-independent cache key for one numerically identical field."""

    field_kind: str
    source_signature: str
    sample_selection_signature: str
    weight_signature: str
    fixed_kernel_signature: str
    logical_grid_signature: str
    normalization_signature: str
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_FIELD_REUSE_KEY_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_FIELD_REUSE_KEY_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported field-reuse key schema {self.schema_version!r}."
            )
        for name in (
            "field_kind",
            "source_signature",
            "sample_selection_signature",
            "weight_signature",
            "fixed_kernel_signature",
            "logical_grid_signature",
            "normalization_signature",
        ):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name=name))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        identity_payload = {
            "schema_version": self.schema_version,
            "field_kind": self.field_kind,
            "source_signature": self.source_signature,
            "sample_selection_signature": self.sample_selection_signature,
            "weight_signature": self.weight_signature,
            "fixed_kernel_signature": self.fixed_kernel_signature,
            "logical_grid_signature": self.logical_grid_signature,
            "normalization_signature": self.normalization_signature,
        }
        object.__setattr__(self, "signature", _signature(identity_payload))

    @property
    def cache_key(self) -> str:
        return f"mdstats-density-field:{self.signature}"

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "field_kind": self.field_kind,
            "source_signature": self.source_signature,
            "sample_selection_signature": self.sample_selection_signature,
            "weight_signature": self.weight_signature,
            "fixed_kernel_signature": self.fixed_kernel_signature,
            "logical_grid_signature": self.logical_grid_signature,
            "normalization_signature": self.normalization_signature,
            "cache_key": self.cache_key,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(cls, payload: Mapping[str, Any]) -> "DensityFieldReuseKey":
        expected = payload.get("signature")
        result = cls(
            field_kind=str(payload["field_kind"]),
            source_signature=str(payload["source_signature"]),
            sample_selection_signature=str(payload["sample_selection_signature"]),
            weight_signature=str(payload["weight_signature"]),
            fixed_kernel_signature=str(payload["fixed_kernel_signature"]),
            logical_grid_signature=str(payload["logical_grid_signature"]),
            normalization_signature=str(payload["normalization_signature"]),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if expected is not None and str(expected) != result.signature:
            raise DensityNumericalSerializationError(
                "Field-reuse key signature mismatch."
            )
        if payload.get("cache_key", result.cache_key) != result.cache_key:
            raise DensityNumericalSerializationError("Field cache-key mismatch.")
        return result


def require_identical_density_field_reuse(
    left: DensityFieldReuseKey, right: DensityFieldReuseKey
) -> None:
    """Fail closed unless two field requests are numerically identical."""

    if not isinstance(left, DensityFieldReuseKey) or not isinstance(
        right, DensityFieldReuseKey
    ):
        raise TypeError("left and right must be DensityFieldReuseKey.")
    if left.signature != right.signature:
        differing = [
            name
            for name in (
                "field_kind",
                "source_signature",
                "sample_selection_signature",
                "weight_signature",
                "fixed_kernel_signature",
                "logical_grid_signature",
                "normalization_signature",
            )
            if getattr(left, name) != getattr(right, name)
        ]
        raise DensityNumericalInputError(
            "Density field reuse requires identical source, sample, weight, kernel, "
            "logical-grid, and normalization signatures; differing fields: "
            + ", ".join(differing)
        )


@dataclass(frozen=True, slots=True)
class DensityBackendCandidatePlan:
    """Backend feasibility estimate bound to one frozen grid and kernel."""

    backend: str
    logical_grid_signature: str
    fixed_kernel_signature: str
    feasible: bool
    estimated_storage_values: int
    estimated_workspace_bytes: int
    estimated_work: float
    reason_codes: tuple[str, ...] = ()
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_BACKEND_CANDIDATE_PLAN_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_BACKEND_CANDIDATE_PLAN_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported backend-candidate schema {self.schema_version!r}."
            )
        object.__setattr__(self, "backend", _nonempty(self.backend, name="backend"))
        object.__setattr__(
            self,
            "logical_grid_signature",
            _nonempty(self.logical_grid_signature, name="logical_grid_signature"),
        )
        object.__setattr__(
            self,
            "fixed_kernel_signature",
            _nonempty(self.fixed_kernel_signature, name="fixed_kernel_signature"),
        )
        if not isinstance(self.feasible, bool):
            raise DensityNumericalInputError("feasible must be Boolean.")
        object.__setattr__(
            self,
            "estimated_storage_values",
            _nonnegative_int(
                self.estimated_storage_values, name="estimated_storage_values"
            ),
        )
        object.__setattr__(
            self,
            "estimated_workspace_bytes",
            _nonnegative_int(
                self.estimated_workspace_bytes, name="estimated_workspace_bytes"
            ),
        )
        object.__setattr__(
            self,
            "estimated_work",
            _nonnegative_float(self.estimated_work, name="estimated_work"),
        )
        reasons = tuple(_nonempty(item, name="reason_code") for item in self.reason_codes)
        if self.feasible and reasons:
            raise DensityNumericalInputError(
                "Feasible backend candidates cannot carry infeasibility reasons."
            )
        if not self.feasible and not reasons:
            raise DensityNumericalInputError(
                "Infeasible backend candidates require a reason code."
            )
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        object.__setattr__(
            self,
            "signature",
            _signature(self.to_json_dict(include_signature=False)),
        )

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "backend": self.backend,
            "logical_grid_signature": self.logical_grid_signature,
            "fixed_kernel_signature": self.fixed_kernel_signature,
            "feasible": self.feasible,
            "estimated_storage_values": self.estimated_storage_values,
            "estimated_workspace_bytes": self.estimated_workspace_bytes,
            "estimated_work": self.estimated_work,
            "reason_codes": list(self.reason_codes),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any]
    ) -> "DensityBackendCandidatePlan":
        expected = payload.get("signature")
        result = cls(
            backend=str(payload["backend"]),
            logical_grid_signature=str(payload["logical_grid_signature"]),
            fixed_kernel_signature=str(payload["fixed_kernel_signature"]),
            feasible=payload["feasible"],
            estimated_storage_values=payload["estimated_storage_values"],
            estimated_workspace_bytes=payload["estimated_workspace_bytes"],
            estimated_work=payload["estimated_work"],
            reason_codes=tuple(payload.get("reason_codes", ())),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if expected is not None and str(expected) != result.signature:
            raise DensityNumericalSerializationError(
                "Backend-candidate signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class DensityBackendSelectionPlan:
    """Deterministic backend choice made after logical-grid resolution."""

    logical_grid_plan_signature: str
    logical_grid_signature: str
    fixed_kernel_signature: str
    requested_backend: str
    selected_backend: str
    candidates: tuple[DensityBackendCandidatePlan, ...]
    selection_reason: str
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_BACKEND_SELECTION_PLAN_SCHEMA
    signature: str = field(init=False)

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_BACKEND_SELECTION_PLAN_SCHEMA:
            raise DensityNumericalSerializationError(
                f"Unsupported backend-selection schema {self.schema_version!r}."
            )
        for name in (
            "logical_grid_plan_signature",
            "logical_grid_signature",
            "fixed_kernel_signature",
            "requested_backend",
            "selected_backend",
            "selection_reason",
        ):
            object.__setattr__(self, name, _nonempty(getattr(self, name), name=name))
        candidates = tuple(self.candidates)
        if not candidates:
            raise DensityNumericalInputError("candidates cannot be empty.")
        if len({item.backend for item in candidates}) != len(candidates):
            raise DensityNumericalInputError("Backend candidate names must be unique.")
        for item in candidates:
            if item.logical_grid_signature != self.logical_grid_signature:
                raise DensityNumericalInputError(
                    "Backend candidates cannot change the logical grid."
                )
            if item.fixed_kernel_signature != self.fixed_kernel_signature:
                raise DensityNumericalInputError(
                    "Backend candidates cannot change the fixed kernel."
                )
        selected = next(
            (item for item in candidates if item.backend == self.selected_backend),
            None,
        )
        if selected is None or not selected.feasible:
            raise DensityNumericalInputError(
                "selected_backend must name a feasible candidate."
            )
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))
        object.__setattr__(
            self,
            "signature",
            _signature(self.to_json_dict(include_signature=False)),
        )

    def to_json_dict(self, *, include_signature: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "logical_grid_plan_signature": self.logical_grid_plan_signature,
            "logical_grid_signature": self.logical_grid_signature,
            "fixed_kernel_signature": self.fixed_kernel_signature,
            "requested_backend": self.requested_backend,
            "selected_backend": self.selected_backend,
            "candidates": [item.to_json_dict() for item in self.candidates],
            "selection_reason": self.selection_reason,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_signature:
            result["signature"] = self.signature
        return result

    @classmethod
    def from_json_dict(
        cls, payload: Mapping[str, Any]
    ) -> "DensityBackendSelectionPlan":
        expected = payload.get("signature")
        result = cls(
            logical_grid_plan_signature=str(payload["logical_grid_plan_signature"]),
            logical_grid_signature=str(payload["logical_grid_signature"]),
            fixed_kernel_signature=str(payload["fixed_kernel_signature"]),
            requested_backend=str(payload["requested_backend"]),
            selected_backend=str(payload["selected_backend"]),
            candidates=tuple(
                DensityBackendCandidatePlan.from_json_dict(item)
                for item in payload["candidates"]
            ),
            selection_reason=str(payload["selection_reason"]),
            metadata=payload.get("metadata", {}),
            schema_version=str(payload.get("schema_version", "")),
        )
        if expected is not None and str(expected) != result.signature:
            raise DensityNumericalSerializationError(
                "Backend-selection signature mismatch."
            )
        return result


def select_density_backend_after_grid(
    grid_plan: DensityLogicalGridPlan,
    *,
    fixed_kernel_signature: str,
    candidates: Sequence[DensityBackendCandidatePlan],
    requested_backend: str = "auto",
    metadata: Mapping[str, Any] | None = None,
) -> DensityBackendSelectionPlan:
    """Select storage/execution only after the physical logical grid is frozen."""

    if not isinstance(grid_plan, DensityLogicalGridPlan):
        raise TypeError("grid_plan must be DensityLogicalGridPlan.")
    kernel = _nonempty(
        fixed_kernel_signature, name="fixed_kernel_signature"
    )
    request = _nonempty(requested_backend, name="requested_backend")
    candidate_tuple = tuple(candidates)
    if not candidate_tuple:
        raise DensityNumericalInputError("candidates cannot be empty.")
    logical_signature = grid_plan.logical_grid_signature
    for item in candidate_tuple:
        if not isinstance(item, DensityBackendCandidatePlan):
            raise TypeError("candidates must contain DensityBackendCandidatePlan.")
        if item.logical_grid_signature != logical_signature:
            raise DensityNumericalInputError(
                "Backend planning must preserve the frozen logical grid."
            )
        if item.fixed_kernel_signature != kernel:
            raise DensityNumericalInputError(
                "Backend planning must preserve the fixed kernel."
            )
    feasible = [item for item in candidate_tuple if item.feasible]
    if not feasible:
        raise DensityNumericalResourceError(
            "No feasible scientific density backend remains for the frozen grid and kernel."
        )
    if request == "auto":
        selected = min(
            feasible,
            key=lambda item: (
                item.estimated_work,
                item.estimated_workspace_bytes,
                item.estimated_storage_values,
                item.backend,
            ),
        )
        reason = "minimum_estimated_scientific_work_after_grid_freeze"
    else:
        selected = next((item for item in feasible if item.backend == request), None)
        if selected is None:
            raise DensityNumericalResourceError(
                f"Requested backend {request!r} is unavailable or infeasible."
            )
        reason = "explicit_scientific_backend_request_after_grid_freeze"
    return DensityBackendSelectionPlan(
        logical_grid_plan_signature=grid_plan.signature,
        logical_grid_signature=logical_signature,
        fixed_kernel_signature=kernel,
        requested_backend=request,
        selected_backend=selected.backend,
        candidates=candidate_tuple,
        selection_reason=reason,
        metadata={} if metadata is None else metadata,
    )


__all__ = [
    "DENSITY_LOGICAL_GRID_PLAN_SCHEMA",
    "DENSITY_NESTED_GRID_LADDER_SCHEMA",
    "DENSITY_FIELD_REUSE_KEY_SCHEMA",
    "DENSITY_BACKEND_CANDIDATE_PLAN_SCHEMA",
    "DENSITY_BACKEND_SELECTION_PLAN_SCHEMA",
    "DensityGridPlanStatus",
    "DensityLogicalGridPlan",
    "DensityNestedGridLadder",
    "DensityFieldReuseKey",
    "DensityBackendCandidatePlan",
    "DensityBackendSelectionPlan",
    "density_logical_grid_signature",
    "plan_finest_feasible_density_grid",
    "plan_deterministic_density_grid_ladder",
    "require_identical_density_field_reuse",
    "select_density_backend_after_grid",
]
