"""Canonical target-owned direct realization for LD8-S2.

The executor consumes one globally aggregated packed CIC source, the exact finite
periodic Gaussian stencil, a source-independent block-routing template, and the
field-specific exact support atlas.  Each target block has one deterministic
owner.  Source/stencil work is processed in bounded NumPy chunks and completed
blocks are packed immediately; no global pair or target-coordinate array is
allocated.

Periodic CIC assignment follows Hockney and Eastwood, *Computer Simulation
Using Particles* (1988).  Target ownership, translated-source interval pruning,
and immediate packed realization are project-specific mdstats designs.
"""

from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_block_routing import (
    PeriodicKernelBlockRouting,
    bitset_popcount,
    bitset_popcounts,
    block_grid_shape,
    local_node_count,
    stencil_content_identity,
    unpack_local_bitset,
)
from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_kernel import PeriodicGaussianStencilSupport
from .density_packed_field import PeriodicPackedBlockScalarField3D
from .density_support_atlas import (
    DensitySupportAtlas,
    PeriodicPackedCICSourceField3D,
)
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits
from .density_scheduler import current_density_worker_count, current_density_worker_lease
from .density_autotune import autotuned_group_size_multiplier

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

DENSITY_DIRECT_REALIZATION_LIMITS_SCHEMA = (
    "mdstats.density-direct-realization-limits.v2"
)
DENSITY_DIRECT_REALIZATION_PLAN_SCHEMA = "mdstats.density-direct-realization-plan.v1"

