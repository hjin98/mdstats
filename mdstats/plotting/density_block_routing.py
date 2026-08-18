"""Exact reusable block routing for finite-support periodic density kernels.

LD8-S0 separates immutable kernel geometry from field-specific source support.
This module contains only source-independent routing information: the exact
canonical stencil offsets, their nominal block displacement groups, terminal
block extent classes, and packed local validity masks.  It deliberately stores
no source blocks, source occupancy, or target support.

The packed bit ordering and terminal routing are project-specific mdstats
contracts.  Bit ``i`` corresponds to the C-order local node index ``i`` and is
stored in word ``i // 64`` at bit ``i % 64``.
"""

from __future__ import annotations

import hashlib
from collections import OrderedDict
from collections.abc import Mapping
from dataclasses import dataclass, field
from itertools import product
from threading import RLock
from typing import Any

import numpy as np
from numpy.typing import NDArray

from .density_contracts import FrozenJSONMapping, freeze_json_mapping
from .density_kernel import PeriodicGaussianStencilSupport
from .graph_errors import GraphAdapterError, GraphComplexityError, GraphStyleError
from .runtime_resources import resolve_density_resource_limits

IntArray = NDArray[np.int64]
UInt64Array = NDArray[np.uint64]

BLOCK_OFFSET_STENCIL_GROUP_SCHEMA = "mdstats.block-offset-stencil-group.v1"
PERIODIC_KERNEL_BLOCK_ROUTING_SCHEMA = "mdstats.periodic-kernel-block-routing.v1"
DENSITY_ROUTING_CACHE_INFO_SCHEMA = "mdstats.density-routing-cache-info.v1"

DEFAULT_ROUTING_CACHE_MAX_ENTRIES = 16
DEFAULT_ROUTING_CACHE_MAX_BYTES = 128 * 1024 * 1024
DEFAULT_MAX_ROUTING_STENCIL_OFFSETS = 2_000_000

# NumPy 1.26 does not yet expose a portable uint64 bit-count ufunc.  A tiny
# uint8 lookup table keeps all bulk popcount work inside NumPy rather than
# iterating over Python integers.
_BYTE_POPCOUNT = np.unpackbits(
    np.arange(256, dtype=np.uint8)[:, None], axis=1
).sum(axis=1, dtype=np.uint16).astype(np.uint8)


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


def block_grid_shape(
    logical_grid_shape: tuple[int, int, int],
    storage_block_shape: tuple[int, int, int],
) -> tuple[int, int, int]:
    logical = _shape3(logical_grid_shape, name="logical_grid_shape")
    block = _shape3(storage_block_shape, name="storage_block_shape")
    return tuple(
        (logical[axis] + block[axis] - 1) // block[axis] for axis in range(3)
    )  # type: ignore[return-value]


def local_node_count(storage_block_shape: tuple[int, int, int]) -> int:
    return int(np.prod(_shape3(storage_block_shape, name="storage_block_shape"), dtype=object))


def local_word_count(storage_block_shape: tuple[int, int, int]) -> int:
    return (local_node_count(storage_block_shape) + 63) // 64


def _canonical_signed_axis(indices: NDArray[np.int64], size: int) -> NDArray[np.int64]:
    """Map canonical periodic indices to one deterministic signed representative.

    For an even axis, the Nyquist index ``size // 2`` remains positive.  This
    convention is deterministic and does not change the modular convolution.
    """

    threshold = size // 2
    result = np.array(indices, dtype=np.int64, copy=True)
    result[result > threshold] -= size
    return result


def canonical_signed_stencil_offsets(
    stencil: PeriodicGaussianStencilSupport,
) -> IntArray:
    """Return exact canonical modular offsets as signed logical triples."""

    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    coordinates = np.column_stack(
        np.unravel_index(stencil.active_flat_indices, stencil.grid_shape, order="C")
    ).astype(np.int64, copy=False)
    for axis, size in enumerate(stencil.grid_shape):
        coordinates[:, axis] = _canonical_signed_axis(coordinates[:, axis], size)
    result = np.array(coordinates, dtype=np.int64, copy=True, order="C")
    result.setflags(write=False)
    return result


