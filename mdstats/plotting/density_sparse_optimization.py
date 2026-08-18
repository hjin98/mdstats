"""Exact sparse-density optimization and bounded stencil-support caching.

This module implements LD5 and the LD7 full-trajectory tractability corrections. Periodic cloud-in-cell assignment
continues to follow Hockney and Eastwood, *Computer Simulation Using Particles*
(1988). The vectorized accumulation order, bounded immutable cache, limit
revalidation, bounded block streaming, deterministic source-group batching, and integration with mdstats planning are project-specific.

The LD1-A implementation in :mod:`mdstats.plotting.density_sparse_reference`
remains the simple numerical oracle.
"""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_contracts import (
    FrozenJSONMapping,
    PeriodicWeightedSamples3D,
    freeze_json_mapping,
)
from .density_kernel import (
    MAX_STENCIL_CANDIDATE_CONTRIBUTIONS,
    PeriodicGaussianStencilSupport,
    build_periodic_gaussian_stencil_support,
)
from .density_sparse_reference import (
    SparseCICNodeMasses3D,
    SparseCanonicalDensityReference3D,
    estimate_periodic_cic_sparse_workspace_bytes,
)
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]

DENSITY_OPTIMIZATION_CACHE_INFO_SCHEMA = "mdstats.density-optimization-cache-info.v1"
DEFAULT_STENCIL_CACHE_MAX_ENTRIES = 16
DEFAULT_STENCIL_CACHE_MAX_BYTES = 256 * 1024 * 1024
DEFAULT_DENSE_REDUCTION_MAX_NODES = 4_194_304


def _positive_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be a positive integer.")
    result = int(value)
    if result <= 0:
        raise GraphStyleError(f"{name} must be positive.")
    return result


def _validated_shape(value: Any) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError("grid_shape must contain three entries.")
    return tuple(_positive_int(item, name="grid_shape entry") for item in value)  # type: ignore[return-value]


def _validated_cell(value: Any) -> FloatArray:
    cell = np.asarray(value, dtype=np.float64)
    if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
        raise GraphAdapterError("display_cell must be a finite 3x3 matrix.")
    if abs(float(np.linalg.det(cell))) <= 64.0 * np.finfo(np.float64).eps * max(
        1.0, float(np.linalg.norm(cell, ord=np.inf)) ** 3
    ):
        raise GraphAdapterError("display_cell must be nonsingular.")
    return np.ascontiguousarray(cell, dtype=np.float64)


def _float_bits(value: float) -> int:
    array = np.asarray([float(value)], dtype=np.float64)
    return int(array.view(np.uint64)[0])


def _support_key(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    kernel_tail_tolerance: float,
) -> tuple[Any, ...]:
    shape = _validated_shape(grid_shape)
    cell = _validated_cell(display_cell)
    return (
        shape,
        cell.tobytes(order="C"),
        _float_bits(float(gaussian_bandwidth)),
        _float_bits(float(kernel_tail_tolerance)),
    )


def _support_array_bytes(support: PeriodicGaussianStencilSupport) -> int:
    return int(
        support.display_cell.nbytes
        + support.active_flat_indices.nbytes
        + support.active_weights.nbytes
        + support.covariance.nbytes
    )


def _enforce_cached_support_limits(
    support: PeriodicGaussianStencilSupport,
    *,
    max_candidate_contributions: int,
    max_workspace_bytes: int,
) -> None:
    candidate_limit = _positive_int(
        max_candidate_contributions, name="max_candidate_contributions"
    )
    workspace_limit = _positive_int(max_workspace_bytes, name="max_workspace_bytes")
    candidate = int(support.metadata["candidate_contribution_count"])
    workspace = int(support.metadata["workspace_upper_bound_bytes"])
    if candidate > candidate_limit:
        raise GraphComplexityError(
            "Canonical Gaussian-stencil support requires "
            f"{candidate} candidate image contributions, exceeding "
            f"max_candidate_contributions={candidate_limit}."
        )
    if workspace > workspace_limit:
        raise GraphComplexityError(
            "Sparse Gaussian-stencil support requires at most "
            f"{workspace} bytes of package-owned workspace, exceeding "
            f"max_workspace_bytes={workspace_limit}."
        )


@dataclass(frozen=True, slots=True)
class DensityOptimizationCacheInfo:
    """Operational counters for the bounded immutable support cache."""

    hits: int
    misses: int
    insertions: int
    evictions: int
    current_entries: int
    retained_array_bytes: int
    max_entries: int
    max_array_bytes: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = FrozenJSONMapping()
    schema_version: str = DENSITY_OPTIMIZATION_CACHE_INFO_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_OPTIMIZATION_CACHE_INFO_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported cache-info schema {self.schema_version!r}."
            )
        for name in (
            "hits",
            "misses",
            "insertions",
            "evictions",
            "current_entries",
            "retained_array_bytes",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "max_entries", _positive_int(self.max_entries, name="max_entries"))
        object.__setattr__(self, "max_array_bytes", _positive_int(self.max_array_bytes, name="max_array_bytes"))
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "hits": self.hits,
            "misses": self.misses,
            "insertions": self.insertions,
            "evictions": self.evictions,
            "current_entries": self.current_entries,
            "retained_array_bytes": self.retained_array_bytes,
            "max_entries": self.max_entries,
            "max_array_bytes": self.max_array_bytes,
            "metadata": self.metadata.to_json_dict(),
        }


