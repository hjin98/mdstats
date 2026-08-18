"""Exact shared HDR selection and lazy contour-support planning for LD8-S4.

The scientific field is immutable and all logical voxels have one common volume.
Multiple requested highest-density-region thresholds are therefore resolved from
one ascending value sort.  Cumulative work is performed in bounded chunks rather
than retaining a second full-length cumulative array.  The thresholds are exact
for the stored discrete field, including threshold ties.

Contour support is a conservative block-level plan.  It uses the packed field's
block extrema and periodic six-neighbour topology; it never changes the density
values or HDR thresholds.  Node/cell-level contour extraction remains owned by
LD9.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_sparse_reference import SparseHDRDetails
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

IntArray = NDArray[np.int64]
FloatArray = NDArray[np.float64]

DENSITY_HDR_BATCH_SCHEMA = "mdstats.density-hdr-batch.v1"
DENSITY_CONTOUR_SUPPORT_SCHEMA = "mdstats.density-contour-support.v1"
DEFAULT_HDR_CHUNK_SIZE = 1_048_576
DEFAULT_MAX_HDR_WORKSPACE_BYTES = 512 * 1024 * 1024


class _PackedFieldLike(Protocol):
    packed_values: FloatArray
    voxel_volume: float
    total_measure: float
    active_block_indices: NDArray[np.int32]
    block_min_values: FloatArray
    block_max_values: FloatArray
    block_grid_shape: tuple[int, int, int]
    field_key: str


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _fractions(values: Sequence[float]) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if not result:
        raise GraphStyleError("At least one HDR fraction is required.")
    if any(not np.isfinite(value) or not 0.0 < value < 1.0 for value in result):
        raise GraphStyleError("HDR fractions must lie strictly between zero and one.")
    if len(set(result)) != len(result):
        raise GraphStyleError("HDR fractions must be unique.")
    return result


@dataclass(frozen=True, slots=True)
class DensityHDRBatch:
    """Exact HDR results resolved together from one packed-field value ordering."""

    field_key: str
    fractions: tuple[float, ...]
    details: tuple[SparseHDRDetails, ...]
    value_count: int
    sort_workspace_bytes: int
    peak_cumulative_chunk_bytes: int
    algorithm: str = "single_sort_chunked_multi_hdr_v1"
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DENSITY_HDR_BATCH_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_HDR_BATCH_SCHEMA:
            raise GraphAdapterError(f"Unsupported HDR-batch schema {self.schema_version!r}.")
        if not isinstance(self.field_key, str) or not self.field_key:
            raise GraphAdapterError("field_key must be nonempty.")
        fractions = _fractions(self.fractions)
        if len(self.details) != len(fractions):
            raise GraphAdapterError("HDR details must align with fractions.")
        for fraction, detail in zip(fractions, self.details, strict=True):
            if not isinstance(detail, SparseHDRDetails):
                raise TypeError("details must contain SparseHDRDetails.")
            if detail.requested_mass_fraction != fraction:
                raise GraphAdapterError("HDR detail fraction does not match the batch.")
        object.__setattr__(self, "fractions", fractions)
        object.__setattr__(self, "value_count", _positive_int(self.value_count, name="value_count"))
        object.__setattr__(self, "sort_workspace_bytes", _positive_int(self.sort_workspace_bytes, name="sort_workspace_bytes"))
        if int(self.peak_cumulative_chunk_bytes) < 0:
            raise GraphAdapterError("peak_cumulative_chunk_bytes must be nonnegative.")
        object.__setattr__(self, "peak_cumulative_chunk_bytes", int(self.peak_cumulative_chunk_bytes))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def for_fraction(self, fraction: float) -> SparseHDRDetails:
        query = float(fraction)
        for stored, detail in zip(self.fractions, self.details, strict=True):
            if stored == query:
                return detail
        raise KeyError(query)

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "fractions": list(self.fractions),
            "details": [detail.to_json_dict() for detail in self.details],
            "value_count": self.value_count,
            "sort_workspace_bytes": self.sort_workspace_bytes,
            "peak_cumulative_chunk_bytes": self.peak_cumulative_chunk_bytes,
            "algorithm": self.algorithm,
            "metadata": self.metadata.to_json_dict(),
        }

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensityHDRBatch":
        details = tuple(
            SparseHDRDetails(
                schema_version=str(item["schema_version"]),
                requested_mass_fraction=float(item["requested_mass_fraction"]),
                threshold=float(item["threshold"]),
                achieved_mass_fraction=float(item["achieved_mass_fraction"]),
                selected_node_count=int(item["selected_node_count"]),
                threshold_tie_count=int(item["threshold_tie_count"]),
                selected_measure=float(item["selected_measure"]),
                total_measure=float(item["total_measure"]),
            )
            for item in value["details"]
        )
        return cls(
            schema_version=str(value["schema_version"]),
            field_key=str(value["field_key"]),
            fractions=tuple(value["fractions"]),
            details=details,
            value_count=int(value["value_count"]),
            sort_workspace_bytes=int(value["sort_workspace_bytes"]),
            peak_cumulative_chunk_bytes=int(value["peak_cumulative_chunk_bytes"]),
            algorithm=str(value.get("algorithm", "single_sort_chunked_multi_hdr_v1")),
            metadata=value.get("metadata", {}),
        )


@dataclass(frozen=True, slots=True)
class DensityContourSupport:
    """Conservative periodic block support for one exact HDR threshold."""

    field_key: str
    hdr_details: SparseHDRDetails
    selected_block_indices: NDArray[np.int32]
    crossing_block_indices: NDArray[np.int32]
    halo_block_indices: NDArray[np.int32]
    component_labels: NDArray[np.int32] | None
    block_grid_shape: tuple[int, int, int]
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(default_factory=dict)
    schema_version: str = DENSITY_CONTOUR_SUPPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_CONTOUR_SUPPORT_SCHEMA:
            raise GraphAdapterError(f"Unsupported contour-support schema {self.schema_version!r}.")
        if not isinstance(self.field_key, str) or not self.field_key:
            raise GraphAdapterError("field_key must be nonempty.")
        if not isinstance(self.hdr_details, SparseHDRDetails):
            raise TypeError("hdr_details must be SparseHDRDetails.")
        for name in ("selected_block_indices", "crossing_block_indices", "halo_block_indices"):
            array = np.array(getattr(self, name), dtype=np.int32, copy=True, order="C")
            if array.ndim != 2 or array.shape[1:] != (3,):
                raise GraphAdapterError(f"{name} must have shape (n, 3).")
            array.setflags(write=False)
            object.__setattr__(self, name, array)
        if len(self.block_grid_shape) != 3 or min(int(v) for v in self.block_grid_shape) <= 0:
            raise GraphAdapterError("block_grid_shape must contain three positive integers.")
        object.__setattr__(self, "block_grid_shape", tuple(int(v) for v in self.block_grid_shape))
        if self.component_labels is not None:
            labels = np.array(self.component_labels, dtype=np.int32, copy=True, order="C")
            if labels.ndim != 1 or labels.size != self.selected_block_indices.shape[0]:
                raise GraphAdapterError("component_labels must align with selected blocks.")
            labels.setflags(write=False)
            object.__setattr__(self, "component_labels", labels)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def component_count(self) -> int | None:
        if self.component_labels is None:
            return None
        return 0 if self.component_labels.size == 0 else int(np.max(self.component_labels)) + 1

    def to_json_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result = {
            "schema_version": self.schema_version,
            "field_key": self.field_key,
            "hdr_details": self.hdr_details.to_json_dict(),
            "selected_block_count": int(self.selected_block_indices.shape[0]),
            "crossing_block_count": int(self.crossing_block_indices.shape[0]),
            "halo_block_count": int(self.halo_block_indices.shape[0]),
            "component_count": self.component_count,
            "block_grid_shape": list(self.block_grid_shape),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_arrays:
            result.update({
                "selected_block_indices": self.selected_block_indices.tolist(),
                "crossing_block_indices": self.crossing_block_indices.tolist(),
                "halo_block_indices": self.halo_block_indices.tolist(),
                "component_labels": None if self.component_labels is None else self.component_labels.tolist(),
            })
        return result


def select_hdr_details_many(
    field: _PackedFieldLike,
    fractions: Sequence[float],
    *,
    chunk_size: int | None = None,
    max_workspace_bytes: int | None = None,
) -> DensityHDRBatch:
    """Resolve several exact discrete HDR thresholds using one value sort.

    The sorted value copy is the only full-length temporary.  Reverse cumulative
    sums are constructed one bounded chunk at a time, so the routine never holds
    a second full-length cumulative vector.
    """

    requested = _fractions(fractions)
    budget, _model, _derived = resolve_density_resource_limits()
    default_chunk = max(1, min(DEFAULT_HDR_CHUNK_SIZE, budget.max_memory_bytes // 16))
    chunk = (
        default_chunk
        if chunk_size is None
        else min(default_chunk, _positive_int(chunk_size, name="chunk_size"))
    )
    byte_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    source = np.asarray(field.packed_values, dtype=np.float64)
    if source.ndim != 1 or source.size == 0 or np.any(source <= 0.0) or np.any(~np.isfinite(source)):
        raise GraphAdapterError("Packed HDR selection requires finite positive one-dimensional values.")
    required = int(source.nbytes + min(source.size, chunk) * np.dtype(np.float64).itemsize)
    if required > byte_limit:
        raise GraphComplexityError(
            f"HDR selection needs approximately {required} bytes, exceeding max_workspace_bytes={byte_limit}."
        )
    ordered = np.sort(source)  # ascending, one full-sized copy
    target_pairs = sorted(
        ((fraction * float(field.total_measure), fraction) for fraction in requested),
        key=lambda item: item[0],
    )
    thresholds: dict[float, float] = {}
    cumulative_before = 0.0
    target_position = 0
    peak_chunk_bytes = 0
    stop = int(ordered.size)
    while target_position < len(target_pairs) and stop > 0:
        start = max(0, stop - chunk)
        descending_chunk = ordered[start:stop][::-1]
        chunk_sum = float(np.sum(descending_chunk, dtype=np.float64)) * float(field.voxel_volume)
        upper = cumulative_before + chunk_sum
        if target_pairs[target_position][0] <= upper:
            cumulative = np.cumsum(descending_chunk, dtype=np.float64) * float(field.voxel_volume)
            peak_chunk_bytes = max(peak_chunk_bytes, int(cumulative.nbytes))
            while target_position < len(target_pairs) and target_pairs[target_position][0] <= upper:
                target, fraction = target_pairs[target_position]
                local = min(
                    int(np.searchsorted(cumulative, target - cumulative_before, side="left")),
                    cumulative.size - 1,
                )
                thresholds[fraction] = float(descending_chunk[local])
                target_position += 1
        cumulative_before = upper
        stop = start
    if target_position != len(target_pairs):
        raise GraphAdapterError("HDR target mass exceeds the stored field measure.")

    details_by_fraction: dict[float, SparseHDRDetails] = {}
    for fraction in requested:
        threshold = thresholds[fraction]
        left = int(np.searchsorted(ordered, threshold, side="left"))
        right = int(np.searchsorted(ordered, threshold, side="right"))
        selected_measure = float(np.sum(ordered[left:], dtype=np.float64)) * float(field.voxel_volume)
        details_by_fraction[fraction] = SparseHDRDetails(
            requested_mass_fraction=fraction,
            threshold=threshold,
            achieved_mass_fraction=selected_measure / float(field.total_measure),
            selected_node_count=int(ordered.size - left),
            threshold_tie_count=int(right - left),
            selected_measure=selected_measure,
            total_measure=float(field.total_measure),
        )
    return DensityHDRBatch(
        field_key=str(field.field_key),
        fractions=requested,
        details=tuple(details_by_fraction[value] for value in requested),
        value_count=int(source.size),
        sort_workspace_bytes=int(ordered.nbytes),
        peak_cumulative_chunk_bytes=peak_chunk_bytes,
        metadata={
            "voxel_volume": float(field.voxel_volume),
            "one_full_length_sort_copy": True,
            "full_length_cumulative_array_allocated": False,
            "chunk_size": chunk,
        },
    )


def _component_labels(indices: NDArray[np.int32], grid: tuple[int, int, int]) -> NDArray[np.int32]:
    if indices.shape[0] == 0:
        result = np.empty(0, dtype=np.int32)
        result.setflags(write=False)
        return result
    flat = np.ravel_multi_index((indices[:, 0], indices[:, 1], indices[:, 2]), grid, order="C")
    row_by_flat = {int(value): row for row, value in enumerate(flat)}
    labels = np.full(indices.shape[0], -1, dtype=np.int32)
    component = 0
    for start in range(indices.shape[0]):
        if labels[start] >= 0:
            continue
        labels[start] = component
        queue: deque[int] = deque([start])
        while queue:
            row = queue.popleft()
            current = indices[row].astype(np.int64)
            for axis in range(3):
                for delta in (-1, 1):
                    neighbor = current.copy()
                    neighbor[axis] = (neighbor[axis] + delta) % grid[axis]
                    neighbor_flat = int(np.ravel_multi_index(tuple(neighbor), grid, order="C"))
                    neighbor_row = row_by_flat.get(neighbor_flat)
                    if neighbor_row is not None and labels[neighbor_row] < 0:
                        labels[neighbor_row] = component
                        queue.append(neighbor_row)
        component += 1
    labels.setflags(write=False)
    return labels


def prepare_contour_support(
    field: _PackedFieldLike,
    details: SparseHDRDetails,
    *,
    compute_components: bool = False,
) -> DensityContourSupport:
    """Build conservative block support for one exact HDR contour level."""

    threshold = float(details.threshold)
    indices = np.asarray(field.active_block_indices, dtype=np.int32)
    minima = np.asarray(field.block_min_values, dtype=np.float64)
    maxima = np.asarray(field.block_max_values, dtype=np.float64)
    selected_mask = maxima >= threshold
    selected = indices[selected_mask]
    selected_set = {tuple(int(v) for v in row) for row in selected}
    grid = tuple(int(v) for v in field.block_grid_shape)
    crossing_rows: list[tuple[int, int, int]] = []
    for row, minimum, maximum in zip(indices, minima, maxima, strict=True):
        coordinate = tuple(int(v) for v in row)
        if maximum < threshold:
            continue
        crossing = minimum <= threshold <= maximum
        if not crossing:
            for axis in range(3):
                for delta in (-1, 1):
                    neighbor = list(coordinate)
                    neighbor[axis] = (neighbor[axis] + delta) % grid[axis]
                    if tuple(neighbor) not in selected_set:
                        crossing = True
                        break
                if crossing:
                    break
        if crossing:
            crossing_rows.append(coordinate)
    crossing = np.asarray(sorted(set(crossing_rows)), dtype=np.int32).reshape(-1, 3)
    halo_set: set[tuple[int, int, int]] = set()
    for row in crossing:
        coordinate = tuple(int(v) for v in row)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    halo_set.add(((coordinate[0] + dx) % grid[0], (coordinate[1] + dy) % grid[1], (coordinate[2] + dz) % grid[2]))
    halo = np.asarray(sorted(halo_set), dtype=np.int32).reshape(-1, 3)
    labels = _component_labels(selected, grid) if compute_components else None
    return DensityContourSupport(
        field_key=str(field.field_key),
        hdr_details=details,
        selected_block_indices=selected,
        crossing_block_indices=crossing,
        halo_block_indices=halo,
        component_labels=labels,
        block_grid_shape=grid,
        metadata={
            "support_kind": "conservative_block_extrema_with_periodic_boundary_detection",
            "scientific_field_modified": False,
            "node_level_contouring_deferred_to_ld9": True,
        },
    )


def prepare_contour_support_many(
    field: _PackedFieldLike,
    batch: DensityHDRBatch,
    *,
    compute_components: bool = False,
) -> tuple[DensityContourSupport, ...]:
    if batch.field_key != field.field_key:
        raise GraphAdapterError("HDR batch belongs to a different field.")
    return tuple(
        prepare_contour_support(field, detail, compute_components=compute_components)
        for detail in batch.details
    )