def stencil_content_identity(stencil: PeriodicGaussianStencilSupport) -> str:
    """Return an exact immutable identity for one canonical stencil support."""

    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    digest = hashlib.sha256()
    digest.update(stencil.schema_version.encode("ascii"))
    digest.update(np.asarray(stencil.grid_shape, dtype=np.int64).tobytes(order="C"))
    digest.update(stencil.display_cell.tobytes(order="C"))
    digest.update(np.asarray([stencil.gaussian_bandwidth], dtype=np.float64).tobytes())
    digest.update(np.asarray([stencil.kernel_tail_tolerance], dtype=np.float64).tobytes())
    digest.update(stencil.active_flat_indices.tobytes(order="C"))
    digest.update(stencil.active_weights.tobytes(order="C"))
    return digest.hexdigest()


def pack_local_indices(
    local_flat_indices: Any,
    storage_block_shape: tuple[int, int, int],
) -> UInt64Array:
    """Pack unique local C-order indices with vectorized uint64 scatter-OR."""

    block = _shape3(storage_block_shape, name="storage_block_shape")
    count = int(np.prod(block, dtype=object))
    indices = np.asarray(local_flat_indices, dtype=np.int64)
    if indices.ndim != 1:
        raise GraphAdapterError("local_flat_indices must be one-dimensional.")
    if indices.size:
        if int(np.min(indices)) < 0 or int(np.max(indices)) >= count:
            raise GraphAdapterError("local_flat_indices lie outside the storage block.")
        indices = np.unique(indices)
    words = np.zeros((count + 63) // 64, dtype=np.uint64)
    if indices.size:
        word_indices = np.right_shift(indices, 6)
        bit_indices = np.bitwise_and(indices, 63).astype(np.uint64, copy=False)
        masks = np.left_shift(np.uint64(1), bit_indices)
        np.bitwise_or.at(words, word_indices, masks)
    words.setflags(write=False)
    return words


def unpack_local_bitset(
    words: Any,
    storage_block_shape: tuple[int, int, int],
) -> IntArray:
    """Return sorted local indices using NumPy's compiled bit unpacker."""

    block = _shape3(storage_block_shape, name="storage_block_shape")
    count = int(np.prod(block, dtype=object))
    vector = np.asarray(words, dtype=np.uint64)
    expected = (count + 63) // 64
    if vector.ndim != 1 or vector.shape != (expected,):
        raise GraphAdapterError(
            f"words must have shape ({expected},) for block shape {block}."
        )
    byte_view = np.ascontiguousarray(vector).view(np.uint8)
    occupied = np.unpackbits(byte_view, bitorder="little")[:count]
    array = np.flatnonzero(occupied).astype(np.int64, copy=False)
    array.setflags(write=False)
    return array


def bitset_popcounts(words: Any) -> IntArray:
    """Return one compiled popcount per bitset row.

    A one-dimensional input is treated as one row.  The returned array is always
    one-dimensional so callers can use the same kernel for one or many bitsets.
    """

    vector = np.asarray(words, dtype=np.uint64)
    if vector.ndim == 1:
        matrix = vector.reshape(1, -1)
    elif vector.ndim == 2:
        matrix = vector
    else:
        raise GraphAdapterError("words must be one- or two-dimensional.")
    byte_view = np.ascontiguousarray(matrix).view(np.uint8).reshape(matrix.shape[0], -1)
    counts = np.sum(_BYTE_POPCOUNT[byte_view], axis=1, dtype=np.int64)
    counts = np.asarray(counts, dtype=np.int64)
    counts.setflags(write=False)
    return counts


def bitset_popcount(words: Any) -> int:
    vector = np.asarray(words, dtype=np.uint64)
    if vector.ndim != 1:
        raise GraphAdapterError("words must be one-dimensional.")
    return int(bitset_popcounts(vector)[0])


def bitset_words_to_int(words: Any) -> int:
    vector = np.asarray(words, dtype=np.uint64)
    if vector.ndim != 1:
        raise GraphAdapterError("words must be one-dimensional.")
    little = np.ascontiguousarray(vector.astype("<u8", copy=False))
    return int.from_bytes(little.tobytes(order="C"), byteorder="little", signed=False)


def bitset_int_to_words(value: int, word_count: int) -> UInt64Array:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise GraphAdapterError("value must be a nonnegative Python integer.")
    words_count = _positive_int(word_count, name="word_count")
    bit_width = 64 * words_count
    truncated = value & ((1 << bit_width) - 1)
    raw = truncated.to_bytes(8 * words_count, byteorder="little", signed=False)
    words = np.frombuffer(raw, dtype="<u8").astype(np.uint64, copy=True)
    words.setflags(write=False)
    return words


def validity_bitset_for_extent(
    extent: tuple[int, int, int],
    storage_block_shape: tuple[int, int, int],
) -> UInt64Array:
    block = _shape3(storage_block_shape, name="storage_block_shape")
    if len(extent) != 3:
        raise GraphAdapterError("extent must contain three entries.")
    resolved = tuple(
        _positive_int(value, name="extent entry") for value in extent
    )
    if any(resolved[axis] > block[axis] for axis in range(3)):
        raise GraphAdapterError("extent cannot exceed storage_block_shape.")
    local = np.arange(int(np.prod(block, dtype=object)), dtype=np.int64).reshape(block)
    indices = local[
        : resolved[0],
        : resolved[1],
        : resolved[2],
    ].reshape(-1)
    return pack_local_indices(indices, block)


@dataclass(frozen=True, slots=True)
class BlockOffsetStencilGroup:
    """Canonical stencil offsets sharing one nominal coarse-block displacement."""

    nominal_block_offset: tuple[int, int, int]
    stencil_indices: NDArray[np.int32]
    signed_offsets: NDArray[np.int32]
    local_remainders: NDArray[np.int16]
    schema_version: str = BLOCK_OFFSET_STENCIL_GROUP_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != BLOCK_OFFSET_STENCIL_GROUP_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported block-offset group schema {self.schema_version!r}."
            )
        if len(self.nominal_block_offset) != 3:
            raise GraphAdapterError("nominal_block_offset must contain three entries.")
        nominal = tuple(int(value) for value in self.nominal_block_offset)
        indices = _readonly_array(
            self.stencil_indices, np.int32, ndim=1, name="stencil_indices"
        )
        offsets = _readonly_array(
            self.signed_offsets, np.int32, ndim=2, name="signed_offsets"
        )
        remainders = _readonly_array(
            self.local_remainders,
            np.int16,
            ndim=2,
            name="local_remainders",
        )
        if offsets.shape != (indices.size, 3) or remainders.shape != offsets.shape:
            raise GraphAdapterError("Block-offset group arrays must align as (n, 3).")
        if indices.size == 0:
            raise GraphAdapterError("A block-offset group cannot be empty.")
        if indices.size > 1 and np.any(indices[1:] <= indices[:-1]):
            raise GraphAdapterError("stencil_indices must be strictly increasing.")
        object.__setattr__(self, "nominal_block_offset", nominal)
        object.__setattr__(self, "stencil_indices", indices)
        object.__setattr__(self, "signed_offsets", offsets)
        object.__setattr__(self, "local_remainders", remainders)

    def to_json_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "nominal_block_offset": list(self.nominal_block_offset),
            "stencil_count": int(self.stencil_indices.size),
        }
        if include_arrays:
            result.update(
                {
                    "stencil_indices": self.stencil_indices.tolist(),
                    "signed_offsets": self.signed_offsets.tolist(),
                    "local_remainders": self.local_remainders.tolist(),
                }
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "BlockOffsetStencilGroup":
        return cls(
            schema_version=str(value["schema_version"]),
            nominal_block_offset=tuple(value["nominal_block_offset"]),
            stencil_indices=np.asarray(value["stencil_indices"], dtype=np.int32),
            signed_offsets=np.asarray(value["signed_offsets"], dtype=np.int32),
            local_remainders=np.asarray(value["local_remainders"], dtype=np.int16),
        )


@dataclass(frozen=True, slots=True)
class PeriodicKernelBlockRouting:
    """Reusable source-independent routing template for one exact stencil."""

    logical_grid_shape: tuple[int, int, int]
    storage_block_shape: tuple[int, int, int]
    block_grid_shape: tuple[int, int, int]
    axis_block_extents: tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]
    stencil_identity: str
    signed_offsets: NDArray[np.int32]
    relative_block_offsets: NDArray[np.int32]
    grouped_stencil_ranges: tuple[BlockOffsetStencilGroup, ...]
    terminal_extent_classes: NDArray[np.int32]
    terminal_validity_bitsets: UInt64Array
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = PERIODIC_KERNEL_BLOCK_ROUTING_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != PERIODIC_KERNEL_BLOCK_ROUTING_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported routing schema {self.schema_version!r}."
            )
        logical = _shape3(self.logical_grid_shape, name="logical_grid_shape")
        block = _shape3(self.storage_block_shape, name="storage_block_shape")
        grid = _shape3(self.block_grid_shape, name="block_grid_shape")
        if grid != block_grid_shape(logical, block):
            raise GraphAdapterError("block_grid_shape is inconsistent.")
        if len(self.axis_block_extents) != 3:
            raise GraphAdapterError("axis_block_extents must contain three axes.")
        extents: list[tuple[int, ...]] = []
        for axis in range(3):
            current = tuple(int(value) for value in self.axis_block_extents[axis])
            if len(current) != grid[axis]:
                raise GraphAdapterError("axis_block_extents do not match block_grid_shape.")
            if any(value <= 0 or value > block[axis] for value in current):
                raise GraphAdapterError("axis block extents are invalid.")
            if sum(current) != logical[axis]:
                raise GraphAdapterError("axis block extents do not sum to the logical shape.")
            extents.append(current)
        if not isinstance(self.stencil_identity, str) or len(self.stencil_identity) != 64:
            raise GraphAdapterError("stencil_identity must be a SHA-256 hexadecimal digest.")
        offsets = _readonly_array(
            self.signed_offsets, np.int32, ndim=2, name="signed_offsets"
        )
        if offsets.shape[1:] != (3,) or offsets.shape[0] == 0:
            raise GraphAdapterError("signed_offsets must have shape (n, 3), n > 0.")
        relative = _readonly_array(
            self.relative_block_offsets,
            np.int32,
            ndim=2,
            name="relative_block_offsets",
        )
        groups = tuple(self.grouped_stencil_ranges)
        if relative.shape != (len(groups), 3):
            raise GraphAdapterError("relative_block_offsets must align with groups.")
        concatenated: list[int] = []
        for row, group in enumerate(groups):
            if not isinstance(group, BlockOffsetStencilGroup):
                raise TypeError("grouped_stencil_ranges must contain BlockOffsetStencilGroup.")
            if tuple(int(value) for value in relative[row]) != group.nominal_block_offset:
                raise GraphAdapterError("Relative block offsets and groups disagree.")
            concatenated.extend(int(value) for value in group.stencil_indices)
        if sorted(concatenated) != list(range(offsets.shape[0])):
            raise GraphAdapterError("Routing groups must partition every stencil offset exactly once.")
        classes = _readonly_array(
            self.terminal_extent_classes,
            np.int32,
            ndim=2,
            name="terminal_extent_classes",
        )
        bitsets = _readonly_array(
            self.terminal_validity_bitsets,
            np.uint64,
            ndim=2,
            name="terminal_validity_bitsets",
        )
        if classes.shape[1:] != (3,) or bitsets.shape[0] != classes.shape[0]:
            raise GraphAdapterError("Terminal extent classes and validity masks must align.")
        expected_words = local_word_count(block)
        if bitsets.shape[1] != expected_words:
            raise GraphAdapterError("Terminal validity bitsets have the wrong word count.")
        if classes.shape[0] == 0:
            raise GraphAdapterError("At least one terminal extent class is required.")
        seen: set[tuple[int, int, int]] = set()
        for row, raw_extent in enumerate(classes):
            extent = tuple(int(value) for value in raw_extent)
            if extent in seen:
                raise GraphAdapterError("Terminal extent classes must be unique.")
            seen.add(extent)
            expected = validity_bitset_for_extent(extent, block)
            if not np.array_equal(expected, bitsets[row]):
                raise GraphAdapterError("Terminal validity bitset does not match its extent.")
        object.__setattr__(self, "logical_grid_shape", logical)
        object.__setattr__(self, "storage_block_shape", block)
        object.__setattr__(self, "block_grid_shape", grid)
        object.__setattr__(self, "axis_block_extents", tuple(extents))
        object.__setattr__(self, "signed_offsets", offsets)
        object.__setattr__(self, "relative_block_offsets", relative)
        object.__setattr__(self, "grouped_stencil_ranges", groups)
        object.__setattr__(self, "terminal_extent_classes", classes)
        object.__setattr__(self, "terminal_validity_bitsets", bitsets)
        object.__setattr__(self, "metadata", freeze_json_mapping(self.metadata))

    @property
    def stencil_offset_count(self) -> int:
        return int(self.signed_offsets.shape[0])

    @property
    def block_local_node_count(self) -> int:
        return local_node_count(self.storage_block_shape)

    @property
    def block_word_count(self) -> int:
        return local_word_count(self.storage_block_shape)

    @property
    def retained_array_bytes(self) -> int:
        group_bytes = sum(
            group.stencil_indices.nbytes
            + group.signed_offsets.nbytes
            + group.local_remainders.nbytes
            for group in self.grouped_stencil_ranges
        )
        return int(
            self.signed_offsets.nbytes
            + self.relative_block_offsets.nbytes
            + self.terminal_extent_classes.nbytes
            + self.terminal_validity_bitsets.nbytes
            + group_bytes
        )

    @property
    def cache_identity(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.schema_version.encode("ascii"))
        digest.update(self.stencil_identity.encode("ascii"))
        digest.update(np.asarray(self.logical_grid_shape, dtype=np.int64).tobytes())
        digest.update(np.asarray(self.storage_block_shape, dtype=np.int64).tobytes())
        digest.update(self.signed_offsets.tobytes(order="C"))
        return digest.hexdigest()

    def extent_for_block(self, block_index: tuple[int, int, int]) -> tuple[int, int, int]:
        if len(block_index) != 3:
            raise GraphAdapterError("block_index must contain three entries.")
        result: list[int] = []
        for axis, value in enumerate(block_index):
            index = int(value)
            if index < 0 or index >= self.block_grid_shape[axis]:
                raise GraphAdapterError("block_index lies outside the block grid.")
            result.append(self.axis_block_extents[axis][index])
        return tuple(result)  # type: ignore[return-value]

    def validity_bitset(self, extent: tuple[int, int, int]) -> UInt64Array:
        target = tuple(int(value) for value in extent)
        matches = np.flatnonzero(
            np.all(self.terminal_extent_classes == np.asarray(target, dtype=np.int32), axis=1)
        )
        if matches.size != 1:
            raise GraphAdapterError(f"Unknown terminal extent class {target}.")
        result = self.terminal_validity_bitsets[int(matches[0])]
        result.setflags(write=False)
        return result

    def to_json_dict(self, *, include_arrays: bool = True) -> dict[str, Any]:
        result: dict[str, Any] = {
            "schema_version": self.schema_version,
            "logical_grid_shape": list(self.logical_grid_shape),
            "storage_block_shape": list(self.storage_block_shape),
            "block_grid_shape": list(self.block_grid_shape),
            "axis_block_extents": [list(axis) for axis in self.axis_block_extents],
            "stencil_identity": self.stencil_identity,
            "stencil_offset_count": self.stencil_offset_count,
            "group_count": len(self.grouped_stencil_ranges),
            "terminal_extent_class_count": int(self.terminal_extent_classes.shape[0]),
            "retained_array_bytes": self.retained_array_bytes,
            "cache_identity": self.cache_identity,
            "metadata": self.metadata.to_json_dict(),
        }
        if include_arrays:
            result.update(
                {
                    "signed_offsets": self.signed_offsets.tolist(),
                    "relative_block_offsets": self.relative_block_offsets.tolist(),
                    "grouped_stencil_ranges": [
                        group.to_json_dict(include_arrays=True)
                        for group in self.grouped_stencil_ranges
                    ],
                    "terminal_extent_classes": self.terminal_extent_classes.tolist(),
                    "terminal_validity_bitsets": [
                        [int(value) for value in row]
                        for row in self.terminal_validity_bitsets
                    ],
                }
            )
        return result

    @classmethod
    def from_json_dict(cls, value: Mapping[str, Any]) -> "PeriodicKernelBlockRouting":
        return cls(
            schema_version=str(value["schema_version"]),
            logical_grid_shape=tuple(value["logical_grid_shape"]),
            storage_block_shape=tuple(value["storage_block_shape"]),
            block_grid_shape=tuple(value["block_grid_shape"]),
            axis_block_extents=tuple(
                tuple(axis) for axis in value["axis_block_extents"]
            ),  # type: ignore[arg-type]
            stencil_identity=str(value["stencil_identity"]),
            signed_offsets=np.asarray(value["signed_offsets"], dtype=np.int32),
            relative_block_offsets=np.asarray(
                value["relative_block_offsets"], dtype=np.int32
            ),
            grouped_stencil_ranges=tuple(
                BlockOffsetStencilGroup.from_json_dict(item)
                for item in value["grouped_stencil_ranges"]
            ),
            terminal_extent_classes=np.asarray(
                value["terminal_extent_classes"], dtype=np.int32
            ),
            terminal_validity_bitsets=np.asarray(
                value["terminal_validity_bitsets"], dtype=np.uint64
            ),
            metadata=value.get("metadata", {}),
        )