class _StencilSupportCache:
    def __init__(self, *, max_entries: int, max_array_bytes: int) -> None:
        self.max_entries = _positive_int(max_entries, name="max_entries")
        self.max_array_bytes = _positive_int(max_array_bytes, name="max_array_bytes")
        self._entries: OrderedDict[tuple[Any, ...], tuple[PeriodicGaussianStencilSupport, int]] = OrderedDict()
        self._array_bytes = 0
        self._hits = 0
        self._misses = 0
        self._insertions = 0
        self._evictions = 0
        self._lock = RLock()

    def configure(self, *, max_entries: int, max_array_bytes: int) -> None:
        entries = _positive_int(max_entries, name="max_entries")
        array_bytes = _positive_int(max_array_bytes, name="max_array_bytes")
        with self._lock:
            self.max_entries = entries
            self.max_array_bytes = array_bytes
            while self._entries and (
                len(self._entries) > self.max_entries
                or self._array_bytes > self.max_array_bytes
            ):
                _, (_, removed_size) = self._entries.popitem(last=False)
                self._array_bytes -= removed_size
                self._evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._array_bytes = 0
            self._hits = 0
            self._misses = 0
            self._insertions = 0
            self._evictions = 0

    def get(self, key: tuple[Any, ...]) -> PeriodicGaussianStencilSupport | None:
        with self._lock:
            item = self._entries.pop(key, None)
            if item is None:
                self._misses += 1
                return None
            self._entries[key] = item
            self._hits += 1
            return item[0]

    def insert(
        self,
        key: tuple[Any, ...],
        support: PeriodicGaussianStencilSupport,
    ) -> PeriodicGaussianStencilSupport:
        size = _support_array_bytes(support)
        with self._lock:
            existing = self._entries.pop(key, None)
            if existing is not None:
                self._entries[key] = existing
                return existing[0]
            if size > self.max_array_bytes:
                return support
            while self._entries and (
                len(self._entries) >= self.max_entries
                or self._array_bytes + size > self.max_array_bytes
            ):
                _, (_, removed_size) = self._entries.popitem(last=False)
                self._array_bytes -= removed_size
                self._evictions += 1
            self._entries[key] = (support, size)
            self._array_bytes += size
            self._insertions += 1
            return support

    def info(self) -> DensityOptimizationCacheInfo:
        with self._lock:
            return DensityOptimizationCacheInfo(
                hits=self._hits,
                misses=self._misses,
                insertions=self._insertions,
                evictions=self._evictions,
                current_entries=len(self._entries),
                retained_array_bytes=self._array_bytes,
                max_entries=self.max_entries,
                max_array_bytes=self.max_array_bytes,
                metadata={"cache_kind": "periodic_gaussian_stencil_support_lru"},
            )


_STENCIL_SUPPORT_CACHE = _StencilSupportCache(
    max_entries=DEFAULT_STENCIL_CACHE_MAX_ENTRIES,
    max_array_bytes=DEFAULT_STENCIL_CACHE_MAX_BYTES,
)


def clear_density_optimization_caches() -> None:
    """Release all process-local density optimization caches and reset counters."""

    _STENCIL_SUPPORT_CACHE.clear()


def density_optimization_cache_info() -> DensityOptimizationCacheInfo:
    """Return immutable operational cache counters."""

    return _STENCIL_SUPPORT_CACHE.info()


