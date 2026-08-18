"""Packed CIC sources and exact finite-support bitset atlases for LD8-S1.

The scientific estimator is unchanged: periodic cloud-in-cell source masses are
combined with the exact canonical finite Gaussian stencil.  This module changes
only source storage and support planning.  It constructs the exact modular
Minkowski sum

    A = S (+) K_epsilon

with packed block bitsets, bounded local shifts, and explicit terminal-block
routing.  No array proportional to the complete source-node by stencil-offset
pair count is allocated.

Cloud-in-cell assignment itself follows Hockney and Eastwood, *Computer
Simulation Using Particles* (1988).  The packed periodic bitset atlas and its
terminal routing are project-specific mdstats designs.
"""

from __future__ import annotations

import hashlib
import time
from concurrent.futures import ThreadPoolExecutor
from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
from scipy.fft import next_fast_len, set_workers
from scipy.signal import fftconvolve
from numpy.typing import NDArray

from .density_block_routing import (
    PeriodicKernelBlockRouting,
    bitset_int_to_words,
    bitset_popcount,
    bitset_popcounts,
    bitset_words_to_int,
    block_grid_shape,
    local_node_count,
    local_word_count,
    pack_local_indices,
    stencil_content_identity,
    unpack_local_bitset,
)
from .density_contracts import (
    DensitySourceProvenance,
    FrozenJSONMapping,
    freeze_json_mapping,
)
from .density_kernel import PeriodicGaussianStencilSupport
from .density_scene_planning import (
    DensitySupportAtlasPlan,
    DensitySupportPlanningLimits,
    plan_density_support_atlas,
)
from .density_sparse_reference import SparseCICNodeMasses3D
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits
from .density_scheduler import current_density_worker_count, current_density_worker_lease
from .density_autotune import autotuned_fft_worker_count, autotuned_group_size_multiplier
from .density_gpu import estimate_fft_cpu_seconds, try_gpu_linear_fft_convolution
from ..progress import ProgressEmitter, ProgressPortLike, resolve_progress_port

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]
UInt64Array = NDArray[np.uint64]

PERIODIC_PACKED_CIC_SOURCE_SCHEMA = "mdstats.periodic-packed-cic-source-field.v1"
DENSITY_SUPPORT_ATLAS_SCHEMA = "mdstats.density-support-atlas.v1"
DENSITY_SUPPORT_EQUIVALENCE_SCHEMA = "mdstats.density-support-equivalence-report.v1"

DEFAULT_MAX_PACKED_SOURCE_BLOCKS = 2_000_000
DEFAULT_MAX_PACKED_SOURCE_NODES = 20_000_000
DEFAULT_MAX_PACKED_SOURCE_BYTES = 1_000_000_000
DEFAULT_MAX_EXPLICIT_SUPPORT_PAIRS = 20_000_000
DEFAULT_FFT_DILATION_STENCIL_THRESHOLD = 1_024

SupportDilationBackend = Literal["auto", "bitset", "fft"]