def build_periodic_kernel_block_routing(
    stencil: PeriodicGaussianStencilSupport,
    *,
    storage_block_shape: tuple[int, int, int] = (16, 16, 16),
    max_stencil_offsets: int | None = None,
) -> PeriodicKernelBlockRouting:
    """Build exact source-independent routing records for one finite stencil."""

    if not isinstance(stencil, PeriodicGaussianStencilSupport):
        raise TypeError("stencil must be PeriodicGaussianStencilSupport.")
    block = _shape3(storage_block_shape, name="storage_block_shape")
    _budget, _model, derived = resolve_density_resource_limits()
    default_limit = derived["max_density_stencil_values"]
    limit = (
        default_limit
        if max_stencil_offsets is None
        else min(
            default_limit,
            _positive_int(max_stencil_offsets, name="max_stencil_offsets"),
        )
    )
    signed = canonical_signed_stencil_offsets(stencil)
    if signed.shape[0] > limit:
        raise GraphComplexityError(
            "Kernel block routing requires "
            f"{signed.shape[0]} offsets, exceeding max_stencil_offsets={limit}."
        )
    signed32 = np.asarray(signed, dtype=np.int32)
    block_vector = np.asarray(block, dtype=np.int64)
    nominal = np.floor_divide(signed, block_vector[None, :]).astype(np.int32)
    remainder = (signed - nominal.astype(np.int64) * block_vector[None, :]).astype(np.int16)
    group_map: dict[tuple[int, int, int], list[int]] = {}
    for index, raw in enumerate(nominal):
        key = tuple(int(value) for value in raw)
        group_map.setdefault(key, []).append(index)
    groups: list[BlockOffsetStencilGroup] = []
    for key in sorted(group_map):
        indices = np.asarray(group_map[key], dtype=np.int32)
        groups.append(
            BlockOffsetStencilGroup(
                nominal_block_offset=key,
                stencil_indices=indices,
                signed_offsets=signed32[indices],
                local_remainders=remainder[indices],
            )
        )
    relative = np.asarray(
        [group.nominal_block_offset for group in groups], dtype=np.int32
    )
    logical = stencil.grid_shape
    grid = block_grid_shape(logical, block)
    axis_extents: list[tuple[int, ...]] = []
    unique_extents: list[tuple[int, ...]] = []
    for axis in range(3):
        full_count = grid[axis] - 1
        terminal = logical[axis] - full_count * block[axis]
        values = tuple([block[axis]] * full_count + [terminal])
        axis_extents.append(values)
        unique_extents.append(tuple(sorted(set(values))))
    classes = np.asarray(
        sorted(product(*unique_extents)), dtype=np.int32
    )
    bitsets = np.vstack(
        [validity_bitset_for_extent(tuple(int(v) for v in extent), block) for extent in classes]
    ).astype(np.uint64, copy=False)
    return PeriodicKernelBlockRouting(
        logical_grid_shape=logical,
        storage_block_shape=block,
        block_grid_shape=grid,
        axis_block_extents=tuple(axis_extents),  # type: ignore[arg-type]
        stencil_identity=stencil_content_identity(stencil),
        signed_offsets=signed32,
        relative_block_offsets=relative,
        grouped_stencil_ranges=tuple(groups),
        terminal_extent_classes=classes,
        terminal_validity_bitsets=bitsets,
        metadata={
            "bit_order": "c_order_local_index_little_endian_uint64",
            "signed_offset_convention": "nyquist_positive",
            "routing_scope": "source_independent_exact_modular_stencil",
            "source_field_data_present": False,
            "forbidden_interaction_map_materialized": False,
        },
    )