def get_periodic_gaussian_stencil_support(
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    *,
    kernel_tail_tolerance: float = 1.0e-8,
    max_candidate_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
    use_cache: bool = True,
    max_cache_entries: int | None = None,
    max_cache_bytes: int | None = None,
) -> tuple[PeriodicGaussianStencilSupport, bool]:
    """Return a certified support and whether it came from the process cache."""

    budget, _model, derived = resolve_density_resource_limits()
    candidate_default = derived["max_density_stencil_values"]
    candidate_limit = (
        candidate_default
        if max_candidate_contributions is None
        else min(candidate_default, _positive_int(max_candidate_contributions, name="max_candidate_contributions"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    cache_entry_default = max(4, 2 * budget.max_threads)
    cache_entries = (
        cache_entry_default
        if max_cache_entries is None
        else min(cache_entry_default, _positive_int(max_cache_entries, name="max_cache_entries"))
    )
    cache_bytes = (
        max(1, budget.max_memory_bytes // 20)
        if max_cache_bytes is None
        else min(_positive_int(max_cache_bytes, name="max_cache_bytes"), budget.max_memory_bytes)
    )
    _STENCIL_SUPPORT_CACHE.configure(
        max_entries=cache_entries, max_array_bytes=cache_bytes
    )
    key = _support_key(
        grid_shape, display_cell, gaussian_bandwidth, kernel_tail_tolerance
    )
    if use_cache:
        cached = _STENCIL_SUPPORT_CACHE.get(key)
        if cached is not None:
            _enforce_cached_support_limits(
                cached,
                max_candidate_contributions=candidate_limit,
                max_workspace_bytes=workspace_limit,
            )
            return cached, True
    support = build_periodic_gaussian_stencil_support(
        grid_shape,
        display_cell,
        gaussian_bandwidth,
        kernel_tail_tolerance=kernel_tail_tolerance,
        max_candidate_contributions=candidate_limit,
        max_workspace_bytes=workspace_limit,
    )
    if use_cache:
        support = _STENCIL_SUPPORT_CACHE.insert(key, support)
    return support, False


def _stable_group_sum(flat: IntArray, values: FloatArray) -> tuple[IntArray, FloatArray]:
    order = np.argsort(flat, kind="stable")
    sorted_flat = flat[order]
    sorted_values = values[order]
    starts = np.concatenate(
        (
            np.asarray([0], dtype=np.int64),
            np.flatnonzero(sorted_flat[1:] != sorted_flat[:-1]).astype(np.int64) + 1,
        )
    )
    unique = sorted_flat[starts].astype(np.int64, copy=False)
    reduced = np.add.reduceat(sorted_values, starts).astype(np.float64, copy=False)
    return unique, reduced




def estimate_periodic_cic_sparse_optimized_workspace_bytes(sample_count: int) -> int:
    """Conservative package-owned workspace bound for optimized CIC v2.

    PAR-DENS6 shortened array lifetimes before the stable global reduction.
    The remaining peak is bounded by the preallocated contribution vectors,
    per-offset temporaries, stable-sort order/copies, and reduced outputs.  A
    512-byte/sample envelope includes explicit safety headroom while excluding
    caller-owned input samples and retained output arrays.
    """

    count = _positive_int(sample_count, name="sample_count")
    return int(512 * count + 4096)


def aggregate_periodic_cic_sparse_optimized(
    samples: PeriodicWeightedSamples3D,
    grid_shape: tuple[int, int, int],
    *,
    max_cic_contributions: int | None = None,
    max_workspace_bytes: int | None = None,
) -> SparseCICNodeMasses3D:
    """Preallocate and stably reduce periodic CIC contributions."""

    if not isinstance(samples, PeriodicWeightedSamples3D):
        raise TypeError("samples must be PeriodicWeightedSamples3D.")
    shape = _validated_shape(grid_shape)
    budget, _model, derived = resolve_density_resource_limits()
    contribution_default = derived["max_density_kernel_pairs"]
    contribution_limit = (
        contribution_default
        if max_cic_contributions is None
        else min(contribution_default, _positive_int(max_cic_contributions, name="max_cic_contributions"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    sample_count = int(samples.fractional_positions.shape[0])
    contribution_upper = 8 * sample_count
    if contribution_upper > contribution_limit:
        raise GraphComplexityError(
            "Sparse CIC aggregation requires at most "
            f"{contribution_upper} contributions, exceeding "
            f"max_cic_contributions={contribution_limit}."
        )
    workspace_upper = estimate_periodic_cic_sparse_optimized_workspace_bytes(sample_count)
    if workspace_upper > workspace_limit:
        raise GraphComplexityError(
            "Sparse CIC aggregation requires at most "
            f"{workspace_upper} bytes of package-owned workspace, exceeding "
            f"max_workspace_bytes={workspace_limit}."
        )

    folded = samples.fractional_positions - np.floor(samples.fractional_positions)
    scale = np.asarray(shape, dtype=np.float64)
    scaled = folded * scale[None, :]
    base = np.floor(scaled).astype(np.int64)
    delta = scaled - base
    flat_all = np.empty(contribution_upper, dtype=np.int64)
    mass_all = np.empty(contribution_upper, dtype=np.float64)
    cursor = 0
    for ox in (0, 1):
        wx = (1.0 - delta[:, 0]) if ox == 0 else delta[:, 0]
        ix = (base[:, 0] + ox) % shape[0]
        for oy in (0, 1):
            wy = (1.0 - delta[:, 1]) if oy == 0 else delta[:, 1]
            iy = (base[:, 1] + oy) % shape[1]
            for oz in (0, 1):
                wz = (1.0 - delta[:, 2]) if oz == 0 else delta[:, 2]
                iz = (base[:, 2] + oz) % shape[2]
                contribution = samples.weights * wx * wy * wz
                mask = contribution > 0.0
                count = int(np.count_nonzero(mask))
                if count == 0:
                    continue
                stop = cursor + count
                flat_all[cursor:stop] = (
                    (ix[mask] * shape[1] + iy[mask]) * shape[2] + iz[mask]
                )
                mass_all[cursor:stop] = contribution[mask]
                cursor = stop
    if cursor == 0:
        raise GraphAdapterError("Positive weighted samples produced no CIC mass.")
    flat_all = flat_all[:cursor]
    mass_all = mass_all[:cursor]
    # PAR-DENS6 memory qualification: deposition geometry is dead before the
    # stable global reduction.  Drop those large sample temporaries now instead
    # of retaining them across argsort/sorted-copy allocation.  This is a
    # lifetime-only change; offset-major/sample-major reduction order is intact.
    del folded, scaled, base, delta, scale
    del wx, ix, wy, iy, wz, iz, contribution, mask
    unique_flat, reduced_mass = _stable_group_sum(flat_all, mass_all)
    positive = reduced_mass > 0.0
    unique_flat = unique_flat[positive]
    reduced_mass = reduced_mass[positive]
    deposited = float(np.sum(reduced_mass, dtype=np.float64))
    error = deposited - samples.total_measure
    tolerance = 5.0e-13 * max(1.0, samples.total_measure)
    if abs(error) > tolerance:
        raise GraphAdapterError(
            "Periodic CIC assignment failed measure conservation: "
            f"error={error:.17g}, tolerance={tolerance:.17g}."
        )
    return SparseCICNodeMasses3D(
        grid_shape=shape,
        flat_indices=unique_flat,
        node_masses=reduced_mass,
        total_measure=samples.total_measure,
        source_provenance=samples.source_provenance,
        metadata={
            "deposition": "periodic_trilinear_cloud_in_cell",
            "sample_count": sample_count,
            "positive_contribution_count": cursor,
            "contribution_upper_bound": contribution_upper,
            "occupied_node_count": int(unique_flat.size),
            "deposited_measure_before_smoothing": deposited,
            "deposition_measure_error": error,
            "deterministic_accumulation_order": "offset_major_then_sample_stable",
            "cic_implementation": "vectorized_preallocated_stable_reduce_v1",
            "workspace_upper_bound_bytes": workspace_upper,
        },
    )


def _stream_pair_slices(
    occupied: int,
    stencil_count: int,
    chunk_limit: int,
):
    """Yield offset-major/source-major pair batches bounded by chunk_limit."""

    if occupied <= chunk_limit:
        offsets_per_chunk = max(1, chunk_limit // max(1, occupied))
        for offset_start in range(0, stencil_count, offsets_per_chunk):
            yield offset_start, min(stencil_count, offset_start + offsets_per_chunk), 0, occupied
        return
    for offset in range(stencil_count):
        for source_start in range(0, occupied, chunk_limit):
            yield offset, offset + 1, source_start, min(occupied, source_start + chunk_limit)


def _target_block_coordinates(
    targets: IntArray,
    block_shape: tuple[int, int, int],
) -> tuple[IntArray, IntArray]:
    block = np.asarray(block_shape, dtype=np.int64)
    block_coordinates = targets // block[None, :]
    local = targets - block_coordinates * block[None, :]
    return block_coordinates, local


def _block_flat_indices(
    block_coordinates: IntArray,
    block_grid_shape: tuple[int, int, int],
) -> IntArray:
    return (
        (block_coordinates[:, 0] * block_grid_shape[1] + block_coordinates[:, 1])
        * block_grid_shape[2]
        + block_coordinates[:, 2]
    ).astype(np.int64, copy=False)


def _local_flat_indices(
    local_coordinates: IntArray,
    block_shape: tuple[int, int, int],
) -> IntArray:
    return (
        (local_coordinates[:, 0] * block_shape[1] + local_coordinates[:, 1])
        * block_shape[2]
        + local_coordinates[:, 2]
    ).astype(np.int64, copy=False)


def _global_flat_from_block_local(
    block_flat: int,
    local_flat: IntArray,
    *,
    grid_shape: tuple[int, int, int],
    block_shape: tuple[int, int, int],
    block_grid_shape: tuple[int, int, int],
) -> IntArray:
    bx, rem = divmod(int(block_flat), block_grid_shape[1] * block_grid_shape[2])
    by, bz = divmod(rem, block_grid_shape[2])
    lx, rem_local = np.divmod(local_flat, block_shape[1] * block_shape[2])
    ly, lz = np.divmod(rem_local, block_shape[2])
    gx = bx * block_shape[0] + lx
    gy = by * block_shape[1] + ly
    gz = bz * block_shape[2] + lz
    valid = (gx < grid_shape[0]) & (gy < grid_shape[1]) & (gz < grid_shape[2])
    gx = gx[valid]
    gy = gy[valid]
    gz = gz[valid]
    flat = ((gx * grid_shape[1] + gy) * grid_shape[2] + gz).astype(np.int64)
    return flat


def _discover_stream_blocks(
    source_coordinates: IntArray,
    offset_coordinates: IntArray,
    *,
    shape: tuple[int, int, int],
    block_shape: tuple[int, int, int],
    chunk_limit: int,
) -> tuple[IntArray, IntArray, int]:
    """Discover target blocks without sorting or materializing all pairs."""

    occupied = int(source_coordinates.shape[0])
    stencil_count = int(offset_coordinates.shape[0])
    block_grid_shape = tuple(
        (shape[i] + block_shape[i] - 1) // block_shape[i] for i in range(3)
    )
    block_count = int(np.prod(block_grid_shape, dtype=object))
    active_mask = np.zeros(block_count, dtype=np.bool_)
    shape_array = np.asarray(shape, dtype=np.int64)
    peak_chunk_pairs = 0
    for offset_start, offset_stop, source_start, source_stop in _stream_pair_slices(
        occupied, stencil_count, chunk_limit
    ):
        targets = np.mod(
            offset_coordinates[offset_start:offset_stop, None, :]
            + source_coordinates[None, source_start:source_stop, :],
            shape_array[None, None, :],
        ).reshape((-1, 3))
        peak_chunk_pairs = max(peak_chunk_pairs, int(targets.shape[0]))
        block_coordinates = targets // np.asarray(block_shape, dtype=np.int64)[None, :]
        active_mask[_block_flat_indices(block_coordinates, block_grid_shape)] = True
    active_block_ids = np.flatnonzero(active_mask).astype(np.int64, copy=False)
    lookup = np.full(block_count, -1, dtype=np.int64)
    lookup[active_block_ids] = np.arange(active_block_ids.size, dtype=np.int64)
    return active_block_ids, lookup, peak_chunk_pairs


def scatter_periodic_stencil_sparse_optimized(
    cic_masses: SparseCICNodeMasses3D,
    stencil: PeriodicGaussianStencilSupport,
    *,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    pair_chunk_size: int | None = None,
    block_shape: tuple[int, int, int] = (16, 16, 16),
    max_kernel_pairs: int | None = None,
    max_workspace_bytes: int | None = None,
    cache_hit: bool = False,
) -> SparseCanonicalDensityReference3D:
    """Stream canonical stencil pairs into bounded dense block accumulators.

    A first vectorized pass discovers the exact target-block set.  A second
    pass accumulates directly into a compact block array through a dense
    block-lattice lookup.  No sorting and no arrays proportional to the full
    kernel-pair count are required.
    """

    if not isinstance(cic_masses, SparseCICNodeMasses3D):
        raise TypeError("cic_masses must be SparseCICNodeMasses3D.")
    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    if cic_masses.grid_shape != stencil.grid_shape:
        raise GraphAdapterError("CIC masses and stencil must share grid_shape.")
    budget, _model, derived = resolve_density_resource_limits()
    chunk_default = max(1_024, min(262_144, budget.max_memory_bytes // 384))
    chunk_limit = (
        chunk_default
        if pair_chunk_size is None
        else min(chunk_default, _positive_int(pair_chunk_size, name="pair_chunk_size"))
    )
    pair_default = derived["max_density_kernel_pairs"]
    pair_limit = (
        pair_default
        if max_kernel_pairs is None
        else min(pair_default, _positive_int(max_kernel_pairs, name="max_kernel_pairs"))
    )
    workspace_limit = (
        budget.max_memory_bytes
        if max_workspace_bytes is None
        else min(_positive_int(max_workspace_bytes, name="max_workspace_bytes"), budget.max_memory_bytes)
    )
    block_shape = _validated_shape(block_shape)
    occupied = cic_masses.occupied_node_count
    stencil_count = stencil.stencil_offset_count
    pair_count = occupied * stencil_count
    if pair_count > pair_limit:
        raise GraphComplexityError(
            "Sparse canonical scatter requires "
            f"{pair_count} kernel pairs, exceeding max_kernel_pairs={pair_limit}."
        )

    shape = cic_masses.grid_shape
    block_grid_shape = tuple(
        (shape[i] + block_shape[i] - 1) // block_shape[i] for i in range(3)
    )
    block_volume = int(np.prod(block_shape, dtype=object))
    source_coordinates = np.column_stack(
        np.unravel_index(cic_masses.flat_indices, shape, order="C")
    ).astype(np.int64, copy=False)
    offset_coordinates = np.column_stack(
        np.unravel_index(stencil.active_flat_indices, shape, order="C")
    ).astype(np.int64, copy=False)
    active_block_ids, block_lookup, peak_chunk_pairs = _discover_stream_blocks(
        source_coordinates,
        offset_coordinates,
        shape=shape,
        block_shape=block_shape,
        chunk_limit=chunk_limit,
    )
    fixed_bytes = int(
        source_coordinates.nbytes
        + offset_coordinates.nbytes
        + active_block_ids.nbytes
        + block_lookup.nbytes
        + 4096
    )
    block_bytes = int(active_block_ids.size * block_volume * 8)
    chunk_bytes = int(88 * peak_chunk_pairs)
    block_slot_count = int(active_block_ids.size * block_volume)
    use_block_bincount = (
        pair_count >= 20_000_000 and block_slot_count <= 4_194_304
    )
    reduction_temp_bytes = (8 * block_slot_count) if use_block_bincount else 0
    if fixed_bytes + block_bytes + chunk_bytes + reduction_temp_bytes > workspace_limit:
        raise GraphComplexityError(
            "Streaming sparse scatter requires at most "
            f"{fixed_bytes + block_bytes + chunk_bytes + reduction_temp_bytes} bytes for "
            f"{active_block_ids.size} target blocks and a {peak_chunk_pairs}-pair "
            f"chunk, exceeding max_workspace_bytes={workspace_limit}."
        )
    block_values = np.zeros(
        (active_block_ids.size, block_volume), dtype=np.float64
    )
    flat_block_values = block_values.reshape(-1)
    shape_array = np.asarray(shape, dtype=np.int64)
    processed_pairs = 0
    for offset_start, offset_stop, source_start, source_stop in _stream_pair_slices(
        occupied, stencil_count, chunk_limit
    ):
        targets = np.mod(
            offset_coordinates[offset_start:offset_stop, None, :]
            + source_coordinates[None, source_start:source_stop, :],
            shape_array[None, None, :],
        ).reshape((-1, 3))
        values = (
            stencil.active_weights[offset_start:offset_stop, None]
            * cic_masses.node_masses[None, source_start:source_stop]
        ).reshape(-1)
        processed_pairs += int(values.size)
        block_coordinates, local_coordinates = _target_block_coordinates(
            targets, block_shape
        )
        block_flat = _block_flat_indices(block_coordinates, block_grid_shape)
        local_flat = _local_flat_indices(local_coordinates, block_shape)
        storage_block = block_lookup[block_flat]
        if np.any(storage_block < 0):
            raise AssertionError("Target block was absent from streaming discovery.")
        combined = storage_block * block_volume + local_flat
        if use_block_bincount:
            flat_block_values += np.bincount(
                combined,
                weights=values,
                minlength=block_slot_count,
            )
        else:
            np.add.at(flat_block_values, combined, values)
    if processed_pairs != pair_count:
        raise AssertionError("Internal streaming sparse scatter pair-count mismatch.")

    flat_parts: list[IntArray] = []
    mass_parts: list[FloatArray] = []
    for storage_index, block_id in enumerate(active_block_ids):
        values = block_values[storage_index]
        local_active = np.flatnonzero(values > 0.0).astype(np.int64, copy=False)
        if local_active.size == 0:
            continue
        global_flat = _global_flat_from_block_local(
            int(block_id),
            local_active,
            grid_shape=shape,
            block_shape=block_shape,
            block_grid_shape=block_grid_shape,
        )
        if global_flat.size != local_active.size:
            raise AssertionError("Active values escaped a partial terminal block mask.")
        flat_parts.append(global_flat)
        mass_parts.append(values[local_active])
    if not flat_parts:
        raise GraphAdapterError("Sparse canonical scatter produced zero measure.")
    active_flat = np.concatenate(flat_parts)
    node_masses = np.concatenate(mass_parts)
    order = np.argsort(active_flat, kind="stable")
    active_flat = active_flat[order]
    node_masses = node_masses[order]
    raw_measure = float(np.sum(node_masses, dtype=np.float64))
    if not np.isfinite(raw_measure) or raw_measure <= 0.0:
        raise GraphAdapterError("Sparse canonical scatter produced zero measure.")
    normalization_factor = cic_masses.total_measure / raw_measure
    node_masses *= normalization_factor
    correction_index = _apply_total_mass_correction(
        node_masses, total_measure=cic_masses.total_measure
    )
    voxel_volume = abs(float(np.linalg.det(stencil.display_cell))) / float(
        np.prod(shape, dtype=object)
    )
    active_values = node_masses / voxel_volume
    final_measure = float(np.sum(active_values, dtype=np.float64)) * voxel_volume
    scatter_workspace_upper = int(
        fixed_bytes
        + block_bytes
        + chunk_bytes
        + reduction_temp_bytes
        + active_flat.nbytes
        + node_masses.nbytes
    )
    return SparseCanonicalDensityReference3D(
        field_key=field_key,
        label=label,
        physical_units=physical_units,
        logical_grid_shape=shape,
        active_flat_indices=active_flat,
        active_values=active_values,
        display_cell=stencil.display_cell,
        total_measure=cic_masses.total_measure,
        gaussian_bandwidth=stencil.gaussian_bandwidth,
        broadening_metric=broadening_metric,
        source_provenance=cic_masses.source_provenance,
        metadata={
            "reference_path": "ld7_streaming_block_sparse_nodes",
            "production_backend": True,
            "deposition_schema": cic_masses.schema_version,
            "stencil_schema": stencil.schema_version,
            "occupied_cic_node_count": occupied,
            "stencil_offset_count": stencil_count,
            "kernel_pair_count": pair_count,
            "active_node_count": int(active_flat.size),
            "raw_measure_before_final_normalization": raw_measure,
            "final_normalization_factor": float(normalization_factor),
            "final_measure": final_measure,
            "deterministic_accumulation_order": "stencil_major_then_source_stable",
            "scatter_implementation": "two_pass_block_lookup_streaming_v1",
            "reduction_implementation": (
                "bounded_block_bincount_v1"
                if use_block_bincount
                else "block_lookup_add_at_v1"
            ),
            "block_chunk_reduction": (
                "bounded_block_bincount_v1"
                if use_block_bincount
                else "block_lookup_add_at_v1"
            ),
            "pair_chunk_size": chunk_limit,
            "peak_chunk_pair_count": peak_chunk_pairs,
            "stream_block_shape": block_shape,
            "stream_active_block_count": int(active_block_ids.size),
            "stencil_cache_hit_for_realization": bool(cache_hit),
            "scatter_workspace_upper_bound_bytes": scatter_workspace_upper,
            **stencil.metadata_dict(),
        },
    )

def _apply_total_mass_correction(
    node_masses: np.ndarray,
    *,
    total_measure: float,
) -> int:
    """Apply a final floating residual to the largest positive mass.

    Sparse indices are sorted geometrically, so the first entry can be an
    arbitrarily small Gaussian-tail value.  Applying a negative roundoff
    residual there can make an otherwise valid field nonpositive.  The largest
    node provides the maximal positivity margin while preserving deterministic
    normalization.
    """

    if node_masses.ndim != 1 or node_masses.size == 0:
        raise GraphAdapterError("node_masses must be a nonempty one-dimensional array.")
    correction_index = int(np.argmax(node_masses))
    correction = float(total_measure) - float(
        np.sum(node_masses, dtype=np.float64)
    )
    corrected_mass = float(node_masses[correction_index]) + correction
    if corrected_mass <= 0.0 or not np.isfinite(corrected_mass):
        raise GraphAdapterError(
            "Sparse-density normalization produced a nonpositive correction node."
        )
    node_masses[correction_index] = corrected_mass
    return correction_index


def merge_sparse_canonical_density_fields(
    fields: tuple[SparseCanonicalDensityReference3D, ...],
    *,
    source_provenance: Any,
    group_count: int,
    group_batch_size: int,
) -> SparseCanonicalDensityReference3D:
    """Merge deterministic linear sparse-density batches on one grid."""

    if not fields:
        raise GraphAdapterError("At least one sparse density batch is required.")
    first = fields[0]
    for field in fields[1:]:
        if (
            field.logical_grid_shape != first.logical_grid_shape
            or field.physical_units != first.physical_units
            or field.broadening_metric != first.broadening_metric
            or field.gaussian_bandwidth != first.gaussian_bandwidth
            or not np.array_equal(field.display_cell, first.display_cell)
        ):
            raise GraphAdapterError(
                "Sparse density batches must share grid, cell, units, and kernel."
            )
    shape = first.logical_grid_shape
    voxel_volume = abs(float(np.linalg.det(first.display_cell))) / float(
        np.prod(shape, dtype=object)
    )
    all_indices = np.concatenate([field.active_flat_indices for field in fields])
    all_masses = np.concatenate(
        [field.active_values * voxel_volume for field in fields]
    )
    active_flat, node_masses = _stable_group_sum(all_indices, all_masses)
    positive = node_masses > 0.0
    active_flat = active_flat[positive]
    node_masses = node_masses[positive]
    total_measure = float(sum(field.total_measure for field in fields))
    raw_measure = float(np.sum(node_masses, dtype=np.float64))
    if raw_measure <= 0.0 or not np.isfinite(raw_measure):
        raise GraphAdapterError("Merged sparse density has zero measure.")
    normalization = total_measure / raw_measure
    node_masses *= normalization
    correction_index = _apply_total_mass_correction(
        node_masses, total_measure=total_measure
    )
    active_values = node_masses / voxel_volume
    metadata = dict(first.metadata)
    metadata.update(
        {
            "reference_path": "ld7_group_batched_sparse_nodes",
            "scatter_implementation": "group_batched_two_pass_block_lookup_v1",
            "group_batch_count": len(fields),
            "source_group_count": int(group_count),
            "sparse_group_batch_size": int(group_batch_size),
            "kernel_pair_count": int(
                sum(int(field.metadata.get("kernel_pair_count", 0)) for field in fields)
            ),
            "active_node_count": int(active_flat.size),
            "raw_measure_before_final_normalization": raw_measure,
            "final_normalization_factor": normalization,
            "final_mass_correction_index": correction_index,
            "final_measure": total_measure,
            "batch_merge_order": "ascending_group_id_then_stable_node_index",
            "scatter_workspace_peak_bytes": int(
                max(
                    int(field.metadata.get("scatter_workspace_upper_bound_bytes", 0))
                    for field in fields
                )
            ),
        }
    )
    return SparseCanonicalDensityReference3D(
        field_key=first.field_key,
        label=first.label,
        physical_units=first.physical_units,
        logical_grid_shape=shape,
        active_flat_indices=active_flat,
        active_values=active_values,
        display_cell=first.display_cell,
        total_measure=total_measure,
        gaussian_bandwidth=first.gaussian_bandwidth,
        broadening_metric=first.broadening_metric,
        source_provenance=source_provenance,
        metadata=metadata,
    )


def prepare_sparse_canonical_density_optimized(
    samples: PeriodicWeightedSamples3D,
    *,
    grid_shape: tuple[int, int, int],
    display_cell: FloatArray,
    gaussian_bandwidth: float,
    field_key: str,
    label: str,
    physical_units: str,
    broadening_metric: str,
    kernel_tail_tolerance: float = 1.0e-8,
    pair_chunk_size: int | None = None,
    block_shape: tuple[int, int, int] = (16, 16, 16),
    group_batch_size: int = 8,
    cache_stencil_supports: bool = True,
    max_cic_contributions: int | None = None,
    max_stencil_candidate_contributions: int | None = None,
    max_kernel_pairs: int | None = None,
    max_workspace_bytes: int | None = None,
) -> SparseCanonicalDensityReference3D:
    """Prepare the optimized sparse field with exact group batching."""

    support, cache_hit = get_periodic_gaussian_stencil_support(
        grid_shape,
        display_cell,
        gaussian_bandwidth,
        kernel_tail_tolerance=kernel_tail_tolerance,
        max_candidate_contributions=max_stencil_candidate_contributions,
        max_workspace_bytes=max_workspace_bytes,
        use_cache=cache_stencil_supports,
    )
    groups = samples.sample_group_ids
    batch_size = _positive_int(group_batch_size, name="group_batch_size")
    group_values = (
        np.empty(0, dtype=np.int64)
        if groups is None
        else np.unique(groups).astype(np.int64, copy=False)
    )

    cumulative_pairs = 0

    def prepare_one(batch_samples: PeriodicWeightedSamples3D, *, hit: bool):
        nonlocal cumulative_pairs
        cic = aggregate_periodic_cic_sparse_optimized(
            batch_samples,
            grid_shape,
            max_cic_contributions=max_cic_contributions,
            max_workspace_bytes=max_workspace_bytes,
        )
        batch_pairs = cic.occupied_node_count * support.stencil_offset_count
        cumulative_pairs += batch_pairs
        if max_kernel_pairs is not None and cumulative_pairs > max_kernel_pairs:
            raise GraphComplexityError(
                "Group-batched sparse canonical scatter requires "
                f"{cumulative_pairs} cumulative kernel pairs, exceeding "
                f"max_kernel_pairs={max_kernel_pairs}."
            )
        return scatter_periodic_stencil_sparse_optimized(
            cic,
            support,
            field_key=field_key,
            label=label,
            physical_units=physical_units,
            broadening_metric=broadening_metric,
            pair_chunk_size=pair_chunk_size,
            block_shape=block_shape,
            max_kernel_pairs=max_kernel_pairs,
            max_workspace_bytes=max_workspace_bytes,
            cache_hit=hit,
        )

    if group_values.size <= batch_size:
        return prepare_one(samples, hit=cache_hit)

    fields: list[SparseCanonicalDensityReference3D] = []
    for start_index in range(0, group_values.size, batch_size):
        selected_groups = group_values[start_index : start_index + batch_size]
        mask = np.isin(groups, selected_groups, assume_unique=False)
        batch_weights = samples.weights[mask]
        batch_total = float(np.sum(batch_weights, dtype=np.float64))
        batch_samples = PeriodicWeightedSamples3D(
            fractional_positions=samples.fractional_positions[mask],
            weights=batch_weights,
            sample_group_ids=groups[mask],
            source_provenance=samples.source_provenance,
            total_measure=batch_total,
            measure_kind=samples.measure_kind,
            measure_units=samples.measure_units,
            metadata={
                **samples.metadata.to_json_dict(),
                "group_batch_start": int(start_index),
                "group_batch_stop": int(
                    min(group_values.size, start_index + batch_size)
                ),
            },
        )
        fields.append(prepare_one(batch_samples, hit=cache_hit or bool(fields)))
    return merge_sparse_canonical_density_fields(
        tuple(fields),
        source_provenance=samples.source_provenance,
        group_count=int(group_values.size),
        group_batch_size=batch_size,
    )


def plan_group_batched_sparse_targets_optimized(
    samples: PeriodicWeightedSamples3D,
    global_cic: SparseCICNodeMasses3D,
    stencil: PeriodicGaussianStencilSupport,
    *,
    pair_chunk_size: int | None = None,
    block_shape: tuple[int, int, int] = (16, 16, 16),
    group_batch_size: int = 8,
    max_cic_contributions: int | None = None,
    max_kernel_pairs: int | None = None,
    max_planning_bytes: int | None = None,
) -> tuple[IntArray, int, FrozenJSONMapping]:
    """Plan exact sparse targets through deterministic source-group batches.

    The union is scientifically identical to planning all source groups at once,
    while the peak pair-generation workspace is bounded by one group batch.
    The returned pair count is the exact cumulative work of the batched
    realization rather than the monolithic combined-CIC count.
    """

    groups = samples.sample_group_ids
    batch_size = _positive_int(group_batch_size, name="group_batch_size")
    if groups is None:
        targets = plan_sparse_target_nodes_optimized(
            global_cic,
            stencil,
            pair_chunk_size=pair_chunk_size,
            block_shape=block_shape,
            max_kernel_pairs=max_kernel_pairs,
            max_planning_bytes=max_planning_bytes,
        )
        pairs = global_cic.occupied_node_count * stencil.stencil_offset_count
        return targets, pairs, freeze_json_mapping({
            "group_batch_count": 1,
            "source_group_count": 0,
            "peak_batch_kernel_pair_count": pairs,
            "planning_mode": "monolithic_streaming_v1",
        })
    group_values = np.unique(groups).astype(np.int64, copy=False)
    if group_values.size <= batch_size:
        targets = plan_sparse_target_nodes_optimized(
            global_cic,
            stencil,
            pair_chunk_size=pair_chunk_size,
            block_shape=block_shape,
            max_kernel_pairs=max_kernel_pairs,
            max_planning_bytes=max_planning_bytes,
        )
        pairs = global_cic.occupied_node_count * stencil.stencil_offset_count
        return targets, pairs, freeze_json_mapping({
            "group_batch_count": 1,
            "source_group_count": int(group_values.size),
            "peak_batch_kernel_pair_count": pairs,
            "planning_mode": "monolithic_streaming_v1",
        })

    target_parts: list[IntArray] = []
    cumulative_pairs = 0
    peak_pairs = 0
    batch_count = 0
    for start_index in range(0, group_values.size, batch_size):
        selected = group_values[start_index : start_index + batch_size]
        mask = np.isin(groups, selected, assume_unique=False)
        batch_weights = samples.weights[mask]
        batch_samples = PeriodicWeightedSamples3D(
            fractional_positions=samples.fractional_positions[mask],
            weights=batch_weights,
            sample_group_ids=groups[mask],
            source_provenance=samples.source_provenance,
            total_measure=float(np.sum(batch_weights, dtype=np.float64)),
            measure_kind=samples.measure_kind,
            measure_units=samples.measure_units,
            metadata=samples.metadata,
        )
        batch_cic = aggregate_periodic_cic_sparse_optimized(
            batch_samples,
            global_cic.grid_shape,
            max_cic_contributions=max_cic_contributions,
            max_workspace_bytes=max_planning_bytes,
        )
        batch_pairs = batch_cic.occupied_node_count * stencil.stencil_offset_count
        cumulative_pairs += batch_pairs
        peak_pairs = max(peak_pairs, batch_pairs)
        if cumulative_pairs > max_kernel_pairs:
            raise GraphComplexityError(
                "Group-batched sparse planning requires "
                f"{cumulative_pairs} cumulative kernel pairs, exceeding "
                f"max_kernel_pairs={max_kernel_pairs}."
            )
        target_parts.append(
            plan_sparse_target_nodes_optimized(
                batch_cic,
                stencil,
                pair_chunk_size=pair_chunk_size,
                block_shape=block_shape,
                max_kernel_pairs=max_kernel_pairs,
                max_planning_bytes=max_planning_bytes,
            )
        )
        batch_count += 1
    if not target_parts:
        targets = np.empty(0, dtype=np.int64)
    else:
        targets = np.unique(np.concatenate(target_parts)).astype(np.int64, copy=False)
    targets.setflags(write=False)
    return targets, cumulative_pairs, freeze_json_mapping({
        "group_batch_count": batch_count,
        "source_group_count": int(group_values.size),
        "peak_batch_kernel_pair_count": peak_pairs,
        "planning_mode": "group_batched_streaming_union_v1",
        "sparse_group_batch_size": batch_size,
    })

def plan_sparse_target_nodes_optimized(
    cic_masses: SparseCICNodeMasses3D,
    stencil: PeriodicGaussianStencilSupport,
    *,
    pair_chunk_size: int | None = None,
    block_shape: tuple[int, int, int] = (16, 16, 16),
    max_kernel_pairs: int | None = None,
    max_planning_bytes: int | None = None,
) -> IntArray:
    """Return exact target nodes with bounded two-pass block streaming."""

    if cic_masses.grid_shape != stencil.grid_shape:
        raise GraphAdapterError("CIC masses and stencil must share grid_shape.")
    budget, _model, derived = resolve_density_resource_limits()
    chunk_default = max(1_024, min(262_144, budget.max_memory_bytes // 384))
    chunk_limit = (
        chunk_default
        if pair_chunk_size is None
        else min(chunk_default, _positive_int(pair_chunk_size, name="pair_chunk_size"))
    )
    pair_default = derived["max_density_kernel_pairs"]
    pair_limit = (
        pair_default
        if max_kernel_pairs is None
        else min(pair_default, _positive_int(max_kernel_pairs, name="max_kernel_pairs"))
    )
    planning_limit = (
        budget.max_memory_bytes
        if max_planning_bytes is None
        else min(_positive_int(max_planning_bytes, name="max_planning_bytes"), budget.max_memory_bytes)
    )
    block_shape = _validated_shape(block_shape)
    occupied = cic_masses.occupied_node_count
    stencil_count = stencil.stencil_offset_count
    pair_count = occupied * stencil_count
    if pair_count > pair_limit:
        raise GraphComplexityError(
            f"Sparse planning requires {pair_count} kernel pairs, exceeding "
            f"max_kernel_pairs={pair_limit}."
        )
    shape = cic_masses.grid_shape
    block_grid_shape = tuple(
        (shape[i] + block_shape[i] - 1) // block_shape[i] for i in range(3)
    )
    block_volume = int(np.prod(block_shape, dtype=object))
    sources = np.column_stack(
        np.unravel_index(cic_masses.flat_indices, shape, order="C")
    ).astype(np.int64, copy=False)
    offsets = np.column_stack(
        np.unravel_index(stencil.active_flat_indices, shape, order="C")
    ).astype(np.int64, copy=False)
    active_block_ids, block_lookup, peak_chunk_pairs = _discover_stream_blocks(
        sources,
        offsets,
        shape=shape,
        block_shape=block_shape,
        chunk_limit=chunk_limit,
    )
    fixed_bytes = int(
        sources.nbytes
        + offsets.nbytes
        + active_block_ids.nbytes
        + block_lookup.nbytes
        + 4096
    )
    mask_bytes = int(active_block_ids.size * block_volume)
    chunk_bytes = int(72 * peak_chunk_pairs)
    if fixed_bytes + mask_bytes + chunk_bytes > planning_limit:
        raise GraphComplexityError(
            "Streaming sparse target planning requires at most "
            f"{fixed_bytes + mask_bytes + chunk_bytes} bytes for "
            f"{active_block_ids.size} target block masks, exceeding "
            f"max_planning_bytes={planning_limit}."
        )
    block_masks = np.zeros(
        (active_block_ids.size, block_volume), dtype=np.bool_
    )
    flat_masks = block_masks.reshape(-1)
    shape_array = np.asarray(shape, dtype=np.int64)
    processed_pairs = 0
    for offset_start, offset_stop, source_start, source_stop in _stream_pair_slices(
        occupied, stencil_count, chunk_limit
    ):
        targets = np.mod(
            offsets[offset_start:offset_stop, None, :]
            + sources[None, source_start:source_stop, :],
            shape_array[None, None, :],
        ).reshape((-1, 3))
        processed_pairs += int(targets.shape[0])
        block_coordinates, local_coordinates = _target_block_coordinates(
            targets, block_shape
        )
        block_flat = _block_flat_indices(block_coordinates, block_grid_shape)
        local_flat = _local_flat_indices(local_coordinates, block_shape)
        storage_block = block_lookup[block_flat]
        if np.any(storage_block < 0):
            raise AssertionError("Target block was absent from streaming discovery.")
        flat_masks[storage_block * block_volume + local_flat] = True
    if processed_pairs != pair_count:
        raise AssertionError("Internal streaming target-plan pair-count mismatch.")
    parts: list[IntArray] = []
    for storage_index, block_id in enumerate(active_block_ids):
        local_active = np.flatnonzero(block_masks[storage_index]).astype(
            np.int64, copy=False
        )
        if local_active.size:
            parts.append(
                _global_flat_from_block_local(
                    int(block_id),
                    local_active,
                    grid_shape=shape,
                    block_shape=block_shape,
                    block_grid_shape=block_grid_shape,
                )
            )
    if not parts:
        active = np.empty(0, dtype=np.int64)
    else:
        active = np.concatenate(parts)
        active.sort(kind="stable")
    active.setflags(write=False)
    return active