def _positive_int(value: Any, *, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise GraphStyleError(f"{name} must be an integer >= {minimum}.")
    result = int(value)
    if result < minimum:
        raise GraphStyleError(f"{name} must be >= {minimum}.")
    return result


def _shape3(value: Any, *, name: str) -> tuple[int, int, int]:
    if len(value) != 3:
        raise GraphAdapterError(f"{name} must contain three entries.")
    return tuple(_positive_int(item, name=f"{name} entry") for item in value)  # type: ignore[return-value]


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


def _flat_block_indices(
    block_indices: NDArray[np.integer], block_grid: tuple[int, int, int]
) -> IntArray:
    if block_indices.ndim != 2 or block_indices.shape[1:] != (3,):
        raise GraphAdapterError("block_indices must have shape (n, 3).")
    if block_indices.shape[0] == 0:
        result = np.asarray([], dtype=np.int64)
    else:
        result = np.ravel_multi_index(
            (
                block_indices[:, 0],
                block_indices[:, 1],
                block_indices[:, 2],
            ),
            block_grid,
            order="C",
        ).astype(np.int64, copy=False)
    result = np.array(result, dtype=np.int64, copy=True, order="C")
    result.setflags(write=False)
    return result


def _popcount_rows(bitsets: UInt64Array) -> IntArray:
    return bitset_popcounts(bitsets)


def _validate_offsets(offsets: Any, expected_values: int, *, name: str) -> IntArray:
    array = _readonly_array(offsets, np.int64, ndim=1, name=name)
    if array.shape != (expected_values + 1,):
        raise GraphAdapterError(f"{name} must have shape ({expected_values + 1},).")
    if int(array[0]) != 0 or np.any(array[1:] < array[:-1]):
        raise GraphAdapterError(f"{name} must be a nondecreasing CSR offset array.")
    return array


@dataclass(frozen=True, slots=True)
class PeriodicPackedCICSourceField3D:
    """One field-specific globally aggregated periodic CIC source."""

    logical_grid_shape: tuple[int, int, int]
    storage_block_shape: tuple[int, int, int]
    source_block_indices: NDArray[np.int32]
    occupancy_bitsets: UInt64Array
    block_value_offsets: IntArray
    packed_values: FloatArray
    total_measure: float
    source_provenance: DensitySourceProvenance
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = PERIODIC_PACKED_CIC_SOURCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERIODIC_PACKED_CIC_SOURCE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported packed-CIC-source schema {self.schema_version!r}."
            )
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        block = _shape3(self.storage_block_shape, name="storage_block_shape")
        grid = block_grid_shape(logical, block)
        indices = _readonly_array(
            self.source_block_indices,
            np.int32,
            ndim=2,
            name="source_block_indices",
        )
        if indices.shape[1:] != (3,) or indices.shape[0] == 0:
            raise GraphAdapterError("source_block_indices must have shape (n, 3), n > 0.")
        if np.any(indices < 0) or np.any(indices >= np.asarray(grid, dtype=np.int32)[None, :]):
            raise GraphAdapterError("source_block_indices lie outside the block grid.")
        flats = _flat_block_indices(indices, grid)
        if flats.size > 1 and np.any(flats[1:] <= flats[:-1]):
            raise GraphAdapterError("source_block_indices must be unique and C-order sorted.")
        bitsets = _readonly_array(
            self.occupancy_bitsets,
            np.uint64,
            ndim=2,
            name="occupancy_bitsets",
        )
        words = local_word_count(block)
        if bitsets.shape != (indices.shape[0], words):
            raise GraphAdapterError(
                f"occupancy_bitsets must have shape ({indices.shape[0]}, {words})."
            )
        counts = _popcount_rows(bitsets)
        if np.any(counts <= 0):
            raise GraphAdapterError("Every source block must contain at least one occupied node.")
        offsets = _validate_offsets(
            self.block_value_offsets,
            int(indices.shape[0]),
            name="block_value_offsets",
        )
        if not np.array_equal(np.diff(offsets), counts):
            raise GraphAdapterError("block_value_offsets disagree with occupancy bit counts.")
        values = _readonly_array(
            self.packed_values, np.float64, ndim=1, name="packed_values"
        )
        if int(offsets[-1]) != values.size:
            raise GraphAdapterError("block_value_offsets do not span packed_values.")
        if np.any(values <= 0.0):
            raise GraphAdapterError("packed_values must be strictly positive.")
        total = float(self.total_measure)
        if not np.isfinite(total) or total <= 0.0:
            raise GraphAdapterError("total_measure must be finite and positive.")
        deposited = float(np.sum(values, dtype=np.float64))
        if abs(deposited - total) > 5.0e-13 * max(1.0, total):
            raise GraphAdapterError(
                "Packed CIC source does not conserve total_measure: "
                f"deposited={deposited:.17g}, target={total:.17g}."
            )
        if not isinstance(self.source_provenance, DensitySourceProvenance):
            raise TypeError("source_provenance must be DensitySourceProvenance.")
        # Terminal validity is checked against global logical coordinates.
        for row, block_index in enumerate(indices):
            local_indices = unpack_local_bitset(bitsets[row], block)
            local_coords = np.column_stack(
                np.unravel_index(local_indices, block, order="C")
            ).astype(np.int64, copy=False)
            global_coords = block_index.astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            if np.any(global_coords >= np.asarray(logical)[None, :]):
                raise GraphAdapterError("Packed source occupies an invalid terminal-block slot.")
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "storage_block_shape", block)
        object.__setattr__(self, "source_block_indices", indices)
        object.__setattr__(self, "occupancy_bitsets", bitsets)
        object.__setattr__(self, "block_value_offsets", offsets)
        object.__setattr__(self, "packed_values", values)
        object.__setattr__(self, "total_measure", total)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def source_block_count(self) -> int:
        return int(self.source_block_indices.shape[0])

    @property
    def occupied_node_count(self) -> int:
        return int(self.packed_values.size)

    @property
    def block_grid_shape(self) -> tuple[int, int, int]:
        return block_grid_shape(self.logical_grid_shape, self.storage_block_shape)

    @property
    def retained_array_bytes(self) -> int:
        return int(
            self.source_block_indices.nbytes
            + self.occupancy_bitsets.nbytes
            + self.block_value_offsets.nbytes
            + self.packed_values.nbytes
        )

    @property
    def content_identity(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.schema_version.encode("ascii"))
        digest.update(np.asarray(self.logical_grid_shape, dtype=np.int64).tobytes())
        digest.update(np.asarray(self.storage_block_shape, dtype=np.int64).tobytes())
        digest.update(self.source_block_indices.tobytes(order="C"))
        digest.update(self.occupancy_bitsets.tobytes(order="C"))
        digest.update(self.block_value_offsets.tobytes(order="C"))
        digest.update(self.packed_values.tobytes(order="C"))
        return digest.hexdigest()

    def iter_occupied_nodes(
        self, *, batch_size: int | None = None
    ) -> Iterator[tuple[IntArray, FloatArray]]:
        flat_parts: list[IntArray] = []
        value_parts: list[FloatArray] = []
        block = self.storage_block_shape
        for row, block_index in enumerate(self.source_block_indices):
            local_flat = unpack_local_bitset(self.occupancy_bitsets[row], block)
            local_coords = np.column_stack(
                np.unravel_index(local_flat, block, order="C")
            ).astype(np.int64, copy=False)
            global_coords = block_index.astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            flat = np.ravel_multi_index(
                (global_coords[:, 0], global_coords[:, 1], global_coords[:, 2]),
                self.logical_grid_shape,
                order="C",
            ).astype(np.int64, copy=False)
            start = int(self.block_value_offsets[row])
            stop = int(self.block_value_offsets[row + 1])
            flat_parts.append(flat)
            value_parts.append(self.packed_values[start:stop])
        flat_all = np.concatenate(flat_parts)
        values_all = np.concatenate(value_parts)
        order = np.argsort(flat_all, kind="stable")
        flat_all = flat_all[order]
        values_all = values_all[order]
        size = int(flat_all.size) if batch_size is None else _positive_int(batch_size, name="batch_size")
        for start in range(0, int(flat_all.size), size):
            stop = min(int(flat_all.size), start + size)
            flat_batch = np.array(flat_all[start:stop], dtype=np.int64, copy=True)
            value_batch = np.array(values_all[start:stop], dtype=np.float64, copy=True)
            flat_batch.setflags(write=False)
            value_batch.setflags(write=False)
            yield flat_batch, value_batch

    def to_sparse_cic_node_masses(self) -> SparseCICNodeMasses3D:
        batches = list(self.iter_occupied_nodes())
        flat = np.concatenate([item[0] for item in batches])
        values = np.concatenate([item[1] for item in batches])
        return SparseCICNodeMasses3D(
            grid_shape=self.logical_grid_shape,
            flat_indices=flat,
            node_masses=values,
            total_measure=self.total_measure,
            source_provenance=self.source_provenance,
            metadata={
                **self.metadata.to_json_dict(),
                "adapter": "periodic_packed_cic_source_to_sparse_cic_v1",
                "source_field_identity": self.content_identity,
            },
        )

    def to_json_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "logical_grid_shape": list(self.logical_grid_shape),
            "storage_block_shape": list(self.storage_block_shape),
            "source_block_count": self.source_block_count,
            "occupied_node_count": self.occupied_node_count,
            "total_measure": self.total_measure,
            "retained_array_bytes": self.retained_array_bytes,
            "content_identity": self.content_identity,
            "source_provenance": self.source_provenance.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_arrays:
            result.update(
                {
                    "source_block_indices": self.source_block_indices.tolist(),
                    "occupancy_bitsets": [
                        [int(value) for value in row] for row in self.occupancy_bitsets
                    ],
                    "block_value_offsets": self.block_value_offsets.tolist(),
                    "packed_values": self.packed_values.tolist(),
                }
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicPackedCICSourceField3D":
        return cls(
            schema_version=str(value["schema_version"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            storage_block_shape=tuple(value["storage_block_shape"]),
            source_block_indices=np.asarray(value["source_block_indices"], dtype=np.int32),
            occupancy_bitsets=np.asarray(value["occupancy_bitsets"], dtype=np.uint64),
            block_value_offsets=np.asarray(value["block_value_offsets"], dtype=np.int64),
            packed_values=np.asarray(value["packed_values"], dtype=np.float64),
            total_measure=float(value["total_measure"]),
            source_provenance=DensitySourceProvenance.from_json_dict(
                value["source_provenance"]
            ),
            metadata=value.get("metadata", {}),
        )


def pack_periodic_cic_source(
    cic_masses: SparseCICNodeMasses3D,
    *,
    storage_block_shape: tuple[int, int, int] = (16, 16, 16),
    max_source_blocks: int | None = None,
    max_source_nodes: int | None = None,
    max_retained_bytes: int | None = None,
) -> PeriodicPackedCICSourceField3D:
    """Pack one globally aggregated sparse CIC source into immutable blocks."""

    if not isinstance(cic_masses, SparseCICNodeMasses3D):
        raise TypeError("cic_masses must be SparseCICNodeMasses3D.")
    block = _shape3(storage_block_shape, name="storage_block_shape")
    budget, _model, derived = resolve_density_resource_limits()
    node_default = derived["max_density_nonzero_nodes"]
    node_limit = (
        node_default
        if max_source_nodes is None
        else min(node_default, _positive_int(max_source_nodes, name="max_source_nodes"))
    )
    block_default = derived["max_density_blocks"]
    block_limit = (
        block_default
        if max_source_blocks is None
        else min(block_default, _positive_int(max_source_blocks, name="max_source_blocks"))
    )
    byte_limit = (
        budget.max_memory_bytes
        if max_retained_bytes is None
        else min(_positive_int(max_retained_bytes, name="max_retained_bytes"), budget.max_memory_bytes)
    )
    if cic_masses.occupied_node_count > node_limit:
        raise GraphComplexityError(
            f"Packed CIC source needs {cic_masses.occupied_node_count} nodes, "
            f"exceeding max_source_nodes={node_limit}."
        )
    logical = cic_masses.grid_shape
    grid = block_grid_shape(logical, block)
    coords = np.column_stack(
        np.unravel_index(cic_masses.flat_indices, logical, order="C")
    ).astype(np.int64, copy=False)
    block_coords = np.floor_divide(coords, np.asarray(block)[None, :])
    local_coords = coords - block_coords * np.asarray(block)[None, :]
    block_flat = np.ravel_multi_index(
        (block_coords[:, 0], block_coords[:, 1], block_coords[:, 2]),
        grid,
        order="C",
    ).astype(np.int64, copy=False)
    local_flat = np.ravel_multi_index(
        (local_coords[:, 0], local_coords[:, 1], local_coords[:, 2]),
        block,
        order="C",
    ).astype(np.int64, copy=False)
    order = np.lexsort((local_flat, block_flat))
    block_flat = block_flat[order]
    local_flat = local_flat[order]
    masses = cic_masses.node_masses[order]
    starts = np.concatenate(
        (
            np.asarray([0], dtype=np.int64),
            np.flatnonzero(block_flat[1:] != block_flat[:-1]).astype(np.int64) + 1,
        )
    )
    unique_blocks = block_flat[starts]
    if unique_blocks.size > block_limit:
        raise GraphComplexityError(
            f"Packed CIC source needs {unique_blocks.size} blocks, "
            f"exceeding max_source_blocks={block_limit}."
        )
    source_indices = np.column_stack(
        np.unravel_index(unique_blocks, grid, order="C")
    ).astype(np.int32, copy=False)
    counts = np.diff(np.concatenate((starts, np.asarray([block_flat.size], dtype=np.int64))))
    offsets = np.concatenate(
        (np.asarray([0], dtype=np.int64), np.cumsum(counts, dtype=np.int64))
    )
    bitsets = np.vstack(
        [
            pack_local_indices(local_flat[start : start + count], block)
            for start, count in zip(starts, counts, strict=True)
        ]
    ).astype(np.uint64, copy=False)
    retained = int(
        source_indices.nbytes + bitsets.nbytes + offsets.nbytes + masses.nbytes
    )
    if retained > byte_limit:
        raise GraphComplexityError(
            f"Packed CIC source needs {retained} bytes, exceeding "
            f"max_retained_bytes={byte_limit}."
        )
    return PeriodicPackedCICSourceField3D(
        logical_grid_shape=logical,
        storage_block_shape=block,
        source_block_indices=source_indices,
        occupancy_bitsets=bitsets,
        block_value_offsets=offsets,
        packed_values=masses,
        total_measure=cic_masses.total_measure,
        source_provenance=cic_masses.source_provenance,
        metadata={
            **cic_masses.metadata.to_json_dict(),
            "packing": "ld8_s1_positive_cic_bitset_blocks_v1",
            "source_schema": cic_masses.schema_version,
            "block_grid_shape": list(grid),
            "bit_order": "c_order_local_index_little_endian_uint64",
            "fixed_block_value_bytes_avoided": int(unique_blocks.size)
            * local_node_count(block)
            * 8,
        },
    )


@dataclass(frozen=True, slots=True)
class DensitySupportAtlas:
    """Exact field-specific target support derived from one packed CIC source."""

    logical_grid_shape: tuple[int, int, int]
    storage_block_shape: tuple[int, int, int]
    source_field_identity: str
    routing_identity: str
    active_target_block_indices: NDArray[np.int32]
    target_support_bitsets: UInt64Array
    source_to_target_block_ranges: IntArray
    source_to_target_block_indices: NDArray[np.int32]
    connected_component_labels: NDArray[np.int32] | None
    planning: DensitySupportAtlasPlan
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_SUPPORT_ATLAS_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SUPPORT_ATLAS_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported density-support-atlas schema {self.schema_version!r}."
            )
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        block = _shape3(self.storage_block_shape, name="storage_block_shape")
        grid = block_grid_shape(logical, block)
        for name in ("source_field_identity", "routing_identity"):
            value = getattr(self, name)
            if not isinstance(value, str) or len(value) != 64:
                raise GraphAdapterError(f"{name} must be a SHA-256 digest.")
        target = _readonly_array(
            self.active_target_block_indices,
            np.int32,
            ndim=2,
            name="active_target_block_indices",
        )
        if target.shape[1:] != (3,) or target.shape[0] == 0:
            raise GraphAdapterError("active_target_block_indices must have shape (n, 3), n > 0.")
        if np.any(target < 0) or np.any(target >= np.asarray(grid, dtype=np.int32)[None, :]):
            raise GraphAdapterError("Target block indices lie outside the block grid.")
        target_flat = _flat_block_indices(target, grid)
        if target_flat.size > 1 and np.any(target_flat[1:] <= target_flat[:-1]):
            raise GraphAdapterError("Target blocks must be unique and C-order sorted.")
        bitsets = _readonly_array(
            self.target_support_bitsets,
            np.uint64,
            ndim=2,
            name="target_support_bitsets",
        )
        words = local_word_count(block)
        if bitsets.shape != (target.shape[0], words):
            raise GraphAdapterError("target_support_bitsets do not align with target blocks.")
        if np.any(_popcount_rows(bitsets) <= 0):
            raise GraphAdapterError("Every active target block must contain support nodes.")
        ranges = _readonly_array(
            self.source_to_target_block_ranges,
            np.int64,
            ndim=1,
            name="source_to_target_block_ranges",
        )
        if ranges.size == 0 or int(ranges[0]) != 0 or np.any(ranges[1:] < ranges[:-1]):
            raise GraphAdapterError("source_to_target_block_ranges must be valid CSR offsets.")
        edges = _readonly_array(
            self.source_to_target_block_indices,
            np.int32,
            ndim=1,
            name="source_to_target_block_indices",
        )
        if int(ranges[-1]) != edges.size:
            raise GraphAdapterError("source-to-target CSR arrays do not align.")
        if edges.size and (int(np.min(edges)) < 0 or int(np.max(edges)) >= target.shape[0]):
            raise GraphAdapterError("source_to_target_block_indices contain invalid target rows.")
        for row in range(ranges.size - 1):
            current = edges[int(ranges[row]) : int(ranges[row + 1])]
            if current.size > 1 and np.any(current[1:] <= current[:-1]):
                raise GraphAdapterError("Each source-to-target row must be unique and sorted.")
        labels = None
        if self.connected_component_labels is not None:
            labels = _readonly_array(
                self.connected_component_labels,
                np.int32,
                ndim=1,
                name="connected_component_labels",
            )
            if labels.shape != (target.shape[0],) or np.any(labels < 0):
                raise GraphAdapterError("connected_component_labels must align with targets.")
        if not isinstance(self.planning, DensitySupportAtlasPlan):
            raise TypeError("planning must be DensitySupportAtlasPlan.")
        if self.planning.source_field_identity != self.source_field_identity:
            raise GraphAdapterError("Planning source identity does not match the atlas.")
        # Every support bit must be a valid logical node, including terminal blocks.
        for row, block_index in enumerate(target):
            local_flat = unpack_local_bitset(bitsets[row], block)
            local_coords = np.column_stack(
                np.unravel_index(local_flat, block, order="C")
            ).astype(np.int64, copy=False)
            global_coords = block_index.astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            if np.any(global_coords >= np.asarray(logical)[None, :]):
                raise GraphAdapterError("Target support contains an invalid terminal-block slot.")
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "storage_block_shape", block)
        object.__setattr__(self, "active_target_block_indices", target)
        object.__setattr__(self, "target_support_bitsets", bitsets)
        object.__setattr__(self, "source_to_target_block_ranges", ranges)
        object.__setattr__(self, "source_to_target_block_indices", edges)
        object.__setattr__(self, "connected_component_labels", labels)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def target_block_count(self) -> int:
        return int(self.active_target_block_indices.shape[0])

    @property
    def target_support_node_count(self) -> int:
        return int(np.sum(_popcount_rows(self.target_support_bitsets), dtype=np.int64))

    @property
    def source_block_count(self) -> int:
        return int(self.source_to_target_block_ranges.size - 1)

    @property
    def source_target_edge_count(self) -> int:
        return int(self.source_to_target_block_indices.size)

    @property
    def retained_array_bytes(self) -> int:
        label_bytes = 0 if self.connected_component_labels is None else int(self.connected_component_labels.nbytes)
        return int(
            self.active_target_block_indices.nbytes
            + self.target_support_bitsets.nbytes
            + self.source_to_target_block_ranges.nbytes
            + self.source_to_target_block_indices.nbytes
            + label_bytes
        )

    @property
    def component_count(self) -> int | None:
        if self.connected_component_labels is None:
            return None
        return 0 if self.connected_component_labels.size == 0 else int(np.max(self.connected_component_labels)) + 1

    @property
    def content_identity(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.schema_version.encode("ascii"))
        digest.update(self.source_field_identity.encode("ascii"))
        digest.update(self.routing_identity.encode("ascii"))
        digest.update(self.active_target_block_indices.tobytes(order="C"))
        digest.update(self.target_support_bitsets.tobytes(order="C"))
        digest.update(self.source_to_target_block_ranges.tobytes(order="C"))
        digest.update(self.source_to_target_block_indices.tobytes(order="C"))
        return digest.hexdigest()

    def support_flat_indices(self) -> IntArray:
        parts: list[IntArray] = []
        block = self.storage_block_shape
        for row, block_index in enumerate(self.active_target_block_indices):
            local_flat = unpack_local_bitset(self.target_support_bitsets[row], block)
            local_coords = np.column_stack(
                np.unravel_index(local_flat, block, order="C")
            ).astype(np.int64, copy=False)
            global_coords = block_index.astype(np.int64)[None, :] * np.asarray(block)[None, :] + local_coords
            flat = np.ravel_multi_index(
                (global_coords[:, 0], global_coords[:, 1], global_coords[:, 2]),
                self.logical_grid_shape,
                order="C",
            ).astype(np.int64, copy=False)
            parts.append(flat)
        result = np.sort(np.concatenate(parts)).astype(np.int64, copy=False)
        if result.size > 1 and np.any(result[1:] <= result[:-1]):
            raise GraphAdapterError("Atlas support contains duplicate logical nodes.")
        result = np.array(result, dtype=np.int64, copy=True, order="C")
        result.setflags(write=False)
        return result

    def to_json_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "logical_grid_shape": list(self.logical_grid_shape),
            "storage_block_shape": list(self.storage_block_shape),
            "source_field_identity": self.source_field_identity,
            "routing_identity": self.routing_identity,
            "target_block_count": self.target_block_count,
            "target_support_node_count": self.target_support_node_count,
            "source_block_count": self.source_block_count,
            "source_target_edge_count": self.source_target_edge_count,
            "retained_array_bytes": self.retained_array_bytes,
            "component_count": self.component_count,
            "content_identity": self.content_identity,
            "planning": self.planning.to_json_dict(),
            "metadata": self.metadata.to_json_dict(),
        }
        if include_arrays:
            result.update(
                {
                    "active_target_block_indices": self.active_target_block_indices.tolist(),
                    "target_support_bitsets": [
                        [int(value) for value in row]
                        for row in self.target_support_bitsets
                    ],
                    "source_to_target_block_ranges": self.source_to_target_block_ranges.tolist(),
                    "source_to_target_block_indices": self.source_to_target_block_indices.tolist(),
                    "connected_component_labels": None
                    if self.connected_component_labels is None
                    else self.connected_component_labels.tolist(),
                }
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "DensitySupportAtlas":
        labels = value.get("connected_component_labels")
        return cls(
            schema_version=str(value["schema_version"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            storage_block_shape=tuple(value["storage_block_shape"]),
            source_field_identity=str(value["source_field_identity"]),
            routing_identity=str(value["routing_identity"]),
            active_target_block_indices=np.asarray(
                value["active_target_block_indices"], dtype=np.int32
            ),
            target_support_bitsets=np.asarray(
                value["target_support_bitsets"], dtype=np.uint64
            ),
            source_to_target_block_ranges=np.asarray(
                value["source_to_target_block_ranges"], dtype=np.int64
            ),
            source_to_target_block_indices=np.asarray(
                value["source_to_target_block_indices"], dtype=np.int32
            ),
            connected_component_labels=None
            if labels is None
            else np.asarray(labels, dtype=np.int32),
            planning=DensitySupportAtlasPlan.from_json_dict(value["planning"]),
            metadata=value.get("metadata", {}),
        )


def _connected_component_labels(
    active_block_indices: NDArray[np.int32],
    grid_shape: tuple[int, int, int],
) -> NDArray[np.int32]:
    """Label periodic face-connected blocks with SciPy sparse graph kernels."""

    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components

    coordinates = np.asarray(active_block_indices, dtype=np.int64)
    flat = _flat_block_indices(active_block_indices, grid_shape)
    steps = np.asarray(
        ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)),
        dtype=np.int64,
    )
    neighbors = (
        coordinates[:, None, :] + steps[None, :, :]
    ) % np.asarray(grid_shape, dtype=np.int64)[None, None, :]
    neighbor_flat = np.ravel_multi_index(
        (
            neighbors[:, :, 0].ravel(),
            neighbors[:, :, 1].ravel(),
            neighbors[:, :, 2].ravel(),
        ),
        grid_shape,
        order="C",
    ).astype(np.int64, copy=False)
    positions = np.searchsorted(flat, neighbor_flat)
    present = (positions < flat.size) & (
        flat[np.minimum(positions, flat.size - 1)] == neighbor_flat
    )
    rows = np.repeat(np.arange(flat.size, dtype=np.int64), steps.shape[0])[present]
    cols = positions[present].astype(np.int64, copy=False)
    adjacency = coo_matrix(
        (np.ones(rows.size, dtype=np.int8), (rows, cols)),
        shape=(flat.size, flat.size),
    ).tocsr()
    _count, labels = connected_components(
        adjacency, directed=False, return_labels=True
    )
    result = np.asarray(labels, dtype=np.int32)
    result.setflags(write=False)
    return result


def _brick_coordinates_to_target_bitsets(
    brick_coordinates: NDArray[np.int64],
    source_block_index: NDArray[np.int32],
    routing: PeriodicKernelBlockRouting,
    signed_minimum: NDArray[np.int64],
) -> tuple[IntArray, UInt64Array, int]:
    """Fold lifted-brick coordinates into packed periodic target bitsets."""

    block = routing.storage_block_shape
    logical = routing.logical_grid_shape
    source_start = source_block_index.astype(np.int64) * np.asarray(block, dtype=np.int64)
    global_coordinates = (
        source_start[None, :] + brick_coordinates + signed_minimum[None, :]
    ) % np.asarray(logical, dtype=np.int64)[None, :]
    target_blocks = np.floor_divide(
        global_coordinates, np.asarray(block, dtype=np.int64)[None, :]
    )
    target_local = global_coordinates - target_blocks * np.asarray(block, dtype=np.int64)[None, :]
    target_block_flat = np.ravel_multi_index(
        (target_blocks[:, 0], target_blocks[:, 1], target_blocks[:, 2]),
        routing.block_grid_shape,
        order="C",
    ).astype(np.int64, copy=False)
    target_local_flat = np.ravel_multi_index(
        (target_local[:, 0], target_local[:, 1], target_local[:, 2]),
        block,
        order="C",
    ).astype(np.int64, copy=False)
    block_nodes = local_node_count(block)
    encoded = np.unique(target_block_flat * block_nodes + target_local_flat)
    unique_flats, inverse = np.unique(
        encoded // block_nodes, return_inverse=True
    )
    local_flat = encoded % block_nodes
    word_indices = (local_flat // 64).astype(np.int64, copy=False)
    bit_indices = (local_flat % 64).astype(np.uint64, copy=False)
    bit_values = np.left_shift(np.uint64(1), bit_indices)
    words = np.zeros(
        (unique_flats.size, routing.block_word_count), dtype=np.uint64
    )
    np.bitwise_or.at(words, (inverse, word_indices), bit_values)
    transient_bytes = int(
        global_coordinates.nbytes
        + target_blocks.nbytes
        + target_local.nbytes
        + target_block_flat.nbytes
        + target_local_flat.nbytes
        + encoded.nbytes
        + inverse.nbytes
        + local_flat.nbytes
        + word_indices.nbytes
        + bit_values.nbytes
    )
    return (
        unique_flats.astype(np.int64, copy=False),
        words,
        transient_bytes,
    )


def _dilate_source_block_bitset(
    source_words: UInt64Array,
    source_block_index: NDArray[np.int32],
    routing: PeriodicKernelBlockRouting,
) -> tuple[IntArray, UInt64Array, int, int]:
    """Dilate one source block with the canonical Python-integer oracle."""

    block = routing.storage_block_shape
    source_extent = routing.extent_for_block(
        tuple(int(value) for value in source_block_index)
    )
    signed = np.asarray(routing.signed_offsets, dtype=np.int64)
    minimum = np.min(signed, axis=0)
    maximum = np.max(signed, axis=0)
    span = maximum - minimum
    brick_shape = tuple(
        int(source_extent[axis] + span[axis]) for axis in range(3)
    )
    brick_count = int(np.prod(brick_shape, dtype=object))
    source_local_flat = unpack_local_bitset(source_words, block)
    source_local = np.column_stack(
        np.unravel_index(source_local_flat, block, order="C")
    ).astype(np.int64, copy=False)
    embedded = source_local - minimum[None, :]
    embedded_flat = np.ravel_multi_index(
        (embedded[:, 0], embedded[:, 1], embedded[:, 2]),
        brick_shape,
        order="C",
    ).astype(np.int64, copy=False)
    source_integer = bitset_words_to_int(
        pack_local_indices(embedded_flat, brick_shape)
    )
    strides = np.asarray(
        (brick_shape[1] * brick_shape[2], brick_shape[2], 1),
        dtype=np.int64,
    )
    flat_shifts = signed @ strides
    dilated = 0
    for shift in flat_shifts:
        value = int(shift)
        dilated |= source_integer << value if value >= 0 else source_integer >> (-value)
    byte_count = (brick_count + 7) // 8
    packed_bytes = dilated.to_bytes(byte_count, byteorder="little", signed=False)
    bit_bytes = np.frombuffer(packed_bytes, dtype=np.uint8)
    active_bits = np.unpackbits(bit_bytes, bitorder="little")[:brick_count]
    brick_flat = np.flatnonzero(active_bits).astype(np.int64, copy=False)
    brick_coordinates = np.column_stack(
        np.unravel_index(brick_flat, brick_shape, order="C")
    ).astype(np.int64, copy=False)
    target_flats, target_words, fold_bytes = _brick_coordinates_to_target_bitsets(
        brick_coordinates, source_block_index, routing, minimum
    )
    transient_bytes = int(
        byte_count
        + active_bits.nbytes
        + brick_flat.nbytes
        + brick_coordinates.nbytes
        + fold_bytes
    )
    return target_flats, target_words, brick_count, transient_bytes


def _binary_stencil_kernel(
    routing: PeriodicKernelBlockRouting,
) -> tuple[FloatArray, NDArray[np.int64]]:
    signed = np.asarray(routing.signed_offsets, dtype=np.int64)
    minimum = np.min(signed, axis=0)
    maximum = np.max(signed, axis=0)
    kernel_shape = tuple(int(value) for value in (maximum - minimum + 1))
    kernel = np.zeros(kernel_shape, dtype=np.float64)
    local = signed - minimum[None, :]
    kernel[local[:, 0], local[:, 1], local[:, 2]] = 1.0
    return kernel, minimum


def _dilate_source_block_fft(
    source_words: UInt64Array,
    source_block_index: NDArray[np.int32],
    routing: PeriodicKernelBlockRouting,
    *,
    binary_kernel: FloatArray,
    signed_minimum: NDArray[np.int64],
    fft_workers: int,
    fft_work_units_per_second: float,
) -> tuple[IntArray, UInt64Array, int, int, bool]:
    """Exact binary dilation via zero-padded integer-count FFT convolution.

    Source and stencil arrays are binary, so the true linear-convolution output
    is integer-valued.  A strict distance-to-nearest-integer certificate is
    checked before thresholding at one half.  This is an execution optimization
    only; the resulting modular support is identical to the bitset oracle.
    """

    block = routing.storage_block_shape
    source_extent = routing.extent_for_block(
        tuple(int(value) for value in source_block_index)
    )
    source_dense = np.zeros(source_extent, dtype=np.float64)
    source_local_flat = unpack_local_bitset(source_words, block)
    source_local = np.column_stack(
        np.unravel_index(source_local_flat, block, order="C")
    ).astype(np.int64, copy=False)
    source_dense[source_local[:, 0], source_local[:, 1], source_local[:, 2]] = 1.0
    full_shape = tuple(
        int(source_extent[axis] + binary_kernel.shape[axis] - 1)
        for axis in range(3)
    )
    # PAR-DENS5 may execute a sufficiently large binary convolution on CUDA,
    # but only in FP64 and only when transfer/setup cost is predicted to be
    # amortized under the 80% free-VRAM ceiling.  The CPU scipy path remains
    # complete and authoritative for fallback.
    padded_shape = tuple(next_fast_len(value) for value in full_shape)
    cpu_estimate = estimate_fft_cpu_seconds(
        int(np.prod(padded_shape, dtype=object)),
        work_units_per_second=float(fft_work_units_per_second),
    )
    gpu_full = try_gpu_linear_fft_convolution(
        source_dense,
        binary_kernel,
        padded_shape,
        cpu_estimate_seconds=cpu_estimate,
        kernel_name="support_binary_fft_dilation",
    )
    used_gpu = gpu_full is not None
    if gpu_full is None:
        # scipy.signal.fftconvolve is backed by scipy.fft.  PAR-DENS3 binds its
        # default worker pool to the live scene lease instead of allowing an
        # unconstrained per-field transform.  Cross-block spectra are deliberately
        # not retained, preserving the existing bounded-workspace contract.
        with set_workers(max(1, int(fft_workers))):
            convolution = fftconvolve(source_dense, binary_kernel, mode="full")
    else:
        convolution = gpu_full[
            : full_shape[0], : full_shape[1], : full_shape[2]
        ]
    rounded = np.rint(convolution)
    maximum_roundoff = float(np.max(np.abs(convolution - rounded)))
    if maximum_roundoff > 1.0e-6:
        raise GraphAdapterError(
            "Binary support FFT lost its integer-convolution certificate: "
            f"maximum roundoff={maximum_roundoff:.6g}."
        )
    brick_coordinates = np.argwhere(rounded >= 1.0).astype(np.int64, copy=False)
    target_flats, target_words, fold_bytes = _brick_coordinates_to_target_bitsets(
        brick_coordinates, source_block_index, routing, signed_minimum
    )
    brick_count = int(np.prod(full_shape, dtype=object))
    transient_bytes = int(
        source_dense.nbytes
        + convolution.nbytes
        + rounded.nbytes
        + brick_coordinates.nbytes
        + fold_bytes
    )
    return target_flats, target_words, brick_count, transient_bytes, used_gpu

def build_density_support_atlas(
    source_field: PeriodicPackedCICSourceField3D,
    routing: PeriodicKernelBlockRouting,
    *,
    planning_limits: DensitySupportPlanningLimits | None = None,
    compute_connected_components: bool = False,
    dilation_backend: SupportDilationBackend = "auto",
    fft_workers: int | None = None,
    progress: ProgressPortLike | None = None,
    field_key: str = "density-field",
) -> DensitySupportAtlas:
    """Construct exact support by bounded source-block padded-bitset dilation."""

    if not isinstance(source_field, PeriodicPackedCICSourceField3D):
        raise TypeError("source_field must be PeriodicPackedCICSourceField3D.")
    if not isinstance(routing, PeriodicKernelBlockRouting):
        raise TypeError("routing must be PeriodicKernelBlockRouting.")
    if source_field.logical_grid_shape != routing.logical_grid_shape:
        raise GraphAdapterError("source field and routing must share logical_grid_shape.")
    if source_field.storage_block_shape != routing.storage_block_shape:
        raise GraphAdapterError("source field and routing must share storage_block_shape.")
    if dilation_backend not in {"auto", "bitset", "fft"}:
        raise GraphStyleError("dilation_backend must be auto, bitset, or fft.")
    budget, time_model, _derived = resolve_density_resource_limits()
    worker_cap = (
        budget.max_threads
        if fft_workers is None
        else min(budget.max_threads, _positive_int(fft_workers, name="fft_workers"))
    )

    def live_workers() -> int:
        return min(
            worker_cap,
            autotuned_fft_worker_count(current_density_worker_count(default=budget.max_threads)),
        )
    resolved_backend: SupportDilationBackend = dilation_backend
    if resolved_backend == "auto":
        resolved_backend = (
            "fft"
            if routing.stencil_offset_count >= DEFAULT_FFT_DILATION_STENCIL_THRESHOLD
            else "bitset"
        )
    plan = plan_density_support_atlas(source_field, routing, limits=planning_limits)
    reporter = ProgressEmitter(
        resolve_progress_port(progress), source="plotting.density_support_atlas"
    )
    grid = routing.block_grid_shape
    words = routing.block_word_count
    source_edge_parts: list[np.ndarray] = []
    target_flat_parts: list[np.ndarray] = []
    target_word_parts: list[np.ndarray] = []
    bitset_shift_operations = 0
    maximum_lifted_brick_nodes = 0
    maximum_lifted_transient_bytes = 0
    gpu_fft_dilation_count = 0
    cpu_fft_dilation_count = 0
    binary_kernel: FloatArray | None = None
    signed_minimum: NDArray[np.int64] | None = None
    if resolved_backend == "fft":
        binary_kernel, signed_minimum = _binary_stencil_kernel(routing)
    def dilate_row(source_row: int) -> tuple[int, IntArray, UInt64Array, int, int, bool]:
        source_block = source_field.source_block_indices[source_row]
        if resolved_backend == "fft":
            assert binary_kernel is not None and signed_minimum is not None
            local_flats, local_words, brick_nodes, transient_bytes, used_gpu = _dilate_source_block_fft(
                source_field.occupancy_bitsets[source_row],
                source_block,
                routing,
                binary_kernel=binary_kernel,
                signed_minimum=signed_minimum,
                fft_workers=live_workers(),
                fft_work_units_per_second=time_model.fft_work_units_per_second,
            )
        else:
            local_flats, local_words, brick_nodes, transient_bytes = _dilate_source_block_bitset(
                source_field.occupancy_bitsets[source_row], source_block, routing
            )
            used_gpu = False
        return source_row, local_flats, local_words, brick_nodes, transient_bytes, used_gpu

    # Bitset source blocks are independent.  Run bounded groups concurrently
    # only when the enclosing field task has enough transient-memory slack for
    # more than the one lifted brick already priced by the S1 plan.  FFT
    # dilation remains one block at a time and spends the lease inside scipy.fft.
    # This keeps aggregate task memory within the PAR-DENS2 field declaration.
    lease = current_density_worker_lease()
    # During Phase-B planning there is no field lease yet, so the global LD10
    # memory ceiling is authoritative.  During realization/preflight nested in
    # PAR-DENS2/3, use the task's declared transient allowance instead.  This
    # enables bounded source-block planning parallelism without escaping the one
    # scene-level memory authority.
    transient_ceiling = (
        int(budget.max_memory_bytes)
        if lease is None
        else int(lease.resources.transient_bytes)
    )
    extra_transient = max(
        0, transient_ceiling - int(plan.transient_bytes_upper)
    )
    per_parallel_block_bytes = max(1, int(plan.maximum_lifted_transient_bytes))
    memory_parallel_cap = 1 + extra_transient // per_parallel_block_bytes
    source_count = int(source_field.source_block_count)
    atlas_started = time.perf_counter()
    last_progress_emit = atlas_started
    reporter.started(
        "density_support_atlas",
        f"{field_key}: constructing exact support atlas; backend={resolved_backend}; "
        f"source_blocks={source_count}; stencil_offsets={routing.stencil_offset_count}",
        current=0,
        total=source_count,
        unit="source blocks",
        metadata={
            "field_key": field_key,
            "backend": resolved_backend,
            "source_block_count": source_count,
            "stencil_offset_count": int(routing.stencil_offset_count),
        },
    )
    cursor = 0
    while cursor < source_count:
        available = live_workers()
        group_workers = 1
        if resolved_backend == "bitset":
            group_workers = max(
                1,
                min(available, memory_parallel_cap, source_count - cursor),
            )
        # Small bounded groups let a long field observe lease growth after
        # sibling fields finish without creating more live workspaces than the
        # declared transient-memory slack permits.
        group_size = max(1, min(source_count - cursor, autotuned_group_size_multiplier(default=4) * group_workers))
        rows = tuple(range(cursor, cursor + group_size))
        if group_workers == 1:
            realized_group = tuple(dilate_row(row) for row in rows)
        else:
            with ThreadPoolExecutor(
                max_workers=group_workers,
                thread_name_prefix="mdstats-density-atlas",
            ) as pool:
                realized_group = tuple(pool.map(dilate_row, rows))
        for source_row, local_flats, local_words, brick_nodes, transient_bytes, used_gpu in realized_group:
            bitset_shift_operations += routing.stencil_offset_count
            if resolved_backend == "fft":
                if used_gpu:
                    gpu_fft_dilation_count += 1
                else:
                    cpu_fft_dilation_count += 1
            maximum_lifted_brick_nodes = max(maximum_lifted_brick_nodes, brick_nodes)
            maximum_lifted_transient_bytes = max(
                maximum_lifted_transient_bytes, transient_bytes
            )
            if local_flats.size:
                source_edge_parts.append(
                    np.full(local_flats.size, source_row, dtype=np.int32)
                )
                target_flat_parts.append(local_flats)
                target_word_parts.append(local_words)
        cursor += group_size
        now = time.perf_counter()
        if now - last_progress_emit >= 2.0 or cursor >= source_count:
            last_progress_emit = now
            reporter.update(
                "density_support_atlas",
                f"{field_key}: dilating exact support; backend={resolved_backend}; "
                f"workers={live_workers()}",
                current=min(cursor, source_count),
                total=source_count,
                unit="source blocks",
                metadata={
                    "field_key": field_key,
                    "backend": resolved_backend,
                    "workers": int(live_workers()),
                },
            )
    if not target_flat_parts:
        raise GraphAdapterError("Positive source support produced an empty target atlas.")

    reporter.update(
        "density_support_atlas_finalize",
        f"{field_key}: merging routed support blocks and building CSR lookup",
        current=0,
        total=1,
        unit="steps",
        metadata={"field_key": field_key},
    )
    edge_sources = np.concatenate(source_edge_parts).astype(np.int32, copy=False)
    edge_target_flats = np.concatenate(target_flat_parts).astype(np.int64, copy=False)
    edge_words = np.concatenate(target_word_parts, axis=0).astype(
        np.uint64, copy=False
    )
    target_flat_sorted, target_rows = np.unique(
        edge_target_flats, return_inverse=True
    )
    target_rows = target_rows.astype(np.int32, copy=False)
    target_bitsets = np.zeros(
        (target_flat_sorted.size, words), dtype=np.uint64
    )
    for word in range(words):
        np.bitwise_or.at(target_bitsets[:, word], target_rows, edge_words[:, word])
    target_indices = np.column_stack(
        np.unravel_index(target_flat_sorted, grid, order="C")
    ).astype(np.int32, copy=False)

    # Terminal-block validity has at most eight distinct extents.  Grouping by
    # extent avoids Python dispatch per target block while retaining the exact
    # routing certificate.
    extents = np.minimum(
        np.asarray(routing.storage_block_shape, dtype=np.int64)[None, :],
        np.asarray(routing.logical_grid_shape, dtype=np.int64)[None, :]
        - target_indices.astype(np.int64)
        * np.asarray(routing.storage_block_shape, dtype=np.int64)[None, :],
    )
    unique_extents, extent_inverse = np.unique(extents, axis=0, return_inverse=True)
    for extent_row, extent in enumerate(unique_extents):
        valid = routing.validity_bitset(tuple(int(value) for value in extent))
        rows = extent_inverse == extent_row
        if np.any(target_bitsets[rows] & ~valid):
            raise GraphAdapterError(
                "Exact terminal routing produced support outside the logical grid."
            )

    # Build source -> target CSR by compiled sorting and counting.  Local target
    # maps are already unique per source, but a final pair unique operation is
    # retained as a defensive certificate.
    pair_codes = (
        edge_sources.astype(np.int64) * target_flat_sorted.size
        + target_rows.astype(np.int64)
    )
    unique_pair_codes = np.unique(pair_codes)
    sorted_sources = unique_pair_codes // target_flat_sorted.size
    sorted_targets = unique_pair_codes % target_flat_sorted.size
    source_counts = np.bincount(
        sorted_sources, minlength=source_field.source_block_count
    ).astype(np.int64, copy=False)
    range_array = np.empty(source_field.source_block_count + 1, dtype=np.int64)
    range_array[0] = 0
    np.cumsum(source_counts, out=range_array[1:])
    edges = sorted_targets.astype(np.int32, copy=False)

    labels = _connected_component_labels(target_indices, grid) if compute_connected_components else None
    realized_bytes = int(
        target_indices.nbytes
        + target_bitsets.nbytes
        + range_array.nbytes
        + edges.nbytes
        + (0 if labels is None else labels.nbytes)
    )
    if target_indices.shape[0] > plan.target_block_count_upper:
        raise GraphAdapterError("Realized target blocks exceed the approved upper bound.")
    if edges.size > plan.source_target_edge_count_upper:
        raise GraphAdapterError("Realized source-target edges exceed the approved upper bound.")
    if bitset_shift_operations > plan.bitset_region_operations_upper:
        raise GraphAdapterError("Realized bitset shifts exceed the approved upper bound.")
    if realized_bytes > plan.atlas_retained_bytes_upper:
        raise GraphAdapterError("Realized atlas bytes exceed the approved upper bound.")
    atlas = DensitySupportAtlas(
        logical_grid_shape=source_field.logical_grid_shape,
        storage_block_shape=source_field.storage_block_shape,
        source_field_identity=source_field.content_identity,
        routing_identity=routing.cache_identity,
        active_target_block_indices=target_indices,
        target_support_bitsets=target_bitsets,
        source_to_target_block_ranges=range_array,
        source_to_target_block_indices=edges,
        connected_component_labels=labels,
        planning=plan,
        metadata={
            "algorithm": (
                "ld8_s4_exact_binary_fft_support_dilation_v1"
                if resolved_backend == "fft"
                else "ld8_s1_exact_source_block_padded_bitset_dilation_v1"
            ),
            "dilation_backend": resolved_backend,
            "requested_dilation_backend": dilation_backend,
            "fft_worker_policy": ("bounded_scheduler_or_explicit_cap" if resolved_backend == "fft" else "not_applicable"),
            "fft_kernel_transform_count": (
                source_field.source_block_count if resolved_backend == "fft" else 0
            ),
            "gpu_fft_dilation_count": gpu_fft_dilation_count,
            "cpu_fft_dilation_count": cpu_fft_dilation_count,
            "gpu_execution_is_scientifically_neutral": True,
            "bit_order": "c_order_local_index_little_endian_uint64",
            "stencil_identity": routing.stencil_identity,
            "target_block_count": int(target_indices.shape[0]),
            "target_support_node_count": int(np.sum(_popcount_rows(target_bitsets))),
            "source_target_edge_count": int(edges.size),
            "bitset_shift_operations": bitset_shift_operations,
            "maximum_lifted_brick_nodes": maximum_lifted_brick_nodes,
            "maximum_lifted_transient_bytes": maximum_lifted_transient_bytes,
            "complete_fine_pair_array_allocated": False,
            "source_specific_global_cache_used": False,
            "connected_components_computed": labels is not None,
        },
    )
    reporter.completed(
        "density_support_atlas",
        f"{field_key}: support atlas complete in {time.perf_counter() - atlas_started:.1f} s; "
        f"target_blocks={atlas.target_block_count}; target_nodes={atlas.target_support_node_count}",
        current=source_count,
        total=source_count,
        unit="source blocks",
        metadata={
            "field_key": field_key,
            "target_block_count": int(atlas.target_block_count),
            "target_support_node_count": int(atlas.target_support_node_count),
        },
    )
    return atlas


@dataclass(frozen=True, slots=True)
class DensitySupportEquivalenceReport:
    source_field_identity: str
    atlas_identity: str
    source_node_count: int
    stencil_offset_count: int
    explicit_pair_count: int
    expected_support_node_count: int
    atlas_support_node_count: int
    missing_node_count: int
    extra_node_count: int
    exact_match: bool
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_SUPPORT_EQUIVALENCE_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_SUPPORT_EQUIVALENCE_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported support-equivalence schema {self.schema_version!r}."
            )
        for name in ("source_field_identity", "atlas_identity"):
            if not isinstance(getattr(self, name), str) or len(getattr(self, name)) != 64:
                raise GraphAdapterError(f"{name} must be a SHA-256 digest.")
        for name in (
            "source_node_count",
            "stencil_offset_count",
            "explicit_pair_count",
            "expected_support_node_count",
            "atlas_support_node_count",
            "missing_node_count",
            "extra_node_count",
        ):
            value = int(getattr(self, name))
            if value < 0:
                raise GraphAdapterError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        exact = self.missing_node_count == 0 and self.extra_node_count == 0
        if bool(self.exact_match) != exact:
            raise GraphAdapterError("exact_match disagrees with missing/extra counts.")
        object.__setattr__(self, "exact_match", exact)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    def to_json_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "source_field_identity": self.source_field_identity,
            "atlas_identity": self.atlas_identity,
            "source_node_count": self.source_node_count,
            "stencil_offset_count": self.stencil_offset_count,
            "explicit_pair_count": self.explicit_pair_count,
            "expected_support_node_count": self.expected_support_node_count,
            "atlas_support_node_count": self.atlas_support_node_count,
            "missing_node_count": self.missing_node_count,
            "extra_node_count": self.extra_node_count,
            "exact_match": self.exact_match,
            "metadata": self.metadata.to_json_dict(),
        }