@dataclass(frozen=True, slots=True)
class DensityRoutingCacheInfo:
    hits: int
    misses: int
    insertions: int
    evictions: int
    current_entries: int
    retained_array_bytes: int
    max_entries: int
    max_array_bytes: int
    metadata: FrozenJSONMapping | Mapping[str, Any] = field(
        default_factory=FrozenJSONMapping
    )
    schema_version: str = DENSITY_ROUTING_CACHE_INFO_SCHEMA

    def __post_init__(self) -> None:
        if self.schema_version != DENSITY_ROUTING_CACHE_INFO_SCHEMA:
            raise GraphAdapterError(
                f"Unsupported routing-cache schema {self.schema_version!r}."
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
        object.__setattr__(
            self, "max_entries", _positive_int(self.max_entries, name="max_entries")
        )
        object.__setattr__(
            self,
            "max_array_bytes",
            _positive_int(self.max_array_bytes, name="max_array_bytes"),
        )
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


class _RoutingCache:
    def __init__(self, *, max_entries: int, max_array_bytes: int) -> None:
        self.max_entries = _positive_int(max_entries, name="max_entries")
        self.max_array_bytes = _positive_int(max_array_bytes, name="max_array_bytes")
        self._entries: OrderedDict[str, tuple[PeriodicKernelBlockRouting, int]] = OrderedDict()
        self._bytes = 0
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
                len(self._entries) > self.max_entries or self._bytes > self.max_array_bytes
            ):
                _, (_, removed) = self._entries.popitem(last=False)
                self._bytes -= removed
                self._evictions += 1

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._bytes = 0
            self._hits = 0
            self._misses = 0
            self._insertions = 0
            self._evictions = 0

    def get(self, key: str) -> PeriodicKernelBlockRouting | None:
        with self._lock:
            item = self._entries.pop(key, None)
            if item is None:
                self._misses += 1
                return None
            self._entries[key] = item
            self._hits += 1
            return item[0]

    def insert(
        self, key: str, routing: PeriodicKernelBlockRouting
    ) -> PeriodicKernelBlockRouting:
        size = routing.retained_array_bytes
        with self._lock:
            existing = self._entries.pop(key, None)
            if existing is not None:
                self._entries[key] = existing
                return existing[0]
            if size > self.max_array_bytes:
                return routing
            while self._entries and (
                len(self._entries) >= self.max_entries
                or self._bytes + size > self.max_array_bytes
            ):
                _, (_, removed) = self._entries.popitem(last=False)
                self._bytes -= removed
                self._evictions += 1
            self._entries[key] = (routing, size)
            self._bytes += size
            self._insertions += 1
            return routing

    def info(self) -> DensityRoutingCacheInfo:
        with self._lock:
            return DensityRoutingCacheInfo(
                hits=self._hits,
                misses=self._misses,
                insertions=self._insertions,
                evictions=self._evictions,
                current_entries=len(self._entries),
                retained_array_bytes=self._bytes,
                max_entries=self.max_entries,
                max_array_bytes=self.max_array_bytes,
                metadata={"cache_kind": "periodic_kernel_block_routing_lru"},
            )


