"""Transactional planning records for LD8 finite-support block atlases.

The planner approves field-specific support construction before target masks are
allocated.  It records conservative block/edge/bitset bounds and explicitly
excludes arrays proportional to the complete source-node by stencil-offset pair
count.  Realized counts are stored by :mod:`mdstats.plotting.density_support_atlas`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .density_block_routing import PeriodicKernelBlockRouting
from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

DENSITY_SUPPORT_PLANNING_LIMITS_SCHEMA = "mdstats.density-support-planning-limits.v2"
DENSITY_SUPPORT_ATLAS_PLAN_SCHEMA = "mdstats.density-support-atlas-plan.v1"

DEFAULT_MAX_SUPPORT_TARGET_BLOCKS = 1_000_000
DEFAULT_MAX_SUPPORT_SOURCE_TARGET_EDGES = 20_000_000
DEFAULT_MAX_SUPPORT_BITSET_REGION_OPERATIONS = 250_000_000
DEFAULT_MAX_SUPPORT_RETAINED_BYTES = 1_000_000_000
DEFAULT_MAX_SUPPORT_TRANSIENT_BYTES = 1_000_000_000


def _nonnegative_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a nonnegative integer.")
    result = int(value)
    if result < 0:
        raise GraphStyleError(f"{name} must be nonnegative.")
    return result


def _positive_int(value: Any, *, name: str) -> int:
    result = _nonnegative_int(value, name=name)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


@dataclass(frozen=True, slots=True)
class DensitySupportPlanningLimits:
    """Runtime-derived support-atlas planning limits."""

    max_target_blocks: int | None = None
    max_source_target_edges: int | None = None
    max_bitset_region_operations: int | None = None
    max_retained_bytes: int | None = None
    max_transient_bytes: int | None = None
    max_total_peak_bytes: int | None = None
    schema_version: str = DENSITY_SUPPORT_PLANNING_LIMITS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {
            DENSITY_SUPPORT_PLANNING_LIMITS_SCHEMA,
            "mdstats.density-support-planning-limits.v1",
        }:
            raise GraphAdapterError(
                f"Unsupported support-planning-limits schema {self.schema_version!r}."
            )
        budget, _model, derived = resolve_density_resource_limits()
        defaults = {
            "max_target_blocks": derived["max_density_blocks"],
            "max_source_target_edges": derived["max_density_component_values"],
            "max_bitset_region_operations": derived["max_density_kernel_pairs"],
            "max_retained_bytes": budget.max_memory_bytes,
            "max_transient_bytes": budget.max_memory_bytes,
            "max_total_peak_bytes": budget.max_memory_bytes,
        }
        memory_names = {
            "max_retained_bytes",
            "max_transient_bytes",
            "max_total_peak_bytes",
        }
        for name, default in defaults.items():
            current = getattr(self, name)
            resolved = default if current is None else min(default, _positive_int(current, name=name))
            if name in memory_names:
                resolved = min(resolved, budget.max_memory_bytes)
            object.__setattr__(self, name, resolved)
        object.__setattr__(self, "schema_version", DENSITY_SUPPORT_PLANNING_LIMITS_SCHEMA)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_target_blocks": self.max_target_blocks,
            "max_source_target_edges": self.max_source_target_edges,
            "max_bitset_region_operations": self.max_bitset_region_operations,
            "max_retained_bytes": self.max_retained_bytes,
            "max_transient_bytes": self.max_transient_bytes,
            "max_total_peak_bytes": self.max_total_peak_bytes,
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensitySupportPlanningLimits":
        data = dict(value)
        data.setdefault("max_total_peak_bytes", None)
        return cls(**data)


@dataclass(frozen=True, slots=True)
class DensitySupportAtlasPlan:
    source_field_identity: str
    source_node_count: int
    source_block_count: int
    stencil_offset_count: int
    block_word_count: int
    maximum_target_blocks_per_source_upper: int
    target_block_count_upper: int
    source_target_edge_count_upper: int
    target_support_node_count_upper: int
    bitset_region_operations_upper: int
    source_retained_bytes: int
    routing_retained_bytes: int
    atlas_retained_bytes_upper: int
    maximum_lifted_brick_nodes: int
    maximum_lifted_transient_bytes: int
    transient_bytes_upper: int
    complete_fine_pair_count_reference: int
    approved: bool
    limits: DensitySupportPlanningLimits
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_SUPPORT_ATLAS_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SUPPORT_ATLAS_PLAN_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported support-atlas-plan schema {self.schema_version!r}."
            )
        if not isinstance(self.source_field_identity, str) or len(self.source_field_identity) != 64:
            raise GraphAdapterError("source_field_identity must be a SHA-256 digest.")
        if not isinstance(self.limits, DensitySupportPlanningLimits):
            raise TypeError("limits must be DensitySupportPlanningLimits.")
        for name in (
            "source_node_count",
            "source_block_count",
            "stencil_offset_count",
            "block_word_count",
            "maximum_target_blocks_per_source_upper",
            "target_block_count_upper",
            "source_target_edge_count_upper",
            "target_support_node_count_upper",
            "bitset_region_operations_upper",
            "source_retained_bytes",
            "routing_retained_bytes",
            "atlas_retained_bytes_upper",
            "maximum_lifted_brick_nodes",
            "maximum_lifted_transient_bytes",
            "transient_bytes_upper",
            "complete_fine_pair_count_reference",
        ):
            object.__setattr__(self, name, _nonnegative_int(getattr(self, name), name=name))
        if self.source_node_count <= 0 or self.source_block_count <= 0:
            raise GraphAdapterError("A support-atlas plan requires positive source counts.")
        if self.stencil_offset_count <= 0 or self.block_word_count <= 0:
            raise GraphAdapterError("A support-atlas plan requires positive routing counts.")
        object.__setattr__(self, "approved", bool(self.approved))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def predicted_peak_bytes(self) -> int:
        return self.source_retained_bytes + self.routing_retained_bytes + self.atlas_retained_bytes_upper + self.transient_bytes_upper

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_field_identity": self.source_field_identity,
            "source_node_count": self.source_node_count,
            "source_block_count": self.source_block_count,
            "stencil_offset_count": self.stencil_offset_count,
            "block_word_count": self.block_word_count,
            "maximum_target_blocks_per_source_upper": self.maximum_target_blocks_per_source_upper,
            "target_block_count_upper": self.target_block_count_upper,
            "source_target_edge_count_upper": self.source_target_edge_count_upper,
            "target_support_node_count_upper": self.target_support_node_count_upper,
            "bitset_region_operations_upper": self.bitset_region_operations_upper,
            "source_retained_bytes": self.source_retained_bytes,
            "routing_retained_bytes": self.routing_retained_bytes,
            "atlas_retained_bytes_upper": self.atlas_retained_bytes_upper,
            "maximum_lifted_brick_nodes": self.maximum_lifted_brick_nodes,
            "maximum_lifted_transient_bytes": self.maximum_lifted_transient_bytes,
            "transient_bytes_upper": self.transient_bytes_upper,
            "complete_fine_pair_count_reference": self.complete_fine_pair_count_reference,
            "predicted_peak_bytes": self.predicted_peak_bytes,
            "approved": self.approved,
            "limits": self.limits.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensitySupportAtlasPlan":
        data = dict(value)
        data.pop("predicted_peak_bytes", None)
        data["limits"] = DensitySupportPlanningLimits.from_json_dict(data["limits"])
        return cls(**data)


def _axis_target_block_count_upper(
    source_block_index: int,
    *,
    logical_size: int,
    block_size: int,
    signed_axis_offsets: np.ndarray,
) -> int:
    block_start = source_block_index * block_size
    extent = min(block_size, logical_size - block_start)
    local = np.arange(extent, dtype=np.int64)
    targets: set[int] = set()
    # ``signed_axis_offsets`` is pre-unique in the production planner.  The
    # helper remains correct for callers that provide duplicates, but avoids a
    # repeated O(K log K) unique/sort in the per-source-block loop.
    offsets = signed_axis_offsets
    if offsets.size > 1 and np.any(offsets[1:] <= offsets[:-1]):
        offsets = np.unique(offsets)
    for offset in offsets:
        global_target = (block_start + local + int(offset)) % logical_size
        targets.update(int(value) for value in np.unique(global_target // block_size))
    return len(targets)


def plan_density_support_atlas(
    source_field: Any,
    routing: PeriodicKernelBlockRouting,
    *,
    limits: DensitySupportPlanningLimits | None = None,
) -> DensitySupportAtlasPlan:
    """Approve bounded exact support planning for one packed source field.

    ``source_field`` is duck-typed to avoid an import cycle.  It must expose the
    immutable LD8 packed-source attributes used below.
    """

    if not isinstance(routing, PeriodicKernelBlockRouting):
        raise TypeError("routing must be PeriodicKernelBlockRouting.")
    resolved_limits = DensitySupportPlanningLimits() if limits is None else limits
    if not isinstance(resolved_limits, DensitySupportPlanningLimits):
        raise TypeError("limits must be DensitySupportPlanningLimits.")
    required = (
        "content_identity",
        "occupied_node_count",
        "source_block_count",
        "source_block_indices",
        "retained_array_bytes",
        "logical_grid_shape",
        "storage_block_shape",
    )
    for name in required:
        if not hasattr(source_field, name):
            raise TypeError(f"source_field is missing required attribute {name!r}.")
    if tuple(source_field.logical_grid_shape) != routing.logical_grid_shape:
        raise GraphAdapterError("source field and routing must share logical_grid_shape.")
    if tuple(source_field.storage_block_shape) != routing.storage_block_shape:
        raise GraphAdapterError("source field and routing must share storage_block_shape.")
    source_blocks = np.asarray(source_field.source_block_indices, dtype=np.int64)
    signed = np.asarray(routing.signed_offsets, dtype=np.int64)
    # Stencil axis offsets and source block coordinates repeat heavily.  Resolve
    # each axis/block-index combination once instead of sorting the full stencil
    # independently for every source block.  This is exact because the planner's
    # upper bound is the Cartesian product of independent axis target sets.
    axis_unique_offsets = tuple(
        np.unique(signed[:, axis]).astype(np.int64, copy=False) for axis in range(3)
    )
    axis_target_counts: list[np.ndarray] = []
    for axis in range(3):
        counts = np.zeros(routing.block_grid_shape[axis], dtype=np.int64)
        unique_indices = np.unique(source_blocks[:, axis])
        counts[unique_indices] = np.fromiter(
            (
                _axis_target_block_count_upper(
                    int(index),
                    logical_size=routing.logical_grid_shape[axis],
                    block_size=routing.storage_block_shape[axis],
                    signed_axis_offsets=axis_unique_offsets[axis],
                )
                for index in unique_indices
            ),
            dtype=np.int64,
            count=unique_indices.size,
        )
        axis_target_counts.append(counts)
    per_source_upper = (
        axis_target_counts[0][source_blocks[:, 0]]
        * axis_target_counts[1][source_blocks[:, 1]]
        * axis_target_counts[2][source_blocks[:, 2]]
    )
    maximum_per_source = int(np.max(per_source_upper, initial=0))
    edge_upper = int(np.sum(per_source_upper, dtype=np.int64))
    total_block_count = int(np.prod(routing.block_grid_shape, dtype=object))
    target_upper = min(total_block_count, edge_upper)
    local_nodes = int(np.prod(routing.storage_block_shape, dtype=object))
    target_node_upper = min(
        int(np.prod(routing.logical_grid_shape, dtype=object)),
        target_upper * local_nodes,
    )
    # LD8-S1 uses one bounded padded-bitset shift per source block and exact
    # stencil offset; it does not split offsets into fine-node pair routes.
    region_operations_upper = int(source_field.source_block_count) * routing.stencil_offset_count
    word_bytes = 8 * routing.block_word_count
    atlas_retained_upper = (
        target_upper * (3 * 4 + word_bytes)
        + (int(source_field.source_block_count) + 1) * 8
        + edge_upper * 4
        + 4096
    )
    # Bound the actual padded-bitset dilation workspace used by LD8-S1.  The
    # lifted brick spans one valid source-block extent plus the exact signed
    # stencil halo.  The byte model includes the packed Python integers, the
    # unpacked brick mask, coordinate/index work arrays, and sorting arrays.
    signed_minimum = np.min(signed, axis=0)
    signed_maximum = np.max(signed, axis=0)
    signed_span = signed_maximum - signed_minimum
    logical_shape = np.asarray(routing.logical_grid_shape, dtype=np.int64)
    block_shape = np.asarray(routing.storage_block_shape, dtype=np.int64)
    extents = np.minimum(
        block_shape[None, :],
        logical_shape[None, :] - source_blocks * block_shape[None, :],
    )
    if np.any(extents <= 0):
        raise GraphAdapterError("Source block lies outside the logical grid.")
    brick_shapes = extents + signed_span[None, :]
    maximum_lifted_brick_nodes = int(
        np.max(np.prod(brick_shapes, axis=1, dtype=np.int64), initial=0)
    )
    maximum_source_nodes_per_block = int(
        np.max(np.prod(extents, axis=1, dtype=np.int64), initial=0)
    )
    brick_bytes = (maximum_lifted_brick_nodes + 7) // 8
    # 160 bytes per potentially active lifted node is intentionally
    # conservative for all uint8/int64 coordinate, sorting, and grouping
    # arrays used by the current implementation.
    maximum_lifted_transient_bytes = (
        2 * brick_bytes
        + 160 * maximum_lifted_brick_nodes
        + 64 * maximum_source_nodes_per_block
        + 8 * routing.stencil_offset_count
        + 64 * 1024
    )
    # Conservative Python-map allowance plus CSR assembly.  Only one lifted
    # source-block brick is live at a time.
    transient_upper = (
        target_upper * (128 + word_bytes)
        + edge_upper * 48
        + maximum_lifted_transient_bytes
        + 4 * 1024 * 1024
    )
    complete_pairs = int(source_field.occupied_node_count) * routing.stencil_offset_count
    failures: list[str] = []
    if target_upper > resolved_limits.max_target_blocks:
        failures.append("target_block_count_upper")
    if edge_upper > resolved_limits.max_source_target_edges:
        failures.append("source_target_edge_count_upper")
    if region_operations_upper > resolved_limits.max_bitset_region_operations:
        failures.append("bitset_region_operations_upper")
    if atlas_retained_upper > resolved_limits.max_retained_bytes:
        failures.append("atlas_retained_bytes_upper")
    if transient_upper > resolved_limits.max_transient_bytes:
        failures.append("transient_bytes_upper")
    predicted_peak_upper = (
        int(source_field.retained_array_bytes)
        + routing.retained_array_bytes
        + atlas_retained_upper
        + transient_upper
    )
    if predicted_peak_upper > resolved_limits.max_total_peak_bytes:
        failures.append("total_peak_bytes_upper")
    approved = not failures
    plan = DensitySupportAtlasPlan(
        source_field_identity=str(source_field.content_identity),
        source_node_count=int(source_field.occupied_node_count),
        source_block_count=int(source_field.source_block_count),
        stencil_offset_count=routing.stencil_offset_count,
        block_word_count=routing.block_word_count,
        maximum_target_blocks_per_source_upper=maximum_per_source,
        target_block_count_upper=target_upper,
        source_target_edge_count_upper=edge_upper,
        target_support_node_count_upper=target_node_upper,
        bitset_region_operations_upper=region_operations_upper,
        source_retained_bytes=int(source_field.retained_array_bytes),
        routing_retained_bytes=routing.retained_array_bytes,
        atlas_retained_bytes_upper=atlas_retained_upper,
        maximum_lifted_brick_nodes=maximum_lifted_brick_nodes,
        maximum_lifted_transient_bytes=maximum_lifted_transient_bytes,
        transient_bytes_upper=transient_upper,
        complete_fine_pair_count_reference=complete_pairs,
        approved=approved,
        limits=resolved_limits,
        metadata={
            "planner": "ld8_s1_axis_product_and_lifted_brick_bound_v1",
            "signed_stencil_minimum": signed_minimum.tolist(),
            "signed_stencil_maximum": signed_maximum.tolist(),
            "axis_unique_offset_counts": [int(item.size) for item in axis_unique_offsets],
            "axis_target_count_cache_entries": int(sum(len(item) for item in axis_target_counts)),
            "complete_fine_pair_array_allocated": False,
            "predicted_total_peak_bytes_upper": predicted_peak_upper,
            "failure_fields": failures,
        },
    )
    if not approved:
        raise GraphComplexityError(
            "Density support-atlas planning exceeded limits: " + ", ".join(failures)
        )
    return plan
