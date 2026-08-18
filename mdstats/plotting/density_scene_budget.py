"""Scene-wide density mesh allocation for LD9-V3.

The allocator converts one hard post-replication browser face budget into
per-shell canonical face targets.  It deliberately uses only immutable HDR and
replication metadata; no Plotly objects are created here.

The allocation policy is project-specific.  It reserves a minimum face count
for every requested shell, weights the remainder by estimated surface scale and
visual importance, and uses a deterministic largest-remainder apportionment so
that the final post-replication total never exceeds the hard browser limit.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_render_budget import BrowserMeshBudget
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError

DENSITY_SCENE_SHELL_REQUEST_SCHEMA = "mdstats.density-scene-shell-request.v1"
DENSITY_SCENE_SHELL_ALLOCATION_SCHEMA = "mdstats.density-scene-shell-allocation.v1"
DENSITY_SCENE_ALLOCATION_OPTIONS_SCHEMA = "mdstats.density-scene-allocation-options.v1"
DENSITY_SCENE_BUDGET_PLAN_SCHEMA = "mdstats.density-scene-budget-plan.v1"


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


@dataclass(frozen=True, slots=True)
class DensitySceneShellRequest:
    """One requested density shell before scene-wide allocation."""

    shell_key: str
    field_key: str
    label: str
    mass_fraction: float
    selected_node_count: int
    display_replication: int = 1
    visual_importance: float = 1.0
    max_canonical_faces: int = 250_000
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_SCENE_SHELL_REQUEST_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SCENE_SHELL_REQUEST_SCHEMA:
            raise GraphAdapterError("Unsupported density-scene-shell-request schema.")
        for name in ("shell_key", "field_key", "label"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value:
                raise GraphAdapterError(f"{name} must be a nonempty string.")
        fraction = float(self.mass_fraction)
        if not np.isfinite(fraction) or not 0.0 < fraction < 1.0:
            raise GraphStyleError("mass_fraction must lie strictly between zero and one.")
        importance = float(self.visual_importance)
        if not np.isfinite(importance) or importance <= 0.0:
            raise GraphStyleError("visual_importance must be finite and positive.")
        object.__setattr__(self, "mass_fraction", fraction)
        object.__setattr__(
            self,
            "selected_node_count",
            _positive_int(self.selected_node_count, name="selected_node_count"),
        )
        object.__setattr__(
            self,
            "display_replication",
            _positive_int(self.display_replication, name="display_replication"),
        )
        object.__setattr__(
            self,
            "max_canonical_faces",
            _positive_int(self.max_canonical_faces, name="max_canonical_faces"),
        )
        object.__setattr__(self, "visual_importance", importance)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def allocation_weight(self) -> float:
        # Surface area of a compact 3-D region scales as volume^(2/3).  The HDR
        # selected-node count is a stable backend-neutral proxy for volume.
        return float(self.selected_node_count) ** (2.0 / 3.0) * self.visual_importance

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "shell_key": self.shell_key,
            "field_key": self.field_key,
            "label": self.label,
            "mass_fraction": self.mass_fraction,
            "selected_node_count": self.selected_node_count,
            "display_replication": self.display_replication,
            "visual_importance": self.visual_importance,
            "max_canonical_faces": self.max_canonical_faces,
            "allocation_weight": self.allocation_weight,
            "metadata": self.metadata.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class DensitySceneAllocationOptions:
    """Deterministic scene-wide allocation policy."""

    min_canonical_faces_per_shell: int = 4_000
    shell_importance: tuple[float, ...] = (1.0, 0.72, 0.48)
    reserve_face_fraction: float = 0.15
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_SCENE_ALLOCATION_OPTIONS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SCENE_ALLOCATION_OPTIONS_SCHEMA:
            raise GraphAdapterError("Unsupported density-scene-allocation-options schema.")
        object.__setattr__(
            self,
            "min_canonical_faces_per_shell",
            _positive_int(
                self.min_canonical_faces_per_shell,
                name="min_canonical_faces_per_shell",
                minimum=4,
            ),
        )
        importance = tuple(float(value) for value in self.shell_importance)
        if not importance or any(not np.isfinite(value) or value <= 0.0 for value in importance):
            raise GraphStyleError("shell_importance must contain positive finite values.")
        reserve = float(self.reserve_face_fraction)
        if not np.isfinite(reserve) or not 0.0 <= reserve < 1.0:
            raise GraphStyleError("reserve_face_fraction must lie in [0, 1).")
        object.__setattr__(self, "shell_importance", importance)
        object.__setattr__(self, "reserve_face_fraction", reserve)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "min_canonical_faces_per_shell": self.min_canonical_faces_per_shell,
            "shell_importance": list(self.shell_importance),
            "reserve_face_fraction": self.reserve_face_fraction,
            "metadata": self.metadata.to_json_dict(),
        }


@dataclass(frozen=True, slots=True)
class DensitySceneShellAllocation:
    shell_key: str
    target_canonical_faces: int
    target_serialized_faces: int
    display_replication: int
    allocation_weight: float
    schema_version: str = DENSITY_SCENE_SHELL_ALLOCATION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SCENE_SHELL_ALLOCATION_SCHEMA:
            raise GraphAdapterError("Unsupported density-scene-shell-allocation schema.")
        if not isinstance(self.shell_key, str) or not self.shell_key:
            raise GraphAdapterError("shell_key must be a nonempty string.")
        for name in ("target_canonical_faces", "target_serialized_faces", "display_replication"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name=name, minimum=0 if "target" in name else 1))
        weight = float(self.allocation_weight)
        if not np.isfinite(weight) or weight <= 0.0:
            raise GraphAdapterError("allocation_weight must be finite and positive.")
        object.__setattr__(self, "allocation_weight", weight)
        if self.target_serialized_faces != self.target_canonical_faces * self.display_replication:
            raise GraphAdapterError("Serialized and canonical allocation counts disagree.")

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "shell_key": self.shell_key,
            "target_canonical_faces": self.target_canonical_faces,
            "target_serialized_faces": self.target_serialized_faces,
            "display_replication": self.display_replication,
            "allocation_weight": self.allocation_weight,
        }


@dataclass(frozen=True, slots=True)
class DensitySceneBudgetPlan:
    budget: BrowserMeshBudget
    requests: tuple[DensitySceneShellRequest, ...]
    allocations: tuple[DensitySceneShellAllocation, ...]
    allocated_serialized_faces: int
    unallocated_serialized_faces: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=FrozenJSONMapping)
    schema_version: str = DENSITY_SCENE_BUDGET_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SCENE_BUDGET_PLAN_SCHEMA:
            raise GraphAdapterError("Unsupported density-scene-budget-plan schema.")
        if not isinstance(self.budget, BrowserMeshBudget):
            raise TypeError("budget must be BrowserMeshBudget.")
        requests = tuple(self.requests)
        allocations = tuple(self.allocations)
        if len(requests) != len(allocations):
            raise GraphAdapterError("requests and allocations must align.")
        if tuple(item.shell_key for item in requests) != tuple(item.shell_key for item in allocations):
            raise GraphAdapterError("request/allocation shell order must agree.")
        allocated = sum(item.target_serialized_faces for item in allocations)
        if allocated != int(self.allocated_serialized_faces):
            raise GraphAdapterError("allocated_serialized_faces is inconsistent.")
        if allocated > self.budget.max_final_density_faces:
            raise GraphComplexityError("Scene allocation exceeds browser face budget.")
        unallocated = self.budget.max_final_density_faces - allocated
        if unallocated != int(self.unallocated_serialized_faces):
            raise GraphAdapterError("unallocated_serialized_faces is inconsistent.")
        object.__setattr__(self, "requests", requests)
        object.__setattr__(self, "allocations", allocations)
        object.__setattr__(self, "allocated_serialized_faces", allocated)
        object.__setattr__(self, "unallocated_serialized_faces", unallocated)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def allocation_for(self, shell_key: str) -> DensitySceneShellAllocation:
        for allocation in self.allocations:
            if allocation.shell_key == shell_key:
                return allocation
        raise KeyError(shell_key)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "budget": self.budget.to_json_dict(),
            "requests": [item.to_json_dict() for item in self.requests],
            "allocations": [item.to_json_dict() for item in self.allocations],
            "allocated_serialized_faces": self.allocated_serialized_faces,
            "unallocated_serialized_faces": self.unallocated_serialized_faces,
            "metadata": self.metadata.to_json_dict(),
        }


def allocate_density_scene_budget(
    requests: Sequence[DensitySceneShellRequest],
    *,
    budget: BrowserMeshBudget | None = None,
    options: DensitySceneAllocationOptions | None = None,
) -> DensitySceneBudgetPlan:
    """Allocate one hard post-replication face budget across all shells."""

    resolved_budget = BrowserMeshBudget() if budget is None else budget
    resolved_options = DensitySceneAllocationOptions() if options is None else options
    if not isinstance(resolved_budget, BrowserMeshBudget):
        raise TypeError("budget must be BrowserMeshBudget or None.")
    if not isinstance(resolved_options, DensitySceneAllocationOptions):
        raise TypeError("options must be DensitySceneAllocationOptions or None.")
    items = tuple(requests)
    if not items:
        return DensitySceneBudgetPlan(
            budget=resolved_budget,
            requests=(),
            allocations=(),
            allocated_serialized_faces=0,
            unallocated_serialized_faces=resolved_budget.max_final_density_faces,
            metadata={"policy": "largest_remainder_surface_proxy_v1"},
        )
    keys = [item.shell_key for item in items]
    if len(set(keys)) != len(keys):
        raise GraphAdapterError("Density shell keys must be unique.")

    usable = int(np.floor(resolved_budget.max_final_density_faces * (1.0 - resolved_options.reserve_face_fraction)))
    minima_canonical = [
        min(resolved_options.min_canonical_faces_per_shell, item.max_canonical_faces)
        for item in items
    ]
    minima_serialized = [
        minima_canonical[index] * item.display_replication
        for index, item in enumerate(items)
    ]
    minimum_total = sum(minima_serialized)
    if minimum_total > usable:
        raise GraphComplexityError(
            "The hard browser face budget cannot provide the minimum face reserve "
            f"for every shell: required={minimum_total}, usable={usable}."
        )

    remaining = usable - minimum_total
    weights = np.asarray([item.allocation_weight for item in items], dtype=np.float64)
    weights /= float(np.sum(weights))
    ideal_extra_serialized = remaining * weights

    # Convert serialized extras to whole canonical faces.  The floor guarantees
    # the hard budget, and deterministic largest-remainder assignment spends any
    # residual while respecting replication and per-shell maxima.
    extras_canonical = np.floor(
        ideal_extra_serialized
        / np.asarray([item.display_replication for item in items], dtype=np.float64)
    ).astype(np.int64)
    for index, item in enumerate(items):
        extras_canonical[index] = min(
            int(extras_canonical[index]),
            item.max_canonical_faces - minima_canonical[index],
        )
    allocated = minimum_total + sum(
        int(extras_canonical[index]) * item.display_replication
        for index, item in enumerate(items)
    )
    residual = usable - allocated
    remainders = ideal_extra_serialized - extras_canonical * np.asarray(
        [item.display_replication for item in items], dtype=np.float64
    )
    order = sorted(
        range(len(items)),
        key=lambda index: (-float(remainders[index]), items[index].shell_key),
    )
    progress = True
    while residual > 0 and progress:
        progress = False
        for index in order:
            item = items[index]
            replication = item.display_replication
            current = minima_canonical[index] + int(extras_canonical[index])
            if current >= item.max_canonical_faces or replication > residual:
                continue
            extras_canonical[index] += 1
            residual -= replication
            progress = True
            if residual <= 0:
                break

    allocations = tuple(
        DensitySceneShellAllocation(
            shell_key=item.shell_key,
            target_canonical_faces=minima_canonical[index] + int(extras_canonical[index]),
            target_serialized_faces=(minima_canonical[index] + int(extras_canonical[index])) * item.display_replication,
            display_replication=item.display_replication,
            allocation_weight=item.allocation_weight,
        )
        for index, item in enumerate(items)
    )
    allocated = sum(item.target_serialized_faces for item in allocations)
    return DensitySceneBudgetPlan(
        budget=resolved_budget,
        requests=items,
        allocations=allocations,
        allocated_serialized_faces=allocated,
        unallocated_serialized_faces=resolved_budget.max_final_density_faces - allocated,
        metadata={
            "policy": "largest_remainder_surface_proxy_v1",
            "usable_serialized_faces": usable,
            "minimum_serialized_faces": minimum_total,
            "reserve_face_fraction": resolved_options.reserve_face_fraction,
        },
    )