def verify_density_support_atlas(
    source_field: PeriodicPackedCICSourceField3D,
    stencil: PeriodicGaussianStencilSupport,
    atlas: DensitySupportAtlas,
    *,
    max_explicit_pairs: int | None = None,
) -> DensitySupportEquivalenceReport:
    """Exhaustively compare an atlas to the explicit modular Minkowski sum.

    This verification path is intentionally bounded and belongs to tests,
    migration audits, and small diagnostic cases.  It is not used by production
    support planning.
    """

    if not isinstance(source_field, PeriodicPackedCICSourceField3D):
        raise TypeError("source_field must be PeriodicPackedCICSourceField3D.")
    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    if not isinstance(atlas, DensitySupportAtlas):
        raise TypeError("atlas must be DensitySupportAtlas.")
    if source_field.logical_grid_shape != stencil.grid_shape or atlas.logical_grid_shape != stencil.grid_shape:
        raise GraphAdapterError("Source, stencil, and atlas must share a logical grid.")
    if atlas.source_field_identity != source_field.content_identity:
        raise GraphAdapterError("Atlas source identity does not match source_field.")
    pair_count = source_field.occupied_node_count * stencil.stencil_offset_count
    _budget, _model, derived = resolve_density_resource_limits()
    default_limit = derived["max_density_kernel_pairs"]
    limit = (
        default_limit
        if max_explicit_pairs is None
        else min(
            default_limit,
            _positive_int(max_explicit_pairs, name="max_explicit_pairs"),
        )
    )
    if pair_count > limit:
        raise GraphComplexityError(
            f"Explicit support verification needs {pair_count} pairs, exceeding "
            f"max_explicit_pairs={limit}."
        )
    source_sparse = source_field.to_sparse_cic_node_masses()
    source_coords = np.column_stack(
        np.unravel_index(
            source_sparse.flat_indices, source_field.logical_grid_shape, order="C"
        )
    ).astype(np.int64, copy=False)
    stencil_coords = np.column_stack(
        np.unravel_index(
            stencil.active_flat_indices, stencil.grid_shape, order="C"
        )
    ).astype(np.int64, copy=False)
    targets = (
        source_coords[:, None, :] + stencil_coords[None, :, :]
    ) % np.asarray(stencil.grid_shape, dtype=np.int64)[None, None, :]
    expected = np.unique(
        np.ravel_multi_index(
            (targets[..., 0].reshape(-1), targets[..., 1].reshape(-1), targets[..., 2].reshape(-1)),
            stencil.grid_shape,
            order="C",
        )
    ).astype(np.int64, copy=False)
    actual = atlas.support_flat_indices()
    missing = np.setdiff1d(expected, actual, assume_unique=True)
    extra = np.setdiff1d(actual, expected, assume_unique=True)
    return DensitySupportEquivalenceReport(
        source_field_identity=source_field.content_identity,
        atlas_identity=atlas.content_identity,
        source_node_count=source_field.occupied_node_count,
        stencil_offset_count=stencil.stencil_offset_count,
        explicit_pair_count=pair_count,
        expected_support_node_count=int(expected.size),
        atlas_support_node_count=int(actual.size),
        missing_node_count=int(missing.size),
        extra_node_count=int(extra.size),
        exact_match=missing.size == 0 and extra.size == 0,
        metadata={
            "verification": "explicit_modular_minkowski_sum_v1",
            "stencil_identity": stencil_content_identity(stencil),
            "missing_sample": missing[:16].tolist(),
            "extra_sample": extra[:16].tolist(),
        },
    )