_ROUTING_CACHE = _RoutingCache(
    max_entries=DEFAULT_ROUTING_CACHE_MAX_ENTRIES,
    max_array_bytes=DEFAULT_ROUTING_CACHE_MAX_BYTES,
)


def _routing_cache_key(
    stencil: PeriodicGaussianStencilSupport,
    storage_block_shape: tuple[int, int, int],
) -> str:
    digest = hashlib.sha256()
    digest.update(stencil_content_identity(stencil).encode("ascii"))
    digest.update(
        np.asarray(_shape3(storage_block_shape, name="storage_block_shape"), dtype=np.int64).tobytes()
    )
    return digest.hexdigest()


def get_periodic_kernel_block_routing(
    stencil: PeriodicGaussianStencilSupport,
    *,
    storage_block_shape: tuple[int, int, int] = (16, 16, 16),
    max_stencil_offsets: int | None = None,
    use_cache: bool = True,
    max_cache_entries: int | None = None,
    max_cache_bytes: int | None = None,
) -> tuple[PeriodicKernelBlockRouting, bool]:
    """Return an exact routing template and whether it came from the bounded cache."""

    budget, _model, derived = resolve_density_resource_limits()
    default_offset_limit = derived["max_density_stencil_values"]
    offset_limit = (
        default_offset_limit
        if max_stencil_offsets is None
        else min(
            default_offset_limit,
            _positive_int(max_stencil_offsets, name="max_stencil_offsets"),
        )
    )
    default_cache_entries = max(4, 2 * budget.max_threads)
    cache_entries = (
        default_cache_entries
        if max_cache_entries is None
        else min(
            default_cache_entries,
            _positive_int(max_cache_entries, name="max_cache_entries"),
        )
    )
    cache_bytes = (
        max(1, budget.max_memory_bytes // 20)
        if max_cache_bytes is None
        else min(_positive_int(max_cache_bytes, name="max_cache_bytes"), budget.max_memory_bytes)
    )
    _ROUTING_CACHE.configure(max_entries=cache_entries, max_array_bytes=cache_bytes)
    key = _routing_cache_key(stencil, storage_block_shape)
    if use_cache:
        cached = _ROUTING_CACHE.get(key)
        if cached is not None:
            if cached.stencil_offset_count > offset_limit:
                raise GraphComplexityError(
                    "Cached routing exceeds the caller's max_stencil_offsets limit."
                )
            return cached, True
    routing = build_periodic_kernel_block_routing(
        stencil,
        storage_block_shape=storage_block_shape,
        max_stencil_offsets=offset_limit,
    )
    if use_cache:
        routing = _ROUTING_CACHE.insert(key, routing)
    return routing, False


def clear_density_routing_cache() -> None:
    _ROUTING_CACHE.clear()


def density_routing_cache_info() -> DensityRoutingCacheInfo:
    return _ROUTING_CACHE.info()