DEFAULT_MAX_DIRECT_TARGET_BLOCKS = 2_000_000
DEFAULT_MAX_DIRECT_TARGET_NODES = 20_000_000
DEFAULT_MAX_DIRECT_CANDIDATE_PAIRS = 500_000_000
DEFAULT_MAX_DIRECT_EXACT_CONTRIBUTIONS = 500_000_000
DEFAULT_DIRECT_PAIR_CHUNK_SIZE = 262_144
DEFAULT_MAX_DIRECT_TRANSIENT_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_DIRECT_RETAINED_BYTES = 1_000_000_000


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _nonempty_string(value: Any, *, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GraphStyleError(f"{name} must be a nonempty string.")
    return value


def _readonly_array(
    value: Any,
    dtype: Any,
    *,
    ndim: int | None = None,
    name: str,
) -> NDArray[Any]:
    array = np.array(value, dtype=dtype, copy=True, order="C")
    if ndim is not None and array.ndim != ndim:
        raise GraphAdapterError(
            f"{name} must be {ndim}-dimensional; received shape {array.shape}."
        )
    if np.issubdtype(array.dtype, np.floating) and np.any(~np.isfinite(array)):
        raise GraphAdapterError(f"{name} must contain only finite values.")
    array.setflags(write=False)
    return array


@dataclass(frozen=True, slots=True)
class DensityDirectRealizationLimits:
    """Runtime-derived transactional limits for one direct realization.

    Omitted values are resolved from the active host/job memory and CPU budget.
    Wall-time metadata is advisory only.  The legacy ``DEFAULT_*`` constants
    remain importable for compatibility but no longer define public default
    admission behavior.
    """

    max_target_blocks: int | None = None
    max_target_nodes: int | None = None
    max_candidate_pairs: int | None = None
    max_exact_contributions: int | None = None
    max_pair_chunk_size: int | None = None
    max_transient_bytes: int | None = None
    max_retained_bytes: int | None = None
    max_total_peak_bytes: int | None = None
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_DIRECT_REALIZATION_LIMITS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version not in {
            DENSITY_DIRECT_REALIZATION_LIMITS_SCHEMA,
            "mdstats.density-direct-realization-limits.v1",
        }:
            raise GraphAdapterError(
                f"Unsupported direct-realization limits schema {self.schema_version!r}."
            )
        budget, model, derived = resolve_density_resource_limits()
        defaults = {
            "max_target_blocks": derived["max_density_blocks"],
            "max_target_nodes": derived["max_density_nonzero_nodes"],
            "max_candidate_pairs": derived["max_density_kernel_pairs"],
            "max_exact_contributions": derived["max_density_kernel_pairs"],
            # The pair tile is an execution granularity, not a scene-size cap.
            # Keep it cache-conscious while reducing it on small-memory jobs.
            "max_pair_chunk_size": max(
                1_024, min(DEFAULT_DIRECT_PAIR_CHUNK_SIZE, budget.max_memory_bytes // 512)
            ),
            "max_transient_bytes": budget.max_memory_bytes,
            "max_retained_bytes": budget.max_memory_bytes,
            "max_total_peak_bytes": budget.max_memory_bytes,
        }
        memory_names = {
            "max_transient_bytes",
            "max_retained_bytes",
            "max_total_peak_bytes",
        }
        for name, default in defaults.items():
            current = getattr(self, name)
            resolved = default if current is None else min(default, _positive_int(current, name=name))
            if name in memory_names:
                resolved = min(resolved, budget.max_memory_bytes)
            object.__setattr__(self, name, resolved)
        metadata = dict(freeze_json_mapping(self.metadata))
        metadata.setdefault("resource_policy", "runtime_derived_v1")
        metadata.setdefault("max_threads", budget.max_threads)
        metadata.setdefault("max_wall_time_seconds", budget.max_wall_time_seconds)
        metadata.setdefault("time_model_source", model.calibration_source)
        object.__setattr__(self, "metadata", freeze_json_mapping(metadata))
        object.__setattr__(self, "schema_version", DENSITY_DIRECT_REALIZATION_LIMITS_SCHEMA)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "max_target_blocks": self.max_target_blocks,
            "max_target_nodes": self.max_target_nodes,
            "max_candidate_pairs": self.max_candidate_pairs,
            "max_exact_contributions": self.max_exact_contributions,
            "max_pair_chunk_size": self.max_pair_chunk_size,
            "max_transient_bytes": self.max_transient_bytes,
            "max_retained_bytes": self.max_retained_bytes,
            "max_total_peak_bytes": self.max_total_peak_bytes,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityDirectRealizationLimits":
        return cls(
            schema_version=str(value.get("schema_version", DENSITY_DIRECT_REALIZATION_LIMITS_SCHEMA)),
            max_target_blocks=int(value["max_target_blocks"]),
            max_target_nodes=int(value["max_target_nodes"]),
            max_candidate_pairs=int(value["max_candidate_pairs"]),
            max_exact_contributions=int(value["max_exact_contributions"]),
            max_pair_chunk_size=int(value["max_pair_chunk_size"]),
            max_transient_bytes=int(value["max_transient_bytes"]),
            max_retained_bytes=int(value["max_retained_bytes"]),
            max_total_peak_bytes=(
                None if value.get("max_total_peak_bytes") is None
                else int(value["max_total_peak_bytes"])
            ),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityDirectRealizationPlan:
    """Identity-bound exact/conservative work plan for target-owned realization."""

    source_field_identity: str
    routing_identity: str
    atlas_identity: str
    stencil_identity: str
    target_block_count: int
    target_support_node_count: int
    source_target_edge_count: int
    exact_contribution_count: int
    conservative_candidate_pair_count: int
    pair_chunk_size: int
    source_coordinate_bytes: int
    reverse_csr_bytes: int
    peak_pair_workspace_bytes: int
    accumulator_bytes: int
    packed_field_bytes_upper: int
    predicted_peak_bytes: int
    limits: DensityDirectRealizationLimits
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_DIRECT_REALIZATION_PLAN_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_DIRECT_REALIZATION_PLAN_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported direct-realization plan schema {self.schema_version!r}."
            )
        for name in (
            "source_field_identity",
            "routing_identity",
            "atlas_identity",
            "stencil_identity",
        ):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise GraphAdapterError(f"{name} must be a SHA-256 digest.")
        for name in (
            "target_block_count",
            "target_support_node_count",
            "source_target_edge_count",
            "exact_contribution_count",
            "conservative_candidate_pair_count",
            "pair_chunk_size",
            "source_coordinate_bytes",
            "reverse_csr_bytes",
            "peak_pair_workspace_bytes",
            "accumulator_bytes",
            "packed_field_bytes_upper",
            "predicted_peak_bytes",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        if self.target_block_count <= 0 or self.target_support_node_count <= 0:
            raise GraphAdapterError("A direct-realization plan cannot be empty.")
        if self.pair_chunk_size <= 0:
            raise GraphAdapterError("pair_chunk_size must be positive.")
        if self.conservative_candidate_pair_count < self.exact_contribution_count:
            raise GraphAdapterError(
                "conservative_candidate_pair_count cannot be smaller than exact work."
            )
        if not isinstance(self.limits, DensityDirectRealizationLimits):
            raise TypeError("limits must be DensityDirectRealizationLimits.")
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def content_identity(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.schema_version.encode("ascii"))
        for value in (
            self.source_field_identity,
            self.routing_identity,
            self.atlas_identity,
            self.stencil_identity,
        ):
            digest.update(value.encode("ascii"))
        digest.update(
            np.asarray(
                [
                    self.target_block_count,
                    self.target_support_node_count,
                    self.source_target_edge_count,
                    self.exact_contribution_count,
                    self.conservative_candidate_pair_count,
                    self.pair_chunk_size,
                    self.source_coordinate_bytes,
                    self.reverse_csr_bytes,
                    self.peak_pair_workspace_bytes,
                    self.accumulator_bytes,
                    self.packed_field_bytes_upper,
                    self.predicted_peak_bytes,
                ],
                dtype=np.int64,
            ).tobytes()
        )
        return digest.hexdigest()

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_field_identity": self.source_field_identity,
            "routing_identity": self.routing_identity,
            "atlas_identity": self.atlas_identity,
            "stencil_identity": self.stencil_identity,
            "target_block_count": self.target_block_count,
            "target_support_node_count": self.target_support_node_count,
            "source_target_edge_count": self.source_target_edge_count,
            "exact_contribution_count": self.exact_contribution_count,
            "conservative_candidate_pair_count": self.conservative_candidate_pair_count,
            "pair_chunk_size": self.pair_chunk_size,
            "source_coordinate_bytes": self.source_coordinate_bytes,
            "reverse_csr_bytes": self.reverse_csr_bytes,
            "peak_pair_workspace_bytes": self.peak_pair_workspace_bytes,
            "accumulator_bytes": self.accumulator_bytes,
            "packed_field_bytes_upper": self.packed_field_bytes_upper,
            "predicted_peak_bytes": self.predicted_peak_bytes,
            "limits": self.limits.to_json_dict(),
            "content_identity": self.content_identity,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(
        cls, value: Mapping[str, Any]
    ) -> "DensityDirectRealizationPlan":
        return cls(
            schema_version=str(value["schema_version"]),
            source_field_identity=str(value["source_field_identity"]),
            routing_identity=str(value["routing_identity"]),
            atlas_identity=str(value["atlas_identity"]),
            stencil_identity=str(value["stencil_identity"]),
            target_block_count=int(value["target_block_count"]),
            target_support_node_count=int(value["target_support_node_count"]),
            source_target_edge_count=int(value["source_target_edge_count"]),
            exact_contribution_count=int(value["exact_contribution_count"]),
            conservative_candidate_pair_count=int(
                value["conservative_candidate_pair_count"]
            ),
            pair_chunk_size=int(value["pair_chunk_size"]),
            source_coordinate_bytes=int(value["source_coordinate_bytes"]),
            reverse_csr_bytes=int(value["reverse_csr_bytes"]),
            peak_pair_workspace_bytes=int(value["peak_pair_workspace_bytes"]),
            accumulator_bytes=int(value["accumulator_bytes"]),
            packed_field_bytes_upper=int(value["packed_field_bytes_upper"]),
            predicted_peak_bytes=int(value["predicted_peak_bytes"]),
            limits=DensityDirectRealizationLimits.from_json_dict(value["limits"]),
            metadata=value.get("metadata", {}),
        )


def _validate_inputs(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
) -> None:
    if not isinstance(source_field, PeriodicPackedCICSourceField3D):
        raise TypeError("source_field must be PeriodicPackedCICSourceField3D.")
    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    if not isinstance(routing, PeriodicKernelBlockRouting):
        raise TypeError("routing must be PeriodicKernelBlockRouting.")
    if not isinstance(atlas, DensitySupportAtlas):
        raise TypeError("atlas must be DensitySupportAtlas.")
    logical = source_field.logical_grid_shape
    if (
        stencil.grid_shape != logical
        or routing.logical_grid_shape != logical
        or atlas.logical_grid_shape != logical
    ):
        raise GraphAdapterError(
            "Source, stencil, routing, and atlas must share logical_grid_shape."
        )
    if (
        routing.storage_block_shape != source_field.storage_block_shape
        or atlas.storage_block_shape != source_field.storage_block_shape
    ):
        raise GraphAdapterError(
            "Source, routing, and atlas must share storage_block_shape."
        )
    if atlas.source_field_identity != source_field.content_identity:
        raise GraphAdapterError("Atlas source identity does not match source_field.")
    if atlas.routing_identity != routing.cache_identity:
        raise GraphAdapterError("Atlas routing identity does not match routing.")
    if routing.stencil_identity != stencil_content_identity(stencil):
        raise GraphAdapterError("Routing stencil identity does not match stencil.")
    if atlas.source_block_count != source_field.source_block_count:
        raise GraphAdapterError("Atlas source rows do not align with source_field.")


def _source_coordinate_table(
    source_field: PeriodicPackedCICSourceField3D,
) -> tuple[IntArray, IntArray, IntArray]:
    """Return global coordinates and occupied bounding boxes in packed-value order."""

    block = np.asarray(source_field.storage_block_shape, dtype=np.int64)
    total = source_field.occupied_node_count
    coordinates = np.empty((total, 3), dtype=np.int64)
    minima = np.empty((source_field.source_block_count, 3), dtype=np.int64)
    maxima = np.empty((source_field.source_block_count, 3), dtype=np.int64)
    for row, block_index in enumerate(source_field.source_block_indices):
        start = int(source_field.block_value_offsets[row])
        stop = int(source_field.block_value_offsets[row + 1])
        local_flat = unpack_local_bitset(
            source_field.occupancy_bitsets[row], source_field.storage_block_shape
        )
        local = np.column_stack(
            np.unravel_index(local_flat, source_field.storage_block_shape, order="C")
        ).astype(np.int64, copy=False)
        current = block_index.astype(np.int64)[None, :] * block[None, :] + local
        coordinates[start:stop] = current
        minima[row] = np.min(current, axis=0)
        maxima[row] = np.max(current, axis=0)
    coordinates.setflags(write=False)
    minima.setflags(write=False)
    maxima.setflags(write=False)
    return coordinates, minima, maxima


def _reverse_source_target_csr(
    atlas: DensitySupportAtlas,
) -> tuple[IntArray, NDArray[np.int32]]:
    targets = np.asarray(atlas.source_to_target_block_indices, dtype=np.int32)
    source_counts = np.diff(atlas.source_to_target_block_ranges).astype(
        np.int64, copy=False
    )
    source_ids = np.repeat(
        np.arange(atlas.source_block_count, dtype=np.int32), source_counts
    )
    if source_ids.size != targets.size:
        raise GraphAdapterError("Source-to-target CSR edge count is inconsistent.")
    order = np.lexsort((source_ids, targets))
    sorted_targets = targets[order]
    sources = np.asarray(source_ids[order], dtype=np.int32)
    counts = np.bincount(
        sorted_targets, minlength=atlas.target_block_count
    ).astype(np.int64, copy=False)
    ranges = np.concatenate(
        (np.asarray([0], dtype=np.int64), np.cumsum(counts, dtype=np.int64))
    )
    duplicate = (
        (sorted_targets[1:] == sorted_targets[:-1])
        & (sources[1:] == sources[:-1])
    )
    if np.any(duplicate):
        raise GraphAdapterError(
            "Reverse target-to-source rows must be unique and canonical."
        )
    ranges.setflags(write=False)
    sources.setflags(write=False)
    return ranges, sources


def _axis_interval_intersection_mask(
    offsets: IntArray,
    *,
    source_minimum: int,
    source_maximum: int,
    target_start: int,
    target_stop: int,
    logical_size: int,
) -> NDArray[np.bool_]:
    """Conservatively test translated occupied-source intervals against one target."""

    low = source_minimum + offsets
    high = source_maximum + offsets
    low_image = np.floor_divide(low, logical_size)
    high_image = np.floor_divide(high, logical_size)
    low_mod = np.mod(low, logical_size)
    high_mod = np.mod(high, logical_size)
    target_end = target_stop - 1
    same_image = low_image == high_image
    ordinary = (low_mod <= target_end) & (high_mod >= target_start)
    wrapped = (target_end >= low_mod) | (target_start <= high_mod)
    return np.where(same_image, ordinary, wrapped)


def _relevant_stencil_mask(
    signed_offsets: IntArray,
    source_minimum: IntArray,
    source_maximum: IntArray,
    target_start: IntArray,
    target_stop: IntArray,
    logical_shape: tuple[int, int, int],
) -> NDArray[np.bool_]:
    mask = np.ones(signed_offsets.shape[0], dtype=bool)
    for axis in range(3):
        mask &= _axis_interval_intersection_mask(
            signed_offsets[:, axis].astype(np.int64, copy=False),
            source_minimum=int(source_minimum[axis]),
            source_maximum=int(source_maximum[axis]),
            target_start=int(target_start[axis]),
            target_stop=int(target_stop[axis]),
            logical_size=int(logical_shape[axis]),
        )
    return mask


def _relevant_stencil_matrix(
    signed_offsets: IntArray,
    source_minima: IntArray,
    source_maxima: IntArray,
    target_start: IntArray,
    target_stop: IntArray,
    logical_shape: tuple[int, int, int],
) -> NDArray[np.bool_]:
    """Vectorized translated-interval test for many source blocks."""

    minima = np.asarray(source_minima, dtype=np.int64)
    maxima = np.asarray(source_maxima, dtype=np.int64)
    if minima.shape != maxima.shape or minima.ndim != 2 or minima.shape[1:] != (3,):
        raise GraphAdapterError("source interval arrays must have shape (n, 3).")
    offsets = np.asarray(signed_offsets, dtype=np.int64)
    mask = np.ones((minima.shape[0], offsets.shape[0]), dtype=bool)
    for axis in range(3):
        low = minima[:, axis, None] + offsets[None, :, axis]
        high = maxima[:, axis, None] + offsets[None, :, axis]
        logical_size = int(logical_shape[axis])
        low_image = np.floor_divide(low, logical_size)
        high_image = np.floor_divide(high, logical_size)
        low_mod = np.mod(low, logical_size)
        high_mod = np.mod(high, logical_size)
        target_end = int(target_stop[axis]) - 1
        ordinary = (low_mod <= target_end) & (
            high_mod >= int(target_start[axis])
        )
        wrapped = (target_end >= low_mod) | (
            int(target_start[axis]) <= high_mod
        )
        mask &= np.where(low_image == high_image, ordinary, wrapped)
    return mask


def _packed_field_bytes_upper(atlas: DensitySupportAtlas) -> int:
    block_count = atlas.target_block_count
    node_count = atlas.target_support_node_count
    return int(
        atlas.active_target_block_indices.nbytes
        + atlas.target_support_bitsets.nbytes
        + (block_count + 1) * np.dtype(np.int64).itemsize
        + node_count * np.dtype(np.float64).itemsize
        + 2 * block_count * np.dtype(np.float64).itemsize
    )


def plan_target_owned_direct_realization(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
    *,
    limits: DensityDirectRealizationLimits | None = None,
) -> DensityDirectRealizationPlan:
    """Plan exact target-owned work before allocating floating target values."""

    _validate_inputs(source_field, stencil, routing, atlas)
    resolved = limits or DensityDirectRealizationLimits()
    if not isinstance(resolved, DensityDirectRealizationLimits):
        raise TypeError("limits must be DensityDirectRealizationLimits or None.")
    if atlas.target_block_count > resolved.max_target_blocks:
        raise GraphComplexityError(
            "target_block_count exceeds max_target_blocks: "
            f"{atlas.target_block_count} > {resolved.max_target_blocks}."
        )
    if atlas.target_support_node_count > resolved.max_target_nodes:
        raise GraphComplexityError(
            "target_support_node_count exceeds max_target_nodes: "
            f"{atlas.target_support_node_count} > {resolved.max_target_nodes}."
        )
    exact = source_field.occupied_node_count * stencil.stencil_offset_count
    if exact > resolved.max_exact_contributions:
        raise GraphComplexityError(
            "exact_contribution_count exceeds max_exact_contributions: "
            f"{exact} > {resolved.max_exact_contributions}."
        )

    source_coordinates, source_minima, source_maxima = _source_coordinate_table(
        source_field
    )
    target_ranges, target_sources = _reverse_source_target_csr(atlas)
    block = np.asarray(source_field.storage_block_shape, dtype=np.int64)
    signed = routing.signed_offsets.astype(np.int64, copy=False)
    candidate = 0
    maximum_source_nodes = 0
    maximum_relevant_offsets = 0
    for target_row, target_index in enumerate(atlas.active_target_block_indices):
        target_start = target_index.astype(np.int64) * block
        extent = np.asarray(
            routing.extent_for_block(tuple(int(value) for value in target_index)),
            dtype=np.int64,
        )
        target_stop = target_start + extent
        source_rows = target_sources[
            int(target_ranges[target_row]) : int(target_ranges[target_row + 1])
        ].astype(np.int64, copy=False)
        if source_rows.size:
            relevant = _relevant_stencil_matrix(
                signed,
                source_minima[source_rows],
                source_maxima[source_rows],
                target_start,
                target_stop,
                source_field.logical_grid_shape,
            )
            offset_counts = np.count_nonzero(relevant, axis=1).astype(
                np.int64, copy=False
            )
            source_counts = (
                source_field.block_value_offsets[source_rows + 1]
                - source_field.block_value_offsets[source_rows]
            ).astype(np.int64, copy=False)
            candidate += int(np.dot(source_counts, offset_counts))
            maximum_source_nodes = max(
                maximum_source_nodes, int(np.max(source_counts, initial=0))
            )
            maximum_relevant_offsets = max(
                maximum_relevant_offsets, int(np.max(offset_counts, initial=0))
            )
            if candidate > resolved.max_candidate_pairs:
                raise GraphComplexityError(
                    "conservative_candidate_pair_count exceeds max_candidate_pairs: "
                    f"> {resolved.max_candidate_pairs}."
                )
    if candidate < exact:
        raise GraphAdapterError(
            "Translated-source interval planning underestimated exact contributions."
        )

    pair_chunk = resolved.max_pair_chunk_size
    # Conservative package-owned arrays per pair: target coordinates (3*int64),
    # mask, nonzero indices (2*int64), local index, and contribution value.
    # Conservative package-owned chunk arrays include target coordinates, masks,
    # accepted pair indices, local coordinates/indices, and contribution values.
    peak_pair_workspace = int(128 * pair_chunk + 16 * maximum_relevant_offsets + 4096)
    accumulator_bytes = local_node_count(source_field.storage_block_shape) * 8
    source_coordinate_bytes = int(
        source_coordinates.nbytes + source_minima.nbytes + source_maxima.nbytes
    )
    reverse_csr_bytes = int(target_ranges.nbytes + target_sources.nbytes)
    retained_upper = _packed_field_bytes_upper(atlas)
    transient = int(
        source_coordinate_bytes
        + reverse_csr_bytes
        + peak_pair_workspace
        + accumulator_bytes
    )
    if transient > resolved.max_transient_bytes:
        raise GraphComplexityError(
            "predicted transient workspace exceeds max_transient_bytes: "
            f"{transient} > {resolved.max_transient_bytes}."
        )
    if retained_upper > resolved.max_retained_bytes:
        raise GraphComplexityError(
            "packed field upper bound exceeds max_retained_bytes: "
            f"{retained_upper} > {resolved.max_retained_bytes}."
        )
    predicted_peak = 2 * retained_upper + transient
    if predicted_peak > resolved.max_total_peak_bytes:
        raise GraphComplexityError(
            "predicted direct-realization peak exceeds max_total_peak_bytes: "
            f"{predicted_peak} > {resolved.max_total_peak_bytes}."
        )
    return DensityDirectRealizationPlan(
        source_field_identity=source_field.content_identity,
        routing_identity=routing.cache_identity,
        atlas_identity=atlas.content_identity,
        stencil_identity=stencil_content_identity(stencil),
        target_block_count=atlas.target_block_count,
        target_support_node_count=atlas.target_support_node_count,
        source_target_edge_count=atlas.source_target_edge_count,
        exact_contribution_count=exact,
        conservative_candidate_pair_count=candidate,
        pair_chunk_size=pair_chunk,
        source_coordinate_bytes=source_coordinate_bytes,
        reverse_csr_bytes=reverse_csr_bytes,
        peak_pair_workspace_bytes=peak_pair_workspace,
        accumulator_bytes=accumulator_bytes,
        packed_field_bytes_upper=retained_upper,
        # The immutable packed-field constructor validates/copies the completed
        # arrays, so both caller-owned and immutable arrays coexist briefly.
        predicted_peak_bytes=predicted_peak,
        limits=resolved,
        metadata={
            "planner": "ld14_vectorized_source_interval_candidate_plan_v2",
            "maximum_source_nodes_per_block": maximum_source_nodes,
            "maximum_relevant_offsets_per_source_target_edge": maximum_relevant_offsets,
            "complete_fine_pair_array_allocated": False,
            "global_target_coordinate_array_allocated": False,
        },
    )


def _validate_approved_plan(
    plan: DensityDirectRealizationPlan,
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
) -> None:
    if not isinstance(plan, DensityDirectRealizationPlan):
        raise TypeError("approved_plan must be DensityDirectRealizationPlan.")
    expected = (
        source_field.content_identity,
        routing.cache_identity,
        atlas.content_identity,
        stencil_content_identity(stencil),
    )
    actual = (
        plan.source_field_identity,
        plan.routing_identity,
        plan.atlas_identity,
        plan.stencil_identity,
    )
    if actual != expected:
        raise GraphAdapterError("approved_plan identities do not match realization inputs.")


def _apply_total_mass_correction(
    node_masses: FloatArray, *, total_measure: float
) -> int:
    if node_masses.ndim != 1 or node_masses.size == 0:
        raise GraphAdapterError("node_masses must be a nonempty vector.")
    index = int(np.argmax(node_masses))
    residual = float(total_measure) - float(np.sum(node_masses, dtype=np.float64))
    corrected = float(node_masses[index]) + residual
    if not np.isfinite(corrected) or corrected <= 0.0:
        raise GraphAdapterError(
            "Direct-realization normalization produced a nonpositive correction node."
        )
    node_masses[index] = corrected
    return index


def realize_density_target_owned_direct(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    routing: PeriodicKernelBlockRouting,
    atlas: DensitySupportAtlas,
    *,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    limits: DensityDirectRealizationLimits | None = None,
    approved_plan: DensityDirectRealizationPlan | None = None,
) -> PeriodicPackedBlockScalarField3D:
    """Realize one exact packed scientific field with canonical target ownership."""

    _validate_inputs(source_field, stencil, routing, atlas)
    key = _nonempty_string(field_key, name="field_key")
    resolved_label = _nonempty_string(label, name="label")
    units = _nonempty_string(physical_units, name="physical_units")
    metric = _nonempty_string(broadening_metric, name="broadening_metric")
    if approved_plan is None:
        plan = plan_target_owned_direct_realization(
            source_field, stencil, routing, atlas, limits=limits
        )
    else:
        _validate_approved_plan(
            approved_plan, source_field, stencil, routing, atlas
        )
        if limits is not None and limits != approved_plan.limits:
            raise GraphAdapterError(
                "Explicit limits disagree with the identity-bound approved_plan."
            )
        plan = approved_plan

    source_coordinates, source_minima, source_maxima = _source_coordinate_table(
        source_field
    )
    target_ranges, target_sources = _reverse_source_target_csr(atlas)
    logical = np.asarray(source_field.logical_grid_shape, dtype=np.int64)
    block_shape = source_field.storage_block_shape
    block = np.asarray(block_shape, dtype=np.int64)
    block_nodes = local_node_count(block_shape)
    signed = routing.signed_offsets.astype(np.int64, copy=False)
    weights = stencil.active_weights
    support_counts = bitset_popcounts(atlas.target_support_bitsets)
    offsets = np.concatenate(
        (np.asarray([0], dtype=np.int64), np.cumsum(support_counts, dtype=np.int64))
    )
    node_masses = np.empty(atlas.target_support_node_count, dtype=np.float64)
    accepted_contributions = 0
    candidate_pairs = 0
    chunk_count = 0
    peak_chunk_pairs = 0
    peak_pair_workspace = 0

    def realize_target_row(
        target_row: int,
    ) -> tuple[int, int, int, int, int]:
        # Target ownership makes this write-disjoint: every worker owns one
        # packed output slice and accumulates into a private dense block.
        accumulator = np.zeros(block_nodes, dtype=np.float64)
        target_index = atlas.active_target_block_indices[target_row]
        target_start = target_index.astype(np.int64) * block
        extent = np.asarray(
            routing.extent_for_block(tuple(int(value) for value in target_index)),
            dtype=np.int64,
        )
        target_stop = target_start + extent
        source_rows = target_sources[
            int(target_ranges[target_row]) : int(target_ranges[target_row + 1])
        ].astype(np.int64, copy=False)
        local_candidate_pairs = 0
        local_accepted = 0
        local_chunk_count = 0
        local_peak_chunk_pairs = 0
        local_peak_workspace = 0
        if source_rows.size:
            relevant = _relevant_stencil_matrix(
                signed,
                source_minima[source_rows],
                source_maxima[source_rows],
                target_start,
                target_stop,
                source_field.logical_grid_shape,
            )
            edge_rows, offset_indices = np.nonzero(relevant)
            if edge_rows.size:
                source_rows_per_edge = source_rows[edge_rows]
                source_counts_per_edge = (
                    source_field.block_value_offsets[source_rows_per_edge + 1]
                    - source_field.block_value_offsets[source_rows_per_edge]
                ).astype(np.int64, copy=False)
                edge_pair_ends = np.cumsum(source_counts_per_edge, dtype=np.int64)
                total_pairs = int(edge_pair_ends[-1])
                local_candidate_pairs += total_pairs
                for pair_start in range(0, total_pairs, plan.pair_chunk_size):
                    pair_stop = min(total_pairs, pair_start + plan.pair_chunk_size)
                    pair_positions = np.arange(pair_start, pair_stop, dtype=np.int64)
                    selected_edges = np.searchsorted(
                        edge_pair_ends, pair_positions, side="right"
                    ).astype(np.int64, copy=False)
                    prior_ends = np.where(
                        selected_edges == 0, 0, edge_pair_ends[selected_edges - 1]
                    )
                    local_source_positions = pair_positions - prior_ends
                    selected_source_rows = source_rows_per_edge[selected_edges]
                    source_indices = (
                        source_field.block_value_offsets[selected_source_rows]
                        + local_source_positions
                    ).astype(np.int64, copy=False)
                    chosen_offsets = offset_indices[selected_edges]
                    targets = np.mod(
                        signed[chosen_offsets] + source_coordinates[source_indices],
                        logical[None, :],
                    )
                    inside = np.all(
                        (targets >= target_start[None, :])
                        & (targets < target_stop[None, :]),
                        axis=1,
                    )
                    accepted_rows = np.flatnonzero(inside).astype(
                        np.int64, copy=False
                    )
                    if accepted_rows.size:
                        local_accepted += int(accepted_rows.size)
                        accepted_targets = targets[accepted_rows]
                        local = accepted_targets - target_start[None, :]
                        local_flat = (
                            (local[:, 0] * block[1] + local[:, 1]) * block[2]
                            + local[:, 2]
                        ).astype(np.int64, copy=False)
                        contributions = (
                            weights[chosen_offsets[accepted_rows]]
                            * source_field.packed_values[source_indices[accepted_rows]]
                        )
                        # Destination-owned bounded bincount replaces contended
                        # global scatter while preserving one canonical target.
                        accumulator += np.bincount(
                            local_flat,
                            weights=contributions,
                            minlength=block_nodes,
                        ).astype(np.float64, copy=False)
                        local_peak_workspace = max(
                            local_peak_workspace,
                            int(
                                pair_positions.nbytes
                                + selected_edges.nbytes
                                + prior_ends.nbytes
                                + local_source_positions.nbytes
                                + selected_source_rows.nbytes
                                + source_indices.nbytes
                                + chosen_offsets.nbytes
                                + targets.nbytes
                                + inside.nbytes
                                + accepted_rows.nbytes
                                + accepted_targets.nbytes
                                + local_flat.nbytes
                                + contributions.nbytes
                            ),
                        )
                    else:
                        local_peak_workspace = max(
                            local_peak_workspace,
                            int(
                                pair_positions.nbytes
                                + selected_edges.nbytes
                                + source_indices.nbytes
                                + chosen_offsets.nbytes
                                + targets.nbytes
                                + inside.nbytes
                            ),
                        )
                    pair_count = pair_stop - pair_start
                    local_peak_chunk_pairs = max(local_peak_chunk_pairs, pair_count)
                    local_chunk_count += 1
        expected_local = unpack_local_bitset(
            atlas.target_support_bitsets[target_row], block_shape
        )
        actual_local = np.flatnonzero(accumulator > 0.0).astype(np.int64, copy=False)
        if not np.array_equal(actual_local, expected_local):
            missing = np.setdiff1d(expected_local, actual_local, assume_unique=True)
            extra = np.setdiff1d(actual_local, expected_local, assume_unique=True)
            raise GraphAdapterError(
                "Target-owned realization disagrees with the exact support atlas: "
                f"target_row={target_row}, missing={missing[:8].tolist()}, "
                f"extra={extra[:8].tolist()}."
            )
        current = np.array(accumulator[expected_local], dtype=np.float64, copy=True)
        if np.any(~np.isfinite(current)) or np.any(current <= 0.0):
            raise GraphAdapterError("A supported target node is nonpositive or nonfinite.")
        packed_start = int(offsets[target_row])
        packed_stop = int(offsets[target_row + 1])
        if packed_stop - packed_start != current.size:
            raise GraphAdapterError(
                "Atlas support count changed during target realization."
            )
        node_masses[packed_start:packed_stop] = current
        return (
            local_candidate_pairs,
            local_accepted,
            local_chunk_count,
            local_peak_chunk_pairs,
            local_peak_workspace,
        )

    lease = current_density_worker_lease()
    shared_transient = int(plan.source_coordinate_bytes + plan.reverse_csr_bytes)
    per_worker_transient = max(
        1, int(plan.peak_pair_workspace_bytes + plan.accumulator_bytes)
    )
    available_transient = (
        shared_transient + per_worker_transient
        if lease is None
        else max(shared_transient + per_worker_transient, int(lease.resources.transient_bytes))
    )
    memory_worker_cap = max(
        1, (available_transient - shared_transient) // per_worker_transient
    )
    target_count = int(atlas.target_block_count)
    cursor = 0
    while cursor < target_count:
        group_workers = max(
            1,
            min(
                current_density_worker_count(default=1),
                memory_worker_cap,
                target_count - cursor,
            ),
        )
        group_size = max(1, min(target_count - cursor, autotuned_group_size_multiplier(default=4) * group_workers))
        rows = tuple(range(cursor, cursor + group_size))
        if group_workers == 1:
            stats = tuple(realize_target_row(row) for row in rows)
        else:
            with ThreadPoolExecutor(
                max_workers=group_workers,
                thread_name_prefix="mdstats-density-direct",
            ) as pool:
                stats = tuple(pool.map(realize_target_row, rows))
        # Reductions follow canonical target-row order irrespective of worker
        # completion order.  Floating values themselves were written only by
        # their unique destination owners.
        for local_candidate, local_accepted, local_chunks, local_peak_pairs, local_peak_bytes in stats:
            candidate_pairs += int(local_candidate)
            accepted_contributions += int(local_accepted)
            chunk_count += int(local_chunks)
            peak_chunk_pairs = max(peak_chunk_pairs, int(local_peak_pairs))
            peak_pair_workspace = max(peak_pair_workspace, int(local_peak_bytes))
        cursor += group_size

    if candidate_pairs != plan.conservative_candidate_pair_count:
        raise GraphAdapterError(
            "Realized candidate-pair count disagrees with the approved plan."
        )
    if accepted_contributions != plan.exact_contribution_count:
        raise GraphAdapterError(
            "Accepted contribution count disagrees with source-node/stencil work: "
            f"{accepted_contributions} != {plan.exact_contribution_count}."
        )
    if node_masses.size != atlas.target_support_node_count:
        raise GraphAdapterError("Packed target-node count disagrees with the atlas.")
    raw_measure = float(np.sum(node_masses, dtype=np.float64))
    if not np.isfinite(raw_measure) or raw_measure <= 0.0:
        raise GraphAdapterError("Target-owned realization produced zero measure.")
    normalization_factor = source_field.total_measure / raw_measure
    node_masses *= normalization_factor
    correction_index = _apply_total_mass_correction(
        node_masses, total_measure=source_field.total_measure
    )
    voxel_volume = abs(float(np.linalg.det(stencil.display_cell))) / float(
        np.prod(source_field.logical_grid_shape, dtype=object)
    )
    node_masses /= voxel_volume
    packed_values = node_masses
    minima = np.empty(atlas.target_block_count, dtype=np.float64)
    maxima = np.empty(atlas.target_block_count, dtype=np.float64)
    for row, target_index in enumerate(atlas.active_target_block_indices):
        start = int(offsets[row])
        stop = int(offsets[row + 1])
        current = packed_values[start:stop]
        maxima[row] = float(np.max(current))
        extent = routing.extent_for_block(tuple(int(value) for value in target_index))
        valid_count = int(np.prod(extent, dtype=object))
        support_count = bitset_popcount(atlas.target_support_bitsets[row])
        minima[row] = float(np.min(current)) if support_count == valid_count else 0.0
    final_measure = float(np.sum(packed_values, dtype=np.float64)) * voxel_volume
    retained_bytes = int(
        atlas.active_target_block_indices.nbytes
        + atlas.target_support_bitsets.nbytes
        + offsets.nbytes
        + packed_values.nbytes
        + minima.nbytes
        + maxima.nbytes
    )
    if retained_bytes > plan.limits.max_retained_bytes:
        raise GraphComplexityError(
            "Realized packed field exceeds max_retained_bytes after construction."
        )
    return PeriodicPackedBlockScalarField3D(
        field_key=key,
        label=resolved_label,
        physical_units=units,
        logical_grid_shape=source_field.logical_grid_shape,
        storage_block_shape=source_field.storage_block_shape,
        active_block_indices=atlas.active_target_block_indices,
        occupancy_bitsets=atlas.target_support_bitsets,
        block_value_offsets=offsets,
        packed_values=packed_values,
        block_min_values=minima,
        block_max_values=maxima,
        display_cell=stencil.display_cell,
        total_measure=source_field.total_measure,
        gaussian_bandwidth=stencil.gaussian_bandwidth,
        broadening_metric=metric,
        source_provenance=source_field.source_provenance,
        metadata={
            **source_field.metadata.to_json_dict(),
            "reference_path": "ld8_s2_canonical_target_owned_direct",
            "production_backend": False,
            "source_field_identity": source_field.content_identity,
            "routing_identity": routing.cache_identity,
            "atlas_identity": atlas.content_identity,
            "stencil_identity": stencil_content_identity(stencil),
            "direct_realization_plan": plan.to_json_dict(),
            "exact_contribution_count": plan.exact_contribution_count,
            "conservative_candidate_pair_count": candidate_pairs,
            "accepted_contribution_count": accepted_contributions,
            "vectorized_chunk_count": chunk_count,
            "peak_chunk_pair_count": peak_chunk_pairs,
            "peak_pair_workspace_bytes": peak_pair_workspace,
            "raw_measure_before_final_normalization": raw_measure,
            "final_normalization_factor": float(normalization_factor),
            "mass_correction_index": correction_index,
            "final_measure": final_measure,
            "packed_field_bytes": retained_bytes,
            "deterministic_accumulation_order": (
                "destination_owned_target_blocks_with_canonical_per_block_reduction"
            ),
            "complete_fine_pair_array_allocated": False,
            "global_target_coordinate_array_allocated": False,
            "completed_dense_target_blocks_retained": False,
            "fixed_active_block_value_array_allocated": False,
        },
    )
